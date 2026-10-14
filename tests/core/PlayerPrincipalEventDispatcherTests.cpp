#include "core/GameplayCallbackScope.h"
#include "core/PlayerPrincipalEventDispatcher.h"

#ifndef OBELISK_PLAYER_PRINCIPAL_EVENT_DISPATCHER_ENABLE_TEST_HOOKS
#error PlayerPrincipalEventDispatcher tests must explicitly enable internal test hooks.
#endif

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <iostream>
#include <limits>
#include <mutex>
#include <new>
#include <stdexcept>
#include <thread>
#include <type_traits>
#include <vector>

namespace
{
    using Obelisk::Core::PlayerPrincipalAction;
    using Obelisk::Core::PlayerPrincipalBoolField;
    using Obelisk::Core::PlayerPrincipalBoolValue;
    using Obelisk::Core::PlayerPrincipalEventCallback;
    using Obelisk::Core::PlayerPrincipalEventDispatcher;
    using Obelisk::Core::PlayerPrincipalEventKind;
    using Obelisk::Core::PlayerPrincipalEventView;

    static_assert(std::is_same_v<
                      std::invoke_result_t<PlayerPrincipalEventCallback,
                                           const PlayerPrincipalEventView&,
                                           void*>,
                      void>,
                  "Player principal callbacks must not expose block/override return values");
    static_assert(std::is_same_v<decltype(PlayerPrincipalEventView::Bools),
                                 std::span<const PlayerPrincipalBoolValue>>,
                  "Player principal dispatch must expose only copied bool storage");
    static_assert(std::is_const_v<decltype(PlayerPrincipalEventView::Bools)::element_type>,
                  "Player principal bool payload elements must remain read-only to callbacks");

    struct Capture
    {
        int Calls = 0;
        PlayerPrincipalEventKind Kind = PlayerPrincipalEventKind::SessionStart;
        PlayerPrincipalAction Action = PlayerPrincipalAction::None;
        uint64_t EventSequence = 0;
        uint64_t ServerProcessEpoch = 0;
        std::vector<PlayerPrincipalBoolValue> Bools;
        const PlayerPrincipalBoolValue* BoolPointer = nullptr;
    };

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    std::vector<PlayerPrincipalBoolValue> MakeStartBools(bool isFromLogin = true, bool returnValue = true)
    {
        return {
            {.Field = PlayerPrincipalBoolField::BIsFromLogin, .Value = isFromLogin},
            {.Field = PlayerPrincipalBoolField::ReturnValue, .Value = returnValue},
        };
    }

    PlayerPrincipalEventView MakeStartEvent(const std::vector<PlayerPrincipalBoolValue>& bools)
    {
        return {
            .Kind = PlayerPrincipalEventKind::SessionStart,
            .Action = PlayerPrincipalAction::CandidateCreated,
            .EventSequence = 101,
            .ServerProcessEpoch = 7,
            .Bools = bools,
        };
    }

    PlayerPrincipalEventView MakeRejectedEvent(const std::vector<PlayerPrincipalBoolValue>& bools)
    {
        return {
            .Kind = PlayerPrincipalEventKind::SessionStartRejected,
            .Action = PlayerPrincipalAction::None,
            .EventSequence = 102,
            .ServerProcessEpoch = 7,
            .Bools = bools,
        };
    }

    PlayerPrincipalEventView MakeEndEvent()
    {
        return {
            .Kind = PlayerPrincipalEventKind::SessionEnd,
            .Action = PlayerPrincipalAction::CandidateInvalidated,
            .EventSequence = 103,
            .ServerProcessEpoch = 7,
            .Bools = {},
        };
    }

    void CaptureCallback(const PlayerPrincipalEventView& event, void* userData)
    {
        auto* capture = static_cast<Capture*>(userData);
        ++capture->Calls;
        capture->Kind = event.Kind;
        capture->Action = event.Action;
        capture->EventSequence = event.EventSequence;
        capture->ServerProcessEpoch = event.ServerProcessEpoch;
        capture->Bools.assign(event.Bools.begin(), event.Bools.end());
        capture->BoolPointer = event.Bools.data();
    }

    void ThrowingCallback(const PlayerPrincipalEventView&, void*)
    {
        throw std::runtime_error("expected player principal dispatcher test exception");
    }

    void ThrowingUnknownCallback(const PlayerPrincipalEventView&, void*)
    {
        throw 7;
    }

    void NoopCallback(const PlayerPrincipalEventView&, void*)
    {
    }

    struct DestroyFailureState
    {
        int Calls = 0;
    };

    void ThrowingDestroyUserData(void* userData)
    {
        auto* state = static_cast<DestroyFailureState*>(userData);
        ++state->Calls;
        throw std::runtime_error("expected destroy failure");
    }

    void CountingDestroyUserData(void* userData)
    {
        auto* state = static_cast<DestroyFailureState*>(userData);
        ++state->Calls;
    }

    void TestPlayerPrincipalSurfaceIsInternalObservationOnly()
    {
        const auto [kind, action, eventSequence, serverProcessEpoch, bools] = PlayerPrincipalEventView{};
        const auto [field, value] = PlayerPrincipalBoolValue{};
        (void)kind;
        (void)action;
        (void)eventSequence;
        (void)serverProcessEpoch;
        (void)bools;
        (void)field;
        (void)value;
    }

    void TestNoSubscriberDispatchReturnsBeforePayloadCopy()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();

