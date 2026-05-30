#if !defined(obelisk_EXPORTS)
#define OBELISK_STRUCTURE_EVENT_DISPATCHER_ENABLE_TEST_HOOKS
#endif

#include "StructureEventDispatcher.h"
#include "GameplayCallbackScope.h"
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

            const StructureScalarField* expectedFields = nullptr;
            const StructureScalarType* expectedTypes = nullptr;
            size_t expectedFieldCount = 0;
            constexpr StructureScalarField returnOnlyFields[] = {
                StructureScalarField::ReturnValue,
            };
            constexpr StructureScalarType returnOnlyTypes[] = {
                StructureScalarType::Bool,
            };
            constexpr StructureScalarField setVariantFields[] = {
                StructureScalarField::VariantIndex,
                StructureScalarField::BForceSet,
                StructureScalarField::ReturnValue,
            };
            constexpr StructureScalarType setVariantTypes[] = {
                StructureScalarType::Int32,
                StructureScalarType::Bool,
                StructureScalarType::Bool,
            };
            constexpr StructureScalarField canSeatFields[] = {
                StructureScalarField::BForce,
                StructureScalarField::ReturnValue,
            };
            constexpr StructureScalarType canSeatTypes[] = {
                StructureScalarType::Bool,
                StructureScalarType::Bool,
            };
            switch (event.Kind)
            {
            case StructureEventKind::AllowStructureAccess:
            case StructureEventKind::IsAllowedToDemolish:
            case StructureEventKind::AllowToggleActivation:
            case StructureEventKind::VerifyPinCode:
                expectedFields = returnOnlyFields;
                expectedTypes = returnOnlyTypes;
                expectedFieldCount = std::size(returnOnlyFields);
                break;
            case StructureEventKind::SetVariant:
                expectedFields = setVariantFields;
                expectedTypes = setVariantTypes;
                expectedFieldCount = std::size(setVariantFields);
                break;
            case StructureEventKind::CanSeat:
                expectedFields = canSeatFields;
                expectedTypes = canSeatTypes;
                expectedFieldCount = std::size(canSeatFields);
                break;
            }

            if (event.Scalars.size() != expectedFieldCount)
                return false;

            size_t index = 0;
            for (const StructureScalarValue& scalar : event.Scalars)
            {
                if (!IsKnownScalarField(scalar.Field) || !IsKnownScalarType(scalar.Type))
                    return false;
                if (!expectedFields || !expectedTypes ||
                    scalar.Field != expectedFields[index] ||
                    scalar.Type != expectedTypes[index])
                {
                    return false;
                }
                ++index;
            }

            return true;
        }

        void DestroySubscriptionUserData(const StructureEventSubscription& subscription)
        {
            if (!subscription.DestroyUserData)
                return;

            try
            {
                DestroyUserDataScope cleanupScope;
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

        bool IsInsideAnyGameplayCallback()
        {
            return GameplayCallbackScope::IsInsideAnyCallback();
        }
    }

    StructureEventDispatcher& StructureEventDispatcher::Get()
    {
        static auto* dispatcher = new StructureEventDispatcher();
        return *dispatcher;
    }

    uint64_t StructureEventDispatcher::Register(void* owner, const StructureEventSubscription& subscription)
    {
        if (!owner || !subscription.Callback)
            return 0;

        std::lock_guard<std::mutex> lock(m_Mutex);
        const uint64_t id = AllocateRegistrationId();
        m_Registrations.push_back({id, owner, subscription});
        m_SubscriptionCount.store(m_Registrations.size());
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

        std::vector<StructureEventSubscription> removed;
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
            m_SubscriptionCount.store(after);
            if (QueueOrDestroyRemovedSubscriptions(removed, lock))
                m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
            else if (!IsInsideAnyGameplayCallback() &&
                     !IsInsideDispatcherCleanup() &&
                     !IsDispatchCleanupComplete())
                m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
        }
        for (const StructureEventSubscription& subscription : removed)
            DestroySubscriptionUserData(subscription);
        return after != before;
    }

    bool StructureEventDispatcher::UnregisterCallbackForOwner(void* owner, uint64_t registrationId)
    {
        if (!owner || registrationId == 0)
            return false;

        std::vector<StructureEventSubscription> removed;
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
            m_SubscriptionCount.store(after);
            if (QueueOrDestroyRemovedSubscriptions(removed, lock))
                m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
            else if (!IsInsideAnyGameplayCallback() &&
                     !IsInsideDispatcherCleanup() &&
                     !IsDispatchCleanupComplete())
                m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
        }
        for (const StructureEventSubscription& subscription : removed)
            DestroySubscriptionUserData(subscription);
        return after != before;
    }

    size_t StructureEventDispatcher::UnregisterCallbacksForOwner(void* owner)
    {
        if (!owner)
            return 0;

        std::vector<StructureEventSubscription> removed;
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
            m_SubscriptionCount.store(after);
            if (QueueOrDestroyRemovedSubscriptions(removed, lock))
                m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
            else if (!IsInsideAnyGameplayCallback() &&
                     !IsInsideDispatcherCleanup() &&
                     !IsDispatchCleanupComplete())
                m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
        }
        for (const StructureEventSubscription& subscription : removed)
            DestroySubscriptionUserData(subscription);
        return before - after;
    }

    bool StructureEventDispatcher::QueueOrDestroyRemovedSubscriptions(
        std::vector<StructureEventSubscription>& removed,
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

    bool StructureEventDispatcher::IsDispatchCleanupComplete() const
    {
        return m_DispatchDepth == 0 && m_PendingDestroy.empty() && m_PendingDestroyInProgress == 0;
    }

    void StructureEventDispatcher::FinishDispatch()
    {
        std::vector<StructureEventSubscription> pending;
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

        for (const StructureEventSubscription& subscription : pending)
            DestroySubscriptionUserData(subscription);
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
            m_PendingDestroyInProgress -= pending.size();
        }
        m_DispatchCv.notify_all();
    }

