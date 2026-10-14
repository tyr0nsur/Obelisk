#pragma once

#include <stddef.h>
#include <stdint.h>

#define OBELISK_COMMAND_INVOCATION_ABI_VERSION 1u
#define OBELISK_COMMAND_PLAYER_ABI_VERSION 1u
#define OBELISK_COMMAND_PLAYER_FLAG_NAME_AVAILABLE (1ull << 0)
#define OBELISK_COMMAND_PLAYER_FLAG_PLATFORM_ID_AVAILABLE (1ull << 1)
#define OBELISK_COMMAND_PLAYER_NAME_MAX_BYTES 256u
#define OBELISK_COMMAND_PLAYER_PLATFORM_ID_MAX_BYTES 256u

#ifdef __cplusplus
extern "C" {
#endif

typedef struct ObeliskCommandStringView {
    const char* data;
    size_t size;
} ObeliskCommandStringView;

// A copied observation of the player originating the current command. Neither
// field is authority, authentication, a session handle, or a storefront label.
// In particular, native platform_id is an opaque UTF-8 string: its shape does
// not establish Steam/Epic provenance, uniqueness, or persistence guarantees.
// Available fields contain 1..256 valid UTF-8 bytes and no embedded NULs;
// unavailable fields have data=NULL and size=0. Names are display data, not keys.
// Views belong to the runtime and are valid only until this callback returns.
// Copy bytes into plugin-owned storage before retaining observations. A copied
// platform_id cannot authorize later lookup/reply or revive an expired token.
typedef struct ObeliskCommandPlayer {
    uint32_t abi_version;
    uint32_t struct_size;
    uint64_t flags;
    ObeliskCommandStringView player_name;
    ObeliskCommandStringView platform_id;
} ObeliskCommandPlayer;

// All fields are borrowed for the callback only. The runtime copies UTF-8 text.
// invocation_token permits a synchronous reply only while this exact callback is
// executing on the invoking thread. It expires when the callback returns and is
// rejected by nested callbacks until the original callback resumes. It is neither
// player identity nor a persistent session handle. Retaining it cannot authorize a
// reply after disconnect/reconnect. This invocation contains no UE pointers or
// identity fields; origin observations are supplied by the separate scoped getter.
typedef struct ObeliskCommandInvocation {
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t send_mode;
    uint32_t reserved0;
    uint64_t invocation_token;
    ObeliskCommandStringView command_text;
} ObeliskCommandInvocation;

// Do not throw across this ABI boundary. Replies must occur inside this callback;
// worker-thread, queued, and retained-token replies are rejected.
typedef void (*ObeliskCommandCallback)(const ObeliskCommandInvocation* invocation, void* user_data);

#ifdef __cplusplus
}
#endif
