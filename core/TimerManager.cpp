#include "TimerManager.h"

#include "runtime/Logger.h"

#include <algorithm>
#include <chrono>
#include <condition_variable>
#include <exception>
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
                    if (!timer->Cancelled && (next == state.Timers.end() || timer->NextFire < next->second->NextFire))
                        next = it;
                    ++it;
                }

                if (next == state.Timers.end())
                    continue;

                const auto now = Clock::now();
                if (now < next->second->NextFire)
                {
                    state.Cv.wait_until(lock, next->second->NextFire);
                    continue;
                }

                auto timer = next->second;
                if (timer->Cancelled || !timer->Callback)
                {
                    EraseCancelledTimerIfIdleLocked(state, timer);
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
    }

    TimerManager& TimerManager::Get()
    {
        static auto* manager = new TimerManager();
        return *manager;
    }

    uint64_t TimerManager::Register(void* owner,
                                    uint64_t delayMs,
                                    uint64_t intervalMs,
                                    bool repeating,
                                    TimerCallback callback,
                                    void* userData)
    {
        if (!owner || !callback || (repeating && intervalMs == 0))
            return 0;

        TimerState& state = State();
        std::lock_guard<std::mutex> lock(state.Mutex);
        EnsureWorkerStartedLocked(state);
        const uint64_t id = AllocateTimerIdLocked(state);
        state.Timers[id] = std::make_shared<TimerEntry>(TimerEntry{
            .Id = id,
            .Owner = owner,
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

    size_t TimerManager::UnregisterCallbacksForOwner(void* owner)
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
        state.Cv.wait(lock, [&state, owner]() {
            return std::none_of(state.Timers.begin(), state.Timers.end(), [owner](const auto& item) {
                return item.second->Owner == owner && item.second->InFlight != 0;
            });
        });
        return removed;
    }
}
