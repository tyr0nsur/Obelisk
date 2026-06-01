#include "InventoryReflection.h"

#include <array>
#include <cstring>
#include <utility>

namespace Obelisk::UE::InventoryReflection
{
    namespace
    {
        constexpr int32_t kAllowRemoteAddToInventoryNameIndex = 6236;
        constexpr int32_t kCanUseNameIndex = 6252;
        constexpr int32_t kServerRequestInventoryUseItemNameIndex = 2651;
        constexpr int32_t kServerRequestInventoryUseItemWithActorNameIndex = 2652;
        constexpr int32_t kPrimalItemNameIndex = 6231;
        constexpr int32_t kPrimalItemObjectIndex = 17;
        constexpr int32_t kShooterPlayerControllerNameIndex = 6721;
        constexpr int32_t kShooterPlayerControllerObjectIndex = 50;

        constexpr int32_t kBoolPropertyClassNameIndex = 3;
        constexpr int32_t kFunctionClassNameIndex = 10650;
        constexpr int32_t kIntPropertyClassNameIndex = 2;
        constexpr int32_t kObjectPropertyClassNameIndex = 5;
        constexpr int32_t kStructPropertyClassNameIndex = 10;
        constexpr int32_t kBoolPropertyClassObjectIndex = 532;
        constexpr int32_t kFunctionClassObjectIndex = 518;
        constexpr int32_t kIntPropertyClassObjectIndex = 539;
        constexpr int32_t kObjectPropertyClassObjectIndex = 534;
        constexpr int32_t kStructPropertyClassObjectIndex = 548;

        constexpr int32_t kInvCompNameIndex = 18798;
        constexpr int32_t kInventoryCompNameIndex = 16929;
        constexpr int32_t kByPCNameIndex = 18797;
        constexpr int32_t kBRequestedByPlayerNameIndex = 18796;
        constexpr int32_t kReturnValueNameIndex = 17716;
        constexpr int32_t kBIgnoreCooldownNameIndex = 18814;
        constexpr int32_t kItemIdNameIndex = 16928;
        constexpr int32_t kItemID1NameIndex = 16926;
        constexpr int32_t kAdditionalDataNameIndex = 19290;
        constexpr int32_t kAnActorNameIndex = 20098;

        constexpr uint32_t kAllowRemoteAddToInventoryFunctionFlags = 0x04020400;
        constexpr uint32_t kCanUseFunctionFlags = 0x54020400;
        constexpr uint32_t kInventoryActionFunctionFlags = 0x00220cc0;
        constexpr size_t kObjectPropertySize = 0x8;
        constexpr size_t kBoolPropertySize = 0x1;
        constexpr size_t kIntPropertySize = 0x4;
        constexpr size_t kRedactedStructPropertySize = 0x8;

        constexpr uint64_t kBoolInputPropertyFlags = 0x1040000280;
        constexpr uint64_t kBoolReturnPropertyFlags = 0x1040000780;
        constexpr uint64_t kRemoteAddInventoryComponentPropertyFlags = 0x1044080280;
        constexpr uint64_t kObjectInputPropertyFlags = 0x1040000280;
        constexpr uint64_t kIntInputPropertyFlags = 0x1040000280;
        constexpr uint64_t kStructInputPropertyFlags = 0x1040000280;

        struct InventoryFieldSpec
        {
            InventoryField Field;
            int32_t NameIndex;
            int32_t Offset;
            size_t Size;
            int32_t ClassNameIndex;
            int32_t ClassObjectIndex;
            uint64_t PropertyFlags;
            bool ExposesRange;
        };

        struct InventoryFunctionSpec
        {
            InventoryFunction Function;
            int32_t NameIndex;
            int32_t OuterNameIndex;
            int32_t OuterObjectIndex;
            uint32_t FunctionFlags;
            uint16_t NumParms;
            uint16_t ParmsSize;
            uint16_t ReturnValueOffset;
            const InventoryFieldSpec* Fields;
            size_t FieldCount;
        };

