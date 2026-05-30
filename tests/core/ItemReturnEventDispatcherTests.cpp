#define OBELISK_ITEM_RETURN_EVENT_DISPATCHER_ENABLE_TEST_HOOKS

#include "core/ItemReturnEventDispatcher.h"

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
        Obelisk::Core::ItemReturnEventKind Kind = Obelisk::Core::ItemReturnEventKind::AllowEquipItem;
        std::vector<Obelisk::Core::ItemReturnScalarValue> Scalars;
        const Obelisk::Core::ItemReturnScalarValue* ScalarPointer = nullptr;
    };

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    std::vector<Obelisk::Core::ItemReturnScalarValue> MakeScalars(bool returnValue = true)
    {
        return {{
            .Field = Obelisk::Core::ItemReturnScalarField::ReturnValue,
            .BoolValue = returnValue,
        }};
    }

    Obelisk::Core::ItemReturnEventView MakeEvent(
        Obelisk::Core::ItemReturnEventKind kind,
        const std::vector<Obelisk::Core::ItemReturnScalarValue>& scalars)
    {
        return {
            .Kind = kind,
            .Scalars = scalars,
        };
    }

    Obelisk::Core::ItemReturnEventView MakeEvent(
        const std::vector<Obelisk::Core::ItemReturnScalarValue>& scalars)
    {
        return MakeEvent(Obelisk::Core::ItemReturnEventKind::AllowEquipItem, scalars);
    }

    void CaptureCallback(const Obelisk::Core::ItemReturnEventView& event, void* userData)
    {
        auto* capture = static_cast<Capture*>(userData);
        ++capture->Calls;
        capture->Kind = event.Kind;
        capture->Scalars.assign(event.Scalars.begin(), event.Scalars.end());
        capture->ScalarPointer = event.Scalars.data();
    }

    void ThrowingCallback(const Obelisk::Core::ItemReturnEventView&, void*)
    {
        throw std::runtime_error("expected item return dispatcher test exception");
    }

    void ThrowingUnknownCallback(const Obelisk::Core::ItemReturnEventView&, void*)
    {
        throw 7;
    }

    void TestDispatchCopiesScalarInputForCallbackDuration()
    {
        Obelisk::Core::ItemReturnEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        const std::vector<Obelisk::Core::ItemReturnScalarValue> scalars = MakeScalars(false);
        const auto* sourcePointer = scalars.data();

        const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(id != 0, "registration id was not assigned");
        Require(dispatcher.Dispatch(MakeEvent(Obelisk::Core::ItemReturnEventKind::UseItemOntoItem, scalars)) == 1,
                "dispatch count was wrong");

        Require(capture.Calls == 1, "callback did not run");
        Require(capture.Kind == Obelisk::Core::ItemReturnEventKind::UseItemOntoItem,
                "event kind changed");
        Require(capture.Scalars.size() == 1, "scalar count mismatch");
        Require(capture.Scalars[0].Field == Obelisk::Core::ItemReturnScalarField::ReturnValue,
                "return scalar field mismatch");
        Require(!capture.Scalars[0].BoolValue, "return scalar value mismatch");
        Require(capture.ScalarPointer != sourcePointer, "dispatcher passed borrowed scalar storage");
    }

    void TestRegisterRejectsInvalidInput()
    {
        Obelisk::Core::ItemReturnEventDispatcher dispatcher;
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
        Obelisk::Core::ItemReturnEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        std::vector<Obelisk::Core::ItemReturnScalarValue> scalars = MakeScalars();
        dispatcher.Register(&owner, {CaptureCallback, &capture});

        Obelisk::Core::ItemReturnEventView unknownKind = MakeEvent(scalars);
        unknownKind.Kind = static_cast<Obelisk::Core::ItemReturnEventKind>(99);
        Require(dispatcher.Dispatch(unknownKind) == 0, "unknown item return event kind was dispatched");

        Obelisk::Core::ItemReturnEventView unknownScalar = MakeEvent(scalars);
        scalars[0].Field = static_cast<Obelisk::Core::ItemReturnScalarField>(99);
        unknownScalar.Scalars = scalars;
        Require(dispatcher.Dispatch(unknownScalar) == 0, "unknown item return scalar was dispatched");
        Require(capture.Calls == 0, "invalid item return event reached callback");
    }

    void TestDispatchRejectsUnexpectedScalarShape()
    {
        Obelisk::Core::ItemReturnEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        std::vector<Obelisk::Core::ItemReturnScalarValue> scalars = MakeScalars();
        dispatcher.Register(&owner, {CaptureCallback, &capture});

        scalars.clear();
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 0,
                "missing item return scalar was dispatched");

        scalars = MakeScalars();
        scalars.push_back({
            .Field = Obelisk::Core::ItemReturnScalarField::ReturnValue,
            .BoolValue = false,
        });
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 0,
                "extra item return scalar was dispatched");
        Require(capture.Calls == 0, "invalid scalar shapes reached callback");

        scalars = MakeScalars();
        Require(dispatcher.Dispatch(MakeEvent(Obelisk::Core::ItemReturnEventKind::AllowEquipItem, scalars)) == 1,
                "valid AllowEquipItem item return shape was rejected");
        Require(dispatcher.Dispatch(MakeEvent(Obelisk::Core::ItemReturnEventKind::CanRepair, scalars)) == 1,
                "valid CanRepair item return shape was rejected");
        Require(dispatcher.Dispatch(MakeEvent(Obelisk::Core::ItemReturnEventKind::UseItemOntoItem, scalars)) == 1,
                "valid UseItemOntoItem item return shape was rejected");
        Require(capture.Calls == 3, "valid item return events did not reach callback");
    }

    void TestUnregisterForOwnerRequiresMatchingOwner()
    {
        Obelisk::Core::ItemReturnEventDispatcher dispatcher;
        int owner = 0;
        int otherOwner = 0;
        Capture capture;
        const std::vector<Obelisk::Core::ItemReturnScalarValue> scalars = MakeScalars();

        const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(id != 0, "registration id was not assigned");
        Require(!dispatcher.UnregisterCallbackForOwner(&otherOwner, id),
                "wrong owner unregistered an item return callback");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                "callback was removed by wrong owner");
        Require(dispatcher.UnregisterCallbackForOwner(&owner, id),
                "matching owner could not unregister item return callback");
        Require(!dispatcher.UnregisterCallbackForOwner(&owner, id),
                "matching owner unregister succeeded twice");
        Require(!dispatcher.UnregisterCallbackForOwner(&owner, 0),
                "zero registration id unregistered an item return callback");
        Require(!dispatcher.UnregisterCallbackForOwner(nullptr, id),
                "null owner unregistered an item return callback");
        Require(dispatcher.SubscriptionCount() == 0, "owner-scoped unregister left callback behind");
    }

    void TestRegistrationIdsSkipZeroAndLiveIdsAfterWrap()
    {
        Obelisk::Core::ItemReturnEventDispatcher dispatcher;
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
        Obelisk::Core::ItemReturnEventDispatcher* Dispatcher = nullptr;
        uint64_t RegistrationId = 0;
        int Calls = 0;
        int Destroyed = 0;
    };

    void SelfUnregisterWithDestroyCallback(const Obelisk::Core::ItemReturnEventView&, void* userData)
    {
        auto* capture = static_cast<SelfUnregisterDestroyCapture*>(userData);
        ++capture->Calls;
        Require(capture->Destroyed == 0, "item return user data was destroyed before callback body");
        Require(capture->Dispatcher != nullptr, "self-unregister destroy callback had no dispatcher");
        Require(capture->Dispatcher->Unregister(capture->RegistrationId),
                "self-unregister with destroy from item return callback failed");
        Require(capture->Destroyed == 0, "item return user data was destroyed before callback returned");
    }

    void CountSelfUnregisterDestroyed(void* userData)
    {
        auto* capture = static_cast<SelfUnregisterDestroyCapture*>(userData);
        ++capture->Destroyed;
    }

    void TestSelfUnregisterDefersUserDataDestroyUntilCallbackReturns()
    {
        Obelisk::Core::ItemReturnEventDispatcher dispatcher;
        int owner = 0;
        SelfUnregisterDestroyCapture capture{&dispatcher, 0, 0, 0};
        const std::vector<Obelisk::Core::ItemReturnScalarValue> scalars = MakeScalars();

        capture.RegistrationId = dispatcher.Register(
            &owner,
            {SelfUnregisterWithDestroyCallback, &capture, CountSelfUnregisterDestroyed});
        Require(capture.RegistrationId != 0, "self-unregister destroy registration id was not assigned");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                "self-unregister destroy item return callback did not run");
        Require(capture.Calls == 1, "self-unregister destroy item return callback ran wrong number of times");
        Require(capture.Destroyed == 1, "item return user data was not destroyed after callback returned");
        Require(dispatcher.SubscriptionCount() == 0,
                "self-unregister destroy item return callback remained registered");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 0, "self-unregistered callback ran twice");
    }

    struct OwnerCleanupDuringDispatchState
    {
        Obelisk::Core::ItemReturnEventDispatcher* Dispatcher = nullptr;
        void* Owner = nullptr;
        int FirstCalls = 0;
        int SecondCalls = 0;
        int Destroyed = 0;
        size_t Removed = 99;
    };

    void OwnerCleanupFirstCallback(const Obelisk::Core::ItemReturnEventView&, void* userData)
    {
        auto* state = static_cast<OwnerCleanupDuringDispatchState*>(userData);
        ++state->FirstCalls;
        Require(state->Destroyed == 0, "item return owner cleanup destroyed user data before callback body");
        Require(state->Dispatcher != nullptr, "owner cleanup callback had no dispatcher");
        state->Removed = state->Dispatcher->UnregisterCallbacksForOwner(state->Owner);
        Require(state->Removed == 2, "owner cleanup during item return dispatch removed wrong count");
        Require(state->Destroyed == 0, "item return owner cleanup destroyed user data before callback returned");
    }

    void OwnerCleanupSecondCallback(const Obelisk::Core::ItemReturnEventView&, void* userData)
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
        Obelisk::Core::ItemReturnEventDispatcher dispatcher;
        int owner = 0;
        OwnerCleanupDuringDispatchState state{&dispatcher, &owner, 0, 0, 0, 99};
        const std::vector<Obelisk::Core::ItemReturnScalarValue> scalars = MakeScalars();

        const uint64_t firstId =
            dispatcher.Register(&owner, {OwnerCleanupFirstCallback, &state, CountOwnerCleanupDestroyed});
        const uint64_t secondId =
            dispatcher.Register(&owner, {OwnerCleanupSecondCallback, &state, CountOwnerCleanupDestroyed});
        Require(firstId != 0 && secondId != 0, "owner cleanup during dispatch registrations failed");

        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                "owner cleanup during item return dispatch ran removed callback");
        Require(state.FirstCalls == 1, "owner cleanup first item return callback did not run");
        Require(state.SecondCalls == 0, "cleaned item return callback ran from stale snapshot");
        Require(state.Destroyed == 2, "item return owner cleanup did not destroy user data after dispatch");
        Require(dispatcher.SubscriptionCount() == 0,
                "owner cleanup during item return dispatch left callbacks registered");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 0,
                "owner-cleaned item return callback ran in a later dispatch");
        Require(state.FirstCalls == 1 && state.SecondCalls == 0,
                "owner-cleaned item return callbacks changed after later dispatch");
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

    void BlockingOwnerCleanupCallback(const Obelisk::Core::ItemReturnEventView&, void* userData)
    {
        auto* state = static_cast<BlockingOwnerCleanupState*>(userData);
        std::unique_lock<std::mutex> lock(state->Mutex);
        ++state->Calls;
        state->CallbackEntered = true;
        state->Cv.notify_all();
        state->Cv.wait(lock, [&state]() { return state->ReleaseCallback; });
        Require(state->Destroyed == 0, "item return user data was destroyed while callback was in flight");
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
        Obelisk::Core::ItemReturnEventDispatcher dispatcher;
        int owner = 0;
        BlockingOwnerCleanupState state;
        std::atomic<bool> cleanupFinished{false};
        size_t removed = 99;
        const std::vector<Obelisk::Core::ItemReturnScalarValue> scalars = MakeScalars();

        const uint64_t id = dispatcher.Register(&owner, {
            BlockingOwnerCleanupCallback,
            &state,
            CountBlockingOwnerCleanupDestroyed,
        });
        Require(id != 0, "blocking owner cleanup item return registration failed");

        std::thread dispatchThread([&dispatcher, &scalars]() {
            Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                    "blocking owner cleanup item return callback did not dispatch");
        });

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() { return state.CallbackEntered; }),
                    "blocking owner cleanup item return callback did not enter");
        }

        std::thread cleanupThread([&]() {
            removed = dispatcher.UnregisterCallbacksForOwner(&owner);
            cleanupFinished.store(true, std::memory_order_release);
        });

        const auto cleanupDeadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (dispatcher.SubscriptionCount() != 0 && std::chrono::steady_clock::now() < cleanupDeadline)
            std::this_thread::sleep_for(std::chrono::milliseconds(1));

        Require(dispatcher.SubscriptionCount() == 0,
                "owner cleanup did not remove item return callback during dispatch");
        Require(!cleanupFinished.load(std::memory_order_acquire),
                "owner cleanup completed while item return callback was still in flight");
        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            Require(state.Destroyed == 0, "item return user data was destroyed before dispatch finished");
            state.ReleaseCallback = true;
        }
        state.Cv.notify_all();

        dispatchThread.join();
        cleanupThread.join();

        Require(cleanupFinished.load(std::memory_order_acquire), "owner cleanup did not complete after dispatch");
        Require(removed == 1, "owner cleanup removed wrong item return callback count after dispatch");
        Require(state.Calls == 1, "blocking owner cleanup item return callback ran wrong number of times");
        Require(state.Destroyed == 1, "item return user data was not destroyed after dispatch");
        Require(dispatcher.SubscriptionCount() == 0, "owner cleanup left item return callback registered");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 0,
                "owner-cleaned item return callback ran after in-flight cleanup");
        Require(state.Calls == 1, "owner-cleaned item return callback ran again");
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

    void BlockingDestroyCallback(const Obelisk::Core::ItemReturnEventView&, void* userData)
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
        Obelisk::Core::ItemReturnEventDispatcher dispatcher;
        int owner = 0;
        DeferredDestroyState state;
        std::atomic<bool> cleanupFinished{false};
        std::atomic<bool> secondCleanupFinished{false};
        size_t secondRemoved = 99;
        const std::vector<Obelisk::Core::ItemReturnScalarValue> scalars = MakeScalars();

        const uint64_t id = dispatcher.Register(&owner, {BlockingDestroyCallback, &state, BlockingDestroy});
        Require(id != 0, "deferred destroy item return callback registration failed");

        std::thread dispatchThread([&dispatcher, &scalars]() {
            Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                    "deferred destroy item return callback did not dispatch");
        });

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() { return state.CallbackEntered; }),
                    "deferred destroy item return callback did not enter");
        }

        std::thread cleanupThread([&]() {
            Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 1,
                    "owner cleanup removed wrong deferred destroy item return callback count");
            cleanupFinished.store(true, std::memory_order_release);
        });

        const auto cleanupDeadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (dispatcher.SubscriptionCount() != 0 && std::chrono::steady_clock::now() < cleanupDeadline)
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        Require(dispatcher.SubscriptionCount() == 0,
                "owner cleanup did not remove deferred destroy item return callback during dispatch");
        Require(!cleanupFinished.load(std::memory_order_acquire),
                "owner cleanup completed before deferred destroy item return dispatch was released");

        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            state.ReleaseCallback = true;
        }
        state.Cv.notify_all();

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() { return state.DestroyEntered; }),
                    "deferred item return destroy did not run");
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        Require(!cleanupFinished.load(std::memory_order_acquire),
                "owner cleanup completed while deferred item return destroy was still running");

        std::thread secondCleanupThread([&]() {
            secondRemoved = dispatcher.UnregisterCallbacksForOwner(&owner);
            secondCleanupFinished.store(true, std::memory_order_release);
        });

        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        Require(!secondCleanupFinished.load(std::memory_order_acquire),
                "no-op owner cleanup completed while deferred item return destroy was still running");

        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            state.ReleaseDestroy = true;
        }
        state.Cv.notify_all();

        dispatchThread.join();
        cleanupThread.join();
        secondCleanupThread.join();

        Require(cleanupFinished.load(std::memory_order_acquire),
                "owner cleanup did not complete after deferred item return destroy");
        Require(secondCleanupFinished.load(std::memory_order_acquire),
                "no-op owner cleanup did not complete after deferred item return destroy");
        Require(secondRemoved == 0, "no-op owner cleanup removed item return callbacks after deferred destroy");
        Require(dispatcher.SubscriptionCount() == 0, "deferred destroy item return callback survived cleanup");
    }

    struct OwnerCleanupNoDispatchState
    {
        int Calls = 0;
        int Destroyed = 0;
    };

    void OwnerCleanupNoDispatchCallback(const Obelisk::Core::ItemReturnEventView&, void* userData)
    {
        auto* state = static_cast<OwnerCleanupNoDispatchState*>(userData);
        ++state->Calls;
    }

    void CountOwnerCleanupNoDispatchDestroyed(void* userData)
    {
        auto* state = static_cast<OwnerCleanupNoDispatchState*>(userData);
        ++state->Destroyed;
    }

    void TestOwnerCleanupWithoutDispatchDestroysImmediatelyAndSuppressesCallbacks()
    {
        Obelisk::Core::ItemReturnEventDispatcher dispatcher;
        int ownerA = 0;
        int ownerB = 0;
        OwnerCleanupNoDispatchState removedState;
        OwnerCleanupNoDispatchState keptState;
        const std::vector<Obelisk::Core::ItemReturnScalarValue> scalars = MakeScalars();

        Require(dispatcher.Register(
                    &ownerA,
                    {OwnerCleanupNoDispatchCallback, &removedState, CountOwnerCleanupNoDispatchDestroyed}) != 0,
                "first no-dispatch owner cleanup registration failed");
        Require(dispatcher.Register(
                    &ownerA,
                    {OwnerCleanupNoDispatchCallback, &removedState, CountOwnerCleanupNoDispatchDestroyed}) != 0,
                "second no-dispatch owner cleanup registration failed");
        Require(dispatcher.Register(&ownerB, {OwnerCleanupNoDispatchCallback, &keptState}) != 0,
                "kept no-dispatch owner cleanup registration failed");

        Require(dispatcher.UnregisterCallbacksForOwner(&ownerA) == 2,
                "no-dispatch owner cleanup removed wrong item return callback count");
        Require(removedState.Destroyed == 2, "no-dispatch owner cleanup did not destroy user data immediately");
        Require(removedState.Calls == 0, "no-dispatch owner cleanup ran removed callbacks");
        Require(dispatcher.SubscriptionCount() == 1,
                "no-dispatch owner cleanup removed the wrong item return callbacks");

        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                "kept item return callback did not run after owner cleanup");
        Require(removedState.Calls == 0, "cleaned item return callback ran after no-dispatch cleanup");
        Require(keptState.Calls == 1, "kept item return callback ran wrong number of times");
    }

    void TestCallbackExceptionDoesNotStopDispatch()
    {
        Obelisk::Core::ItemReturnEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        const std::vector<Obelisk::Core::ItemReturnScalarValue> scalars = MakeScalars();

        Require(dispatcher.Register(&owner, {ThrowingCallback, nullptr}) != 0,
                "throwing callback registration failed");
        Require(dispatcher.Register(&owner, {ThrowingUnknownCallback, nullptr}) != 0,
                "unknown-throwing callback registration failed");
        Require(dispatcher.Register(&owner, {CaptureCallback, &capture}) != 0,
                "capture callback registration failed");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                "throwing callback counted as successful dispatch or stopped later callback");
        Require(capture.Calls == 1, "callback after throwing item return callback did not run");
        Require(dispatcher.SubscriptionCount() == 3, "exception changed item return registrations");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 3,
                "owner cleanup after exception removed wrong callback count");
    }
}

int main()
{
    try
    {
        TestDispatchCopiesScalarInputForCallbackDuration();
        TestRegisterRejectsInvalidInput();
        TestDispatchRejectsUnknownEventShape();
        TestDispatchRejectsUnexpectedScalarShape();
        TestUnregisterForOwnerRequiresMatchingOwner();
        TestRegistrationIdsSkipZeroAndLiveIdsAfterWrap();
        TestSelfUnregisterDefersUserDataDestroyUntilCallbackReturns();
        TestOwnerCleanupDuringDispatchDefersDestroyAndSkipsRemovedCallbacks();
        TestOwnerCleanupWaitsForInFlightDispatchBeforeDestroy();
        TestOwnerCleanupWaitsForDeferredDestroyAfterInFlightDispatch();
        TestOwnerCleanupWithoutDispatchDestroysImmediatelyAndSuppressesCallbacks();
        TestCallbackExceptionDoesNotStopDispatch();
    }
    catch (const std::exception& e)
    {
        std::cerr << "ItemReturnEventDispatcherTests failed: " << e.what() << "\n";
        return 1;
    }

    std::cout << "ItemReturnEventDispatcherTests passed\n";
    return 0;
}
