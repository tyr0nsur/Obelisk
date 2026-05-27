#include "BuffReflection.h"

#include <array>
#include <utility>

namespace Obelisk::UE::BuffReflection
{
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

        constexpr size_t kObjectPropertySize = 0x8;
        constexpr size_t kBoolPropertySize = 0x1;

        struct BuffFieldSpec
        {
            BuffField Field;
            int32_t NameIndex;
            int32_t Offset;
            size_t Size;
            int32_t ClassNameIndex;
            int32_t ClassObjectIndex;
            bool ExposesRange;
        };

        struct BuffFunctionSpec
        {
            BuffFunction Function;
            int32_t NameIndex;
            int32_t OuterNameIndex;
            uint16_t NumParms;
            uint16_t ParmsSize;
            uint16_t ReturnValueOffset;
            const BuffFieldSpec* Fields;
            size_t FieldCount;
        };

        constexpr std::array<BuffFieldSpec, 1> kBoolReturnFields{{
            {BuffField::ReturnValue,
             kReturnValueNameIndex,
             0x00,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             true},
        }};

        constexpr std::array<BuffFieldSpec, 0> kNoFields{};

        constexpr std::array<BuffFieldSpec, 3> kBuffOverrideInventoryAccessInputFields{{
            {BuffField::InController,
             kInControllerNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             false},
            {BuffField::BInputPressed,
             kBInputPressedNameIndex,
             0x08,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             true},
            {BuffField::ReturnValue,
             kReturnValueNameIndex,
             0x09,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             true},
        }};

        constexpr std::array<BuffFieldSpec, 3> kBPCustomAllowAddBuffFields{{
            {BuffField::ForCharacter,
             kForCharacterNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             false},
            {BuffField::DamageCauser,
             kDamageCauserNameIndex,
             0x08,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             false},
            {BuffField::ReturnValue,
             kReturnValueNameIndex,
             0x10,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             true},
        }};

        constexpr std::array<BuffFieldSpec, 2> kBPPreventAddingOtherBuffFields{{
            {BuffField::AnotherBuffClass,
             kAnotherBuffClassNameIndex,
             0x00,
             kObjectPropertySize,
             kClassPropertyClassNameIndex,
             kClassPropertyClassObjectIndex,
             false},
            {BuffField::ReturnValue,
             kReturnValueNameIndex,
             0x08,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             true},
        }};

        constexpr BuffFunctionSpec kAllowPostProcessEffectSpec{
            BuffFunction::AllowPostProcessEffect,
            kAllowPostProcessEffectNameIndex,
            kPrimalBuffNameIndex,
            1,
            0x01,
            0x00,
            kBoolReturnFields.data(),
            kBoolReturnFields.size(),
        };

        constexpr BuffFunctionSpec kBPBuffPreventUploadingSpec{
            BuffFunction::BPBuffPreventUploading,
            kBPBuffPreventUploadingNameIndex,
            kPrimalBuffNameIndex,
            1,
            0x01,
            0x00,
            kBoolReturnFields.data(),
            kBoolReturnFields.size(),
        };

        constexpr BuffFunctionSpec kBPOnBuffLifetimeUpdatedSpec{
            BuffFunction::BPOnBuffLifetimeUpdated,
            kBPOnBuffLifetimeUpdatedNameIndex,
            kPrimalBuffNameIndex,
            0,
            0x00,
            0xffff,
            kNoFields.data(),
            kNoFields.size(),
        };

        constexpr BuffFunctionSpec kBuffOverrideInventoryAccessInputSpec{
            BuffFunction::BuffOverrideInventoryAccessInput,
            kBuffOverrideInventoryAccessInputNameIndex,
            kPrimalBuffNameIndex,
            3,
            0x0a,
            0x09,
            kBuffOverrideInventoryAccessInputFields.data(),
            kBuffOverrideInventoryAccessInputFields.size(),
        };

        constexpr BuffFunctionSpec kBPCustomAllowAddBuffSpec{
            BuffFunction::BPCustomAllowAddBuff,
            kBPCustomAllowAddBuffNameIndex,
            kPrimalBuffNameIndex,
            3,
            0x11,
            0x10,
            kBPCustomAllowAddBuffFields.data(),
            kBPCustomAllowAddBuffFields.size(),
        };

        constexpr BuffFunctionSpec kBPPreventAddingOtherBuffSpec{
            BuffFunction::BPPreventAddingOtherBuff,
            kBPPreventAddingOtherBuffNameIndex,
            kPrimalBuffNameIndex,
            2,
            0x09,
            0x08,
            kBPPreventAddingOtherBuffFields.data(),
            kBPPreventAddingOtherBuffFields.size(),
        };

