# Current Agent Handoff
This file is an active routing table only. Durable evidence belongs in
`docs/research/`, resume facts in `COMPACT_CONTEXT.md`, and old detail in
`HISTORY-*.md`. Historical recovery context is not active routing; use
`git log --oneline -1` for the checkpoint.

## Active Objective
- Published baseline: `v0.1.0-rc.2` is the current published core-first RC baseline after
  a clean release gate and exact tag/ref verification, not a production-stable `v1.0` or
  complete SDK claim. Stale tags must not be reused. RC public scope remains limited to
  promoted copied `GameplayPolicyEvent`, minimal copied `ChatMessageEvent`,
  `DescribeResourceKind`, and `DescribeGameplayPolicyEventKind`; core scope also includes
  process-local timers.
- Current post-RC focus: a complete `v1.0` public SDK contract for plugin authors. The
  complete v1 claim is blocked; do not use complete/full/production/stable SDK wording
  unless `scripts/check_public_sdk_v1_completion.py --json` allows it. The accepted RC
  UFunction second-source root remains release-scope evidence only.
- Active P0 spine:
  `docs/public_sdk_surfaces.json::v1_required_dependency_chain` is promoted-only for a
  complete SDK claim and currently ordered as `obelisk.player_identity.v1` ->
  `obelisk.permissions_admin.v1` -> `obelisk.command_chat_response_path.v1` ->
  `obelisk.commands_replies.v1`. Excluded/post-v1 results are scoped non-complete
  bookkeeping only.
- Current accounting: SDK completion remains fail-closed with complete-SDK progress
  `0/12`, P0 promoted count `0/4`, and `stable_claim_allowed=false`.
- Current identity status: repo-local lifecycle-anchor planning manifests are source-bound
  to the durable static report
  `docs/research/player-identity-planning-sources/players-lifecycle-anchor-static-report.json`
  SHA256 `03acc0573b680d3e0b19937b30cc73028c5fd833e3796fe839006941b8779cf4`.
  Default routing now reports `approved_runtime_evidence_missing`, with
  `promotion_ready=false`, `public_sdk_ready=false`, and `runtime_ready=false`. After
  accepted approved runtime evidence, the only allowed later route blocker is
  `identity_public_contract_gate_missing`, still locked and planning-only.

## Hard Overrides
- GitHub work may be delegated only for an evidenced, stable milestone. No tag or
  release-ref push has release-manager/lead authorization for this current-turn; this
  handoff does not authorize push, tag, release-ref updates, rebase, or routine publication.
- No server target has standing approval. Technical progress is only a reason to request a
  scoped run; it is not approval to change markers/env, start/restart/stop a server, run
  ReflectionScanner, ptrace/gcore, broad ProcessEvent tracing, runtime observers, or write
  under protected live paths.
- Request-pack/preflight/window-manifest/operator-receipt/sidecar readiness, planning
  acceptance, or route acceptance are operational preparation only; they do not authorize
  runtime work, public identity readiness, public ABI readiness, public SDK readiness, release readiness, command router,
  reply/send-chat ABI, marker/env changes, runtime capture, Discord, or v1 completion.
- The lead retains server-safety decisions.
- no Discord for internal rounds or agent status. Public modder-facing milestones and
  beta-test notices require explicit current-turn approval, the guarded helper, embed
  shape, and dry-run first. Use only `OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL` or
  `OBELISK_BETA_TEST_WEBHOOK_URL` by variable name. Always dry-run before any approved send.
  No Discord for routine validation, speculative reversing notes, private live-ops detail,
  raw player text, or secrets.
- ArkServerApi/AseApi and local `NextGenPlugins` clones are names and demand signals only:
  do not copy code, offsets, layouts, vtables, ABI assumptions, architecture, ergonomics,
  behavior, wrappers, raw UE pointer APIs, command parsers, return semantics, or source
  implementations; not architecture, behavior maps, porting targets, copying source, or
  implementations.
