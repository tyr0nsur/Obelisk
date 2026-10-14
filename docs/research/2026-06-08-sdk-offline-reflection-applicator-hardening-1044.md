# SDK Offline Reflection And Applicator Hardening 1044

Date: 2026-06-08

## Scope

This note records the 10:44 CEST offline ObeliskSDK hardening checkpoint. It did not
touch live ARK servers, `/servidor/ark`, RCON, Discord network sends/reads, deployment
markers, environment files, GitHub, release tags, or publication state.

The checkpoint is non-authorizing and non-evidence. It does not change the active SDK
route: `approved_runtime_evidence_missing` remains the blocker, SDK progress remains
`0/12`, P0 remains `0/4`, and runtime/public/stable readiness remain false until the
approved copied runtime principal lifecycle sibling set passes the checker.

## Integrated Facts

- Six delegated agents completed and were explicitly closed; no standby sub-agent
  remains.
- `tests/core/PlayerPrincipalLifecycleReflectionTests.cpp` now asserts that exact
  `ShooterGameMode.CheckJoinInProgress(1,0)` produces no diagnostic reason, reports
  `PropertyNameIndicesMatched=true`, leaves `PropertyFNameDriftDiagnosticOnly=false`, and
  records no drift entries.
- The same reflection suite now rejects the mixed observed drift chain
  `28512.28414.17729`: each position is individually known from an observed approved
  chain, but the whole Ragnarok/TheIsland mixture is not an approved chain.
- `hooks/ProcessEventPlayerPrincipalLifecycleApplicator.*` now requires a process-local
  apply validation stamp before dispatching or treating an apply result as approved
  runtime evidence loggable. Hand-built `ApplyResult` values with only
  `ValidatedLifecycleEvent=true` no longer dispatch or pass the approved-log gate.
- Applicator canonical shape checks now require exact `FunctionNameIndex` and
  `OuterNameIndex` for accepted start, rejected start, and session end observations, not
  only normalized lifecycle enums/fields.
- `tests/core/PlayerPrincipalLifecycleApplicatorTests.cpp` reproduces the former false
  positive: a real rejected-start apply result paired with a drifted
  `CheckJoinInProgress` observation was loggable before the guard change. It now fails
  the approved-log gate, internal dispatch, and approved evidence budget reservation.
- `scripts/check_player_identity_static_lifecycle_orientation.py` now includes
  `ShooterGameMode.CheckJoinInProgress` as rejected-start static orientation only and
  adds zero-credit guardrails for `CheckJoinInProgressDiagnostic` wording and FName drift
  notes.
- `scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py` now
  rejects mixed/diagnostic `CheckJoinInProgress` context, property/FName mismatch,
  property/FName drift, property-FName chain metadata, and diagnostic guardrails inside
  otherwise exact-looking bundles.
- `scripts/discord_beta_bridge.py` was hardened offline for the beta tester workflow:
  real sends require a matching reviewed dry-run receipt, webhook sends stay deprecated,
  the bot-first bidirectional channel remains `1513238083741683934`, arbitrary tester note
  text is not retained, and the flow stays a single editable status/control message with
  no evidence/progress/readiness claim.
- Handoff/guardrail docs already preserve standing runtime-test authority as
  authorization only, not evidence/readiness/progress; no skill or handoff-policy rule
  change was needed for that invariant.

## Validation

- `cmake --build build --target player_principal_lifecycle_reflection_tests player_principal_lifecycle_applicator_tests -j$(nproc)` passed.
- `ctest --test-dir build -R '^(PlayerPrincipalLifecycleReflectionTests|PlayerPrincipalLifecycleApplicatorTests)$' --output-on-failure` passed (`2/2`).
- `python3 -m unittest scripts/test_check_player_identity_static_lifecycle_orientation.py` -> `5 OK`.
- `python3 -m unittest scripts.test_discord_beta_bridge` -> `31 OK`.
- `python3 -m unittest scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence` -> `197 OK`.
- Focused `git diff --check` over the touched SDK/runtime/checker/Discord files passed.

## Remaining Risks

- The route still requires accepted copied runtime evidence: one sibling-set window with
  `session_start`, exact `ShooterGameMode.CheckJoinInProgress(1,0)`
  `session_start_rejected`, and matched `session_end`.
- Start/end-only runtime material must continue to be treated as partial role material
  until the approved bundle checker accepts the full triplet. The current applicator
  guard prevents local false positives, but route promotion still belongs to the bundle
  checker.
- No live runtime evidence was collected in this checkpoint.

## Next Work

The fastest unblock remains producing and checker-accepting the copied approved runtime
principal lifecycle evidence bundle. Offline work should keep preparing parallel evidence
lanes without relaxing the exact `CheckJoinInProgress(1,0)` triplet contract.
