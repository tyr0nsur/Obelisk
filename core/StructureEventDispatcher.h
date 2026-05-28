#pragma once

#include <cstddef>
#include <cstdint>
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
    };

    class StructureEventDispatcher
    {
    public:
        static StructureEventDispatcher& Get();

        uint64_t Register(void* owner, const StructureEventSubscription& subscription);
        bool Unregister(uint64_t registrationId);
        size_t UnregisterCallbacksForOwner(void* owner);
        void SetNextRegistrationIdForTesting(uint64_t nextRegistrationId);

        size_t Dispatch(const StructureEventView& event);
        size_t SubscriptionCount() const;

    private:
        struct Registration
        {
            uint64_t Id = 0;
            void* Owner = nullptr;
            StructureEventSubscription Subscription;
        };

        uint64_t AllocateRegistrationId();
        bool HasRegistrationId(uint64_t registrationId) const;

        mutable std::mutex m_Mutex;
        std::recursive_mutex m_DispatchMutex;
        uint64_t m_NextRegistrationId = 1;
        std::vector<Registration> m_Registrations;
    };
}
