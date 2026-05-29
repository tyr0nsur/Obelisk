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
static uint64_t g_ChatMessageEventHandle = 0;
static uint64_t g_ChatMessageEventUserData = 0xC0FFEE02;

static void OnGameplayPolicyEvent(const ObeliskGameplayPolicyEvent* event, void* user_data)
{
    (void)user_data;
    if (event && event->struct_size >= sizeof(ObeliskGameplayPolicyEvent))
    {
        volatile uint32_t event_kind = event->event_kind;
        volatile uint64_t field_mask = event->field_mask;
        volatile int32_t variant_index =
            event->int32_values[OBELISK_GAMEPLAY_POLICY_FIELD_VARIANT_INDEX];
        volatile bool requested_by_player =
            (event->field_mask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER) != 0 &&
            (event->bool_values & (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_REQUESTED_BY_PLAYER)) != 0;
        volatile bool ignore_cooldown =
            (event->field_mask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN) != 0 &&
            (event->bool_values & (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_IGNORE_COOLDOWN)) != 0;
        (void)event_kind;
        (void)field_mask;
        (void)variant_index;
        (void)requested_by_player;
        (void)ignore_cooldown;
    }
}

static void OnChatMessageEvent(const ObeliskChatMessageEvent* event, void* user_data)
{
    if (event && event->struct_size >= sizeof(ObeliskChatMessageEvent))
    {
        volatile uint32_t send_mode = event->send_mode;
        volatile uint64_t flags = event->flags;
        volatile uint64_t sequence = event->sequence;
        volatile size_t message_size = event->message.size;
        volatile bool copied_payload =
            event->abi_version == OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION &&
            (event->flags & OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD) != 0 &&
            user_data == &g_ChatMessageEventUserData;
        (void)send_mode;
        (void)flags;
        (void)sequence;
        (void)message_size;
        (void)copied_payload;
    }
}

static void CompileGameplayPolicyAbi(void)
{
    volatile uint64_t capability = OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS;
    volatile uint64_t resource_descriptor_capability = OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS;
    volatile uint64_t chat_capability = OBELISK_API_CAPABILITY_CHAT_EVENTS;
    volatile uint64_t all_events = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL;
    volatile uint64_t all_structures = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES;
    volatile uint64_t all_inventory = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY;
    volatile uint64_t copied_payload = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD;
    volatile uint64_t inventory_backed = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED;
    volatile uint64_t return_value = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE;
    volatile uint64_t requested_by_player = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER;
    volatile uint64_t ignore_cooldown = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN;
    volatile uint64_t category_only = OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY;
    volatile uint64_t chat_copied_payload = OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD;
    ObeliskStringView chat_message_view = {"!ping", 5};
    ObeliskChatMessageEvent chat_event = {
        OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION,
        sizeof(ObeliskChatMessageEvent),
        OBELISK_CHAT_SEND_MODE_GLOBAL,
        0,
        OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD,
        1,
        {"!ping", 5},
    };
    ObeliskGameplayPolicyEvent event = {
        OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION,
        sizeof(ObeliskGameplayPolicyEvent),
        OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE,
        OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
        OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
            OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
        OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX,
        0,
        {0, 7, 0, 0, 0, 0},
    };
    ObeliskGameplayPolicyEvent inventory_remote_add_event = {
        OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION,
        sizeof(ObeliskGameplayPolicyEvent),
        OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK,
        OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
        OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
            OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
        OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER,
        (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE) |
            (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_REQUESTED_BY_PLAYER),
        {0, 0, 0, 0, 0, 0},
    };
    ObeliskGameplayPolicyEvent inventory_use_event = {
        OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION,
        sizeof(ObeliskGameplayPolicyEvent),
        OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK,
        OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
        OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
            OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
        OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN,
        1ull << OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE,
        {0, 0, 0, 0, 0, 0},
    };
    ObeliskResourceKindDescriptor descriptor = {
        OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION,
        sizeof(ObeliskResourceKindDescriptor),
        OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
        0,
        OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY |
            OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY |
            OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP,
        OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES,
        OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
        "structure",
        "Structure",
    };
    ObeliskGameplayPolicyEventDescriptor event_descriptor = {
        OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION,
        sizeof(ObeliskGameplayPolicyEventDescriptor),
        OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK,
        OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
        OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
            OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
        OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK,
        OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN,
        "inventory.use_check",
        "Inventory Use Check",
    };
    ObeliskGameplayPolicyEventCallback callback = OnGameplayPolicyEvent;
    ObeliskChatMessageEventCallback chat_callback = OnChatMessageEvent;
    callback(&event, NULL);
    callback(&inventory_remote_add_event, NULL);
    callback(&inventory_use_event, NULL);
    chat_callback(&chat_event, NULL);
    (void)capability;
    (void)resource_descriptor_capability;
    (void)chat_capability;
    (void)all_events;
    (void)all_structures;
    (void)all_inventory;
    (void)copied_payload;
    (void)inventory_backed;
    (void)return_value;
    (void)requested_by_player;
    (void)ignore_cooldown;
    (void)category_only;
    (void)chat_copied_payload;
    (void)chat_message_view;
    (void)descriptor;
    (void)event_descriptor;
}

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

