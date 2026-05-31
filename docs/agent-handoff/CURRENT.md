# Current Agent Handoff
This file is an active routing table only. Durable evidence belongs in `docs/research/`,
resume facts in `COMPACT_CONTEXT.md`, and old detail in `HISTORY-*.md`. Historical
recovery context is not active routing; use `git log --oneline -1` for the checkpoint.

## Active Objective

- `v0.1.0-rc.2` is the current published core-first RC baseline: Linux runtime, ProcessEvent
  hook, plugin lifecycle, central install layout, `oBaseEvents`, `GameplayPolicyEvent`,
  minimal copied `ChatMessageEvent`, descriptors, timers, and refreshed RC evidence.
- Publication used a clean release gate and exact tag/ref verification. Do not reinterpret,
  retag, or expand the published RC for routine post-RC work; treat stale local tags as
  invalid until revalidated.
- Post-RC work moves toward `v1.0`: UE4 reflection, copied-data module APIs,
  lifecycle-safe plugins, operator tooling, and Linux-native equivalents for familiar ARK
  plugin concepts.
- Treat chat, inventory, structures, players, tribes, dinos, buffs, missions, transfers,
  commands, permissions, timers, config/logging, economy/database, and admin tooling as
  module areas above the core. Promote each only through copied-data ABI, privacy,
  lifecycle, and second-source/static evidence gates.

## Hard Overrides

- GitHub publication is lead-only. GitHub work may be delegated only for an evidenced, stable milestone; this handoff does not authorize push, tag, release-ref updates, rebase, or routine publication.
- No tag or release-ref push is authorized without explicit release-manager/lead
  authorization for the current-turn. Stale local tags are recreated only after rerunning
  the release gate on the intended ref and are not reused or pushed.
- No server target has standing approval. Server-backed debug/beta work requires a current
  approved live-ops brief naming target instance/map, feature gates, marker/env changes,
  start/restart/stop window, notice path when players are involved, evidence capture, and
  rollback. Do not restart/start/stop servers, edit `/servidor/ark`, change markers, run
  ReflectionScanner, attach ptrace/gcore, enable broad ProcessEvent tracing, or publish
  runtime observations outside an exact approved run. Technical progress is only a reason
  to request a scoped run, not approval by itself.
- Runtime posture is default-deny for filtered/global raw `ProcessEvent`, public
  `CallProcessEvent`, ProcessEvent blocking, broad tracing, ReflectionScanner, debug
  controls, and observers unless the matching approved env+marker pair is enabled for a
  scoped debug window.
- Discord sends require explicit current-turn approval for approved public milestones or
  beta-test windows. Use no Discord for internal rounds or agent status, routine validation,
  or speculative notes. Always dry-run before any approved send and send one public-safe
  embed. Webhook URLs stay only in ignored `local/discord-webhooks.env`; repo text may
  name only `OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL` and `OBELISK_BETA_TEST_WEBHOOK_URL`.
  Publication approval does not imply Discord approval.

## Current Routing Facts

- RC public scope remains limited to `GameplayPolicyEvent`, minimal copied
  `ChatMessageEvent`, `DescribeResourceKind`, and `DescribeGameplayPolicyEventKind`.
  `v0.1.0-rc.2` additionally includes process-local owner-token timers as core runtime
  API without promoting gameplay/module timers. It is not a production-stable `v1.0`
  claim.
- `ObeliskApi` v1 remains append-only. New public surfaces require copied-data ownership,
  capability/`struct_size` gates, lifecycle cleanup, privacy rules, and accepted
  second-source/static evidence.
- SDK packaging publishes only `include/obelisk/ObeliskApi.h`; more public headers require
  explicit install layout/test updates and ABI review.
- Installed `Obelisk_*` CMake variables are derived from public C header `OBELISK_*` ABI
  macros at configure time; installed SDK consumers verify package/header parity.
- Core dump evidence-pack manifests must declare `obelisk.core-dump-evidence-pack.v1`;
  snapshot/regeneration consumers and offline artifact gates require binary/core SHA,
  safe `core.path`, complete status, and `gdb_core_failed=false`.
- Promoted copied events are observational and non-authoritative: no UE pointers, raw
  params, identity, lookup, mutation, return override, pincode/player text publication, or
  broad module SDK claim.
