# Current Agent Handoff

This file is an active routing table only. Durable evidence belongs in
`docs/research/`; resume facts in `COMPACT_CONTEXT.md`. Historical recovery context is
not active routing for the current head; use `git log --oneline -1` plus tag/ref
verification and a clean release gate without `--allow-dirty`. Stale tags are not
publicable and must not be reused or pushed.

## Active Objective

- Objective: finish the complete `v1.0` public SDK contract after `v0.1.0-rc.2`.
  The RC scope remains limited and is not a production-stable `v1.0` or complete SDK
  claim. `v0.1.0-rc.2` is the current published frozen core-first RC baseline, not the
  complete SDK target.
- Current post-RC focus: complete the SDK blockers after the accepted RC UFunction
  second-source root; RC public scope remains limited to `GameplayPolicyEvent`, the
  minimal copied `ChatMessageEvent`, `DescribeResourceKind`, and
  `DescribeGameplayPolicyEventKind`.
- No tag or release-ref push may occur without release-manager/lead authorization scoped
  to the current-turn; stale local tags are not publicable and are not reused or pushed.
- Complete-SDK `v1_required_dependency_chain` is promoted-only for a complete SDK
  claim: `obelisk.player_identity.v1` -> `obelisk.permissions_admin.v1` ->
  `obelisk.command_chat_response_path.v1` -> `obelisk.commands_replies.v1`.
  scoped non-complete rows are bookkeeping only.
- Strict current accounting is fail-closed: route `approved_runtime_evidence_missing`,
  next `approved_runtime_principal_lifecycle_evidence_bundle`, after-runtime blocker
  `identity_public_contract_gate_missing`, SDK `0/12`, P0 `0/4`,
  `stable_claim_allowed=false`, runtime/public/stable false, runtime readiness false.
- Fastest unblock remains approved copied runtime principal lifecycle evidence: a
  checker-accepted copied runtime principal lifecycle evidence bundle with one exact
  triplet: `session_start`, exact
  `ShooterGameMode.CheckJoinInProgress(1,0)` `session_start_rejected`, and matched
  `session_end`, all in one valid sibling-set window with safe copied fields.
- Runtime start/end-only material, passive snapshots, diagnostic complete triplets,
  route samples, public reachability, beta notices, request packs, package-shape installs,
  side-lane candidates, and status reports remain non-evidence and non-progress until the
  approved bundle checker accepts the copied sibling set.
- ResourceHandle/public GObjects remain blocked. old flag-policy artifact is obsolete;
  durable rich-provenance refresh is preserved. Consume mode accepts it and promote mode
  stays blocked; strict serial policy artifacts are candidate-only. Do not rerun broad
  FName, GObjects, or core scans for ResourceHandle. Do not replace this with another
  broad offline FName/GObjects scan. The next strict ResourceHandle blocker is rejected
  runtime object samples plus runtime serial reuse/wraparound semantics; the
  future-runtime-observation-plan still needs an operator-approved live-ops brief names
  the exact debug target. It does not unlock runtime negative samples, public lookup,
  object identity, public `ResourceHandle`, mutation, return overrides, GObjects
  promotion, persistent handles, or cross-callback lookup. post-callback rejection
  contract is preserved as candidate-only; first strict serial reuse/wraparound policy
  artifact is preserved; manifest consume mode accepts it and promote mode blocks it as
  candidate-only. Semantic helper paths remain fail-closed and do not unlock mutation.
- Item return-only policy has three copied `GameplayPolicyEvent` `ReturnValue` kinds;
  this is not a public Inventory SDK or Items SDK and does not unlock identity, mutation,
  or return override.
- Mission copied-bool observer remains internal and not ready: no public Mission SDK,
  public module SDK, ResourceHandle, identity, mutation, or return override.
  Exact candidate bool tail remains `bool_field_size=1`, `bool_byte_offset=0`,
  `byte_mask=0x01`, `field_mask=0xff`, and `native_bool=false`; Consume mode accepts it
  and promote mode blocks it.
- Transfer `bAccept` remains test-only candidate context and does not authorize Transfer
  runtime work.
- Core timers are process-local core timer primitives with owner-token registration and
  explicit unregister; they are not gameplay/module timer APIs, shared scheduler state,
  UE identity, or persistent handles.
- Plugin cleanup failure retry policy skips `dlclose`, retains the plugin for retry, and
  does not repeat plugin shutdown.
