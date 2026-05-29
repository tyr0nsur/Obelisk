#include <obelisk/ObeliskApi.h>

#include <stdatomic.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

static ObeliskApi g_Api;
static bool g_HasApi = false;
static uint64_t g_OwnerToken = 0;
static uint64_t g_ChatRegistrationId = 0;
static atomic_int g_LoggedEvents = 0;

enum
{
    kLogLimit = 5
};

static const char* kDefaultConfig =
    "{\n"
    "  \"enabled\": false,\n"
    "  \"allow_all_instances\": false,\n"
    "  \"instance_allowlist\": []\n"
    "}\n";

static void SafeLogInfo(const char* message)
{
    if (g_HasApi && g_Api.LogInfo)
        g_Api.LogInfo(message);
}

static void SafeLogError(const char* message)
{
    if (g_HasApi && g_Api.LogError)
        g_Api.LogError(message);
}

static bool HasChatMessageEventApi(const ObeliskApi* api)
{
    return api &&
        (api->capabilities & OBELISK_API_CAPABILITY_CHAT_EVENTS) != 0 &&
        api->struct_size >= offsetof(ObeliskApi, UnregisterChatMessageEventWithOwnerToken) +
            sizeof(api->UnregisterChatMessageEventWithOwnerToken) &&
        api->RegisterChatMessageEventWithOwnerTokenHandle &&
        api->UnregisterChatMessageEventWithOwnerToken;
}

static void OnChatMessageEvent(const ObeliskChatMessageEvent* event, void* user_data)
{
    (void)user_data;
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

    if (atomic_fetch_add_explicit(&g_LoggedEvents, 1, memory_order_relaxed) >= kLogLimit)
        return;

    char buffer[192];
    snprintf(buffer,
             sizeof(buffer),
             "[oChatLogger] ChatMessageEvent received sequence=%llu send_mode=%u flags=0x%llx message_size=%zu.",
             (unsigned long long)event->sequence,
             (unsigned)event->send_mode,
             (unsigned long long)event->flags,
             event->message.size);
    SafeLogInfo(buffer);
}

static void ResetState(void)
{
    g_Api = (ObeliskApi){0};
    g_HasApi = false;
    g_OwnerToken = 0;
    g_ChatRegistrationId = 0;
    atomic_store_explicit(&g_LoggedEvents, 0, memory_order_relaxed);
}

__attribute__((visibility("default"))) bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out)
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

__attribute__((visibility("default"))) bool ObeliskPlugin_Init(
    ObeliskApi* api,
    const ObeliskPluginInitContext* context)
{
    if (!api || !context)
        return false;
    if (api->abi_version != OBELISK_API_ABI_VERSION ||
        api->struct_size < sizeof(ObeliskApi) ||
        context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
        context->struct_size < sizeof(ObeliskPluginInitContext) ||
        context->plugin_owner_token == 0)
    {
        if (api && api->LogError)
            api->LogError("[oChatLogger] Incompatible Obelisk API.");
        return false;
    }

    g_Api = *api;
    g_HasApi = true;
    g_OwnerToken = context->plugin_owner_token;
    atomic_store_explicit(&g_LoggedEvents, 0, memory_order_relaxed);

    api->LogInfo("[oChatLogger] Loaded.");
    if (!HasChatMessageEventApi(api))
    {
        api->LogError("[oChatLogger] ChatMessageEvent API is not available.");
        ResetState();
        return false;
    }

    g_ChatRegistrationId = api->RegisterChatMessageEventWithOwnerTokenHandle(
        context->plugin_owner_token,
        OnChatMessageEvent,
        NULL);
    if (g_ChatRegistrationId == 0)
    {
        api->LogError("[oChatLogger] Failed to register ChatMessageEvent callback.");
        ResetState();
        return false;
    }

    api->LogInfo("[oChatLogger] Registered ChatMessageEvent callback.");
    return true;
}

__attribute__((visibility("default"))) void ObeliskPlugin_Shutdown(void)
{
    if (g_HasApi && g_ChatRegistrationId != 0 && g_Api.UnregisterChatMessageEventWithOwnerToken)
    {
        g_Api.UnregisterChatMessageEventWithOwnerToken(g_OwnerToken, g_ChatRegistrationId);
        g_ChatRegistrationId = 0;
    }
    SafeLogInfo("[oChatLogger] Shutdown.");
    ResetState();
}
