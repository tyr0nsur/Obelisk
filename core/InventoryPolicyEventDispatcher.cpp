#if !defined(obelisk_EXPORTS)
#define OBELISK_INVENTORY_POLICY_EVENT_DISPATCHER_ENABLE_TEST_HOOKS
#endif

#include "InventoryPolicyEventDispatcher.h"
#include "GameplayCallbackScope.h"
#include "runtime/Logger.h"

#include <algorithm>
#include <array>
#include <exception>

namespace Obelisk::Core
{
    namespace
    {
        struct DispatchRegistration
        {
            uint64_t Id = 0;
            InventoryPolicyEventSubscription Subscription;
        };

        thread_local size_t g_DestroyUserDataDepth = 0;

        struct DestroyUserDataScope
        {
            DestroyUserDataScope()
            {
                ++g_DestroyUserDataDepth;
            }

            ~DestroyUserDataScope()
            {
                --g_DestroyUserDataDepth;
            }
        };

        bool IsInsideDispatcherCleanup()
        {
            return g_DestroyUserDataDepth > 0;
        }

        bool IsKnownEventKind(InventoryPolicyEventKind kind)
        {
            return static_cast<uint32_t>(kind) <=
                static_cast<uint32_t>(InventoryPolicyEventKind::CanUse);
        }

        bool IsKnownScalarField(InventoryPolicyScalarField field)
        {
            return static_cast<uint32_t>(field) <=
                static_cast<uint32_t>(InventoryPolicyScalarField::ReturnValue);
        }

        bool IsValidEvent(const InventoryPolicyEventView& event)
        {
            if (!IsKnownEventKind(event.Kind))
                return false;

            const InventoryPolicyScalarField* expectedFields = nullptr;
            size_t expectedFieldCount = 0;
            constexpr InventoryPolicyScalarField allowRemoteAddFields[] = {
                InventoryPolicyScalarField::BRequestedByPlayer,
                InventoryPolicyScalarField::ReturnValue,
            };
            constexpr InventoryPolicyScalarField canUseFields[] = {
                InventoryPolicyScalarField::BIgnoreCooldown,
                InventoryPolicyScalarField::ReturnValue,
            };
            switch (event.Kind)
            {
            case InventoryPolicyEventKind::AllowRemoteAddToInventory:
                expectedFields = allowRemoteAddFields;
                expectedFieldCount = std::size(allowRemoteAddFields);
                break;
            case InventoryPolicyEventKind::CanUse:
                expectedFields = canUseFields;
                expectedFieldCount = std::size(canUseFields);
                break;
            }

            if (event.Scalars.size() != expectedFieldCount)
                return false;

            size_t index = 0;
            for (const InventoryPolicyScalarValue& scalar : event.Scalars)
            {
                if (!IsKnownScalarField(scalar.Field))
                    return false;
                if (!expectedFields || scalar.Field != expectedFields[index])
                    return false;
                ++index;
            }

            return true;
        }

        void DestroySubscriptionUserData(const InventoryPolicyEventSubscription& subscription)
        {
            if (!subscription.DestroyUserData)
                return;

            try
            {
                DestroyUserDataScope cleanupScope;
                GameplayCallbackScope callbackScope(GameplayCallbackFamily::Inventory);
                subscription.DestroyUserData(subscription.UserData);
            }
            catch (const std::exception& e)
            {
                if (Obelisk::Logger::IsInitialized())
                    OBELISK_ERROR("Inventory policy event subscription cleanup threw: {}", e.what());
            }
            catch (...)
            {
                if (Obelisk::Logger::IsInitialized())
                    OBELISK_ERROR("Inventory policy event subscription cleanup threw an unknown exception.");
            }
        }

        bool IsInsideAnyGameplayCallback()
        {
            return GameplayCallbackScope::IsInsideAnyCallback();
        }
    }

    InventoryPolicyEventDispatcher& InventoryPolicyEventDispatcher::Get()
    {
        static auto* dispatcher = new InventoryPolicyEventDispatcher();
        return *dispatcher;
    }

    uint64_t InventoryPolicyEventDispatcher::Register(
        void* owner,
        const InventoryPolicyEventSubscription& subscription)
    {
        if (!owner || !subscription.Callback)
            return 0;

        std::lock_guard<std::mutex> lock(m_Mutex);
        const uint64_t id = AllocateRegistrationId();
        m_Registrations.push_back({id, owner, subscription});
        m_SubscriptionCount.fetch_add(1, std::memory_order_release);
        return id;
    }

