# Static GObjects Field-Window Audit

## Objective

Audit the offline static "field-window reconciliation" for the
`GUObjectArray`/`GObjects` research candidate `0x595b7e0`, using only the
copied static artifacts under:

```text
/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529
```

No server paths or runtime probes were used. This note reconstructs the requested
windows and keeps the gate non-promotable unless a coherent root/chunks/count/serial
path is demonstrated.

## Environment

- Obelisk commit at audit time: `a6b2649b4895a92c84b3c7c14f67a0b9db2748b5`
- Offline binary:
  `/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer`
- Binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Binary type: stripped ELF64 x86-64 executable
- Tool versions:
  - `GNU objdump (GNU Binutils for Ubuntu) 2.42`
  - `GNU readelf (GNU Binutils for Ubuntu) 2.42`
  - `jq-1.7`

The prebuilt objdump/readelf artifacts have verified provenance sidecars:

```text
ShooterGameServer.objdump                  f2d4f2ed10e3dd85e3c90ec2d66910c2b1458b138d265a585b63a3499e793524
ShooterGameServer.readelf-sections.txt     95ee4a2294d86423cafed2f8621ca4c5ea74cef6f421b4726b66e20420d59530
ShooterGameServer.readelf-programs.txt     81d140d2580eca57d5c416a605c4d93cdbf1d42ac9a720e75d62befa180940ee
ShooterGameServer                          7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
```

Relevant ELF placement:

```text
.text  0x0648400..0x3f6170f AX
.bss   0x58446c0..0x5a25b90 WA
LOAD   0x400000..0x5604aac R E
LOAD   0x5805000..0x5a25b90 RW
```

`0x595b7e0` is in `.bss` and in the RW LOAD segment.

## Static Evidence Summary

`static-global-evidence.json` still marks `gobjects=0x595b7e0` as blocked:

```text
static_contract.satisfied=false
static_contract.blockers=["missing_gobjects_coherent_field_window"]
promotion_gate.ready=false
promotion blockers:
  - static_only_evidence
  - candidate_static_contract_blocked / missing_gobjects_coherent_field_window
```

Analyzer field labels for this audit:

```text
gobjects.root    0x595b7e0  base/root struct address, also base+0 first int field
gobjects.chunks  0x595b7f0  base+0x10
gobjects.count   0x595b804  base+0x24
gobjects.serial  0x595b838  base+0x58
```

The strongest reconciled layout is consistent with UE4's
`FUObjectArray` containing an `FChunkedFixedUObjectArray` at `base+0x10`:

```text
base+0x10  chunks pointer
base+0x20  max elements-like value, initialized to 0xc10000
base+0x24  count/num elements-like value
base+0x28  max chunks-like value, initialized to 0xc1
base+0x2c  num chunks-like value
base+0x58  serial/master serial-like counter
```

This is useful field evidence, but it is not a promotion proof.

## Reconstructed Windows

### `0x1d4a8b8..0x1d4aa27`

Classification: initialization of the object-array storage and count fields.

Key instructions:

```text
0x1d4a8ef: mov DWORD PTR [rip+...],0xffffffff  # 0x595b7e0  root/base+0x0 field
0x1d4a903: mov DWORD PTR [rip+...],0xc10000    # 0x595b800  max elements-like field
0x1d4a8f9: mov DWORD PTR [rip+...],0xc1        # 0x595b808  max chunks-like field
0x1d4a91a: mov QWORD PTR [rip+...],r15         # 0x595b7f0  chunks pointer
0x1d4a930: mov eax,DWORD PTR [rip+...]         # 0x595b804  count load
0x1d4a960: mov r15,QWORD PTR [rip+...]         # 0x595b7f0  chunks reload
0x1d4a9d4: lock cmpxchg QWORD PTR [r15+rdx*8],rcx
0x1d4a9e7: mov DWORD PTR [rip+...],ebx         # 0x595b80c  num chunks-like field
0x1d4aa01: mov DWORD PTR [rip+...],eax         # 0x595b804  count store
0x1d4aa07: mov BYTE PTR [rip+...],0x1          # 0x595b840  initialized-like flag
```

Control/data-flow:

- Allocates `0x608` bytes for the chunks pointer array, matching `0xc1 * 8`.
- Stores that allocation at `0x595b7f0`.
- Computes required chunks from `count + 0xd6d7`, shifts by `0x10`, and allocates
  `0x100000` byte chunks.
- Publishes each chunk with `lock cmpxchg [chunks + num_chunks * 8], new_chunk`.
- Adds `0xd6d8` to `0x595b804`.

