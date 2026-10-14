#include <obelisk/ObeliskApi.h>

#include <cstddef>
#include <cstdint>
#include <type_traits>

#ifdef OBELISK_API_CAPABILITY_STRUCTURE_EVENTS
#error "Public structure API must stay gated until StructureEvents promotion requirements are complete."
#endif

#if defined(OBELISK_API_CAPABILITY_IDENTITY) || defined(OBELISK_API_CAPABILITY_IDENTITIES) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL) || defined(OBELISK_API_CAPABILITY_PRINCIPALS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_IDENTITY) || defined(OBELISK_API_CAPABILITY_PLAYER_IDENTITIES) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL) || defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPALS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_LIFECYCLE) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_LIFECYCLE_EVENTS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_IDENTITY_LIFECYCLE) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_LOOKUP) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_LOOKUP) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_RESOLVE) || defined(OBELISK_API_CAPABILITY_PLAYER_RESOLVER) || \
    defined(OBELISK_API_CAPABILITY_IDENTITY_LOOKUP) || defined(OBELISK_API_CAPABILITY_IDENTITY_RESOLVE) || \
    defined(OBELISK_API_CAPABILITY_IDENTITY_RESOLVER) || defined(OBELISK_API_CAPABILITY_PRINCIPAL_LOOKUP) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL_RESOLVE) || defined(OBELISK_API_CAPABILITY_PRINCIPAL_RESOLVER) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_RESOLVE) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_RESOLVER) || \
    defined(OBELISK_API_CAPABILITY_IDENTITY_OWNER_TOKEN) || \
    defined(OBELISK_API_CAPABILITY_OWNER_TOKEN_IDENTITY) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_IDENTITY_OWNER_TOKEN) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_OWNER_TOKEN) || \
    defined(OBELISK_API_CAPABILITY_IDENTITY_OWNER_CALLBACKS) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL_OWNER_CALLBACKS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_IDENTITY_OWNER_CALLBACKS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_OWNER_CALLBACKS) || \
    defined(OBELISK_API_CAPABILITY_IDENTITY_OWNER_TOKEN_CALLBACKS) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL_OWNER_TOKEN_CALLBACKS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_IDENTITY_OWNER_TOKEN_CALLBACKS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_OWNER_TOKEN_CALLBACKS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_HANDLE) || defined(OBELISK_API_CAPABILITY_PLAYER_ID) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL_HANDLE) || defined(OBELISK_API_CAPABILITY_PRINCIPAL_ID) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_HANDLE) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_ID) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_DATA_ID) || defined(OBELISK_API_CAPABILITY_ACCOUNT_ID) || \
    defined(OBELISK_API_CAPABILITY_PLATFORM_ID) || defined(OBELISK_API_CAPABILITY_NETWORK_ID) || \
    defined(OBELISK_API_CAPABILITY_IDENTITY_STORAGE) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL_STORAGE) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_IDENTITY_STORAGE) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_STORAGE) || \
    defined(OBELISK_API_CAPABILITY_IDENTITY_PERSISTENCE) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL_PERSISTENCE) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_IDENTITY_PERSISTENCE) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_PERSISTENCE) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_SESSION) || defined(OBELISK_API_CAPABILITY_PLAYER_LIFECYCLE) || \
    defined(OBELISK_API_CAPABILITY_IDENTITY_EVENTS) || defined(OBELISK_API_CAPABILITY_PRINCIPAL_EVENTS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_EVENTS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_IDENTITY_EVENTS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_EVENTS) || \
    defined(OBELISK_API_CAPABILITY_IDENTITY_CALLBACKS) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL_CALLBACKS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_CALLBACKS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_IDENTITY_CALLBACKS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_CALLBACKS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_CONNECT) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_DISCONNECT) || defined(OBELISK_API_CAPABILITY_PLAYER_LOGIN) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_LOGOUT) || defined(OBELISK_API_CAPABILITY_STEAM_ID) || \
    defined(OBELISK_API_CAPABILITY_STEAMID) || defined(OBELISK_API_CAPABILITY_EOS_ID) || \
    defined(OBELISK_API_CAPABILITY_UNIQUE_NET_ID) || defined(OBELISK_IDENTITY_ABI_VERSION) || \
    defined(OBELISK_PRINCIPAL_ABI_VERSION) || defined(OBELISK_PLAYER_IDENTITY_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_ABI_VERSION) || defined(OBELISK_PLAYER_IDENTITY_DESCRIPTOR_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_DESCRIPTOR_ABI_VERSION) || defined(OBELISK_PLAYER_PRINCIPAL_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_IDENTITY_EVENT_ABI_VERSION) || defined(OBELISK_IDENTITY_EVENT_ABI_VERSION) || \
    defined(OBELISK_PRINCIPAL_EVENT_ABI_VERSION) || defined(OBELISK_PLAYER_SESSION_ABI_VERSION) || \
    defined(OBELISK_PLAYER_LIFECYCLE_ABI_VERSION) || defined(OBELISK_PLAYER_CALLBACK_ABI_VERSION) || \
    defined(OBELISK_IDENTITY_CALLBACK_ABI_VERSION) || defined(OBELISK_PRINCIPAL_CALLBACK_ABI_VERSION) || \
    defined(OBELISK_PLAYER_IDENTITY_CALLBACK_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_CALLBACK_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_IDENTITY_LIFECYCLE_ABI_VERSION) || \
    defined(OBELISK_IDENTITY_OWNER_TOKEN_ABI_VERSION) || \
    defined(OBELISK_PLAYER_IDENTITY_OWNER_TOKEN_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_OWNER_TOKEN_ABI_VERSION) || \
    defined(OBELISK_IDENTITY_OWNER_CALLBACK_ABI_VERSION) || \
    defined(OBELISK_PRINCIPAL_OWNER_CALLBACK_ABI_VERSION) || \
    defined(OBELISK_PLAYER_IDENTITY_OWNER_CALLBACK_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_OWNER_CALLBACK_ABI_VERSION) || \
    defined(OBELISK_IDENTITY_OWNER_TOKEN_CALLBACK_ABI_VERSION) || \
    defined(OBELISK_PRINCIPAL_OWNER_TOKEN_CALLBACK_ABI_VERSION) || \
    defined(OBELISK_PLAYER_IDENTITY_OWNER_TOKEN_CALLBACK_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_OWNER_TOKEN_CALLBACK_ABI_VERSION) || \
    defined(OBELISK_PLAYER_IDENTITY_OWNER_TOKEN_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_OWNER_TOKEN_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_IDENTITY_OWNER_TOKEN_HANDLE_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_OWNER_TOKEN_HANDLE_ABI_VERSION) || \
    defined(OBELISK_PLAYER_EVENT_ABI_VERSION) || defined(OBELISK_PLAYER_CONNECT_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_DISCONNECT_EVENT_ABI_VERSION) || defined(OBELISK_PLAYER_JOIN_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_LEAVE_EVENT_ABI_VERSION) || defined(OBELISK_PRINCIPAL_HANDLE_ABI_VERSION) || \
    defined(OBELISK_IDENTITY_HANDLE_ABI_VERSION) || defined(OBELISK_STEAM_ID_ABI_VERSION) || \
    defined(OBELISK_EOS_ID_ABI_VERSION) || defined(OBELISK_UNIQUE_NET_ID_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_LOOKUP_ABI_VERSION) || defined(OBELISK_PLAYER_RESOLVE_ABI_VERSION) || \
    defined(OBELISK_PLAYER_RESOLVER_ABI_VERSION) || defined(OBELISK_IDENTITY_RESOLVE_ABI_VERSION) || \
    defined(OBELISK_IDENTITY_RESOLVER_ABI_VERSION) || defined(OBELISK_PRINCIPAL_RESOLVE_ABI_VERSION) || \
    defined(OBELISK_PRINCIPAL_RESOLVER_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_RESOLVE_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_RESOLVER_ABI_VERSION) || defined(OBELISK_PLAYER_HANDLE_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_HANDLE_ABI_VERSION) || \
    defined(OBELISK_PLAYER_IDENTITY_HANDLE_ABI_VERSION) || defined(OBELISK_PRINCIPAL_ID_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_ID_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_STARTED_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_ENDED_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_START_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_END_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_ID_ABI_VERSION) || defined(OBELISK_PLAYER_DATA_ID_ABI_VERSION) || \
    defined(OBELISK_ACCOUNT_ID_ABI_VERSION) || defined(OBELISK_PLATFORM_ID_ABI_VERSION) || \
    defined(OBELISK_NETWORK_ID_ABI_VERSION) || defined(OBELISK_IDENTITY_STORAGE_ABI_VERSION) || \
    defined(OBELISK_PRINCIPAL_STORAGE_ABI_VERSION) || defined(OBELISK_PLAYER_IDENTITY_STORAGE_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_STORAGE_ABI_VERSION) || \
    defined(OBELISK_IDENTITY_PERSISTENCE_ABI_VERSION) || defined(OBELISK_PRINCIPAL_PERSISTENCE_ABI_VERSION) || \
    defined(OBELISK_PLAYER_IDENTITY_PERSISTENCE_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_PERSISTENCE_ABI_VERSION)
