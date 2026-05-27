#include "api/ObeliskApi.h"
#include "extern/nlohmann/json.hpp"

#include <atomic>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <string>
#include <system_error>

using json = nlohmann::json;

namespace
{
    ObeliskApi* g_Api = nullptr;
    std::mutex g_ConfigMutex;
    bool g_Enabled = false;
    bool g_ProcessEventEnabled = false;
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
            return std::filesystem::path(configDir) / "plugins" / "oBaseEvents" / "config.json";
        }

        if (const char* root = std::getenv("OBELISK_ROOT");
            root && root[0] != '\0')
        {
            return std::filesystem::path(root) / "config" / "plugins" / "oBaseEvents" / "config.json";
        }

        return std::filesystem::path("oBaseEvents.json");
    }

    json DefaultConfig()
    {
        return {
            {"enabled", false},
            {"log_level", "info"},
            {"map_allowlist", json::array()},
            {"process_event", {
                {"enabled", false},
                {"filtered_function_index", -1},
                {"log_limit", 5}
            }}
        };
    }

    void WriteDefaultConfig(const std::filesystem::path& path, const json& config)
    {
        std::error_code ec;
        const std::filesystem::path parent = path.parent_path();
        if (!parent.empty())
        {
            std::filesystem::create_directories(parent, ec);
            if (ec)
                return;
        }

        std::ofstream out(path);
        if (!out.is_open())
            return;

        out << config.dump(4) << '\n';
    }

    json LoadConfigDocument(const std::filesystem::path& path)
    {
        json config = DefaultConfig();
        std::error_code ec;
        if (!std::filesystem::exists(path, ec))
        {
            WriteDefaultConfig(path, config);
            if (g_Api)
                g_Api->LogInfo("[oBaseEvents] Default config created.");
            return config;
        }

        std::ifstream in(path);
        if (!in.is_open())
        {
            if (g_Api)
                g_Api->LogWarn("[oBaseEvents] Config not readable; using safe defaults.");
            return config;
        }

        try
        {
            json parsed = json::parse(in);
            if (parsed.is_object())
                return parsed;
        }
        catch (...)
        {
            if (g_Api)
                g_Api->LogWarn("[oBaseEvents] Config parse failed; using safe defaults.");
        }

        return config;
    }

    void LoadConfig()
    {
        const std::filesystem::path path = ResolveConfigPath();
        std::lock_guard<std::mutex> lock(g_ConfigMutex);

        const json config = LoadConfigDocument(path);
        g_Enabled = config.value("enabled", false);

        const json processEvent = config.value("process_event", json::object());
        if (processEvent.is_object())
        {
            g_ProcessEventEnabled = processEvent.value("enabled", false);
            g_FilteredFunctionIndex = processEvent.value("filtered_function_index", -1);
            g_LogLimit = processEvent.value("log_limit", 5);
        }

        if (g_LogLimit < 0)
            g_LogLimit = 0;
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

    if (api->abi_version != OBELISK_API_ABI_VERSION ||
        api->struct_size < sizeof(ObeliskApi))
    {
        api->LogError("[oBaseEvents] Incompatible Obelisk API.");
        return false;
    }

    g_Api = api;
    g_LoggedEvents.store(0);

    LoadConfig();
    api->LogInfo("[oBaseEvents] Loaded.");

    if (!g_Enabled)
    {
        api->LogInfo("[oBaseEvents] Disabled by config.");
        return true;
    }

    if (g_ProcessEventEnabled && g_FilteredFunctionIndex >= 0)
    {
        api->RegisterPreProcessEventForNameIndex(g_FilteredFunctionIndex, OnFilteredProcessEvent);
        api->LogInfo("[oBaseEvents] Registered filtered ProcessEvent callback.");
    }
    else
    {
        api->LogInfo("[oBaseEvents] ProcessEvent example disabled by config.");
    }

    return true;
}

extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown()
{
    if (g_Api)
        g_Api->LogInfo("[oBaseEvents] Shutdown.");

    g_Api = nullptr;
    g_Enabled = false;
    g_ProcessEventEnabled = false;
    g_FilteredFunctionIndex = -1;
    g_LogLimit = 5;
    g_LoggedEvents.store(0);
}
