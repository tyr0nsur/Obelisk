# 2026-06-08 SDK Offline Terminal Gate Runtime Watch 1932

## Scope

Lead-owned ObeliskSDK checkpoint while the standing-authorized TheIsland runtime window
waits for player-principal lifecycle evidence.

This note does not claim approved runtime evidence, runtime readiness, public SDK
readiness, SDK/P0 progress, Plugin Hub readiness, or publication authority.

## Runtime Watch

- Active runtime lane remains `arkserver2` / `TheIsland`, run id
  `20260608T171142Z-player-principal-lifecycle`.
- Monitor is bounded and still active at 2026-06-08 `19:32 CEST`: timeout PID `2542521`,
  inner PID `2542523`.
- Latest checked ticks show TheIsland query/RCON `0` players and observer gate only.
- No approved lifecycle events have appeared yet. Missing roles remain `session_start`,
  `session_start_rejected`, and `session_end`.
- The exact evidence run directory remains clean after moving the non-evidence beta notice
  sidecar to the report directory.

## Agents

Four agents were spawned for the post-runtime P0 chain and then all closed:

- Carson: player-identity post-runtime gate, shut down without integration.
- Anscombe: permissions/admin gate, shut down without integration.
- Sagan: command/chat response gate, shut down without integration.
- Galileo: commands/replies terminal gate, completed and then closed.

Galileo's first lead rerun was treated as suspect while the workspace was still being
checked. The final isolated lead rerun passed, so the terminal commands/replies changes
are accepted as integrated for this checkpoint.

## Commands/Replies Gate

Integrated behavior:

- Terminal commands/replies accounting now requires an exact hash-bound
  `commands_replies_promotion_certificate`.
- That certificate must bind to the current hash-bound
  `command_response_promotion_certificate`.
- Inline, extra-key, package-shape, status, beta, and offline shortcut-shaped bindings are
  rejected.
- Diagnostics name `commands_replies_promotion_certificate` as the first missing terminal
  artifact, with zero SDK/P0 contribution.

## Validation

- `python3 -m unittest scripts.test_check_commands_replies_public_readiness scripts.test_build_commands_replies_promotion_certificate`
  passed: `121 OK`.
- Focused completion terminal-certificate tests passed: `5 OK`.
- `python3 scripts/check_command_permission_route_gate.py --json` reported
  `accepted_for_planning=true`, blockers `0`.
- `python3 scripts/report_obelisk_sdk_status.py --compact` still reports
  `approved_runtime_evidence_missing`, next
  `approved_runtime_principal_lifecycle_evidence_bundle`, after-runtime blocker
  `identity_public_contract_gate_missing`, SDK `0/12`, P0 `0/4`, source overclaims `0`.

## Non-Claims

This checkpoint hardens the terminal P0 gate only. It does not advance SDK/P0 counters
and does not change the runtime evidence blocker.
