#include <obelisk/ObeliskApi.h>
#include <nlohmann/json.hpp>

#include <algorithm>
#include <cstring>
#include <fstream>
#include <string>

namespace
{
    ObeliskApi g_Api{};
    uint64_t g_OwnerToken = 0;
    uint64_t g_Registration = 0;
    uint64_t g_WhoamiRegistration = 0;
    uint64_t g_LifecycleRegistration = 0;
    constexpr const char* kDefaultConfig =
        "{\n  \"enabled\": false,\n  \"allow_all_instances\": false,\n  \"instance_allowlist\": []\n}\n";

    void LogError(const char* message)
    {
        if (g_Api.LogError)
            g_Api.LogError(message);
    }

    bool EnabledForInstance(const ObeliskPluginInitContext& context, bool& enabled)
    {
        if (!context.config_path || !context.instance_id)
            return false;
        std::ifstream stream(context.config_path, std::ios::binary);
        if (!stream)
            return false;
        std::string text(8193, '\0');
        stream.read(text.data(), static_cast<std::streamsize>(text.size()));
        const auto count = stream.gcount();
        if (count > 8192 || stream.bad())
            return false;
        text.resize(static_cast<size_t>(count));
        const auto document = nlohmann::json::parse(text, nullptr, false);
        if (!document.is_object() || !document.contains("enabled") || !document["enabled"].is_boolean() ||
            !document.contains("allow_all_instances") || !document["allow_all_instances"].is_boolean() ||
            !document.contains("instance_allowlist") || !document["instance_allowlist"].is_array())
            return false;
        enabled = false;
        for (const auto& instance : document["instance_allowlist"])
        {
            if (!instance.is_string())
                return false;
            if (instance.get<std::string>() == context.instance_id)
                enabled = true;
        }
        enabled = document["enabled"].get<bool>() &&
                  (document["allow_all_instances"].get<bool>() || enabled);
        return true;
    }

    void OnPing(const ObeliskCommandInvocation* invocation, void*)
    {
        if (!invocation || invocation->abi_version != OBELISK_COMMAND_INVOCATION_ABI_VERSION ||
            invocation->struct_size < sizeof(ObeliskCommandInvocation) || !invocation->invocation_token ||
            invocation->send_mode > OBELISK_CHAT_SEND_MODE_MAX || !invocation->command_text.data ||
            invocation->command_text.size != 5 || std::memcmp(invocation->command_text.data, "/ping", 5) != 0)
            return;
        if (!g_Api.ReplyToCommandWithOwnerToken(g_OwnerToken, invocation->invocation_token, {"pong", 4}))
            LogError("[oPing] The synchronous reply backend rejected pong.");
    }

    bool HasPlayerApi()
    {
        return g_Api.struct_size >= offsetof(ObeliskApi, GetCommandPlayerWithOwnerToken) +
                                      sizeof(g_Api.GetCommandPlayerWithOwnerToken) &&
               (g_Api.capabilities & OBELISK_API_CAPABILITY_COMMAND_PLAYER_SNAPSHOT) &&
               g_Api.GetCommandPlayerWithOwnerToken;
    }

