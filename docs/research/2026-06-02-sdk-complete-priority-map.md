# SDK Complete Priority Map

Date: 2026-06-02

## Scope

Accumulated routing and blocker ledger for future compactations. This note records
priority and completion posture only; it is not runtime approval, release approval,
Plugin Hub scope, or a public SDK readiness claim.

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
  originally passed as planning-only with
  `lifecycle_anchor_first_evidence_provenance_unbound` as the default-route critical-path
  blocker. That historical blocker is now closed by repo-local source-bound planning
  artifacts; the current default-route blocker is `approved_runtime_evidence_missing`.
  After accepted approved runtime evidence, the next allowed locked blocker is
  `identity_public_contract_gate_missing`.
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
immediate default-route blocker is `approved_runtime_evidence_missing`. Request-pack,
preflight, and planning-layout readiness are not approved runtime principal lifecycle
evidence and do not authorize runtime. After accepted approved runtime evidence, the
allowed locked route blocker is `identity_public_contract_gate_missing`. Do not spend more
rounds on broad offline rediscovery unless the binary/hash changes, the accepted packs
fail, or a focused checker contradicts the current evidence.

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
  passed as planning-only on the default route with
  `lifecycle_anchor_first_evidence_provenance_unbound`.
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
  passed as planning-only on the default route with current blocker
  `lifecycle_anchor_first_evidence_provenance_unbound`.
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
  passed as planning-only on the default route with current blocker
  `lifecycle_anchor_first_evidence_provenance_unbound`.
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
  passed as planning-only in that historical route context with blocker `approved_runtime_evidence_missing`.
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
  passed as planning-only in that historical route context with blocker `approved_runtime_evidence_missing`.
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
- Superseded by `bf5f055`: `scripts/check_command_permission_route_gate.py` now accepts
  `identity_public_contract_gate_missing` as a locked planning blocker after approved
  runtime evidence, while keeping downstream readiness/unlock flags false. It still
  rejects bare `identity_public_contract_gate` as not a route-lock blocker.
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
  passed as planning-only in that historical route context with blocker `approved_runtime_evidence_missing`.
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
  passed as planning-only in that historical route context with blocker `approved_runtime_evidence_missing`.
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
  passed as planning-only in that historical route context with blocker `approved_runtime_evidence_missing`.
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
  passed as planning-only in that historical route context with blocker `approved_runtime_evidence_missing`, and
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
  passed as planning-only in that historical route context with blocker `approved_runtime_evidence_missing` and
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
  passed as planning-only in that historical route context with blocker `approved_runtime_evidence_missing` and
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

## Identity Public Contract Post-Evidence Route Modeling

The next supervised P0 round closed the route-accounting gap after approved runtime
principal lifecycle evidence:

- Four read-only sub-agent scopes were lead-delegated and closed: public-contract
  gap/readiness, route composition, privacy/redaction, and handoff/research continuity.
- `scripts/check_player_identity_public_contract_gap_report.py` remains the current
  no-runtime-evidence gap report. It is intentionally not the post-evidence intake path:
  it keeps `accepted_for_contract_review=false`, `runtime_evidence_missing=true`, and
  primary offline gap `privacy.identifier_redaction`.
- `scripts/check_player_identity_public_contract_readiness.py` remains the post-evidence
  path. It consumes approved runtime evidence only as contract-review input and keeps
  promotion, public SDK, runtime, and public header readiness false.
- `scripts/check_command_permission_route_gate.py` now includes
  `identity_public_contract_gate_missing` as an allowed identity lock blocker. Validation
  still requires planning-only posture and all downstream unlock/readiness flags false.
- `scripts/check_command_permission_route_gate_bound_identity_sources.py` accepts the same
  post-evidence blocker as locked planning. This is not runtime authorization and does not
  create server-operation authority.
- `scripts/check_public_sdk_v1_completion.py` now rejects optimistic/minimal player
  identity contract reports unless they retain `next_blocker=identity_public_contract_gate`
  and unresolved `privacy.identifier_redaction`.

At this historical checkpoint, the default route remained blocked at
`lifecycle_anchor_first_evidence_provenance_unbound`; the transient bound route without
approved runtime evidence remained blocked at `approved_runtime_evidence_missing`. Later
repo-local source-bound planning artifacts closed the default-route provenance blocker;
the current default route is documented in the later
`Default Identity Planning-Source Provenance Closure` section.

This round still does not approve runtime work, public identity, public permissions/admin,
command response, commands/replies, public header symbols, release readiness, or a stable
SDK claim.

## Route Lock And Identity Evidence Shape Hardening

The next supervised P0 round tightened the post-evidence route lock and the identity
structured-evidence shape:

- Four read-only sub-agent scopes were lead-delegated and closed: route/accounting,
  permissions/admin dependency evidence, side-lane SDK accounting, and handoff/research
  continuity.
- `scripts/check_command_permission_route_gate.py` now computes
  `route_lock.blocked_until` without duplicate entries. The post-approved-runtime-evidence
  blocker `identity_public_contract_gate_missing` reports only
  `[reviewed_identity_public_contract]`; no-runtime-evidence bound planning still reports
  `[approved_runtime_principal_lifecycle_evidence, reviewed_identity_public_contract]`.
- `scripts/check_command_permission_route_gate_bound_identity_sources.py` accepts the
  deduped post-evidence route-lock shape and still requires locked/planning-only posture.
- `scripts/check_public_sdk_v1_completion.py` now rejects player-identity contract
  structured evidence unless the public-contract readiness report preserves the full
  blocker set from the producer, has `blockers=[]`, and reports
  `resolved_inputs=[runtime.lifecycle_evidence]`. A report truncated to only
  `privacy.identifier_redaction`, or one with checker blockers, is not promotion evidence.
- P0 accounting has direct regression coverage that
  `identity_public_contract_gate_missing` does not count toward complete SDK progress.

Deferred side-lane finding: `check_mission_transfer_dino_tribe_v1_outcome_accounting.py`
is stricter than top-level SDK release-statement matching because it requires explicit
mission, transfer, dino-policy, tribe-policy, and buff-status leaf outcomes. The next
side-lane guardrail should wire that checker into `check_public_sdk_v1_completion.py`
similarly to inventory copied signals and ResourceHandle/object identity, so umbrella
wording cannot satisfy top-level bookkeeping without leaf evidence.

This round still does not approve runtime work, public identity, public permissions/admin,
command response, commands/replies, Mission/Transfer/Dino/Tribe SDKs, public header
symbols, release readiness, or a stable SDK claim.

## Approved Evidence Operational-Window Projection Binding

The next supervised round closed the semantic-drop gap between an accepted
`window-manifest.env` check and the approved runtime principal lifecycle evidence
manifest. The lead delegated four read-only scopes and kept integration ownership:

- approved-manifest `operational_window` projection audit;
- replay attack-path audit;
- live-ops authorization safety audit;
- handoff and knowledge-continuity audit.

Integrated changes:

- `check_player_identity_runtime_principal_lifecycle_window_manifest.py` now emits the
  exact approval boundary, approved window, actual capture window, rollback window,
  `notice_sent`, `log_budget`, and fixed window non-claims in its JSON report.
- `build_player_identity_runtime_principal_lifecycle_approved_manifest.py` now requires
  those fields before projection and embeds them in
  `operational_window`. Beta-user windows still require `notice_sent=true`.
- `check_player_identity_runtime_principal_lifecycle_approved_evidence.py` now allows,
  validates, and replay-compares those fields. `log_budget` must be `"10"`, approval
  must remain `current-turn operator-approved runtime window, not standing approval`,
  window timestamps must be UTC-shaped, and window non-claims must match the fixed
  non-authorization set.
- A guardrail test now requires
  `set(OPERATIONAL_WINDOW_REPLAY_KEYS) == set(ALLOWED_OPERATIONAL_WINDOW_KEYS)` so future
  approved-evidence `operational_window` fields cannot be added without replay coverage.
- `build_player_identity_runtime_principal_lifecycle_evidence_bundle.py` now preserves
  `log_budget` and window non-claims in the bundle report's compact operational-window
  summary.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_build_player_identity_runtime_principal_lifecycle_approved_manifest scripts.test_build_player_identity_runtime_principal_lifecycle_evidence_bundle`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_runtime_principal_lifecycle_window_manifest`

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Inventory/Items SDKs, Structure SDK, Mission/Transfer/Dino/Tribe SDKs,
ResourceHandle, release readiness, or a stable SDK claim.

## Runtime Principal Lifecycle Request Brief Hardening

The next P0 preparation round tightened the future player-principal lifecycle runtime
evidence request and replay path without authorizing runtime. The lead delegated four
read-only scopes and kept integration ownership:

- live-ops brief completeness;
- runtime observer safety;
- approved-evidence bundle/replay provenance;
- handoff and knowledge-continuity audit.

Integrated changes:

- `scripts/prepare_player_principal_lifecycle_window_request.py` now emits a structured
  `operator_live_ops_brief` inside `window-request.json`. The brief records target
  instance/map, reviewed `ShooterGameServer` path plus SHA, feature gates, exact marker
  set and forbidden marker list, observer env snapshot, start/restart/stop window, notice
  path, evidence capture paths, rollback, post-run stable posture, and explicit
  non-authorization.
- `scripts/check_player_principal_lifecycle_window_request.py` validates that brief
  exactly and keeps request-pack acceptance as pre-window planning only. The request pack
  now also records and checks `server_binary_path`.
- `enable-inventory-action-redacted-observer` was added to the player-principal request
  pack forbidden marker list, matching wrapper/posture/preflight safety expectations.
- `scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py` now
  rejects request packs whose `obelisk_commit` or ARK binary SHA drift from the checked
  window manifest, and requires the canonical rollback delta
  `removed_observer_env_and_markers_preserved_disable_plugins`.
- `scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py` now
  allows, preserves, and validates that canonical rollback delta in
  `operational_window.rollback`.

Read-only findings preserved:

- Runtime observer exclusivity remains primarily enforced by the wrapper, preflight, and
  posture checkers rather than only by the observer translation unit. This is acceptable
  for the operational path, but future defense-in-depth could duplicate selected
  exclusivity checks in runtime if a wrapper bypass becomes realistic.
- Preflight sidecars are still not fully bound to run id, target map, copied log path,
  window manifest path, and request pack path. The next offline guardrail should extend
  preflight JSON output and window-manifest validation before any runtime request is made.
- No current-turn runtime/server approval exists. These request packs remain planning
  artifacts and their next blocker is operator current-turn runtime window approval.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_principal_lifecycle_window_request scripts.test_check_player_identity_runtime_principal_lifecycle_window_manifest`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_build_player_identity_runtime_principal_lifecycle_evidence_bundle scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence scripts.test_build_player_identity_runtime_principal_lifecycle_approved_manifest`

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Inventory/Items SDKs, Structure SDK, Mission/Transfer/Dino/Tribe SDKs,
ResourceHandle, release readiness, or a stable SDK claim.

## Lifecycle Anchor Snapshot Provenance Binding

The next P0-focused supervised round closed the remaining offline provenance gap for the
explicit bound player-identity route. The lead delegated four read-only scopes and kept
integration ownership:

- offline identity provenance audit;
- SDK-route overclaim audit;
- UE4 snapshot fixture/provenance audit;
- handoff and knowledge-continuity audit.

Integrated changes:

