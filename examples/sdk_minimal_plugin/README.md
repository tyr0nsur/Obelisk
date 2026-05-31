# Minimal Installed-SDK Plugin

This is the smallest creator-facing example for building an Obelisk plugin outside the
Obelisk source tree. It uses only the installed CMake package and public C ABI:

Support tier: release-supported seed.

- `find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)`
- `Obelisk::obelisk_sdk`
- `ObeliskPlugin_GetInfo`
- `ObeliskPlugin_Init`
- optional `ObeliskPlugin_Shutdown`
- logging through the copied `ObeliskApi` table

It does not use `ProcessEvent`, gameplay events, new gameplay APIs, chat events, timers,
UE pointers, identity, lookup, mutation, return overrides, chat replies/send-chat, ArkApi
compatibility, Windows/MSVC portability, or private Obelisk headers.

In a real Obelisk load, the runtime evaluates the plugin activation envelope before
calling `ObeliskPlugin_Init`: `enabled=false`, a missing or non-matching
`instance_allowlist`, or an unsafe allowlist prevents the plugin from initializing. This
minimal example does not parse config itself and must not be copied as the activation
model for feature plugins. Once a plugin uses an optional surface such as events or
timers, follow the reference plugins by checking capabilities, enforcing `struct_size`
gates before reading appended API slots, validating `plugin_owner_token`, keeping
returned handles, and unregistering owned runtime state during shutdown or init-failure
cleanup.

The example intentionally uses the installed SDK package and the current numeric
compatibility floor:

```cmake
find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)
target_link_libraries(obelisk_sdk_minimal_plugin PRIVATE Obelisk::obelisk_sdk)
```

That package version is a compatibility floor for the current pre-release SDK line, not a
complete SDK claim and not a claim that a stable `v0.1.0` release tag exists.
This example is a foundation/contributor-readiness sample, not ArkApi portability
guidance and not Obelisk SDK v1 evidence.

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
