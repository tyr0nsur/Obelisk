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
  `lifecycle_anchor_first_evidence_provenance_unbound` on the default route;
  `PYTHONDONTWRITEBYTECODE=1 python3
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
  `obelisk.reflection-snapshot-readiness.v1` as a dependency artifact. The default route
  gate remains planning-only and blocks at
  `lifecycle_anchor_first_evidence_provenance_unbound`; only explicit bound
  lifecycle/principal planning artifacts may advance the route to
  `approved_runtime_evidence_missing`.
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
  The default route gate remains planning-only with
  `lifecycle_anchor_first_evidence_provenance_unbound`; SDK completion remains
  fail-closed at `stable_claim_allowed=false`, P0 `0/4`, and complete SDK `0/12`.
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
  file itself and does not reopen temp-path provenance. The default route gate now remains
  planning-only at `lifecycle_anchor_first_evidence_provenance_unbound`; an explicit
  bound route may advance only to `approved_runtime_evidence_missing`. SDK completion
  remains fail-closed at `stable_claim_allowed=false`, P0 `0/4`, and complete SDK `0/12`.
- 2026-06-02 Structure/P0/ResourceHandle guardrail hardening: structure build-policy
  offline intake now validates manifest-level `obelisk.structure_census.v1` posture
  against promoted/planning list placement, `status=planning`, `support_tier=blocked`, and
  empty public/ABI contract posture. Player-identity first-evidence now keeps
  `identity_public_contract_gate_missing` as a top-level blocker after approved runtime
  evidence, so accepted runtime evidence cannot make the checker `ready=true` before
  public contract review. The command/permission route gate rejects child-reported
  identity contract gates as premature current-route blockers; the default current route
  remains pinned to `lifecycle_anchor_first_evidence_provenance_unbound`, and only the
  explicit bound route may advance to `approved_runtime_evidence_missing`. ResourceHandle
  readiness now scans decisions text for positive public ResourceHandle/object
  lookup/post-callback claims. These remain offline guardrails only; no runtime, public
  SDK, Structure SDK, ResourceHandle, identity, or v1 completion readiness is promoted.
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
- 2026-06-02 provenance/dispatcher/descriptor/release guardrails: commands/replies
  public readiness now revalidates embedded command response-path source artifacts and
  rejects missing/unreadable or summary-drifted child reports. PluginManager static
  guardrails now require every internal/test-only copied dispatcher cleanup exception,
  including `MissionCopiedBoolEventDispatcher`, to carry blocked public ABI and
  PluginManager wiring tokens while owner cleanup is absent. ResourceHandle readiness now
  scans promoted descriptor metadata surfaces such as `obelisk.descriptors.v1` for
  forbidden ResourceHandle/object lookup public contracts and positive evidence claims.
  SDK completion release-statement scanning now rejects active broad release verbs such
  as `ships`, `launches`, `goes live`, and `generally available` for SDK v1/complete or
  stable SDK wording. These are offline guardrails only; route gate remains planning-only
  and SDK completion remains fail-closed.
- 2026-06-02 route/Dino/ResourceHandle wording guardrails: the command/permission route
  gate now forwards the supplied `--public-sdk-surfaces` and `--public-header` to the
  downstream permissions/admin, command response, and commands/replies child checks, so a
  caller cannot validate aggregate route posture against one manifest while child checks
  read the repo default. Dino scalar readiness now revalidates external `--report`
  provenance by rebuilding the redacted signature report from the supplied snapshot root
  and rejecting `generated_from`/`descriptor_preflight` drift. ResourceHandle readiness
  now rejects positive `ships`/`includes`/`part of v1` wording, and SDK completion
  rejects `production-grade`/`release-grade` SDK/API/support claims. Runtime/ABI audit in
  the same round found no actionable gap in public ABI, owner cleanup, CallProcessEvent,
  timers, or PluginManager static guardrails. These remain offline guardrails only; no
  public SDK, runtime, ResourceHandle, Dino SDK, or v1 completion readiness is promoted.
- 2026-06-02 route blocker and release wording guardrails: the command/permission route
  gate now preserves the player-identity first-evidence checker's reported primary/next
  blocker and readiness booleans in `critical_path_phase` and rejects missing identity
  blocker provenance or positive readiness overclaims instead of manufacturing a clean
  planning-locked phase. SDK completion release-statement scanning now rejects `GA`
  abbreviations such as `Obelisk SDK v1 is GA`, `reaches GA`, and `The v1 SDK is GA`.
  These are offline guardrails only; route gate remains planning-only and SDK completion
  remains fail-closed.
- 2026-06-02 promoted-leaf and route-validity hardening: Mission/Transfer/Dino/Tribe
  `per_leaf_promoted` accounting now requires per-leaf promoted evidence entries with
  readable JSON reports, expected SHA256, matching `surface`/`leaf`/`evidence_kind`,
  promoted status/readiness booleans, artifact identity, and second-source provenance for
  second-source evidence; placeholder strings no longer account a leaf or select the
  promoted route. SDK completion also refuses to treat the umbrella
  `obelisk.mission_transfer_dino_tribe.v1` row as promoted evidence unless all five
  leaf decision units are promoted. The command/permission route gate now requires
  explicit `valid=true` from child checks and validates the player-identity
  first-evidence child exit/status/ready/internal-planning fields. Gap/query child reports
  now emit explicit `valid`. These remain offline guardrails only; no public SDK/runtime
  readiness or v1 completion is promoted.
- 2026-06-02 post-compaction route/umbrella evidence hardening: SDK completion now also
  requires the umbrella `obelisk.mission_transfer_dino_tribe.v1` row to carry per-leaf
  promoted evidence for all five leaf decision units, not only top-level umbrella
  evidence. The command/permission route gate now rejects any child check that reports
  non-empty `blockers` even when that child also says `valid=true`, and surfaces that
  condition as `child blockers not empty`. These are offline fail-closed guardrails only;
  no runtime, public SDK, command route, Mission/Transfer/Dino/Tribe, or v1 completion
  readiness is promoted.
- Deferred read-only audit risks from the same subagent round: structure second-source
  readiness should reject additional ready aliases and positive readiness strings;
  inventory/item copied-signal hygiene should scan `docs/public_gameplay_events.json`
  readiness claims; ResourceHandle/object-identity readiness should scan structured
  metadata in `docs/public_sdk_surfaces.json` and decisions, not only strings and gameplay
  events. Treat these as next offline guardrail targets, not current readiness evidence.
- 2026-06-02 side-lane overclaim closure: structure second-source readiness now rejects
  positive Structure SDK/build-policy/enforcement/runtime/v1 aliases and readiness
  strings without breaking the accepted planning-layout second-source artifact. Inventory
  copied-signal stability and item return-only readiness now reject generic runtime/v1
  readiness keys and strings in `docs/public_gameplay_events.json`; item return-only also
  accepts and validates the current copied+inventory-backed `required_flags` metadata.
  ResourceHandle readiness now applies structured positive-claim scanning to decisions and
  `docs/public_sdk_surfaces.json`, not only public gameplay events. These are offline
  guardrails only; no Structure SDK, Inventory SDK, Items SDK, ResourceHandle, runtime, or
  v1 completion readiness is promoted.
- New deferred P0 offline route-provenance risk: command/chat response public readiness can
  still consume a well-shaped synthetic `--command-response-readiness` JSON that is not
  bound to the supplied `--command-response-root` or regenerated snapshot provenance. This
  was a downstream route-provenance risk only after explicit identity source binding; the
  default aggregate route now remains planning-only at
  `lifecycle_anchor_first_evidence_provenance_unbound`. The next P0 guardrail target was
  to bind or regenerate command response readiness artifacts before the route treats them
  as aligned planning evidence.
- 2026-06-02 P0 command response provenance closure: command/chat response public
  readiness now binds the readiness JSON to its selected root, requires target-detail
  snapshot paths to be the expected files under `base-snapshots/`, and emits
  `readiness_root` for downstream replay. The route gate now rejects caller-supplied
  command response readiness without a matching `--command-response-root`, and
  commands/replies can compare embedded response-path reports against expected response
  root/readiness when the route supplies that context. This is still planning-only; it
  does not promote command response, replies/send-chat ABI, command router, runtime
  readiness, or v1 completion.
- 2026-06-02 P0 report replay and release-template guardrails: permissions/admin public
  readiness no longer accepts checker reports as `--query-failclosed-artifact`; it accepts
  only the candidate query manifest and revalidates it in consume mode. Commands/replies
  public readiness now requires response-path reports to be bound to expected response
  root/readiness and current surfaces/header inputs; the route gate forwards the freshly
  composed command response report's root/readiness into replies. Release v1 public SDK
  templates under `release/v1/public-sdk/*.md` are now scanned with the release-statement
  broad-claim detector while `stable_claim_allowed=false`. This remains offline
  guardrail work only; no public permissions/admin, command response, commands/replies,
  runtime readiness, release readiness, or v1 completion is promoted.
- 2026-06-02 P0 promotion-evidence accounting closure: SDK v1 completion now requires
  promoted `obelisk.command_chat_response_path.v1` rows to carry structured command
  response public-readiness report evidence plus an executed ABI/SDK test report, and
  promoted `obelisk.commands_replies.v1` rows to carry structured commands/replies
  readiness, structured command-response dependency evidence, and executed ABI/SDK test
  evidence. Completion-blocker rows now keep `counts_toward_complete_sdk_claim=false`
  when structured promotion evidence is missing, even if generic ABI/SDK paths and all
  prose terms are present. Inventory copied-signal stability also rejects
  `v1_sdk_ready`, `release_ready`, and `public_abi_ready` aliases in
  `docs/public_gameplay_events.json`, and ResourceHandle readiness rejects generic
  readiness booleans in decisions and the ResourceHandle surface row. A later follow-up
  wires the ResourceHandle/object-identity readiness checker into SDK completion
  accounting, closes Structure alias/string overclaim gaps in census/build-policy
  checkers, rejects non-canonical command/permission route-gate overrides unless the
  explicit test-only env flag is set, and lets commands/replies structured evidence carry
  a complete nested command-response promotion-evidence object instead of permanently
  failing on a missing nested executed-test report. Remaining deferred guardrail:
  executed promotion test reports are still inline manifest objects; future accounting
  should require repo-relative runner-emitted JSON with current HEAD/argv/exit/output
  provenance. ABI audit also recommends an offline test for GameplayPolicyEvent
  multi-dispatcher partial registration rollback. This is offline guardrail work only;
  command response, commands/replies, Inventory/Items SDK, Structure SDK, ResourceHandle,
  runtime, release readiness, and v1 completion remain unpromoted.
- 2026-06-02 P0 identity aggregate provenance closure: player-identity first-evidence now
  rejects standalone lifecycle-anchor/principal-policy planning artifacts unless they are
  bound to the first-evidence source artifact identity and the principal policy binds back
  to the lifecycle manifest's source identity and accepted anchors. The active route gate
  now accepts `lifecycle_anchor_first_evidence_provenance_unbound` as an identity-lock
  planning-only blocker, with all promotion/public/runtime flags false. This supersedes
  the earlier `approved_runtime_evidence_missing` primary blocker until the offline
  lifecycle/principal source binding is produced; after that binding, approved copied
  runtime principal lifecycle evidence is still required before public identity review.
  This is offline guardrail work only and does not approve runtime capture, public
  identity, permissions/admin, command response, commands/replies, release readiness, or
  v1 completion.
- 2026-06-02 P0 identity planning-source binder: `scripts/bind_player_identity_planning_sources.py`
  now emits bound lifecycle-anchor and principal-policy planning artifacts from validated
  first-evidence, lifecycle, and principal JSON inputs. The tool writes only to a checked
  offline output directory, rejects protected output paths and symlinks, emits a
  non-claim report, and validates aggregate planning provenance. A later hardening
  requires lifecycle `artifact_identity.source_artifact_ids`, principal
  `lifecycle_layout_source.source_binding`, and principal start/end anchors to match the
  first-evidence/lifecycle source before binding; stale standalone manifests now fail
  before outputs are written. The default repo route remains blocked on
  `lifecycle_anchor_first_evidence_provenance_unbound` unless explicit source-aligned
  bound lifecycle/principal planning artifacts are supplied to the route gate via
  `--lifecycle-anchor-candidates-manifest` and
  `--principal-invalidation-policy-manifest`; with those explicit bound inputs, the route
  may advance only to `approved_runtime_evidence_missing`. The route gate rejects partial
  lifecycle/principal input. Bound outputs do not provide approved runtime evidence,
  public identity, permissions/admin, command response, commands/replies, release
  readiness, or v1 completion.
- `scripts/check_command_permission_route_gate_bound_identity_sources.py` is the explicit
  offline wrapper for the bound route transition. It builds transient first-evidence from
  sanitized snapshots, binds supplied lifecycle/principal planning manifests in a private
  temp directory, forces child temp writes under that non-protected temp root, and runs
  the route gate with explicit bound inputs. A valid wrapper report may show only
  `approved_runtime_evidence_missing`; it still authorizes no runtime/server work and no
  public SDK/ABI/v1 readiness.
- Latest bound-identity/default-route/SDK rerun: the historical
  `/servidor/ark/workspace-offline/player-identity-principal-invalidation-policy-20260531T231247Z/`
  lifecycle/principal manifests are still valid standalone consume-only planning artifacts,
  but the stricter wrapper rejects them as not source-bound to the generated first
  evidence (`lifecycle_anchor_source_artifact_ids_mismatch`). The default
  `scripts/check_command_permission_route_gate.py --json` route remains planning-only and
  blocks at `lifecycle_anchor_first_evidence_provenance_unbound` when explicit source-bound
  lifecycle/principal manifests are not supplied. A wrapper run with source-aligned
  synthetic test fixtures may advance only to `approved_runtime_evidence_missing` with all
  public/runtime/promotion/v1 flags false; the historical standalone bundle must not be
  treated as bound-route evidence until regenerated/aligned.
  `scripts/check_public_sdk_v1_completion.py --json` still fails closed with
  `stable_claim_allowed=false`, complete-SDK `0/12`, and P0 `0/4`. This is offline
  routing evidence only: no runtime/server work, public identity, permissions/admin,
  command response, commands/replies, release readiness, or completion claim is promoted.
- Approved runtime principal lifecycle evidence guardrails now require producer-shaped
  `approval.reviewed_by` and `approval.review_note`, reject blank or identity/UE-internal
  approval review text even when phrased as a negative claim, normalize whitespace before
  public/runtime readiness claim scanning, and reject request-pack JSON whose copied log,
  copied evidence dir, or `window-manifest.env` path drifts from the current manifest
  being checked. This is consume-side offline validation only and does not approve runtime
  capture, public identity, route promotion, or v1 completion.
- Follow-up preflight/window guardrails require structured
  `obelisk.player-principal-lifecycle-preflight.v1` JSON for `preflight-pre.json` and
  `preflight-post.json`, reject legacy text sidecars, bind observer-window preflight JSON
  to the manifest's observer env path/SHA, normalize window-manifest report paths to
  resolved artifact paths, and reject launch-posture env keys such as `LD_PRELOAD`,
  `LD_LIBRARY_PATH`, `OBELISK_ROOT`, and Obelisk plugin/config/log roots in observer
  preflight env. This remains offline consume-side validation only.
- Follow-up route/SDK provenance guardrails now bind the identity child
  `primary_blocker` to the child blocker list, make `route_lock.locked` reflect all route
  blockers, and require the bound wrapper and SDK completion wrapper to reject route-gate
  reports with stale source checker readiness/status/internal-planning fields, non-empty
  route blockers, route-lock drift, or stale default `source_checker_next_blocker`.
  This remains planning-only validation and does not advance the default or bound route.
- Follow-up downstream input provenance guardrails now require command response and
  commands/replies public readiness to scan the canonical
  `include/obelisk/ObeliskApi.h`, reject fake/protected/symlink public-header inputs,
  bind response-path reports to canonical command response decisions/header artifacts,
  and require permissions/admin public readiness to load decisions, surfaces, and query
  artifacts through protected/symlink-safe JSON input guards. The route gate has
  aggregate coverage that fake `--public-header` fails through the downstream child
  checks. This remains offline planning-only validation and does not promote public
  permissions/admin, command response, commands/replies, runtime readiness, or v1
  completion.
- Follow-up player-identity public-contract and bound-planning guardrails now load
  player-identity public-contract decisions and private candidate contracts through
  protected/symlink-safe JSON guards, require the public contract checker to scan the
  canonical `include/obelisk/ObeliskApi.h`, and reject approved-runtime reports that try
  to overclaim `public_header_allowed`. Lifecycle-anchor planning manifests now reject
  unexpected top-level fields and positive runtime/server/command/public-SDK claims;
  principal-invalidation policy now rejects extra `lifecycle_layout_source` fields and no
  longer exempts that source from positive command/permission claim scanning. The binder
  therefore fails before writing bound outputs if planning inputs carry runtime/server
  authorization claims. This remains offline planning-only validation and does not
  authorize runtime/server work or promote public identity.
- 2026-06-02 SDK completion evidence-routing hardening: `check_public_sdk_v1_completion.py`
  now forwards its selected `--manifest` and `--public-header` to the command/permission
  route gate, validates required public-contract decision manifests even for non-default
  `--contract-decisions-dir`, and requires promoted `obelisk.player_identity.v1` evidence
  to include structured approved-runtime, public-contract-readiness, and executed ABI/SDK
  test evidence, and promoted `obelisk.permissions_admin.v1` evidence to include structured
  query fail-closed, public-readiness, and executed ABI/SDK test evidence, instead of
  relying on placeholder paths plus prose terms. This does not promote player identity,
  permissions/admin, or v1 completion; default SDK completion still fails closed with
  `stable_claim_allowed=false`, complete-SDK `0/12`, and P0 `0/4`.
- Deferred SDK-completion audit risk: extend the same structured promotion-evidence
  binding to command response and commands/replies before future promotion accounting can
  trust synthetic promoted evidence.
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
  lifecycle-anchor and principal-invalidation manifests. Those standalone lifecycle and
  principal manifests are consume-only planning inputs; they must be source-bound before
  the aggregate route can move past `lifecycle_anchor_first_evidence_provenance_unbound`.
  Promotion remains false. After explicit bound artifacts are supplied and accepted, the
  next blocker is approved runtime principal lifecycle evidence. Do not rerun the
  completed admin snapshot, second-source layout, or lifecycle layout routes.
- Current recipe:
  `docs/research/2026-05-31-player-identity-offline-pack-preflight.md`.
- If the identity offline packs remain accepted, the default route is blocked first on
  source-bound lifecycle/principal planning provenance. Only the explicit bound-wrapper
  route may advance to the approved runtime principal lifecycle evidence blocker; neither
  path calls for broad offline rediscovery.
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
- Latest supervised guardrail round hardened P0/release accounting without changing
  readiness:
  - `scripts/check_public_sdk_v1_completion.py` now requires
    `evidence.executed_test_report` for promoted P0 surfaces to be a repo-relative JSON
    artifact using schema `obelisk.promoted-surface-test-execution-artifact.v1`, matching
    the surface id, current HEAD, command/argv, `exit_code=0`, and a nonempty output or
    provenance hash. Inline self-attested executed-test objects no longer satisfy
    player identity, permissions/admin, command response, or commands/replies.
  - P0 blocker rows now carry `route_gate_claim_satisfied=false` while the default
    command/permission route gate remains
    `lifecycle_anchor_first_evidence_provenance_unbound`; promoted-looking P0 evidence
    cannot count toward complete-SDK progress until the route gate is unlocked.
  - `scripts/check_release_readiness.sh` now rejects second-source readiness JSON that
    omits the layout-only non-promotion envelope
    (`ready_scope=layout_only`, `layout_ready=true`, promotion/public/runtime false,
    `evidence_scope=second_source_layout_evidence_only`, non-promoted surfaces, and
    non-claims).
  - Release-statement broad-claim scanning now treats `not only`/`not merely` wording as
    affirmative context, not as safe negation.
  - `PluginManagerTests` covers partial `GameplayPolicyEvent` multi-dispatcher
    registration rollback: injected ItemReturn registration failure after earlier
    families returns handle `0` and leaves Structure/Inventory/ItemReturn subscription
    counts at zero.
- Latest follow-up round tightened those same gates further:
  - Promoted P0 executed-test artifacts must now carry canonical provenance
    (`producer=obelisk.promoted-surface-test-execution-runner.v1`, checker path, and
    `produced_at_utc`) plus SHA256-bound inputs for `docs/public_sdk_surfaces.json` and
    `include/obelisk/ObeliskApi.h`. Well-shaped local JSON without those bindings is
    rejected.
  - P0 route-gate accounting now stays false for any planning-only, locked, invalid, or
    blocker-bearing route gate, including the explicit
    `approved_runtime_evidence_missing` blocker. Promoted-looking P0 rows cannot increase
    progress while the route remains identity-blocked.
  - `scripts/validate_offline_artifact_gate.py` now blocks every reflection snapshot
    readiness report in promote mode, even when `promotion_gate.ready=false`, and rejects
    `promotion_ready`/`public_sdk_ready`/`runtime_ready` overclaims on not-ready reports.
  - The real `scripts/compare_reflection_snapshots.py --readiness-report --json`
    producer was audited and already emits the required layout-only envelope; no producer
    edit was needed.

## Priority Next Steps

- P0: produce or regenerate lifecycle-anchor/principal-policy planning manifests whose
  source artifact IDs and principal lifecycle source binding match the current
  first-evidence source, then run `scripts/check_command_permission_route_gate_bound_identity_sources.py`
  and confirm the wrapper route blocker is only `approved_runtime_evidence_missing`. Do
  not treat the default-route `lifecycle_anchor_first_evidence_provenance_unbound` blocker
  as runtime-evidence work. After the runtime principal lifecycle evidence blocker is
  cleared by future scoped evidence, review the identity contract before permissions/admin,
  command response, or commands/replies ABI.
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
- Mission/Transfer/Dino/Tribe outcome accounting: audit the future `per_leaf_promoted`
  route before any use as promotion evidence. The placeholder-list bypass is now blocked;
  future promoted leaves should use actual promote-mode gate outputs or a reviewed
  promotion report shape with leaf/surface binding, artifact identity, and second-source
  provenance. Current mission/transfer/item/structure side lanes remain consume-only or
  candidate planning evidence and must not be reinterpreted as promoted leaves.
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
