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
  and P0 promoted count remains `0/4`. The official complete-SDK claim is still `0%`;
  the technical foundation is estimated at roughly `20-25%` because RC core/runtime,
  copied events, offline intake tooling, and several consume-only module slices exist but
  the required public SDK dependency chain has no promoted rows. The next promoted work
  starts with approved copied runtime principal lifecycle evidence, then the reviewed
  player-identity public contract, permissions/admin, command response, and
  commands/replies.

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

- 2026-06-02 post-compaction reorganization checkpoint: the lead reran the canonical
  offline checks from the current worktree. `PYTHONDONTWRITEBYTECODE=1 python3
  scripts/check_command_permission_route_gate.py --json` passes as planning-only with
  `approved_runtime_evidence_missing`; `PYTHONDONTWRITEBYTECODE=1 python3
  scripts/check_public_sdk_v1_completion.py --json` still fails closed with
  `stable_claim_allowed=false`, complete-SDK progress `0/12`, and P0 progress `0/4`;
  `PYTHONDONTWRITEBYTECODE=1 python3
  scripts/check_inventory_item_copied_signals_stability.py --json` passes with five
  allowed copied inventory/item signals while keeping public SDK/v1 completion false; and
  `PYTHONDONTWRITEBYTECODE=1 python3
  scripts/check_object_identity_resource_handle_public_contract_readiness.py --json`
  passes as planning-only with ResourceHandle/object identity still blocked. See
  `docs/research/2026-06-02-sdk-complete-priority-map.md`.
- Follow-up hardening in the same checkpoint tightened planning-only child posture in the
  command/permission route gate, inventory copied-signal required flags across decisions
  and `docs/public_gameplay_events.json`, and request-pack privacy/readiness negation
  scanning. These guardrails do not change runtime approval, public SDK readiness, or v1
  completion.
- 2026-06-02 P0 route hardening follow-up: permissions/admin public readiness now rejects
  fabricated query fail-closed reports without the checker-emitted contract fingerprint and
  rejects top-level permissions/admin promotion/sequence drift in
  `docs/public_sdk_surfaces.json`. Command response and commands/replies readiness scanners
  now distinguish mixed positive claims after `but/then/however` from legitimate
  `before/until/only/never` non-claims. Commands/replies public readiness now requires the
  exact composed `command_chat_response_public_readiness` report and rejects raw
  `obelisk.reflection-snapshot-readiness.v1` as a dependency artifact. Route gate remains
  planning-only and still blocks at `approved_runtime_evidence_missing`.
- 2026-06-02 identity/permissions evidence-gate hardening: the permissions/admin
  query fail-closed checker now rejects ABI order drift and duplicates for query fields,
  decision fields/results, fail-closed cases, and reason flags, including flag-name to
  bit-index drift. Permissions/admin public readiness now fingerprints the sequence-aware
  report. Player-identity first-evidence request diagnosis preserves observer env parse
  blockers, and the runtime window-manifest checker no longer reads protected or
  non-approved request-pack paths while trying to validate sidecars. Validation passed
  with the P0 route suite; route gate remains planning-only and SDK completion still fails
  closed at `stable_claim_allowed=false`, P0 `0/4`, and complete SDK `0/12`.
- 2026-06-02 follow-up guardrails: permissions/admin public readiness now enforces
  cache key sequence, blocked public cache ABI, cache invalidation semantics, manifest
  public-header path matching, protected/symlink public-header rejection, and additional
  permissions/admin header aliases. SDK v1 completion now rejects all demand-family
  equivalents unless an explicit reviewed allowlist names the blocker/equivalent pair;
  the allowlist is intentionally empty. ResourceHandle readiness now scans the
  `obelisk.object_identity_resource_handle.v1` surface row for positive public
  ResourceHandle/object lookup/post-callback claims, not only public gameplay events.
  Route gate remains planning-only with `approved_runtime_evidence_missing`; SDK
  completion remains fail-closed at `stable_claim_allowed=false`, P0 `0/4`, and complete
  SDK `0/12`.
- 2026-06-02 approved-evidence and Mission frontier hardening: approved player-identity
  runtime evidence now replays the operational `window-manifest.env` and compares the
  replayed operational-window projection against the embedded report, so mutated
  manifest/request/env/preflight sidecars fail even if their SHA and artifact identity are
  refreshed. The replay tolerates only an expiry-only request-window blocker for already
  captured evidence; target/window/env/preflight drift still fails. Mission copied-bool
  readiness now scans nested `CMakeLists.txt` and `*.cmake` files outside ignored
  build/local/cache roots so nested CMake runtime/shared wiring cannot over-attest the
  consume-only Mission frontier.
