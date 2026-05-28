---
name: obelisk-c-abi-validation
description: "Validates Obelisk runtime/plugin API changes so shared libraries keep a stable C ABI, explicit ownership, and safe callback lifetimes."
---

# Obelisk C ABI Validation Skill

Use this skill whenever code crosses the runtime/plugin boundary: `api/ObeliskApi.h`,
`loader/PluginManager.*`, plugin entry points, callback registration, and any SDK surface
that a `.so` will consume.

## Current ABI State

- The runtime loads plugins with `dlopen` and calls exported C entry points.
- Plugins receive an `ObeliskApi` function table.
- Event callbacks may be global or filtered by `FName` index.
- The current API appends `abi_version`, `struct_size`, and capability flags after the
  original function table to preserve existing offsets. Treat this as an ABI v1 bridge, not
  the final ABI shape.
- Callback ownership and unregister-on-unload exist for plugin ProcessEvent callbacks.
  Preserve that behavior: raw callback pointers must not survive plugin init failure,
  plugin unload, or `dlclose`.
- Plugin callback registration wrappers reject callbacks whose owner cannot be resolved to
  the plugin currently initializing or an already-loaded Obelisk plugin shared object.
- Helper-module or background-thread callback registrations must use the append-only
  owner-token registration functions and the `plugin_owner_token` supplied in
  `ObeliskPluginInitContext`. The runtime accepts those owner-token registrations during
  `ObeliskPlugin_Init`, including from helper/background threads that do not inherit the
  loader thread-local current owner.
- Handle-returning owner-token ProcessEvent registrations are the preferred public path
  for long-lived callbacks. Public unregister must be owner-scoped with the same
  `plugin_owner_token`; never expose bare unregister-by-id across the plugin ABI.
- Plugins may optionally export `extern "C" void ObeliskPlugin_Shutdown()`. The runtime
  resolves it with `dlsym` outside the `ObeliskApi` table and calls it before callback
  owner cleanup and before `dlclose`.
- The runtime should resolve `ObeliskPlugin_GetInfo` and prepare/apply config gates before
  resolving mandatory `ObeliskPlugin_Init`. A disabled plugin may be discovered and get a
  default safe-disabled config without requiring its init symbol to be usable.
- Plugin metadata `default_config_json` must be an explicit cluster-safe envelope:
  `enabled=false`, an `instance_allowlist` array, and `allow_all_instances=false`.
  Existing operator configs may omit `allow_all_instances`; enabled configs still fail
  closed unless scoped to the current `OBELISK_INSTANCE_ID` or explicitly all-instance.
- `OBELISK_INSTANCE_ID` and `instance_allowlist` entries must be non-empty safe tokens
  containing only letters, digits, `_`, or `-`. Plugin loading must fail closed before
  discovery when the runtime instance id is missing or unsafe.
- `ObeliskPluginInitContext` string pointers are borrowed for `ObeliskPlugin_Init` only;
  plugin examples should copy `config_dir`, `config_path`, or `instance_id` before using
  them from shutdown, threads, or later callbacks.

## Required Boundary Rules

- Export/import plugin functions with `extern "C"`.
- Use only POD structs, primitive integer types, raw pointers, fixed-size buffers, and
  function pointers across the ABI.
- Do not pass `std::string`, `std::vector`, `std::function`, STL containers, exceptions,
  references, C++ classes, virtual interfaces, or RTTI-dependent types across the boundary.
- Use explicit sizes for buffers and structs. Prefer `uint32_t`, `uint64_t`, `size_t`, and
  `const char*` over compiler-dependent aliases.
- Catch all plugin exceptions inside the plugin boundary. The runtime must never receive a
  C++ exception from plugin code.

## API Versioning Pattern

When designing a future ABI-breaking `ObeliskApi` v2, prefer a front-loaded header like
this:

```cpp
struct ObeliskApi {
    uint32_t abi_version;
    uint32_t struct_size;
    uint64_t capabilities;

    void (*LogInfo)(const char* message);
    // New fields must be appended, not inserted before existing fields.
};
```

