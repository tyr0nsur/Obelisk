# Compact Context Snapshot

Updated: 2026-05-31

Use this file after conversation compaction or when resuming Obelisk from repository
state. Current routing table only: read `docs/agent-handoff/CURRENT.md` for active
priorities, and do not use history files as the active source of truth.

## Resume Protocol

1. Read this file, `docs/agent-handoff/CURRENT.md`, and the relevant subsystem skill.
2. In lead/integration turns where current instructions do not prohibit Git, check
   `git status --short --ignored`.
3. Close completed or obsolete internal agents before starting a new round.
4. Continue direct supervised work with scoped sub-agent prompts when delegation is used.

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
  after a concrete offline/code advance genuinely needs new runtime logs.
- Community updates are for major public modder-facing milestones only; beta-test
  activation notices are separate operational live-ops messages. Discord URLs are ignored
  local secrets in `local/discord-webhooks.env`; use only
  `OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL` or `OBELISK_BETA_TEST_WEBHOOK_URL` by variable
  name, and send concise professional embeds without raw logs, player text, secrets, or
  speculative reversing notes. Use `community` only for stable modder-facing milestones,
  `beta-test` only for approved player action windows, and no Discord for internal rounds
  or agent status. Explicit current-turn approval is required for every Discord send;
  publication approval does not imply Discord approval. Always dry-run the embed first and
  verify a public-safe title, description, status/scope, and 2-5 useful fields.
- `ArkServerApi/AseApi` may be used only as a names and demand dictionary for familiar
  ArkApi-style plugin concepts. Do not import offsets, vtables, layouts, `.lib`
  artifacts, MSVC/Windows ABI assumptions, direct `GetNativePointerField`/`NativeCall`
  wrappers, raw UE pointer APIs, constants, schemas, control flow, command parsers,
  return semantics, or source-derived implementations; all access must be rebuilt through
  Obelisk reflection/ProcessEvent copied-data evidence.
- Local `NextGenPlugins` clones are names and demand dictionaries only, not porting or
  copying sources. Keep clones out of the repo and do not copy code, constants, schemas,
  control flow, command parsers, return constants, or implementations.

## Stable Baseline

- Repo: `/home/flowcommunity-ark/Obelisk`
- Remote: `git@github.com:tyr0nsur/Obelisk.git`
- Central Obelisk root: `/servidor/ark/obelisk`
- Current release baseline: `v0.1.0-rc.2` is published as the frozen core-first RC
  baseline after a clean release gate and exact tag/ref verification. It is not a
  production-stable `v1.0` claim. Post-RC work should move toward a broader `v1.0`
  complete SDK through architecture hardening, UE4 reflection evidence, copied-data
  module APIs, and later compatibility for familiar ARK plugin concepts on top of
  Obelisk primitives.
- `v1.0` stable means the complete public SDK contract for plugin authors, not merely a
  stable internal runtime. The current v1 surface inventory lives in
  `docs/public_sdk_surfaces.json`, with human guidance in `docs/SDK_V1_COMPATIBILITY.md`;
  both are planning-contract artifacts until a future release gate packages or supersedes
  them.
- The v1 completion checker must reject promoted permissions/admin or commands/replies
  rows whose dependencies are not promoted, and promoted player identity must name the
  reviewed core/reflection evidence terms before supporting public permissions or command
  claims.
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
- Plugin Hub v1 seed work starts from `docs/PLUGIN_HUB_FOUNDATION_V1.md` and
  `docs/PLUGIN_HUB_CAPABILITY_MATRIX.md`. Release-supported seeds are small
  Obelisk-native lifecycle/config/logging examples, descriptor reads, and process-local
  timers. Passive copied chat parsing and copied policy auditing are experimental pattern
  examples only; demand-map or `NextGenPlugins` dictionary entries do not make a seed
  release-ready and do not promote permissions, RCON, economy, homes/safe zones,
  structure enforcement, dinos, tribes, transfers, inventory, item mutation, identity,
  lookup, replies, send-chat, moderation, or ArkApi portability.
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
  descriptor structs.
