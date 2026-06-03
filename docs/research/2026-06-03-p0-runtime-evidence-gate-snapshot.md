# P0 Runtime Evidence Gate Snapshot

## Purpose

Record the current P0 SDK route after the tribe/accounting checkpoint so future
agents do not confuse internal side-lanes with progress on the complete v1 SDK
claim.

## Baseline

- Original checkpoint commit: `279b16c Integrate tribe scalar accounting evidence`
- Hygiene-audit starting baseline: `b46906d`
- Date: 2026-06-03
- Runtime/server operation: none
- Publication operation: none

## Commands

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_player_principal_lifecycle_planning_blocker_smoke.py --json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json
```

## Observed State

`check_command_permission_route_gate.py --json` reports:

- `valid=true`
- `planning_only=true`
- `current_route_blocker=approved_runtime_evidence_missing`
- `next_route_action=produce_approved_runtime_principal_lifecycle_evidence`
- `counts_toward_v1_completion=false`
- `public_sdk_ready=false`
- `runtime_ready=false`
- `promotion_ready=false`
- route lock `locked=true`
- `blocked_until=[approved_runtime_principal_lifecycle_evidence, reviewed_identity_public_contract]`

`check_player_principal_lifecycle_planning_blocker_smoke.py --json` reports:

- `ready=true`
- `next_blocker=approved_runtime_evidence_missing`
- `approved_runtime_evidence_present=false`
- `server_operations_authorized=false`
- `runtime_work_authorized=false`
- `public_sdk_ready=false`
- `runtime_ready=false`
- `promotion_ready=false`
- `v1_completion_ready=false`

`check_public_sdk_v1_completion.py --json` exits blocked by design and reports:

- `ready=false`
- `status=blocked`
- `stable_claim_allowed=false`
- `stable_release_contract_claim_allowed=false`
- complete SDK progress `0/12`
- P0 dependency chain progress `0/4`
- route blocker `approved_runtime_evidence_missing`
- recommended next action: produce approved copied runtime principal lifecycle
  evidence before any public identity, permissions/admin, command response, or
  commands/replies ABI.

## Non-Claims

- This snapshot is not runtime evidence.
- This snapshot does not authorize marker changes, env changes, server starts,
  server restarts, runtime observation, ReflectionScanner, ptrace/gcore, broad
  tracing, Discord, publication, or GitHub state changes.
- Request packs, preflight sidecars, receipt templates, route acceptance, and
  planning smoke acceptance remain offline guardrails only.
- Tribe scalar/accounting, inventory copied signals, structure census, mission
  copied bools, and other side-lanes remain non-counting for the P0 dependency
  chain and complete SDK claim.

## Next Action

The next true P0 blocker remains approved copied runtime principal lifecycle
evidence under a current-turn operator-approved live-ops window. After that
the public identity contract can be reviewed, then permissions/admin, command
response path, and commands/replies can proceed in order.

## 2026-06-03 Later Guardrail Update

Later supervised hardening did not change the P0 count: SDK remains `0/12`,
the dependency chain remains `0/4`, and `stable_claim_allowed=false`.

Additional offline guardrails now bind downstream command response and
commands/replies readiness reports to their source artifacts through SHA-256
hashes, scope the request-checker test fake `git` to subprocesses, reject
fractional UTC timestamps in runtime window manifests, and refresh Buff
side-lane accounting so the current Buff blocker is the missing dedicated
Buff consume/readiness checker rather than stale compact bool-tail repair.

These updates reduce false positives only. They are not approved runtime
evidence and do not authorize SDK completion, runtime work, server operations,
publication, or stable-release wording.
After approved runtime evidence is accepted, the route may advance only to locked
planning blocker
`identity_public_contract_gate_missing`, with all public SDK, public ABI,
runtime, promotion, permissions/admin, command response, commands/replies, and
v1 completion flags still false until the separate public contract gate is
reviewed.

## Same-Day Route Hardening

The next supervised audit round closed two offline route-accounting gaps without
changing the default blocker:

- `check_player_identity_public_contract_gap_report.py` now keeps both
  `current_blocker` and `next_blocker` at `approved_runtime_evidence_missing`
  until approved runtime evidence is actually accepted. It no longer advertises
  `identity_public_contract_gate_missing` as the next blocker while runtime
  evidence is missing.
- `check_player_identity_public_contract_readiness.py` now treats
  `runtime.lifecycle_evidence` as resolved only when the approved runtime
  evidence input is accepted, while all public/header/runtime/promotion/v1 flags
  remain false.
- `bind_player_identity_planning_sources.py` preserves durable lifecycle
  `artifact_identity.source_artifact_ids` when a lifecycle manifest already has
  accepted static anchor provenance. Binding still updates per-anchor snapshot
  SHA evidence from the selected first-evidence source; it does not replace the
  static source IDs with first-evidence placeholder IDs.
- `check_command_permission_route_gate_bound_identity_sources.py` now verifies
  that route-gate canonical manifest paths point to the exact transient bound
  lifecycle/principal manifests it generated, not only that the child report says
  `matched=true`.
- The bound route wrapper can forward an explicit approved runtime principal
  lifecycle evidence manifest; with that input the only allowed blocker is still
  locked planning-only `identity_public_contract_gate_missing`.

These changes are guardrails only. They do not create approved runtime evidence,
do not authorize runtime work, do not promote public identity, and do not move
SDK progress above `0/12` or P0 above `0/4`.

## Downstream P0 Gate Snapshot

The follow-up downstream audit sampled the three public-readiness gates that
depend on player identity:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_permissions_admin_public_readiness.py \
  --query-failclosed-artifact docs/permissions_admin_query_failclosed_contract.json \
  --json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_chat_response_public_readiness.py --json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_commands_replies_public_readiness.py --json
```

