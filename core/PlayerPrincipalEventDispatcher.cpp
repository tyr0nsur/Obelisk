#if !defined(obelisk_EXPORTS)
#define OBELISK_PLAYER_PRINCIPAL_EVENT_DISPATCHER_ENABLE_TEST_HOOKS
#endif

#include "PlayerPrincipalEventDispatcher.h"
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
            uint64_t Generation = 0;
            PlayerPrincipalEventSubscription Subscription;
        };

        constexpr size_t kMaxBoolCount = 2;
        constexpr size_t kStackCallbackCapacity = 4;

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

        bool IsKnownEventKind(PlayerPrincipalEventKind kind)
        {
            return static_cast<uint32_t>(kind) <=
                static_cast<uint32_t>(PlayerPrincipalEventKind::SessionEnd);
        }

        bool IsKnownAction(PlayerPrincipalAction action)
        {
            return static_cast<uint32_t>(action) <=
                static_cast<uint32_t>(PlayerPrincipalAction::CandidateInvalidated);
        }

        bool IsKnownBoolField(PlayerPrincipalBoolField field)
        {
            return static_cast<uint32_t>(field) <=
                static_cast<uint32_t>(PlayerPrincipalBoolField::ReturnValue);
        }

        bool HasCanonicalStartBools(const PlayerPrincipalEventView& event)
        {
            if (event.Bools.size() != 2)
                return false;

            return event.Bools[0].Field == PlayerPrincipalBoolField::BIsFromLogin &&
                event.Bools[1].Field == PlayerPrincipalBoolField::ReturnValue;
        }

        bool IsValidEvent(const PlayerPrincipalEventView& event)
        {
            if (!IsKnownEventKind(event.Kind) || !IsKnownAction(event.Action))
                return false;
            if (event.Bools.size() > kMaxBoolCount)
                return false;

            for (const PlayerPrincipalBoolValue& value : event.Bools)
            {
                if (!IsKnownBoolField(value.Field))
                    return false;
            }

            switch (event.Kind)
            {
            case PlayerPrincipalEventKind::SessionStart:
                return event.Action == PlayerPrincipalAction::CandidateCreated &&
                    HasCanonicalStartBools(event) &&
                    event.Bools[0].Value &&
                    event.Bools[1].Value;
            case PlayerPrincipalEventKind::SessionStartRejected:
                return event.Action == PlayerPrincipalAction::None &&
                    HasCanonicalStartBools(event) &&
                    !(event.Bools[0].Value && event.Bools[1].Value);
            case PlayerPrincipalEventKind::SessionEnd:
                return event.Action == PlayerPrincipalAction::CandidateInvalidated &&
                    event.Bools.empty();
            }

            return false;
        }

        void DestroySubscriptionUserData(
            const PlayerPrincipalEventSubscription& subscription,
            bool propagateFailure = false)
        {
            if (!subscription.DestroyUserData)
                return;

            try
            {
                DestroyUserDataScope cleanupScope;
                GameplayCallbackScope callbackScope(GameplayCallbackFamily::PlayerPrincipal);
                subscription.DestroyUserData(subscription.UserData);
            }
            catch (const std::exception& e)
            {
                if (Obelisk::Logger::IsInitialized())
                    OBELISK_ERROR("Player principal event subscription cleanup threw: {}", e.what());
                if (propagateFailure)
                    throw;
            }
            catch (...)
            {
                if (Obelisk::Logger::IsInitialized())
                    OBELISK_ERROR("Player principal event subscription cleanup threw an unknown exception.");
                if (propagateFailure)
                    throw;
            }
        }

        void DestroySubscriptionsForOwnerCleanup(
            const std::vector<PlayerPrincipalEventSubscription>& subscriptions)
        {
            std::exception_ptr firstFailure;
            for (const PlayerPrincipalEventSubscription& subscription : subscriptions)
            {
                try
                {
                    DestroySubscriptionUserData(subscription, true);
                }
                catch (...)
                {
                    if (!firstFailure)
                        firstFailure = std::current_exception();
                }
            }

            if (firstFailure)
                std::rethrow_exception(firstFailure);
        }

        bool IsInsideAnyGameplayCallback()
        {
            return GameplayCallbackScope::IsInsideAnyCallback();
        }
    }

    PlayerPrincipalEventDispatcher& PlayerPrincipalEventDispatcher::Get()
    {
        static auto* dispatcher = new PlayerPrincipalEventDispatcher();
        return *dispatcher;
    }

    uint64_t PlayerPrincipalEventDispatcher::Register(
        void* owner,
        const PlayerPrincipalEventSubscription& subscription)
    {
        if (!owner || !subscription.Callback)
            return 0;

        try
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
            const uint64_t id = AllocateRegistrationId();
            const uint64_t generation = m_NextGeneration++;
            if (m_NextGeneration == 0)
                m_NextGeneration = 1;
            m_Registrations.push_back({id, generation, owner, subscription});
            m_SubscriptionCount.fetch_add(1, std::memory_order_release);
            return id;
        }
        catch (const std::exception& e)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Player principal event registration failed: {}", e.what());
        }
        catch (...)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Player principal event registration failed with an unknown exception.");
        }

        return 0;
    }

    uint64_t PlayerPrincipalEventDispatcher::AllocateRegistrationId()
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

    bool PlayerPrincipalEventDispatcher::HasRegistrationId(uint64_t registrationId) const
    {
        return std::any_of(m_Registrations.begin(),
                           m_Registrations.end(),
                           [registrationId](const Registration& item) {
                               return item.Id == registrationId;
                           });
    }

    bool PlayerPrincipalEventDispatcher::IsRegistrationActive(uint64_t registrationId, uint64_t generation) const
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        return std::any_of(m_Registrations.begin(),
                           m_Registrations.end(),
                           [registrationId, generation](const Registration& item) {
                               return item.Id == registrationId && item.Generation == generation;
                           });
    }

    bool PlayerPrincipalEventDispatcher::Unregister(uint64_t registrationId)
    {
        if (registrationId == 0)
            return false;

        std::vector<PlayerPrincipalEventSubscription> removed;
        size_t before = 0;
        size_t after = 0;
        try
        {
            std::unique_lock<std::mutex> lock(m_Mutex);
            before = m_Registrations.size();
            const size_t matchingCount = static_cast<size_t>(
                std::count_if(m_Registrations.begin(),
                              m_Registrations.end(),
                              [registrationId](const Registration& item) {
                                  return item.Id == registrationId;
                              }));
            if (matchingCount == 0)
            {
                if (!IsInsideAnyGameplayCallback() &&
                    !IsInsideDispatcherCleanup() &&
                    !IsDispatchCleanupComplete())
                {
                    m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
                }
                return false;
            }
            removed.reserve(matchingCount);
            if (m_DispatchDepth > 0)
                m_PendingDestroy.reserve(m_PendingDestroy.size() + matchingCount);
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
        catch (const std::exception& e)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Player principal event unregister failed: {}", e.what());
            return false;
        }
        catch (...)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Player principal event unregister failed with an unknown exception.");
            return false;
        }
        for (const PlayerPrincipalEventSubscription& subscription : removed)
            DestroySubscriptionUserData(subscription);
        return after != before;
    }

    bool PlayerPrincipalEventDispatcher::UnregisterCallbackForOwner(void* owner, uint64_t registrationId)
    {
        if (!owner || registrationId == 0)
            return false;

        std::vector<PlayerPrincipalEventSubscription> removed;
        std::exception_ptr deferredFailure;
        size_t before = 0;
        size_t after = 0;
        try
        {
            std::unique_lock<std::mutex> lock(m_Mutex);
            before = m_Registrations.size();
            const size_t matchingCount = static_cast<size_t>(
                std::count_if(m_Registrations.begin(),
                              m_Registrations.end(),
                              [owner, registrationId](const Registration& item) {
                                  return item.Owner == owner && item.Id == registrationId;
                              }));
            if (matchingCount == 0)
            {
                if (!IsInsideAnyGameplayCallback() &&
                    !IsInsideDispatcherCleanup() &&
                    !IsDispatchCleanupComplete())
                {
                    m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
                }
                return false;
            }
            removed.reserve(matchingCount);
            if (m_DispatchDepth > 0)
                m_PendingDestroy.reserve(m_PendingDestroy.size() + matchingCount);
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
            uint64_t cleanupBatchId = 0;
            if (!IsInsideAnyGameplayCallback() && !IsInsideDispatcherCleanup())
            {
                cleanupBatchId = m_NextCleanupBatchId++;
                if (m_NextCleanupBatchId == 0)
                    m_NextCleanupBatchId = 1;
            }
            if (QueueOrDestroyRemovedSubscriptions(removed, lock, cleanupBatchId))
            {
                m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
                deferredFailure = TakeDeferredDestroyFailure(cleanupBatchId);
            }
            else if (!IsInsideAnyGameplayCallback() &&
                     !IsInsideDispatcherCleanup() &&
                     !IsDispatchCleanupComplete())
                m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
        }
        catch (const std::exception& e)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Player principal event owner unregister failed: {}", e.what());
            return false;
        }
        catch (...)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Player principal event owner unregister failed with an unknown exception.");
            return false;
        }
        for (const PlayerPrincipalEventSubscription& subscription : removed)
            DestroySubscriptionUserData(subscription);
        return after != before;
    }

    size_t PlayerPrincipalEventDispatcher::UnregisterCallbacksForOwner(void* owner)
    {
        if (!owner)
            return 0;

        std::vector<PlayerPrincipalEventSubscription> removed;
        size_t before = 0;
        size_t after = 0;
        try
        {
            std::unique_lock<std::mutex> lock(m_Mutex);
            before = m_Registrations.size();
            const size_t matchingCount = static_cast<size_t>(
                std::count_if(m_Registrations.begin(),
                              m_Registrations.end(),
                              [owner](const Registration& item) {
                                  return item.Owner == owner;
                              }));
            if (matchingCount == 0)
            {
                if (!IsInsideAnyGameplayCallback() &&
                    !IsInsideDispatcherCleanup() &&
                    !IsDispatchCleanupComplete())
                {
                    m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
                }
                return 0;
            }
            removed.reserve(matchingCount);
            if (m_DispatchDepth > 0)
                m_PendingDestroy.reserve(m_PendingDestroy.size() + matchingCount);
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
        catch (const std::exception& e)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Player principal event owner cleanup failed: {}", e.what());
            throw;
        }
        catch (...)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Player principal event owner cleanup failed with an unknown exception.");
            throw;
        }
        DestroySubscriptionsForOwnerCleanup(removed);
        if (deferredFailure)
            std::rethrow_exception(deferredFailure);
        return before - after;
    }

    bool PlayerPrincipalEventDispatcher::QueueOrDestroyRemovedSubscriptions(
        std::vector<PlayerPrincipalEventSubscription>& removed,
        std::unique_lock<std::mutex>&,
        uint64_t cleanupBatchId)
    {
        if (removed.empty())
            return false;

        if (m_DispatchDepth > 0)
        {
            for (const PlayerPrincipalEventSubscription& subscription : removed)
                m_PendingDestroy.push_back({subscription, cleanupBatchId});
            removed.clear();
            return !IsInsideAnyGameplayCallback();
        }

        return false;
    }

    std::exception_ptr PlayerPrincipalEventDispatcher::TakeDeferredDestroyFailure(uint64_t cleanupBatchId)
    {
        if (cleanupBatchId == 0)
            return nullptr;

        const auto failureIt = std::find_if(
            m_DeferredDestroyFailures.begin(),
            m_DeferredDestroyFailures.end(),
            [cleanupBatchId](const DeferredDestroyFailure& failure) {
                return failure.CleanupBatchId == cleanupBatchId;
            });
        if (failureIt == m_DeferredDestroyFailures.end())
            return nullptr;

        std::exception_ptr failure = failureIt->Failure;
        m_DeferredDestroyFailures.erase(failureIt);
        return failure;
    }

    bool PlayerPrincipalEventDispatcher::IsDispatchCleanupComplete() const
    {
        return m_DispatchDepth == 0 && m_PendingDestroy.empty() && m_PendingDestroyInProgress == 0;
    }

    void PlayerPrincipalEventDispatcher::FinishDispatch()
    {
        std::vector<PendingDestroy> pending;
        std::vector<DeferredDestroyFailure> failures;
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

        for (const PendingDestroy& item : pending)
        {
            try
            {
                DestroySubscriptionUserData(item.Subscription, item.CleanupBatchId != 0);
            }
            catch (...)
            {
                if (item.CleanupBatchId == 0)
                    continue;
                const bool alreadyCaptured = std::any_of(
                    failures.begin(),
                    failures.end(),
                    [&item](const DeferredDestroyFailure& failure) {
                        return failure.CleanupBatchId == item.CleanupBatchId;
                    });
                if (!alreadyCaptured)
                    failures.push_back({item.CleanupBatchId, std::current_exception()});
            }
        }
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
            m_PendingDestroyInProgress -= pending.size();
            m_DeferredDestroyFailures.insert(
                m_DeferredDestroyFailures.end(),
                failures.begin(),
                failures.end());
        }
        m_DispatchCv.notify_all();
    }

