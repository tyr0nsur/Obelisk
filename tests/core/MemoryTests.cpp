#include "ue/Memory.h"

#include <array>
#include <cstdint>
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

    void TestReadableStackBuffer()
    {
        std::array<uint8_t, 64> buffer{};
        Require(Obelisk::Memory::IsReadable(buffer.data(), buffer.size()),
                "stack buffer should be readable");
    }

    void TestRejectsInvalidInputs()
    {
        std::array<uint8_t, 1> buffer{};
        Require(!Obelisk::Memory::IsReadable(nullptr, 1), "null pointer should be unreadable");
        Require(!Obelisk::Memory::IsReadable(buffer.data(), 0), "zero-size range should be unreadable");
        Require(!Obelisk::Memory::IsReadable(reinterpret_cast<void*>(uintptr_t{0x1}), 1),
                "low invalid pointer should be unreadable");
        Require(!Obelisk::Memory::IsReadable(reinterpret_cast<void*>(UINTPTR_MAX - 1), 8),
                "overflowing pointer range should be unreadable");
    }

    void TestRejectsProtNoneMapping()
    {
        const long pageSize = sysconf(_SC_PAGESIZE);
        Require(pageSize > 0, "invalid page size");

        void* mapping = mmap(nullptr,
                             static_cast<size_t>(pageSize),
                             PROT_NONE,
                             MAP_PRIVATE | MAP_ANONYMOUS,
                             -1,
                             0);
        Require(mapping != MAP_FAILED, "mmap(PROT_NONE) failed");

        const bool readable = Obelisk::Memory::IsReadable(mapping, 1);
        munmap(mapping, static_cast<size_t>(pageSize));
        Require(!readable, "PROT_NONE mapping should be unreadable");
    }
}

int main()
{
    TestReadableStackBuffer();
    TestRejectsInvalidInputs();
    TestRejectsProtNoneMapping();

    std::cout << "MemoryTests passed\n";
    return 0;
}
