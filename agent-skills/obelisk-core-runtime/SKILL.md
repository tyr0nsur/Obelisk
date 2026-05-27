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
- Gate risky behavior behind explicit env vars or marker files.
- Prefer per-instance enablement under `/servidor/ark/obelisk/state/instances/<id>`.
- Keep plugin loading optional via `OBELISK_DISABLE_PLUGINS=1`.
- Never use `OBELISK_ENABLE_NATIVE_EXEC_PROBES=1` as part of normal runtime validation.
- Do not let plugin exceptions or STL types cross the C ABI boundary.
- Do not subscribe plugins to all `ProcessEvent` calls unless explicitly debugging.
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

Ragnarok is currently reserved for player performance testing. Do not restart it, change
markers, deploy runtime, or increase logging unless the operator opens a maintenance
window.

For TheIsland debug/development validation:

```bash
mkdir -p /servidor/ark/obelisk/state/instances/arkserver2
touch /servidor/ark/obelisk/state/instances/arkserver2/enable-process-event-hook
touch /servidor/ark/obelisk/state/instances/arkserver2/disable-plugins
./arkserver2 restart
```

Validate:

```bash
pgrep -af '^./ShooterGameServer'
tail -n 80 /servidor/ark/obelisk/logs/arkserver2/Obelisk.log
rg 'libobelisk|libsubhook' /proc/$(pgrep -f '^./ShooterGameServer TheIsland' | head -n1)/maps
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
- Keep global ProcessEvent callbacks off production paths unless a measured debug session
  needs them.
- Keep hook-side experimental chat reflection cheap while it remains internal:
  disabled, non-chat, and `OBELISK_CHAT_REFLECTION_LOG_LIMIT=0` paths must stay
  allocation-free in `chat_reflection_benchmark`; matched metadata-only
  `ServerSendChatMessage` should also remain allocation-free unless a research note
  justifies the regression. Hook-like text logging should stay at one allocation or lower.
- Any text logging work must keep `OBELISK_CHAT_REFLECTION_LOG_TEXT=1` as a separate gate,
  sanitize output through the tested `ProcessEventChatReflection` helper, and avoid
  publishing player chat contents in docs or Discord updates.
- Require a validated, idempotent plugin shutdown export before treating thread-owning or
  HTTP-owning plugins as stable.

## Before Shipping

Run:

```bash
cmake --build build -j"$(nproc)"
git diff --check
```

For chat reflection hot-path work also run:

```bash
cmake --build build --target chat_reflection_benchmark
./build/chat_reflection_benchmark 20000 > /tmp/obelisk-chat-reflection-benchmark.txt
python3 scripts/check_chat_reflection_benchmark.py /tmp/obelisk-chat-reflection-benchmark.txt
```

Never commit built `.so` files, logs, server configs, or runtime state marker files.
