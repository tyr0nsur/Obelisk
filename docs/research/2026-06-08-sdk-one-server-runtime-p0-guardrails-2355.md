# 2026-06-08 SDK One-Server Runtime/P0 Guardrails 2355

## Summary

Lead integrated a six-agent ObeliskSDK round and a local runtime-evidence checker patch.
The work stayed focused on SDK guardrails except for the operator-requested live posture
change to free RAM: `arkserver2` / TheIsland was stopped, leaving `arkserver` / Ragnarok
as the only ARK server process. This live posture change is operational only and is not
runtime evidence, SDK/P0 progress, public readiness, or stable readiness.

## Live Posture Change

- Before stop, local A2S query showed Ragnarok `players=1/70` and TheIsland `players=0/70`.
- The first `/servidor/ark/arkserver2 stop` hit LinuxGSM `tmuxception`.
- The accepted stop command was `env -u TMUX /servidor/ark/arkserver2 stop`.
- After stop, `pgrep -af 'ShooterGameServer|arkserver'` showed only the Ragnarok
  `arkserver` tmux/session and ShooterGameServer process.
- A follow-up local query showed Ragnarok reachable and TheIsland query timed out.

No RCON broadcast was sent because the stopped server had zero queried players. Ragnarok
was not restarted or modified.

## Integrated SDK Changes

- Approved runtime lifecycle checker output now explicitly reports zero SDK/P0 promotion
  from a checker-accepted runtime evidence bundle:
  `sdk_surfaces_promoted_by_this_checker=0`,
  `p0_surfaces_promoted_by_this_checker=0`,
  `accepted_runtime_evidence_counts_as_sdk_progress=false`,
  `accepted_runtime_evidence_counts_as_p0_progress=false`, and
  `post_runtime_contract_gate=identity_public_contract_gate_missing`.
- Runtime evidence bundle sidecar checks allow only that exact post-runtime-gate
  non-promotion field while preserving readiness/contract-review alias rejection.
- SDK inventory audit example now requires resource-kind descriptor capability plus
  category-only/no-identity/no-lookup descriptor flags before registering copied inventory
  policy callbacks.
- Mission/transfer/dino/tribe/buff accounting rejects numeric/progress aliases such as
  `publicSdkCount`, `completeSdkClaimCount`, and public/complete SDK progress ratios.
- Item return-only readiness recursively scans value text for public SDK/API/ABI,
  runtime, P0, package-shape, Plugin Hub, identity, lookup, mutation, return-override,
  and `ResourceHandle` claims.
- Dispatcher cleanup retry queues reserve output storage before clearing fallback state,
  preserving retry state on allocation failure before `PluginManager` can retain the
  plugin for another unload attempt.
- Offline artifact gate now requires exact named redacted UFunction target-set coverage
  metadata and rejects duplicate `generated_from.input_snapshots[].id` values.
- Public status/release docs now explicitly state standing live authority is
  authorization only, not evidence/progress/readiness; completion tests now treat scoped
  release statement `8/8` as bookkeeping-valid while global SDK remains blocked.

## Delegation Closure

All six agents were closed:

- Harvey: SDK ABI/example guardrail.
- Sartre: side-lane accounting.
- Dewey: inventory/item/transfer readiness.
- Herschel: runtime core dispatcher cleanup.
- Mill: static/reversing artifact gate.
- Goodall: status/release accounting docs.

No standby sub-agent remains.

## Validation

- `python3 scripts/test_check_player_identity_runtime_principal_lifecycle_approved_evidence.py`
  -> 202 tests OK.
- `python3 scripts/test_build_player_identity_runtime_principal_lifecycle_evidence_bundle.py`
  -> 127 tests OK.
- `python3 scripts/test_check_public_sdk_v1_completion.py` -> 350 tests OK.
- `python3 scripts/report_obelisk_sdk_status.py --compact`:
  `approved_runtime_evidence_missing`, next
  `approved_runtime_principal_lifecycle_evidence_bundle`, after-runtime blocker
  `identity_public_contract_gate_missing`, SDK `0/12`, P0 `0/4`, source overclaims `0`.
- `python3 scripts/check_public_sdk_v1_completion.py --json`:
  `ready=false`, `status=blocked`, current blocker
  `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, scoped `8/8`,
  `stable_claim_allowed=false`.
- `git diff --check` clean.

## Current Route

The fastest unblock remains a checker-accepted copied runtime principal lifecycle
evidence bundle containing one exact sibling-set triplet: `session_start`, exact
`ShooterGameMode.CheckJoinInProgress(1,0)` `session_start_rejected`, and matched
`session_end`. The one-server Ragnarok posture may collect future player evidence only
if the deployed observer/gates match the approved evidence route and the copied sibling
set passes the checker chain.
