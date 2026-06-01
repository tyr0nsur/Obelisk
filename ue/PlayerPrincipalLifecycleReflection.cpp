#include "PlayerPrincipalLifecycleReflection.h"

#include <array>
#include <cstring>
#include <utility>

namespace Obelisk::UE::PlayerPrincipalLifecycleReflection
{
    namespace
    {
        constexpr int32_t kHandleNewPlayerNameIndex = 2170;
        constexpr int32_t kOnLogoutNameIndex = 2384;
        constexpr int32_t kShooterGameModeNameIndex = 9755;
        constexpr int32_t kShooterGameModeObjectIndex = 411;

        constexpr int32_t kBoolPropertyClassNameIndex = 3;
        constexpr int32_t kObjectPropertyClassNameIndex = 5;
        constexpr int32_t kFunctionClassNameIndex = 10650;
        constexpr int32_t kBoolPropertyClassObjectIndex = 532;
        constexpr int32_t kObjectPropertyClassObjectIndex = 534;
        constexpr int32_t kFunctionClassObjectIndex = 518;

        constexpr int32_t kReturnValueNameIndex = 17716;
        constexpr int32_t kPlayerDataNameIndex = 21307;
        constexpr int32_t kPlayerCharacterNameIndex = 22961;
        constexpr int32_t kNewPlayerNameIndex = 28411;
        constexpr int32_t kBIsFromLoginNameIndex = 28509;
        constexpr int32_t kExitingNameIndex = 28543;

        constexpr uint32_t kLifecycleFunctionFlags = 0x0c020c00;
        constexpr size_t kObjectPropertySize = 0x8;
        constexpr size_t kBoolPropertySize = 0x1;

        constexpr uint64_t kObjectInputPropertyFlags = 0x1040000280;
        constexpr uint64_t kBoolInputPropertyFlags = 0x1040000280;
        constexpr uint64_t kBoolReturnPropertyFlags = 0x1040000780;
        constexpr size_t kBoolPropertyFieldSizeOffset = 0x70;
        constexpr size_t kBoolPropertyByteOffsetOffset = 0x71;
        constexpr size_t kBoolPropertyByteMaskOffset = 0x72;
        constexpr size_t kBoolPropertyFieldMaskOffset = 0x73;
        constexpr uint8_t kBoolFieldSize = 0x01;
        constexpr uint8_t kBoolByteOffset = 0x00;
        constexpr uint8_t kBoolByteMask = 0x01;
        constexpr uint8_t kBoolFieldMask = 0xff;

        struct LifecycleFieldSpec
        {
            LifecycleField Field;
            int32_t NameIndex;
            int32_t Offset;
            size_t Size;
            int32_t ClassNameIndex;
            int32_t ClassObjectIndex;
            uint64_t PropertyFlags;
            bool ExposesRange;
            bool Redacted;
        };

        struct LifecycleFunctionSpec
        {
            LifecycleFunction Function;
            int32_t NameIndex;
            int32_t OuterNameIndex;
            int32_t OuterObjectIndex;
            uint32_t FunctionFlags;
            uint16_t NumParms;
            uint16_t ParmsSize;
            uint16_t ReturnValueOffset;
            const LifecycleFieldSpec* Fields;
            size_t FieldCount;
        };

        struct BoolPropertyMetadata
        {
            uint8_t FieldSize = 0;
            uint8_t ByteOffset = 0;
            uint8_t ByteMask = 0;
            uint8_t FieldMask = 0;
        };

        constexpr std::array<LifecycleFieldSpec, 5> kHandleNewPlayerFields{{
            {LifecycleField::NewPlayer,
             kNewPlayerNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags,
             false,
             true},
            {LifecycleField::PlayerData,
             kPlayerDataNameIndex,
             0x08,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags,
             false,
             true},
            {LifecycleField::PlayerCharacter,
             kPlayerCharacterNameIndex,
             0x10,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags,
             false,
             true},
            {LifecycleField::BIsFromLogin,
             kBIsFromLoginNameIndex,
             0x18,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolInputPropertyFlags,
             true,
             false},
            {LifecycleField::ReturnValue,
             kReturnValueNameIndex,
             0x19,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolReturnPropertyFlags,
             true,
             false},
        }};

        constexpr std::array<LifecycleFieldSpec, 1> kOnLogoutFields{{
            {LifecycleField::Exiting,
             kExitingNameIndex,
             0x00,
             kObjectPropertySize,
             kObjectPropertyClassNameIndex,
             kObjectPropertyClassObjectIndex,
             kObjectInputPropertyFlags,
             false,
             true},
        }};

