# oBaseEvents

`oBaseEvents` is the first official Obelisk plugin example. It is intentionally small and
safe by default.

It demonstrates plugin lifecycle, config, and filtered `ProcessEvent` callback mechanics.
The promoted v0.1 gameplay callback path is `GameplayPolicyEvent`; use
`DescribeGameplayPolicyEventKind` and `DescribeResourceKind` for metadata-only discovery
when building gameplay policy plugins.

It demonstrates:

- C ABI validation with `abi_version` and `struct_size`.
- Runtime-owned first-run config creation under the central Obelisk config directory.
- `ObeliskPlugin_GetInfo` metadata and `ObeliskPluginInitContext` config paths.
- A filtered `ProcessEvent` callback.
- Handle-returning callback registration plus explicit unregister during shutdown when the
  runtime advertises both `OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS` and
  `OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES`.
- Optional `ObeliskPlugin_Shutdown()`.

`oBaseEvents` does not start background workers, open sockets, run HTTP listeners/clients,
or keep long-lived file readers. That is intentional for the first stable example. Plugins
that own background work stay experimental until they prove idempotent shutdown, stop
external ingress, unregister owner-token callback handles, drain queues, join threads,
close sockets/files, and avoid detached workers or persisted runtime handles.

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
scripts/install_obelisk_plugin.sh build/plugins/oBaseEvents/oBaseEvents.so <obelisk-root>
```

If the plugin should not load, do not place it in `<obelisk-root>/plugins/`.
On a clustered install, the plugin directory is shared discovery scope: every instance that
restarts can discover the `.so`, read metadata, and prepare config. Use
`instance_allowlist` to restrict which ARK server instances may initialize the plugin after
restart. Allowlist entries must be safe `OBELISK_INSTANCE_ID` values using only letters,
digits, `_`, or `-`. An enabled config with an empty allowlist stays skipped unless
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

For offline operator-side resolution, validate a binary-scoped manifest before copying an
index into config:

```bash
python3 scripts/validate_fname_index_manifest.py \
  --manifest /path/to/accepted/fname-index-manifest.json \
  --ark-binary /path/to/offline/ShooterGameServer \
  --resolve-name ServerChat
```

This prints both `ServerChat#0=<index>` and
`generated_for_ark_binary_sha256=<sha256>` only when the manifest schema and target binary
hash match. If only a previously recorded lowercase hash is available, use
`--ark-binary-sha256`, but prefer `--ark-binary` during config generation so the tool
computes the hash from the actual offline binary. The tool rejects `--ark-binary` paths
under protected live-server roots, including symlinked live-server paths; copy the binary
to an offline artifact location first. Candidate-only manifests are rejected for name
resolution by default; add `--allow-candidate` only for explicit internal/debug testing,
not stable operator config generation.

Generated config notes should record the binary hash used to resolve the index, for
example `generated_for_ark_binary_sha256`, so clustered servers fail review when they run
different ARK binaries during updates.
