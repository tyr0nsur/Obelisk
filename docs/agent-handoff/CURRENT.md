# Current Agent Handoff

This file is an active routing table only. Durable evidence belongs in `docs/research/`,
resume facts in `COMPACT_CONTEXT.md`, and old detail in `HISTORY-*.md`. Historical
recovery context is not active routing; use `git log --oneline -1` for the checkpoint.

## Active Objective

- `v0.1.0-rc.2` is the current published core-first RC baseline after a clean release
  gate and tag/ref verification; stale tags must not be reused.
- Current post-RC focus: move from the accepted RC UFunction second-source root and
  core-first release baseline toward the complete SDK track without treating historical
  recovery context as active routing.
- Post-RC work moves toward `v1.0`: a complete public SDK contract for plugin authors,
  not just a stable runtime. Use `docs/SDK_V1_COMPATIBILITY.md` and
  `docs/public_sdk_surfaces.json` as the v1 surface map until a release gate supersedes
  them.
- Treat chat, inventory, structures, players, tribes, dinos, buffs, missions, transfers,
  commands, permissions, timers, config/logging, economy/database, and admin tooling as
  module areas above the same core. Promote each only through copied-data ABI, privacy,
  lifecycle, and second-source/static evidence gates.

## Hard Overrides

- GitHub publication is lead-only. GitHub work may be delegated only for an evidenced, stable milestone; this handoff does not authorize push, tag, release-ref updates,
  rebase, or routine publication.
- No tag or release-ref push may occur without release-manager/lead authorization for
  the current-turn release scope.
- No server target has standing approval. Server-backed debug/beta work requires a
  current approved live-ops brief naming target instance/map, feature gates,
  marker/env changes, start/restart/stop window, notice path when players are involved,
  evidence capture, and rollback. Technical progress is only a reason to request a scoped
  run, not approval by itself.
- no Discord for internal rounds or agent status. Discord sends require explicit
  current-turn approval for approved public milestones or beta-test windows, must use
  `OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL` or `OBELISK_BETA_TEST_WEBHOOK_URL`, and must
  use embed shape through `scripts/send_discord_embed.py`. Always dry-run before any approved send.
  Never send routine validation notes, speculative reversing notes, or
  internal agent status.
- Runtime posture is default-deny for filtered/global raw `ProcessEvent`, public
  `CallProcessEvent`, ProcessEvent blocking, broad tracing, ReflectionScanner, debug
  controls, and observers unless the matching approved env+marker pair is enabled for a
  scoped debug window.
- `CallProcessEvent` remains an init-window debug escape hatch only: the current plugin
  owner is inside `ObeliskPlugin_Init`, has
  `OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT`, and Post-init calls through captured API
  tables are unsupported until a future replacement must carry an owner token.
- ArkServerApi/AseApi and local `NextGenPlugins` clones are names and demand dictionaries
  only, not a behavior map, not a porting target, and not a copying source.
  Do not copy code, offsets, layouts, vtables, ABI assumptions. Do not copy wrappers, raw UE pointer
  APIs, constants, schemas, control flow, command parsers, return constants, return
  semantics, or implementations.

## Current Routing Facts

- RC public scope remains limited to `GameplayPolicyEvent`, minimal copied
  `ChatMessageEvent`, `DescribeResourceKind`, `DescribeGameplayPolicyEventKind`, and
  process-local owner-token timers with explicit unregister; this is not a gameplay/module timer API, shared scheduler state, UE identity, or persistent handles. It is not a production-stable `v1.0` claim.
- `docs/public_sdk_surfaces.json::v1_sdk_completion_blockers` is the active blocker list
  for a complete SDK claim. Player identity, permissions/admin, the command/chat response
  path, commands/replies, inventory/items mutation, structure census/build policy,
  mission/transfer/dino/tribe, player services/economy/mobility, operator
  ingress/storage, and lifecycle ops recovery remain unresolved unless promoted or
  explicitly excluded in a reviewed v1 release statement.
- `scripts/check_public_sdk_v1_completion.py --json` intentionally reports blocked on the
  current tree. Do not use broad phrases like `v1.0 stable`, `complete SDK`, `full SDK`,
  or `production SDK` in public sinks unless that gate allows the stable SDK claim.
  The checker also enforces canonical `stable_release_contract.claim_requires` and
  `not_sufficient` clauses so Plugin Hub package shape, RC readiness, and copied-data
  seeds cannot become sufficient evidence by manifest drift.
