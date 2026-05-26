# Architecture

Obelisk is split into a small runtime core and optional plugins.

## Runtime Bootstrap

`loader/Bootstrap.cpp` runs from a shared library constructor after
`libobelisk.so` is injected with `LD_PRELOAD`.

The bootstrap:

1. Verifies the process is `ShooterGameServer`.
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

Plugins interact with Obelisk through `api/ObeliskApi.h`.

The ABI is C-compatible by design:

- No STL types cross the boundary.
- No exceptions cross the boundary.
- Plugin entrypoints use `extern "C"`.

Plugins export:

```cpp
extern "C" __attribute__((visibility("default")))
bool ObeliskPlugin_Init(ObeliskApi* api);
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
```

This keeps Obelisk artifacts outside the ARK binary directory and allows
multiple LinuxGSM instances to share one runtime root.

## Reflection Strategy

Long term, Obelisk should avoid raw memory scanning in plugins.

Preferred direction:

1. Resolve FName indices to strings.
2. Resolve GObjects and UFunction objects.
3. Register plugin callbacks by function name.
4. Decode parameters using reflected property metadata.
5. Expose higher-level APIs for chat, players, inventory, tribes, dinos, and timers.

## Experimental Components

`ue/ReflectionScanner.*` currently exists as a research tool. It should remain
disabled by default on live servers.

The chat plugin is a testbed for command interception, not yet a stable API.

`plugins/monitor` is also experimental. It currently combines HTTP service,
log tailing, whitelist enforcement, raw parameter discovery, and a global
`ProcessEvent` callback without a stable shutdown contract.