        constexpr std::array<InventoryFieldSpec, 4> kAllowRemoteAddToInventoryFields{{
            {InventoryField::InventoryComponent,
             kInvCompNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kRemoteAddInventoryComponentPropertyFlags,
             false},
            {InventoryField::ByPC,
             kByPCNameIndex,
             0x08,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags,
             false},
            {InventoryField::BRequestedByPlayer,
             kBRequestedByPlayerNameIndex,
             0x10,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolInputPropertyFlags,
             true},
            {InventoryField::ReturnValue,
             kReturnValueNameIndex,
             0x11,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolReturnPropertyFlags,
             true},
        }};

        constexpr std::array<InventoryFieldSpec, 2> kCanUseFields{{
            {InventoryField::BIgnoreCooldown,
             kBIgnoreCooldownNameIndex,
             0x00,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolInputPropertyFlags,
             true},
            {InventoryField::ReturnValue,
             kReturnValueNameIndex,
             0x01,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolReturnPropertyFlags,
             true},
        }};

        constexpr std::array<InventoryFieldSpec, 2> kServerRequestInventoryUseItemFields{{
            {InventoryField::InventoryComponent,
             kInventoryCompNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kRemoteAddInventoryComponentPropertyFlags,
             false},
            {InventoryField::RedactedItemId,
             kItemIdNameIndex,
             0x08,
             kRedactedStructPropertySize,
             kStructPropertyClassNameIndex,
             kStructPropertyClassObjectIndex,
             kStructInputPropertyFlags,
             false},
        }};

        constexpr std::array<InventoryFieldSpec, 4> kServerRequestInventoryUseItemWithActorFields{{
            {InventoryField::Actor,
             kAnActorNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags,
             false},
            {InventoryField::InventoryComponent,
             kInventoryCompNameIndex,
             0x08,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kRemoteAddInventoryComponentPropertyFlags,
             false},
            {InventoryField::RedactedItemId1,
             kItemID1NameIndex,
             0x10,
             kRedactedStructPropertySize,
             kStructPropertyClassNameIndex,
             kStructPropertyClassObjectIndex,
             kStructInputPropertyFlags,
             false},
            {InventoryField::AdditionalData,
             kAdditionalDataNameIndex,
             0x18,
             kIntPropertySize,
             kIntPropertyClassNameIndex,
             kIntPropertyClassObjectIndex,
             kIntInputPropertyFlags,
             false},
        }};

        constexpr InventoryFunctionSpec kAllowRemoteAddToInventorySpec{
            InventoryFunction::AllowRemoteAddToInventory,
            kAllowRemoteAddToInventoryNameIndex,
            kPrimalItemNameIndex,
            kPrimalItemObjectIndex,
            kAllowRemoteAddToInventoryFunctionFlags,
            4,
            0x12,
            0x11,
            kAllowRemoteAddToInventoryFields.data(),
            kAllowRemoteAddToInventoryFields.size(),
        };

        constexpr InventoryFunctionSpec kCanUseSpec{
            InventoryFunction::CanUse,
            kCanUseNameIndex,
            kPrimalItemNameIndex,
            kPrimalItemObjectIndex,
            kCanUseFunctionFlags,
            2,
            0x02,
            0x01,
            kCanUseFields.data(),
            kCanUseFields.size(),
        };

        constexpr InventoryFunctionSpec kServerRequestInventoryUseItemSpec{
            InventoryFunction::ServerRequestInventoryUseItem,
            kServerRequestInventoryUseItemNameIndex,
            kShooterPlayerControllerNameIndex,
            kShooterPlayerControllerObjectIndex,
            kInventoryActionFunctionFlags,
            2,
            0x10,
            0xffff,
            kServerRequestInventoryUseItemFields.data(),
            kServerRequestInventoryUseItemFields.size(),
        };

