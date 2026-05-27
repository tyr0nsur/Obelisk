# Chat SDK ABI Preflight

## Objective

Define the test-first contract for a future public `OnChatMessage` SDK event without
adding the event to `include/obelisk/ObeliskApi.h` yet.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Current public ABI: `include/obelisk/ObeliskApi.h`
- Current ABI version: `OBELISK_API_ABI_VERSION=1`
- Related plan: `docs/research/2026-05-27-sdk-chat-event-ownership-plan.md`
- Related performance helper: `chat_reflection_benchmark`

## Contract Draft

The first public chat event must be an Obelisk-level event, not a UE4 object exposure.

Minimum public shapes, once promoted:

```cpp
typedef struct ObeliskStringView {
    const char* data;
    size_t size;
} ObeliskStringView;

typedef enum ObeliskChatSendMode : uint32_t {
    OBELISK_CHAT_SEND_MODE_GLOBAL = 0,
    OBELISK_CHAT_SEND_MODE_TRIBE = 1,
    OBELISK_CHAT_SEND_MODE_LOCAL = 2,
    OBELISK_CHAT_SEND_MODE_ALLIANCE = 3,
} ObeliskChatSendMode;

typedef struct ObeliskChatMessage {
    uint32_t abi_version;
    uint32_t struct_size;
    uint64_t flags;
    ObeliskStringView message;
    ObeliskStringView sender_name;
    ObeliskStringView sender_platform_id;
    uint32_t send_mode;
    int32_t sender_name_index;
} ObeliskChatMessage;

typedef void (*ObeliskOnChatMessageCallback)(
    const ObeliskChatMessage* message,
    void* user_data
);

typedef struct ObeliskChatMessageSubscription {
    uint32_t abi_version;
    uint32_t struct_size;
    uint64_t flags;
    ObeliskOnChatMessageCallback callback;
    void* user_data;
} ObeliskChatMessageSubscription;
```

Do not include `UObject*`, `FString`, `UFunction*`, raw `ProcessEvent` params, or borrowed
UE4 memory in these structs.

## ABI Test Plan

Before any header promotion, add layout tests in `tests/abi/AbiLayoutTests.cpp` for:

- `ObeliskStringView`: standard layout, trivial, trivially copyable, pointer then `size_t`.
- `ObeliskChatSendMode`: exactly `uint32_t`.
- `ObeliskChatMessage`: standard layout, version and size first, no raw UE pointer fields.
- `ObeliskChatMessageSubscription`: version and size first, callback pointer plus
  `user_data`.
- capability bit: `OBELISK_API_CAPABILITY_CHAT_EVENTS` must not overlap existing bits.
- appended API functions: `RegisterOnChatMessage` and unregister path must be appended only
  after the current v1 function table and guarded by `struct_size`.

The test should fail compilation if the layout is changed without explicitly updating the
ABI note and version strategy.

## Runtime Test Plan

Before dispatch is connected to `ProcessEvent`:

- Unit-test a dedicated chat dispatcher with copied UTF-8 text stored in runtime-owned
  memory for callback duration. Implemented internally by `core/ChatEventDispatcher.*`
  and covered by `ChatEventDispatcherTests`.
- Verify callback receives valid data during the call and no borrowed UE4 param pointer
  crosses the ABI. Covered by `TestDispatchCopiesInputForCallbackDuration`.
- Verify `send_mode` accepts only `0..3` and rejects `>=4`. Covered by
  `TestRejectsUnknownSendMode`.
- Verify register returns an opaque `uint64_t` id. Covered by registration tests.
- Verify unregister is idempotent. Covered by `TestUnregisterIsIdempotent`.
- Verify plugin init failure, explicit unload, and shutdown cleanup remove callbacks.
  Owner cleanup is covered internally by `TestOwnerCleanup`; PluginManager integration is
  covered by `PluginManagerTests` with an injected `ChatEventDispatcher`.
- Verify plugin exceptions are caught before returning to runtime code. Covered by
  `TestExceptionsDoNotStopDispatch`.
- Keep a dispatch mutex held across callback invocation so plugin owner cleanup cannot
  remove callbacks and `dlclose` a plugin while a copied callback is still executing. This
  mirrors `EventManager` lifecycle protection.
- Verify installed SDK consumer can compile and load a plugin using the chat declarations.
  Pending until the public SDK header is intentionally promoted.

## Promotion Gates

The public API should remain blocked until all are true:

- Local benchmark keeps disabled and non-chat paths allocation-free.
- Matched chat and text decode allocation costs are either reduced with bounded storage or
  explicitly accepted with isolated runtime A/B evidence.
- Controlled runtime text validation confirms copied UTF-8 contents for at least
  `GlobalChat`.
- Isolated runtime A/B captures chat reflection off, metadata-only on, and text logging on.
- Binary-hash validation is rerun with `scripts/verify_chat_reflection_constants.py` for
  the target ARK server build.

## Result

This is a preflight checklist, not an ABI change. The internal dispatcher test foundation
exists, but `include/obelisk/ObeliskApi.h` remains unchanged until ABI layout tests,
plugin-manager integration, installed SDK consumer coverage, and isolated runtime
validation are ready.

## Next Steps

- Keep reducing or bounding the current matched-chat/text temporary allocations.
- Integrate dispatcher registration with plugin owner resolution only after the public ABI
  shape and capability gate are ready.
- Do not expose sender object identity until Obelisk-owned handles and lifetime rules are
  designed.
