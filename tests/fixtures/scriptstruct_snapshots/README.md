# ScriptStruct Snapshot Fixtures

This fixture root stores sanitized `ScriptStruct` snapshots generated from offline core
evidence. Fixtures are manifest-backed and candidate-only; they document reflected field
metadata, not public decoding or runtime dispatch contracts.

Regenerate accepted entries with:

```bash
python3 scripts/regenerate_scriptstruct_snapshots.py \
  --core /path/to/offline/core \
  --obelisk-commit <commit> \
  --artifact-kind offline_core \
  --artifact-sha256 <core-or-evidence-artifact-sha256> \
  --capture-id <sanitized-capture-id> \
  --evidence-pack-id <sanitized-evidence-pack-id> \
  --check
```

For second-core comparisons where the evidence commit naturally differs, use
`--check-layout` with the full artifact identity and explicit `--fname-root-slot` as a
semantic layout check that ignores capture-specific identity indices:

```bash
python3 scripts/regenerate_scriptstruct_snapshots.py \
  --core /path/to/second/offline/core \
  --obelisk-commit <commit> \
  --artifact-kind offline_core \
  --artifact-sha256 <core-or-evidence-artifact-sha256> \
  --capture-id <sanitized-capture-id> \
  --evidence-pack-id <sanitized-evidence-pack-id> \
  --fname-root-slot <verified-artifact-fname-root-slot> \
  --check-layout
```

The artifact fields are sanitized identifiers used by the comparator to mark
self-comparison, shared artifact identity, or missing second-source identity as
`inconclusive`; do not store absolute core paths here. A valid second source must use a
distinct `artifact_sha256`, `capture_id`, and `evidence_pack_id`.

Accepted fixtures use:

```text
tests/fixtures/scriptstruct_snapshots/<ark-sha12>/<sdk_module>/<SafeOuter>.<Struct>.snapshot.json
```

ScriptStruct snapshots must use schema `obelisk.scriptstruct-chain.snapshot.v1` and stay
separate from UFunction fixtures.

Use the shared comparator for second-source evidence roots:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/scriptstruct_snapshots/<ark-sha12>/<sdk_module> \
  --candidate-root /path/to/second-source/scriptstruct_snapshots/<ark-sha12>/<sdk_module> \
  --target Outer.Struct \
  --json
```

For the focused transfer intake, prefer the named target set:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/scriptstruct_snapshots \
  --candidate-root /path/to/second-source/scriptstruct_snapshots \
  --target-set transfer-scriptstruct \
  --json
```

Before a second evidence root exists, use the same comparator as a readiness report so the
ScriptStruct gap stays visible without touching a live server:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/scriptstruct_snapshots \
  --readiness-report \
  --target-set transfer-scriptstruct
```

Use `--json` with readiness reports when creating evidence packs. The JSON includes
per-module `target_details` entries with each target key, fixture path, comparability,
block reasons, second-source status, and a top-level `promotion_gate` summary with a
boolean `ready` value plus blocker counts. Target-set entries missing from the base root
are `not_applicable` for second-source status and block the gate as missing base coverage.

When this readiness report is acting as a promotion gate, add
`--fail-on-readiness-gaps` or run
`scripts/check_release_readiness.sh --require-second-source-readiness`.

The release-readiness script has no default RC ScriptStruct target set. Passing
`--scriptstruct-second-source-root` requires at least one explicit
`--scriptstruct-second-source-target-set`; ScriptStruct promotion, including
`transfer-scriptstruct`, is opt-in only and is not part of the default RC gate.

List focused target groups, including `transfer-scriptstruct`, with:

```bash
python3 scripts/compare_reflection_snapshots.py --list-target-sets
```
