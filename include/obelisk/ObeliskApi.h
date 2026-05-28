#pragma once

#include <stdint.h>
#include <stdbool.h>

#define OBELISK_API_ABI_VERSION 1u
#define OBELISK_PLUGIN_METADATA_ABI_VERSION 1u
#define OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION 1u
#define OBELISK_API_CAPABILITY_PLUGIN_OWNED_CALLBACKS (1ull << 0)
#define OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS (1ull << 1)

#ifdef __cplusplus
extern "C" {
#endif

// ============================================================================
// Types
// ============================================================================

// Prototype for a function that will receive the ProcessEvent hook
// Returns true if the event should continue execution, false to block it.
typedef bool (*OnProcessEventCallback)(void* caller, void* function, void* parms);

struct ObeliskPluginMetadata {
    uint32_t abi_version;
    uint32_t struct_size;
    const char* plugin_id;
    const char* name;
    const char* version;
    const char* config_file;
    const char* default_config_json;
};

struct ObeliskPluginInitContext {
    uint32_t abi_version;
    uint32_t struct_size;
    const char* config_dir;
    const char* config_path;
    const char* instance_id;
};

// ============================================================================
// Public API Interface provided by Obelisk to Plugins
// ============================================================================
struct ObeliskApi {
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
    // Reentrancy contract: do not call this from a ProcessEvent callback unless the
    // callback returns false to block the detour's automatic original call. Calling it
    // from a pre-callback and then returning true can execute the same UE function twice.
    // Post-callback use is observationally after the original call and must not attempt
    // to replay the same event. Stable plugins should prefer future higher-level APIs
    // over direct ProcessEvent replay.
    void (*CallProcessEvent)(void* caller, void* function, void* parms);

    // ABI metadata appended for compatibility with the original function table layout.
    // Future ABI-breaking layouts should move these fields to the front with a version bump.
    uint32_t abi_version;
    uint32_t struct_size;
    uint64_t capabilities;
};

// Plugins must export these functions to be loaded by Obelisk.
// Metadata is validated before initialization. The runtime creates a missing
// safe-disabled default config at:
//   ${OBELISK_CONFIG_DIR}/<plugin_id>/config.json
// __attribute__((visibility("default"))) bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out);
// __attribute__((visibility("default"))) bool ObeliskPlugin_Init(ObeliskApi* api, const ObeliskPluginInitContext* context);
//
// Plugins may also export this optional lifecycle hook. When present, the runtime
// calls it before unregistering plugin-owned callbacks and before dlclose.
// The hook must be idempotent and must not throw across the C ABI boundary.
// __attribute__((visibility("default"))) void ObeliskPlugin_Shutdown();

#ifdef __cplusplus
}
#endif