#error "Public player identity/principal ABI must stay gated until promotion evidence is accepted."
#endif

#if defined(OBELISK_API_CAPABILITY_OWNERSHIP) || defined(OBELISK_API_CAPABILITY_OWNER_LOOKUP) || \
    defined(OBELISK_API_CAPABILITY_OWNER_RESOLVE) || defined(OBELISK_API_CAPABILITY_OWNER_RESOLVER) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_OWNERSHIP) || defined(OBELISK_API_CAPABILITY_PRINCIPAL_OWNERSHIP) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_OWNERSHIP) || defined(OBELISK_API_CAPABILITY_RESOURCE_OWNER) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_OWNER) || defined(OBELISK_API_CAPABILITY_PRINCIPAL_OWNER) || \
    defined(OBELISK_API_CAPABILITY_TRIBE) || defined(OBELISK_API_CAPABILITY_TRIBE_ID) || \
    defined(OBELISK_API_CAPABILITY_TRIBE_LOOKUP) || defined(OBELISK_API_CAPABILITY_TRIBE_OWNERSHIP) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_TRIBE) || defined(OBELISK_OWNERSHIP_ABI_VERSION) || \
    defined(OBELISK_OWNER_LOOKUP_ABI_VERSION) || defined(OBELISK_OWNER_RESOLVE_ABI_VERSION) || \
    defined(OBELISK_OWNER_RESOLVER_ABI_VERSION) || \
    defined(OBELISK_PLAYER_OWNERSHIP_ABI_VERSION) || defined(OBELISK_PRINCIPAL_OWNERSHIP_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_OWNERSHIP_ABI_VERSION) || defined(OBELISK_RESOURCE_OWNER_ABI_VERSION) || \
    defined(OBELISK_PLAYER_OWNER_ABI_VERSION) || defined(OBELISK_PRINCIPAL_OWNER_ABI_VERSION) || \
    defined(OBELISK_TRIBE_ABI_VERSION) || defined(OBELISK_TRIBE_ID_ABI_VERSION) || \
    defined(OBELISK_TRIBE_LOOKUP_ABI_VERSION) || defined(OBELISK_TRIBE_OWNERSHIP_ABI_VERSION) || \
    defined(OBELISK_PLAYER_TRIBE_ABI_VERSION)
