# Player Identity Lifecycle Anchor Schema Gap

Date: 2026-05-31

## Summary

`players-identity-lifecycle-intake` can guide player identity research, but it does not
yet contain accepted session-start or session-end anchors. The admin-surface fixture gap
and the distinct second-source layout gap are now closed for planning evidence; the
remaining gap is a reviewed lifecycle-anchor schema plus principal invalidation policy.

## Current Evidence Boundary

- The existing target set is planning-only and must stay out of release/public readiness.
- Fixture coverage for the 12-target player-identity intake is now complete. The
  vanilla-gdb candidate root
  `/servidor/ark/workspace-offline/player-identity-offline-identity-vanilla-gdb-20260529T012853Z/focal-snapshots`
  compares `12/12` accepted in planning-layout mode against the committed fixtures.
- Static offline string/registration orientation has identified two additional
  lifecycle-shaped clues in the same ShooterGameServer binary hash:
  - `ShooterGameMode.HandleNewPlayer`: ASCII name VMA `0x4170122`, registration VMA
    `0x13cc20a`, native thunk `0x15d04c0`, class slot `0x58f2bd0`, class name UTF-32 VMA
    `0x40e0b24`, probable FName-ish slot `0x58ed3d0`.
  - `ShooterGameMode.OnLogout`: ASCII name VMA `0x417024f`, registration VMA
    `0x13cc560`, native thunk `0x15d1500`, class slot `0x58f2bd0`, class name UTF-32 VMA
    `0x40e0b24`, probable FName-ish slot `0x58ed3e0`.
  These began as navigation clues only. They are still not in the committed target set, do
  not prove login/logout order, and must not be treated as accepted lifecycle anchors
  without a reviewed schema update and invalidation policy.
- Sanitized lifecycle snapshots now exist for both candidates from the base and
  vanilla-gdb offline cores:
  - `ShooterGameMode.HandleNewPlayer`: `ParmsSize=26`, `NumParms=5`, fields
    `NewPlayer:ObjectProperty@0/8`, `PlayerData:ObjectProperty@8/8`,
    `PlayerCharacter:ObjectProperty@16/8`, `bIsFromLogin:BoolProperty@24/1`,
    `ReturnValue:BoolProperty@25/1`.
  - `ShooterGameMode.OnLogout`: `ParmsSize=8`, `NumParms=1`, field
    `Exiting:ObjectProperty@0/8`.
  Comparing those lifecycle snapshot roots with `scripts/compare_reflection_snapshots.py`
  reports `accepted=2`, `inconclusive=0`, `rejected=0`. This is exact layout
  corroboration only; object-typed fields remain non-public, raw UE pointers stay
  forbidden, and principal validity/invalidation semantics are not proven.
- `build_redacted_ufunction_signatures.py --players-identity-first-evidence` intentionally
  reports `session_start_accepted=false`, `session_end_accepted=false`, and empty accepted
  target lists.
- `validate_offline_artifact_gate.py` currently rejects lifecycle overclaims; true
  lifecycle anchors or non-empty accepted target lists are blockers for the existing
  candidate-only first-evidence artifact.
- `check_player_identity_lifecycle_anchor_candidates.py` now distinguishes the known
  static-orientation-only targets `ShooterGameMode.HandleNewPlayer` and
  `ShooterGameMode.OnLogout` with
  `candidate_anchor_known_lifecycle_orientation_not_accepted`. Unknown out-of-set targets
  still fail with `candidate_anchor_target_outside_closed_target_set`. This preserves the
  clues without accepting lifecycle semantics or adding them to the closed first-evidence
  target set.

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

Before adding login/logout target names to release or public SDK gates, update the
lifecycle-anchor candidate schema and tests so they can consume the two corroborated
layout snapshots while still blocking promotion until explicit invalidation semantics are
recorded. The test should prove that a candidate can be preserved as research evidence
while accepted lifecycle anchors remain non-public and do not imply public identity,
permissions, commands, lookup, mutation, return override, ResourceHandle, or runtime
readiness.