static bool HasChatMessageEventApi(const ObeliskApi* api)
{
    return api &&
        (api->capabilities & OBELISK_API_CAPABILITY_CHAT_EVENTS) != 0 &&
        api->struct_size >= offsetof(ObeliskApi, UnregisterChatMessageEventWithOwnerToken) +
            sizeof(api->UnregisterChatMessageEventWithOwnerToken) &&
        api->RegisterChatMessageEventWithOwnerTokenHandle &&
        api->UnregisterChatMessageEventWithOwnerToken;
}

static bool ValidateStructureResourceKindDescriptor(const ObeliskApi* api)
{
    ObeliskResourceKindDescriptor descriptor;
    const uint64_t required_flags = OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY |
        OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY |
        OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP;

    if (!api ||
        (api->capabilities & OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS) == 0 ||
        api->struct_size < offsetof(ObeliskApi, DescribeResourceKind) + sizeof(api->DescribeResourceKind) ||
        !api->DescribeResourceKind)
    {
        return true;
    }

    memset(&descriptor, 0, sizeof(descriptor));
    descriptor.struct_size = sizeof(ObeliskResourceKindDescriptor);
    if (!api->DescribeResourceKind(OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE, &descriptor))
        return false;

    return descriptor.abi_version == OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION &&
        descriptor.struct_size >= sizeof(ObeliskResourceKindDescriptor) &&
        descriptor.resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE &&
        (descriptor.flags & required_flags) == required_flags &&
        (descriptor.supported_gameplay_policy_event_mask &
            OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES) ==
            OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES &&
        (descriptor.supported_gameplay_policy_field_mask &
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE) != 0 &&
        strcmp(descriptor.stable_name, "structure") == 0;
}

static bool ValidateGameplayPolicyEventDescriptor(const ObeliskApi* api)
{
    ObeliskGameplayPolicyEventDescriptor descriptor;

    if (!api ||
        (api->capabilities & OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS) == 0 ||
        api->struct_size < offsetof(ObeliskApi, DescribeGameplayPolicyEventKind) +
            sizeof(api->DescribeGameplayPolicyEventKind) ||
        !api->DescribeGameplayPolicyEventKind)
    {
        return true;
    }

    memset(&descriptor, 0, sizeof(descriptor));
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
        strcmp(descriptor.stable_name, "structure.variant_change") == 0;
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

    if (!ValidateStructureResourceKindDescriptor(api))
        return false;
    if (!ValidateGameplayPolicyEventDescriptor(api))
        return false;

    if (HasProcessEventHandleApi(api))
    {
        g_ProcessEventHandle = api->RegisterPreProcessEventForNameIndexWithOwnerTokenHandle(
            g_OwnerToken,
            42,
            OnProcessEvent);
        if (g_ProcessEventHandle == 0)
            return false;
    }

    if (HasChatMessageEventApi(api))
    {
        g_ChatMessageEventHandle = api->RegisterChatMessageEventWithOwnerTokenHandle(
            g_OwnerToken,
            OnChatMessageEvent,
            &g_ChatMessageEventUserData);
        if (g_ChatMessageEventHandle == 0)
            return false;
    }

    CompileGameplayPolicyAbi();
    return true;
}

__attribute__((visibility("default"))) void ObeliskPlugin_Shutdown(void)
{
    if (g_HasApi && g_ProcessEventHandle != 0 && g_Api.UnregisterProcessEventCallbackWithOwnerToken)
        g_Api.UnregisterProcessEventCallbackWithOwnerToken(g_OwnerToken, g_ProcessEventHandle);
    if (g_HasApi && g_ChatMessageEventHandle != 0 && g_Api.UnregisterChatMessageEventWithOwnerToken)
        g_Api.UnregisterChatMessageEventWithOwnerToken(g_OwnerToken, g_ChatMessageEventHandle);

    memset(&g_Api, 0, sizeof(g_Api));
    g_HasApi = false;
    g_OwnerToken = 0;
    g_ProcessEventHandle = 0;
    g_ChatMessageEventHandle = 0;
}
