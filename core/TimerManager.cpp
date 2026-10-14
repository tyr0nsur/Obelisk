#if !defined(obelisk_EXPORTS)
#define OBELISK_TIMER_MANAGER_ENABLE_TEST_HOOKS
#endif

#include "TimerManager.h"
#include "GameplayCallbackScope.h"
#include "OwnerExecutionGate.h"

#include "runtime/Logger.h"

#include <algorithm>
#include <chrono>
#include <condition_variable>
#include <exception>
#include <stdexcept>
#include <memory>
#include <mutex>
#include <thread>
#include <unordered_map>
#include <vector>

namespace Obelisk::Core
{
    namespace
    {
        using Clock = std::chrono::steady_clock;

        struct TimerEntry
        {
            uint64_t Id = 0;
            void* Owner = nullptr;
            OwnerExecutionGate::Binding ExecutionBinding;
            uint64_t IntervalMs = 0;
            TimerCallback Callback = nullptr;
            void* UserData = nullptr;
            Clock::time_point NextFire{};
            bool Cancelled = false;
            size_t InFlight = 0;
        };

        struct TimerState
        {
            std::mutex Mutex;
            std::condition_variable Cv;
            std::unordered_map<uint64_t, std::shared_ptr<TimerEntry>> Timers;
            uint64_t NextId = 1;
            bool WorkerStarted = false;
        };

        TimerState& State()
        {
            static auto* state = new TimerState();
            return *state;
        }

        thread_local uint64_t t_CurrentTimerId = 0;
        thread_local void* t_CurrentTimerOwner = nullptr;

        void SafeLogTimerCallbackException(const char* message, const char* detail = nullptr) noexcept
        {
            try
            {
                if (!Logger::IsInitialized())
                    return;
                if (detail)
                    Logger::Get()->error("{}: {}", message ? message : "", detail);
                else
                    Logger::Get()->error("{}", message ? message : "");
            }
            catch (...)
            {
            }
        }

        uint64_t AllocateTimerIdLocked(TimerState& state)
        {
            for (;;)
            {
                const uint64_t id = state.NextId++;
                if (state.NextId == 0)
                    state.NextId = 1;
                if (id != 0 && state.Timers.find(id) == state.Timers.end())
                    return id;
            }
        }

        void EraseCancelledTimerIfIdleLocked(TimerState& state, const std::shared_ptr<TimerEntry>& timer)
        {
            if (timer && timer->Cancelled && timer->InFlight == 0)
                state.Timers.erase(timer->Id);
        }

        void WorkerLoop()
        {
            TimerState& state = State();
            std::unique_lock<std::mutex> lock(state.Mutex);
            for (;;)
            {
                if (state.Timers.empty())
                {
                    state.Cv.wait(lock, [&state]() { return !state.Timers.empty(); });
                    continue;
                }

                auto next = state.Timers.end();
                for (auto it = state.Timers.begin(); it != state.Timers.end();)
                {
                    const auto& timer = it->second;
                    if (timer->Cancelled && timer->InFlight == 0)
                    {
                        it = state.Timers.erase(it);
                        continue;
                    }
                    // Closed/initializing owners retain their deadlines and handles.
                    // Skip them rather than letting a due paused timer starve others.
                    const auto gateState = OwnerExecutionGate::Get().Inspect(timer->ExecutionBinding);
                    const bool runnable = !timer->ExecutionBinding ||
                        (gateState.phase == OwnerExecutionGate::Phase::Running && !gateState.faulted);
                    if (!timer->Cancelled && runnable &&
                        (next == state.Timers.end() || timer->NextFire < next->second->NextFire))
                        next = it;
                    ++it;
                }

                if (next == state.Timers.end())
                {
                    // Activation may occur without a timer-specific notification.
                    // Bounded sleeping also preserves paused one-shot timers.
                    state.Cv.wait_for(lock, std::chrono::milliseconds(50));
                    continue;
                }

                const auto now = Clock::now();
                if (now < next->second->NextFire)
                {
                    state.Cv.wait_until(lock, std::min(next->second->NextFire,
                        now + std::chrono::milliseconds(50)));
                    continue;
                }

                auto timer = next->second;
                if (timer->Cancelled || !timer->Callback)
                {
                    EraseCancelledTimerIfIdleLocked(state, timer);
                    continue;
                }

                // Acquire before consuming the occurrence. A concurrent pause
                // leaves this timer due, including a one-shot registration.
                // The lease spans callback catches and timer completion bookkeeping.
                auto executionLease = OwnerExecutionGate::EnterCallback(timer->ExecutionBinding);
                if (!executionLease)
                {
                    state.Cv.wait_for(lock, std::chrono::milliseconds(50));
                    continue;
                }

                ++timer->InFlight;
                const uint64_t timerId = timer->Id;
                void* owner = timer->Owner;
                TimerCallback callback = timer->Callback;
                void* userData = timer->UserData;
                lock.unlock();

                t_CurrentTimerId = timerId;
                t_CurrentTimerOwner = owner;
                try
                {
                    GameplayCallbackScope callbackScope(GameplayCallbackFamily::Timer,
                                                         GameplayCallbackScope::TrackingMode::CurrentOnly);
                    callback(timerId, userData);
                }
                catch (const std::exception& e)
                {
                    SafeLogTimerCallbackException("Timer callback threw an exception", e.what());
                }
                catch (...)
                {
                    SafeLogTimerCallbackException("Timer callback threw an unknown exception");
                }
                t_CurrentTimerOwner = nullptr;
                t_CurrentTimerId = 0;

                lock.lock();
                --timer->InFlight;
                if (!timer->Cancelled && timer->IntervalMs > 0)
                {
                    timer->NextFire = Clock::now() + std::chrono::milliseconds(timer->IntervalMs);
                }
                else
                {
                    timer->Cancelled = true;
                }
                EraseCancelledTimerIfIdleLocked(state, timer);
                state.Cv.notify_all();
            }
        }

