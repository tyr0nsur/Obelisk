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
  config/plugins/
  logs/
  state/
```

Install the runtime:

```bash
./scripts/install_obelisk.sh /servidor/ark/obelisk
```

The script copies:

```text
build/libobelisk.so                         -> lib/libobelisk.so
build/_deps/subhook-build/libsubhook.so     -> lib/libsubhook.so
build/plugins/chat/ChatPlugin.so            -> plugins/ChatPlugin.so
```

It also creates `config/plugins`, `logs`, and `state`.

## LinuxGSM Wrapper

Place `ObeliskRun.sh` in:

```text
ShooterGame/Binaries/Linux/ObeliskRun.sh
```

Example wrapper:

```bash
#!/bin/bash
export OBELISK_ROOT="/servidor/ark/obelisk"
export OBELISK_PLUGIN_DIR="${OBELISK_ROOT}/plugins"
export OBELISK_CONFIG_DIR="${OBELISK_ROOT}/config"
export OBELISK_LOG_DIR="${OBELISK_ROOT}/logs"
export LD_LIBRARY_PATH="${OBELISK_ROOT}/lib:${LD_LIBRARY_PATH}"
export LD_PRELOAD="${OBELISK_ROOT}/lib/libobelisk.so"

case "$1" in
    Ragnarok*)
        [[ -f "${OBELISK_ROOT}/state/enable-process-event-hook-ragnarok" ]] && export OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
        [[ -f "${OBELISK_ROOT}/state/disable-plugins-ragnarok" ]] && export OBELISK_DISABLE_PLUGINS=1
        [[ -f "${OBELISK_ROOT}/state/enable-chat-discovery-ragnarok" ]] && export OBELISK_CHAT_DISCOVERY=1
        ;;
    TheIsland*)
        [[ -f "${OBELISK_ROOT}/state/enable-process-event-hook-theisland" ]] && export OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
        [[ -f "${OBELISK_ROOT}/state/disable-plugins-theisland" ]] && export OBELISK_DISABLE_PLUGINS=1
        [[ -f "${OBELISK_ROOT}/state/enable-chat-discovery-theisland" ]] && export OBELISK_CHAT_DISCOVERY=1
        ;;
esac

exec ./ShooterGameServer "$@"
```

Then configure LinuxGSM:

```ini
executable="./ObeliskRun.sh"
```

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
```

## Current Safe Production Posture

For live servers, the safest known posture is:

```text
enable-process-event-hook-ragnarok
disable-plugins-ragnarok
```

This validates the core ProcessEvent hook without loading experimental plugins.