- The 12-target `players-identity-lifecycle-intake` focal set is exact and includes
  `ShooterPlayerController.ServerListPlayers` and `ShooterPlayerController.ServerKickPlayer`;
  those names do not replace runtime lifecycle proof.
- Player identity current route has complete `obelisk.core-dump-evidence-pack.v1` non-protected input, accepted `obelisk.reflection-inventory-pack.v1`, 12/12 candidate fixtures, and accepted distinct second-source layout evidence from the vanilla-gdb core; remaining blocker is approved runtime principal lifecycle evidence.
- Repo-local lifecycle-anchor and principal-invalidation manifests are consume-only planning inputs and source-bound; default route consumes those repo-local fallbacks and reports `approved_runtime_evidence_missing`. Do not rerun completed admin snapshot, second-source layout, or lifecycle layout routes. Current recipe: `docs/research/2026-05-31-player-identity-offline-pack-preflight.md`.
- ArkServerApi/AseApi and local `NextGenPlugins` clones are names and demand signals only;
  do not copy code, offsets, layouts, vtables, ABI assumptions. They are not architecture,
  ergonomics, behavior maps, porting targets, copying source, wrappers, raw UE pointer
  APIs, command parsers, return semantics, or implementations.
- Plugin Hub remains post-SDK-complete planning only.
- field-window packaging blocker evidence is not a `v1.0` SDK blocker, route shortcut, or
  completion signal. CMake package target are present as package-shape evidence only, not
  a `v1.0` completion marker. The explicit non-`EXACT` numeric version plus `COMPONENTS
  SDK` request above is part of that package-shape contract only. It is not evidence for
  stable SDK readiness, public package readiness, Plugin Hub readiness/publication,
  support-tier activation, runtime readiness, or v1 completion. Plugin Hub seeds do not
  gain priority, support tier, public SDK scope, or `v1.0` completion weight while
  complete-SDK blockers remain open. No Plugin Hub publication, intake prioritization,
  production module availability, or support-tier activation is in the current
  RC/post-RC SDK scope.

## Live Authority And Safety

- Standing operator authorization, 2026-06-06 local: applies across future turns and
  compactions until explicitly revoked. It grants persistent authority to run any runtime
  tests, live/log/process/posture checks, Obelisk marker/env changes, safe ARK instance
  starts/stops/restarts, beta-tester Discord notices, evidence capture, and debug actions
  necessary to accelerate ObeliskSDK launch; `arkserver2` / `TheIsland` explicitly
  approved. Never keep three ARK servers running; safety shorthand: never keep three ARK
  servers running, avoid raw player text/secrets, and do not claim SDK/stable/public
  readiness until gates accept. recorded standing launch authority applies; Technical
  progress alone is not runtime evidence or readiness.
- Standing-authority checkpoint, 2026-06-06 local: standing authority is preserved as
  authorization only, not evidence or readiness; specifically not runtime evidence,
  SDK/P0 progress, public/stable readiness, or general Discord permission.
- Safety limits stay attached: never keep three ARK servers running; keep ARK concurrency
  at two or fewer; avoid raw player text/secrets; broadcast/timer before strictly
  necessary restarts with connected players; keep a transfer server available when
  practical; do not restart merely to broaden logging while players are active; avoid
  repeated restarts; no publication, tag, push, Plugin Hub action, or
  SDK/stable/public-readiness claim until gates accept.
- Default live-ops rule: the recorded standing launch authority is active and persistent
  for necessary ObeliskSDK runtime evidence/debug work, but Prior passive evidence remains
  non-evidence until checkers accept a copied bundle. Operator instruction, 2026-06-04,
  is superseded by the 2026-06-06 persistent launch authority.
- Default offline/agent rounds have no `/servidor/ark` writes, must not write under
  protected live paths, and must not touch RCON, Discord, servers, markers, env, GitHub,
  commits, tags, or release refs unless that exact scope is assigned; the lead retains
  server-safety decisions.
- Historical map assignments such as `arkserver` / `Ragnarok`, `arkserver2` /
  `TheIsland`, and `arkserver3` / `Genesis2` are context only and must be reconfirmed
  before live action. Latest operator-directed posture, 2026-06-08 `23:55 CEST`: only
  Ragnarok `arkserver` remains running; TheIsland `arkserver2` was stopped after query
  showed `0/70`, and no third ARK server was running. Keep this one-server posture unless
  current evidence work requires a scoped change.
