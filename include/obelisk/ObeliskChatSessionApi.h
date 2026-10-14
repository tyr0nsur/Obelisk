#pragma once
#include <stddef.h>
#include <stdint.h>
#define OBELISK_CHAT_SESSION_ABI_VERSION 1u
#define OBELISK_COMMAND_WORLD_INFO_ABI_VERSION 1u
#define OBELISK_CHAT_SESSION_NAME_MAX_BYTES 256u
#define OBELISK_CHAT_SESSION_LIST_MAX 64u
#define OBELISK_CHAT_SESSION_FLAG_NAME_AVAILABLE 1ull
#define OBELISK_COMMAND_WORLD_FLAG_POSITION_AVAILABLE 1ull
#define OBELISK_COMMAND_WORLD_FLAG_TRIBE_ID_AVAILABLE 2ull
#define OBELISK_COMMAND_WORLD_FLAG_ROTATION_AVAILABLE 4ull
#define OBELISK_COMMAND_WORLD_FLAG_MOUNTED_DINO_IDS_AVAILABLE 8ull
#define OBELISK_COMMAND_WORLD_FLAG_TARGET_STRUCTURE_ID_AVAILABLE 16ull
#ifdef __cplusplus
extern "C" {
#endif
// Caller-owned copied record. Tokens identify observed chat destinations within
// this runtime only; they are not account IDs, authentication or durable handles.
// Logout/relogin invalidates old destinations. Missing names are empty/size0.
typedef struct ObeliskChatSession {
    uint32_t abi_version;
    uint32_t struct_size;
    uint64_t session_token;
    uint64_t process_epoch;
    uint64_t flags;
    char player_name[257];
    uint32_t player_name_size;
    uint32_t reserved0;
} ObeliskChatSession;
// Native values for the current command's character, never another player.
// Availability flags are checked independently. Tribe ID is a native group
// observation, not a membership/permission decision. Units are engine units.
// Values are copied on the main thread. process_epoch is not a map identifier.
typedef struct ObeliskCommandWorldInfo {
    uint32_t abi_version;
    uint32_t struct_size;
    uint64_t flags;
    float x, y, z;
    uint32_t native_tribe_id;
    float pitch, yaw, roll;
    uint32_t reserved0;
    uint64_t process_epoch;
    uint64_t session_token;
    uint32_t mounted_dino_id1, mounted_dino_id2;
    uint32_t target_structure_id;
    uint32_t reserved1;
} ObeliskCommandWorldInfo;
#ifdef __cplusplus
}
#endif
