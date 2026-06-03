# P0 Runtime Evidence Gate Snapshot

## Purpose

Record the current P0 SDK route after the tribe/accounting checkpoint so future
agents do not confuse internal side-lanes with progress on the complete v1 SDK
claim.

## Baseline

- Obelisk commit: `279b16c Integrate tribe scalar accounting evidence`
- Date: 2026-06-03
- Runtime/server operation: none
- Publication operation: none

## Commands

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_player_principal_lifecycle_planning_blocker_smoke.py --json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json
```

## Observed State

`check_command_permission_route_gate.py --json` reports:

- `valid=true`
- `planning_only=true`
- `current_route_blocker=approved_runtime_evidence_missing`
- `next_route_action=produce_approved_runtime_principal_lifecycle_evidence`
- `counts_toward_v1_completion=false`
- `public_sdk_ready=false`
- `runtime_ready=false`
- `promotion_ready=false`
- route lock `locked=true`
- `blocked_until=[approved_runtime_principal_lifecycle_evidence, reviewed_identity_public_contract]`

`check_player_principal_lifecycle_planning_blocker_smoke.py --json` reports:

- `ready=true`
- `next_blocker=approved_runtime_evidence_missing`
- `approved_runtime_evidence_present=false`
- `server_operations_authorized=false`
- `runtime_work_authorized=false`
- `public_sdk_ready=false`
- `runtime_ready=false`
- `promotion_ready=false`
- `v1_completion_ready=false`

`check_public_sdk_v1_completion.py --json` exits blocked by design and reports:

- `ready=false`
- `status=blocked`
- `stable_claim_allowed=false`
- `stable_release_contract_claim_allowed=false`
- complete SDK progress `0/12`
- P0 dependency chain progress `0/4`
- route blocker `approved_runtime_evidence_missing`
- recommended next action: produce approved copied runtime principal lifecycle
  evidence before any public identity, permissions/admin, command response, or
  commands/replies ABI.

## Non-Claims

- This snapshot is not runtime evidence.
- This snapshot does not authorize marker changes, env changes, server starts,
  server restarts, runtime observation, ReflectionScanner, ptrace/gcore, broad
  tracing, Discord, publication, or GitHub state changes.
- Request packs, preflight sidecars, receipt templates, route acceptance, and
  planning smoke acceptance remain offline guardrails only.
- Tribe scalar/accounting, inventory copied signals, structure census, mission
  copied bools, and other side-lanes remain non-counting for the P0 dependency
  chain and complete SDK claim.

## Next Action

The next true P0 blocker remains approved copied runtime principal lifecycle
evidence under a current-turn operator-approved live-ops window. After that
evidence is accepted, the route may advance only to locked planning blocker
`identity_public_contract_gate_missing`, with all public SDK, public ABI,
runtime, promotion, permissions/admin, command response, commands/replies, and
v1 completion flags still false until the separate public contract gate is
reviewed.

## Same-Day Route Hardening

The next supervised audit round closed two offline route-accounting gaps without
changing the default blocker:

- `check_player_identity_public_contract_gap_report.py` now keeps both
  `current_blocker` and `next_blocker` at `approved_runtime_evidence_missing`
  until approved runtime evidence is actually accepted. It no longer advertises
  `identity_public_contract_gate_missing` as the next blocker while runtime
  evidence is missing.
- `check_player_identity_public_contract_readiness.py` now treats
  `runtime.lifecycle_evidence` as resolved only when the approved runtime
  evidence input is accepted, while all public/header/runtime/promotion/v1 flags
  remain false.
- `bind_player_identity_planning_sources.py` preserves durable lifecycle
  `artifact_identity.source_artifact_ids` when a lifecycle manifest already has
  accepted static anchor provenance. Binding still updates per-anchor snapshot
  SHA evidence from the selected first-evidence source; it does not replace the
  static source IDs with first-evidence placeholder IDs.
- `check_command_permission_route_gate_bound_identity_sources.py` now verifies
  that route-gate canonical manifest paths point to the exact transient bound
  lifecycle/principal manifests it generated, not only that the child report says
  `matched=true`.
- The bound route wrapper can forward an explicit approved runtime principal
  lifecycle evidence manifest; with that input the only allowed blocker is still
  locked planning-only `identity_public_contract_gate_missing`.

These changes are guardrails only. They do not create approved runtime evidence,
do not authorize runtime work, do not promote public identity, and do not move
SDK progress above `0/12` or P0 above `0/4`.
