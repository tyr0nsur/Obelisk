# Player Identity First Evidence

## Objective

Audit the `players_identity_lifecycle` planning lane and define the smallest evidence
package that must exist before public permissions, command, or economy SDK design work can
start.

This note is documentation-only. It does not run scans, read dumps, touch servers, use
runtime tools, change target sets, widen public SDK scope, or promote identity.

## Inputs Reviewed

- `docs/research/2026-05-30-player-identity-lifecycle-plan.md`
- `docs/research/2026-05-30-v1-core-capability-map.md`
- `docs/research/2026-05-29-module-surface-roadmap.md`
- `docs/research/2026-05-29-public-gameplay-event-readiness-audit.md`
- `docs/research/2026-05-30-chat-command-helper-roadmap.md`
- `docs/PLUGIN_HUB_FOUNDATION_V1.md`
- `docs/PLUGIN_HUB_CAPABILITY_MATRIX.md`
- `docs/agent-handoff/CURRENT.md`
- `scripts/reflection_target_sets.py`

## Current Blockers

The current lane is not ready to start public permissions, command, or economy SDK work.
The block is not a lack of demand. It is a lack of accepted identity lifecycle evidence.

- `players-identity-lifecycle-intake` exists only as a planning/guidance target set.
  `scripts/reflection_target_sets.py` correctly classifies it as `planning_only`, and
  `CURRENT.md` records that it is release-gate rejected.
- The closed seed set is risk classification, not lifecycle proof. It contains admin
  pressure, chat sender precedent, tribe membership shapes, a transfer edge, and mission
  add/leave/remove names. It does not establish an accepted login/logout target.
- `ShooterPlayerController.ServerSendChatMessage` supports copied chat text, send mode,
  and local sequence only. It intentionally excludes sender/player identity, so it cannot
  back authenticated commands or per-player permission checks.
- Tribe, mission, transfer, and admin names contain identity-sensitive object refs,
  arrays, IDs, names, and authority surfaces. Existing notes keep those fields
  recognition-only or redacted.
- `ResourceHandle`, public GObjects, pointer-derived identity, lookup, object correlation,
  mutation, and return override remain blocked. Player identity must not be built by
  exposing UE object coordinates or borrowed pointers.
- No current policy defines which copied player identifier is public, private, hashed,
  process-local, persistent, or forbidden.
- No accepted lifecycle cleanup contract proves when a principal appears, becomes
  authenticated, disconnects, changes controller/state object, transfers, or must be
  invalidated.
- No command response path, permission grant/check service, persistence model, storage
  schema, operator reload policy, or abuse-control model exists.
- Economy remains additionally blocked on commands, identity, permissions, persistence,
  item/inventory mutation, and event evidence. Identity evidence alone cannot start an
  economy SDK implementation.

## Smallest First Evidence Package

The first useful package should be named as a candidate-only planning artifact, for
example `players-identity-first-evidence`, and should answer only whether a safe principal
model is possible. It should not add ABI, runtime observers, public commands, permissions,
economy, or lookup.

Required shape:

1. Artifact identity and scope:
   - ARK binary SHA256, Obelisk commit, build type, artifact/source IDs, and exact target
     set revision.
   - Inputs copied from approved offline locations only, with no protected live-server path
     dependencies in manifests.
   - A closed target list matching `players-identity-lifecycle-intake`, plus any proposed
     login/logout additions kept as candidate-only until separately reviewed.

2. Exact lifecycle anchors:
   - At least one accepted session-start/login/connect candidate and one accepted
     session-end/logout/disconnect candidate, or an explicit blocker stating that none is
     yet proven.
   - Exact `Outer.Function`, `Function` identity, parameter count, `ParmsSize`, property
     order, offsets, sizes, and property classes for each anchor.
   - Second-source layout comparison or equivalent accepted static evidence for the
     anchors before they can influence public design.

3. Principal field classification:
   - For each candidate field that could identify a player, record property name, property
     class, offset, size, owning function/object, and whether it is copied-candidate,
     private-redacted, recognition-only, or forbidden.
   - Treat player IDs, Steam/EOS/platform IDs, names, IPs, tribe IDs, transfer IDs,
     object refs, arrays, strings, FName/GObjects indices, raw params, and UE pointers as
     redacted until a separate privacy policy accepts a narrower copied form.
   - Reject pointer-derived IDs and memory addresses as public or persistent identity.

