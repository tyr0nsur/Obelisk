# Plugin Architecture

This document defines the expected shape for Obelisk plugins before promoting
larger plugins such as `MonitorPlugin` beyond experimental status.

## Repository Layout

Keep plugin source code split by maturity:

```text
plugins/
  README.md
  examples/
    minimal/
    process_event_filtered/
    http_status/
  experimental/
    monitor/
  chat/
  monitor/
```

Current reality is still transitional: `plugins/chat` and `plugins/monitor`
exist at the top of `plugins/`, but only the deliberately small
`helloworld_plugin` target is built by the top-level build as a stable example.
Do not add `plugins/monitor` to the top-level build until the responsibilities
below are separated and validated in isolation.

## Plugin Categories

| Category | Purpose | Build policy | Runtime policy |
| --- | --- | --- | --- |
| `examples/` | Minimal reference plugins that teach one safe pattern. | May be built by CI after review. | Disabled by default unless explicitly installed. |
| `experimental/` | Research, probes, and prototype integrations. | Excluded from top-level build by default. | Do not install into `plugins/` except isolated tests. |
| stable plugin directories | Operational plugins with documented config, tests, and rollback. | Eligible for top-level build after review. | Map-gated rollout only. |

An example plugin should demonstrate exactly one behavior. For example, an HTTP
status example should not also decode `ProcessEvent` params, and a filtered
`ProcessEvent` example should not also start background services.

## ABI Boundary

Plugins must treat `api/ObeliskApi.h` as a C ABI boundary:

- Export entry points with `extern "C"` and default visibility.
- Pass only POD structs, primitive types, raw pointers, explicit sizes, and
  function pointers across the boundary.
- Do not pass STL types, C++ classes, references, exceptions, RTTI-dependent
  objects, or ownership-bearing wrappers across the ABI.
- Catch all plugin exceptions before returning to the runtime.
- Check `abi_version`, `struct_size`, and capability flags before using appended
  API fields when the plugin depends on them.

Runtime-owned callback cleanup is already part of the stable baseline. Plugin
authors must still make callback registration explicit and avoid registering
callbacks from background threads unless the runtime API documents that path.

## Configuration Convention

Plugin configuration belongs under the central install root, not the ARK binary
directory:

```text
${OBELISK_CONFIG_DIR}/plugins/<plugin-id>/config.json
```

Fallback order:

1. A plugin-specific override env var, for example
   `OBELISK_MONITOR_CONFIG=/path/to/monitor.json`.
2. `${OBELISK_CONFIG_DIR}/plugins/<plugin-id>/config.json`.
3. `${OBELISK_CONFIG_DIR}/plugins/<plugin-id>.json` for legacy plugins.
4. `${OBELISK_ROOT}/config/plugins/<plugin-id>/config.json`.
5. `${OBELISK_ROOT}/config/plugins/<plugin-id>.json` for legacy plugins.

Config files should include:

- `enabled`: boolean defaulting to `false` for experimental plugins.
- `map_allowlist`: list of map names where the plugin may run.
- `log_level`: plugin-local verbosity.
- Feature gates for every risky subsystem, such as `http.enabled`,
  `process_event.enabled`, and `discovery.enabled`.
- Explicit limits: queue lengths, log retention, trace caps, request body caps,
  and timeouts.

Plugins may create a default config on first initialization when the file is missing, but
the generated defaults must be safe-disabled. They should create only their own
`plugins/<plugin-id>/` config directory and log the chosen config path.

## Build And Drop-In Model

Obelisk should support two plugin build paths:

- In-tree plugins for examples, experiments, and CI coverage.
- External plugins compiled against `api/ObeliskApi.h` and copied into
  `${OBELISK_PLUGIN_DIR}` as `.so` files.

The runtime does not need to know how a plugin was compiled. On restart it scans
`${OBELISK_PLUGIN_DIR}` for `.so` files, resolves `ObeliskPlugin_Init`, optionally resolves
`ObeliskPlugin_Shutdown`, and lets the plugin initialize its own safe config defaults.

The stable operational flow is:

1. Build or obtain `PluginName.so`.
2. Ensure `${OBELISK_ROOT}/config/plugins/plugin-name/config.json` exists or that the
   plugin creates a safe-disabled default on first init.
3. Copy the `.so` into `${OBELISK_ROOT}/plugins/`.
4. Restart only the target ARK instance.

