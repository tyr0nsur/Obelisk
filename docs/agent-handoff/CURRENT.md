# Current Agent Handoff

Updated: 2026-05-30

This file is an active routing table only. Durable evidence belongs in `docs/research/`,
resume facts in `COMPACT_CONTEXT.md`, and old detail in `HISTORY-*.md`. Historical
recovery context is not active routing for the current head; use `git log --oneline -1`
for the current checkpoint.

## Active Objective

- `v0.1.0-rc.2` is the current published core-first RC baseline: Linux runtime, ProcessEvent hook
  infrastructure, plugin lifecycle, central install layout, `oBaseEvents`,
  `GameplayPolicyEvent`, minimal copied `ChatMessageEvent`, descriptor helpers,
  process-local owner-token timers, and refreshed RC UFunction second-source evidence.
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

- GitHub publication is lead-only and only for an evidenced, stable milestone. This
  handoff does not authorize push, tag, release-ref updates, rebase, or routine
  publication.
- GitHub work may be delegated only for an evidenced, stable milestone.
- No tag or release-ref push is authorized without explicit release-manager/lead
  authorization for the current-turn. Stale local tags are recreated only after rerunning
  the release gate on the intended ref and are not reused or pushed.
- Server-backed debug/beta work requires a current approved live-ops brief naming target
  instance/map, feature gates, marker/env changes, start/restart/stop window, notice path
  when players are involved, evidence capture, and rollback.
- No server target has standing approval. Do not restart/start/stop servers, edit
  `/servidor/ark`, change markers, run ReflectionScanner, attach ptrace/gcore, enable broad
  ProcessEvent tracing, or publish runtime observations outside an exact approved run.
  Technical progress is only a reason to request a scoped run, not approval by itself.
- Runtime posture is default-deny for filtered/global raw `ProcessEvent`, public
  `CallProcessEvent`, ProcessEvent blocking, broad tracing, ReflectionScanner, debug
  controls, and observers unless the matching approved env+marker pair is enabled for a
  scoped debug window.
- Discord sends require explicit current-turn approval for approved public milestones or
  approved beta-test windows. Use no Discord for internal rounds or agent status, routine validation,
  or speculative notes. Prefer `scripts/send_discord_embed.py --dry-run` and
  one public-safe embed. Webhook URLs stay only in ignored `local/discord-webhooks.env`;
  repo text may name only `OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL` and
  `OBELISK_BETA_TEST_WEBHOOK_URL`.

## Current Routing Facts

- RC public scope remains limited to `GameplayPolicyEvent`, minimal copied
  `ChatMessageEvent`, `DescribeResourceKind`, and `DescribeGameplayPolicyEventKind`.
  `v0.1.0-rc.2` additionally includes process-local owner-token timers as core runtime
  API without promoting gameplay/module timers. It is not a production-stable `v1.0`
  claim.
- `ObeliskApi` v1 remains append-only. New public surfaces require copied-data ownership,
  capability/`struct_size` gates, lifecycle cleanup, privacy rules, and accepted
  second-source/static evidence.
- Promoted copied events are observational and non-authoritative: no UE pointers, raw
  params, identity, lookup, mutation, return override, pincode/player text publication, or
  broad module SDK claim.
- Plugin unload/init-failure cleanup skips `dlclose` when callback cleanup cannot be
  proven complete, retains the plugin for retry when possible, does not repeat plugin shutdown,
  and leaves the library mapped if retention tracking also fails.
- `oProcessTimer` is the first process-local timer example. Timer ids are process-local,
  not cluster state, UE identity, gameplay/module timer abstractions, or persistent
  handles, or shared scheduler state; owner-token timers require explicit unregister.
  Safe-disabled discovery/config prep succeeds without optional timer capability, while
  active timer config still fails closed if timer capability, owner token, or appended
  timer slots are unavailable.
- `oPolicyAudit` now unregisters its `GameplayPolicyEvent` owner-token handle if init
  fails after callback registration. The SDK fixture covers injected post-registration log
  failure cleanup.
- `oDescriptorCatalog` is the metadata-only descriptor example. It registers no callbacks,
  timers, chat handlers, identity, lookup, mutation, return override, or ABI expansion.
- `oBaseEvents` has a disabled-by-default plugin-local chat command helper over copied
  `ChatMessageEvent` bytes; no command ABI/router, identity, replies, moderation, send-chat
  API, mutation, or extra exported plugin symbols.
- `oChatLogger` and `oChatAudit` are experimental and excluded from default release scope.
  Safe-disabled init requires only the base ABI prefix/owner token; active config fails
  closed on missing capabilities, short `struct_size`, null registration slots, or null
  callback user data.
- ArkServerApi/AseApi remain names and behavior dictionaries for familiar ARK plugin
  concepts. Local `NextGenPlugins` clones are names/demand dictionaries only, not a
  porting target or copying source. Do not copy code, offsets, layouts, vtables, ABI
  assumptions, wrappers, raw UE pointer APIs, `.lib` artifacts, constants, schemas,
  control flow, command parsers, return constants, or implementations.

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
  copied-scalar, and Buff breadth packages remain evidence-only/internal. Mission bool-tail
  preserves `bool_field_size=1`, `bool_byte_offset=0`, `byte_mask=0x01`,
  `field_mask=0xff`, and `native_bool=false`; consume mode accepts documented slices and
  promote mode blocks promotion. This does not authorize Transfer
  runtime work, public Mission SDK, ResourceHandle, identity, mutation, or return override.
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
- Transfer ScriptStruct bool-tail evidence has a refreshed local root; older
  `/servidor/ark/workspace-offline/...20260529...` transfer roots are stale under current
  bool-tail strictness.
