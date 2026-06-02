# Compact Context Snapshot

Updated: 2026-06-02

Use this file after conversation compaction or when resuming Obelisk from repository
state. Current routing table only: read `docs/agent-handoff/CURRENT.md` for active
priorities, and do not use history files as the active source of truth.

## Resume Protocol

1. Read this file, `docs/agent-handoff/CURRENT.md`, and the relevant subsystem skill.
2. In lead/integration turns where current instructions do not prohibit Git, check
   `git status --short --ignored`.
3. Close completed or obsolete internal agents before starting a new round.
4. Continue direct supervised work with scoped sub-agent prompts when delegation is used.
   When the user asks for delegation, the lead must spawn/coordinate the agents directly
   and record the delegated scopes plus integrated findings in handoff/research notes
   before finishing so compaction does not lose them.

## Active Overrides

- GitHub work may be delegated only for an evidenced, stable milestone; routine local
  rounds are not publication events. No tag or release-ref push is authorized without
  explicit release-manager/lead authorization for the current turn. Stale local tags are
  recreated only after rerunning the gate on the intended ref and are not reused or
  pushed.
- No standing operator approval for Obelisk debug/development or beta tests applies to
  starts, restarts, marker edits, `/servidor/ark` edits, ReflectionScanner, ptrace/gcore,
  broad ProcessEvent tracing, or runtime observation. Any server-backed run requires a
  live-ops brief for that turn naming the target, feature gates, marker/env changes,
  restart/start window, notice path when players are involved, evidence capture, and
  rollback. Technical progress alone is not approval to restart; request an exact run only
  after a concrete offline/code advance genuinely needs new runtime logs. Request packs
  and preflight acceptance prepare or validate a future window only; they are not runtime
  approval, public SDK readiness, runtime readiness, release readiness, or permission to
  change markers/env/restart without a current-turn live-ops brief.
- Community updates are for major public modder-facing milestones only; beta-test
  activation notices are separate operational live-ops messages. Use only
  `OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL` or `OBELISK_BETA_TEST_WEBHOOK_URL` by variable
  name. No Discord for routine validation, internal rounds, speculative reversing notes,
  private live-ops detail, raw player text, secrets, or agent status. Explicit
  current-turn approval and a guarded dry-run are required for every send.
- `ArkServerApi/AseApi` and local `NextGenPlugins` clones may be used only as names and
  demand signals for familiar ArkApi-style plugin concepts. Do not treat them as
  architecture or ergonomics sources, and do not import offsets, vtables, layouts, `.lib` artifacts,
  MSVC/Windows ABI assumptions, direct `GetNativePointerField`/`NativeCall` wrappers, raw
  UE pointer APIs, constants, schemas, control flow, command parsers, return semantics, or
  source-derived implementations; all access must be rebuilt through Obelisk
  reflection/ProcessEvent copied-data evidence.

## Stable Baseline

- Repo: `/home/flowcommunity-ark/Obelisk`
- Remote: `git@github.com:tyr0nsur/Obelisk.git`
- Central Obelisk root: `/servidor/ark/obelisk`
- Current release baseline: `v0.1.0-rc.2` is the current published core-first RC baseline for the
  current public surface after a clean release gate and exact tag/ref verification. It is not a
  production-stable `v1.0` claim. Post-RC work should move toward a complete `v1.0` SDK
  through architecture hardening, UE4 reflection evidence, copied-data module APIs, and
  later compatibility for familiar ARK plugin concepts on top of Obelisk primitives.
- `v1.0` stable means the complete public SDK contract for plugin authors, not merely a
  stable internal runtime. The current v1 surface inventory lives in
  `docs/public_sdk_surfaces.json`, with human guidance in `docs/SDK_V1_COMPATIBILITY.md`;
  both are planning-contract artifacts until a future release gate packages or supersedes
  them.
- The v1 completion checker must reject promoted permissions/admin, command/chat response
  path, or commands/replies rows whose dependencies are not promoted, and promoted player
  identity must name the reviewed core/reflection evidence terms before supporting public
  permissions or command claims. It must also enforce the canonical
  `stable_release_contract.claim_requires` and `not_sufficient` clauses so Plugin Hub
  package shape, RC package readiness, and copied event surfaces remain non-sufficient for a
  stable SDK claim.
- The active P0 dependency route is identity/principal -> permissions/admin ->
  command response -> commands/replies.
  After player identity/principal, the permissions/admin candidate is query-only
  fail-closed checks; commands/replies still require identity, permissions/admin, and the
  named `obelisk.command_chat_response_path.v1` planning dependency. The P0 chain is
  tracked as `v1_required_dependency_chain` and those four surfaces are promoted-only for
  a complete SDK claim; excluded/post-v1 records are scoped non-complete accounting only.
  Official complete-SDK progress remains `0%` (`0/12` complete-SDK rows and `0/4` P0
  promoted rows). The technical foundation is estimated at roughly `20-25%`: RC
  core/runtime, copied plugin events, installed package-shape checks, offline intake
  tooling, and consume-only module slices exist, but none can replace the promoted P0
  dependency chain.
  That response path adds no
  ABI today and keeps public `CallProcessEvent`, raw UE pointer/params/FString response
  APIs, replies, send-chat, broadcast/notices, and moderation blocked until promoted or
  explicitly excluded. `docs/command_chat_response_public_contract_decisions.json` is the
  blocked pre-ABI checklist for that future response path; static thunk orientation,
  passive copied chat parsing, candidate vtable slots, raw ProcessEvent callbacks, and
  legacy `CallProcessEvent` are not sufficient response-path evidence.
  `obelisk.command_copied_response_intent_lifecycle.planning.v1` is a planning-only
  lifecycle guardrail for owner-scoped create/cancel/drain/expire/unload-cleanup response
  intent vocabulary. It is integrated into the route gate but adds no public ABI, runtime
  delivery, reply/send-chat API, command router, public SDK readiness, or v1 completion
  evidence.
  `command-chat-response-route-planning` exists only as a planning-only focal snapshot
  target set for `ClientServerChatDirectMessage`, `ClientServerChatMessage`, and
  `ClientChatMessage`; it is not a release-readiness target set, public reply/send-chat
  ABI, command router, or runtime response claim.
  `scripts/check_command_permission_route_gate.py --json` is the canonical offline route
  posture check for this dependency chain; passing it means planning-only alignment, not
  public ABI, runtime readiness, command router, reply/send-chat ABI, or v1 completion.
  It must scan sub-checker reports recursively for public/runtime aliases and positive
  text claims; nested public reply/send-chat, command routing, permissions/admin, ABI,
  runtime, or v1-completion claims block planning alignment even if a leaf report says
  `valid=true`.
  Identity now has repo-local source-bound lifecycle/principal planning artifacts in
  `docs/research/player-identity-planning-sources/`, generated from the current
  first-evidence and sanitized lifecycle snapshots. The default no-runtime route is
  blocked at `approved_runtime_evidence_missing`, remains locked/planning-only, and
  keeps all public/runtime/promotion/SDK readiness flags false; with accepted approved
  runtime evidence, the route may advance only to `identity_public_contract_gate_missing`,
  still locked/planning-only. Inventory copied signals remain the higher-value side lane
  after identity -> permissions/admin -> commands/replies, while Structure census is
  explicitly excluded/non-counting and Structure build-policy remains offline planning only.
  The accepted lifecycle-anchor snapshot binding gap is closed in the current builder and
  default route: `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout` source
  hashes are checked against the actual `--snapshot-root` files before the route may
  report `approved_runtime_evidence_missing`.
  Operator approval receipt handling is provenance-only: request preparation writes only
  `operator-approval-receipt.template.json`; post-window replay requires a completed
  `operator-approval-receipt.json`, exact current-turn completion metadata, bound-request
  parity, and request replay that tolerates only `approved_window_expired`.
- `docs/permissions_admin_public_contract_decisions.json` blocks any public
  permissions/admin ABI until principal generation, principal scope, cache keying, and
  stale/scope-mismatch fail-closed behavior are resolved on top of promoted copied
  player identity. Identity and permissions decision contracts carry `v1_sequence_gate`
  entries preserving identity/principal -> permissions/admin -> command response ->
  commands/replies.
  The candidate `obelisk.permissions-admin-query-failclosed-contract.v1` is now supported
  by the offline artifact gate in consume mode only; it is not public ABI, runtime
  readiness, public SDK readiness, or v1 completion evidence.
  `scripts/check_permissions_admin_public_readiness.py` is the reusable planning-only
  public-readiness guard for this surface and must keep public header/ABI/SDK/runtime
  readiness false until promoted identity and a reviewed ABI exist. The internal
  `AuthzDecisionModel` models copied query text bounds (`action` required <=128 bytes,
  optional `resource_scope` <=256 bytes) without promoting a public parser, cache, or
  permissions/admin ABI.
  Permissions authority is split between recognized and allow-capable kinds:
  `operator-config` is recognized but not allow-capable; only runtime-local/runtime-owned
  provenance may allow. Nested readiness/promotion overclaims in the candidate contract
  must be rejected by the schema checker and offline artifact gate.
  `unknown_authority` is an explicit fail-closed `unknown` result in both fail-closed
  cases and reason flags; drift back to `deny` must fail the checker because downstream
  command/reply planning distinguishes `deny` from `unknown`.
- `scripts/check_command_permission_route_gate.py --json` must compose the exact
  `command_chat_response_public_readiness` report into
  `commands_replies_public_readiness --response-path-report`. The route is not aligned if
  response path and commands/replies only pass as independent sibling checks.
- Stable plugin loading requires safe `OBELISK_INSTANCE_ID` plus real non-symlink plugin,
  config, log, and state roots.
