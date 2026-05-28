# Tribe Log Control Fixture

## Objective

Add a narrow `sdk.tribes` control fixture for a gameplay zero-parameter reflected
function before exploring broader tribe/alliance policy surfaces.

## Environment

- Core:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Real snapshot:
  `tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_tribes/ShooterPlayerController.ServerRequestTribeLog.snapshot.json`
- Obelisk baseline before this note:
  `5825e4a Add dino second-wave UFunction fixtures`
- Instance source: existing offline core/inventory evidence only.
- Live-server impact: none.

## Hypothesis

`ShooterPlayerController.ServerRequestTribeLog` is a useful observation-control candidate
because it has no parameters and no reflected payload to decode, while still representing
a gameplay request outside chat.

## Method

Added a synthetic zero-param chain fixture and generated a real-core sanitized snapshot
with exact filters:

```text
--outer-exact ShooterPlayerController
--name-exact ServerRequestTribeLog
```

## Evidence

Accepted chain:

```text
ShooterPlayerController.ServerRequestTribeLog
  NumParms 0
  ParmsSize 0
  properties []
```

Validation:

```text
python3 scripts/test_inspect_core_ufunctions.py
python3 scripts/test_ufunction_snapshot_fixtures.py
```

## Result

Confirmed as `candidate-only`. This adds one low-risk shape to the fixture matrix:
gameplay exact target, no params, no param buffer reads.

## Rejected Paths

- Broader tribe/alliance policy remains deferred until a focused inventory identifies
  compact non-admin surfaces.
- Runtime observation is still blocked pending an approved debug/development window.

## Risks

- Zero-param metadata proves recognition shape, not gameplay semantics.
- This should be treated as a control signal, not a public SDK tribe API.

## Next Steps

1. Keep admin, transfer, and NetExec deferred.
2. Consider a focused buffs inventory next only if offline evidence is strong enough.
3. Use this zero-param fixture as a regression target for future exact-name filters.
