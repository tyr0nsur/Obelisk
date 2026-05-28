# Architecture

Obelisk is split into a small Linux runtime core, a C plugin API, and optional
plugins. The current ARK server integration is a validation adapter for checking
that runtime against a real stripped UE4 dedicated server process.

## Runtime Bootstrap

`loader/Bootstrap.cpp` runs from a shared library constructor after
`libobelisk.so` is injected with `LD_PRELOAD`.

The current bootstrap:

1. Verifies the target process for the active harness.
2. Initializes logging.
3. Installs enabled hooks.
4. Optionally runs experimental scanners.
5. Loads plugins unless disabled.

## Hooking

`hooks/ProcessEventHook.cpp` locates `UObject::ProcessEvent` using a byte
signature derived from UE4 vtable analysis.

The current hook uses an absolute x64 jump:

```text
mov rax, imm64
jmp rax
```

This avoids the x86_64 `jmp rel32` distance limitation when the game binary is
mapped low and `libobelisk.so` is mapped high.

## Event Dispatch

`core/EventManager` supports two callback styles:

- Global pre/post `ProcessEvent` callbacks.
- Filtered pre/post callbacks by `FName` index.

Filtered callbacks are strongly preferred because `ProcessEvent` is extremely
hot. A global callback can receive millions of calls during normal startup and
player connection flows.

## Plugin ABI

Plugins interact with Obelisk through the public SDK header
`include/obelisk/ObeliskApi.h`. The older `api/ObeliskApi.h` path remains a
transition wrapper.

The ABI is C-compatible by design:

- No STL types cross the boundary.
- No exceptions cross the boundary.
- Plugin entrypoints use `extern "C"`.

Plugins export:

```cpp
extern "C" __attribute__((visibility("default")))
bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out);

extern "C" __attribute__((visibility("default")))
bool ObeliskPlugin_Init(ObeliskApi* api, const ObeliskPluginInitContext* context);
```

Plugin structure, configuration, lifecycle, HTTP safety, and promotion rules are
documented in [PLUGIN_ARCHITECTURE.md](PLUGIN_ARCHITECTURE.md). Larger plugins
must follow that document before they are added to the top-level build.

## Central Install Root

At runtime, paths come from:

```text
OBELISK_ROOT
OBELISK_PLUGIN_DIR
OBELISK_CONFIG_DIR
OBELISK_LOG_DIR
OBELISK_INSTANCE_ID
```

This keeps Obelisk artifacts outside the target binary directory and allows multiple ARK
server processes to share one runtime root. `OBELISK_INSTANCE_ID` separates logs,
operational markers, plugin activation gates, and process-local runtime state by instance.
Plugin discovery is fail-closed: plugin loading requires an explicit absolute
`OBELISK_PLUGIN_DIR` or `OBELISK_ROOT`-derived `plugins` path, and the runtime does not scan
a working-directory-relative `plugins/` fallback.
Plugin binaries and config may be shared across a cluster; mutable plugin state should be
instance-scoped unless the plugin documents and implements safe cross-process ownership.

## ARK Validation Adapter

The current harness injects Obelisk into `ShooterGameServer` with `LD_PRELOAD`.
LinuxGSM wrapper templates under `packaging/linuxgsm/` are operational helpers
for that harness, not the core product surface.

ARK-specific paths, instance names, and observed `FName` indices are validation
inputs only. Stable plugin contracts should be expressed through public SDK
headers and documented runtime behavior.

Current runtime debug work must keep `arkserver` / Ragnarok untouched while users are
active. Server-backed validation targets `arkserver2` / TheIsland only after explicit
operator approval; it starts from powered off, uses gates plus rollback checks, and is shut
down when the window ends.

## SDK Direction

The SDK currently exposes the C ABI header and CMake `obelisk_sdk` interface
target. Higher-level runtime-backed APIs for common modding tasks remain planned
until reflection metadata is reliable enough to support them.

## Research Strategy

Long term, Obelisk should avoid raw memory scanning in plugins.

Preferred direction:

1. Resolve FName indices to strings.
2. Resolve GObjects and UFunction objects.
3. Register plugin callbacks by function name.
4. Decode parameters using reflected property metadata.
5. Expose higher-level APIs for chat, players, inventory, tribes, dinos, and timers.

## Experimental Components

`ue/ReflectionScanner.*` currently exists as a research tool. It should remain
disabled by default on validation adapter servers.

The first official plugin target is `plugins/oBaseEvents`, which demonstrates the C ABI,
safe default config creation, filtered event registration, and plugin shutdown. Larger
modding features should be built as separate plugins after the reflection layer
is more complete.