- `ObeliskApi` v1 is append-only for `v0.1.0`; ABI v2 requires an explicit migration plan.
- First-stable `v0.1.0` timers are the first non-UE-dependent core primitive and are part
  of the current `v0.1.0-rc.2` public surface: owner-token scoped, process-local, zero-failure
  handles, one-shot/repeating callbacks, explicit unregister, and unload/init-failure
  cleanup.
  Timer ids are not shared config, cluster state, UE identity, gameplay/module timer
  abstractions, shared scheduler state, or persistent handles. `oProcessTimer` is the
  first-party process-local timer example.
  PluginManager tests now cover repeating timer cleanup under an in-flight callback during
  `UnloadAll`, proving the plugin is not closed early and the repeating timer does not
  reschedule after owner cleanup.
- EventManager granular raw ProcessEvent unregister avoids waiting behind unrelated
  in-flight callbacks and active-id checks skip unregistered callbacks from stale
  snapshots; owner cleanup still waits before plugin unload. Tests cover debug-gated
  filtered pre-ProcessEvent and post-ProcessEvent callback paths.
- PluginManager unload must not `dlclose` if any plugin-owned callback cleanup family
  fails. The current runtime retains the plugin mapped for a later `UnloadAll()` retry
  and records that shutdown was already called so retry cleanup/close does not invoke
  plugin shutdown twice. Init-failure cleanup also leaves the library mapped if callback
  cleanup cannot be proven complete.
- Runtime posture is default-deny for filtered raw `ProcessEvent` callbacks, global
  callbacks, public `CallProcessEvent`, ProcessEvent blocking, broad tracing,
  scanner/debug controls, and experimental observers.
  Filtered raw callbacks expose borrowed UE pointers/raw params and require
  `OBELISK_ALLOW_FILTERED_PROCESS_EVENT_CALLBACKS=1` plus
  `allow-filtered-process-event-callbacks`; copied `GameplayPolicyEvent` and
  `ChatMessageEvent` are the RC plugin paths.
  `CallProcessEvent` remains an ABI v1 compatibility/init-window debug escape hatch only:
  it now fails closed unless the current plugin owner is inside `ObeliskPlugin_Init`, that
  owner captured `OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT`, and the live env+marker gate
  is still active. Post-init calls through captured API tables are not a supported callable
  path; a future replacement must carry an owner token.

## Product Baseline

- Current RC public scope has one promoted gameplay policy callback surface:
  `GameplayPolicyEvent`. Promotion scope and exclusions are recorded in
  `docs/research/2026-05-29-public-gameplay-event-readiness-audit.md`. The separate
  minimal `ChatMessageEvent` RC surface is a copied chat notification contract, not a
  command or moderation API. RC public scope remains limited to `GameplayPolicyEvent`,
  the minimal copied `ChatMessageEvent`, `DescribeResourceKind`, and
  `DescribeGameplayPolicyEventKind`. `v0.1.0-rc.2` additionally includes process-local
  owner-token timers as core runtime API without promoting gameplay/module timers or a
  broader gameplay policy/module SDK.
- Post-RC dictionary research against `/tmp/aseapi-inspect` confirms AseApi/ArkServerApi
  is useful only for names and concept grouping. The nearest stable plugin-facing path is
  still copied `GameplayPolicyEvent` structure/inventory, especially `PrimalItem.CanUse`
  and `PrimalItem.AllowRemoteAddToInventory`. The three ReturnValue-only item-return
  checks are now append-only public `GameplayPolicyEvent` kinds, but their artifact
  promote mode remains blocked and they do not promote an Items SDK, Inventory SDK,
  identity, mutation, or return override. Dino/buff/mission/tribe/transfer stay internal
  or layout-only until copied-data, lifecycle, privacy, and promotion gates pass.
- `GameplayPolicyEvent` excludes mutation, raw UE pointer exposure, public
  callback-by-name APIs, public `StructureEvents`, public Inventory/etc. module APIs,
  richer chat APIs beyond minimal `ChatMessageEvent`, HTTP/threads/file-reader plugin
  ingress, and lifecycle-unsafe plugins.
- Plugin Hub work is post-SDK-complete planning only. Do not spend current rounds on
  Plugin Hub examples, packaging, intake tooling, or package hardening while the complete SDK
  blocker chain remains open. Historical Plugin Hub docs may be read as boundaries only;
  they do not replace the active identity/principal -> permissions/admin -> command
  response -> commands/replies route. Storage, mutation, ResourceHandle, and gameplay
  module surfaces remain later blockers or scoped side lanes. Passive copied chat parsing
  and copied policy auditing remain experimental pattern examples only;
  demand-map or `NextGenPlugins` dictionary entries do not make an idea release-ready and
  do not promote permissions, RCON, economy, homes/safe zones, structure enforcement,
  dinos, tribes, transfers, inventory, item mutation, identity, lookup, replies,
  send-chat, moderation, or ArkApi portability.
- Post-P0 module routing should favor Mission copied bools and item return-only copied
  signals as rentable SDK hardening paths because they have focused consume-only evidence
  and explicit no-public-SDK/no-mutation/no-identity boundaries. They remain side lanes
  until identity -> permissions/admin -> command response -> commands/replies is promoted.
- The current inventory/item copied-signal side-lane guardrail pins public evidence to
  `minimal-second-source-intake` and `item-return-only-policy-slice`, keeps
  `inventory-action-compact-intake` excluded, and rejects positive raw inventory/item
  identity/action-param claims such as `ItemId`, `ItemID1`, `InventoryComp`, `anActor`,
  `ItemNetID identity`, and raw params.
- `DescribeResourceKind` is a metadata-only v0.1 SDK helper for known resource categories.
  It returns copied POD descriptors with supported gameplay-policy event/field masks and
  explicit no-identity/no-lookup flags.
- `DescribeGameplayPolicyEventKind` is a metadata-only v0.1 SDK helper for promoted
  `GameplayPolicyEvent` kinds. It returns copied POD descriptors for routing/config, not
  UE lookup, identity, mutation, or return override.
- `oDescriptorCatalog` is a release-scope reference plugin for those descriptor helpers.
  It validates descriptor coherence and logs sanitized resource/event metadata only; it
  registers no callbacks/timers and adds no ABI surface. Installed SDK consumer fixtures
  now cover fail-closed rejection of unknown resource/event kinds and undersized v1
  descriptor structs. Installed SDK examples are Linux x86_64 samples only and must not
  carry Windows/MSVC export branches or portability signals.
- `InventoryPolicyEventDispatcher` and `StructureEventDispatcher` are internal
  copied-scalar infrastructure only. They do not promote public Inventory or
  StructureEvents SDKs.
- Inventory copied-policy dispatch uses build-once payload reuse after budget reservation
  and a cheap atomic live-subscriber mirror; lifecycle cleanup must still use dispatcher
  depth/deferred-destroy state, not the subscriber mirror. Copied inventory payloads
  rebind scalar spans on copy/move so dispatch-time values own their storage, and failed
  budget reservation clears stale payloads.
  Item copied-signal dispatch now preserves and revalidates property class FName index,
  property class object index, and property flags in `ItemFieldRange`; forged item
  observations with correct name/offset/size but wrong class metadata fail closed. This is
  still internal copied-signal hardening, not a public Inventory/Items SDK, identity,
  mutation, return override, runtime readiness, or v1 completion signal.
- Structure copied-policy dispatch now follows the same safety pattern: dispatch budget
  requires live subscribers, matched attempts reserve with one self-contained copied event,
  copied scalar spans rebind on copy/move, exposed scalar range sizes are validated, and
  reader exceptions fail closed. Structure dispatcher output also rejects scalar
  fields/types outside the exact public descriptor contract for each event kind, and
  structure dispatch budget no longer keeps the hook hot path active when there are no
  subscribers. This remains internal infrastructure, not a public StructureEvents SDK or
  structure identity surface.
- Structure build-policy offline intake has a consume-only artifact-gate schema:
  `obelisk.structure-build-policy-offline-attestation.v1`. It pins accepted planning
  readiness, requires the embedded `obelisk.structure-build-policy-offline-intake-check.v1`
  checker report, distinct base/candidate snapshot identities, and redaction boundaries,
  keeps public/runtime/enforcement flags false, and blocks promote mode. It is not
  Structure SDK, enforcement, identity/lookup, mutation, return override, runtime readiness,
  or v1 completion evidence.
- Public `GameplayPolicyEvent` and `ChatMessageEvent` plugin callbacks are caught at the
  bridge to prevent C++ plugin exceptions from escaping into dispatcher/hook code.
- Release scope wording separates copied RC plugin events from debug-gated raw
  ProcessEvent callback infrastructure and experimental target-specific gameplay/module
  observers.
- Runtime timer owner cleanup has regression coverage for cleanup initiated from inside
  that owner's timer callback: it must not deadlock, must remove the repeating timer,
  must cancel peer timers for the same owner, and must prevent later delivery.

## Evidence Baseline

- ProcessEvent, FName, GObjects, UObject, UFunction, and unpromoted gameplay recognizer
  evidence is binary-scoped until the relevant second-source/static promotion gates pass.
