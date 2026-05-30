# Current Agent Handoff

Updated: 2026-05-30

This file is an active routing table only. Durable evidence belongs in `docs/research/`,
resume facts in `COMPACT_CONTEXT.md`, and old detail in `HISTORY-*.md`. Historical
recovery context is not active routing for the current head; use
`git log --oneline -1` rather than preserving old checkpoint slicing here.

## Active Objective

- `v0.1.0-rc.2` is the current published core-first RC baseline: Linux runtime,
  ProcessEvent hook infrastructure, plugin lifecycle, central install layout,
  `oBaseEvents`, `GameplayPolicyEvent`, minimal copied `ChatMessageEvent`,
  `DescribeResourceKind`, `DescribeGameplayPolicyEventKind`, process-local owner-token
  timers, and refreshed RC UFunction second-source evidence.
- RC publication passed a clean release gate on the intended ref with exact tag/ref
  verification. Do not expand, retag, or reinterpret published RC tags for routine
  post-RC work.
- Post-RC work moves toward a broader `v1.0` production-stable core: UE4 reflection,
  copied-data module APIs, lifecycle-safe plugins, operator lifecycle tooling, and a
  Linux-native compatibility surface for familiar ARK plugin concepts.
- Treat chat, inventory, structures, players, tribes, dinos, buffs, missions, transfers,
  commands, permissions, timers, config/logging, economy/database integrations, and admin
  tooling as module areas above the core. Promote each only through copied-data ABI,
  privacy, lifecycle, and second-source/static evidence gates.

## Hard Overrides

- GitHub publication is lead-only and only for an evidenced, stable milestone. No commit,
  push, tag, release-ref update, rebase, or routine checkpoint is authorized by this
  handoff. Stale local tags are recreated only after rerunning the release gate on the
  intended ref and are never reused or pushed without current-turn authorization.
  No tag or release-ref push is authorized without explicit release-manager/lead
  authorization for the current turn.
- GitHub work may be delegated only for an evidenced, stable milestone.
- Any server-backed debug or beta work requires a current approved live-ops brief:
  target instance/map, feature gates, marker/env changes, restart/start/stop window,
  player notice path when needed, evidence capture, and rollback.
- No server target has standing approval. Do not restart servers, edit `/servidor/ark`,
  change markers, run ReflectionScanner, attach ptrace/gcore, enable broad ProcessEvent
  tracing, or publish runtime observations outside an exact approved run. Technical
  progress is only a reason to request a scoped run; it is not approval by itself.
- Runtime posture is default-deny for filtered/global raw `ProcessEvent`, public
  `CallProcessEvent`, ProcessEvent blocking, broad tracing, ReflectionScanner, debug
  control, and observers unless the matching approved env+marker pair is enabled for a
  scoped debug window.
- Community and beta-test Discord sends are lead-only and require explicit current-turn
  approval for public milestones or approved beta-test windows. Webhook URLs stay only in
  ignored `local/discord-webhooks.env`; repo text may name only
  `OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL` and `OBELISK_BETA_TEST_WEBHOOK_URL`.
  Prefer `scripts/send_discord_embed.py --dry-run` before an approved send. Use no
  Discord for internal rounds or agent status, and never expose raw URLs, player text,
  secrets, routine validation logs, or speculative reversing notes.

## Current Routing Facts

- RC public scope remains limited to `GameplayPolicyEvent`, the minimal copied
  `ChatMessageEvent`, `DescribeResourceKind`, and
  `DescribeGameplayPolicyEventKind`. It is not a production-stable `v1.0` claim and must
  not be expanded retroactively. `v0.1.0-rc.2` additionally includes process-local
  owner-token timers as core runtime API without promoting gameplay/module timers.
  Post-RC internal modeling does not change the RC public API; accepted RC UFunction
  second-source root evidence remains the publication baseline.
- `ObeliskApi` v1 remains append-only. New public surfaces require copied-data ownership,
  explicit capability/`struct_size` gates, lifecycle cleanup, privacy rules, and accepted
  second-source/static evidence.
- Promoted copied events remain non-authoritative: no UE pointers, raw params, object
  identity, lookup, mutation, return override, pincode/player text publication, or broad
  module SDK claim.
- Owner-token process-local timers are now first-stable v0.1 core scope, not gameplay/module
  timer abstractions, gameplay/module timer APIs, or shared scheduler state. They are ABI
  append-only, zero-failure handles, one-shot/repeating, explicit unregister, and cleaned
  on plugin init failure/unload. Timer ids are not shared config, cluster state, UE
  identity, or persistent handles. `oProcessTimer` is the first-party example with SDK
  consumer coverage and release-gate dry-run publication.
