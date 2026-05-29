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
- Central install and LinuxGSM wrapper guardrails, including read-only wrapper drift
  checks before maintenance restarts.
- Plugin-owned callback cleanup and optional `ObeliskPlugin_Shutdown`.
- Public SDK header at `include/obelisk/ObeliskApi.h`.
- Promoted `GameplayPolicyEvent` callback ABI for copied POD structure and
  inventory-backed policy signals.
- Metadata-only `DescribeResourceKind` helper for category descriptors; no resource
  handles or lookup yet.
- CTest coverage for plugin config and ABI layout.

Experimental:

- ReflectionScanner and offline analyzer tooling.
- FName/GNames/GObjects/UFunction discovery.
- Binary-hash-gated runtime observers for candidate modules.
- Internal UTF-32 `FString` decoder candidate.
- Sanitized UFunction/ScriptStruct snapshot fixtures and second-source comparison tooling.
- General reflected parameter decoding beyond candidate-only module recognizers.

Not ready:

- Public gameplay module APIs beyond `GameplayPolicyEvent`: players, chat, tribes,
  inventory, items, dinos, full structure/resources APIs, missions, transfers,
  permissions, timers, admin, and commands.
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
[docs/PLUGIN_ARCHITECTURE.md](docs/PLUGIN_ARCHITECTURE.md). The initial read-only
operator CLI is documented in [docs/OPERATOR_CLI.md](docs/OPERATOR_CLI.md).

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
scripts/test_install_obelisk_layout.sh /tmp/obelisk-layout-check
```

Main build outputs:

```text
build/libobelisk.so
build/plugins/oBaseEvents/oBaseEvents.so
build/_deps/subhook-build/libsubhook.so
```

## Runtime Layout

Obelisk installs under an operator-chosen root, referenced in docs as
`<obelisk-root>`:

```text
<obelisk-root>/
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
        allow-experimental-observers  # required with experimental observer markers
        enable-chat-reflection  # experimental
        enable-inventory-reflection  # experimental
        enable-structure-reflection  # experimental
        allow-ptrace  # approved debug window only
        enable-debug-control  # approved debug window only
        enable-reflection-scanner  # approved debug window only
        enable-native-exec-probes  # never on live/shared instances
        allow-global-process-event-callbacks  # experimental SDK callback scope
        allow-call-process-event  # experimental outbound UE call surface
```

The target binary directory should only need a thin launcher/wrapper. Runtime
libraries, plugins, config, logs, and state markers belong under the Obelisk
root. Use `scripts/check_linuxgsm_wrapper_drift.sh` before maintenance restarts to
confirm the installed LinuxGSM wrapper still matches the versioned template. See
[docs/INSTALL.md](docs/INSTALL.md).

## Public Plugin ABI

Plugins compile against:

```cpp
#include <obelisk/ObeliskApi.h>
```

External plugins should consume the installed SDK package:

```cmake
find_package(Obelisk 0.1.0 CONFIG REQUIRED)
target_link_libraries(MyPlugin PRIVATE Obelisk::obelisk_sdk)
```

Minimal shape:

```cpp
#include <obelisk/ObeliskApi.h>
#include <cstddef>

static ObeliskApi g_api{};
static bool g_has_api = false;
static uint64_t g_owner_token = 0;
static uint64_t g_pre_handle = 0;

static void ResetState()
{
    g_api = {};
    g_has_api = false;
    g_owner_token = 0;
    g_pre_handle = 0;
}

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
    try {
        if (!out)
            return false;

        out->abi_version = OBELISK_PLUGIN_METADATA_ABI_VERSION;
        out->struct_size = sizeof(ObeliskPluginMetadata);
        out->plugin_id = "example";
        out->name = "Example Plugin";
        out->version = "0.1.0-dev";
        out->config_file = "config.json";
        out->default_config_json =
            "{\"enabled\":false,\"allow_all_instances\":false,\"instance_allowlist\":[]}\n";
        return true;
    } catch (...) {
        return false;
    }
}

