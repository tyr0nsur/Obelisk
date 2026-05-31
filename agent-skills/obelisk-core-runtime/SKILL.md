---
name: obelisk-core-runtime
description: "Use when developing or auditing Obelisk runtime stability: LD_PRELOAD bootstrap, absolute x64 ProcessEvent hook, EventManager, PluginManager, C ABI, logging, install layout, and live-server safety flags."
---

# Obelisk Core Runtime

Use this skill for runtime/core work. Do not use it for chat heuristics or UE4 reflection research unless the change affects the runtime contract.

## Scope

Own these areas:

- `loader/Bootstrap.cpp`
- `hooks/ProcessEventHook.*`
- `core/EventManager.*`
- `core/PluginManager.*`
- `core/TimerManager.*`
- `include/obelisk/ObeliskApi.h`
- `runtime/Logger.*`
- `scripts/install_obelisk.sh`
- `docs/INSTALL.md`

## Operating Rules

- Keep live servers stable before adding features.
- Gate runtime hooks and risky behavior behind explicit env vars plus safe per-instance
  marker files.
- Avoid namespace-scope or destructible function-local STL state for plugin lifecycle,
  callback registration, owner-token maps, `EventManager`, and internal event dispatchers
  in the LD_PRELOAD path. Bootstrap can run before C++ static initialization is fully
  safe, and process teardown order can call plugin cleanup after function-local statics
  are destroyed. Use first-use state with process-lifetime storage for those runtime
  registries.
- Prefer per-instance enablement under `/servidor/ark/obelisk/state/instances/<id>`.
- Plugin loading requires a non-empty safe `OBELISK_INSTANCE_ID` containing only letters,
  digits, `_`, or `-`; do not weaken this fail-closed guard for shared-cluster installs.
- Keep plugin loading optional via `OBELISK_DISABLE_PLUGINS=1`.
- Runtime plugin discovery must require `${OBELISK_ROOT}/plugins` or `OBELISK_PLUGIN_DIR`
  to already be a real non-symlink directory. Do not create or follow the plugin directory
  inside `PluginManager::LoadPlugins`; installers own layout creation. Never fall back to a
  working-directory-relative `plugins/` path.
- Never use `OBELISK_ENABLE_NATIVE_EXEC_PROBES=1` plus
  `enable-native-exec-probes` as part of normal runtime validation.
- Do not let plugin exceptions or STL types cross the C ABI boundary.
- Do not subscribe plugins to all `ProcessEvent` calls except during a specifically
  operator-approved debug window on the named debug instance, with bounded limits and a
  rollback plan.
- Global `RegisterPreProcessEvent` and `RegisterPostProcessEvent` callbacks are runtime
  default-deny. They require `OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS=1` plus the
  safe per-instance marker `allow-global-process-event-callbacks`.
- Filtered raw `ProcessEvent` callbacks are also runtime default-deny because they expose
  borrowed UE pointers and raw parameter buffers. They require
  `OBELISK_ALLOW_FILTERED_PROCESS_EVENT_CALLBACKS=1` plus the safe per-instance marker
  `allow-filtered-process-event-callbacks`; stable plugins should use copied
  `GameplayPolicyEvent` or `ChatMessageEvent` surfaces instead.
- Public `CallProcessEvent` is also runtime default-deny. It requires
  `OBELISK_ALLOW_CALL_PROCESS_EVENT=1` plus the safe per-instance marker
  `allow-call-process-event`, and the runtime only advertises
  `OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT` when that gate is active.
- `CallProcessEvent` is an ABI v1 compatibility/debug escape hatch only. It is not
  a production plugin API. ABI v1 has no owner-token call signature, so the only accepted
  legacy call context is the current `ObeliskPlugin_Init` owner while that owner has a
  captured `OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT` snapshot and the live env+marker
  gate is still active. Post-init calls through a copied `ObeliskApi` table must fail
  closed. A future callable path must use an owner-token ABI and reject calls when the
  owner's init-time capability snapshot did not advertise the callable capability.
- Pre-callback blocking of the original `ProcessEvent` is runtime default-deny. A
  callback return value of `false` is observational unless
  `OBELISK_ALLOW_PROCESS_EVENT_BLOCKING=1`, `allow-process-event-blocking`, and
  `OBELISK_API_CAPABILITY_PROCESS_EVENT_BLOCKING` are active for the instance.
- Stable posture must reject ReflectionScanner, broad ProcessEvent tracing
  (`OBELISK_PE_TRACE_LIMIT` non-zero), global callbacks, public `CallProcessEvent`, and
  ProcessEvent blocking unless an explicit debug-window workflow says otherwise.
