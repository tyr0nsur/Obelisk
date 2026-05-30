#include <obelisk/ObeliskApi.h>

#include <dlfcn.h>

#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>

#define OBELISK_CONCAT_INNER(a, b) a##b
#define OBELISK_CONCAT(a, b) OBELISK_CONCAT_INNER(a, b)

namespace
{
    using GetInfoFn = bool (*)(ObeliskPluginMetadata*);
    using InitFn = bool (*)(ObeliskApi*, const ObeliskPluginInitContext*);
    using ShutdownFn = void (*)();
    using BoolProbeFn = bool (*)();
    using ScheduledCallbackFn = void (*)(uint64_t, void*);

    int g_RegisterCount = 0;
    int g_UnregisterCount = 0;
    int g_GameplayPolicyRegisterCount = 0;
    int g_GameplayPolicyUnregisterCount = 0;
    int g_ChatMessageRegisterCount = 0;
    int g_ChatMessageUnregisterCount = 0;
    int g_TimerRegisterCount = 0;
    int g_TimerUnregisterCount = 0;
    ObeliskGameplayPolicyEventCallback g_GameplayPolicyCallback = nullptr;
    void* g_GameplayPolicyUserData = nullptr;
    ObeliskChatMessageEventCallback g_ChatMessageCallback = nullptr;
    void* g_ChatMessageUserData = nullptr;
    ScheduledCallbackFn g_TimerCallback = nullptr;
    void* g_TimerUserData = nullptr;

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    void NoOpLog(const char*)
    {
    }

    void RegisterProcessEvent(OnProcessEventCallback)
    {
    }

    void RegisterNamedProcessEvent(int32_t, OnProcessEventCallback)
    {
    }

    void CallProcessEvent(void*, void*, void*)
    {
    }

    uint64_t RegisterNamedProcessEventWithOwnerTokenHandle(uint64_t ownerToken,
                                                           int32_t nameIndex,
                                                           OnProcessEventCallback callback)
    {
        Require(ownerToken == 0xC0FFEE, "unexpected owner token in callback registration");
        Require(nameIndex == 42, "unexpected callback FName index");
        Require(callback != nullptr, "callback registration received null callback");
        ++g_RegisterCount;
        return 1001;
    }

    bool UnregisterProcessEventCallbackWithOwnerToken(uint64_t ownerToken, uint64_t registrationId)
    {
        Require(ownerToken == 0xC0FFEE, "unexpected owner token in callback unregister");
        Require(registrationId == 1001, "unexpected callback registration id");
        ++g_UnregisterCount;
        return true;
    }

    uint64_t RegisterGameplayPolicyEventWithOwnerTokenHandle(uint64_t ownerToken,
                                                             uint64_t eventKindMask,
                                                             ObeliskGameplayPolicyEventCallback callback,
                                                             void* userData)
    {
        Require(ownerToken == 0xC0FFEE, "unexpected owner token in gameplay policy registration");
        Require(eventKindMask == OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL,
                "unexpected gameplay policy event mask");
        Require(callback != nullptr, "gameplay policy registration received null callback");
        Require(userData != nullptr, "gameplay policy registration received null user data");
        ++g_GameplayPolicyRegisterCount;
        g_GameplayPolicyCallback = callback;
        g_GameplayPolicyUserData = userData;
        return 2002;
    }

    bool UnregisterGameplayPolicyEventWithOwnerToken(uint64_t ownerToken, uint64_t registrationId)
    {
        Require(ownerToken == 0xC0FFEE, "unexpected owner token in gameplay policy unregister");
        Require(registrationId == 2002, "unexpected gameplay policy registration id");
        ++g_GameplayPolicyUnregisterCount;
        g_GameplayPolicyCallback = nullptr;
        g_GameplayPolicyUserData = nullptr;
        return true;
    }

    uint64_t RegisterChatMessageEventWithOwnerTokenHandle(uint64_t ownerToken,
                                                          ObeliskChatMessageEventCallback callback,
                                                          void* userData)
    {
        Require(ownerToken == 0xC0FFEE, "unexpected owner token in chat message registration");
        Require(callback != nullptr, "chat message registration received null callback");
        Require(userData != nullptr, "chat message registration received null user data");
        ++g_ChatMessageRegisterCount;
        g_ChatMessageCallback = callback;
        g_ChatMessageUserData = userData;
        return 3003;
    }

