#include <obelisk/ObeliskApi.h>

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/*
 * This guard validates the C ABI shape consumed by plugins. A passing build is
 * intentionally not a public SDK readiness, stable SDK, package publication, or
 * v1 completion claim.
 */

#if !defined(__linux__) || !defined(__x86_64__)
#error "Obelisk public SDK ABI layout guard is defined for Linux x86_64 consumers."
#endif

#define OBELISK_FIELD_END(type, field) (offsetof(type, field) + sizeof(((type*)0)->field))

_Static_assert(sizeof(void*) == 8, "Obelisk public SDK ABI guard expects 64-bit pointers");

_Static_assert(OBELISK_API_ABI_VERSION == 1u, "unexpected ObeliskApi ABI version");
_Static_assert(OBELISK_PLUGIN_METADATA_ABI_VERSION == 1u, "unexpected metadata ABI version");
_Static_assert(OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION == 1u, "unexpected init context ABI version");
_Static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION == 1u,
    "unexpected gameplay policy event ABI version");
_Static_assert(OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION == 1u,
    "unexpected resource kind descriptor ABI version");
_Static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION == 1u,
    "unexpected gameplay policy descriptor ABI version");
_Static_assert(OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION == 1u,
    "unexpected chat message event ABI version");

_Static_assert(OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS == (1ull << 0),
    "plugin-owned callback capability bit changed");
_Static_assert(OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS == (1ull << 1),
    "global ProcessEvent capability bit changed");
_Static_assert(OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS == (1ull << 2),
    "owner-token callback capability bit changed");
_Static_assert(OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES == (1ull << 3),
    "ProcessEvent handle capability bit changed");
_Static_assert(OBELISK_API_CAPABILITY_CALL_PROCESS_\
EVENT == (1ull << 4),
    "CallProcessEvent capability bit changed");
_Static_assert(OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING == (1ull << 5),
    "ProcessEvent blocking capability bit changed");
_Static_assert(OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS == (1ull << 6),
    "gameplay policy capability bit changed");
_Static_assert(OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS == (1ull << 7),
    "resource descriptor capability bit changed");
_Static_assert(OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS == (1ull << 8),
    "gameplay policy descriptor capability bit changed");
_Static_assert(OBELISK_API_CAPABILITY_CHAT_EVENTS == (1ull << 9),
    "chat event capability bit changed");
_Static_assert(OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS == (1ull << 10),
    "filtered ProcessEvent capability bit changed");
_Static_assert(OBELISK_API_CAPABILITY_TIMERS == (1ull << 11),
    "timer capability bit changed");

#if defined(OBELISK_API_CAPABILITY_IDENTITY) || \
    defined(OBELISK_API_CAPABILITY_IDENTITIES) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPALS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_IDENTITY) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_IDENTITIES) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPALS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_LIFECYCLE) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_LIFECYCLE_EVENTS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_IDENTITY_LIFECYCLE) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_LOOKUP) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_LOOKUP) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_RESOLVE) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_RESOLVER) || \
    defined(OBELISK_API_CAPABILITY_IDENTITY_LOOKUP) || \
    defined(OBELISK_API_CAPABILITY_IDENTITY_RESOLVE) || \
    defined(OBELISK_API_CAPABILITY_IDENTITY_RESOLVER) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL_LOOKUP) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL_RESOLVE) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL_RESOLVER) || \
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
    defined(OBELISK_API_CAPABILITY_PLAYER_HANDLE) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_ID) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL_HANDLE) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL_ID) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_HANDLE) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_ID) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_DATA_ID) || \
    defined(OBELISK_API_CAPABILITY_ACCOUNT_ID) || \
    defined(OBELISK_API_CAPABILITY_PLATFORM_ID) || \
    defined(OBELISK_API_CAPABILITY_NETWORK_ID) || \
    defined(OBELISK_API_CAPABILITY_IDENTITY_STORAGE) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL_STORAGE) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_IDENTITY_STORAGE) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_STORAGE) || \
    defined(OBELISK_API_CAPABILITY_IDENTITY_PERSISTENCE) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL_PERSISTENCE) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_IDENTITY_PERSISTENCE) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_PERSISTENCE) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_SESSION) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_LIFECYCLE) || \
    defined(OBELISK_API_CAPABILITY_IDENTITY_EVENTS) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL_EVENTS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_\
