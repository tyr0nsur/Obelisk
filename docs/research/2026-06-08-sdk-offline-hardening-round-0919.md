# SDK Offline Hardening Round 0919

Date: 2026-06-08

## Scope

This note records the 09:19 CEST offline SDK hardening checkpoint. It did not touch live
ARK servers, RCON, Discord network sends/reads, `/servidor/ark`, deployment markers,
environment files, GitHub, release tags, or publication state.

The checkpoint is non-authorizing and non-evidence. It does not change the active SDK
route: `approved_runtime_evidence_missing` remains the blocker, SDK progress remains
`0/12`, P0 remains `0/4`, and runtime/public/stable readiness remain false.

## Integrated Facts

- Identity public-contract readiness is now fail-closed until a reviewed decision record
  is accepted and bound to the same approved runtime evidence. Accepted runtime evidence
  can still appear as the resolved `runtime.lifecycle_evidence` review input, but it no
  longer makes the public-contract checker return `ready=true` by itself.
- The identity decision-record builder and post-runtime bridge now replay the strict
  approved-runtime checker report for the supplied runtime manifest. Stale or mismatched
  strict reports, evidence artifacts, decision records, or certificate summaries are
  rejected before writing downstream artifacts.
- Runtime ready-log copy blocks duplicate start/end context that would later fail the
  approved evidence checker. Exact copy readiness now requires an exact selected triplet,
  one candidate, and zero non-counting context events.
- The older synthetic runtime principal lifecycle shape checker now mirrors the current
  strict vocabulary: `HandleNewPlayer(1,1)`, exact `CheckJoinInProgress(1,0)`, and matched
  `OnLogout`, with apply/correlation status fields. It remains shape-only and cannot
  count as approved runtime evidence.
- Public SDK completion now requires a terminal
  `commands_replies_promotion_certificate` for `obelisk.commands_replies.v1`, and
  promotion certificate bindings must be canonical repo-relative `{path, sha256}` objects
  without absolute paths, `../`, or inline `schema` payloads.
- The local Discord beta bridge gained a summary-only button and command path. It reads
  local redacted bridge metadata, does not append another event row, does not send/read
  Discord network traffic, and cannot count as evidence/progress/readiness.

## Delegated Results

Five delegated agents completed and were closed. One multi-surface pack worker timed out
and was shut down without integration, so no standby sub-agent remained.

- Carver: implemented decision-record builder strict checker replay/canonical mismatch
  rejection.
- Singer: hardened post-runtime bridge binding propagation for strict checker reports,
  runtime evidence artifacts, decision records, and certificate summaries.
- Aristotle: implemented the local-only Discord beta summary button/path.
- Gauss: found ready-log copy duplicate-context and synthetic-shape vocabulary drift;
  lead patched both.
- Copernicus: found terminal commands/replies completion certificate enforcement and
  certificate binding canonicality gaps; lead patched both.
- Noether: multi-surface beta pack task timed out and was closed without integration.

## Validation

- `python3 -m unittest scripts.test_check_player_identity_public_contract_readiness scripts.test_check_player_identity_public_contract_gap_report` -> `185 OK`.
- `python3 -m unittest scripts.test_build_player_identity_public_contract_decision_record scripts.test_build_player_identity_post_runtime_bridge` -> `13 OK`.
- `python3 -m unittest scripts.test_discord_beta_bridge scripts.test_prepare_player_principal_lifecycle_beta_notice scripts.test_check_discord_beta_bridge_plan` -> `69 OK`.
- `python3 -m unittest scripts.test_copy_player_principal_lifecycle_ready_log scripts.test_check_player_identity_runtime_principal_lifecycle_evidence` -> `49 OK`.
- Public completion focals for terminal commands/replies certificate, canonical certificate binding, planning-only commands/replies, nested readiness overclaims, and builder-report non-counting behavior -> `5 OK`.
- `python3 scripts/report_obelisk_sdk_status.py --compact` still reports
  `approved_runtime_evidence_missing`, next
  `approved_runtime_principal_lifecycle_evidence_bundle`, after-runtime blocker
  `identity_public_contract_gate_missing`, SDK `0/12`, P0 `0/4`, runtime/public/stable
  false, approved runtime/in-game evidence false, and source overclaims `0`.

## Next Work

The fastest unblock remains a checker-accepted copied runtime principal lifecycle sibling
set containing `session_start`, exact `ShooterGameMode.CheckJoinInProgress(1,0)`
`session_start_rejected`, and matched `session_end`.

Offline follow-up: re-run the multi-surface beta pack worker scope or fold its intended
correlation improvements into a later, bounded pass.
