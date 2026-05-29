# FUObjectItem Serial and Lifetime Audit

## Objective

Clarify what the current offline evidence does and does not prove about
`FUObjectItem` serial fields, stale-handle detection, slot reuse, and object lifetime
before any opaque Obelisk `ResourceHandle` design.

This note used only existing repo docs, scripts, and copied offline artifacts. It did not
read or write protected server paths, attach to a process, create a core, stage, commit, or
push.

## Environment

- Obelisk worktree: `/home/flowcommunity-ark/Obelisk`
- ARK binary SHA256 under discussion:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Copied static artifact root:
  `/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529`
- Offline binary artifact:
  `/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer`

## Current Hypotheses

1. `GUObjectArray` remains a binary-hash-scoped research candidate at `0x595b7e0`.

   Existing field evidence supports `chunks=base+0x10`, `count=base+0x24`,
   `serial/master serial=base+0x58`, chunk size `0x10000`, and `FUObjectItem` stride
   `0x10`. Redacted field-window evidence can improve the static contract, but clearing
   that window blocker does not prove serial lifetime, slot reuse, post-callback
   revalidation, or a public `ResourceHandle`.

2. The strongest static evidence says the handle serial dword is `FUObjectItem+0x8`,
   not `FUObjectItem+0xc`.

   In the copied binary, the `0x1d56970..0x1d56eb0` accessor family derives the item as
   `chunks[index / 0x10000] + (index % 0x10000) * 0x10`, compares
   `DWORD PTR [item+0x8]` to the handle serial, tests it for zero, and publishes a newly
   allocated serial with `lock cmpxchg DWORD PTR [item+0x8], r15d`. The master serial
   source is `lock xadd DWORD PTR [0x595b838], r15d`.

3. `FUObjectItem+0xc` is currently unknown, not accepted serial evidence.

   Older local tooling used to label `item+0xc` as `item_serial_number`, while reading
   `item+0x8` as metadata/flags. That model is contradicted by the static handle-accessor
   path unless there is an unproven packed-qword interpretation. Current tooling records
   both dwords neutrally; treat `+0xc` as unknown until core samples are reconciled against
   the static path.

4. Stale-handle detection likely requires at least `{index, serial}` plus object flags.

   The static accessor family treats a handle as `{int32 index, int32 serial}`. It rejects
   zero serials, negative indices, indices outside `count`, and serial mismatches at
   `item+0x8`. Several paths then load `UObject*` from `item+0x0` and inspect
   `UObject+0x8` flag bits before returning a pointer or validity result. The exact flag
   meanings are not accepted.

5. Slot reuse is not proven.

   The observed `lock xadd` and `cmpxchg` show lazy/nonzero serial publication and a
   monotonic master serial source for this binary run. They do not prove when item serials
   are cleared, whether a reused slot always receives a fresh serial before exposure, what
   happens on wrap, or whether an object observed during `ProcessEvent` can be safely
   revalidated after the hook frame.

## Evidence References

- `docs/research/2026-05-29-static-gobjects-field-window-audit.md` records the blocked
  static contract and the field model for `0x595b7e0`, including the split between
  root/chunks/count windows and chunks/count/serial windows.
- The same note records that the handle-accessor window compares the item serial at
  `FUObjectItem+0x8`, uses `0x595b838` as the serial counter, and keeps
  `missing_gobjects_coherent_field_window` active.
- Static disassembly of the copied offline binary at `0x1d56970..0x1d56eb0` shows:
  - `0x1d56986`: reads `UObject+0xc` as the array index source;
  - `0x1d569c2`: reads `DWORD PTR [item+0x8]`;
  - `0x1d569d3`: `lock xadd` on `0x595b838`;
  - `0x1d56a88`, `0x1d56b2a`, `0x1d56c50`, `0x1d56d50`, `0x1d56ddc`:
    compare `DWORD PTR [item+0x8]` with the handle serial;
  - `0x1d56ea5`: `lock cmpxchg DWORD PTR [item+0x8], r15d`.
- `scripts/enumerate_core_uobjects.py` records `item+0x8` and `item+0xc` as neutral
  dword fields instead of assigning serial semantics to `+0xc`.
- `scripts/build_core_dump_evidence_pack.py` emits neutral GDB variable names for
  `item+0x8` and `item+0xc` instead of assigning serial semantics to `+0xc`.
- `scripts/test_enumerate_core_uobjects.py` and `scripts/test_inspect_core_ufunctions.py`
  fixtures are synthetic; they prove parsing mechanics, not the ARK binary layout.
- `ue/RuntimeReflection` validates `UObject` shape and `InternalIndex`, but it does not
  validate `GObjects[InternalIndex]`, `FUObjectItem` serials, stale handles, or slot reuse.

## Rejected Assumptions

- Do not expose or design a `ResourceHandle` around `GObjects` index plus `item+0xc`
  serial. The best static evidence points to `item+0x8`.
- Do not treat current object-array membership as lifetime safety. It proves only a
  current point-in-time relationship when the item, object, class, and outer backrefs are
  all checked.
- Do not treat the static `0x595b838` serial counter as a complete reuse contract. It is a
  serial source, not proof of invalidation behavior.
- Do not expose raw UE coordinates, serials, object pointers, `InternalIndex`,
  `FUObjectItem` addresses, or pointer-derived IDs through the public ABI.
- Do not promote the root/chunks/count/serial layout from static xrefs alone while
  `missing_gobjects_coherent_field_window` remains active.

## Unknowns Blocking ResourceHandle Work

- Exact semantic name of `FUObjectItem+0x8` in this binary: serial only, flags plus serial,
  or another packed metadata field.
- Exact semantic name of `FUObjectItem+0xc`.
- Whether serial zero is the only invalid item-serial state.
- When item serials are cleared or assigned during object destruction/allocation.
- Whether object slots are reused and whether reuse always changes the observed serial.
- Whether `UObject+0x8` flag checks in the accessor path correspond to pending-kill,
  unreachable, garbage-collection, cluster, or other lifetime states.
- Safe duration of any internal Obelisk handle: hook-frame only, tick-local,
  process-local until failed revalidation, or never safe.

## Next Validation Step

Run a focused offline reconciliation against the independent copied core evidence pack,
using explicit artifact-specific FName root and `GObjects` inputs. The pack must capture
both dwords at `FUObjectItem+0x8` and `FUObjectItem+0xc` for sampled indices, then compare
them against the static accessor path:

1. For each sampled object, compute `item = chunks[index / 0x10000] + (index % 0x10000) * 0x10`.
2. Record `item+0x0`, `u32(item+0x8)`, `u32(item+0xc)`, `u64(item+0x8)`, `UObject+0xc`,
   class membership, and outer membership.
3. Require `UObject.InternalIndex == index` and direct `GObjects[InternalIndex].Object`
   back-reference.
4. Treat acceptance as only an internal lifetime-evidence improvement. It must not create
   a public `ResourceHandle` until invalidation, reuse, redaction, capability, ABI, and
   callback-lifecycle gates are separately designed and tested.
