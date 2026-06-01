#define OBELISK_PLAYER_PRINCIPAL_EVENT_DISPATCHER_ENABLE_TEST_HOOKS

#include "core/GameplayCallbackScope.h"
#include "core/PlayerPrincipalEventDispatcher.h"

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <iostream>
#include <limits>
#include <mutex>
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
            .Bools = bools,
        };
    }

    PlayerPrincipalEventView MakeRejectedEvent(const std::vector<PlayerPrincipalBoolValue>& bools)
    {
        return {
            .Kind = PlayerPrincipalEventKind::SessionStartRejected,
            .Action = PlayerPrincipalAction::None,
            .Bools = bools,
        };
    }

    PlayerPrincipalEventView MakeEndEvent()
    {
        return {
            .Kind = PlayerPrincipalEventKind::SessionEnd,
            .Action = PlayerPrincipalAction::CandidateInvalidated,
            .Bools = {},
        };
    }

    void CaptureCallback(const PlayerPrincipalEventView& event, void* userData)
    {
        auto* capture = static_cast<Capture*>(userData);
        ++capture->Calls;
        capture->Kind = event.Kind;
        capture->Action = event.Action;
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

    void TestPlayerPrincipalSurfaceIsInternalObservationOnly()
    {
        const auto [kind, action, bools] = PlayerPrincipalEventView{};
        const auto [field, value] = PlayerPrincipalBoolValue{};
        (void)kind;
        (void)action;
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
        Require(capture.Bools.size() == 2, "bool count mismatch");
        Require(capture.Bools[0].Field == PlayerPrincipalBoolField::BIsFromLogin,
                "first bool field mismatch");
        Require(capture.Bools[0].Value, "first bool value mismatch");
        Require(capture.Bools[1].Field == PlayerPrincipalBoolField::ReturnValue,
                "return bool field mismatch");
        Require(capture.Bools[1].Value, "return bool value mismatch");
        Require(capture.BoolPointer != sourcePointer, "dispatcher passed borrowed bool storage");
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

    void TestRegistrationIdsSkipZeroAndLiveIdsAfterWrap()
    {
        PlayerPrincipalEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;

        const uint64_t firstId = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(firstId == 1, "first registration id was not one");

        dispatcher.SetNextRegistrationIdForTesting(std::numeric_limits<uint64_t>::max());
        const uint64_t lastId = dispatcher.Register(&owner, {CaptureCallback, &capture});
        const uint64_t wrappedId = dispatcher.Register(&owner, {CaptureCallback, &capture});

        Require(lastId == std::numeric_limits<uint64_t>::max(), "last registration id was not preserved");
        Require(wrappedId == 2, "wrapped registration id did not skip zero or live ids");
        Require(wrappedId != firstId, "wrapped registration reused a live registration id");
        Require(!dispatcher.Unregister(0), "zero registration id unregistered a callback after wrap");
        Require(dispatcher.Unregister(firstId), "first registration id could not unregister");
        Require(dispatcher.Unregister(lastId), "last registration id could not unregister");
        Require(dispatcher.Unregister(wrappedId), "wrapped registration id could not unregister");
        Require(dispatcher.SubscriptionCount() == 0, "wrapped registrations survived unregister");
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
        Require(replacementId == state->RemovedRegistrationId,
                "stale-snapshot setup did not reuse removed id");
    }

    void ReuseRemovedCallback(const PlayerPrincipalEventView&, void* userData)
    {
        auto* state = static_cast<ReuseRegistrationDuringDispatchState*>(userData);
        ++state->RemovedCalls;
    }

    void TestReusedRegistrationIdDoesNotReactivateStaleSnapshot()
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
        TestDispatchSnapshotsStackAndHeapSubscribers();
        TestRegisterRejectsInvalidInput();
        TestDispatchRejectsUnknownEventShape();
        TestDispatchRejectsUnexpectedLifecycleShape();
        TestUnregisterForOwnerRequiresMatchingOwner();
        TestRegistrationIdsSkipZeroAndLiveIdsAfterWrap();
        TestCallbackCanUnregisterItselfAndDefersDestroy();
        TestOwnerScopedCallbackCanUnregisterItselfAndDefersDestroy();
        TestOwnerCleanupDuringDispatchDefersDestroyAndSkipsRemovedCallbacks();
        TestReentrantUnregisterSkipsRemovedSnapshotCallback();
        TestReusedRegistrationIdDoesNotReactivateStaleSnapshot();
        TestOwnerCleanupWaitsForInFlightDispatch();
        TestOwnerCleanupWaitsForDeferredDestroyAfterInFlightDispatch();
        TestCrossFamilyCallbackSuppressesDeferredCleanupWait();
        TestOwnerCleanupRemovesOnlyMatchingOwner();
        TestCallbackExceptionsAreContained();
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
