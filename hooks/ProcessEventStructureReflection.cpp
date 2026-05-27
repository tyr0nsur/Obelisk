#include "ProcessEventStructureReflection.h"

#include <cstring>
#include <string_view>
#include <utility>

namespace Obelisk::Hooks::ProcessEventStructureReflection
{
    Gate EvaluateGate(const char* enableStructureReflection, bool instanceMarkerEnabled, const char* binarySha256)
    {
        if (!enableStructureReflection || std::strcmp(enableStructureReflection, "1") != 0)
            return {};

        if (!instanceMarkerEnabled)
            return {GateStatus::MissingInstanceMarker, {}};

        if (!binarySha256 || binarySha256[0] == '\0')
            return {GateStatus::MissingBinarySha256, {}};

        if (std::string_view(binarySha256) != Obelisk::UE::RuntimeReflection::kSupportedShooterGameServerSha256)
            return {GateStatus::UnsupportedBinarySha256, binarySha256};

        return {GateStatus::Enabled, binarySha256};
    }

    bool IsReflectedStructureNameIndex(int32_t nameIndex)
    {
        return nameIndex == 7541 ||
               nameIndex == 7574 ||
               nameIndex == 7605 ||
               nameIndex == 7620 ||
               nameIndex == 7636 ||
               nameIndex == 8481;
    }

    bool ShouldAttemptObservation(uint64_t limit)
    {
        return limit != 0;
    }

    bool ShouldAttemptNameObservation(int32_t nameIndex, uint64_t limit)
    {
        return ShouldAttemptObservation(limit) && IsReflectedStructureNameIndex(nameIndex);
    }

    bool ShouldLogObservation(uint64_t observationNumber, uint64_t limit)
    {
        return ShouldAttemptObservation(limit) && observationNumber != 0 && observationNumber <= limit;
    }

    bool TryReserveObservationBudget(std::atomic<uint64_t>& counter, uint64_t limit, uint64_t& observationNumber)
    {
        if (!ShouldAttemptObservation(limit))
        {
            observationNumber = 0;
            return false;
        }
        uint64_t current = counter.load();
        while (current < limit)
        {
            if (counter.compare_exchange_weak(current, current + 1))
            {
                observationNumber = current + 1;
                return true;
            }
        }
        observationNumber = 0;
        return false;
    }

    Attempt TryIdentifyInvocation(const Gate& gate,
                                  int32_t nameIndex,
                                  const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                  void* function,
                                  void* params)
    {
        if (!gate.Enabled())
            return {};

        if (!IsReflectedStructureNameIndex(nameIndex))
        {
            return {
                AttemptStatus::NonStructureFunction,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                {},
            };
        }

        Obelisk::UE::RuntimeReflection::ReadOptions options =
            Obelisk::UE::RuntimeReflection::MakeReadOptionsForBinary(gate.BinarySha256, true);

        Obelisk::UE::StructureReflection::StructureInvocation invocation;
        Obelisk::UE::RuntimeReflection::ReadResult result =
            Obelisk::UE::StructureReflection::TryIdentifyStructureInvocation(
                reader, options, function, params, invocation);
        if (!result)
            return {AttemptStatus::Rejected, std::move(result), {}};

        return {AttemptStatus::Matched, std::move(result), std::move(invocation)};
    }
}
