#include "ue/SafeMemoryRead.h"

#include <array>
#include <cerrno>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <sys/mman.h>
#include <unistd.h>

namespace
{
    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    void TestExactCopyAndInvalidRanges()
    {
        std::array<uint8_t, 64> source{};
        std::array<uint8_t, 64> destination{};
        for (size_t i = 0; i < source.size(); ++i)
            source[i] = static_cast<uint8_t>(i + 1);
        Require(Obelisk::Memory::ReadExact(destination.data(), source.data(), source.size()),
                "stack memory copy failed");
        Require(source == destination, "copy changed bytes");
        Require(!Obelisk::Memory::ReadExact(destination.data(), nullptr, 1), "null source accepted");
        Require(!Obelisk::Memory::ReadExact(nullptr, source.data(), 1), "null destination accepted");
        Require(!Obelisk::Memory::ReadExact(destination.data(), source.data(), 0), "zero size accepted");
        errno = EBUSY;
        Require(!Obelisk::Memory::ReadExact(destination.data(), reinterpret_cast<void*>(uintptr_t{1}), 1),
                "invalid source accepted");
        Require(errno == EBUSY, "failed read changed game errno");
        Require(!Obelisk::Memory::ReadExact(reinterpret_cast<void*>(uintptr_t{1}), source.data(), 1),
                "invalid destination accepted");
        Require(!Obelisk::Memory::ReadExact(destination.data(), reinterpret_cast<void*>(UINTPTR_MAX), 1),
                "wrapping exclusive end accepted");
        Require(!Obelisk::Memory::ReadExact(destination.data(), reinterpret_cast<void*>(UINTPTR_MAX - 1), 8),
                "source overflow accepted");
        Require(!Obelisk::Memory::ReadExact(reinterpret_cast<void*>(UINTPTR_MAX), source.data(), 1),
                "destination overflow accepted");
    }

    void TestMappingChangesAndPartialCopy()
    {
        const long pageSizeResult = sysconf(_SC_PAGESIZE);
        Require(pageSizeResult > 0, "page size unavailable");
        const size_t pageSize = static_cast<size_t>(pageSizeResult);
        void* mapping = mmap(nullptr, pageSize * 2, PROT_READ | PROT_WRITE,
                             MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        Require(mapping != MAP_FAILED, "mmap failed");
        std::memset(mapping, 0x5a, pageSize * 2);
        std::array<uint8_t, 32> output{};
        Require(Obelisk::Memory::ReadExact(output.data(), mapping, output.size()), "initial read failed");

        Require(mprotect(mapping, pageSize, PROT_NONE) == 0, "mprotect none failed");
        Require(!Obelisk::Memory::ReadExact(output.data(), mapping, output.size()),
                "old readable mapping accepted after mprotect");
        Require(!Obelisk::Memory::ReadExact(mapping, output.data(), output.size()),
                "PROT_NONE destination accepted");
        Require(mprotect(mapping, pageSize, PROT_READ | PROT_WRITE) == 0, "mprotect restore failed");
        Require(Obelisk::Memory::ReadExact(output.data(), mapping, output.size()),
                "restored readable mapping rejected");

        auto* secondPage = static_cast<uint8_t*>(mapping) + pageSize;
        Require(mprotect(secondPage, pageSize, PROT_NONE) == 0, "second page protection failed");
        const void* crossing = secondPage - 16;
        Require(!Obelisk::Memory::ReadExact(output.data(), crossing, output.size()),
                "partial read was reported as an exact read");
        Require(munmap(mapping, pageSize * 2) == 0, "munmap failed");
        Require(!Obelisk::Memory::ReadExact(output.data(), mapping, output.size()),
                "unmapped source accepted");
    }
}

int main()
{
    TestExactCopyAndInvalidRanges();
    TestMappingChangesAndPartialCopy();
    std::cout << "SafeMemoryReadTests passed\n";
    return 0;
}
