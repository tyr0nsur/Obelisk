# GNames Evidence Pack Workflow

## Objective

Define the next offline workflow for confirming or rejecting `GNames`/`FNamePool`
candidates without touching `/servidor/ark` or promoting weak offsets into runtime code.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Scope: offline analyzer, copied logs, copied binary artifacts.
- Server state: not touched.
- Runtime probes: not used by this workflow.

## Method

For each isolated capture, keep raw artifacts outside Git and record only the evidence
summary in `docs/research/`.

```bash
sha256sum /path/to/ShooterGameServer
readelf -h -W /path/to/ShooterGameServer > /tmp/ShooterGameServer.readelf-header.txt
readelf -S -W /path/to/ShooterGameServer > /tmp/ShooterGameServer.readelf-sections.txt
readelf -l -W /path/to/ShooterGameServer > /tmp/ShooterGameServer.readelf-programs.txt
objdump -d -M intel /path/to/ShooterGameServer > /tmp/ShooterGameServer.objdump

python3 scripts/analyze_reflectionscanner_capture.py \
  --json \
  --binary /path/to/ShooterGameServer \
  --objdump-xrefs /tmp/ShooterGameServer.objdump \
  /path/to/copied/Obelisk.log
```

The analyzer JSON now includes an `evidence_pack` block with Obelisk commit, copied logs,
binary SHA256, objdump artifact path, candidate count, reject marker count, status, and the
promotion gate.

## Acceptance Criteria

A `GNames`/`FNamePool` table remains a hypothesis unless it has:

- analyzer `gname_table_candidates.status == research-candidate`;
- no reject markers in the evidence pack;
- binary SHA256 and Obelisk commit recorded;
- static xrefs that explain why the source global can lead to the table;
- a second isolated capture or independent static path.

Promotion into runtime code also requires guarded reads, bounds checks, reject logs, and a
rollback path.

## Rejection Criteria

Reject or keep as inconclusive when:

- the table is single-source only;
- clue previews mismatch `None`, `ClientMessage`, or `ServerChat`;
- element/chunk counts are implausible;
- objdump xrefs cannot connect the source global to code/data flow;
- the log includes legacy/native probe reject markers;
- the evidence depends on a live/shared server.

## Next Steps

1. Use this workflow for the next isolated `ReflectionScanner` capture.
2. Add analyzer fixtures when a new false positive appears.
3. Only after a repeatable `FName` resolver exists, continue toward `GObjects`,
   `UFunction`, and parameter decoding.
