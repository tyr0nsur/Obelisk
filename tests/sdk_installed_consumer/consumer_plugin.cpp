#include <obelisk/ObeliskApi.h>

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <sys/stat.h>

static_assert(OBELISK_API_ABI_VERSION == 1u, "unexpected Obelisk API ABI version");
static_assert(OBELISK_PLUGIN_METADATA_ABI_VERSION == 1u, "unexpected plugin metadata ABI version");
static_assert(OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION == 1u, "unexpected plugin init context ABI version");

namespace
{
    ObeliskApi g_Api{};
    bool g_HasApi = false;
    uint64_t g_OwnerToken = 0;
    uint64_t g_ProcessEventHandle = 0;

    constexpr const char* kDefaultConfig = R"json({
    "enabled": false,
    "allow_all_instances": false,
    "instance_allowlist": []
})json";

    bool PathExists(const char* path)
    {
        struct stat st {};
        return path && stat(path, &st) == 0;
    }

    bool OnProcessEvent(void*, void*, void*)
    {
        return true;
    }

    bool HasProcessEventHandleApi(const ObeliskApi* api)
    {
        return api &&
            (api->capabilities & OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS) != 0 &&
            (api->capabilities & OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES) != 0 &&
            api->struct_size >= offsetof(ObeliskApi, UnregisterProcessEventCallbackWithOwnerToken) +
                sizeof(api->UnregisterProcessEventCallbackWithOwnerToken) &&
            api->RegisterPreProcessEventForNameIndexWithOwnerTokenHandle &&
            api->UnregisterProcessEventCallbackWithOwnerToken;
    }

    void ResetState()
    {
        g_Api = {};
        g_HasApi = false;
        g_OwnerToken = 0;
        g_ProcessEventHandle = 0;
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
        out->plugin_id = "install_layout_consumer";
        out->name = "Install Layout Consumer";
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

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_Init(
    ObeliskApi* api,
    const ObeliskPluginInitContext* context)
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
            return false;
        }

        g_Api = *api;
        g_HasApi = true;
        g_OwnerToken = context->plugin_owner_token;

        const bool contextOk = context->config_dir &&
            context->config_path &&
            context->instance_id &&
            context->plugin_owner_token != 0 &&
            std::strcmp(context->instance_id, "install-layout-test") == 0 &&
            PathExists(context->config_dir) &&
            PathExists(context->config_path);
        if (!contextOk)
        {
            ResetState();
            return false;
        }

        if (HasProcessEventHandleApi(api))
        {
            g_ProcessEventHandle = api->RegisterPreProcessEventForNameIndexWithOwnerTokenHandle(
                g_OwnerToken,
                42,
                OnProcessEvent);
            if (g_ProcessEventHandle == 0)
            {
                ResetState();
                return false;
            }
        }

        return true;
    }
    catch (...)
    {
        ResetState();
        return false;
    }
}

extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown()
{
    try
    {
        if (g_HasApi && g_ProcessEventHandle != 0 && g_Api.UnregisterProcessEventCallbackWithOwnerToken)
            g_Api.UnregisterProcessEventCallbackWithOwnerToken(g_OwnerToken, g_ProcessEventHandle);
    }
    catch (...)
    {
    }
    ResetState();
}
