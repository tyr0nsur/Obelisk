#include <obelisk/ObeliskApi.h>

#include <stddef.h>
#include <stdint.h>
#include <string.h>

static ObeliskApi g_Api;
static bool g_HasApi = false;
static uint64_t g_OwnerToken = 0;
static uint64_t g_GameplayPolicyEventHandle = 0;
static uint64_t g_GameplayPolicyEventUserData = 0xC0FFEE04;
static bool g_GameplayPolicyEventSeen = false;
static bool g_GameplayPolicyEventAccepted = false;
static uint64_t g_ChatMessageEventHandle = 0;
static uint64_t g_ChatMessageEventUserData = 0xC0FFEE03;
static bool g_ChatMessageEventSeen = false;
static bool g_ChatMessageEventAccepted = false;

static void OnGameplayPolicyEvent(const ObeliskGameplayPolicyEvent* event, void* user_data)
{
    g_GameplayPolicyEventSeen = true;
    g_GameplayPolicyEventAccepted = false;

    if (event &&
        event->abi_version == OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION &&
        event->struct_size >= sizeof(ObeliskGameplayPolicyEvent) &&
        (event->flags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD) != 0 &&
        user_data == &g_GameplayPolicyEventUserData)
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

        if (event->event_kind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE)
        {
            g_GameplayPolicyEventAccepted =
                event->resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE &&
                (event->flags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED) != 0 &&
                (event->field_mask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX) != 0 &&
                event->int32_values[OBELISK_GAMEPLAY_POLICY_FIELD_VARIANT_INDEX] == 7;
        }
        else if (event->event_kind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK)
        {
            g_GameplayPolicyEventAccepted =
                event->resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM &&
                (event->flags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED) != 0 &&
                requested_by_player;
        }
        else if (event->event_kind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK)
        {
            g_GameplayPolicyEventAccepted =
                event->resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM &&
                (event->flags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED) != 0 &&
                (event->field_mask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN) != 0;
        }
    }
}

static void OnCompileGameplayPolicyEvent(const ObeliskGameplayPolicyEvent* event, void* user_data)
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
    g_ChatMessageEventSeen = true;
    g_ChatMessageEventAccepted = false;

    if (!event ||
        event->abi_version != OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION ||
        event->struct_size < sizeof(ObeliskChatMessageEvent) ||
        event->send_mode > OBELISK_CHAT_SEND_MODE_MAX ||
        (event->flags & OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD) == 0 ||
        event->sequence == 0 ||
        !event->message.data ||
        event->message.size != 5 ||
        user_data != &g_ChatMessageEventUserData)
    {
        return;
    }

    g_ChatMessageEventAccepted =
        event->message.data[0] == 'h' &&
        event->message.data[1] == 'e' &&
        event->message.data[2] == 'l' &&
        event->message.data[3] == 'l' &&
        event->message.data[4] == 'o';
}

