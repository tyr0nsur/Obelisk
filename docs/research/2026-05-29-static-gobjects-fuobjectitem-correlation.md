# Static GObjects / FUObjectItem Correlation

## Objective

Correlate the improved static `GObjects` near-miss windows with the current copied-core
`FUObjectItem` samples from `2026-05-29-next-offline-gold-extraction.md`, without live
server access, new runtime probing, or heavy scans.

## Environment

- Worktree: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-29
- Binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Static source artifacts:
  `/home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529`
- Regenerated lightweight static report:
  `/tmp/obelisk-static-gobjects-near-miss-20260529/manifest.json`
- Core evidence source:
  `/servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/pack/manifest.json`
- `GObjects` candidate: `0x595b7e0`
- Artifact-specific FName root slot used by the core sample: `0x5956f30`
- Live-server impact: none.

The static report was regenerated from existing objdump/readelf text plus verified
provenance sidecars. No new objdump/readelf scan over the protected server tree was run.

## Commands

```bash
python3 scripts/build_static_global_promotion_evidence.py \
  --binary /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer \
  --candidate gobjects=0x595b7e0 \
  --candidate-kind gobjects=gobjects \
  --output-dir /tmp/obelisk-static-gobjects-near-miss-20260529 \
  --objdump /home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.objdump \
  --readelf-programs /home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.readelf-programs.txt \
  --readelf-sections /home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.readelf-sections.txt \
  --json

jq '.candidates[] | select(.label=="gobjects") | .static_contract.near_miss.windows[:3]' \
  /tmp/obelisk-static-gobjects-near-miss-20260529/manifest.json

jq '.promotion_gate' /tmp/obelisk-static-gobjects-near-miss-20260529/manifest.json
```

## Static Near-Miss Correlation

The regenerated static report sees code-backed RIP-relative xrefs for all four required
labels in aggregate:

```text
gobjects.root    3
gobjects.chunks  8016
gobjects.count   5870
gobjects.serial  2
```

It still has no coherent non-oversized window containing `root`, `chunks`, `count`, and
`serial` together:

```text
static_contract.satisfied=false
static_contract.blockers=["missing_gobjects_coherent_field_window"]
promotion_gate.ready=false
```

The three closest near-miss windows are:

| Window | Present labels | Missing label | Correlation with sampled evidence |
| --- | --- | --- | --- |
| `0x1d5698e..0x1d56e75` | `chunks`, `count`, `serial` | `root` | This is compatible with the sampled `GObjects[index]` membership and the static handle-accessor model: it bounds indices by `0x595b804`, loads chunks from `0x595b7f0`, increments `0x595b838`, and compares/publishes serials at `FUObjectItem+0x8`. It does not locally prove those fields belong to the `0x595b7e0` root. |
| `0x1d4a8ef..0x1d4aa01` | `root`, `chunks`, `count` | `serial` | This supports the root/chunk/count layout used by the copied-core samples, where the five sampled indices round-trip through `GObjects[index]`. It never touches `0x595b838` or the item serial slot, so it cannot prove handle invalidation semantics. |
| `0x1cdb239..0x1cdb31a` | `root`, `chunks`, `count` | `serial` | This reset/cache scan also matches chunked `FUObjectItem` traversal and object membership. It remains a cache/root path, not a serial publication path. |

## Copied-Core FUObjectItem Evidence

The current copied-core pack sampled indices `0`, `1`, `25447`, `19479`, and `19489`.
All five passed direct `GObjects[index]` membership checks using the artifact-specific
FName root and resolved to the expected object/class names. The neutral item fields were:

```text
index 0:     item+0x8 low dword=0, item+0xc=1919251567
index 1:     item+0x8 low dword=0, item+0xc=1701667175
index 25447: item+0x8 low dword=0, item+0xc=1701016181
index 19479: item+0x8 low dword=0, item+0xc=1344421223
index 19489: item+0x8 low dword=0, item+0xc=1382510185
```

This does not reject the static `FUObjectItem+0x8` serial path. The static accessor rejects
zero handle serials and compares nonzero handle serials against `FUObjectItem+0x8`; the
sampled objects simply do not show published nonzero serials in this frozen core. The
nonzero `FUObjectItem+0xc` values stay unknown and are not promoted as serials.

