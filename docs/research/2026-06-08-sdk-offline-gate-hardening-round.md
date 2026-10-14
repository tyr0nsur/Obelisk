# SDK Offline Gate Hardening Round

Date: 2026-06-08

## Scope

This note records the 2026-06-08 offline SDK integration round after six delegated
agents completed. It did not touch live ARK servers, RCON, Discord network sends/reads,
`/servidor/ark`, deployment markers, environment files, GitHub, release tags, or
publication state.

This checkpoint is non-authorizing and non-evidence. It does not change the active SDK
route: `approved_runtime_evidence_missing` remains the blocker, SDK progress remains
`0/12`, P0 remains `0/4`, and runtime/public/stable readiness remain false.

## Integrated Facts

- The multi-surface beta capture pack now carries a target-bound blank worksheet for
  broad admin, command, dino, tribe, and buff candidates. The worksheet is redacted
  metadata only and cannot count as runtime evidence, SDK/P0 progress, or readiness.
- Beta tester notice preparation now requires the bot-first path with
  `--send-beta-notice`, `--with-beta-controls`, and `--update-active-notice`; webhook
  helper options are rejected for real beta sends.
- Commands/replies final-gate status is visible as non-counting roadmap context. A
  missing or present `obelisk.commands-replies-promotion-certificate.v1` does not move
  SDK/P0 counters without the full dependency chain.
- Runtime observer/checker tests now cover gapped but strictly increasing lifecycle
  sequences such as `[1,3,4]`. Gaps alone are not a violation; the exact strict lifecycle
  triplet still requires `session_start`, exact
  `ShooterGameMode.CheckJoinInProgress(1,0)` `session_start_rejected`, and matched
  `session_end`.
- Player identity public-contract readiness and gap reports now treat planning source
  manifest verification as provenance-only. Planning manifests are not resolved
  contract-review inputs and cannot unlock the after-runtime public-contract gate.
- Runtime player-principal lifecycle applicator evidence logging reuses final safe
  apply/correlation validation before consuming approved evidence budget. A
  `session_end` evidence line requires the supplied logout correlation token to exactly
  match the applied principal token.

## Delegated Results

All six delegated agents completed and were explicitly closed by lead. No standby agent
remained after integration.

- Anscombe: implemented the multi-surface beta capture worksheet and checker coverage.
- Zeno: implemented commands/replies final-gate status/report integration and stale-output
  guardrails.
- Kepler: audited the identity public-contract after-runtime gate; lead integrated the
  planning-manifest provenance-only demotion and deferred stricter builder cross-binding.
- Nietzsche: hardened beta notice preparation and bridge-plan checks for bot-first
  editable notice/buttons and webhook fail-closed posture.
- Plato: hardened runtime applicator approved-evidence budget validation and exact
  logout-correlation token handling.
- Rawls: refreshed compact handoff memory for the previous final-gate/beta-bridge
  checkpoint.

## Validation

Lead-run validation after integration:

- `python3 -m unittest scripts.test_plan_obelisk_multi_surface_beta_capture scripts.test_prepare_obelisk_multi_surface_beta_capture_pack scripts.test_check_obelisk_multi_surface_beta_capture_pack scripts.test_prepare_player_principal_lifecycle_beta_notice scripts.test_check_discord_beta_bridge_plan scripts.test_build_commands_replies_promotion_certificate scripts.test_report_obelisk_sdk_status` -> `157 OK`.
- `cmake --build build --target player_principal_registry_tests player_principal_lifecycle_applicator_tests && ctest --test-dir build -R 'PlayerPrincipal(Registry|LifecycleApplicator)Tests' --output-on-failure` -> `2/2 OK`.
- `python3 -m unittest scripts.test_check_player_identity_public_contract_readiness scripts.test_check_player_identity_public_contract_gap_report` -> `185 OK`.
- Gapped sequence focal tests:
  `scripts.test_analyze_runtime_observer_log.RuntimeObserverLogAnalyzerTests.test_accepts_exact_lifecycle_triplet_with_gapped_increasing_sequences` and
  `scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence.ApprovedRuntimePrincipalLifecycleEvidenceTests.test_strict_selector_accepts_gapped_increasing_sequences` -> `2 OK`.
- `python3 -m unittest scripts.test_agent_handoff_guardrails scripts.test_research_doc_guardrails scripts.test_operational_doc_guardrails` -> `93 OK`.
- `python3 scripts/report_obelisk_sdk_status.py --compact` still reports
  `approved_runtime_evidence_missing`, next
  `approved_runtime_principal_lifecycle_evidence_bundle`, after-runtime blocker
  `identity_public_contract_gate_missing`, SDK `0/12`, P0 `0/4`, runtime/public/stable
  false, approved runtime/in-game evidence false, and source overclaims `0`.

## Deferred Follow-Up

The fastest SDK unblock remains a checker-accepted copied runtime principal lifecycle
sibling-set bundle containing `session_start`, exact
`ShooterGameMode.CheckJoinInProgress(1,0)` `session_start_rejected`, and matched
`session_end`.

The next offline hardening task is to make the identity public-contract decision-record
builder prove that its strict approved-runtime checker report is bound to the same
runtime manifest/evidence input, instead of accepting an unrelated valid strict report.
