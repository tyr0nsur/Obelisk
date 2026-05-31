# Minimal Installed-SDK Plugin

This is the smallest creator-facing example for building an Obelisk plugin outside the
Obelisk source tree. It uses only the installed CMake package and public C ABI:

- `find_package(Obelisk CONFIG REQUIRED)`
- `Obelisk::obelisk_sdk`
- `ObeliskPlugin_GetInfo`
- `ObeliskPlugin_Init`
- optional `ObeliskPlugin_Shutdown`
- logging through the copied `ObeliskApi` table

It does not use `ProcessEvent`, gameplay events, chat events, timers, UE pointers,
identity, lookup, mutation, return overrides, ArkApi compatibility, or private Obelisk
headers.

The example intentionally uses the installed SDK package and the current numeric
compatibility floor:

```cmake
find_package(Obelisk 0.1.0 CONFIG REQUIRED)
target_link_libraries(obelisk_sdk_minimal_plugin PRIVATE Obelisk::obelisk_sdk)
```

That package version is a compatibility floor for the current pre-release SDK line, not a
claim that a stable `v0.1.0` release tag exists.

## Build

Install Obelisk into a test root first, then point CMake at that install:

```bash
cmake -S examples/sdk_minimal_plugin -B /tmp/obelisk-sdk-minimal-build \
  -DCMAKE_PREFIX_PATH=/path/to/obelisk-install-root
cmake --build /tmp/obelisk-sdk-minimal-build -j"$(nproc)"
```

The output is `obelisk_sdk_minimal_plugin.so`. Publish plugins with
`scripts/install_obelisk_plugin.sh`; do not copy a partially built `.so` into a shared
runtime `plugins/` directory.
