# Current Agent Handoff

This file is an active routing table only. Durable evidence belongs in `docs/research/`,
resume facts in `COMPACT_CONTEXT.md`, and old detail in `HISTORY-*.md`. Historical
recovery context is not active routing; use `git log --oneline -1` for the checkpoint.

## Active Objective

- `v0.1.0-rc.2` is the current published core-first RC baseline for the current public surface after a clean release gate and tag/ref verification; stale tags must not be reused.
- Current post-RC focus: use the accepted RC UFunction second-source root and release baseline as evidence, then continue the complete-SDK blocker track without treating historical recovery context as active routing or implying v1 completion.
- Post-RC work moves toward `v1.0`: a complete public SDK contract for plugin authors,
  not just a stable runtime. Use `docs/SDK_V1_COMPATIBILITY.md` and
  `docs/public_sdk_surfaces.json` as the v1 surface map until a release gate supersedes
  them.
- Treat player identity/principal, permissions/admin, command response, chat, inventory, structures, tribes, dinos, buffs, missions, transfers, timers, config/logging, economy/database, and admin tooling as module areas above the same core. Promote each only through copied-data ABI, privacy, lifecycle, and second-source/static evidence gates.
- Latest local hardening: player-identity first-evidence reporting can now include an
  accepted player-principal lifecycle request-pack/observer env pair while keeping
  `approved_runtime_evidence_missing` as the blocker; request packs and window-manifest
  checks are explicitly rejected as runtime principal lifecycle evidence. Inventory-action
  fixture boundary now locks exact function flags, param counts/sizes, return offset,
  field offsets, element sizes, array dims, property flags, and direction for the two
  redacted action fixtures. Permissions/admin query planning now also requires a
  candidate-only `principal_provenance_policy`: the principal tuple source must be
  runtime-owned player identity observation, plugin/command/operator-config supplied
  principal tuples are forbidden, generation/scope provenance is required before allow,
  and server-process epoch mismatch fails closed internally. These are guardrails only
  and do not promote identity, permissions/admin, Inventory SDK, runtime readiness,
  public SDK readiness, or v1 completion.
- Latest SDK-v1 alignment: `docs/public_sdk_surfaces.json::v1_required_dependency_chain`
  is the P0 complete-SDK spine: `player_identity`, `permissions_admin`,
  `command_chat_response_path`, and `commands_replies`. Those four surfaces must be
  promoted with evidence for any complete/full/production SDK wording; excluding or
  naming them post-v1 is only scoped non-complete release-statement accounting.
- Latest copied-surface hardening: Inventory copied-policy recognition now records
  borrowed params provenance only for targets with copied scalar ranges, rejects forged
  scalar ranges that do not point to `params + reflected_offset`, keeps metadata-only
  inventory action targets without hidden params provenance, and preserves no-budget/no-read
  tests. The command/permission route gate also has an explicit `route_lock` invariant
  keeping permissions, command response, and replies locked behind player-identity runtime
  evidence plus the reviewed identity public-contract gate.
- Latest offline gate hardening: player-principal runtime evidence bundle preflight and
  window-manifest checks now validate the paired `window-request.json` and
  `observer-window.env` semantically, not just by path/SHA. The current request-pack for
  `arkserver2/TheIsland` is semantically ready again; bundle inputs still correctly fail
  closed until copied `Obelisk.log`, `window-manifest.env`, and an approved evidence bundle
  exist. Inventory copied-policy dispatch also requires exact reflected `ParmsSize`
  provenance before scalar copy.

## Hard Overrides

- GitHub publication is lead-only. GitHub work may be delegated only for an evidenced, stable milestone; this handoff does not authorize push, tag, release-ref updates, rebase, or routine publication.
- No tag or release-ref push may occur without release-manager/lead authorization for the current-turn release scope.
- No server target has standing approval. Server-backed debug/beta work requires a current approved live-ops brief naming target instance/map, feature gates, marker/env changes, start/restart/stop window, notice path when players are involved, evidence capture, and rollback. Technical progress is only a reason to request a scoped run, not approval by itself.
- no Discord for internal rounds or agent status; also no Discord for routine validation or speculative reversing notes. Discord drafts or sends require explicit current-turn approval for approved major public modder-facing milestones or operator-approved beta-test windows, must use `OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL` or `OBELISK_BETA_TEST_WEBHOOK_URL`, and must dry-run through `scripts/send_discord_embed.py` before any approved send. Always dry-run before any approved send.
- Runtime posture is default-deny for filtered/global raw `ProcessEvent`, public `CallProcessEvent`, ProcessEvent blocking, broad tracing, ReflectionScanner, debug controls, and observers unless the matching approved env+marker pair is enabled for a scoped debug window.
- PluginManager unload cleanup skips `dlclose`, retains the plugin for retry, and does not repeat plugin shutdown when plugin-owned callback cleanup fails.
- `CallProcessEvent` remains an init-window debug escape hatch only: the current plugin owner is inside `ObeliskPlugin_Init`, has `OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT`, and Post-init calls through captured API tables are unsupported until a future replacement must carry an owner token.
- ArkServerApi/AseApi and local `NextGenPlugins` clones are names and demand signals only,
  not architecture, ergonomics, behavior maps, porting targets, or copying sources. Do not
  copy code, offsets, layouts, vtables, ABI assumptions, wrappers, raw UE pointer APIs,
  constants, schemas, control flow, command parsers, return constants, return semantics,
  or implementations.

