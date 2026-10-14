#if !defined(obelisk_EXPORTS)
#define OBELISK_CHAT_EVENT_DISPATCHER_ENABLE_TEST_HOOKS
#endif

#include "ChatEventDispatcher.h"
#include "GameplayCallbackScope.h"
#include "runtime/Logger.h"

#include <algorithm>
#include <exception>
#include <stdexcept>
#include <new>
#include <string>

namespace Obelisk::Core
{
    namespace
    {
        struct DispatchRegistration
        {
            uint64_t Id = 0;
            uint64_t Generation = 0;
            ChatMessageSubscription Subscription;
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

        void DestroySubscriptionUserData(const ChatMessageSubscription& subscription, bool propagateFailure = false)
        {
            if (!subscription.DestroyUserData)
                return;

            auto executionLease = OwnerExecutionGate::EnterLifecycle(
                subscription.ExecutionBinding, OwnerExecutionGate::LifecycleEntry::Cleanup);
            if (!executionLease)
                throw std::runtime_error("Subscription cleanup admission denied; keep plugin mapped");

            try
            {
                DestroyUserDataScope cleanupScope;
                GameplayCallbackScope callbackScope(GameplayCallbackFamily::Chat);
                subscription.DestroyUserData(subscription.UserData);
            }
            catch (const std::exception& e)
            {
                if (Obelisk::Logger::IsInitialized())
                    OBELISK_ERROR("Chat message subscription cleanup threw: {}", e.what());
                if (propagateFailure)
                    throw;
            }
            catch (...)
            {
                if (Obelisk::Logger::IsInitialized())
                    OBELISK_ERROR("Chat message subscription cleanup threw an unknown exception.");
                if (propagateFailure)
                    throw;
            }
        }

        std::vector<ChatMessageSubscription> DestroySubscriptionsForOwnerCleanup(
            const std::vector<ChatMessageSubscription>& subscriptions,
            std::exception_ptr& firstFailure, size_t additionalCapacity = 0)
        {
            std::vector<ChatMessageSubscription> failed;
            // Allocate before any deleter succeeds: failures can then be recorded
            // without an allocation after partially destroying the input batch.
            if (additionalCapacity > failed.max_size() - subscriptions.size())
                throw std::length_error("Cleanup failure batch exceeds supported size");
            failed.reserve(subscriptions.size() + additionalCapacity);
            for (const ChatMessageSubscription& subscription : subscriptions)
            {
                auto cleanupLease = OwnerExecutionGate::EnterLifecycle(
                    subscription.ExecutionBinding, OwnerExecutionGate::LifecycleEntry::Cleanup);
                try
                {
                    DestroySubscriptionUserData(subscription, true);
                }
                catch (...)
                {
                    if (!firstFailure)
                        firstFailure = std::current_exception();
                    failed.push_back(subscription);
                }
            }

            return failed;
        }

        bool IsInsideAnyGameplayCallback()
        {
            return GameplayCallbackScope::IsInsideAnyCallback();
        }
    }

    ChatEventDispatcher& ChatEventDispatcher::Get()
    {
        static auto* dispatcher = new ChatEventDispatcher();
        return *dispatcher;
    }

