#include <cstdio>
#include "runtime/Logger.h"

// The constructor attribute ensures this function runs as soon as the shared library 
// is loaded into the target process via LD_PRELOAD.
__attribute__((constructor))
void Obelisk_Init() 
{
    // Initialize our logging system
    Obelisk::Logger::Init();

    OBELISK_INFO("==========================================");
    OBELISK_INFO(" Obelisk Runtime Loaded Native (LD_PRELOAD)");
    OBELISK_INFO("==========================================");
    OBELISK_INFO("Starting runtime bootstrap...");
    
    // Future phases: Initialize hooking engine, setup plugins, etc.
}

__attribute__((destructor))
void Obelisk_Shutdown()
{
    OBELISK_INFO("Obelisk Runtime Shutting Down...");
    // Future phases: Unload plugins, remove hooks, etc.
}
