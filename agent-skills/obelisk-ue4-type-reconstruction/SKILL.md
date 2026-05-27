---
name: obelisk-ue4-type-reconstruction
description: Use when Obelisk work reconstructs UE4 runtime types such as FName, GNames/FNamePool, GUObjectArray/GObjects, UObject, UClass, UFunction, UProperty/FProperty, and ProcessEvent parameter layouts.
---

# Obelisk UE4 Type Reconstruction

Use this skill when converting raw addresses and memory shapes into a metadata-backed UE4
model for Obelisk.

## Reconstruction Order

Do not jump straight to chat params. Build the type chain in this order:

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
- Parameter buffers must be bounded by reflected `ParmsSize`.
- `FString` decoding requires a validated layout for this binary. Do not accept arbitrary
  readable pointer/length pairs as chat text.

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

## `GNames/FNamePool` First Milestone

The first accepted reflection milestone is not chat. It is a bounded `FName` resolver that
can turn known indices like `9619` and `9622` into expected strings on the validated binary.
Do not move to `GObjects`, `UFunction`, or params until this is repeatable from evidence
packs plus guarded runtime reads.
