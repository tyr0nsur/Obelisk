# UFunction Snapshot Fixtures

Sanitized `UFunction` property-chain snapshots live here as versioned evidence for
offline analyzer behavior. Each file is generated from an existing offline core with:

```bash
python3 scripts/inspect_core_ufunctions.py \
  --core <offline-core-path> \
  --max-object-scan 30000 \
  --outer-exact <OuterName> \
  --name-exact <FunctionName> \
  --snapshot-json \
  --evidence-ark-sha256 <ark-binary-sha256> \
  --evidence-obelisk-commit <obelisk-commit>
```

Naming:

```text
tests/fixtures/ufunction_snapshots/<ark-sha12>/<sdk_module>/<Outer>.<Function>.snapshot.json
tests/fixtures/ufunction_snapshots/<ark-sha12>/<sdk_module>/<Outer>.<Function>.rejected.snapshot.json
```

These fixtures must not contain core paths, server paths, absolute object addresses,
pointer windows, integer windows, raw logs, player data, or native function pointers. Keep
one target per file so review diffs stay small.
