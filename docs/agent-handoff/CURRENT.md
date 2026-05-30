# Current Agent Handoff

Updated: 2026-05-30

This is an active routing table only: durable evidence belongs in `docs/research/`, resume facts in
`COMPACT_CONTEXT.md`, and old detail in `HISTORY-*.md`.
historical recovery context is not active routing for the current head; use
`git log --oneline -1` for the current head rather than by the old 0-pre/0a/0b slicing
sequence.

## Active Objective

- `v0.1.0-rc.1` is published and should be treated as the frozen core-first RC baseline:
  Linux runtime, ProcessEvent hook infrastructure, plugin lifecycle, central install
  layout, `oBaseEvents`, `GameplayPolicyEvent`, minimal copied `ChatMessageEvent`,
  `DescribeResourceKind`, and `DescribeGameplayPolicyEventKind`.
- RC publication passed a clean release gate on the intended ref and exact tag/ref
  verification; stale tags are recreated only after rerunning the gate and are not reused.
- Do not expand or retag the RC for routine post-RC development. Future work should move
  toward a broader `v1.0` production-stable Obelisk core: general UE4 reflection,
  copied-data module APIs, lifecycle-safe plugins, operator lifecycle tooling, and enough
  compatibility surface for familiar ARK plugin concepts on Linux.
- Treat chat, inventory, structures, players, tribes, dinos, buffs, missions, transfers,
  commands, permissions, gameplay/module timer abstractions, economy/database
  integrations, and admin tooling as module areas above the core. Promote each only
  through copied-data ABI, privacy, lifecycle, and second-source/static evidence gates.

## Hard Overrides

- GitHub work may be delegated only for an evidenced, stable milestone. Keep commits
  minimized; no routine push/checkpoint unless selected for validated publication. No tag
  or release-ref push is authorized without explicit release-manager/lead authorization
  for the current turn. Stale local tags are recreated only after rerunning the gate on
  the intended ref and are not reused or pushed.
- Any server-backed debug or beta work requires an approved live-ops brief for that turn:
  target instance/map, feature gates, marker/env changes, restart/start/stop window,
  notice path when players are involved, evidence capture, and rollback. No server target
  has standing approval for starts, stops, restarts, marker edits, or runtime observation.
  Technical progress is only a reason to request a scoped run; it is not approval by
  itself.
- Do not restart servers, edit `/servidor/ark`, change markers, run ReflectionScanner,
  attach ptrace/gcore, enable broad ProcessEvent tracing, or publish runtime observations
  outside an approved exact run. For in-game function tests, use an operator-approved
  notice before activation; keep operator secret endpoints out of repo files, skills,
  prompts, and handoff notes.
- Community updates are lead-only for major public modder-facing milestones, migrations,
  or releases; beta-test activation notices are separate live-ops messages.
  Webhook URLs live only in ignored `local/discord-webhooks.env`: use
  `OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL` for public modder-facing milestones and
  `OBELISK_BETA_TEST_WEBHOOK_URL` for approved in-game test windows. Send professional
  Discord embeds only; never expose raw URLs, player text, secrets, routine validation
  logs, or speculative reversing notes. Use `community` only for stable modder-facing
  milestones, `beta-test` only for approved player action windows, and no Discord for
  internal rounds or agent status. Explicit current-turn approval is required for every
  Discord send; publication approval does not imply Discord approval. Prefer `scripts/send_discord_embed.py --dry-run` as the
  guarded workflow; run it before any approved send, then verify title, description,
  status/scope, and 2-5 fields are public-safe.

## Current Routing Facts

- `v0.1.0-rc.1` is frozen. RC public scope remains limited to `GameplayPolicyEvent`, the
  minimal copied `ChatMessageEvent`, `DescribeResourceKind`, and
  `DescribeGameplayPolicyEventKind`. It is not a production-stable `v1.0` claim and must
  not be expanded retroactively. Post-RC internal modeling does not change the RC public
  API; accepted RC UFunction second-source root evidence remains the publication baseline.
- `ObeliskApi` v1 remains append-only. New public surfaces need copied-data ownership,
  explicit capability/`struct_size` gates, lifecycle cleanup, privacy rules, and accepted
  second-source/static evidence.
- Promoted copied events remain non-authoritative: no UE pointers, raw params, object
  identity, lookup, mutation, return override, pincode/player text publication, or broad
  module SDK claim.