## Result

The static and copied-core evidence are mutually compatible:

- static root/chunks/count windows explain the chunked object membership used by the core
  samples;
- the static serial window explains a plausible weak-handle serial path at
  `FUObjectItem+0x8`;
- the sampled `FUObjectItem+0x8` zeros show that the current core does not prove serial
  lifetime or reuse behavior;
- no single static window proves `0x595b7e0` root plus chunks/count/serial in one coherent
  local path.

Therefore `0x595b7e0` remains a binary-hash-specific `GUObjectArray` research candidate,
not a promoted runtime global. The active static blocker remains:

```text
missing_gobjects_coherent_field_window
```

## Next Static Evidence Blocker

The next static blocker is a code-backed proof that the serial-bearing handle path and the
root-bearing init/cache paths operate on the same `FUObjectArray` instance. The preferred
evidence is either:

1. a non-oversized executable instruction window with coherent local flow over
   `gobjects.root`, `gobjects.chunks`, `gobjects.count`, and `gobjects.serial`; or
2. an independent decompiler/static path that connects the `0x595b7e0` root to the
   `0x595b838` serial path without global xref aggregation or immediate-only
   piggybacking.

Even after that, promotion still needs distinct second-source runtime/core evidence before
the `GUObjectArray` contract can move beyond candidate-only.

## Targeted Static Follow-Up

Objective: take the smallest next offline static step toward connecting the
root/chunks/count and serial-bearing paths for the same `FUObjectArray`, without new
runtime access, broad objdump generation, or live server contact.

Environment additions:

```text
Obelisk commit: a6b2649
objdump: GNU objdump (GNU Binutils for Ubuntu) 2.42
binary: /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
binary SHA256: 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
file: ELF 64-bit LSB executable, x86-64, dynamically linked, stripped
```

Commands:

```bash
git rev-parse --short HEAD
objdump --version | head -1
sha256sum /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
file /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer

objdump -d -M intel --start-address=0x1d4a850 --stop-address=0x1d4aa80 \
  /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer

objdump -d -M intel --start-address=0x1d568f0 --stop-address=0x1d56ef0 \
  /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer

objdump -d -M intel --start-address=0x1d56d60 --stop-address=0x1d56ed0 \
  /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer

jq '.promotion_gate, (.candidates[] | select(.label=="gobjects") | .static_contract.blockers)' \
  /tmp/obelisk-static-gobjects-near-miss-20260529/manifest.json
```

Targeted evidence:

- `0x1d4a8b0..0x1d4aa18` is a compact init path for the candidate's adjacent global
  fields. It writes `0xffffffff` to `0x595b7e0`, allocates/zeros chunk storage, stores the
  chunk pointer at `0x595b7f0`, reads then updates count at `0x595b804`, and toggles
  `0x595b840`. This supports treating `0x595b7e0` as the base of the same global object
  whose `+0x10` chunks and `+0x24` count are used by the copied-core membership checks.
- `0x1d56970..0x1d56a26` constructs/publishes a weak-handle-like pair from a `UObject`
  pointer: it reads `UObject+0xc` as the object index, bounds it against `0x595b804`,
  loads chunk storage from `0x595b7f0`, computes `chunk[index & 0xffff] * 0x10`, reads
  `FUObjectItem+0x8`, and when zero allocates a new serial through
  `lock xadd DWORD PTR [0x595b838]`.
- `0x1d56d60..0x1d56ecd` repeats the same object-array membership path before an
  observer/callback call and then repeats the serial publication path: it validates a
  handle against `0x595b804`, `0x595b7f0`, and `FUObjectItem+0x8`, later reads
  `UObject+0xc`, recomputes the same chunked item address, and publishes through
  `0x595b838` if the item serial is still zero.

This is a stronger static correlation than the previous aggregate near-miss: the serial
paths do not merely touch an isolated `0x595b838`; they first resolve the item through the
same count/chunks globals initialized beside `0x595b7e0`. However, it still is not a
promotion-grade proof. The serial accessors do not contain a local RIP-relative reference
to `0x595b7e0` itself, and no decompiler/type database is available in this environment to
recover a named `FUObjectArray` instance or member method.

Rejected follow-up:

