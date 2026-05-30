#include "core/InventoryPolicyEventDispatcher.h"
#include "core/GameplayCallbackScope.h"

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <iostream>
#include <limits>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <vector>

namespace
{
    struct Capture
    {
        int Calls = 0;
        Obelisk::Core::InventoryPolicyEventKind Kind = Obelisk::Core::InventoryPolicyEventKind::CanUse;
        std::vector<Obelisk::Core::InventoryPolicyScalarValue> Scalars;
        const Obelisk::Core::InventoryPolicyScalarValue* ScalarPointer = nullptr;
    };

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    std::vector<Obelisk::Core::InventoryPolicyScalarValue> MakeScalars()
    {
        return {
            {
                .Field = Obelisk::Core::InventoryPolicyScalarField::BRequestedByPlayer,
                .BoolValue = true,
            },
            {
                .Field = Obelisk::Core::InventoryPolicyScalarField::ReturnValue,
                .BoolValue = false,
            },
        };
    }

    Obelisk::Core::InventoryPolicyEventView MakeEvent(
        const std::vector<Obelisk::Core::InventoryPolicyScalarValue>& scalars)
    {
        return {
            .Kind = Obelisk::Core::InventoryPolicyEventKind::AllowRemoteAddToInventory,
            .Scalars = scalars,
        };
    }

    void CaptureCallback(const Obelisk::Core::InventoryPolicyEventView& event, void* userData)
    {
        auto* capture = static_cast<Capture*>(userData);
        ++capture->Calls;
        capture->Kind = event.Kind;
        capture->Scalars.assign(event.Scalars.begin(), event.Scalars.end());
        capture->ScalarPointer = event.Scalars.data();
    }

    void ThrowingCallback(const Obelisk::Core::InventoryPolicyEventView&, void*)
    {
        throw std::runtime_error("expected inventory policy dispatcher test exception");
    }

    void ThrowingUnknownCallback(const Obelisk::Core::InventoryPolicyEventView&, void*)
    {
        throw 7;
    }

    void TestDispatchCopiesScalarInputForCallbackDuration()
    {
        Obelisk::Core::InventoryPolicyEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        const std::vector<Obelisk::Core::InventoryPolicyScalarValue> scalars = MakeScalars();
        const auto* sourcePointer = scalars.data();

        const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(id != 0, "registration id was not assigned");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1, "dispatch count was wrong");

