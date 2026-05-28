#include "hooks/ProcessEventHook.h"

namespace Obelisk::Hooks
{
    namespace
    {
        int g_CallOriginalProcessEventCount = 0;
    }

    void ProcessEventHook::CallOriginalProcessEvent(void*, void*, void*)
    {
        ++g_CallOriginalProcessEventCount;
    }

    int ProcessEventCallOriginalCountForTesting()
    {
        return g_CallOriginalProcessEventCount;
    }

    void ResetProcessEventCallOriginalCountForTesting()
    {
        g_CallOriginalProcessEventCount = 0;
    }
}