Reconciliation: this window strongly connects the base struct, chunks and count.
It does not touch the serial counter at `0x595b838`, so it is not a complete
root/chunks/count/serial field window.

### `0x1d56970..0x1d56eb0`

Classification: object handle lookup/accessor family plus serial assignment.

Key instructions:

```text
0x1d5698e: cmp DWORD PTR [rip+...],eax         # 0x595b804  count bound
0x1d569b0: mov rdx,QWORD PTR [rip+...]         # 0x595b7f0  chunks
0x1d569d3: lock xadd DWORD PTR [rip+...],r15d  # 0x595b838  serial
0x1d56a49: cmp DWORD PTR [rip+...],edi         # 0x595b804  count bound
0x1d56a6e: mov rcx,QWORD PTR [rip+...]         # 0x595b7f0  chunks
0x1d56b10: mov rsi,QWORD PTR [rip+...]         # 0x595b7f0  chunks
0x1d56c32: mov rsi,QWORD PTR [rip+...]         # 0x595b7f0  chunks
0x1d56d32: mov rsi,QWORD PTR [rip+...]         # 0x595b7f0  chunks
0x1d56e30: cmp DWORD PTR [rip+...],eax         # 0x595b804  count bound
0x1d56e52: mov rdx,QWORD PTR [rip+...]         # 0x595b7f0  chunks
0x1d56e75: lock xadd DWORD PTR [rip+...],r15d  # 0x595b838  serial
```

Control/data-flow:

- Treats input handles as `{index, serial}` pairs: index at offset `0`, serial at
  offset `4`.
- Rejects zero serials, negative indices, and indices outside `0x595b804`.
- Computes chunk index with signed-safe division by `0x10000`, then derives the
  in-chunk item offset with `index % 0x10000` and item stride `0x10`.
- Loads the object item with `chunks[chunk_index] + item_index * 0x10`.
- Compares item serial at `FUObjectItem+0x8` against the handle serial.
- Generates serial numbers with `lock xadd` on `0x595b838`, then publishes the
  serial into the item with `lock cmpxchg`.

Reconciliation: this is the strongest chunks/count/serial window. It does not
reference `0x595b7e0` as the base/root address in the same local path; therefore it
does not close the full static contract by itself.

### `0x79ce22..0x79cea6`

Classification: startup/cache scan for the first non-null object item.

Key instructions:

```text
0x79ce22: mov QWORD PTR [rip+...],0x595b7e0  # cache slot 0x5958128
0x79ce42: mov ecx,DWORD PTR [rip+...]        # 0x595b804 count
0x79ce4d: mov rdx,QWORD PTR [rip+...]        # 0x595b7f0 chunks
0x79ce60..0x79ce92: loop index 0..count-1, chunk index / item stride 0x10
0x79ce97: mov DWORD PTR [rip+...],eax        # cache first index at 0x5958130
0x79ce9d: mov QWORD PTR [rip+...],rsi        # cache first item at 0x5958138
```

Control/data-flow:

- Stores the immediate candidate address `0x595b7e0` into a separate cache slot.
- Reads count and chunks directly from `0x595b804` and `0x595b7f0`.
- Walks indices until it finds a non-null `FUObjectItem.Object` pointer.
- Caches the first found index and item pointer outside the candidate struct.

Reconciliation: this connects the candidate base immediate with chunks/count-shaped
lookup behavior, but the immediate is stored into a cache slot rather than used as a
base register for field accesses. It does not touch `serial`.

### `0x1cdb239..0x1cdb37d`

Classification: reset plus cache scan variant for first non-null object item.

Key instructions:

```text
0x1cdb239: mov DWORD PTR [rip+...],0x0       # 0x595b7e0 root/base+0x0 reset
0x1cdb2d4: mov QWORD PTR [rip+...],0x595b7e0 # cache slot 0x5958128
0x1cdb2fd: mov eax,DWORD PTR [rip+...]       # 0x595b7e4 optional cached index source
0x1cdb314: mov edx,DWORD PTR [rip+...]       # 0x595b804 count
0x1cdb31a: mov rsi,QWORD PTR [rip+...]       # 0x595b7f0 chunks
0x1cdb330..0x1cdb362: loop index 0..count-1, chunk index / item stride 0x10
0x1cdb367: mov DWORD PTR [rip+...],eax       # cache first index at 0x5958130
0x1cdb36d: mov QWORD PTR [rip+...],rcx       # cache first item at 0x5958138
```

Control/data-flow:

- Resets the first dword at `0x595b7e0`.
- Resets cache state around `0x5958128..0x5958154`.
- Stores the immediate `0x595b7e0` into the cache root slot.
- Reads `count` and `chunks`, then performs the same chunked `FUObjectItem` scan
  shape as `0x79ce22`.

