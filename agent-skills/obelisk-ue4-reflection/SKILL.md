---
name: obelisk-ue4-reflection
description: "Guides Obelisk work that should decode UE4 objects, UFunctions, FNames, and parameters through reflection instead of fragile raw memory scans."
---

# Obelisk UE4 Reflection Skill

Use this skill when building gameplay APIs, chat interception, SDK wrappers, object lookup,
or parameter decoding for ARK's Linux UE4 server.

## Current Reality

- `UObject::ProcessEvent` is hookable and currently observed around `0x1d34e20` on the
  validated Ragnarok binary.
- `UObjectBase::NamePrivate.ComparisonIndex` has been observed at object offset `0x18`
  and `Number` at `0x1c`.
- Confirmed core FName clues for the current ARK binary hash include:
  - `4884 -> ClientMessage`
  - `9619 -> ServerChat`
  - `9622 -> SetActiveMissionDebugFlags`
- Older chat experiments that assumed `9619 -> ClientMessage` and `9622 -> ServerChat`
  are obsolete. Treat historical chat indices as research clues, not stable API.
- Core evidence promotes `0x595b7e0` to a binary-specific `GUObjectArray`
  research-candidate; use it to enumerate objects and validate gameplay/API module
  candidates.
- `scripts/enumerate_core_uobjects.py` and `scripts/inspect_core_ufunctions.py` can
  reproduce the current offline path from core dump to chat `UFunction` property chains.
- Internal runtime layers exist:
  - `ue/RuntimeReflection.{h,cpp}` for binary-hash-gated `UObject`/`UFunction`/
    `UProperty` validation and UTF-32 `FString` decoding helpers.
  - `ue/ChatReflection.{h,cpp}` for `ServerChat`, `ServerChatTo`, `ServerChatToPlayer`,
    `ShooterPlayerController.ServerSendChatMessage`, and metadata-only fallback
    recognition.
  - `hooks/ProcessEventChatReflection.{h,cpp}` for hook-side gate/recognition tests.
- Historical/current-state evidence: `arkserver` has had
  `state/instances/arkserver/enable-chat-reflection` active, and current logs include
  accepted `ServerSendChatMessage` hits with `send_mode=0` plus bounded `ChatMessage` /
  `SendMode` ranges. Do not add, remove, or rely on that Ragnarok marker for new
  validation. Future chat reflection work belongs on approved `arkserver2` windows or a
  dedicated debug instance. This confirms the experimental runtime path, not a public SDK
  event.
- `ServerChat`, `ServerChatTo`, and `ServerChatToPlayer` have `ShooterCheatManager` outer
  evidence and should not be treated as the primary normal player chat path. Current best
  incoming player chat candidate is `ServerSendChatMessage` with FName index `2697`,
  `StrProperty ChatMessage` at offset `0x0`, `ByteProperty SendMode` at offset `0x10`,
  and `ParmsSize=0x11`. `SendMode` is `EChatSendMode`: `0 GlobalChat`,
  `1 GlobalTribeChat`, `2 LocalChat`, `3 AllianceChat`; values `>=4` must be rejected
  for logging/dispatch.
- The deployed experimental chat runtime logs reflected `send_mode` and `send_mode_name`
  for accepted `ServerSendChatMessage` hits. It still must not dispatch plugin events
  until text is copied into Obelisk-owned memory and callback ownership is specified.
- Current `main` decodes `ServerSendChatMessage.ChatMessage` with the internal UTF-32
  `FString` decoder for experimental logs only, after `SendMode` is known and
  `OBELISK_CHAT_REFLECTION_LOG_TEXT=1` is explicitly set. Treat this as validation
  instrumentation, not SDK behavior, and do not assume it is deployed to the active server.
- Offline core evidence also supports two `ShooterGameMode` fallback candidates as
  metadata-only recognizers: `SendServerChatMessage` with FName index `9801`,
  `ParmsSize=0x2c`, and five fields; and `OnServerChatMessage__DelegateSignature` with
  FName index `28549`, `ParmsSize=0x18`, and three fields. Treat these as observation
  targets only: no text decoding, no plugin dispatch, and no native exec hooks until a
  confirmed runtime hit changes the evidence.
