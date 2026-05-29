#include <nlohmann/json.hpp>
#include <obelisk/ObeliskApi.h>

#include <atomic>
#include <cctype>
#include <cstdint>
#include <cstdio>
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
    int g_LogLimit = 5;
    uint64_t g_OwnerToken = 0;
    uint64_t g_ChatRegistrationId = 0;
    std::atomic<int> g_LoggedEvents{0};

    constexpr const char* kDefaultConfig = R"json({
    "enabled": false,
    "allow_all_instances": false,
    "instance_allowlist": [],
    "chat_logger": {
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
        {
            SafeLogError("[oChatLogger] Config not readable.");
            return false;
        }

        try
        {
            config = json::parse(in);
        }
        catch (const std::exception& e)
        {
            SafeLogError((std::string("[oChatLogger] Config parse failed: ") + e.what()).c_str());
            return false;
        }

        if (!config.is_object())
        {
            SafeLogError("[oChatLogger] Config root must be an object.");
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
            SafeLogError("[oChatLogger] Invalid plugin init context.");
            return false;
        }

        const std::filesystem::path path = context->config_path;
        std::lock_guard<std::mutex> lock(g_ConfigMutex);

        json config;
        if (!LoadConfigDocument(path, config))
            return false;

        if (!config.contains("enabled") || !config["enabled"].is_boolean())
        {
            SafeLogError("[oChatLogger] Config field enabled must be boolean.");
            return false;
        }
        if (config.contains("allow_all_instances") && !config["allow_all_instances"].is_boolean())
        {
            SafeLogError("[oChatLogger] Config field allow_all_instances must be boolean.");
            return false;
        }
        if (config.contains("instance_allowlist") && !IsSafeInstanceAllowlist(config["instance_allowlist"]))
        {
            SafeLogError("[oChatLogger] Config field instance_allowlist must be an array of safe instance ids.");
            return false;
        }

        if (!InstanceAllowed(config, context->instance_id))
        {
            g_Enabled = false;
            return true;
        }

        g_Enabled = config.value("enabled", false);
        const json chatLogger = config.value("chat_logger", json::object());
        if (!chatLogger.is_object())
        {
            SafeLogError("[oChatLogger] Config field chat_logger must be an object.");
            return false;
        }
        if (!chatLogger.contains("log_limit") || !chatLogger["log_limit"].is_number_integer())
        {
            SafeLogError("[oChatLogger] chat_logger.log_limit must be integer.");
            return false;
        }
        g_LogLimit = chatLogger.value("log_limit", 5);
        if (g_LogLimit < 0)
            g_LogLimit = 0;
        return true;
    }

    void OnChatMessageEvent(const ObeliskChatMessageEvent* event, void*) noexcept
    {
        if (!event ||
            event->abi_version != OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION ||
            event->struct_size < sizeof(ObeliskChatMessageEvent) ||
            event->send_mode > OBELISK_CHAT_SEND_MODE_MAX ||
            (event->flags & OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD) == 0 ||
            event->sequence == 0)
        {
            SafeLogError("[oChatLogger] Rejected malformed ChatMessageEvent.");
            return;
        }

        const int current = g_LoggedEvents.fetch_add(1);
        if (current >= g_LogLimit)
            return;

        char buffer[192];
        std::snprintf(buffer,
                      sizeof(buffer),
                      "[oChatLogger] ChatMessageEvent received sequence=%llu send_mode=%u flags=0x%llx message_size=%zu.",
                      static_cast<unsigned long long>(event->sequence),
                      static_cast<unsigned>(event->send_mode),
                      static_cast<unsigned long long>(event->flags),
                      event->message.size);
        SafeLogInfo(buffer);
    }

    bool HasChatMessageEventApi(const ObeliskApi* api)
    {
        return api &&
            (api->capabilities & OBELISK_API_CAPABILITY_CHAT_EVENTS) != 0 &&
            api->struct_size >= offsetof(ObeliskApi, UnregisterChatMessageEventWithOwnerToken) +
                sizeof(api->UnregisterChatMessageEventWithOwnerToken) &&
            api->RegisterChatMessageEventWithOwnerTokenHandle &&
            api->UnregisterChatMessageEventWithOwnerToken;
    }

    void ResetState()
    {
        g_Api = {};
        g_HasApi = false;
        g_Enabled = false;
        g_LogLimit = 5;
        g_OwnerToken = 0;
        g_ChatRegistrationId = 0;
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
        out->plugin_id = "oChatLogger";
        out->name = "oChatLogger";
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
            context->struct_size < sizeof(ObeliskPluginInitContext) ||
            context->plugin_owner_token == 0)
        {
            SafeLogError(api, "[oChatLogger] Incompatible Obelisk API.");
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

        api->LogInfo("[oChatLogger] Loaded.");
        if (!g_Enabled)
        {
            api->LogInfo("[oChatLogger] Disabled by config.");
            return true;
        }

        if (!HasChatMessageEventApi(api))
        {
            api->LogError("[oChatLogger] ChatMessageEvent API is not available.");
            ResetState();
            return false;
        }

        g_ChatRegistrationId = api->RegisterChatMessageEventWithOwnerTokenHandle(
            context->plugin_owner_token,
            OnChatMessageEvent,
            nullptr);
        if (g_ChatRegistrationId == 0)
        {
            api->LogError("[oChatLogger] Failed to register ChatMessageEvent callback.");
            ResetState();
            return false;
        }

        api->LogInfo("[oChatLogger] Registered ChatMessageEvent callback.");
        return true;
    }
    catch (const std::exception& e)
    {
        SafeLogError(api, (std::string("[oChatLogger] Init failed: ") + e.what()).c_str());
        ResetState();
        return false;
    }
    catch (...)
    {
        SafeLogError(api, "[oChatLogger] Init failed with unknown exception.");
        ResetState();
        return false;
    }
}

extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown()
{
    try
    {
        if (g_HasApi && g_ChatRegistrationId != 0 && g_Api.UnregisterChatMessageEventWithOwnerToken)
        {
            g_Api.UnregisterChatMessageEventWithOwnerToken(g_OwnerToken, g_ChatRegistrationId);
            g_ChatRegistrationId = 0;
        }
        SafeLogInfo("[oChatLogger] Shutdown.");
    }
    catch (...)
    {
    }
    ResetState();
}
