#include "ProcessEventPlayerPrincipalLifecycleApplicator.h"
#include "ProcessEventPlayerPrincipalLifecycleCorrelation.h"

#include <array>
#include <limits>

namespace Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleApplicator
{
    namespace
    {
        constexpr int32_t kCheckJoinInProgressNameIndex = 1845;
        constexpr int32_t kHandleNewPlayerNameIndex = 2170;
        constexpr int32_t kOnLogoutNameIndex = 2384;
        constexpr int32_t kShooterGameModeNameIndex = 9755;

        ApplyResult Result(ApplyStatus status)
        {
            return {.Status = status};
        }

        bool IsValidatedLifecycleEventStatus(ApplyStatus status)
        {
            switch (status)
            {
            case ApplyStatus::SessionStartCreated:
            case ApplyStatus::SessionStartRejectedNoop:
            case ApplyStatus::SessionEndInvalidated:
                return true;
            case ApplyStatus::UnsupportedObservation:
            case ApplyStatus::SessionStartAllocationFailed:
            case ApplyStatus::SessionEndUnresolvedNoop:
            case ApplyStatus::SessionEndDuplicateNoop:
            case ApplyStatus::SessionEndStaleNoop:
            case ApplyStatus::RegistryFailure:
                return false;
            }

            return false;
        }

        uint64_t MixValidationStamp(uint64_t value)
        {
            value ^= value >> 30;
            value *= 0xbf58476d1ce4e5b9ULL;
            value ^= value >> 27;
            value *= 0x94d049bb133111ebULL;
            value ^= value >> 31;
            return value;
        }

        uint64_t ValidationStampSalt()
        {
            static auto* salt = new uint64_t(0x706c617965727031ULL);
            return static_cast<uint64_t>(reinterpret_cast<uintptr_t>(salt));
        }

        uint64_t SignedComponent(int32_t value)
        {
            return static_cast<uint64_t>(static_cast<int64_t>(value));
        }

        uint64_t BuildObservationValidationFingerprint(
            const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation)
        {
            uint64_t value = MixValidationStamp(0x6f62736572766531ULL);
            const auto mixComponent = [&value](uint64_t component) {
                value = MixValidationStamp(value ^ (component + 0x9e3779b97f4a7c15ULL));
            };

            mixComponent(static_cast<uint64_t>(observation.Function));
            mixComponent(SignedComponent(observation.FunctionNameIndex));
            mixComponent(SignedComponent(observation.OuterNameIndex));
            mixComponent(static_cast<uint64_t>(observation.Role));
            mixComponent(static_cast<uint64_t>(observation.Action));
            mixComponent(static_cast<uint64_t>(observation.BoolCount));
            for (const auto& boolValue : observation.BoolStorage)
            {
                mixComponent(static_cast<uint64_t>(boolValue.Field));
                mixComponent(boolValue.Value ? 1 : 0);
            }
            mixComponent(static_cast<uint64_t>(observation.RedactedCount));
            for (const auto field : observation.RedactedStorage)
                mixComponent(static_cast<uint64_t>(field));
            for (const uint64_t token : observation.RedactedProcessLocalSubjectTokens)
                mixComponent(token);

            return value == 0 ? 1 : value;
        }

        uint64_t BuildValidationStamp(ApplyStatus status,
                                      uint64_t eventSequence,
                                      uint64_t serverProcessEpoch,
                                      const Obelisk::Core::PlayerPrincipalToken& principal,
                                      const Obelisk::Core::PlayerPrincipalRegistry* registry,
                                      Obelisk::Core::PlayerPrincipalInvalidationFlags invalidationReasons,
                                      bool registryChanged,
                                      bool principalLive,
                                      bool matchedLogoutCorrelation,
                                      const ProcessEventPlayerPrincipalLifecycleObserver::
                                          CopiedLifecycleObservation* observation)
        {
            if (!IsValidatedLifecycleEventStatus(status) ||
                eventSequence == 0 ||
                serverProcessEpoch == 0)
            {
                return 0;
            }
            if (!observation)
                return 0;

            uint64_t value = MixValidationStamp(0x6f62656c69736b31ULL ^ ValidationStampSalt());
            const auto mixComponent = [&value](uint64_t component) {
                value = MixValidationStamp(value ^ (component + 0x9e3779b97f4a7c15ULL));
            };

            mixComponent(static_cast<uint64_t>(status));
            mixComponent(eventSequence);
            mixComponent(serverProcessEpoch);
            mixComponent(principal.Handle);
            mixComponent(principal.Generation);
            mixComponent(principal.RegistryId);
            mixComponent(static_cast<uint64_t>(reinterpret_cast<uintptr_t>(registry)));
            mixComponent(invalidationReasons);
            mixComponent(registryChanged ? 0xbad5eed5eed5eed1ULL : 0x51d15ab1ed000000ULL);
            mixComponent(principalLive ? 0x11fefeedfaceb00cULL : 0x1eaf000000000000ULL);
            mixComponent(matchedLogoutCorrelation ? 0x10a90f0c01e1a7e1ULL : 0xc011e1a7ed000000ULL);
            mixComponent(BuildObservationValidationFingerprint(*observation));
            return value == 0 ? 1 : value;
        }

