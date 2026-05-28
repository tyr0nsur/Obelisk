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
commit or capture-specific identity indices naturally differ, use `--check-layout` to
compare only target identity, UFunction fields, and property-chain layout. Use
`--target Outer.Function` to regenerate or check one manifest entry.
The artifact fields are sanitized identifiers used by the comparator to mark
self-comparison or missing second-source identity as `inconclusive`; do not store absolute
core paths here.

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
second-source gap with:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --readiness-report
```

Use `--json` with readiness reports when creating evidence packs. The JSON includes
per-module `target_details` entries with each target key, fixture path, comparability,
block reasons, and second-source status.

List the named target sets used by focused readiness checks with:

```bash
python3 scripts/compare_reflection_snapshots.py --list-target-sets
```

Naming:

```text
tests/fixtures/ufunction_snapshots/<ark-sha12>/<sdk_module>/<Outer>.<Function>.snapshot.json
tests/fixtures/ufunction_snapshots/<ark-sha12>/<sdk_module>/<Outer>.<Function>.rejected.snapshot.json
```

These fixtures must not contain core paths, server paths, absolute object addresses,
pointer windows, integer windows, raw logs, player data, or native function pointers. Keep
one target per file so review diffs stay small.
