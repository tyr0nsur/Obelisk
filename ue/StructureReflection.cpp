#include "StructureReflection.h"

#include <array>
#include <utility>

namespace Obelisk::UE::StructureReflection
{
    namespace
    {
        constexpr int32_t kAllowStructureAccessNameIndex = 7541;
        constexpr int32_t kIsAllowedToDemolishNameIndex = 7574;
        constexpr int32_t kSetVariantNameIndex = 7605;
        constexpr int32_t kAllowToggleActivationNameIndex = 7620;
        constexpr int32_t kVerifyPinCodeNameIndex = 7636;
        constexpr int32_t kCanSeatNameIndex = 8481;

        constexpr int32_t kPrimalStructureNameIndex = 7539;
        constexpr int32_t kPrimalStructureItemContainerNameIndex = 7617;
        constexpr int32_t kPrimalStructureSeatingNameIndex = 8480;

        constexpr int32_t kIntPropertyClassNameIndex = 2;
        constexpr int32_t kIntPropertyClassObjectIndex = 539;
        constexpr int32_t kBoolPropertyClassNameIndex = 3;
        constexpr int32_t kObjectPropertyClassNameIndex = 5;
        constexpr int32_t kObjectPropertyClassObjectIndex = 534;

        constexpr int32_t kForPCNameIndex = 18805;
        constexpr int32_t kForCharacterNameIndex = 17726;
        constexpr int32_t kBForceNameIndex = 18793;
        constexpr int32_t kReturnValueNameIndex = 17716;
        constexpr int32_t kVariantIndexNameIndex = 22292;
        constexpr int32_t kBForceSetNameIndex = 22388;
        constexpr int32_t kPinCodeNameIndex = 22699;

        constexpr size_t kObjectPropertySize = 0x8;
        constexpr size_t kBoolPropertySize = 0x1;
        constexpr size_t kIntPropertySize = 0x4;
        constexpr int32_t kAnyObjectIndex = -1;

        struct StructureFieldSpec
        {
            StructureField Field;
            int32_t NameIndex;
            int32_t Offset;
            size_t Size;
            int32_t ClassNameIndex;
            int32_t ClassObjectIndex;
            bool Sensitive;
            bool ExposesRange;
        };

        struct StructureFunctionSpec
        {
            StructureFunction Function;
            int32_t NameIndex;
            int32_t OuterNameIndex;
            uint16_t NumParms;
            uint16_t ParmsSize;
            uint16_t ReturnValueOffset;
            const StructureFieldSpec* Fields;
            size_t FieldCount;
        };

        constexpr std::array<StructureFieldSpec, 2> kForPCReturnFields{{
            {StructureField::ForPC,
             kForPCNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             false,
             false},
            {StructureField::ReturnValue,
             kReturnValueNameIndex,
             0x08,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kAnyObjectIndex,
             false,
             true},
        }};

        constexpr std::array<StructureFieldSpec, 2> kVerifyPinCodeFields{{
            {StructureField::PinCode,
             kPinCodeNameIndex,
             0x00,
             kIntPropertySize,
             kIntPropertyClassNameIndex,
             kIntPropertyClassObjectIndex,
             true,
             false},
            {StructureField::ReturnValue,
             kReturnValueNameIndex,
             0x04,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kAnyObjectIndex,
             false,
             true},
        }};

        constexpr std::array<StructureFieldSpec, 3> kSetVariantFields{{
            {StructureField::VariantIndex,
             kVariantIndexNameIndex,
             0x00,
             kIntPropertySize,
             kIntPropertyClassNameIndex,
             kIntPropertyClassObjectIndex,
             false,
             true},
            {StructureField::BForceSet,
             kBForceSetNameIndex,
             0x04,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kAnyObjectIndex,
             false,
             true},
            {StructureField::ReturnValue,
             kReturnValueNameIndex,
             0x05,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kAnyObjectIndex,
             false,
             true},
        }};

        constexpr std::array<StructureFieldSpec, 4> kCanSeatFields{{
            {StructureField::ForPC,
             kForPCNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             false,
             false},
            {StructureField::ForCharacter,
             kForCharacterNameIndex,
             0x08,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             false,
             false},
            {StructureField::BForce,
             kBForceNameIndex,
             0x10,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kAnyObjectIndex,
             false,
             true},
            {StructureField::ReturnValue,
             kReturnValueNameIndex,
             0x11,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kAnyObjectIndex,
             false,
             true},
        }};

        constexpr StructureFunctionSpec kAllowStructureAccessSpec{
            StructureFunction::AllowStructureAccess,
            kAllowStructureAccessNameIndex,
            kPrimalStructureNameIndex,
            2,
            0x09,
            0x08,
            kForPCReturnFields.data(),
            kForPCReturnFields.size(),
        };

        constexpr StructureFunctionSpec kIsAllowedToDemolishSpec{
            StructureFunction::IsAllowedToDemolish,
            kIsAllowedToDemolishNameIndex,
            kPrimalStructureNameIndex,
            2,
            0x09,
            0x08,
            kForPCReturnFields.data(),
            kForPCReturnFields.size(),
        };

        constexpr StructureFunctionSpec kAllowToggleActivationSpec{
            StructureFunction::AllowToggleActivation,
            kAllowToggleActivationNameIndex,
            kPrimalStructureItemContainerNameIndex,
            2,
            0x09,
            0x08,
            kForPCReturnFields.data(),
            kForPCReturnFields.size(),
        };

        constexpr StructureFunctionSpec kVerifyPinCodeSpec{
            StructureFunction::VerifyPinCode,
            kVerifyPinCodeNameIndex,
            kPrimalStructureItemContainerNameIndex,
            2,
            0x05,
            0x04,
            kVerifyPinCodeFields.data(),
            kVerifyPinCodeFields.size(),
        };