- `validate_offline_artifact_gate.py` now consumes `obelisk.artifact-pack.manifest.v1`
  containers: the pack manifest and relative `SHA256SUMS` must match current contents,
  symlinked pack entries fail closed, supported child manifests keep their own
  consume/promote blockers, and `promote` mode blocks the pack as container-only.
  Relative `--root` and protected-root inputs are normalized before direct-path and
  symlink-resolved protected path checks. Duplicate `--target-set` filters in target
  guidance now fail closed instead of emitting repeated planning output.
- `scripts/check_static_tooling.py` records optional radare2/rizin/Ghidra availability and
  runs smoke checks only on approved offline binaries/output roots.
- `APrimalStructure.IsAllowedToBuild` is a high-demand build-policy dictionary seed, but it
  is second-wave only: no committed snapshot, no second-source comparison, no target-set
  promotion, no public StructureEvents/build-policy SDK, no mutation, and no return
  override.
- `players-identity-lifecycle-intake` is a guidance-only target set backed by
  `docs/research/2026-05-30-player-identity-lifecycle-plan.md`; it stays out of RC/public
  target sets, is release-gate rejected, and does not promote identity, lookup, runtime
  work, mutation, or return override.

## Priority Next Steps

- Current post-RC focus: preserve RC scope while reducing architecture debt, improving evidence tooling, and
  promoting only copied module APIs through strict gates.
- `mission-copied-bool-policy-slice` is the next best internal offline copied-data lane:
  it is now planning-only/consume-only, blocks release/public promotion, and keeps
  `GetPlayerUsableItems` recognition-only with no Mission SDK, identity, mutation, or
  return override.
- Item return-only bridge hardening now keeps copied dispatch construction in
  `ProcessEventItemReflection` helpers, with unit coverage for the three supported event
  kinds, `CraftBlueprint` rejection before runtime item-return reflection, exact
  `ReturnValue` scalar scope, attempt-budgeted runtime reads, and no
  identity/mutation/return-override leakage. Dispatcher hot-path allocation has a local
  benchmark gate for no-subscriber and <=4-subscriber snapshots; do not expand it unless
  profiling justifies a larger callback snapshot strategy.
- Structure second-wave next step is offline-only candidate metadata/redaction review for
  `PrimalStructure.IsAllowedToBuild`. There is still no specific IsAllowedToBuild
  candidate pack to validate; fixture-only readiness reports `missing_base_snapshot` for
  both `PrimalStructure.IsAllowedToBuild` and `APrimalStructure.IsAllowedToBuild`. First
  useful action is a sanitized focused snapshot from an approved copied/offline core or
  complete core evidence-pack manifest outside protected server paths; rootless or
  fixture-only reports are a negative guardrail, not progress or promotion evidence. Use
  the binary-scoped `0x5956f30` FName root slot and `0x595b7e0` GObjects candidate, then a
  distinct second-source compare. Do not add either key to release target sets, ABI enums,
  descriptors, dispatchers, public docs, or runtime gates.
- Plugin Hub planning order from current demand map and local `NextGenPlugins` dictionary:
  `docs/PLUGIN_HUB_FOUNDATION_V1.md` is now the contributor-facing foundation boundary,
  backed by `docs/PLUGIN_HUB_CAPABILITY_MATRIX.md`. The fastest honest creator path after
  `v0.1` is small Obelisk-native examples for lifecycle/config/logging, descriptor reads,
  passive copied-chat parsing, process-local timers, and copied policy auditing. Treat
  that as a non-production-ready seed, not a Plugin Hub stability or compatibility claim.
  Keep permissions, RCON, economy, homes/safe zones, structure enforcement, dinos, tribes,
  transfers, inventory, item mutation, identity, lookup, replies, send-chat, moderation,
  and ArkApi portability as design backlogs until their own public surfaces are promoted.
  Keep the clone out of repo and use it only as a names/demand dictionary.
- Artifact-pack contributor onboarding now has `docs/OFFLINE_ARTIFACT_PACKS.md` as the
  concise contributor runbook. It documents normalize/check, consume gate, strict
  target-set coverage, second-source compare, pack-shape expectations, and non-claims.
  Use `--manifest` for structured JSON reports and artifact-pack manifests; keep
  normalizer stdout summaries outside the pack; legacy
  `obelisk.artifact_pack.manifest.v1` spelling and in-pack zero-byte normalizer summaries
  fail closed.
  The default release gate and `check_rc_layout_evidence_smoke.sh` are aligned on the four
  public RC UFunction target sets, including `item-return-only-policy-slice`; the combined
  RC UFunction root helper now requires `--item-return-root` and assembles 12 snapshots.
- Runtime/plugin lifecycle audit found no P1 blocker, but `EventManager` raw ProcessEvent
  unregister still waits behind dispatch callbacks and can deliver already-snapshotted
  callbacks before delayed unregister takes effect. Treat snapshot/in-flight cleanup for
  raw callbacks as v1 debt; current owner cleanup remains the unload barrier.
- Any future live/player validation requires a new approved live-ops brief and beta-test
  notice through the configured local webhook variable when players are involved.

## Agent Protocol

- Lead owns server-safety decisions, GitHub, Discord, and stale-agent cleanup.
- Before each sub-agent round: close stale agents, assign expert role, declare allowed paths,
  pass only the skills required for the task, and record any still-active agent with a polling or integration plan.
- Sub-agents receive scoped expert tasks, safety baseline, allowed paths, forbidden paths,
  required skills, validation expectations, and one concrete expected decision. Do not pass
  leader cadence, unrelated module history, or broad policy unless it changes the task.
