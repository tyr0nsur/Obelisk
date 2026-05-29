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
- Reflection inventory packs are candidate-only review aids unless backed by a separate
  strict readiness note. Record artifact identity, hashes, commands, output paths,
  redacted field sets, second-source comparison, and explicit non-claims.
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
  current operator direction grants standing use of `arkserver2` / TheIsland for Obelisk
  debug/development tests when needed.
- `ReflectionScanner` FName table output must be treated as candidate ranking. Analyzer
  `--strict` requires repeat-confirmed exact `matched_clues=3/3` evidence, and even that
  needs a second isolated capture or static xref before becoming an accepted offset.
- When the binary-hash-scoped FName root slot is already known for the artifact, do not
  spend new rounds on broad reverse FName table scans. Reuse the reviewed root slot as an
  explicit input and abort scan-expansion plans unless the binary hash or artifact
  evidence contradicts it.
- `FName`/`GObjects`/`UObject` identity and runtime-global evidence remains candidate-only
  until a second isolated core or independent static path validates the same fields.
  UFunction layout evidence is promoted only per target set after a second-source
  readiness report. Static xrefs and analyzer evidence are supporting evidence; they are
  not acceptance by themselves.
- Public/post-callback `ResourceHandle` remains blocked by
  `uobject_flags_validity_semantics_unproven`: `UObject+0x8` is confirmed only as a 32-bit
  flags field; helper paths consult `0x100` and `0x4000` after `{index, serial}` validation;
  accepted samples show `0x81`/`0xc7`/`0xc5`; no rejected sample or exact lifetime semantic
  is proven.
- Do not claim all copied-core `FUObjectItem+0x8` serial samples are zero. Wider offline
  scans with `scripts/scan_resource_handle_serials.py` found repeatable nonzero serial
  candidates in both copied cores. This supports internal handle-revalidation tooling only;
  `ResourceHandle`, object identity, lookup, and post-callback validity remain unpromoted
  until lifetime/reuse behavior and `UObject+0x8` flag semantics are proven.
- Do not restart `GObjects` work from broad candidate search. Repeat classified checks on a
  second isolated core or future binary before promoting runtime-stable contracts.
- General/core offline layout promotion has accepted `minimal-second-source-intake`:
  `PrimalItem.CanUse`, `PrimalItem.AllowRemoteAddToInventory`,
  `PrimalStructure.AllowStructureAccess`, and `PrimalStructure.IsAllowedToDemolish`.
  This target set now has accepted offline second-source UFunction layout evidence from
  `/servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z`
  with `promotion_gate.ready=true`, empty blockers, and `4/4` accepted targets. Treat it
  as layout promotion only; it does not promote `GObjects`, `ResourceHandle`, `UObject`
  identity, mutation, return overrides, raw params, player/item/inventory identity, or
  public Inventory/StructureEvents SDK surfaces. `dino-compact-intake` is a separate
  internal-layout result.
- Module recognizers are active research tracks, not public SDK:
  - `ue/StructureReflection` has a hook-side observer, but it requires env, supported SHA,
    non-zero budget, `state/instances/<id>/allow-experimental-observers`, and
    `state/instances/<id>/enable-structure-reflection`.
    Its accepted `structure-observer-intake` evidence now backs the public
    `GameplayPolicyEvent` ABI, but only through copied/redacted POD scalars.
  - `ue/InventoryReflection` is internal recognizer only. A future runtime observer must
    require `allow-experimental-observers`, `enable-inventory-reflection`, exact `CanUse`
    / `AllowRemoteAddToInventory` FName prefiltering before budget reservation, exact
    per-target `FunctionFlags` for the supported binary, and no return override or
    gameplay mutation. Current copied-scalar fields are `CanUse.bIgnoreCooldown`,
    `CanUse.ReturnValue`, `AllowRemoteAddToInventory.bRequestedByPlayer`, and
    `AllowRemoteAddToInventory.ReturnValue`; object fields stay redacted.
  - `ue/BuffReflection` has accepted `buff-compact-intake` layout evidence for three
    compact targets, but remains an offline/internal recognizer track only. Keep buff
    hooks, callbacks, return overrides, raw object/class exposure, and gameplay mutation
    blocked until SDK policy, copied payload design, runtime gates, and lifecycle tests
    exist.
  - `ue/DinoReflection` is allowed only as an internal, fixture-backed compact recognizer
    for the accepted `dino-compact-intake` layouts
    (`PrimalDinoCharacter.AddPassenger` and `PrimalDinoCharacter.AllowCarryCharacter`).
    This is internal layout evidence only; no public Dino SDK/API, runtime observer,
    object identity, mutation, return override, or resource-handle behavior is promoted.
  - `mission-compact-intake` and `tribe-compact-intake` now have accepted offline
    second-source layout evidence. Mission is the next cleaner internal module candidate
    after inventory hardening, but only as a reduced copied-scalar observer; tribe requires
    a reduced scalar subset before public consideration. Keep player/tribe/mission
    identity, arrays, strings, object pointers, mutation, return override, and public
    Mission/Tribe SDK surfaces blocked.
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
- Internal copied-data dispatchers are the required bridge between candidate recognizers
  and public SDK modules. `core/StructureEventDispatcher` feeds the promoted
  `GameplayPolicyEvent` ABI by copying approved scalar values only through
  `ProcessEventStructureReflection` event building, dispatching only after the original
  `ProcessEvent` path reports that the original call ran, and hiding object/string/array/
  raw param storage. Public plugins must receive only `field_mask`, `bool_values`, and
  `int32_values`; `pinCode`, player identity, object identity, FName/GObjects indices, and
  UE pointers stay redacted.
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
- Current operator direction protects `arkserver` / Ragnarok because users may be active
  there. Do not restart it, change markers, or run runtime tests there. `arkserver2` /
  TheIsland has standing approval for Obelisk debug/development tests when needed; restore
  stable posture and shut it down when no longer needed.
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