- `InventoryPolicyEventDispatcher` and `StructureEventDispatcher` are internal
  copied-scalar infrastructure only. They do not promote public Inventory or
  StructureEvents SDKs.
- Inventory copied-policy dispatch uses build-once payload reuse after budget reservation
  and a cheap atomic live-subscriber mirror; lifecycle cleanup must still use dispatcher
  depth/deferred-destroy state, not the subscriber mirror. Copied inventory payloads
  rebind scalar spans on copy/move so dispatch-time values own their storage, and failed
  budget reservation clears stale payloads.
- Structure copied-policy dispatch now follows the same safety pattern: dispatch budget
  requires live subscribers, matched attempts reserve with one self-contained copied event,
  copied scalar spans rebind on copy/move, exposed scalar range sizes are validated, and
  reader exceptions fail closed. Structure dispatcher output also rejects scalar
  fields/types outside the exact public descriptor contract for each event kind, and
  structure dispatch budget no longer keeps the hook hot path active when there are no
  subscribers. This remains internal infrastructure, not a public StructureEvents SDK or
  structure identity surface.
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
  core-first release gate but does not promote GObjects, ResourceHandle, identity,
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
  blockers.
- Structure non-PIN copied-scalar evidence is preserved at
  `/home/flowcommunity-ark/obelisk-artifacts/structure-nonpin-copied-scalar-policy-slice-20260530T100717Z/`.
  It excludes `VerifyPinCode`, copies only `SetVariant.{VariantIndex,bForceSet,ReturnValue}`,
  `AllowToggleActivation.ReturnValue`, and `CanSeat.{bForce,ReturnValue}`, accepts consume
  mode, and blocks promote mode with
  `promote_mode_structure_nonpin_copied_scalar_policy_slice_evidence_only` plus non-claim
  blockers. `artifact-pack.manifest.json` SHA256 is
  `90a7e51f6cb491bd56ef4f7c0445b0e61265982dadc7f7316139a0ffd43189a3`; `SHA256SUMS` SHA256
  is `9334831106ce31818a64ed762baf95aadc01eeec4470c77ea5d7f47759e67209`. This does not
  promote public `StructureEvents`, SDK callbacks, identity, lookup, mutation, return
  override, dispatcher/hook wiring, `ResourceHandle`, runtime observation, or probing.
- `PrimalStructure.IsAllowedToBuild` / `APrimalStructure.IsAllowedToBuild` is a
  second-wave build-policy dictionary seed only. There is no committed candidate pack,
  second-source comparison, target-set promotion, public StructureEvents/build-policy SDK,
  mutation, or return override. Fixture-only `missing_base_snapshot` readiness is a
  negative guardrail, not progress or promotion evidence. First useful work is an approved
  offline focused snapshot with an explicit base root or complete core evidence-pack
  manifest, followed by a distinct second-source compare; do not add either key to release
  targets, ABI enums, descriptors, dispatchers, public docs, or runtime gates.
- Focal UFunction snapshot planning helpers live in
  `scripts/ufunction_focal_snapshot_plan.py`; `build_reflection_inventory_pack.py` uses
  them for candidate-only exact snapshot command plans. Target-set bridge coverage proves
  named planning sets can emit exact `--snapshot-json` commands from unfiltered redacted
  inventory without adding release target-set regeneration claims.
  `scripts/plan_ufunction_focal_snapshots.py` consumes an already reviewed
  reflection-inventory pack plus exact targets/target files and emits candidate-only
  planned commands without rereading a core, executing commands, writing snapshots, or
  promoting target sets/runtime/API scope. For player identity, first review a complete
  reflection inventory pack with full 12-target `players-identity-lifecycle-intake`
  coverage, then plan only the exact `ShooterPlayerController.ServerListPlayers` and
  `ShooterPlayerController.ServerKickPlayer` targets; do not use the full target set to
  emit focal plans.
