# SDK Complete Priority Map

Date: 2026-06-02

## Scope

Concise routing facts for future compactations. This note records priority and completion
posture only; it is not runtime approval, release approval, Plugin Hub scope, or a public
SDK readiness claim.

## Current Completion Posture

- Official complete-SDK progress remains `0%`: complete-SDK accounting is still `0/12`
  and the P0 promoted chain is still `0/4`.
- The technical foundation is estimated at roughly `20-25%`. The basis is existing
  RC core/runtime work, copied plugin events, installed package-shape checks, offline
  intake tooling, and consume-only gameplay/module evidence. These are useful foundation
  pieces, but they do not satisfy the complete public SDK contract.
- Plugin Hub remains post-SDK-complete planning. Package examples, catalog/intake work,
  package hardening, and marketplace polish must not be routed ahead of SDK blockers.

## Reorganization Checkpoint

After the 2026-06-02 compaction/reorganization, the lead reran the canonical offline
checks from the current worktree:

- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
  passed as planning-only with `approved_runtime_evidence_missing` as the current
  critical-path blocker.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
  intentionally failed closed with `stable_claim_allowed=false`,
  complete-SDK progress `0/12`, and P0 progress `0/4`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_inventory_item_copied_signals_stability.py --json`
  passed with five allowed copied inventory/item signals while keeping
  `public_sdk_ready=false` and `v1_completion_ready=false`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_object_identity_resource_handle_public_contract_readiness.py --json`
  passed as planning-only with ResourceHandle/object identity still blocked.

These checks are routing evidence only. They do not approve runtime work, public SDK
promotion, release wording, Plugin Hub work, or a stable/production SDK claim.

## Guardrail Hardening Follow-Up

The same reorganization round added offline guardrails without changing readiness:

- `scripts/check_command_permission_route_gate.py` now requires planning/public-readiness
  child reports to keep both `planning_only=true` and `accepted_for_planning=true`; tests
  cover direct child JSON drift for both fields.
- `scripts/check_inventory_item_copied_signals_stability.py` now verifies copied and
  inventory-backed flags in the decisions manifest, `docs/public_gameplay_events.json`
  descriptor metadata, and each inventory/item event entry. It also rejects `non-copied`
  payload-contract drift instead of relying on substring checks.
- `scripts/check_player_principal_lifecycle_window_request.py` now scopes negation to the
  forbidden/private or readiness token being matched, skips exact fixed `non_claims`, and
  rejects broad `blocked ...` wording as a fake negation. This preserves request-pack
  safety without authorizing runtime work.
- `docs/agent-handoff/COMPACT_CONTEXT.md`, `docs/agent-handoff/CURRENT.md`,
  `docs/research/README.md`, and `agent-skills/obelisk-github-research-workflow/SKILL.md`
  were normalized so the active route is always
  `identity/principal -> permissions/admin -> command response -> commands/replies`.

