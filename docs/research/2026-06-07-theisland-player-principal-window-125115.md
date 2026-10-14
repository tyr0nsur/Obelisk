# TheIsland Player Principal Window 20260607T125115Z

Date: 2026-06-07

## Scope

This note records a lead-owned live runtime evidence attempt on `arkserver2` /
`TheIsland`. It is runtime context and negative evidence for the missing
`CheckJoinInProgress(1,0)` role only.

It does not claim approved runtime evidence, runtime readiness, public SDK readiness,
SDK/P0 progress, stable readiness, publication authority, Plugin Hub readiness, or a
complete SDK route.

## Window

- Run id: `20260607T125115Z-player-principal-lifecycle`
- Evidence root:
  `/servidor/ark/workspace-offline/live-validation-logs/20260607T125115Z-player-principal-lifecycle`
- Window start/end: `2026-06-07T12:51:15Z` to `2026-06-07T13:06:15Z`
- Target instance/map: `arkserver2` / `TheIsland`
- ARK binary SHA256:
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`
- Installed Obelisk runtime SHA256:
  `a9e5f330c042132847ac9296cea8b3ef38fd70d4ecfce6a23fe2c44d9b5d8ec5`

The beta tester notice and RCON broadcasts were sent under the recorded 2026-06-06
standing launch/debug authority. TheIsland was restarted inside the approved window only
after zero players were confirmed. Ragnarok stayed online as the other cluster server;
Genesis2 stayed off, preserving the hard two-server maximum.

## Runtime Result

The Obelisk runtime loaded at `2026-06-07T12:52:02Z`, installed the ProcessEvent hook at
`12:52:03Z`, disabled plugin loading, and enabled `PlayerPrincipalLifecycleObserver` at
`12:52:25Z` with plugins disabled, dispatch limit `0`, log limit `10`, and no diagnostic
candidates.

Accepted copied observer events inside the fresh window:

- `2026-06-07T12:53:14Z`: `session_start` on
  `ShooterGameMode.HandleNewPlayer`, copied bool fields `bIsFromLogin,ReturnValue`,
  copied bool values `1,1`, `apply_status=session_start_created`.
- `2026-06-07T12:56:07Z`: `session_end` on `ShooterGameMode.OnLogout`,
  `apply_status=session_end_invalidated`, `correlation_status=matched`.

No accepted `session_start_rejected` event for
`ShooterGameMode.CheckJoinInProgress(1,0)` appeared in this window.

## Post-Window Checker State

The post-window dry-run report was saved at:

`/servidor/ark/workspace-offline/live-validation-logs/20260607T125115Z-player-principal-lifecycle/copy-ready-log.dry-run.json`

Important fields:

- `ready_to_copy=false`
- `approved_runtime_evidence=false`
- `copy_readiness=blocked_missing_lifecycle_roles`
- `roles_present=["session_start","session_end"]`
- `missing_roles=["session_start_rejected"]`
- `required_rejected_start_shape.target=ShooterGameMode.CheckJoinInProgress`
- `required_rejected_start_shape.copied_bool_values=1,0`

No log was copied into the evidence root as an approved candidate, no approved bundle was
built, and no runtime evidence was promoted.

## Conclusion

This window proves the current clean TheIsland flow can capture accepted start/end
lifecycle observer events under the scoped runtime window, but it still does not produce
the complete approved copied runtime triplet. The active blocker remains
`approved_runtime_evidence_missing`; the next runtime window must still capture the exact
`CheckJoinInProgress(1,0)` `session_start_rejected` role between start and matched end.