- `scripts/bind_player_identity_planning_sources.py` now resolves required accepted
  lifecycle anchors through the selected `--snapshot-root/manifest.json`, validates
  manifest schema/source/status and exact snapshot target identity, rejects duplicate or
  missing focal targets, rejects symlink/protected/out-of-root paths, hashes the real
  snapshot files, and fails closed when accepted `ShooterGameMode.HandleNewPlayer` or
  `ShooterGameMode.OnLogout` anchor `evidence.source_snapshot_sha256` is stale or
  missing.
- `scripts/build_player_identity_planning_source_manifests.py` now self-checks and emits
  `source_alignment.lifecycle_snapshot_root_binding` so generated planning artifacts show
  the snapshot-root binding used for the bound route.
- `scripts/check_command_permission_route_gate_bound_identity_sources.py` now enforces the
  same snapshot-root binding after schema/prebind validation and before lifecycle
  normalization, then emits `lifecycle_snapshot_root_binding` in the wrapper report.
- Tests cover successful explicit bound-route advancement, stale accepted-anchor snapshot
  hash rejection, missing focal snapshot rejection, duplicate focal manifest-row
  rejection, and builder report binding visibility.

Read-only findings preserved:

- The original gap was real: before this change, stale accepted-anchor snapshot hashes
  could still yield a valid explicit bound wrapper with
  `critical_path_phase.current_blocker=approved_runtime_evidence_missing`.
- The SDK-route audit found no guardrail path where this provenance fix promotes public
  SDK, runtime, permissions/admin, command response, or commands/replies readiness.
- The authoritative fixture resolution is manifest-based, not glob-based. Current focal
  snapshot file hashes are:
  `ShooterGameMode.HandleNewPlayer` =
  `a9b3049dc221f128924ff0c6eb45287bf630dfaea4e4ab33bbf93647a5d3361b` and
  `ShooterGameMode.OnLogout` =
  `e79e416a408bbe652a31f58c710cfeb03daa0acf2e0ebef55a7ba61c83a414aa`.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_command_permission_route_gate_bound_identity_sources scripts.test_build_player_identity_planning_source_manifests scripts.test_bind_player_identity_planning_sources`
- Real transient build plus bound wrapper:
  `build_valid=true`, `snapshot_binding_ready=true`, `route_valid=true`, and
  `route_current_blocker=approved_runtime_evidence_missing`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
  then remained default-planning-only at `lifecycle_anchor_first_evidence_provenance_unbound`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
  remains fail-closed with `stable_claim_allowed=false`.

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Inventory/Items SDKs, Structure SDK, Mission/Transfer/Dino/Tribe SDKs,
ResourceHandle, release readiness, or a stable SDK claim.

## Delegated Runtime And Inventory Guardrail Round

The next supervised round was delegated by the lead into four scoped read-only lanes:
live-ops P0 principal lifecycle evidence planning, runtime/ABI TimerManager audit,
identity public-contract sequencing, and inventory copied-signal guardrails. The lead
integrated only offline, low-risk changes; agents did not commit, push, touch servers, or
edit protected live paths.

Implemented guardrails:

- `PluginManagerTests` now covers gameplay-policy registration tracking failure with
  rollback-unregister failure on the inventory dispatcher and item-return dispatcher, not
  only the structure dispatcher. The orphaned dispatcher subscription is inert during
  dispatch and is removed by `UnloadAll()`.
- `check_inventory_item_copied_signals_stability.py` now pins inventory copied-signal
  public evidence to `minimal-second-source-intake` and `item-return-only-policy-slice`,
  requires `inventory-action-compact-intake` to remain excluded, and requires the same
  release-readiness target set list in `docs/public_sdk_surfaces.json`.
- Inventory/item copied-signal public-claim scanning now treats raw identity/action-param
  terms such as `ItemId`, `ItemID1`, `InventoryComp`, `anActor`, `ItemNetID identity`,
  server request action params, and raw params as forbidden positive public claims.
- The Inventory/Items public-contract boundary test now scans JSON `resource_contract`,
  `scope`, `inventory_sdk`, `item_module_sdk`, and `support_tier` fields in addition to
  public contract payload fields.

Read-only findings preserved for the next focused rounds:

- Live-ops P0 runtime evidence remains planning-only. Any future approved copied runtime
  principal lifecycle evidence request must name exact target instance/map, run id,
  binary SHA, reviewed Obelisk commit, UTC window, restart expectation, final posture,
  user policy/notice path, copied evidence dir, rollback owner/delta, exact observer env,
  exact markers, and post-copy manifest checks. No runtime approval exists from this
  planning brief.
- TimerManager audit found no confirmed bug in owner validation, callback exception
  handling, owner cleanup, ABI flag validation, or unload/init-failure cleanup. The
  actionable test gap is a repeating timer with an in-flight callback during
  `PluginManager::UnloadAll()` to prove cleanup waits, does not `dlclose` early, and does
  not reschedule.
- Identity public-contract sequencing remains blocked after runtime evidence: resolving
  `approved_runtime_evidence_missing` should advance to
  `identity_public_contract_gate_missing`, not public SDK readiness. Permissions/admin
  must remain blocked until identity has a reviewed public contract, capability, ABI,
  lifecycle cleanup, and SDK consumer coverage.

Validation:

- `cmake --build build --target plugin_manager_tests -j$(nproc) && ./build/plugin_manager_tests`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_inventory_item_copied_signals_stability scripts.test_inventory_items_public_contract_boundary`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_inventory_item_copied_signals_stability.py --json`

This round does not approve runtime work, public identity, public permissions/admin,
command replies, Inventory/Items SDKs, Structure SDK, Mission/Transfer/Dino/Tribe SDKs,
ResourceHandle, release readiness, or a stable SDK claim.

## Timer Cleanup And Release/Runtime Evidence Guardrail Round

The next supervised round used four read-only agents for live-ops evidence route audit,
identity/permissions public-contract audit, offline identity provenance audit, and SDK
release overclaim audit. The lead integrated only offline changes and did not touch
servers, `/servidor/ark`, markers/env, Discord, GitHub publication, or release refs.

Integrated changes:

- `PluginManagerTests` now covers a plugin-owned repeating timer whose callback is
  in-flight while `PluginManager::UnloadAll()` runs. The test proves unload reaches
  shutdown, does not close the plugin while the callback is blocked, waits for callback
  completion, unregisters owner callbacks, and does not reschedule the repeating timer
  after cleanup.
- The short `scripts/check_player_principal_lifecycle_window_manifest.py` entry point is
  now the canonical route for player-principal lifecycle window manifest checking in the
  evidence bundle builder and approved-evidence replay. It re-exports the long checker's
  replay API so consumers can use the exact operator-facing artifact name.
- Permissions/admin public-readiness tests now pin that even a promoted-looking
  `obelisk.player_identity.v1` row with accepted runtime evidence and readiness
  overclaims remains blocked from permissions/admin readiness unless the public identity
  contract is actually promoted.
- Scoped release-statement validation now rejects broad claim variants such as
  `SDK v1.0: stable.`, `complete-SDK is available`, `GA SDK is published`, and
  `1.0 stable SDK is ready`. The package manifest schema doc is included in the broad
  v1-completion claim scan without treating the schema's enumerated blocked surfaces as
  public promotion claims.

Read-only findings preserved:

- Identity/permissions audit found no direct bypass: approved runtime principal lifecycle
  evidence remains only a contract-review input and does not imply public identity ABI,
  permissions/admin readiness, runtime readiness, or public SDK readiness.
- The remaining P0 offline provenance gap is lifecycle-anchor snapshot binding. Current
  source binding checks artifact ids, but accepted `ShooterGameMode.HandleNewPlayer` and
  `ShooterGameMode.OnLogout` anchor `source_snapshot_sha256` values should be checked
  against the actual `--snapshot-root` files before a bound route advances to the final
  `approved_runtime_evidence_missing` posture.

Validation:

- `cmake --build build --target plugin_manager_tests -j$(nproc) && ./build/plugin_manager_tests`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_permissions_admin_public_readiness scripts.test_check_player_principal_lifecycle_window_manifest scripts.test_check_public_sdk_v1_completion`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_public_sdk_guardrails`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_inventory_item_copied_signals_stability scripts.test_inventory_items_public_contract_boundary scripts.test_agent_handoff_guardrails`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`

At this checkpoint, the default command/permission route remained valid only as planning,
with `promotion_ready=false` and the then-current blocker
`lifecycle_anchor_first_evidence_provenance_unbound`. The SDK completion checker remained
fail-closed with `stable_claim_allowed=false`. This round still did not approve runtime
work, public identity, public permissions/admin,
command replies, Inventory/Items SDKs, Structure SDK, Mission/Transfer/Dino/Tribe SDKs,
ResourceHandle, release readiness, or a stable SDK claim.

## Delegated Route Runtime Rollback Hardening

The next delegated round kept the lead-owned integration model and split four scoped
tasks across sub-agents:

- Command route readiness binding: `scripts/check_command_permission_route_gate.py` now
  rejects command response child reports whose embedded readiness path is not bound to
  their embedded readiness root, or whose embedded readiness context disagrees with the
  route caller. This tightens composition without changing the route from planning-only
  evidence.
- Item-return side-lane overclaim closure:
  `scripts/check_item_return_only_readiness.py` now rejects positive status strings in
  public gameplay metadata that imply public SDK, runtime, ResourceHandle, v1, release,
  or promotion readiness. Scoped non-ready status text remains acceptable.
- Player-identity offline next action:
  `scripts/check_player_identity_first_evidence_readiness.py` now emits a structured
  `planning_provenance.next_action` when the active blocker is
  `lifecycle_anchor_first_evidence_provenance_unbound`. The only recommended step is to
  regenerate or select lifecycle/principal planning manifests bound to the current
  first-evidence source, then run the bound identity route wrapper. The expected next
  blocker after correct alignment is `approved_runtime_evidence_missing`.
- Runtime/ABI rollback hardening: `core/PluginManager.cpp` now makes released public
  chat and gameplay-policy callback state inert before rollback after public tracking
  failure. If dispatcher rollback unregister also fails, any retained internal
  subscription cannot invoke plugin code and owner cleanup still removes it.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_command_permission_route_gate scripts.test_check_item_return_only_readiness scripts.test_check_player_identity_first_evidence_readiness`
- `cmake --build build --target plugin_manager_tests -j$(nproc) && ./build/plugin_manager_tests`
- `cmake --build build -j$(nproc)`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
- `git diff --check`

At this checkpoint, the default route remained planning-only with then-current blocker
`lifecycle_anchor_first_evidence_provenance_unbound`. SDK completion remained fail-closed:
`stable_claim_allowed=false`, complete-SDK progress `0/12`, and P0 progress `0/4`.
This round does not approve runtime work, public identity, public permissions/admin,
command response, command replies, Inventory/Items SDKs, Structure SDK,
Mission/Transfer/Dino/Tribe SDKs, ResourceHandle, release readiness, or a stable SDK
claim.

## Player Identity Planning Source Producer

The next delegated P0 identity round converted the deferred offline next action into a
deterministic producer:

- Added `scripts/build_player_identity_planning_source_manifests.py`.
- The producer rebuilds `players-identity-first-evidence.json` from sanitized UFunction
  snapshots, constructs accepted candidate-only lifecycle anchors for
  `ShooterGameMode.HandleNewPlayer` and `ShooterGameMode.OnLogout`, constructs the
  candidate-only opaque principal invalidation policy, binds the principal source to the
  lifecycle artifact identity, and validates all generated manifests with the existing
  first-evidence, lifecycle, principal, and binder checks before writing output.