Observed results:

- Permissions/admin: `valid=true`, `accepted_for_planning=true`,
  `planning_only=true`, `current_route_blocker=approved_runtime_evidence_missing`,
  `dependency_chain_locked=true`, and `counts_toward_public_sdk=false`,
  `counts_toward_runtime=false`, `counts_toward_v1_completion=false`.
- Command chat response: `valid=true`, `accepted_for_planning=true`,
  `planning_only=true`, `current_route_blocker=approved_runtime_evidence_missing`,
  `dependency_chain_locked=true`, and all public/runtime/v1 accounting flags false.
- Commands/replies standalone: `valid=false`, `accepted_for_planning=false`, and
  `blockers=[response_path_report_required]` when run without the composed
  response-path report supplied by the canonical route gate. This standalone
  failure is expected and prevents commands/replies from bypassing the response
  path dependency.

The canonical route gate remains the source of truth for composing these checks;
standalone downstream acceptance does not imply public SDK, runtime, command
router, reply/send-chat ABI, or v1 completion readiness.

## Downstream P0 Hardening

The next supervised downstream round closed three additional bypass classes:

- Permissions/admin promotion certificates now require
  `reviewed_artifact_hash == reviewed_surface_record_sha256` after the reviewed
  surface record hash is checked against the promoted player-identity surface.
  A non-zero but unrelated reviewed artifact hash no longer satisfies the
  player-identity dependency certificate.
- Command chat response and commands/replies direct public-readiness reports no
  longer accept `identity_public_contract_gate_missing` as a route-blocker alias.
  That blocker is valid for the identity stage after approved runtime evidence,
  but command response/replies remain downstream of both promoted identity and
  permissions/admin; their direct gates now accept only the canonical
  pre-runtime blocker `approved_runtime_evidence_missing` and report
  `current_route_blocker_mismatch` otherwise.
- Command response/replies overclaim scans now catch explicit `public SDK`,
  `release readiness`, and `v1 completion` wording; `release_guardrails` no
  longer hides positive public/v1 readiness claims in the commands/replies gate.
- Approved runtime principal lifecycle evidence and window-manifest sidecar
  scanners now catch compound positive keys/text such as
  `public_runtime_v1_ready` and `runtime v1 ready`.

