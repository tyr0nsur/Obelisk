---
name: obelisk-live-ops
description: "Use when operating Obelisk on ARK server instances: central install root, arkmanager wrappers, per-instance state markers, log symlinks, config restore backups, restart safety, isolated debug instances, and production experiment gates."
---

# Obelisk Live Ops

Use this skill when touching server deployment, `/servidor/ark`, arkmanager scripts,
runtime marker files, restore backups, or operational checks after installing Obelisk.
Even if an operator calls both instances "development", treat shared/public/clustered
instances as live-like until an isolated debug instance is confirmed.

## Live Layout

Central root:

```text
/servidor/ark/obelisk/
  lib/
  plugins/
  config/
  logs/
  state/instances/
```

Managed subdirectories under the central root must be real directories, not symlinks.
Runtime/plugin installers own layout creation, and `PluginManager` should fail closed if
the plugin directory is missing, a symlink, or not a directory.

Only the thin launcher/wrapper should live inside the ARK binary directory. Runtime
libraries, plugin `.so` files, plugin config, logs, and state markers belong under the
central Obelisk root.
Wrappers must fail before exporting `LD_PRELOAD` when `OBELISK_ROOT` is relative, `/`, a
symlink, missing managed directories, or has a symlinked `lib/libobelisk.so`. They must
execute the `ShooterGameServer` located beside the wrapper, not a CWD-relative binary.

Convenience log links may live under:

```text
/home/flowcommunity-ark/logs/ark/
```

Current instance posture belongs in `docs/agent-handoff/CURRENT.md`, not in this durable
skill. Before server-backed validation, read that file. If it grants standing approval for
`arkserver2` / TheIsland, the lead may start, stop, restart, and adjust Obelisk markers for
scoped debug/development tests on that instance without asking again. Other instances still
require explicit operator approval for the target instance, marker changes, restart window,
rollback plan, and whether the server must be shut down afterward. ReflectionScanner,
native exec probes, ptrace/gcore, broad ProcessEvent tracing, and text/gameplay-payload
logging must still have a written scoped run plan before activation.

## Production Baseline

Keep production/shared baselines simple: ProcessEvent hook enabled only when intended,
plugins disabled unless a maintenance window explicitly scopes a plugin test,
scanner/native-exec/broad tracing off, and no restarts or marker edits without approval.
Offline config preparation tools must not read `ShooterGameServer` directly from
`/servidor/ark`; use a copied offline binary artifact or an explicit, recorded SHA256.
Offline evidence-pack and release-readiness report tools must not write under
`/servidor/ark`, including historical dump subdirectories; use `/tmp` or another offline
artifact workspace.

```bash
# Only run marker/start/stop commands when that change is part of an approved
# debug/development instance test window:
# mkdir -p /servidor/ark/obelisk/state/instances/arkserver2
# touch /servidor/ark/obelisk/state/instances/arkserver2/enable-process-event-hook
# touch /servidor/ark/obelisk/state/instances/arkserver2/disable-plugins
# env -u TMUX ./arkserver2 start
```

Expected logs:

- runtime loaded through `LD_PRELOAD`
- ProcessEvent hook installed
- plugin loading disabled
- server remains joinable

Post-checks after an approved runtime experiment should use the same approved target and
should reject experimental observers unless the maintenance plan explicitly says otherwise:

```bash
scripts/check_obelisk_server_posture.sh --expect-stable \
  --map <map> --instance <instance-id>
```

## Experiment Gates

- Keep experimental plugins outside `plugins/` until an isolated server test passes.
- Publish plugin `.so` files with
  `scripts/install_obelisk_plugin.sh <PluginName.so> <obelisk-root>` or an equivalent
  staged non-`.so` copy plus atomic rename. Do not copy directly into the active shared
  plugin directory while ARK instances may restart.
- Enable one marker/config gate at a time and record the exact change.
- Use instance markers under `state/instances/<instance-id>/`; map markers are obsolete.
- Experimental runtime observers must have their own instance markers in addition to env
  gates, `OBELISK_WRAPPER_PROFILE=observer-debug`, `allow-observer-debug-window`, and
  `allow-experimental-observers` on the same instance. Current observer markers:
  - `allow-observer-debug-window`
  - `allow-experimental-observers`
  - `enable-chat-reflection`
  - `enable-structure-reflection`
  - `enable-inventory-reflection`
- Runtime debug/scanner gates also require both env and instance markers:
  - `allow-ptrace`
  - `enable-debug-control`
  - `enable-reflection-scanner`
  - `enable-native-exec-probes`
- Never enable native exec probes without explicit approval for the named debug run.
- Do not set `OBELISK_DEBUG_ALLOW_PTRACE=1` by default in debug wrappers. Ptrace requires
  an approved isolated run plus the `allow-ptrace` marker.
- Never enable `ReflectionScanner` on `arkserver` / Ragnarok while users are active.
  Current operator direction grants standing use of `arkserver2` / TheIsland as the debug
  target when runtime validation is needed; keep plugins disabled unless the test
  explicitly requires them, preserve copied-log evidence, make marker/env rollback
  explicit, and shut down TheIsland when the test window no longer needs it.
- Never persist `OBELISK_WRAPPER_PROFILE=observer-debug` in a normal service environment.
  It is a per-launch debug-window profile for the normal wrapper.
- Keep `OBELISK_PE_TRACE_LIMIT=0` by default; use short trace windows only for approved
  evidence windows on `arkserver2`.