    uint64_t InventoryPolicyEventDispatcher::AllocateRegistrationId()
    {
        uint64_t id = 0;
        do
        {
            id = m_NextRegistrationId++;
            if (m_NextRegistrationId == 0)
                m_NextRegistrationId = 1;
        } while (id == 0 || HasRegistrationId(id));

        return id;
    }

    bool InventoryPolicyEventDispatcher::HasRegistrationId(uint64_t registrationId) const
    {
        return std::any_of(m_Registrations.begin(),
                           m_Registrations.end(),
                           [registrationId](const Registration& item) {
                               return item.Id == registrationId;
                           });
    }

    bool InventoryPolicyEventDispatcher::IsRegistrationActive(uint64_t registrationId) const
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        return HasRegistrationId(registrationId);
    }

    bool InventoryPolicyEventDispatcher::Unregister(uint64_t registrationId)
    {
        if (registrationId == 0)
            return false;

        std::vector<InventoryPolicyEventSubscription> removed;
        size_t before = 0;
        size_t after = 0;
        {
            std::unique_lock<std::mutex> lock(m_Mutex);
            before = m_Registrations.size();
            auto keepEnd = std::remove_if(m_Registrations.begin(),
                                          m_Registrations.end(),
                                          [registrationId, &removed](const Registration& item) {
                                              if (item.Id != registrationId)
                                                  return false;
                                              removed.push_back(item.Subscription);
                                              return true;
                                          });
            m_Registrations.erase(keepEnd, m_Registrations.end());
            after = m_Registrations.size();
            if (before > after)
                m_SubscriptionCount.fetch_sub(before - after, std::memory_order_release);
            if (QueueOrDestroyRemovedSubscriptions(removed, lock))
                m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
            else if (!IsInsideAnyGameplayCallback() &&
                     !IsInsideDispatcherCleanup() &&
                     !IsDispatchCleanupComplete())
                m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
        }
        for (const InventoryPolicyEventSubscription& subscription : removed)
            DestroySubscriptionUserData(subscription);
        return after != before;
    }

    bool InventoryPolicyEventDispatcher::UnregisterCallbackForOwner(void* owner, uint64_t registrationId)
    {
        if (!owner || registrationId == 0)
            return false;

        std::vector<InventoryPolicyEventSubscription> removed;
        size_t before = 0;
        size_t after = 0;
        {
            std::unique_lock<std::mutex> lock(m_Mutex);
            before = m_Registrations.size();
            auto keepEnd = std::remove_if(m_Registrations.begin(),
                                          m_Registrations.end(),
                                          [owner, registrationId, &removed](const Registration& item) {
                                              if (item.Owner != owner || item.Id != registrationId)
                                                  return false;
                                              removed.push_back(item.Subscription);
                                              return true;
                                          });
            m_Registrations.erase(keepEnd, m_Registrations.end());
            after = m_Registrations.size();
            if (before > after)
                m_SubscriptionCount.fetch_sub(before - after, std::memory_order_release);
            if (QueueOrDestroyRemovedSubscriptions(removed, lock))
                m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
            else if (!IsInsideAnyGameplayCallback() &&
                     !IsInsideDispatcherCleanup() &&
                     !IsDispatchCleanupComplete())
                m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
        }
        for (const InventoryPolicyEventSubscription& subscription : removed)
            DestroySubscriptionUserData(subscription);
        return after != before;
    }

    size_t InventoryPolicyEventDispatcher::UnregisterCallbacksForOwner(void* owner)
    {
        if (!owner)
            return 0;

        std::vector<InventoryPolicyEventSubscription> removed;
        size_t before = 0;
        size_t after = 0;
        {
            std::unique_lock<std::mutex> lock(m_Mutex);
            before = m_Registrations.size();
            auto keepEnd = std::remove_if(m_Registrations.begin(),
                                          m_Registrations.end(),
                                          [owner, &removed](const Registration& item) {
                                              if (item.Owner != owner)
                                                  return false;
                                              removed.push_back(item.Subscription);
                                              return true;
                                          });
            m_Registrations.erase(keepEnd, m_Registrations.end());
            after = m_Registrations.size();
            if (before > after)
                m_SubscriptionCount.fetch_sub(before - after, std::memory_order_release);
            if (QueueOrDestroyRemovedSubscriptions(removed, lock))
                m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
            else if (!IsInsideAnyGameplayCallback() &&
                     !IsInsideDispatcherCleanup() &&
                     !IsDispatchCleanupComplete())
                m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
        }
        for (const InventoryPolicyEventSubscription& subscription : removed)
            DestroySubscriptionUserData(subscription);
        return before - after;
    }

    bool InventoryPolicyEventDispatcher::QueueOrDestroyRemovedSubscriptions(
        std::vector<InventoryPolicyEventSubscription>& removed,
        std::unique_lock<std::mutex>&)
    {
        if (removed.empty())
            return false;

        if (m_DispatchDepth > 0)
        {
            m_PendingDestroy.insert(m_PendingDestroy.end(), removed.begin(), removed.end());
            removed.clear();
            return !IsInsideAnyGameplayCallback();
        }

        return false;
    }

    bool InventoryPolicyEventDispatcher::IsDispatchCleanupComplete() const
    {
        return m_DispatchDepth == 0 && m_PendingDestroy.empty() && m_PendingDestroyInProgress == 0;
    }

    void InventoryPolicyEventDispatcher::FinishDispatch()
    {
        std::vector<InventoryPolicyEventSubscription> pending;
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
            if (m_DispatchDepth == 0)
                return;

            --m_DispatchDepth;
            if (m_DispatchDepth != 0)
                return;

            pending.swap(m_PendingDestroy);
            m_PendingDestroyInProgress += pending.size();
        }

        for (const InventoryPolicyEventSubscription& subscription : pending)
            DestroySubscriptionUserData(subscription);
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
            m_PendingDestroyInProgress -= pending.size();
        }
        m_DispatchCv.notify_all();
    }

