# Real Core UFunction Snapshot Fixtures

## Objective

Bridge synthetic analyzer fixtures to committed, sanitized real-core snapshots for compact
gameplay `UFunction` property chains.

## Environment

- Core:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Snapshot fixture root:
  `tests/fixtures/ufunction_snapshots/7e7ded49e0c6/`
- Obelisk baseline before this note:
  `9ea497c Add structure policy UFunction fixtures`
- Instance source: existing offline core only.
- Live-server impact: none.

## Hypothesis

Small, one-target `--snapshot-json` files can preserve enough real-core evidence for
review and regression tests without committing core paths, server paths, object addresses,
pointer windows, logs, or player data.

## Method

Added exact name/outer filters to `scripts/inspect_core_ufunctions.py`:

```text
--name-exact <FunctionName>
--outer-exact <OuterName>
```

Added snapshot evidence metadata:

```text
--evidence-ark-sha256 <sha256>
--evidence-obelisk-commit <commit>
--evidence-source offline_core
--evidence-status candidate-only
```

Generated three real-core snapshots:

```text
tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_structures/PrimalStructure.AllowStructureAccess.snapshot.json
tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_structures/PrimalStructure.IsAllowedToDemolish.snapshot.json
tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_missions/MissionType.AddPlayerToMission.snapshot.json
```

## Evidence

Validation now includes:

```text
python3 scripts/test_ufunction_snapshot_fixtures.py
Ran 1 test: OK

python3 scripts/test_inspect_core_ufunctions.py
Ran 28 tests: OK
```

The committed fixture validator checks:

- schema and evidence metadata;
- exactly one target per file;
- absence of local core/server path strings and raw diagnostic windows;
- absence of raw address-like strings except known metadata fields such as flags;
- object/class/outer membership statuses;
- property count agreement;
- `offset_internal + element_size <= ParmsSize` for candidate properties.

## Result

Confirmed. Obelisk now has the first committed real-core `UFunction` snapshot fixtures for
structure policy and mission membership surfaces. This is still `candidate-only`; it
improves regression evidence and reviewability, not public SDK readiness.

## Rejected Paths

- A partial-name snapshot for `AllowStructureAccess` also matched
  `BPOverrideAllowStructureAccess`; exact filters are required for one-target fixtures.
- `MissionType.DeferredMissionStringArray` did not resolve in the current real core by
  exact name/outer, so it remains a synthetic rejected-chain fixture only.

## Risks

- Snapshots are scoped to one binary hash and one core.
- GObjects indices are evidence, not runtime contracts.
- Runtime observation still needs a controlled TheIsland/debug-instance window.

## Next Steps

1. Add a small fixture regeneration helper once more real-core snapshots are accepted.
2. Add dino second-wave fixtures from offline inventory next.
3. Keep rejected real-core snapshots optional until a real rejected chain is found without
   fabricating evidence.
