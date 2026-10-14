# SDK Offline Lifecycle Target Split And Parallel Lanes

Date: 2026-06-08 20:07 CEST

## Summary

This checkpoint advanced the ObeliskSDK offline route while the TheIsland
player-principal lifecycle monitor continued passively. No server restart, marker/env
change, RCON action, Discord send, GitHub operation, release tag, or publication action
occurred in this checkpoint.

Strict route status remains unchanged:

- `approved_runtime_evidence_missing`
- next: `approved_runtime_principal_lifecycle_evidence_bundle`
- after runtime evidence: `identity_public_contract_gate_missing`
- SDK `0/12`, P0 `0/4`
- runtime/public/stable readiness false
- source overclaims `0`

## Integrated Work

The lifecycle static report now separates the two target-set meanings that were easy to
confuse:

- `anchor_binding_target_set = players-identity-lifecycle-intake`
- `triplet_source_target_set = players-lifecycle-anchor-candidates`
- `HandleNewPlayer` and `OnLogout` remain the only lifecycle anchor-binding targets
- `CheckJoinInProgress` is recorded only as observer/rejected-start triplet source
  material with `anchor_binding_status=observer_only_rejected_start_source_not_anchor`

The static report also records that bare `CheckJoinInProgress` names or aliases do not
count as runtime evidence. Approved runtime evidence still requires the copied exact
triplet: `HandleNewPlayer(1,1)`, `CheckJoinInProgress(1,0)`, and matched `OnLogout` in
one valid sibling-set window.

The planning-source manifests were regenerated and verified after the static report hash
changed. `players-identity-lifecycle-anchor-candidates.json` now binds to the current
static report SHA, and `player-identity-planning-source-manifests-report.json` verifies
the generated planning source set.

The lifecycle next-action planner/runner now exposes parallel offline lanes when a
runtime window is active or expires without the exact triplet. These lanes make the next
offline work visible without authorizing any live action:

- runtime-evidence closure/status helpers, waiting for a copied log and sibling sidecars
- single-player multi-surface candidate pack preparation
- post-runtime identity public-contract gate preparation
- post-identity P0 promotion-certificate chain preparation

The runner explicitly blocks those lanes as planning metadata only, so they cannot become
automatic execution, live ops, runtime evidence, SDK progress, P0 progress, or readiness.

The CheckJoin drift parity patch adds fail-closed diagnostic coverage for a mixed
current-runtime-shaped `CheckJoinInProgress` chain. It does not add a new accepted drift
chain and does not weaken the exact triplet contract.

## Delegation

Six agents were spawned and closed.

- Hegel completed the lifecycle static-report target-set split. Lead regenerated and
  verified dependent planning manifests before integrating.
- Gibbs completed the bounded CheckJoin drift parity patch. Lead rebuilt and ran focal
  CTest before integrating.
- Hume completed a read-only SDK/P0 blocker scan. The useful next offline routes are
  identity post-runtime checklist hardening and mission/transfer/dino/tribe/buff outcome
  accounting after this checkpoint.
- McClintock, Plato, and Locke were still running after the wait window and were shut
  down without lead integration.

No sub-agent remains in standby.

## Runtime Watch

At `2026-06-08T18:07:06Z`, the TheIsland passive monitor PIDs `2542521`/`2542523` were
still running. The latest redacted tail showed TheIsland query/RCON `0/70`, only the
player-principal observer-enable line, no accepted lifecycle roles, no complete triplet,
and no approved runtime evidence.

The monitor output remains passive metadata/non-evidence. It does not authorize SDK/P0
progress or readiness.

## Validation

- `python3 -m py_compile` over lifecycle static report, planning manifests, lifecycle
  next-action planner/runner, and owned tests
- `python3 -m unittest scripts.test_build_player_identity_lifecycle_anchor_static_report scripts.test_build_player_identity_planning_source_manifests scripts.test_check_player_principal_lifecycle_planning_blocker_smoke scripts.test_plan_player_principal_lifecycle_next_actions scripts.test_run_player_principal_lifecycle_next_actions` -> `90 OK`
- `python3 scripts/build_player_identity_planning_source_manifests.py --verify-existing-dir docs/research/player-identity-planning-sources --lifecycle-static-report docs/research/player-identity-planning-sources/players-lifecycle-anchor-static-report.json --json` -> `accepted_for_planning=true`, blockers `0`
- `cmake --build build --target player_principal_lifecycle_reflection_tests process_event_player_principal_lifecycle_observer_tests -j2`
- `ctest --test-dir build --output-on-failure -R '^(PlayerPrincipalLifecycleReflectionTests|ProcessEventPlayerPrincipalLifecycleObserverTests|PlayerPrincipalLifecycleReflection|ProcessEventPlayerPrincipalLifecycle)'` -> `2/2`
- `python3 scripts/report_obelisk_sdk_status.py --compact` -> unchanged blocked route, SDK `0/12`, P0 `0/4`, source overclaims `0`
- `python3 scripts/check_public_sdk_v1_completion.py --json` -> blocked, first blockers include stable/release claim disallowance, promoted-experimental surfaces, planning surfaces, and unpromoted P0 dependency chain
- `git diff --check` on the touched lifecycle/planner/research files passed

## Non-Claims

This checkpoint does not provide approved runtime evidence, public SDK readiness, runtime
readiness, stable SDK readiness, SDK/P0 progress, Plugin Hub readiness, publication
authority, or release authority.
