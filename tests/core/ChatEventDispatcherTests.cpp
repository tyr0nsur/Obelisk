#include "core/ChatEventDispatcher.h"
#include "core/GameplayCallbackScope.h"

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <iostream>
#include <limits>
#include <mutex>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>

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

    void NoopCallback(const Obelisk::Core::ChatMessageView&, void*)
    {
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
        dispatcher.Register(&owner, {CaptureCallback, &capture});

        Require(dispatcher.Dispatch(MakeMessage()) == 1, "successful dispatch count ignored exception");
        Require(capture.calls == 1, "callback after exception did not run");
    }
}

int main()
{
    TestDispatchCopiesInputForCallbackDuration();
    TestRegisterRejectsInvalidInput();
    TestUnregisterIsIdempotent();
    TestRegistrationIdsSkipZeroAndLiveIdsAfterWrap();
    TestCallbackCanUnregisterItself();
    TestReentrantUnregisterSkipsRemovedSnapshotCallback();
    TestOwnerCleanupWaitsForInFlightDispatch();
    TestCrossFamilyCallbackSuppressesDeferredCleanupWait();
    TestOwnerCleanupWaitsForDeferredDestroyAfterInFlightDispatch();
    TestOwnerCleanup();
    TestDestroyUserDataCanUnregisterAnotherCallbackWithoutDeadlock();
    TestRejectsUnknownSendMode();
    TestExceptionsDoNotStopDispatch();

    std::cout << "ChatEventDispatcherTests passed\n";
    return 0;
}