- Runtime posture is default-deny for filtered/global raw `ProcessEvent`, public
  `CallProcessEvent`, ProcessEvent blocking, broad tracing, ReflectionScanner, debug
  control, and observers unless an exact approved debug window enables the matching
  env+marker pair.
- Current post-RC core primitive: owner-token process-local timers. They are core runtime
  utilities only, not gameplay/module timer abstractions or shared scheduler state. They
  are ABI append-only, zero-failure handles, one-shot/repeating, explicit unregister, and
  cleaned on plugin init failure/unload. Timer ids are not shared config, cluster state,
  UE identity, or persistent handles. `oProcessTimer` is the first-party process-local timer
  example and has SDK consumer coverage for disabled config, active one-shot callback,
  missing capability, short API, zero owner token, registration failure, post-registration
  init-failure cleanup, idempotent shutdown, and shutdown unregister.
- Internal bridges only: `StructureEventDispatcher`, `InventoryPolicyEventDispatcher`,
  Item/Mission/Transfer recognizers, weak-helper artifacts, GObjects evidence, and route
  observers are planning/evidence inputs until a separate promotion gate changes scope.
- Structure copied-event dispatch has been hardened to match the Inventory copied-event
  safety pattern: dispatch budget requires a live subscriber, matched invocations build
  one self-contained copied payload before reservation, copy/move rebinding keeps scalar
  spans owned, scalar range sizes are validated, and reader exceptions fail closed. This
  remains internal copied-scalar infrastructure only; it does not promote public
  StructureEvents, identity, lookup, mutation, return override, or `ResourceHandle`.
  Follow-up contract hardening also rejects any structure event whose scalar fields/types
  do not exactly match the public descriptor for that event kind, and the hook hot-path
  predicate now requires structure subscribers before dispatch budget can activate
  structure observation.
- ResourceHandle/public GObjects remain blocked. The old flag-policy artifact is obsolete;
  the durable rich-provenance refresh is preserved at
  `/home/flowcommunity-ark/obelisk-artifacts/uobject-flag-policy-refresh-20260530T071436Z/`.
  It now includes `artifact-pack.manifest.json`
  (`sha256=1f678c05461131055e4b18fd68862de431a27bbf49609297030ac62bf6f5478d`)
  and `SHA256SUMS`
  (`sha256=cf76ee33a8ea640233af7eff4de78171254a5ee5fa11de714259b27f2731a87a`).
  Consume mode accepts it and promote mode stays blocked with candidate-only/non-claim
  blockers; see `docs/research/2026-05-30-uobject-flag-policy-gate-refresh.md`.

## Priority Next Steps

- Preserve RC scope while moving toward `v1.0`: reduce architecture debt, improve evidence
  tooling, and promote only copied module APIs with strict gates.
- Current post-RC focus: Item return-only policy, Mission copied-bool observer, then
  Transfer `bAccept`.
- The current pushed post-RC line has `oBaseEvents` with a
  disabled-by-default plugin-local `chat_command_helper` over copied `ChatMessageEvent`
  bytes, with config, owner-token register/unregister, no command ABI/router, no identity,
  no reply, no mutation, and no extra exported plugin symbols beyond `GetInfo`/`Init`/
  `Shutdown`. Full build, CTest 61/61, focused guardrails, `git diff --check`, and
  exported-symbol audit passed before push.
- The current pushed post-RC line also adds `ProcessEventBuffReflection` as a
  test-only/internal target. It is
  not linked into `libobelisk.so`, not SDK-facing, and does not authorize runtime Buff
  hooks/callbacks, public Buff SDK, object/class exposure, mutation, return override, raw
  params, `ResourceHandle`, or gameplay semantics.
- ArkServerApi/AseApi dictionary review confirms the fastest stable plugin-facing route
  remains copied `GameplayPolicyEvent` structure/inventory, chat helper ergonomics,
  process-local timers, and config/logging/lifecycle helpers. Use AseApi only for names
  and behavior / familiar concept grouping; it is not a porting target or copying source.
  Do not copy offsets, layouts, ABI assumptions, wrappers, raw UE pointer APIs, or
  implementations.
