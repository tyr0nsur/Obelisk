# Runtime Chat Reflection Plan

## Objective

Define the first safe runtime path from reflected offline chat evidence to a bounded
`ProcessEvent` chat filter.

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
`ServerChat`, `ServerChatTo`, and `ServerChatToPlayer` by FName index plus reflected
property-chain shape, and can return borrowed parameter ranges when `params` is provided.
It still does not decode `FString` contents and is not wired into the hook yet.

`ProcessEvent_Detour` now has experimental observation wiring. It is disabled unless both
environment variables are present:

```text
OBELISK_ENABLE_CHAT_REFLECTION=1
OBELISK_CHAT_REFLECTION_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
```

When enabled, it cheaply filters by chat FName index, validates the reflected chat shape,
and logs only function/field metadata and borrowed parameter ranges. It does not decode
text, call plugins, expose ABI, or hook native exec pointers.

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

## Runtime Rules

- Keep this gated behind an explicit experimental config or environment flag.
- Do not scan GObjects in the detour.
- Do not resolve arbitrary names in the detour unless a cheap cached resolver exists.
- Do not hook native exec pointers.
- Do not expose `UFunction*`, `UProperty*`, or raw offsets to plugins yet.
- Do not cache borrowed `params` pointers.
- Keep any logging rate-limited.
- Decode `FString` only after the reflected offset and `ParmsSize` checks pass.

## Tests To Add

- `RuntimeReflectionTests` currently cover disabled/unsupported gates, bounded property
  chains, `ParmsSize` bounds, owner mismatch rejection, borrowed parameter ranges, and
  inert `FString` header parsing.
- `ChatReflectionTests` cover valid `ServerChat`, `ServerChatTo`, and
  `ServerChatToPlayer` shapes; same-FName wrong shapes; wrong property names; wrong
  `StrProperty` class; and disabled/unsupported gates.
- Still needed: hook-level dispatch tests for the new observation path.

## Next Step

Deploy to an isolated debug server with the two environment gates above and
`OBELISK_CHAT_REFLECTION_LOG_LIMIT` set to a small value. Then write one chat message and
check for `Reflected chat ProcessEvent` log entries.
