#include "hooks/ProcessEventPlayerPrincipalLifecycleApplicator.h"
#include "hooks/ProcessEventPlayerPrincipalLifecycleCorrelation.h"

#ifndef OBELISK_PLAYER_PRINCIPAL_REGISTRY_ENABLE_TEST_HOOKS
#error PlayerPrincipalLifecycleApplicator tests must explicitly enable registry test hooks.
#endif

#include <atomic>
#include <cstddef>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace
{
    namespace Applicator = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleApplicator;
    namespace Observer = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleObserver;
    namespace Reflection = Obelisk::UE::PlayerPrincipalLifecycleReflection;

    constexpr int32_t kCheckJoinInProgressNameIndex = 1845;
    constexpr int32_t kHandleNewPlayerNameIndex = 2170;
    constexpr int32_t kOnLogoutNameIndex = 2384;
    constexpr int32_t kGameModeK2PostLoginNameIndex = 4943;
    constexpr int32_t kShooterGameModeNameIndex = 9755;

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    void RequireEventContext(const Applicator::ApplyResult& result,
                             uint64_t expectedSequence,
                             uint64_t expectedEpoch,
                             const char* sequenceMessage,
                             const char* epochMessage)
    {
        Require(result.EventSequence == expectedSequence, sequenceMessage);
        Require(result.ServerProcessEpoch == expectedEpoch, epochMessage);
    }

    void RequireNoRegistryPointer(const Applicator::ApplyResult& result,
                                  const char* message)
    {
        Require(result.Registry == nullptr, message);
    }

    void RequireRegistryPointer(const Applicator::ApplyResult& result,
                                const Obelisk::Core::PlayerPrincipalRegistry& registry,
                                const char* message)
    {
        Require(result.Registry == &registry, message);
    }

    struct DispatchCapture
    {
        int Calls = 0;
        Obelisk::Core::PlayerPrincipalEventKind Kind =
            Obelisk::Core::PlayerPrincipalEventKind::SessionStart;
        Obelisk::Core::PlayerPrincipalAction Action =
            Obelisk::Core::PlayerPrincipalAction::None;
        uint64_t EventSequence = 0;
        uint64_t ServerProcessEpoch = 0;
        size_t BoolCount = 0;
    };

    void CaptureDispatch(const Obelisk::Core::PlayerPrincipalEventView& event, void* userData)
    {
        auto* capture = static_cast<DispatchCapture*>(userData);
        ++capture->Calls;
        capture->Kind = event.Kind;
        capture->Action = event.Action;
        capture->EventSequence = event.EventSequence;
        capture->ServerProcessEpoch = event.ServerProcessEpoch;
        capture->BoolCount = event.Bools.size();
    }

    Observer::CopiedLifecycleObservation MakeStartObservation(bool isFromLogin,
                                                              bool returnValue,
                                                              uint64_t subjectToken = 1)
    {
        Observer::CopiedLifecycleObservation observation;
        observation.Function = Reflection::LifecycleFunction::HandleNewPlayer;
        observation.FunctionNameIndex = kHandleNewPlayerNameIndex;
        observation.OuterNameIndex = kShooterGameModeNameIndex;
        observation.Role = (isFromLogin && returnValue)
            ? Observer::LifecycleRole::SessionStart
            : Observer::LifecycleRole::SessionStartRejected;
        observation.Action = (isFromLogin && returnValue)
            ? Observer::PrincipalAction::CandidateCreated
            : Observer::PrincipalAction::None;
        observation.BoolStorage[0] = {
            .Field = Reflection::LifecycleField::BIsFromLogin,
            .Value = isFromLogin,
        };
        observation.BoolStorage[1] = {
            .Field = Reflection::LifecycleField::ReturnValue,
            .Value = returnValue,
        };
        observation.BoolCount = 2;
        observation.RedactedStorage[0] = Reflection::LifecycleField::NewPlayer;
        observation.RedactedStorage[1] = Reflection::LifecycleField::PlayerData;
        observation.RedactedStorage[2] = Reflection::LifecycleField::PlayerCharacter;
        observation.RedactedProcessLocalSubjectTokens[0] = subjectToken;
        observation.RedactedCount = 3;
        return observation;
    }

    Observer::CopiedLifecycleObservation MakeEndObservation(uint64_t subjectToken = 0)
    {
        Observer::CopiedLifecycleObservation observation;
        observation.Function = Reflection::LifecycleFunction::OnLogout;
        observation.FunctionNameIndex = kOnLogoutNameIndex;
        observation.OuterNameIndex = kShooterGameModeNameIndex;
        observation.Role = Observer::LifecycleRole::SessionEnd;
        observation.Action = Observer::PrincipalAction::CandidateInvalidated;
        observation.RedactedStorage[0] = Reflection::LifecycleField::Exiting;
        observation.RedactedProcessLocalSubjectTokens[0] = subjectToken;
        observation.RedactedCount = 1;
        return observation;
    }

    Observer::CopiedLifecycleObservation MakeCheckJoinRejectedObservation()
    {
        Observer::CopiedLifecycleObservation observation;
        observation.Function = Reflection::LifecycleFunction::CheckJoinInProgressDiagnostic;
        observation.FunctionNameIndex = kCheckJoinInProgressNameIndex;
        observation.OuterNameIndex = kShooterGameModeNameIndex;
        observation.Role = Observer::LifecycleRole::SessionStartRejected;
        observation.Action = Observer::PrincipalAction::None;
        observation.BoolStorage[0] = {
            .Field = Reflection::LifecycleField::BIsFromLogin,
            .Value = true,
        };
        observation.BoolStorage[1] = {
            .Field = Reflection::LifecycleField::ReturnValue,
            .Value = false,
        };
        observation.BoolCount = 2;
        observation.RedactedStorage[0] = Reflection::LifecycleField::NewPlayer;
        observation.RedactedCount = 1;
        return observation;
    }

    Observer::CopiedLifecycleObservation MakeDiagnosticObservation()
    {
        Observer::CopiedLifecycleObservation observation;
        observation.Function = Reflection::LifecycleFunction::K2PostLoginDiagnostic;
        observation.FunctionNameIndex = kGameModeK2PostLoginNameIndex;
        observation.OuterNameIndex = kShooterGameModeNameIndex;
        observation.Role = Observer::LifecycleRole::SessionStartRejected;
        observation.Action = Observer::PrincipalAction::None;
        observation.RedactedStorage[0] = Reflection::LifecycleField::NewPlayer;
        observation.RedactedCount = 1;
        return observation;
    }

    Applicator::ProcessLocalEventContext ProofContext(uint64_t sequence,
                                                      uint64_t epoch = 77)
    {
        return {
            .EventSequence = sequence,
            .ServerProcessEpoch = epoch,
        };
    }

    Obelisk::Core::PlayerPrincipalToken RequireResolvedLogoutCorrelation(
        const Observer::CopiedLifecycleObservation& logoutObservation,
        const char* message)
    {
        Obelisk::Core::PlayerPrincipalToken resolved;
        Require(Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation::TryResolveLogoutCorrelation(
                    logoutObservation,
                    resolved),
                message);
        Require(resolved.HasValidShape(), "resolved logout correlation had invalid token shape");
        return resolved;
    }

    Obelisk::Core::PlayerPrincipalToken InvalidateForReconnectAndReactivate(
        Obelisk::Core::PlayerPrincipalRegistry& registry,
        const Obelisk::Core::PlayerPrincipalToken& principal,
        const char* invalidationMessage,
        const char* reactivationMessage)
    {
        Require(registry.InvalidatePrincipal(
                    principal,
                    Obelisk::Core::PlayerPrincipalInvalidationFlag(
                        Obelisk::Core::PlayerPrincipalInvalidationReason::Reconnect)),
                invalidationMessage);
        const Obelisk::Core::PlayerPrincipalToken reactivated =
            registry.ReactivatePrincipal(principal);
        Require(reactivated.HasValidShape(), reactivationMessage);
        return reactivated;
    }

    void TestAcceptedSessionStartAllocatesPrincipal()
    {
        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Applicator::ProcessLocalEventContext context = ProofContext(801);
        const Applicator::ApplyResult result =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            MakeStartObservation(true, true),
                                                            nullptr,
                                                            &context);

        Require(result.Status == Applicator::ApplyStatus::SessionStartCreated,
                "accepted session_start did not create a principal");
        Require(result.RegistryChanged, "accepted session_start did not report registry mutation");
        Require(result.PrincipalLive, "accepted session_start did not report live principal");
        Require(result.Principal.HasValidShape(), "accepted session_start returned invalid principal token");
        RequireRegistryPointer(result,
                               registry,
                               "accepted session_start did not retain registry revalidation pointer");
        RequireEventContext(result,
                            context.EventSequence,
                            context.ServerProcessEpoch,
                            "accepted session_start lost event sequence",
                            "accepted session_start lost server process epoch");
        Require(registry.Validate(result.Principal), "accepted session_start principal did not validate");
        Require(registry.LiveCount() == 1, "accepted session_start live count mismatch");
    }

    void TestRejectedAndDiagnosticObservationsDoNotAllocate()
    {
        Obelisk::Core::PlayerPrincipalRegistry registry;
        Applicator::ApplyResult result =
            Applicator::ApplyLifecycleObservationToRegistry(registry, MakeStartObservation(true, false));

        Require(result.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "login-backed rejected session_start was treated as canonical evidence");
        Require(!result.RegistryChanged, "login-backed rejected session_start changed registry");
        RequireNoRegistryPointer(result,
                                 "login-backed rejected session_start exposed a registry pointer");
        Require(registry.LiveCount() == 0, "login-backed rejected session_start allocated a principal");

        result = Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                                 MakeCheckJoinRejectedObservation());
        Require(result.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "zero-context CheckJoinInProgress rejected session_start did not fail closed");
        Require(!result.RegistryChanged,
                "zero-context CheckJoinInProgress rejected session_start changed registry");
        RequireNoRegistryPointer(result,
                                 "zero-context CheckJoinInProgress rejected session_start exposed a registry pointer");
        Require(registry.LiveCount() == 0,
                "zero-context CheckJoinInProgress rejected session_start allocated a principal");

        const Applicator::ProcessLocalEventContext rejectedContext = ProofContext(806);
        result = Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                                 MakeCheckJoinRejectedObservation(),
                                                                 nullptr,
                                                                 &rejectedContext);
        Require(result.Status == Applicator::ApplyStatus::SessionStartRejectedNoop,
                "CheckJoinInProgress rejected session_start did not no-op");
        Require(!result.RegistryChanged,
                "CheckJoinInProgress rejected session_start changed registry");
        RequireNoRegistryPointer(result,
                                 "CheckJoinInProgress rejected session_start exposed a registry pointer");
        RequireEventContext(result,
                            rejectedContext.EventSequence,
                            rejectedContext.ServerProcessEpoch,
                            "CheckJoinInProgress rejected session_start lost event sequence",
                            "CheckJoinInProgress rejected session_start lost server process epoch");
        Require(registry.LiveCount() == 0,
                "CheckJoinInProgress rejected session_start allocated a principal");

        result = Applicator::ApplyLifecycleObservationToRegistry(
            registry,
            MakeStartObservation(false, true));
        Require(result.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "return-true non-login session_start was treated as a rejected no-op");
        Require(!result.RegistryChanged,
                "return-true non-login session_start changed registry");
        RequireNoRegistryPointer(result,
                                 "return-true non-login session_start exposed a registry pointer");
        Require(registry.LiveCount() == 0,
                "return-true non-login session_start allocated a principal");

        result = Applicator::ApplyLifecycleObservationToRegistry(registry, MakeDiagnosticObservation());
        Require(result.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "diagnostic observation was accepted by registry applicator");
        RequireNoRegistryPointer(result,
                                 "diagnostic observation exposed a registry pointer");
        Require(registry.LiveCount() == 0, "diagnostic observation changed registry");
    }

    void TestMalformedObservationFailsClosed()
    {
        Obelisk::Core::PlayerPrincipalRegistry registry;
        Observer::CopiedLifecycleObservation malformed = MakeStartObservation(true, false);
        malformed.Role = Observer::LifecycleRole::SessionStart;
        malformed.Action = Observer::PrincipalAction::CandidateCreated;

        const Applicator::ApplyResult result =
            Applicator::ApplyLifecycleObservationToRegistry(registry, malformed);
        Require(result.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "malformed accepted-start observation did not fail closed");
        Require(registry.LiveCount() == 0, "malformed observation changed registry");
    }

    void TestSessionEndWithoutCorrelationDoesNotInvalidate()
    {
        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Applicator::ProcessLocalEventContext startContext = ProofContext(802);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            MakeStartObservation(true, true),
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "start fixture did not create principal");

        const Applicator::ApplyResult end =
            Applicator::ApplyLifecycleObservationToRegistry(registry, MakeEndObservation(999));
        Require(end.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "uncorrelated session_end did not no-op");
        Require(!end.RegistryChanged, "uncorrelated session_end changed registry");
        RequireNoRegistryPointer(end,
                                 "uncorrelated session_end exposed a registry pointer");
        Require(!end.Principal.HasValidShape(),
                "uncorrelated session_end returned a principal token");
        Require(end.InvalidationReasons == 0,
                "uncorrelated session_end reported invalidation reasons");
        Require(!end.PrincipalLive,
                "uncorrelated session_end reported a live principal");
        Require(registry.Validate(start.Principal),
                "uncorrelated session_end invalidated a live principal");
        Require(registry.LiveCount() == 1, "uncorrelated session_end live count mismatch");
    }

    void TestSessionEndWithSuppliedPrincipalButNoBoundProofDoesNotInvalidate()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Observer::CopiedLifecycleObservation startObservation =
            MakeStartObservation(true, true, 300);
        const Applicator::ProcessLocalEventContext startContext = ProofContext(900);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            startObservation,
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "unbound-proof start fixture did not create principal");

        const Observer::CopiedLifecycleObservation endObservation = MakeEndObservation(300);
        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation;
        Require(!Correlation::TryResolveLogoutCorrelation(endObservation, resolvedLogoutCorrelation),
                "unbound-proof logout resolved private correlation before bind");

        const Applicator::ProcessLocalEventContext endContext = ProofContext(901);
        const Applicator::ApplyResult end =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            endObservation,
                                                            &start.Principal,
                                                            &endContext);
        Require(end.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "fresh logout with supplied principal but no bound proof did not fail closed");
        Require(!end.RegistryChanged,
                "fresh logout with supplied principal but no bound proof changed registry");
        RequireNoRegistryPointer(end,
                                 "fresh logout with supplied principal but no bound proof exposed a registry pointer");
        Require(!end.Principal.HasValidShape(),
                "fresh logout with supplied principal but no bound proof returned a principal");
        Require(end.InvalidationReasons == 0,
                "fresh logout with supplied principal but no bound proof reported invalidation reasons");
        Require(!end.PrincipalLive,
                "fresh logout with supplied principal but no bound proof reported a live principal");
        Require(registry.Validate(start.Principal),
                "fresh logout with supplied principal but no bound proof invalidated live principal");
        Require(registry.LiveCount() == 1,
                "fresh logout with supplied principal but no bound proof changed live count");
    }

    void TestSessionEndWithCorrelationInvalidates()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Observer::CopiedLifecycleObservation startObservation =
            MakeStartObservation(true, true, 301);
        const Applicator::ProcessLocalEventContext startContext = ProofContext(901);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            startObservation,
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "start fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, startObservation, start);

        const Observer::CopiedLifecycleObservation endObservation = MakeEndObservation(301);
        const Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation =
            RequireResolvedLogoutCorrelation(endObservation,
                                             "correlated session_end did not resolve private proof");
        const Applicator::ProcessLocalEventContext endContext = ProofContext(902);
        const Applicator::ApplyResult end =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            endObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &endContext);
        Require(end.Status == Applicator::ApplyStatus::SessionEndInvalidated,
                "correlated session_end did not invalidate principal");
        Require(end.RegistryChanged, "correlated session_end did not report registry mutation");
        Require(!end.PrincipalLive, "correlated session_end reported live principal");
        RequireRegistryPointer(end,
                               registry,
                               "correlated session_end did not retain registry revalidation pointer");
        Require(!registry.Validate(start.Principal),
                "correlated session_end principal still validated");
        const auto lookup = registry.Lookup(start.Principal);
        Require(lookup.Status == Obelisk::Core::PlayerPrincipalLookupStatus::Invalidated,
                "correlated session_end lookup was not invalidated");
        Require(lookup.InvalidationReasons == Obelisk::Core::PlayerPrincipalInvalidationFlag(
                    Obelisk::Core::PlayerPrincipalInvalidationReason::Logout),
                "correlated session_end did not preserve logout reason");
        Require(registry.LiveCount() == 0, "correlated session_end live count mismatch");
    }

    void TestSessionEndWithZeroPrivateTokenDoesNotUseSuppliedCorrelation()
    {
        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Applicator::ProcessLocalEventContext startContext = ProofContext(803);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            MakeStartObservation(true, true),
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "zero-token logout fixture did not create principal");

        const Applicator::ApplyResult end =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            MakeEndObservation(0),
                                                            &start.Principal);
        Require(end.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "zero-token correlated session_end did not fail closed");
        Require(!end.RegistryChanged, "zero-token correlated session_end changed registry");
        Require(!end.Principal.HasValidShape(),
                "zero-token correlated session_end returned a principal");
        Require(registry.Validate(start.Principal),
                "zero-token correlated session_end invalidated a live principal");
        Require(registry.LiveCount() == 1,
                "zero-token correlated session_end changed live count");
    }

    void TestPrivateSubjectTokenCorrelationInvalidatesMatchingSessionEnd()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Observer::CopiedLifecycleObservation startObservation =
            MakeStartObservation(true, true, 77);
        const Applicator::ProcessLocalEventContext startContext = ProofContext(1001);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            startObservation,
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "private correlation start fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, startObservation, start);

        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation;
        const Observer::CopiedLifecycleObservation endObservation = MakeEndObservation(77);
        Require(Correlation::TryResolveLogoutCorrelation(endObservation, resolvedLogoutCorrelation),
                "private logout correlation did not resolve matching subject token");
        Require(resolvedLogoutCorrelation.Handle == start.Principal.Handle,
                "private logout correlation resolved wrong handle");
        Require(resolvedLogoutCorrelation.Generation == start.Principal.Generation,
                "private logout correlation resolved wrong generation");

        const Applicator::ProcessLocalEventContext endContext = ProofContext(1002);
        const Applicator::ApplyResult end =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            endObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &endContext);
        Correlation::ClearSessionEndCorrelation(endObservation, end);
        Require(end.Status == Applicator::ApplyStatus::SessionEndInvalidated,
                "private correlated session_end did not invalidate principal");
        Require(!registry.Validate(start.Principal),
                "private correlated session_end left principal valid");
        Require(!Correlation::TryResolveLogoutCorrelation(endObservation, resolvedLogoutCorrelation),
                "private logout correlation was not cleared after invalidation");
    }

    void TestPrivateSubjectTokenMismatchDoesNotResolveOrInvalidate()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        constexpr uint64_t kSubjectTokenA = 111;
        constexpr uint64_t kSubjectTokenB = 222;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Observer::CopiedLifecycleObservation tokenAStartObservation =
            MakeStartObservation(true, true, kSubjectTokenA);
        const Applicator::ProcessLocalEventContext tokenAStartContext = ProofContext(1101);
        const Applicator::ApplyResult tokenAStart =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            tokenAStartObservation,
                                                            nullptr,
                                                            &tokenAStartContext);
        Require(tokenAStart.Status == Applicator::ApplyStatus::SessionStartCreated,
                "token A start fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, tokenAStartObservation, tokenAStart);

        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation;
        const Observer::CopiedLifecycleObservation tokenBLogoutObservation =
            MakeEndObservation(kSubjectTokenB);
        Require(!Correlation::TryResolveLogoutCorrelation(tokenBLogoutObservation,
                                                          resolvedLogoutCorrelation),
                "mismatched private subject token resolved an unrelated principal");
        Require(!resolvedLogoutCorrelation.HasValidShape(),
                "mismatched private subject token left a resolved principal");
        const Applicator::ApplyResult mismatchedLogout =
            Applicator::ApplyLifecycleObservationToRegistry(registry, tokenBLogoutObservation);
        Correlation::ClearSessionEndCorrelation(tokenBLogoutObservation, mismatchedLogout);
        Require(mismatchedLogout.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "mismatched private subject logout did not no-op");
        Require(!mismatchedLogout.RegistryChanged,
                "mismatched private subject logout changed registry");
        Require(registry.Validate(tokenAStart.Principal),
                "mismatched private subject logout invalidated token A");
        Require(registry.LiveCount() == 1,
                "mismatched private subject logout changed live count");

        const Observer::CopiedLifecycleObservation tokenBStartObservation =
            MakeStartObservation(true, true, kSubjectTokenB);
        const Applicator::ProcessLocalEventContext tokenBStartContext = ProofContext(1102);
        const Applicator::ApplyResult tokenBStart =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            tokenBStartObservation,
                                                            nullptr,
                                                            &tokenBStartContext);
        Require(tokenBStart.Status == Applicator::ApplyStatus::SessionStartCreated,
                "token B start fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, tokenBStartObservation, tokenBStart);
        Require(registry.Validate(tokenAStart.Principal),
                "token B binding invalidated unrelated token A");
        Require(registry.Validate(tokenBStart.Principal),
                "token B binding did not leave token B live");
        Require(registry.LiveCount() == 2, "token B binding live count mismatch");

        Require(Correlation::TryResolveLogoutCorrelation(tokenBLogoutObservation,
                                                         resolvedLogoutCorrelation),
                "token B private logout correlation did not resolve after token B start");
        Require(resolvedLogoutCorrelation.Handle == tokenBStart.Principal.Handle,
                "token B private logout correlation resolved wrong handle");
        Require(resolvedLogoutCorrelation.Generation == tokenBStart.Principal.Generation,
                "token B private logout correlation resolved wrong generation");
        const Applicator::ProcessLocalEventContext tokenBLogoutContext = ProofContext(1103);
        const Applicator::ApplyResult tokenBLogout =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            tokenBLogoutObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &tokenBLogoutContext);
        Correlation::ClearSessionEndCorrelation(tokenBLogoutObservation, tokenBLogout);
        Require(tokenBLogout.Status == Applicator::ApplyStatus::SessionEndInvalidated,
                "token B private logout did not invalidate token B");
        Require(!registry.Validate(tokenBStart.Principal),
                "token B private logout left token B valid");
        Require(registry.Validate(tokenAStart.Principal),
                "token B private logout invalidated unrelated token A");
        Require(registry.LiveCount() == 1, "token B private logout live count mismatch");

        const Observer::CopiedLifecycleObservation tokenALogoutObservation =
            MakeEndObservation(kSubjectTokenA);
        Require(Correlation::TryResolveLogoutCorrelation(tokenALogoutObservation,
                                                         resolvedLogoutCorrelation),
                "token B private logout cleared unrelated token A correlation");
        Require(resolvedLogoutCorrelation.Handle == tokenAStart.Principal.Handle,
                "remaining token A correlation resolved wrong handle");
        Require(resolvedLogoutCorrelation.Generation == tokenAStart.Principal.Generation,
                "remaining token A correlation resolved wrong generation");
    }

    void TestPrivateSubjectTokenCorrelationFailsClosed()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Observer::CopiedLifecycleObservation zeroTokenStart =
            MakeStartObservation(true, true, 0);
        const Applicator::ApplyResult zeroStart =
            Applicator::ApplyLifecycleObservationToRegistry(registry, zeroTokenStart);
        Require(zeroStart.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "zero-token start fixture did not fail closed");
        Require(!zeroStart.RegistryChanged, "zero-token start changed registry");
        Require(registry.LiveCount() == 0, "zero-token start allocated a principal");
        Correlation::BindSessionStartCorrelation(registry, zeroTokenStart, zeroStart);

        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation;
        Require(!Correlation::TryResolveLogoutCorrelation(MakeEndObservation(0), resolvedLogoutCorrelation),
                "zero private subject token resolved a logout correlation");
        Require(!Correlation::TryResolveLogoutCorrelation(MakeEndObservation(999), resolvedLogoutCorrelation),
                "unknown private subject token resolved a logout correlation");
        Require(!zeroStart.Principal.HasValidShape(),
                "zero-token start returned a principal");

        const Observer::CopiedLifecycleObservation noProofStart =
            MakeStartObservation(true, true, 99);
        const Applicator::ApplyResult noProofResult =
            Applicator::ApplyLifecycleObservationToRegistry(registry, noProofStart);
        Require(noProofResult.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "accepted session_start without proof context did not fail closed");
        Require(!noProofResult.RegistryChanged,
                "accepted session_start without proof context changed registry");
        Require(!noProofResult.Principal.HasValidShape(),
                "accepted session_start without proof context returned a principal");
        Require(registry.LiveCount() == 0,
                "accepted session_start without proof context allocated a principal");
        Correlation::BindSessionStartCorrelation(registry, noProofStart, noProofResult);
        Require(!Correlation::TryResolveLogoutCorrelation(MakeEndObservation(99), resolvedLogoutCorrelation),
                "session_start without proof context bound a private logout correlation");

        const Observer::CopiedLifecycleObservation rejectedStart =
            MakeStartObservation(true, false, 88);
        const Applicator::ProcessLocalEventContext rejectedStartContext = ProofContext(1309);
        const Applicator::ApplyResult rejected =
            Applicator::ApplyLifecycleObservationToRegistry(
                registry,
                rejectedStart,
                nullptr,
                &rejectedStartContext);
        Require(rejected.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "login-backed rejected private correlation start fixture became canonical evidence");
        Correlation::BindSessionStartCorrelation(registry, rejectedStart, rejected);
        Require(!Correlation::TryResolveLogoutCorrelation(MakeEndObservation(88), resolvedLogoutCorrelation),
                "rejected session_start bound a private logout correlation");
    }

    void TestValidateOnlySubjectTokenSentinelFailsClosed()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        constexpr uint64_t kSentinel = std::numeric_limits<uint64_t>::max();

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;

        const Observer::CopiedLifecycleObservation sentinelStartObservation =
            MakeStartObservation(true, true, kSentinel);
        const Applicator::ProcessLocalEventContext sentinelStartContext = ProofContext(1320);
        const Applicator::ApplyResult sentinelStart =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            sentinelStartObservation,
                                                            nullptr,
                                                            &sentinelStartContext);
        Require(sentinelStart.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "validate-only subject token sentinel allocated a principal");
        Require(!sentinelStart.RegistryChanged,
                "validate-only subject token sentinel changed registry on start");
        Require(!sentinelStart.Principal.HasValidShape(),
                "validate-only subject token sentinel returned a start principal");
        Require(registry.LiveCount() == 0,
                "validate-only subject token sentinel changed live count on start");
        Correlation::BindSessionStartCorrelation(registry,
                                                 sentinelStartObservation,
                                                 sentinelStart);

        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation;
        Require(!Correlation::TryResolveLogoutCorrelation(MakeEndObservation(kSentinel),
                                                          resolvedLogoutCorrelation),
                "validate-only subject token sentinel resolved a logout correlation after start");
        Require(!resolvedLogoutCorrelation.HasValidShape(),
                "validate-only subject token sentinel left a resolved principal after start");

        const Observer::CopiedLifecycleObservation validStartObservation =
            MakeStartObservation(true, true, 1321);
        const Applicator::ProcessLocalEventContext validStartContext = ProofContext(1321);
        const Applicator::ApplyResult validStart =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            validStartObservation,
                                                            nullptr,
                                                            &validStartContext);
        Require(validStart.Status == Applicator::ApplyStatus::SessionStartCreated,
                "sentinel logout fixture did not create a valid principal");
        Correlation::BindSessionStartCorrelation(registry,
                                                 validStartObservation,
                                                 validStart);
        Require(registry.Validate(validStart.Principal),
                "sentinel logout fixture principal was not live");

        const Observer::CopiedLifecycleObservation sentinelLogoutObservation =
            MakeEndObservation(kSentinel);
        Require(!Correlation::TryResolveLogoutCorrelation(sentinelLogoutObservation,
                                                          resolvedLogoutCorrelation),
                "validate-only subject token sentinel resolved a logout correlation");
        Require(!resolvedLogoutCorrelation.HasValidShape(),
                "validate-only subject token sentinel left a resolved logout principal");

        const Applicator::ProcessLocalEventContext sentinelLogoutContext = ProofContext(1322);
        const Applicator::ApplyResult sentinelLogout =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            sentinelLogoutObservation,
                                                            &validStart.Principal,
                                                            &sentinelLogoutContext);
        Correlation::ClearSessionEndCorrelation(sentinelLogoutObservation, sentinelLogout);
        Require(sentinelLogout.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "validate-only subject token sentinel logout reached registry correlation");
        Require(!sentinelLogout.RegistryChanged,
                "validate-only subject token sentinel logout changed registry");
        Require(!sentinelLogout.Principal.HasValidShape(),
                "validate-only subject token sentinel logout returned a principal");
        Require(registry.Validate(validStart.Principal),
                "validate-only subject token sentinel logout invalidated a valid principal");
        Require(registry.LiveCount() == 1,
                "validate-only subject token sentinel logout changed live count");
    }

    void TestPrivateSubjectTokenCorrelationAcceptsFreshStartAfterRejectedNoop()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        constexpr uint64_t kSubjectToken = 156;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Observer::CopiedLifecycleObservation rejectedObservation =
            MakeCheckJoinRejectedObservation();
        const Applicator::ProcessLocalEventContext rejectedContext = ProofContext(1310);
        const Applicator::ApplyResult rejected =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            rejectedObservation,
                                                            nullptr,
                                                            &rejectedContext);
        Require(rejected.Status == Applicator::ApplyStatus::SessionStartRejectedNoop,
                "rejected-start fixture did not no-op");
        Correlation::BindSessionStartCorrelation(registry, rejectedObservation, rejected);

        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation;
        Require(!Correlation::TryResolveLogoutCorrelation(MakeEndObservation(kSubjectToken),
                                                          resolvedLogoutCorrelation),
                "rejected-start fixture bound a logout correlation");
        Require(registry.LiveCount() == 0,
                "rejected-start fixture allocated a principal");

        const Observer::CopiedLifecycleObservation acceptedObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext acceptedContext = ProofContext(1311);
        const Applicator::ApplyResult accepted =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            acceptedObservation,
                                                            nullptr,
                                                            &acceptedContext);
        Require(accepted.Status == Applicator::ApplyStatus::SessionStartCreated,
                "accepted start after rejected no-op did not create principal");
        Correlation::BindSessionStartCorrelation(registry, acceptedObservation, accepted);
        Require(registry.Validate(accepted.Principal),
                "accepted start after rejected no-op was not live");
        Require(Correlation::TryResolveLogoutCorrelation(MakeEndObservation(kSubjectToken),
                                                         resolvedLogoutCorrelation),
                "accepted start after rejected no-op did not bind logout correlation");
        Require(resolvedLogoutCorrelation.Handle == accepted.Principal.Handle,
                "accepted start after rejected no-op resolved wrong handle");
        Require(resolvedLogoutCorrelation.Generation == accepted.Principal.Generation,
                "accepted start after rejected no-op resolved wrong generation");
        Require(registry.LiveCount() == 1,
                "accepted start after rejected no-op live count mismatch");
    }

    void TestPrivateSubjectTokenCorrelationBindFailureInvalidatesNewPrincipal()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        constexpr uint64_t kSubjectToken = 89;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Observer::CopiedLifecycleObservation startObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext startContext = ProofContext(1189);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            startObservation,
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "bind-failure fixture did not create a principal");
        Require(registry.Validate(start.Principal),
                "bind-failure fixture principal was not initially live");

        Correlation::FailNextBindForTesting();
        Correlation::BindSessionStartCorrelation(registry, startObservation, start);

        const auto lookup = registry.Lookup(start.Principal);
        Require(lookup.Status == Obelisk::Core::PlayerPrincipalLookupStatus::Invalidated,
                "correlation bind failure left new principal live");
        Require(lookup.InvalidationReasons == Obelisk::Core::PlayerPrincipalInvalidationFlag(
                    Obelisk::Core::PlayerPrincipalInvalidationReason::RuntimeReset),
                "correlation bind failure did not mark runtime-reset invalidation");
        Require(registry.LiveCount() == 0,
                "correlation bind failure left a live uncorrelatable principal");

        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation;
        Require(!Correlation::TryResolveLogoutCorrelation(MakeEndObservation(kSubjectToken),
                                                          resolvedLogoutCorrelation),
                "failed correlation bind left a resolvable logout principal");
        Require(!resolvedLogoutCorrelation.HasValidShape(),
                "failed correlation bind returned a private principal token");
    }

    void TestPrivateSubjectTokenCorrelationSupersedeFailureInvalidatesNewPrincipal()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        constexpr uint64_t kSubjectToken = 90;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Observer::CopiedLifecycleObservation firstObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext firstContext = ProofContext(1190);
        const Applicator::ApplyResult first =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            firstObservation,
                                                            nullptr,
                                                            &firstContext);
        Require(first.Status == Applicator::ApplyStatus::SessionStartCreated,
                "supersede-failure first fixture did not create a principal");
        Correlation::BindSessionStartCorrelation(registry, firstObservation, first);
        Require(registry.Validate(first.Principal),
                "supersede-failure first principal was not live after bind");

        const Observer::CopiedLifecycleObservation secondObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext secondContext = ProofContext(1191);
        const Applicator::ApplyResult second =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            secondObservation,
                                                            nullptr,
                                                            &secondContext);
        Require(second.Status == Applicator::ApplyStatus::SessionStartCreated,
                "supersede-failure second fixture did not create a principal");
        Require(registry.Validate(second.Principal),
                "supersede-failure second principal was not initially live");

        Correlation::FailNextSupersedeForTesting();
        Correlation::BindSessionStartCorrelation(registry, secondObservation, second);

        Require(registry.Validate(first.Principal),
                "supersede failure invalidated the already-bound principal");
        const auto secondLookup = registry.Lookup(second.Principal);
        Require(secondLookup.Status == Obelisk::Core::PlayerPrincipalLookupStatus::Invalidated,
                "supersede failure left new principal live");
        Require(secondLookup.InvalidationReasons == Obelisk::Core::PlayerPrincipalInvalidationFlag(
                    Obelisk::Core::PlayerPrincipalInvalidationReason::RuntimeReset),
                "supersede failure did not mark new principal runtime-reset");
        Require(registry.LiveCount() == 1,
                "supersede failure left an uncorrelatable live principal");

        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation;
        Require(Correlation::TryResolveLogoutCorrelation(MakeEndObservation(kSubjectToken),
                                                         resolvedLogoutCorrelation),
                "supersede failure removed the previous valid correlation");
        Require(resolvedLogoutCorrelation.Handle == first.Principal.Handle,
                "supersede failure rebound logout correlation to failed principal");
        Require(resolvedLogoutCorrelation.Generation == first.Principal.Generation,
                "supersede failure changed logout correlation generation");
    }

    void TestPrivateSubjectTokenCorrelationSupersedesPreviousPrincipal()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Observer::CopiedLifecycleObservation firstObservation =
            MakeStartObservation(true, true, 101);
        const Applicator::ProcessLocalEventContext firstContext = ProofContext(1201);
        const Applicator::ApplyResult first =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            firstObservation,
                                                            nullptr,
                                                            &firstContext);
        Require(first.Status == Applicator::ApplyStatus::SessionStartCreated,
                "first supersede fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, firstObservation, first);

        const Observer::CopiedLifecycleObservation secondObservation =
            MakeStartObservation(true, true, 101);
        const Applicator::ProcessLocalEventContext secondContext = ProofContext(1202);
        const Applicator::ApplyResult second =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            secondObservation,
                                                            nullptr,
                                                            &secondContext);
        Require(second.Status == Applicator::ApplyStatus::SessionStartCreated,
                "second supersede fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, secondObservation, second);

        Require(!registry.Validate(first.Principal),
                "same private subject token did not supersede previous principal");
        const auto firstLookup = registry.Lookup(first.Principal);
        Require(firstLookup.Status == Obelisk::Core::PlayerPrincipalLookupStatus::Invalidated,
                "superseded private subject principal was not invalidated");
        Require(firstLookup.InvalidationReasons == Obelisk::Core::PlayerPrincipalInvalidationFlag(
                    Obelisk::Core::PlayerPrincipalInvalidationReason::Superseded),
                "superseded private subject principal did not preserve reason");

        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation;
        const Observer::CopiedLifecycleObservation logoutObservation =
            MakeEndObservation(101);
        Require(Correlation::TryResolveLogoutCorrelation(logoutObservation, resolvedLogoutCorrelation),
                "ambiguous post-supersede logout did not resolve tentative current principal");
        Require(resolvedLogoutCorrelation.Handle == second.Principal.Handle,
                "ambiguous post-supersede logout resolved wrong tentative handle");
        Require(resolvedLogoutCorrelation.Generation == second.Principal.Generation,
                "ambiguous post-supersede logout resolved wrong tentative generation");
        const Applicator::ProcessLocalEventContext ambiguousLogoutContext = ProofContext(1203);
        const Applicator::ApplyResult ambiguousLogout =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            logoutObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &ambiguousLogoutContext);
        Require(ambiguousLogout.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "ambiguous post-supersede logout did not fail closed as unresolved");
        Require(!ambiguousLogout.RegistryChanged,
                "ambiguous post-supersede logout changed registry");
        Require(registry.Validate(second.Principal),
                "ambiguous post-supersede logout invalidated current principal");

        Require(Correlation::TryResolveLogoutCorrelation(logoutObservation, resolvedLogoutCorrelation),
                "post-supersede private subject token did not resolve after ambiguous logout rejection");
        Require(resolvedLogoutCorrelation.Handle == second.Principal.Handle,
                "superseded private subject token resolved stale handle");
        Require(registry.Validate(second.Principal),
                "superseded private subject token invalidated current principal");

        const Applicator::ApplyResult staleClearAttempt{
            .Status = Applicator::ApplyStatus::SessionEndDuplicateNoop,
            .Principal = first.Principal,
            .EventSequence = 1204,
            .ServerProcessEpoch = 77,
        };
        Correlation::ClearSessionEndCorrelation(logoutObservation, staleClearAttempt);
        Require(Correlation::TryResolveLogoutCorrelation(logoutObservation, resolvedLogoutCorrelation),
                "stale superseded clear removed current private subject correlation");
        Require(resolvedLogoutCorrelation.Handle == second.Principal.Handle,
                "stale superseded clear changed the current correlation handle");
        Require(resolvedLogoutCorrelation.Generation == second.Principal.Generation,
                "stale superseded clear changed the current correlation generation");
    }

    void TestPrivateSubjectTokenCorrelationRejectsOutOfOrderStartBind()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        constexpr uint64_t kSubjectToken = 151;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;

        const Observer::CopiedLifecycleObservation olderObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext olderContext = ProofContext(1231);
        const Applicator::ApplyResult older =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            olderObservation,
                                                            nullptr,
                                                            &olderContext);
        Require(older.Status == Applicator::ApplyStatus::SessionStartCreated,
                "older out-of-order fixture did not create principal");

        const Observer::CopiedLifecycleObservation newerObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext newerContext = ProofContext(1232);
        const Applicator::ApplyResult newer =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            newerObservation,
                                                            nullptr,
                                                            &newerContext);
        Require(newer.Status == Applicator::ApplyStatus::SessionStartCreated,
                "newer out-of-order fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, newerObservation, newer);

        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation;
        const Observer::CopiedLifecycleObservation logoutObservation =
            MakeEndObservation(kSubjectToken);
        Require(Correlation::TryResolveLogoutCorrelation(logoutObservation,
                                                         resolvedLogoutCorrelation),
                "newer out-of-order correlation did not resolve before stale bind");
        Require(resolvedLogoutCorrelation.Handle == newer.Principal.Handle,
                "newer out-of-order correlation resolved wrong handle before stale bind");
        Require(resolvedLogoutCorrelation.Generation == newer.Principal.Generation,
                "newer out-of-order correlation resolved wrong generation before stale bind");

        Correlation::BindSessionStartCorrelation(registry, olderObservation, older);
        Require(registry.Validate(newer.Principal),
                "late older start bind superseded the newer live principal");
        Require(!registry.Validate(older.Principal),
                "late older start bind left stale principal live");
        const auto olderLookup = registry.Lookup(older.Principal);
        Require(olderLookup.Status == Obelisk::Core::PlayerPrincipalLookupStatus::Invalidated,
                "late older start principal was not invalidated");
        Require(olderLookup.InvalidationReasons == Obelisk::Core::PlayerPrincipalInvalidationFlag(
                    Obelisk::Core::PlayerPrincipalInvalidationReason::Superseded),
                "late older start principal did not preserve superseded reason");
        Require(registry.LiveCount() == 1,
                "late older start bind did not leave exactly one live principal");

        Require(Correlation::TryResolveLogoutCorrelation(logoutObservation,
                                                         resolvedLogoutCorrelation),
                "late older start bind removed the newer correlation");
        Require(resolvedLogoutCorrelation.Handle == newer.Principal.Handle,
                "late older start bind rewound correlation handle");
        Require(resolvedLogoutCorrelation.Generation == newer.Principal.Generation,
                "late older start bind rewound correlation generation");

        const Applicator::ProcessLocalEventContext logoutContext = ProofContext(1233);
        const Applicator::ApplyResult logout =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            logoutObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &logoutContext);
        Correlation::ClearSessionEndCorrelation(logoutObservation, logout);
        Require(logout.Status == Applicator::ApplyStatus::SessionEndInvalidated,
                "newer principal logout after stale bind did not invalidate");
        Require(!registry.Validate(newer.Principal),
                "newer principal stayed live after correlated logout");
        Require(registry.LiveCount() == 0,
                "out-of-order stale bind fixture left live principals after logout");
        Require(!Correlation::TryResolveLogoutCorrelation(logoutObservation,
                                                          resolvedLogoutCorrelation),
                "out-of-order stale bind correlation was not cleared after logout");
    }

    void TestPrivateSubjectTokenCorrelationRejectsEqualSequenceStartBind()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        constexpr uint64_t kSubjectToken = 152;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;

        const Observer::CopiedLifecycleObservation firstObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext firstContext = ProofContext(1241);
        const Applicator::ApplyResult first =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            firstObservation,
                                                            nullptr,
                                                            &firstContext);
        Require(first.Status == Applicator::ApplyStatus::SessionStartCreated,
                "first equal-sequence fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, firstObservation, first);

        const Observer::CopiedLifecycleObservation duplicateObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext duplicateContext = ProofContext(1241);
        const Applicator::ApplyResult duplicate =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            duplicateObservation,
                                                            nullptr,
                                                            &duplicateContext);
        Require(duplicate.Status == Applicator::ApplyStatus::SessionStartCreated,
                "duplicate equal-sequence fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, duplicateObservation, duplicate);

        Require(registry.Validate(first.Principal),
                "equal-sequence start bind invalidated the original principal");
        Require(!registry.Validate(duplicate.Principal),
                "equal-sequence start bind left duplicate principal live");
        const auto duplicateLookup = registry.Lookup(duplicate.Principal);
        Require(duplicateLookup.Status == Obelisk::Core::PlayerPrincipalLookupStatus::Invalidated,
                "equal-sequence duplicate principal was not invalidated");
        Require(duplicateLookup.InvalidationReasons == Obelisk::Core::PlayerPrincipalInvalidationFlag(
                    Obelisk::Core::PlayerPrincipalInvalidationReason::Superseded),
                "equal-sequence duplicate principal did not preserve superseded reason");

        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation;
        Require(Correlation::TryResolveLogoutCorrelation(MakeEndObservation(kSubjectToken),
                                                         resolvedLogoutCorrelation),
                "equal-sequence duplicate bind removed the original correlation");
        Require(resolvedLogoutCorrelation.Handle == first.Principal.Handle,
                "equal-sequence duplicate bind changed correlation handle");
        Require(resolvedLogoutCorrelation.Generation == first.Principal.Generation,
                "equal-sequence duplicate bind changed correlation generation");
        Require(registry.LiveCount() == 1,
                "equal-sequence duplicate bind did not leave exactly one live principal");
    }

    void TestPrivateSubjectTokenCorrelationRejectsServerEpochDriftStartBind()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        constexpr uint64_t kSubjectToken = 153;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;

        const Observer::CopiedLifecycleObservation firstObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext firstContext = ProofContext(1261, 77);
        const Applicator::ApplyResult first =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            firstObservation,
                                                            nullptr,
                                                            &firstContext);
        Require(first.Status == Applicator::ApplyStatus::SessionStartCreated,
                "first epoch-drift fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, firstObservation, first);

        const Observer::CopiedLifecycleObservation driftObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext driftContext = ProofContext(1262, 88);
        const Applicator::ApplyResult drift =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            driftObservation,
                                                            nullptr,
                                                            &driftContext);
        Require(drift.Status == Applicator::ApplyStatus::SessionStartCreated,
                "epoch-drift fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, driftObservation, drift);

        Require(registry.Validate(first.Principal),
                "epoch-drift start bind invalidated the original principal");
        Require(!registry.Validate(drift.Principal),
                "epoch-drift start bind left drift principal live");
        const auto driftLookup = registry.Lookup(drift.Principal);
        Require(driftLookup.Status == Obelisk::Core::PlayerPrincipalLookupStatus::Invalidated,
                "epoch-drift principal was not invalidated");
        Require(driftLookup.InvalidationReasons == Obelisk::Core::PlayerPrincipalInvalidationFlag(
                    Obelisk::Core::PlayerPrincipalInvalidationReason::RuntimeReset),
                "epoch-drift principal did not preserve runtime-reset reason");

        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation;
        Require(Correlation::TryResolveLogoutCorrelation(MakeEndObservation(kSubjectToken),
                                                         resolvedLogoutCorrelation),
                "epoch-drift bind removed the original correlation");
        Require(resolvedLogoutCorrelation.Handle == first.Principal.Handle,
                "epoch-drift bind changed correlation handle");
        Require(resolvedLogoutCorrelation.Generation == first.Principal.Generation,
                "epoch-drift bind changed correlation generation");
        Require(registry.LiveCount() == 1,
                "epoch-drift bind did not leave exactly one live principal");
    }

    void TestPrivateSubjectTokenCorrelationRejectsEqualSequenceServerEpochDriftStartBind()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        constexpr uint64_t kSubjectToken = 157;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;

        const Observer::CopiedLifecycleObservation firstObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext firstContext = ProofContext(1263, 77);
        const Applicator::ApplyResult first =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            firstObservation,
                                                            nullptr,
                                                            &firstContext);
        Require(first.Status == Applicator::ApplyStatus::SessionStartCreated,
                "first equal-sequence epoch-drift fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, firstObservation, first);

        const Observer::CopiedLifecycleObservation driftObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext driftContext = ProofContext(1263, 88);
        const Applicator::ApplyResult drift =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            driftObservation,
                                                            nullptr,
                                                            &driftContext);
        Require(drift.Status == Applicator::ApplyStatus::SessionStartCreated,
                "equal-sequence epoch-drift fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, driftObservation, drift);

        Require(registry.Validate(first.Principal),
                "equal-sequence epoch-drift start bind invalidated the original principal");
        Require(!registry.Validate(drift.Principal),
                "equal-sequence epoch-drift start bind left drift principal live");
        const auto driftLookup = registry.Lookup(drift.Principal);
        Require(driftLookup.Status == Obelisk::Core::PlayerPrincipalLookupStatus::Invalidated,
                "equal-sequence epoch-drift principal was not invalidated");
        Require(driftLookup.InvalidationReasons == Obelisk::Core::PlayerPrincipalInvalidationFlag(
                    Obelisk::Core::PlayerPrincipalInvalidationReason::RuntimeReset),
                "equal-sequence epoch-drift principal did not preserve runtime-reset reason");

        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation;
        Require(Correlation::TryResolveLogoutCorrelation(MakeEndObservation(kSubjectToken),
                                                         resolvedLogoutCorrelation),
                "equal-sequence epoch-drift bind removed the original correlation");
        Require(resolvedLogoutCorrelation.Handle == first.Principal.Handle,
                "equal-sequence epoch-drift bind changed correlation handle");
        Require(resolvedLogoutCorrelation.Generation == first.Principal.Generation,
                "equal-sequence epoch-drift bind changed correlation generation");
        Require(registry.LiveCount() == 1,
                "equal-sequence epoch-drift bind did not leave exactly one live principal");
    }

    void TestPrivateSubjectTokenCorrelationClearRequiresFreshSameEpochLogout()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        constexpr uint64_t kSubjectToken = 154;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Observer::CopiedLifecycleObservation startObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext startContext = ProofContext(1271, 77);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            startObservation,
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "fresh-clear fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, startObservation, start);

        const Observer::CopiedLifecycleObservation logoutObservation =
            MakeEndObservation(kSubjectToken);
        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation;
        Require(Correlation::TryResolveLogoutCorrelation(logoutObservation,
                                                         resolvedLogoutCorrelation),
                "fresh-clear fixture did not resolve before stale clear attempts");

        const Applicator::ApplyResult olderClear{
            .Status = Applicator::ApplyStatus::SessionEndDuplicateNoop,
            .Principal = start.Principal,
            .EventSequence = 1270,
            .ServerProcessEpoch = 77,
        };
        Correlation::ClearSessionEndCorrelation(logoutObservation, olderClear);
        Require(Correlation::TryResolveLogoutCorrelation(logoutObservation,
                                                         resolvedLogoutCorrelation),
                "older logout clear removed a live correlation");

        const Applicator::ApplyResult equalClear{
            .Status = Applicator::ApplyStatus::SessionEndDuplicateNoop,
            .Principal = start.Principal,
            .EventSequence = 1271,
            .ServerProcessEpoch = 77,
        };
        Correlation::ClearSessionEndCorrelation(logoutObservation, equalClear);
        Require(Correlation::TryResolveLogoutCorrelation(logoutObservation,
                                                         resolvedLogoutCorrelation),
                "equal-sequence logout clear removed a live correlation");

        const Applicator::ApplyResult epochDriftClear{
            .Status = Applicator::ApplyStatus::SessionEndDuplicateNoop,
            .Principal = start.Principal,
            .EventSequence = 1272,
            .ServerProcessEpoch = 88,
        };
        Correlation::ClearSessionEndCorrelation(logoutObservation, epochDriftClear);
        Require(Correlation::TryResolveLogoutCorrelation(logoutObservation,
                                                         resolvedLogoutCorrelation),
                "epoch-drift logout clear removed a live correlation");
        Require(registry.Validate(start.Principal),
                "stale/equal/drift clear attempts invalidated the live principal");

        const Applicator::ProcessLocalEventContext olderLogoutContext = ProofContext(1270, 77);
        Applicator::ApplyResult staleApply =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            logoutObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &olderLogoutContext);
        Correlation::ClearSessionEndCorrelation(logoutObservation, staleApply);
        Require(staleApply.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "older pre-apply logout context did not fail closed");
        Require(!staleApply.RegistryChanged,
                "older pre-apply logout context changed registry");
        Require(!staleApply.Principal.HasValidShape(),
                "older pre-apply logout context returned a principal without fresh proof");
        Require(registry.Validate(start.Principal),
                "older pre-apply logout context invalidated the live principal");
        Require(Correlation::TryResolveLogoutCorrelation(logoutObservation,
                                                         resolvedLogoutCorrelation),
                "older pre-apply logout context cleared live correlation");

        const Applicator::ProcessLocalEventContext equalLogoutContext = ProofContext(1271, 77);
        staleApply = Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                                     logoutObservation,
                                                                     &resolvedLogoutCorrelation,
                                                                     &equalLogoutContext);
        Correlation::ClearSessionEndCorrelation(logoutObservation, staleApply);
        Require(staleApply.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "equal-sequence pre-apply logout context did not fail closed");
        Require(!staleApply.RegistryChanged,
                "equal-sequence pre-apply logout context changed registry");
        Require(!staleApply.Principal.HasValidShape(),
                "equal-sequence pre-apply logout context returned a principal without fresh proof");
        Require(registry.Validate(start.Principal),
                "equal-sequence pre-apply logout context invalidated the live principal");
        Require(Correlation::TryResolveLogoutCorrelation(logoutObservation,
                                                         resolvedLogoutCorrelation),
                "equal-sequence pre-apply logout context cleared live correlation");

        const Applicator::ProcessLocalEventContext epochDriftLogoutContext = ProofContext(1272, 88);
        staleApply = Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                                     logoutObservation,
                                                                     &resolvedLogoutCorrelation,
                                                                     &epochDriftLogoutContext);
        Correlation::ClearSessionEndCorrelation(logoutObservation, staleApply);
        Require(staleApply.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "epoch-drift pre-apply logout context did not fail closed");
        Require(!staleApply.RegistryChanged,
                "epoch-drift pre-apply logout context changed registry");
        Require(!staleApply.Principal.HasValidShape(),
                "epoch-drift pre-apply logout context returned a principal without fresh proof");
        Require(registry.Validate(start.Principal),
                "epoch-drift pre-apply logout context invalidated the live principal");
        Require(Correlation::TryResolveLogoutCorrelation(logoutObservation,
                                                         resolvedLogoutCorrelation),
                "epoch-drift pre-apply logout context cleared live correlation");

        const Applicator::ProcessLocalEventContext validLogoutContext = ProofContext(1272, 77);
        const Applicator::ApplyResult validLogout =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            logoutObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &validLogoutContext);
        Correlation::ClearSessionEndCorrelation(logoutObservation, validLogout);
        Require(validLogout.Status == Applicator::ApplyStatus::SessionEndInvalidated,
                "fresh same-epoch logout did not invalidate principal");
        Require(!Correlation::TryResolveLogoutCorrelation(logoutObservation,
                                                          resolvedLogoutCorrelation),
                "fresh same-epoch logout did not clear correlation");
        Require(!registry.Validate(start.Principal),
                "fresh same-epoch logout left principal live");
        Require(registry.LiveCount() == 0,
                "fresh same-epoch logout left live principals");
    }

    void TestPrivateSubjectTokenCorrelationDoesNotSpendAmbiguousBudgetOnStaleLogoutProof()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        constexpr uint64_t kSubjectToken = 155;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;

        const Observer::CopiedLifecycleObservation firstObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext firstContext = ProofContext(1281, 77);
        const Applicator::ApplyResult first =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            firstObservation,
                                                            nullptr,
                                                            &firstContext);
        Require(first.Status == Applicator::ApplyStatus::SessionStartCreated,
                "ambiguous-budget first fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, firstObservation, first);

        const Observer::CopiedLifecycleObservation secondObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext secondContext = ProofContext(1282, 77);
        const Applicator::ApplyResult second =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            secondObservation,
                                                            nullptr,
                                                            &secondContext);
        Require(second.Status == Applicator::ApplyStatus::SessionStartCreated,
                "ambiguous-budget second fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, secondObservation, second);

        Require(!registry.Validate(first.Principal),
                "ambiguous-budget first principal was not superseded");
        Require(registry.Validate(second.Principal),
                "ambiguous-budget current principal was not live");

        const Observer::CopiedLifecycleObservation logoutObservation =
            MakeEndObservation(kSubjectToken);
        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation;
        Require(Correlation::TryResolveLogoutCorrelation(logoutObservation, resolvedLogoutCorrelation),
                "ambiguous-budget current correlation did not resolve tentatively");
        Require(resolvedLogoutCorrelation.Handle == second.Principal.Handle,
                "ambiguous-budget tentative correlation resolved wrong handle");
        Require(resolvedLogoutCorrelation.Generation == second.Principal.Generation,
                "ambiguous-budget tentative correlation resolved wrong generation");

        const Applicator::ProcessLocalEventContext staleLogoutContext = ProofContext(1281, 77);
        Applicator::ApplyResult logout =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            logoutObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &staleLogoutContext);
        Correlation::ClearSessionEndCorrelation(logoutObservation, logout);
        Require(logout.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "stale ambiguous logout proof did not fail closed");
        Require(!logout.RegistryChanged,
                "stale ambiguous logout proof changed registry");
        Require(registry.Validate(second.Principal),
                "stale ambiguous logout proof invalidated current principal");
        Require(Correlation::TryResolveLogoutCorrelation(logoutObservation, resolvedLogoutCorrelation),
                "stale ambiguous logout proof consumed the reject budget");

        const Applicator::ProcessLocalEventContext epochDriftLogoutContext = ProofContext(1283, 88);
        logout = Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                                 logoutObservation,
                                                                 &resolvedLogoutCorrelation,
                                                                 &epochDriftLogoutContext);
        Correlation::ClearSessionEndCorrelation(logoutObservation, logout);
        Require(logout.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "epoch-drift ambiguous logout proof did not fail closed");
        Require(!logout.RegistryChanged,
                "epoch-drift ambiguous logout proof changed registry");
        Require(registry.Validate(second.Principal),
                "epoch-drift ambiguous logout proof invalidated current principal");
        Require(Correlation::TryResolveLogoutCorrelation(logoutObservation, resolvedLogoutCorrelation),
                "epoch-drift ambiguous logout proof consumed the reject budget");

        const Applicator::ProcessLocalEventContext freshAmbiguousLogoutContext = ProofContext(1283, 77);
        logout = Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                                 logoutObservation,
                                                                 &resolvedLogoutCorrelation,
                                                                 &freshAmbiguousLogoutContext);
        Correlation::ClearSessionEndCorrelation(logoutObservation, logout);
        Require(logout.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "fresh ambiguous logout proof did not consume one reject");
        Require(!logout.RegistryChanged,
                "fresh ambiguous logout proof changed registry");
        Require(registry.Validate(second.Principal),
                "fresh ambiguous logout proof invalidated current principal");

        Require(Correlation::TryResolveLogoutCorrelation(logoutObservation, resolvedLogoutCorrelation),
                "current correlation did not resolve after fresh ambiguous reject");
        const Applicator::ProcessLocalEventContext currentLogoutContext = ProofContext(1284, 77);
        logout = Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                                 logoutObservation,
                                                                 &resolvedLogoutCorrelation,
                                                                 &currentLogoutContext);
        Correlation::ClearSessionEndCorrelation(logoutObservation, logout);
        Require(logout.Status == Applicator::ApplyStatus::SessionEndInvalidated,
                "current logout after preserved ambiguous budget did not invalidate");
        Require(!registry.Validate(second.Principal),
                "current logout after preserved ambiguous budget left principal live");
        Require(registry.LiveCount() == 0,
                "current logout after preserved ambiguous budget left live principals");
    }

    void TestPrivateSubjectTokenCorrelationRejectsEachSupersededLogout()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        constexpr uint64_t kSubjectToken = 202;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;

        const Observer::CopiedLifecycleObservation firstObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext firstContext = ProofContext(1251);
        const Applicator::ApplyResult first =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            firstObservation,
                                                            nullptr,
                                                            &firstContext);
        Require(first.Status == Applicator::ApplyStatus::SessionStartCreated,
                "first multi-supersede fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, firstObservation, first);

        const Observer::CopiedLifecycleObservation secondObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext secondContext = ProofContext(1252);
        const Applicator::ApplyResult second =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            secondObservation,
                                                            nullptr,
                                                            &secondContext);
        Require(second.Status == Applicator::ApplyStatus::SessionStartCreated,
                "second multi-supersede fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, secondObservation, second);

        const Observer::CopiedLifecycleObservation thirdObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext thirdContext = ProofContext(1253);
        const Applicator::ApplyResult third =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            thirdObservation,
                                                            nullptr,
                                                            &thirdContext);
        Require(third.Status == Applicator::ApplyStatus::SessionStartCreated,
                "third multi-supersede fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, thirdObservation, third);

        Require(!registry.Validate(first.Principal),
                "first multi-supersede principal stayed live");
        Require(!registry.Validate(second.Principal),
                "second multi-supersede principal stayed live");
        Require(registry.Validate(third.Principal),
                "current multi-supersede principal did not stay live");
        Require(registry.LiveCount() == 1,
                "multi-supersede registry did not retain only the current principal");

        const Observer::CopiedLifecycleObservation logoutObservation =
            MakeEndObservation(kSubjectToken);
        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation;

        const Applicator::ProcessLocalEventContext firstAmbiguousLogoutContext = ProofContext(1254);
        Require(Correlation::TryResolveLogoutCorrelation(logoutObservation, resolvedLogoutCorrelation),
                "first stale post-supersede logout did not resolve tentative current principal");
        Require(resolvedLogoutCorrelation.Handle == third.Principal.Handle,
                "first stale post-supersede logout resolved wrong tentative handle");
        Require(resolvedLogoutCorrelation.Generation == third.Principal.Generation,
                "first stale post-supersede logout resolved wrong tentative generation");
        Applicator::ApplyResult unresolved =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            logoutObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &firstAmbiguousLogoutContext);
        Correlation::ClearSessionEndCorrelation(logoutObservation, unresolved);
        Require(unresolved.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "first stale post-supersede logout did not no-op");
        Require(registry.Validate(third.Principal),
                "first stale post-supersede logout invalidated current principal");

        const Applicator::ProcessLocalEventContext secondAmbiguousLogoutContext = ProofContext(1255);
        Require(Correlation::TryResolveLogoutCorrelation(logoutObservation, resolvedLogoutCorrelation),
                "second stale post-supersede logout did not resolve tentative current principal");
        Require(resolvedLogoutCorrelation.Handle == third.Principal.Handle,
                "second stale post-supersede logout resolved wrong tentative handle");
        Require(resolvedLogoutCorrelation.Generation == third.Principal.Generation,
                "second stale post-supersede logout resolved wrong tentative generation");
        unresolved = Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                                     logoutObservation,
                                                                     &resolvedLogoutCorrelation,
                                                                     &secondAmbiguousLogoutContext);
        Correlation::ClearSessionEndCorrelation(logoutObservation, unresolved);
        Require(unresolved.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "second stale post-supersede logout did not no-op");
        Require(registry.Validate(third.Principal),
                "second stale post-supersede logout invalidated current principal");

        Require(Correlation::TryResolveLogoutCorrelation(logoutObservation, resolvedLogoutCorrelation),
                "current principal did not resolve after all superseded logout budget was consumed");
        Require(resolvedLogoutCorrelation.Handle == third.Principal.Handle,
                "current correlation resolved wrong handle after multi-supersede budget");
        Require(resolvedLogoutCorrelation.Generation == third.Principal.Generation,
                "current correlation resolved wrong generation after multi-supersede budget");

        const Applicator::ProcessLocalEventContext currentLogoutContext = ProofContext(1256);
        const Applicator::ApplyResult currentLogout =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            logoutObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &currentLogoutContext);
        Correlation::ClearSessionEndCorrelation(logoutObservation, currentLogout);
        Require(currentLogout.Status == Applicator::ApplyStatus::SessionEndInvalidated,
                "current logout after multi-supersede budget did not invalidate");
        Require(!registry.Validate(third.Principal),
                "current logout after multi-supersede budget left principal live");
        Require(registry.LiveCount() == 0,
                "current logout after multi-supersede budget left live principals");
        Require(!Correlation::TryResolveLogoutCorrelation(logoutObservation, resolvedLogoutCorrelation),
                "multi-supersede correlation was not cleared after current logout");
    }

    void TestPrivateSubjectTokenCorrelationRejectsMalformedShapes()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Observer::CopiedLifecycleObservation startObservation =
            MakeStartObservation(true, true, 515);
        const Applicator::ProcessLocalEventContext startContext = ProofContext(1301);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            startObservation,
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "malformed-shape correlation fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, startObservation, start);

        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation;
        Observer::CopiedLifecycleObservation malformedEnd = MakeEndObservation(515);
        malformedEnd.RedactedCount = 2;
        malformedEnd.RedactedStorage[1] = Reflection::LifecycleField::Exiting;
        malformedEnd.RedactedProcessLocalSubjectTokens[1] = 515;
        Require(!Correlation::TryResolveLogoutCorrelation(malformedEnd, resolvedLogoutCorrelation),
                "duplicate Exiting redaction resolved a private logout correlation");
        Require(!resolvedLogoutCorrelation.HasValidShape(),
                "malformed logout left a resolved private correlation");

        malformedEnd = MakeEndObservation(515);
        malformedEnd.RedactedProcessLocalSubjectTokens[1] = 515;
        const Applicator::ProcessLocalEventContext malformedEndContext = ProofContext(1302);
        const Applicator::ApplyResult malformedEndApply =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            malformedEnd,
                                                            &start.Principal,
                                                            &malformedEndContext);
        Require(malformedEndApply.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "logout with unused private subject token did not fail closed");
        Require(!malformedEndApply.RegistryChanged,
                "logout with unused private subject token changed registry");
        Require(!malformedEndApply.Principal.HasValidShape(),
                "logout with unused private subject token returned a principal");
        Require(registry.Validate(start.Principal),
                "logout with unused private subject token invalidated live principal");
        Require(!Correlation::TryResolveLogoutCorrelation(malformedEnd, resolvedLogoutCorrelation),
                "logout with unused private subject token resolved a private correlation");
        Require(!resolvedLogoutCorrelation.HasValidShape(),
                "logout with unused private subject token left a resolved private correlation");

        malformedEnd = MakeEndObservation(515);
        malformedEnd.Function = Reflection::LifecycleFunction::HandleNewPlayer;
        Require(!Correlation::TryResolveLogoutCorrelation(malformedEnd, resolvedLogoutCorrelation),
                "wrong-function logout resolved a private correlation");
        Require(!resolvedLogoutCorrelation.HasValidShape(),
                "wrong-function logout left a resolved private correlation");

        Observer::CopiedLifecycleObservation wrongActionStart =
            MakeStartObservation(true, true, 717);
        wrongActionStart.Action = Observer::PrincipalAction::None;
        Correlation::BindSessionStartCorrelation(registry, wrongActionStart, start);
        Require(!Correlation::TryResolveLogoutCorrelation(MakeEndObservation(717),
                                                          resolvedLogoutCorrelation),
                "wrong-action start bound a private correlation");
        Require(!resolvedLogoutCorrelation.HasValidShape(),
                "wrong-action start left a resolved private correlation");

        Observer::CopiedLifecycleObservation malformedStart =
            MakeStartObservation(true, true, 616);
        malformedStart.RedactedProcessLocalSubjectTokens[1] = 617;
        const Applicator::ApplyResult malformedStartApply =
            Applicator::ApplyLifecycleObservationToRegistry(registry, malformedStart);
        Require(malformedStartApply.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "start with extra private token did not fail closed");
        Require(!malformedStartApply.RegistryChanged,
                "start with extra private token changed registry");
        Correlation::BindSessionStartCorrelation(registry, malformedStart, start);
        Require(!Correlation::TryResolveLogoutCorrelation(MakeEndObservation(616),
                                                          resolvedLogoutCorrelation),
                "malformed start redaction shape bound a private correlation");

        const Applicator::ApplyResult fakeEnd{
            .Status = Applicator::ApplyStatus::SessionEndInvalidated,
            .Principal = start.Principal,
        };
        Correlation::ClearSessionEndCorrelation(malformedEnd, fakeEnd);
        Require(Correlation::TryResolveLogoutCorrelation(MakeEndObservation(515),
                                                         resolvedLogoutCorrelation),
                "malformed logout clear removed a valid private correlation");
        Require(resolvedLogoutCorrelation.Handle == start.Principal.Handle,
                "malformed logout clear changed correlation handle");
        Require(resolvedLogoutCorrelation.Generation == start.Principal.Generation,
                "malformed logout clear changed correlation generation");

        const Applicator::ApplyResult duplicateWithoutLogoutReason{
            .Status = Applicator::ApplyStatus::SessionEndDuplicateNoop,
            .Principal = start.Principal,
            .EventSequence = 1302,
            .ServerProcessEpoch = 77,
        };
        Correlation::ClearSessionEndCorrelation(MakeEndObservation(515),
                                                duplicateWithoutLogoutReason);
        Require(Correlation::TryResolveLogoutCorrelation(MakeEndObservation(515),
                                                         resolvedLogoutCorrelation),
                "duplicate logout clear without logout invalidation reason removed a valid private correlation");
        Require(resolvedLogoutCorrelation.Handle == start.Principal.Handle,
                "duplicate logout clear without logout reason changed correlation handle");
        Require(resolvedLogoutCorrelation.Generation == start.Principal.Generation,
                "duplicate logout clear without logout reason changed correlation generation");

        const Applicator::ApplyResult extraReasonEnd{
            .Status = Applicator::ApplyStatus::SessionEndInvalidated,
            .Principal = start.Principal,
            .InvalidationReasons = Obelisk::Core::PlayerPrincipalInvalidationFlag(
                    Obelisk::Core::PlayerPrincipalInvalidationReason::Logout) |
                Obelisk::Core::PlayerPrincipalInvalidationFlag(
                    Obelisk::Core::PlayerPrincipalInvalidationReason::RuntimeReset),
            .EventSequence = 1302,
            .ServerProcessEpoch = 77,
            .RegistryChanged = true,
        };
        Correlation::ClearSessionEndCorrelation(MakeEndObservation(515), extraReasonEnd);
        Require(Correlation::TryResolveLogoutCorrelation(MakeEndObservation(515),
                                                         resolvedLogoutCorrelation),
                "extra-reason logout clear removed a valid private correlation");
        Require(resolvedLogoutCorrelation.Handle == start.Principal.Handle,
                "extra-reason logout clear changed correlation handle");
        Require(resolvedLogoutCorrelation.Generation == start.Principal.Generation,
                "extra-reason logout clear changed correlation generation");

        Correlation::ClearSessionEndCorrelation(MakeEndObservation(515), fakeEnd);
        Require(Correlation::TryResolveLogoutCorrelation(MakeEndObservation(515),
                                                         resolvedLogoutCorrelation),
                "incomplete logout apply proof removed a valid private correlation");
        Require(resolvedLogoutCorrelation.Handle == start.Principal.Handle,
                "incomplete logout apply proof changed correlation handle");
    }

    void TestPrivateSubjectTokenCorrelationRejectsNonExactRoleShapes()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        const auto requireMalformedStartDoesNotBind =
            [](Observer::CopiedLifecycleObservation malformedStart, const char* message) {
                Correlation::ResetForTesting();
                Obelisk::Core::PlayerPrincipalRegistry registry;
                const uint64_t subjectToken =
                    malformedStart.RedactedProcessLocalSubjectTokens[0];
                const Observer::CopiedLifecycleObservation validStart =
                    MakeStartObservation(true, true, subjectToken);
                const Applicator::ProcessLocalEventContext context = ProofContext(1325);
                const Applicator::ApplyResult result =
                    Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                                    validStart,
                                                                    nullptr,
                                                                    &context);
                Require(result.Status == Applicator::ApplyStatus::SessionStartCreated,
                        "non-exact start bind fixture did not create principal");

                Correlation::BindSessionStartCorrelation(registry, malformedStart, result);

                Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation;
                Require(!Correlation::TryResolveLogoutCorrelation(MakeEndObservation(subjectToken),
                                                                  resolvedLogoutCorrelation),
                        message);
                Require(!resolvedLogoutCorrelation.HasValidShape(),
                        "non-exact start bind left a resolved private correlation");
                Require(registry.Validate(result.Principal),
                        "non-exact start bind invalidated the valid principal");
            };

        Observer::CopiedLifecycleObservation malformedStart =
            MakeStartObservation(true, true, 1325);
        malformedStart.FunctionNameIndex = kHandleNewPlayerNameIndex + 1;
        requireMalformedStartDoesNotBind(
            malformedStart,
            "start correlation bound wrong HandleNewPlayer FName index");

        malformedStart = MakeStartObservation(true, true, 1326);
        malformedStart.OuterNameIndex = kShooterGameModeNameIndex + 1;
        requireMalformedStartDoesNotBind(
            malformedStart,
            "start correlation bound wrong HandleNewPlayer outer index");

        malformedStart = MakeStartObservation(true, true, 1327);
        malformedStart.BoolStorage[1].Value = false;
        requireMalformedStartDoesNotBind(
            malformedStart,
            "start correlation bound non-accepted bool tuple");

        malformedStart = MakeStartObservation(true, true, 1328);
        malformedStart.BoolStorage[0].Field = Reflection::LifecycleField::ReturnValue;
        malformedStart.BoolStorage[1].Field = Reflection::LifecycleField::BIsFromLogin;
        requireMalformedStartDoesNotBind(
            malformedStart,
            "start correlation bound swapped bool fields");

        const auto requireMalformedLogoutDoesNotResolve =
            [](Observer::CopiedLifecycleObservation malformedLogout, const char* message) {
                Correlation::ResetForTesting();
                Obelisk::Core::PlayerPrincipalRegistry registry;
                const uint64_t subjectToken =
                    malformedLogout.RedactedProcessLocalSubjectTokens[0];
                const Observer::CopiedLifecycleObservation validStart =
                    MakeStartObservation(true, true, subjectToken);
                const Applicator::ProcessLocalEventContext context = ProofContext(1330);
                const Applicator::ApplyResult result =
                    Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                                    validStart,
                                                                    nullptr,
                                                                    &context);
                Require(result.Status == Applicator::ApplyStatus::SessionStartCreated,
                        "non-exact logout resolve fixture did not create principal");
                Correlation::BindSessionStartCorrelation(registry, validStart, result);

                Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation;
                Require(!Correlation::TryResolveLogoutCorrelation(malformedLogout,
                                                                  resolvedLogoutCorrelation),
                        message);
                Require(!resolvedLogoutCorrelation.HasValidShape(),
                        "non-exact logout resolve left a private principal token");
                Require(registry.Validate(result.Principal),
                        "non-exact logout resolve invalidated the valid principal");

                const Observer::CopiedLifecycleObservation validLogout =
                    MakeEndObservation(subjectToken);
                Require(Correlation::TryResolveLogoutCorrelation(validLogout,
                                                                 resolvedLogoutCorrelation),
                        "non-exact logout resolve removed the valid correlation");
                Require(resolvedLogoutCorrelation.Handle == result.Principal.Handle,
                        "non-exact logout resolve changed the valid correlation handle");
                Require(resolvedLogoutCorrelation.Generation == result.Principal.Generation,
                        "non-exact logout resolve changed the valid correlation generation");
            };

        Observer::CopiedLifecycleObservation malformedLogout =
            MakeEndObservation(1331);
        malformedLogout.FunctionNameIndex = kOnLogoutNameIndex + 1;
        requireMalformedLogoutDoesNotResolve(
            malformedLogout,
            "logout correlation resolved wrong OnLogout FName index");

        malformedLogout = MakeEndObservation(1332);
        malformedLogout.OuterNameIndex = kShooterGameModeNameIndex + 1;
        requireMalformedLogoutDoesNotResolve(
            malformedLogout,
            "logout correlation resolved wrong OnLogout outer index");

        malformedLogout = MakeEndObservation(1333);
        malformedLogout.BoolCount = 1;
        malformedLogout.BoolStorage[0] = {
            .Field = Reflection::LifecycleField::ReturnValue,
            .Value = false,
        };
        requireMalformedLogoutDoesNotResolve(
            malformedLogout,
            "logout correlation resolved a shape with unexpected bool payload");

        Correlation::ResetForTesting();
    }

    void TestDuplicateAndStaleSessionEndNoop()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Observer::CopiedLifecycleObservation startObservation =
            MakeStartObservation(true, true, 302);
        const Applicator::ProcessLocalEventContext startContext = ProofContext(910);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            startObservation,
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "start fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, startObservation, start);

        const Observer::CopiedLifecycleObservation endObservation = MakeEndObservation(302);
        const Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation =
            RequireResolvedLogoutCorrelation(endObservation,
                                             "duplicate/stale fixture did not resolve logout proof");
        const Applicator::ProcessLocalEventContext firstLogoutContext = ProofContext(911);
        const Applicator::ApplyResult firstLogout =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            endObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &firstLogoutContext);
        Require(firstLogout.Status == Applicator::ApplyStatus::SessionEndInvalidated,
                "first correlated logout did not invalidate");

        const Applicator::ProcessLocalEventContext duplicateContext = ProofContext(912);
        Applicator::ApplyResult duplicate =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            endObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &duplicateContext);
        Require(duplicate.Status == Applicator::ApplyStatus::SessionEndDuplicateNoop,
                "duplicate logout did not no-op");
        Require(!duplicate.RegistryChanged, "duplicate logout changed registry");
        RequireRegistryPointer(duplicate,
                               registry,
                               "duplicate logout did not retain registry proof");
        Correlation::ClearSessionEndCorrelation(endObservation, duplicate);
        Obelisk::Core::PlayerPrincipalToken stillResolvedLogoutCorrelation;
        Require(!Correlation::TryResolveLogoutCorrelation(endObservation,
                                                          stillResolvedLogoutCorrelation),
                "duplicate logout clear retained stale private correlation");

        Correlation::ResetForTesting();
        const Observer::CopiedLifecycleObservation staleStartObservation =
            MakeStartObservation(true, true, 306);
        const Applicator::ProcessLocalEventContext staleStartContext = ProofContext(913);
        const Applicator::ApplyResult staleStart =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            staleStartObservation,
                                                            nullptr,
                                                            &staleStartContext);
        Require(staleStart.Status == Applicator::ApplyStatus::SessionStartCreated,
                "stale fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, staleStartObservation, staleStart);

        const Observer::CopiedLifecycleObservation staleEndObservation = MakeEndObservation(306);
        const Obelisk::Core::PlayerPrincipalToken staleResolvedLogoutCorrelation =
            RequireResolvedLogoutCorrelation(staleEndObservation,
                                             "stale fixture did not resolve logout proof");
        const Obelisk::Core::PlayerPrincipalToken reactivated =
            InvalidateForReconnectAndReactivate(registry,
                                                staleStart.Principal,
                                                "stale fixture reconnect invalidation failed",
                                                "stale fixture reactivation failed");
        const Applicator::ProcessLocalEventContext staleContext = ProofContext(914);
        Applicator::ApplyResult stale =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            staleEndObservation,
                                                            &staleResolvedLogoutCorrelation,
                                                            &staleContext);
        Require(stale.Status == Applicator::ApplyStatus::SessionEndStaleNoop,
                "stale logout generation did not no-op");
        RequireRegistryPointer(stale,
                               registry,
                               "stale logout did not retain registry proof");
        Correlation::ClearSessionEndCorrelation(staleEndObservation, stale);
        Require(!Correlation::TryResolveLogoutCorrelation(staleEndObservation,
                                                          stillResolvedLogoutCorrelation),
                "stale logout clear retained stale private correlation");
        Require(registry.Validate(reactivated), "stale logout invalidated current generation");
        Require(registry.LiveCount() == 1, "stale logout live count mismatch");
    }

    void TestNonLogoutInvalidatedSessionEndClearsStaleCorrelation()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        Correlation::ResetForTesting();
        for (const auto reason : {
                 Obelisk::Core::PlayerPrincipalInvalidationReason::RuntimeReset,
                 Obelisk::Core::PlayerPrincipalInvalidationReason::Superseded,
             })
        {
            Correlation::ResetForTesting();
            Obelisk::Core::PlayerPrincipalRegistry registry;
            const uint64_t subjectToken =
                reason == Obelisk::Core::PlayerPrincipalInvalidationReason::RuntimeReset ? 304 : 305;
            const Observer::CopiedLifecycleObservation startObservation =
                MakeStartObservation(true, true, subjectToken);
            const Applicator::ProcessLocalEventContext startContext = ProofContext(930, 77);
            const Applicator::ApplyResult start =
                Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                                startObservation,
                                                                nullptr,
                                                                &startContext);
            Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                    "non-logout invalidation fixture did not create principal");
            Correlation::BindSessionStartCorrelation(registry, startObservation, start);

            Require(registry.InvalidatePrincipal(
                        start.Principal,
                        Obelisk::Core::PlayerPrincipalInvalidationFlag(reason)),
                    "non-logout invalidation fixture could not invalidate principal");

            const Observer::CopiedLifecycleObservation endObservation =
                MakeEndObservation(subjectToken);
            Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation =
                RequireResolvedLogoutCorrelation(endObservation,
                                                 "non-logout invalidation fixture did not resolve logout proof");
            const Applicator::ProcessLocalEventContext endContext = ProofContext(931, 77);
            const Applicator::ApplyResult end =
                Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                                endObservation,
                                                                &resolvedLogoutCorrelation,
                                                                &endContext);
            Require(end.Status == Applicator::ApplyStatus::SessionEndStaleNoop,
                    "non-logout invalidated principal was reported as a duplicate logout");
            Require(!end.RegistryChanged,
                    "non-logout invalidated principal changed registry during logout apply");
            Require(!end.PrincipalLive,
                    "non-logout invalidated principal was reported live");
            RequireRegistryPointer(end,
                                   registry,
                                   "non-logout invalidated principal did not retain registry proof");
            Require(end.InvalidationReasons == Obelisk::Core::PlayerPrincipalInvalidationFlag(reason),
                    "non-logout invalidated principal did not preserve terminal reason");
            Require(registry.LiveCount() == 0,
                    "non-logout invalidated principal left live registry entries");

            Correlation::ClearSessionEndCorrelation(endObservation, end);
            Require(!Correlation::TryResolveLogoutCorrelation(endObservation,
                                                              resolvedLogoutCorrelation),
                    "non-logout stale correlation remained resolvable after registry-confirmed clear");
        }
    }

    void TestPrunedInvalidatedSessionEndClearsStaleCorrelation()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        constexpr uint64_t kSubjectToken = 309;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;
        registry.SetMaxRetainedInvalidatedPrincipalsForTesting(0);

        const Observer::CopiedLifecycleObservation startObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext startContext = ProofContext(950, 77);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            startObservation,
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "pruned-correlation fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, startObservation, start);

        Require(registry.LogoutPrincipal(start.Principal),
                "pruned-correlation fixture could not invalidate principal");
        Require(registry.Lookup(start.Principal).Status ==
                    Obelisk::Core::PlayerPrincipalLookupStatus::UnknownHandle,
                "zero retention did not prune invalidated principal");

        const Observer::CopiedLifecycleObservation endObservation =
            MakeEndObservation(kSubjectToken);
        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation =
            RequireResolvedLogoutCorrelation(endObservation,
                                             "pruned-correlation fixture did not resolve stale proof");
        const Applicator::ProcessLocalEventContext endContext = ProofContext(951, 77);
        const Applicator::ApplyResult end =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            endObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &endContext);
        Require(end.Status == Applicator::ApplyStatus::SessionEndStaleNoop,
                "pruned invalidated principal did not produce a stale terminal no-op");
        Require(!end.RegistryChanged,
                "pruned invalidated principal changed registry during logout apply");
        RequireRegistryPointer(end,
                               registry,
                               "pruned invalidated principal did not retain registry proof");

        Correlation::ClearSessionEndCorrelation(endObservation, end);
        Require(!Correlation::TryResolveLogoutCorrelation(endObservation,
                                                          resolvedLogoutCorrelation),
                "pruned stale private correlation remained resolvable after clear");
        Require(registry.LiveCount() == 0,
                "pruned-correlation fixture left live registry entries");
        Require(registry.RetainedInvalidatedCount() == 0,
                "pruned-correlation fixture retained invalidated principals");
    }

    void TestSessionEndInvalidationRequiresRetainedLogoutProof()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        constexpr uint64_t kSubjectToken = 312;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;
        registry.SetMaxRetainedInvalidatedPrincipalsForTesting(0);

        const Observer::CopiedLifecycleObservation startObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext startContext = ProofContext(970, 77);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            startObservation,
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "retained-proof fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, startObservation, start);

        const Observer::CopiedLifecycleObservation endObservation =
            MakeEndObservation(kSubjectToken);
        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation =
            RequireResolvedLogoutCorrelation(
                endObservation,
                "retained-proof fixture did not resolve logout correlation");
        const Applicator::ProcessLocalEventContext endContext = ProofContext(971, 77);
        const Applicator::ApplyResult end =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            endObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &endContext);

        Require(end.Status == Applicator::ApplyStatus::SessionEndStaleNoop,
                "pruned logout proof was reported as accepted session_end evidence");
        Require(!end.ValidatedLifecycleEvent,
                "pruned logout proof was marked as validated lifecycle evidence");
        Require(!end.RegistryChanged,
                "pruned logout proof reported an evidence-bearing registry mutation");
        Require(!end.PrincipalLive,
                "pruned logout proof reported a live principal");
        RequireRegistryPointer(end,
                               registry,
                               "pruned logout proof did not retain registry confirmation pointer");
        Require(end.Principal.Handle == start.Principal.Handle,
                "pruned logout proof returned the wrong principal handle");
        Require(end.Principal.Generation == start.Principal.Generation,
                "pruned logout proof returned the wrong principal generation");
        Require(end.InvalidationReasons == 0,
                "pruned logout proof retained an unconfirmed invalidation reason");
        Require(registry.Lookup(start.Principal).Status ==
                    Obelisk::Core::PlayerPrincipalLookupStatus::UnknownHandle,
                "pruned logout proof unexpectedly retained registry state");
        Require(registry.LiveCount() == 0,
                "pruned logout proof left a live principal");
        Require(registry.RetainedInvalidatedCount() == 0,
                "pruned logout proof retained invalidated state");

        Correlation::ClearSessionEndCorrelation(endObservation, end);
        Require(!Correlation::TryResolveLogoutCorrelation(endObservation,
                                                          resolvedLogoutCorrelation),
                "pruned non-evidence logout did not clear stale private correlation");
    }

    void TestPrivateSubjectTokenCorrelationClearRequiresRegistryConfirmation()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        constexpr uint64_t kSubjectToken = 308;
        constexpr auto kLogoutReason =
            Obelisk::Core::PlayerPrincipalInvalidationFlag(
                Obelisk::Core::PlayerPrincipalInvalidationReason::Logout);

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Observer::CopiedLifecycleObservation startObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext startContext = ProofContext(940, 77);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            startObservation,
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "registry-confirmation clear fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, startObservation, start);

        const Observer::CopiedLifecycleObservation endObservation =
            MakeEndObservation(kSubjectToken);
        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation =
            RequireResolvedLogoutCorrelation(endObservation,
                                             "registry-confirmation clear fixture did not resolve proof");

        const Applicator::ApplyResult forgedWithoutRegistry{
            .Status = Applicator::ApplyStatus::SessionEndInvalidated,
            .Principal = start.Principal,
            .InvalidationReasons = kLogoutReason,
            .EventSequence = 941,
            .ServerProcessEpoch = 77,
            .RegistryChanged = true,
            .PrincipalLive = false,
        };
        Correlation::ClearSessionEndCorrelation(endObservation, forgedWithoutRegistry);
        Require(Correlation::TryResolveLogoutCorrelation(endObservation,
                                                         resolvedLogoutCorrelation),
                "registry-confirmation clear accepted logout result without registry proof");
        Require(resolvedLogoutCorrelation.Handle == start.Principal.Handle,
                "registry-confirmation no-registry clear changed correlation handle");
        Require(resolvedLogoutCorrelation.Generation == start.Principal.Generation,
                "registry-confirmation no-registry clear changed correlation generation");

        const Applicator::ApplyResult forgedWithLiveRegistry{
            .Status = Applicator::ApplyStatus::SessionEndInvalidated,
            .Principal = start.Principal,
            .Registry = &registry,
            .InvalidationReasons = kLogoutReason,
            .EventSequence = 942,
            .ServerProcessEpoch = 77,
            .RegistryChanged = true,
            .PrincipalLive = false,
        };
        Correlation::ClearSessionEndCorrelation(endObservation, forgedWithLiveRegistry);
        Require(Correlation::TryResolveLogoutCorrelation(endObservation,
                                                         resolvedLogoutCorrelation),
                "registry-confirmation clear accepted logout result while registry was still live");
        Require(registry.Validate(start.Principal),
                "registry-confirmation forged clear invalidated live principal");

        Obelisk::Core::PlayerPrincipalRegistry unrelatedRegistry;
        const Applicator::ApplyResult forgedPrunedWithUnrelatedRegistry{
            .Status = Applicator::ApplyStatus::SessionEndInvalidated,
            .Principal = start.Principal,
            .Registry = &unrelatedRegistry,
            .InvalidationReasons = kLogoutReason,
            .EventSequence = 943,
            .ServerProcessEpoch = 77,
            .RegistryChanged = true,
            .PrincipalLive = false,
        };
        Correlation::ClearSessionEndCorrelation(endObservation,
                                                forgedPrunedWithUnrelatedRegistry);
        Require(Correlation::TryResolveLogoutCorrelation(endObservation,
                                                         resolvedLogoutCorrelation),
                "registry-confirmation clear accepted pruned proof from an unrelated registry");
        Require(resolvedLogoutCorrelation.Handle == start.Principal.Handle,
                "registry-confirmation unrelated-registry clear changed correlation handle");
        Require(resolvedLogoutCorrelation.Generation == start.Principal.Generation,
                "registry-confirmation unrelated-registry clear changed correlation generation");

        const Applicator::ApplyResult staleWithUnrelatedRegistry{
            .Status = Applicator::ApplyStatus::SessionEndStaleNoop,
            .Principal = start.Principal,
            .Registry = &unrelatedRegistry,
            .EventSequence = 944,
            .ServerProcessEpoch = 77,
        };
        Correlation::ClearSessionEndCorrelation(endObservation,
                                                staleWithUnrelatedRegistry);
        Require(Correlation::TryResolveLogoutCorrelation(endObservation,
                                                         resolvedLogoutCorrelation),
                "registry-confirmation clear accepted stale proof from an unrelated registry");
        Require(resolvedLogoutCorrelation.Handle == start.Principal.Handle,
                "registry-confirmation stale unrelated-registry clear changed correlation handle");
        Require(resolvedLogoutCorrelation.Generation == start.Principal.Generation,
                "registry-confirmation stale unrelated-registry clear changed correlation generation");

        const Applicator::ProcessLocalEventContext endContext = ProofContext(943, 77);
        const Applicator::ApplyResult end =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            endObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &endContext);
        Correlation::ClearSessionEndCorrelation(endObservation, end);
        Require(end.Status == Applicator::ApplyStatus::SessionEndInvalidated,
                "registry-confirmation valid logout did not invalidate principal");
        Require(!Correlation::TryResolveLogoutCorrelation(endObservation,
                                                          resolvedLogoutCorrelation),
                "registry-confirmation valid logout was not cleared");
    }

    void TestPrivateSubjectTokenCorrelationRejectsForeignRegistryTokenCollision()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        constexpr uint64_t kSubjectToken = 310;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry sourceRegistry;
        const Observer::CopiedLifecycleObservation startObservation =
            MakeStartObservation(true, true, kSubjectToken);
        const Applicator::ProcessLocalEventContext startContext = ProofContext(960, 77);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(sourceRegistry,
                                                            startObservation,
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "foreign-registry collision fixture did not create source principal");
        Correlation::BindSessionStartCorrelation(sourceRegistry, startObservation, start);

        Obelisk::Core::PlayerPrincipalRegistry foreignRegistry;
        const Obelisk::Core::PlayerPrincipalToken foreignPrincipal =
            foreignRegistry.AllocatePrincipal();
        Require(foreignPrincipal.Handle == start.Principal.Handle,
                "foreign-registry collision fixture did not reuse handle shape");
        Require(foreignPrincipal.Generation == start.Principal.Generation,
                "foreign-registry collision fixture did not reuse generation shape");
        Require(foreignRegistry.Validate(foreignPrincipal),
                "foreign-registry collision fixture principal was not live");

        const Observer::CopiedLifecycleObservation endObservation =
            MakeEndObservation(kSubjectToken);
        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation =
            RequireResolvedLogoutCorrelation(
                endObservation,
                "foreign-registry collision fixture did not resolve source proof");
        Require(resolvedLogoutCorrelation.Handle == start.Principal.Handle,
                "foreign-registry collision resolved wrong source handle");
        Require(resolvedLogoutCorrelation.Generation == start.Principal.Generation,
                "foreign-registry collision resolved wrong source generation");

        const Applicator::ProcessLocalEventContext endContext = ProofContext(961, 77);
        const Applicator::ApplyResult foreignEnd =
            Applicator::ApplyLifecycleObservationToRegistry(foreignRegistry,
                                                            endObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &endContext);
        Correlation::ClearSessionEndCorrelation(endObservation, foreignEnd);

        Require(foreignEnd.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "foreign-registry collision reached registry mutation");
        Require(!foreignEnd.RegistryChanged,
                "foreign-registry collision changed registry");
        RequireNoRegistryPointer(foreignEnd,
                                 "foreign-registry collision exposed registry proof");
        Require(!foreignEnd.Principal.HasValidShape(),
                "foreign-registry collision returned a token-bearing logout result");
        Require(foreignRegistry.Validate(foreignPrincipal),
                "foreign-registry collision invalidated colliding foreign principal");
        Require(sourceRegistry.Validate(start.Principal),
                "foreign-registry collision invalidated source principal");
        Require(Correlation::TryResolveLogoutCorrelation(endObservation,
                                                         resolvedLogoutCorrelation),
                "foreign-registry collision cleared source correlation");
        Require(resolvedLogoutCorrelation.Handle == start.Principal.Handle,
                "foreign-registry collision changed retained source handle");
        Require(resolvedLogoutCorrelation.Generation == start.Principal.Generation,
                "foreign-registry collision changed retained source generation");
    }

    void TestCorrelatedDuplicateAndStaleSessionEndPreserveEventContext()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Observer::CopiedLifecycleObservation startObservation =
            MakeStartObservation(true, true, 303);
        const Applicator::ProcessLocalEventContext startContext = ProofContext(920, 9);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            startObservation,
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "context logout fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, startObservation, start);

        const Observer::CopiedLifecycleObservation endObservation = MakeEndObservation(303);
        const Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation =
            RequireResolvedLogoutCorrelation(endObservation,
                                             "context logout fixture did not resolve private proof");
        const Applicator::ProcessLocalEventContext correlatedContext{
            .EventSequence = 921,
            .ServerProcessEpoch = 9,
        };
        const Applicator::ApplyResult correlated =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            endObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &correlatedContext);
        Require(correlated.Status == Applicator::ApplyStatus::SessionEndInvalidated,
                "context correlated logout did not invalidate");
        RequireEventContext(correlated,
                            correlatedContext.EventSequence,
                            correlatedContext.ServerProcessEpoch,
                            "context correlated logout lost event sequence",
                            "context correlated logout lost server process epoch");

        const Applicator::ProcessLocalEventContext duplicateContext{
            .EventSequence = 922,
            .ServerProcessEpoch = 9,
        };
        const Applicator::ApplyResult duplicate =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            endObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &duplicateContext);
        Require(duplicate.Status == Applicator::ApplyStatus::SessionEndDuplicateNoop,
                "context duplicate logout did not no-op");
        Require(!duplicate.RegistryChanged, "context duplicate logout changed registry");
        RequireRegistryPointer(duplicate,
                               registry,
                               "context duplicate logout did not retain registry proof");
        RequireEventContext(duplicate,
                            duplicateContext.EventSequence,
                            duplicateContext.ServerProcessEpoch,
                            "context duplicate logout lost event sequence",
                            "context duplicate logout lost server process epoch");

        Correlation::ResetForTesting();
        const Observer::CopiedLifecycleObservation staleStartObservation =
            MakeStartObservation(true, true, 307);
        const Applicator::ProcessLocalEventContext staleStartContext{
            .EventSequence = 923,
            .ServerProcessEpoch = 9,
        };
        const Applicator::ApplyResult staleStart =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            staleStartObservation,
                                                            nullptr,
                                                            &staleStartContext);
        Require(staleStart.Status == Applicator::ApplyStatus::SessionStartCreated,
                "context stale fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry,
                                                 staleStartObservation,
                                                 staleStart);

        const Observer::CopiedLifecycleObservation staleEndObservation =
            MakeEndObservation(307);
        const Obelisk::Core::PlayerPrincipalToken staleResolvedLogoutCorrelation =
            RequireResolvedLogoutCorrelation(staleEndObservation,
                                             "context stale fixture did not resolve private proof");
        const Obelisk::Core::PlayerPrincipalToken reactivated =
            InvalidateForReconnectAndReactivate(
                registry,
                staleStart.Principal,
                "context stale fixture reconnect invalidation failed",
                "context stale logout reactivation fixture failed");

        const Applicator::ProcessLocalEventContext staleContext{
            .EventSequence = 924,
            .ServerProcessEpoch = 9,
        };
        const Applicator::ApplyResult stale =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            staleEndObservation,
                                                            &staleResolvedLogoutCorrelation,
                                                            &staleContext);
        Require(stale.Status == Applicator::ApplyStatus::SessionEndStaleNoop,
                "context stale logout did not no-op");
        Require(!stale.RegistryChanged, "context stale logout changed registry");
        RequireRegistryPointer(stale,
                               registry,
                               "context stale logout did not retain registry proof");
        Require(registry.Validate(reactivated),
                "context stale logout invalidated current generation");
        RequireEventContext(stale,
                            staleContext.EventSequence,
                            staleContext.ServerProcessEpoch,
                            "context stale logout lost event sequence",
                            "context stale logout lost server process epoch");
    }

    void TestSessionStartAllocationFailureFailsClosed()
    {
        Obelisk::Core::PlayerPrincipalRegistry registry;
        registry.SetNextHandleForTesting(0);

        const Applicator::ProcessLocalEventContext context = ProofContext(804);
        const Applicator::ApplyResult result =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            MakeStartObservation(true, true),
                                                            nullptr,
                                                            &context);
        Require(result.Status == Applicator::ApplyStatus::SessionStartAllocationFailed,
                "session_start allocation failure did not fail closed");
        Require(!result.RegistryChanged, "failed allocation changed registry");
        RequireNoRegistryPointer(result,
                                 "failed allocation exposed a registry pointer");
        Require(registry.LiveCount() == 0, "failed allocation changed live count");
    }

    void TestSessionStartWithoutMatchedEventContextFailsClosed()
    {
        Obelisk::Core::PlayerPrincipalRegistry registry;
        Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry, MakeStartObservation(true, true));
        Require(start.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "missing-context accepted session_start did not fail closed");
        Require(!start.RegistryChanged,
                "missing-context accepted session_start changed registry");
        Require(!start.Principal.HasValidShape(),
                "missing-context accepted session_start returned a principal");
        RequireEventContext(start,
                            0,
                            0,
                            "missing-context session_start had nonzero event sequence",
                            "missing-context session_start had nonzero server process epoch");
        Require(registry.LiveCount() == 0,
                "missing-context accepted session_start allocated a principal");

        const Applicator::ProcessLocalEventContext zeroSequenceContext{
            .EventSequence = 0,
            .ServerProcessEpoch = 7,
        };
        start = Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                                MakeStartObservation(true, true),
                                                                nullptr,
                                                                &zeroSequenceContext);
        Require(start.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "zero-sequence accepted session_start did not fail closed");
        Require(!start.RegistryChanged,
                "zero-sequence accepted session_start changed registry");
        Require(!start.Principal.HasValidShape(),
                "zero-sequence accepted session_start returned a principal");
        RequireEventContext(start,
                            0,
                            0,
                            "zero-sequence session_start retained event sequence",
                            "zero-sequence session_start retained server process epoch");
        Require(registry.LiveCount() == 0,
                "zero-sequence accepted session_start allocated a principal");

        const Applicator::ProcessLocalEventContext zeroEpochContext{
            .EventSequence = 8,
            .ServerProcessEpoch = 0,
        };
        start = Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                                MakeStartObservation(true, true),
                                                                nullptr,
                                                                &zeroEpochContext);
        Require(start.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "zero-epoch accepted session_start did not fail closed");
        Require(!start.RegistryChanged,
                "zero-epoch accepted session_start changed registry");
        Require(!start.Principal.HasValidShape(),
                "zero-epoch accepted session_start returned a principal");
        RequireEventContext(start,
                            0,
                            0,
                            "zero-epoch session_start retained event sequence",
                            "zero-epoch session_start retained server process epoch");
        Require(registry.LiveCount() == 0,
                "zero-epoch accepted session_start allocated a principal");

        const Applicator::ProcessLocalEventContext validStartContext = ProofContext(805);
        start = Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                                MakeStartObservation(true, true),
                                                                nullptr,
                                                                &validStartContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "valid-context start fixture did not create principal");

        const Applicator::ApplyResult end =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            MakeEndObservation(1),
                                                            &start.Principal);
        Require(end.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "default-context correlated end did not fail closed without proof context");
        Require(!end.RegistryChanged,
                "default-context correlated end changed registry without proof context");
        Require(!end.Principal.HasValidShape(),
                "default-context correlated end returned a principal without proof context");
        Require(registry.Validate(start.Principal),
                "default-context correlated end invalidated without proof context");
        RequireEventContext(end,
                            0,
                            0,
                            "default-context session_end had nonzero event sequence",
                            "default-context session_end had nonzero server process epoch");
    }

    void TestSuppliedEventContextReachesValidatedEventViews()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;

        const Applicator::ProcessLocalEventContext startContext{
            .EventSequence = 101,
            .ServerProcessEpoch = 7,
        };
        const Observer::CopiedLifecycleObservation startObservation =
            MakeStartObservation(true, true);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            startObservation,
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "context session_start did not create principal");
        Correlation::BindSessionStartCorrelation(registry, startObservation, start);
        RequireEventContext(start,
                            startContext.EventSequence,
                            startContext.ServerProcessEpoch,
                            "context session_start lost event sequence",
                            "context session_start lost server process epoch");

        const Applicator::ProcessLocalEventContext rejectedContext{
            .EventSequence = 102,
            .ServerProcessEpoch = 7,
        };
        const Applicator::ApplyResult rejected =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            MakeCheckJoinRejectedObservation(),
                                                            nullptr,
                                                            &rejectedContext);
        Require(rejected.Status == Applicator::ApplyStatus::SessionStartRejectedNoop,
                "context CheckJoinInProgress rejected session_start did not no-op");
        RequireNoRegistryPointer(rejected,
                                 "context CheckJoinInProgress rejected session_start exposed a registry pointer");
        RequireEventContext(rejected,
                            rejectedContext.EventSequence,
                            rejectedContext.ServerProcessEpoch,
                            "context CheckJoinInProgress rejected session_start lost event sequence",
                            "context CheckJoinInProgress rejected session_start lost server process epoch");

        const Applicator::ProcessLocalEventContext unresolvedEndContext{
            .EventSequence = 103,
            .ServerProcessEpoch = 7,
        };
        const Applicator::ApplyResult unresolvedEnd =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            MakeEndObservation(999),
                                                            nullptr,
                                                            &unresolvedEndContext);
        Require(unresolvedEnd.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "context uncorrelated session_end did not no-op");
        RequireNoRegistryPointer(unresolvedEnd,
                                 "context uncorrelated session_end exposed a registry pointer");
        RequireEventContext(unresolvedEnd,
                            unresolvedEndContext.EventSequence,
                            unresolvedEndContext.ServerProcessEpoch,
                            "context uncorrelated session_end lost event sequence",
                            "context uncorrelated session_end lost server process epoch");

        const Applicator::ProcessLocalEventContext endContext{
            .EventSequence = 104,
            .ServerProcessEpoch = 7,
        };
        const Observer::CopiedLifecycleObservation endObservation = MakeEndObservation(1);
        const Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation =
            RequireResolvedLogoutCorrelation(endObservation,
                                             "context session_end did not resolve private proof");
        const Applicator::ApplyResult end =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            endObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &endContext);
        Require(end.Status == Applicator::ApplyStatus::SessionEndInvalidated,
                "context correlated session_end did not invalidate principal");
        RequireRegistryPointer(end,
                               registry,
                               "context correlated session_end did not retain registry revalidation pointer");
        RequireEventContext(end,
                            endContext.EventSequence,
                            endContext.ServerProcessEpoch,
                            "context correlated session_end lost event sequence",
                            "context correlated session_end lost server process epoch");
    }

    void TestSuppliedEventContextDoesNotReachUnsupportedObservations()
    {
        const Applicator::ProcessLocalEventContext context{
            .EventSequence = 777,
            .ServerProcessEpoch = 44,
        };

        Obelisk::Core::PlayerPrincipalRegistry registry;
        Applicator::ApplyResult result =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            MakeDiagnosticObservation(),
                                                            nullptr,
                                                            &context);
        Require(result.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "diagnostic observation with context was accepted");
        RequireEventContext(result,
                            0,
                            0,
                            "unsupported diagnostic observation retained event sequence",
                            "unsupported diagnostic observation retained server process epoch");

        Observer::CopiedLifecycleObservation malformed = MakeStartObservation(true, false);
        malformed.Role = Observer::LifecycleRole::SessionStart;
        malformed.Action = Observer::PrincipalAction::CandidateCreated;
        result = Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                                 malformed,
                                                                 nullptr,
                                                                 &context);
        Require(result.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "malformed observation with context was accepted");
        RequireEventContext(result,
                            0,
                            0,
                            "malformed observation retained event sequence",
                            "malformed observation retained server process epoch");
        Require(registry.LiveCount() == 0, "unsupported observations with context changed registry");
    }

    void TestZeroEventContextDoesNotOpenUnsupportedObservations()
    {
        const Applicator::ProcessLocalEventContext zeroContext{};

        Obelisk::Core::PlayerPrincipalRegistry registry;
        Applicator::ApplyResult result =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            MakeDiagnosticObservation(),
                                                            nullptr,
                                                            &zeroContext);
        Require(result.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "diagnostic observation with zero context was accepted");
        Require(!result.RegistryChanged, "diagnostic observation with zero context changed registry");
        Require(!result.Principal.HasValidShape(),
                "diagnostic observation with zero context returned a principal");
        RequireEventContext(result,
                            0,
                            0,
                            "diagnostic observation with zero context retained event sequence",
                            "diagnostic observation with zero context retained server process epoch");

        Observer::CopiedLifecycleObservation malformed = MakeStartObservation(true, false);
        malformed.Role = Observer::LifecycleRole::SessionStart;
        malformed.Action = Observer::PrincipalAction::CandidateCreated;
        result = Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                                 malformed,
                                                                 nullptr,
                                                                 &zeroContext);
        Require(result.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "malformed observation with zero context was accepted");
        Require(!result.RegistryChanged, "malformed observation with zero context changed registry");
        Require(!result.Principal.HasValidShape(),
                "malformed observation with zero context returned a principal");
        RequireEventContext(result,
                            0,
                            0,
                            "malformed observation with zero context retained event sequence",
                            "malformed observation with zero context retained server process epoch");
        Require(registry.LiveCount() == 0,
                "unsupported observations with zero context changed registry live count");
    }

    void TestInternalDispatchBridgeSendsOnlySafeValidatedEvents()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        Correlation::ResetForTesting();
        auto& dispatcher = Obelisk::Core::PlayerPrincipalEventDispatcher::Get();
        int owner = 0;
        dispatcher.UnregisterCallbacksForOwner(&owner);

        DispatchCapture capture;
        const uint64_t registrationId = dispatcher.Register(&owner, {CaptureDispatch, &capture});
        Require(registrationId != 0, "internal dispatch bridge registration failed");

        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Applicator::ProcessLocalEventContext startContext{
            .EventSequence = 301,
            .ServerProcessEpoch = 10,
        };
        const Observer::CopiedLifecycleObservation startObservation =
            MakeStartObservation(true, true);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            startObservation,
                                                            nullptr,
                                                            &startContext);
        Correlation::BindSessionStartCorrelation(registry, startObservation, start);
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    start,
                    startObservation) == 1,
                "internal dispatch bridge did not dispatch accepted session_start");
        Require(capture.Calls == 1, "accepted session_start dispatch count mismatch");
        Require(capture.Kind == Obelisk::Core::PlayerPrincipalEventKind::SessionStart,
                "accepted session_start dispatch kind mismatch");
        Require(capture.Action == Obelisk::Core::PlayerPrincipalAction::CandidateCreated,
                "accepted session_start dispatch action mismatch");
        Require(capture.EventSequence == startContext.EventSequence,
                "accepted session_start dispatch lost event sequence");
        Require(capture.ServerProcessEpoch == startContext.ServerProcessEpoch,
                "accepted session_start dispatch lost server process epoch");
        Require(capture.BoolCount == 2, "accepted session_start dispatch bool count mismatch");

        const Applicator::ProcessLocalEventContext rejectedContext{
            .EventSequence = 302,
            .ServerProcessEpoch = 10,
        };
        const Applicator::ApplyResult rejected =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            MakeStartObservation(true, false),
                                                            nullptr,
                                                            &rejectedContext);
        Require(rejected.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "login-backed rejected session_start was treated as canonical evidence");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    rejected,
                    MakeStartObservation(true, false)) == 0,
                "internal dispatch bridge dispatched login-backed rejected session_start");
        Require(capture.Calls == 1,
                "login-backed rejected session_start reached internal dispatcher");

        const Applicator::ProcessLocalEventContext checkJoinRejectedContext{
            .EventSequence = 303,
            .ServerProcessEpoch = 10,
        };
        const Observer::CopiedLifecycleObservation checkJoinRejectedObservation =
            MakeCheckJoinRejectedObservation();
        const Applicator::ApplyResult checkJoinRejected =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            checkJoinRejectedObservation,
                                                            nullptr,
                                                            &checkJoinRejectedContext);
        Require(checkJoinRejected.Status == Applicator::ApplyStatus::SessionStartRejectedNoop,
                "CheckJoinInProgress rejected session_start did not no-op");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    checkJoinRejected,
                    checkJoinRejectedObservation) == 1,
                "internal dispatch bridge did not dispatch CheckJoinInProgress rejected session_start");
        Require(capture.Calls == 2, "CheckJoinInProgress rejected session_start dispatch count mismatch");
        Require(capture.Kind == Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected,
                "CheckJoinInProgress rejected session_start dispatch kind mismatch");
        Require(capture.Action == Obelisk::Core::PlayerPrincipalAction::None,
                "CheckJoinInProgress rejected session_start dispatch action mismatch");
        Require(capture.EventSequence == checkJoinRejectedContext.EventSequence,
                "CheckJoinInProgress rejected session_start dispatch lost event sequence");
        Require(capture.ServerProcessEpoch == checkJoinRejectedContext.ServerProcessEpoch,
                "CheckJoinInProgress rejected session_start dispatch lost server process epoch");
        Require(capture.BoolCount == 2,
                "CheckJoinInProgress rejected session_start dispatch bool count mismatch");

        const Applicator::ProcessLocalEventContext unresolvedContext{
            .EventSequence = 304,
            .ServerProcessEpoch = 10,
        };
        const Applicator::ApplyResult unresolved =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            MakeEndObservation(999),
                                                            nullptr,
                                                            &unresolvedContext);
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    unresolved,
                    MakeEndObservation(999)) == 0,
                "internal dispatch bridge dispatched unresolved session_end");
        Require(capture.Calls == 2, "unresolved session_end reached internal dispatcher");

        const Applicator::ProcessLocalEventContext endContext{
            .EventSequence = 305,
            .ServerProcessEpoch = 10,
        };
        const Observer::CopiedLifecycleObservation endObservation = MakeEndObservation(1);
        const Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation =
            RequireResolvedLogoutCorrelation(endObservation,
                                             "internal dispatch bridge did not resolve logout proof");
        const Applicator::ApplyResult end =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            endObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &endContext);
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    end,
                    endObservation) == 1,
                "internal dispatch bridge did not dispatch correlated session_end");
        Require(capture.Calls == 3, "correlated session_end dispatch count mismatch");
        Require(capture.Kind == Obelisk::Core::PlayerPrincipalEventKind::SessionEnd,
                "correlated session_end dispatch kind mismatch");
        Require(capture.Action == Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated,
                "correlated session_end dispatch action mismatch");
        Require(capture.EventSequence == endContext.EventSequence,
                "correlated session_end dispatch lost event sequence");
        Require(capture.ServerProcessEpoch == endContext.ServerProcessEpoch,
                "correlated session_end dispatch lost server process epoch");
        Require(capture.BoolCount == 0, "correlated session_end dispatch bool count mismatch");

        const Applicator::ProcessLocalEventContext duplicateContext{
            .EventSequence = 306,
            .ServerProcessEpoch = 10,
        };
        const Applicator::ApplyResult duplicate =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            endObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &duplicateContext);
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    duplicate,
                    endObservation) == 0,
                "internal dispatch bridge dispatched duplicate session_end");
        Require(capture.Calls == 3, "duplicate session_end reached internal dispatcher");

        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 1,
                "internal dispatch bridge cleanup removed wrong callback count");
    }

    void TestSessionEndDispatchRequiresCorrelationAndNonzeroContext()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        Correlation::ResetForTesting();
        auto& dispatcher = Obelisk::Core::PlayerPrincipalEventDispatcher::Get();
        int owner = 0;
        dispatcher.UnregisterCallbacksForOwner(&owner);

        DispatchCapture capture;
        const uint64_t registrationId = dispatcher.Register(&owner, {CaptureDispatch, &capture});
        Require(registrationId != 0, "session_end dispatch edge registration failed");

        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Applicator::ProcessLocalEventContext startContext{
            .EventSequence = 500,
            .ServerProcessEpoch = 12,
        };
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            MakeStartObservation(true, true),
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "session_end dispatch edge fixture did not create principal");

        const Applicator::ProcessLocalEventContext unresolvedContext{
            .EventSequence = 501,
            .ServerProcessEpoch = 12,
        };
        const Applicator::ApplyResult unresolved =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            MakeEndObservation(999),
                                                            nullptr,
                                                            &unresolvedContext);
        Require(unresolved.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "unresolved logout did not no-op");
        Require(!unresolved.RegistryChanged, "unresolved logout changed registry");
        Require(registry.Validate(start.Principal),
                "unresolved logout invalidated live principal");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    unresolved,
                    MakeEndObservation(999)) == 0,
                "unresolved logout reached internal dispatcher");
        Require(capture.Calls == 0, "unresolved logout reached subscriber");

        const Applicator::ApplyResult zeroContextEnd =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            MakeEndObservation(1),
                                                            &start.Principal);
        Require(zeroContextEnd.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "zero-context correlated logout did not fail closed");
        Require(!zeroContextEnd.RegistryChanged,
                "zero-context correlated logout changed registry");
        Require(!zeroContextEnd.Principal.HasValidShape(),
                "zero-context correlated logout returned a principal without proof context");
        Require(registry.Validate(start.Principal),
                "zero-context correlated logout invalidated live principal");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    zeroContextEnd,
                    MakeEndObservation(1)) == 0,
                "zero-context correlated logout reached internal dispatcher");
        Require(capture.Calls == 0, "zero-context correlated logout reached subscriber");

        const Applicator::ProcessLocalEventContext zeroEpochStartContext{
            .EventSequence = 502,
            .ServerProcessEpoch = 12,
        };
        const Applicator::ApplyResult zeroEpochStart =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            MakeStartObservation(true, true),
                                                            nullptr,
                                                            &zeroEpochStartContext);
        Require(zeroEpochStart.Status == Applicator::ApplyStatus::SessionStartCreated,
                "zero-epoch logout fixture did not create principal");
        const Applicator::ProcessLocalEventContext zeroEpochContext{
            .EventSequence = 503,
            .ServerProcessEpoch = 0,
        };
        const Applicator::ApplyResult zeroEpochEnd =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            MakeEndObservation(1),
                                                            &zeroEpochStart.Principal,
                                                            &zeroEpochContext);
        Require(zeroEpochEnd.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "zero-epoch correlated logout did not fail closed");
        Require(!zeroEpochEnd.RegistryChanged,
                "zero-epoch correlated logout changed registry");
        Require(!zeroEpochEnd.Principal.HasValidShape(),
                "zero-epoch correlated logout returned a principal without full proof context");
        Require(registry.Validate(zeroEpochStart.Principal),
                "zero-epoch correlated logout invalidated live principal");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    zeroEpochEnd,
                    MakeEndObservation(1)) == 0,
                "zero-epoch correlated logout reached internal dispatcher");
        Require(capture.Calls == 0, "zero-epoch correlated logout reached subscriber");

        const Applicator::ProcessLocalEventContext zeroSequenceStartContext{
            .EventSequence = 504,
            .ServerProcessEpoch = 12,
        };
        const Applicator::ApplyResult zeroSequenceStart =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            MakeStartObservation(true, true),
                                                            nullptr,
                                                            &zeroSequenceStartContext);
        Require(zeroSequenceStart.Status == Applicator::ApplyStatus::SessionStartCreated,
                "zero-sequence logout fixture did not create principal");
        const Applicator::ProcessLocalEventContext zeroSequenceContext{
            .EventSequence = 0,
            .ServerProcessEpoch = 12,
        };
        const Applicator::ApplyResult zeroSequenceEnd =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            MakeEndObservation(1),
                                                            &zeroSequenceStart.Principal,
                                                            &zeroSequenceContext);
        Require(zeroSequenceEnd.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "zero-sequence correlated logout did not fail closed");
        Require(!zeroSequenceEnd.RegistryChanged,
                "zero-sequence correlated logout changed registry");
        Require(!zeroSequenceEnd.Principal.HasValidShape(),
                "zero-sequence correlated logout returned a principal without full proof context");
        Require(registry.Validate(zeroSequenceStart.Principal),
                "zero-sequence correlated logout invalidated live principal");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    zeroSequenceEnd,
                    MakeEndObservation(1)) == 0,
                "zero-sequence correlated logout reached internal dispatcher");
        Require(capture.Calls == 0, "zero-sequence correlated logout reached subscriber");

        const Observer::CopiedLifecycleObservation validStartObservation =
            MakeStartObservation(true, true, 404);
        const Applicator::ProcessLocalEventContext validStartContext{
            .EventSequence = 505,
            .ServerProcessEpoch = 12,
        };
        const Applicator::ApplyResult validStart =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            validStartObservation,
                                                            nullptr,
                                                            &validStartContext);
        Require(validStart.Status == Applicator::ApplyStatus::SessionStartCreated,
                "valid logout fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, validStartObservation, validStart);
        const Applicator::ProcessLocalEventContext validContext{
            .EventSequence = 506,
            .ServerProcessEpoch = 12,
        };
        const Observer::CopiedLifecycleObservation validEndObservation = MakeEndObservation(404);
        const Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation =
            RequireResolvedLogoutCorrelation(validEndObservation,
                                             "valid logout fixture did not resolve private proof");
        const Applicator::ApplyResult validEnd =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            validEndObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &validContext);
        Require(validEnd.Status == Applicator::ApplyStatus::SessionEndInvalidated,
                "valid correlated logout did not invalidate");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    validEnd,
                    validEndObservation) == 1,
                "valid correlated logout did not reach internal dispatcher");
        Require(capture.Calls == 1, "valid correlated logout dispatch count mismatch");
        Require(capture.Kind == Obelisk::Core::PlayerPrincipalEventKind::SessionEnd,
                "valid correlated logout dispatch kind mismatch");
        Require(capture.Action == Obelisk::Core::PlayerPrincipalAction::CandidateInvalidated,
                "valid correlated logout dispatch action mismatch");
        Require(capture.EventSequence == validContext.EventSequence,
                "valid correlated logout dispatch lost event sequence");
        Require(capture.ServerProcessEpoch == validContext.ServerProcessEpoch,
                "valid correlated logout dispatch lost server process epoch");
        Require(capture.BoolCount == 0, "valid correlated logout dispatch bool count mismatch");

        const Applicator::ProcessLocalEventContext duplicateContext{
            .EventSequence = 507,
            .ServerProcessEpoch = 12,
        };
        const Applicator::ApplyResult duplicate =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            validEndObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &duplicateContext);
        Require(duplicate.Status == Applicator::ApplyStatus::SessionEndDuplicateNoop,
                "duplicate correlated logout did not no-op");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    duplicate,
                    validEndObservation) == 0,
                "duplicate correlated logout reached internal dispatcher");
        Require(capture.Calls == 1, "duplicate correlated logout reached subscriber");

        Correlation::ResetForTesting();
        const Observer::CopiedLifecycleObservation staleStartObservation =
            MakeStartObservation(true, true, 405);
        const Applicator::ProcessLocalEventContext staleStartContext{
            .EventSequence = 508,
            .ServerProcessEpoch = 12,
        };
        const Applicator::ApplyResult staleStart =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            staleStartObservation,
                                                            nullptr,
                                                            &staleStartContext);
        Require(staleStart.Status == Applicator::ApplyStatus::SessionStartCreated,
                "dispatch stale fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry,
                                                 staleStartObservation,
                                                 staleStart);
        const Observer::CopiedLifecycleObservation staleEndObservation =
            MakeEndObservation(405);
        const Obelisk::Core::PlayerPrincipalToken staleResolvedLogoutCorrelation =
            RequireResolvedLogoutCorrelation(staleEndObservation,
                                             "dispatch stale fixture did not resolve private proof");
        const Obelisk::Core::PlayerPrincipalToken reactivated =
            InvalidateForReconnectAndReactivate(
                registry,
                staleStart.Principal,
                "dispatch stale fixture reconnect invalidation failed",
                "stale logout reactivation fixture failed");
        const Applicator::ProcessLocalEventContext staleContext{
            .EventSequence = 509,
            .ServerProcessEpoch = 12,
        };
        const Applicator::ApplyResult stale =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            staleEndObservation,
                                                            &staleResolvedLogoutCorrelation,
                                                            &staleContext);
        Require(stale.Status == Applicator::ApplyStatus::SessionEndStaleNoop,
                "stale correlated logout did not no-op");
        Require(!stale.RegistryChanged, "stale correlated logout changed registry");
        Require(registry.Validate(reactivated),
                "stale correlated logout invalidated current generation");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    stale,
                    staleEndObservation) == 0,
                "stale correlated logout reached internal dispatcher");
        Require(capture.Calls == 1, "stale correlated logout reached subscriber");

        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 1,
                "session_end dispatch edge cleanup removed wrong callback count");
    }

    void TestApprovedRuntimeEvidenceLogGateSkipsUnmatchedLogoutUntilMatched()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;
        std::atomic<uint64_t> counter{0};
        std::atomic<uint32_t> roleMask{0};
        constexpr uint64_t logLimit = 3;
        uint64_t observationNumber = 99;

        const Observer::CopiedLifecycleObservation startObservation =
            MakeStartObservation(true, true, 701);
        const Applicator::ProcessLocalEventContext startContext = ProofContext(701);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            startObservation,
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "approved evidence gate fixture did not create session_start");
        Require(Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    startObservation,
                    nullptr,
                    start),
                "safe session_start was not loggable for approved runtime evidence");
        Require(Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    startObservation,
                    logLimit,
                    observationNumber),
                "safe session_start did not reserve approved evidence log slot");
        Require(observationNumber == 1,
                "safe session_start reserved wrong approved evidence sequence");
        Correlation::BindSessionStartCorrelation(registry, startObservation, start);

        const Observer::CopiedLifecycleObservation unrelatedLogoutObservation =
            MakeEndObservation(702);
        Require(Observer::ApprovedRuntimeEvidenceLogRoleMask(unrelatedLogoutObservation) == (1u << 2),
                "canonical but unmatched logout did not expose the session_end role risk");
        const Applicator::ProcessLocalEventContext unrelatedLogoutContext = ProofContext(702);
        const Applicator::ApplyResult unrelatedLogout =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            unrelatedLogoutObservation,
                                                            nullptr,
                                                            &unrelatedLogoutContext);
        Require(unrelatedLogout.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "unmatched logout did not fail closed before approved evidence logging");
        Require(!Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    unrelatedLogoutObservation,
                    nullptr,
                    unrelatedLogout),
                "unmatched logout was loggable as approved runtime evidence");
        Require(counter.load(std::memory_order_relaxed) == 1,
                "unmatched logout consumed approved evidence log budget");
        Require(roleMask.load(std::memory_order_relaxed) == (1u << 0),
                "unmatched logout reserved the session_end approved evidence role");

        const Observer::CopiedLifecycleObservation rejectedObservation =
            MakeCheckJoinRejectedObservation();
        const Applicator::ProcessLocalEventContext rejectedContext = ProofContext(703);
        const Applicator::ApplyResult rejected =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            rejectedObservation,
                                                            nullptr,
                                                            &rejectedContext);
        Require(rejected.Status == Applicator::ApplyStatus::SessionStartRejectedNoop,
                "CheckJoinInProgress rejected fixture did not no-op");
        Require(Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    rejectedObservation,
                    nullptr,
                    rejected),
                "safe CheckJoinInProgress rejected event was not approved-evidence loggable");
        observationNumber = 99;
        Require(Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    rejectedObservation,
                    logLimit,
                    observationNumber),
                "safe CheckJoinInProgress rejected event did not reserve approved log slot");
        Require(observationNumber == 2,
                "safe CheckJoinInProgress rejected event reserved wrong approved evidence sequence");

        const Observer::CopiedLifecycleObservation matchedLogoutObservation =
            MakeEndObservation(701);
        const Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation =
            RequireResolvedLogoutCorrelation(matchedLogoutObservation,
                                             "matched logout did not resolve after skipped unmatched logout");
        const Applicator::ProcessLocalEventContext matchedLogoutContext = ProofContext(704);
        const Applicator::ApplyResult matchedLogout =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            matchedLogoutObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &matchedLogoutContext);
        Correlation::ClearSessionEndCorrelation(matchedLogoutObservation, matchedLogout);
        Require(matchedLogout.Status == Applicator::ApplyStatus::SessionEndInvalidated,
                "matched logout did not invalidate after skipped unmatched logout");
        Require(Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    matchedLogoutObservation,
                    &resolvedLogoutCorrelation,
                    matchedLogout),
                "matched logout was not approved-evidence loggable");
        observationNumber = 99;
        Require(Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    matchedLogoutObservation,
                    logLimit,
                    observationNumber),
                "matched logout did not reserve the preserved session_end log slot");
        Require(observationNumber == 3,
                "matched logout reserved wrong approved evidence sequence");
        Require(counter.load(std::memory_order_relaxed) == 3,
                "approved evidence triplet did not consume exactly three log slots");
        Require(roleMask.load(std::memory_order_relaxed) == ((1u << 0) | (1u << 1) | (1u << 2)),
                "approved evidence triplet did not reserve all exact role bits");

        Correlation::ResetForTesting();
    }

    void TestApprovedRuntimeEvidenceLogGateDoesNotCompleteTripletWithoutRejectedStart()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;
        std::atomic<uint64_t> counter{0};
        std::atomic<uint32_t> roleMask{0};
        constexpr uint64_t logLimit = 3;
        uint64_t observationNumber = 99;

        const Observer::CopiedLifecycleObservation startObservation =
            MakeStartObservation(true, true, 720);
        const Applicator::ProcessLocalEventContext startContext = ProofContext(720);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            startObservation,
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "start/end subset fixture did not create session_start");
        Require(start.ValidatedLifecycleEvent,
                "start/end subset fixture did not stamp session_start validation");
        Require(Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    startObservation,
                    nullptr,
                    start),
                "start/end subset session_start was not individually loggable");
        Require(Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    startObservation,
                    logLimit,
                    observationNumber),
                "start/end subset session_start did not reserve approved evidence log slot");
        Require(counter.load(std::memory_order_relaxed) == 1,
                "start/end subset session_start consumed wrong log budget");
        Require(roleMask.load(std::memory_order_relaxed) == (1u << 0),
                "start/end subset session_start reserved wrong role bit");
        Correlation::BindSessionStartCorrelation(registry, startObservation, start);

        const Observer::CopiedLifecycleObservation endObservation = MakeEndObservation(720);
        const Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation =
            RequireResolvedLogoutCorrelation(endObservation,
                                             "start/end subset matched logout did not resolve");
        const Applicator::ProcessLocalEventContext endContext = ProofContext(721);
        const Applicator::ApplyResult end =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            endObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &endContext);
        Correlation::ClearSessionEndCorrelation(endObservation, end);
        Require(end.Status == Applicator::ApplyStatus::SessionEndInvalidated,
                "start/end subset matched logout did not invalidate");
        Require(end.ValidatedLifecycleEvent,
                "start/end subset fixture did not stamp session_end validation");
        Require(!registry.Validate(start.Principal),
                "start/end subset matched logout did not invalidate the start principal");
        Require(Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    endObservation,
                    &resolvedLogoutCorrelation,
                    end),
                "start/end subset matched session_end was not individually loggable");
        observationNumber = 99;
        Require(Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    endObservation,
                    logLimit,
                    observationNumber),
                "start/end subset matched session_end did not reserve approved evidence log slot");
        Require(observationNumber == 2,
                "start/end subset matched session_end reserved wrong sequence");

        Require(counter.load(std::memory_order_relaxed) == 2,
                "start/end subset consumed more than two approved evidence log slots");
        Require(roleMask.load(std::memory_order_relaxed) == ((1u << 0) | (1u << 2)),
                "start/end subset reserved unexpected approved evidence role bits");
        Require((roleMask.load(std::memory_order_relaxed) & (1u << 1)) == 0,
                "start/end subset inferred the missing CheckJoinInProgress rejected-start role");
        Require(roleMask.load(std::memory_order_relaxed) !=
                    ((1u << 0) | (1u << 1) | (1u << 2)),
                "start/end subset was indistinguishable from the complete approved triplet");

        Correlation::ResetForTesting();
    }

    void TestRejectedStartAndUnresolvedLogoutDoNotCompleteTripletWithoutSessionStart()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;
        std::atomic<uint64_t> counter{0};
        std::atomic<uint32_t> roleMask{0};
        constexpr uint64_t logLimit = 3;
        uint64_t observationNumber = 99;

        const Observer::CopiedLifecycleObservation rejectedObservation =
            MakeCheckJoinRejectedObservation();
        const Applicator::ProcessLocalEventContext rejectedContext = ProofContext(730);
        const Applicator::ApplyResult rejected =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            rejectedObservation,
                                                            nullptr,
                                                            &rejectedContext);
        Require(rejected.Status == Applicator::ApplyStatus::SessionStartRejectedNoop,
                "rejected/start-end subset CheckJoinInProgress did not no-op");
        Require(!rejected.RegistryChanged,
                "rejected/start-end subset CheckJoinInProgress changed the registry");
        RequireNoRegistryPointer(rejected,
                                 "rejected/start-end subset CheckJoinInProgress exposed registry pointer");
        Require(rejected.ValidatedLifecycleEvent,
                "rejected/start-end subset CheckJoinInProgress lost validation stamp");
        Require(registry.LiveCount() == 0,
                "rejected/start-end subset CheckJoinInProgress allocated a principal");
        Correlation::BindSessionStartCorrelation(registry, rejectedObservation, rejected);
        Require(Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    rejectedObservation,
                    nullptr,
                    rejected),
                "rejected/start-end subset CheckJoinInProgress was not individually loggable");
        Require(Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    rejectedObservation,
                    logLimit,
                    observationNumber),
                "rejected/start-end subset CheckJoinInProgress did not reserve rejected-start slot");
        Require(counter.load(std::memory_order_relaxed) == 1,
                "rejected/start-end subset consumed wrong log budget after CheckJoin");
        Require(roleMask.load(std::memory_order_relaxed) == (1u << 1),
                "rejected/start-end subset CheckJoin reserved wrong role bit");

        const Observer::CopiedLifecycleObservation unresolvedEndObservation = MakeEndObservation(730);
        Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation;
        Require(!Correlation::TryResolveLogoutCorrelation(unresolvedEndObservation,
                                                          resolvedLogoutCorrelation),
                "rejected/start-end subset logout unexpectedly resolved without session_start");
        const Applicator::ProcessLocalEventContext endContext = ProofContext(731);
        const Applicator::ApplyResult unresolvedEnd =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            unresolvedEndObservation,
                                                            nullptr,
                                                            &endContext);
        Require(unresolvedEnd.Status == Applicator::ApplyStatus::SessionEndUnresolvedNoop,
                "rejected/start-end subset unresolved logout did not no-op");
        Require(!unresolvedEnd.RegistryChanged,
                "rejected/start-end subset unresolved logout changed registry");
        RequireNoRegistryPointer(unresolvedEnd,
                                 "rejected/start-end subset unresolved logout exposed registry pointer");
        Require(unresolvedEnd.ValidatedLifecycleEvent == false,
                "rejected/start-end subset unresolved logout was stamped as validated");
        Require(!unresolvedEnd.Principal.HasValidShape(),
                "rejected/start-end subset unresolved logout returned a principal token");
        Require(!Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    unresolvedEndObservation,
                    nullptr,
                    unresolvedEnd),
                "rejected/start-end subset unresolved logout was approved-evidence loggable");
        Require(counter.load(std::memory_order_relaxed) == 1,
                "rejected/start-end subset unresolved logout consumed log budget");
        Require(roleMask.load(std::memory_order_relaxed) == (1u << 1),
                "rejected/start-end subset unresolved logout changed approved evidence role bits");
        Require((roleMask.load(std::memory_order_relaxed) & (1u << 0)) == 0,
                "rejected/start-end subset inferred the missing HandleNewPlayer session_start role");
        Require((roleMask.load(std::memory_order_relaxed) & (1u << 2)) == 0,
                "rejected/start-end subset inferred a matched session_end role");
        Require(roleMask.load(std::memory_order_relaxed) !=
                    ((1u << 0) | (1u << 1) | (1u << 2)),
                "rejected/start-end subset was indistinguishable from the complete approved triplet");

        Correlation::ResetForTesting();
    }

    void TestApprovedRuntimeEvidenceLogGateRejectsUnsafeCorrelationState()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        Correlation::ResetForTesting();
        Obelisk::Core::PlayerPrincipalRegistry registry;

        const Observer::CopiedLifecycleObservation failedBindStartObservation =
            MakeStartObservation(true, true, 710);
        const Applicator::ProcessLocalEventContext failedBindStartContext =
            ProofContext(710);
        const Applicator::ApplyResult failedBindStart =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            failedBindStartObservation,
                                                            nullptr,
                                                            &failedBindStartContext);
        Require(failedBindStart.Status == Applicator::ApplyStatus::SessionStartCreated,
                "failed-bind evidence fixture did not create a principal");
        Correlation::FailNextBindForTesting();
        Correlation::BindSessionStartCorrelation(registry,
                                                 failedBindStartObservation,
                                                 failedBindStart);
        Require(!registry.Validate(failedBindStart.Principal),
                "failed bind did not invalidate the uncorrelatable start principal");
        Require(!Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    failedBindStartObservation,
                    nullptr,
                    failedBindStart),
                "correlation-invalidated session_start was loggable as approved evidence");

        const Observer::CopiedLifecycleObservation validStartObservation =
            MakeStartObservation(true, true, 711);
        const Applicator::ProcessLocalEventContext validStartContext = ProofContext(711);
        const Applicator::ApplyResult validStart =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            validStartObservation,
                                                            nullptr,
                                                            &validStartContext);
        Require(validStart.Status == Applicator::ApplyStatus::SessionStartCreated,
                "mismatched-correlation evidence fixture did not create a principal");
        Correlation::BindSessionStartCorrelation(registry,
                                                 validStartObservation,
                                                 validStart);

        const Observer::CopiedLifecycleObservation validLogoutObservation =
            MakeEndObservation(711);
        const Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation =
            RequireResolvedLogoutCorrelation(
                validLogoutObservation,
                "mismatched-correlation fixture did not resolve logout proof");
        const Applicator::ProcessLocalEventContext validLogoutContext = ProofContext(712);
        const Applicator::ApplyResult validLogout =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            validLogoutObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &validLogoutContext);
        Correlation::ClearSessionEndCorrelation(validLogoutObservation, validLogout);
        Require(validLogout.Status == Applicator::ApplyStatus::SessionEndInvalidated,
                "mismatched-correlation fixture did not invalidate logout");
        Require(validLogout.MatchedLogoutCorrelation,
                "matched logout did not retain matched-correlation apply proof");

        Applicator::ApplyResult strippedCorrelationProof = validLogout;
        strippedCorrelationProof.MatchedLogoutCorrelation = false;
        Require(!Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    validLogoutObservation,
                    &resolvedLogoutCorrelation,
                    strippedCorrelationProof),
                "session_end with stripped matched-correlation proof was loggable");

        Obelisk::Core::PlayerPrincipalRegistry unrelatedRegistry;
        const Obelisk::Core::PlayerPrincipalToken unrelatedCorrelation =
            unrelatedRegistry.AllocatePrincipal();
        Require(unrelatedCorrelation.HasValidShape(),
                "mismatched-correlation fixture did not allocate unrelated principal");
        Require(!Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    validLogoutObservation,
                    &unrelatedCorrelation,
                    validLogout),
                "session_end with unrelated correlation token was loggable as approved evidence");
        Require(Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    validLogoutObservation,
                    &resolvedLogoutCorrelation,
                    validLogout),
                "session_end with exact matched correlation token was not loggable");

        Correlation::ResetForTesting();
    }

    void TestInternalDispatchBridgeRequiresNonzeroContextAndValidShape()
    {
        auto& dispatcher = Obelisk::Core::PlayerPrincipalEventDispatcher::Get();
        int owner = 0;
        dispatcher.UnregisterCallbacksForOwner(&owner);

        DispatchCapture capture;
        const uint64_t registrationId = dispatcher.Register(&owner, {CaptureDispatch, &capture});
        Require(registrationId != 0, "internal dispatch bridge guard registration failed");

        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Applicator::ApplyResult zeroContext =
            Applicator::ApplyLifecycleObservationToRegistry(registry, MakeStartObservation(true, true));
        Require(zeroContext.Status == Applicator::ApplyStatus::UnsupportedObservation,
                "internal dispatch bridge guard accepted zero-context session_start");
        Require(!zeroContext.RegistryChanged,
                "internal dispatch bridge guard zero-context session_start changed registry");
        Require(!zeroContext.Principal.HasValidShape(),
                "internal dispatch bridge guard zero-context session_start returned a principal");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    zeroContext,
                    MakeStartObservation(true, true)) == 0,
                "internal dispatch bridge dispatched zero-context session_start");

        Observer::CopiedLifecycleObservation malformed = MakeStartObservation(true, false);
        malformed.Role = Observer::LifecycleRole::SessionStart;
        malformed.Action = Observer::PrincipalAction::CandidateCreated;
        const Applicator::ApplyResult fakeAccepted{
            .Status = Applicator::ApplyStatus::SessionStartCreated,
            .EventSequence = 401,
            .ServerProcessEpoch = 11,
        };
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    fakeAccepted,
                    malformed) == 0,
                "internal dispatch bridge dispatched malformed observation");

        const Applicator::ApplyResult unsupported{
            .Status = Applicator::ApplyStatus::UnsupportedObservation,
            .EventSequence = 402,
            .ServerProcessEpoch = 11,
        };
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    unsupported,
                    MakeStartObservation(true, true)) == 0,
                "internal dispatch bridge dispatched unsupported apply status");

        const Applicator::ApplyResult fakeCreatedWithoutPrincipal{
            .Status = Applicator::ApplyStatus::SessionStartCreated,
            .EventSequence = 403,
            .ServerProcessEpoch = 11,
            .RegistryChanged = true,
            .PrincipalLive = true,
        };
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    fakeCreatedWithoutPrincipal,
                    MakeStartObservation(true, true)) == 0,
                "internal dispatch bridge dispatched accepted start without a principal");

        const Applicator::ApplyResult fakeEndWithoutPrincipal{
            .Status = Applicator::ApplyStatus::SessionEndInvalidated,
            .InvalidationReasons = Obelisk::Core::PlayerPrincipalInvalidationFlag(
                Obelisk::Core::PlayerPrincipalInvalidationReason::Logout),
            .EventSequence = 404,
            .ServerProcessEpoch = 11,
            .RegistryChanged = true,
        };
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    fakeEndWithoutPrincipal,
                    MakeEndObservation(1)) == 0,
                "internal dispatch bridge dispatched accepted logout without a principal");

        const Applicator::ApplyResult fakeEndWithExtraReason{
            .Status = Applicator::ApplyStatus::SessionEndInvalidated,
            .Principal = zeroContext.Principal,
            .InvalidationReasons = Obelisk::Core::PlayerPrincipalInvalidationFlag(
                    Obelisk::Core::PlayerPrincipalInvalidationReason::Logout) |
                Obelisk::Core::PlayerPrincipalInvalidationFlag(
                    Obelisk::Core::PlayerPrincipalInvalidationReason::RuntimeReset),
            .EventSequence = 405,
            .ServerProcessEpoch = 11,
            .RegistryChanged = true,
        };
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    fakeEndWithExtraReason,
                    MakeEndObservation(1)) == 0,
                "internal dispatch bridge dispatched logout with extra invalidation reason");

        const Applicator::ApplyResult fakeCreatedWithMalformedTokens{
            .Status = Applicator::ApplyStatus::SessionStartCreated,
            .Principal = zeroContext.Principal,
            .EventSequence = 406,
            .ServerProcessEpoch = 11,
            .RegistryChanged = true,
            .PrincipalLive = true,
        };
        Observer::CopiedLifecycleObservation extraTokenStart = MakeStartObservation(true, true);
        extraTokenStart.RedactedProcessLocalSubjectTokens[1] = 2;
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    fakeCreatedWithMalformedTokens,
                    extraTokenStart) == 0,
                "internal dispatch bridge dispatched accepted start with extra private token");

        const Observer::CopiedLifecycleObservation acceptedObservation =
            MakeStartObservation(true, true, 407);
        const Applicator::ProcessLocalEventContext acceptedContext{
            .EventSequence = 407,
            .ServerProcessEpoch = 11,
        };
        const Applicator::ApplyResult accepted =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            acceptedObservation,
                                                            nullptr,
                                                            &acceptedContext);
        Require(accepted.Status == Applicator::ApplyStatus::SessionStartCreated,
                "internal dispatch bridge malformed-bool fixture did not create a principal");

        Observer::CopiedLifecycleObservation malformedAcceptedBools = acceptedObservation;
        malformedAcceptedBools.BoolStorage[0].Field = Reflection::LifecycleField::ReturnValue;
        malformedAcceptedBools.BoolStorage[1].Field = Reflection::LifecycleField::BIsFromLogin;
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    accepted,
                    malformedAcceptedBools) == 0,
                "internal dispatch bridge dispatched accepted start with malformed bool order");

        const Applicator::ApplyResult fakeRejected{
            .Status = Applicator::ApplyStatus::SessionStartRejectedNoop,
            .EventSequence = 408,
            .ServerProcessEpoch = 11,
        };
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    fakeRejected,
                    MakeCheckJoinRejectedObservation()) == 0,
                "internal dispatch bridge dispatched forged rejected start without applicator validation");

        Observer::CopiedLifecycleObservation extraTokenRejected =
            MakeCheckJoinRejectedObservation();
        extraTokenRejected.RedactedProcessLocalSubjectTokens[1] = 3;
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    fakeRejected,
                    extraTokenRejected) == 0,
                "internal dispatch bridge dispatched rejected start with unused private token");

        Require(capture.Calls == 0,
                "internal dispatch bridge guard let invalid event reach callback");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 1,
                "internal dispatch bridge guard cleanup removed wrong callback count");
    }

    void TestInternalDispatchAndLogGateRequireApplyValidationStamp()
    {
        auto& dispatcher = Obelisk::Core::PlayerPrincipalEventDispatcher::Get();
        int owner = 0;
        dispatcher.UnregisterCallbacksForOwner(&owner);

        DispatchCapture capture;
        const uint64_t registrationId = dispatcher.Register(&owner, {CaptureDispatch, &capture});
        Require(registrationId != 0, "apply validation stamp guard registration failed");

        Obelisk::Core::PlayerPrincipalRegistry registry;

        const Observer::CopiedLifecycleObservation startObservation =
            MakeStartObservation(true, true, 904);
        const Applicator::ProcessLocalEventContext startContext = ProofContext(904, 17);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            startObservation,
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "apply validation stamp start fixture did not create principal");
        Require(start.ValidatedLifecycleEvent, "start fixture did not mark validated lifecycle event");
        Require(start.ValidationStamp != 0, "start fixture did not carry apply validation stamp");
        Require(Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    startObservation,
                    nullptr,
                    start),
                "stamped start was not loggable");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    start,
                    startObservation) == 1,
                "stamped start did not dispatch");
        Require(capture.Calls == 1, "stamped start dispatch count mismatch");

        Applicator::ApplyResult forgedStart = start;
        forgedStart.ValidationStamp = 0;
        Require(!Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    startObservation,
                    nullptr,
                    forgedStart),
                "start with stripped apply validation stamp was loggable");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    forgedStart,
                    startObservation) == 0,
                "start with stripped apply validation stamp dispatched");
        Require(capture.Calls == 1, "stripped-stamp start reached subscriber");

        forgedStart = start;
        ++forgedStart.EventSequence;
        Require(!Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    startObservation,
                    nullptr,
                    forgedStart),
                "start with mismatched apply validation stamp was loggable");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    forgedStart,
                    startObservation) == 0,
                "start with mismatched apply validation stamp dispatched");
        Require(capture.Calls == 1, "mismatched-stamp start reached subscriber");

        const Observer::CopiedLifecycleObservation rejectedObservation =
            MakeCheckJoinRejectedObservation();
        const Applicator::ProcessLocalEventContext rejectedContext = ProofContext(905, 17);
        const Applicator::ApplyResult rejected =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            rejectedObservation,
                                                            nullptr,
                                                            &rejectedContext);
        Require(rejected.Status == Applicator::ApplyStatus::SessionStartRejectedNoop,
                "apply validation stamp rejected fixture did not no-op");
        Require(rejected.ValidatedLifecycleEvent,
                "rejected fixture did not mark validated lifecycle event");
        Require(rejected.ValidationStamp != 0,
                "rejected fixture did not carry apply validation stamp");
        Require(Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    rejectedObservation,
                    nullptr,
                    rejected),
                "stamped CheckJoinInProgress rejected event was not loggable");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    rejected,
                    rejectedObservation) == 1,
                "stamped CheckJoinInProgress rejected event did not dispatch");
        Require(capture.Calls == 2, "stamped rejected dispatch count mismatch");

        const Applicator::ApplyResult forgedRejected{
            .Status = Applicator::ApplyStatus::SessionStartRejectedNoop,
            .EventSequence = 905,
            .ServerProcessEpoch = 17,
            .ValidatedLifecycleEvent = true,
        };
        Require(!Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    rejectedObservation,
                    nullptr,
                    forgedRejected),
                "forged CheckJoinInProgress rejected apply result was loggable");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    forgedRejected,
                    rejectedObservation) == 0,
                "forged CheckJoinInProgress rejected apply result dispatched");
        Require(capture.Calls == 2, "forged rejected result reached subscriber");

        Applicator::ApplyResult strippedRejected = rejected;
        strippedRejected.ValidationStamp = 0;
        Require(!Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    rejectedObservation,
                    nullptr,
                    strippedRejected),
                "CheckJoinInProgress rejected result with stripped stamp was loggable");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    strippedRejected,
                    rejectedObservation) == 0,
                "CheckJoinInProgress rejected result with stripped stamp dispatched");
        Require(capture.Calls == 2, "stripped-stamp rejected result reached subscriber");

        Observer::CopiedLifecycleObservation driftedRejected = rejectedObservation;
        driftedRejected.FunctionNameIndex = kCheckJoinInProgressNameIndex + 1;
        driftedRejected.OuterNameIndex = kShooterGameModeNameIndex + 1;
        Require(!Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    driftedRejected,
                    nullptr,
                    rejected),
                "drifted CheckJoinInProgress observation was loggable with real apply result");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    rejected,
                    driftedRejected) == 0,
                "drifted CheckJoinInProgress observation dispatched with real apply result");
        std::atomic<uint64_t> counter{0};
        std::atomic<uint32_t> roleMask{0};
        uint64_t observationNumber = 99;
        Require(!Observer::TryReserveApprovedRuntimeEvidenceLogBudget(
                    counter,
                    roleMask,
                    driftedRejected,
                    3,
                    observationNumber),
                "drifted CheckJoinInProgress observation reserved approved evidence budget");
        Require(counter.load(std::memory_order_relaxed) == 0,
                "drifted CheckJoinInProgress observation consumed approved evidence budget");
        Require(roleMask.load(std::memory_order_relaxed) == 0,
                "drifted CheckJoinInProgress observation reserved approved evidence role");
        Require(capture.Calls == 2, "drifted CheckJoinInProgress observation reached subscriber");

        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 1,
                "apply validation stamp guard cleanup removed wrong callback count");
    }

    void TestApplyValidationStampBindsRegistryPrincipalProvenance()
    {
        auto& dispatcher = Obelisk::Core::PlayerPrincipalEventDispatcher::Get();
        int owner = 0;
        dispatcher.UnregisterCallbacksForOwner(&owner);

        DispatchCapture capture;
        const uint64_t registrationId = dispatcher.Register(&owner, {CaptureDispatch, &capture});
        Require(registrationId != 0, "apply provenance guard registration failed");

        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Observer::CopiedLifecycleObservation startObservation =
            MakeStartObservation(true, true, 906);
        const Applicator::ProcessLocalEventContext startContext = ProofContext(906, 18);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            startObservation,
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "apply provenance fixture did not create principal");
        Require(Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    startObservation,
                    nullptr,
                    start),
                "unmodified apply provenance fixture was not loggable");

        Applicator::ApplyResult forgedSameRegistryPrincipal = start;
        forgedSameRegistryPrincipal.Principal = registry.AllocatePrincipal();
        Require(forgedSameRegistryPrincipal.Principal.HasValidShape(),
                "apply provenance fixture did not allocate same-registry alternate principal");
        Require(registry.Validate(forgedSameRegistryPrincipal.Principal),
                "apply provenance fixture alternate principal was not live");
        Require(!Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    startObservation,
                    nullptr,
                    forgedSameRegistryPrincipal),
                "apply result with swapped same-registry principal was loggable");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    forgedSameRegistryPrincipal,
                    startObservation) == 0,
                "apply result with swapped same-registry principal dispatched");

        Obelisk::Core::PlayerPrincipalRegistry foreignRegistry;
        Applicator::ApplyResult forgedForeignRegistry = start;
        forgedForeignRegistry.Registry = &foreignRegistry;
        forgedForeignRegistry.Principal = foreignRegistry.AllocatePrincipal();
        Require(forgedForeignRegistry.Principal.HasValidShape(),
                "apply provenance fixture did not allocate foreign-registry principal");
        Require(foreignRegistry.Validate(forgedForeignRegistry.Principal),
                "apply provenance fixture foreign principal was not live");
        Require(!Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    startObservation,
                    nullptr,
                    forgedForeignRegistry),
                "apply result with swapped registry provenance was loggable");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    forgedForeignRegistry,
                    startObservation) == 0,
                "apply result with swapped registry provenance dispatched");

        Require(capture.Calls == 0,
                "apply provenance forged results reached subscribers");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 1,
                "apply provenance guard cleanup removed wrong callback count");
    }

    void TestApplyValidationStampBindsCopiedObservationExactness()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        Correlation::ResetForTesting();
        auto& dispatcher = Obelisk::Core::PlayerPrincipalEventDispatcher::Get();
        int owner = 0;
        dispatcher.UnregisterCallbacksForOwner(&owner);

        DispatchCapture capture;
        const uint64_t registrationId = dispatcher.Register(&owner, {CaptureDispatch, &capture});
        Require(registrationId != 0, "observation exactness guard registration failed");

        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Observer::CopiedLifecycleObservation startObservation =
            MakeStartObservation(true, true, 907);
        const Applicator::ProcessLocalEventContext startContext = ProofContext(907, 19);
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            startObservation,
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "observation exactness start fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, startObservation, start);
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    start,
                    startObservation) == 1,
                "observation exactness start fixture did not dispatch");
        Require(Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    startObservation,
                    nullptr,
                    start),
                "observation exactness start fixture was not loggable");

        const Observer::CopiedLifecycleObservation replayedStartObservation =
            MakeStartObservation(true, true, 908);
        Require(!Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    replayedStartObservation,
                    nullptr,
                    start),
                "start apply result replayed with a different copied subject token");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    start,
                    replayedStartObservation) == 0,
                "start apply result dispatched a different copied subject token");
        Require(capture.Calls == 1,
                "replayed start observation reached subscriber");

        const Observer::CopiedLifecycleObservation rejectedObservation =
            MakeCheckJoinRejectedObservation();
        const Applicator::ProcessLocalEventContext rejectedContext = ProofContext(908, 19);
        const Applicator::ApplyResult rejected =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            rejectedObservation,
                                                            nullptr,
                                                            &rejectedContext);
        Require(rejected.Status == Applicator::ApplyStatus::SessionStartRejectedNoop,
                "observation exactness rejected fixture did not no-op");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    rejected,
                    rejectedObservation) == 1,
                "observation exactness rejected fixture did not dispatch");

        Observer::CopiedLifecycleObservation replayedRejectedObservation = rejectedObservation;
        replayedRejectedObservation.RedactedStorage[1] = Reflection::LifecycleField::Exiting;
        Require(!Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    replayedRejectedObservation,
                    nullptr,
                    rejected),
                "rejected apply result replayed with mutated copied observation storage");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    rejected,
                    replayedRejectedObservation) == 0,
                "rejected apply result dispatched mutated copied observation storage");
        Require(capture.Calls == 2,
                "replayed rejected observation reached subscriber");

        const Observer::CopiedLifecycleObservation endObservation = MakeEndObservation(907);
        const Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation =
            RequireResolvedLogoutCorrelation(
                endObservation,
                "observation exactness logout fixture did not resolve correlation");
        const Applicator::ProcessLocalEventContext endContext = ProofContext(909, 19);
        const Applicator::ApplyResult end =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            endObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &endContext);
        Correlation::ClearSessionEndCorrelation(endObservation, end);
        Require(end.Status == Applicator::ApplyStatus::SessionEndInvalidated,
                "observation exactness logout fixture did not invalidate");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    end,
                    endObservation) == 1,
                "observation exactness logout fixture did not dispatch");
        Require(Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    endObservation,
                    &resolvedLogoutCorrelation,
                    end),
                "observation exactness logout fixture was not loggable");

        const Observer::CopiedLifecycleObservation replayedEndObservation =
            MakeEndObservation(908);
        Require(!Applicator::IsApprovedRuntimeEvidenceLoggableApplyResult(
                    replayedEndObservation,
                    &resolvedLogoutCorrelation,
                    end),
                "logout apply result replayed with a different copied subject token");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    end,
                    replayedEndObservation) == 0,
                "logout apply result dispatched a different copied subject token");
        Require(capture.Calls == 3,
                "replayed logout observation reached subscriber");

        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 1,
                "observation exactness guard cleanup removed wrong callback count");
        Correlation::ResetForTesting();
    }

    void TestInternalDispatchBridgeRejectsRejectedNoopWithRegistryProof()
    {
        auto& dispatcher = Obelisk::Core::PlayerPrincipalEventDispatcher::Get();
        int owner = 0;
        dispatcher.UnregisterCallbacksForOwner(&owner);

        DispatchCapture capture;
        const uint64_t registrationId = dispatcher.Register(&owner, {CaptureDispatch, &capture});
        Require(registrationId != 0, "rejected-noop registry-proof guard registration failed");

        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Applicator::ApplyResult forgedRejected{
            .Status = Applicator::ApplyStatus::SessionStartRejectedNoop,
            .Registry = &registry,
            .EventSequence = 901,
            .ServerProcessEpoch = 16,
        };

        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    forgedRejected,
                    MakeCheckJoinRejectedObservation()) == 0,
                "canonical rejected session_start no-op with registry proof reached internal dispatcher");
        Require(capture.Calls == 0,
                "canonical rejected session_start no-op with registry proof reached subscriber");

        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 1,
                "rejected-noop registry-proof guard cleanup removed wrong callback count");
    }

    void TestInternalDispatchBridgeRejectsPrunedTerminalProof()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        Correlation::ResetForTesting();
        auto& dispatcher = Obelisk::Core::PlayerPrincipalEventDispatcher::Get();
        int owner = 0;
        dispatcher.UnregisterCallbacksForOwner(&owner);

        DispatchCapture capture;
        const uint64_t registrationId = dispatcher.Register(&owner, {CaptureDispatch, &capture});
        Require(registrationId != 0, "pruned terminal dispatch guard registration failed");

        Obelisk::Core::PlayerPrincipalRegistry registry;
        registry.SetMaxRetainedInvalidatedPrincipalsForTesting(0);
        const Observer::CopiedLifecycleObservation startObservation =
            MakeStartObservation(true, true, 902);
        const Applicator::ProcessLocalEventContext startContext{
            .EventSequence = 902,
            .ServerProcessEpoch = 16,
        };
        const Applicator::ApplyResult start =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            startObservation,
                                                            nullptr,
                                                            &startContext);
        Require(start.Status == Applicator::ApplyStatus::SessionStartCreated,
                "pruned terminal fixture did not create a principal");
        Correlation::BindSessionStartCorrelation(registry, startObservation, start);

        const Observer::CopiedLifecycleObservation endObservation = MakeEndObservation(902);
        const Obelisk::Core::PlayerPrincipalToken resolvedLogoutCorrelation =
            RequireResolvedLogoutCorrelation(endObservation,
                                             "pruned terminal fixture did not resolve private proof");
        const Applicator::ProcessLocalEventContext endContext{
            .EventSequence = 903,
            .ServerProcessEpoch = 16,
        };
        const Applicator::ApplyResult end =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            endObservation,
                                                            &resolvedLogoutCorrelation,
                                                            &endContext);
        Require(end.Status == Applicator::ApplyStatus::SessionEndStaleNoop,
                "pruned terminal fixture was reported as accepted session_end evidence");
        Require(!end.ValidatedLifecycleEvent,
                "pruned terminal fixture was marked as validated lifecycle evidence");
        Require(!end.RegistryChanged,
                "pruned terminal fixture reported an evidence-bearing registry mutation");
        Require(registry.Lookup(end.Principal).Status ==
                    Obelisk::Core::PlayerPrincipalLookupStatus::UnknownHandle,
                "pruned terminal fixture retained invalidated registry proof");

        Correlation::ClearSessionEndCorrelation(endObservation, end);
        Obelisk::Core::PlayerPrincipalToken retainedLogoutCorrelation;
        Require(!Correlation::TryResolveLogoutCorrelation(endObservation,
                                                          retainedLogoutCorrelation),
                "pruned terminal logout retained private correlation after clear");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    end,
                    endObservation) == 0,
                "pruned terminal logout reached internal dispatcher");
        Require(capture.Calls == 0,
                "pruned terminal logout reached subscriber");

        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 1,
                "pruned terminal dispatch guard cleanup removed wrong callback count");
    }

    void TestInternalDispatchBridgeSkipsWithoutSubscribers()
    {
        auto& dispatcher = Obelisk::Core::PlayerPrincipalEventDispatcher::Get();
        int owner = 0;
        dispatcher.UnregisterCallbacksForOwner(&owner);
        Require(dispatcher.SubscriptionCount() == 0,
                "no-subscriber dispatch fixture started with callbacks");

        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Applicator::ProcessLocalEventContext context{
            .EventSequence = 601,
            .ServerProcessEpoch = 13,
        };
        const Observer::CopiedLifecycleObservation observation =
            MakeStartObservation(true, true);
        const Applicator::ApplyResult result =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            observation,
                                                            nullptr,
                                                            &context);
        Require(result.Status == Applicator::ApplyStatus::SessionStartCreated,
                "no-subscriber dispatch fixture did not create principal");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    result,
                    observation) == 0,
                "no-subscriber dispatch bridge reported callbacks");
        Require(dispatcher.SubscriptionCount() == 0,
                "no-subscriber dispatch bridge changed subscriptions");
    }

    void TestInternalDispatchBridgeRejectsApplyObservationMismatch()
    {
        auto& dispatcher = Obelisk::Core::PlayerPrincipalEventDispatcher::Get();
        int owner = 0;
        dispatcher.UnregisterCallbacksForOwner(&owner);

        DispatchCapture capture;
        const uint64_t registrationId = dispatcher.Register(&owner, {CaptureDispatch, &capture});
        Require(registrationId != 0, "mismatched dispatch registration failed");

        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Applicator::ProcessLocalEventContext createdContext{
            .EventSequence = 701,
            .ServerProcessEpoch = 14,
        };
        const Observer::CopiedLifecycleObservation acceptedObservation =
            MakeStartObservation(true, true);
        const Applicator::ApplyResult created =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            acceptedObservation,
                                                            nullptr,
                                                            &createdContext);
        Require(created.Status == Applicator::ApplyStatus::SessionStartCreated,
                "mismatched dispatch created fixture failed");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    created,
                    MakeStartObservation(true, false)) == 0,
                "created apply result dispatched login-backed rejected observation");
        Require(capture.Calls == 0,
                "created/rejected mismatch reached subscriber");

        const Applicator::ProcessLocalEventContext rejectedContext{
            .EventSequence = 702,
            .ServerProcessEpoch = 14,
        };
        const Observer::CopiedLifecycleObservation rejectedObservation =
            MakeCheckJoinRejectedObservation();
        const Applicator::ApplyResult rejected =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            rejectedObservation,
                                                            nullptr,
                                                            &rejectedContext);
        Require(rejected.Status == Applicator::ApplyStatus::SessionStartRejectedNoop,
                "mismatched dispatch rejected fixture failed");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    rejected,
                    acceptedObservation) == 0,
                "rejected apply result dispatched accepted observation");
        Require(capture.Calls == 0,
                "rejected/accepted mismatch reached subscriber");

        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    rejected,
                    rejectedObservation) == 1,
                "matched CheckJoinInProgress rejected observation did not dispatch");
        Require(capture.Calls == 1,
                "matched CheckJoinInProgress rejected observation dispatch count mismatch");
        Require(capture.Kind == Obelisk::Core::PlayerPrincipalEventKind::SessionStartRejected,
                "matched CheckJoinInProgress rejected observation dispatch kind mismatch");

        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 1,
                "mismatched dispatch cleanup removed wrong callback count");
    }

    void TestInternalDispatchBridgeRejectsStartInvalidatedByCorrelation()
    {
        namespace Correlation = Obelisk::Hooks::ProcessEventPlayerPrincipalLifecycleCorrelation;

        Correlation::ResetForTesting();
        auto& dispatcher = Obelisk::Core::PlayerPrincipalEventDispatcher::Get();
        int owner = 0;
        dispatcher.UnregisterCallbacksForOwner(&owner);

        DispatchCapture capture;
        const uint64_t registrationId = dispatcher.Register(&owner, {CaptureDispatch, &capture});
        Require(registrationId != 0, "correlation-dispatch guard registration failed");

        Obelisk::Core::PlayerPrincipalRegistry registry;
        const Observer::CopiedLifecycleObservation firstObservation =
            MakeStartObservation(true, true, 706);
        const Applicator::ProcessLocalEventContext firstContext{
            .EventSequence = 801,
            .ServerProcessEpoch = 15,
        };
        const Applicator::ApplyResult first =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            firstObservation,
                                                            nullptr,
                                                            &firstContext);
        Require(first.Status == Applicator::ApplyStatus::SessionStartCreated,
                "correlation-dispatch first fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, firstObservation, first);
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    first,
                    firstObservation) == 1,
                "correlation-dispatch first start did not dispatch");
        Require(capture.Calls == 1,
                "correlation-dispatch first start dispatch count mismatch");

        const Observer::CopiedLifecycleObservation duplicateObservation =
            MakeStartObservation(true, true, 706);
        const Applicator::ProcessLocalEventContext duplicateContext{
            .EventSequence = 801,
            .ServerProcessEpoch = 15,
        };
        const Applicator::ApplyResult duplicate =
            Applicator::ApplyLifecycleObservationToRegistry(registry,
                                                            duplicateObservation,
                                                            nullptr,
                                                            &duplicateContext);
        Require(duplicate.Status == Applicator::ApplyStatus::SessionStartCreated,
                "correlation-dispatch duplicate fixture did not create principal");
        Correlation::BindSessionStartCorrelation(registry, duplicateObservation, duplicate);
        Require(!registry.Validate(duplicate.Principal),
                "correlation-dispatch duplicate principal was not invalidated");
        Require(Applicator::DispatchLifecycleApplyResultToInternalSubscribers(
                    duplicate,
                    duplicateObservation) == 0,
                "correlation-dispatch emitted an invalidated duplicate start");
        Require(capture.Calls == 1,
                "correlation-dispatch invalidated duplicate reached subscriber");

        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 1,
                "correlation-dispatch guard cleanup removed wrong callback count");
    }
}