Reconciliation: this is a useful reset/cache path for the candidate, but again it
lacks `serial` and uses the base address primarily as an immediate cache value.

## Window Xref Reconciliation

Flattening `static-global-xrefs.json` for the four requested ranges produced these
field hits:

```text
window 0x1d4a8b8..0x1d4aa27:
  root:   0x1d4a8ef -> 0x595b7e0 store
  chunks: 0x1d4a91a -> 0x595b7f0 store; 0x1d4a960 -> 0x595b7f0 load
  count:  0x1d4a930 -> 0x595b804 load; 0x1d4a9f6 -> load; 0x1d4aa01 -> store
  serial: none

window 0x1d56970..0x1d56eb0:
  root:   none
  chunks: 10 loads from 0x595b7f0
  count:  9 bounds checks against 0x595b804
  serial: 0x1d569d3 and 0x1d56e75 lock xadd stores to 0x595b838

window 0x79ce22..0x79cea6:
  root:   0x79ce22 immediate 0x595b7e0 stored to cache slot 0x5958128
  chunks: 0x79ce4d -> 0x595b7f0 load
  count:  0x79ce42 -> 0x595b804 load
  serial: none

window 0x1cdb239..0x1cdb37d:
  root:   0x1cdb239 -> 0x595b7e0 store; 0x1cdb2d4 immediate 0x595b7e0 cached
  chunks: 0x1cdb31a -> 0x595b7f0 load
  count:  0x1cdb314 -> 0x595b804 load
  serial: none
```

## Continuation Audit

The machine-readable anchor groups in `static-global-xrefs.json` add more
root/chunks/count evidence, but they do not change the blocker:

```text
root/chunks/count windows:
  0xb3643f..0xb36771    span=818  xrefs=12  non-oversized
  0x1d4a8ef..0x1d4aa01  span=274  xrefs=6   non-oversized
  0x1d14269..0x1d14337  span=206  xrefs=5   non-oversized
  0x1cdb239..0x1cdb31a  span=225  xrefs=4   non-oversized
  0x1cdb6d5..0x1cdb71b  span=70   xrefs=3   non-oversized
  0x79ce22..0x79ce4d    span=43   xrefs=3   non-oversized

serial-bearing window:
  0x1d5698e..0x1d56e75  span=1255 xrefs=20  non-oversized
```

Only two serial xrefs exist in the current static artifact, both in the
`0x1d5698e..0x1d56e75` handle/serial window:

```text
0x1d569d3: lock xadd DWORD PTR [rip+...]  # 0x595b838
0x1d56e75: lock xadd DWORD PTR [rip+...]  # 0x595b838
```

That window repeatedly validates handle indices against `0x595b804`, loads
`0x595b7f0`, computes `chunk[index >> 16] + (index & 0xffff) * 0x10`, compares the
handle serial against `FUObjectItem+0x8`, and publishes new serials with
`lock cmpxchg` on the same `+0x8` item dword after incrementing `0x595b838`. It still
does not reference `0x595b7e0` locally as either a RIP-relative root field or a base
argument.

The additional root/chunks/count windows are useful but incomplete:

- `0xb3643f..0xb36771` repeats bounded object-item lookup and includes immediate
  `0x595b7e0` cache/state setup later in the same local neighborhood, but it does not
  touch `0x595b838`.
- `0x1d14269..0x1d14337`, `0x1cdb6d5..0x1cdb71b`, and `0x79ce22..0x79ce4d` are cache or
  first-non-null-object walks over the chunked array; none reaches serial.
- the only code-backed RIP-relative references to `0x595b7e0` itself are reset/init
  stores at `0x81f118`, `0x1cdb239`, and `0x1d4a8ef`, again outside the serial window.

Therefore the exact static evidence still missing is one of:

1. a non-oversized executable instruction window where `gobjects.root`,
   `gobjects.chunks`, `gobjects.count`, and `gobjects.serial` all appear as
   code-backed field references with coherent control/data flow; or
2. an independent decompiler/static path that proves the root-bearing init/cache path and
   the serial-bearing handle path operate on the same `FUObjectArray` instance, without
   relying on oversized nearest-symbol buckets, immediate-only piggybacking, or global
   xref aggregation.

Even if that static gap is closed, static evidence remains non-promotable by itself. Later
second-core reconciliation strengthens offline reflection use of `0x595b7e0`, but it does
not make the `GUObjectArray` contract runtime-stable or public.

## Cross-Note Consistency