        uint64_t BuildValidationStamp(ApplyStatus status,
                                      const Obelisk::Core::PlayerPrincipalEventView& event,
                                      const ProcessEventPlayerPrincipalLifecycleObserver::
                                          CopiedLifecycleObservation* observation)
        {
            return BuildValidationStamp(status,
                                        event.EventSequence,
                                        event.ServerProcessEpoch,
                                        {},
                                        nullptr,
                                        0,
                                        false,
                                        false,
                                        false,
                                        observation);
        }

        uint64_t BuildValidationStamp(ApplyStatus status,
                                      const Obelisk::Core::PlayerPrincipalEventView& event,
                                      const Obelisk::Core::PlayerPrincipalToken& principal,
                                      const Obelisk::Core::PlayerPrincipalRegistry* registry,
                                      Obelisk::Core::PlayerPrincipalInvalidationFlags invalidationReasons,
                                      bool registryChanged,
                                      bool principalLive,
                                      bool matchedLogoutCorrelation,
                                      const ProcessEventPlayerPrincipalLifecycleObserver::
                                          CopiedLifecycleObservation* observation)
        {
            return BuildValidationStamp(status,
                                        event.EventSequence,
                                        event.ServerProcessEpoch,
                                        principal,
                                        registry,
                                        invalidationReasons,
                                        registryChanged,
                                        principalLive,
                                        matchedLogoutCorrelation,
                                        observation);
        }

        bool HasValidApplyValidationStamp(
            const ApplyResult& result,
            const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation)
        {
            return result.ValidatedLifecycleEvent &&
                result.ValidationStamp != 0 &&
                result.ValidationStamp == BuildValidationStamp(
                    result.Status,
                    result.EventSequence,
                    result.ServerProcessEpoch,
                    result.Principal,
                    result.Registry,
                    result.InvalidationReasons,
                    result.RegistryChanged,
                    result.PrincipalLive,
                    result.MatchedLogoutCorrelation,
                    &observation);
        }

        ApplyResult Result(ApplyStatus status,
                           const Obelisk::Core::PlayerPrincipalEventView& event,
                           const ProcessEventPlayerPrincipalLifecycleObserver::
                               CopiedLifecycleObservation* observation = nullptr)
        {
            return {
                .Status = status,
                .EventSequence = event.EventSequence,
                .ServerProcessEpoch = event.ServerProcessEpoch,
                .ValidatedLifecycleEvent = IsValidatedLifecycleEventStatus(status),
                .MatchedLogoutCorrelation = false,
                .ValidationStamp = BuildValidationStamp(status, event, observation),
            };
        }

        ApplyResult Result(ApplyStatus status,
                           const Obelisk::Core::PlayerPrincipalEventView& event,
                           const Obelisk::Core::PlayerPrincipalRegistry& registry,
                           const ProcessEventPlayerPrincipalLifecycleObserver::
                               CopiedLifecycleObservation* observation = nullptr)
        {
            return {
                .Status = status,
                .Registry = &registry,
                .EventSequence = event.EventSequence,
                .ServerProcessEpoch = event.ServerProcessEpoch,
                .ValidatedLifecycleEvent = IsValidatedLifecycleEventStatus(status),
                .MatchedLogoutCorrelation = false,
                .ValidationStamp = BuildValidationStamp(status,
                                                        event,
                                                        {},
                                                        &registry,
                                                        0,
                                                        false,
                                                        false,
                                                        false,
                                                        observation),
            };
        }