- Discord policy: no Discord for internal rounds or agent status. Public modder-facing
  milestones require approved scope, guarded embed shape, dry-run first, and
  `OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL`. Beta-test coordination is bot-first in channel
  `1513238083741683934`; use
  `scripts/discord_beta_bridge.py --send-beta-notice`. `OBELISK_BETA_TEST_WEBHOOK_URL`
  is deprecated for real beta sends but kept as a guarded compatibility variable; no
  routine validation, speculative notes, raw player text, or secrets. Always dry-run before any approved send.
- Request-pack/preflight/window-manifest/operator-receipt/sidecar readiness, planning
  acceptance, or route acceptance do not authorize runtime work, runtime capture, public
  SDK readiness, or runtime readiness; they remain non-evidence until the
  checker-accepted copied sibling set exists.

## Latest Development State

- 2026-06-09 `03:15 CEST`: Offline SDK hardening continuation. All six delegated agents
  from this round are closed; Poincare was shut down after timeout with no lead
  integration. No live/server/RCON/Discord/GitHub/release operation occurred. Integrated
  package-shape accepted-runtime/contract alias guards, lifecycle next-action/runtime
  evidence alias hardening, exact CheckJoin observer-brief guardrail, standing beta-notice
  authority semantics, activation false-positive policy fixes, and public guardrail text
  alignment. Validation: public guardrails `210 OK`, activation preconditions `66 OK`,
  runtime-window executor `27 OK`, lifecycle/status pack `164 OK`, handoff/research/status
  `146 OK`, CTest package-shape guard `1/1`, plus prior plan/runner/beta/research focal
  tests in this round. SDK route still `approved_runtime_evidence_missing`, SDK `0/12`,
  P0 `0/4`.
- 2026-06-09 `01:36 CEST`: SDK offline ABI/static/runtime-chain checkpoint. All current
  agents A-F are closed; no standby remains. No live/server/RCON/Discord/GitHub/release
  operation occurred. Integrated runtime evidence alias hardening, identity public-contract
  artifact binding, permissions/admin and command-chain certificate hardening,
  ABI/package example guardrails, dispatcher cleanup retry visibility, offline artifact
  gates, release-scope docs, and post-RC mission/transfer runtime-target exclusion.
  Validation: release scope `62 OK`, runtime evidence `457 OK`, permissions/commands
  `633 OK`, CTest `4/4`, status compact blocked with SDK `0/12`, P0 `0/4`, source
  overclaims `0`. Detail:
  `docs/research/2026-06-09-sdk-offline-abi-static-runtime-chain-hardening.md`.
- 2026-06-09 `00:37 CEST`: Prior post-compaction runtime/command/beta hardening is
  recorded in `COMPACT_CONTEXT.md`; no live/server/RCON/Discord/release operation
  occurred and route stayed `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`.
- Earlier 2026-06-08 SDK checkpoints are compacted in `COMPACT_CONTEXT.md` and indexed
  under `docs/research/`; all referenced agents were closed or explicitly shut down.
- `CallProcessEvent` remains an init-window debug escape hatch only: the current plugin
  owner is inside `ObeliskPlugin_Init`, requires
  `OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT`, Post-init calls through captured API
  tables are unsupported, and any future replacement must carry an owner token ABI.

## Legacy Guardrail Anchors

- Earlier 2026-06-04/05 supervised offline rounds are summarized in `COMPACT_CONTEXT.md`
  and are non-authorizing. They preserve route `approved_runtime_evidence_missing`,
  SDK `0/12`, P0 `0/4`, and historical passive material only.
- Historical lead round, 2026-06-05 local `08:06 CEST`: all six spawned agents were closed; Carver/Erdos/Planck/Halley/Laplace completed and Boyle was shut down after timeout, so no standby sub-agent remains.
  Non-promoting findings: timestamped copied lifecycle log lines; public/P0 gates reject reviewed/current identity contract aliases; lifecycle runtime rejects unknown invalidation reason bits; RC assembly is minimal/structure/chat only; stale `--item-return-root` rejected; side-lane/offline gates reject readiness/counting/accounting aliases; completion scanner no longer flags its own negative/non-claim disclaimers.
  Validation: evidence/window suite 411 OK, public contract/header/route suite 427 OK, reflection/side-lane focal 518 OK, worker rerun 705 OK, release-options/posture/wrapper/install tests passed, release scope 63 OK, C++ lifecycle build plus CTest 4/4 passed, runtime guardrail 20 OK, public SDK completion suite 301 OK.
  Result: blocker `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`; Ragnarok remains diagnostic/non-evidence; Genesis2 still lacks `session_end`; no complete in-game evidence is approved yet; No live server/log/`/servidor/ark` changes from that round.