- `oDescriptorCatalog` and Plugin Hub foundation work are metadata/contributor seeds only:
  lifecycle/config/logging, descriptor/catalog, and process-local timers are
  release-supported seed lanes; copied chat/policy stays experimental. Foundation work is
  not a substitute for v1 blockers.
- `obelisk.command_chat_response_path.v1` is post-v1 planning only, adds no ABI today,
  and keeps replies/send-chat/broadcast/moderation blocked. Static thunks, passive chat,
  vtable slots, raw callbacks, and legacy `CallProcessEvent` are insufficient; see
  `docs/command_chat_response_public_contract_decisions.json` and
  `docs/research/2026-05-31-commands-principal-routing-contract.md`.
- Player identity is the first v1 dependency for permissions, commands, economy,
  moderation, and several ownership-sensitive module APIs. The target set is 12-target
  `players-identity-lifecycle-intake`; it remains planning-only and candidate-only.
- Current player-identity state: the artifact root has the matching offline
  `ShooterGameServer` SHA `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`,
  but no non-protected copied core, no complete `obelisk.core-dump-evidence-pack.v1`, and
  no accepted `obelisk.reflection-inventory-pack.v1`.
- Current identity next step is to produce or approve a non-protected UFunction
  reflection-inventory pack with `target_set_coverage` for the full 12-target
  `players-identity-lifecycle-intake` set after core evidence exists. Then use
  `scripts/plan_ufunction_focal_snapshots.py` for
  `ShooterPlayerController.ServerListPlayers` and
  `ShooterPlayerController.ServerKickPlayer` only; do not treat ScriptStruct inventory,
  standalone snapshots, redacted signatures, static thunks, or a two-function-only
  inventory as satisfying this lane.
- `scripts/check_player_identity_first_evidence_readiness.py --artifact-root
  /home/flowcommunity-ark/obelisk-artifacts --json` currently reports
  `next_actionable_blocker.code=non_protected_core_input_missing`; the expected copied
  core path pattern is
  `/home/flowcommunity-ark/obelisk-artifacts/player-identity-offline-<run-id>/raw/core`.
- Static orientation reports for identity/lifecycle/admin and command response are
  navigation clues only, not consume/promote evidence packs or artifact-gate schemas.
- The current artifact-root audit is summarized in
  `docs/research/2026-05-31-offline-artifact-inventory-audit.md`: usable roots are
  layout-only, evidence-only, or consume-only, command/chat response remains
  orientation-only, and player identity is still blocked on a non-protected core plus a
  complete reflection inventory pack.
- Inventory, structures, missions, transfers, dinos, buffs, tribes, ResourceHandle, and
  GObjects remain internal/candidate. ResourceHandle/public GObjects remain blocked; old
  flag-policy artifact is obsolete; durable rich-provenance refresh is preserved; Consume
  mode accepts it and promote mode stays blocked. Do not rerun broad FName, GObjects, or
  core scans for ResourceHandle. The semantic helper/post-callback rejection contract is
  preserved as candidate-only and fail-closed; first strict serial reuse/wraparound policy
  artifact is preserved; manifest consume mode accepts it and promote mode blocks it as
  candidate-only; does not unlock runtime negative samples, public lookup, object identity,
  mutation, or return override. The next strict ResourceHandle blocker is rejected runtime
  object samples plus runtime serial reuse/wraparound semantics; future-runtime-observation-plan
  requires an operator-approved live-ops brief names the exact debug target. Do not replace
  this with another broad offline FName/GObjects scan.
- Static field-window evidence clears only the field-window packaging blocker, is not a
  `v1.0` SDK blocker, route shortcut, or completion signal. CMake package target are
  present as package-shape evidence only, not a `v1.0` completion marker.

## Priority Next Steps

- Primary v1 route: player identity remains blocked on a regular non-symlink
  non-protected copied core under
  `/home/flowcommunity-ark/obelisk-artifacts/player-identity-offline-<run-id>/raw/`.
  Matching offline binary exists; no paired core/run dir exists. After inputs exist, stage
  them with `scripts/prepare_player_identity_offline_raw_layout.py`, build
  `obelisk.core-dump-evidence-pack.v1`, then the 12-target
  `obelisk.reflection-inventory-pack.v1`, then exact admin focal snapshots. Current
  recipe: `docs/research/2026-05-31-player-identity-offline-pack-preflight.md`.
