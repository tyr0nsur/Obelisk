# Compact Context Snapshot

Updated: 2026-05-29

Use this file after conversation compaction or when resuming Obelisk from repository
state. Current routing table only: read `docs/agent-handoff/CURRENT.md` for active
priorities, and do not use history files as the active source of truth.

## Resume Protocol

1. Read this file, `docs/agent-handoff/CURRENT.md`, and the relevant subsystem skill.
2. Check `git status --short --ignored`.
3. Close completed or obsolete internal agents before starting a new round.
4. Continue one local critical-path task plus only scoped parallel sub-agents.

## Active Overrides

- Persistent leader objective lives outside skills and default sub-agent prompts.
- GitHub work may be delegated only for an evidenced, stable milestone; routine local
  rounds are not publication events.
- No server restart, `/servidor/ark` edit, marker change, ReflectionScanner, ptrace/gcore,
  broad ProcessEvent tracing, or runtime observation outside the standing debug scope or a
  separately approved exact run.
- `arkserver` / Ragnarok is protected while users are active. `arkserver2` / TheIsland has
  standing operator approval for Obelisk debug/development tests when needed; preserve
  evidence, restore stable posture, and shut it down afterward when no longer needed.
- Discord/community updates are for major public modder-facing milestones only.

## Stable Baseline

- Repo: `/home/flowcommunity-ark/Obelisk`
- Remote: `git@github.com:tyr0nsur/Obelisk.git`
- Central Obelisk root: `/servidor/ark/obelisk`
- Current dev line: `0.1.0-dev`; the release path should go through `0.1.0-rc.1` before
  stable.
- Stable plugin loading requires safe `OBELISK_INSTANCE_ID` plus real non-symlink plugin,
  config, log, and state roots.
- `ObeliskApi` v1 is append-only for `v0.1.0`; ABI v2 requires an explicit migration plan.
- EventManager owner cleanup is expected to wait for in-flight callbacks before plugin
  unload; tests cover filtered pre-ProcessEvent and post-ProcessEvent callback paths.
- Runtime posture is default-deny for global callbacks, public `CallProcessEvent`,
  ProcessEvent blocking, broad tracing, scanner/debug controls, and experimental observers.

## Product Baseline

- First stable release has one promoted gameplay SDK surface: `GameplayPolicyEvent`.
  Promotion scope and exclusions are recorded in
  `docs/research/2026-05-29-public-gameplay-event-readiness-audit.md`.
- `GameplayPolicyEvent` excludes mutation, raw UE pointer exposure, public
  callback-by-name APIs, public `StructureEvents`, public Inventory/Chat/etc. module APIs,
  HTTP/threads/file-reader plugin ingress, and lifecycle-unsafe plugins.
- `DescribeResourceKind` is a metadata-only v0.1 SDK helper for known resource categories.
  It returns copied POD descriptors with supported gameplay-policy event/field masks and
  explicit no-identity/no-lookup flags.
- `InventoryPolicyEventDispatcher` and `StructureEventDispatcher` are internal
  copied-scalar infrastructure only. They do not promote public Inventory or
  StructureEvents SDKs.
- Release scope wording separates stable filtered ProcessEvent callback infrastructure from
  experimental target-specific gameplay/module observers.

## Evidence Baseline

- ProcessEvent, FName, GObjects, UObject, UFunction, and unpromoted gameplay recognizer
  evidence is binary-scoped until the relevant second-source/static promotion gates pass.
- The accepted minimal second-source layout evidence is recorded in
  `docs/research/2026-05-29-minimal-second-source-readiness.md`. It supports the
  core-first release gate but does not promote GObjects, ResourceHandle, identity,
  mutation, return overrides, raw params, player/item/inventory identity, or public
  Inventory/StructureEvents SDK surfaces.
- Dino, buff, mission, and tribe compact intakes are layout evidence only. Use
  `docs/research/2026-05-29-dino-compact-second-source-readiness.md`,
  `docs/research/2026-05-29-buff-compact-second-source-result.md`, and
  `docs/research/2026-05-29-next-targetset-discovery.md` for exact target counts and
  blockers.
- `scripts/evaluate_resource_handle_revalidation.py` is the current offline redacted
  ResourceHandle readiness gate. Current evidence keeps public/post-callback handles
  blocked; see `docs/research/2026-05-29-resource-handle-revalidation-evaluator.md` and
  `docs/research/2026-05-29-uobject-flags-validity-blocker.md`.
