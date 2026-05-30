#include "ProcessEventHook.h"
#include "ProcessEventCallGuard.h"
#include "ProcessEventDispatch.h"
#include "ProcessEventChatReflection.h"
#include "ProcessEventInventoryReflection.h"
#include "ProcessEventItemReflection.h"
#include "ProcessEventStructureReflection.h"
#include "core/ItemReturnEventDispatcher.h"
#include "ue/Memory.h"
#include "runtime/Logger.h"
#include "runtime/RuntimeMarkers.h"
#include "core/EventManager.h"
#include <array>
#include <atomic>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <exception>
#include <mutex>
#include <span>
#include <string>
#include <string_view>
#include <sys/mman.h>
#include <thread>
#include <unistd.h>

namespace Obelisk::Hooks
{
    typedef void (*ProcessEvent_t)(void* object, void* function, void* params);

    struct FNameProbe {
        int32_t ComparisonIndex;
        int32_t Number;
    };

    struct UObjectProbe {
        void** VTable;
        int32_t ObjectFlags;
        int32_t InternalIndex;
        void* ClassPrivate;
        FNameProbe NamePrivate;
    };

    namespace
    {
        constexpr size_t kJumpSize = 12;
        constexpr size_t kPatchSize = 18;
        constexpr size_t kTrampolineSize = kPatchSize + kJumpSize;
        constexpr std::array<uint8_t, kPatchSize> kExpectedProcessEventPrologue = {
            0x55, 0x48, 0x89, 0xE5, 0x41, 0x57, 0x41, 0x56, 0x41,
            0x54, 0x53, 0x48, 0x81, 0xEC, 0xA0, 0x00, 0x00, 0x00
        };

        struct AbsoluteHook
        {
            void* Target = nullptr;
            void* Detour = nullptr;
            void* Trampoline = nullptr;
            std::array<uint8_t, kPatchSize> OriginalBytes{};
            bool Installed = false;
        };

        AbsoluteHook s_ProcessEventHook;
        std::mutex s_ProcessEventHookMutex;

        class ActiveProcessEventFrame
        {
        public:
            ActiveProcessEventFrame();
            ~ActiveProcessEventFrame();
            ActiveProcessEventFrame(const ActiveProcessEventFrame&) = delete;
            ActiveProcessEventFrame& operator=(const ActiveProcessEventFrame&) = delete;
        };

        thread_local bool* s_CurrentOriginalProcessEventCalled = nullptr;

        class OriginalProcessEventCallFlagScope
        {
        public:
            explicit OriginalProcessEventCallFlagScope(bool& originalWasCalled)
                : m_Previous(s_CurrentOriginalProcessEventCalled)
            {
                s_CurrentOriginalProcessEventCalled = &originalWasCalled;
            }

            OriginalProcessEventCallFlagScope(const OriginalProcessEventCallFlagScope&) = delete;
            OriginalProcessEventCallFlagScope& operator=(const OriginalProcessEventCallFlagScope&) = delete;

            ~OriginalProcessEventCallFlagScope()
            {
                s_CurrentOriginalProcessEventCalled = m_Previous;
            }

        private:
            bool* m_Previous = nullptr;
        };
    }

    static std::atomic<uint32_t> s_ActiveProcessEventFrames{0};
    static std::atomic<bool> s_RemovingProcessEventHook{false};
    static std::atomic<uint64_t> s_ProcessEventCalls{0};
    static std::atomic<uint64_t> s_ReflectedChatCalls{0};
    static std::atomic<uint64_t> s_ReflectedChatRejects{0};
    static std::atomic<uint64_t> s_ReflectedChatEventDispatches{0};
    static std::atomic<uint64_t> s_ChatRouteObserverSequences{0};
    static std::atomic<uint64_t> s_ReflectedInventoryCalls{0};
    static std::atomic<uint64_t> s_ReflectedInventoryRejects{0};
    static std::atomic<uint64_t> s_ReflectedInventoryDispatches{0};
    static std::atomic<uint64_t> s_ReflectedItemReturnRejects{0};
    static std::atomic<uint64_t> s_ReflectedItemReturnAttempts{0};
    static std::atomic<uint64_t> s_ReflectedItemReturnDispatches{0};
    static std::atomic<uint64_t> s_ReflectedStructureCalls{0};
    static std::atomic<uint64_t> s_ReflectedStructureDispatches{0};
    static std::atomic<uint64_t> s_ReflectedStructureRejects{0};

    static void WriteAbsoluteJump(uint8_t* at, void* destination)
    {
        // mov rax, imm64; jmp rax. This works regardless of the distance between
        // ShooterGameServer .text and libobelisk.so.
        at[0] = 0x48;
        at[1] = 0xB8;
        uintptr_t dst = reinterpret_cast<uintptr_t>(destination);
        std::memcpy(at + 2, &dst, sizeof(dst));
        at[10] = 0xFF;
        at[11] = 0xE0;
    }

    static bool MakeWritableExecutable(void* address, size_t size)
    {
        const long pageSize = sysconf(_SC_PAGESIZE);
        if (pageSize <= 0)
            return false;

        uintptr_t start = reinterpret_cast<uintptr_t>(address) & ~(static_cast<uintptr_t>(pageSize) - 1);
        uintptr_t end = (reinterpret_cast<uintptr_t>(address) + size + pageSize - 1) & ~(static_cast<uintptr_t>(pageSize) - 1);
        return mprotect(reinterpret_cast<void*>(start), end - start, PROT_READ | PROT_WRITE | PROT_EXEC) == 0;
    }

    static bool MakeReadableExecutable(void* address, size_t size)
    {
        const long pageSize = sysconf(_SC_PAGESIZE);
        if (pageSize <= 0)
            return false;

        uintptr_t start = reinterpret_cast<uintptr_t>(address) & ~(static_cast<uintptr_t>(pageSize) - 1);
        uintptr_t end = (reinterpret_cast<uintptr_t>(address) + size + pageSize - 1) & ~(static_cast<uintptr_t>(pageSize) - 1);
        return mprotect(reinterpret_cast<void*>(start), end - start, PROT_READ | PROT_EXEC) == 0;
    }

    static bool IsInExecutableSegment(void* address, size_t size, const Memory::ModuleInfo& moduleInfo)
    {
        if (!address || size == 0 || !moduleInfo.found)
            return false;

        const uintptr_t start = reinterpret_cast<uintptr_t>(address);
        if (start < moduleInfo.start)
            return false;
        if (start > UINTPTR_MAX - size)
            return false;

        const uintptr_t end = start + size;
        return end <= moduleInfo.end;
    }

    static bool HasExpectedProcessEventPrologue(void* target)
    {
        if (!Memory::IsReadable(target, kExpectedProcessEventPrologue.size()))
            return false;

        return std::memcmp(target,
                           kExpectedProcessEventPrologue.data(),
                           kExpectedProcessEventPrologue.size()) == 0;
    }

    static bool ValidateProcessEventTarget(void* target,
                                           const Memory::ModuleInfo& moduleInfo,
                                           const char* source)
    {
        if (!target)
        {
            OBELISK_WARN("Rejected null ProcessEvent {} candidate.", source);
            return false;
        }

        if (!IsInExecutableSegment(target, kPatchSize, moduleInfo))
        {
            OBELISK_WARN("Rejected ProcessEvent {} candidate {}: outside ShooterGameServer executable segment.",
                         source, target);
            return false;
        }

        if (!HasExpectedProcessEventPrologue(target))
        {
            OBELISK_WARN("Rejected ProcessEvent {} candidate {}: unexpected or unreadable prologue.",
                         source, target);
            return false;
        }

        return true;
    }

