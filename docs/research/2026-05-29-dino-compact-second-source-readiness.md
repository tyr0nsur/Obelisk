# Dino Compact Second-Source Readiness

## Objective

Record the accepted offline layout-comparison state for `dino-compact-intake` and define
the next safe internal step toward a dino module without promoting a public ABI surface.

This note is documentation only. It does not authorize live-server access, restarts,
marker changes, runtime observers, scanners, ptrace, `gcore`, hook wiring, gameplay
mutation, return overrides, commits, or pushes.

## Environment

- Worktree: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-29
- Input readiness artifact:
  `/servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/dino-compact-readiness.json`
- Candidate snapshot root:
  `/servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/ufunction-snapshots`
- Target set: `dino-compact-intake`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Candidate artifact SHA256:
  `56cf24c61d6822a060fa1bb74ebdb7dc13e3ddf9afc3d5f4843787c046eeeedb`
- Live-server impact: none. Validation used sanitized snapshots and offline workspace
  JSON only.

## Accepted Evidence

`dino-compact-readiness.json` reports:

```text
schema=obelisk.reflection-snapshot-readiness.v1
gate_mode=second_source_promotion
target_sets=dino-compact-intake
promotion_gate.ready=true
targets=2 comparable=2 blocked=0
second_source_accepted=2
second_source_missing=0
second_source_inconclusive=0
second_source_rejected=0
strict_identity_indices=false
```

Accepted targets:

```text
PrimalDinoCharacter.AddPassenger
  NumParms=6 ParmsSize=16 ReturnValueOffset=0xf
  ACharacter ObjectProperty @0x0 size 8
  PassengerSeatIndex IntProperty @0x8 size 4
  bForcePassenger BoolProperty @0xc size 1
  bAllowFlyersAndWaterDinos BoolProperty @0xd size 1
  bSkipLineTrace BoolProperty @0xe size 1
  ReturnValue BoolProperty @0xf size 1

PrimalDinoCharacter.AllowCarryCharacter
  NumParms=2 ParmsSize=9 ReturnValueOffset=0x8
  CanCarryPawn ObjectProperty @0x0 size 8
  ReturnValue BoolProperty @0x8 size 1
```

The current `scripts/reflection_target_sets.py` definition already matches the accepted
compact set exactly:

```text
obelisk.ufunction-chain.snapshot.v1:PrimalDinoCharacter.AddPassenger
obelisk.ufunction-chain.snapshot.v1:PrimalDinoCharacter.AllowCarryCharacter
```

No target-set expansion is justified by this artifact. Transfer dino targets,
blueprint-side carry hooks, tame-state functions, attack functions, controller stat
requests, arrays, strings, structs, and admin/NetExec surfaces remain outside this
compact promotion gate.

## Boundary Decision

This evidence accepts `dino-compact-intake` as offline layout evidence only. It does not
complete `minimal-second-source-intake`, promote a runtime observer, or promote:

- a public Dino SDK or C ABI addition;
- a plugin callback, capability bit, public event kind, or public resource kind;
- object identity, dino identity, rider/passenger identity, resource handles, lookup APIs,
  `InternalIndex`, FName indices, GObjects indices, raw pointers, or `FUObjectItem` fields;
- runtime hook wiring, broad tracing, return override, mutation, or UE function calls;
- logging of raw params, object pointers, actor names, player identity, or persistent
  identity-like values.

The only plausible copied internal fields from this compact pair are:

```text
PassengerSeatIndex
bForcePassenger
bAllowFlyersAndWaterDinos
bSkipLineTrace
ReturnValue
```

`ACharacter` and `CanCarryPawn` are useful for exact metadata recognition but must stay
redacted from any copied event payload until a separate identity and lifetime policy
exists.

## Next Safe Internal Step

The next safe implementation step is an internal, fixture-backed dino recognizer/copy
plan with no public ABI and no hook integration:

1. Add `ue/DinoReflection` only if it exactly recognizes the two accepted metadata shapes
   by function name, outer name, `NumParms`, `ParmsSize`, return offset, property names,
   property classes, property offsets, and candidate UObject membership.
2. Add unit tests from synthetic fixtures for accepted and rejected shapes, including
   partial-name collisions such as `BPNotifyAddPassenger` and `BPAllowCarryCharacter`.
3. If a copied internal event builder is added later, copy only the scalar fields listed
   above into Obelisk-owned memory and keep object fields as recognition-only.
4. Do not wire `ProcessEvent` observation until the recognizer has negative tests, cheap
   exact prefilters, supported-SHA gating, observer-profile gating, instance markers,
   explicit non-zero budgets, no mutation, no return override, and rollback docs.

The follow-on runtime-observation step, when separately approved, should use a dedicated
debug instance or the approved `arkserver2` development posture only. It should not touch
`arkserver` / Ragnarok and should produce bounded metadata-only logs for the exact compact
targets.

## Validation

Offline readiness was rechecked with:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root /servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/ufunction-snapshots \
  --target-set dino-compact-intake \
  --readiness-report \
  --fail-on-readiness-gaps \
  --json
```

Result:

```text
promotion_gate.ready=true
targets=2 comparable=2
second_source_accepted=2
second_source_missing=0
second_source_inconclusive=0
second_source_rejected=0
```

Target-set audit was rechecked with:

```bash
python3 scripts/compare_reflection_snapshots.py --list-target-sets
```

Result: `dino-compact-intake` lists only `PrimalDinoCharacter.AddPassenger` and
`PrimalDinoCharacter.AllowCarryCharacter`.

## Public API Decision

No public API work is justified now. The ABI boundary still lacks runtime observation,
copied-data dispatcher tests, owner-token lifecycle cleanup for a dino event family,
public payload/redaction policy, ABI layout tests, installed SDK consumer tests,
capability documentation, and explicit operator-facing capability guidance.

The accepted offline layout artifact is valuable internal module evidence. It is not a
plugin boundary contract, and it does not change the separate
`minimal-second-source-intake` status.