- Runtime posture is default-deny for filtered/global raw `ProcessEvent`, public
  `CallProcessEvent`, ProcessEvent blocking, broad tracing, scanner/debug controls, and
  observers unless an approved env+marker pair exists for a scoped debug window.
- `CallProcessEvent` remains an init-window debug escape hatch only: the current plugin
  owner is inside `ObeliskPlugin_Init`, has `OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT`,
  and the live env+marker gate is active. Post-init calls through captured API tables are
  unsupported; any future replacement must carry an owner token ABI.
- Plugin Hub is post-SDK-complete planning only. Archived Plugin Hub docs are boundaries,
  not current work. Plugin Hub examples, package intake, catalog publication, and seed
  review do not replace the active SDK blocker chain.
- Plugin Hub/field-window packaging blocker notes remain package-shape evidence only, not
  a `v1.0` completion marker. Plugin Hub seed examples, CMake package target presence, and
  package schema docs are not a `v1.0` SDK blocker, route shortcut, or completion signal;
  they do not gain priority, support tier, public SDK scope, or `v1.0` completion weight
  while complete-SDK blockers remain open. No Plugin Hub publication, intake
  prioritization, production module availability, or support-tier activation is in the
  current RC/post-RC SDK scope.
- ResourceHandle/public GObjects remain blocked: old flag-policy artifact is obsolete,
  durable rich-provenance refresh is preserved, Consume mode accepts it and promote mode
  stays blocked. Strict serial policy artifacts remain candidate-only; the first strict
  serial reuse/wraparound policy artifact is preserved, manifest consume mode accepts it
  and promote mode blocks it as candidate-only, and post-callback rejection contract is
  preserved as candidate-only. It does not unlock runtime negative samples, public lookup,
  object identity, public lookup safety, or public ResourceHandle readiness. The next
  strict ResourceHandle blocker is rejected runtime object samples plus runtime serial
  reuse/wraparound semantics; future-runtime-observation-plan requires an
  operator-approved live-ops brief names the exact debug target. Do not rerun broad FName,
  GObjects, or core scans for ResourceHandle. Do not replace this with another broad
  offline FName/GObjects scan.

## Current Routing Facts
- `scripts/check_command_permission_route_gate.py --json` is the canonical offline route
  posture check for identity/principal -> permissions/admin -> command response ->
  commands/replies. Passing it means planning-only alignment, not public ABI, runtime
  readiness, command router readiness, reply/send-chat ABI, or v1 completion.
- The default route currently reports `valid=true`, `planning_only=true`,
  `promotion_ready=false`, and current blocker `approved_runtime_evidence_missing`.
- `scripts/build_player_identity_planning_source_manifests.py --output-dir
  docs/research/player-identity-planning-sources` emits planning-only
  `players-identity-first-evidence.json`,
  `players-identity-lifecycle-anchor-candidates.json`, and
  `players-identity-principal-invalidation-policy.json`. Accepted lifecycle anchors
  `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout` are
  `static_accepted` and cite static report SHA256
  `03acc0573b680d3e0b19937b30cc73028c5fd833e3796fe839006941b8779cf4`. Runtime/server
  authorization remains false. Route-lock expectation:
  `approved_runtime_evidence_missing` keeps
  `blocked_until=[approved_runtime_principal_lifecycle_evidence,
  reviewed_identity_public_contract]`.
- Current recipe: `docs/research/2026-05-31-player-identity-offline-pack-preflight.md`
  remains the safe offline pack route. It requires a non-protected complete
  `obelisk.core-dump-evidence-pack.v1`, accepted `obelisk.reflection-inventory-pack.v1`,
  12/12 candidate fixtures, and accepted distinct second-source layout evidence from the
  vanilla-gdb core. Repo-local lifecycle-anchor and principal-invalidation manifests are
  consume-only planning inputs and source-bound; the default route consumes those
  repo-local fallbacks and reports `approved_runtime_evidence_missing`. The remaining
  blocker is approved runtime principal lifecycle evidence. Do not rerun completed admin
  snapshot, second-source layout, or lifecycle layout routes.
