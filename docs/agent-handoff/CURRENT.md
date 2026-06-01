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
- `docs/public_sdk_surfaces.json::v1_sdk_completion_blockers` is the active blocker list for a complete SDK claim; all blocker rows remain unresolved unless promoted or explicitly excluded/post-v1 where the reviewed v1 release statement and surface contract allow it.
- `scripts/check_public_sdk_v1_completion.py --json` intentionally reports blocked on the current tree. Do not use broad phrases like `v1.0 stable`, `complete SDK`, `full SDK`, or `production SDK` in public sinks unless that gate allows the stable SDK claim. The checker also enforces canonical `stable_release_contract.claim_requires` and `not_sufficient` clauses so Plugin Hub package shape, RC readiness, and copied-data surfaces cannot become sufficient evidence by manifest drift.
- Plugin Hub work is post-SDK-complete planning only. Do not route active rounds to Plugin Hub examples, packaging, intake tooling, or package hardening while SDK blockers remain open. Installed SDK examples are Linux x86_64 contributor/package-shape evidence only and are not Plugin Hub inputs.
- `obelisk.command_chat_response_path.v1` and `obelisk.commands_replies.v1` remain
  blocked/planning-only until promoted player identity and permissions/admin exist. Their
  checkers must keep public header, ABI, runtime, SDK, reply/send/broadcast/moderation, and
  migration/ArkApi portability claims false.
- `scripts/check_command_permission_route_gate.py --json` is the canonical offline
  planning gate for the principal -> permissions/admin -> command response ->
  commands/replies route. It composes the permissions query fail-closed contract,
  permissions/admin public-readiness, command copied-response intent, command/principal/
  authz bridge, command/chat response public-readiness, and commands/replies readiness
  checks. A pass is planning-only; promotion/public ABI/public SDK/runtime/public-header
  claims must stay false.
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
- Current identity next blocker is approved copied runtime principal lifecycle evidence
  for the accepted login/logout anchor route. Lifecycle-anchor and principal-invalidation
  manifests are consume-only; no public identity, permissions, commands, runtime lookup,
  ResourceHandle, mutation, return override, or v1 SDK completion claim is promoted.
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
  public SDK, and runtime readiness stay false.
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
  reading UFunction memory or dispatching callbacks.
- Static field-window evidence clears only the field-window packaging blocker, is not a `v1.0` SDK blocker, route shortcut, or completion signal. CMake package target are present as package-shape evidence only, not a `v1.0` completion marker.
## Priority Next Steps

- Primary v1 route: player identity has accepted offline/core/reflection inventory,
  12/12 candidate fixtures for the exact 12-target `players-identity-lifecycle-intake`
  set, distinct second-source layout evidence, consume-only lifecycle/principal manifests,
  and an exact runtime evidence builder/checker path. Current blocker: a real approved
  copied runtime principal lifecycle evidence summary, still with no identity promotion,
  public SDK readiness, or runtime readiness. Do not rerun completed broad/offline routes
  unless a new binary hash or rejected evidence requires it. For the current binary hash,
  the next useful artifact is a consume-accepted
  `obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1` manifest
  from a copied, redacted, approved observer log; more FName/GObjects/Ghidra/radare
  orientation work is not the SDK blocker.
- Demand-map priority from local NextGenPlugins dictionary signals is P0 principal ->
  permissions/admin -> command response; P1 economy/storage/operator
  ingress, inventory/items mutation, and structure/build policy; P2 dino/tribe/
  buff-status/mission/transfer leaf lanes. Do not copy ArkApi/NextGenPlugins
  implementation details.
- Offline fallback while runtime/core work is blocked: keep progress through guardrails,
  permission/admin query-only design, command/principal contract, and inventory
  copied-signal hygiene. Inventory copied
  signals are the higher-value side lane, but do not displace identity -> permissions/admin
  -> commands/replies and does not authorize Transfer runtime work. Neither side lane
  displaces identity -> permissions/admin -> commands/replies. Prefer inventory
  copied-signal hygiene over structure census when choosing one side lane, while
  structure census remains useful offline planning/consume-only work.
