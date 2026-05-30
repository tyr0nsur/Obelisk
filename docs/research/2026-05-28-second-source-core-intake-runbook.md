# Second-Source Core Intake Runbook

## Objective

Define the shortest offline path from an approved independent ARK core artifact to
promotion-grade evidence for Obelisk's UE4 reflection substrate. This runbook does not
authorize server restarts, marker changes, `ptrace`, `gcore`, ReflectionScanner, native
exec probes, or live runtime observation.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-28
- Repository baseline when this runbook was authored: `8f16875`
- Current ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Protected live instance: `arkserver` / Ragnarok; do not touch while users are active.
- Debug fallback: `arkserver2` / TheIsland can be used only under a fresh scoped Obelisk
  debug/development approval when needed; preserve evidence, restore stable posture, and
  shut it down afterward when the scoped run requires it.

## Current Evidence State

- Primary UFunction fixtures are comparable but single-source.
- Primary ScriptStruct fixtures are comparable but single-source.
- The primary core is
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
  with SHA256
  `1c4bf8876706b3af40bd9b73fbeb907a31356e62d6c9ff93aed0158d2cb2fe5e`.
  Copying, renaming, repacking, or symlinking this artifact to another directory does not
  create a second source; it remains primary fixture provenance.
- `GUObjectArray` candidate `0x595b7e0` and the current UFunction property-chain layouts
  remain research-candidate evidence until a second isolated core or independent static
  path validates the chain.
- A clean vanilla independent core candidate is available from `arkserver2` / TheIsland:
  `/servidor/ark/obelisk/dumps/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z`.
  Its core SHA256 is
  `56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb`, and its copied
  `ShooterGameServer` SHA256 is
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.
  Pre-capture evidence records no Obelisk env, maps, or process evidence. Because this is
  a vanilla capture, record the offline Obelisk repo commit used for intake separately;
  there was no loaded Obelisk runtime commit in the captured process.

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

For `minimal-second-source-intake`, "independent" means a capture with distinct artifact
identity from the primary core above. A copied primary core, even from a non-`/servidor/ark`
path, must be rejected by identity (`artifact_sha256`, `capture_id`, and
`evidence_pack_id`) and cannot satisfy second-source readiness.

The current clean candidate is useful source provenance, but it is not a valid direct
promotion-tool input under the protected-path policy. Hardlink or copy the matching binary
and core into `/servidor/ark/workspace-offline` or another approved offline workspace,
record fresh staged-artifact hashes, and run the intake against those staged paths:

- capture id: `vanilla-gdb-arkserver2-TheIsland-20260529T012853Z`;
- instance/map: `arkserver2` / TheIsland;
- core:
  `/servidor/ark/obelisk/dumps/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/arkserver2-TheIsland-vanilla-gdb.922783`;
- core SHA256:
  `56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb`;
- copied binary:
  `/servidor/ark/obelisk/dumps/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer`;
- binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`;
- Obelisk posture: pre-capture negative check says no Obelisk env, maps, or process
  evidence.

This records the source as clean and distinct. It does not by itself accept FName,
GObjects, UFunction layout, or public SDK readiness.

The 2026-05-29 local intake on this clean candidate recorded the following triage result:

- FName root slot `0x5956f30` resolves to table `0x5a94660`;
- exact FName clues: `None=0`, `ClientMessage=4884`, `ServerChat=9619`, and
  `SetActiveMissionDebugFlags=9622`;
- `GObjects` candidate `0x595b7e0` samples round-trip by `InternalIndex` for indices
  `0`, `1`, and `25447`;
- sample names/classes resolve as `/Script/CoreUObject` / `Package`, `Object` / `Class`,
  and `ServerChat` / `Function`;
- `minimal-second-source-intake` comparison returned
  `schema=obelisk.reflection-snapshot-readiness.v1`,
  `gate_mode=second_source_promotion`, `promotion_gate.ready=true`, `blockers=[]`, and
  `4/4` accepted UFunction targets across `sdk.inventory` and `sdk.structures`.

That earlier local result was historical triage until regenerated from staged artifacts.
The later direct-root execution under
`/servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z`
is the accepted protected-path-clean report for this target set. It does not accept all
`GObjects` behavior, all modules, runtime callbacks, public mutation APIs, return
overrides, object identity, `ResourceHandle`, or broad SDK readiness. Acceptance of
`minimal-second-source-intake` is limited to the four named sanitized UFunction layouts:
two inventory targets and two structure targets. The inventory half remains internal-only,
and the structure half is not the public `GameplayPolicyEvent` gate; public event
promotion is separately tied to `structure-observer-intake`, copied/redacted POD payloads,
owner-token lifecycle cleanup, ABI tests, and SDK consumer coverage.

## Procedure

Full-intake planning is offline and does not touch any live server. For the current
ARK binary hash, the reviewed FName root slot is already available, so abort broad
FName-table scans and plan the full sequence with direct root validation:

```bash
python3 scripts/run_second_source_core_intake.py \
  --binary <ShooterGameServer> \
  --core <second-source-core> \
  --pack-dir <pack-dir> \
  --snapshot-root <second-source-ufunction-snapshots> \
  --verified-fname-root-slot <verified-slot> \
  --gobjects-candidate 0x595b7e0 \
  --target-set minimal-second-source-intake \
  --json-plan
