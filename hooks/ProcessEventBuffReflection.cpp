#include "ProcessEventBuffReflection.h"

#include <array>
#include <cstdint>
#include <cstring>
#include <string_view>
#include <utility>

namespace Obelisk::Hooks::ProcessEventBuffReflection
{
    Gate EvaluateGate(const char* enableBuffReflection,
                      bool observerDebugProfileEnabled,
                      bool observerDebugWindowEnabled,
                      bool instanceMarkerEnabled,
                      const char* binarySha256)
    {
        if (!enableBuffReflection || std::strcmp(enableBuffReflection, "1") != 0)
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

    bool IsReflectedBuffNameIndex(int32_t nameIndex)
    {
        return nameIndex == 1073 ||
            nameIndex == 1129 ||
            nameIndex == 1236 ||
            nameIndex == 1288 ||
            nameIndex == 1690 ||
            nameIndex == 1814;
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
            IsReflectedBuffNameIndex(nameIndex);
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
        constexpr int32_t kAllowPostProcessEffectNameIndex = 1073;
        constexpr int32_t kBPOnBuffLifetimeUpdatedNameIndex = 1129;
        constexpr int32_t kBPBuffPreventUploadingNameIndex = 1236;
        constexpr int32_t kBPCustomAllowAddBuffNameIndex = 1288;
        constexpr int32_t kBPPreventAddingOtherBuffNameIndex = 1690;
        constexpr int32_t kBuffOverrideInventoryAccessInputNameIndex = 1814;
        constexpr int32_t kPrimalBuffNameIndex = 7843;

        constexpr int32_t kBoolPropertyClassNameIndex = 3;
        constexpr int32_t kObjectPropertyClassNameIndex = 5;
        constexpr int32_t kClassPropertyClassNameIndex = 8;
        constexpr int32_t kBoolPropertyClassObjectIndex = 532;
        constexpr int32_t kObjectPropertyClassObjectIndex = 534;
        constexpr int32_t kClassPropertyClassObjectIndex = 535;

        constexpr int32_t kReturnValueNameIndex = 17716;
        constexpr int32_t kForCharacterNameIndex = 17726;
        constexpr int32_t kDamageCauserNameIndex = 19001;
        constexpr int32_t kAnotherBuffClassNameIndex = 24180;
        constexpr int32_t kBInputPressedNameIndex = 24188;
        constexpr int32_t kInControllerNameIndex = 24189;

        constexpr uint64_t kObjectInputPropertyFlags = 0x1040000280;
        constexpr uint64_t kBoolInputPropertyFlags = 0x1040000280;
        constexpr uint64_t kBoolReturnPropertyFlags = 0x1040000780;

        struct ExpectedBuffField
        {
            Obelisk::UE::BuffReflection::BuffField Field;
            int32_t PropertyNameIndex = -1;
            int32_t PropertyClassNameIndex = -1;
            int32_t PropertyClassObjectIndex = -1;
            uint64_t PropertyFlags = 0;
            int32_t Offset = -1;
            size_t Size = 0;
            bool ExposesRange = false;
        };

        struct ExpectedBuffObservation
        {
            Obelisk::UE::BuffReflection::BuffFunction Function =
                Obelisk::UE::BuffReflection::BuffFunction::AllowPostProcessEffect;
            int32_t FunctionNameIndex = -1;
            int32_t OuterNameIndex = -1;
            const ExpectedBuffField* Fields = nullptr;
            size_t FieldCount = 0;
            size_t BoolCount = 0;
        };

        constexpr std::array<ExpectedBuffField, 1> kBoolReturnFields{{
            {Obelisk::UE::BuffReflection::BuffField::ReturnValue,
             kReturnValueNameIndex,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolReturnPropertyFlags,
             0x00,
             sizeof(uint8_t),
             true},
        }};

        constexpr std::array<ExpectedBuffField, 0> kNoFields{};

        constexpr std::array<ExpectedBuffField, 3> kBuffOverrideInventoryAccessInputFields{{
            {Obelisk::UE::BuffReflection::BuffField::InController,
             kInControllerNameIndex,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags,
             0x00,
             sizeof(uint64_t),
             false},
            {Obelisk::UE::BuffReflection::BuffField::BInputPressed,
             kBInputPressedNameIndex,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolInputPropertyFlags,
             0x08,
             sizeof(uint8_t),
             true},
            {Obelisk::UE::BuffReflection::BuffField::ReturnValue,
             kReturnValueNameIndex,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolReturnPropertyFlags,
             0x09,
             sizeof(uint8_t),
             true},
        }};

        constexpr std::array<ExpectedBuffField, 3> kBPCustomAllowAddBuffFields{{
            {Obelisk::UE::BuffReflection::BuffField::ForCharacter,
             kForCharacterNameIndex,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags,
             0x00,
             sizeof(uint64_t),
             false},
            {Obelisk::UE::BuffReflection::BuffField::DamageCauser,
             kDamageCauserNameIndex,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags,
             0x08,
             sizeof(uint64_t),
             false},
            {Obelisk::UE::BuffReflection::BuffField::ReturnValue,
             kReturnValueNameIndex,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolReturnPropertyFlags,
             0x10,
             sizeof(uint8_t),
             true},
        }};

        constexpr std::array<ExpectedBuffField, 2> kBPPreventAddingOtherBuffFields{{
            {Obelisk::UE::BuffReflection::BuffField::AnotherBuffClass,
             kAnotherBuffClassNameIndex,
             kClassPropertyClassNameIndex,
             kClassPropertyClassObjectIndex,
             kObjectInputPropertyFlags,
             0x00,
             sizeof(uint64_t),
             false},
            {Obelisk::UE::BuffReflection::BuffField::ReturnValue,
             kReturnValueNameIndex,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolReturnPropertyFlags,
             0x08,
             sizeof(uint8_t),
             true},
        }};

        constexpr std::array<ExpectedBuffObservation, 6> kExpectedBuffObservations{{
            {Obelisk::UE::BuffReflection::BuffFunction::AllowPostProcessEffect,
             kAllowPostProcessEffectNameIndex,
             kPrimalBuffNameIndex,
             kBoolReturnFields.data(),
             kBoolReturnFields.size(),
             1},
            {Obelisk::UE::BuffReflection::BuffFunction::BPBuffPreventUploading,
             kBPBuffPreventUploadingNameIndex,
             kPrimalBuffNameIndex,
             kBoolReturnFields.data(),
             kBoolReturnFields.size(),
             1},
            {Obelisk::UE::BuffReflection::BuffFunction::BPOnBuffLifetimeUpdated,
             kBPOnBuffLifetimeUpdatedNameIndex,
             kPrimalBuffNameIndex,
             kNoFields.data(),
             kNoFields.size(),
             0},
            {Obelisk::UE::BuffReflection::BuffFunction::BuffOverrideInventoryAccessInput,
             kBuffOverrideInventoryAccessInputNameIndex,
             kPrimalBuffNameIndex,
             kBuffOverrideInventoryAccessInputFields.data(),
             kBuffOverrideInventoryAccessInputFields.size(),
             2},
            {Obelisk::UE::BuffReflection::BuffFunction::BPCustomAllowAddBuff,
             kBPCustomAllowAddBuffNameIndex,
             kPrimalBuffNameIndex,
             kBPCustomAllowAddBuffFields.data(),
             kBPCustomAllowAddBuffFields.size(),
             1},
            {Obelisk::UE::BuffReflection::BuffFunction::BPPreventAddingOtherBuff,
             kBPPreventAddingOtherBuffNameIndex,
             kPrimalBuffNameIndex,
             kBPPreventAddingOtherBuffFields.data(),
             kBPPreventAddingOtherBuffFields.size(),
             1},
        }};

        const ExpectedBuffObservation* FindExpectedObservation(
            Obelisk::UE::BuffReflection::BuffFunction function,
            int32_t functionNameIndex,
            int32_t outerNameIndex)
        {
            for (const ExpectedBuffObservation& expected : kExpectedBuffObservations)
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

        bool MatchesExpectedField(const Obelisk::UE::BuffReflection::BuffFieldRange& field,
                                  const ExpectedBuffField& expected)
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

        bool IsCopiedBoolField(Obelisk::UE::BuffReflection::BuffField field)
        {
            return field == Obelisk::UE::BuffReflection::BuffField::ReturnValue ||
                field == Obelisk::UE::BuffReflection::BuffField::BInputPressed;
        }

        bool TryCopyBool(const Obelisk::UE::BuffReflection::BuffFieldRange& field,
                         BuffBoolObservation& out)
        {
            if (!IsCopiedBoolField(field.Field))
                return false;
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

        bool IsRangeInsideCopiedParams(const Obelisk::UE::BuffReflection::BuffInvocation& invocation,
                                       const Obelisk::UE::BuffReflection::BuffFieldRange& field)
        {
            if (!invocation.HasParameterRanges || !invocation.ParameterData || !field.Range.Data)
                return false;
            if (field.Offset < 0)
                return false;

            const auto offset = static_cast<size_t>(field.Offset);
            if (offset > invocation.ParameterSize ||
                field.Range.Size > invocation.ParameterSize - offset)
            {
                return false;
            }

            const auto paramBegin = reinterpret_cast<uintptr_t>(invocation.ParameterData);
            const auto rangeBegin = reinterpret_cast<uintptr_t>(field.Range.Data);
            return rangeBegin >= paramBegin && rangeBegin - paramBegin == offset;
        }
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

        if (!IsReflectedBuffNameIndex(nameIndex))
        {
            return {
                AttemptStatus::NonBuffFunction,
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

        Obelisk::UE::RuntimeReflection::ReadOptions options =
            Obelisk::UE::RuntimeReflection::MakeReadOptionsForBinary(gate.BinarySha256, true);

        Obelisk::UE::BuffReflection::BuffInvocation invocation;
        Obelisk::UE::RuntimeReflection::ReadResult result;
        try
        {
            result = Obelisk::UE::BuffReflection::TryIdentifyBuffInvocation(
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
                    "buff prefilter FName does not match reflected UFunction FName"),
                {},
            };
        }

        return {AttemptStatus::Matched, std::move(result), std::move(invocation)};
    }

    bool TryBuildCopiedBuffObservation(const Obelisk::UE::BuffReflection::BuffInvocation& invocation,
                                       CopiedBuffObservation& out)
    {
        out = {};
        const ExpectedBuffObservation* expected = FindExpectedObservation(
            invocation.Function, invocation.FunctionNameIndex, invocation.OuterNameIndex);
        if (!expected)
            return false;

        if (expected->BoolCount != 0 && !invocation.HasParameterRanges)
            return false;
        if (invocation.Fields.size() != expected->FieldCount)
            return false;

        out.Function = invocation.Function;
        out.FunctionNameIndex = invocation.FunctionNameIndex;
        out.OuterNameIndex = invocation.OuterNameIndex;

        for (size_t fieldIndex = 0; fieldIndex < invocation.Fields.size(); ++fieldIndex)
        {
            const Obelisk::UE::BuffReflection::BuffFieldRange& field = invocation.Fields[fieldIndex];
            const ExpectedBuffField& expectedField = expected->Fields[fieldIndex];
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

            if (!IsRangeInsideCopiedParams(invocation, field))
            {
                out = {};
                return false;
            }

            BuffBoolObservation copiedBool;
            if (!TryCopyBool(field, copiedBool))
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

    bool TryBuildCopiedBuffObservationForMatchedAttempt(const Attempt& attempt,
                                                        CopiedBuffObservation& out)
    {
        out = {};
        if (attempt.Status != AttemptStatus::Matched)
            return false;

        return TryBuildCopiedBuffObservation(attempt.Invocation, out);
    }
}