- Added `scripts/test_build_player_identity_planning_source_manifests.py` covering the
  source-aligned build, bound route proof, protected output rejection, symlink output
  rejection, and missing focal lifecycle snapshot failure.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_build_player_identity_planning_source_manifests scripts.test_bind_player_identity_planning_sources scripts.test_check_player_identity_first_evidence_readiness scripts.test_check_command_permission_route_gate_bound_identity_sources`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile scripts/build_player_identity_planning_source_manifests.py scripts/test_build_player_identity_planning_source_manifests.py`
- A transient run of `scripts/build_player_identity_planning_source_manifests.py --output-dir <tmp>/planning --json` followed by `scripts/check_command_permission_route_gate_bound_identity_sources.py --lifecycle-anchor-candidates-manifest <tmp>/planning/players-identity-lifecycle-anchor-candidates.json --principal-invalidation-policy-manifest <tmp>/planning/players-identity-principal-invalidation-policy.json --json`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`

The transient bound route proof returned `valid=true`, `blockers=[]`, and
`critical_path_phase.current_blocker=approved_runtime_evidence_missing`, with
`promotion_ready=false`, `public_sdk_ready=false`, `runtime_ready=false`,
`runtime_work_authorized=false`, and `server_operations_authorized=false`. The default
route remained planning-only at `lifecycle_anchor_first_evidence_provenance_unbound`
unless explicit aligned manifests were supplied. SDK completion remained fail-closed:
`stable_claim_allowed=false`, complete-SDK progress `0/12`, and P0 progress `0/4`.

This round does not approve runtime work, public identity, public permissions/admin,
command response, command replies, Inventory/Items SDKs, Structure SDK,
Mission/Transfer/Dino/Tribe SDKs, ResourceHandle, release readiness, or a stable SDK
claim. The next true blocker is approved copied runtime principal lifecycle evidence,
which still requires a fresh scoped live-ops brief before any marker/env/server/runtime
action.

## Delegated Guardrail And Plugin Retention Hardening

A later supervised round delegated four scoped audits/workers after compaction:

- A P0 route/progress read-only audit found no remaining route-gate accounting bypass
  after the previous `approved_runtime_evidence_missing` closure. P0 rows still require
  promoted evidence, structured evidence, release-statement agreement, satisfied
  dependencies, and an unlocked non-planning route gate before they can count.
- P0 executed-test evidence now rejects malformed SHA-256 digest fields. Top-level
  output/provenance hashes and nested `output.hash`/`output.sha256`/`output.digest` or
  `provenance.*` digests must be valid SHA-256 values, not merely non-empty strings.
  Residual risk: a fully hand-authored artifact with valid schema, current commit, bound
  canonical input hashes, exit code `0`, and valid digest remains indistinguishable from
  a genuine execution transcript until a dedicated runner/transcript flow exists.
- Offline artifact validation now recursively rejects generic true public/runtime/
  release/v1/SDK/promotion claim aliases in candidate and consume artifacts, including
  nested `public_sdk_ready`, `runtime_ready`, `v1_complete`, and `complete_sdk` fields.
  ResourceHandle-specific aliases remain intentionally outside the generic set where a
  schema has an explicit promote-mode ResourceHandle evidence path.
- A runtime/C ABI audit found a real retry-state bug in `PluginManager::UnloadAll()`: if
  a later plugin was already retained for retry and a subsequent plugin's retention
  tracking failed, the old abort path erased the processed tail before publishing the
  retained vector. The fix rebuilds retry state from the unprocessed prefix plus retained
  plugins in original order. Regression coverage uses delayed retention-failure injection.
- Public `CallProcessEvent` docs/header text now matches the implementation: the legacy
  ABI v1 slot is init-window debug-only, post-init calls through captured API tables fail
  closed, and callback/runtime execution requires a future owner-token ABI.

Validation:

- `cmake --build build --target plugin_manager_tests -j$(nproc) && ./build/plugin_manager_tests`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_validate_offline_artifact_gate`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
- `git diff --check`

At this checkpoint, the default route remained planning-only at
`lifecycle_anchor_first_evidence_provenance_unbound`. SDK completion remained fail-closed:
`stable_claim_allowed=false`, complete-SDK progress `0/12`, and P0 progress `0/4`. This
round does not approve runtime work, public identity, public permissions/admin, command
response, commands/replies, release readiness, or a stable SDK claim.

## Executed-Test Artifact, Route-Gate, Release-Readiness, And ABI Rollback Closure

The next supervised round closed four audit findings and added one runtime-core
regression test without changing SDK readiness:

- Promoted P0 `executed_test_report` evidence in
  `scripts/check_public_sdk_v1_completion.py` must now be a repo-relative JSON artifact
  using schema `obelisk.promoted-surface-test-execution-artifact.v1`. The artifact must
  match the promoted surface id, name the current repository HEAD through one of the
  accepted commit keys, include a nonempty command or argv, report `exit_code=0`, and
  include a nonempty output/provenance hash. Inline
  `obelisk.promoted-surface-test-execution.v1` objects no longer satisfy player identity,
  permissions/admin, command response, or commands/replies structured evidence.
- P0 completion accounting now receives the command/permission route-gate state. While
  this checkpoint's default route remained `lifecycle_anchor_first_evidence_provenance_unbound`, P0 rows
  expose `route_gate_claim_satisfied=false` and cannot increment complete-SDK or P0
  promoted counts even if promoted-looking local evidence is present. If such rows appear,
  the report emits `p0_dependency_chain_route_gate_locked`.
- Release-statement broad-claim scanning now treats `not only`, `not merely`, `not just`,
  and `not simply` as affirmative context instead of safe negation. Scoped release
  statements containing phrases such as `Not only is Inventory SDK ready for v1` are
  rejected.
- `scripts/check_release_readiness.sh` now rejects thin second-source readiness JSON that
  only says `promotion_gate.ready=true` with empty blockers. Accepted readiness reports
  must keep the layout-only/non-promotion envelope:
  `ready_scope=layout_only`, `layout_ready=true`, `promotion_ready=false`,
  `public_sdk_ready=false`, `runtime_ready=false`,
  `evidence_scope=second_source_layout_evidence_only`, non-promoted surfaces, and
  non-claims.
- `PluginManagerTests` now covers public `GameplayPolicyEvent` multi-dispatcher rollback.
  A test-only seam injects ItemReturn registration failure after earlier Structure and
  Inventory registrations. `RegisterGameplayPolicyEventWithOwnerTokenHandle(... MASK_ALL
  ...)` returns `0`, and Structure, Inventory, and ItemReturn subscription counts remain
  zero.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile scripts/check_public_sdk_v1_completion.py scripts/test_check_public_sdk_v1_completion.py`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion`
  passed with 133 tests.
- `bash scripts/test_check_release_readiness_options.sh` passed.
- `cmake --build build --target plugin_manager_tests` passed.
- `./build/plugin_manager_tests` passed.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
  passed as planning-only with then-current blocker
  `lifecycle_anchor_first_evidence_provenance_unbound`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
  still failed closed as expected with `stable_claim_allowed=false`, complete-SDK
  progress `0/12`, and P0 progress `0/4`.
- `git diff --check` passed.

Remaining risks:

- P0 promotion artifacts are now harder to replay, but future promoted artifacts should
  still prefer canonical producer outputs or checker-rerun binding over manually authored
  local JSON.
- The default route remains blocked on source-bound lifecycle-anchor/principal-policy
  planning provenance. Do not treat the new executed-test artifact contract as a route
  unlock.
- Second-source readiness acceptance is now fail-closed for the layout-only envelope, but
  future producer changes should keep this boundary in both generated reports and release
  gate validation.

This round still does not approve runtime work, public identity, public permissions/admin,
command response, commands/replies, Inventory/Items SDKs, Structure SDK,
Mission/Transfer/Dino/Tribe SDKs, ResourceHandle, release readiness, or a stable SDK
claim.

## Executed-Test Replay And Artifact-Gate Promote-Mode Closure

The next supervised round split four scopes across sub-agents and closed two additional
replay/promote-mode gaps while preserving fail-closed SDK accounting:

- `scripts/check_public_sdk_v1_completion.py` now requires promoted P0 executed-test
  artifacts to include canonical provenance:
  `producer=obelisk.promoted-surface-test-execution-runner.v1`,
  `checker=scripts/check_public_sdk_v1_completion.py`, and ISO-like `produced_at_utc`.
  The same artifacts must bind inputs for `docs/public_sdk_surfaces.json` and
  `include/obelisk/ObeliskApi.h` by repo-relative path and current SHA256. Otherwise
  well-shaped local JSON artifacts no longer satisfy P0 structured evidence.
- P0 row accounting now treats route-gate satisfaction as fail-closed. A P0 row cannot
  count while the route gate is planning-only, locked, invalid, has blockers, carries any
  current blocker, or lacks promotion/public/runtime readiness. This explicitly covers
  both the default `lifecycle_anchor_first_evidence_provenance_unbound` blocker and the
  explicit bound-route `approved_runtime_evidence_missing` blocker.
- `scripts/validate_offline_artifact_gate.py` now blocks every
  `obelisk.reflection-snapshot-readiness.v1` report in promote mode, including not-ready
  reports. It also rejects `promotion_ready`, `public_sdk_ready`, and `runtime_ready`
  overclaims on not-ready readiness reports.
- The real producer path,
  `scripts/compare_reflection_snapshots.py --readiness-report --json`, was audited. It
  already emits `evidence_scope=second_source_layout_evidence_only`,
  `not_promoted_surfaces`, `non_claims`, `ready_scope=layout_only` when ready,
  `layout_ready`, and false promotion/public/runtime readiness. No producer change was
  needed.
- The artifact-gate full suite exposed a test drift in command response route planning:
  `validate_offline_artifact_gate.py` called
  `check_command_chat_response_public_readiness.validate_readiness` without the now
  required `root` argument. The gate now passes `root=readiness_path.parent`.
  The same full-suite run exposed that imported approved player-identity runtime
  fixtures need the existing test-only
  `OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES=1` opt-in; the artifact-gate tests now set that
  env only around those fixture-backed tests.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion`
  passed with 135 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_validate_offline_artifact_gate`
  passed with 353 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
  still failed closed with `stable_claim_allowed=false`, complete-SDK progress `0/12`,
  P0 progress `0/4`, and then-current default blocker
  `lifecycle_anchor_first_evidence_provenance_unbound`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
  passed with `valid=true`, `planning_only=true`, `promotion_ready=false`, and then-current
  blocker `lifecycle_anchor_first_evidence_provenance_unbound`.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_compare_reflection_snapshots`
  was run by the readiness producer auditor and passed with 102 tests.
- `git diff --check` passed.

Remaining risks:

- The executed-test artifact schema is now stricter, but future promotion should still
  prefer a canonical runner that writes these artifacts from actual child check execution
  rather than hand-authored JSON.
- The route-gate accounting rule is intentionally conservative. Future work that wants P0
  rows to count must first introduce a non-planning unlocked route-gate state with no
  blocker and explicit promotion/public/runtime readiness semantics.

This round still does not approve runtime work, public identity, public permissions/admin,
command response, commands/replies, Inventory/Items SDKs, Structure SDK,
Mission/Transfer/Dino/Tribe SDKs, ResourceHandle, release readiness, or a stable SDK
claim.

## Command/Replies Structured Promotion Evidence And Alias Closure

The next supervised round closed the remaining P0 synthetic promotion-accounting gap for
the command response and commands/replies dependency chain:

- `scripts/check_public_sdk_v1_completion.py` now requires promoted
  `obelisk.command_chat_response_path.v1` evidence to include a repo-relative
  `obelisk.command-chat-response-public-readiness-check.v1` report with planning-only
  false public/runtime/promotion flags, compared readiness status, blocked decisions
  status, planning/post-v1 surface status, and empty blockers. It also requires a
  structured `obelisk.promoted-surface-test-execution.v1` report for executed ABI and SDK
  consumer tests.
- Promoted `obelisk.commands_replies.v1` evidence now requires its structured
  `obelisk.commands-replies-public-readiness-check.v1` report, a structured
  command-response public-readiness dependency report, and an executed ABI/SDK test
  report. Prose terms and placeholder ABI/SDK paths alone no longer satisfy structured
  promotion evidence.
- Completion blocker accounting now records
  `structured_promotion_evidence_satisfied=false` and keeps
  `counts_toward_complete_sdk_claim=false` when a promoted row lacks structured evidence,
  even if generic evidence paths and all required semantic terms are present.
- Inventory copied-signal stability now rejects additional public gameplay event
  readiness aliases: `v1_sdk_ready`, `release_ready`, and `public_abi_ready`.
- ResourceHandle/object-identity readiness now rejects generic readiness booleans such as
  `public_sdk_ready`, `runtime_ready`, `promotion_ready`, `v1_sdk_ready`, `release_ready`,
  and `public_abi_ready` when they appear as extra metadata in the decisions payload or
  the ResourceHandle surface row.

Read-only side-lane audits still found two deferred guardrails:

- Wire `scripts/check_object_identity_resource_handle_public_contract_readiness.py` into
  SDK completion accounting, analogous to the inventory copied-signal checker, so complete
  SDK reports include ResourceHandle/object-identity posture.
- Tighten Structure census/build-policy readiness scanners for generic boolean aliases,
  status-string aliases such as `sdk_status=ready` or `promotion_status=promoted`, and
  build-policy public-contract/header aliases.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_inventory_item_copied_signals_stability scripts.test_check_object_identity_resource_handle_public_contract_readiness`

