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
    enum class InventoryPolicyEventKind : uint32_t
    {
        AllowRemoteAddToInventory = 0,
        CanUse = 1,
    };

    enum class InventoryPolicyScalarField : uint32_t
    {
        BRequestedByPlayer = 0,
        BIgnoreCooldown = 1,
        ReturnValue = 2,
    };

    struct InventoryPolicyScalarValue
    {
        InventoryPolicyScalarField Field = InventoryPolicyScalarField::ReturnValue;
        bool BoolValue = false;
    };

    struct InventoryPolicyEventView
    {
        InventoryPolicyEventKind Kind = InventoryPolicyEventKind::CanUse;
        std::span<const InventoryPolicyScalarValue> Scalars;
    };

    using InventoryPolicyEventCallback = void (*)(const InventoryPolicyEventView& event, void* userData);

    struct InventoryPolicyEventSubscription
    {
        InventoryPolicyEventCallback Callback = nullptr;
        void* UserData = nullptr;
        void (*DestroyUserData)(void*) = nullptr;
    };

    class InventoryPolicyEventDispatcher
    {
    public:
        static InventoryPolicyEventDispatcher& Get();

        uint64_t Register(void* owner, const InventoryPolicyEventSubscription& subscription);
        bool Unregister(uint64_t registrationId);
        bool UnregisterCallbackForOwner(void* owner, uint64_t registrationId);
        size_t UnregisterCallbacksForOwner(void* owner);
#ifdef OBELISK_INVENTORY_POLICY_EVENT_DISPATCHER_ENABLE_TEST_HOOKS
        void SetNextRegistrationIdForTesting(uint64_t nextRegistrationId);
#endif

        size_t Dispatch(const InventoryPolicyEventView& event);
        size_t SubscriptionCount() const;

    private:
        struct Registration
        {
            uint64_t Id = 0;
            uint64_t Generation = 0;
            void* Owner = nullptr;
            InventoryPolicyEventSubscription Subscription;
        };

        struct PendingDestroy
        {
            InventoryPolicyEventSubscription Subscription;
            uint64_t CleanupBatchId = 0;
        };

        struct DeferredDestroyFailure
        {
            uint64_t CleanupBatchId = 0;
            InventoryPolicyEventSubscription Subscription;
            std::exception_ptr Failure;
        };

        struct FailedOwnerDestroy
        {
            void* Owner = nullptr;
            InventoryPolicyEventSubscription Subscription;
        };

        uint64_t AllocateRegistrationId();
        bool HasRegistrationId(uint64_t registrationId) const;
        bool IsRegistrationActive(uint64_t registrationId, uint64_t generation) const;
        bool QueueOrDestroyRemovedSubscriptions(
            std::vector<InventoryPolicyEventSubscription>& removed,
            std::unique_lock<std::mutex>& lock,
            uint64_t cleanupBatchId = 0);
        bool IsDispatchCleanupComplete() const;
        std::vector<InventoryPolicyEventSubscription> TakeFailedOwnerDestroySubscriptions(void* owner);
        void RetainFailedOwnerDestroySubscriptions(
            void* owner,
            const std::vector<InventoryPolicyEventSubscription>& subscriptions);
        std::vector<InventoryPolicyEventSubscription> TakeDeferredDestroyFailures(
            uint64_t cleanupBatchId,
            std::exception_ptr& firstFailure);
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
        std::vector<FailedOwnerDestroy> m_FailedOwnerDestroy;
        size_t m_PendingDestroyInProgress = 0;
        uint64_t m_NextCleanupBatchId = 1;
    };
}