- Player identity first evidence uses the 12-target `players-identity-lifecycle-intake`
  planning set. `ShooterPlayerController.ServerListPlayers` and
  `ShooterPlayerController.ServerKickPlayer` are exact required admin targets in that set,
  but they are not accepted lifecycle anchors. Current accepted planning anchors for the
  bound route are `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout`.
- The next P0 runtime-side blocker is approved copied runtime principal lifecycle
  evidence. No approved copied runtime principal lifecycle evidence exists yet, and no
  runtime request is authorized by this file.
- Permissions/admin remains query-only planning until promoted copied identity/principal
  semantics exist. Command response and commands/replies remain blocked by identity and
  permissions/admin.
- Inventory copied signals remain the preferred side lane while P0 waits, but they do not
  promote inventory mutation, identity, lookup, ResourceHandle, or v1 completion.
  Current guardrails pin accepted inventory evidence to `minimal-second-source-intake`
  and `item-return-only-policy-slice`, keep `inventory-action-compact-intake` excluded,
  and reject positive raw identity/action-param claims such as `ItemId`, `ItemID1`,
  `InventoryComp`, `anActor`, and raw params. Item return-only public shape remains three
  copied `GameplayPolicyEvent` `ReturnValue` kinds only; no public Inventory SDK, Items
  SDK, identity, mutation, return override, or ResourceHandle.
- Structure census is explicitly `excluded`/non-counting for scoped v1 accounting;
  Structure build-policy remains offline/planning-only. Mission/Transfer/Dino/Tribe,
  ResourceHandle, economy/storage/operator ingress, and gameplay tick remain planning,
  post-v1, or blocked unless a future route explicitly promotes them with evidence.

## Priority Next Steps
- P0 identity: use `scripts/build_player_identity_planning_source_manifests.py` when a
  bound route proof is needed, then run
  `scripts/check_command_permission_route_gate_bound_identity_sources.py`. The default
  no-runtime-evidence proof should report `approved_runtime_evidence_missing`. If accepted
  approved runtime evidence is supplied to the route, confirm
  `identity_public_contract_gate_missing` and keep all unlock/readiness flags false.
- P0 runtime evidence: prepare, but do not run, a fresh live-ops brief for approved copied
  runtime principal lifecycle evidence. Request/window preparation is offline guardrail
  work only: request-pack acceptance keeps `server_operations_authorized=false`,
  `runtime_work_authorized=false`, public/runtime/promotion/v1 readiness false, and
  `next_blocker=operator_current_turn_runtime_window_approval_required`. Preserve checked
  `operator_live_ops_brief`, reviewed server binary path/SHA, exact env/marker
  boundaries, and sibling `window-request.json`, `observer-window.env`,
  `operator-approval-request.md`, completed `operator-approval-receipt.json`,
  `preflight-pre.json`, `preflight-post.json`, `window-manifest.env`, and copied log.
  Receipts count only for post-window replay; preflight sidecars keep false auth/readiness
  flags; preserve post-run checks, rollback delta, and no runtime/server authorization.
  Request packs are pre-window only: started/expired windows fail closed; receipt
  templates never count.
- P0 public contract: after approved runtime principal lifecycle evidence exists, the
  next blocker is `identity_public_contract_gate_missing`; review the player identity
  contract before permissions/admin, command response, or commands/replies ABI. The
  offline `privacy.identifier_redaction` evidence artifact at
  `docs/research/2026-06-02-player-identity-identifier-redaction-evidence.json` passes
  contract-review-only intake; it cannot promote identity, unlock public SDK/runtime/header
  readiness, or satisfy the complete SDK claim.
- Runtime/ABI hardening: cleanup failure skips `dlclose`, retains the plugin for retry,
  and does not repeat plugin shutdown. Copied-event `DestroyUserData` owner-cleanup
  failures are now retry-stable across chat, structure, inventory policy, item return, and
  player-principal dispatchers. owner-token process-local core timer explicit unregister
  remains distinct from gameplay/module timer, shared scheduler state, UE identity, and
  persistent handles; see
  `docs/research/2026-06-02-copied-event-destroy-userdata-retry-stability.md`.
