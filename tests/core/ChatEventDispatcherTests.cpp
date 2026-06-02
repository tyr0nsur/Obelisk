#define OBELISK_CHAT_EVENT_DISPATCHER_ENABLE_TEST_HOOKS

#include "core/ChatEventDispatcher.h"
#include "core/GameplayCallbackScope.h"

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <memory>
#include <mutex>
#include <new>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>

namespace
{
    std::atomic<bool> g_FailNextAllocation{false};

    void FailNextAllocation()
    {
        g_FailNextAllocation.store(true, std::memory_order_release);
    }
}

void* operator new(std::size_t size)
{
    if (g_FailNextAllocation.exchange(false, std::memory_order_acq_rel))
        throw std::bad_alloc();

    if (void* pointer = std::malloc(size == 0 ? 1 : size))
        return pointer;

    throw std::bad_alloc();
}

void* operator new[](std::size_t size)
{
    if (g_FailNextAllocation.exchange(false, std::memory_order_acq_rel))
        throw std::bad_alloc();

    if (void* pointer = std::malloc(size == 0 ? 1 : size))
        return pointer;

    throw std::bad_alloc();
}

void operator delete(void* pointer) noexcept
{
    std::free(pointer);
}

void operator delete(void* pointer, std::size_t) noexcept
{
    std::free(pointer);
}

void operator delete[](void* pointer) noexcept
{
    std::free(pointer);
}

void operator delete[](void* pointer, std::size_t) noexcept
{
    std::free(pointer);
}

namespace
{
    struct Capture
    {
        int calls = 0;
        std::string message;
        std::string senderName;
        std::string senderPlatformId;
        Obelisk::Core::ChatSendMode sendMode = Obelisk::Core::ChatSendMode::Global;
        int32_t senderNameIndex = -1;
        const char* messagePointer = nullptr;
    };

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    void CaptureCallback(const Obelisk::Core::ChatMessageView& message, void* userData)
    {
        auto* capture = static_cast<Capture*>(userData);
        ++capture->calls;
        capture->message = std::string(message.Message);
        capture->senderName = std::string(message.SenderName);
        capture->senderPlatformId = std::string(message.SenderPlatformId);
        capture->sendMode = message.SendMode;
        capture->senderNameIndex = message.SenderNameIndex;
        capture->messagePointer = message.Message.data();
    }

    void ThrowingCallback(const Obelisk::Core::ChatMessageView&, void*)
    {
        throw std::runtime_error("expected test exception");
    }

    void ThrowingUnknownCallback(const Obelisk::Core::ChatMessageView&, void*)
    {
        throw 7;
    }

    void NoopCallback(const Obelisk::Core::ChatMessageView&, void*)
    {
    }

    struct DestroyFailureState
    {
        int calls = 0;
    };

    void ThrowingDestroyUserData(void* userData)
    {
        auto* state = static_cast<DestroyFailureState*>(userData);
        ++state->calls;
        throw std::runtime_error("expected destroy failure");
    }

    void CountingDestroyUserData(void* userData)
    {
        auto* state = static_cast<DestroyFailureState*>(userData);
        ++state->calls;
    }

    Obelisk::Core::ChatMessageView MakeMessage(std::string_view text = "hello from copied chat")
    {
        return {
            .Message = text,
            .SenderName = "PlayerOne",
            .SenderPlatformId = "123456789",
            .SendMode = Obelisk::Core::ChatSendMode::Global,
            .SenderNameIndex = 42,
        };
    }

    void TestDispatchCopiesInputForCallbackDuration()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        const std::string source = "message that should be copied before callbacks";
        const char* sourcePointer = source.data();

        const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(id != 0, "registration id was not assigned");
        Require(dispatcher.Dispatch(MakeMessage(source)) == 1, "dispatch count was wrong");

