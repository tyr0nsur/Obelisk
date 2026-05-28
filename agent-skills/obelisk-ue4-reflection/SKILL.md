---
name: obelisk-ue4-reflection
description: "Guides Obelisk work that should decode UE4 objects, UFunctions, FNames, and parameters through reflection instead of fragile raw memory scans."
---

# Obelisk UE4 Reflection Skill

Use this skill when building Obelisk's general ARK Linux reflection substrate: gameplay
APIs, SDK wrappers, module recognizers, object lookup, or parameter decoding through UE4
metadata.

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
  reproduce the current offline path from core dump to candidate `UFunction` and
  `ScriptStruct` property chains across module surfaces.
- `scripts/compare_reflection_snapshots.py` compares sanitized UFunction/ScriptStruct
  snapshots offline and supports `--target Outer.Name` or schema-qualified targets for
  focused second-source checks.
- Internal runtime layers exist:
  - `ue/RuntimeReflection.{h,cpp}` for binary-hash-gated `UObject`/`UFunction`/
    `UProperty` validation and UTF-32 `FString` decoding helpers.
  - `ue/ChatReflection.{h,cpp}` for `ServerChat`, `ServerChatTo`, `ServerChatToPlayer`,
    `ShooterPlayerController.ServerSendChatMessage`, and metadata-only fallback
    recognition. Treat this as historical module evidence and internal experimentation,
    not the project center.
  - `ue/InventoryReflection`, `ue/StructureReflection`, and `ue/BuffReflection` are
    module recognizers at different maturity levels; all remain internal/candidate-only
    until second-source evidence and SDK ownership policy exist.
  - `hooks/ProcessEventChatReflection.{h,cpp}` for hook-side gate/recognition tests.
- Historical chat evidence proved useful patterns for exact UFunction/outer/`ParmsSize`/
  property-chain recognition, bounded FString decoding, marker/env/SHA gates, dispatcher
  ownership, ABI guardrails, and benchmark gates. Keep details in `docs/research/`; do
  not let chat dominate new reflection/API rounds unless explicitly requested.
- `arkserver` / Ragnarok has carried experimental chat reflection in historical runs. Do
  not add, remove, or rely on that marker for new validation. Current runtime observer
  work belongs only on the currently approved target or a dedicated debug instance;
  `arkserver2` / TheIsland is an explicit operator-approved fallback while RAM is
  constrained.
- `ReflectionScanner` FName table output must be treated as candidate ranking. Analyzer
  `--strict` requires repeat-confirmed exact `matched_clues=3/3` evidence, and even that
  needs a second isolated capture or static xref before becoming an accepted offset.
- `FName`/`GObjects`/`UObject`/`UFunction` evidence remains candidate-only until a second
  isolated core or independent static path validates the same fields. Static xrefs and
  analyzer evidence are supporting evidence; they are not acceptance by themselves.
- Do not restart `GObjects` work from broad candidate search. Repeat classified checks on a
  second isolated core or future binary before promoting runtime-stable contracts.
- Module recognizers are active research tracks, not public SDK:
  - `ue/StructureReflection` has a hook-side observer, but it requires env, supported SHA,
    non-zero budget, and `state/instances/<id>/enable-structure-reflection`.
  - `ue/InventoryReflection` is internal recognizer only. A future runtime observer must
    require `enable-inventory-reflection`, exact `CanUse` / `AllowRemoteAddToInventory`
    FName prefiltering before budget reservation, and no return override or gameplay
    mutation.
  - `ue/BuffReflection` is an offline internal recognizer only. Keep buff hooks,
    callbacks, return overrides, raw object/class exposure, and gameplay mutation blocked
    until second-source evidence and SDK policy exist.
  - Use the same gates for future dinos, tribes, missions, transfers, admin, and item
    recognizers: exact metadata shape, candidate-only fixtures, no mutation, no raw UE
    pointer exposure, and no public callbacks before ABI/lifetime policy.

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

## Module Promotion Ladder

Use the same ladder for chat, inventory, structures, buffs, dinos, tribes, missions,
transfers, admin, and future module surfaces:

1. Offline candidate: exact function/struct name, outer, class, `ParmsSize` or
   `PropertiesSize`, and property-chain shape are plausible.
2. Fixture-backed: sanitized UFunction/ScriptStruct snapshots and tests cover accepted and
   rejected shapes.
