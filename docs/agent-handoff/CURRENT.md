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
  process-local owner-token timers. It is not a production-stable `v1.0` claim.
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
- `obelisk.command_chat_response_path.v1` is a named post-v1 planning dependency only. It
  adds no ABI symbols and keeps public `CallProcessEvent`, raw UE pointer/params/FString
  response APIs, replies, send-chat, broadcast/notices, and moderation blocked until a
  future copied owner-token/capability/lifecycle/privacy promotion gate accepts it or a v1
  statement explicitly excludes it.
  Its blocked pre-ABI checklist is `docs/command_chat_response_public_contract_decisions.json`;
  static thunk orientation, passive chat parsing, vtable slots, raw callbacks, and legacy
  CallProcessEvent remain insufficient evidence.
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
- `scripts/check_player_identity_first_evidence_readiness.py --artifact-root
  /home/flowcommunity-ark/obelisk-artifacts --json` currently reports
  `next_actionable_blocker.code=non_protected_core_input_missing`; the expected copied
  core path pattern is
  `/home/flowcommunity-ark/obelisk-artifacts/player-identity-offline-<run-id>/raw/core`.
- Player identity focal snapshot planning must start from a complete non-protected
  `obelisk.reflection-inventory-pack.v1` with target-set coverage for the full 12-target
  `players-identity-lifecycle-intake` set and exact rows for
  `ShooterPlayerController.ServerListPlayers` and
  `ShooterPlayerController.ServerKickPlayer`. After that pack is reviewed, plan exactly
  those two targets; do not use `--target-set players-identity-lifecycle-intake` with
  `scripts/plan_ufunction_focal_snapshots.py`.
- Static orientation reports for player identity, player identity lifecycle/admin thunks,
  and command/chat response are explicitly not offline artifact-gate schemas. They must
  fail closed both as `--manifest` inputs and as `--artifact` inputs even with valid
  provenance sidecars; they are navigation clues only, not consume/promote evidence packs.
- The current artifact-root audit is summarized in
  `docs/research/2026-05-31-offline-artifact-inventory-audit.md`: usable roots are
  layout-only, evidence-only, or consume-only, command/chat response remains
  orientation-only, and player identity is still blocked on a non-protected core plus a
  complete reflection inventory pack.
- Inventory, structures, missions, transfers, dinos, buffs, tribes, ResourceHandle, and
  GObjects remain internal/candidate unless promoted through their own copied ABI, privacy,
  lifecycle, and evidence gates. While identity waits on copied core evidence, inventory
  copied signals are the higher-value side lane; structure census remains useful offline
  planning/consume-only work. Neither side lane displaces identity -> permissions/admin
  -> commands/replies. Do not restart broad FName, GObjects, or core scans for
  ResourceHandle. Strict serial policy remains candidate-only; ResourceHandle public
  lookup remains blocked and does not unlock public handles.
- Static field-window evidence clears only the static coherent field-window packaging
  blocker, supports `obelisk.fuobjectarray-field-window-redacted.v1` as a durable
  normalized artifact-pack child manifest in consume mode only, and is not a `v1.0` SDK
  blocker, route shortcut, or completion signal. CMake package target are present as
  package-shape evidence only, not a `v1.0` completion marker.

## Priority Next Steps

- Keep player identity as the primary route: obtain or approve a non-protected copied core
  under `/home/flowcommunity-ark/obelisk-artifacts/player-identity-offline-<run-id>/raw/`.
  If starting from explicit non-protected binary/core files, use
  `scripts/prepare_player_identity_offline_raw_layout.py` only to stage those existing
  inputs, then build `obelisk.core-dump-evidence-pack.v1`, then the full 12-target
  `obelisk.reflection-inventory-pack.v1` with the reviewed ARK binary SHA, then plan only
  `ServerListPlayers` and `ServerKickPlayer` focal snapshots. Current artifact audit:
  the matching offline binary exists under `/home/flowcommunity-ark/obelisk-artifacts`,
  but no core file or `player-identity-offline-*` run directory exists there; no command
  can advance the identity pack until a regular non-symlink non-protected core input is
  available. Player identity next step is to produce or approve a non-protected UFunction
  reflection-inventory pack with `target_set_coverage` for the full 12-target
  `players-identity-lifecycle-intake` set. do not treat ScriptStruct inventory, standalone
  snapshots, redacted signatures, static thunks, or a two-function-only inventory as
  satisfying this lane; use `scripts/plan_ufunction_focal_snapshots.py` for
  `ShooterPlayerController.ServerListPlayers` and
  `ShooterPlayerController.ServerKickPlayer` only. The exact current command recipe lives
  in `docs/research/2026-05-31-player-identity-offline-pack-preflight.md`; older
  2026-05-27 core/dump notes are historical evidence and are not runnable promotion
  instructions.
