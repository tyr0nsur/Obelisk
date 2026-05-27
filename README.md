# Obelisk

Obelisk is a Linux-native modding runtime, C API, and SDK foundation for Unreal
Engine dedicated server processes.

It aims to bring an ArkApi/DarkApi-style developer experience to Linux without
porting Windows assumptions: runtime injection, UE event hooks, a stable plugin
ABI, reflection-driven research tooling, and eventually reusable gameplay APIs.

ARK: Survival Evolved is currently the debug harness used to validate Obelisk
inside a real stripped UE4 Linux server. ARK/LinuxGSM details are validation
adapters, not the core product surface.

## Status

Stable baseline:

- `LD_PRELOAD` bootstrap for the current debug harness.
- Absolute x64 `UObject::ProcessEvent` hook with target validation.
- C ABI plugin loading through `ObeliskPlugin_GetInfo` and
  `ObeliskPlugin_Init(api, context)`.
- Runtime-owned plugin config under `${OBELISK_CONFIG_DIR}/<plugin-id>/config.json`.
- Plugin-owned callback cleanup and optional `ObeliskPlugin_Shutdown`.
- Public SDK header at `include/obelisk/ObeliskApi.h`.
- CTest coverage for plugin config and ABI layout.

Experimental:

- ReflectionScanner and offline analyzer tooling.
- FName/GNames/GObjects/UFunction discovery.
- Binary-hash-gated chat reflection observation.
- Internal UTF-32 `FString` decoder candidate.
- General reflected parameter decoding beyond the current chat path.

Not ready:

- General-purpose chat interception.
- Player, tribe, inventory, dino, permission, timer, and command APIs.
- Production-ready gameplay SDK.

See [docs/STATUS.md](docs/STATUS.md) for the current stability matrix and
[docs/VERSIONING.md](docs/VERSIONING.md) for the pre-release versioning policy.

## Why Obelisk

Linux dedicated server binaries are often stripped and do not expose a clean
native plugin interface. Obelisk takes the Linux path:

- ELF runtime injection via `LD_PRELOAD`.
- Native Linux memory and module inspection.
- x86_64-safe detours.
- A C ABI boundary for plugins.
- UE4 reflection and `ProcessEvent` as the long-term compatibility layer.

## Repository Layout

```text
include/obelisk/      Public SDK headers for plugin authors
api/                  Transitional include wrappers
core/                 Event manager, plugin manager, config validation
hooks/                Runtime hooks, including ProcessEvent
loader/               LD_PRELOAD bootstrap
runtime/              Logging and runtime services
ue/                   UE4 memory/reflection helpers
plugins/oBaseEvents/  First official example plugin
tests/                Offline C++/SDK/ABI tests
docs/                 Architecture, install, research, release notes
scripts/              Install and offline analyzer helpers
packaging/            Harness adapters and wrapper templates
```

Plugin policy is documented in
[docs/PLUGIN_ARCHITECTURE.md](docs/PLUGIN_ARCHITECTURE.md).

## Build And Test

Requirements:

- Linux x86_64
- CMake 3.22+
- C++20 compiler
- Git

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build -j"$(nproc)"
ctest --test-dir build --output-on-failure
python3 scripts/test_analyze_reflectionscanner_capture.py
python3 scripts/test_scan_core_fname_tables.py
python3 scripts/test_enumerate_core_uobjects.py
python3 scripts/test_inspect_core_ufunctions.py
python3 scripts/test_build_core_dump_evidence_pack.py
python3 scripts/test_verify_chat_reflection_constants.py
python3 scripts/test_summarize_core_ufunction_inventory.py
python3 scripts/test_ufunction_snapshot_fixtures.py
python3 scripts/test_regenerate_ufunction_snapshots.py
python3 scripts/test_research_doc_guardrails.py
python3 scripts/test_public_sdk_chat_guardrails.py
python3 scripts/test_dependency_pins.py
python3 scripts/test_versioning_guardrails.py
python3 scripts/test_secret_guardrails.py
python3 scripts/test_repo_hygiene.py
scripts/install_obelisk.sh --dry-run /tmp/obelisk-install-check
```

Main build outputs:

```text
build/libobelisk.so
build/plugins/oBaseEvents/oBaseEvents.so
build/_deps/subhook-build/libsubhook.so
```

## Runtime Layout

Obelisk installs under an operator-chosen root. The current ARK debug harness
uses `/servidor/ark/obelisk`:

```text
/servidor/ark/obelisk/
  lib/
    libobelisk.so
    libsubhook.so
  plugins/
    PluginName.so
  config/
    <plugin-id>/
      config.json
  logs/
    <instance-id>/
      Obelisk.log
      Obelisk-<Map>.log
  state/
    instances/
      <instance-id>/
        enable-process-event-hook
        disable-plugins
        enable-chat-reflection  # experimental
