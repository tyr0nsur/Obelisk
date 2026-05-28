---
name: obelisk-ue4-type-reconstruction
description: "Use when Obelisk work reconstructs UE4 runtime types such as FName, GNames/FNamePool, GUObjectArray/GObjects, UObject, UClass, UFunction, UProperty/FProperty, and ProcessEvent parameter layouts."
---

# Obelisk UE4 Type Reconstruction

Use this skill when converting raw addresses and memory shapes into a metadata-backed UE4
model for Obelisk.

## Reconstruction Order

Do not jump straight to any gameplay module's params. Build the type chain in this order:

1. `FName` entry decoding through `GNames` or `FNamePool`.
2. `GUObjectArray`/`GObjects` enumeration.
3. `UObject` base shape: vtable, object flags, internal index, class, name, outer.
4. `UClass` and `UStruct` inheritance enough to identify functions and properties.
5. `UFunction`: flags, function pointer where relevant, `NumParms`, `ParmsSize`.
6. `UProperty`/`FProperty` chain: parameter names, offsets, element sizes, type tags.
7. `ProcessEvent` parameter decoding bounded by `ParmsSize`.

## Validation Rules

- Treat `FName` indices like `9619` or `9622` as clues only.
- A pointer is not a `UObject` until name, class, vtable/range, and object array context
  are mutually plausible.
- A `UFunction` is not accepted from string proximity alone; it needs resolved name,
  class/outer context, function flags, and parameter metadata.
- Offline `UObject`/`UFunction`/`UProperty` evidence should validate target, class, and
  outer pointers through direct `GObjects[InternalIndex]` back-references when a candidate
  `GUObjectArray` is available. Do not substitute broad address-to-index scans for this
  point check.
- Parameter buffers must be bounded by reflected `ParmsSize`.
- `FString` decoding requires a validated layout for this binary. Do not accept arbitrary
  readable pointer/length pairs as module text or names.
- For the current validated ARK Linux hash, `FString` is an internal candidate of
  `{Data, ArrayNum, ArrayMax}` with UTF-32LE `TCHAR`; use
  `RuntimeReflection::TryDecodeFStringUtf32` only after reflected `StrProperty`
  validation.

## Evidence To Record

For each reconstructed field:

- binary hash and Obelisk commit,
- source of evidence: static xref, isolated log, UE4 source comparison, or controlled
  memory read,
- field offset and expected type/size,
- pass/fail examples,
- reject conditions that prevent unsafe reads.

## Implementation Shape

- Put reusable structs and guarded readers under `ue/`.
- Current internal layers include `ue/RuntimeReflection.{h,cpp}` for bounded type reads
  and module-specific recognizers such as chat, inventory, structures, and buffs. Keep
  recognizers internal until second-source evidence, copied-data ownership, and SDK ABI
  gates are complete.
- Historical chat work proved the pattern for reflected strings/enums and dispatcher
  ownership. Treat those details as module evidence in `docs/research/`, not as the active
  reconstruction center.
- Keep scanners gated and bounded.
- Log candidate scores and reasons, not just addresses.
- Prefer analyzer fixtures before runtime reads.
- Do not expose a public SDK API until type evidence is stable enough to survive another
  binary update.

## Promotion Checklist

- [ ] The type field has at least two evidence paths.
- [ ] There is an evidence pack with binary SHA256, Obelisk commit, copied log paths,
      objdump/readelf artifact paths, and candidate status.
- [ ] Reads are bounded and reject unreadable or implausible memory.
- [ ] Analyzer or C++ tests cover accepted and rejected examples.
- [ ] Research notes describe why false positives were rejected.
- [ ] No live server mutation is required to validate the field.

## Current Milestones

- Core evidence has already produced a binary-hash-scoped FName table, `GUObjectArray`
  candidate, UObject enumeration, UFunction property chains, and internal runtime readers.
- The active blocker for public module APIs is not more raw scanning; it is second-source
  reflection evidence, copied-data ownership, callback lifecycle, ABI layout tests,
  installed SDK consumer coverage, and approved isolated runtime validation.
- Candidate module recognizers for inventory, structures, buffs, dinos, tribes, missions,
  transfers, admin, and chat must stay internal until the common promotion gates pass.
- Use sanitized snapshots and `compare_reflection_snapshots.py --target <Outer.Name>` to
  compare semantic layouts before accepting any UFunction or ScriptStruct shape beyond
  candidate-only. Acceptance requires distinct sanitized artifact identity on both roots;
  missing or matching identity is `inconclusive`, so self-comparison cannot satisfy
  second-source evidence.
- When regenerating UFunction or ScriptStruct snapshots with artifact identity fields,
  pass a FName root/table verified for that artifact. The regenerators must reject artifact
  identity runs that omit explicit `--fname-root-slot`; do not let the primary-core default
  become second-source evidence.
