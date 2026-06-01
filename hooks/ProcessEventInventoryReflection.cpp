#include "ProcessEventInventoryReflection.h"

#include <cstdint>
#include <cstring>
#include <iterator>
#include <span>
#include <string_view>
#include <utility>

namespace Obelisk::Hooks::ProcessEventInventoryReflection
{
    Gate EvaluateGate(const char* enableInventoryReflection,
                      bool observerDebugProfileEnabled,
                      bool observerDebugWindowEnabled,
                      bool instanceMarkerEnabled,
                      const char* binarySha256)
    {
        if (!enableInventoryReflection || std::strcmp(enableInventoryReflection, "1") != 0)
            return {};

        if (!observerDebugProfileEnabled)
            return {GateStatus::MissingObserverDebugProfile, {}};

        if (!observerDebugWindowEnabled)
            return {GateStatus::MissingObserverDebugWindow, {}};

        if (!instanceMarkerEnabled)
            return {GateStatus::MissingInstanceMarker, {}};

        if (!binarySha256 || binarySha256[0] == '\0')
            return {GateStatus::MissingBinarySha256, {}};

        if (std::string_view(binarySha256) != Obelisk::UE::RuntimeReflection::kSupportedShooterGameServerSha256)
            return {GateStatus::UnsupportedBinarySha256, binarySha256};

        return {GateStatus::Enabled, binarySha256};
    }

    bool IsReflectedInventoryNameIndex(int32_t nameIndex)
    {
        return nameIndex == 6236 || nameIndex == 6252;
    }

    bool ShouldAttemptObservation(uint64_t limit)
    {
        return limit != 0;
    }

    bool ShouldAttemptRuntimeObservation(uint64_t logLimit, uint64_t dispatchLimit)
    {
        return ShouldAttemptObservation(logLimit) || ShouldAttemptObservation(dispatchLimit);
    }

    bool ShouldAttemptRuntimeObservation(const std::atomic<uint64_t>& logCounter,
                                         uint64_t logLimit,
                                         const std::atomic<uint64_t>& dispatchCounter,
                                         uint64_t dispatchLimit)
    {
        return HasObservationBudgetRemaining(logCounter, logLimit) ||
               HasObservationBudgetRemaining(dispatchCounter, dispatchLimit);
    }

    bool ShouldAttemptDispatchObservation(const std::atomic<uint64_t>& dispatchCounter,
                                          uint64_t dispatchLimit,
                                          size_t subscriptionCount)
    {
        return subscriptionCount != 0 &&
               HasObservationBudgetRemaining(dispatchCounter, dispatchLimit);
    }

    bool ShouldAttemptNameObservation(int32_t nameIndex, uint64_t limit)
    {
        return ShouldAttemptObservation(limit) && IsReflectedInventoryNameIndex(nameIndex);
    }

    bool ShouldAttemptNameObservation(int32_t nameIndex, uint64_t logLimit, uint64_t dispatchLimit)
    {
        return ShouldAttemptRuntimeObservation(logLimit, dispatchLimit) &&
               IsReflectedInventoryNameIndex(nameIndex);
    }

    bool ShouldLogObservation(uint64_t observationNumber, uint64_t limit)
    {
        return ShouldAttemptObservation(limit) && observationNumber != 0 && observationNumber <= limit;
    }

    bool HasObservationBudgetRemaining(const std::atomic<uint64_t>& counter, uint64_t limit)
    {
        return ShouldAttemptObservation(limit) && counter.load() < limit;
    }

    bool TryReserveObservationBudget(std::atomic<uint64_t>& counter, uint64_t limit, uint64_t& observationNumber)
    {
        if (!ShouldAttemptObservation(limit))
        {
            observationNumber = 0;
            return false;
        }
        uint64_t current = counter.load();
        while (current < limit)
        {
            if (counter.compare_exchange_weak(current, current + 1))
            {
                observationNumber = current + 1;
                return true;
            }
        }
        observationNumber = 0;
        return false;
    }

