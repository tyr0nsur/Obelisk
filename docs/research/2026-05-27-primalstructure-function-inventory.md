# PrimalStructure Function Inventory

## Objective

Extend the gameplay `UFunction` roadmap into structures: access, snapping, pickup,
demolish, variant, seating, containers, and elevator controls.

## Environment

- Evidence pack:
  `/servidor/ark/obelisk/dumps/core-pack-gobjects-sample-20260527T041027Z`
- Core:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Instance source: existing offline core/evidence pack only.
- Live-server impact: none.

## Method

Focused inventory:

```bash
python3 scripts/summarize_core_ufunction_inventory.py \
  --evidence-pack /servidor/ark/obelisk/dumps/core-pack-gobjects-sample-20260527T041027Z \
  --max-objects 30000 \
  --outer-contains PrimalStructure \
  --max-groups 20 \
  --include-functions \
  --json
```

Selected property-chain inspection:

```bash
python3 scripts/inspect_core_ufunctions.py \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --max-object-scan 30000 \
  --outer-contains PrimalStructure \
  --name-contains AllowStructureAccess \
  --name-contains AllowSnappingWith \
  --name-contains IsAllowedToDemolish \
  --name-contains PickupStructure \
  --name-contains SetVariant \
  --name-contains VerifyPinCode \
  --name-contains CanSeat \
  --name-contains ServerActivate \
  --json
```

## Evidence

`--outer-contains PrimalStructure` finds `222` reflected functions in the current offline
inventory:

```text
PrimalStructure:154
PrimalStructureItemContainer:42
PrimalStructureSeating:15
PrimalStructureElevatorPlatform:11
```

Top families:

```text
BP:83
Get:19
Is:17
Set:14
Net:10
On:10
Can:7
Update:6
```

Useful clusters:

```text
placement/snapping/build:53
blueprint/BP hooks:86
network/client/replication:30
seating/elevator/control:28
pickup/demolish/destroy/repair:23
container/inventory/fuel:23
linked/range/water/power:20
color/variant/paint/material:17
access/pincode/owner/tribe:15
ship/exosuit/critical:17
```

Representative candidates:

| Area | Candidate | Params | ParmsSize | Notes |
| --- | --- | ---: | ---: | --- |
| Access | `AllowStructureAccess` | 2 | 9 | PC object + bool return. |
| Snapping | `AllowSnappingWith` | 3 | 17 | Other structure, PC, bool return. |
| Demolish | `IsAllowedToDemolish` | 2 | 9 | PC object + bool return. |
| Pickup | `PickupStructure` | 3 | 24 | Quick pickup bool, PC, object return. |
| Variant | `SetVariant` | 3 | 6 | Int, bool, bool return. |
| Container | `VerifyPinCode` | 2 | 5 | Int pincode + bool return. |
| Seating | `CanSeat` | 4 | 18 | PC, character, force bool, bool return. |
| Elevator | `ServerActivate` | 3 | 10 | PC, bool, `ByteProperty` direction. |
| Deferred string | `BPRename` | 1 | 16 | Useful only after `FString` gates. |
| Deferred placement | `IsAllowedToBuild*` / placement functions | many | large | Struct-heavy and mutation-prone. |

Selected property-chain observations:

```text
PrimalStructure.AllowStructureAccess: 2/2 properties
  ForPC ObjectProperty offset 0x0 element 8
  ReturnValue BoolProperty offset 0x8 element 1

PrimalStructure.AllowSnappingWith: 3/3 properties
  OtherStructure ObjectProperty offset 0x0 element 8
  ForPC ObjectProperty offset 0x8 element 8
  ReturnValue BoolProperty offset 0x10 element 1

PrimalStructure.IsAllowedToDemolish: 2/2 properties
  ForPC ObjectProperty offset 0x0 element 8
  ReturnValue BoolProperty offset 0x8 element 1

PrimalStructure.PickupStructure: 3/3 properties
  bIsQuickPickup BoolProperty offset 0x0 element 1
  PC ObjectProperty offset 0x8 element 8
  ReturnValue ObjectProperty offset 0x10 element 8

PrimalStructure.SetVariant: 3/3 properties
  VariantIndex IntProperty offset 0x0 element 4
  bForceSet BoolProperty offset 0x4 element 1
  ReturnValue BoolProperty offset 0x5 element 1

PrimalStructureItemContainer.VerifyPinCode: 2/2 properties
  pinCode IntProperty offset 0x0 element 4
  ReturnValue BoolProperty offset 0x4 element 1

PrimalStructureSeating.CanSeat: 4/4 properties
  ForPC ObjectProperty offset 0x0 element 8
  forCharacter ObjectProperty offset 0x8 element 8
  bForce BoolProperty offset 0x10 element 1
  ReturnValue BoolProperty offset 0x11 element 1

PrimalStructureElevatorPlatform.ServerActivate: 3/3 properties
  ForPC ObjectProperty offset 0x0 element 8
  bForceDirection BoolProperty offset 0x8 element 1
  Dir ByteProperty offset 0x9 element 1
```

## Result

Confirmed as `candidate-only`: structure access, pincode, variant, seating, and simple
pickup/demolish functions are good offline fixture candidates. Placement/build/range
functions should stay second-wave because they include larger structs, arrays, and higher
gameplay-authority risk.

No runtime hook, invocation, or public SDK structure API is ready from this evidence alone.

## Risks

- Evidence is binary-hash-scoped to one core.
- `outer_contains=PrimalStructure` is useful but not a complete derived-structure taxonomy.
- Placement, build, range, network replication, and `BP*` hooks may mutate or depend on
  complex authority state.
- `StrProperty`, `ArrayProperty`, and large struct params need separate ownership/type
  gates before runtime observation.

## Next Steps

1. Add analyzer fixtures for `AllowStructureAccess`, `IsAllowedToDemolish`,
   `VerifyPinCode`, `SetVariant`, and `CanSeat`.
2. Add one `ByteProperty` fixture from `PrimalStructureElevatorPlatform.ServerActivate`.
3. Defer `BPRename` until `FString` handling remains gated and fixture-backed.
4. Keep placement/build functions as second-wave offline fixtures; do not runtime-probe
   them first.
