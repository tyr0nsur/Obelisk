# UObject Flags Validity Blocker

## Objective

Record what the current offline evidence can and cannot say about `UObject+0x8`
flags in the ARK Linux `ShooterGameServer` binary before any internal
`ResourceHandle` work depends on object validity, destroyed-state, or stale-handle
revalidation.

This note used only existing scripts, copied/offline static artifacts, copied core
evidence packs, and existing research notes. It did not attach to a process, create a
core, touch live runtime markers, run ReflectionScanner, stage commits, push, or post an
external status update.

## Environment

- Obelisk commit: `a6b2649`
- Binary:
  `/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer`
- Binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- objdump:
  `GNU objdump (GNU Binutils for Ubuntu) 2.42`
- Static artifact root:
  `/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529`
- Copied core evidence:
  `/servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/pack`
- Second-source GObjects reconciliation:
  `/servidor/ark/workspace-offline/gobjects-reconcile-second-source-20260529T034447Z/gobjects-reconciliation.json`

## What Is Evidenced

`UObject+0x8` is a 32-bit object flag field for this binary-hash-scoped layout.
The evidence paths are:

- `scripts/enumerate_core_uobjects.py` reads `UOBJECT_FLAGS_OFFSET = 0x8`,
  `UOBJECT_INTERNAL_INDEX_OFFSET = 0xc`, class at `+0x10`, name at `+0x18`, and outer at
  `+0x20`.
- `ue/RuntimeReflection.h` stores the same layout as `UObjectObjectFlags = 0x08`.
- `ue/RuntimeReflection.cpp` and `ue/ReflectionScanner.cpp` currently treat flags only as
  a plausibility field and reject negative signed values; this is an Obelisk guard, not
  an accepted ARK lifetime semantic.
- Copied-core samples read plausible object headers and matching `InternalIndex` values
  through `GObjects[index]` point checks.

The static weak-handle/object-validity helper family at
`0x1d56970..0x1d56eb0` uses two flags masks after resolving a `UObject*` from an
`{index, serial}` pair:

```text
0x1d56ab1: mov ecx,DWORD PTR [rax+0x8]
0x1d56ab6: and eax,0x100
0x1d56ac5: and ecx,0x4000

0x1d56b41: mov eax,DWORD PTR [rcx+0x8]
0x1d56b44: test ah,0x1      # 0x100
0x1d56b55: test ah,0x40     # 0x4000

0x1d56c60: test BYTE PTR [rcx+0x9],0x41  # 0x100 | 0x4000
0x1d56ccf: mov edx,DWORD PTR [rcx+0x8]
0x1d56cd4: and edi,0x100
0x1d56ce3: test dh,0x40     # 0x4000

0x1d56dec: test BYTE PTR [rax+0x9],0x1   # 0x100
```

Therefore the current static evidence supports only these neutral claims:

- `0x100` is a `UObject+0x8` bit consulted by ARK's weak-handle/object-validity helpers.
- `0x4000` is a `UObject+0x8` bit consulted by the same helper family.
- Several helper variants reject or invert results when either or both bits are present,
  depending on caller options.
- The serial path validates `{index, serial}` through `GObjects.count`, `GObjects.chunks`,
  `FUObjectItem+0x8`, then optionally checks `UObject+0x8`.

Copied-core samples that passed object-array membership had these flags:

```text
fuobjectitem-dino-reconcile core:
  index 0      /Script/CoreUObject   class Package   flags=0x81
  index 1      Object                class Class     flags=0xc7
  index 25447  ServerChat            class Function  flags=0xc5
  index 19479  AddPassenger          class Function  flags=0xc5
  index 19489  AllowCarryCharacter   class Function  flags=0xc5

second-source GObjects reconciliation:
  index 0      /Script/CoreUObject   class Package   flags=0x81
  index 1      Object                class Class     flags=0xc7
  index 25447  ServerChat            class Function  flags=0xc5
```

