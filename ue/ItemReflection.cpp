#include "ItemReflection.h"

#include <array>
#include <utility>

namespace Obelisk::UE::ItemReflection
{
    namespace
    {
        constexpr int32_t kAllowEquipItemNameIndex = 6235;
        constexpr int32_t kCanRepairNameIndex = 6250;
        constexpr int32_t kCraftBlueprintNameIndex = 6257;
        constexpr int32_t kUseItemOntoItemNameIndex = 6346;
        constexpr int32_t kPrimalItemNameIndex = 6231;
        constexpr int32_t kPrimalItemObjectIndex = 17;

        constexpr int32_t kIntPropertyClassNameIndex = 2;
        constexpr int32_t kBoolPropertyClassNameIndex = 3;
        constexpr int32_t kObjectPropertyClassNameIndex = 5;
        constexpr int32_t kFunctionClassNameIndex = 10650;
        constexpr int32_t kBoolPropertyClassObjectIndex = 532;
        constexpr int32_t kObjectPropertyClassObjectIndex = 534;
        constexpr int32_t kFunctionClassObjectIndex = 518;
        constexpr int32_t kIntPropertyClassObjectIndex = 539;

        constexpr int32_t kReturnValueNameIndex = 17716;
        constexpr int32_t kBIgnoreInventoryRequirementNameIndex = 18617;
        constexpr int32_t kToInventoryNameIndex = 18795;
        constexpr int32_t kDestinationItemNameIndex = 19285;
        constexpr int32_t kAdditionalDataNameIndex = 19290;
        constexpr int32_t kBConsumeResourcesNameIndex = 19293;

        constexpr uint32_t kItemFunctionFlags = 0x04020400;
        constexpr size_t kObjectPropertySize = 0x8;
        constexpr size_t kIntPropertySize = 0x4;
        constexpr size_t kBoolPropertySize = 0x1;

        constexpr uint64_t kBoolInputPropertyFlags = 0x1040000280;
        constexpr uint64_t kBoolReturnPropertyFlags = 0x1040000780;
        constexpr uint64_t kToInventoryPropertyFlags = 0x1044080280;
        constexpr uint64_t kObjectInputPropertyFlags = 0x1040000280;
        constexpr uint64_t kIntInputPropertyFlags = 0x1040000280;

        struct ItemFieldSpec
        {
            ItemField Field;
            int32_t NameIndex;
            int32_t Offset;
            size_t Size;
            int32_t ClassNameIndex;
            int32_t ClassObjectIndex;
            uint64_t PropertyFlags;
            bool ExposesRange;
        };

        struct ItemFunctionSpec
        {
            ItemFunction Function;
            int32_t NameIndex;
            int32_t OuterNameIndex;
            int32_t OuterObjectIndex;
            uint32_t FunctionFlags;
            uint16_t NumParms;
            uint16_t ParmsSize;
            uint16_t ReturnValueOffset;
            const ItemFieldSpec* Fields;
            size_t FieldCount;
        };

        constexpr std::array<ItemFieldSpec, 2> kAllowEquipItemFields{{
            {ItemField::ToInventory,
             kToInventoryNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kToInventoryPropertyFlags,
             false},
            {ItemField::ReturnValue,
             kReturnValueNameIndex,
             0x08,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolReturnPropertyFlags,
             true},
        }};

        constexpr std::array<ItemFieldSpec, 2> kCanRepairFields{{
            {ItemField::BIgnoreInventoryRequirement,
             kBIgnoreInventoryRequirementNameIndex,
             0x00,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolInputPropertyFlags,
             true},
            {ItemField::ReturnValue,
             kReturnValueNameIndex,
             0x01,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolReturnPropertyFlags,
             true},
        }};

        constexpr std::array<ItemFieldSpec, 1> kCraftBlueprintFields{{
            {ItemField::BConsumeResources,
             kBConsumeResourcesNameIndex,
             0x00,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolInputPropertyFlags,
             true},
        }};

        constexpr std::array<ItemFieldSpec, 3> kUseItemOntoItemFields{{
            {ItemField::DestinationItem,
             kDestinationItemNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags,
             false},
            {ItemField::AdditionalData,
             kAdditionalDataNameIndex,
             0x08,
             kIntPropertySize,
             kIntPropertyClassNameIndex,
             kIntPropertyClassObjectIndex,
             kIntInputPropertyFlags,
             false},
            {ItemField::ReturnValue,
             kReturnValueNameIndex,
             0x0c,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolReturnPropertyFlags,
             true},
        }};

        constexpr ItemFunctionSpec kAllowEquipItemSpec{
            ItemFunction::AllowEquipItem,
            kAllowEquipItemNameIndex,
            kPrimalItemNameIndex,
            kPrimalItemObjectIndex,
            kItemFunctionFlags,
            2,
            0x09,
            0x08,
            kAllowEquipItemFields.data(),
            kAllowEquipItemFields.size(),
        };

        constexpr ItemFunctionSpec kCanRepairSpec{
            ItemFunction::CanRepair,
            kCanRepairNameIndex,
            kPrimalItemNameIndex,
            kPrimalItemObjectIndex,
            kItemFunctionFlags,
            2,
            0x02,
            0x01,
            kCanRepairFields.data(),
            kCanRepairFields.size(),
        };

        constexpr ItemFunctionSpec kCraftBlueprintSpec{
            ItemFunction::CraftBlueprint,
            kCraftBlueprintNameIndex,
            kPrimalItemNameIndex,
            kPrimalItemObjectIndex,
            kItemFunctionFlags,
            1,
            0x01,
            0xffff,
            kCraftBlueprintFields.data(),
            kCraftBlueprintFields.size(),
        };

