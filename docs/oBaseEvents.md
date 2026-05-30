# oBaseEvents

`oBaseEvents` is the first official Obelisk plugin example. It is intentionally small and
safe by default.

It demonstrates plugin lifecycle, config, and filtered `ProcessEvent` callback mechanics.
The promoted v0.1 gameplay callback path is `GameplayPolicyEvent`; use
`DescribeGameplayPolicyEventKind` and `DescribeResourceKind` for metadata-only descriptions
of promoted event kinds and resource categories when building gameplay policy plugins.

It demonstrates:

- C ABI validation with `abi_version` and `struct_size`.
- Runtime-owned first-run config creation under the central Obelisk config directory.
- `ObeliskPlugin_GetInfo` metadata and `ObeliskPluginInitContext` config paths.
- A filtered raw `ProcessEvent` callback when the runtime explicitly advertises the
  filtered debug capability.
- An optional plugin-local chat command helper layered on copied `ChatMessageEvent`
  bytes, disabled by default.
- Handle-returning callback registration plus explicit unregister during shutdown when the
  runtime advertises `OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS`,
  `OBELISK_API_CAPABILITY_FILTERED_PROCESS_EVENT_CALLBACKS`, and
  `OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES` for the raw ProcessEvent
  example, or `OBELISK_API_CAPABILITY_CHAT_EVENTS` for the chat helper.
- Optional `ObeliskPlugin_Shutdown()`.

`oBaseEvents` does not start background workers, open sockets, run HTTP listeners/clients,
or keep long-lived file readers. That is intentional for the first stable example. Plugins
that own background work stay experimental until they prove idempotent shutdown, stop
external ingress, unregister owner-token callback handles, drain queues, join threads,
close sockets/files, and avoid detached workers or persisted runtime handles.

## Plugin-Local Chat Command Parsing

Command-like chat helpers should be implemented inside a plugin on top of the copied
`ChatMessageEvent` notification. Do not add command registration, routing, reply, send,
permission, identity, or mutation functions to `ObeliskApi` for this pattern.

A plugin-local helper should:

- subscribe with `RegisterChatMessageEventWithOwnerTokenHandle` only after checking
  `OBELISK_API_CAPABILITY_CHAT_EVENTS`, `struct_size`, a non-zero `plugin_owner_token`,
  and non-null chat register/unregister function pointers;
- reject malformed events unless `event`, `event->struct_size >= sizeof(ObeliskChatMessageEvent)`,
  `event->abi_version == OBELISK_CHAT_MESSAGE_EVENT_ABI_VERSION`,
  `event->send_mode <= OBELISK_CHAT_SEND_MODE_MAX`,
  `(event->flags & OBELISK_CHAT_MESSAGE_EVENT_FLAG_COPIED_PAYLOAD) != 0`, and
  `event->message.data != nullptr || event->message.size == 0` are all valid;
- treat empty messages and messages without a configured command prefix as local no-match
  cases, not authorization failures;
- treat `event->message` as callback-scope borrowed bytes and copy the command text into
  plugin-owned memory before any deferred work;
- parse only plugin-owned prefixes and command tables from that copied text;
- pass `principal=unknown` to every local handler;
- log command names, send mode, sequence, and rejection reasons only, not raw chat text by
  default.

Handlers must stay plugin-local and fail closed for anything that needs a real sender,
player identity, permissions, targeted replies, chat send, moderation, blocking, mutation,
return override, UE lookup, `FString`, `UObject`, raw params, or FName/GObjects indices.
`sequence` is process-local diagnostic ordering only and must not be persisted or used as
identity across server processes.

`oBaseEvents` includes a deliberately inert helper example behind
`chat_command_helper.enabled`. When enabled, it subscribes to `ChatMessageEvent`, copies at
most 1024 callback-scope message bytes into plugin-owned memory, matches one configured
printable prefix, and recognizes only the local `help` command. The handler does not reply,
send chat, mutate game state, block chat, resolve identity, or authorize a sender; it only
logs sanitized command metadata with `principal=unknown`.

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
    },
    "chat_command_helper": {
        "enabled": false,
        "prefix": "!",
        "log_limit": 5
    }
}
```

The callback stays disabled unless both `enabled` and `process_event.enabled` are `true`
and `process_event.filtered_function_index` is a validated non-negative `FName` index.
When enabled on more than one server instance, each ARK process receives its own callback
registration handle and unregisters that process-local handle during plugin shutdown.

The chat helper separately stays disabled unless both `enabled` and
`chat_command_helper.enabled` are `true`, the instance is allowed, and the runtime
advertises `OBELISK_API_CAPABILITY_CHAT_EVENTS` with the owner-token chat registration
functions. Its prefix is local plugin config only; it is not a public command router or
permission model.

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