These are offline guardrails only. They keep P0 downstream gates from treating
identity-stage progress, request/window artifacts, or wording sidecars as
permissions/admin, response-path, replies, public SDK, runtime, or v1 completion
promotion evidence.

## P0 Claim-Surface Hardening

The next supervised 4-agent round closed additional claim-surface gaps without
changing the runtime blocker:

- The route gate now imports structured public/runtime/source-claim findings
  from the upstream player-identity first-evidence checker into
  `critical_path_phase` and rejects request-pack, window-manifest, operator
  receipt, planning artifact/manifest/source, placeholder evidence, and similar
  source fields when they are presented as approved runtime identity evidence.
- After accepted approved runtime evidence, the parent identity route may move
  only to locked planning blocker `identity_public_contract_gate_missing`.
  Downstream permissions/admin, command response, and commands/replies direct
  gates still receive and must report `approved_runtime_evidence_missing`; they
  must not inherit the identity-stage contract blocker as their own readiness
  alias.
- SDK completion claim scanning now recognizes structured aliases such as
  `public_sdk.ready`, `runtime.ready`, `stable_claim.allowed`, and
  `counts_toward.v1_completion`. Named nested report/readiness/summary/result/
  accounting objects start their own claim context, so a parent blocker cannot
  hide a child public/runtime/v1 overclaim.
- Runtime window-manifest and evidence-bundle reports now explicitly emit false
  non-authorization/readiness flags for server operations, runtime work,
  promotion, public header, public SDK, public ABI, v1 completion, and runtime
  readiness.
- Downstream P0 readiness scans now catch complete/full/production/stable SDK,
  `v1.0 stable`, and release-readiness wording overclaims while preserving
  negative stable-release-contract contexts.

Validation stayed offline-only: route-gate tests 46, downstream permissions/
admin and command response/replies tests 135, window-manifest tests 70,
evidence-bundle tests 45, focused SDK structured-alias tests 3, full SDK
completion suite 211, py_compile, route JSON valid/planning-only, SDK JSON
blocked by design, and `git diff --check`. The stable
state remains `current_route_blocker=approved_runtime_evidence_missing`, SDK
progress `0/12`, P0 progress `0/4`, and `stable_claim_allowed=false`.

## Bound Evidence Source Hardening

The next supervised 4-agent round closed additional source-boundary gaps without
running a server or changing the route blocker:

- The bound identity route wrapper now validates any supplied
  `--approved-runtime-principal-lifecycle-evidence-manifest` with the approved
  runtime evidence checker before forwarding it to the route gate. An arbitrary
  file path no longer moves the expected blocker to
  `identity_public_contract_gate_missing`; rejected input stays at
  `approved_runtime_evidence_missing` and records
  `approved_runtime_evidence_not_accepted`.
- Evidence-bundle preflight now requires approved-offline readable sidecars
  before invoking request-pack, operator-receipt, or approved-runtime manifest
  checkers, so unapproved existing files are not read or treated as checked.
- Player identity public-contract readiness now records
  `accepted_for_contract_review` for approved runtime evidence and rejects
  nested public/header/capability/SDK/ABI/v1/downstream overclaims in the
  approved-runtime report before resolving `runtime.lifecycle_evidence`.
- SDK completion accounting normalizes camelCase source-marker keys such as
  `sourceKind`, `sourceTargetSets`, and `evidenceKinds`, and rejects
  `request_pack`, `preflight`, `live_ops_sidecar`,
  `approved_runtime_principal_lifecycle_evidence`, and
  `identity_public_contract_gate_missing` as promotion evidence markers.
- Research hygiene clarified that this note's original checkpoint commit is
  historical and that later hardening rounds have newer local checkpoints.

Validated offline: bound identity route 9, evidence-bundle 48, player identity
public-contract readiness/gap 82, route gate 46, full SDK completion suite 214,
route JSON valid/planning-only, SDK JSON blocked by design, py_compile, and
`git diff --check`. The stable state remains
`current_route_blocker=approved_runtime_evidence_missing`, SDK progress `0/12`,
P0 progress `0/4`, and `stable_claim_allowed=false`.