        constexpr ItemFunctionSpec kUseItemOntoItemSpec{
            ItemFunction::UseItemOntoItem,
            kUseItemOntoItemNameIndex,
            kPrimalItemNameIndex,
            kPrimalItemObjectIndex,
            kItemFunctionFlags,
            3,
            0x0d,
            0x0c,
            kUseItemOntoItemFields.data(),
            kUseItemOntoItemFields.size(),
        };

        const ItemFunctionSpec* FindSpec(int32_t nameIndex)
        {
            switch (nameIndex)
            {
            case kAllowEquipItemNameIndex:
                return &kAllowEquipItemSpec;
            case kCanRepairNameIndex:
                return &kCanRepairSpec;
            case kCraftBlueprintNameIndex:
                return &kCraftBlueprintSpec;
            case kUseItemOntoItemNameIndex:
                return &kUseItemOntoItemSpec;
            default:
                return nullptr;
            }
        }

        RuntimeReflection::ReadResult ValidateGate(const RuntimeReflection::ReadOptions& options)
        {
            if (!options.Enabled)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Disabled,
                                                           "item reflection is disabled");
            if (!options.Layout)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "no supported layout for item reflection");
            const RuntimeReflection::FieldLayout* supportedLayout =
                RuntimeReflection::FindSupportedLayout(RuntimeReflection::kSupportedShooterGameServerSha256);
            if (options.Layout != supportedLayout)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "item reflection constants do not match binary layout");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionClass(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UFunctionView& function)
        {
            if (!function.Object.ClassPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "item UFunction has null class");

            RuntimeReflection::UObjectView functionClass;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, function.Object.ClassPrivate, functionClass);
            if (!result)
                return result;

            if (functionClass.NamePrivate.ComparisonIndex != kFunctionClassNameIndex ||
                functionClass.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "item UFunction class FName mismatch");
            if (functionClass.InternalIndex != kFunctionClassObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "item UFunction class object index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionShape(const RuntimeReflection::UFunctionView& function,
                                                            const ItemFunctionSpec& spec)
        {
            if (function.Object.NamePrivate.ComparisonIndex != spec.NameIndex ||
                function.Object.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "UFunction FName does not match item spec");
            if (function.FunctionFlags != spec.FunctionFlags)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "item UFunction FunctionFlags mismatch");
            if (function.NumParms != spec.NumParms)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "item UFunction NumParms mismatch");
            if (function.ParmsSize != spec.ParmsSize)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "item UFunction ParmsSize mismatch");
            if (function.ReturnValueOffset != spec.ReturnValueOffset)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "item UFunction ReturnValueOffset mismatch");
            if (function.Parameters.size() != spec.FieldCount)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "item property count mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionOuter(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UFunctionView& function,
                                                            const ItemFunctionSpec& spec)
        {
            if (!function.Object.OuterPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "item UFunction has null outer");

            RuntimeReflection::UObjectView outer;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, function.Object.OuterPrivate, outer);
            if (!result)
                return result;

            if (outer.NamePrivate.ComparisonIndex != spec.OuterNameIndex ||
                outer.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "item UFunction outer FName mismatch");
            if (outer.InternalIndex != spec.OuterObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "item UFunction outer object index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidatePropertyClass(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UPropertyView& property,
                                                            const ItemFieldSpec& spec)
        {
            if (!property.Object.ClassPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "item property has null class");

            RuntimeReflection::UObjectView propertyClass;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, property.Object.ClassPrivate, propertyClass);
            if (!result)
                return result;

            if (propertyClass.NamePrivate.ComparisonIndex != spec.ClassNameIndex ||
                propertyClass.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "item property class FName mismatch");
            if (propertyClass.InternalIndex != spec.ClassObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "item property class object index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateProperty(const RuntimeReflection::MemoryReader& reader,
                                                       const RuntimeReflection::FieldLayout& layout,
                                                       const RuntimeReflection::UPropertyView& property,
                                                       const ItemFieldSpec& spec)
        {
            if (property.Object.NamePrivate.ComparisonIndex != spec.NameIndex ||
                property.Object.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "item property FName mismatch");
            if (property.OffsetInternal != spec.Offset)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "item property offset mismatch");
            if (property.ByteSize != spec.Size)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "item property size mismatch");
            if (property.ElementSize != static_cast<int32_t>(spec.Size))
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "item property ElementSize mismatch");
            if (property.ArrayDim != 1)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "item property ArrayDim mismatch");
            if (property.PropertyFlags != spec.PropertyFlags)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "item property flags mismatch");

            return ValidatePropertyClass(reader, layout, property, spec);
        }
    }

    RuntimeReflection::ReadResult TryIdentifyItemInvocation(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::ReadOptions& options,
                                                            const void* function,
                                                            const void* params,
                                                            ItemInvocation& out)
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

        const ItemFunctionSpec* spec = FindSpec(functionObject.NamePrivate.ComparisonIndex);
        if (!spec)
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                       "UFunction FName index is not a supported item target");

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

        ItemInvocation value;
        value.Function = spec->Function;
        value.FunctionNameIndex = spec->NameIndex;
        value.OuterNameIndex = spec->OuterNameIndex;
        value.HasParameterRanges = params != nullptr;
        if (spec->FieldCount > value.Fields.capacity())
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::OutOfBounds,
                                                       "item field count exceeds storage capacity");
        value.Fields.reserve(spec->FieldCount);

        for (size_t i = 0; i < spec->FieldCount; ++i)
        {
            const ItemFieldSpec& fieldSpec = spec->Fields[i];
            const RuntimeReflection::UPropertyView& property = reflectedFunction.Parameters[i];
            if (RuntimeReflection::ReadResult result =
                    ValidateProperty(reader, *options.Layout, property, fieldSpec);
                !result)
            {
                return result;
            }

            ItemFieldRange field;
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
