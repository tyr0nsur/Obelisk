# Current Agent Handoff

This file is an active routing table only. Durable evidence belongs in `docs/research/`,
resume facts in `COMPACT_CONTEXT.md`, and old detail in `HISTORY-*.md`. Historical
recovery context is not active routing; use `git log --oneline -1` for the checkpoint.

## Active Objective

- `v0.1.0-rc.2` is the current published core-first RC baseline: Linux runtime,
  ProcessEvent hook, plugin lifecycle, central install layout, `oBaseEvents`,
  `GameplayPolicyEvent`, minimal copied `ChatMessageEvent`, descriptors, timers, and
  refreshed RC evidence.
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
- ArkServerApi/AseApi and local `NextGenPlugins` clones are names and demand dictionaries
  only, not a behavior map, not a porting target, and not a copying source.
  Do not copy code, offsets, layouts, vtables, ABI assumptions. Do not copy wrappers, raw UE pointer
  APIs, constants, schemas, control flow, command parsers, return constants, return
  semantics, or implementations.

## Current Routing Facts

- RC public scope remains limited to `GameplayPolicyEvent`, minimal copied
  `ChatMessageEvent`, `DescribeResourceKind`, `DescribeGameplayPolicyEventKind`, and
  process-local owner-token timers. It is not a production-stable `v1.0` claim.
- Current post-RC focus: preserve the accepted RC UFunction second-source root as release
  evidence while moving toward copied-data v1 SDK blockers.
- Published RC state used a clean release gate and exact tag/ref verification. Treat stale
  local tags as invalid until revalidated against the intended ref; stale local tags must
  not be reused or pushed.
- `docs/public_sdk_surfaces.json::v1_sdk_completion_blockers` is the active blocker list
  for a complete SDK claim. Player identity, permissions/admin, commands/replies,
  inventory/items mutation, structure census/build policy, mission/transfer/dino/tribe,
  player services/economy/mobility, operator ingress/storage, and lifecycle ops recovery
  remain unresolved unless promoted or explicitly excluded in a reviewed v1 release
  statement.
- `scripts/check_public_sdk_v1_completion.py --json` intentionally reports blocked on the
  current tree. Do not use broad phrases like `v1.0 stable`, `complete SDK`, `full SDK`,
  or `production SDK` in public sinks unless that gate allows the stable SDK claim.
- The public SDK completion checker now also blocks promoted commands/replies or
  permissions/admin claims when their dependency rows are not promoted, and promoted
  player identity must name `obelisk.core-dump-evidence-pack.v1`,
  `obelisk.reflection-inventory-pack.v1`, `ServerListPlayers`, and `ServerKickPlayer`
  evidence terms.
- `ObeliskApi` v1 remains append-only. New public surfaces require copied-data ownership,
  capability and `struct_size` gates, lifecycle cleanup, privacy rules, accepted evidence,
  ABI tests, and installed SDK consumer tests.
- `CallProcessEvent` remains ABI-present only as an init-window debug escape hatch: the
  current plugin owner is inside `ObeliskPlugin_Init`, must have captured
  `OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT`, and the live gate must still be active.
  Post-init calls through captured API tables are unsupported; a future replacement
  owner-token ABI is required.
- Process-local owner-token timers are core primitives with explicit unregister. They are
  not gameplay/module timer APIs, shared scheduler state, UE identity, or persistent
  handles.
- Plugin unload/init-failure cleanup skips `dlclose` when callback cleanup cannot be
  proven complete, retains the plugin for retry, and does not repeat plugin shutdown on
  retry. Dispatcher families with owner cleanup must be covered by
  `PluginManager::UnregisterPluginCallbacks`.
- `oDescriptorCatalog` and Plugin Hub foundation work are metadata/contributor seeds only:
  lifecycle/config/logging, descriptor/catalog, and process-local timers are
  release-supported seed lanes; copied chat/policy stays experimental. Foundation work is
  not a substitute for v1 blockers.
- `docs/PLUGIN_HUB_CONTRIBUTOR_PATH.md` is the short contributor path. Guardrails cover it
  as public SDK wording so it cannot imply ArkApi compatibility, production Plugin Hub
  modules, identity, permissions, commands, inventory/structure SDKs, mutation, or v1
  completion.
- Chat/commands near-term value remains plugin-local parsing over copied
  `ChatMessageEvent`. Do not promote a public command router, replies, send-chat,
  moderation, or player permissions until copied player identity, permissions, and a safe
  response path are separately promoted.
- Future command/principal routing is a new copied C ABI lifecycle/callback-ownership
  surface, not a parser-only extension. Current planning note:
  `docs/research/2026-05-31-commands-principal-routing-contract.md`.
- Player identity is the first v1 dependency for permissions, commands, economy,
  moderation, and several ownership-sensitive module APIs. The target set is 12-target
  `players-identity-lifecycle-intake`; it remains planning-only and candidate-only.
- Current player-identity state: the artifact root has the matching offline
  `ShooterGameServer` SHA `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`,
  but no non-protected copied core, no complete `obelisk.core-dump-evidence-pack.v1`, and
  no accepted `obelisk.reflection-inventory-pack.v1`.
- Player identity now has a candidate-only privacy/invalidation contract in
  `docs/research/2026-05-31-player-identity-privacy-invalidation-contract.md` and
  machine-readable decision guardrails. Future principals must be opaque copied values,
  generation/invalidation-aware, process-local by default, and fail closed; this does not
  promote `obelisk.player_identity.v1`, lookup, persistence, platform ids, names,
  `ResourceHandle`, or UE pointers.