## Request Pack And Replay Binding Hardening

The next supervised 4-agent round prepared the runtime-evidence path further
without running a server or changing the blocker:

- Player-principal lifecycle request packs now carry explicit false
  `authorization_flags`, including `server_operations_authorized=false`,
  `runtime_work_authorized=false`,
  `request_pack_counts_as_approved_runtime_evidence=false`,
  `publication_authorized=false`, `stable_claim_allowed=false`, and false
  public/runtime/v1 readiness flags.
- Generated `observer-window.env` now includes request-pack-only comments. The
  request checker ignores those comments for env parsing; approved-evidence
  replay also ignores comment lines while still enforcing exact env key order
  and values for real env entries.
- Request-pack validation rejects future `prepared_at_utc`, future completed
  operator receipts, and `--post-window-replay` before the approved window has
  completed. A fresh `/tmp` request-pack sample validated as `ready=true` only
  for pre-window planning, with
  `next_blocker=operator_current_turn_runtime_window_approval_required` and all
  authorization/readiness flags false.
- Evidence-bundle generation now requires the supplied `--window-manifest` to
  resolve to the exact sibling `window-manifest.env` beside the copied
  `Obelisk.log` before output creation.
- SDK completion now rejects nested public/runtime/v1 overclaims inside command
  response and commands/replies structured readiness reports.
- ResourceHandle serial-policy, post-callback contract, and public-readiness
  checkers reject camel-case, snake-case, and hyphenated aliases that claim
  ResourceHandle/object identity/object lookup/runtime/v1 promotion while
  preserving candidate-only status.

Validated offline: request-pack prepare 13, request-pack check 54,
evidence-bundle 46, approved-evidence/manifest 80, ResourceHandle 33,
consolidated touched suite 159, route JSON valid/planning-only, SDK JSON
blocked by design, py_compile, full SDK completion suite 213, and `git diff --check`.
The stable state remains `current_route_blocker=approved_runtime_evidence_missing`, SDK
progress `0/12`, P0 progress `0/4`, and `stable_claim_allowed=false`.

## Evidence And Claim-Scan Hardening

The next supervised 4-agent round tightened the same P0 boundary without running
a server or changing the blocker:

- Approved runtime evidence consume checks reject future completed receipts,
  future preflight `checked_at_utc`, future post-window approved/capture/
  rollback windows, and bad approved/capture/rollback ordering.
- Window-manifest replay now treats semantically invalid UTC values as blockers
  instead of allowing a traceback during replay.
- Player-principal planning smoke rejects nested positive runtime/public/v1
  alias claims while remaining planning-only and non-authorizing.
- Permissions/admin, command response, and commands/replies readiness scans no
  longer let blocker-like containers such as `blockers`, `block_reasons`, or
  `why_blocked` hide unnegated public/runtime readiness claims.
- SDK completion scanning catches additional structured aliases:
  `public_abi_available`, `runtime_v1_ready`, `complete_sdk_allowed`,
  `production_ready`, and `stable_v1_sdk`; detached negators no longer suppress
  later affirmative public SDK claims.
- ResourceHandle side-lane guardrails catch `resource_lookup`,
  `publicResourceLookupReady`, and `stable_claim_allowed` without promoting
  ResourceHandle, object lookup, runtime object samples, serial reuse/
  wraparound safety, or SDK completion.

Validated offline: approved-evidence/manifest 84, window-manifest 70,
downstream route/permissions/command/replies 184, ResourceHandle 33, planning
smoke 6, route JSON valid/planning-only, SDK JSON blocked by design,
py_compile, full SDK completion suite 213, and `git diff --check`. The stable
state remains `current_route_blocker=approved_runtime_evidence_missing`, SDK
progress `0/12`, P0 progress `0/4`, and `stable_claim_allowed=false`.

## Route Readiness And Release Wording Hardening

