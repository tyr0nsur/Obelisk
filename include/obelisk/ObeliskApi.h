#pragma once

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#define OBELISK_API_ABI_VERSION 1u
#define OBELISK_PLUGIN_METADATA_ABI_VERSION 1u
#define OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION 1u
#define OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS (1ull << 0)
#define OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS (1ull << 1)
#define OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS (1ull << 2)
#define OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES (1ull << 3)
#define OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT (1ull << 4)
#define OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING (1ull << 5)
#define OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS (1ull << 6)
#define OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS (1ull << 7)
#define OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS (1ull << 8)
#define OBELISK_API_CAPABILITY_CHAT_EVENTS (1ull << 9)
#define OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS (1ull << 10)
#define OBELISK_API_CAPABILITY_TIMERS (1ull << 11)
#define OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION 1u
#define OBELISK_RESOURCE_KIND_DESCRIPTOR_ABI_VERSION 1u
#define OBELISK_GAMEPLAY_POLICY_EVENT_DESCRIPTOR_ABI_VERSION 1u
#define OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION 1u
#define OBELISK_TIMER_FLAG_REPEATING (1ull << 0)
#define OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD (1ull << 0)
#define OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_STRUCTURE_BACKED (1ull << 1)
#define OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED (1ull << 2)
#define OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD (1ull << 0)
#define OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY (1ull << 0)
#define OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY (1ull << 1)
#define OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP (1ull << 2)
#define OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK (1ull << 0)
#define OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_DEMOLISH_CHECK (1ull << 1)
#define OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_VARIANT_CHANGE (1ull << 2)
#define OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACTIVATION_TOGGLE (1ull << 3)
#define OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_PIN_CODE_CHECK (1ull << 4)
#define OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_SEAT_CHECK (1ull << 5)
#define OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK (1ull << 6)
#define OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK (1ull << 7)
#define OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_ALLOW_EQUIP_ITEM_CHECK (1ull << 8)
#define OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CAN_REPAIR_CHECK (1ull << 9)
#define OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK (1ull << 10)
#define OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES \
    (OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACCESS_CHECK | \
     OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_DEMOLISH_CHECK | \
     OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_VARIANT_CHANGE | \
     OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_ACTIVATION_TOGGLE | \
     OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_PIN_CODE_CHECK | \
     OBELISK_GAMEPLAY_POLICY_EVENT_MASK_STRUCTURE_SEAT_CHECK)
#define OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY \
    (OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK | \
     OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK | \
     OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_ALLOW_EQUIP_ITEM_CHECK | \
     OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CAN_REPAIR_CHECK | \
     OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK)
#define OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL \
    (OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES | \
     OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY)
#define OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE (1ull << 0)
#define OBELISK_GAMEPLAY_POLICY_FIELD_MASK_VARIANT_INDEX (1ull << 1)
#define OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE_SET (1ull << 2)
#define OBELISK_GAMEPLAY_POLICY_FIELD_MASK_FORCE (1ull << 3)
#define OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER (1ull << 4)
#define OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN (1ull << 5)