        ApplyResult Result(ApplyStatus status,
                           const Obelisk::Core::PlayerPrincipalToken& principal,
                           Obelisk::Core::PlayerPrincipalInvalidationFlags reasons,
                           bool registryChanged,
                           bool principalLive,
                           const Obelisk::Core::PlayerPrincipalEventView& event,
                           bool matchedLogoutCorrelation = false,
                           const ProcessEventPlayerPrincipalLifecycleObserver::
                               CopiedLifecycleObservation* observation = nullptr)
        {
            return {
                .Status = status,
                .Principal = principal,
                .InvalidationReasons = reasons,
                .EventSequence = event.EventSequence,
                .ServerProcessEpoch = event.ServerProcessEpoch,
                .RegistryChanged = registryChanged,
                .PrincipalLive = principalLive,
                .ValidatedLifecycleEvent = IsValidatedLifecycleEventStatus(status),
                .MatchedLogoutCorrelation = matchedLogoutCorrelation,
                .ValidationStamp = BuildValidationStamp(status,
                                                        event,
                                                        principal,
                                                        nullptr,
                                                        reasons,
                                                        registryChanged,
                                                        principalLive,
                                                        matchedLogoutCorrelation,
                                                        observation),
            };
        }

        ApplyResult Result(ApplyStatus status,
                           const Obelisk::Core::PlayerPrincipalToken& principal,
                           Obelisk::Core::PlayerPrincipalInvalidationFlags reasons,
                           bool registryChanged,
                           bool principalLive,
                           const Obelisk::Core::PlayerPrincipalEventView& event,
                           const Obelisk::Core::PlayerPrincipalRegistry& registry,
                           bool matchedLogoutCorrelation = false,
                           const ProcessEventPlayerPrincipalLifecycleObserver::
                               CopiedLifecycleObservation* observation = nullptr)
        {
            return {
                .Status = status,
                .Principal = principal,
                .Registry = &registry,
                .InvalidationReasons = reasons,
                .EventSequence = event.EventSequence,
                .ServerProcessEpoch = event.ServerProcessEpoch,
                .RegistryChanged = registryChanged,
                .PrincipalLive = principalLive,
                .ValidatedLifecycleEvent = IsValidatedLifecycleEventStatus(status),
                .MatchedLogoutCorrelation = matchedLogoutCorrelation,
                .ValidationStamp = BuildValidationStamp(status,
                                                        event,
                                                        principal,
                                                        &registry,
                                                        reasons,
                                                        registryChanged,
                                                        principalLive,
                                                        matchedLogoutCorrelation,
                                                        observation),
            };
        }

        void ApplyEventContext(const ProcessLocalEventContext* context,
                               Obelisk::Core::PlayerPrincipalEventView& event)
        {
            if (!context)
                return;

            event.EventSequence = context->EventSequence;
            event.ServerProcessEpoch = context->ServerProcessEpoch;
        }

        bool HasCanonicalSessionStartSubjectTokenShape(
            const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
            return observation.RedactedCount == 3 &&
                observation.RedactedStorage[0] == LifecycleField::NewPlayer &&
                observation.RedactedStorage[1] == LifecycleField::PlayerData &&
                observation.RedactedStorage[2] == LifecycleField::PlayerCharacter &&
                observation.RedactedProcessLocalSubjectTokens[0] != 0 &&
                observation.RedactedProcessLocalSubjectTokens[0] != std::numeric_limits<uint64_t>::max() &&
                observation.RedactedProcessLocalSubjectTokens[1] == 0 &&
                observation.RedactedProcessLocalSubjectTokens[2] == 0;
        }

        bool HasCanonicalSessionEndSubjectTokenShape(
            const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
            return observation.RedactedCount == 1 &&
                observation.RedactedStorage[0] == LifecycleField::Exiting &&
                observation.RedactedProcessLocalSubjectTokens[0] != 0 &&
                observation.RedactedProcessLocalSubjectTokens[0] != std::numeric_limits<uint64_t>::max() &&
                observation.RedactedProcessLocalSubjectTokens[1] == 0 &&
                observation.RedactedProcessLocalSubjectTokens[2] == 0;
        }

        bool HasCanonicalCheckJoinRejectedSubjectTokenShape(
            const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction;
            return observation.Function == LifecycleFunction::CheckJoinInProgressDiagnostic &&
                observation.RedactedCount == 1 &&
                observation.RedactedStorage[0] == LifecycleField::NewPlayer &&
                observation.RedactedProcessLocalSubjectTokens[0] == 0 &&
                observation.RedactedProcessLocalSubjectTokens[1] == 0 &&
                observation.RedactedProcessLocalSubjectTokens[2] == 0;
        }