EVENTS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_IDENTITY_EVENTS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_EVENTS) || \
    defined(OBELISK_API_CAPABILITY_IDENTITY_CALLBACKS) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL_CALLBACKS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_CALLBACKS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_IDENTITY_CALLBACKS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_CALLBACKS) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_CONNECT) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_DISCONNECT) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_LOGIN) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_LOGOUT) || \
    defined(OBELISK_API_CAPABILITY_STEAM_ID) || \
    defined(OBELISK_API_CAPABILITY_STEAMID) || \
    defined(OBELISK_API_CAPABILITY_EOS_ID) || \
    defined(OBELISK_API_CAPABILITY_UNIQUE_NET_ID) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_HANDLE) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_HANDLES) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_IDENTITY) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_LOOKUP) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_RESOLVE) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_RESOLVER) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_ID) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_REF) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_REFERENCE) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_TOKEN) || \
    defined(OBELISK_API_CAPABILITY_OBJECT_HANDLE) || \
    defined(OBELISK_API_CAPABILITY_OBJECT_IDENTITY) || \
    defined(OBELISK_API_CAPABILITY_OBJECT_LOOKUP) || \
    defined(OBELISK_API_CAPABILITY_OWNERSHIP) || \
    defined(OBELISK_API_CAPABILITY_OWNER_LOOKUP) || \
    defined(OBELISK_API_CAPABILITY_OWNER_RESOLVE) || \
    defined(OBELISK_API_CAPABILITY_OWNER_RESOLVER) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_OWNERSHIP) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL_OWNERSHIP) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_OWNERSHIP) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_OWNER) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_OWNER) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL_OWNER) || \
    defined(OBELISK_API_CAPABILITY_TRIBE) || \
    defined(OBELISK_API_CAPABILITY_TRIBE_ID) || \
    defined(OBELISK_API_CAPABILITY_TRIBE_LOOKUP) || \
    defined(OBELISK_API_CAPABILITY_TRIBE_OWNERSHIP) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_TRIBE) || \
    defined(OBELISK_API_CAPABILITY_COMMANDS) || \
    defined(OBELISK_API_CAPABILITY_CHAT_COMMANDS) || \
    defined(OBELISK_API_CAPABILITY_COMMAND_CHAT_RESPONSE_PATH) || \
    defined(OBELISK_API_CAPABILITY_COMMAND_RESPONSE) || \
    defined(OBELISK_API_CAPABILITY_CHAT_RESPONSE) || \
    defined(OBELISK_API_CAPABILITY_CHAT_REPLY) || \
    defined(OBELISK_API_CAPABILITY_CHAT_REPLIES) || \
    defined(OBELISK_API_CAPABILITY_COMMAND_REPLY) || \
    defined(OBELISK_API_CAPABILITY_COMMANDS_REPLIES) || \
    defined(OBELISK_API_CAPABILITY_COMMAND_ROUTER) || \
    defined(OBELISK_API_CAPABILITY_SEND_CHAT) || \
    defined(OBELISK_API_CAPABILITY_BROADCAST) || \
    defined(OBELISK_API_CAPABILITY_NOTICES) || \
    defined(OBELISK_API_CAPABILITY_CALL_PROCESS_\
EVENT_RESPONSE) || \
    defined(OBELISK_API_CAPABILITY_ADMIN) || \
    defined(OBELISK_API_CAPABILITY_AUTH) || \
    defined(OBELISK_API_CAPABILITY_AUTHZ) || \
    defined(OBELISK_API_CAPABILITY_ACCESS_CONTROL) || \
    defined(OBELISK_API_CAPABILITY_ACL) || \
    defined(OBELISK_API_CAPABILITY_PERMISSIONS) || \
    defined(OBELISK_API_CAPABILITY_PERMISSION_CHECKS) || \
    defined(OBELISK_API_CAPABILITY_PERMISSION_QUERY) || \
    defined(OBELISK_API_CAPABILITY_PLAYER_PERMISSION) || \
    defined(OBELISK_API_CAPABILITY_PRINCIPAL_PERMISSION) || \
    defined(OBELISK_API_CAPABILITY_PERMISSIONS_ADMIN) || \
    defined(OBELISK_API_CAPABILITY_ADMIN_COMMANDS) || \
    defined(OBELISK_API_CAPABILITY_ROLES) || \
    defined(OBELISK_API_CAPABILITY_PRIVILEGES) || \
    defined(OBELISK_API_CAPABILITY_MODERATION) || \
    defined(OBELISK_API_CAPABILITY_BAN) || \
    defined(OBELISK_API_CAPABILITY_KICK) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_MUTATION) || \
    defined(OBELISK_API_CAPABILITY_MUTATION) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_MUTABLE) || \
    defined(OBELISK_API_CAPABILITY_MUTABLE_RESOURCE) || \
    defined(OBELISK_API_CAPABILITY_RESOURCE_WRITE) || \
    defined(OBELISK_API_CAPABILITY_WRITE_RESOURCE) || \
    defined(OBELISK_API_CAPABILITY_RETURN_OVERRIDE) || \
    defined(OBELISK_API_CAPABILITY_RETURN_OVERRIDES) || \
    defined(OBELISK_API_CAPABILITY_RUNTIME_READY) || \
    defined(OBELISK_IDENTITY_READY) || \
    defined(OBELISK_IDENTITY_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_IDENTITY_P0_DEPENDENCY_READY) || \
    defined(OBELISK_PLAYER_IDENTITY_P0_DEPENDENCY_READY) || \
    defined(OBELISK_IDENTITY_DEPENDENCY_READY) || \
    defined(OBELISK_PLAYER_IDENTITY_DEPENDENCY_READY) || \
    defined(OBELISK_PLAYER_IDENTITY_READY) || \
    defined(OBELISK_PLAYER_PRINCIPAL_READY) || \
    defined(OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_READY) || \
    defined(OBELISK_PLAYER_IDENTITY_OWNER_TOKEN_READY) || \
    defined(OBELISK_PLAYER_PRINCIPAL_OWNER_TOKEN_READY) || \
    defined(OBELISK_IDENTITY_OWNER_TOKEN_READY) || \
    defined(OBELISK_OWNER_TOKEN_IDENTITY_READY) || \
    defined(OBELISK_IDENTITY_OWNER_TOKEN_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_PLAYER_IDENTITY_OWNER_TOKEN_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_PLAYER_PRINCIPAL_OWNER_TOKEN_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_IDENTITY_CALLBACK_LIFETIME_READY) || \
    defined(OBELISK_PLAYER_IDENTITY_CALLBACK_LIFETIME_READY) || \
    defined(OBELISK_PLAYER_PRINCIPAL_CALLBACK_LIFETIME_READY) || \
    defined(OBELISK_PUBLIC_IDENTITY_CALLBACKS_READY) || \
    defined(OBELISK_PUBLIC_PLAYER_IDENTITY_CALLBACKS_READY) || \
    defined(OBELISK_PUBLIC_IDENTITY_ALLOWED) || \
    defined(OBELISK_PUBLIC_IDENTITY_READY) || \
    defined(OBELISK_PUBLIC_PRINCIPAL_READY) || \
    defined(OBELISK_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_COMPLETE_SDK_READY) || \
    defined(OBELISK_COMPLETE_SDK_V1_READY) || \
    defined(OBELISK_SDK_COMPLETE) || \
    defined(OBELISK_SDK_V1_COMPLETE) || \
    defined(OBELISK_V1_SDK_COMPLETE) || \
    defined(OBELISK_PUBLIC_API_READY) || \
    defined(OBELISK_PUBLIC_ABI_READY) || \
    defined(OBELISK_PUBLIC_HEADER_GATE_OPEN) || \
    defined(OBELISK_PUBLIC_HEADER_GATE_PASSED) || \
    defined(OBELISK_PUBLIC_HEADER_GATE_READY) || \
    defined(OBELISK_HEADER_PROMOTION_GATE_OPEN) || \
    defined(OBELISK_HEADER_PROMOTION_GATE_PASSED) || \
    defined(OBELISK_HEADER_PROMOTION_GATE_READY) || \
    defined(OBELISK_PUBLIC_HEADER_PROMOTION_GATE_OPEN) || \
    defined(OBELISK_PUBLIC_HEADER_PROMOTION_GATE_PASSED) || \
    defined(OBELISK_PUBLIC_HEADER_PROMOTION_GATE_READY) || \
    defined(OBELISK_APPROVED_RUNTIME_EVIDENCE_ACCEPTED) || \
    defined(OBELISK_APPROVED_RUNTIME_BUNDLE_ACCEPTED) || \
    defined(OBELISK_PUBLIC_CONTRACT_REVIEW_ACCEPTED) || \
    defined(OBELISK_IDENTITY_LOOKUP_READY) || \
    defined(OBELISK_PUBLIC_LOOKUP_READY) || \
    defined(OBELISK_IDENTITY_STORAGE_READY) || \
    defined(OBELISK_PUBLIC_IDENTITY_STORAGE_READY) || \
    defined(OBELISK_IDENTITY_PERSISTENCE_READY) || \
    defined(OBELISK_PUBLIC_IDENTITY_PERSISTENCE_READY) || \
    defined(OBELISK_PERMISSIONS_P0_DEPENDENCY_READY) || \
    defined(OBELISK_COMMANDS_P0_DEPENDENCY_READY) || \
    defined(OBELISK_PERMISSIONS_DEPENDENCY_READY) || \
    defined(OBELISK_COMMANDS_DEPENDENCY_READY) || \
    defined(OBELISK_IDENTITY_PERMISSION_COMMANDS_DEPENDENCIES_READY) || \
    defined(OBELISK_PERMISSIONS_ADMIN_READY) || \
    defined(OBELISK_COMMANDS_READY) || \
    defined(OBELISK_POST_INIT_CALL_PROCESS_EVENT_SHORTCUT_READY) || \
    defined(OBELISK_CALL_PROCESS_EVENT_POST_INIT_READY) || \
    defined(OBELISK_CALL_PROCESS_EVENT_SHORTCUT_READY) || \
    defined(OBELISK_SDK_P0_PROGRESS_READY) || \
    defined(OBELISK_SDK_P0_PROGRESS_CLAIM_ALLOWED) || \
    defined(OBELISK_ABI_CANDIDATE_COUNTS_TOWARD_SDK_P0_PROGRESS) || \
    defined(OBELISK_IDENTITY_ABI_VERSION) || \
    defined(OBELISK_PRINCIPAL_ABI_VERSION) || \
    defined(OBELISK_IDENTITY_EVENT_ABI_VERSION) || \
    defined(OBELISK_PRINCIPAL_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_IDENTITY_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_IDENTITY_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_IDENTITY_LIFECYCLE_ABI_VERSION) || \
    defined(OBELISK_IDENTITY_OWNER_TOKEN_ABI_VERSION) || \
    defined(OBELISK_PLAYER_IDENTITY_OWNER_TOKEN_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_OWNER_TOKEN_ABI_VERSION) || \
    defined(OBELISK_PLAYER_IDENTITY_DESCRIPTOR_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_DESCRIPTOR_ABI_VERSION) || \
    defined(OBELISK_PLAYER_SESSION_ABI_VERSION) || \
    defined(OBELISK_PLAYER_LIFECYCLE_ABI_VERSION) || \
    defined(OBELISK_PLAYER_CALLBACK_ABI_VERSION) || \
    defined(OBELISK_IDENTITY_CALLBACK_ABI_VERSION) || \
    defined(OBELISK_PRINCIPAL_CALLBACK_ABI_VERSION) || \
    defined(OBELISK_PLAYER_IDENTITY_CALLBACK_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_CALLBACK_ABI_VERSION) || \
    defined(OBELISK_PLAYER_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_CONNECT_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_DISCONNECT_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_JOIN_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_LEAVE_EVENT_ABI_VERSION) || \
    defined(OBELISK_PRINCIPAL_HANDLE_ABI_VERSION) || \
    defined(OBELISK_IDENTITY_HANDLE_ABI_VERSION) || \
    defined(OBELISK_STEAM_ID_ABI_VERSION) || \
    defined(OBELISK_EOS_ID_ABI_VERSION) || \
    defined(OBELISK_UNIQUE_NET_ID_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_LOOKUP_ABI_VERSION) || \
    defined(OBELISK_PLAYER_RESOLVE_ABI_VERSION) || \
    defined(OBELISK_PLAYER_RESOLVER_ABI_VERSION) || \
    defined(OBELISK_IDENTITY_RESOLVE_ABI_VERSION) || \
    defined(OBELISK_IDENTITY_RESOLVER_ABI_VERSION) || \
    defined(OBELISK_PRINCIPAL_RESOLVE_ABI_VERSION) || \
    defined(OBELISK_PRINCIPAL_RESOLVER_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_RESOLVE_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_RESOLVER_ABI_VERSION) || \
    defined(OBELISK_PLAYER_HANDLE_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_HANDLE_ABI_VERSION) || \
    defined(OBELISK_PLAYER_IDENTITY_HANDLE_ABI_VERSION) || \
    defined(OBELISK_PRINCIPAL_ID_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_ID_ABI_VERSION) || \
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
    defined(OBELISK_PLAYER_PRINCIPAL_STARTED_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_ENDED_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_START_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_END_EVENT_ABI_VERSION) || \
    defined(OBELISK_PLAYER_ID_ABI_VERSION) || \
    defined(OBELISK_PLAYER_DATA_ID_ABI_VERSION) || \
    defined(OBELISK_ACCOUNT_ID_ABI_VERSION) || \
    defined(OBELISK_PLATFORM_ID_ABI_VERSION) || \
    defined(OBELISK_NETWORK_ID_ABI_VERSION) || \
    defined(OBELISK_IDENTITY_STORAGE_ABI_VERSION) || \
    defined(OBELISK_PRINCIPAL_STORAGE_ABI_VERSION) || \
    defined(OBELISK_PLAYER_IDENTITY_STORAGE_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_STORAGE_ABI_VERSION) || \
    defined(OBELISK_IDENTITY_PERSISTENCE_ABI_VERSION) || \
    defined(OBELISK_PRINCIPAL_PERSISTENCE_ABI_VERSION) || \
    defined(OBELISK_PLAYER_IDENTITY_PERSISTENCE_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PRINCIPAL_PERSISTENCE_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_HANDLE_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_HANDLE_DESCRIPTOR_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_IDENTITY_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_LOOKUP_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_RESOLVE_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_RESOLVER_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_ID_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_REF_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_REFERENCE_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_TOKEN_ABI_VERSION) || \
    defined(OBELISK_OBJECT_HANDLE_ABI_VERSION) || \
    defined(OBELISK_OBJECT_IDENTITY_ABI_VERSION) || \
    defined(OBELISK_OBJECT_LOOKUP_ABI_VERSION) || \
    defined(OBELISK_OWNERSHIP_ABI_VERSION) || \
    defined(OBELISK_OWNER_LOOKUP_ABI_VERSION) || \
    defined(OBELISK_OWNER_RESOLVE_ABI_VERSION) || \
    defined(OBELISK_OWNER_RESOLVER_ABI_VERSION) || \
    defined(OBELISK_PLAYER_OWNERSHIP_ABI_VERSION) || \
    defined(OBELISK_PRINCIPAL_OWNERSHIP_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_OWNERSHIP_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_OWNER_ABI_VERSION) || \
    defined(OBELISK_PLAYER_OWNER_ABI_VERSION) || \
    defined(OBELISK_PRINCIPAL_OWNER_ABI_VERSION) || \
    defined(OBELISK_TRIBE_ABI_VERSION) || \
    defined(OBELISK_TRIBE_ID_ABI_VERSION) || \
    defined(OBELISK_TRIBE_LOOKUP_ABI_VERSION) || \
    defined(OBELISK_TRIBE_OWNERSHIP_ABI_VERSION) || \
    defined(OBELISK_PLAYER_TRIBE_ABI_VERSION) || \
    defined(OBELISK_ADMIN_ABI_VERSION) || \
    defined(OBELISK_AUTH_ABI_VERSION) || \
    defined(OBELISK_AUTHZ_ABI_VERSION) || \
    defined(OBELISK_ACCESS_CONTROL_ABI_VERSION) || \
    defined(OBELISK_ACL_ABI_VERSION) || \
    defined(OBELISK_PERMISSION_QUERY_ABI_VERSION) || \
    defined(OBELISK_PERMISSION_CACHE_ABI_VERSION) || \
    defined(OBELISK_PERMISSION_CHECKS_ABI_VERSION) || \
    defined(OBELISK_PERMISSIONS_ABI_VERSION) || \
    defined(OBELISK_PLAYER_PERMISSION_ABI_VERSION) || \
    defined(OBELISK_PRINCIPAL_PERMISSION_ABI_VERSION) || \
    defined(OBELISK_PERMISSIONS_ADMIN_ABI_VERSION) || \
    defined(OBELISK_AUTHORIZATION_ABI_VERSION) || \
    defined(OBELISK_ADMIN_ACTION_ABI_VERSION) || \
    defined(OBELISK_ROLE_ABI_VERSION) || \
    defined(OBELISK_ROLES_ABI_VERSION) || \
    defined(OBELISK_PRIVILEGE_ABI_VERSION) || \
    defined(OBELISK_PRIVILEGES_ABI_VERSION) || \
    defined(OBELISK_MODERATION_ABI_VERSION) || \
    defined(OBELISK_BAN_ABI_VERSION) || \
    defined(OBELISK_KICK_ABI_VERSION) || \
    defined(OBELISK_COMMAND_ABI_VERSION) || \
    defined(OBELISK_COMMANDS_ABI_VERSION) || \
    defined(OBELISK_CHAT_COMMAND_ABI_VERSION) || \
    defined(OBELISK_CHAT_COMMANDS_ABI_VERSION) || \
    defined(OBELISK_COMMAND_CHAT_RESPONSE_ABI_VERSION) || \
    defined(OBELISK_COMMAND_RESPONSE_ABI_VERSION) || \
    defined(OBELISK_CHAT_RESPONSE_ABI_VERSION) || \
    defined(OBELISK_COMMAND_REPLY_ABI_VERSION) || \
    defined(OBELISK_CHAT_REPLY_ABI_VERSION) || \
    defined(OBELISK_COMMANDS_REPLIES_ABI_VERSION) || \
    defined(OBELISK_COMMAND_ROUTER_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_MUTATION_ABI_VERSION) || \
    defined(OBELISK_MUTATION_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_MUTABLE_ABI_VERSION) || \
    defined(OBELISK_MUTABLE_RESOURCE_ABI_VERSION) || \
    defined(OBELISK_RESOURCE_WRITE_ABI_VERSION) || \
    defined(OBELISK_WRITE_RESOURCE_ABI_VERSION) || \
    defined(OBELISK_RETURN_OVERRIDE_ABI_VERSION) || \
    defined(OBELISK_RETURN_OVERRIDES_ABI_VERSION)
