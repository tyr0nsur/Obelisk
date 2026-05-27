# Inventory Controller Snapshot Fixtures

## Objective

Promote the safest compact `sdk.inventory` item/controller candidates from synthetic
fixture coverage to real-core sanitized snapshots.

## Environment

- Manifest:
  `tests/fixtures/ufunction_snapshots/manifest.json`
- Core:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Obelisk baseline used for regenerated snapshot evidence:
  `9e685c2 Add UFunction snapshot regeneration manifest`
- Live-server impact: none.

## Hypothesis

`PrimalItem` use gates and the controller-side inventory request are the next safest
offline-only capability slice because they are compact, already covered by synthetic
fixtures, and connect item policy to player/controller requests without runtime probing.

## Method

Added manifest entries and regenerated all snapshot fixtures through:

```text
python3 scripts/regenerate_ufunction_snapshots.py \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --obelisk-commit 9e685c2 \
  --write
```

Then verified drift:

```text
python3 scripts/regenerate_ufunction_snapshots.py \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --obelisk-commit 9e685c2 \
  --check
```

## Evidence

New real-core snapshots:

```text
tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_inventory/PrimalItem.AllowRemoteAddToInventory.snapshot.json
tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_inventory/PrimalItem.CanUse.snapshot.json
tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_inventory/ShooterPlayerController.ServerRequestInventoryUseItem.snapshot.json
tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_inventory/ShooterPlayerController.ServerRequestInventoryUseItemWithActor.snapshot.json
```

Accepted chains:

```text
PrimalItem.AllowRemoteAddToInventory
  invComp ObjectProperty @0x0 size 8
  ByPC ObjectProperty @0x8 size 8
  bRequestedByPlayer BoolProperty @0x10 size 1
  ReturnValue BoolProperty @0x11 size 1

PrimalItem.CanUse
  bIgnoreCooldown BoolProperty @0x0 size 1
  ReturnValue BoolProperty @0x1 size 1

ShooterPlayerController.ServerRequestInventoryUseItem
  InventoryComp ObjectProperty @0x0 size 8
  ItemId StructProperty @0x8 size 8

ShooterPlayerController.ServerRequestInventoryUseItemWithActor
  anActor ObjectProperty @0x0 size 8
  InventoryComp ObjectProperty @0x8 size 8
  ItemID1 StructProperty @0x10 size 8
  AdditionalData IntProperty @0x18 size 4
```

## Result

Confirmed as `candidate-only`. `sdk.inventory` now has real-core snapshots connecting
item gates and controller-side inventory requests.

`ItemId` and `ItemID1` are reflected `StructProperty` values in the snapshots. This
preserves layout evidence but does not authorize public struct decoding, invocation, or SDK
exposure.

## Rejected Paths

- Transform-heavy item use and item NetExec surfaces remain deferred because they include
  larger structs or command-like behavior.
- Runtime observation remains blocked without a TheIsland/debug-instance approved window.

## Risks

- Evidence is scoped to one core and one ARK binary hash.
- Inventory and item use are gameplay-authoritative surfaces; metadata alone is not policy.
- Public SDK work needs ownership and permission design before exposing item events.

## Next Steps

1. Keep `UseWithTransform` and item NetExec deferred until struct decoding and policy
   gates mature.
2. Use manifest-driven regeneration for all future snapshot additions.
