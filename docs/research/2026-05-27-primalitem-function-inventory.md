# PrimalItem Function Inventory

## Objective

Extend the general `UFunction` inventory beyond controller/chat work into item and
inventory behavior, identifying small reflected property chains that can become offline
fixtures before any runtime experiment.

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
  --outer-contains PrimalItem \
  --max-groups 20 \
  --include-functions \
  --json
```

Selected property-chain inspection:

```bash
python3 scripts/inspect_core_ufunctions.py \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --max-object-scan 30000 \
  --outer-contains PrimalItem \
  --name-contains AllowEquipItem \
  --name-contains AllowRemoteAddToInventory \
  --name-contains CanRepair \
  --name-contains CraftBlueprint \
  --name-contains ServerSendItemExecCommandToPlayer \
  --name-contains Use \
  --json
```

## Evidence

`PrimalItem` has `194` reflected functions in the current offline inventory.

Top families:

```text
BP:67
Get:43
Can:9
Is:8
Set:7
Server:6
Remove:5
Blueprint:4
Add:3
Use:3
```

Useful clusters:

```text
crafting/repair:18
use/equip/slot/remote:39
durability:15
ownership/access/allow:17
blueprint hooks:74
server item commands:8
get/is/can/has helpers:89
```

Representative candidates:

| Area | Candidate | Params | ParmsSize | Notes |
| --- | --- | ---: | ---: | --- |
| Equip | `AllowEquipItem` | 2 | 9 | Small object + bool return chain. |
| Remote inventory | `AllowRemoteAddToInventory` | 4 | 18 | Inventory, player controller, request flag, bool return. |
| Use gate | `BPCanUse` / `CanUse` | 2 | 2 | Compact bool-param + bool-return shape. |
| Local use | `LocalUse` | 1 | 8 | Object param for player controller. |
| Item-to-item | `UseItemOntoItem` | 3 | 13 | Destination item, additional data, bool return. |
| Transform use | `UseWithTransform` | 2 | 64 | Tests struct layout pressure via transform-sized param. |
| Crafting | `CraftBlueprint` | 1 | 1 | Minimal bool param. |
| Repair | `CanRepair` | 2 | 2 | Compact repair gate. |
| NetExec | `ServerSendItemExecCommandToPlayer` | 6 | 83 | Larger command surface; defer runtime use. |

Selected property-chain observations:

```text
AllowEquipItem: 2/2 properties
  toInventory ObjectProperty offset 0x0 element 8
  ReturnValue BoolProperty offset 0x8 element 1

AllowRemoteAddToInventory: 4/4 properties
  invComp ObjectProperty offset 0x0 element 8
  ByPC ObjectProperty offset 0x8 element 8
  bRequestedByPlayer BoolProperty offset 0x10 element 1
  ReturnValue BoolProperty offset 0x11 element 1

BPCanUse / CanUse: 2/2 properties
  bIgnoreCooldown BoolProperty offset 0x0 element 1
  ReturnValue BoolProperty offset 0x1 element 1

UseItemOntoItem: 3/3 properties
  DestinationItem ObjectProperty offset 0x0 element 8
  AdditionalData IntProperty offset 0x8 element 4
  ReturnValue BoolProperty offset 0xc element 1

UseWithTransform: 2/2 properties
  bOverridePlayerInput BoolProperty offset 0x0 element 1
  SpawnTransform StructProperty offset 0x10 element 48

ServerSendItemExecCommandToPlayer: 6/6 properties
  ToPC ObjectProperty offset 0x0 element 8
  CommandName NameProperty offset 0x8 element 8
  ExecParams StructProperty offset 0x10 element 64
  bIsReliable BoolProperty offset 0x50 element 1
  bForceSendToLocalPlayer BoolProperty offset 0x51 element 1
  bIgnoreRelevancy BoolProperty offset 0x52 element 1
```

## Rejected Paths

The broad `--name-contains Use` filter also matched non-function or non-call-surface
objects such as `UseItemAddCharacterStatusValue` and `UseSpawnActorLocOffset`. Their
observed property chains were rejected or implausible (`ParmsSize` values such as `49520`
or `19547`). Future focused runs should prefer exact or narrow substrings such as
`CanUse`, `UseItemOntoItem`, `LocalUse`, and `UseWithTransform`.

## Result

Confirmed as `candidate-only`: `PrimalItem` is a strong next offline module because it has
many compact bool/object/struct property chains. It is better suited than admin or transfer
surfaces for the next analyzer fixtures.

No candidate is safe to invoke and no public SDK item API is ready.

## Risks

- Evidence is binary-hash-scoped to one core.
- Blueprint hooks and server item exec commands may encode game-specific authority rules
  that are not visible from metadata alone.
- Transform and exec-param structs need additional struct decoding before runtime
  observation.
- Broad substring matching can pull in unrelated reflected objects; use narrow filters.

## Next Steps

1. Add analyzer fixtures for `AllowRemoteAddToInventory`, `CanUse`, and
   `UseItemOntoItem`.
2. Compare item-use property chains against the controller-side
   `ServerRequestInventoryUseItem*` functions.
3. Produce the next focused report for `PrimalDinoCharacter`.
4. Treat runtime observation as a separate live-ops/debug-window task, not evidence from
   this note; it requires explicit approval, scoped gates, rollback, and stable-posture
   checks before any server execution.