## Current Routing Facts

- RC public scope remains limited to `GameplayPolicyEvent`, minimal copied
  `ChatMessageEvent`, `DescribeResourceKind`, `DescribeGameplayPolicyEventKind`, and
  process-local owner-token timers with explicit unregister; this is not a gameplay/module timer API, shared scheduler state, UE identity, or persistent handles. It is not a production-stable `v1.0` claim.
- `docs/public_sdk_surfaces.json::v1_sdk_completion_blockers` is the active blocker list
  for a complete SDK claim. The P0 `v1_required_dependency_chain` is promoted-only for a
  complete SDK claim; non-chain blockers may be promoted or explicitly excluded/post-v1
  where the reviewed v1 release statement and surface contract allow scoped accounting.
- `scripts/check_public_sdk_v1_completion.py --json` intentionally reports blocked on the current tree. Do not use broad phrases like `v1.0 stable`, `complete SDK`, `full SDK`, or `production SDK` in public sinks unless that gate allows the stable SDK claim. The checker also enforces canonical `stable_release_contract.claim_requires` and `not_sufficient` clauses so Plugin Hub package shape, RC readiness, and copied-data surfaces cannot become sufficient evidence by manifest drift.
- Plugin Hub work is post-SDK-complete planning only. Do not route active rounds to Plugin Hub examples, packaging, intake tooling, or package hardening while SDK blockers remain open. Installed SDK examples are Linux x86_64 contributor/package-shape evidence only and are not Plugin Hub inputs.
- `obelisk.command_chat_response_path.v1` and `obelisk.commands_replies.v1` remain
  blocked/planning-only until promoted player identity and permissions/admin exist. Their
  checkers must keep public header, ABI, runtime, SDK, reply/send/broadcast/moderation, and
  migration/ArkApi portability claims false.
- `scripts/check_command_permission_route_gate.py --json` is the canonical offline
  planning gate for the principal -> permissions/admin -> command response ->
  commands/replies route. It now starts with the player-identity public-contract gap
  guardrail, then composes the permissions query fail-closed contract,
  permissions/admin public-readiness, command copied-response intent, command/principal/
  authz bridge, command copied-response intent lifecycle, command/chat response
  public-readiness, and commands/replies readiness checks. A pass is planning-only;
  promotion/public ABI/public SDK/runtime/public-header claims must stay false.
- `docs/permissions_admin_query_failclosed_contract.json` requires principal provenance
  before any future allow: runtime-owned player identity observation is the only accepted
  principal tuple source, plugin/command/operator-config supplied principal tuples are
  fail-closed, and `missing_principal_provenance`, `plugin_supplied_principal_tuple`, and
  `server_process_epoch_mismatch` are internal candidate reason flags. This is not a
  public ABI field or permissions/admin promotion.
- `docs/command_copied_response_intent_planning_decisions.json` mirrors the same
  principal-provenance boundary in the permission-query crosswalk before command response:
  response-intent planning requires runtime-owned principal tuple provenance and fails
  closed on missing principal provenance, plugin/command/operator-config supplied tuples,
  and server-process epoch mismatch. This remains planning-only and does not create a
  public response ABI, reply/send-chat API, runtime delivery, or command router.
- The active P0 dependency route is principal -> permissions/admin -> command response.
  Player identity/principal is the first v1 dependency for permissions, commands,
  economy, moderation, and several ownership-sensitive module APIs. The target set is
  12-target `players-identity-lifecycle-intake`; it remains planning-only and
  candidate-only.
- Current player-identity state: accepted offline/core/reflection inventory,
  complete `obelisk.core-dump-evidence-pack.v1`, accepted
  `obelisk.reflection-inventory-pack.v1`, 12/12 candidate fixtures for
  `players-identity-lifecycle-intake`, and accepted distinct second-source layout
  evidence from the vanilla-gdb core, including committed candidates
  `ShooterPlayerController.ServerListPlayers` and
  `ShooterPlayerController.ServerKickPlayer`. The lane depends on a non-protected
  evidence root; lifecycle-anchor and principal-invalidation manifests are accepted for
  consume-only planning. Promotion remains false.