    bool TryReserveDispatchBudgetForMatchedAttempt(const Attempt& attempt,
                                                   std::atomic<uint64_t>& counter,
                                                   uint64_t limit,
                                                   uint64_t& observationNumber)
    {
        CopiedInventoryPolicyEvent event;
        return TryBuildAndReserveDispatchBudgetForMatchedAttempt(
            attempt, counter, limit, observationNumber, event);
    }

    bool TryBuildAndReserveDispatchBudgetForMatchedAttempt(const Attempt& attempt,
                                                           std::atomic<uint64_t>& counter,
                                                           uint64_t limit,
                                                           uint64_t& observationNumber,
                                                           CopiedInventoryPolicyEvent& out)
    {
        if (attempt.Status != AttemptStatus::Matched)
        {
            observationNumber = 0;
            out = {};
            return false;
        }

        if (Obelisk::Core::InventoryPolicyEventDispatcher::Get().SubscriptionCount() == 0 ||
            !HasObservationBudgetRemaining(counter, limit))
        {
            observationNumber = 0;
            out = {};
            return false;
        }

        if (!TryBuildCopiedInventoryPolicyEvent(attempt.Invocation, out))
        {
            observationNumber = 0;
            return false;
        }

        if (!TryReserveObservationBudget(counter, limit, observationNumber))
        {
            out = {};
            return false;
        }
        return true;
    }

    namespace
    {
        constexpr int32_t kAllowRemoteAddToInventoryNameIndex = 6236;
        constexpr int32_t kCanUseNameIndex = 6252;
        constexpr int32_t kPrimalItemNameIndex = 6231;
        constexpr int32_t kInvCompNameIndex = 18798;
        constexpr int32_t kByPCNameIndex = 18797;
        constexpr int32_t kBRequestedByPlayerNameIndex = 18796;
        constexpr int32_t kReturnValueNameIndex = 17716;
        constexpr int32_t kBIgnoreCooldownNameIndex = 18814;
        constexpr int32_t kBoolPropertyClassNameIndex = 3;
        constexpr int32_t kObjectPropertyClassNameIndex = 5;
        constexpr int32_t kBoolPropertyClassObjectIndex = 532;
        constexpr int32_t kObjectPropertyClassObjectIndex = 534;
        constexpr uint64_t kBoolInputPropertyFlags = 0x1040000280;
        constexpr uint64_t kBoolReturnPropertyFlags = 0x1040000780;
        constexpr uint64_t kRemoteAddInventoryComponentPropertyFlags = 0x1044080280;
        constexpr uint64_t kObjectInputPropertyFlags = 0x1040000280;

        struct ExpectedPolicyField
        {
            Obelisk::UE::InventoryReflection::InventoryField SourceField;
            int32_t PropertyNameIndex;
            int32_t PropertyClassNameIndex;
            int32_t PropertyClassObjectIndex;
            uint64_t PropertyFlags;
            int32_t Offset;
            size_t Size;
            bool ExposesRange;
            Obelisk::Core::InventoryPolicyScalarField TargetField;
        };

        struct ExpectedPolicyShape
        {
            Obelisk::Core::InventoryPolicyEventKind Kind = Obelisk::Core::InventoryPolicyEventKind::CanUse;
            const ExpectedPolicyField* Fields = nullptr;
            size_t FieldCount = 0;
            size_t ScalarCount = 0;
        };

