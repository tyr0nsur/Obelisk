# Examples

This directory contains creator-facing examples that build against the installed Obelisk
SDK package. These examples are separate from `plugins/`, which contains first-party
in-tree reference plugins used by Obelisk's own build and tests.

- `sdk_minimal_plugin/`: smallest external C plugin using `find_package(Obelisk 0.1.0
  CONFIG REQUIRED COMPONENTS SDK)` and `Obelisk::obelisk_sdk`.

Examples must stay inside public `include/obelisk/ObeliskApi.h` contracts. Do not use
private headers, raw UE pointers, `ProcessEvent` internals, identity, lookup, mutation,
return overrides, new gameplay APIs, chat replies/send-chat, or ArkApi implementation
patterns in creator-facing examples.

## Installed-SDK Author Validation

Use this pass before publishing a copied example or production seed. It validates package
shape and ABI hygiene only; it does not promote gameplay/module readiness or prove a
complete v1 SDK claim.

From the external plugin source root:

```bash
cmake -S . -B build -DCMAKE_PREFIX_PATH=/path/to/obelisk-install-root
cmake --build build -j"$(nproc)"
```

The plugin CMake must request only the installed SDK package and target:

```bash
rg -n 'find_package\(Obelisk 0\.1\.0 CONFIG REQUIRED COMPONENTS SDK\)|Obelisk::obelisk_sdk' CMakeLists.txt
```

The public-source check should return no matches for private or unpromoted patterns:

```bash
rg -n --glob '!README.md' --glob '!build/**' \
  '#include .*(core/|plugins/|private|ArkApi|AseApi)|ProcessEvent|UObject|UFunction|FString|GObjects|GetNativePointerField|NativeCall|ResourceHandle' .
```

For a minimal lifecycle/config/logging seed, the dynamic exports should be limited to the
Obelisk plugin entry points:

```bash
nm -D --defined-only build/<plugin-name>.so
```

Before packaging, confirm the plugin:

- exports `ObeliskPlugin_GetInfo` and `ObeliskPlugin_Init` with `extern "C"` or C
  linkage;
- exports idempotent `ObeliskPlugin_Shutdown` if it keeps copied API state, callback
  handles, timer handles, catalog state, threads, files, sockets, or other process-local
  state;
- copies the `ObeliskApi` table by value before using it after init, and never stores
  borrowed `ObeliskPluginInitContext` pointers;
- checks `abi_version`, `struct_size`, capability bits, non-null function pointers, and a
  non-zero `plugin_owner_token` before using optional callbacks, descriptors, or timers;
- ships safe-disabled default config with `enabled=false`, `allow_all_instances=false`,
  and an empty `instance_allowlist`;
- documents its support tier as production seed, experimental pattern, or blocked backlog
  prototype.