        bool HasCanonicalBoolFieldOrder(
            const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleField;
            return observation.BoolCount == 2 &&
                observation.BoolStorage[0].Field == LifecycleField::BIsFromLogin &&
                observation.BoolStorage[1].Field == LifecycleField::ReturnValue;
        }

        bool HasCanonicalAcceptedSessionStartObservationShape(
            const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction;
            return observation.Function == LifecycleFunction::HandleNewPlayer &&
                observation.FunctionNameIndex == kHandleNewPlayerNameIndex &&
                observation.OuterNameIndex == kShooterGameModeNameIndex &&
                HasCanonicalSessionStartSubjectTokenShape(observation) &&
                HasCanonicalBoolFieldOrder(observation) &&
                observation.BoolStorage[0].Value &&
                observation.BoolStorage[1].Value;
        }

        bool HasCanonicalRejectedSessionStartObservationShape(
            const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction;
            if (!HasCanonicalBoolFieldOrder(observation))
                return false;

            return observation.Function == LifecycleFunction::CheckJoinInProgressDiagnostic &&
                observation.FunctionNameIndex == kCheckJoinInProgressNameIndex &&
                observation.OuterNameIndex == kShooterGameModeNameIndex &&
                HasCanonicalCheckJoinRejectedSubjectTokenShape(observation) &&
                observation.BoolStorage[0].Value &&
                !observation.BoolStorage[1].Value;
        }

        bool HasCanonicalSessionEndObservationShape(
            const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation)
        {
            using Obelisk::UE::PlayerPrincipalLifecycleReflection::LifecycleFunction;
            return observation.Function == LifecycleFunction::OnLogout &&
                observation.FunctionNameIndex == kOnLogoutNameIndex &&
                observation.OuterNameIndex == kShooterGameModeNameIndex &&
                observation.BoolCount == 0 &&
                HasCanonicalSessionEndSubjectTokenShape(observation);
        }

        bool IsExactLogoutInvalidationReason(Obelisk::Core::PlayerPrincipalInvalidationFlags reasons)
        {
            return reasons == Obelisk::Core::PlayerPrincipalInvalidationFlag(
                                  Obelisk::Core::PlayerPrincipalInvalidationReason::Logout);
        }

        bool IsSamePrincipal(const Obelisk::Core::PlayerPrincipalToken& left,
                             const Obelisk::Core::PlayerPrincipalToken& right)
        {
            return left.Handle == right.Handle &&
                left.Generation == right.Generation &&
                left.RegistryId == right.RegistryId;
        }

        bool RegistryStillValidatesPrincipal(const ApplyResult& result)
        {
            return result.Registry != nullptr &&
                result.Registry->Lookup(result.Principal).Status ==
                    Obelisk::Core::PlayerPrincipalLookupStatus::Valid;
        }

        bool HasMatchedEventContext(const Obelisk::Core::PlayerPrincipalEventView& event)
        {
            return event.EventSequence != 0 && event.ServerProcessEpoch != 0;
        }

        bool RegistryConfirmsExactLogoutInvalidation(const ApplyResult& result)
        {
            if (result.Registry == nullptr || !result.Principal.HasValidShape())
                return false;

            const Obelisk::Core::PlayerPrincipalLookup lookup =
                result.Registry->Lookup(result.Principal);
            return lookup.Status == Obelisk::Core::PlayerPrincipalLookupStatus::Invalidated &&
                IsExactLogoutInvalidationReason(lookup.InvalidationReasons);
        }

        ApplyStatus SessionEndNoopStatusForLookup(
            const Obelisk::Core::PlayerPrincipalLookup& lookup)
        {
            if (lookup.Status == Obelisk::Core::PlayerPrincipalLookupStatus::Invalidated &&
                IsExactLogoutInvalidationReason(lookup.InvalidationReasons))
            {
                return ApplyStatus::SessionEndDuplicateNoop;
            }

            return ApplyStatus::SessionEndStaleNoop;
        }

