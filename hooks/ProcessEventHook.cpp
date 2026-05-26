#include "ProcessEventHook.h"
#include "ue/Memory.h"
#include "runtime/Logger.h"
#include "core/EventManager.h"
#include <array>
#include <atomic>
#include <cstdlib>
#include <cstring>
#include <sys/mman.h>
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

        struct AbsoluteHook
        {
            void* Target = nullptr;
            void* Detour = nullptr;
            void* Trampoline = nullptr;
            std::array<uint8_t, kPatchSize> OriginalBytes{};
            bool Installed = false;
        };

        AbsoluteHook s_ProcessEventHook;
    }

    static std::atomic<uint64_t> s_ProcessEventCalls{0};

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

    static bool InstallAbsoluteHook(AbsoluteHook& hook, void* target, void* detour)
    {
        if (!target || !detour)
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
        MakeReadableExecutable(target, kPatchSize);

        hook.Trampoline = trampoline;
        hook.Installed = true;
        return true;
    }

    static void RemoveAbsoluteHook(AbsoluteHook& hook)
    {
        if (!hook.Installed || !hook.Target)
            return;

        if (MakeWritableExecutable(hook.Target, kPatchSize))
        {
            std::memcpy(hook.Target, hook.OriginalBytes.data(), hook.OriginalBytes.size());
            __builtin___clear_cache(reinterpret_cast<char*>(hook.Target),
                                    reinterpret_cast<char*>(static_cast<uint8_t*>(hook.Target) + kPatchSize));
            MakeReadableExecutable(hook.Target, kPatchSize);
        }

        if (hook.Trampoline)
            munmap(hook.Trampoline, kTrampolineSize);

        hook = {};
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

    void ProcessEvent_Detour(void* object, void* function, void* params)
    {
        uint64_t callNumber = ++s_ProcessEventCalls;
        TraceProcessEventCall(callNumber, object, function, params);

        auto& eventManager = Core::EventManager::Get();
        const bool hasPreCallbacks = eventManager.HasPreProcessEventCallbacks();
        const bool hasPostCallbacks = eventManager.HasPostProcessEventCallbacks();
        const int32_t nameIndex = (hasPreCallbacks || hasPostCallbacks) ? GetFunctionNameIndex(function) : -1;

        if (hasPreCallbacks &&
            !eventManager.TriggerPreProcessEvent(nameIndex, object, function, params))
        {
            return;
        }

        // Call original function
        ProcessEvent_t original = reinterpret_cast<ProcessEvent_t>(s_ProcessEventHook.Trampoline);
        if (original)
            original(object, function, params);

        if (hasPostCallbacks)
            eventManager.TriggerPostProcessEvent(nameIndex, object, function, params);
    }

    void ProcessEventHook::Install()
    {
        if (s_ProcessEventHook.Installed)
        {
            OBELISK_WARN("ProcessEvent hook already installed.");
            return;
        }

        // UObject::ProcessEvent(UFunction*, void*) as seen from UE UObject-derived vtables.
        // The previous 0x1D11CB0 candidate is another virtual method and does not receive gameplay events.
        std::string pattern =
            "55 48 89 E5 41 57 41 56 41 54 53 48 81 EC A0 00 00 00 "
            "49 89 D6 49 89 F4 49 89 FF 64 48 8B 04 25 28 00 00 00";
        auto candidates = Memory::FindPatternAll(pattern, 16);
        OBELISK_INFO("ProcessEvent vtable-derived pattern candidates found: {}", candidates.size());
        for (size_t i = 0; i < candidates.size(); ++i)
            OBELISK_INFO("ProcessEvent candidate[{}] = {}", i, candidates[i]);

        void* processEventAddr = candidates.empty() ? nullptr : candidates.front();

        if (!processEventAddr)
        {
            OBELISK_WARN("ProcessEvent pattern not found. Trying current ARK direct offset fallback...");
            auto moduleInfo = Memory::GetMainModuleInfo();
            uintptr_t baseAddress = moduleInfo.imageBase;
            if (baseAddress != 0) {
                // Current ShooterGameServer vtable slot 61 target.
                processEventAddr = reinterpret_cast<void*>(baseAddress + 0x1D34E20);
            }
        }

        if (!processEventAddr)
        {
            OBELISK_ERROR("Failed to find ProcessEvent signature or offset. Hook NOT installed.");
            return;
        }

        OBELISK_INFO("Found ProcessEvent at address: {}", processEventAddr);

        if (InstallAbsoluteHook(s_ProcessEventHook, processEventAddr, reinterpret_cast<void*>(&ProcessEvent_Detour)))
        {
            OBELISK_INFO("ProcessEvent absolute x64 hook installed successfully. patch_size={} trampoline={}",
                         kPatchSize, s_ProcessEventHook.Trampoline);
        }
        else
        {
            OBELISK_ERROR("Failed to install ProcessEvent hook!");
        }
    }

    void ProcessEventHook::CallOriginalProcessEvent(void* object, void* function, void* params)
    {
        if (s_ProcessEventHook.Trampoline)
        {
            ProcessEvent_t original = reinterpret_cast<ProcessEvent_t>(s_ProcessEventHook.Trampoline);
            if (original)
                original(object, function, params);
        }
    }

    bool ProcessEventHook::IsInstalled()
    {
        return s_ProcessEventHook.Installed;
    }

    void ProcessEventHook::Remove()
    {
        RemoveAbsoluteHook(s_ProcessEventHook);
        OBELISK_INFO("ProcessEvent hook removed.");
    }
}