- Player identity has a candidate-only privacy/invalidation contract in
  `docs/research/2026-05-31-player-identity-privacy-invalidation-contract.md`: future
  principals must be opaque copied POD values, generation-checked, process-local by
  default, and invalidated fail-closed. This does not promote public identity, lookup,
  persistence, platform ids, player names, `ResourceHandle`, UE pointers, or runtime
  access.
- `ue/MissionReflection.*` is an internal fixture-backed recognizer for
  `mission-compact-intake`: copied bool ranges only, object refs and `OutItemIDs` arrays
  recognition-only, with only a test-only internal dispatcher/helper and no hook/runtime
  dispatcher/public Mission SDK. Tests reject copied
  bool ranges that exceed `ParameterSize` and clear poisoned output on failure.
  The internal readiness note is
  `docs/research/2026-05-29-mission-reflection-internal-readiness.md`. A local
  test-only `ProcessEventMissionReflection` helper scaffold exists, but it has no live
  hook path, dispatcher, public ABI, server marker/env, or runtime logs. Any next Mission
  slice needs a separate runtime-observation/lifecycle review.
  The canonical offline Mission refresh input is
  `/servidor/ark/workspace-offline/mission-compact-intake-bool-semantics-refresh-20260530T020021Z/pack/redacted-signatures.json`
  with SHA256 `09074e71666f755801802e5d796361cf4f84d3e7d8c00663801d84f981a1cc13`.
  The durable focused Mission policy slice is preserved at
  `/home/flowcommunity-ark/obelisk-artifacts/mission-copied-bool-tail-policy-slice-20260530T090211Z/`
  with exact bool-tail evidence (`bool_field_size=1`, `bool_byte_offset=0`,
  `byte_mask=0x01`, `field_mask=0xff`, `native_bool=false`), `artifact-pack.manifest.json`
  SHA256 `b47f0497c92ae3e8f9a006fb5be87cfbcc1d1dd5f15d78267ad186073e4c26fb`
  and `SHA256SUMS` SHA256
  `9dc277b8e3dddeed66d140a12654e4d5f7e7dc13b8b9aca75d96446c53069545`;
  consume mode accepts it and promote mode remains blocked.
- `ue/TransferReflection.*` is an internal/test-only recognizer for the
  `ServerTransferredPlayerConfirmationResult.bAccept` copied bool. It validates exact
  SHA-scoped function/property shape and bool mask metadata, but has no hook/runtime
  dispatcher/public Transfer SDK. The durable focused Transfer policy slice is preserved at
  `/home/flowcommunity-ark/obelisk-artifacts/transfer-baccept-only-policy-slice-20260530T073308Z/`
  with `artifact-pack.manifest.json`
  SHA256 `dc35acbf63c9f22ffa5281952f2b651e034288f56ab9dec093cbfcfd368d841d`
  and `SHA256SUMS` SHA256
  `715f7c2b048370a74dbacfadd13d06496cf7e56867bb571351c2653d4fd297f8`;
  consume mode accepts it and promote mode remains blocked.