#error "Public ownership/tribe ABI must stay gated until identity and ownership promotion evidence is accepted."
#endif

#if defined(OBELISK_API_CAPABILITY_ADMIN) || defined(OBELISK_API_CAPABILITY_ADMIN_COMMANDS) || \
    defined(OBELISK_API_CAPABILITY_AUTHORIZATION) || defined(OBELISK_API_CAPABILITY_AUTH) || \
    defined(OBELISK_API_CAPABILITY_AUTHZ) || defined(OBELISK_API_CAPABILITY_ACCESS_CONTROL) || \
    defined(OBELISK_API_CAPABILITY_ACL) || defined(OBELISK_API_CAPABILITY_PERMISSION_CHECKS) || \
    defined(OBELISK_API_CAPABILITY_PERMISSION_QUERY) || defined(OBELISK_API_CAPABILITY_PERMISSIONS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PERMISSION) || defined(OBELISK_API_CAPABILITY_PRINCIPAL_PERMISSION) || \
    defined(OBELISK_API_CAPABILITY_PERMISSIONS_ADMIN) || defined(OBELISK_API_CAPABILITY_ROLES) || \
    defined(OBELISK_API_CAPABILITY_PRIVILEGES) || defined(OBELISK_API_CAPABILITY_MODERATION) || \
    defined(OBELISK_API_CAPABILITY_BAN) || defined(OBELISK_API_CAPABILITY_KICK) || \
    defined(OBELISK_ADMIN_ABI_VERSION) || defined(OBELISK_AUTH_ABI_VERSION) || defined(OBELISK_AUTHZ_ABI_VERSION) || \
    defined(OBELISK_ACCESS_CONTROL_ABI_VERSION) || defined(OBELISK_ACL_ABI_VERSION) || \
    defined(OBELISK_PERMISSION_QUERY_ABI_VERSION) || defined(OBELISK_PERMISSION_CACHE_ABI_VERSION) || \
    defined(OBELISK_PERMISSION_CHECKS_ABI_VERSION) || defined(OBELISK_PERMISSIONS_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PERMISSION_ABI_VERSION) || defined(OBELISK_PRINCIPAL_PERMISSION_ABI_VERSION) || \
    defined(OBELISK_PERMISSIONS_ADMIN_ABI_VERSION) || defined(OBELISK_AUTHORIZATION_ABI_VERSION) || \
    defined(OBELISK_ADMIN_ACTION_ABI_VERSION) || defined(OBELISK_ROLE_ABI_VERSION) || \
    defined(OBELISK_ROLES_ABI_VERSION) || defined(OBELISK_PRIVILEGE_ABI_VERSION) || \
    defined(OBELISK_PRIVILEGES_ABI_VERSION) || defined(OBELISK_MODERATION_ABI_VERSION) || \
    defined(OBELISK_BAN_ABI_VERSION) || defined(OBELISK_KICK_ABI_VERSION)
#error "Public permissions/admin ABI must stay gated until player identity and permissions promotion evidence is accepted."
#endif

#if defined(OBELISK_API_CAPABILITY_COMMANDS) || defined(OBELISK_API_CAPABILITY_CHAT_COMMANDS) || \
    defined(OBELISK_API_CAPABILITY_COMMAND_CHAT_RESPONSE_PATH) || \
    defined(OBELISK_API_CAPABILITY_COMMAND_RESPONSE) || defined(OBELISK_API_CAPABILITY_CHAT_RESPONSE) || \
    defined(OBELISK_API_CAPABILITY_CHAT_REPLY) || defined(OBELISK_API_CAPABILITY_CHAT_REPLIES) || \
    defined(OBELISK_API_CAPABILITY_COMMAND_REPLY) || \
    defined(OBELISK_API_CAPABILITY_COMMANDS_REPLIES) || \
    defined(OBELISK_API_CAPABILITY_COMMAND_ROUTER) || defined(OBELISK_API_CAPABILITY_SEND_CHAT) || \
    defined(OBELISK_API_CAPABILITY_BROADCAST) || defined(OBELISK_API_CAPABILITY_NOTICES) || \
    defined(OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT_RESPONSE) || \
    defined(OBELISK_COMMAND_ABI_VERSION) || defined(OBELISK_COMMANDS_ABI_VERSION) || \
    defined(OBELISK_CHAT_COMMAND_ABI_VERSION) || defined(OBELISK_CHAT_COMMANDS_ABI_VERSION) || \
    defined(OBELISK_COMMAND_CHAT_RESPONSE_ABI_VERSION) || defined(OBELISK_COMMAND_RESPONSE_ABI_VERSION) || \
    defined(OBELISK_CHAT_RESPONSE_ABI_VERSION) || defined(OBELISK_COMMAND_REPLY_ABI_VERSION) || \
    defined(OBELISK_CHAT_REPLY_ABI_VERSION) || defined(OBELISK_COMMANDS_REPLIES_ABI_VERSION) || \
    defined(OBELISK_COMMAND_ROUTER_ABI_VERSION)
#error "Public command response/reply ABI must stay gated until identity, permissions/admin, and response-path promotion evidence is accepted."
#endif

