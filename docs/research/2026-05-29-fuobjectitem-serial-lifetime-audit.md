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

## Static Weak Helper Truth Table

Follow-up static/offline review of the copied binary refined the internal helper polarity
without closing the public `ResourceHandle` blocker.

Environment:

- Offline binary:
  `/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer`
- SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Obelisk commit used by the static review: `3cb248a`
- `.text` range: `0x648400..0x3f6170f`

Common weak shape:

```text
Weak = { int32 index @ +0, int32 serial @ +4 }

serial != 0
index >= 0 && index < *(int32*)0x595b804
chunk = (*(void***)0x595b7f0)[index >> 16]
item = chunk + 0x10 * (index & 0xffff)
item_serial = *(int32*)(item + 0x8)
obj = *(void**)(item + 0x0)
flags = *(uint32*)(obj + 0x8)
```

Observed raw flag bits remain `0x100` and `0x4000`. Do not assign UE4 semantic names to
them yet.

| Address | Working name | Static result |
| --- | --- | --- |
| `0x1d56d00` | `GetRaw(Weak*) -> UObject*` | Returns `obj` when serial is nonzero, index is in range, and `item+0x8 == serial`; no flag filtering. |
| `0x1d56c00` | `GetStrict(Weak*) -> UObject*` | Like raw lookup, but requires `obj != 0`, no `0x100`, and no `0x4000`. |
| `0x1d56c70` | `GetMaybePending(Weak*, bool allow4000)` | Requires `obj != 0` and no `0x100`; `0x4000` is allowed only when `sil != 0`. |
| `0x1d56a30` | `IsValidLike(Weak*, bool allow4000, bool threadSafe)` | With `dl != 0`, validates only index and serial. Otherwise true when serial matches and either `obj == 0` or no `0x100` and (`allow4000` or no `0x4000`). Preserve the static `obj == 0 => true` edge case as unresolved. |
| `0x1d56ae0` | `IsValidStrictNoArgsLike(Weak*)` | True when index and serial match and either `obj == 0` or flags have neither `0x100` nor `0x4000`; false for zero serial, invalid index, or mismatch. |
| `0x1d56b60` | `IsStaleLike(Weak*, bool include4000, bool threadSafe)` | `serial == 0 => false`; invalid index or serial mismatch => true. With `dl == 0`, `sil == 0` reports stale only for `0x100`; `sil != 0` reports stale for `0x100 | 0x4000`. `obj == 0 => false`. |
| `0x1d56d60` | `Assign/repair weak from object via virtual callback` | Resolves the current weak, calls virtual `[this+vtable+0x18]`, writes `index = obj+0xc` when an object is returned, lazily publishes `item+0x8` with `lock xadd`/`cmpxchg` when serial is zero, and writes `-1` to the weak when no object is available. |

Reviewed caller windows:

- `0x83a2a0..0x83a2c6`: calls `0x1d56c00`; later use requires a returned object, so both
  `0x100` and `0x4000` are filtered.
- `0x83a340..0x83a370`: calls `0x1d56c70(elem, 1)` while iterating 16-byte elements; this
  permits `0x4000` but not `0x100`.
- `0x3522bf0..0x3522c1d`: calls `0x1d56ae0`, then `0x1d56c00`; because `ae0` may be
  true when `obj == 0`, the downstream call may receive null in that static edge case.

Direct call counts observed by bounded objdump scan:

```text
0x1d56a30: 8958
0x1d56ae0: 315
0x1d56b60: 4
0x1d56c00: 512
0x1d56c70: 6
0x1d56d00: 0
0x1d56d60: 14
```

Reproducible offline commands:

```bash
BIN=/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer

sha256sum "$BIN"
file "$BIN"
readelf -h -W "$BIN"
readelf -S -W "$BIN" | sed -n '1,80p'

objdump -d -M intel --start-address=0x1d56a00 --stop-address=0x1d56df0 "$BIN"
objdump -d -M intel --start-address=0x1d56d60 --stop-address=0x1d56f60 "$BIN"
objdump -d -M intel --start-address=0x83a260 --stop-address=0x83a3b0 "$BIN"
objdump -d -M intel --start-address=0x3522bb0 --stop-address=0x3522c60 "$BIN"

objdump -d -M intel "$BIN" |
  awk '/call/ {for (i=1;i<=NF;i++) if ($i ~ /^1d56(a30|ae0|b60|c00|c70|d00|d60)$/) count[$i]++}
       END {for (t in count) print t, count[t]}' | sort
```

This table is durable internal static evidence only. It does not prove UE4 flag names,
runtime invalidation semantics, post-callback safety, or a public/persistent
`ResourceHandle`.

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
