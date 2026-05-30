# Compact Context Snapshot

Updated: 2026-05-29

Use this file after conversation compaction or when resuming Obelisk from repository
state. Current routing table only: read `docs/agent-handoff/CURRENT.md` for active
priorities, and do not use history files as the active source of truth.

## Resume Protocol

1. Read this file, `docs/agent-handoff/CURRENT.md`, and the relevant subsystem skill.
2. Check `git status --short --ignored`.
3. Close completed or obsolete internal agents before starting a new round.
4. Continue direct supervised work with scoped sub-agent prompts when delegation is used.

## Active Overrides

- GitHub work may be delegated only for an evidenced, stable milestone; routine local
  rounds are not publication events.
- No server restart/start/stop, `/servidor/ark` edit, marker change, ReflectionScanner,
  ptrace/gcore, broad ProcessEvent tracing, or runtime observation unless the current
  operator turn names an approved debug/beta scope or separately approved exact run.
  Technical progress alone is not approval to restart; request the exact run only when
  new runtime logs are genuinely needed after a concrete offline/code advance.
- No standing operator approval for Obelisk debug/development or beta tests applies to
  starts, restarts, marker edits, or runtime observation. Any server-backed run requires a
  live-ops brief for that turn naming the target, feature gates, marker/env changes,
  restart/start window, notice path when players are involved, evidence capture, and
  rollback.
- Community updates are for major public modder-facing milestones only; beta-test
  activation notices are separate operational live-ops messages.

## Stable Baseline

- Repo: `/home/flowcommunity-ark/Obelisk`
- Remote: `git@github.com:tyr0nsur/Obelisk.git`
- Central Obelisk root: `/servidor/ark/obelisk`
- Current release baseline: local tag `v0.1.0-rc.1` exists as the small core-first RC
  checkpoint. Post-RC work stays internal/offline unless a separate promotion gate
  changes scope.
- Stable plugin loading requires safe `OBELISK_INSTANCE_ID` plus real non-symlink plugin,
  config, log, and state roots.
- `ObeliskApi` v1 is append-only for `v0.1.0`; ABI v2 requires an explicit migration plan.
- EventManager owner cleanup is expected to wait for in-flight callbacks before plugin
  unload; tests cover debug-gated filtered pre-ProcessEvent and post-ProcessEvent callback
  paths.
- Runtime posture is default-deny for filtered raw `ProcessEvent` callbacks, global
  callbacks, public `CallProcessEvent`, ProcessEvent blocking, broad tracing,
  scanner/debug controls, and experimental observers.
  Filtered raw callbacks expose borrowed UE pointers/raw params and require
  `OBELISK_ALLOW_FILTERED_PROCESS_EVENT_CALLBACKS=1` plus
  `allow-filtered-process-event-callbacks`; copied `GameplayPolicyEvent` and
  `ChatMessageEvent` are the RC plugin paths.
  `CallProcessEvent` remains an ABI v1 compatibility/debug escape hatch only: it is not
  owner-scoped, so the live env+marker gate is enforceable but the caller plugin's
  captured capability snapshot is not. Keep it out of the RC production path; a future
  replacement must carry an owner token and test cross-manager capability snapshots.

## Product Baseline

- Current RC public scope has one promoted gameplay policy callback surface:
  `GameplayPolicyEvent`. Promotion scope and exclusions are recorded in
  `docs/research/2026-05-29-public-gameplay-event-readiness-audit.md`. The separate
  minimal `ChatMessageEvent` RC surface is a copied chat notification contract, not a
  gameplay policy/module SDK.
- `GameplayPolicyEvent` excludes mutation, raw UE pointer exposure, public
  callback-by-name APIs, public `StructureEvents`, public Inventory/etc. module APIs,
  richer chat APIs beyond minimal `ChatMessageEvent`, HTTP/threads/file-reader plugin
  ingress, and lifecycle-unsafe plugins.
- `DescribeResourceKind` is a metadata-only v0.1 SDK helper for known resource categories.
  It returns copied POD descriptors with supported gameplay-policy event/field masks and
  explicit no-identity/no-lookup flags.