#if defined(OBELISK_API_CAPABILITY_PUBLIC_CALL_PROCESS_EVENT) || \
    defined(OBELISK_API_CAPABILITY_STABLE_CALL_PROCESS_EVENT) || \
    defined(OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT_PUBLIC) || \
    defined(OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT_STABLE) || \
    defined(OBELISK_API_CAPABILITY_PUBLIC_PROCESS_EVENT) || \
    defined(OBELISK_API_CAPABILITY_STABLE_PROCESS_EVENT) || \
    defined(OBELISK_API_CAPABILITY_RAW_PROCESS_EVENT_PUBLIC) || \
    defined(OBELISK_API_CAPABILITY_RAW_PROCESS_EVENT_STABLE) || \
    defined(OBELISK_CALL_PROCESS_EVENT_ABI_VERSION) || \
    defined(OBELISK_PUBLIC_CALL_PROCESS_EVENT_ABI_VERSION) || \
    defined(OBELISK_STABLE_CALL_PROCESS_EVENT_ABI_VERSION) || \
    defined(OBELISK_PROCESS_EVENT_PUBLIC_ABI_VERSION) || \
    defined(OBELISK_PROCESS_EVENT_STABLE_ABI_VERSION) || \
    defined(OBELISK_RAW_PROCESS_EVENT_ABI_VERSION) || \
    defined(OBELISK_RAW_PROCESS_EVENT_PUBLIC_ABI_VERSION)
#error "Public raw ProcessEvent/CallProcessEvent ABI must stay gated until promotion evidence is accepted."
#endif

#if defined(OBELISK_API_CAPABILITY_RESOURCE_HANDLE) || defined(OBELISK_API_CAPABILITY_RESOURCE_HANDLES) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_IDENTITY) || defined(OBELISK_API_CAPABILITY_RESOURCE_LOOKUP) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_RESOLVE) || defined(OBELISK_API_CAPABILITY_RESOURCE_RESOLVER) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_ID) || defined(OBELISK_API_CAPABILITY_RESOURCE_REF) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_REFERENCE) || defined(OBELISK_API_CAPABILITY_RESOURCE_TOKEN) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_MUTATION) || defined(OBELISK_API_CAPABILITY_MUTATION) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_MUTABLE) || defined(OBELISK_API_CAPABILITY_MUTABLE_RESOURCE) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_WRITE) || defined(OBELISK_API_CAPABILITY_WRITE_RESOURCE) || \
    defined(OBELISK_API_CAPABILITY_RETURN_OVERRIDE) || defined(OBELISK_API_CAPABILITY_RETURN_OVERRIDES) || \
    defined(OBELISK_API_CAPABILITY_OBJECT_HANDLE) || defined(OBELISK_API_CAPABILITY_OBJECT_IDENTITY) || \
    defined(OBELISK_API_CAPABILITY_OBJECT_LOOKUP) || \
    defined(OBELISK_RESOURCE_HANDLE_ABI_VERSION) || defined(OBELISK_RESOURCE_HANDLE_DESCRIPTOR_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_IDENTITY_ABI_VERSION) || defined(OBELISK_RESOURCE_LOOKUP_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_RESOLVE_ABI_VERSION) || defined(OBELISK_RESOURCE_RESOLVER_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_ID_ABI_VERSION) || defined(OBELISK_RESOURCE_REF_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_REFERENCE_ABI_VERSION) || defined(OBELISK_RESOURCE_TOKEN_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_MUTATION_ABI_VERSION) || defined(OBELISK_MUTATION_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_MUTABLE_ABI_VERSION) || defined(OBELISK_MUTABLE_RESOURCE_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_WRITE_ABI_VERSION) || defined(OBELISK_WRITE_RESOURCE_ABI_VERSION) || \
    defined(OBELISK_RETURN_OVERRIDE_ABI_VERSION) || defined(OBELISK_RETURN_OVERRIDES_ABI_VERSION) || \
    defined(OBELISK_OBJECT_HANDLE_ABI_VERSION) || defined(OBELISK_OBJECT_IDENTITY_ABI_VERSION) || \
    defined(OBELISK_OBJECT_LOOKUP_ABI_VERSION)
#error "Public ResourceHandle ABI must stay gated until ResourceHandle promotion requirements are complete."
#endif

