# Current Agent Handoff

Updated: 2026-05-30

Active routing only: durable evidence belongs in `docs/research/`, resume facts in
`COMPACT_CONTEXT.md`, and old detail in `HISTORY-*.md`.

## Active Objective

- `v0.1.0-rc.1` is published and should be treated as the frozen core-first RC baseline:
  Linux runtime, ProcessEvent hook infrastructure, plugin lifecycle, central install
  layout, `oBaseEvents`, `GameplayPolicyEvent`, minimal copied `ChatMessageEvent`,
  `DescribeResourceKind`, and `DescribeGameplayPolicyEventKind`.
- Do not expand or retag the RC for routine post-RC development. Future work should move
  toward a broader `v1.0` production-stable Obelisk core: general UE4 reflection,
  copied-data module APIs, lifecycle-safe plugins, operator lifecycle tooling, and enough
  compatibility surface to later recreate common ArkApi plugins on Linux.
- Treat chat, inventory, structures, players, tribes, dinos, buffs, missions, transfers,
  commands, permissions, timers, economy/database integrations, and admin tooling as
  module areas above the core. Promote each only through copied-data ABI, privacy,
  lifecycle, and second-source/static evidence gates.

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
- Community updates are lead-only for major public modder-facing milestones, previews,
  migrations, or releases; beta-test activation notices are separate live-ops messages.
  Webhook URLs live only in ignored `local/discord-webhooks.env`: use
  `OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL` for public modder-facing milestones and
  `OBELISK_BETA_TEST_WEBHOOK_URL` for approved in-game test windows. Send professional
  Discord embeds only; never expose raw URLs, player text, secrets, routine validation
  logs, or speculative reversing notes.

## Current Routing Facts

- `v0.1.0-rc.1` is frozen. Public RC scope is only `GameplayPolicyEvent`, minimal copied
  `ChatMessageEvent`, `DescribeResourceKind`, and `DescribeGameplayPolicyEventKind`.
  It is not a production-stable `v1.0` claim and must not be expanded retroactively.
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
- Current post-RC core primitive: owner-token process-local timers. They are ABI
  append-only, zero-failure handles, one-shot/repeating, explicit unregister, and cleaned
  on plugin init failure/unload. Timer ids are not shared config, cluster state, UE
  identity, or persistent handles.
- Internal bridges only: `StructureEventDispatcher`, `InventoryPolicyEventDispatcher`,
  Item/Mission/Transfer recognizers, weak-helper artifacts, GObjects evidence, and route
  observers are planning/evidence inputs until a separate promotion gate changes scope.
- ResourceHandle/public GObjects remain blocked. Latest flag-policy consume check is
  blocked by old artifact vocabulary and missing provenance/caller rows; see
  `docs/research/2026-05-30-uobject-flag-policy-gate-refresh.md`.

## Priority Next Steps

- Preserve RC scope while moving toward `v1.0`: reduce architecture debt, improve evidence
  tooling, and promote only copied module APIs with strict gates.
- Next development target after timer hardening: Item return-only policy modeling inside
  the existing internal recognizer/`GameplayPolicyEvent` path. Keep it copied bools only:
  no `ItemId`, `AdditionalData`, `ResourceHandle`, return override, public Inventory SDK,
  hook wiring, marker/env, or runtime logs until promoted.
- Research order after Item: Mission copied-bool observer, then Transfer `bAccept`.
  Commands/chat routing is important but waits on player context, permissions, and safe
  response semantics. ArkServerApi/AseApi remains names/behavior reference only.
- Regenerate the blocked UObject flag-policy artifact with current provenance/caller-row
  requirements before spending more ResourceHandle effort. Do not rerun broad FName,
  GObjects, or core scans unless the binary hash changes or evidence contradicts current
  roots/candidates.
- Any future live/player validation requires a new approved live-ops brief and, when
  players are involved, a beta-test notice through the configured local webhook variable.

## Agent Protocol

- Lead owns server safety, GitHub, and stale-agent cleanup.
- Before each round: close stale agents, assign expert role, declare read-only/edit paths,
  pass only relevant skills, state validation expected, and keep integration with lead.
