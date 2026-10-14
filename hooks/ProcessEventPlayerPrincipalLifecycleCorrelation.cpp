#include "ProcessEventPlayerPrincipalLifecycleCorrelation.h"

#include <cstddef>
#include <limits>
#include <mutex>
#include <new>
#include <unordered_map>

namespace Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation
{
    namespace
    {
        using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
        using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction;

        constexpr int32_t kHandleNewPlayerNameIndex = 2170;
        constexpr int32_t kOnLogoutNameIndex = 2384;
        constexpr int32_t kShooterGameModeNameIndex = 9755;

        struct CorrelationState
        {
            std::mutex Mutex;
            struct Entry
            {
                const Obelisk::Core::PlayerPrincipalRegistry* Registry = nullptr;
                Obelisk::Core::PlayerPrincipalToken Principal;
                size_t AmbiguousLogoutRejectBudget = 0;
                uint64_t EventSequence = 0;
                uint64_t ServerProcessEpoch = 0;
            };

            std::unordered_map<uint64_t, Entry> PrincipalsBySubjectToken;
#ifdef OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_CORRELATION_ENABLE_TEST_HOOKS
            bool FailNextBind = false;
            bool FailNextSupersede = false;
#endif
        };

        CorrelationState& GetCorrelationState()
        {
            static auto* state = new CorrelationState();
            return *state;
        }

        bool TryGetCanonicalSessionStartSubjectToken(
            const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation,
            uint64_t& out)
        {
            out = 0;
            if (observation.Role !=
                    ProcessEventPlayerPrincipalLifecycleObserver::LifecycleRole::SessionStart ||
                observation.Action !=
                    ProcessEventPlayerPrincipalLifecycleObserver::PrincipalAction::CandidateCreated ||
                observation.Function != LifecycleFunction::HandleNewPlayer ||
                observation.FunctionNameIndex != kHandleNewPlayerNameIndex ||
                observation.OuterNameIndex != kShooterGameModeNameIndex ||
                observation.BoolCount != 2 ||
                observation.BoolStorage[0].Field != LifecycleField::BIsFromLogin ||
                !observation.BoolStorage[0].Value ||
                observation.BoolStorage[1].Field != LifecycleField::ReturnValue ||
                !observation.BoolStorage[1].Value ||
                observation.RedactedCount != 3 ||
                observation.RedactedStorage[0] != LifecycleField::NewPlayer ||
                observation.RedactedStorage[1] != LifecycleField::PlayerData ||
                observation.RedactedStorage[2] != LifecycleField::PlayerCharacter ||
                observation.RedactedProcessLocalSubjectTokens[0] == 0 ||
                observation.RedactedProcessLocalSubjectTokens[0] == std::numeric_limits<uint64_t>::max() ||
                observation.RedactedProcessLocalSubjectTokens[1] != 0 ||
                observation.RedactedProcessLocalSubjectTokens[2] != 0)
            {
                return false;
            }

            out = observation.RedactedProcessLocalSubjectTokens[0];
            return true;
        }

        bool TryGetCanonicalSessionEndSubjectToken(
            const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation,
            uint64_t& out)
        {
            out = 0;
            if (observation.Role !=
                    ProcessEventPlayerPrincipalLifecycleObserver::LifecycleRole::SessionEnd ||
                observation.Action !=
                    ProcessEventPlayerPrincipalLifecycleObserver::PrincipalAction::CandidateInvalidated ||
                observation.Function != LifecycleFunction::OnLogout ||
                observation.FunctionNameIndex != kOnLogoutNameIndex ||
                observation.OuterNameIndex != kShooterGameModeNameIndex ||
                observation.BoolCount != 0 ||
                observation.RedactedCount != 1 ||
                observation.RedactedStorage[0] != LifecycleField::Exiting ||
                observation.RedactedProcessLocalSubjectTokens[0] == 0 ||
                observation.RedactedProcessLocalSubjectTokens[0] == std::numeric_limits<uint64_t>::max() ||
                observation.RedactedProcessLocalSubjectTokens[1] != 0 ||
                observation.RedactedProcessLocalSubjectTokens[2] != 0)
            {
                return false;
            }

            out = observation.RedactedProcessLocalSubjectTokens[0];
            return true;
        }