#if defined(OBELISK_API_CAPABILITY_RUNTIME_READY) || defined(OBELISK_RUNTIME_READY) || \
    defined(OBELISK_IDENTITY_READY) || defined(OBELISK_IDENTITY_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_IDENTITY_P0_DEPENDENCY_READY) || \
    defined(OBELISK_PLAYER_IDENTITY_P0_DEPENDENCY_READY) || \
    defined(OBELISK_IDENTITY_DEPENDENCY_READY) || defined(OBELISK_PLAYER_IDENTITY_DEPENDENCY_READY) || \
    defined(OBELISK_PLAYER_IDENTITY_READY) || defined(OBELISK_PLAYER_PRINCIPAL_READY) || \
    defined(OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_READY) || \
    defined(OBELISK_PLAYER_IDENTITY_OWNER_TOKEN_READY) || \
    defined(OBELISK_PLAYER_PRINCIPAL_OWNER_TOKEN_READY) || \
    defined(OBELISK_IDENTITY_OWNER_TOKEN_READY) || defined(OBELISK_OWNER_TOKEN_IDENTITY_READY) || \
    defined(OBELISK_IDENTITY_OWNER_TOKEN_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_PLAYER_IDENTITY_OWNER_TOKEN_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_PLAYER_PRINCIPAL_OWNER_TOKEN_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_IDENTITY_CALLBACK_LIFETIME_READY) || \
    defined(OBELISK_PLAYER_IDENTITY_CALLBACK_LIFETIME_READY) || \
    defined(OBELISK_PLAYER_PRINCIPAL_CALLBACK_LIFETIME_READY) || \
    defined(OBELISK_PUBLIC_IDENTITY_CALLBACKS_READY) || \
    defined(OBELISK_PUBLIC_PLAYER_IDENTITY_CALLBACKS_READY) || \
    defined(OBELISK_PUBLIC_IDENTITY_ALLOWED) || defined(OBELISK_PUBLIC_IDENTITY_READY) || \
    defined(OBELISK_PUBLIC_PRINCIPAL_READY) || defined(OBELISK_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_PUBLIC_SDK_READY) || defined(OBELISK_STABLE_SDK_READY) || \
    defined(OBELISK_COMPLETE_SDK_READY) || defined(OBELISK_COMPLETE_SDK_V1_READY) || \
    defined(OBELISK_SDK_COMPLETE) || defined(OBELISK_SDK_V1_COMPLETE) || \
    defined(OBELISK_V1_SDK_COMPLETE) || \
    defined(OBELISK_PUBLIC_API_READY) || defined(OBELISK_PUBLIC_ABI_READY) || \
    defined(OBELISK_PUBLIC_HEADER_GATE_OPEN) || defined(OBELISK_PUBLIC_HEADER_GATE_PASSED) || \
    defined(OBELISK_PUBLIC_HEADER_GATE_READY) || \
    defined(OBELISK_HEADER_PROMOTION_GATE_OPEN) || defined(OBELISK_HEADER_PROMOTION_GATE_PASSED) || \
    defined(OBELISK_HEADER_PROMOTION_GATE_READY) || \
    defined(OBELISK_PUBLIC_HEADER_PROMOTION_GATE_OPEN) || \
    defined(OBELISK_PUBLIC_HEADER_PROMOTION_GATE_PASSED) || \
    defined(OBELISK_PUBLIC_HEADER_PROMOTION_GATE_READY) || \
    defined(OBELISK_APPROVED_RUNTIME_EVIDENCE_ACCEPTED) || \
    defined(OBELISK_APPROVED_RUNTIME_BUNDLE_ACCEPTED) || \
    defined(OBELISK_PUBLIC_CONTRACT_REVIEW_ACCEPTED) || \
    defined(OBELISK_IDENTITY_LOOKUP_READY) || defined(OBELISK_PUBLIC_LOOKUP_READY) || \
    defined(OBELISK_IDENTITY_STORAGE_READY) || defined(OBELISK_PUBLIC_IDENTITY_STORAGE_READY) || \
    defined(OBELISK_IDENTITY_PERSISTENCE_READY) || defined(OBELISK_PUBLIC_IDENTITY_PERSISTENCE_READY) || \
    defined(OBELISK_RESOURCE_READY) || defined(OBELISK_RESOURCE_HANDLE_READY) || \
    defined(OBELISK_RESOURCE_LOOKUP_READY) || defined(OBELISK_PUBLIC_RESOURCE_READY) || \
    defined(OBELISK_PUBLIC_RESOURCE_HANDLE_READY) || \
    defined(OBELISK_RESOURCE_HANDLE_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_RESOURCE_MUTATION_READY) || defined(OBELISK_MUTATION_READY) || \
    defined(OBELISK_RESOURCE_MUTABLE_READY) || defined(OBELISK_MUTABLE_RESOURCE_READY) || \
    defined(OBELISK_RESOURCE_WRITE_READY) || defined(OBELISK_RETURN_OVERRIDE_READY) || \
    defined(OBELISK_RETURN_OVERRIDES_READY) || \
    defined(OBELISK_PERMISSIONS_P0_DEPENDENCY_READY) || defined(OBELISK_COMMANDS_P0_DEPENDENCY_READY) || \
    defined(OBELISK_PERMISSIONS_DEPENDENCY_READY) || defined(OBELISK_COMMANDS_DEPENDENCY_READY) || \
    defined(OBELISK_IDENTITY_PERMISSION_COMMANDS_DEPENDENCIES_READY) || \
    defined(OBELISK_PERMISSIONS_ADMIN_READY) || defined(OBELISK_COMMANDS_READY) || \
    defined(OBELISK_COMMAND_REPLIES_READY) || defined(OBELISK_CHAT_REPLIES_READY) || \
    defined(OBELISK_POST_INIT_CALL_PROCESS_EVENT_SHORTCUT_READY) || \
    defined(OBELISK_CALL_PROCESS_EVENT_POST_INIT_READY) || defined(OBELISK_CALL_PROCESS_EVENT_SHORTCUT_READY) || \
    defined(OBELISK_PUBLIC_CALL_PROCESS_EVENT_READY) || defined(OBELISK_STABLE_CALL_PROCESS_EVENT_READY) || \
    defined(OBELISK_CALL_PROCESS_EVENT_PUBLIC_READY) || defined(OBELISK_CALL_PROCESS_EVENT_STABLE_READY) || \
    defined(OBELISK_RAW_PROCESS_EVENT_READY) || defined(OBELISK_RAW_PROCESS_EVENT_PUBLIC_READY) || \
    defined(OBELISK_PUBLIC_PROCESS_EVENT_READY) || defined(OBELISK_PROCESS_EVENT_PUBLIC_READY) || \
    defined(OBELISK_PROCESS_EVENT_PUBLIC_SDK_READY) || \
    defined(OBELISK_PROCESS_EVENT_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_RAW_PROCESS_EVENT_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_PROCESS_EVENT_STABLE_SDK_READY) || \
    defined(OBELISK_PROCESS_EVENT_CALLBACKS_PUBLIC_READY) || \
    defined(OBELISK_RAW_PROCESS_EVENT_CALLBACKS_READY) || \
    defined(OBELISK_SDK_P0_PROGRESS_READY) || defined(OBELISK_SDK_P0_PROGRESS_CLAIM_ALLOWED) || \
    defined(OBELISK_ABI_CANDIDATE_COUNTS_TOWARD_SDK_P0_PROGRESS) || \
    defined(OBELISK_RUNTIME_READINESS_CLAIM_ALLOWED) || \
    defined(OBELISK_V1_COMPLETION_CLAIM_ALLOWED) || \
    defined(OBELISK_PUBLIC_MODULE_SDK_COVERAGE_CLAIM_ALLOWED) || \
    defined(OBELISK_PRODUCTION_STABLE_SDK_CLAIM_ALLOWED)