- Plugin unload/init-failure cleanup skips `dlclose` when callback cleanup cannot be proven complete, retains the plugin for retry, does not repeat plugin shutdown, runs copied-event `DestroyUserData` inside the relevant gameplay callback scope to avoid reentrant cleanup deadlocks, and release readiness rejects production `libobelisk.so` builds exposing manager/dispatcher test-only symbols.
- `oProcessTimer` is the first process-local timer example. Timer ids are process-local,
  not cluster state, UE identity, gameplay/module timer abstractions, or persistent
  handles, or shared scheduler state; owner-token timers require explicit unregister.
  Timer allocation skips zero/live ids after wrap. Safe-disabled config prep works without
  optional timer capability; active config fails closed on missing timer capability, owner
  token, or appended timer slots.
- `oPolicyAudit` now unregisters its `GameplayPolicyEvent` owner-token handle if init
  fails after callback registration. The SDK fixture covers injected post-registration log
  failure cleanup.
- `oDescriptorCatalog` is the metadata-only descriptor example. It registers no callbacks,
  timers, chat handlers, identity, lookup, mutation, return override, or ABI expansion.
- `oBaseEvents` has a disabled-by-default plugin-local chat command helper over copied
  `ChatMessageEvent` bytes; no command ABI/router, identity, replies, moderation, send-chat
  API, mutation, or extra exported plugin symbols.
- `oChatLogger` and `oChatAudit` are experimental and excluded from default release scope;
  safe-disabled init needs only the base ABI prefix/owner token, while active config fails
  closed on missing capabilities, short `struct_size`, null registration slots, or null
  callback user data.
- ArkServerApi/AseApi and local `NextGenPlugins` clones are names and demand dictionaries
  only, not a behavior map, not a porting target, not a copying source, and not
  implementation guides. Do not copy code, offsets, layouts, vtables, ABI assumptions, wrappers, raw UE
  pointer APIs, `.lib` artifacts, constants, schemas, control flow, command parsers,
  return constants, return semantics, or implementations.

## Evidence Routing

- Minimal second-source intake supports only the copied `GameplayPolicyEvent`
  structure/inventory lane. Consume gates accept; promotion remains blocked for identity,
  lookup, mutation, return override, Inventory SDK, StructureEvents, GObjects, and
  `ResourceHandle`.
- The accepted RC UFunction second-source root remains the publication baseline.
- `v0.1.0-rc.2` was published from `1a7cd98` after refreshing the RC UFunction
  second-source root for the intended ref and passing the release gate with all public RC
  targets accepted. Future RC/stable candidates must regenerate evidence for their exact
  intended ref.
- Item return-only policy has three append-only public `GameplayPolicyEvent` kinds:
  `AllowEquipItem`, `CanRepair`, and `UseItemOntoItem`, copied `ReturnValue` only and
  `inventory_item` category only. Runtime validation, public Inventory SDK, Items SDK,
  identity, mutation, and return override remain blocked without a live-ops brief and
  separate promotion gates.
- Mission copied-bool, Transfer `bAccept`, Structure return-only, Structure non-PIN
  copied-scalar, and Buff breadth packages remain evidence-only/internal. Mission's exact
  internal bridge lane is the focused `mission-copied-bool-policy-slice` consumed as
  offline evidence, then `MissionReflection`-only recognition for a future default-off
  post-original log observer; it is not runtime/API promotion. Mission bool-tail preserves
  `bool_field_size=1`, `bool_byte_offset=0`, `byte_mask=0x01`, `field_mask=0xff`, and
  `native_bool=false`. The only copied bools are
  `AddPlayerToMission.bForceAdd`, `AddPlayerToMission.ReturnValue`,
  `BPAllowPlayerToLeaveMission.ReturnValue`,
  `BPOnPlayerRemovedFromMission.bFromMissionCompleteEvent`, and
  `BPOnPlayerRemovedFromMission.bLastPhaseSuccess`. The redacted-only fields are
  `AddPlayerToMission.PlayerCharacter`, `BPAllowPlayerToLeaveMission.PlayerPawn`,
  `BPOnPlayerRemovedFromMission.Player`, `BPOnPlayerRemovedFromMission.Controller`,
  `GetPlayerUsableItems.Character`, and `GetPlayerUsableItems.OutItemIDs`;
  `GetPlayerUsableItems` stays recognition-only and outside copied-bool policy output.
  Consume mode accepts documented slices and promote mode blocks release/public/runtime
  promotion through local consume-only/planning-only denylists even if shared metadata
  drifts. Next Mission validation is local lifecycle/gate proof: disabled/missing
  profile/window/marker/SHA, unsupported SHA, zero budget, and non-target FName must do no
  metadata/parameter reads and reserve no budget; rejection must clear copied output and
  non-canonical bool bytes greater than `1` must fail closed. `transfer-baccept-only-policy-slice`
  is blocked from release/public SDK gates. This does not authorize Transfer runtime work,
  public Mission SDK, runtime Mission dispatchers/callbacks, ResourceHandle, identity,
  arrays, mutation, return override, or server observation.