- Side lanes: Mission copied-bool exact bool-tail evidence is `bool_field_size=1`,
  `bool_byte_offset=0`, `byte_mask=0x01`, `field_mask=0xff`, and `native_bool=false`;
  consume mode accepts and promote mode blocks. Mission/Transfer/Dino/Tribe/Buff leaf
  accounting is enforced by `check_mission_transfer_dino_tribe_v1_outcome_accounting.py`;
  it remains internal/not ready, with no public Mission SDK, public module SDK,
  ResourceHandle, identity, mutation, return override, runtime, ABI, public callbacks,
  v1 completion, and does not authorize Transfer runtime work.
- P0 guardrail: permissions/admin structured promotion now requires a matching
  player-identity promotion certificate for `obelisk.player_identity.v1`, chain position
  1, and a reviewed artifact hash before permissions/admin structured evidence can
  count. Missing, mismatched, or stale certificates keep permissions/admin non-counting.

## Agent Protocol
- Delegated sub-agents get only the scoped objective, safety baseline, allowed paths,
  required skills, expert role, expected decision, and edit permission needed for their
  task. Pass only the skills needed for that scope.
- Do not pass leader-only cadence, active-goal framing, community policy, or unrelated
  module history unless it changes the worker's concrete task.
- Sub-agents must not commit, amend, rebase, tag, push, update GitHub state, touch
  servers, send Discord updates, or broaden live-ops scope unless explicitly delegated for
  the current turn.
- Sub-agents are not alone in the codebase: do not revert unrelated changes; leave edits
  unstaged/uncommitted and report touched paths, validations, and risks.
- Lead handles delegation directly when asked; before finishing, record delegated scopes,
  skills, integrated findings, and pending findings so compaction does not erase them.
- Earlier identity route/evidence-hardening rounds made route validation accept
  `identity_public_contract_gate_missing` only as locked planning after approved runtime
  evidence, and route locks now dedupe
  `blocked_until=[reviewed_identity_public_contract]` for
  `identity_public_contract_gate_missing`; SDK completion requires identity contract
  structured evidence to carry the full blocker set, `blockers=[]`, and
  `resolved_inputs=[runtime.lifecycle_evidence]`; P0 keeps it non-counting.
- Latest round delegated tribe accounting, SDK completion bypass audit, runtime cleanup
  guardrails, and live-ops fixture isolation. Integrated result:
  `check_mission_transfer_dino_tribe_v1_outcome_accounting.py` now consumes the standalone
  Tribe scalar-boundary checker as `tribe_leaf_blocker_accounting` for candidate-only
  internal blocker accounting. It preserves all missing leaf-family semantics and keeps
  tribe, umbrella, public SDK, runtime, promotion, and v1 completion flags false. The
  research index now lists `docs/research/2026-06-03-tribe-scalar-boundary-design.md`.
  SDK completion audit found no bypass: the tribe side lane remains non-counting and SDK
  JSON remains blocked with SDK `0/12`, P0 `0/4`, `stable_claim_allowed=false`.
  PluginManager guardrails additionally assert retry state preserves owner token,
  shutdown function, `shutdownCalled=true`, and retry logging before retention.
  Approved-runtime evidence fixture audit made no edits and confirmed per-test offline
  temp roots under `/servidor/ark/workspace-offline` leave no new top-level residue. Route
  JSON remains valid/planning-only at `approved_runtime_evidence_missing`. No runtime/server
  op. Agents closed.