- Current no-core side-lane: `item-return-only-policy-slice` has three copied
  `GameplayPolicyEvent` `ReturnValue` checks and accepted descriptor reconciliation; it
  does not promote public Inventory SDK, Items SDK, identity, mutation, return override,
  or v1.
  The item copied-signal bridge now revalidates property class FName index, property class
  object index, and property flags in `ItemFieldRange`, matching the inventory copied-signal
  metadata hardening pattern. This rejects forged item observations but still does not
  promote public Inventory/Items SDK, identity, mutation, return override, runtime readiness,
  or v1.
- v0.2 internal hardening lane: Mission copied-bool is internal/default-off only, not a
  Plugin Hub module or Mission SDK claim. The preserved bool-tail evidence is
  `bool_field_size=1`, `bool_byte_offset=0`, `byte_mask=0x01`, `field_mask=0xff`, and
  `native_bool=false`; consume mode accepts it and promote mode blocks it as candidate-only.
  Detail:
  `docs/research/2026-05-31-v02-module-priority.md`.
- `scripts/check_mission_transfer_dino_tribe_v1_outcome_accounting.py` is accounting-only:
  the umbrella blocker must name mission, transfer, dino policy, tribe policy, and
  buff/status leaf outcomes, but the checker does not promote any module SDK.
- Buff copied-scalar evidence is repaired at the layout layer: `buff-breadth-intake` and
  refreshed `buff-compact-intake` both compare `3/3`, but compact remains
  internal-layout-only with `target_set_not_release_readiness`. Do not mark Buff scalar
  public/runtime readiness ready until copied payload policy, redaction, dispatcher
  lifecycle, and promotion gates exist.
- Structure aggregate/census remains planning/consume-only, and build-policy intake now
  has accepted planning-only `3/3` second-source layout evidence; no runtime observer,
  public StructureEvents SDK, enforcement, return override, or v1 claim is promoted.
  `scripts/check_structure_build_policy_offline_intake.py` validates only the offline
  build-policy intake manifest/target set/SHA/non-claim/readiness-false shape and its OK
  result is `accepted_for_offline_planning`, not SDK or runtime readiness.
- Command/principal/authz/response bridge is planning-only over
  `principal_handle + principal_generation + principal_scope_flags`; it adds no public
  header, capability bit, response ABI, runtime wiring, or server validation.
- Command/chat response static orientation is complete for the reviewed binary but remains
  orientation-only until identity, permissions/admin, and a copied response contract exist.
- Permissions/admin pre-ABI contracts remain candidate-only. Public symbols stay empty
  until copied identity/principal semantics, provenance, scope/generation, epoch,
  rate-limit/audit, and v1 sequence gates are resolved. `operator-config` is recognized
  for planning/audit but is not allow-capable. Fail-closed coverage must include
  `principal_generation_mismatch`, not only missing or stale generations.
  `scripts/check_permissions_admin_public_readiness.py` is now the planning-only reusable
  gate for this surface: it accepts the current blocked state only with
  `public_header_allowed=false`, `public_abi_ready=false`, `public_sdk_ready=false`, and
  `runtime_ready=false`. The internal `AuthzDecisionModel` also models copied query text
  bounds (`action` required <=128 bytes, optional `resource_scope` <=256 bytes), without
  promoting public permissions/admin ABI, parser, cache, mutation, or admin actions.
- Operator ingress/storage is an offline internal planning contract only:
  `obelisk.operator_ingress_storage.v1` has no public header, public ABI, runtime
  services, promotion readiness, or v1 completion meaning. It is useful for shaping later
  operator-owned inputs, schema migration, queue lifecycle, text/audit redaction, and
  multi-instance lifecycle, but it must not become a shortcut around identity ->
  permissions/admin -> command response.
  `scripts/check_operator_ingress_storage_offline_contract.py` validates only this
  offline planning contract and does not create public SDK, runtime, or promotion evidence.
- Plugin Hub review is parked until SDK completion; keep any Plugin Hub wording
  non-promotional and route active work to SDK blockers.
- Revalidate before lead integration: with the vanilla-gdb candidate root plus
  consume-only lifecycle-anchor and principal-invalidation manifests, identity readiness
  stays blocked on approved runtime principal lifecycle evidence. Public SDK v1
  completion stays blocked, and Plugin Hub docs stay non-promotional.
- Do not rerun the completed admin snapshot, second-source layout, or lifecycle layout
  routes; the next identity blocker is approved runtime principal lifecycle evidence.
  Current recipe:
  `docs/research/2026-05-31-player-identity-offline-pack-preflight.md`

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
