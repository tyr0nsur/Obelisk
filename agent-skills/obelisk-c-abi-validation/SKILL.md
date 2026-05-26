---
name: obelisk-c-abi-validation
description: Validates Obelisk runtime/plugin API changes so shared libraries keep a stable C ABI, explicit ownership, and safe callback lifetimes.
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
- Plugins may optionally export `extern "C" void ObeliskPlugin_Shutdown()`. The runtime
  resolves it with `dlsym` outside the `ObeliskApi` table and calls it before callback
  owner cleanup and before `dlclose`.

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

## Review Checklist

- [ ] Boundary structs are POD and include explicit version/size where public.
- [ ] All exported plugin entry points use `extern "C"`.
- [ ] No STL, exceptions, references, virtual classes, or ownership ambiguity cross the ABI.
- [ ] Plugin callback registrations can be unregistered on failure and unload.
- [ ] ProcessEvent callbacks are filtered by `FName` index unless there is a measured reason.
- [ ] ABI additions are appended and guarded by `struct_size` checks.
- [ ] The runtime can reject incompatible plugin ABI versions with a clear log line.
