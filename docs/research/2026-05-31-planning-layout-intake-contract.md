# Planning Layout Intake Contract

## Purpose

`planning-layout-intake` is a documentation contract for consuming layout evidence while
keeping a lane explicitly non-promoted. For the current use case, it applies to player
identity target sets such as `players-identity-lifecycle-intake`.

This contract is planning-only and consume-only. It can organize exact UFunction layout
inputs, target coverage, redaction decisions, blockers, and non-claims. It is not a
promotion gate, release gate, SDK gate, runtime gate, or evidence shortcut.

## Required Meaning

A `planning-layout-intake` artifact or note may say:

- the named target set is closed enough for planning review;
- sanitized layout evidence can be consumed by docs, planners, preflight checks, or
  candidate-only report builders;
- missing targets, missing second-source roots, missing lifecycle anchors, and privacy
  blockers are machine-readable planning blockers;
- all player identity fields remain copied-candidate, private-redacted, recognition-only,
  or forbidden until a later privacy/lifecycle policy promotes a narrower copied form.

It must also say:

- `readiness_classification=planning_only`;
- `consume_mode=consume_only`;
- `promotion_ready=false`;
- `public_sdk_ready=false`;
- `runtime_ready=false`;
- `release_readiness=false`.

## Player Identity Boundary

For player identity, the contract is scoped to target-set evidence, not identity
semantics. It can cover exact names, `ParmsSize`, property order, offsets, property
classes, bool canonicality expectations, fixture coverage, and redacted field
classification for `players-identity-lifecycle-intake` or later reviewed player identity
planning sets.

It does not prove an authenticated principal, sender identity, login/logout lifecycle,
disconnect cleanup, reconnect behavior, transfer identity, tribe identity, command
authority, permission state, economy account, storage key, or cross-instance identity.

Adding `ServerListPlayers`, `ServerKickPlayer`, or future login/logout candidates to a
planning layout intake only improves planning coverage. It does not promote those
functions as public anchors or runtime events.

## Consumer Rules

Consumers may use this contract to:

- fail closed when target-set coverage is incomplete;
- plan focal snapshots from a reviewed reflection inventory pack;
- build candidate-only first-evidence summaries;
- compare sanitized layouts while still reporting no promotion;
- keep redaction, privacy, and lifecycle blockers visible.

Consumers must not use it to:

- add target sets to release readiness;
- publish SDK headers, capability bits, plugin APIs, examples, or compatibility claims;
- authorize runtime observation, hooks, scanners, server access, restarts, marker changes,
  `ptrace`, or `gcore`;
- expose UE pointers, raw params, object-array coordinates, `FName`/GObjects indices,
  `ResourceHandle`, lookup, mutation, return override, or persistent player IDs.

## Non-Claims

This note does not modify target sets, fixtures, tests, scripts, runtime behavior, public
docs, SDK contracts, handoff routing, or release policy. It records the meaning of the
contract so future player identity planning artifacts cannot be mistaken for promotion
evidence.