#error "Obelisk public SDK ABI guard saw a blocked public capability macro"
#endif

#if defined(OBELISK_API_CAPABILITY_PUBLIC_CALL_PROCESS_EVENT) || \
    defined(OBELISK_API_CAPABILITY_STABLE_CALL_PROCESS_EVENT) || \
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
#error "Obelisk public SDK ABI guard saw a public raw ProcessEvent or CallProcessEvent macro"
#endif

#if defined(OBELISK_ABI_LAYOUT_READY) || \
    defined(OBELISK_ABI_LAYOUT_VALIDATED) || \
    defined(OBELISK_C_ABI_READY) || \
    defined(OBELISK_STRUCT_SIZE_READY) || \
    defined(OBELISK_STRUCT_SIZE_VALIDATED) || \
    defined(OBELISK_PUBLIC_ABI_AVAILABLE) || \
    defined(OBELISK_PUBLIC_HEADER_ALLOWED) || \
    defined(OBELISK_PUBLIC_HEADER_READY) || \
    defined(OBELISK_PUBLIC_HEADERS_READY) || \
    defined(OBELISK_PUBLIC_SDK_READY) || \
    defined(OBELISK_COMPLETE_SDK_READY) || \
    defined(OBELISK_COMPLETE_SDK_V1_READY) || \
    defined(OBELISK_SDK_COMPLETE) || \
    defined(OBELISK_SDK_V1_COMPLETE) || \
    defined(OBELISK_V1_SDK_COMPLETE) || \
    defined(OBELISK_PUBLIC_IDENTITY_ALLOWED) || \
    defined(OBELISK_PUBLIC_IDENTITY_READY) || \
    defined(OBELISK_PUBLIC_PRINCIPAL_READY) || \
    defined(OBELISK_IDENTITY_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_IDENTITY_OWNER_TOKEN_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_PLAYER_IDENTITY_OWNER_TOKEN_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_PLAYER_PRINCIPAL_OWNER_TOKEN_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_IDENTITY_CALLBACK_LIFETIME_READY) || \
    defined(OBELISK_PLAYER_IDENTITY_CALLBACK_LIFETIME_READY) || \
    defined(OBELISK_PLAYER_PRINCIPAL_CALLBACK_LIFETIME_READY) || \
    defined(OBELISK_PUBLIC_IDENTITY_CALLBACKS_READY) || \
    defined(OBELISK_PUBLIC_PLAYER_IDENTITY_CALLBACKS_READY) || \
    defined(OBELISK_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_PUBLIC_API_READY) || \
    defined(OBELISK_PUBLIC_ABI_READY) || \
    defined(OBELISK_IDENTITY_LOOKUP_READY) || \
    defined(OBELISK_PUBLIC_LOOKUP_READY) || \
    defined(OBELISK_RUNTIME_READY) || \
    defined(OBELISK_IDENTITY_P0_DEPENDENCY_READY) || \
    defined(OBELISK_PLAYER_IDENTITY_P0_DEPENDENCY_READY) || \
    defined(OBELISK_IDENTITY_DEPENDENCY_READY) || \
    defined(OBELISK_PLAYER_IDENTITY_DEPENDENCY_READY) || \
    defined(OBELISK_IDENTITY_STORAGE_READY) || \
    defined(OBELISK_PUBLIC_IDENTITY_STORAGE_READY) || \
    defined(OBELISK_IDENTITY_PERSISTENCE_READY) || \
    defined(OBELISK_PUBLIC_IDENTITY_PERSISTENCE_READY) || \
    defined(OBELISK_RESOURCE_READY) || \
    defined(OBELISK_RESOURCE_HANDLE_READY) || \
    defined(OBELISK_RESOURCE_LOOKUP_READY) || \
    defined(OBELISK_PUBLIC_RESOURCE_READY) || \
    defined(OBELISK_PUBLIC_RESOURCE_HANDLE_READY) || \
    defined(OBELISK_RESOURCE_HANDLE_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_RESOURCE_MUTATION_READY) || \
    defined(OBELISK_MUTATION_READY) || \
    defined(OBELISK_RESOURCE_MUTABLE_READY) || \
    defined(OBELISK_MUTABLE_RESOURCE_READY) || \
    defined(OBELISK_RESOURCE_WRITE_READY) || \
    defined(OBELISK_RETURN_OVERRIDE_READY) || \
    defined(OBELISK_RETURN_OVERRIDES_READY) || \
    defined(OBELISK_PERMISSIONS_P0_DEPENDENCY_READY) || \
    defined(OBELISK_COMMANDS_P0_DEPENDENCY_READY) || \
    defined(OBELISK_PERMISSIONS_DEPENDENCY_READY) || \
    defined(OBELISK_COMMANDS_DEPENDENCY_READY) || \
    defined(OBELISK_IDENTITY_PERMISSION_COMMANDS_DEPENDENCIES_READY) || \
    defined(OBELISK_PERMISSIONS_ADMIN_READY) || \
    defined(OBELISK_COMMANDS_READY) || \
    defined(OBELISK_COMMAND_REPLIES_READY) || \
    defined(OBELISK_CHAT_REPLIES_READY) || \
    defined(OBELISK_POST_INIT_CALL_PROCESS_EVENT_SHORTCUT_READY) || \
    defined(OBELISK_CALL_PROCESS_EVENT_POST_INIT_READY) || \
    defined(OBELISK_CALL_PROCESS_EVENT_SHORTCUT_READY) || \
    defined(OBELISK_PUBLIC_CALL_PROCESS_EVENT_READY) || \
    defined(OBELISK_STABLE_CALL_PROCESS_EVENT_READY) || \
    defined(OBELISK_CALL_PROCESS_EVENT_PUBLIC_READY) || \
    defined(OBELISK_CALL_PROCESS_EVENT_STABLE_READY) || \
    defined(OBELISK_RAW_PROCESS_EVENT_READY) || \
    defined(OBELISK_RAW_PROCESS_EVENT_PUBLIC_READY) || \
    defined(OBELISK_PUBLIC_PROCESS_EVENT_READY) || \
    defined(OBELISK_PROCESS_EVENT_PUBLIC_READY) || \
    defined(OBELISK_PROCESS_EVENT_PUBLIC_SDK_READY) || \
    defined(OBELISK_PROCESS_EVENT_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_RAW_PROCESS_EVENT_PUBLIC_CONTRACT_READY) || \
    defined(OBELISK_PROCESS_EVENT_STABLE_SDK_READY) || \
    defined(OBELISK_PROCESS_EVENT_CALLBACKS_PUBLIC_READY) || \
    defined(OBELISK_RAW_PROCESS_EVENT_CALLBACKS_READY) || \
    defined(OBELISK_SDK_P0_PROGRESS_READY) || \
    defined(OBELISK_SDK_P0_PROGRESS_CLAIM_ALLOWED) || \
    defined(OBELISK_ABI_CANDIDATE_COUNTS_TOWARD_SDK_P0_PROGRESS) || \
    defined(OBELISK_STABLE_SDK_READY) || \
    defined(OBELISK_RUNTIME_READINESS_CLAIM_ALLOWED) || \
    defined(OBELISK_RUNTIME_LIVE_OP_APPROVAL_ALLOWED) || \
    defined(OBELISK_PLUGIN_HUB_PUBLICATION_ALLOWED) || \
    defined(OBELISK_PLUGIN_HUB_READINESS_CLAIM_ALLOWED) || \
    defined(OBELISK_SUPPORT_TIER_ACTIVATION_ALLOWED) || \
    defined(OBELISK_V1_COMPLETION_CLAIM_ALLOWED) || \
    defined(OBELISK_PUBLIC_MODULE_SDK_COVERAGE_CLAIM_ALLOWED) || \
    defined(OBELISK_PRODUCTION_STABLE_SDK_CLAIM_ALLOWED) || \
    defined(OBELISK_INSTALLED_SDK_PACKAGE_READY) || \
    defined(OBELISK_PACKAGE_SHAPE_READY) || \
    defined(OBELISK_PACKAGE_PUBLICATION_ALLOWED) || \
    defined(OBELISK_SDK_CONSUMER_TESTS_READY)
