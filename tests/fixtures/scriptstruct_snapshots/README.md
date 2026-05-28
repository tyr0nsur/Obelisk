# ScriptStruct Snapshot Fixtures

This fixture root stores sanitized `ScriptStruct` snapshots generated from offline core
evidence. Fixtures are manifest-backed and candidate-only; they document reflected field
metadata, not public decoding or runtime dispatch contracts.

Regenerate accepted entries with:

```bash
python3 scripts/regenerate_scriptstruct_snapshots.py \
  --core /path/to/offline/core \
  --obelisk-commit <commit> \
  --check
```

For second-core comparisons where the evidence commit naturally differs, use
`--check-layout` as a semantic layout check that ignores capture-specific identity
indices:

```bash
python3 scripts/regenerate_scriptstruct_snapshots.py \
  --core /path/to/second/offline/core \
  --obelisk-commit <commit> \
  --check-layout
```

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

Before a second evidence root exists, use the same comparator as a readiness report so the
ScriptStruct gap stays visible without touching a live server:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/scriptstruct_snapshots \
  --readiness-report
```
