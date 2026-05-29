#include "StructureEventDispatcher.h"
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
            StructureEventSubscription Subscription;
        };

        bool IsKnownEventKind(StructureEventKind kind)
        {
            return static_cast<uint32_t>(kind) <=
                static_cast<uint32_t>(StructureEventKind::CanSeat);
        }

        bool IsKnownScalarField(StructureScalarField field)
        {
            return static_cast<uint32_t>(field) <=
                static_cast<uint32_t>(StructureScalarField::ReturnValue);
        }

        bool IsKnownScalarType(StructureScalarType type)
        {
            return static_cast<uint32_t>(type) <=
                static_cast<uint32_t>(StructureScalarType::Int32);
        }

        bool IsValidEvent(const StructureEventView& event)
        {
            if (!IsKnownEventKind(event.Kind))
                return false;

            for (const StructureScalarValue& scalar : event.Scalars)
            {
                if (!IsKnownScalarField(scalar.Field) || !IsKnownScalarType(scalar.Type))
                    return false;
            }

            return true;
        }

        void DestroySubscriptionUserData(const StructureEventSubscription& subscription)
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
                    OBELISK_ERROR("Structure event subscription cleanup threw: {}", e.what());
            }
            catch (...)
            {
                if (Obelisk::Logger::IsInitialized())
                    OBELISK_ERROR("Structure event subscription cleanup threw an unknown exception.");
            }
        }
    }

    StructureEventDispatcher& StructureEventDispatcher::Get()
    {
        static StructureEventDispatcher dispatcher;
        return dispatcher;
    }

    uint64_t StructureEventDispatcher::Register(void* owner, const StructureEventSubscription& subscription)
    {
        if (!owner || !subscription.Callback)
            return 0;

        std::lock_guard<std::mutex> lock(m_Mutex);
        const uint64_t id = AllocateRegistrationId();
        m_Registrations.push_back({id, owner, subscription});
        return id;
    }

    uint64_t StructureEventDispatcher::AllocateRegistrationId()
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

    bool StructureEventDispatcher::HasRegistrationId(uint64_t registrationId) const
    {
        return std::any_of(m_Registrations.begin(),
                           m_Registrations.end(),
                           [registrationId](const Registration& item) {
                               return item.Id == registrationId;
                           });
    }

    bool StructureEventDispatcher::IsRegistrationActive(uint64_t registrationId) const
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        return HasRegistrationId(registrationId);
    }

    bool StructureEventDispatcher::Unregister(uint64_t registrationId)
    {
        if (registrationId == 0)
            return false;

        std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
        std::vector<StructureEventSubscription> removed;
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
        for (const StructureEventSubscription& subscription : removed)
            DestroySubscriptionUserData(subscription);
        return after != before;
    }

    bool StructureEventDispatcher::UnregisterCallbackForOwner(void* owner, uint64_t registrationId)
    {
        if (!owner || registrationId == 0)
            return false;

        std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
        std::vector<StructureEventSubscription> removed;
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
        for (const StructureEventSubscription& subscription : removed)
            DestroySubscriptionUserData(subscription);
        return after != before;
    }

    size_t StructureEventDispatcher::UnregisterCallbacksForOwner(void* owner)
    {
        if (!owner)
            return 0;

        std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
        std::vector<StructureEventSubscription> removed;
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
        for (const StructureEventSubscription& subscription : removed)
            DestroySubscriptionUserData(subscription);
        return before - after;
    }

    void StructureEventDispatcher::SetNextRegistrationIdForTesting(uint64_t nextRegistrationId)
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        m_NextRegistrationId = nextRegistrationId == 0 ? 1 : nextRegistrationId;
    }

    size_t StructureEventDispatcher::Dispatch(const StructureEventView& event)
    {
        if (!IsValidEvent(event))
            return 0;

        std::vector<StructureScalarValue> scalarCopies(event.Scalars.begin(), event.Scalars.end());
        StructureEventView copiedEvent{
            .Kind = event.Kind,
            .FunctionNameIndex = event.FunctionNameIndex,
            .OuterNameIndex = event.OuterNameIndex,
            .Scalars = scalarCopies,
        };

        std::vector<DispatchRegistration> callbacks;
        std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
            callbacks.reserve(m_Registrations.size());
            for (const Registration& item : m_Registrations)
                callbacks.push_back({item.Id, item.Subscription});
        }

        size_t dispatched = 0;
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
                    OBELISK_ERROR("Structure event callback threw: {}", e.what());
            }
            catch (...)
            {
                if (Obelisk::Logger::IsInitialized())
                    OBELISK_ERROR("Structure event callback threw an unknown exception.");
            }
        }

        return dispatched;
    }

    size_t StructureEventDispatcher::SubscriptionCount() const
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        return m_Registrations.size();
    }
}