This round remains offline guardrail work only. It does not promote command response,
commands/replies, Inventory/Items SDKs, ResourceHandle, Structure SDK, runtime readiness,
release readiness, or a stable SDK claim.

## ResourceHandle Accounting, Structure Alias Closure, And Route-Gate Override Lock

The next supervised round closed the two deferred side-lane guardrails and one P0
direct-invocation bypass:

- `scripts/check_public_sdk_v1_completion.py` now runs
  `scripts/check_object_identity_resource_handle_public_contract_readiness.py` as part of
  SDK completion accounting, records the ResourceHandle/object-identity report, and fails
  closed if that checker emits invalid JSON, blockers, non-planning posture, public/runtime
  promotion flags, or ResourceHandle/object-identity overclaims.
- Structure census and build-policy offline-intake checkers now reject generic readiness
  aliases such as `sdk_ready`, `ready_for_promotion`, `public_abi_ready`,
  `structure_events_ready`, nested `public_sdk_gate.ready=true`, and status/string aliases
  such as `public-ready`, `sdk_status=ready`, `promotion_status=promoted`,
  `public_sdk_status=accepted`, or `Structure SDK ready`. Existing planning-only
  artifacts and negated non-claims remain accepted.
- SDK completion now rejects non-canonical `--command-permission-route-gate` paths unless
  `OBELISK_SDK_COMPLETION_ALLOW_ROUTE_GATE_OVERRIDE_FOR_TESTS=1` is set. This keeps direct
  checker invocations from replacing the real P0 child route with a self-consistent fake
  gate. Test fixtures still use the override explicitly when validating child-field
  rejection behavior.
- Commands/replies structured promotion evidence now accepts a complete nested
  `command_response_promotion_evidence` object, so future legitimate evidence can include
  command-response readiness plus its executed ABI/SDK test report. Without that object,
  the fallback remains fail-closed.

Deferred risks from this round:

- Inline `executed_test_report` objects still self-attest `status=passed` and existing
  file paths. Future promotion accounting should require repo-relative runner-emitted JSON
  artifacts carrying current HEAD, argv, exit code, and output/hash provenance.
- Public ABI tests should add a regression for `GameplayPolicyEvent` multi-dispatcher
  partial registration rollback, forcing a later dispatcher registration to fail/throw
  after an earlier family registered and asserting all family subscription counts return
  to zero.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_structure_census_readiness scripts.test_check_structure_build_policy_offline_intake`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_object_identity_resource_handle_public_contract_readiness.py --json`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`

The final SDK completion command still fails closed with `stable_claim_allowed=false`,
complete-SDK progress `0/12`, and P0 progress `0/4`. This round does not approve runtime
work, public identity, permissions/admin, command response, commands/replies,
Inventory/Items SDKs, Structure SDK, ResourceHandle, release readiness, or a stable SDK
claim.

## Player Identity Public Contract And Bound Planning Input Hardening

The next supervised P0 identity guardrail round closed two offline input-provenance and
overclaim gaps before the approved runtime evidence blocker can feed public contract
review:

- `scripts/check_player_identity_public_contract_readiness.py` now loads player identity
  public-contract decisions and private candidate contracts through symlink/protected-path
  safe JSON guards, emits structured blockers for rejected JSON inputs, and requires the
  scanned public header to resolve to canonical `include/obelisk/ObeliskApi.h`.
- The public-contract checker now rejects approved runtime evidence reports that try to
  carry `public_header_allowed=true`, matching the existing promotion/public-SDK/runtime
  overclaim guards.
- `scripts/check_player_identity_lifecycle_anchor_candidates.py` now rejects unexpected
  top-level fields and positive runtime/server/command/public-SDK text claims in
  lifecycle-anchor planning artifacts.
- `scripts/check_player_identity_principal_invalidation_policy.py` now rejects unexpected
  `lifecycle_layout_source` fields and no longer exempts that source from positive
  command/permission claim scanning.
- `scripts/bind_player_identity_planning_sources.py` therefore fails validation before
  writing bound lifecycle/principal outputs when a planning input tries to preserve
  runtime/server authorization claims.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_public_contract_readiness`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_lifecycle_anchor_candidates scripts.test_check_player_identity_principal_invalidation_policy scripts.test_bind_player_identity_planning_sources`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_public_contract_readiness scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence scripts.test_check_player_identity_first_evidence_readiness scripts.test_check_command_permission_route_gate scripts.test_check_command_permission_route_gate_bound_identity_sources scripts.test_check_public_sdk_v1_completion`

Deferred read-only audit findings for the next offline guardrail round:

- SDK completion promotion evidence should be bound to approved runtime/public-contract
  evidence and executed ABI/SDK tests rather than placeholder term-bearing files.
- SDK completion should either forward non-default manifest/header inputs into the route
  gate or reject non-default route-relevant inputs while route consistency is unproven.
- Approved runtime principal lifecycle evidence still needs stronger external capture and
  builder provenance binding before any future runtime evidence can be treated as more
  than consume-side review input.

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Inventory/Items SDKs, Structure SDK, Mission/Transfer/Dino/Tribe SDKs,
ResourceHandle, release readiness, or a stable SDK claim.

## Route And SDK Provenance Lock Hardening

The next supervised P0 guardrail round closed the route/SDK shallow-trust findings from
read-only audit:

- `check_command_permission_route_gate.py` now preserves the identity child checker's
  `blockers` list in `critical_path_phase.source_checker_blockers` and requires the
  allowed `source_checker_primary_blocker` to be present in that list. Identity child
  blockers are expected while identity remains blocked; the primary blocker must be
  provenance-backed rather than invented by the route gate.
- The route gate's `route_lock.locked` now reflects all aggregate route blockers, not only
  the isolated critical-path phase, so identity-mode drift cannot still publish a locked
  route posture.
- `check_command_permission_route_gate_bound_identity_sources.py` now rejects valid-looking
  route reports with non-empty route blockers, bound-route primary blocker drift,
  source-checker ready/status/internal-planning overclaims, or route-lock `locked` /
  `blocked_until` drift.
- `check_public_sdk_v1_completion.py` now rejects default route reports with non-empty
  route blockers, route-lock drift, stale `source_checker_next_blocker`, or source-checker
  ready/status/internal-planning overclaims even if the route report says `valid=true`.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_command_permission_route_gate`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_command_permission_route_gate_bound_identity_sources`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion`

Follow-up closure in the next offline guardrail round:

- `check_command_chat_response_public_readiness.py` now rejects symlink/protected
  `--public-header` inputs, requires the resolved scanned header to be the canonical
  `include/obelisk/ObeliskApi.h`, and validates that the decisions manifest's
  `public_header` declaration matches that canonical scanned header.
- `check_commands_replies_public_readiness.py` applies the same canonical public-header
  binding and rejects embedded command response reports whose `public_header_path` or
  `decisions_path` source artifact drifts from the canonical command response inputs.
- `check_permissions_admin_public_readiness.py` now uses the protected/symlink-safe JSON
  loader for `--decisions`, `--surfaces`, and `--query-failclosed-artifact`, returning
  structured blocker output instead of trusting symlinked or protected JSON inputs.
- `check_command_permission_route_gate.py` now has aggregate coverage that a fake
  `--public-header` fails through the downstream command response and commands/replies
  child checks.

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Inventory/Items SDKs, Structure SDK, Mission/Transfer/Dino/Tribe SDKs,
ResourceHandle, release readiness, or a stable SDK claim.

## Structured Player-Principal Preflight Sidecars

The next supervised round closed the deferred structured-preflight sidecar gap on the
future approved runtime principal lifecycle evidence path:

- `check_player_identity_runtime_principal_lifecycle_window_manifest.py` now requires
  structured `obelisk.player-principal-lifecycle-preflight.v1` JSON sidecars for
  `preflight-pre.json` and `preflight-post.json`. Legacy one-line text preflight sidecars
  fail closed even when the manifest SHA is refreshed.
- The window-manifest checker validates `ready=true`, `posture_check=accepted`, expected
  mode, target instance, reviewed ARK binary SHA, wrapper SHA shape, marker-dir instance
  binding, and observer-window env-file path/SHA against the manifest's
  `observer_env_path` and `observer_env_sha256`.
- Window-manifest reports now emit resolved paths for the manifest, request pack,
  observer env, and preflight sidecars so approved-evidence consumers do not interpret
  relative paths under a different cwd. Both the window checker and approved-evidence
  consumer require canonical preflight artifact filenames.
- `check_player_principal_lifecycle_preflight.sh` now rejects launch-posture env keys in
  observer-window mode, including `LD_PRELOAD`, `LD_LIBRARY_PATH`, `OBELISK_ROOT`,
  `OBELISK_PLUGIN_DIR`, `OBELISK_CONFIG_DIR`, `OBELISK_LOG_DIR`, and
  `OBELISK_STATE_DIR`.

Validation:

- `bash scripts/test_check_player_principal_lifecycle_preflight.sh`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_runtime_principal_lifecycle_window_manifest scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence scripts.test_build_player_identity_runtime_principal_lifecycle_approved_manifest scripts.test_build_player_identity_runtime_principal_lifecycle_evidence_bundle`

Deferred read-only audit findings for future offline guardrail rounds:

- Route/SDK provenance should bind child `primary_blocker` values to child blocker lists,
  stale child readiness/status fields, and route-lock `blocked_until` values.
- Closed in the downstream input provenance round: command response and commands/replies
  now reject fake public-header paths and bind response-path reports to canonical command
  response decisions/header source artifacts; permissions/admin now rejects symlinked or
  protected JSON inputs for decisions, surfaces, and query artifacts.

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Inventory/Items SDKs, Structure SDK, Mission/Transfer/Dino/Tribe SDKs,
ResourceHandle, release readiness, or a stable SDK claim.

