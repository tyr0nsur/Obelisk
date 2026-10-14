#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

namespace Obelisk::UE::NativeChatText
{
    // Linux TCHAR layout demonstrated in this build's native chat RPC wrappers.
    struct FString
    {
        const char32_t* Data = nullptr;
        int32_t Num = 0;
        int32_t Max = 0;
    };
    static_assert(sizeof(FString) == 16);
    static_assert(sizeof(char32_t) == 4);

    bool Decode(const FString* borrowed, std::string& utf8) noexcept;
    bool Encode(std::string_view utf8, std::vector<char32_t>& owned) noexcept;
}