Validation for this hardening:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_command_permission_route_gate scripts.test_check_inventory_item_copied_signals_stability scripts.test_check_player_principal_lifecycle_window_request`
  passed with 35 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
  passed as planning-only.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
  still failed closed with `stable_claim_allowed=false`, P0 `0/4`, and complete SDK
  `0/12`.

## P0 Dependency Chain

The real complete-SDK P0 route is:

1. `obelisk.player_identity.v1`
2. `obelisk.permissions_admin.v1`
3. `obelisk.command_chat_response_path.v1`
4. `obelisk.commands_replies.v1`

Static orientation, planning-layout acceptance, request-pack readiness, package-shape
evidence, and module side lanes are not substitutes for promotion of this chain.

## Identity Blocker

Player identity is first. If the current offline identity packs continue to pass, the
remaining blocker is an approved copied runtime principal lifecycle evidence window.
Do not spend more rounds on broad offline rediscovery unless the binary/hash changes,
the accepted packs fail, or a focused checker contradicts the current evidence.

## Post-P0 Target Map

After the P0 chain is promoted, the rentable module hardening routes are:

- Mission copied bools: focused copied-bool evidence with consume-only acceptance and
  explicit no-public-SDK/no-runtime-readiness/no-mutation/no-identity boundaries.
- Item return-only copied signals: already adjacent to copied `GameplayPolicyEvent`
  evidence and useful as a no-core, return-only policy lane, while still not promoting
  public Inventory SDK, Items SDK, mutation, identity, lookup, or v1 completion.

These routes are good post-P0 candidates because they have clear evidence boundaries and
limited blast radius. They remain side lanes until identity -> permissions/admin ->
command response -> commands/replies is promoted.

## P0 Route Hardening Follow-Up

The next supervised audit round tightened the planning-only P0 route without changing the
runtime blocker:

- `scripts/check_permissions_admin_public_readiness.py` now rejects fabricated
  `obelisk.permissions-admin-query-failclosed-contract-check.v1` reports unless they carry
  the checker-emitted contract fingerprint: input schema, query fields, decisions,
  provenance fields, authority kinds, and fail-closed cases.
- The same permissions/admin checker now rejects top-level drift in
  `docs/public_sdk_surfaces.json` that lists permissions/admin as promoted, removes it
  from planning surfaces, enables `v1_completion_required`, or rewrites the P0 dependency
  chain.
- `scripts/check_command_chat_response_public_readiness.py` and
  `scripts/check_commands_replies_public_readiness.py` now scope overclaim negation by
  clause, so mixed text such as `... remains blocked but reply API ready` is rejected
  while current dependency statements with `before`, `until`, `only`, or `never` remain
  valid non-claims.
- `scripts/check_commands_replies_public_readiness.py` now requires the composed
  `obelisk.command-chat-response-public-readiness-check.v1` report through
  `--response-path-report`. A raw `obelisk.reflection-snapshot-readiness.v1` planning
  JSON is no longer accepted as the response-path dependency artifact.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_permissions_admin_public_readiness scripts.test_check_command_chat_response_public_readiness scripts.test_check_commands_replies_public_readiness scripts.test_check_command_permission_route_gate`
  passed with 98 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
  passed as planning-only with `approved_runtime_evidence_missing`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
  still failed closed with `stable_claim_allowed=false`, P0 `0/4`, and complete SDK
  `0/12`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_inventory_item_copied_signals_stability.py --json`
  passed with public SDK/v1 completion false.

Deferred audit findings for future focused rounds:

- Player-identity approved evidence should rerun or strongly verify the window manifest
  and request-pack sidecars beyond path/hash checks before accepting promoted runtime
  evidence.
- Permissions/admin should validate cache generation/scope invalidation semantics and
  expand public header alias/protected-path coverage.
- `scripts/check_public_sdk_v1_completion.py` should reject weak non-canonical demand
  family equivalents unless a reviewed allowlist and surface-specific evidence prove the
  equivalent is legitimate.

## Identity And Permissions Evidence-Gate Hardening

A follow-up supervised audit round closed several high-value offline guardrails without
changing runtime or SDK readiness:

- `scripts/check_permissions_admin_query_failclosed_contract.py` now rejects duplicate and
  reordered query fields, decision fields/results, fail-closed cases, and reason flags.
  Reason flags must also keep the canonical flag-name to bit-index mapping.
- `scripts/check_permissions_admin_public_readiness.py` now fingerprints the
  sequence-aware query fail-closed checker report, so fabricated readiness JSON cannot
  pass by presenting sorted or drifted contract lists.
- `scripts/check_player_identity_first_evidence_readiness.py` preserves observer env parse
  blockers from the player-principal lifecycle request checker when reporting request-pack
  diagnosis.
- `scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py` no longer
  reads protected or non-approved request-pack paths while validating sidecars. This keeps
  protected-path blockers from being masked by JSON/schema validation side effects.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_runtime_principal_lifecycle_window_manifest`
  passed with 28 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_permissions_admin_query_failclosed_contract scripts.test_check_permissions_admin_public_readiness`
  passed with 73 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_first_evidence_readiness scripts.test_check_player_identity_runtime_principal_lifecycle_window_manifest`
  passed with 59 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_command_permission_route_gate scripts.test_check_permissions_admin_query_failclosed_contract scripts.test_check_permissions_admin_public_readiness scripts.test_check_player_identity_first_evidence_readiness scripts.test_check_player_identity_runtime_principal_lifecycle_window_manifest`
  passed with 147 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
  passed as planning-only with current blocker `approved_runtime_evidence_missing`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
  still failed closed with `stable_claim_allowed=false`, complete-SDK progress `0/12`,
  and P0 progress `0/4`.
- `git diff --check` passed.

This hardening is routing and evidence-gate hygiene only. It does not approve runtime
work, public permissions/admin ABI, public identity, command replies, release readiness,
or a stable SDK claim.

## Follow-Up Guardrail Round

The next supervised round closed three additional offline overclaim paths:

- `scripts/check_permissions_admin_public_readiness.py` now enforces the exact
  permissions/admin cache key sequence, keeps public cache ABI blocked, requires explicit
  generation/scope invalidation semantics, rejects mismatched manifest public-header
  declarations, rejects protected or symlinked public-header inputs, and scans additional
  permissions/admin header aliases such as `PermissionQuery`, `PermissionReasonFlags`,
  and `CheckPermission`.
- `scripts/check_public_sdk_v1_completion.py` now rejects all demand-family completion
  equivalents unless an explicit reviewed allowlist names the blocker/equivalent pair.
  The allowlist is empty, so synthetic `*_equivalent.v1` rows and foundation/package-shape
  equivalents cannot satisfy complete-SDK demand-family gaps.
- `scripts/check_object_identity_resource_handle_public_contract_readiness.py` now scans
  the `obelisk.object_identity_resource_handle.v1` surface row in
  `docs/public_sdk_surfaces.json` for positive ResourceHandle/object lookup/post-callback
  claims. This closes a gap where the checker scanned public gameplay events for positive
  claims but not the ResourceHandle blocker row itself.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_permissions_admin_public_readiness`
  passed with 42 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion`
  passed with 107 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_object_identity_resource_handle_public_contract_readiness`
  passed with 8 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
  passed as planning-only with current blocker `approved_runtime_evidence_missing`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_object_identity_resource_handle_public_contract_readiness.py --json`
  passed as planning-only with ResourceHandle/object identity still blocked.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
  still failed closed with `stable_claim_allowed=false`, complete-SDK progress `0/12`,
  and P0 progress `0/4`.
- `git diff --check` passed.

Remaining focused offline finding:

- `scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py` should
  replay or strongly compare the operational `window-manifest.env` and request/env/preflight
  sidecars instead of trusting embedded operational-window metadata plus hashes alone.
  The replay must tolerate expiry-only request-window blockers for already-captured
  approved evidence only after confirming capture timestamps are inside the approved
  window; target/window/env/preflight drift should fail with a top-level blocker such as
  `operational_window_manifest_check_failed`.

This round still does not approve runtime work, public permissions/admin ABI, public
identity, command replies, ResourceHandle, release readiness, or a stable SDK claim.

## Approved Evidence And Mission Frontier Hardening

The next supervised round closed the focused player-identity approved-evidence sidecar
gap and one Mission side-lane frontier gap:

- `scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py` now
  replays the operational `window-manifest.env` with the existing window-manifest checker
  and compares the replayed operational-window projection against the embedded
  `operational_window` report. Mutated `window-manifest.env`, `window-request.json`,
  `observer-window.env`, or preflight sidecars now fail even if their embedded SHA and
  output artifact identity are refreshed.
- The approved-evidence replay tolerates only the historical
  `approved_window_expired` request-check blocker when it is the sole nested request
  blocker. This keeps already-captured approved evidence consumable while still failing
  target/window/env/preflight drift.
- `scripts/check_mission_copied_bool_readiness.py` now scans nested `CMakeLists.txt` and
  `*.cmake` files, excluding ignored `build/`, `local/`, `.git`, `__pycache__`, and
  `.pytest_cache` roots. This prevents a nested CMake file from wiring
  `hooks/ProcessEventMissionReflection.cpp` into a runtime/shared target while the Mission
  checker still reports the side lane as internal consume-only evidence.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence`
  passed with 39 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_runtime_principal_lifecycle_window_manifest`
  passed with 28 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_mission_copied_bool_readiness`
  passed with 18 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_first_evidence_readiness scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence scripts.test_check_player_identity_runtime_principal_lifecycle_window_manifest scripts.test_check_mission_copied_bool_readiness`
  passed with 116 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_mission_copied_bool_readiness.py --json`
  passed as consume-only Mission evidence with public SDK/runtime/v1 completion false.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
  passed as planning-only with `approved_runtime_evidence_missing`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
  still failed closed with `stable_claim_allowed=false`, complete-SDK progress `0/12`,
  and P0 progress `0/4`.