- 2026-06-02 commands/replies response-path provenance hardening: standalone
  `commands/replies` public-readiness now rejects summary-only
  `--response-path-report` JSON unless the child response-path report carries the
  checker-emitted `readiness_path`, `decisions_path`, `surfaces_path`,
  `public_header_path`, and acceptable `surfaces_status` provenance fields. These embedded
  paths are treated as report provenance strings only; the checker validates the report
  file itself and does not reopen temp-path provenance. Route gate remains planning-only
  and still blocks at `approved_runtime_evidence_missing`; SDK completion remains
  fail-closed at `stable_claim_allowed=false`, P0 `0/4`, and complete SDK `0/12`.
- 2026-06-02 Structure/P0/ResourceHandle guardrail hardening: structure build-policy
  offline intake now validates manifest-level `obelisk.structure_census.v1` posture
  against promoted/planning list placement, `status=planning`, `support_tier=blocked`, and
  empty public/ABI contract posture. Player-identity first-evidence now keeps
  `identity_public_contract_gate_missing` as a top-level blocker after approved runtime
  evidence, so accepted runtime evidence cannot make the checker `ready=true` before
  public contract review. The command/permission route gate rejects child-reported
  identity contract gates as premature current-route blockers and stays pinned to
  `approved_runtime_evidence_missing` in the current route. ResourceHandle readiness now
  scans decisions text for positive public ResourceHandle/object lookup/post-callback
  claims. These remain offline guardrails only; no runtime, public SDK, Structure SDK,
  ResourceHandle, identity, or v1 completion readiness is promoted.
- 2026-06-02 Inventory/Mission/release wording hardening: inventory copied-signal
  stability now scans all `docs/public_sdk_surfaces.json` string text for positive
  Inventory/Items SDK side-lane claims while preserving negated non-claims. Mission/
  transfer/dino/tribe/buff outcome accounting now scans every non-promoted leaf evidence
  object for readiness booleans and forbidden ResourceHandle/lookup/identity/mutation/
  return-override claims, not only the Mission leaf. Player-identity first-evidence now
  uses `identity_public_contract_gate_missing` consistently for both blockers and
  `primary_blocker` after approved runtime evidence. SDK completion release-statement
  scanning now rejects broad wording such as `Obelisk SDK v1 is ready` and production-ready
  variants. These changes keep route gate planning-only and SDK completion fail-closed.
- Plugin Hub is post-SDK-complete planning only. Do not route active rounds to Plugin Hub
  examples, packaging, intake tooling, or package hardening while SDK blockers remain open.
- The real P0 route for a complete SDK is identity/principal -> permissions/admin ->
  command response -> commands/replies. Do not substitute package shape, Plugin Hub work,
  static orientation, planning-layout readiness, or side-lane module evidence for this
  chain.
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
- If the identity offline packs remain accepted, identity is blocked on an approved
  runtime principal lifecycle window rather than more offline rediscovery.
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
  helper promotion. The dedicated
  `scripts/check_object_identity_resource_handle_public_contract_readiness.py` guardrail
  now enforces that copied events and category-only `resource_kind` metadata cannot imply
  public ResourceHandle, object identity, lookup, post-callback correlation, mutation, or
  runtime/public SDK readiness. Do not rerun broad FName, GObjects, or core scans for ResourceHandle.
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
  Current command route hardening requires `commands_replies_public_readiness` to consume
  the exact composed `command_chat_response_public_readiness` report; validating both as
  sibling checks is not enough.
- Offline artifact gates: keep tightening consume-vs-promote overclaim checks for
  ResourceHandle, Mission copied-bool, and Structure planning slices. Consume acceptance
  must not imply public SDK, runtime readiness, mutation, return override, lookup,
  post-callback handles, or v1 completion.
- ResourceHandle: wait for rejected runtime object samples plus runtime serial
  reuse/wraparound semantics from an approved live-ops brief; offline/core artifacts cannot
  synthesize that blocker away.
- Demand-map priority from NextGenPlugins names is P0 identity/principal ->
  permissions/admin -> command response -> commands/replies; P1 economy/storage/operator
  ingress, inventory/items mutation, and structure/build policy; P2
  dino/tribe/buff-status/mission/transfer leaves. Names are demand signals only.
- Post-P0 target map: after the P0 chain is promoted, the rentable module routes are
  Mission copied bools and item return-only copied signals because they already have
  focused consume-only evidence and clear no-mutation/no-identity boundaries. Treat them
  as next SDK hardening candidates, not as current v1 completion substitutes.

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