int main()
{
    try
    {
        TestAcceptedSessionStartAllocatesPrincipal();
        TestRejectedAndDiagnosticObservationsDoNotAllocate();
        TestMalformedObservationFailsClosed();
        TestSessionEndWithoutCorrelationDoesNotInvalidate();
        TestSessionEndWithSuppliedPrincipalButNoBoundProofDoesNotInvalidate();
        TestSessionEndWithCorrelationInvalidates();
        TestSessionEndWithZeroPrivateTokenDoesNotUseSuppliedCorrelation();
        TestPrivateSubjectTokenCorrelationInvalidatesMatchingSessionEnd();
        TestPrivateSubjectTokenMismatchDoesNotResolveOrInvalidate();
        TestPrivateSubjectTokenCorrelationFailsClosed();
        TestValidateOnlySubjectTokenSentinelFailsClosed();
        TestPrivateSubjectTokenCorrelationAcceptsFreshStartAfterRejectedNoop();
        TestPrivateSubjectTokenCorrelationBindFailureInvalidatesNewPrincipal();
        TestPrivateSubjectTokenCorrelationSupersedeFailureInvalidatesNewPrincipal();
        TestPrivateSubjectTokenCorrelationSupersedesPreviousPrincipal();
        TestPrivateSubjectTokenCorrelationRejectsOutOfOrderStartBind();
        TestPrivateSubjectTokenCorrelationRejectsEqualSequenceStartBind();
        TestPrivateSubjectTokenCorrelationRejectsServerEpochDriftStartBind();
        TestPrivateSubjectTokenCorrelationRejectsEqualSequenceServerEpochDriftStartBind();
        TestPrivateSubjectTokenCorrelationClearRequiresFreshSameEpochLogout();
        TestPrivateSubjectTokenCorrelationDoesNotSpendAmbiguousBudgetOnStaleLogoutProof();
        TestPrivateSubjectTokenCorrelationRejectsEachSupersededLogout();
        TestPrivateSubjectTokenCorrelationRejectsMalformedShapes();
        TestPrivateSubjectTokenCorrelationRejectsNonExactRoleShapes();
        TestDuplicateAndStaleSessionEndNoop();
        TestNonLogoutInvalidatedSessionEndClearsStaleCorrelation();
        TestPrunedInvalidatedSessionEndClearsStaleCorrelation();
        TestSessionEndInvalidationRequiresRetainedLogoutProof();
        TestPrivateSubjectTokenCorrelationClearRequiresRegistryConfirmation();
        TestPrivateSubjectTokenCorrelationRejectsForeignRegistryTokenCollision();
        TestCorrelatedDuplicateAndStaleSessionEndPreserveEventContext();
        TestSessionStartAllocationFailureFailsClosed();
        TestSessionStartWithoutMatchedEventContextFailsClosed();
        TestSuppliedEventContextReachesValidatedEventViews();
        TestSuppliedEventContextDoesNotReachUnsupportedObservations();
        TestZeroEventContextDoesNotOpenUnsupportedObservations();
        TestInternalDispatchBridgeSendsOnlySafeValidatedEvents();
        TestSessionEndDispatchRequiresCorrelationAndNonzeroContext();
        TestApprovedRuntimeEvidenceLogGateSkipsUnmatchedLogoutUntilMatched();
        TestApprovedRuntimeEvidenceLogGateDoesNotCompleteTripletWithoutRejectedStart();
        TestRejectedStartAndUnresolvedLogoutDoNotCompleteTripletWithoutSessionStart();
        TestApprovedRuntimeEvidenceLogGateRejectsUnsafeCorrelationState();
        TestInternalDispatchBridgeRequiresNonzeroContextAndValidShape();
        TestInternalDispatchAndLogGateRequireApplyValidationStamp();
        TestApplyValidationStampBindsRegistryPrincipalProvenance();
        TestApplyValidationStampBindsCopiedObservationExactness();
        TestInternalDispatchBridgeRejectsRejectedNoopWithRegistryProof();
        TestInternalDispatchBridgeRejectsPrunedTerminalProof();
        TestInternalDispatchBridgeSkipsWithoutSubscribers();
        TestInternalDispatchBridgeRejectsApplyObservationMismatch();
        TestInternalDispatchBridgeRejectsStartInvalidatedByCorrelation();
    }
    catch (const std::exception& e)
    {
        std::cerr << "PlayerPrincipalLifecycleApplicatorTests failed: " << e.what() << '\n';
        return 1;
    }

    std::cout << "PlayerPrincipalLifecycleApplicatorTests passed\n";
    return 0;
}
