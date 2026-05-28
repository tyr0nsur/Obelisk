# PrimalBuff Snapshot Fixtures

## Objective

Run the first focused `sdk.buffs` offline round and determine whether compact, exact
`PrimalBuff` functions are strong enough for real-core snapshot fixtures.

## Environment

- Manifest:
  `tests/fixtures/ufunction_snapshots/manifest.json`
- Core:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Obelisk baseline used for regenerated snapshot evidence:
  `1c551af Validate snapshot manifest coverage`
- Live-server impact: none.

## Hypothesis

Most buff surfaces are too broad or Blueprint-heavy for runtime planning, but a small set
of exact, compact `PrimalBuff` functions can still improve offline type coverage.

## Method

Generated a focused inventory with:

```text
python3 scripts/summarize_core_ufunction_inventory.py \
  --evidence-pack /servidor/ark/obelisk/dumps/core-pack-gobjects-sample-20260527T041027Z \
  --max-objects 30000 \
  --outer-contains PrimalBuff \
  --max-groups 20 \
  --include-functions \
  --json
```

Then inspected exact candidates and regenerated all manifest snapshots:

```text
python3 scripts/regenerate_ufunction_snapshots.py \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --obelisk-commit 1c551af \
  --write
```

## Evidence

Focused inventory summary:

```text
PrimalBuff* functions: 422
Top outers:
  PrimalBuff: 167
  PrimalBuff_Grappled: 128
  PrimalBuff_Companion: 74
  PrimalBuff_MissionData: 53
Top families:
  BP: 103
  Get: 63
  On: 45
  Is: 21
  Set: 18
  Can: 15
```

New real-core snapshots:

```text
tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_buffs/PrimalBuff.AllowPostProcessEffect.snapshot.json
tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_buffs/PrimalBuff.BuffOverrideInventoryAccessInput.snapshot.json
tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_buffs/PrimalBuff.BPCustomAllowAddBuff.snapshot.json
tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_buffs/PrimalBuff.BP_OnBuffLifetimeUpdated.snapshot.json
tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_buffs/PrimalBuff.BPBuffPreventUploading.snapshot.json
tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_buffs/PrimalBuff.BPPreventAddingOtherBuff.snapshot.json
```

Accepted compact chains:

```text
PrimalBuff.AllowPostProcessEffect
  ReturnValue BoolProperty @0x0 size 1

PrimalBuff.BuffOverrideInventoryAccessInput
  InController ObjectProperty @0x0 size 8
  bInputPressed BoolProperty @0x8 size 1
  ReturnValue BoolProperty @0x9 size 1

PrimalBuff.BPCustomAllowAddBuff
  forCharacter ObjectProperty @0x0 size 8
  DamageCauser ObjectProperty @0x8 size 8
  ReturnValue BoolProperty @0x10 size 1

PrimalBuff.BP_OnBuffLifetimeUpdated
  NumParms 0
  ParmsSize 0
  properties []

PrimalBuff.BPBuffPreventUploading
  ReturnValue BoolProperty @0x0 size 1

PrimalBuff.BPPreventAddingOtherBuff
  anotherBuffClass ClassProperty @0x0 size 8
  ReturnValue BoolProperty @0x8 size 1
```

`--check` passed for the full manifest after adding these entries.

## Result

Confirmed as `candidate-only`. `sdk.buffs` now has a focused real-core snapshot foothold
and an offline internal recognizer in `ue/BuffReflection.*`: inventory-access input,
allow-add-buff policy, class-based prevent-add-buff, bool-return, and zero-param shapes.
This is useful for reflection coverage, but not enough to define a public buff SDK or
runtime observation plan.

## Rejected Paths

- `PrimalCharacter.BuffsPreventInventoryAccess` is a useful adjacent control, but its
  outer is not `PrimalBuff`; defer until a broader character-status module exists.
- `ShooterPlayerController.ServerRequestCreateMissionDataBuff` is a mission/buff bridge,
  but should wait until the mission/buff boundary is better defined.
- Large `PrimalBuff_Grappled`, `PrimalBuff_Companion`, and damage/movement functions are
  deferred because many carry larger structs, vectors, arrays, strings, or gameplay state.
- Blueprint-heavy hooks remain metadata-only until policy and runtime semantics are clear.
- Runtime observation remains blocked without an approved debug/development window.

## Risks

- Buff semantics are highly gameplay-specific; metadata alone is weaker than for inventory
  or structure access.
- Zero-param and bool-return snapshots improve type coverage but do not prove safe event
  dispatch or callback design.

## Next Steps

1. Keep `ue/BuffReflection.*` offline/internal and expand it only with fixture-backed,
   exact reflected metadata.
2. Keep object/class pointer ranges internal for secondary targets such as
   `BuffOverrideInventoryAccessInput`, `BPCustomAllowAddBuff`, and
   `BPPreventAddingOtherBuff`.
3. Do not add runtime buff hooks, public SDK callbacks, return-value override, or gameplay
   mutation until there is an explicit policy and isolated validation plan.