- `DescribeGameplayPolicyEventKind` is a metadata-only v0.1 SDK helper for promoted
  `GameplayPolicyEvent` kinds. It returns copied POD descriptors for routing/config, not
  UE lookup, identity, mutation, or return override.
- `InventoryPolicyEventDispatcher` and `StructureEventDispatcher` are internal
  copied-scalar infrastructure only. They do not promote public Inventory or
  StructureEvents SDKs.
- Inventory copied-policy dispatch uses build-once payload reuse after budget reservation
  and a cheap atomic live-subscriber mirror; lifecycle cleanup must still use dispatcher
  depth/deferred-destroy state, not the subscriber mirror. Copied inventory payloads
  rebind scalar spans on copy/move so dispatch-time values own their storage, and failed
  budget reservation clears stale payloads.
- Public `GameplayPolicyEvent` and `ChatMessageEvent` plugin callbacks are caught at the
  bridge to prevent C++ plugin exceptions from escaping into dispatcher/hook code.
- Release scope wording separates copied RC plugin events from debug-gated raw
  ProcessEvent callback infrastructure and experimental target-specific gameplay/module
  observers.

## Evidence Baseline

- ProcessEvent, FName, GObjects, UObject, UFunction, and unpromoted gameplay recognizer
  evidence is binary-scoped until the relevant second-source/static promotion gates pass.
- The accepted minimal second-source layout evidence is recorded in
  `docs/research/2026-05-29-minimal-second-source-readiness.md`. It supports the
  core-first release gate but does not promote GObjects, ResourceHandle, identity,
  mutation, return overrides, raw params, player/item/inventory identity, or public
  Inventory/StructureEvents SDK surfaces.
  Current validator refresh:
  `/servidor/ark/workspace-offline/minimal-second-source-intake-refresh-20260529T124340Z`
  passed offline artifact consume gates for both the readiness report and optional
  redacted signatures. Treat it as layout-only evidence with `promotion_ready=false`.
- Minimal copied `ChatMessageEvent` has accepted `chat-message-intake` second-source
  evidence and approved beta delivery evidence for known send modes. Keep future route
  observations `delivery_claim=none` unless a new controlled copied-plugin delivery window
  is approved and preserved.
- Historical server prep note: `/servidor/ark/obelisk` and `oChatLogger` were installed
  for an `arkserver` beta validation. Do not treat that snapshot as current authorization
  or current posture. Reconfirm process, markers, plugins, and operator approval before
  any new runtime observation; rollback plans must remove beta launch/config changes,
  restore stable markers such as `disable-plugins`, restart only in an approved window,
  and validate stable posture afterward.
- The only near-term player-backed test candidate is minimal `ChatMessageEvent` delivery.
  Inventory/mission/item/dino/buff/tribe/transfer/admin surfaces stay internal/offline
  until their copied-data, callback lifecycle, ABI, and runtime gate requirements are
  satisfied.
- Dino, buff, mission, and tribe compact intakes are layout evidence only. Use
  `docs/research/2026-05-29-dino-compact-second-source-readiness.md`,
  `docs/research/2026-05-29-buff-compact-second-source-result.md`, and
  `docs/research/2026-05-29-next-targetset-discovery.md` for exact target counts and
  blockers.
- `ue/MissionReflection.*` is an internal fixture-backed recognizer for
  `mission-compact-intake`: copied bool ranges only, object refs and `OutItemIDs` arrays
  recognition-only, no hook/runtime dispatcher/public Mission SDK.
  The internal readiness note is
  `docs/research/2026-05-29-mission-reflection-internal-readiness.md`. A local
  test-only `ProcessEventMissionReflection` helper scaffold exists, but it has no live
  hook path, dispatcher, public ABI, server marker/env, or runtime logs. Any next Mission
  slice needs a separate runtime-observation/lifecycle review.