        void EnsureWorkerStartedLocked(TimerState& state)
        {
            if (state.WorkerStarted)
                return;

            std::thread(WorkerLoop).detach();
            state.WorkerStarted = true;
        }

        uint64_t MaxSupportedTimerDurationMs()
        {
            const auto safeDuration = Clock::duration::max() / 4;
            const auto safeMilliseconds = std::chrono::duration_cast<std::chrono::milliseconds>(safeDuration).count();
            return safeMilliseconds > 0 ? static_cast<uint64_t>(safeMilliseconds) : 0;
        }
    }

    TimerManager& TimerManager::Get()
    {
        static auto* manager = new TimerManager();
        return *manager;
    }

    bool TimerManager::IsSupportedDuration(uint64_t durationMs)
    {
        return durationMs != 0 && durationMs <= MaxSupportedTimerDurationMs();
    }

    uint64_t TimerManager::Register(void* owner,
                                    uint64_t delayMs,
                                    uint64_t intervalMs,
                                    bool repeating,
                                    TimerCallback callback,
                                    void* userData)
    {
        if (!owner || !callback || !IsSupportedDuration(delayMs) ||
            (repeating && !IsSupportedDuration(intervalMs)) ||
            (!repeating && intervalMs != 0))
            return 0;

        const auto binding = OwnerExecutionGate::Get().Capture(owner);
        auto registrationLease = OwnerExecutionGate::EnterRegistration(binding);
        if (!registrationLease)
            return 0;

        TimerState& state = State();
        std::lock_guard<std::mutex> lock(state.Mutex);
        EnsureWorkerStartedLocked(state);
        const uint64_t id = AllocateTimerIdLocked(state);
        state.Timers[id] = std::make_shared<TimerEntry>(TimerEntry{
            .Id = id,
            .Owner = owner,
            .ExecutionBinding = binding,
            .IntervalMs = repeating ? intervalMs : 0,
            .Callback = callback,
            .UserData = userData,
            .NextFire = Clock::now() + std::chrono::milliseconds(delayMs),
            .Cancelled = false,
            .InFlight = 0,
        });
        state.Cv.notify_all();
        return id;
    }

    void TimerManager::NotifyOwnerResumed(void* owner) noexcept
    {
        // Wake only: preserved timers fire at most once before normal rescheduling.
        // A plugin with no timers need not have initialized the lazy timer state.
        (void)owner;
        try
        {
            State().Cv.notify_all();
        }
        catch (...)
        {
        }
    }

    bool TimerManager::Unregister(void* owner, uint64_t timerId)
    {
        if (!owner || timerId == 0)
            return false;

        TimerState& state = State();
        std::unique_lock<std::mutex> lock(state.Mutex);
        const auto it = state.Timers.find(timerId);
        if (it == state.Timers.end() || it->second->Owner != owner)
            return false;

        auto timer = it->second;
        const bool wasActive = !timer->Cancelled;
        timer->Cancelled = true;
        if (timer->InFlight == 0)
            state.Timers.erase(timerId);
        state.Cv.notify_all();
        return wasActive;
    }

    size_t TimerManager::UnregisterCallbacksForOwner(
        void* owner, OwnerExecutionGate::Clock::time_point deadline)
    {
        if (!owner)
            return 0;

        TimerState& state = State();
        std::unique_lock<std::mutex> lock(state.Mutex);
        size_t removed = 0;
        for (auto it = state.Timers.begin(); it != state.Timers.end();)
        {
            auto timer = it->second;
            if (timer->Owner != owner)
            {
                ++it;
                continue;
            }

            if (!timer->Cancelled)
                ++removed;
            timer->Cancelled = true;
            if (timer->InFlight == 0)
                it = state.Timers.erase(it);
            else
                ++it;
        }

        if (t_CurrentTimerOwner == owner)
        {
            state.Cv.notify_all();
            return removed;
        }

        state.Cv.notify_all();
        if (!state.Cv.wait_until(lock, deadline, [&state, owner]() {
            return std::none_of(state.Timers.begin(), state.Timers.end(), [owner](const auto& item) {
                return item.second->Owner == owner && item.second->InFlight != 0;
            });
        }))
            throw std::runtime_error("Timer owner cleanup timed out; keep plugin mapped");
        return removed;
    }

#ifdef OBELISK_TIMER_MANAGER_ENABLE_TEST_HOOKS
    void TimerManager::SetNextTimerIdForTesting(uint64_t nextTimerId)
    {
        TimerState& state = State();
        std::lock_guard<std::mutex> lock(state.Mutex);
        state.NextId = nextTimerId == 0 ? 1 : nextTimerId;
    }
#endif
}
