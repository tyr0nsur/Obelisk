# Plugins

This directory contains first-party Obelisk plugins.

Read [../docs/PLUGIN_ARCHITECTURE.md](../docs/PLUGIN_ARCHITECTURE.md) before adding a new
plugin.

## First-Party Plugins

```text
plugins/
  oBaseEvents/    Official example plugin for events, config, ABI checks, and shutdown.
  oProcessTimer/  Official core example plugin for process-local Obelisk timers.
```

`oBaseEvents` is the first plugin planned for the initial public release. It should remain
small and instructional: it exists to show contributors how to build their own Obelisk
plugin, not to become a feature-heavy server plugin.

`oProcessTimer` is part of the first-stable core plugin set for `v0.1.0`. It demonstrates
only the process-local timer ABI: owner-token registration, zero-failure handles, and
explicit unregister on shutdown. It is not a gameplay/module timer abstraction and does not
use UE timers, gameplay timers, UE identity, lookup, permissions, commands, shared
scheduler state, persistent handles, or cluster coordination.

## Experimental Examples

`oPolicyAudit` demonstrates the promoted `GameplayPolicyEvent` callback family without
touching `ProcessEvent`, UE internals, object identity, or pointer-derived data.
`oChatLogger` demonstrates the minimal copied `ChatMessageEvent` surface by logging only
event metadata and copied message size, not player identity or raw chat payload text.
Their default configs are safe-disabled and cluster-scoped. They are not part of the first
release scope or the default top-level build; build them only when explicitly investigating
experimental examples:

```bash
cmake -S . -B build -DOBELISK_BUILD_EXPERIMENTAL_PLUGINS=ON
cmake --build build --target oPolicyAudit oChatLogger -j"$(nproc)"
```

```json
{
  "enabled": false,
  "allow_all_instances": false,
  "instance_allowlist": [],
  "policy_audit": {
    "enabled": false,
    "event_kind_mask": 255,
    "log_limit": 10
  }
}
```

`oChatLogger` config:

```json
{
  "enabled": false,
  "allow_all_instances": false,
  "instance_allowlist": []
}
```

`oChatLogger` logs a bounded first set per chat send mode, currently up to sixteen accepted
events for each mode `0..3`. It records only sequence, send mode, copied-payload flag,
message size, per-mode count, and first-observed status; it does not log raw chat text,
sender identity, or UE pointers.

## Policy

- Plugins activate only when their `.so` is published into the runtime `plugins/`
  directory. Use `scripts/install_obelisk_plugin.sh` instead of copying directly into the
  active directory, so shared clusters never discover a partial `.so`. In a clustered
  install that directory can be shared by every ARK instance, so use `instance_allowlist`
  for targeted rollout. `enabled=true` with an empty allowlist stays skipped unless
  `allow_all_instances=true` is set explicitly.
- Stable plugins must use runtime-owned central config paths:
  `${OBELISK_CONFIG_DIR}/<plugin-id>/config.json`.
- Treat multi-instance loading as the default cluster shape. A plugin may read shared
  config from every ARK process, but mutable plugin state should be stored per
  `OBELISK_INSTANCE_ID` unless the plugin has a documented cross-process locking model.
- Prefer copied Obelisk-level events. Filtered and global raw `ProcessEvent` callbacks
  require explicit debug gates and isolated validation.
- Long-lived callbacks should use owner-token handle registration and explicit unregister
  during shutdown; registration handles are process-local, not shared cluster state.
- Plugins that start HTTP servers, threads, or file readers need a documented shutdown
  design before they can be stable.
