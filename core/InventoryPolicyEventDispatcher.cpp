#include "InventoryPolicyEventDispatcher.h"
#include "runtime/Logger.h"

#include <algorithm>
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

        std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
        std::vector<InventoryPolicyEventSubscription> removed;
        size_t before = 0;
        size_t after = 0;
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
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
        }
        QueueOrDestroyRemovedSubscriptions(removed);
        return after != before;
    }

    bool InventoryPolicyEventDispatcher::UnregisterCallbackForOwner(void* owner, uint64_t registrationId)
    {
        if (!owner || registrationId == 0)
            return false;

        std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
        std::vector<InventoryPolicyEventSubscription> removed;
        size_t before = 0;
        size_t after = 0;
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
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
        }
        QueueOrDestroyRemovedSubscriptions(removed);
        return after != before;
    }

    size_t InventoryPolicyEventDispatcher::UnregisterCallbacksForOwner(void* owner)
    {
        if (!owner)
            return 0;

        std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
        std::vector<InventoryPolicyEventSubscription> removed;
        size_t before = 0;
        size_t after = 0;
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
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
        }
        QueueOrDestroyRemovedSubscriptions(removed);
        return before - after;
    }

    void InventoryPolicyEventDispatcher::QueueOrDestroyRemovedSubscriptions(
        std::vector<InventoryPolicyEventSubscription>& removed)
    {
        if (removed.empty())
            return;

        if (m_DispatchDepth > 0)
        {
            m_PendingDestroy.insert(m_PendingDestroy.end(), removed.begin(), removed.end());
            removed.clear();
            return;
        }

        for (const InventoryPolicyEventSubscription& subscription : removed)
            DestroySubscriptionUserData(subscription);
    }

    void InventoryPolicyEventDispatcher::FinishDispatch()
    {
        if (m_DispatchDepth == 0)
            return;

        --m_DispatchDepth;
        if (m_DispatchDepth != 0)
            return;

        std::vector<InventoryPolicyEventSubscription> pending;
        pending.swap(m_PendingDestroy);
        for (const InventoryPolicyEventSubscription& subscription : pending)
            DestroySubscriptionUserData(subscription);
    }

    void InventoryPolicyEventDispatcher::SetNextRegistrationIdForTesting(uint64_t nextRegistrationId)
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        m_NextRegistrationId = nextRegistrationId == 0 ? 1 : nextRegistrationId;
    }

    size_t InventoryPolicyEventDispatcher::Dispatch(const InventoryPolicyEventView& event)
    {
        if (!IsValidEvent(event))
            return 0;

        std::vector<InventoryPolicyScalarValue> scalarCopies(event.Scalars.begin(), event.Scalars.end());
        InventoryPolicyEventView copiedEvent{
            .Kind = event.Kind,
            .Scalars = scalarCopies,
        };

        std::vector<DispatchRegistration> callbacks;
        std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
        ++m_DispatchDepth;
        size_t dispatched = 0;
        try
        {
            {
                std::lock_guard<std::mutex> lock(m_Mutex);
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
        catch (...)
        {
            FinishDispatch();
            throw;
        }

        FinishDispatch();
        return dispatched;
    }

    size_t InventoryPolicyEventDispatcher::SubscriptionCount() const
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        return m_Registrations.size();
    }
}
