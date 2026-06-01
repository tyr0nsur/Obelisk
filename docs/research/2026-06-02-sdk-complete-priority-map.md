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