- The accepted minimal second-source layout evidence is recorded in
  `docs/research/2026-05-29-minimal-second-source-readiness.md`. It supports the
  v0.1 RC release gate but does not promote GObjects, ResourceHandle, identity,
  mutation, return overrides, raw params, player/item/inventory identity, or public
  Inventory/StructureEvents SDK surfaces.
  Current validator refresh:
  `/servidor/ark/workspace-offline/minimal-second-source-intake-refresh-20260529T124340Z`
  passed offline artifact consume gates for both the readiness report and optional
  redacted signatures. Treat it as layout-only evidence with `promotion_ready=false`.
  The latest focused consume refresh is preserved at
  `/home/flowcommunity-ark/obelisk-artifacts/minimal-second-source-intake-offline-20260530T075501Z/`;
  it has 4/4 targets accepted and consume gates accepted for the copied
  `GameplayPolicyEvent` structure/inventory lane only. The pack is normalized with
  relative checksums and `artifact-pack.manifest.json`
  (`sha256=072ff1f71c59e59189fa53922376dfc61d00915cfcd57817b1e5eacbc8200f8c`);
  `SHA256SUMS`
  (`sha256=21d8b0c0f30799b43110ddd4eed2484cc8c8527df878139dde28bc7d12598cf0`)
  verifies the durable pack.
- Minimal copied `ChatMessageEvent` has accepted `chat-message-intake` second-source
  evidence and approved beta delivery evidence for known send modes. The durable evidence
  is recorded in `docs/research/2026-05-29-chat-message-second-source-readiness.md` and
  `docs/research/2026-05-30-rc-second-source-release-gate-check.md`; use
  `docs/agent-handoff/CURRENT.md` for any current chat routing. Keep future route
  observations `delivery_claim=none` unless a new controlled copied-plugin delivery window
  is approved and preserved.
- Historical server prep note: `/servidor/ark/obelisk` and `oChatLogger` were installed
  for an `arkserver` beta validation. Do not treat that snapshot as current authorization
  or current posture. Reconfirm process, markers, plugins, and operator approval before
  any new runtime observation; rollback plans must remove beta launch/config changes,
  restore stable markers such as `disable-plugins`, restart only in an approved window,
  and validate stable posture afterward.
- Historical player-backed beta scope was minimal `ChatMessageEvent` delivery, now
  recorded as accepted evidence in the chat readiness note. Future player-backed
  validation is not authorized by this snapshot; use `CURRENT.md` and a current live-ops
  brief. Inventory/mission/item/dino/buff/tribe/transfer/admin surfaces stay
  internal/offline until their copied-data, callback lifecycle, ABI, and runtime gate
  requirements are satisfied.
- Dino, buff, mission, and tribe compact intakes are layout evidence only. Use
  `docs/research/2026-05-29-dino-compact-second-source-readiness.md`,
  `docs/research/2026-05-29-buff-compact-second-source-result.md`, and
  `docs/research/2026-05-29-next-targetset-discovery.md` for exact target counts and
  blockers. Buff compact was refreshed on 2026-06-01 and now compares `3/3` again, but
  remains internal-layout-only and not release/public/runtime readiness.
  Dino now has `scripts/check_dino_scalar_readiness.py --json` as a read-only internal
  candidate gate over the redacted UFunction descriptor preflight for `dino-compact-intake`.
  It accepts the four `AddPassenger` pre-call copied scalars only, keeps
  `AddPassenger.ReturnValue` and `AllowCarryCharacter.ReturnValue` deferred, keeps
  `ACharacter` and `CanCarryPawn` recognition-only, and reports public/runtime/v1
  readiness false. It does not promote a Dino SDK, ABI, runtime observer, identity,
  lookup, mutation, return override, `ResourceHandle`, or v1 completion.
- Structure non-PIN copied-scalar evidence is historical legacy context at
  `/home/flowcommunity-ark/obelisk-artifacts/structure-nonpin-copied-scalar-policy-slice-20260530T100717Z/`.
  It excludes `VerifyPinCode`, copies only `SetVariant.{VariantIndex,bForceSet,ReturnValue}`,
  `AllowToggleActivation.ReturnValue`, and `CanSeat.{bForce,ReturnValue}`, but its artifact
  pack schema/gate sidecars are legacy and should not be cited as current normalized pack
  evidence. Prefer the current structure aggregate/census pack for active consume-only
  citations. This legacy root does not promote public `StructureEvents`, SDK callbacks,
  identity, lookup, mutation, return override, dispatcher/hook wiring, `ResourceHandle`,
  runtime observation, or probing.
- `structure-build-policy-offline-intake` now exists as a planning-only target set for
  `PrimalStructure.IsAllowedToBuild`, `PrimalStructure.BPIsAllowedToBuild`, and
  `PrimalStructure.BPIsAllowedToBuildEx`. It is in the `structures` lane and is not in
  release readiness. Planning-only second-source layout now accepts `3/3`; public/runtime/
  promotion gates, mutation, enforcement, return override, identity/lookup, and
  `ResourceHandle` all remain blocked.
- Focal UFunction snapshot planning helpers live in
  `scripts/ufunction_focal_snapshot_plan.py`; `build_reflection_inventory_pack.py` uses
  them for candidate-only exact snapshot command plans. Target-set bridge coverage proves
  named planning sets can emit exact `--snapshot-json` commands from unfiltered redacted
  inventory without adding release target-set regeneration claims.
  `scripts/plan_ufunction_focal_snapshots.py` consumes an already reviewed
  reflection-inventory pack plus exact targets/target files and emits candidate-only
  planned commands without rereading a core, executing commands, writing snapshots, or
  promoting target sets/runtime/API scope. For player identity, the 2026-05-31 workspace
  route produced a complete 12-target `players-identity-lifecycle-intake` reflection
  inventory pack and committed candidate fixtures for `ShooterPlayerController.ServerListPlayers` and
  `ShooterPlayerController.ServerKickPlayer`. A distinct vanilla-gdb candidate root at
  `/servidor/ark/workspace-offline/player-identity-offline-identity-vanilla-gdb-20260529T012853Z/focal-snapshots`
  now compares `12/12` accepted in planning-layout mode. A consume-only policy/lifecycle
  bundle at
  `/servidor/ark/workspace-offline/player-identity-principal-invalidation-policy-20260531T231247Z/`
  is accepted by the offline artifact gate. Passing both lifecycle-anchor and
  principal-invalidation manifests to the first-evidence readiness checker is no longer
  sufficient unless those planning artifacts are bound to the same first-evidence source
  artifact identity. The repo-local generated planning manifests now close that default
  provenance gap, so the active aggregate blocker is approved copied runtime principal
  lifecycle evidence, reported as `approved_runtime_evidence_missing`.
  `scripts/bind_player_identity_planning_sources.py` is the offline binder for that
  transition: it validates first-evidence, lifecycle-anchor, and principal-policy JSON,
  now rejects stale prebind provenance before writing outputs when lifecycle
  `artifact_identity.source_artifact_ids`, principal lifecycle source binding, or
  principal start/end anchors do not match the selected first-evidence/lifecycle source,
  emits bound lifecycle/principal planning artifacts plus a non-claim report, and rejects
  protected output paths and symlinks. Bound outputs are planning provenance only; they do
  not approve runtime evidence, public identity, public SDK readiness, or v1 completion.
  Route-gate passthrough for these bound artifacts is explicit: the repo-default route
  consumes the generated repo-local lifecycle/principal fallbacks and, with no approved
  runtime evidence, reports `approved_runtime_evidence_missing` as the next blocker. With
  accepted approved runtime evidence, the allowed locked blocker is
  `identity_public_contract_gate_missing`.
  `scripts/check_command_permission_route_gate_bound_identity_sources.py` is the
  checker-style wrapper for that explicit route: it uses transient bound artifacts under a
  non-protected temp root and still authorizes no runtime/server work or SDK readiness.
  The historical `/servidor/ark/workspace-offline/player-identity-principal-invalidation-policy-20260531T231247Z/`
  lifecycle/principal bundle remains standalone consume-only planning evidence but is no
  longer the default fallback. Regenerate or align source-bound manifests before expecting
  non-default inputs to advance to `approved_runtime_evidence_missing`, or the
  post-evidence route to advance to `identity_public_contract_gate_missing`.
  Later SDK-completion hardening also applies structured promotion-evidence requirements
  to command response and commands/replies: generic ABI/SDK paths plus prose terms no
  longer let those P0 rows count toward complete SDK accounting. Command response needs
  its structured public-readiness report plus executed ABI/SDK tests; commands/replies
  needs its structured readiness report, structured command-response dependency evidence,
  and executed ABI/SDK tests. Inventory copied-signal and ResourceHandle readiness
  scanners now reject additional generic readiness aliases (`v1_sdk_ready`,
  `release_ready`, `public_abi_ready`, and related ResourceHandle metadata booleans).
  Later follow-up wires ResourceHandle/object-identity readiness into SDK completion
  accounting, closes Structure census/build-policy alias/string overclaim gaps, rejects
  non-canonical command/permission route-gate overrides by default, and fixes
  commands/replies nested command-response structured evidence so future legitimate
  evidence can include the command-response executed-test report. Deferred next
  guardrails: replace inline executed promotion test reports with runner-emitted
  repo-relative JSON carrying current HEAD/argv/exit/output provenance, and add an
  offline ABI regression test for GameplayPolicyEvent multi-dispatcher partial
  registration rollback.
  The report still carries a requirements-only
  `first_evidence.runtime_principal_lifecycle_evidence` block for the future approved
  runtime window; it is not accepted evidence and must not be used for promotion. The
  optional runtime-principal lifecycle manifest checker accepts only a synthetic/redacted
  shape fixture and stays blocked on runtime promotion.
  Future runtime evidence must use the exact player-principal lifecycle window contract:
  single module, plugins disabled, dispatch limit `0`, no sibling observer/debug markers,
  checked `--window-manifest`, analyzer source path/SHA match, stable posture, rollback,
  no-claim semantics, and public/runtime/promotion readiness all false.
  Separately, all six `players-lifecycle-anchor-candidates` targets are reproducible in
  scratch base-vs-vanilla evidence with `accepted=6` and now have committed
  planning-only base fixtures under `players_lifecycle`; promotion still fails as
  planning-only with `target_set_not_release_readiness`. See
  `docs/research/2026-06-01-players-lifecycle-anchor-candidates-fixture-gap.md`.
