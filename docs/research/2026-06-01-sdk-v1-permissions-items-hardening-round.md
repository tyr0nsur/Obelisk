# SDK v1 Permissions And Items Hardening Round

Date: 2026-06-01

## Scope

Offline/code-only round. No server starts, restarts, live markers, Discord, push, tag, or
release publication.

This round advanced two SDK-v1-adjacent gates without promoting public ABI:

- permissions/admin planning and pre-ABI checks;
- inventory/items copied-signal hardening.

## Permissions/Admin

Added `scripts/check_permissions_admin_public_readiness.py` as the reusable planning-only
gate for `obelisk.permissions_admin.v1`.

The checker consumes:

- `docs/permissions_admin_public_contract_decisions.json`;
- `docs/public_sdk_surfaces.json`;
- `include/obelisk/ObeliskApi.h`;
- optionally a candidate-only permissions/admin query fail-closed manifest/report.

Current accepted state:

- `accepted_for_planning=true`;
- `planning_only=true`;
- `promotion_ready=false`;
- `public_header_allowed=false`;
- `public_abi_ready=false`;
- `public_sdk_ready=false`;
- `runtime_ready=false`;
- dependency remains `obelisk.player_identity.v1`.

The internal `AuthzDecisionModel` now represents copied query text boundaries already
required by the contract: action bytes are required and bounded to 128 bytes; optional
resource scope bytes are bounded to 256 bytes. This remains an internal candidate model,
not a public permission ABI, command parser, cache ABI, mutation path, or admin surface.

## Items Copied-Signal Hardening

`ItemFieldRange` now preserves property class FName index, property class object index,
and property flags. The copied item bridge revalidates those fields before building copied
item observations for `AllowEquipItem`, `CanRepair`, and `UseItemOntoItem`.

This closes the prior asymmetry with inventory copied-signal handling: item observations
with correct name/offset/size but forged property class metadata or flags now fail closed.

Non-claims:

- no public Inventory SDK or Items SDK;
- no item/inventory identity;
- no lookup, mutation, or return override;
- no new callback ABI;
- no runtime readiness or public SDK readiness.

## Identity Fixture Alignment

Player-principal lifecycle tests now use a temporary directory under the approved offline
workspace root when testing accepted runtime-evidence shapes. This aligns tests with the
current checker rule that accepted copied logs must live under
`/servidor/ark/workspace-offline/live-validation-logs/<run-id>/Obelisk.log`.

The change does not create runtime evidence, authorize server operations, or promote
player identity. It only keeps the synthetic tests aligned with the hardened path
contract.

## Validation

Focused validation run during the round:

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_check_permissions_admin_query_failclosed_contract.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_permissions_admin_public_contract_decisions.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_check_permissions_admin_public_readiness.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_runtime_principal_lifecycle_evidence scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence scripts.test_build_player_identity_runtime_principal_lifecycle_evidence_bundle scripts.test_check_player_identity_public_contract_readiness
ctest --test-dir build --output-on-failure -R 'InventoryReflection|ItemReflection|ProcessEventInventoryReflection|ProcessEventItemReflection|InventoryPolicyEventDispatcher|ItemReturnEventDispatcher'
```

All focused checks passed.
