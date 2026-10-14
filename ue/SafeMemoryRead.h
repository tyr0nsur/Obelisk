#pragma once

#include <cstddef>

namespace Obelisk::Memory
{
    // Copies through the kernel instead of checking a cached mapping and then
    // dereferencing the source. A failed/partial read may modify destination;
    // callers must not use its contents unless the entire read succeeds.
    // This establishes readable bytes at copy time, not UObject lifetime.
    // Preserves errno so a hook-side check does not change the game's errno.
    bool ReadExact(void* destination, const void* source, size_t size) noexcept;
}