- Demand-map priority from local NextGenPlugins dictionary signals is P0:
  player identity, commands/replies/response path, and permissions/admin. P1:
  economy/storage/operator ingress, inventory/items mutation, and structure/build policy.
  P2: dinos/tribes/missions/transfers unless stronger demand appears. This priority map
  does not authorize copying ArkApi/NextGenPlugins implementation details.
- If no copied core is available, keep progressing offline by tightening guardrails,
  permission/admin query-only minimum design, command/principal contract, inventory
  copied-signal evidence hygiene, and structure census consume/promote-blocked checks
  without claiming SDK promotion. Prefer inventory copied-signal hygiene over structure
  census when choosing one side lane, because it has more near-term Plugin Hub value while
  identity remains core-blocked. Keep that work experimental and non-completion. This
  does not authorize Transfer runtime work.
- Current no-core side-lane priority: `item-return-only-policy-slice` is the best
  value/risk target set because it already has release-readiness classification,
  fixture coverage, and second-source layout evidence behind existing
  `GameplayPolicyEvent` event kinds. It still must be described only as copied
  `ReturnValue` signal evidence; it does not promote an Inventory SDK, Items SDK,
  identity, lookup, mutation, return override, runtime validation, or v1 completion.
- Keep `obelisk.command_chat_response_path.v1` as orientation-only until identity and
  permissions/admin are promoted and a copied response contract exists. The current static
  checker is useful for later target matching, but it must not become public ABI or
  runtime work by itself. Its portable unit coverage now uses a synthetic ELF fixture;
  the reviewed real-binary check is optional smoke/evidence only.
  The companion thunk note
  `docs/research/2026-05-31-command-chat-response-thunk-orientation.md` records candidate
  vtable slots `0x19d0`, `0x1790`, and `0x1788` for the reviewed binary only; it is
  navigation evidence and does not unlock replies, send-chat, identity, permissions,
  runtime testing, artifact-gate input, or public SDK promotion.
- Permissions/admin now has a machine-readable pre-ABI decision contract in
  `docs/permissions_admin_public_contract_decisions.json`. Future permission checks must
  consume promoted copied principal semantics with generation/scope fail-closed behavior;
  do not add public permission ABI symbols before that contract is resolved. Public
  permission cache ABI is blocked until `policy_epoch` plus full principal
  generation/scope keying semantics are promoted; no `allow` decision is valid without
  runtime-owned policy source/authority provenance, and permission queries need
  owner-scoped rate-limit/audit gates. Current public header symbols remain an explicit
  empty set. `v1_sequence_gate` entries keep identity -> permissions -> command response
  -> commands/replies ordered and keep downstream storage/admin/replies/ingress out.
- Plugin Hub seed review now mechanically requires exactly one `Support tier: <tier>`
  declaration in seed README/package/public docs and rejects unnegated claims for v1,
  ArkApi/AseApi compatibility, commands, permissions, identity, send-chat/replies,
  mutation, storage, inventory, or structure support outside that tier. Public v1
  completion evidence also rejects strict blocker evidence paths/schemas that are
  candidate/planning/orientation/preflight/readiness/consume-only/evidence-only.
- Installed-SDK contributor examples now include `examples/sdk_minimal_plugin`,
  `examples/sdk_descriptor_catalog`, and `examples/sdk_timer_plugin`. Use
  `examples/sdk_descriptor_catalog` as the external scaffold for descriptor/catalog
  readers; `plugins/oDescriptorCatalog` remains the in-tree runtime reference plugin, not
  the external package scaffold.
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
