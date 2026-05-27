# Plugin Architecture

This document defines the expected shape for Obelisk plugins before promoting them into
the first-party release set.

## Repository Layout

Keep plugin source code split by maturity:

```text
plugins/
  README.md
  oBaseEvents/
```

`oBaseEvents` is the first official plugin planned for release. Keep it small and focused
on teaching the plugin model.

## Plugin Categories

| Category | Purpose | Build policy | Runtime policy |
| --- | --- | --- | --- |
| `oBaseEvents` | Official reference plugin for event/config/lifecycle patterns. | Built by default. | Installed only when the operator copies the `.so` into the runtime plugin directory. |
| research branches | Probes and prototype integrations. | Excluded from top-level build by default. | Do not install into `plugins/` except isolated tests. |
| stable plugin directories | Operational plugins with documented config, tests, and rollback. | Eligible for top-level build after review. | Instance-gated rollout only. |

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
${OBELISK_CONFIG_DIR}/<plugin-id>/<plugin-config-file>
```

Resolution order:

1. `${OBELISK_CONFIG_DIR}/<plugin-id>/<plugin-config-file>`.

Config files should include:

- `enabled`: boolean defaulting to `false` for experimental plugins.
- `instance_allowlist`: list of `OBELISK_INSTANCE_ID` values where the plugin may run.
- `map_allowlist`: optional plugin-owned map filter when behavior genuinely depends on map.
- `log_level`: plugin-local verbosity.
- Feature gates for every risky subsystem, such as `http.enabled`,
  `process_event.enabled`, and `discovery.enabled`.
- Explicit limits: queue lengths, log retention, trace caps, request body caps,
  and timeouts.

Plugins may create a default config on first initialization when the file is missing, but
the generated defaults must be safe-disabled. They should create only their own
`<plugin-id>/` config directory and log the chosen config path.

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
2. Ensure `${OBELISK_CONFIG_DIR}/plugin-name/<config-file>` exists or that the
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

## Promotion Checklist

Before a plugin is promoted to stable or added to the top-level build:

- [ ] Config path follows `${OBELISK_CONFIG_DIR}/<plugin-id>/<config-file>`.
- [ ] Risky features are safe-disabled and map-gated.
- [ ] No global `ProcessEvent` callback outside a documented debug gate.
- [ ] Callback lifetime is covered by runtime owner cleanup and plugin-local
      shutdown design.
- [ ] Background threads, sockets, and file readers have a stop and join path.
- [ ] HTTP endpoints are local-only by default, authenticated when mutating, and
      bounded by request limits.
- [ ] Raw UE memory scanning is absent from the stable path.
- [ ] Build, `git diff --check`, and isolated runtime validation are recorded.