#error "Obelisk ABI layout guard saw a public readiness or claim macro"
#endif

_Static_assert(OBELISK_TIMER_FLAG_REPEATING == (1ull << 0), "timer repeating flag changed");
_Static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD == (1ull << 0),
    "gameplay policy copied-payload flag changed");
_Static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED == (1ull << 1),
    "gameplay policy structure-backed flag changed");
_Static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED == (1ull << 2),
    "gameplay policy inventory-backed flag changed");
_Static_assert(OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD == (1ull << 0),
    "chat copied-payload flag changed");
_Static_assert(OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY == (1ull << 0),
    "resource descriptor category-only flag changed");
_Static_assert(OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY == (1ull << 1),
    "resource descriptor no-identity flag changed");
_Static_assert(OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP == (1ull << 2),
    "resource descriptor no-lookup flag changed");

_Static_assert(OBELISK_CHAT_SEND_MODE_GLOBAL == 0, "chat global send mode changed");
_Static_assert(OBELISK_CHAT_SEND_MODE_ALLIANCE == 3, "chat alliance send mode changed");
_Static_assert(OBELISK_CHAT_SEND_MODE_COUNT == 4u, "chat send mode count changed");
_Static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACCESS_CHECK == 1,
    "first gameplay policy event kind changed");
_Static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK == 11,
    "last gameplay policy event kind changed");
_Static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_COUNT == 11u,
    "gameplay policy event kind count changed");
_Static_assert(OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE == 1,
    "structure resource kind changed");
_Static_assert(OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM == 2,
    "inventory item resource kind changed");
_Static_assert(OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE == 0,
    "return-value gameplay policy field changed");
_Static_assert(OBELISK_GAMEPLAY_POLICY_FIELD_IGNORE_COOLDOWN == 5,
    "ignore-cooldown gameplay policy field changed");
_Static_assert(OBELISK_GAMEPLAY_POLICY_FIELD_COUNT == 6,
    "gameplay policy field count changed");

_Static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK == (1ull << 0),
    "structure access event mask changed");
_Static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK == (1ull << 10),
    "inventory use-onto-item event mask changed");
_Static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES == 0x3full,
    "all-structures event mask changed");
_Static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY == 0x7c0ull,
    "all-inventory event mask changed");
_Static_assert(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL == 0x7ffull,
    "all gameplay policy event mask changed");
_Static_assert(OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE == (1ull << 0),
    "return-value field mask changed");
_Static_assert(OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN == (1ull << 5),
    "ignore-cooldown field mask changed");

_Static_assert(offsetof(ObeliskStringView, data) == 0u, "ObeliskStringView data offset changed");
_Static_assert(offsetof(ObeliskStringView, size) == 8u, "ObeliskStringView size offset changed");
_Static_assert(_Alignof(ObeliskStringView) == 8u, "ObeliskStringView alignment changed");
_Static_assert(sizeof(ObeliskStringView) == 16u, "ObeliskStringView size changed");

_Static_assert(offsetof(ObeliskChatMessageEvent, abi_version) == 0u,
    "ObeliskChatMessageEvent abi_version offset changed");
_Static_assert(offsetof(ObeliskChatMessageEvent, struct_size) == 4u,
    "ObeliskChatMessageEvent struct_size offset changed");
_Static_assert(offsetof(ObeliskChatMessageEvent, send_mode) == 8u,
    "ObeliskChatMessageEvent send_mode offset changed");
_Static_assert(offsetof(ObeliskChatMessageEvent, reserved0) == 12u,
    "ObeliskChatMessageEvent reserved0 offset changed");
_Static_assert(offsetof(ObeliskChatMessageEvent, flags) == 16u,
    "ObeliskChatMessageEvent flags offset changed");
_Static_assert(offsetof(ObeliskChatMessageEvent, sequence) == 24u,
    "ObeliskChatMessageEvent sequence offset changed");
_Static_assert(offsetof(ObeliskChatMessageEvent, message) == 32u,
    "ObeliskChatMessageEvent message offset changed");
_Static_assert(sizeof(ObeliskChatMessageEvent) == 48u,
    "ObeliskChatMessageEvent v1 size changed");
_Static_assert(_Alignof(ObeliskChatMessageEvent) == 8u,
    "ObeliskChatMessageEvent alignment changed");
_Static_assert(OBELISK_FIELD_END(ObeliskChatMessageEvent, message) ==
        sizeof(ObeliskChatMessageEvent),
    "future chat event fields must be appended and struct_size-gated");

_Static_assert(offsetof(ObeliskGameplayPolicyEvent, abi_version) == 0u,
    "ObeliskGameplayPolicyEvent abi_version offset changed");
_Static_assert(offsetof(ObeliskGameplayPolicyEvent, struct_size) == 4u,
    "ObeliskGameplayPolicyEvent struct_size offset changed");
_Static_assert(offsetof(ObeliskGameplayPolicyEvent, event_kind) == 8u,
    "ObeliskGameplayPolicyEvent event_kind offset changed");
_Static_assert(offsetof(ObeliskGameplayPolicyEvent, resource_kind) == 12u,
    "ObeliskGameplayPolicyEvent resource_kind offset changed");
_Static_assert(offsetof(ObeliskGameplayPolicyEvent, flags) == 16u,
    "ObeliskGameplayPolicyEvent flags offset changed");
_Static_assert(offsetof(ObeliskGameplayPolicyEvent, field_mask) == 24u,
    "ObeliskGameplayPolicyEvent field_mask offset changed");
_Static_assert(offsetof(ObeliskGameplayPolicyEvent, bool_values) == 32u,
    "ObeliskGameplayPolicyEvent bool_values offset changed");
_Static_assert(offsetof(ObeliskGameplayPolicyEvent, int32_values) == 40u,
    "ObeliskGameplayPolicyEvent int32_values offset changed");
_Static_assert(sizeof(ObeliskGameplayPolicyEvent) == 64u,
    "ObeliskGameplayPolicyEvent v1 size changed");
_Static_assert(_Alignof(ObeliskGameplayPolicyEvent) == 8u,
    "ObeliskGameplayPolicyEvent alignment changed");
_Static_assert(OBELISK_FIELD_END(ObeliskGameplayPolicyEvent, int32_values) ==
        sizeof(ObeliskGameplayPolicyEvent),
    "future gameplay policy event fields must be appended and struct_size-gated");

_Static_assert(offsetof(ObeliskResourceKindDescriptor, abi_version) == 0u,
    "ObeliskResourceKindDescriptor abi_version offset changed");
_Static_assert(offsetof(ObeliskResourceKindDescriptor, struct_size) == 4u,
    "ObeliskResourceKindDescriptor struct_size offset changed");
_Static_assert(offsetof(ObeliskResourceKindDescriptor, resource_kind) == 8u,
    "ObeliskResourceKindDescriptor resource_kind offset changed");
_Static_assert(offsetof(ObeliskResourceKindDescriptor, reserved0) == 12u,
    "ObeliskResourceKindDescriptor reserved0 offset changed");
_Static_assert(offsetof(ObeliskResourceKindDescriptor, flags) == 16u,
    "ObeliskResourceKindDescriptor flags offset changed");
_Static_assert(offsetof(ObeliskResourceKindDescriptor, supported_gameplay_policy_event_mask) == 24u,
    "ObeliskResourceKindDescriptor event mask offset changed");
_Static_assert(offsetof(ObeliskResourceKindDescriptor, supported_gameplay_policy_field_mask) == 32u,
    "ObeliskResourceKindDescriptor field mask offset changed");
_Static_assert(offsetof(ObeliskResourceKindDescriptor, stable_name) == 40u,
    "ObeliskResourceKindDescriptor stable_name offset changed");
_Static_assert(offsetof(ObeliskResourceKindDescriptor, display_name) == 72u,
    "ObeliskResourceKindDescriptor display_name offset changed");
_Static_assert(_Alignof(ObeliskResourceKindDescriptor) == 8u,
    "ObeliskResourceKindDescriptor alignment changed");
_Static_assert(OBELISK_FIELD_END(ObeliskResourceKindDescriptor, display_name) ==
        sizeof(ObeliskResourceKindDescriptor),
    "future resource descriptor fields must be appended and struct_size-gated");

_Static_assert(offsetof(ObeliskGameplayPolicyEventDescriptor, abi_version) == 0u,
    "ObeliskGameplayPolicyEventDescriptor abi_version offset changed");
_Static_assert(offsetof(ObeliskGameplayPolicyEventDescriptor, struct_size) == 4u,
    "ObeliskGameplayPolicyEventDescriptor struct_size offset changed");
_Static_assert(offsetof(ObeliskGameplayPolicyEventDescriptor, event_kind) == 8u,
    "ObeliskGameplayPolicyEventDescriptor event_kind offset changed");
_Static_assert(offsetof(ObeliskGameplayPolicyEventDescriptor, resource_kind) == 12u,
    "ObeliskGameplayPolicyEventDescriptor resource_kind offset changed");