        bool HasProofContext(
            const ProcessEventPlayerPrincipalLifecycleApplicator::ApplyResult& result)
        {
            return result.EventSequence != 0 && result.ServerProcessEpoch != 0;
        }

        bool HasProofContext(
            const ProcessEventPlayerPrincipalLifecycleApplicator::ProcessLocalEventContext* context)
        {
            return context != nullptr && context->EventSequence != 0 && context->ServerProcessEpoch != 0;
        }

        bool HasStoredProofContext(const CorrelationState::Entry& entry)
        {
            return entry.EventSequence != 0 && entry.ServerProcessEpoch != 0;
        }

        bool IsConsistentSessionStartCreated(
            const ProcessEventPlayerPrincipalLifecycleApplicator::ApplyResult& result)
        {
            return result.Status ==
                    ProcessEventPlayerPrincipalLifecycleApplicator::ApplyStatus::SessionStartCreated &&
                result.Registry != nullptr &&
                result.Principal.HasValidShape() &&
                result.RegistryChanged &&
                result.PrincipalLive &&
                result.InvalidationReasons == 0 &&
                HasProofContext(result);
        }

        bool IsExactLogoutInvalidationReason(Obelisk::Core::PlayerPrincipalInvalidationFlags reasons)
        {
            return reasons == Obelisk::Core::PlayerPrincipalInvalidationFlag(
                                  Obelisk::Core::PlayerPrincipalInvalidationReason::Logout);
        }

        bool HasConsistentSessionEndInvalidatedClearShape(
            const ProcessEventPlayerPrincipalLifecycleApplicator::ApplyResult& result)
        {
            return result.Status ==
                    ProcessEventPlayerPrincipalLifecycleApplicator::ApplyStatus::SessionEndInvalidated &&
                result.Principal.HasValidShape() &&
                HasProofContext(result) &&
                result.Registry != nullptr &&
                result.RegistryChanged &&
                !result.PrincipalLive &&
                IsExactLogoutInvalidationReason(result.InvalidationReasons);
        }

        bool RegistryConfirmsSessionEndInvalidatedClear(
            const ProcessEventPlayerPrincipalLifecycleApplicator::ApplyResult& result)
        {
            const Obelisk::Core::PlayerPrincipalLookup lookup =
                result.Registry->Lookup(result.Principal);
            return (lookup.Status == Obelisk::Core::PlayerPrincipalLookupStatus::Invalidated &&
                    IsExactLogoutInvalidationReason(lookup.InvalidationReasons)) ||
                lookup.Status == Obelisk::Core::PlayerPrincipalLookupStatus::UnknownHandle;
        }

        bool HasConsistentSessionEndTerminalNoopClearShape(
            const ProcessEventPlayerPrincipalLifecycleApplicator::ApplyResult& result)
        {
            using ProcessEventPlayerPrincipalLifecycleApplicator::ApplyStatus;

            return (result.Status == ApplyStatus::SessionEndDuplicateNoop ||
                    result.Status == ApplyStatus::SessionEndStaleNoop) &&
                result.Principal.HasValidShape() &&
                HasProofContext(result) &&
                result.Registry != nullptr &&
                !result.RegistryChanged &&
                !result.PrincipalLive;
        }

        bool RegistryConfirmsSessionEndTerminalNoopClear(
            const ProcessEventPlayerPrincipalLifecycleApplicator::ApplyResult& result)
        {
            using ProcessEventPlayerPrincipalLifecycleApplicator::ApplyStatus;
            using Obelisk::Core::PlayerPrincipalLookupStatus;

            const Obelisk::Core::PlayerPrincipalLookup lookup =
                result.Registry->Lookup(result.Principal);
            if (result.Status == ApplyStatus::SessionEndDuplicateNoop)
            {
                return lookup.Status == PlayerPrincipalLookupStatus::Invalidated &&
                    IsExactLogoutInvalidationReason(lookup.InvalidationReasons) &&
                    result.InvalidationReasons == lookup.InvalidationReasons;
            }

            switch (lookup.Status)
            {
            case PlayerPrincipalLookupStatus::UnknownHandle:
            case PlayerPrincipalLookupStatus::StaleGeneration:
            case PlayerPrincipalLookupStatus::RegistryMismatch:
                return result.InvalidationReasons == lookup.InvalidationReasons;
            case PlayerPrincipalLookupStatus::Invalidated:
                return !IsExactLogoutInvalidationReason(lookup.InvalidationReasons) &&
                    result.InvalidationReasons == lookup.InvalidationReasons;
            case PlayerPrincipalLookupStatus::Valid:
            case PlayerPrincipalLookupStatus::ZeroHandle:
            case PlayerPrincipalLookupStatus::ZeroGeneration:
            case PlayerPrincipalLookupStatus::ZeroRegistryId:
                return false;
            }

            return false;
        }

