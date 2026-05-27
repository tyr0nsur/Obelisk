# Status Matrix

This matrix separates the stable baseline from experimental work. It is a
contributor-facing summary, not a replacement for detailed research notes.

## Stability Levels

| Level | Meaning | Required before promotion |
| --- | --- | --- |
| Stable baseline | Safe enough for guarded live validation in the documented posture. | Reproducible build, documented flags, and observed live stability. |
| Experimental | Useful for isolated tests or evidence gathering, but not a default live path. | Isolated validation, bounded logs, rollback notes, and research evidence. |
| Not ready | Planned API or behavior without enough evidence for runtime use. | Design, implementation, tests, and safe operational gates. |

## Current Matrix

| Area | Status | Notes |
| --- | --- | --- |
| `LD_PRELOAD` bootstrap | Stable baseline | Runtime loads through the central install layout. |
| Central install root | Stable baseline | `/servidor/ark/obelisk` with `lib/`, `plugins/`, `config/plugins/`, `config/instances/`, `logs/`, and `state/`. |
| LinuxGSM wrapper templates | Stable baseline | Versioned under `packaging/linuxgsm/`; copy to the ARK binary directory during a maintenance window. |
| Installer plugin posture | Stable baseline | `scripts/install_obelisk.sh` installs only runtime libraries; plugins are activated only by copying `.so` files into `plugins/`. |
| Per-map runtime flags | Stable baseline | Marker files gate hooks, plugins, and discovery per server instance. |
| ProcessEvent hook | Stable baseline | Current Ragnarok posture enables the hook while disabling plugins. |
| Plugin C ABI loading | Stable baseline | ABI is C-compatible and currently append-only for new metadata fields. |
| Filtered ProcessEvent callbacks | Stable baseline | Prefer callbacks scoped by `FName` index over global callbacks. |
| Plugin callback ownership | Stable baseline | Callback owner tokens are unregistered on init failure and before plugin unload. |
| Plugin architecture policy | Stable baseline | See `docs/PLUGIN_ARCHITECTURE.md`; examples must stay small and experimental plugins stay out of top-level build. |
| `oBaseEvents` | Stable baseline | First official example plugin; demonstrates ABI validation, config creation, filtered callbacks, and shutdown. |
| ReflectionScanner | Experimental | Use for isolated captures with explicit gates; keep disabled by default. |
| Raw FString/FName inference | Experimental | Evidence gathering only until reflection-backed decoding replaces it. |
| GNames/FNamePool resolution | Not ready | Priority research item. |
| GObjects/GUObjectArray enumeration | Not ready | Validate object shapes in isolation before accepting offsets. |
| Reflected UFunction parameter decoding | Not ready | Required before stable chat command interception. |
| Higher-level SDK APIs | Not ready | Players, tribes, inventory, dinos, permissions, timers, and RCON helpers remain roadmap items. |

## Live Safety Baseline

For Ragnarok live stability, the currently documented posture is:

```text
enable-process-event-hook-ragnarok
disable-plugins-ragnarok
```

Do not enable native exec probes on live servers. Keep experimental plugins in
the repository or another staging location until isolated validation passes.
