# Obelisk

Obelisk is a Linux x86-64 runtime and C SDK for writing native server plugins for **ARK: Survival Evolved**. It provides versioned plugin entry points, command registration and replies, and cooperative plugin lifecycle controls. The native adapter targets specific ARK dedicated-server builds.

This development snapshot adds the `oMonitor` process monitor and a C11 command starter. `oMonitor` publishes process metrics and observed session data in an owner-only local snapshot. Live compatibility still depends on the server executable and should be verified on a test instance.

## Build and test

Install a C++20 compiler, Git, CMake 3.22+, OpenSSL and SQLite development headers. CMake fetches pinned copies of fmt, spdlog and subhook on first configure.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

Stage the runtime and SDK in a test directory with `scripts/install_obelisk.sh --build-dir build --dry-run <absolute-path>`. Review the output and remove `--dry-run` to stage the files. Install the game server separately. Stage the monitor with `scripts/install_obelisk_plugin.sh build/plugins/oMonitor/oMonitor.so <absolute-path>` using the same runtime root. Before enabling it on a test instance, make its configuration directory owner-only (`0700`) and owned by the game process user. See [plugin activation](docs/PLUGIN_LIFECYCLE_OPERATIONS.md).

Start a plugin from the [SDK guide](docs/SDK_QUICKSTART.md) or the [C11 command example](examples/sdk_command_plugin/README.md). The [plugin architecture](docs/PLUGIN_ARCHITECTURE.md) describes the ABI and lifecycle.

## Collaborate

See [CONTRIBUTING.md](CONTRIBUTING.md) for pull requests and checks, and [SECURITY.md](SECURITY.md) for private vulnerability reports. The runtime and SDK use the [MIT license](LICENSE).
