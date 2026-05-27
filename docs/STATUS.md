# Status Matrix

This matrix separates the stable baseline from experimental work. It is a
contributor-facing summary for the Obelisk runtime/API/SDK, not a replacement
for detailed research notes.

The current ARK server setup is the debug harness used to validate Obelisk in a
real UE4 Linux process. Harness operations are documented here only when they
define or protect runtime behavior.

## Stability Levels

| Level | Meaning | Required before promotion |
| --- | --- | --- |
| Stable baseline | Safe enough for guarded debug-harness validation in the documented posture. | Reproducible build, documented flags, and observed harness stability. |
| Experimental | Useful for isolated tests or evidence gathering, but not a default live path. | Isolated validation, bounded logs, rollback notes, and research evidence. |
| Not ready | Planned API or behavior without enough evidence for runtime use. | Design, implementation, tests, and safe operational gates. |

## Current Matrix

| Area | Status | Notes |
| --- | --- | --- |
| `LD_PRELOAD` bootstrap | Stable baseline | Runtime loads through the central install layout. |
| Central install root | Stable baseline | Operator-chosen Obelisk root with `lib/`, `plugins/`, `config/`, `logs/`, and `state/instances/`; current harness uses `/servidor/ark/obelisk`. |
| ARK/LinuxGSM debug harness | Stable baseline | Versioned wrappers live under `packaging/linuxgsm/`; copy to the ARK binary directory only for harness validation. |
| Installer plugin posture | Stable baseline | `scripts/install_obelisk.sh` installs only runtime libraries; plugins are activated only by copying `.so` files into `plugins/`. |
| Per-instance runtime flags | Stable baseline | `OBELISK_INSTANCE_ID` selects logs and markers under `state/instances/<id>/`; map markers are obsolete. |
| ProcessEvent hook | Stable baseline | Current Ragnarok posture enables the hook while disabling plugins. |
| Server posture check | Stable baseline | `scripts/check_obelisk_server_posture.sh --expect-stable` validates the expected env flags, requires a mapped `libobelisk.so`, rejects deleted runtime mappings, and is covered by offline procfs-fixture tests. |
| Plugin C ABI loading | Stable baseline | ABI is C-compatible and currently append-only for new metadata fields. |
| Filtered ProcessEvent callbacks | Stable baseline | Prefer callbacks scoped by `FName` index over global callbacks. |
| Plugin callback ownership | Stable baseline | Callback owner tokens are unregistered on init failure and before plugin unload. |
| Plugin architecture policy | Stable baseline | See `docs/PLUGIN_ARCHITECTURE.md`; examples must stay small and experimental plugins stay out of top-level build. |
| `oBaseEvents` | Release example | First official example plugin; demonstrates ABI validation, config creation, filtered callbacks, and shutdown. |
| ReflectionScanner | Experimental | Use for isolated captures with explicit gates; keep disabled by default. |
| Raw FString/FName inference | Experimental | Evidence gathering only until reflection-backed decoding replaces it. |
| GNames/FNamePool resolution | Not ready | Priority research item. |
| GObjects/GUObjectArray enumeration | Not ready | Validate object shapes in isolation before accepting offsets. |
| Reflected UFunction parameter decoding | Not ready | Required before stable chat command interception. |
| Higher-level SDK APIs | Not ready | Players, tribes, inventory, dinos, permissions, timers, and RCON helpers remain roadmap items. |

## Harness Safety Baseline

For the current Ragnarok ARK harness, the documented debug posture is:

```text
state/instances/arkserver/enable-process-event-hook
state/instances/arkserver/disable-plugins
```

Do not enable native exec probes on debug harness servers. Keep experimental
plugins in the repository or another staging location until isolated validation
passes.

After any scanner/plugin capture or runtime redeploy, run
`scripts/check_obelisk_server_posture.sh --expect-stable` before treating the
harness as stable. The check is read-only and should fail closed rather than
depending on a live experiment to reveal stale runtime state.