_Static_assert(offsetof(ObeliskGameplayPolicyEventDescriptor, flags) == 16u,
    "ObeliskGameplayPolicyEventDescriptor flags offset changed");
_Static_assert(offsetof(ObeliskGameplayPolicyEventDescriptor, event_kind_mask) == 24u,
    "ObeliskGameplayPolicyEventDescriptor event_kind_mask offset changed");
_Static_assert(offsetof(ObeliskGameplayPolicyEventDescriptor, field_mask) == 32u,
    "ObeliskGameplayPolicyEventDescriptor field_mask offset changed");
_Static_assert(offsetof(ObeliskGameplayPolicyEventDescriptor, stable_name) == 40u,
    "ObeliskGameplayPolicyEventDescriptor stable_name offset changed");
_Static_assert(offsetof(ObeliskGameplayPolicyEventDescriptor, display_name) == 88u,
    "ObeliskGameplayPolicyEventDescriptor display_name offset changed");
_Static_assert(_Alignof(ObeliskGameplayPolicyEventDescriptor) == 8u,
    "ObeliskGameplayPolicyEventDescriptor alignment changed");
_Static_assert(OBELISK_FIELD_END(ObeliskGameplayPolicyEventDescriptor, display_name) ==
        sizeof(ObeliskGameplayPolicyEventDescriptor),
    "future gameplay policy descriptor fields must be appended and struct_size-gated");

_Static_assert(offsetof(ObeliskApi, LogInfo) == 0u, "ObeliskApi LogInfo offset changed");
_Static_assert(offsetof(ObeliskApi, LogWarn) == 8u, "ObeliskApi LogWarn offset changed");
_Static_assert(offsetof(ObeliskApi, LogError) == 16u, "ObeliskApi LogError offset changed");
_Static_assert(offsetof(ObeliskApi, RegisterPreProcessEvent) == 24u,
    "ObeliskApi RegisterPreProcessEvent offset changed");
_Static_assert(offsetof(ObeliskApi, RegisterPostProcessEvent) == 32u,
    "ObeliskApi RegisterPostProcessEvent offset changed");
_Static_assert(offsetof(ObeliskApi, RegisterPreProcessEventForNameIndex) == 40u,
    "ObeliskApi RegisterPreProcessEventForNameIndex offset changed");
_Static_assert(offsetof(ObeliskApi, RegisterPostProcessEventForNameIndex) == 48u,
    "ObeliskApi RegisterPostProcessEventForNameIndex offset changed");
_Static_assert(offsetof(ObeliskApi, CallProcessEvent) == 56u,
    "ObeliskApi CallProcessEvent offset changed");
_Static_assert(OBELISK_FIELD_END(ObeliskApi, CallProcessEvent) == offsetof(ObeliskApi, abi_version),
    "legacy raw ProcessEvent slots must end before appended struct_size metadata");
_Static_assert(offsetof(ObeliskApi, abi_version) == 64u,
    "ObeliskApi metadata must remain appended after the original v1 function table");
_Static_assert(offsetof(ObeliskApi, struct_size) == 68u, "ObeliskApi struct_size offset changed");
_Static_assert(offsetof(ObeliskApi, capabilities) == 72u, "ObeliskApi capabilities offset changed");

_Static_assert(offsetof(ObeliskApi, RegisterPreProcessEventWithOwnerToken) == 80u,
    "ObeliskApi owner-token registration offset changed");
_Static_assert(offsetof(ObeliskApi, RegisterPostProcessEventWithOwnerToken) == 88u,
    "ObeliskApi owner-token registration offset changed");
_Static_assert(offsetof(ObeliskApi, RegisterPreProcessEventForNameIndexWithOwnerToken) == 96u,
    "ObeliskApi owner-token filtered registration offset changed");
_Static_assert(offsetof(ObeliskApi, RegisterPostProcessEventForNameIndexWithOwnerToken) == 104u,
    "ObeliskApi owner-token filtered registration offset changed");
_Static_assert(offsetof(ObeliskApi, RegisterPreProcessEventWithOwnerTokenHandle) == 112u,
    "ObeliskApi owner-token handle registration offset changed");
_Static_assert(offsetof(ObeliskApi, RegisterPostProcessEventWithOwnerTokenHandle) == 120u,
    "ObeliskApi owner-token handle registration offset changed");
_Static_assert(offsetof(ObeliskApi, RegisterPreProcessEventForNameIndexWithOwnerTokenHandle) == 128u,
    "ObeliskApi filtered handle registration offset changed");
_Static_assert(offsetof(ObeliskApi, RegisterPostProcessEventForNameIndexWithOwnerTokenHandle) == 136u,
    "ObeliskApi filtered handle registration offset changed");
_Static_assert(offsetof(ObeliskApi, UnregisterProcessEventCallbackWithOwnerToken) == 144u,
    "ObeliskApi ProcessEvent unregister offset changed");

_Static_assert(offsetof(ObeliskApi, RegisterGameplayPolicyEventWithOwnerTokenHandle) == 152u,
    "ObeliskApi gameplay policy registration offset changed");
_Static_assert(offsetof(ObeliskApi, UnregisterGameplayPolicyEventWithOwnerToken) == 160u,
    "ObeliskApi gameplay policy unregister offset changed");
_Static_assert(offsetof(ObeliskApi, DescribeResourceKind) == 168u,
    "ObeliskApi resource descriptor offset changed");
_Static_assert(offsetof(ObeliskApi, DescribeGameplayPolicyEventKind) == 176u,
    "ObeliskApi gameplay policy descriptor offset changed");
_Static_assert(offsetof(ObeliskApi, RegisterChatMessageEventWithOwnerTokenHandle) == 184u,
    "ObeliskApi chat registration offset changed");
_Static_assert(offsetof(ObeliskApi, UnregisterChatMessageEventWithOwnerToken) == 192u,
    "ObeliskApi chat unregister offset changed");
_Static_assert(offsetof(ObeliskApi, RegisterTimerWithOwnerTokenHandle) == 200u,
    "ObeliskApi timer registration offset changed");
_Static_assert(offsetof(ObeliskApi, UnregisterTimerWithOwnerToken) == 208u,
    "ObeliskApi timer unregister offset changed");
_Static_assert(OBELISK_FIELD_END(ObeliskApi, UnregisterTimerWithOwnerToken) == 216u,
    "ObeliskApi pre-command v1 prefix changed");
_Static_assert(OBELISK_API_CAPABILITY_COMMAND_REPLIES == (1ull << 12), "Command capability bit changed");
_Static_assert(offsetof(ObeliskApi, RegisterCommandWithOwnerTokenHandle) == 216u, "Command registration offset changed");
_Static_assert(offsetof(ObeliskApi, UnregisterCommandWithOwnerToken) == 224u, "Command unregister offset changed");
_Static_assert(offsetof(ObeliskApi, ReplyToCommandWithOwnerToken) == 232u, "Command reply offset changed");
_Static_assert(OBELISK_FIELD_END(ObeliskApi, ReplyToCommandWithOwnerToken) == 240u, "Command/reply prefix changed");
_Static_assert(offsetof(ObeliskApi, GetCommandPlayerWithOwnerToken) == 240u, "Command player getter offset changed");
_Static_assert(offsetof(ObeliskApi, RegisterPlayerLifecycleWithOwnerTokenHandle) == 248u, "Lifecycle register offset changed");
_Static_assert(offsetof(ObeliskApi, UnregisterPlayerLifecycleWithOwnerToken) == 256u, "Lifecycle unregister offset changed");
_Static_assert(OBELISK_FIELD_END(ObeliskApi, UnregisterPlayerLifecycleWithOwnerToken) == 264u, "Lifecycle prefix changed");
_Static_assert(offsetof(ObeliskApi, RegisterCommandWithOptionsWithOwnerTokenHandle) == 264u, "Command options offset changed");
_Static_assert(OBELISK_FIELD_END(ObeliskApi, RegisterCommandWithOptionsWithOwnerTokenHandle) == 272u, "Command options tail changed");
// Append-only scoped destinations/world observation; all older prefixes stay fixed.
_Static_assert(offsetof(ObeliskApi, GetCommandChatSessionWithOwnerToken) == 272u, "GetCommandChatSessionWithOwnerToken offset changed");
_Static_assert(offsetof(ObeliskApi, ListChatSessionsWithOwnerToken) == 280u, "ListChatSessionsWithOwnerToken offset changed");
_Static_assert(offsetof(ObeliskApi, SendChatToSessionWithOwnerToken) == 288u, "SendChatToSessionWithOwnerToken offset changed");
_Static_assert(offsetof(ObeliskApi, GetCommandWorldInfoWithOwnerToken) == 296u, "GetCommandWorldInfoWithOwnerToken offset changed");
_Static_assert(offsetof(ObeliskApi, RegisterCommandWithOptionsWithOwnerTokenHandle) +
    sizeof(((ObeliskApi*)0)->RegisterCommandWithOptionsWithOwnerTokenHandle) == 272u, "Command options prefix changed");
_Static_assert(offsetof(ObeliskApi, GetCommandWorldInfoWithOwnerToken) +
    sizeof(((ObeliskApi*)0)->GetCommandWorldInfoWithOwnerToken) == 304u, "Scoped native API tail changed");
_Static_assert(offsetof(ObeliskApi, TeleportCommandOriginWithOwnerToken) == 304u, "Self teleport offset changed");
_Static_assert(offsetof(ObeliskApi, TeleportCommandOriginWithOwnerToken) +
    sizeof(((ObeliskApi*)0)->TeleportCommandOriginWithOwnerToken) == 312u, "Self teleport tail changed");
_Static_assert(OBELISK_API_CAPABILITY_COMMAND_SELF_TELEPORT == (1ull << 18), "Self teleport bit changed");
typedef bool (*TeleportCommandOriginWithOwnerTokenSignature)(uint64_t, uint64_t, const ObeliskCommandWorldInfo*);
_Static_assert(_Generic(((ObeliskApi*)0)->TeleportCommandOriginWithOwnerToken,
    TeleportCommandOriginWithOwnerTokenSignature: 1, default: 0), "Self teleport function signature changed");
