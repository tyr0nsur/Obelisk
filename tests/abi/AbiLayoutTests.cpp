#include <obelisk/ObeliskApi.h>

#include <cstddef>
#include <cstdint>
#include <type_traits>

#ifdef OBELISK_API_CAPABILITY_STRUCTURE_EVENTS
#error "Public structure API must stay gated until StructureEvents promotion requirements are complete."
#endif

namespace
{
    template <typename T>
    constexpr void AssertAbiType()
    {
        static_assert(std::is_standard_layout_v<T>);
        static_assert(std::is_trivial_v<T>);
        static_assert(std::is_trivially_copyable_v<T>);
    }

    void RuntimeNoOp()
    {
        volatile std::uint32_t apiVersion = OBELISK_API_ABI_VERSION;
        volatile std::uint32_t metadataVersion = OBELISK_PLUGIN_METADATA_ABI_VERSION;
        volatile std::uint32_t initContextVersion = OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION;
        volatile std::uint64_t ownedCallbacksCapability = OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS;
        volatile std::uint64_t globalCallbacksCapability = OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS;
        volatile std::uint64_t ownerTokenCallbacksCapability = OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS;
        volatile std::uint64_t callbackHandlesCapability = OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES;
        volatile std::uint64_t callProcessEventCapability = OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT;
        volatile std::uint64_t processEventBlockingCapability = OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING;
        volatile std::uint64_t gameplayPolicyEventsCapability = OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS;
        volatile std::uint64_t resourceKindDescriptorsCapability = OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS;
        volatile std::uint64_t gameplayPolicyEventDescriptorsCapability =
            OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS;
        volatile std::uint64_t chatEventsCapability = OBELISK_API_CAPABILITY_CHAT_EVENTS;
        volatile std::uint32_t gameplayPolicyEventVersion = OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION;
        volatile std::uint32_t resourceKindDescriptorVersion = OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION;
        volatile std::uint32_t gameplayPolicyEventDescriptorVersion =
            OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION;
        volatile std::uint32_t chatMessageEventVersion = OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION;
        volatile std::uint32_t gameplayPolicyEventKindMin = OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MIN;
        volatile std::uint32_t gameplayPolicyEventKindMax = OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MAX;
        volatile std::uint32_t gameplayPolicyEventKindCount = OBELISK_GAMEPLAY_POLICY_EVENT_KIND_COUNT;
        volatile std::uint64_t gameplayPolicyCopiedPayloadFlag = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD;
        volatile std::uint64_t gameplayPolicyStructureBackedFlag = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED;
        volatile std::uint64_t gameplayPolicyInventoryBackedFlag = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED;
        volatile std::uint64_t chatCopiedPayloadFlag = OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD;
        volatile std::uint64_t resourceKindCategoryOnlyFlag = OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY;
        volatile std::uint64_t resourceKindNoIdentityFlag = OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY;
        volatile std::uint64_t resourceKindNoLookupFlag = OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP;
        volatile std::uint64_t gameplayPolicyAllStructuresMask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES;
        volatile std::uint64_t gameplayPolicyAllInventoryMask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY;
        volatile std::uint64_t gameplayPolicyAllMask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL;
        volatile std::uint64_t gameplayPolicyReturnValueMask = OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE;

        (void)apiVersion;
        (void)metadataVersion;
        (void)initContextVersion;
        (void)ownedCallbacksCapability;
        (void)globalCallbacksCapability;
        (void)ownerTokenCallbacksCapability;
        (void)callbackHandlesCapability;
        (void)callProcessEventCapability;
        (void)processEventBlockingCapability;
        (void)gameplayPolicyEventsCapability;
        (void)resourceKindDescriptorsCapability;
        (void)gameplayPolicyEventDescriptorsCapability;
        (void)chatEventsCapability;
        (void)gameplayPolicyEventVersion;
        (void)resourceKindDescriptorVersion;
        (void)gameplayPolicyEventDescriptorVersion;
        (void)chatMessageEventVersion;
        (void)gameplayPolicyEventKindMin;
        (void)gameplayPolicyEventKindMax;
        (void)gameplayPolicyEventKindCount;
        (void)gameplayPolicyCopiedPayloadFlag;
        (void)gameplayPolicyStructureBackedFlag;
        (void)gameplayPolicyInventoryBackedFlag;
        (void)chatCopiedPayloadFlag;
        (void)resourceKindCategoryOnlyFlag;
        (void)resourceKindNoIdentityFlag;
        (void)resourceKindNoLookupFlag;
        (void)gameplayPolicyAllStructuresMask;
        (void)gameplayPolicyAllInventoryMask;
        (void)gameplayPolicyAllMask;
        (void)gameplayPolicyReturnValueMask;
    }
}