    uint64_t ChatEventDispatcher::Register(void* owner, const ChatMessageSubscription& subscription)
    {
        if (!owner || !subscription.Callback)
            return 0;

        const auto binding = OwnerExecutionGate::Get().Capture(owner);
        auto registrationLease = OwnerExecutionGate::EnterRegistration(binding);
        if (!registrationLease)
            return 0;
        auto storedSubscription = subscription;
        storedSubscription.ExecutionBinding = binding;
        storedSubscription.ExecutionOwner = owner;

        try
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
            const uint64_t id = AllocateRegistrationId();
            const uint64_t generation = m_NextGeneration++;
            if (m_NextGeneration == 0)
                m_NextGeneration = 1;
            m_Registrations.push_back({id, generation, owner, storedSubscription});
            m_SubscriptionCount.fetch_add(1, std::memory_order_release);
            return id;
        }
        catch (const std::exception& e)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Chat event registration failed: {}", e.what());
        }
        catch (...)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Chat event registration failed with an unknown exception.");
        }

        return 0;
    }

    uint64_t ChatEventDispatcher::AllocateRegistrationId()
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

    bool ChatEventDispatcher::HasRegistrationId(uint64_t registrationId) const
    {
        return std::any_of(m_Registrations.begin(), m_Registrations.end(), [registrationId](const Registration& item) {
            return item.Id == registrationId;
        });
    }

    bool ChatEventDispatcher::IsRegistrationActive(uint64_t registrationId, uint64_t generation) const
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        return std::any_of(m_Registrations.begin(),
                           m_Registrations.end(),
                           [registrationId, generation](const Registration& item) {
                               return item.Id == registrationId && item.Generation == generation;
                           });
    }

    bool ChatEventDispatcher::Unregister(uint64_t registrationId)
    {
        if (registrationId == 0)
            return false;

        const auto cleanupBinding = CaptureCleanupBinding(nullptr, registrationId);
        auto cleanupLease = OwnerExecutionGate::EnterLifecycle(
            cleanupBinding, OwnerExecutionGate::LifecycleEntry::Cleanup);
        if (!cleanupLease)
            throw std::runtime_error("Dispatcher cleanup admission denied; keep plugin mapped");

        std::vector<ChatMessageSubscription> removed;
        std::exception_ptr deferredFailure;
        void* removedOwner = nullptr;
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
                                          [registrationId, &removed, &removedOwner](const Registration& item) {
                                              if (item.Id != registrationId)
                                                  return false;
                                              removedOwner = item.Owner;
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
            if (m_DispatchDepth > 0 && cleanupBatchId != 0)
                ReserveDeferredDestroyFailureSlots(matchingCount);
            if (QueueOrDestroyRemovedSubscriptions(removedOwner, removed, lock, cleanupBatchId))
            {
                m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
                removed = TakeDeferredDestroyFailures(cleanupBatchId, deferredFailure);
            }
            else if (!IsInsideAnyGameplayCallback() &&
                     !IsInsideDispatcherCleanup() &&
                     !IsDispatchCleanupComplete())
                m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
        }
        catch (const std::exception& e)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Chat event unregister failed: {}", e.what());
            return false;
        }
        catch (...)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Chat event unregister failed with an unknown exception.");
            return false;
        }
        std::exception_ptr cleanupFailure;
        std::vector<ChatMessageSubscription> failed =
            DestroyRemovedSubscriptionsForOwner(removedOwner, removed, cleanupFailure);
        if (deferredFailure)
            cleanupFailure = cleanupFailure ? cleanupFailure : deferredFailure;
        if (!failed.empty())
            RetainFailedOwnerDestroySubscriptions(removedOwner, failed);
        if (cleanupFailure)
            std::rethrow_exception(cleanupFailure);
        return after != before;
    }

    bool ChatEventDispatcher::UnregisterCallbackForOwner(void* owner, uint64_t registrationId)
    {
        if (!owner || registrationId == 0)
            return false;

        const auto cleanupBinding = CaptureCleanupBinding(owner, registrationId);
        auto cleanupLease = OwnerExecutionGate::EnterLifecycle(
            cleanupBinding, OwnerExecutionGate::LifecycleEntry::Cleanup);
        if (!cleanupLease)
            throw std::runtime_error("Dispatcher cleanup admission denied; keep plugin mapped");

        std::vector<ChatMessageSubscription> removed;
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
            if (m_DispatchDepth > 0 && cleanupBatchId != 0)
                ReserveDeferredDestroyFailureSlots(matchingCount);
            if (QueueOrDestroyRemovedSubscriptions(owner, removed, lock, cleanupBatchId))
            {
                m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
                removed = TakeDeferredDestroyFailures(cleanupBatchId, deferredFailure);
            }
            else if (!IsInsideAnyGameplayCallback() &&
                     !IsInsideDispatcherCleanup() &&
                     !IsDispatchCleanupComplete())
                m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
        }
        catch (const std::exception& e)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Chat event owner unregister failed: {}", e.what());
            return false;
        }
        catch (...)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Chat event owner unregister failed with an unknown exception.");
            return false;
        }
        std::exception_ptr cleanupFailure;
        std::vector<ChatMessageSubscription> failed =
            DestroyRemovedSubscriptionsForOwner(owner, removed, cleanupFailure);
        if (deferredFailure)
            cleanupFailure = cleanupFailure ? cleanupFailure : deferredFailure;
        if (!failed.empty())
            RetainFailedOwnerDestroySubscriptions(owner, failed);
        if (cleanupFailure)
            std::rethrow_exception(cleanupFailure);
        return after != before;
    }

    size_t ChatEventDispatcher::UnregisterCallbacksForOwner(
        void* owner, OwnerExecutionGate::Clock::time_point deadline)
    {
        if (!owner)
            return 0;

        const auto cleanupBinding = CaptureCleanupBinding(owner);
        auto cleanupLease = OwnerExecutionGate::EnterLifecycle(
            cleanupBinding, OwnerExecutionGate::LifecycleEntry::Cleanup);
        if (!cleanupLease)
            throw std::runtime_error("Dispatcher cleanup admission denied; keep plugin mapped");

        RequireCleanupRetentionIntact();

        std::vector<ChatMessageSubscription> removed;
        std::vector<ChatMessageSubscription> currentRemoved;
        std::exception_ptr retainedFailure;
        std::exception_ptr deferredFailure;
        std::vector<ChatMessageSubscription> deferredFailures;
        size_t retainedCount = 0;
        size_t before = 0;
        size_t after = 0;
        const auto retainPendingOwnerCleanupFailures = [&]() {
            if (!removed.empty())
                RetainFailedOwnerDestroySubscriptions(owner, removed, retainedFailure);
            if (!currentRemoved.empty())
                RetainFailedOwnerDestroySubscriptions(owner, currentRemoved);
        };
        try
        {
            std::unique_lock<std::mutex> lock(m_Mutex);
            removed = TakeFailedOwnerDestroySubscriptions(owner, retainedFailure);
            retainedCount = removed.size();
#ifdef OBELISK_CHAT_EVENT_DISPATCHER_ENABLE_TEST_HOOKS
            if (retainedCount != 0 && m_FailNextFailedOwnerDestroyRetrySetupForTesting)
            {
                m_FailNextFailedOwnerDestroyRetrySetupForTesting = false;
                throw std::bad_alloc();
            }
#endif
            before = m_Registrations.size();
            const size_t matchingCount = static_cast<size_t>(
                std::count_if(m_Registrations.begin(),
                              m_Registrations.end(),
                              [owner](const Registration& item) {
                                  return item.Owner == owner;
                              }));
            if (matchingCount == 0 && retainedCount == 0)
            {
                if (!IsInsideAnyGameplayCallback() &&
                    !IsInsideDispatcherCleanup() &&
                    !IsDispatchCleanupComplete())
                {
                    if (!m_DispatchCv.wait_until(lock, deadline, [this]() { return IsDispatchCleanupComplete(); }))
                        throw std::runtime_error("Dispatcher owner cleanup timed out; keep plugin mapped");
                    removed = TakeFailedOwnerDestroySubscriptions(owner, retainedFailure);
                    retainedCount = removed.size();
#ifdef OBELISK_CHAT_EVENT_DISPATCHER_ENABLE_TEST_HOOKS
                    if (retainedCount != 0 && m_FailNextFailedOwnerDestroyRetrySetupForTesting)
                    {
                        m_FailNextFailedOwnerDestroyRetrySetupForTesting = false;
                        throw std::bad_alloc();
                    }
#endif
                    if (retainedCount != 0)
                        after = before;
                    else
                        return 0;
                }
                else
                    return 0;
            }
            removed.reserve(retainedCount + matchingCount);
            currentRemoved.reserve(matchingCount);
            if (m_DispatchDepth > 0)
                m_PendingDestroy.reserve(m_PendingDestroy.size() + matchingCount);
            auto keepEnd = std::remove_if(m_Registrations.begin(),
                                          m_Registrations.end(),
                                          [owner, &currentRemoved](const Registration& item) {
                                              if (item.Owner != owner)
                                                  return false;
                                              currentRemoved.push_back(item.Subscription);
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
            if (m_DispatchDepth > 0 && cleanupBatchId != 0)
                ReserveDeferredDestroyFailureSlots(matchingCount);
            const bool queuedForDeferredDestroy = m_DispatchDepth > 0 && !currentRemoved.empty();
            if (QueueOrDestroyRemovedSubscriptions(owner, currentRemoved, lock, cleanupBatchId))
            {
                if (!m_DispatchCv.wait_until(lock, deadline, [this]() { return IsDispatchCleanupComplete(); }))
                    throw std::runtime_error("Dispatcher owner cleanup timed out; keep plugin mapped");
                deferredFailures = TakeDeferredDestroyFailures(cleanupBatchId, deferredFailure);
            }
            if (!queuedForDeferredDestroy)
                removed.insert(removed.end(), currentRemoved.begin(), currentRemoved.end());
            else if (!IsInsideAnyGameplayCallback() &&
                     !IsInsideDispatcherCleanup() &&
                     !IsDispatchCleanupComplete())
            {
                if (!m_DispatchCv.wait_until(lock, deadline, [this]() { return IsDispatchCleanupComplete(); }))
                    throw std::runtime_error("Dispatcher owner cleanup timed out; keep plugin mapped");
            }
        }
        catch (const std::exception& e)
        {
            retainPendingOwnerCleanupFailures();
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Chat event owner cleanup failed: {}", e.what());
            throw;
        }
        catch (...)
        {
            retainPendingOwnerCleanupFailures();
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Chat event owner cleanup failed with an unknown exception.");
            throw;
        }
        std::exception_ptr cleanupFailure;
        std::vector<ChatMessageSubscription> failed;
        try
        {
            failed = DestroyRemovedSubscriptionsForOwner(
                owner, removed, cleanupFailure, deferredFailures.size());
        }
        catch (...)
        {
            RetainFailedOwnerDestroySubscriptions(owner, deferredFailures, std::current_exception());
            throw;
        }
        if (retainedFailure)
            cleanupFailure = cleanupFailure ? cleanupFailure : retainedFailure;
        if (deferredFailure)
        {
            cleanupFailure = cleanupFailure ? cleanupFailure : deferredFailure;
            failed.insert(failed.end(), deferredFailures.begin(), deferredFailures.end());
        }
        if (!failed.empty())
            RetainFailedOwnerDestroySubscriptions(owner, failed);
        RequireCleanupRetentionIntact();
        if (cleanupFailure)
            std::rethrow_exception(cleanupFailure);
        return retainedCount + (before - after);
    }

#ifdef OBELISK_CHAT_EVENT_DISPATCHER_ENABLE_TEST_HOOKS
    void ChatEventDispatcher::SetNextRegistrationIdForTesting(uint64_t nextRegistrationId)
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        m_NextRegistrationId = nextRegistrationId == 0 ? 1 : nextRegistrationId;
    }

    void ChatEventDispatcher::FailNextDeferredDestroyFailureRecordForTesting()
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        m_FailNextDeferredDestroyFailureRecordForTesting = true;
    }

    void ChatEventDispatcher::FailNextFailedOwnerDestroyRetrySetupForTesting()
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        m_FailNextFailedOwnerDestroyRetrySetupForTesting = true;
    }
