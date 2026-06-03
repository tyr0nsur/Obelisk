# SDK Route Claim Hardening

Date: 2026-06-04

## Scope

This checkpoint records a lead-supervised six-agent offline hardening round for
the current SDK route. It does not create approved runtime evidence, promote
player identity, complete the SDK, or authorize runtime/server operations.

The active route remains:

- current blocker: `approved_runtime_evidence_missing`;
- SDK completion: `0/12`;
- P0 dependency chain: `0/4`;
- `stable_claim_allowed=false`.

## Integrated Findings

- Request/window preparation rejects split current-turn approval and operational
  authorization aliases such as runtime work authorized, server restart approved,
  marker changes enabled, publication approved, and generated templates counting
  as operator approval.
- Player identity public-contract readiness rejects nested prose/key/split
  overclaims for public header symbols, opaque principal, principal generation,
  privacy/redaction, real identifiers, lookup, ResourceHandle, permissions/admin,
  commands, runtime readiness, and v1 completion.
- The bound identity route wrapper rejects positive public/runtime/v1 text claims
  outside `non_claim` and `non_claims` fields while continuing to accept negated
  non-claim wording.
- SDK completion release-statement accounting rejects mixed-case surface/status
  rows, support-tier and release-supported wording, nested secondary split
  claims, and mixed-case/hyphen demand-family equivalent aliases.
- Mission/Transfer/Dino/Tribe/Buff umbrella accounting fails closed on promoted
  leaf attempts. The checker can preserve explicit leaf exclusion bookkeeping,
  but it does not create a promoted public SDK, runtime, ABI, ResourceHandle, or
  v1 completion path.
- Buff/status readiness rejects additional public/runtime/v1 false-flag aliases,
  textual overclaims, and symlinked snapshot inputs.
- Logger path validation rejects explicit or root-derived `.` and `..` aliases
  before directory creation.

## Validation

Offline-only validation completed:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  scripts.test_check_player_principal_lifecycle_window_request \
  scripts.test_prepare_player_principal_lifecycle_window_request \
  scripts.test_check_command_permission_route_gate \
  scripts.test_check_command_permission_route_gate_bound_identity_sources
# Ran 147 tests: OK

PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  scripts.test_check_player_identity_public_contract_readiness \
  scripts.test_player_identity_public_contract_decisions \
  scripts.test_check_player_identity_public_contract_gap_report
# Ran 108 tests: OK

PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  scripts.test_check_buff_status_readiness \
  scripts.test_check_mission_transfer_dino_tribe_v1_outcome_accounting
# Ran 49 tests: OK

PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_check_public_sdk_v1_completion.py
# Ran 248 tests in 530.343s: OK

ctest --test-dir build -R '^(LoggerTests|ProcessEventDispatchTests|ProcessEventCallGuardTests|AbiLayoutTests|CAbiLayoutTests|ProcessEvent.*Tests)$' --output-on-failure
# 14/14 tests passed
```

The docs/status auditor also ran the combined guardrail/full-SDK set:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  scripts.test_research_doc_guardrails \
  scripts.test_agent_handoff_guardrails \
  scripts.test_public_sdk_guardrails \
  scripts.test_check_public_sdk_v1_completion \
  scripts.test_release_scope_guardrails \
  scripts.test_check_buff_status_readiness
# Ran 556 tests in 562.171s: OK
```

Final JSON summaries:

- `scripts/check_command_permission_route_gate.py --json`: `valid=true`,
  `planning_only=true`, `current_route_blocker=approved_runtime_evidence_missing`,
  `promotion_ready=false`, `public_sdk_ready=false`, `runtime_ready=false`, and
  `counts_toward_v1_completion=false`.
- `scripts/check_public_sdk_v1_completion.py --json`: `ready=false`,
  `status=blocked`, SDK `0/12`, P0 `0/4`, and
  `stable_claim_allowed=false`.
- `scripts/check_buff_status_readiness.py --json`: `ready=true`,
  `status=candidate_ready`, `fixture_only=true`, `public_sdk_ready=false`,
  `runtime_ready=false`, `stable_claim_allowed=false`, and
  `v1_completion_ready=false`.

## Non-Claims

This checkpoint does not authorize `/servidor/ark` writes, server starts, server
stops, server restarts, marker/env edits, runtime observation, ReflectionScanner,
ptrace/gcore, broad tracing, Discord sends, GitHub publication, tags, releases,
Plugin Hub publication, support-tier activation, v1 completion, or production
stable SDK wording.
