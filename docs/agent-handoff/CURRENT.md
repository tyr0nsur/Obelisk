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
  not a substitute for v1 blockers. Installed SDK examples are Linux x86_64 samples only;
  they must not carry Windows/MSVC export branches or portability signals.
- `obelisk.command_chat_response_path.v1` is post-v1 planning only, adds no ABI today,
  and keeps replies/send-chat/broadcast/moderation blocked. Static thunks, passive chat,
  vtable slots, raw callbacks, and legacy `CallProcessEvent` are insufficient; see
  `docs/command_chat_response_public_contract_decisions.json` and
  `docs/research/2026-05-31-commands-principal-routing-contract.md`.
- The active P0 dependency route is principal -> permissions/admin -> command response.
  Player identity/principal is the first v1 dependency for permissions, commands,
  economy, moderation, and several ownership-sensitive module APIs. The target set is
  12-target `players-identity-lifecycle-intake`; it remains planning-only and
  candidate-only.
- Current player-identity state: `/servidor/ark/workspace-offline` now has the staged
  `player-identity-offline-identity-second-source-20260529T011227Z` hardlink layout, a
  complete `obelisk.core-dump-evidence-pack.v1`, an accepted
  `obelisk.reflection-inventory-pack.v1` with 12/12
  `players-identity-lifecycle-intake` target coverage, and committed candidate fixtures
  for `ShooterPlayerController.ServerListPlayers` and
  `ShooterPlayerController.ServerKickPlayer`.
- Distinct second-source layout is now accepted for the 12-target player-identity intake
  when using candidate root
  `/servidor/ark/workspace-offline/player-identity-offline-identity-vanilla-gdb-20260529T012853Z/focal-snapshots`
  with `scripts/compare_reflection_snapshots.py --planning-layout-intake`: totals are
  `targets=12`, `comparable=12`, `second_source_accepted=12`, rejected/inconclusive/missing
  all zero, and promotion remains false.
- Current identity next step is accepted login/logout lifecycle anchor evidence and
  principal invalidation semantics. The
  `obelisk.players-identity-principal-invalidation-policy.v1` schema is a
  planning/candidate-only policy artifact and is not promoted. The lane remains
  planning-only and candidate-only: no public identity, permissions, commands, runtime
  lookup, ResourceHandle, mutation, return override, or v1 SDK completion claim is
  promoted.
- Candidate lifecycle layouts are now reproducible across the base and vanilla-gdb offline
  cores for all six `players-lifecycle-anchor-candidates` targets in scratch evidence:
  `accepted=6`, `inconclusive=0`, `rejected=0`. This is still planning-only/candidate-only
  layout evidence; promotion mode fails as expected with `target_set_not_release_readiness`.
  The committed fixture tree now has the six base snapshots under
  `tests/fixtures/ufunction_snapshots/7e7ded49e0c6/players_lifecycle/`; planning-layout
  intake is ready against the vanilla scratch root, while promotion remains blocked by
  `target_set_not_release_readiness`. Details:
  `docs/research/2026-06-01-players-lifecycle-anchor-candidates-fixture-gap.md`.
  `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout` remain the narrow
  candidate anchors for principal planning; the other four targets are order/admission
  candidates only and do not prove runtime ordering. The lifecycle-anchor schema/target-set
  and principal invalidation policy still need a reviewed gate.
- `scripts/check_player_identity_first_evidence_readiness.py --artifact-root
  /servidor/ark/workspace-offline/player-identity-offline-identity-second-source-20260529T011227Z
  --candidate-root
  /servidor/ark/workspace-offline/player-identity-offline-identity-vanilla-gdb-20260529T012853Z/focal-snapshots
  --json` currently reports `primary_blocker=accepted_lifecycle_anchor_evidence_missing`.
  It can also take `--lifecycle-anchor-candidates-manifest` for the candidate-only
  `obelisk.players-identity-lifecycle-anchor-candidates.v1` artifact. That clears only
  the lifecycle-anchor evidence precondition; the checker must then remain blocked on
  `principal_invalidation_semantics_unresolved` and must keep identity, runtime,
  promotion, and public SDK readiness false.
  A consume-only offline policy/lifecycle bundle now exists at
  `/servidor/ark/workspace-offline/player-identity-principal-invalidation-policy-20260531T231247Z/`.
  Its manifests are accepted by `scripts/validate_offline_artifact_gate.py` in consume
  mode. When both manifests are passed to
  `scripts/check_player_identity_first_evidence_readiness.py`, the current primary blocker
  becomes `approved_runtime_evidence_missing`; this still does not promote identity,
  permissions, commands, runtime readiness, or public SDK readiness.