        constexpr InventoryFunctionSpec kServerRequestInventoryUseItemWithActorSpec{
            InventoryFunction::ServerRequestInventoryUseItemWithActor,
            kServerRequestInventoryUseItemWithActorNameIndex,
            kShooterPlayerControllerNameIndex,
            kShooterPlayerControllerObjectIndex,
            kInventoryActionFunctionFlags,
            4,
            0x1c,
            0xffff,
            kServerRequestInventoryUseItemWithActorFields.data(),
            kServerRequestInventoryUseItemWithActorFields.size(),
        };

        const InventoryFunctionSpec* FindSpec(int32_t nameIndex)
        {
            switch (nameIndex)
            {
            case kAllowRemoteAddToInventoryNameIndex:
                return &kAllowRemoteAddToInventorySpec;
            case kCanUseNameIndex:
                return &kCanUseSpec;
            case kServerRequestInventoryUseItemNameIndex:
                return &kServerRequestInventoryUseItemSpec;
            case kServerRequestInventoryUseItemWithActorNameIndex:
                return &kServerRequestInventoryUseItemWithActorSpec;
            default:
                return nullptr;
            }
        }

        bool HasCopiedParameterRange(const InventoryFunctionSpec& spec)
        {
            for (size_t i = 0; i < spec.FieldCount; ++i)
            {
                if (spec.Fields[i].ExposesRange)
                    return true;
            }
            return false;
        }

