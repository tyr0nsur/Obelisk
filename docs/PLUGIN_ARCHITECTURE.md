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

Plugins must treat `include/obelisk/ObeliskApi.h` as a C ABI boundary:

- Export entry points with `extern "C"` and default visibility.
- Export mandatory metadata through `ObeliskPlugin_GetInfo`.
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
${OBELISK_CONFIG_DIR}/<plugin-id>/config.json
```

Resolution order:

1. `${OBELISK_CONFIG_DIR}/<plugin-id>/config.json`.

Config files should include:

- `enabled`: boolean defaulting to `false` for experimental plugins.
- `instance_allowlist`: list of `OBELISK_INSTANCE_ID` values where the plugin may run.
- `map_allowlist`: optional plugin-owned map filter when behavior genuinely depends on map.
- `log_level`: plugin-local verbosity.
- Feature gates for every risky subsystem, such as `http.enabled`,
  `process_event.enabled`, and `discovery.enabled`.
- Explicit limits: queue lengths, log retention, trace caps, request body caps,
  and timeouts.

The runtime creates a plugin's missing default config before initialization using
`default_config_json` from `ObeliskPlugin_GetInfo`. Defaults must be safe-disabled
with `enabled: false`. If metadata, default config, or an existing config is invalid,
the runtime rejects the plugin before calling `ObeliskPlugin_Init`.

The runtime interprets the common activation envelope before initialization:
`enabled=false` or a non-matching `instance_allowlist` skips
`ObeliskPlugin_Init` and closes the shared object. Plugin-specific feature gates remain
owned by the plugin and must be checked before registering callbacks or starting
background work.

## Build And Drop-In Model

Obelisk should support two plugin build paths:

- In-tree plugins for examples, experiments, and CI coverage.
- External plugins compiled against `include/obelisk/ObeliskApi.h` and copied into
  `${OBELISK_PLUGIN_DIR}` as `.so` files.

The runtime does not need to know how a plugin was compiled. On restart it scans
`${OBELISK_PLUGIN_DIR}` for `.so` files directly inside that directory, resolves
`ObeliskPlugin_GetInfo`, validates metadata/config, rejects duplicate `plugin_id`
values, applies runtime activation gates, resolves `ObeliskPlugin_Init`, optionally
resolves `ObeliskPlugin_Shutdown`, and passes enabled plugins their resolved config
paths.

The stable operational flow is:

1. Build or obtain `PluginName.so`.
2. Ensure `${OBELISK_CONFIG_DIR}/<plugin-id>/config.json` exists or let the runtime
   create the safe-disabled default on first load.
3. Copy the `.so` into `${OBELISK_ROOT}/plugins/`.
4. Restart only the target ARK instance.

Dropping a plugin into `plugins/` is therefore the discovery and config-preparation step.
Runtime activation still requires `enabled=true` and a matching `instance_allowlist`.
Plugins that should not even be discovered must stay outside the plugin directory.

## Lifecycle

Every non-trivial plugin should be designed around these phases:

1. Load config and validate ABI/capabilities.
2. Initialize plugin-owned state without starting background work.
3. Register callbacks only after all required state is ready.
4. Start optional background services after callback registration succeeds.
5. On shutdown, stop external ingress first, unregister callbacks, drain worker
   queues, join threads, then release state.

The ABI exposes metadata/config through `ObeliskPlugin_GetInfo`, initialization
through `ObeliskPlugin_Init`, and supports an
optional shutdown export resolved directly from the plugin shared object:

```cpp
extern "C" __attribute__((visibility("default")))
bool ObeliskPlugin_GetInfo(ObeliskPluginMetadata* out);

extern "C" __attribute__((visibility("default")))
bool ObeliskPlugin_Init(ObeliskApi* api, const ObeliskPluginInitContext* context);

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
- `CallProcessEvent` is a low-level trampoline escape hatch, not a stable event
  mutation API. A pre-callback that calls it must return `false`; otherwise the
  detour will also call the original and the UE function can run twice. Post-callbacks
  must not replay the same event through `CallProcessEvent`.
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

- [ ] Config path follows `${OBELISK_CONFIG_DIR}/<plugin-id>/config.json`.
- [ ] Risky features are safe-disabled and map-gated.
- [ ] No global `ProcessEvent` callback outside a documented debug gate.
- [ ] Callback lifetime is covered by runtime owner cleanup and plugin-local
      shutdown design.
- [ ] Background threads, sockets, and file readers have a stop and join path.
- [ ] HTTP endpoints are local-only by default, authenticated when mutating, and
      bounded by request limits.
- [ ] Raw UE memory scanning is absent from the stable path.
- [ ] Build, `git diff --check`, and isolated runtime validation are recorded.
