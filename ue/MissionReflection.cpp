#include "MissionReflection.h"

#include <array>
#include <utility>

namespace Obelisk::UE::MissionReflection
{
    namespace
    {
        constexpr int32_t kBPAllowPlayerToLeaveMissionNameIndex = 1211;
        constexpr int32_t kBPOnPlayerRemovedFromMissionNameIndex = 1582;
        constexpr int32_t kAddPlayerToMissionNameIndex = 7649;
        constexpr int32_t kMissionTypeNameIndex = 7646;
        constexpr int32_t kGetPlayerUsableItemsNameIndex = 7702;

        constexpr int32_t kBoolPropertyClassNameIndex = 3;
        constexpr int32_t kObjectPropertyClassNameIndex = 5;
        constexpr int32_t kArrayPropertyClassNameIndex = 9;
        constexpr int32_t kFunctionClassNameIndex = 10650;

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

        constexpr size_t kObjectPropertySize = 0x8;
        constexpr size_t kBoolPropertySize = 0x1;
        constexpr size_t kArrayPropertySize = 0x10;
        constexpr uint64_t kObjectInputPropertyFlags = 0x1040000280;
        constexpr uint64_t kBoolInputPropertyFlags = 0x1040000280;
        constexpr uint64_t kBoolReturnPropertyFlags = 0x1040000780;
        constexpr uint64_t kArrayOutPropertyFlags = 0x380;

        struct MissionFieldSpec
        {
            MissionField Field;
            int32_t NameIndex;
            int32_t Offset;
            size_t Size;
            int32_t ClassNameIndex;
            uint64_t PropertyFlags;
            bool ExposesRange;
        };

        struct MissionFunctionSpec
        {
            MissionFunction Function;
            int32_t NameIndex;
            int32_t OuterNameIndex;
            uint16_t NumParms;
            uint16_t ParmsSize;
            uint16_t ReturnValueOffset;
            uint32_t FunctionFlags;
            const MissionFieldSpec* Fields;
            size_t FieldCount;
        };

        constexpr std::array<MissionFieldSpec, 2> kGetPlayerUsableItemsFields{{
            {MissionField::Character,
             kCharacterNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectInputPropertyFlags,
             false},
            {MissionField::OutItemIDs,
             kOutItemIDsNameIndex,
             0x08,
             kArrayPropertySize,
             kArrayPropertyClassNameIndex,
             kArrayOutPropertyFlags,
             false},
        }};

        constexpr std::array<MissionFieldSpec, 3> kAddPlayerToMissionFields{{
            {MissionField::PlayerCharacter,
             kPlayerCharacterNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectInputPropertyFlags,
             false},
            {MissionField::BForceAdd,
             kBForceAddNameIndex,
             0x08,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolInputPropertyFlags,
             true},
            {MissionField::ReturnValue,
             kReturnValueNameIndex,
             0x09,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolReturnPropertyFlags,
             true},
        }};

        constexpr std::array<MissionFieldSpec, 2> kBPAllowPlayerToLeaveMissionFields{{
            {MissionField::PlayerPawn,
             kPlayerPawnNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectInputPropertyFlags,
             false},
            {MissionField::ReturnValue,
             kReturnValueNameIndex,
             0x08,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolReturnPropertyFlags,
             true},
        }};

        constexpr std::array<MissionFieldSpec, 4> kBPOnPlayerRemovedFromMissionFields{{
            {MissionField::Player,
             kPlayerNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectInputPropertyFlags,
             false},
            {MissionField::Controller,
             kControllerNameIndex,
             0x08,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectInputPropertyFlags,
             false},
            {MissionField::BFromMissionCompleteEvent,
             kBFromMissionCompleteEventNameIndex,
             0x10,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolInputPropertyFlags,
             true},
            {MissionField::BLastPhaseSuccess,
             kBLastPhaseSuccessNameIndex,
             0x11,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolInputPropertyFlags,
             true},
        }};

        constexpr MissionFunctionSpec kGetPlayerUsableItemsSpec{
            MissionFunction::GetPlayerUsableItems,
            kGetPlayerUsableItemsNameIndex,
            kMissionTypeNameIndex,
            2,
            0x18,
            0xffff,
            0x04420405,
            kGetPlayerUsableItemsFields.data(),
            kGetPlayerUsableItemsFields.size(),
        };