- Plugin unload now treats callback cleanup failure as a hard `dlclose` blocker: unload
  calls shutdown once, attempts owner cleanup, retains the plugin mapped for retry when
  cleanup fails, does not repeat plugin shutdown on retry, and only closes the library
  after a successful cleanup retry. Init-failure cleanup follows the same retry path if
  callback cleanup cannot be proven complete. This is internal runtime hardening, not a C
  ABI change.
- `oBaseEvents` has a disabled-by-default plugin-local `chat_command_helper` over copied
  `ChatMessageEvent` bytes. It has config and owner-token register/unregister, but no
  command ABI/router, identity, reply, mutation, or extra exported plugin symbols beyond
  `GetInfo`/`Init`/`Shutdown`.
- `oDescriptorCatalog` is the next release-scope reference plugin after timers: it
  demonstrates `DescribeResourceKind` and `DescribeGameplayPolicyEventKind` consumption
  only, validates descriptor coherence, and logs sanitized metadata without callbacks,
  timers, chat, identity, lookup, mutation, return override, or ABI expansion.
- Internal/evidence-only lanes include `ProcessEventBuffReflection`,
  `StructureEventDispatcher`, `InventoryPolicyEventDispatcher`, Item/Mission/Transfer
  recognizers, weak-helper artifacts, GObjects evidence, route observers, and structure
  copied-scalar dispatch hardening. None of these promote public module SDKs, hooks,
  callbacks, identity, lookup, mutation, return override, raw params, UE pointers, or
  `ResourceHandle`.
- Structure copied-event dispatch is hardened to the Inventory copied-event pattern:
  live-subscriber dispatch budget, self-contained copied payload before reservation,
  copy/move rebinding for owned scalar spans, scalar range validation, fail-closed reader
  exceptions, exact descriptor field/type matching, and hot-path subscriber checks.
- Structure non-PIN copied-scalar dispatch now has explicit internal helpers for
  `SetVariant`, `AllowToggleActivation`, and `CanSeat`. The general structure recognizer
  still accepts the six historical structure targets; use the non-PIN helpers only where
  PIN/access/demolish targets must be rejected before event build or dispatch budget.
  This remains evidence-only internal plumbing, not public `StructureEvents`, runtime
  observation, mutation, return override, or server-test authorization.
- ArkServerApi/AseApi may be used only as a dictionary for names and behavior / familiar
  concept grouping. It is not a porting target or copying source. Do not copy offsets,
  layouts, ABI assumptions, wrappers, raw UE pointer APIs, `.lib` artifacts, or
  implementations.

## Evidence State

- Minimal second-source intake supports only the copied `GameplayPolicyEvent`
  structure/inventory lane. Consume gates are accepted, `promotion_ready=false`, and it
  does not authorize Inventory SDK, StructureEvents, identity, lookup, mutation, return
  override, or raw UE internals.
- `v0.1.0-rc.2` was published from `1a7cd98` after refreshing the RC UFunction
  second-source root for the intended ref and passing the release gate with all nine
  public RC targets accepted. The historical `v0.1.0-rc.1` root remains evidence for that
  tag only; future RC/stable candidates must regenerate a root for their exact intended
  ref. See
  `docs/research/2026-05-30-head-rc-second-source-refresh-gap.md`.
- Mission copied-bool, Transfer `bAccept`, Structure return-only, Structure non-pin
  copied-scalar, and Buff breadth packages remain evidence-only/internal. Consume mode
  accepts the relevant slices where documented, while promote mode remains blocked. See
  `docs/research/` for artifact paths, manifests, hashes, and target lists.
- Item return-only policy now has three append-only public `GameplayPolicyEvent` kinds for
  `AllowEquipItem`, `CanRepair`, and `UseItemOntoItem`, all copied `ReturnValue` only and
  `inventory_item` category only. The private `ItemReturnEventDispatcher` and gated hook
  producer exist, but runtime validation, broader item/inventory decoding, identity,
  lookup, mutation, return override, `ResourceHandle`, public Inventory SDK, and public
  Items SDK remain absent. Stable wrapper/posture tooling now treats
  `enable-item-return-events` and `OBELISK_ITEM_RETURN_EVENTS_*` as experimental and
  forbidden in stable posture. Do not reuse `INVENTORY_USE_CHECK` or map
  `CanRepair.bIgnoreInventoryRequirement` to `IGNORE_COOLDOWN`.
