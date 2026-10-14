#include <obelisk/ObeliskApi.h>

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <sys/stat.h>

#define OBELISK_CONCAT_INNER(a, b) a##b
#define OBELISK_CONCAT(a, b) OBELISK_CONCAT_INNER(a, b)

#ifndef OBELISK_CMAKE_CHAT_MESSAGE_EVENT_ABI_VERSION
#error "Installed Obelisk CMake ABI variables were not passed to the consumer build"
#endif

static_assert(OBELISK_API_ABI_VERSION == 1u, "unexpected Obelisk API ABI version");
static_assert(OBELISK_PLUGIN_METADATA_ABI_VERSION == 1u, "unexpected plugin metadata ABI version");
static_assert(OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION == 1u, "unexpected plugin init context ABI version");
static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION == 1u, "unexpected gameplay policy event ABI version");
static_assert(OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION == 1u, "unexpected resource kind descriptor ABI version");
static_assert(
    OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION == 1u,
    "unexpected gameplay policy event descriptor ABI version");
static_assert(OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION == 1u, "unexpected chat message event ABI version");
static_assert(
    OBELISK_CMAKE_API_ABI_VERSION == OBELISK_API_ABI_VERSION,
    "Obelisk CMake API ABI version does not match the public header");
static_assert(
    OBELISK_CMAKE_PLUGIN_METADATA_ABI_VERSION == OBELISK_PLUGIN_METADATA_ABI_VERSION,
    "Obelisk CMake plugin metadata ABI version does not match the public header");
static_assert(
    OBELISK_CMAKE_PLUGIN_INIT_CONTEXT_ABI_VERSION == OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION,
    "Obelisk CMake plugin init context ABI version does not match the public header");
static_assert(
    OBELISK_CMAKE_GAMEPLAY_POLICY_EVENT_ABI_VERSION == OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION,
    "Obelisk CMake gameplay policy event ABI version does not match the public header");
static_assert(
    OBELISK_CMAKE_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION == OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION,
    "Obelisk CMake resource kind descriptor ABI version does not match the public header");
static_assert(
    OBELISK_CMAKE_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION ==
        OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION,
    "Obelisk CMake gameplay policy event descriptor ABI version does not match the public header");
static_assert(
    OBELISK_CMAKE_CHAT_MESSAGE_EVENT_ABI_VERSION == OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION,
    "Obelisk CMake chat message event ABI version does not match the public header");

namespace
{
    ObeliskApi g_Api{};
    bool g_HasApi = false;
    uint64_t g_OwnerToken = 0;
    uint64_t g_GameplayPolicyEventHandle = 0;
    uint64_t g_ChatMessageEventHandle = 0;
    uint64_t g_ScheduledHandle = 0;
    uint64_t g_GameplayPolicyEventUserData = 0x5DC0DE02;
    uint64_t g_ChatMessageEventUserData = 0xC0FFEE02;
    uint64_t g_ScheduledUserData = 0x71A1E02;
    uint64_t g_GameplayPolicyEventSeenMask = 0;
    uint64_t g_GameplayPolicyEventAcceptedMask = 0;
    uint64_t g_ChatMessageEventSeenModes = 0;
    bool g_ScheduledSeen = false;

