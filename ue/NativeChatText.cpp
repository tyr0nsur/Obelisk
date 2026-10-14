#include "NativeChatText.h"
#include "SafeMemoryRead.h"

namespace Obelisk::UE::NativeChatText
{
    namespace
    {
        constexpr int32_t kMaximumCharacters = 2048;
        bool IsScalar(uint32_t value)
        {
            return value <= 0x10ffff && !(value >= 0xd800 && value <= 0xdfff);
        }
        void Append(std::string& output, uint32_t value)
        {
            if (value < 0x80)
                output.push_back(static_cast<char>(value));
            else if (value < 0x800)
            {
                output.push_back(static_cast<char>(0xc0 | (value >> 6)));
                output.push_back(static_cast<char>(0x80 | (value & 0x3f)));
            }
            else if (value < 0x10000)
            {
                output.push_back(static_cast<char>(0xe0 | (value >> 12)));
                output.push_back(static_cast<char>(0x80 | ((value >> 6) & 0x3f)));
                output.push_back(static_cast<char>(0x80 | (value & 0x3f)));
            }
            else
            {
                output.push_back(static_cast<char>(0xf0 | (value >> 18)));
                output.push_back(static_cast<char>(0x80 | ((value >> 12) & 0x3f)));
                output.push_back(static_cast<char>(0x80 | ((value >> 6) & 0x3f)));
                output.push_back(static_cast<char>(0x80 | (value & 0x3f)));
            }
        }
    }

    bool Decode(const FString* borrowed, std::string& utf8) noexcept
    {
        utf8.clear();
        try
        {
            FString header;
            if (!Memory::ReadExact(&header, borrowed, sizeof(header)) || !header.Data ||
                header.Num < 1 || header.Num > kMaximumCharacters || header.Max < header.Num)
                return false;
            std::vector<char32_t> characters(static_cast<size_t>(header.Num));
            if (!Memory::ReadExact(characters.data(), header.Data, characters.size() * sizeof(char32_t)) ||
                characters.back() != U'\0')
                return false;
            std::string result;
            for (size_t i = 0; i + 1 < characters.size(); ++i)
            {
                const uint32_t value = characters[i];
                if (!value || !IsScalar(value))
                    return false;
                Append(result, value);
            }
            utf8 = std::move(result);
            return true;
        }
        catch (...)
        {
            return false;
        }
    }

    bool Encode(std::string_view utf8, std::vector<char32_t>& owned) noexcept
    {
        owned.clear();
        try
        {
            if (utf8.size() > static_cast<size_t>(kMaximumCharacters) * 4)
                return false;
            std::vector<char32_t> result;
            for (size_t i = 0; i < utf8.size();)
            {
                const auto first = static_cast<unsigned char>(utf8[i++]);
                uint32_t value = 0;
                unsigned int continuation = 0;
                uint32_t minimum = 0;
                if (first < 0x80)
                    value = first;
                else if (first >= 0xc2 && first <= 0xdf)
                {
                    value = first & 0x1f; continuation = 1; minimum = 0x80;
                }
                else if (first >= 0xe0 && first <= 0xef)
                {
                    value = first & 0x0f; continuation = 2; minimum = 0x800;
                }
                else if (first >= 0xf0 && first <= 0xf4)
                {
                    value = first & 7; continuation = 3; minimum = 0x10000;
                }
                else
                    return false;
                if (continuation > utf8.size() - i)
                    return false;
                for (unsigned int j = 0; j < continuation; ++j)
                {
                    const auto next = static_cast<unsigned char>(utf8[i++]);
                    if ((next & 0xc0) != 0x80)
                        return false;
                    value = (value << 6) | (next & 0x3f);
                }
                if (!value || value < minimum || !IsScalar(value) ||
                    result.size() >= static_cast<size_t>(kMaximumCharacters - 1))
                    return false;
                result.push_back(static_cast<char32_t>(value));
            }
            result.push_back(U'\0');
            owned = std::move(result);
            return true;
        }
        catch (...)
        {
            return false;
        }
    }
}
