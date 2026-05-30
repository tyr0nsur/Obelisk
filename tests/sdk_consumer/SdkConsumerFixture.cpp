#include <obelisk/ObeliskApi.h>

#include <dlfcn.h>

#include <cstddef>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>
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

    constexpr size_t kOBaseEventsMaxLocalCommandBytes = 1024;

    int g_RegisterCount = 0;
    int g_UnregisterCount = 0;
    int g_GameplayPolicyRegisterCount = 0;
    int g_GameplayPolicyUnregisterCount = 0;
    int g_ChatMessageRegisterCount = 0;
    int g_ChatMessageUnregisterCount = 0;
    int g_TimerRegisterCount = 0;
    int g_TimerUnregisterCount = 0;
    bool g_ThrowLog = false;
    bool g_FailGameplayPolicyRegistration = false;
    bool g_FailChatMessageRegistration = false;
    bool g_FailTimerRegistration = false;
    bool g_ThrowLogAfterTimerRegistration = false;
    bool g_BadGameplayPolicyDescriptor = false;
    std::vector<std::string> g_InfoLogs;
    std::vector<std::string> g_ErrorLogs;
    OnProcessEventCallback g_RegisteredCallback = nullptr;
    ObeliskGameplayPolicyEventCallback g_RegisteredGameplayPolicyCallback = nullptr;
    void* g_RegisteredGameplayPolicyUserData = nullptr;
    ObeliskChatMessageEventCallback g_RegisteredChatMessageCallback = nullptr;
    void* g_RegisteredChatMessageUserData = nullptr;
    ScheduledCallbackFn g_RegisteredTimerCallback = nullptr;
    void* g_RegisteredTimerUserData = nullptr;

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    void NoOpLog(const char* message)
    {
        if (g_ThrowLog)
            throw std::runtime_error("injected log callback failure");
        (void)message;
    }

    void CaptureInfoLog(const char* message)
    {
        NoOpLog(message);
        if (message)
            g_InfoLogs.emplace_back(message);
    }

    void CaptureErrorLog(const char* message)
    {
        NoOpLog(message);
        if (message)
            g_ErrorLogs.emplace_back(message);
    }

    bool HasLogContaining(const std::vector<std::string>& logs, const char* needle)
    {
        for (const std::string& log : logs)
        {
            if (log.find(needle) != std::string::npos)
                return true;
        }
        return false;
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
        g_RegisteredCallback = callback;
        ++g_RegisterCount;
        return 1001;
    }

    bool UnregisterProcessEventCallbackWithOwnerToken(uint64_t ownerToken, uint64_t registrationId)
    {
        Require(ownerToken == 0xC0FFEE, "unexpected owner token in callback unregister");
        Require(registrationId == 1001, "unexpected callback registration id");
        g_RegisteredCallback = nullptr;
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
        if (g_FailGameplayPolicyRegistration)
            return 0;
        g_RegisteredGameplayPolicyCallback = callback;
        g_RegisteredGameplayPolicyUserData = userData;
        ++g_GameplayPolicyRegisterCount;
        return 2002;
    }

    bool UnregisterGameplayPolicyEventWithOwnerToken(uint64_t ownerToken, uint64_t registrationId)
    {
        Require(ownerToken == 0xC0FFEE, "unexpected owner token in gameplay policy unregister");
        Require(registrationId == 2002, "unexpected gameplay policy registration id");
        g_RegisteredGameplayPolicyCallback = nullptr;
        g_RegisteredGameplayPolicyUserData = nullptr;
        ++g_GameplayPolicyUnregisterCount;
        return true;
    }

    uint64_t RegisterChatMessageEventWithOwnerTokenHandle(uint64_t ownerToken,
                                                          ObeliskChatMessageEventCallback callback,
                                                          void* userData)
    {
        Require(ownerToken == 0xC0FFEE, "unexpected owner token in chat message registration");
        Require(callback != nullptr, "chat message registration received null callback");
        Require(userData != nullptr, "chat message registration received null user data");
        if (g_FailChatMessageRegistration)
            return 0;
        g_RegisteredChatMessageCallback = callback;
        g_RegisteredChatMessageUserData = userData;
        ++g_ChatMessageRegisterCount;
        return 3003;
    }

    bool UnregisterChatMessageEventWithOwnerToken(uint64_t ownerToken, uint64_t registrationId)
    {
        Require(ownerToken == 0xC0FFEE, "unexpected owner token in chat message unregister");
        Require(registrationId == 3003, "unexpected chat message registration id");
        g_RegisteredChatMessageCallback = nullptr;
        g_RegisteredChatMessageUserData = nullptr;
        ++g_ChatMessageUnregisterCount;
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
        Require(intervalMs == 0, "unexpected one-shot timer interval");
        Require(flags == 0, "unexpected timer flags");
        Require(callback != nullptr, "timer registration received null callback");
        Require(userData != nullptr, "timer registration received null user data");
        if (g_FailTimerRegistration)
            return 0;
        g_RegisteredTimerCallback = callback;
        g_RegisteredTimerUserData = userData;
        ++g_TimerRegisterCount;
        if (g_ThrowLogAfterTimerRegistration)
            g_ThrowLog = true;
        return 4004;
    }

    bool RemoveScheduledWithOwnerToken(uint64_t ownerToken, uint64_t timerId)
    {
        Require(ownerToken == 0xC0FFEE, "unexpected owner token in timer unregister");
        Require(timerId == 4004, "unexpected timer id");
        g_RegisteredTimerCallback = nullptr;
        g_RegisteredTimerUserData = nullptr;
        ++g_TimerUnregisterCount;
        return true;
    }

    void DispatchValidChatMessageEvent()
    {
        Require(g_RegisteredChatMessageCallback != nullptr, "missing chat message callback");
        Require(g_RegisteredChatMessageUserData != nullptr, "missing chat message user data");

        const char message[] = "hello";
        ObeliskChatMessageEvent event{};
        event.abi_version = OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION;
        event.struct_size = sizeof(ObeliskChatMessageEvent);
        event.send_mode = OBELISK_CHAT_SEND_MODE_GLOBAL;
        event.flags = OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD;
        event.sequence = 42;
        event.message = {message, sizeof(message) - 1};

        g_RegisteredChatMessageCallback(&event, g_RegisteredChatMessageUserData);
    }

    void DispatchValidChatMessageEventWithText(const char* message)
    {
        Require(g_RegisteredChatMessageCallback != nullptr, "missing chat message callback");
        Require(g_RegisteredChatMessageUserData != nullptr, "missing chat message user data");
        Require(message != nullptr, "chat message text was null");

        ObeliskChatMessageEvent event{};
        event.abi_version = OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION;
        event.struct_size = sizeof(ObeliskChatMessageEvent);
        event.send_mode = OBELISK_CHAT_SEND_MODE_GLOBAL;
        event.flags = OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD;
        event.sequence = 42;
        event.message = {message, std::strlen(message)};

        g_RegisteredChatMessageCallback(&event, g_RegisteredChatMessageUserData);
    }

    void DispatchChatMessageEventWithTextAndSize(const char* message, size_t size)
    {
        Require(g_RegisteredChatMessageCallback != nullptr, "missing chat message callback");
        Require(g_RegisteredChatMessageUserData != nullptr, "missing chat message user data");
        Require(message != nullptr, "chat message text was null");

        ObeliskChatMessageEvent event{};
        event.abi_version = OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION;
        event.struct_size = sizeof(ObeliskChatMessageEvent);
        event.send_mode = OBELISK_CHAT_SEND_MODE_GLOBAL;
        event.flags = OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD;
        event.sequence = 43;
        event.message = {message, size};

        g_RegisteredChatMessageCallback(&event, g_RegisteredChatMessageUserData);
    }

    void DispatchValidTimer()
    {
        Require(g_RegisteredTimerCallback != nullptr, "missing timer callback");
        Require(g_RegisteredTimerUserData != nullptr, "missing timer user data");
        g_RegisteredTimerCallback(4004, g_RegisteredTimerUserData);
    }

    void DispatchValidStructureGameplayPolicyEvent()
    {
        Require(g_RegisteredGameplayPolicyCallback != nullptr, "missing gameplay policy callback");
        Require(g_RegisteredGameplayPolicyUserData != nullptr, "missing gameplay policy user data");

        ObeliskGameplayPolicyEvent event{};
        event.abi_version = OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION;
        event.struct_size = sizeof(ObeliskGameplayPolicyEvent);
        event.event_kind = OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE;
        event.resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE;
        event.flags = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
            OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED;
        event.field_mask = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX |
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET;
        event.bool_values = 1ull << OBELISK_GAMEPLAY_POLICY_FIELD_FORCE_SET;
        event.int32_values[OBELISK_GAMEPLAY_POLICY_FIELD_VARIANT_INDEX] = 7;

        g_RegisteredGameplayPolicyCallback(&event, g_RegisteredGameplayPolicyUserData);
    }

    void DispatchValidInventoryRemoteAddGameplayPolicyEvent()
    {
        Require(g_RegisteredGameplayPolicyCallback != nullptr, "missing gameplay policy callback");
        Require(g_RegisteredGameplayPolicyUserData != nullptr, "missing gameplay policy user data");

        ObeliskGameplayPolicyEvent event{};
        event.abi_version = OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION;
        event.struct_size = sizeof(ObeliskGameplayPolicyEvent);
        event.event_kind = OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK;
        event.resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM;
        event.flags = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
            OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED;
        event.field_mask = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER;
        event.bool_values = (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE) |
            (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_REQUESTED_BY_PLAYER);

        g_RegisteredGameplayPolicyCallback(&event, g_RegisteredGameplayPolicyUserData);
    }

    void DispatchValidInventoryUseGameplayPolicyEvent()
    {
        Require(g_RegisteredGameplayPolicyCallback != nullptr, "missing gameplay policy callback");
        Require(g_RegisteredGameplayPolicyUserData != nullptr, "missing gameplay policy user data");

        ObeliskGameplayPolicyEvent event{};
        event.abi_version = OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION;
        event.struct_size = sizeof(ObeliskGameplayPolicyEvent);
        event.event_kind = OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK;
        event.resource_kind = OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM;
        event.flags = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
            OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED;
        event.field_mask = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE |
            OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN;
        event.bool_values = 1ull << OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE;

        g_RegisteredGameplayPolicyCallback(&event, g_RegisteredGameplayPolicyUserData);
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
            if (!g_BadGameplayPolicyDescriptor)
                out->field_mask |= OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN;
            std::strncpy(out->stable_name, "inventory.use_check", sizeof(out->stable_name) - 1);
            std::strncpy(out->display_name, "Inventory Use Check", sizeof(out->display_name) - 1);
            return true;
        }
        throw std::runtime_error("unexpected gameplay policy event kind");
    }

    constexpr const char* kActiveOBaseEventsConfig = R"json({
    "enabled": true,
    "log_level": "info",
    "allow_all_instances": false,
    "instance_allowlist": ["sdk-consumer-test"],
    "process_event": {
        "enabled": true,
        "filtered_function_index": 42,
        "log_limit": 1
    }
})json";

    constexpr const char* kActiveOBaseEventsChatCommandConfig = R"json({
    "enabled": true,
    "log_level": "info",
    "allow_all_instances": false,
    "instance_allowlist": ["sdk-consumer-test"],
    "process_event": {
        "enabled": false,
        "filtered_function_index": -1,
        "log_limit": 1
    },
    "chat_command_helper": {
        "enabled": true,
        "prefix": "/",
        "log_limit": 8
    }
})json";

    constexpr const char* kInvalidChatCommandConfig = R"json({
    "enabled": true,
    "log_level": "info",
    "allow_all_instances": false,
    "instance_allowlist": ["sdk-consumer-test"],
    "process_event": {
        "enabled": false,
        "filtered_function_index": -1,
        "log_limit": 1
    },
    "chat_command_helper": {
        "enabled": true,
        "prefix": "",
        "log_limit": 1
    }
})json";

    constexpr const char* kUnsupportedMapAllowlistConfig = R"json({
    "enabled": true,
    "log_level": "info",
    "allow_all_instances": false,
    "instance_allowlist": ["sdk-consumer-test"],
    "map_allowlist": ["Ragnarok"],
    "process_event": {
        "enabled": true,
        "filtered_function_index": 42,
        "log_limit": 1
    }
})json";

    constexpr const char* kInvalidProcessEventConfig = R"json({
    "enabled": true,
    "log_level": "info",
    "allow_all_instances": false,
    "instance_allowlist": ["sdk-consumer-test"],
    "process_event": {
        "enabled": true,
        "filtered_function_index": -1,
        "log_limit": 1
    }
})json";

    constexpr const char* kUnsafeInstanceAllowlistConfig = R"json({
    "enabled": true,
    "log_level": "info",
    "allow_all_instances": false,
    "instance_allowlist": ["../sdk-consumer-test"],
    "process_event": {
        "enabled": true,
        "filtered_function_index": 42,
        "log_limit": 1
    }
})json";

    std::filesystem::path CreateConfigDir(const char* defaultConfigJson)
    {
        char templatePath[] = "/tmp/obelisk-sdk-consumer.XXXXXX";
        char* directory = mkdtemp(templatePath);
        Require(directory != nullptr, "mkdtemp failed");

        const std::filesystem::path configDir = directory;
        std::ofstream config(configDir / "config.json");
        Require(config.is_open(), "failed to create plugin config");
        config << defaultConfigJson;
        config.close();
        return configDir;
    }

    template <typename T>
    T ResolveRequired(void* handle, const char* symbol)
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
        Require(argc >= 2 && argc <= 4, "usage: sdk_consumer_fixture <plugin-so> [expected-plugin-id] [mode]");
        const char* expectedPluginId = argc == 3 ? argv[2] : "sdk_consumer_minimal";
        if (argc == 4)
            expectedPluginId = argv[2];
        const std::string mode = argc == 4 ? argv[3] : "";

        void* handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
        if (!handle)
            throw std::runtime_error(std::string("dlopen failed: ") + dlerror());

        const auto closeHandle = [&handle]() {
            if (handle)
            {
                dlclose(handle);
                handle = nullptr;
            }
        };

        GetInfoFn getInfo = ResolveRequired<GetInfoFn>(handle, "ObeliskPlugin_GetInfo");
        InitFn init = ResolveRequired<InitFn>(handle, "ObeliskPlugin_Init");
        ShutdownFn shutdown = ResolveOptional<ShutdownFn>(handle, "ObeliskPlugin_Shutdown");
        BoolProbeFn gameplayPolicyEventSeen =
            ResolveOptional<BoolProbeFn>(handle, "SdkConsumerMinimal_GameplayPolicyEventSeen");
        BoolProbeFn gameplayPolicyEventAccepted =
            ResolveOptional<BoolProbeFn>(handle, "SdkConsumerMinimal_GameplayPolicyEventAccepted");
        BoolProbeFn chatMessageEventSeen =
            ResolveOptional<BoolProbeFn>(handle, "SdkConsumerMinimal_ChatMessageEventSeen");
        BoolProbeFn chatMessageEventAccepted =
            ResolveOptional<BoolProbeFn>(handle, "SdkConsumerMinimal_ChatMessageEventAccepted");
        BoolProbeFn timerSeen =
            ResolveOptional<BoolProbeFn>(handle, "SdkConsumerMinimal_ScheduledCallbackSeen");
        BoolProbeFn timerAccepted =
            ResolveOptional<BoolProbeFn>(handle, "SdkConsumerMinimal_ScheduledCallbackAccepted");
        if (!chatMessageEventSeen)
            chatMessageEventSeen = ResolveOptional<BoolProbeFn>(handle, "CAbiMinimal_ChatMessageEventSeen");
        if (!chatMessageEventAccepted)
            chatMessageEventAccepted = ResolveOptional<BoolProbeFn>(handle, "CAbiMinimal_ChatMessageEventAccepted");
        if (!gameplayPolicyEventSeen)
            gameplayPolicyEventSeen = ResolveOptional<BoolProbeFn>(handle, "CAbiMinimal_GameplayPolicyEventSeen");
        if (!gameplayPolicyEventAccepted)
            gameplayPolicyEventAccepted = ResolveOptional<BoolProbeFn>(handle, "CAbiMinimal_GameplayPolicyEventAccepted");
        if (!timerSeen)
            timerSeen = ResolveOptional<BoolProbeFn>(handle, "CAbiMinimal_TimerSeen");
        if (!timerAccepted)
            timerAccepted = ResolveOptional<BoolProbeFn>(handle, "CAbiMinimal_TimerAccepted");
        if (!timerSeen)
            timerSeen = ResolveOptional<BoolProbeFn>(handle, "OProcessTimer_TimerSeen");
        if (!timerAccepted)
            timerAccepted = ResolveOptional<BoolProbeFn>(handle, "OProcessTimer_TimerAccepted");
        ObeliskPluginMetadata metadata{};
        Require(getInfo(&metadata), "ObeliskPlugin_GetInfo failed");
        Require(metadata.abi_version == OBELISK_PLUGIN_METADATA_ABI_VERSION, "metadata ABI mismatch");
        Require(metadata.struct_size >= sizeof(ObeliskPluginMetadata), "metadata size mismatch");
        Require(std::strcmp(metadata.plugin_id, expectedPluginId) == 0, "plugin_id mismatch");
        Require(std::strcmp(metadata.config_file, "config.json") == 0, "config file mismatch");
        Require(metadata.default_config_json != nullptr, "missing default config");
        const char* configJson = metadata.default_config_json;
        if (mode == "active-process-event" || mode == "callback-throw-log")
            configJson = kActiveOBaseEventsConfig;
        else if (mode == "active-chat-command-helper" ||
            mode == "active-chat-command-helper-no-chat-capability")
            configJson = kActiveOBaseEventsChatCommandConfig;
        else if (mode == "active-timer" ||
            mode == "active-timer-double-shutdown" ||
            mode == "throw-log-after-timer-registration" ||
            (mode == "fail-timer-registration" && std::strcmp(expectedPluginId, "oProcessTimer") == 0))
            configJson = R"json({
    "enabled": true,
    "allow_all_instances": false,
    "instance_allowlist": ["sdk-consumer-test"]
})json";
        else if (mode == "unsupported-map-allowlist")
            configJson = kUnsupportedMapAllowlistConfig;
        else if (mode == "invalid-process-event-config")
            configJson = kInvalidProcessEventConfig;
        else if (mode == "invalid-chat-command-config")
            configJson = kInvalidChatCommandConfig;
        else if (mode == "unsafe-instance-allowlist")
            configJson = kUnsafeInstanceAllowlistConfig;
        std::filesystem::path configDir = CreateConfigDir(configJson);
        const auto cleanupConfigDir = [&configDir]() {
            if (!configDir.empty())
                std::filesystem::remove_all(configDir);
        };

        ObeliskApi api{};
        api.LogInfo = CaptureInfoLog;
        api.LogWarn = NoOpLog;
        api.LogError = CaptureErrorLog;
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
            OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS;
        api.RegisterPreProcessEventForNameIndexWithOwnerTokenHandle =
            RegisterNamedProcessEventWithOwnerTokenHandle;
        api.UnregisterProcessEventCallbackWithOwnerToken =
            UnregisterProcessEventCallbackWithOwnerToken;
        if (mode != "no-gameplay-policy-capability")
        {
            api.capabilities |= OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS |
                OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS |
                OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS;
            api.RegisterGameplayPolicyEventWithOwnerTokenHandle =
                RegisterGameplayPolicyEventWithOwnerTokenHandle;
            api.UnregisterGameplayPolicyEventWithOwnerToken =
                UnregisterGameplayPolicyEventWithOwnerToken;
            api.DescribeResourceKind = DescribeResourceKind;
            api.DescribeGameplayPolicyEventKind = DescribeGameplayPolicyEventKind;
        }
        if (mode != "no-chat-message-capability" &&
            mode != "active-chat-command-helper-no-chat-capability")
        {
            api.capabilities |= OBELISK_API_CAPABILITY_CHAT_EVENTS;
            api.RegisterChatMessageEventWithOwnerTokenHandle =
                RegisterChatMessageEventWithOwnerTokenHandle;
            api.UnregisterChatMessageEventWithOwnerToken =
                UnregisterChatMessageEventWithOwnerToken;
        }
        if (mode != "no-timer-capability")
        {
            api.capabilities |= OBELISK_API_CAPABILITY_TIMERS;
            api.RegisterTimerWithOwnerTokenHandle = RegisterTimerWithOwnerTokenHandle;
            api.OBELISK_CONCAT(Unregister, TimerWithOwnerToken) = RemoveScheduledWithOwnerToken;
        }
        if (mode == "short-api-before-gameplay-policy")
        {
            api.struct_size = offsetof(ObeliskApi, RegisterGameplayPolicyEventWithOwnerTokenHandle);
            api.RegisterGameplayPolicyEventWithOwnerTokenHandle = nullptr;
            api.UnregisterGameplayPolicyEventWithOwnerToken = nullptr;
            api.RegisterChatMessageEventWithOwnerTokenHandle = nullptr;
            api.UnregisterChatMessageEventWithOwnerToken = nullptr;
            api.RegisterTimerWithOwnerTokenHandle = nullptr;
            api.OBELISK_CONCAT(Unregister, TimerWithOwnerToken) = nullptr;
        }
        if (mode == "fail-gameplay-policy-registration")
            g_FailGameplayPolicyRegistration = true;
        if (mode == "fail-chat-message-registration")
            g_FailChatMessageRegistration = true;
        if (mode == "fail-timer-registration")
            g_FailTimerRegistration = true;
        if (mode == "throw-log-after-timer-registration")
            g_ThrowLogAfterTimerRegistration = true;
        if (mode == "bad-gameplay-policy-descriptor")
            g_BadGameplayPolicyDescriptor = true;

        ObeliskPluginInitContext context{};
        context.abi_version = OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION;
        context.struct_size = sizeof(ObeliskPluginInitContext);
        const std::string configDirString = configDir.string();
        const std::string configPathString = (configDir / "config.json").string();
        context.config_dir = configDirString.c_str();
        context.config_path = configPathString.c_str();
        context.instance_id = "sdk-consumer-test";
        context.plugin_owner_token = 0xC0FFEE;
        if (mode == "zero-owner-token")
            context.plugin_owner_token = 0;

        if (mode == "throw-log-init")
            g_ThrowLog = true;

        if (mode == "invalid-context")
        {
            Require(!init(&api, nullptr), "plugin accepted null init context");
            ObeliskPluginInitContext shortContext = context;
            shortContext.struct_size = offsetof(ObeliskPluginInitContext, plugin_owner_token);
            Require(!init(&api, &shortContext), "plugin accepted too-small init context");
            Require(g_RegisterCount == 0, "invalid context unexpectedly registered a callback");
            Require(g_UnregisterCount == 0, "invalid context unexpectedly unregistered a callback");
            Require(g_GameplayPolicyRegisterCount == 0,
                "invalid context unexpectedly registered a gameplay policy callback");
            Require(g_GameplayPolicyUnregisterCount == 0,
                "invalid context unexpectedly unregistered a gameplay policy callback");
            Require(g_ChatMessageRegisterCount == 0,
                "invalid context unexpectedly registered a chat message callback");
            Require(g_ChatMessageUnregisterCount == 0,
                "invalid context unexpectedly unregistered a chat message callback");
            Require(g_TimerRegisterCount == 0,
                "invalid context unexpectedly registered a timer callback");
            Require(g_TimerUnregisterCount == 0,
                "invalid context unexpectedly unregistered a timer callback");
            cleanupConfigDir();
            closeHandle();
            return 0;
        }

        const bool initSucceeded = init(&api, &context);
        if (mode == "zero-owner-token")
        {
            Require(!initSucceeded, "plugin accepted zero owner token");
            Require(g_RegisterCount == 0, "zero owner token unexpectedly registered a callback");
            Require(g_UnregisterCount == 0, "zero owner token unexpectedly unregistered a callback");
            Require(g_GameplayPolicyRegisterCount == 0,
                "zero owner token unexpectedly registered a gameplay policy callback");
            Require(g_GameplayPolicyUnregisterCount == 0,
                "zero owner token unexpectedly unregistered a gameplay policy callback");
            Require(g_ChatMessageRegisterCount == 0,
                "zero owner token unexpectedly registered a chat message callback");
            Require(g_ChatMessageUnregisterCount == 0,
                "zero owner token unexpectedly unregistered a chat message callback");
            Require(g_TimerRegisterCount == 0, "zero owner token unexpectedly registered a timer callback");
            Require(g_TimerUnregisterCount == 0, "zero owner token unexpectedly unregistered a timer callback");
            cleanupConfigDir();
            closeHandle();
            return 0;
        }
        if (mode == "throw-log-init")
        {
            Require(!initSucceeded, "plugin allowed log exception to cross or reported init success");
            Require(g_RegisterCount == 0, "failed init unexpectedly registered a callback");
            Require(g_UnregisterCount == 0, "failed init unexpectedly unregistered a callback");
            Require(g_GameplayPolicyRegisterCount == 0,
                "failed init unexpectedly registered a gameplay policy callback");
            Require(g_GameplayPolicyUnregisterCount == 0,
                "failed init unexpectedly unregistered a gameplay policy callback");
            Require(g_ChatMessageRegisterCount == 0,
                "failed init unexpectedly registered a chat message callback");
            Require(g_ChatMessageUnregisterCount == 0,
                "failed init unexpectedly unregistered a chat message callback");
            Require(g_TimerRegisterCount == 0, "failed init unexpectedly registered a timer callback");
            Require(g_TimerUnregisterCount == 0, "failed init unexpectedly unregistered a timer callback");
            cleanupConfigDir();
            closeHandle();
            return 0;
        }
        if (mode == "throw-log-after-timer-registration")
        {
            Require(!initSucceeded, "plugin accepted log failure after timer registration");
            Require(g_TimerRegisterCount == 1, "plugin did not register timer before injected log failure");
            Require(g_TimerUnregisterCount == 1, "plugin did not unregister timer after injected log failure");
            Require(g_RegisteredTimerCallback == nullptr,
                "timer callback survived post-registration init failure cleanup");
            Require(g_RegisteredTimerUserData == nullptr,
                "timer user data survived post-registration init failure cleanup");
            g_ThrowLog = false;
            g_ThrowLogAfterTimerRegistration = false;
            cleanupConfigDir();
            closeHandle();
            return 0;
        }
        if (std::strcmp(expectedPluginId, "oProcessTimer") == 0 &&
            (mode == "no-timer-capability" || mode == "short-api-before-gameplay-policy"))
        {
            Require(!initSucceeded, "timer example accepted missing or too-short timer API");
            Require(g_TimerRegisterCount == 0, "timer example unexpectedly registered with unavailable timer API");
            Require(g_TimerUnregisterCount == 0, "timer example unexpectedly unregistered with unavailable timer API");
            cleanupConfigDir();
            closeHandle();
            return 0;
        }
        if (mode == "fail-gameplay-policy-registration")
        {
            Require(!initSucceeded, "plugin accepted failed gameplay policy registration");
            Require(g_GameplayPolicyRegisterCount == 0,
                "failed gameplay policy registration should not be counted as accepted");
            Require(g_GameplayPolicyUnregisterCount == 0,
                "failed gameplay policy registration unexpectedly unregistered a callback");
            Require(g_ChatMessageRegisterCount == 0,
                "plugin registered chat after gameplay policy registration failed");
            Require(g_TimerRegisterCount == 0,
                "plugin registered timer after gameplay policy registration failed");
            g_FailGameplayPolicyRegistration = false;
            cleanupConfigDir();
            closeHandle();
            return 0;
        }
        if (mode == "bad-gameplay-policy-descriptor")
        {
            Require(!initSucceeded, "plugin accepted malformed gameplay policy descriptor metadata");
            Require(g_RegisterCount == 0,
                "bad gameplay policy descriptor unexpectedly registered a ProcessEvent callback");
            Require(g_GameplayPolicyRegisterCount == 0,
                "bad gameplay policy descriptor unexpectedly registered a gameplay policy callback");
            Require(g_ChatMessageRegisterCount == 0,
                "bad gameplay policy descriptor unexpectedly registered a chat message callback");
            Require(g_TimerRegisterCount == 0,
                "bad gameplay policy descriptor unexpectedly registered a timer callback");
            g_BadGameplayPolicyDescriptor = false;
            cleanupConfigDir();
            closeHandle();
            return 0;
        }
        if (mode == "fail-chat-message-registration")
        {
            Require(!initSucceeded, "plugin accepted failed chat message registration");
            Require(g_GameplayPolicyRegisterCount == 1,
                "plugin did not register gameplay policy before chat failure");
            Require(g_GameplayPolicyUnregisterCount == 1,
                "plugin did not unregister gameplay policy after chat failure");
            Require(g_RegisteredGameplayPolicyCallback == nullptr,
                "gameplay policy callback survived failed chat registration cleanup");
            Require(g_RegisteredGameplayPolicyUserData == nullptr,
                "gameplay policy user data survived failed chat registration cleanup");
            Require(g_ChatMessageRegisterCount == 0,
                "failed chat message registration should not be counted as accepted");
            Require(g_ChatMessageUnregisterCount == 0,
                "failed chat message registration unexpectedly unregistered a callback");
            Require(g_TimerRegisterCount == 0,
                "plugin registered timer after chat message registration failed");
            g_FailChatMessageRegistration = false;
            cleanupConfigDir();
            closeHandle();
            return 0;
        }
        if (mode == "fail-timer-registration")
        {
            Require(!initSucceeded, "plugin accepted failed timer registration");
            if (std::strcmp(expectedPluginId, "oProcessTimer") == 0)
            {
                Require(g_GameplayPolicyRegisterCount == 0,
                    "timer example unexpectedly registered gameplay policy before timer failure");
                Require(g_GameplayPolicyUnregisterCount == 0,
                    "timer example unexpectedly unregistered gameplay policy after timer failure");
                Require(g_ChatMessageRegisterCount == 0,
                    "timer example unexpectedly registered chat before timer failure");
                Require(g_ChatMessageUnregisterCount == 0,
                    "timer example unexpectedly unregistered chat after timer failure");
            }
            else
            {
                Require(g_GameplayPolicyRegisterCount == 1,
                    "plugin did not register gameplay policy before timer failure");
                Require(g_GameplayPolicyUnregisterCount == 1,
                    "plugin did not unregister gameplay policy after timer failure");
                Require(g_ChatMessageRegisterCount == 1,
                    "plugin did not register chat before timer failure");
                Require(g_ChatMessageUnregisterCount == 1,
                    "plugin did not unregister chat after timer failure");
            }
            Require(g_RegisteredGameplayPolicyCallback == nullptr,
                "gameplay policy callback survived failed timer registration cleanup");
            Require(g_RegisteredChatMessageCallback == nullptr,
                "chat message callback survived failed timer registration cleanup");
            Require(g_TimerRegisterCount == 0,
                "failed timer registration should not be counted as accepted");
            Require(g_TimerUnregisterCount == 0,
                "failed timer registration unexpectedly unregistered a callback");
            g_FailTimerRegistration = false;
            cleanupConfigDir();
            closeHandle();
            return 0;
        }
        if (mode == "unsupported-map-allowlist")
        {
            Require(!initSucceeded, "oBaseEvents accepted unsupported map_allowlist");
            Require(g_RegisterCount == 0, "rejected oBaseEvents unexpectedly registered a callback");
            Require(g_UnregisterCount == 0, "rejected oBaseEvents unexpectedly unregistered a callback");
            cleanupConfigDir();
            closeHandle();
            return 0;
        }
        if (mode == "invalid-process-event-config")
        {
            Require(!initSucceeded, "oBaseEvents accepted enabled ProcessEvent config without a valid filtered index");
            Require(g_RegisterCount == 0, "rejected oBaseEvents unexpectedly registered a callback");
            Require(g_UnregisterCount == 0, "rejected oBaseEvents unexpectedly unregistered a callback");
            cleanupConfigDir();
            closeHandle();
            return 0;
        }
        if (mode == "invalid-chat-command-config")
        {
            Require(!initSucceeded, "oBaseEvents accepted invalid chat command helper config");
            Require(g_ChatMessageRegisterCount == 0,
                "rejected oBaseEvents unexpectedly registered a chat message callback");
            Require(g_ChatMessageUnregisterCount == 0,
                "rejected oBaseEvents unexpectedly unregistered a chat message callback");
            cleanupConfigDir();
            closeHandle();
            return 0;
        }
        if (mode == "active-chat-command-helper-no-chat-capability")
        {
            Require(!initSucceeded, "oBaseEvents accepted active chat command helper without chat capability");
            Require(g_ChatMessageRegisterCount == 0,
                "chat command helper registered without chat capability");
            Require(g_ChatMessageUnregisterCount == 0,
                "chat command helper unregistered without chat capability");
            cleanupConfigDir();
            closeHandle();
            return 0;
        }
        if (mode == "unsafe-instance-allowlist")
        {
            Require(!initSucceeded, "oBaseEvents accepted unsafe instance_allowlist entry");
            Require(g_RegisterCount == 0, "rejected oBaseEvents unexpectedly registered a callback");
            Require(g_UnregisterCount == 0, "rejected oBaseEvents unexpectedly unregistered a callback");
            cleanupConfigDir();
            closeHandle();
            return 0;
        }

        Require(initSucceeded, "ObeliskPlugin_Init failed");
        const bool hasGameplayPolicyProbe = gameplayPolicyEventSeen && gameplayPolicyEventAccepted;
        const bool hasChatMessageProbe = chatMessageEventSeen && chatMessageEventAccepted;
        const bool hasTimerProbe = timerSeen && timerAccepted;
        if (hasGameplayPolicyProbe && mode == "short-api-before-gameplay-policy")
        {
            Require(g_GameplayPolicyRegisterCount == 0,
                "plugin registered gameplay policy callback with short API table");
            Require(g_GameplayPolicyUnregisterCount == 0,
                "plugin unregistered gameplay policy callback with short API table");
            Require(g_ChatMessageRegisterCount == 0,
                "plugin registered chat callback with short API table");
            Require(g_ChatMessageUnregisterCount == 0,
                "plugin unregistered chat callback with short API table");
            Require(!gameplayPolicyEventSeen(), "plugin reported gameplay policy event with short API table");
            Require(!gameplayPolicyEventAccepted(), "plugin accepted gameplay policy event with short API table");
        }
        else if (hasGameplayPolicyProbe && mode == "no-gameplay-policy-capability")
        {
            Require(g_GameplayPolicyRegisterCount == 0,
                "plugin registered gameplay policy callback without capability");
            Require(g_GameplayPolicyUnregisterCount == 0,
                "plugin unregistered gameplay policy callback without capability");
            Require(!gameplayPolicyEventSeen(), "plugin reported gameplay policy event without registration");
            Require(!gameplayPolicyEventAccepted(), "plugin accepted gameplay policy event without registration");
        }
        else if (hasGameplayPolicyProbe)
        {
            Require(g_GameplayPolicyRegisterCount == 1,
                "plugin did not register one gameplay policy callback");
            Require(g_GameplayPolicyUnregisterCount == 0,
                "plugin unregistered gameplay policy callback before shutdown");
            DispatchValidStructureGameplayPolicyEvent();
            Require(gameplayPolicyEventSeen(), "plugin did not observe structure gameplay policy event");
            Require(gameplayPolicyEventAccepted(), "plugin did not validate copied structure gameplay policy event");
            DispatchValidInventoryRemoteAddGameplayPolicyEvent();
            Require(gameplayPolicyEventAccepted(),
                "plugin did not validate copied requested-by-player inventory policy event");
            DispatchValidInventoryUseGameplayPolicyEvent();
            Require(gameplayPolicyEventAccepted(),
                "plugin did not validate copied ignore-cooldown inventory policy event");
        }
        if (hasChatMessageProbe && mode == "short-api-before-gameplay-policy")
        {
            Require(g_ChatMessageRegisterCount == 0,
                "plugin registered chat message callback with short API table");
            Require(g_ChatMessageUnregisterCount == 0,
                "plugin unregistered chat message callback with short API table");
            Require(!chatMessageEventSeen(), "plugin reported chat message event with short API table");
            Require(!chatMessageEventAccepted(), "plugin accepted chat message event with short API table");
        }
        else if (hasChatMessageProbe && mode == "no-chat-message-capability")
        {
            Require(g_ChatMessageRegisterCount == 0,
                "plugin registered chat message callback without capability");
            Require(g_ChatMessageUnregisterCount == 0,
                "plugin unregistered chat message callback without capability");
            Require(!chatMessageEventSeen(), "plugin reported chat message event without registration");
            Require(!chatMessageEventAccepted(), "plugin accepted chat message event without registration");
        }
        else if (hasChatMessageProbe)
        {
            Require(g_ChatMessageRegisterCount == 1,
                "plugin did not register one chat message callback");
            Require(g_ChatMessageUnregisterCount == 0,
                "plugin unregistered chat message callback before shutdown");
            DispatchValidChatMessageEvent();
            Require(chatMessageEventSeen(), "plugin did not observe chat message event");
            Require(chatMessageEventAccepted(), "plugin did not validate copied chat message event");
        }
        if (hasTimerProbe && mode == "short-api-before-gameplay-policy")
        {
            Require(g_TimerRegisterCount == 0,
                "plugin registered timer callback with short API table");
            Require(g_TimerUnregisterCount == 0,
                "plugin unregistered timer callback with short API table");
            Require(!timerSeen(), "plugin reported timer event with short API table");
            Require(!timerAccepted(), "plugin accepted timer event with short API table");
        }
        else if (hasTimerProbe && mode == "no-timer-capability")
        {
            Require(g_TimerRegisterCount == 0,
                "plugin registered timer callback without capability");
            Require(g_TimerUnregisterCount == 0,
                "plugin unregistered timer callback without capability");
            Require(!timerSeen(), "plugin reported timer event without registration");
            Require(!timerAccepted(), "plugin accepted timer event without registration");
        }
        else if (hasTimerProbe && (mode == "active-timer" ||
            mode == "active-timer-double-shutdown" ||
            std::strcmp(expectedPluginId, "oProcessTimer") != 0))
        {
            Require(g_TimerRegisterCount == 1, "plugin did not register one timer callback");
            Require(g_TimerUnregisterCount == 0, "plugin unregistered timer callback before shutdown");
            DispatchValidTimer();
            Require(timerSeen(), "plugin did not observe timer event");
            Require(timerAccepted(), "plugin did not validate timer event");
        }
        else if (hasTimerProbe && std::strcmp(expectedPluginId, "oProcessTimer") == 0)
        {
            Require(g_TimerRegisterCount == 0, "disabled timer example unexpectedly registered a timer");
            Require(g_TimerUnregisterCount == 0, "disabled timer example unexpectedly unregistered a timer");
            Require(!timerSeen(), "disabled timer example reported timer event");
            Require(!timerAccepted(), "disabled timer example accepted timer event");
        }
        if (mode == "callback-throw-log")
        {
            Require(g_RegisterCount == 1, "active plugin did not register one callback");
            Require(g_RegisteredCallback != nullptr, "active plugin did not expose callback to fixture");
            g_ThrowLog = true;
            Require(g_RegisteredCallback(nullptr, nullptr, nullptr), "callback returned false");
            g_ThrowLog = false;
        }
        if (mode == "active-chat-command-helper")
        {
            Require(g_RegisterCount == 0, "chat command helper unexpectedly registered ProcessEvent callback");
            Require(g_UnregisterCount == 0, "chat command helper unexpectedly unregistered ProcessEvent callback");
            Require(g_ChatMessageRegisterCount == 1,
                "chat command helper did not register one chat message callback");
            Require(g_ChatMessageUnregisterCount == 0,
                "chat command helper unregistered chat callback before shutdown");
            DispatchValidChatMessageEventWithText("hello");
            DispatchValidChatMessageEventWithText("!help");
            Require(!HasLogContaining(g_InfoLogs, "Local chat command matched"),
                "chat command helper matched a message without configured prefix");
            DispatchValidChatMessageEventWithText("/help raw-secret");
            Require(HasLogContaining(g_InfoLogs, "Local chat command matched principal=unknown command=help"),
                "chat command helper did not accept local help command");
            DispatchValidChatMessageEventWithText("/dance raw-secret");
            Require(HasLogContaining(g_InfoLogs,
                    "Local chat command rejected reason=unknown-command principal=unknown command=dance"),
                "chat command helper did not reject unknown local command");
            DispatchValidChatMessageEventWithText("/bad$name raw-secret");
            Require(HasLogContaining(g_ErrorLogs, "Local chat command rejected reason=invalid-command-name"),
                "chat command helper did not reject invalid local command name");
            DispatchChatMessageEventWithTextAndSize(
                "/help oversize-secret",
                kOBaseEventsMaxLocalCommandBytes + 1);
            Require(HasLogContaining(g_ErrorLogs, "Local chat command rejected reason=malformed-event"),
                "chat command helper did not reject oversized chat message event");
            Require(!HasLogContaining(g_InfoLogs, "hello"), "chat command helper logged raw non-command chat text");
            Require(!HasLogContaining(g_InfoLogs, "raw-secret") &&
                    !HasLogContaining(g_ErrorLogs, "raw-secret"),
                "chat command helper logged raw command arguments");
            Require(!HasLogContaining(g_InfoLogs, "oversize-secret") &&
                    !HasLogContaining(g_ErrorLogs, "oversize-secret"),
                "chat command helper logged raw oversized chat text");
        }
        api = {};
        if (shutdown)
            shutdown();
        if (mode == "active-timer-double-shutdown" && shutdown)
            shutdown();
        if (mode == "active-process-event" || mode == "callback-throw-log")
        {
            Require(g_RegisterCount == 1, "active plugin did not register one callback");
            Require(g_UnregisterCount == 1, "active plugin did not unregister one callback");
            Require(g_RegisteredCallback == nullptr, "active plugin callback survived shutdown unregister");
        }
        if (mode == "active-chat-command-helper")
        {
            Require(g_ChatMessageRegisterCount == 1,
                "chat command helper did not register one chat message callback");
            Require(g_ChatMessageUnregisterCount == 1,
                "chat command helper did not unregister one chat message callback");
            Require(g_RegisteredChatMessageCallback == nullptr,
                "chat command helper callback survived shutdown unregister");
            Require(g_RegisteredChatMessageUserData == nullptr,
                "chat command helper user data survived shutdown unregister");
        }
        if (hasGameplayPolicyProbe && mode == "short-api-before-gameplay-policy")
        {
            Require(g_GameplayPolicyRegisterCount == 0,
                "plugin registered gameplay policy callback with short API table");
            Require(g_GameplayPolicyUnregisterCount == 0,
                "plugin unregistered gameplay policy callback with short API table");
        }
        else if (hasGameplayPolicyProbe && mode == "no-gameplay-policy-capability")
        {
            Require(g_GameplayPolicyRegisterCount == 0,
                "plugin registered gameplay policy callback without capability");
            Require(g_GameplayPolicyUnregisterCount == 0,
                "plugin unregistered gameplay policy callback without capability");
        }
        else if (hasGameplayPolicyProbe)
        {
            Require(g_GameplayPolicyRegisterCount == 1,
                "plugin did not register one gameplay policy callback");
            Require(g_GameplayPolicyUnregisterCount == 1,
                "plugin did not unregister one gameplay policy callback");
            Require(g_RegisteredGameplayPolicyCallback == nullptr,
                "gameplay policy callback survived shutdown unregister");
            Require(g_RegisteredGameplayPolicyUserData == nullptr,
                "gameplay policy user data survived shutdown unregister");
        }
        if (hasChatMessageProbe && mode == "short-api-before-gameplay-policy")
        {
            Require(g_ChatMessageRegisterCount == 0,
                "plugin registered chat message callback with short API table");
            Require(g_ChatMessageUnregisterCount == 0,
                "plugin unregistered chat message callback with short API table");
        }
        else if (hasChatMessageProbe && mode == "no-chat-message-capability")
        {
            Require(g_ChatMessageRegisterCount == 0,
                "plugin registered chat message callback without capability");
            Require(g_ChatMessageUnregisterCount == 0,
                "plugin unregistered chat message callback without capability");
        }
        else if (hasChatMessageProbe)
        {
            Require(g_ChatMessageRegisterCount == 1,
                "plugin did not register one chat message callback");
            Require(g_ChatMessageUnregisterCount == 1,
                "plugin did not unregister one chat message callback");
            Require(g_RegisteredChatMessageCallback == nullptr,
                "chat message callback survived shutdown unregister");
            Require(g_RegisteredChatMessageUserData == nullptr,
                "chat message user data survived shutdown unregister");
        }
        if (hasTimerProbe && mode == "short-api-before-gameplay-policy")
        {
            Require(g_TimerRegisterCount == 0,
                "plugin registered timer callback with short API table");
            Require(g_TimerUnregisterCount == 0,
                "plugin unregistered timer callback with short API table");
        }
        else if (hasTimerProbe && mode == "no-timer-capability")
        {
            Require(g_TimerRegisterCount == 0,
                "plugin registered timer callback without capability");
            Require(g_TimerUnregisterCount == 0,
                "plugin unregistered timer callback without capability");
        }
        else if (hasTimerProbe && (mode == "active-timer" ||
            mode == "active-timer-double-shutdown" ||
            std::strcmp(expectedPluginId, "oProcessTimer") != 0))
        {
            Require(g_TimerRegisterCount == 1, "plugin did not register one timer callback");
            Require(g_TimerUnregisterCount == 1, "plugin did not unregister one timer callback");
            Require(g_RegisteredTimerCallback == nullptr, "timer callback survived shutdown unregister");
            Require(g_RegisteredTimerUserData == nullptr, "timer user data survived shutdown unregister");
        }
        else if (hasTimerProbe && std::strcmp(expectedPluginId, "oProcessTimer") == 0)
        {
            Require(g_TimerRegisterCount == 0, "disabled timer example registered a timer before shutdown");
            Require(g_TimerUnregisterCount == 0, "disabled timer example unregistered a timer on shutdown");
        }
        else if (std::strcmp(expectedPluginId, "oBaseEvents") == 0 && mode.empty())
        {
            Require(g_RegisterCount == 0, "disabled oBaseEvents unexpectedly registered a callback");
            Require(g_UnregisterCount == 0, "disabled oBaseEvents unexpectedly unregistered a callback");
        }
        cleanupConfigDir();
        closeHandle();
    }
    catch (const std::exception& e)
    {
        std::cerr << e.what() << '\n';
        return 1;
    }

    return 0;
}
