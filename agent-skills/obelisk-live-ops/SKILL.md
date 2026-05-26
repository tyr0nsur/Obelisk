---
name: obelisk-live-ops
description: Use when operating Obelisk on live ARK servers: central install root, arkmanager wrappers, per-map state markers, log symlinks, restart safety, and production experiment gates.
---

# Obelisk Live Ops

Use this skill when touching live server deployment, `/servidor/ark`, arkmanager scripts,
runtime marker files, or operational checks after installing Obelisk.

## Live Layout

Central root:

```text
/servidor/ark/obelisk/
  lib/
  plugins/
  plugins-disabled/
  config/plugins/
  logs/
  state/
```

Only the thin launcher/wrapper should live inside the ARK binary directory. Runtime
libraries, plugin `.so` files, plugin config, logs, and state markers belong under the
central Obelisk root.

Convenience log links may live under:

```text
/home/flowcommunity-ark/logs/ark/
```

## Production Baseline

For Ragnarok live stability:

```bash
touch /servidor/ark/obelisk/state/enable-process-event-hook-ragnarok
touch /servidor/ark/obelisk/state/disable-plugins-ragnarok
./arkserver restart
```

Expected logs:

- runtime loaded through `LD_PRELOAD`
- ProcessEvent hook installed
- plugin loading disabled
- server remains joinable

## Experiment Gates

- Do not activate `ChatPlugin.so` or chat discovery on a production map as the first test.
- Keep experimental plugins in `plugins-disabled/` until an isolated server test passes.
- Enable one marker/config gate at a time and record the exact change.
- Never enable native exec probes on live servers.
- Keep `OBELISK_PE_TRACE_LIMIT=0` by default; use short trace windows only for evidence.

## Operational Checks

Before restart:

```bash
git -C /home/flowcommunity-ark/Obelisk status --short
ls -la /servidor/ark/obelisk/lib /servidor/ark/obelisk/plugins
ls -la /servidor/ark/obelisk/state
```

After restart:

```bash
pgrep -af '^./ShooterGameServer'
tail -n 100 /servidor/ark/obelisk/logs/Obelisk-Ragnarok.log
pid=$(pgrep -f '^./ShooterGameServer Ragnarok' | head -n1)
rg 'libobelisk|libsubhook' /proc/$pid/maps
```

## Rollback

If a live map crashes after an Obelisk change:

```bash
touch /servidor/ark/obelisk/state/disable-plugins-ragnarok
rm -f /servidor/ark/obelisk/state/enable-chat-discovery-ragnarok
./arkserver start
```

Preserve logs and core files before rebuilding or changing markers again.