The older primary core note also observed `obj0 flags=0x400081`, which proves that
higher object flag bits may appear in real samples, but the current evidence does not map
that bit to a validity or lifetime semantic.

## What Is Not Evidenced

The current offline artifacts do not prove accepted names or lifecycle semantics for the
bits:

- Do not document `0x100` as pending-kill, unreachable, garbage, destroyed, or any named
  UE4 flag without a separate version-matched UE source comparison or decompiler path.
- Do not document `0x4000` as pending-kill, begin-destroyed, newer-version, or any named
  UE4 flag without the same second evidence path.
- No current sample shows an object rejected because `0x100` or `0x4000` was set.
- No current sample proves which bit represents pending kill, unreachable, begin destroy,
  finish destroy, slot reuse, or garbage-collection reachability for ARK's exact UE4
  build.
- No current static path proves that checking only these two bits is enough to validate
  a resource object after the hook frame.
- The Obelisk `flags >= 0` plausibility check does not mean bit 31 is an ARK validity bit.
  It only keeps obviously implausible signed values out of internal readers.

## ResourceHandle Boundary

For future internal `ResourceHandle` work, `UObject+0x8` can be used only as a recorded
candidate field. It must not be used as a public or persistent validity contract yet.

The blocker should be documented as:

```text
uobject_flags_validity_semantics_unproven:
  UObject+0x8 is confirmed as a 32-bit object flags field for the current binary hash.
  Static weak-handle/object-validity helpers consult masks 0x100 and 0x4000 after
  GObjects index/serial validation, but offline evidence has not mapped those masks to
  version-matched UE4 lifetime names or proven destroyed/pending-kill/unreachable
  behavior. ResourceHandle revalidation must remain blocked beyond hook-frame-internal
  experiments until negative samples or an independent source/decompiler path prove the
  exact reject bits and their lifetime semantics.
```

This blocker is separate from, and additive to:

- static global promotion remains candidate-only even though later GObjects work found
  stronger same-base and two-core reconciliation evidence
- unproven `FUObjectItem+0x8` serial lifetime/reuse behavior; later full scans found
  repeatable nonzero serial candidates, so earlier zero-only samples are narrow historical
  evidence rather than the active blocker
- class/outer privacy and redaction policy
- public ABI/lifecycle/SDK consumer tests

## Reproducible Commands

```bash
git rev-parse --short HEAD
sha256sum /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
objdump --version | head -1

sed -n '1,260p' scripts/enumerate_core_uobjects.py
sed -n '1,130p' ue/RuntimeReflection.h
sed -n '190,220p' ue/RuntimeReflection.cpp
sed -n '330,340p' ue/ReflectionScanner.cpp

objdump -d -M intel --start-address=0x1d56a30 --stop-address=0x1d56ae0 \
  /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer

objdump -d -M intel --start-address=0x1d56ae0 --stop-address=0x1d56bf0 \
  /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer

objdump -d -M intel --start-address=0x1d56bf0 --stop-address=0x1d56d60 \
  /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer

objdump -d -M intel --start-address=0x1d56d60 --stop-address=0x1d56ed0 \
  /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer

sed -n '960,1085p' \
  /servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/pack/gdb-core.txt

jq '.samples[] | {label,index,object_name,class_name,uobject_flags:.uobject.flags,internal_index:.uobject.internal_index,item_dword_0x8,item_dword_0xc}' \
  /servidor/ark/workspace-offline/gobjects-reconcile-second-source-20260529T034447Z/gobjects-reconciliation.json
```

## Next Evidence Needed

The smallest useful next step is still offline-only:

1. Use a bounded decompiler/static pass on the existing helper family to recover caller
   options and return polarity for the `0x100` and `0x4000` branches.
2. Add a fixture/report format that records `UObject+0x8`, `flags & 0x100`, and
   `flags & 0x4000` for accepted and rejected samples without assigning UE flag names.