- `ChatMessageEvent` is sufficient for plugin-local command parsing/handlers in the next
  RC scope when described as copied chat input only, not a command SDK: no identity,
  permissions, replies, send-chat API, blocking, mutation, or return override. Before an
  RC claim, rerun chat/ABI/SDK/release guardrails.
- Mission copied-bool observer remains internal and non-authoritative. Mission bool-tail
  evidence is consume-only non-promotion: consume mode accepts and promote mode blocks.
- Mission bool-tail evidence preserves `bool_field_size=1`, `bool_byte_offset=0`,
  `byte_mask=0x01`, `field_mask=0xff`, and `native_bool=false`.
- Mission test-only recognizer hardening now enforces that exact bool-tail metadata before
  exposing copied bool ranges. This still does not promote runtime wiring, public Mission
  SDK/API, identity, mutation, return override, or server validation.
- Buff breadth is layout-only evidence for the accepted target set. It is not a public
  Buff SDK/runtime promotion and does not authorize hooks, callbacks, object/class
  exposure, mutation, return override, raw params, `ResourceHandle`, or gameplay
  semantics.
- GObjects two-core strict consume tooling can rebuild a complete artifact-identity
  manifest from the existing offline reports. The local gate now rejects mismatched
  `artifact_identity.artifact_sha256`; durable `/servidor/ark/workspace-offline`
  regeneration remains a separate explicit offline write step and still does not promote
  public GObjects, `ResourceHandle`, lookup, identity, mutation, or return override.
- Transfer ScriptStruct fixtures and the refreshed local second-source root preserve
  `ArkTributePlayerData` bool-tail metadata for `bWasAllowDPCUpload`, `bWithItems`, and
  `bForServerTransfer`: `bool_field_size=1`, `bool_byte_offset=0`, `byte_mask=0x1`,
  `field_mask=0xff`, and `native_bool=false`. Current refreshed evidence accepted
  `transfer-scriptstruct` 2/2 as layout-only at
  `/home/flowcommunity-ark/obelisk-artifacts/transfer-scriptstruct-bool-tail-refresh-20260530T163945Z`.
  Its regenerated `inventory-pack` includes structs, has consume gate accepted, promote
  gate blocked, and normalized `artifact-pack.manifest.json`/`SHA256SUMS`. The offline
  artifact gate now rejects `transfer-scriptstruct` inventory packs that omit
  `scriptstructs` or any of the three exact `ArkTributePlayerData` bool-tail contracts.
  The gate also treats `PrimalLocalProfile.ArkTributePlayerData` redacted ScriptStruct
  signatures as Transfer evidence even if `target_sets/source_target_sets` omit
  `transfer-scriptstruct`, and requires complete
  `obelisk.redacted-scriptstruct-target-set-coverage.v1` coverage before accepting that
  Transfer signature family.
  The older root under `/servidor/ark/workspace-offline/transfer-second-source-20260529T154200Z/scriptstruct-snapshots`
  is stale under current bool-tail strictness and should not be reused for current
  comparisons.

## ResourceHandle Blockers

- ResourceHandle/public GObjects remain blocked. The old flag-policy artifact is obsolete;
  the durable rich-provenance refresh is preserved in
  `docs/research/2026-05-30-uobject-flag-policy-gate-refresh.md`.
- Consume mode accepts it and promote mode stays blocked.
- Do not rerun broad FName, GObjects, or core scans for ResourceHandle unless the binary
  hash changes or evidence contradicts current roots/candidates.
- Do not relax `evaluate_resource_handle_revalidation.py` to infer artifact identity from
  bare hashes. Strict mode requires complete top-level `artifact_identity` from producers.
- Keep `InternalUObjectRevalidationCandidate` internal: no public `ResourceHandle`,
  GObjects, identity, lookup, lifecycle names, mutation, return override, object indices,
  serials, or UE pointers.
- `ResourceHandle` semantic promotion still needs helper evidence, mutation-window
  rejection, runtime negative samples, and a fail-closed lookup contract.
- The ResourceHandle evaluator now has identity-complete strict input under
  `/home/flowcommunity-ark/obelisk-artifacts/resourcehandle-identity-complete-failclosed-20260530T165521Z/`:
  3/3 inputs have complete `artifact_identity`, the evaluator output carries
  `output_artifact_identity.artifact_sha256=d358b16e4c70ef3b320e00143f3ed2bd41581c4d40045974b02ef61c55b4dab2`,
  44/44 reconciliation samples are accepted, field-window evidence is coherent, and the
  result remains fail-closed with `promotion_ready=false`,
  `public_resource_handle_ready=false`, and `post_callback_resource_handle_ready=false`.
