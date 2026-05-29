# Plugin Architecture

This document defines the expected shape for Obelisk plugins before promoting them into
the first-party release set.

## Repository Layout

Keep plugin source code split by maturity:

```text
plugins/
  README.md
  oBaseEvents/
  oPolicyAudit/
```

`oBaseEvents` is the first official plugin planned for release. Keep it small and focused
on teaching the plugin model.

`oPolicyAudit` is an experimental first-party example for `GameplayPolicyEvent`
descriptors and callbacks. It is excluded from the default build and release scope unless
`OBELISK_BUILD_EXPERIMENTAL_PLUGINS=ON`.

## Plugin Categories

| Category | Purpose | Build policy | Runtime policy |
| --- | --- | --- | --- |
| `oBaseEvents` | Official reference plugin for event/config/lifecycle patterns. | Built by default. | Published with `scripts/install_obelisk_plugin.sh`; activation remains config and instance gated. |
| `oPolicyAudit` | Experimental example for copied `GameplayPolicyEvent` auditing. | Excluded unless `OBELISK_BUILD_EXPERIMENTAL_PLUGINS=ON`. | Do not publish as part of the first release; install only for isolated tests. |
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
- Treat the `ObeliskApi*` and `ObeliskPluginInitContext*` passed to
  `ObeliskPlugin_Init` as borrowed for init only. Copy `ObeliskApi` by value if shutdown,
  worker threads, or later callbacks need runtime function pointers.
- Metadata strings returned by `ObeliskPlugin_GetInfo` must point to static or
  plugin-owned storage that remains valid until the shared object is closed.

Runtime-owned callback cleanup is already part of the stable baseline. Plugin
authors must still make callback registration explicit and avoid registering
callbacks from background threads unless the runtime API documents that path.
Callbacks registered through the current ABI are accepted only when the runtime can assign
them to the plugin being initialized, to an already-loaded plugin shared object, or to a
valid `plugin_owner_token` supplied in `ObeliskPluginInitContext`. Callback functions in
helper `.so` files, external thunks, or background threads must use the owner-token
registration functions and remain covered by plugin-local shutdown tests. New code should
prefer the handle-returning owner-token functions when
`OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS` and
`OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES` are both advertised, store the
returned non-zero handle in process-local state, and call
`UnregisterProcessEventCallbackWithOwnerToken` during shutdown before callback code or
state can disappear. Owner-token registration is valid during `ObeliskPlugin_Init`, even
from helper/background threads, and remains valid after successful load until unload.

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
  Entries must be non-empty safe tokens using only letters, digits, `_`, or `-`.
- `allow_all_instances`: explicit boolean escape hatch for operators who intentionally
  want `enabled=true` to run on every instance sharing the config.
- `log_level`: plugin-local verbosity.
- Feature gates for every risky subsystem, such as `http.enabled`,
  `process_event.enabled`, and `discovery.enabled`.
- Explicit limits: queue lengths, log retention, trace caps, request body caps,
  and timeouts.

The runtime creates a plugin's missing default config before initialization using
`default_config_json` from `ObeliskPlugin_GetInfo`. Defaults must be safe-disabled
with `enabled: false`, must include an `instance_allowlist` array, and must set
`allow_all_instances: false` explicitly. If metadata, default config, or an existing config
is invalid, the runtime rejects the plugin before calling `ObeliskPlugin_Init`.
Existing config paths must stay inside the central config tree as regular files and
directories; symlinked plugin config directories or `config.json` files are rejected.

The runtime interprets the common activation envelope before initialization:
`enabled=false`, a missing/empty `instance_allowlist`, or a non-matching
`instance_allowlist` skips `ObeliskPlugin_Init` and closes the shared object. An enabled
plugin may run on every instance only when `allow_all_instances=true` is present. Plugin-
specific feature gates remain owned by the plugin and must be checked before registering
callbacks or starting background work. If a feature is explicitly enabled but its routing
inputs are invalid, such as a filtered `ProcessEvent` feature with a negative FName index,
the plugin should fail closed instead of silently behaving as disabled. Do not publish map-scoped config fields
until the plugin has a reliable map identity source; the runtime does not enforce map
identity today.

