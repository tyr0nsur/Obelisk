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
    uint64_t g_ChatMessageEventHandle = 0;
    uint64_t g_ChatMessageEventUserData = 0xC0FFEE02;
    bool g_ChatMessageEventSeen = false;

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

    void OnChatMessageEvent(const ObeliskChatMessageEvent* event, void* userData)
    {
        if (event &&
            event->abi_version == OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION &&
            event->struct_size >= sizeof(ObeliskChatMessageEvent) &&
            event->send_mode == OBELISK_CHAT_SEND_MODE_GLOBAL &&
            (event->flags & OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD) != 0 &&
            event->sequence != 0 &&
            event->message.data &&
            event->message.size == 5 &&
            userData == &g_ChatMessageEventUserData &&
            std::memcmp(event->message.data, "!ping", 5) == 0)
        {
            g_ChatMessageEventSeen = true;
        }
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

    bool ValidateStructureResourceKindDescriptor(const ObeliskApi* api)
    {
        if (!api ||
            (api->capabilities & OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS) == 0 ||
            api->struct_size < offsetof(ObeliskApi, DescribeResourceKind) + sizeof(api->DescribeResourceKind) ||
            !api->DescribeResourceKind)
        {
            return true;
        }

        ObeliskResourceKindDescriptor descriptor{};
        descriptor.struct_size = sizeof(ObeliskResourceKindDescriptor);
        if (!api->DescribeResourceKind(OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE, &descriptor))
            return false;

        constexpr uint64_t kRequiredFlags = OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY |
            OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY |
            OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP;
        return descriptor.abi_version == OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION &&
            descriptor.struct_size >= sizeof(ObeliskResourceKindDescriptor) &&
            descriptor.resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE &&
            (descriptor.flags & kRequiredFlags) == kRequiredFlags &&
            (descriptor.supported_gameplay_policy_event_mask &
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES) ==
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES &&
            (descriptor.supported_gameplay_policy_field_mask &
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE) != 0 &&
            std::strcmp(descriptor.stable_name, "structure") == 0;
    }

    bool ValidateGameplayPolicyEventDescriptor(const ObeliskApi* api)
    {
        if (!api ||
            (api->capabilities & OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS) == 0 ||
            api->struct_size < offsetof(ObeliskApi, DescribeGameplayPolicyEventKind) +
                sizeof(api->DescribeGameplayPolicyEventKind) ||
            !api->DescribeGameplayPolicyEventKind)
        {
            return true;
        }

        ObeliskGameplayPolicyEventDescriptor descriptor{};
        descriptor.struct_size = sizeof(ObeliskGameplayPolicyEventDescriptor);
        if (!api->DescribeGameplayPolicyEventKind(
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE,
                &descriptor))
        {
            return false;
        }

        return descriptor.abi_version == OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION &&
            descriptor.struct_size >= sizeof(ObeliskGameplayPolicyEventDescriptor) &&
            descriptor.event_kind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE &&
            descriptor.resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE &&
            (descriptor.flags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD) != 0 &&
            (descriptor.flags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED) != 0 &&
            descriptor.event_kind_mask == OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_VARIANT_CHANGE &&
            (descriptor.field_mask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX) != 0 &&
            std::strcmp(descriptor.stable_name, "structure.variant_change") == 0;
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
        g_OwnerToken = 0;
        g_ProcessEventHandle = 0;
        g_ChatMessageEventHandle = 0;
        g_ChatMessageEventSeen = false;
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

        if (HasChatMessageEventApi(api))
        {
            g_ChatMessageEventHandle = api->RegisterChatMessageEventWithOwnerTokenHandle(
                g_OwnerToken,
                OnChatMessageEvent,
                &g_ChatMessageEventUserData);
            if (g_ChatMessageEventHandle == 0)
            {
                ResetState();
                return false;
            }
        }

        if (!ValidateStructureResourceKindDescriptor(api))
        {
            ResetState();
            return false;
        }
        if (!ValidateGameplayPolicyEventDescriptor(api))
        {
            ResetState();
            return false;
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
        if (g_HasApi && g_ChatMessageEventHandle != 0 && g_Api.UnregisterChatMessageEventWithOwnerToken)
            g_Api.UnregisterChatMessageEventWithOwnerToken(g_OwnerToken, g_ChatMessageEventHandle);
    }
    catch (...)
    {
    }
    ResetState();
}

extern "C" __attribute__((visibility("default"))) bool InstallLayoutConsumer_ChatMessageEventSeen()
{
    return g_ChatMessageEventSeen;
}
