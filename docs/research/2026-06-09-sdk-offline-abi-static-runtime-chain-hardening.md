# 2026-06-09 SDK Offline ABI, Static, Runtime Chain Hardening

## Objective

Integrate the delegated offline SDK hardening round after the `00:37 CEST` checkpoint,
repair release-scope drift, and keep offline guardrail hardening moving while accepted
runtime lifecycle evidence is still missing.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Local time: 2026-06-09 01:36 CEST
- Live operations: none. No `/servidor/ark` write, RCON, Discord send, restart,
  marker/env change, GitHub operation, commit, tag, or release-ref operation occurred.
- Strict status after the round: `approved_runtime_evidence_missing`, next
  `approved_runtime_principal_lifecycle_evidence_bundle`, SDK `0/12`, P0 `0/4`,
  source overclaims `0`.

## Integrated Work

- Runtime evidence closure tooling now rejects lifecycle-role aliases across approved
  evidence checks, bundle preflight, ready-log copy reports, start/end-only checks, and
  status split JSON, while keeping internal observer diagnostic counters non-promoting.
- Player identity post-runtime/public-contract tooling now requires full decision-record
  artifact binding with current file SHA and canonical payload SHA; stale reviewed records
  are non-counting until regenerated after accepted runtime evidence.
- Permissions/admin, command response, and commands/replies promotion paths now require
  direct hash-bound upstream artifacts and reject package/support/beta/status/scoped
  release shortcuts.
- C ABI/package-shape examples validate copied API prefix, slot struct sizes, descriptor
  capabilities, and avoid raw `ProcessEvent`/`CallProcessEvent` public leakage.
- Dispatcher cleanup retry visibility is preserved for structure and mission copied-bool
  families; cleanup failures retain plugins for retry and do not repeat plugin shutdown.
- Offline artifact gates reject duplicate source IDs, duplicate snapshot SHAs, stale target
  revision hashes, unknown target-set aliases, and lifecycle-anchor/guidance confusion.
- Post-RC mission/transfer recognizers remain test-only: `ue/MissionReflection.cpp`,
  `ue/TransferReflection.cpp`, and `hooks/ProcessEventTransferReflection.cpp` were removed
  from the `obelisk` runtime target while their CTest targets remain available.
- `docs/public_sdk_surfaces.json` keeps mission/transfer/dino/tribe/buff lanes as planning
  with explicit non-complete exclusion wording, not release-supported SDK scope.

## Validation

- `python3 scripts/test_release_scope_guardrails.py`: `62 OK`.
- `cmake --build build --target obelisk mission_reflection_tests process_event_mission_reflection_tests transfer_reflection_tests process_event_transfer_reflection_tests -j$(nproc)`: passed; compiler emitted existing third-party fmt/spdlog warnings.
- `ctest --test-dir build --output-on-failure -R '^(MissionReflectionTests|ProcessEventMissionReflectionTests|TransferReflectionTests|ProcessEventTransferReflectionTests)$'`: `4/4` passed.
- Runtime principal lifecycle evidence/status suite: `457 OK`.
- Permissions/admin plus command response/replies suite: `633 OK`.
- Player identity post-runtime/public-contract focal script chain: passed.
- `python3 scripts/report_obelisk_sdk_status.py --compact`: blocked as expected with
  SDK `0/12`, P0 `0/4`, source overclaims `0`.
