# 2026-06-08 TheIsland Player-Principal Window 171142

## Scope

Lead-owned runtime/SDK checkpoint for the current fastest unblock:
`approved_runtime_principal_lifecycle_evidence_bundle`.

This note records operational facts only. It does not claim approved runtime evidence,
runtime readiness, public SDK readiness, SDK/P0 progress, Plugin Hub readiness, or
publication authority.

## Runtime Window

- Target: `arkserver2` / `TheIsland`.
- Window: `2026-06-08T17:11:42Z` to `2026-06-08T19:11:42Z`.
- Request pack:
  `/servidor/ark/workspace-offline/live-validation-logs/20260608T171142Z-player-principal-lifecycle/`.
- Preparation report:
  `/servidor/ark/workspace-offline/live-validation-logs/20260608T170642Z-theisland-player-principal/runtime-window-execution.json`.
- Activation preconditions were checked after a stale-window false blocker was fixed:
  `ready=true`, `blockers=[]`, recorded standing authority consumable for the scoped
  sequence.
- Beta notice confirmed through the bot in channel `1513238083741683934`; the helper
  used `PATCH` against the active embed, not a webhook, with buttons enabled.
- 2026-06-08 `19:24 CEST` cleanup: moved the confirmed beta notice sidecar out of the
  exact evidence sibling-set to the report directory:
  `/servidor/ark/workspace-offline/live-validation-logs/20260608T170642Z-theisland-player-principal/beta-notice.confirmed-send.sidecar.json`.
  The evidence run directory keeps only exact sibling/request artifacts until a copied
  `Obelisk.log`, `window-manifest.env`, `preflight-post.json`, and the approved bundle
  are produced.

## Live Actions

- Before restart, TheIsland query and redacted RCON both reported `0` players.
- Refreshed only the installed LinuxGSM wrapper:
  `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh`.
  SHA after refresh matched repo wrapper:
  `2c1abbecd73409f2ad76fdbc7fbd5983d32aba9c723620efa322eeffea7b1ede`.
- `preflight-pre.json` passed in observer-window mode for the fresh sibling set.
- `SaveWorld` through RCON port `27021` returned `ok=true`.
- Restarted only `arkserver2`; Ragnarok stayed running and Genesis2 stayed off.
- Post-restart ARK processes:
  - Ragnarok `arkserver` PID `895600`, `ActiveEvent=Summer`.
  - TheIsland `arkserver2` PID `2539922`, `ActiveEvent=Summer`.
- TheIsland runtime log showed:
  - LD_PRELOAD loaded at `2026-06-08T17:12:41Z`.
  - ProcessEvent absolute x64 hook installed at `2026-06-08T17:12:44Z`.
  - plugins disabled.
  - `PlayerPrincipalLifecycleObserver` enabled at `2026-06-08T17:13:28Z` with binary
    SHA `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`,
    log limit `10`, dispatch limit `0`.
- Post-warmup one-shot at `2026-06-08T17:15:27Z` showed TheIsland query `0/70`,
  redacted RCON `0`, observer gate only, and no lifecycle events yet.

## Monitor

The unbounded passive monitor attempt was replaced with a bounded monitor:

- Timeout PID: `2542521`.
- Internal monitor PID: `2542523`.
- Session id: `theisland-window-20260608T171142Z-bounded`.
- Log: `/tmp/obelisk-passive-monitors/theisland-window-20260608T171142Z-bounded.log`.
- Snapshot root: `/tmp/obelisk-passive-evidence-snapshots`.
- Interval: `60s`.
- Linger after detection: `900s`.
- Scope: passive metadata only until copied sibling-set bundle checker accepts evidence.

## SDK Work Integrated This Round

All six delegated agents from the round were explicitly closed:

- Runtime evidence manifest builder now reports duplicate/ambiguous valid triplet context
  separately from wrong-shape rejected-start material and remains fail-closed.
- Player identity promotion certificate tests now reject stale public-contract decision
  records against the current file.
- Permissions/admin query-only fail-closed checker rejects nested progress/public aliases.
- Commands/replies readiness now delegates upstream certificate validation to the stricter
  command/chat response checker and clarifies missing non-counting artifacts.
- Public SDK/package wording changed from `foundation/contributor-readiness` to
  `foundation/contributor package-shape`, with guardrails to prevent reintroducing the
  readiness claim.
- Multi-surface beta pack now includes `mission_copied_bool` and a simultaneous redacted
  worksheet for admin/commands/dino/tribe/buff/inventory/item/transfer/mission surfaces,
  all non-counting.

## Validation

- `python3 -m unittest scripts.test_check_player_principal_lifecycle_activation_preconditions`
  passed: `66 OK`.
- `python3 scripts/report_obelisk_sdk_status.py --compact` still reports
  `approved_runtime_evidence_missing`, next
  `approved_runtime_principal_lifecycle_evidence_bundle`, after-runtime blocker
  `identity_public_contract_gate_missing`, SDK `0/12`, P0 `0/4`, source overclaims `0`.
- Current runtime-evidence status after the sidecar move:
  `status=blocked_missing_lifecycle_roles`, `invalid_sidecars=None`,
  `sidecar_validation_blockers=0`, missing roles `session_start`,
  `session_start_rejected`, and `session_end`; runner dry-run over the generated plan
  has `eligible_count=0` and `blocked_count=4`, so no bundle/copy action is available
  until the exact triplet appears.
- Sub-agent focused validations passed as reported in their closure summaries:
  runtime evidence bundle/checker/manifest suites, identity public-contract certificate
  suites, permissions/admin P0 suites, commands/replies suites, SDK guardrails/ABI CTest
  subset, and multi-surface beta pack suites.

## Next Steps

If a tester joins TheIsland during the active window, watch the bounded monitor and
`/servidor/ark/obelisk/logs/arkserver2/Obelisk.log` for:

1. `session_start` from `HandleNewPlayer(1,1)`.
2. exact `session_start_rejected` from `CheckJoinInProgress(1,0)`.
3. matched `session_end` from `OnLogout`.

Only after those appear in the same fresh sibling set should the lead run the copied-log
closure path:

- `scripts/copy_player_principal_lifecycle_ready_log.py`
- `scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py`
- `scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py`

Until the approved checker accepts that bundle, SDK/P0 progress remains `0`.
