#pragma once

#include "OwnerExecutionGate.h"

#include <cstddef>
#include <cstdint>

namespace Obelisk::Core
{
    using TimerCallback = void (*)(uint64_t timerId, void* userData);

    class TimerManager
    {
    public:
        static TimerManager& Get();
        static bool IsSupportedDuration(uint64_t durationMs);

        uint64_t Register(void* owner,
                          uint64_t delayMs,
                          uint64_t intervalMs,
                          bool repeating,
                          TimerCallback callback,
                          void* userData);
        bool Unregister(void* owner, uint64_t timerId);
        size_t UnregisterCallbacksForOwner(
            void* owner, OwnerExecutionGate::Clock::time_point deadline = OwnerExecutionGate::Clock::time_point::max());
        void NotifyOwnerResumed(void* owner) noexcept;
#ifdef OBELISK_TIMER_MANAGER_ENABLE_TEST_HOOKS
        void SetNextTimerIdForTesting(uint64_t nextTimerId);
#endif

    private:
        TimerManager() = default;
    };
}
