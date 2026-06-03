# Core GUObjectArray Candidate

## Objective

Validate a stronger `GUObjectArray`/`GObjects` candidate from the existing authorized
`arkserver` core dump, using the already confirmed FName table from the same core.

## Environment

- Instance: `arkserver`
- Map: `Ragnarok`
- ARK binary:
  `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ShooterGameServer`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Core:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
- Evidence artifact:
  `/servidor/ark/obelisk/dumps/core-pack-20260527T031311Z/gdb-gobjects-candidate-0x595b7e0.txt`
- Confirmed FName table in this core: `0x5956f30 -> 0x2ae5c660`

## Hypothesis

The current binary contains a `GUObjectArray`-shaped global at or near `0x595b7e0`.
Unlike chat string/object leads, this should validate through object-array structure:
chunk pointer, object count, object item, `UObjectBase` fields, and FName-resolved object
names.

## Evidence

GDB core inspection of `0x595b7e0`:

```text
chunks=0x2c6f2cc0 count=1243796 max=12648448 serial=45862
chunk0=0x2d10e000
obj0=0x79b62f8ff000
obj0 flags=0x400081 internal=0 class=0x2b1dd8c0 name_index=2866 name_number=0 outer=(nil)
obj0 name ... header=0x1664 string="/Script/CoreUObject"
class0 flags=0xc7 internal=516 class=0x2b1dda80 name_index=207 name_number=0 outer=0x79b62f8ff000
class0 name ... header=0x19e string="Package"
```

Generated evidence-pack sample commands later validated multiple object items:

```text
sample[0]: object=0x79b62f8ff000 internal_index=0 name="/Script/CoreUObject" class="Package"
sample[1]: object=0x2aed7340 internal_index=1 name="Object" class="Class"
```

The FName headers match `index * 2`:

- `2866 * 2 = 0x1664`
- `207 * 2 = 0x19e`

This confirms that multiple early object items point to plausible `UObjectBase` values,
their `InternalIndex` fields match their array indices, and their object/class names
resolve through the same FName table previously validated from the core.

Static xrefs from the matching `ShooterGameServer.objdump` also support the layout:

- `0x595b7f0` has thousands of code references using a chunked object lookup shape:
  load chunk pointer, derive `index >> 16`, load chunk, then access item with
  `index * 0x10`.
- `0x595b804` is repeatedly compared against requested object indices as a count-like
  upper bound.
- `0x595b838` is updated through `lock xadd`, consistent with a serial-number source.
- `0x595b7e0` is passed as an immediate first argument to several helper functions,
  consistent with a global object-array root/struct.

`scripts/build_core_dump_evidence_pack.py` now reproduces these xref summaries in
`gobjects-static-xrefs.json` when run with `--gobjects-candidate`. A local offline pack
for `0x595b7e0` reported `13884` load xrefs and `7` store xrefs across the tracked root,
chunks, count, and serial fields. The same JSON now groups xrefs by objdump function
anchor, making `0x12d1400` the strongest follow-up static context because it touches
root, chunks, count, and serial.

Concrete static contexts observed from that pack:

```text
0x79ce22: stores immediate 0x595b7e0 into a nearby global slot, then reads
          0x595b804 and 0x595b7f0 for a bounded object-array walk.
0x7a27a7: passes 0x595b7e0 as the first argument to a helper and then registers a
          destructor-like callback through __cxa_atexit with 0x595b7e0 as state.
0x81f118: writes zero to 0x595b7e0 during startup/reset flow.
0x81f206: later passes 0x595b7e0 to another helper in the same startup path.
```

Interpretation: these contexts are stronger than raw xref volume because they show root
initialization/reset, destructor registration, and lookup/walk behavior. The symbol names
in stripped objdump are often nearest exported labels and should not be treated as true
function names.

`2026-05-27-gobjects-static-anchor-classification.md` later classified these contexts and
rejected the broad `0x12d1400` function group as a standalone decompiler target because its
sample xrefs are dispersed under a huge nearest-symbol range.

## Result

`0x595b7e0` is promoted to `GUObjectArray research-candidate` for this ARK binary hash.
It is not yet a stable runtime offset.

The current best model from this core is:

- `GUObjectArray`-shaped root/struct: `0x595b7e0`
- chunk pointer field: `0x595b7f0`
- count-like field: `0x595b804`
- serial-like field: `0x595b838`
- first chunk: `0x2d10e000`

## Rejected Paths

- Do not continue treating chat UObject globals as direct GNames roots.
- Do not promote `0x5956f30` as a stable runtime slot from one core session. A later
  post-start debug-control probe rejected it with `table=0x13733660` and
  `implausible_num_elements`.
- Do not extend bootstrap sleeps as the main research strategy.

## Risks

- GDB warned that the currently installed `libobelisk.so` build id does not match the core.
  The ARK binary hash still matches the target executable, and this evidence reads ARK/core
  data, not Obelisk symbols.
- Initial validation covered item 0 only; later offline enumeration validated multiple
  object indices and FName-backed names in `2026-05-27-core-uobject-enumeration.md`.
  Promotion beyond `research-candidate` still requires stronger class/outer back-reference
  checks and a second independent evidence path.
- `0x595b7e0` is binary-hash-specific evidence.

## Current No-Repeat Checkpoint

Completed/superseded by `scripts/enumerate_core_uobjects.py`,
`2026-05-27-core-uobject-enumeration.md`, later static context notes, and the
second-core GObjects reconciliation notes:

1. Validate several `FUObjectItem` indices from the candidate `GUObjectArray`.
2. Resolve object `NamePrivate` through the confirmed FName table.
3. Check that `InternalIndex` matches the array index for sampled objects.

Do not repeat core/object enumeration, GObjects discovery, FName discovery, or isolated
core capture for the current binary hash from this note. Reuse `0x595b7e0` only as a
binary-hash-specific `GUObjectArray research-candidate` for offline reflection work.

Reopen enumeration only for a new binary hash or contradictory artifact evidence.
Runtime-stable/public object identity, lookup, `ResourceHandle`, mutation, return
override, and SDK surfaces remain blocked by separate runtime/public-contract gates,
including `approved_runtime_evidence_missing` where applicable.
