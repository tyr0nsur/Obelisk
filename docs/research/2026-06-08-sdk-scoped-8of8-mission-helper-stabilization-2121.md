# SDK Scoped 8/8 Mission Helper Stabilization

Date: 2026-06-08 21:21 CEST

## Summary

Fact: the scoped non-complete v1 release statement now records `8/8` reviewed
post-v1/excluded bookkeeping rows. This includes the
`obelisk.mission_transfer_dino_tribe.v1` umbrella and its five leaf exclusions.
The rows remain non-complete accounting only: SDK progress stays `0/12`, P0
dependency-chain progress stays `0/4`, and the active route remains
`approved_runtime_evidence_missing`.

Fact: `scripts/check_mission_transfer_dino_tribe_v1_outcome_accounting.py` now
selects the canonical `obelisk.mission_transfer_dino_tribe.v1:` release-statement
row before scanning leaf exclusions, forbidden claims, or readiness claims. This
fixes a false positive where earlier mention/comment rows, negated readiness
context, or unrelated surface rows could make the mission helper report
`release_statement_forbidden_claims`, `release_statement_ready_overclaims`, or
missing leaf exclusions despite the canonical row being valid.

Fact: tests now separate two routes:

- Current repo manifest: `manifest_umbrella_excluded`, ready, `v1_accounted=true`,
  zero SDK/P0 progress.
- Explicit candidate fixture: `candidate_only`, internal planning coverage for
  candidate/overclaim negative tests.

Fact: Rawls, Lagrange, and Anscombe audit agents completed read-only checks and
were closed. No standby agents remain from this checkpoint.

## Validation

Commands run by the lead:

```bash
python3 -m unittest scripts.test_check_mission_transfer_dino_tribe_v1_outcome_accounting
```

Result: `54 OK`.

```bash
python3 -m unittest scripts.test_report_obelisk_sdk_status
```

Result: `73 OK`.

```bash
python3 -m unittest \
  scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_plain_gate_uses_durable_scoped_statement_without_progress \
  scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_explicit_durable_scoped_statement_satisfies_bookkeeping_without_progress \
  scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_validate_release_statement_scope_uses_durable_default_without_completion_progress \
  scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_release_statement_forbids_scoped_outcome_progress_claims \
  scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_current_manifest_fails_closed_for_v1_completion \
  scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_scoped_release_statement_scope_rejects_affirmative_not_only_claim \
  scripts.test_check_public_sdk_v1_completion.PublicSdkV1CompletionCheckTests.test_scoped_release_statement_scope_rejects_unexpected_surface_records_by_default
```

Result: `7 OK`.

```bash
python3 scripts/report_obelisk_sdk_status.py --compact
```

Result: blocked at `approved_runtime_evidence_missing`, next
`approved_runtime_principal_lifecycle_evidence_bundle`, after-runtime blocker
`identity_public_contract_gate_missing`, SDK `0/12`, P0 `0/4`, source overclaims
`0`.

```bash
python3 scripts/check_public_sdk_v1_completion.py --json | jq '{ready,status,current_route_blocker,complete:.complete_sdk_claim_progress_ratio,p0:.p0_dependency_chain_claim_progress_ratio,release_missing:.release_statement_missing_blocker_outcomes,scoped_missing:.scoped_release_statement_missing_required_outcome_surfaces,mission_ready:.mission_transfer_dino_tribe_outcome_accounting.ready,mission_route:.mission_transfer_dino_tribe_outcome_accounting.accounting_route,mission_source_ready:.mission_transfer_dino_tribe_outcome_accounting.source_ready,mission_source_blockers:.mission_transfer_dino_tribe_outcome_accounting.source_blockers,blockers}'
```

Result: expected blocked JSON with `release_missing=[]`, `scoped_missing=[]`,
mission route `release_statement_umbrella_excluded`, mission source blockers `[]`,
SDK `0/12`, P0 `0/4`.

## Non-Claims

- `8/8` scoped rows do not promote public SDK readiness, runtime readiness,
  package readiness, Plugin Hub readiness, support-tier activation, or stable SDK
  claims.
- Mission/Transfer/Dino/Tribe/Buff umbrella accounting does not add public Mission
  SDK, Transfer SDK, Dino SDK, Tribe SDK, Buff/status SDK, identity, lookup,
  mutation, return override, teleport/spawn, ResourceHandle, or runtime evidence.
- No live server, RCON, Discord send, GitHub, tag, release, marker, env, or ARK log
  operation occurred in this checkpoint.

## Next Step

Fastest complete-SDK unblock is unchanged: produce a checker-accepted copied
approved runtime principal lifecycle evidence bundle, then review the identity
public contract gate. Continue offline SDK hardening in parallel, but do not relax
the `session_start`, exact `CheckJoinInProgress(1,0)` rejected start, and matched
`session_end` sibling-set contract.
