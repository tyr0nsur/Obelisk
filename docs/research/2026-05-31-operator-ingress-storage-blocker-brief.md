# Operator Ingress Storage Blocker Brief

Date: 2026-05-31
Status: blocker brief
Surface: `obelisk.operator_ingress_storage.v1`

## Purpose

`obelisk.operator_ingress_storage.v1` is a separate promotion blocker from
`player_identity`. Operator ingress and durable storage must be specified,
reviewed, and validated independently before any public API, plugin ABI surface,
or server-facing implementation is exposed.

This brief is intentionally minimal. It defines acceptance criteria and
non-scope for a future design/API round; it does not implement an API.

## Current v1 Decision

Decision: `blocked_until_promoted_or_explicitly_excluded`.

`player_identity` promotion does not unblock this surface. A v1 release must either:

- promote a reviewed append-only POD C ABI contract with the acceptance criteria below
  and SDK consumer or integration coverage; or
- explicitly exclude `obelisk.operator_ingress_storage.v1` by name in the v1 release
  statement and state that RCON, webhook, database/storage, secret manager, external
  ingress, and cross-instance storage APIs are not included.

Until one of those outcomes is recorded, `v1_completion_required` must remain false and
this surface must not declare a public contract.

## Offline Validation Profile

The next useful improvement is offline-only contract evidence. It may refine
requirements and tests for a future design/API round, but it must not add
headers, callbacks, services, server experiments, RCON/storage/webhook
connectivity, or a plugin-facing ABI.

Required offline lanes:

- Ingress contract matrix: list each candidate ingress transport, trust
  boundary, authorization source, rate limit, backpressure rule, rejected
  secret class, and fail-closed mode.
- Storage migration plan: define schema version fields, migration order,
  rollback posture, retention, corruption handling, and per-instance isolation
  without naming a promoted backend API.
- Queue lifecycle model: cover enqueue durability, retry, poison-message
  handling, shutdown drain, plugin unload drain, restart recovery, and maximum
  drain deadline.
- Text and audit policy: define UTF-8 validation, normalization, maximum byte
  length, rejection behavior, log/audit escaping, stable audit event names, and
  redacted payload rules.
- Multi-instance/lifecycle proof: describe shared-root locking, duplicate
  ingestion, replay protection, crash behavior, init-failure cleanup,
  `dlclose` safety, and owner-scoped worker/callback teardown.

Completion of this profile is planning evidence only. Promotion still requires
a reviewed append-only POD C ABI, capability gates, owner-scoped cleanup, and
SDK consumer or integration coverage.

## Acceptance Criteria

- The design names the ingress sources, trust boundaries, authorization model,
  rate limits, backpressure behavior, and failure modes before implementation.
- The storage contract defines schema versioning, migrations, rollback posture,
  retention, corruption handling, and per-instance isolation.
- Queue behavior is explicit: enqueue durability, retry policy, poison-message
  handling, shutdown drain, unload drain, restart recovery, and maximum drain
  time must be specified.
- Secrets are never accepted, logged, persisted, echoed in audit output, or
  exposed through plugin callbacks. Any required secret material must use an
  external secret source with clear ownership and redaction rules.
- All external text input must define UTF-8 validation, normalization policy,
  maximum byte length, rejection behavior, and log/audit escaping.
- Audit records must cover accepted, rejected, retried, dropped, migrated, and
  operator-initiated actions with stable event names and redacted payloads.
- Multi-instance behavior must be explicit for shared plugin/config roots:
  instance IDs, file/database locking, duplicate ingestion, replay protection,
  and cross-process ownership must fail closed unless deliberately designed.
- Lifecycle must be safe across plugin init failure, shutdown, unload, `dlclose`,
  server restart, and process crash. No background worker, callback, handle, or
  borrowed pointer may outlive its owning plugin/runtime context.
- Any future C ABI surface must be append-only, POD-only, versioned by
  `abi_version`/`struct_size` or an equivalent prefix, guarded by capability
  bits, and backed by owner-scoped unregister/cleanup paths.
- Validation must include unit or integration coverage for schema migration,
  queue drain, UTF-8 rejection, redaction, multi-instance isolation, and
  lifecycle cleanup before promotion.

## No-Scope

- No player identity, tribe identity, account linking, identity resolution, or
  identity-derived authorization is promoted by this blocker.
- No gameplay mutation, chat send/reply, moderation action, inventory action, or
  ProcessEvent return override is implied.
- No raw UE4 pointers, `UObject`, `UFunction`, `FString`, raw params, GObjects
  indices, FName-derived identity, pincode values, or resource handles may cross
  this boundary.
- No shared cluster handle, persistent runtime callback id, or process-local
  registration id may be stored as durable state.
- No public API, header change, C++ implementation, plugin example, or live
  server experiment is authorized by this brief.

## Open Design Questions

- Which operator ingress transports are allowed, and which are explicitly
  rejected for v1?
- What is the authoritative storage backend for v1, and what is the smallest
  migration format that supports rollback?
- What audit sink is required for production use, and how are audit records
  correlated without depending on `player_identity`?
- What queue-drain deadline is acceptable during server shutdown or plugin
  unload, and what happens when it is exceeded?
