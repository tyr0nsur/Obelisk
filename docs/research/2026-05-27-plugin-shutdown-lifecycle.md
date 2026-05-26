# Plugin Shutdown Lifecycle

## Objective

Add the smallest runtime lifecycle step that lets plugins export
`ObeliskPlugin_Shutdown()` and have Obelisk call it before unloading the shared
object, without changing the existing `ObeliskApi` function table layout.

## Environment

- Obelisk commit at start: `1870682`
- Working directory: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-27
- No live-server state or `/servidor/ark` files touched.

## Hypothesis

An optional exported C symbol can provide plugin shutdown without breaking ABI
because it is resolved with `dlsym` from the plugin `.so` and is not appended to
or inserted into `ObeliskApi`.

## Method

- Added an internal `ShutdownFunc = void(*)()` in `core/PluginManager.cpp`.
- Resolved optional `ObeliskPlugin_Shutdown` after resolving the required
  `ObeliskPlugin_Init`.
- Stored the shutdown function pointer in `PluginInfo` for initialized plugins.
- Called shutdown before owner callback cleanup and before `dlclose`.
- Also called shutdown on init failure when the symbol exists, before callback
  owner cleanup and `dlclose`, to let partially initialized plugins stop any
  external ingress they may have started.
- Wrapped runtime calls to shutdown in `try/catch` so plugin exceptions do not
  unwind through the runtime.
- Documented the optional export in `api/ObeliskApi.h`,
  `docs/PLUGIN_ARCHITECTURE.md`, and the ABI/runtime skills.

## Evidence

Validation run:

```bash
cmake --build build -j"$(nproc)"
```

Result: build completed successfully. The build emitted an existing warning from
the vendored `fmt/spdlog` path while compiling `hooks/ProcessEventHook.cpp`; it
did not stop the build.

## Result

Runtime support for optional plugin shutdown exists without changing the public
`ObeliskApi` struct size or field offsets. Existing plugins that only export
`ObeliskPlugin_Init` still load and unload through callback owner cleanup.

## Rejected Paths

- Did not add a shutdown function pointer to `ObeliskApi`, because that would
  require plugins to inspect `struct_size` before use and would still expand the
  ABI table for a lifecycle operation that can be discovered as a plugin export.
- Did not promote or modify `MonitorPlugin`.

## Risks

- Shutdown is only invoked during runtime unload paths; there is no isolated
  plugin test yet proving ordering with active background threads.
- A plugin that throws from shutdown is logged by the runtime, but any plugin
  state left behind remains the plugin's responsibility.
- Existing plugins without `ObeliskPlugin_Shutdown` remain unsuitable for stable
  thread/socket/file-reader behavior.

## Next Steps

- Add a small example or test plugin that exports shutdown and records call order
  when a plugin test harness exists.
- Add explicit unregister functions only if a future plugin contract needs
  plugin-driven callback removal before runtime unload.
- Keep `MonitorPlugin` experimental until it implements a validated idempotent
  shutdown path and separates unrelated responsibilities.

## Skill Updates Needed

- Updated `agent-skills/obelisk-c-abi-validation/SKILL.md` with the optional
  export contract and ordering requirement.
- Updated `agent-skills/obelisk-core-runtime/SKILL.md` so future runtime work
  requires validated plugin shutdown before treating thread-owning or HTTP-owning
  plugins as stable.