        bool TryGetDispatchShape(Obelisk::UE::InventoryReflection::InventoryFunction function,
                                 int32_t functionNameIndex,
                                 int32_t outerNameIndex,
                                 ExpectedPolicyShape& out)
        {
            using Obelisk::Core::InventoryPolicyEventKind;
            using Obelisk::Core::InventoryPolicyScalarField;
            using Obelisk::UE::InventoryReflection::InventoryFunction;
            using Obelisk::UE::InventoryReflection::InventoryField;
            static constexpr ExpectedPolicyField kAllowRemoteAddFields[] = {
                {InventoryField::InventoryComponent,
                 kInvCompNameIndex,
                 kObjectPropertyClassNameIndex,
                 kObjectPropertyClassObjectIndex,
                 kRemoteAddInventoryComponentPropertyFlags,
                 0x00,
                 sizeof(uint64_t),
                 false,
                 InventoryPolicyScalarField::BRequestedByPlayer},
                {InventoryField::ByPC,
                 kByPCNameIndex,
                 kObjectPropertyClassNameIndex,
                 kObjectPropertyClassObjectIndex,
                 kObjectInputPropertyFlags,
                 0x08,
                 sizeof(uint64_t),
                 false,
                 InventoryPolicyScalarField::BRequestedByPlayer},
                {InventoryField::BRequestedByPlayer,
                 kBRequestedByPlayerNameIndex,
                 kBoolPropertyClassNameIndex,
                 kBoolPropertyClassObjectIndex,
                 kBoolInputPropertyFlags,
                 0x10,
                 sizeof(uint8_t),
                 true,
                 InventoryPolicyScalarField::BRequestedByPlayer},
                {InventoryField::ReturnValue,
                 kReturnValueNameIndex,
                 kBoolPropertyClassNameIndex,
                 kBoolPropertyClassObjectIndex,
                 kBoolReturnPropertyFlags,
                 0x11,
                 sizeof(uint8_t),
                 true,
                 InventoryPolicyScalarField::ReturnValue},
            };
            static constexpr ExpectedPolicyField kCanUseFields[] = {
                {InventoryField::BIgnoreCooldown,
                 kBIgnoreCooldownNameIndex,
                 kBoolPropertyClassNameIndex,
                 kBoolPropertyClassObjectIndex,
                 kBoolInputPropertyFlags,
                 0x00,
                 sizeof(uint8_t),
                 true,
                 InventoryPolicyScalarField::BIgnoreCooldown},
                {InventoryField::ReturnValue,
                 kReturnValueNameIndex,
                 kBoolPropertyClassNameIndex,
                 kBoolPropertyClassObjectIndex,
                 kBoolReturnPropertyFlags,
                 0x01,
                 sizeof(uint8_t),
                 true,
                 InventoryPolicyScalarField::ReturnValue},
            };

            out = {};
            switch (function)
            {
            case InventoryFunction::AllowRemoteAddToInventory:
                if (functionNameIndex != kAllowRemoteAddToInventoryNameIndex ||
                    outerNameIndex != kPrimalItemNameIndex)
                {
                    return false;
                }
                out.Kind = InventoryPolicyEventKind::AllowRemoteAddToInventory;
                out.Fields = kAllowRemoteAddFields;
                out.FieldCount = std::size(kAllowRemoteAddFields);
                out.ScalarCount = 2;
                return true;
            case InventoryFunction::CanUse:
                if (functionNameIndex != kCanUseNameIndex ||
                    outerNameIndex != kPrimalItemNameIndex)
                {
                    return false;
                }
                out.Kind = InventoryPolicyEventKind::CanUse;
                out.Fields = kCanUseFields;
                out.FieldCount = std::size(kCanUseFields);
                out.ScalarCount = 2;
                return true;
            case InventoryFunction::ServerRequestInventoryUseItem:
            case InventoryFunction::ServerRequestInventoryUseItemWithActor:
                return false;
            }
            return false;
        }

        bool TryGetScalarField(Obelisk::UE::InventoryReflection::InventoryField source,
                               Obelisk::Core::InventoryPolicyScalarField& out)
        {
            using Obelisk::Core::InventoryPolicyScalarField;
            using Obelisk::UE::InventoryReflection::InventoryField;
            switch (source)
            {
            case InventoryField::BRequestedByPlayer:
                out = InventoryPolicyScalarField::BRequestedByPlayer;
                return true;
            case InventoryField::BIgnoreCooldown:
                out = InventoryPolicyScalarField::BIgnoreCooldown;
                return true;
            case InventoryField::ReturnValue:
                out = InventoryPolicyScalarField::ReturnValue;
                return true;
            case InventoryField::Actor:
            case InventoryField::RedactedItemId:
            case InventoryField::RedactedItemId1:
            case InventoryField::AdditionalData:
            case InventoryField::InventoryComponent:
            case InventoryField::ByPC:
                return false;
            }
            return false;
        }

