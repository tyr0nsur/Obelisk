# Installation

This guide describes the centralized LinuxGSM layout used by Obelisk.

## Build

```bash
cd /home/flowcommunity-ark/Obelisk
cmake -S . -B build
cmake --build build -j"$(nproc)"
```

## Install Layout

Recommended root:

```text
/servidor/ark/obelisk/
  lib/
  plugins/
  config/<plugin-id>/<plugin-config-file>
  logs/<instance-id>/
  state/instances/<instance-id>/
```

Install the runtime:

```bash
./scripts/install_obelisk.sh --backup-existing /servidor/ark/obelisk
```

The script copies:

```text
build/libobelisk.so                         -> lib/libobelisk.so
build/_deps/subhook-build/libsubhook.so     -> lib/libsubhook.so
```

It also creates `plugins`, `config`, `logs`, and `state/instances`.

Plugins loaded from `plugins/` are expected to own their config defaults. The preferred
directory for plugin config is:

```text
/servidor/ark/obelisk/config/<plugin-id>/
```

The runtime loads every `.so` directly inside `/servidor/ark/obelisk/plugins/` on restart.
If a plugin should not load, do not place it in `plugins/`.

Useful installer flags:

```text
--dry-run
--backup-existing
```

## LinuxGSM Wrapper

Versioned wrapper templates live in:

```text
packaging/linuxgsm/ObeliskRun.sh
packaging/linuxgsm/ObeliskRunDebug.sh
packaging/linuxgsm/arkserver-obelisk-debug.cfg.example
```

Place the production wrapper in:

```text
ShooterGame/Binaries/Linux/ObeliskRun.sh
```

Then configure LinuxGSM:

```ini
executable="./ObeliskRun.sh"
```

For scanner or reflection research, use the debug wrapper from `ObeliskRunDebug.sh` on a
separate instance such as `arkserver-obelisk-debug`; do not reuse live map markers for
debug captures.

## Instance Identity

`OBELISK_INSTANCE_ID` identifies the LinuxGSM instance, not the ARK map. The production
wrapper sets known defaults:

```text
Ragnarok  -> arkserver
TheIsland -> arkserver2
Debug     -> arkserver-obelisk-debug
```

Operators can override it before launching the wrapper.

## Feature Flags

Instance marker files are preferred for production operations:

```bash
mkdir -p /servidor/ark/obelisk/state/instances/arkserver
touch /servidor/ark/obelisk/state/instances/arkserver/enable-process-event-hook
touch /servidor/ark/obelisk/state/instances/arkserver/disable-plugins
```

Useful flags:

```text
state/instances/<instance-id>/enable-process-event-hook
state/instances/<instance-id>/disable-plugins
```

Map markers such as `enable-process-event-hook-ragnarok` are obsolete and are not read by
the release wrapper.

## Logs

Runtime logs are written to:

```text
/servidor/ark/obelisk/logs/arkserver/Obelisk.log
/servidor/ark/obelisk/logs/arkserver/Obelisk-Ragnarok.log
/servidor/ark/obelisk/logs/arkserver2/Obelisk.log
/servidor/ark/obelisk/logs/arkserver2/Obelisk-TheIsland.log
/servidor/ark/obelisk/logs/isolated-debug/
```

The LinuxGSM wrapper sets `OBELISK_INSTANCE_ID`. Custom launchers should set it explicitly
before loading Obelisk.

## Current Safe Production Posture

For live servers, the safest known posture is:

```text
state/instances/arkserver/enable-process-event-hook
state/instances/arkserver/disable-plugins
```

This validates the core ProcessEvent hook without loading experimental plugins.
