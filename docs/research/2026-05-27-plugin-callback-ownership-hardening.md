# Plugin Callback Ownership Hardening

## Objective

Implement priority runtime hardening so plugin ProcessEvent callbacks are owned by the
plugin that registered them and are removed before plugin init failure cleanup, unload,
and `dlclose`.

## Environment

- Repo: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-27
- Scope: `core/EventManager.*`, `core/PluginManager.*`, `api/ObeliskApi.h`,
  `docs/research/*`, `docs/agent-handoff/CURRENT.md`

## Hypothesis

The existing C API registration functions can remain source-compatible if runtime-owned
wrappers assign callback ownership internally instead of adding owner parameters to the
plugin ABI.

## Method

- Changed `EventManager` callback storage from raw callback vectors to callback
  registrations with `{nameIndex, callback, owner}`.
- Added `EventManager::UnregisterCallbacksForOwner`.
- Added a dispatch mutex so unregister waits for in-flight callback dispatch before
  returning to `PluginManager` and `dlclose`.
- Changed `PluginManager` C API wrappers to derive owner from the current plugin init
  frame or `dladdr(callback).dli_fbase`.
- Removed callbacks for failed plugin init before `dlclose`.
- Removed callbacks for loaded plugins before unload `dlclose`.
- Added `abi_version`, `struct_size`, and `capabilities` to `ObeliskApi` at the end of
  the existing function table.

## Evidence

- Directed object validation passed:
  - `cmake --build build --target CMakeFiles/obelisk.dir/core/EventManager.cpp.o -- -j1`
  - `cmake --build build --target CMakeFiles/obelisk.dir/core/PluginManager.cpp.o -- -j1`
  - `cmake --build build --target ChatPlugin -j"$(nproc)"`
- `git diff --check -- api/ObeliskApi.h core/EventManager.h core/EventManager.cpp core/PluginManager.h core/PluginManager.cpp` passed.
- Full `cmake --build build -j"$(nproc)"` passed after the reflection/chat metadata audit
  fixed the unrelated `ue/ReflectionScanner.cpp` pointer formatting issues.

## Result

- Plugin callbacks registered during init are owned by the plugin module base.
- Plugin callbacks registered later through the existing API can still be owned when
  `dladdr` resolves the callback function to a loaded module.
- Failed init now unregisters callbacks before closing the plugin library.
- `UnloadAll` unregisters callbacks before `dlclose`.
- Existing function-table offsets are preserved for old plugins because ABI metadata was
  appended, not inserted before logging functions.

## Rejected paths

- Inserting `abi_version`, `struct_size`, and `capabilities` at the beginning of
  `ObeliskApi` was rejected for this pass because it would shift every existing function
  pointer offset and break plugins compiled against the current header.

## Risks

- Appended ABI metadata is a compatibility bridge, not a complete long-term ABI contract.
  A future ABI major version should introduce a front-loaded versioned header and runtime
  rejection of incompatible plugins.
- Callback owner inference depends on `dladdr`. If a plugin registers a callback pointer
  that does not resolve to its shared object, the runtime cannot safely associate that
  callback with the plugin.

## Next steps

- For a future ABI-major change, move ABI metadata to the front of a new function table
  and add explicit plugin-side validation before plugins use newer fields.

## Skill updates needed

- None. Existing runtime and C ABI skills already required callback ownership cleanup and
  ABI version planning.
