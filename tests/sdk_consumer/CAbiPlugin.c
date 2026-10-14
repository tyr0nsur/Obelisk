#include <obelisk/ObeliskApi.h>

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define OBELISK_CONCAT_INNER(a, b) a##b
#define OBELISK_CONCAT(a, b) OBELISK_CONCAT_INNER(a, b)

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
static uint64_t g_TimerHandle = 0;
static uint64_t g_TimerUserData = 0xC0FFEE05;
static bool g_TimerSeen = false;
static bool g_TimerAccepted = false;
static char g_ConfigDir[256];
static char g_ConfigPath[256];
static char g_InstanceId[64];

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
        else if (event->event_kind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK ||
                 event->event_kind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK ||
                 event->event_kind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK)
        {
            g_GameplayPolicyEventAccepted =
                event->resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM &&
                (event->flags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED) != 0 &&
                event->field_mask == OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE;
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

static void HandleScheduledCallback(uint64_t timer_id, void* user_data)
{
    g_TimerSeen = true;
    g_TimerAccepted = timer_id == g_TimerHandle &&
        timer_id != 0 &&
        user_data == &g_TimerUserData;
}

static void CompileScheduledCallback(uint64_t timer_id, void* user_data)
{
    volatile uint64_t id = timer_id;
    volatile bool has_user_data = user_data != NULL;
    (void)id;
    (void)has_user_data;
}

static void CompileGameplayPolicyAbi(void)
{
    volatile uint64_t owner_token_callback_capability = OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS;
    volatile uint64_t capability = OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS;
    volatile uint64_t resource_descriptor_capability = OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS;
    volatile uint64_t event_descriptor_capability =
        OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS;
    volatile uint64_t chat_capability = OBELISK_API_CAPABILITY_CHAT_EVENTS;
    volatile uint64_t timer_capability = OBELISK_API_CAPABILITY_TIMERS;
    volatile uint64_t timer_repeating = OBELISK_TIMER_FLAG_REPEATING;
    volatile uint64_t all_events = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL;
    volatile uint64_t all_structures = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES;
    volatile uint64_t all_inventory = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY;
    volatile uint64_t allow_equip_item = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_ALLOW_EQUIP_ITEM_CHECK;
    volatile uint64_t can_repair = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CAN_REPAIR_CHECK;
    volatile uint64_t use_item_onto_item = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK;
    volatile uint64_t copied_payload = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD;
    volatile uint64_t inventory_backed = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED;
    volatile uint64_t return_value = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE;
    volatile uint64_t requested_by_player = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER;
    volatile uint64_t ignore_cooldown = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN;
    volatile uint64_t category_only = OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY;
    volatile uint64_t no_identity = OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY;
    volatile uint64_t no_lookup = OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP;
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
    ObeliskGameplayPolicyEvent item_return_event = {
        OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION,
        sizeof(ObeliskGameplayPolicyEvent),
        OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK,
        OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
        OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
            OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
        OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
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
    void (*scheduled_callback)(uint64_t, void*) = CompileScheduledCallback;
    callback(&event, NULL);
    callback(&inventory_remote_add_event, NULL);
    callback(&inventory_use_event, NULL);
    callback(&item_return_event, NULL);
    chat_callback(&chat_event, NULL);
    scheduled_callback(1, NULL);
    (void)owner_token_callback_capability;
    (void)capability;
    (void)resource_descriptor_capability;
    (void)event_descriptor_capability;
    (void)chat_capability;
    (void)timer_capability;
    (void)timer_repeating;
    (void)all_events;
    (void)all_structures;
    (void)all_inventory;
    (void)allow_equip_item;
    (void)can_repair;
    (void)use_item_onto_item;
    (void)copied_payload;
    (void)inventory_backed;
    (void)return_value;
    (void)requested_by_player;
    (void)ignore_cooldown;
    (void)category_only;
    (void)no_identity;
    (void)no_lookup;
    (void)event_descriptor_abi;
    (void)chat_copied_payload;
    (void)chat_message_view;
    (void)descriptor;
    (void)event_descriptor;
}

static bool CopyInitString(char* destination, size_t destination_size, const char* value)
{
    if (!destination || destination_size == 0 || !value || strlen(value) >= destination_size)
        return false;

    strncpy(destination, value, destination_size - 1);
    destination[destination_size - 1] = '\0';
    return true;
}

static bool CopiedInitPointersIntact(void)
{
    return strncmp(g_ConfigDir, "/tmp/obelisk-sdk-consumer.", 26) == 0 &&
        strstr(g_ConfigPath, "/config.json") != NULL &&
        strcmp(g_InstanceId, "sdk-consumer-test") == 0;
}

static bool HasApiMetadataPrefix(const ObeliskApi* api)
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

static bool HasTimerApi(const ObeliskApi* api)
{
    return HasApiMetadataPrefix(api) &&
        (api->capabilities & OBELISK_API_CAPABILITY_TIMERS) != 0 &&
        api->struct_size >= offsetof(ObeliskApi, OBELISK_CONCAT(Register, TimerWithOwnerTokenHandle)) +
            sizeof(api->OBELISK_CONCAT(Register, TimerWithOwnerTokenHandle)) &&
        api->struct_size >= offsetof(ObeliskApi, OBELISK_CONCAT(Unregister, TimerWithOwnerToken)) +
            sizeof(api->OBELISK_CONCAT(Unregister, TimerWithOwnerToken)) &&
        api->OBELISK_CONCAT(Register, TimerWithOwnerTokenHandle) &&
        api->OBELISK_CONCAT(Unregister, TimerWithOwnerToken);
}

static bool HasChatMessageEventApi(const ObeliskApi* api)
{
    return HasApiMetadataPrefix(api) &&
        (api->capabilities & OBELISK_API_CAPABILITY_CHAT_EVENTS) != 0 &&
        api->struct_size >= offsetof(ObeliskApi, RegisterChatMessageEventWithOwnerTokenHandle) +
            sizeof(api->RegisterChatMessageEventWithOwnerTokenHandle) &&
        api->struct_size >= offsetof(ObeliskApi, UnregisterChatMessageEventWithOwnerToken) +
            sizeof(api->UnregisterChatMessageEventWithOwnerToken) &&
        api->RegisterChatMessageEventWithOwnerTokenHandle &&
        api->UnregisterChatMessageEventWithOwnerToken;
}

static bool HasGameplayPolicyEventApi(const ObeliskApi* api)
{
    return HasApiMetadataPrefix(api) &&
        (api->capabilities & OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS) != 0 &&
        api->struct_size >= offsetof(ObeliskApi, RegisterGameplayPolicyEventWithOwnerTokenHandle) +
            sizeof(api->RegisterGameplayPolicyEventWithOwnerTokenHandle) &&
        api->struct_size >= offsetof(ObeliskApi, UnregisterGameplayPolicyEventWithOwnerToken) +
            sizeof(api->UnregisterGameplayPolicyEventWithOwnerToken) &&
        api->RegisterGameplayPolicyEventWithOwnerTokenHandle &&
        api->UnregisterGameplayPolicyEventWithOwnerToken;
}

static bool PostInitCallProcessEventSkipped(void)
{
    if (!g_HasApi ||
        g_Api.struct_size < offsetof(ObeliskApi, capabilities) + sizeof(g_Api.capabilities) ||
        (g_Api.capabilities & OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT) == 0 ||
        !g_Api.CallProcessEvent)
    {
        return false;
    }

    return true;
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

    if (!HasApiMetadataPrefix(api) ||
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
        descriptor.struct_size == sizeof(ObeliskResourceKindDescriptor) &&
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

static bool ValidateGameplayPolicyEventDescriptor(const ObeliskApi* api,
                                                  uint32_t event_kind,
                                                  uint32_t resource_kind,
                                                  uint64_t expected_flags,
                                                  uint64_t event_kind_mask,
                                                  uint64_t field_mask,
                                                  const char* stable_name)
{
    ObeliskGameplayPolicyEventDescriptor descriptor;

    if (!HasApiMetadataPrefix(api) ||
        (api->capabilities & OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS) == 0 ||
        api->struct_size < offsetof(ObeliskApi, DescribeGameplayPolicyEventKind) +
            sizeof(api->DescribeGameplayPolicyEventKind) ||
        !api->DescribeGameplayPolicyEventKind)
    {
        return true;
    }

    memset(&descriptor, 0, sizeof(descriptor));
    descriptor.struct_size = sizeof(ObeliskGameplayPolicyEventDescriptor);
    if (!api->DescribeGameplayPolicyEventKind(event_kind, &descriptor))
        return false;

    return descriptor.abi_version == OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION &&
        descriptor.struct_size == sizeof(ObeliskGameplayPolicyEventDescriptor) &&
        descriptor.event_kind == event_kind &&
        descriptor.resource_kind == resource_kind &&
        (descriptor.flags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD) != 0 &&
        (descriptor.flags & expected_flags) == expected_flags &&
        descriptor.event_kind_mask == event_kind_mask &&
        (descriptor.field_mask & field_mask) == field_mask &&
        strcmp(descriptor.stable_name, stable_name) == 0;
}

static bool ValidateGameplayPolicyDescriptors(const ObeliskApi* api)
{
    if (!ValidateResourceKindDescriptors(api))
        return false;

    if (!ValidateGameplayPolicyEventDescriptor(
            api,
            OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE,
            OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
            OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
            OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_VARIANT_CHANGE,
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX,
            "structure.variant_change"))
        return false;

    if (!ValidateGameplayPolicyEventDescriptor(
            api,
            OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK,
            OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
            OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
            OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK,
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER,
            "inventory.remote_add_check"))
        return false;

    if (!ValidateGameplayPolicyEventDescriptor(
            api,
            OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK,
            OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
            OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
            OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK,
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN,
            "inventory.use_check"))
        return false;

    if (!ValidateGameplayPolicyEventDescriptor(
            api,
            OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK,
            OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
            OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
            OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_ALLOW_EQUIP_ITEM_CHECK,
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
            "inventory_item.allow_equip_check"))
        return false;

    if (!ValidateGameplayPolicyEventDescriptor(
            api,
            OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK,
            OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
            OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
            OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CAN_REPAIR_CHECK,
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
            "inventory_item.can_repair_check"))
        return false;

    if (!ValidateGameplayPolicyEventDescriptor(
            api,
            OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK,
            OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
            OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
            OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK,
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
            "inventory_item.use_onto_item_check"))
        return false;

    return true;
}

static void UnregisterCallbacks(void)
{
    if (g_HasApi && g_TimerHandle != 0 && g_Api.OBELISK_CONCAT(Unregister, TimerWithOwnerToken))
    {
        g_Api.OBELISK_CONCAT(Unregister, TimerWithOwnerToken)(g_OwnerToken, g_TimerHandle);
        g_TimerHandle = 0;
    }
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
    g_TimerHandle = 0;
    g_TimerSeen = false;
    g_TimerAccepted = false;
    g_ConfigDir[0] = '\0';
    g_ConfigPath[0] = '\0';
    g_InstanceId[0] = '\0';
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

    if (!HasApiMetadataPrefix(api) ||
        context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
        context->struct_size < sizeof(ObeliskPluginInitContext))
    {
        return false;
    }

    if (!api->LogInfo || !context->config_dir || !context->config_path || !context->instance_id)
        return false;

    if (context->plugin_owner_token == 0)
        return false;

    if (!ValidateGameplayPolicyDescriptors(api))
        return false;

    memset(&g_Api, 0, sizeof(g_Api));
    memcpy(&g_Api, api, api->struct_size < sizeof(g_Api) ? api->struct_size : sizeof(g_Api));
    g_HasApi = true;
    g_OwnerToken = context->plugin_owner_token;
    g_GameplayPolicyEventSeen = false;
    g_GameplayPolicyEventAccepted = false;
    g_ChatMessageEventSeen = false;
    g_ChatMessageEventAccepted = false;
    g_TimerSeen = false;
    g_TimerAccepted = false;
    if (!CopyInitString(g_ConfigDir, sizeof(g_ConfigDir), context->config_dir) ||
        !CopyInitString(g_ConfigPath, sizeof(g_ConfigPath), context->config_path) ||
        !CopyInitString(g_InstanceId, sizeof(g_InstanceId), context->instance_id))
    {
        ResetState();
        return false;
    }

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

    if (HasTimerApi(api))
    {
        g_TimerHandle = api->OBELISK_CONCAT(Register, TimerWithOwnerTokenHandle)(
            g_OwnerToken,
            1000,
            0,
            0,
            HandleScheduledCallback,
            &g_TimerUserData);
        if (g_TimerHandle == 0)
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

__attribute__((visibility("default"))) bool CAbiMinimal_TimerSeen(void)
{
    return g_TimerSeen;
}

__attribute__((visibility("default"))) bool CAbiMinimal_TimerAccepted(void)
{
    return g_TimerAccepted;
}

__attribute__((visibility("default"))) bool CAbiMinimal_CopiedInitPointersIntact(void)
{
    return CopiedInitPointersIntact();
}

__attribute__((visibility("default"))) bool CAbiMinimal_PostInitCallProcessEventSkipped(void)
{
    return PostInitCallProcessEventSkipped();
}