## Player-Principal Preflight Sidecar Window Binding

The next supervised round closed the remaining stale/swapped preflight sidecar gap before
any runtime request. The lead delegated four read-only scopes and kept integration
ownership:

- preflight JSON schema/binding audit;
- window manifest and approved-evidence replay audit;
- live-ops/runtime authorization-safety audit;
- handoff and knowledge-continuity audit.

Integrated changes:

- `check_player_principal_lifecycle_preflight.sh --json` now accepts evidence-binding
  inputs for `--run-id`, `--target-map`, `--window-manifest`, `--copied-log`, and
  `--evidence-dir`/`--copied-evidence-dir`. `--target-map` binds the sidecar target
  without triggering procfs posture inspection, while `--map` keeps its existing
  running-process posture meaning.
- Evidence binding is all-or-nothing: partial binding args fail closed, unsafe target
  maps fail, and the copied evidence shape must be
  `.../live-validation-logs/<run-id>/`, with `Obelisk.log` and `window-manifest.env`
  beside each other under that directory.
- Structured preflight JSON now records `run_id`, flat legacy `instance`/`map`, canonical
  `target`, `window_manifest_path`, `copied_log_path`, `copied_evidence_dir`, and
  `checked_at_utc` in addition to the posture, binary, wrapper, marker, and env fields.
- `check_player_identity_runtime_principal_lifecycle_window_manifest.py` now validates
  those preflight anchors against the loaded manifest target, run id, resolved manifest
  path, copied log path, copied evidence directory, and UTC timestamp shape. A stale or
  swapped preflight sidecar fails even if `preflight_*_sha256` is recomputed in the
  manifest.
- Request-pack binding remains separate and indirect through the window manifest sidecar
  and request-check replay. Do not claim a `request_pack_path` field inside preflight
  JSON.

Validation:

- `bash scripts/test_check_player_principal_lifecycle_preflight.sh`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_runtime_principal_lifecycle_window_manifest`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_build_player_identity_runtime_principal_lifecycle_evidence_bundle scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence scripts.test_build_player_identity_runtime_principal_lifecycle_approved_manifest`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_principal_lifecycle_window_request`

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

## Player Identity Planning Source Binder

The follow-up identity round added an offline binder for the aggregate provenance gate:

- `scripts/bind_player_identity_planning_sources.py` consumes validated
  `obelisk.players-identity-first-evidence.v1`,
  `obelisk.players-identity-lifecycle-anchor-candidates.v1`, and
  `obelisk.players-identity-principal-invalidation-policy.v1` JSON inputs.
- The tool writes bound copies of the lifecycle-anchor and principal-policy planning
  artifacts, plus `player-identity-planning-source-binding-report.json`, to a validated
  output directory. It rejects protected output paths and symlink components, uses atomic
  canonical JSON writes, and records source/output SHA256s.
- The lifecycle output is rebound to first-evidence
  `artifact_identity.source_artifact_ids` and accepted anchor snapshot hashes. The
  principal output gains `lifecycle_layout_source.source_binding` for lifecycle schema,
  lifecycle source ids, accepted start targets, and accepted end targets.
- The binder verifies the outputs through
  `check_player_identity_first_evidence_readiness.planning_provenance_blockers(...)`.
  A successful report means aggregate planning provenance is aligned only; it does not
  provide approved runtime principal lifecycle evidence.
- Focused tests cover the real CLI output path, route aggregation moving from
  `lifecycle_anchor_first_evidence_provenance_unbound` to
  `approved_runtime_evidence_missing`, invalid first-evidence rejection, protected output
  rejection, self-consistent stale lifecycle source rejection, and principal source
  binding mismatch rejection.
- Route-gate consumption of bound lifecycle/principal artifacts is explicit. At this
  checkpoint, the default repo route still blocked on
  `lifecycle_anchor_first_evidence_provenance_unbound` until bound artifacts were
  supplied; later repo-local source-bound planning artifacts closed that default-route
  provenance blocker. With no approved runtime evidence, route aggregation may advance
  only to `approved_runtime_evidence_missing`.
- `scripts/check_command_permission_route_gate_bound_identity_sources.py` composes that
  explicit route without leaving durable artifacts: it builds transient first-evidence,
  binds supplied lifecycle/principal planning manifests in a private non-protected temp
  root, forces child temp writes under that temp root, and requires the route gate to
  remain valid/planning-only with explicit-wrapper blocker `approved_runtime_evidence_missing`.
- The route-gate passthrough round found that real first-evidence can carry multiple
  complete `artifact_sha256`/`capture_id`/`evidence_pack_id` source triples. The lifecycle
  checker now accepts multiple complete triples while still rejecting incomplete or
  mismatched source-id counts, so the binder can preserve exact first-evidence provenance.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_bind_player_identity_planning_sources scripts.test_check_player_identity_first_evidence_readiness`

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Inventory/Items SDKs, Structure SDK, Mission/Transfer/Dino/Tribe SDKs,
ResourceHandle, release readiness, or a stable SDK claim.

## Bound Route And Runtime Window Preflight Guardrails

The next supervised round tightened the offline bridge between bound identity planning
sources and a future runtime principal lifecycle window:

- `prepare_player_principal_lifecycle_window_request.py` and
  `check_player_principal_lifecycle_window_request.py` now emit explicit false
  authorization/readiness flags on accepted request-pack reports:
  `server_operations_authorized=false`, `runtime_work_authorized=false`,
  `publication_authorized=false`, and all promotion/public/runtime/v1 readiness flags
  false. A ready request pack is still only pre-window planning and its next blocker
  remains `operator_current_turn_runtime_window_approval_required`.
- `check_player_identity_runtime_principal_lifecycle_window_manifest.py` now validates
  the real text line emitted by `check_player_principal_lifecycle_preflight.sh`, including
  the reviewed ARK `binary_sha256`. Legacy one-line preflight text without the binary hash
  and refreshed sidecars with a wrong binary hash fail closed.
- `check_command_permission_route_gate.py` enforced the then-current route mode split:
  before default source-bound artifact generation, the default route had to remain blocked
  at `lifecycle_anchor_first_evidence_provenance_unbound`, while a route with explicit
  bound lifecycle/principal manifests had to advance only to `approved_runtime_evidence_missing`.
- `check_public_sdk_v1_completion.py` now records the default route gate's
  `current_blocker`, `source_checker_primary_blocker`, and `route_lock.blocked_until`,
  and rejects SDK completion if the default route drifts away from
  `lifecycle_anchor_first_evidence_provenance_unbound`.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_prepare_player_principal_lifecycle_window_request scripts.test_check_player_principal_lifecycle_window_request scripts.test_check_player_identity_runtime_principal_lifecycle_window_manifest`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_command_permission_route_gate scripts.test_check_command_permission_route_gate_bound_identity_sources`

Closed in later guardrail rounds: runtime preflight sidecars are now structured JSON and
the later sidecar window-binding round requires run id, target map, copied log, copied
evidence dir, manifest path, and UTC check timestamp to match the window manifest before
approved evidence can consume the window.

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Inventory/Items SDKs, Structure SDK, Mission/Transfer/Dino/Tribe SDKs,
ResourceHandle, release readiness, or a stable SDK claim.

## Approved Runtime Evidence Review Provenance Guardrails

The next supervised round tightened the consume-side checker and test fixtures for the
future approved player-principal lifecycle evidence path:

- `check_player_identity_runtime_principal_lifecycle_approved_evidence.py` now requires
  `approval.reviewed_by` and `approval.review_note` to be present, strings, and non-blank.
  It rejects identity/UE-internal approval review text with the same strict posture as the
  approved-manifest builder, including negated phrases such as `does not expose Steam IDs`.
- The approved-evidence readiness scanner now normalizes whitespace and splits negation
  scope on comma and conjunction boundaries such as `and`, `but`, `while`, `however`, and
  `then`, so `does not promote identity and public SDK ready` and tabbed `public SDK ready`
  variants fail closed instead of inheriting an unrelated negative clause.
- `check_player_identity_runtime_principal_lifecycle_window_manifest.py` now compares the
  request-pack JSON's `copied_log_path`, `copied_evidence_dir`, and
  `window_manifest_path` against the copied log and current `window-manifest.env` being
  checked, so a structurally valid stale request pack cannot describe a different
  approved-workspace evidence path.
- Builder and bundle tests now use future run ids, current request-pack shape, reviewed
  binary SHA preflight text, and test-workspace replay flags so producer-shaped manifests
  are exercised against the stricter consumer.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_runtime_principal_lifecycle_window_manifest`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_build_player_identity_runtime_principal_lifecycle_approved_manifest`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_build_player_identity_runtime_principal_lifecycle_evidence_bundle`

This round still does not approve runtime work, public identity, public permissions/admin,
command replies, Inventory/Items SDKs, Structure SDK, Mission/Transfer/Dino/Tribe SDKs,
ResourceHandle, release readiness, or a stable SDK claim.

## SDK Completion Evidence Routing Hardening

The next SDK-completion guardrail round closed three fail-open paths in the v1 completion
checker:

- `scripts/check_public_sdk_v1_completion.py` now forwards the selected `--manifest` and
  `--public-header` into `scripts/check_command_permission_route_gate.py` as
  `--public-sdk-surfaces` and `--public-header`, so non-default completion invocations no
  longer validate aggregate SDK accounting against one manifest/header while the route gate
  checks repo defaults.
- `missing_required_contract_decision_manifests()` now validates required public-contract,
  route-guardrail, and planning decision manifests against the supplied
  `--contract-decisions-dir` even when that directory is non-default. Empty or partial
  custom decision directories therefore fail closed with
  `required_public_contract_decision_manifest_missing`.
- Promoted `obelisk.player_identity.v1` rows now require structured promotion evidence:
  repo-relative approved-runtime evidence checker report, repo-relative public-contract
  readiness checker report, and an executed-test report for ABI and SDK consumer tests.
  Placeholder files under `tests/core` and `tests/sdk_consumer` plus the required prose
  terms no longer clear promotion accounting; they trigger
  `promoted_surface_structured_evidence_missing`.

Read-only explorer agents confirmed the three audited gaps before integration:
placeholder promoted evidence could satisfy path/term checks, completion did not forward
non-default manifest/header inputs to the route gate, and non-default decision directories
skipped required-manifest enforcement. A fourth audit identified the player-identity
checker schemas and fields used for the new structured-evidence binding.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_command_permission_route_gate scripts.test_check_public_sdk_v1_completion`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
- `git diff --check`

At this checkpoint, the default route remained planning-only at
`lifecycle_anchor_first_evidence_provenance_unbound`. The default SDK completion check
still fails closed with `stable_claim_allowed=false`, complete-SDK progress `0/12`, and
P0 progress `0/4`. This round does not approve runtime work, public identity, public
permissions/admin, command response, commands/replies, release readiness, or a stable SDK
claim.

## Permissions Structured Evidence And Bound-Route Prebind Closure

The next supervised guardrail round extended the structured evidence pattern and tightened
the explicit bound identity route:

- Promoted `obelisk.permissions_admin.v1` rows in
  `scripts/check_public_sdk_v1_completion.py` now require structured evidence instead of
  accepting surface-specific placeholder ABI/SDK files plus the required prose terms.
  Required evidence includes a repo-relative
  `obelisk.permissions-admin-query-failclosed-contract-check.v1` consume report,
  a repo-relative `obelisk.permissions-admin-public-readiness-check.v1` planning report,
  and an executed ABI/SDK test report. These reports are prerequisites only: the current
  permissions/admin artifacts still keep `promotion_ready=false`, `public_abi_ready=false`,
  `public_sdk_ready=false`, and `runtime_ready=false`.
