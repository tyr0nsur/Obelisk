#include "InventoryReflection.h"

#include <array>
#include <utility>

namespace Obelisk::UE::InventoryReflection
{
    namespace
    {
        constexpr int32_t kAllowRemoteAddToInventoryNameIndex = 6236;
        constexpr int32_t kCanUseNameIndex = 6252;
        constexpr int32_t kPrimalItemNameIndex = 6231;

        constexpr int32_t kBoolPropertyClassNameIndex = 3;
        constexpr int32_t kObjectPropertyClassNameIndex = 5;
        constexpr int32_t kObjectPropertyClassObjectIndex = 534;

        constexpr int32_t kInvCompNameIndex = 18798;
        constexpr int32_t kByPCNameIndex = 18797;
        constexpr int32_t kBRequestedByPlayerNameIndex = 18796;
        constexpr int32_t kReturnValueNameIndex = 17716;
        constexpr int32_t kBIgnoreCooldownNameIndex = 18814;

        constexpr size_t kObjectPropertySize = 0x8;
        constexpr size_t kBoolPropertySize = 0x1;
        constexpr int32_t kAnyObjectIndex = -1;

        struct InventoryFieldSpec
        {
            InventoryField Field;
            int32_t NameIndex;
            int32_t Offset;
            size_t Size;
            int32_t ClassNameIndex;
            int32_t ClassObjectIndex;
            bool ExposesRange;
        };

        struct InventoryFunctionSpec
        {
            InventoryFunction Function;
            int32_t NameIndex;
            int32_t OuterNameIndex;
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
             false},
            {InventoryField::ByPC,
             kByPCNameIndex,
             0x08,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             false},
            {InventoryField::BRequestedByPlayer,
             kBRequestedByPlayerNameIndex,
             0x10,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kAnyObjectIndex,
             true},
            {InventoryField::ReturnValue,
             kReturnValueNameIndex,
             0x11,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kAnyObjectIndex,
             true},
        }};

        constexpr std::array<InventoryFieldSpec, 2> kCanUseFields{{
            {InventoryField::BIgnoreCooldown,
             kBIgnoreCooldownNameIndex,
             0x00,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kAnyObjectIndex,
             true},
            {InventoryField::ReturnValue,
             kReturnValueNameIndex,
             0x01,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kAnyObjectIndex,
             true},
        }};

        constexpr InventoryFunctionSpec kAllowRemoteAddToInventorySpec{
            InventoryFunction::AllowRemoteAddToInventory,
            kAllowRemoteAddToInventoryNameIndex,
            kPrimalItemNameIndex,
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
            2,
            0x02,
            0x01,
            kCanUseFields.data(),
            kCanUseFields.size(),
        };

        const InventoryFunctionSpec* FindSpec(int32_t nameIndex)
        {
            switch (nameIndex)
            {
            case kAllowRemoteAddToInventoryNameIndex:
                return &kAllowRemoteAddToInventorySpec;
            case kCanUseNameIndex:
                return &kCanUseSpec;
            default:
                return nullptr;
            }
        }

        RuntimeReflection::ReadResult ValidateGate(const RuntimeReflection::ReadOptions& options)
        {
            if (!options.Enabled)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Disabled,
                                                           "inventory reflection is disabled");
            if (!options.Layout)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "no supported layout for inventory reflection");
            if (options.Layout->BinarySha256 != RuntimeReflection::kSupportedShooterGameServerSha256)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "inventory reflection constants do not match binary layout");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionShape(const RuntimeReflection::UFunctionView& function,
                                                            const InventoryFunctionSpec& spec)
        {
            if (function.Object.NamePrivate.ComparisonIndex != spec.NameIndex ||
                function.Object.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "UFunction FName does not match inventory spec");
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
            if (spec.ClassObjectIndex != kAnyObjectIndex &&
                propertyClass.InternalIndex != spec.ClassObjectIndex)
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

            return ValidatePropertyClass(reader, layout, property, spec);
        }
    }

    RuntimeReflection::ReadResult TryIdentifyInventoryInvocation(const RuntimeReflection::MemoryReader& reader,
                                                                 const RuntimeReflection::ReadOptions& options,
                                                                 const void* function,
                                                                 const void* params,
                                                                 InventoryInvocation& out)
    {
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
        value.HasParameterRanges = params != nullptr;
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