- Player identity offline staging has a helper for the raw sibling layout:
  `scripts/prepare_player_identity_offline_raw_layout.py`. Use it only to stage explicit
  offline `ShooterGameServer` and core inputs into a
  `player-identity-offline-<run-id>/raw/` directory under a non-protected artifact root
  or the approved `/servidor/ark/workspace-offline` root. It does not create or approve
  cores, touch live server roots, or authorize server access or runtime/core changes.
  Current workspace run:
  `/servidor/ark/workspace-offline/player-identity-offline-identity-second-source-20260529T011227Z`.
  Current distinct second-source workspace run:
  `/servidor/ark/workspace-offline/player-identity-offline-identity-vanilla-gdb-20260529T012853Z`.
  The detailed stop/continue recipe remains in
  `docs/research/2026-05-31-player-identity-offline-pack-preflight.md`.
- `scripts/validate_player_identity_raw_inputs.py` is the read-only dry-run validator for
  an existing `player-identity-offline-<run-id>/raw/{ShooterGameServer,core}` pair. It
  rejects direct or symlink-resolved `/servidor/ark`, symlinks, wrong layout, empty files,
  and binary SHA mismatch; it hashes only the binary and treats the core as metadata-only.
- `scripts/check_reflection_inventory_pack_readiness.py --json` reports candidate-only
  planning boundaries: accepted reflection inventory is not identity, Inventory SDK,
  public SDK, runtime, lookup, or `ResourceHandle` promotion. Player-identity readiness
  requires full 12-target coverage and inventory rows for all 12
  `players-identity-lifecycle-intake` targets before focal planning can start.
- Player identity has a candidate-only privacy/invalidation contract in
  `docs/research/2026-05-31-player-identity-privacy-invalidation-contract.md`: future
  principals must be opaque copied POD values, generation-checked, process-local by
  default, and invalidated fail-closed. This does not promote public identity, lookup,
  persistence, platform ids, player names, `ResourceHandle`, UE pointers, or runtime
  access.
  The `obelisk.players-identity-principal-invalidation-policy.v1` schema is a
  planning/candidate-only policy artifact only; it does not unlock `player_identity`,
  permissions/admin, command response, commands/replies, or v1 SDK completion.
- Static admin thunk orientation for `ServerListPlayers` and `ServerKickPlayer` is
  hash-pinned, bounded, and now checks exact vtable-dispatch byte sequences. It remains
  candidate-only navigation evidence and does not replace core evidence, reflection
  inventory, focal snapshots, lifecycle anchors, or privacy/invalidation implementation.
- Permissions/admin has no public header symbols and no public cache ABI now. Any future
  permission query must carry principal generation/scope semantics and public cache ABI
  remains blocked until `policy_epoch` plus full generation/scope keying is promoted.
  No `allow` decision is valid without runtime-owned policy source/authority provenance,
  and public permission queries need owner-scoped rate-limit/audit gates.
- Plugin Hub guardrails are archived boundaries only until SDK completion: keep them
  non-promotional and do not reopen examples, packaging, intake tooling, or review while
  the identity/principal -> permissions/admin -> command response -> commands/replies
  route remains open. Storage, mutation, ResourceHandle, and gameplay module surfaces
  remain later blockers or scoped side lanes unless `CURRENT.md` routes them.
- Public v1 completion evidence rejects strict blocker evidence paths or schema/status
  fields that are candidate/planning/orientation/preflight/readiness/consume-only/
  evidence-only. Do not let static orientation, planning docs, or candidate reports
  masquerade as promoted ABI or SDK consumer evidence.
- Command/chat response-path static orientation for `ClientChatMessage`,
  `ClientServerChatMessage`, and `ClientServerChatDirectMessage` is complete for the
  current reviewed offline binary and remains candidate-only planning for
  `obelisk.command_chat_response_path.v1`. It is not a pending primary task and must not
  imply replies/send-chat, command router, identity, permissions, raw UE/FString
  exposure, mutation, runtime readiness, or public SDK promotion. Details:
  `docs/research/2026-05-31-command-chat-response-static-orientation.md` and
  `docs/research/2026-05-31-command-chat-response-thunk-orientation.md`.
  The repo fixture root still reports `missing_base_snapshot=3` for
  `command-chat-response-route-planning`. The durable offline root
  `/servidor/ark/workspace-offline/command-chat-response-route-planning-distinct-second-source-20260601`
  now preserves base and vanilla-gdb focal snapshots with distinct evidence identity,
  `manifest.json`, `SHA256SUMS`, and
  `command-chat-response-route-planning-readiness.json`. Planning-layout comparison
  reports `targets=3`, `second_source_accepted=3`, `second_source_inconclusive=0`,
  `planning_layout_gate.ready=true`, `promotion_ready=false`, `public_sdk_ready=false`,
  and `runtime_ready=false`. This closes response-route planning evidence identity only;
  accepted planning is not public SDK readiness, runtime readiness, reply/send-chat ABI,
  command router, or ABI/runtime wiring.
- Mission copied-bool is the selected v0.2 internal hardening lane only. Keep it
  internal/test-only and default-off; it does not promote a Mission SDK, runtime observer,
  public callback ABI, authority, identity, mutation, return override, or v1 completion.
  Details: `docs/research/2026-05-31-v02-module-priority.md`,
  `docs/research/2026-05-29-mission-reflection-internal-readiness.md`, and
  `docs/research/2026-05-30-mission-copied-bool-observer-plan.md`.
- Structure aggregate/census remains a product-facing planning direction only. Keep
  it planning/consume-only with no runtime observer, callback ABI, descriptor, capability
  bit, public StructureEvents SDK, identity, lookup, mutation, enforcement, return
  override, or v1 completion claim. Details:
  `docs/research/2026-05-31-aggregate-census-product-priority.md` and
  `docs/research/2026-05-31-structure-aggregate-census-v0.md`.
  The offline root
  `/servidor/ark/workspace-offline/structure-observer-intake-refresh-20260529T141455Z/ufunction-snapshots`
  has all six files but remains `second_source_inconclusive=6` because bool metadata is
  incomplete; do not treat it as accepted second-source evidence.
  The regenerated bool-tail root was materialized under the approved offline workspace at
  `/servidor/ark/workspace-offline/structure-aggregate-census-planning-second-source-bool-tail-20260530-offline-regenerated`
  with `manifest.json`, `SHA256SUMS`, the six sanitized `sdk_structures` snapshots, and
  `structure-aggregate-census-planning-readiness.json`. Re-running
  `scripts/compare_reflection_snapshots.py --planning-layout-intake --target-set structure-aggregate-census-planning`
  against its `ufunction-snapshots` root reports `second_source_accepted=6`,
  `planning_layout_gate.ready=true`, `ready_scope=planning_only`,
  `promotion_ready=false`, `public_sdk_ready=false`, and `runtime_ready=false`. This
  closes the durable second-source layout gap for Structure aggregate/census planning
  only; it still does not promote `StructureEvents`, a public Structure SDK, identity,
  lookup, mutation, return override, runtime hooks, enforcement, `ResourceHandle`, or v1
  completion.
- Inventory item return-only copied signals are the preferred no-core side lane because
  they already ride copied `GameplayPolicyEvent` evidence. They remain consume/evidence
  only and do not promote public Inventory SDK, public Items SDK, identity, lookup,
  mutation, return override, runtime validation, or v1 completion. Details:
  `docs/research/2026-05-30-item-return-only-policy-slice.md`.
- Transfer, Dino, Buff, Tribe, ResourceHandle, static GObjects/FUObjectItem, UObject flag,
  weak-helper, redacted-signature, and offline manifest work remains internal or
  candidate-only. Do not duplicate their artifact roots, hashes, or gate sidecars here;
  use the dated `docs/research/` notes and gate output as the durable evidence catalog.
  Do not rerun broad FName, GObjects, or core scans for ResourceHandle unless the binary
  hash changes, evidence is contradicted, or an approved focused runtime lifecycle/reuse
  plan changes scope. If the reviewed binary/artifact FName root slot is already known,
  pass it explicitly to evidence-pack, GObjects sampling, or snapshot regeneration
  tooling instead of running broad reverse FName scans.
- If explicitly tasked with chat command ergonomics, start as a plugin-local parser/helper
  over the existing copied `ChatMessageEvent`, not as a new ABI. Keep output
  callback-scope only and keep player identity, permissions, targeting, chat send/reply,
  moderation/blocking, mutation, and return override blocked.

## Tooling Baseline

- Offline core evidence-pack outputs and release second-source readiness report paths must
  stay in `/servidor/ark/workspace-offline` or another operator-approved offline root
  that resolves outside protected live-server paths. Direct and symlink-resolved
  live-server input/output paths are rejected; `/servidor/ark/workspace-offline` is the
  explicit exception.
- `scripts/validate_offline_artifact_gate.py` rejects unsupported manifest schemas; add
  schema-specific validation before accepting any new offline artifact schema.
- `obelisk.resource-handle-serial-scan.v1` is consume-only internal evidence. It must be
  `candidate_blocked` with `internal_offline_scan_candidate`, verified redacted
  provenance, required `scan_limit` matching provenance, coherent
  `consume_gate_expectation`, and real copied-core hash checks; it is always blocked in
  promote mode.
