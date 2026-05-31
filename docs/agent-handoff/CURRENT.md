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
  for a complete SDK claim; all blocker rows remain unresolved unless promoted or
  explicitly excluded in a reviewed v1 release statement.
- `scripts/check_public_sdk_v1_completion.py --json` intentionally reports blocked on the
  current tree. Do not use broad phrases like `v1.0 stable`, `complete SDK`, `full SDK`,
  or `production SDK` in public sinks unless that gate allows the stable SDK claim.
  The checker also enforces canonical `stable_release_contract.claim_requires` and
  `not_sufficient` clauses so Plugin Hub package shape, RC readiness, and copied-data
  seeds cannot become sufficient evidence by manifest drift.
- `oDescriptorCatalog` and Plugin Hub foundation work are metadata/contributor seeds only,
  not substitutes for v1 blockers. Installed SDK examples are Linux x86_64 only.
- `obelisk.command_chat_response_path.v1` is post-v1 planning only and adds no ABI today.
  Replies/send-chat/broadcast/moderation stay blocked; static thunks, passive chat,
  vtable slots, raw callbacks, and legacy `CallProcessEvent` are insufficient.
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
- Candidate lifecycle layouts are reproducible for all six
  `players-lifecycle-anchor-candidates` targets, but remain planning-only. The narrow
  candidate anchors are `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout`;
  the other four targets do not prove runtime ordering. Details:
  `docs/research/2026-06-01-players-lifecycle-anchor-candidates-fixture-gap.md`.
- `scripts/check_player_identity_first_evidence_readiness.py` without extra manifests still
  reports `primary_blocker=accepted_lifecycle_anchor_evidence_missing`. With the consume-only
  lifecycle and principal-policy manifests from
  `/servidor/ark/workspace-offline/player-identity-principal-invalidation-policy-20260531T231247Z/`,
  the primary blocker becomes `approved_runtime_evidence_missing`. The emitted
  `first_evidence.runtime_principal_lifecycle_evidence` block is requirements-only, not
  accepted evidence or promotion. The optional
  `--runtime-principal-lifecycle-evidence-manifest` input accepts only a synthetic/redacted
  shape fixture; it still leaves `approved_runtime_evidence_missing` in place.
- Static orientation reports for identity/lifecycle/admin and command response are
  navigation clues only, not consume/promote evidence packs or artifact-gate schemas.
- The current artifact-root audit is summarized in
  `docs/research/2026-05-31-offline-artifact-inventory-audit.md`; the active
  `/servidor/ark/workspace-offline` player-identity run has passed the old artifact-root
  stage and is blocked only on approved runtime principal lifecycle evidence.
- Inventory, structures, missions, transfers, dinos, buffs, tribes, ResourceHandle, and
  GObjects remain internal/candidate. Do not rerun broad FName, GObjects, or core scans for
  ResourceHandle; its next strict blockers are rejected runtime object samples plus runtime
  serial reuse/wraparound semantics under an operator-approved live-ops brief.
- Static field-window evidence clears only the field-window packaging blocker, is not a
  `v1.0` SDK blocker, route shortcut, or completion signal. CMake package target are
  present as package-shape evidence only, not a `v1.0` completion marker.

## Priority Next Steps

- Primary v1 route: player identity has accepted offline/core/reflection inventory,
  12/12 candidate fixtures for the exact 12-target `players-identity-lifecycle-intake`
  set, distinct second-source layout evidence, and consume-only lifecycle/principal
  manifests. Next blocker: approved runtime principal lifecycle evidence. Do not rerun the
  completed admin snapshot, second-source layout, lifecycle layout, or broad discovery
  routes unless a new binary hash or rejected evidence requires it.
- Demand-map priority from local NextGenPlugins dictionary signals is P0 principal ->
  permissions/admin -> command response; P1 economy/storage/operator
  ingress, inventory/items mutation, and structure/build policy; P2 dinos/tribes/
  missions/transfers. Do not copy ArkApi/NextGenPlugins implementation details.
- No-core fallback: keep progress offline through guardrails, permission/admin query-only
  design, command/principal contract, and inventory copied-signal hygiene. Inventory copied
  signals are the higher-value side lane, but do not displace identity -> permissions/admin
  -> commands/replies or authorize Transfer runtime work.
- Current no-core side-lane: `item-return-only-policy-slice` has three copied
  `GameplayPolicyEvent` `ReturnValue` checks and accepted descriptor reconciliation; it
  does not promote Inventory/Items SDK, identity, mutation, return override, or v1.
- v0.2 internal hardening lane: Mission copied-bool is internal/default-off only, not a
  Plugin Hub module or Mission SDK claim. Detail:
  `docs/research/2026-05-31-v02-module-priority.md`.
- Product-planning lane: Structure aggregate/census is planning/consume-only with no
  runtime observer, public StructureEvents SDK, enforcement, return override, or v1 claim.
  Exact build-policy target names stay out of public docs/ABI/descriptors until promoted.
- Command/chat response static orientation is complete for the reviewed binary but remains
  orientation-only until identity, permissions/admin, and a copied response contract exist.
- Permissions/admin pre-ABI contracts remain candidate-only. Public symbols stay empty
  until copied identity/principal semantics, provenance, scope/generation, epoch,
  rate-limit/audit, and v1 sequence gates are resolved. `operator-config` is recognized
  for planning/audit but is not allow-capable.
- Plugin Hub seed review requires exactly one package `Support tier: <tier>` declaration
  and rejects unnegated v1/ArkApi/permissions/identity/replies/mutation/storage/module
  support claims outside that tier.
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