3. Accept named semantics only after either a version-matched UE4 source comparison or an
   independent decompiler path explains the masks and a copied-core/offline artifact
   demonstrates at least one rejected object state.

Until then, any `ResourceHandle` can be at most hook-frame-internal research scaffolding,
with no public handle, no post-callback lookup, and no promise that object-array
membership plus these two bits proves lifetime safety.

## 2026-05-29 Ghidra/Radare2 Targeted Update

After `radare2` and Ghidra headless became available, a bounded no-global-analysis pass
under `/servidor/ark/workspace-offline/static-ghidra-r2-uobject-validity-20260529T040322Z`
confirmed the current weak-object/handle helper shape:

```text
0x1d56a30:
  reads handle index from param[0] and serial from param[1]
  rejects serial == 0 and negative index
  bounds-checks index against 0x595b804
  loads chunks from 0x595b7f0
  computes FUObjectItem slot as chunks[index >> 16] + (index & 0xffff) * 0x10
  compares FUObjectItem+0x8 against the handle serial
  loads UObject* from FUObjectItem+0x0
  reads UObject flags at UObject+0x8
  tests masks 0x100 and 0x4000
```

Two bounded serial-publication candidates at `0x1d56980` and `0x1d56e20` also load
`0x595b7f0`/`0x595b804`, read `FUObjectItem+0x8`, and, when it is zero, allocate through
`lock xadd [0x595b838]` followed by `lock cmpxchg [FUObjectItem+0x8]`.

This strengthens `FUObjectItem+0x8` as the serial-backed field and `0x595b838` as a
serial counter candidate for this binary hash. It does not by itself prove named lifetime
semantics for `0x100`/`0x4000`, provide a rejected-object sample, or promote public
`ResourceHandle` revalidation.

## 2026-05-29 FUObjectArray Flag Sweep Update

A later bounded pass used the durable static pack at
`/servidor/ark/workspace-offline/gobjects-fuobjectarray-durable-pack-20260529T051759Z`.
It inspected only the existing `ShooterGameServer.objdump` for the same binary SHA256
`7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`; no server process,
marker, scanner, ptrace/gcore run, external status update, commit, or push was involved.

The function starting at `0x1d18a90` is useful evidence because it iterates over the
`FUObjectArray` chunks/count pair and writes object flags directly:

```text
0x1d18ada: mov eax,DWORD PTR [rip+0x3c42d24]  # 0x595b804 count
0x1d18ae5: mov rcx,QWORD PTR [rip+0x3c42d04]  # 0x595b7f0 chunks
0x1d18b33: mov rdi,QWORD PTR [rdi]            # FUObjectItem+0x0 UObject*
0x1d18b36: or  DWORD PTR [rdi+0x8],0x100      # set UObject+0x8 mask 0x100
```

The same function later performs a second pass over non-null object slots:

```text
0x1d18be0: mov rdi,QWORD PTR [rdx]            # FUObjectItem+0x0 UObject*
0x1d18be3: mov edx,DWORD PTR [rdi+0x8]
0x1d18be8: and esi,0x8100
0x1d18bee: cmp esi,0x100
0x1d18bf6: or  edx,0x8000
0x1d18bfc: mov DWORD PTR [rdi+0x8],edx
0x1d18bff: call QWORD PTR [rax+0x88]
```

This strengthens the neutral model:

- `UObject+0x8` is a mutable object-flags dword, not just a passive header field.
- `0x100` is mass-applied across live `FUObjectArray` object slots in this binary hash.
- `0x8000` is set on objects where `(flags & 0x8100) == 0x100`, followed by a virtual
  call at vtable offset `0x88`.
- The static path is consistent with the weak-helper evidence that later consults
  `0x100` and `0x4000`, but it does not map any mask to a version-matched UE4 lifecycle
  name.

This does not close `uobject_flags_validity_semantics_unproven`. The update still lacks:

