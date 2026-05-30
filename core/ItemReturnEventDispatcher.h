#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <condition_variable>
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
        void SetNextRegistrationIdForTesting(uint64_t nextRegistrationId);

        size_t Dispatch(const ItemReturnEventView& event);
        size_t SubscriptionCount() const;

    private:
        struct Registration
        {
            uint64_t Id = 0;
            void* Owner = nullptr;
            ItemReturnEventSubscription Subscription;
        };

        uint64_t AllocateRegistrationId();
        bool HasRegistrationId(uint64_t registrationId) const;
        bool IsRegistrationActive(uint64_t registrationId) const;
        bool QueueOrDestroyRemovedSubscriptions(
            std::vector<ItemReturnEventSubscription>& removed,
            std::unique_lock<std::mutex>& lock);
        bool IsDispatchCleanupComplete() const;
        void FinishDispatch();

        mutable std::mutex m_Mutex;
        std::condition_variable m_DispatchCv;
        size_t m_DispatchDepth = 0;
        uint64_t m_NextRegistrationId = 1;
        std::vector<Registration> m_Registrations;
        std::atomic<size_t> m_SubscriptionCount{0};
        std::vector<ItemReturnEventSubscription> m_PendingDestroy;
        size_t m_PendingDestroyInProgress = 0;
    };
}
