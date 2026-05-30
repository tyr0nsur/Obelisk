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

## Promotion Update

Post-RC hardening promoted this slice into exactly three append-only public
`GameplayPolicyEvent` kinds:

- `inventory_item.allow_equip_check`
- `inventory_item.can_repair_check`
- `inventory_item.use_onto_item_check`

Each public kind exposes only `OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE` on the
`INVENTORY_ITEM` resource category. The implementation keeps copied post-original
observation semantics only; artifact promote mode for the broader slice remains blocked,
and this does not create an Items SDK, Inventory SDK, identity surface, mutation path, or
return override.
The current public shape is represented through append-only entries in
`include/obelisk/ObeliskApi.h`, `docs/public_gameplay_events.json`, runtime dispatcher
tables, public SDK fixtures, and plugin callbacks for the narrow copied
`GameplayPolicyEvent` lane only.

## Non-Claims

This does not promote an Items SDK, Inventory SDK, object identity, item identity,
inventory identity, object lookup, `ResourceHandle`, mutation, blocking, return override,
runtime hook, or live-server validation.

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

## Target-Specific Second Source

A distinct sanitized local second-source root exists for this target set:

```text
/servidor/ark/workspace-offline/item-compact-intake-second-source-20260529T141900Z/ufunction-snapshots
```

Focused comparison against the committed fixture root accepted all three copied return bool
targets:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root /servidor/ark/workspace-offline/item-compact-intake-second-source-20260529T141900Z/ufunction-snapshots \
  --readiness-report \
  --target-set item-return-only-policy-slice \
  --fail-on-readiness-gaps \
  --json
```

Preserved evidence pack:

```text
/home/flowcommunity-ark/obelisk-artifacts/item-return-only-second-source-20260530T084918Z
```

Pack checksums:

- `item-return-only-second-source-readiness.json`
  (`sha256=ed05f564352bb63f2d57226fd8d190229af61cc71bdd478782dda31994a609d7`)
- `item-return-only-policy-slice.json`
  (`sha256=53ac249aa107eb059ee420de8e939cc4117fb3590d651025a0bb6286625b1849`)
- `consume-gate.json`
  (`sha256=3aec3d0da5efa8b21291c7b3c29096c46766bed37c7f4ded2286de40bb7407de`)
- `promote-gate.json`
  (`sha256=7044fa956c750c1c6668d812df416065e4ab47a022eb62d01a88b14e8b5b55db`)
- `artifact-pack.manifest.json`
  (`sha256=f513bb3d764b16097cd5c645c02cd602808f6af4e1162ae377163f12579c13b2`)
- relative `SHA256SUMS`
  (`sha256=f89cea383474f8137948f3d5d2687be301b3e08d3ac3bc230f63f455ec20d413`)

Readiness result:

- `targets=3`
- `comparable=3`
- `second_source_accepted=3`
- `promotion_gate.ready=true`
- `promotion_gate.ready_scope=layout_only`
- `promotion_ready=false`

The consume gate accepts the policy slice in this pack. The promote gate still blocks with
`promote_mode_item_return_policy_slice_evidence_only` and
`promote_mode_manifest_has_non_claims`. This closes the target-specific layout
second-source gap for Item return-only, but it does not promote public API, runtime wiring,
identity, mutation, return override, or an Inventory/Items SDK.

## Bool-Tail Refresh

The stale second-source snapshot root above predates strict `BoolProperty` tail
comparison. A fresh offline regeneration from the existing clean core now preserves the
current bool-tail metadata and restores strict second-source acceptance for the same three
targets.

Artifact root:

```text
/home/flowcommunity-ark/obelisk-artifacts/item-return-only-bool-tail-refresh-20260530T172552Z
```

Regenerated snapshots:

- `PrimalItem.AllowEquipItem`
- `PrimalItem.CanRepair`
- `PrimalItem.UseItemOntoItem`

Focused comparison:

```bash
python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root "$OUT/ufunction-snapshots" \
  --readiness-report \
  --target-set item-return-only-policy-slice \
  --fail-on-readiness-gaps \
  --json