    bool UnregisterChatMessageEventWithOwnerToken(uint64_t ownerToken, uint64_t registrationId)
    {
        Require(ownerToken == 0xC0FFEE, "unexpected owner token in chat message unregister");
        Require(registrationId == 3003, "unexpected chat message registration id");
        ++g_ChatMessageUnregisterCount;
        g_ChatMessageCallback = nullptr;
        g_ChatMessageUserData = nullptr;
        return true;
    }

    uint64_t RegisterTimerWithOwnerTokenHandle(uint64_t ownerToken,
                                               uint64_t delayMs,
                                               uint64_t intervalMs,
                                               uint64_t flags,
                                               ScheduledCallbackFn callback,
                                               void* userData)
    {
        Require(ownerToken == 0xC0FFEE, "unexpected owner token in timer registration");
        Require(delayMs == 1000, "unexpected timer delay");
        Require(intervalMs == 1000, "unexpected repeating timer interval");
        Require(flags == OBELISK_TIMER_FLAG_REPEATING, "unexpected repeating timer flags");
        Require(callback != nullptr, "timer registration received null callback");
        Require(userData != nullptr, "timer registration received null user data");
        ++g_TimerRegisterCount;
        g_TimerCallback = callback;
        g_TimerUserData = userData;
        return 4004;
    }

    bool RemoveScheduledWithOwnerToken(uint64_t ownerToken, uint64_t timerId)
    {
        Require(ownerToken == 0xC0FFEE, "unexpected owner token in timer unregister");
        Require(timerId == 4004, "unexpected timer id");
        ++g_TimerUnregisterCount;
        g_TimerCallback = nullptr;
        g_TimerUserData = nullptr;
        return true;
    }

    void DispatchValidChatMessageEvent(uint32_t sendMode)
    {
        Require(g_ChatMessageCallback != nullptr, "chat message callback was not registered");
        Require(g_ChatMessageUserData != nullptr, "chat message user data was not registered");
        const char message[] = "!ping";
        ObeliskChatMessageEvent event{};
        event.abi_version = OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION;
        event.struct_size = sizeof(ObeliskChatMessageEvent);
        event.send_mode = sendMode;
        event.flags = OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD;
        event.sequence = 7 + sendMode;
        event.message.data = message;
        event.message.size = 5;
        g_ChatMessageCallback(&event, g_ChatMessageUserData);
    }

    void DispatchAllValidChatMessageEvents()
    {
        DispatchValidChatMessageEvent(OBELISK_CHAT_SEND_MODE_GLOBAL);
        DispatchValidChatMessageEvent(OBELISK_CHAT_SEND_MODE_TRIBE);
        DispatchValidChatMessageEvent(OBELISK_CHAT_SEND_MODE_LOCAL);
        DispatchValidChatMessageEvent(OBELISK_CHAT_SEND_MODE_ALLIANCE);
    }

    void DispatchValidTimer()
    {
        Require(g_TimerCallback != nullptr, "timer callback was not registered");
        Require(g_TimerUserData != nullptr, "timer user data was not registered");
        g_TimerCallback(4004, g_TimerUserData);
    }

    void DispatchValidGameplayPolicyEvent(uint32_t eventKind,
                                          uint32_t resourceKind,
                                          uint64_t flags,
                                          uint64_t fieldMask,
                                          uint64_t boolValues,
                                          int32_t variantIndex)
    {
        Require(g_GameplayPolicyCallback != nullptr, "gameplay policy callback was not registered");
        Require(g_GameplayPolicyUserData != nullptr, "gameplay policy user data was not registered");
        ObeliskGameplayPolicyEvent event{};
        event.abi_version = OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION;
        event.struct_size = sizeof(ObeliskGameplayPolicyEvent);
        event.event_kind = eventKind;
        event.resource_kind = resourceKind;
        event.flags = flags;
        event.field_mask = fieldMask;
        event.bool_values = boolValues;
        event.int32_values[OBELISK_GAMEPLAY_POLICY_FIELD_VARIANT_INDEX] = variantIndex;
        g_GameplayPolicyCallback(&event, g_GameplayPolicyUserData);
    }

