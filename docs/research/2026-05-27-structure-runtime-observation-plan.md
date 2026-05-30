# Structure Runtime Observation Plan

## Objective

Prepare the first gameplay runtime-observed module plan for `sdk.structures`, using
fixture-backed compact functions while keeping public SDK and gameplay mutation blocked.

## Environment

- UFunction manifest:
  `tests/fixtures/ufunction_snapshots/manifest.json`
- Snapshot binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Obelisk baseline:
  `016778a Add transfer ScriptStruct snapshot fixtures`
- Runtime target for future validation:
  `arkserver2` / TheIsland only during a current-turn operator-approved exact debug
  window, or a dedicated debug instance if available and current-turn approved for that
  exact run.

## Candidate Targets

The first runtime-observed structure pass should stay on compact, fixture-backed targets:

| Target | Params | ParmsSize | Observation Value | Runtime Policy |
| --- | ---: | ---: | --- | --- |
| `PrimalStructureItemContainer.VerifyPinCode` | 2 | 5 | pincode gate hit and bool result shape | observe only, do not log pincode values |
| `PrimalStructureItemContainer.AllowToggleActivation` | 2 | 9 | activation permission hit | observe only, copy no `UObject*` |
| `PrimalStructureSeating.CanSeat` | 4 | 18 | seating permission hit | observe only, bool/scalar metadata only |
| `PrimalStructure.SetVariant` | 3 | 6 | variant permission hit | observe only, no mutation/override |

`AllowStructureAccess` and `IsAllowedToDemolish` are also compact, but they are closer to
permission policy and should follow after the four targets above have a working copied-data
pattern.

Second-wave candidates such as `AllowSnappingWith`, `PickupStructure`, elevator helpers,
placement/build/range functions, and string/array/struct-heavy paths stay offline-only
until the first observer proves its filters and data policy.

## Data Policy

Allowed for the first observation pass:

- target name and outer name from reflected metadata,
- `ParmsSize`, `NumParms`, and property class sequence,
- safe scalar copies for bool/int return or input fields when they are bounded by
  `ParmsSize`,
- anonymous counters per target.

Blocked:

- raw `UObject*` exposure to plugins,
- raw pincode values in logs, SDK callbacks, research notes, or external status updates,
- strings, arrays, structs, or object dereferences,
- player names, Steam IDs, tribe IDs, inventories, locations, or dereferenced
  `ForPC`/`forCharacter` data,
- callback mutation, return-value override, or `CallProcessEvent`,
- public SDK surface until ownership and lifetime rules are proven.

## Runtime Gates

Future validation must use the existing filtered `ProcessEvent` path and the debug
instance policy:

1. Do not run on Ragnarok while player testing is active.
2. Use `arkserver2` / TheIsland only in a current-turn operator-approved exact window,
   with plugins disabled unless that approval explicitly names a minimal observer plugin.
3. Resolve exact `Outer.Function` identity before accepting a hit; do not use
   `name-contains` filters because aliases such as `BPOverrideAllowStructureAccess` can
   collide with the intended target family.
4. Register only filtered callbacks by exact name index once a safe runtime name map
   exists. Snapshot `object_index`/GObjects evidence is not a portable runtime filter.
5. Keep global callbacks and broad `ProcessEvent` trace disabled.
6. Confirm stable posture before and after the run.

## Tests Needed Before Runtime

- A structure-specific reflection recognizer test with the four accepted shapes.
- Negative tests for placement/build-authoritative functions such as snapping/build
  targets, ensuring they are not accepted by the first observer.
- Negative tests proving exact outer/name matching rejects partial-name collisions.
- Negative tests rejecting unsupported `StrProperty`, `ArrayProperty`, and
  `StructProperty` in the first observer.
- Bounds tests proving scalar reads never exceed `ParmsSize`.
- Dispatcher tests proving copied data does not outlive callback-owned buffers.

## Result

`sdk.structures` is the best next gameplay runtime-observed candidate because it has compact
fixture-backed functions and clear gameplay value. A first internal `StructureReflection`
recognizer now validates the six compact shapes locally with synthetic memory fixtures.
`ProcessEventStructureReflection` wires that recognizer behind an explicit
disabled-by-default runtime gate:

```bash
touch /servidor/ark/obelisk/state/instances/<instance>/enable-structure-reflection
OBELISK_ENABLE_STRUCTURE_REFLECTION=1
OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256=7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520
OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT=25
OBELISK_STRUCTURE_REFLECTION_DISPATCH_LIMIT=0
```

The command block is a gate template, not approval. The runtime now requires the instance
marker as well as env/SHA/budget. Log and
internal-dispatch limits are separate budgets; both absent or `0` keeps structure
observation inactive. It is not deployed, not enabled by default, and not a public SDK or
mutation API.

## Next Steps

1. Extend `StructureReflection` only if the next target stays scalar-only and
   fixture-backed.
2. Add an operator runbook for the disabled-by-default structure observation gate.
3. Schedule controlled debug/development validation only after the recognizer and negative
   gates pass locally and the operator gives current-turn approval for the exact target
   window, marker/env deltas, start/restart/stop, rollback, and evidence capture.
4. Keep `StructureEvents` internal-only until `structure-observer-intake` has accepted
   second-source evidence and the copied-data ownership gate is reflected in tests and
   release docs.
