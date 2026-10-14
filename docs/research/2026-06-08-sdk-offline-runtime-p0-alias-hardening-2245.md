# 2026-06-08 SDK Offline Runtime/P0 Alias Hardening 2245

## Summary

Lead resumed the persistent ObeliskSDK goal and ran a six-agent offline hardening round.
The work stayed offline: no ARK server, live log, RCON, Discord send, marker/env change,
GitHub, tag, release, or publication operation occurred.

All six delegated agents were closed: Kierkegaard, Turing, Erdos, Chandrasekhar, Newton,
and Epicurus. No standby sub-agent remained after integration.

## Integrated Changes

- Runtime evidence builder/checker now reject `checkjoin`, `checkjoin-bool-order`,
  `bool-tuple`, and `copied-bool` sidecars by schema and by path alias, so offline
  rejected-start candidates cannot replace the exact copied sibling-set bundle.
- Generated runtime bundle sidecar scans now skip diagnostic `blocker_details` and
  explicit non-claim internal proof fields while still blocking positive readiness,
  authorization, public surface, and SDK/P0 aliases.
- Planner/runner current-live diagnostic context is now marked
  `source_freshness=stale_operator_supplied`, with stale blockers suppressed as context
  only; it cannot become a live action, restart instruction, evidence, or progress.
- Player identity post-runtime bridge/certificate now carries canonical
  `post_runtime_bridge_constraints`: after accepted runtime evidence the next blocker is
  still `identity_public_contract_gate_missing`, and terminal/public/package/support/P0
  aliases stay false/zero.
- Permissions/admin, command/chat-response, commands/replies, ResourceHandle, and offline
  artifact gates reject nested support-tier/package-shape, route-cleared,
  scoped-statement, terminal-certificate, runtime-status, serial-scan, flag-report,
  caller-row, and `sourceOverclaimTotal=0` shortcut aliases.

## Validation

- Runtime evidence builder/checker: 329 OK.
- Player identity post-runtime bridge/certificate/decision record: 96 OK.
- Permissions/admin/query/certificate: 205 OK.
- Command bridge/route/public readiness/certificates: 363 OK.
- ResourceHandle/offline artifact gate: 453 OK.
- Planner/runner/status: 130 OK.
- `git diff --check` on touched SDK/checker/docs paths: clean.
- `python3 scripts/report_obelisk_sdk_status.py --compact`: blocked at
  `approved_runtime_evidence_missing`, next
  `approved_runtime_principal_lifecycle_evidence_bundle`, after-runtime blocker
  `identity_public_contract_gate_missing`, SDK `0/12`, P0 `0/4`, source overclaims `0`.
- `python3 scripts/check_public_sdk_v1_completion.py --json`: blocked, scoped release
  statement bookkeeping `8/8`, `stable_claim_allowed=false`.

## Current Route

The route remains unchanged. The only next promotable input is a checker-accepted copied
runtime principal lifecycle evidence bundle containing `session_start`, exact
`ShooterGameMode.CheckJoinInProgress(1,0)` `session_start_rejected`, and matched
`session_end` in one valid sibling-set window. This checkpoint improves fail-closed
offline gates and P0 preparation, but it does not add runtime evidence, SDK progress, P0
progress, public readiness, or stable readiness.
