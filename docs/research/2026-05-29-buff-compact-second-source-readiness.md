# Buff Compact Second-Source Readiness

Superseded by `2026-05-29-buff-compact-second-source-result.md`, which records the
accepted `034751Z` run. Keep this note as historical preparation only; do not rerun the
`034526Z` plan as an active next task.

## Objective

Check whether `buff-compact-intake` can be the next fast second-source breadth run using
the already staged offline core plus reviewed FName/GObjects context, without runtime work
or broad/heavy discovery.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-29
- Evidence only: scripts, target sets, committed sanitized fixtures, and staged offline
  workspace manifests.
- Live-server impact: none. No restart, marker change, ptrace, `gcore`, scanner, or
  runtime observer was executed.
- Candidate offline binary:
  `/servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer`
- Candidate offline core:
  `/servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core`
- Binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Candidate core SHA256:
  `56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb`
- Reviewed context from existing packs: FName root slot `0x5956f30`, GObjects candidate
  `0x595b7e0`.

## Evidence

`scripts/reflection_target_sets.py` defines `buff-compact-intake` as exactly three
UFunction targets:

```text
PrimalBuff.AllowPostProcessEffect
PrimalBuff.BPBuffPreventUploading
PrimalBuff.BP_OnBuffLifetimeUpdated
```

Committed base fixtures are present and comparable:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target-set buff-compact-intake \
  --json
```

Result summary:

```text
gate_mode=informational_gap_report
targets=3
comparable=3
promotion_gate.ready=false
blockers=missing_second_source:3
```

Existing accepted/offline candidate roots do not contain `sdk_buffs` snapshots. Comparing
against both current roots yields `missing_candidate_snapshot` for all three targets:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root /servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z/ufunction-snapshots \
  --readiness-report \
  --target-set buff-compact-intake \
  --json

python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root /servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/ufunction-snapshots \
  --readiness-report \
  --target-set buff-compact-intake \
  --json
```

Both reports are non-promotable:

```text
targets=3
comparable=3
second_source_inconclusive=3
promotion_gate.ready=false
blockers=inconclusive_second_source:3
reason=missing_candidate_snapshot
```

## Result

Status: `ready-to-run`.

`buff-compact-intake` is a good next quick offline breadth run. It is not already complete,
but the target set is narrow, base fixtures are clean, and the same validated offline core
context used by prior accepted compact runs is sufficient to regenerate only the three buff
snapshots and compare them. This should remain metadata/layout evidence only.

## Exact Command

Fast path using the existing validated `gobjects-sampling` manifest:

```bash
mkdir -p /servidor/ark/workspace-offline/buff-compact-intake-20260529T034526Z/pack/snapshot-comparison

python3 scripts/regenerate_ufunction_snapshots.py \
  --core /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core \
  --evidence-pack-manifest /servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z/pack/gobjects-sampling/manifest.json \
  --output-root /servidor/ark/workspace-offline/buff-compact-intake-20260529T034526Z/ufunction-snapshots \
  --target-set buff-compact-intake \
  --write

python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root /servidor/ark/workspace-offline/buff-compact-intake-20260529T034526Z/ufunction-snapshots \
  --target-set buff-compact-intake \
  --readiness-report \
  --fail-on-readiness-gaps \
  --json \
  > /servidor/ark/workspace-offline/buff-compact-intake-20260529T034526Z/pack/snapshot-comparison/readiness-report.json
```

If review requires a fresh evidence-pack wrapper instead of reusing the existing manifest,
use this slower full-intake command:

```bash
python3 scripts/run_second_source_core_intake.py \
  --binary /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer \
  --core /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core \
  --pack-dir /servidor/ark/workspace-offline/buff-compact-intake-20260529T034526Z/pack \
  --snapshot-root /servidor/ark/workspace-offline/buff-compact-intake-20260529T034526Z/ufunction-snapshots \
  --verified-fname-root-slot 0x5956f30 \
  --gobjects-candidate 0x595b7e0 \
  --target-set buff-compact-intake \
  --base-root tests/fixtures/ufunction_snapshots \
  --execute
```

Expected success shape:

```text
gate_mode=second_source_promotion
target_sets=["buff-compact-intake"]
promotion_gate.ready=true
promotion_gate.blockers=[]
totals.targets=3
totals.second_source_accepted=3
```

In that expected shape, `promotion_gate.ready=true` means only that the offline
second-source layout comparison would be ready for the named target set. It would not make
the named UE functions usable plugin APIs and would not authorize public SDK, runtime
hook, callback, mutation, return override, identity, or raw pointer exposure.

## Risks And Boundaries

- Do not treat existing minimal or dino snapshot roots as buff second-source evidence; they
  lack the three buff snapshots.
- Do not run a new runtime capture, scanner, ptrace, or `gcore` for this task.
- This does not promote buff hooks, public callbacks, object/class exposure, return
  overrides, gameplay mutation, raw params, or a public Buff SDK.
- If the command returns missing, inconclusive, rejected, or base-blocked targets, keep the
  result blocked and inspect only the persisted readiness report plus regenerated
  sanitized snapshots.
