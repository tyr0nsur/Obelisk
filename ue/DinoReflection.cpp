#include "DinoReflection.h"

#include <array>
#include <utility>

namespace Obelisk::UE::DinoReflection
{
    namespace
    {
        constexpr int32_t kAddPassengerNameIndex = 8267;
        constexpr int32_t kAllowCarryCharacterNameIndex = 8269;
        constexpr int32_t kPrimalDinoCharacterNameIndex = 8265;

        constexpr int32_t kIntPropertyClassNameIndex = 2;
        constexpr int32_t kBoolPropertyClassNameIndex = 3;
        constexpr int32_t kObjectPropertyClassNameIndex = 5;
        constexpr int32_t kFunctionClassNameIndex = 10650;

        constexpr int32_t kACharacterNameIndex = 4044;
        constexpr int32_t kReturnValueNameIndex = 17716;
        constexpr int32_t kBSkipLineTraceNameIndex = 25580;
        constexpr int32_t kBAllowFlyersAndWaterDinosNameIndex = 25581;
        constexpr int32_t kBForcePassengerNameIndex = 25582;
        constexpr int32_t kPassengerSeatIndexNameIndex = 25583;
        constexpr int32_t kCanCarryPawnNameIndex = 25584;

        constexpr size_t kObjectPropertySize = 0x8;
        constexpr size_t kIntPropertySize = 0x4;
        constexpr size_t kBoolPropertySize = 0x1;

        struct DinoFieldSpec
        {
            DinoField Field;
            int32_t NameIndex;
            int32_t Offset;
            size_t Size;
            int32_t ClassNameIndex;
            bool ExposesRange;
        };

        struct DinoFunctionSpec
        {
            DinoFunction Function;
            int32_t NameIndex;
            int32_t OuterNameIndex;
            uint16_t NumParms;
            uint16_t ParmsSize;
            uint16_t ReturnValueOffset;
            uint32_t FunctionFlags;
            const DinoFieldSpec* Fields;
            size_t FieldCount;
        };

        constexpr std::array<DinoFieldSpec, 6> kAddPassengerFields{{
            {DinoField::ACharacter,
             kACharacterNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             false},
            {DinoField::PassengerSeatIndex,
             kPassengerSeatIndexNameIndex,
             0x08,
             kIntPropertySize,
             kIntPropertyClassNameIndex,
             true},
            {DinoField::BForcePassenger,
             kBForcePassengerNameIndex,
             0x0c,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             true},
            {DinoField::BAllowFlyersAndWaterDinos,
             kBAllowFlyersAndWaterDinosNameIndex,
             0x0d,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             true},
            {DinoField::BSkipLineTrace,
             kBSkipLineTraceNameIndex,
             0x0e,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             true},
            {DinoField::ReturnValue,
             kReturnValueNameIndex,
             0x0f,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             true},
        }};

        constexpr std::array<DinoFieldSpec, 2> kAllowCarryCharacterFields{{
            {DinoField::CanCarryPawn,
             kCanCarryPawnNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             false},
            {DinoField::ReturnValue,
             kReturnValueNameIndex,
             0x08,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             true},
        }};

        constexpr DinoFunctionSpec kAddPassengerSpec{
            DinoFunction::AddPassenger,
            kAddPassengerNameIndex,
            kPrimalDinoCharacterNameIndex,
            6,
            0x10,
            0x0f,
            0x04020401,
            kAddPassengerFields.data(),
            kAddPassengerFields.size(),
        };

        constexpr DinoFunctionSpec kAllowCarryCharacterSpec{
            DinoFunction::AllowCarryCharacter,
            kAllowCarryCharacterNameIndex,
            kPrimalDinoCharacterNameIndex,
            2,
            0x09,
            0x08,
            0x04020400,
            kAllowCarryCharacterFields.data(),
            kAllowCarryCharacterFields.size(),
        };

        const DinoFunctionSpec* FindSpec(int32_t nameIndex)
        {
            switch (nameIndex)
            {
            case kAddPassengerNameIndex:
                return &kAddPassengerSpec;
            case kAllowCarryCharacterNameIndex:
                return &kAllowCarryCharacterSpec;
            default:
                return nullptr;
            }
        }