        bool TryCopyScalar(const Obelisk::UE::InventoryReflection::InventoryFieldRange& field,
                           const ExpectedPolicyField& expected,
                           Obelisk::Core::InventoryPolicyScalarValue& out)
        {
            Obelisk::Core::InventoryPolicyScalarField scalarField;
            if (!TryGetScalarField(field.Field, scalarField))
                return false;
            if (field.Field != expected.SourceField ||
                field.PropertyNameIndex != expected.PropertyNameIndex ||
                field.PropertyClassNameIndex != expected.PropertyClassNameIndex ||
                field.PropertyClassObjectIndex != expected.PropertyClassObjectIndex ||
                field.PropertyFlags != expected.PropertyFlags ||
                field.Offset != expected.Offset ||
                field.Size != expected.Size ||
                scalarField != expected.TargetField)
            {
                return false;
            }
            if (!field.ExposesRange ||
                !field.Range.Data ||
                field.Range.Size != expected.Size ||
                field.Size != sizeof(uint8_t) ||
                !expected.ExposesRange)
            {
                return false;
            }

            uint8_t value = 0;
            std::memcpy(&value, field.Range.Data, sizeof(value));
            if (value > 1)
            {
                out = {};
                return false;
            }
            out.Field = scalarField;
            out.BoolValue = value != 0;
            return true;
        }

        bool MatchesExpectedParamRange(
            const Obelisk::UE::InventoryReflection::InventoryInvocation& invocation,
            const Obelisk::UE::InventoryReflection::InventoryFieldRange& field,
            const ExpectedPolicyField& expected)
        {
            if (!invocation.HasParameterRanges ||
                !invocation.ParamData ||
                expected.Offset < 0 ||
                expected.Size > invocation.ParamSize)
            {
                return false;
            }

            const size_t offset = static_cast<size_t>(expected.Offset);
            if (offset > invocation.ParamSize ||
                expected.Size > invocation.ParamSize - offset)
            {
                return false;
            }

            return field.Range.Data == invocation.ParamData + offset &&
                   field.Range.Size == expected.Size;
        }
    }

    Attempt TryIdentifyInvocation(const Gate& gate,
                                  int32_t nameIndex,
                                  const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                  void* function,
                                  void* params)
    {
        if (!gate.Enabled())
            return {};

        if (!IsReflectedInventoryNameIndex(nameIndex))
        {
            return {
                AttemptStatus::NonInventoryFunction,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                {},
            };
        }

        Obelisk::UE::RuntimeReflection::ReadOptions options =
            Obelisk::UE::RuntimeReflection::MakeReadOptionsForBinary(gate.BinarySha256, true);

        Obelisk::UE::InventoryReflection::InventoryInvocation invocation;
        Obelisk::UE::RuntimeReflection::ReadResult result;
        try
        {
            result = Obelisk::UE::InventoryReflection::TryIdentifyInventoryInvocation(
                reader, options, function, params, invocation);
        }
        catch (...)
        {
            return {
                AttemptStatus::Rejected,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                {},
            };
        }
        if (!result)
            return {AttemptStatus::Rejected, std::move(result), {}};
        if (invocation.FunctionNameIndex != nameIndex)
        {
            return {
                AttemptStatus::Rejected,
                Obelisk::UE::RuntimeReflection::ReadResult::Fail(
                    Obelisk::UE::RuntimeReflection::ReadStatus::Implausible,
                    "inventory prefilter FName does not match reflected UFunction FName"),
                {},
            };
        }

        return {AttemptStatus::Matched, std::move(result), std::move(invocation)};
    }

