# Plugins

This directory contains first-party Obelisk plugins.

Read [../docs/PLUGIN_ARCHITECTURE.md](../docs/PLUGIN_ARCHITECTURE.md) before adding a new
plugin.

## Current Release Target

```text
plugins/
  oBaseEvents/    Official example plugin for events, config, ABI checks, and shutdown.
```

`oBaseEvents` is the first plugin planned for the initial public release. It should remain
small and instructional: it exists to show contributors how to build their own Obelisk
plugin, not to become a feature-heavy server plugin.

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
- Prefer filtered `ProcessEvent` callbacks. Global callbacks require an explicit research
  gate and isolated validation.
- Long-lived callbacks should use owner-token handle registration and explicit unregister
  during shutdown; registration handles are process-local, not shared cluster state.
- Plugins that start HTTP servers, threads, or file readers need a documented shutdown
  design before they can be stable.
