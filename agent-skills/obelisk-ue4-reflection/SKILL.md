---
name: obelisk-ue4-reflection
description: Guides Obelisk work that should decode UE4 objects, UFunctions, FNames, and parameters through reflection instead of fragile raw memory scans.
---

# Obelisk UE4 Reflection Skill

Use this skill when building gameplay APIs, chat interception, SDK wrappers, object lookup,
or parameter decoding for ARK's Linux UE4 server.

## Current Reality

- `UObject::ProcessEvent` is hookable and currently observed around `0x1d34e20` on the
  validated Ragnarok binary.
- `UObjectBase::NamePrivate.ComparisonIndex` has been observed at object offset `0x18`
  and `Number` at `0x1c`.
- The chat experiment has seen likely `FName` indices:
  - `ServerChat`: `9622`
  - `ClientMessage`: `9619`
- These indices are useful research clues, not a stable public API.
- `ChatPlugin` currently uses raw parameter probing and FString heuristics. Treat that as
  temporary discovery code, not the final architecture.

## Reflection Direction

Build toward a real UE4 metadata pipeline:

1. Resolve `FName` indices to strings through `GNames`/`FNamePool`.
2. Resolve `GUObjectArray`/`GObjects`.
3. Enumerate `UObject` instances and identify `UFunction` objects.
4. Model enough `UFunction` fields to read flags, `NumParms`, `ParmsSize`, and the property
   chain.
5. Model `UProperty`/`FProperty` offsets and types for function parameters.
6. Decode `ProcessEvent` params from reflected metadata instead of scanning arbitrary memory.
7. Expose stable Obelisk-level events such as `OnChatMessage` only after metadata-backed
   decoding exists.

## Parameter Decoding Rules

- Prefer reflected property offsets over hardcoded struct offsets.
- Validate `ParmsSize` before reading a parameter buffer.
- Decode strings with a known UE4 `FString` layout for this binary, not by accepting any
  readable pointer-like value.
- Do not send chat or client messages from inside a pre-hook until reentrancy and caller
  object semantics are understood.
- Do not cache a `UFunction*` or caller object as valid unless it has been verified against
  the object array or another reliable lifetime signal.

## ChatPlugin Guidance

- Keep chat interception experimental until `ServerChat` and outbound message functions are
  resolved through reflection.
- Do not expand raw `0x00..0x80` param scanning as the long-term fix.
- Avoid manual construction of `ClientMessage` params until the real property layout is
  decoded.
- Prefer logging metadata discoveries over mutating gameplay state while researching.
- On live servers, keep plugin discovery off unless testing a known safe build.

## Review Checklist

- [ ] Does this code resolve names/objects/functions through UE4 metadata where possible?
- [ ] Are all raw offsets documented with binary hash, map/server, and validation evidence?
- [ ] Is `FName` index use treated as a hint rather than a stable identifier?
- [ ] Are parameter reads bounded by `ParmsSize` and property metadata?
- [ ] Does the implementation avoid blocking or unsafe UE4 calls inside ProcessEvent hooks?
- [ ] Is experimental reflection or chat discovery gated by environment variables/config?
