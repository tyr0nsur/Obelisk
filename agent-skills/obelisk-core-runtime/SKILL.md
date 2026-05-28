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
- `api/ObeliskApi.h`
- `runtime/Logger.*`
- `scripts/install_obelisk.sh`
- `docs/INSTALL.md`

## Operating Rules

- Keep live servers stable before adding features.
- Gate runtime hooks and risky behavior behind explicit env vars plus safe per-instance
  marker files.
- Prefer per-instance enablement under `/servidor/ark/obelisk/state/instances/<id>`.
- Plugin loading requires a non-empty safe `OBELISK_INSTANCE_ID` containing only letters,
  digits, `_`, or `-`; do not weaken this fail-closed guard for shared-cluster installs.
- Keep plugin loading optional via `OBELISK_DISABLE_PLUGINS=1`.
- Never use `OBELISK_ENABLE_NATIVE_EXEC_PROBES=1` plus
  `enable-native-exec-probes` as part of normal runtime validation.
- Do not let plugin exceptions or STL types cross the C ABI boundary.
- Do not subscribe plugins to all `ProcessEvent` calls except during a specifically
  operator-approved debug window on the named debug instance, with bounded limits and a
  rollback plan.
- Global `RegisterPreProcessEvent` and `RegisterPostProcessEvent` callbacks are runtime
  default-deny. They require `OBELISK_ALLOW_GLOBAL_PROCESS_EVENT_CALLBACKS=1` plus the
  safe per-instance marker `allow-global-process-event-callbacks`; filtered callbacks stay
  the stable plugin path.
- Public `CallProcessEvent` is also runtime default-deny. It requires
  `OBELISK_ALLOW_CALL_PROCESS_EVENT=1` plus the safe per-instance marker
  `allow-call-process-event`, and the runtime only advertises
  `OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT` when that gate is active.
- Stable posture must reject ReflectionScanner, broad ProcessEvent tracing
  (`OBELISK_PE_TRACE_LIMIT` non-zero), global callbacks, and public `CallProcessEvent`
  unless an explicit debug-window workflow says otherwise.
- Treat callback ownership as runtime-critical: callbacks registered by a plugin must be
  unregistered if init fails, before unload, and before `dlclose`.
- Reject plugin callback registrations that cannot be attributed to the currently
  initializing plugin or an already-loaded plugin owner. Do not allow ownerless callbacks
  through the public plugin API.
- Owner-token callback registration is the supported path for helper-module or
  background-thread callbacks whose function pointer does not live in the plugin `.so`.
  The runtime accepts owner-token registrations from helper/background threads during
  `ObeliskPlugin_Init` while the plugin owner is in the initializing set, then removes
  owner tokens on init failure and before/with plugin unload.
- For new public ProcessEvent registrations, prefer owner-token handle functions that
  return a non-zero `uint64_t` handle and require
  `UnregisterProcessEventCallbackWithOwnerToken(owner_token, handle)` for granular
  unregister. Do not expose bare unregister-by-id across the plugin ABI.
- Public and internal callback handles or owner tokens must never use `0` as a successful
  value and must not reuse currently-live IDs after counter wrap. `0` remains the failure
  sentinel across plugin-facing registration APIs.
- Keep plugin-owned lifecycle cleanup shared across `EventManager` and the internal
  `ChatEventDispatcher`; future event families must join the same owner cleanup path before
  any public SDK exposure.
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

## Safe Runtime Validation

Current operator direction as of 2026-05-28: users are active on `arkserver` / Ragnarok,
so it is protected from Obelisk restarts, marker changes, and runtime tests. `arkserver2`
/ TheIsland is powered off; if server validation is needed, start it only with explicit
operator approval, keep changes controlled one gate at a time, restore stable posture, and
shut it down when the test window ends.

For risky probes such as ReflectionScanner, native exec, ptrace/gcore, broad tracing, or
text/gameplay-payload logging, first obtain explicit operator approval for the exact
`arkserver2` run, marker changes, restart window, rollback plan, and shutdown at the end.

Validate:

```bash
pgrep -af '^./ShooterGameServer'
tail -n 80 /servidor/ark/obelisk/logs/arkserver/Obelisk.log
rg 'libobelisk|libsubhook' /proc/$(pgrep -f '^./ShooterGameServer Ragnarok' | head -n1)/maps
scripts/check_obelisk_server_posture.sh --expect-stable --forbid-chat-reflection --map Ragnarok --instance arkserver
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
  through tested helpers, and avoid publishing player contents in docs or Discord updates.
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