        constexpr LifecycleFunctionSpec kHandleNewPlayerSpec{
            LifecycleFunction::HandleNewPlayer,
            kHandleNewPlayerNameIndex,
            kShooterGameModeNameIndex,
            kShooterGameModeObjectIndex,
            kLifecycleFunctionFlags,
            5,
            0x1a,
            0x19,
            kHandleNewPlayerFields.data(),
            kHandleNewPlayerFields.size(),
        };

        constexpr LifecycleFunctionSpec kOnLogoutSpec{
            LifecycleFunction::OnLogout,
            kOnLogoutNameIndex,
            kShooterGameModeNameIndex,
            kShooterGameModeObjectIndex,
            kLifecycleFunctionFlags,
            1,
            0x08,
            0xffff,
            kOnLogoutFields.data(),
            kOnLogoutFields.size(),
        };

        const LifecycleFunctionSpec* FindSpec(int32_t nameIndex)
        {
            switch (nameIndex)
            {
            case kHandleNewPlayerNameIndex:
                return &kHandleNewPlayerSpec;
            case kOnLogoutNameIndex:
                return &kOnLogoutSpec;
            default:
                return nullptr;
            }
        }

        RuntimeReflection::ReadResult ValidateGate(const RuntimeReflection::ReadOptions& options)
        {
            if (!options.Enabled)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Disabled,
                                                           "player principal lifecycle reflection is disabled");
            if (!options.Layout)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "no supported layout for player principal lifecycle reflection");
            const RuntimeReflection::FieldLayout* supportedLayout =
                RuntimeReflection::FindSupportedLayout(RuntimeReflection::kSupportedShooterGameServerSha256);
            if (options.Layout != supportedLayout)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "player principal lifecycle constants do not match binary layout");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ReadByteAt(const RuntimeReflection::MemoryReader& reader,
                                                 const void* base,
                                                 size_t offset,
                                                 uint8_t& out)
        {
            if (!base)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::InvalidArgument,
                                                           "null lifecycle bool property base");
            const auto* address = reinterpret_cast<const uint8_t*>(base) + offset;
            if (!reader.CanRead(address, sizeof(uint8_t)))
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Unreadable,
                                                           "lifecycle bool property metadata is unreadable");
            std::memcpy(&out, address, sizeof(uint8_t));
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ReadBoolPropertyMetadata(const RuntimeReflection::MemoryReader& reader,
                                                               const RuntimeReflection::UPropertyView& property,
                                                               BoolPropertyMetadata& out)
        {
            BoolPropertyMetadata value;
            if (RuntimeReflection::ReadResult result =
                    ReadByteAt(reader, property.Address, kBoolPropertyFieldSizeOffset, value.FieldSize);
                !result)
            {
                return result;
            }
            if (RuntimeReflection::ReadResult result =
                    ReadByteAt(reader, property.Address, kBoolPropertyByteOffsetOffset, value.ByteOffset);
                !result)
            {
                return result;
            }
            if (RuntimeReflection::ReadResult result =
                    ReadByteAt(reader, property.Address, kBoolPropertyByteMaskOffset, value.ByteMask);
                !result)
            {
                return result;
            }
            if (RuntimeReflection::ReadResult result =
                    ReadByteAt(reader, property.Address, kBoolPropertyFieldMaskOffset, value.FieldMask);
                !result)
            {
                return result;
            }
            out = value;
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionClass(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UFunctionView& function)
        {
            if (!function.Object.ClassPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle UFunction has null class");

            RuntimeReflection::UObjectView functionClass;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, function.Object.ClassPrivate, functionClass);
            if (!result)
                return result;

            if (functionClass.NamePrivate.ComparisonIndex != kFunctionClassNameIndex ||
                functionClass.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle UFunction class FName mismatch");
            if (functionClass.InternalIndex != kFunctionClassObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle UFunction class object index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionShape(const RuntimeReflection::UFunctionView& function,
                                                            const LifecycleFunctionSpec& spec)
        {
            if (function.Object.NamePrivate.ComparisonIndex != spec.NameIndex ||
                function.Object.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "UFunction FName does not match lifecycle spec");
            if (function.FunctionFlags != spec.FunctionFlags)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle UFunction FunctionFlags mismatch");
            if (function.NumParms != spec.NumParms)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle UFunction NumParms mismatch");
            if (function.ParmsSize != spec.ParmsSize)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle UFunction ParmsSize mismatch");
            if (function.ReturnValueOffset != spec.ReturnValueOffset)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle UFunction ReturnValueOffset mismatch");
            if (function.Parameters.size() != spec.FieldCount)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle property count mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionOuter(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UFunctionView& function,
                                                            const LifecycleFunctionSpec& spec)
        {
            if (!function.Object.OuterPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle UFunction has null outer");

            RuntimeReflection::UObjectView outer;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, function.Object.OuterPrivate, outer);
            if (!result)
                return result;

            if (outer.NamePrivate.ComparisonIndex != spec.OuterNameIndex ||
                outer.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle UFunction outer FName mismatch");
            if (outer.InternalIndex != spec.OuterObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle UFunction outer object index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidatePropertyClass(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UPropertyView& property,
                                                            const LifecycleFieldSpec& spec)
        {
            if (!property.Object.ClassPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle property has null class");

            RuntimeReflection::UObjectView propertyClass;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, property.Object.ClassPrivate, propertyClass);
            if (!result)
                return result;

            if (propertyClass.NamePrivate.ComparisonIndex != spec.ClassNameIndex ||
                propertyClass.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle property class FName mismatch");
            if (propertyClass.InternalIndex != spec.ClassObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle property class object index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateProperty(const RuntimeReflection::MemoryReader& reader,
                                                       const RuntimeReflection::FieldLayout& layout,
                                                       const RuntimeReflection::UPropertyView& property,
                                                       const LifecycleFieldSpec& spec)
        {
            if (property.Object.NamePrivate.ComparisonIndex != spec.NameIndex ||
                property.Object.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle property FName mismatch");
            if (property.OffsetInternal != spec.Offset)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle property offset mismatch");
            if (property.ByteSize != spec.Size)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle property size mismatch");
            if (property.ElementSize != static_cast<int32_t>(spec.Size))
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle property ElementSize mismatch");
            if (property.ArrayDim != 1)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle property ArrayDim mismatch");
            if (property.PropertyFlags != spec.PropertyFlags)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle property flags mismatch");
            if (RuntimeReflection::ReadResult result = ValidatePropertyClass(reader, layout, property, spec); !result)
                return result;
            if (spec.ClassNameIndex == kBoolPropertyClassNameIndex)
            {
                BoolPropertyMetadata metadata;
                if (RuntimeReflection::ReadResult result = ReadBoolPropertyMetadata(reader, property, metadata);
                    !result)
                {
                    return result;
                }
                if (metadata.FieldSize != kBoolFieldSize ||
                    metadata.ByteOffset != kBoolByteOffset ||
                    metadata.ByteMask != kBoolByteMask ||
                    metadata.FieldMask != kBoolFieldMask)
                {
                    return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                               "lifecycle bool property metadata mismatch");
                }
            }
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateCanonicalCopiedBool(const RuntimeReflection::ParamRange& range)
        {
            if (!range.Data || range.Size != sizeof(uint8_t))
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle bool range is not a single byte");

            uint8_t value = 0;
            std::memcpy(&value, range.Data, sizeof(value));
            if (value > 1)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "lifecycle bool byte is not canonical");
            return RuntimeReflection::ReadResult::Ok();
        }
    }

    RuntimeReflection::ReadResult TryIdentifyLifecycleInvocation(
        const RuntimeReflection::MemoryReader& reader,
        const RuntimeReflection::ReadOptions& options,
        const void* function,
        const void* params,
        LifecycleInvocation& out)
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

        const LifecycleFunctionSpec* spec = FindSpec(functionObject.NamePrivate.ComparisonIndex);
        if (!spec)
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                       "UFunction FName index is not a supported lifecycle target");

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

        LifecycleInvocation value;
        value.Function = spec->Function;
        value.FunctionNameIndex = spec->NameIndex;
        value.OuterNameIndex = spec->OuterNameIndex;
        value.HasParameterRanges = params != nullptr;
        if (spec->FieldCount > value.Fields.capacity())
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::OutOfBounds,
                                                       "lifecycle field count exceeds storage capacity");
        value.Fields.reserve(spec->FieldCount);

        for (size_t i = 0; i < spec->FieldCount; ++i)
        {
            const LifecycleFieldSpec& fieldSpec = spec->Fields[i];
            const RuntimeReflection::UPropertyView& property = reflectedFunction.Parameters[i];
            if (RuntimeReflection::ReadResult result =
                    ValidateProperty(reader, *options.Layout, property, fieldSpec);
                !result)
            {
                return result;
            }

            LifecycleFieldRange field;
            field.Field = fieldSpec.Field;
            field.PropertyNameIndex = fieldSpec.NameIndex;
            field.Offset = fieldSpec.Offset;
            field.Size = fieldSpec.Size;
            field.ExposesRange = fieldSpec.ExposesRange;
            field.Redacted = fieldSpec.Redacted;

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
