# ScriptStruct Snapshot Fixtures

This fixture root is reserved for sanitized `ScriptStruct` snapshots generated from
offline core evidence.

No real ScriptStruct fixtures are committed yet. Regenerate accepted entries with:

```bash
python3 scripts/regenerate_scriptstruct_snapshots.py \
  --core /path/to/offline/core \
  --obelisk-commit <commit> \
  --check
```

The first accepted fixtures should use:

```text
tests/fixtures/scriptstruct_snapshots/<ark-sha12>/<sdk_module>/<SafeOuter>.<Struct>.snapshot.json
```

ScriptStruct snapshots must use schema `obelisk.scriptstruct-chain.snapshot.v1` and stay
separate from UFunction fixtures.
