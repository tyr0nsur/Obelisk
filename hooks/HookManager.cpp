#include "HookManager.h"
#include "ProcessEventHook.h"
#include "runtime/Logger.h"
#include <cstdlib>
#include <cstring>

namespace Obelisk::Hooks
{
    void HookManager::Init()
    {
        OBELISK_INFO("Initializing HookManager...");
        const char* processEventHook = std::getenv("OBELISK_ENABLE_PROCESS_EVENT_HOOK");
        if (processEventHook && std::strcmp(processEventHook, "1") == 0)
        {
            ProcessEventHook::Install();
        }
        else
        {
            OBELISK_WARN("ProcessEvent hook disabled. Set OBELISK_ENABLE_PROCESS_EVENT_HOOK=1 only for controlled hook testing.");
        }
    }
}