The next supervised 4-agent round closed offline claim/evidence gaps without
changing the P0 route blocker:

- The route gate only forwards an approved-runtime evidence manifest after an
  explicit accepted diagnosis; generated `argv` metadata is excluded from text
  claim scans while structured route-ready/public-runtime aliases still block.
- Permissions/admin readiness now emits explicit false route-readiness fields
  and rejects `route_ready`, `public_route_ready`, and related aliases as
  overclaims.
- SDK completion revalidates the nested command response readiness report
  schema and child source-artifact SHA-256 bindings before commands/replies
  structured evidence can count.
- Release-statement guardrails now reject broad `release-grade` and
  `production-grade` SDK/API/support claims while allowing negated boundary
  wording.
- Mission/Transfer/Dino/Tribe side-lane accounting rejects generic ready,
  public-runtime, and v1 completion overclaims in release statements and
  public-contract fields while remaining candidate-only.

Validated offline: route gate 50, permissions/admin readiness 59, command
response/replies readiness 79, public SDK guardrails 193, mission/transfer/
dino/tribe accounting 23, full SDK completion suite 219, route JSON
valid/planning-only, release-statement scope check, SDK JSON blocked by design,
py_compile, and `git diff --check`. The stable state remains
`current_route_blocker=approved_runtime_evidence_missing`, SDK progress `0/12`,
P0 progress `0/4`, and `stable_claim_allowed=false`.

## Runtime Preflight, ABI Candidate, And Dependency Certificate Hardening

The next supervised 4-agent round closed additional offline replay and P0
dependency-accounting gaps without running a server or changing the blocker:

- Runtime request/preflight sidecars now explicitly keep request-pack,
  preflight, completed-receipt, and approved-runtime-evidence counters false.
  Window-manifest replay requires those false counters, and evidence-bundle
  preflight reports approved runtime evidence present only after the
  approved-evidence checker accepts it.
- Player identity public ABI preflight, public-contract gap/readiness, and the
  owner-token SDK consumer contract reject nested or alias public header,
  capability, callback ABI, public SDK, runtime, promotion, and v1 claims while
  staying candidate-only.
- SDK completion now requires hash-bound promoted dependency certificates for
  `obelisk.permissions_admin.v1` before `obelisk.command_chat_response_path.v1`
  can consume it, and for `obelisk.command_chat_response_path.v1` before
  `obelisk.commands_replies.v1` can consume it. Certificates must match active
  promoted surface-record SHA-256 values; loose inline downstream evidence does
  not substitute.
- Mission/Transfer/Dino/Tribe/Buff side-lane accounting rejects module,
  callback, descriptor, capability, C ABI, `ResourceHandle`, and v1-accounted
  aliases while remaining candidate-only and non-counting.

Validated offline: full SDK completion suite 221, identity ABI/contract/
owner-token suite 96, runtime/preflight suite 204, side-lane accounting 25,
preflight shell, route JSON valid/planning-only, SDK JSON blocked by design,
py_compile, and `git diff --check`. The stable state remains
`current_route_blocker=approved_runtime_evidence_missing`, SDK progress `0/12`,
P0 progress `0/4`, and `stable_claim_allowed=false`.

## Runtime Evidence And Identity Text-Overclaim Hardening

The next supervised 4-agent round closed recovery/context and offline
overclaim gaps without changing the P0 blocker:

- Runtime replay audit confirmed request packs, preflight sidecars, window
  manifests, completed receipts, and stale approved-bundle sidecars still do
  not count as approved runtime evidence unless the approved runtime evidence
  checker accepts the bound post-window manifest/log set.
- Player identity public ABI preflight, public-contract readiness/gap, and
  owner-token SDK consumer checks now reject recursive positive text or
  source-key claims for public headers, capability bits, callback ABI, public
  SDK/runtime/promotion/v1 readiness, player identity promotion, and stable or
  complete SDK wording while preserving negated non-claim contexts.
- Player-principal planning smoke rejects camelCase positive aliases and
  explicit positive text claims such as approved runtime evidence present or
  SDK complete while remaining planning-only and non-authorizing.
