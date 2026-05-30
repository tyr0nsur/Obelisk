---
name: obelisk-ue4-reflection
description: "Guides Obelisk work that should decode UE4 objects, UFunctions, FNames, and parameters through reflection instead of fragile raw memory scans."
---

# Obelisk UE4 Reflection Skill

Use this skill when building Obelisk's general ARK Linux reflection substrate: gameplay
APIs, SDK wrappers, module recognizers, object lookup, or parameter decoding through UE4
metadata.

## Current Reality

- ArkServerApi/AseApi may be used only as a names and behavior dictionary for familiar
  Unreal/ARK `Class.Function` and `Class.Property` concepts. Do not copy memory offsets,
  vtable definitions, struct layouts, MSVC calling conventions, Windows-only ABI choices,
  or direct native call wrappers from it. Reimplement any property/function access through
  Obelisk's Linux-native `ReflectionScanner`, `RuntimeReflection`, and
  `ProcessEventHook` paths with binary-hash-scoped evidence.
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
- Runtime/server routing belongs to `obelisk-live-ops` and the current handoff, not this
  reflection skill. Any runtime observation requires an approved scoped live-ops plan.
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
- Public/post-callback `ResourceHandle`, object identity, lookup, and post-callback
  validity remain blocked until lifecycle/reuse behavior and `UObject` flag semantics are
  proven. Keep detailed masks, samples, paths, and rejected-candidate criteria in dated
  research notes; skills should only preserve the blocking rule.
- Do not restart `GObjects` work from broad candidate search. Repeat classified checks on a
  second isolated core or future binary before promoting runtime-stable contracts.
- Accepted target sets are layout-only unless the release/public SDK docs name the surface
  and a strict readiness note promotes it. Keep exact target lists, counts, artifact paths,
  and commands in `docs/research/`; do not pass them to sub-agents through this skill.
- Module recognizers are active research tracks, not public SDKs. Use the same gates for
  structures, inventory, items, buffs, dinos, tribes, missions, transfers, admin, and future
  modules: exact metadata shape, fixture-backed tests, SHA/binary scoping, copied scalars
  only, no raw UE pointer exposure, no identity/lookup/`ResourceHandle`, no mutation, no
  return override, no public callback before ABI/lifetime policy, and no runtime observer
  without live-ops approval.

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
- Item return-only observations use a private `core/ItemReturnEventDispatcher` before any
  public SDK promotion. It is post-original, copied `ReturnValue` bool only, and must not
  be routed through `InventoryPolicyEventKind::CanUse` or public ABI/docs until a separate
  append-only `GameplayPolicyEvent` promotion is designed and tested.
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
- Treat mutation and return override as separate promotions after read-only copied-scalar
  callbacks; neither is implied by layout acceptance, runtime observation, or internal
  event support.
- Copied `BoolProperty` values must be canonical: copy only bytes `0` or `1`; reject
  bytes greater than `1` instead of normalizing them to `true`.
- Observer/helper gates must prove fail-closed behavior before runtime wiring: disabled
  gates, missing profile/window/marker/SHA, unsupported SHA, zero budget, and non-target
  `fname_index` must not read metadata/params or reserve sequence/log budget.
- Rejection paths must clear copied output, and recognition-only object/array fields must
  reject forged copied ranges.
- Reserve runtime observation budgets only after cheap exact prefilters pass.
- On live servers, keep plugin discovery off unless testing a known safe build.
- Current operator direction in `docs/agent-handoff/CURRENT.md` selects the server-backed
  target. `arkserver` / Ragnarok may be used only for an approved announced beta window
  with privacy bounds and exact feature gates. `arkserver2` / TheIsland is the isolated
  debug target when player involvement is not desired, but it still requires an approved
  scoped run before starts, restarts, marker edits, or runtime observation.
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