    void OnWhoami(const ObeliskCommandInvocation* invocation, void*)
    {
        if (!invocation || invocation->abi_version != OBELISK_COMMAND_INVOCATION_ABI_VERSION ||
            invocation->struct_size < sizeof(ObeliskCommandInvocation) || !invocation->invocation_token ||
            invocation->send_mode > OBELISK_CHAT_SEND_MODE_MAX || !invocation->command_text.data ||
            invocation->command_text.size != 7 || std::memcmp(invocation->command_text.data, "/whoami", 7) != 0 ||
            !HasPlayerApi())
            return;
        ObeliskCommandPlayer player{};
        player.struct_size = sizeof(player);
        std::string response = "Identidad no disponible para este comando.";
        if (g_Api.GetCommandPlayerWithOwnerToken(g_OwnerToken, invocation->invocation_token, &player) &&
            player.abi_version == OBELISK_COMMAND_PLAYER_ABI_VERSION && player.struct_size >= sizeof(player))
        {
            response = "Nombre: ";
            if ((player.flags & OBELISK_COMMAND_PLAYER_FLAG_NAME_AVAILABLE) && player.player_name.data &&
                player.player_name.size <= OBELISK_COMMAND_PLAYER_NAME_MAX_BYTES)
                response.append(player.player_name.data, player.player_name.size);
            else
                response += "no disponible";
            response += " | ID nativo: ";
            if ((player.flags & OBELISK_COMMAND_PLAYER_FLAG_PLATFORM_ID_AVAILABLE) && player.platform_id.data &&
                player.platform_id.size <= OBELISK_COMMAND_PLAYER_PLATFORM_ID_MAX_BYTES)
                response.append(player.platform_id.data, player.platform_id.size);
            else
                response += "no disponible";
        }
        if (!g_Api.ReplyToCommandWithOwnerToken(g_OwnerToken, invocation->invocation_token,
                                               {response.data(), response.size()}))
            LogError("[oPing] The synchronous reply backend rejected whoami.");
    }

    bool HasLifecycleApi()
    {
        return g_Api.struct_size >= offsetof(ObeliskApi, UnregisterPlayerLifecycleWithOwnerToken) +
                                      sizeof(g_Api.UnregisterPlayerLifecycleWithOwnerToken) &&
               (g_Api.capabilities & OBELISK_API_CAPABILITY_PLAYER_LIFECYCLE_EVENTS) &&
               g_Api.RegisterPlayerLifecycleWithOwnerTokenHandle && g_Api.UnregisterPlayerLifecycleWithOwnerToken;
    }

