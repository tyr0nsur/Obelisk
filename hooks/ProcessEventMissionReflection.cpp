#include "ProcessEventMissionReflection.h"

#include <array>
#include <cstdint>
#include <cstring>
#include <string_view>
#include <utility>

namespace Obelisk::Hooks::ProcessEventMissionReflection
{
    Gate EvaluateGate(const char* enableMissionReflection,
                      bool observerDebugProfileEnabled,
                      bool observerDebugWindowEnabled,
                      bool instanceMarkerEnabled,
                      const char* binarySha256)
    {
        if (!enableMissionReflection || std::strcmp(enableMissionReflection, "1") != 0)
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

    bool IsReflectedMissionNameIndex(int32_t nameIndex)
    {
        return nameIndex == 7702 ||
               nameIndex == 7649 ||
               nameIndex == 1211 ||
               nameIndex == 1582;
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
               IsReflectedMissionNameIndex(nameIndex);
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
        constexpr int32_t kBPAllowPlayerToLeaveMissionNameIndex = 1211;
        constexpr int32_t kBPOnPlayerRemovedFromMissionNameIndex = 1582;
        constexpr int32_t kAddPlayerToMissionNameIndex = 7649;
        constexpr int32_t kMissionTypeNameIndex = 7646;
        constexpr int32_t kGetPlayerUsableItemsNameIndex = 7702;

        constexpr int32_t kControllerNameIndex = 5908;
        constexpr int32_t kCharacterNameIndex = 7990;
        constexpr int32_t kPlayerNameIndex = 9972;
        constexpr int32_t kReturnValueNameIndex = 17716;
        constexpr int32_t kPlayerPawnNameIndex = 21376;
        constexpr int32_t kBForceAddNameIndex = 22956;
        constexpr int32_t kPlayerCharacterNameIndex = 22961;
        constexpr int32_t kBLastPhaseSuccessNameIndex = 22976;
        constexpr int32_t kBFromMissionCompleteEventNameIndex = 22980;
        constexpr int32_t kOutItemIDsNameIndex = 23031;

        struct ExpectedMissionField
        {
            Obelisk::UE::MissionReflection::MissionField Field;
            int32_t PropertyNameIndex = -1;
            int32_t Offset = -1;
            size_t Size = 0;
            bool ExposesRange = false;
        };

        struct ExpectedMissionObservation
        {
            Obelisk::UE::MissionReflection::MissionFunction Function;
            int32_t FunctionNameIndex = -1;
            int32_t OuterNameIndex = -1;
            const ExpectedMissionField* Fields = nullptr;
            size_t FieldCount = 0;
            size_t BoolCount = 0;
        };

        constexpr std::array<ExpectedMissionField, 2> kGetPlayerUsableItemsFields{{
            {Obelisk::UE::MissionReflection::MissionField::Character,
             kCharacterNameIndex,
             0x00,
             0x08,
             false},
            {Obelisk::UE::MissionReflection::MissionField::OutItemIDs,
             kOutItemIDsNameIndex,
             0x08,
             0x10,
             false},
        }};

        constexpr std::array<ExpectedMissionField, 3> kAddPlayerToMissionFields{{
            {Obelisk::UE::MissionReflection::MissionField::PlayerCharacter,
             kPlayerCharacterNameIndex,
             0x00,
             0x08,
             false},
            {Obelisk::UE::MissionReflection::MissionField::BForceAdd,
             kBForceAddNameIndex,
             0x08,
             0x01,
             true},
            {Obelisk::UE::MissionReflection::MissionField::ReturnValue,
             kReturnValueNameIndex,
             0x09,
             0x01,
             true},
        }};

        constexpr std::array<ExpectedMissionField, 2> kBPAllowPlayerToLeaveMissionFields{{
            {Obelisk::UE::MissionReflection::MissionField::PlayerPawn,
             kPlayerPawnNameIndex,
             0x00,
             0x08,
             false},
            {Obelisk::UE::MissionReflection::MissionField::ReturnValue,
             kReturnValueNameIndex,
             0x08,
             0x01,
             true},
        }};

        constexpr std::array<ExpectedMissionField, 4> kBPOnPlayerRemovedFromMissionFields{{
            {Obelisk::UE::MissionReflection::MissionField::Player,
             kPlayerNameIndex,
             0x00,
             0x08,
             false},
            {Obelisk::UE::MissionReflection::MissionField::Controller,
             kControllerNameIndex,
             0x08,
             0x08,
             false},
            {Obelisk::UE::MissionReflection::MissionField::BFromMissionCompleteEvent,
             kBFromMissionCompleteEventNameIndex,
             0x10,
             0x01,
             true},
            {Obelisk::UE::MissionReflection::MissionField::BLastPhaseSuccess,
             kBLastPhaseSuccessNameIndex,
             0x11,
             0x01,
             true},
        }};

        constexpr ExpectedMissionObservation kExpectedMissionObservations[]{
            {Obelisk::UE::MissionReflection::MissionFunction::GetPlayerUsableItems,
             kGetPlayerUsableItemsNameIndex,
             kMissionTypeNameIndex,
             kGetPlayerUsableItemsFields.data(),
             kGetPlayerUsableItemsFields.size(),
             0},
            {Obelisk::UE::MissionReflection::MissionFunction::AddPlayerToMission,
             kAddPlayerToMissionNameIndex,
             kMissionTypeNameIndex,
             kAddPlayerToMissionFields.data(),
             kAddPlayerToMissionFields.size(),
             2},
            {Obelisk::UE::MissionReflection::MissionFunction::BPAllowPlayerToLeaveMission,
             kBPAllowPlayerToLeaveMissionNameIndex,
             kMissionTypeNameIndex,
             kBPAllowPlayerToLeaveMissionFields.data(),
             kBPAllowPlayerToLeaveMissionFields.size(),
             1},
            {Obelisk::UE::MissionReflection::MissionFunction::BPOnPlayerRemovedFromMission,
             kBPOnPlayerRemovedFromMissionNameIndex,
             kMissionTypeNameIndex,
             kBPOnPlayerRemovedFromMissionFields.data(),
             kBPOnPlayerRemovedFromMissionFields.size(),
             2},
        };

        const ExpectedMissionObservation* FindExpectedObservation(
            Obelisk::UE::MissionReflection::MissionFunction function,
            int32_t functionNameIndex,
            int32_t outerNameIndex)
        {
            for (const ExpectedMissionObservation& expected : kExpectedMissionObservations)
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

        bool MatchesExpectedField(const Obelisk::UE::MissionReflection::MissionFieldRange& field,
                                  const ExpectedMissionField& expected)
        {
            return field.Field == expected.Field &&
                   field.PropertyNameIndex == expected.PropertyNameIndex &&
                   field.Offset == expected.Offset &&
                   field.Size == expected.Size &&
                   field.ExposesRange == expected.ExposesRange;
        }

        bool TryCopyBool(const Obelisk::UE::MissionReflection::MissionFieldRange& field,
                         MissionBoolObservation& out)
        {
            using Obelisk::UE::MissionReflection::MissionField;
            switch (field.Field)
            {
            case MissionField::BForceAdd:
            case MissionField::BFromMissionCompleteEvent:
            case MissionField::BLastPhaseSuccess:
            case MissionField::ReturnValue:
                break;
            case MissionField::Character:
            case MissionField::OutItemIDs:
            case MissionField::PlayerCharacter:
            case MissionField::PlayerPawn:
            case MissionField::Player:
            case MissionField::Controller:
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
    }

    Attempt TryIdentifyInvocation(const Gate& gate,
                                  int32_t nameIndex,
                                  const Obelisk::UE::RuntimeReflection::MemoryReader& reader,
                                  void* function,
                                  void* params)
    {
        if (!gate.Enabled())
            return {};

        if (!IsReflectedMissionNameIndex(nameIndex))
        {
            return {
                AttemptStatus::NonMissionFunction,
                {Obelisk::UE::RuntimeReflection::ReadStatus::Implausible, {}},
                {},
            };
        }

        Obelisk::UE::RuntimeReflection::ReadOptions options =
            Obelisk::UE::RuntimeReflection::MakeReadOptionsForBinary(gate.BinarySha256, true);

        Obelisk::UE::MissionReflection::MissionInvocation invocation;
        Obelisk::UE::RuntimeReflection::ReadResult result;
        try
        {
            result = Obelisk::UE::MissionReflection::TryIdentifyMissionInvocation(
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
                    "mission prefilter FName does not match reflected UFunction FName"),
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

        if (!IsReflectedMissionNameIndex(nameIndex))
        {
            return {
                AttemptStatus::NonMissionFunction,
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

    bool TryBuildCopiedMissionObservation(const Obelisk::UE::MissionReflection::MissionInvocation& invocation,
                                          CopiedMissionObservation& out)
    {
        out = {};
        const ExpectedMissionObservation* expected = FindExpectedObservation(
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
            const Obelisk::UE::MissionReflection::MissionFieldRange& field = invocation.Fields[fieldIndex];
            const ExpectedMissionField& expectedField = expected->Fields[fieldIndex];
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

            MissionBoolObservation copiedBool;
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
}
