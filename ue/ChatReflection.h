#pragma once

#include "RuntimeReflection.h"

#include <cstddef>
#include <cstdint>
#include <vector>

namespace Obelisk::UE::ChatReflection
{
    enum class ChatFunction
    {
        ServerChat,
        ServerChatTo,
        ServerChatToPlayer,
        ServerSendChatMessage,
        ClientChatMessage,
        ClientServerChatDirectMessage,
        ClientServerChatMessage,
    };

    enum class ChatField
    {
        MessageText,
        SteamID,
        PlayerName,
        ChatMessage,
        SendMode,
        Chat,
        MessageColor,
        BIsBold,
    };

    struct ChatFieldRange
    {
        ChatField Field = ChatField::MessageText;
        int32_t PropertyNameIndex = -1;
        int32_t Offset = -1;
        size_t Size = 0;
        RuntimeReflection::ParamRange Range;
    };

    struct ChatInvocation
    {
        ChatFunction Function = ChatFunction::ServerChat;
        int32_t FunctionNameIndex = -1;
        RuntimeReflection::UFunctionView ReflectedFunction;
        bool HasParameterRanges = false;
        bool MetadataOnlyCandidate = false;
        std::vector<ChatFieldRange> Fields;
    };

    RuntimeReflection::ReadResult TryIdentifyChatInvocation(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::ReadOptions& options,
                                                            const void* function,
                                                            const void* params,
                                                            ChatInvocation& out);

    bool TryGetSendMode(const ChatInvocation& invocation, uint8_t& out);
    const char* SendModeName(uint8_t sendMode);
    bool IsKnownSendMode(uint8_t sendMode);
}
