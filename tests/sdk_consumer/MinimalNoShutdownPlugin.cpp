#include <obelisk/ObeliskApi.h>

namespace
{
    constexpr const char* kDefaultConfig = R"json({
    "enabled": false,
    "instance_allowlist": []
})json";
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

    return api->abi_version == OBELISK_API_ABI_VERSION &&
        api->struct_size >= sizeof(ObeliskApi) &&
        context->abi_version == OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION &&
        context->struct_size >= sizeof(ObeliskPluginInitContext);
}