- ResourceHandle remains post-RC/internal and blocked by
  `uobject_flags_validity_semantics_unproven`; see the ResourceHandle/UObject flag
  research notes for evidence. Do not reopen broad FName/GObjects discovery or create
  another semantic-correlation artifact unless new evidence contradicts the current
  consume-accepted/promote-blocked semantic artifact. A primary Ragnarok copied-core scan
  produced 44 coherent `0x4000` rejected-object candidate samples and is preserved under
  `/home/flowcommunity-ark/obelisk-artifacts/resource-handle-serial-scan-primary-20260530T000000Z/`;
  consume mode is accepted and promote mode remains blocked. A focused `GObjects`
  reconciliation resolved all 44 as `ParticleSystemComponent0` under `Text_Actor` /
  `Text_Actor_C` and is preserved under
  `/home/flowcommunity-ark/obelisk-artifacts/resource-handle-flag4000-reconciliation-primary-20260530T000000Z/`.
  This is internal lifecycle/blocker evidence only, not public `ResourceHandle`, lookup,
  identity, mutation, return override, or lifetime promotion.
- Static GObjects/FUObjectItem evidence is internal offline input only. `0x595b7e0`
  supports target-set enumeration across current copied-core evidence, but not public
  GObjects, identity, lookup, `ResourceHandle`, mutation, or return override. Evidence:
  `docs/research/2026-05-29-gobjects-fuobjectarray-durable-pack.md`,
  `docs/research/2026-05-29-gobjects-second-core-reconciliation.md`, and
  `docs/research/2026-05-29-gobjects-cross-manifest-comparison.md`.
- Redacted UFunction signatures, offline manifests, item compact intake, inventory-action
  compact intake, and BoolProperty mask/native markers are candidate/layout hygiene only.
  They are useful for planning and fixture comparison, not runtime safety, public SDKs,
  identity, mutation, return override, or `ResourceHandle`. Use the dated research notes
  such as `docs/research/2026-05-29-item-compact-second-source-readiness.md`,
  `docs/research/2026-05-29-item-return-only-policy-bridge-plan.md`,
  `docs/research/2026-05-29-inventory-action-redacted-signature-readiness.md`, and
  `/servidor/ark/workspace-offline/redacted-ufunction-signatures-rollup-20260529T101249Z`
  instead of copying artifact detail into handoff.
  The strict RC `minimal-second-source-intake` redacted signature pack with complete
  target-set coverage is preserved at
  `/home/flowcommunity-ark/obelisk-artifacts/rc-minimal-redacted-signatures-strict-20260530T000000Z/`;
  consume mode is accepted and promote mode remains candidate-only blocked.
- The historical static-negative UObject flag policy pack is obsolete. The regenerated
  strict-pattern artifact is accepted for consume-mode indexing only; it is not
  ResourceHandle promotion evidence, and promote mode remains blocked by
  candidate-only/non-claims.
- Post-RC offline tooling checkpoint `8e76d3c` added candidate-only UObject flag,
  weak-helper, and GObjects evidence builders. They are consume-mode internal/offline
  indexing tools only and do not promote public GObjects, lookup, identity, lifecycle,
  `ResourceHandle`, mutation, return override, or SDK surfaces.
- `scripts/build_uobject_flag_sample_report.py` produces
  `obelisk.uobject-flag-sample-report.v1` from the transition-matrix plus regenerated
  policy artifacts. Each `--input` must be paired with a `--consume-gate` in the same
  order, and the output embeds redacted consume-gate summaries for the source artifacts,
  not raw gate JSON. The offline artifact gate accepts it only in consume mode and blocks
  promote mode; use the script tests and gate output as the authoritative reference.
- Weak-helper caller-mode artifacts are consume-mode research hygiene and promote-mode
  blocked. They refine helper evidence while keeping `ResourceHandle`, UE lifecycle names,
  post-callback lookup, mutation, and return override blocked; summarize durable policy in
  `docs/research/2026-05-29-resource-handle-flag-policy-candidate.md` and
  `docs/research/2026-05-29-uobject-flags-validity-blocker.md`.
- `weak-helper-static-polarity-report.v1` has a candidate-only builder/gate contract for
  provenance-gated consume-mode indexing. It narrows internal flag-policy research only;
  promote mode remains blocked and it does not clear `ResourceHandle`, lifecycle-name,
  lookup, mutation, or return-override blockers.
