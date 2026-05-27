#include "ProcessEventHook.h"
#include "ProcessEventChatReflection.h"
#include "ue/Memory.h"
#include "runtime/Logger.h"
#include "core/EventManager.h"
#include <array>
#include <atomic>
#include <cstdlib>
#include <cstring>
#include <string>
#include <string_view>
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
    }

    static std::atomic<uint64_t> s_ProcessEventCalls{0};
    static std::atomic<uint64_t> s_ReflectedChatCalls{0};
    static std::atomic<uint64_t> s_ReflectedChatRejects{0};

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

    static bool RuntimeReflectionReader(const void* address, size_t size, void*)
    {
        return Memory::IsReadable(const_cast<void*>(address), size);
    }

    static const ProcessEventChatReflection::Gate& GetChatReflectionGate()
    {
        static ProcessEventChatReflection::Gate gate = [] {
            ProcessEventChatReflection::Gate value =
                ProcessEventChatReflection::EvaluateGate(
                    std::getenv("OBELISK_ENABLE_CHAT_REFLECTION"),
                    std::getenv("OBELISK_CHAT_REFLECTION_BINARY_SHA256"));

            switch (value.Status)
            {
            case ProcessEventChatReflection::GateStatus::Disabled:
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

    static uint64_t GetChatReflectionLogLimit()
    {
        static uint64_t limit = [] {
            const char* env = std::getenv("OBELISK_CHAT_REFLECTION_LOG_LIMIT");
            if (!env || env[0] == '\0') return uint64_t{25};
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

    static std::string SanitizeChatTextForLog(std::string_view text)
    {
        constexpr size_t kMaxLoggedBytes = 256;
        std::string sanitized;
        sanitized.reserve(text.size() < kMaxLoggedBytes ? text.size() : kMaxLoggedBytes);
        bool truncated = false;
        for (size_t i = 0; i < text.size();)
        {
            const unsigned char byte = static_cast<unsigned char>(text[i]);
            if (sanitized.size() >= kMaxLoggedBytes)
            {
                truncated = true;
                break;
            }

            if (byte == '"' || byte == '\\')
            {
                if (sanitized.size() + 2 > kMaxLoggedBytes)
                {
                    truncated = true;
                    break;
                }
                sanitized.push_back('\\');
                sanitized.push_back(static_cast<char>(byte));
                ++i;
                continue;
            }
            if (byte < 0x20 || byte == 0x7f)
            {
                const std::string_view replacement = byte == '\n' ? std::string_view{"\\n"} : std::string_view{"?"};
                if (sanitized.size() + replacement.size() > kMaxLoggedBytes)
                {
                    truncated = true;
                    break;
                }
                sanitized.append(replacement);
                ++i;
                continue;
            }

            size_t sequenceLength = 1;
            if ((byte & 0xe0) == 0xc0)
                sequenceLength = 2;
            else if ((byte & 0xf0) == 0xe0)
                sequenceLength = 3;
            else if ((byte & 0xf8) == 0xf0)
                sequenceLength = 4;
            if (sequenceLength > text.size() - i || sanitized.size() + sequenceLength > kMaxLoggedBytes)
            {
                truncated = true;
                break;
            }
            sanitized.append(text.substr(i, sequenceLength));
            i += sequenceLength;
        }
        if (truncated)
            sanitized += "...";
        return sanitized;
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
            std::string chatText;
            Obelisk::UE::RuntimeReflection::ReadResult textResult =
                ProcessEventChatReflection::TryDecodeUtf32Field(
                    reader,
                    invocation,
                    Obelisk::UE::ChatReflection::ChatField::ChatMessage,
                    512,
                    chatText);
            if (textResult)
            {
                OBELISK_INFO("Reflected chat ServerSendChatMessage text=\"{}\"",
                             SanitizeChatTextForLog(chatText));
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

    void ProcessEvent_Detour(void* object, void* function, void* params)
    {
        uint64_t callNumber = ++s_ProcessEventCalls;
        TraceProcessEventCall(callNumber, object, function, params);

        auto& eventManager = Core::EventManager::Get();
        const bool hasPreCallbacks = eventManager.HasPreProcessEventCallbacks();
        const bool hasPostCallbacks = eventManager.HasPostProcessEventCallbacks();
        const bool chatReflectionEnabled = IsChatReflectionEnabled();
        const int32_t nameIndex = (hasPreCallbacks || hasPostCallbacks || chatReflectionEnabled)
            ? GetFunctionNameIndex(function)
            : -1;

        TraceReflectedChatInvocation(nameIndex, function, params);

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
