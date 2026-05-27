#include "ChatReflection.h"

#include <array>
#include <utility>

namespace Obelisk::UE::ChatReflection
{
    namespace
    {
        constexpr int32_t kServerChatNameIndex = 9619;
        constexpr int32_t kServerChatToNameIndex = 9620;
        constexpr int32_t kServerChatToPlayerNameIndex = 9621;

        constexpr int32_t kMessageTextNameIndex = 21409;
        constexpr int32_t kSteamIDNameIndex = 20681;
        constexpr int32_t kPlayerNameNameIndex = 16693;

        constexpr int32_t kStrPropertyClassNameIndex = 13;
        constexpr int32_t kStrPropertyClassObjectIndex = 547;

        constexpr size_t kFStringHeaderSize = 0x10;

        struct ChatFieldSpec
        {
            ChatField Field;
            int32_t NameIndex;
            int32_t Offset;
            size_t Size;
        };

        struct ChatFunctionSpec
        {
            ChatFunction Function;
            int32_t NameIndex;
            uint16_t NumParms;
            uint16_t ParmsSize;
            const ChatFieldSpec* Fields;
            size_t FieldCount;
        };

        constexpr std::array<ChatFieldSpec, 1> kServerChatFields{{
            {ChatField::MessageText, kMessageTextNameIndex, 0x00, kFStringHeaderSize},
        }};

        constexpr std::array<ChatFieldSpec, 2> kServerChatToFields{{
            {ChatField::SteamID, kSteamIDNameIndex, 0x00, kFStringHeaderSize},
            {ChatField::MessageText, kMessageTextNameIndex, 0x10, kFStringHeaderSize},
        }};

        constexpr std::array<ChatFieldSpec, 2> kServerChatToPlayerFields{{
            {ChatField::PlayerName, kPlayerNameNameIndex, 0x00, kFStringHeaderSize},
            {ChatField::MessageText, kMessageTextNameIndex, 0x10, kFStringHeaderSize},
        }};

        constexpr ChatFunctionSpec kServerChatSpec{
            ChatFunction::ServerChat,
            kServerChatNameIndex,
            1,
            0x10,
            kServerChatFields.data(),
            kServerChatFields.size(),
        };

        constexpr ChatFunctionSpec kServerChatToSpec{
            ChatFunction::ServerChatTo,
            kServerChatToNameIndex,
            2,
            0x20,
            kServerChatToFields.data(),
            kServerChatToFields.size(),
        };

        constexpr ChatFunctionSpec kServerChatToPlayerSpec{
            ChatFunction::ServerChatToPlayer,
            kServerChatToPlayerNameIndex,
            2,
            0x20,
            kServerChatToPlayerFields.data(),
            kServerChatToPlayerFields.size(),
        };

        const ChatFunctionSpec* FindSpec(int32_t nameIndex)
        {
            switch (nameIndex)
            {
            case kServerChatNameIndex:
                return &kServerChatSpec;
            case kServerChatToNameIndex:
                return &kServerChatToSpec;
            case kServerChatToPlayerNameIndex:
                return &kServerChatToPlayerSpec;
            default:
                return nullptr;
            }
        }

        RuntimeReflection::ReadResult ValidateGate(const RuntimeReflection::ReadOptions& options)
        {
            if (!options.Enabled)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Disabled,
                                                           "chat reflection is disabled");
            if (!options.Layout)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "no supported layout for chat reflection");
            if (options.Layout->BinarySha256 != RuntimeReflection::kSupportedShooterGameServerSha256)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::UnsupportedLayout,
                                                           "chat reflection constants do not match binary layout");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateFunctionShape(const RuntimeReflection::UFunctionView& function,
                                                            const ChatFunctionSpec& spec)
        {
            if (function.Object.NamePrivate.ComparisonIndex != spec.NameIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "UFunction FName index does not match chat spec");
            if (function.NumParms != spec.NumParms)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "chat UFunction NumParms mismatch");
            if (function.ParmsSize != spec.ParmsSize)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "chat UFunction ParmsSize mismatch");
            if (function.ReturnValueOffset != 0xffff)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "chat UFunction unexpectedly has a return value");
            if (function.Parameters.size() != spec.FieldCount)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "chat property count mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateStrPropertyClass(const RuntimeReflection::MemoryReader& reader,
                                                               const RuntimeReflection::FieldLayout& layout,
                                                               const RuntimeReflection::UPropertyView& property)
        {
            if (!property.Object.ClassPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "chat property has null class");

            RuntimeReflection::UObjectView propertyClass;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, property.Object.ClassPrivate, propertyClass);
            if (!result)
                return result;

            if (propertyClass.NamePrivate.ComparisonIndex != kStrPropertyClassNameIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "chat property class is not StrProperty");
            if (propertyClass.InternalIndex != kStrPropertyClassObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "chat property class object index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateProperty(const RuntimeReflection::MemoryReader& reader,
                                                       const RuntimeReflection::FieldLayout& layout,
                                                       const RuntimeReflection::UPropertyView& property,
                                                       const ChatFieldSpec& spec)
        {
            if (property.Object.NamePrivate.ComparisonIndex != spec.NameIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "chat property FName index mismatch");
            if (property.OffsetInternal != spec.Offset)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "chat property offset mismatch");
            if (property.ByteSize != spec.Size)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "chat property size mismatch");
            if (property.ElementSize != static_cast<int32_t>(spec.Size))
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "chat property ElementSize mismatch");
            if (property.ArrayDim != 1)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "chat property ArrayDim mismatch");

            return ValidateStrPropertyClass(reader, layout, property);
        }
    }

    RuntimeReflection::ReadResult TryIdentifyChatInvocation(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::ReadOptions& options,
                                                            const void* function,
                                                            const void* params,
                                                            ChatInvocation& out)
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

        const ChatFunctionSpec* spec = FindSpec(functionObject.NamePrivate.ComparisonIndex);
        if (!spec)
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                       "UFunction FName index is not a supported chat target");

        RuntimeReflection::UFunctionView reflectedFunction;
        if (RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUFunction(reader, options, function, reflectedFunction);
            !result)
        {
            return result;
        }
        if (RuntimeReflection::ReadResult result = ValidateFunctionShape(reflectedFunction, *spec); !result)
            return result;

        ChatInvocation value;
        value.Function = spec->Function;
        value.FunctionNameIndex = spec->NameIndex;
        value.ReflectedFunction = std::move(reflectedFunction);
        value.HasParameterRanges = params != nullptr;

        size_t index = 0;
        for (size_t i = 0; i < spec->FieldCount; ++i)
        {
            const ChatFieldSpec& fieldSpec = spec->Fields[i];
            const RuntimeReflection::UPropertyView& property = value.ReflectedFunction.Parameters[index];
            if (RuntimeReflection::ReadResult result = ValidateProperty(reader, *options.Layout, property, fieldSpec);
                !result)
            {
                return result;
            }

            ChatFieldRange field;
            field.Field = fieldSpec.Field;
            field.PropertyNameIndex = fieldSpec.NameIndex;
            field.Offset = fieldSpec.Offset;
            field.Size = fieldSpec.Size;

            if (params)
            {
                if (RuntimeReflection::ReadResult result =
                        RuntimeReflection::TryGetParameterRange(reader,
                                                                params,
                                                                value.ReflectedFunction.ParmsSize,
                                                                property,
                                                                fieldSpec.Size,
                                                                field.Range);
                    !result)
                {
                    return result;
                }
            }

            value.Fields.push_back(field);
            ++index;
        }

        out = std::move(value);
        return RuntimeReflection::ReadResult::Ok();
    }
}