Validation rules:

- Runtime fills `abi_version` and `struct_size`. In ABI v1 these fields are appended for
  compatibility; in a future ABI v2 they should move to the front.
- Plugin validates both before using later fields when compiled against an ABI that exposes
  them.
- New API functions are appended to avoid shifting older field offsets.
- Removing or retyping fields is an ABI break and requires a major version bump.

## Callback Lifetime Rules

- Every registration function must have a matching unregister path or be owned by a plugin
  handle that can be removed as a group.
- If `Plugin_Load` or `Plugin_Init` fails, all callbacks registered by that plugin must be
  removed before the library is closed.
- Before `dlclose`, runtime must call optional plugin shutdown, remove plugin-owned
  callbacks, and stop dispatching into that address range.
- Shutdown exports must be idempotent, stop external ingress before releasing state, and
  catch all exceptions before returning across the C ABI boundary.
- Prefer filtered ProcessEvent callbacks over global callbacks. Global callbacks are hot
  path and should be rare, measured, and disabled by default for experimental plugins.
- Callback implementations must be non-blocking and must not call back into unsafe UE4
  functions unless reentrancy is explicitly handled.
- Future gameplay events such as chat must copy data into Obelisk-owned memory before
  calling plugins. Do not expose borrowed UE4 params, `FString`, `UObject`, `UFunction`, or
  raw `ProcessEvent` buffers as a stable SDK contract.
- Future chat events should pass through the internal `core/ChatEventDispatcher` ownership
  layer before any SDK exposure. Do not dispatch plugin-facing chat callbacks directly from
  the `ProcessEvent` hook.
- `PluginManager` must unregister both `EventManager` and `ChatEventDispatcher` callbacks
  for a plugin owner on init failure and before `dlclose` during unload.
- Current public callback registration functions must not create ownerless registrations.
  If owner resolution fails outside `ObeliskPlugin_Init` and the plugin did not use a valid
  owner token, reject the registration with a warning instead of relying on `dladdr`
  fallback blindly.
- Owner-token registration must stay valid during the plugin's init window for helper
  threads, then continue to work after successful load through the loaded-owner set. On
  init failure, plugin shutdown and owner cleanup must still remove callbacks registered
  through that temporary initializing-owner window before `dlclose`.
- Chat callback unregister must be idempotent and safe when called by the callback itself;
  cross-thread owner cleanup must still wait until in-flight dispatch finishes.
- Keep tests for both self-unregister and cross-thread owner cleanup waiting before
  exposing any chat callback registration through the public SDK.
- Prefer opaque `uint64_t` registration ids plus explicit unregister for new event APIs.
  Keep owner-token cleanup on init failure/unload as the backstop, and include `user_data`
  in callback subscriptions instead of asking plugins to capture global state.
- Registration ids returned across the ABI are process-local handles, not shared cluster
  state. They must not be written to shared config or reused across ARK server processes.
- Assume most real plugins may load in more than one ARK server process that shares the
  same plugin binary and config directory. Public API guidance must keep runtime handles,
  callbacks, threads, sockets, caches, and mutable state process-local unless a plugin
  explicitly documents cross-process ownership and locking.
- Owner-token API additions must stay append-only: `plugin_owner_token` remains at the end
  of `ObeliskPluginInitContext`, and owner-token registration function pointers remain
  after existing `ObeliskApi` fields.

## Review Checklist

- [ ] Boundary structs are POD and include explicit version/size where public.
- [ ] All exported plugin entry points use `extern "C"`.
- [ ] No STL, exceptions, references, virtual classes, or ownership ambiguity cross the ABI.
- [ ] Plugin callback registrations can be unregistered on failure and unload.
- [ ] ProcessEvent callbacks are filtered by `FName` index unless there is a measured reason.
- [ ] ABI additions are appended and guarded by `struct_size` checks.
- [ ] The runtime can reject incompatible plugin ABI versions with a clear log line.
