#pragma once

#include "obelisk/ObeliskCommandApi.h"
#include "OwnerExecutionGate.h"

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <memory>
#include <mutex>
#include <string>
#include <string_view>
#include <vector>

namespace Obelisk::Core
{
    // Private adapter data, borrowed only while Dispatch copies it. Availability
    // flags describe observed data; they convey no authentication or authority.
    struct CommandPlayerSnapshot
    {
        uint64_t Flags = 0;
        std::string_view PlayerName;
        std::string_view PlatformId;
    };

    // Controller pointers and the backend stay private to the Linux adapter.
    class CommandDispatcher
    {
    public:
        using ReplyBackend = bool (*)(void* controller, std::string_view text, void* data) noexcept;

        static CommandDispatcher& Get();
        void SetAvailable(bool available) noexcept;
        bool IsAvailable() const noexcept;
        void SetPlayerSnapshotsAvailable(bool available) noexcept;
        bool IsPlayerSnapshotsAvailable() const noexcept;

        uint64_t Register(void* owner, std::string_view command, ObeliskCommandCallback callback, void* userData);
        uint64_t RegisterWithOptions(void* owner, std::string_view command, uint64_t matchFlags,
                                     ObeliskCommandCallback callback, void* userData);
        bool Unregister(void* owner, uint64_t registrationId);
        // A deadline failure cancels future delivery but retains in-flight
        // records. The caller must keep code/data mapped and retry after drain.
        size_t UnregisterCallbacksForOwner(
            void* owner, std::chrono::steady_clock::time_point deadline = std::chrono::steady_clock::time_point::max());
        size_t SubscriptionCount() const;

        size_t Dispatch(void* controller, std::string_view message, uint32_t sendMode,
                        ReplyBackend backend, void* backendData = nullptr,
                        const CommandPlayerSnapshot* player = nullptr);
        bool Reply(void* owner, uint64_t invocationToken, std::string_view reply) noexcept;
        bool GetPlayer(void* owner, uint64_t invocationToken, ObeliskCommandPlayer* out) noexcept;

    private:
        struct Registration
        {
            uint64_t Id = 0;
            void* Owner = nullptr;
            OwnerExecutionGate::Binding Execution;
            std::string Command;
            uint64_t MatchFlags = 0;
            ObeliskCommandCallback Callback = nullptr;
            void* UserData = nullptr;
            bool Active = true;
            size_t InFlight = 0;
        };

        void FinishInvocation(const std::shared_ptr<Registration>& registration) noexcept;
        void PruneInactiveLocked();
        bool HasOwnerInvocationsLocked(void* owner) const;

        std::atomic_bool m_Available{false};
        std::atomic_bool m_PlayerSnapshotsAvailable{false};
        mutable std::mutex m_Mutex;
        std::condition_variable m_Quiescence;
        uint64_t m_NextRegistrationId = 1;
        std::vector<std::shared_ptr<Registration>> m_Registrations;
    };
}
