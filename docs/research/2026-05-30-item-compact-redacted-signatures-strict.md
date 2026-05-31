# Item Compact Redacted Signatures Strict Coverage

## Summary

Generated a fresh candidate-only redacted UFunction signature report for
`item-compact-intake` from sanitized fixture snapshots, with strict target-set coverage
metadata and a consume gate result.

This is offline review evidence only. It does not promote a public Items SDK, Inventory
SDK, ResourceHandle, identity, lookup, mutation, return override, runtime hook, or public
callback.

## Artifact

- Artifact root:
  `/servidor/ark/workspace-offline/item-compact-redacted-signatures-strict-20260530T013606Z`
- Signatures:
  `/servidor/ark/workspace-offline/item-compact-redacted-signatures-strict-20260530T013606Z/signatures.json`
- Consume gate:
  `/servidor/ark/workspace-offline/item-compact-redacted-signatures-strict-20260530T013606Z/consume-gate.json`
- `signatures.json` SHA256:
  `85e79300f0f46f4c71811e1195d806a8692c0a697fb8b6321831d877a9715b97`
- `consume-gate.json` SHA256:
  `f9e245285bd79134aca42646187bc421eae80d853bd2ce1d6712eefdd494ea55`

## Command

```bash
artifact_dir=/servidor/ark/workspace-offline/item-compact-redacted-signatures-strict-20260530T013606Z
mkdir -p "$artifact_dir"
python3 scripts/build_redacted_ufunction_signatures.py \
  --target-set item-compact-intake \
  --json > "$artifact_dir/signatures.json"
python3 scripts/validate_offline_artifact_gate.py \
  --mode consume \
  --root /servidor/ark/workspace-offline \
  --manifest "$artifact_dir/signatures.json" \
  --strict-target-set-coverage \
  --json > "$artifact_dir/consume-gate.json"
```

## Result

- Gate status: `accepted`
- Gate blockers: `0`
- Target set: `item-compact-intake`
- Coverage status: `complete`
- Signature count: `4`
- Promotion ready: `false`
- Emitted targets:
  - `PrimalItem.AllowEquipItem`
  - `PrimalItem.CanRepair`
  - `PrimalItem.CraftBlueprint`
  - `PrimalItem.UseItemOntoItem`

## Interpretation

This replaces the older item compact redacted-signature artifact for future review work
because it includes `target_set_coverage` and passes strict consume validation.

The useful post-RC path remains internal/test-only return-value exploration for selected
`PrimalItem` functions. Do not map `CanRepair.bIgnoreInventoryRequirement` to the public
`IGNORE_COOLDOWN` field, and do not expose object refs or `AdditionalData` through the
public ABI.

## GameplayPolicyEvent Boundary

This strict `item-compact-intake` artifact is a review aid for item recognizer shape. It
is not the public backing lane by itself. The public `GameplayPolicyEvent` item backing is
the narrower `item-return-only-policy-slice`, and only these copied fields may cross that
boundary:

- `PrimalItem.AllowEquipItem.ReturnValue`;
- `PrimalItem.CanRepair.ReturnValue`;
- `PrimalItem.UseItemOntoItem.ReturnValue`.

`CraftBlueprint`, `CanRepair.bIgnoreInventoryRequirement`, destination inventory refs,
destination item refs, `AdditionalData`, item identity, lookup, mutation, and return
override remain redacted or blocked. The next real gate for richer item work is a separate
copied-data proposal with second-source evidence, ABI tests, installed SDK consumer tests,
privacy/redaction policy, lifecycle cleanup, and approved runtime validation if runtime
evidence is needed.