    void DispatchValidStructureGameplayPolicyEvent(uint32_t eventKind, uint64_t fieldMask, uint64_t boolValues = 0)
    {
        DispatchValidGameplayPolicyEvent(
            eventKind,
            OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE,
            OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED,
            fieldMask,
            boolValues,
            7);
    }

    void DispatchValidInventoryGameplayPolicyEvent(uint32_t eventKind, uint64_t fieldMask, uint64_t boolValues)
    {
        DispatchValidGameplayPolicyEvent(
            eventKind,
            OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM,
            OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
                OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED,
            fieldMask,
            boolValues,
            0);
    }

    void DispatchAllValidGameplayPolicyEvents()
    {
        DispatchValidStructureGameplayPolicyEvent(
            OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACCESS_CHECK,
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE);
        DispatchValidStructureGameplayPolicyEvent(
            OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_DEMOLISH_CHECK,
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE);
        DispatchValidStructureGameplayPolicyEvent(
            OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE,
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX |
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET,
            1ull << OBELISK_GAMEPLAY_POLICY_FIELD_FORCE_SET);
        DispatchValidStructureGameplayPolicyEvent(
            OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACTIVATION_TOGGLE,
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE);
        DispatchValidStructureGameplayPolicyEvent(
            OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_PIN_CODE_CHECK,
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE);
        DispatchValidStructureGameplayPolicyEvent(
            OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_SEAT_CHECK,
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE,
            1ull << OBELISK_GAMEPLAY_POLICY_FIELD_FORCE);
        DispatchValidInventoryGameplayPolicyEvent(
            OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK,
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER,
            (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE) |
                (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_REQUESTED_BY_PLAYER));
        DispatchValidInventoryGameplayPolicyEvent(
            OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK,
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN,
            1ull << OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE);
    }

    bool DescribeResourceKind(uint32_t resourceKind, ObeliskResourceKindDescriptor* out)
    {
        Require(out != nullptr, "resource descriptor output was null");
        Require(out->struct_size >= sizeof(ObeliskResourceKindDescriptor), "resource descriptor size mismatch");

        out->abi_version = OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION;
        out->struct_size = sizeof(ObeliskResourceKindDescriptor);
        out->resource_kind = resourceKind;
        out->reserved0 = 0;
        out->flags = OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY |
            OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY |
            OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP;
        if (resourceKind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE)
        {
            out->supported_gameplay_policy_event_mask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES;
            out->supported_gameplay_policy_field_mask = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX |
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET |
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE;
            std::strncpy(out->stable_name, "structure", sizeof(out->stable_name) - 1);
            std::strncpy(out->display_name, "Structure", sizeof(out->display_name) - 1);
            return true;
        }
        if (resourceKind == OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM)
        {
            out->supported_gameplay_policy_event_mask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY;
            out->supported_gameplay_policy_field_mask = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER |
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN;
            std::strncpy(out->stable_name, "inventory_item", sizeof(out->stable_name) - 1);
            std::strncpy(out->display_name, "Inventory Item", sizeof(out->display_name) - 1);
            return true;
        }
        throw std::runtime_error("unexpected resource kind");
        return true;
    }