Remaining focused offline finding:

- Standalone `scripts/check_commands_replies_public_readiness.py` still accepts a
  summary-only `--response-path-report` fixture. The route gate composes a real child
  response-path report, but the standalone checker should reject unverifiable response
  reports unless they include source artifact paths or equivalent child-checker provenance.

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Mission SDK, release readiness, or a stable SDK claim.

## Commands Replies Response-Path Provenance Guardrail

The next supervised round closed the standalone commands/replies response-path report
gap:

- `scripts/check_commands_replies_public_readiness.py` now requires
  `--response-path-report` payloads using
  `obelisk.command-chat-response-public-readiness-check.v1` to carry the child checker's
  provenance fields: `readiness_path`, `decisions_path`, `surfaces_path`, and
  `public_header_path`.
- Missing provenance fails with `response_path_report_source_artifacts_missing`.
  Empty or non-string provenance fails with `response_path_report_unverifiable`.
- The checker also requires child `surfaces_status` to be `planning` or `post-v1`. This
  catches summary fixtures that copied readiness/decisions status but omitted the
  response-path surface posture.
- Embedded paths are provenance strings only. The standalone commands/replies checker
  validates the response report file path itself, but does not reopen embedded child
  paths because the response-path checker can emit temporary or CLI-overridden path
  strings.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_command_chat_response_public_readiness scripts.test_check_commands_replies_public_readiness scripts.test_check_command_permission_route_gate`
  passed with 64 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
  passed as planning-only with current blocker `approved_runtime_evidence_missing`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
  still failed closed with `stable_claim_allowed=false`, complete-SDK progress `0/12`,
  and P0 progress `0/4`.
- `git diff --check` passed.

Remaining focused offline finding:

- `scripts/check_structure_build_policy_offline_intake.py` should validate manifest-level
  `obelisk.structure_census.v1` posture, not only the unique surface ID. A manifest-only
  overclaim should fail if the surface is promoted, missing from the planning list,
  assigned the wrong support tier, or carries a non-empty public contract while the
  structure build-policy artifact remains consume-only planning evidence.

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Structure SDK, release readiness, or a stable SDK claim.

## Structure, P0 Route, And ResourceHandle Text Guardrails

The next supervised round closed three additional offline overclaim paths:

- `scripts/check_structure_build_policy_offline_intake.py` now validates the
  manifest-level `obelisk.structure_census.v1` surface posture, not only the nested
  structure build-policy report. It rejects placement in `promoted_surfaces`, absence from
  `planning_surfaces`, status/support-tier drift away from `planning`/`blocked`, and
  non-empty public contract, public ABI, or ABI contract posture.
- `scripts/check_player_identity_first_evidence_readiness.py` now adds
  `identity_public_contract_gate_missing` as a top-level blocker after approved runtime
  principal lifecycle evidence is accepted. Approved runtime evidence can clear
  `approved_runtime_evidence_missing`, but it cannot make the first-evidence checker
  `ready=true` before reviewed public contract work.
- `scripts/check_command_permission_route_gate.py` now rejects child-reported
  `identity_public_contract_gate` or `identity_public_contract_gate_missing` as the
  current route blocker. The current route remains pinned to
  `approved_runtime_evidence_missing` until the route gate is explicitly updated with
  reviewed public-contract evidence.
- `scripts/check_object_identity_resource_handle_public_contract_readiness.py` now scans
  decisions-manifest text for positive ResourceHandle/object identity/object lookup or
  post-callback correlation claims, closing a gap where only the public SDK surface row
  and public events were text-scanned.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_first_evidence_readiness scripts.test_check_command_permission_route_gate scripts.test_check_structure_build_policy_offline_intake`
  passed with 70 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_object_identity_resource_handle_public_contract_readiness`
  passed with 9 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
  passed as planning-only with current blocker `approved_runtime_evidence_missing`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_structure_build_policy_offline_intake.py --json`
  passed as planning-only Structure build-policy intake with public SDK/runtime/enforcement
  readiness false.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_object_identity_resource_handle_public_contract_readiness.py --json`
  passed as planning-only with ResourceHandle/object identity still blocked.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
  still failed closed with `stable_claim_allowed=false`, complete-SDK progress `0/12`,
  and P0 progress `0/4`.
- `git diff --check` passed.

Remaining focused offline finding:

- `scripts/check_inventory_item_copied_signals_stability.py` should scan top-level and
  adjacent `docs/public_sdk_surfaces.json` text for positive Inventory/Items SDK
  side-lane claims. Current scanning catches forbidden public claim terms inside the
  inventory copied-signal surface row and readiness booleans across the manifest, but a
  crafted top-level text such as an inventory SDK release note can still overstate the
  no-core side lane.

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Structure SDK, ResourceHandle, Inventory SDK, release readiness, or a
stable SDK claim.

## Inventory, Mission Leaf, And Release Wording Guardrails

The next supervised round closed four more offline overclaim paths:

- `scripts/check_inventory_item_copied_signals_stability.py` now scans all
  `docs/public_sdk_surfaces.json` string text for positive `Inventory SDK` and `Items SDK`
  side-lane claims. It still skips negative-key areas such as exclusions/non-claims and
  honors existing negation handling, so scoped wording like `no Inventory SDK readiness`
  remains valid.
- `scripts/check_player_identity_first_evidence_readiness.py` now reports
  `identity_public_contract_gate_missing` consistently in both `blockers` and
  `primary_blocker`/`next_actionable_blocker.code` after approved runtime evidence. This
  removes the blocker-alias drift between the safer missing-contract blocker and the
  contract-gate route label.
- `scripts/check_public_sdk_v1_completion.py` now rejects release-statement wording in
  the form `Obelisk SDK v1 is ready` and `Obelisk SDK v1 is production ready`, closing a
  word-order gap in broad stable/complete SDK claim scanning.
- `scripts/check_mission_transfer_dino_tribe_v1_outcome_accounting.py` now validates
  every non-promoted mission/transfer/dino/tribe/buff leaf evidence object for readiness
  boolean overclaims and forbidden claims. The previous guardrail only scanned the
  Mission leaf, so a Transfer leaf could claim `public_sdk_ready`, `runtime_ready`, or
  `ResourceHandle lookup ready` without blocking candidate-only accounting.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_inventory_item_copied_signals_stability scripts.test_check_player_identity_first_evidence_readiness scripts.test_check_public_sdk_v1_completion scripts.test_check_mission_transfer_dino_tribe_v1_outcome_accounting`
  passed with 166 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_inventory_item_copied_signals_stability.py --json`
  passed with five allowed copied inventory/item signals while keeping public SDK/v1
  completion false.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_mission_transfer_dino_tribe_v1_outcome_accounting.py --json`
  passed as candidate-only Mission/Transfer/Dino/Tribe/Buff accounting with public
  SDK/runtime/v1 accounting false.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
  passed as planning-only with current blocker `approved_runtime_evidence_missing`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
  still failed closed with `stable_claim_allowed=false`, complete-SDK progress `0/12`,
  and P0 progress `0/4`.