- Future ResourceHandle runtime observations are gated by candidate-only
  `obelisk.internal-uobject-revalidation-runtime-rejection-samples.v1` and
  `obelisk.internal-uobject-revalidation-runtime-serial-semantics.v1` manifests. These
  schemas require redacted run identity, privacy-safe copied output, the strict serial
  policy source artifact, consume-only acceptance, promote-mode blockers, and no
  post-callback lookup, public `ResourceHandle`, object identity, mutation, return
  override, raw UE pointer, serial-value, or protected-path disclosure. They are not public
  SDK/runtime-readiness contracts and cannot be satisfied by offline or copied-core scans.
- Raw core captures under `/servidor/ark/obelisk/dumps` are protected storage, not direct
  promotion inputs. Promotion tooling consumes hardlinked or copied offline artifacts.
- Second-source intake must derive artifact-specific FName root, validate GObjects,
  regenerate snapshots, and compare fail-closed with `--readiness-report
  --fail-on-readiness-gaps`.
- `scripts/check_release_readiness.sh --require-second-source-readiness` defaults to the
  public RC UFunction target sets: `minimal-second-source-intake`,
  `structure-observer-intake`, `item-return-only-policy-slice`, and
  `chat-message-intake`. ScriptStruct promotion requires an explicit ScriptStruct target
  set.
- Reflection snapshot readiness reports are consumable only when they come from
  `gate_mode=second_source_promotion`, name at least one target set, and keep
  `promotion_ready=false`; this is layout evidence, not public API/runtime promotion.
- `scripts/assemble_rc_ufunction_second_source_root.py` assembles those four accepted
  UFunction roots into one release-gate root. It copies existing sanitized snapshots only
  and does not regenerate evidence. It produced
  `/tmp/obelisk-rc-ufunction-second-source-root` with 12 unique snapshots from the current
  accepted minimal/structure/item-return/chat roots, and each target set passed
  `compare_reflection_snapshots.py --readiness-report --fail-on-readiness-gaps` against
  that assembled root. The helper manifest is path-redacted; do not preserve or publish
  older `/tmp` manifests that contain absolute source roots.
- Static-only global evidence uses `scripts/build_static_global_promotion_evidence.py`,
  now with complete top-level `artifact_identity` and gate-side canonical hash
  validation. `promotion_gate.ready` remains false for static global candidates, and this
  still does not promote public GObjects, ResourceHandle, identity, lookup, mutation, or
  return override.
- UObject flag-policy reports now follow the same strict artifact identity contract:
  `build_uobject_flag_policy_report.py` emits complete identity, the refresh wrapper can
  pass explicit identity IDs, `validate_offline_artifact_gate.py` verifies the canonical
  report hash in consume mode, and the ResourceHandle evaluator counts complete policy
  identity without promoting public `ResourceHandle` or post-callback lookup.
- Weak-helper evidence archives use `scripts/build_weak_helper_provenance_bundle.py`.
  Missing or invalid source sidecars are preserved as blockers and keep
  `promotion_ready=false`; the current bundle is valid archival material but blocked by
  missing original source sidecars.

## Historical Checkpoint Baseline

- Published RC baseline is for the v0.1 public surface: `ObeliskApi` v1 is frozen
  around Linux runtime, ProcessEvent hook infrastructure, plugin lifecycle, central install layout,
  `oBaseEvents`, `GameplayPolicyEvent`, minimal copied `ChatMessageEvent`,
  `DescribeResourceKind`, `DescribeGameplayPolicyEventKind`, and process-local
  owner-token timers.
- `plugins/oPolicyAudit` is experimental and excluded from the default build/release
  scope unless `OBELISK_BUILD_EXPERIMENTAL_PLUGINS=ON`.
- Historical dirty/offline release-gate runs are smoke evidence only. The published
  `v0.1.0-rc.2` baseline was tagged only after the release gate without `--allow-dirty`
  and exact tag/ref verification. Do not keep reworking that RC unless a critical fix
  requires a new RC tag.
- `docs/research/2026-05-29-rc-checkpoint-slicing-plan.md` is historical recovery
  context, not active routing for the current head. Use `git log --oneline -1` for the
  current head, use `CURRENT.md` for current blockers, and use the accepted
  `ChatMessageEvent` evidence notes above for chat facts. Keep future changes focused by
  subsystem rather than by the old 0-pre/0a/0b slicing sequence.
- Current ResourceHandle pointers:
  `docs/research/2026-05-30-post-rc-offline-resourcehandle-priority.md` and
  `docs/research/2026-06-01-object-identity-resource-handle-v1-blocker.md`. The old
  flag-policy artifact is obsolete; the rich-provenance refresh remains preserved and
  consume-accepted/promote-blocked, and the strict serial reuse/wraparound policy is
  candidate-only. `scripts/build_resource_handle_zero_serial_negative_samples.py` now
  produces a deterministic zero-serial negative cohort from both existing cores with
  positive anchor index `50834`. Do not rerun broad FName, GObjects, or core scans for
  ResourceHandle; runtime rejected-object samples and runtime serial reuse/wraparound
  semantics still require an approved live-ops brief.
- Weak-helper caller-mode manifests now require embedded verified provenance for
  `ghidra_stdout`, `r2_windows`, and `direct_call_counts`; consume acceptance remains
  internal static evidence only and promote mode stays blocked.
- ResourceHandle remains post-RC/internal only. The copied/offline core blocker artifact
  now yields 44 coherent `0x4000` rejected-object candidates, reconciled as
  `ParticleSystemComponent0` under `Text_Actor` / `Text_Actor_C`; this is internal
  blocker evidence only. Avoid more broad ResourceHandle scanning unless the binary hash
  changes, evidence is contradicted, or an approved focused runtime lifecycle/reuse plan
  explicitly changes scope. Runtime lifecycle/reuse evidence still must pass the
  candidate-only runtime rejection-samples and runtime serial-semantics schemas above.
- `obelisk.resource-handle-serial-scan.v1` is now gated for that exact internal candidate
  shape: consume requires coherent `flag_rejection_candidate_samples`, a required
  `binary_sha256`, verified `core_sha256` bytes, required `scan_limit` matching
  provenance, unique candidate indices below `scan_limit`, and `core_path` under the
  approved offline workspace; promote remains blocked. Use
  `scripts/scan_resource_handle_serials.py --gate-ready` only for post-RC/internal
  consume-mode scans, not as a public RC gate.
- Do not retroactively promote post-RC work into `v0.1.0-rc.2`: ResourceHandle,
  GNames/GObjects promotion, full UE4 reflection, public Inventory SDK, public
  StructureEvents, chat APIs beyond minimal copied `ChatMessageEvent`,
  player/tribe/dino/buff/transfer APIs, mutation, return overrides, public
  `CallProcessEvent`, background worker plugins, operator lifecycle commands, and
  ScriptStruct/transfer promotion remain blocked unless a later focused gate changes
  scope.
- Transfer `bAccept` hook-side recognition now exists only as a CTest helper in
  `hooks/ProcessEventTransferReflection.{h,cpp}` plus
  `process_event_transfer_reflection_tests`; keep it out of runtime, public headers,
  ops, and plugin surfaces. It remains a useful bool-layout fixture but is lower product
  value than Structure aggregate/census planning and Player identity research because it
  lacks identity, payload correlation, cross-map semantics, enforcement, and privacy
  policy. This is not RC public SDK/API scope and does not change the RC public API.
  None of these promote public Mission/Items/Transfer SDKs, public callbacks, ABI,
  markers/env, runtime logs, hook wiring, mutation, return override, object identity,
  lookup, or `ResourceHandle`, and this handoff does not authorize Transfer runtime work.
  Start from the dated research notes, not public API docs; any live observation,
  dispatcher lifecycle, ABI, or SDK policy decision needs a separate scoped gate.
- Local offline evidence tooling now rejects GObjects two-core manifest artifact identity
  hash drift and ScriptStruct inventory bool-tail gaps. The known Transfer ScriptStruct
  durable artifacts under `/servidor/ark/workspace-offline` are stale until regenerated
  with `bool_field_size` and `bool_byte_offset`; do not cite the old readiness report as
  current acceptance.
- Runtime lifecycle callback-cleanup debt is addressed in post-RC head: if PluginManager
  callback cleanup fails, unload skips `dlclose`, retains the plugin mapped for retry,
  preserves owner-token unregister while unloading, and does not repeat plugin shutdown on
  the retry.
- Runtime dispatcher hardening: hook-called Chat, Structure, and Inventory dispatchers
  must fail closed on setup/internal errors instead of rethrowing into `ProcessEvent`.
  Chat dispatch snapshots registration ids, skips callbacks removed during the same
  dispatch, invokes callbacks outside dispatcher mutexes, and defers `DestroyUserData`
  until outermost dispatch completion.
  Gameplay callback-scope detection is shared across gameplay families so callback-
  initiated cross-family unregister cannot deadlock. Structure/Inventory unregister waits
  for the other in-flight `GameplayPolicyEvent` family before returning; Chat remains
  non-blocking for cross-family cleanup. Non-callback owner/plugin cleanup still waits for
  in-flight dispatch and deferred `DestroyUserData` cleanup before returning.
- RC API audit found and fixed owner-token capability-snapshot blockers for
  `ChatMessageEvent`, `GameplayPolicyEvent`, and global ProcessEvent callback
  registration. Public gameplay/chat callback bridges also catch plugin exceptions and
  continue dispatch; `PluginManagerTests` covers these regressions.
- Post-RC command/chat response-path orientation exists as candidate-only tooling:
  `scripts/check_command_chat_response_static_orientation.py --json` validates bounded
  static clues for `ShooterPlayerController.ClientChatMessage`,
  `ShooterPlayerController.ClientServerChatMessage`, and
  `ShooterPlayerController.ClientServerChatDirectMessage` on the reviewed
  `ShooterGameServer` SHA. It does not prove replies, send-chat, command routing,
  identity, permissions, runtime readiness, or public SDK promotion.
