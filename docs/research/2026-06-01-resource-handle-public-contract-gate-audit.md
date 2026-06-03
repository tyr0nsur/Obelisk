# ResourceHandle Public Contract Gate Audit

## Scope

Offline-only audit of the public SDK ResourceHandle/object-identity blocker. The named
decision manifest and dedicated readiness checker were absent when this historical note
was written. Later hardening added
`docs/object_identity_resource_handle_public_contract_decisions.json`,
`scripts/check_object_identity_resource_handle_public_contract_readiness.py`, focused
tests, and SDK-completion integration. This note now records the original surface-map
hardening target and the current remaining blockers.

No runtime C++, public headers, build outputs, servers, Discord, Git state, or
`/servidor/ark` paths were touched.

## Gate Hardened

`obelisk.object_identity_resource_handle.v1` remains `post-v1` and blocked. The public SDK
surface map now states that the current public slice is copied/redacted scalar callback
data and category-only metadata descriptors only.

The hardened blocker is a non-substitution rule:

- copied events do not imply object identity;
- `resource_kind` metadata is category-only and does not imply lookup or correlation;
- raw `UObject` pointers are not a public handle source;
- lookup paths, persistence, and mutation surfaces cannot imply `ResourceHandle`;
- post-callback object correlation remains blocked until lifecycle, generation, validity
  scope, privacy/redaction, owner-token cleanup, C ABI layout, and installed-SDK consumer
  rules are explicit and tested.

## Audit Result

Existing broad guardrails already block public-header symbols and release-claim wording for
blocked ResourceHandle/object-identity surfaces. The gap was wording precision in the
surface map: copied event payloads, categorical metadata, raw pointers, lookup,
persistence, and mutation were all excluded elsewhere, but not bound together as a single
ResourceHandle non-substitution rule in the cross-cutting blocker row.

The public SDK map now fails closed at the planning-contract level: no public handle ABI is
preserved or implied by existing copied events or metadata-only descriptors.

## Remaining Blockers

- Runtime lifecycle/reuse evidence, approved stale-object negative samples, and runtime
  serial reuse/wraparound semantics remain missing.
- UObject flag semantics, callback-scope behavior, owner-token cleanup, privacy/redaction,
  ABI layout, and installed-SDK consumer evidence remain missing.
- Existing decisions/checker/tests keep ResourceHandle/object identity blocked and
  planning-only; they do not promote lookup, persistence-backed handles, mutation handles,
  or post-callback object correlation.

Until the remaining runtime/ABI evidence is promoted and the existing guardrails pass,
`ResourceHandle`, object identity, lookup, persistence-backed handles, mutation handles,
and post-callback object correlation must remain blocked or explicitly excluded from v1
release wording.