```

The target binary directory should only need a thin launcher/wrapper. Runtime
libraries, plugins, config, logs, and state markers belong under the Obelisk
root. See [docs/INSTALL.md](docs/INSTALL.md).

## Public Plugin ABI

Plugins compile against:

```cpp
#include <obelisk/ObeliskApi.h>
```

Minimal shape:

```cpp
#include <obelisk/ObeliskApi.h>

static bool OnProcessEvent(void* caller, void* function, void* params)
{
    (void)caller;
    (void)function;
    (void)params;
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
    if (!api || !context)
        return false;
    if (api->abi_version != OBELISK_API_ABI_VERSION ||
        api->struct_size < sizeof(ObeliskApi))
        return false;
    if (context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
        context->struct_size < sizeof(ObeliskPluginInitContext))
        return false;

    api->LogInfo("Plugin loaded");

    const int32_t validated_function_index = -1;
    if (validated_function_index >= 0)
        api->RegisterPreProcessEventForNameIndex(validated_function_index, OnProcessEvent);

    return true;
}
```

Prefer filtered callbacks. Global `ProcessEvent` callbacks are hot-path debug
tools unless explicitly measured and gated.

The first official example is [oBaseEvents](docs/oBaseEvents.md).

## ARK Debug Harness

The current harness runs Obelisk inside `ShooterGameServer` with `LD_PRELOAD`.
LinuxGSM wrapper templates live under `packaging/linuxgsm/`.

This harness validates loader, hook, logging, marker, and plugin ABI behavior
against a real UE4 Linux server. Do not treat ARK paths, map names, or observed
`FName` indices as stable SDK contracts.

## Runtime Controls

Important environment variables:

```text
OBELISK_ROOT
OBELISK_PLUGIN_DIR
OBELISK_CONFIG_DIR
OBELISK_LOG_DIR
OBELISK_INSTANCE_ID
OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
OBELISK_DISABLE_PLUGINS=1
OBELISK_ENABLE_REFLECTION_SCANNER=1
OBELISK_ENABLE_CHAT_REFLECTION=1
OBELISK_CHAT_REFLECTION_BINARY_SHA256=<supported ARK SHA256>
OBELISK_CHAT_REFLECTION_LOG_LIMIT=25
OBELISK_CHAT_REFLECTION_LOG_TEXT=1  # extra opt-in for decoded experimental chat text
OBELISK_PE_TRACE_LIMIT=0
```

Experimental scanners and native exec probes stay opt-in. Reflection captures
belong on isolated/debug instances only.

## Roadmap

Near-term engineering:

- Keep CI as a real quality gate: build, CTest, analyzer tests, SDK consumer
  fixture, and install dry-run.
- Validate the local UTF-32 `FString` chat-text logger in a controlled runtime window
  while keeping chat reflection experimental.
- Define copied-data ownership and callback lifetime before exposing a plugin-facing chat
  event.
- Generalize FName/GObjects/UFunction lookup only after another capture or binary hash
  validates the current field layout.
- Add small SDK examples for minimal load, filtered events, config, and safe
  lifecycle.

Later:

- Chat commands.
- Players, permissions, timers, RCON helpers.
- Tribe, inventory, dino, and gameplay APIs.

## Contributing

Useful starting points:

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/STATUS.md](docs/STATUS.md)
- [docs/PLUGIN_ARCHITECTURE.md](docs/PLUGIN_ARCHITECTURE.md)
- [docs/research/](docs/research/)

High-value areas:

- Linux ELF/x86_64 hooking.
- UE4 reflection and reverse engineering.
- C ABI/plugin lifecycle design.
- CMake, SDK packaging, and CI.
- Offline analyzers and reproducible research notes.

## Safety

Obelisk runs inside the target server process. A bad hook or unsafe plugin can
crash that process.

For debug harness validation:

- Enable hooks per instance, not globally.
- Keep experimental scanners disabled by default.
- Keep native exec probes off unless explicitly isolated.
- Prefer filtered callbacks.
- Keep logs per instance.
- Do not promote observed offsets or `FName` indices without repeatable evidence.