#ifdef OBELISK_PLAYER_PRINCIPAL_EVENT_DISPATCHER_ENABLE_TEST_HOOKS
    void PlayerPrincipalEventDispatcher::SetNextRegistrationIdForTesting(uint64_t nextRegistrationId)
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        m_NextRegistrationId = nextRegistrationId == 0 ? 1 : nextRegistrationId;
    }
#endif

    size_t PlayerPrincipalEventDispatcher::Dispatch(const PlayerPrincipalEventView& event)
    {
        if (m_SubscriptionCount.load(std::memory_order_acquire) == 0)
            return 0;
        if (!IsValidEvent(event))
            return 0;

        size_t dispatched = 0;
        try
        {
            std::array<PlayerPrincipalBoolValue, kMaxBoolCount> boolCopies{};
            std::copy(event.Bools.begin(), event.Bools.end(), boolCopies.begin());
            PlayerPrincipalEventView copiedEvent{
                .Kind = event.Kind,
                .Action = event.Action,
                .EventSequence = event.EventSequence,
                .ServerProcessEpoch = event.ServerProcessEpoch,
                .Bools = std::span<const PlayerPrincipalBoolValue>(boolCopies.data(), event.Bools.size()),
            };

            std::array<DispatchRegistration, kStackCallbackCapacity> stackCallbacks{};
            size_t stackCallbackCount = 0;
            std::vector<DispatchRegistration> heapCallbacks;
            try
            {
                {
                    std::lock_guard<std::mutex> lock(m_Mutex);
                    ++m_DispatchDepth;
                    if (m_Registrations.size() <= stackCallbacks.size())
                    {
                        for (const Registration& item : m_Registrations)
                            stackCallbacks[stackCallbackCount++] = {item.Id, item.Generation, item.Subscription};
                    }
                    else
                    {
                        heapCallbacks.reserve(m_Registrations.size());
                        for (const Registration& item : m_Registrations)
                            heapCallbacks.push_back({item.Id, item.Generation, item.Subscription});
                    }
                }

                const std::span<const DispatchRegistration> callbacks =
                    heapCallbacks.empty()
                        ? std::span<const DispatchRegistration>(stackCallbacks.data(), stackCallbackCount)
                        : std::span<const DispatchRegistration>(heapCallbacks.data(), heapCallbacks.size());

                for (const DispatchRegistration& item : callbacks)
                {
                    if (!IsRegistrationActive(item.Id, item.Generation))
                        continue;
                    if (!item.Subscription.Callback)
                        continue;

                    try
                    {
                        GameplayCallbackScope callbackScope(GameplayCallbackFamily::PlayerPrincipal);
                        item.Subscription.Callback(copiedEvent, item.Subscription.UserData);
                        ++dispatched;
                    }
                    catch (const std::exception& e)
                    {
                        if (Obelisk::Logger::IsInitialized())
                            OBELISK_ERROR("Player principal event callback threw: {}", e.what());
                    }
                    catch (...)
                    {
                        if (Obelisk::Logger::IsInitialized())
                            OBELISK_ERROR("Player principal event callback threw an unknown exception.");
                    }
                }
            }
            catch (const std::exception& e)
            {
                FinishDispatch();
                if (Obelisk::Logger::IsInitialized())
                    OBELISK_ERROR("Player principal event dispatch failed internally: {}", e.what());
                return dispatched;
            }
            catch (...)
            {
                FinishDispatch();
                if (Obelisk::Logger::IsInitialized())
                    OBELISK_ERROR("Player principal event dispatch failed internally with an unknown exception.");
                return dispatched;
            }

            FinishDispatch();
            return dispatched;
        }
        catch (const std::exception& e)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Player principal event dispatch setup failed: {}", e.what());
            return 0;
        }
        catch (...)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Player principal event dispatch setup failed with an unknown exception.");
            return 0;
        }
    }

    size_t PlayerPrincipalEventDispatcher::SubscriptionCount() const
    {
        return m_SubscriptionCount.load(std::memory_order_acquire);
    }
}
