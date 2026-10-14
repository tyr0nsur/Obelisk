#include "StartupNativeHook.h"
#include "ue/SafeMemoryRead.h"

#include <array>
#include <cstdio>
#include <cstring>
#include <dirent.h>
#include <sys/mman.h>
#include <unistd.h>

#if !defined(__x86_64__)
#error StartupNativeHook supports only Linux x86-64.
#endif

namespace Obelisk::Hooks
{
    namespace
    {
        constexpr size_t kJumpSize = 14;
        constexpr size_t kMaximumPrologueSize = 128;

        void WriteJump(uint8_t* destination, const void* target) noexcept
        {
            // jmp qword ptr [rip + 0]; address. No registers are clobbered,
            // including RAX and the SysV varargs vector-register count in AL.
            constexpr std::array<uint8_t, 6> instruction{0xff, 0x25, 0, 0, 0, 0};
            std::memcpy(destination, instruction.data(), instruction.size());
            const uintptr_t address = reinterpret_cast<uintptr_t>(target);
            std::memcpy(destination + instruction.size(), &address, sizeof(address));
        }

        bool HasOneThread() noexcept
        {
            DIR* directory = opendir("/proc/self/task");
            if (!directory)
                return false;
            size_t count = 0;
            while (dirent* entry = readdir(directory))
            {
                if (entry->d_name[0] >= '0' && entry->d_name[0] <= '9')
                    ++count;
            }
            closedir(directory);
            return count == 1;
        }

        bool IsReadExecuteMapping(uintptr_t begin, uintptr_t end) noexcept
        {
            FILE* maps = std::fopen("/proc/self/maps", "r");
            if (!maps)
                return false;
            bool matches = false;
            char line[4096];
            while (std::fgets(line, sizeof(line), maps))
            {
                unsigned long long low = 0, high = 0;
                char permissions[5]{};
                if (std::sscanf(line, "%llx-%llx %4s", &low, &high, permissions) == 3 &&
                    begin >= low && end <= high &&
                    permissions[0] == 'r' && permissions[1] == '-' && permissions[2] == 'x')
                {
                    matches = true;
                    break;
                }
            }
            std::fclose(maps);
            return matches;
        }
    }

    bool StartupNativeHook::Install(void* target, void* detour,
                                    std::span<const uint8_t> expectedPrologue) noexcept
    {
        m_LastError = {};
        if (m_Installed)
        {
            m_LastError = "hook already installed";
            return false;
        }
        const size_t patchSize = expectedPrologue.size();
        const uintptr_t start = reinterpret_cast<uintptr_t>(target);
        if (!target || !detour || target == detour || patchSize < kJumpSize ||
            patchSize > kMaximumPrologueSize || !expectedPrologue.data() ||
            start > UINTPTR_MAX - patchSize)
        {
            m_LastError = "invalid target, detour or prologue";
            return false;
        }
        if (!HasOneThread())
        {
            m_LastError = "startup hook requires exactly one process thread";
            return false;
        }
        if (!IsReadExecuteMapping(start, start + patchSize))
        {
            m_LastError = "target is not in a read-execute mapping";
            return false;
        }

        std::array<uint8_t, kMaximumPrologueSize> original{};
        if (!Memory::ReadExact(original.data(), target, patchSize) ||
            std::memcmp(original.data(), expectedPrologue.data(), patchSize) != 0)
        {
            m_LastError = "target prologue differs from the verified profile";
            return false;
        }

        const long pageSizeResult = sysconf(_SC_PAGESIZE);
        if (pageSizeResult <= 0)
        {
            m_LastError = "page size unavailable";
            return false;
        }
        const auto pageSize = static_cast<uintptr_t>(pageSizeResult);
        const uintptr_t firstPage = start - start % pageSize;
        const uintptr_t lastByte = start + patchSize - 1;
        const uintptr_t lastPage = lastByte - lastByte % pageSize;
        if (lastPage > UINTPTR_MAX - pageSize)
        {
            m_LastError = "target page range overflow";
            return false;
        }
        const size_t protectedSize = lastPage + pageSize - firstPage;
        const size_t trampolineSize = patchSize + kJumpSize;
        void* trampoline = mmap(nullptr, trampolineSize, PROT_READ | PROT_WRITE,
                                MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (trampoline == MAP_FAILED)
        {
            m_LastError = "trampoline allocation failed";
            return false;
        }
        auto* bytes = static_cast<uint8_t*>(trampoline);
        std::memcpy(bytes, original.data(), patchSize);
        WriteJump(bytes + patchSize, reinterpret_cast<void*>(start + patchSize));
        __builtin___clear_cache(reinterpret_cast<char*>(bytes),
                               reinterpret_cast<char*>(bytes + trampolineSize));
        if (mprotect(trampoline, trampolineSize, PROT_READ | PROT_EXEC) != 0)
        {
            munmap(trampoline, trampolineSize);
            m_LastError = "trampoline could not be made read-execute";
            return false;
        }

        void* protectedAddress = reinterpret_cast<void*>(firstPage);
        if (mprotect(protectedAddress, protectedSize, PROT_READ | PROT_WRITE | PROT_EXEC) != 0)
        {
            munmap(trampoline, trampolineSize);
            m_LastError = "target could not be made writable";
            return false;
        }
        auto* targetBytes = static_cast<uint8_t*>(target);
        WriteJump(targetBytes, detour);
        std::memset(targetBytes + kJumpSize, 0x90, patchSize - kJumpSize);
        __builtin___clear_cache(reinterpret_cast<char*>(targetBytes),
                               reinterpret_cast<char*>(targetBytes + patchSize));
        if (mprotect(protectedAddress, protectedSize, PROT_READ | PROT_EXEC) != 0)
        {
            // No other thread may execute this target during installation.
            std::memcpy(targetBytes, original.data(), patchSize);
            __builtin___clear_cache(reinterpret_cast<char*>(targetBytes),
                                   reinterpret_cast<char*>(targetBytes + patchSize));
            mprotect(protectedAddress, protectedSize, PROT_READ | PROT_EXEC);
            munmap(trampoline, trampolineSize);
            m_LastError = "target read-execute protection failed; patch restored";
            return false;
        }

        m_Trampoline = trampoline;
        m_Installed = true;
        return true;
    }
}
