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
skill. Before server-backed validation, read that file for context only; it is never
standing approval. Marker edits, start/stop/restart commands, runtime observation,
ReflectionScanner, native exec probes, ptrace/gcore, broad ProcessEvent tracing,
text/gameplay-payload logging, beta/community notices, and player-facing validation all
require explicit current-turn operator approval for the exact scoped run. Approval must
name the target instance, marker/env gates, start/stop/restart window, rollback plan,
evidence paths, notice path when applicable, and shutdown/posture expectation. Agents may
use only that current-turn approved scope. Request packs, preflight outputs, and accepted
planning artifacts can support an approval request, but they do not authorize markers,
env changes, runtime observation, starts, stops, restarts, Discord, runtime readiness, or
public SDK readiness. Do not write or execute an operational runbook
unless those details are named for the current turn.

## Production Baseline

Keep production/shared baselines simple: ProcessEvent hook enabled only when intended,
plugins disabled unless a maintenance window explicitly scopes a plugin test,
scanner/native-exec/broad tracing off, and no restarts or marker edits without
current-turn approval for the exact scoped run. Server restarts are never implied by
research progress: require explicit current-turn operator approval for the exact instance
and restart window, and only request it when new runtime logs are needed after a concrete
offline/code advance.
Offline config preparation tools must not read `ShooterGameServer` directly from
`/servidor/ark`; use a copied offline binary artifact or an explicit, recorded SHA256.
Offline evidence-pack and release-readiness report tools must not write under protected
live-server paths or historical dump subdirectories. `/servidor/ark/workspace-offline` is
the only approved under-`/servidor/ark` offline workspace; otherwise use `/tmp` or another
current-turn operator-approved offline artifact workspace.

```bash
# Only run marker/start/stop commands when that exact change is part of a
# current-turn operator-approved debug/development instance test window:
# mkdir -p /servidor/ark/obelisk/state/instances/<approved-instance-id>
# touch /servidor/ark/obelisk/state/instances/<approved-instance-id>/enable-process-event-hook
# touch /servidor/ark/obelisk/state/instances/<approved-instance-id>/disable-plugins
# env -u TMUX ./<approved-instance-id> start
```

Expected logs:

- runtime loaded through `LD_PRELOAD`
- ProcessEvent hook installed
- plugin loading disabled
- server remains joinable

Post-checks after a current-turn approved runtime experiment should use the same exact
target and should reject experimental observers unless the current-turn maintenance plan
explicitly says otherwise:

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
  - `enable-chat-events`
  - `enable-chat-reflection`
  - `enable-chat-route-observer`
  - `enable-structure-reflection`
  - `enable-inventory-reflection`
  - `enable-item-return-events`
  - `enable-player-principal-lifecycle-observer`
- The player-principal lifecycle evidence window is stricter than a normal observer
  window: plugins disabled, `OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0`,
  log limit `1..10`, exact observer exclusivity, and no debug/scanner/callback escape
  markers. The wrapper must reject residual observer markers or symlink marker entries
  on the same instance, and approved evidence must be copied/analyzed as a single-module
  `player_principal_lifecycle` summary only. Evidence bundles must be bound to a checked
  `--window-manifest` whose source path/SHA match the analyzed copied log and preserve
  stable posture, rollback, no-claim, and no-public-readiness semantics. This remains
  consume-only and does not promote public player identity, lookup, permissions, commands,
  or SDK completion.
- Runtime debug/scanner gates also require both env and instance markers:
  - `allow-ptrace`
  - `enable-debug-control`
  - `enable-reflection-scanner`
  - `enable-native-exec-probes`
- Never enable native exec probes without explicit current-turn operator approval for the
  named debug run.
- Do not set `OBELISK_DEBUG_ALLOW_PTRACE=1` by default in debug wrappers. Ptrace requires
  a current-turn approved isolated run plus the `allow-ptrace` marker.
- Never enable `ReflectionScanner` on a player-facing instance while users are active.
  When the operator explicitly selects a live/beta instance for in-game function testing,
  keep the window narrow: announce the test through the current-turn operator-approved
  notice path before activation, enable only the markers required by the exact feature
  under test, preserve copied-log evidence, avoid raw player text/identity logging, and
  make marker/env rollback explicit.
- Never persist `OBELISK_WRAPPER_PROFILE=observer-debug` in a normal service environment.
  It is a per-launch debug-window profile for the normal wrapper.
