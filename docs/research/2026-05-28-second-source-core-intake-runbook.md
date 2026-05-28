# Second-Source Core Intake Runbook

## Objective

Define the shortest offline path from an approved independent ARK core artifact to
promotion-grade evidence for Obelisk's UE4 reflection substrate. This runbook does not
authorize server restarts, marker changes, `ptrace`, `gcore`, ReflectionScanner, native
exec probes, or live runtime observation.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-28
- Current baseline commit when written: `8f16875`
- Current ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Protected live instance: `arkserver` / Ragnarok; do not touch while users are active.
- Debug fallback: `arkserver2` / TheIsland is powered off; start only with explicit
  operator approval and shut it down after the scoped test.

## Current Evidence State

- Primary UFunction fixtures are comparable but single-source.
- Primary ScriptStruct fixtures are comparable but single-source.
- `GUObjectArray` candidate `0x595b7e0` and the current UFunction property-chain layouts
  remain research-candidate evidence until a second isolated core or independent static
  path validates the chain.

## Minimal Intake

Validate only these four UFunction targets first:

- `PrimalItem.CanUse`
- `PrimalItem.AllowRemoteAddToInventory`
- `PrimalStructure.AllowStructureAccess`
- `PrimalStructure.IsAllowedToDemolish`

They are compact inventory/structure policy shapes with existing primary fixtures and no
public SDK mutation contract.

## Required Artifact

Use an already-captured independent core artifact plus its matching `ShooterGameServer`
binary. The artifact must record:

- instance id and map;
- ARK binary path and SHA256;
- Obelisk commit used at capture time;
- core path and SHA256;
- active Obelisk env and marker posture;
- explicit statement that Ragnarok was not touched, or the exact approved maintenance
  window if it was.

## Procedure

The full offline sequence can be planned without touching any live server:

```bash
python3 scripts/run_second_source_core_intake.py \
  --binary <ShooterGameServer> \
  --core <second-source-core> \
  --pack-dir <pack-dir> \
  --snapshot-root <second-source-ufunction-snapshots> \
  --verified-fname-root-slot <verified-slot> \
  --gobjects-candidate 0x595b7e0
```

The command is dry-run by default and prints the reproducible command sequence. Add
`--execute` only after the independent artifact, artifact-specific FName root, and
GObjects candidate have been reviewed.

1. Build a core evidence pack from the existing artifact. Derive or scan the per-artifact
   FName root first; do not reuse the primary-core-only FName slot by default.

```bash
python3 scripts/build_core_dump_evidence_pack.py \
  --binary <ShooterGameServer> \
  --core <second-source-core> \
  --output-dir <pack-dir> \
  --scan-fname-tables \
  --no-default-fname-indices \
  --fname-index None=0 \
  --fname-index ClientMessage=4884 \
  --fname-index ServerChat=9619 \
  --fname-index SetActiveMissionDebugFlags=9622
```

2. Once the artifact-specific FName root is verified, sample the current GObjects
   candidate through that root.

```bash
python3 scripts/build_core_dump_evidence_pack.py \
  --binary <ShooterGameServer> \
  --core <second-source-core> \
  --output-dir <pack-dir> \
  --fname-root-slot verified_fname_root_slot=<verified-slot> \
  --gobjects-candidate gobjects=0x595b7e0 \
  --gobjects-sample-index 0 \
  --gobjects-sample-index 1 \
  --gobjects-sample-index 25447
```

3. Regenerate only the minimal UFunction intake from the evidence pack manifest.

```bash
python3 scripts/regenerate_ufunction_snapshots.py \
  --core <second-source-core> \
  --evidence-pack-manifest <pack-dir>/manifest.json \
  --output-root <second-source-ufunction-snapshots> \
  --target-set minimal-second-source-intake \
  --write
```

4. Compare the candidate snapshots against committed primary fixtures.

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root <second-source-ufunction-snapshots> \
  --target-set minimal-second-source-intake \
  --json
```

5. Record results in a dated research note. Include the exact commands, manifest paths,
   accepted/rejected/inconclusive targets, and any static xref artifacts used.

## Acceptance Criteria

Promotion remains blocked unless all four minimal targets are `accepted` and both roots
include distinct sanitized artifact identity:

- `artifact_kind`;
- `artifact_sha256`;
- `capture_id`;
- `evidence_pack_id`.

Missing identity, matching identity, shared artifact SHA, shared capture id, shared
evidence pack id, GDB/core inspection failure, reused primary FName-root assumptions, or
layout mismatch is `inconclusive` or `rejected`, not accepted.

## Result

Runbook created. No second-source artifact was present in-repo during this note, so no
promotion status changed.

## Next Steps

Wait for an explicitly approved independent artifact, then execute the minimal intake
before expanding to structure-observer, buff, dino, tribe, mission, or transfer target
sets.
