#pragma once

#include <cstdint>
#include <string>
#include <vector>
#include <cstddef>

namespace Obelisk::Memory
{
    struct ModuleInfo {
        uintptr_t imageBase;
        uintptr_t start;
        uintptr_t end;
        bool found;
    };

    ModuleInfo GetMainModuleInfo();
    void* FindPattern(const std::string& pattern);
    std::vector<void*> FindPatternAll(const std::string& pattern, size_t maxResults = 0);
    __attribute__((visibility("default"))) bool IsReadable(void* ptr, size_t size);
}