    void OnLifecycle(const ObeliskPlayerLifecycleEvent* event, void*)
    {
        if (!event || event->abi_version != OBELISK_PLAYER_LIFECYCLE_EVENT_ABI_VERSION ||
            event->struct_size < sizeof(*event) || !event->sequence || !event->process_epoch ||
            (event->kind != OBELISK_PLAYER_LIFECYCLE_KIND_LOGIN_OBSERVED &&
             event->kind != OBELISK_PLAYER_LIFECYCLE_KIND_LOGOUT_OBSERVED) ||
            (event->flags & ~OBELISK_PLAYER_LIFECYCLE_FLAGS_SUPPORTED_MASK))
            return;
        try
        {
            nlohmann::json details{
                {"kind", event->kind == OBELISK_PLAYER_LIFECYCLE_KIND_LOGIN_OBSERVED ? "login_observed" : "logout_observed"},
                {"sequence", event->sequence}, {"process_epoch", event->process_epoch}, {"flags", event->flags},
                {"player_name", nullptr}, {"platform_id", nullptr}, {"observation_only", true}};
            if ((event->flags & OBELISK_PLAYER_LIFECYCLE_FLAG_NAME_AVAILABLE) && event->player_name.data &&
                event->player_name.size <= OBELISK_PLAYER_LIFECYCLE_NAME_MAX_BYTES)
                details["player_name"] = std::string(event->player_name.data, event->player_name.size);
            if ((event->flags & OBELISK_PLAYER_LIFECYCLE_FLAG_PLATFORM_ID_AVAILABLE) && event->platform_id.data &&
                event->platform_id.size <= OBELISK_PLAYER_LIFECYCLE_PLATFORM_ID_MAX_BYTES)
                details["platform_id"] = std::string(event->platform_id.data, event->platform_id.size);
            if (g_Api.LogInfo)
            {
                const auto message = "[oPing] Player lifecycle observation: " + details.dump();
                g_Api.LogInfo(message.c_str());
            }
        }
        catch (...)
        {
            // Logging is observational and must never escape into the UE event.
        }
    }
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out)
{
    if (!out)
        return false;
    *out = {OBELISK_PLUGIN_METADATA_ABI_VERSION, sizeof(ObeliskPluginMetadata),
            "oPing", "oPing", "0.1.1-prototype", "config.json", kDefaultConfig};
    return true;
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(
    ObeliskApi* api, const ObeliskPluginInitContext* context)
{
    if (!api || !context || g_Registration || g_WhoamiRegistration || g_LifecycleRegistration ||
        api->abi_version != OBELISK_API_ABI_VERSION ||
        api->struct_size < offsetof(ObeliskApi, capabilities) + sizeof(api->capabilities) ||
        context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
        context->struct_size < sizeof(ObeliskPluginInitContext) || !context->plugin_owner_token)
        return false;
    g_Api = {};
    std::memcpy(&g_Api, api, std::min<size_t>(api->struct_size, sizeof(g_Api)));
    g_OwnerToken = context->plugin_owner_token;
    try
    {
        bool enabled = false;
        if (!EnabledForInstance(*context, enabled))
        {
            LogError("[oPing] Invalid config.");
            return false;
        }
        if (!enabled)
        {
            if (g_Api.LogInfo)
                g_Api.LogInfo("[oPing] Disabled by config.");
            return true;
        }
        if (g_Api.struct_size < offsetof(ObeliskApi, ReplyToCommandWithOwnerToken) +
                                  sizeof(g_Api.ReplyToCommandWithOwnerToken) ||
            !(g_Api.capabilities & OBELISK_API_CAPABILITY_COMMAND_REPLIES) ||
            !g_Api.RegisterCommandWithOwnerTokenHandle || !g_Api.UnregisterCommandWithOwnerToken ||
            !g_Api.ReplyToCommandWithOwnerToken)
        {
            LogError("[oPing] Verified command/reply backend is unavailable.");
            return false;
        }
        g_Registration = g_Api.RegisterCommandWithOwnerTokenHandle(g_OwnerToken, "/ping", OnPing, nullptr);
        if (!g_Registration)
        {
            LogError("[oPing] Command registration failed.");
            return false;
        }
        if (HasPlayerApi())
        {
            g_WhoamiRegistration = g_Api.RegisterCommandWithOwnerTokenHandle(g_OwnerToken, "/whoami", OnWhoami, nullptr);
            if (!g_WhoamiRegistration)
            {
                g_Api.UnregisterCommandWithOwnerToken(g_OwnerToken, g_Registration);
                g_Registration = 0;
                LogError("[oPing] Whoami registration failed.");
                return false;
            }
            if (g_Api.LogInfo)
                g_Api.LogInfo("[oPing] /whoami registered; native IDs are copied observations, without storefront inference.");
        }
        if (HasLifecycleApi())
        {
            g_LifecycleRegistration = g_Api.RegisterPlayerLifecycleWithOwnerTokenHandle(g_OwnerToken, OnLifecycle, nullptr);
            if (!g_LifecycleRegistration)
            {
                LogError("[oPing] Player lifecycle observation registration failed.");
                return false; // PluginManager drains all registered families after init failure.
            }
            if (g_Api.LogInfo)
                g_Api.LogInfo("[oPing] Typed player lifecycle observations registered; these events are not authentication results.");
        }
        if (g_Api.LogInfo)
            g_Api.LogInfo("[oPing] /ping registered; replies are synchronous and targeted to this invocation.");
        return true;
    }
    catch (...)
    {
        LogError("[oPing] Initialization failed.");
        return false;
    }
}

extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown()
{
    if (g_LifecycleRegistration && g_Api.UnregisterPlayerLifecycleWithOwnerToken)
        g_Api.UnregisterPlayerLifecycleWithOwnerToken(g_OwnerToken, g_LifecycleRegistration);
    if (g_WhoamiRegistration && g_Api.UnregisterCommandWithOwnerToken)
        g_Api.UnregisterCommandWithOwnerToken(g_OwnerToken, g_WhoamiRegistration);
    if (g_Registration && g_Api.UnregisterCommandWithOwnerToken)
        g_Api.UnregisterCommandWithOwnerToken(g_OwnerToken, g_Registration);
    g_Registration = 0;
    g_WhoamiRegistration = 0;
    g_LifecycleRegistration = 0;
    g_OwnerToken = 0;
    g_Api = {};
}