- `git diff --check` passed.

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Mission/Transfer/Dino/Tribe/Buff SDKs, Inventory SDK, release readiness,
or a stable SDK claim.

## Provenance, Dispatcher Exception, Descriptor, And Release Verb Guardrails

The next supervised round closed four additional offline guardrail gaps:

- `scripts/check_commands_replies_public_readiness.py` now treats embedded
  `check_command_chat_response_public_readiness.py` source paths as verifiable report
  provenance. It rejects missing/unreadable source artifacts, re-runs the child response
  path checker from those artifacts, and rejects child summary fields that drift from the
  rebuilt report. A plausible JSON report with nonexistent paths is no longer accepted.
- `scripts/test_plugin_manager_guardrails.py` now requires every
  `COPIED_DISPATCHER_CLEANUP_EXCEPTIONS` entry to declare blocked public ABI and
  PluginManager wiring tokens. `MissionCopiedBoolEventDispatcher` remains an
  internal/test-only cleanup exception, but Mission public ABI or PluginManager wiring
  tokens now fail while owner cleanup is absent.
- `scripts/check_object_identity_resource_handle_public_contract_readiness.py` now scans
  promoted descriptor metadata surfaces, including `obelisk.descriptors.v1`, for forbidden
  ResourceHandle/object identity/object lookup public-contract terms and positive
  evidence claims. Public descriptor helpers remain category-only metadata and cannot
  imply ResourceHandle lookup or post-callback object correlation.