```bash
rg "call\s+1d56970|call\s+1d56d60|call\s+1d56a30|call\s+1d56ae0|call\s+1d56d00" \
  /home/flowcommunity-ark/obelisk-artifacts/static-global-preflight-20260529/ShooterGameServer.objdump | wc -l
```

Result: `12795` direct-call hits with this broad matcher. That is not a small correlating
step and does not improve the root-to-serial proof without a narrower callgraph or
decompiler context.

Result: `0x595b7e0` remains a hash-scoped `GUObjectArray` research candidate. The next
exact blocker is no longer "are the serial path and object membership path compatible";
they are compatible and share `0x595b7f0`/`0x595b804`. The exact remaining blocker is:

```text
missing local/decompiler proof that the serial-bearing accessors' 0x595b7f0/0x595b804/0x595b838 globals are members of the same FUObjectArray instance whose base/root is 0x595b7e0
```

The machine gate remains unchanged:

```text
promotion_gate.ready=false
static_contract.blockers=["missing_gobjects_coherent_field_window"]
```

## Smallest Decompiler/Static Plan

Objective: prove or reject whether `0x595b7e0`, `0x595b7f0`, `0x595b804`, and
`0x595b838` are fields of the same `FUObjectArray` instance, without broad scans or
runtime probing.

Use only the copied/offline binary:

```text
/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
```

Preferred path: open an existing Ghidra project for this binary if one exists. If no
project exists, create a temporary project with auto-analysis disabled and define only
the known target functions/ranges before decompiling. Do not start with Ghidra whole
program analyzer output as the claim source.

Target only these ranges first:

```text
0x1d4a8b0..0x1d4aa18  root/chunks/count init
0x1d56970..0x1d56a26  weak-handle serial publish from UObject index
0x1d56d60..0x1d56ecd  repeated handle validate/publish path
```

Optional tie-breaker ranges, only if the three primary ranges are inconclusive:

```text
0x79ce22..0x79cea6    cache slot receives immediate 0x595b7e0 plus chunks/count reads
0x1cdb239..0x1cdb37d  reset/cache root path plus chunks/count traversal
```

Ghidra evidence to record:

- function start/end for each target range;
- decompiler output or p-code summary showing the exact memory references;
- whether the decompiler represents the globals as one base object plus member offsets
  `+0x0`, `+0x10`, `+0x24`, and `+0x58`, or as unrelated globals;
- call edges between the init/cache ranges and the serial ranges, if present in the
  same local caller neighborhood;
- any recovered constructor/static-init path that uses `0x595b7e0` as the base and then
  accesses `0x595b838` as `base+0x58`.

Rizin fallback, if Ghidra is unavailable: use fixed seeks/disassembly only, not `-A`,
`aaa`, or broad `axt` sweeps. The fallback can corroborate instruction-level flow but
will not by itself close the blocker unless it finds a local base-derived access:

```bash
rizin -q \
  -c 's 0x1d4a8b0; pd 120' \
  -c 's 0x1d56970; pd 100' \
  -c 's 0x1d56d60; pd 130' \
  -c q \
  /home/flowcommunity-ark/obelisk-artifacts/offline-binaries/7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/ShooterGameServer
```

Accept as static same-instance proof only if one of these bounded checks succeeds:

1. a decompiled local path derives `0x595b7f0`, `0x595b804`, and `0x595b838` from the
   base `0x595b7e0` or from a single recovered object symbol representing that base;
2. a constructor/static-init path initializes or passes a single object at
   `0x595b7e0` and the same decompiled path reaches the serial counter at
   `0x595b838`;
3. a narrow caller decompilation shows the root-bearing path and serial-bearing path
   operate on the same recovered global object, not merely on adjacent absolute
   addresses.

Reject this static path, leaving the blocker unchanged, if the decompiler shows only
independent absolute globals, if the connection depends on manual structure overlays
alone, or if proving the call relationship requires broad callgraph/xref enumeration.

Expected result if rejected:

```text
promotion_gate.ready=false
static_contract.blockers=["missing_gobjects_coherent_field_window"]
remaining_blocker="no bounded decompiler/static path proves 0x595b838 is base+0x58 of the same FUObjectArray rooted at 0x595b7e0"
```
