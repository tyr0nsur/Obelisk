#include "HookManager.h"
#include "ProcessEventHook.h"
#include "runtime/Logger.h"
#include "runtime/RuntimeMarkers.h"

namespace Obelisk::Hooks
{
    void HookManager::Init()
    {
        OBELISK_INFO("Initializing HookManager...");
        if (Obelisk::Runtime::IsEnvAndInstanceMarkerEnabled("OBELISK_ENABLE_PROCESS_EVENT_HOOK",
                                                            "enable-process-event-hook"))
        {
            ProcessEventHook::Install();
        }
        else
        {
            OBELISK_WARN("ProcessEvent hook disabled. Set OBELISK_ENABLE_PROCESS_EVENT_HOOK=1 with enable-process-event-hook marker only for controlled hook testing.");
        }
    }
}
