# Current Agent Handoff
This file is an active routing table only. Durable evidence belongs in
`docs/research/`, resume facts in `COMPACT_CONTEXT.md`, and old detail in
`HISTORY-*.md`. Historical recovery context is not active routing; use
`git log --oneline -1` for the checkpoint.

## Active Objective
- Published baseline: `v0.1.0-rc.2` is the current published core-first RC baseline after
  a clean release gate and exact tag/ref verification, not a production-stable `v1.0` or
  complete SDK claim. Stale tags must not be reused. RC public scope remains limited to
  promoted copied `GameplayPolicyEvent`, minimal copied `ChatMessageEvent`,
  `DescribeResourceKind`, and `DescribeGameplayPolicyEventKind`; core scope also includes
  process-local timers.
- Current post-RC focus: a complete `v1.0` public SDK contract for plugin authors. The
  complete v1 claim is blocked; do not use complete/full/production/stable SDK wording
  unless `scripts/check_public_sdk_v1_completion.py --json` allows it. The accepted RC
  UFunction second-source root remains release-scope evidence only.
- Active P0 spine:
  `docs/public_sdk_surfaces.json::v1_required_dependency_chain` is promoted-only for a
  complete SDK claim and currently ordered as `obelisk.player_identity.v1` ->
  `obelisk.permissions_admin.v1` -> `obelisk.command_chat_response_path.v1` ->
  `obelisk.commands_replies.v1`. Excluded/post-v1 results are scoped non-complete
  bookkeeping only.
- Current accounting: SDK completion remains fail-closed with complete-SDK progress
  `0/12`, P0 promoted count `0/4`, and `stable_claim_allowed=false`.
- Current identity status: repo-local lifecycle-anchor planning manifests are source-bound
  to the durable static report
  `docs/research/player-identity-planning-sources/players-lifecycle-anchor-static-report.json`
  SHA256 `03acc0573b680d3e0b19937b30cc73028c5fd833e3796fe839006941b8779cf4`.
  Default routing now reports `approved_runtime_evidence_missing`, with
  `promotion_ready=false`, `public_sdk_ready=false`, and `runtime_ready=false`. After
  accepted approved runtime evidence, the only allowed later route blocker is
  `identity_public_contract_gate_missing`, still locked and planning-only.
- Latest runtime attempt:
  `20260603T233330Z-player-principal-lifecycle` on approved `arkserver2` / `TheIsland`
  produced a valid operational manifest and stable rollback but no approved runtime
  evidence; no player/client was available, so the analyzer reported
  `player_principal_lifecycle: no_accepted_or_rejected_observer_lines`. Route remains
  `approved_runtime_evidence_missing`; see
  `docs/research/2026-06-04-arkserver2-runtime-sdk-fast-path.md`.
- Live-ops correction, 2026-06-04: do not chain short observer windows with restarts while
  waiting for organic players. Use passive presence detection via
  `scripts/monitor_ark_player_presence_passive.sh`; it must not call LinuxGSM `monitor`,
  start, stop, restart, or edit markers. Details are in `COMPACT_CONTEXT.md` and the
  2026-06-04 fast-path research note.

## Hard Overrides
- GitHub work may be delegated only for an evidenced, stable milestone. No tag or
  release-ref push has release-manager/lead authorization for this current-turn; this
  handoff does not authorize push, tag, release-ref updates, rebase, or routine publication.
- Operator approval update, 2026-06-04: `arkserver2` / `TheIsland` and, if needed,
  `arkserver` / `Ragnarok` are explicitly approved debug/development targets for the
  player-principal lifecycle evidence window needed to clear
  `approved_runtime_evidence_missing`. No server target has standing approval outside
  this target-specific scope. Technical progress is only a reason to request a scoped run
  unless current operator approval names the exact target and operation. Before each
  server-backed run, record exact marker/env changes, restart window, rollback plan,
  evidence paths, and final stable posture; this does not allow broad ProcessEvent
  tracing, raw player/gameplay payload logging, ReflectionScanner/native-exec/ptrace/
  gcore/Frida/rr, Discord, publication, or SDK readiness claims unless separately scoped.
- Request-pack/preflight/window-manifest/operator-receipt/sidecar readiness, planning
  acceptance, or route acceptance are operational preparation only; they do not authorize
  runtime work, public identity readiness, public ABI readiness, public SDK readiness, release readiness, command router,
  reply/send-chat ABI, marker/env changes, runtime capture, Discord, or v1 completion.
- Default agent/offline rounds remain no `/servidor/ark` writes and must not write under
  protected live paths unless the current operator-approved scoped run names the exact
  target, paths, operations, and rollback.
- While waiting for player presence, do not start a new player-principal lifecycle window
  solely on a timer. Use passive presence detection first; never use LinuxGSM `monitor`
  because it may restart a server after query failure.
