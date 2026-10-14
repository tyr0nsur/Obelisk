# 2026-06-08 SDK Focused Runtime Correlation/P0 Guardrails Checkpoint

## Summary

Checkpoint at 2026-06-08 15:00 CEST after a focused ObeliskSDK round. The route remains
blocked by missing approved runtime player-principal lifecycle evidence. This round
hardened the paths around that blocker so passive monitor state, beta notices, stale
certificates, side-lane artifacts, and forged lifecycle apply/correlation results cannot
inflate SDK/P0 progress.

Strict status after the round:

- `route=approved_runtime_evidence_missing`
- `next=approved_runtime_principal_lifecycle_evidence_bundle`
- `after_runtime_evidence=identity_public_contract_gate_missing`
- SDK `0/12`
- P0 `0/4`
- runtime/public/stable false
- `source_overclaim_total_flag_count=0`

## Integrated Work

- SDK status reporter guardrail: active passive monitor session metadata with positive
  `ready`, `runtimeReady`, `publicSdkReady`, SDK progress, or P0 progress aliases is
  reported as source overclaim and still contributes zero progress.
- Approved runtime lifecycle checker guardrail: a stray confirmed beta notice sidecar
  beside a no-regular-users window cannot unlock approved evidence.
- C++ player-principal lifecycle hardening: apply validation stamps now bind
  registry/principal/invalidation/mutation provenance, and logout correlation requires
  exact function FName, outer, bool tuple, and redacted-token shape.
- Structure build-policy side-lane hardening: passive snapshots, copied start/end runtime
  evidence, beta-pack aliases, route-blocker rewrites, required-artifact substitutions,
  and non-current target-set aliases remain candidate-only/non-authorizing.
- Installed SDK C ABI consumer hardening: invalid post-copy context and descriptor
  validation failures clear copied API state and do not retain callback/register state.
- Permissions/admin and command/chat response promotion builders re-run current manifest
  validation and report `certificate_written=false` with no hash/binding when blocked,
  even if a preexisting output certificate file exists.

## Delegation State

- Agent A completed and was closed: approved runtime evidence checker/bundle path
  regression for stray confirmed beta notices.
- Agent B completed and was closed: C++ lifecycle applicator/correlation guardrails.
- Agent C was shut down without final result and without lead integration. Treat any
  identity-public-contract work in that scope as pending review until a clean validation
  round accepts it.
- Agent D completed and was closed: permissions/admin and command/chat response
  certificate-builder preflight hardening.
- Agent E completed and was closed: structure build-policy side-lane source artifact
  guardrails.
- Agent F completed and was closed: installed SDK C ABI consumer invalid-context cleanup.

No sub-agent remains in standby.

## Passive Runtime Observation

Standing-authorized passive monitor remains intentionally active:

- parent PID `2164532`
- script PID `2164533`
- log `/tmp/obelisk_passive_player_monitor_20260608T124647Z-player-principal-lifecycle.log`
- snapshot root `/tmp/obelisk-passive-evidence-snapshots/20260608T124647Z-player-principal-lifecycle`
- targets: `arkserver2:TheIsland` and `arkserver:Ragnarok`

Latest checked tail around 2026-06-08 15:00 CEST showed both maps at `players=0/70` and
only partial non-evidence lifecycle material: exact `CheckJoinInProgress(1,0)`
`session_start_rejected` plus unresolved `OnLogout` `session_end` with missing
correlation. This remains passive observer context only and does not satisfy the approved
runtime evidence bundle.

No restart, RCON command, Discord send, marker/env change, GitHub operation, release tag,
publication, or server deployment was performed in this checkpoint.

## Validation

Lead-run validation:

- `python3 -m unittest scripts.test_report_obelisk_sdk_status`: 68 OK
- focused approved-evidence stray beta notice regression: 1 OK
- `ctest --test-dir build --output-on-failure -R '^(PlayerPrincipalLifecycleApplicatorTests|ProcessEventPlayerPrincipalLifecycleObserverTests|PlayerPrincipalLifecycleReflectionTests)$'`: 3/3 passed
- `python3 -m unittest scripts.test_check_structure_build_policy_offline_intake`: 30 OK
- installed SDK C ABI focused CTest regex: 6/6 passed
- permissions/admin and command/chat response builder focal tests: 19 OK
- `python3 scripts/report_obelisk_sdk_status.py --compact`: unchanged blocked route, SDK `0/12`, P0 `0/4`, source overclaims `0`
- `git diff --check` over integrated files passed

Agent-reported additional validation:

- permissions/admin -> command/chat response -> commands/replies suite: 412 OK
- side-lane reflection/structure suite: 282 OK
- installed SDK consumer build/install/package-shape checks passed in the agent report

## Remaining Risk And Next Step

The current critical path is unchanged: capture and checker-accept one valid copied
runtime principal lifecycle sibling set containing `session_start`, exact
`ShooterGameMode.CheckJoinInProgress(1,0)` `session_start_rejected`, and matched
`session_end`. Offline work should continue to close post-identity gates and harden
consumer/package boundaries, but no side-lane artifact, passive monitor, beta notice,
certificate, status report, or package-shape result can count as SDK/P0 progress until
the approved runtime evidence checker accepts the bundle.