        const BuffFunctionSpec* FindSpec(int32_t nameIndex)
        {
            switch (nameIndex)
            {
            case kAllowPostProcessEffectNameIndex:
                return &kAllowPostProcessEffectSpec;
            case kBPBuffPreventUploadingNameIndex:
                return &kBPBuffPreventUploadingSpec;
            case kBPOnBuffLifetimeUpdatedNameIndex:
                return &kBPOnBuffLifetimeUpdatedSpec;
            case kBuffOverrideInventoryAccessInputNameIndex:
                return &kBuffOverrideInventoryAccessInputSpec;
            case kBPCustomAllowAddBuffNameIndex:
                return &kBPCustomAllowAddBuffSpec;
            case kBPPreventAddingOtherBuffNameIndex:
                return &kBPPreventAddingOtherBuffSpec;
            default:
                return nullptr;
            }
        }

        RuntimeReflection::ReadResult ValidateGate(const RuntimeReflection::ReadOptions& options)
        {
            if (!options.Enabled)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Disabled,
                                                           "buff reflection is disabled");
            if (!options.Layout)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "no supported layout for buff reflection");
            if (options.Layout->BinarySha256 != RuntimeReflection::kSupportedShooterGameServerSha256)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "buff reflection constants do not match binary layout");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionShape(const RuntimeReflection::UFunctionView& function,
                                                            const BuffFunctionSpec& spec)
        {
            if (function.Object.NamePrivate.ComparisonIndex != spec.NameIndex ||
                function.Object.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "UFunction FName does not match buff spec");
            if (function.NumParms != spec.NumParms)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "buff UFunction NumParms mismatch");
            if (function.ParmsSize != spec.ParmsSize)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "buff UFunction ParmsSize mismatch");
            if (function.ReturnValueOffset != spec.ReturnValueOffset)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "buff UFunction ReturnValueOffset mismatch");
            if (function.Parameters.size() != spec.FieldCount)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "buff property count mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionOuter(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UFunctionView& function,
                                                            const BuffFunctionSpec& spec)
        {
            if (!function.Object.OuterPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "buff UFunction has null outer");

            RuntimeReflection::UObjectView outer;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, function.Object.OuterPrivate, outer);
            if (!result)
                return result;

            if (outer.NamePrivate.ComparisonIndex != spec.OuterNameIndex ||
                outer.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "buff UFunction outer FName mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidatePropertyClass(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UPropertyView& property,
                                                            const BuffFieldSpec& spec)
        {
            if (!property.Object.ClassPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "buff property has null class");

            RuntimeReflection::UObjectView propertyClass;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, property.Object.ClassPrivate, propertyClass);
            if (!result)
                return result;

            if (propertyClass.NamePrivate.ComparisonIndex != spec.ClassNameIndex ||
                propertyClass.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "buff property class FName mismatch");
            if (propertyClass.InternalIndex != spec.ClassObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "buff property class object index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateProperty(const RuntimeReflection::MemoryReader& reader,
                                                       const RuntimeReflection::FieldLayout& layout,
                                                       const RuntimeReflection::UPropertyView& property,
                                                       const BuffFieldSpec& spec)
        {
            if (property.Object.NamePrivate.ComparisonIndex != spec.NameIndex ||
                property.Object.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "buff property FName mismatch");
            if (property.OffsetInternal != spec.Offset)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "buff property offset mismatch");
            if (property.ByteSize != spec.Size)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "buff property size mismatch");
            if (property.ElementSize != static_cast<int32_t>(spec.Size))
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "buff property ElementSize mismatch");
            if (property.ArrayDim != 1)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "buff property ArrayDim mismatch");

            return ValidatePropertyClass(reader, layout, property, spec);
        }
    }

    RuntimeReflection::ReadResult TryIdentifyBuffInvocation(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::ReadOptions& options,
                                                            const void* function,
                                                            const void* params,
                                                            BuffInvocation& out)
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

        const BuffFunctionSpec* spec = FindSpec(functionObject.NamePrivate.ComparisonIndex);
        if (!spec)
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                       "UFunction FName index is not a supported buff target");

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

        BuffInvocation value;
        value.Function = spec->Function;
        value.FunctionNameIndex = spec->NameIndex;
        value.OuterNameIndex = spec->OuterNameIndex;
        value.HasParameterRanges = params != nullptr;
        if (spec->FieldCount > value.Fields.capacity())
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::OutOfBounds,
                                                       "buff field count exceeds storage capacity");
        value.Fields.reserve(spec->FieldCount);

        for (size_t i = 0; i < spec->FieldCount; ++i)
        {
            const BuffFieldSpec& fieldSpec = spec->Fields[i];
            const RuntimeReflection::UPropertyView& property = reflectedFunction.Parameters[i];
            if (RuntimeReflection::ReadResult result =
                    ValidateProperty(reader, *options.Layout, property, fieldSpec);
                !result)
            {
                return result;
            }

            BuffFieldRange field;
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
