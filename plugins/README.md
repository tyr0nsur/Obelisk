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

- Plugins activate only when their `.so` is copied into the runtime `plugins/` directory.
- Stable plugins must use central config paths:
  `${OBELISK_CONFIG_DIR}/plugins/<plugin-id>/<config-file>` or an explicitly documented
  plugin override env var.
- Prefer filtered `ProcessEvent` callbacks. Global callbacks require an explicit research
  gate and isolated validation.
- Plugins that start HTTP servers, threads, or file readers need a documented shutdown
  design before they can be stable.