- Keep `OBELISK_PE_TRACE_LIMIT=0` by default; use short trace windows only for
  current-turn approved exact evidence windows.
- Do not move debug instrumentation to any player-facing instance until the same posture
  is proven on the current approved isolated target and the operator gives current-turn
  approval for an exact privacy-bounded player signal window.

## Debug Profiles

Use named profiles instead of ad hoc env mixes:

- Stable dev: ProcessEvent hook on, plugins disabled, scanner/static roots/native exec off.
- Runtime debug control: plugins disabled, scanner/native exec off,
  `enable-debug-control` marker enabled only for a short window, request marker consumed,
  then immediate restart back to stable dev.
- Scanner capture: current-turn operator-approved debug window only, named instance,
  plugins disabled, native exec off, one scanner env family enabled, copied logs analyzed
  offline, then immediate restart back to stable dev inside the same current-turn approved
  window.
- Plugin capture: scanner off, only the target plugin installed, plugin config backed up,
  short run, then return to stable dev.
- Item-return copied-event capture: current-turn operator-approved debug window only,
  named instance, plugin/subscriber plan explicit, `enable-item-return-events` gated by
  observer-debug markers, positive dispatch budget, optional bounded log budget, copied
  logs analyzed offline, then return to stable dev.

After any scanner/plugin capture, run the posture check for the same current-turn approved
debug target:

```bash
scripts/check_obelisk_server_posture.sh --expect-stable \
  --map <map> --instance <instance-id>
```

Use the matching explicit `--map` and `--instance` for the current-turn approved debug
target. That check must pass before launching another agent round that assumes a stable
server.
In `--expect-stable` mode it must fail closed if `libobelisk.so` is not mapped, if a
deleted `libobelisk` mapping remains after redeploy, if `LD_PRELOAD` does not include the
central `${OBELISK_ROOT}/lib/libobelisk.so`, if scanner/native-exec variables are still
present, if stable markers `enable-process-event-hook` and `disable-plugins` are missing,
if the instance id or marker directory would be rejected by the wrapper/runtime, if
chat, chat-route, inventory, or structure observer variables are present, or if per-instance marker entries
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

Before a current-turn approved restart, these checks are read-only context:

```bash
git -C /home/flowcommunity-ark/Obelisk status --short
scripts/check_linuxgsm_wrapper_drift.sh \
  --installed /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh
ls -la /servidor/ark/obelisk/lib /servidor/ark/obelisk/plugins
ls -la /servidor/ark/obelisk/state
```

After a current-turn approved maintenance-window restart on a protected live-like
instance, use the profile named for that exact run and explicit map/instance values:

```bash
pgrep -af '^./ShooterGameServer'
tail -n 100 /path/to/copied/Obelisk.log
pid=$(pgrep -f '^./ShooterGameServer <map>' | head -n1)
rg 'libobelisk|libsubhook' /proc/$pid/maps
scripts/check_obelisk_server_posture.sh --expect-stable \
  --map <map> --instance <instance-id>
```

Current server-backed debug target context comes from `docs/agent-handoff/CURRENT.md`, but
that file does not grant approval. The target may be a dedicated debug instance or a
current-turn approved beta-test instance. For powered-off debug instances, start only for
the exact scoped test, restore stable posture, then shut down when the current-turn run
plan requires it. For player-facing beta instances, do not assume shutdown; follow the
current-turn approved maintenance/beta window:

```bash
tail -n 100 /servidor/ark/obelisk/logs/<instance-id>/Obelisk.log
pid=$(pgrep -f '^./ShooterGameServer <map>' | head -n1)
rg 'libobelisk|libsubhook' /proc/$pid/maps
scripts/check_obelisk_server_posture.sh --expect-stable \
  --map <map> --instance <instance-id>
```

## Rollback

If a current-turn approved target crashes after an Obelisk change, preserve logs/core
files first. For a powered-off debug target, stop it at the end of the exact test or
rollback window. For a player-facing beta target, restore the current-turn approved stable
markers/config and restart only if the maintenance plan requires it:

```bash
# Preserve evidence first.
# mkdir -p /servidor/ark/obelisk/state/instances/<instance-id>
# touch /servidor/ark/obelisk/state/instances/<instance-id>/disable-plugins
# env -u TMUX ./<instance-id> stop
```

Preserve logs and core files before rebuilding or changing markers again.
