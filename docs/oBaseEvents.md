# oBaseEvents

`oBaseEvents` is the first official Obelisk plugin example. It is intentionally small and
safe by default.

It demonstrates:

- C ABI validation with `abi_version` and `struct_size`.
- Runtime-owned first-run config creation under the central Obelisk config directory.
- `ObeliskPlugin_GetInfo` metadata and `ObeliskPluginInitContext` config paths.
- A filtered `ProcessEvent` callback.
- Handle-returning callback registration plus explicit unregister during shutdown when the
  runtime advertises `OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES`.
- Optional `ObeliskPlugin_Shutdown()`.

## Build

```bash
cmake -S . -B build
cmake --build build --target oBaseEvents -j"$(nproc)"
```

Output:

```text
build/plugins/oBaseEvents/oBaseEvents.so
```

## Install

Copy the plugin into the active plugin directory only when you want it to load on the next
server restart:

```bash
cp -a build/plugins/oBaseEvents/oBaseEvents.so /servidor/ark/obelisk/plugins/
```

If the plugin should not load, do not place it in `/servidor/ark/obelisk/plugins/`.
On a clustered install, that directory is shared discovery scope. Use
`instance_allowlist` to restrict which ARK server instances may initialize the plugin after
restart.

## Config

Default path:

```text
${OBELISK_CONFIG_DIR}/oBaseEvents/config.json
```

Default generated config:

```json
{
    "enabled": false,
    "log_level": "info",
    "instance_allowlist": [],
    "map_allowlist": [],
    "process_event": {
        "enabled": false,
        "filtered_function_index": -1,
        "log_limit": 5
    }
}
```

The callback stays disabled unless both `enabled` and `process_event.enabled` are `true`
and `process_event.filtered_function_index` is a validated non-negative `FName` index.
When enabled on more than one server instance, each ARK process receives its own callback
registration handle and unregisters that process-local handle during plugin shutdown.

Do not treat observed ARK indices as stable API contracts. They must come from a validated
reflection capture or future reflected function lookup.