- Experimental observer wrappers require `OBELISK_WRAPPER_PROFILE=observer-debug`, the
  `allow-observer-debug-window` marker, the observer-specific marker, and
  `allow-experimental-observers` on the same instance; stable posture must reject those
  observer/debug-window markers and observer env.
- Treat callback ownership as runtime-critical: callbacks registered by a plugin must be
  unregistered if init fails, before unload, and before `dlclose`.
- Owner cleanup must fail visibly. Dispatcher `UnregisterCallbacksForOwner(owner)` methods
  must propagate internal cleanup exceptions to `PluginManager`; a `0` return is reserved
  for "nothing removed" and must not hide a cleanup failure before `dlclose`.
- `TimerManager` is a process-lifetime runtime service for plugin-owned delayed/repeating
  callbacks. Keep it owner-token scoped through `PluginManager`, zero-failure handle
  based, process-local only, and independent of UE4/server state. Plugin unload/init
  failure must remove owner timers before `dlclose` and wait for in-flight callbacks from
  other threads.
- Reject plugin callback registrations that cannot be attributed to the currently
  initializing plugin or an already-loaded plugin owner. Do not allow ownerless callbacks
  through the public plugin API.
- Mark plugin owners as unloading before `ObeliskPlugin_Shutdown()` on init failure or
  unload. New callback registrations must be rejected while unloading, but owner-token
  unregister must remain valid so shutdown can clean existing handles.
- Plugin config default creation must validate the config root and per-plugin directory
  before writing. Reject relative or symlinked `OBELISK_CONFIG_DIR` roots and symlinked
  plugin config directories before first-run default config creation, not only before
  parsing an existing `config.json`.
- Runtime logging must reject explicit relative or symlinked `OBELISK_LOG_DIR` values,
  symlinked `${OBELISK_ROOT}/logs`, and symlinked per-instance log directories. Missing
  absolute log roots may be created; inherited env must not redirect logs through symlink
  escapes.
- Operator tooling should mirror runtime path safety: read-only CLI views must surface
  invalid plugin/config entries and avoid following symlinked plugin directories,
  per-plugin config directories, or `config.json` entries. CLI config summaries should
  report malformed activation envelopes instead of showing unsafe configs as enabled.
- Owner-token callback registration is the supported path for helper-module or
  background-thread callbacks whose function pointer does not live in the plugin `.so`.
  The runtime accepts owner-token registrations from helper/background threads during
  `ObeliskPlugin_Init` while the plugin owner is in the initializing set, then removes
  owner tokens on init failure and before/with plugin unload.
- Capability-gated owner-token registrations must check the plugin owner's init-time
  capability snapshot plus the current live runtime gate. Do not authorize public
  callback registration from process-global capability state that a later `PluginManager`
  construction could widen for an already-loaded plugin.
- For new public ProcessEvent registrations, prefer owner-token handle functions that
  return a non-zero `uint64_t` handle and require
  `UnregisterProcessEventCallbackWithOwnerToken(owner_token, handle)` for granular
  unregister. Do not expose bare unregister-by-id across the plugin ABI.
- Public and internal callback handles or owner tokens must never use `0` as a successful
  value and must not reuse currently-live IDs after counter wrap. `0` remains the failure
  sentinel across plugin-facing registration APIs.
- Keep plugin-owned lifecycle cleanup shared across `EventManager`, the internal
  `ChatEventDispatcher`, and `StructureEventDispatcher`. Public `GameplayPolicyEvent`
  subscriptions are backed by `StructureEventDispatcher` and must keep owner-token handle
  registration, owner-scoped unregister, `DestroyUserData` cleanup, and plugin unload
  cleanup intact.
- New copied event dispatcher families with owner cleanup must be added to
  `PluginManager::UnregisterPluginCallbacks` and the static guardrail in
  `scripts/test_plugin_manager_guardrails.py`; a dispatcher may be excluded only while it
  is explicitly documented as internal/test-only and not plugin-facing.
- Internal dispatchers called from the `ProcessEvent` hook must fail closed on setup or
  internal allocation errors. Do not rethrow dispatcher internals into the hook path.
  Snapshot callbacks by registration id, skip callbacks whose registration was removed
  during the same dispatch, and defer `DestroyUserData` until the outermost dispatch
  finishes. Owner/plugin cleanup that is not running inside the same dispatcher callback
  must wait for both in-flight dispatch and deferred `DestroyUserData` cleanup to finish
  before returning, so plugin unload cannot race `dlclose` against user-data destructors.
