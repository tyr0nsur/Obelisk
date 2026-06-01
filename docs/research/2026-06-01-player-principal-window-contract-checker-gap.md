# Player Principal Window Contract Checker Gap

Date: 2026-06-01

## Scope

This is an offline contract audit only. It does not authorize a server window, marker
edits, wrapper/env changes, restarts, Discord notices, Git actions, runtime code changes,
public SDK claims, plugin delivery, lookup, mutation, permissions, commands, or release
readiness.

## Current Gap And Resolution

The exact checker artifact requested for the future player-principal window contract was
absent during this audit:

- `scripts/check_player_principal_lifecycle_window_manifest.py`
- `scripts/test_check_player_principal_lifecycle_window_manifest.py`

A related checker exists under the longer player-identity name, but future approval
should not depend on operators or reviewers guessing that alias. The contract should have
an exact player-principal checker entry point, with focused tests, before requesting a
runtime evidence window.

Resolution in this round: the short entry point now delegates to the existing
`scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py` checker,
and a focused alias test verifies that the short and long entry points produce the same
fail-closed report for an invalid manifest. The long checker remains the implementation
owner; the short checker is an operator/reviewer-facing entry point.

## Required Checker Artifact

The future checker must fail closed unless the copied manifest proves all of these facts
for one approved window:

- exact `run_id` / window id and exact target instance/map match the approval
- copied log path is the approved workspace copy for that `run_id`
- copied log SHA256 matches the bytes analyzed offline
- reviewed Obelisk source/build SHA is recorded and non-placeholder
- observer scope is `player_principal_lifecycle` only
- plugins are disabled
- `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0`
- `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10`
- no sibling observer/debug/scanner/callback marker entries or env gates survived the
  window
- pre/post posture checks are stable for the same instance
- rollback completed, removed observer env/markers, and preserved stable hook/plugin
  posture
- result remains consume-only: no public SDK, player identity, lookup, permissions,
  commands, plugin delivery, mutation, `ResourceHandle`, return override, runtime
  readiness, or release claim

## Hardened Requirement To Carry Forward

Treat "no sibling markers/env" as a manifest-bound assertion, not an implied posture
summary. The exact checker should require explicit fields such as
`sibling_marker_entries=absent` and `sibling_observer_env=absent`, and tests should prove
that any alternate observer, scanner, native-exec, ptrace, debug-control, callback escape,
or malformed/symlink marker summary blocks acceptance.

Until the long checker and the short entry-point test pass in the integration gate, the
future runtime window request remains blocked at the manifest/checker contract stage.
