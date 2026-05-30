# Current Agent Handoff

Updated: 2026-05-30

This file is an active routing table only. Durable evidence belongs in `docs/research/`,
resume facts in `COMPACT_CONTEXT.md`, and old detail in `HISTORY-*.md`. Historical
recovery context is not active routing for the current head; use
`git log --oneline -1` rather than preserving old checkpoint slicing here.

## Active Objective

- `v0.1.0-rc.1` is the published frozen core-first RC baseline: Linux runtime,
  ProcessEvent hook infrastructure, plugin lifecycle, central install layout,
  `oBaseEvents`, `GameplayPolicyEvent`, minimal copied `ChatMessageEvent`,
  `DescribeResourceKind`, and `DescribeGameplayPolicyEventKind`.
- RC publication passed a clean release gate on the intended ref with exact tag/ref
  verification. Do not expand, retag, or reinterpret the RC for routine post-RC work.
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
  not be expanded retroactively. Post-RC internal modeling does not change the RC public
  API; accepted RC UFunction second-source root evidence remains the publication baseline.
- `ObeliskApi` v1 remains append-only. New public surfaces require copied-data ownership,
  explicit capability/`struct_size` gates, lifecycle cleanup, privacy rules, and accepted
  second-source/static evidence.
- Promoted copied events remain non-authoritative: no UE pointers, raw params, object
  identity, lookup, mutation, return override, pincode/player text publication, or broad
  module SDK claim.
- Current post-RC core primitive: owner-token process-local timers. They are not part of
  the RC public surface, gameplay/module timer abstractions, gameplay/module timer APIs,
  or shared scheduler state.
  They are ABI append-only, zero-failure handles, one-shot/repeating, explicit unregister,
  and cleaned on plugin init failure/unload. Timer ids are not shared config, cluster
  state, UE identity, or persistent handles. `oProcessTimer` is the first-party example
  with SDK consumer coverage.
- `oBaseEvents` has a disabled-by-default plugin-local `chat_command_helper` over copied
  `ChatMessageEvent` bytes. It has config and owner-token register/unregister, but no
  command ABI/router, identity, reply, mutation, or extra exported plugin symbols beyond
  `GetInfo`/`Init`/`Shutdown`.
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
- Item return-only, Mission copied-bool, Transfer `bAccept`, Structure return-only,
  Structure non-pin copied-scalar, and Buff breadth packages are evidence-only/internal.
  Consume mode accepts the relevant slices where documented, while promote mode remains
  blocked. See `docs/research/` for artifact paths, manifests, hashes, and target lists.
- Item return-only policy remains internal and non-authoritative: no public Inventory SDK,
  hook wiring, markers/env, runtime logs, identity, lookup, mutation, return override, or
  ResourceHandle.
- Mission copied-bool observer remains internal and non-authoritative. Mission bool-tail
  evidence is consume-only non-promotion: consume mode accepts and promote mode blocks.
- Mission bool-tail evidence preserves `bool_field_size=1`, `bool_byte_offset=0`,
  `byte_mask=0x01`, `field_mask=0xff`, and `native_bool=false`.
- Buff breadth is layout-only evidence for the accepted target set. It is not a public
  Buff SDK/runtime promotion and does not authorize hooks, callbacks, object/class
  exposure, mutation, return override, raw params, `ResourceHandle`, or gameplay
  semantics.

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

## Priority Next Steps

- Preserve RC scope while reducing architecture debt, improving evidence tooling, and
  promoting only copied module APIs through strict gates.
- Current post-RC focus: Item return-only policy, Mission copied-bool observer, then
  Transfer `bAccept`; this is no RC public SDK/API promotion and does not authorize
  Transfer runtime work.
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
