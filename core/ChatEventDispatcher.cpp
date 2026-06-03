#if !defined(obelisk_EXPORTS)
#define OBELISK_CHAT_EVENT_DISPATCHER_ENABLE_TEST_HOOKS
#endif

#include "ChatEventDispatcher.h"
#include "GameplayCallbackScope.h"
#include "runtime/Logger.h"

#include <algorithm>
#include <exception>
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
            std::exception_ptr& firstFailure)
        {
            std::vector<ChatMessageSubscription> failed;
            for (const ChatMessageSubscription& subscription : subscriptions)
            {
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
        for (const ChatMessageSubscription& subscription : removed)
            DestroySubscriptionUserData(subscription);
        if (deferredFailure)
            std::rethrow_exception(deferredFailure);
        return after != before;
    }

    size_t ChatEventDispatcher::UnregisterCallbacksForOwner(void* owner)
    {
        if (!owner)
            return 0;

        std::vector<ChatMessageSubscription> removed;
        std::exception_ptr deferredFailure;
        std::vector<ChatMessageSubscription> deferredFailures;
        size_t retainedCount = 0;
        size_t before = 0;
        size_t after = 0;
        try
        {
            std::unique_lock<std::mutex> lock(m_Mutex);
            removed = TakeFailedOwnerDestroySubscriptions(owner);
            retainedCount = removed.size();
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
                    m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
                }
                return 0;
            }
            removed.reserve(retainedCount + matchingCount);
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
            uint64_t cleanupBatchId = 0;
            if (!IsInsideAnyGameplayCallback() && !IsInsideDispatcherCleanup())
            {
                cleanupBatchId = m_NextCleanupBatchId++;
                if (m_NextCleanupBatchId == 0)
                    m_NextCleanupBatchId = 1;
            }
            std::vector<ChatMessageSubscription> currentRemoved(
                removed.begin() + static_cast<std::ptrdiff_t>(retainedCount),
                removed.end());
            const bool queuedForDeferredDestroy = m_DispatchDepth > 0 && !currentRemoved.empty();
            if (QueueOrDestroyRemovedSubscriptions(currentRemoved, lock, cleanupBatchId))
            {
                m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
                deferredFailures = TakeDeferredDestroyFailures(cleanupBatchId, deferredFailure);
            }
            if (queuedForDeferredDestroy)
                removed.erase(removed.begin() + static_cast<std::ptrdiff_t>(retainedCount), removed.end());
            else if (!IsInsideAnyGameplayCallback() &&
                     !IsInsideDispatcherCleanup() &&
                     !IsDispatchCleanupComplete())
                m_DispatchCv.wait(lock, [this]() { return IsDispatchCleanupComplete(); });
        }
        catch (const std::exception& e)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Chat event owner cleanup failed: {}", e.what());
            throw;
        }
        catch (...)
        {
            if (Obelisk::Logger::IsInitialized())
                OBELISK_ERROR("Chat event owner cleanup failed with an unknown exception.");
            throw;
        }
        std::exception_ptr cleanupFailure;
        std::vector<ChatMessageSubscription> failed =
            DestroySubscriptionsForOwnerCleanup(removed, cleanupFailure);
        if (deferredFailure)
        {
            cleanupFailure = cleanupFailure ? cleanupFailure : deferredFailure;
            failed.insert(failed.end(), deferredFailures.begin(), deferredFailures.end());
        }
        if (!failed.empty())
            RetainFailedOwnerDestroySubscriptions(owner, failed);
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
#endif

    bool ChatEventDispatcher::QueueOrDestroyRemovedSubscriptions(
        std::vector<ChatMessageSubscription>& removed,
        std::unique_lock<std::mutex>&,
        uint64_t cleanupBatchId)
    {
        if (removed.empty())
            return false;

        if (m_DispatchDepth > 0)
        {
            for (const ChatMessageSubscription& subscription : removed)
                m_PendingDestroy.push_back({subscription, cleanupBatchId});
            removed.clear();
            return !IsInsideAnyGameplayCallback();
        }

        return false;
    }

    std::vector<ChatMessageSubscription> ChatEventDispatcher::TakeFailedOwnerDestroySubscriptions(void* owner)
    {
        std::vector<ChatMessageSubscription> subscriptions;
        auto keepEnd = std::remove_if(
            m_FailedOwnerDestroy.begin(),
            m_FailedOwnerDestroy.end(),
            [owner, &subscriptions](const FailedOwnerDestroy& item) {
                if (item.Owner != owner)
                    return false;
                subscriptions.push_back(item.Subscription);
                return true;
            });
        m_FailedOwnerDestroy.erase(keepEnd, m_FailedOwnerDestroy.end());
        return subscriptions;
    }

    void ChatEventDispatcher::RetainFailedOwnerDestroySubscriptions(
        void* owner,
        const std::vector<ChatMessageSubscription>& subscriptions)
    {
        if (!owner || subscriptions.empty())
            return;

        std::lock_guard<std::mutex> lock(m_Mutex);
        m_FailedOwnerDestroy.reserve(m_FailedOwnerDestroy.size() + subscriptions.size());
        for (const ChatMessageSubscription& subscription : subscriptions)
            m_FailedOwnerDestroy.push_back({owner, subscription});
    }

    std::vector<ChatMessageSubscription> ChatEventDispatcher::TakeDeferredDestroyFailures(
        uint64_t cleanupBatchId,
        std::exception_ptr& firstFailure)
    {
        std::vector<ChatMessageSubscription> failedSubscriptions;
        if (cleanupBatchId == 0)
            return failedSubscriptions;

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

    bool ChatEventDispatcher::IsDispatchCleanupComplete() const
    {
        return m_DispatchDepth == 0 && m_PendingDestroy.empty() && m_PendingDestroyInProgress == 0;
    }

    void ChatEventDispatcher::FinishDispatch()
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
                try
                {
                    failures.push_back({item.CleanupBatchId, item.Subscription, std::current_exception()});
                }
                catch (...)
                {
                }
            }
        }
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
            m_PendingDestroyInProgress -= pending.size();
            try
            {
                m_DeferredDestroyFailures.insert(
                    m_DeferredDestroyFailures.end(),
                    failures.begin(),
                    failures.end());
            }
            catch (...)
            {
            }
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
