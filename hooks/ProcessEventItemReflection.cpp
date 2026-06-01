#include "ProcessEventItemReflection.h"

#include <array>
#include <cstdint>
#include <cstring>
#include <string_view>
#include <utility>

namespace Obelisk::Hooks::ProcessEventItemReflection
{
    Gate EvaluateGate(const char* enableItemReflection,
                      bool observerDebugProfileEnabled,
                      bool observerDebugWindowEnabled,
                      bool instanceMarkerEnabled,
                      const char* binarySha256)
    {
        if (!enableItemReflection || std::strcmp(enableItemReflection, "1") != 0)
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

    bool IsReflectedItemNameIndex(int32_t nameIndex)
    {
        return nameIndex == 6235 ||
            nameIndex == 6250 ||
            nameIndex == 6257 ||
            nameIndex == 6346;
    }

    bool IsReflectedItemReturnNameIndex(int32_t nameIndex)
    {
        return nameIndex == 6235 ||
            nameIndex == 6250 ||
            nameIndex == 6346;
    }

    bool ShouldAttemptObservation(uint64_t observationLimit)
    {
        return observationLimit != 0;
    }

    bool ShouldAttemptRuntimeObservation(uint64_t observationLimit)
    {
        return ShouldAttemptObservation(observationLimit);
    }

    bool ShouldAttemptRuntimeObservation(const std::atomic<uint64_t>& observationCounter,
                                         uint64_t observationLimit)
    {
        return HasObservationBudgetRemaining(observationCounter, observationLimit);
    }

    bool ShouldAttemptNameObservation(int32_t nameIndex, uint64_t observationLimit)
    {
        return ShouldAttemptRuntimeObservation(observationLimit) &&
            IsReflectedItemNameIndex(nameIndex);
    }

    bool ShouldLogObservation(uint64_t observationNumber, uint64_t observationLimit)
    {
        return ShouldAttemptObservation(observationLimit) &&
            observationNumber != 0 &&
            observationNumber <= observationLimit;
    }

    bool HasObservationBudgetRemaining(const std::atomic<uint64_t>& counter, uint64_t observationLimit)
    {
        return ShouldAttemptObservation(observationLimit) && counter.load() < observationLimit;
    }

    bool TryReserveObservationBudget(std::atomic<uint64_t>& counter,
                                     uint64_t observationLimit,
                                     uint64_t& observationNumber)
    {
        if (!ShouldAttemptObservation(observationLimit))
        {
            observationNumber = 0;
            return false;
        }

        uint64_t current = counter.load();
        while (current < observationLimit)
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

    namespace
    {
        constexpr int32_t kAllowEquipItemNameIndex = 6235;
        constexpr int32_t kCanRepairNameIndex = 6250;
        constexpr int32_t kCraftBlueprintNameIndex = 6257;
        constexpr int32_t kUseItemOntoItemNameIndex = 6346;
        constexpr int32_t kPrimalItemNameIndex = 6231;
        constexpr int32_t kReturnValueNameIndex = 17716;
        constexpr int32_t kBIgnoreInventoryRequirementNameIndex = 18617;
        constexpr int32_t kToInventoryNameIndex = 18795;
        constexpr int32_t kDestinationItemNameIndex = 19285;
        constexpr int32_t kAdditionalDataNameIndex = 19290;
        constexpr int32_t kBConsumeResourcesNameIndex = 19293;
        constexpr int32_t kIntPropertyClassNameIndex = 2;
        constexpr int32_t kBoolPropertyClassNameIndex = 3;
        constexpr int32_t kObjectPropertyClassNameIndex = 5;
        constexpr int32_t kBoolPropertyClassObjectIndex = 532;
        constexpr int32_t kObjectPropertyClassObjectIndex = 534;
        constexpr int32_t kIntPropertyClassObjectIndex = 539;
        constexpr uint64_t kBoolInputPropertyFlags = 0x1040000280;
        constexpr uint64_t kBoolReturnPropertyFlags = 0x1040000780;
        constexpr uint64_t kToInventoryPropertyFlags = 0x1044080280;
        constexpr uint64_t kObjectInputPropertyFlags = 0x1040000280;
        constexpr uint64_t kIntInputPropertyFlags = 0x1040000280;

        struct ExpectedItemField
        {
            Obelisk::UE::ItemReflection::ItemField Field;
            int32_t PropertyNameIndex = -1;
            int32_t PropertyClassNameIndex = -1;
            int32_t PropertyClassObjectIndex = -1;
            uint64_t PropertyFlags = 0;
            int32_t Offset = -1;
            size_t Size = 0;
            bool ExposesRange = false;
        };

        struct ExpectedItemObservation
        {
            Obelisk::UE::ItemReflection::ItemFunction Function;
            int32_t FunctionNameIndex = -1;
            int32_t OuterNameIndex = -1;
            const ExpectedItemField* Fields = nullptr;
            size_t FieldCount = 0;
            size_t BoolCount = 0;
            size_t ParamSize = 0;
        };

        constexpr std::array<ExpectedItemField, 2> kAllowEquipItemFields{{
            {Obelisk::UE::ItemReflection::ItemField::ToInventory,
             kToInventoryNameIndex,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kToInventoryPropertyFlags,
             0x00,
             0x08,
             false},
            {Obelisk::UE::ItemReflection::ItemField::ReturnValue,
             kReturnValueNameIndex,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolReturnPropertyFlags,
             0x08,
             0x01,
             true},
        }};

        constexpr std::array<ExpectedItemField, 2> kCanRepairFields{{
            {Obelisk::UE::ItemReflection::ItemField::BIgnoreInventoryRequirement,
             kBIgnoreInventoryRequirementNameIndex,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolInputPropertyFlags,
             0x00,
             0x01,
             true},
            {Obelisk::UE::ItemReflection::ItemField::ReturnValue,
             kReturnValueNameIndex,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolReturnPropertyFlags,
             0x01,
             0x01,
             true},
        }};

        constexpr std::array<ExpectedItemField, 3> kUseItemOntoItemFields{{
            {Obelisk::UE::ItemReflection::ItemField::DestinationItem,
             kDestinationItemNameIndex,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags,
             0x00,
             0x08,
             false},
            {Obelisk::UE::ItemReflection::ItemField::AdditionalData,
             kAdditionalDataNameIndex,
             kIntPropertyClassNameIndex,
             kIntPropertyClassObjectIndex,
             kIntInputPropertyFlags,
             0x08,
             0x04,
             false},
            {Obelisk::UE::ItemReflection::ItemField::ReturnValue,
             kReturnValueNameIndex,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolReturnPropertyFlags,
             0x0c,
             0x01,
             true},
        }};

        constexpr ExpectedItemObservation kExpectedItemObservations[]{
            {Obelisk::UE::ItemReflection::ItemFunction::AllowEquipItem,
             kAllowEquipItemNameIndex,
             kPrimalItemNameIndex,
             kAllowEquipItemFields.data(),
             kAllowEquipItemFields.size(),
             1,
             0x09},
            {Obelisk::UE::ItemReflection::ItemFunction::CanRepair,
             kCanRepairNameIndex,
             kPrimalItemNameIndex,
             kCanRepairFields.data(),
             kCanRepairFields.size(),
             1,
             0x02},
            {Obelisk::UE::ItemReflection::ItemFunction::UseItemOntoItem,
             kUseItemOntoItemNameIndex,
             kPrimalItemNameIndex,
             kUseItemOntoItemFields.data(),
             kUseItemOntoItemFields.size(),
             1,
             0x0d},
        };

        const ExpectedItemObservation* FindExpectedObservation(
            Obelisk::UE::ItemReflection::ItemFunction function,
            int32_t functionNameIndex,
            int32_t outerNameIndex)
        {
            for (const ExpectedItemObservation& expected : kExpectedItemObservations)
            {
                if (expected.Function == function &&
                    expected.FunctionNameIndex == functionNameIndex &&
                    expected.OuterNameIndex == outerNameIndex)
                {
                    return &expected;
                }
            }
            return nullptr;
        }

        bool MatchesExpectedField(const Obelisk::UE::ItemReflection::ItemFieldRange& field,
                                  const ExpectedItemField& expected)
        {
            return field.Field == expected.Field &&
                field.PropertyNameIndex == expected.PropertyNameIndex &&
                field.PropertyClassNameIndex == expected.PropertyClassNameIndex &&
                field.PropertyClassObjectIndex == expected.PropertyClassObjectIndex &&
                field.PropertyFlags == expected.PropertyFlags &&
                field.Offset == expected.Offset &&
                field.Size == expected.Size &&
                field.ExposesRange == expected.ExposesRange;
        }

        bool TryCopyBool(const Obelisk::UE::ItemReflection::ItemFieldRange& field,
                         ItemBoolObservation& out)
        {
            using Obelisk::UE::ItemReflection::ItemField;
            switch (field.Field)
            {
            case ItemField::ReturnValue:
                break;
            case ItemField::BIgnoreInventoryRequirement:
            case ItemField::BConsumeResources:
            case ItemField::ToInventory:
            case ItemField::DestinationItem:
            case ItemField::AdditionalData:
                return false;
            }

            if (!field.ExposesRange ||
                !field.Range.Data ||
                field.Size != sizeof(uint8_t) ||
                field.Range.Size != sizeof(uint8_t))
            {
                return false;
            }

            uint8_t value = 0;
            std::memcpy(&value, field.Range.Data, sizeof(value));
            if (value > 1)
                return false;

            out.Field = field.Field;
            out.Value = value != 0;
            return true;
        }

        bool TryReadCanonicalBoolByte(const Obelisk::UE::ItemReflection::ItemFieldRange& field)
        {
            if (!field.Range.Data || field.Range.Size != sizeof(uint8_t))
                return false;

            uint8_t value = 0;
            std::memcpy(&value, field.Range.Data, sizeof(value));
            return value <= 1;
        }

        bool MatchesExpectedParamRange(
            const Obelisk::UE::ItemReflection::ItemInvocation& invocation,
            const Obelisk::UE::ItemReflection::ItemFieldRange& field,
            const ExpectedItemField& expected)
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

            const auto base = reinterpret_cast<uintptr_t>(invocation.ParamData);
            const auto actual = reinterpret_cast<uintptr_t>(field.Range.Data);
            return actual == base + offset &&
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

        if (!IsReflectedItemNameIndex(nameIndex))
        {
            return {
                AttemptStatus::NonItemFunction,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                {},
            };
        }

        Obelisk::UE::RuntimeReflection::ReadOptions options =
            Obelisk::UE::RuntimeReflection::MakeReadOptionsForBinary(gate.BinarySha256, true);

        Obelisk::UE::ItemReflection::ItemInvocation invocation;
        Obelisk::UE::RuntimeReflection::ReadResult result;
        try
        {
            result = Obelisk::UE::ItemReflection::TryIdentifyItemInvocation(
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
                    "item prefilter FName does not match reflected UFunction FName"),
                {},
            };
        }

        return {AttemptStatus::Matched, std::move(result), std::move(invocation)};
    }

    Attempt TryObserveInvocation(const Gate& gate,
                                 int32_t nameIndex,
                                 const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                 void* function,
                                 void* params,
                                 std::atomic<uint64_t>& observationCounter,
                                 uint64_t observationLimit,
                                 uint64_t& observationNumber)
    {
        observationNumber = 0;
        if (!gate.Enabled())
            return {};

        if (!IsReflectedItemNameIndex(nameIndex))
        {
            return {
                AttemptStatus::NonItemFunction,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                {},
            };
        }

        if (!TryReserveObservationBudget(observationCounter, observationLimit, observationNumber))
        {
            return {
                AttemptStatus::BudgetExhausted,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Disabled, {}},
                {},
            };
        }

        return TryIdentifyInvocation(gate, nameIndex, reader, function, params);
    }