- Latest round delegated live-ops request/window audit, identity public-contract audit,
  bound identity route audit, and SDK completion wording/accounting audit. Integrated
  result: public-contract gap/readiness reports now keep `current_blocker` and
  `next_blocker` at `approved_runtime_evidence_missing` until approved runtime evidence is
  accepted; after accepted runtime evidence they may report only locked planning blocker
  `identity_public_contract_gate_missing`, with public/header/runtime/promotion/v1 flags
  false. Bound identity route checks now forward explicit approved runtime evidence,
  verify exact canonical paths for transient bound lifecycle/principal manifests, and
  preserve durable static lifecycle `source_artifact_ids` instead of replacing them with
  first-evidence IDs. Added
  `docs/research/2026-06-03-p0-runtime-evidence-gate-snapshot.md`. Live-ops and SDK
  audits made no edits and found no request/window or release-wording bypass. Route JSON
  remains valid/planning-only at `approved_runtime_evidence_missing`; SDK JSON remains
  blocked with SDK `0/12`, P0 `0/4`, `stable_claim_allowed=false`. No runtime/server op.
  Agents closed.
- Latest round delegated permissions/admin dependency, command response/replies readiness,
  approved-runtime replay, and release/SDK wording audits. Integrated result:
  permissions/admin player-identity promotion certificates now require
  `reviewed_artifact_hash` to match the reviewed player-identity surface record hash,
  preventing unrelated reviewed hashes from satisfying the dependency. Command response
  and commands/replies direct readiness now reject `identity_public_contract_gate_missing`
  as a blocker alias; that blocker is identity-stage only, while downstream command gates
  stay at `approved_runtime_evidence_missing` until identity and permissions/admin are
  promoted. Command response/replies wording scans now catch public SDK, release
  readiness, and v1 completion overclaims; commands/replies no longer treats
  `release_guardrails` as a negative context. Approved-runtime replay/window sidecar
  scans now catch compound `public_runtime_v1_ready`/runtime-v1-ready claims. Release/SDK
  audit made no edits. Route JSON remains valid/planning-only at
  `approved_runtime_evidence_missing`; SDK JSON remains blocked with SDK `0/12`, P0
  `0/4`, `stable_claim_allowed=false`. No runtime/server op. Agents closed.
- Latest round delegated route-gate, SDK completion, approved-runtime/window replay, and
  downstream P0 contract hardening. Integrated result: route gate now carries structured
  upstream identity public/runtime/source-claim findings into `critical_path_phase` and
  rejects request/window/receipt/planning/placeholder evidence source claims. After
  accepted runtime evidence, the parent identity route may lock at
  `identity_public_contract_gate_missing`, but downstream permissions/admin, command
  response, and commands/replies children still receive and must report the canonical
  `approved_runtime_evidence_missing` blocker until identity and permissions/admin are
  promoted. SDK completion now detects structured aliases such as `public_sdk.ready`,
  `runtime.ready`, `stable_claim.allowed`, and `counts_toward.v1_completion`, and treats
  named nested report/readiness/summary/result/accounting objects as independent claim
  contexts. Runtime window/evidence-bundle reports now explicitly emit false
  non-authorization/readiness flags: `server_operations_authorized`,
  `runtime_work_authorized`, `promotion_ready`, `public_header_allowed`,
  `public_sdk_ready`, `public_abi_ready`, `v1_completion_ready`, and `runtime_ready`.
  Downstream wording scans now also catch complete/full/production/stable SDK,
  `v1.0 stable`, and release-readiness overclaims while preserving negative
  stable-release-contract contexts. Validation passed: route gate 46, downstream 135,
  window-manifest 70, evidence-bundle 45, focused SDK alias tests 3, py_compile, route
  JSON valid/planning-only, SDK JSON blocked by design with SDK `0/12`, P0 `0/4`,
  `stable_claim_allowed=false`, full SDK completion suite 211, and `git diff --check`.
  No runtime/server operation. Agents closed.
