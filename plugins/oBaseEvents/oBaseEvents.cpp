#include <nlohmann/json.hpp>
#include <obelisk/ObeliskApi.h>

#include <atomic>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <string>

using json = nlohmann::json;

namespace
{
    ObeliskApi g_Api{};
    bool g_HasApi = false;
    std::mutex g_ConfigMutex;
    bool g_Enabled = false;
    bool g_ProcessEventEnabled = false;
    int32_t g_FilteredFunctionIndex = -1;
    int g_LogLimit = 5;
    uint64_t g_OwnerToken = 0;
    uint64_t g_ProcessEventRegistrationId = 0;
    std::atomic<int> g_LoggedEvents{0};

    constexpr const char* kDefaultConfig = R"json({
    "enabled": false,
    "log_level": "info",
    "allow_all_instances": false,
    "instance_allowlist": [],
    "process_event": {
        "enabled": false,
        "filtered_function_index": -1,
        "log_limit": 5
    }
})json";

    bool IsStringArray(const json& value)
    {
        if (!value.is_array())
            return false;

        for (const auto& entry : value)
        {
            if (!entry.is_string())
                return false;
        }

        return true;
    }

    void SafeLogInfo(const char* message) noexcept
    {
        try
        {
            if (g_HasApi && g_Api.LogInfo)
                g_Api.LogInfo(message);
        }
        catch (...)
        {
        }
    }

    void SafeLogError(const char* message) noexcept
    {
        try
        {
            if (g_HasApi && g_Api.LogError)
                g_Api.LogError(message);
        }
        catch (...)
        {
        }
    }

    void SafeLogError(const ObeliskApi* api, const char* message) noexcept
    {
        try
        {
            if (api && api->LogError)
                api->LogError(message);
        }
        catch (...)
        {
        }
    }

    bool InstanceAllowed(const json& config, const char* instanceId)
    {
        if (config.value("allow_all_instances", false))
            return true;

        const auto allowlist = config.find("instance_allowlist");
        if (allowlist == config.end() || allowlist->empty())
            return false;

        if (!IsStringArray(*allowlist))
            return false;

        const std::string current = instanceId ? instanceId : "";
        for (const auto& entry : *allowlist)
        {
            if (entry.get<std::string>() == current)
                return true;
        }

        return false;
    }

    bool LoadConfigDocument(const std::filesystem::path& path, json& config)
    {
        std::ifstream in(path);
        if (!in.is_open())
        {
            SafeLogError("[oBaseEvents] Config not readable.");
            return false;
        }

        try
        {
            config = json::parse(in);
        }
        catch (const std::exception& e)
        {
            SafeLogError((std::string("[oBaseEvents] Config parse failed: ") + e.what()).c_str());
            return false;
        }

        if (!config.is_object())
        {
            SafeLogError("[oBaseEvents] Config root must be an object.");
            return false;
        }

        return true;
    }

    bool LoadConfig(const ObeliskPluginInitContext* context)
    {
        if (!context || context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
            context->struct_size < sizeof(ObeliskPluginInitContext) ||
            !context->config_path || context->config_path[0] == '\0')
        {
            SafeLogError("[oBaseEvents] Invalid plugin init context.");
            return false;
        }

        const std::filesystem::path path = context->config_path;
        std::lock_guard<std::mutex> lock(g_ConfigMutex);

        json config;
        if (!LoadConfigDocument(path, config))
            return false;

        if (!config.contains("enabled") || !config["enabled"].is_boolean())
        {
            SafeLogError("[oBaseEvents] Config field enabled must be boolean.");
            return false;
        }

        if (config.contains("log_level") && !config["log_level"].is_string())
        {
            SafeLogError("[oBaseEvents] Config field log_level must be string.");
            return false;
        }

        if (config.contains("instance_allowlist") && !IsStringArray(config["instance_allowlist"]))
        {
            SafeLogError("[oBaseEvents] Config field instance_allowlist must be an array of strings.");
            return false;
        }

        if (config.contains("allow_all_instances") && !config["allow_all_instances"].is_boolean())
        {
            SafeLogError("[oBaseEvents] Config field allow_all_instances must be boolean.");
            return false;
        }

        if (config.contains("map_allowlist") && !IsStringArray(config["map_allowlist"]))
        {
            SafeLogError("[oBaseEvents] Config field map_allowlist must be an array of strings.");
            return false;
        }
        if (config.contains("map_allowlist") && !config["map_allowlist"].empty())
        {
            SafeLogError("[oBaseEvents] Config field map_allowlist is not supported yet and must be empty.");
            return false;
        }

        if (!InstanceAllowed(config, context->instance_id))
        {
            g_Enabled = false;
            return true;
        }

        g_Enabled = config.value("enabled", false);

        const json processEvent = config.value("process_event", json::object());
        if (!processEvent.is_object())
        {
            SafeLogError("[oBaseEvents] Config field process_event must be an object.");
            return false;
        }

        if (!processEvent.contains("enabled") || !processEvent["enabled"].is_boolean() ||
            !processEvent.contains("filtered_function_index") || !processEvent["filtered_function_index"].is_number_integer() ||
            !processEvent.contains("log_limit") || !processEvent["log_limit"].is_number_integer())
        {
            SafeLogError("[oBaseEvents] process_event fields have invalid types.");
            return false;
        }

        g_ProcessEventEnabled = processEvent.value("enabled", false);
        g_FilteredFunctionIndex = processEvent.value("filtered_function_index", -1);
        g_LogLimit = processEvent.value("log_limit", 5);

        if (g_LogLimit < 0)
            g_LogLimit = 0;

        return true;
    }

    bool OnFilteredProcessEvent(void* caller, void* function, void* params) noexcept
    {
        (void)caller;
        (void)function;
        (void)params;

        const int current = g_LoggedEvents.fetch_add(1);
        if (current < g_LogLimit)
            SafeLogInfo("[oBaseEvents] Filtered ProcessEvent callback fired.");

        return true;
    }

    void ResetState()
    {
        g_Api = {};
        g_HasApi = false;
        g_Enabled = false;
        g_ProcessEventEnabled = false;
        g_FilteredFunctionIndex = -1;
        g_LogLimit = 5;
        g_OwnerToken = 0;
        g_ProcessEventRegistrationId = 0;
        g_LoggedEvents.store(0);
    }
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out)
{
    try
    {
        if (!out)
            return false;

        out->abi_version = OBELISK_PLUGIN_METADATA_ABI_VERSION;
        out->struct_size = sizeof(ObeliskPluginMetadata);
        out->plugin_id = "oBaseEvents";
        out->name = "oBaseEvents";
        out->version = "0.1.0-dev";
        out->config_file = "config.json";
        out->default_config_json = kDefaultConfig;
        return true;
    }
    catch (...)
    {
        return false;
    }
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(ObeliskApi* api, const ObeliskPluginInitContext* context)
{
    try
    {
        if (!api || !context)
            return false;

        if (api->abi_version != OBELISK_API_ABI_VERSION ||
            api->struct_size < sizeof(ObeliskApi) ||
            context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
            context->struct_size < sizeof(ObeliskPluginInitContext))
        {
            api->LogError("[oBaseEvents] Incompatible Obelisk API.");
            return false;
        }

        g_Api = *api;
        g_HasApi = true;
        g_OwnerToken = context->plugin_owner_token;
        g_LoggedEvents.store(0);

        if (!LoadConfig(context))
        {
            ResetState();
            return false;
        }

        api->LogInfo("[oBaseEvents] Loaded.");

        if (!g_Enabled)
        {
            api->LogInfo("[oBaseEvents] Disabled by config.");
            return true;
        }

        if (g_ProcessEventEnabled && g_FilteredFunctionIndex >= 0)
        {
            if ((api->capabilities & OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS) == 0 ||
                (api->capabilities & OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES) == 0 ||
                api->struct_size < offsetof(ObeliskApi, UnregisterProcessEventCallbackWithOwnerToken) +
                    sizeof(api->UnregisterProcessEventCallbackWithOwnerToken) ||
                context->plugin_owner_token == 0 ||
                !api->RegisterPreProcessEventForNameIndexWithOwnerTokenHandle ||
                !api->UnregisterProcessEventCallbackWithOwnerToken)
            {
                api->LogError("[oBaseEvents] ProcessEvent example requires owner-token callback handle API.");
                ResetState();
                return false;
            }

            g_ProcessEventRegistrationId =
                api->RegisterPreProcessEventForNameIndexWithOwnerTokenHandle(
                    context->plugin_owner_token,
                    g_FilteredFunctionIndex,
                    OnFilteredProcessEvent);
            if (g_ProcessEventRegistrationId == 0)
            {
                api->LogError("[oBaseEvents] Failed to register filtered ProcessEvent callback.");
                ResetState();
                return false;
            }

            api->LogInfo("[oBaseEvents] Registered filtered ProcessEvent callback with explicit handle.");
        }
        else
        {
            api->LogInfo("[oBaseEvents] ProcessEvent example disabled by config.");
        }

        return true;
    }
    catch (const std::exception& e)
    {
        SafeLogError(api, (std::string("[oBaseEvents] Init failed: ") + e.what()).c_str());
        ResetState();
        return false;
    }
    catch (...)
    {
        SafeLogError(api, "[oBaseEvents] Init failed with unknown exception.");
        ResetState();
        return false;
    }
}

extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown()
{
    try
    {
        if (g_HasApi && g_ProcessEventRegistrationId != 0 && g_Api.UnregisterProcessEventCallbackWithOwnerToken)
        {
            g_Api.UnregisterProcessEventCallbackWithOwnerToken(g_OwnerToken, g_ProcessEventRegistrationId);
            g_ProcessEventRegistrationId = 0;
        }

        SafeLogInfo("[oBaseEvents] Shutdown.");
    }
    catch (...)
    {
    }
    ResetState();
}