        Require(dispatcher.SubscriptionCount() == 0,
                "new player principal dispatcher unexpectedly had subscribers");
        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 0,
                "no-subscriber player principal dispatch returned callbacks");
        Require(dispatcher.SubscriptionCount() == 0,
                "no-subscriber player principal dispatch changed registrations");
    }

    void TestDispatchCopiesBoolInputForCallbackDuration()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools(true, true);
        const auto* sourcePointer = bools.data();

        const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(id != 0, "registration id was not assigned");
        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 1, "dispatch count was wrong");

        Require(capture.Calls == 1, "callback did not run");
        Require(capture.Kind == PlayerPrincipalEventKind::SessionStart, "event kind changed");
        Require(capture.Action == PlayerPrincipalAction::CandidateCreated, "action changed");
        Require(capture.EventSequence == 101, "event sequence changed");
        Require(capture.ServerProcessEpoch == 7, "server process epoch changed");
        Require(capture.Bools.size() == 2, "bool count mismatch");
        Require(capture.Bools[0].Field == PlayerPrincipalBoolField::BIsFromLogin,
                "first bool field mismatch");
        Require(capture.Bools[0].Value, "first bool value mismatch");
        Require(capture.Bools[1].Field == PlayerPrincipalBoolField::ReturnValue,
                "return bool field mismatch");
        Require(capture.Bools[1].Value, "return bool value mismatch");
        Require(capture.BoolPointer != sourcePointer, "dispatcher passed borrowed bool storage");
    }

    void TestDispatchCopiesSourceEventSequenceForAllSubscribers()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        std::vector<Capture> captures(2);
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();
        PlayerPrincipalEventView event = MakeStartEvent(bools);
        event.EventSequence = 777;
        event.ServerProcessEpoch = 44;

        for (Capture& capture : captures)
        {
            const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
            Require(id != 0, "source-sequence subscriber registration failed");
        }

        Require(dispatcher.Dispatch(event) == captures.size(),
                "source-sequence dispatch count mismatch");
        for (const Capture& capture : captures)
        {
            Require(capture.EventSequence == 777,
                    "player principal event sequence was not copied from the source event");
            Require(capture.ServerProcessEpoch == 44,
                    "player principal server process epoch was not copied from the source event");
        }
    }

    void TestDispatchSnapshotsStackAndHeapSubscribers()
    {
        for (const size_t subscriberCount : {size_t{4}, size_t{5}})
        {
            PlayerPrincipalEventDispatcher dispatcher;
            int owner = 0;
            std::vector<Capture> captures(subscriberCount);
            const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();
            const auto* sourcePointer = bools.data();

            for (Capture& capture : captures)
            {
                const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
                Require(id != 0, "stack/heap subscriber registration failed");
            }

            Require(dispatcher.Dispatch(MakeStartEvent(bools)) == subscriberCount,
                    "stack/heap subscriber dispatch count mismatch");
            for (const Capture& capture : captures)
            {
                Require(capture.Calls == 1, "stack/heap subscriber did not run once");
                Require(capture.BoolPointer != sourcePointer,
                        "stack/heap subscriber received borrowed bool storage");
            }
            Require(dispatcher.UnregisterCallbacksForOwner(&owner) == subscriberCount,
                    "stack/heap subscriber cleanup removed wrong count");
        }
    }

    void TestRegisterRejectsInvalidInput()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;

        Require(dispatcher.Register(nullptr, {CaptureCallback, &capture}) == 0,
                "registration without owner was accepted");
        Require(dispatcher.Register(&owner, {nullptr, &capture}) == 0,
                "registration without callback was accepted");
        Require(dispatcher.SubscriptionCount() == 0, "invalid registrations were stored");
    }

    void TestDispatchRejectsUnknownEventShape()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();
        dispatcher.Register(&owner, {CaptureCallback, &capture});

        PlayerPrincipalEventView unknownKind = MakeStartEvent(bools);
        unknownKind.Kind = static_cast<PlayerPrincipalEventKind>(99);
        Require(dispatcher.Dispatch(unknownKind) == 0, "unknown player principal event kind dispatched");

        PlayerPrincipalEventView unknownAction = MakeStartEvent(bools);
        unknownAction.Action = static_cast<PlayerPrincipalAction>(99);
        Require(dispatcher.Dispatch(unknownAction) == 0, "unknown player principal action dispatched");

        PlayerPrincipalEventView unknownBool = MakeStartEvent(bools);
        bools[0].Field = static_cast<PlayerPrincipalBoolField>(99);
        unknownBool.Bools = bools;
        Require(dispatcher.Dispatch(unknownBool) == 0, "unknown player principal bool field dispatched");
        Require(capture.Calls == 0, "invalid player principal event reached callback");
    }

    void TestDispatchRejectsZeroRuntimeContext()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();
        dispatcher.Register(&owner, {CaptureCallback, &capture});

        PlayerPrincipalEventView zeroSequence = MakeStartEvent(bools);
        zeroSequence.EventSequence = 0;
        Require(dispatcher.Dispatch(zeroSequence) == 0,
                "zero player principal event sequence dispatched");

        PlayerPrincipalEventView zeroEpoch = MakeStartEvent(bools);
        zeroEpoch.ServerProcessEpoch = 0;
        Require(dispatcher.Dispatch(zeroEpoch) == 0,
                "zero player principal server process epoch dispatched");

        Require(capture.Calls == 0,
                "zero runtime-context player principal event reached callback");
    }

    void TestDispatchRejectsUnexpectedLifecycleShape()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();
        dispatcher.Register(&owner, {CaptureCallback, &capture});

        PlayerPrincipalEventView start = MakeStartEvent(bools);
        start.Action = PlayerPrincipalAction::None;
        Require(dispatcher.Dispatch(start) == 0, "session start without candidate creation dispatched");

        bools = MakeStartBools(false, true);
        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 0,
                "rejected start bools created a principal candidate");
        Require(dispatcher.Dispatch(MakeRejectedEvent(bools)) == 0,
                "return-true non-login start dispatched as a rejected principal");

        bools = MakeStartBools(true, false);
        Require(dispatcher.Dispatch(MakeRejectedEvent(bools)) == 1,
                "valid rejected start event was rejected");

        bools = MakeStartBools(true, true);
        Require(dispatcher.Dispatch(MakeRejectedEvent(bools)) == 0,
                "accepted start bools dispatched as rejected");

        bools = MakeStartBools();
        std::swap(bools[0], bools[1]);
        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 0,
                "misordered player principal bools dispatched");

        bools = MakeStartBools();
        PlayerPrincipalEventView endWithBools = MakeEndEvent();
        endWithBools.Bools = bools;
        Require(dispatcher.Dispatch(endWithBools) == 0,
                "session end with start bools dispatched");
        Require(dispatcher.Dispatch(MakeEndEvent()) == 1, "valid session end was rejected");
        Require(capture.Calls == 2, "valid lifecycle events did not reach callback");
    }

    void TestRejectedStartDispatchesOnlyNoopDiagnosticShape()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools(true, false);
        const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(id != 0, "rejected-start noop diagnostic registration failed");

        PlayerPrincipalEventView rejected = MakeRejectedEvent(bools);
        rejected.EventSequence = 707;
        rejected.ServerProcessEpoch = 17;
        Require(dispatcher.Dispatch(rejected) == 1,
                "canonical rejected-start noop diagnostic did not dispatch");
        Require(capture.Calls == 1,
                "canonical rejected-start noop diagnostic callback count mismatch");
        Require(capture.Kind == PlayerPrincipalEventKind::SessionStartRejected,
                "rejected-start noop diagnostic kind changed");
        Require(capture.Action == PlayerPrincipalAction::None,
                "rejected-start noop diagnostic carried a principal action");
        Require(capture.EventSequence == 707,
                "rejected-start noop diagnostic lost event sequence");
        Require(capture.ServerProcessEpoch == 17,
                "rejected-start noop diagnostic lost server process epoch");
        Require(capture.Bools.size() == 2,
                "rejected-start noop diagnostic bool count mismatch");
        Require(capture.Bools[0].Field == PlayerPrincipalBoolField::BIsFromLogin &&
                    capture.Bools[0].Value,
                "rejected-start noop diagnostic lost login bool");
        Require(capture.Bools[1].Field == PlayerPrincipalBoolField::ReturnValue &&
                    !capture.Bools[1].Value,
                "rejected-start noop diagnostic lost rejected return bool");

        PlayerPrincipalEventView candidateCreated = rejected;
        candidateCreated.Action = PlayerPrincipalAction::CandidateCreated;
        Require(dispatcher.Dispatch(candidateCreated) == 0,
                "rejected start with candidate-created action dispatched");

        PlayerPrincipalEventView candidateInvalidated = rejected;
        candidateInvalidated.Action = PlayerPrincipalAction::CandidateInvalidated;
        Require(dispatcher.Dispatch(candidateInvalidated) == 0,
                "rejected start with candidate-invalidated action dispatched");
        Require(capture.Calls == 1,
                "invalid rejected-start principal actions reached callback");
    }

    void TestUnregisterForOwnerRequiresMatchingOwner()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        int otherOwner = 0;
        Capture capture;
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();

        const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(id != 0, "registration id was not assigned");
        Require(!dispatcher.UnregisterCallbackForOwner(&otherOwner, id),
                "wrong owner unregistered a player principal callback");
        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 1,
                "callback was removed by wrong owner");
        Require(dispatcher.UnregisterCallbackForOwner(&owner, id),
                "matching owner could not unregister player principal callback");
        Require(!dispatcher.UnregisterCallbackForOwner(&owner, id),
                "matching owner unregister succeeded twice");
        Require(!dispatcher.UnregisterCallbackForOwner(&owner, 0),
                "zero registration id unregistered a player principal callback");
        Require(!dispatcher.UnregisterCallbackForOwner(nullptr, id),
                "null owner unregistered a player principal callback");
        Require(dispatcher.SubscriptionCount() == 0, "owner-scoped unregister left callback behind");
    }

    struct OwnerScopedRetryDestroyState
    {
        int DestroyCalls = 0;
        bool FailNext = true;
    };

    void FailsOnceOwnerScopedDestroyUserData(void* userData)
    {
        auto* state = static_cast<OwnerScopedRetryDestroyState*>(userData);
        ++state->DestroyCalls;
        if (state->FailNext)
        {
            state->FailNext = false;
            throw std::runtime_error("expected owner-scoped player principal destroy failure");
        }
    }

    void TestOwnerScopedUnregisterPropagatesDestroyUserDataFailureAndRetainsRetry()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        OwnerScopedRetryDestroyState state;

        const uint64_t id = dispatcher.Register(
            &owner,
            {NoopCallback, &state, FailsOnceOwnerScopedDestroyUserData});
        Require(id != 0, "owner-scoped destroy-failure registration failed");

        bool threw = false;
        try
        {
            (void)dispatcher.UnregisterCallbackForOwner(&owner, id);
        }
        catch (const std::runtime_error&)
        {
            threw = true;
        }

        Require(threw, "owner-scoped unregister hid throwing player principal DestroyUserData");
        Require(state.DestroyCalls == 1,
                "owner-scoped unregister did not attempt failing DestroyUserData once");
        Require(dispatcher.SubscriptionCount() == 0,
                "owner-scoped unregister failure left player principal callback dispatchable");

        const size_t retryRemoved = dispatcher.UnregisterCallbacksForOwner(&owner);
        Require(retryRemoved == 1,
                "owner cleanup retry did not report retained owner-scoped DestroyUserData failure");
        Require(state.DestroyCalls == 2,
                "owner cleanup retry did not rerun retained owner-scoped DestroyUserData");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 0,
                "completed owner-scoped DestroyUserData retry was not idempotent");
    }

    void TestUnregisterPropagatesDestroyUserDataFailureAndRetainsOwnerRetry()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        OwnerScopedRetryDestroyState state;

        const uint64_t id = dispatcher.Register(
            &owner,
            {NoopCallback, &state, FailsOnceOwnerScopedDestroyUserData});
        Require(id != 0, "direct unregister destroy-failure registration failed");

        bool threw = false;
        try
        {
            (void)dispatcher.Unregister(id);
        }
        catch (const std::runtime_error&)
        {
            threw = true;
        }

        Require(threw, "direct unregister hid throwing player principal DestroyUserData");
        Require(state.DestroyCalls == 1,
                "direct unregister did not attempt failing DestroyUserData once");
        Require(dispatcher.SubscriptionCount() == 0,
                "direct unregister failure left player principal callback dispatchable");

        const size_t retryRemoved = dispatcher.UnregisterCallbacksForOwner(&owner);
        Require(retryRemoved == 1,
                "owner cleanup retry did not report direct unregister DestroyUserData failure");
        Require(state.DestroyCalls == 2,
                "owner cleanup retry did not rerun direct unregister DestroyUserData");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 0,
                "completed direct unregister DestroyUserData retry was not idempotent");
    }

    void TestRegistrationIdsAreRetiredAndOverflowFailsClosed()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();

        const uint64_t firstId = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(firstId == 1, "first registration id was not one");
        Require(dispatcher.Unregister(firstId),
                "first registration id could not unregister before retire check");

        dispatcher.SetNextRegistrationIdForTesting(firstId);
        const uint64_t rewoundId = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(rewoundId != 0, "rewound registration allocation failed unexpectedly");
        Require(rewoundId != firstId, "retired registration id was reused");
        Require(!dispatcher.Unregister(firstId),
                "stale retired registration id unregistered a later callback");
        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 1,
                "callback with fresh registration id did not dispatch");
        Require(capture.Calls == 1,
                "retired registration id changed callback dispatch count");
        Require(dispatcher.Unregister(rewoundId),
                "fresh registration id could not unregister after retire check");

        dispatcher.SetNextRegistrationIdForTesting(std::numeric_limits<uint64_t>::max());
        const uint64_t lastId = dispatcher.Register(&owner, {CaptureCallback, &capture});
        const uint64_t exhaustedId = dispatcher.Register(&owner, {CaptureCallback, &capture});

        Require(lastId == std::numeric_limits<uint64_t>::max(), "last registration id was not preserved");
        Require(exhaustedId == 0, "registration id counter wrapped instead of failing closed");
        Require(!dispatcher.Unregister(0), "zero registration id unregistered a callback after wrap");
        Require(dispatcher.SubscriptionCount() == 1,
                "registration id exhaustion changed existing subscriptions");
        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 1,
                "registration id exhaustion prevented existing callback dispatch");
        Require(capture.Calls == 2,
                "registration id exhaustion changed callback dispatch count");
        Require(dispatcher.Unregister(lastId), "last registration id could not unregister");
        Require(dispatcher.Register(&owner, {CaptureCallback, &capture}) == 0,
                "exhausted registration id counter resumed after unregister");

        dispatcher.SetNextRegistrationIdForTesting(0);
        Require(dispatcher.Register(&owner, {CaptureCallback, &capture}) == 0,
                "zero next-registration-id test hook did not fail closed");
        Require(dispatcher.SubscriptionCount() == 0,
                "registration id exhaustion left callbacks behind");
    }

    void TestRegistrationGenerationOverflowFailsClosed()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();

        dispatcher.SetNextGenerationForTesting(std::numeric_limits<uint64_t>::max());
        const uint64_t saturatedId = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(saturatedId != 0, "max generation registration failed before exhaustion");

        const uint64_t exhaustedId = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(exhaustedId == 0, "generation counter wrapped instead of failing closed");
        Require(dispatcher.SubscriptionCount() == 1,
                "generation exhaustion changed existing subscriptions");
        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 1,
                "generation exhaustion prevented existing callback dispatch");
        Require(capture.Calls == 1, "max generation callback did not run");

        Require(dispatcher.Unregister(saturatedId), "max generation callback did not unregister");
        Require(dispatcher.Register(&owner, {CaptureCallback, &capture}) == 0,
                "exhausted generation counter resumed after unregister");

        dispatcher.SetNextGenerationForTesting(0);
        Require(dispatcher.Register(&owner, {CaptureCallback, &capture}) == 0,
                "zero next-generation test hook did not fail closed");
        Require(dispatcher.SubscriptionCount() == 0,
                "failed generation registrations changed subscription count");
    }

    struct SelfUnregisterCapture
    {
        PlayerPrincipalEventDispatcher* Dispatcher = nullptr;
        uint64_t RegistrationId = 0;
        int Calls = 0;
        int Destroyed = 0;
    };

    void SelfUnregisterCallback(const PlayerPrincipalEventView&, void* userData)
    {
        auto* capture = static_cast<SelfUnregisterCapture*>(userData);
        ++capture->Calls;
        Require(capture->Destroyed == 0, "player principal user data destroyed before callback body");
        Require(capture->Dispatcher->Unregister(capture->RegistrationId),
                "self-unregister from callback failed");
        Require(capture->Destroyed == 0, "player principal user data destroyed before callback returned");
    }

    void CountSelfUnregisterDestroyed(void* userData)
    {
        auto* capture = static_cast<SelfUnregisterCapture*>(userData);
        ++capture->Destroyed;
    }

    void TestCallbackCanUnregisterItselfAndDefersDestroy()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        SelfUnregisterCapture capture{&dispatcher, 0, 0, 0};
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();

        capture.RegistrationId = dispatcher.Register(
            &owner,
            {SelfUnregisterCallback, &capture, CountSelfUnregisterDestroyed});
        Require(capture.RegistrationId != 0, "registration id was not assigned");
        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 1, "self-unregister callback did not run");
        Require(capture.Calls == 1, "self-unregister callback ran wrong number of times");
        Require(capture.Destroyed == 1, "player principal user data was not destroyed after callback");
        Require(dispatcher.SubscriptionCount() == 0, "self-unregister callback remained registered");
        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 0, "self-unregistered callback ran twice");
    }

    struct SelfUnregisterFailingDestroyState
    {
        PlayerPrincipalEventDispatcher* Dispatcher = nullptr;
        uint64_t RegistrationId = 0;
        int Calls = 0;
        int DestroyCalls = 0;
        bool FailNextDestroy = true;
    };

    void SelfUnregisterFailingDestroyCallback(const PlayerPrincipalEventView&, void* userData)
    {
        auto* state = static_cast<SelfUnregisterFailingDestroyState*>(userData);
        ++state->Calls;
        Require(state->Dispatcher != nullptr, "self-unregister failing destroy callback had no dispatcher");
        Require(state->Dispatcher->Unregister(state->RegistrationId),
                "self-unregister failing destroy callback could not unregister itself");
    }

    void FailsOnceSelfUnregisterDestroyUserData(void* userData)
    {
        auto* state = static_cast<SelfUnregisterFailingDestroyState*>(userData);
        ++state->DestroyCalls;
        if (state->FailNextDestroy)
        {
            state->FailNextDestroy = false;
            throw std::runtime_error("expected self-unregister player principal destroy failure");
        }
    }

    void TestSelfUnregisterDestroyFailureIsRetainedForOwnerCleanup()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        SelfUnregisterFailingDestroyState state{&dispatcher, 0, 0, 0, true};
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();

        state.RegistrationId = dispatcher.Register(
            &owner,
            {SelfUnregisterFailingDestroyCallback, &state, FailsOnceSelfUnregisterDestroyUserData});
        Require(state.RegistrationId != 0, "self-unregister failing destroy registration failed");

        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 1,
                "self-unregister failing destroy callback did not dispatch");
        Require(state.Calls == 1, "self-unregister failing destroy callback ran wrong count");
        Require(state.DestroyCalls == 1, "self-unregister failing destroy did not run once");
        Require(dispatcher.SubscriptionCount() == 0,
                "self-unregister failing destroy callback stayed dispatchable after failure");

        bool cleanupThrew = false;
        try
        {
            (void)dispatcher.UnregisterCallbacksForOwner(&owner);
        }
        catch (const std::runtime_error&)
        {
            cleanupThrew = true;
        }

        Require(cleanupThrew,
                "owner cleanup did not report retained self-unregister player principal destroy failure");
        Require(state.DestroyCalls == 2,
                "owner cleanup did not retry self-unregister player principal destroy failure");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 0,
                "completed self-unregister player principal destroy retry was not idempotent");
    }

    struct WaitingOwnerCleanupSelfUnregisterState
    {
        PlayerPrincipalEventDispatcher* Dispatcher = nullptr;
        uint64_t RegistrationId = 0;
        std::mutex Mutex;
        std::condition_variable Cv;
        bool Unregistered = false;
        bool ReleaseCallback = false;
        int Calls = 0;
        int DestroyCalls = 0;
        int FailuresRemaining = 1;
    };

    void WaitingOwnerCleanupSelfUnregisterCallback(const PlayerPrincipalEventView&, void* userData)
    {
        auto* state = static_cast<WaitingOwnerCleanupSelfUnregisterState*>(userData);
        Require(state->Dispatcher != nullptr, "waiting owner cleanup callback had no dispatcher");
        ++state->Calls;
        Require(state->Dispatcher->Unregister(state->RegistrationId),
                "waiting owner cleanup callback could not unregister itself");
        {
            std::unique_lock<std::mutex> lock(state->Mutex);
            state->Unregistered = true;
            state->Cv.notify_all();
            state->Cv.wait(lock, [state]() { return state->ReleaseCallback; });
        }
    }

    void FailsOnceWaitingOwnerCleanupDestroyUserData(void* userData)
    {
        auto* state = static_cast<WaitingOwnerCleanupSelfUnregisterState*>(userData);
        std::lock_guard<std::mutex> lock(state->Mutex);
        ++state->DestroyCalls;
        if (state->FailuresRemaining > 0)
        {
            --state->FailuresRemaining;
            throw std::runtime_error("expected waiting owner cleanup player principal destroy failure");
        }
    }

    void TestWaitingOwnerCleanupObservesSelfUnregisterDeferredDestroyFailure()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        WaitingOwnerCleanupSelfUnregisterState state{&dispatcher};
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();

        state.RegistrationId = dispatcher.Register(
            &owner,
            {WaitingOwnerCleanupSelfUnregisterCallback,
             &state,
             FailsOnceWaitingOwnerCleanupDestroyUserData});
        Require(state.RegistrationId != 0,
                "waiting owner cleanup self-unregister registration failed");

        std::thread dispatchThread([&]() {
            Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 1,
                    "waiting owner cleanup self-unregister callback did not dispatch");
        });

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock,
                                      std::chrono::seconds(2),
                                      [&state]() { return state.Unregistered; }),
                    "waiting owner cleanup self-unregister callback did not unregister");
        }
        Require(dispatcher.SubscriptionCount() == 0,
                "waiting owner cleanup self-unregister callback remained dispatchable");

        std::atomic<bool> cleanupThrew{false};
        std::atomic<bool> cleanupFinished{false};
        std::thread cleanupThread([&]() {
            try
            {
                (void)dispatcher.UnregisterCallbacksForOwner(&owner);
            }
            catch (const std::runtime_error&)
            {
                cleanupThrew.store(true, std::memory_order_release);
            }
            cleanupFinished.store(true, std::memory_order_release);
        });

        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        Require(!cleanupFinished.load(std::memory_order_acquire),
                "waiting owner cleanup completed before deferred destroy ran");

        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            state.ReleaseCallback = true;
        }
        state.Cv.notify_all();

        dispatchThread.join();
        cleanupThread.join();

        Require(cleanupThrew.load(std::memory_order_acquire),
                "waiting owner cleanup hid self-unregister deferred DestroyUserData failure");
        Require(state.DestroyCalls == 2,
                "waiting owner cleanup did not retry the retained deferred DestroyUserData failure");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 0,
                "waiting owner cleanup retry was not idempotent");
    }

    struct OwnerScopedSelfUnregisterCapture
    {
        PlayerPrincipalEventDispatcher* Dispatcher = nullptr;
        void* Owner = nullptr;
        uint64_t RegistrationId = 0;
        int Calls = 0;
        int Destroyed = 0;
    };

    void OwnerScopedSelfUnregisterCallback(const PlayerPrincipalEventView&, void* userData)
    {
        auto* capture = static_cast<OwnerScopedSelfUnregisterCapture*>(userData);
        ++capture->Calls;
        Require(capture->Destroyed == 0,
                "owner-scoped self-unregister destroyed user data before callback body");
        Require(capture->Dispatcher != nullptr, "owner-scoped self-unregister callback had no dispatcher");
        Require(capture->Dispatcher->UnregisterCallbackForOwner(capture->Owner, capture->RegistrationId),
                "owner-scoped self-unregister from callback failed");
        Require(capture->Destroyed == 0,
                "owner-scoped self-unregister destroyed user data before callback returned");
    }

    void CountOwnerScopedSelfUnregisterDestroyed(void* userData)
    {
        auto* capture = static_cast<OwnerScopedSelfUnregisterCapture*>(userData);
        ++capture->Destroyed;
    }

    void TestOwnerScopedCallbackCanUnregisterItselfAndDefersDestroy()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        OwnerScopedSelfUnregisterCapture capture{&dispatcher, &owner, 0, 0, 0};
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();

        capture.RegistrationId = dispatcher.Register(
            &owner,
            {OwnerScopedSelfUnregisterCallback, &capture, CountOwnerScopedSelfUnregisterDestroyed});
        Require(capture.RegistrationId != 0, "owner-scoped self-unregister registration id was not assigned");
        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 1,
                "owner-scoped self-unregister callback did not run");
        Require(capture.Calls == 1,
                "owner-scoped self-unregister callback ran wrong number of times");
        Require(capture.Destroyed == 1,
                "owner-scoped self-unregister user data was not destroyed after callback");
        Require(dispatcher.SubscriptionCount() == 0,
                "owner-scoped self-unregister callback remained registered");
        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 0,
                "owner-scoped self-unregistered callback ran twice");
    }

    struct OwnerCleanupDuringDispatchState
    {
        PlayerPrincipalEventDispatcher* Dispatcher = nullptr;
        void* Owner = nullptr;
        int FirstCalls = 0;
        int SecondCalls = 0;
        int Destroyed = 0;
        size_t Removed = 99;
    };

    void OwnerCleanupFirstCallback(const PlayerPrincipalEventView&, void* userData)
    {
        auto* state = static_cast<OwnerCleanupDuringDispatchState*>(userData);
        ++state->FirstCalls;
        Require(state->Destroyed == 0,
                "player principal owner cleanup destroyed user data before callback body");
        Require(state->Dispatcher != nullptr, "owner cleanup callback had no dispatcher");
        state->Removed = state->Dispatcher->UnregisterCallbacksForOwner(state->Owner);
        Require(state->Removed == 2, "owner cleanup during player principal dispatch removed wrong count");
        Require(state->Destroyed == 0,
                "player principal owner cleanup destroyed user data before callback returned");
    }

    void OwnerCleanupSecondCallback(const PlayerPrincipalEventView&, void* userData)
    {
        auto* state = static_cast<OwnerCleanupDuringDispatchState*>(userData);
        ++state->SecondCalls;
    }

    void CountOwnerCleanupDestroyed(void* userData)
    {
        auto* state = static_cast<OwnerCleanupDuringDispatchState*>(userData);
        ++state->Destroyed;
    }

    void TestOwnerCleanupDuringDispatchDefersDestroyAndSkipsRemovedCallbacks()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        OwnerCleanupDuringDispatchState state{&dispatcher, &owner, 0, 0, 0, 99};
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();

        const uint64_t firstId =
            dispatcher.Register(&owner, {OwnerCleanupFirstCallback, &state, CountOwnerCleanupDestroyed});
        const uint64_t secondId =
            dispatcher.Register(&owner, {OwnerCleanupSecondCallback, &state, CountOwnerCleanupDestroyed});
        Require(firstId != 0 && secondId != 0,
                "owner cleanup during player principal dispatch registrations failed");

        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 1,
                "owner cleanup during player principal dispatch ran removed callback");
        Require(state.FirstCalls == 1, "owner cleanup first player principal callback did not run");
        Require(state.SecondCalls == 0, "cleaned player principal callback ran from stale snapshot");
        Require(state.Destroyed == 2,
                "player principal owner cleanup did not destroy user data after dispatch");
        Require(dispatcher.SubscriptionCount() == 0,
                "owner cleanup during player principal dispatch left callbacks registered");
        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 0,
                "owner-cleaned player principal callback ran in a later dispatch");
        Require(state.FirstCalls == 1 && state.SecondCalls == 0,
                "owner-cleaned player principal callbacks changed after later dispatch");
    }

    struct UnregisterOtherCapture
    {
        PlayerPrincipalEventDispatcher* Dispatcher = nullptr;
        uint64_t TargetRegistrationId = 0;
        int Calls = 0;
    };

    struct RemovedSnapshotState
    {
        int Calls = 0;
        int Destroys = 0;
    };

    void UnregisterOtherCallback(const PlayerPrincipalEventView&, void* userData)
    {
        auto* capture = static_cast<UnregisterOtherCapture*>(userData);
        ++capture->Calls;
        Require(capture->Dispatcher->Unregister(capture->TargetRegistrationId),
                "unregister-other callback failed to remove target");
    }

    void RemovedSnapshotCallback(const PlayerPrincipalEventView&, void* userData)
    {
        auto* state = static_cast<RemovedSnapshotState*>(userData);
        ++state->Calls;
    }

    void CountDestroy(void* userData)
    {
        auto* state = static_cast<RemovedSnapshotState*>(userData);
        ++state->Destroys;
    }

    void TestReentrantUnregisterSkipsRemovedSnapshotCallback()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        RemovedSnapshotState removedState;
        UnregisterOtherCapture unregisterOther{&dispatcher, 0, 0};
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();

        Require(dispatcher.Register(&owner, {UnregisterOtherCallback, &unregisterOther}) != 0,
                "remover registration failed");
        unregisterOther.TargetRegistrationId =
            dispatcher.Register(&owner, {RemovedSnapshotCallback, &removedState, CountDestroy});
        Require(unregisterOther.TargetRegistrationId != 0, "target registration failed");

        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 1,
                "removed snapshot callback was dispatched or remover was skipped");
        Require(unregisterOther.Calls == 1, "remover callback did not run");
        Require(removedState.Calls == 0, "removed snapshot callback still ran");
        Require(removedState.Destroys == 1, "removed callback user data was not destroyed after dispatch");
        Require(dispatcher.SubscriptionCount() == 1, "wrong subscriptions remained after reentrant unregister");
    }

    struct ReuseRegistrationDuringDispatchState
    {
        PlayerPrincipalEventDispatcher* Dispatcher = nullptr;
        int* Owner = nullptr;
        uint64_t RemovedRegistrationId = 0;
        int FirstCalls = 0;
        int RemovedCalls = 0;
        int ReplacementCalls = 0;
        uint64_t ReplacementRegistrationId = 0;
    };

    void ReuseFirstCallback(const PlayerPrincipalEventView&, void* userData)
    {
        auto* state = static_cast<ReuseRegistrationDuringDispatchState*>(userData);
        ++state->FirstCalls;
        if (state->FirstCalls != 1)
            return;

        Require(state->Dispatcher->Unregister(state->RemovedRegistrationId),
                "stale-snapshot setup could not unregister callback");
        state->Dispatcher->SetNextRegistrationIdForTesting(state->RemovedRegistrationId);
        const uint64_t replacementId = state->Dispatcher->Register(state->Owner, {
            [](const PlayerPrincipalEventView&, void* replacementUserData) {
                auto* replacementState =
                    static_cast<ReuseRegistrationDuringDispatchState*>(replacementUserData);
                ++replacementState->ReplacementCalls;
            },
            state,
        });
        state->ReplacementRegistrationId = replacementId;
        Require(replacementId != 0, "stale-snapshot replacement registration failed");
        Require(replacementId != state->RemovedRegistrationId,
                "retired registration id was reused during dispatch");
    }

    void ReuseRemovedCallback(const PlayerPrincipalEventView&, void* userData)
    {
        auto* state = static_cast<ReuseRegistrationDuringDispatchState*>(userData);
        ++state->RemovedCalls;
    }

    void TestRetiredRegistrationIdDoesNotReactivateStaleSnapshot()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        ReuseRegistrationDuringDispatchState state{&dispatcher, &owner, 0, 0, 0, 0};
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();

        Require(dispatcher.Register(&owner, {ReuseFirstCallback, &state}) != 0,
                "stale-snapshot first registration failed");
        state.RemovedRegistrationId = dispatcher.Register(&owner, {ReuseRemovedCallback, &state});
        Require(state.RemovedRegistrationId != 0, "stale-snapshot removed registration failed");

        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 1,
                "stale snapshot reused id as active callback");
        Require(state.FirstCalls == 1, "stale-snapshot first callback did not run");
        Require(state.RemovedCalls == 0, "stale-snapshot removed callback ran");
        Require(state.ReplacementCalls == 0, "replacement callback ran in stale snapshot");
        Require(state.ReplacementRegistrationId != 0,
                "stale-snapshot replacement registration id was not recorded");
        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 2,
                "replacement callback was not active for later dispatch");
        Require(state.FirstCalls == 2, "stale-snapshot first callback did not run later");
        Require(state.RemovedCalls == 0, "stale-snapshot removed callback ran later");
        Require(state.ReplacementCalls == 1, "replacement callback did not run later");
    }

    struct BlockingCallbackState
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        bool Entered = false;
        bool Release = false;
    };

    void BlockingCallback(const PlayerPrincipalEventView&, void* userData)
    {
        auto* state = static_cast<BlockingCallbackState*>(userData);
        std::unique_lock<std::mutex> lock(state->Mutex);
        state->Entered = true;
        state->Cv.notify_all();
        state->Cv.wait(lock, [&state]() { return state->Release; });
    }

    void TestOwnerCleanupWaitsForInFlightDispatch()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        BlockingCallbackState state;
        std::atomic<bool> cleanupFinished{false};
        size_t removed = 0;
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();

        Require(dispatcher.Register(&owner, {BlockingCallback, &state}) != 0,
                "blocking callback registration failed");

        std::thread dispatchThread([&]() {
            Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 1, "blocking callback did not dispatch");
        });

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() { return state.Entered; }),
                    "blocking callback did not enter");
        }

        std::thread cleanupThread([&]() {
            removed = dispatcher.UnregisterCallbacksForOwner(&owner);
            cleanupFinished.store(true, std::memory_order_release);
        });

        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        Require(!cleanupFinished.load(std::memory_order_acquire),
                "owner cleanup completed while callback was still in flight");

        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            state.Release = true;
        }
        state.Cv.notify_all();

        dispatchThread.join();
        cleanupThread.join();

        Require(cleanupFinished.load(std::memory_order_acquire), "owner cleanup did not complete");
        Require(removed == 1, "owner cleanup removed wrong callback count after dispatch");
        Require(dispatcher.SubscriptionCount() == 0, "owner callback survived cleanup after dispatch");
    }

    struct DeferredDestroyState
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        bool CallbackEntered = false;
        bool DestroyEntered = false;
        bool ReleaseCallback = false;
        bool ReleaseDestroy = false;
    };

    void BlockingDestroyCallback(const PlayerPrincipalEventView&, void* userData)
    {
        auto* state = static_cast<DeferredDestroyState*>(userData);
        std::unique_lock<std::mutex> lock(state->Mutex);
        state->CallbackEntered = true;
        state->Cv.notify_all();
        state->Cv.wait(lock, [&state]() { return state->ReleaseCallback; });
    }

    void BlockingDestroy(void* userData)
    {
        auto* state = static_cast<DeferredDestroyState*>(userData);
        std::unique_lock<std::mutex> lock(state->Mutex);
        state->DestroyEntered = true;
        state->Cv.notify_all();
        state->Cv.wait(lock, [&state]() { return state->ReleaseDestroy; });
    }

    void TestOwnerCleanupWaitsForDeferredDestroyAfterInFlightDispatch()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        DeferredDestroyState state;
        std::atomic<bool> cleanupFinished{false};
        std::atomic<bool> secondCleanupFinished{false};
        size_t secondRemoved = 99;
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();

        const uint64_t id = dispatcher.Register(&owner, {BlockingDestroyCallback, &state, BlockingDestroy});
        Require(id != 0, "deferred destroy player principal callback registration failed");

        std::thread dispatchThread([&]() {
            Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 1,
                    "deferred destroy player principal callback did not dispatch");
        });

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock,
                                      std::chrono::seconds(2),
                                      [&state]() { return state.CallbackEntered; }),
                    "deferred destroy player principal callback did not enter");
        }

        std::thread cleanupThread([&]() {
            Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 1,
                    "owner cleanup removed wrong deferred destroy player principal callback count");
            cleanupFinished.store(true, std::memory_order_release);
        });

        const auto cleanupDeadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (dispatcher.SubscriptionCount() != 0 && std::chrono::steady_clock::now() < cleanupDeadline)
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        Require(dispatcher.SubscriptionCount() == 0,
                "owner cleanup did not remove deferred destroy player principal callback during dispatch");
        Require(!cleanupFinished.load(std::memory_order_acquire),
                "owner cleanup completed before deferred destroy player principal dispatch was released");

        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            state.ReleaseCallback = true;
        }
        state.Cv.notify_all();

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock,
                                      std::chrono::seconds(2),
                                      [&state]() { return state.DestroyEntered; }),
                    "deferred destroy player principal cleanup did not run");
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        Require(!cleanupFinished.load(std::memory_order_acquire),
                "owner cleanup completed while deferred destroy player principal cleanup was still running");

        std::thread secondCleanupThread([&]() {
            secondRemoved = dispatcher.UnregisterCallbacksForOwner(&owner);
            secondCleanupFinished.store(true, std::memory_order_release);
        });

        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        Require(!secondCleanupFinished.load(std::memory_order_acquire),
                "no-op owner cleanup completed while deferred destroy player principal cleanup was still running");

        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            state.ReleaseDestroy = true;
        }
        state.Cv.notify_all();

        dispatchThread.join();
        cleanupThread.join();
        secondCleanupThread.join();

        Require(cleanupFinished.load(std::memory_order_acquire),
                "owner cleanup did not complete after deferred destroy player principal cleanup");
        Require(secondCleanupFinished.load(std::memory_order_acquire),
                "no-op owner cleanup did not complete after deferred destroy player principal cleanup");
        Require(secondRemoved == 0,
                "no-op owner cleanup removed callbacks after deferred destroy player principal cleanup");
        Require(dispatcher.SubscriptionCount() == 0,
                "deferred destroy player principal callback survived cleanup");
    }

    struct RetryingGranularDestroyState
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        bool CallbackEntered = false;
        bool ReleaseCallback = false;
        int DestroyCalls = 0;
        int FailuresRemaining = 1;
    };

    void BlockingGranularDestroyCallback(const PlayerPrincipalEventView&, void* userData)
    {
        auto* state = static_cast<RetryingGranularDestroyState*>(userData);
        std::unique_lock<std::mutex> lock(state->Mutex);
        state->CallbackEntered = true;
        state->Cv.notify_all();
        state->Cv.wait(lock, [&state]() { return state->ReleaseCallback; });
    }

    void FailsOnceGranularDestroy(void* userData)
    {
        auto* state = static_cast<RetryingGranularDestroyState*>(userData);
        std::lock_guard<std::mutex> lock(state->Mutex);
        ++state->DestroyCalls;
        if (state->FailuresRemaining > 0)
        {
            --state->FailuresRemaining;
            throw std::runtime_error("expected granular player principal destroy failure");
        }
    }

    void TestGranularUnregisterPropagatesDeferredDestroyFailure()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        RetryingGranularDestroyState state;
        std::atomic<bool> unregisterThrew{false};
        std::atomic<bool> unregisterFinished{false};
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();

        const uint64_t id = dispatcher.Register(&owner, {
            BlockingGranularDestroyCallback,
            &state,
            FailsOnceGranularDestroy,
        });
        Require(id != 0, "granular deferred destroy player principal registration failed");

        std::thread dispatchThread([&dispatcher, &bools]() {
            Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 1,
                    "granular deferred destroy player principal callback did not dispatch");
        });

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock,
                                      std::chrono::seconds(2),
                                      [&state]() { return state.CallbackEntered; }),
                    "granular deferred destroy player principal callback did not enter");
        }

        std::thread unregisterThread([&]() {
            try
            {
                (void)dispatcher.Unregister(id);
            }
            catch (const std::runtime_error&)
            {
                unregisterThrew.store(true, std::memory_order_release);
            }
            unregisterFinished.store(true, std::memory_order_release);
        });

        const auto cleanupDeadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (dispatcher.SubscriptionCount() != 0 && std::chrono::steady_clock::now() < cleanupDeadline)
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        Require(dispatcher.SubscriptionCount() == 0,
                "granular unregister did not remove player principal callback during dispatch");
        Require(!unregisterFinished.load(std::memory_order_acquire),
                "granular unregister completed before deferred destroy player principal dispatch was released");

        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            state.ReleaseCallback = true;
        }
        state.Cv.notify_all();

        dispatchThread.join();
        unregisterThread.join();

        Require(unregisterThrew.load(std::memory_order_acquire),
                "granular unregister hid deferred player principal DestroyUserData failure");
        Require(state.DestroyCalls == 2,
                "granular unregister did not retry the failed deferred player principal DestroyUserData");
        Require(dispatcher.SubscriptionCount() == 0,
                "granular unregister left player principal callback dispatchable after failure");
        Require(!dispatcher.Unregister(id),
                "completed granular player principal unregister was not idempotent");
    }

    void TestCrossFamilyCallbackSuppressesDeferredCleanupWait()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        BlockingCallbackState state;
        std::atomic<bool> cleanupFinished{false};
        size_t removed = 0;
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();

        Require(dispatcher.Register(&owner, {BlockingCallback, &state}) != 0,
                "cross-family blocking callback registration failed");

        std::thread dispatchThread([&]() {
            Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 1,
                    "cross-family blocking callback did not dispatch");
        });

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() { return state.Entered; }),
                    "cross-family blocking callback did not enter");
        }

        std::thread cleanupThread([&]() {
            Obelisk::Core::GameplayCallbackScope callbackScope(Obelisk::Core::GameplayCallbackFamily::Chat);
            removed = dispatcher.UnregisterCallbacksForOwner(&owner);
            cleanupFinished.store(true, std::memory_order_release);
        });

        bool finishedBeforeRelease = false;
        for (int attempt = 0; attempt < 20; ++attempt)
        {
            if (cleanupFinished.load(std::memory_order_acquire))
            {
                finishedBeforeRelease = true;
                break;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }

        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            state.Release = true;
        }
        state.Cv.notify_all();

        dispatchThread.join();
        cleanupThread.join();

        Require(finishedBeforeRelease,
                "cross-family gameplay callback waited for player principal deferred cleanup");
        Require(removed == 1, "cross-family cleanup removed wrong callback count");
        Require(dispatcher.SubscriptionCount() == 0, "cross-family cleanup left callback registered");
    }

    void TestOwnerCleanupRemovesOnlyMatchingOwner()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        int otherOwner = 0;
        Capture ownerCapture;
        Capture otherCapture;
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();

        Require(dispatcher.Register(&owner, {CaptureCallback, &ownerCapture}) != 0,
                "owner callback registration failed");
        Require(dispatcher.Register(&owner, {CaptureCallback, &ownerCapture}) != 0,
                "second owner callback registration failed");
        Require(dispatcher.Register(&otherOwner, {CaptureCallback, &otherCapture}) != 0,
                "other owner callback registration failed");

        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 2,
                "owner cleanup removed wrong callback count");
        Require(dispatcher.SubscriptionCount() == 1, "owner cleanup removed unrelated callback");
        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 1,
                "remaining owner callback did not dispatch");
        Require(ownerCapture.Calls == 0, "cleaned owner callback still ran");
        Require(otherCapture.Calls == 1, "other owner callback did not run");
    }

    void TestCallbackExceptionsAreContained()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();

        Require(dispatcher.Register(&owner, {ThrowingCallback, nullptr}) != 0,
                "throwing callback registration failed");
        Require(dispatcher.Register(&owner, {ThrowingUnknownCallback, nullptr}) != 0,
                "unknown throwing callback registration failed");
        Require(dispatcher.Register(&owner, {CaptureCallback, &capture}) != 0,
                "capture callback registration failed");

        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 1,
                "exception containment returned wrong successful dispatch count");
        Require(capture.Calls == 1, "callback after throwing callbacks did not run");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 3,
                "owner cleanup after exception containment removed wrong count");
    }

    void TestOwnerCleanupPropagatesDestroyUserDataFailure()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        DestroyFailureState state;

        Require(dispatcher.Register(&owner, {NoopCallback, &state, ThrowingDestroyUserData}) != 0,
                "throwing destroy player principal registration failed");
        Require(dispatcher.Register(&owner, {NoopCallback, &state, CountingDestroyUserData}) != 0,
                "counting destroy player principal registration failed");

        bool threw = false;
        try
        {
            (void)dispatcher.UnregisterCallbacksForOwner(&owner);
        }
        catch (const std::runtime_error&)
        {
            threw = true;
        }

        Require(threw, "owner cleanup hid throwing player principal DestroyUserData");
        Require(state.Calls == 2, "owner cleanup did not attempt all player principal DestroyUserData callbacks");
        Require(dispatcher.SubscriptionCount() == 0,
                "owner cleanup failure left player principal callbacks registered");
    }

    struct RetryDestroyFailureState
    {
        int FailingCalls = 0;
        int CountingCalls = 0;
        bool FailNext = true;
    };

    void FailsOnceDestroyUserData(void* userData)
    {
        auto* state = static_cast<RetryDestroyFailureState*>(userData);
        ++state->FailingCalls;
        if (state->FailNext)
        {
            state->FailNext = false;
            throw std::runtime_error("expected one-shot player principal destroy failure");
        }
    }

    void CountRetryDestroyUserData(void* userData)
    {
        auto* state = static_cast<RetryDestroyFailureState*>(userData);
        ++state->CountingCalls;
    }

    void TestOwnerCleanupRetriesFailedDestroyUserData()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        RetryDestroyFailureState state;

        Require(dispatcher.Register(&owner, {NoopCallback, &state, FailsOnceDestroyUserData}) != 0,
                "failing retry player principal registration failed");
        Require(dispatcher.Register(&owner, {NoopCallback, &state, CountRetryDestroyUserData}) != 0,
                "counting retry player principal registration failed");

        bool threw = false;
        try
        {
            (void)dispatcher.UnregisterCallbacksForOwner(&owner);
        }
        catch (const std::runtime_error&)
        {
            threw = true;
        }

        Require(threw, "owner cleanup hid one-shot player principal DestroyUserData failure");
        Require(state.FailingCalls == 1, "first cleanup did not call failing player principal destroy once");
        Require(state.CountingCalls == 1, "first cleanup did not attempt successful player principal destroy");

        const size_t retryRemoved = dispatcher.UnregisterCallbacksForOwner(&owner);
        Require(retryRemoved == 1, "retry cleanup did not report pending failed player principal destroy");
        Require(state.FailingCalls == 2, "retry cleanup did not retry failed player principal DestroyUserData");
        Require(state.CountingCalls == 1, "retry cleanup repeated successful player principal DestroyUserData");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 0,
                "completed player principal cleanup was not idempotent");
        Require(dispatcher.SubscriptionCount() == 0, "retry cleanup left player principal callbacks dispatchable");
    }

    void TestOwnerCleanupRetrySetupFailureRetainsPendingDestroyUserData()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        RetryDestroyFailureState state;

        Require(dispatcher.Register(&owner, {NoopCallback, &state, FailsOnceDestroyUserData}) != 0,
                "retry setup failure player principal registration failed");

        bool firstCleanupThrew = false;
        try
        {
            (void)dispatcher.UnregisterCallbacksForOwner(&owner);
        }
        catch (const std::runtime_error&)
        {
            firstCleanupThrew = true;
        }

        Require(firstCleanupThrew,
                "retry setup failure fixture did not create a retained DestroyUserData failure");
        Require(state.FailingCalls == 1,
                "retry setup failure fixture did not attempt first DestroyUserData cleanup");
        Require(dispatcher.SubscriptionCount() == 0,
                "retry setup failure fixture left callback dispatchable after first cleanup");

        dispatcher.FailNextFailedOwnerDestroyRetrySetupForTesting();
        bool setupFailureThrew = false;
        try
        {
            (void)dispatcher.UnregisterCallbacksForOwner(&owner);
        }
        catch (const std::bad_alloc&)
        {
            setupFailureThrew = true;
        }

        Require(setupFailureThrew,
                "owner cleanup retry setup failure did not propagate to PluginManager");
        Require(state.FailingCalls == 1,
                "owner cleanup retry setup failure reran DestroyUserData before setup completed");

        const size_t retryRemoved = dispatcher.UnregisterCallbacksForOwner(&owner);
        Require(retryRemoved == 1,
                "owner cleanup retry setup failure did not retain pending DestroyUserData for retry");
        Require(state.FailingCalls == 2,
                "owner cleanup retry setup failure did not retry retained DestroyUserData");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 0,
                "owner cleanup retry setup failure retry was not idempotent after success");
        Require(dispatcher.SubscriptionCount() == 0,
                "owner cleanup retry setup failure left callback dispatchable");
    }

    struct DeferredMultiRetryDestroyState
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        bool CallbackEntered = false;
        bool ReleaseCallback = false;
        int FirstDestroyCalls = 0;
        int SecondDestroyCalls = 0;
        bool FirstFailNext = true;
        bool SecondFailNext = true;
    };

    void DeferredMultiRetryBlockingCallback(const PlayerPrincipalEventView&, void* userData)
    {
        auto* state = static_cast<DeferredMultiRetryDestroyState*>(userData);
        std::unique_lock<std::mutex> lock(state->Mutex);
        state->CallbackEntered = true;
        state->Cv.notify_all();
        state->Cv.wait(lock, [&state]() { return state->ReleaseCallback; });
    }

    void FirstDeferredRetryDestroyUserData(void* userData)
    {
        auto* state = static_cast<DeferredMultiRetryDestroyState*>(userData);
        ++state->FirstDestroyCalls;
        if (state->FirstFailNext)
        {
            state->FirstFailNext = false;
            throw std::runtime_error("expected first deferred player principal destroy failure");
        }
    }

    void SecondDeferredRetryDestroyUserData(void* userData)
    {
        auto* state = static_cast<DeferredMultiRetryDestroyState*>(userData);
        ++state->SecondDestroyCalls;
        if (state->SecondFailNext)
        {
            state->SecondFailNext = false;
            throw std::runtime_error("expected second deferred player principal destroy failure");
        }
    }

    void TestOwnerCleanupRetriesAllDeferredDestroyUserDataFailures()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        DeferredMultiRetryDestroyState state;
        std::atomic<bool> cleanupThrew{false};
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();

        Require(dispatcher.Register(
                    &owner,
                    {DeferredMultiRetryBlockingCallback, &state, FirstDeferredRetryDestroyUserData}) != 0,
                "first deferred multi-retry player principal registration failed");
        Require(dispatcher.Register(
                    &owner,
                    {DeferredMultiRetryBlockingCallback, &state, SecondDeferredRetryDestroyUserData}) != 0,
                "second deferred multi-retry player principal registration failed");

        std::thread dispatchThread([&]() {
            Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 1,
                    "deferred multi-retry dispatch did not skip owner-cleaned snapshot");
        });

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock,
                                      std::chrono::seconds(2),
                                      [&state]() { return state.CallbackEntered; }),
                    "deferred multi-retry callback did not enter");
        }

        std::thread cleanupThread([&]() {
            try
            {
                (void)dispatcher.UnregisterCallbacksForOwner(&owner);
            }
            catch (const std::runtime_error&)
            {
                cleanupThrew.store(true, std::memory_order_release);
            }
        });

        const auto cleanupDeadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (dispatcher.SubscriptionCount() != 0 && std::chrono::steady_clock::now() < cleanupDeadline)
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        Require(dispatcher.SubscriptionCount() == 0,
                "deferred multi-retry cleanup did not remove dispatchable callbacks");

        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            state.ReleaseCallback = true;
        }
        state.Cv.notify_all();

        dispatchThread.join();
        cleanupThread.join();

        Require(cleanupThrew.load(std::memory_order_acquire),
                "deferred multi-retry cleanup hid DestroyUserData failures");
        Require(state.FirstDestroyCalls == 1,
                "first deferred multi-retry cleanup was not attempted once");
        Require(state.SecondDestroyCalls == 1,
                "second deferred multi-retry cleanup was not attempted once");

        const size_t retryRemoved = dispatcher.UnregisterCallbacksForOwner(&owner);
        Require(retryRemoved == 2,
                "deferred multi-retry cleanup did not retain every failed subscription");
        Require(state.FirstDestroyCalls == 2,
                "first deferred multi-retry cleanup was not retried");
        Require(state.SecondDestroyCalls == 2,
                "second deferred multi-retry cleanup was not retried");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 0,
                "completed deferred multi-retry cleanup was not idempotent");
        Require(dispatcher.SubscriptionCount() == 0,
                "deferred multi-retry cleanup left callbacks dispatchable");
    }

    struct DeferredFailureRecordFallbackState
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        bool CallbackEntered = false;
        bool ReleaseCallback = false;
        int DestroyCalls = 0;
        bool FailNextDestroy = true;
    };

    void DeferredFailureRecordFallbackCallback(const PlayerPrincipalEventView&, void* userData)
    {
        auto* state = static_cast<DeferredFailureRecordFallbackState*>(userData);
        std::unique_lock<std::mutex> lock(state->Mutex);
        state->CallbackEntered = true;
        state->Cv.notify_all();
        state->Cv.wait(lock, [&state]() { return state->ReleaseCallback; });
    }

    void DeferredFailureRecordFallbackDestroyUserData(void* userData)
    {
        auto* state = static_cast<DeferredFailureRecordFallbackState*>(userData);
        ++state->DestroyCalls;
        if (state->FailNextDestroy)
        {
            state->FailNextDestroy = false;
            throw std::runtime_error("expected deferred fallback destroy failure");
        }
    }

    void TestDeferredDestroyFailureRecordStorageFailureIsRetainedForOwnerRetry()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        DeferredFailureRecordFallbackState state;
        std::atomic<bool> cleanupThrewRuntimeError{false};
        std::atomic<bool> cleanupThrewUnexpected{false};
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();

        Require(dispatcher.Register(
                    &owner,
                    {DeferredFailureRecordFallbackCallback,
                     &state,
                     DeferredFailureRecordFallbackDestroyUserData}) != 0,
                "deferred failure-record fallback registration failed");

        std::thread dispatchThread([&]() {
            Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 1,
                    "deferred failure-record fallback dispatch did not run");
        });

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock,
                                      std::chrono::seconds(2),
                                      [&state]() { return state.CallbackEntered; }),
                    "deferred failure-record fallback callback did not enter");
        }

        std::thread cleanupThread([&]() {
            try
            {
                dispatcher.FailNextDeferredDestroyFailureRecordForTesting();
                (void)dispatcher.UnregisterCallbacksForOwner(&owner);
            }
            catch (const std::runtime_error&)
            {
                cleanupThrewRuntimeError.store(true, std::memory_order_release);
            }
            catch (...)
            {
                cleanupThrewUnexpected.store(true, std::memory_order_release);
            }
        });

        const auto cleanupDeadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (dispatcher.SubscriptionCount() != 0 && std::chrono::steady_clock::now() < cleanupDeadline)
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        Require(dispatcher.SubscriptionCount() == 0,
                "deferred failure-record fallback cleanup did not remove dispatchable callback");

        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            state.ReleaseCallback = true;
        }
        state.Cv.notify_all();

        dispatchThread.join();
        cleanupThread.join();

        Require(cleanupThrewRuntimeError.load(std::memory_order_acquire),
                "deferred failure-record storage failure hid original DestroyUserData failure");
        Require(!cleanupThrewUnexpected.load(std::memory_order_acquire),
                "deferred failure-record storage fallback propagated the wrong exception type");
        Require(state.DestroyCalls == 1,
                "deferred failure-record fallback first cleanup did not destroy once");

        const size_t retryRemoved = dispatcher.UnregisterCallbacksForOwner(&owner);
        Require(retryRemoved == 1,
                "deferred failure-record fallback did not retain failed subscription for retry");
        Require(state.DestroyCalls == 2,
                "deferred failure-record fallback retry did not rerun DestroyUserData");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 0,
                "deferred failure-record fallback cleanup was not idempotent after retry");
        Require(dispatcher.SubscriptionCount() == 0,
                "deferred failure-record fallback left callback dispatchable");
    }

    void TestUnregisterIsIdempotent()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        const std::vector<PlayerPrincipalBoolValue> bools = MakeStartBools();

        const uint64_t id = dispatcher.Register(&owner, {NoopCallback, nullptr});
        Require(id != 0, "registration id was not assigned");
        Require(dispatcher.Unregister(id), "first unregister failed");
        Require(!dispatcher.Unregister(id), "second unregister was not idempotent");
        Require(dispatcher.Dispatch(MakeStartEvent(bools)) == 0, "unregistered callback ran");
    }
}

