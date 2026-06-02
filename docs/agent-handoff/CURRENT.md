# Current Agent Handoff

This file is an active routing table only. Durable evidence belongs in
`docs/research/`, resume facts in `COMPACT_CONTEXT.md`, and old detail in
`HISTORY-*.md`. Historical recovery context is not active routing; use
`git log --oneline -1` for the checkpoint.

## Active Objective

- Published baseline: `v0.1.0-rc.2` is a core-first RC, not a production-stable `v1.0`
  or complete SDK claim. Public RC scope remains limited to promoted copied
  `GameplayPolicyEvent`, minimal copied `ChatMessageEvent`, descriptor helpers, and
  process-local timers.
- Post-RC target: a complete `v1.0` public SDK contract for plugin authors. The complete
  v1 claim is blocked; do not use complete/full/production/stable SDK wording unless
  `scripts/check_public_sdk_v1_completion.py --json` allows it.
- Active P0 spine:
  `docs/public_sdk_surfaces.json::v1_required_dependency_chain` is promoted-only for a
  complete SDK claim and currently ordered as `obelisk.player_identity.v1` ->
  `obelisk.permissions_admin.v1` -> `obelisk.command_chat_response_path.v1` ->
  `obelisk.commands_replies.v1`. Excluded/post-v1 results are scoped non-complete
  bookkeeping only.
- Current accounting: SDK completion remains fail-closed with complete-SDK progress
  `0/12`, P0 promoted count `0/4`, and `stable_claim_allowed=false`.
- Current identity status: `scripts/build_player_identity_planning_source_manifests.py`
  can produce source-aligned planning manifests for the bound identity route. It now
  proves accepted lifecycle anchor `source_snapshot_sha256` values against the current
  `--snapshot-root` files before a no-approved-runtime-evidence bound proof may report
  `approved_runtime_evidence_missing`. After accepted approved runtime evidence, the only
  allowed route blocker is `identity_public_contract_gate_missing`, still
  locked/planning-only. The default route remains blocked first at
  `lifecycle_anchor_first_evidence_provenance_unbound` unless explicit aligned manifests
  are supplied.

## Hard Overrides

- GitHub work may be delegated only for an evidenced, stable milestone. This handoff does
  not authorize push, tag, release-ref updates, rebase, or routine publication.
- No server target has standing approval. Technical progress is only a reason to request a
  scoped run; it is not approval to change markers/env, start/restart/stop a server, run
  ReflectionScanner, ptrace/gcore, broad ProcessEvent tracing, runtime observers, or write
  under protected live paths.
- Request-pack, preflight, `planning_layout_gate.ready=true`, planning acceptance, or
  route acceptance are not runtime approval and do not authorize public SDK readiness,
  runtime readiness, release readiness, command router, reply/send-chat ABI, marker/env
  changes, runtime capture, Discord, or v1 completion.
- The lead retains server-safety decisions.
- no Discord for internal rounds or agent status. Public modder-facing milestones and
  beta-test notices require explicit current-turn approval, the guarded helper, embed
  shape, and dry-run first. Use only `OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL` or
  `OBELISK_BETA_TEST_WEBHOOK_URL` by variable name. Always dry-run before any approved send.
  No Discord for routine validation, speculative reversing notes, private live-ops detail,
  raw player text, or secrets.
- ArkServerApi/AseApi and local `NextGenPlugins` clones are names and demand signals only.
  Do not
  copy code, offsets, layouts, vtables, ABI assumptions.
  Do not copy architecture, ergonomics, behavior, offsets, layouts, vtables, ABI
  assumptions, wrappers, raw UE pointer APIs, command parsers, return semantics, or source
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
- ResourceHandle remains blocked on rejected runtime object samples plus runtime serial
  reuse/wraparound semantics. Strict serial policy artifacts remain candidate-only and do
  not prove runtime reuse semantics, public lookup safety, public lookup, or public
  ResourceHandle readiness. Do not restart broad FName, GObjects, or core scans for that
  blocker unless current evidence is contradicted.

## Current Routing Facts

- `scripts/check_command_permission_route_gate.py --json` is the canonical offline route
  posture check for identity/principal -> permissions/admin -> command response ->
  commands/replies. Passing it means planning-only alignment, not public ABI, runtime
  readiness, command router readiness, reply/send-chat ABI, or v1 completion.
- The default route currently reports `valid=true`, `planning_only=true`,
  `promotion_ready=false`, and current blocker
  `lifecycle_anchor_first_evidence_provenance_unbound`.
- `scripts/build_player_identity_planning_source_manifests.py --output-dir <tmp>/planning`
  emits planning-only `players-identity-first-evidence.json`,
  `players-identity-lifecycle-anchor-candidates.json`, and
  `players-identity-principal-invalidation-policy.json` bound to the current
  first-evidence source and current snapshot-root hashes for `ShooterGameMode.HandleNewPlayer`
  and `ShooterGameMode.OnLogout`. A transient bound route proof with those outputs reports
  `approved_runtime_evidence_missing`, with runtime/server authorization false.
  If future accepted approved runtime evidence is supplied, aggregate and bound route
  validation may accept `identity_public_contract_gate_missing` only as locked,
  planning-only state with identity, permissions/admin, command response, commands/replies,
  public SDK, public header, and runtime readiness still false.
  Route-lock expectation: `approved_runtime_evidence_missing` keeps
  `blocked_until=[approved_runtime_principal_lifecycle_evidence,
  reviewed_identity_public_contract]`; `identity_public_contract_gate_missing` keeps
  `blocked_until=[reviewed_identity_public_contract]`.
