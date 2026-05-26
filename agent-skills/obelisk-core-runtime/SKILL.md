---
name: obelisk-core-runtime
description: Use when developing or auditing Obelisk runtime stability: LD_PRELOAD bootstrap, absolute x64 ProcessEvent hook, EventManager, PluginManager, C ABI, logging, install layout, and live-server safety flags.
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
- Prefer per-map enablement under `/servidor/ark/obelisk/state`.
- Keep plugin loading optional via `OBELISK_DISABLE_PLUGINS=1`.
- Do not let plugin exceptions or STL types cross the C ABI boundary.
- Do not subscribe plugins to all `ProcessEvent` calls unless explicitly debugging.
- Treat callback ownership as runtime-critical: callbacks registered by a plugin must be
  unregistered if init fails, before unload, and before `dlclose`.
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

For a live Ragnarok test:

```bash
touch /servidor/ark/obelisk/state/enable-process-event-hook-ragnarok
touch /servidor/ark/obelisk/state/disable-plugins-ragnarok
./arkserver restart
```

Validate:

```bash
pgrep -af '^./ShooterGameServer'
tail -n 80 /servidor/ark/obelisk/logs/Obelisk-Ragnarok.log
rg 'libobelisk|libsubhook' /proc/$(pgrep -f '^./ShooterGameServer Ragnarok' | head -n1)/maps
```

Expected:

- `ProcessEvent absolute x64 hook installed successfully`
- `Plugin loading disabled by OBELISK_DISABLE_PLUGINS=1`
- process remains alive
- players can join

## Runtime Hardening Priorities

- Add plugin-owned callback registration and unregister paths in `EventManager` and
  `PluginManager`.
- Reject or disable plugin callbacks before closing a plugin library.
- Avoid raw callback pointers that can survive `dlclose`.
- Keep global ProcessEvent callbacks off production paths unless a measured debug session
  needs them.
- Add a first-class plugin shutdown export before treating thread-owning or HTTP-owning
  plugins as stable.

## Before Shipping

Run:

```bash
cmake --build build -j"$(nproc)"
git diff --check
```

Never commit built `.so` files, logs, server configs, or runtime state marker files.