- Player-identity preflight contract drift was corrected: reflection-inventory readiness
  now emits the accepted pack fields consumed by the combined identity preflight, and
  `prepare_player_identity_offline_raw_layout.py` supports
  `--obelisk-commit <reviewed-obelisk-id>` so evidence commands can name the reviewed
  checkpoint explicitly instead of relying on Git HEAD.
- The combined identity readiness wrapper now accepts the real lower-level flat
  `target_set_coverage` shape from `check_reflection_inventory_pack_readiness.py`, with a
  regression test preserving candidate-only/non-promotion semantics. The raw layout helper
  rejects artifact roots under the repository to match
  `validate_player_identity_raw_inputs.py` and the offline preflight note.
- Earlier local integration checkpoint on 2026-06-02 hardened SDK/release accounting but
  did not change readiness:
  - `scripts/check_public_sdk_v1_completion.py` requires promoted P0
    `executed_test_report` evidence to be a repo-relative
    `obelisk.promoted-surface-test-execution-artifact.v1` JSON artifact tied to the
    current HEAD, surface id, command/argv, zero exit code, and output/provenance hash.
    Inline self-attested executed-test objects no longer satisfy P0 structured evidence.
  - P0 rows cannot count toward complete-SDK progress while the default
    command/permission route gate remains locked/planning-only; rows expose
    `route_gate_claim_satisfied=false` and promoted-looking rows are blocked by
    `p0_dependency_chain_route_gate_locked`.
  - `scripts/check_release_readiness.sh` rejects thin second-source readiness JSON that
    omits the explicit layout-only/non-promotion envelope. Valid release readiness
    fixtures now include `ready_scope=layout_only`, `layout_ready=true`,
    promotion/public/runtime false, `evidence_scope=second_source_layout_evidence_only`,
    `not_promoted_surfaces`, and `non_claims`.
  - Release statement scanning treats `not only`/`not merely` as affirmative overclaim
    context.
  - `PluginManagerTests` includes a test-only injected ItemReturn registration failure
    proving public `GameplayPolicyEvent` multi-dispatcher registration rolls back
    Structure/Inventory/ItemReturn subscriptions and returns handle `0`.
- Follow-up on the same checkpoint tightened replay and promote-mode gaps:
  - P0 executed-test artifacts now require canonical producer/checker/timestamp
    provenance and SHA256-bound `docs/public_sdk_surfaces.json` plus
    `include/obelisk/ObeliskApi.h` input bindings.
  - P0 completion accounting stays route-gate-blocked for any planning-only, locked,
    invalid, blocker-bearing, or identity-blocked route, including
    `approved_runtime_evidence_missing`; only a non-planning, unlocked, promotion/public/
    runtime-ready route with no current blocker can satisfy P0 claim accounting.
  - `validate_offline_artifact_gate.py` blocks all reflection snapshot readiness reports
    in promote mode, including `promotion_gate.ready=false`, and rejects
    `promotion_ready`, `public_sdk_ready`, or `runtime_ready` overclaims on not-ready
    reports.
  - `compare_reflection_snapshots.py` was audited and already emits the required
    layout-only readiness envelope; no producer edit was needed.
- Delegated post-compaction hardening on 2026-06-02 added three local guardrail/runtime
  fixes without changing SDK readiness:
  - P0 executed-test artifacts now require any top-level or nested output/provenance hash
    to be a valid SHA-256 digest; malformed non-empty hash strings are rejected.
  - Offline artifact validation now recursively rejects generic true public/runtime/
    release/v1/SDK/promotion claim aliases in candidate/consume manifests and artifact
    pack children.
  - `PluginManager::UnloadAll()` preserves previously retained retry plugins if a later
    retention-tracking failure aborts the pass, and public `CallProcessEvent` docs now
    state the init-window-only behavior. No server/runtime run, GitHub publication, tag,
    or Discord action was performed.
  - Latest validation for this round: `plugin_manager_tests` passed;
    `scripts.test_check_public_sdk_v1_completion` passed 136 tests;
    `scripts.test_validate_offline_artifact_gate` passed 354 tests;
    `check_command_permission_route_gate.py --json` remained planning-only at the then
    current identity provenance blocker; and
    `check_public_sdk_v1_completion.py --json` remained fail-closed with
    `stable_claim_allowed=false`, complete-SDK progress `0/12`, and P0 progress `0/4`.
- Delegated route/runtime rollback hardening on 2026-06-02 added four scoped outcomes and
  closed all sub-agents:
  - Command route gate now verifies the command response child readiness report is bound
    to its embedded `readiness_root` and agrees with caller-supplied response root/path
    context.
  - Item-return standalone readiness now rejects positive public gameplay status strings
    that imply public SDK, runtime, ResourceHandle, v1, release, or promotion readiness.
  - Player-identity first-evidence readiness now emits a structured offline
    `planning_provenance.next_action` for
    `lifecycle_anchor_first_evidence_provenance_unbound`: regenerate or select
    lifecycle/principal planning manifests bound to current first-evidence, then verify
    with the bound identity route wrapper. Expected no-approved-runtime-evidence next
    blocker after correct alignment is `approved_runtime_evidence_missing`.
  - Public chat and gameplay-policy registration rollback now inerts released callback
    state before rollback. If rollback unregister fails, the orphan cannot invoke plugin
    code and owner cleanup still removes it. Test-only hooks cover both paths.
  - Validation: 86 focused Python tests passed, `plugin_manager_tests` passed,
    full `cmake --build build -j$(nproc)` passed, and `git diff --check` was clean.
    Default route and SDK completion remained fail-closed at the then current identity
    provenance blocker, with `stable_claim_allowed=false`, complete-SDK progress `0/12`,
    and P0 progress `0/4`.
- Delegated player-identity planning-source producer round on 2026-06-02 closed all
  sub-agents and added the offline tool for the current P0 provenance blocker:
  - `scripts/build_player_identity_planning_source_manifests.py` rebuilds
    `players-identity-first-evidence.json` from sanitized UFunction snapshots and emits
    source-aligned lifecycle/principal planning manifests plus a build report.
  - The producer validates generated first-evidence, lifecycle, principal, and binder
    alignment before writing outputs; outputs are planning-only and keep promotion/public
    SDK/public ABI/runtime/v1 readiness false.
  - A real transient producer run plus
    `scripts/check_command_permission_route_gate_bound_identity_sources.py` returned
    `valid=true`, `blockers=[]`, and
    `critical_path_phase.current_blocker=approved_runtime_evidence_missing`, with
    `runtime_work_authorized=false` and `server_operations_authorized=false`.
  - The default route now consumes the generated repo-local source-aligned manifests and
    reports `approved_runtime_evidence_missing`. SDK completion remains fail-closed:
    `stable_claim_allowed=false`, complete-SDK progress `0/12`, P0 progress `0/4`.
  - Next true blocker is approved copied runtime principal lifecycle evidence; no runtime,
    marker/env/server action is authorized without a fresh live-ops brief.
- Delegated lifecycle-anchor snapshot provenance round on 2026-06-02 closed the remaining
  offline hash-binding gap in the explicit bound identity route:
  - Four read-only sub-agent scopes were lead-delegated and closed: offline identity
    provenance, SDK-route overclaim audit, UE4 snapshot fixture provenance, and
    handoff/knowledge continuity.
  - `bind_player_identity_planning_sources.py` resolves required accepted lifecycle
    anchors through `snapshot-root/manifest.json`, rejects duplicate/missing/protected or
    target-mismatched snapshot rows, hashes the real snapshot files, and fails closed on
    stale or missing anchor `evidence.source_snapshot_sha256`.
  - `build_player_identity_planning_source_manifests.py` and
    `check_command_permission_route_gate_bound_identity_sources.py` both enforce and emit
    `lifecycle_snapshot_root_binding`. The default generated route remains valid only as
    planning and advances to `approved_runtime_evidence_missing`.
  - SDK-route audit found no public SDK/runtime/permissions/admin/commands overclaim path
    from this provenance fix. SDK completion remains fail-closed with
    `stable_claim_allowed=false`.
- Delegated runtime-evidence preparation round on 2026-06-02 tightened the next
  player-principal lifecycle request/manifest route without authorizing runtime:
  - Four read-only sub-agent scopes were lead-delegated and closed: live-ops brief
    completeness, runtime observer safety, approved-evidence provenance, and
    handoff/knowledge continuity.
  - `prepare_player_principal_lifecycle_window_request.py` now emits a structured
    `operator_live_ops_brief` with target, reviewed server binary path/SHA, feature
    gates, marker/env snapshot, start/restart/stop window, notice path, evidence capture,
    rollback, final posture, and exact target-bound post-run verification commands. The
    request checker validates the brief exactly and rejects windows over ten minutes plus
    restart/final-posture incoherence.
  - Request packs now forbid `enable-inventory-action-redacted-observer`, bind
    `server_binary_path`, and the window manifest checker rejects request-pack
    `obelisk_commit`/binary drift before evidence can be accepted.
  - Window/approved evidence now preserves and validates canonical rollback delta
    `removed_observer_env_and_markers_preserved_disable_plugins`.
  - Request packs are planning artifacts only: no runtime/server/marker/env work is
    authorized, and acceptance keeps runtime/public/promotion/v1 readiness false with
    current-turn operator approval still required.
