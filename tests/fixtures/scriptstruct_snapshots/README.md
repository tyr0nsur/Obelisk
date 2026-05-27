# ScriptStruct Snapshot Fixtures

This fixture root is reserved for sanitized `ScriptStruct` snapshots generated from
offline core evidence.

No real ScriptStruct fixtures are committed yet. The first accepted fixtures should use:

```text
tests/fixtures/scriptstruct_snapshots/<ark-sha12>/<sdk_module>/<SafeOuter>.<Struct>.snapshot.json
```

ScriptStruct snapshots must use schema `obelisk.scriptstruct-chain.snapshot.v1` and stay
separate from UFunction fixtures.
