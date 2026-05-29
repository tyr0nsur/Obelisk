# Buff Compact Second-Source Result

## Objective

Record the executed offline second-source comparison for the compact buff UFunction target
set.

## Artifact

- Worktree: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-29
- Offline workspace:
  `/servidor/ark/workspace-offline/buff-compact-intake-20260529T034751Z`
- Candidate snapshots:
  `ufunction-snapshots/7e7ded49e0c6/sdk_buffs/`
- Readiness report:
  `pack/snapshot-comparison/readiness-report.json`
- Evidence-pack manifest reused:
  `/servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z/pack/gobjects-sampling/manifest.json`

## Commands

```bash
python3 scripts/regenerate_ufunction_snapshots.py \
  --core /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core \
  --evidence-pack-manifest /servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z/pack/gobjects-sampling/manifest.json \
  --output-root /servidor/ark/workspace-offline/buff-compact-intake-20260529T034751Z/ufunction-snapshots \
  --target-set buff-compact-intake \
  --write

python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root /servidor/ark/workspace-offline/buff-compact-intake-20260529T034751Z/ufunction-snapshots \
  --target-set buff-compact-intake \
  --readiness-report \
  --fail-on-readiness-gaps \
  --json > /servidor/ark/workspace-offline/buff-compact-intake-20260529T034751Z/pack/snapshot-comparison/readiness-report.json
```

## Result

```text
schema=obelisk.reflection-snapshot-readiness.v1
gate_mode=second_source_promotion
promotion_gate.ready=true
promotion_gate.blockers=[]
targets=3
comparable=3
second_source_accepted=3
second_source_missing=0
second_source_inconclusive=0
second_source_rejected=0
```

Accepted targets:

```text
PrimalBuff.AllowPostProcessEffect
PrimalBuff.BPBuffPreventUploading
PrimalBuff.BP_OnBuffLifetimeUpdated
```

## Boundary

This promotes compact buff UFunction layout evidence only. It does not promote a public
Buff SDK, hooks, callbacks, object/class exposure, mutation, return overrides, raw params,
or resource identity. Buff runtime work still needs copied payload policy, exact runtime
gates, ABI/lifecycle tests, and public redaction docs before any plugin-facing surface.