#ifdef __cplusplus
extern "C" {
#endif

// ============================================================================
// Types
// ============================================================================

// Prototype for a function that will receive the ProcessEvent hook.
// Pre-process callbacks return true to continue execution. Returning false blocks the
// original event only when OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING is advertised;
// stable/default posture treats false as observational and continues.
// Post-process callbacks use the same ABI type, but their return value is ignored; return
// true from post callbacks for forward compatibility.
typedef bool (*OnProcessEventCallback)(void* caller, void* function, void* parms);

typedef struct ObeliskStringView {
    const char* data;
    size_t size;
} ObeliskStringView;

typedef enum ObeliskChatSendMode {
    OBELISK_CHAT_SEND_MODE_GLOBAL = 0,
    OBELISK_CHAT_SEND_MODE_TRIBE = 1,
    OBELISK_CHAT_SEND_MODE_LOCAL = 2,
    OBELISK_CHAT_SEND_MODE_ALLIANCE = 3,
} ObeliskChatSendMode;

#define OBELISK_CHAT_SEND_MODE_MIN OBELISK_CHAT_SEND_MODE_GLOBAL
#define OBELISK_CHAT_SEND_MODE_MAX OBELISK_CHAT_SEND_MODE_ALLIANCE
#define OBELISK_CHAT_SEND_MODE_COUNT 4u

typedef struct ObeliskChatMessageEvent {
    uint32_t abi_version;
    uint32_t struct_size;
    // ObeliskChatSendMode stored as uint32_t for a fixed C ABI layout.
    uint32_t send_mode;
    uint32_t reserved0;
    uint64_t flags;
    // Process-local monotonically increasing sequence for ordering observations. It is
    // not persistent identity and may reset on restart.
    uint64_t sequence;
    // UTF-8 copied message text, not NUL-termination dependent.
    ObeliskStringView message;
} ObeliskChatMessageEvent;

typedef enum ObeliskGameplayPolicyEventKind {
    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_UNKNOWN = 0,
    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACCESS_CHECK = 1,
    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_DEMOLISH_CHECK = 2,
    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_VARIANT_CHANGE = 3,
    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACTIVATION_TOGGLE = 4,
    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_PIN_CODE_CHECK = 5,
    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_SEAT_CHECK = 6,
    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK = 7,
    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK = 8,
    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK = 9,
    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK = 10,
    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK = 11,
} ObeliskGameplayPolicyEventKind;

#define OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MIN \
    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_STRUCTURE_ACCESS_CHECK
#define OBELISK_GAMEPLAY_POLICY_EVENT_KIND_MAX \
    OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK
#define OBELISK_GAMEPLAY_POLICY_EVENT_KIND_COUNT 11u

typedef enum ObeliskGameplayPolicyResourceKind {
    OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_UNKNOWN = 0,
    OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_STRUCTURE = 1,
    OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM = 2,
} ObeliskGameplayPolicyResourceKind;

typedef enum ObeliskGameplayPolicyField {
    OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE = 0,
    OBELISK_GAMEPLAY_POLICY_FIELD_VARIANT_INDEX = 1,
    OBELISK_GAMEPLAY_POLICY_FIELD_FORCE_SET = 2,
    OBELISK_GAMEPLAY_POLICY_FIELD_FORCE = 3,
    OBELISK_GAMEPLAY_POLICY_FIELD_REQUESTED_BY_PLAYER = 4,
    OBELISK_GAMEPLAY_POLICY_FIELD_IGNORE_COOLDOWN = 5,
    OBELISK_GAMEPLAY_POLICY_FIELD_COUNT = 6,
} ObeliskGameplayPolicyField;

typedef struct ObeliskGameplayPolicyEvent {
    uint32_t abi_version;
    uint32_t struct_size;
    // ObeliskGameplayPolicyEventKind stored as uint32_t for a fixed C ABI layout.
    uint32_t event_kind;
    // ObeliskGameplayPolicyResourceKind stored as uint32_t for a fixed C ABI layout.
    uint32_t resource_kind;
    // Flags describe payload ownership and evidence backing.
    uint64_t flags;
    // Bitmask of copied scalar fields present in bool_values/int32_values.
    uint64_t field_mask;
    // Boolean fields use 1ull << ObeliskGameplayPolicyField.
    uint64_t bool_values;
    // Integer fields are indexed by ObeliskGameplayPolicyField.
    int32_t int32_values[OBELISK_GAMEPLAY_POLICY_FIELD_COUNT];
} ObeliskGameplayPolicyEvent;

typedef struct ObeliskResourceKindDescriptor {
    uint32_t abi_version;
    uint32_t struct_size;
    // ObeliskGameplayPolicyResourceKind stored as uint32_t for a fixed C ABI layout.
    uint32_t resource_kind;
    uint32_t reserved0;
    // Descriptor flags define what this category is not: identity, lookup, or handle.
    uint64_t flags;
    uint64_t supported_gameplay_policy_event_mask;
    uint64_t supported_gameplay_policy_field_mask;
    // Stable ASCII identifier for config/routing/log metrics, null-terminated when set.
    char stable_name[32];
    // Human-readable ASCII label, null-terminated when set.
    char display_name[64];
} ObeliskResourceKindDescriptor;

typedef struct ObeliskGameplayPolicyEventDescriptor {
    uint32_t abi_version;
    uint32_t struct_size;
    // ObeliskGameplayPolicyEventKind stored as uint32_t for a fixed C ABI layout.
    uint32_t event_kind;
    // ObeliskGameplayPolicyResourceKind stored as uint32_t for a fixed C ABI layout.
    uint32_t resource_kind;
    // Same evidence/ownership flags used by ObeliskGameplayPolicyEvent for this kind.
    uint64_t flags;
    uint64_t event_kind_mask;
    uint64_t field_mask;
    // Stable ASCII identifier for config/routing/log metrics, null-terminated when set.
    char stable_name[48];
    // Human-readable ASCII label, null-terminated when set.
    char display_name[64];
} ObeliskGameplayPolicyEventDescriptor;

// Gameplay policy event data is callback-scope: plugins may read the copied POD
// payload during the callback only; retaining data requires a plugin-owned copy.
// This observational surface provides no identity, lookup, mutation, return
// override, or raw UE pointer access unless a future append-only API explicitly
// adds a separate decision contract.
typedef void (*ObeliskGameplayPolicyEventCallback)(const ObeliskGameplayPolicyEvent* event, void* user_data);

// Chat message event data is callback-scope: plugins may read the copied UTF-8
// payload during the callback only; retaining data requires a plugin-owned copy.
// This notification surface provides no identity, lookup, mutation, return
// override, or raw UE pointer access. It does not provide command routing,
// moderation, replies, or authoritative sender/resource identity.
typedef void (*ObeliskChatMessageEventCallback)(const ObeliskChatMessageEvent* event, void* user_data);

// Process-local timer callback. Timer ids are runtime handles only: they are not stable
// across process restarts, maps, cluster instances, or plugin reloads. Callback code must
// return quickly and must not throw across the C ABI boundary. Timer user_data is plugin
// owned; plugins must keep it valid until no timer callback using it can still be in
// flight.
typedef void (*ObeliskTimerCallback)(uint64_t timer_id, void* user_data);

typedef struct ObeliskPluginMetadata {
    uint32_t abi_version;
    uint32_t struct_size;
    // Metadata strings must point to static or plugin-owned storage that remains valid
    // until the plugin shared object is closed.
    const char* plugin_id;
    const char* name;
    const char* version;
    const char* config_file;
    const char* default_config_json;
} ObeliskPluginMetadata;

typedef struct ObeliskPluginInitContext {
    uint32_t abi_version;
    uint32_t struct_size;
    // Borrowed strings are valid only for the duration of ObeliskPlugin_Init.
    // Copy values that are needed by shutdown hooks, worker threads, or later callbacks.
    const char* config_dir;
    const char* config_path;
    const char* instance_id;
    uint64_t plugin_owner_token;
} ObeliskPluginInitContext;

// ============================================================================
// Public API Interface provided by Obelisk to Plugins
// ============================================================================
typedef struct ObeliskApi {
    // Logging functions for plugins
    void (*LogInfo)(const char* message);
    void (*LogWarn)(const char* message);
    void (*LogError)(const char* message);

    // Legacy raw ProcessEvent callback registration. These slots remain for ABI
    // compatibility and scoped debug windows only; they are not a stable SDK/module
    // surface and do not provide owner-token handles for long-lived lifecycle ownership.
    // These callbacks expose borrowed UE4 pointers and raw parameter buffers; stable
    // plugin code should use copied v0.1 ABI seeds such as GameplayPolicyEvent and
    // minimal ChatMessageEvent. Those copied seeds are promoted-experimental-only for v1
    // planning and are not a v1-complete SDK claim.
    // Global registrations are rejected unless
    // OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS is advertised. Filtered
    // registrations are rejected unless
    // OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS is advertised.
    void (*RegisterPreProcessEvent)(OnProcessEventCallback callback);
    void (*RegisterPostProcessEvent)(OnProcessEventCallback callback);
    void (*RegisterPreProcessEventForNameIndex)(int32_t nameIndex, OnProcessEventCallback callback);
    void (*RegisterPostProcessEventForNameIndex)(int32_t nameIndex, OnProcessEventCallback callback);

    // Call the original ProcessEvent trampoline for explicit UE function execution.
    //
    // Availability contract: this ABI slot is present for compatibility, but stable
    // posture rejects calls unless OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT was advertised
    // to the calling plugin and the call happens inside that plugin's init callback while
    // the live debug env+marker gate is active. Post-init calls through a captured API table
    // fail closed. Plugins must check struct_size, capabilities, and this function pointer
    // before use.
    //
    // Callback/runtime contract: copied API-table calls made after ObeliskPlugin_Init
    // fail closed because ABI v1 has no owner-token call signature. Callback-time or
    // other post-init execution needs a future owner-token ABI; stable plugins should
    // prefer higher-level APIs over direct ProcessEvent replay.
    void (*CallProcessEvent)(void* caller, void* function, void* parms);

    // ABI metadata appended for compatibility with the original function table layout.
    // Future ABI-breaking layouts should move these fields to the front with a version bump.
    uint32_t abi_version;
    uint32_t struct_size;
    uint64_t capabilities;

    // Owner-token callback registration for callbacks whose function pointer does not
    // live in the plugin shared object. Plugins must check struct_size,
    // OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS, and plugin_owner_token != 0 before
    // using these fields.
    void (*RegisterPreProcessEventWithOwnerToken)(uint64_t ownerToken, OnProcessEventCallback callback);
    void (*RegisterPostProcessEventWithOwnerToken)(uint64_t ownerToken, OnProcessEventCallback callback);
    void (*RegisterPreProcessEventForNameIndexWithOwnerToken)(uint64_t ownerToken, int32_t nameIndex, OnProcessEventCallback callback);
    void (*RegisterPostProcessEventForNameIndexWithOwnerToken)(uint64_t ownerToken, int32_t nameIndex, OnProcessEventCallback callback);

    // Handle-returning ProcessEvent callback registration. Plugins must check struct_size,
    // OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS, plugin_owner_token != 0, and
    // OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES before using these fields.
    // Name-index-filtered variants also require
    // OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS. Global variants require
    // OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS and remain debug-only.
    // A return value of 0 means the registration was rejected. Non-zero handles can be
    // passed with the same owner token to
    // UnregisterProcessEventCallbackWithOwnerToken for granular cleanup; plugin-owner
    // cleanup on unload remains the runtime backstop.
    uint64_t (*RegisterPreProcessEventWithOwnerTokenHandle)(uint64_t ownerToken, OnProcessEventCallback callback);
    uint64_t (*RegisterPostProcessEventWithOwnerTokenHandle)(uint64_t ownerToken, OnProcessEventCallback callback);
    uint64_t (*RegisterPreProcessEventForNameIndexWithOwnerTokenHandle)(uint64_t ownerToken, int32_t nameIndex, OnProcessEventCallback callback);
    uint64_t (*RegisterPostProcessEventForNameIndexWithOwnerTokenHandle)(uint64_t ownerToken, int32_t nameIndex, OnProcessEventCallback callback);
    bool (*UnregisterProcessEventCallbackWithOwnerToken)(uint64_t ownerToken, uint64_t registrationId);

    // Copied gameplay policy events. Plugins must check struct_size,
    // OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS, plugin_owner_token != 0, and these
    // function pointers before use. A return value of 0 means registration was rejected.
    // Non-zero handles are process-local and must be unregistered with the same owner token.
    uint64_t (*RegisterGameplayPolicyEventWithOwnerTokenHandle)(
        uint64_t ownerToken,
        uint64_t eventKindMask,
        ObeliskGameplayPolicyEventCallback callback,
        void* userData);
    bool (*UnregisterGameplayPolicyEventWithOwnerToken)(uint64_t ownerToken, uint64_t registrationId);

    // Metadata-only resource kind descriptors. Plugins must check struct_size,
    // OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS, and this function pointer before
    // use. This is category information for routing and plugin capability discovery only;
    // it is not object identity, lookup, persistence, or a mutable resource API. Callers
    // must initialize out->struct_size to sizeof(ObeliskResourceKindDescriptor) before use.
    bool (*DescribeResourceKind)(uint32_t resourceKind, ObeliskResourceKindDescriptor* out);

    // Metadata-only gameplay policy event descriptors. Plugins must check struct_size,
    // OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS, and this function pointer
    // before use. This is event-kind discovery for routing and plugin capability checks
    // only; it is not identity, lookup, mutation, or return-override authority. Callers
    // must initialize out->struct_size to sizeof(ObeliskGameplayPolicyEventDescriptor)
    // before use.
    bool (*DescribeGameplayPolicyEventKind)(uint32_t eventKind, ObeliskGameplayPolicyEventDescriptor* out);

    // Copied chat message notifications for plugins that parse text locally. Plugins must
    // check struct_size, OBELISK_API_CAPABILITY_CHAT_EVENTS, plugin_owner_token != 0, and
    // these function pointers before use. A return value of 0 means registration was
    // rejected. Non-zero handles are process-local and must be unregistered with the same
    // owner token.
    uint64_t (*RegisterChatMessageEventWithOwnerTokenHandle)(
        uint64_t ownerToken,
        ObeliskChatMessageEventCallback callback,
        void* userData);
    bool (*UnregisterChatMessageEventWithOwnerToken)(uint64_t ownerToken, uint64_t registrationId);

    // Process-local owner-token timers. Plugins must check struct_size,
    // OBELISK_API_CAPABILITY_TIMERS, plugin_owner_token != 0, and these function pointers
    // before use. A return value of 0 means registration was rejected. Non-zero handles
    // are process-local, owned by the registering plugin, cleaned up on plugin unload/init
    // failure, and must not be persisted to shared config or reused across ARK server
    // processes. delayMs must be non-zero. One-shot timers require intervalMs=0 and
    // flags=0. Repeating timers require OBELISK_TIMER_FLAG_REPEATING and non-zero
    // intervalMs. Reserved flags are rejected. UnregisterTimerWithOwnerToken cancels
    // future delivery for one handle, but it is not a callback quiescence barrier for
    // heap or plugin-owned userData that might already be in flight. Plugins that free
    // timer state during shutdown must provide their own synchronization or defer that
    // release until owner cleanup has quiesced callbacks. Plugin unload/init-failure
    // owner cleanup is the runtime barrier before plugin code is unmapped.
    uint64_t (*RegisterTimerWithOwnerTokenHandle)(
        uint64_t ownerToken,
        uint64_t delayMs,
        uint64_t intervalMs,
        uint64_t flags,
        ObeliskTimerCallback callback,
        void* userData);
    bool (*UnregisterTimerWithOwnerToken)(uint64_t ownerToken, uint64_t timerId);
} ObeliskApi;

// Plugins must export these functions to be loaded by Obelisk.
// Metadata is validated before initialization. The runtime creates a missing
// safe-disabled default config at:
//   ${OBELISK_CONFIG_DIR}/<plugin_id>/config.json
// default_config_json must include enabled=false, allow_all_instances=false, and an
// instance_allowlist array so clustered installs have an explicit activation envelope.
// __attribute__((visibility("default"))) bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out);
// The api and context pointers passed to ObeliskPlugin_Init are borrowed for init only.
// If a plugin needs runtime callbacks during shutdown, worker threads, or later event
// callbacks, copy only the advertised API prefix with a bounded copy and check
// struct_size/capabilities before using appended fields.
// __attribute__((visibility("default"))) bool ObeliskPlugin_Init(ObeliskApi* api, const ObeliskPluginInitContext* context);
//
// Plugins may also export this optional lifecycle hook. When present, the runtime
// calls it before unregistering plugin-owned callbacks and before dlclose.
// The hook must be idempotent and must not throw across the C ABI boundary.
// __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown();

#ifdef __cplusplus
}
#endif