In clustered deployments, multiple ARK processes may share the same `${OBELISK_CONFIG_DIR}`
and plugin binaries. Plugin config should therefore be treated as shared, mostly-static
input. Plugin-owned mutable state should be instance-scoped by default, using the supplied
`instance_id` or an operator-configured per-instance path. A plugin may use shared mutable
state only when it documents the file/process ownership model and uses atomic writes or
locking that is safe across multiple server processes.
Runtime values are process-local unless the plugin explicitly builds a cross-process
protocol around them. Callback handles, owner tokens, worker threads, sockets, in-memory
caches, borrowed UE pointers, and open file descriptors must not be persisted into shared
config or reused by another ARK server process.

Callback registration handles are process-local runtime values. Do not write them into
shared config, cluster state, or cross-instance files; a handle from one ARK process is not
valid in another server process that happens to load the same plugin binary.

## Build And Drop-In Model

Obelisk should support two plugin build paths:

- In-tree plugins for examples, experiments, and CI coverage.
- External plugins compiled against `include/obelisk/ObeliskApi.h` and copied into
  `${OBELISK_PLUGIN_DIR}` as `.so` files.

The runtime does not need to know how a plugin was compiled. On restart it requires an
explicit absolute plugin directory from `${OBELISK_PLUGIN_DIR}` or `${OBELISK_ROOT}/plugins`;
it does not fall back to a `plugins/` directory relative to the ARK process working
directory. It scans `.so` files directly inside that directory, resolves
`ObeliskPlugin_GetInfo`, validates metadata/config, rejects duplicate `plugin_id` values,
applies runtime activation gates, resolves `ObeliskPlugin_Init`, optionally resolves
`ObeliskPlugin_Shutdown`, and passes enabled plugins their resolved config paths.

Treat `${OBELISK_PLUGIN_DIR}` as shared discovery scope in clustered installs. Copying a
plugin there publishes it for discovery by every ARK process that shares the directory;
activation is still limited by config. `ObeliskPlugin_GetInfo` must therefore be
side-effect-free and safe to call on instances where the plugin will not initialize.

The stable operational flow is:

1. Build or obtain `PluginName.so`.
2. Ensure `${OBELISK_CONFIG_DIR}/<plugin-id>/config.json` exists or let the runtime
   create the safe-disabled default on first load.
3. Install the `.so` with `scripts/install_obelisk_plugin.sh PluginName.so <obelisk-root>`.
4. Restart only the target ARK instance.

The plugin installer copies to a temporary non-`.so` name in the destination directory and
then publishes with an atomic rename, so runtime discovery cannot see a partial copy. Direct
`cp` into the active plugin directory is not the stable deployment path. Dropping a plugin
into `plugins/` is therefore the discovery and config-preparation step.
Runtime activation still requires `enabled=true` and either a matching
`instance_allowlist` or explicit `allow_all_instances=true`. Plugins that should not even
be discovered must stay outside the plugin directory.

## Lifecycle

Every non-trivial plugin should be designed around these phases:

1. Load config and validate ABI/capabilities.
2. Initialize plugin-owned state without starting background work.
3. Register callbacks only after all required state is ready.
4. Start optional background services after callback registration succeeds.
5. On shutdown, stop external ingress first, unregister callbacks, drain worker
   queues, join threads, then release state.

The safest callback registration point is `ObeliskPlugin_Init`, where the runtime assigns
the current plugin owner explicitly. Post-init registration is allowed only for callbacks
whose function pointer resolves back to an already-loaded Obelisk plugin shared object or
when the plugin passes its `plugin_owner_token` to the append-only owner-token registration
functions. Plugins must check `struct_size`, `OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS`,
and non-null function pointers before using those fields.
Strings in `ObeliskPluginInitContext`, including `config_dir`, `config_path`, and
`instance_id`, are borrowed for `ObeliskPlugin_Init`; copy them into plugin-owned storage
before using them from shutdown hooks, worker threads, or later callbacks.

For callback code owned by helper modules, worker threads, or reloadable state, prefer the
handle-returning owner-token API and explicit unregister:

1. Check `OBELISK_API_CAPABILITY_OWNER_TOKEN_CALLBACKS`,
   `OBELISK_API_CAPABILITY_PROCESS_EVENT_CALLBACK_HANDLES`, `struct_size`, a non-zero
   `plugin_owner_token`, and the relevant function pointers.