```

Use `--scan-only` only while deriving and reviewing an artifact-specific FName root for a
new binary hash or when contradictory artifact evidence invalidates the known root. It
rejects full-intake arguments such as `--gobjects-candidate` so the scan phase cannot be
mistaken for GObjects sampling or snapshot comparison.

The JSON output uses schema `obelisk.second-source-core-intake-plan.v1`, names every phase,
stores both argv and shell-rendered commands, and lists the required offline artifact
inputs plus promotion blockers such as missing or partial sanitized artifact identity
(`artifact_kind`, `artifact_sha256`, `capture_id`, and `evidence_pack_id`), reused
primary-core identity, treating dry-run or scan-only plans as accepted evidence, treating
FName table scans as accepted FName evidence or layout promotion, reused FName-root
assumptions, failed core inspection, missing candidate snapshots, or a readiness report
whose `promotion_gate.ready` is not true. It is intentionally incompatible with
`--execute`.

Wrapper inputs are intentionally stricter than the lower-level evidence-pack command:
`--verified-fname-root-slot` and `--gobjects-candidate` take raw non-negative addresses
such as `0x595b7e0`, not `LABEL=ADDR`; `--fname-index` takes either `LABEL=INDEX` or a raw
non-negative index; `--gobjects-sample-index` takes a non-negative integer.

The command is dry-run by default and prints the reproducible command sequence. Remove
`--json-plan` and add `--execute` only after the independent artifact, artifact-specific
FName root, and GObjects candidate have been reviewed. Execution requires existing
binary/core paths and rejects in-repository output paths unless Git already ignores them,
so local evidence packs and regenerated candidate snapshots cannot be staged accidentally.
Planning and execution reject direct or symlink-resolved live-server roots under
`/servidor/ark` for snapshot promotion inputs and outputs except the approved
`/servidor/ark/workspace-offline` workspace. Operators may store large raw captures under
`/servidor/ark/obelisk/dumps` for disk-space reasons, but promotion tooling must consume
hardlinked or copied offline artifacts from the workspace, not direct `dumps` paths.
Full-intake planning validates that `--target-set` exists and contains UFunction snapshot
targets before expensive evidence-pack or snapshot phases start.

The wrapper writes phase evidence under separate subdirectories below `--pack-dir`.
Full intake writes `fname-root-validation/`, `gobjects-sampling/`, and
`snapshot-comparison/`. Scan-only derivation writes `fname-scan/` and remains
candidate-only provenance, not accepted FName evidence.

1. Validate the reviewed per-artifact FName root directly. For the current binary hash,
   use the reviewed `0x5956f30` root slot unless a new hash or contradictory artifact
   evidence invalidates it.

```bash
python3 scripts/scan_core_fname_tables.py \
  --core <second-source-core> \
  --root-slot <verified-slot> \
  --require-exact-root \
  --no-default-indices \
  --json \
  --json-out <pack-dir>/fname-root-validation/core.fname-root-validation.json \
  --index None=0 \
  --index ClientMessage=4884 \
  --index ServerChat=9619 \
  --index SetActiveMissionDebugFlags=9622
```

This phase must pass exact requested indices before GObjects sampling starts.

2. Once the artifact-specific FName root is verified, sample the current GObjects
   candidate through that root.

```bash
python3 scripts/build_core_dump_evidence_pack.py \
  --binary <ShooterGameServer> \
  --core <second-source-core> \
  --output-dir <pack-dir>/gobjects-sampling \
  --no-default-candidates \
  --no-default-fname-roots \
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
  --evidence-pack-manifest <pack-dir>/gobjects-sampling/manifest.json \
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
  --readiness-report \
  --fail-on-readiness-gaps \
  --json
```

When `scripts/run_second_source_core_intake.py --execute` reaches this phase, the
readiness gate is fail-closed and writes the comparison stdout to
`<pack-dir>/snapshot-comparison/readiness-report.json`, with stderr beside it as
`readiness-report.stderr.txt` when present. Missing, inconclusive, rejected, or
base-blocked targets must return non-zero after the report is written. The wrapper then
parses the persisted `readiness-report.json` and requires
`schema=obelisk.reflection-snapshot-readiness.v1`,
`gate_mode=second_source_promotion`, `promotion_gate.ready=true`, no
`promotion_gate.blockers`, the executed `--target-set` in `target_sets`, and
`totals.targets>0`. A comparator exit code of 0 or a minimal `ready=true` JSON fragment is
not acceptable for promotion review.

5. Record results in a dated research note. Include the exact commands, manifest paths,
   `<pack-dir>/snapshot-comparison/readiness-report.json`,
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

Runbook created. A clean vanilla `arkserver2` / TheIsland core candidate is now recorded
as the preferred source artifact to copy into an offline workspace for intake:
`vanilla-gdb-arkserver2-TheIsland-20260529T012853Z`.

The direct-root intake for the four compact inventory/structure UFunction targets now has
an accepted report at
`/servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z/pack/snapshot-comparison/readiness-report.json`:
`gate_mode=second_source_promotion`, `promotion_gate.ready=true`, `blockers=[]`, and
`4/4` accepted targets across `sdk_inventory` and `sdk_structures`. Broader module sets,
public callbacks, mutation APIs, return overrides, object identity, `ResourceHandle`, and
global `GObjects` promotion remain blocked until their own target sets and runtime
policies pass.

## Next Steps

Use the recorded vanilla candidate and verified `0x5956f30` / `0x595b7e0` path as the
baseline for the next target set. Expand to structure-observer, buff, dino, tribe,
mission, or transfer target sets one set at a time, and require each set to produce its
own accepted readiness report before promotion.
