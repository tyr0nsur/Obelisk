# arkserver2 Runtime SDK Fast Path

## Scope

2026-06-04 operator update: `arkserver2` on `TheIsland` is approved as the
debug/development target for necessary ObeliskSDK runtime work and launch acceleration.
The immediate SDK blocker remains approved copied runtime principal lifecycle evidence.

This approval is target-specific. It does not grant Discord publication, GitHub
publication, broad ProcessEvent tracing, raw player text/gameplay payload logging,
ReflectionScanner, native-exec probes, ptrace/gcore, Frida/rr, public SDK readiness, or
v1 completion claims.

## Fastest Safe Route

1. Commit the current validated hardening checkpoint so runtime evidence can bind to a
   reviewed 40-character Obelisk commit.
2. Rebuild `libobelisk.so`.
3. Refresh `/servidor/ark/obelisk` with `scripts/install_obelisk.sh --backup-existing`.
4. Refresh `/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh` from
   `packaging/linuxgsm/ObeliskRun.sh`; read-only preflight found wrapper drift.
5. Prepare a fresh player-principal lifecycle request pack for a short future window on
   `arkserver2` / `TheIsland`.
6. Use only the player-principal lifecycle observer markers/env, plugins disabled,
   dispatch limit `0`, log limit `10`, and no scanner/debug/callback escape markers.
7. Start or restart `arkserver2` only inside the scoped window, copy `Obelisk.log` to the
   run evidence directory, rollback observer markers/env to stable posture, then run the
   post-window checks.
8. Build the approved runtime principal lifecycle evidence bundle and route proof. The
   expected route transition is from `approved_runtime_evidence_missing` to locked
   `identity_public_contract_gate_missing`, with all public/runtime/promotion/v1 flags
   still false.

## Observed Preflight

- `scripts/check_player_principal_lifecycle_preflight.sh --instance arkserver2 --map
  TheIsland --mode stable --expected-binary-sha256
  7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520 --allow-stopped
  --json` failed on LinuxGSM wrapper drift before any marker/runtime changes.
- `scripts/check_obelisk_server_posture.sh --expect-stable --map TheIsland --instance
  arkserver2` reported no running `ShooterGameServer` process for `TheIsland`.
- `scripts/install_obelisk.sh --build-dir build --dry-run /servidor/ark/obelisk` printed
  the expected staged runtime/SDK install plan without changing files.

## 20260603T233330Z Runtime Window Result

Artifacts:

```text
/servidor/ark/workspace-offline/live-validation-logs/20260603T233330Z-player-principal-lifecycle/
```

Window:

- approved start: `2026-06-03T23:33:30Z`
- approved end: `2026-06-03T23:41:30Z`
- actual observer capture: `2026-06-03T23:33:54Z` to `2026-06-03T23:40:00Z`
- rollback completed: `2026-06-03T23:40:23Z`; manifest rollback end recorded as
  `2026-06-03T23:40:50Z` to include the stable post-check sidecar.

Accepted operational facts:

- LinuxGSM wrapper matched the versioned template before the run.
- Pre-window observer preflight passed with `offline_only=false` and `allow_stopped=false`.
- Runtime log showed native LD_PRELOAD load, ProcessEvent candidate count `1`, candidate
  address `0x1d34e20`, absolute hook patch size `18`, ReflectionScanner disabled, plugins
  disabled, and a single player-principal lifecycle observer gate:
  `limit=10`, `dispatch_limit=0`, `delivery_claim=none`, `principal_claim=none`.
- Post-window manifest replay is accepted with verified completed operator receipt.
- Stable rollback left only `disable-plugins` and `enable-process-event-hook` markers on
  `arkserver2`; stable posture/preflight passed and the new server process has no observer
  env.

Rejected evidence result:

```text
analyze_runtime_observer_log failed with exit 1:
runtime observer summary has quality blockers:
player_principal_lifecycle: no_accepted_or_rejected_observer_lines
```

No approved runtime-principal lifecycle evidence manifest was produced. The route remains
`approved_runtime_evidence_missing`.

Reason: no ARK client/player was available during the window, so startup produced the
observer gate but no `HandleNewPlayer` or `OnLogout` lifecycle events. Accepted evidence
requires real lifecycle activity in the copied log: `session_start`,
`session_start_rejected`, and `session_end`.

## Passive Wait Correction

After additional short windows, the operator correctly pointed out that repeated restarts
make it unlikely for organic players to join. The live-ops posture changed from timed
window chaining to passive presence detection:

- stop scheduled player-principal window controllers instead of allowing another
  automatic rollback/restart while waiting for players;
- leave running ARK processes alone;
- remove future observer markers from `arkserver2` so a future normal restart does not
  inherit the observer window;
- monitor player count with local Steam query only, not LinuxGSM `monitor`;
- open the next bounded observer/evidence window only after real player presence is
  detected or the operator gives a fresh exact instruction.

Integrated helper:

```bash
scripts/monitor_ark_player_presence_passive.sh --interval 30 \
  arkserver:Ragnarok arkserver2:TheIsland
```

Implementation facts:

- `arkserver` / `Ragnarok` query port: `27015`
- `arkserver2` / `TheIsland` query port: `27016`
- this installed GameDig catalog uses type `ase`; old alias `arkse` returns
  `{"error":"Invalid game: arkse"}` and must be treated as a query error, not as
  `0` players
- the helper never calls LinuxGSM `monitor`, `start`, `stop`, or `restart`, and never
  edits markers
- the detached monitor log/PID were placed outside `/servidor/ark`:
  `/tmp/obelisk-player-presence-monitor.log` and
  `/tmp/obelisk-player-presence-monitor.pid`

Observed passive check at `2026-06-04T00:21:07Z`: both `Ragnarok` and `TheIsland` were
queryable with `players=0/70`, maps matched expected values, and both current server
processes carried `-ActiveEvent=Summer`.

## Required Evidence Siblings

Each run must preserve this exact sibling set under
`/servidor/ark/workspace-offline/live-validation-logs/<run-id>/`:

- `window-request.json`
- `observer-window.env`
- `operator-approval-request.md`
- completed `operator-approval-receipt.json`
- `preflight-pre.json`
- `preflight-post.json`
- `window-manifest.env`
- copied `Obelisk.log`

The generated receipt template is not evidence. The completed receipt must bind the
request pack for the current run.

## Non-Claims

This fast path is intended to clear the runtime evidence blocker only. It does not promote
player identity/principal, permissions/admin, command response, commands/replies,
ResourceHandle, lookup, mutation, return override, runtime readiness, public SDK
readiness, or complete/stable v1 SDK status.