- The latest `minimal-second-source-intake` consume refresh is preserved at
  `/home/flowcommunity-ark/obelisk-artifacts/minimal-second-source-intake-offline-20260530T075501Z/`:
  4/4 targets accepted, consume gates accepted, and `promotion_ready=false`. It supports
  the copied `GameplayPolicyEvent` structure/inventory lane only, not Inventory SDK,
  StructureEvents, identity, lookup, mutation, return override, or raw UE internals.
  The pack has been normalized with relative checksums and `artifact-pack.manifest.json`
  (`sha256=072ff1f71c59e59189fa53922376dfc61d00915cfcd57817b1e5eacbc8200f8c`);
  `SHA256SUMS`
  (`sha256=21d8b0c0f30799b43110ddd4eed2484cc8c8527df878139dde28bc7d12598cf0`)
  verifies the manifest, readiness report, gate results, and redacted signatures.
- Existing internal policy-slice artifacts remain evidence-only: Item return-only
  (`item-return-only-policy-slice-20260530T072255Z`, plus second source
  `item-return-only-second-source-20260530T084918Z`), Mission copied-bool
  (`mission-copied-bool-tail-policy-slice-20260530T090211Z`), and Transfer `bAccept`
  (`transfer-baccept-only-policy-slice-20260530T073308Z`): consume mode accepts and promote
  mode blocks for all. They do not authorize public module SDKs, hook wiring, markers/env,
  runtime logs, public Inventory SDK, public Mission SDK, identity, lookup, mutation,
  return override, or `ResourceHandle`. Mission bool-tail evidence preserves
  `bool_field_size=1`, `bool_byte_offset=0`, `byte_mask=0x01`, `field_mask=0xff`, and
  `native_bool=false`.
  Post-RC recognizer order remains Item return-only policy, Mission copied-bool observer,
  then Transfer `bAccept`; this is no RC public SDK/API promotion and does not authorize
  Transfer runtime work.
- Buff breadth now has accepted offline second-source layout evidence at
  `/servidor/ark/workspace-offline/buff-breadth-intake-second-source-20260530T091014Z/`.
  The target set is exactly `PrimalBuff.BuffOverrideInventoryAccessInput`,
  `PrimalBuff.BPCustomAllowAddBuff`, and `PrimalBuff.BPPreventAddingOtherBuff`; readiness
  accepts 3/3 comparable targets at layout-only scope and consume gate accepts the report.
  This is not a public Buff SDK/runtime promotion and does not authorize hooks, callbacks,
  object/class exposure, mutation, return override, raw params, `ResourceHandle`, or
  gameplay semantics.
- Structure return-only now has an internal consume-mode policy slice at
  `/home/flowcommunity-ark/obelisk-artifacts/structure-return-only-policy-slice-20260530T093002Z/`.
  It copies only the two `AllowStructureAccess`/`IsAllowedToDemolish` return bools,
  redacts `ForPC`, defers `VerifyPinCode`/activation/variant/seating targets, accepts
  consume mode, and blocks promote mode. No public `StructureEvents`, identity, lookup,
  mutation, return override, `ResourceHandle`, hook wiring, dispatcher wiring, or runtime
  observation is promoted.
  `structure-nonpin-copied-scalar-policy-slice` now exists as an offline evidence-only
  builder/gate path. It excludes `VerifyPinCode`, copies only
  `SetVariant.{VariantIndex,bForceSet,ReturnValue}`,
  `AllowToggleActivation.ReturnValue`, and `CanSeat.{bForce,ReturnValue}`, accepts consume
  mode, and blocks promote mode with
  `promote_mode_structure_nonpin_copied_scalar_policy_slice_evidence_only`.
- Do not rerun broad FName, GObjects, or core scans for ResourceHandle unless the binary
  hash changes or evidence contradicts current roots/candidates. Do not relax
  `evaluate_resource_handle_revalidation.py` to infer artifact identity from bare hashes.
  The correct strict-mode path is complete top-level `artifact_identity` from producers
  (`reconcile_gobjects_samples.py`, `build_static_global_promotion_evidence.py`) and
  regenerated offline artifacts. Keep `InternalUObjectRevalidationCandidate` internal:
  no public ResourceHandle, GObjects, identity, lookup, lifecycle names, mutation, return
  override, object indices, serials, or UE pointers. ResourceHandle semantic work still
  needs helper evidence, mutation-window rejection, runtime negative samples, and a
  fail-closed lookup contract.
- Any future live/player validation requires a new approved live-ops brief and, when
  players are involved, a beta-test notice through the configured local webhook variable.

## Agent Protocol

- Lead owns server-safety decisions, GitHub, and stale-agent cleanup.
- Sub-agents receive scoped expert tasks, not leader cadence or unrelated project policy.
- Before each sub-agent round: close stale agents, assign expert role, declare allowed paths,
  required skills, pass only the skills required, state validation and expected decision.
