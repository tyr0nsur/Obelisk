#pragma once

#include "ProcessEventPlayerPrincipalLifecycleObserver.h"
#include "core/PlayerPrincipalRegistry.h"

#include <cstddef>
#include <cstdint>

namespace Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleApplicator
{
    enum class ApplyStatus : uint32_t
    {
        UnsupportedObservation,
        SessionStartCreated,
        SessionStartAllocationFailed,
        SessionStartRejectedNoop,
        SessionEndUnresolvedNoop,
        SessionEndInvalidated,
        SessionEndDuplicateNoop,
        SessionEndStaleNoop,
        RegistryFailure,
    };

    struct ApplyResult
    {
        ApplyStatus Status = ApplyStatus::UnsupportedObservation;
        Obelisk::Core::PlayerPrincipalToken Principal;
        const Obelisk::Core::PlayerPrincipalRegistry* Registry = nullptr;
        Obelisk::Core::PlayerPrincipalInvalidationFlags InvalidationReasons = 0;
        uint64_t EventSequence = 0;
        uint64_t ServerProcessEpoch = 0;
        bool RegistryChanged = false;
        bool PrincipalLive = false;
        bool ValidatedLifecycleEvent = false;
        bool MatchedLogoutCorrelation = false;
        uint64_t ValidationStamp = 0;
    };

    // Internal hook-side metadata only. Values are process-local and are not
    // persisted, logged, or exposed through the public plugin ABI.
    struct ProcessLocalEventContext
    {
        uint64_t EventSequence = 0;
        uint64_t ServerProcessEpoch = 0;
    };

    ApplyResult ApplyLifecycleObservationToRegistry(
        Obelisk::Core::PlayerPrincipalRegistry& registry,
        const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation,
        const Obelisk::Core::PlayerPrincipalToken* correlatedLogoutPrincipal = nullptr,
        const ProcessLocalEventContext* eventContext = nullptr) noexcept;

    bool IsApprovedRuntimeEvidenceLoggableApplyResult(
        const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation,
        const Obelisk::Core::PlayerPrincipalToken* logoutCorrelationPrincipal,
        const ApplyResult& result) noexcept;

    size_t DispatchLifecycleApplyResultToInternalSubscribers(
        const ApplyResult& result,
        const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation) noexcept;
}
