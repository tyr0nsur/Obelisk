#pragma once

#include "core/StructureEventDispatcher.h"
#include "ue/RuntimeReflection.h"
#include "ue/StructureReflection.h"

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <string>

namespace Obelisk::Hooks::ProcessEventStructureReflection
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

    struct CopiedStructureEvent
    {
        Obelisk::Core::StructureEventView View;
        std::array<Obelisk::Core::StructureScalarValue, 6> ScalarStorage{};
        size_t ScalarCount = 0;
    };

    Gate EvaluateGate(const char* enableStructureReflection, bool instanceMarkerEnabled, const char* binarySha256);
    bool IsReflectedStructureNameIndex(int32_t nameIndex);
    bool ShouldAttemptObservation(uint64_t limit);
    bool ShouldAttemptNameObservation(int32_t nameIndex, uint64_t limit);
    bool ShouldLogObservation(uint64_t observationNumber, uint64_t limit);
    bool TryReserveObservationBudget(std::atomic<uint64_t>& counter, uint64_t limit, uint64_t& observationNumber);

    Attempt TryIdentifyInvocation(const Gate& gate,
                                  int32_t nameIndex,
                                  const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                  void* function,
                                  void* params);
    bool TryBuildCopiedStructureEvent(const Obelisk::UE::StructureReflection::StructureInvocation& invocation,
                                      CopiedStructureEvent& out);
}
