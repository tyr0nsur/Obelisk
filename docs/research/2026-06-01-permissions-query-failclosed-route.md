# Permissions Query Fail-Closed Route

Date: 2026-06-01

## Summary

The next permissions/admin step after the player principal policy is a candidate-only
pre-ABI contract, not public SDK surface. The intended schema name is:

```text
obelisk.permissions-admin-query-failclosed-contract.v1
```

This artifact should validate the shape of a future query-only permission decision over a
copied opaque principal. It must not add `ObeliskApi.h` symbols, public callbacks,
permission groups, grants, admin mutation, command routing, replies/send-chat, storage,
operator ingress, `ResourceHandle`, UE pointers, lookup, mutation, or return override.
The artifact must also carry its own candidate-only `artifact_identity` plus a
`dependency_context` that binds it to `obelisk.player_identity.v1`, the accepted
lifecycle/principal planning schemas, and the future approved runtime principal lifecycle
evidence schema. That dependency context is accounting only; it does not promote player
identity or permissions/admin.

The active v1 dependency route remains:

```text
principal -> permissions/admin -> command response -> commands/replies
```

## Candidate Query Shape

The candidate query contract should require these input fields or exact equivalents:

- `plugin_owner_token`;
- `principal_handle`;
- `principal_generation`;
- `principal_scope_flags`;
- `action`;
- `action_size`;
- `resource_scope`;
- `resource_scope_size`;
- `request_flags`.

The decision shape should require:

- `decision`: only `deny`, `allow`, or `unknown`;
- `reason_flags`;
- `policy_source_id`;
- `policy_source_generation`;
- `authority_kind`;
- `authority_generation`;
- `policy_epoch`.

`allow` must require runtime-owned policy/authority provenance. Plugin-provided input
cannot self-attest authority, policy source, or policy epoch.

Config can enable a permissions/admin surface or provide policy inputs only. It cannot
establish principal identity or permission claims. Command text is copied request data
only and cannot establish identity, authority, policy provenance, or admin permission
claims before runtime observation has established a principal.

## Fail-Closed Requirements

The candidate contract should require deny/unknown for:

- missing or zero owner token;
- missing capability;
- missing principal;
- missing established runtime principal identity;
- command text principal or permission claim;
- operator-config principal or permission claim;
- missing or mismatched principal generation;
- stale principal;
- unsupported principal scope flags;
- process/scope mismatch;
- missing action or malformed action size;
- missing policy source;
- missing policy source generation;
- missing authority kind/generation;
- missing policy epoch;
- unknown authority source;
- plugin-supplied/self-attested provenance;
- rate limit exceeded.

`principal_handle` alone must never authorize.

## Non-Claims

This route is not evidence for:

- public permissions/admin ABI;
- permission groups or admin groups;
- grant/revoke APIs;
- ban/kick APIs;
- moderation authority;
- command router;
- command/chat response path;
- replies/send-chat;
- storage or persistence;
- public permission cache ABI;
- v1 SDK completion.

The existing `docs/permissions_admin_public_contract_decisions.json` stays authoritative
for public promotion requirements. A checker for this candidate route can consume the
principal policy artifact as dependency context, but it must not convert that policy
artifact into public identity readiness or v1 completion evidence.
