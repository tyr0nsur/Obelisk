# Current Agent Handoff

This file is an active routing table only. Durable evidence belongs in
`docs/research/`, resume facts in `COMPACT_CONTEXT.md`, and old detail in
`HISTORY-*.md`. Historical recovery context is not active routing; use
`git log --oneline -1` for the checkpoint.

## Active Objective

- `v0.1.0-rc.2` is the current published core-first RC baseline after a clean release gate
  and tag/ref verification; stale tags must not be reused. RC public scope remains limited
  to `GameplayPolicyEvent`, minimal copied `ChatMessageEvent`, `DescribeResourceKind`, and
  `DescribeGameplayPolicyEventKind`. Post-RC work moves toward `v1.0`: a complete public
  SDK contract for plugin authors, not just a stable runtime. The v1 claim is blocked; do
  not use complete/full/production/stable SDK wording unless
  `scripts/check_public_sdk_v1_completion.py --json` allows it.
- Current post-RC focus: use the accepted RC UFunction second-source root and release
  baseline as evidence without treating historical recovery context as active routing or
  implying v1 completion.
- The active P0 spine is `docs/public_sdk_surfaces.json::v1_required_dependency_chain`:
  `obelisk.player_identity.v1`, `obelisk.permissions_admin.v1`,
  `obelisk.command_chat_response_path.v1`, and `obelisk.commands_replies.v1`. This chain
  is promoted-only for a complete SDK claim; excluded/post-v1 results are scoped
  non-complete bookkeeping.
- Current SDK accounting is intentionally blocked: complete-SDK progress remains `0/12`
  and P0 promoted count remains `0/4`. The next promoted work starts with approved copied
  runtime principal lifecycle evidence, then the reviewed player-identity public contract,
  permissions/admin, command response, and commands/replies.

## Hard Overrides

- GitHub publication is lead-only. GitHub work may be delegated only for an evidenced, stable milestone; this handoff does not authorize push, tag, release-ref updates, rebase, or routine publication.
- No tag or release-ref push may occur without release-manager/lead authorization for the
  current-turn release scope.
- No server target has standing approval. Server-backed debug/beta work requires a current
  approved live-ops brief naming instance/map, feature gates, marker/env changes,
  start/restart/stop window, notice path when players are involved, evidence capture, and
  rollback. Request-pack, preflight, and planning acceptance are not runtime approval and
  do not authorize marker/env changes, starts/restarts/stops, runtime capture, Discord,
  public SDK readiness, runtime readiness, or v1 completion. Technical progress is only a
  reason to request a scoped run.
- The lead retains server-safety decisions.
- no Discord for internal rounds or agent status; no Discord for routine validation or
  speculative reversing notes. Discord drafts or sends require explicit current-turn
  approval for approved public modder-facing milestones or operator-approved beta-test
  windows, must use `OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL` or
  `OBELISK_BETA_TEST_WEBHOOK_URL`, and must dry-run through `scripts/send_discord_embed.py`
  before any approved send. Always dry-run before any approved send; use embeds.
- ArkServerApi/AseApi and local `NextGenPlugins` clones are names and demand signals only,
  not architecture, ergonomics, behavior maps, porting targets, or copying source. Do not
  copy code, offsets, layouts, vtables, ABI assumptions, wrappers, raw UE pointer APIs,
  command parsers, return semantics, or implementations.
- Runtime posture is default-deny for filtered/global raw `ProcessEvent`, public
  `CallProcessEvent`, ProcessEvent blocking, broad tracing, ReflectionScanner, debug
  controls, and observers unless the matching approved env+marker pair is enabled for a
  scoped debug window.
- `CallProcessEvent` remains an init-window debug escape hatch only: the current plugin
  owner is inside `ObeliskPlugin_Init`, has `OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT`,
  and Post-init calls through captured API tables are unsupported until a future
  replacement must carry an owner-token ABI.
- PluginManager unload cleanup skips `dlclose`, retains the plugin for retry, and does not repeat plugin shutdown when plugin-owned callback cleanup fails.

## Current Routing Facts

- Plugin Hub is post-SDK-complete planning only. Do not route active rounds to Plugin Hub
  examples, packaging, intake tooling, or package hardening while SDK blockers remain open.
- Command/permission routing is planning-only. `planning_layout_gate.ready=true` on command
  response layout does not promote reply/send-chat ABI, command router, public header, ABI,
  SDK, runtime readiness, public SDK readiness, or v1 completion.
  The route gate recursively scans sub-checker reports for public/runtime aliases and
  positive text claims; a leaf `valid=true` is not enough if it reports public
  reply/send-chat, command routing, permissions/admin, ABI, runtime, or v1-completion
  readiness.
- Player identity is first. The exact 12-target `players-identity-lifecycle-intake` set
  includes `ShooterPlayerController.ServerListPlayers` and
  `ShooterPlayerController.ServerKickPlayer`; do not replace exact focal targets with a
  broad target-set plan.
- Current player-identity offline evidence is accepted for planning: complete
  `obelisk.core-dump-evidence-pack.v1` from a non-protected source, accepted
  `obelisk.reflection-inventory-pack.v1`, 12/12 candidate fixtures, accepted distinct
  second-source layout evidence from the vanilla-gdb core, and consume-only
  lifecycle-anchor and principal-invalidation manifests. The lifecycle-anchor and
  principal-invalidation manifests are accepted for consume-only planning. Promotion
  remains false; the next identity blocker is approved runtime principal lifecycle
  evidence. Do not rerun the completed admin snapshot, second-source layout, or lifecycle
  layout routes.
