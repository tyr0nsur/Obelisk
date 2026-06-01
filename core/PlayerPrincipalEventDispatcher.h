#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <condition_variable>
#include <exception>
#include <mutex>
#include <span>
#include <vector>

namespace Obelisk::Core
{
    enum class PlayerPrincipalEventKind : uint32_t
    {
        SessionStart = 0,
        SessionStartRejected = 1,
        SessionEnd = 2,
    };

    enum class PlayerPrincipalAction : uint32_t
    {
        None = 0,
        CandidateCreated = 1,
        CandidateInvalidated = 2,
    };

    enum class PlayerPrincipalBoolField : uint32_t
    {
        BIsFromLogin = 0,
        ReturnValue = 1,
    };

    struct PlayerPrincipalBoolValue
    {
        PlayerPrincipalBoolField Field = PlayerPrincipalBoolField::BIsFromLogin;
        bool Value = false;
    };

    struct PlayerPrincipalEventView
    {
        PlayerPrincipalEventKind Kind = PlayerPrincipalEventKind::SessionStart;
        PlayerPrincipalAction Action = PlayerPrincipalAction::None;
        uint64_t EventSequence = 0;
        uint64_t ServerProcessEpoch = 0;
        std::span<const PlayerPrincipalBoolValue> Bools;
    };

    using PlayerPrincipalEventCallback = void (*)(const PlayerPrincipalEventView& event, void* userData);

    struct PlayerPrincipalEventSubscription
    {
        PlayerPrincipalEventCallback Callback = nullptr;
        void* UserData = nullptr;
        void (*DestroyUserData)(void*) = nullptr;
    };

    // Internal-only copied event dispatcher. There is no public ABI registration path for this family yet.
    class PlayerPrincipalEventDispatcher
    {
    public:
        static PlayerPrincipalEventDispatcher& Get();

        uint64_t Register(void* owner, const PlayerPrincipalEventSubscription& subscription);
        bool Unregister(uint64_t registrationId);
        bool UnregisterCallbackForOwner(void* owner, uint64_t registrationId);
        size_t UnregisterCallbacksForOwner(void* owner);
#ifdef OBELISK_PLAYER_PRINCIPAL_EVENT_DISPATCHER_ENABLE_TEST_HOOKS
        void SetNextRegistrationIdForTesting(uint64_t nextRegistrationId);
#endif

        size_t Dispatch(const PlayerPrincipalEventView& event);
        size_t SubscriptionCount() const;

    private:
        struct Registration
        {
            uint64_t Id = 0;
            uint64_t Generation = 0;
            void* Owner = nullptr;
            PlayerPrincipalEventSubscription Subscription;
        };

        struct PendingDestroy
        {
            PlayerPrincipalEventSubscription Subscription;
            uint64_t CleanupBatchId = 0;
        };

        struct DeferredDestroyFailure
        {
            uint64_t CleanupBatchId = 0;
            std::exception_ptr Failure;
        };

        uint64_t AllocateRegistrationId();
        bool HasRegistrationId(uint64_t registrationId) const;
        bool IsRegistrationActive(uint64_t registrationId, uint64_t generation) const;
        bool QueueOrDestroyRemovedSubscriptions(
            std::vector<PlayerPrincipalEventSubscription>& removed,
            std::unique_lock<std::mutex>& lock,
            uint64_t cleanupBatchId = 0);
        bool IsDispatchCleanupComplete() const;
        std::exception_ptr TakeDeferredDestroyFailure(uint64_t cleanupBatchId);
        void FinishDispatch();

        mutable std::mutex m_Mutex;
        std::condition_variable m_DispatchCv;
        size_t m_DispatchDepth = 0;
        uint64_t m_NextRegistrationId = 1;
        uint64_t m_NextGeneration = 1;
        std::vector<Registration> m_Registrations;
        std::atomic<size_t> m_SubscriptionCount{0};
        std::vector<PendingDestroy> m_PendingDestroy;
        std::vector<DeferredDestroyFailure> m_DeferredDestroyFailures;
        size_t m_PendingDestroyInProgress = 0;
        uint64_t m_NextCleanupBatchId = 1;
    };
}
