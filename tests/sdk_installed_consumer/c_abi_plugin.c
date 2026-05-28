#include <obelisk/ObeliskApi.h>

#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <sys/stat.h>

static const char* kDefaultConfig = "{\n"
    "  \"enabled\": false,\n"
    "  \"allow_all_instances\": false,\n"
    "  \"instance_allowlist\": []\n"
    "}\n";

static ObeliskApi g_Api;
static bool g_HasApi = false;
static uint64_t g_OwnerToken = 0;
static uint64_t g_ProcessEventHandle = 0;

static bool PathExists(const char* path)
{
    struct stat st;
    return path && stat(path, &st) == 0;
}

static bool OnProcessEvent(void* object, void* function, void* params)
{
    (void)object;
    (void)function;
    (void)params;
    return true;
}

static bool HasProcessEventHandleApi(const ObeliskApi* api)
{
    return api &&
        (api->capabilities & OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS) != 0 &&
        (api->capabilities & OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES) != 0 &&
        api->struct_size >= offsetof(ObeliskApi, UnregisterProcessEventCallbackWithOwnerToken) +
            sizeof(api->UnregisterProcessEventCallbackWithOwnerToken) &&
        api->RegisterPreProcessEventForNameIndexWithOwnerTokenHandle &&
        api->UnregisterProcessEventCallbackWithOwnerToken;
}

__attribute__((visibility("default"))) bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out)
{
    if (!out)
        return false;

    out->abi_version = OBELISK_PLUGIN_METADATA_ABI_VERSION;
    out->struct_size = sizeof(ObeliskPluginMetadata);
    out->plugin_id = "install_layout_c_abi_consumer";
    out->name = "Install Layout C ABI Consumer";
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
        context->struct_size < sizeof(ObeliskPluginInitContext))
    {
        return false;
    }

    g_Api = *api;
    g_HasApi = true;
    g_OwnerToken = context->plugin_owner_token;

    if (!context->config_dir ||
        !context->config_path ||
        !context->instance_id ||
        context->plugin_owner_token == 0 ||
        strcmp(context->instance_id, "install-layout-test") != 0 ||
        !PathExists(context->config_dir) ||
        !PathExists(context->config_path))
    {
        return false;
    }

    if (HasProcessEventHandleApi(api))
    {
        g_ProcessEventHandle = api->RegisterPreProcessEventForNameIndexWithOwnerTokenHandle(
            g_OwnerToken,
            42,
            OnProcessEvent);
        if (g_ProcessEventHandle == 0)
            return false;
    }

    return true;
}

__attribute__((visibility("default"))) void ObeliskPlugin_Shutdown(void)
{
    if (g_HasApi && g_ProcessEventHandle != 0 && g_Api.UnregisterProcessEventCallbackWithOwnerToken)
        g_Api.UnregisterProcessEventCallbackWithOwnerToken(g_OwnerToken, g_ProcessEventHandle);

    memset(&g_Api, 0, sizeof(g_Api));
    g_HasApi = false;
    g_OwnerToken = 0;
    g_ProcessEventHandle = 0;
}