        Require(capture.calls == 1, "callback did not run");
        Require(capture.message == source, "message text was not copied through callback");
        Require(capture.senderName == "PlayerOne", "sender name was not copied");
        Require(capture.senderPlatformId == "123456789", "sender platform id was not copied");
        Require(capture.sendMode == Obelisk::Core::ChatSendMode::Global, "send mode changed");
        Require(capture.senderNameIndex == 42, "sender name index changed");
        Require(capture.messagePointer != sourcePointer, "dispatcher passed borrowed input text");
    }

    void TestNoSubscriberDispatchReturnsBeforeCallbackSnapshot()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;

        Require(dispatcher.SubscriptionCount() == 0, "new chat dispatcher unexpectedly had subscribers");
        Require(dispatcher.Dispatch(MakeMessage("private text that should not be copied")) == 0,
                "no-subscriber chat dispatch returned callbacks");
        Require(dispatcher.SubscriptionCount() == 0, "no-subscriber chat dispatch changed registrations");
    }

    void TestRegisterRejectsInvalidInput()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;

        Require(dispatcher.Register(nullptr, {CaptureCallback, &capture}) == 0,
                "registration without owner was accepted");
        Require(dispatcher.Register(&owner, {nullptr, &capture}) == 0,
                "registration without callback was accepted");
        Require(dispatcher.SubscriptionCount() == 0, "invalid registrations were stored");
    }

    void TestRegisterHandlesAllocationFailureWithoutCountDrift()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;

        FailNextAllocation();
        Require(dispatcher.Register(&owner, {NoopCallback, nullptr}) == 0,
                "registration allocation failure did not return zero");
        Require(dispatcher.SubscriptionCount() == 0,
                "failed registration changed subscription count");

        const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(id != 0, "valid registration failed after allocation failure");
        Require(dispatcher.SubscriptionCount() == 1,
                "successful registration after failure did not update subscription count");
        Require(dispatcher.Dispatch(MakeMessage()) == 1,
                "callback registered after allocation failure did not dispatch");
        Require(capture.calls == 1, "registered callback after allocation failure did not run");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 1,
                "owner cleanup after allocation failure removed wrong count");
        Require(dispatcher.SubscriptionCount() == 0,
                "owner cleanup after allocation failure left subscription count non-zero");
    }

    void TestUnregisterIsIdempotent()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;

        const uint64_t id = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(id != 0, "registration id was not assigned");
        Require(dispatcher.Unregister(id), "first unregister failed");
        Require(!dispatcher.Unregister(id), "second unregister was not idempotent");
        Require(dispatcher.Dispatch(MakeMessage()) == 0, "unregistered callback ran");
    }

    void TestRegistrationIdsSkipZeroAndLiveIdsAfterWrap()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
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
        Obelisk::Core::ChatEventDispatcher* dispatcher = nullptr;
        uint64_t registrationId = 0;
        int calls = 0;
    };

    void SelfUnregisterCallback(const Obelisk::Core::ChatMessageView&, void* userData)
    {
        auto* capture = static_cast<SelfUnregisterCapture*>(userData);
        ++capture->calls;
        Require(capture->dispatcher != nullptr, "self-unregister callback had no dispatcher");
        Require(capture->dispatcher->Unregister(capture->registrationId),
                "self-unregister from callback failed");
    }

    void TestCallbackCanUnregisterItself()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        SelfUnregisterCapture capture{&dispatcher, 0, 0};

        capture.registrationId = dispatcher.Register(&owner, {SelfUnregisterCallback, &capture});
        Require(capture.registrationId != 0, "registration id was not assigned");
        Require(dispatcher.Dispatch(MakeMessage()) == 1, "self-unregister callback did not run");
        Require(capture.calls == 1, "self-unregister callback ran wrong number of times");
        Require(dispatcher.SubscriptionCount() == 0, "self-unregister callback remained registered");
        Require(dispatcher.Dispatch(MakeMessage()) == 0, "self-unregistered callback ran twice");
    }

    struct SelfUnregisterDestroyCapture
    {
        Obelisk::Core::ChatEventDispatcher* dispatcher = nullptr;
        uint64_t registrationId = 0;
        int calls = 0;
        int destroyed = 0;
    };

    void SelfUnregisterWithDestroyCallback(const Obelisk::Core::ChatMessageView&, void* userData)
    {
        auto* capture = static_cast<SelfUnregisterDestroyCapture*>(userData);
        ++capture->calls;
        Require(capture->destroyed == 0, "chat user data was destroyed before callback body");
        Require(capture->dispatcher != nullptr, "self-unregister destroy callback had no dispatcher");
        Require(capture->dispatcher->Unregister(capture->registrationId),
                "self-unregister with destroy from chat callback failed");
        Require(capture->destroyed == 0, "chat user data was destroyed before callback returned");
    }

    void CountSelfUnregisterDestroyed(void* userData)
    {
        auto* capture = static_cast<SelfUnregisterDestroyCapture*>(userData);
        ++capture->destroyed;
    }

    void TestSelfUnregisterDefersUserDataDestroyUntilCallbackReturns()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        SelfUnregisterDestroyCapture capture{&dispatcher, 0, 0, 0};

        capture.registrationId = dispatcher.Register(
            &owner,
            {SelfUnregisterWithDestroyCallback, &capture, CountSelfUnregisterDestroyed});
        Require(capture.registrationId != 0, "self-unregister destroy registration id was not assigned");
        Require(dispatcher.Dispatch(MakeMessage()) == 1,
                "self-unregister destroy chat callback did not run");
        Require(capture.calls == 1, "self-unregister destroy chat callback ran wrong number of times");
        Require(capture.destroyed == 1, "chat user data was not destroyed after callback returned");
        Require(dispatcher.SubscriptionCount() == 0,
                "self-unregister destroy chat callback remained registered");
    }

    struct UnregisterOtherCapture
    {
        Obelisk::Core::ChatEventDispatcher* dispatcher = nullptr;
        uint64_t targetRegistrationId = 0;
        int calls = 0;
    };

    void UnregisterOtherCallback(const Obelisk::Core::ChatMessageView&, void* userData)
    {
        auto* capture = static_cast<UnregisterOtherCapture*>(userData);
        ++capture->calls;
        Require(capture->dispatcher != nullptr, "unregister-other callback had no dispatcher");
        Require(capture->dispatcher->Unregister(capture->targetRegistrationId),
                "unregister-other callback failed to remove target");
    }

    struct RemovedSnapshotState
    {
        int calls = 0;
        int destroys = 0;
    };

    void RemovedSnapshotCallback(const Obelisk::Core::ChatMessageView&, void* userData)
    {
        auto* state = static_cast<RemovedSnapshotState*>(userData);
        ++state->calls;
    }

    void CountDestroy(void* userData)
    {
        auto* state = static_cast<RemovedSnapshotState*>(userData);
        ++state->destroys;
    }

    void TestReentrantUnregisterSkipsRemovedSnapshotCallback()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        RemovedSnapshotState removedState;
        UnregisterOtherCapture unregisterOther{&dispatcher, 0, 0};

        const uint64_t removerId = dispatcher.Register(&owner, {UnregisterOtherCallback, &unregisterOther});
        Require(removerId != 0, "remover registration failed");
        unregisterOther.targetRegistrationId =
            dispatcher.Register(&owner, {RemovedSnapshotCallback, &removedState, CountDestroy});
        Require(unregisterOther.targetRegistrationId != 0, "target registration failed");

        Require(dispatcher.Dispatch(MakeMessage()) == 1,
                "removed snapshot callback was dispatched or remover was skipped");
        Require(unregisterOther.calls == 1, "remover callback did not run");
        Require(removedState.calls == 0, "removed snapshot callback still ran");
        Require(removedState.destroys == 1, "removed callback user data was not destroyed after dispatch");
        Require(dispatcher.SubscriptionCount() == 1, "wrong subscriptions remained after reentrant unregister");
    }

    struct ReuseRegistrationDuringDispatchState
    {
        Obelisk::Core::ChatEventDispatcher* dispatcher = nullptr;
        int* owner = nullptr;
        uint64_t removedRegistrationId = 0;
        int firstCalls = 0;
        int removedCalls = 0;
        int replacementCalls = 0;
    };

    void ReuseFirstCallback(const Obelisk::Core::ChatMessageView&, void* userData)
    {
        auto* state = static_cast<ReuseRegistrationDuringDispatchState*>(userData);
        ++state->firstCalls;
        if (state->firstCalls != 1)
            return;

        Require(state->dispatcher->Unregister(state->removedRegistrationId),
                "chat stale-snapshot setup could not unregister callback");
        state->dispatcher->SetNextRegistrationIdForTesting(state->removedRegistrationId);
        const uint64_t replacementId = state->dispatcher->Register(state->owner, {
            [](const Obelisk::Core::ChatMessageView&, void* replacementUserData) {
                auto* replacementState =
                    static_cast<ReuseRegistrationDuringDispatchState*>(replacementUserData);
                ++replacementState->replacementCalls;
            },
            state,
        });
        Require(replacementId == state->removedRegistrationId,
                "chat stale-snapshot setup did not reuse removed id");
    }

    void ReuseRemovedCallback(const Obelisk::Core::ChatMessageView&, void* userData)
    {
        auto* state = static_cast<ReuseRegistrationDuringDispatchState*>(userData);
        ++state->removedCalls;
    }

    void TestReusedRegistrationIdDoesNotReactivateStaleSnapshot()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        ReuseRegistrationDuringDispatchState state{&dispatcher, &owner, 0, 0, 0, 0};

        Require(dispatcher.Register(&owner, {ReuseFirstCallback, &state}) != 0,
                "chat stale-snapshot first registration failed");
        state.removedRegistrationId = dispatcher.Register(&owner, {ReuseRemovedCallback, &state});
        Require(state.removedRegistrationId != 0, "chat stale-snapshot removed registration failed");

        Require(dispatcher.Dispatch(MakeMessage()) == 1,
                "chat stale snapshot reused id as active callback");
        Require(state.firstCalls == 1, "chat stale-snapshot first callback did not run");
        Require(state.removedCalls == 0, "chat stale-snapshot removed callback ran");
        Require(state.replacementCalls == 0, "chat replacement callback ran in stale snapshot");
        Require(dispatcher.Dispatch(MakeMessage()) == 2,
                "chat replacement callback was not active for later dispatch");
        Require(state.firstCalls == 2, "chat stale-snapshot first callback did not run later");
        Require(state.removedCalls == 0, "chat stale-snapshot removed callback ran later");
        Require(state.replacementCalls == 1, "chat replacement callback did not run later");
    }

    struct BlockingCallbackState
    {
        std::mutex mutex;
        std::condition_variable cv;
        bool entered = false;
        bool release = false;
    };

    void BlockingCallback(const Obelisk::Core::ChatMessageView&, void* userData)
    {
        auto* state = static_cast<BlockingCallbackState*>(userData);
        std::unique_lock<std::mutex> lock(state->mutex);
        state->entered = true;
        state->cv.notify_all();
        state->cv.wait(lock, [&state]() { return state->release; });
    }

    void TestOwnerCleanupWaitsForInFlightDispatch()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        BlockingCallbackState state;
        std::atomic<bool> cleanupFinished{false};
        size_t removed = 0;

        const uint64_t id = dispatcher.Register(&owner, {BlockingCallback, &state});
        Require(id != 0, "blocking callback registration failed");

        std::thread dispatchThread([&dispatcher]() {
            Require(dispatcher.Dispatch(MakeMessage()) == 1, "blocking callback did not dispatch");
        });

        {
            std::unique_lock<std::mutex> lock(state.mutex);
            Require(state.cv.wait_for(lock, std::chrono::seconds(2), [&state]() { return state.entered; }),
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
            std::lock_guard<std::mutex> lock(state.mutex);
            state.release = true;
        }
        state.cv.notify_all();

        dispatchThread.join();
        cleanupThread.join();

        Require(cleanupFinished.load(std::memory_order_acquire), "owner cleanup did not complete");
        Require(removed == 1, "owner cleanup removed wrong callback count after dispatch");
        Require(dispatcher.SubscriptionCount() == 0, "owner callback survived cleanup after dispatch");
    }

    void TestCrossFamilyCallbackSuppressesDeferredCleanupWaitForFamily(
        Obelisk::Core::GameplayCallbackFamily family)
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        BlockingCallbackState state;
        std::atomic<bool> cleanupFinished{false};
        size_t removed = 0;

        const uint64_t id = dispatcher.Register(&owner, {BlockingCallback, &state});
        Require(id != 0, "cross-family blocking callback registration failed");

        std::thread dispatchThread([&dispatcher]() {
            Require(dispatcher.Dispatch(MakeMessage()) == 1, "cross-family blocking callback did not dispatch");
        });

        {
            std::unique_lock<std::mutex> lock(state.mutex);
            Require(state.cv.wait_for(lock, std::chrono::seconds(2), [&state]() { return state.entered; }),
                    "cross-family blocking callback did not enter");
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
            std::lock_guard<std::mutex> lock(state.mutex);
            state.release = true;
        }
        state.cv.notify_all();

        dispatchThread.join();
        cleanupThread.join();

        Require(finishedBeforeRelease,
                "cross-family gameplay callback waited for chat deferred cleanup");
        Require(removed == 1, "cross-family cleanup removed wrong callback count");
        Require(dispatcher.SubscriptionCount() == 0, "cross-family cleanup left callback registered");
    }

    void TestCrossFamilyCallbackSuppressesDeferredCleanupWait()
    {
        TestCrossFamilyCallbackSuppressesDeferredCleanupWaitForFamily(
            Obelisk::Core::GameplayCallbackFamily::Structure);
        TestCrossFamilyCallbackSuppressesDeferredCleanupWaitForFamily(
            Obelisk::Core::GameplayCallbackFamily::Inventory);
    }

    struct DeferredDestroyState
    {
        std::mutex mutex;
        std::condition_variable cv;
        bool callbackEntered = false;
        bool releaseCallback = false;
        bool destroyEntered = false;
        bool releaseDestroy = false;
    };

    void BlockingDestroyCallback(const Obelisk::Core::ChatMessageView&, void* userData)
    {
        auto* state = static_cast<DeferredDestroyState*>(userData);
        std::unique_lock<std::mutex> lock(state->mutex);
        state->callbackEntered = true;
        state->cv.notify_all();
        state->cv.wait(lock, [&state]() { return state->releaseCallback; });
    }

    void BlockingDestroy(void* userData)
    {
        auto* state = static_cast<DeferredDestroyState*>(userData);
        std::unique_lock<std::mutex> lock(state->mutex);
        state->destroyEntered = true;
        state->cv.notify_all();
        state->cv.wait(lock, [&state]() { return state->releaseDestroy; });
    }

    void TestOwnerCleanupWaitsForDeferredDestroyAfterInFlightDispatch()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        DeferredDestroyState state;
        std::atomic<bool> cleanupFinished{false};
        std::atomic<bool> secondCleanupFinished{false};
        size_t secondRemoved = 99;

        const uint64_t id = dispatcher.Register(&owner, {BlockingDestroyCallback, &state, BlockingDestroy});
        Require(id != 0, "deferred destroy callback registration failed");

        std::thread dispatchThread([&dispatcher]() {
            Require(dispatcher.Dispatch(MakeMessage()) == 1, "deferred destroy callback did not dispatch");
        });

        {
            std::unique_lock<std::mutex> lock(state.mutex);
            Require(state.cv.wait_for(lock, std::chrono::seconds(2), [&state]() { return state.callbackEntered; }),
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
            std::lock_guard<std::mutex> lock(state.mutex);
            state.releaseCallback = true;
        }
        state.cv.notify_all();

        {
            std::unique_lock<std::mutex> lock(state.mutex);
            Require(state.cv.wait_for(lock, std::chrono::seconds(2), [&state]() { return state.destroyEntered; }),
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
            std::lock_guard<std::mutex> lock(state.mutex);
            state.releaseDestroy = true;
        }
        state.cv.notify_all();

        dispatchThread.join();
        cleanupThread.join();
        secondCleanupThread.join();

        Require(cleanupFinished.load(std::memory_order_acquire), "owner cleanup did not complete after destroy");
        Require(secondCleanupFinished.load(std::memory_order_acquire),
                "no-op owner cleanup did not complete after destroy");
        Require(secondRemoved == 0, "no-op owner cleanup removed callbacks after deferred destroy");
        Require(dispatcher.SubscriptionCount() == 0, "deferred destroy callback survived cleanup");
    }

    void TestOwnerCleanup()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int ownerA = 0;
        int ownerB = 0;
        Capture captureA;
        Capture captureB;

        dispatcher.Register(&ownerA, {CaptureCallback, &captureA});
        dispatcher.Register(&ownerA, {CaptureCallback, &captureA});
        dispatcher.Register(&ownerB, {CaptureCallback, &captureB});

        Require(dispatcher.UnregisterCallbacksForOwner(&ownerA) == 2, "owner cleanup removed wrong count");
        Require(dispatcher.Dispatch(MakeMessage()) == 1, "wrong number of callbacks after owner cleanup");
        Require(captureA.calls == 0, "owner A callback survived cleanup");
        Require(captureB.calls == 1, "owner B callback did not run");
    }

    void TestOwnerCleanupPropagatesDestroyUserDataFailure()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        DestroyFailureState state;

        Require(dispatcher.Register(&owner, {NoopCallback, &state, ThrowingDestroyUserData}) != 0,
                "throwing destroy chat registration failed");
        Require(dispatcher.Register(&owner, {NoopCallback, &state, CountingDestroyUserData}) != 0,
                "counting destroy chat registration failed");

        bool threw = false;
        try
        {
            (void)dispatcher.UnregisterCallbacksForOwner(&owner);
        }
        catch (const std::runtime_error&)
        {
            threw = true;
        }

        Require(threw, "owner cleanup hid throwing chat DestroyUserData");
        Require(state.calls == 2, "owner cleanup did not attempt all chat DestroyUserData callbacks");
        Require(dispatcher.SubscriptionCount() == 0, "owner cleanup failure left chat callbacks registered");
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
            throw std::runtime_error("expected one-shot chat destroy failure");
        }
    }

    void CountRetryDestroyUserData(void* userData)
    {
        auto* state = static_cast<RetryDestroyFailureState*>(userData);
        ++state->CountingCalls;
    }

    void TestOwnerCleanupRetriesFailedDestroyUserData()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        RetryDestroyFailureState state;

        Require(dispatcher.Register(&owner, {NoopCallback, &state, FailsOnceDestroyUserData}) != 0,
                "failing retry chat registration failed");
        Require(dispatcher.Register(&owner, {NoopCallback, &state, CountRetryDestroyUserData}) != 0,
                "counting retry chat registration failed");

        bool threw = false;
        try
        {
            (void)dispatcher.UnregisterCallbacksForOwner(&owner);
        }
        catch (const std::runtime_error&)
        {
            threw = true;
        }

        Require(threw, "owner cleanup hid one-shot chat DestroyUserData failure");
        Require(state.FailingCalls == 1, "first cleanup did not call failing chat destroy once");
        Require(state.CountingCalls == 1, "first cleanup did not attempt successful chat destroy");

        const size_t retryRemoved = dispatcher.UnregisterCallbacksForOwner(&owner);
        Require(retryRemoved == 1, "retry cleanup did not report pending failed chat destroy");
        Require(state.FailingCalls == 2, "retry cleanup did not retry failed chat DestroyUserData");
        Require(state.CountingCalls == 1, "retry cleanup repeated successful chat DestroyUserData");
        Require(dispatcher.UnregisterCallbacksForOwner(&owner) == 0, "completed chat cleanup was not idempotent");
        Require(dispatcher.SubscriptionCount() == 0, "retry cleanup left chat callbacks dispatchable");
    }

    struct DestroyUnregisterOtherState
    {
        Obelisk::Core::ChatEventDispatcher* dispatcher = nullptr;
        uint64_t otherRegistrationId = 0;
        std::mutex mutex;
        std::condition_variable cv;
        bool finished = false;
        bool result = false;
        bool timedOut = false;
    };

    void DestroyAndUnregisterOther(void* userData)
    {
        auto* state = static_cast<DestroyUnregisterOtherState*>(userData);
        std::thread worker([state]() {
            const bool result = state->dispatcher && state->dispatcher->Unregister(state->otherRegistrationId);
            {
                std::lock_guard<std::mutex> lock(state->mutex);
                state->result = result;
                state->finished = true;
            }
            state->cv.notify_all();
        });

        {
            std::unique_lock<std::mutex> lock(state->mutex);
            state->timedOut = !state->cv.wait_for(lock, std::chrono::seconds(2), [state]() {
                return state->finished;
            });
        }

        if (state->timedOut)
        {
            worker.detach();
            return;
        }
        worker.join();
    }

    void TestDestroyUserDataCanUnregisterAnotherCallbackWithoutDeadlock()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        DestroyUnregisterOtherState state{&dispatcher, 0};

        state.otherRegistrationId = dispatcher.Register(&owner, {CaptureCallback, &capture});
        Require(state.otherRegistrationId != 0, "other chat callback registration failed");
        const uint64_t destroyRegistrationId =
            dispatcher.Register(&owner, {NoopCallback, &state, DestroyAndUnregisterOther});
        Require(destroyRegistrationId != 0, "destroy callback registration failed");

        Require(dispatcher.Unregister(destroyRegistrationId), "destroy callback unregister failed");
        Require(!state.timedOut, "DestroyUserData blocked while unregistering another chat callback");
        Require(state.result, "DestroyUserData failed to unregister the other chat callback");
        Require(dispatcher.SubscriptionCount() == 0, "chat callbacks survived reentrant destroy cleanup");
    }

    struct DeferredDestroyUnregisterOtherState
    {
        Obelisk::Core::ChatEventDispatcher* dispatcher = nullptr;
        uint64_t otherRegistrationId = 0;
        std::mutex mutex;
        std::condition_variable cv;
        bool callbackEntered = false;
        bool releaseCallback = false;
        bool destroyEntered = false;
        bool unregisterReturned = false;
        bool unregisterResult = false;
    };

    void BlockingDeferredDestroyCallback(const Obelisk::Core::ChatMessageView&, void* userData)
    {
        auto* state = static_cast<DeferredDestroyUnregisterOtherState*>(userData);
        std::unique_lock<std::mutex> lock(state->mutex);
        state->callbackEntered = true;
        state->cv.notify_all();
        state->cv.wait(lock, [&state]() { return state->releaseCallback; });
    }

    void DeferredDestroyAndUnregisterOther(void* userData)
    {
        auto* state = static_cast<DeferredDestroyUnregisterOtherState*>(userData);
        {
            std::lock_guard<std::mutex> lock(state->mutex);
            state->destroyEntered = true;
        }
        state->cv.notify_all();

        const bool result = state->dispatcher && state->dispatcher->Unregister(state->otherRegistrationId);
        {
            std::lock_guard<std::mutex> lock(state->mutex);
            state->unregisterResult = result;
            state->unregisterReturned = true;
        }
        state->cv.notify_all();
    }

    void TestDeferredDestroyUserDataCanUnregisterAnotherCallbackWithoutDeadlock()
    {
        auto dispatcher = std::make_unique<Obelisk::Core::ChatEventDispatcher>();
        int owner = 0;
        Capture capture;
        DeferredDestroyUnregisterOtherState state{dispatcher.get(), 0};
        std::atomic<size_t> dispatchCount{0};

        const uint64_t destroyRegistrationId = dispatcher->Register(
            &owner,
            {BlockingDeferredDestroyCallback, &state, DeferredDestroyAndUnregisterOther});
        Require(destroyRegistrationId != 0, "deferred destroy callback registration failed");
        state.otherRegistrationId = dispatcher->Register(&owner, {CaptureCallback, &capture});
        Require(state.otherRegistrationId != 0, "other deferred destroy callback registration failed");

        std::thread dispatchThread([&]() {
            dispatchCount.store(dispatcher->Dispatch(MakeMessage()), std::memory_order_release);
        });

        {
            std::unique_lock<std::mutex> lock(state.mutex);
            Require(state.cv.wait_for(lock, std::chrono::seconds(2), [&state]() {
                        return state.callbackEntered;
                    }),
                    "deferred destroy callback did not enter");
        }

        std::thread cleanupThread([&]() {
            Require(dispatcher->Unregister(destroyRegistrationId),
                    "deferred destroy callback unregister failed");
        });

        {
            std::lock_guard<std::mutex> lock(state.mutex);
            state.releaseCallback = true;
        }
        state.cv.notify_all();

        bool unregisterReturned = false;
        {
            std::unique_lock<std::mutex> lock(state.mutex);
            unregisterReturned = state.cv.wait_for(lock, std::chrono::seconds(2), [&state]() {
                return state.unregisterReturned;
            });
        }

        if (!unregisterReturned)
        {
            dispatchThread.detach();
            cleanupThread.detach();
            (void)dispatcher.release();
            Require(false, "deferred DestroyUserData deadlocked while unregistering another chat callback");
        }

        dispatchThread.join();
        cleanupThread.join();

        Require(state.destroyEntered, "deferred destroy cleanup did not run");
        Require(state.unregisterResult,
                "deferred DestroyUserData failed to unregister the other chat callback");
        Require(dispatchCount.load(std::memory_order_acquire) == 2,
                "deferred destroy dispatch count changed unexpectedly");
        Require(dispatcher->SubscriptionCount() == 0,
                "chat callbacks survived deferred reentrant destroy cleanup");
    }

    struct DestroyScopeState
    {
        bool insideAnyCallback = false;
        bool insideChatCallback = false;
    };

    void RecordDestroyGameplayScope(void* userData)
    {
        auto* state = static_cast<DestroyScopeState*>(userData);
        state->insideAnyCallback = Obelisk::Core::GameplayCallbackScope::IsInsideAnyCallback();
        state->insideChatCallback =
            Obelisk::Core::GameplayCallbackScope::IsInsideCallback(Obelisk::Core::GameplayCallbackFamily::Chat);
    }

    void TestDestroyUserDataRunsInsideGameplayCallbackScope()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        DestroyScopeState state;

        const uint64_t id = dispatcher.Register(&owner, {NoopCallback, &state, RecordDestroyGameplayScope});
        Require(id != 0, "destroy scope chat registration failed");
        Require(dispatcher.Unregister(id), "destroy scope chat unregister failed");

        Require(state.insideAnyCallback, "DestroyUserData did not enter any gameplay callback scope");
        Require(state.insideChatCallback, "DestroyUserData did not enter chat callback scope");
    }

    void TestRejectsUnknownSendMode()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        dispatcher.Register(&owner, {CaptureCallback, &capture});

        Obelisk::Core::ChatMessageView message = MakeMessage();
        message.SendMode = static_cast<Obelisk::Core::ChatSendMode>(4);
        Require(dispatcher.Dispatch(message) == 0, "unknown send mode was dispatched");
        Require(capture.calls == 0, "unknown send mode reached callback");
    }

    void TestExceptionsDoNotStopDispatch()
    {
        Obelisk::Core::ChatEventDispatcher dispatcher;
        int owner = 0;
        Capture capture;
        dispatcher.Register(&owner, {ThrowingCallback, nullptr});
        dispatcher.Register(&owner, {ThrowingUnknownCallback, nullptr});
        dispatcher.Register(&owner, {CaptureCallback, &capture});

        Require(dispatcher.Dispatch(MakeMessage()) == 1, "successful dispatch count ignored exception");
        Require(capture.calls == 1, "callback after exception did not run");
    }
}

