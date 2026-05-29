# Current Agent Handoff

Updated: 2026-05-29

This file is the active routing table for the next Obelisk leader or agent round. Keep
durable evidence in `docs/research/`, stable resume facts in `COMPACT_CONTEXT.md`, and old
detail in `HISTORY-*.md`.

## Active Objective

- Continue the core-first `v0.1.0-rc.1` path: Linux runtime, ProcessEvent hook
  infrastructure, plugin lifecycle, central install layout, `oBaseEvents`,
  `GameplayPolicyEvent`, `DescribeResourceKind`, and `DescribeGameplayPolicyEventKind`.
- Do not add public gameplay callback/module APIs beyond `GameplayPolicyEvent`, or public
  metadata helpers beyond `DescribeResourceKind` / `DescribeGameplayPolicyEventKind`,
  before the RC unless a new blocker proves the API is required.
- Treat module work as evidence and tooling above the core, not as the RC center.

## Hard Overrides

- GitHub work may be delegated only for an evidenced, stable milestone. Keep commits
  minimized; no routine push/checkpoint unless the milestone is useful, validated, and
  explicitly selected for GitHub publication.
- `arkserver` / Ragnarok is protected while users are active. `arkserver2` / TheIsland has
  standing debug approval; preserve evidence, restore posture, and shut it down afterward.
- Do not restart servers, edit `/servidor/ark`, change markers, run ReflectionScanner,
  attach ptrace/gcore, enable broad ProcessEvent tracing, or publish runtime observations
  outside the standing `arkserver2` debug scope or a separately approved exact run.
- Community/Discord updates are lead-only and only for major public modder-facing
  milestones, previews, migrations, or releases.

## Current Routing Facts

- ABI/API: `ObeliskApi` v1 stays append-only for `v0.1.0`; public gameplay SDK surfaces
  require accepted second-source evidence, copied-data ownership, and lifecycle gates.
- Promoted surface: `GameplayPolicyEvent` is the only public gameplay event, backed by
  `docs/public_gameplay_events.json` and
  `docs/research/2026-05-29-public-gameplay-event-readiness-audit.md`. Its payload is
  copied/redacted POD only; no UE pointers, raw params, identity, mutation, or return
  override are promoted.
- Promoted helper: `DescribeResourceKind` is metadata-only for known resource categories.
  It is not a `ResourceHandle`, lookup API, object identity, mutation surface, or
  cross-instance contract.
- Promoted helper: `DescribeGameplayPolicyEventKind` is metadata-only for promoted
  `GameplayPolicyEvent` kinds. It is event discovery for routing/config, not a module SDK,
  object identity, UE lookup, mutation path, or return-override API.
- RC chat surface: minimal copied `ChatMessageEvent` is now backed by the
  `chat-message-intake` target set with accepted second-source snapshot comparison.
  It remains limited to copied UTF-8 message bytes, send mode, copied-payload flag, and
  process-local sequence. An isolated `arkserver2` run proved runtime/plugin bootstrap,
  hook install, `oChatLogger` load, and callback registration; actual plugin-facing
  delivery from a real chat message is still pending before public milestone publication.
- ResourceHandle remains blocked. Use
  `docs/research/2026-05-29-resource-handle-revalidation-evaluator.md`,
  `docs/research/2026-05-29-resource-handle-nonzero-revalidation.md`,
  `docs/research/2026-05-29-uobject-flags-validity-blocker.md`, and the static/GObjects
  notes for evidence. The current nonzero revalidation pack clears serial-zero and
  coherent-window blockers for that input set, but public handles remain blocked on
  `uobject_flags_validity_semantics_unproven`; do not restate offsets or sample tables
  here.
- Runtime posture remains default-deny for global callbacks, public `CallProcessEvent`,
  ProcessEvent blocking, broad tracing, scanner/debug controls, and experimental observers.
- Internal bridges only: `core/StructureEventDispatcher` and
  `core/InventoryPolicyEventDispatcher` feed copied-scalar policy events. They do not
  promote public StructureEvents or Inventory SDKs.
- `plugins/oPolicyAudit` is an experimental first-party example for
  `GameplayPolicyEvent` descriptors and callbacks. It is outside the first release scope
  and builds only with `-DOBELISK_BUILD_EXPERIMENTAL_PLUGINS=ON`.
- Release readiness is core-first through `scripts/check_release_readiness.sh`. Local head
  has passed focused gates in prior slices, but a real publication decision must rerun the
  release gate without `--allow-dirty` at the selected checkpoint.
- Evidence details for accepted layout-only target sets live in:
  `docs/research/2026-05-29-minimal-second-source-readiness.md`,
  `docs/research/2026-05-29-dino-compact-second-source-readiness.md`,
  `docs/research/2026-05-29-buff-compact-second-source-result.md`, and
  `docs/research/2026-05-29-next-targetset-discovery.md`.
