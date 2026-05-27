#pragma once

#include "ue/ChatReflection.h"
#include "ue/RuntimeReflection.h"

#include <cstdint>
#include <string>

namespace Obelisk::Hooks::ProcessEventChatReflection
{
    enum class GateStatus
    {
        Disabled,
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

    Gate EvaluateGate(const char* enableChatReflection, const char* binarySha256);
    bool IsReflectedChatNameIndex(int32_t nameIndex);
    bool ShouldLogObservation(uint64_t observationNumber, uint64_t limit);

    Obelisk::UE::RuntimeReflection::ReadResult TryDecodeUtf32Field(
        const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
        const Obelisk::UE::ChatReflection::ChatInvocation& invocation,
        Obelisk::UE::ChatReflection::ChatField field,
        int32_t maxChars,
        std::string& out);

    Attempt TryIdentifyInvocation(const Gate& gate,
                                  int32_t nameIndex,
                                  const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                  void* function,
                                  void* params);
}
