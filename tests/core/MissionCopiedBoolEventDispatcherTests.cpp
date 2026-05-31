#define OBELISK_MISSION_COPIED_BOOL_EVENT_DISPATCHER_ENABLE_TEST_HOOKS

#include "core/MissionCopiedBoolEventDispatcher.h"

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
    using Obelisk::Core::MissionCopiedBoolEventCallback;
    using Obelisk::Core::MissionCopiedBoolEventDispatcher;
    using Obelisk::Core::MissionCopiedBoolEventKind;
    using Obelisk::Core::MissionCopiedBoolEventView;
    using Obelisk::Core::MissionCopiedBoolField;
    using Obelisk::Core::MissionCopiedBoolValue;

    static_assert(std::is_same_v<
                      std::invoke_result_t<MissionCopiedBoolEventCallback,
                                           const MissionCopiedBoolEventView&,
                                           void*>,
                      void>,
                  "Mission copied-bool callbacks must not expose block/override return values");
    static_assert(std::is_same_v<decltype(MissionCopiedBoolEventView::Bools),
                                 std::span<const MissionCopiedBoolValue>>,
                  "Mission copied-bool dispatch must expose only immutable copied bool storage");
    static_assert(std::is_const_v<decltype(MissionCopiedBoolEventView::Bools)::element_type>,
                  "Mission copied-bool payload elements must remain read-only to callbacks");

    struct Capture
    {
        int Calls = 0;
        MissionCopiedBoolEventKind Kind = MissionCopiedBoolEventKind::AddPlayerToMission;
        std::vector<MissionCopiedBoolValue> Bools;
        const MissionCopiedBoolValue* BoolPointer = nullptr;
    };

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    std::vector<MissionCopiedBoolValue> MakeAddPlayerBools(bool forceAdd = true, bool returnValue = false)
    {
        return {
            {.Field = MissionCopiedBoolField::BForceAdd, .Value = forceAdd},
            {.Field = MissionCopiedBoolField::ReturnValue, .Value = returnValue},
        };
    }

    std::vector<MissionCopiedBoolValue> MakeAllowLeaveBools(bool returnValue = true)
    {
        return {{
            .Field = MissionCopiedBoolField::ReturnValue,
            .Value = returnValue,
        }};
    }

    std::vector<MissionCopiedBoolValue> MakeRemovedBools(bool fromComplete = true, bool lastPhaseSuccess = false)
    {
        return {
            {.Field = MissionCopiedBoolField::BFromMissionCompleteEvent, .Value = fromComplete},
            {.Field = MissionCopiedBoolField::BLastPhaseSuccess, .Value = lastPhaseSuccess},
        };
    }

    MissionCopiedBoolEventView MakeEvent(MissionCopiedBoolEventKind kind,
                                         const std::vector<MissionCopiedBoolValue>& bools)
    {
        return {
            .Kind = kind,
            .Bools = bools,
        };
    }

    MissionCopiedBoolEventView MakeEvent(const std::vector<MissionCopiedBoolValue>& bools)
    {
        return MakeEvent(MissionCopiedBoolEventKind::AddPlayerToMission, bools);
    }

    void CaptureCallback(const MissionCopiedBoolEventView& event, void* userData)
    {
        auto* capture = static_cast<Capture*>(userData);
        ++capture->Calls;
        capture->Kind = event.Kind;
        capture->Bools.assign(event.Bools.begin(), event.Bools.end());
        capture->BoolPointer = event.Bools.data();
    }

    void ThrowingCallback(const MissionCopiedBoolEventView&, void*)
    {
        throw std::runtime_error("expected mission copied-bool dispatcher test exception");
    }

    void ThrowingUnknownCallback(const MissionCopiedBoolEventView&, void*)
    {
        throw 7;
    }

    void TestMissionCopiedBoolSurfaceIsInternalObservationOnly()
    {
        const auto [kind, bools] = MissionCopiedBoolEventView{};
        const auto [field, value] = MissionCopiedBoolValue{};
        (void)kind;
        (void)bools;
        (void)field;
        (void)value;
    }

    void TestDispatchCopiesBoolInputForCallbackDuration()
    {
        MissionCopiedBoolEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        const std::vector<MissionCopiedBoolValue> bools = MakeRemovedBools(false, true);
        const auto* sourcePointer = bools.data();

        const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(id != 0, "registration id was not assigned");
        Require(dispatcher.Dispatch(MakeEvent(MissionCopiedBoolEventKind::BPOnPlayerRemovedFromMission, bools)) == 1,
                "dispatch count was wrong");

        Require(capture.Calls == 1, "callback did not run");
        Require(capture.Kind == MissionCopiedBoolEventKind::BPOnPlayerRemovedFromMission,
                "event kind changed");
        Require(capture.Bools.size() == 2, "bool count mismatch");
        Require(capture.Bools[0].Field == MissionCopiedBoolField::BFromMissionCompleteEvent,
                "first bool field mismatch");
        Require(!capture.Bools[0].Value, "first bool value mismatch");
        Require(capture.Bools[1].Field == MissionCopiedBoolField::BLastPhaseSuccess,
                "second bool field mismatch");
        Require(capture.Bools[1].Value, "second bool value mismatch");
        Require(capture.BoolPointer != sourcePointer, "dispatcher passed borrowed bool storage");
    }

    void TestDispatchSnapshotsStackAndHeapSubscribers()
    {
        for (const size_t subscriberCount : {size_t{4}, size_t{5}})
        {
            MissionCopiedBoolEventDispatcher dispatcher;
            int owner = 0;
            std::vector<Capture> captures(subscriberCount);
            const std::vector<MissionCopiedBoolValue> bools = MakeAddPlayerBools(false, true);
            const auto* sourcePointer = bools.data();

            for (Capture& capture : captures)
            {
                const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
                Require(id != 0, "stack/heap subscriber registration failed");
            }
            Require(dispatcher.SubscriptionCount() == subscriberCount,
                    "stack/heap subscriber count mismatch before dispatch");

            Require(dispatcher.Dispatch(MakeEvent(bools)) == subscriberCount,
                    "stack/heap subscriber dispatch count mismatch");

            for (const Capture& capture : captures)
            {
                Require(capture.Calls == 1, "stack/heap subscriber did not run once");
                Require(capture.Kind == MissionCopiedBoolEventKind::AddPlayerToMission,
                        "stack/heap subscriber event kind mismatch");
                Require(capture.Bools.size() == 2, "stack/heap subscriber bool count mismatch");
                Require(capture.Bools[0].Field == MissionCopiedBoolField::BForceAdd,
                        "stack/heap subscriber first field mismatch");
                Require(!capture.Bools[0].Value, "stack/heap subscriber first value mismatch");
                Require(capture.Bools[1].Field == MissionCopiedBoolField::ReturnValue,
                        "stack/heap subscriber return field mismatch");
                Require(capture.Bools[1].Value, "stack/heap subscriber return value mismatch");
                Require(capture.BoolPointer != sourcePointer,
                        "stack/heap subscriber received borrowed bool storage");
            }

            Require(dispatcher.UnregisterCallbacksForOwner(&owner) == subscriberCount,
                    "stack/heap subscriber cleanup removed wrong count");
            Require(dispatcher.SubscriptionCount() == 0,
                    "stack/heap subscriber cleanup left registrations behind");
        }
    }

    void TestRegisterRejectsInvalidInput()
    {
        MissionCopiedBoolEventDispatcher dispatcher;
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
        MissionCopiedBoolEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        std::vector<MissionCopiedBoolValue> bools = MakeAddPlayerBools();
        dispatcher.Register(&owner, {CaptureCallback, &capture});

        MissionCopiedBoolEventView unknownKind = MakeEvent(bools);
        unknownKind.Kind = static_cast<MissionCopiedBoolEventKind>(99);
        Require(dispatcher.Dispatch(unknownKind) == 0, "unknown mission copied-bool event kind was dispatched");

        MissionCopiedBoolEventView unknownField = MakeEvent(bools);
        bools[0].Field = static_cast<MissionCopiedBoolField>(99);
        unknownField.Bools = bools;
        Require(dispatcher.Dispatch(unknownField) == 0, "unknown mission copied-bool field was dispatched");
        Require(capture.Calls == 0, "invalid mission copied-bool event reached callback");
    }

    void TestDispatchRejectsUnexpectedBoolShape()
    {
        MissionCopiedBoolEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        std::vector<MissionCopiedBoolValue> bools = MakeAddPlayerBools();
        dispatcher.Register(&owner, {CaptureCallback, &capture});

        bools.clear();
        Require(dispatcher.Dispatch(MakeEvent(bools)) == 0, "missing mission copied bools were dispatched");

        bools = MakeAddPlayerBools();
        bools.push_back({.Field = MissionCopiedBoolField::ReturnValue, .Value = true});
        Require(dispatcher.Dispatch(MakeEvent(bools)) == 0, "extra mission copied bool was dispatched");

        bools = MakeAddPlayerBools();
        std::swap(bools[0], bools[1]);
        Require(dispatcher.Dispatch(MakeEvent(bools)) == 0, "misordered mission copied bools were dispatched");
        Require(capture.Calls == 0, "invalid bool shapes reached callback");

        bools = MakeAddPlayerBools();
        Require(dispatcher.Dispatch(MakeEvent(MissionCopiedBoolEventKind::AddPlayerToMission, bools)) == 1,
                "valid AddPlayerToMission mission bool shape was rejected");
        bools = MakeAllowLeaveBools();
        Require(dispatcher.Dispatch(MakeEvent(MissionCopiedBoolEventKind::BPAllowPlayerToLeaveMission, bools)) == 1,
                "valid BPAllowPlayerToLeaveMission mission bool shape was rejected");
        bools = MakeRemovedBools();
        Require(dispatcher.Dispatch(MakeEvent(MissionCopiedBoolEventKind::BPOnPlayerRemovedFromMission, bools)) == 1,
                "valid BPOnPlayerRemovedFromMission mission bool shape was rejected");
        Require(capture.Calls == 3, "valid mission copied-bool events did not reach callback");
    }

    void TestUnregisterForOwnerRequiresMatchingOwner()
    {
        MissionCopiedBoolEventDispatcher dispatcher;
        int owner = 0;
        int otherOwner = 0;
        Capture capture;
        const std::vector<MissionCopiedBoolValue> bools = MakeAddPlayerBools();

        const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(id != 0, "registration id was not assigned");
        Require(!dispatcher.UnregisterCallbackForOwner(&otherOwner, id),
                "wrong owner unregistered a mission copied-bool callback");
        Require(dispatcher.Dispatch(MakeEvent(bools)) == 1, "callback was removed by wrong owner");
        Require(dispatcher.UnregisterCallbackForOwner(&owner, id),
                "matching owner could not unregister mission copied-bool callback");
        Require(!dispatcher.UnregisterCallbackForOwner(&owner, id),
                "matching owner unregister succeeded twice");
        Require(!dispatcher.UnregisterCallbackForOwner(&owner, 0),
                "zero registration id unregistered a mission copied-bool callback");
        Require(!dispatcher.UnregisterCallbackForOwner(nullptr, id),
                "null owner unregistered a mission copied-bool callback");
        Require(dispatcher.SubscriptionCount() == 0, "owner-scoped unregister left callback behind");
    }

    void TestRegistrationIdsSkipZeroAndLiveIdsAfterWrap()
    {
        MissionCopiedBoolEventDispatcher dispatcher;
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

    struct SelfUnregisterDestroyCapture
    {
        MissionCopiedBoolEventDispatcher* Dispatcher = nullptr;
        uint64_t RegistrationId = 0;
        int Calls = 0;
        int Destroyed = 0;
    };

    void SelfUnregisterWithDestroyCallback(const MissionCopiedBoolEventView&, void* userData)
    {
        auto* capture = static_cast<SelfUnregisterDestroyCapture*>(userData);
        ++capture->Calls;
        Require(capture->Destroyed == 0, "mission user data was destroyed before callback body");
        Require(capture->Dispatcher != nullptr, "self-unregister destroy callback had no dispatcher");
        Require(capture->Dispatcher->Unregister(capture->RegistrationId),
                "self-unregister with destroy from mission callback failed");
        Require(capture->Destroyed == 0, "mission user data was destroyed before callback returned");
    }

    void CountSelfUnregisterDestroyed(void* userData)
    {
        auto* capture = static_cast<SelfUnregisterDestroyCapture*>(userData);
        ++capture->Destroyed;
    }

    void TestSelfUnregisterDefersUserDataDestroyUntilCallbackReturns()
    {
        MissionCopiedBoolEventDispatcher dispatcher;
        int owner = 0;
        SelfUnregisterDestroyCapture capture{&dispatcher, 0, 0, 0};
        const std::vector<MissionCopiedBoolValue> bools = MakeAddPlayerBools();

        capture.RegistrationId = dispatcher.Register(
            &owner,
            {SelfUnregisterWithDestroyCallback, &capture, CountSelfUnregisterDestroyed});
        Require(capture.RegistrationId != 0, "self-unregister destroy registration id was not assigned");
        Require(dispatcher.Dispatch(MakeEvent(bools)) == 1,
                "self-unregister destroy mission callback did not run");
        Require(capture.Calls == 1, "self-unregister destroy mission callback ran wrong number of times");
        Require(capture.Destroyed == 1, "mission user data was not destroyed after callback returned");
        Require(dispatcher.SubscriptionCount() == 0,
                "self-unregister destroy mission callback remained registered");
        Require(dispatcher.Dispatch(MakeEvent(bools)) == 0, "self-unregistered callback ran twice");
    }

    struct OwnerCleanupDuringDispatchState
    {
        MissionCopiedBoolEventDispatcher* Dispatcher = nullptr;
        void* Owner = nullptr;
        int FirstCalls = 0;
        int SecondCalls = 0;
        int Destroyed = 0;
        size_t Removed = 99;
    };

    void OwnerCleanupFirstCallback(const MissionCopiedBoolEventView&, void* userData)
    {
        auto* state = static_cast<OwnerCleanupDuringDispatchState*>(userData);
        ++state->FirstCalls;
        Require(state->Destroyed == 0, "mission owner cleanup destroyed user data before callback body");
        Require(state->Dispatcher != nullptr, "owner cleanup callback had no dispatcher");
        state->Removed = state->Dispatcher->UnregisterCallbacksForOwner(state->Owner);
        Require(state->Removed == 2, "owner cleanup during mission dispatch removed wrong count");
        Require(state->Destroyed == 0, "mission owner cleanup destroyed user data before callback returned");
    }

    void OwnerCleanupSecondCallback(const MissionCopiedBoolEventView&, void* userData)
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
        MissionCopiedBoolEventDispatcher dispatcher;
        int owner = 0;
        OwnerCleanupDuringDispatchState state{&dispatcher, &owner, 0, 0, 0, 99};
        const std::vector<MissionCopiedBoolValue> bools = MakeAddPlayerBools();

        const uint64_t firstId =
            dispatcher.Register(&owner, {OwnerCleanupFirstCallback, &state, CountOwnerCleanupDestroyed});
        const uint64_t secondId =
            dispatcher.Register(&owner, {OwnerCleanupSecondCallback, &state, CountOwnerCleanupDestroyed});
        Require(firstId != 0 && secondId != 0, "owner cleanup during dispatch registrations failed");

        Require(dispatcher.Dispatch(MakeEvent(bools)) == 1,
                "owner cleanup during mission dispatch ran removed callback");
        Require(state.FirstCalls == 1, "owner cleanup first mission callback did not run");
        Require(state.SecondCalls == 0, "cleaned mission callback ran from stale snapshot");
        Require(state.Destroyed == 2, "mission owner cleanup did not destroy user data after dispatch");
        Require(dispatcher.SubscriptionCount() == 0,
                "owner cleanup during mission dispatch left callbacks registered");
        Require(dispatcher.Dispatch(MakeEvent(bools)) == 0,
                "owner-cleaned mission callback ran in a later dispatch");
    }

    struct ReuseRegistrationDuringDispatchState
    {
        MissionCopiedBoolEventDispatcher* Dispatcher = nullptr;
        int* Owner = nullptr;
        uint64_t RemovedRegistrationId = 0;
        int FirstCalls = 0;
        int RemovedCalls = 0;
        int ReplacementCalls = 0;
    };

    void ReuseFirstCallback(const MissionCopiedBoolEventView&, void* userData)
    {
        auto* state = static_cast<ReuseRegistrationDuringDispatchState*>(userData);
        ++state->FirstCalls;
        if (state->FirstCalls != 1)
            return;

        Require(state->Dispatcher->Unregister(state->RemovedRegistrationId),
                "mission stale-snapshot setup could not unregister callback");
        state->Dispatcher->SetNextRegistrationIdForTesting(state->RemovedRegistrationId);
        const uint64_t replacementId = state->Dispatcher->Register(state->Owner, {
            [](const MissionCopiedBoolEventView&, void* replacementUserData) {
                auto* replacementState =
                    static_cast<ReuseRegistrationDuringDispatchState*>(replacementUserData);
                ++replacementState->ReplacementCalls;
            },
            state,
        });
        Require(replacementId == state->RemovedRegistrationId,
                "mission stale-snapshot setup did not reuse removed id");
    }

    void ReuseRemovedCallback(const MissionCopiedBoolEventView&, void* userData)
    {
        auto* state = static_cast<ReuseRegistrationDuringDispatchState*>(userData);
        ++state->RemovedCalls;
    }

    void TestReusedRegistrationIdDoesNotReactivateStaleSnapshot()
    {
        MissionCopiedBoolEventDispatcher dispatcher;
        int owner = 0;
        ReuseRegistrationDuringDispatchState state{&dispatcher, &owner, 0, 0, 0, 0};
        const std::vector<MissionCopiedBoolValue> bools = MakeAddPlayerBools();

        Require(dispatcher.Register(&owner, {ReuseFirstCallback, &state}) != 0,
                "mission stale-snapshot first registration failed");
        state.RemovedRegistrationId = dispatcher.Register(&owner, {ReuseRemovedCallback, &state});
        Require(state.RemovedRegistrationId != 0, "mission stale-snapshot removed registration failed");

        Require(dispatcher.Dispatch(MakeEvent(bools)) == 1,
                "mission stale snapshot reused id as active callback");
        Require(state.FirstCalls == 1, "mission stale-snapshot first callback did not run");
        Require(state.RemovedCalls == 0, "mission stale-snapshot removed callback ran");
        Require(state.ReplacementCalls == 0, "mission replacement callback ran in stale snapshot");
        Require(dispatcher.Dispatch(MakeEvent(bools)) == 2,
                "mission replacement callback was not active for later dispatch");
        Require(state.FirstCalls == 2, "mission stale-snapshot first callback did not run later");
        Require(state.RemovedCalls == 0, "mission stale-snapshot removed callback ran later");
        Require(state.ReplacementCalls == 1, "mission replacement callback did not run later");
    }

    struct BlockingOwnerCleanupState
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        bool CallbackEntered = false;
        bool ReleaseCallback = false;
        int Calls = 0;
        int Destroyed = 0;
    };

    void BlockingOwnerCleanupCallback(const MissionCopiedBoolEventView&, void* userData)
    {
        auto* state = static_cast<BlockingOwnerCleanupState*>(userData);
        std::unique_lock<std::mutex> lock(state->Mutex);
        ++state->Calls;
        state->CallbackEntered = true;
        state->Cv.notify_all();
        state->Cv.wait(lock, [&state]() { return state->ReleaseCallback; });
        Require(state->Destroyed == 0, "mission user data was destroyed while callback was in flight");
    }

    void CountBlockingOwnerCleanupDestroyed(void* userData)
    {
        auto* state = static_cast<BlockingOwnerCleanupState*>(userData);
        std::lock_guard<std::mutex> lock(state->Mutex);
        ++state->Destroyed;
        state->Cv.notify_all();
    }

    void TestOwnerCleanupWaitsForInFlightDispatchBeforeDestroy()
    {
        MissionCopiedBoolEventDispatcher dispatcher;
        int owner = 0;
        BlockingOwnerCleanupState state;
        std::atomic<bool> cleanupFinished{false};
        size_t removed = 99;
        const std::vector<MissionCopiedBoolValue> bools = MakeAddPlayerBools();

        const uint64_t id = dispatcher.Register(&owner, {
            BlockingOwnerCleanupCallback,
            &state,
            CountBlockingOwnerCleanupDestroyed,
        });
        Require(id != 0, "blocking owner cleanup mission registration failed");

        std::thread dispatchThread([&dispatcher, &bools]() {
            Require(dispatcher.Dispatch(MakeEvent(bools)) == 1,
                    "blocking owner cleanup mission callback did not dispatch");
        });

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() { return state.CallbackEntered; }),
                    "blocking owner cleanup mission callback did not enter");
        }

        std::thread cleanupThread([&]() {
            removed = dispatcher.UnregisterCallbacksForOwner(&owner);
            cleanupFinished.store(true, std::memory_order_release);
        });

        const auto cleanupDeadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (dispatcher.SubscriptionCount() != 0 && std::chrono::steady_clock::now() < cleanupDeadline)
            std::this_thread::sleep_for(std::chrono::milliseconds(1));

        Require(dispatcher.SubscriptionCount() == 0,
                "owner cleanup did not remove mission callback during dispatch");
        Require(!cleanupFinished.load(std::memory_order_acquire),
                "owner cleanup completed while mission callback was still in flight");
        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            Require(state.Destroyed == 0, "mission user data was destroyed before dispatch finished");
            state.ReleaseCallback = true;
        }
        state.Cv.notify_all();

        dispatchThread.join();
        cleanupThread.join();

        Require(cleanupFinished.load(std::memory_order_acquire), "owner cleanup did not complete after dispatch");
        Require(removed == 1, "owner cleanup removed wrong mission callback count after dispatch");
        Require(state.Calls == 1, "blocking owner cleanup mission callback ran wrong number of times");
        Require(state.Destroyed == 1, "mission user data was not destroyed after dispatch");
        Require(dispatcher.SubscriptionCount() == 0, "owner cleanup left mission callback registered");
        Require(dispatcher.Dispatch(MakeEvent(bools)) == 0,
                "owner-cleaned mission callback ran after in-flight cleanup");
    }

    struct DeferredDestroyState
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        bool CallbackEntered = false;
        bool ReleaseCallback = false;
        bool DestroyEntered = false;
        bool ReleaseDestroy = false;
    };

    void BlockingDestroyCallback(const MissionCopiedBoolEventView&, void* userData)
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
        MissionCopiedBoolEventDispatcher dispatcher;
        int owner = 0;
        DeferredDestroyState state;
        std::atomic<bool> cleanupFinished{false};
        std::atomic<bool> secondCleanupFinished{false};
        size_t secondRemoved = 99;
        const std::vector<MissionCopiedBoolValue> bools = MakeAddPlayerBools();

        const uint64_t id = dispatcher.Register(&owner, {BlockingDestroyCallback, &state, BlockingDestroy});
        Require(id != 0, "deferred destroy mission callback registration failed");

        std::thread dispatchThread([&dispatcher, &bools]() {
            Require(dispatcher.Dispatch(MakeEvent(bools)) == 1,
                    "deferred destroy mission callback did not dispatch");
        });

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() { return state.CallbackEntered; }),
                    "deferred destroy mission callback did not enter");
        }

        std::thread cleanupThread([&]() {
            Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 1,
                    "owner cleanup removed wrong deferred destroy mission callback count");
            cleanupFinished.store(true, std::memory_order_release);
        });

        const auto cleanupDeadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (dispatcher.SubscriptionCount() != 0 && std::chrono::steady_clock::now() < cleanupDeadline)
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        Require(dispatcher.SubscriptionCount() == 0,
                "owner cleanup did not remove deferred destroy mission callback during dispatch");
        Require(!cleanupFinished.load(std::memory_order_acquire),
                "owner cleanup completed before deferred destroy mission dispatch was released");

        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            state.ReleaseCallback = true;
        }
        state.Cv.notify_all();

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() { return state.DestroyEntered; }),
                    "deferred destroy mission cleanup did not run");
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        Require(!cleanupFinished.load(std::memory_order_acquire),
                "owner cleanup completed while deferred destroy mission cleanup was still running");

        std::thread secondCleanupThread([&]() {
            secondRemoved = dispatcher.UnregisterCallbacksForOwner(&owner);
            secondCleanupFinished.store(true, std::memory_order_release);
        });

        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        Require(!secondCleanupFinished.load(std::memory_order_acquire),
                "no-op owner cleanup completed while deferred destroy mission cleanup was still running");

        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            state.ReleaseDestroy = true;
        }
        state.Cv.notify_all();

        dispatchThread.join();
        cleanupThread.join();
        secondCleanupThread.join();

        Require(cleanupFinished.load(std::memory_order_acquire),
                "owner cleanup did not complete after deferred destroy mission cleanup");
        Require(secondCleanupFinished.load(std::memory_order_acquire),
                "no-op owner cleanup did not complete after deferred destroy mission cleanup");
        Require(secondRemoved == 0, "no-op owner cleanup removed callbacks after deferred destroy");
        Require(dispatcher.SubscriptionCount() == 0, "deferred destroy mission callback survived cleanup");
    }

    void TestCallbackExceptionDoesNotStopDispatch()
    {
        MissionCopiedBoolEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        const std::vector<MissionCopiedBoolValue> bools = MakeAddPlayerBools();

        Require(dispatcher.Register(&owner, {ThrowingCallback, nullptr}) != 0,
                "throwing callback registration failed");
        Require(dispatcher.Register(&owner, {ThrowingUnknownCallback, nullptr}) != 0,
                "unknown-throwing callback registration failed");
        Require(dispatcher.Register(&owner, {CaptureCallback, &capture}) != 0,
                "capture callback registration failed");
        Require(dispatcher.Dispatch(MakeEvent(bools)) == 1,
                "throwing callback counted as successful dispatch or stopped later callback");
        Require(capture.Calls == 1, "callback after throwing mission callback did not run");
        Require(dispatcher.SubscriptionCount() == 3, "exception changed mission registrations");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 3,
                "owner cleanup after exception removed wrong callback count");
    }
}

