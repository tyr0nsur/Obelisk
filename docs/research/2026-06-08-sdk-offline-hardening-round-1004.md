# SDK Offline Hardening Round 1004

Date: 2026-06-08

## Scope

This note records the 10:04 CEST offline SDK hardening checkpoint. It did not touch live
ARK servers, RCON, Discord network sends/reads, `/servidor/ark`, deployment markers,
environment files, GitHub, release tags, or publication state.

The checkpoint is non-authorizing and non-evidence. It does not change the active SDK
route: `approved_runtime_evidence_missing` remains the blocker, SDK progress remains
`0/12`, P0 remains `0/4`, and runtime/public/stable readiness remain false.

## Integrated Facts

- Six delegated agents completed and were explicitly closed; no standby sub-agent
  remains.
- The multi-surface beta capture pack is now deterministic and candidate-only. Pack
  manifests use pack-relative artifact paths, exclude output-root fields from the
  manifest/hash, and reject absolute or nondeterministic manifest tampering. It still
  cannot count as runtime evidence, SDK/P0 progress, or readiness.
- The local beta bridge/notice flow now enforces one active operational message with one
  embed and unique buttons. Beta-control sends require an update-active-notice path, and
  status summaries/buttons cannot create follow-up chat messages or claim
  evidence/progress/readiness.
- The commands/replies promotion-certificate builder now requires the full upstream
  hash-bound chain: player identity, permissions/admin, and command-response promotion
  certificates. It emits canonical repo-relative `{path, sha256}` bindings while keeping
  all SDK/P0/runtime/publication progress false/zero.
- Public SDK completion hardening now rejects inline certificate-shaped bindings,
  absolute paths, `..`, non-canonical `./` paths, builder/report shortcut containers, and
  blocked/non-authorizing terminal commands/replies certificates. `command_response`
  remains an upstream surface and does not depend on the downstream terminal
  `commands_replies_promotion_certificate`; the terminal certificate is enforced on
  `obelisk.commands_replies.v1`.
- SDK status final-gate context no longer treats an inline commands/replies certificate
  payload with `input_bindings` and `input_binding_sha256` as hash-bound evidence. Only a
  canonical path+sha certificate binding satisfies `source_hash_bound`.
- Duplicate start/end lifecycle context is now selected only for diagnostics, not
  accepted as strict evidence. Selectors expose `selected=true` plus
  `selected_context_only=true`, but `accepted=false`; approved evidence remains blocked.

## Read-Only Findings Deferred

- `HandleNewPlayer(1,0)` still has C++ observer/test paths that build a rejected-start
  observation even though the strict approved runtime route accepts rejected start only
  from `ShooterGameMode.CheckJoinInProgress(1,0)`. Existing C++ budget/event-view tests
  already keep it non-canonical, but the construction path should be removed in a bounded
  runtime patch.
- Diagnostic-only C++ observations still carry accepted role labels internally for
  `K2_PostLogin` and non-strict `CheckJoinInProgress` diagnostics. They are rejected
  downstream, but a future patch should add an explicit diagnostic-only role or separate
  diagnostic observation shape.

## Validation

- `python3 -m unittest scripts.test_plan_obelisk_multi_surface_beta_capture scripts.test_prepare_obelisk_multi_surface_beta_capture_pack scripts.test_check_obelisk_multi_surface_beta_capture_pack` -> `50 OK`.
- `python3 -m unittest scripts.test_discord_beta_bridge scripts.test_check_discord_beta_bridge_plan scripts.test_prepare_player_principal_lifecycle_beta_notice` -> `72 OK`.
- `python3 -m unittest scripts.test_build_commands_replies_promotion_certificate` -> `7 OK`.
- `python3 -m unittest scripts.test_report_obelisk_sdk_status` -> `64 OK`.
- `python3 -m unittest scripts.test_copy_player_principal_lifecycle_ready_log scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence` -> `232 OK`.
- Public completion full pass executed `345` tests and exposed two stale terminal-gate
  expectations; the two corrected focused regressions now pass (`2 OK`). The completion
  CLI remains blocked as expected with SDK `0/12` and P0 `0/4`.
- `python3 scripts/report_obelisk_sdk_status.py --compact` still reports
  `approved_runtime_evidence_missing`, next
  `approved_runtime_principal_lifecycle_evidence_bundle`, after-runtime blocker
  `identity_public_contract_gate_missing`, SDK `0/12`, P0 `0/4`, runtime/public/stable
  false, approved runtime/in-game evidence false, and source overclaims `0`.
- `python3 -m py_compile` on the touched Python scripts passed.
- `git diff --check` passed.

## Next Work

The fastest unblock remains a checker-accepted copied runtime principal lifecycle sibling
set containing `session_start`, exact `ShooterGameMode.CheckJoinInProgress(1,0)`
`session_start_rejected`, and matched `session_end`.

Offline follow-up: patch the C++ observer so `HandleNewPlayer(1,0)` no longer builds a
rejected-start lifecycle observation and diagnostic-only observations cannot carry
accepted lifecycle roles.
