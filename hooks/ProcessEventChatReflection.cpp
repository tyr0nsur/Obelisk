#include "ProcessEventChatReflection.h"

#include <cstring>
#include <string_view>
#include <utility>

namespace Obelisk::Hooks::ProcessEventChatReflection
{
    Gate EvaluateGate(const char* enableChatReflection, const char* binarySha256)
    {
        if (!enableChatReflection || std::strcmp(enableChatReflection, "1") != 0)
            return {};

        if (!binarySha256 || binarySha256[0] == '\0')
            return {GateStatus::MissingBinarySha256, {}};

        if (std::string_view(binarySha256) != Obelisk::UE::RuntimeReflection::kSupportedShooterGameServerSha256)
            return {GateStatus::UnsupportedBinarySha256, binarySha256};

        return {GateStatus::Enabled, binarySha256};
    }

    bool IsReflectedChatNameIndex(int32_t nameIndex)
    {
        return nameIndex == 1865 ||
               nameIndex == 1983 ||
               nameIndex == 1984 ||
               nameIndex == 2697 ||
               nameIndex == 9619 ||
               nameIndex == 9620 ||
               nameIndex == 9621;
    }

    bool ShouldLogObservation(uint64_t observationNumber, uint64_t limit)
    {
        return limit != 0 && observationNumber != 0 && observationNumber <= limit;
    }

    Attempt TryIdentifyInvocation(const Gate& gate,
                                  int32_t nameIndex,
                                  const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                  void* function,
                                  void* params)
    {
        if (!gate.Enabled())
            return {};

        if (!IsReflectedChatNameIndex(nameIndex))
        {
            return {
                AttemptStatus::NonChatFunction,
                Obelisk::UE::RuntimeReflection::ReadResult::Fail(
                    Obelisk::UE::RuntimeReflection::ReadStatus::Implausible,
                    "UFunction FName index is not a supported chat target"),
                {},
            };
        }

        Obelisk::UE::RuntimeReflection::ReadOptions options =
            Obelisk::UE::RuntimeReflection::MakeReadOptionsForBinary(gate.BinarySha256, true);

        Obelisk::UE::ChatReflection::ChatInvocation invocation;
        Obelisk::UE::RuntimeReflection::ReadResult result =
            Obelisk::UE::ChatReflection::TryIdentifyChatInvocation(
                reader, options, function, params, invocation);
        if (!result)
            return {AttemptStatus::Rejected, std::move(result), {}};

        return {AttemptStatus::Matched, std::move(result), std::move(invocation)};
    }
}