    bool DescribeGameplayPolicyEventKind(uint32_t eventKind, ObeliskGameplayPolicyEventDescriptor* out)
    {
        Require(out != nullptr, "event descriptor output was null");
        Require(out->struct_size >= sizeof(ObeliskGameplayPolicyEventDescriptor),
                "event descriptor size mismatch");

        out->abi_version = OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION;
        out->struct_size = sizeof(ObeliskGameplayPolicyEventDescriptor);
        out->event_kind = eventKind;
        out->flags = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD;
        out->field_mask = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE;
        if (eventKind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACCESS_CHECK)
        {
            out->resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE;
            out->flags |= OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED;
            out->event_kind_mask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK;
            std::strncpy(out->stable_name, "structure.access_check", sizeof(out->stable_name) - 1);
            std::strncpy(out->display_name, "Structure Access Check", sizeof(out->display_name) - 1);
            return true;
        }
        if (eventKind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_DEMOLISH_CHECK)
        {
            out->resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE;
            out->flags |= OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED;
            out->event_kind_mask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_DEMOLISH_CHECK;
            std::strncpy(out->stable_name, "structure.demolish_check", sizeof(out->stable_name) - 1);
            std::strncpy(out->display_name, "Structure Demolish Check", sizeof(out->display_name) - 1);
            return true;
        }
        if (eventKind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE)
        {
            out->resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE;
            out->flags |= OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED;
            out->event_kind_mask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_VARIANT_CHANGE;
            out->field_mask |= OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX |
                OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET;
            std::strncpy(out->stable_name, "structure.variant_change", sizeof(out->stable_name) - 1);
            std::strncpy(out->display_name, "Structure Variant Change", sizeof(out->display_name) - 1);
            return true;
        }
        if (eventKind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACTIVATION_TOGGLE)
        {
            out->resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE;
            out->flags |= OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED;
            out->event_kind_mask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACTIVATION_TOGGLE;
            std::strncpy(out->stable_name, "structure.activation_toggle", sizeof(out->stable_name) - 1);
            std::strncpy(out->display_name, "Structure Activation Toggle", sizeof(out->display_name) - 1);
            return true;
        }
        if (eventKind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_PIN_CODE_CHECK)
        {
            out->resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE;
            out->flags |= OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED;
            out->event_kind_mask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_PIN_CODE_CHECK;
            std::strncpy(out->stable_name, "structure.pin_code_check", sizeof(out->stable_name) - 1);
            std::strncpy(out->display_name, "Structure Pin Code Check", sizeof(out->display_name) - 1);
            return true;
        }
        if (eventKind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_SEAT_CHECK)
        {
            out->resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE;
            out->flags |= OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED;
            out->event_kind_mask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_SEAT_CHECK;
            out->field_mask |= OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE;
            std::strncpy(out->stable_name, "structure.seat_check", sizeof(out->stable_name) - 1);
            std::strncpy(out->display_name, "Structure Seat Check", sizeof(out->display_name) - 1);
            return true;
        }
        if (eventKind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK)
        {
            out->resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM;
            out->flags |= OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED;
            out->event_kind_mask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK;
            out->field_mask |= OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER;
            std::strncpy(out->stable_name, "inventory.remote_add_check", sizeof(out->stable_name) - 1);
            std::strncpy(out->display_name, "Inventory Remote Add Check", sizeof(out->display_name) - 1);
            return true;
        }
        if (eventKind == OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK)
        {
            out->resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM;
            out->flags |= OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED;
            out->event_kind_mask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK;
            out->field_mask |= OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN;
            std::strncpy(out->stable_name, "inventory.use_check", sizeof(out->stable_name) - 1);
            std::strncpy(out->display_name, "Inventory Use Check", sizeof(out->display_name) - 1);
            return true;
        }
        throw std::runtime_error("unexpected gameplay policy event kind");
        return true;
    }

    template <typename T>
    T Resolve(void* handle, const char* symbol)
    {
        dlerror();
        void* pointer = dlsym(handle, symbol);
        const char* error = dlerror();
        if (error)
            throw std::runtime_error(std::string("missing symbol ") + symbol + ": " + error);
        return reinterpret_cast<T>(pointer);
    }

    template <typename T>
    T ResolveOptional(void* handle, const char* symbol)
    {
        dlerror();
        void* pointer = dlsym(handle, symbol);
        const char* error = dlerror();
        if (error)
            return nullptr;
        return reinterpret_cast<T>(pointer);
    }
}