- `scripts/check_public_sdk_v1_completion.py` now rejects active release verbs in scoped
  release statements, including `Obelisk SDK v1 ships today`, `complete SDK ships`,
  `stable SDK launches`, and `Obelisk SDK v1 is generally available`.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_commands_replies_public_readiness`
  passed with 28 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_plugin_manager_guardrails.py`
  passed with 24 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_object_identity_resource_handle_public_contract_readiness`
  passed with 10 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion`
  passed with 108 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
  passed as planning-only with current blocker `approved_runtime_evidence_missing`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_object_identity_resource_handle_public_contract_readiness.py --json`
  passed as planning-only with ResourceHandle/object identity still blocked.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
  still failed closed with `stable_claim_allowed=false`, complete-SDK progress `0/12`,
  and P0 progress `0/4`.
- `git diff --check` passed.

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Mission SDK, ResourceHandle, object lookup, release readiness, or a
stable SDK claim.

## Route Manifest, Dino Provenance, And Wording Guardrails

The next supervised round closed four offline gaps and recorded one negative ABI/runtime
audit result:

- `scripts/check_command_permission_route_gate.py` now forwards the route-level
  `--public-sdk-surfaces` and `--public-header` arguments into the downstream
  permissions/admin, command response, and commands/replies child checks. The aggregate
  route gate can no longer pass against a caller-supplied manifest that promotes
  `obelisk.commands_replies.v1` while the downstream child checks silently read the repo
  default manifest.
- `scripts/check_dino_scalar_readiness.py` now revalidates external `--report` input by
  rebuilding the redacted UFunction signature report from the supplied snapshot root and
  comparing `generated_from` plus `descriptor_preflight`. A synthetic Dino scalar report
  with fabricated snapshot ids no longer passes as candidate-ready planning evidence.
- `scripts/check_object_identity_resource_handle_public_contract_readiness.py` now treats
  `ships`, `includes`, and `part of v1` as positive ResourceHandle/object identity text
  claims when they occur with ResourceHandle/object lookup/post-callback correlation
  terms.
- `scripts/check_public_sdk_v1_completion.py` now rejects `production-grade` and
  `release-grade` SDK/API/support release-statement claims, along with existing
  production/stable/complete/full wording.
- Runtime/ABI audit found no actionable gap in the inspected public header,
  `CallProcessEvent` init-window enforcement, PluginManager/EventManager/TimerManager
  owner cleanup, callback exception containment, or PluginManager static guardrails. This
  was a read-only negative result; it does not promote additional ABI or runtime scope.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_dino_scalar_readiness`
  passed with 16 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_command_permission_route_gate`
  passed with 17 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_object_identity_resource_handle_public_contract_readiness`
  passed with 12 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion`
  passed with 109 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
  passed as planning-only with current blocker `approved_runtime_evidence_missing`, and
  its child argv now shows shared `--surfaces`/`--public-header` on permissions/admin,
  command response, and commands/replies checks.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_dino_scalar_readiness.py --json`
  passed as internal candidate-only Dino scalar planning evidence with public
  SDK/runtime/v1 readiness false.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_object_identity_resource_handle_public_contract_readiness.py --json`
  passed as planning-only with ResourceHandle/object identity still blocked.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
  still failed closed with `stable_claim_allowed=false`, complete-SDK progress `0/12`,
  and P0 progress `0/4`.
- `git diff --check` passed.

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Dino SDK, ResourceHandle, object lookup, release readiness, or a stable
SDK claim.

## Route Blocker Provenance And GA Wording Guardrails

The next supervised round closed two offline release/route guardrail gaps and recorded one
deferred side-lane promotion provenance risk:

- `scripts/check_command_permission_route_gate.py` now preserves
  `source_checker_primary_blocker`, `source_checker_next_blocker`, and the player-identity
  first-evidence readiness booleans in `critical_path_phase`. The route validator rejects
  missing first-evidence blocker provenance and positive readiness overclaims instead of
  defaulting a malformed child report back to `approved_runtime_evidence_missing`.
- `scripts/check_public_sdk_v1_completion.py` now rejects `GA` abbreviations in scoped
  release statements, including `Obelisk SDK v1 is GA`, `Obelisk SDK v1 reaches GA`, and
  `The v1 SDK is GA`, alongside existing `generally available`, `ships`, `launches`,
  `production-grade`, and `release-grade` broad wording.
- Read-only side-lane audit found a deferred risk in the future
  `per_leaf_promoted` path of
  `scripts/check_mission_transfer_dino_tribe_v1_outcome_accounting.py`: placeholder
  `abi_tests`, `sdk_consumer_tests`, and `second_source_evidence` lists can satisfy the
  promoted leaf shape without verifying path existence, approved gate report identity,
  leaf ownership, or second-source provenance. This was not integrated in this checkpoint;
  it should be the next offline artifact-gate hardening target before any promoted
  Mission/Transfer/Dino/Tribe leaf is accepted.
- Runtime/ABI audit again found no actionable offline-detectable gap in the inspected
  public header, PluginManager/EventManager/TimerManager cleanup, CallProcessEvent
  init-window posture, callback exception containment, or static PluginManager guardrails.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_command_permission_route_gate`
  passed with 19 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion`
  passed with 110 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
  passed as planning-only with current blocker `approved_runtime_evidence_missing` and
  preserved source-checker blocker provenance.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
  still failed closed with `stable_claim_allowed=false`, complete-SDK progress `0/12`,
  and P0 progress `0/4`.
- `git diff --check` passed.

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Mission/Transfer/Dino/Tribe SDKs, ResourceHandle, release readiness, or a
stable SDK claim.

## Promoted Leaf Provenance And Route Validity Guardrails

The next supervised round closed the deferred Mission/Transfer/Dino/Tribe promoted-leaf
accounting risk and two remaining command-route fail-closed gaps:

- `scripts/check_mission_transfer_dino_tribe_v1_outcome_accounting.py` no longer accepts
  non-empty placeholder lists as promoted leaf evidence. Each promoted leaf evidence entry
  must now be a JSON report reference with `path` and expected `sha256`; the file must be
  readable, match the SHA, decode as an object, declare the expected `surface`, `leaf`,
  `evidence_kind`, `status=promoted`, `promotion_ready/public_sdk_ready/runtime_ready`,
  and include `artifact_identity`. `second_source_evidence` entries must also include
  `second_source_provenance`.
- The promoted-leaf route now returns false if promoted evidence blockers were added, so
  invalid promoted leaves cannot still select `accounting_route=per_leaf_promoted`,
  clear missing public gates, or mark `v1_accounted=true`.
- `scripts/check_public_sdk_v1_completion.py` now refuses to treat
  `obelisk.mission_transfer_dino_tribe.v1` as having promotion evidence unless all five
  leaf decision units (`mission`, `transfer`, `dino_policy`, `tribe_policy`,
  `buff_status`) are present and promoted. Mission-only evidence cannot count the umbrella
  blocker toward complete-SDK progress.
- `scripts/check_command_permission_route_gate.py` now requires route child reports to
  emit explicit `valid=true`, and validates the player-identity first-evidence child
  `source_checker_exit_code`, `status`, `ready`, and
  `accepted_for_internal_planning` fields. A child that preserves the current blocker text
  but claims readiness now blocks the route.
- `scripts/check_player_identity_public_contract_gap_report.py` and
  `scripts/check_permissions_admin_query_failclosed_contract.py` now emit explicit
  `valid` fields, allowing the stricter route gate to stay fail-closed without rejecting
  healthy current prereqs.

Reusable provenance notes from read-only artifact-gate audit:

- `validate_offline_artifact_gate.py` emits
  `schema=obelisk.offline-artifact-gate-result.v1`, `mode`, `binary_sha256`, `status`,
  `manifests[]`, `artifacts[]`, and `blockers`; manifest records include `path`,
  `resolved_path`, `schema`, and `sha256`; artifact records include `label`, `sha256`,
  `provenance`, and `provenance_verified`.
- Existing side-lane readiness wrappers for Mission, Transfer, Item return, and Structure
  are consume-only/candidate evidence today. `ready=true`, `status=candidate_ready`,
  `not_artifact_gate=true`, or skipped consume/promote gates must not be interpreted as
  promoted leaf evidence.
- Future promoted leaves should bind evidence to leaf/source snapshots/targets and carry
  artifact identity plus second-source provenance; no Dino/Tribe promoted-leaf schema is
  currently present in the scoped files.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_mission_transfer_dino_tribe_v1_outcome_accounting`
  passed with 14 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_command_permission_route_gate`
  passed with 21 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_public_contract_gap_report scripts.test_check_permissions_admin_query_failclosed_contract`
  passed with 48 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion`
  passed with 111 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
  passed as planning-only with current blocker `approved_runtime_evidence_missing` and
  explicit valid child reports.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_mission_transfer_dino_tribe_v1_outcome_accounting.py --json`
  passed as candidate-only accounting with all five leaves still planning.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
  still failed closed with `stable_claim_allowed=false`, complete-SDK progress `0/12`,
  and P0 progress `0/4`.
