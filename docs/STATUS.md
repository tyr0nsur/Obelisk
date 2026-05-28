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
| Multi-server shared root | Stable baseline | Multiple ARK processes may share Obelisk `lib/`, `plugins/`, and `config/` when each process has a unique `OBELISK_INSTANCE_ID`; logs, markers, and mutable runtime state stay per instance. |
| ARK/LinuxGSM validation adapter | Stable baseline | Versioned wrappers live under `packaging/linuxgsm/`; copy to the ARK binary directory only for adapter validation. Use `scripts/check_linuxgsm_wrapper_drift.sh` before maintenance restarts and review `linuxgsm_wrapper_drift_status` in supervisor snapshots. |
| Installer plugin posture | Stable baseline | `scripts/install_obelisk.sh` installs runtime/SDK artifacts; plugins are published with `scripts/install_obelisk_plugin.sh`, which stages under a non-`.so` name before atomic rename into `plugins/`. |
| Operator CLI | Experimental | `scripts/obelisk.py` exposes read-only `status`, `instances list`, `plugins list`, and `plugins show`; lifecycle commands are planned after LinuxGSM integration and explicit restart safety gates. |
| Per-instance runtime flags | Stable baseline | `OBELISK_INSTANCE_ID` selects logs and markers under `state/instances/<id>/`; map markers are obsolete. |
| ProcessEvent hook | Stable baseline | The preferred Ragnarok baseline enables the hook while disabling plugins, but current live posture must be verified from `docs/agent-handoff/CURRENT.md` and `check_obelisk_server_posture.sh` before making claims. |
| Server posture check | Stable baseline | `scripts/check_obelisk_server_posture.sh --expect-stable --map <map> --instance <instance-id>` validates stable env flags, requires central `${OBELISK_ROOT}/lib/libobelisk.so` in `LD_PRELOAD` and maps, requires a safe instance id, a non-symlink marker directory, and the stable per-instance markers, rejects deleted runtime mappings, and fails closed on forbidden per-instance marker entries that would reactivate experimental features at next restart. Covered by offline procfs-fixture tests. `--forbid-chat-reflection` remains a legacy compatibility flag because chat observers are already forbidden by `--expect-stable`. |
| Plugin C ABI loading | Stable baseline | ABI is C-compatible and currently append-only for new metadata fields. |
| Filtered ProcessEvent callbacks | Stable baseline | Prefer callbacks scoped by `FName` index over global callbacks. |
| Plugin callback ownership | Stable baseline | Callback owner tokens are unregistered on init failure and before plugin unload; owner-token handle registration supports helper/background-thread callbacks and explicit owner-scoped unregister without creating ownerless registrations. |
| Plugin architecture policy | Stable baseline | See `docs/PLUGIN_ARCHITECTURE.md`; examples must stay small and experimental plugins stay out of top-level build. |
| `oBaseEvents` | Release example | First official example plugin; demonstrates ABI validation, config creation, filtered callback handles, and shutdown unregister. |
| Game interaction surface | Experimental | Obelisk can already observe selected UE4 `ProcessEvent` calls through filtered callbacks when the target `FName` index is known. Gameplay mutation, return overrides, arbitrary UE4 calls, and public module SDK dispatch remain blocked until reflection-backed parameter decoding, ownership policy, and isolated runtime evidence exist. |
| Internal copied structure events | Experimental | `core/StructureEventDispatcher` is an internal bridge for copied scalar-only structure observations. It has owner cleanup and callback lifetime tests, exposes no borrowed UE pointers, and is not public ABI or plugin SDK yet. |
| ReflectionScanner | Experimental | Use for isolated captures with explicit gates; keep disabled by default. |
| Runtime debug control | Experimental | Marker-triggered post-start probes for short debug windows; stable posture rejects `OBELISK_ENABLE_DEBUG_CONTROL`. |
| Binary-hash-gated module observers | Experimental | Internal observation paths for exact candidate functions; metadata logging is gated by env, supported binary SHA, `OBELISK_WRAPPER_PROFILE=observer-debug`, `allow-observer-debug-window`, `allow-experimental-observers`, and the observer marker on the same instance. There is no plugin dispatch or public ABI yet. Chat is one historical observer in this family, not the center of the SDK. |
| Reflection snapshot tooling | Experimental | Sanitized UFunction and ScriptStruct fixtures, manifest regeneration, and offline comparison support second-source research. Fixtures are candidate-only evidence, not SDK contracts. |
| Raw FString/FName inference | Experimental | Evidence gathering only until reflection-backed decoding replaces it. |
| GNames/FNamePool resolution | Not ready | Priority research item. |
| GObjects/GUObjectArray enumeration | Not ready | Validate object shapes in isolation before accepting offsets. |
| General reflected UFunction parameter decoding | Not ready | Candidate-only module recognizers exist, but SDK-facing decoding remains unpromoted. |
| Higher-level SDK APIs | Not ready | Players, chat, tribes, inventory, items, dinos, structures, missions, transfers, permissions, timers, admin, and commands remain roadmap items. |

## Current Game Interaction Boundary

The first stable line should prove the Linux runtime, hook, plugin ABI, install layout, and
safe observation model before promising gameplay-authoritative behavior.

Current safe interaction shape:

- observe a narrow `ProcessEvent` target by exact `FName` index;
- keep callbacks filtered, non-blocking, and instance-gated;
- record metadata or plugin-local state only;
- restore stable posture after any approved debug-server experiment.

Blocked from stable plugin APIs until promoted with evidence:

- mutating UE4 parameter buffers or return values;
- calling arbitrary UE4 functions or replaying events through `CallProcessEvent`;
- exposing borrowed `UObject`, `FString`, `UFunction`, or raw parameter memory to plugins;
- publishing player, inventory, structure, dino, tribe, transfer, admin, or command APIs.

## Harness Safety Baseline

For the protected Ragnarok performance baseline, the documented stable markers are:

```text
state/instances/arkserver/enable-process-event-hook
state/instances/arkserver/disable-plugins
```

Do not enable native exec probes on validation adapter servers. Keep experimental
plugins in the repository or another staging location until isolated validation
passes.

Current instance posture is tracked in `docs/agent-handoff/CURRENT.md`. Do not restart,
change markers, or run Obelisk tests on shared or player-facing instances without explicit
operator approval for the target, rollback plan, and shutdown expectations. For `gcore`,
`ptrace`, ReflectionScanner, broad tracing, or scanner-like probes, use only a specifically
approved debug/development run window with rollback.

After any scanner/plugin capture or runtime redeploy on an approved debug target, run
`scripts/check_obelisk_server_posture.sh --expect-stable --map <map> --instance
<instance-id>` before treating the harness as stable. The check is read-only and should
fail closed rather than depending on a live experiment to reveal stale runtime state.