- If the reviewed binary/artifact FName root slot is already known, do not run broad
  reverse FName scans. Pass the root slot explicitly to evidence-pack, GObjects sampling,
  or snapshot regeneration tooling.

## Tooling Baseline

- Offline core evidence-pack outputs and release second-source readiness report paths must
  stay in `/servidor/ark/workspace-offline` or another operator-approved offline root
  that resolves outside protected live-server paths. Direct and symlink-resolved
  live-server input/output paths are rejected; `/servidor/ark/workspace-offline` is the
  explicit exception.
- `scripts/validate_offline_artifact_gate.py` rejects unsupported manifest schemas; add
  schema-specific validation before accepting any new offline artifact schema.
- `obelisk.resource-handle-serial-scan.v1` is consume-only internal evidence. It must be
  `candidate_blocked` with `internal_offline_scan_candidate`, verified redacted
  provenance, required `scan_limit` matching provenance, coherent
  `consume_gate_expectation`, and real copied-core hash checks; it is always blocked in
  promote mode.
- Raw core captures under `/servidor/ark/obelisk/dumps` are protected storage, not direct
  promotion inputs. Promotion tooling consumes hardlinked or copied offline artifacts.
- Second-source intake must derive artifact-specific FName root, validate GObjects,
  regenerate snapshots, and compare fail-closed with `--readiness-report
  --fail-on-readiness-gaps`.
- `scripts/check_release_readiness.sh --require-second-source-readiness` defaults to the
  public RC UFunction target sets: `minimal-second-source-intake`,
  `structure-observer-intake`, and `chat-message-intake`. ScriptStruct promotion requires
  an explicit ScriptStruct target set.
- `scripts/assemble_rc_ufunction_second_source_root.py` assembles those three accepted
  UFunction roots into one release-gate root. It copies existing sanitized snapshots only
  and does not regenerate evidence. It produced
  `/tmp/obelisk-rc-ufunction-second-source-root` with 9 unique snapshots from the current
  accepted minimal/structure/chat roots, and each target set passed
  `compare_reflection_snapshots.py --readiness-report --fail-on-readiness-gaps` against
  that assembled root. The helper manifest is path-redacted; do not preserve or publish
  older `/tmp` manifests that contain absolute source roots.
- Static-only global evidence uses `scripts/build_static_global_promotion_evidence.py`;
  `promotion_gate.ready` remains false for static global candidates.
- Weak-helper evidence archives use `scripts/build_weak_helper_provenance_bundle.py`.
  Missing or invalid source sidecars are preserved as blockers and keep
  `promotion_ready=false`; the current bundle is valid archival material but blocked by
  missing original source sidecars.

## Checkpoint Baseline

- Current RC direction is core-first: freeze `ObeliskApi` v1 around Linux runtime,
  ProcessEvent hook infrastructure, plugin lifecycle, central install layout,
  `oBaseEvents`, `GameplayPolicyEvent`, minimal copied `ChatMessageEvent`,
  `DescribeResourceKind`, and `DescribeGameplayPolicyEventKind`.
- `plugins/oPolicyAudit` is experimental and excluded from the default build/release
  scope unless `OBELISK_BUILD_EXPERIMENTAL_PLUGINS=ON`.
- Historical dirty/offline release-gate runs are smoke evidence only. A real RC requires
  focused checkpoints and the release gate without `--allow-dirty`.
- Use `docs/research/2026-05-29-rc-checkpoint-slicing-plan.md` for slicing. Handoff docs
  should be refreshed separately from runtime, release/public docs, offline tooling, and
  research-evidence slices.
- Checkpoint 0-pre is first: staged-path helper only. Checkpoint 0a is artifact-gate
  scanner/gate only, currently isolated to `scripts/scan_resource_handle_serials.py`,
  `scripts/test_scan_resource_handle_serials.py`,
  `scripts/validate_offline_artifact_gate.py`, and
  `scripts/test_validate_offline_artifact_gate.py`. Checkpoint 0b is release-gate
  options only (`scripts/check_release_readiness.sh` and its option tests). These
  checkpoints require exact staged path validation before publication; broad
  release/public guardrails run with the release docs/guardrails slice because they also read handoff, skills, and
  post-RC routing. Keep runtime/API implementation changes out of both prelude
  checkpoints.