        constexpr MissionFunctionSpec kAddPlayerToMissionSpec{
            MissionFunction::AddPlayerToMission,
            kAddPlayerToMissionNameIndex,
            kMissionTypeNameIndex,
            3,
            0x0a,
            0x09,
            0x04020405,
            kAddPlayerToMissionFields.data(),
            kAddPlayerToMissionFields.size(),
        };

        constexpr MissionFunctionSpec kBPAllowPlayerToLeaveMissionSpec{
            MissionFunction::BPAllowPlayerToLeaveMission,
            kBPAllowPlayerToLeaveMissionNameIndex,
            kMissionTypeNameIndex,
            2,
            0x09,
            0x08,
            0x0c020c00,
            kBPAllowPlayerToLeaveMissionFields.data(),
            kBPAllowPlayerToLeaveMissionFields.size(),
        };

        constexpr MissionFunctionSpec kBPOnPlayerRemovedFromMissionSpec{
            MissionFunction::BPOnPlayerRemovedFromMission,
            kBPOnPlayerRemovedFromMissionNameIndex,
            kMissionTypeNameIndex,
            4,
            0x12,
            0xffff,
            0x0c020c00,
            kBPOnPlayerRemovedFromMissionFields.data(),
            kBPOnPlayerRemovedFromMissionFields.size(),
        };

        const MissionFunctionSpec* FindSpec(int32_t nameIndex)
        {
            switch (nameIndex)
            {
            case kGetPlayerUsableItemsNameIndex:
                return &kGetPlayerUsableItemsSpec;
            case kAddPlayerToMissionNameIndex:
                return &kAddPlayerToMissionSpec;
            case kBPAllowPlayerToLeaveMissionNameIndex:
                return &kBPAllowPlayerToLeaveMissionSpec;
            case kBPOnPlayerRemovedFromMissionNameIndex:
                return &kBPOnPlayerRemovedFromMissionSpec;
            default:
                return nullptr;
            }
        }