        Require(capture.Calls == 1, "callback did not run");
        Require(capture.Kind == Obelisk::Core::InventoryPolicyEventKind::AllowRemoteAddToInventory,
                "event kind changed");
        Require(capture.Scalars.size() == 2, "scalar count mismatch");
        Require(capture.Scalars[0].Field == Obelisk::Core::InventoryPolicyScalarField::BRequestedByPlayer,
                "first scalar field mismatch");
        Require(capture.Scalars[0].BoolValue, "first scalar value mismatch");
        Require(capture.Scalars[1].Field == Obelisk::Core::InventoryPolicyScalarField::ReturnValue,
                "return scalar field mismatch");
        Require(!capture.Scalars[1].BoolValue, "return scalar value mismatch");
        Require(capture.ScalarPointer != sourcePointer, "dispatcher passed borrowed scalar storage");
    }

    void TestRegisterRejectsInvalidInput()
    {
        Obelisk::Core::InventoryPolicyEventDispatcher dispatcher;
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
        Obelisk::Core::InventoryPolicyEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        std::vector<Obelisk::Core::InventoryPolicyScalarValue> scalars = MakeScalars();
        dispatcher.Register(&owner, {CaptureCallback, &capture});

        Obelisk::Core::InventoryPolicyEventView unknownKind = MakeEvent(scalars);
        unknownKind.Kind = static_cast<Obelisk::Core::InventoryPolicyEventKind>(99);
        Require(dispatcher.Dispatch(unknownKind) == 0, "unknown inventory policy event kind was dispatched");

        Obelisk::Core::InventoryPolicyEventView unknownScalar = MakeEvent(scalars);
        scalars[0].Field = static_cast<Obelisk::Core::InventoryPolicyScalarField>(99);
        unknownScalar.Scalars = scalars;
        Require(dispatcher.Dispatch(unknownScalar) == 0, "unknown inventory policy scalar was dispatched");
        Require(capture.Calls == 0, "invalid inventory policy event reached callback");
    }

    void TestDispatchRejectsUnexpectedScalarShape()
    {
        Obelisk::Core::InventoryPolicyEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        std::vector<Obelisk::Core::InventoryPolicyScalarValue> scalars = MakeScalars();
        dispatcher.Register(&owner, {CaptureCallback, &capture});

        scalars.pop_back();
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 0,
                "missing inventory policy scalar was dispatched");

        scalars = MakeScalars();
        scalars[0].Field = Obelisk::Core::InventoryPolicyScalarField::ReturnValue;
        scalars[1].Field = Obelisk::Core::InventoryPolicyScalarField::BRequestedByPlayer;
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 0,
                "reordered inventory policy scalars were dispatched");

        scalars = {
            {
                .Field = Obelisk::Core::InventoryPolicyScalarField::BIgnoreCooldown,
                .BoolValue = true,
            },
            {
                .Field = Obelisk::Core::InventoryPolicyScalarField::ReturnValue,
                .BoolValue = false,
            },
        };
        Obelisk::Core::InventoryPolicyEventView canUse{
            .Kind = Obelisk::Core::InventoryPolicyEventKind::CanUse,
            .Scalars = scalars,
        };
        Require(dispatcher.Dispatch(canUse) == 1,
                "valid CanUse inventory policy shape was rejected");
        Require(capture.Calls == 1, "valid CanUse event did not reach callback");
    }

    void TestUnregisterForOwnerRequiresMatchingOwner()
    {
        Obelisk::Core::InventoryPolicyEventDispatcher dispatcher;
        int owner = 0;
        int otherOwner = 0;
        Capture capture;
        const std::vector<Obelisk::Core::InventoryPolicyScalarValue> scalars = MakeScalars();

        const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(id != 0, "registration id was not assigned");
        Require(!dispatcher.UnregisterCallbackForOwner(&otherOwner, id),
                "wrong owner unregistered an inventory policy callback");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                "callback was removed by wrong owner");
        Require(dispatcher.UnregisterCallbackForOwner(&owner, id),
                "matching owner could not unregister inventory policy callback");
        Require(!dispatcher.UnregisterCallbackForOwner(&owner, id),
                "matching owner unregister succeeded twice");
        Require(!dispatcher.UnregisterCallbackForOwner(&owner, 0),
                "zero registration id unregistered an inventory policy callback");
        Require(!dispatcher.UnregisterCallbackForOwner(nullptr, id),
                "null owner unregistered an inventory policy callback");
        Require(dispatcher.SubscriptionCount() == 0, "owner-scoped unregister left callback behind");
    }

    void TestRegistrationIdsSkipZeroAndLiveIdsAfterWrap()
    {
        Obelisk::Core::InventoryPolicyEventDispatcher dispatcher;
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
        Obelisk::Core::InventoryPolicyEventDispatcher* Dispatcher = nullptr;
        uint64_t RegistrationId = 0;
        int Calls = 0;
    };

    void SelfUnregisterCallback(const Obelisk::Core::InventoryPolicyEventView&, void* userData)
    {
        auto* capture = static_cast<SelfUnregisterCapture*>(userData);
        ++capture->Calls;
        Require(capture->Dispatcher != nullptr, "self-unregister callback had no dispatcher");
        Require(capture->Dispatcher->Unregister(capture->RegistrationId),
                "self-unregister from callback failed");
    }

    void TestCallbackCanUnregisterItself()
    {
        Obelisk::Core::InventoryPolicyEventDispatcher dispatcher;
        int owner = 0;
        SelfUnregisterCapture capture{&dispatcher, 0, 0};
        const std::vector<Obelisk::Core::InventoryPolicyScalarValue> scalars = MakeScalars();

        capture.RegistrationId = dispatcher.Register(&owner, {SelfUnregisterCallback, &capture});
        Require(capture.RegistrationId != 0, "registration id was not assigned");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1, "self-unregister callback did not run");
        Require(capture.Calls == 1, "self-unregister callback ran wrong number of times");
        Require(dispatcher.SubscriptionCount() == 0, "self-unregister callback remained registered");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 0, "self-unregistered callback ran twice");
    }

    struct SelfUnregisterDestroyCapture
    {
        Obelisk::Core::InventoryPolicyEventDispatcher* Dispatcher = nullptr;
        uint64_t RegistrationId = 0;
        int Calls = 0;
        int Destroyed = 0;
    };

    void SelfUnregisterWithDestroyCallback(const Obelisk::Core::InventoryPolicyEventView&, void* userData)
    {
        auto* capture = static_cast<SelfUnregisterDestroyCapture*>(userData);
        ++capture->Calls;
        Require(capture->Destroyed == 0, "inventory policy user data was destroyed before callback body");
        Require(capture->Dispatcher != nullptr, "self-unregister destroy callback had no dispatcher");
        Require(capture->Dispatcher->Unregister(capture->RegistrationId),
                "self-unregister with destroy from inventory policy callback failed");
        Require(capture->Destroyed == 0, "inventory policy user data was destroyed before callback returned");
    }

    void CountSelfUnregisterDestroyed(void* userData)
    {
        auto* capture = static_cast<SelfUnregisterDestroyCapture*>(userData);
        ++capture->Destroyed;
    }

    void TestSelfUnregisterDefersUserDataDestroyUntilCallbackReturns()
    {
        Obelisk::Core::InventoryPolicyEventDispatcher dispatcher;
        int owner = 0;
        SelfUnregisterDestroyCapture capture{&dispatcher, 0, 0, 0};
        const std::vector<Obelisk::Core::InventoryPolicyScalarValue> scalars = MakeScalars();

        capture.RegistrationId = dispatcher.Register(
            &owner,
            {SelfUnregisterWithDestroyCallback, &capture, CountSelfUnregisterDestroyed});
        Require(capture.RegistrationId != 0, "self-unregister destroy registration id was not assigned");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                "self-unregister destroy inventory policy callback did not run");
        Require(capture.Calls == 1, "self-unregister destroy inventory policy callback ran wrong number of times");
        Require(capture.Destroyed == 1, "inventory policy user data was not destroyed after callback returned");
        Require(dispatcher.SubscriptionCount() == 0,
                "self-unregister destroy inventory policy callback remained registered");
    }

    struct ReentrantUnregisterOtherState
    {
        Obelisk::Core::InventoryPolicyEventDispatcher* Dispatcher = nullptr;
        void* Owner = nullptr;
        uint64_t OtherRegistrationId = 0;
        int FirstCalls = 0;
        int SecondCalls = 0;
        int Destroyed = 0;
    };

    void ReentrantUnregisterFirstCallback(const Obelisk::Core::InventoryPolicyEventView&, void* userData)
    {
        auto* state = static_cast<ReentrantUnregisterOtherState*>(userData);
        ++state->FirstCalls;
        Require(state->Dispatcher != nullptr, "reentrant unregister callback had no dispatcher");
        Require(state->Dispatcher->UnregisterCallbackForOwner(state->Owner, state->OtherRegistrationId),
                "reentrant unregister of second inventory policy callback failed");
    }

    void ReentrantUnregisterSecondCallback(const Obelisk::Core::InventoryPolicyEventView&, void* userData)
    {
        auto* state = static_cast<ReentrantUnregisterOtherState*>(userData);
        ++state->SecondCalls;
    }

    void CountDestroyed(void* userData)
    {
        auto* state = static_cast<ReentrantUnregisterOtherState*>(userData);
        ++state->Destroyed;
    }

    void TestReentrantUnregisterSkipsRemovedSnapshotCallback()
    {
        Obelisk::Core::InventoryPolicyEventDispatcher dispatcher;
        int owner = 0;
        ReentrantUnregisterOtherState state{&dispatcher, &owner, 0, 0, 0, 0};
        const std::vector<Obelisk::Core::InventoryPolicyScalarValue> scalars = MakeScalars();

        const uint64_t firstId = dispatcher.Register(&owner, {ReentrantUnregisterFirstCallback, &state});
        state.OtherRegistrationId = dispatcher.Register(&owner, {ReentrantUnregisterSecondCallback, &state, CountDestroyed});
        Require(firstId != 0 && state.OtherRegistrationId != 0, "reentrant unregister registrations failed");

        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                "removed snapshot inventory policy callback was dispatched");
        Require(state.FirstCalls == 1, "first reentrant inventory policy callback did not run");
        Require(state.SecondCalls == 0, "unregistered second inventory policy callback ran from stale snapshot");
        Require(state.Destroyed == 1, "second inventory policy callback user data was not destroyed exactly once");
        Require(dispatcher.SubscriptionCount() == 1, "wrong inventory policy subscription count after reentrant unregister");
    }

    struct ReentrantRegisterState
    {
        Obelisk::Core::InventoryPolicyEventDispatcher* Dispatcher = nullptr;
        void* Owner = nullptr;
        uint64_t AddedRegistrationId = 0;
        int FirstCalls = 0;
        int AddedCalls = 0;
    };

    void ReentrantRegisteredCallback(const Obelisk::Core::InventoryPolicyEventView&, void* userData)
    {
        auto* state = static_cast<ReentrantRegisterState*>(userData);
        ++state->AddedCalls;
    }

    void ReentrantRegisterCallback(const Obelisk::Core::InventoryPolicyEventView&, void* userData)
    {
        auto* state = static_cast<ReentrantRegisterState*>(userData);
        ++state->FirstCalls;
        if (state->AddedRegistrationId != 0)
            return;

        Require(state->Dispatcher != nullptr, "reentrant register callback had no dispatcher");
        state->AddedRegistrationId =
            state->Dispatcher->Register(state->Owner, {ReentrantRegisteredCallback, state});
        Require(state->AddedRegistrationId != 0, "reentrant inventory policy registration failed");
        Require(state->Dispatcher->SubscriptionCount() == 2,
                "inventory policy subscription count did not include reentrant registration");
    }

    void TestReentrantRegisterDoesNotEnterCurrentSnapshot()
    {
        Obelisk::Core::InventoryPolicyEventDispatcher dispatcher;
        int owner = 0;
        ReentrantRegisterState state{&dispatcher, &owner, 0, 0, 0};
        const std::vector<Obelisk::Core::InventoryPolicyScalarValue> scalars = MakeScalars();

        const uint64_t firstId = dispatcher.Register(&owner, {ReentrantRegisterCallback, &state});
        Require(firstId != 0, "reentrant register first callback registration failed");
        Require(dispatcher.SubscriptionCount() == 1, "initial inventory policy subscription count was wrong");

        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                "reentrant registration entered the current inventory policy snapshot");
        Require(state.FirstCalls == 1, "reentrant register first callback did not run");
        Require(state.AddedRegistrationId != 0, "reentrant inventory policy registration was not recorded");
        Require(state.AddedCalls == 0, "reentrant registered inventory policy callback ran in current snapshot");
        Require(dispatcher.SubscriptionCount() == 2,
                "inventory policy subscription count did not retain reentrant registration");

        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 2,
                "reentrant registered inventory policy callback did not run on the next dispatch");
        Require(state.FirstCalls == 2, "reentrant register first callback did not run on next dispatch");
        Require(state.AddedCalls == 1, "reentrant registered inventory policy callback ran wrong number of times");
        Require(dispatcher.Unregister(firstId), "first reentrant register callback could not unregister");
        Require(dispatcher.Unregister(state.AddedRegistrationId),
                "reentrant registered inventory policy callback could not unregister");
        Require(dispatcher.SubscriptionCount() == 0,
                "reentrant register inventory policy callbacks survived unregister");
    }

    struct BlockingCallbackState
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        bool Entered = false;
        bool Release = false;
    };

    void BlockingCallback(const Obelisk::Core::InventoryPolicyEventView&, void* userData)
    {
        auto* state = static_cast<BlockingCallbackState*>(userData);
        std::unique_lock<std::mutex> lock(state->Mutex);
        state->Entered = true;
        state->Cv.notify_all();
        state->Cv.wait(lock, [&state]() { return state->Release; });
    }

    void TestOwnerCleanupWaitsForInFlightDispatch()
    {
        Obelisk::Core::InventoryPolicyEventDispatcher dispatcher;
        int owner = 0;
        BlockingCallbackState state;
        std::atomic<bool> cleanupFinished{false};
        size_t removed = 0;
        const std::vector<Obelisk::Core::InventoryPolicyScalarValue> scalars = MakeScalars();

        const uint64_t id = dispatcher.Register(&owner, {BlockingCallback, &state});
        Require(id != 0, "blocking callback registration failed");

        std::thread dispatchThread([&dispatcher, &scalars]() {
            Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1, "blocking callback did not dispatch");
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

    void TestCrossFamilyCallbackSuppressesDeferredCleanupWaitForFamily(
        Obelisk::Core::GameplayCallbackFamily family)
    {
        Obelisk::Core::InventoryPolicyEventDispatcher dispatcher;
        int owner = 0;
        BlockingCallbackState state;
        std::atomic<bool> cleanupFinished{false};
        size_t removed = 0;
        const std::vector<Obelisk::Core::InventoryPolicyScalarValue> scalars = MakeScalars();

        const uint64_t id = dispatcher.Register(&owner, {BlockingCallback, &state});
        Require(id != 0, "cross-family blocking inventory callback registration failed");

        std::thread dispatchThread([&dispatcher, &scalars]() {
            Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                    "cross-family blocking inventory callback did not dispatch");
        });

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() { return state.Entered; }),
                    "cross-family blocking inventory callback did not enter");
        }

        std::thread cleanupThread([&]() {
            Obelisk::Core::GameplayCallbackScope callbackScope(family);
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
                "cross-family gameplay callback waited for inventory deferred cleanup");
        Require(removed == 1, "cross-family inventory cleanup removed wrong callback count");
        Require(dispatcher.SubscriptionCount() == 0, "cross-family inventory cleanup left callback registered");
    }

    void TestCrossFamilyCallbackSuppressesDeferredCleanupWait()
    {
        TestCrossFamilyCallbackSuppressesDeferredCleanupWaitForFamily(
            Obelisk::Core::GameplayCallbackFamily::Chat);
        TestCrossFamilyCallbackSuppressesDeferredCleanupWaitForFamily(
            Obelisk::Core::GameplayCallbackFamily::Structure);
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

    void BlockingDestroyCallback(const Obelisk::Core::InventoryPolicyEventView&, void* userData)
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
        Obelisk::Core::InventoryPolicyEventDispatcher dispatcher;
        int owner = 0;
        DeferredDestroyState state;
        std::atomic<bool> cleanupFinished{false};
        std::atomic<bool> secondCleanupFinished{false};
        size_t secondRemoved = 99;
        const std::vector<Obelisk::Core::InventoryPolicyScalarValue> scalars = MakeScalars();

        const uint64_t id = dispatcher.Register(&owner, {BlockingDestroyCallback, &state, BlockingDestroy});
        Require(id != 0, "deferred destroy callback registration failed");

        std::thread dispatchThread([&dispatcher, &scalars]() {
            Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1, "deferred destroy callback did not dispatch");
        });

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() { return state.CallbackEntered; }),
                    "deferred destroy callback did not enter");
        }

        std::thread cleanupThread([&]() {
            Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 1,
                    "owner cleanup removed wrong deferred destroy callback count");
            cleanupFinished.store(true, std::memory_order_release);
        });

        const auto cleanupDeadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (dispatcher.SubscriptionCount() != 0 && std::chrono::steady_clock::now() < cleanupDeadline)
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        Require(dispatcher.SubscriptionCount() == 0, "owner cleanup did not remove callback during dispatch");
        Require(!cleanupFinished.load(std::memory_order_acquire),
                "owner cleanup completed before dispatch was released");

        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            state.ReleaseCallback = true;
        }
        state.Cv.notify_all();

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() { return state.DestroyEntered; }),
                    "deferred destroy did not run");
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        Require(!cleanupFinished.load(std::memory_order_acquire),
                "owner cleanup completed while deferred destroy was still running");

        std::thread secondCleanupThread([&]() {
            secondRemoved = dispatcher.UnregisterCallbacksForOwner(&owner);
            secondCleanupFinished.store(true, std::memory_order_release);
        });

        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        Require(!secondCleanupFinished.load(std::memory_order_acquire),
                "no-op owner cleanup completed while deferred destroy was still running");

        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            state.ReleaseDestroy = true;
        }
        state.Cv.notify_all();

        dispatchThread.join();
        cleanupThread.join();
        secondCleanupThread.join();

        Require(cleanupFinished.load(std::memory_order_acquire), "owner cleanup did not complete after destroy");
        Require(secondCleanupFinished.load(std::memory_order_acquire),
                "no-op owner cleanup did not complete after destroy");
        Require(secondRemoved == 0, "no-op owner cleanup removed callbacks after deferred destroy");
        Require(dispatcher.SubscriptionCount() == 0, "deferred destroy callback survived cleanup");
    }

    void TestExceptionsDoNotStopDispatch()
    {
        Obelisk::Core::InventoryPolicyEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        const std::vector<Obelisk::Core::InventoryPolicyScalarValue> scalars = MakeScalars();
        dispatcher.Register(&owner, {ThrowingCallback, nullptr});
        dispatcher.Register(&owner, {ThrowingUnknownCallback, nullptr});
        dispatcher.Register(&owner, {CaptureCallback, &capture});

        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1, "successful dispatch count ignored exception");
        Require(capture.Calls == 1, "callback after exception did not run");
    }
}

int main()
{
    TestDispatchCopiesScalarInputForCallbackDuration();
    TestRegisterRejectsInvalidInput();
    TestDispatchRejectsUnknownEventShape();
    TestDispatchRejectsUnexpectedScalarShape();
    TestUnregisterForOwnerRequiresMatchingOwner();
    TestRegistrationIdsSkipZeroAndLiveIdsAfterWrap();
    TestCallbackCanUnregisterItself();
    TestSelfUnregisterDefersUserDataDestroyUntilCallbackReturns();
    TestReentrantUnregisterSkipsRemovedSnapshotCallback();
    TestReentrantRegisterDoesNotEnterCurrentSnapshot();
    TestOwnerCleanupWaitsForInFlightDispatch();
    TestCrossFamilyCallbackSuppressesDeferredCleanupWait();
    TestOwnerCleanupWaitsForDeferredDestroyAfterInFlightDispatch();
    TestExceptionsDoNotStopDispatch();

    std::cout << "InventoryPolicyEventDispatcherTests passed\n";
    return 0;
}