Second-source notes may report `promotion_gate.ready=true` for selected UFunction target
sets. That status applies only to the named sanitized reflected layout comparison that
produced it. This GObjects audit does not claim `minimal-second-source-intake` is complete,
does not clear the static `GObjects` blocker, does not promote the global
`GUObjectArray` contract, and does not make `0x595b7e0` a stable runtime offset while
`missing_gobjects_coherent_field_window` remains active.

## Result

The field-window audit strengthens the local layout model for
`gobjects=0x595b7e0`:

```text
base/root struct: 0x595b7e0
chunks:           0x595b7f0  (base+0x10)
count:            0x595b804  (base+0x24)
serial:           0x595b838  (base+0x58)
item stride:       0x10
chunk size:        0x10000 entries
```

It does not produce the strong proof required to promote a runtime contract. The
requested windows split the evidence into:

- root/chunks/count initialization or cache scans without serial;
- chunks/count/serial lookup helpers without an in-window root/base reference.

Therefore the existing blocker remains correct:

```text
missing_gobjects_coherent_field_window
promotion_gate.ready=false
```

## Smallest Evidence Improvement

A read-only near-miss scan over the existing `static-global-xrefs.json`, using the
builder's current grouping constants (`0x100` max gap; oversized at `64` xrefs or
`0x1000` bytes), found only three non-oversized code-backed RIP-relative windows that
cover three of the four required fields:

```text
0x1cdb239..0x1cdb31a  root/chunks/count   missing serial
0x1d4a8ef..0x1d4aa01  root/chunks/count   missing serial
0x1d5698e..0x1d56e75  chunks/count/serial missing root
```

The next smallest offline improvement is to make this near-miss evidence
machine-readable in `build_static_global_promotion_evidence.py` while preserving
`missing_gobjects_coherent_field_window` and `promotion_gate.ready=false`. That would
reduce the blocker from a generic missing coherent window to an explicit split:
root-bearing init/cache paths lack serial, and the serial-bearing handle path lacks a
code-backed root/base field reference.

## Commands Used

Representative command trail:

```bash
sed -n '1,260p' /home/flowcommunity-ark/Obelisk/agent-skills/obelisk-static-binary-analysis/SKILL.md
sed -n '1,220p' /home/flowcommunity-ark/Obelisk/agent-skills/obelisk-tooling-discipline/SKILL.md
sed -n '1,260p' /home/flowcommunity-ark/Obelisk/agent-skills/obelisk-reversing-research/SKILL.md
find /home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529 -maxdepth 3 -type f | sort
jq . /home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/manifest.json
jq . /home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.objdump.provenance.json
sha256sum /home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.objdump
sha256sum /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
file /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
objdump --version
readelf --version
jq --version
rg -n '\.text|\.bss|LOAD' /home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.readelf-sections.txt /home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.readelf-programs.txt
jq '.targets' /home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/static-global-xrefs.json
jq '.candidates[] | select(.address=="0x595b7e0")' /home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/static-global-evidence.json
jq '.promotion_gate' /home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/static-global-evidence.json
objdump -d -M intel --start-address=0x1d4a8b8 --stop-address=0x1d4aa27 /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
objdump -d -M intel --start-address=0x1d56970 --stop-address=0x1d56eb0 /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
objdump -d -M intel --start-address=0x79ce22 --stop-address=0x79cea6 /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
objdump -d -M intel --start-address=0x1cdb239 --stop-address=0x1cdb37d /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
jq -r '.xrefs | to_entries[] as $target | $target.value[] | [.instruction_address, .target_label, .access, .semantic.field, .semantic.role, .target_address, .instruction] | @tsv' /home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/static-global-xrefs.json | gawk 'function h(x){return strtonum(x)} BEGIN{ranges[1]="0x1d4a8b8 0x1d4aa27"; ranges[2]="0x1d56970 0x1d56eb0"; ranges[3]="0x79ce22 0x79cea6"; ranges[4]="0x1cdb239 0x1cdb37d"} {addr=h($1); for (i=1;i<=4;i++){split(ranges[i],r," "); if(addr>=h(r[1]) && addr<h(r[2])) print i "\t" $0}}'
```

## Current No-Repeat Checkpoint

Before any promotion beyond research-candidate, require either:

1. a narrower independent static path that uses the root/base address to derive
   `chunks`, `count`, and `serial` in one coherent local control-flow region; or
2. separately approved runtime/public-contract evidence that names the promotion being
   attempted.

Do not rerun broad FName/GObjects scans, core capture, or isolated-core enumeration for
the current binary hash from this note. Reopen this route only for a new binary hash or
contradictory artifact evidence. Until a separate promotion gate accepts more, `0x595b7e0`
remains binary-hash-specific research evidence, not a stable runtime offset contract.