    constexpr const char* kDefaultConfig = R"json({
    "enabled": false,
    "allow_all_instances": false,
    "instance_allowlist": []
})json";

    uint64_t EventMask(uint32_t eventKind)
    {
        switch (eventKind)
        {
        case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACCESS_CHECK:
            return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK;
        case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_DEMOLISH_CHECK:
            return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_DEMOLISH_CHECK;
        case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE:
            return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_VARIANT_CHANGE;
        case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACTIVATION_TOGGLE:
            return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACTIVATION_TOGGLE;
        case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_PIN_CODE_CHECK:
            return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_PIN_CODE_CHECK;
        case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_SEAT_CHECK:
            return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_SEAT_CHECK;
        case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK:
            return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK;
        case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK:
            return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK;
        case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK:
            return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_ALLOW_EQUIP_ITEM_CHECK;
        case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK:
            return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CAN_REPAIR_CHECK;
        case OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK:
            return OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK;
        default:
            return 0;
        }
    }

    uint64_t ChatModeMask(uint32_t sendMode)
    {
        switch (sendMode)
        {
        case OBELISK_CHAT_SEND_MODE_GLOBAL:
        case OBELISK_CHAT_SEND_MODE_TRIBE:
        case OBELISK_CHAT_SEND_MODE_LOCAL:
        case OBELISK_CHAT_SEND_MODE_ALLIANCE:
            return 1ull << sendMode;
        default:
            return 0;
        }
    }

    bool PathExists(const char* path)
    {
        struct stat st {};
        return path && stat(path, &st) == 0;
    }

    bool HasApiMetadataPrefix(const ObeliskApi* api)
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

    void CopyApiPrefix(const ObeliskApi* api)
    {
        g_Api = {};
        if (!api)
            return;
        std::memcpy(&g_Api, api, api->struct_size < sizeof(g_Api) ? api->struct_size : sizeof(g_Api));
    }

    void OnGameplayPolicyEvent(const ObeliskGameplayPolicyEvent* event, void* userData)
    {
        if (!event ||
            event->abi_version != OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION ||
            event->struct_size < sizeof(ObeliskGameplayPolicyEvent) ||
            userData != &g_GameplayPolicyEventUserData ||
            (event->flags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD) == 0)
        {
            return;
        }

        const uint64_t eventMask = EventMask(event->event_kind);
        g_GameplayPolicyEventSeenMask |= eventMask;
        bool accepted = false;
        if (event->resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE)
        {
            constexpr uint64_t kRequiredFlags = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED;
            accepted =
                (event->flags & kRequiredFlags) == kRequiredFlags &&
                (event->flags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED) == 0 &&
                (event->field_mask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE) != 0;
            if (event->event_kind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE)
            {
                accepted = accepted &&
                    (event->field_mask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX) != 0 &&
                    (event->field_mask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET) != 0 &&
                    event->int32_values[OBELISK_GAMEPLAY_POLICY_FIELD_VARIANT_INDEX] == 7 &&
                    (event->bool_values & (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_FORCE_SET)) != 0;
            }
            if (event->event_kind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_SEAT_CHECK)
            {
                accepted = accepted &&
                    (event->field_mask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE) != 0 &&
                    (event->bool_values & (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_FORCE)) != 0;
            }
        }
        else if (event->resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM)
        {
            constexpr uint64_t kRequiredFlags = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED;
            accepted =
                (event->flags & kRequiredFlags) == kRequiredFlags &&
                (event->flags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED) == 0 &&
                (event->field_mask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE) != 0;
            if (event->event_kind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK)
            {
                accepted = accepted &&
                    (event->field_mask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER) != 0 &&
                    (event->bool_values & (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE)) != 0 &&
                    (event->bool_values & (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_REQUESTED_BY_PLAYER)) != 0;
            }
            if (event->event_kind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK)
            {
                accepted = accepted &&
                    (event->field_mask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN) != 0 &&
                    (event->bool_values & (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE)) != 0 &&
                    (event->bool_values & (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_IGNORE_COOLDOWN)) == 0;
            }
        }

        if (accepted)
            g_GameplayPolicyEventAcceptedMask |= eventMask;
    }

    void OnChatMessageEvent(const ObeliskChatMessageEvent* event, void* userData)
    {
        if (event &&
            event->abi_version == OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION &&
            event->struct_size >= sizeof(ObeliskChatMessageEvent) &&
            ChatModeMask(event->send_mode) != 0 &&
            (event->flags & OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD) != 0 &&
            event->sequence != 0 &&
            event->message.data &&
            event->message.size == 5 &&
            userData == &g_ChatMessageEventUserData &&
            std::memcmp(event->message.data, "!ping", 5) == 0)
        {
            g_ChatMessageEventSeenModes |= ChatModeMask(event->send_mode);
        }
    }

    void HandleScheduledCallback(uint64_t timerId, void* userData)
    {
        if (timerId == g_ScheduledHandle && timerId != 0 && userData == &g_ScheduledUserData)
            g_ScheduledSeen = true;
    }

    bool HasGameplayPolicyEventApi(const ObeliskApi* api)
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

    bool ValidateResourceKindDescriptor(const ObeliskApi* api,
                                        uint32_t resourceKind,
                                        uint64_t eventMask,
                                        uint64_t fieldMask,
                                        const char* stableName)
    {
        if (!HasApiMetadataPrefix(api) ||
            (api->capabilities & OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS) == 0 ||
            api->struct_size < offsetof(ObeliskApi, DescribeResourceKind) + sizeof(api->DescribeResourceKind) ||
            !api->DescribeResourceKind)
        {
            return true;
        }

        ObeliskResourceKindDescriptor descriptor{};
        descriptor.struct_size = sizeof(ObeliskResourceKindDescriptor);
        if (!api->DescribeResourceKind(resourceKind, &descriptor))
            return false;

        constexpr uint64_t kRequiredFlags = OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY |
            OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY |
            OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP;
        return descriptor.abi_version == OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION &&
            descriptor.struct_size == sizeof(ObeliskResourceKindDescriptor) &&
            descriptor.resource_kind == resourceKind &&
            (descriptor.flags & kRequiredFlags) == kRequiredFlags &&
            descriptor.supported_gameplay_policy_event_mask == eventMask &&
            descriptor.supported_gameplay_policy_field_mask == fieldMask &&
            std::strcmp(descriptor.stable_name, stableName) == 0;
    }

    bool ValidateGameplayPolicyEventDescriptor(const ObeliskApi* api,
                                               uint32_t eventKind,
                                               uint32_t resourceKind,
                                               uint64_t eventKindMask,
                                               uint64_t fieldMask,
                                               uint64_t requiredFlag,
                                               const char* stableName)
    {
        if (!HasApiMetadataPrefix(api) ||
            (api->capabilities & OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS) == 0 ||
            api->struct_size < offsetof(ObeliskApi, DescribeGameplayPolicyEventKind) +
                sizeof(api->DescribeGameplayPolicyEventKind) ||
            !api->DescribeGameplayPolicyEventKind)
        {
            return true;
        }

        ObeliskGameplayPolicyEventDescriptor descriptor{};
        descriptor.struct_size = sizeof(ObeliskGameplayPolicyEventDescriptor);
        if (!api->DescribeGameplayPolicyEventKind(eventKind, &descriptor))
            return false;

        return descriptor.abi_version == OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION &&
            descriptor.struct_size == sizeof(ObeliskGameplayPolicyEventDescriptor) &&
            descriptor.event_kind == eventKind &&
            descriptor.resource_kind == resourceKind &&
            (descriptor.flags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD) != 0 &&
            (descriptor.flags & requiredFlag) != 0 &&
            descriptor.event_kind_mask == eventKindMask &&
            (descriptor.field_mask & fieldMask) == fieldMask &&
            std::strcmp(descriptor.stable_name, stableName) == 0;
    }

    bool HasChatMessageEventApi(const ObeliskApi* api)
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

    bool HasScheduledApi(const ObeliskApi* api)
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

    void ResetState()
    {
        g_Api = {};
        g_HasApi = false;
        g_OwnerToken = 0;
        g_GameplayPolicyEventHandle = 0;
        g_ChatMessageEventHandle = 0;
        g_ScheduledHandle = 0;
        g_GameplayPolicyEventSeenMask = 0;
        g_GameplayPolicyEventAcceptedMask = 0;
        g_ChatMessageEventSeenModes = 0;
        g_ScheduledSeen = false;
    }

    void UnregisterCallbacks()
    {
        if (g_HasApi && g_ScheduledHandle != 0 && g_Api.OBELISK_CONCAT(Unregister, TimerWithOwnerToken))
        {
            g_Api.OBELISK_CONCAT(Unregister, TimerWithOwnerToken)(g_OwnerToken, g_ScheduledHandle);
            g_ScheduledHandle = 0;
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

        if (!HasApiMetadataPrefix(api) ||
            context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
            context->struct_size < sizeof(ObeliskPluginInitContext))
        {
            return false;
        }

        CopyApiPrefix(api);
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

        if (HasScheduledApi(api))
        {
            g_ScheduledHandle = api->OBELISK_CONCAT(Register, TimerWithOwnerTokenHandle)(
                g_OwnerToken,
                1000,
                1000,
                OBELISK_TIMER_FLAG_REPEATING,
                HandleScheduledCallback,
                &g_ScheduledUserData);
            if (g_ScheduledHandle == 0)
            {
                UnregisterCallbacks();
                ResetState();
                return false;
            }
        }

        if (!ValidateResourceKindDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE,
                "structure"))
        {
            UnregisterCallbacks();
            ResetState();
            return false;
        }
        if (!ValidateResourceKindDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN,
                "inventory_item"))
        {
            UnregisterCallbacks();
            ResetState();
            return false;
        }

        const bool descriptorOk =
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACCESS_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
                "structure.access_check") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_DEMOLISH_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_DEMOLISH_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
                "structure.demolish_check") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_VARIANT_CHANGE,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
                "structure.variant_change") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACTIVATION_TOGGLE,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACTIVATION_TOGGLE,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
                "structure.activation_toggle") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_PIN_CODE_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_PIN_CODE_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
                "structure.pin_code_check") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_SEAT_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_SEAT_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
                "structure.seat_check") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                "inventory.remote_add_check") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                "inventory.use_check") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_ALLOW_EQUIP_ITEM_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                "inventory_item.allow_equip_check") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CAN_REPAIR_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                "inventory_item.can_repair_check") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                "inventory_item.use_onto_item_check");
        if (!descriptorOk)
        {
            UnregisterCallbacks();
            ResetState();
            return false;
        }

        return true;
    }
    catch (...)
    {
        UnregisterCallbacks();
        ResetState();
        return false;
    }
}