static void OnCompileChatMessageEvent(const ObeliskChatMessageEvent* event, void* user_data)
{
    (void)user_data;
    if (event && event->struct_size >= sizeof(ObeliskChatMessageEvent))
    {
        volatile uint32_t send_mode = event->send_mode;
        volatile uint64_t flags = event->flags;
        volatile uint64_t sequence = event->sequence;
        volatile size_t message_size = event->message.size;
        volatile bool copied_payload =
            event->abi_version == OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION &&
            (event->flags & OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD) != 0;
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
    volatile uint64_t event_descriptor_capability =
        OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS;
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
    volatile uint32_t event_descriptor_abi = OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION;
    volatile uint64_t chat_copied_payload = OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD;
    ObeliskStringView chat_message_view = {"hello", 5};
    ObeliskChatMessageEvent chat_event = {
        OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION,
        sizeof(ObeliskChatMessageEvent),
        OBELISK_CHAT_SEND_MODE_GLOBAL,
        0,
        OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD,
        1,
        {"hello", 5},
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
        OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE,
        OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
        OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
            OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
        OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_VARIANT_CHANGE,
        OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX,
        "structure.variant_change",
        "Structure Variant Change",
    };
    ObeliskGameplayPolicyEventCallback callback = OnCompileGameplayPolicyEvent;
    ObeliskChatMessageEventCallback chat_callback = OnCompileChatMessageEvent;
    callback(&event, NULL);
    callback(&inventory_remote_add_event, NULL);
    callback(&inventory_use_event, NULL);
    chat_callback(&chat_event, NULL);
    (void)capability;
    (void)resource_descriptor_capability;
    (void)event_descriptor_capability;
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
    (void)event_descriptor_abi;
    (void)chat_copied_payload;
    (void)chat_message_view;
    (void)descriptor;
    (void)event_descriptor;
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

static bool HasGameplayPolicyEventApi(const ObeliskApi* api)
{
    return api &&
        (api->capabilities & OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS) != 0 &&
        api->struct_size >= offsetof(ObeliskApi, UnregisterGameplayPolicyEventWithOwnerToken) +
            sizeof(api->UnregisterGameplayPolicyEventWithOwnerToken) &&
        api->RegisterGameplayPolicyEventWithOwnerTokenHandle &&
        api->UnregisterGameplayPolicyEventWithOwnerToken;
}

static bool ValidateResourceKindDescriptor(const ObeliskApi* api,
                                           uint32_t resource_kind,
                                           uint64_t expected_event_mask,
                                           uint64_t expected_field_mask,
                                           const char* stable_name)
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
    if (!api->DescribeResourceKind(resource_kind, &descriptor))
        return false;

    return descriptor.abi_version == OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION &&
        descriptor.struct_size >= sizeof(ObeliskResourceKindDescriptor) &&
        descriptor.resource_kind == resource_kind &&
        (descriptor.flags & required_flags) == required_flags &&
        descriptor.supported_gameplay_policy_event_mask == expected_event_mask &&
        descriptor.supported_gameplay_policy_field_mask == expected_field_mask &&
        strcmp(descriptor.stable_name, stable_name) == 0;
}

static bool ValidateResourceKindDescriptors(const ObeliskApi* api)
{
    if (!ValidateResourceKindDescriptor(
            api,
            OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
            OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES,
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX |
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET |
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE,
            "structure"))
        return false;

    if (!ValidateResourceKindDescriptor(
            api,
            OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
            OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY,
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER |
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN,
            "inventory_item"))
        return false;

    return true;
}

static void UnregisterCallbacks(void)
{
    if (g_HasApi && g_GameplayPolicyEventHandle != 0 && g_Api.UnregisterGameplayPolicyEventWithOwnerToken)
    {
        g_Api.UnregisterGameplayPolicyEventWithOwnerToken(g_OwnerToken, g_GameplayPolicyEventHandle);
        g_GameplayPolicyEventHandle = 0;
    }
    if (g_HasApi && g_ChatMessageEventHandle != 0 && g_Api.UnregisterChatMessageEventWithOwnerToken)
    {
        g_Api.UnregisterChatMessageEventWithOwnerToken(g_OwnerToken, g_ChatMessageEventHandle);
        g_ChatMessageEventHandle = 0;
    }
}

static void ResetState(void)
{
    g_Api = (ObeliskApi){0};
    g_HasApi = false;
    g_OwnerToken = 0;
    g_GameplayPolicyEventHandle = 0;
    g_GameplayPolicyEventSeen = false;
    g_GameplayPolicyEventAccepted = false;
    g_ChatMessageEventHandle = 0;
    g_ChatMessageEventSeen = false;
    g_ChatMessageEventAccepted = false;
}

static const char* kDefaultConfig = "{\n"
    "  \"enabled\": false,\n"
    "  \"allow_all_instances\": false,\n"
    "  \"instance_allowlist\": []\n"
    "}\n";

__attribute__((visibility("default"))) bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out)
{
    if (!out)
        return false;

    out->abi_version = OBELISK_PLUGIN_METADATA_ABI_VERSION;
    out->struct_size = sizeof(ObeliskPluginMetadata);
    out->plugin_id = "c_abi_minimal";
    out->name = "C ABI Minimal";
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
        api->struct_size < offsetof(ObeliskApi, capabilities) + sizeof(api->capabilities) ||
        context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
        context->struct_size < sizeof(ObeliskPluginInitContext))
    {
        return false;
    }

    if (!api->LogInfo || !context->config_dir || !context->config_path || !context->instance_id)
        return false;

    if (context->plugin_owner_token == 0)
        return false;

    if (!ValidateResourceKindDescriptors(api))
        return false;

    memset(&g_Api, 0, sizeof(g_Api));
    memcpy(&g_Api, api, api->struct_size < sizeof(g_Api) ? api->struct_size : sizeof(g_Api));
    g_HasApi = true;
    g_OwnerToken = context->plugin_owner_token;
    g_GameplayPolicyEventSeen = false;
    g_GameplayPolicyEventAccepted = false;
    g_ChatMessageEventSeen = false;
    g_ChatMessageEventAccepted = false;

    if (HasGameplayPolicyEventApi(api))
    {
        g_GameplayPolicyEventHandle = api->RegisterGameplayPolicyEventWithOwnerTokenHandle(
            g_OwnerToken,
            OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL,
            OnGameplayPolicyEvent,
            &g_GameplayPolicyEventUserData);
        if (g_GameplayPolicyEventHandle == 0)
        {
            UnregisterCallbacks();
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
            UnregisterCallbacks();
            ResetState();
            return false;
        }
    }

    CompileGameplayPolicyAbi();
    api->LogInfo("[c_abi_minimal] Loaded.");
    return true;
}

__attribute__((visibility("default"))) void ObeliskPlugin_Shutdown(void)
{
    UnregisterCallbacks();
    ResetState();
}

__attribute__((visibility("default"))) bool CAbiMinimal_GameplayPolicyEventSeen(void)
{
    return g_GameplayPolicyEventSeen;
}

__attribute__((visibility("default"))) bool CAbiMinimal_GameplayPolicyEventAccepted(void)
{
    return g_GameplayPolicyEventAccepted;
}

__attribute__((visibility("default"))) bool CAbiMinimal_ChatMessageEventSeen(void)
{
    return g_ChatMessageEventSeen;
}

__attribute__((visibility("default"))) bool CAbiMinimal_ChatMessageEventAccepted(void)
{
    return g_ChatMessageEventAccepted;
}