- Delegated preflight-provenance round on 2026-06-02 closed the next stale/swapped
  sidecar gap before any runtime request:
  - Four read-only sub-agent scopes were lead-delegated and closed: preflight JSON
    schema/binding, window manifest/evidence replay, live-ops safety, and
    handoff/knowledge continuity.
  - `check_player_principal_lifecycle_preflight.sh --json` now accepts all-or-nothing
    evidence binding via `--run-id`, `--target-map`, `--window-manifest`,
    `--copied-log`, and `--evidence-dir`/`--copied-evidence-dir`. `--target-map` binds
    sidecar provenance without triggering procfs posture checks.
  - Preflight JSON now records run id, target instance/map, copied log, copied evidence
    dir, window manifest path, and `checked_at_utc`; the window-manifest checker compares
    those anchors against the resolved manifest, copied log, approved window, capture
    interval, and rollback end. A stale, late, or swapped preflight sidecar fails even if
    the outer manifest SHA is refreshed.
  - Request-pack binding remains indirect through manifest sidecar validation and
    request-check replay; there is no preflight `request_pack_path` field. No
    runtime/server/marker/env work is authorized by these artifacts.
- Delegated operational-window projection round on 2026-06-02 closed the next approved
  evidence semantic-drop gap:
  - Four read-only sub-agent scopes were lead-delegated and closed: approved-manifest
    projection, replay attack path, live-ops authorization safety, and handoff continuity.
  - The window manifest report now emits approval text, approved/capture/rollback
    timestamps, `notice_sent`, `log_budget`, and fixed window non-claims.
  - The approved runtime evidence manifest now preserves those fields inside
    `operational_window`; the approved-evidence checker validates them and includes every
    allowed `operational_window` key in replay coverage.
  - This is consume-only runtime evidence hardening. It does not authorize runtime/server
    operations, marker/env edits, Discord, publication, public identity, permissions,
    commands, or stable SDK claims.
- Delegated identity-public-contract route round on 2026-06-02 closed the post-approved
  runtime-evidence route modeling gap:
  - Four read-only sub-agent scopes were lead-delegated and closed: public-contract
    gap/readiness, route composition, privacy/redaction, and handoff/research continuity.
  - The gap report remains the correct current no-runtime-evidence blocker and keeps
    `privacy.identifier_redaction` as the primary offline gap. The readiness checker is
    the post-evidence path and already rejects public-header/readiness overclaims.
  - `check_command_permission_route_gate.py` now accepts
    `identity_public_contract_gate_missing` as an allowed identity lock blocker only while
    planning-only/downstream unlock flags remain false. The bound identity wrapper accepts
    the same post-evidence blocker as locked planning, not runtime approval.
  - `check_public_sdk_v1_completion.py` now requires player-identity structured contract
    evidence to retain `next_blocker=identity_public_contract_gate` and unresolved
    `privacy.identifier_redaction`; a minimal optimistic contract report is invalid.
  - This round does not authorize runtime/server operations, marker/env edits, Discord,
    publication, public identity, permissions/admin, command response, commands/replies,
    public header symbols, or stable SDK claims.
- Delegated route-lock/evidence-hardening round on 2026-06-02 closed the next P0
  accounting ambiguity:
  - Four read-only sub-agent scopes were lead-delegated and closed: route/accounting,
    permissions/admin dependency evidence, side-lane SDK accounting, and handoff
    continuity.
  - Route locks now dedupe the post-approved-runtime-evidence state:
    `identity_public_contract_gate_missing` emits
    `blocked_until=[reviewed_identity_public_contract]`, while
    `approved_runtime_evidence_missing` still emits
    `blocked_until=[approved_runtime_principal_lifecycle_evidence,
    reviewed_identity_public_contract]`.
  - Player-identity structured contract evidence in
    `check_public_sdk_v1_completion.py` must now preserve the full producer blocker set,
    `blockers=[]`, and `resolved_inputs=[runtime.lifecycle_evidence]`; truncated or
    checker-blocked reports remain invalid.
  - P0 SDK accounting explicitly keeps `identity_public_contract_gate_missing`
    non-counting.
- Follow-up mission-leaf accounting integration closed the deferred side-lane finding:
  top-level SDK completion now runs
  `check_mission_transfer_dino_tribe_v1_outcome_accounting.py` so umbrella wording
  cannot bypass explicit mission/transfer/dino/tribe/buff leaf outcomes. This is
  accounting-only; SDK completion remains fail-closed with
  `stable_claim_allowed=false`, complete-SDK progress `0/12`, and P0 progress `0/4`.
- Follow-up permissions/admin certificate guardrail closed the deferred P0
  dependency-evidence gap: permissions/admin structured promotion evidence now needs a
  matching player-identity promotion certificate bound to `obelisk.player_identity.v1`,
  P0 chain position 1, and a reviewed artifact hash. This is accounting-only and does
  not promote identity, permissions/admin, public ABI, runtime readiness, or SDK
  completion.
- Follow-up command-response provenance guardrail now requires non-default
  command-response readiness JSON to bind `source_root` plus
  `scripts/compare_reflection_snapshots.py` producer argv for
  `command-chat-response-route-planning`; default legacy offline readiness remains
  planning-only until regenerated. P0 identity build-report regression now proves valid
  player-principal request packs do not satisfy approved runtime evidence. Follow-up
  commands/replies hardening now requires the child response-path report at
  `<response-path-report-root>/command-chat-response-public-readiness.json`, with the
  route gate forwarding a temp report root while preserving the original response
  readiness root. SDK structured promotion evidence for command response/replies now
  requires those planning-checker source-artifact bindings before promoted rows can
  count. This remains provenance-only, not response/replies readiness.
- Follow-up default identity planning-source provenance closure generated repo-local
  source-bound planning manifests in `docs/research/player-identity-planning-sources/`.
  The default no-runtime route now reports
  `critical_path_phase.current_blocker=approved_runtime_evidence_missing` while staying
  locked/planning-only with all public/runtime/promotion/SDK readiness flags false. SDK
  completion remains fail-closed with `stable_claim_allowed=false`, complete-SDK progress
  `0/12`, and P0 progress `0/4`. Next true blocker is approved copied runtime principal
  lifecycle evidence; no runtime/server operation is authorized by this planning closure.
- Follow-up delegated runtime-evidence request hardening closed the next offline hygiene
  gaps before any live window: request-pack generation rejects expired approved windows,
  `check_player_principal_lifecycle_window_request.py` replay-checks the exact
  `operator-approval-request.md` sidecar beside JSON/env, bundle preflight validates any
  present approved runtime manifest with the approved-evidence checker, and SDK blocker
  guidance no longer asks for already-closed bound lifecycle provenance. This does not
  authorize runtime/server work. The next offline public-contract lane is an
  identity-specific `privacy.identifier_redaction` policy/checker over sanitized snapshots.
- Follow-up guardrail pass added a standalone offline identifier-redaction evidence
  checker for sanitized player-identity manifests, expanded the route-gate claim scanner
  to reject broad public SDK/public header/v1 completion/stable-claim overclaims, and
  made request-pack preparation/checking reject already-started approved windows. This is
  still offline-only: no runtime/server operation, public header, public ABI, promotion,
  SDK completion, or release claim is authorized.
- Follow-up delegated guardrail pass registered the identifier-redaction checker as
  external contract-review intake only, pinned operator Markdown sidecar replay through
  window-manifest/approved-evidence/bundle-preflight paths, required approved-manifest
  preflight to see checker `ready` plus exit zero, and blocked rejected route-gate reports
  from giving P0 route credit in SDK accounting. Broad offline UE4/dump rediscovery was
  explicitly lower value for the current blocker.
- Follow-up delegated guardrail pass integrated the active useful findings from four
  read-only agents: stricter identifier-redaction `sample_logs` schema
  (`event`, `principal_present`, allowlisted `redaction_reason_flags` only), optional
  public-contract readiness consumption of identifier-redaction evidence as
  contract-review input only, and approved-runtime-evidence operational sidecar
  short-circuiting before `sha256_file()` on protected, symlinked, or non-approved paths.
  Runtime/ABI and SDK wording audits found no higher-value blocker than the current
  request/contract gates; route/SDK remain fail-closed with
  `approved_runtime_evidence_missing`, `stable_claim_allowed=false`, complete SDK `0/12`,
  and P0 `0/4`.
- Follow-up delegated evidence-completion guardrail pass integrated four more scoped
  read-only findings: runtime principal lifecycle request/window checks now require
  checker `ready=true` plus exit zero, private player-identity candidates must document
  stale-handle fail-closed tuple semantics, inventory target-set evidence must carry
  pinned scope/report accounting, and SDK release wording rejects bare
  "complete/full/production/stable SDK" claims. Canonical route gate remains
  planning-only at `approved_runtime_evidence_missing`; SDK completion remains expected
  fail-closed with `stable_claim_allowed=false`, complete SDK `0/12`, and P0 `0/4`.
- Follow-up delegated guardrail pass integrated first-evidence request-pack sidecar replay,
  identifier-redaction evidence as non-routing contract-review input only, release
  statement accounting for alternate allowed scoped outcomes, and hash-bound replay of the
  raw approved runtime-principal manifest before player-identity structured promotion
  evidence can count.
- Follow-up delegated SDK accounting pass integrated the pending Structure side-lane:
  `check_public_sdk_v1_completion.py` now accepts Structure census/build-policy checker
  overrides, runs both child reports, includes them in canonical JSON, adds blocker
  guidance, and tests missing checkers/overclaim/fail-closed cases.
- Follow-up delegated SDK guardrail pass closed the active-input binding gap: promoted P0
  executed-test artifacts and command-response/commands-replies readiness source artifacts
  must now match the active `--manifest` and `--public-header`, including nested
  command-response dependency evidence inside commands/replies. The same round fixed the
  Structure build-policy standalone checker scope so unrelated manifest-wide public SDK
  wording and unrelated promoted surfaces no longer produce Structure blockers; canonical
  build-policy now reports `ready=true,status=accepted_planning_only`, while SDK
  completion remains fail-closed at complete SDK `0/12`, P0 `0/4`, and
  `stable_claim_allowed=false`. Next offline identity side-lane: sanitized
  `privacy.identifier_redaction` evidence as contract-review input only.
