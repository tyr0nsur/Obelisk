#include "SafeMemoryRead.h"

#include <cerrno>
#include <cstdint>
#include <limits>
#include <sys/syscall.h>
#include <sys/uio.h>
#include <unistd.h>

namespace Obelisk::Memory
{
    bool ReadExact(void* destination, const void* source, size_t size) noexcept
    {
        if (!destination || !source || size == 0 ||
            size > static_cast<size_t>(std::numeric_limits<ssize_t>::max()))
            return false;

        const auto from = reinterpret_cast<uintptr_t>(source);
        const auto to = reinterpret_cast<uintptr_t>(destination);
        // Use an exclusive end and reject arithmetic wrapping at UINTPTR_MAX.
        if (from > UINTPTR_MAX - size || to > UINTPTR_MAX - size)
            return false;

        iovec local{destination, size};
        iovec remote{const_cast<void*>(source), size};
        const int previousErrno = errno;
        ssize_t copied;
        do
        {
            copied = static_cast<ssize_t>(syscall(
                SYS_process_vm_readv, getpid(), &local, 1UL, &remote, 1UL, 0UL));
        }
        while (copied == -1 && errno == EINTR);

        errno = previousErrno;
        return copied == static_cast<ssize_t>(size);
    }
}