- `git diff --check` passed.

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Mission/Transfer/Dino/Tribe SDKs, ResourceHandle, release readiness, or a
stable SDK claim.

## Post-Compaction Route And Umbrella Evidence Guardrails

The resumed lead round closed two more offline fail-closed gaps while preserving the same
P0 blocker and SDK-completion accounting:

- `scripts/check_public_sdk_v1_completion.py` now requires the
  `obelisk.mission_transfer_dino_tribe.v1` umbrella row to carry promoted evidence for
  each leaf decision unit (`mission`, `transfer`, `dino_policy`, `tribe_policy`, and
  `buff_status`). Top-level umbrella evidence plus promoted leaf statuses is no longer
  enough to satisfy `promotion_evidence_satisfied`.
- `scripts/check_command_permission_route_gate.py` now treats non-empty `blockers` in a
  child report as a hard route failure even when the child also reports `valid=true`.
  Aggregated reports surface this as `child blockers not empty` so dependency blockers
  cannot be masked by a contradictory child `valid` field.
- Deferred read-only audit findings remain open for future guardrail rounds:
  structure second-source readiness alias/string overclaims, inventory/item copied-signal
  readiness claims in `docs/public_gameplay_events.json`, and structured ResourceHandle/
  object-identity metadata claims in surfaces or decision JSON.

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Inventory/Items SDKs, Structure SDK, Mission/Transfer/Dino/Tribe SDKs,
ResourceHandle, release readiness, or a stable SDK claim.