        bool IsSamePrincipal(const Obelisk::Core::PlayerPrincipalToken& left,
                             const Obelisk::Core::PlayerPrincipalToken& right)
        {
            return left.Handle == right.Handle &&
                left.Generation == right.Generation &&
                left.RegistryId == right.RegistryId;
        }

        bool SupersedePreviousPrincipalIfLive(
            Obelisk::Core::PlayerPrincipalRegistry& registry,
            const Obelisk::Core::PlayerPrincipalToken& previous,
            const Obelisk::Core::PlayerPrincipalToken& replacement,
            bool& supersededLivePrevious)
        {
            supersededLivePrevious = false;
            if (!previous.HasValidShape() || IsSamePrincipal(previous, replacement))
                return true;

            const Obelisk::Core::PlayerPrincipalLookup lookup = registry.Lookup(previous);
            if (!lookup.IsValid())
                return true;

            if (!registry.InvalidatePrincipal(
                    previous,
                    Obelisk::Core::PlayerPrincipalInvalidationFlag(
                        Obelisk::Core::PlayerPrincipalInvalidationReason::Superseded)))
            {
                return false;
            }

            supersededLivePrevious = true;
            return true;
        }

        void InvalidateStartPrincipal(
            Obelisk::Core::PlayerPrincipalRegistry& registry,
            const Obelisk::Core::PlayerPrincipalToken& principal,
            Obelisk::Core::PlayerPrincipalInvalidationReason reason)
        {
            if (!principal.HasValidShape())
                return;

            (void)registry.InvalidatePrincipal(
                principal,
                Obelisk::Core::PlayerPrincipalInvalidationFlag(reason));
        }

        bool IsStaleOrDuplicateStartBind(
            const CorrelationState::Entry& previous,
            const ProcessEventPlayerPrincipalLifecycleApplicator::ApplyResult& result)
        {
            return previous.ServerProcessEpoch == result.ServerProcessEpoch &&
                previous.EventSequence != 0 &&
                result.EventSequence != 0 &&
                result.EventSequence <= previous.EventSequence;
        }

        bool IsServerEpochDrift(
            const CorrelationState::Entry& previous,
            const ProcessEventPlayerPrincipalLifecycleApplicator::ApplyResult& result)
        {
            return HasStoredProofContext(previous) &&
                HasProofContext(result) &&
                previous.ServerProcessEpoch != result.ServerProcessEpoch;
        }

        bool IsFreshSessionEndClear(
            const CorrelationState::Entry& entry,
            const ProcessEventPlayerPrincipalLifecycleApplicator::ApplyResult& result)
        {
            return HasStoredProofContext(entry) &&
                HasProofContext(result) &&
                entry.ServerProcessEpoch == result.ServerProcessEpoch &&
                result.EventSequence > entry.EventSequence;
        }

        bool IsFreshSessionEndContext(
            const CorrelationState::Entry& entry,
            const ProcessEventPlayerPrincipalLifecycleApplicator::ProcessLocalEventContext* context)
        {
            return HasStoredProofContext(entry) &&
                HasProofContext(context) &&
                entry.ServerProcessEpoch == context->ServerProcessEpoch &&
                context->EventSequence > entry.EventSequence;
        }
    }

