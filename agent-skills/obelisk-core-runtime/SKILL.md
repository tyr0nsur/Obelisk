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
- Treat callback ownership as runtime-critical: callbacks registered by a plugin must be
  unregistered if init fails, before unload, and before `dlclose`.
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

Current operator direction as of 2026-05-28: RAM is tight, `arkserver2` / TheIsland should
stay stopped, and `arkserver` / Ragnarok is available as the Obelisk development/test
harness. Keep changes controlled, one gate at a time, and restore stable posture after
runtime validation.

For risky probes such as ReflectionScanner, native exec, ptrace/gcore, broad tracing, or
text/gameplay-payload logging, first obtain explicit operator approval for the exact
`arkserver` run, marker changes, restart window, and rollback plan.

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