```

Readiness result:

- `targets=3`
- `comparable=3`
- `second_source_accepted=3`
- `second_source_inconclusive=0`
- `promotion_gate.ready=true`
- `promotion_gate.ready_scope=layout_only`

Pack checksums:

- `compare-readiness.json`
  (`sha256=ed05f564352bb63f2d57226fd8d190229af61cc71bdd478782dda31994a609d7`)
- `consume-gate.json`
  (`sha256=6c8902f305bae3da62c930dd42a17c756cf0454e46fc69698b5a1ae2188db2ec`)
- `promote-gate.json`
  (`sha256=85c979dc6b5d247ca190d44ba4fa2be302c0296ea5e595884414720bf96cc6e7`)
- `SHA256SUMS`
  (`sha256=3ab095fb4cedeb40e9b02d3f84fa792e4e64f128ca9e36f6577e5d487145ef4f`)

Consume gate accepts this readiness report. Promote gate remains blocked with
`promote_mode_readiness_report_layout_only` and `promote_mode_manifest_has_non_claims`.
This closes the stale bool-tail comparison gap, but it still does not promote public API,
runtime wiring, identity, mutation, return override, or an Inventory/Items SDK.

## Descriptor-Only Preflight

The next descriptor shape, if this slice is ever promoted, should be three distinct
`GameplayPolicyEvent` event-kind descriptors rather than a reuse of
`OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK`. The current public
`INVENTORY_USE_CHECK` descriptor includes `OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN`;
these item observations prove only `ReturnValue`, so reusing that kind would overclaim the
payload and blur `CanRepair.bIgnoreInventoryRequirement` into an unrelated cooldown field.

This section is a historical descriptor-only preflight for the public shape above. The
deliberate ABI promotion has since added append-only enum values, masks, descriptor
coverage, SDK consumer tests, and callback lifecycle review for the three ReturnValue-only
`GameplayPolicyEvent` kinds. Do not reuse the historical candidate-slot guidance for any
new item, inventory, identity, mutation, or return-override surface.

Common candidate descriptor fields:

- `resource_kind`: `OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM`
- `flags`: `OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD |
  OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED`
- `field_mask`: `OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE` only
- `payload`: `bool_values[OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE]` only
- `int32_values`: no copied fields
- `dispatch_phase`: post-original observation only
- `event_kind` and `event_kind_mask`: unassigned candidate slots; future public values must
  be appended and ABI-tested if promoted

Candidate event descriptors:

| Source UFunction | Candidate stable name | Candidate display name | Copied field |
| --- | --- | --- | --- |
| `PrimalItem.AllowEquipItem` | `inventory_item.allow_equip_check` | `Inventory item allow equip check` | `ReturnValue` bool |
| `PrimalItem.CanRepair` | `inventory_item.can_repair_check` | `Inventory item can repair check` | `ReturnValue` bool |
| `PrimalItem.UseItemOntoItem` | `inventory_item.use_onto_item_check` | `Inventory item use onto item check` | `ReturnValue` bool |

Candidate non-claims:

- no `CraftBlueprint` event descriptor;
- no `bIgnoreInventoryRequirement`, `bConsumeResources`, `toInventory`, `DestinationItem`,
  or `AdditionalData` payload fields;
- no item identity, inventory identity, object lookup, stable handle, `ResourceHandle`,
  coordinates, owner/player/tribe identity, mutation, blocking, return override, or UE
  pointer exposure;
- no new capability bit, callback registration function, unregister function, marker/env
  gate, runtime dispatch, or live-server validation.

Promotion gates remain explicit: append-only ABI design, numeric event/mask allocation,
descriptor tests, C and installed-SDK consumer coverage, owner-token lifecycle cleanup
coverage, and a public manifest update are all required before these names become more
than candidate metadata.

## Internal Post-Original Helper

The hook-side item return-only path now has an internal
`TryBuildCopiedItemReturnObservationAfterOriginal` helper. It builds the copied return-only
payload only when the original `ProcessEvent` path reports success, rejects pre-original or
rejected attempts, clears failed output, and keeps copied bool storage independent from
later parameter mutation.

The slice now also has a private/internal `ItemReturnEventDispatcher`. It accepts only
three event kinds (`AllowEquipItem`, `CanRepair`, `UseItemOntoItem`) and exactly one copied
scalar field (`ReturnValue` bool). The dispatcher mirrors existing owner-scoped callback
lifecycle behavior, copies payload storage for callback duration, contains callback
exceptions, and defers user-data cleanup safely when a callback unregisters itself.

The hook producer remains internal plumbing. It is default-off and gated by
`OBELISK_ENABLE_ITEM_RETURN_EVENTS`, observer debug profile/window markers, binary SHA, and
dispatch budget before it builds or dispatches copied observations.

Post-RC HEAD promotes only the three copied `ReturnValue` checks as append-only
`GameplayPolicyEvent` kinds:

- `OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK`
- `OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK`
- `OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK`

That promotion does not add a public Items SDK, public Inventory SDK, live-server
validation claim, mutation, blocking, return override, object identity, `ResourceHandle`,
or any UE internal exposure. Runtime producer validation is still a separate gated
debug-window task.