- Historical lifecycle/admin target-gap research notes now state that old
  FName/GObjects/core/admin and lifecycle-layout routes are superseded for the
  current blocker and must not be restarted without new reviewed evidence.
- SDK completion accounting audit found no count-through bypass: promoted P0
  rows still require promoted manifest status, promotion evidence, required
  semantic terms, structured evidence/certificates, matching release-statement
  promoted outcome, dependency order, and route-gate satisfaction.

Validated offline: identity checker suite 374, focused identity ABI/contract/
owner-token/gap suite 100, planning smoke 8, route JSON valid/planning-only,
planning-smoke JSON ready/non-authorizing, SDK JSON blocked by design,
py_compile, and `git diff --check`. The stable state remains
`current_route_blocker=approved_runtime_evidence_missing`, SDK progress `0/12`,
P0 progress `0/4`, and `stable_claim_allowed=false`.

## Downstream Route And Accounting Alias Hardening

The next supervised 4-agent round closed a downstream P0 structured-alias gap
without changing the active blocker:

- Permissions/admin, command response, and commands/replies readiness now reject
  nested or secondary `counts_toward_public_sdk`, `counts_toward_runtime`,
  `counts_toward_v1_completion`, `public_or_runtime_accounting_allowed`,
  route-ready variants, `stable_claim_allowed`, and v1-completion aliases.
- Permissions/admin additionally rejects nested runtime authorization and server
  operation aliases such as `runtime_work_authorized` and
  `server_operations_authorized`.
- Runtime evidence audit confirmed request packs, receipts, preflight/window
  sidecars, copied logs, aliases, and stale bundle checks still do not count as
  approved runtime evidence.
- SDK completion route-gate current-blocker flakiness was not reproduced across
  focused, file-order, reverse-order, discovery, and full SDK completion runs.
- Research hygiene found the current index and recent identity notes consistently
  route to `approved_runtime_evidence_missing` and do not direct broad FName/
  GObjects/core scans, admin snapshot regeneration, or runtime/live probes.

Validated offline: downstream route/readiness suite 200, full SDK completion
suite 221, runtime/preflight suites 256 by delegated audit, route JSON
valid/planning-only, SDK JSON blocked by design, and `git diff --check`. The
stable state remains `current_route_blocker=approved_runtime_evidence_missing`,
SDK progress `0/12`, P0 progress `0/4`, and `stable_claim_allowed=false`.

## Command Bridge, SDK Release Wording, And Side-Lane Alias Hardening

The next supervised 4-agent round closed additional nested/secondary alias
gaps without changing the active P0 blocker:

- Runtime evidence/preflight audit found no remaining scoped path where
  request packs, preflight/window sidecars, completed receipts, copied logs,
  aliases, or stale bundle checks count as approved runtime evidence.
- Permissions/admin query fail-closed now rejects nested route readiness,
  public/runtime accounting, runtime authorization, server operation, and
  runtime approval aliases.
- Command principal authz response bridge and copied response intent planning/
  lifecycle checks reject route-ready, command-router, reply/send-chat, public
  ABI/header/SDK/runtime, stable SDK, and v1 completion/accounting aliases.
  Negated boundary wording remains accepted.
- SDK completion rejects additional secondary report aliases such as SDK/API/
  support ready, stable ready, production grade, release grade, and v1 stable
  SDK variants, plus broad release-statement wording claiming SDK/API/support
  production or stable readiness.
- Mission/Transfer/Dino/Tribe/Buff accounting rejects nested completion,
  stable, promoted, and complete-SDK claim aliases. Release statements that
  claim leaf promotion without strict promoted leaf evidence now block.

Validated offline: combined six-file suite 332, public SDK guardrails 193,
command bridge/intent suite 42, permissions/admin query fail-closed 42,
runtime/preflight suites 256 by delegated audit, route JSON valid/planning-only,
SDK JSON blocked by design, and `git diff --check`. The stable state remains
`current_route_blocker=approved_runtime_evidence_missing`, SDK progress `0/12`,
P0 progress `0/4`, and `stable_claim_allowed=false`.

