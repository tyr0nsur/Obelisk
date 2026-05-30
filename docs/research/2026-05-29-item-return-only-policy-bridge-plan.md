# Item Return-Only Policy Bridge Plan

Date: 2026-05-29

## Objective

Define the next safe internal step for `item-compact-intake` after accepted offline layout
evidence, without expanding the `v0.1.0-rc.1` public ABI or promoting a public Items SDK.

## Current Evidence

- `item-compact-intake` has accepted second-source layout evidence for:
  - `PrimalItem.AllowEquipItem`
  - `PrimalItem.CanRepair`
  - `PrimalItem.CraftBlueprint`
  - `PrimalItem.UseItemOntoItem`
- `ue/ItemReflection.{h,cpp}` recognizes those targets through exact metadata gates and
  exposes only copied bool ranges.
- `ToInventory`, `DestinationItem`, and `AdditionalData` remain metadata-only.

## Existing Event-Shape Boundary

The existing public `GameplayPolicyEvent` surface already has these generic copied POD
concepts:

- `OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK`
- `OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM`
- `OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE`

Only these item fields match that existing copied `RETURN_VALUE` shape:

```text
PrimalItem.AllowEquipItem.ReturnValue
PrimalItem.CanRepair.ReturnValue
PrimalItem.UseItemOntoItem.ReturnValue
```

This shape match does not create an Items SDK, a new callback, a new capability bit, or a
new public Inventory semantic. These fields must stay internal/metadata-only for the RC
public surface:

```text
PrimalItem.CanRepair.bIgnoreInventoryRequirement
PrimalItem.CraftBlueprint.bConsumeResources
PrimalItem.AllowEquipItem.toInventory
PrimalItem.UseItemOntoItem.DestinationItem
PrimalItem.UseItemOntoItem.AdditionalData
```

`bIgnoreInventoryRequirement` must not be mapped to
`OBELISK_GAMEPLAY_POLICY_FIELD_IGNORE_COOLDOWN`; that would create a false semantic claim.
`bConsumeResources` also has no matching public field.

## Design Constraint

`InventoryPolicyEventDispatcher` currently validates `InventoryPolicyEventKind::CanUse`
as an exact two-field shape:

```text
BIgnoreCooldown, ReturnValue
```

Therefore, a future item bridge must not send item return-only events through that shape
by fabricating `BIgnoreCooldown`. The safe choices are:

1. Add an internal return-only item builder/subtype that reaches `GameplayPolicyEvent`
   as `INVENTORY_USE_CHECK` with only `RETURN_VALUE`.
2. Keep `ProcessEventItemReflection` test-only until the internal dispatcher can represent
   return-only inventory-backed signals without weakening `CanUse` validation.

## Test-Only Bridge Status

`ProcessEventItemReflection.{h,cpp}` and `ProcessEventItemReflectionTests` now exist as a
test-only bridge. The helper validates gate state, FName prefiltering, budget handling,
reader-exception fail-closed behavior, exact item field shapes, and forged object/int
range rejection.

The copied observation is intentionally return-only for the existing generic
`GameplayPolicyEvent` field shape:

- `AllowEquipItem.ReturnValue`
- `CanRepair.ReturnValue`, while `bIgnoreInventoryRequirement` is validated but not copied
  into a public-compatible observation
- `UseItemOntoItem.ReturnValue`

`CraftBlueprint.bConsumeResources` has no public field and does not produce a
public-compatible copied observation.

## Minimum Test Requirements Before Runtime Wiring

- Exact FName/outer/flags/`ParmsSize`/property-chain filters for each accepted item target.
- `HasParameterRanges=true` required for copied `ReturnValue` dispatch.
- Object/int fields reject forged ranges.
- `CraftBlueprint` does not dispatch publicly.
- `bIgnoreInventoryRequirement` and `bConsumeResources` do not cross the public payload.
- Reader exceptions fail closed before any copied payload or callback path. The
  hook-side helper may reserve bounded observation budget after exact item FName
  prefiltering and before metadata reads so malformed or throwing reads cannot spam the
  observer window.
- Dispatch, if added later, runs only post-original.
- No SDK/API header, capability bit, plugin callback, marker/env, or runtime log claim is
  added by the test-only slice.

Current validation:

```bash
cmake -S . -B build
cmake --build build --target process_event_item_reflection_tests item_reflection_tests inventory_policy_event_dispatcher_tests c_abi_layout_tests -j"$(nproc)"
ctest --test-dir build -R '^(ProcessEventItemReflectionTests|ItemReflectionTests|InventoryPolicyEventDispatcherTests|CAbiLayoutTests)$' --output-on-failure
```

## Non-Claims

This plan does not promote Items SDK, Inventory SDK, item identity, inventory identity,
object lookup, stable handles, `ResourceHandle`, mutation, blocking, return override,
equip/repair/craft authority, command routing, or live runtime validation.
