#pragma once

#include <atomic>
#include <cstdint>
#include <cstddef>
#include <condition_variable>
#include <exception>
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
        void (*DestroyUserData)(void*) = nullptr;
    };

    class ChatEventDispatcher
    {
    public:
        static ChatEventDispatcher& Get();

        uint64_t Register(void* owner, const ChatMessageSubscription& subscription);
        bool Unregister(uint64_t registrationId);
        size_t UnregisterCallbacksForOwner(void* owner);
#ifdef OBELISK_CHAT_EVENT_DISPATCHER_ENABLE_TEST_HOOKS
        void SetNextRegistrationIdForTesting(uint64_t nextRegistrationId);
#endif

        size_t Dispatch(const ChatMessageView& message);
        size_t SubscriptionCount() const;

    private:
        struct Registration
        {
            uint64_t Id = 0;
            uint64_t Generation = 0;
            void* Owner = nullptr;
            ChatMessageSubscription Subscription;
        };

        struct PendingDestroy
        {
            ChatMessageSubscription Subscription;
            uint64_t CleanupBatchId = 0;
        };

        struct DeferredDestroyFailure
        {
            uint64_t CleanupBatchId = 0;
            std::exception_ptr Failure;
        };

        uint64_t AllocateRegistrationId();
        bool HasRegistrationId(uint64_t registrationId) const;
        bool IsRegistrationActive(uint64_t registrationId, uint64_t generation) const;
        bool QueueOrDestroyRemovedSubscriptions(
            std::vector<ChatMessageSubscription>& removed,
            std::unique_lock<std::mutex>& lock,
            uint64_t cleanupBatchId = 0);
        bool IsDispatchCleanupComplete() const;
        std::exception_ptr TakeDeferredDestroyFailure(uint64_t cleanupBatchId);
        void FinishDispatch();

        mutable std::mutex m_Mutex;
        std::condition_variable m_DispatchCv;
        size_t m_DispatchDepth = 0;
        uint64_t m_NextRegistrationId = 1;
        uint64_t m_NextGeneration = 1;
        std::vector<Registration> m_Registrations;
        std::atomic<size_t> m_SubscriptionCount{0};
        std::vector<PendingDestroy> m_PendingDestroy;
        std::vector<DeferredDestroyFailure> m_DeferredDestroyFailures;
        size_t m_PendingDestroyInProgress = 0;
        uint64_t m_NextCleanupBatchId = 1;
    };
}