## Runtime Evidence, SDK Secondary Reports, And Inventory Source-Marker Hardening

The next supervised 4-agent round closed three concrete offline bypasses and
confirmed one core runtime area had no missing guardrail:

- Runtime evidence/preflight text scanners now reject phrases that present
  request packs, preflight sidecars, window manifests, completed receipts,
  copied logs or bundles, stale bundles, sidecars, or generic artifacts as
  counting as approved runtime evidence.
- SDK completion secondary-report scanning now treats certificate, dependency,
  manifest, record, release-statement, and section child objects as independent
  report contexts. A blocker on the parent report no longer suppresses child
  public SDK, runtime, stable/support, or v1 completion overclaims.
- Inventory copied-signal stability now scans source-marker/source-label,
  marker, alias, report-section, artifact/evidence marker, and plural alias
  fields for Inventory SDK, Items SDK, ResourceHandle, return override, runtime
  readiness, promotion, public readiness, and v1 completion claims.
- `docs/STATUS.md` now states the current executable SDK gate result:
  `stable_claim_allowed=false` and canonical P0 route blocker
  `approved_runtime_evidence_missing`.
- Core runtime/plugin lifecycle audit made no edits. Existing guardrails still
  cover plugin cleanup failure retention, no repeated shutdown on retry,
  callback cleanup families, and default-deny risky runtime paths.

Validated offline: integrated suite 457, public SDK guardrails 194, route JSON
valid/planning-only, inventory JSON ready with `public_sdk_ready=false` and
`v1_completion_ready=false`, SDK JSON blocked by design, core runtime delegated
validations 29/6 plus `build/plugin_manager_tests`, and `git diff --check`.
The stable state remains `current_route_blocker=approved_runtime_evidence_missing`,
SDK progress `0/12`, P0 progress `0/4`, and `stable_claim_allowed=false`.

## Downstream Readiness, ResourceHandle, Live-Ops Docs, And Stale Research Hardening

The next supervised 4-agent round plus a lead release-gate wording patch closed
additional offline gaps without changing the P0 blocker:

- Downstream permissions/admin, command response, and commands/replies child
  readiness collectors now cover the parent route gate's forbidden alias set for
  nested public/runtime/route/reply/send-chat/accounting claims. Direct child
  runs can no longer miss aliases such as public ABI allowed, public SDK,
  runtime work authorized, send-chat ready, or similar route-readiness claims.
- ResourceHandle/object identity revalidation, serial-policy, post-callback,
  and public-contract readiness now reject nested source markers, public-contract
  or capability fields, and positive text such as `not blocked and ready` when
  they imply public lookup, object identity, runtime readiness, public SDK,
  promotion, or v1 completion.
- `docs/SERVER_RESTORE.md` now states that live log and `/proc` post-start
  checks are runtime observations inside the same current-turn approved
  maintenance window, not offline receipts or copied-log review.
- `scripts/check_release_readiness.sh` now reports `Public SDK v1 stable claim
  gate` wording instead of generic v1 completion wording, so a release-gate
  message cannot be read as partial SDK progress.
- Historical FName/GObjects notes now use `Current No-Repeat Checkpoint`
  sections and no longer direct broad FName/GObjects/core/decompiler reruns for
  the current blocker.

Validated offline: integrated suite 253, release-options shell, operational docs
10, route JSON valid/planning-only, ResourceHandle JSON planning-only with all
readiness false, SDK JSON blocked by design, research doc guardrails, and
`git diff --check`. The stable state remains
`current_route_blocker=approved_runtime_evidence_missing`, SDK progress `0/12`,
P0 progress `0/4`, and `stable_claim_allowed=false`.

## Runtime, SDK, Candidate, And Package Non-Claim Hardening

The next supervised 4-agent round plus lead integration closed offline
guardrail gaps without changing the P0 route blocker or SDK completion state.

