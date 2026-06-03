# Direct Route Approved Runtime Binding

Date: 2026-06-03

## Summary

`check_command_permission_route_gate.py` must derive the identity route lock from the
player-identity source checker's approved-runtime diagnosis, not from the mere presence
of `--approved-runtime-principal-lifecycle-evidence-manifest`.

## Facts

- In unit-test and replay contexts, the bound identity wrapper validates a supplied
  approved runtime principal lifecycle evidence manifest with the approved-evidence
  checker before forwarding it. This note records that guardrail, not a current evidence
  artifact.
- The direct route gate path still needed the same fail-closed distinction.
- Unaccepted or arbitrary approved-runtime manifests now keep
  `approved_runtime_evidence_missing`.
- The direct route can reach `identity_public_contract_gate_missing` only in checker output
  where the source checker reports an accepted approved-runtime diagnosis with:
  - `ready=true`
  - `approved_runtime_evidence_present=true`
  - `runtime_evidence_ready=true`
  - `remaining_blockers=[]`
- Player identity first-evidence readiness no longer forwards an unaccepted
  approved-runtime manifest into the public-contract gap checker.

## Non-Claims

- This does not produce approved runtime evidence.
- This does not record a current approved runtime target or approved runtime evidence
  artifact.
- This does not authorize server operations, marker/env changes, runtime capture, or
  Discord.
- This does not promote public identity, permissions/admin, command response,
  commands/replies, ResourceHandle, or SDK v1 completion.

## Validation

- `python3 -m unittest scripts.test_check_command_permission_route_gate`
- `python3 -m unittest scripts.test_check_player_identity_first_evidence_readiness`
- `python3 -m unittest -f scripts.test_check_public_sdk_v1_completion`
- `python3 scripts/check_command_permission_route_gate.py --json`
- `python3 scripts/check_public_sdk_v1_completion.py --json` remains blocked by design:
  SDK `0/12`, P0 `0/4`, `stable_claim_allowed=false`.
