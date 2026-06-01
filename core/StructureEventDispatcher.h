#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <condition_variable>
#include <exception>
#include <mutex>
#include <span>
#include <vector>

namespace Obelisk::Core
{
    enum class StructureEventKind : uint32_t
    {
        AllowStructureAccess = 0,
        IsAllowedToDemolish = 1,
        SetVariant = 2,
        AllowToggleActivation = 3,
        VerifyPinCode = 4,
        CanSeat = 5,
    };

    enum class StructureScalarField : uint32_t
    {
        VariantIndex = 0,
        BForceSet = 1,
        BForce = 2,
        ReturnValue = 3,
    };

    enum class StructureScalarType : uint32_t
    {
        Bool = 0,
        Int32 = 1,
    };

    struct StructureScalarValue
    {
        StructureScalarField Field = StructureScalarField::ReturnValue;
        StructureScalarType Type = StructureScalarType::Bool;
        bool BoolValue = false;
        int32_t Int32Value = 0;
    };

    struct StructureEventView
    {
        StructureEventKind Kind = StructureEventKind::VerifyPinCode;
        int32_t FunctionNameIndex = -1;
        int32_t OuterNameIndex = -1;
        std::span<const StructureScalarValue> Scalars;
    };

    using StructureEventCallback = void (*)(const StructureEventView& event, void* userData);

    struct StructureEventSubscription
    {
        StructureEventCallback Callback = nullptr;
        void* UserData = nullptr;
        void (*DestroyUserData)(void*) = nullptr;
    };

    class StructureEventDispatcher
    {
    public:
        static StructureEventDispatcher& Get();

        uint64_t Register(void* owner, const StructureEventSubscription& subscription);
        bool Unregister(uint64_t registrationId);
        bool UnregisterCallbackForOwner(void* owner, uint64_t registrationId);
        size_t UnregisterCallbacksForOwner(void* owner);
#ifdef OBELISK_STRUCTURE_EVENT_DISPATCHER_ENABLE_TEST_HOOKS
        void SetNextRegistrationIdForTesting(uint64_t nextRegistrationId);
#endif

        size_t Dispatch(const StructureEventView& event);
        size_t SubscriptionCount() const;

    private:
        struct Registration
        {
            uint64_t Id = 0;
            uint64_t Generation = 0;
            void* Owner = nullptr;
            StructureEventSubscription Subscription;
        };

        struct PendingDestroy
        {
            StructureEventSubscription Subscription;
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
            std::vector<StructureEventSubscription>& removed,
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