- `scripts/check_player_identity_first_evidence_readiness.py --artifact-root
  /home/flowcommunity-ark/obelisk-artifacts --json` currently reports
  `next_actionable_blocker.code=non_protected_core_input_missing`; the expected copied
  core path pattern is
  `/home/flowcommunity-ark/obelisk-artifacts/player-identity-offline-<run-id>/raw/core`.
- `scripts/prepare_player_identity_offline_raw_layout.py` may stage explicit
  non-protected offline `ShooterGameServer` and core inputs into the raw sibling layout
  under `/home/flowcommunity-ark/obelisk-artifacts/player-identity-offline-<run-id>/`.
  It does not create or approve cores, touch protected server paths, or authorize server
  access or runtime/core changes; follow the full recipe in
  `docs/research/2026-05-31-player-identity-offline-pack-preflight.md`.
- Player identity focal snapshot planning must start from a complete non-protected
  `obelisk.reflection-inventory-pack.v1` with target-set coverage for the full 12-target
  `players-identity-lifecycle-intake` set and exact rows for
  `ShooterPlayerController.ServerListPlayers` and
  `ShooterPlayerController.ServerKickPlayer`. After that pack is reviewed, plan exactly
  those two targets; do not use `--target-set players-identity-lifecycle-intake` with
  `scripts/plan_ufunction_focal_snapshots.py`.
- Player identity next step is to produce or approve a non-protected UFunction
  reflection-inventory pack with `target_set_coverage` for the full 12-target
  `players-identity-lifecycle-intake` set. do not treat ScriptStruct inventory,
  standalone snapshots, redacted signatures, static thunks, or a two-function-only
  inventory as satisfying this lane. After acceptance, use
  `scripts/plan_ufunction_focal_snapshots.py` for
  `ShooterPlayerController.ServerListPlayers` and
  `ShooterPlayerController.ServerKickPlayer` only.
- Static orientation for all 12 identity targets and bounded admin thunk byte checks are
  valid navigation evidence only. They do not replace the missing core evidence pack,
  reflection inventory, focal snapshots, second source, lifecycle anchors, or
  accepted privacy/invalidation implementation and tests.
- `PrimalLocalProfile.ArkTributePlayerData` is metadata/layout evidence only. The
  `scripts/check_arktribute_playerdata_identity_boundary.py` checker proves only that the
  current transfer ScriptStruct artifacts remain layout-only, candidate-only,
  promote-blocked, and non-public.
- Static field-window evidence only cleared the field-window packaging blocker. It is not
  a `v1.0` SDK blocker, route shortcut, or completion signal; CMake package target are
  present, but package-shape evidence only, not a `v1.0` completion marker. The gate
  supports `obelisk.fuobjectarray-field-window-redacted.v1` as a durable normalized
  artifact-pack child manifest in consume mode only.
- Item return-only policy has three public `GameplayPolicyEvent` `ReturnValue` kinds only;
  no public Inventory SDK, Items SDK, identity, mutation, or return override is promoted.
- Mission copied-bool evidence keeps exact bool-tail metadata:
  `bool_field_size=1`, `bool_byte_offset=0`, `byte_mask=0x01`, `field_mask=0xff`, and
  `native_bool=false`. Consume mode accepts; promote mode blocks, with promotion ready:
  `false`.
- ResourceHandle/public GObjects remain blocked: old flag-policy artifact is obsolete,
  durable rich-provenance refresh is preserved, Consume mode accepts it and promote mode
  stays blocked, post-callback rejection contract is preserved as candidate-only, and the first strict serial reuse/wraparound policy artifact is
  preserved. manifest consume mode accepts it and promote mode blocks it as candidate-only;
  it does not unlock runtime negative samples, public lookup, object identity, persistent
  handles, mutation, return override, or ResourceHandle semantic helper predicate work
  beyond fail-closed planning.
- The next strict ResourceHandle blocker is rejected runtime object samples plus runtime
  serial reuse/wraparound semantics. Future work needs a future-runtime-observation-plan
  and an operator-approved live-ops brief names the exact debug target. Do not rerun broad
  FName, GObjects, or core scans for ResourceHandle; Do not replace this with another
  broad offline FName/GObjects scan.
- Structure, Inventory item-return, Mission, Transfer, Dino, Buff, Tribe, and
  ResourceHandle lanes stay internal/candidate unless promoted through their own copied
  ABI, privacy, lifecycle, and evidence gates. Structure census is a useful offline side
  lane, but identity -> permissions/admin -> commands/replies is the highest-impact v1
  unblock route.

## Priority Next Steps

- Keep player identity as the primary route: obtain or approve a non-protected copied core
  under `/home/flowcommunity-ark/obelisk-artifacts/player-identity-offline-<run-id>/raw/`.
  If starting from explicit non-protected binary/core files, use
  `scripts/prepare_player_identity_offline_raw_layout.py` only to stage those existing
  inputs, then build `obelisk.core-dump-evidence-pack.v1`, then the full 12-target
  `obelisk.reflection-inventory-pack.v1`, then plan only `ServerListPlayers` and
  `ServerKickPlayer` focal snapshots.
- If no copied core is available, keep progressing offline by tightening guardrails,
  permission/admin query-only minimum design, command/principal contract, and structure
  census side-lane consume/promote-blocked checks without claiming SDK promotion. This
  does not authorize Transfer runtime work.
- Permissions/admin now has a machine-readable pre-ABI decision contract in
  `docs/permissions_admin_public_contract_decisions.json`. Future permission checks must
  consume promoted copied principal semantics with generation/scope fail-closed behavior;
  do not add public permission ABI symbols before that contract is resolved.
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
