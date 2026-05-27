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
- Still needed: named chat target validation for `ServerChat`, `ServerChatTo`, and
  `ServerChatToPlayer` shapes, plus hook-level dispatch tests once the helper is wired
  into `ProcessEvent_Detour`.

## Next Step

Implement the chat-specific target recognizer on top of `ue/RuntimeReflection`, then wire
it into `ProcessEvent_Detour` only after tests prove the recognizer rejects malformed
layouts.
