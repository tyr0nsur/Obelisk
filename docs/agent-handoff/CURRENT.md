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

## Current Routing Facts

- ABI/API: `ObeliskApi` v1 stays append-only for `v0.1.0`; public gameplay SDK surfaces
  require accepted second-source evidence, copied-data ownership, and lifecycle gates.
- RC public scope remains limited to `GameplayPolicyEvent`, the minimal copied
  `ChatMessageEvent`, `DescribeResourceKind`, and `DescribeGameplayPolicyEventKind`.
- Promoted gameplay surface: `GameplayPolicyEvent` is the only public gameplay policy
  event, backed by `docs/public_gameplay_events.json` and
  `docs/research/2026-05-29-public-gameplay-event-readiness-audit.md`. Its structure and
  inventory inputs are copied/redacted POD only; no UE pointers, raw params, identity,
  mutation, or return override are promoted. The separate minimal `ChatMessageEvent` RC
  surface is a copied chat notification contract, not a gameplay policy/module SDK.
- Promoted helpers: `DescribeResourceKind` and `DescribeGameplayPolicyEventKind` are
  metadata-only descriptors for known resource categories and promoted policy event kinds.
  They are not object identity, UE lookup, mutation, return-override, module SDK, or
  `ResourceHandle` surfaces.
- RC chat surface: minimal copied `ChatMessageEvent` is backed by accepted
  `chat-message-intake` evidence and copied plugin delivery logs; see
  `docs/research/2026-05-29-chat-message-second-source-readiness.md`. The latest copied
  `oChatLogger` beta evidence validates plugin-facing delivery for `send_mode=0,1,2,3`
  with `flags=0x1`, bounded `mode_count` metadata, and no raw text/identity/pointer logs.
  This promotes only the minimal copied notification contract for plugin-local parsing;
  it does not promote command routing, sender identity, moderation/blocking, mutation,
  return override, or UE internals. `docs/public_gameplay_events.json` keeps the event in
  `rc_events`, not a broad stable chat API.
- Player-backed beta readiness remains limited to minimal `ChatMessageEvent` copied
  delivery if a new approved beta window is opened. Inventory, mission, item, dino, buff,
  tribe, transfer, admin, identity, mutation, and return override are not ready for
  player-facing SDK tests.
- ResourceHandle remains blocked on `uobject_flags_validity_semantics_unproven`.
  Primary Ragnarok copied-core serial scan now has 44 coherent `0x4000` rejected-object
  candidates; focused reconciliation resolved them as `ParticleSystemComponent0` under
  `Text_Actor` / `Text_Actor_C`. This is internal blocker evidence only, not public
  handle/lookup/identity/lifetime promotion. Serial-scan gate consumption requires
  `scan_limit` to be present, match provenance, and bound sparse candidate indices.
- Runtime posture remains default-deny for filtered/global raw `ProcessEvent` callbacks,
  public `CallProcessEvent`, blocking, broad tracing, scanner/debug controls, and
  observers. Filtered raw callbacks require `OBELISK_ALLOW_FILTERED_PROCESS_EVENT_CALLBACKS=1`
  plus `allow-filtered-process-event-callbacks`; copied events are the RC plugin paths.
  `CallProcessEvent` is ABI v1 compatibility/debug only, not owner-scoped, and out of RC.
- Internal bridges only: `core/StructureEventDispatcher` and
  `core/InventoryPolicyEventDispatcher` feed copied-scalar policy events. They do not
  promote standalone public StructureEvents or Inventory SDKs.
- `plugins/oPolicyAudit` is an experimental `GameplayPolicyEvent` example, outside first
  release scope, built only with `-DOBELISK_BUILD_EXPERIMENTAL_PLUGINS=ON`.
- `v0.1.0-rc.1` publication completed after `scripts/check_release_readiness.sh` passed
  without `--allow-dirty` using the accepted RC UFunction second-source root and after
  exact tag/ref verification. Treat this as a published RC baseline only, not a
  production-stable `v1.0` claim.
- Offline/module evidence stays in dated research notes. Use
  `docs/research/2026-05-29-minimal-second-source-readiness.md`,
  `docs/research/2026-05-29-dino-compact-second-source-readiness.md`,
  `docs/research/2026-05-29-buff-compact-second-source-result.md`,
  `docs/research/2026-05-29-item-compact-second-source-readiness.md`,
  `docs/research/2026-05-29-inventory-action-redacted-signature-readiness.md`, and
  `docs/research/2026-05-29-mission-reflection-internal-readiness.md` for exact target
  counts, blockers, and accepted/rejected promotion claims.
