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

## Hard Overrides
- GitHub work may be delegated only for an evidenced, stable milestone. No tag or
  release-ref push has release-manager/lead authorization for this current-turn; this
  handoff does not authorize push, tag, release-ref updates, rebase, or routine publication.
- No server target has standing approval. Technical progress is only a reason to request a
  scoped run; it is not approval to change markers/env, start/restart/stop a server, run
  ReflectionScanner, ptrace/gcore, broad ProcessEvent tracing, runtime observers, or write
  under protected live paths.
- Request-pack/preflight/window-manifest/operator-receipt/sidecar readiness, planning
  acceptance, or route acceptance are operational preparation only; they do not authorize
  runtime work, public identity readiness, public ABI readiness, public SDK readiness, release readiness, command router,
  reply/send-chat ABI, marker/env changes, runtime capture, Discord, or v1 completion.
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
- Plugin Hub is post-SDK-complete planning only. Archived Plugin Hub docs are boundaries,
  not current work. Plugin Hub examples, package intake, catalog publication, and seed
  review do not replace the active SDK blocker chain.
- Plugin Hub/field-window packaging blocker notes remain package-shape evidence only, not
  a `v1.0` completion marker. Plugin Hub seed examples, CMake package target presence, and
  package schema docs are not a `v1.0` SDK blocker, route shortcut, or completion signal;
  they do not gain priority, support tier, public SDK scope, or `v1.0` completion weight
  while complete-SDK blockers remain open. No Plugin Hub publication, intake
  prioritization, production module availability, or support-tier activation is in the
  current RC/post-RC SDK scope.
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
  authorization remains false. Route-lock expectation:
  `approved_runtime_evidence_missing` keeps
  `blocked_until=[approved_runtime_principal_lifecycle_evidence,
  reviewed_identity_public_contract]`.
- Current recipe: `docs/research/2026-05-31-player-identity-offline-pack-preflight.md`
  remains the safe offline pack route. It requires a non-protected complete
  `obelisk.core-dump-evidence-pack.v1`, accepted `obelisk.reflection-inventory-pack.v1`,
  12/12 candidate fixtures, and accepted distinct second-source layout evidence from the
  vanilla-gdb core. Repo-local lifecycle-anchor and principal-invalidation manifests are
  consume-only planning inputs and source-bound; the default route consumes those
  repo-local fallbacks and reports `approved_runtime_evidence_missing`. The remaining
  blocker is approved runtime principal lifecycle evidence. Do not rerun completed admin
  snapshot, second-source layout, or lifecycle layout routes.
- Player identity first evidence uses the 12-target `players-identity-lifecycle-intake`
  planning set. `ShooterPlayerController.ServerListPlayers` and
  `ShooterPlayerController.ServerKickPlayer` are exact required admin targets in that set,
  but they are not accepted lifecycle anchors. Current accepted planning anchors for the
  bound route are `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout`.
- The next P0 runtime-side blocker is approved copied runtime principal lifecycle
  evidence. No approved copied runtime principal lifecycle evidence exists yet, and no
  runtime request is authorized by this file.
- Permissions/admin remains query-only planning until promoted copied identity/principal
  semantics exist. Command response and commands/replies remain blocked by identity and
  permissions/admin.
- Inventory copied signals remain the preferred side lane while P0 waits, but they do not
  promote inventory mutation, identity, lookup, ResourceHandle, or v1 completion.
  Current guardrails pin accepted inventory evidence to `minimal-second-source-intake`
  and `item-return-only-policy-slice`, keep `inventory-action-compact-intake` excluded,
  and reject positive raw identity/action-param claims such as `ItemId`, `ItemID1`,
  `InventoryComp`, `anActor`, and raw params. Item return-only public shape remains three
  copied `GameplayPolicyEvent` `ReturnValue` kinds only; no public Inventory SDK, Items
  SDK, identity, mutation, return override, or ResourceHandle.
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
- P0 runtime evidence: prepare, but do not run, a fresh live-ops brief for approved copied
  runtime principal lifecycle evidence. Request/window preparation is offline guardrail
  work only: request-pack acceptance keeps `server_operations_authorized=false`,
  `runtime_work_authorized=false`, public/runtime/promotion/v1 readiness false, and
  `next_blocker=operator_current_turn_runtime_window_approval_required`. Preserve checked
  `operator_live_ops_brief`, reviewed server binary path/SHA, exact env/marker
  boundaries, and sibling `window-request.json`, `observer-window.env`,
  `operator-approval-request.md`, completed `operator-approval-receipt.json`,
  `preflight-pre.json`, `preflight-post.json`, `window-manifest.env`, and copied log.
  Receipts count only for post-window replay; preflight sidecars keep false auth/readiness
  flags; preserve post-run checks, rollback delta, and no runtime/server authorization.
  Request packs are pre-window only: started/expired windows fail closed; receipt
  templates never count.
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
- Side lanes: Mission copied-bool exact bool-tail evidence is `bool_field_size=1`,
  `bool_byte_offset=0`, `byte_mask=0x01`, `field_mask=0xff`, and `native_bool=false`;
  consume mode accepts and promote mode blocks. Mission/Transfer/Dino/Tribe/Buff leaf
  accounting is enforced by `check_mission_transfer_dino_tribe_v1_outcome_accounting.py`;
  it remains internal/not ready, with no public Mission SDK, public module SDK,
  ResourceHandle, identity, mutation, return override, runtime, ABI, public callbacks,
  v1 completion, and does not authorize Transfer runtime work.
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


- Latest integration note: 2026-06-03 delegated four scopes for P0 runtime-evidence
  preparation, bound-route manifests, scoped release-statement parsing, and runtime ABI
  static guardrails. Integrated changes require approved-evidence replay sidecars to name
  the full post-window sibling set including operator request and copied log, reject
  unexpected stale sidecar keys, make planning-source manifests fail closed on source/
  schema/status/SHA/path drift and admin-target lifecycle misuse, require bound-route
  checks to use exact CLI-bound manifests, make scoped release-statement validation see
  delimiter variants and generated broad claims, and pin plugin-manager static guardrails
  for init-window `CallProcessEvent`, non-zero/non-reused owner/registration handles, and
  per-owner capability snapshots. `STATUS.md` now distinguishes default `0/7` statement
  outcomes from generated `7/7` bookkeeping while keeping P0 `0/4`, demand-family gate
  `0/12`, and `stable_claim_allowed=false`. Validation: approved-evidence/bundle 123 OK,
  planning/bound-route 71 OK, SDK completion 234 OK, plugin/timer/event guardrails
  36/7/6 OK, public SDK guardrails 196 OK, public chat guardrails 196 OK, handoff 15 OK,
  route JSON planning-only at `approved_runtime_evidence_missing`, SDK JSON blocked with
  SDK `0/12`, P0 `0/4`, generated scoped statement `ready=true` as non-complete
  bookkeeping only, `py_compile` and `git diff --check` OK. No runtime/server/Discord/
  GitHub operation.
- Active SDK guardrail follow-up integrated: runtime-evidence provenance/report-contract checks, downstream P0 false-only aliases, installed SDK/header guardrails, and four-note source-boundary indexing are hardened; baseline remains route `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`, stable false.
