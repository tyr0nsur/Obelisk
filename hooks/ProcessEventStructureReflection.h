#pragma once

#include "ue/RuntimeReflection.h"
#include "ue/StructureReflection.h"

#include <cstdint>
#include <string>

namespace Obelisk::Hooks::ProcessEventStructureReflection
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
        NonStructureFunction,
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
        Obelisk::UE::StructureReflection::StructureInvocation Invocation;
    };

    Gate EvaluateGate(const char* enableStructureReflection, const char* binarySha256);
    bool IsReflectedStructureNameIndex(int32_t nameIndex);
    bool ShouldAttemptObservation(uint64_t limit);
    bool ShouldLogObservation(uint64_t observationNumber, uint64_t limit);

    Attempt TryIdentifyInvocation(const Gate& gate,
                                  int32_t nameIndex,
                                  const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                  void* function,
                                  void* params);
}
