# Compact Context Snapshot

Updated: 2026-05-27

Use this file when conversation context is compacted or an agent needs to resume Obelisk
work from repository state instead of chat history.

## Current Repo State

- Repo: `/home/flowcommunity-ark/Obelisk`
- Remote: `git@github.com:tyr0nsur/Obelisk.git`
- Current known good commit: `8d3da3c Add plugin shutdown and scanner audit tooling`
- Local ignored artifacts normally present: `build/`, `Obelisk.log`
- Do not commit built `.so` files, logs, server config, core dumps, or state markers.

## Production Server State

- ARK root: `/servidor/ark`
- Central Obelisk root: `/servidor/ark/obelisk`
- Ragnarok stable live posture:
  - `/servidor/ark/obelisk/state/enable-process-event-hook-ragnarok`
  - `/servidor/ark/obelisk/state/disable-plugins-ragnarok`
- Treat both observed ARK instances as live/non-isolated until the operator explicitly says
  otherwise:
  - `arkserver` / Ragnarok
  - `arkserver2` / TheIsland
- Do not restart servers, edit marker files, change `/servidor/ark`, or activate
  ReflectionScanner without explicit operator permission and an isolated/debug instance.

## What Is Stable Enough

- LD_PRELOAD runtime bootstrap.
- Central install layout under `/servidor/ark/obelisk`.
- Absolute x64 ProcessEvent hook with executable range and known prologue validation.
- C ABI plugin loading.
- Plugin-owned callback cleanup on init failure and unload.
- Optional plugin export: `extern "C" void ObeliskPlugin_Shutdown()`.
- `helloworld_plugin` builds as the minimal plugin example.

## What Is Experimental Or Blocked

- `ChatPlugin` remains experimental and unsafe as a production chat API.
- `MonitorPlugin` remains experimental and intentionally excluded from top-level stable
  build; it needs lifecycle, HTTP security, config, and callback redesign.
- ReflectionScanner is experimental and must stay disabled on live servers.
- No confirmed isolated/debug ARK instance exists right now.
- `GNames`, `GObjects`, `UFunction` metadata, and reflected parameter decoding are not
  solved yet.

## Current Research Direction

Next technical milestone is `FName -> string` resolution:

1. Run `ReflectionScanner` only on a confirmed isolated/debug instance.
2. Use `docs/research/2026-05-27-reflectionscanner-isolated-capture-runbook.md`.
3. Analyze copied logs with:

```bash
python3 scripts/analyze_reflectionscanner_capture.py /path/to/isolated/Obelisk.log
python3 scripts/analyze_reflectionscanner_capture.py --json /path/to/isolated/Obelisk.log
```

4. Treat `GNames` only as a research candidate when `matched_clues=3/3` repeats for the
   same table pointer and there are no reject markers.
5. Before committing offsets, require a second isolated capture or static xref validation.

## Hard Rules

- Never enable `OBELISK_ENABLE_NATIVE_EXEC_PROBES=1` on live servers.
- Never enable ChatPlugin discovery on live Ragnarok as a normal test.
- Do not treat observed FName indices such as `9619` or `9622` as stable API contracts.
- Do not promote plugins with HTTP, threads, or file readers until they implement and
  validate `ObeliskPlugin_Shutdown()`.
- Global ProcessEvent callbacks are debug-only unless documented and measured.

## Key Files To Read First

- `docs/agent-handoff/CURRENT.md`
- `docs/STATUS.md`
- `docs/PLUGIN_ARCHITECTURE.md`
- `docs/research/README.md`
- `agent-skills/obelisk-agent-handoff/SKILL.md`
- `agent-skills/obelisk-continuous-learning/SKILL.md`
- subsystem-specific skill under `agent-skills/`

## Next Good Rounds

- Ops: design/create a truly isolated ARK debug instance plan without touching live servers.
- Reflection: improve FName/GNames probes and analyzer fixtures offline.
- Runtime: add tests/harness for plugin shutdown order and callback cleanup.
- Build/QA: add lightweight offline tests for scripts/analyzer and ABI layout assumptions.