extern "C" __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown()
{
    try
    {
        UnregisterCallbacks();
    }
    catch (...)
    {
    }
    ResetState();
}

extern "C" __attribute__((visibility("default"))) bool InstallLayoutConsumer_ChatMessageEventSeen()
{
    constexpr uint64_t kAllChatModes =
        (1ull << OBELISK_CHAT_SEND_MODE_GLOBAL) |
        (1ull << OBELISK_CHAT_SEND_MODE_TRIBE) |
        (1ull << OBELISK_CHAT_SEND_MODE_LOCAL) |
        (1ull << OBELISK_CHAT_SEND_MODE_ALLIANCE);
    return (g_ChatMessageEventSeenModes & kAllChatModes) == kAllChatModes;
}

extern "C" __attribute__((visibility("default"))) bool InstallLayoutConsumer_GameplayPolicyEventSeen()
{
    return (g_GameplayPolicyEventSeenMask & OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL) ==
        OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL;
}

extern "C" __attribute__((visibility("default"))) bool InstallLayoutConsumer_GameplayPolicyEventAccepted()
{
    return (g_GameplayPolicyEventAcceptedMask & OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL) ==
        OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL;
}

extern "C" __attribute__((visibility("default"))) bool InstallLayoutConsumer_ScheduledCallbackSeen()
{
    return g_ScheduledSeen;
}
