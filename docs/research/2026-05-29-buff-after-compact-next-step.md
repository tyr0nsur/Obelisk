# Buff After Compact Next Step

## Objective

Decide whether `buff-compact-intake` should lead to recognizer tests, docs, target-set
expansion, runtime hooks, or an explicit no-go.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-29
- Live-server impact: none. No runtime server, restarts, marker changes, ptrace, `gcore`,
  scanner runs, commits, pushes, public ABI edits, or external status updates.
- Accepted offline result:
  `/servidor/ark/workspace-offline/buff-compact-intake-20260529T034751Z/pack/snapshot-comparison/readiness-report.json`

## Evidence

`buff-compact-intake` is accepted as second-source UFunction layout evidence:

```text
gate_mode=second_source_promotion
promotion_gate.ready=true
blockers=[]
targets=3
second_source_accepted=3
```

Accepted targets:

```text
PrimalBuff.AllowPostProcessEffect
PrimalBuff.BPBuffPreventUploading
PrimalBuff.BP_OnBuffLifetimeUpdated
```

`ue/BuffReflection.*` and `tests/core/BuffReflectionTests.cpp` already cover the compact
targets plus three broader fixture-backed buff shapes. The recognizer validates exact
function name, outer, `NumParms`, `ParmsSize`, return offset, property names/classes,
offsets, sizes, array dimensions, supported SHA, and enabled-layout gates. Object and
class pointer ranges remain hidden.

## Recommendation

Do not start buff runtime hooks yet. The useful safe next step is documentation cleanup and,
only if more buff breadth is explicitly desired, a new offline-only target set for the
three existing non-compact fixture-backed shapes:

```text
PrimalBuff.BuffOverrideInventoryAccessInput
PrimalBuff.BPCustomAllowAddBuff
PrimalBuff.BPPreventAddingOtherBuff
```

Treat that expansion as layout breadth only. It must not expose controller, character,
damage-causer, or class pointers, and it must not add callbacks, return overrides,
mutation, public Buff SDK, resource identity, or runtime observation.

## No-Go Boundary

Buff runtime hooks remain a no-go until copied payload policy, exact runtime gates,
approved debug posture, lifecycle tests, ABI tests, public redaction docs, and
non-mutating/no-return-override policy exist. The current accepted compact intake improves
offline confidence only.
