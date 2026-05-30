#include <obelisk/ObeliskApi.h>

#include <stdatomic.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static ObeliskApi g_Api;
static bool g_HasApi = false;
static uint64_t g_OwnerToken = 0;
static uint64_t g_ChatRegistrationId = 0;
static uint64_t g_UserData = 0xC0A71066;
static atomic_uint_fast64_t g_ModeEventCounts[OBELISK_CHAT_SEND_MODE_COUNT];

enum
{
    kConfigMaxBytes = 8192,
    kPerModeLogLimit = 16
};

static const char* kDefaultConfig =
    "{\n"
    "  \"enabled\": false,\n"
    "  \"allow_all_instances\": false,\n"
    "  \"instance_allowlist\": []\n"
    "}\n";

static const size_t kRequiredBaseApiSize = offsetof(ObeliskApi, capabilities) + sizeof(((ObeliskApi*)0)->capabilities);

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

static const char* SkipWhitespace(const char* cursor)
{
    while (cursor && (*cursor == ' ' || *cursor == '\t' || *cursor == '\r' || *cursor == '\n'))
        ++cursor;
    return cursor;
}

static bool ReadConfigFile(const char* path, char* buffer, size_t bufferSize)
{
    if (!path || path[0] == '\0' || !buffer || bufferSize == 0)
        return false;

    FILE* file = fopen(path, "rb");
    if (!file)
        return false;

    const size_t bytesRead = fread(buffer, 1u, bufferSize - 1u, file);
    const bool readError = ferror(file) != 0;
    const int next = fgetc(file);
    fclose(file);

    if (readError || next != EOF)
        return false;

    buffer[bytesRead] = '\0';
    return true;
}

static bool JsonBoolValue(const char* document, const char* key, bool* out)
{
    if (!document || !key || !out)
        return false;

    char quotedKey[96];
    if (snprintf(quotedKey, sizeof(quotedKey), "\"%s\"", key) >= (int)sizeof(quotedKey))
        return false;

    const char* cursor = strstr(document, quotedKey);
    if (!cursor)
        return false;
    cursor += strlen(quotedKey);
    cursor = SkipWhitespace(cursor);
    if (!cursor || *cursor != ':')
        return false;
    cursor = SkipWhitespace(cursor + 1);
    if (!cursor)
        return false;
    if (strncmp(cursor, "true", 4u) == 0)
    {
        *out = true;
        return true;
    }
    if (strncmp(cursor, "false", 5u) == 0)
    {
        *out = false;
        return true;
    }
    return false;
}

static bool InstanceAllowlistContains(const char* document, const char* instanceId)
{
    if (!document || !instanceId || instanceId[0] == '\0')
        return false;

    const char* cursor = strstr(document, "\"instance_allowlist\"");
    if (!cursor)
        return false;
    cursor = strchr(cursor, '[');
    if (!cursor)
        return false;
    ++cursor;

    while (*cursor)
    {
        cursor = SkipWhitespace(cursor);
        if (!cursor || *cursor == ']')
            return false;
        if (*cursor != '"')
            return false;
        ++cursor;
        const char* end = strchr(cursor, '"');
        if (!end)
            return false;
        if ((size_t)(end - cursor) == strlen(instanceId) &&
            strncmp(cursor, instanceId, (size_t)(end - cursor)) == 0)
            return true;
        cursor = SkipWhitespace(end + 1);
        if (!cursor)
            return false;
        if (*cursor == ',')
        {
            ++cursor;
            continue;
        }
        if (*cursor == ']')
            return false;
        return false;
    }

    return false;
}

static bool LoadRuntimeEnabled(const ObeliskPluginInitContext* context, bool* runtimeEnabled)
{
    if (!context || !runtimeEnabled)
        return false;

    char config[kConfigMaxBytes];
    if (!ReadConfigFile(context->config_path, config, sizeof(config)))
        return false;

    bool enabled = false;
    if (!JsonBoolValue(config, "enabled", &enabled))
        return false;
    if (!enabled)
    {
        *runtimeEnabled = false;
        return true;
    }

    bool allowAllInstances = false;
    if (JsonBoolValue(config, "allow_all_instances", &allowAllInstances) && allowAllInstances)
    {
        *runtimeEnabled = true;
        return true;
    }

    *runtimeEnabled = InstanceAllowlistContains(config, context->instance_id);
    return true;
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

    const unsigned sendMode = event->send_mode;
    const uint_fast64_t previousCount =
        atomic_fetch_add_explicit(&g_ModeEventCounts[sendMode], 1u, memory_order_relaxed);
    if (previousCount >= kPerModeLogLimit)
        return;

    const uint_fast64_t modeCount = previousCount + 1u;
    char buffer[240];
    snprintf(buffer,
             sizeof(buffer),
             "[oChatLogger] ChatMessageEvent received sequence=%llu send_mode=%u flags=0x%llx message_size=%zu. "
             "mode_count=%llu first_observed=%s.",
             (unsigned long long)event->sequence,
             sendMode,
             (unsigned long long)event->flags,
             event->message.size,
             (unsigned long long)modeCount,
             modeCount == 1u ? "true" : "false");
    SafeLogInfo(buffer);
}

static void ResetState(void)
{
    g_Api = (ObeliskApi){0};
    g_HasApi = false;
    g_OwnerToken = 0;
    g_ChatRegistrationId = 0;
    for (unsigned i = 0; i < OBELISK_CHAT_SEND_MODE_COUNT; ++i)
        atomic_store_explicit(&g_ModeEventCounts[i], 0u, memory_order_relaxed);
}

static void CopyApiPrefix(const ObeliskApi* api)
{
    g_Api = (ObeliskApi){0};
    if (!api)
    {
        g_HasApi = false;
        return;
    }

    const size_t copySize = api->struct_size < sizeof(g_Api) ? api->struct_size : sizeof(g_Api);
    memcpy(&g_Api, api, copySize);
    g_HasApi = true;
}

__attribute__((visibility("default"))) bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out)
{
    if (!out)
        return false;

    out->abi_version = OBELISK_PLUGIN_METADATA_ABI_VERSION;
    out->struct_size = sizeof(ObeliskPluginMetadata);
    out->plugin_id = "oChatLogger";
    out->name = "oChatLogger";
    out->version = "0.1.0-rc.2";
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
        api->struct_size < kRequiredBaseApiSize ||
        context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
        context->struct_size < sizeof(ObeliskPluginInitContext) ||
        context->plugin_owner_token == 0)
    {
        if (api && api->LogError)
            api->LogError("[oChatLogger] Incompatible Obelisk API.");
        return false;
    }

    CopyApiPrefix(api);
    g_OwnerToken = context->plugin_owner_token;
    for (unsigned i = 0; i < OBELISK_CHAT_SEND_MODE_COUNT; ++i)
        atomic_store_explicit(&g_ModeEventCounts[i], 0u, memory_order_relaxed);

    bool runtimeEnabled = false;
    if (!LoadRuntimeEnabled(context, &runtimeEnabled))
    {
        api->LogError("[oChatLogger] Invalid config.");
        ResetState();
        return false;
    }
    if (!runtimeEnabled)
    {
        api->LogInfo("[oChatLogger] Disabled by config.");
        return true;
    }

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
        &g_UserData);
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