    bool TryBuildCopiedItemObservation(const Obelisk::UE::ItemReflection::ItemInvocation& invocation,
                                       CopiedItemObservation& out)
    {
        out = {};
        const ExpectedItemObservation* expected = FindExpectedObservation(
            invocation.Function, invocation.FunctionNameIndex, invocation.OuterNameIndex);
        if (!expected)
            return false;

        if (expected->BoolCount != 0 && !invocation.HasParameterRanges)
            return false;
        if (expected->BoolCount != 0 && invocation.ParamSize != expected->ParamSize)
            return false;

        if (invocation.Fields.size() != expected->FieldCount)
            return false;

        out.Function = invocation.Function;
        out.FunctionNameIndex = invocation.FunctionNameIndex;
        out.OuterNameIndex = invocation.OuterNameIndex;

        for (size_t fieldIndex = 0; fieldIndex < invocation.Fields.size(); ++fieldIndex)
        {
            const Obelisk::UE::ItemReflection::ItemFieldRange& field = invocation.Fields[fieldIndex];
            const ExpectedItemField& expectedField = expected->Fields[fieldIndex];
            if (!MatchesExpectedField(field, expectedField))
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

            if (field.Field != Obelisk::UE::ItemReflection::ItemField::ReturnValue)
            {
                if (!TryReadCanonicalBoolByte(field))
                {
                    out = {};
                    return false;
                }
                continue;
            }

            ItemBoolObservation copiedBool;
            if (!MatchesExpectedParamRange(invocation, field, expectedField) ||
                !TryCopyBool(field, copiedBool))
            {
                out = {};
                return false;
            }
            if (out.BoolCount >= out.BoolStorage.size())
            {
                out = {};
                return false;
            }

            out.BoolStorage[out.BoolCount++] = copiedBool;
        }

        if (out.BoolCount != expected->BoolCount)
        {
            out = {};
            return false;
        }

        return true;
    }