int main()
{
    try
    {
        TestMissionCopiedBoolSurfaceIsInternalObservationOnly();
        TestDispatchCopiesBoolInputForCallbackDuration();
        TestDispatchSnapshotsStackAndHeapSubscribers();
        TestRegisterRejectsInvalidInput();
        TestDispatchRejectsUnknownEventShape();
        TestDispatchRejectsUnexpectedBoolShape();
        TestUnregisterForOwnerRequiresMatchingOwner();
        TestRegistrationIdsSkipZeroAndLiveIdsAfterWrap();
        TestSelfUnregisterDefersUserDataDestroyUntilCallbackReturns();
        TestOwnerCleanupDuringDispatchDefersDestroyAndSkipsRemovedCallbacks();
        TestReusedRegistrationIdDoesNotReactivateStaleSnapshot();
        TestOwnerCleanupWaitsForInFlightDispatchBeforeDestroy();
        TestOwnerCleanupWaitsForDeferredDestroyAfterInFlightDispatch();
        TestCallbackExceptionDoesNotStopDispatch();
    }
    catch (const std::exception& e)
    {
        std::cerr << "MissionCopiedBoolEventDispatcherTests failed: " << e.what() << "\n";
        return 1;
    }

    std::cout << "MissionCopiedBoolEventDispatcherTests passed\n";
    return 0;
}