- The lead retains server-safety decisions.
- no Discord for internal rounds or agent status. Public modder-facing milestones and
  beta-test notices require explicit current-turn approval, the guarded helper, embed
  shape, and dry-run first. Use only `OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL` or
  `OBELISK_BETA_TEST_WEBHOOK_URL` by variable name. Always dry-run before any approved send.
  No Discord for routine validation, speculative reversing notes, private live-ops detail,
  raw player text, or secrets.
- ArkServerApi/AseApi and local `NextGenPlugins` clones are names and demand signals only:
  do not copy code, offsets, layouts, vtables, ABI assumptions, architecture, ergonomics,
  behavior, wrappers, raw UE pointer APIs, command parsers, return semantics, or source
  implementations; not architecture, behavior maps, porting targets, copying source, or
  implementations.
- Runtime posture is default-deny for filtered/global raw `ProcessEvent`, public
  `CallProcessEvent`, ProcessEvent blocking, broad tracing, scanner/debug controls, and
  observers unless an approved env+marker pair exists for a scoped debug window.
- `CallProcessEvent` remains an init-window debug escape hatch only: the current plugin
  owner is inside `ObeliskPlugin_Init`, has `OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT`,
  and the live env+marker gate is active. Post-init calls through captured API tables are
  unsupported; any future replacement must carry an owner token ABI.
- Plugin Hub remains post-SDK-complete planning only; package-shape notes and examples do
  not replace the active SDK blocker chain or count toward `v1.0` completion.
- ResourceHandle/public GObjects remain blocked: old flag-policy artifact is obsolete,
  durable rich-provenance refresh is preserved, Consume mode accepts it and promote mode
  stays blocked. Strict serial policy artifacts remain candidate-only; the first strict
  serial reuse/wraparound policy artifact is preserved, manifest consume mode accepts it
  and promote mode blocks it as candidate-only, and post-callback rejection contract is
  preserved as candidate-only. It does not unlock runtime negative samples, public lookup,
  object identity, public lookup safety, or public ResourceHandle readiness. The next
  strict ResourceHandle blocker is rejected runtime object samples plus runtime serial
  reuse/wraparound semantics; future-runtime-observation-plan requires an
  operator-approved live-ops brief names the exact debug target. Do not rerun broad FName,
  GObjects, or core scans for ResourceHandle. Do not replace this with another broad
  offline FName/GObjects scan.

## Current Routing Facts
- `scripts/check_command_permission_route_gate.py --json` is the canonical offline route
  posture check for identity/principal -> permissions/admin -> command response ->
  commands/replies. Passing it means planning-only alignment, not public ABI, runtime
  readiness, command router readiness, reply/send-chat ABI, or v1 completion.
- The default route currently reports `valid=true`, `planning_only=true`,
  `promotion_ready=false`, and current blocker `approved_runtime_evidence_missing`.
- `scripts/build_player_identity_planning_source_manifests.py --output-dir
  docs/research/player-identity-planning-sources` emits planning-only
  `players-identity-first-evidence.json`,
  `players-identity-lifecycle-anchor-candidates.json`, and
  `players-identity-principal-invalidation-policy.json`. Accepted lifecycle anchors
  `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout` are
  `static_accepted` and cite static report SHA256
  `03acc0573b680d3e0b19937b30cc73028c5fd833e3796fe839006941b8779cf4`. Runtime/server
  authorization is now approved only for the scoped `arkserver2` / `TheIsland` debug
  target described in Hard Overrides. Route-lock expectation:
  `approved_runtime_evidence_missing` keeps
  `blocked_until=[approved_runtime_principal_lifecycle_evidence,
  reviewed_identity_public_contract]`.
- Current offline identity recipe remains
  `docs/research/2026-05-31-player-identity-offline-pack-preflight.md`; repo-local
  lifecycle/principal manifests are consume-only and the remaining blocker is approved
  runtime principal lifecycle evidence. Do not rerun completed admin snapshot,
  second-source layout, or lifecycle layout routes.
- Player identity first evidence uses the 12-target `players-identity-lifecycle-intake`
  planning set. `ShooterPlayerController.ServerListPlayers` and
  `ShooterPlayerController.ServerKickPlayer` are exact required admin targets in that set,
  but they are not accepted lifecycle anchors. Current accepted planning anchors for the
  bound route are `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout`.
- The next P0 runtime-side blocker is approved copied runtime principal lifecycle
  evidence. No approved copied runtime principal lifecycle evidence exists yet. The
  approved runtime target for producing it is `arkserver2` on `TheIsland`; `arkserver` on
  `Ragnarok` is also operator-approved for necessary debug/development evidence work.
  Preserve the single-module copied-log evidence route and the stable-posture rollback
  checks. Do not repeat short restart windows while waiting for player activity.
- Permissions/admin remains query-only planning until promoted copied identity/principal
  semantics exist. Command response and commands/replies remain blocked by identity and
  permissions/admin.
