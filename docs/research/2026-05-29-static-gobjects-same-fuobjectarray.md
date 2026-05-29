# Static GObjects Same FUObjectArray Check

## Objective

Check whether `0x595b7e0`, `0x595b7f0`, `0x595b804`, and `0x595b838` belong to the
same `FUObjectArray` / `GUObjectArray` candidate in the offline ARK
`ShooterGameServer` binary.

## Environment

- Obelisk commit: `a6b2649b4895`
- Binary:
  `/servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer`
- Same-hash alternate offline copy:
  `/servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/ShooterGameServer`
- Binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Tools: `objdump`, `readelf`, `radare2 5.5.0`, `scripts/build_static_global_promotion_evidence.py`
- Ghidra headless was available at `/usr/local/bin/analyzeHeadless`, but not run: the
  bounded constructor/destructor windows were sufficient for this static question, while a
  full Ghidra import/decompile pass would be broader than needed.

## Commands

```bash
sha256sum \
  /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer \
  /servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/ShooterGameServer

file /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer
readelf -S -W /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer
readelf -l -W /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer

objdump -d -M intel --start-address=0x79ce00 --stop-address=0x79cec0 \
  /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer
objdump -d -M intel --start-address=0x7a2780 --stop-address=0x7a27d8 \
  /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer
objdump -d -M intel --start-address=0x1d474e0 --stop-address=0x1d47640 \
  /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer
objdump -d -M intel --start-address=0x1d475a0 --stop-address=0x1d476d0 \
  /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer
objdump -d -M intel --start-address=0x1d476e0 --stop-address=0x1d477d0 \
  /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer
objdump -d -M intel --start-address=0x1d58fb0 --stop-address=0x1d59050 \
  /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer

r2 -2 -q -e scr.color=false -c 's 0x1d474e0' -c 'pd 38' -c 'q' \
  /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer
r2 -2 -q -e scr.color=false -c 's 0x79ce22' -c 'pd 34' -c 'q' \
  /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer
r2 -2 -q -e scr.color=false -c 's 0x1d58fb0' -c 'pd 32' -c 'q' \
  /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer
r2 -2 -q -e scr.color=false -c 's 0x1d476e0' -c 'pd 18' -c 'q' \
  /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer

python3 scripts/build_static_global_promotion_evidence.py \
  --binary /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer \
  --candidate gobjects=0x595b7e0 \
  --candidate-kind gobjects=gobjects \
  --output-dir /tmp/obelisk-static-gobjects-same-array-20260529 \
  --json
```

One attempted full radare2 xref command was killed after it produced no output quickly:

```bash
timeout 180 r2 -2 -A -q -e scr.color=false \
  -c 'axt @ 0x595b7e0' \
  -c 'axt @ 0x595b7f0' \
  -c 'axt @ 0x595b804' \
  -c 'axt @ 0x595b838' \
  -c 'q' \
  /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer
```

## Evidence

All four addresses are inside `.bss` / the RW LOAD segment:

```text
.bss: 0x58446c0..0x5a25b90
RW LOAD: 0x5805000..0x5a25b90
```

The offsets relative to `0x595b7e0` are:

```text
0x595b7e0 = base + 0x00
0x595b7f0 = base + 0x10
0x595b804 = base + 0x24
0x595b838 = base + 0x58
```

Constructor/helper evidence:

```text
0x7a27a7: mov edi,0x595b7e0
0x7a27ac: call 0x1d474e0

0x1d474eb: mov rbx,rdi
0x1d474ee: mov dword [rbx],0
0x1d47502: mov byte [rbx+0xc],1
0x1d47506: lea r15,[rbx+0x10]
0x1d4750d: movups [rbx+0x20],xmm0
0x1d47511: movups [rbx+0x10],xmm0
0x1d4752d: mov dword [rbx+0x58],0x3e8
0x1d47534: mov qword [0x5938bb0],0x595b7f0
```

This is accepted static evidence that `0x595b7f0` and `0x595b838` are fields of the
structure whose base is passed as `0x595b7e0`. The `0x1d475a0` allocation/helper path uses
the same object pointer as `r15` and accesses `[r15+0x10]`, `[r15+0x20]`, `[r15+0x24]`,
`[r15+0x28]`, and `[r15+0x2c]`, which accepts `0x595b804` as the same base's `+0x24`
field.