- ResourceHandle remains post-RC/internal. The old flag-policy artifact is obsolete; the
  durable rich-provenance refresh and strict serial policy are consume-accepted but
  promote-blocked candidate evidence only. Do not rerun broad FName, GObjects, or core
  scans for ResourceHandle unless the binary hash changes or evidence is contradicted.
  The next strict blocker is rejected runtime object samples plus runtime serial
  reuse/wraparound semantics under an operator-approved live-ops brief. A primary Ragnarok
  copied-core scan produced 44 coherent `0x4000` rejected-object candidate samples and is
  preserved under
  `/home/flowcommunity-ark/obelisk-artifacts/resource-handle-serial-scan-primary-20260530T000000Z/`;
  consume mode is accepted and promote mode remains blocked. A focused `GObjects`
  reconciliation resolved all 44 as `ParticleSystemComponent0` under `Text_Actor` /
  `Text_Actor_C` and is preserved under
  `/home/flowcommunity-ark/obelisk-artifacts/resource-handle-flag4000-reconciliation-primary-20260530T000000Z/`.
  This is internal lifecycle/blocker evidence only, not public `ResourceHandle`, lookup,
  identity, mutation, return override, or lifetime promotion.
  Current offline flag-policy tooling requires the internal label
  `InternalUObjectRevalidationCandidate` with frame-local lifetime only, post-callback
  lookup rejected, `0x100` rejected, `0x4000` rejected by default, and output limited to
  copied bool/reason or Obelisk-owned copied data. The consume gate also validates the
  exact `weak_helper_caller_mode` shape/flag rules, rejects candidate fields outside the
  known contract, and blocks extra blocker/non-claim text that overclaims public
  `ResourceHandle`, lookup, SDK, runtime, or callback readiness.
- Static GObjects/FUObjectItem evidence is internal offline input only. `0x595b7e0`
  supports target-set enumeration across current copied-core evidence, but not public
  GObjects, identity, lookup, `ResourceHandle`, mutation, or return override. Evidence:
  `docs/research/2026-05-29-gobjects-fuobjectarray-durable-pack.md`,
  `docs/research/2026-05-29-gobjects-second-core-reconciliation.md`, and
  `docs/research/2026-05-29-gobjects-cross-manifest-comparison.md`.
- Redacted UFunction signatures, offline manifests, item compact intake, inventory-action
  compact intake, and BoolProperty mask/native markers are candidate/layout hygiene only.
  They are useful for planning and fixture comparison, not runtime safety, public SDKs,
  identity, mutation, return override, or `ResourceHandle`. Use the dated research notes
  such as `docs/research/2026-05-29-item-compact-second-source-readiness.md`,
  `docs/research/2026-05-29-item-return-only-policy-bridge-plan.md`,
  `docs/research/2026-05-30-item-return-only-policy-slice.md`,
  `docs/research/2026-05-29-inventory-action-redacted-signature-readiness.md`, and
  `/servidor/ark/workspace-offline/redacted-ufunction-signatures-rollup-20260529T101249Z`
  instead of copying artifact detail into handoff.
  The durable Item return-only policy slice is preserved at
  `/home/flowcommunity-ark/obelisk-artifacts/item-return-only-policy-slice-20260530T072255Z/`;
  consume mode is accepted and promote mode is blocked with evidence-only/non-claim
  blockers. It copies only `AllowEquipItem.ReturnValue`, `CanRepair.ReturnValue`, and
  `UseItemOntoItem.ReturnValue`. Its internal helper can build-and-reserve the copied
  return observation in one operation and clears output on invalid attempts or exhausted
  budget; it remains internal/test-only. The pack now includes relative `SHA256SUMS`
  (`sha256=ccd33e42337fd5b1ae3c51333c73ec17aeadef29d3c203b6680bb3be49c7a046`) and
  `artifact-pack.manifest.json`
  (`sha256=89e9b4af96472314055614824a2b2fce4a0b4343832ae38a2495d77411a5671a`).
  The public shape is now limited to three post-original copied bool observations through
  `GameplayPolicyEvent`, not an Inventory SDK or return override; artifact promote mode
  remains blocked.
  A target-specific second-source pack is preserved at
  `/home/flowcommunity-ark/obelisk-artifacts/item-return-only-second-source-20260530T084918Z/`;
  it accepts 3/3 copied return-bool targets at `layout_only` scope while promote mode
  remains blocked.
  If explicitly tasked with chat command ergonomics, start as a plugin-local parser/helper
  over the existing copied `ChatMessageEvent`, not as a new ABI. Keep output
  callback-scope only and keep player identity, permissions, targeting, chat send/reply,
  moderation/blocking, mutation, and return override blocked.
  The strict RC `minimal-second-source-intake` redacted signature pack with complete
  target-set coverage is preserved at
  `/home/flowcommunity-ark/obelisk-artifacts/rc-minimal-redacted-signatures-strict-20260530T000000Z/`;
  consume mode is accepted and promote mode remains candidate-only blocked.
