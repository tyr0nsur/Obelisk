#include "ChatEventDispatcher.h"
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
            ChatMessageSubscription Subscription;
        };

        void DestroySubscriptionUserData(const ChatMessageSubscription& subscription)
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
                    OBELISK_ERROR("Chat message subscription cleanup threw: {}", e.what());
            }
            catch (...)
            {
                if (Obelisk::Logger::IsInitialized())
                    OBELISK_ERROR("Chat message subscription cleanup threw an unknown exception.");
            }
        }
    }

    ChatEventDispatcher& ChatEventDispatcher::Get()
    {
        static ChatEventDispatcher dispatcher;
        return dispatcher;
    }

    uint64_t ChatEventDispatcher::Register(void* owner, const ChatMessageSubscription& subscription)
    {
        if (!owner || !subscription.Callback)
            return 0;

        std::lock_guard<std::mutex> lock(m_Mutex);
        const uint64_t id = AllocateRegistrationId();
        m_Registrations.push_back({id, owner, subscription});
        return id;
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

    bool ChatEventDispatcher::Unregister(uint64_t registrationId)
    {
        if (registrationId == 0)
            return false;

        std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
        std::lock_guard<std::mutex> lock(m_Mutex);
        const auto before = m_Registrations.size();
        std::vector<ChatMessageSubscription> removed;
        m_Registrations.erase(
            std::remove_if(m_Registrations.begin(),
                           m_Registrations.end(),
                           [registrationId, &removed](const Registration& item) {
                               if (item.Id != registrationId)
                                   return false;
                               removed.push_back(item.Subscription);
                               return true;
                           }),
            m_Registrations.end());
        for (const ChatMessageSubscription& subscription : removed)
            DestroySubscriptionUserData(subscription);
        return m_Registrations.size() != before;
    }

    size_t ChatEventDispatcher::UnregisterCallbacksForOwner(void* owner)
    {
        if (!owner)
            return 0;

        std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
        std::lock_guard<std::mutex> lock(m_Mutex);
        const auto before = m_Registrations.size();
        std::vector<ChatMessageSubscription> removed;
        m_Registrations.erase(
            std::remove_if(m_Registrations.begin(),
                           m_Registrations.end(),
                           [owner, &removed](const Registration& item) {
                               if (item.Owner != owner)
                                   return false;
                               removed.push_back(item.Subscription);
                               return true;
                           }),
            m_Registrations.end());
        for (const ChatMessageSubscription& subscription : removed)
            DestroySubscriptionUserData(subscription);
        return before - m_Registrations.size();
    }

    void ChatEventDispatcher::SetNextRegistrationIdForTesting(uint64_t nextRegistrationId)
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        m_NextRegistrationId = nextRegistrationId == 0 ? 1 : nextRegistrationId;
    }

    size_t ChatEventDispatcher::Dispatch(const ChatMessageView& message)
    {
        if (static_cast<uint32_t>(message.SendMode) > static_cast<uint32_t>(ChatSendMode::Alliance))
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
        std::lock_guard<std::recursive_mutex> dispatchLock(m_DispatchMutex);
        {
            std::lock_guard<std::mutex> lock(m_Mutex);
            callbacks.reserve(m_Registrations.size());
            for (const Registration& item : m_Registrations)
                callbacks.push_back({item.Subscription});
        }

        size_t dispatched = 0;
        for (const DispatchRegistration& item : callbacks)
        {
            if (!item.Subscription.Callback)
                continue;

            try
            {
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

        return dispatched;
    }

    size_t ChatEventDispatcher::SubscriptionCount() const
    {
        std::lock_guard<std::mutex> lock(m_Mutex);
        return m_Registrations.size();
    }
}