3. Second-source checked: another isolated core or independent static path repeats the
   semantic layout; unstable FName/GObjects indices are not promotion criteria. Snapshot
   comparison acceptance requires distinct sanitized artifact identity on both roots;
   missing or matching identity is `inconclusive`, so self-comparison cannot satisfy
   second-source evidence.
4. Runtime-observed: an approved isolated/debug window sees the exact metadata shape with
   bounded params, no mutation, and rollback/posture evidence.
5. Internal event: exposed data is copied into Obelisk-owned memory and callback owner
   cleanup/lifetime is tested.
6. Public SDK: append-only C ABI, ABI layout tests, installed SDK consumer tests, docs, and
   explicit capability policy are in place.

Do not skip steps because a single core, log line, or recognizer test looks convincing.

## Parameter Decoding Rules

- Prefer reflected property offsets over hardcoded struct offsets.
- Validate `ParmsSize` before reading a parameter buffer.
- Use exact filters (`FName`/name, outer, class, size, and property-chain shape) for
  runtime recognizers. Substring filters are discovery-only.
- Decode strings with a known UE4 `FString` layout for this binary, not by accepting any
  readable pointer-like value.
- For this ARK Linux binary, the internal `FString` candidate is 16 bytes and points to
  UTF-32LE `TCHAR`; keep it behind reflected `StrProperty` validation.
- Do not send chat or client messages from inside a pre-hook until reentrancy and caller
  object semantics are understood.
- Do not cache a `UFunction*` or caller object as valid unless it has been verified against
  the object array or another reliable lifetime signal.

## Module/Event Guidance

- Keep every gameplay module experimental until its reflection evidence, copied-data
  ownership, callback lifetime, ABI layout, installed SDK consumer coverage, and runtime
  safety gates are complete.
- Use snapshot fixtures and `compare_reflection_snapshots.py` before promoting any
  UFunction or ScriptStruct shape beyond candidate-only.
- `compare_reflection_snapshots.py --target <Outer.Name>` is offline. It compares
  sanitized JSON only, does not read cores, and does not touch servers.
- For ScriptStructs and cross-source checks, compare semantic layout by default; use strict
  identity indices only when intentionally checking same-binary identity evidence.
- For snapshot comparisons, acceptance requires distinct sanitized artifact identity on
  both roots; missing or matching identity is `inconclusive`.
- Snapshot comparison must also require each property and nested array/struct candidate
  to be backed by `candidate-uobject` membership before accepting a layout as comparable.
- Do not expand raw `0x00..0x80` param scanning as the long-term fix for any module.
- Avoid manual construction of UE params until the real reflected property layout and
  caller semantics are decoded.
- Prefer logging metadata discoveries over mutating gameplay state while researching.
- For inventory, structure, buff, transfer, admin, chat, and other authority functions, do
  not override return values, mutate params, call original `ProcessEvent` manually, or
  dispatch public plugin callbacks from candidate evidence.
- Reserve runtime observation budgets only after cheap exact prefilters pass.
- On live servers, keep plugin discovery off unless testing a known safe build.
- Current operator direction as of 2026-05-28 protects `arkserver` / Ragnarok because
  users are active there. Do not restart it, change markers, or run runtime tests there.
  `arkserver2` / TheIsland is powered off; if a server is needed, start it only with
  explicit operator approval and shut it down when the test window ends.
- Do not enable raw discovery, broad tracing, native exec probes, ptrace/gcore, or
  `ReflectionScanner` without exact operator approval for that run, copied-log evidence,
  and rollback. Prefer `arkserver2` / TheIsland or `arkserver-obelisk-debug` for
  scanner-like captures only when the operator explicitly approves that target.

## Review Checklist

- [ ] Does this code resolve names/objects/functions through UE4 metadata where possible?
- [ ] Are all raw offsets documented with binary hash, map/server, and validation evidence?
- [ ] Is `FName` index use treated as a hint rather than a stable identifier?
- [ ] Are parameter reads bounded by `ParmsSize` and property metadata?
- [ ] Does the implementation avoid blocking or unsafe UE4 calls inside ProcessEvent hooks?
- [ ] Is experimental reflection or module discovery gated by environment variables/config,
      markers, binary hash checks, and explicit budgets?
