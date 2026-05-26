#include <cstdio>
#include <cstring>
#include <errno.h>
#include "runtime/Logger.h"
#include "hooks/HookManager.h"
#include "core/PluginManager.h"

// The constructor attribute ensures this function runs as soon as the shared library 
// is loaded into the target process via LD_PRELOAD.
__attribute__((constructor))
void Obelisk_Init() 
{
    // Avoid injecting into LinuxGSM scripts (bash, grep, tmux, etc)
    if (program_invocation_short_name != nullptr && strstr(program_invocation_short_name, "ShooterGameServer") == nullptr) 
    {
        return;
    }

    // Initialize our logging system
    Obelisk::Logger::Init();

    OBELISK_INFO("==========================================");
    OBELISK_INFO(" Obelisk Runtime Loaded Native (LD_PRELOAD)");
    OBELISK_INFO("==========================================");
    OBELISK_INFO("Starting runtime bootstrap...");
    
    // Initialize hooking engine
    Obelisk::Hooks::HookManager::Init();

    // Load Plugins
    Obelisk::Core::PluginManager::Get().LoadPlugins("ObeliskPlugins");
}

__attribute__((destructor))
void Obelisk_Shutdown()
{
    OBELISK_INFO("Obelisk Runtime Shutting Down...");
    // Future phases: Unload plugins, remove hooks, etc.
}
