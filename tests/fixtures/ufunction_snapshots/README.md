# UFunction Snapshot Fixtures

Sanitized `UFunction` property-chain snapshots live here as versioned evidence for
offline analyzer behavior. The committed set is listed in `manifest.json` and can be
regenerated from an existing offline core with:

```bash
python3 scripts/regenerate_ufunction_snapshots.py \
  --core <offline-core-path> \
  --obelisk-commit <obelisk-commit> \
  --artifact-kind offline_core \
  --artifact-sha256 <core-or-evidence-artifact-sha256> \
  --capture-id <sanitized-capture-id> \
  --evidence-pack-id <sanitized-evidence-pack-id> \
  --write
```

Omit `--write` for a dry-run, or use `--check` to compare regenerated output against the
committed fixtures without modifying files. For second-core regeneration where the evidence
commit or capture-specific identity indices naturally differ, use `--check-layout` with
the full artifact identity and explicit `--fname-root-slot` to compare only target
identity, UFunction fields, and property-chain layout. Use
`--target Outer.Function` to regenerate or check one manifest entry.
The artifact fields are sanitized identifiers used by the comparator to mark
self-comparison, shared artifact identity, or missing second-source identity as
`inconclusive`; do not store absolute core paths here. A valid second source must use a
distinct `artifact_sha256`, `capture_id`, and `evidence_pack_id`.

Compare sanitized snapshot layouts between two evidence roots with:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots/<ark-sha12>/<sdk_module> \
  --candidate-root /path/to/second-source/ufunction_snapshots/<ark-sha12>/<sdk_module> \
  --target Outer.Function \
  --json
```

The comparator ignores unstable FName/GObjects indices by default. Use
`--strict-identity-indices` only for intentional same-binary identity checks.

Before a second evidence root exists, summarize current fixture coverage and the remaining
second-source gap with a named target set:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report \
  --target-set minimal-second-source-intake
```

Use `--json` with readiness reports when creating evidence packs. The JSON includes
per-module `target_details` entries with each target key, fixture path, comparability,
block reasons, second-source status, and a top-level `promotion_gate` summary with a
boolean `ready` value plus blocker counts. Target-set entries missing from the base root
are `not_applicable` for second-source status and block the gate as missing base coverage.

When this readiness report is acting as a promotion gate, add
`--fail-on-readiness-gaps` or run
`scripts/check_release_readiness.sh --require-second-source-readiness`.

List the named target sets used by focused readiness checks with:

```bash
python3 scripts/compare_reflection_snapshots.py --list-target-sets
```

Current UFunction target sets:

- `minimal-second-source-intake`: first inventory/structure promotion gate.
- `structure-observer-intake`: all six structure observer UFunctions currently recognized
  internally.
- `buff-compact-intake`: compact `PrimalBuff` bool/scalar shapes for P1 research.
- `dino-compact-intake`: compact dino passenger/carry shapes for P1 research.
- `mission-compact-intake`: compact mission lifecycle and usable-item targets.
- `tribe-compact-intake`: compact tribe/admin-adjacent identity and log targets.
- `transfer-ufunction-intake`: transfer upload/download and validation functions.

Naming:

```text
tests/fixtures/ufunction_snapshots/<ark-sha12>/<sdk_module>/<Outer>.<Function>.snapshot.json
tests/fixtures/ufunction_snapshots/<ark-sha12>/<sdk_module>/<Outer>.<Function>.rejected.snapshot.json
```

These fixtures must not contain core paths, server paths, absolute object addresses,
pointer windows, integer windows, raw logs, player data, or native function pointers. Keep
one target per file so review diffs stay small.
