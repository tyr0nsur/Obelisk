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
  config/plugins/<plugin-id>/config.json
  config/instances/
  logs/
  state/
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

It also creates `plugins`, `config/plugins`, `config/instances`, `logs`, and `state`.

Plugins loaded from `plugins/` are expected to own their config defaults. The preferred
path for plugin config is:

```text
/servidor/ark/obelisk/config/plugins/<plugin-id>/config.json
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

## Feature Flags

Marker files are preferred for production operations:

```bash
touch /servidor/ark/obelisk/state/enable-process-event-hook-ragnarok
touch /servidor/ark/obelisk/state/disable-plugins-ragnarok
rm -f /servidor/ark/obelisk/state/disable-plugins-ragnarok
```

Useful flags:

```text
enable-process-event-hook-ragnarok
disable-plugins-ragnarok
enable-chat-discovery-ragnarok
enable-process-event-hook-theisland
disable-plugins-theisland
enable-chat-discovery-theisland
```

## Logs

Runtime logs are written to:

```text
/servidor/ark/obelisk/logs/Obelisk.log
/servidor/ark/obelisk/logs/Obelisk-Ragnarok.log
/servidor/ark/obelisk/logs/Obelisk-TheIsland.log
/servidor/ark/obelisk/logs/isolated-debug/
```

## Current Safe Production Posture

For live servers, the safest known posture is:

```text
enable-process-event-hook-ragnarok
disable-plugins-ragnarok
```

This validates the core ProcessEvent hook without loading experimental plugins.
