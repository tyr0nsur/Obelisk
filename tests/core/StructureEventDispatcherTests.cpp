#define OBELISK_STRUCTURE_EVENT_DISPATCHER_ENABLE_TEST_HOOKS

#include "core/StructureEventDispatcher.h"
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
                .Field = Obelisk::Core::StructureScalarField::BForceSet,
                .Type = Obelisk::Core::StructureScalarType::Bool,
                .BoolValue = true,
                .Int32Value = 0,
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

    void ThrowingUnknownCallback(const Obelisk::Core::StructureEventView&, void*)
    {
        throw 7;
    }

    void NoopCallback(const Obelisk::Core::StructureEventView&, void*)
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
        Require(capture.Scalars.size() == 3, "scalar count mismatch");
        Require(capture.Scalars[0].Field == Obelisk::Core::StructureScalarField::VariantIndex,
                "first scalar field mismatch");
        Require(capture.Scalars[0].Type == Obelisk::Core::StructureScalarType::Int32,
                "first scalar type mismatch");
        Require(capture.Scalars[0].Int32Value == 7, "first scalar value mismatch");
        Require(capture.Scalars[1].Field == Obelisk::Core::StructureScalarField::BForceSet,
                "force-set scalar field mismatch");
        Require(capture.Scalars[1].Type == Obelisk::Core::StructureScalarType::Bool,
                "force-set scalar type mismatch");
        Require(capture.Scalars[1].BoolValue, "force-set scalar value mismatch");
        Require(capture.Scalars[2].Field == Obelisk::Core::StructureScalarField::ReturnValue,
                "return scalar field mismatch");
        Require(capture.Scalars[2].Type == Obelisk::Core::StructureScalarType::Bool,
                "return scalar type mismatch");
        Require(capture.Scalars[2].BoolValue, "return scalar value mismatch");
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

    void TestDispatchRejectsFieldsOutsideEventContract()
    {
        Obelisk::Core::StructureEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        dispatcher.Register(&owner, {CaptureCallback, &capture});

        std::vector<Obelisk::Core::StructureScalarValue> returnOnly{{
            .Field = Obelisk::Core::StructureScalarField::ReturnValue,
            .Type = Obelisk::Core::StructureScalarType::Bool,
            .BoolValue = true,
            .Int32Value = 0,
        }};
        Obelisk::Core::StructureEventView pinCode{
            .Kind = Obelisk::Core::StructureEventKind::VerifyPinCode,
            .FunctionNameIndex = 7556,
            .OuterNameIndex = 7540,
            .Scalars = returnOnly,
        };
        Require(dispatcher.Dispatch(pinCode) == 1, "valid pin-code structure event was rejected");

        std::vector<Obelisk::Core::StructureScalarValue> wrongPinCode = returnOnly;
        wrongPinCode.insert(wrongPinCode.begin(),
                            {
                                .Field = Obelisk::Core::StructureScalarField::VariantIndex,
                                .Type = Obelisk::Core::StructureScalarType::Int32,
                                .BoolValue = false,
                                .Int32Value = 7,
                            });
        pinCode.Scalars = wrongPinCode;
        Require(dispatcher.Dispatch(pinCode) == 0,
                "pin-code event accepted fields outside its allowed promoted field mask");

        std::vector<Obelisk::Core::StructureScalarValue> scalars = MakeScalars();
        Obelisk::Core::StructureEventView setVariant = MakeEvent(scalars);
        Require(dispatcher.Dispatch(setVariant) == 1, "valid SetVariant structure event was rejected");

        std::swap(scalars[0], scalars[1]);
        setVariant.Scalars = scalars;
        Require(dispatcher.Dispatch(setVariant) == 0, "reordered SetVariant fields were dispatched");

        scalars = MakeScalars();
        scalars.pop_back();
        setVariant.Scalars = scalars;
        Require(dispatcher.Dispatch(setVariant) == 0, "partial SetVariant fields were dispatched");

        std::vector<Obelisk::Core::StructureScalarValue> canSeatScalars{
            {
                .Field = Obelisk::Core::StructureScalarField::BForce,
                .Type = Obelisk::Core::StructureScalarType::Bool,
                .BoolValue = true,
                .Int32Value = 0,
            },
            {
                .Field = Obelisk::Core::StructureScalarField::ReturnValue,
                .Type = Obelisk::Core::StructureScalarType::Bool,
                .BoolValue = true,
                .Int32Value = 0,
            },
        };
        Obelisk::Core::StructureEventView canSeat{
            .Kind = Obelisk::Core::StructureEventKind::CanSeat,
            .FunctionNameIndex = 8481,
            .OuterNameIndex = 7538,
            .Scalars = canSeatScalars,
        };
        Require(dispatcher.Dispatch(canSeat) == 1, "valid CanSeat structure event was rejected");

        canSeatScalars[0].Type = Obelisk::Core::StructureScalarType::Int32;
        canSeat.Scalars = canSeatScalars;
        Require(dispatcher.Dispatch(canSeat) == 0, "CanSeat accepted wrong scalar type");
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

    struct SelfUnregisterDestroyCapture
    {
        Obelisk::Core::StructureEventDispatcher* Dispatcher = nullptr;
        uint64_t RegistrationId = 0;
        int Calls = 0;
        int Destroyed = 0;
    };

    void SelfUnregisterWithDestroyCallback(const Obelisk::Core::StructureEventView&, void* userData)
    {
        auto* capture = static_cast<SelfUnregisterDestroyCapture*>(userData);
        ++capture->Calls;
        Require(capture->Destroyed == 0, "structure user data was destroyed before callback body");
        Require(capture->Dispatcher != nullptr, "self-unregister destroy callback had no dispatcher");
        Require(capture->Dispatcher->Unregister(capture->RegistrationId),
                "self-unregister with destroy from structure callback failed");
        Require(capture->Destroyed == 0, "structure user data was destroyed before callback returned");
    }

    void CountSelfUnregisterDestroyed(void* userData)
    {
        auto* capture = static_cast<SelfUnregisterDestroyCapture*>(userData);
        ++capture->Destroyed;
    }

    void TestSelfUnregisterDefersUserDataDestroyUntilCallbackReturns()
    {
        Obelisk::Core::StructureEventDispatcher dispatcher;
        int owner = 0;
        SelfUnregisterDestroyCapture capture{&dispatcher, 0, 0, 0};
        const std::vector<Obelisk::Core::StructureScalarValue> scalars = MakeScalars();

        capture.RegistrationId = dispatcher.Register(
            &owner,
            {SelfUnregisterWithDestroyCallback, &capture, CountSelfUnregisterDestroyed});
        Require(capture.RegistrationId != 0, "self-unregister destroy registration id was not assigned");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                "self-unregister destroy structure callback did not run");
        Require(capture.Calls == 1, "self-unregister destroy structure callback ran wrong number of times");
        Require(capture.Destroyed == 1, "structure user data was not destroyed after callback returned");
        Require(dispatcher.SubscriptionCount() == 0,
                "self-unregister destroy structure callback remained registered");
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

    struct ReuseRegistrationDuringDispatchState
    {
        Obelisk::Core::StructureEventDispatcher* Dispatcher = nullptr;
        int* Owner = nullptr;
        uint64_t RemovedRegistrationId = 0;
        int FirstCalls = 0;
        int RemovedCalls = 0;
        int ReplacementCalls = 0;
    };

    void ReuseFirstCallback(const Obelisk::Core::StructureEventView&, void* userData)
    {
        auto* state = static_cast<ReuseRegistrationDuringDispatchState*>(userData);
        ++state->FirstCalls;
        if (state->FirstCalls != 1)
            return;

        Require(state->Dispatcher->Unregister(state->RemovedRegistrationId),
                "structure stale-snapshot setup could not unregister callback");
        state->Dispatcher->SetNextRegistrationIdForTesting(state->RemovedRegistrationId);
        const uint64_t replacementId = state->Dispatcher->Register(state->Owner, {
            [](const Obelisk::Core::StructureEventView&, void* replacementUserData) {
                auto* replacementState =
                    static_cast<ReuseRegistrationDuringDispatchState*>(replacementUserData);
                ++replacementState->ReplacementCalls;
            },
            state,
        });
        Require(replacementId == state->RemovedRegistrationId,
                "structure stale-snapshot setup did not reuse removed id");
    }

    void ReuseRemovedCallback(const Obelisk::Core::StructureEventView&, void* userData)
    {
        auto* state = static_cast<ReuseRegistrationDuringDispatchState*>(userData);
        ++state->RemovedCalls;
    }

    void TestReusedRegistrationIdDoesNotReactivateStaleSnapshot()
    {
        Obelisk::Core::StructureEventDispatcher dispatcher;
        int owner = 0;
        ReuseRegistrationDuringDispatchState state{&dispatcher, &owner, 0, 0, 0, 0};
        const std::vector<Obelisk::Core::StructureScalarValue> scalars = MakeScalars();

        Require(dispatcher.Register(&owner, {ReuseFirstCallback, &state}) != 0,
                "structure stale-snapshot first registration failed");
        state.RemovedRegistrationId = dispatcher.Register(&owner, {ReuseRemovedCallback, &state});
        Require(state.RemovedRegistrationId != 0, "structure stale-snapshot removed registration failed");

        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                "structure stale snapshot reused id as active callback");
        Require(state.FirstCalls == 1, "structure stale-snapshot first callback did not run");
        Require(state.RemovedCalls == 0, "structure stale-snapshot removed callback ran");
        Require(state.ReplacementCalls == 0, "structure replacement callback ran in stale snapshot");
        Require(dispatcher.Dispatch(MakeEvent(scalars)) == 2,
                "structure replacement callback was not active for later dispatch");
        Require(state.FirstCalls == 2, "structure stale-snapshot first callback did not run later");
        Require(state.RemovedCalls == 0, "structure stale-snapshot removed callback ran later");
        Require(state.ReplacementCalls == 1, "structure replacement callback did not run later");
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

    void TestCrossFamilyCallbackSuppressesDeferredCleanupWaitForFamily(
        Obelisk::Core::GameplayCallbackFamily family)
    {
        Obelisk::Core::StructureEventDispatcher dispatcher;
        int owner = 0;
        BlockingCallbackState state;
        std::atomic<bool> cleanupFinished{false};
        size_t removed = 0;
        const std::vector<Obelisk::Core::StructureScalarValue> scalars = MakeScalars();

        const uint64_t id = dispatcher.Register(&owner, {BlockingCallback, &state});
        Require(id != 0, "cross-family blocking structure callback registration failed");

        std::thread dispatchThread([&dispatcher, &scalars]() {
            Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                    "cross-family blocking structure callback did not dispatch");
        });

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&state]() { return state.Entered; }),
                    "cross-family blocking structure callback did not enter");
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
                "cross-family gameplay callback waited for structure deferred cleanup");
        Require(removed == 1, "cross-family structure cleanup removed wrong callback count");
        Require(dispatcher.SubscriptionCount() == 0, "cross-family structure cleanup left callback registered");
    }

    void TestCrossFamilyCallbackSuppressesDeferredCleanupWait()
    {
        TestCrossFamilyCallbackSuppressesDeferredCleanupWaitForFamily(
            Obelisk::Core::GameplayCallbackFamily::Chat);
        TestCrossFamilyCallbackSuppressesDeferredCleanupWaitForFamily(
            Obelisk::Core::GameplayCallbackFamily::Inventory);
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

    void BlockingDestroyCallback(const Obelisk::Core::StructureEventView&, void* userData)
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
        Obelisk::Core::StructureEventDispatcher dispatcher;
        int owner = 0;
        DeferredDestroyState state;
        std::atomic<bool> cleanupFinished{false};
        std::atomic<bool> secondCleanupFinished{false};
        size_t secondRemoved = 99;
        const std::vector<Obelisk::Core::StructureScalarValue> scalars = MakeScalars();

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

    struct RetryingDeferredDestroyState
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        bool CallbackEntered = false;
        bool ReleaseCallback = false;
        int DestroyCalls = 0;
        int FailuresRemaining = 1;
    };

    void BlockingRetryDestroyCallback(const Obelisk::Core::StructureEventView&, void* userData)
    {
        auto* state = static_cast<RetryingDeferredDestroyState*>(userData);
        std::unique_lock<std::mutex> lock(state->Mutex);
        state->CallbackEntered = true;
        state->Cv.notify_all();
        state->Cv.wait(lock, [&state]() { return state->ReleaseCallback; });
    }

    void FailsThenCountsDestroy(void* userData)
    {
        auto* state = static_cast<RetryingDeferredDestroyState*>(userData);
        ++state->DestroyCalls;
        if (state->FailuresRemaining > 0)
        {
            --state->FailuresRemaining;
            throw std::runtime_error("expected deferred destroy retry failure");
        }
    }

    void TestDeferredOwnerCleanupRetainsEveryFailedDestroy()
    {
        Obelisk::Core::StructureEventDispatcher dispatcher;
        int owner = 0;
        RetryingDeferredDestroyState first;
        RetryingDeferredDestroyState second;
        std::atomic<bool> cleanupThrew{false};
        std::atomic<bool> cleanupFinished{false};
        const std::vector<Obelisk::Core::StructureScalarValue> scalars = MakeScalars();

        Require(dispatcher.Register(&owner, {BlockingRetryDestroyCallback, &first, FailsThenCountsDestroy}) != 0,
                "first retrying deferred destroy registration failed");
        Require(dispatcher.Register(&owner, {NoopCallback, &second, FailsThenCountsDestroy}) != 0,
                "second retrying deferred destroy registration failed");

        std::thread dispatchThread([&dispatcher, &scalars]() {
            Require(dispatcher.Dispatch(MakeEvent(scalars)) == 1,
                    "retrying deferred destroy callback did not dispatch");
        });

        {
            std::unique_lock<std::mutex> lock(first.Mutex);
            Require(first.Cv.wait_for(lock, std::chrono::seconds(2), [&first]() { return first.CallbackEntered; }),
                    "retrying deferred destroy callback did not enter");
        }

        std::thread cleanupThread([&]() {
            try
            {
                (void)dispatcher.UnregisterCallbacksForOwner(&owner);
            }
            catch (...)
            {
                cleanupThrew.store(true, std::memory_order_release);
            }
            cleanupFinished.store(true, std::memory_order_release);
        });

        const auto cleanupDeadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (dispatcher.SubscriptionCount() != 0 && std::chrono::steady_clock::now() < cleanupDeadline)
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        Require(dispatcher.SubscriptionCount() == 0,
                "retrying deferred destroy cleanup did not remove callbacks during dispatch");
        Require(!cleanupFinished.load(std::memory_order_acquire),
                "retrying deferred destroy cleanup finished before dispatch was released");

        {
            std::lock_guard<std::mutex> lock(first.Mutex);
            first.ReleaseCallback = true;
        }
        first.Cv.notify_all();

        dispatchThread.join();
        cleanupThread.join();

        Require(cleanupThrew.load(std::memory_order_acquire),
                "retrying deferred destroy cleanup did not propagate first failure");
        Require(first.DestroyCalls == 1, "first deferred destroy was not attempted once before retry");
        Require(second.DestroyCalls == 1, "second deferred destroy was not attempted once before retry");

        const size_t retryRemoved = dispatcher.UnregisterCallbacksForOwner(&owner);
        Require(retryRemoved == 2, "retry did not retain both failed deferred destroys");
        Require(first.DestroyCalls == 2, "retry did not rerun first failed deferred destroy");
        Require(second.DestroyCalls == 2, "retry did not rerun second failed deferred destroy");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 0,
                "completed deferred destroy retry was not idempotent");
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

    void TestOwnerCleanupPropagatesDestroyUserDataFailure()
    {
        Obelisk::Core::StructureEventDispatcher dispatcher;
        int owner = 0;
        DestroyFailureState state;

        Require(dispatcher.Register(&owner, {NoopCallback, &state, ThrowingDestroyUserData}) != 0,
                "throwing destroy structure registration failed");
        Require(dispatcher.Register(&owner, {NoopCallback, &state, CountingDestroyUserData}) != 0,
                "counting destroy structure registration failed");

        bool threw = false;
        try
        {
            (void)dispatcher.UnregisterCallbacksForOwner(&owner);
        }
        catch (const std::runtime_error&)
        {
            threw = true;
        }

        Require(threw, "owner cleanup hid throwing structure DestroyUserData");
        Require(state.Calls == 2, "owner cleanup did not attempt all structure DestroyUserData callbacks");
        Require(dispatcher.SubscriptionCount() == 0, "owner cleanup failure left structure callbacks registered");
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
            throw std::runtime_error("expected one-shot structure destroy failure");
        }
    }

    void CountRetryDestroyUserData(void* userData)
    {
        auto* state = static_cast<RetryDestroyFailureState*>(userData);
        ++state->CountingCalls;
    }

    void TestOwnerCleanupRetriesFailedDestroyUserData()
    {
        Obelisk::Core::StructureEventDispatcher dispatcher;
        int owner = 0;
        RetryDestroyFailureState state;

        Require(dispatcher.Register(&owner, {NoopCallback, &state, FailsOnceDestroyUserData}) != 0,
                "failing retry structure registration failed");
        Require(dispatcher.Register(&owner, {NoopCallback, &state, CountRetryDestroyUserData}) != 0,
                "counting retry structure registration failed");

        bool threw = false;
        try
        {
            (void)dispatcher.UnregisterCallbacksForOwner(&owner);
        }
        catch (const std::runtime_error&)
        {
            threw = true;
        }

        Require(threw, "owner cleanup hid one-shot structure DestroyUserData failure");
        Require(state.FailingCalls == 1, "first cleanup did not call failing structure destroy once");
        Require(state.CountingCalls == 1, "first cleanup did not attempt successful structure destroy");

        const size_t retryRemoved = dispatcher.UnregisterCallbacksForOwner(&owner);
        Require(retryRemoved == 1, "retry cleanup did not report pending failed structure destroy");
        Require(state.FailingCalls == 2, "retry cleanup did not retry failed structure DestroyUserData");
        Require(state.CountingCalls == 1, "retry cleanup repeated successful structure DestroyUserData");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 0, "completed structure cleanup was not idempotent");
        Require(dispatcher.SubscriptionCount() == 0, "retry cleanup left structure callbacks dispatchable");
    }

    void TestExceptionsDoNotStopDispatch()
    {
        Obelisk::Core::StructureEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        const std::vector<Obelisk::Core::StructureScalarValue> scalars = MakeScalars();
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
    TestDispatchRejectsFieldsOutsideEventContract();
    TestUnregisterIsIdempotent();
    TestUnregisterForOwnerRequiresMatchingOwner();
    TestRegistrationIdsSkipZeroAndLiveIdsAfterWrap();
    TestCallbackCanUnregisterItself();
    TestSelfUnregisterDefersUserDataDestroyUntilCallbackReturns();
    TestReentrantUnregisterSkipsRemovedSnapshotCallback();
    TestReusedRegistrationIdDoesNotReactivateStaleSnapshot();
    TestOwnerCleanupWaitsForInFlightDispatch();
    TestCrossFamilyCallbackSuppressesDeferredCleanupWait();
    TestOwnerCleanupWaitsForDeferredDestroyAfterInFlightDispatch();
    TestDeferredOwnerCleanupRetainsEveryFailedDestroy();
    TestOwnerCleanup();
    TestOwnerCleanupPropagatesDestroyUserDataFailure();
    TestOwnerCleanupRetriesFailedDestroyUserData();
    TestExceptionsDoNotStopDispatch();

    std::cout << "StructureEventDispatcherTests passed\n";
    return 0;
}
