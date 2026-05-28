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

Only the thin launcher/wrapper should live inside the ARK binary directory. Runtime
libraries, plugin `.so` files, plugin config, logs, and state markers belong under the
central Obelisk root.

Convenience log links may live under:

```text
/home/flowcommunity-ark/logs/ark/
```

Current operator direction as of 2026-05-28:

- RAM is currently tight. Keep `arkserver2` / TheIsland stopped unless the operator
  explicitly reopens it.
- `arkserver` / Ragnarok is now operator-approved as the active Obelisk development/test
  harness. Use it for controlled runtime validation and plugin lifecycle checks, with
  one gate at a time, copied evidence, and rollback to stable posture.
- ReflectionScanner, native exec probes, ptrace/gcore, broad ProcessEvent tracing, and
  text/gameplay-payload logging still require a specific operator-approved run window and
  rollback plan before activation on `arkserver`.

## Production Baseline

Ragnarok is the current development/test harness. Keep its stable baseline simple:
ProcessEvent hook enabled, plugins disabled unless a plugin test is explicitly in scope,
scanner/native-exec/broad tracing off, and posture checked after any marker or restart.

```bash
# Only run marker/restart commands when that change is part of the active approved test:
# mkdir -p /servidor/ark/obelisk/state/instances/arkserver
# touch /servidor/ark/obelisk/state/instances/arkserver/enable-process-event-hook
# touch /servidor/ark/obelisk/state/instances/arkserver/disable-plugins
# env -u TMUX ./arkserver restart
```

Expected logs:

- runtime loaded through `LD_PRELOAD`
- ProcessEvent hook installed
- plugin loading disabled
- server remains joinable

Post-check for the current protected Ragnarok baseline should also reject experimental chat
reflection unless the maintenance plan explicitly says otherwise:

```bash
scripts/check_obelisk_server_posture.sh --expect-stable --forbid-chat-reflection
```

## Experiment Gates

- Keep experimental plugins outside `plugins/` until an isolated server test passes.
- Enable one marker/config gate at a time and record the exact change.
- Use instance markers under `state/instances/<instance-id>/`; map markers are obsolete.
- Experimental runtime observers must have their own instance markers in addition to env
  gates. Current observer markers:
  - `enable-chat-reflection`
  - `enable-structure-reflection`
  - `enable-inventory-reflection`
- Never enable native exec probes without explicit approval for the named `arkserver` run.
- Never enable `ReflectionScanner` on `arkserver` without a specific operator-approved
  debug window, plugins disabled, copied-log evidence, and a marker/env rollback plan.
- Keep `OBELISK_PE_TRACE_LIMIT=0` by default; use short trace windows only for approved
  evidence windows on `arkserver`.
- Do not start `arkserver2` to get extra isolation while RAM is constrained.

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

After any scanner/plugin capture, run:

```bash
scripts/check_obelisk_server_posture.sh --expect-stable --forbid-chat-reflection \
  --map Ragnarok --instance arkserver
```

Use the matching explicit `--map` and `--instance` for the approved debug target. That
check must pass before launching another agent round that assumes a stable server.
In `--expect-stable` mode it must fail closed if `libobelisk.so` is not mapped, if a
deleted `libobelisk` mapping remains after redeploy, or if scanner/native-exec variables
are still present. Its parser is tested offline with procfs fixtures; do not weaken those
tests to depend on a live ARK process.

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
ls -la /servidor/ark/obelisk/lib /servidor/ark/obelisk/plugins
ls -la /servidor/ark/obelisk/state
```

After a maintenance-window Ragnarok restart, use the protected live-like profile:

```bash
pgrep -af '^./ShooterGameServer'
tail -n 100 /servidor/ark/obelisk/logs/arkserver/Obelisk.log
pid=$(pgrep -f '^./ShooterGameServer Ragnarok' | head -n1)
rg 'libobelisk|libsubhook' /proc/$pid/maps
scripts/check_obelisk_server_posture.sh --expect-stable --forbid-chat-reflection \
  --map Ragnarok --instance arkserver
```

Current routine debug uses Ragnarok/`arkserver` because the operator made it available and
`arkserver2` is stopped for RAM pressure:

```bash
tail -n 100 /servidor/ark/obelisk/logs/arkserver/Obelisk.log
pid=$(pgrep -f '^./ShooterGameServer Ragnarok' | head -n1)
rg 'libobelisk|libsubhook' /proc/$pid/maps
scripts/check_obelisk_server_posture.sh --expect-stable --forbid-chat-reflection \
  --map Ragnarok --instance arkserver
```

## Rollback

If a live map crashes after an Obelisk change, preserve logs/core files first. Restarting
Ragnarok is maintenance-window work and should be lead/operator approved:

```bash
# Maintenance-window-only for Ragnarok; do not run during normal agent rounds.
# mkdir -p /servidor/ark/obelisk/state/instances/arkserver
# touch /servidor/ark/obelisk/state/instances/arkserver/disable-plugins
# ./arkserver start  # Maintenance-window-only for Ragnarok.
```

Preserve logs and core files before rebuilding or changing markers again.