extern "C" __attribute__((visibility("default")))
bool ObeliskPlugin_Init(ObeliskApi* api, const ObeliskPluginInitContext* context)
{
    try {
        if (!api || !context)
            return false;
        if (api->abi_version != OBELISK_API_ABI_VERSION ||
            api->struct_size < sizeof(ObeliskApi))
            return false;
        if (context->abi_version != OBELISK_PLUGIN_INIT_CONTEXT_ABI_VERSION ||
            context->struct_size < sizeof(ObeliskPluginInitContext))
            return false;

        g_api = *api;
        g_has_api = true;
        g_owner_token = context->plugin_owner_token;
        api->LogInfo("Plugin loaded");

        const int32_t validated_function_index = -1;
        if (validated_function_index >= 0 &&
            (api->capabilities & OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS) &&
            (api->capabilities & OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES) &&
            api->struct_size >= offsetof(ObeliskApi, UnregisterProcessEventCallbackWithOwnerToken) +
                sizeof(api->UnregisterProcessEventCallbackWithOwnerToken) &&
            g_owner_token != 0 &&
            api->RegisterPreProcessEventForNameIndexWithOwnerTokenHandle &&
            api->UnregisterProcessEventCallbackWithOwnerToken)
        {
            g_pre_handle = api->RegisterPreProcessEventForNameIndexWithOwnerTokenHandle(
                g_owner_token, validated_function_index, OnProcessEvent);
            if (g_pre_handle == 0)
                api->LogWarn("Filtered ProcessEvent callback registration was rejected");
        }

        return true;
    } catch (...) {
        ResetState();
        return false;
    }
}

extern "C" __attribute__((visibility("default")))
void ObeliskPlugin_Shutdown()
{
    try {
        if (g_has_api && g_pre_handle != 0 && g_api.UnregisterProcessEventCallbackWithOwnerToken)
            g_api.UnregisterProcessEventCallbackWithOwnerToken(g_owner_token, g_pre_handle);
    } catch (...) {
    }
    ResetState();
}
```

Prefer filtered callbacks. Global `ProcessEvent` callbacks are hot-path debug
tools unless explicitly measured and gated.

Callbacks registered after `ObeliskPlugin_Init`, from helper libraries, or from background
threads should use the owner-token registration fields appended to `ObeliskApi`. New
plugins should prefer the handle-returning owner-token functions when both
`OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS` and
`OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES` are advertised, store returned
handles only in process-local state, and unregister them with
`UnregisterProcessEventCallbackWithOwnerToken` during shutdown. Handles are not cluster
state: never write them into shared plugin config or assume they are valid in another ARK
server process. Legacy registration functions reject callbacks that cannot be attributed
to the initializing plugin or an already-loaded plugin shared object.
Apply the same rule to owner tokens, worker threads, sockets, caches, open file handles,
borrowed UE pointers, and other mutable runtime state: keep them process-local unless the
plugin documents and tests explicit cross-process ownership and locking.

`ObeliskApi*` and `ObeliskPluginInitContext*` are borrowed for `ObeliskPlugin_Init` only.
Copy the `ObeliskApi` table by value if shutdown, worker threads, or later callbacks need
runtime functions.

The promoted gameplay callback path is `GameplayPolicyEvent`. It is copied POD policy
data, not a UE object/resource handle. Plugins must check the capability, appended
function pointers, `struct_size`, and a non-zero `plugin_owner_token` before subscribing:

```cpp
static uint64_t g_gameplay_policy_handle = 0;

static void OnGameplayPolicyEvent(const ObeliskGameplayPolicyEvent* event, void* user_data)
{
    (void)user_data;
    if (!event ||
        event->abi_version != OBELISK_GAMEPLAY_POLICY_EVENT_ABI_VERSION ||
        event->struct_size < sizeof(ObeliskGameplayPolicyEvent))
        return;

    if ((event->field_mask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE) != 0)
    {
        const bool allowed =
            (event->bool_values & (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_RETURN_VALUE)) != 0;
        (void)allowed;
    }

    if ((event->flags & OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED) != 0)
    {
        if ((event->field_mask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER) != 0)
        {
            const bool requested_by_player =
                (event->bool_values &
                    (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_REQUESTED_BY_PLAYER)) != 0;
            (void)requested_by_player;
        }
        if ((event->field_mask & OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN) != 0)
        {
            const bool ignore_cooldown =
                (event->bool_values &
                    (1ull << OBELISK_GAMEPLAY_POLICY_FIELD_IGNORE_COOLDOWN)) != 0;
            (void)ignore_cooldown;
        }
    }
}

static bool HasGameplayPolicyEventApi(const ObeliskApi* api, uint64_t owner_token)
{
    return api &&
        owner_token != 0 &&
        (api->capabilities & OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS) != 0 &&
        api->struct_size >= offsetof(ObeliskApi, UnregisterGameplayPolicyEventWithOwnerToken) +
            sizeof(api->UnregisterGameplayPolicyEventWithOwnerToken) &&
        api->RegisterGameplayPolicyEventWithOwnerTokenHandle &&
        api->UnregisterGameplayPolicyEventWithOwnerToken;
}