4. Chat-to-principal boundary:
   - Preserve the current `ChatMessageEvent` non-claim: copied text does not authenticate a
     sender.
   - If a future command model needs sender identity, require separate evidence proving a
     copied principal association for the chat sender without exposing controller/player
     pointers or object-array coordinates.

5. Lifecycle and invalidation semantics:
   - State whether identity is process-local, restart-local, cluster-stable, or persistent.
     The default must be no persistence and no cross-instance claim.
   - Define fail-closed cleanup behavior for disconnect, transfer, reconnect, missing
     identity, duplicate identity, stale controller/state object, and failed validation.
   - Do not require or imply post-callback UE lookup. If later lookup is requested, route it
     through the separate blocked `ResourceHandle`/object-lifetime lane.

6. Privacy and capability policy:
   - Define what is safe to expose to plugins, what stays redacted, what may be stored, and
     what must never be logged.
   - Define separate capability gates for passive identity observation, command principal
     use, permission checks, and persistence. Do not collapse them into one "player API".

7. Tests and gates before public API drafting:
   - Fixture tests for exact layout and bool canonicality where bools are copied.
   - ABI/SDK consumer tests only after the evidence package identifies a copied payload
     shape.
   - Lifecycle cleanup tests for owner-token callback cleanup and principal invalidation.
   - Negative tests proving missing identity, disabled capability, unsupported artifact,
     stale lifecycle state, and malformed copied fields fail closed.

## Minimal Candidate Builder Design

Extend `scripts/build_redacted_ufunction_signatures.py` with a focused
`--players-identity-first-evidence` mode rather than creating a public SDK generator. The
mode should consume only sanitized UFunction snapshot roots for
`players-identity-lifecycle-intake`, reuse the existing protected-path rejection and
target-set manifest coverage helpers, and then apply a stricter player-identity classifier
on top of the generic redacted UFunction report. If the implementation becomes large,
split helpers into `scripts/build_players_identity_first_evidence.py`, but keep the CLI
and tests identity-specific and candidate-only.

Required output schema:

```text
schema = "obelisk.players-identity-first-evidence.v1"
artifact_status = "candidate_only"
readiness_classification = "planning_only"
promotion_ready = false
public_sdk_ready = false
runtime_ready = false
snapshot_root = "redacted"
input_target_set = "players-identity-lifecycle-intake"
generated_from.snapshot_schema
generated_from.input_snapshots[] = {id, sha256}
target_set_coverage = existing redacted UFunction target-set coverage object
artifact_identity = {
  ark_binary_sha256,
  obelisk_commit,
  build_type,
  target_set_revision,
  source_artifact_ids[],
  path_redacted = true
}
targets[] = {
  target,
  source_snapshot,
  source_snapshot_sha256,
  function_flags,
  num_parms,
  parms_size,
  return_value_offset,
  property_order[],
  status,
  lifecycle_anchor_role,
  blockers[]
}
fields[] = {
  field,
  target,
  name,
  source_property_class,
  direction,
  offset,
  element_size,
  array_dim,
  property_flags,
  bool_masks?,
  classification,
  redaction_reason,
  evidence_status,
  source_snapshot,
  source_snapshot_sha256,
  blockers[]
}
copied_candidates[] = only canonical non-identity bool/scalar candidates, if any
forced_redacted_fields[] = every identity-like scalar/string/container/object/FName field
forbidden_fields[] = pointer-derived identity, raw params, UE pointers, GObjects/FName indices
lifecycle_anchors = {
  session_start_accepted = false,
  session_end_accepted = false,
  accepted_start_targets[],
  accepted_end_targets[],
  blockers[]
}
privacy_policy = {
  public_principal_ready = false,
  copied_public_identifier = null,
  persistent_identifier_ready = false,
  process_local_identifier_ready = false,
  storage_ready = false,
  logging_policy = "identity_values_not_logged"
}
promotion_gate = {
  ready = false,
  ready_scope = "planning_only",
  promotion_ready = false,
  blockers[]
}
safety_summary = {
  target_count,
  missing_target_count,
  field_count,
  copied_candidate_count,
  forced_redacted_count,
  forbidden_count,
  blocker_count,
  promotion_ready = false,
  public_sdk_ready = false
}
non_claims[]
```

## Candidate Builder Status

