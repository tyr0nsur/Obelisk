# MissionType Function Inventory

## Objective

Evaluate `MissionType` as the next gameplay module after player, item, dino, and structure
fixtures, and record the first fixture-backed mission candidates.

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
  --outer-contains MissionType \
  --max-groups 20 \
  --include-functions \
  --json
```

Fixture coverage was added to `scripts/test_inspect_core_ufunctions.py` for three compact
accepted mission chains plus one deferred string/array-heavy reject path.

## Evidence

`MissionType` has `223` reflected functions in the current offline inventory.

Top families:

```text
Get:45
BP:39
On:15
Set:15
Race:11
Is:9
Mission:8
Spawn:8
Total:6
```

Useful clusters:

```text
player/team:60
allow/can:7
mission state:35
leaderboard/score:5
spawn/teleport:15
blueprint hooks:39
```

Fixture-backed compact candidates:

```text
AddPlayerToMission: 3/3 properties
  PlayerCharacter ObjectProperty offset 0x0 element 8
  bForceAdd BoolProperty offset 0x8 element 1
  ReturnValue BoolProperty offset 0x9 element 1

BPAllowPlayerToLeaveMission: 2/2 properties
  PlayerPawn ObjectProperty offset 0x0 element 8
  ReturnValue BoolProperty offset 0x8 element 1

BPOnPlayerRemovedFromMission: 4/4 properties
  Player ObjectProperty offset 0x0 element 8
  Controller ObjectProperty offset 0x8 element 8
  bFromMissionCompleteEvent BoolProperty offset 0x10 element 1
  bLastPhaseSuccess BoolProperty offset 0x11 element 1
```

Deferred/rejected fixture:

```text
DeferredMissionStringArray: 2/2 properties, rejected
  MissionName StrProperty offset 0x0 element 16
  MissionTags ArrayProperty offset 0x10 element 16

Rejected because the second property exceeds the synthetic ParmsSize. This fixture keeps
string/array-heavy mission paths deferred behind stronger ownership/type gates.
```

## Result

Confirmed as `candidate-only`, with synthetic fixture coverage for compact mission
property-chain shapes. `sdk.missions` is now the next reasonable offline module after
player/items/dinos/structures because it has coherent player-facing mission functions and
small object/bool chains.

No runtime mission hook, invocation, or public SDK mission API is ready.

## Risks

- Evidence is binary-hash-scoped to one core.
- Mission functions may be Genesis/map-specific and blueprint-heavy.
- Mission start/spawn/teleport/leaderboard paths can be gameplay-authoritative and should
  stay offline until stronger policy and ownership gates exist.
- String, array, and large spawn/placement-style structs are explicitly deferred.

## Next Steps

1. Keep fixture work focused on compact object/bool/int/byte chains.
2. Defer `SpawnMission*`, leaderboard rows, string, array, and payload-heavy functions.
3. Compare mission player object params against `ShooterPlayerController` player/session
   candidates before any runtime observation.
4. Consider `PrimalBuff_MissionData` only after mission fixture coverage remains stable.
