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
    };

    enum class ChatField
    {
        MessageText,
        SteamID,
        PlayerName,
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
        std::vector<ChatFieldRange> Fields;
    };

    RuntimeReflection::ReadResult TryIdentifyChatInvocation(const RuntimeReflection::MemoryReader& reader,
                                                            const RuntimeReflection::ReadOptions& options,
                                                            const void* function,
                                                            const void* params,
                                                            ChatInvocation& out);
}
