#include "HookManager.h"
#include "ProcessEventHook.h"
#include "runtime/Logger.h"

namespace Obelisk::Hooks
{
    void HookManager::Init()
    {
        OBELISK_INFO("Initializing HookManager...");
        ProcessEventHook::Install();
    }
}