int main()
{
    TestDispatchCopiesInputForCallbackDuration();
    TestNoSubscriberDispatchReturnsBeforeCallbackSnapshot();
    TestRegisterRejectsInvalidInput();
    TestRegisterHandlesAllocationFailureWithoutCountDrift();
    TestUnregisterIsIdempotent();
    TestRegistrationIdsSkipZeroAndLiveIdsAfterWrap();
    TestCallbackCanUnregisterItself();
    TestSelfUnregisterDefersUserDataDestroyUntilCallbackReturns();
    TestReentrantUnregisterSkipsRemovedSnapshotCallback();
    TestReusedRegistrationIdDoesNotReactivateStaleSnapshot();
    TestOwnerCleanupWaitsForInFlightDispatch();
    TestCrossFamilyCallbackSuppressesDeferredCleanupWait();
    TestOwnerCleanupWaitsForDeferredDestroyAfterInFlightDispatch();
    TestOwnerCleanup();
    TestOwnerCleanupPropagatesDestroyUserDataFailure();
    TestOwnerCleanupRetriesFailedDestroyUserData();
    TestDestroyUserDataCanUnregisterAnotherCallbackWithoutDeadlock();
    TestDeferredDestroyUserDataCanUnregisterAnotherCallbackWithoutDeadlock();
    TestDestroyUserDataRunsInsideGameplayCallbackScope();
    TestRejectsUnknownSendMode();
    TestExceptionsDoNotStopDispatch();

    std::cout << "ChatEventDispatcherTests passed\n";
    return 0;
}