- Historical passive snapshot anchor remains non-evidence.
- Historical TheIsland evidence round and passive monitor/snapshot anchor remain
  non-evidence:
  `/tmp/obelisk-passive-evidence-snapshots/passive-manual-20260604T085119Z-arkserver+arkserver2-3215640/manifest.json`,
  `captured_at_utc=2026-06-04T08:51:19Z`, script PID `3261082`,
  `/tmp/obelisk_passive_player_monitor_arkserver_arkserver2.log`, snapshots under
  `/tmp/obelisk-passive-evidence-snapshots`; `scripts/monitor_ark_player_presence_passive.sh`
  can write `/tmp/obelisk_passive_player_monitor_arkserver_arkserver3.log` and snapshots
  after `players=1+` are review-only until a future scoped marker/server change.
  Ragnarok `accepted=0`, `rejected=0`, `diagnostic_candidates=17`, target_counts
  `HandleNewPlayer=7`, `OnLogout=5`,
  `CheckJoinInProgress=2`, `K2_PostLogin=3`, mismatches `HandleNewPlayer=4`,
  `OnLogout=3`, TheIsland `accepted=0`, `rejected=0`, `diagnostic_candidates=0`,
  `ready=false`, `approved_runtime_evidence=false`, `passive_snapshot_non_evidence`;
  approved-evidence checker rejects it.
- Diagnostic/passive material remains non-evidence. Genesis2 public query now works, but
  public reachability still does not change SDK route or readiness.
- P0 runtime evidence: recorded 2026-06-06 standing launch authority or exact scoped
  current-turn approval can authorize runtime work, but Plain offline sub-agents without
  that delegated scope must not continue passive observation, read live logs, touch
  `/servidor/ark`, or perform any server/log read, marker/env change, or runtime capture.
  Preserve the historical TheIsland copied `Obelisk.log` and existing request files; a
  valid sibling set still requires `window-request.json`, `observer-window.env`,
  `operator-approval-request.md`, `operator-approval-receipt.json`, `preflight-pre.json`,
  `preflight-post.json`, `window-manifest.env`, copied `Obelisk.log`, and
  `approved-runtime-principal-lifecycle-evidence.json`. Diagnostic candidate lines,
  passive player presence, and public-query results are non-evidence; but do not call it
  approved. Accepted evidence now requires real `session_start`,
  `session_start_rejected`, and `session_end` lines with safe `apply_status` and
  `correlation_status` proof.
- P0 public contract: remains blocked behind the runtime evidence route above.

## Priority Next Steps

- Keep working offline on SDK surfaces while runtime evidence is missing; prepare multiple
  evidence lanes but do not relax the `CheckJoinInProgress(1,0)` triplet contract.
- If runtime deployment of the route sampler becomes necessary, use only a diagnostics
  debug window: diagnostics envs make copied logs non-promotable for approved evidence.
- When beta players are useful, use the bot-first Discord beta path and RCON broadcasts
  only under the recorded authority/safety limits. Keep at most two ARK servers running.
- After any candidate triplet, copy and check the complete sibling set before changing
  SDK/P0 counters.

## Agent Protocol

- Memory-loss/compaction recovery flow: treat memory loss, context compaction, reboot, or
  a resumed Codex session as a recovery event, not as revocation of recorded standing
  authority.
- Before delegating, give sub-agents scoped tasks with allowed paths, required skills,
  expert role, expected decision, current stable baseline, and safety limits. Do not pass
  unrelated history. Share only the skills and context required for that sub-agent's
  expert role and expected decision.
- delegated results become active routing only after lead integration.
- Close completed or obsolete sub-agent work before finishing; no standby sub-agent should
  remain after an integration round.
- GitHub work may be delegated only for an evidenced, stable milestone; publication still
  requires explicit scope.
- Keep changes scoped, use `rg` first, avoid secrets/player identity in docs or output,
  and record reusable facts in research notes or compact handoff.