Dropping a plugin into `plugins/` is therefore the activation step. Plugins that should not
load must stay outside the plugin directory.

## Lifecycle

Every non-trivial plugin should be designed around these phases:

1. Load config and validate ABI/capabilities.
2. Initialize plugin-owned state without starting background work.
3. Register callbacks only after all required state is ready.
4. Start optional background services after callback registration succeeds.
5. On shutdown, stop external ingress first, unregister callbacks, drain worker
   queues, join threads, then release state.

The ABI exposes initialization through `ObeliskPlugin_Init` and supports an
optional shutdown export resolved directly from the plugin shared object:

```cpp
extern "C" __attribute__((visibility("default")))
void ObeliskPlugin_Shutdown();
```

This export is not part of the `ObeliskApi` function table, so it does not shift
existing ABI offsets. When present, the runtime calls shutdown before
unregistering plugin-owned callbacks and before `dlclose`. Plugin shutdown must
be idempotent, must stop external ingress first, and must catch all exceptions
before returning across the C ABI boundary. Plugins that start threads, sockets,
or long-lived file readers remain experimental until they implement and validate
this shutdown path.

## ProcessEvent Policy

`ProcessEvent` is a hot path. Global callbacks are the highest-risk plugin
integration point.

Rules:

- Prefer `RegisterPreProcessEventForNameIndex` or another filtered API.
- Global callbacks require a documented debug objective, a bounded trace limit,
  and an explicit config or env gate.
- Global callbacks must not block, allocate heavily, perform file or network I/O,
  parse JSON, sleep, or take contended locks.
- Parameter decoding must be reflection-backed before it is considered stable.
  Raw memory scans and string heuristics are research tools only.
- A global callback may be acceptable for an isolated discovery run if plugins
  are otherwise disabled on live maps and the test has rollback instructions.

Promotion from experimental to stable requires proving that a plugin can run
with filtered callbacks only, or documenting why a global callback is necessary
and measuring its overhead on an isolated server.

## HTTP And Security

HTTP-capable plugins are two systems: an Obelisk plugin and a network service.
They need separate gates.

Minimum HTTP requirements before stability:

- Bind to `127.0.0.1` by default. Binding to `0.0.0.0` must require explicit
  config.
- Authentication for every mutating endpoint.
- Request body size limits and content-type checks.
- Timeouts for reads, writes, and idle connections.
- No config write endpoint without auth, validation, atomic write, and a backup
  or rollback path.
- No server log streaming endpoint that can expose secrets unless explicitly
  enabled and access-controlled.
- A shutdown path that stops accepting requests and joins the HTTP thread.

Until those controls exist, HTTP plugins belong in `experimental/` and should be
installed only on isolated test instances or behind a trusted local proxy.

## Why MonitorPlugin Is Experimental

`plugins/monitor` is useful as a prototype, but it is not a stable plugin
architecture yet:

- It registers a global `ProcessEvent` callback rather than a filtered callback.
- It discovers `PreLogin` by scanning raw parameter memory and caching a name
  index heuristic.
- It starts detached log and HTTP threads with no plugin shutdown path.
- Its HTTP server binds to `0.0.0.0` and exposes config/log endpoints without a
  documented auth and network policy.
- It reads and writes config outside the central config convention.
- It combines monitoring, whitelist enforcement, HTTP API, log tailing, and UE4
  event discovery in one plugin.

For that reason, keep `MonitorPlugin` out of the top-level build and out of the
stable install path. The safe path forward is to split it into small examples or
future plugins: one HTTP status example, one config convention example, one
filtered `ProcessEvent` example, and a later monitor plugin that only composes
validated pieces.

## Promotion Checklist

Before a plugin is promoted to stable or added to the top-level build:

- [ ] Config path follows `${OBELISK_CONFIG_DIR}/plugins/<plugin-id>.json`.
- [ ] Risky features are safe-disabled and map-gated.
- [ ] No global `ProcessEvent` callback outside a documented debug gate.
- [ ] Callback lifetime is covered by runtime owner cleanup and plugin-local
      shutdown design.
- [ ] Background threads, sockets, and file readers have a stop and join path.
- [ ] HTTP endpoints are local-only by default, authenticated when mutating, and
      bounded by request limits.
- [ ] Raw UE memory scanning is absent from the stable path.
- [ ] Build, `git diff --check`, and isolated runtime validation are recorded.