Delegated scopes and integrated findings:

- Core runtime ABI/default-deny: `include/obelisk/ObeliskApi.h` now documents that
  raw global/filtered ProcessEvent registrations require the plugin's init-time
  capability snapshot plus the live env+marker gate. These are controlled debug
  windows, not production readiness signals. Static guardrail tests now verify
  capability bits still depend on the live gates and that `CallProcessEvent`
  remains an init-owner debug escape hatch.
- SDK completion wording: `check_public_sdk_v1_completion.py` now rejects release
  statements that hide positive stable/SDK readiness claims behind blocker
  phrasing, including patterns like "blocked ... stable SDK is ready" and
  contradictory tails like "stable is blocked but ready".
- Mission/Transfer/Dino/Tribe/Buff accounting: candidate-only evidence marker
  fields such as target/source markers, artifact status, evidence status, and
  reflection evidence now reject values implying public SDK/API/ABI, runtime,
  observer/hook wiring, promotion, ResourceHandle, identity, lookup, mutation,
  return override, v1 completion, stable, release, or ready unless they carry
  explicit candidate-only/blocked wording.
- Build/install/package shape: installed CMake package metadata now carries
  explicit `FALSE` markers for runtime readiness, live-ops approval, Plugin Hub
  readiness/publication, support-tier activation, v1 completion, public-module
  SDK coverage, and production-stable SDK claims. Installer, plugin-installer,
  and release-gate output now state that passing or publishing artifacts is
  evidence for the exact gate only.
- Community helper: `send_discord_embed.py` now rejects internal status phrases
  such as agent status, internal validation, release gate completed, routine
  validation, route JSON, and SDK JSON in dry-run or send payload text.

Observed unchanged route and SDK state:

- `check_command_permission_route_gate.py --json`: `valid=true`,
  `planning_only=true`, `current_route_blocker=approved_runtime_evidence_missing`,
  `counts_toward_public_sdk=false`, `counts_toward_runtime=false`,
  `counts_toward_v1_completion=false`, and route lock valid/locked.
- `check_public_sdk_v1_completion.py --json`: exits blocked by design with
  `ready=false`, `status=blocked`, SDK completion `0/12`, P0 dependency chain
  `0/4`, `stable_claim_allowed=false`, and
  `stable_release_contract_claim_allowed=false`.
- `check_mission_transfer_dino_tribe_v1_outcome_accounting.py --json` remains
  `candidate_only`, `promotion_ready=false`, `public_sdk_ready=false`,
  `runtime_ready=false`, and `v1_accounted=false`.

Validation remained offline-only:

- Runtime/API guardrails: `test_plugin_manager_guardrails.py`,
  `test_event_manager_guardrails.py`, and `ctest` for PluginManager,
  EventManager, AbiLayout, and CAbiLayout.
- SDK/completion guardrails: `test_public_sdk_guardrails.py`,
  `test_check_public_sdk_v1_completion.py`, and the blocked SDK JSON gate.
- Side-lane guardrails:
  `test_check_mission_transfer_dino_tribe_v1_outcome_accounting.py`,
  `test_check_mission_copied_bool_readiness.py`,
  `test_check_transfer_baccept_readiness.py`, and candidate-only JSON output.
- Package/release guardrails: `test_release_scope_guardrails.py`,
  `test_check_release_readiness_options.sh`, `test_install_obelisk_plugin.sh`,
  `test_install_obelisk_layout.sh` with a fresh `/tmp` install root, and
  installed SDK external example builds.
- Community/secret guardrails: `test_send_discord_embed.py`,
  `scripts.test_agent_handoff_guardrails`, and `scripts.test_secret_guardrails`.
- Hygiene: `git diff --check`.

Non-claims:

- These changes do not create approved runtime evidence and do not authorize
  server operations, marker/env changes, runtime observation, ReflectionScanner,
  ptrace/gcore, broad tracing, Discord sends, GitHub publication, tag updates,
  Plugin Hub publication, support-tier activation, stable SDK wording, or v1 SDK
  completion.
