# SDK Chat Event Ownership Plan

## Objective

Define the minimum ownership, ABI, and validation requirements before Obelisk exposes a
public plugin-facing chat event such as `OnChatMessage`.

This is a design note only. It does not promote the current experimental chat reflection
logger to public SDK behavior.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Current runtime evidence:
  `docs/research/2026-05-27-server-send-chat-runtime-hit.md`
- Current internal decoder evidence:
  `docs/research/2026-05-27-fstring-layout.md`
- Current public ABI header: `include/obelisk/ObeliskApi.h`
- Current ABI version line: `OBELISK_API_ABI_VERSION=1`

## Current Facts

- `ServerSendChatMessage` is runtime-observed for the current ARK binary hash.
- Current text decoding is instrumentation behind `OBELISK_CHAT_REFLECTION_LOG_TEXT=1`.
- Reflected parameter ranges point into the borrowed `ProcessEvent` parameter frame.
- Plugins must not receive borrowed UE4 pointers as a stable SDK contract.
- Existing plugin callback cleanup is owner-token based and must remain the pattern for any
  future chat callback registration.

## Non-Goals

- Do not add `OnChatMessage` to `ObeliskApi` yet.
- Do not expose `FString`, `UObject`, `UFunction`, or raw params to plugins.
- Do not dispatch chat callbacks from metadata-only recognizers.
- Do not treat `ServerSendChatMessage` as binary-independent.
- Do not promise player identity until caller semantics are verified.

## Proposed Future ABI Shape

Future public chat data should be copied into Obelisk-owned memory before invoking plugin
callbacks. A first version should stay small and POD-only:

```cpp
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

`ObeliskStringView` should be a POD `{const char* data, size_t size}`. All string views
should be valid only for the duration of the callback unless a future API explicitly
documents another lifetime. They must point to UTF-8 bytes owned by the runtime, not UE4
memory. Sizes should exclude any trailing NUL if one is provided.

Raw UE pointers such as `sender_controller` and `sender_primal_character` should be kept
out of the first public chat event. If sender identity needs runtime object access later,
expose it through Obelisk-owned opaque handles with explicit operations and lifetime rules
instead of raw `UObject` pointers.

## Registration Model

Prefer owner-token cleanup consistent with current ProcessEvent callback ownership:

- append registration functions to `ObeliskApi` only after deciding the ABI versioning
  strategy,
- gate new fields behind `OBELISK_API_CAPABILITY_CHAT_EVENTS` and `struct_size`,
- register callbacks only for enabled plugins,
- return an opaque `uint64_t` registration id instead of exposing runtime pointers,
- make explicit unregister idempotent,
- unregister all chat callbacks on init failure and unload,
- call optional plugin shutdown before callback owner cleanup, consistent with current
  plugin lifecycle,
- catch all plugin exceptions before returning to runtime code.

A future append-only API shape should look like:

```cpp
bool (*RegisterOnChatMessage)(
    const ObeliskChatMessageSubscription* subscription,
    uint64_t* out_registration_id
);