- Static orientation reports for identity/lifecycle/admin and command response are
  navigation clues only, not consume/promote evidence packs or artifact-gate schemas.
- The current artifact-root audit is summarized in
  `docs/research/2026-05-31-offline-artifact-inventory-audit.md`: usable roots are
  layout-only, evidence-only, or consume-only, command/chat response remains
  orientation-only, and the older `/home/flowcommunity-ark/obelisk-artifacts` route is
  still blocked on a non-protected core plus a complete reflection inventory pack. The
  active `/servidor/ark/workspace-offline` player-identity run has already passed that
  stage and now has distinct second-source layout evidence; it is blocked on accepted
  lifecycle anchors and principal invalidation semantics.
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

- Primary v1 route: player identity now has a staged approved-offline workspace run,
  complete `obelisk.core-dump-evidence-pack.v1`, accepted
  `obelisk.reflection-inventory-pack.v1`, 12/12 candidate fixtures for the
  `players-identity-lifecycle-intake` set, and accepted distinct second-source layout
  evidence from the vanilla-gdb core. The lifecycle-anchor and principal-invalidation
  candidate manifests can now be consumed together; the next blocker is approved runtime
  principal lifecycle evidence. Do not
  rerun the completed admin snapshot, second-source layout, or lifecycle layout routes or
  broad FName/GObjects/core discovery unless a new binary hash or rejected evidence
  requires it. Current recipe:
  `docs/research/2026-05-31-player-identity-offline-pack-preflight.md`. Additional
  lifecycle fixture note:
  `docs/research/2026-06-01-players-lifecycle-anchor-candidates-fixture-gap.md`.
- Demand-map priority from local NextGenPlugins dictionary signals is P0 principal ->
  permissions/admin -> command response; P1 economy/storage/operator
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
- Permissions/admin has machine-readable pre-ABI contracts in
  `docs/permissions_admin_public_contract_decisions.json` and
  `obelisk.permissions-admin-query-failclosed-contract.v1`. The artifact gate may consume
  the query fail-closed contract, but promote/readiness remains blocked as candidate-only;
  public symbols remain empty until copied identity/principal semantics, policy provenance,
  scope/generation, epoch, rate-limit/audit, and v1 sequence gates are resolved.
  The authority model is deliberately conservative: `operator-config` is recognized for
  planning/audit, but only runtime-local/runtime-owned provenance is allow-capable until a
  separate promotion explicitly widens that rule. The checker and artifact gate reject
  nested readiness/promotion overclaims in this candidate contract.
- Plugin Hub seed review requires exactly one package `Support tier: <tier>` declaration
  and rejects unnegated v1/ArkApi/permissions/identity/replies/mutation/storage/module
  support claims outside that tier. Release-supported examples are
  `sdk_minimal_plugin`, `sdk_descriptor_catalog`, and `sdk_timer_plugin`;
  `sdk_inventory_policy_audit` remains experimental. Example source files should fail
  clearly outside Linux x86_64 instead of advertising Windows/MSVC compatibility.
- Plugin cleanup failure policy skips `dlclose`, retains the plugin for retry, and does not repeat plugin shutdown after shutdown already ran.
- Revalidate before any checkpoint: identity readiness with the vanilla-gdb candidate root
  stays blocked on lifecycle-anchor evidence unless an explicit lifecycle-anchor candidate
  manifest is provided; with both lifecycle-anchor and principal-invalidation policy
  manifests it stays blocked on approved runtime evidence. Public SDK v1 completion stays
  blocked, Plugin Hub docs stay non-promotional, and `git diff --check` passes.
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