## Player Identity Aggregate Provenance Closure

The next supervised P0 identity round closed the deferred aggregate provenance gap:

- `scripts/check_player_identity_first_evidence_readiness.py` now exposes lifecycle
  candidate `artifact_identity.source_artifact_ids` and accepted-anchor snapshot hashes
  to the aggregate checker, extracts principal-policy lifecycle source binding, and emits
  `first_evidence.planning_provenance` with a non-claim boundary.
- The aggregate checker now blocks on
  `lifecycle_anchor_first_evidence_provenance_unbound` before
  `approved_runtime_evidence_missing` when standalone lifecycle-anchor or principal-policy
  planning artifacts cannot prove they came from the same first-evidence source identity.
  Bound test fixtures can still advance to `approved_runtime_evidence_missing`; stale or
  unbound fixtures cannot.
- `scripts/check_command_permission_route_gate.py` now treats
  `lifecycle_anchor_first_evidence_provenance_unbound` as an allowed identity-lock
  planning-only blocker, alongside `approved_runtime_evidence_missing`, while still
  requiring the identity checker to exit blocked with readiness/public/runtime flags
  false and permissions/command unlocks false.
- The standalone principal invalidation policy checker remains consume-mode
  backward-compatible for unbound candidate manifests; stricter source binding is enforced
  by the aggregate readiness checker where the policy is used to advance the P0 route.

Current route posture changes accordingly: the immediate offline P0 next step is to bind
the lifecycle anchor and principal policy sources to the first-evidence source identity.
Approved copied runtime principal lifecycle evidence remains required after that, and
public identity review remains after approved runtime evidence.

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Inventory/Items SDKs, Structure SDK, Mission/Transfer/Dino/Tribe SDKs,
ResourceHandle, release readiness, or a stable SDK claim.

## P0 Report Provenance And Release Template Guardrails

The next supervised P0/offline audit round closed two report replay paths and one release
wording sink:

