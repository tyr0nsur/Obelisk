# Architecture

Obelisk is split into a small Linux runtime core, a C plugin ABI, a core SDK header,
and optional plugins. The current ARK server integration is a validation adapter for
checking that core against a real stripped UE4 dedicated server process.

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

`core/EventManager` retains debug-gated raw `ProcessEvent` callback infrastructure:

- Global pre/post `ProcessEvent` callbacks.
- Filtered pre/post callbacks by `FName` index.

Stable RC plugin paths are copied Obelisk-level events such as
`GameplayPolicyEvent` and `ChatMessageEvent`. Filtered raw callbacks are preferred over
global raw callbacks only inside approved debug/tooling runs because `ProcessEvent` is
extremely hot. A global callback can receive millions of calls during normal startup and
player connection flows.

## Core Plugin ABI

Plugins interact with Obelisk through the public core SDK header
`include/obelisk/ObeliskApi.h`. The older `api/ObeliskApi.h` path remains a
transition wrapper. In this document, "public SDK" means this core C ABI and any
surface explicitly promoted by release gates; it does not mean public `sdk.inventory`,
`sdk.chat`, `sdk.structures`, or other module namespaces.

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
inputs only. Stable plugin contracts should be expressed through the core SDK header,
documented runtime behavior, and named promotion gates.

Current runtime debug work must keep shared/player-facing instances untouched unless the
operator approves a specific maintenance window. Server-backed validation should use an
operator-approved debug/development target with explicit gates, rollback checks, and
shutdown expectations.

## SDK Completion Direction

The SDK currently exposes the C ABI header and CMake `obelisk_sdk` interface target.
Those foundation pieces are necessary, but they are not the stable production target by
themselves. The `v1.0` planning direction covers the ARK plugin-author SDK surface:
bootstrap, hook safety, plugin lifecycle, callback ownership, install layout, ABI
compatibility, and promoted module surfaces for common modding tasks. Each module surface
requires explicit evidence, copied-data ABI design, lifecycle tests, documentation, and
operator-safe runtime validation before it can be described as public.

Process-local core timer callbacks belong to this layer only as owner-token runtime
utilities with explicit unregister and plugin lifecycle cleanup. They do not define
gameplay/module timer APIs, shared scheduler state, UE identity, persistent handles, or
cluster coordination.

## Research Strategy

Long term, Obelisk should avoid raw memory scanning in plugins.

Preferred copied-SDK direction:

1. Validate reflection primitives with second-source evidence.
2. Keep runtime observation exact, bounded, gated, and non-mutating.
3. Promote only copied-data ABI surfaces with owner-token lifecycle coverage.
4. Document every public surface in the release and SDK guardrails.
5. Treat chat, players, inventory, tribes, dinos, gameplay/module timer abstractions, and
   other gameplay areas as module-after-gates work, not as the core architecture.

Compatibility references such as ArkServerApi/AseApi are names and demand signals only.
They are not architecture or ergonomics sources, behavior maps, porting
targets, copying sources, or implementation guides for offsets, layouts, ABI assumptions,
wrappers, raw UE pointer APIs, command parsers, return semantics, or implementations.

## Experimental Components

`ue/ReflectionScanner.*` currently exists as a research tool. It should remain
disabled by default on validation adapter servers.

The first official plugin target is `plugins/oBaseEvents`, which demonstrates the C ABI,
safe default config creation, optional debug-gated filtered event registration, and plugin
shutdown. Larger modding features should be built as separate plugins after the reflection
layer is more complete.
