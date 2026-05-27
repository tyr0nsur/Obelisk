# Obelisk

Obelisk is a Linux-native modding runtime, API, and SDK foundation for
Unreal Engine dedicated server processes.

The goal is to bring an ArkApi/DarkApi-style developer experience to Linux:
central runtime injection, Unreal Engine event hooks, a stable C plugin ABI,
reflection utilities, and reusable server-side modding APIs.

ARK: Survival Evolved is the current debug harness used to validate the
runtime inside a real stripped UE4 Linux server. Obelisk's public surface should
remain the runtime/API/SDK layer; ARK-specific operational details belong in
debug harness documentation and install notes.

## Current Status

Obelisk is in active reverse-engineering and runtime stabilization work.
See [docs/STATUS.md](docs/STATUS.md) for the contributor-facing stable,
experimental, and not-ready matrix.

Runtime baseline:

- LD_PRELOAD bootstrap for `ShooterGameServer`.
- Centralized runtime layout under an operator-chosen Obelisk root.
- Absolute x64 hook for `UObject::ProcessEvent`.
- Per-instance logs.
- Runtime feature flags per server instance.

API baseline:

- C ABI plugin loading.
- `ObeliskPlugin_GetInfo` metadata validation.
- `ObeliskPlugin_Init(api, context)` initialization.
- Filtered ProcessEvent callbacks by `FName` index.
- Plugin-owned callback cleanup and optional plugin shutdown.

SDK status:

- Higher-level SDK APIs are not ready yet.
- Player, tribe, inventory, dino, permission, timer, and command abstractions
  remain roadmap items.

Research:

- Raw reflection scanner.
- FString/FName inference.
- GNames/GObjects-backed reflection.

Harness:

- ARK: Survival Evolved validates the runtime in a real stripped UE4 Linux
  server process.
- LinuxGSM wrappers are adapters for the ARK debug harness, not the core
  project interface.

Not production-ready:

- General-purpose chat interception.
- Full GObjects/GNames reflection.

## Why Obelisk Exists

Linux dedicated server binaries often ship stripped and without a clean native
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
plugins/oBaseEvents/ First official example plugin for events and plugin structure
docs/                Contributor and operator documentation
scripts/             Install/deploy helpers
```

Plugin structure and promotion rules are documented in
[docs/PLUGIN_ARCHITECTURE.md](docs/PLUGIN_ARCHITECTURE.md).

## Runtime Layout

The recommended install layout is an operator-chosen Obelisk root. The current
ARK harness uses this concrete path:

```text
/servidor/ark/obelisk/
  lib/
    libobelisk.so
    libsubhook.so
  plugins/
  config/
    plugins/
      <plugin-id>/
        <plugin-config-file>
  logs/
    arkserver/
      Obelisk.log
      Obelisk-Ragnarok.log
    arkserver2/
      Obelisk.log
      Obelisk-TheIsland.log
  state/
    instances/
      arkserver/
        enable-process-event-hook
        disable-plugins
```

See [docs/INSTALL.md](docs/INSTALL.md).

## ARK Debug Harness

The current harness runs Obelisk inside `ShooterGameServer` with `LD_PRELOAD`.
The ARK binary directory only needs a thin `ObeliskRun.sh` wrapper. Versioned
LinuxGSM templates live under `packaging/linuxgsm/`.

This harness is for validating loader, hook, logging, marker, and plugin ABI
behavior against a real UE4 Linux server. Do not treat ARK paths, map names, or
observed `FName` indices as stable SDK contracts.

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
build/plugins/oBaseEvents/oBaseEvents.so
build/_deps/subhook-build/libsubhook.so
```

`oBaseEvents` is the first official plugin target. It is intentionally small: it validates
the C ABI, creates a safe default config, demonstrates a filtered `ProcessEvent` callback,
and exports `ObeliskPlugin_Shutdown`.

See [docs/oBaseEvents.md](docs/oBaseEvents.md).

## Plugin Example

```cpp
#include "api/ObeliskApi.h"

static bool OnProcessEvent(void* caller, void* function, void* params)
{
    return true;
}

extern "C" __attribute__((visibility("default")))
bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out)
{
    if (!out)
        return false;

    out->abi_version = OBELISK_PLUGIN_METADATA_ABI_VERSION;
    out->struct_size = sizeof(ObeliskPluginMetadata);
    out->plugin_id = "example";
    out->name = "Example Plugin";
    out->version = "0.1.0";
    out->config_file = "config.json";
    out->default_config_json = "{\"enabled\":false}\n";
    return true;
}

extern "C" __attribute__((visibility("default")))
bool ObeliskPlugin_Init(ObeliskApi* api, const ObeliskPluginInitContext* context)
{
    if (!api)
        return false;
    if (api->abi_version != OBELISK_API_ABI_VERSION ||
        api->struct_size < sizeof(ObeliskApi))
        return false;
    if (!context ||
        context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
        context->struct_size < sizeof(ObeliskPluginInitContext))
        return false;

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
OBELISK_INSTANCE_ID
OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
OBELISK_DISABLE_PLUGINS=1
OBELISK_ENABLE_REFLECTION_SCANNER=1
OBELISK_PE_TRACE_LIMIT=0
```

Marker files are usually placed under the selected Obelisk root. The current
ARK harness uses:

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
- Document reversing workflows and signatures per target binary version.

## Contributing

Contributors are welcome, especially in these areas:

- Linux ELF/x86_64 hooking
- Unreal Engine 4 reflection
- UE4/Linux dedicated server internals
- ARK harness internals
- C ABI plugin systems
- CMake and packaging
- Documentation and reproducible test environments

Start with [CONTRIBUTING.md](CONTRIBUTING.md) and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Use
[docs/STATUS.md](docs/STATUS.md) to choose work that matches the current
safety posture.

## Safety Notes

The current harness runs Obelisk inside `ShooterGameServer`. A bad hook or
unsafe plugin can crash the whole target process.

For debug harness servers:

- Enable hooks per instance, not globally.
- Keep experimental scanners disabled by default.
- Prefer filtered callbacks.
- Keep logs per instance.
- Test new plugins on one map before rolling out cluster-wide.
