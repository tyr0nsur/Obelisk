# Dino Second-Wave Fixtures

## Objective

Extend `sdk.dinos` beyond the first attack/passenger-notify fixtures into passenger,
carry, tame-state, and controller dino-stat property chains.

## Environment

- Core:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Real snapshot fixture root:
  `tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_dinos/`
- Obelisk baseline before this note:
  `546e27a Add real core UFunction snapshots`
- Instance source: existing offline core/inventory evidence only.
- Live-server impact: none.

## Hypothesis

Dino passenger and carry functions are the next best broad non-chat surface after
structures because they exercise object, int, bool, bool-return, and gameplay policy
shapes without strings, arrays, large structs, transfer payloads, or admin command risk.

## Method

Extended the synthetic core fixture in `scripts/test_inspect_core_ufunctions.py` with:

```text
PrimalDinoCharacter.AddPassenger
PrimalDinoCharacter.AllowCarryCharacter
PrimalDinoCharacter.BPAllowCarryCharacter
PrimalDinoCharacter.SetCharacterStatusTameable
ShooterPlayerController.ServerRequestDinoCharStats
```

Generated exact-match real-core snapshots for:

```text
PrimalDinoCharacter.AddPassenger
PrimalDinoCharacter.AllowCarryCharacter
```

Exact filters are required because partial matches can mix `AddPassenger` with
`BPNotifyAddPassenger`, and `AllowCarryCharacter` with `BPAllowCarryCharacter`.

## Evidence

Accepted synthetic chains:

```text
PrimalDinoCharacter.AddPassenger
  ACharacter ObjectProperty @0x0 size 8
  PassengerSeatIndex IntProperty @0x8 size 4
  bForcePassenger BoolProperty @0xc size 1
  bAllowFlyersAndWaterDinos BoolProperty @0xd size 1
  bSkipLineTrace BoolProperty @0xe size 1
  ReturnValue BoolProperty @0xf size 1

PrimalDinoCharacter.AllowCarryCharacter
  CanCarryPawn ObjectProperty @0x0 size 8
  ReturnValue BoolProperty @0x8 size 1

PrimalDinoCharacter.BPAllowCarryCharacter
  checkCharacter ObjectProperty @0x0 size 8
  ReturnValue BoolProperty @0x8 size 1

PrimalDinoCharacter.SetCharacterStatusTameable
  bSetTameable BoolProperty @0x0 size 1
  bCreateInventory BoolProperty @0x1 size 1
  bInventoryForWakingTame BoolProperty @0x2 size 1

ShooterPlayerController.ServerRequestDinoCharStats
  theDinoChar ObjectProperty @0x0 size 8
```

Real-core snapshots:

```text
tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_dinos/PrimalDinoCharacter.AddPassenger.snapshot.json
tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_dinos/PrimalDinoCharacter.AllowCarryCharacter.snapshot.json
```

Validation:

```text
python3 scripts/test_inspect_core_ufunctions.py
Ran 33 tests: OK

python3 scripts/test_ufunction_snapshot_fixtures.py
Ran 1 test: OK
```

## Result

Confirmed as `candidate-only`. `sdk.dinos` now has richer fixture-backed coverage and two
real-core sanitized snapshots. This strengthens metadata reconstruction and module
planning, but does not create a runtime hook, invocation path, or public SDK dino API.

## Rejected Paths

- `ServerRequestDinoCharStats` belongs to `ShooterPlayerController`; it supports the dino
  module but should not be documented as a `PrimalDinoCharacter` function.
- Transfer and download dino functions remain deferred because they use large struct
  payloads.
- Runtime observation is blocked until TheIsland or an isolated debug instance has an
  approved window.

## Risks

- Evidence is scoped to one ARK binary hash and one offline core.
- Gameplay-authoritative functions need policy and safety design before runtime use.
- Blueprint hooks may be valuable, but metadata alone does not prove safe call semantics.

## Next Steps

1. Add more real-core snapshots only for exact, compact candidates.
2. Use a future read-only tribe/control fixture as a narrow observation control.
3. Keep transfer/admin/NetExec out of runtime work until policy and struct decoding mature.
