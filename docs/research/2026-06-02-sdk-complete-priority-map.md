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
