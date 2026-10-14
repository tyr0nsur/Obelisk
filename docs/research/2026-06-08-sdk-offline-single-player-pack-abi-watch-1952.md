# SDK Offline Single-Player Pack And ABI Watch

Date: 2026-06-08 19:52 CEST

## Summary

This checkpoint advanced ObeliskSDK offline while the standing-authorized TheIsland
player-principal lifecycle monitor continued to wait for organic players. No server
restart, marker/env change, RCON action, Discord send, GitHub operation, release tag, or
publication action occurred in this checkpoint.

Strict route status remains unchanged:

- `approved_runtime_evidence_missing`
- next: `approved_runtime_principal_lifecycle_evidence_bundle`
- after runtime evidence: `identity_public_contract_gate_missing`
- SDK `0/12`, P0 `0/4`
- runtime/public/stable readiness false
- source overclaims `0`

## Integrated Work

The multi-surface beta capture pack now includes a single-player full-sequence worksheet:

- `single-player-full-sequence-candidate-worksheet.json`
- schema `obelisk.multi-surface-beta-capture-single-player-sequence-worksheet.v1`
- first row is the primary `player_principal_lifecycle` phase
- remaining rows are optional side-lane candidate observations across admin, commands,
  dino, tribe, buff, inventory, item, transfer, and mission
- all rows remain blank-template, redacted-metadata-only, candidate-only, non-evidence,
  non-progress, and non-authorizing

The checker now treats that worksheet as a required pack artifact, hash-bound through the
manifest, validates row order, validates the primary player-principal fields, rejects
pre-filled observation rows, and rejects readiness/runtime/SDK overclaims.

The ABI/package-shape guardrails from the delegated ABI worker were lead-validated:

- example READMEs now say the exact
  `find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)` request is package-shape
  only
- examples clarify borrowed `ObeliskApi`/`ObeliskPluginInitContext` lifetimes, appended
  `struct_size` checks, capability-bit checks, non-zero owner tokens, and paired
  register/unregister slot requirements
- `tests/sdk_consumer/AbiLayoutGuard.c` checks copied gameplay policy, chat, timers, and
  descriptor API consumer preconditions without claiming public package or stable SDK
  readiness

## Delegation

Six agents were spawned and then closed.

- Dalton, Bernoulli, Dirac, and Noether were still running after the wait window and were
  shut down without lead integration.
- Ramanujan completed ABI/package-shape hardening; lead validation passed and the work is
  integrated for this checkpoint.
- Singer completed a read-only static/reversing audit; no files were changed. The useful
  finding is that `CheckJoinInProgress` remains observer-only `session_start_rejected`
  material, not a session-start anchor. The target-set naming still risks confusion:
  `players-identity-lifecycle-intake` is the anchor binding target set, while
  `players-lifecycle-anchor-candidates` is the triplet source set. A future offline patch
  should make that split explicit and should not infer a new `CheckJoinInProgress`
  current-runtime drift chain without copied diagnostic evidence.

No sub-agent remains in standby.

## Runtime Watch

The active TheIsland window was still running at `2026-06-08T17:52:30Z` with monitor
PIDs `2542521`/`2542523`. The latest redacted passive monitor tail showed query/RCON
`0/70`, only the observer-enable gate line, no accepted lifecycle event roles, no complete
triplet candidate, and no approved runtime evidence.

The monitor output remains passive metadata/non-evidence. It does not authorize SDK/P0
progress or readiness.

## Validation

- `python3 -m py_compile scripts/plan_obelisk_multi_surface_beta_capture.py scripts/prepare_obelisk_multi_surface_beta_capture_pack.py scripts/check_obelisk_multi_surface_beta_capture_pack.py scripts/test_prepare_obelisk_multi_surface_beta_capture_pack.py scripts/test_check_obelisk_multi_surface_beta_capture_pack.py`
- `python3 -m unittest scripts.test_plan_obelisk_multi_surface_beta_capture scripts.test_prepare_obelisk_multi_surface_beta_capture_pack scripts.test_check_obelisk_multi_surface_beta_capture_pack` -> `53 OK`
- `python3 -m unittest scripts.test_public_sdk_guardrails` -> `209 OK`
- `cmake --build build --target sdk_consumer_abi_layout_guard`
- `ctest --test-dir build --output-on-failure -R '^(SdkConsumerAbiLayoutGuard|SdkConsumerPackageShapeNonClaimGuard)$'` -> `2/2`
- `cmake --build build --target abi_layout_tests c_abi_layout_tests`
- `ctest --test-dir build --output-on-failure -R '^(AbiLayoutTests|CAbiLayoutTests)$'` -> `2/2`
- `python3 scripts/check_command_permission_route_gate.py --json` -> `accepted_for_planning=true`, blockers `0`
- `python3 scripts/report_obelisk_sdk_status.py --compact` -> unchanged blocked route, SDK `0/12`, P0 `0/4`, source overclaims `0`
- `git diff --check` on tracked ABI/package-shape files passed

## Non-Claims

This checkpoint does not provide approved runtime evidence, public SDK readiness, runtime
readiness, stable SDK readiness, SDK/P0 progress, Plugin Hub readiness, publication
authority, or release authority.