- a copied-core negative sample where `0x100`, `0x4000`, or `0x8000` proves rejection;
- a decompiler/source-backed name for the masks in ARK's exact UE4 fork;
- proof that checking these bits after a plugin callback is a safe lifetime guarantee;
- a fail-closed runtime design for object identity, lookup, reuse, and unload behavior.

Therefore `ResourceHandle` remains blocked for public SDK work. The only safe use of this
evidence is internal research planning for flag sampling and decompiler-target selection.

## 2026-05-29 0x4000 Cross-Window Classification

A parallel bounded static audit classified additional windows and found real `0x4000`
accesses on the same `UObject+0x8` flags field:

```text
0x11ee150: test BYTE PTR [rdi+0x9],0x40      # flags & 0x4000 skip/reject branch
0x11ee1df: or   DWORD PTR [rax+0x8],0x4000   # marks prior object before holder clear
0x29829ed: test BYTE PTR [rbx+0x9],0x40      # after GObjects/FUObjectItem resolution
0x2982ad3: or   DWORD PTR [rax+0x8],0x4000   # mark/propagation path
0x298d4dd: or   DWORD PTR [rax+0x8],0x4000
0x2abee38: or   DWORD PTR [rax+0x8],0x4000
```

The strongest validation window is `0x2982920..0x2982b60`: it checks the same
`0x595b804` count and `0x595b7f0` chunk globals, resolves an `FUObjectItem`, loads the
`UObject*`, and then tests `BYTE [object+0x9],0x40`.

This confirms `0x4000` is an engine-side object flag consulted by reject/skip/mark paths.
It still does not prove the named lifetime semantic. Full copied-core scans remain
mask-negative for `0x100` and `0x4000`, so there is still no runtime negative sample that
would justify public post-callback object validity.

## 2026-05-29 Static Flag Semantics Update

A later read-only pass over the verified
`/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.objdump`
adds stronger internal semantics, but still does not promote public handles.

`0x100` is now a strong internal hard-invalid candidate tied to a garbage-collection
marking pass:

- the `0x1d18a90` pass iterates `FUObjectArray` through `0x595b804` and `0x595b7f0`;
- `0x1d18b36` mass-applies `or DWORD PTR [object+0x8],0x100`;
- a second pass checks `(flags & 0x8100) == 0x100`, sets `0x8000`, and calls
  `vtable+0x88`;
- binary strings include `GarbageCollection.cpp` and `CollectGarbage`;
- nearby code clears `0x100` with masks such as `0x7fffeff`.

`0x4000` is now a strong internal strict-invalid/stale-or-replaced candidate:

- weak helpers reject it in strict paths and allow it only in reviewed helper modes;
- `0x11ee150` skips when `flags & 0x4000` is set, then `0x11ee1df` marks a previous
  object with `0x4000` before clearing its holder;
- `0x29829ed` resolves through `FUObjectArray`, rejects/skips `0x4000`, and nearby paths
  propagate that bit to object/outer/related objects;
- a small set/clear sequence writes `0x4000`, calls `vtable+0x68`, then clears it with
  `0x7ffbfff`.

The names `RF_TagGarbageTemp` for `0x100` and `RF_NewerVersionExists` for `0x4000` are
plausible UE4 hypotheses only. Do not use those names as accepted ARK contracts until a
version-matched source or decompiler path is recorded.

Current policy:

```text
post_callback_resource_handle_ready=false
0x100: hard-invalid internal candidate
0x4000: strict-invalid internal candidate unless an explicitly reviewed helper mode allows it
required next evidence: controlled negative sample showing a valid {index, serial}
  resolving to an object with one of these bits and being rejected by the intended policy
```

Follow-up static negative-equivalent evidence is now represented by the post-RC offline
tooling in `scripts/build_uobject_flag_policy_report.py`,
`scripts/build_uobject_flag_transition_matrix.py`, and
`scripts/build_uobject_flag_sample_report.py`. The resulting artifacts must remain
`promotion_ready=false` and `post_callback_resource_handle_ready=false`; use them only as
internal support for future fail-closed handle-candidate design.
