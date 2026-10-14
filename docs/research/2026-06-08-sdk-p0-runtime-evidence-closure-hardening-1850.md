# 2026-06-08 SDK P0 Runtime Evidence Closure Hardening

## Summary

Checkpoint at 18:50 CEST focused on the fastest ObeliskSDK path: keep the P0 chain
blocked until an approved copied runtime principal lifecycle evidence bundle is accepted,
while hardening the offline gates that prepare the post-runtime identity, permissions,
command response, and commands/replies chain.

Strict status after validation remains:

- `current_route_blocker=approved_runtime_evidence_missing`
- `next_required_artifact=approved_runtime_principal_lifecycle_evidence_bundle`
- `after_runtime_evidence=identity_public_contract_gate_missing`
- SDK progress `0/12`, P0 progress `0/4`
- runtime/public/stable readiness false
- source overclaims `0`

## Integrated Work

Six delegated scopes were integrated and all agents were closed:

- Runtime evidence closure fast path: closure requests, next-action planning, and runner
  commands now bind source paths and SHA256 values, reject drift, and keep live-copy or
  passive-wait commands non-executable guidance unless the approved scope exists.
- Static UE4 lifecycle orientation: the required exact runtime triplet is
  `HandleNewPlayer(1,1)`, `CheckJoinInProgress(1,0)`, and matched `OnLogout`; bare
  `CheckJoinInProgress` aliases stay non-counting.
- Beta/live-ops offline orchestration: bot-first beta coordination stays pinned to
  channel `1513238083741683934`; wrong-channel plans fail closed; active notices remain
  communication metadata, not evidence.
- Permissions/admin and command/chat response gates: downstream certificates now require
  current hash-bound upstream identity/permissions inputs and reject stale, alias, or
  runtime-only shortcuts.
- Commands/replies final gate: the terminal certificate records current/upstream surface
  hashes and keeps route-ready/progress aliases false.
- Public SDK completion accounting: the historical Ragnarok passive complete triplet is
  explicitly summarized as `source_scope=historical_documented_passive_context`,
  `freshness=not_current_runtime_evidence`, and `current_live_capture=false`.

## Lead Fix

The lead fixed the final integration failure in
`scripts/check_public_sdk_v1_completion.py`: `approved_in_game_evidence.path_summaries`
now propagates path classification fields from actionable paths:

- `source_scope`
- `freshness`
- `current_live_capture`
- `current_posture_input`
- `approved_offline_bundle_candidate`

The purpose is fail-closed accounting. A passive diagnostic triplet can be visible for
operator routing without becoming current runtime evidence, SDK progress, P0 progress, or
public readiness.

## Validation

Focused validation:

- `python3 -m unittest scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_scoped_release_statement_builder_generates_non_claim_blocker_outcomes`
  - 1 test OK
- `python3 -m unittest scripts.test_build_native_ufunction_registration_static_discovery scripts.test_build_player_identity_lifecycle_anchor_static_report scripts.test_check_player_identity_static_lifecycle_orientation`
  - 19 tests OK
- `python3 -m unittest scripts.test_report_obelisk_sdk_status scripts.test_check_public_sdk_v1_completion scripts.test_build_v1_scoped_release_statement`
  - 431 tests OK
- `python3 scripts/report_obelisk_sdk_status.py --compact`
  - blocked, SDK `0/12`, P0 `0/4`, next approved runtime bundle
- `python3 scripts/check_public_sdk_v1_completion.py --json`
  - exits blocked as expected; confirms the Ragnarok passive triplet is diagnostic
    non-evidence and the approved bundle is still missing
- `git diff --check`
  - OK

Earlier integrated delegated suites also passed before the final checkpoint:

- runtime evidence closure fast path: 118 tests OK
- beta/live-ops offline orchestration: 156 tests OK
- permissions/admin: 289 tests OK
- command/chat response: 142 tests OK
- commands/replies: 126 tests OK

## Live-Ops Boundary

No ARK start/stop/restart, RCON command, Discord send, marker edit, env edit, deployment,
GitHub action, tag, or publication happened in this checkpoint.

The standing authority was used only for posture context before integration: a read-only
process audit observed exactly two ARK servers running, TheIsland `arkserver2` and
Ragnarok `arkserver`, both with `ActiveEvent=Summer`; no Genesis2/third ARK server was
running, and one Discord beta bridge process was present. This posture read is
authorization context only and is not runtime evidence.

## Next Step

The fastest valid route is unchanged: produce and checker-accept a copied
`approved_runtime_principal_lifecycle_evidence_bundle` containing the exact role triplet
in one valid sibling-set window. Offline work can continue preparing downstream gates, but
no SDK/P0 counter should move before that bundle is accepted.
