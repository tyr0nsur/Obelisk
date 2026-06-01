#pragma once

#include "ue/PlayerPrincipalLifecycleReflection.h"
#include "ue/RuntimeReflection.h"

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <string>

namespace Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleObserver
{
    enum class GateStatus
    {
        Disabled,
        MissingObserverDebugProfile,
        MissingObserverDebugWindow,
        MissingInstanceMarker,
        MissingBinarySha256,
        UnsupportedBinarySha256,
        MissingLogLimit,
        MalformedLogLimit,
        ZeroLogLimit,
        LogLimitTooLarge,
        MissingDispatchLimit,
        MalformedDispatchLimit,
        NonZeroDispatchLimit,
        Enabled,
    };

    struct Gate
    {
        GateStatus Status = GateStatus::Disabled;
        std::string BinarySha256;
        uint64_t LogLimit = 0;
        uint64_t DispatchLimit = 0;

        bool Enabled() const { return Status == GateStatus::Enabled; }
    };

    enum class AttemptStatus
    {
        Disabled,
        BudgetExhausted,
        NonLifecycleFunction,
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
        Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleInvocation Invocation;
    };

    enum class LifecycleRole
    {
        SessionStart,
        SessionEnd,
        SessionStartRejected,
    };

    enum class PrincipalAction
    {
        CandidateCreated,
        CandidateInvalidated,
        None,
    };

    struct LifecycleBoolObservation
    {
        Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField Field =
            Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField::BIsFromLogin;
        bool Value = false;
    };

    struct CopiedLifecycleObservation
    {
        Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction Function =
            Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction::HandleNewPlayer;
        int32_t FunctionNameIndex = -1;
        int32_t OuterNameIndex = -1;
        LifecycleRole Role = LifecycleRole::SessionStart;
        PrincipalAction Action = PrincipalAction::None;
        std::array<LifecycleBoolObservation, 2> BoolStorage{};
        size_t BoolCount = 0;
        std::array<Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField, 3> RedactedStorage{};
        size_t RedactedCount = 0;
    };

    Gate EvaluateGate(const char* enableLifecycleObserver,
                      bool observerDebugProfileEnabled,
                      bool observerDebugWindowEnabled,
                      bool instanceMarkerEnabled,
                      const char* binarySha256,
                      const char* logLimit,
                      const char* dispatchLimit);
    bool IsReflectedLifecycleNameIndex(int32_t nameIndex);
    bool HasObservationBudgetRemaining(const std::atomic<uint64_t>& counter, uint64_t limit);
    bool TryReserveObservationBudget(std::atomic<uint64_t>& counter,
                                     uint64_t limit,
                                     uint64_t& observationNumber);
    bool ShouldLogObservation(uint64_t observationNumber, uint64_t limit);

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
                                 uint64_t& observationNumber);
    bool TryBuildCopiedLifecycleObservation(
        const Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleInvocation& invocation,
        CopiedLifecycleObservation& out);
    bool TryBuildCopiedLifecycleObservationAfterOriginal(bool originalWasCalled,
                                                         const Attempt& attempt,
                                                         CopiedLifecycleObservation& out);

    const char* LifecycleFunctionName(Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction function);
    const char* LifecycleTargetName(Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction function);
    const char* LifecycleFieldName(Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField field);
    const char* LifecycleRoleName(LifecycleRole role);
    const char* PrincipalActionName(PrincipalAction action);
}
