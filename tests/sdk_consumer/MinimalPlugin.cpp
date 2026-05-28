#include <obelisk/ObeliskApi.h>

#include <cstddef>
#include <cstdint>

namespace
{
    ObeliskApi* g_Api = nullptr;
    uint64_t g_OwnerToken = 0;
    uint64_t g_ProcessEventHandle = 0;

    constexpr const char* kDefaultConfig = R"json({
    "enabled": false,
    "allow_all_instances": false,
    "instance_allowlist": []
})json";

    bool OnProcessEvent(void*, void*, void*)
    {
        return true;
    }

    bool HasProcessEventHandleApi(const ObeliskApi* api)
    {
        return api &&
            (api->capabilities & OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES) != 0 &&
            api->struct_size >= offsetof(ObeliskApi, UnregisterProcessEventCallbackWithOwnerToken) +
                sizeof(api->UnregisterProcessEventCallbackWithOwnerToken) &&
            api->RegisterPreProcessEventForNameIndexWithOwnerTokenHandle &&
            api->UnregisterProcessEventCallbackWithOwnerToken;
    }
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out)
{
    if (!out)
        return false;

    out->abi_version = OBELISK_PLUGIN_METADATA_ABI_VERSION;
    out->struct_size = sizeof(ObeliskPluginMetadata);
    out->plugin_id = "sdk_consumer_minimal";
    out->name = "SDK Consumer Minimal";
    out->version = "0.1.0";
    out->config_file = "config.json";
    out->default_config_json = kDefaultConfig;
    return true;
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(
    ObeliskApi* api,
    const ObeliskPluginInitContext* context)
{
    if (!api || !context)
        return false;

    if (api->abi_version != OBELISK_API_ABI_VERSION ||
        api->struct_size < sizeof(ObeliskApi) ||
        context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
        context->struct_size < sizeof(ObeliskPluginInitContext))
    {
        return false;
    }

    g_Api = api;
    g_OwnerToken = context->plugin_owner_token;

    if (g_Api->LogInfo)
        g_Api->LogInfo("[sdk_consumer_minimal] Loaded.");

    if (HasProcessEventHandleApi(g_Api))
    {
        g_ProcessEventHandle = g_Api->RegisterPreProcessEventForNameIndexWithOwnerTokenHandle(
            g_OwnerToken,
            42,
            OnProcessEvent);
        if (g_ProcessEventHandle == 0)
            return false;
    }

    return true;
}

extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown()
{
    if (g_Api && g_ProcessEventHandle != 0)
        g_Api->UnregisterProcessEventCallbackWithOwnerToken(g_OwnerToken, g_ProcessEventHandle);

    if (g_Api && g_Api->LogInfo)
        g_Api->LogInfo("[sdk_consumer_minimal] Shutdown.");

    g_Api = nullptr;
    g_OwnerToken = 0;
    g_ProcessEventHandle = 0;
}