- `scripts/bind_player_identity_planning_sources.py` now validates prebind provenance
  before writing bound outputs. Lifecycle `artifact_identity.source_artifact_ids` must
  already match the selected first-evidence source, principal `start_anchor`/`end_anchor`
  must match accepted lifecycle targets, and an existing principal
  `lifecycle_layout_source.source_binding` must match the lifecycle source. The binder no
  longer silently normalizes stale standalone lifecycle/principal manifests into bound
  route evidence.
- The historical standalone lifecycle/principal bundle under
  `/servidor/ark/workspace-offline/player-identity-principal-invalidation-policy-20260531T231247Z/`
  remains consume-only planning evidence, but the stricter bound wrapper now rejects it
  with `lifecycle_anchor_source_artifact_ids_mismatch` when paired with the generated
  first-evidence source. A future bound-route run must regenerate or align the planning
  manifests to the first-evidence source before it may advance to
  `approved_runtime_evidence_missing`.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_bind_player_identity_planning_sources scripts.test_check_command_permission_route_gate_bound_identity_sources`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate_bound_identity_sources.py --lifecycle-anchor-candidates-manifest /servidor/ark/workspace-offline/player-identity-principal-invalidation-policy-20260531T231247Z/players-identity-lifecycle-anchor-candidates.json --principal-invalidation-policy-manifest /servidor/ark/workspace-offline/player-identity-principal-invalidation-policy-20260531T231247Z/players-identity-principal-invalidation-policy.json --json`

The last command is expected to fail closed on stale prebind provenance. This round does
not approve runtime work, public identity, public permissions/admin, command response,
commands/replies, release readiness, or a stable SDK claim.

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
planning-only. On the default repo route it can still be blocked by
`lifecycle_anchor_first_evidence_provenance_unbound`; with explicit bound identity
planning artifacts it may advance only to `approved_runtime_evidence_missing`.

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

## Mission Leaf Accounting Integration

The next delegated follow-up closed the mission/transfer/dino/tribe/buff accounting
gap found during route-lock hardening:

- `scripts/check_public_sdk_v1_completion.py` now runs
  `scripts/check_mission_transfer_dino_tribe_v1_outcome_accounting.py` and embeds its
  compact report under `mission_transfer_dino_tribe_outcome_accounting`.
- Default repo accounting stays `candidate_only`, `v1_accounted=false`, and
  `promotion_ready=false`, `public_sdk_ready=false`, `runtime_ready=false`.
- Mission umbrella release-statement wording no longer satisfies the exclusion contract
  unless it names explicit mission, transfer, dino-policy, tribe-policy, and buff-status
  outcomes.
- The integration rejects invalid checker output, schema/surface drift, missing required
  leaves, unexpected accounting routes, child blockers, and public/runtime/promotion
  overclaims unless the leaf route is explicitly promoted.
Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_mission_transfer_dino_tribe_v1_outcome_accounting`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_public_sdk_guardrails scripts.test_agent_handoff_guardrails`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`

The default SDK completion check still fails closed with `stable_claim_allowed=false`,
complete-SDK progress `0/12`, and P0 progress `0/4`. This round does not approve runtime
work, public identity, public permissions/admin, command response, commands/replies,
Mission/Transfer/Dino/Tribe/Buff SDKs, ResourceHandle, release readiness, or a stable
SDK claim.

## Permissions/Admin Identity Promotion Certificate Guardrail

The next delegated follow-up closed the permissions/admin dependency-evidence gap from
the mission-leaf accounting round:

- `scripts/check_public_sdk_v1_completion.py` now requires promoted
  `obelisk.permissions_admin.v1` structured evidence to include a matching
  player-identity promotion certificate.
- The certificate must identify `obelisk.player_identity.v1`, the expected P0 chain
  position before permissions/admin, and a reviewed artifact hash.
- Missing certificate, wrong surface, wrong chain position, artifact-hash drift, or
  invalid nested player-identity structured evidence keeps permissions/admin structured
  promotion evidence unsatisfied and non-counting.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_agent_handoff_guardrails`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
- `git diff --check`

This is accounting-only. It does not authorize runtime/server work, marker/env changes,
Discord, public identity, public permissions/admin ABI, command response,
commands/replies, ResourceHandle, release readiness, or stable/complete SDK wording.
At this checkpoint, default route and SDK accounting remained fail-closed with
`lifecycle_anchor_first_evidence_provenance_unbound`, `stable_claim_allowed=false`,
complete-SDK progress `0/12`, and P0 progress `0/4` at this checkpoint.

## Player-Principal Request/Window Preparation Guardrail

The next delegated follow-up hardened the offline preparation path for the future
approved player-principal lifecycle runtime evidence window:

- `prepare_player_principal_lifecycle_window_request.py` limits the first approved window
  to ten minutes, rejects restart/final-posture incoherence, and emits exact post-run
  verification commands in `operator_live_ops_brief`.
- `check_player_principal_lifecycle_window_request.py` validates those request-pack
  fields exactly: target instance/map, reviewed server binary path/SHA, Obelisk commit,
  env snapshot, marker and forbidden-marker boundaries, copied evidence/log paths, window
  manifest path, canonical rollback delta, final posture, and target-bound post-run
  checks.
- `check_player_identity_runtime_principal_lifecycle_window_manifest.py` now binds
  preflight sidecar `checked_at_utc` values to the manifest timeline:
  preflight-pre must fall between approved-window start and capture start, preflight-post
  must fall between capture end and rollback end, and pre/post ordering must be forward.
  Stale, late, or swapped sidecars fail even when their refreshed SHA is present.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_prepare_player_principal_lifecycle_window_request scripts.test_check_player_principal_lifecycle_window_request scripts.test_check_player_identity_runtime_principal_lifecycle_window_manifest`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_agent_handoff_guardrails scripts.test_check_command_permission_route_gate scripts.test_check_public_sdk_v1_completion`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
- `git diff --check`

This is offline request/window preparation only. It does not authorize runtime/server
work, `/servidor/ark` writes, marker/env changes, start/stop/restart, Discord,
publication, tags, release refs, public identity, permissions/admin ABI, command
response, commands/replies, public header symbols, ResourceHandle, release readiness, or
stable/complete SDK wording. Request-pack, preflight, and window-manifest readiness are
not approved runtime evidence. At this checkpoint, the default route remained
`lifecycle_anchor_first_evidence_provenance_unbound`; after the later default source-bound
artifact closure, a no-runtime route may only reach `approved_runtime_evidence_missing`,
and accepted runtime evidence may only advance to `identity_public_contract_gate_missing`.

## Command Response Readiness Provenance Guardrail

The next delegated follow-up closed the non-default synthetic command-response readiness
gap and added a P0 request-pack aggregate regression:

- `scripts/check_command_chat_response_public_readiness.py` now requires non-default
  readiness JSON to carry `source_root` matching the selected root and a producer block
  naming `scripts/compare_reflection_snapshots.py`, the
  `command-chat-response-route-planning` target set, `--readiness-report`, `--json`, and
  the canonical output name.
- `scripts/validate_offline_artifact_gate.py` requires that same provenance when
  validating command-response route readiness inside offline artifact manifests.
- `scripts/test_check_player_identity_first_evidence_readiness.py` now has a
  build-report-level regression proving that valid player-principal lifecycle
  request-pack/env inputs, with lifecycle/principal planning aligned but no approved
  runtime evidence, still leave top-level `approved_runtime_evidence_missing` and all
  public/runtime/promotion flags false.
- Runtime approved-evidence fixtures were aligned with preflight timeline binding so
  accepted runtime-evidence tests continue to prove only the runtime-evidence blocker,
  not public identity or SDK readiness.

Validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_command_chat_response_public_readiness scripts.test_check_player_identity_first_evidence_readiness scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_validate_offline_artifact_gate.ValidateOfflineArtifactGateTests.test_accepts_command_chat_response_route_planning_manifest_for_consume_mode scripts.test_validate_offline_artifact_gate.ValidateOfflineArtifactGateTests.test_blocks_command_chat_response_route_planning_manifest_in_promote_mode scripts.test_validate_offline_artifact_gate.ValidateOfflineArtifactGateTests.test_command_chat_response_route_manifest_fails_closed_on_overclaims_and_bad_layout`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`

Follow-up commands/replies hardening closed the deferred child-report location gap:

- `scripts/check_commands_replies_public_readiness.py` now requires
  `--response-path-report` to resolve exactly to
  `<response-path-report-root>/command-chat-response-public-readiness.json`, falling back
  to `--response-path-root` when no explicit report root is supplied.
- `scripts/check_command_permission_route_gate.py` preserves temp composition by writing
  the composed child report under its own temp report root and forwarding both
  `--response-path-report` and `--response-path-report-root`.
- Copied child reports outside the expected report root now fail with
  `response_path_report_path_mismatch`, even when their source artifacts rebuild
  identically.

Additional validation:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_commands_replies_public_readiness scripts.test_check_command_permission_route_gate`
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`

Structured promotion evidence for command response/replies now requires the same
source-artifact bindings used by the planning readiness checkers before those rows can
count toward SDK completion. Command response evidence must carry bound readiness,
decisions, surfaces, public-header paths, and readiness producer provenance; commands/
replies evidence must also bind its own decisions/surfaces/header paths plus the canonical
child response-path report root/name. This remains provenance-only and does not create
response/replies readiness while the route gate is locked and planning-only.

This round does not authorize runtime/server work, `/servidor/ark` writes, marker/env
changes, Discord, GitHub publication, release refs, public identity, permissions/admin
ABI, command response/replies readiness, ResourceHandle, or stable/complete SDK wording.
At this checkpoint, default route and SDK accounting remained fail-closed with
`lifecycle_anchor_first_evidence_provenance_unbound`, `stable_claim_allowed=false`,
complete-SDK progress `0/12`, and P0 progress `0/4`.

## Default Identity Planning-Source Provenance Closure

The follow-up default-route provenance pass generated repo-local, source-bound planning
artifacts under `docs/research/player-identity-planning-sources/`:

- `players-identity-first-evidence.json`
- `players-identity-lifecycle-anchor-candidates.json`
- `players-identity-principal-invalidation-policy.json`
- `player-identity-planning-source-manifests-report.json`

These artifacts are generated by
`scripts/build_player_identity_planning_source_manifests.py` from the current first-evidence
inputs and sanitized lifecycle snapshots. The lifecycle snapshot bindings checked by the
default route include:

- `ShooterGameMode.HandleNewPlayer` snapshot SHA-256
  `a9b3049dc221f128924ff0c6eb45287bf630dfaea4e4ab33bbf93647a5d3361b`
- `ShooterGameMode.OnLogout` snapshot SHA-256
  `e79e416a408bbe652a31f58c710cfeb03daa0acf2e0ebef55a7ba61c83a414aa`

Result: `scripts/check_command_permission_route_gate.py --json` now reports the default
no-runtime route as valid planning-only with
`critical_path_phase.current_blocker=approved_runtime_evidence_missing`, and the SDK
completion gate expects that blocker. This closes only the default identity planning-source
provenance gap. It does not approve runtime evidence, runtime/server work, public identity,
permissions/admin ABI, command response/replies readiness, public SDK readiness, promotion,
release readiness, or stable/complete SDK wording. SDK accounting remains fail-closed with
`stable_claim_allowed=false`, complete-SDK progress `0/12`, and P0 progress `0/4`.