int main(int argc, char** argv)
{
    try
    {
        Require(argc == 6, "usage: consumer_fixture <plugin-so> <expected-plugin-id> <config-dir> <config-path> <instance-id>");

        void* handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
        if (!handle)
            throw std::runtime_error(std::string("dlopen failed: ") + dlerror());

        GetInfoFn getInfo = Resolve<GetInfoFn>(handle, "ObeliskPlugin_GetInfo");
        InitFn init = Resolve<InitFn>(handle, "ObeliskPlugin_Init");
        ShutdownFn shutdown = ResolveOptional<ShutdownFn>(handle, "ObeliskPlugin_Shutdown");
    BoolProbeFn chatMessageEventSeen =
        ResolveOptional<BoolProbeFn>(handle, "InstallLayoutConsumer_ChatMessageEventSeen");
    BoolProbeFn gameplayPolicyEventSeen =
        ResolveOptional<BoolProbeFn>(handle, "InstallLayoutConsumer_GameplayPolicyEventSeen");
    BoolProbeFn gameplayPolicyEventAccepted =
        ResolveOptional<BoolProbeFn>(handle, "InstallLayoutConsumer_GameplayPolicyEventAccepted");
    BoolProbeFn timerSeen =
        ResolveOptional<BoolProbeFn>(handle, "InstallLayoutConsumer_ScheduledCallbackSeen");
    BoolProbeFn descriptorCatalogValidated =
        ResolveOptional<BoolProbeFn>(handle, "InstallLayoutConsumer_DescriptorCatalogValidated");
    const bool expectsGameplayPolicy = gameplayPolicyEventSeen != nullptr && gameplayPolicyEventAccepted != nullptr;
    const bool expectsTimer = timerSeen != nullptr;

        ObeliskPluginMetadata metadata{};
        Require(getInfo(&metadata), "ObeliskPlugin_GetInfo failed");
        Require(metadata.abi_version == OBELISK_PLUGIN_METADATA_ABI_VERSION, "metadata ABI mismatch");
        Require(metadata.struct_size >= sizeof(ObeliskPluginMetadata), "metadata size mismatch");
        Require(std::strcmp(metadata.plugin_id, argv[2]) == 0, "plugin_id mismatch");
        Require(std::strcmp(metadata.config_file, "config.json") == 0, "config file mismatch");
        Require(metadata.default_config_json != nullptr, "missing default config");

        ObeliskApi api{};
        api.LogInfo = NoOpLog;
        api.LogWarn = NoOpLog;
        api.LogError = NoOpLog;
        api.RegisterPreProcessEvent = RegisterProcessEvent;
        api.RegisterPostProcessEvent = RegisterProcessEvent;
        api.RegisterPreProcessEventForNameIndex = RegisterNamedProcessEvent;
        api.RegisterPostProcessEventForNameIndex = RegisterNamedProcessEvent;
        api.CallProcessEvent = CallProcessEvent;
        api.abi_version = OBELISK_API_ABI_VERSION;
        api.struct_size = sizeof(ObeliskApi);
        api.capabilities = OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS |
            OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS |
            OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES |
            OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS |
            OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS |
            OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS |
            OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS |
            OBELISK_API_CAPABILITY_CHAT_EVENTS |
            OBELISK_API_CAPABILITY_TIMERS;
        api.RegisterPreProcessEventForNameIndexWithOwnerTokenHandle =
            RegisterNamedProcessEventWithOwnerTokenHandle;
        api.UnregisterProcessEventCallbackWithOwnerToken =
            UnregisterProcessEventCallbackWithOwnerToken;
        api.RegisterGameplayPolicyEventWithOwnerTokenHandle =
            RegisterGameplayPolicyEventWithOwnerTokenHandle;
        api.UnregisterGameplayPolicyEventWithOwnerToken =
            UnregisterGameplayPolicyEventWithOwnerToken;
        api.DescribeResourceKind = DescribeResourceKind;
        api.DescribeGameplayPolicyEventKind = DescribeGameplayPolicyEventKind;
        api.RegisterChatMessageEventWithOwnerTokenHandle = RegisterChatMessageEventWithOwnerTokenHandle;
        api.UnregisterChatMessageEventWithOwnerToken = UnregisterChatMessageEventWithOwnerToken;
        api.RegisterTimerWithOwnerTokenHandle = RegisterTimerWithOwnerTokenHandle;
        api.OBELISK_CONCAT(Unregister, TimerWithOwnerToken) = RemoveScheduledWithOwnerToken;

        ObeliskPluginInitContext context{};
        context.abi_version = OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION;
        context.struct_size = sizeof(ObeliskPluginInitContext);
        context.config_dir = argv[3];
        context.config_path = argv[4];
        context.instance_id = argv[5];
        context.plugin_owner_token = 0xC0FFEE;

        g_RegisterCount = 0;
        g_UnregisterCount = 0;
        g_GameplayPolicyRegisterCount = 0;
        g_GameplayPolicyUnregisterCount = 0;
        g_ChatMessageRegisterCount = 0;
        g_ChatMessageUnregisterCount = 0;
        g_TimerRegisterCount = 0;
        g_TimerUnregisterCount = 0;
        g_GameplayPolicyCallback = nullptr;
        g_GameplayPolicyUserData = nullptr;
        g_ChatMessageCallback = nullptr;
        g_ChatMessageUserData = nullptr;
        g_TimerCallback = nullptr;
        g_TimerUserData = nullptr;
        Require(init(&api, &context), "ObeliskPlugin_Init failed");
        if (descriptorCatalogValidated)
        {
            Require(descriptorCatalogValidated(), "expected plugin to validate descriptor catalog");
            Require(g_RegisterCount == 0, "descriptor catalog consumer unexpectedly registered ProcessEvent callback");
            Require(g_GameplayPolicyRegisterCount == 0,
                    "descriptor catalog consumer unexpectedly registered gameplay policy callback");
            Require(g_ChatMessageRegisterCount == 0,
                    "descriptor catalog consumer unexpectedly registered chat message callback");
            Require(g_TimerRegisterCount == 0, "descriptor catalog consumer unexpectedly registered timer");
        }
        if (shutdown)
        {
            Require(g_RegisterCount == 1, "expected one owner-token callback registration");
            if (expectsGameplayPolicy)
                Require(g_GameplayPolicyRegisterCount == 1, "expected one gameplay policy callback registration");
            else
                Require(g_GameplayPolicyRegisterCount == 0, "unexpected gameplay policy callback registration");
            Require(g_ChatMessageRegisterCount == 1, "expected one chat message callback registration");
            if (expectsTimer)
                Require(g_TimerRegisterCount == 1, "expected one timer callback registration");
            else
                Require(g_TimerRegisterCount == 0, "unexpected timer callback registration");
            if (expectsGameplayPolicy)
            {
                DispatchAllValidGameplayPolicyEvents();
                Require(gameplayPolicyEventSeen(), "expected plugin to observe all gameplay policy events");
                Require(gameplayPolicyEventAccepted(), "expected plugin to accept all gameplay policy events");
            }
            DispatchAllValidChatMessageEvents();
            if (chatMessageEventSeen)
                Require(chatMessageEventSeen(), "expected plugin to accept all chat message send modes");
            if (expectsTimer)
            {
                DispatchValidTimer();
                Require(timerSeen(), "expected plugin to observe timer callback");
            }
            api = {};
            shutdown();
            Require(g_UnregisterCount == 1, "expected one owner-token callback unregister");
            if (expectsGameplayPolicy)
                Require(g_GameplayPolicyUnregisterCount == 1, "expected one gameplay policy callback unregister");
            else
                Require(g_GameplayPolicyUnregisterCount == 0, "unexpected gameplay policy callback unregister");
            Require(g_ChatMessageUnregisterCount == 1, "expected one chat message callback unregister");
            if (expectsTimer)
                Require(g_TimerUnregisterCount == 1, "expected one timer callback unregister");
            else
                Require(g_TimerUnregisterCount == 0, "unexpected timer callback unregister");
            if (expectsGameplayPolicy)
            {
                Require(g_GameplayPolicyCallback == nullptr, "gameplay policy callback was not cleared");
                Require(g_GameplayPolicyUserData == nullptr, "gameplay policy user data was not cleared");
            }
            Require(g_ChatMessageCallback == nullptr, "chat message callback was not cleared");
            Require(g_ChatMessageUserData == nullptr, "chat message user data was not cleared");
            if (expectsTimer)
            {
                Require(g_TimerCallback == nullptr, "timer callback was not cleared");
                Require(g_TimerUserData == nullptr, "timer user data was not cleared");
            }
        }
        else
        {
            Require(g_RegisterCount == 0, "no-shutdown fixture should not register callbacks");
            Require(g_UnregisterCount == 0, "no-shutdown fixture should not unregister callbacks");
            Require(g_GameplayPolicyRegisterCount == 0, "no-shutdown fixture should not register gameplay callbacks");
            Require(g_GameplayPolicyUnregisterCount == 0, "no-shutdown fixture should not unregister gameplay callbacks");
            Require(g_ChatMessageRegisterCount == 0, "no-shutdown fixture should not register chat callbacks");
            Require(g_ChatMessageUnregisterCount == 0, "no-shutdown fixture should not unregister chat callbacks");
            Require(g_TimerRegisterCount == 0, "no-shutdown fixture should not register timer callbacks");
            Require(g_TimerUnregisterCount == 0, "no-shutdown fixture should not unregister timer callbacks");
        }
        dlclose(handle);
    }
    catch (const std::exception& e)
    {
        std::cerr << e.what() << '\n';
        return 1;
    }

    return 0;
}