2. Register with `RegisterPreProcessEventForNameIndexWithOwnerTokenHandle` or the matching
   post/global variant.
3. Treat a `0` return value as rejected registration.
4. On shutdown, stop external ingress first, call
   `UnregisterProcessEventCallbackWithOwnerToken(owner_token, handle)` while callback code
   and state are still valid, drain in-flight work, then join threads and release state.

Owner-token attribution is not a lifetime system by itself. Runtime owner cleanup on
plugin unload remains the backstop, but stable plugins should unregister their own
long-lived callbacks explicitly.

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
- Global callbacks are rejected by default. They require both
  `OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS=1` and the per-instance marker
  `allow-global-process-event-callbacks`; only then does the runtime advertise
  `OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS`.
- A plugin that does not see `OBELISK_API_CAPABILITY_GLOBAL_PROCESS_EVENT_CALLBACKS`
  must treat `RegisterPreProcessEvent` and `RegisterPostProcessEvent` as unavailable.
- Handle-returning global registration follows the same gate and returns `0` when global
  callbacks are not explicitly enabled for the current instance.
- Any global-callback debug window also requires a documented objective, bounded trace
  limits, named debug instance, and rollback plan.
- Pre-callbacks are observational by default. A `false` return blocks the original
  `ProcessEvent` only when `OBELISK_ALLOW_PROCESS_EVENT_BLOCKING=1`, the per-instance
  `allow-process-event-blocking` marker exists, and
  `OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING` is advertised. Stable plugins should
  return `true`.
- Global callbacks must not block, allocate heavily, perform file or network I/O,
  parse JSON, sleep, or take contended locks.
- Parameter decoding must be reflection-backed before it is considered stable.
  Raw memory scans and string heuristics are research tools only.
- `CallProcessEvent` is a low-level trampoline escape hatch, not a stable event
  mutation API. It is rejected by default and requires both
  `OBELISK_ALLOW_CALL_PROCESS_EVENT=1` and the per-instance marker
  `allow-call-process-event`; only then does the runtime advertise
  `OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT`. A pre-callback that calls it should return
  `false`; if it returns `true`, the runtime skips the automatic original call and warns
  to avoid double execution. Post-callbacks must not replay the same event through
  `CallProcessEvent`.
- A global callback may be acceptable for an isolated discovery run if the explicit gate
  is enabled only on the approved debug instance and the test has rollback instructions.

Promotion from experimental to stable requires proving that a plugin can run
with filtered callbacks only, or documenting why a global callback is necessary
and measuring its overhead on an isolated server.

## Gameplay Event Promotion Gate

Future gameplay event APIs must be Obelisk-level contracts, not thin wrappers over UE4
runtime objects. Do not promote a module event into the public SDK until the promotion PR
proves all of these items together:

- the reflected function or struct target set has accepted, distinct second-source
  evidence and the readiness report says `promotion_gate.ready=true`;
- every callback payload is copied into Obelisk-owned POD storage before plugin code runs;
- the public structs contain explicit sizes and primitive fields only, with no `UObject`,
  `UFunction`, `FString`, raw parameter buffer, UE property pointer, STL type, reference,
  exception, or ownership-bearing C++ object crossing the ABI;
- registration is append-only in `ObeliskApi`, guarded by a capability bit, returns a
  non-zero process-local handle, and has an owner-token unregister path;
- plugin-owner cleanup removes the event callbacks on init failure and before `dlclose`;
- SDK consumer tests build against the installed headers and exercise register,
  unregister, shutdown cleanup, and rejected capability paths;
- release docs name every promoted target set and keep runtime-observer log summaries
  separate from second-source promotion evidence.

The promoted v0.1 gameplay surface is `GameplayPolicyEvent`, an Obelisk-level copied POD
policy signal backed by the accepted `structure-observer-intake` target set and the
accepted compact inventory/structure layouts from `minimal-second-source-intake`. It is
not a public `StructureEvents` wrapper, not a public Inventory SDK, and it does not expose
UE4 objects. Plugins subscribe with `RegisterGameplayPolicyEventWithOwnerTokenHandle`, an
event-kind mask, and a process-local owner-token handle; shutdown must call
`UnregisterGameplayPolicyEventWithOwnerToken`.