- Prior raw chat experiments used parameter probing and FString heuristics. Treat that as
  historical discovery code, not the final architecture.
- `ReflectionScanner` FName table output must be treated as candidate ranking. Analyzer
  `--strict` requires repeat-confirmed exact `matched_clues=3/3` evidence, and even that
  needs a second isolated capture or static xref before becoming an accepted offset.
- Gameplay recognizers are active research tracks, not public SDK:
  - `ue/StructureReflection` has a hook-side observer, but it requires env, supported SHA,
    non-zero budget, and `state/instances/<id>/enable-structure-reflection`.
  - `ue/InventoryReflection` is internal recognizer only. A future runtime observer must
    require `enable-inventory-reflection`, exact `CanUse` / `AllowRemoteAddToInventory`
    FName prefiltering before budget reservation, and no return override or gameplay
    mutation.
  - `ue/BuffReflection` is an offline internal recognizer only. Keep buff hooks,
    callbacks, return overrides, raw object/class exposure, and gameplay mutation blocked
    until second-source evidence and SDK policy exist.

## Reflection Direction

Build toward a real UE4 metadata pipeline:

1. Resolve `FName` indices to strings through `GNames`/`FNamePool`.
2. Resolve `GUObjectArray`/`GObjects`.
3. Enumerate `UObject` instances and identify `UFunction` objects.
4. Model enough `UFunction` fields to read flags, `NumParms`, `ParmsSize`, and the property
   chain.
5. Model `UProperty`/`FProperty` offsets and types for function parameters.
6. Decode `ProcessEvent` params from reflected metadata instead of scanning arbitrary memory.
7. Expose stable Obelisk-level events only after metadata-backed decoding, copied-data
   ownership, callback lifecycle, and ABI policy exist for the target module.

## Parameter Decoding Rules

- Prefer reflected property offsets over hardcoded struct offsets.
- Validate `ParmsSize` before reading a parameter buffer.
- Decode strings with a known UE4 `FString` layout for this binary, not by accepting any
  readable pointer-like value.
- For this ARK Linux binary, the internal `FString` candidate is 16 bytes and points to
  UTF-32LE `TCHAR`; keep it behind reflected `StrProperty` validation.
- Do not send chat or client messages from inside a pre-hook until reentrancy and caller
  object semantics are understood.
- Do not cache a `UFunction*` or caller object as valid unless it has been verified against
  the object array or another reliable lifetime signal.

## Chat/Event Guidance

- Keep chat interception experimental even though `ServerSendChatMessage` is now observed
  in the deployed hook path; the next boundary is copied text decoding plus a stable
  callback ownership contract.
- For `ServerSendChatMessage`, only log or dispatch recognized `EChatSendMode` values
  `0..3`; treat `>=4` as rejected evidence, not a chat event.
- Do not expand raw `0x00..0x80` param scanning as the long-term fix.
- Avoid manual construction of `ClientMessage` params until the real property layout is
  decoded.
- Prefer logging metadata discoveries over mutating gameplay state while researching.
- For inventory and other authority functions, do not override return values, mutate params,
  call original `ProcessEvent` manually, or dispatch public plugin callbacks from candidate
  evidence.
- On live servers, keep plugin discovery off unless testing a known safe build.
- Do not enable raw chat discovery or `ReflectionScanner` on shared/live-like instances;
  use the isolated debug instance plan and keep plugins disabled during scanner captures.

## Review Checklist

- [ ] Does this code resolve names/objects/functions through UE4 metadata where possible?
- [ ] Are all raw offsets documented with binary hash, map/server, and validation evidence?
- [ ] Is `FName` index use treated as a hint rather than a stable identifier?
- [ ] Are parameter reads bounded by `ParmsSize` and property metadata?
- [ ] Does the implementation avoid blocking or unsafe UE4 calls inside ProcessEvent hooks?
- [ ] Is experimental reflection or chat discovery gated by environment variables/config?