bool (*UnregisterCallback)(uint64_t registration_id);
```

`OnChatMessage` should start as a post-decode notification. Blocking/moderation semantics
belong in a separate future `PreChatMessage` contract after reentrancy and behavior are
understood.

## Acceptance Requirements

Before adding public ABI fields:

1. Validate runtime text logging in a controlled restart window with
   `OBELISK_CHAT_REFLECTION_LOG_TEXT=1`, then remove the text gate.
2. Confirm copied UTF-8 text contents for at least `GlobalChat`; collect more modes when
   safely available.
3. Benchmark chat reflection enabled/disabled enough to understand hot-path cost.
4. Define caller/player identity separately; do not include raw UE pointers or player
   object fields until evidence and handle lifetime rules are available.
5. Add ABI layout tests for struct size, field offsets, enum size, and appended API fields.
6. Add EventManager or dedicated dispatcher tests for registration, callback invocation,
   unregister-on-init-failure, unload cleanup, and `send_mode >= 4` rejection.
7. Add plugin fixture coverage that consumes the new API through installed SDK layout.
8. Document binary-hash validation: rerun `scripts/verify_chat_reflection_constants.py`
   before accepting chat constants on a new ARK binary.

## Hot-Path Benchmark Requirements

Measure before any SDK promotion:

- local microbenchmark for `TryIdentifyInvocation()` with synthetic readers:
  non-chat fast path, rejected chat candidate, matched `ServerSendChatMessage`, and text
  decode;
- local hook-like microbenchmark for the enabled/disabled branch, name-index read,
  recognition, send-mode check, optional text decode, and synthetic log sanitization;
- count reader calls or `Memory::IsReadable` calls per path;
- report p50/p95/p99 latency and allocation behavior for each path;
- isolated debug runtime A/B: chat reflection off, metadata-only on, text logging on;
- collect CPU, RSS, log rate, candidate/reject/match counters, and any tick/hitch signal
  available from the harness.

Reject promotion if non-chat cost is dominated by readability checks, if rejected
candidates produce a log storm, or if p99/runtime tick behavior changes materially in the
isolated validation run.

The local helper target is intentionally excluded from the default build:

```bash
cmake --build build --target chat_reflection_benchmark
./build/chat_reflection_benchmark 100000
```

It uses synthetic memory only and must not be treated as a replacement for isolated runtime
A/B validation.

Initial local run after adding the helper:

```text
./build/chat_reflection_benchmark 50000
non_chat_filter ns_per_iter=45 reader_calls_per_iter=0
server_send_chat_match ns_per_iter=629 reader_calls_per_iter=53
server_send_chat_decode_utf32 ns_per_iter=31 reader_calls_per_iter=1
```

This measures the recognizer helper after a caller already has a `nameIndex`; it does not
include the hook-side `GetFunctionNameIndex()` / `Memory::IsReadable()` cost paid when chat
reflection is enabled. That cost still needs an isolated runtime A/B measurement.

Follow-up audit promoted a local improvement: the helper should also report tail latency
and hook-like cases, because an average-only recognizer measurement is not enough for SDK
promotion gates. The helper can approximate the hook branch locally, but real
`/proc/self/maps` readability checks, logging backend cost, and server tick impact still
require isolated runtime A/B validation.

Follow-up local run after adding percentiles and hook-like cases:

```text
./build/chat_reflection_benchmark 50000
non_chat_filter ns_avg=25 ns_p50=30 ns_p95=30 ns_p99=40 reader_calls_per_iter=0 allocations=0 allocations_per_iter=0
server_send_chat_match ns_avg=437 ns_p50=431 ns_p95=450 ns_p99=471 reader_calls_per_iter=53 allocations=150000 allocations_per_iter=3
server_send_chat_decode_utf32 ns_avg=238 ns_p50=231 ns_p95=241 ns_p99=381 reader_calls_per_iter=1 allocations=150000 allocations_per_iter=3
hook_like_disabled ns_avg=35 ns_p50=31 ns_p95=40 ns_p99=41 reader_calls_per_iter=0 allocations=0 allocations_per_iter=0
hook_like_enabled_non_chat ns_avg=33 ns_p50=30 ns_p95=40 ns_p99=41 reader_calls_per_iter=1 allocations=0 allocations_per_iter=0
hook_like_server_send_chat ns_avg=459 ns_p50=451 ns_p95=481 ns_p99=501 reader_calls_per_iter=54 allocations=150000 allocations_per_iter=3
hook_like_server_send_chat_text ns_avg=904 ns_p50=901 ns_p95=932 ns_p99=942 reader_calls_per_iter=55 allocations=350000 allocations_per_iter=7
```

Interpretation: the synthetic non-chat enabled path adds one name-index readability check;
the disabled and non-chat paths now stay allocation-free; reserving reflected parameter
and field vectors, then replacing the property-cycle `unordered_set` with a reserved
linear vector, reduced matched-chat temporary allocations from seven to three per
iteration. The fixture text intentionally exceeds small-string optimization storage, so
text decode now shows three allocations and the hook-like text path shows seven
allocations per iteration. These are local regression signals only, not runtime acceptance
evidence.

## Risks

- Borrowed UE4 memory crossing the ABI would create use-after-return risks.
- Decoding text in the `ProcessEvent` hot path can add overhead if left enabled broadly.
- Chat event semantics may differ by mode or caller object.
- ARK binary updates can invalidate FName indices, property offsets, or `FString` layout.
- Exposing too much too early would make later ABI cleanup harder.

## Next Steps

- Keep the current code as instrumentation.
- Run a controlled text-logging validation only when operator-approved.
- Draft ABI additions only after copied text and callback lifetime tests are designed.
- Keep Discord/community messaging explicit: chat SDK events are a future goal, not current
  public API.