- Weak-helper caller-mode manifests now require embedded verified provenance for
  `ghidra_stdout`, `r2_windows`, and `direct_call_counts`; consume acceptance remains
  internal static evidence only and promote mode stays blocked.
- ResourceHandle remains post-RC/internal only. The copied/offline core blocker artifact
  now yields 44 coherent `0x4000` rejected-object candidates, reconciled as
  `ParticleSystemComponent0` under `Text_Actor` / `Text_Actor_C`; this is internal
  blocker evidence only. Avoid more broad ResourceHandle scanning for the RC unless a
  later focused lifecycle/reuse plan explicitly changes scope.
- `obelisk.resource-handle-serial-scan.v1` is now gated for that exact internal candidate
  shape: consume requires coherent `flag_rejection_candidate_samples`, a required
  `binary_sha256`, verified `core_sha256` bytes, required `scan_limit` matching
  provenance, unique candidate indices below `scan_limit`, and `core_path` under the
  approved offline workspace; promote remains blocked. Use
  `scripts/scan_resource_handle_serials.py --gate-ready` only for post-RC/internal
  consume-mode scans, not as a public RC gate.
- Do not promote post-RC work into the RC: ResourceHandle, GNames/GObjects promotion, full
  UE4 reflection, public Inventory SDK, public StructureEvents, chat APIs beyond minimal
  copied `ChatMessageEvent`, player/tribe/dino/buff/transfer APIs, mutation, return overrides,
  public `CallProcessEvent`, background worker plugins, operator lifecycle commands, and
  ScriptStruct/transfer promotion remain blocked unless a later focused gate changes
  scope.
- If post-RC internal recognizer work resumes, keep it test-only. For plugin/resource
  usefulness, preserve Item return-only policy evidence first; keep Mission copied-bool
  lifecycle review as the better-covered parallel/next recognizer; keep Transfer
  `bAccept` fixture-only after those. None of these promote public Mission/Items/Transfer
  SDKs, public callbacks, ABI, markers/env, runtime logs, hook wiring, mutation, return
  override, object identity, lookup, or `ResourceHandle`. Start from the dated research
  notes, not public API docs, until a separate promotion gate approves runtime
  observation, dispatcher lifecycle, ABI, and SDK policy.
- Runtime dispatcher hardening: hook-called Chat, Structure, and Inventory dispatchers
  must fail closed on setup/internal errors instead of rethrowing into `ProcessEvent`.
  Chat dispatch snapshots registration ids, skips callbacks removed during the same
  dispatch, invokes callbacks outside dispatcher mutexes, and defers `DestroyUserData`
  until outermost dispatch completion.
  Gameplay callback-scope detection is shared across gameplay families so callback-
  initiated cross-family unregister cannot deadlock. Structure/Inventory unregister waits
  for the other in-flight `GameplayPolicyEvent` family before returning; Chat remains
  non-blocking for cross-family cleanup. Non-callback owner/plugin cleanup still waits for
  in-flight dispatch and deferred `DestroyUserData` cleanup before returning.
- RC API audit found and fixed owner-token capability-snapshot blockers for
  `ChatMessageEvent`, `GameplayPolicyEvent`, and global ProcessEvent callback
  registration. Public gameplay/chat callback bridges also catch plugin exceptions and
  continue dispatch; `PluginManagerTests` covers these regressions.

## Agent Coordination

- Use `obelisk-github-research-workflow` as the canonical coordination rule set. Repo-local
  JSON queue coordination stays out of active prompts, handoff, and checkpoint planning.
- sub-agent prompts still need scoped objective, safety baseline, allowed paths, required skills,
  expert role, and expected decision; pass only the skills needed for that scope and close
  completed sub-agents before the next round.

## Canonical References

- `docs/agent-handoff/CURRENT.md`: active routing and immediate next steps.
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

Archive reference, not active source of truth:

- `docs/agent-handoff/HISTORY-2026-05-28-pre-current-compaction.md`: historical handoff
  detail before the active routing file was compacted; use only to resolve old context.
