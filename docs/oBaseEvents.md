# oBaseEvents

`oBaseEvents` is the first official Obelisk plugin example. It is intentionally small and
safe by default.

It demonstrates:

- C ABI validation with `abi_version` and `struct_size`.
- Runtime-owned first-run config creation under the central Obelisk config directory.
- `ObeliskPlugin_GetInfo` metadata and `ObeliskPluginInitContext` config paths.
- A filtered `ProcessEvent` callback.
- Handle-returning callback registration plus explicit unregister during shutdown when the
  runtime advertises both `OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS` and
  `OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES`.
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

Publish the plugin into the active plugin directory only when you want it to be discovered
on the next server restart. Use the staged installer so the shared `plugins/` directory
never exposes a partially copied `.so`:

```bash
scripts/install_obelisk_plugin.sh build/plugins/oBaseEvents/oBaseEvents.so /servidor/ark/obelisk
```

If the plugin should not load, do not place it in `/servidor/ark/obelisk/plugins/`.
On a clustered install, that directory is shared discovery scope: every instance that
restarts can discover the `.so`, read metadata, and prepare config. Use
`instance_allowlist` to restrict which ARK server instances may initialize the plugin after
restart. An enabled config with an empty allowlist stays skipped unless
`allow_all_instances` is set to `true` explicitly.

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
    "allow_all_instances": false,
    "instance_allowlist": [],
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
