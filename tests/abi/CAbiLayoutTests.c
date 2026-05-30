#include <obelisk/ObeliskApi.h>

#include <stddef.h>
#include <stdint.h>

#define ASSERT_SIZE(type, expected) _Static_assert(sizeof(type) == (expected), #type " size changed")
#define ASSERT_ALIGN(type, expected) _Static_assert(_Alignof(type) == (expected), #type " alignment changed")
#define ASSERT_OFFSET(type, field, expected) \
    _Static_assert(offsetof(type, field) == (expected), #type "." #field " offset changed")
#define ASSERT_U64(name, expected) _Static_assert((name) == (expected), #name " value changed")
#define ASSERT_ENUM(name, expected) _Static_assert((uint32_t)(name) == (expected), #name " value changed")

ASSERT_U64(OBELISK_API_ABI_VERSION, 1u);
ASSERT_U64(OBELISK_PLUGIN_METADATA_ABI_VERSION, 1u);
ASSERT_U64(OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION, 1u);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION, 1u);
ASSERT_U64(OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION, 1u);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION, 1u);
ASSERT_U64(OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION, 1u);
ASSERT_U64(sizeof(void*), 8);
ASSERT_U64(sizeof(size_t), 8);

ASSERT_U64(OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS, 1ull << 0);
ASSERT_U64(OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS, 1ull << 1);
ASSERT_U64(OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS, 1ull << 2);
ASSERT_U64(OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES, 1ull << 3);
ASSERT_U64(OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT, 1ull << 4);
ASSERT_U64(OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING, 1ull << 5);
ASSERT_U64(OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS, 1ull << 6);
ASSERT_U64(OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS, 1ull << 7);
ASSERT_U64(OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS, 1ull << 8);
ASSERT_U64(OBELISK_API_CAPABILITY_CHAT_EVENTS, 1ull << 9);
ASSERT_U64(OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS, 1ull << 10);

ASSERT_U64(OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD, 1ull << 0);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED, 1ull << 1);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED, 1ull << 2);
ASSERT_U64(OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD, 1ull << 0);
ASSERT_U64(OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY, 1ull << 0);
ASSERT_U64(OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY, 1ull << 1);
ASSERT_U64(OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP, 1ull << 2);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK, 1ull << 0);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_DEMOLISH_CHECK, 1ull << 1);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_VARIANT_CHANGE, 1ull << 2);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACTIVATION_TOGGLE, 1ull << 3);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_PIN_CODE_CHECK, 1ull << 4);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_SEAT_CHECK, 1ull << 5);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK, 1ull << 6);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK, 1ull << 7);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES, 0x3full);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY, 0xc0ull);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL, 0xffull);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE, 1ull << 0);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX, 1ull << 1);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET, 1ull << 2);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE, 1ull << 3);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER, 1ull << 4);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN, 1ull << 5);

ASSERT_SIZE(ObeliskStringView, 16);
ASSERT_ALIGN(ObeliskStringView, 8);
ASSERT_OFFSET(ObeliskStringView, data, 0);
ASSERT_OFFSET(ObeliskStringView, size, 8);

ASSERT_SIZE(ObeliskChatSendMode, 4);
ASSERT_ENUM(OBELISK_CHAT_SEND_MODE_GLOBAL, 0);
ASSERT_ENUM(OBELISK_CHAT_SEND_MODE_TRIBE, 1);
ASSERT_ENUM(OBELISK_CHAT_SEND_MODE_LOCAL, 2);
ASSERT_ENUM(OBELISK_CHAT_SEND_MODE_ALLIANCE, 3);
ASSERT_U64(OBELISK_CHAT_SEND_MODE_COUNT, 4u);

ASSERT_SIZE(ObeliskChatMessageEvent, 48);
ASSERT_ALIGN(ObeliskChatMessageEvent, 8);
ASSERT_OFFSET(ObeliskChatMessageEvent, abi_version, 0);
ASSERT_OFFSET(ObeliskChatMessageEvent, struct_size, 4);
ASSERT_OFFSET(ObeliskChatMessageEvent, send_mode, 8);
ASSERT_OFFSET(ObeliskChatMessageEvent, reserved0, 12);
ASSERT_OFFSET(ObeliskChatMessageEvent, flags, 16);
ASSERT_OFFSET(ObeliskChatMessageEvent, sequence, 24);
ASSERT_OFFSET(ObeliskChatMessageEvent, message, 32);