    bool TryBuildCopiedItemReturnObservationForMatchedAttempt(const Attempt& attempt,
                                                              CopiedItemObservation& out)
    {
        out = {};
        if (attempt.Status != AttemptStatus::Matched)
            return false;

        return TryBuildCopiedItemObservation(attempt.Invocation, out);
    }

    bool TryBuildCopiedItemReturnObservationAfterOriginal(bool originalWasCalled,
                                                          const Attempt& attempt,
                                                          CopiedItemObservation& out)
    {
        out = {};
        if (!originalWasCalled)
            return false;

        return TryBuildCopiedItemReturnObservationForMatchedAttempt(attempt, out);
    }

    bool TryMapItemReturnEventKind(Obelisk::UE::ItemReflection::ItemFunction function,
                                   Obelisk::Core::ItemReturnEventKind& out)
    {
        using Obelisk::UE::ItemReflection::ItemFunction;
        switch (function)
        {
        case ItemFunction::AllowEquipItem:
            out = Obelisk::Core::ItemReturnEventKind::AllowEquipItem;
            return true;
        case ItemFunction::CanRepair:
            out = Obelisk::Core::ItemReturnEventKind::CanRepair;
            return true;
        case ItemFunction::UseItemOntoItem:
            out = Obelisk::Core::ItemReturnEventKind::UseItemOntoItem;
            return true;
        case ItemFunction::CraftBlueprint:
            return false;
        }
        return false;
    }