- Canonical offline roots for post-RC modules: Mission compact refresh `20260530T020021Z`;
  Item `20260529T141900Z`/`20260530T013606Z`; Transfer `20260529T154200Z`.
- Transfer second-source evidence is accepted as layout-only. No public Transfer SDK,
  object identity, payload decoding, mutation, return override, runtime hooks, or
  `ResourceHandle` claim is promoted.
- Internal recognizers may expand only as fixture-backed, SHA-gated, copied-scalar
  planning aids. Inventory dispatch stays exact-shape/fail-closed for copied bools only;
  Mission/Item/Transfer recognizers remain test-only or post-RC planning surfaces unless a
  separate promotion gate changes scope.
- Weak-helper and GObjects evidence is internal offline input only. `0x595b7e0` supports
  target-set enumeration across current copied-core evidence, but not public GObjects,
  identity, lookup, `ResourceHandle`, mutation, or return override. Do not spend RC rounds
  on broad FName/GObjects discovery unless a new binary hash or contradictory evidence
  appears; current RC progress is accepted target-set evidence plus clean release slicing,
  not proving every FName/UFunction.
- Weak-helper polarity/caller-mode reports are candidate-only hygiene. Normalized semantic
  artifacts are consume accepted and promote blocked; they remain internal hook-frame
  policy input only.
- Weak-helper `caller_rows` remain internal static caller-mode hygiene only. Follow the
  static-binary-analysis skill for source/digest rules; do not promote `ResourceHandle`,
  lookup, lifecycle names, mutation, return override, or public SDK surface from them.
- Runtime dispatchers use process-lifetime storage, fail closed, snapshot registrations,
  handle same-dispatch unregister, and preserve cleanup waits. Structure/Inventory now wait
  across the other in-flight `GameplayPolicyEvent` family; Chat keeps non-blocking
  cross-family cleanup. Public `GameplayPolicyEvent` and `ChatMessageEvent` plugin
  callbacks are caught at the public callback bridge so C++ plugin exceptions do not
  escape back into dispatcher/hook code.
- RC API audit fixed owner-token capability snapshot blockers for `ChatMessageEvent`,
  `GameplayPolicyEvent`, and global ProcessEvent callback registration. Legacy public
  `CallProcessEvent` remains debug-gated and out of the RC public production path.
- Chat route observation is internal-only; see
  `docs/research/2026-05-29-chat-route-observer-plan.md`. The route observer is
  default-off, post-original, no SDK/ABI change, no plugin callback,
  `delivery_claim=none`, and no text/identity/pointer logging. Wrapper, stable posture,
  and CLI guardrails now own `enable-chat-route-observer` /
  `OBELISK_CHAT_ROUTE_OBSERVER_*`: stable launches scrub/fail closed, and
  `observer-debug` requires the scoped markers, exact supported SHA, and a positive limit.
  Route observations must not expand public delivery claims without copied plugin delivery
  logs.
- `docs/research/2026-05-29-rc-checkpoint-slicing-plan.md` is now historical recovery
  context for the broad pre-RC worktree, not active routing. The current tracked tree is
  past that recovery slice; use `git log --oneline -1` for the current head and continue
  with focused RC publication review and post-RC research notes instead of restarting the
  old slicing sequence.

## Priority Next Steps

- Keep the published RC public API frozen around `GameplayPolicyEvent`, minimal copied
  `ChatMessageEvent`, and descriptor helpers; continue post-RC work without redefining it.
- Current post-RC focus: move toward a general `v1.0` production core by reducing
  architecture debt, improving evidence tooling, and extracting UE4 reflection knowledge
  needed for safe copied module APIs. Do not jump straight to broad public SDKs.
- Start a durable v1.0 capability map for ArkApi-style plugin replacement: commands,
  permissions, players, tribes, dinos, items/inventory, structures, timers, admin, and
  external storage integrations. Separate core primitives from plugins that should be
  rebuilt later on top of those primitives.
- `ArkServerApi/AseApi` is names/behavior reference only; see
  `docs/research/2026-05-30-aseapi-reference-scan.md`. Do not copy offsets, vtables,
  layouts, `.lib` artifacts, MSVC conventions, direct field/native-call wrappers, or raw
  UE pointer APIs; rebuild through Obelisk reflection/ProcessEvent copied-data evidence.
