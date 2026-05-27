# Ops Restart Audit After OBELISK_INSTANCE_ID

Date: 2026-05-27

Scope: read-only audit of `/servidor/ark` before applying the instance-aware wrapper and
runtime. No server files were edited and no servers were restarted during this audit.

## Current Runtime State

- `arkserver2` / TheIsland is still running the old binary-local preload:
  - `LD_PRELOAD=./libobelisk.so`
  - deleted mappings for `libobelisk.so`, `libsubhook.so`, and
    `ObeliskPlugins/ChatPlugin.so`
- `arkserver` / Ragnarok is running from the centralized root:
  - `LD_PRELOAD=/servidor/ark/obelisk/lib/libobelisk.so`
  - `LD_LIBRARY_PATH=/servidor/ark/obelisk/lib:`
  - deleted mappings for centralized `libobelisk.so` and `libsubhook.so`
- Disk is clean of active legacy plugin artifacts:
  - no `ChatPlugin`
  - no `HelloWorld`
  - no `MonitorPlugin`
  - no `ObeliskPlugins`
  - no `chat_config.json`
  - no active `.bak` runtime libraries under `/servidor/ark`

## LinuxGSM Config State

- `common.cfg` sets `executable="./ObeliskRun.sh"`.
- `arkserver.cfg` also sets `executable="./ObeliskRun.sh"` explicitly.
- `arkserver2.cfg` inherits the executable from `common.cfg`.
- Both instances are development instances, but they still share the cluster id
  `MiClusterArk`.

## Wrapper Gap

The live wrapper in:

```text
/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh
```

is older than the repo template. It sets root/plugin/config/log env vars and handles only
map-specific markers. It does not export `OBELISK_INSTANCE_ID`.

The repo template now sets:

```text
Ragnarok  -> OBELISK_INSTANCE_ID=arkserver
TheIsland -> OBELISK_INSTANCE_ID=arkserver2
```

and checks markers only under:

```text
state/instances/<instance-id>/<feature>
```

## Marker State

Current disk markers before migration:

```text
/servidor/ark/obelisk/state/enable-process-event-hook-ragnarok
/servidor/ark/obelisk/state/disable-plugins-ragnarok
```

Required instance markers before restart:

```text
/servidor/ark/obelisk/state/instances/arkserver/enable-process-event-hook
/servidor/ark/obelisk/state/instances/arkserver/disable-plugins
```

Optional safety marker for TheIsland while plugin development is settling:

```text
/servidor/ark/obelisk/state/instances/arkserver2/disable-plugins
```

## Restart Plan

> Historical restart plan. Do not execute the Ragnarok portion while player performance
> testing is active. Any `arkserver` restart now requires an explicit operator maintenance
> window; debug/development validation should use `arkserver2` or, for high-risk captures,
> `arkserver-obelisk-debug`.

1. Build and install the current repo runtime into the centralized root:

   ```bash
   cd /home/flowcommunity-ark/Obelisk
   cmake --build build -j"$(nproc)"
   ./scripts/install_obelisk.sh --backup-existing /servidor/ark/obelisk
   ```

2. Copy the versioned production wrapper into the ARK binary directory:

   ```bash
   install -m 755 packaging/linuxgsm/ObeliskRun.sh \
     /servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh
   ```

3. Historical instance marker creation from this maintenance window:

   ```text
   Historical only; do not rerun on Ragnarok during normal agent rounds.
   state/instances/arkserver/enable-process-event-hook
   state/instances/arkserver/disable-plugins
   state/instances/arkserver2/disable-plugins
  ```

   Remove obsolete map markers after instance markers exist:

   ```bash
   rm -f /servidor/ark/obelisk/state/enable-process-event-hook-ragnarok
   rm -f /servidor/ark/obelisk/state/disable-plugins-ragnarok
   rm -f /servidor/ark/obelisk/state/enable-process-event-hook-theisland
   rm -f /servidor/ark/obelisk/state/disable-plugins-theisland
   ```

4. Restart one approved instance at a time through LinuxGSM:

   ```bash
   cd /servidor/ark
   ./arkserver2 restart
   # ./arkserver restart  # Maintenance-window-only for Ragnarok.
   ```

   `arkserver2` should go first because it is still carrying the old binary-local runtime
   and deleted `ChatPlugin` mapping.

5. Verify mappings and environment after each restart before moving to the next instance.

## Verification Commands

List running ARK processes:

```bash
pgrep -af 'ShooterGameServer|ObeliskRun|arkserver'
```

Inspect Obelisk environment per process:

```bash
for pid in $(pgrep -f ShooterGameServer); do
  echo "## PID $pid"
  tr '\0' '\n' < /proc/$pid/environ | rg '^(OBELISK|LD_PRELOAD|LD_LIBRARY_PATH)=' || true
done
```

Check that no deleted Obelisk libraries remain mapped:

```bash
for pid in $(pgrep -f ShooterGameServer); do
  echo "## PID $pid"
  rg 'obelisk|subhook|ChatPlugin|ObeliskPlugins|deleted' /proc/$pid/maps || true
done
```

Confirm expected logs:

```bash
ls -lah /servidor/ark/obelisk/logs
tail -n 80 /servidor/ark/obelisk/logs/arkserver/Obelisk.log
tail -n 80 /servidor/ark/obelisk/logs/arkserver/Obelisk-Ragnarok.log
tail -n 80 /servidor/ark/obelisk/logs/arkserver2/Obelisk.log
tail -n 80 /servidor/ark/obelisk/logs/arkserver2/Obelisk-TheIsland.log
```

Confirm there are no active legacy artifacts:

```bash
find /servidor/ark -xdev \( \
  -iname '*ChatPlugin*' -o \
  -iname '*HelloWorld*' -o \
  -iname '*MonitorPlugin*' -o \
  -iname 'ObeliskPlugins' -o \
  -iname 'chat_config.json' -o \
  -iname 'libobelisk.so.bak*' -o \
  -iname 'libsubhook.so.bak*' \
\) -print
```

## Expected Post-Restart State

- `arkserver` logs under `/servidor/ark/obelisk/logs/arkserver/`.
- `arkserver2` logs under `/servidor/ark/obelisk/logs/arkserver2/`.
- No `/proc/<pid>/maps` line for Obelisk should include `(deleted)`.
- TheIsland should no longer map binary-local `libobelisk.so`, `libsubhook.so`, or
  `ObeliskPlugins/ChatPlugin.so`.
- Plugin loading should remain disabled on Ragnarok; TheIsland should also have plugins
  disabled if `state/instances/arkserver2/disable-plugins` is present.
