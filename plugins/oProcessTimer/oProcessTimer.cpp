#include <nlohmann/json.hpp>
#include <obelisk/ObeliskApi.h>

#include <atomic>
#include <cctype>
#include <cstddef>
#include <cstdint>
#include <cstring>
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
    std::mutex g_StateMutex;
    bool g_Enabled = false;
    uint64_t g_OwnerToken = 0;
    std::atomic<uint64_t> g_TimerId{0};
    uint64_t g_TimerUserData = 0x710E;
    std::atomic<bool> g_TimerSeen{false};
    std::atomic<bool> g_TimerAccepted{false};

    constexpr const char* kDefaultConfig = R"json({
    "enabled": false,
    "allow_all_instances": false,
    "instance_allowlist": []
})json";

    void CopyApiPrefix(const ObeliskApi* api)
    {
        g_Api = {};
        if (!api)
        {
            g_HasApi = false;
            return;
        }

        const size_t copySize = api->struct_size < sizeof(g_Api) ? api->struct_size : sizeof(g_Api);
        std::memcpy(&g_Api, api, copySize);
        g_HasApi = true;
    }

    bool HasBaseApiPrefix(const ObeliskApi* api)
    {
        return api &&
            api->abi_version == OBELISK_API_ABI_VERSION &&
            api->struct_size >= offsetof(ObeliskApi, capabilities) + sizeof(api->capabilities);
    }

    bool HasTimerApi(const ObeliskApi* api, const ObeliskPluginInitContext* context)
    {
        return HasBaseApiPrefix(api) &&
            api->struct_size >= offsetof(ObeliskApi, UnregisterTimerWithOwnerToken) +
                sizeof(api->UnregisterTimerWithOwnerToken) &&
            (api->capabilities & OBELISK_API_CAPABILITY_TIMERS) != 0 &&
            context &&
            context->plugin_owner_token != 0 &&
            api->RegisterTimerWithOwnerTokenHandle &&
            api->UnregisterTimerWithOwnerToken;
    }

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

    bool IsSafeInstanceId(const std::string& value)
    {
        if (value.empty())
            return false;
        for (const unsigned char ch : value)
        {
            if (std::isalnum(ch) || ch == '_' || ch == '-')
                continue;
            return false;
        }
        return true;
    }

    bool IsSafeInstanceAllowlist(const json& value)
    {
        if (!IsStringArray(value))
            return false;
        for (const auto& entry : value)
        {
            if (!IsSafeInstanceId(entry.get<std::string>()))
                return false;
        }
        return true;
    }

    void SafeLogInfo(const char* message) noexcept
    {
        try
        {
            void (*logInfo)(const char*) = nullptr;
            {
                std::lock_guard<std::mutex> lock(g_StateMutex);
                if (g_HasApi)
                    logInfo = g_Api.LogInfo;
            }
            if (logInfo)
                logInfo(message);
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
        if (!IsSafeInstanceAllowlist(*allowlist))
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
            return false;
        try
        {
            config = json::parse(in);
        }
        catch (...)
        {
            return false;
        }
        return config.is_object();
    }

    bool LoadConfig(const ObeliskPluginInitContext* context)
    {
        if (!context || context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
            context->struct_size < sizeof(ObeliskPluginInitContext) ||
            !context->config_path || context->config_path[0] == '\0')
        {
            return false;
        }

        const std::filesystem::path path = context->config_path;
        std::lock_guard<std::mutex> lock(g_StateMutex);

        json config;
        if (!LoadConfigDocument(path, config))
            return false;
        if (!config.contains("enabled") || !config["enabled"].is_boolean())
            return false;
        if (config.contains("allow_all_instances") && !config["allow_all_instances"].is_boolean())
            return false;
        if (config.contains("instance_allowlist") && !IsSafeInstanceAllowlist(config["instance_allowlist"]))
            return false;

        g_Enabled = config.value("enabled", false) && InstanceAllowed(config, context->instance_id);
        return true;
    }

    void OnTimer(uint64_t timerId, void* userData) noexcept
    {
        g_TimerSeen.store(true);
        if (userData == &g_TimerUserData && timerId == g_TimerId.load())
            g_TimerAccepted.store(true);
        SafeLogInfo("[oProcessTimer] Process-local timer fired.");
    }

    void ResetState()
    {
        std::lock_guard<std::mutex> lock(g_StateMutex);
        g_Api = {};
        g_HasApi = false;
        g_Enabled = false;
        g_OwnerToken = 0;
        g_TimerId.store(0);
        g_TimerSeen.store(false);
        g_TimerAccepted.store(false);
    }

    void UnregisterTimer() noexcept
    {
        try
        {
            bool (*unregisterTimer)(uint64_t, uint64_t) = nullptr;
            uint64_t ownerToken = 0;
            uint64_t timerId = 0;
            {
                std::lock_guard<std::mutex> lock(g_StateMutex);
                timerId = g_TimerId.exchange(0);
                if (g_HasApi && timerId != 0)
                {
                    unregisterTimer = g_Api.UnregisterTimerWithOwnerToken;
                    ownerToken = g_OwnerToken;
                }
            }
            if (unregisterTimer)
            {
                unregisterTimer(ownerToken, timerId);
            }
        }
        catch (...)
        {
        }
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
        out->plugin_id = "oProcessTimer";
        out->name = "oProcessTimer";
        out->version = "0.1.0";
        out->config_file = "config.json";
        out->default_config_json = kDefaultConfig;
        return true;
    }
    catch (...)
    {
        return false;
    }
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(
    ObeliskApi* api,
    const ObeliskPluginInitContext* context)
{
    try
    {
        if (!api || !context)
            return false;
        if (!HasBaseApiPrefix(api) ||
            context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
            context->struct_size < sizeof(ObeliskPluginInitContext))
        {
            SafeLogError(api, "[oProcessTimer] Incompatible Obelisk API.");
            return false;
        }
        if (context->plugin_owner_token == 0)
        {
            SafeLogError(api, "[oProcessTimer] Owner token is not available.");
            return false;
        }

        {
            std::lock_guard<std::mutex> lock(g_StateMutex);
            CopyApiPrefix(api);
            g_OwnerToken = context->plugin_owner_token;
        }
        g_TimerSeen.store(false);
        g_TimerAccepted.store(false);

        if (!LoadConfig(context))
        {
            ResetState();
            return false;
        }

        api->LogInfo("[oProcessTimer] Loaded.");
        if (!g_Enabled)
        {
            api->LogInfo("[oProcessTimer] Disabled by config.");
            return true;
        }
        if (!HasTimerApi(api, context))
        {
            SafeLogError(api, "[oProcessTimer] Timer API is not available.");
            ResetState();
            return false;
        }

        const uint64_t timerId = api->RegisterTimerWithOwnerTokenHandle(
            g_OwnerToken,
            1000,
            0,
            0,
            OnTimer,
            &g_TimerUserData);
        g_TimerId.store(timerId);
        if (timerId == 0)
        {
            SafeLogError(api, "[oProcessTimer] Failed to register process-local timer.");
            ResetState();
            return false;
        }

        api->LogInfo("[oProcessTimer] Registered process-local timer.");
        return true;
    }
    catch (const std::exception& e)
    {
        SafeLogError(api, (std::string("[oProcessTimer] Init failed: ") + e.what()).c_str());
        UnregisterTimer();
        ResetState();
        return false;
    }
    catch (...)
    {
        SafeLogError(api, "[oProcessTimer] Init failed with unknown exception.");
        UnregisterTimer();
        ResetState();
        return false;
    }
}

extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown()
{
    try
    {
        UnregisterTimer();
        SafeLogInfo("[oProcessTimer] Shutdown.");
    }
    catch (...)
    {
    }
    ResetState();
}

extern "C" __attribute__((visibility("default"))) bool OProcessTimer_TimerSeen()
{
    return g_TimerSeen.load();
}

extern "C" __attribute__((visibility("default"))) bool OProcessTimer_TimerAccepted()
{
    return g_TimerAccepted.load();
}
