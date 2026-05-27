#include <cstdio>
#include <cstring>
#include <errno.h>
#include <exception>
#include <cstdlib>
#include <filesystem>
#include <string>
#include "runtime/Logger.h"
#include "hooks/HookManager.h"
#include "hooks/ProcessEventHook.h"
#include "core/PluginManager.h"
#include "ue/ReflectionScanner.h"

static bool g_ObeliskStarted = false;

static std::string GetPluginDirectory()
{
    const char* specific = std::getenv("OBELISK_PLUGIN_DIR");
    if (specific && specific[0] != '\0')
        return specific;

    const char* root = std::getenv("OBELISK_ROOT");
    if (root && root[0] != '\0')
        return (std::filesystem::path(root) / "plugins").string();

    const char* legacy = std::getenv("OBELISK_ENABLE_LEGACY_PLUGIN_DIR");
    if (legacy && std::strcmp(legacy, "1") == 0)
        return "ObeliskPlugins";

    return "plugins";
}

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

    try
    {
        Obelisk::Logger::Init();
        g_ObeliskStarted = true;

    OBELISK_INFO("==========================================");
    OBELISK_INFO(" Obelisk Runtime Loaded Native (LD_PRELOAD)");
    OBELISK_INFO("==========================================");
    OBELISK_INFO("Starting runtime bootstrap...");
    
    // Initialize hooking engine
    Obelisk::Hooks::HookManager::Init();

        const char* reflectionScanner = std::getenv("OBELISK_ENABLE_REFLECTION_SCANNER");
        if (reflectionScanner && std::strcmp(reflectionScanner, "1") == 0)
        {
            Obelisk::UE::ReflectionScanner::RunStartupScan();
        }
        else
        {
            OBELISK_INFO("ReflectionScanner disabled. Set OBELISK_ENABLE_REFLECTION_SCANNER=1 to run the experimental scanner.");
        }

        const char* disablePlugins = std::getenv("OBELISK_DISABLE_PLUGINS");
        if (disablePlugins && std::strcmp(disablePlugins, "1") == 0)
        {
            OBELISK_WARN("Plugin loading disabled by OBELISK_DISABLE_PLUGINS=1.");
        }
        else
        {
            Obelisk::Core::PluginManager::Get().LoadPlugins(GetPluginDirectory());
        }
    }
    catch (const std::exception& e)
    {
        if (Obelisk::Logger::IsInitialized())
        {
            OBELISK_CRITICAL("Obelisk bootstrap failed: {}", e.what());
            Obelisk::Hooks::ProcessEventHook::Remove();
            Obelisk::Core::PluginManager::Get().UnloadAll();
            Obelisk::Logger::Shutdown();
        }
        g_ObeliskStarted = false;
    }
    catch (...)
    {
        if (Obelisk::Logger::IsInitialized())
        {
            OBELISK_CRITICAL("Obelisk bootstrap failed with unknown exception.");
            Obelisk::Hooks::ProcessEventHook::Remove();
            Obelisk::Core::PluginManager::Get().UnloadAll();
            Obelisk::Logger::Shutdown();
        }
        g_ObeliskStarted = false;
    }
}

__attribute__((destructor))
void Obelisk_Shutdown()
{
    if (!g_ObeliskStarted || !Obelisk::Logger::IsInitialized())
        return;

    OBELISK_INFO("Obelisk Runtime Shutting Down...");
    Obelisk::Hooks::ProcessEventHook::Remove();
    Obelisk::Core::PluginManager::Get().UnloadAll();
    Obelisk::Logger::Shutdown();
    g_ObeliskStarted = false;
}
