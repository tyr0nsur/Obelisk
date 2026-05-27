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

Accepted fixtures use:

```text
tests/fixtures/scriptstruct_snapshots/<ark-sha12>/<sdk_module>/<SafeOuter>.<Struct>.snapshot.json
```

ScriptStruct snapshots must use schema `obelisk.scriptstruct-chain.snapshot.v1` and stay
separate from UFunction fixtures.