Lookup/bootstrap evidence:

```text
0x79ce22: stores immediate 0x595b7e0 into global cache slot 0x5958128
0x79ce42: reads dword [0x595b804]
0x79ce4d: reads qword [0x595b7f0]
0x79ce60..0x79ce9d: walks count/chunks, derives chunk index, uses item stride 0x10,
                    and caches the first non-null item
```

Destructor/finalizer evidence:

```text
0x7a27b6: registers 0x595b7e0 as __cxa_atexit callback state
0x1d58fb0: destructor-like helper receives base in rdi/r14 and frees fields
           [r14+0x48], [r14+0x38], [r14+0x18], chunk entries from [r14+0x10],
           and finally [r14+0x10]
```

Reset/finalization evidence:

```text
0x81f118: writes zero to 0x595b7e0 during startup/reset flow
0x81f206: passes 0x595b7e0 to 0x1d476e0
0x1d476e0: writes [rdi+0xc]=0 and updates [rdi] from [rdi+4]+1
```

The generated static evidence pack under `/tmp/obelisk-static-gobjects-same-array-20260529`
reported:

```text
target_code_backed_xref_counts:
  gobjects.root   3
  gobjects.chunks 8016
  gobjects.count  5870
  gobjects.serial 2

manifest.sha256: 0908df6624f010897265fa214067a5a0a3b76aa3a1a45f4775022dc65e7d286d
objdump.sha256:  581d3244a5ef5ff5cb946b3b65d4e5682fa68b4a5a17624766e993b21201b0eb
static-global-xrefs.sha256: cd9e5e95973fc9359ac5c0989c3c862a85626840c92e8019505ca752523ef584
```

A later machine-readable split report under
`/tmp/obelisk-static-gobjects-split-evidence-check/manifest.json` records this as a
`split_near_miss`, not a promotion:

```text
static_contract.split_evidence.status=split_near_miss
root/chunks/count windows=2
chunks/count/serial windows=1
coherent_contract_satisfied=false
does_not_satisfy=missing_gobjects_coherent_field_window
promotion_gate.ready=false
```

## Accepted Manual Evidence

- Accept that `0x595b7e0` is the base of the static `FUObjectArray`/`GUObjectArray`
  candidate for this binary hash as a manual bounded-static interpretation.
- Accept that `0x595b7f0`, `0x595b804`, and `0x595b838` are fields in the same base object
  at offsets `+0x10`, `+0x24`, and `+0x58` for offline research.
- Accept the local static interpretation as a binary-hash-scoped research result only, not
  a machine-promoted runtime-stable public contract.

## Rejected / Blocked

- Reject promotion to a runtime-stable global: the static promotion gate remains
  `ready=false`.
- Reject the helper's strict "coherent field window" as satisfied: the generated manifest
  reports `missing_gobjects_coherent_field_window`; near-miss windows include
  chunks+count+serial without root, or root+chunks+count without serial.
- A separate bounded static audit kept the official gate inconclusive for the same reason:
  no non-oversized executable window contains root, chunks, count, and serial as coherent
  code-backed field references together. Do not cite this note as satisfying that machine
  gate; use it as supporting manual evidence for follow-up tooling or decompiler work.
- Reject full radare2 `-A axt` as useful for this bounded check; direct radare2/objdump
  windows were faster and more reproducible.
- Reject Ghidra headless as necessary for this turn; keep it for decompiler confirmation if
  a later question needs recovered control flow beyond these windows.

## Next Test Needed

Run an independent static or isolated-core reconciliation that ties the constructor-field
evidence to object samples from the same binary/artifact:

1. Use the reviewed artifact-specific FName root.
2. Sample `GObjects=0x595b7e0` at known indices such as `0`, `1`, and `25447`.
3. Require `GObjects[index] -> UObject.InternalIndex -> same index` round trips, plus class
   and outer membership checks.
4. Keep promotion blocked until a second independent static path or isolated runtime/core
   evidence agrees for the same binary hash.