#ifdef OBELISK_INVENTORY_POLICY_EVENT_DISPATCHER_ENABLE_TEST_HOOKS
    void InventoryPolicyEventDispatcher::SetNextRegistrationIdForTesting(uint64_t nextRegistrationId)
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        m_NextRegistrationId = nextRegistrationId == 0 ? 1 : nextRegistrationId;
    }
#endif

    size_t InventoryPolicyEventDispatcher::Dispatch(const InventoryPolicyEventView& event)
    {
        if (!IsValidEvent(event))
            return 0;

        size_t dispatched = 0;
        try
        {
            if (event.Scalars.size() > 3)
                return 0;
            std::array<InventoryPolicyScalarValue, 3> scalarCopies{};
            std::copy(event.Scalars.begin(), event.Scalars.end(), scalarCopies.begin());
            InventoryPolicyEventView copiedEvent{
                .Kind = event.Kind,
                .Scalars = std::span<const InventoryPolicyScalarValue>(scalarCopies.data(), event.Scalars.size()),
            };

            std::vector<DispatchRegistration> callbacks;
            try
            {
                {
                    std::lock_guard<std::mutex> lock(m_Mutex);
                    ++m_DispatchDepth;
                    m_PendingDestroy.reserve(m_PendingDestroy.size() + m_Registrations.size());
                    callbacks.reserve(m_Registrations.size());
                    for (const Registration& item : m_Registrations)
                        callbacks.push_back({item.Id, item.Subscription});
                }

                for (const DispatchRegistration& item : callbacks)
                {
                    if (!IsRegistrationActive(item.Id))
                        continue;
                    if (!item.Subscription.Callback)
                        continue;

                    try
                    {
                        GameplayCallbackScope callbackScope(GameplayCallbackFamily::Inventory);
                        item.Subscription.Callback(copiedEvent, item.Subscription.UserData);
                        ++dispatched;
                    }
                    catch (const std::exception& e)
                    {
                        if (Obelisk::Logger::IsInitialized())
                            OBELISK_ERROR("Inventory policy event callback threw: {}", e.what());
                    }
                    catch (...)
                    {
                        if (Obelisk::Logger::IsInitialized())
                            OBELISK_ERROR("Inventory policy event callback threw an unknown exception.");
                    }
                }
            }
            catch (const std::exception& e)
            {
                FinishDispatch();
                if (Obelisk::Logger::IsInitialized())
                {
                    OBELISK_ERROR("Inventory policy event dispatch failed internally: {}", e.what());
                }
                return dispatched;
            }
            catch (...)
            {
                FinishDispatch();
                if (Obelisk::Logger::IsInitialized())
                    OBELISK_ERROR("Inventory policy event dispatch failed internally with an unknown exception.");
                return dispatched;
            }

            FinishDispatch();
            return dispatched;
        }
        catch (const std::exception& e)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Inventory policy event dispatch setup failed: {}", e.what());
            return 0;
        }
        catch (...)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Inventory policy event dispatch setup failed with an unknown exception.");
            return 0;
        }
    }

    size_t InventoryPolicyEventDispatcher::SubscriptionCount() const
    {
        return m_SubscriptionCount.load(std::memory_order_acquire);
    }
}