- Treat the latest `ChatMessageEvent` beta window as closed and preserved. Copied-log
  evidence under `/servidor/ark/workspace-offline` validates plugin-facing delivery for
  `send_mode=0,1,2,3` with no raw text/identity leaks. Any future live chat evidence must
  be a newly approved, privacy-bounded window with analyzer and manifest gates.
- Keep second-source intake fail-closed: derive artifact-specific FName root, validate
  GObjects, regenerate snapshots, compare with readiness gaps enabled, and review the JSON
  plan before execution. Ready readiness reports must come from
  `gate_mode=second_source_promotion`, name at least one target set, and keep
  `promotion_ready=false`; consume-mode acceptance is layout evidence, not API/runtime
  promotion.
- Keep ResourceHandle promotion blocked and internal only. Use
  `docs/research/2026-05-30-post-rc-offline-resourcehandle-priority.md` as the current
  flag-policy/ResourceHandle pointer: consume-mode evidence is useful, promote-mode stays
  blocked, and the next meaningful step is a post-RC lifecycle/reuse experiment plan, not
  more broad scans.
- Treat Item return-only policy modeling as the best next value/risk target only inside
  the existing `GameplayPolicyEvent`/internal recognizer path. Keep it copied bools only;
  no `ItemId`, `AdditionalData`, `ResourceHandle`, return override, or public Inventory
  SDK. Freeze broader Inventory target sets for now; `CraftBlueprint`,
  `InventoryCustomFilter` arrays, and `ServerRequestInventoryUseItemWithTransform` stay
  out of scope.
- For the first non-UE-dependent v1 core service, prefer owner-token process-local timers
  before identity, permissions, and command routing. Timers still need append-only ABI,
  capability bits, zero-is-failure handles, owner cleanup on init failure/unload,
  idempotent unregister, and in-flight callback shutdown tests before implementation.
- InventoryReflection hardening now validates snapshot-backed class object indices,
  outer object indices, and per-property flags before copied bool dispatch. This is
  internal-only `GameplayPolicyEvent` hardening, not a public Inventory SDK or ABI change.
- Inventory hook dispatch builds/reuses copied payloads once, uses subscriber count only
  as a cheap mirror, and rebinding/cancel paths keep copied scalar spans owner-local. The
  strict RC `minimal-second-source-intake` redacted signature pack has complete coverage.
- Internal recognizer work stays test-only until promoted. The current recognizer order
  is Item return-only policy, Mission copied-bool observer, then Transfer `bAccept`; this
  is not RC public SDK/API scope and does not change the RC public API. It does not
  promote public module SDKs, callbacks, ABI, marker/env, runtime logs, hook wiring,
  mutation, return override, object identity, lookup, or `ResourceHandle`; keep detailed
  test coverage in dated research notes.
- Post-RC offline tooling added candidate-only UObject flag, weak-helper, and GObjects
  evidence builders plus gate tests. These tools are for consume-mode internal/offline
  indexing only. They do not promote public GObjects, lookup, identity, lifecycle,
  `ResourceHandle`, mutation, return override, or SDK surfaces.
- Keep redacted UFunction signatures, offline manifests, item compact intake,
  inventory-action compact intake, and BoolProperty gates candidate/layout-only unless the
  exact target set passes promote-mode artifact gates plus second-source/static evidence.
- Keep MissionReflection and ProcessEventItemReflection test-only: no hook wiring,
  dispatcher, public ABI, marker/env, runtime logs, or SDK surface.
- Route observer remains internal diagnostic evidence only; see the chat route observation
  fact above for gates and limits.
- No broad new core dump is needed for the published RC surfaces. Existing fixture-backed
  target sets cover exact RC UFunctions; safe claims remain target-set-scoped, not "all
  FNames" or "all UFunctions". For v1.0 research, prefer focused offline evidence:
  GObjects coherent-field-window hardening, Mission copied-bool observer planning, Item
  return-only policy modeling, and Transfer `bAccept` modeling before any live-server
  debug request.

## Agent Protocol

- Lead owns server safety; use `obelisk-github-research-workflow` for delegation, GitHub,
  and stale-agent cleanup.
- Sub-agent prompts need scoped objective, safety baseline, paths, skills, expert role, and expected decision; pass only needed skills and close completed agents.