- Post-RC side-lane order: Item return-only policy, Mission copied-bool observer, then
  Transfer `bAccept`; this is not RC public SDK/API and does not change the RC public API.
  Item return-only public shape is exactly three `GameplayPolicyEvent` `ReturnValue`
  kinds; no separate public Inventory SDK or Items SDK, identity, mutation, return
  override. Mission consume mode accepts exact bool-tail `bool_field_size=1`,
  `bool_byte_offset=0`, `byte_mask=0x01`, `field_mask=0xff`, and `native_bool=false`;
  promote mode blocks. Transfer planning does not authorize Transfer runtime work.
- Structure census is explicitly `excluded`/non-counting for scoped v1 accounting;
  Structure build-policy remains offline/planning-only. Mission/Transfer/Dino/Tribe,
  ResourceHandle, economy/storage/operator ingress, and gameplay tick remain planning,
  post-v1, or blocked unless a future route explicitly promotes them with evidence.

## Priority Next Steps
- P0 identity: use `scripts/build_player_identity_planning_source_manifests.py` when a
  bound route proof is needed, then run
  `scripts/check_command_permission_route_gate_bound_identity_sources.py`. The default
  no-runtime-evidence proof should report `approved_runtime_evidence_missing`. If accepted
  approved runtime evidence is supplied to the route, confirm
  `identity_public_contract_gate_missing` and keep all unlock/readiness flags false.
- P0 runtime evidence: run the next scoped live-ops brief on approved target `arkserver2`
  / `TheIsland` to produce copied runtime principal lifecycle evidence. The run must keep
  plugins disabled, use the player-principal lifecycle observer only, set dispatch limit
  `0`, use log limit exactly `10` for the first approved evidence, reject residual
  observer/debug/scanner/callback markers, and preserve the sibling set
  `window-request.json`, `observer-window.env`, `operator-approval-request.md`,
  completed `operator-approval-receipt.json`, `preflight-pre.json`,
  `preflight-post.json`, `window-manifest.env`, and copied `Obelisk.log`. Receipts count
  only for post-window replay; preserve rollback delta, post-run stable posture, and
  no-public/no-promotion/no-v1-completion semantics.
  Startup alone is insufficient: accepted evidence requires real lifecycle activity that
  logs `session_start`, `session_start_rejected`, and `session_end` observer events.
- P0 public contract: after approved runtime principal lifecycle evidence exists, the
  next blocker is `identity_public_contract_gate_missing`; review the player identity
  contract before permissions/admin, command response, or commands/replies ABI. The
  offline `privacy.identifier_redaction` evidence artifact at
  `docs/research/2026-06-02-player-identity-identifier-redaction-evidence.json` passes
  contract-review-only intake; it cannot promote identity, unlock public SDK/runtime/header
  readiness, or satisfy the complete SDK claim.
- Runtime/ABI hardening: cleanup failure skips `dlclose`, retains the plugin for retry,
  and does not repeat plugin shutdown. Copied-event `DestroyUserData` owner-cleanup
  failures are now retry-stable across chat, structure, inventory policy, item return, and
  player-principal dispatchers. owner-token process-local core timer explicit unregister
  remains distinct from gameplay/module timer, shared scheduler state, UE identity, and
  persistent handles; see
  `docs/research/2026-06-02-copied-event-destroy-userdata-retry-stability.md`.
- Side lanes: Mission/Transfer/Dino/Tribe/Buff leaf accounting remains internal/not ready
  and enforced by `check_mission_transfer_dino_tribe_v1_outcome_accounting.py`; no public
  module SDK, ResourceHandle, mutation, runtime, ABI, callbacks, or v1 completion.
- P0 guardrail: permissions/admin structured promotion now requires a matching
  player-identity promotion certificate for `obelisk.player_identity.v1`, chain position
  1, and a reviewed artifact hash before permissions/admin structured evidence can
  count. Missing, mismatched, or stale certificates keep permissions/admin non-counting.

## Agent Protocol
- Delegated sub-agents get only the scoped objective, safety baseline, allowed paths,
  required skills, expert role, expected decision, and edit permission needed for their
  task. Pass only the skills needed for that scope.
- Do not pass leader-only cadence, active-goal framing, community policy, or unrelated
  module history unless it changes the worker's concrete task.
- Sub-agents must not commit, amend, rebase, tag, push, update GitHub state, touch
  servers, send Discord updates, or broaden live-ops scope unless explicitly delegated for
  the current turn.
- Sub-agents are not alone in the codebase: do not revert unrelated changes; leave edits
  unstaged/uncommitted and report touched paths, validations, and risks.
- Lead handles delegation directly when asked; before finishing, record delegated scopes,
  skills, integrated findings, and pending findings so compaction does not erase them.

- Latest SDK fast-path hardening round integrated and six agents closed; detailed
  validation is in `COMPACT_CONTEXT.md`. Route JSON remains planning-only at
  `approved_runtime_evidence_missing`; SDK JSON remains blocked with SDK `0/12`, P0
  `0/4`, `stable_claim_allowed=false`.
- Runtime fast-path note: wrapper/runtime were refreshed and the first bounded observer
  window is documented in the 2026-06-04 fast-path research note. Next retry needs a real
  player lifecycle window; startup alone is known insufficient.
