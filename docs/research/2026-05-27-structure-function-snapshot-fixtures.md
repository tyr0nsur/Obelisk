# Structure Function Snapshot Fixtures

## Objective

Promote a second wave of real-core `sdk.structures` UFunction snapshot fixtures beyond
access and demolish checks, focused on pincode, seating, and variant controls.

## Environment

- Snapshot manifest:
  `tests/fixtures/ufunction_snapshots/manifest.json`
- Snapshot binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Obelisk baseline:
  `19caa07 Check snapshot modules in readiness matrix`
- Source:
  offline core, candidate-only metadata.
- Live-server impact: none.

## Method

Used the offline UFunction inventory and exact inspector snapshots for structure-related
outers and names:

- `PrimalStructureItemContainer.VerifyPinCode`
- `PrimalStructureItemContainer.AllowToggleActivation`
- `PrimalStructureSeating.CanSeat`
- `PrimalStructure.SetVariant`
- `PrimalStructure.AllowSnappingWith` as a deferred comparison candidate.

## Evidence

Accepted fixture targets:

| Target | Params | ParmsSize | Signal |
| --- | ---: | ---: | --- |
| `PrimalStructureItemContainer.VerifyPinCode` | 2 | 5 | `IntProperty pinCode` plus bool return, compact pincode gate. |
| `PrimalStructureItemContainer.AllowToggleActivation` | 2 | 9 | `ObjectProperty ForPC` plus bool return, compact container activation gate. |
| `PrimalStructureSeating.CanSeat` | 4 | 18 | Controller/character object refs, force bool, bool return. |
| `PrimalStructure.SetVariant` | 3 | 6 | Variant index, force bool, bool return. |

All four exact targets resolved as `Function` with candidate UObject membership and
bounded property chains in the inspected core.

## Result

`sdk.structures` now has real fixture coverage for access, demolish, pincode, container
activation, seating, and variant paths. This remains metadata evidence only; the fixtures
do not imply public SDK surface, permission behavior, or safe runtime dispatch.

## Rejected Paths

- `PrimalStructure.AllowSnappingWith`: valid compact candidate, but deferred because
  snapping/placement policy is closer to build-authoritative gameplay and should follow
  pincode/seating/variant evidence.
- Elevator pin-code and weight helpers: deferred until broader structure-container scope is
  needed.
- Large placement/build chains: deferred because they require deeper struct and policy
  review.

## Risks

- Names describe gameplay intent, but the snapshots only prove reflected metadata shape.
- Object parameters remain pointer metadata, not ownership or lifetime guarantees.
- Runtime probing stays gated to the currently approved debug/development target or an
  isolated debug instance in an approved window.

## Next Steps

- Regenerate fixtures from the manifest and keep path coverage validated.
- Consider mission leave/notify snapshots next to broaden gameplay functionality.
- Keep placement/build-authoritative targets deferred until policy and struct decoding
  gates are explicit.
