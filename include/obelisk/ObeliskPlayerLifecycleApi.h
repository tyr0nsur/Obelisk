#pragma once

#include <stddef.h>
#include <stdint.h>

#define OBELISK_PLAYER_LIFECYCLE_EVENT_ABI_VERSION 1u
#define OBELISK_PLAYER_LIFECYCLE_KIND_LOGIN_OBSERVED 1u
#define OBELISK_PLAYER_LIFECYCLE_KIND_LOGOUT_OBSERVED 2u

#define OBELISK_PLAYER_LIFECYCLE_FLAG_NAME_AVAILABLE (1ull << 0)
#define OBELISK_PLAYER_LIFECYCLE_FLAG_PLATFORM_ID_AVAILABLE (1ull << 1)
#define OBELISK_PLAYER_LIFECYCLE_FLAG_OWNER_CLASS_VALIDATED (1ull << 2)
#define OBELISK_PLAYER_LIFECYCLE_FLAG_CONTROLLER_CLASS_VALIDATED (1ull << 3)
#define OBELISK_PLAYER_LIFECYCLE_FLAG_MAIN_THREAD (1ull << 4)
#define OBELISK_PLAYER_LIFECYCLE_FLAG_ORIGINAL_CALLED (1ull << 5)
#define OBELISK_PLAYER_LIFECYCLE_FLAG_NET_CONNECTION_AVAILABLE (1ull << 6)
#define OBELISK_PLAYER_LIFECYCLE_FLAGS_SUPPORTED_MASK ((1ull << 7) - 1)

#define OBELISK_PLAYER_LIFECYCLE_NAME_MAX_BYTES 256u
#define OBELISK_PLAYER_LIFECYCLE_PLATFORM_ID_MAX_BYTES 256u

#ifdef __cplusplus
extern "C" {
#endif

typedef struct ObeliskPlayerLifecycleStringView {
    const char* data;
    size_t size;
} ObeliskPlayerLifecycleStringView;

// An observation from the verified native adapter, not an authentication result
// or a persistent player/session identity. LOGIN_OBSERVED is delivered after the
// original post-login notification returns; LOGOUT_OBSERVED is delivered before
// the original logout notification. Neither kind promises exactly-once delivery.
// Identity and connection availability describe data copied at notification entry.
// ORIGINAL_CALLED means that the original login notification returned normally;
// it is absent for the logout-entry observation. Owner/controller validation and
// main-thread flags describe adapter checks, not permissions or player authority.
// sequence and process_epoch order observations within a running process. They
// are not lookup, reply, session, or persistent identity tokens.
typedef struct ObeliskPlayerLifecycleEvent {
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t kind;
    uint32_t reserved0;
    uint64_t flags;
    uint64_t sequence;
    uint64_t process_epoch;
    // Available fields contain 1..256 valid UTF-8 bytes without embedded NULs.
    // Unavailable fields have data=NULL and size=0. Names are display data; the
    // native platform ID is opaque and does not establish Steam/Epic provenance,
    // uniqueness, persistence, or authority. Missing/malformed fields remain
    // unavailable instead of preventing the lifecycle observation.
    ObeliskPlayerLifecycleStringView player_name;
    ObeliskPlayerLifecycleStringView platform_id;
} ObeliskPlayerLifecycleEvent;

// The event and its strings belong to the runtime and are valid only during this
// callback. Copy bytes before retaining data; copying the struct retains borrowed
// pointers. No UE pointers or gameplay/reply authorization are exposed. Callbacks
// run synchronously on the observed game thread and must return quickly and not
// throw across the C ABI. user_data remains plugin-owned. Self-unregister cancels
// future delivery but does not allow freeing data used by the current callback;
// owner cleanup must drain callbacks before plugin code/data is released.
typedef void (*ObeliskPlayerLifecycleCallback)(const ObeliskPlayerLifecycleEvent* event, void* user_data);

#ifdef __cplusplus
}
#endif
