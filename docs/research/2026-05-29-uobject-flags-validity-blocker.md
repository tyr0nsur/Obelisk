# UObject Flags Validity Blocker

## Objective

Record what the current offline evidence can and cannot say about `UObject+0x8`
flags in the ARK Linux `ShooterGameServer` binary before any internal
`ResourceHandle` work depends on object validity, destroyed-state, or stale-handle
revalidation.

This note used only existing scripts, copied/offline static artifacts, copied core
evidence packs, and existing research notes. It did not attach to a process, create a
core, touch live runtime markers, run ReflectionScanner, stage commits, push, or post to
Discord.

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

- `missing_gobjects_coherent_field_window`
- unproven `FUObjectItem+0x8` serial lifetime/reuse behavior
- zero serial samples in copied cores
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