- Internal recognizers now include `ue/MissionReflection.*` for the
  `mission-compact-intake` targets. It is fixture-backed, SHA-gated, recognizes exact
  UFunction metadata and copied bool ranges only, and keeps object references plus
  `OutItemIDs` arrays recognition-only. It does not add a runtime hook, dispatcher, public
  Mission SDK, identity, mutation, or return override.
- Weak-helper static/decompiler evidence can now be archived with
  `scripts/build_weak_helper_provenance_bundle.py`. Bundles are archival and fail closed:
  missing or invalid source provenance keeps `promotion_ready=false`; do not treat them as
  public `ResourceHandle` promotion evidence.
- Follow `docs/research/2026-05-29-rc-checkpoint-slicing-plan.md` for checkpoint slicing;
  do not stage by path proximity. Ignored local build/pycache artifacts may exist and
  should remain unstaged.

## Checkpoint Groups If Commits Reopen

- RC API and public-scope docs: public ABI, copied policy event payload, resource metadata,
  SDK consumers, `docs/public_gameplay_events.json`, release docs, and public guardrails.
- Runtime observer safety: ProcessEvent hook infrastructure, exact-target internal
  observers, dispatcher tests, and runtime lifecycle tests.
- Script harness prelude: `scripts/run_script_tests.sh` and
  `scripts/test_run_script_tests.sh` before script-heavy validation.
- Offline evidence tooling: FName manifests, second-source intake, snapshot regeneration,
  static global evidence, ResourceHandle evaluator, protected-path guards, and matching
  tests.
- Research and handoff cleanup: dated research notes for evidence; handoff files only for
  immediate routing; skills only when a repeatable rule changes.

## Priority Next Steps

- Freeze the RC public API around `GameplayPolicyEvent`, the minimal copied
  `ChatMessageEvent`, `DescribeResourceKind`, and `DescribeGameplayPolicyEventKind`; keep
  public Inventory, StructureEvents, dino, buff, mission, tribe, transfer, richer chat,
  command, player, admin, mutation, return override, and public `CallProcessEvent`
  surfaces out of RC.
- Revalidate each checkpoint slice independently before any GitHub publication decision.
- Validate actual `ChatMessageEvent` delivery on `arkserver2` / TheIsland with explicit
  observer-debug markers, SHA, positive dispatch budget, `oChatLogger` allowlisted only for
  `arkserver2`, no raw chat text logging, copied log evidence, and immediate rollback to
  stable markers plus safe-disabled plugin config.
- Keep second-source intake fail-closed: derive artifact-specific FName root, validate
  GObjects, regenerate snapshots, compare with readiness gaps enabled, and review the JSON
  plan before execution.
- Reconcile the GObjects coherent field window before promoting beyond
  binary-hash-scoped research candidate status.
- Keep ResourceHandle blocked on current evaluator output and
  `uobject_flags_validity_semantics_unproven`. Broad core-scan rounds are low value unless
  a new artifact likely contains negative flag samples. Static weak-helper evidence now
  refines `0x100` as invalid and `0x4000` as strict-mode invalid, but public handles still
  need named lifetime semantics, more Ghidra helper/caller windows, and a fail-closed
  runtime policy.
- Inventory hardening now requires exact per-target `FunctionFlags` for
  `PrimalItem.CanUse` and `PrimalItem.AllowRemoteAddToInventory`, plus copied bool ranges
  only. Do not promote public Inventory SDK, identity, mutation, or return override.
- Runtime hardening has moved `EventManager`, `ChatEventDispatcher`,
  `StructureEventDispatcher`, and `InventoryPolicyEventDispatcher` singleton storage to
  process lifetime to avoid fallback teardown ordering hazards. Prefer explicit shutdown,
  and do not reintroduce destructible function-local STL registries on plugin cleanup
  paths.
- After MissionReflection, DinoReflection is the next clean internal module candidate.
  Buff remains useful for offline expansion; tribe should be split to a scalar subset
  before use; transfer remains high-risk/offline-only. Keep all out of public RC APIs.
- Keep ignored local artifacts, logs, build output, pycache, raw cores, dumps, generated
  reports, and server config unstaged.

## Agent Protocol

- Lead owns commits, pushes, handoff integration, and server-safety decisions.
- Apply `obelisk-github-research-workflow`; pass sub-agents only scoped objective,
  ownership, safety baseline, allowed paths, required skills, expert role, and expected decision.
- Pass only the skills required by scope; sub-agents follow the same minimal-skill rule.
- Before each supervised round, check for stale stand-by agents and close completed or
  obsolete agents before launching replacements.

Operator routing for active supervised rounds: when the operator requests the standing
six-agent split, keep two on Obelisk engineering/audit/development and four
on research/knowledge/reversing/dump work. Keep this out of default contributor docs and
sub-agent prompts unless it changes the concrete task.
