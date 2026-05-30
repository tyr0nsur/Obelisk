# Item Return-Only Policy Slice

Date: 2026-05-30

## Objective

Create the smallest offline evidence slice that proves only these copied item return bools
from committed sanitized UFunction snapshots:

- `PrimalItem.AllowEquipItem.ReturnValue`
- `PrimalItem.CanRepair.ReturnValue`
- `PrimalItem.UseItemOntoItem.ReturnValue`

This slice intentionally excludes `CraftBlueprint`,
`CanRepair.bIgnoreInventoryRequirement`, `CraftBlueprint.bConsumeResources`,
`toInventory`, `DestinationItem`, `AdditionalData`, object refs, mutation, return override,
and public SDK exposure.

## Implementation

- `scripts/reflection_target_sets.py` adds `item-return-only-policy-slice` with exactly
  `AllowEquipItem`, `CanRepair`, and `UseItemOntoItem`.
- `scripts/build_redacted_ufunction_signatures.py --item-return-only-policy-slice --json`
  reads the existing `item-compact-intake` fixture snapshots, validates all four compact
  item shapes, and emits a separate evidence-only report containing only the three copied
  `ReturnValue` bool fields plus the explicit exclusion list.
- The report fails closed if the committed snapshot shape drifts, if `CraftBlueprint` is
  copied, if `bIgnoreInventoryRequirement` or `bConsumeResources` is copied, or if
  `toInventory`, `DestinationItem`, or `AdditionalData` crosses into the copied payload.

## Evidence Source

- Snapshot root: `tests/fixtures/ufunction_snapshots`
- Input target set: `item-compact-intake`
- Output target set: `item-return-only-policy-slice`
- Source ARK binary SHA in fixtures:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Source artifact status: committed sanitized offline-core snapshots, candidate-only
  metadata evidence.

## Validation

```bash
python3 scripts/test_build_redacted_ufunction_signatures.py
python3 scripts/build_redacted_ufunction_signatures.py \
  --item-return-only-policy-slice \
  --json > /tmp/obelisk-item-slice.json
python3 scripts/validate_offline_artifact_gate.py \
  --root /tmp \
  --manifest /tmp/obelisk-item-slice.json \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --mode consume \
  --json
```

Expected policy report result:

- schema: `obelisk.item-return-only-policy-slice.v1`
- copied return bool count: `3`
- excluded field count: `5`
- policy status: `evidence-only`
- copied fields:
  - `PrimalItem.AllowEquipItem.ReturnValue`
  - `PrimalItem.CanRepair.ReturnValue`
  - `PrimalItem.UseItemOntoItem.ReturnValue`
- excluded fields:
  - `PrimalItem.AllowEquipItem.toInventory`
  - `PrimalItem.CanRepair.bIgnoreInventoryRequirement`
  - `PrimalItem.CraftBlueprint.bConsumeResources`
  - `PrimalItem.UseItemOntoItem.DestinationItem`
  - `PrimalItem.UseItemOntoItem.AdditionalData`

## Result

Confirmed as an offline evidence-only slice. The implementation proves that the committed
snapshots support exactly three copied return bool observations and no wider item payload.
The offline artifact gate accepts this schema in consume mode only when the evidence-only
contract, exact copied/excluded field sets, non-claims, and `promotion_ready=false` are
present. It also pins the compact input/copy target sets, requires four declared source
snapshot hashes, and rejects public/runtime readiness overclaims. Promote mode remains
blocked with `promote_mode_item_return_policy_slice_evidence_only`.

The internal `TryBuildCopiedItemReturnObservationForMatchedAttempt` helper is
return-bearing only. It accepts only `AttemptStatus::Matched` attempts whose copied
observation contains the approved `ReturnValue` bool, rejects non-canonical bool bytes
greater than `1`, and returns false for disabled, budget-exhausted, non-item, rejected,
metadata-only, or recognition-only item attempts. It does not authorize public Items SDK,
runtime hook wiring, dispatcher work, mutation, or return override.

Follow-up hardening added explicit wrapper coverage for
`TryObserveInvocation`: disabled gates, non-item FNames, and zero-budget windows do not
read memory, do not reserve observation budget, clear the observation number, and leave no
copied output path. Matching item FNames may reserve bounded budget before metadata reads
so throwing readers fail closed inside the capped observation window. This keeps the helper
test-only and preserves the no-read/no-budget rule for rejected preconditions.

The policy slice artifact and gates were then preserved under:

```text
/home/flowcommunity-ark/obelisk-artifacts/item-return-only-policy-slice-20260530T072255Z
```

Preserved result:

- `item-return-only-policy-slice.json`
  (`sha256=53ac249aa107eb059ee420de8e939cc4117fb3590d651025a0bb6286625b1849`)
- `copied_return_bools=3`
- `excluded_fields=5`
- `coverage.status=complete`
- consume gate: `accepted`
- promote gate: `blocked` with `promote_mode_item_return_policy_slice_evidence_only`
  and `promote_mode_manifest_has_non_claims`

The canonical item compact redacted-signature source remains
`/servidor/ark/workspace-offline/item-compact-redacted-signatures-strict-20260530T013606Z/signatures.json`;
older item compact redacted-signature packs without strict target-set coverage are
historical inputs only.

## Non-Claims

This does not promote an Items SDK, Inventory SDK, public callback, public metadata helper,
object identity, item identity, inventory identity, object lookup, `ResourceHandle`,
mutation, blocking, return override, runtime hook, or live-server validation.