        bool ShouldDispatch(
            const ApplyResult& result,
            const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation)
        {
            using ProcessEventPlayerPrincipalLifecycleObserver::LifecycleRole;
            using ProcessEventPlayerPrincipalLifecycleObserver::PrincipalAction;

            if (result.EventSequence == 0 || result.ServerProcessEpoch == 0)
                return false;
            if (!HasValidApplyValidationStamp(result, observation))
                return false;

            switch (result.Status)
            {
            case ApplyStatus::SessionStartCreated:
                return result.RegistryChanged &&
                    result.PrincipalLive &&
                    !result.MatchedLogoutCorrelation &&
                    result.Principal.HasValidShape() &&
                    RegistryStillValidatesPrincipal(result) &&
                    result.InvalidationReasons == 0 &&
                    observation.Role == LifecycleRole::SessionStart &&
                    observation.Action == PrincipalAction::CandidateCreated &&
                    HasCanonicalAcceptedSessionStartObservationShape(observation);
            case ApplyStatus::SessionStartRejectedNoop:
                return result.Registry == nullptr &&
                    !result.RegistryChanged &&
                    !result.PrincipalLive &&
                    !result.MatchedLogoutCorrelation &&
                    !result.Principal.HasValidShape() &&
                    result.InvalidationReasons == 0 &&
                    observation.Role == LifecycleRole::SessionStartRejected &&
                    observation.Action == PrincipalAction::None &&
                    HasCanonicalRejectedSessionStartObservationShape(observation);
            case ApplyStatus::SessionEndInvalidated:
                return result.RegistryChanged &&
                    !result.PrincipalLive &&
                    result.MatchedLogoutCorrelation &&
                    result.Principal.HasValidShape() &&
                    RegistryConfirmsExactLogoutInvalidation(result) &&
                    IsExactLogoutInvalidationReason(result.InvalidationReasons) &&
                    observation.Role == LifecycleRole::SessionEnd &&
                    observation.Action == PrincipalAction::CandidateInvalidated &&
                    HasCanonicalSessionEndObservationShape(observation);
            case ApplyStatus::UnsupportedObservation:
            case ApplyStatus::SessionStartAllocationFailed:
            case ApplyStatus::SessionEndUnresolvedNoop:
            case ApplyStatus::SessionEndDuplicateNoop:
            case ApplyStatus::SessionEndStaleNoop:
            case ApplyStatus::RegistryFailure:
                return false;
            }

            return false;
        }
    }

    ApplyResult ApplyLifecycleObservationToRegistry(
        Obelisk::Core::PlayerPrincipalRegistry& registry,
        const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation,
        const Obelisk::Core::PlayerPrincipalToken* correlatedLogoutPrincipal,
        const ProcessLocalEventContext* eventContext) noexcept
    {
        try
        {
            std::array<Obelisk::Core::PlayerPrincipalBoolValue, 2> boolStorage{};
            Obelisk::Core::PlayerPrincipalEventView event;
            if (!ProcessEventPlayerPrincipalLifecycleObserver::TryBuildPlayerPrincipalEventView(
                    observation,
                    boolStorage,
                    event))
            {
                return Result(ApplyStatus::UnsupportedObservation);
            }
            ApplyEventContext(eventContext, event);

            switch (event.Kind)
            {
            case Obelisk::Core::PlayerPrincipalEventKind::SessionStart:
            {
                if (!HasCanonicalSessionStartSubjectTokenShape(observation) ||
                    !HasMatchedEventContext(event))
                {
                    return Result(ApplyStatus::UnsupportedObservation);
                }

                const Obelisk::Core::PlayerPrincipalToken principal = registry.AllocatePrincipal();
                if (!principal.HasValidShape())
                    return Result(ApplyStatus::SessionStartAllocationFailed, event);
                return Result(
                    ApplyStatus::SessionStartCreated,
                    principal,
                    0,
                    true,
                    true,
                    event,
                    registry,
                    false,
                    &observation);
            }
            case Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected:
                if (!HasCanonicalRejectedSessionStartObservationShape(observation) ||
                    !HasMatchedEventContext(event))
                {
                    return Result(ApplyStatus::UnsupportedObservation);
                }
                return Result(ApplyStatus::SessionStartRejectedNoop, event, &observation);
            case Obelisk::Core::PlayerPrincipalEventKind::SessionEnd:
                break;
            }

            if (!HasCanonicalSessionEndSubjectTokenShape(observation))
                return Result(ApplyStatus::UnsupportedObservation);

            if (!correlatedLogoutPrincipal || !correlatedLogoutPrincipal->HasValidShape())
                return Result(ApplyStatus::SessionEndUnresolvedNoop, event);

            if (!ProcessEventPlayerPrincipalLifecycleCorrelation::IsFreshResolvedLogoutCorrelation(
                    observation,
                    *correlatedLogoutPrincipal,
                    registry,
                    eventContext))
            {
                return Result(ApplyStatus::SessionEndUnresolvedNoop, event);
            }

            const Obelisk::Core::PlayerPrincipalLookup lookup =
                registry.Lookup(*correlatedLogoutPrincipal);
            if (!lookup.IsValid())
            {
                return Result(SessionEndNoopStatusForLookup(lookup),
                              *correlatedLogoutPrincipal,
                              lookup.InvalidationReasons,
                              false,
                              false,
                              event,
                              registry);
            }

            const Obelisk::Core::PlayerPrincipalInvalidationFlags logoutReason =
                Obelisk::Core::PlayerPrincipalInvalidationFlag(
                    Obelisk::Core::PlayerPrincipalInvalidationReason::Logout);
            if (!registry.LogoutPrincipal(*correlatedLogoutPrincipal))
            {
                const Obelisk::Core::PlayerPrincipalLookup afterRace =
                    registry.Lookup(*correlatedLogoutPrincipal);
                return Result(SessionEndNoopStatusForLookup(afterRace),
                              *correlatedLogoutPrincipal,
                              afterRace.InvalidationReasons,
                              false,
                              false,
                              event,
                              registry);
            }

            const Obelisk::Core::PlayerPrincipalLookup confirmedLogout =
                registry.Lookup(*correlatedLogoutPrincipal);
            if (confirmedLogout.Status != Obelisk::Core::PlayerPrincipalLookupStatus::Invalidated ||
                !IsExactLogoutInvalidationReason(confirmedLogout.InvalidationReasons))
            {
                return Result(SessionEndNoopStatusForLookup(confirmedLogout),
                              *correlatedLogoutPrincipal,
                              confirmedLogout.InvalidationReasons,
                              false,
                              false,
                              event,
                              registry);
            }

            return Result(ApplyStatus::SessionEndInvalidated,
                          *correlatedLogoutPrincipal,
                          logoutReason,
                          true,
                          false,
                          event,
                          registry,
                          true,
                          &observation);
        }
        catch (...)
        {
            return Result(ApplyStatus::RegistryFailure);
        }
    }