- ResourceHandle/public GObjects remain blocked; old flag-policy artifact is obsolete and
  durable rich-provenance refresh is preserved. Consume mode accepts it and promote mode
  stays blocked. Do not rerun broad FName, GObjects, or core scans for ResourceHandle
  unless the binary hash changes or evidence is contradicted. The semantic blockers remain:
  the post-callback rejection contract is preserved as candidate-only and fail-closed.
  The first strict serial reuse/wraparound policy artifact is preserved at
  `/home/flowcommunity-ark/obelisk-artifacts/resourcehandle-serial-policy-20260530T190642Z/serial-policy.json`;
  manifest consume mode accepts it and promote mode blocks it as candidate-only. This
  narrows the serial-policy design gap but does not unlock runtime negative samples,
  public lookup, object identity, mutation, return override, persistent handles, or
  public `ResourceHandle`. The next strict ResourceHandle blocker is rejected runtime
  object samples plus runtime serial reuse/wraparound semantics. Future runtime artifacts
  must use the candidate-only
  `obelisk.internal-uobject-revalidation-runtime-rejection-samples.v1` and
  `obelisk.internal-uobject-revalidation-runtime-serial-semantics.v1` schemas, remain
  consume-only/promote-blocked, redact run identity and privacy-sensitive values, and
  still reject post-callback lookup. These schemas are not public SDK/runtime-readiness
  contracts, and offline or copied-core scans cannot satisfy them. The minimal planning
  note now lives in
  `docs/research/2026-05-30-post-rc-offline-resourcehandle-priority.md#future-runtime-observation-plan`;
  execution is still blocked until an operator-approved live-ops brief names the exact
  debug target, gates, window, rollback, artifacts, and posture checks. Do not replace
  this with another broad offline FName/GObjects scan.
- Transfer ScriptStruct/bAccept evidence has refreshed internal-layout roots; old 20260529
  transfer roots are stale. Transfer scalar/bool fields are redacted metadata only; gates
  detect Transfer structs without labels and require transfer blockers on every field.
- `validate_offline_artifact_gate.py` consumes `obelisk.artifact-pack.manifest.v1`
  containers with current-content checksums, symlink fail-closed checks, child-manifest
  blockers, container-only promote blocking, protected-root checks, and duplicate target
  guidance rejection.
- UFunction target-set listing and release-gate option parsing are classified as
  `release_readiness`, `planning_only`, or `internal_layout_only`; listings expose module lanes, promotion accepts only explicit release-readiness sets, rejects explicit `--target` widening outside named target sets, reports target-set guidance/non-claims in readiness JSON, blocks duplicate/unknown/overlapping readiness coverage, and marks internal/layout-only gaps as `target_set_not_release_readiness`.
- Release gate UFunction preflight compares all requested target sets together so
  cross-set overlaps fail before build/test with `ambiguous_target_set_coverage`.
- Offline artifact JSON manifests, provenance sidecars, artifact checksum reads, and core inspector inputs use no-symlink regular-file opens after protected-path prechecks; relative
  manifest/provenance/resource-handle core paths resolve against their sidecar, and `--snapshot-json` verifies observed offline core SHA256 plus safe capture/evidence-pack IDs before emitting evidence.
- `scripts/check_static_tooling.py` records optional radare2/rizin/Ghidra availability and
  runs smoke checks only on approved offline binaries/output roots.
- `APrimalStructure.IsAllowedToBuild` is second-wave only: no committed snapshot,
  second-source comparison, target-set promotion, public StructureEvents/build-policy SDK,
  mutation, or return override. Guidance requires one exact sanitized candidate snapshot
  before any target set; `inspect_core_ufunctions.py --core` rejects evidence-pack
  manifests.
- `players-identity-lifecycle-intake` is a guidance-only target set backed by
  `docs/research/2026-05-30-player-identity-lifecycle-plan.md`; it stays out of RC/public
  target sets, is release-gate rejected, and does not promote identity, lookup, runtime
  work, mutation, or return override.

