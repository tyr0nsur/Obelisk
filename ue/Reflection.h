#pragma once

#include <cstdint>
#include <cstddef>
#include <string>

namespace Obelisk::UE
{
    struct FString
    {
        void* Data;
        int32_t ArrayNum;
        int32_t ArrayMax;

        bool IsSane(int32_t maxChars = 2048) const
        {
            if (!Data || ArrayNum <= 0 || ArrayNum > maxChars)
                return false;
            if (ArrayMax < ArrayNum || ArrayMax > maxChars * 2)
                return false;

            uintptr_t p = reinterpret_cast<uintptr_t>(Data);
            return p >= 0x10000 && p <= 0x00007FFFFFFFFFFF;
        }

        template <typename CharT>
        std::string ToAsciiString(size_t maxChars = 1024) const
        {
            std::string result;
            if (!IsSane())
                return result;

            const CharT* ptr = static_cast<const CharT*>(Data);
            int32_t limit = ArrayNum < static_cast<int32_t>(maxChars) ? ArrayNum : static_cast<int32_t>(maxChars);
            for (int32_t i = 0; i < limit; ++i)
            {
                if (ptr[i] == 0)
                    break;
                result += ptr[i] < 0x80 ? static_cast<char>(ptr[i]) : '?';
            }
            return result;
        }
    };

    struct FName
    {
        int32_t ComparisonIndex;
        int32_t Number;
    };

    struct UObjectBase
    {
        void** VTable;
        int32_t ObjectFlags;
        int32_t InternalIndex;
        void* ClassPrivate;
        FName NamePrivate;
    };

    struct UObjectProbe : UObjectBase
    {
        void* OuterPrivate;
    };

    // Candidate UE4 UFunction tail fields. Offsets are not accepted as facts until
    // validated against the target ARK binary; use only for bounded research logging.
    struct UFunctionMetadataProbe
    {
        uint64_t CandidateFunctionFlags;
        uint16_t CandidateNumParms;
        uint16_t CandidateParmsSize;
        uint16_t CandidateReturnValueOffset;
        uint16_t CandidateRpcId;
        uint16_t CandidateRpcResponseId;
    };
}
