#pragma once

#include "ue/InventoryReflection.h"
#include "ue/RuntimeReflection.h"

#include <atomic>
#include <cstdint>
#include <string>

namespace Obelisk::Hooks::ProcessEventInventoryReflection
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
        NonInventoryFunction,
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
        Obelisk::UE::InventoryReflection::InventoryInvocation Invocation;
    };

    Gate EvaluateGate(const char* enableInventoryReflection, bool instanceMarkerEnabled, const char* binarySha256);
    bool IsReflectedInventoryNameIndex(int32_t nameIndex);
    bool ShouldAttemptObservation(uint64_t limit);
    bool ShouldAttemptNameObservation(int32_t nameIndex, uint64_t limit);
    bool ShouldLogObservation(uint64_t observationNumber, uint64_t limit);
    bool TryReserveObservationBudget(std::atomic<uint64_t>& counter, uint64_t limit, uint64_t& observationNumber);

    Attempt TryIdentifyInvocation(const Gate& gate,
                                  int32_t nameIndex,
                                  const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                  void* function,
                                  void* params);
}
