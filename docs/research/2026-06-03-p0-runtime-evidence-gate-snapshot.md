# P0 Runtime Evidence Gate Snapshot

## Purpose

Record the current P0 SDK route after the tribe/accounting checkpoint so future
agents do not confuse internal side-lanes with progress on the complete v1 SDK
claim.

## Baseline

- Obelisk commit: `279b16c Integrate tribe scalar accounting evidence`
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
evidence is accepted, the route may advance only to locked planning blocker
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
