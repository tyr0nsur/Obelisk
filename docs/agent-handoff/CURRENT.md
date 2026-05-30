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
- ResourceHandle/public GObjects remain blocked. The old flag-policy artifact is blocked
  by old artifact vocabulary and missing provenance/caller rows; a `/tmp`
  rich-provenance rehearsal proved the small refresh route can pass preflight and consume
  mode while promote mode stays blocked. Durable refresh still needs preserved
  regenerated/enriched sidecars; see
  `docs/research/2026-05-30-uobject-flag-policy-gate-refresh.md`.

## Priority Next Steps

- Preserve RC scope while moving toward `v1.0`: reduce architecture debt, improve evidence
  tooling, and promote only copied module APIs with strict gates.
- Current post-RC focus: Item return-only policy, Mission copied-bool observer,
  then Transfer `bAccept`. This is no RC public SDK/API promotion. Item return-only and
  Mission copied-bool now have internal/test-only consume-mode policy slices, and Mission
  copied-bool observer hardening also includes recognizer-side canonical-bool rejection
  plus hook-side `params + offset` provenance checks. Keep Item and Mission free of
  `ResourceHandle`, identity, mutation, return override, public Inventory SDK, public
  Mission SDK, hook wiring, marker/env, or runtime logs unless a future separate promotion
  gate changes scope. Transfer `bAccept` is likewise an internal/test-only consume-mode
  policy slice; this handoff does not authorize Transfer runtime work. ResourceHandle
  semantic work still needs helper evidence, mutation-window rejection, and a fail-closed
  contract.
  Commands/chat routing waits on player context, permissions, and safe response semantics.
  ArkServerApi/AseApi remains a names and behavior dictionary only; it is not a porting
  target or copying source. Do not copy offsets, layouts, ABI assumptions, wrappers, raw
  UE pointer APIs, or algorithmic implementations.
- Regenerate the blocked UObject flag-policy artifact with current provenance/caller-row
  requirements before spending more ResourceHandle effort. Do not rerun broad FName,
  GObjects, or core scans unless the binary hash changes or evidence contradicts current
  roots/candidates. A `/tmp` rehearsal proved the small rich-provenance route can pass
  preflight and consume mode while promote mode remains blocked; keep it internal static
  evidence only and use the command shape recorded in
  `docs/research/2026-05-30-uobject-flag-policy-gate-refresh.md`.
- Any future live/player validation requires a new approved live-ops brief and, when
  players are involved, a beta-test notice through the configured local webhook variable.

## Agent Protocol

- Lead owns server-safety decisions, GitHub, and stale-agent cleanup.
- Sub-agents receive scoped expert tasks, not leader cadence or unrelated project policy.
- Before each sub-agent round: close stale agents, assign expert role, declare
  read-only/edit paths, declare allowed paths and required skills, pass only the skills
  required for that scope, state validation expected, state the expected decision, and
  keep integration with lead.
