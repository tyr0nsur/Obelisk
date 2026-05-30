#include "hooks/ProcessEventHook.h"

#include <stdexcept>

namespace Obelisk::Hooks
{
    namespace
    {
        int g_CallOriginalProcessEventCount = 0;
        bool g_ThrowOnCallOriginalProcessEvent = false;
    }

    void ProcessEventHook::CallOriginalProcessEvent(void*, void*, void*)
    {
        ++g_CallOriginalProcessEventCount;
        if (g_ThrowOnCallOriginalProcessEvent)
            throw std::runtime_error("test CallOriginalProcessEvent exception");
    }

    int ProcessEventCallOriginalCountForTesting()
    {
        return g_CallOriginalProcessEventCount;
    }

    void ResetProcessEventCallOriginalCountForTesting()
    {
        g_CallOriginalProcessEventCount = 0;
        g_ThrowOnCallOriginalProcessEvent = false;
    }

    void SetProcessEventCallOriginalThrowForTesting(bool enabled)
    {
        g_ThrowOnCallOriginalProcessEvent = enabled;
    }
}
