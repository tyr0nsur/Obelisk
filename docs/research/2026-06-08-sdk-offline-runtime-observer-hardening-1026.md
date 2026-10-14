# SDK Offline Runtime Observer Hardening 1026

Date: 2026-06-08

## Scope

This note records the 10:26 CEST offline SDK/runtime hardening checkpoint. It did not
touch live ARK servers, RCON, Discord network sends/reads, `/servidor/ark`, deployment
markers, environment files, GitHub, release tags, or publication state.

The checkpoint is non-authorizing and non-evidence. It does not change the active SDK
route: `approved_runtime_evidence_missing` remains the blocker, SDK progress remains
`0/12`, P0 remains `0/4`, and runtime/public/stable readiness remain false.

## Integrated Facts

- Six delegated agents completed and were explicitly closed; no standby sub-agent
  remains.
- `hooks/ProcessEventPlayerPrincipalLifecycleObserver.*` now rejects
  `HandleNewPlayer(1,0)` as copied lifecycle evidence. `HandleNewPlayer` can build only
  the accepted `session_start` shape when `(bIsFromLogin=true, ReturnValue=true)`.
- Diagnostic-only lifecycle copies now use `LifecycleRole::DiagnosticOnly`. That role
  does not map to `PlayerPrincipalEventKind`, cannot build a `PlayerPrincipalEventView`,
  and has approved runtime evidence log mask `0`.
- Exact rejected-start evidence remains constrained to copied post-original
  `ShooterGameMode.CheckJoinInProgress(1,0)`.
- Activation/runtime-window execution checks now reject diagnostics-only observer envs
  for approved evidence, preserve multi-surface candidate packs as non-evidence, and
  record the exact `CheckJoinInProgress(1,0)` route.
- Closure-request helpers now keep closure/request reports non-ready even when input
  completeness is true, report the full sibling set precisely, include `Obelisk.log` when
  missing, and require copied-bundle checker acceptance before any SDK/P0/status/readiness
  change.
- Runtime evidence status reports now distinguish diagnostic/passive/start-end/context
  material from checker-accepted approved evidence and keep SDK/P0/readiness false.
- Public `STATUS` and `SDK_V1_COMPATIBILITY` docs now state that deferred observer patch
  notes and diagnostic/passive lifecycle material are planning-only and not approved
  runtime evidence, SDK/P0 progress, public SDK readiness, or stable SDK claims.
- UE reflection naming remains unchanged: `CheckJoinInProgressDiagnostic` is retained as
  a reflection-level identifier. Acceptance belongs to downstream exact bool/shape
  validation, not the enum name.

## Deferred Follow-Up

- Add reflection tests asserting exact `CheckJoinInProgress(1,0)` has empty diagnostic
  reason, `PropertyNameIndicesMatched=true`, `PropertyFNameDriftDiagnosticOnly=false`,
  and no drift records.
- Add mixed approved-chain rejection tests for `CheckJoinInProgress` FName drift across
  Ragnarok/TheIsland position values.

## Validation

- `cmake --build build --target process_event_player_principal_lifecycle_observer_tests -j$(nproc)` passed.
- `ctest --test-dir build -R '^ProcessEventPlayerPrincipalLifecycleObserverTests$' --output-on-failure` passed.
- `python3 -m unittest scripts.test_check_player_principal_lifecycle_activation_preconditions scripts.test_prepare_player_principal_lifecycle_runtime_window_execution` -> `89 OK`.
- `python3 -m unittest scripts.test_prepare_player_principal_lifecycle_evidence_closure_request` -> `63 OK`.
- `python3 -m unittest scripts.test_report_player_principal_lifecycle_runtime_evidence_status` -> `36 OK`.
- Focused public SDK/release doc guardrails for deferred-observer non-evidence boundary -> `4 OK`.
- `python3 -m py_compile` on touched Python scripts passed.
- `git diff --check` passed.
- `python3 scripts/report_obelisk_sdk_status.py --compact` still reports
  `approved_runtime_evidence_missing`, next
  `approved_runtime_principal_lifecycle_evidence_bundle`, after-runtime blocker
  `identity_public_contract_gate_missing`, SDK `0/12`, P0 `0/4`, runtime/public/stable
  false, approved runtime/in-game evidence false, and source overclaims `0`.

## Next Work

The fastest unblock remains a checker-accepted copied runtime principal lifecycle sibling
set containing `session_start`, exact `ShooterGameMode.CheckJoinInProgress(1,0)`
`session_start_rejected`, and matched `session_end`.