#ifdef OBELISK_STRUCTURE_EVENT_DISPATCHER_ENABLE_TEST_HOOKS
    void StructureEventDispatcher::SetNextRegistrationIdForTesting(uint64_t nextRegistrationId)
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        m_NextRegistrationId = nextRegistrationId == 0 ? 1 : nextRegistrationId;
    }
#endif

    size_t StructureEventDispatcher::Dispatch(const StructureEventView& event)
    {
        if (!IsValidEvent(event))
            return 0;

        size_t dispatched = 0;
        try
        {
            std::vector<StructureScalarValue> scalarCopies(event.Scalars.begin(), event.Scalars.end());
            StructureEventView copiedEvent{
                .Kind = event.Kind,
                .FunctionNameIndex = event.FunctionNameIndex,
                .OuterNameIndex = event.OuterNameIndex,
                .Scalars = scalarCopies,
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
                        GameplayCallbackScope callbackScope(GameplayCallbackFamily::Structure);
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
            }
            catch (const std::exception& e)
            {
                FinishDispatch();
                if (Obelisk::Logger::IsInitialized())
                {
                    OBELISK_ERROR("Structure event dispatch failed internally: {}", e.what());
                }
                return dispatched;
            }
            catch (...)
            {
                FinishDispatch();
                if (Obelisk::Logger::IsInitialized())
                    OBELISK_ERROR("Structure event dispatch failed internally with an unknown exception.");
                return dispatched;
            }

            FinishDispatch();
            return dispatched;
        }
        catch (const std::exception& e)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Structure event dispatch setup failed: {}", e.what());
            return 0;
        }
        catch (...)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Structure event dispatch setup failed with an unknown exception.");
            return 0;
        }
    }

    size_t StructureEventDispatcher::SubscriptionCount() const
    {
        return m_SubscriptionCount.load();
    }
}
