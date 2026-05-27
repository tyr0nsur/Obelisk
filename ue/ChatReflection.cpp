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
        constexpr int32_t kServerSendChatMessageNameIndex = 2697;
        constexpr int32_t kClientChatMessageNameIndex = 1865;
        constexpr int32_t kClientServerChatDirectMessageNameIndex = 1983;
        constexpr int32_t kClientServerChatMessageNameIndex = 1984;
        constexpr int32_t kSendServerChatMessageNameIndex = 9801;
        constexpr int32_t kOnServerChatMessageDelegateNameIndex = 28549;

        constexpr int32_t kShooterPlayerControllerNameIndex = 101;
        constexpr int32_t kShooterGameModeNameIndex = 9755;
        constexpr int32_t kChatMessageNameIndex = 588;
        constexpr int32_t kMessageTextNameIndex = 21409;
        constexpr int32_t kMessageColorNameIndex = 21408;
        constexpr int32_t kBIsBoldNameIndex = 21407;
        constexpr int32_t kReceiverPlayerIDNameIndex = 28550;
        constexpr int32_t kReceiverTeamIdNameIndex = 28551;
        constexpr int32_t kSendModeNameIndex = 16753;
        constexpr int32_t kSteamIDNameIndex = 20681;
        constexpr int32_t kPlayerNameNameIndex = 16693;

        constexpr int32_t kBytePropertyClassNameIndex = 1;
        constexpr int32_t kBytePropertyClassObjectIndex = 533;
        constexpr int32_t kBoolPropertyClassNameIndex = 3;
        constexpr int32_t kIntPropertyClassNameIndex = 2;
        constexpr int32_t kIntPropertyClassObjectIndex = 539;
        constexpr int32_t kStructPropertyClassNameIndex = 10;
        constexpr int32_t kStrPropertyClassNameIndex = 13;
        constexpr int32_t kStrPropertyClassObjectIndex = 547;

        constexpr size_t kFStringHeaderSize = 0x10;
        constexpr size_t kBytePropertySize = 0x1;
        constexpr size_t kBoolPropertySize = 0x1;
        constexpr size_t kIntPropertySize = 0x4;
        constexpr size_t kStructPropertySize = 0x10;
        constexpr size_t kChatStructPropertySize = 0x90;
        constexpr int32_t kAnyNameIndex = -1;
        constexpr int32_t kAnyObjectIndex = -1;
        constexpr int32_t kAnyOuterNameIndex = -1;

        struct ChatFieldSpec
        {
            ChatField Field;
            int32_t NameIndex;
            int32_t Offset;
            size_t Size;
            int32_t ClassNameIndex;
            int32_t ClassObjectIndex;
        };

        struct ChatFunctionSpec
        {
            ChatFunction Function;
            int32_t NameIndex;
            uint16_t NumParms;
            uint16_t ParmsSize;
            const ChatFieldSpec* Fields;
            size_t FieldCount;
            int32_t OuterNameIndex;
            bool MetadataOnlyCandidate;
        };

        constexpr std::array<ChatFieldSpec, 1> kServerChatFields{{
            {ChatField::MessageText,
             kMessageTextNameIndex,
             0x00,
             kFStringHeaderSize,
             kStrPropertyClassNameIndex,
             kStrPropertyClassObjectIndex},
        }};

        constexpr std::array<ChatFieldSpec, 2> kServerChatToFields{{
            {ChatField::SteamID,
             kSteamIDNameIndex,
             0x00,
             kFStringHeaderSize,
             kStrPropertyClassNameIndex,
             kStrPropertyClassObjectIndex},
            {ChatField::MessageText,
             kMessageTextNameIndex,
             0x10,
             kFStringHeaderSize,
             kStrPropertyClassNameIndex,
             kStrPropertyClassObjectIndex},
        }};

        constexpr std::array<ChatFieldSpec, 2> kServerChatToPlayerFields{{
            {ChatField::PlayerName,
             kPlayerNameNameIndex,
             0x00,
             kFStringHeaderSize,
             kStrPropertyClassNameIndex,
             kStrPropertyClassObjectIndex},
            {ChatField::MessageText,
             kMessageTextNameIndex,
             0x10,
             kFStringHeaderSize,
             kStrPropertyClassNameIndex,
             kStrPropertyClassObjectIndex},
        }};

        constexpr std::array<ChatFieldSpec, 2> kServerSendChatMessageFields{{
            {ChatField::ChatMessage,
             kChatMessageNameIndex,
             0x00,
             kFStringHeaderSize,
             kStrPropertyClassNameIndex,
             kStrPropertyClassObjectIndex},
            {ChatField::SendMode,
             kSendModeNameIndex,
             0x10,
             kBytePropertySize,
             kBytePropertyClassNameIndex,
             kBytePropertyClassObjectIndex},
        }};

        constexpr std::array<ChatFieldSpec, 1> kClientChatMessageFields{{
            {ChatField::Chat,
             kAnyNameIndex,
             0x00,
             kChatStructPropertySize,
             kStructPropertyClassNameIndex,
             kAnyObjectIndex},
        }};

        constexpr std::array<ChatFieldSpec, 3> kClientServerChatMessageFields{{
            {ChatField::MessageText,
             kMessageTextNameIndex,
             0x00,
             kFStringHeaderSize,
             kStrPropertyClassNameIndex,
             kStrPropertyClassObjectIndex},
            {ChatField::MessageColor,
             kAnyNameIndex,
             0x10,
             kStructPropertySize,
             kStructPropertyClassNameIndex,
             kAnyObjectIndex},
            {ChatField::BIsBold,
             kAnyNameIndex,
             0x20,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kAnyObjectIndex},
        }};

        constexpr std::array<ChatFieldSpec, 5> kSendServerChatMessageFields{{
            {ChatField::MessageText,
             kMessageTextNameIndex,
             0x00,
             kFStringHeaderSize,
             kStrPropertyClassNameIndex,
             kStrPropertyClassObjectIndex},
            {ChatField::MessageColor,
             kMessageColorNameIndex,
             0x10,
             kStructPropertySize,
             kStructPropertyClassNameIndex,
             kAnyObjectIndex},
            {ChatField::BIsBold,
             kBIsBoldNameIndex,
             0x20,
             kBoolPropertySize,
             kBoolPropertyClassNameIndex,
             kAnyObjectIndex},
            {ChatField::ReceiverTeamId,
             kReceiverTeamIdNameIndex,
             0x24,
             kIntPropertySize,
             kIntPropertyClassNameIndex,
             kIntPropertyClassObjectIndex},
            {ChatField::ReceiverPlayerID,
             kReceiverPlayerIDNameIndex,
             0x28,
             kIntPropertySize,
             kIntPropertyClassNameIndex,
             kIntPropertyClassObjectIndex},
        }};

        constexpr std::array<ChatFieldSpec, 3> kOnServerChatMessageDelegateFields{{
            {ChatField::MessageText,
             kMessageTextNameIndex,
             0x00,
             kFStringHeaderSize,
             kStrPropertyClassNameIndex,
             kStrPropertyClassObjectIndex},
            {ChatField::ReceiverTeamId,
             kReceiverTeamIdNameIndex,
             0x10,
             kIntPropertySize,
             kIntPropertyClassNameIndex,
             kIntPropertyClassObjectIndex},
            {ChatField::ReceiverPlayerID,
             kReceiverPlayerIDNameIndex,
             0x14,
             kIntPropertySize,
             kIntPropertyClassNameIndex,
             kIntPropertyClassObjectIndex},
        }};

        constexpr ChatFunctionSpec kServerChatSpec{
            ChatFunction::ServerChat,
            kServerChatNameIndex,
            1,
            0x10,
            kServerChatFields.data(),
            kServerChatFields.size(),
            kAnyOuterNameIndex,
            false,
        };

        constexpr ChatFunctionSpec kServerChatToSpec{
            ChatFunction::ServerChatTo,
            kServerChatToNameIndex,
            2,
            0x20,
            kServerChatToFields.data(),
            kServerChatToFields.size(),
            kAnyOuterNameIndex,
            false,
        };

        constexpr ChatFunctionSpec kServerChatToPlayerSpec{
            ChatFunction::ServerChatToPlayer,
            kServerChatToPlayerNameIndex,
            2,
            0x20,
            kServerChatToPlayerFields.data(),
            kServerChatToPlayerFields.size(),
            kAnyOuterNameIndex,
            false,
        };

        constexpr ChatFunctionSpec kServerSendChatMessageSpec{
            ChatFunction::ServerSendChatMessage,
            kServerSendChatMessageNameIndex,
            2,
            0x11,
            kServerSendChatMessageFields.data(),
            kServerSendChatMessageFields.size(),
            kAnyOuterNameIndex,
            false,
        };

        constexpr ChatFunctionSpec kClientChatMessageSpec{
            ChatFunction::ClientChatMessage,
            kClientChatMessageNameIndex,
            1,
            0x90,
            kClientChatMessageFields.data(),
            kClientChatMessageFields.size(),
            kShooterPlayerControllerNameIndex,
            true,
        };

        constexpr ChatFunctionSpec kClientServerChatDirectMessageSpec{
            ChatFunction::ClientServerChatDirectMessage,
            kClientServerChatDirectMessageNameIndex,
            3,
            0x21,
            kClientServerChatMessageFields.data(),
            kClientServerChatMessageFields.size(),
            kShooterPlayerControllerNameIndex,
            true,
        };

        constexpr ChatFunctionSpec kClientServerChatMessageSpec{
            ChatFunction::ClientServerChatMessage,
            kClientServerChatMessageNameIndex,
            3,
            0x21,
            kClientServerChatMessageFields.data(),
            kClientServerChatMessageFields.size(),
            kShooterPlayerControllerNameIndex,
            true,
        };

        constexpr ChatFunctionSpec kSendServerChatMessageSpec{
            ChatFunction::SendServerChatMessage,
            kSendServerChatMessageNameIndex,
            5,
            0x2c,
            kSendServerChatMessageFields.data(),
            kSendServerChatMessageFields.size(),
            kShooterGameModeNameIndex,
            true,
        };

        constexpr ChatFunctionSpec kOnServerChatMessageDelegateSpec{
            ChatFunction::OnServerChatMessageDelegate,
            kOnServerChatMessageDelegateNameIndex,
            3,
            0x18,
            kOnServerChatMessageDelegateFields.data(),
            kOnServerChatMessageDelegateFields.size(),
            kShooterGameModeNameIndex,
            true,
        };

        const ChatFunctionSpec* FindSpec(int32_t nameIndex)
        {
            switch (nameIndex)
            {
            case kClientChatMessageNameIndex:
                return &kClientChatMessageSpec;
            case kClientServerChatDirectMessageNameIndex:
                return &kClientServerChatDirectMessageSpec;
            case kClientServerChatMessageNameIndex:
                return &kClientServerChatMessageSpec;
            case kSendServerChatMessageNameIndex:
                return &kSendServerChatMessageSpec;
            case kOnServerChatMessageDelegateNameIndex:
                return &kOnServerChatMessageDelegateSpec;
            case kServerSendChatMessageNameIndex:
                return &kServerSendChatMessageSpec;
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

        RuntimeReflection::ReadResult ValidateFunctionOuter(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UFunctionView& function,
                                                            const ChatFunctionSpec& spec)
        {
            if (spec.OuterNameIndex == kAnyOuterNameIndex)
                return RuntimeReflection::ReadResult::Ok();
            if (!function.Object.OuterPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "chat UFunction has null outer");

            RuntimeReflection::UObjectView outer;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, function.Object.OuterPrivate, outer);
            if (!result)
                return result;

            if (outer.NamePrivate.ComparisonIndex != spec.OuterNameIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "chat UFunction outer FName index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidatePropertyClass(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::FieldLayout& layout,
                                                            const RuntimeReflection::UPropertyView& property,
                                                            const ChatFieldSpec& spec)
        {
            if (!property.Object.ClassPrivate)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "chat property has null class");

            RuntimeReflection::UObjectView propertyClass;
            RuntimeReflection::ReadResult result =
                RuntimeReflection::TryReadUObject(reader, layout, property.Object.ClassPrivate, propertyClass);
            if (!result)
                return result;

            if (propertyClass.NamePrivate.ComparisonIndex != spec.ClassNameIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "chat property class FName index mismatch");
            if (spec.ClassObjectIndex != kAnyObjectIndex &&
                propertyClass.InternalIndex != spec.ClassObjectIndex)
                return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::Implausible,
                                                           "chat property class object index mismatch");
            return RuntimeReflection::ReadResult::Ok();
        }

        RuntimeReflection::ReadResult ValidateProperty(const RuntimeReflection::MemoryReader& reader,
                                                       const RuntimeReflection::FieldLayout& layout,
                                                       const RuntimeReflection::UPropertyView& property,
                                                       const ChatFieldSpec& spec)
        {
            if (spec.NameIndex != kAnyNameIndex &&
                property.Object.NamePrivate.ComparisonIndex != spec.NameIndex)
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

            return ValidatePropertyClass(reader, layout, property, spec);
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
        if (RuntimeReflection::ReadResult result =
                ValidateFunctionOuter(reader, *options.Layout, reflectedFunction, *spec);
            !result)
        {
            return result;
        }

        ChatInvocation value;
        value.Function = spec->Function;
        value.FunctionNameIndex = spec->NameIndex;
        value.MetadataOnlyCandidate = spec->MetadataOnlyCandidate;
        value.HasParameterRanges = params != nullptr && !value.MetadataOnlyCandidate;
        if (spec->FieldCount > value.Fields.capacity())
            return RuntimeReflection::ReadResult::Fail(RuntimeReflection::ReadStatus::OutOfBounds,
                                                       "chat field count exceeds storage capacity");
        value.Fields.reserve(spec->FieldCount);

        size_t index = 0;
        for (size_t i = 0; i < spec->FieldCount; ++i)
        {
            const ChatFieldSpec& fieldSpec = spec->Fields[i];
            const RuntimeReflection::UPropertyView& property = reflectedFunction.Parameters[index];
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

            if (value.HasParameterRanges)
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
            ++index;
        }

        out = std::move(value);
        return RuntimeReflection::ReadResult::Ok();
    }

    bool TryGetSendMode(const ChatInvocation& invocation, uint8_t& out)
    {
        if (invocation.Function != ChatFunction::ServerSendChatMessage)
            return false;

        for (const ChatFieldRange& field : invocation.Fields)
        {
            if (field.Field != ChatField::SendMode)
                continue;
            if (field.Range.Size != 1 || !field.Range.Data)
                return false;

            out = field.Range.Data[0];
            return true;
        }

        return false;
    }

    const char* SendModeName(uint8_t sendMode)
    {
        switch (sendMode)
        {
        case 0:
            return "GlobalChat";
        case 1:
            return "GlobalTribeChat";
        case 2:
            return "LocalChat";
        case 3:
            return "AllianceChat";
        default:
            return "Unknown";
        }
    }

    bool IsKnownSendMode(uint8_t sendMode)
    {
        return sendMode <= 3;
    }
}