- Current recipe:
  `docs/research/2026-05-31-player-identity-offline-pack-preflight.md`.
- The old `20260601T120000Z-player-principal-lifecycle` request-pack is expired and should
  report `approved_window_expired`, `request_pack_ready=false`, and `bundle_inputs_ready=false`.
  It is not runtime evidence. Missing runtime artifacts remain copied `Obelisk.log`,
  checked `window-manifest.env`, runtime observer summary, and an approved runtime
  principal lifecycle evidence manifest.
- Inventory/item copied signals are a no-core side lane only. They may expose three
  copied `ReturnValue` gameplay policy events through `GameplayPolicyEvent`, but this is
  not public Inventory SDK, Items SDK, identity, mutation, return override, lookup,
  `ResourceHandle`, runtime readiness, or v1 completion evidence.
- process-local owner-token timers are core scheduling only with explicit unregister, not
  gameplay/module timer APIs, persistent handles, UE identity, or shared scheduler state.
- The field-window packaging blocker clears only package-shape evidence once the CMake
  package target are present; it is not a `v1.0` SDK blocker, route shortcut, or completion
  signal. Installed SDK/package checks are package-shape evidence only, not a `v1.0`
  completion marker.
- Inventory action targets stay redacted/metadata-only: `AdditionalData` is action
  metadata, `ExposesRange=false`, no copied integer range, no dispatch, no public
  Inventory SDK, and no public Items SDK.
- Mission copied-bool is internal reusable evidence only. `mission-copied-bool-policy-slice`
  consume mode accepts and promote mode blocks; exact bool tail is `bool_field_size=1`,
  `bool_byte_offset=0`, `byte_mask=0x01`, `field_mask=0xff`, and `native_bool=false`.
  Preserve exactly three copied targets, five copied bool fields, six redacted fields, and
  `MissionType.GetPlayerUsableItems` recognition-only with copied bool count `0`.
- Structure build-policy offline intake is accepted only as planning layout for
  `PrimalStructure.IsAllowedToBuild`, `PrimalStructure.BPIsAllowedToBuild`, and
  `PrimalStructure.BPIsAllowedToBuildEx`; no Structure SDK, enforcement, runtime readiness,
  mutation, return override, identity/lookup, `ResourceHandle`, or v1 completion. The
  checker rejects protected/symlink snapshot paths, non-sibling `base/`/`candidate/`
  roots, raw address leaks, and value-bearing keys on redacted/layout-only fields.
  `obelisk.structure-build-policy-offline-attestation.v1` is a consume-only artifact-gate
  schema for this planning evidence; it must include the checker report schema
  `obelisk.structure-build-policy-offline-intake-check.v1` and promote mode remains
  blocked.
- ResourceHandle/public GObjects remain blocked. old flag-policy artifact is obsolete;
  durable rich-provenance refresh is preserved; Consume mode accepts it and promote mode
  stays blocked; post-callback rejection contract is preserved as candidate-only; first
  strict serial reuse/wraparound policy artifact is preserved; manifest consume mode
  accepts it and promote mode blocks it as candidate-only. This does not unlock runtime
  negative samples, public lookup, object identity, mutation, or fail-closed semantic
  helper promotion. Do not rerun broad FName, GObjects, or core scans for ResourceHandle.
  Do not replace this with another broad offline FName/GObjects scan. The next strict
  ResourceHandle blocker is rejected runtime object samples plus runtime serial
  reuse/wraparound semantics with a future-runtime-observation-plan only after an
  operator-approved live-ops brief names the exact debug target.
- Transfer `bAccept` and transfer planning does not authorize Transfer runtime work.

## Priority Next Steps

- P0: produce approved copied runtime principal lifecycle evidence from an approved,
  copied, redacted observer log; then review the public identity contract before any
  permissions/admin, command response, or commands/replies ABI.
- Offline: keep tightening guardrails around permissions/admin query-only provenance,
  command/principal contracts, command route drift, inventory copied-signal hygiene, and
  structure build-policy snapshot envelopes.
- Offline artifact gates: keep tightening consume-vs-promote overclaim checks for
  ResourceHandle, Mission copied-bool, and Structure planning slices. Consume acceptance
  must not imply public SDK, runtime readiness, mutation, return override, lookup,
  post-callback handles, or v1 completion.
- ResourceHandle: wait for rejected runtime object samples plus runtime serial
  reuse/wraparound semantics from an approved live-ops brief; offline/core artifacts cannot
  synthesize that blocker away.
- Demand-map priority from NextGenPlugins names is P0 principal -> permissions/admin ->
  command response; P1 economy/storage/operator ingress, inventory/items mutation, and
  structure/build policy; P2 dino/tribe/buff-status/mission/transfer leaves. Names are
  demand signals only.

## Agent Protocol

- Delegated sub-agents get only the scoped objective, safety baseline, allowed paths,
  required skills, expert role, expected decision, and edit permission needed for their
  task; pass only the skills needed for that scope.
- Do not pass leader-only cadence, active-goal framing, community policy, or unrelated
  module history unless it changes the worker's concrete task.
- Sub-agents must not commit, amend, rebase, tag, push, update GitHub state, touch servers,
  send Discord updates, or broaden live-ops scope unless explicitly delegated for the
  current turn.
- Sub-agents are not alone in the codebase: do not revert unrelated changes; leave edits
  unstaged/uncommitted and report touched paths, validations, and risks.
