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
    enum class ItemReturnEventKind : uint32_t
    {
        AllowEquipItem = 0,
        CanRepair = 1,
        UseItemOntoItem = 2,
    };

    enum class ItemReturnScalarField : uint32_t
    {
        ReturnValue = 0,
    };

    struct ItemReturnScalarValue
    {
        ItemReturnScalarField Field = ItemReturnScalarField::ReturnValue;
        bool BoolValue = false;
    };

    struct ItemReturnEventView
    {
        ItemReturnEventKind Kind = ItemReturnEventKind::AllowEquipItem;
        std::span<const ItemReturnScalarValue> Scalars;
    };

    using ItemReturnEventCallback = void (*)(const ItemReturnEventView& event, void* userData);

    struct ItemReturnEventSubscription
    {
        ItemReturnEventCallback Callback = nullptr;
        void* UserData = nullptr;
        void (*DestroyUserData)(void*) = nullptr;
    };

    class ItemReturnEventDispatcher
    {
    public:
        static ItemReturnEventDispatcher& Get();

        uint64_t Register(void* owner, const ItemReturnEventSubscription& subscription);
        bool Unregister(uint64_t registrationId);
        bool UnregisterCallbackForOwner(void* owner, uint64_t registrationId);
        size_t UnregisterCallbacksForOwner(void* owner);
#ifdef OBELISK_ITEM_RETURN_EVENT_DISPATCHER_ENABLE_TEST_HOOKS
        void SetNextRegistrationIdForTesting(uint64_t nextRegistrationId);
#endif

        size_t Dispatch(const ItemReturnEventView& event);
        size_t SubscriptionCount() const;

    private:
        struct Registration
        {
            uint64_t Id = 0;
            uint64_t Generation = 0;
            void* Owner = nullptr;
            ItemReturnEventSubscription Subscription;
        };

        struct PendingDestroy
        {
            ItemReturnEventSubscription Subscription;
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
            std::vector<ItemReturnEventSubscription>& removed,
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
