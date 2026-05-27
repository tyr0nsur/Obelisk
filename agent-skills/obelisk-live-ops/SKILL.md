---
name: obelisk-live-ops
description: Use when operating Obelisk on ARK server instances: central install root, arkmanager wrappers, per-instance state markers, log symlinks, config restore backups, restart safety, isolated debug instances, and production experiment gates.
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

## Production Baseline

For Ragnarok live-like stability:

```bash
mkdir -p /servidor/ark/obelisk/state/instances/arkserver
touch /servidor/ark/obelisk/state/instances/arkserver/enable-process-event-hook
touch /servidor/ark/obelisk/state/instances/arkserver/disable-plugins
./arkserver restart
```

Expected logs:

- runtime loaded through `LD_PRELOAD`
- ProcessEvent hook installed
- plugin loading disabled
- server remains joinable

## Experiment Gates

- Keep experimental plugins outside `plugins/` until an isolated server test passes.
- Enable one marker/config gate at a time and record the exact change.
- Use instance markers under `state/instances/<instance-id>/`; map markers are obsolete.
- Never enable native exec probes on live servers.
- Never enable `ReflectionScanner` on `arkserver` or `arkserver2` unless the operator has
  explicitly converted that instance into an isolated debug target.
- Keep `OBELISK_PE_TRACE_LIMIT=0` by default; use short trace windows only for evidence.
- Prefer the planned `arkserver-obelisk-debug` instance for scanner captures. Use distinct
  ports, save directory, cluster id, and `OBELISK_LOG_DIR`; do not reuse live map markers.

## Debug Profiles

Use named profiles instead of ad hoc env mixes:

- Stable dev: ProcessEvent hook on, plugins disabled, scanner/static roots/native exec off.
- Scanner capture: plugins disabled, native exec off, one scanner env family enabled, copied
  logs analyzed offline, then immediate restart back to stable dev.
- Plugin capture: scanner off, only the target plugin installed, plugin config backed up,
  short run, then return to stable dev.

After any scanner/plugin capture, run:

```bash
scripts/check_obelisk_server_posture.sh --expect-stable
```

That check must pass before launching another agent round that assumes a stable server.
In `--expect-stable` mode it must fail closed if `libobelisk.so` is not mapped, if a
deleted `libobelisk` mapping remains after redeploy, or if scanner/native-exec variables
are still present. Its parser is tested offline with procfs fixtures; do not weaken those
tests to depend on a live ARK process.

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

After restart:

```bash
pgrep -af '^./ShooterGameServer'
tail -n 100 /servidor/ark/obelisk/logs/arkserver/Obelisk.log
pid=$(pgrep -f '^./ShooterGameServer Ragnarok' | head -n1)
rg 'libobelisk|libsubhook' /proc/$pid/maps
scripts/check_obelisk_server_posture.sh --expect-stable
```

## Rollback

If a live map crashes after an Obelisk change:

```bash
mkdir -p /servidor/ark/obelisk/state/instances/arkserver
touch /servidor/ark/obelisk/state/instances/arkserver/disable-plugins
./arkserver start
```

Preserve logs and core files before rebuilding or changing markers again.
