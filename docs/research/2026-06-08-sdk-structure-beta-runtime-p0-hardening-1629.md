# SDK Structure/Beta/Runtime/P0 Hardening 1629

## Objective

Advance the fastest ObeliskSDK path without waiting on beta testers by hardening the
offline gates that must consume the next approved runtime player-principal lifecycle
evidence bundle. Preserve the standing runtime/beta-test authority as authorization only,
not evidence or SDK progress.

## Environment

- Date: 2026-06-08 `16:29 CEST`.
- Workspace: `/home/flowcommunity-ark/Obelisk`.
- Live ops: no ARK restart, RCON, marker/env change, deploy, GitHub, tag, release, or
  publication operation was performed in this round.
- Standing authority: recorded in `docs/agent-handoff/CURRENT.md` and
  `docs/agent-handoff/COMPACT_CONTEXT.md`; it remains valid for necessary ObeliskSDK
  runtime/debug/beta evidence operations until revoked, with the two-server cap and
  no-claim limits attached.

## Changes Integrated

- `scripts/check_structure_build_policy_offline_intake.py` now ignores the legacy
  aggregate/census `readiness_checker_candidate` lane while validating only the
  build-policy offline-intake lane. The checker now accepts the current build-policy
  side-lane with `blockers=[]`, while still reporting planning-only and non-counting
  semantics.
- `scripts/prepare_player_principal_lifecycle_beta_notice.py` now preserves the recorded
  standing launch authority as sufficient for the guarded Discord beta notice send scope
  when the request window is current and sendable. It still keeps broad
  `discord_authorized`, SDK progress, runtime evidence, and readiness flags false.
- The stale active-notice state path now rejects positive evidence/progress/readiness
  aliases before reusing or repairing a single editable beta notice.
- Runtime evidence copy/status helpers now carry request-bound commit/review metadata into
  exact analyzer/bundle commands and emit explicit blockers when that metadata is missing.
- P0 promotion-certificate builders now reject stale/current file-payload mismatches,
  shortcut upstream certificate bindings, and invalid output parents while preserving
  zero-progress behavior.
- SDK status accounting now rejects route/blocker-clear aliases from runtime monitors,
  beta bridge reports, beta packs, scoped statements, and side-lane artifacts.
- Focused C++ player-principal lifecycle dispatcher/registry/applicator tests were
  revalidated with no code changes needed.

## Results

- Current SDK route remains `approved_runtime_evidence_missing`.
- Next required artifact remains
  `approved_runtime_principal_lifecycle_evidence_bundle`.
- After-runtime blocker remains `identity_public_contract_gate_missing`.
- SDK progress remains `0/12`; P0 dependency-chain progress remains `0/4`.
- `structure_build_policy_offline_intake` is now accepted for offline planning but remains
  non-evidence, non-runtime, non-public-SDK, and non-completion.
- The Discord beta bridge/bot path is still the preferred beta-tester communication path:
  one editable embed with controls, dry-run/receipt guarded confirmed send, no webhook
  real-send fallback, no raw player text, and no channel flooding.

## Validation

- `python3 -m unittest scripts.test_prepare_player_principal_lifecycle_beta_notice scripts.test_discord_beta_bridge scripts.test_check_discord_beta_bridge_plan`
  - `79 OK`.
- `PYTHONPATH=scripts python3 -m unittest scripts.test_plan_player_principal_lifecycle_runtime_window scripts.test_prepare_player_principal_lifecycle_runtime_window_execution scripts.test_run_player_principal_lifecycle_next_actions scripts.test_copy_player_principal_lifecycle_ready_log scripts.test_report_player_principal_lifecycle_runtime_evidence_status`
  - `158 OK`.
- `python3 -m unittest scripts.test_build_player_identity_promotion_certificate scripts.test_build_permissions_admin_promotion_certificate scripts.test_build_command_chat_response_promotion_certificate scripts.test_build_commands_replies_promotion_certificate`
  - `44 OK` when rerun serially after the completion checker stopped using repo-local
    temp directories.
- `python3 -m unittest scripts.test_check_structure_build_policy_offline_intake`
  - `31 OK`.
- `ctest --test-dir build -R 'PlayerPrincipal(EventDispatcher|Registry|LifecycleApplicator)Tests' --output-on-failure`
  - `3/3` passed.
- `python3 scripts/report_obelisk_sdk_status.py --compact`
  - blocked route, SDK `0/12`, P0 `0/4`, runtime/public/stable false.
- `python3 scripts/check_public_sdk_v1_completion.py --json`
  - blocked as expected; `structure_build_policy_offline_intake.blockers=[]`.
- `git diff --check`
  - clean.

## Rejected Or Non-Evidence

- Standing authority does not count as runtime evidence, SDK/P0 progress, publication
  permission, public SDK readiness, stable SDK readiness, or Plugin Hub readiness.
- Beta notices, active notice state, button events, status summaries, passive monitors,
  copied-log presence, side-lane readiness, and package-shape checks remain non-counting.
- A current build-policy offline-intake `blockers=[]` result must not be used to claim the
  Structure SDK, runtime enforcement, or v1 completion.

## Next Steps

- Keep offline surfaces ready while waiting for the exact runtime triplet:
  `session_start`, `CheckJoinInProgress(1,0)` `session_start_rejected`, and matched
  `session_end` in one checked sibling set.
- When beta testers are available or a runtime candidate needs capture, use the bot-first
  beta notice path under the recorded standing authority and keep ARK concurrency at two
  servers or fewer.
- After a candidate copied log appears, build and check the complete sibling-set evidence
  bundle before changing any SDK/P0 accounting.
