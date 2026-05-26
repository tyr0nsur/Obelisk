#pragma once
#include <stdint.h>
#include <string>

namespace Obelisk::UE
{
    struct FString {
        void* Data;
        int32_t ArrayNum;
        int32_t ArrayMax;

        std::string ToString() const {
            if (!Data || ArrayNum <= 0) return "";
            
            std::string result;
            // ARK Linux usually uses 4-byte wchar_t or 2-byte char16_t depending on the compiler flags.
            // Let's assume 2-byte char16_t for TCHAR as it's standard UE4, but we can safely read it
            // by just casting to char* and reading every 2nd or 4th byte if it's wide.
            
            // For safety, let's just read it as 2-byte chars first
            char16_t* ptr = (char16_t*)Data;
            for (int32_t i = 0; i < ArrayNum && i < 1024; ++i) {
                if (ptr[i] == 0) break;
                // Basic ASCII downcast
                result += (char)(ptr[i] & 0xFF);
            }
            return result;
        }
    };

    // Very basic structural representation of PreLogin params
    // Note: FUniqueNetIdRepl size can vary. In 4.5 it's usually small.
    // If we assume standard 64-bit packing:
    // 0x00: FString Options (16 bytes)
    // 0x10: FString Address (16 bytes)
    // 0x20: FUniqueNetIdRepl UniqueId (Size unknown, maybe 16-24 bytes)
    // 0x??: FString ErrorMessage
}