The smallest candidate-only mode now lives in
`scripts/build_redacted_ufunction_signatures.py --players-identity-first-evidence`. It
requires `players-identity-lifecycle-intake`, emits schema
`obelisk.players-identity-first-evidence.v1`, keeps `promotion_ready`,
`public_sdk_ready`, and `runtime_ready` false, and fails closed when the snapshot manifest
does not include the required `ShooterPlayerController.ServerListPlayers` and
`ShooterPlayerController.ServerKickPlayer` evidence.

This mode is still planning-only. It force-redacts identity-like fields, records
FName/GObjects indices, UE pointers, borrowed payloads, and raw params as forbidden
identity coordinates without emitting their values, and preserves the non-claim that
copied chat text does not authenticate a sender. It adds no ABI, public API, runtime
observer, command surface, permissions surface, lookup, persistence, mutation, or return
override.

The identity classifier must force-redact, even when the generic signature builder would
otherwise mark them as copied scalars: player IDs, Steam/EOS/platform IDs, names, IPs,
tribe IDs, transfer IDs, bed/spawn IDs, online-list values, mission tags, object refs,
arrays, strings/text, `NameProperty`, `FName`/GObjects indices, raw params, UE pointers,
and pointer-derived handles. Bool candidates remain candidates only and must preserve the
canonical-byte rule.

Minimum blockers to always record until independently cleared:

```text
planning_guidance_only
target_set_not_release_readiness
missing_accepted_session_start_anchor
missing_accepted_session_end_anchor
identity_privacy_policy_unproven
principal_copy_policy_unproven
lifecycle_invalidation_policy_unproven
second_source_identity_layout_not_accepted
resourcehandle_lookup_blocked
runtime_observation_requires_separate_approval
public_player_sdk_blocked
```

Required tests belong beside the existing script tests:

- `scripts/test_build_redacted_ufunction_signatures.py`: focused builder/mode emits
  `obelisk.players-identity-first-evidence.v1`, keeps `promotion_ready=false`, fails
  closed on missing `ServerListPlayers` or `ServerKickPlayer`, redacts input paths, and
  reports every required blocker.
- Identity scalar negatives: `PlayerDataID`, online-player arrays, mission tags, chat
  strings, object refs, and synthetic `SteamID`/`EOSID`/`PlatformID` fields never appear in
  copied/public fields.
- Bool canonicality: copied-candidate bool metadata is shape-only; any future runtime
  copied bool path must accept only `0` or `1` and clear output on non-canonical bytes.
- Target-set guardrails: `scripts/test_compare_reflection_snapshots.py` and
  `scripts/test_release_scope_guardrails.py` continue asserting
  `players-identity-lifecycle-intake` is `planning_only`, not release readiness, and
  promote-mode second-source reports are blocked by `target_set_not_release_readiness`.
- Second-source layout test: a complete 12-target comparison may set layout comparison
  success, but `promotion_gate.ready=false` and `promotion_gate.promotion_ready=false`
  remain mandatory.

## Minimal Ordering

The first identity package should unlock only design discussion for a copied principal
model:

1. Prove exact offline lifecycle target shapes.
2. Classify identity fields and privacy risk without copying public values.
3. Prove, in a later approved debug window if offline evidence cannot answer it, the
   runtime order and cleanup semantics for join/chat/leave or equivalent lifecycle events.
4. Only then draft a public identity payload.
5. Only after identity exists can command routing with a real principal be designed.
6. Only after identity plus command routing exists can a permission service be designed.
7. Only after identity, commands, permissions, persistence, and relevant item/event
   evidence exist can economy SDK work start.

## Explicit Non-Claims

- This note does not promote `players-identity-lifecycle-intake`.
- This note does not add or approve public player identity, permissions, commands,
  economy, admin, tribe, mission, transfer, chat moderation, replies, send-chat,
  persistence, database, storage, webhook, or RCON APIs.
- This note does not claim an accepted login/logout target exists.
- This note does not claim `ServerListPlayers`, `ServerKickPlayer`, tribe functions,
  mission functions, transfer functions, or chat functions are safe public identity
  anchors.
- This note does not promote `ResourceHandle`, public GObjects, object identity, lookup,
  mutation, return override, raw params, UE pointers, FName/GObjects indices, or
  pointer-derived handles.
- This note does not authorize runtime observation, server access, scanner runs, ptrace,
  `gcore`, broad tracing, marker changes, restarts, Discord updates, commits, tags, or
  pushes.