int main()
{
    try
    {
        TestPlayerPrincipalSurfaceIsInternalObservationOnly();
        TestNoSubscriberDispatchReturnsBeforePayloadCopy();
        TestDispatchCopiesBoolInputForCallbackDuration();
        TestDispatchCopiesSourceEventSequenceForAllSubscribers();
        TestDispatchSnapshotsStackAndHeapSubscribers();
        TestRegisterRejectsInvalidInput();
        TestDispatchRejectsUnknownEventShape();
        TestDispatchRejectsZeroRuntimeContext();
        TestDispatchRejectsUnexpectedLifecycleShape();
        TestRejectedStartDispatchesOnlyNoopDiagnosticShape();
        TestUnregisterForOwnerRequiresMatchingOwner();
        TestOwnerScopedUnregisterPropagatesDestroyUserDataFailureAndRetainsRetry();
        TestUnregisterPropagatesDestroyUserDataFailureAndRetainsOwnerRetry();
        TestRegistrationIdsAreRetiredAndOverflowFailsClosed();
        TestRegistrationGenerationOverflowFailsClosed();
        TestCallbackCanUnregisterItselfAndDefersDestroy();
        TestSelfUnregisterDestroyFailureIsRetainedForOwnerCleanup();
        TestWaitingOwnerCleanupObservesSelfUnregisterDeferredDestroyFailure();
        TestOwnerScopedCallbackCanUnregisterItselfAndDefersDestroy();
        TestOwnerCleanupDuringDispatchDefersDestroyAndSkipsRemovedCallbacks();
        TestReentrantUnregisterSkipsRemovedSnapshotCallback();
        TestRetiredRegistrationIdDoesNotReactivateStaleSnapshot();
        TestOwnerCleanupWaitsForInFlightDispatch();
        TestOwnerCleanupWaitsForDeferredDestroyAfterInFlightDispatch();
        TestGranularUnregisterPropagatesDeferredDestroyFailure();
        TestCrossFamilyCallbackSuppressesDeferredCleanupWait();
        TestOwnerCleanupRemovesOnlyMatchingOwner();
        TestCallbackExceptionsAreContained();
        TestOwnerCleanupPropagatesDestroyUserDataFailure();
        TestOwnerCleanupRetriesFailedDestroyUserData();
        TestOwnerCleanupRetrySetupFailureRetainsPendingDestroyUserData();
        TestOwnerCleanupRetriesAllDeferredDestroyUserDataFailures();
        TestDeferredDestroyFailureRecordStorageFailureIsRetainedForOwnerRetry();
        TestUnregisterIsIdempotent();
    }
    catch (const std::exception& e)
    {
        std::cerr << "PlayerPrincipalEventDispatcherTests failed: " << e.what() << '\n';
        return 1;
    }

    std::cout << "PlayerPrincipalEventDispatcherTests passed\n";
    return 0;
}
