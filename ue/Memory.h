#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace Obelisk::Memory
{
    struct ModuleInfo {
        uintptr_t start;
        uintptr_t end;
        bool found;
    };

    ModuleInfo GetMainModuleInfo();
    void* FindPattern(const std::string& pattern);
    bool IsReadable(void* ptr, size_t size);
}
