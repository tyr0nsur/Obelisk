# Reflection Property Redaction Coverage Check

## Summary

This offline audit looked for an existing generic checker that validates planning-only
UProperty class coverage and redaction policy across sanitized reflection snapshots.
Existing tooling covered adjacent surfaces:

- `scripts/build_redacted_ufunction_signatures.py` and its tests classify/redact generated
  UFunction signature manifests.
- `scripts/build_redacted_scriptstruct_signatures.py` and its tests classify/redact
  generated ScriptStruct signature manifests.
- `scripts/summarize_reflection_scalar_candidates.py` summarizes copied-scalar candidates
  for named UFunction target sets.
- `scripts/validate_offline_artifact_gate.py` validates several produced artifact schemas.

No small standalone checker existed for generic snapshot-level UProperty coverage,
redaction planning, and `ParmsSize` bounds across classes such as `BoolProperty`,
`ObjectProperty`, `IntProperty`, `ArrayProperty.Inner`, `StrProperty`, `StructProperty`,
`ClassProperty`, `ByteProperty`, and `UInt64Property`.

## Added Checker

Added `scripts/check_reflection_property_redaction_coverage.py`.

The checker consumes sanitized JSON artifacts only:

- `obelisk.ufunction-chain.snapshot.v1`
- `obelisk.scriptstruct-chain.snapshot.v1`

It reports planning-only policy for:

- scalar metadata candidates: `BoolProperty`, `ByteProperty`, `IntProperty`,
  `UInt64Property`;
- redacted references/payloads: `ObjectProperty`, `ClassProperty`, `ArrayProperty`,
  `StrProperty`/FString, `StructProperty`;
- nested `ArrayProperty.Inner` metadata with identity redacted;
- identity-like scalar names, including `PlayerDataID`, as redacted sensitive scalars.

For UFunction snapshots it validates `offset_internal + element_size * array_dim <=
ParmsSize`. ScriptStruct snapshots use `PropertiesSize` for the analogous offline bound.

## Non-Claims

This is not payload decoding, FString decoding, object identity, lookup, mutation, return
override, runtime observation, public callbacks, or public ABI. The report explicitly
carries those non-claims.

## Validation

Commands run:

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_check_reflection_property_redaction_coverage.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_reflection_property_redaction_coverage.py --artifact tests/fixtures/ufunction_snapshots/7e7ded49e0c6/sdk_missions/MissionType.GetPlayerUsableItems.snapshot.json --require-class ObjectProperty --require-class ArrayProperty --require-class ArrayProperty.Inner --json
```

Results:

- unit tests: 5 passed;
- real fixture smoke: no blockers for required `ObjectProperty`, `ArrayProperty`, and
  `ArrayProperty.Inner` coverage.
