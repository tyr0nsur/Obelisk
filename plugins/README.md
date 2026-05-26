# Plugins

This directory contains Obelisk plugins and plugin experiments.

Read [../docs/PLUGIN_ARCHITECTURE.md](../docs/PLUGIN_ARCHITECTURE.md)
before adding a new plugin or promoting an existing one.

## Intended Layout

```text
plugins/
  examples/       Small reference plugins, each showing one safe pattern.
  experimental/   Research plugins and prototypes excluded from top-level build.
```

The repository is still transitioning to that layout. Existing directories such
as `chat/` and `monitor/` are not automatically stable because they live under
`plugins/`.

## Current Policy

- `monitor/` is experimental. Do not add it to the top-level build yet.
- New examples should be minimal, safe-disabled by default, and documented.
- Stable candidates must use central config paths:
  `${OBELISK_CONFIG_DIR}/plugins/<plugin-id>.json`.
- Prefer filtered `ProcessEvent` callbacks. Global callbacks require an explicit
  research gate and isolated validation.
- Plugins that start HTTP servers, threads, or file readers need a documented
  shutdown design before they can be stable.

## Example Candidates

Future examples should be split by responsibility:

- `examples/minimal`: load, log, validate ABI, return.
- `examples/process_event_filtered`: register one filtered callback by known
  `FName` index and do no I/O inside the callback.
- `examples/http_status`: expose a localhost-only read-only status endpoint with
  request limits and a clean shutdown path once the ABI supports shutdown.
