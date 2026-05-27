#include "api/ObeliskApi.h"

#include <atomic>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <string>

namespace
{
    ObeliskApi* g_Api = nullptr;
    std::mutex g_ConfigMutex;
    int32_t g_FilteredFunctionIndex = -1;
    int g_LogLimit = 5;
    std::atomic<int> g_LoggedEvents{0};

    std::filesystem::path ResolveConfigPath()
    {
        if (const char* overridePath = std::getenv("OBASEEVENTS_CONFIG");
            overridePath && overridePath[0] != '\0')
        {
            return overridePath;
        }

        if (const char* configDir = std::getenv("OBELISK_CONFIG_DIR");
            configDir && configDir[0] != '\0')
        {
            return std::filesystem::path(configDir) / "plugins" / "oBaseEvents" / "config.conf";
        }

        if (const char* root = std::getenv("OBELISK_ROOT");
            root && root[0] != '\0')
        {
            return std::filesystem::path(root) / "config" / "plugins" / "oBaseEvents" / "config.conf";
        }

        return std::filesystem::path("oBaseEvents.conf");
    }

    void WriteDefaultConfig(const std::filesystem::path& path)
    {
        const std::filesystem::path parent = path.parent_path();
        if (!parent.empty())
            std::filesystem::create_directories(parent);
        std::ofstream out(path);
        if (!out.is_open())
            return;

        out
            << "# oBaseEvents example config\n"
            << "# filtered_function_index=-1 keeps the event callback disabled.\n"
            << "filtered_function_index=-1\n"
            << "log_limit=5\n";
    }

    void LoadConfig()
    {
        const std::filesystem::path path = ResolveConfigPath();
        std::lock_guard<std::mutex> lock(g_ConfigMutex);

        if (!std::filesystem::exists(path))
        {
            WriteDefaultConfig(path);
            if (g_Api)
                g_Api->LogInfo("[oBaseEvents] Default config created.");
        }

        std::ifstream in(path);
        if (!in.is_open())
        {
            if (g_Api)
                g_Api->LogWarn("[oBaseEvents] Config not readable; using safe defaults.");
            return;
        }

        std::string line;
        while (std::getline(in, line))
        {
            if (line.empty() || line[0] == '#')
                continue;

            const std::string::size_type eq = line.find('=');
            if (eq == std::string::npos)
                continue;

            const std::string key = line.substr(0, eq);
            const std::string value = line.substr(eq + 1);

            try
            {
                if (key == "filtered_function_index")
                    g_FilteredFunctionIndex = static_cast<int32_t>(std::stoi(value));
                else if (key == "log_limit")
                    g_LogLimit = std::stoi(value);
            }
            catch (...)
            {
                if (g_Api)
                    g_Api->LogWarn("[oBaseEvents] Ignoring invalid config value.");
            }
        }
    }

    bool OnFilteredProcessEvent(void* caller, void* function, void* params)
    {
        (void)caller;
        (void)function;
        (void)params;

        const int current = g_LoggedEvents.fetch_add(1);
        if (current < g_LogLimit && g_Api)
            g_Api->LogInfo("[oBaseEvents] Filtered ProcessEvent callback fired.");

        return true;
    }
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(ObeliskApi* api)
{
    if (!api)
        return false;

    g_Api = api;

    if (api->abi_version != OBELISK_API_ABI_VERSION ||
        api->struct_size < sizeof(ObeliskApi))
    {
        api->LogError("[oBaseEvents] Incompatible Obelisk API.");
        return false;
    }

    LoadConfig();
    api->LogInfo("[oBaseEvents] Loaded.");

    if (g_FilteredFunctionIndex >= 0)
    {
        api->RegisterPreProcessEventForNameIndex(g_FilteredFunctionIndex, OnFilteredProcessEvent);
        api->LogInfo("[oBaseEvents] Registered filtered ProcessEvent callback.");
    }
    else
    {
        api->LogInfo("[oBaseEvents] Event callback disabled by config.");
    }

    return true;
}

extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown()
{
    if (g_Api)
        g_Api->LogInfo("[oBaseEvents] Shutdown.");
    g_Api = nullptr;
}