    bool TryResolveLogoutCorrelation(
        const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation,
        Obelisk::Core::PlayerPrincipalToken& out) noexcept
    {
        try
        {
            out = {};
            if (observation.Role != ProcessEventPlayerPrincipalLifecycleObserver::LifecycleRole::SessionEnd)
                return false;

            uint64_t subjectToken = 0;
            if (!TryGetCanonicalSessionEndSubjectToken(observation, subjectToken))
                return false;

            auto& state = GetCorrelationState();
            std::lock_guard<std::mutex> lock(state.Mutex);
            auto found = state.PrincipalsBySubjectToken.find(subjectToken);
            if (found == state.PrincipalsBySubjectToken.end() ||
                found->second.Registry == nullptr ||
                !found->second.Principal.HasValidShape() ||
                !HasStoredProofContext(found->second))
            {
                return false;
            }

            out = found->second.Principal;
            return true;
        }
        catch (...)
        {
            out = {};
            return false;
        }
    }

    bool IsFreshResolvedLogoutCorrelation(
        const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation,
        const Obelisk::Core::PlayerPrincipalToken& principal,
        const Obelisk::Core::PlayerPrincipalRegistry& registry,
        const ProcessEventPlayerPrincipalLifecycleApplicator::ProcessLocalEventContext* eventContext) noexcept
    {
        try
        {
            if (observation.Role != ProcessEventPlayerPrincipalLifecycleObserver::LifecycleRole::SessionEnd ||
                !principal.HasValidShape() ||
                !HasProofContext(eventContext))
            {
                return false;
            }

            uint64_t subjectToken = 0;
            if (!TryGetCanonicalSessionEndSubjectToken(observation, subjectToken))
                return false;

            auto& state = GetCorrelationState();
            std::lock_guard<std::mutex> lock(state.Mutex);
            auto found = state.PrincipalsBySubjectToken.find(subjectToken);
            if (found == state.PrincipalsBySubjectToken.end() ||
                found->second.Registry == nullptr ||
                found->second.Registry != &registry ||
                !found->second.Principal.HasValidShape() ||
                !IsSamePrincipal(found->second.Principal, principal) ||
                !IsFreshSessionEndContext(found->second, eventContext))
            {
                return false;
            }

            if (found->second.AmbiguousLogoutRejectBudget != 0)
            {
                --found->second.AmbiguousLogoutRejectBudget;
                return false;
            }

            return true;
        }
        catch (...)
        {
            return false;
        }
    }

