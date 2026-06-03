# Core-Based GObjects Next Development

## Objective

Use the confirmed core-dump FName root as the base for the next offline
`GUObjectArray`/`GObjects` reconstruction step. This note does not promote a `GObjects`
offset and does not require running ARK, attaching GDB to a live process, or enabling
ReflectionScanner.

## Current Input

- Binary SHA256 from core evidence:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Strong FName/GNames research candidate for that binary:
  `0x5956f30 -> table`
- Confirmed core clue indices:
  - `0 -> None`
  - `4884 -> ClientMessage`
  - `9619 -> ServerChat`

## Proposed Development

The next concrete step is an offline candidate loop:

1. Use static analysis to collect likely `GUObjectArray` global slots from code paths that
   iterate global objects, construct/register `UObject`, or perform object-name lookups.
   Accept only addresses with real load/store xrefs, not string proximity.
2. Run the core evidence pack with the FName root plus each `GObjects` candidate:

   ```bash
   python3 scripts/build_core_dump_evidence_pack.py \
     --binary /path/to/ShooterGameServer \
     --core /path/to/core \
     --output-dir /tmp/obelisk-core-gobjects-pack \
     --gobjects-candidate gobjects_slot=0xADDR
   ```

3. In `gdb-core.txt`, reject candidates whose root is unmapped, unaligned, null after
   expected startup, or whose nearby count-like fields are implausible.
4. For survivors, sample object pointers from bounded array-like windows and check each
   candidate `UObject` shape against:
   - executable vtable mapping,
   - readable or null class/outer pointers,
   - plausible flags/internal index fields,
   - `NamePrivate.ComparisonIndex` resolving through `0x5956f30`.
5. Only after a candidate object array can map multiple `InternalIndex` values back to the
   same sampled objects should it become a `GObjects` research candidate.

## Script Improvement

`scripts/build_core_dump_evidence_pack.py` now emits bounded GDB commands for:

- direct FName entry reads from `--fname-root-slot` using `--fname-index` values;
- default FName clues for `0`, `4884`, and `9619`;
- bounded `--gobjects-candidate LABEL=ADDR` global-slot and pointer-window previews.
- bounded `--gobjects-sample-index INDEX` reads `FUObjectItem` samples from each
  `--gobjects-candidate` interpreted as a direct `GUObjectArray` struct. This is intended
  for candidates such as `0x595b7e0`; when sampling is enabled, the older indirect
  slot-preview block is skipped.
- bounded `--scan-pointer-value LABEL=ADDR` searches across small readable/writable core
  mappings to find slots that point to a confirmed in-memory table/root value.
- optional `--scan-fname-tables` runs `scripts/scan_core_fname_tables.py`, an offline
  legacy FName-table shape scanner that starts from `None`, reconstructs
  entry -> chunk -> table pointer chains, and validates known FName indices.
- when `--gobjects-candidate` is supplied, the pack now writes
  `gobjects-static-xrefs.json` from the generated objdump. It summarizes xrefs for the
  candidate root, direct chunks field `+0x10`, count field `+0x24`, and serial-like field
  `+0x58`, with access classification and objdump function-group anchors.

These commands are evidence generation only. They deliberately do not perform a broad core
scan by default or infer a final UE4 layout.

Example for the already captured FName table value:

```bash
python3 scripts/build_core_dump_evidence_pack.py \
  --binary /path/to/ShooterGameServer \
  --core /path/to/core \
  --output-dir /tmp/obelisk-core-pointer-scan \
  --scan-pointer-value fname_table=0x2ae5c660 \
  --scan-fname-tables \
  --skip-core-sha256
```

The resulting `gdb-core.txt` prints rows like:

```text
hit fname_table value=0x2ae5c660 slot=0x... mapping=0x...-0x... <mapping>
```

Treat each hit as a candidate slot only. Promote it only after static xrefs and a second
capture or independent validation path.

The FName table scanner writes `core.fname-table-scan.json` when enabled. A candidate from
that file is still a research candidate, not a stable runtime offset, because it is derived
from one core image. On large cores this scanner can be slow; run it deliberately, prefer
bounded limits or `timeout`, and do not enable it in unattended workflows.

Local offline validation on 2026-05-27 wrote a temporary pack under
`/tmp/obelisk-gobjects-xrefs-20260527-190349` for `gobjects=0x595b7e0`. Its
`gobjects-static-xrefs.json` reported:

```text
access_counts={'load': 13884, 'store': 7}
gobjects.root 0x595b7e0: 3 xrefs
gobjects.chunks 0x595b7f0: 8016 xrefs
gobjects.count 0x595b804: 5870 xrefs
gobjects.serial 0x595b838: 2 xrefs
```

The `/tmp` pack is a disposable validation artifact; the durable result is the script
support and these summarized counts.

Manual context review from the same pack identified useful anchors for follow-up:

- `0x79ce22`: stores immediate `0x595b7e0` into a nearby global slot, then reads
  `0x595b804` and `0x595b7f0` in a bounded walk.
- `0x7a27a7`: passes `0x595b7e0` to a helper and registers a destructor-like callback
  through `__cxa_atexit`.
- `0x81f118`: clears `0x595b7e0` during startup/reset flow.
- `0x81f206`: passes `0x595b7e0` to another startup helper.

Treat these as static context anchors for decompiler/rizin follow-up. They are not
accepted function names, because this stripped binary's objdump labels often point to
nearest exported symbols rather than real internal functions.

After adding function grouping to `gobjects-static-xrefs.json`, parsing the same objdump
reported the highest-volume groups:

```text
0x886d80  xrefs=6298 targets=gobjects.chunks,gobjects.count
0xeaa3a0  xrefs=4013 targets=gobjects.chunks,gobjects.count
0x12d1400 xrefs=3488 targets=gobjects.root,gobjects.chunks,gobjects.count,gobjects.serial
0x81dc59  xrefs=90   targets=gobjects.root,gobjects.chunks,gobjects.count
0x648400  xrefs=2    targets=gobjects.chunks,gobjects.count
```

Follow-up classification in `2026-05-27-gobjects-static-anchor-classification.md` found
that the `0x12d1400` group is too broad to treat as one decompiler target: sample xrefs
are dispersed under a nearest exported symbol. Prefer concrete instruction windows such as
`0x79ce22`, `0x7a27a7`, `0x81f118`, and `0x81f206` when reasoning about init/reset/lookup
behavior. The `0x81dc59` group remains useful only as a broad startup/reset neighborhood.

## Acceptance Gate

A `GObjects` candidate remains inconclusive until all of these are available:

- matching binary hash and core pack manifest;
- static xrefs explaining the global slot;
- bounded core evidence showing plausible root/count/chunk or array shape;
- multiple object samples with names resolved through the validated FName table;
- a second isolated capture or independent static path before runtime code when the route
  is reopened for a new binary hash or contradictory artifact evidence.

## Current No-Repeat Checkpoint

The original slot-finding step is superseded by `0x595b7e0`, now documented in
`2026-05-27-core-gobjects-candidate.md` as a binary-hash-specific
`GUObjectArray research-candidate`. The evidence pack direct-sample mode is the correct
path for this candidate; the older legacy `--gobjects-candidate` preview treats `ADDR` as
an indirect slot and is only useful for unresolved slot-style candidates.

After `0x595b7e0`, the next offline step is not another broad candidate search. The
current binary already has reviewed no-scan FName/GObjects inputs and later second-core
reconciliation. Do not repeat classified static/context checks, core capture, or
GObjects/FName discovery for this hash unless a new binary hash or contradictory artifact
evidence invalidates the route.