_Static_assert(OBELISK_API_CAPABILITY_CHAT_SESSIONS == (1ull << 16), "OBELISK_API_CAPABILITY_CHAT_SESSIONS value changed");
_Static_assert(OBELISK_API_CAPABILITY_COMMAND_WORLD_INFO_NATIVE == (1ull << 17), "OBELISK_API_CAPABILITY_COMMAND_WORLD_INFO_NATIVE value changed");
_Static_assert(OBELISK_CHAT_SESSION_ABI_VERSION == 1u, "OBELISK_CHAT_SESSION_ABI_VERSION value changed");
_Static_assert(OBELISK_COMMAND_WORLD_INFO_ABI_VERSION == 1u, "OBELISK_COMMAND_WORLD_INFO_ABI_VERSION value changed");
_Static_assert(OBELISK_CHAT_SESSION_NAME_MAX_BYTES == 256u, "OBELISK_CHAT_SESSION_NAME_MAX_BYTES value changed");
_Static_assert(OBELISK_CHAT_SESSION_LIST_MAX == 64u, "OBELISK_CHAT_SESSION_LIST_MAX value changed");
_Static_assert(OBELISK_CHAT_SESSION_FLAG_NAME_AVAILABLE == 1ull, "OBELISK_CHAT_SESSION_FLAG_NAME_AVAILABLE value changed");
_Static_assert(OBELISK_COMMAND_WORLD_FLAG_POSITION_AVAILABLE == 1ull, "OBELISK_COMMAND_WORLD_FLAG_POSITION_AVAILABLE value changed");
_Static_assert(OBELISK_COMMAND_WORLD_FLAG_TRIBE_ID_AVAILABLE == 2ull, "OBELISK_COMMAND_WORLD_FLAG_TRIBE_ID_AVAILABLE value changed");
_Static_assert(OBELISK_COMMAND_WORLD_FLAG_ROTATION_AVAILABLE == 4ull, "OBELISK_COMMAND_WORLD_FLAG_ROTATION_AVAILABLE value changed");
_Static_assert(OBELISK_COMMAND_WORLD_FLAG_MOUNTED_DINO_IDS_AVAILABLE == 8ull, "OBELISK_COMMAND_WORLD_FLAG_MOUNTED_DINO_IDS_AVAILABLE value changed");
_Static_assert(OBELISK_COMMAND_WORLD_FLAG_TARGET_STRUCTURE_ID_AVAILABLE == 16ull, "OBELISK_COMMAND_WORLD_FLAG_TARGET_STRUCTURE_ID_AVAILABLE value changed");
_Static_assert(sizeof(ObeliskChatSession) == 304u, "ObeliskChatSession size changed");
_Static_assert(_Alignof(ObeliskChatSession) == 8u, "ObeliskChatSession alignment changed");
_Static_assert(offsetof(ObeliskChatSession, abi_version) == 0u, "ObeliskChatSession.abi_version offset changed");
_Static_assert(offsetof(ObeliskChatSession, struct_size) == 4u, "ObeliskChatSession.struct_size offset changed");
_Static_assert(offsetof(ObeliskChatSession, session_token) == 8u, "ObeliskChatSession.session_token offset changed");
_Static_assert(offsetof(ObeliskChatSession, process_epoch) == 16u, "ObeliskChatSession.process_epoch offset changed");
_Static_assert(offsetof(ObeliskChatSession, flags) == 24u, "ObeliskChatSession.flags offset changed");
_Static_assert(offsetof(ObeliskChatSession, player_name) == 32u, "ObeliskChatSession.player_name offset changed");
_Static_assert(offsetof(ObeliskChatSession, player_name_size) == 292u, "ObeliskChatSession.player_name_size offset changed");
_Static_assert(offsetof(ObeliskChatSession, reserved0) == 296u, "ObeliskChatSession.reserved0 offset changed");
_Static_assert(sizeof(ObeliskCommandWorldInfo) == 80u, "ObeliskCommandWorldInfo size changed");
_Static_assert(_Alignof(ObeliskCommandWorldInfo) == 8u, "ObeliskCommandWorldInfo alignment changed");
_Static_assert(offsetof(ObeliskCommandWorldInfo, abi_version) == 0u, "ObeliskCommandWorldInfo.abi_version offset changed");
_Static_assert(offsetof(ObeliskCommandWorldInfo, struct_size) == 4u, "ObeliskCommandWorldInfo.struct_size offset changed");
_Static_assert(offsetof(ObeliskCommandWorldInfo, flags) == 8u, "ObeliskCommandWorldInfo.flags offset changed");
_Static_assert(offsetof(ObeliskCommandWorldInfo, x) == 16u, "ObeliskCommandWorldInfo.x offset changed");
_Static_assert(offsetof(ObeliskCommandWorldInfo, y) == 20u, "ObeliskCommandWorldInfo.y offset changed");
_Static_assert(offsetof(ObeliskCommandWorldInfo, z) == 24u, "ObeliskCommandWorldInfo.z offset changed");
_Static_assert(offsetof(ObeliskCommandWorldInfo, native_tribe_id) == 28u, "ObeliskCommandWorldInfo.native_tribe_id offset changed");
_Static_assert(offsetof(ObeliskCommandWorldInfo, pitch) == 32u, "ObeliskCommandWorldInfo.pitch offset changed");
_Static_assert(offsetof(ObeliskCommandWorldInfo, yaw) == 36u, "ObeliskCommandWorldInfo.yaw offset changed");
_Static_assert(offsetof(ObeliskCommandWorldInfo, roll) == 40u, "ObeliskCommandWorldInfo.roll offset changed");
_Static_assert(offsetof(ObeliskCommandWorldInfo, reserved0) == 44u, "ObeliskCommandWorldInfo.reserved0 offset changed");
_Static_assert(offsetof(ObeliskCommandWorldInfo, process_epoch) == 48u, "ObeliskCommandWorldInfo.process_epoch offset changed");
_Static_assert(offsetof(ObeliskCommandWorldInfo, session_token) == 56u, "ObeliskCommandWorldInfo.session_token offset changed");
_Static_assert(offsetof(ObeliskCommandWorldInfo, mounted_dino_id1) == 64u, "ObeliskCommandWorldInfo.mounted_dino_id1 offset changed");
_Static_assert(offsetof(ObeliskCommandWorldInfo, mounted_dino_id2) == 68u, "ObeliskCommandWorldInfo.mounted_dino_id2 offset changed");
_Static_assert(offsetof(ObeliskCommandWorldInfo, target_structure_id) == 72u, "ObeliskCommandWorldInfo.target_structure_id offset changed");
_Static_assert(offsetof(ObeliskCommandWorldInfo, reserved1) == 76u, "ObeliskCommandWorldInfo.reserved1 offset changed");
_Static_assert(sizeof(((ObeliskChatSession*)0)->player_name) == 257u, "Copied session name extent changed");
typedef bool (*GetCommandChatSessionWithOwnerTokenSignature)(uint64_t, uint64_t, ObeliskChatSession*);
_Static_assert(_Generic(((ObeliskApi*)0)->GetCommandChatSessionWithOwnerToken,
    GetCommandChatSessionWithOwnerTokenSignature: 1, default: 0), "GetCommandChatSessionWithOwnerToken signature changed");
typedef bool (*ListChatSessionsWithOwnerTokenSignature)(uint64_t, uint64_t, ObeliskChatSession*, size_t, size_t*, size_t*);
_Static_assert(_Generic(((ObeliskApi*)0)->ListChatSessionsWithOwnerToken,
    ListChatSessionsWithOwnerTokenSignature: 1, default: 0), "ListChatSessionsWithOwnerToken signature changed");
typedef bool (*SendChatToSessionWithOwnerTokenSignature)(uint64_t, uint64_t, uint64_t, uint64_t, ObeliskCommandStringView);
_Static_assert(_Generic(((ObeliskApi*)0)->SendChatToSessionWithOwnerToken,
    SendChatToSessionWithOwnerTokenSignature: 1, default: 0), "SendChatToSessionWithOwnerToken signature changed");
typedef bool (*GetCommandWorldInfoWithOwnerTokenSignature)(uint64_t, uint64_t, ObeliskCommandWorldInfo*);
_Static_assert(_Generic(((ObeliskApi*)0)->GetCommandWorldInfoWithOwnerToken,
    GetCommandWorldInfoWithOwnerTokenSignature: 1, default: 0), "GetCommandWorldInfoWithOwnerToken signature changed");

_Static_assert(OBELISK_API_CAPABILITY_COMMAND_MATCH_OPTIONS == (1ull << 15), "Command options capability changed");
_Static_assert(OBELISK_COMMAND_MATCH_FLAG_VERB == 1ull, "Command verb flag changed");
_Static_assert(OBELISK_COMMAND_MATCH_FLAG_ASCII_CASE_INSENSITIVE == 2ull, "Command case flag changed");
typedef uint64_t (*RegisterOptionsSignature)(uint64_t, const char*, uint64_t, ObeliskCommandCallback, void*);
_Static_assert(_Generic(((ObeliskApi*)0)->RegisterCommandWithOptionsWithOwnerTokenHandle,
    RegisterOptionsSignature: 1, default: 0), "Command options function signature changed");
_Static_assert(sizeof(ObeliskPlayerLifecycleEvent) == 72u, "Lifecycle event layout changed");
_Static_assert(offsetof(ObeliskPlayerLifecycleEvent, player_name) == 40u, "Lifecycle name offset changed");
_Static_assert(offsetof(ObeliskPlayerLifecycleEvent, platform_id) == 56u, "Lifecycle ID offset changed");
_Static_assert(OBELISK_API_CAPABILITY_PLAYER_LIFECYCLE_EVENTS == (1ull << 14), "Lifecycle capability changed");
_Static_assert(OBELISK_API_CAPABILITY_COMMAND_PLAYER_SNAPSHOT == (1ull << 13), "Command player bit changed");
_Static_assert(sizeof(ObeliskCommandPlayer) == 48u, "Command player layout changed");
_Static_assert(offsetof(ObeliskCommandPlayer, flags) == 8u, "Command player flags offset changed");
_Static_assert(offsetof(ObeliskCommandPlayer, player_name) == 16u, "Command player name offset changed");
_Static_assert(offsetof(ObeliskCommandPlayer, platform_id) == 32u, "Command player ID offset changed");
_Static_assert(sizeof(ObeliskCommandInvocation) == 40u, "Command event layout changed");
_Static_assert(offsetof(ObeliskCommandInvocation, invocation_token) == 16u, "Invocation token offset changed");
_Static_assert(offsetof(ObeliskCommandInvocation, command_text) == 24u, "Command text offset changed");
_Static_assert(_Alignof(ObeliskApi) == 8u, "ObeliskApi alignment changed");
_Static_assert(sizeof(ObeliskApi) == 312u,
    "ObeliskApi v1 size changed; public ABI additions need an explicit consumer guard update");

