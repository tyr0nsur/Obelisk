# PrimalDinoCharacter Function Inventory

## Objective

Extend the gameplay `UFunction` roadmap into dino gameplay surfaces: riding, passengers,
carry checks, attacks, movement, tame state, and blueprint hooks.

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
  --outer-contains PrimalDinoCharacter \
  --max-groups 20 \
  --include-functions \
  --json
```

Selected property-chain inspection:

```bash
python3 scripts/inspect_core_ufunctions.py \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --max-object-scan 30000 \
  --outer-contains PrimalDinoCharacter \
  --name-contains ServerRequestAttack \
  --name-contains ServerRequestToggleFlight \
  --name-contains ServerClearRider \
  --name-contains AddPassenger \
  --name-contains AllowCarryCharacter \
  --name-contains BP_CanFly \
  --name-contains SetCharacterStatusTameable \
  --json
```

## Evidence

`PrimalDinoCharacter` has `420` reflected functions in the current offline inventory.

Top families:

```text
BP:157
Get:56
Set:21
Is:14
On:13
Server:13
Can:12
Blueprint:11
Update:9
```

Useful clusters:

```text
taming/imprint/order:37
riding/passenger/carry/mounted:94
stats/food/level:13
combat/target/damage/attack:67
movement/fly/jump/velocity:28
buff/status:4
server dino RPCs:13
blueprint hooks:171
```

Representative candidates:

`Candidate` here means an offline metadata target for reconstruction. These names are not
usable functions, callable plugin APIs, runtime hook approvals, or public SDK promises.

| Area | Candidate | Params | ParmsSize | Notes |
| --- | --- | ---: | ---: | --- |
| Passenger | `AddPassenger` | 6 | 16 | Compact object/int/bool return chain. |
| Carry | `AllowCarryCharacter` | 2 | 9 | Small object + bool return gate. |
| Carry hook | `BPAllowCarryCharacter` | 2 | 9 | Blueprint counterpart for comparison. |
| Passenger notify | `BPNotifyAddPassenger` | 2 | 12 | Object + seat index observation surface. |
| Server rider | `ServerClearRider` | 1 | 4 | Minimal server rider control candidate. |
| Server attack | `ServerRequestAttack` | 1 | 4 | Compact attack-index metadata. |
| Server movement | `ServerRequestToggleFlight` | 0 | 0 | Low-param movement observation candidate. |
| Tame setup | `SetCharacterStatusTameable` | 3 | 3 | Three bool params; compact tame-state fixture. |
| Flight gate | `BP_CanFly` | 1 | 1 | Bool return-only blueprint hook. |

Selected property-chain observations:

```text
AddPassenger: 6/6 properties
  ACharacter ObjectProperty offset 0x0 element 8
  PassengerSeatIndex IntProperty offset 0x8 element 4
  bForcePassenger BoolProperty offset 0xc element 1
  bAllowFlyersAndWaterDinos BoolProperty offset 0xd element 1
  bSkipLineTrace BoolProperty offset 0xe element 1
  ReturnValue BoolProperty offset 0xf element 1

AllowCarryCharacter: 2/2 properties
  CanCarryPawn ObjectProperty offset 0x0 element 8
  ReturnValue BoolProperty offset 0x8 element 1

BP_CanFly: 1/1 properties
  ReturnValue BoolProperty offset 0x0 element 1

BPAllowCarryCharacter: 2/2 properties
  checkCharacter ObjectProperty offset 0x0 element 8
  ReturnValue BoolProperty offset 0x8 element 1

BPNotifyAddPassenger: 2/2 properties
  PassengerChar ObjectProperty offset 0x0 element 8
  SeatIndex IntProperty offset 0x8 element 4

ServerClearRider: 1/1 properties
  OverrideUnboardDirection IntProperty offset 0x0 element 4

ServerRequestAttack: 1/1 properties
  AttackIndex IntProperty offset 0x0 element 4

ServerRequestToggleFlight: 0/0 properties

SetCharacterStatusTameable: 3/3 properties
  bSetTameable BoolProperty offset 0x0 element 1
  bCreateInventory BoolProperty offset 0x1 element 1
  bInventoryForWakingTame BoolProperty offset 0x2 element 1
```

## Result

Confirmed as `candidate-only`: dino gameplay has several compact property chains suitable
for offline analyzer fixtures. The best next fixture set is passenger/carry/attack/tame
status because it exercises object, int, bool, bool-return, and zero-param shapes without
large structs.

No runtime hook, invocation, or public SDK dino API is ready from this evidence alone.

## Risks

- Evidence is binary-hash-scoped to one core.
- Blueprint hooks may represent mod extension points, but metadata alone does not prove
  safe server-side call semantics.
- Server attack/rider/flight functions are gameplay-authoritative surfaces and need
  strict runtime gating before observation.
- Taming and order functions may require ownership/team state that is invisible from
  reflected params alone.

## Next Steps

1. Add analyzer fixtures for `AddPassenger`, `AllowCarryCharacter`,
   `ServerRequestAttack`, and `SetCharacterStatusTameable`.
2. Compare dino object params with `ShooterPlayerController` dino request candidates.
3. Build a module taxonomy that groups player, item, dino, and structure candidates into
   future SDK areas while keeping SDK promotion blocked.
4. Use only the currently approved debug/development target or a dedicated debug instance
   for future runtime validation after explicit approval.
