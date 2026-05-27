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

For current Obelisk debug/development work, use `arkserver2` / TheIsland instead of
Ragnarok. For scanner or reflection research that needs stronger isolation, use the debug
wrapper from `ObeliskRunDebug.sh` on a separate instance such as
`arkserver-obelisk-debug`; do not reuse live map markers for debug captures.
For `gcore`, `ptrace`, ReflectionScanner, broad tracing, or scanner-like probes,
`arkserver2` is an explicit fallback, not the default target.

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
# Approved debug window only. Do not run from an ordinary install or agent round.
# mkdir -p /servidor/ark/obelisk/state/instances/arkserver2
# touch /servidor/ark/obelisk/state/instances/arkserver2/<approved-marker>
```

Do not create, remove, or refresh `arkserver` / Ragnarok markers from install or debug
rounds. Treat the Ragnarok marker list as observed baseline unless the operator opens a
Ragnarok maintenance window in the current turn. Experimental module markers, scanners,
ptrace/gcore, broad tracing, and restarts require explicit run-window approval.

Useful flags:

```text
state/instances/<instance-id>/enable-process-event-hook
state/instances/<instance-id>/disable-plugins
state/instances/<instance-id>/enable-chat-reflection  # experimental
state/instances/<instance-id>/enable-inventory-reflection  # experimental, metadata-only
state/instances/<instance-id>/enable-structure-reflection  # experimental, metadata-only
```

`enable-chat-reflection` makes the wrapper set:

```text
OBELISK_ENABLE_CHAT_REFLECTION=1
OBELISK_CHAT_REFLECTION_BINARY_SHA256=<supported ARK SHA256>
OBELISK_CHAT_REFLECTION_LOG_LIMIT=25
```

`enable-structure-reflection` makes the wrapper set:

```text
OBELISK_ENABLE_STRUCTURE_REFLECTION=1
OBELISK_STRUCTURE_REFLECTION_BINARY_SHA256=<supported ARK SHA256>
OBELISK_STRUCTURE_REFLECTION_LOG_LIMIT=0
```

The structure log limit is also the observation budget and defaults to `0`, so the marker
alone does not read reflected structure fields. A short debug window must set an explicit
non-zero budget, and stable posture checks reject these variables.

`enable-inventory-reflection` follows the same policy:

```text
OBELISK_ENABLE_INVENTORY_REFLECTION=1
OBELISK_INVENTORY_REFLECTION_BINARY_SHA256=<supported ARK SHA256>
OBELISK_INVENTORY_REFLECTION_LOG_LIMIT=0
```

Inventory reflection is internal metadata observation only. It must not expose item ids,
contents, player identity, or gameplay-authoritative overrides.

Decoded chat text logging is not enabled by the marker. It requires an additional explicit
environment gate:

```text
OBELISK_CHAT_REFLECTION_LOG_TEXT=1
```

Rollback is removing the marker and restarting the instance. The stable production posture
is still process-event hook enabled, plugins disabled for debug, and chat reflection off
unless a development validation run explicitly needs it.

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

While Ragnarok is under player performance testing, use `arkserver2` / TheIsland for
debug/development markers and validation windows.