- the next identity blocker is approved runtime principal lifecycle evidence for the
  accepted login/logout anchor route; consume-only lifecycle-anchor and
  principal-invalidation manifests are accepted for consume-only planning. No public
  identity, permissions, commands, runtime lookup, ResourceHandle, mutation, return
  override, or v1 SDK completion claim is promoted.
- Private hook-side player-principal lifecycle observer wiring now exists for
  `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout`: it is default-off,
  observer-debug/env/marker/SHA/log-budget gated, redacted, dispatch-limit `0`, and
  plugin-invisible. It is evidence collection only; no player identity, permissions,
  commands/replies, runtime/public SDK readiness, or v1 claim is promoted.
- Player-principal runtime evidence must use the exact single-module, plugins-disabled,
  dispatch-limit-`0`, no-sibling marker window, an observer-window preflight with a
  secret-free `--env-file`, and a checked `--window-manifest` whose source path/SHA
  matches the copied log under
  `/servidor/ark/workspace-offline/live-validation-logs/<run-id>/Obelisk.log`. Live/protected
  source paths are rejected. The effective env snapshot must fail closed on missing or
  duplicate required keys, unsupported SHA, `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT`
  other than `10`, nonzero dispatch or PE trace, wrong instance, alternate observer env,
  or callback/debug escape env. Request packs, `operator-approval-request.md`,
  `observer-window.env`, and `preflight=ok` are preparation/posture checks only; they do
  not authorize marker/env changes, starts/restarts/stops, runtime capture, Discord,
  runtime readiness, public SDK readiness, or v1 completion. Analyzer rules remain strict: copied bool cases,
  redaction, lifecycle order, post-gate events, log-budget bounds, monotonic sequence
  quality, stable posture, rollback, no private identity/UE terms in keys or values, and
  no-claim/no-public-readiness semantics.
- Candidate lifecycle layouts are reproducible for all six
  `players-lifecycle-anchor-candidates` targets, but only `ShooterGameMode.HandleNewPlayer`
  and `ShooterGameMode.OnLogout` are narrow runtime-ordering candidates. Details:
  `docs/research/2026-06-01-players-lifecycle-anchor-candidates-fixture-gap.md`.
- `scripts/check_player_identity_first_evidence_readiness.py` accepts current consume-only
  first evidence and leaves `approved_runtime_evidence_missing` as the blocker; promotion,
  public SDK, and runtime readiness stay false. If passed the current request-pack and
  observer env, it reports `request_pack_ready=true` only as pre-window planning state;
  the missing runtime artifacts remain copied `Obelisk.log`, checked `window-manifest.env`,
  runtime observer summary, and approved evidence manifest.
- Static orientation reports for identity/lifecycle/admin and command response are
  navigation clues only, not consume/promote evidence packs or artifact-gate schemas.
- The current artifact-root audit is summarized in
  `docs/research/2026-05-31-offline-artifact-inventory-audit.md`; the active
  `/servidor/ark/workspace-offline` player-identity run has passed the old artifact-root
  stage. First-evidence consume-gate acceptance is restored; runtime principal lifecycle
  evidence is the next promotion blocker.
- Inventory, structures, missions, transfers, dinos, buffs, tribes, ResourceHandle, and
  GObjects remain internal/candidate. ResourceHandle/public GObjects remain blocked; old
  flag-policy artifact is obsolete; durable rich-provenance refresh is preserved; Consume
  mode accepts it and promote mode stays blocked; post-callback rejection contract is
  preserved as candidate-only; first strict serial reuse/wraparound policy artifact is
  preserved; manifest consume mode accepts it and promote mode blocks it as candidate-only.
  This does not unlock runtime negative samples, public lookup, object identity, mutation,
  or fail-closed semantic helper promotion. Do not rerun broad FName, GObjects, or core
  scans for ResourceHandle. Do not replace this with another broad offline FName/GObjects
  scan. next strict ResourceHandle blocker is rejected runtime object samples plus runtime
  serial reuse/wraparound semantics with a future-runtime-observation-plan only after an
  operator-approved live-ops brief names the exact debug target.
- `scripts/check_inventory_action_redacted_observer_gate.py` is an offline
  candidate-only checker for the future `enable-inventory-action-redacted-observer`
  marker and `inventory-action-compact-intake` fixtures. It must stay non-promotional:
  no runtime observer, dispatch readiness, public Inventory/Items SDK, item/inventory
  identity, lookup, mutation, return override, `ResourceHandle`, public callback, public
  ABI, runtime readiness, public SDK readiness, or `v1.0` completion claim.
  `ue/InventoryReflection` recognizes the two inventory-action targets by exact metadata
  only; all fields, including `AdditionalData`, keep `ExposesRange=false`, and
  `ProcessEventInventoryReflection` must continue rejecting their FName indices before
  reading UFunction memory or dispatching callbacks. The fixture boundary checker also
  fails closed on exact metadata drift for function flags, param counts/sizes, return
  offset, offsets, element sizes, array dims, property flags, and direction.
