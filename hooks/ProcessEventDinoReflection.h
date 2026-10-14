#pragma once

#include "ue/DinoReflection.h"
#include "ue/RuntimeReflection.h"

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <string>

namespace Obelisk::Hooks::ProcessEventDinoReflection
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
        NonDinoFunction,
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
        Obelisk::UE::DinoReflection::DinoInvocation Invocation;
    };

    enum class DinoScalarType
    {
        Bool,
        Int32,
    };

    enum class DinoScalarField
    {
        PassengerSeatIndex,
        BForcePassenger,
        BAllowFlyersAndWaterDinos,
        BSkipLineTrace,
    };

    struct DinoScalarValue
    {
        DinoScalarField Field = DinoScalarField::PassengerSeatIndex;
        DinoScalarType Type = DinoScalarType::Bool;
        bool BoolValue = false;
        int32_t Int32Value = 0;
    };

    struct CopiedDinoScalarObservation
    {
        Obelisk::UE::DinoReflection::DinoFunction Function =
            Obelisk::UE::DinoReflection::DinoFunction::AddPassenger;
        std::array<DinoScalarValue, 4> ScalarStorage{};
        size_t ScalarCount = 0;
    };

    Gate EvaluateGate(const char* enableDinoReflection,
                      bool observerDebugProfileEnabled,
                      bool observerDebugWindowEnabled,
                      bool instanceMarkerEnabled,
                      const char* binarySha256);
    bool IsReflectedDinoNameIndex(int32_t nameIndex);
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
    bool TryBuildCopiedDinoScalarObservation(
        const Obelisk::UE::DinoReflection::DinoInvocation& invocation,
        CopiedDinoScalarObservation& out);
    bool TryBuildCopiedDinoScalarObservationForMatchedAttempt(
        const Attempt& attempt,
        CopiedDinoScalarObservation& out);
}