_Static_assert(offsetof(ObeliskPluginInitContext, abi_version) == 0u,
    "ObeliskPluginInitContext abi_version offset changed");
_Static_assert(offsetof(ObeliskPluginInitContext, struct_size) == 4u,
    "ObeliskPluginInitContext struct_size offset changed");
_Static_assert(offsetof(ObeliskPluginInitContext, config_dir) == 8u,
    "ObeliskPluginInitContext config_dir offset changed");
_Static_assert(offsetof(ObeliskPluginInitContext, config_path) == 16u,
    "ObeliskPluginInitContext config_path offset changed");
_Static_assert(offsetof(ObeliskPluginInitContext, instance_id) == 24u,
    "ObeliskPluginInitContext instance_id offset changed");
_Static_assert(offsetof(ObeliskPluginInitContext, plugin_owner_token) == 32u,
    "ObeliskPluginInitContext owner token offset changed");
_Static_assert(OBELISK_FIELD_END(ObeliskPluginInitContext, plugin_owner_token) ==
        sizeof(ObeliskPluginInitContext),
    "plugin_owner_token must remain the last init context field");
_Static_assert(_Alignof(ObeliskPluginInitContext) == 8u,
    "ObeliskPluginInitContext alignment changed");
_Static_assert(sizeof(ObeliskPluginInitContext) == 40u,
    "ObeliskPluginInitContext size changed");

_Static_assert(offsetof(ObeliskPluginMetadata, abi_version) == 0u,
    "ObeliskPluginMetadata abi_version offset changed");
_Static_assert(offsetof(ObeliskPluginMetadata, struct_size) == 4u,
    "ObeliskPluginMetadata struct_size offset changed");
_Static_assert(offsetof(ObeliskPluginMetadata, plugin_id) == 8u,
    "ObeliskPluginMetadata plugin_id offset changed");
_Static_assert(offsetof(ObeliskPluginMetadata, name) == 16u,
    "ObeliskPluginMetadata name offset changed");
_Static_assert(offsetof(ObeliskPluginMetadata, version) == 24u,
    "ObeliskPluginMetadata version offset changed");
_Static_assert(offsetof(ObeliskPluginMetadata, config_file) == 32u,
    "ObeliskPluginMetadata config_file offset changed");
_Static_assert(offsetof(ObeliskPluginMetadata, default_config_json) == 40u,
    "ObeliskPluginMetadata default_config_json offset changed");
_Static_assert(_Alignof(ObeliskPluginMetadata) == 8u, "ObeliskPluginMetadata alignment changed");
_Static_assert(sizeof(ObeliskPluginMetadata) == 48u, "ObeliskPluginMetadata size changed");
_Static_assert(sizeof(ObeliskResourceKindDescriptor) == 136u,
    "ObeliskResourceKindDescriptor v1 fixed size changed");
_Static_assert(sizeof(ObeliskGameplayPolicyEventDescriptor) == 152u,
    "ObeliskGameplayPolicyEventDescriptor v1 fixed size changed");

static void GuardLegacyProcessEventRegister(OnProcessEventCallback callback)
{
    (void)callback;
}

static void GuardLegacyNamedProcessEventRegister(int32_t name_index, OnProcessEventCallback callback)
{
    (void)name_index;
    (void)callback;
}

static uint64_t GuardProcessEventRegisterWithOwnerTokenHandle(
    uint64_t owner_token,
    OnProcessEventCallback callback)
{
    (void)owner_token;
    (void)callback;
    return 1;
}

static uint64_t GuardNamedProcessEventRegisterWithOwnerTokenHandle(
    uint64_t owner_token,
    int32_t name_index,
    OnProcessEventCallback callback)
{
    (void)owner_token;
    (void)name_index;
    (void)callback;
    return 1;
}

static bool GuardUnregisterProcessEventWithOwnerToken(uint64_t owner_token, uint64_t registration_id)
{
    (void)owner_token;
    (void)registration_id;
    return true;
}

static void GuardGameplayPolicyEventCallback(const ObeliskGameplayPolicyEvent* event, void* user_data)
{
    (void)event;
    (void)user_data;
}

static void GuardChatMessageEventCallback(const ObeliskChatMessageEvent* event, void* user_data)
{
    (void)event;
    (void)user_data;
}

static void GuardTimerCallback(uint64_t timer_id, void* user_data)
{
    (void)timer_id;
    (void)user_data;
}

static uint64_t GuardRegisterGameplayPolicyEvent(
    uint64_t owner_token,
    uint64_t event_kind_mask,
    ObeliskGameplayPolicyEventCallback callback,
    void* user_data)
{
    (void)owner_token;
    (void)event_kind_mask;
    (void)callback;
    (void)user_data;
    return 2;
}

static bool GuardUnregisterGameplayPolicyEvent(uint64_t owner_token, uint64_t registration_id)
{
    (void)owner_token;
    (void)registration_id;
    return true;
}

static bool GuardDescribeResourceKind(uint32_t resource_kind, ObeliskResourceKindDescriptor* out)
{
    if (!out || out->struct_size < sizeof(ObeliskResourceKindDescriptor))
        return false;

    out->abi_version = OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION;
    out->struct_size = sizeof(ObeliskResourceKindDescriptor);
    out->resource_kind = resource_kind;
    out->flags = OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY |
        OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY |
        OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP;
    return true;
}

static bool GuardDescribeGameplayPolicyEventKind(uint32_t event_kind, ObeliskGameplayPolicyEventDescriptor* out)
{
    if (!out || out->struct_size < sizeof(ObeliskGameplayPolicyEventDescriptor))
        return false;

    out->abi_version = OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION;
    out->struct_size = sizeof(ObeliskGameplayPolicyEventDescriptor);
    out->event_kind = event_kind;
    out->flags = OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD;
    return true;
}

static uint64_t GuardRegisterChatMessageEvent(
    uint64_t owner_token,
    ObeliskChatMessageEventCallback callback,
    void* user_data)
{
    (void)owner_token;
    (void)callback;
    (void)user_data;
    return 3;
}

static bool GuardUnregisterChatMessageEvent(uint64_t owner_token, uint64_t registration_id)
{
    (void)owner_token;
    (void)registration_id;
    return true;
}

static uint64_t GuardRegisterTimer(
    uint64_t owner_token,
    uint64_t delay_ms,
    uint64_t interval_ms,
    uint64_t flags,
    ObeliskTimerCallback callback,
    void* user_data)
{
    (void)owner_token;
    (void)delay_ms;
    (void)interval_ms;
    (void)flags;
    (void)callback;
    (void)user_data;
    return 4;
}

static bool GuardUnregisterTimer(uint64_t owner_token, uint64_t timer_id)
{
    (void)owner_token;
    (void)timer_id;
    return true;
}

static bool GuardHasApiMetadataPrefix(const ObeliskApi* api)
{
    return api &&
        api->abi_version == OBELISK_API_ABI_VERSION &&
        api->struct_size >= offsetof(ObeliskApi, capabilities) + sizeof(api->capabilities);
}

static bool GuardApiFieldAvailable(const ObeliskApi* api, size_t field_end)
{
    return GuardHasApiMetadataPrefix(api) && api->struct_size >= field_end;
}

static bool GuardHasGlobalRawProcessEventDebugApi(const ObeliskApi* api, uint64_t owner_token)
{
    return owner_token != 0 &&
        GuardApiFieldAvailable(api, OBELISK_FIELD_END(ObeliskApi, UnregisterProcessEventCallbackWithOwnerToken)) &&
        (api->capabilities & OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS) != 0 &&
        (api->capabilities & OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES) != 0 &&
        (api->capabilities & OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS) != 0 &&
        api->RegisterPreProcessEventWithOwnerTokenHandle &&
        api->UnregisterProcessEventCallbackWithOwnerToken;
}

static bool GuardHasFilteredRawProcessEventDebugApi(const ObeliskApi* api, uint64_t owner_token)
{
    return owner_token != 0 &&
        GuardApiFieldAvailable(api, OBELISK_FIELD_END(ObeliskApi, UnregisterProcessEventCallbackWithOwnerToken)) &&
        (api->capabilities & OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS) != 0 &&
        (api->capabilities & OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES) != 0 &&
        (api->capabilities & OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS) != 0 &&
        api->RegisterPreProcessEventForNameIndexWithOwnerTokenHandle &&
        api->UnregisterProcessEventCallbackWithOwnerToken;
}

static bool GuardHasGameplayPolicyEventApi(const ObeliskApi* api, uint64_t owner_token)
{
    return owner_token != 0 &&
        GuardApiFieldAvailable(api, OBELISK_FIELD_END(ObeliskApi, UnregisterGameplayPolicyEventWithOwnerToken)) &&
        (api->capabilities & OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS) != 0 &&
        api->RegisterGameplayPolicyEventWithOwnerTokenHandle &&
        api->UnregisterGameplayPolicyEventWithOwnerToken;
}

static bool GuardHasResourceKindDescriptorApi(const ObeliskApi* api)
{
    return GuardApiFieldAvailable(api, OBELISK_FIELD_END(ObeliskApi, DescribeResourceKind)) &&
        (api->capabilities & OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS) != 0 &&
        api->DescribeResourceKind;
}