- Follow-up delegated identity-redaction pass added
  `docs/research/2026-06-02-player-identity-identifier-redaction-evidence.json` and
  hardened `check_player_identity_identifier_redaction_evidence.py`: all required
  identifier classes must be `private-redacted`/`forbidden`, raw identifier material is
  rejected anywhere in the evidence manifest, and both decision-manifest logging-policy
  wordings are accepted. The artifact passes standalone intake as
  `resolved_inputs=[privacy.identifier_redaction]` and all readiness/header flags false.
  Public-contract readiness consumes it only as contract-review input; SDK and route gates
  remain fail-closed at `approved_runtime_evidence_missing`, SDK `0/12`, P0 `0/4`.
- 2026-06-02 delegated gap/runtime audit round: public-contract gap report now consumes
  the sanitized redaction evidence and moves the visible offline gap to
  `lifetime.generation_scope_invalidation` without opening readiness. First-evidence,
  route, and SDK aggregation were updated for the new report shape. Runtime evidence bundle
  building now calls the window-manifest checker with explicit `--post-window-replay`,
  which tolerates only nested `approved_window_expired` after the capture window; normal
  pre-window request approval remains strict. No runtime/server operation was performed.
- 2026-06-02 follow-up delegated lifetime/P0 audit: public-contract gap/readiness now also
  consume the existing repo-local `players-identity-principal-invalidation-policy` in
  consume mode as `lifetime.generation_scope_invalidation.candidate_policy`. This is
  candidate-only policy review evidence; `lifetime.generation_scope_invalidation` remains
  the visible gap, `principal_invalidation_ready=false`, and SDK/P0 remain fail-closed.
  Bundle post-window replay also rejects contradictory ready reports with retained blockers.
- 2026-06-02 follow-up delegated SDK/contract audit: SDK completion now has a regression
  assertion that `command_permission_route_gate.completion_gate_accepted=true` while the
  route is still `planning_only=true` does not satisfy P0 route credit or increment
  `p0_chain_promoted_count`. The player-identity gap report now emits
  `remaining_contract_gate_inputs` and `next_offline_actions`, making explicit that the
  candidate principal-invalidation policy does not resolve full
  `lifetime.generation_scope_invalidation`; remaining inputs include runtime lifecycle
  evidence, principal scope, invalidation events, reconnect/duplicate stale policy, and
  ABI POD contract. Delegated request-pack audit then added a generated pre-window
  `post_window_replay_contract`: request packs project it into JSON/markdown, the request
  checker validates it, and window-manifest replay compares request/env/preflight/manifest
  sidecars plus the `--post-window-replay` command before tolerating an expiry-only nested
  request check. No runtime/server operation was authorized.
- 2026-06-02 follow-up identity/SDK guardrail audit: `identity.fail_closed` is now covered
  only as contract-review input by the principal-invalidation policy lane; it does not
  resolve the full lifetime blocker or open public ABI/header. SDK completion rejects
  player-identity public-contract readiness reports that still carry lifetime/ABI/cleanup
  blockers or `private_candidate_contract.candidate_only=true` as promoted evidence, and
  permissions/admin certificates replay the same identity validator. Next offline delta is
  a private candidate POD layout evidence lane for `abi.public_pod_contract`, still leaving
  `abi.layout`/SDK consumer coverage missing until a real public ABI promotion path exists.
- 2026-06-02 follow-up private POD layout lane: added
  `player-identity-private-pod-layout-candidate.json` plus checker/tests. The candidate
  pins `PlayerPrincipalEventCandidate` (`sizeof=80`, `align=8`) and
  `PlayerPrincipalDescriptorCandidate` (`sizeof=48`, `align=8`) as private fixed-width POD
  review input only. Gap report summarizes it under `private_pod_layout_candidate` and keeps
  `abi.public_pod_contract`, `abi.layout`, SDK consumer, runtime evidence, and P0 completion
  unresolved. SDK completion rejects the private layout as structured promotion evidence or
  `abi_tests`; route gate remains planning-only at `approved_runtime_evidence_missing`.
- 2026-06-02 follow-up runtime preflight guardrail round: delegated live-ops, ABI/SDK,
  reversing, and P0-accounting audits. Bundle preflight classification now requires
  `window_check.ready=true` before reporting `request_pack_ready`, so valid request/env
  bytes cannot hide invalid preflight sidecars or replay failure. Sub-agents recommended
  the next offline runtime delta as a digest-bound `operator-approval-receipt.json`; ABI
  work should stay candidate-only until approved runtime lifecycle evidence exists. No
  runtime/server operation was performed.
- 2026-06-02 delegated approval-receipt round: lead delegated schema/design, window
  manifest integration, fixture migration, and SDK/accounting impact audits. Preparation
  now emits `operator-approval-receipt.template.json`; window manifests require a
  completed digest-bound `operator-approval-receipt.json`; bundle and approved-evidence
  replay project it as verified provenance only. Receipt verification does not unlock
  runtime evidence, route gates, P0 accounting, or SDK completion. No runtime/server
  operation was performed.
- 2026-06-02 delegated public-ABI preflight round: lead delegated ABI, live-ops, SDK/P0,
  and reversing evidence audits. Added
  `player-identity-public-abi-preflight-candidate.json` plus checker/tests and wired the
  gap report/first-evidence route to consume it as candidate-only routing. It documents
  accepted identifier-redaction, principal-invalidation policy, and private POD layout
  review inputs, while keeping header symbols, capability bits, callback ABI, promotion,
  runtime readiness, SDK readiness, route credit, and v1 completion false. Runtime
  evidence remains the P0 blocker; no runtime/server operation was performed.
- 2026-06-02 no-runtime Transfer/replay hardening: lead delegated Transfer, release-scope,
  SDK/P0, request-pack, and handoff audits. Transfer `bAccept` now has a CTest-only
  hook-side helper and tests, absent from runtime/public/ops surfaces. Follow-up replay
  docs require `--post-window-replay`, completed digest-bound
  `operator-approval-receipt.json`, stable-only final posture, and live-validation sidecar
  paths. Default route/SDK still fail closed at `approved_runtime_evidence_missing`,
  SDK `0/12`, P0 `0/4`, `stable_claim_allowed=false`; no runtime/server operation was
  performed.
- 2026-06-02 delegated Structure non-complete accounting pass: `obelisk.structure_census.v1`
  is now explicitly `excluded` in `docs/public_sdk_surfaces.json`, removed from
  `planning_surfaces`, and named in `post_v1_or_excluded_surfaces` plus the scoped release
  statement with exact no-StructureEvents/no-census/no-identity/no-lookup/no-build-policy/
  no-collision/no-ownership wording. Structure census and build-policy checkers remain
  accepted only as offline/planning evidence with public SDK/runtime/promotion/enforcement
  false. SDK completion with the scoped statement remains blocked at
  `stable_claim_allowed=false`, SDK `0/12`, P0 `0/4`; no runtime/server operation was
  performed.
- 2026-06-02 delegated runtime-evidence replay hardening pass: request-window checking now
  rejects a completed `operator-approval-receipt.json` unless `--post-window-replay` is
  used; window-manifest replay forwards `--post-window-replay --operator-approval-receipt`
  to the nested request checker; approved runtime evidence replay directly revalidates the
  receipt verified flag, false authorization flags, scope flags, and bound sidecar
  artifacts. A real accepted-runtime-evidence route-gate regression now proves the route
  advances only to `identity_public_contract_gate_missing`, keeps route lock
  `blocked_until=[reviewed_identity_public_contract]`, leaves all unlock/readiness flags
  false, and does not count P0. No runtime/server operation was performed.

## Agent Coordination

- Use `obelisk-github-research-workflow` as the canonical coordination rule set. Repo-local
  JSON queue coordination stays out of active prompts, handoff, and checkpoint planning.
- Sub-agent prompts still need scoped objective, safety baseline, allowed paths,
  required skills, expert role, expected decision, and edit permission. Pass only the skills
  needed for that scope, and omit leader-only cadence, active-goal framing,
  community policy, and unrelated module history unless it changes the concrete task.
  Treat sub-agents as scope experts, not generic workers.

## Canonical References

- `docs/agent-handoff/CURRENT.md`: active routing and immediate next steps.
- `docs/STATUS.md`: contributor-facing stability matrix.
- `docs/RELEASE.md`: release and second-source gates.
- `docs/VERSIONING.md`: version and ABI line rules.
- `docs/PLUGIN_ARCHITECTURE.md`: plugin lifecycle and promotion rules.
- `docs/research/README.md`: canonical research-note format.
- `docs/research/2026-05-29-rc-checkpoint-slicing-plan.md`: historical dirty-tree
  recovery reference, not active routing for the current head.
- `docs/research/2026-05-29-public-gameplay-event-readiness-audit.md`: promoted
  `GameplayPolicyEvent` boundary.
- `docs/research/2026-05-29-minimal-second-source-readiness.md`: accepted minimal
  second-source UFunction layout evidence.
- `docs/research/2026-05-28-second-source-core-intake-runbook.md`: shortest offline
  second-source intake.
- `docs/research/2026-05-28-second-source-reversing-gap-matrix.md`: evidence gap matrix.

Archive reference, not active source of truth:

- `docs/agent-handoff/HISTORY-2026-05-28-pre-current-compaction.md`: historical handoff
  detail before the active routing file was compacted; use only to resolve old context.
