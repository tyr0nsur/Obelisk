# Inventory Recognition Plan

Current note, 2026-05-31: this is historical planning for the internal recognizer. Since
this note was written, `PrimalItem.CanUse` and `PrimalItem.AllowRemoteAddToInventory`
copied scalars were promoted only through the general `GameplayPolicyEvent` copied policy
surface as inventory-backed signals. There is still no standalone Inventory SDK, Items
SDK, item/inventory identity, lookup, mutation, return override, raw UE pointer exposure,
or item payload decoding. Treat the final 2026-05-27 statement about "no public callback"
as superseded only by that narrow `GameplayPolicyEvent` path.

## Objective

Define the next gameplay SDK recognition target after `sdk.structures`: a narrow internal
`InventoryReflection` recognizer for compact item-use and remote-add metadata.

## Environment

- UFunction manifest:
  `tests/fixtures/ufunction_snapshots/manifest.json`
- Snapshot binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Obelisk baseline:
  `26d2c7b Bound structure reflection observation budget`
- Live-server impact: none.

## First-Wave Targets

| Target | Params | ParmsSize | Policy |
| --- | ---: | ---: | --- |
| `PrimalItem.CanUse` | 2 | 2 | Scalar-only recognizer candidate. |
| `PrimalItem.AllowRemoteAddToInventory` | 4 | 18 | Object refs remain opaque; bool fields only may expose ranges internally. |

Observed fixture shapes:

```text
PrimalItem.CanUse
  bIgnoreCooldown BoolProperty @0x0 size 1
  ReturnValue BoolProperty @0x1 size 1

PrimalItem.AllowRemoteAddToInventory
  invComp ObjectProperty @0x0 size 8
  ByPC ObjectProperty @0x8 size 8
  bRequestedByPlayer BoolProperty @0x10 size 1
  ReturnValue BoolProperty @0x11 size 1
```

## Deferred Targets

- `ShooterPlayerController.ServerRequestInventoryUseItem`
- `ShooterPlayerController.ServerRequestInventoryUseItemWithActor`
- `PrimalInventoryComponent.InventoryCustomFilter`

These are useful fixture-backed surfaces, but they include `StructProperty` or
`ArrayProperty` payloads. They can be recognized as metadata-only in a later phase, but
must not expose decoded item ids, arrays, inventory contents, actor refs, or item movement
semantics.

## Data Policy

Allowed internally:

- exact function and outer identity,
- `NumParms`, `ParmsSize`, return offset, and field metadata,
- safe bool ranges for non-object, non-struct fields,
- bounded observation counts.

Blocked:

- raw `UObject*` exposure,
- inventory contents,
- decoded `ItemId` or item net structs,
- array contents,
- `CallProcessEvent`, return override, or mutation,
- public SDK callbacks.

## Tests Needed

- `InventoryReflectionTests` for `CanUse` and `AllowRemoteAddToInventory`.
- Reject wrong SHA, wrong outer, wrong `ParmsSize`, wrong `NumParms`, wrong field class,
  wrong offset, and partial-name collisions.
- Verify object parameters do not expose borrowed ranges.
- Verify bool fields expose ranges only when params are readable.
- Future `ProcessEventInventoryReflectionTests` must copy the structure gate discipline:
  disabled gate reads nothing, non-inventory FName reads nothing, and observation budget is
  explicit and bounded.

## Result

`sdk.inventory` should be the next internal recognizer after structures because it has
compact fixture-backed item policy functions and high modding value. It remains
gameplay-authoritative, so this plan is recognition-only and must not become public SDK or
runtime mutation work.

`InventoryReflection` now validates `PrimalItem.CanUse` and
`PrimalItem.AllowRemoteAddToInventory` locally with synthetic fixtures. It is internal only:
there is no `ProcessEvent` gate, no public callback, and no item payload decoding.