- Static field-window evidence clears only the field-window packaging blocker, is not a `v1.0` SDK blocker, route shortcut, or completion signal. CMake package target are present as package-shape evidence only, not a `v1.0` completion marker.
## Priority Next Steps

- Primary v1 route: Do not rerun the completed admin snapshot, second-source layout, or
  lifecycle layout routes; do not rerun completed broad/offline player-identity routes
  unless a new binary hash or rejected evidence requires it. The exact 12-target
  `players-identity-lifecycle-intake` set already includes
  `ShooterPlayerController.ServerListPlayers` and
  `ShooterPlayerController.ServerKickPlayer`; the next useful artifact is approved copied
  runtime principal lifecycle evidence from a copied, redacted, approved observer log.
  Current recipe: `docs/research/2026-05-31-player-identity-offline-pack-preflight.md`.
- Before runtime evidence exists, make offline progress through guardrails, permissions/admin
  query-only design, command/principal contracts, route-gate drift checks, and inventory
  copied-signal hygiene. Do not let inventory, structure, mission, transfer, dino, tribe,
  buff, or operator lanes displace identity -> permissions/admin -> commands/replies.
- Current request-pack directory
  `/servidor/ark/workspace-offline/live-validation-logs/20260601T120000Z-player-principal-lifecycle`
  is request-pack ready only and still lacks copied `Obelisk.log` plus
  `window-manifest.env`; this is not runtime approval or approved evidence. If this
  directory is rechecked, `scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py --preflight-only`
  should report `request_pack_ready=true`, `bundle_inputs_ready=false`, and blockers only
  for copied log/window manifest/approved manifest.
- `command_chat_response_public_readiness`, `commands_replies_public_readiness`, and
  `check_command_permission_route_gate.py` preserve runtime-owned principal provenance and
  keep public header, ABI, SDK, runtime, reply/send-chat, command-router, and permissions
  claims false.
- `check_player_identity_public_contract_gap_report.py` keeps player identity blocked on
  `privacy.identifier_redaction`, scans the public header for accidental identity/principal
  symbols, and does not require or replace approved runtime principal lifecycle evidence.
- Inventory copied signals are the current no-core side lane with the best return; item
  return-only policy signals and metadata hardening stay copied-signal-only and do not
  promote Inventory SDK, Items SDK, identity, mutation, return override, runtime readiness,
  or v1 completion.
- Mission copied-bool, buff scalar, structure census/build-policy, operator ingress/storage,
  and mission/transfer/dino/tribe/buff-status accounting stay internal, planning-only, or
  consume-only until their own copied ABI, redaction, lifecycle, and promotion gates exist.
- Structure build-policy offline intake is already accepted as planning layout for
  `PrimalStructure.IsAllowedToBuild`, `PrimalStructure.BPIsAllowedToBuild`, and
  `PrimalStructure.BPIsAllowedToBuildEx`; the useful next side-lane is a fixture/policy
  guardrail that freezes field shape/redaction and prevents public payload, runtime-ready,
  enforcement-ready, or return-override claims.
- ResourceHandle remains blocked on rejected runtime object samples plus runtime serial
  reuse/wraparound semantics; do not restart broad FName/GObjects/core scans for it.
- Demand-map priority from NextGenPlugins names is P0 principal -> permissions/admin ->
  command response; P1 economy/storage/operator ingress, inventory/items mutation, and
  structure/build policy; P2 dino/tribe/buff-status/mission/transfer leaves. Names are
  demand signals only, never implementation sources.
- Plugin Hub review is parked until SDK completion; keep any Plugin Hub wording
  non-promotional and route active work to SDK blockers.

## Agent Protocol
- Delegated sub-agents get only the scoped objective, safety baseline, allowed paths,
  required skills, expert role, expected decision, and edit permission needed for their
  task; pass only the skills needed for that scope. Do not pass leader-only cadence,
  active-goal framing, community policy, or
  unrelated module history unless it changes the worker's concrete task.
- The lead retains server-safety decisions. Sub-agents must not commit, amend, rebase,
  tag, push, update GitHub state, touch servers, send Discord updates, or broaden live-ops
  scope unless explicitly delegated for the current turn.
- Sub-agents are not alone in the codebase: do not revert unrelated changes; leave edits
  unstaged/uncommitted and report touched paths, validations, and risks.