#error "Public identity/readiness macros must stay gated until accepted runtime and contract evidence exist."
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
        volatile std::uint64_t filteredCallbacksCapability =
            OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS;
        volatile std::uint64_t timersCapability = OBELISK_API_CAPABILITY_TIMERS;
        volatile std::uint64_t repeatingTimerFlag = OBELISK_TIMER_FLAG_REPEATING;
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
        (void)filteredCallbacksCapability;
        (void)timersCapability;
        (void)repeatingTimerFlag;
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
    static_assert(OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS == (1ull << 10));
    static_assert(OBELISK_API_CAPABILITY_TIMERS == (1ull << 11));
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION == 1u);
    static_assert(OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION == 1u);
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION == 1u);
    static_assert(OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION == 1u);
    static_assert(OBELISK_TIMER_FLAG_REPEATING == (1ull << 0));
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
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_ALLOW_EQUIP_ITEM_CHECK == (1ull << 8));
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CAN_REPAIR_CHECK == (1ull << 9));
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK == (1ull << 10));
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES == ((1ull << 6) - 1));
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY ==
        ((1ull << 6) | (1ull << 7) | (1ull << 8) | (1ull << 9) | (1ull << 10)));
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL == ((1ull << 11) - 1));
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
        OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK);
    static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_COUNT == 11);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_UNKNOWN) == 0);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACCESS_CHECK) == 1);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_DEMOLISH_CHECK) == 2);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE) == 3);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACTIVATION_TOGGLE) == 4);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_PIN_CODE_CHECK) == 5);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_SEAT_CHECK) == 6);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK) == 7);
    static_assert(static_cast<std::uint32_t>(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK) == 8);
    static_assert(static_cast<std::uint32_t>(
        OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK) == 9);
    static_assert(static_cast<std::uint32_t>(
        OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK) == 10);
    static_assert(static_cast<std::uint32_t>(
        OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK) == 11);

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
    static_assert(sizeof(ObeliskTimerCallback) == sizeof(void*));

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
    static_assert(offsetof(ObeliskChatMessageEvent, message) +
        sizeof(ObeliskChatMessageEvent::message) == sizeof(ObeliskChatMessageEvent),
        "future chat event fields must be appended and struct_size-gated");

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
    static_assert(offsetof(ObeliskGameplayPolicyEvent, int32_values) +
        sizeof(ObeliskGameplayPolicyEvent::int32_values) == sizeof(ObeliskGameplayPolicyEvent),
        "future gameplay policy event fields must be appended and struct_size-gated");

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
    static_assert(offsetof(ObeliskResourceKindDescriptor, display_name) +
        sizeof(ObeliskResourceKindDescriptor::display_name) == sizeof(ObeliskResourceKindDescriptor),
        "future resource descriptor fields must be appended and struct_size-gated");

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
    static_assert(offsetof(ObeliskGameplayPolicyEventDescriptor, display_name) +
        sizeof(ObeliskGameplayPolicyEventDescriptor::display_name) ==
        sizeof(ObeliskGameplayPolicyEventDescriptor),
        "future gameplay policy descriptor fields must be appended and struct_size-gated");

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
    static_assert(offsetof(ObeliskPluginInitContext, plugin_owner_token) >
        offsetof(ObeliskPluginInitContext, instance_id));
    static_assert(offsetof(ObeliskPluginInitContext, plugin_owner_token) +
        sizeof(ObeliskPluginInitContext::plugin_owner_token) == sizeof(ObeliskPluginInitContext));

    AssertAbiType<ObeliskApi>();
    static_assert(alignof(ObeliskApi) == 8);
    static_assert(sizeof(ObeliskApi) == 312);
    static_assert(offsetof(ObeliskApi, LogInfo) == 0);
    static_assert(offsetof(ObeliskApi, LogWarn) == 8);
    static_assert(offsetof(ObeliskApi, LogError) == 16);
    static_assert(offsetof(ObeliskApi, RegisterPreProcessEvent) == 24);
    static_assert(offsetof(ObeliskApi, RegisterPostProcessEvent) == 32);
    static_assert(offsetof(ObeliskApi, RegisterPreProcessEventForNameIndex) == 40);
    static_assert(offsetof(ObeliskApi, RegisterPostProcessEventForNameIndex) == 48);
    static_assert(offsetof(ObeliskApi, CallProcessEvent) == 56);
    static_assert(offsetof(ObeliskApi, abi_version) == 64);
    static_assert(offsetof(ObeliskApi, CallProcessEvent) +
        sizeof(ObeliskApi::CallProcessEvent) == offsetof(ObeliskApi, abi_version),
        "legacy raw ProcessEvent slots must end before appended struct_size metadata");
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
    static_assert(offsetof(ObeliskApi, RegisterTimerWithOwnerTokenHandle) == 200);
    static_assert(offsetof(ObeliskApi, UnregisterTimerWithOwnerToken) == 208);

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
    static_assert(offsetof(ObeliskApi, RegisterTimerWithOwnerTokenHandle) > offsetof(ObeliskApi, UnregisterChatMessageEventWithOwnerToken));
    static_assert(offsetof(ObeliskApi, UnregisterTimerWithOwnerToken) > offsetof(ObeliskApi, RegisterTimerWithOwnerTokenHandle));
    static_assert(offsetof(ObeliskApi, UnregisterTimerWithOwnerToken) +
        sizeof(ObeliskApi::UnregisterTimerWithOwnerToken) == 216);
    static_assert(offsetof(ObeliskApi, RegisterCommandWithOwnerTokenHandle) == 216);
    static_assert(offsetof(ObeliskApi, UnregisterCommandWithOwnerToken) == 224);
    static_assert(offsetof(ObeliskApi, ReplyToCommandWithOwnerToken) == 232);
    static_assert(offsetof(ObeliskApi, ReplyToCommandWithOwnerToken) +
        sizeof(ObeliskApi::ReplyToCommandWithOwnerToken) == 240);
    static_assert(offsetof(ObeliskApi, GetCommandPlayerWithOwnerToken) == 240);
    static_assert(offsetof(ObeliskApi, RegisterPlayerLifecycleWithOwnerTokenHandle) == 248);
    static_assert(offsetof(ObeliskApi, UnregisterPlayerLifecycleWithOwnerToken) == 256);
    static_assert(offsetof(ObeliskApi, UnregisterPlayerLifecycleWithOwnerToken) +
        sizeof(ObeliskApi::UnregisterPlayerLifecycleWithOwnerToken) == 264);
    static_assert(offsetof(ObeliskApi, RegisterCommandWithOptionsWithOwnerTokenHandle) == 264);
    static_assert(offsetof(ObeliskApi, RegisterCommandWithOptionsWithOwnerTokenHandle) +
        sizeof(ObeliskApi::RegisterCommandWithOptionsWithOwnerTokenHandle) == 272);
    static_assert(std::is_same_v<decltype(ObeliskApi::RegisterCommandWithOptionsWithOwnerTokenHandle),
        uint64_t (*)(uint64_t, const char*, uint64_t, ObeliskCommandCallback, void*)>);
    // Append-only scoped native destinations and copied world observations.
    static_assert(offsetof(ObeliskApi, GetCommandChatSessionWithOwnerToken) == 272);
    static_assert(offsetof(ObeliskApi, ListChatSessionsWithOwnerToken) == 280);
    static_assert(offsetof(ObeliskApi, SendChatToSessionWithOwnerToken) == 288);
    static_assert(offsetof(ObeliskApi, GetCommandWorldInfoWithOwnerToken) == 296);
    static_assert(offsetof(ObeliskApi, GetCommandWorldInfoWithOwnerToken) +
        sizeof(ObeliskApi::GetCommandWorldInfoWithOwnerToken) == 304);
    static_assert(offsetof(ObeliskApi, TeleportCommandOriginWithOwnerToken) == 304);
    static_assert(offsetof(ObeliskApi, TeleportCommandOriginWithOwnerToken) +
        sizeof(ObeliskApi::TeleportCommandOriginWithOwnerToken) == sizeof(ObeliskApi));
    static_assert(OBELISK_API_CAPABILITY_COMMAND_SELF_TELEPORT == (1ull << 18));
    static_assert(std::is_same_v<decltype(ObeliskApi::TeleportCommandOriginWithOwnerToken),
        bool (*)(uint64_t, uint64_t, const ObeliskCommandWorldInfo*)>);
    static_assert(OBELISK_API_CAPABILITY_CHAT_SESSIONS == (1ull << 16));
    static_assert(OBELISK_API_CAPABILITY_COMMAND_WORLD_INFO_NATIVE == (1ull << 17));
    static_assert(OBELISK_CHAT_SESSION_ABI_VERSION == 1u);
    static_assert(OBELISK_COMMAND_WORLD_INFO_ABI_VERSION == 1u);
    static_assert(OBELISK_CHAT_SESSION_NAME_MAX_BYTES == 256u);
    static_assert(OBELISK_CHAT_SESSION_LIST_MAX == 64u);
    static_assert(OBELISK_CHAT_SESSION_FLAG_NAME_AVAILABLE == 1ull);
    static_assert(OBELISK_COMMAND_WORLD_FLAG_POSITION_AVAILABLE == 1ull);
    static_assert(OBELISK_COMMAND_WORLD_FLAG_TRIBE_ID_AVAILABLE == 2ull);
    static_assert(OBELISK_COMMAND_WORLD_FLAG_ROTATION_AVAILABLE == 4ull);
    static_assert(OBELISK_COMMAND_WORLD_FLAG_MOUNTED_DINO_IDS_AVAILABLE == 8ull);
    static_assert(OBELISK_COMMAND_WORLD_FLAG_TARGET_STRUCTURE_ID_AVAILABLE == 16ull);
    AssertAbiType<ObeliskChatSession>();
    static_assert(sizeof(ObeliskChatSession) == 304);
    static_assert(alignof(ObeliskChatSession) == 8);
    static_assert(offsetof(ObeliskChatSession, abi_version) == 0);
    static_assert(offsetof(ObeliskChatSession, struct_size) == 4);
    static_assert(offsetof(ObeliskChatSession, session_token) == 8);
    static_assert(offsetof(ObeliskChatSession, process_epoch) == 16);
    static_assert(offsetof(ObeliskChatSession, flags) == 24);
    static_assert(offsetof(ObeliskChatSession, player_name) == 32);
    static_assert(offsetof(ObeliskChatSession, player_name_size) == 292);
    static_assert(offsetof(ObeliskChatSession, reserved0) == 296);
    AssertAbiType<ObeliskCommandWorldInfo>();
    static_assert(sizeof(ObeliskCommandWorldInfo) == 80);
    static_assert(alignof(ObeliskCommandWorldInfo) == 8);
    static_assert(offsetof(ObeliskCommandWorldInfo, abi_version) == 0);
    static_assert(offsetof(ObeliskCommandWorldInfo, struct_size) == 4);
    static_assert(offsetof(ObeliskCommandWorldInfo, flags) == 8);
    static_assert(offsetof(ObeliskCommandWorldInfo, x) == 16);
    static_assert(offsetof(ObeliskCommandWorldInfo, y) == 20);
    static_assert(offsetof(ObeliskCommandWorldInfo, z) == 24);
    static_assert(offsetof(ObeliskCommandWorldInfo, native_tribe_id) == 28);
    static_assert(offsetof(ObeliskCommandWorldInfo, pitch) == 32);
    static_assert(offsetof(ObeliskCommandWorldInfo, yaw) == 36);
    static_assert(offsetof(ObeliskCommandWorldInfo, roll) == 40);
    static_assert(offsetof(ObeliskCommandWorldInfo, reserved0) == 44);
    static_assert(offsetof(ObeliskCommandWorldInfo, process_epoch) == 48);
    static_assert(offsetof(ObeliskCommandWorldInfo, session_token) == 56);
    static_assert(offsetof(ObeliskCommandWorldInfo, mounted_dino_id1) == 64);
    static_assert(offsetof(ObeliskCommandWorldInfo, mounted_dino_id2) == 68);
    static_assert(offsetof(ObeliskCommandWorldInfo, target_structure_id) == 72);
    static_assert(offsetof(ObeliskCommandWorldInfo, reserved1) == 76);
    static_assert(sizeof(ObeliskChatSession::player_name) == 257);
    static_assert(std::is_same_v<decltype(ObeliskApi::GetCommandChatSessionWithOwnerToken), bool (*)(uint64_t, uint64_t, ObeliskChatSession*)>);
    static_assert(std::is_same_v<decltype(ObeliskApi::ListChatSessionsWithOwnerToken), bool (*)(uint64_t, uint64_t, ObeliskChatSession*, size_t, size_t*, size_t*)>);
    static_assert(std::is_same_v<decltype(ObeliskApi::SendChatToSessionWithOwnerToken), bool (*)(uint64_t, uint64_t, uint64_t, uint64_t, ObeliskCommandStringView)>);
    static_assert(std::is_same_v<decltype(ObeliskApi::GetCommandWorldInfoWithOwnerToken), bool (*)(uint64_t, uint64_t, ObeliskCommandWorldInfo*)>);

    static_assert(OBELISK_API_CAPABILITY_COMMAND_MATCH_OPTIONS == (1ull << 15));
    static_assert(OBELISK_COMMAND_MATCH_FLAG_VERB == 1ull);
    static_assert(OBELISK_COMMAND_MATCH_FLAG_ASCII_CASE_INSENSITIVE == 2ull);
    static_assert(sizeof(ObeliskPlayerLifecycleEvent) == 72);
    static_assert(offsetof(ObeliskPlayerLifecycleEvent, kind) == 8);
    static_assert(offsetof(ObeliskPlayerLifecycleEvent, flags) == 16);
    static_assert(offsetof(ObeliskPlayerLifecycleEvent, sequence) == 24);
    static_assert(offsetof(ObeliskPlayerLifecycleEvent, process_epoch) == 32);
    static_assert(offsetof(ObeliskPlayerLifecycleEvent, player_name) == 40);
    static_assert(offsetof(ObeliskPlayerLifecycleEvent, platform_id) == 56);
    AssertAbiType<ObeliskPlayerLifecycleEvent>();
    static_assert(OBELISK_API_CAPABILITY_PLAYER_LIFECYCLE_EVENTS == (1ull << 14));
    static_assert(sizeof(ObeliskCommandPlayer) == 48);
    static_assert(offsetof(ObeliskCommandPlayer, flags) == 8);
    static_assert(offsetof(ObeliskCommandPlayer, player_name) == 16);
    static_assert(offsetof(ObeliskCommandPlayer, platform_id) == 32);
    AssertAbiType<ObeliskCommandPlayer>();
    static_assert(OBELISK_API_CAPABILITY_COMMAND_PLAYER_SNAPSHOT == (1ull << 13));
    static_assert(sizeof(ObeliskCommandInvocation) == 40);
    static_assert(offsetof(ObeliskCommandInvocation, invocation_token) == 16);
    static_assert(offsetof(ObeliskCommandInvocation, command_text) == 24);
    static_assert(OBELISK_API_CAPABILITY_COMMAND_REPLIES == (1ull << 12));

    static_assert(offsetof(ObeliskApi, RegisterPostProcessEventForNameIndexWithOwnerToken) +
        sizeof(ObeliskApi::RegisterPostProcessEventForNameIndexWithOwnerToken) <= sizeof(ObeliskApi),
        "owner-token callback capability requires the owner-token registration prefix");
    static_assert(offsetof(ObeliskApi, UnregisterProcessEventCallbackWithOwnerToken) +
        sizeof(ObeliskApi::UnregisterProcessEventCallbackWithOwnerToken) <= sizeof(ObeliskApi),
        "ProcessEvent callback handle capability requires the unregister slot");
    static_assert(offsetof(ObeliskApi, UnregisterGameplayPolicyEventWithOwnerToken) +
        sizeof(ObeliskApi::UnregisterGameplayPolicyEventWithOwnerToken) <= sizeof(ObeliskApi),
        "gameplay policy event capability requires register and unregister slots");
    static_assert(offsetof(ObeliskApi, DescribeResourceKind) +
        sizeof(ObeliskApi::DescribeResourceKind) <= sizeof(ObeliskApi),
        "resource kind descriptor capability requires the descriptor slot");
    static_assert(offsetof(ObeliskApi, DescribeGameplayPolicyEventKind) +
        sizeof(ObeliskApi::DescribeGameplayPolicyEventKind) <= sizeof(ObeliskApi),
        "gameplay policy event descriptor capability requires the descriptor slot");
    static_assert(offsetof(ObeliskApi, UnregisterChatMessageEventWithOwnerToken) +
        sizeof(ObeliskApi::UnregisterChatMessageEventWithOwnerToken) <= sizeof(ObeliskApi),
        "chat event capability requires register and unregister slots");
    static_assert(offsetof(ObeliskApi, UnregisterTimerWithOwnerToken) +
        sizeof(ObeliskApi::UnregisterTimerWithOwnerToken) <= sizeof(ObeliskApi),
        "timer capability requires register and unregister slots");

    RuntimeNoOp();
    return 0;
}