        constexpr StructureFunctionSpec kSetVariantSpec{
            StructureFunction::SetVariant,
            kSetVariantNameIndex,
            kPrimalStructureNameIndex,
            3,
            0x06,
            0x05,
            kSetVariantFields.data(),
            kSetVariantFields.size(),
        };

        constexpr StructureFunctionSpec kCanSeatSpec{
            StructureFunction::CanSeat,
            kCanSeatNameIndex,
            kPrimalStructureSeatingNameIndex,
            4,
            0x12,
            0x11,
            kCanSeatFields.data(),
            kCanSeatFields.size(),
        };

        const StructureFunctionSpec* FindSpec(int32_t nameIndex)
        {
            switch (nameIndex)
            {
            case kAllowStructureAccessNameIndex:
                return &kAllowStructureAccessSpec;
            case kIsAllowedToDemolishNameIndex:
                return &kIsAllowedToDemolishSpec;
            case kSetVariantNameIndex:
                return &kSetVariantSpec;
            case kAllowToggleActivationNameIndex:
                return &kAllowToggleActivationSpec;
            case kVerifyPinCodeNameIndex:
                return &kVerifyPinCodeSpec;
            case kCanSeatNameIndex:
                return &kCanSeatSpec;
            default:
                return nullptr;
            }
        }

        RuntimeReflection::ReadResult ValidateGate(const RuntimeReflection::ReadOptions& options)
        {
            if (!options.Enabled)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Disabled,
                                                           "structure reflection is disabled");
            if (!options.Layout)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "no supported layout for structure reflection");
            if (options.Layout->BinarySha256 != RuntimeReflection::kSupportedShooterGameServerSha256)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "structure reflection constants do not match binary layout");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionShape(const RuntimeReflection::UFunctionView& function,
                                                            const StructureFunctionSpec& spec)
        {
            if (function.Object.NamePrivate.ComparisonIndex != spec.NameIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "UFunction FName index does not match structure spec");
            if (function.NumParms != spec.NumParms)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "structure UFunction NumParms mismatch");
            if (function.ParmsSize != spec.ParmsSize)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "structure UFunction ParmsSize mismatch");
            if (function.ReturnValueOffset != spec.ReturnValueOffset)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "structure UFunction ReturnValueOffset mismatch");
            if (function.Parameters.size() != spec.FieldCount)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "structure property count mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionOuter(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UFunctionView& function,
                                                            const StructureFunctionSpec& spec)
        {
            if (!function.Object.OuterPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "structure UFunction has null outer");

            RuntimeReflection::UObjectView outer;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, function.Object.OuterPrivate, outer);
            if (!result)
                return result;

            if (outer.NamePrivate.ComparisonIndex != spec.OuterNameIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "structure UFunction outer FName index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidatePropertyClass(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UPropertyView& property,
                                                            const StructureFieldSpec& spec)
        {
            if (!property.Object.ClassPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "structure property has null class");

            RuntimeReflection::UObjectView propertyClass;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, property.Object.ClassPrivate, propertyClass);
            if (!result)
                return result;

            if (propertyClass.NamePrivate.ComparisonIndex != spec.ClassNameIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "structure property class FName index mismatch");
            if (spec.ClassObjectIndex != kAnyObjectIndex &&
                propertyClass.InternalIndex != spec.ClassObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "structure property class object index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateProperty(const RuntimeReflection::MemoryReader& reader,
                                                       const RuntimeReflection::FieldLayout& layout,
                                                       const RuntimeReflection::UPropertyView& property,
                                                       const StructureFieldSpec& spec)
        {
            if (property.Object.NamePrivate.ComparisonIndex != spec.NameIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "structure property FName index mismatch");
            if (property.OffsetInternal != spec.Offset)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "structure property offset mismatch");
            if (property.ByteSize != spec.Size)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "structure property size mismatch");
            if (property.ElementSize != static_cast<int32_t>(spec.Size))
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "structure property ElementSize mismatch");
            if (property.ArrayDim != 1)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "structure property ArrayDim mismatch");

            return ValidatePropertyClass(reader, layout, property, spec);
        }
    }

    RuntimeReflection::ReadResult TryIdentifyStructureInvocation(const RuntimeReflection::MemoryReader& reader,
                                                                 const RuntimeReflection::ReadOptions& options,
                                                                 const void* function,
                                                                 const void* params,
                                                                 StructureInvocation& out)
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

        const StructureFunctionSpec* spec = FindSpec(functionObject.NamePrivate.ComparisonIndex);
        if (!spec)
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                       "UFunction FName index is not a supported structure target");

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

        StructureInvocation value;
        value.Function = spec->Function;
        value.FunctionNameIndex = spec->NameIndex;
        value.OuterNameIndex = spec->OuterNameIndex;
        value.HasParameterRanges = params != nullptr;
        if (spec->FieldCount > value.Fields.capacity())
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::OutOfBounds,
                                                       "structure field count exceeds storage capacity");
        value.Fields.reserve(spec->FieldCount);

        for (size_t i = 0; i < spec->FieldCount; ++i)
        {
            const StructureFieldSpec& fieldSpec = spec->Fields[i];
            const RuntimeReflection::UPropertyView& property = reflectedFunction.Parameters[i];
            if (RuntimeReflection::ReadResult result =
                    ValidateProperty(reader, *options.Layout, property, fieldSpec);
                !result)
            {
                return result;
            }

            StructureFieldRange field;
            field.Field = fieldSpec.Field;
            field.PropertyNameIndex = fieldSpec.NameIndex;
            field.Offset = fieldSpec.Offset;
            field.Size = fieldSpec.Size;
            field.Sensitive = fieldSpec.Sensitive;
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