    bool TryBuildCopiedInventoryPolicyEvent(
        const Obelisk::UE::InventoryReflection::InventoryInvocation& invocation,
        CopiedInventoryPolicyEvent& out)
    {
        out = {};
        ExpectedPolicyShape expected;
        if (!TryGetDispatchShape(invocation.Function,
                                 invocation.FunctionNameIndex,
                                 invocation.OuterNameIndex,
                                 expected))
        {
            return false;
        }
        if (!invocation.HasParameterRanges)
            return false;

        if (!expected.Fields || invocation.Fields.size() != expected.FieldCount)
            return false;

        out.View.Kind = expected.Kind;

        for (size_t fieldIndex = 0; fieldIndex < invocation.Fields.size(); ++fieldIndex)
        {
            const Obelisk::UE::InventoryReflection::InventoryFieldRange& field = invocation.Fields[fieldIndex];
            const ExpectedPolicyField& expectedField = expected.Fields[fieldIndex];
            if (field.Field != expectedField.SourceField ||
                field.PropertyNameIndex != expectedField.PropertyNameIndex ||
                field.PropertyClassNameIndex != expectedField.PropertyClassNameIndex ||
                field.PropertyClassObjectIndex != expectedField.PropertyClassObjectIndex ||
                field.PropertyFlags != expectedField.PropertyFlags ||
                field.Offset != expectedField.Offset ||
                field.Size != expectedField.Size ||
                field.ExposesRange != expectedField.ExposesRange)
            {
                out = {};
                return false;
            }

            if (!expectedField.ExposesRange)
            {
                if (field.Range.Data || field.Range.Size != 0)
                {
                    out = {};
                    return false;
                }
                continue;
            }

            Obelisk::Core::InventoryPolicyScalarValue scalar;
            if (out.ScalarCount >= out.ScalarStorage.size() ||
                !MatchesExpectedParamRange(invocation, field, expectedField) ||
                !TryCopyScalar(field, expectedField, scalar))
            {
                out = {};
                return false;
            }
            out.ScalarStorage[out.ScalarCount++] = scalar;
        }

        out.View.Scalars = std::span<const Obelisk::Core::InventoryPolicyScalarValue>(
            out.ScalarStorage.data(), out.ScalarCount);
        if (out.ScalarCount != expected.ScalarCount)
        {
            out = {};
            return false;
        }
        return true;
    }

    namespace
    {
        bool HasExpectedCopiedScalarShape(const CopiedInventoryPolicyEvent& event)
        {
            using Obelisk::Core::InventoryPolicyEventKind;
            using Obelisk::Core::InventoryPolicyScalarField;

            const std::span<const Obelisk::Core::InventoryPolicyScalarValue> scalars =
                event.View.Scalars;
            switch (event.View.Kind)
            {
            case InventoryPolicyEventKind::AllowRemoteAddToInventory:
                return scalars.size() == 2 &&
                       scalars[0].Field == InventoryPolicyScalarField::BRequestedByPlayer &&
                       scalars[1].Field == InventoryPolicyScalarField::ReturnValue;
            case InventoryPolicyEventKind::CanUse:
                return scalars.size() == 2 &&
                       scalars[0].Field == InventoryPolicyScalarField::BIgnoreCooldown &&
                       scalars[1].Field == InventoryPolicyScalarField::ReturnValue;
            }
            return false;
        }

        bool IsSelfContainedCopiedEvent(const CopiedInventoryPolicyEvent& event)
        {
            if (event.ScalarCount > event.ScalarStorage.size())
                return false;
            if (event.View.Scalars.size() != event.ScalarCount)
                return false;
            if (event.ScalarCount == 0)
                return false;
            return event.View.Scalars.data() == event.ScalarStorage.data() &&
                   HasExpectedCopiedScalarShape(event);
        }

        size_t DispatchCopiedInventoryPolicyEvent(const CopiedInventoryPolicyEvent& event)
        {
            if (!IsSelfContainedCopiedEvent(event))
                return 0;

            return Obelisk::Core::InventoryPolicyEventDispatcher::Get().Dispatch(event.View);
        }
    }

    size_t MaybeDispatchCopiedInventoryPolicyEventAfterOriginal(
        bool originalWasCalled,
        const Obelisk::UE::InventoryReflection::InventoryInvocation& invocation)
    {
        if (!originalWasCalled)
            return 0;

        CopiedInventoryPolicyEvent event;
        if (!TryBuildCopiedInventoryPolicyEvent(invocation, event))
            return 0;

        return DispatchCopiedInventoryPolicyEvent(event);
    }

    size_t MaybeDispatchCopiedInventoryPolicyEventAfterOriginal(
        bool originalWasCalled,
        const CopiedInventoryPolicyEvent& event)
    {
        if (!originalWasCalled)
            return 0;

        return DispatchCopiedInventoryPolicyEvent(event);
    }
}
