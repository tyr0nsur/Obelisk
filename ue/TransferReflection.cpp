#include "TransferReflection.h"

#include <array>
#include <cstring>
#include <limits>
#include <utility>

namespace Obelisk::UE::TransferReflection
{
    namespace
    {
        constexpr int32_t kServerTransferredPlayerConfirmationResultNameIndex = 2759;
        constexpr int32_t kBoolPropertyClassNameIndex = 3;
        constexpr int32_t kFunctionClassNameIndex = 10650;
        constexpr int32_t kShooterPlayerControllerNameIndex = 6721;
        constexpr int32_t kBAcceptNameIndex = 21480;
        constexpr int32_t kServerTransferredPlayerConfirmationResultObjectIndex = 10494;
        constexpr int32_t kBAcceptObjectIndex = 10495;
        constexpr int32_t kBoolPropertyClassObjectIndex = 532;
        constexpr int32_t kFunctionClassObjectIndex = 518;
        constexpr int32_t kShooterPlayerControllerObjectIndex = 50;

        constexpr size_t kBoolPropertySize = 0x1;
        constexpr uint64_t kBoolInputPropertyFlags = 0x1040000280;
        constexpr size_t kBoolPropertyFieldSizeOffset = 0x70;
        constexpr size_t kBoolPropertyByteOffsetOffset = 0x71;
        constexpr size_t kBoolPropertyByteMaskOffset = 0x72;
        constexpr size_t kBoolPropertyFieldMaskOffset = 0x73;

        struct TransferFieldSpec
        {
            TransferField Field;
            int32_t NameIndex;
            int32_t ObjectIndex;
            int32_t Offset;
            size_t Size;
            int32_t ClassNameIndex;
            int32_t ClassObjectIndex;
            uint64_t PropertyFlags;
            uint8_t BoolFieldSize;
            uint8_t BoolByteOffset;
            uint8_t BoolByteMask;
            uint8_t BoolFieldMask;
            bool NativeBool;
            bool ExposesRange;
        };

        struct TransferFunctionSpec
        {
            TransferFunction Function;
            int32_t NameIndex;
            int32_t ObjectIndex;
            int32_t OuterNameIndex;
            int32_t OuterObjectIndex;
            uint16_t NumParms;
            uint16_t ParmsSize;
            uint16_t ReturnValueOffset;
            uint32_t FunctionFlags;
            const TransferFieldSpec* Fields;
            size_t FieldCount;
        };

        struct BoolPropertyMetadata
        {
            uint8_t FieldSize = 0;
            uint8_t ByteOffset = 0;
            uint8_t ByteMask = 0;
            uint8_t FieldMask = 0;
        };

        constexpr std::array<TransferFieldSpec, 1> kServerTransferredPlayerConfirmationResultFields{{
            {TransferField::BAccept,
             kBAcceptNameIndex,
             kBAcceptObjectIndex,
             0x00,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kBoolPropertyClassObjectIndex,
             kBoolInputPropertyFlags,
             0x01,
             0x00,
             0x01,
             0xff,
             false,
             true},
        }};

        constexpr TransferFunctionSpec kServerTransferredPlayerConfirmationResultSpec{
            TransferFunction::ServerTransferredPlayerConfirmationResult,
            kServerTransferredPlayerConfirmationResultNameIndex,
            kServerTransferredPlayerConfirmationResultObjectIndex,
            kShooterPlayerControllerNameIndex,
            kShooterPlayerControllerObjectIndex,
            1,
            0x01,
            0xffff,
            0x220cc0,
            kServerTransferredPlayerConfirmationResultFields.data(),
            kServerTransferredPlayerConfirmationResultFields.size(),
        };

        const TransferFunctionSpec* FindSpec(int32_t nameIndex)
        {
            if (nameIndex == kServerTransferredPlayerConfirmationResultNameIndex)
                return &kServerTransferredPlayerConfirmationResultSpec;
            return nullptr;
        }

