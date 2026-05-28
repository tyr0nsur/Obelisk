#pragma once

#include <cstdint>

namespace Obelisk::Hooks
{
    using ProcessEventOriginalInvoker = void (*)(void* object, void* function, void* params);

    bool DispatchProcessEventCallbacks(
        int32_t nameIndex,
        void* object,
        void* function,
        void* params,
        bool hasPreCallbacks,
        bool hasPostCallbacks,
        ProcessEventOriginalInvoker original);
}
