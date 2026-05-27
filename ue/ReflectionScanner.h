#pragma once

#include <cstdint>
#include <vector>

namespace Obelisk::UE
{
    class ReflectionScanner
    {
    public:
        static void RunStartupScan();
        static void RunStaticFNameRootProbe(const std::vector<uintptr_t>& slots);
    };
}