## Runtime-Evidence Request Hygiene Hardening

The next delegated round split audit across live-ops request packs, SDK route/accounting,
identity public-contract privacy, and UE4/offline evidence. Integrated findings:

- `prepare_player_principal_lifecycle_window_request.py` must reject expired approved
  windows at generation time; relying on the checker to reject stale packs is too late for
  operator-facing next actions.
- `check_player_principal_lifecycle_window_request.py` must validate the exact
  `operator-approval-request.md` sidecar beside the request JSON/env, because the Markdown
  is the human approval artifact for any future live window.
- `build_player_identity_runtime_principal_lifecycle_evidence_bundle.py --preflight-only`
  must validate any present approved runtime manifest with the approved-evidence checker
  before reporting `approved_runtime_evidence_ready=true`; a present invalid JSON now routes
  to `approved_runtime_evidence_not_accepted`.
- `check_public_sdk_v1_completion.py` route-lock guidance now points to approved runtime
  principal lifecycle evidence and reviewed identity public contract, not the already closed
  bound lifecycle-anchor provenance step.

This is offline hygiene only. It does not authorize runtime/server work, marker/env edits,
Discord, public identity, public ABI/header readiness, permissions/admin, command response,
commands/replies, promotion, release readiness, or stable/complete SDK wording. The useful
next offline public-contract lane is an identity-specific `privacy.identifier_redaction`
policy/checker over sanitized snapshots only; more broad FName/GObjects/core/static
rediscovery is not useful for the current blocker.

## Identifier-Redaction And Route-Claim Guardrails

A follow-up delegated round split audit across identity/privacy, route/SDK accounting,
docs, and request-hardening tests. Integrated offline changes:

- Added `scripts/check_player_identity_identifier_redaction_evidence.py`, a standalone
  sanitized-manifest checker for `privacy.identifier_redaction` evidence. A passing report
  is contract-review evidence only: it keeps promotion, public SDK, runtime readiness, and
  public header readiness false and does not promote `obelisk.player_identity.v1`.
- Expanded `scripts/check_command_permission_route_gate.py` claim scanning so child
  reports that claim public SDK readiness, public-header readiness, v1 completion, or
  stable-claim allowance are rejected by the standalone route gate instead of only by the
  top-level SDK completion wrapper.
- Hardened player-principal request packs as pre-window-only artifacts: generation and
  checking now reject approved windows that have already started, not only windows whose
  end time has expired.

Validation added focused unit coverage for identifier-redaction evidence, route-gate
public SDK/v1/stable-claim overclaim scanning, and already-started approved-window
rejection. No runtime/server work, `/servidor/ark` writes, marker/env edits, Discord,
public ABI/header readiness, promotion, release readiness, or complete/stable SDK claim
was authorized. The route remains locked/planning-only at
`approved_runtime_evidence_missing`; complete-SDK progress remains non-counting until
approved runtime principal lifecycle evidence and reviewed identity public contract exist.

## Downstream Runtime-Request And SDK Accounting Guardrails

A follow-up delegated round split audit across identity/privacy integration, runtime
request replay, SDK accounting, and UE4/offline priority. Integrated offline changes:

- `docs/player_identity_public_contract_decisions.json` now records
  `identifier_redaction_evidence_intake` as an external manifest intake for
  contract-review evidence only. The readiness and gap checkers validate its checker path
  and false readiness flags, but it does not remove `privacy.identifier_redaction` from
  blockers and does not add public header/capability/callback symbols.
- Window-manifest replay, approved runtime evidence replay, and bundle preflight now have
  focused tests proving `operator-approval-request.md` drift is not hidden by request-pack
  expiry or transitive checks.
- Approved runtime manifest preflight now requires both checker `ready=true` and
  `exit_code=0` before `approved_runtime_evidence_ready` can be true.
- SDK completion now requires `completion_gate_accepted=true` from the route-gate wrapper
  before P0 rows can receive route-gate credit; a fake unlocked/ready route report that
  the wrapper rejects keeps P0 route credit false.

The UE4/offline audit found no broad dump/reversing task higher value than these
request/contract guardrails for the current blocker. This remains offline-only and does
not authorize runtime/server work, marker/env edits, Discord, publication, public ABI,
promotion, release readiness, or stable/complete SDK wording.

## Structure Exclusion Accounting And Scoped Statement Closure

A delegated Structure accounting round split review across SDK completion accounting,
release wording, P0 invariants, and focused test work. Integrated offline changes:

- `obelisk.structure_census.v1` is explicitly classified as `excluded` in
  `docs/public_sdk_surfaces.json`, removed from `planning_surfaces`, and included in
  `post_v1_or_excluded_surfaces` while staying in `v1_sdk_completion_blockers`.
- `release/v1/public-sdk/scoped-release-statement-template.md` now carries exact
  non-complete wording for Structure: no StructureEvents SDK, structure census, structure
  identity, structure lookup, build placement policy, no-collision policy, or ownership
  lookup API is included in v1.
- `scripts/check_structure_build_policy_offline_intake.py` now accepts either `planning`
  or `excluded` Structure status as non-promoting offline accounting, while still rejecting
  promoted/public/runtime/enforcement overclaims.
- Completion tests now prove the Structure exclusion is bookkeeping only: it does not
  count toward complete SDK progress, broad complete/full/production SDK wording is
  rejected, and imprecise Structure exclusion text fails the release-statement contract.

Validation remained offline-only. Targeted tests and checkers confirmed
`stable_claim_allowed=false`, complete SDK `0/12`, P0 `0/4`, and Structure census/build
policy public SDK/runtime/promotion/enforcement flags all false. No runtime/server work,
`/servidor/ark` writes, marker/env edits, Discord, public ABI/header readiness, promotion,
release readiness, or stable/complete SDK claim was authorized.

## Runtime Evidence Replay Receipt Hardening

A delegated runtime-evidence replay round split work across live-ops request-window audit,
approved-evidence manifest hardening, SDK/P0 invariants, and handoff durability. Integrated
offline changes:

- `check_player_principal_lifecycle_window_request.py` now rejects a completed
  `operator-approval-receipt.json` unless the checker is running in `--post-window-replay`
  mode. This keeps a pre-window request-pack check from treating receipt presence as
  runtime authorization.
- `check_player_identity_runtime_principal_lifecycle_window_manifest.py` now forwards
  `--post-window-replay --operator-approval-receipt <receipt>` to the nested request-pack
  checker during post-window manifest replay, aligning manifest replay with bundle
  preflight.
- `check_player_identity_runtime_principal_lifecycle_approved_evidence.py` now directly
  revalidates the operational-window receipt: `verified=true`, exact false scope and
  non-authorization flags, bound request/window/log fields, and request/env/operator
  request sidecar artifact hashes.
- `test_check_command_permission_route_gate.py` now exercises a real accepted approved
  runtime evidence manifest through the route gate and asserts it reaches only
  `identity_public_contract_gate_missing`, with route lock
  `blocked_until=[reviewed_identity_public_contract]`, P0 unlock flags false, and all
  public/runtime/promotion readiness flags false.

Validation remained offline-only. The request/window/approved-evidence suites passed, and
the route-gate regression confirmed approved runtime evidence is necessary but still
insufficient: the next blocker is reviewed identity public contract, not permissions/admin,
command response, commands/replies, public SDK readiness, runtime readiness, release
readiness, or complete/stable SDK wording. No runtime/server operation, marker/env change,
Discord, GitHub publication, or protected live-server operation was authorized.

## Public Contract Route Blocker And SDK Non-Counting Hardening

A delegated follow-up round split scope across public-contract gate audit, SDK/P0 route
accounting, approved-evidence negative regressions, and handoff durability. Required/used
skills were `obelisk-agent-handoff`, `obelisk-github-research-workflow`,
`obelisk-live-ops`, and `obelisk-continuous-learning`.

Integrated offline changes:

- `check_player_identity_public_contract_readiness.py` now separates the internal
  decision gate id `identity_public_contract_gate` from the route blocker
  `identity_public_contract_gate_missing`, and reports `public_contract_allowed=false`
  alongside other false public/runtime readiness flags.
- `check_public_sdk_v1_completion.py` now accepts the locked post-evidence route state
  `identity_public_contract_gate_missing` only when its route lock is
  `blocked_until=[reviewed_identity_public_contract]`; the state remains non-counting for
  complete SDK progress and P0 promotion.
- `test_check_player_identity_runtime_principal_lifecycle_approved_evidence.py` now adds
  negative regressions for edited receipt payload SHA drift, operator approval request
  sidecar mismatch, copied log path mismatch, and request artifact mismatch.
- Handoff/compact context now records delegated scopes, required/used skills, integrated
  findings, and pending findings so compaction does not erase coordination state.

These public-contract gap-report items were later integrated in the same supervised
goal: optional approved runtime evidence can now be consumed as contract-review input
only, custom private-candidate drift reaches nested layout/preflight checks, and
forbidden identity exposure scanning is clause-local. Validation remained offline-only.
No runtime/server operation, marker/env change, ReflectionScanner, ptrace/gcore,
Discord, GitHub publication, public ABI/header opening, promotion, release readiness, or
stable/complete SDK claim was authorized.

## Public Contract Gap Report Runtime-Input Hardening

A delegated follow-up round split scope across gap-report design, private-candidate drift
tests, SDK/P0 accounting audit, and offline reversing priority. Required/used skills were
`obelisk-agent-handoff`, `obelisk-github-research-workflow`, `obelisk-live-ops`,
`obelisk-continuous-learning`, and read-only reversing/tooling skills for the reversing
audit.

Integrated offline changes:

- `check_player_identity_public_contract_gap_report.py` now has optional
  `--approved-runtime-evidence`. Accepted evidence resolves only
  `runtime.lifecycle_evidence`, sets `runtime_evidence_missing=false`, reports
  `current_blocker=identity_public_contract_gate_missing`, keeps
  `blocked_until=[reviewed_identity_public_contract]`, and leaves promotion/public
  SDK/runtime/header readiness false.
- The same checker validates `approved_runtime_evidence_intake` id/status/resolved input,
  checker path, non-claim text, and false readiness flags in the public-contract decision
  manifest.
- Nested private POD layout and public ABI preflight validation now use the supplied
  `--private-candidate-contract` instead of silently reloading the default contract.
- Private-candidate forbidden exposure scanning is clause-local: negative non-claims such
  as `does not expose player names` remain allowed, but positive `SteamID` or
  `PlayerDataID` exposure followed by an unrelated `no lookup` clause fails.
- `check_player_identity_first_evidence_readiness.py` was updated to call the widened
  gap-report helpers while preserving the default pre-runtime `approved_runtime_evidence_missing`
  route.

Auditor findings:

- Reverse-engineering/offline dump audit found no useful broad FName/GObjects/core/admin
  or lifecycle-layout task left for this P0 blocker. Existing copied player-principal
  lifecycle artifacts cannot clear `approved_runtime_evidence_missing` because the
  canonical route shape is missing approved window/request/receipt evidence.
- SDK/P0 auditor recommended mixed P0 non-counting visibility for combinations of
  `identity_public_contract_gate_missing`, scoped P0 excluded/post-v1 release-statement
  records, and manifest-promoted-but-non-counting P0 rows. A later pass integrated that
  visibility; see the following section.

Validation remained offline-only. No runtime/server operation, marker/env change,
ReflectionScanner, ptrace/gcore, Discord, GitHub publication, public ABI/header opening,
promotion, release readiness, or stable/complete SDK claim was authorized.

