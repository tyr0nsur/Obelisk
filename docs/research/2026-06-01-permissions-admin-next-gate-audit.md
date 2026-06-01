# Permissions/Admin Next Gate Audit

Date: 2026-06-01
Local HEAD: `5bc9da2`

## Scope

Audit the candidate-only `permissions/admin` contract before any public ABI work after
player identity. Reviewed inputs:

- `docs/permissions_admin_public_contract_decisions.json`
- `scripts/check_permissions_admin_public_readiness.py` (absent)
- `scripts/check_public_sdk_v1_completion.py`
- `scripts/test_permissions_admin_public_contract_decisions.py`
- `docs/research/2026-05-31-permissions-admin-minimum-post-identity.md`
- `docs/research/2026-06-01-permissions-query-failclosed-route.md`

No public header, ABI, runtime C++, server work, commits, tags, pushes, or operator
actions were performed.

## Audit Result

`obelisk.permissions_admin.v1` remains blocked and candidate-only. The next public slice,
after promoted player identity, is still limited to query-only fail-closed permission
decision checks over copied principals.

The audited contract preserves these boundaries:

- no public `include/obelisk/ObeliskApi.h` permission/admin symbols;
- no public permission cache ABI;
- no command router, command/chat response path, replies/send-chat, groups, grants,
  ban/kick, admin mutation, storage, operator ingress, lookup, `ResourceHandle`, raw UE
  pointers, raw params, mutation, or return override;
- missing, stale, or mismatched `principal_generation` fails closed;
- missing or unsupported `principal_scope_flags`, process mismatch, and wider than
  promoted principal scope fail closed;
- `operator-config` can be recognized as a policy input source but is not allow-capable;
- `allow` is limited to `runtime-local` authority with runtime-owned provenance;
- `runtime-local` authority without runtime-owned provenance fails closed.

## Contract Hardening

The decision manifest now records `allow_capable_authority_ownership` and
`operator_config_allow_capable=false` at the public contract level and repeats the same
machine-readable policy inside the authority provenance blocker.

The associated test now asserts:

- top-level operator-config remains not allow-capable;
- allow-capable authority ownership is runtime-owned;
- runtime-local authority must be runtime-owned before it can return `allow`;
- operator-config authority and runtime-local authority without runtime-owned provenance
  are both deny/unknown-only conditions.

## Next Blocker

Exact next blocker:

`obelisk.player_identity.v1` must be promoted with copied principal handles,
`principal_generation`, `principal_scope_flags`, lifecycle invalidation, runtime principal
observation, privacy/redaction policy, and process-scope semantics before
`permissions/admin` may add any public header, capability, callback, cache ABI, or
query-only permission check ABI.

Until that blocker is resolved, permissions/admin can only advance as candidate-only
contract evidence and guardrail tests.
