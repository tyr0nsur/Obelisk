#include <obelisk/ObeliskApi.h>

#include <cstddef>

namespace
{
    bool HasMinimalApiPrefix(const ObeliskApi* api)
    {
        if (!api ||
            api->struct_size < offsetof(ObeliskApi, capabilities) + sizeof(api->capabilities))
        {
            return false;
        }

        if (api->abi_version != OBELISK_API_ABI_VERSION)
            return false;

        return true;
    }

    constexpr const char* kDefaultConfig = R"json({
    "enabled": false,
    "allow_all_instances": false,
    "instance_allowlist": []
})json";
}

extern "C" __attribute__((visibility("default"))) bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out)
{
    try
    {
        if (!out)
            return false;

        out->abi_version = OBELISK_PLUGIN_METADATA_ABI_VERSION;
        out->struct_size = sizeof(ObeliskPluginMetadata);
        out->plugin_id = "install_layout_no_shutdown_consumer";
        out->name = "Install Layout No-Shutdown Consumer";
        out->version = "0.1.0-rc.2";
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

        return HasMinimalApiPrefix(api) &&
            context->abi_version == OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION &&
            context->struct_size >= sizeof(ObeliskPluginInitContext) &&
            context->config_dir != nullptr &&
            context->config_path != nullptr &&
            context->instance_id != nullptr &&
            context->plugin_owner_token != 0;
    }
    catch (...)
    {
        return false;
    }
}
