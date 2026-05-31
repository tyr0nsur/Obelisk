# Player Identity Lifecycle Anchor Schema Gap

Date: 2026-05-31

## Summary

`players-identity-lifecycle-intake` can guide player identity research, but it does not
yet contain accepted session-start or session-end anchors. Closing the current
`ServerListPlayers` and `ServerKickPlayer` fixture gap would improve admin-surface
coverage only; it would not prove login/logout lifecycle semantics or public principal
invalidation.

## Current Evidence Boundary

- The existing target set is planning-only and must stay out of release/public readiness.
- Fixture coverage remains blocked on missing sanitized snapshots for:
  - `ShooterPlayerController.ServerListPlayers`
  - `ShooterPlayerController.ServerKickPlayer`
- `build_redacted_ufunction_signatures.py --players-identity-first-evidence` intentionally
  reports `session_start_accepted=false`, `session_end_accepted=false`, and empty accepted
  target lists.
- `validate_offline_artifact_gate.py` currently rejects lifecycle overclaims; true
  lifecycle anchors or non-empty accepted target lists are blockers for the existing
  candidate-only first-evidence artifact.

## Missing Schema

The next useful artifact format is a candidate-only lifecycle-anchor schema that can
record possible session-start/session-end evidence without promoting public identity. A
future `obelisk.players-identity-lifecycle-anchor-candidates.v1` shape should distinguish:

- candidate anchor recorded but not accepted;
- accepted start/end anchor only when exact `Outer.Function`, `ParmsSize`, property order,
  field classes, and second-source/static evidence are present;
- principal privacy and invalidation questions that remain unresolved even after layout
  acceptance.

Required candidate fields should include:

- `role`: `session_start` or `session_end`;
- exact `outer` and `function` name;
- redacted `ParmsSize`, property order, field classes, and copied/scalar eligibility;
- evidence source identity and binary/core/snapshot provenance;
- second-source or static corroboration status;
- non-claims for public identity, lookup, permissions, commands, mutation, return override,
  ResourceHandle, and runtime readiness.

## Next Step

Before adding login/logout target names to release or public SDK gates, add a synthetic
fixture/test for the lifecycle-anchor candidate schema. The test should prove that a
candidate can be preserved as research evidence while accepted lifecycle anchors still
require exact layout evidence plus second-source/static corroboration and explicit
invalidation semantics.
