#pragma once

#include "ue/MissionReflection.h"
#include "ue/RuntimeReflection.h"

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <string>

namespace Obelisk::Hooks::ProcessEventMissionReflection
{
    enum class GateStatus
    {
        Disabled,
        MissingObserverDebugProfile,
        MissingObserverDebugWindow,
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
        BudgetExhausted,
        NonMissionFunction,
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
        Obelisk::UE::MissionReflection::MissionInvocation Invocation;
    };

    struct MissionBoolObservation
    {
        Obelisk::UE::MissionReflection::MissionField Field =
            Obelisk::UE::MissionReflection::MissionField::ReturnValue;
        bool Value = false;
    };

    struct CopiedMissionObservation
    {
        Obelisk::UE::MissionReflection::MissionFunction Function =
            Obelisk::UE::MissionReflection::MissionFunction::GetPlayerUsableItems;
        int32_t FunctionNameIndex = -1;
        int32_t OuterNameIndex = -1;
        std::array<MissionBoolObservation, 2> BoolStorage{};
        size_t BoolCount = 0;
    };

    Gate EvaluateGate(const char* enableMissionReflection,
                      bool observerDebugProfileEnabled,
                      bool observerDebugWindowEnabled,
                      bool instanceMarkerEnabled,
                      const char* binarySha256);
    bool IsReflectedMissionNameIndex(int32_t nameIndex);
    bool ShouldAttemptObservation(uint64_t observationLimit);
    bool ShouldAttemptRuntimeObservation(uint64_t observationLimit);
    bool ShouldAttemptRuntimeObservation(const std::atomic<uint64_t>& observationCounter,
                                         uint64_t observationLimit);
    bool ShouldAttemptNameObservation(int32_t nameIndex, uint64_t observationLimit);
    bool ShouldLogObservation(uint64_t observationNumber, uint64_t observationLimit);
    bool HasObservationBudgetRemaining(const std::atomic<uint64_t>& counter, uint64_t observationLimit);
    bool TryReserveObservationBudget(std::atomic<uint64_t>& counter,
                                     uint64_t observationLimit,
                                     uint64_t& observationNumber);

    Attempt TryIdentifyInvocation(const Gate& gate,
                                  int32_t nameIndex,
                                  const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                  void* function,
                                  void* params);
    Attempt TryObserveInvocation(const Gate& gate,
                                 int32_t nameIndex,
                                 const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                 void* function,
                                 void* params,
                                 std::atomic<uint64_t>& observationCounter,
                                 uint64_t observationLimit,
                                 uint64_t& observationNumber);
    bool TryBuildCopiedMissionObservation(const Obelisk::UE::MissionReflection::MissionInvocation& invocation,
                                          CopiedMissionObservation& out);
    bool TryBuildCopiedMissionBoolObservationForMatchedAttempt(const Attempt& attempt,
                                                               CopiedMissionObservation& out);
}
