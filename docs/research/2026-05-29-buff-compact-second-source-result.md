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

This records accepted compact buff UFunction layout evidence only.
`promotion_gate.ready=true` in this note means the offline layout comparison passed for
the named target set; it is not runtime readiness and it does not make the named UE
functions usable plugin APIs. It does not promote a public Buff SDK, hooks, callbacks,
object/class exposure, mutation, return overrides, raw params, or resource identity.
Buff runtime work still needs copied payload policy, exact runtime gates, ABI/lifecycle
tests, and public redaction docs before any plugin-facing surface.

## Breadth Follow-Up

On 2026-05-30, `buff-breadth-intake` was regenerated from the existing offline
second-source core without server/runtime activity:

```text
/servidor/ark/workspace-offline/buff-breadth-intake-second-source-20260530T091014Z
```

Source identity:

```text
core=/servidor/ark/workspace-offline/second-source-arkserver2-TheIsland-20260529T011227Z/raw/core
core_sha256=62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78
binary_sha256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
gobjects=0x595b7e0
fname_root_slot=0x5956f30
```

Result:

```text
schema=obelisk.reflection-snapshot-readiness.v1
gate_mode=second_source_promotion
target_sets=buff-breadth-intake
promotion_gate.ready=true
promotion_gate.ready_scope=layout_only
promotion_gate.promotion_ready=false
totals.targets=3
totals.comparable=3
totals.second_source_accepted=3
```

Accepted breadth targets:

```text
PrimalBuff.BuffOverrideInventoryAccessInput
PrimalBuff.BPCustomAllowAddBuff
PrimalBuff.BPPreventAddingOtherBuff
```

Consume gate accepted the readiness report. This is still internal layout evidence only:
no public Buff SDK, runtime hooks, callbacks, object/class exposure, mutation, return
override, raw params, `ResourceHandle`, or gameplay semantics are promoted.
