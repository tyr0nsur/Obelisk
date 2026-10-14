# 2026-06-08 SDK Offline Public Boundary And Runtime Contract Hardening

## Scope

Offline/local ObeliskSDK acceleration checkpoint. No live server, RCON, Discord, marker,
env, GitHub, tag, release, or `/servidor/ark` operation occurred in this round.

Current SDK accounting remains intentionally unchanged:

- route: `approved_runtime_evidence_missing`
- next: `approved_runtime_principal_lifecycle_evidence_bundle`
- after-runtime blocker: `identity_public_contract_gate_missing`
- SDK: `0/12`
- P0: `0/4`
- runtime/public/stable readiness: false
- source overclaims: `0`

## Delegated Work Integrated

All six delegated workers were closed; no standby agent remained after integration.

- Planck hardened `scripts/check_player_identity_public_header_gate.py` and tests so
  public header gate aliases require an approved strict runtime report shape, exact
  lifecycle triplet, source provenance, and fresh runtime binding.
- Huygens hardened player-identity public contract readiness/gap reporting so reviewed
  templates and accepted post-runtime decision records are distinct, non-progress inputs
  unless the runtime evidence binding is accepted.
- Cicero hardened `scripts/check_public_sdk_v1_completion.py` so public header/contract
  reports, templates, generated certs, beta packs, package-shape metadata, status reports,
  and start/end-only artifacts cannot shortcut P0 or v1 completion.
- Darwin hardened command permission route gates and bound-identity source checks against
  reviewed-template, public-header/status, generic status/copy, generated-cert, and stale
  identity-certificate aliases.
- Leibniz hardened the approved runtime evidence bundle builder/checker by binding the
  lifecycle correlation proof to the source summary, copied log, window, selected roles,
  sibling cases, safe fields, and logout correlation.
- Fermat completed a read-only public/debug boundary audit and found raw ProcessEvent
  debug registration leaking into generic SDK consumer fixtures.

## Lead Integration

The lead removed raw ProcessEvent debug registration from generic SDK consumers:

- `tests/sdk_consumer/MinimalPlugin.cpp`
- `tests/sdk_installed_consumer/consumer_plugin.cpp`
- `tests/sdk_installed_consumer/c_abi_plugin.c`
- `tests/sdk_consumer/SdkConsumerFixture.cpp`
- `tests/sdk_consumer/CMakeLists.txt`
- `scripts/test_public_sdk_guardrails.py`

Raw ProcessEvent handle coverage remains in explicit debug/legacy guardrails. Generic SDK
consumer smoke tests now exercise copied public surfaces instead of advertising filtered
raw PE debug slots.

The lead also fixed a production checker bug in
`scripts/check_player_identity_public_contract_decision_record.py`: a validation helper
passed `blockers=` to a local `add()` wrapper whose first positional parameter is already
named `blockers`. The code now uses `checker_blockers=`, restoring decision-record
validation instead of raising `TypeError`.

Test helpers for player-identity public contract readiness, gap reporting, and decision
records now patch deterministic runtime fixture time and approved offline workspace roots.
This keeps strict runtime reports reproducible in-process while preserving fail-closed
path-drift behavior.

## Validation

Passed in this checkpoint:

- `python3 -m unittest scripts.test_report_obelisk_sdk_status` - 65 tests
- `python3 scripts/report_obelisk_sdk_status.py --compact`
- focused public SDK guardrails for raw PE public/debug boundary and ABI slot policy
- `ctest --test-dir build -R '^SdkConsumerFixture' --output-on-failure` - 99 tests
- `python3 -m unittest scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence` - 198 tests
- `python3 -m unittest scripts.test_build_player_identity_runtime_principal_lifecycle_evidence_bundle` - 122 tests
- `python3 -m unittest scripts.test_check_public_sdk_v1_completion` - 347 tests
- `python3 -m unittest scripts.test_check_command_permission_route_gate scripts.test_check_command_permission_route_gate_bound_identity_sources` - 152 tests
- `python3 -m unittest scripts.test_check_player_identity_public_header_gate scripts.test_check_player_identity_public_contract_readiness scripts.test_check_player_identity_public_contract_gap_report` - 255 tests
- `python3 -m unittest scripts.test_check_player_identity_public_contract_decision_record` - 70 tests
- focused installed/package-shape public SDK guardrails
- `python3 -m py_compile scripts/test_public_sdk_guardrails.py`
- `git diff --check`

Process check after validation showed no leftover worker/test Python process; only the
persistent Open WebUI process was present.

## Result

This is real SDK hardening progress, but not SDK completion progress. The next fastest
route remains producing a checker-accepted approved runtime principal lifecycle evidence
bundle with the exact sibling set:

1. `session_start`
2. exact `ShooterGameMode.CheckJoinInProgress(1,0)` `session_start_rejected`
3. matched `session_end`

Only after that accepted bundle exists should the player-identity public contract gate be
advanced.