    static bool InstallAbsoluteHook(AbsoluteHook& hook, void* target, void* detour)
    {
        if (!target || !detour)
            return false;
        if (!Memory::IsReadable(target, kPatchSize))
            return false;

        hook.Target = target;
        hook.Detour = detour;
        std::memcpy(hook.OriginalBytes.data(), target, hook.OriginalBytes.size());

        void* trampoline = mmap(nullptr, kTrampolineSize, PROT_READ | PROT_WRITE | PROT_EXEC,
                                MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (trampoline == MAP_FAILED)
        {
            hook.Trampoline = nullptr;
            return false;
        }

        auto* trampolineBytes = static_cast<uint8_t*>(trampoline);
        std::memcpy(trampolineBytes, hook.OriginalBytes.data(), kPatchSize);
        WriteAbsoluteJump(trampolineBytes + kPatchSize, static_cast<uint8_t*>(target) + kPatchSize);
        __builtin___clear_cache(reinterpret_cast<char*>(trampolineBytes),
                                reinterpret_cast<char*>(trampolineBytes + kTrampolineSize));

        if (!MakeWritableExecutable(target, kPatchSize))
        {
            munmap(trampoline, kTrampolineSize);
            hook.Trampoline = nullptr;
            return false;
        }

        auto* targetBytes = static_cast<uint8_t*>(target);
        WriteAbsoluteJump(targetBytes, detour);
        for (size_t i = kJumpSize; i < kPatchSize; ++i)
            targetBytes[i] = 0x90;

        __builtin___clear_cache(reinterpret_cast<char*>(targetBytes),
                                reinterpret_cast<char*>(targetBytes + kPatchSize));
        if (!MakeReadableExecutable(target, kPatchSize))
        {
            std::memcpy(targetBytes, hook.OriginalBytes.data(), hook.OriginalBytes.size());
            __builtin___clear_cache(reinterpret_cast<char*>(targetBytes),
                                    reinterpret_cast<char*>(targetBytes + kPatchSize));
            munmap(trampoline, kTrampolineSize);
            hook = {};
            return false;
        }

        hook.Trampoline = trampoline;
        hook.Installed = true;
        return true;
    }

    ActiveProcessEventFrame::ActiveProcessEventFrame()
    {
        s_ActiveProcessEventFrames.fetch_add(1, std::memory_order_acq_rel);
    }

    ActiveProcessEventFrame::~ActiveProcessEventFrame()
    {
        s_ActiveProcessEventFrames.fetch_sub(1, std::memory_order_acq_rel);
    }

    static bool WaitForActiveProcessEventFramesToDrain()
    {
        for (int attempt = 0; attempt < 100; ++attempt)
        {
            if (s_ActiveProcessEventFrames.load(std::memory_order_acquire) == 0)
                return true;
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
        return s_ActiveProcessEventFrames.load(std::memory_order_acquire) == 0;
    }

    static ProcessEvent_t SnapshotOriginalProcessEvent()
    {
        std::lock_guard<std::mutex> lock(s_ProcessEventHookMutex);
        if (s_RemovingProcessEventHook.load(std::memory_order_acquire))
            return nullptr;
        if (!s_ProcessEventHook.Installed || !s_ProcessEventHook.Trampoline)
            return nullptr;
        return reinterpret_cast<ProcessEvent_t>(s_ProcessEventHook.Trampoline);
    }

    static void CallOriginalProcessEventFromDetour(void* object, void* function, void* params)
    {
        ProcessEvent_t original = SnapshotOriginalProcessEvent();
        if (!original)
        {
            if (s_RemovingProcessEventHook.load(std::memory_order_acquire))
                OBELISK_WARN("ProcessEvent original skipped while hook removal is in progress.");
            return;
        }

        if (s_CurrentOriginalProcessEventCalled)
            *s_CurrentOriginalProcessEventCalled = true;
        original(object, function, params);
    }

    static void TryCallOriginalProcessEventAfterDetourFailure(
        bool& originalWasCalled,
        void* object,
        void* function,
        void* params)
    {
        if (originalWasCalled)
            return;

        try
        {
            CallOriginalProcessEventFromDetour(object, function, params);
        }
        catch (const std::exception& e)
        {
            OBELISK_CRITICAL("ProcessEvent original threw while recovering from detour failure: {}", e.what());
        }
        catch (...)
        {
            OBELISK_CRITICAL("ProcessEvent original threw an unknown exception while recovering from detour failure.");
        }
    }

    static bool RemoveAbsoluteHook(AbsoluteHook& hook)
    {
        {
            std::lock_guard<std::mutex> lock(s_ProcessEventHookMutex);
            if (!hook.Installed || !hook.Target)
                return true;

            s_RemovingProcessEventHook.store(true, std::memory_order_release);

            if (!MakeWritableExecutable(hook.Target, kPatchSize))
            {
                s_RemovingProcessEventHook.store(false, std::memory_order_release);
                OBELISK_CRITICAL("ProcessEvent hook removal failed: target page could not be made writable; hook state preserved.");
                return false;
            }

            std::memcpy(hook.Target, hook.OriginalBytes.data(), hook.OriginalBytes.size());
            __builtin___clear_cache(reinterpret_cast<char*>(hook.Target),
                                    reinterpret_cast<char*>(static_cast<uint8_t*>(hook.Target) + kPatchSize));
            if (!MakeReadableExecutable(hook.Target, kPatchSize))
            {
                s_RemovingProcessEventHook.store(false, std::memory_order_release);
                OBELISK_CRITICAL("ProcessEvent hook removal failed: restored target page could not be made RX; hook state and trampoline preserved.");
                return false;
            }

            // The patched target is restored now, so no new detour frames should enter
            // through ProcessEvent. Let already-active frames keep resolving the
            // trampoline while they drain; otherwise they can incorrectly skip the
            // original call during shutdown.
            s_RemovingProcessEventHook.store(false, std::memory_order_release);
        }

        const bool drained = WaitForActiveProcessEventFramesToDrain();

        {
            std::lock_guard<std::mutex> lock(s_ProcessEventHookMutex);
            s_RemovingProcessEventHook.store(true, std::memory_order_release);

            if (!drained || s_ActiveProcessEventFrames.load(std::memory_order_acquire) != 0)
            {
                s_RemovingProcessEventHook.store(false, std::memory_order_release);
                OBELISK_WARN("ProcessEvent hook removal deferred because {} frame(s) were still active; hook state and trampoline preserved.",
                             s_ActiveProcessEventFrames.load(std::memory_order_acquire));
                return false;
            }

            if (hook.Trampoline && drained)
                munmap(hook.Trampoline, kTrampolineSize);

            hook = {};
            s_RemovingProcessEventHook.store(false, std::memory_order_release);
        }
        return true;
    }

    static uint64_t GetTraceLimit()
    {
        static uint64_t limit = [] {
            const char* env = std::getenv("OBELISK_PE_TRACE_LIMIT");
            if (!env || env[0] == '\0') return uint64_t{0};
            return static_cast<uint64_t>(std::strtoull(env, nullptr, 10));
        }();
        return limit;
    }

    static void TraceProcessEventCall(uint64_t callNumber, void* object, void* function, void* params)
    {
        uint64_t limit = GetTraceLimit();
        if (limit == 0)
            return;
        if (callNumber > limit && (callNumber % 100000) != 0)
            return;

        int32_t functionNameIndex = -1;
        int32_t functionNameNumber = -1;
        if (Memory::IsReadable(function, sizeof(UObjectProbe)))
        {
            auto* functionObject = static_cast<UObjectProbe*>(function);
            functionNameIndex = functionObject->NamePrivate.ComparisonIndex;
            functionNameNumber = functionObject->NamePrivate.Number;
        }

        OBELISK_INFO("ProcessEvent detour hit #{} object={} function={} params={} fname_index={} fname_number={}",
                     callNumber, object, function, params, functionNameIndex, functionNameNumber);
    }

    static int32_t GetFunctionNameIndex(void* function)
    {
        if (!Memory::IsReadable(function, sizeof(UObjectProbe)))
            return -1;

        auto* functionObject = static_cast<UObjectProbe*>(function);
        return functionObject->NamePrivate.ComparisonIndex;
    }

    static bool RuntimeReflectionReader(const void* address, size_t size, void*)
    {
        return Memory::IsReadable(const_cast<void*>(address), size);
    }

    static bool AreExperimentalObserverMarkersEnabled(const char* observerMarkerName)
    {
        return Runtime::AreInstanceMarkersEnabled(std::getenv("OBELISK_ROOT"),
                                                  std::getenv("OBELISK_INSTANCE_ID"),
                                                  "allow-experimental-observers",
                                                  observerMarkerName);
    }

    static bool IsObserverDebugProfileEnabled()
    {
        const char* profile = std::getenv("OBELISK_WRAPPER_PROFILE");
        return profile && std::strcmp(profile, "observer-debug") == 0;
    }

    static bool IsObserverDebugWindowMarkerEnabled()
    {
        return Runtime::IsInstanceMarkerEnabled(std::getenv("OBELISK_ROOT"),
                                                std::getenv("OBELISK_INSTANCE_ID"),
                                                "allow-observer-debug-window");
    }

    static bool IsChatReflectionObserverDebugGateEnabled()
    {
        return IsObserverDebugProfileEnabled() &&
               IsObserverDebugWindowMarkerEnabled() &&
               AreExperimentalObserverMarkersEnabled("enable-chat-reflection");
    }

    static bool IsChatEventsObserverDebugGateEnabled()
    {
        return IsObserverDebugProfileEnabled() &&
               IsObserverDebugWindowMarkerEnabled() &&
               AreExperimentalObserverMarkersEnabled("enable-chat-events");
    }

    static bool IsChatRouteObserverDebugGateEnabled()
    {
        return IsObserverDebugProfileEnabled() &&
               IsObserverDebugWindowMarkerEnabled() &&
               AreExperimentalObserverMarkersEnabled("enable-chat-route-observer");
    }

    static const ProcessEventChatReflection::Gate& GetChatReflectionGate()
    {
        static ProcessEventChatReflection::Gate gate = [] {
            ProcessEventChatReflection::Gate value =
                ProcessEventChatReflection::EvaluateGate(
                    std::getenv("OBELISK_ENABLE_CHAT_REFLECTION"),
                    IsChatReflectionObserverDebugGateEnabled(),
                    std::getenv("OBELISK_CHAT_REFLECTION_BINARY_SHA256"));

            switch (value.Status)
            {
            case ProcessEventChatReflection::GateStatus::Disabled:
                break;
            case ProcessEventChatReflection::GateStatus::MissingInstanceMarker:
                if (!IsObserverDebugProfileEnabled())
                {
                    OBELISK_WARN("Chat reflection disabled: OBELISK_WRAPPER_PROFILE=observer-debug is required.");
                }
                else if (!IsObserverDebugWindowMarkerEnabled())
                {
                    OBELISK_WARN("Chat reflection disabled: allow-observer-debug-window instance marker is required.");
                }
                else
                {
                    OBELISK_WARN("Chat reflection disabled: instance markers allow-experimental-observers and "
                                 "enable-chat-reflection are required.");
                }
                break;
            case ProcessEventChatReflection::GateStatus::MissingBinarySha256:
                OBELISK_WARN("Chat reflection disabled: OBELISK_CHAT_REFLECTION_BINARY_SHA256 is required.");
                break;
            case ProcessEventChatReflection::GateStatus::UnsupportedBinarySha256:
                OBELISK_WARN("Chat reflection disabled: unsupported ShooterGameServer SHA256 '{}'.",
                             value.BinarySha256);
                break;
            case ProcessEventChatReflection::GateStatus::Enabled:
                OBELISK_WARN("Experimental chat reflection enabled for ShooterGameServer SHA256 {}.",
                             value.BinarySha256);
                break;
            }

            return value;
        }();
        return gate;
    }

    static bool IsChatReflectionEnabled()
    {
        return GetChatReflectionGate().Enabled();
    }

    static const ProcessEventChatReflection::Gate& GetChatEventProducerGate()
    {
        static ProcessEventChatReflection::Gate gate = [] {
            ProcessEventChatReflection::Gate value =
                ProcessEventChatReflection::EvaluateGate(
                    std::getenv("OBELISK_ENABLE_CHAT_EVENTS"),
                    IsChatEventsObserverDebugGateEnabled(),
                    std::getenv("OBELISK_CHAT_EVENTS_BINARY_SHA256"));

            switch (value.Status)
            {
            case ProcessEventChatReflection::GateStatus::Disabled:
                break;
            case ProcessEventChatReflection::GateStatus::MissingInstanceMarker:
                if (!IsObserverDebugProfileEnabled())
                {
                    OBELISK_WARN("Chat message event producer disabled: OBELISK_WRAPPER_PROFILE=observer-debug is required.");
                }
                else if (!IsObserverDebugWindowMarkerEnabled())
                {
                    OBELISK_WARN("Chat message event producer disabled: allow-observer-debug-window instance marker is required.");
                }
                else
                {
                    OBELISK_WARN("Chat message event producer disabled: instance markers allow-experimental-observers and "
                                 "enable-chat-events are required.");
                }
                break;
            case ProcessEventChatReflection::GateStatus::MissingBinarySha256:
                OBELISK_WARN("Chat message event producer disabled: OBELISK_CHAT_EVENTS_BINARY_SHA256 is required.");
                break;
            case ProcessEventChatReflection::GateStatus::UnsupportedBinarySha256:
                OBELISK_WARN("Chat message event producer disabled: unsupported ShooterGameServer SHA256 '{}'.",
                             value.BinarySha256);
                break;
            case ProcessEventChatReflection::GateStatus::Enabled:
                OBELISK_WARN("Chat message event producer enabled for ShooterGameServer SHA256 {}.",
                             value.BinarySha256);
                break;
            }

            return value;
        }();
        return gate;
    }

    static bool IsChatEventProducerEnabled()
    {
        return GetChatEventProducerGate().Enabled();
    }

    static const ProcessEventChatReflection::Gate& GetChatRouteObserverGate()
    {
        static ProcessEventChatReflection::Gate gate = [] {
            ProcessEventChatReflection::Gate value =
                ProcessEventChatReflection::EvaluateGate(
                    std::getenv("OBELISK_ENABLE_CHAT_ROUTE_OBSERVER"),
                    IsChatRouteObserverDebugGateEnabled(),
                    std::getenv("OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256"));

            switch (value.Status)
            {
            case ProcessEventChatReflection::GateStatus::Disabled:
                break;
            case ProcessEventChatReflection::GateStatus::MissingInstanceMarker:
                if (!IsObserverDebugProfileEnabled())
                {
                    OBELISK_WARN("Chat route observer disabled: OBELISK_WRAPPER_PROFILE=observer-debug is required.");
                }
                else if (!IsObserverDebugWindowMarkerEnabled())
                {
                    OBELISK_WARN("Chat route observer disabled: allow-observer-debug-window instance marker is required.");
                }
                else
                {
                    OBELISK_WARN("Chat route observer disabled: instance markers allow-experimental-observers and "
                                 "enable-chat-route-observer are required.");
                }
                break;
            case ProcessEventChatReflection::GateStatus::MissingBinarySha256:
                OBELISK_WARN("Chat route observer disabled: OBELISK_CHAT_ROUTE_OBSERVER_BINARY_SHA256 is required.");
                break;
            case ProcessEventChatReflection::GateStatus::UnsupportedBinarySha256:
                OBELISK_WARN("Chat route observer disabled: unsupported ShooterGameServer SHA256 '{}'.",
                             value.BinarySha256);
                break;
            case ProcessEventChatReflection::GateStatus::Enabled:
                OBELISK_WARN("Chat route observer enabled for ShooterGameServer SHA256 {}.",
                             value.BinarySha256);
                break;
            }

            return value;
        }();
        return gate;
    }

    static bool IsChatRouteObserverEnabled()
    {
        return GetChatRouteObserverGate().Enabled();
    }

    static const ProcessEventStructureReflection::Gate& GetStructureReflectionGate()
    {
        static ProcessEventStructureReflection::Gate gate = [] {
            ProcessEventStructureReflection::Gate value =
                ProcessEventStructureReflection::EvaluateGate(
                    std::getenv("OBELISK_ENABLE_STRUCTURE_REFLECTION"),
                    IsObserverDebugProfileEnabled(),
                    IsObserverDebugWindowMarkerEnabled(),
                    AreExperimentalObserverMarkersEnabled("enable-structure-reflection"),
                    std::getenv("OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256"));

            switch (value.Status)
            {
            case ProcessEventStructureReflection::GateStatus::Disabled:
                break;
            case ProcessEventStructureReflection::GateStatus::MissingObserverDebugProfile:
                OBELISK_WARN("Structure reflection disabled: OBELISK_WRAPPER_PROFILE=observer-debug is required.");
                break;
            case ProcessEventStructureReflection::GateStatus::MissingObserverDebugWindow:
                OBELISK_WARN("Structure reflection disabled: allow-observer-debug-window instance marker is required.");
                break;
            case ProcessEventStructureReflection::GateStatus::MissingInstanceMarker:
                OBELISK_WARN("Structure reflection disabled: instance markers allow-experimental-observers and "
                             "enable-structure-reflection are required.");
                break;
            case ProcessEventStructureReflection::GateStatus::MissingBinarySha256:
                OBELISK_WARN("Structure reflection disabled: OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256 is required.");
                break;
            case ProcessEventStructureReflection::GateStatus::UnsupportedBinarySha256:
                OBELISK_WARN("Structure reflection disabled: unsupported ShooterGameServer SHA256 '{}'.",
                             value.BinarySha256);
                break;
            case ProcessEventStructureReflection::GateStatus::Enabled:
                OBELISK_WARN("Experimental structure reflection enabled for ShooterGameServer SHA256 {}.",
                             value.BinarySha256);
                break;
            }

            return value;
        }();
        return gate;
    }

    static bool IsStructureReflectionEnabled()
    {
        return GetStructureReflectionGate().Enabled();
    }

    static const ProcessEventInventoryReflection::Gate& GetInventoryReflectionGate()
    {
        static ProcessEventInventoryReflection::Gate gate = [] {
            ProcessEventInventoryReflection::Gate value =
                ProcessEventInventoryReflection::EvaluateGate(
                    std::getenv("OBELISK_ENABLE_INVENTORY_REFLECTION"),
                    IsObserverDebugProfileEnabled(),
                    IsObserverDebugWindowMarkerEnabled(),
                    AreExperimentalObserverMarkersEnabled("enable-inventory-reflection"),
                    std::getenv("OBELISK_INVENTORY_REFLECTION_BINARY_SHA256"));

            switch (value.Status)
            {
            case ProcessEventInventoryReflection::GateStatus::Disabled:
                break;
            case ProcessEventInventoryReflection::GateStatus::MissingObserverDebugProfile:
                OBELISK_WARN("Inventory reflection disabled: OBELISK_WRAPPER_PROFILE=observer-debug is required.");
                break;
            case ProcessEventInventoryReflection::GateStatus::MissingObserverDebugWindow:
                OBELISK_WARN("Inventory reflection disabled: allow-observer-debug-window instance marker is required.");
                break;
            case ProcessEventInventoryReflection::GateStatus::MissingInstanceMarker:
                OBELISK_WARN("Inventory reflection disabled: instance markers allow-experimental-observers and "
                             "enable-inventory-reflection are required.");
                break;
            case ProcessEventInventoryReflection::GateStatus::MissingBinarySha256:
                OBELISK_WARN("Inventory reflection disabled: OBELISK_INVENTORY_REFLECTION_BINARY_SHA256 is required.");
                break;
            case ProcessEventInventoryReflection::GateStatus::UnsupportedBinarySha256:
                OBELISK_WARN("Inventory reflection disabled: unsupported ShooterGameServer SHA256 '{}'.",
                             value.BinarySha256);
                break;
            case ProcessEventInventoryReflection::GateStatus::Enabled:
                OBELISK_WARN("Experimental inventory reflection enabled for ShooterGameServer SHA256 {}.",
                             value.BinarySha256);
                break;
            }

            return value;
        }();
        return gate;
    }

    static bool IsInventoryReflectionEnabled()
    {
        return GetInventoryReflectionGate().Enabled();
    }

    static const ProcessEventItemReflection::Gate& GetItemReturnEventGate()
    {
        static ProcessEventItemReflection::Gate gate = [] {
            ProcessEventItemReflection::Gate value =
                ProcessEventItemReflection::EvaluateGate(
                    std::getenv("OBELISK_ENABLE_ITEM_RETURN_EVENTS"),
                    IsObserverDebugProfileEnabled(),
                    IsObserverDebugWindowMarkerEnabled(),
                    AreExperimentalObserverMarkersEnabled("enable-item-return-events"),
                    std::getenv("OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256"));

            switch (value.Status)
            {
            case ProcessEventItemReflection::GateStatus::Disabled:
                break;
            case ProcessEventItemReflection::GateStatus::MissingObserverDebugProfile:
                OBELISK_WARN("Item return event producer disabled: OBELISK_WRAPPER_PROFILE=observer-debug is required.");
                break;
            case ProcessEventItemReflection::GateStatus::MissingObserverDebugWindow:
                OBELISK_WARN("Item return event producer disabled: allow-observer-debug-window instance marker is required.");
                break;
            case ProcessEventItemReflection::GateStatus::MissingInstanceMarker:
                OBELISK_WARN("Item return event producer disabled: instance markers allow-experimental-observers and "
                             "enable-item-return-events are required.");
                break;
            case ProcessEventItemReflection::GateStatus::MissingBinarySha256:
                OBELISK_WARN("Item return event producer disabled: OBELISK_ITEM_RETURN_EVENTS_BINARY_SHA256 is required.");
                break;
            case ProcessEventItemReflection::GateStatus::UnsupportedBinarySha256:
                OBELISK_WARN("Item return event producer disabled: unsupported ShooterGameServer SHA256 '{}'.",
                             value.BinarySha256);
                break;
            case ProcessEventItemReflection::GateStatus::Enabled:
                OBELISK_WARN("Experimental item return event producer enabled for ShooterGameServer SHA256 {}.",
                             value.BinarySha256);
                break;
            }

            return value;
        }();
        return gate;
    }

    static bool IsItemReturnEventProducerEnabled()
    {
        return GetItemReturnEventGate().Enabled();
    }

    static uint64_t GetChatReflectionLogLimit()
    {
        static uint64_t limit = [] {
            const char* env = std::getenv("OBELISK_CHAT_REFLECTION_LOG_LIMIT");
            if (!env || env[0] == '\0') return uint64_t{0};
            return static_cast<uint64_t>(std::strtoull(env, nullptr, 10));
        }();
        return limit;
    }

    static bool IsChatReflectionTextLoggingEnabled()
    {
        static bool enabled = [] {
            const char* env = std::getenv("OBELISK_CHAT_REFLECTION_LOG_TEXT");
            return env && std::strcmp(env, "1") == 0;
        }();
        return enabled;
    }

    static uint64_t GetChatEventDispatchLimit()
    {
        static uint64_t limit = [] {
            const char* env = std::getenv("OBELISK_CHAT_EVENTS_DISPATCH_LIMIT");
            if (!env || env[0] == '\0') return uint64_t{0};
            return static_cast<uint64_t>(std::strtoull(env, nullptr, 10));
        }();
        return limit;
    }

    static uint64_t GetChatRouteObserverLimit()
    {
        static uint64_t limit = [] {
            const char* env = std::getenv("OBELISK_CHAT_ROUTE_OBSERVER_LIMIT");
            if (!env || env[0] == '\0') return uint64_t{0};
            return static_cast<uint64_t>(std::strtoull(env, nullptr, 10));
        }();
        return limit;
    }

    static bool IsChatEventProducerActive()
    {
        const uint64_t dispatchLimit = GetChatEventDispatchLimit();
        return IsChatEventProducerEnabled() &&
               ProcessEventChatReflection::ShouldAttemptObservation(dispatchLimit) &&
               s_ReflectedChatEventDispatches.load(std::memory_order_relaxed) < dispatchLimit &&
               Core::ChatEventDispatcher::Get().SubscriptionCount() > 0;
    }

    static bool IsChatRouteObserverActive()
    {
        const uint64_t limit = GetChatRouteObserverLimit();
        return ProcessEventChatReflection::ShouldAttemptObservation(limit) &&
               IsChatRouteObserverEnabled() &&
               s_ChatRouteObserverSequences.load(std::memory_order_relaxed) < limit;
    }

    static uint64_t GetStructureReflectionLogLimit()
    {
        static uint64_t limit = [] {
            const char* env = std::getenv("OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT");
            if (!env || env[0] == '\0') return uint64_t{0};
            return static_cast<uint64_t>(std::strtoull(env, nullptr, 10));
        }();
        return limit;
    }

    static uint64_t GetStructureReflectionDispatchLimit()
    {
        static uint64_t limit = [] {
            const char* env = std::getenv("OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT");
            if (!env || env[0] == '\0') return uint64_t{0};
            return static_cast<uint64_t>(std::strtoull(env, nullptr, 10));
        }();
        return limit;
    }

    static uint64_t GetInventoryReflectionLogLimit()
    {
        static uint64_t limit = [] {
            const char* env = std::getenv("OBELISK_INVENTORY_REFLECTION_LOG_LIMIT");
            if (!env || env[0] == '\0') return uint64_t{0};
            return static_cast<uint64_t>(std::strtoull(env, nullptr, 10));
        }();
        return limit;
    }

    static uint64_t GetInventoryReflectionDispatchLimit()
    {
        static uint64_t limit = [] {
            const char* env = std::getenv("OBELISK_INVENTORY_REFLECTION_DISPATCH_LIMIT");
            if (!env || env[0] == '\0') return uint64_t{0};
            return static_cast<uint64_t>(std::strtoull(env, nullptr, 10));
        }();
        return limit;
    }

    static uint64_t GetItemReturnEventDispatchLimit()
    {
        static uint64_t limit = [] {
            const char* env = std::getenv("OBELISK_ITEM_RETURN_EVENTS_DISPATCH_LIMIT");
            if (!env || env[0] == '\0') return uint64_t{0};
            return static_cast<uint64_t>(std::strtoull(env, nullptr, 10));
        }();
        return limit;
    }

    static uint64_t GetItemReturnEventLogLimit()
    {
        static uint64_t limit = [] {
            const char* env = std::getenv("OBELISK_ITEM_RETURN_EVENTS_LOG_LIMIT");
            if (!env || env[0] == '\0') return uint64_t{0};
            return static_cast<uint64_t>(std::strtoull(env, nullptr, 10));
        }();
        return limit;
    }

    static bool IsStructureObservationActive()
    {
        const uint64_t logLimit = GetStructureReflectionLogLimit();
        const uint64_t dispatchLimit = GetStructureReflectionDispatchLimit();
        return IsStructureReflectionEnabled() &&
               (ProcessEventStructureReflection::HasObservationBudgetRemaining(
                    s_ReflectedStructureCalls,
                    logLimit) ||
                ProcessEventStructureReflection::ShouldAttemptDispatchObservation(
                    s_ReflectedStructureDispatches,
                    dispatchLimit,
                    Core::StructureEventDispatcher::Get().SubscriptionCount()));
    }

    static bool IsInventoryObservationActive()
    {
        const uint64_t logLimit = GetInventoryReflectionLogLimit();
        const uint64_t dispatchLimit = GetInventoryReflectionDispatchLimit();
        return IsInventoryReflectionEnabled() &&
               (ProcessEventInventoryReflection::HasObservationBudgetRemaining(
                    s_ReflectedInventoryCalls,
                    logLimit) ||
                ProcessEventInventoryReflection::ShouldAttemptDispatchObservation(
                    s_ReflectedInventoryDispatches,
                    dispatchLimit,
                    Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount()));
    }

    static bool IsItemReturnEventProducerActive()
    {
        const uint64_t dispatchLimit = GetItemReturnEventDispatchLimit();
        return IsItemReturnEventProducerEnabled() &&
               ProcessEventItemReflection::ShouldAttemptRuntimeObservation(
                   s_ReflectedItemReturnAttempts,
                   dispatchLimit) &&
               Core::ItemReturnEventDispatcher::Get().SubscriptionCount() > 0;
    }

    static const char* ChatFunctionName(Obelisk::UE::ChatReflection::ChatFunction function)
    {
        using Obelisk::UE::ChatReflection::ChatFunction;
        switch (function)
        {
        case ChatFunction::ServerChat:
            return "ServerChat";
        case ChatFunction::ServerChatTo:
            return "ServerChatTo";
        case ChatFunction::ServerChatToPlayer:
            return "ServerChatToPlayer";
        case ChatFunction::ServerSendChatMessage:
            return "ServerSendChatMessage";
        case ChatFunction::ClientChatMessage:
            return "ClientChatMessage";
        case ChatFunction::ClientServerChatDirectMessage:
            return "ClientServerChatDirectMessage";
        case ChatFunction::ClientServerChatMessage:
            return "ClientServerChatMessage";
        case ChatFunction::SendServerChatMessage:
            return "SendServerChatMessage";
        case ChatFunction::OnServerChatMessageDelegate:
            return "OnServerChatMessage__DelegateSignature";
        }
        return "Unknown";
    }

    static const char* ChatFieldName(Obelisk::UE::ChatReflection::ChatField field)
    {
        using Obelisk::UE::ChatReflection::ChatField;
        switch (field)
        {
        case ChatField::MessageText:
            return "MessageText";
        case ChatField::SteamID:
            return "SteamID";
        case ChatField::PlayerName:
            return "PlayerName";
        case ChatField::ChatMessage:
            return "ChatMessage";
        case ChatField::SendMode:
            return "SendMode";
        case ChatField::Chat:
            return "Chat";
        case ChatField::MessageColor:
            return "MessageColor";
        case ChatField::BIsBold:
            return "bIsBold";
        case ChatField::ReceiverTeamId:
            return "ReceiverTeamId";
        case ChatField::ReceiverPlayerID:
            return "ReceiverPlayerID";
        }
        return "Unknown";
    }

    static const char* StructureFunctionName(Obelisk::UE::StructureReflection::StructureFunction function)
    {
        using Obelisk::UE::StructureReflection::StructureFunction;
        switch (function)
        {
        case StructureFunction::VerifyPinCode:
            return "VerifyPinCode";
        case StructureFunction::AllowToggleActivation:
            return "AllowToggleActivation";
        case StructureFunction::CanSeat:
            return "CanSeat";
        case StructureFunction::SetVariant:
            return "SetVariant";
        case StructureFunction::AllowStructureAccess:
            return "AllowStructureAccess";
        case StructureFunction::IsAllowedToDemolish:
            return "IsAllowedToDemolish";
        }
        return "Unknown";
    }

    static const char* StructureFieldName(Obelisk::UE::StructureReflection::StructureField field)
    {
        using Obelisk::UE::StructureReflection::StructureField;
        switch (field)
        {
        case StructureField::ForPC:
            return "ForPC";
        case StructureField::ForCharacter:
            return "forCharacter";
        case StructureField::PinCode:
            return "pinCode";
        case StructureField::VariantIndex:
            return "VariantIndex";
        case StructureField::BForceSet:
            return "bForceSet";
        case StructureField::BForce:
            return "bForce";
        case StructureField::ReturnValue:
            return "ReturnValue";
        }
        return "Unknown";
    }

    static const char* InventoryFunctionName(Obelisk::UE::InventoryReflection::InventoryFunction function)
    {
        using Obelisk::UE::InventoryReflection::InventoryFunction;
        switch (function)
        {
        case InventoryFunction::AllowRemoteAddToInventory:
            return "AllowRemoteAddToInventory";
        case InventoryFunction::CanUse:
            return "CanUse";
        }
        return "Unknown";
    }

    static const char* InventoryFieldName(Obelisk::UE::InventoryReflection::InventoryField field)
    {
        using Obelisk::UE::InventoryReflection::InventoryField;
        switch (field)
        {
        case InventoryField::InventoryComponent:
            return "InventoryComponent";
        case InventoryField::ByPC:
            return "ByPC";
        case InventoryField::BRequestedByPlayer:
            return "bRequestedByPlayer";
        case InventoryField::BIgnoreCooldown:
            return "bIgnoreCooldown";
        case InventoryField::ReturnValue:
            return "ReturnValue";
        }
        return "Unknown";
    }

    static const char* ItemFunctionName(Obelisk::UE::ItemReflection::ItemFunction function)
    {
        using Obelisk::UE::ItemReflection::ItemFunction;
        switch (function)
        {
        case ItemFunction::AllowEquipItem:
            return "AllowEquipItem";
        case ItemFunction::CanRepair:
            return "CanRepair";
        case ItemFunction::CraftBlueprint:
            return "CraftBlueprint";
        case ItemFunction::UseItemOntoItem:
            return "UseItemOntoItem";
        }
        return "Unknown";
    }

    static size_t DispatchReflectedItemReturnEventAfterOriginal(
        bool originalWasCalled,
        int32_t nameIndex,
        void* function,
        void* params)
    {
        if (!originalWasCalled)
            return 0;

        const ProcessEventItemReflection::Gate& gate = GetItemReturnEventGate();
        if (!gate.Enabled())
            return 0;
        if (!ProcessEventItemReflection::IsReflectedItemReturnNameIndex(nameIndex))
            return 0;
        if (Core::ItemReturnEventDispatcher::Get().SubscriptionCount() == 0)
            return 0;

        const uint64_t dispatchLimit = GetItemReturnEventDispatchLimit();
        uint64_t attemptNumber = 0;
        if (!ProcessEventItemReflection::TryReserveObservationBudget(
                s_ReflectedItemReturnAttempts,
                dispatchLimit,
                attemptNumber))
        {
            return 0;
        }

        Obelisk::UE::RuntimeReflection::MemoryReader reader{RuntimeReflectionReader, nullptr};
        ProcessEventItemReflection::Attempt attempt =
            ProcessEventItemReflection::TryIdentifyInvocation(gate, nameIndex, reader, function, params);
        const uint64_t logLimit = GetItemReturnEventLogLimit();
        if (attempt.Status == ProcessEventItemReflection::AttemptStatus::Rejected)
        {
            const uint64_t rejectNumber = ++s_ReflectedItemReturnRejects;
            if (ProcessEventItemReflection::ShouldLogObservation(rejectNumber, logLimit))
            {
                OBELISK_INFO("Reflected item return rejected #{} fname_index={} reason={}",
                             rejectNumber,
                             nameIndex,
                             attempt.Result.Reason);
            }
        }

        ProcessEventItemReflection::CopiedItemObservation observation;
        if (!ProcessEventItemReflection::TryBuildCopiedItemReturnObservationForMatchedAttempt(
                attempt,
                observation))
        {
            return 0;
        }

        std::array<Core::ItemReturnScalarValue, 1> scalarStorage{};
        Core::ItemReturnEventView event;
        if (!ProcessEventItemReflection::TryBuildItemReturnEventView(observation, scalarStorage, event))
            return 0;

        const size_t dispatched = Core::ItemReturnEventDispatcher::Get().Dispatch(event);
        ++s_ReflectedItemReturnDispatches;
        if (ProcessEventItemReflection::ShouldLogObservation(attemptNumber, logLimit))
        {
            OBELISK_INFO("Reflected item return dispatched attempt #{} function={} fname_index={} callbacks={} field_mask=ReturnValue",
                         attemptNumber,
                         ItemFunctionName(observation.Function),
                         observation.FunctionNameIndex,
                         dispatched);
        }
        return dispatched;
    }

    static void TraceReflectedChatInvocation(int32_t nameIndex, void* function, void* params)
    {
        const ProcessEventChatReflection::Gate& gate = GetChatReflectionGate();
        if (!gate.Enabled())
            return;
        const uint64_t limit = GetChatReflectionLogLimit();
        if (!ProcessEventChatReflection::ShouldAttemptObservation(limit))
            return;

        Obelisk::UE::RuntimeReflection::MemoryReader reader{RuntimeReflectionReader, nullptr};
        ProcessEventChatReflection::Attempt attempt =
            ProcessEventChatReflection::TryIdentifyInvocation(gate, nameIndex, reader, function, params);
        if (attempt.Status == ProcessEventChatReflection::AttemptStatus::Disabled ||
            attempt.Status == ProcessEventChatReflection::AttemptStatus::NonChatFunction)
        {
            return;
        }
        if (attempt.Status == ProcessEventChatReflection::AttemptStatus::Rejected)
        {
            const uint64_t rejectNumber = ++s_ReflectedChatRejects;
            if (ProcessEventChatReflection::ShouldLogObservation(rejectNumber, limit))
            {
                OBELISK_INFO("Reflected chat rejected #{} fname_index={} function={} reason={}",
                             rejectNumber, nameIndex, function, attempt.Result.Reason);
            }
            return;
        }

        const Obelisk::UE::ChatReflection::ChatInvocation& invocation = attempt.Invocation;
        const uint64_t callNumber = ++s_ReflectedChatCalls;
        if (!ProcessEventChatReflection::ShouldLogObservation(callNumber, limit))
            return;

        OBELISK_INFO("Reflected chat ProcessEvent #{} function={} fname_index={} params={} fields={} metadata_only={}",
                     callNumber,
                     ChatFunctionName(invocation.Function),
                     invocation.FunctionNameIndex,
                     params,
                     invocation.Fields.size(),
                     invocation.MetadataOnlyCandidate);
        uint8_t sendMode = 0;
        bool sendModeKnown = false;
        if (Obelisk::UE::ChatReflection::TryGetSendMode(invocation, sendMode))
        {
            sendModeKnown = Obelisk::UE::ChatReflection::IsKnownSendMode(sendMode);
            OBELISK_INFO("Reflected chat ServerSendChatMessage send_mode={} send_mode_name={} send_mode_known={}",
                         static_cast<unsigned int>(sendMode),
                         Obelisk::UE::ChatReflection::SendModeName(sendMode),
                         sendModeKnown);
        }
        if (invocation.Function == Obelisk::UE::ChatReflection::ChatFunction::ServerSendChatMessage &&
            sendModeKnown &&
            IsChatReflectionTextLoggingEnabled())
        {
            std::string sanitizedChatText;
            Obelisk::UE::RuntimeReflection::ReadResult textResult =
                ProcessEventChatReflection::TryDecodeUtf32FieldForLog(
                    reader,
                    invocation,
                    Obelisk::UE::ChatReflection::ChatField::ChatMessage,
                    512,
                    sanitizedChatText);
            if (textResult)
            {
                OBELISK_INFO("Reflected chat ServerSendChatMessage text=\"{}\"",
                             sanitizedChatText);
            }
            else
            {
                OBELISK_INFO("Reflected chat ServerSendChatMessage text_decode_status={} reason={}",
                             static_cast<int>(textResult.Status),
                             textResult.Reason);
            }
        }
        for (const auto& field : invocation.Fields)
        {
            OBELISK_INFO("Reflected chat field {} offset=0x{:X} size={} has_range={}",
                         ChatFieldName(field.Field),
                         static_cast<unsigned int>(field.Offset),
                         field.Size,
                         field.Range.Data != nullptr);
        }
    }

    static size_t DispatchReflectedChatMessageEventAfterOriginal(
        bool originalWasCalled,
        int32_t nameIndex,
        void* function,
        void* params)
    {
        if (!originalWasCalled)
            return 0;

        const ProcessEventChatReflection::Gate& gate = GetChatEventProducerGate();
        if (!gate.Enabled())
            return 0;
        if (!ProcessEventChatReflection::IsReflectedChatNameIndex(nameIndex))
            return 0;
        const uint64_t dispatchLimit = GetChatEventDispatchLimit();
        if (!ProcessEventChatReflection::ShouldAttemptObservation(dispatchLimit))
            return 0;
        if (s_ReflectedChatEventDispatches.load(std::memory_order_relaxed) >= dispatchLimit)
            return 0;
        if (Core::ChatEventDispatcher::Get().SubscriptionCount() == 0)
            return 0;

        Obelisk::UE::RuntimeReflection::MemoryReader reader{RuntimeReflectionReader, nullptr};
        ProcessEventChatReflection::Attempt attempt =
            ProcessEventChatReflection::TryIdentifyInvocation(gate, nameIndex, reader, function, params);
        if (attempt.Status != ProcessEventChatReflection::AttemptStatus::Matched)
            return 0;

        ProcessEventChatReflection::CopiedChatMessageEvent event;
        if (!ProcessEventChatReflection::TryBuildCopiedChatMessageEvent(reader, attempt.Invocation, event))
            return 0;

        const uint64_t dispatchNumber =
            s_ReflectedChatEventDispatches.fetch_add(1, std::memory_order_relaxed) + 1;
        if (dispatchNumber > dispatchLimit)
            return 0;

        return Core::ChatEventDispatcher::Get().Dispatch(event.View);
    }

    static bool TryReserveChatRouteObserverSequence(uint64_t limit, uint64_t& sequence)
    {
        sequence = 0;
        if (!ProcessEventChatReflection::ShouldAttemptObservation(limit))
            return false;

        uint64_t current = s_ChatRouteObserverSequences.load(std::memory_order_relaxed);
        while (current < limit)
        {
            if (s_ChatRouteObserverSequences.compare_exchange_weak(
                    current,
                    current + 1,
                    std::memory_order_relaxed,
                    std::memory_order_relaxed))
            {
                sequence = current + 1;
                return true;
            }
        }
        return false;
    }

    static void ObserveChatRouteAfterOriginal(
        bool originalWasCalled,
        int32_t nameIndex,
        void* function,
        void* params)
    {
        if (!originalWasCalled)
            return;

        if (!ProcessEventChatReflection::IsServerSendChatMessageNameIndex(nameIndex))
            return;

        const uint64_t limit = GetChatRouteObserverLimit();
        if (!ProcessEventChatReflection::ShouldAttemptObservation(limit))
            return;

        const ProcessEventChatReflection::Gate& gate = GetChatRouteObserverGate();
        if (!gate.Enabled())
            return;

        Obelisk::UE::RuntimeReflection::MemoryReader reader{RuntimeReflectionReader, nullptr};
        ProcessEventChatReflection::Attempt attempt =
            ProcessEventChatReflection::TryIdentifyInvocation(gate, nameIndex, reader, function, params);
        if (attempt.Status != ProcessEventChatReflection::AttemptStatus::Matched)
            return;

        ProcessEventChatReflection::ChatRouteObservation observation;
        if (!ProcessEventChatReflection::TryBuildChatRouteObservation(attempt.Invocation, observation))
            return;

        uint64_t sequence = 0;
        if (!TryReserveChatRouteObserverSequence(limit, sequence))
            return;

        OBELISK_INFO("ChatRouteObserver event sequence={} send_mode={} send_mode_name={} "
                     "post_original=true delivery_claim=none.",
                     sequence,
                     static_cast<unsigned int>(observation.SendMode),
                     observation.SendModeName);
    }

    static void TraceReflectedStructureInvocation(bool originalWasCalled, int32_t nameIndex, void* function, void* params)
    {
        if (!originalWasCalled)
            return;

        const ProcessEventStructureReflection::Gate& gate = GetStructureReflectionGate();
        if (!gate.Enabled())
            return;
        const uint64_t logLimit = GetStructureReflectionLogLimit();
        const uint64_t dispatchLimit = GetStructureReflectionDispatchLimit();
        if (!ProcessEventStructureReflection::IsReflectedStructureNameIndex(nameIndex))
            return;
        const bool hasDispatchSubscriber =
            Core::StructureEventDispatcher::Get().SubscriptionCount() > 0;
        const bool hasLogBudget =
            ProcessEventStructureReflection::HasObservationBudgetRemaining(s_ReflectedStructureCalls, logLimit);
        const bool hasDispatchBudget =
            ProcessEventStructureReflection::ShouldAttemptDispatchObservation(
                s_ReflectedStructureDispatches,
                dispatchLimit,
                hasDispatchSubscriber ? 1 : 0);
        if (!hasLogBudget && !hasDispatchBudget)
            return;
        uint64_t logObservationNumber = 0;
        const bool logReserved = ProcessEventStructureReflection::TryReserveObservationBudget(
            s_ReflectedStructureCalls, logLimit, logObservationNumber);
        if (!logReserved &&
            !ProcessEventStructureReflection::ShouldAttemptDispatchObservation(
                s_ReflectedStructureDispatches,
                dispatchLimit,
                hasDispatchSubscriber ? 1 : 0))
            return;

        Obelisk::UE::RuntimeReflection::MemoryReader reader{RuntimeReflectionReader, nullptr};
        ProcessEventStructureReflection::Attempt attempt =
            ProcessEventStructureReflection::TryIdentifyInvocation(gate, nameIndex, reader, function, params);
        if (attempt.Status == ProcessEventStructureReflection::AttemptStatus::Disabled ||
            attempt.Status == ProcessEventStructureReflection::AttemptStatus::NonStructureFunction)
        {
            return;
        }
        if (attempt.Status == ProcessEventStructureReflection::AttemptStatus::Rejected)
        {
            ++s_ReflectedStructureRejects;
            if (logReserved && ProcessEventStructureReflection::ShouldLogObservation(logObservationNumber, logLimit))
            {
                OBELISK_INFO("Reflected structure rejected #{} fname_index={} reason={}",
                             logObservationNumber, nameIndex, attempt.Result.Reason);
            }
            return;
        }

        const Obelisk::UE::StructureReflection::StructureInvocation& invocation = attempt.Invocation;
        size_t dispatched = 0;
        uint64_t dispatchObservationNumber = 0;
        ProcessEventStructureReflection::CopiedStructureEvent copiedEvent;
        const bool dispatchReserved = hasDispatchSubscriber &&
            ProcessEventStructureReflection::TryBuildAndReserveDispatchBudgetForMatchedAttempt(
                attempt, s_ReflectedStructureDispatches, dispatchLimit, dispatchObservationNumber, copiedEvent);
        if (dispatchReserved)
        {
            dispatched = ProcessEventStructureReflection::MaybeDispatchCopiedStructureEventAfterOriginal(
                originalWasCalled,
                copiedEvent);
        }

        if (!logReserved || !ProcessEventStructureReflection::ShouldLogObservation(logObservationNumber, logLimit))
            return;

        OBELISK_INFO("Reflected structure ProcessEvent #{} function={} fname_index={} outer_fname_index={} fields={}",
                     logObservationNumber,
                     StructureFunctionName(invocation.Function),
                     invocation.FunctionNameIndex,
                     invocation.OuterNameIndex,
                     invocation.Fields.size());
        if (dispatched > 0)
        {
            OBELISK_INFO("Reflected structure dispatched {} copied internal event callback(s).",
                         dispatched);
        }
        for (const auto& field : invocation.Fields)
        {
            OBELISK_INFO("Reflected structure field {} offset=0x{:X} size={} sensitive={} has_range={}",
                         StructureFieldName(field.Field),
                         static_cast<unsigned int>(field.Offset),
                         field.Size,
                         field.Sensitive,
                         field.Range.Data != nullptr);
        }
    }

    static void TraceReflectedInventoryInvocation(bool originalWasCalled, int32_t nameIndex, void* function, void* params)
    {
        if (!originalWasCalled)
            return;

        const ProcessEventInventoryReflection::Gate& gate = GetInventoryReflectionGate();
        if (!gate.Enabled())
            return;
        const uint64_t logLimit = GetInventoryReflectionLogLimit();
        const uint64_t dispatchLimit = GetInventoryReflectionDispatchLimit();
        if (!ProcessEventInventoryReflection::IsReflectedInventoryNameIndex(nameIndex))
            return;
        const bool hasDispatchSubscriber =
            Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() > 0;
        const bool hasLogBudget =
            ProcessEventInventoryReflection::HasObservationBudgetRemaining(s_ReflectedInventoryCalls, logLimit);
        const bool hasDispatchBudget =
            ProcessEventInventoryReflection::ShouldAttemptDispatchObservation(
                s_ReflectedInventoryDispatches,
                dispatchLimit,
                hasDispatchSubscriber ? 1 : 0);
        if (!hasLogBudget && !hasDispatchBudget)
            return;
        uint64_t observationNumber = 0;
        const bool logReserved = ProcessEventInventoryReflection::TryReserveObservationBudget(
            s_ReflectedInventoryCalls, logLimit, observationNumber);
        if (!logReserved &&
            !ProcessEventInventoryReflection::ShouldAttemptDispatchObservation(
                s_ReflectedInventoryDispatches,
                dispatchLimit,
                hasDispatchSubscriber ? 1 : 0))
            return;

        Obelisk::UE::RuntimeReflection::MemoryReader reader{RuntimeReflectionReader, nullptr};
        ProcessEventInventoryReflection::Attempt attempt =
            ProcessEventInventoryReflection::TryIdentifyInvocation(gate, nameIndex, reader, function, params);
        if (attempt.Status == ProcessEventInventoryReflection::AttemptStatus::Disabled ||
            attempt.Status == ProcessEventInventoryReflection::AttemptStatus::NonInventoryFunction)
        {
            return;
        }
        if (attempt.Status == ProcessEventInventoryReflection::AttemptStatus::Rejected)
        {
            ++s_ReflectedInventoryRejects;
            if (logReserved && ProcessEventInventoryReflection::ShouldLogObservation(observationNumber, logLimit))
            {
                OBELISK_INFO("Reflected inventory rejected #{} fname_index={} reason={}",
                             observationNumber, nameIndex, attempt.Result.Reason);
            }
            return;
        }

        const Obelisk::UE::InventoryReflection::InventoryInvocation& invocation = attempt.Invocation;
        size_t dispatched = 0;
        uint64_t dispatchObservationNumber = 0;
        ProcessEventInventoryReflection::CopiedInventoryPolicyEvent copiedEvent;
        const bool dispatchReserved = hasDispatchSubscriber &&
            ProcessEventInventoryReflection::TryBuildAndReserveDispatchBudgetForMatchedAttempt(
                attempt, s_ReflectedInventoryDispatches, dispatchLimit, dispatchObservationNumber, copiedEvent);
        if (dispatchReserved)
        {
            dispatched = ProcessEventInventoryReflection::MaybeDispatchCopiedInventoryPolicyEventAfterOriginal(
                originalWasCalled,
                copiedEvent);
        }

        if (!logReserved || !ProcessEventInventoryReflection::ShouldLogObservation(observationNumber, logLimit))
            return;

        OBELISK_INFO("Reflected inventory ProcessEvent #{} function={} fname_index={} outer_fname_index={} fields={}",
                     observationNumber,
                     InventoryFunctionName(invocation.Function),
                     invocation.FunctionNameIndex,
                     invocation.OuterNameIndex,
                     invocation.Fields.size());
        if (dispatched > 0)
        {
            OBELISK_INFO("Reflected inventory dispatched {} copied internal event callback(s).",
                         dispatched);
        }
        for (const auto& field : invocation.Fields)
        {
            OBELISK_INFO("Reflected inventory field {} offset=0x{:X} size={} has_range={}",
                         InventoryFieldName(field.Field),
                         static_cast<unsigned int>(field.Offset),
                         field.Size,
                         field.Range.Data != nullptr);
        }
    }

    void ProcessEvent_Detour(void* object, void* function, void* params)
    {
        ActiveProcessEventFrame activeFrame;
        bool originalWasCalled = false;
        OriginalProcessEventCallFlagScope originalCallFlag(originalWasCalled);
        try
        {
            uint64_t callNumber = ++s_ProcessEventCalls;
            TraceProcessEventCall(callNumber, object, function, params);

            auto& eventManager = Core::EventManager::Get();
            const bool hasPreCallbacks = eventManager.HasPreProcessEventCallbacks();
            const bool hasPostCallbacks = eventManager.HasPostProcessEventCallbacks();
            const bool chatReflectionEnabled = IsChatReflectionEnabled();
            const bool chatEventProducerActive = IsChatEventProducerActive();
            const bool chatRouteObserverActive = IsChatRouteObserverActive();
            const bool inventoryObservationActive = IsInventoryObservationActive();
            const bool itemReturnEventProducerActive = IsItemReturnEventProducerActive();
            const bool structureObservationActive = IsStructureObservationActive();
            const bool needsNameIndex =
                hasPreCallbacks || hasPostCallbacks || chatReflectionEnabled || chatEventProducerActive ||
                chatRouteObserverActive || inventoryObservationActive || itemReturnEventProducerActive ||
                structureObservationActive;
            const int32_t nameIndex = needsNameIndex ? GetFunctionNameIndex(function) : -1;

            TraceReflectedChatInvocation(nameIndex, function, params);
            originalWasCalled = DispatchProcessEventCallbacks(
                nameIndex,
                object,
                function,
                params,
                hasPreCallbacks,
                hasPostCallbacks,
                CallOriginalProcessEventFromDetour);

            ObserveChatRouteAfterOriginal(originalWasCalled, nameIndex, function, params);
            DispatchReflectedChatMessageEventAfterOriginal(originalWasCalled, nameIndex, function, params);
            DispatchReflectedItemReturnEventAfterOriginal(originalWasCalled, nameIndex, function, params);
            TraceReflectedInventoryInvocation(originalWasCalled, nameIndex, function, params);
            TraceReflectedStructureInvocation(originalWasCalled, nameIndex, function, params);
        }
        catch (const std::exception& e)
        {
            OBELISK_ERROR("ProcessEvent detour failed internally: {}", e.what());
            TryCallOriginalProcessEventAfterDetourFailure(originalWasCalled, object, function, params);
        }
        catch (...)
        {
            OBELISK_ERROR("ProcessEvent detour failed internally with an unknown exception.");
            TryCallOriginalProcessEventAfterDetourFailure(originalWasCalled, object, function, params);
        }
    }

    void ProcessEventHook::Install()
    {
        {
            std::lock_guard<std::mutex> lock(s_ProcessEventHookMutex);
            if (s_ProcessEventHook.Installed)
            {
                OBELISK_WARN("ProcessEvent hook already installed.");
                return;
            }
        }

        // UObject::ProcessEvent(UFunction*, void*) as seen from UE UObject-derived vtables.
        // The previous 0x1D11CB0 candidate is another virtual method and does not receive gameplay events.
        std::string pattern =
            "55 48 89 E5 41 57 41 56 41 54 53 48 81 EC A0 00 00 00 "
            "49 89 D6 49 89 F4 49 89 FF 64 48 8B 04 25 28 00 00 00";
        const auto moduleInfo = Memory::GetMainModuleInfo();
        if (!moduleInfo.found)
        {
            OBELISK_ERROR("Failed to find ShooterGameServer executable segment. ProcessEvent hook NOT installed.");
            return;
        }

        auto candidates = Memory::FindPatternAll(pattern, 16);
        OBELISK_INFO("ProcessEvent vtable-derived pattern candidates found: {}", candidates.size());
        for (size_t i = 0; i < candidates.size(); ++i)
            OBELISK_INFO("ProcessEvent candidate[{}] = {}", i, candidates[i]);

        void* processEventAddr = nullptr;
        if (candidates.size() == 1 &&
            ValidateProcessEventTarget(candidates.front(), moduleInfo, "pattern"))
        {
            processEventAddr = candidates.front();
        }
        else if (candidates.empty())
        {
            OBELISK_ERROR("ProcessEvent pattern produced no candidates. Hook target must be rediscovered.");
        }
        else if (candidates.size() > 1)
        {
            OBELISK_ERROR("ProcessEvent pattern produced {} candidates. Refusing ambiguous hook target.",
                          candidates.size());
        }

        if (!processEventAddr)
        {
            OBELISK_ERROR("Failed to find ProcessEvent signature. Hook NOT installed.");
            return;
        }

        OBELISK_INFO("Found ProcessEvent at address: {}", processEventAddr);

        bool installed = false;
        void* trampoline = nullptr;
        {
            std::lock_guard<std::mutex> lock(s_ProcessEventHookMutex);
            installed = InstallAbsoluteHook(s_ProcessEventHook, processEventAddr, reinterpret_cast<void*>(&ProcessEvent_Detour));
            trampoline = s_ProcessEventHook.Trampoline;
        }

        if (installed)
        {
            OBELISK_INFO("ProcessEvent absolute x64 hook installed successfully. patch_size={} trampoline={}",
                         kPatchSize, trampoline);
        }
        else
        {
            OBELISK_ERROR("Failed to install ProcessEvent hook!");
        }
    }

    void ProcessEventHook::CallOriginalProcessEvent(void* object, void* function, void* params)
    {
        ProcessEventCallGuard::MarkOriginalCalledFromPublicApi();
        ActiveProcessEventFrame activeFrame;
        ProcessEvent_t original = SnapshotOriginalProcessEvent();
        if (!original)
        {
            if (s_RemovingProcessEventHook.load(std::memory_order_acquire))
                OBELISK_WARN("CallOriginalProcessEvent skipped while ProcessEvent hook removal is in progress.");
            return;
        }

        original(object, function, params);
    }

    bool ProcessEventHook::IsInstalled()
    {
        std::lock_guard<std::mutex> lock(s_ProcessEventHookMutex);
        return s_ProcessEventHook.Installed;
    }

    bool ProcessEventHook::Remove()
    {
        const bool removed = RemoveAbsoluteHook(s_ProcessEventHook);
        if (removed)
            OBELISK_INFO("ProcessEvent hook removed.");
        else
            OBELISK_CRITICAL("ProcessEvent hook removal did not complete; leaving hook state installed for safety.");
        return removed;
    }
}