`GameplayPolicyEvent` exposes only approved scalar fields through `field_mask`,
`bool_values`, and `int32_values`: return values, variant index, force-set, force,
requested-by-player, and ignore-cooldown where the backing target contains them. Pincode
values, player identity, character identity, structure identity, inventory identity, item
identity, raw params, FName/GNames/GObjects indices, and all UE pointers remain redacted.
`STRUCTURE_PIN_CODE_CHECK` is ReturnValue-only; plugins that do not want that timing
signal should omit its event-kind mask. Inventory-backed policy events are still generic
policy events under the same callback family. They use
`OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL` for every promoted policy event,
`OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY`,
`OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED`, and
`OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM`; they do not promote
`InventoryPolicyEvent*` structs, Inventory callback capability bits, item handles,
inventory lookup, inventory contents, item/player handles, mutation, or return override
authority.
Filtered `ProcessEvent` callbacks and runtime-observer log summaries are still not a public gameplay event API.

In v0.1, `resource_kind` is a category only, not a game object identity. It may be used for
routing, metrics, and sanitized logs such as "this policy event is structure-backed" or
"inventory-item-backed"; it must not be treated as "this same structure/item", a lookup
handle, a persistent ID, or a way to link events to a player, tribe, inventory, actor,
coordinates, or UE object.
`DescribeResourceKind` is the only v0.1 resource metadata helper: it returns a copied POD
descriptor for known categories with supported event/field masks and explicit
category-only/no-identity/no-lookup flags. Plugins must check the resource descriptor
capability bit, that `struct_size` covers the appended `DescribeResourceKind` slot, and
that the function pointer is non-null before calling it. Do not add `GetResource`,
`ResolveResource`, `ResourceHandle`, pointer-derived IDs, GNames/GObjects-derived IDs, or
object mutation APIs until a later promotion gate defines identity stability, privacy,
lifecycle, and cross-instance semantics.

`DescribeGameplayPolicyEventKind` is the matching event-kind metadata helper. It returns
copied POD descriptors for promoted `GameplayPolicyEvent` kinds: stable event name,
resource category, event-kind mask, supported field mask, and copied-payload/backing flags.
It is discovery data for routing and plugin configuration, not a module SDK, object
identity, UE lookup, mutation path, or return-override API. Plugins must check
`OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS`, `struct_size`, and the
function pointer before using it.

`ChatMessageEvent` is the other v0.1-rc public event ABI surface, but it is intentionally
minimal and separate from gameplay policy events. It carries copied UTF-8 chat message
bytes, `send_mode`, copied-payload flags, and a process-local `sequence` through
`RegisterChatMessageEventWithOwnerTokenHandle` and
`UnregisterChatMessageEventWithOwnerToken`. Plugins must check
`OBELISK_API_CAPABILITY_CHAT_EVENTS`, `struct_size`, a non-zero owner token, and both
function pointers before subscribing. The callback data is valid only for the callback
duration. The event does not expose sender/player identity, resource identity, raw
`FString`, `UObject`, `UFunction`, raw parameter buffers, FName/GObjects indices, chat
send/moderation/blocking authority, command registration/routing, mutation, or return
override. Plugins that want commands must parse the copied text locally; Obelisk v0.1 does
not ship a separate command SDK. Runtime producer hookup remains a separate gate, so
registration support does not by itself prove end-to-end chat delivery.

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
- [ ] Risky features are safe-disabled and scoped with `instance_allowlist` or explicit
      `allow_all_instances`; map filters are plugin-owned until a reliable map identity is
      available.
- [ ] No global `ProcessEvent` callback outside a documented debug gate.
- [ ] Callback lifetime is covered by runtime owner cleanup and plugin-local
      shutdown design.
- [ ] Runtime handles, owner tokens, worker threads, sockets, caches, and mutable files are
      process-local by default, or have a documented cross-process ownership and locking
      design.
- [ ] Helper-module or background-thread callbacks use handle-returning owner-token
      registration and explicit unregister before their code/state is released.
- [ ] Background threads, sockets, and file readers have a stop and join path.
- [ ] HTTP endpoints are local-only by default, authenticated when mutating, and
      bounded by request limits.
- [ ] Raw UE memory scanning is absent from the stable path.
- [ ] Build, `git diff --check`, and isolated runtime validation are recorded.