- 2026-06-09 `02:48 CEST` follow-up: `python3 scripts/test_check_public_sdk_v1_completion.py`
  passed `350 OK` after fixing scoped non-complete accounting for the planning
  `obelisk.mission_transfer_dino_tribe.v1` blocker. That surface can satisfy the
  release-statement exclusion contract as bookkeeping only, but it remains a planning
  manifest outcome gap and unresolved SDK blocker. `python3 scripts/test_build_v1_scoped_release_statement.py`
  passed `12 OK`; `python3 scripts/test_check_mission_transfer_dino_tribe_v1_outcome_accounting.py`
  passed `54 OK`; `python3 scripts/test_agent_handoff_guardrails.py` passed `24 OK`;
  `python3 scripts/test_research_doc_guardrails.py` passed `47 OK`;
  `python3 scripts/test_release_scope_guardrails.py` passed `62 OK`;
  `python3 scripts/test_report_obelisk_sdk_status.py` passed `74 OK`;
  `python3 scripts/report_obelisk_sdk_status.py --compact` remained blocked with
  SDK `0/12`, P0 `0/4`, source overclaims `0`; `git diff --check` passed.

## Result

Confirmed. The round closes more shortcut paths and fixes a runtime target scope leak, but
it does not promote public SDK readiness. The first strict blocker remains the
checker-accepted copied runtime principal lifecycle bundle with `session_start`, exact
`ShooterGameMode.CheckJoinInProgress(1,0)` `session_start_rejected`, and matched
`session_end`.

## Next Steps

- Keep offline SDK hardening moving while runtime evidence is absent.
- When beta/runtime evidence is needed, use the recorded standing authority, bot-first beta
  notice path, and RCON broadcast/timer safety rules.
- Do not change SDK/P0 counters until the approved runtime evidence checker accepts the
  copied sibling-set bundle.

## 03:15 CEST Follow-Up

No live/server/RCON/Discord/GitHub/release operation occurred. The follow-up round closed
all delegated agents; Poincare was shut down after timeout without integrated changes.

Integrated offline hardening:

- Package-shape guards now reject positive accepted-runtime, approved-runtime, contract
  review, promotion, counting, and package-publication aliases across installer, layout
  helper, installed consumer CMake, and public guardrail tests while preserving
  `Obelisk_FIND_PACKAGE_SDK_PACKAGE_SHAPE_ONLY TRUE` as the only true package-shape flag.
- Runtime lifecycle planning/status paths now classify source-present and candidate-pack
  aliases as source-only/non-evidence, and next-action aliases such as approved-in-game or
  runtime-evidence-ready stay false/non-promoting.
- The player-principal observer brief now names exact
  `ShooterGameMode.CheckJoinInProgress(1,0)` as the only approved
  `session_start_rejected` source for the copied sibling-set route.
- Standing launch authority semantics are consistent for beta notices: recorded standing
  authority satisfies the guarded beta-notice send scope for the bound request, but the
  offline executor still does not send Discord, touch ARK, change markers/env, or count
  anything as evidence/progress/readiness.
- Activation preconditions now treat negative policy fields such as
  `accepted_copied_sibling_set_required_before_runtime_claims` and
  `edit_existing_message_when_active_notice_state_present` as policy metadata, not
  forbidden positive evidence claims.

Validation:

- `python3 -m unittest scripts/test_public_sdk_guardrails.py`: `210 OK`.
- `python3 -m unittest scripts/test_check_player_principal_lifecycle_activation_preconditions.py`: `66 OK`.
- `python3 -m unittest scripts/test_prepare_player_principal_lifecycle_runtime_window_execution.py`: `27 OK`.
- `python3 -m unittest scripts/test_plan_player_principal_lifecycle_next_actions.py scripts/test_run_player_principal_lifecycle_next_actions.py scripts/test_report_player_principal_lifecycle_runtime_evidence_status.py scripts/test_prepare_player_principal_lifecycle_evidence_closure_request.py`: `164 OK`.
- `python3 -m unittest scripts/test_research_doc_guardrails.py scripts/test_agent_handoff_guardrails.py scripts/test_report_obelisk_sdk_status.py`: `146 OK`.
- `ctest --test-dir build -R '^SdkConsumerPackageShapeNonClaimGuard$' --output-on-failure`: `1/1` passed.

Result: route remains `approved_runtime_evidence_missing`; SDK `0/12`, P0 `0/4`.
