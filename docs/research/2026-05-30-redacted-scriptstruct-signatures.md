# Redacted ScriptStruct Signatures

## Objective

Add a small offline review artifact for sanitized `ScriptStruct` snapshots so transfer
payload layouts can be summarized without treating them as runtime payload decoding or a
public SDK contract.

## Environment

- Server impact: none.
- Input root: `tests/fixtures/scriptstruct_snapshots`.
- Target set: `transfer-scriptstruct`.
- Snapshot schema: `obelisk.scriptstruct-chain.snapshot.v1`.
- Output schema: `obelisk.redacted-scriptstruct-signatures.v1`.
- ARK binary SHA from fixture manifest:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.

## Commands

```bash
python3 scripts/build_redacted_scriptstruct_signatures.py \
  --target-set transfer-scriptstruct \
  --json > /tmp/obelisk-redacted-scriptstruct-transfer.json

python3 -m py_compile \
  scripts/build_redacted_scriptstruct_signatures.py \
  scripts/test_build_redacted_scriptstruct_signatures.py

python3 scripts/test_build_redacted_scriptstruct_signatures.py
```

## Result

The `transfer-scriptstruct` target set is summarized from the two committed sanitized
fixtures:

- `PrimalLocalProfile.ARKTributeDino`
- `PrimalLocalProfile.ArkTributePlayerData`

Observed summary from `/tmp/obelisk-redacted-scriptstruct-transfer.json`:

- `signature_count=2`
- `target_set_coverage.status=complete`
- `safety_summary.artifact_status=candidate_only`
- `safety_summary.promotion_ready=false`
- copied scalar candidates by kind: `bool=3`, `float=3`, `uint32=1`
- redacted fields by reason: `array=2`, `class_ref=1`, `sensitive_scalar=3`,
  `text=8`

The script redacts source paths in output, records input snapshot hashes only, preserves
field class/offset/size/array-dim/property-flag metadata, and marks every signature with
promotion blockers.

## Non-Claims

This artifact does not promote:

- public ScriptStruct, Transfer, Inventory, or Items SDKs;
- transfer payload decoding;
- runtime hooks, observers, dispatchers, or plugin callbacks;
- `ResourceHandle`, object identity, lookup, raw UE params, mutation, or return override;
- portability across ARK binary hashes;
- second-source readiness or layout acceptance.

`compare_reflection_snapshots.py` remains the authority for strict second-source layout
readiness. A future broader ScriptStruct inventory pack should consume an offline
evidence-pack/core manifest; this redacted signature script intentionally consumes only
already-sanitized snapshots.