- The historical static-negative UObject flag policy pack is obsolete and blocked by old
  vocabulary/provenance. The durable rich-provenance refresh is preserved at
  `/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-refresh-20260530T071436Z/`;
  consume mode is accepted and promote mode is blocked with candidate-only/non-claim
  blockers. The pack now includes `artifact-pack.manifest.json`
  (`sha256=1f678c05461131055e4b18fd68862de431a27bbf49609297030ac62bf6f5478d`)
  and `SHA256SUMS`
  (`sha256=cf76ee33a8ea640233af7eff4de78171254a5ee5fa11de714259b27f2731a87a`).
  This is internal static evidence only and does not promote public GObjects, lookup,
  identity, lifecycle, `ResourceHandle`, mutation, return override, or SDK surfaces.
- Post-RC offline tooling added candidate-only UObject flag, weak-helper, and GObjects
  evidence builders. They are consume-mode internal/offline indexing tools only and do not
  promote public GObjects, lookup, identity, lifecycle, `ResourceHandle`, mutation, return
  override, or SDK surfaces.
- `scripts/build_uobject_flag_sample_report.py` produces
  `obelisk.uobject-flag-sample-report.v1` from the transition-matrix plus regenerated
  policy artifacts. Each `--input` must be paired with a `--consume-gate` in the same
  order, and the output embeds redacted consume-gate summaries for the source artifacts,
  not raw gate JSON. The offline artifact gate accepts it only in consume mode and blocks
  promote mode; use the script tests and gate output as the authoritative reference.
- Weak-helper caller-mode artifacts are consume-mode research hygiene and promote-mode
  blocked. They refine helper evidence while keeping `ResourceHandle`, UE lifecycle names,
  post-callback lookup, mutation, and return override blocked; summarize durable policy in
  `docs/research/2026-05-29-resource-handle-flag-policy-candidate.md` and
  `docs/research/2026-05-29-uobject-flags-validity-blocker.md`.
- `weak-helper-static-polarity-report.v1` has a candidate-only builder/gate contract for
  provenance-gated consume-mode indexing. It narrows internal flag-policy research only;
  promote mode remains blocked and it does not clear `ResourceHandle`, lifecycle-name,
  lookup, mutation, or return-override blockers.
- If the reviewed binary/artifact FName root slot is already known, do not run broad
  reverse FName scans. Pass the root slot explicitly to evidence-pack, GObjects sampling,
  or snapshot regeneration tooling.

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

- Published RC baseline is core-first: `ObeliskApi` v1 is frozen around Linux runtime,
  ProcessEvent hook infrastructure, plugin lifecycle, central install layout,
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
- Current ResourceHandle flag-policy pointer:
  `docs/research/2026-05-30-post-rc-offline-resourcehandle-priority.md`. It records
  consume-accepted/promote-blocked internal evidence; public `ResourceHandle`, lookup,
  lifecycle names, mutation, and return override remain blocked.
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
- If internal recognizer work resumes, keep it test-only. Transfer `bAccept` remains a
  useful bool-layout fixture but is lower product value than Structure aggregate/census
  planning and Player identity research because it lacks identity, payload correlation,
  cross-map semantics, enforcement, and privacy policy. This is not RC public SDK/API
  scope and does not change the RC public API.
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

## Agent Coordination

- Use `obelisk-github-research-workflow` as the canonical coordination rule set. Repo-local
  JSON queue coordination stays out of active prompts, handoff, and checkpoint planning.
- Sub-agent prompts still need scoped objective, safety baseline, allowed paths,
  required skills, expert role, and expected decision; pass only the skills needed for
  that scope and close completed sub-agents before the next round.

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