// During ObeliskPlugin_Init, after copying api/context into plugin-owned state:
if (HasGameplayPolicyEventApi(&g_api, g_owner_token))
{
    const uint64_t event_mask = OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL;
    // Use OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY for inventory-backed only.
    g_gameplay_policy_handle = g_api.RegisterGameplayPolicyEventWithOwnerTokenHandle(
        g_owner_token,
        event_mask,
        OnGameplayPolicyEvent,
        nullptr);
    if (g_gameplay_policy_handle == 0)
        return false;
}

// During ObeliskPlugin_Shutdown, before callback state can disappear:
if (g_has_api && g_gameplay_policy_handle != 0 && g_api.UnregisterGameplayPolicyEventWithOwnerToken)
    g_api.UnregisterGameplayPolicyEventWithOwnerToken(g_owner_token, g_gameplay_policy_handle);
```

`resource_kind` is categorical only. It is useful for routing or sanitized metrics such as
"structure-backed policy event" or "inventory-item-backed policy event", but it is not a
lookup key, persistent resource id, player/tribe/inventory/item identity, coordinates, UE
pointer, or proof that two events refer to the same game object. Inventory-backed policy
events are delivered through the same generic `GameplayPolicyEvent` masks, kinds, fields,
and `INVENTORY_BACKED` flag; v0.1 does not ship a public Inventory SDK, Inventory callback
ABI, item handle, lookup API, inventory contents API, mutation API, or return-override
contract.

Use `OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL` to receive every promoted policy event,
`OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_STRUCTURES` for structure-backed policy only, or
`OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY` for inventory-backed policy only.
Inventory-backed events currently expose copied scalar booleans only when their field bits
are present: `REQUESTED_BY_PLAYER` for remote-add checks, `IGNORE_COOLDOWN` for use checks,
and `RETURN_VALUE` for the observed policy result. These fields are observations, not
identity, lookup, mutation, or override authority.

Plugins that need category metadata can call `DescribeResourceKind` after checking
`OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS`, that `struct_size` covers the appended
`DescribeResourceKind` slot, and that the function pointer is non-null. The returned
`ObeliskResourceKindDescriptor` is copied POD metadata only: stable category name,
supported gameplay policy masks, supported field masks, and flags that explicitly mark the
category as no-identity and no-lookup.

`CallProcessEvent` is a low-level trampoline escape hatch. The ABI slot exists for
compatibility, but plugins must treat it as unavailable unless `struct_size` covers the
field, `OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT` is advertised, and the function pointer
is non-null. If a pre-callback calls it, that callback should return `false`; if it returns
`true`, the runtime skips the automatic original call and warns to avoid double execution.
Stable plugin APIs should prefer higher-level Obelisk module surfaces as they are promoted.

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
OBELISK_ENABLE_INVENTORY_REFLECTION=1
OBELISK_ENABLE_STRUCTURE_REFLECTION=1
OBELISK_ENABLE_CHAT_REFLECTION=1
OBELISK_<MODULE>_REFLECTION_BINARY_SHA256=<supported ARK SHA256>
OBELISK_<MODULE>_REFLECTION_LOG_LIMIT=<bounded-count>
OBELISK_PE_TRACE_LIMIT=0
```

`OBELISK_INSTANCE_ID` must be a non-empty safe token using only letters, digits, `_`, or
`-`. Plugin loading fails closed when the id is missing or unsafe, because shared-cluster
plugin config uses this value for activation scope.

Experimental runtime controls that can affect server safety require both their environment
variable and the matching instance marker under
`OBELISK_ROOT/state/instances/<OBELISK_INSTANCE_ID>/`:

```text
OBELISK_DEBUG_ALLOW_PTRACE=1             + allow-ptrace
OBELISK_ENABLE_DEBUG_CONTROL=1           + enable-debug-control
OBELISK_ENABLE_REFLECTION_SCANNER=1      + enable-reflection-scanner
OBELISK_ENABLE_NATIVE_EXEC_PROBES=1      + enable-native-exec-probes
```

Experimental scanners, candidate module observers, text logging, broad tracing, and native
exec probes stay opt-in. Reflection captures belong on isolated/debug instances or an
operator-approved validation target only. Do not use these controls on normal player-facing
or performance-sensitive servers. Debug targets should be started only for scoped tests and
returned to stable posture afterward.

Candidate module observers require the environment gate, supported binary SHA, the
observer-specific instance marker, and `allow-experimental-observers` on the same
instance. Stable posture rejects that allow marker.

## Roadmap

Near-term engineering:

- Keep CI as a real quality gate: build, CTest, analyzer tests, SDK consumer
  fixture, and install dry-run.
- Strengthen sanitized reflection snapshots, manifest regeneration, and second-source
  comparison for candidate modules.
- Define copied-data ownership and callback lifetime before exposing additional
  plugin-facing gameplay events.
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