- Current recipe:
  `docs/research/2026-05-31-player-identity-offline-pack-preflight.md` remains the safe
  offline pack route. It requires a non-protected complete
  `obelisk.core-dump-evidence-pack.v1`, accepted `obelisk.reflection-inventory-pack.v1`,
  12/12 candidate fixtures, and accepted distinct second-source layout
  evidence from the vanilla-gdb core. The standalone lifecycle and principal manifests
  are consume-only planning inputs; the consume-only lifecycle-anchor and
  principal-invalidation manifests are consume-only planning inputs; they must be
  source-bound before the aggregate route can move past
  `lifecycle_anchor_first_evidence_provenance_unbound`.
  After explicit bound artifacts are supplied and accepted, the next blocker is approved
  runtime principal lifecycle evidence. Do not rerun the completed admin snapshot,
  second-source layout, or lifecycle layout routes.
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
  `InventoryComp`, `anActor`, and raw params.
- Structure census, Mission/Transfer/Dino/Tribe, ResourceHandle, economy/storage/operator
  ingress, and gameplay tick surfaces remain planning, post-v1, or blocked unless a
  future route explicitly promotes them with evidence.

## Priority Next Steps

- P0 identity: use `scripts/build_player_identity_planning_source_manifests.py` when a
  bound route proof is needed, then run
  `scripts/check_command_permission_route_gate_bound_identity_sources.py`. For a
  no-runtime-evidence bound proof, confirm the wrapper blocker is
  `approved_runtime_evidence_missing`. If accepted approved runtime evidence is supplied
  to the route, confirm `identity_public_contract_gate_missing` and keep all
  unlock/readiness flags false. The previous offline
  provenance gap for accepted lifecycle-anchor snapshot hashes is closed in the builder
  and bound wrapper; stale standalone manifests still fail closed unless regenerated or
  explicitly aligned to the current `--snapshot-root`.
- P0 runtime evidence: prepare, but do not run, a fresh live-ops brief for approved copied
  runtime principal lifecycle evidence. It must name target instance/map, feature gates,
  marker/env changes, restart/start window, notice path if players are involved, evidence
  capture, rollback, and post-run stable posture. The request-pack now carries a checked
  `operator_live_ops_brief`, reviewed server binary path/SHA, explicit pre/post evidence
  paths, exact env/marker boundaries, and canonical rollback delta; acceptance still only
  advances to current-turn operator approval required.
- P0 public contract: after approved runtime principal lifecycle evidence exists, the
  next blocker is `identity_public_contract_gate_missing`; review the player identity
  contract before permissions/admin, command response, or commands/replies ABI. The
  primary offline gap remains `privacy.identifier_redaction`.
- Runtime/ABI hardening: gameplay-policy rollback-failure orphan coverage now includes
  structure, inventory, and item-return paths in `PluginManagerTests`; repeating timer
  cleanup under an in-flight callback during `UnloadAll` is now covered.
- Side lanes: mission/transfer/dino/tribe/buff leaf accounting is now enforced by
  top-level SDK completion via
  `check_mission_transfer_dino_tribe_v1_outcome_accounting.py`; umbrella release
  wording cannot bypass explicit mission, transfer, dino-policy, tribe-policy, and
  buff-status outcomes. This is accounting-only and does not promote
  Mission/Transfer/Dino/Tribe/Buff SDKs, runtime, ABI, public callbacks,
  ResourceHandle, or v1 completion.
- Next P0 guardrail: permissions/admin structured promotion must require a matching
  player-identity promotion certificate with the expected surface, chain position, and
  artifact hash before any permissions/admin public/readiness claim can count.

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
- Lead handles delegation directly when the user asks for agents. Keep the scoped
  delegation fact in handoff/research notes before finishing so compaction does not erase
  which work was delegated and which findings remain pending.
- Recent delegated rounds before the current route work are summarized in
  `COMPACT_CONTEXT.md`: snapshot-root binding, runtime-evidence request/brief hardening,
  preflight sidecar replay, and operational-window projection.
- Latest identity-public-contract route round used four lead-scoped read-only agents:
  public-contract gap/readiness, route composition, privacy/redaction, and
  handoff/research continuity. Integrated result: route and bound-route validation now
  accept `identity_public_contract_gate_missing` only as locked planning after approved
  runtime evidence, SDK completion requires the public-contract readiness report to keep
  `next_blocker=identity_public_contract_gate` plus unresolved
  `privacy.identifier_redaction`, and no permissions/admin, command, runtime, public
  header, or stable SDK readiness is unlocked.
- Latest route-lock/evidence-hardening round used four lead-scoped read-only agents:
  route/accounting, permissions/admin dependency evidence, side-lane SDK accounting, and
  handoff continuity. Integrated result: route locks now dedupe
  `blocked_until=[reviewed_identity_public_contract]` for
  `identity_public_contract_gate_missing`; SDK completion requires identity contract
  structured evidence to carry the full blocker set, `blockers=[]`, and
  `resolved_inputs=[runtime.lifecycle_evidence]`; P0 accounting explicitly keeps
  `identity_public_contract_gate_missing` non-counting.
- Latest mission-leaf accounting follow-up used four lead-scoped read-only agents:
  mission accounting integration, release-statement accounting risk,
  permissions/admin dependency risk, and handoff continuity. Integrated result:
  SDK completion now runs the mission-transfer-dino-tribe outcome checker, rejects
  umbrella wording without explicit leaf outcomes, and preserves fail-closed status:
  `stable_claim_allowed=false`, complete-SDK progress `0/12`, and P0 progress `0/4`.
