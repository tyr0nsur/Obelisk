#pragma once

#include "ue/BuffReflection.h"
#include "ue/RuntimeReflection.h"

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <string>

namespace Obelisk::Hooks::ProcessEventBuffReflection
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
        NonBuffFunction,
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
        Obelisk::UE::BuffReflection::BuffInvocation Invocation;
    };

    struct BuffBoolObservation
    {
        Obelisk::UE::BuffReflection::BuffField Field =
            Obelisk::UE::BuffReflection::BuffField::ReturnValue;
        bool Value = false;
    };

    struct CopiedBuffObservation
    {
        Obelisk::UE::BuffReflection::BuffFunction Function =
            Obelisk::UE::BuffReflection::BuffFunction::AllowPostProcessEffect;
        int32_t FunctionNameIndex = -1;
        int32_t OuterNameIndex = -1;
        std::array<BuffBoolObservation, 2> BoolStorage{};
        size_t BoolCount = 0;
    };

    Gate EvaluateGate(const char* enableBuffReflection,
                      bool observerDebugProfileEnabled,
                      bool observerDebugWindowEnabled,
                      bool instanceMarkerEnabled,
                      const char* binarySha256);
    bool IsReflectedBuffNameIndex(int32_t nameIndex);
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

    Attempt TryObserveInvocation(const Gate& gate,
                                 int32_t nameIndex,
                                 const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                 void* function,
                                 void* params,
                                 std::atomic<uint64_t>& observationCounter,
                                 uint64_t observationLimit,
                                 uint64_t& observationNumber);
    bool TryBuildCopiedBuffObservation(const Obelisk::UE::BuffReflection::BuffInvocation& invocation,
                                       CopiedBuffObservation& out);
    bool TryBuildCopiedBuffObservationForMatchedAttempt(const Attempt& attempt,
                                                        CopiedBuffObservation& out);
}
