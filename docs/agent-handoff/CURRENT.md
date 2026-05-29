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
- Release readiness is core-first through `scripts/check_release_readiness.sh`. The
  documented local gate evidence is the dirty/offline run with the accepted minimal
  second-source root; the current integration round is open and must rerun that gate
  without `--allow-dirty` before any publication decision.
- Evidence details for accepted layout-only target sets live in:
  `docs/research/2026-05-29-minimal-second-source-readiness.md`,
  `docs/research/2026-05-29-dino-compact-second-source-readiness.md`,
  `docs/research/2026-05-29-buff-compact-second-source-result.md`, and
  `docs/research/2026-05-29-next-targetset-discovery.md`.
- Current working tree may be dirty while the active integration round is being reviewed.
  Follow `docs/research/2026-05-29-rc-checkpoint-slicing-plan.md` for checkpoint slicing;
  do not stage by path proximity.

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

- Freeze the RC public API around `GameplayPolicyEvent`, `DescribeResourceKind`, and
  `DescribeGameplayPolicyEventKind`; keep
  public Inventory, StructureEvents, dino, buff, mission, tribe, transfer, chat, player,
  admin, mutation, return override, and public `CallProcessEvent` surfaces out of RC.
- Revalidate each checkpoint slice independently before any GitHub publication decision.
- Keep second-source intake fail-closed: derive artifact-specific FName root, validate
  GObjects, regenerate snapshots, compare with readiness gaps enabled, and review the JSON
  plan before execution.
- Reconcile the GObjects coherent field window before promoting beyond
  binary-hash-scoped research candidate status.
- Keep ResourceHandle blocked on current evaluator output and
  `uobject_flags_validity_semantics_unproven`.
- For utility after the core RC, the fastest safe path is internal copied-scalar inventory
  observation from the accepted minimal target set; if choosing a new module, mission is
  the cleanest next candidate. Tribe and transfer wait behind higher identity/payload risk.
- Keep ignored local artifacts, logs, build output, pycache, raw cores, dumps, generated
  reports, and server config unstaged.
- Preserve the current supervised-agent balance requested by the operator: two on Obelisk engineering/audit/development
  and four on research/knowledge/reversing/dump work.

## Agent Protocol

- Lead owns commits, pushes, handoff integration, and server-safety decisions.
- Apply `obelisk-github-research-workflow`; pass sub-agents only scoped objective,
  ownership, safety baseline, allowed paths, required skills, expert role, and expected decision.
- Pass only the skills required by scope; sub-agents follow the same minimal-skill rule.
- Before each supervised round, check for stale stand-by agents and close completed or
  obsolete agents before launching replacements.
