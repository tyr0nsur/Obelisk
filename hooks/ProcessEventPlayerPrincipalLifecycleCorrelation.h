#pragma once

#include "ProcessEventPlayerPrincipalLifecycleApplicator.h"
#include "ProcessEventPlayerPrincipalLifecycleObserver.h"
#include "core/PlayerPrincipalRegistry.h"

namespace Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation
{
    bool TryResolveLogoutCorrelation(
        const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation,
        Obelisk::Core::PlayerPrincipalToken& out) noexcept;

    bool IsFreshResolvedLogoutCorrelation(
        const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation,
        const Obelisk::Core::PlayerPrincipalToken& principal,
        const Obelisk::Core::PlayerPrincipalRegistry& registry,
        const ProcessEventPlayerPrincipalLifecycleApplicator::ProcessLocalEventContext* eventContext) noexcept;

    void BindSessionStartCorrelation(
        Obelisk::Core::PlayerPrincipalRegistry& registry,
        const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation,
        const ProcessEventPlayerPrincipalLifecycleApplicator::ApplyResult& result) noexcept;

    void ClearSessionEndCorrelation(
        const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation,
        const ProcessEventPlayerPrincipalLifecycleApplicator::ApplyResult& result) noexcept;

#ifdef OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_CORRELATION_ENABLE_TEST_HOOKS
    void FailNextBindForTesting() noexcept;
    void FailNextSupersedeForTesting() noexcept;
    void ResetForTesting() noexcept;
#endif
}
