# Build your first Obelisk plugin

Build Obelisk from the [repository root](../README.md#build-and-test), then install the experimental C SDK into a local prefix.

```sh
cmake --install build --prefix "$PWD/build/sdk" --component SDK
cmake -S examples/sdk_command_plugin -B build/command-starter -DCMAKE_PREFIX_PATH="$PWD/build/sdk"
cmake --build build/command-starter
ctest --test-dir build -R SdkInstalledCommandExample --output-on-failure
```

The C11 starter uses the installed headers and the `Obelisk::obelisk_sdk` CMake target. The build produces `build/command-starter/obelisk_sdk_command_plugin.so`.

To try the plugin on a compatible test server, stage the library with `scripts/install_obelisk_plugin.sh` and enable it for a single instance in its generated config. See the [command starter guide](../examples/sdk_command_plugin/README.md) for activation and expected behavior.

Check the ABI version, advertised table size and capabilities before registering callbacks. Borrowed strings stay valid during their callback. Command replies use the current invocation token before returning. Clean up partial registrations and make shutdown idempotent.
