#pragma once

#include "obelisk/ObeliskPlayerLifecycleApi.h"
#include "OwnerExecutionGate.h"

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <memory>
#include <mutex>
#include <string_view>
#include <vector>

namespace Obelisk::Core
{
    // Private adapter input, borrowed only while Dispatch copies the strings.
    // The adapter establishes the event kind and observation-quality flags.
    struct PlayerLifecycleSnapshot
    {
        uint32_t Kind = 0;
        uint64_t Flags = 0;
        uint64_t Sequence = 0;
        uint64_t ProcessEpoch = 0;
        std::string_view PlayerName;
        std::string_view PlatformId;
    };

    class PlayerLifecycleDispatcher
    {
    public:
        static PlayerLifecycleDispatcher& Get();
        void SetAvailable(bool available) noexcept;
        bool IsAvailable() const noexcept;

        uint64_t Register(void* owner, ObeliskPlayerLifecycleCallback callback, void* userData);
        // Outside this dispatcher's callbacks, waits for this registration to
        // drain. Inside a callback, cancels future delivery without waiting.
        bool Unregister(void* owner, uint64_t registrationId);
        // Cancels and drains this owner's callbacks. Throws when invoked from
        // an active callback belonging to the owner, so unload retains its code.
        // On deadline failure, in-flight records remain until callback return.
        size_t UnregisterCallbacksForOwner(
            void* owner, std::chrono::steady_clock::time_point deadline = std::chrono::steady_clock::time_point::max());
        size_t SubscriptionCount() const;

        // Copies text once before plugin entry; unknown flags, missing required
        // quality, bad event kind/phase, or zero context reject the observation.
        // Invalid optional text loses its availability flag and becomes NULL/0.
        // Observation/callback failures never escape into the original UE call.
        size_t Dispatch(const PlayerLifecycleSnapshot& snapshot) noexcept;

    private:
        struct Registration
        {
            uint64_t Id = 0;
            void* Owner = nullptr;
            OwnerExecutionGate::Binding Execution;
            ObeliskPlayerLifecycleCallback Callback = nullptr;
            void* UserData = nullptr;
            bool Active = true;
            size_t InFlight = 0;
        };

        void FinishInvocation(const std::shared_ptr<Registration>& registration) noexcept;
        void PruneInactiveLocked();
        bool HasOwnerInvocationsLocked(void* owner) const;

        std::atomic_bool m_Available{false};
        mutable std::mutex m_Mutex;
        std::condition_variable m_Quiescence;
        uint64_t m_NextRegistrationId = 1;
        std::vector<std::shared_ptr<Registration>> m_Registrations;
    };
}