- Latest round delegated request-pack hardening, approved-runtime replay/bundle binding,
  SDK completion nested evidence scanning, and ResourceHandle serial/post-callback
  boundary audit. Integrated result: generated player-principal lifecycle request packs
  now include explicit false `authorization_flags`, `stable_claim_allowed=false`, and
  `request_pack_counts_as_approved_runtime_evidence=false`; `observer-window.env` includes
  request-pack-only no-claim comments; request-pack checking rejects future
  `prepared_at_utc`, future operator receipts, and `--post-window-replay` before the
  approved window has completed. Evidence bundles now require `--window-manifest` to
  resolve to the exact sibling `window-manifest.env` beside the copied `Obelisk.log`
  before output creation. Approved-evidence env parsing ignores no-claim comment lines
  while still enforcing exact env key order/set. SDK completion now rejects nested
  public/runtime/v1 overclaims inside command response and commands/replies structured
  readiness reports. ResourceHandle serial and post-callback builders plus public
  readiness checker now reject camel/snake/hyphen public/runtime/v1 alias overclaims
  while keeping artifacts candidate-only. Offline request-pack sample in `/tmp` validated
  as `ready=true` with `next_blocker=operator_current_turn_runtime_window_approval_required`
  and all auth/readiness flags false. Validation passed: request-pack prepare 13,
  request-pack check 54, evidence-bundle 46, approved-evidence/manifest 80,
  ResourceHandle 33, consolidated touched suite 159, route JSON valid/planning-only, SDK
  JSON blocked by design with SDK `0/12`, P0 `0/4`, `stable_claim_allowed=false`,
  py_compile, full SDK completion suite 213, and `git diff --check`. No runtime/server
  operation. Agents closed.
- Latest round delegated approved-evidence timestamp hardening, downstream P0 overclaim
  scanning, SDK completion alias scanning, and ResourceHandle side-lane guardrails. Lead
  additionally hardened the player-principal planning smoke against nested positive
  runtime/public/v1 aliases and integrated window-manifest timestamp parsing so invalid
  semantic UTC values produce blockers instead of tracebacks. Integrated result:
  approved runtime evidence consume checks now reject future completed receipts, future
  preflight `checked_at_utc`, future post-window windows, and bad approved/capture/
  rollback ordering. Window-manifest replay handles semantically invalid timestamps
  fail-closed. Permissions/admin, command response, and commands/replies scans no longer
  let blocker-like containers hide unnegated public/runtime readiness claims. SDK
  completion scans now catch `public_abi_available`, `runtime_v1_ready`,
  `complete_sdk_allowed`, `production_ready`, and `stable_v1_sdk`, and a detached
  `blocked.` sentence no longer suppresses a later affirmative public SDK claim.
  ResourceHandle guards now catch `resource_lookup`/`publicResourceLookupReady` and
  `stable_claim_allowed` without promoting ResourceHandle. Validation passed:
  approved-evidence/manifest 84, window-manifest 70, downstream route/permissions/
  command/replies 184, ResourceHandle 33, planning smoke 6, route JSON
  valid/planning-only, SDK JSON blocked by design with SDK `0/12`, P0 `0/4`,
  `stable_claim_allowed=false`, py_compile, full SDK completion suite 213, and
  `git diff --check`. No runtime/server operation. Agents closed.
- Latest round delegated evidence-bundle preflight hardening, player identity public
  contract readiness audit, offline research hygiene, and SDK completion accounting.
  Lead locally hardened the bound identity route wrapper so an
  `--approved-runtime-principal-lifecycle-evidence-manifest` must pass the approved
  runtime evidence checker before it is forwarded or allowed to change the expected
  blocker to `identity_public_contract_gate_missing`; arbitrary files now keep
  `approved_runtime_evidence_missing` and add `approved_runtime_evidence_not_accepted`.
  Evidence-bundle preflight now requires approved-offline readable sidecars before
  invoking request-pack/operator-receipt/approved-runtime checkers. Public-contract
  readiness now tracks `accepted_for_contract_review` and rejects nested public/header/
  capability/SDK/ABI/v1/downstream overclaims in approved-runtime reports before
  resolving `runtime.lifecycle_evidence`. SDK completion now normalizes camelCase source
  marker keys such as `sourceKind`, `sourceTargetSets`, and `evidenceKinds`, and rejects
  request-pack/preflight/live-ops-sidecar/approved-runtime/identity-contract markers as
  promotion evidence. Research hygiene clarified the P0 snapshot commit baseline.
  Validation passed: bound identity route 9, evidence-bundle 48, player identity
  readiness/gap 82, route gate 46, full SDK completion suite 214, route JSON
  valid/planning-only, SDK JSON blocked by design with SDK `0/12`, P0 `0/4`,
  `stable_claim_allowed=false`, py_compile, and `git diff --check`. No runtime/server
  operation. Agents closed.
