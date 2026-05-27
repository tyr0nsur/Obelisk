#pragma once

#include <cstdint>
#include <cstddef>
#include <mutex>
#include <string_view>
#include <vector>

namespace Obelisk::Core
{
    enum class ChatSendMode : uint32_t
    {
        Global = 0,
        Tribe = 1,
        Local = 2,
        Alliance = 3,
    };

    struct ChatMessageView
    {
        std::string_view Message;
        std::string_view SenderName;
        std::string_view SenderPlatformId;
        ChatSendMode SendMode = ChatSendMode::Global;
        int32_t SenderNameIndex = -1;
    };

    using ChatMessageCallback = void (*)(const ChatMessageView& message, void* userData);

    struct ChatMessageSubscription
    {
        ChatMessageCallback Callback = nullptr;
        void* UserData = nullptr;
    };

    class ChatEventDispatcher
    {
    public:
        static ChatEventDispatcher& Get();

        uint64_t Register(void* owner, const ChatMessageSubscription& subscription);
        bool Unregister(uint64_t registrationId);
        size_t UnregisterCallbacksForOwner(void* owner);

        size_t Dispatch(const ChatMessageView& message);
        size_t SubscriptionCount() const;

    private:
        struct Registration
        {
            uint64_t Id = 0;
            void* Owner = nullptr;
            ChatMessageSubscription Subscription;
        };

        mutable std::mutex m_Mutex;
        std::recursive_mutex m_DispatchMutex;
        uint64_t m_NextRegistrationId = 1;
        std::vector<Registration> m_Registrations;
    };
}
