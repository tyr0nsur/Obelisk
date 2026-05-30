#pragma once

#include "core/ChatEventDispatcher.h"
#include "ue/ChatReflection.h"
#include "ue/RuntimeReflection.h"

#include <cstdint>
#include <string>
#include <string_view>

namespace Obelisk::Hooks::ProcessEventChatReflection
{
    enum class GateStatus
    {
        Disabled,
        MissingInstanceMarker,
        MissingBinarySha256,
        UnsupportedBinarySha256,
        Enabled,
    };

    struct Gate
    {
        GateStatus Status = GateStatus::Disabled;
        std::string BinarySha256;

        bool Enabled() const { return Status == GateStatus::Enabled; }
    };

    enum class AttemptStatus
    {
        Disabled,
        NonChatFunction,
        Rejected,
        Matched,
    };

    struct Attempt
    {
        AttemptStatus Status = AttemptStatus::Disabled;
        Obelisk::UE::RuntimeReflection::ReadResult Result = {
            Obelisk::UE::RuntimeReflection::ReadStatus::Disabled,
            {},
        };
        Obelisk::UE::ChatReflection::ChatInvocation Invocation;
    };

    struct CopiedChatMessageEvent
    {
        Obelisk::Core::ChatMessageView View;
        std::string Message;
    };

    struct ChatRouteObservation
    {
        uint8_t SendMode = 0xff;
        const char* SendModeName = "Unknown";
    };

    Gate EvaluateGate(const char* enableChatReflection, bool instanceMarkerEnabled, const char* binarySha256);
    bool IsServerSendChatMessageNameIndex(int32_t nameIndex);
    bool IsReflectedChatNameIndex(int32_t nameIndex);
    bool ShouldAttemptObservation(uint64_t limit);
    bool ShouldLogObservation(uint64_t observationNumber, uint64_t limit);

    Obelisk::UE::RuntimeReflection::ReadResult TryDecodeUtf32Field(
        const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
        const Obelisk::UE::ChatReflection::ChatInvocation& invocation,
        Obelisk::UE::ChatReflection::ChatField field,
        int32_t maxChars,
        std::string& out);

    Obelisk::UE::RuntimeReflection::ReadResult TryDecodeUtf32FieldForLog(
        const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
        const Obelisk::UE::ChatReflection::ChatInvocation& invocation,
        Obelisk::UE::ChatReflection::ChatField field,
        int32_t maxChars,
        std::string& out,
        size_t maxLoggedBytes = 256);

    void SanitizeTextForLog(std::string_view text, std::string& out, size_t maxLoggedBytes = 256);
    std::string SanitizeTextForLog(std::string_view text, size_t maxLoggedBytes = 256);

    Attempt TryIdentifyInvocation(const Gate& gate,
                                  int32_t nameIndex,
                                  const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                  void* function,
                                  void* params);

    bool TryBuildCopiedChatMessageEvent(
        const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
        const Obelisk::UE::ChatReflection::ChatInvocation& invocation,
        CopiedChatMessageEvent& out,
        int32_t maxChars = 512);

    bool TryBuildChatRouteObservation(
        const Obelisk::UE::ChatReflection::ChatInvocation& invocation,
        ChatRouteObservation& out);
}