- The internal post-callback rejection contract is preserved at
  `/home/flowcommunity-ark/obelisk-artifacts/resourcehandle-post-callback-contract-20260530T171910Z/`.
  `post-callback-contract.json` has file SHA256
  `caaad8b80608e6af603da413f021ae43c8a44a55a3c1964f9e4e69eee10c4fd0` and
  `output_artifact_identity.artifact_sha256=a80e8597a027fd8e7a3c5bb2c42abfc7523e1dc13c69111629aed3450d8260d5`.
  Consume mode accepts it and promote mode blocks with
  `promote_mode_post_callback_contract_candidate_only` and
  `promote_mode_manifest_has_non_claims`. It is a negative lifecycle
  contract only: frame-local internal candidate, post-callback lookup/use rejected, no
  public `ResourceHandle`, identity, GObjects lookup, mutation, return override, or Plugin
  Hub promise.
- Next useful ResourceHandle work is semantic, not more broad static scanning: rejected
  runtime object samples and serial reuse/wraparound policy before any public identity or
  lookup surface can be considered. Do not create another serial policy report from frozen
  cores only; wait for real temporal evidence or version-matched source/decompiler
  correlation.

## Priority Next Steps

- Preserve RC scope while reducing architecture debt, improving evidence tooling, and
  promoting only copied module APIs through strict gates.
- Previous internal recognizer order was Item return-only policy, Mission copied-bool
  observer, then Transfer `bAccept`. That is historical pre-promotion context for the item
  slice; only the three copied `ReturnValue` item checks are promoted publicly, and only as
  `GameplayPolicyEvent` kinds.
- Current post-RC focus: keep remaining item producer/runtime validation and Mission
  copied-bool work internal, then if Transfer continues, consume the refreshed
  bool-tail-complete ScriptStruct root for redacted signature hardening/refresh before any
  Transfer payload/redaction work. The inventory pack is now normalized locally and guarded
  by a transfer-specific bool-tail contract; redacted ScriptStruct signatures now preserve
  the same bool-tail metadata and reject incomplete `transfer-scriptstruct` signatures in
  the offline artifact gate. Public Inventory SDK, Items SDK, Mission SDK, and Transfer SDK
  surfaces remain absent, and this does not authorize Transfer runtime work.
- Runtime lifecycle callback-cleanup debt is addressed in post-RC head: `PluginManager`
  now skips `dlclose` when callback cleanup fails, retains the plugin for retry, preserves
  owner-token unregister while unloading, and avoids repeating shutdown on retry.
- Next Item runtime round, if pursued, should validate only the private producer behind
  fail-closed observer gates and post-original copied payloads for the already-promoted
  three `GameplayPolicyEvent` kinds. Do not route it through
  `InventoryPolicyEventKind::CanUse`, and do not expand into an Items SDK or Inventory SDK
  without a separate promotion gate. The stale bool-tail comparison gap is closed by
  `/home/flowcommunity-ark/obelisk-artifacts/item-return-only-bool-tail-refresh-20260530T172552Z`:
  current `compare_reflection_snapshots.py --target-set item-return-only-policy-slice`
  accepts `3/3` (`AllowEquipItem`, `CanRepair`, `UseItemOntoItem`) as layout-only
  second-source evidence, consume gate accepts, and promote gate blocks with
  `promote_mode_readiness_report_layout_only`. `analyze_runtime_observer_log.py`
  recognizes sanitized item-return enabled/rejected/dispatched lines, but any live item
  runtime window still requires a separate live-ops brief and must remain private producer
  validation only.
- Secondary evidence-only lanes may continue for structure non-pin copied scalars and Buff
  breadth, but they must not imply runtime work, marker/env changes, public SDK expansion,
  or RC surface changes.
- Any future live/player validation requires a new approved live-ops brief and, when
  players are involved, a beta-test notice through the configured local webhook variable.

## Agent Protocol

- Lead owns server-safety decisions, GitHub, Discord, and stale-agent cleanup.
- Sub-agents receive scoped expert tasks, safety baseline, allowed paths, forbidden
  paths, required skills, expert role, validation expectations, and a concrete expected
  decision. Pass only the skills required for the task. Do not pass leader cadence,
  unrelated module history, or broad policy unless it changes the task.
- Each sub-agent prompt must include the expected decision in one line.
- Before each sub-agent round: close stale agents, assign expert role, declare allowed
  paths, pass only required skills, and record any still-active agent with a polling or
  integration plan.