## Priority Next Steps

- Current post-RC focus: preserve RC scope, reduce debt, improve evidence tooling, and promote only copied module APIs through strict gates.
- Mission test-only copied-bool dispatcher exists outside shared runtime/API targets for
  three copied-bool functions; next review is lifecycle/runtime observation, not public API.
- For v0.2 product value, prefer Structure aggregate/census planning over Transfer
  `bAccept`. Transfer `bAccept` remains useful as a fixture/internal bool-layout lane, but
  it is low product value without identity/payload/cross-map/privacy semantics. Do not
  build Transfer runtime/API work unless a later focused gate makes it necessary.
- `structure-aggregate-census-planning` is planning-only, not release readiness, public
  SDK evidence, or a public StructureEvents surface; use it only to bound copied/redacted
  Structure aggregate/census design while evidence, ABI, privacy, and lifecycle policy are
  missing. Design note: `docs/research/2026-05-31-structure-aggregate-census-v0.md`.
  The 2026-05-31 refinement keeps the lane internal/default-off, limits v0 inputs to
  copied scalar event views, excludes `VerifyPinCode.ReturnValue` from aggregate output,
  and records consume-accepted/promote-blocked policy-slice gates. After this lane,
  Mission copied-bool is the next fastest internal copied-data bridge; Dino compact
  remains behind it until scalar-only copied-event policy and lifecycle/redaction review
  exist.
- Item return-only bridge hardening now keeps copied dispatch construction in
  `ProcessEventItemReflection` helpers, with unit coverage for the three supported event
  kinds, `CraftBlueprint` rejection before runtime item-return reflection, exact
  `ReturnValue` scalar scope, attempt-budgeted runtime reads, and no
  identity/mutation/return-override leakage. Dispatcher hot-path allocation has a local
  benchmark gate for no-subscriber and <=4-subscriber snapshots; do not expand it unless
  profiling justifies a larger callback snapshot strategy.
- Structure second-wave remains offline-only. Use
  `scripts/build_reflection_inventory_pack.py --plan-target Outer.Name` to produce a
  candidate-only focal plan from a complete non-protected evidence-pack manifest; the
  planner now uses unfiltered redacted inventory for exact matches, blocks unsafe/incomplete
  FName-root inputs before command emission, requires explicit artifact identity for
  direct-core planning, and remains planning-only. Then generate one sanitized snapshot and
  a distinct second-source compare. Fixture/rootless
  reports remain negative guardrails; do not add these keys to release target sets, ABI
  enums, descriptors, dispatchers, public docs, or runtime gates.
- For general reflected decoding, reuse current FName root `0x5956f30` and GObjects candidate `0x595b7e0` through closed target-set snapshots and second-source comparison; do not repeat broad FName/GObjects/core scans for this binary.
- Plugin Hub planning starts from `docs/PLUGIN_HUB_FOUNDATION_V1.md` and
  `docs/PLUGIN_HUB_CAPABILITY_MATRIX.md`: production seeds are lifecycle/config/logging,
  descriptor/catalog, and process-local timers; copied chat/policy stays experimental.
- Artifact-pack contributor onboarding now has `docs/OFFLINE_ARTIFACT_PACKS.md` as the
  concise runbook. UFunction regeneration and RC root assembly require complete
  `offline_core` artifact identity, sanitized capture/pack IDs, and current bool-tail
  metadata; `--snapshot-json` is exact/direct single-target candidate-only output. The
  release gate preflights the four public RC target sets before build work.
- Runtime/plugin lifecycle audit found no P1 blocker; `EventManager` granular unregister,
  snapshot validation, null-callback rejection, gated raw blocking, no-throw API rejection,
  and `CallProcessEvent` catch boundaries are covered.
- Any future live/player validation requires a new approved live-ops brief. Beta-test
  notice through the configured local webhook variable still requires explicit
  current-turn operator approval and dry-run when players are involved.

## Agent Protocol

- Lead owns server-safety decisions, GitHub, Discord, and stale-agent cleanup.
- Before each sub-agent round: close stale agents, assign expert role, declare allowed
  paths, pass only the skills required for the task, and record any still-active agent
  with a polling or integration plan.
- Sub-agents receive scoped expert tasks, safety baseline, allowed paths, forbidden paths,
  required skills, validation expectations, and one concrete expected decision. Do not pass
  leader cadence, unrelated module history, or broad policy unless it changes the task.
