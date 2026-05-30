# Runtime Chat Reflection Plan

> Historical/superseded chat observer plan: do not execute marker commands from this note
> directly. Current runtime-observation work is module-first, requires explicit
> operator-approved `arkserver2` / TheIsland windows, and requires shutting it down after
> the scoped test. Keep `arkserver` / Ragnarok untouched while users are active.
>
> This note is preserved as evidence for earlier chat-specific research. It is not the
> current product strategy, release plan, or public SDK plan. Chat must not become the
> center of the project again: the active direction is core-first runtime/ABI stability,
> with any gameplay or chat surface promoted only through named gates.

## Historical Objective

This note originally defined a safe runtime path from reflected offline chat evidence to a
bounded `ProcessEvent` chat filter.

## Current Flow

`ProcessEvent_Detour` in `hooks/ProcessEventHook.cpp` currently:

1. increments a call counter;
2. optionally traces the call;
3. checks whether pre/post callbacks exist;
4. reads `function->NamePrivate.ComparisonIndex`;
5. dispatches callbacks filtered only by FName index;
6. calls the original `ProcessEvent`;
7. dispatches post callbacks.

The safest insertion point is after FName extraction and before pre callback dispatch. At
that point `object`, `function`, and `params` are still borrowed pointers from the active
`ProcessEvent` frame, and no plugin ABI change is required.

## Proposed Internal Helper

Add an internal helper, not a public SDK surface:

```text
UE::TryIdentifyReflectedChatFunction(function, params) -> optional ChatInvocation
```

The first building block now exists as `ue/RuntimeReflection.{h,cpp}`. It provides a
binary-hash-gated internal reader for `UObject`, `UFunction`, `UProperty`, bounded
parameter ranges, and inert `FString` header helpers. It is not wired into
`ProcessEvent_Detour` yet.

The chat-specific recognizer now exists as `ue/ChatReflection.{h,cpp}`. It recognizes
`ServerChat`, `ServerChatTo`, `ServerChatToPlayer`, `ServerSendChatMessage`, and three
exact `ShooterPlayerController` fallback candidates by FName index plus reflected
property-chain shape. It can return borrowed parameter ranges when `params` is provided.
It still does not decode `FString` contents.

`ProcessEvent_Detour` now has experimental observation wiring. It is disabled unless both
environment variables are present:

```text
OBELISK_ENABLE_CHAT_REFLECTION=1
OBELISK_CHAT_REFLECTION_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
```

When enabled, it cheaply filters by chat FName index, validates the reflected chat shape,
and logs only function/field metadata and borrowed parameter ranges. Metadata-only
fallback candidates log `metadata_only=true`. It does not decode text, call plugins,
expose ABI, or hook native exec pointers.

Historical LinuxGSM wrapper marker example, preserved for evidence only and not to be run
from this note:

```bash
touch /servidor/ark/obelisk/state/instances/arkserver2/enable-chat-reflection
```

The marker sets `OBELISK_ENABLE_CHAT_REFLECTION=1`, the current supported binary SHA, and
`OBELISK_CHAT_REFLECTION_LOG_LIMIT=0`. Chat now matches the general candidate-observer
policy: the marker opens the gate, but a debug window must set an explicit positive budget
before the runtime reads or logs reflected fields.

Historically, this marker was restricted to the approved debug/development target from
the then-current handoff. In current work, use the active release/readiness checklist and
fresh operator approval instead; keep shared/player-facing instances out of runtime
validation unless the operator opens a specific maintenance window.

The final chat helper should build on that module and:

- reject null or unreadable pointers;
- reject unknown FName indices before doing deeper checks;
- verify `function` still looks like a `UFunction`;
- verify `FunctionFlags`, `NumParms`, `ParmsSize`, `ReturnValueOffset`;
- walk `UStruct.Children +0x38` through `UField.Next +0x28`;
- verify each `UProperty` has the expected owner, class, name, `ElementSize`, and
  `Offset_Internal`;
- only expose borrowed param offsets and sizes to runtime code;
- avoid plugin-visible UE structs until the ABI is intentionally extended.

## First Chat Targets

From `docs/research/2026-05-27-core-ufunction-property-chain.md`:

- `ServerChat`
  - FName index `9619`
  - `NumParms=1`, `ParmsSize=0x10`
  - `StrProperty MessageText`, offset `0x0`, size `0x10`
- `ServerChatTo`
  - FName index `9620`
  - `NumParms=2`, `ParmsSize=0x20`
  - `StrProperty SteamID`, offset `0x0`, size `0x10`
  - `StrProperty MessageText`, offset `0x10`, size `0x10`
- `ServerChatToPlayer`
  - FName index `9621`
  - `NumParms=2`, `ParmsSize=0x20`
  - `StrProperty PlayerName`, offset `0x0`, size `0x10`
  - `StrProperty MessageText`, offset `0x10`, size `0x10`