        RuntimeReflection::ReadResult ValidateGate(const RuntimeReflection::ReadOptions& options)
        {
            if (!options.Enabled)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Disabled,
                                                           "dino reflection is disabled");
            if (!options.Layout)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "no supported layout for dino reflection");
            if (options.Layout->BinarySha256 != RuntimeReflection::kSupportedShooterGameServerSha256)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "dino reflection constants do not match binary layout");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionClass(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UFunctionView& function)
        {
            if (!function.Object.ClassPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "dino UFunction has null class");

            RuntimeReflection::UObjectView functionClass;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, function.Object.ClassPrivate, functionClass);
            if (!result)
                return result;

            if (functionClass.NamePrivate.ComparisonIndex != kFunctionClassNameIndex ||
                functionClass.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "dino UFunction class FName mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionShape(const RuntimeReflection::UFunctionView& function,
                                                            const DinoFunctionSpec& spec)
        {
            if (function.Object.NamePrivate.ComparisonIndex != spec.NameIndex ||
                function.Object.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "UFunction FName does not match dino spec");
            if (function.NumParms != spec.NumParms)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "dino UFunction NumParms mismatch");
            if (function.ParmsSize != spec.ParmsSize)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "dino UFunction ParmsSize mismatch");
            if (function.ReturnValueOffset != spec.ReturnValueOffset)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "dino UFunction ReturnValueOffset mismatch");
            if (function.FunctionFlags != spec.FunctionFlags)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "dino UFunction FunctionFlags mismatch");
            if (function.Parameters.size() != spec.FieldCount)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "dino property count mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionOuter(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UFunctionView& function,
                                                            const DinoFunctionSpec& spec)
        {
            if (!function.Object.OuterPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "dino UFunction has null outer");

            RuntimeReflection::UObjectView outer;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, function.Object.OuterPrivate, outer);
            if (!result)
                return result;

            if (outer.NamePrivate.ComparisonIndex != spec.OuterNameIndex ||
                outer.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "dino UFunction outer FName mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidatePropertyClass(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UPropertyView& property,
                                                            const DinoFieldSpec& spec)
        {
            if (!property.Object.ClassPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "dino property has null class");

            RuntimeReflection::UObjectView propertyClass;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, property.Object.ClassPrivate, propertyClass);
            if (!result)
                return result;

            if (propertyClass.NamePrivate.ComparisonIndex != spec.ClassNameIndex ||
                propertyClass.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "dino property class FName mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateProperty(const RuntimeReflection::MemoryReader& reader,
                                                       const RuntimeReflection::FieldLayout& layout,
                                                       const RuntimeReflection::UPropertyView& property,
                                                       const DinoFieldSpec& spec)
        {
            if (property.Object.NamePrivate.ComparisonIndex != spec.NameIndex ||
                property.Object.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "dino property FName mismatch");
            if (property.OffsetInternal != spec.Offset)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "dino property offset mismatch");
            if (property.ByteSize != spec.Size)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "dino property size mismatch");
            if (property.ElementSize != static_cast<int32_t>(spec.Size))
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "dino property ElementSize mismatch");
            if (property.ArrayDim != 1)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "dino property ArrayDim mismatch");

            return ValidatePropertyClass(reader, layout, property, spec);
        }
    }

    RuntimeReflection::ReadResult TryIdentifyDinoInvocation(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::ReadOptions& options,
                                                            const void* function,
                                                            const void* params,
                                                            DinoInvocation& out)
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

        const DinoFunctionSpec* spec = FindSpec(functionObject.NamePrivate.ComparisonIndex);
        if (!spec)
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                       "UFunction FName index is not a supported dino target");

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

        DinoInvocation value;
        value.Function = spec->Function;
        value.FunctionNameIndex = spec->NameIndex;
        value.OuterNameIndex = spec->OuterNameIndex;
        value.HasParameterRanges = params != nullptr;
        if (spec->FieldCount > value.Fields.capacity())
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::OutOfBounds,
                                                       "dino field count exceeds storage capacity");
        value.Fields.reserve(spec->FieldCount);

        for (size_t i = 0; i < spec->FieldCount; ++i)
        {
            const DinoFieldSpec& fieldSpec = spec->Fields[i];
            const RuntimeReflection::UPropertyView& property = reflectedFunction.Parameters[i];
            if (RuntimeReflection::ReadResult result =
                    ValidateProperty(reader, *options.Layout, property, fieldSpec);
                !result)
            {
                return result;
            }

            DinoFieldRange field;
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
