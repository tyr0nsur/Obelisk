#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <condition_variable>
#include <mutex>
#include <span>
#include <vector>

namespace Obelisk::Core
{
    enum class MissionCopiedBoolEventKind : uint32_t
    {
        AddPlayerToMission = 0,
        BPAllowPlayerToLeaveMission = 1,
        BPOnPlayerRemovedFromMission = 2,
    };

    enum class MissionCopiedBoolField : uint32_t
    {
        BForceAdd = 0,
        BFromMissionCompleteEvent = 1,
        BLastPhaseSuccess = 2,
        ReturnValue = 3,
    };

    struct MissionCopiedBoolValue
    {
        MissionCopiedBoolField Field = MissionCopiedBoolField::ReturnValue;
        bool Value = false;
    };

    struct MissionCopiedBoolEventView
    {
        MissionCopiedBoolEventKind Kind = MissionCopiedBoolEventKind::AddPlayerToMission;
        std::span<const MissionCopiedBoolValue> Bools;
    };

    using MissionCopiedBoolEventCallback = void (*)(const MissionCopiedBoolEventView& event, void* userData);

    struct MissionCopiedBoolEventSubscription
    {
        MissionCopiedBoolEventCallback Callback = nullptr;
        void* UserData = nullptr;
        void (*DestroyUserData)(void*) = nullptr;
    };

    class MissionCopiedBoolEventDispatcher
    {
    public:
        static MissionCopiedBoolEventDispatcher& Get();

        uint64_t Register(void* owner, const MissionCopiedBoolEventSubscription& subscription);
        bool Unregister(uint64_t registrationId);
        bool UnregisterCallbackForOwner(void* owner, uint64_t registrationId);
        size_t UnregisterCallbacksForOwner(void* owner);
#ifdef OBELISK_MISSION_COPIED_BOOL_EVENT_DISPATCHER_ENABLE_TEST_HOOKS
        void SetNextRegistrationIdForTesting(uint64_t nextRegistrationId);
#endif

        size_t Dispatch(const MissionCopiedBoolEventView& event);
        size_t SubscriptionCount() const;

    private:
        struct Registration
        {
            uint64_t Id = 0;
            uint64_t Generation = 0;
            void* Owner = nullptr;
            MissionCopiedBoolEventSubscription Subscription;
        };

        uint64_t AllocateRegistrationId();
        bool HasRegistrationId(uint64_t registrationId) const;
        bool IsRegistrationActive(uint64_t registrationId, uint64_t generation) const;
        bool QueueOrDestroyRemovedSubscriptions(
            std::vector<MissionCopiedBoolEventSubscription>& removed,
            std::unique_lock<std::mutex>& lock);
        bool IsDispatchCleanupComplete() const;
        void FinishDispatch();

        mutable std::mutex m_Mutex;
        std::condition_variable m_DispatchCv;
        size_t m_DispatchDepth = 0;
        uint64_t m_NextRegistrationId = 1;
        uint64_t m_NextGeneration = 1;
        std::vector<Registration> m_Registrations;
        std::atomic<size_t> m_SubscriptionCount{0};
        std::vector<MissionCopiedBoolEventSubscription> m_PendingDestroy;
        size_t m_PendingDestroyInProgress = 0;
    };
}