## SDK/P0 Non-Counting Visibility And Identity Overclaim Hardening

A delegated follow-up round split scope across SDK/P0 implementation, identity-route
audit, reversing/offline evidence audit, and handoff/gate audit. The lead integrated the
code and kept all sub-agents out of GitHub, Discord, runtime/server operations, and
protected live-server writes.

Integrated offline changes:

- `check_public_sdk_v1_completion.py` now exposes per-row `non_counting_reasons`,
  `manifest_promoted_but_non_counting`,
  `release_statement_scoped_non_complete_bookkeeping`, and
  `route_gate_non_counting_blocker`. Summary/progress/report sections now surface P0
  manifest-promoted-but-non-counting rows, P0 scoped release-statement bookkeeping, non-P0
  post-v1/excluded bookkeeping, and route-gate non-counting blocker codes/surfaces.
- The SDK report's `next_v1_work.recommended_next_action` now changes from producing
  runtime lifecycle evidence to reviewing the player identity public contract when the
  route blocker is `identity_public_contract_gate_missing`.
- `check_player_identity_first_evidence_readiness.py` now treats approved-runtime evidence
  report drift in `public_header_allowed`, `public_abi_ready`, `v1_completion_ready`,
  `public_capability_bits_now`, and `public_callback_abi_now` as overclaims. Missing
  fields remain equivalent to closed/empty for compatibility.
- The first-evidence fallback blocker now uses the active route vocabulary
  `identity_public_contract_gate_missing`, not stale `identity_public_contract_gate`.

Offline reversing/evidence audit:

- The stale canonical 20260601 player-principal lifecycle directory under
  `/servidor/ark/workspace-offline/live-validation-logs/20260601T120000Z-player-principal-lifecycle`
  was checked with `build_player_identity_runtime_principal_lifecycle_evidence_bundle.py
  --preflight-only`. It remains insufficient: no `Obelisk.log`, `window-manifest.env`,
  completed `operator-approval-receipt.json`, or
  `approved-bundle/approved-runtime-principal-lifecycle-evidence.json`.
- A better-looking test-style tree under
  `/servidor/ark/workspace-offline/obelisk-test-player-principal-mkgkym0g/...` also stays
  insufficient because exact copied paths/sidecars do not match the canonical approved run
  binding. It should not be normalized into evidence.

Validation remained offline-only. `scripts.test_check_public_sdk_v1_completion` passed
178 tests after the SDK/P0 visibility patch; targeted identity-route overclaim tests also
passed. No runtime/server operation, marker/env change, ReflectionScanner, ptrace/gcore,
Discord, GitHub publication, public ABI/header opening, promotion, release readiness, or
stable/complete SDK claim was authorized.

## Lifecycle Preflight Boundary Follow-Up

A follow-up lead-owned pass integrated the remaining offline boundary checks from the
live-ops/reversing/SDK audits. A fresh sub-agent verifier was attempted after compaction,
but the multi-agent tool reported the agent thread limit was reached, so this pass was
implemented and validated locally.

Integrated offline changes:

- `check_player_identity_runtime_principal_lifecycle_window_manifest.py` now requires
  request/approval/preflight sidecars to live beside the copied `window-manifest.env`;
  sidecars elsewhere in the approved offline workspace fail even if their run id and SHA
  match.
- `build_player_identity_runtime_principal_lifecycle_evidence_bundle.py` now rejects
  consume/preflight/approved-manifest reports that overclaim public header, public ABI,
  v1 completion, or public capability/callback ABI lists. Preflight reports explicitly
  publish those fields as closed/empty.
- `check_public_sdk_v1_completion.py` now exposes `route_gate_current_blockers` in
  `runtime_required_blockers` and `next_v1_work`, and the human report names the active
  P0 route gate. For `approved_runtime_evidence_missing`, it states that request-pack and
  preflight readiness are non-counting preparation.

Validation stayed offline-only:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_runtime_principal_lifecycle_window_manifest scripts.test_build_player_identity_runtime_principal_lifecycle_evidence_bundle scripts.test_check_player_principal_lifecycle_window_request scripts.test_prepare_player_principal_lifecycle_window_request`
  passed 144 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion`
  passed 178 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
  stayed valid/planning-only with `approved_runtime_evidence_missing`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
  exited 1 as expected, with SDK `0/12`, P0 `0/4`, and `stable_claim_allowed=false`.

Freshness follow-up integrated after this boundary pass:

- `prepare_player_principal_lifecycle_window_request.py` now records `prepared_at_utc` in
  `window-request.json`, the human approval request, and the receipt's
  `bound_request_pack`.
- `check_player_principal_lifecycle_window_request.py` requires `prepared_at_utc` before
  the approved window start, includes it in the expected bound request, and rejects
  completed receipts whose `approval_recorded_at_utc` is before request preparation or
  at/after the approved window start.
- `check_player_identity_runtime_principal_lifecycle_window_manifest.py` performs the
  same replay-time freshness checks so window-manifest validation cannot accept a stale
  receipt through a different path.

Validation stayed offline-only after freshness hardening:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_prepare_player_principal_lifecycle_window_request scripts.test_check_player_principal_lifecycle_window_request scripts.test_check_player_identity_runtime_principal_lifecycle_window_manifest scripts.test_build_player_identity_runtime_principal_lifecycle_evidence_bundle`
  passed 148 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence`
  passed 52 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion`
  passed 178 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
  stayed valid/planning-only with `approved_runtime_evidence_missing`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
  exited 1 as expected, with SDK `0/12`, P0 `0/4`, and `stable_claim_allowed=false`.

A fresh 4-agent delegation round was attempted for this follow-up, but the multi-agent
tool reported agent thread limit reached; lead integration continued locally.

No runtime/server operation, marker/env change, ReflectionScanner, ptrace/gcore, Discord,
GitHub publication, public ABI/header opening, promotion, release readiness, or
stable/complete SDK claim was authorized.

## PluginManager Init-Failure Retry Hardening

A supervised four-agent follow-up split runtime/ABI, SDK/P0, reversing/offline evidence,
and live-ops/docs safety review. The runtime/ABI auditor confirmed that the init-failure
path could strand a mapped plugin outside `UnloadAll()` retry if callback cleanup or
`dlclose` failed and retention tracking then failed after scope guards were dismissed.

Integrated fix:

- `PluginManager::LoadPlugins` now reserves one loaded-plugin slot and prebuilds the
  init-failure retry `PluginInfo` before calling `ObeliskPlugin_Init`.
- Callback-cleanup failure and init-failure `dlclose` failure now move that prebuilt
  retry record into `m_LoadedPlugins`, preserving a manager-owned retry path without
  repeating plugin shutdown.
- A local `static_assert` protects the no-throw move assumption used by the pre-reserved
  retry record.
- `PluginManagerTests` now proves cleanup-failure retry and close-failure retry both
  survive the retention-failure test hook and are later cleaned by `UnloadAll()`.
- `test_plugin_manager_guardrails.py` now checks the prebuilt retry state and moved
  retention record instead of expecting allocation-prone inline initializer pushes.

Auditor outcomes:

- SDK/P0 audit found no public SDK accounting change and no extra SDK guardrail needed;
  `PluginManager` lifecycle hardening does not promote identity, permissions/admin,
  command response, commands/replies, runtime readiness, or a stable SDK claim.
- Live-ops/docs audit found no wording that implies server approval, marker/env changes,
  runtime observers, production stability, or v1 SDK completion.
- Reversing/offline audit rejected broad dump, FName, GObjects, core, serial, or
  ResourceHandle rediscovery for this blocker; the useful evidence is local runtime/ABI
  lifecycle validation.

Validation stayed offline-only:

- `cmake --build build -j"$(nproc)"` completed.
- `ctest --test-dir build -R '^PluginManagerTests$' --output-on-failure` passed.
- `python3 scripts/test_plugin_manager_guardrails.py` passed 24 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_command_permission_route_gate`
  passed 40 tests.
- Focused SDK completion tests for fail-closed current manifest, route overclaims, P0
  locked accounting, stable-release contract boundaries, and installed package-shape
  non-claim evidence passed 6 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_research_doc_guardrails`
  passed 23 tests.
- `scripts/check_command_permission_route_gate.py --json` stayed valid/planning-only with
  `critical_path_phase.current_blocker=approved_runtime_evidence_missing` and all
  readiness flags false.
- `scripts/check_public_sdk_v1_completion.py --json` exited 1 as expected with
  `stable_claim_allowed=false`, status `blocked`, SDK 0/12, and P0 0/4.

No runtime/server operation, marker/env change, ReflectionScanner, ptrace/gcore, Discord,
GitHub publication, public ABI/header opening, promotion, release readiness, or
stable/complete SDK claim was authorized.

## Capture-Plan And SDK Manifest Non-Evidence Guardrail

A supervised four-agent read-only round split SDK/P0 route auditing, live-ops/request-pack
auditing, reversing/offline evidence triage, and runtime/ABI guardrail review. The lead
integrated the bounded offline findings.

Integrated changes:

- `docs/research/2026-06-01-player-principal-runtime-capture-plan.md`,
  `docs/research/2026-06-01-player-principal-offline-to-runtime-plan.md`, and
  `docs/research/2026-06-01-player-principal-runtime-window-brief-template.md` now route
  future runtime consumption through prepared request packs, `prepared_at_utc`, completed
  receipt timing after preparation and before window start, sidecars beside copied
  `window-manifest.env`, post-window replay, and approved-evidence bundle checks instead
  of raw copied-log consumption.
- `test_check_player_identity_runtime_principal_lifecycle_window_manifest.py` now covers
  the sibling negative case where a completed receipt is approved at the window start.
- `docs/public_sdk_surfaces.json` now states that prepared request packs, preflight
  readiness, window manifests, observer env files, and operator approval receipts are
  freshness-bound operational preparation only and do not satisfy approved runtime
  principal lifecycle evidence.
- `check_public_sdk_v1_completion.py` enforces that player-identity manifest wording via
  `player_identity_request_pack_non_evidence_manifest_terms_missing`.

Validation stayed offline-only:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_player_principal_lifecycle_window_request scripts.test_check_player_identity_runtime_principal_lifecycle_window_manifest scripts.test_check_player_identity_runtime_principal_lifecycle_approved_evidence scripts.test_build_player_identity_runtime_principal_lifecycle_evidence_bundle`
  passed 189 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_research_doc_guardrails`
  passed 23 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_check_public_sdk_v1_completion`
  passed 179 tests.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_command_permission_route_gate.py --json`
  stayed valid/planning-only with `approved_runtime_evidence_missing`.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_public_sdk_v1_completion.py --json`
  exited 1 as expected, with SDK `0/12`, P0 `0/4`, and `stable_claim_allowed=false`;
  `player_identity_request_pack_non_evidence_terms_missing=[]`.

Rejected reversing work: broad FName/GObjects/core/admin/lifecycle rediscovery and
ResourceHandle zero-serial/serial/GObjects scans do not advance the active P0 blocker.
The missing item remains approved copied runtime principal lifecycle evidence under a
current-turn approved live-ops window.

Pending runtime/ABI follow-up: audit `PluginManager` init-failure retention. The auditor
reported a possible cleanup-failure path where a mapped plugin could be stranded outside
`UnloadAll` retry if retention tracking allocation fails.

No runtime/server operation, marker/env change, ReflectionScanner, ptrace/gcore, Discord,
GitHub publication, public ABI/header opening, promotion, release readiness, or
stable/complete SDK claim was authorized.
