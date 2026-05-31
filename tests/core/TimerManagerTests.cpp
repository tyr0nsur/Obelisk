#define OBELISK_TIMER_MANAGER_ENABLE_TEST_HOOKS
#include "core/TimerManager.h"

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <limits>
#include <mutex>
#include <stdexcept>
#include <thread>

namespace
{
    using Obelisk::Core::TimerManager;

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    struct CounterState
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        int Count = 0;
        uint64_t LastTimerId = 0;
    };

    void CountCallback(uint64_t timerId, void* userData)
    {
        auto* state = static_cast<CounterState*>(userData);
        {
            std::lock_guard<std::mutex> lock(state->Mutex);
            ++state->Count;
            state->LastTimerId = timerId;
        }
        state->Cv.notify_all();
    }

    void ThrowingCallback(uint64_t, void*)
    {
        throw std::runtime_error("timer callback failure");
    }

    void ThrowingUnknownCallback(uint64_t, void*)
    {
        throw 7;
    }

    struct SelfUnregisterState
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        void* Owner = nullptr;
        int Count = 0;
        bool UnregisterResult = false;
    };

    void SelfUnregisterCallback(uint64_t timerId, void* userData)
    {
        auto* state = static_cast<SelfUnregisterState*>(userData);
        const bool result = TimerManager::Get().Unregister(state->Owner, timerId);
        {
            std::lock_guard<std::mutex> lock(state->Mutex);
            ++state->Count;
            state->UnregisterResult = result;
        }
        state->Cv.notify_all();
    }

    struct OwnerCleanupFromCallbackState
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        void* Owner = nullptr;
        int Count = 0;
        size_t Removed = 0;
    };

    void OwnerCleanupFromCallback(uint64_t, void* userData)
    {
        auto* state = static_cast<OwnerCleanupFromCallbackState*>(userData);
        const size_t removed = TimerManager::Get().UnregisterCallbacksForOwner(state->Owner);
        {
            std::lock_guard<std::mutex> lock(state->Mutex);
            ++state->Count;
            state->Removed = removed;
        }
        state->Cv.notify_all();
    }

    struct BlockingState
    {
        std::mutex Mutex;
        std::condition_variable Cv;
        bool Entered = false;
        bool Release = false;
        bool Returned = false;
    };

    void BlockingCallback(uint64_t, void* userData)
    {
        auto* state = static_cast<BlockingState*>(userData);
        std::unique_lock<std::mutex> lock(state->Mutex);
        state->Entered = true;
        state->Cv.notify_all();
        state->Cv.wait(lock, [&]() { return state->Release; });
        state->Returned = true;
        state->Cv.notify_all();
    }

    void TestRegisterRejectsInvalidInputs()
    {
        int owner = 0;
        CounterState state;
        Require(TimerManager::Get().Register(nullptr, 1, 0, false, CountCallback, &state) == 0,
                "timer registration accepted null owner");
        Require(TimerManager::Get().Register(&owner, 1, 0, false, nullptr, &state) == 0,
                "timer registration accepted null callback");
        Require(TimerManager::Get().Register(&owner, 1, 0, true, CountCallback, &state) == 0,
                "timer registration accepted repeating timer with zero interval");
        Require(!TimerManager::Get().Unregister(&owner, 0), "timer unregister accepted zero handle");
    }

    void TestTimerIdsSkipZeroAndLiveIdsAfterWrap()
    {
        int owner = 0;
        CounterState state;
        TimerManager& timers = TimerManager::Get();

        timers.SetNextTimerIdForTesting(1);
        const uint64_t firstId = timers.Register(&owner, 60000, 0, false, CountCallback, &state);
        Require(firstId == 1, "first timer id was not one");

        timers.SetNextTimerIdForTesting(std::numeric_limits<uint64_t>::max());
        const uint64_t lastId = timers.Register(&owner, 60000, 0, false, CountCallback, &state);
        const uint64_t wrappedId = timers.Register(&owner, 60000, 0, false, CountCallback, &state);

        Require(lastId == std::numeric_limits<uint64_t>::max(), "last timer id was not preserved");
        Require(wrappedId == 2, "wrapped timer id did not skip zero or live ids");
        Require(wrappedId != firstId, "wrapped timer id reused a live timer id");
        Require(!timers.Unregister(&owner, 0), "zero timer id unregistered a timer after wrap");
        Require(timers.Unregister(&owner, firstId), "first timer id could not unregister");
        Require(timers.Unregister(&owner, lastId), "last timer id could not unregister");
        Require(timers.Unregister(&owner, wrappedId), "wrapped timer id could not unregister");
    }

    void TestOneShotTimerFiresOnce()
    {
        int owner = 0;
        CounterState state;
        const uint64_t timerId = TimerManager::Get().Register(&owner, 5, 0, false, CountCallback, &state);
        Require(timerId != 0, "one-shot timer registration failed");

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&]() { return state.Count == 1; }),
                    "one-shot timer did not fire");
            Require(state.LastTimerId == timerId, "one-shot timer callback received wrong id");
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(25));
        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            Require(state.Count == 1, "one-shot timer fired more than once");
        }
        Require(!TimerManager::Get().Unregister(&owner, timerId), "completed one-shot timer unregistered as active");
    }

    void TestRepeatingTimerStopsAfterUnregister()
    {
        int owner = 0;
        CounterState state;
        const uint64_t timerId = TimerManager::Get().Register(&owner, 5, 5, true, CountCallback, &state);
        Require(timerId != 0, "repeating timer registration failed");

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&]() { return state.Count >= 2; }),
                    "repeating timer did not repeat");
        }
        Require(TimerManager::Get().Unregister(&owner, timerId), "repeating timer unregister failed");
        const int countAfterUnregister = [&]() {
            std::lock_guard<std::mutex> lock(state.Mutex);
            return state.Count;
        }();
        std::this_thread::sleep_for(std::chrono::milliseconds(25));
        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            Require(state.Count == countAfterUnregister, "repeating timer fired after unregister");
        }
    }

    void TestWrongOwnerCannotUnregister()
    {
        int owner = 0;
        int otherOwner = 0;
        CounterState state;
        const uint64_t timerId = TimerManager::Get().Register(&owner, 50, 0, false, CountCallback, &state);
        Require(timerId != 0, "timer registration failed");
        Require(!TimerManager::Get().Unregister(&otherOwner, timerId), "wrong owner unregistered timer");
        Require(TimerManager::Get().Unregister(&owner, timerId), "owner could not unregister timer");
        Require(!TimerManager::Get().Unregister(&owner, timerId), "second unregister reported success");
    }

    void TestSelfUnregisterDoesNotDeadlock()
    {
        int owner = 0;
        SelfUnregisterState state;
        state.Owner = &owner;
        const uint64_t timerId = TimerManager::Get().Register(&owner, 5, 5, true, SelfUnregisterCallback, &state);
        Require(timerId != 0, "self-unregister timer registration failed");

        std::unique_lock<std::mutex> lock(state.Mutex);
        Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&]() { return state.Count == 1; }),
                "self-unregister callback did not run");
        Require(state.UnregisterResult, "self-unregister returned false");
    }

    void TestOwnerCleanupFromOwnCallbackDoesNotDeadlock()
    {
        int owner = 0;
        OwnerCleanupFromCallbackState state;
        state.Owner = &owner;
        const uint64_t timerId =
            TimerManager::Get().Register(&owner, 5, 5, true, OwnerCleanupFromCallback, &state);
        Require(timerId != 0, "owner-cleanup timer registration failed");

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&]() { return state.Count == 1; }),
                    "owner-cleanup callback did not run");
            Require(state.Removed == 1, "owner cleanup from callback removed wrong timer count");
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(25));
        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            Require(state.Count == 1, "owner-cleanup timer fired again after callback cleanup");
        }
        Require(!TimerManager::Get().Unregister(&owner, timerId),
                "owner-cleanup timer remained active after callback cleanup");
    }

    void TestCallbackExceptionDoesNotStopWorker()
    {
        int throwingOwner = 0;
        int owner = 0;
        CounterState state;
        Require(TimerManager::Get().Register(&throwingOwner, 5, 0, false, ThrowingCallback, nullptr) != 0,
                "throwing timer registration failed");
        Require(TimerManager::Get().Register(&owner, 10, 0, false, CountCallback, &state) != 0,
                "post-throw timer registration failed");

        std::unique_lock<std::mutex> lock(state.Mutex);
        Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&]() { return state.Count == 1; }),
                "timer worker stopped after callback exception");
    }

    void TestUnknownCallbackExceptionDoesNotStopWorker()
    {
        int throwingOwner = 0;
        int owner = 0;
        CounterState state;
        Require(TimerManager::Get().Register(&throwingOwner, 5, 0, false, ThrowingUnknownCallback, nullptr) != 0,
                "unknown-throwing timer registration failed");
        Require(TimerManager::Get().Register(&owner, 10, 0, false, CountCallback, &state) != 0,
                "post-unknown-throw timer registration failed");

        std::unique_lock<std::mutex> lock(state.Mutex);
        Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&]() { return state.Count == 1; }),
                "timer worker stopped after unknown callback exception");
    }

    void TestOwnerCleanupWaitsForInFlightCallback()
    {
        int owner = 0;
        BlockingState state;
        const uint64_t timerId = TimerManager::Get().Register(&owner, 5, 0, false, BlockingCallback, &state);
        Require(timerId != 0, "blocking timer registration failed");

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&]() { return state.Entered; }),
                    "blocking timer did not enter callback");
        }

        std::atomic<bool> cleanupReturned{false};
        std::thread cleanupThread([&]() {
            const size_t removed = TimerManager::Get().UnregisterCallbacksForOwner(&owner);
            Require(removed == 1, "owner cleanup removed wrong timer count");
            cleanupReturned.store(true, std::memory_order_release);
        });

        std::this_thread::sleep_for(std::chrono::milliseconds(25));
        Require(!cleanupReturned.load(std::memory_order_acquire),
                "owner cleanup returned before in-flight callback finished");

        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            state.Release = true;
        }
        state.Cv.notify_all();
        cleanupThread.join();
        Require(cleanupReturned.load(std::memory_order_acquire),
                "owner cleanup did not return after callback finished");
        Require(!TimerManager::Get().Unregister(&owner, timerId), "owner cleanup left timer active");
    }

    void TestOwnerCleanupWaitsForExplicitlyUnregisteredInFlightCallback()
    {
        int owner = 0;
        BlockingState state;
        const uint64_t timerId = TimerManager::Get().Register(&owner, 5, 0, false, BlockingCallback, &state);
        Require(timerId != 0, "explicit unregister blocking timer registration failed");

        {
            std::unique_lock<std::mutex> lock(state.Mutex);
            Require(state.Cv.wait_for(lock, std::chrono::seconds(2), [&]() { return state.Entered; }),
                    "explicit unregister blocking timer did not enter callback");
        }

        Require(TimerManager::Get().Unregister(&owner, timerId),
                "explicit unregister failed for in-flight timer");

        std::atomic<bool> cleanupReturned{false};
        std::thread cleanupThread([&]() {
            const size_t removed = TimerManager::Get().UnregisterCallbacksForOwner(&owner);
            Require(removed == 0, "owner cleanup counted already-unregistered timer as newly removed");
            cleanupReturned.store(true, std::memory_order_release);
        });

        std::this_thread::sleep_for(std::chrono::milliseconds(25));
        Require(!cleanupReturned.load(std::memory_order_acquire),
                "owner cleanup returned before explicitly-unregistered in-flight callback finished");

        {
            std::lock_guard<std::mutex> lock(state.Mutex);
            state.Release = true;
        }
        state.Cv.notify_all();
        cleanupThread.join();
        Require(cleanupReturned.load(std::memory_order_acquire),
                "owner cleanup did not return after explicitly-unregistered callback finished");
    }
}

int main()
{
    TestRegisterRejectsInvalidInputs();
    TestTimerIdsSkipZeroAndLiveIdsAfterWrap();
    TestOneShotTimerFiresOnce();
    TestRepeatingTimerStopsAfterUnregister();
    TestWrongOwnerCannotUnregister();
    TestSelfUnregisterDoesNotDeadlock();
    TestOwnerCleanupFromOwnCallbackDoesNotDeadlock();
    TestCallbackExceptionDoesNotStopWorker();
    TestUnknownCallbackExceptionDoesNotStopWorker();
    TestOwnerCleanupWaitsForInFlightCallback();
    TestOwnerCleanupWaitsForExplicitlyUnregisteredInFlightCallback();
    return 0;
}
