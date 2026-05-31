#include <obelisk/ObeliskApi.h>

#include <cstddef>
#include <cstdint>
#include <cstring>

#define OBELISK_CONCAT_INNER(a, b) a##b
#define OBELISK_CONCAT(a, b) OBELISK_CONCAT_INNER(a, b)

namespace
{
    ObeliskApi g_Api{};
    bool g_HasApi = false;
    uint64_t g_OwnerToken = 0;
    uint64_t g_ProcessEventHandle = 0;
    uint64_t g_GameplayPolicyEventHandle = 0;
    uint64_t g_ChatMessageEventHandle = 0;
    uint64_t g_ScheduledHandle = 0;
    uint64_t g_GameplayPolicyEventUserData = 0x5DC0DE;
    uint64_t g_ChatMessageEventUserData = 0xC0FFEE;
    uint64_t g_ScheduledUserData = 0x710E;
    bool g_GameplayPolicyEventSeen = false;
    bool g_GameplayPolicyEventAccepted = false;
    bool g_ChatMessageEventSeen = false;
    bool g_ChatMessageEventAccepted = false;
    bool g_ScheduledSeen = false;
    bool g_ScheduledAccepted = false;
    ObeliskGameplayPolicyEvent g_GameplayPolicyEventCopy{};

    constexpr const char* kDefaultConfig = R"json({
    "enabled": false,
    "allow_all_instances": false,
    "instance_allowlist": []
})json";

    bool OnProcessEvent(void*, void*, void*)
    {
        return true;
    }

    void CopyApiPrefix(const ObeliskApi* api)
    {
        g_Api = {};
        if (!api)
            return;
        std::memcpy(&g_Api, api, api->struct_size < sizeof(g_Api) ? api->struct_size : sizeof(g_Api));
    }

    bool ValidateGameplayPolicyEventCopy(const ObeliskGameplayPolicyEvent& event, void* userData)
    {
        constexpr uint64_t kCopiedPayload = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD;
        if (userData != &g_GameplayPolicyEventUserData ||
            event.abi_version != OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION ||
            event.struct_size < sizeof(ObeliskGameplayPolicyEvent) ||
            (event.flags & kCopiedPayload) == 0)
        {
            return false;
        }

        if (event.event_kind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE)
        {
            constexpr uint64_t kRequiredFlags = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED;
            constexpr uint64_t kRequiredFields = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX |
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET;

            return event.resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE &&
                (event.flags & kRequiredFlags) == kRequiredFlags &&
                (event.flags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED) == 0 &&
                (event.field_mask & kRequiredFields) == kRequiredFields &&
                (event.bool_values & (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_FORCE_SET)) != 0 &&
                (event.bool_values & (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE)) == 0 &&
                event.int32_values[OBELISK_GAMEPLAY_POLICY_FIELD_VARIANT_INDEX] == 7;
        }

        if (event.event_kind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK)
        {
            constexpr uint64_t kRequiredFlags = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED;
            constexpr uint64_t kRequiredFields = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER;

            return event.resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM &&
                (event.flags & kRequiredFlags) == kRequiredFlags &&
                (event.flags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED) == 0 &&
                (event.field_mask & kRequiredFields) == kRequiredFields &&
                (event.bool_values & (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_REQUESTED_BY_PLAYER)) != 0 &&
                (event.bool_values & (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE)) != 0;
        }

        if (event.event_kind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK)
        {
            constexpr uint64_t kRequiredFlags = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED;
            constexpr uint64_t kRequiredFields = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN;

            return event.resource_kind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM &&
                (event.flags & kRequiredFlags) == kRequiredFlags &&
                (event.flags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED) == 0 &&
                (event.field_mask & kRequiredFields) == kRequiredFields &&
                (event.bool_values & (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_IGNORE_COOLDOWN)) == 0 &&
                (event.bool_values & (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE)) != 0;
        }

        return false;
    }

    void OnGameplayPolicyEvent(const ObeliskGameplayPolicyEvent* event, void* userData)
    {
        g_GameplayPolicyEventSeen = true;
        g_GameplayPolicyEventAccepted = false;
        g_GameplayPolicyEventCopy = {};

        if (!event ||
            event->abi_version != OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION ||
            event->struct_size < sizeof(ObeliskGameplayPolicyEvent))
        {
            return;
        }

        g_GameplayPolicyEventCopy = *event;
        g_GameplayPolicyEventAccepted = ValidateGameplayPolicyEventCopy(g_GameplayPolicyEventCopy, userData);
    }

    void OnChatMessageEvent(const ObeliskChatMessageEvent* event, void* userData)
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
            userData != &g_ChatMessageEventUserData)
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

    void HandleScheduledCallback(uint64_t timerId, void* userData)
    {
        g_ScheduledSeen = true;
        g_ScheduledAccepted = timerId == g_ScheduledHandle &&
            timerId != 0 &&
            userData == &g_ScheduledUserData;
    }

    bool HasProcessEventHandleApi(const ObeliskApi* api)
    {
        return api &&
            (api->capabilities & OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS) != 0 &&
            (api->capabilities & OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES) != 0 &&
            (api->capabilities & OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS) != 0 &&
            api->struct_size >= offsetof(ObeliskApi, UnregisterProcessEventCallbackWithOwnerToken) +
                sizeof(api->UnregisterProcessEventCallbackWithOwnerToken) &&
            api->RegisterPreProcessEventForNameIndexWithOwnerTokenHandle &&
            api->UnregisterProcessEventCallbackWithOwnerToken;
    }

    bool HasGameplayPolicyEventApi(const ObeliskApi* api)
    {
        return api &&
            (api->capabilities & OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS) != 0 &&
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
        if (!api ||
            (api->capabilities & OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS) == 0 ||
            api->struct_size < offsetof(ObeliskApi, DescribeResourceKind) +
                sizeof(api->DescribeResourceKind) ||
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

    bool ValidateResourceKindDescriptors(const ObeliskApi* api)
    {
        return ValidateResourceKindDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE,
                "structure") &&
            ValidateResourceKindDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER |
                    OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN,
                "inventory_item");
    }

    bool ValidateGameplayPolicyEventDescriptor(const ObeliskApi* api,
                                               uint32_t eventKind,
                                               uint32_t resourceKind,
                                               uint64_t flags,
                                               uint64_t eventKindMask,
                                               uint64_t fieldMask,
                                               const char* stableName)
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
        if (!api->DescribeGameplayPolicyEventKind(eventKind, &descriptor))
            return false;

        return descriptor.abi_version == OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION &&
            descriptor.struct_size == sizeof(ObeliskGameplayPolicyEventDescriptor) &&
            descriptor.event_kind == eventKind &&
            descriptor.resource_kind == resourceKind &&
            (descriptor.flags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD) != 0 &&
            (descriptor.flags & flags) == flags &&
            descriptor.event_kind_mask == eventKindMask &&
            (descriptor.field_mask & fieldMask) == fieldMask &&
            std::strcmp(descriptor.stable_name, stableName) == 0;
    }

    bool ValidateGameplayPolicyDescriptors(const ObeliskApi* api)
    {
        return ValidateResourceKindDescriptors(api) &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_VARIANT_CHANGE,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX,
                "structure.variant_change") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER,
                "inventory.remote_add_check") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN,
                "inventory.use_check") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_ALLOW_EQUIP_ITEM_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                "inventory_item.allow_equip_check") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CAN_REPAIR_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                "inventory_item.can_repair_check") &&
            ValidateGameplayPolicyEventDescriptor(
                api,
                OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK,
                OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
                OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK,
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE,
                "inventory_item.use_onto_item_check");
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

    bool HasScheduledApi(const ObeliskApi* api)
    {
        return api &&
            (api->capabilities & OBELISK_API_CAPABILITY_TIMERS) != 0 &&
            api->struct_size >= offsetof(ObeliskApi, OBELISK_CONCAT(Unregister, TimerWithOwnerToken)) +
                sizeof(api->OBELISK_CONCAT(Unregister, TimerWithOwnerToken)) &&
            api->OBELISK_CONCAT(Register, TimerWithOwnerTokenHandle) &&
            api->OBELISK_CONCAT(Unregister, TimerWithOwnerToken);
    }

    void UnregisterCallbacks()
    {
        if (g_HasApi && g_ScheduledHandle != 0 && g_Api.OBELISK_CONCAT(Unregister, TimerWithOwnerToken))
        {
            try
            {
                g_Api.OBELISK_CONCAT(Unregister, TimerWithOwnerToken)(g_OwnerToken, g_ScheduledHandle);
                g_ScheduledHandle = 0;
            }
            catch (...)
            {
            }
        }

        if (g_HasApi && g_ChatMessageEventHandle != 0 && g_Api.UnregisterChatMessageEventWithOwnerToken)
        {
            try
            {
                g_Api.UnregisterChatMessageEventWithOwnerToken(g_OwnerToken, g_ChatMessageEventHandle);
                g_ChatMessageEventHandle = 0;
            }
            catch (...)
            {
            }
        }

        if (g_HasApi && g_GameplayPolicyEventHandle != 0 && g_Api.UnregisterGameplayPolicyEventWithOwnerToken)
        {
            try
            {
                g_Api.UnregisterGameplayPolicyEventWithOwnerToken(g_OwnerToken, g_GameplayPolicyEventHandle);
                g_GameplayPolicyEventHandle = 0;
            }
            catch (...)
            {
            }
        }

        if (g_HasApi && g_ProcessEventHandle != 0 && g_Api.UnregisterProcessEventCallbackWithOwnerToken)
        {
            try
            {
                g_Api.UnregisterProcessEventCallbackWithOwnerToken(g_OwnerToken, g_ProcessEventHandle);
                g_ProcessEventHandle = 0;
            }
            catch (...)
            {
            }
        }
    }

    void ResetState()
    {
        g_Api = {};
        g_HasApi = false;
        g_OwnerToken = 0;
        g_ProcessEventHandle = 0;
        g_GameplayPolicyEventHandle = 0;
        g_ChatMessageEventHandle = 0;
        g_ScheduledHandle = 0;
        g_GameplayPolicyEventSeen = false;
        g_GameplayPolicyEventAccepted = false;
        g_ChatMessageEventSeen = false;
        g_ChatMessageEventAccepted = false;
        g_ScheduledSeen = false;
        g_ScheduledAccepted = false;
        g_GameplayPolicyEventCopy = {};
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
        out->plugin_id = "sdk_consumer_minimal";
        out->name = "SDK Consumer Minimal";
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

        if (api->abi_version != OBELISK_API_ABI_VERSION ||
            api->struct_size < offsetof(ObeliskApi, capabilities) + sizeof(api->capabilities) ||
            context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
            context->struct_size < sizeof(ObeliskPluginInitContext) ||
            context->plugin_owner_token == 0)
        {
            return false;
        }

        CopyApiPrefix(api);
        g_HasApi = true;
        g_OwnerToken = context->plugin_owner_token;

        if (g_Api.LogInfo)
            g_Api.LogInfo("[sdk_consumer_minimal] Loaded.");

        if (!ValidateGameplayPolicyDescriptors(&g_Api))
        {
            ResetState();
            return false;
        }

        if (HasProcessEventHandleApi(&g_Api))
        {
            g_ProcessEventHandle = g_Api.RegisterPreProcessEventForNameIndexWithOwnerTokenHandle(
                g_OwnerToken,
                42,
                OnProcessEvent);
            if (g_ProcessEventHandle == 0)
            {
                ResetState();
                return false;
            }
        }

        if (HasGameplayPolicyEventApi(&g_Api))
        {
            g_GameplayPolicyEventHandle = g_Api.RegisterGameplayPolicyEventWithOwnerTokenHandle(
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

        if (HasChatMessageEventApi(&g_Api))
        {
            g_ChatMessageEventHandle = g_Api.RegisterChatMessageEventWithOwnerTokenHandle(
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

        if (HasScheduledApi(&g_Api))
        {
            g_ScheduledHandle = g_Api.OBELISK_CONCAT(Register, TimerWithOwnerTokenHandle)(
                g_OwnerToken,
                1000,
                0,
                0,
                HandleScheduledCallback,
                &g_ScheduledUserData);
            if (g_ScheduledHandle == 0)
            {
                UnregisterCallbacks();
                ResetState();
                return false;
            }
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

        if (g_HasApi && g_Api.LogInfo)
            g_Api.LogInfo("[sdk_consumer_minimal] Shutdown.");
    }
    catch (...)
    {
    }
    ResetState();
}

extern "C" __attribute__((visibility("default"))) bool SdkConsumerMinimal_GameplayPolicyEventSeen()
{
    return g_GameplayPolicyEventSeen;
}

extern "C" __attribute__((visibility("default"))) bool SdkConsumerMinimal_GameplayPolicyEventAccepted()
{
    return g_GameplayPolicyEventAccepted;
}

extern "C" __attribute__((visibility("default"))) bool SdkConsumerMinimal_ChatMessageEventSeen()
{
    return g_ChatMessageEventSeen;
}

extern "C" __attribute__((visibility("default"))) bool SdkConsumerMinimal_ChatMessageEventAccepted()
{
    return g_ChatMessageEventAccepted;
}

extern "C" __attribute__((visibility("default"))) bool SdkConsumerMinimal_ScheduledCallbackSeen()
{
    return g_ScheduledSeen;
}

extern "C" __attribute__((visibility("default"))) bool SdkConsumerMinimal_ScheduledCallbackAccepted()
{
    return g_ScheduledAccepted;
}
