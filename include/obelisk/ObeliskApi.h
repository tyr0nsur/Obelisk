#pragma once

#include <stdint.h>
#include <stdbool.h>

#define OBELISK_API_ABI_VERSION 1u
#define OBELISK_PLUGIN_METADATA_ABI_VERSION 1u
#define OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION 1u
#define OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS (1ull << 0)
#define OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS (1ull << 1)
#define OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS (1ull << 2)
#define OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES (1ull << 3)
#define OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT (1ull << 4)

#ifdef __cplusplus
extern "C" {
#endif

// ============================================================================
// Types
// ============================================================================

// Prototype for a function that will receive the ProcessEvent hook.
// Pre-process callbacks return true to continue execution or false to block the event.
// Post-process callbacks use the same ABI type, but their return value is ignored; return
// true from post callbacks for forward compatibility.
typedef bool (*OnProcessEventCallback)(void* caller, void* function, void* parms);

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

    // Event Registration
    void (*RegisterPreProcessEvent)(OnProcessEventCallback callback);
    void (*RegisterPostProcessEvent)(OnProcessEventCallback callback);
    void (*RegisterPreProcessEventForNameIndex)(int32_t nameIndex, OnProcessEventCallback callback);
    void (*RegisterPostProcessEventForNameIndex)(int32_t nameIndex, OnProcessEventCallback callback);

    // Call the original ProcessEvent trampoline for explicit UE function execution.
    //
    // Availability contract: this ABI slot is present for compatibility, but stable
    // posture rejects calls unless OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT is advertised.
    // Plugins must check struct_size, capabilities, and this function pointer before use.
    //
    // Reentrancy contract: a pre-callback that calls this should return false. If it
    // returns true, the runtime skips the automatic original call and warns to avoid
    // double execution. Post-callback use is observationally after the original call and
    // must not attempt to replay the same event. Stable plugins should prefer future
    // higher-level APIs over direct ProcessEvent replay.
    void (*CallProcessEvent)(void* caller, void* function, void* parms);

    // ABI metadata appended for compatibility with the original function table layout.
    // Future ABI-breaking layouts should move these fields to the front with a version bump.
    uint32_t abi_version;
    uint32_t struct_size;
    uint64_t capabilities;

    // Owner-token callback registration for callbacks whose function pointer does not
    // live in the plugin shared object. Plugins must check struct_size and
    // OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS before using these fields.
    void (*RegisterPreProcessEventWithOwnerToken)(uint64_t ownerToken, OnProcessEventCallback callback);
    void (*RegisterPostProcessEventWithOwnerToken)(uint64_t ownerToken, OnProcessEventCallback callback);
    void (*RegisterPreProcessEventForNameIndexWithOwnerToken)(uint64_t ownerToken, int32_t nameIndex, OnProcessEventCallback callback);
    void (*RegisterPostProcessEventForNameIndexWithOwnerToken)(uint64_t ownerToken, int32_t nameIndex, OnProcessEventCallback callback);

    // Handle-returning ProcessEvent callback registration. Plugins must check
    // struct_size and OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES before using
    // these fields. A return value of 0 means the registration was rejected. Non-zero
    // handles can be passed with the same owner token to
    // UnregisterProcessEventCallbackWithOwnerToken for granular cleanup; plugin-owner
    // cleanup on unload remains the runtime backstop.
    uint64_t (*RegisterPreProcessEventWithOwnerTokenHandle)(uint64_t ownerToken, OnProcessEventCallback callback);
    uint64_t (*RegisterPostProcessEventWithOwnerTokenHandle)(uint64_t ownerToken, OnProcessEventCallback callback);
    uint64_t (*RegisterPreProcessEventForNameIndexWithOwnerTokenHandle)(uint64_t ownerToken, int32_t nameIndex, OnProcessEventCallback callback);
    uint64_t (*RegisterPostProcessEventForNameIndexWithOwnerTokenHandle)(uint64_t ownerToken, int32_t nameIndex, OnProcessEventCallback callback);
    bool (*UnregisterProcessEventCallbackWithOwnerToken)(uint64_t ownerToken, uint64_t registrationId);
} ObeliskApi;

// Plugins must export these functions to be loaded by Obelisk.
// Metadata is validated before initialization. The runtime creates a missing
// safe-disabled default config at:
//   ${OBELISK_CONFIG_DIR}/<plugin_id>/config.json
// default_config_json must include enabled=false, allow_all_instances=false, and an
// instance_allowlist array so clustered installs have an explicit activation envelope.
// __attribute__((visibility("default"))) bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out);
// The api and context pointers passed to ObeliskPlugin_Init are borrowed for init only.
// Copy ObeliskApi by value if the plugin needs runtime callbacks during shutdown,
// worker threads, or later event callbacks.
// __attribute__((visibility("default"))) bool ObeliskPlugin_Init(ObeliskApi* api, const ObeliskPluginInitContext* context);
//
// Plugins may also export this optional lifecycle hook. When present, the runtime
// calls it before unregistering plugin-owned callbacks and before dlclose.
// The hook must be idempotent and must not throw across the C ABI boundary.
// __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown();

#ifdef __cplusplus
}
#endif
