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