- Latest round delegated approved-runtime direct-consumer audit, player identity public
  contract alias hardening, SDK completion source-marker hardening, and ResourceHandle
  side-lane non-promotion audit. Lead locally hardened the direct command/permission
  route gate so `--approved-runtime-principal-lifecycle-evidence-manifest` changes the
  identity route lock only when the source checker exposes an accepted approved-runtime
  diagnosis (`ready`, `approved_runtime_evidence_present`, `runtime_evidence_ready`, and
  empty `remaining_blockers`). Arbitrary/unaccepted manifests keep the canonical
  `approved_runtime_evidence_missing` lock and are not forwarded to the public-contract
  gap checker. Player identity first-evidence readiness similarly forwards approved
  runtime evidence to contract-gap intake only after the approved-runtime diagnosis is
  ready. Public-contract readiness/gap scans now normalize camelCase, hyphenated, spaced,
  and snake_case readiness/list aliases in nested approved-runtime reports. SDK completion
  rejects camel/hyphen/nested `approvedRuntime` and `identityContract` source/evidence
  markers without treating required semantic terms as promotion evidence. ResourceHandle
  zero-serial negative-sample metadata now rejects nested public/runtime/lookup/SDK
  overclaims while preserving candidate-only status. Added
  `docs/research/2026-06-03-direct-route-approved-runtime-binding.md`. Validation passed:
  route gate 48, player identity first-evidence 39, public-contract readiness/gap 83,
  combined route/identity/contract suite 170, ResourceHandle/offline gate focus 73, full
  SDK completion suite 214 (`-f`), route JSON valid/planning-only at
  `approved_runtime_evidence_missing`, SDK JSON blocked by design with SDK `0/12`, P0
  `0/4`, `stable_claim_allowed=false`, py_compile, and `git diff --check`. No
  runtime/server operation. Agents closed.
- Latest round delegated request/window replay audit, downstream P0 dependency audit, SDK
  source-marker/accounting audit, and offline reflection side-lane audit. Integrated
  result: post-window replay now rejects future `approved_window_end_utc`,
  `actual_capture_end_utc`, and `rollback_end_utc`; SDK completion rejects
  `runtime_lifecycle_evidence` and `runtime_principal_lifecycle_evidence` source markers
  as non-promotional; promoted P0 executed-test artifacts now require the command/argv to
  contain a surface-specific execution marker, so unrelated green suites cannot satisfy
  `executed_test_report`; tribe side-lane research now points at the current
  `check_tribe_scalar_boundary_readiness.py` checker while preserving candidate-only,
  no-public/no-runtime/no-ResourceHandle/no-v1 semantics. Current recipe wording now
  explicitly records that repo-local lifecycle-anchor and principal-invalidation manifests
  are consume-only planning inputs and source-bound, and that the default route consumes
  those repo-local fallbacks while reporting `approved_runtime_evidence_missing`. Added
  `docs/research/2026-06-03-executed-test-artifact-command-binding.md`. Validation
  passed: SDK completion 215, public SDK guardrails 191, request/window/approved-evidence/
  bundle 242, downstream P0/route/bound-route 195, side-lane JSON checks, route JSON
  valid/planning-only at `approved_runtime_evidence_missing`, SDK JSON blocked by design
  with SDK `0/12`, P0 `0/4`, `stable_claim_allowed=false`, py_compile, and
  `git diff --check`. No runtime/server operation. Agents closed.
