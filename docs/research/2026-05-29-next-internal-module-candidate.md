# Next Internal Module Candidate

## Objective

Choose the next fastest internal module candidate toward plugin usefulness after the
accepted `dino-compact-intake` layout evidence, without implementing broad runtime work.

This note is docs-only. It does not authorize live-server reads, restarts, marker changes,
runtime probes, scanners, ptrace, `gcore`, hook expansion, public ABI edits, commits, or
pushes.

## Environment

- Worktree: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-29
- Inputs inspected:
  - `scripts/reflection_target_sets.py`
  - `tests/fixtures/ufunction_snapshots/manifest.json`
  - committed UFunction fixture JSON under `tests/fixtures/ufunction_snapshots/7e7ded49e0c6`
  - offline dino readiness report:
    `/servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/dino-compact-readiness.json`
  - existing module notes for inventory gates, buff fixtures, dino readiness, and module
    surface ranking
- Live-server impact: none. All checks were fixture/readiness reads and offline comparison
  commands.

## Current Target-Set Evidence

`dino-compact-intake` is validated as accepted second-source layout evidence:

```text
gate_mode=second_source_promotion
promotion_gate.ready=true
targets=2 comparable=2
second_source_accepted=2
second_source_missing=0
second_source_inconclusive=0
second_source_rejected=0
```

Accepted compact dino shapes:

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

`minimal-second-source-intake` is the compact inventory/structure layout evidence now
accepted by the direct-root second-source report:

```text
PrimalItem.CanUse
PrimalItem.AllowRemoteAddToInventory
PrimalStructure.AllowStructureAccess
PrimalStructure.IsAllowedToDemolish
```

Accepted readiness:

```text
targets=4 comparable=4 blocked=0
gate_mode=second_source_promotion
promotion_gate.ready=true
blockers=[]
sdk_inventory second_source=accepted:2
sdk_structures second_source=accepted:2
```

Inventory fixture shapes are compact and directly useful as copied internal scalar events:

```text
PrimalItem.CanUse
  NumParms=2 ParmsSize=2 ReturnValueOffset=0x1
  bIgnoreCooldown BoolProperty @0x0 size 1
  ReturnValue BoolProperty @0x1 size 1

PrimalItem.AllowRemoteAddToInventory
  NumParms=4 ParmsSize=18 ReturnValueOffset=0x11
  invComp ObjectProperty @0x0 size 8
  ByPC ObjectProperty @0x8 size 8
  bRequestedByPlayer BoolProperty @0x10 size 1
  ReturnValue BoolProperty @0x11 size 1
```

`buff-compact-intake` now has accepted second-source layout evidence:

```text
targets=3 comparable=3 blocked=0
gate_mode=second_source_promotion
promotion_gate.ready=true
blockers=[]
second_source_accepted=3
```

Buff compact shapes are cheap and clean for metadata breadth, but less plugin-useful:

```text
PrimalBuff.AllowPostProcessEffect
  NumParms=1 ParmsSize=1 ReturnValueOffset=0x0
  ReturnValue BoolProperty @0x0 size 1

PrimalBuff.BPBuffPreventUploading
  NumParms=1 ParmsSize=1 ReturnValueOffset=0x0
  ReturnValue BoolProperty @0x0 size 1

PrimalBuff.BP_OnBuffLifetimeUpdated
  NumParms=0 ParmsSize=0 ReturnValueOffset=0xffff
```

## Recommendation

Pick `sdk.inventory` observer hardening as the next fastest internal module candidate
toward plugin usefulness.

Use the accepted `minimal-second-source-intake` layout evidence to harden the internal
inventory observer only within the existing narrow scope:

```text
/servidor/ark/workspace-offline/minimal-second-source-intake-direct-20260529T033919Z/pack/snapshot-comparison/readiness-report.json
```

- exact FName/name/outer/`NumParms`/`ParmsSize`/return-offset/property-chain recognition for
  `PrimalItem.CanUse` and `PrimalItem.AllowRemoteAddToInventory`;
- cheap exact name prefilter before budget reservation;
- supported-SHA, observer-profile, debug-window, instance-marker, and non-zero-budget
  gates;
- copied internal scalar payloads only:
  `bIgnoreCooldown`, `bRequestedByPlayer`, and `ReturnValue`;
- dispatch only after the original `ProcessEvent` path ran;
- no public Inventory SDK, no capability bit, no return override, no mutation, no raw
  object/item/player identity, no inventory contents, and no arrays or structs.

## Why Not Buff Compact First

`buff-compact-intake` is accepted as offline layout evidence, but it is not the fastest path
to plugin usefulness:

- current compact targets are mostly bool-return or zero-param metadata shapes;
- buff semantics are gameplay-specific and authority-sensitive;
- object/class exposure, callbacks, return overrides, mutation, and runtime hooks remain
  blocked by policy and evidence gaps.

Buff work is a good follow-up only if the next round is explicitly offline recognizer
breadth or copied-payload policy, not plugin-facing runtime utility.

## Why Not Dinos Next

The dino compact pair is already validated for internal layout evidence, but it should not
be the next plugin-usefulness candidate. The useful dino context is tied to actor identity,
passenger/carry object lifetime, resource handles, and mutation/override semantics. Those
remain blocked. Keep `ue/DinoReflection` fixture-backed and internal-only.

## Blockers

- The accepted minimal report promotes only compact `UFunction` layout evidence for two
  inventory targets and two structure targets. It does not promote `GObjects`,
  `ResourceHandle`, object identity, mutation, return override, runtime observers, or
  public Inventory/StructureEvents SDK surfaces.
- Inventory cannot become public SDK work without copied-data lifecycle policy, owner-token
  cleanup tests, ABI layout tests, installed SDK consumer tests, public capability docs,
  and explicit redaction statements.
- Any runtime observation still needs approved debug posture, exact gates, bounded budgets,
  no value logging of sensitive fields, stable-posture rollback, and no contact with the
  protected `arkserver` / Ragnarok instance.
- Buff compact remains policy-blocked for runtime hooks and plugin callbacks even though
  the three compact layouts are accepted as second-source offline evidence.
- Dinos remain blocked on object identity, actor lifetime, resource-handle semantics,
  runtime observation, mutation policy, and public ABI design.

## Commands Used

```bash
python3 scripts/compare_reflection_snapshots.py --list-target-sets

python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target-set minimal-second-source-intake

python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target-set buff-compact-intake

python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root /servidor/ark/workspace-offline/fuobjectitem-dino-reconcile-20260529T120000Z/ufunction-snapshots \
  --readiness-report \
  --fail-on-readiness-gaps \
  --target-set dino-compact-intake \
  --json
```