- `scripts/check_permissions_admin_public_readiness.py` no longer accepts a
  `obelisk.permissions-admin-query-failclosed-contract-check.v1` checker report as
  `--query-failclosed-artifact`. The standalone public-readiness checker now accepts only
  the candidate query manifest and revalidates it in consume mode, so a self-shaped report
  cannot become planning evidence without the source artifact.
- `scripts/check_commands_replies_public_readiness.py` now requires response-path reports
  to be bound to expected response root/readiness inputs and verifies the embedded
  response child `surfaces_path` and `public_header_path` against the aggregate checker's
  current inputs. `scripts/check_command_permission_route_gate.py` forwards the freshly
  composed command response report's `readiness_root` and `readiness_path` into replies,
  preserving the planning-only route while blocking stale self-consistent response
  bundles in standalone use.
- `scripts/test_public_sdk_guardrails.py` now scans `release/v1/public-sdk/*.md` with the
  release-statement broad-claim detector whenever `stable_claim_allowed=false`. This
  covers scoped release statement templates without treating blocker wording as a generic
  public-material false positive.
- The same test update preserves the current inventory copied-signal guardrails by
  allowing and asserting `required_flags` only for inventory-backed copied
  `GameplayPolicyEvent` entries.

Deferred P0 identity risk from the read-only audit remains open: player-identity
first-evidence can still accept standalone lifecycle-anchor and principal-policy planning
artifacts that are valid in isolation without proving they come from the same accepted
reflection inventory, first-evidence output, snapshot root, or source artifact hashes.
Treat that as the next offline identity provenance hardening target; it is not approved
runtime evidence and does not change the current blocker.

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Inventory/Items SDKs, Structure SDK, Mission/Transfer/Dino/Tribe SDKs,
ResourceHandle, release readiness, or a stable SDK claim.

## Command Response Readiness Provenance Binding

The next P0-focused supervised round closed the deferred synthetic readiness provenance
risk on the command response path:

- `scripts/check_command_chat_response_public_readiness.py` now passes a selected
  readiness root through report construction, requires the readiness JSON path to resolve
  exactly to `root/command-chat-response-route-planning-readiness.json`, and validates
  each `modules[0].target_details[*].path` as the expected regular snapshot file under
  `root/base-snapshots/`.
- The command response report now emits `readiness_root` so consumers can compare replayed
  source identity, not only the readiness JSON path.
- `scripts/check_command_permission_route_gate.py` now rejects caller-supplied
  `--command-response-readiness` unless `--command-response-root` is also supplied and the
  readiness path is exactly the default readiness file under that root. When composing
  commands/replies, the route forwards expected response root/readiness context.
- `scripts/check_commands_replies_public_readiness.py` now accepts optional
  `--response-path-root` and `--response-path-readiness` arguments and rejects embedded
  response-path reports whose `readiness_root` or source readiness path disagrees with
  that expected context.

This closes the stale/synthetic self-consistent report path for explicit route
composition without adding public response ABI or runtime authority. The route remains
planning-only and still blocks at approved runtime principal lifecycle evidence.

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Inventory/Items SDKs, Structure SDK, Mission/Transfer/Dino/Tribe SDKs,
ResourceHandle, release readiness, or a stable SDK claim.

## Side-Lane Overclaim Closure And Command Response Provenance Risk

The next supervised round closed the three deferred side-lane overclaim classes and one
related item-return checker drift:

- `scripts/check_structure_census_readiness.py` now applies a second-source readiness
  overclaim scan for positive Structure SDK/build-policy/enforcement/runtime/v1 aliases
  and readiness strings. The accepted default second-source artifact remains
  `candidate-only` planning evidence; the scanner avoids treating negative guidance text
  as a positive claim.
- `scripts/check_inventory_item_copied_signals_stability.py` now scans
  `docs/public_gameplay_events.json` for generic runtime/v1 readiness booleans and
  positive readiness strings, not only `docs/public_sdk_surfaces.json`.
- `scripts/check_item_return_only_readiness.py` now rejects the same generic runtime/v1
  readiness claims when run standalone against public gameplay events, and accepts the
  current copied+inventory-backed `required_flags` metadata while still validating it.
- `scripts/check_object_identity_resource_handle_public_contract_readiness.py` now applies
  structured positive ResourceHandle/object-lookup claim scanning to decisions and the
  `obelisk.object_identity_resource_handle.v1` surface row, not only public gameplay
  events or prose strings.

Read-only P0 route audit found one remaining higher-priority provenance risk:
`check_command_chat_response_public_readiness.py` can validate a well-shaped synthetic
`--readiness` JSON without binding it to the supplied snapshot root or regenerating it
from source artifacts. Because `check_command_permission_route_gate.py` composes that
child report into `commands/replies`, the next P0 guardrail should bind command response
readiness to source root/producer argv/input hashes or rebuild and compare the readiness
report before accepting planning alignment.

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Inventory/Items SDKs, Structure SDK, Mission/Transfer/Dino/Tribe SDKs,
ResourceHandle, release readiness, or a stable SDK claim.
