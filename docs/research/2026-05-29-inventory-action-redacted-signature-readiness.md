# Inventory Action Redacted Signature Readiness

## Objective

Record the first candidate-only redacted signature artifact for controller-side inventory
use actions. This is offline planning evidence only; it does not promote a public
Inventory SDK, Items SDK, item identity, inventory identity, mutation, return override, or
`ResourceHandle`.

## Environment

- Date: 2026-05-29
- Target set: `inventory-action-compact-intake`
- Snapshot source: committed sanitized UFunction fixtures
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`

## Result

The candidate-only artifact is:

```text
/servidor/ark/workspace-offline/inventory-action-compact-redacted-signatures-20260529T115921Z/signatures.json
sha256=463f89e3b8a7bb0dd58a0a3b27215bb2f37d5c88353d41be8d1ccde151c41a40
schema=obelisk.redacted-ufunction-signatures.v1
signature_count=2
snapshot_count=2
param_count_total=6
copied_scalar_count_total=1
redacted_count_total=5
promotion_ready=false
```

The offline artifact gate accepted it in consume mode:

```text
/servidor/ark/workspace-offline/inventory-action-compact-redacted-signatures-20260529T115921Z/consume-gate.json
sha256=ff9befc5099bdd7cbb6c554ce11921b156e83ad07c4aa1d9bdd93d5232d8ed64
status=accepted
```

## Signature Summary

```text
ShooterPlayerController.ServerRequestInventoryUseItem:
  InventoryComp redacted_uobject_ref
  ItemId redacted_struct

ShooterPlayerController.ServerRequestInventoryUseItemWithActor:
  anActor redacted_uobject_ref
  InventoryComp redacted_uobject_ref
  ItemID1 redacted_struct
  AdditionalData int32
```

`AdditionalData` is a copied scalar candidate only. Do not expose it publicly until its
semantics and sensitivity are understood.

## Promotion Blockers

- The first second-source snapshot comparison is accepted for layout only; see the
  update below. Public SDK/runtime promotion is still blocked.
- `ItemId` / `ItemID1` remain redacted structs; do not expose `ItemNetID` or use it as
  object identity.
- `InventoryComp` and `anActor` remain redacted UObject references.
- The artifact keeps `function_flags_not_bound_to_exact_target_gate` and
  `property_flags_unknown_bits` blockers.

## Validation

```bash
python3 scripts/build_redacted_ufunction_signatures.py \
  --target-set inventory-action-compact-intake \
  --json > /servidor/ark/workspace-offline/inventory-action-compact-redacted-signatures-20260529T115921Z/signatures.json

python3 scripts/validate_offline_artifact_gate.py \
  --root /servidor/ark/workspace-offline \
  --mode consume \
  --manifest /servidor/ark/workspace-offline/inventory-action-compact-redacted-signatures-20260529T115921Z/signatures.json \
  --json > /servidor/ark/workspace-offline/inventory-action-compact-redacted-signatures-20260529T115921Z/consume-gate.json
```

## Boundary

This artifact is useful for planning internal inventory-action recognizers and future
second-source intake. It does not authorize runtime hooks, public callbacks, item handles,
inventory handles, object lookup, mutation, return override, raw parameter exposure, or
cross-binary portability.

## 2026-05-29 Second-Source Layout Update

The target set now has accepted offline second-source UFunction layout evidence:

```text
/servidor/ark/workspace-offline/inventory-action-compact-intake-second-source-20260529T121242Z/pack/snapshot-comparison/readiness-report.json
gate_mode=second_source_promotion
promotion_gate.ready=true
blockers=[]
targets=2
second_source_accepted=2
second_source_missing=0
second_source_rejected=0
```

Accepted targets:

```text
ShooterPlayerController.ServerRequestInventoryUseItem
ShooterPlayerController.ServerRequestInventoryUseItemWithActor
```

Reproducible command:

```bash
RUN_ROOT=/servidor/ark/workspace-offline/inventory-action-compact-intake-second-source-20260529T121242Z

python3 scripts/run_second_source_core_intake.py \
  --binary /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/ShooterGameServer \
  --core /servidor/ark/workspace-offline/vanilla-gdb-arkserver2-TheIsland-20260529T012853Z/raw/core \
  --pack-dir "$RUN_ROOT/pack" \
  --snapshot-root "$RUN_ROOT/ufunction-snapshots" \
  --verified-fname-root-slot 0x5956f30 \
  --gobjects-candidate 0x595b7e0 \
  --target-set inventory-action-compact-intake \
  --execute
```

This closes the second-source layout gap only. It does not promote public Inventory or
Items SDKs, `ItemNetID`, item/inventory/actor identity, `ResourceHandle`, mutation, return
override, raw params, or runtime hooks. The safe model for `ItemId` and `ItemID1` remains:
opaque 8-byte struct parameters used by these two inventory action calls.

## 2026-05-30 Strict Artifact Flow Recommendation

The next offline artifact for `inventory-action-compact-intake` should regenerate the
candidate-only redacted UFunction signatures from the committed sanitized snapshot
manifest and require strict target-set coverage at consume time. This is a documentation
recommendation only; no new artifact was generated in this round.

Recommended offline flow:

```bash
artifact_dir=/servidor/ark/workspace-offline/inventory-action-compact-redacted-signatures-strict-YYYYMMDDTHHMMSSZ
mkdir -p "$artifact_dir"
python3 scripts/build_redacted_ufunction_signatures.py \
  --target-set inventory-action-compact-intake \
  --json > "$artifact_dir/signatures.json"
python3 scripts/validate_offline_artifact_gate.py \
  --mode consume \
  --root /servidor/ark/workspace-offline \
  --manifest "$artifact_dir/signatures.json" \
  --strict-target-set-coverage \
  --json > "$artifact_dir/consume-gate.json"
```

The expected strict artifact property is `target_set_coverage.status=complete` for exactly:

```text
ShooterPlayerController.ServerRequestInventoryUseItem
ShooterPlayerController.ServerRequestInventoryUseItemWithActor
```

Consume-gate acceptance would remain planning hygiene only. It must not be treated as
runtime validation or SDK promotion, and it does not weaken the existing blockers around
redacted `ItemNetID` structs, redacted UObject references, identity, mutation, return
override, raw params, public callbacks, or `ResourceHandle`.

## 2026-05-30 Runtime Observer Gate Blocker

Do not run an `inventory-action-compact-intake` runtime observer from the generic
`enable-inventory-reflection` gate. A future observer needs its own exact target-set gate
before any server-backed window is proposed. That gate must allow only:

```text
ShooterPlayerController.ServerRequestInventoryUseItem
ShooterPlayerController.ServerRequestInventoryUseItemWithActor
```

The gate must fail closed unless it can enforce the exact function name, outer/class,
`ParmsSize`, property-chain shape, binary hash, target-set coverage, redacted UObject
refs, and redacted `ItemNetID` structs before reading parameters. Stable posture checks
and wrappers should scrub or reject any future inventory-action observer marker/env unless
an approved `observer-debug` window is active.

Until that gate exists in code/config, runtime observer runbooks for this target set are
premature. The safe next work is gate design and tests, not server execution. This does
not promote public Inventory/Items SDKs, item or inventory identity, actor identity,
lookup, mutation, return override, raw params, public callbacks, or `ResourceHandle`.
