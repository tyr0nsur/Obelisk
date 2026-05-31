# Timer SDK Plugin

This creator-facing example builds outside the Obelisk source tree and uses only the
installed SDK package:

Support tier: release-supported seed.

- `find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK)`
- `Obelisk::obelisk_sdk`
- `OBELISK_API_CAPABILITY_TIMERS`
- `RegisterTimerWithOwnerTokenHandle`
- `UnregisterTimerWithOwnerToken`

It demonstrates one release-supported seed surface: process-local owner-token timers.
Timer IDs are runtime handles only. They are not stable across process restarts, ARK server
instances, maps, plugin reloads, or cluster nodes, and must never be persisted in shared
configuration or storage.

`ObeliskPlugin_Init` receives borrowed `api` and `context` pointers. This example copies
the advertised `ObeliskApi` prefix by value before using it from shutdown, keeps only the
process-local `plugin_owner_token`, and does not store `config_dir`, `config_path`, or
`instance_id` pointers after init returns.

The example does not use private headers, raw UE pointers, gameplay module APIs, identity,
lookup, mutation, return overrides, chat replies/send-chat, ArkApi compatibility, or
implementation patterns from other frameworks.

The `find_package` version is a compatibility floor for the current pre-release SDK line,
not a complete SDK claim and not a claim that a stable `v0.1.0` release tag exists.

## Build

Install Obelisk into a test root first, then point CMake at that install:

```bash
cmake -S examples/sdk_timer_plugin -B /tmp/obelisk-sdk-timer-build \
  -DCMAKE_PREFIX_PATH=/path/to/obelisk-install-root
cmake --build /tmp/obelisk-sdk-timer-build -j"$(nproc)"
```

The output is `obelisk_sdk_timer_plugin.so`. Publish plugins with
`scripts/install_obelisk_plugin.sh`; do not copy a partially built `.so` into a shared
runtime `plugins/` directory.
