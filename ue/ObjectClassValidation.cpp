#include "ObjectClassValidation.h"
#include "SafeMemoryRead.h"

#include <array>
#include <cstdint>

namespace Obelisk::UE::ObjectClassValidation
{
    namespace
    {
        bool ReadPointer(void* object, uintptr_t offset, void*& result) noexcept
        {
            result = nullptr;
            const auto address = reinterpret_cast<uintptr_t>(object);
            return object && address <= UINTPTR_MAX - offset &&
                   Memory::ReadExact(&result, reinterpret_cast<const void*>(address + offset), sizeof(result));
        }
    }

    bool HasClassInAncestry(void* object, void* expectedClass) noexcept
    {
        if (!object || !expectedClass)
            return false;
        void* currentClass = nullptr;
        if (!ReadPointer(object, 0x10, currentClass) || !currentClass)
            return false;

        return ClassHasAncestor(currentClass, expectedClass);
    }

    bool ClassHasAncestor(void* currentClass, void* expectedClass) noexcept
    {
        if (!currentClass || !expectedClass)
            return false;
        std::array<void*, 32> visited{};
        size_t count = 0;
        bool matched = false;
        while (currentClass)
        {
            if (count == visited.size())
                return false;
            for (size_t previous = 0; previous < count; ++previous)
                if (visited[previous] == currentClass)
                    return false;
            visited[count++] = currentClass;
            matched = matched || currentClass == expectedClass;
            void* superclass = nullptr;
            if (!ReadPointer(currentClass, 0x30, superclass))
                return false;
            currentClass = superclass;
        }
        return matched;
    }
}