static bool GuardHasGameplayPolicyEventDescriptorApi(const ObeliskApi* api)
{
    return GuardApiFieldAvailable(api, OBELISK_FIELD_END(ObeliskApi, DescribeGameplayPolicyEventKind)) &&
        (api->capabilities & OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS) != 0 &&
        api->DescribeGameplayPolicyEventKind;
}

static bool GuardHasChatMessageEventApi(const ObeliskApi* api, uint64_t owner_token)
{
    return owner_token != 0 &&
        GuardApiFieldAvailable(api, OBELISK_FIELD_END(ObeliskApi, UnregisterChatMessageEventWithOwnerToken)) &&
        (api->capabilities & OBELISK_API_CAPABILITY_CHAT_EVENTS) != 0 &&
        api->RegisterChatMessageEventWithOwnerTokenHandle &&
        api->UnregisterChatMessageEventWithOwnerToken;
}

static bool GuardHasTimerApi(const ObeliskApi* api, uint64_t owner_token)
{
    return owner_token != 0 &&
        GuardApiFieldAvailable(api, OBELISK_FIELD_END(ObeliskApi, UnregisterTimerWithOwnerToken)) &&
        (api->capabilities & OBELISK_API_CAPABILITY_TIMERS) != 0 &&
        api->RegisterTimerWithOwnerTokenHandle &&
        api->UnregisterTimerWithOwnerToken;
}

static int GuardRawProcessEventDebugAvailability(void)
{
    ObeliskApi api = {0};
    const uint64_t owner_token = 0xC0FFEEu;

    api.RegisterPreProcessEvent = GuardLegacyProcessEventRegister;
    api.RegisterPostProcessEvent = GuardLegacyProcessEventRegister;
    api.RegisterPreProcessEventForNameIndex = GuardLegacyNamedProcessEventRegister;
    api.RegisterPostProcessEventForNameIndex = GuardLegacyNamedProcessEventRegister;
    api.abi_version = OBELISK_API_ABI_VERSION;
    api.struct_size = sizeof(ObeliskApi);
    api.capabilities = OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS;

    if (GuardHasGlobalRawProcessEventDebugApi(&api, owner_token) ||
        GuardHasFilteredRawProcessEventDebugApi(&api, owner_token))
    {
        return 1;
    }

    api.RegisterPreProcessEventWithOwnerTokenHandle =
        GuardProcessEventRegisterWithOwnerTokenHandle;
    api.RegisterPreProcessEventForNameIndexWithOwnerTokenHandle =
        GuardNamedProcessEventRegisterWithOwnerTokenHandle;
    api.UnregisterProcessEventCallbackWithOwnerToken =
        GuardUnregisterProcessEventWithOwnerToken;
    api.capabilities |= OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS |
        OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES;

    if (GuardHasGlobalRawProcessEventDebugApi(&api, owner_token) ||
        GuardHasFilteredRawProcessEventDebugApi(&api, owner_token))
    {
        return 2;
    }

    api.capabilities |= OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS;
    api.struct_size = offsetof(ObeliskApi, RegisterPreProcessEventForNameIndexWithOwnerTokenHandle);
    if (GuardHasFilteredRawProcessEventDebugApi(&api, owner_token))
        return 3;

    api.struct_size = offsetof(ObeliskApi, UnregisterProcessEventCallbackWithOwnerToken);
    if (GuardHasFilteredRawProcessEventDebugApi(&api, owner_token))
        return 4;

    api.struct_size = sizeof(ObeliskApi);
    if (!GuardHasFilteredRawProcessEventDebugApi(&api, owner_token))
        return 5;

    if (GuardHasFilteredRawProcessEventDebugApi(&api, 0))
        return 6;

    api.capabilities &= ~OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS;
    api.capabilities |= OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS;
    api.struct_size = offsetof(ObeliskApi, RegisterPreProcessEventWithOwnerTokenHandle);
    if (GuardHasGlobalRawProcessEventDebugApi(&api, owner_token))
        return 7;

    api.struct_size = offsetof(ObeliskApi, UnregisterProcessEventCallbackWithOwnerToken);
    if (GuardHasGlobalRawProcessEventDebugApi(&api, owner_token))
        return 8;

    api.struct_size = sizeof(ObeliskApi);
    if (!GuardHasGlobalRawProcessEventDebugApi(&api, owner_token))
        return 9;

    if (GuardHasGlobalRawProcessEventDebugApi(&api, 0))
        return 10;

    return 0;
}

static int GuardCopiedSurfaceAvailability(void)
{
    ObeliskApi api = {0};
    const uint64_t owner_token = 0xC0FFEEu;

    api.abi_version = OBELISK_API_ABI_VERSION;
    api.struct_size = sizeof(ObeliskApi);
    api.capabilities = 0;
    if (GuardHasGameplayPolicyEventApi(&api, owner_token) ||
        GuardHasResourceKindDescriptorApi(&api) ||
        GuardHasGameplayPolicyEventDescriptorApi(&api) ||
        GuardHasChatMessageEventApi(&api, owner_token) ||
        GuardHasTimerApi(&api, owner_token))
    {
        return 11;
    }

    api.capabilities = OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS |
        OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS |
        OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS |
        OBELISK_API_CAPABILITY_CHAT_EVENTS |
        OBELISK_API_CAPABILITY_TIMERS;
    if (GuardHasGameplayPolicyEventApi(&api, owner_token) ||
        GuardHasResourceKindDescriptorApi(&api) ||
        GuardHasGameplayPolicyEventDescriptorApi(&api) ||
        GuardHasChatMessageEventApi(&api, owner_token) ||
        GuardHasTimerApi(&api, owner_token))
    {
        return 12;
    }

    api.RegisterGameplayPolicyEventWithOwnerTokenHandle = GuardRegisterGameplayPolicyEvent;
    api.struct_size = OBELISK_FIELD_END(ObeliskApi, RegisterGameplayPolicyEventWithOwnerTokenHandle);
    if (GuardHasGameplayPolicyEventApi(&api, owner_token))
        return 13;
    api.UnregisterGameplayPolicyEventWithOwnerToken = GuardUnregisterGameplayPolicyEvent;
    api.struct_size = OBELISK_FIELD_END(ObeliskApi, UnregisterGameplayPolicyEventWithOwnerToken);
    if (GuardHasGameplayPolicyEventApi(&api, 0))
        return 14;
    if (!GuardHasGameplayPolicyEventApi(&api, owner_token))
        return 15;

    if (api.RegisterGameplayPolicyEventWithOwnerTokenHandle(
            owner_token,
            OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL,
            GuardGameplayPolicyEventCallback,
            &api) == 0)
    {
        return 16;
    }

    api.RegisterChatMessageEventWithOwnerTokenHandle = GuardRegisterChatMessageEvent;
    api.struct_size = OBELISK_FIELD_END(ObeliskApi, RegisterChatMessageEventWithOwnerTokenHandle);
    if (GuardHasChatMessageEventApi(&api, owner_token))
        return 17;
    api.UnregisterChatMessageEventWithOwnerToken = GuardUnregisterChatMessageEvent;
    api.struct_size = OBELISK_FIELD_END(ObeliskApi, UnregisterChatMessageEventWithOwnerToken);
    if (GuardHasChatMessageEventApi(&api, 0))
        return 18;
    if (!GuardHasChatMessageEventApi(&api, owner_token))
        return 19;
    if (api.RegisterChatMessageEventWithOwnerTokenHandle(
            owner_token,
            GuardChatMessageEventCallback,
            &api) == 0)
    {
        return 20;
    }

    api.RegisterTimerWithOwnerTokenHandle = GuardRegisterTimer;
    api.struct_size = OBELISK_FIELD_END(ObeliskApi, RegisterTimerWithOwnerTokenHandle);
    if (GuardHasTimerApi(&api, owner_token))
        return 21;
    api.UnregisterTimerWithOwnerToken = GuardUnregisterTimer;
    api.struct_size = OBELISK_FIELD_END(ObeliskApi, UnregisterTimerWithOwnerToken);
    if (GuardHasTimerApi(&api, 0))
        return 22;
    if (!GuardHasTimerApi(&api, owner_token))
        return 23;
    if (api.RegisterTimerWithOwnerTokenHandle(owner_token, 1, 0, 0, GuardTimerCallback, &api) == 0)
        return 24;

    api.DescribeResourceKind = GuardDescribeResourceKind;
    api.struct_size = offsetof(ObeliskApi, DescribeResourceKind);
    if (GuardHasResourceKindDescriptorApi(&api))
        return 25;
    api.struct_size = OBELISK_FIELD_END(ObeliskApi, DescribeResourceKind);
    if (!GuardHasResourceKindDescriptorApi(&api))
        return 26;

    ObeliskResourceKindDescriptor resource_descriptor = {0};
    resource_descriptor.struct_size = sizeof(resource_descriptor);
    if (!api.DescribeResourceKind(OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM, &resource_descriptor))
        return 27;
    if ((resource_descriptor.flags & OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY) == 0 ||
        (resource_descriptor.flags & OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY) == 0 ||
        (resource_descriptor.flags & OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP) == 0)
    {
        return 28;
    }

    api.DescribeGameplayPolicyEventKind = GuardDescribeGameplayPolicyEventKind;
    api.struct_size = offsetof(ObeliskApi, DescribeGameplayPolicyEventKind);
    if (GuardHasGameplayPolicyEventDescriptorApi(&api))
        return 29;
    api.struct_size = OBELISK_FIELD_END(ObeliskApi, DescribeGameplayPolicyEventKind);
    if (!GuardHasGameplayPolicyEventDescriptorApi(&api))
        return 30;

    ObeliskGameplayPolicyEventDescriptor event_descriptor = {0};
    event_descriptor.struct_size = sizeof(event_descriptor);
    if (!api.DescribeGameplayPolicyEventKind(
            OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK,
            &event_descriptor))
    {
        return 31;
    }
    if ((event_descriptor.flags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD) == 0)
        return 32;

    return 0;
}

int main(void)
{
    const int raw_result = GuardRawProcessEventDebugAvailability();
    if (raw_result != 0)
        return raw_result;
    return GuardCopiedSurfaceAvailability();
}
