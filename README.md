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
- Multi-instance plugin rollout through `OBELISK_INSTANCE_ID` and
  `instance_allowlist`; shared config is supported, while runtime handles and mutable
  state stay process-local unless a plugin implements explicit cross-process locking.
- Plugin-owned callback cleanup and optional `ObeliskPlugin_Shutdown`.
- Public SDK header at `include/obelisk/ObeliskApi.h`.
- CTest coverage for plugin config and ABI layout.

Experimental:

- ReflectionScanner and offline analyzer tooling.
- FName/GNames/GObjects/UFunction discovery.
- Binary-hash-gated runtime observers for candidate modules.
- Internal UTF-32 `FString` decoder candidate.
- Sanitized UFunction/ScriptStruct snapshot fixtures and second-source comparison tooling.
- General reflected parameter decoding beyond candidate-only module recognizers.

Not ready:

- Public gameplay module APIs: players, chat, tribes, inventory, items, dinos,
  structures, missions, transfers, permissions, timers, admin, and commands.
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
scripts/run_script_tests.sh
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
        enable-inventory-reflection  # experimental
        enable-structure-reflection  # experimental
        allow-ptrace  # approved debug window only
        enable-debug-control  # approved debug window only
        enable-reflection-scanner  # approved debug window only
        enable-native-exec-probes  # never on live/shared instances
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
#include <cstddef>

static ObeliskApi* g_api = nullptr;
static uint64_t g_owner_token = 0;
static uint64_t g_pre_handle = 0;

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
    out->default_config_json =
        "{\"enabled\":false,\"allow_all_instances\":false,\"instance_allowlist\":[]}\n";
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

    g_api = api;
    g_owner_token = context->plugin_owner_token;
    api->LogInfo("Plugin loaded");

    const int32_t validated_function_index = -1;
    if (validated_function_index >= 0 &&
        (api->capabilities & OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES) &&
        api->struct_size >= offsetof(ObeliskApi, UnregisterProcessEventCallbackWithOwnerToken) +
            sizeof(api->UnregisterProcessEventCallbackWithOwnerToken))
    {
        g_pre_handle = api->RegisterPreProcessEventForNameIndexWithOwnerTokenHandle(
            g_owner_token, validated_function_index, OnProcessEvent);
        if (g_pre_handle == 0)
            api->LogWarn("Filtered ProcessEvent callback registration was rejected");
    }

    return true;
}

extern "C" __attribute__((visibility("default")))
void ObeliskPlugin_Shutdown()
{
    if (g_api && g_pre_handle != 0)
        g_api->UnregisterProcessEventCallbackWithOwnerToken(g_owner_token, g_pre_handle);
    g_api = nullptr;
    g_owner_token = 0;
    g_pre_handle = 0;
}
```

Prefer filtered callbacks. Global `ProcessEvent` callbacks are hot-path debug
tools unless explicitly measured and gated.

Callbacks registered after `ObeliskPlugin_Init`, from helper libraries, or from background
threads should use the owner-token registration fields appended to `ObeliskApi`. New
plugins should prefer the handle-returning owner-token functions when
`OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES` is advertised, store returned
handles only in process-local state, and unregister them with
`UnregisterProcessEventCallbackWithOwnerToken` during shutdown. Handles are not cluster
state: never write them into shared plugin config or assume they are valid in another ARK
server process. Legacy registration functions reject callbacks that cannot be attributed
to the initializing plugin or an already-loaded plugin shared object.

`CallProcessEvent` is a low-level trampoline escape hatch. If a pre-callback calls it,
that callback should return `false`; if it returns `true`, the runtime skips the automatic
original call and warns to avoid double execution. Stable plugin APIs should prefer
higher-level Obelisk module surfaces as they are promoted.

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

Experimental runtime controls that can affect server safety require both their environment
variable and the matching instance marker under
`OBELISK_ROOT/state/instances/<OBELISK_INSTANCE_ID>/`:

```text
OBELISK_DEBUG_ALLOW_PTRACE=1             + allow-ptrace
OBELISK_ENABLE_DEBUG_CONTROL=1           + enable-debug-control
OBELISK_ENABLE_REFLECTION_SCANNER=1      + enable-reflection-scanner
OBELISK_ENABLE_NATIVE_EXEC_PROBES=1      + enable-native-exec-probes
```

Experimental scanners, candidate module observers, text logging, and native exec probes
stay opt-in. Reflection captures belong on isolated/debug instances only. Do not use these
controls on Ragnarok performance posture, and use TheIsland only during an explicitly
approved debug window for the named instance and rollback plan.

## Roadmap

Near-term engineering:

- Keep CI as a real quality gate: build, CTest, analyzer tests, SDK consumer
  fixture, and install dry-run.
- Strengthen sanitized reflection snapshots, manifest regeneration, and second-source
  comparison for candidate modules.
- Define copied-data ownership and callback lifetime before exposing any plugin-facing
  gameplay event.
- Generalize FName/GObjects/UFunction lookup only after another capture or binary hash
  validates the current field layout.
- Add small SDK examples for minimal load, filtered events, config, and safe
  lifecycle.

Later:

- Public module APIs for players, chat, tribes, inventory, items, dinos, structures,
  missions, transfers, permissions, timers, admin, and commands.

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
- Treat multi-instance plugins as the normal clustered case: shared config is fine,
  shared mutable state requires an explicit ownership and locking design.
- Do not promote observed offsets or `FName` indices without repeatable evidence.