- Do not move debug instrumentation to player-facing `arkserver` / Ragnarok until the same
  posture is proven on `arkserver2` and the operator approves a privacy-bounded player
  signal window.

## Debug Profiles

Use named profiles instead of ad hoc env mixes:

- Stable dev: ProcessEvent hook on, plugins disabled, scanner/static roots/native exec off.
- Runtime debug control: plugins disabled, scanner/native exec off,
  `enable-debug-control` marker enabled only for a short window, request marker consumed,
  then immediate restart back to stable dev.
- Scanner capture: operator-approved debug window only, named instance, plugins disabled,
  native exec off, one scanner env family enabled, copied logs analyzed offline, then
  immediate restart back to stable dev inside the same approved window.
- Plugin capture: scanner off, only the target plugin installed, plugin config backed up,
  short run, then return to stable dev.

After any scanner/plugin capture, run the posture check for the same approved debug target:

```bash
scripts/check_obelisk_server_posture.sh --expect-stable \
  --map <map> --instance <instance-id>
```

Use the matching explicit `--map` and `--instance` for the approved debug target. That
check must pass before launching another agent round that assumes a stable server.
In `--expect-stable` mode it must fail closed if `libobelisk.so` is not mapped, if a
deleted `libobelisk` mapping remains after redeploy, if `LD_PRELOAD` does not include the
central `${OBELISK_ROOT}/lib/libobelisk.so`, if scanner/native-exec variables are still
present, if stable markers `enable-process-event-hook` and `disable-plugins` are missing,
if the instance id or marker directory would be rejected by the wrapper/runtime, if
chat/inventory/structure observer variables are present, or if per-instance marker entries
would re-enable forbidden experimental features at the next restart. It rejects a
forbidden marker name even when the entry is malformed or a symlink.
Its parser is tested offline with procfs fixtures; do not weaken those tests to depend on a
live ARK process.

## Runtime Debug Control

`OBELISK_ENABLE_DEBUG_CONTROL=1` watches:

```text
/servidor/ark/obelisk/state/instances/<instance-id>/
```

Current request marker:

```text
request-static-fname-probe
```

Use it to trigger bounded probes after the ARK process is already alive. Do not use it as
stable posture, and do not leave `enable-debug-control` present after the capture.

Known result: a post-start probe of `0x5956f30` on `arkserver` worked mechanically but
rejected the slot (`table=0x13733660`, `implausible_num_elements`). This proves waiting
longer in bootstrap is not the right strategy; next work should scan live data mappings or
derive roots from code/data references instead of pinning that single slot.

## Overnight Supervision

Unattended cron-style work may collect read-only snapshots only:

- git status/log head,
- server posture,
- LinuxGSM wrapper drift status,
- recent Obelisk logs,
- marker list,
- disk/memory/process summary.

Do not let cron build, install, restart, edit marker files, attach debuggers, run gcore,
enable scanners, commit, push, or create GitHub state. Those require an active lead turn.

## Config Restore Backups

Before SteamCMD/LinuxGSM updates or risky server config work, refresh the gameplay config
backup described in `docs/SERVER_RESTORE.md`. The latest symlink should be:

```text
/home/flowcommunity-ark/backups/ark-config-latest
```

Preserve at minimum:

```text
/servidor/ark/serverfiles/ShooterGame/Saved/Config/LinuxServer/Game.ini
/servidor/ark/serverfiles/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini
/servidor/ark/lgsm/config-lgsm/arkserver/*.cfg
```

Do not restore old binary-local `libobelisk.so`, `ObeliskPlugins/`, logs, or state markers
as part of config recovery.

## Operational Checks

Before restart:

```bash
git -C /home/flowcommunity-ark/Obelisk status --short
scripts/check_linuxgsm_wrapper_drift.sh \
  --installed /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh
ls -la /servidor/ark/obelisk/lib /servidor/ark/obelisk/plugins
ls -la /servidor/ark/obelisk/state
```

After a maintenance-window restart on a protected live-like instance, use that instance's
approved profile and explicit map/instance values:

```bash
pgrep -af '^./ShooterGameServer'
tail -n 100 /path/to/copied/Obelisk.log
pid=$(pgrep -f '^./ShooterGameServer <map>' | head -n1)
rg 'libobelisk|libsubhook' /proc/$pid/maps
scripts/check_obelisk_server_posture.sh --expect-stable \
  --map <map> --instance <instance-id>
```

Current server-backed debug uses `arkserver2` / TheIsland. It normally starts from powered
off, runs the scoped test, restores stable posture, then shuts down when no longer needed:

```bash
tail -n 100 /servidor/ark/obelisk/logs/arkserver2/Obelisk.log
pid=$(pgrep -f '^./ShooterGameServer TheIsland' | head -n1)
rg 'libobelisk|libsubhook' /proc/$pid/maps
scripts/check_obelisk_server_posture.sh --expect-stable \
  --map TheIsland --instance arkserver2
```

## Rollback

If `arkserver2` crashes after an Obelisk change, preserve logs/core files first. Stop
TheIsland at the end of the test or rollback window:

```bash
# Preserve evidence first.
# mkdir -p /servidor/ark/obelisk/state/instances/arkserver2
# touch /servidor/ark/obelisk/state/instances/arkserver2/disable-plugins
# env -u TMUX ./arkserver2 stop
```

Preserve logs and core files before rebuilding or changing markers again.