        RuntimeReflection::ReadResult ValidateGate(const RuntimeReflection::ReadOptions& options)
        {
            if (!options.Enabled)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Disabled,
                                                           "mission reflection is disabled");
            if (!options.Layout)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "no supported layout for mission reflection");
            if (options.Layout->BinarySha256 != RuntimeReflection::kSupportedShooterGameServerSha256)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "mission reflection constants do not match binary layout");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionClass(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UFunctionView& function)
        {
            if (!function.Object.ClassPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "mission UFunction has null class");

            RuntimeReflection::UObjectView functionClass;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, function.Object.ClassPrivate, functionClass);
            if (!result)
                return result;

            if (functionClass.NamePrivate.ComparisonIndex != kFunctionClassNameIndex ||
                functionClass.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "mission UFunction class FName mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionShape(const RuntimeReflection::UFunctionView& function,
                                                            const MissionFunctionSpec& spec)
        {
            if (function.Object.NamePrivate.ComparisonIndex != spec.NameIndex ||
                function.Object.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "UFunction FName does not match mission spec");
            if (function.NumParms != spec.NumParms)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "mission UFunction NumParms mismatch");
            if (function.ParmsSize != spec.ParmsSize)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "mission UFunction ParmsSize mismatch");
            if (function.ReturnValueOffset != spec.ReturnValueOffset)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "mission UFunction ReturnValueOffset mismatch");
            if (function.FunctionFlags != spec.FunctionFlags)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "mission UFunction FunctionFlags mismatch");
            if (function.Parameters.size() != spec.FieldCount)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "mission property count mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionOuter(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UFunctionView& function,
                                                            const MissionFunctionSpec& spec)
        {
            if (!function.Object.OuterPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "mission UFunction has null outer");

            RuntimeReflection::UObjectView outer;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, function.Object.OuterPrivate, outer);
            if (!result)
                return result;

            if (outer.NamePrivate.ComparisonIndex != spec.OuterNameIndex ||
                outer.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "mission UFunction outer FName mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidatePropertyClass(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UPropertyView& property,
                                                            const MissionFieldSpec& spec)
        {
            if (!property.Object.ClassPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "mission property has null class");

            RuntimeReflection::UObjectView propertyClass;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, property.Object.ClassPrivate, propertyClass);
            if (!result)
                return result;

            if (propertyClass.NamePrivate.ComparisonIndex != spec.ClassNameIndex ||
                propertyClass.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "mission property class FName mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateProperty(const RuntimeReflection::MemoryReader& reader,
                                                       const RuntimeReflection::FieldLayout& layout,
                                                       const RuntimeReflection::UPropertyView& property,
                                                       const MissionFieldSpec& spec)
        {
            if (property.Object.NamePrivate.ComparisonIndex != spec.NameIndex ||
                property.Object.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "mission property FName mismatch");
            if (property.OffsetInternal != spec.Offset)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "mission property offset mismatch");
            if (property.ByteSize != spec.Size)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "mission property size mismatch");
            if (property.PropertyFlags != spec.PropertyFlags)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "mission property flags mismatch");
            if (property.ElementSize != static_cast<int32_t>(spec.Size))
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "mission property ElementSize mismatch");
            if (property.ArrayDim != 1)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "mission property ArrayDim mismatch");

            return ValidatePropertyClass(reader, layout, property, spec);
        }
    }

    RuntimeReflection::ReadResult TryIdentifyMissionInvocation(const RuntimeReflection::MemoryReader& reader,
                                                               const RuntimeReflection::ReadOptions& options,
                                                               const void* function,
                                                               const void* params,
                                                               MissionInvocation& out)
    {
        out = {};

        if (RuntimeReflection::ReadResult gate = ValidateGate(options); !gate)
            return gate;
        if (!function)
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::InvalidArgument,
                                                       "null UFunction pointer");

        RuntimeReflection::UObjectView functionObject;
        if (RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, *options.Layout, function, functionObject);
            !result)
        {
            return result;
        }

        const MissionFunctionSpec* spec = FindSpec(functionObject.NamePrivate.ComparisonIndex);
        if (!spec)
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                       "UFunction FName index is not a supported mission target");

        RuntimeReflection::UFunctionView reflectedFunction;
        if (RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUFunction(reader, options, function, reflectedFunction);
            !result)
        {
            return result;
        }
        if (RuntimeReflection::ReadResult result =
                ValidateFunctionClass(reader, *options.Layout, reflectedFunction);
            !result)
        {
            return result;
        }
        if (RuntimeReflection::ReadResult result = ValidateFunctionShape(reflectedFunction, *spec); !result)
            return result;
        if (RuntimeReflection::ReadResult result =
                ValidateFunctionOuter(reader, *options.Layout, reflectedFunction, *spec);
            !result)
        {
            return result;
        }

        MissionInvocation value;
        value.Function = spec->Function;
        value.FunctionNameIndex = spec->NameIndex;
        value.OuterNameIndex = spec->OuterNameIndex;
        value.HasParameterRanges = params != nullptr;
        if (spec->FieldCount > value.Fields.capacity())
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::OutOfBounds,
                                                       "mission field count exceeds storage capacity");
        value.Fields.reserve(spec->FieldCount);

        for (size_t i = 0; i < spec->FieldCount; ++i)
        {
            const MissionFieldSpec& fieldSpec = spec->Fields[i];
            const RuntimeReflection::UPropertyView& property = reflectedFunction.Parameters[i];
            if (RuntimeReflection::ReadResult result =
                    ValidateProperty(reader, *options.Layout, property, fieldSpec);
                !result)
            {
                return result;
            }

            MissionFieldRange field;
            field.Field = fieldSpec.Field;
            field.PropertyNameIndex = fieldSpec.NameIndex;
            field.Offset = fieldSpec.Offset;
            field.Size = fieldSpec.Size;
            field.ExposesRange = fieldSpec.ExposesRange;

            if (value.HasParameterRanges && field.ExposesRange)
            {
                if (RuntimeReflection::ReadResult result =
                        RuntimeReflection::TryGetParameterRange(reader,
                                                                params,
                                                                reflectedFunction.ParmsSize,
                                                                property,
                                                                fieldSpec.Size,
                                                                field.Range);
                    !result)
                {
                    return result;
                }
            }

            value.Fields.push_back(field);
        }

        out = std::move(value);
        return RuntimeReflection::ReadResult::Ok();
    }
}
