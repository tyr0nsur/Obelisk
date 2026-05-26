#pragma once

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// ============================================================================
// Types
// ============================================================================

// Prototype for a function that will receive the ProcessEvent hook
// Returns true if the event should continue execution, false to block it.
typedef bool (*OnProcessEventCallback)(void* caller, void* function, void* parms);

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

    // Call Original ProcessEvent (for executing UE functions)
    void (*CallProcessEvent)(void* caller, void* function, void* parms);
};

// Plugins must export this function to be loaded by Obelisk
// __attribute__((visibility("default"))) bool ObeliskPlugin_Init(ObeliskApi* api);

#ifdef __cplusplus
}
#endif
