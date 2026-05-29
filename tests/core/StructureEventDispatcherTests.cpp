#include "core/StructureEventDispatcher.h"

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
        Obelisk::Core::StructureEventKind Kind = Obelisk::Core::StructureEventKind::VerifyPinCode;
        int32_t FunctionNameIndex = -1;
        int32_t OuterNameIndex = -1;
        std::vector<Obelisk::Core::StructureScalarValue> Scalars;
        const Obelisk::Core::StructureScalarValue* ScalarPointer = nullptr;
    };

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    std::vector<Obelisk::Core::StructureScalarValue> MakeScalars()
    {
        return {
            {
                .Field = Obelisk::Core::StructureScalarField::VariantIndex,
                .Type = Obelisk::Core::StructureScalarType::Int32,
                .BoolValue = false,
                .Int32Value = 7,
            },
            {
                .Field = Obelisk::Core::StructureScalarField::ReturnValue,
                .Type = Obelisk::Core::StructureScalarType::Bool,
                .BoolValue = true,
                .Int32Value = 0,
            },
        };
    }

    Obelisk::Core::StructureEventView MakeEvent(
        const std::vector<Obelisk::Core::StructureScalarValue>& scalars)
    {
        return {
            .Kind = Obelisk::Core::StructureEventKind::SetVariant,
            .FunctionNameIndex = 7605,
            .OuterNameIndex = 7539,
            .Scalars = scalars,
        };
    }

    void CaptureCallback(const Obelisk::Core::StructureEventView& event, void* userData)
    {
        auto* capture = static_cast<Capture*>(userData);
        ++capture->Calls;
        capture->Kind = event.Kind;
        capture->FunctionNameIndex = event.FunctionNameIndex;
        capture->OuterNameIndex = event.OuterNameIndex;
        capture->Scalars.assign(event.Scalars.begin(), event.Scalars.end());
        capture->ScalarPointer = event.Scalars.data();
    }

    void ThrowingCallback(const Obelisk::Core::StructureEventView&, void*)
    {
        throw std::runtime_error("expected structure dispatcher test exception");
    }

    void TestDispatchCopiesScalarInputForCallbackDuration()
    {
        Obelisk::Core::StructureEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        const std::vector<Obelisk::Core::StructureScalarValue> scalars = MakeScalars();
        const auto* sourcePointer = scalars.data();

        const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(id != 0, "registration id was not assigned");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1, "dispatch count was wrong");

        Require(capture.Calls == 1, "callback did not run");
        Require(capture.Kind == Obelisk::Core::StructureEventKind::SetVariant, "event kind changed");
        Require(capture.FunctionNameIndex == 7605, "function name index changed");
        Require(capture.OuterNameIndex == 7539, "outer name index changed");
        Require(capture.Scalars.size() == 2, "scalar count mismatch");
        Require(capture.Scalars[0].Field == Obelisk::Core::StructureScalarField::VariantIndex,
                "first scalar field mismatch");
        Require(capture.Scalars[0].Type == Obelisk::Core::StructureScalarType::Int32,
                "first scalar type mismatch");
        Require(capture.Scalars[0].Int32Value == 7, "first scalar value mismatch");
        Require(capture.Scalars[1].Field == Obelisk::Core::StructureScalarField::ReturnValue,
                "return scalar field mismatch");
        Require(capture.Scalars[1].Type == Obelisk::Core::StructureScalarType::Bool,
                "return scalar type mismatch");
        Require(capture.Scalars[1].BoolValue, "return scalar value mismatch");
        Require(capture.ScalarPointer != sourcePointer, "dispatcher passed borrowed scalar storage");
    }

    void TestRegisterRejectsInvalidInput()
    {
        Obelisk::Core::StructureEventDispatcher dispatcher;
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
        Obelisk::Core::StructureEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        std::vector<Obelisk::Core::StructureScalarValue> scalars = MakeScalars();
        dispatcher.Register(&owner, {CaptureCallback, &capture});

        Obelisk::Core::StructureEventView unknownKind = MakeEvent(scalars);
        unknownKind.Kind = static_cast<Obelisk::Core::StructureEventKind>(99);
        Require(dispatcher.Dispatch(unknownKind) == 0, "unknown structure event kind was dispatched");

        Obelisk::Core::StructureEventView unknownScalar = MakeEvent(scalars);
        scalars[0].Field = static_cast<Obelisk::Core::StructureScalarField>(99);
        unknownScalar.Scalars = scalars;
        Require(dispatcher.Dispatch(unknownScalar) == 0, "unknown structure scalar field was dispatched");

        Obelisk::Core::StructureEventView unknownScalarType = MakeEvent(scalars);
        scalars = MakeScalars();
        scalars[0].Type = static_cast<Obelisk::Core::StructureScalarType>(99);
        unknownScalarType.Scalars = scalars;
        Require(dispatcher.Dispatch(unknownScalarType) == 0, "unknown structure scalar type was dispatched");
        Require(capture.Calls == 0, "invalid structure event reached callback");
    }

    void TestUnregisterIsIdempotent()
    {
        Obelisk::Core::StructureEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        const std::vector<Obelisk::Core::StructureScalarValue> scalars = MakeScalars();

        const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(id != 0, "registration id was not assigned");
        Require(dispatcher.Unregister(id), "first unregister failed");
        Require(!dispatcher.Unregister(id), "second unregister was not idempotent");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 0, "unregistered callback ran");
    }

    void TestUnregisterForOwnerRequiresMatchingOwner()
    {
        Obelisk::Core::StructureEventDispatcher dispatcher;
        int owner = 0;
        int otherOwner = 0;
        Capture capture;
        const std::vector<Obelisk::Core::StructureScalarValue> scalars = MakeScalars();

        const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(id != 0, "registration id was not assigned");
        Require(!dispatcher.UnregisterCallbackForOwner(&otherOwner, id),
                "wrong owner unregistered a structure callback");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                "callback was removed by wrong owner");
        Require(dispatcher.UnregisterCallbackForOwner(&owner, id),
                "matching owner could not unregister structure callback");
        Require(!dispatcher.UnregisterCallbackForOwner(&owner, id),
                "matching owner unregister succeeded twice");
        Require(!dispatcher.UnregisterCallbackForOwner(&owner, 0),
                "zero registration id unregistered a structure callback");
        Require(!dispatcher.UnregisterCallbackForOwner(nullptr, id),
                "null owner unregistered a structure callback");
        Require(dispatcher.SubscriptionCount() == 0, "owner-scoped unregister left callback behind");
    }

    void TestRegistrationIdsSkipZeroAndLiveIdsAfterWrap()
    {
        Obelisk::Core::StructureEventDispatcher dispatcher;
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
        Obelisk::Core::StructureEventDispatcher* Dispatcher = nullptr;
        uint64_t RegistrationId = 0;
        int Calls = 0;
    };

    void SelfUnregisterCallback(const Obelisk::Core::StructureEventView&, void* userData)
    {
        auto* capture = static_cast<SelfUnregisterCapture*>(userData);
        ++capture->Calls;
        Require(capture->Dispatcher != nullptr, "self-unregister callback had no dispatcher");
        Require(capture->Dispatcher->Unregister(capture->RegistrationId),
                "self-unregister from callback failed");
    }

    void TestCallbackCanUnregisterItself()
    {
        Obelisk::Core::StructureEventDispatcher dispatcher;
        int owner = 0;
        SelfUnregisterCapture capture{&dispatcher, 0, 0};
        const std::vector<Obelisk::Core::StructureScalarValue> scalars = MakeScalars();

        capture.RegistrationId = dispatcher.Register(&owner, {SelfUnregisterCallback, &capture});
        Require(capture.RegistrationId != 0, "registration id was not assigned");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1, "self-unregister callback did not run");
        Require(capture.Calls == 1, "self-unregister callback ran wrong number of times");
        Require(dispatcher.SubscriptionCount() == 0, "self-unregister callback remained registered");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 0, "self-unregistered callback ran twice");
    }

    struct ReentrantUnregisterOtherState
    {
        Obelisk::Core::StructureEventDispatcher* Dispatcher = nullptr;
        void* Owner = nullptr;
        uint64_t OtherRegistrationId = 0;
        int FirstCalls = 0;
        int SecondCalls = 0;
        int Destroyed = 0;
    };

    void ReentrantUnregisterFirstCallback(const Obelisk::Core::StructureEventView&, void* userData)
    {
        auto* state = static_cast<ReentrantUnregisterOtherState*>(userData);
        ++state->FirstCalls;
        Require(state->Dispatcher != nullptr, "reentrant unregister callback had no dispatcher");
        Require(state->Dispatcher->UnregisterCallbackForOwner(state->Owner, state->OtherRegistrationId),
                "reentrant unregister of second structure callback failed");
    }

    void ReentrantUnregisterSecondCallback(const Obelisk::Core::StructureEventView&, void* userData)
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
        Obelisk::Core::StructureEventDispatcher dispatcher;
        int owner = 0;
        ReentrantUnregisterOtherState state{&dispatcher, &owner, 0, 0, 0, 0};
        const std::vector<Obelisk::Core::StructureScalarValue> scalars = MakeScalars();

        const uint64_t firstId = dispatcher.Register(&owner, {ReentrantUnregisterFirstCallback, &state});
        state.OtherRegistrationId = dispatcher.Register(&owner, {ReentrantUnregisterSecondCallback, &state, CountDestroyed});
        Require(firstId != 0 && state.OtherRegistrationId != 0, "reentrant unregister registrations failed");

        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                "removed snapshot structure callback was dispatched");
        Require(state.FirstCalls == 1, "first reentrant structure callback did not run");
        Require(state.SecondCalls == 0, "unregistered second structure callback ran from stale snapshot");
        Require(state.Destroyed == 1, "second structure callback user data was not destroyed exactly once");
        Require(dispatcher.SubscriptionCount() == 1, "wrong structure subscription count after reentrant unregister");
    }

    struct BlockingCallbackState
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        bool Entered = false;
        bool Release = false;
    };

    void BlockingCallback(const Obelisk::Core::StructureEventView&, void* userData)
    {
        auto* state = static_cast<BlockingCallbackState*>(userData);
        std::unique_lock<std::mutex> lock(state->Mutex);
        state->Entered = true;
        state->Cv.notify_all();
        state->Cv.wait(lock, [&state]() { return state->Release; });
    }

    void TestOwnerCleanupWaitsForInFlightDispatch()
    {
        Obelisk::Core::StructureEventDispatcher dispatcher;
        int owner = 0;
        BlockingCallbackState state;
        std::atomic<bool> cleanupFinished{false};
        size_t removed = 0;
        const std::vector<Obelisk::Core::StructureScalarValue> scalars = MakeScalars();

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

    void TestOwnerCleanup()
    {
        Obelisk::Core::StructureEventDispatcher dispatcher;
        int ownerA = 0;
        int ownerB = 0;
        Capture captureA;
        Capture captureB;
        const std::vector<Obelisk::Core::StructureScalarValue> scalars = MakeScalars();

        dispatcher.Register(&ownerA, {CaptureCallback, &captureA});
        dispatcher.Register(&ownerA, {CaptureCallback, &captureA});
        dispatcher.Register(&ownerB, {CaptureCallback, &captureB});

        Require(dispatcher.UnregisterCallbacksForOwner(&ownerA) == 2, "owner cleanup removed wrong count");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1, "wrong number of callbacks after owner cleanup");
        Require(captureA.Calls == 0, "owner A callback survived cleanup");
        Require(captureB.Calls == 1, "owner B callback did not run");
    }

    void TestExceptionsDoNotStopDispatch()
    {
        Obelisk::Core::StructureEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        const std::vector<Obelisk::Core::StructureScalarValue> scalars = MakeScalars();
        dispatcher.Register(&owner, {ThrowingCallback, nullptr});
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
    TestUnregisterIsIdempotent();
    TestUnregisterForOwnerRequiresMatchingOwner();
    TestRegistrationIdsSkipZeroAndLiveIdsAfterWrap();
    TestCallbackCanUnregisterItself();
    TestReentrantUnregisterSkipsRemovedSnapshotCallback();
    TestOwnerCleanupWaitsForInFlightDispatch();
    TestOwnerCleanup();
    TestExceptionsDoNotStopDispatch();

    std::cout << "StructureEventDispatcherTests passed\n";
    return 0;
}
