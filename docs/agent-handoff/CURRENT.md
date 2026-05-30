# Current Agent Handoff

Updated: 2026-05-30

This active routing table keeps only next-round facts; put durable evidence in
`docs/research/`, resume facts in `COMPACT_CONTEXT.md`, and old detail in `HISTORY-*.md`.

## Active Objective

- `v0.1.0-rc.1` is not published and must not be treated as closed on the current
  `HEAD`. A stale local tag may exist behind the current release-prep commits; any
  future publication requires a clean release gate on the intended ref and an exact
  tag/ref verification before tag push. Continue from the core-first RC baseline:
  Linux runtime, ProcessEvent hook infrastructure, plugin lifecycle, central install
  layout, `oBaseEvents`, `GameplayPolicyEvent`, minimal copied `ChatMessageEvent`,
  `DescribeResourceKind`, and `DescribeGameplayPolicyEventKind`.
- Do not add public gameplay callback/module APIs beyond `GameplayPolicyEvent` and the
  minimal copied `ChatMessageEvent`, or public metadata helpers beyond
  `DescribeResourceKind` / `DescribeGameplayPolicyEventKind`, before the RC unless a new
  blocker proves the API is required.
- Treat module work as evidence and tooling above the core, not as the RC center.

## Hard Overrides

- GitHub work may be delegated only for an evidenced, stable milestone. Keep commits
  minimized; no routine push/checkpoint unless selected for validated publication.
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
- Release readiness must rerun clean through `scripts/check_release_readiness.sh` without
  `--allow-dirty` before publication. The 2026-05-30 gate passed from a tracked-clean
  checkpoint, but it does not validate any stale local RC tag; publication still requires
  a clean rerun on the intended release ref and exact tag/ref verification.
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
- Follow `docs/research/2026-05-29-rc-checkpoint-slicing-plan.md` for checkpoint slicing;
  do not stage by path proximity. Ignored local build/pycache artifacts, logs, reports,
  cores, dumps, and server config should remain unstaged.

## Priority Next Steps

- Freeze the RC public API around `GameplayPolicyEvent`, the minimal copied
  `ChatMessageEvent`, `DescribeResourceKind`, and `DescribeGameplayPolicyEventKind`; keep
  standalone public Inventory SDK, public StructureEvents SDK, dino, buff, mission, tribe,
  transfer, richer chat, command, player, admin, mutation, return override, and public
  `CallProcessEvent` surfaces out of RC.
- Checkpoint order now starts with 0-pre staged-path helper, then 0a artifact-gate
  scanner/gate, then 0b release-gate options. Start with checkpoint 0-pre staged-path
  helper only; 0a is artifact-gate scanner/gate only; 0b is release-gate options only.
  The current worktree has no staged checkpoint; rerun focused tests and
  `scripts/check_staged_paths.py`; broad release/public guardrails run with the release
  docs/guardrails slice.
- Treat the latest `ChatMessageEvent` beta window as closed and preserved. Copied-log
  evidence under `/servidor/ark/workspace-offline` validates plugin-facing delivery for
  `send_mode=0,1,2,3` with no raw text/identity leaks. Any future live chat evidence must
  be a newly approved, privacy-bounded window with analyzer and manifest gates.
- Keep second-source intake fail-closed: derive artifact-specific FName root, validate
  GObjects, regenerate snapshots, compare with readiness gaps enabled, and review the JSON
  plan before execution.
- Keep ResourceHandle promotion blocked and post-RC/internal only. The 44 primary-core
  `0x4000` samples have been reconciled to `ParticleSystemComponent0` objects, so the next
  RC priority is not more broad ResourceHandle scanning. Continue with inventory copied-bool
  hardening and release slicing unless a focused lifecycle/reuse experiment is explicitly
  scoped later.
- Treat inventory as the best next value/risk hardening target only inside the existing
  `GameplayPolicyEvent` path: `PrimalItem.CanUse` and
  `PrimalItem.AllowRemoteAddToInventory` copied bools only; no `ItemId`, `AdditionalData`,
  `ResourceHandle`, or public Inventory SDK. Freeze the current Inventory target set for
  now; `InventoryCustomFilter` arrays and `ServerRequestInventoryUseItemWithTransform`
  stay out of scope.
- InventoryReflection hardening now validates snapshot-backed class object indices,
  outer object indices, and per-property flags before copied bool dispatch. This is
  internal-only `GameplayPolicyEvent` hardening, not a public Inventory SDK or ABI change.
- Inventory hook dispatch builds/reuses copied payloads once, uses subscriber count only
  as a cheap mirror, and rebinding/cancel paths keep copied scalar spans owner-local. The
  strict RC `minimal-second-source-intake` redacted signature pack has complete coverage.
- Post-RC internal recognizer work stays test-only. The post-RC internal recognizer order
  is Mission copied-bool observer, Item return-only policy, then Transfer `bAccept`; this
  is no RC public SDK/API promotion. It does not promote public module SDKs, callbacks,
  ABI, marker/env, runtime logs, hook wiring, mutation, return override, object identity,
  lookup, or `ResourceHandle`; keep detailed test coverage in dated research notes.
- Post-RC offline tooling checkpoint `8e76d3c` added candidate-only UObject flag,
  weak-helper, and GObjects evidence builders plus gate tests. These tools are for
  consume-mode internal/offline indexing only. They do not promote public GObjects,
  lookup, identity, lifecycle, `ResourceHandle`, mutation, return override, or SDK
  surfaces.
- Keep redacted UFunction signatures, offline manifests, item compact intake,
  inventory-action compact intake, and BoolProperty gates candidate/layout-only unless the
  exact target set passes promote-mode artifact gates plus second-source/static evidence.
- Keep MissionReflection and ProcessEventItemReflection test-only: no hook wiring,
  dispatcher, public ABI, server marker/env, runtime logs, or SDK surface.
- Route observer remains internal diagnostic evidence only; see the chat route observation
  fact above for gates and limits.
- No broad new core dump is needed for current RC surfaces. Existing fixture-backed target
  sets cover exact RC UFunctions; safe claims remain target-set-scoped, not "all FNames" or
  "all UFunctions". The prior focused extraction gap for `transfer-ufunction-intake` and
  `transfer-scriptstruct` now has accepted layout-only second-source evidence; the next
  transfer step is deciding whether any copied-scalar policy surface is worth modeling
  after RC, not broad live scanning.

## Agent Protocol

- Lead owns server-safety decisions; apply `obelisk-github-research-workflow` for
  delegation, GitHub ownership, and stale-agent cleanup.
- Sub-agent prompts still need scoped objective, safety baseline, allowed paths, required skills,
  expert role, and expected decision; pass only the skills needed for that scope and close
  completed sub-agents before the next round.