ASSERT_SIZE(ObeliskGameplayPolicyEventKind, 4);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_UNKNOWN, 0);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACCESS_CHECK, 1);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_DEMOLISH_CHECK, 2);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE, 3);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACTIVATION_TOGGLE, 4);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_PIN_CODE_CHECK, 5);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_SEAT_CHECK, 6);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK, 7);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK, 8);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MIN, 1);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MAX, 8);
ASSERT_U64(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_COUNT, 8u);

ASSERT_SIZE(ObeliskGameplayPolicyResourceKind, 4);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_UNKNOWN, 0);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE, 1);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM, 2);

ASSERT_SIZE(ObeliskGameplayPolicyField, 4);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE, 0);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_FIELD_VARIANT_INDEX, 1);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_FIELD_FORCE_SET, 2);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_FIELD_FORCE, 3);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_FIELD_REQUESTED_BY_PLAYER, 4);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_FIELD_IGNORE_COOLDOWN, 5);
ASSERT_ENUM(OBELISK_GAMEPLAY_POLICY_FIELD_COUNT, 6);

ASSERT_SIZE(ObeliskGameplayPolicyEvent, 64);
ASSERT_ALIGN(ObeliskGameplayPolicyEvent, 8);
ASSERT_OFFSET(ObeliskGameplayPolicyEvent, abi_version, 0);
ASSERT_OFFSET(ObeliskGameplayPolicyEvent, struct_size, 4);
ASSERT_OFFSET(ObeliskGameplayPolicyEvent, event_kind, 8);
ASSERT_OFFSET(ObeliskGameplayPolicyEvent, resource_kind, 12);
ASSERT_OFFSET(ObeliskGameplayPolicyEvent, flags, 16);
ASSERT_OFFSET(ObeliskGameplayPolicyEvent, field_mask, 24);
ASSERT_OFFSET(ObeliskGameplayPolicyEvent, bool_values, 32);
ASSERT_OFFSET(ObeliskGameplayPolicyEvent, int32_values, 40);

ASSERT_SIZE(ObeliskResourceKindDescriptor, 136);
ASSERT_ALIGN(ObeliskResourceKindDescriptor, 8);
ASSERT_OFFSET(ObeliskResourceKindDescriptor, abi_version, 0);
ASSERT_OFFSET(ObeliskResourceKindDescriptor, struct_size, 4);
ASSERT_OFFSET(ObeliskResourceKindDescriptor, resource_kind, 8);
ASSERT_OFFSET(ObeliskResourceKindDescriptor, reserved0, 12);
ASSERT_OFFSET(ObeliskResourceKindDescriptor, flags, 16);
ASSERT_OFFSET(ObeliskResourceKindDescriptor, supported_gameplay_policy_event_mask, 24);
ASSERT_OFFSET(ObeliskResourceKindDescriptor, supported_gameplay_policy_field_mask, 32);
ASSERT_OFFSET(ObeliskResourceKindDescriptor, stable_name, 40);
ASSERT_OFFSET(ObeliskResourceKindDescriptor, display_name, 72);

ASSERT_SIZE(ObeliskGameplayPolicyEventDescriptor, 152);
ASSERT_ALIGN(ObeliskGameplayPolicyEventDescriptor, 8);
ASSERT_OFFSET(ObeliskGameplayPolicyEventDescriptor, abi_version, 0);
ASSERT_OFFSET(ObeliskGameplayPolicyEventDescriptor, struct_size, 4);
ASSERT_OFFSET(ObeliskGameplayPolicyEventDescriptor, event_kind, 8);
ASSERT_OFFSET(ObeliskGameplayPolicyEventDescriptor, resource_kind, 12);
ASSERT_OFFSET(ObeliskGameplayPolicyEventDescriptor, flags, 16);
ASSERT_OFFSET(ObeliskGameplayPolicyEventDescriptor, event_kind_mask, 24);
ASSERT_OFFSET(ObeliskGameplayPolicyEventDescriptor, field_mask, 32);
ASSERT_OFFSET(ObeliskGameplayPolicyEventDescriptor, stable_name, 40);
ASSERT_OFFSET(ObeliskGameplayPolicyEventDescriptor, display_name, 88);