    bool TryBuildItemReturnEventView(const CopiedItemObservation& observation,
                                     std::array<Obelisk::Core::ItemReturnScalarValue, 1>& scalarStorage,
                                     Obelisk::Core::ItemReturnEventView& out)
    {
        Obelisk::Core::ItemReturnEventKind kind =
            Obelisk::Core::ItemReturnEventKind::AllowEquipItem;
        if (!TryMapItemReturnEventKind(observation.Function, kind))
            return false;
        if (observation.BoolCount != 1)
            return false;

        const ItemBoolObservation& returnValue = observation.BoolStorage[0];
        if (returnValue.Field != Obelisk::UE::ItemReflection::ItemField::ReturnValue)
            return false;

        scalarStorage[0] = {
            .Field = Obelisk::Core::ItemReturnScalarField::ReturnValue,
            .BoolValue = returnValue.Value,
        };
        out = {
            .Kind = kind,
            .Scalars = std::span<const Obelisk::Core::ItemReturnScalarValue>(
                scalarStorage.data(),
                1),
        };
        return true;
    }

    bool TryBuildAndReserveItemReturnObservationForMatchedAttempt(const Attempt& attempt,
                                                                  std::atomic<uint64_t>& counter,
                                                                  uint64_t observationLimit,
                                                                  uint64_t& observationNumber,
                                                                  CopiedItemObservation& out)
    {
        observationNumber = 0;
        out = {};
        if (!HasObservationBudgetRemaining(counter, observationLimit))
            return false;

        if (!TryBuildCopiedItemReturnObservationForMatchedAttempt(attempt, out))
            return false;

        if (!TryReserveObservationBudget(counter, observationLimit, observationNumber))
        {
            out = {};
            return false;
        }

        return true;
    }
}