        bool AddWouldOverflow(size_t a, size_t b)
        {
            return a > std::numeric_limits<size_t>::max() - b;
        }

        RuntimeReflection::ReadResult ReadByteAt(const RuntimeReflection::MemoryReader& reader,
                                                 const void* base,
                                                 size_t offset,
                                                 uint8_t& out)
        {
            if (!base)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::InvalidArgument,
                                                           "null transfer bool property pointer");
            if (AddWouldOverflow(reinterpret_cast<size_t>(base), offset))
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::OutOfBounds,
                                                           "transfer bool property metadata address overflow");

            const auto* address = reinterpret_cast<const uint8_t*>(base) + offset;
            if (!reader.CanRead(address, sizeof(out)))
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Unreadable,
                                                           "transfer bool property metadata is unreadable");

            std::memcpy(&out, address, sizeof(out));
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

        RuntimeReflection::ReadResult ValidateGate(const RuntimeReflection::ReadOptions& options)
        {
            if (!options.Enabled)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Disabled,
                                                           "transfer reflection is disabled");
            if (!options.Layout)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "no supported layout for transfer reflection");
            if (options.Layout->BinarySha256 != RuntimeReflection::kSupportedShooterGameServerSha256)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "transfer reflection constants do not match binary layout");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionClass(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UFunctionView& function)
        {
            if (!function.Object.ClassPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer UFunction has null class");

            RuntimeReflection::UObjectView functionClass;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, function.Object.ClassPrivate, functionClass);
            if (!result)
                return result;

            if (functionClass.NamePrivate.ComparisonIndex != kFunctionClassNameIndex ||
                functionClass.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer UFunction class FName mismatch");
            if (functionClass.InternalIndex != kFunctionClassObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer UFunction class object index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionShape(const RuntimeReflection::UFunctionView& function,
                                                            const TransferFunctionSpec& spec)
        {
            if (function.Object.NamePrivate.ComparisonIndex != spec.NameIndex ||
                function.Object.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "UFunction FName does not match transfer spec");
            if (function.Object.InternalIndex != spec.ObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer UFunction object index mismatch");
            if (function.NumParms != spec.NumParms)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer UFunction NumParms mismatch");
            if (function.ParmsSize != spec.ParmsSize)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer UFunction ParmsSize mismatch");
            if (function.ReturnValueOffset != spec.ReturnValueOffset)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer UFunction ReturnValueOffset mismatch");
            if (function.FunctionFlags != spec.FunctionFlags)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer UFunction FunctionFlags mismatch");
            if (function.Parameters.size() != spec.FieldCount)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer property count mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionOuter(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UFunctionView& function,
                                                            const TransferFunctionSpec& spec)
        {
            if (!function.Object.OuterPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer UFunction has null outer");

            RuntimeReflection::UObjectView outer;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, function.Object.OuterPrivate, outer);
            if (!result)
                return result;

            if (outer.NamePrivate.ComparisonIndex != spec.OuterNameIndex ||
                outer.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer UFunction outer FName mismatch");
            if (outer.InternalIndex != spec.OuterObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer UFunction outer object index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidatePropertyClass(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UPropertyView& property,
                                                            const TransferFieldSpec& spec)
        {
            if (!property.Object.ClassPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer property has null class");

            RuntimeReflection::UObjectView propertyClass;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, property.Object.ClassPrivate, propertyClass);
            if (!result)
                return result;

            if (propertyClass.NamePrivate.ComparisonIndex != spec.ClassNameIndex ||
                propertyClass.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer property class FName mismatch");
            if (propertyClass.InternalIndex != spec.ClassObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer property class object index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateBoolPropertyMetadata(const RuntimeReflection::MemoryReader& reader,
                                                                   const RuntimeReflection::UPropertyView& property,
                                                                   const TransferFieldSpec& spec)
        {
            BoolPropertyMetadata metadata;
            if (RuntimeReflection::ReadResult result = ReadBoolPropertyMetadata(reader, property, metadata); !result)
                return result;

            if (metadata.FieldSize != spec.BoolFieldSize)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer bool property field size mismatch");
            if (metadata.ByteOffset != spec.BoolByteOffset)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer bool property byte offset mismatch");
            if (metadata.ByteMask != spec.BoolByteMask)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer bool property byte mask mismatch");
            if (metadata.FieldMask != spec.BoolFieldMask)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer bool property field mask mismatch");

            const bool nativeBool = metadata.FieldSize == 0x01 &&
                                    metadata.ByteMask == 0xff &&
                                    metadata.FieldMask == 0xff;
            if (nativeBool != spec.NativeBool)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer bool property native-bool marker mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateCanonicalCopiedBool(const RuntimeReflection::ParamRange& range)
        {
            if (!range.Data || range.Size != kBoolPropertySize)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::InvalidArgument,
                                                           "transfer copied bool parameter range is invalid");

            uint8_t value = 0;
            std::memcpy(&value, range.Data, sizeof(value));
            if (value > 1)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer copied bool parameter is not canonical");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateProperty(const RuntimeReflection::MemoryReader& reader,
                                                       const RuntimeReflection::FieldLayout& layout,
                                                       const RuntimeReflection::UPropertyView& property,
                                                       const TransferFieldSpec& spec)
        {
            if (property.Object.NamePrivate.ComparisonIndex != spec.NameIndex ||
                property.Object.NamePrivate.Number != 0)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer property FName mismatch");
            if (property.Object.InternalIndex != spec.ObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer property object index mismatch");
            if (property.OffsetInternal != spec.Offset)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer property offset mismatch");
            if (property.ByteSize != spec.Size)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer property size mismatch");
            if (property.PropertyFlags != spec.PropertyFlags)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer property flags mismatch");
            if (property.ElementSize != static_cast<int32_t>(spec.Size))
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer property ElementSize mismatch");
            if (property.ArrayDim != 1)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "transfer property ArrayDim mismatch");

            if (RuntimeReflection::ReadResult result = ValidatePropertyClass(reader, layout, property, spec); !result)
                return result;
            return ValidateBoolPropertyMetadata(reader, property, spec);
        }
    }

    RuntimeReflection::ReadResult TryIdentifyTransferInvocation(const RuntimeReflection::MemoryReader& reader,
                                                                const RuntimeReflection::ReadOptions& options,
                                                                const void* function,
                                                                const void* params,
                                                                TransferInvocation& out)
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

        const TransferFunctionSpec* spec = FindSpec(functionObject.NamePrivate.ComparisonIndex);
        if (!spec)
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                       "UFunction FName index is not a supported transfer target");

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

        TransferInvocation value;
        value.Function = spec->Function;
        value.FunctionNameIndex = spec->NameIndex;
        value.OuterNameIndex = spec->OuterNameIndex;
        value.HasParameterRanges = params != nullptr;
        if (spec->FieldCount > value.Fields.capacity())
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::OutOfBounds,
                                                       "transfer field count exceeds storage capacity");
        value.Fields.reserve(spec->FieldCount);

        for (size_t i = 0; i < spec->FieldCount; ++i)
        {
            const TransferFieldSpec& fieldSpec = spec->Fields[i];
            const RuntimeReflection::UPropertyView& property = reflectedFunction.Parameters[i];
            if (RuntimeReflection::ReadResult result =
                    ValidateProperty(reader, *options.Layout, property, fieldSpec);
                !result)
            {
                return result;
            }

            TransferFieldRange field;
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
                if (RuntimeReflection::ReadResult result = ValidateCanonicalCopiedBool(field.Range); !result)
                    return result;
            }

            value.Fields.push_back(field);
        }

        out = std::move(value);
        return RuntimeReflection::ReadResult::Ok();
    }
}
