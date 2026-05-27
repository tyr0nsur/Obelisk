# Obelisk

Obelisk is a Linux-native runtime and plugin framework for dedicated
ARK: Survival Evolved servers.

The goal is to bring an ArkApi/DarkApi-style developer experience to Linux:
central runtime injection, Unreal Engine event hooks, a stable C plugin ABI,
reflection utilities, and reusable server-side modding APIs.

## Current Status

Obelisk is in active reverse-engineering and runtime stabilization work.
See [docs/STATUS.md](docs/STATUS.md) for the contributor-facing stable,
experimental, and not-ready matrix.

Stable enough to test:

- LD_PRELOAD bootstrap for `ShooterGameServer`.
- Centralized runtime layout under `/servidor/ark/obelisk`.
- Absolute x64 hook for `UObject::ProcessEvent`.
- C ABI plugin loading.
- Filtered ProcessEvent callbacks by `FName` index.
- Per-map logs.
- Runtime feature flags per server instance.

Experimental:

- Chat command discovery.
- Raw reflection scanner.
- FString/FName inference.
- Higher-level SDK APIs.

Not production-ready yet:

- General-purpose chat interception.
- Full GObjects/GNames reflection.
- Player, tribe, inventory, dino, permission, and command abstractions.

## Why Obelisk Exists

ARK's Linux dedicated server binary is stripped and does not expose a clean
plugin interface. Most mature server API ecosystems were built around Windows
tooling and binary assumptions.

Obelisk takes the Linux path:

- ELF runtime injection via `LD_PRELOAD`.
- Native Linux memory and module inspection.
- x86_64-safe detours.
- C ABI boundary for plugins.
- UE4 reflection and `ProcessEvent` as the long-term compatibility layer.

## Repository Layout

```text
api/                 Public C ABI exposed to plugins
core/                Event manager and plugin manager
hooks/               Runtime hooks, including ProcessEvent
loader/              LD_PRELOAD bootstrap
runtime/             Logging and runtime services
ue/                  UE4 memory/reflection helpers
plugins/chat/        Experimental chat plugin
plugins/monitor/     Experimental monitoring plugin
agent-skills/        Local engineering/reversing notes
docs/                Contributor and operator documentation
scripts/             Install/deploy helpers
```

Plugin structure and promotion rules are documented in
[docs/PLUGIN_ARCHITECTURE.md](docs/PLUGIN_ARCHITECTURE.md). `plugins/monitor`
is experimental and intentionally not part of the top-level stable build.

## Central Server Layout

The recommended install layout is:

```text
/servidor/ark/obelisk/
  lib/
    libobelisk.so
    libsubhook.so
  plugins/
    ChatPlugin.so
  config/
    plugins/
      chat_config.json
  logs/
    Obelisk.log
    Obelisk-Ragnarok.log
    Obelisk-TheIsland.log
  state/
    enable-process-event-hook-ragnarok
    disable-plugins-ragnarok
```

The ARK binary directory only needs a thin `ObeliskRun.sh` wrapper. Versioned LinuxGSM
templates live under `packaging/linuxgsm/`.

See [docs/INSTALL.md](docs/INSTALL.md).

## Build

Requirements:

- Linux x86_64
- CMake 3.22+
- C++20 compiler
- Git

```bash
cmake -S . -B build
cmake --build build -j"$(nproc)"
```

Main build outputs:

```text
build/libobelisk.so
build/plugins/chat/ChatPlugin.so
build/helloworld_plugin/HelloWorldPlugin.so
build/_deps/subhook-build/libsubhook.so
```

## Plugin Example

```cpp
#include "api/ObeliskApi.h"

static bool OnProcessEvent(void* caller, void* function, void* params)
{
    return true;
}

extern "C" __attribute__((visibility("default")))
bool ObeliskPlugin_Init(ObeliskApi* api)
{
    api->LogInfo("Plugin loaded");

    // Use a validated FName index from your own reflection research/config.
    // Do not treat observed ARK indices as stable API contracts.
    const int32_t validated_function_index = -1;
    if (validated_function_index >= 0)
        api->RegisterPreProcessEventForNameIndex(validated_function_index, OnProcessEvent);

    return true;
}
```

Prefer filtered callbacks whenever possible. Subscribing to every
`ProcessEvent` is very expensive and unsafe until a plugin has strict guards.

## Runtime Flags

Obelisk uses environment variables and marker files to keep risky features
explicit.

Important variables:

```text
OBELISK_ROOT
OBELISK_PLUGIN_DIR
OBELISK_CONFIG_DIR
OBELISK_LOG_DIR
OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
OBELISK_DISABLE_PLUGINS=1
OBELISK_CHAT_DISCOVERY=1
OBELISK_ENABLE_REFLECTION_SCANNER=1
OBELISK_PE_TRACE_LIMIT=0
```

Marker files are usually placed in:

```text
/servidor/ark/obelisk/state/
```

## Roadmap

High-priority engineering:

- Resolve `FName` indices to real names through GNames/FNamePool.
- Build a safe reflection layer for GObjects and UFunction lookup.
- Replace raw chat memory scanning with reflection-backed parameter decoding.
- Add first-class APIs: chat commands, players, permissions, timers, RCON helpers.
- Create small plugin examples for minimal load, filtered `ProcessEvent`, config,
  and HTTP status patterns.
- Document reversing workflows and signatures per ARK server version.

## Contributing

Contributors are welcome, especially in these areas:

- Linux ELF/x86_64 hooking
- Unreal Engine 4 reflection
- ARK server internals
- C ABI plugin systems
- CMake and packaging
- Documentation and reproducible test environments

Start with [CONTRIBUTING.md](CONTRIBUTING.md) and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Use
[docs/STATUS.md](docs/STATUS.md) to choose work that matches the current
safety posture.

## Safety Notes

Obelisk runs inside `ShooterGameServer`. A bad hook or unsafe plugin can crash
the whole server process.

For live servers:

- Enable hooks per map, not globally.
- Keep experimental scanners disabled by default.
- Prefer filtered callbacks.
- Keep logs per instance.
- Test new plugins on one map before rolling out cluster-wide.
