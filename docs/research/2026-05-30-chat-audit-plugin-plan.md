# Chat Audit Plugin Plan

## Objective

Define the smallest safe post-rc.2 implementation slice for a first-party value plugin
that uses only existing copied public APIs and process-local Obelisk timers.

This is planning only. It does not request runtime/API changes, server validation, marker
changes, C++ edits in this round, or any expansion of the public SDK.

## Decision

Recommend `oChatAudit` as the first slice.

`oChatAudit` should subscribe to the existing minimal copied `ChatMessageEvent` surface,
aggregate process-local counters, and use the existing owner-token timer API to emit a
bounded periodic digest. This provides practical operator-facing value while staying inside
the current v0.1 boundary: no raw chat text in logs, no sender identity, no permissions, no
chat response path, no moderation, no mutation, no raw `ProcessEvent`, and no UE object
access.

`oPolicyDigest` is still reasonable, but it depends on `GameplayPolicyEvent` descriptor
routing and policy-event semantics. That is a larger first value-plugin slice than chat
metadata counting because it has more event kinds, field masks, and category language to
avoid over-claiming.

## First Implementation Files

Owned source/build files:

- `plugins/oChatAudit/oChatAudit.cpp`
- `plugins/oChatAudit/CMakeLists.txt`

Small integration edits:

- top-level `CMakeLists.txt`: include `plugins/oChatAudit` only under
  `OBELISK_BUILD_EXPERIMENTAL_PLUGINS`
- `plugins/README.md`: list `oChatAudit` as experimental and document non-claims
- optional later user-facing doc: `docs/oChatAudit.md`

Tests:

- `tests/sdk_consumer/SdkConsumerFixture.cpp`
- `tests/sdk_consumer/CMakeLists.txt`

Do not edit `include/obelisk/ObeliskApi.h`, runtime dispatchers, hook code, plugin manager,
timer manager, server wrappers, install markers, or live server state for this slice.

## Config Defaults

Default config must be safe-disabled and cluster-scoped:

```json
{
  "enabled": false,
  "allow_all_instances": false,
  "instance_allowlist": [],
  "chat_audit": {
    "enabled": false,
    "digest_interval_ms": 60000,
    "log_on_shutdown": true,
    "max_message_size_bucket": 4096
  }
}
```

Validation rules:

- `enabled`, `allow_all_instances`, and `chat_audit.enabled` must be booleans.
- `instance_allowlist` entries must be safe `OBELISK_INSTANCE_ID` tokens.
- `digest_interval_ms` must be a bounded positive integer when `chat_audit.enabled=true`.
- `max_message_size_bucket` must be a bounded positive integer.
- Invalid explicitly enabled audit config fails closed instead of silently disabling.

## Runtime Shape

Initialization:

1. Validate `ObeliskApi` ABI, `struct_size`, copied chat capability, timer capability, and
   non-zero `plugin_owner_token`.
2. Copy `ObeliskApi` by value for shutdown/timer callback use.
3. Parse config from `context->config_path`.
4. If runtime activation or `chat_audit.enabled` is false, return success without callback
   or timer registration.
5. Register `ChatMessageEvent` with owner-token handle.
6. Register one repeating process-local timer with owner-token handle.

Callbacks:

- Chat callback validates event ABI, struct size, send mode, copied-payload flag, sequence,
  and message span.
- It updates atomics or mutex-protected process-local counters only.
- It does not log raw `event->message.data` or copy/store message text.
- Timer callback snapshots and resets counters, then logs one bounded digest line.

Shutdown:

- Unregister timer first to stop new digest callbacks.
- Unregister chat callback.
- Optionally emit a final digest if `log_on_shutdown=true`.
- Reset process-local state.
- Catch all exceptions before returning across the C ABI.

## Test Slice

Add SDK fixture coverage for `oChatAudit`:

- default config succeeds and registers no chat callback or timer;
- active config registers exactly one chat callback and one repeating timer;
- active config rejects missing chat capability before registration;
- active config rejects missing timer capability before registration;
- active config rejects zero owner token;
- active config unregisters both handles on shutdown;
- failed chat registration leaves no timer registered;
- failed timer registration unregisters the already-registered chat callback;
- dispatched valid chat events plus a timer fire produce a digest log with only counts,
  send modes, byte sizes/buckets, and no raw chat text;
- malformed chat events are ignored or counted without logging raw payload text;
- double shutdown is idempotent.

The existing fixture already has fake chat dispatch, fake timer dispatch, registration
failure toggles, and log capture. The first code change should extend those utilities
instead of adding a new runtime harness.

## Explicit Non-Claims

`oChatAudit` is not:

- a chat command SDK;
- a moderation, blocking, mutation, reply, or return-override path;
- a sender/player/tribe/admin identity or permission system;
- a raw `FString`, raw params, FName/GObjects, `UObject`, or `UFunction` exposure;
- a cross-process or persistent cluster audit database;
- a gameplay timer, shared scheduler, or durable timer handle;
- evidence that any richer chat API is promoted.

All handles, counters, and digest timing are process-local. The plugin may be useful on
one ARK process at a time, but it must not imply correlation across instances sharing the
same plugin binary or config root.