#endif

    bool ChatEventDispatcher::QueueOrDestroyRemovedSubscriptions(
        void* owner,
        std::vector<ChatMessageSubscription>& removed,
        std::unique_lock<std::mutex>&,
        uint64_t cleanupBatchId)
    {
        if (removed.empty())
            return false;

        if (m_DispatchDepth > 0)
        {
            const bool needsFailureReservation = cleanupBatchId != 0;
            try
            {
                for (const ChatMessageSubscription& subscription : removed)
                    m_PendingDestroy.push_back({owner, subscription, cleanupBatchId});
            }
            catch (...)
            {
                if (needsFailureReservation)
                    ReleaseDeferredDestroyFailureSlots(removed.size());
                throw;
            }
            removed.clear();
            return !IsInsideAnyGameplayCallback();
        }

        return false;
    }

    std::vector<ChatMessageSubscription> ChatEventDispatcher::TakeFailedOwnerDestroySubscriptions(
        void* owner,
        std::exception_ptr& firstFailure)
    {
        if (m_CleanupRetentionFailed)
            throw std::runtime_error("Dispatcher cleanup retention failed; keep plugin mapped");
        std::vector<ChatMessageSubscription> subscriptions;
        const size_t fallbackCount =
            m_HasFallbackFailedOwnerDestroy && m_FallbackFailedOwnerDestroy.Owner == owner ? 1 : 0;
        const size_t matchingCount = static_cast<size_t>(
            std::count_if(m_FailedOwnerDestroy.begin(),
                          m_FailedOwnerDestroy.end(),
                          [owner](const FailedOwnerDestroy& item) {
                              return item.Owner == owner;
                          }));
        const size_t deferredFallbackCount = m_HasFallbackDeferredDestroyFailure &&
            m_FallbackDeferredDestroyFailure.Subscription.ExecutionOwner == owner ? 1 : 0;
        const size_t deferredCount = static_cast<size_t>(std::count_if(
            m_DeferredDestroyFailures.begin(), m_DeferredDestroyFailures.end(),
            [owner](const DeferredDestroyFailure& item) { return item.Subscription.ExecutionOwner == owner; }));
        subscriptions.reserve(fallbackCount + matchingCount + deferredFallbackCount + deferredCount);
        if (m_HasFallbackFailedOwnerDestroy &&
            m_FallbackFailedOwnerDestroy.Owner == owner)
        {
            if (!firstFailure && m_FallbackFailedOwnerDestroy.UnreportedFailure)
                firstFailure = m_FallbackFailedOwnerDestroy.UnreportedFailure;
            subscriptions.push_back(m_FallbackFailedOwnerDestroy.Subscription);
            m_HasFallbackFailedOwnerDestroy = false;
            m_FallbackFailedOwnerDestroy = {};
        }

        auto keepEnd = std::remove_if(
            m_FailedOwnerDestroy.begin(),
            m_FailedOwnerDestroy.end(),
            [owner, &subscriptions, &firstFailure](const FailedOwnerDestroy& item) {
                if (item.Owner != owner)
                    return false;
                if (!firstFailure && item.UnreportedFailure)
                    firstFailure = item.UnreportedFailure;
                subscriptions.push_back(item.Subscription);
                return true;
            });
        m_FailedOwnerDestroy.erase(keepEnd, m_FailedOwnerDestroy.end());
        // A deadline can abandon a waiting batch before its deferred deleter
        // finishes. Owner cleanup must collect that batch's failures too; no
        // plugin-defined exception or userdata may survive successful drain.
        if (deferredFallbackCount != 0)
        {
            if (!firstFailure)
                firstFailure = m_FallbackDeferredDestroyFailure.Failure;
            subscriptions.push_back(m_FallbackDeferredDestroyFailure.Subscription);
            m_FallbackDeferredDestroyFailure = {};
            m_HasFallbackDeferredDestroyFailure = false;
        }
        auto deferredKeepEnd = std::remove_if(
            m_DeferredDestroyFailures.begin(), m_DeferredDestroyFailures.end(),
            [owner, &subscriptions, &firstFailure](const DeferredDestroyFailure& item) {
                if (item.Subscription.ExecutionOwner != owner)
                    return false;
                if (!firstFailure)
                    firstFailure = item.Failure;
                subscriptions.push_back(item.Subscription);
                return true;
            });
        m_DeferredDestroyFailures.erase(deferredKeepEnd, m_DeferredDestroyFailures.end());
        return subscriptions;
    }

    void ChatEventDispatcher::RetainFailedOwnerDestroySubscriptions(
        void* owner,
        const std::vector<ChatMessageSubscription>& subscriptions,
        std::exception_ptr unreportedFailure)
    {
        if (!owner || subscriptions.empty())
            return;

        for (const ChatMessageSubscription& subscription : subscriptions)
            RetainFailedOwnerDestroySubscriptionNoThrow(owner, subscription, unreportedFailure);
    }

    void ChatEventDispatcher::RetainFailedOwnerDestroySubscriptionNoThrow(
        void* owner,
        const ChatMessageSubscription& subscription,
        std::exception_ptr unreportedFailure)
    {
        if (!owner)
            return;

        try
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
            m_FailedOwnerDestroy.push_back({owner, subscription, unreportedFailure});
        }
        catch (...)
        {
            try
            {
                std::lock_guard<std::mutex> lock(m_Mutex);
                if (!m_HasFallbackFailedOwnerDestroy)
                {
                    m_FallbackFailedOwnerDestroy = {owner, subscription, unreportedFailure};
                    m_HasFallbackFailedOwnerDestroy = true;
                    return;
                }
            }
            catch (...)
            {
            }

            {
                std::lock_guard<std::mutex> lock(m_Mutex);
                m_CleanupRetentionFailed = true;
            }

            if (Obelisk::Logger::IsInitialized())
            {
                try
                {
                    OBELISK_ERROR(
                        "Chat deferred owner DestroyUserData failure storage failed while fallback was occupied.");
                }
                catch (...)
                {
                }
            }
        }
    }

    std::vector<ChatMessageSubscription> ChatEventDispatcher::TakeDeferredDestroyFailures(
        uint64_t cleanupBatchId,
        std::exception_ptr& firstFailure)
    {
        std::vector<ChatMessageSubscription> failedSubscriptions;
        if (cleanupBatchId == 0)
            return failedSubscriptions;

        const size_t fallbackCount =
            m_HasFallbackDeferredDestroyFailure &&
                    m_FallbackDeferredDestroyFailure.CleanupBatchId == cleanupBatchId
                ? 1
                : 0;
        const size_t matchingCount = static_cast<size_t>(
            std::count_if(m_DeferredDestroyFailures.begin(),
                          m_DeferredDestroyFailures.end(),
                          [cleanupBatchId](const DeferredDestroyFailure& failure) {
                              return failure.CleanupBatchId == cleanupBatchId;
                          }));
        failedSubscriptions.reserve(fallbackCount + matchingCount);
        if (m_HasFallbackDeferredDestroyFailure &&
            m_FallbackDeferredDestroyFailure.CleanupBatchId == cleanupBatchId)
        {
            if (!firstFailure)
                firstFailure = m_FallbackDeferredDestroyFailure.Failure;
            failedSubscriptions.push_back(m_FallbackDeferredDestroyFailure.Subscription);
            m_HasFallbackDeferredDestroyFailure = false;
            m_FallbackDeferredDestroyFailure = {};
        }

        auto keepEnd = std::remove_if(
            m_DeferredDestroyFailures.begin(),
            m_DeferredDestroyFailures.end(),
            [cleanupBatchId, &firstFailure, &failedSubscriptions](const DeferredDestroyFailure& failure) {
                if (failure.CleanupBatchId != cleanupBatchId)
                    return false;
                if (!firstFailure)
                    firstFailure = failure.Failure;
                failedSubscriptions.push_back(failure.Subscription);
                return true;
            });
        m_DeferredDestroyFailures.erase(keepEnd, m_DeferredDestroyFailures.end());

        return failedSubscriptions;
    }

    void ChatEventDispatcher::ReserveDeferredDestroyFailureSlots(size_t count)
    {
        if (count == 0)
            return;

        m_DeferredDestroyFailures.reserve(
            m_DeferredDestroyFailures.size() + m_ReservedDeferredDestroyFailureSlots + count);
        m_ReservedDeferredDestroyFailureSlots += count;
    }

    void ChatEventDispatcher::ReleaseDeferredDestroyFailureSlots(size_t count)
    {
        m_ReservedDeferredDestroyFailureSlots =
            count >= m_ReservedDeferredDestroyFailureSlots
                ? 0
                : m_ReservedDeferredDestroyFailureSlots - count;
    }

    void ChatEventDispatcher::RecordDeferredDestroyFailure(
        uint64_t cleanupBatchId,
        const ChatMessageSubscription& subscription,
        std::exception_ptr failure)
    {
        if (cleanupBatchId == 0)
            return;

        if (m_ReservedDeferredDestroyFailureSlots > 0)
            --m_ReservedDeferredDestroyFailureSlots;

        try
        {
#ifdef OBELISK_CHAT_EVENT_DISPATCHER_ENABLE_TEST_HOOKS
            if (m_FailNextDeferredDestroyFailureRecordForTesting)
            {
                m_FailNextDeferredDestroyFailureRecordForTesting = false;
                throw std::bad_alloc();
            }
#endif
            m_DeferredDestroyFailures.push_back({cleanupBatchId, subscription, failure});
            return;
        }
        catch (...)
        {
            if (!m_HasFallbackDeferredDestroyFailure)
            {
                m_FallbackDeferredDestroyFailure = {
                    cleanupBatchId,
                    subscription,
                    failure,
                };
                m_HasFallbackDeferredDestroyFailure = true;
                return;
            }

            m_CleanupRetentionFailed = true;

            if (Obelisk::Logger::IsInitialized())
            {
                OBELISK_ERROR(
                    "Chat deferred DestroyUserData failure storage failed while fallback was occupied.");
            }
        }
    }

    bool ChatEventDispatcher::IsDispatchCleanupComplete() const
    {
        return m_DispatchDepth == 0 && m_PendingDestroy.empty() && m_PendingDestroyInProgress == 0;
    }

    std::vector<ChatMessageSubscription> ChatEventDispatcher::DestroyRemovedSubscriptionsForOwner(
        void* owner, const std::vector<ChatMessageSubscription>& subscriptions,
        std::exception_ptr& firstFailure, size_t additionalCapacity)
    {
        try
        {
            return DestroySubscriptionsForOwnerCleanup(subscriptions, firstFailure, additionalCapacity);
        }
        catch (...)
        {
            // Only preparation can throw out of the per-deleter collector. Keep
            // the untouched userdata reachable for retry, or poison retention
            // if neither ordinary nor fallback record storage can retain it.
            RetainFailedOwnerDestroySubscriptions(owner, subscriptions, std::current_exception());
            throw;
        }
    }

    OwnerExecutionGate::Binding ChatEventDispatcher::CaptureCleanupBinding(void* owner, uint64_t registrationId) const
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        for (const auto& item : m_Registrations)
            if ((!owner || item.Owner == owner) && (!registrationId || item.Id == registrationId))
                return item.Subscription.ExecutionBinding;
        if (registrationId != 0)
            return {};
        for (const auto& item : m_PendingDestroy)
            if (item.Owner == owner)
                return item.Subscription.ExecutionBinding;
        for (const auto& item : m_FailedOwnerDestroy)
            if (item.Owner == owner)
                return item.Subscription.ExecutionBinding;
        if (m_HasFallbackFailedOwnerDestroy && m_FallbackFailedOwnerDestroy.Owner == owner)
            return m_FallbackFailedOwnerDestroy.Subscription.ExecutionBinding;
        for (const auto& item : m_DeferredDestroyFailures)
            if (item.Subscription.ExecutionOwner == owner)
                return item.Subscription.ExecutionBinding;
        if (m_HasFallbackDeferredDestroyFailure &&
            m_FallbackDeferredDestroyFailure.Subscription.ExecutionOwner == owner)
            return m_FallbackDeferredDestroyFailure.Subscription.ExecutionBinding;
        return {};
    }

    void ChatEventDispatcher::RequireCleanupRetentionIntact() const
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        if (m_CleanupRetentionFailed)
            throw std::runtime_error("Dispatcher cleanup retention failed; keep plugin mapped");
    }

    void ChatEventDispatcher::FinishDispatch()
    {
        std::vector<PendingDestroy> pending;
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
            auto cleanupLease = OwnerExecutionGate::EnterLifecycle(
                item.Subscription.ExecutionBinding, OwnerExecutionGate::LifecycleEntry::Cleanup);
            try
            {
                DestroySubscriptionUserData(item.Subscription, true);
                if (item.CleanupBatchId != 0)
                {
                    std::lock_guard<std::mutex> lock(m_Mutex);
                    ReleaseDeferredDestroyFailureSlots(1);
                }
            }
            catch (...)
            {
                if (item.CleanupBatchId == 0)
                {
                    RetainFailedOwnerDestroySubscriptionNoThrow(
                        item.Owner,
                        item.Subscription,
                        std::current_exception());
                    continue;
                }

                std::lock_guard<std::mutex> lock(m_Mutex);
                RecordDeferredDestroyFailure(
                    item.CleanupBatchId,
                    item.Subscription,
                    std::current_exception());
            }
        }
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
            m_PendingDestroyInProgress -= pending.size();
        }
        m_DispatchCv.notify_all();
    }

    size_t ChatEventDispatcher::Dispatch(const ChatMessageView& message)
    {
        if (static_cast<uint32_t>(message.SendMode) > static_cast<uint32_t>(ChatSendMode::Alliance))
            return 0;

        size_t dispatched = 0;
        try
        {
            if (m_SubscriptionCount.load(std::memory_order_acquire) == 0)
                return 0;

            std::string messageCopy(message.Message);
            std::string senderNameCopy(message.SenderName);
            std::string senderPlatformIdCopy(message.SenderPlatformId);

            ChatMessageView copiedMessage{
                .Message = messageCopy,
                .SenderName = senderNameCopy,
                .SenderPlatformId = senderPlatformIdCopy,
                .SendMode = message.SendMode,
                .SenderNameIndex = message.SenderNameIndex,
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
                        callbacks.push_back({item.Id, item.Generation, item.Subscription});
                }

                for (const DispatchRegistration& item : callbacks)
                {
                    if (!IsRegistrationActive(item.Id, item.Generation))
                        continue;
                    if (!item.Subscription.Callback)
                        continue;

                    auto executionLease = OwnerExecutionGate::EnterCallback(
                        item.Subscription.ExecutionBinding);
                    if (!executionLease)
                        continue;

                    try
                    {
                        GameplayCallbackScope callbackScope(GameplayCallbackFamily::Chat);
                        item.Subscription.Callback(copiedMessage, item.Subscription.UserData);
                        ++dispatched;
                    }
                    catch (const std::exception& e)
                    {
                        if (Obelisk::Logger::IsInitialized())
                            OBELISK_ERROR("Chat message callback threw: {}", e.what());
                    }
                    catch (...)
                    {
                        if (Obelisk::Logger::IsInitialized())
                            OBELISK_ERROR("Chat message callback threw an unknown exception.");
                    }
                }
            }
            catch (const std::exception& e)
            {
                FinishDispatch();
                if (Obelisk::Logger::IsInitialized())
                    OBELISK_ERROR("Chat message dispatch failed internally: {}", e.what());
                return dispatched;
            }
            catch (...)
            {
                FinishDispatch();
                if (Obelisk::Logger::IsInitialized())
                    OBELISK_ERROR("Chat message dispatch failed internally with an unknown exception.");
                return dispatched;
            }

            FinishDispatch();
            return dispatched;
        }
        catch (const std::exception& e)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Chat message dispatch setup failed: {}", e.what());
            return 0;
        }
        catch (...)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Chat message dispatch setup failed with an unknown exception.");
            return 0;
        }
    }

    size_t ChatEventDispatcher::SubscriptionCount() const
    {
        return m_SubscriptionCount.load(std::memory_order_acquire);
    }
}