    void BindSessionStartCorrelation(
        Obelisk::Core::PlayerPrincipalRegistry& registry,
        const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation,
        const ProcessEventPlayerPrincipalLifecycleApplicator::ApplyResult& result) noexcept
    {
        try
        {
            if (!IsConsistentSessionStartCreated(result) ||
                result.Registry != &registry ||
                observation.Role != ProcessEventPlayerPrincipalLifecycleObserver::LifecycleRole::SessionStart ||
                !registry.Validate(result.Principal))
            {
                return;
            }

            uint64_t subjectToken = 0;
            if (!TryGetCanonicalSessionStartSubjectToken(observation, subjectToken))
                return;

            auto& state = GetCorrelationState();
            std::lock_guard<std::mutex> lock(state.Mutex);
#ifdef OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_CORRELATION_ENABLE_TEST_HOOKS
            if (state.FailNextBind)
            {
                state.FailNextBind = false;
                throw std::bad_alloc();
            }
#endif
            const auto previous = state.PrincipalsBySubjectToken.find(subjectToken);
            if (previous != state.PrincipalsBySubjectToken.end())
            {
                if (IsServerEpochDrift(previous->second, result))
                {
                    if (!IsSamePrincipal(previous->second.Principal, result.Principal))
                    {
                        InvalidateStartPrincipal(
                            registry,
                            result.Principal,
                            Obelisk::Core::PlayerPrincipalInvalidationReason::RuntimeReset);
                    }
                    return;
                }

                if (IsStaleOrDuplicateStartBind(previous->second, result))
                {
                    if (!IsSamePrincipal(previous->second.Principal, result.Principal))
                    {
                        InvalidateStartPrincipal(
                            registry,
                            result.Principal,
                            Obelisk::Core::PlayerPrincipalInvalidationReason::Superseded);
                    }
                    return;
                }
            }

            size_t ambiguousLogoutRejectBudget = previous != state.PrincipalsBySubjectToken.end()
                ? previous->second.AmbiguousLogoutRejectBudget
                : 0;
            bool supersededLivePrevious = false;
            if (previous != state.PrincipalsBySubjectToken.end())
            {
#ifdef OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_CORRELATION_ENABLE_TEST_HOOKS
                if (state.FailNextSupersede)
                {
                    state.FailNextSupersede = false;
                    InvalidateStartPrincipal(
                        registry,
                        result.Principal,
                        Obelisk::Core::PlayerPrincipalInvalidationReason::RuntimeReset);
                    return;
                }
#endif
                if (!SupersedePreviousPrincipalIfLive(registry,
                                                      previous->second.Principal,
                                                      result.Principal,
                                                      supersededLivePrevious))
                {
                    InvalidateStartPrincipal(
                        registry,
                        result.Principal,
                        Obelisk::Core::PlayerPrincipalInvalidationReason::RuntimeReset);
                    return;
                }
            }
            if (supersededLivePrevious &&
                ambiguousLogoutRejectBudget != std::numeric_limits<size_t>::max())
            {
                ++ambiguousLogoutRejectBudget;
            }
            state.PrincipalsBySubjectToken[subjectToken] = {
                .Registry = &registry,
                .Principal = result.Principal,
                .AmbiguousLogoutRejectBudget = ambiguousLogoutRejectBudget,
                .EventSequence = result.EventSequence,
                .ServerProcessEpoch = result.ServerProcessEpoch,
            };
        }
        catch (...)
        {
            try
            {
                if (IsConsistentSessionStartCreated(result))
                {
                    InvalidateStartPrincipal(
                        registry,
                        result.Principal,
                        Obelisk::Core::PlayerPrincipalInvalidationReason::RuntimeReset);
                }
            }
            catch (...)
            {
            }
        }
    }

    void ClearSessionEndCorrelation(
        const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation,
        const ProcessEventPlayerPrincipalLifecycleApplicator::ApplyResult& result) noexcept
    {
        try
        {
            const bool canClearInvalidated =
                HasConsistentSessionEndInvalidatedClearShape(result);
            const bool canClearTerminalNoop =
                HasConsistentSessionEndTerminalNoopClearShape(result);
            if (!canClearInvalidated && !canClearTerminalNoop)
            {
                return;
            }

            uint64_t subjectToken = 0;
            if (!TryGetCanonicalSessionEndSubjectToken(observation, subjectToken))
                return;

            auto& state = GetCorrelationState();
            std::lock_guard<std::mutex> lock(state.Mutex);
            const auto found = state.PrincipalsBySubjectToken.find(subjectToken);
            if (found == state.PrincipalsBySubjectToken.end())
                return;
            if (found->second.Registry != result.Registry)
                return;
            if (!IsSamePrincipal(found->second.Principal, result.Principal))
            {
                return;
            }
            if (!IsFreshSessionEndClear(found->second, result))
                return;
            if (canClearInvalidated)
            {
                if (!RegistryConfirmsSessionEndInvalidatedClear(result))
                    return;
            }
            else if (!RegistryConfirmsSessionEndTerminalNoopClear(result))
            {
                return;
            }
            state.PrincipalsBySubjectToken.erase(found);
        }
        catch (...)
        {
        }
    }

#ifdef OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_CORRELATION_ENABLE_TEST_HOOKS
    void FailNextBindForTesting() noexcept
    {
        auto& state = GetCorrelationState();
        std::lock_guard<std::mutex> lock(state.Mutex);
        state.FailNextBind = true;
    }

    void FailNextSupersedeForTesting() noexcept
    {
        auto& state = GetCorrelationState();
        std::lock_guard<std::mutex> lock(state.Mutex);
        state.FailNextSupersede = true;
    }

    void ResetForTesting() noexcept
    {
        auto& state = GetCorrelationState();
        std::lock_guard<std::mutex> lock(state.Mutex);
        state.PrincipalsBySubjectToken.clear();
        state.FailNextBind = false;
        state.FailNextSupersede = false;
    }
#endif
}