        RuntimeReflection::ReadResult ValidateGate(const RuntimeReflection::ReadOptions& options)
        {
            if (!options.Enabled)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Disabled,
                                                           "inventory reflection is disabled");
            if (!options.Layout)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "no supported layout for inventory reflection");
            const RuntimeReflection::FieldLayout* supportedLayout =
                RuntimeReflection::FindSupportedLayout(RuntimeReflection::kSupportedShooterGameServerSha256);
            if (options.Layout != supportedLayout)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "inventory reflection constants do not match binary layout");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionClass(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UFunctionView& function)
        {
            if (!function.Object.ClassPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory UFunction has null class");

            RuntimeReflection::UObjectView functionClass;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, function.Object.ClassPrivate, functionClass);
            if (!result)
                return result;

            if (functionClass.NamePrivate.ComparisonIndex != kFunctionClassNameIndex ||
                functionClass.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory UFunction class FName mismatch");
            if (functionClass.InternalIndex != kFunctionClassObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory UFunction class object index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionShape(const RuntimeReflection::UFunctionView& function,
                                                            const InventoryFunctionSpec& spec)
        {
            if (function.Object.NamePrivate.ComparisonIndex != spec.NameIndex ||
                function.Object.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "UFunction FName does not match inventory spec");
            if (function.FunctionFlags != spec.FunctionFlags)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory UFunction FunctionFlags mismatch");
            if (function.NumParms != spec.NumParms)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory UFunction NumParms mismatch");
            if (function.ParmsSize != spec.ParmsSize)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory UFunction ParmsSize mismatch");
            if (function.ReturnValueOffset != spec.ReturnValueOffset)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory UFunction ReturnValueOffset mismatch");
            if (function.Parameters.size() != spec.FieldCount)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory property count mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionOuter(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UFunctionView& function,
                                                            const InventoryFunctionSpec& spec)
        {
            if (!function.Object.OuterPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory UFunction has null outer");

            RuntimeReflection::UObjectView outer;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, function.Object.OuterPrivate, outer);
            if (!result)
                return result;

            if (outer.NamePrivate.ComparisonIndex != spec.OuterNameIndex ||
                outer.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory UFunction outer FName mismatch");
            if (outer.InternalIndex != spec.OuterObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory UFunction outer object index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidatePropertyClass(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UPropertyView& property,
                                                            const InventoryFieldSpec& spec)
        {
            if (!property.Object.ClassPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory property has null class");

            RuntimeReflection::UObjectView propertyClass;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, property.Object.ClassPrivate, propertyClass);
            if (!result)
                return result;

            if (propertyClass.NamePrivate.ComparisonIndex != spec.ClassNameIndex ||
                propertyClass.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory property class FName mismatch");
            if (propertyClass.InternalIndex != spec.ClassObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory property class object index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateProperty(const RuntimeReflection::MemoryReader& reader,
                                                       const RuntimeReflection::FieldLayout& layout,
                                                       const RuntimeReflection::UPropertyView& property,
                                                       const InventoryFieldSpec& spec)
        {
            if (property.Object.NamePrivate.ComparisonIndex != spec.NameIndex ||
                property.Object.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory property FName mismatch");
            if (property.OffsetInternal != spec.Offset)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory property offset mismatch");
            if (property.ByteSize != spec.Size)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory property size mismatch");
            if (property.ElementSize != static_cast<int32_t>(spec.Size))
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory property ElementSize mismatch");
            if (property.ArrayDim != 1)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory property ArrayDim mismatch");
            if (property.PropertyFlags != spec.PropertyFlags)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory property flags mismatch");

            return ValidatePropertyClass(reader, layout, property, spec);
        }

        RuntimeReflection::ReadResult ValidateCanonicalCopiedBool(const RuntimeReflection::ParamRange& range)
        {
            if (!range.Data || range.Size != kBoolPropertySize)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::InvalidArgument,
                                                           "inventory copied bool parameter range is invalid");

            uint8_t value = 0;
            std::memcpy(&value, range.Data, sizeof(value));
            if (value > 1)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "inventory copied bool parameter is not canonical");
            return RuntimeReflection::ReadResult::Ok();
        }
    }

    RuntimeReflection::ReadResult TryIdentifyInventoryInvocation(const RuntimeReflection::MemoryReader& reader,
                                                                 const RuntimeReflection::ReadOptions& options,
                                                                 const void* function,
                                                                 const void* params,
                                                                 InventoryInvocation& out)
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

        const InventoryFunctionSpec* spec = FindSpec(functionObject.NamePrivate.ComparisonIndex);
        if (!spec)
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                       "UFunction FName index is not a supported inventory target");

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

        InventoryInvocation value;
        value.Function = spec->Function;
        value.FunctionNameIndex = spec->NameIndex;
        value.OuterNameIndex = spec->OuterNameIndex;
        value.HasParameterRanges = params != nullptr && HasCopiedParameterRange(*spec);
        if (value.HasParameterRanges)
        {
            value.ParamData = static_cast<const uint8_t*>(params);
            value.ParamSize = reflectedFunction.ParmsSize;
        }
        if (spec->FieldCount > value.Fields.capacity())
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::OutOfBounds,
                                                       "inventory field count exceeds storage capacity");
        value.Fields.reserve(spec->FieldCount);

        for (size_t i = 0; i < spec->FieldCount; ++i)
        {
            const InventoryFieldSpec& fieldSpec = spec->Fields[i];
            const RuntimeReflection::UPropertyView& property = reflectedFunction.Parameters[i];
            if (RuntimeReflection::ReadResult result =
                    ValidateProperty(reader, *options.Layout, property, fieldSpec);
                !result)
            {
                return result;
            }

            InventoryFieldRange field;
            field.Field = fieldSpec.Field;
            field.PropertyNameIndex = fieldSpec.NameIndex;
            field.PropertyClassNameIndex = fieldSpec.ClassNameIndex;
            field.PropertyClassObjectIndex = fieldSpec.ClassObjectIndex;
            field.PropertyFlags = fieldSpec.PropertyFlags;
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
                if (RuntimeReflection::ReadResult result = ValidateCanonicalCopiedBool(field.Range); !result)
                    return result;
            }

            value.Fields.push_back(field);
        }

        out = std::move(value);
        return RuntimeReflection::ReadResult::Ok();
    }
}