These `ServerChat*` targets are now treated as cheat-manager command coverage, not proof
of normal player chat.

Historical normal-player-chat target:

- `ServerSendChatMessage`
  - FName index `2697`
  - outer: `ShooterPlayerController`
  - `NumParms=2`, `ParmsSize=0x11`
  - `StrProperty ChatMessage`, offset `0x0`, size `0x10`
  - `ByteProperty SendMode`, offset `0x10`, size `0x1`
  - `SendMode` accepted values: `0..3`

Current metadata-only fallback targets:

- `ClientChatMessage`
  - FName index `1865`
  - outer: `ShooterPlayerController`
  - `NumParms=1`, `ParmsSize=0x90`
  - `StructProperty Chat`, offset `0x0`, size `0x90`
- `ClientServerChatDirectMessage`
  - FName index `1983`
  - outer: `ShooterPlayerController`
  - `NumParms=3`, `ParmsSize=0x21`
  - `StrProperty MessageText`, `StructProperty MessageColor`, `BoolProperty bIsBold`
- `ClientServerChatMessage`
  - FName index `1984`
  - outer: `ShooterPlayerController`
  - same reflected shape as `ClientServerChatDirectMessage`

These fallback targets are observation-only. They must not dispatch plugin events or
decode text until a real runtime capture proves they are the path we need.

## Runtime Rules

- Keep this gated behind an explicit experimental config or environment flag.
- Do not scan GObjects in the detour.
- Do not resolve arbitrary names in the detour unless a cheap cached resolver exists.
- Do not hook native exec pointers.
- Do not expose `UFunction*`, `UProperty*`, or raw offsets to plugins yet.
- Do not cache borrowed `params` pointers.
- Keep any logging rate-limited.
- Decode `FString` only after the reflected offset and `ParmsSize` checks pass.
- Do not dispatch events from `metadata_only=true` recognizers.

## Historical Plugin ABI Sketch

This section records a historical sketch from the chat-observer phase. Do not treat it as
a standalone SDK promotion plan. Any public chat or gameplay event surface must remain
append-only, copied-data-only, and explicitly promoted through the current release/public
SDK gates rather than by following this note alone.

That sketch expected any later public chat event API to remain append-only and passive:

- add a capability bit such as `OBELISK_API_CAPABILITY_CHAT_EVENTS`;
- add a POD `ObeliskChatMessageEvent` containing copied data only;
- add `RegisterChatMessage` as the final field of `ObeliskApi`;
- copy decoded UTF-8 text into runtime-owned event storage before invoking plugins;
- expose `send_mode`, text length, and a monotonic sequence number at most for the first
  public version.

Do not expose `UObject*`, `UFunction*`, `params`, `FString.Data`, borrowed ranges, offsets,
FName indices, object indices, controller pointers, SteamID, tribe, sender identity,
blocking/modification, or send/reply helpers yet. `oBaseEvents` should eventually consume
this API behind `chat_message.enabled=false` by default and log mode/length rather than
message text.

## Tests To Add

- `RuntimeReflectionTests` currently cover disabled/unsupported gates, bounded property
  chains, `ParmsSize` bounds, owner mismatch rejection, borrowed parameter ranges, and
  inert `FString` header parsing.
- `ChatReflectionTests` cover valid `ServerChat`, `ServerChatTo`, `ServerChatToPlayer`,
  `ServerSendChatMessage`, and metadata-only fallback shapes; same-FName wrong shapes;
  wrong property names; wrong property classes; and disabled/unsupported gates.
- `ProcessEventChatReflectionTests` cover the extracted hook helper gates and ensure
  disabled/chat-unmatched paths avoid memory reads while valid chat invocations return borrowed
  parameter ranges.
- `scripts/verify_chat_reflection_constants.py` compares `ue/ChatReflection.cpp`
  constants to offline core UFunction/property-chain evidence for all seven current
  targets. It also checks `ServerSendChatMessage` native exec candidate `0x154a600`,
  executable segment membership, and `EChatSendMode` enum names through the
  `ByteProperty SendMode` enum pointer. It should stay in the promotion path for any new
  ARK binary hash or new core dump before runtime wiring is widened.
- Still needed: a runtime smoke test with one real in-game chat message.

## Historical Next Step

This was the next step for the historical observer plan, not a current action item. Do not
activate servers or marker gates from this note without a fresh operator-approved window
and the current release/readiness checklist.

The deployed runtime had the `ServerSendChatMessage` recognizer and metadata-only
fallback recognizers enabled behind the chat reflection gate. The historical validation
step was to write one in-game chat message on the debug server and check for:

- `Reflected chat ProcessEvent ... function=ServerSendChatMessage ... metadata_only=false`
- or exact fallback lines with `metadata_only=true`

If `ServerSendChatMessage` appears with known `SendMode`, the next implementation step is
experimental text decoding in logs. Public plugin ABI should wait until that path is
proven with tests listed above.
