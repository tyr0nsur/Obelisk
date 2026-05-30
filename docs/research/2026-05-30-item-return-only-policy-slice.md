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
- `artifact-pack.manifest.json`
  (`sha256=89e9b4af96472314055614824a2b2fce4a0b4343832ae38a2495d77411a5671a`)
- `SHA256SUMS`
  (`sha256=ccd33e42337fd5b1ae3c51333c73ec17aeadef29d3c203b6680bb3be49c7a046`)
- `copied_return_bools=3`
- `excluded_fields=5`
- `coverage.status=complete`
- consume gate: `accepted`
- promote gate: `blocked` with `promote_mode_item_return_policy_slice_evidence_only`
  and `promote_mode_manifest_has_non_claims`

The artifact root now has relative checksums plus a pack manifest. The historical gate
JSON files still preserve their original absolute labels; do not rewrite them by hand.

The canonical item compact redacted-signature source remains
`/servidor/ark/workspace-offline/item-compact-redacted-signatures-strict-20260530T013606Z/signatures.json`;
older item compact redacted-signature packs without strict target-set coverage are
historical inputs only.

## Non-Claims

This does not promote an Items SDK, Inventory SDK, public callback, public metadata helper,
object identity, item identity, inventory identity, object lookup, `ResourceHandle`,
mutation, blocking, return override, runtime hook, or live-server validation.

## Public Shape Dry Run

A focused offline dry run projected the current slice into a possible future public shape
without changing ABI or promoting it:

```text
schema=obelisk.item-return-only-public-shape-dry-run.v1
api_lane=GameplayPolicyEvent copied-scalar observation
dispatch_phase=post-original-observation-only
promotion_ready=false
```

Command shape:

```bash
OUT=/tmp/obelisk-item-public-shape-dry-run-<stamp>
python3 scripts/build_redacted_ufunction_signatures.py \
  --item-return-only-policy-slice \
  --json > "$OUT/item-return-only-policy-slice.json"
python3 scripts/validate_offline_artifact_gate.py \
  --root "$OUT" \
  --manifest "$OUT/item-return-only-policy-slice.json" \
  --expected-binary-sha256 7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 \
  --mode consume \
  --json > "$OUT/consume-gate.json"
```

Result from the local rehearsal:

- consume gate accepted: `59f95f3cb12e95997c1cb90d53c3d98701e178155251c6bc353f69841e9f581c`
- promote gate blocked: `bd51c2a3a36192308c3fb5b0319dfe38b7a1961eab0bf62a7fe72054aeb161c3`
- public-shape dry-run manifest: `6c85e3013cd7a4482ed0208017d1fbaee47dfae137196fbdfde8c2a42f49f87b`

This confirms the nearest future API shape is not an Inventory SDK: it is at most three
post-original copied bool observations, likely as append-only `GameplayPolicyEvent` kinds.
Promotion remains blocked by missing target-specific second-source/static acceptance,
public ABI design, descriptor updates, SDK consumer tests, and callback lifecycle review.
Return override remains explicitly blocked even though the copied field name is
`ReturnValue`.
