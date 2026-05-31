# UFunction Snapshot Manifest Regeneration

> Historical regeneration note. The protected `/servidor/ark/obelisk/dumps` core path
> below records prior validation provenance only. Do not use it as current promotion input;
> use the non-protected raw-layout/core-pack workflow in
> `docs/research/2026-05-31-player-identity-offline-pack-preflight.md` for
> player-identity evidence.

## Objective

Replace manual one-off snapshot commands with a manifest-driven helper so real-core
`UFunction` fixtures can be regenerated consistently and reviewed for drift.

## Environment

- Manifest:
  `tests/fixtures/ufunction_snapshots/manifest.json`
- Helper:
  `scripts/regenerate_ufunction_snapshots.py`
- Core used for local validation:
  `/servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Obelisk baseline used for regenerated snapshot evidence:
  `dacbdff Add tribe log UFunction control fixture`
- Live-server impact: none.

## Hypothesis

A versioned manifest plus an explicit `--write` helper reduces human error when adding
more snapshots. The manifest should name exact `Outer.Name` targets and fixture file names,
while the local core path remains a CLI argument and is never committed.

## Method

Added `scripts/regenerate_ufunction_snapshots.py` with:

```text
--core <offline-core-path>
--manifest tests/fixtures/ufunction_snapshots/manifest.json
--write
--check
--target Outer.Name
--obelisk-commit <commit>
```

Safety properties:

- dry-run is the default;
- `--write` is required for fixture modification;
- `--check` regenerates in memory and compares against committed fixtures;
- output paths are derived from `<sha_prefix>/<module>/<file>`;
- `module`, `outer`, `name`, and `file` reject traversal and shell-sensitive paths;
- generation fails if an exact target resolves to zero or multiple `UFunction` targets;
- snapshots are still validated by `scripts/test_ufunction_snapshot_fixtures.py`.

## Evidence

Local validation:

```text
python3 scripts/regenerate_ufunction_snapshots.py \
  --core /servidor/ark/obelisk/dumps/arkserver-20260527T031311Z/core/arkserver-20260527T031311Z.2902200 \
  --obelisk-commit dacbdff \
  --check

ok tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_structures/PrimalStructure.AllowStructureAccess.snapshot.json
ok tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_structures/PrimalStructure.IsAllowedToDemolish.snapshot.json
ok tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_missions/MissionType.AddPlayerToMission.snapshot.json
ok tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_dinos/PrimalDinoCharacter.AddPassenger.snapshot.json
ok tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_dinos/PrimalDinoCharacter.AllowCarryCharacter.snapshot.json
ok tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_tribes/ShooterPlayerController.ServerRequestTribeLog.snapshot.json
```

Tests:

```text
python3 scripts/test_regenerate_ufunction_snapshots.py
Ran 5 tests: OK

python3 scripts/test_ufunction_snapshot_fixtures.py
Ran 1 test: OK
```

## Result

Confirmed. The snapshot workflow is now manifest-driven and can detect committed fixture
drift without rewriting files. This should be the default path for adding `sdk.inventory`
or future module snapshots.

## Rejected Paths

- The manifest does not store core paths or server paths.
- Arbitrary output paths were rejected in favor of derived fixture paths under the snapshot
  root.
- Manual broad `--name-contains` snapshot generation remains rejected because it can mix
  similarly named functions.

## Risks

- `--check` still needs access to the offline core locally; CI validates committed fixture
  shape but does not regenerate from the private core.
- Snapshot evidence remains binary-hash-scoped and `candidate-only`.

## Next Steps

1. Add `sdk.inventory` targets to the manifest and regenerate through the helper.
2. Keep one exact target per snapshot file.
3. Add rejected real-core snapshots only when a real rejected target exists.