    bool IsApprovedRuntimeEvidenceLoggableApplyResult(
        const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation,
        const Obelisk::Core::PlayerPrincipalToken* logoutCorrelationPrincipal,
        const ApplyResult& result) noexcept
    {
        try
        {
            using ProcessEventPlayerPrincipalLifecycleObserver::LifecycleRole;

            if (!ShouldDispatch(result, observation))
                return false;

            switch (observation.Role)
            {
            case LifecycleRole::SessionStart:
                return result.Status == ApplyStatus::SessionStartCreated;
            case LifecycleRole::SessionStartRejected:
                return result.Status == ApplyStatus::SessionStartRejectedNoop;
            case LifecycleRole::SessionEnd:
                return result.Status == ApplyStatus::SessionEndInvalidated &&
                    result.MatchedLogoutCorrelation &&
                    logoutCorrelationPrincipal != nullptr &&
                    logoutCorrelationPrincipal->HasValidShape() &&
                    IsSamePrincipal(*logoutCorrelationPrincipal, result.Principal);
            }
        }
        catch (...)
        {
        }

        return false;
    }

    size_t DispatchLifecycleApplyResultToInternalSubscribers(
        const ApplyResult& result,
        const ProcessEventPlayerPrincipalLifecycleObserver::CopiedLifecycleObservation& observation) noexcept
    {
        try
        {
            auto& dispatcher = Obelisk::Core::PlayerPrincipalEventDispatcher::Get();
            if (dispatcher.SubscriptionCount() == 0)
                return 0;

            if (!ShouldDispatch(result, observation))
                return 0;

            std::array<Obelisk::Core::PlayerPrincipalBoolValue, 2> boolStorage{};
            Obelisk::Core::PlayerPrincipalEventView event;
            if (!ProcessEventPlayerPrincipalLifecycleObserver::TryBuildPlayerPrincipalEventView(
                    observation,
                    boolStorage,
                    event))
            {
                return 0;
            }

            event.EventSequence = result.EventSequence;
            event.ServerProcessEpoch = result.ServerProcessEpoch;
            return dispatcher.Dispatch(event);
        }
        catch (...)
        {
            return 0;
        }
    }
}