- Do not hold dispatcher mutexes while invoking plugin/gameplay callbacks. If multiple
  dispatcher families can back one public API, unregister and cleanup paths must not be
  able to deadlock across those families when callbacks unregister themselves or their
  owner token. Unregister/owner cleanup initiated from any gameplay callback family must
  avoid waiting on dispatcher cleanup; non-callback plugin unload/owner cleanup must still
  wait for all in-flight dispatch and deferred `DestroyUserData` cleanup before returning.
- For copied events that may contain player text or identity-like internal fields, keep a
  zero-subscriber fast path before payload copies when the producer or dispatcher can know
  there are no authorized callbacks. Future player identity surfaces must treat
  no-subscriber, disabled gate, unsupported binary/window, zero budget, nonmatching FName,
  and invalid shape as no-copy/no-retain paths.
- Preserve optional plugin shutdown ordering: call `ObeliskPlugin_Shutdown()` before
  plugin-owned callback cleanup and before `dlclose`.
- Follow `docs/PLUGIN_ARCHITECTURE.md` before adding plugin examples or promoting
  experimental plugins. Plugins that start HTTP servers, threads, or file readers need a
  shutdown design before stability.

## Hooking Baseline

The current ProcessEvent hook uses an absolute x64 jump:

```text
48 B8 <imm64> FF E0
mov rax, imm64; jmp rax
```

This is required because `jmp rel32` can fail when `ShooterGameServer` is mapped low and `libobelisk.so` is mapped high.

Hook removal is fail-closed. If target restore or RX reprotection fails, keep hook state
and trampoline ownership intact, return/report failure, and do not claim the hook was
removed. Bootstrap or shutdown recovery must preserve enough state for retry or diagnosis
instead of clearing the hook while patched bytes may still execute.

## Safe Runtime Validation

Do not treat any shared or player-facing ARK instance as a validation target by default.
Read `docs/agent-handoff/CURRENT.md` for the current live target posture before any
server-backed work. Use only the exact instance/map named by the current approved
live-ops brief. Historical instance names in notes or older runbooks are not approval and
must not be treated as defaults for starts, restarts, marker edits, runtime observation,
or `/servidor/ark` access.

For risky probes such as ReflectionScanner, native exec, ptrace/gcore, broad tracing, or
text/gameplay-payload logging, first obtain explicit operator approval for the exact
instance/map, marker changes, restart window, rollback plan, evidence path, and shutdown
expectation.

For an approved validation target, use the target's explicit map, instance id, copied logs,
and posture command. Do not run these checks on a protected production instance unless the
operator has approved that exact maintenance window:

```bash
pgrep -af '^./ShooterGameServer'
tail -n 80 /path/to/copied/Obelisk.log
scripts/check_obelisk_server_posture.sh --expect-stable --map <map> --instance <instance-id>
```

Expected:

- `ProcessEvent absolute x64 hook installed successfully`
- `Plugin loading disabled by OBELISK_DISABLE_PLUGINS=1`
- process remains alive
- players can join

## Runtime Hardening Priorities

- Preserve plugin-owned callback registration and unregister paths in `EventManager` and
  `PluginManager`.
- Preserve optional `ObeliskPlugin_Shutdown()` resolution outside the public API table.
- Add tests or harness coverage for shutdown order and callback cleanup.
- Keep global ProcessEvent callbacks off production paths; the runtime should reject them
  unless the explicit env+marker debug gate is active.
- Keep hook-side experimental module recognizers cheap while they remain internal. The
  historical chat recognizer is the current benchmark fixture: disabled, unmatched, and
  `OBELISK_CHAT_REFLECTION_LOG_LIMIT=0` paths must stay allocation-free in
  `chat_reflection_benchmark`; matched metadata-only `ServerSendChatMessage` should also
  remain allocation-free unless a research note justifies the regression. Hook-like text
  logging should stay at one allocation or lower.
- Any player-text or gameplay-payload logging work must keep a separate explicit gate
  (`OBELISK_CHAT_REFLECTION_LOG_TEXT=1` for the historical chat path), sanitize output
  through tested helpers, and avoid publishing player contents in docs or community
  updates.
- Require a validated, idempotent plugin shutdown export before treating thread-owning or
  HTTP-owning plugins as stable.

## Before Shipping

Run:

```bash
cmake --build build -j"$(nproc)"
git diff --check
```

For recognizer hot-path work that touches the historical chat benchmark fixture also run:

```bash
cmake --build build --target chat_reflection_benchmark
./build/chat_reflection_benchmark 20000 > /tmp/obelisk-chat-reflection-benchmark.txt
python3 scripts/check_chat_reflection_benchmark.py /tmp/obelisk-chat-reflection-benchmark.txt
```

Never commit built `.so` files, logs, server configs, or runtime state marker files.
