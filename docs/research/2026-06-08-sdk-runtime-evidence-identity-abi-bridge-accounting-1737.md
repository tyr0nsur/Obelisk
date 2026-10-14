# SDK Runtime Evidence, Identity, ABI, Bridge, And Accounting 1737

## Objective

Continue the supervised ObeliskSDK push toward a production-stable public SDK without
waiting on beta testers. The round focused on tightening the evidence-consumption path,
post-runtime identity public-contract gate, C ABI/public consumer non-claims, beta tester
bridge behavior, lifecycle exactness, and completion accounting.

## Environment

- Date: 2026-06-08 `17:37 CEST`.
- Workspace: `/home/flowcommunity-ark/Obelisk`.
- Live posture read: exactly two ARK server processes were observed, `arkserver2` /
  TheIsland and `arkserver` / Ragnarok, both with `ActiveEvent=Summer`; no third ARK
  server was running.
- Operational cleanup: a stale duplicate timed Discord bridge process was terminated,
  leaving one persistent `scripts/discord_beta_bridge.py --env-file local/discord-bot.env
  --run` process. No Discord message was sent.
- No ARK restart, RCON broadcast, marker/env change, deploy, GitHub operation, tag,
  release, or publication operation occurred.

## Integrated Work

- Runtime evidence bundle hardening:
  - `runtime-observer-summary.json` inside `approved-bundle/` is no longer accepted on
    schema alone.
  - Generated summary sidecars must bind to the current copied `Obelisk.log` path and
    SHA256.
  - Builder preflight passes the expected copied-log path into sidecar validation, so
    stale summaries block preflight.
- Player identity public-contract gate:
  - Missing `source_artifacts.*.sha256` now reports explicit
    `source_artifact_sha256_missing`.
  - Freshness mismatches include missing/invalid hash reasons and expected current repo
    hash when available.
- C ABI / SDK consumer boundary:
  - `CallProcessEvent` is documented/tested as a compatibility/debug slot, not public SDK
    readiness or stable availability.
  - ABI/package/installed-consumer guards reject raw `ProcessEvent`, public
    `CallProcessEvent`, identity, lookup, and readiness aliases.
- C++ lifecycle exactness:
  - Apply validation stamps now bind to an exact copied-observation fingerprint including
    role/action, function/outer FName indices, bool fields/values, redacted fields, and
    process-local subject tokens.
  - Dispatch/log gates validate the stamp against the supplied observation, preventing
    replay with a mutated observation or different copied subject token.
- Discord beta bridge:
  - Button interactions are local metadata only: redacted local events or local summary,
    ephemeral acknowledgements, no channel messages, no Discord reads/sends, no evidence
    or progress claims.
  - Standing authority remains sufficient for guarded beta notice send scope when the
    request is current/sendable, while broad `discord_authorized`, SDK progress, runtime
    evidence, and readiness remain false.
- Completion/status accounting:
  - Added fail-closed handling for `route_ready`, blocker cleared/resolved aliases,
    `side_lane_promoted`, `structure_build_policy_ready`, and active-notice
    sent/ready/accepted/counting aliases.
  - Legitimate `structure_build_policy_offline_intake.ready=true` remains non-counting
    when `planning_only=true` and `blockers=[]`.

## Runtime Evidence Observation

Passive monitor material from the current logs remains non-evidence. The latest passive
tail showed partial lifecycle material only: accepted `CheckJoinInProgress(1,0)`
rejected-start clues and unresolved logout material, but no complete accepted
`session_start` + `session_start_rejected` + matched `session_end` sibling-set evidence.
No SDK/P0 counter was changed.

## Validation

- `python3 -m py_compile` on touched Python scripts: passed.
- C++/ABI build and focused CTest:
  - PlayerPrincipal/ProcessEvent lifecycle plus ABI/package guard targets: `8/8` passed.
- Beta bridge:
  - `python3 -m unittest scripts.test_discord_beta_bridge scripts.test_check_discord_beta_bridge_plan scripts.test_prepare_player_principal_lifecycle_beta_notice`
  - `82 OK`.
- Player identity public contract:
  - decision record, readiness, gap report, builder, and contract decisions tests:
  - `283 OK`.
- Runtime evidence bundle and approved-evidence checker:
  - bundle builder `125 OK`;
  - approved evidence checker `201 OK`.
- SDK status/completion/scoped release:
  - `python3 -m unittest scripts.test_report_obelisk_sdk_status scripts.test_check_public_sdk_v1_completion scripts.test_build_v1_scoped_release_statement`
  - `431 OK`.
- Final compact status:
  - route `approved_runtime_evidence_missing`;
  - next `approved_runtime_principal_lifecycle_evidence_bundle`;
  - after-runtime blocker `identity_public_contract_gate_missing`;
  - SDK `0/12`, P0 `0/4`;
  - runtime/public/stable false;
  - source overclaims `0`.
- Final completion JSON:
  - `ready=false`, `complete_sdk_ready=false`;
  - `structure_build_policy_offline_intake.blockers=[]`;
  - `structure_build_policy_offline_intake.ready=true`;
  - `structure_build_policy_offline_intake.planning_only=true`.
- `git diff --check`: clean.

## Non-Claims

- This round does not provide approved runtime evidence, approved in-game evidence, SDK
  progress, P0 progress, runtime readiness, public SDK readiness, stable SDK readiness,
  Plugin Hub readiness, publication authority, or release authority.
- Standing authority and beta bridge operation remain authorization/communication only.
- Passive monitor clues, active notice state, side-lane readiness, package shape, copied
  log presence, and scoped release statements remain non-counting.

## Next Steps

- Keep the runtime evidence window ready for a real copied sibling set with
  `session_start`, exact `CheckJoinInProgress(1,0)` `session_start_rejected`, and matched
  `session_end`.
- When beta testers are available, use the single persistent bot bridge and guarded
  beta-notice path; keep ARK concurrency at two servers or fewer.
- After an accepted runtime evidence bundle, move immediately to the hash-bound player
  identity public-contract gate, then permissions/admin, command response, and
  commands/replies promotion certificates.