- Static GObjects/FUObjectItem evidence remains research-candidate material. Details live
  in `docs/research/2026-05-29-static-gobjects-field-window-audit.md`,
  `docs/research/2026-05-29-static-gobjects-fuobjectitem-correlation.md`, and
  `docs/research/2026-05-29-static-gobjects-same-fuobjectarray.md`.
- If the reviewed binary/artifact FName root slot is already known, do not run broad
  reverse FName scans. Pass the root slot explicitly to evidence-pack, GObjects sampling,
  or snapshot regeneration tooling.

## Tooling Baseline

- Offline core evidence-pack outputs and release second-source readiness report paths must
  stay in `/servidor/ark/workspace-offline` or another approved offline root. Direct and
  symlinked live-server input/output paths are rejected.
- Raw core captures under `/servidor/ark/obelisk/dumps` are protected storage, not direct
  promotion inputs. Promotion tooling consumes hardlinked or copied offline artifacts.
- Second-source intake must derive artifact-specific FName root, validate GObjects,
  regenerate snapshots, and compare fail-closed with `--readiness-report
  --fail-on-readiness-gaps`.
- `scripts/check_release_readiness.sh --require-second-source-readiness` defaults to the
  UFunction `minimal-second-source-intake`; ScriptStruct promotion requires an explicit
  ScriptStruct target set.
- Static-only global evidence uses `scripts/build_static_global_promotion_evidence.py`;
  `promotion_gate.ready` remains false for static global candidates.

## Checkpoint Baseline

- Current RC direction is core-first: freeze `ObeliskApi` v1 around Linux runtime,
  ProcessEvent hook infrastructure, plugin lifecycle, central install layout,
  `oBaseEvents`, `GameplayPolicyEvent`, and `DescribeResourceKind`.
- The dirty/offline release gate has passed with the accepted minimal second-source root,
  but a real RC requires focused checkpoints and the same release gate without
  `--allow-dirty`.
- Use `docs/research/2026-05-29-rc-checkpoint-slicing-plan.md` for slicing. Handoff docs
  should be refreshed separately from runtime, release/public docs, offline tooling, and
  research-evidence slices.
- Do not promote post-RC work into the RC: ResourceHandle, GNames/GObjects promotion, full
  UE4 reflection, public Inventory SDK, public StructureEvents, chat/player/tribe/dino/
  buff/transfer APIs, mutation, return overrides, public `CallProcessEvent`, background
  worker plugins, operator lifecycle commands, and ScriptStruct/transfer promotion remain
  blocked unless a later focused gate changes scope.

## Agent Coordination

- Use direct supervised sub-agents only. Repo-local JSON queue coordination stays out of
  active prompts, handoff, and checkpoint planning.
- When running six sub-agents, keep two on Obelisk engineering/audit/development and the
  rest on research/knowledge/reversing/dump work; the lead supervises and integrates.
- Pass sub-agents only scoped objective, ownership, safety baseline, allowed paths,
  required skills, expert role, and expected decision.
- Pass only the skills required for each task; sub-agents should not receive the full skill
  set by default.
- The lead integrates sub-agent findings, owns commits/pushes, and closes stale or
  completed work before launching replacements.

## Canonical References

- `docs/agent-handoff/CURRENT.md`: active routing and immediate next steps.
- `docs/agent-handoff/HISTORY-2026-05-28-pre-current-compaction.md`: historical handoff
  detail before the active routing file was compacted.
- `docs/STATUS.md`: contributor-facing stability matrix.
- `docs/RELEASE.md`: release and second-source gates.
- `docs/VERSIONING.md`: version and ABI line rules.
- `docs/PLUGIN_ARCHITECTURE.md`: plugin lifecycle and promotion rules.
- `docs/research/README.md`: canonical research-note format.
- `docs/research/2026-05-29-rc-checkpoint-slicing-plan.md`: current dirty-tree checkpoint
  slicing plan.
- `docs/research/2026-05-29-public-gameplay-event-readiness-audit.md`: promoted
  `GameplayPolicyEvent` boundary.
- `docs/research/2026-05-29-minimal-second-source-readiness.md`: accepted minimal
  second-source UFunction layout evidence.
- `docs/research/2026-05-28-second-source-core-intake-runbook.md`: shortest offline
  second-source intake.
- `docs/research/2026-05-28-second-source-reversing-gap-matrix.md`: evidence gap matrix.