ASSERT_SIZE(ObeliskPluginMetadata, 48);
ASSERT_ALIGN(ObeliskPluginMetadata, 8);
ASSERT_OFFSET(ObeliskPluginMetadata, abi_version, 0);
ASSERT_OFFSET(ObeliskPluginMetadata, struct_size, 4);
ASSERT_OFFSET(ObeliskPluginMetadata, plugin_id, 8);
ASSERT_OFFSET(ObeliskPluginMetadata, name, 16);
ASSERT_OFFSET(ObeliskPluginMetadata, version, 24);
ASSERT_OFFSET(ObeliskPluginMetadata, config_file, 32);
ASSERT_OFFSET(ObeliskPluginMetadata, default_config_json, 40);

ASSERT_SIZE(ObeliskPluginInitContext, 40);
ASSERT_ALIGN(ObeliskPluginInitContext, 8);
ASSERT_OFFSET(ObeliskPluginInitContext, abi_version, 0);
ASSERT_OFFSET(ObeliskPluginInitContext, struct_size, 4);
ASSERT_OFFSET(ObeliskPluginInitContext, config_dir, 8);
ASSERT_OFFSET(ObeliskPluginInitContext, config_path, 16);
ASSERT_OFFSET(ObeliskPluginInitContext, instance_id, 24);
ASSERT_OFFSET(ObeliskPluginInitContext, plugin_owner_token, 32);

ASSERT_SIZE(OnProcessEventCallback, sizeof(void*));
ASSERT_SIZE(ObeliskGameplayPolicyEventCallback, sizeof(void*));
ASSERT_SIZE(ObeliskChatMessageEventCallback, sizeof(void*));

ASSERT_SIZE(ObeliskApi, 200);
ASSERT_ALIGN(ObeliskApi, 8);
ASSERT_OFFSET(ObeliskApi, LogInfo, 0);
ASSERT_OFFSET(ObeliskApi, LogWarn, 8);
ASSERT_OFFSET(ObeliskApi, LogError, 16);
ASSERT_OFFSET(ObeliskApi, RegisterPreProcessEvent, 24);
ASSERT_OFFSET(ObeliskApi, RegisterPostProcessEvent, 32);
ASSERT_OFFSET(ObeliskApi, RegisterPreProcessEventForNameIndex, 40);
ASSERT_OFFSET(ObeliskApi, RegisterPostProcessEventForNameIndex, 48);
ASSERT_OFFSET(ObeliskApi, CallProcessEvent, 56);
ASSERT_OFFSET(ObeliskApi, abi_version, 64);
ASSERT_OFFSET(ObeliskApi, struct_size, 68);
ASSERT_OFFSET(ObeliskApi, capabilities, 72);
ASSERT_OFFSET(ObeliskApi, RegisterPreProcessEventWithOwnerToken, 80);
ASSERT_OFFSET(ObeliskApi, RegisterPostProcessEventWithOwnerToken, 88);
ASSERT_OFFSET(ObeliskApi, RegisterPreProcessEventForNameIndexWithOwnerToken, 96);
ASSERT_OFFSET(ObeliskApi, RegisterPostProcessEventForNameIndexWithOwnerToken, 104);
ASSERT_OFFSET(ObeliskApi, RegisterPreProcessEventWithOwnerTokenHandle, 112);
ASSERT_OFFSET(ObeliskApi, RegisterPostProcessEventWithOwnerTokenHandle, 120);
ASSERT_OFFSET(ObeliskApi, RegisterPreProcessEventForNameIndexWithOwnerTokenHandle, 128);
ASSERT_OFFSET(ObeliskApi, RegisterPostProcessEventForNameIndexWithOwnerTokenHandle, 136);
ASSERT_OFFSET(ObeliskApi, UnregisterProcessEventCallbackWithOwnerToken, 144);
ASSERT_OFFSET(ObeliskApi, RegisterGameplayPolicyEventWithOwnerTokenHandle, 152);
ASSERT_OFFSET(ObeliskApi, UnregisterGameplayPolicyEventWithOwnerToken, 160);
ASSERT_OFFSET(ObeliskApi, DescribeResourceKind, 168);
ASSERT_OFFSET(ObeliskApi, DescribeGameplayPolicyEventKind, 176);
ASSERT_OFFSET(ObeliskApi, RegisterChatMessageEventWithOwnerTokenHandle, 184);
ASSERT_OFFSET(ObeliskApi, UnregisterChatMessageEventWithOwnerToken, 192);

int main(void)
{
    return 0;
}
