# Status Matrix

This matrix separates the stable baseline from experimental work. It is a
contributor-facing summary for the Obelisk runtime/API/SDK, not a replacement
for detailed research notes.

Current development line is `0.1.0-dev`; see [VERSIONING.md](VERSIONING.md). This is not
a production-stable release claim.

The current ARK server setup is a validation adapter used to check Obelisk in a
real UE4 Linux process. Adapter operations are documented here only when they
define or protect runtime behavior.

## Stability Levels

| Level | Meaning | Required before promotion |
| --- | --- | --- |
| Stable baseline | Safe enough for guarded validation-adapter checks in the documented posture. | Reproducible build, documented flags, and observed adapter stability. |
| Experimental | Useful for isolated tests or evidence gathering, but not a default live path. | Isolated validation, bounded logs, rollback notes, and research evidence. |
| Not ready | Planned API or behavior without enough evidence for runtime use. | Design, implementation, tests, and safe operational gates. |

## Current Matrix

| Area | Status | Notes |
| --- | --- | --- |
| `LD_PRELOAD` bootstrap | Stable baseline | Runtime loads through the central install layout. |
| Central install root | Stable baseline | Operator-chosen Obelisk root with `lib/`, `plugins/`, `config/`, `logs/`, and `state/instances/`; current harness uses `/servidor/ark/obelisk`. |
| ARK/LinuxGSM validation adapter | Stable baseline | Versioned wrappers live under `packaging/linuxgsm/`; copy to the ARK binary directory only for adapter validation. |
| Installer plugin posture | Stable baseline | `scripts/install_obelisk.sh` installs only runtime libraries; plugins are activated only by copying `.so` files into `plugins/`. |
| Per-instance runtime flags | Stable baseline | `OBELISK_INSTANCE_ID` selects logs and markers under `state/instances/<id>/`; map markers are obsolete. |
| ProcessEvent hook | Stable baseline | Current Ragnarok posture enables the hook while disabling plugins. |
| Server posture check | Stable baseline | `scripts/check_obelisk_server_posture.sh --expect-stable --map <map> --instance <instance-id>` validates stable debug env flags, requires a mapped `libobelisk.so`, rejects deleted runtime mappings, and is covered by offline procfs-fixture tests. Use explicit `--map`/`--instance`; add `--forbid-chat-reflection` for production/performance posture where chat reflection and text logging must be off. |
| Plugin C ABI loading | Stable baseline | ABI is C-compatible and currently append-only for new metadata fields. |
| Filtered ProcessEvent callbacks | Stable baseline | Prefer callbacks scoped by `FName` index over global callbacks. |
| Plugin callback ownership | Stable baseline | Callback owner tokens are unregistered on init failure and before plugin unload. |
| Plugin architecture policy | Stable baseline | See `docs/PLUGIN_ARCHITECTURE.md`; examples must stay small and experimental plugins stay out of top-level build. |
| `oBaseEvents` | Release example | First official example plugin; demonstrates ABI validation, config creation, filtered callbacks, and shutdown. |
| ReflectionScanner | Experimental | Use for isolated captures with explicit gates; keep disabled by default. |
| Runtime debug control | Experimental | Marker-triggered post-start probes for short debug windows; stable posture rejects `OBELISK_ENABLE_DEBUG_CONTROL`. |
| Binary-hash-gated module observers | Experimental | Internal observation paths for exact candidate functions; metadata logging is gated and there is no plugin dispatch or public ABI yet. Chat is one historical observer in this family, not the center of the SDK. |
| Reflection snapshot tooling | Experimental | Sanitized UFunction and ScriptStruct fixtures, manifest regeneration, and offline comparison support second-source research. Fixtures are candidate-only evidence, not SDK contracts. |
| Raw FString/FName inference | Experimental | Evidence gathering only until reflection-backed decoding replaces it. |
| GNames/FNamePool resolution | Not ready | Priority research item. |
| GObjects/GUObjectArray enumeration | Not ready | Validate object shapes in isolation before accepting offsets. |
| General reflected UFunction parameter decoding | Not ready | Candidate-only module recognizers exist, but SDK-facing decoding remains unpromoted. |
| Higher-level SDK APIs | Not ready | Players, chat, tribes, inventory, items, dinos, structures, missions, transfers, permissions, timers, admin, and commands remain roadmap items. |

## Harness Safety Baseline

For the current protected Ragnarok performance posture, the documented stable markers are:

```text
state/instances/arkserver/enable-process-event-hook
state/instances/arkserver/disable-plugins
```

Do not enable native exec probes on validation adapter servers. Keep experimental
plugins in the repository or another staging location until isolated validation
passes.

While Ragnarok is under player performance testing, use `arkserver-obelisk-debug` as the
normal Obelisk debug/development harness instead of changing Ragnarok markers or
restarting it. Use `arkserver2` / TheIsland only during an explicitly approved debug
window for the named instance and rollback plan. For `gcore`, `ptrace`, ReflectionScanner,
broad tracing, or scanner-like probes, keep preferring `arkserver-obelisk-debug`.

After any scanner/plugin capture or runtime redeploy on an approved debug target, run
`scripts/check_obelisk_server_posture.sh --expect-stable --map <map> --instance
<instance-id>` before treating the harness as stable. The check is read-only and should
fail closed rather than depending on a live experiment to reveal stale runtime state.

For Ragnarok player performance posture, add `--forbid-chat-reflection` so the same
read-only check also rejects experimental chat reflection and chat text logging env.