- Demand-map priority from local NextGenPlugins dictionary signals is P0 identity,
  commands/replies/response path, and permissions/admin; P1 economy/storage/operator
  ingress, inventory/items mutation, and structure/build policy; P2 dinos/tribes/
  missions/transfers. Do not copy ArkApi/NextGenPlugins implementation details.
- No-core fallback: keep progress offline through guardrails, permission/admin query-only
  design, command/principal contract, and inventory copied-signal hygiene. inventory
  copied signals are the higher-value side lane while identity waits on copied core
  evidence; structure census remains useful offline planning/consume-only work. Neither
  side lane displaces identity -> permissions/admin -> commands/replies. Prefer inventory
  copied-signal hygiene over structure census when choosing one side lane, and treat
  inventory/item copied signals as the higher-value side lane than structure census. Keep
  that work experimental and non-completion. This does not authorize Transfer runtime work.
- Current no-core side-lane: `item-return-only-policy-slice` has three copied
  `GameplayPolicyEvent` `ReturnValue` checks, accepted descriptor reconciliation, and now
  should keep source-snapshot provenance tight. It does not promote public Inventory SDK,
  Items SDK, identity, lookup, mutation, return override, runtime validation, or v1
  completion.
- v0.2 internal hardening lane: Mission copied-bool is internal/default-off only, not a
  product-facing Plugin Hub module or Mission SDK claim. Detail:
  `docs/research/2026-05-31-v02-module-priority.md`. Current bool-tail contract:
  `bool_field_size=1`, `bool_byte_offset=0`, `byte_mask=0x01`, `field_mask=0xff`, and
  `native_bool=false`.
- Product-planning lane: Structure aggregate/census is planning/consume-only, with no
  runtime observer, callback ABI, descriptor, public StructureEvents SDK, identity,
  mutation, enforcement, return override, or v1 completion claim. Detail:
  `docs/research/2026-05-31-aggregate-census-product-priority.md`.
  Exact build-policy target names such as `PrimalStructure.IsAllowedToBuild` and
  `APrimalStructure.IsAllowedToBuild` must stay out of public docs, ABI/descriptors,
  release target sets, and runtime dispatcher surfaces until a separate promotion gate
  accepts them.
- Command/chat response static orientation is complete for the reviewed binary but remains
  orientation-only until identity, permissions/admin, and a copied response contract exist.
- Permissions/admin has a machine-readable pre-ABI contract in
  `docs/permissions_admin_public_contract_decisions.json`; public symbols remain empty
  until copied identity/principal semantics, policy provenance, scope/generation, epoch,
  rate-limit/audit, and v1 sequence gates are resolved.
- Plugin Hub seed review requires exactly one package `Support tier: <tier>` declaration
  and rejects unnegated v1/ArkApi/permissions/identity/replies/mutation/storage/module
  support claims outside that tier. Release-supported examples are
  `sdk_minimal_plugin`, `sdk_descriptor_catalog`, and `sdk_timer_plugin`;
  `sdk_inventory_policy_audit` remains experimental.
- Plugin cleanup failure policy skips `dlclose`, retains the plugin for retry, and does not repeat plugin shutdown after shutdown already ran.
- Revalidate before any checkpoint: identity readiness stays blocked with
  `non_protected_core_input_missing`, public SDK v1 completion stays blocked, Plugin Hub
  docs stay non-promotional, and `git diff --check` passes.
- Start every supervised round by verifying no stale stand-by sub-agent remains open.
  Assign each sub-agent only the scoped objective, safety baseline, allowed paths,
  required skills, expert role, expected decision, and whether edits are allowed. Pass
  only the skills needed for that task. The lead retains server-safety decisions.

## Agent Protocol

- The lead owns integration. Sub-agents must not commit, amend, rebase, tag, push, update
  GitHub state, touch servers, send Discord updates, or broaden live-ops scope.
- Use expert roles with disjoint ownership: ABI/API engineer, build/SDK engineer,
  UE4 reflection engineer, static binary analysis engineer, live-ops engineer, release
  auditor, or docs/skills worker.
- Tell workers they are not alone in the codebase. They must not revert unrelated changes
  and must leave changes unstaged/uncommitted with touched paths and tests run.
- Read-only explorers should answer concrete questions with file/line evidence and no
  edits.
- Close old agents after integrating useful findings. Do not leave active agents without a
  polling/integration plan.