int main()
{
    static_assert(sizeof(void*) == 8, "Obelisk ABI layout tests target Linux x86_64");
    static_assert(OBELISK_API_ABI_VERSION == 1u);
    static_assert(OBELISK_PLUGIN_METADATA_ABI_VERSION == 1u);
    static_assert(OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION == 1u);
    static_assert(OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS == (1ull << 0));
    static_assert(OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS == (1ull << 1));
    static_assert(OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS == (1ull << 2));
    static_assert(OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES == (1ull << 3));
    static_assert(OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT == (1ull << 4));
    static_assert(OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING == (1ull << 5));
    static_assert(OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS == (1ull << 6));
    static_assert(OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS == (1ull << 7));
    static_assert(OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS == (1ull << 8));
    static_assert(OBELISK_API_CAPABILITY_CHAT_EVENTS == (1ull << 9));
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION == 1u);
    static_assert(OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION == 1u);
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION == 1u);
    static_assert(OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION == 1u);
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD == (1ull << 0));
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED == (1ull << 1));
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED == (1ull << 2));
    static_assert(OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD == (1ull << 0));
    static_assert(OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY == (1ull << 0));
    static_assert(OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY == (1ull << 1));
    static_assert(OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP == (1ull << 2));
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK == (1ull << 0));
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_DEMOLISH_CHECK == (1ull << 1));
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_VARIANT_CHANGE == (1ull << 2));
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACTIVATION_TOGGLE == (1ull << 3));
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_PIN_CODE_CHECK == (1ull << 4));
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_SEAT_CHECK == (1ull << 5));
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK == (1ull << 6));
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK == (1ull << 7));
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES == ((1ull << 6) - 1));
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY == ((1ull << 6) | (1ull << 7)));
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL == ((1ull << 8) - 1));
    static_assert(OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE == (1ull << 0));
    static_assert(OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX == (1ull << 1));
    static_assert(OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET == (1ull << 2));
    static_assert(OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE == (1ull << 3));
    static_assert(OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER == (1ull << 4));
    static_assert(OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN == (1ull << 5));

    static_assert(sizeof(ObeliskGameplayPolicyEventKind) == 4);
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MIN ==
        OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACCESS_CHECK);
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MAX ==
        OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK);
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_COUNT == 8);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_UNKNOWN) == 0);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACCESS_CHECK) == 1);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_DEMOLISH_CHECK) == 2);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE) == 3);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACTIVATION_TOGGLE) == 4);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_PIN_CODE_CHECK) == 5);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_SEAT_CHECK) == 6);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK) == 7);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK) == 8);

    static_assert(sizeof(ObeliskGameplayPolicyResourceKind) == 4);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_UNKNOWN) == 0);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE) == 1);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM) == 2);

    static_assert(sizeof(ObeliskGameplayPolicyField) == 4);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE) == 0);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_FIELD_VARIANT_INDEX) == 1);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_FIELD_FORCE_SET) == 2);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_FIELD_FORCE) == 3);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_FIELD_REQUESTED_BY_PLAYER) == 4);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_FIELD_IGNORE_COOLDOWN) == 5);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_FIELD_COUNT) == 6);

    static_assert(sizeof(ObeliskGameplayPolicyEventCallback) == sizeof(void*));
    static_assert(sizeof(ObeliskChatMessageEventCallback) == sizeof(void*));

    AssertAbiType<ObeliskStringView>();
    static_assert(alignof(ObeliskStringView) == 8);
    static_assert(sizeof(ObeliskStringView) == 16);
    static_assert(offsetof(ObeliskStringView, data) == 0);
    static_assert(offsetof(ObeliskStringView, size) == 8);

    static_assert(sizeof(ObeliskChatSendMode) == 4);
    static_assert(static_cast<std::uint32_t>(OBELISK_CHAT_SEND_MODE_GLOBAL) == 0);
    static_assert(static_cast<std::uint32_t>(OBELISK_CHAT_SEND_MODE_TRIBE) == 1);
    static_assert(static_cast<std::uint32_t>(OBELISK_CHAT_SEND_MODE_LOCAL) == 2);
    static_assert(static_cast<std::uint32_t>(OBELISK_CHAT_SEND_MODE_ALLIANCE) == 3);
    static_assert(OBELISK_CHAT_SEND_MODE_MIN == OBELISK_CHAT_SEND_MODE_GLOBAL);
    static_assert(OBELISK_CHAT_SEND_MODE_MAX == OBELISK_CHAT_SEND_MODE_ALLIANCE);
    static_assert(OBELISK_CHAT_SEND_MODE_COUNT == 4);

    AssertAbiType<ObeliskChatMessageEvent>();
    static_assert(alignof(ObeliskChatMessageEvent) == 8);
    static_assert(sizeof(ObeliskChatMessageEvent) == 48);
    static_assert(offsetof(ObeliskChatMessageEvent, abi_version) == 0);
    static_assert(offsetof(ObeliskChatMessageEvent, struct_size) == 4);
    static_assert(offsetof(ObeliskChatMessageEvent, send_mode) == 8);
    static_assert(offsetof(ObeliskChatMessageEvent, reserved0) == 12);
    static_assert(offsetof(ObeliskChatMessageEvent, flags) == 16);
    static_assert(offsetof(ObeliskChatMessageEvent, sequence) == 24);
    static_assert(offsetof(ObeliskChatMessageEvent, message) == 32);

    AssertAbiType<ObeliskGameplayPolicyEvent>();
    static_assert(alignof(ObeliskGameplayPolicyEvent) == 8);
    static_assert(sizeof(ObeliskGameplayPolicyEvent) == 64);
    static_assert(offsetof(ObeliskGameplayPolicyEvent, abi_version) == 0);
    static_assert(offsetof(ObeliskGameplayPolicyEvent, struct_size) == 4);
    static_assert(offsetof(ObeliskGameplayPolicyEvent, event_kind) == 8);
    static_assert(offsetof(ObeliskGameplayPolicyEvent, resource_kind) == 12);
    static_assert(offsetof(ObeliskGameplayPolicyEvent, flags) == 16);
    static_assert(offsetof(ObeliskGameplayPolicyEvent, field_mask) == 24);
    static_assert(offsetof(ObeliskGameplayPolicyEvent, bool_values) == 32);
    static_assert(offsetof(ObeliskGameplayPolicyEvent, int32_values) == 40);

    AssertAbiType<ObeliskResourceKindDescriptor>();
    static_assert(alignof(ObeliskResourceKindDescriptor) == 8);
    static_assert(sizeof(ObeliskResourceKindDescriptor) == 136);
    static_assert(offsetof(ObeliskResourceKindDescriptor, abi_version) == 0);
    static_assert(offsetof(ObeliskResourceKindDescriptor, struct_size) == 4);
    static_assert(offsetof(ObeliskResourceKindDescriptor, resource_kind) == 8);
    static_assert(offsetof(ObeliskResourceKindDescriptor, reserved0) == 12);
    static_assert(offsetof(ObeliskResourceKindDescriptor, flags) == 16);
    static_assert(offsetof(ObeliskResourceKindDescriptor, supported_gameplay_policy_event_mask) == 24);
    static_assert(offsetof(ObeliskResourceKindDescriptor, supported_gameplay_policy_field_mask) == 32);
    static_assert(offsetof(ObeliskResourceKindDescriptor, stable_name) == 40);
    static_assert(offsetof(ObeliskResourceKindDescriptor, display_name) == 72);

    AssertAbiType<ObeliskGameplayPolicyEventDescriptor>();
    static_assert(alignof(ObeliskGameplayPolicyEventDescriptor) == 8);
    static_assert(sizeof(ObeliskGameplayPolicyEventDescriptor) == 152);
    static_assert(offsetof(ObeliskGameplayPolicyEventDescriptor, abi_version) == 0);
    static_assert(offsetof(ObeliskGameplayPolicyEventDescriptor, struct_size) == 4);
    static_assert(offsetof(ObeliskGameplayPolicyEventDescriptor, event_kind) == 8);
    static_assert(offsetof(ObeliskGameplayPolicyEventDescriptor, resource_kind) == 12);
    static_assert(offsetof(ObeliskGameplayPolicyEventDescriptor, flags) == 16);
    static_assert(offsetof(ObeliskGameplayPolicyEventDescriptor, event_kind_mask) == 24);
    static_assert(offsetof(ObeliskGameplayPolicyEventDescriptor, field_mask) == 32);
    static_assert(offsetof(ObeliskGameplayPolicyEventDescriptor, stable_name) == 40);
    static_assert(offsetof(ObeliskGameplayPolicyEventDescriptor, display_name) == 88);

    AssertAbiType<ObeliskPluginMetadata>();
    static_assert(alignof(ObeliskPluginMetadata) == 8);
    static_assert(sizeof(ObeliskPluginMetadata) == 48);
    static_assert(offsetof(ObeliskPluginMetadata, abi_version) == 0);
    static_assert(offsetof(ObeliskPluginMetadata, struct_size) == 4);
    static_assert(offsetof(ObeliskPluginMetadata, plugin_id) == 8);
    static_assert(offsetof(ObeliskPluginMetadata, name) == 16);
    static_assert(offsetof(ObeliskPluginMetadata, version) == 24);
    static_assert(offsetof(ObeliskPluginMetadata, config_file) == 32);
    static_assert(offsetof(ObeliskPluginMetadata, default_config_json) == 40);

    AssertAbiType<ObeliskPluginInitContext>();
    static_assert(alignof(ObeliskPluginInitContext) == 8);
    static_assert(sizeof(ObeliskPluginInitContext) == 40);
    static_assert(offsetof(ObeliskPluginInitContext, abi_version) == 0);
    static_assert(offsetof(ObeliskPluginInitContext, struct_size) == 4);
    static_assert(offsetof(ObeliskPluginInitContext, config_dir) == 8);
    static_assert(offsetof(ObeliskPluginInitContext, config_path) == 16);
    static_assert(offsetof(ObeliskPluginInitContext, instance_id) == 24);
    static_assert(offsetof(ObeliskPluginInitContext, plugin_owner_token) == 32);

    AssertAbiType<ObeliskApi>();
    static_assert(alignof(ObeliskApi) == 8);
    static_assert(sizeof(ObeliskApi) == 200);
    static_assert(offsetof(ObeliskApi, LogInfo) == 0);
    static_assert(offsetof(ObeliskApi, LogWarn) == 8);
    static_assert(offsetof(ObeliskApi, LogError) == 16);
    static_assert(offsetof(ObeliskApi, RegisterPreProcessEvent) == 24);
    static_assert(offsetof(ObeliskApi, RegisterPostProcessEvent) == 32);
    static_assert(offsetof(ObeliskApi, RegisterPreProcessEventForNameIndex) == 40);
    static_assert(offsetof(ObeliskApi, RegisterPostProcessEventForNameIndex) == 48);
    static_assert(offsetof(ObeliskApi, CallProcessEvent) == 56);
    static_assert(offsetof(ObeliskApi, abi_version) == 64);
    static_assert(offsetof(ObeliskApi, struct_size) == 68);
    static_assert(offsetof(ObeliskApi, capabilities) == 72);
    static_assert(offsetof(ObeliskApi, RegisterPreProcessEventWithOwnerToken) == 80);
    static_assert(offsetof(ObeliskApi, RegisterPostProcessEventWithOwnerToken) == 88);
    static_assert(offsetof(ObeliskApi, RegisterPreProcessEventForNameIndexWithOwnerToken) == 96);
    static_assert(offsetof(ObeliskApi, RegisterPostProcessEventForNameIndexWithOwnerToken) == 104);
    static_assert(offsetof(ObeliskApi, RegisterPreProcessEventWithOwnerTokenHandle) == 112);
    static_assert(offsetof(ObeliskApi, RegisterPostProcessEventWithOwnerTokenHandle) == 120);
    static_assert(offsetof(ObeliskApi, RegisterPreProcessEventForNameIndexWithOwnerTokenHandle) == 128);
    static_assert(offsetof(ObeliskApi, RegisterPostProcessEventForNameIndexWithOwnerTokenHandle) == 136);
    static_assert(offsetof(ObeliskApi, UnregisterProcessEventCallbackWithOwnerToken) == 144);
    static_assert(offsetof(ObeliskApi, RegisterGameplayPolicyEventWithOwnerTokenHandle) == 152);
    static_assert(offsetof(ObeliskApi, UnregisterGameplayPolicyEventWithOwnerToken) == 160);
    static_assert(offsetof(ObeliskApi, DescribeResourceKind) == 168);
    static_assert(offsetof(ObeliskApi, DescribeGameplayPolicyEventKind) == 176);
    static_assert(offsetof(ObeliskApi, RegisterChatMessageEventWithOwnerTokenHandle) == 184);
    static_assert(offsetof(ObeliskApi, UnregisterChatMessageEventWithOwnerToken) == 192);

    static_assert(offsetof(ObeliskApi, abi_version) > offsetof(ObeliskApi, CallProcessEvent));
    static_assert(offsetof(ObeliskApi, struct_size) > offsetof(ObeliskApi, abi_version));
    static_assert(offsetof(ObeliskApi, capabilities) > offsetof(ObeliskApi, struct_size));
    static_assert(offsetof(ObeliskApi, RegisterPreProcessEventWithOwnerToken) > offsetof(ObeliskApi, capabilities));
    static_assert(offsetof(ObeliskApi, RegisterPostProcessEventWithOwnerToken) > offsetof(ObeliskApi, RegisterPreProcessEventWithOwnerToken));
    static_assert(offsetof(ObeliskApi, RegisterPreProcessEventForNameIndexWithOwnerToken) > offsetof(ObeliskApi, RegisterPostProcessEventWithOwnerToken));
    static_assert(offsetof(ObeliskApi, RegisterPostProcessEventForNameIndexWithOwnerToken) > offsetof(ObeliskApi, RegisterPreProcessEventForNameIndexWithOwnerToken));
    static_assert(offsetof(ObeliskApi, RegisterPreProcessEventWithOwnerTokenHandle) > offsetof(ObeliskApi, RegisterPostProcessEventForNameIndexWithOwnerToken));
    static_assert(offsetof(ObeliskApi, RegisterPostProcessEventWithOwnerTokenHandle) > offsetof(ObeliskApi, RegisterPreProcessEventWithOwnerTokenHandle));
    static_assert(offsetof(ObeliskApi, RegisterPreProcessEventForNameIndexWithOwnerTokenHandle) > offsetof(ObeliskApi, RegisterPostProcessEventWithOwnerTokenHandle));
    static_assert(offsetof(ObeliskApi, RegisterPostProcessEventForNameIndexWithOwnerTokenHandle) > offsetof(ObeliskApi, RegisterPreProcessEventForNameIndexWithOwnerTokenHandle));
    static_assert(offsetof(ObeliskApi, UnregisterProcessEventCallbackWithOwnerToken) > offsetof(ObeliskApi, RegisterPostProcessEventForNameIndexWithOwnerTokenHandle));
    static_assert(offsetof(ObeliskApi, RegisterGameplayPolicyEventWithOwnerTokenHandle) > offsetof(ObeliskApi, UnregisterProcessEventCallbackWithOwnerToken));
    static_assert(offsetof(ObeliskApi, UnregisterGameplayPolicyEventWithOwnerToken) > offsetof(ObeliskApi, RegisterGameplayPolicyEventWithOwnerTokenHandle));
    static_assert(offsetof(ObeliskApi, DescribeResourceKind) > offsetof(ObeliskApi, UnregisterGameplayPolicyEventWithOwnerToken));
    static_assert(offsetof(ObeliskApi, DescribeGameplayPolicyEventKind) > offsetof(ObeliskApi, DescribeResourceKind));
    static_assert(offsetof(ObeliskApi, RegisterChatMessageEventWithOwnerTokenHandle) > offsetof(ObeliskApi, DescribeGameplayPolicyEventKind));
    static_assert(offsetof(ObeliskApi, UnregisterChatMessageEventWithOwnerToken) > offsetof(ObeliskApi, RegisterChatMessageEventWithOwnerTokenHandle));
    static_assert(offsetof(ObeliskApi, UnregisterChatMessageEventWithOwnerToken) +
        sizeof(ObeliskApi::UnregisterChatMessageEventWithOwnerToken) == sizeof(ObeliskApi));

    RuntimeNoOp();
    return 0;
}
