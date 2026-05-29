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
| Central install root | Stable baseline | Operator-chosen Obelisk root with `lib/`, `plugins/`, `config/`, `logs/`, and `state/instances/`; examples should use placeholders such as `<obelisk-root>`. |
| Multi-server shared root | Stable baseline | Multiple ARK processes may share Obelisk `lib/`, `plugins/`, and `config/` when each process has a unique `OBELISK_INSTANCE_ID`; logs, markers, and mutable runtime state stay per instance. |
| ARK/LinuxGSM validation adapter | Stable baseline | Versioned wrappers live under `packaging/linuxgsm/`; copy to the ARK binary directory only for adapter validation. Use `scripts/check_linuxgsm_wrapper_drift.sh` before maintenance restarts and review `linuxgsm_wrapper_drift_status` in operator posture reports. |
| Installer plugin posture | Stable baseline | `scripts/install_obelisk.sh` installs runtime/SDK artifacts; plugins are published with `scripts/install_obelisk_plugin.sh`, which stages under a non-`.so` name before atomic rename into `plugins/`. |
| Operator CLI | Experimental | `scripts/obelisk.py` exposes read-only `status`, `instances list`, `plugins list`, and `plugins show`; lifecycle commands are planned after LinuxGSM integration and explicit restart safety gates. |
| Per-instance runtime flags | Stable baseline | `OBELISK_INSTANCE_ID` selects logs and markers under `state/instances/<id>/`; map markers are obsolete. |
| ProcessEvent hook | Stable baseline | Stable validation enables the hook while disabling plugins; live posture must be verified with `check_obelisk_server_posture.sh` before making claims. |
| Server posture check | Stable baseline | `scripts/check_obelisk_server_posture.sh --expect-stable --map <map> --instance <instance-id>` validates stable env flags, requires central `${OBELISK_ROOT}/lib/libobelisk.so` in `LD_PRELOAD` and maps, requires a safe instance id, a non-symlink marker directory, and the stable per-instance markers, rejects deleted runtime mappings, and fails closed on forbidden per-instance marker entries that would reactivate experimental features at next restart. Covered by offline procfs-fixture tests. `--forbid-chat-reflection` remains a legacy compatibility flag because chat observers are already forbidden by `--expect-stable`. |
| Plugin C ABI loading | Stable baseline | ABI is C-compatible and currently append-only for new metadata fields; `v0.1.0` freezes the current `ObeliskApi` ABI v1 layout, and any ABI v2 requires an explicit migration plan. |
| Filtered ProcessEvent callbacks | Stable baseline | Prefer callbacks scoped by `FName` index over global callbacks. |
| Plugin callback ownership | Stable baseline | Callback owner tokens are unregistered on init failure and before plugin unload; owner-token handle registration supports helper/background-thread callbacks and explicit owner-scoped unregister without creating ownerless registrations. |
| Plugin architecture policy | Stable baseline | See `docs/PLUGIN_ARCHITECTURE.md`; examples must stay small and experimental plugins stay out of top-level build. Plugins with background workers, sockets, HTTP, long-lived file readers, or other external ingress are experimental until they pass a promotion gate for idempotent shutdown, owner-token unregister, queue drain, thread join, socket/file close, and no detached workers or persisted runtime handles. |
| `oBaseEvents` | Release example | First official example plugin; demonstrates ABI validation, config creation, filtered callback handles, and shutdown unregister. |
| Game interaction surface | Experimental | Obelisk can already observe selected UE4 `ProcessEvent` calls through filtered callbacks when the target `FName` index is known. Outside the promoted copied-POD `GameplayPolicyEvent` surface, gameplay mutation, return overrides, arbitrary UE4 calls, and public module SDK dispatch remain blocked until reflection-backed parameter decoding, ownership policy, and isolated runtime evidence exist. |
| GameplayPolicyEvent | Promoted v0.1 SDK surface | Public copied POD policy event backed by accepted `structure-observer-intake` evidence plus accepted compact inventory/structure layouts from `minimal-second-source-intake`. Plugins use owner-token handle registration, event-kind masks, and owner-scoped unregister. Payloads expose only approved scalar fields through `field_mask`, `bool_values`, and `int32_values`; pincode values, player identity, object/item/inventory identity, raw params, FName/GObjects indices, UE pointers, mutation, and return overrides remain blocked. Inventory-backed signals use the same `GameplayPolicyEvent` family, not a separate Inventory SDK. |
| Resource kind descriptors | Promoted v0.1 SDK metadata | `DescribeResourceKind` exposes metadata-only category descriptors for known resource kinds, currently `STRUCTURE` and `INVENTORY_ITEM`: stable category name, supported `GameplayPolicyEvent` masks, supported field masks, and explicit flags that the category has no identity or lookup. It is not a `ResourceHandle`, object identity, lookup API, persistent handle, or proof that two events refer to the same game object. |
| Resources API | Not ready | Real resource identity, lookup, mutation, coordinates, ownership, and cross-event correlation remain postponed until identity stability, privacy, lifecycle, and cross-instance semantics are proven. |
| Internal copied structure events | Internal bridge | `core/StructureEventDispatcher` remains the internal copied-scalar bridge that feeds `GameplayPolicyEvent` and participates in plugin-owner cleanup on init failure/unload. It is not a public `StructureEvents` SDK. |
| Internal copied inventory policy events | Internal bridge | `core/InventoryPolicyEventDispatcher` remains an internal copied-scalar bridge for inventory policy observation and feeds inventory-backed `GameplayPolicyEvent` dispatch. It is not a public Inventory SDK, public callback ABI, capability bit, mutation surface, return override, or resource identity API. |
| ReflectionScanner | Experimental | Use for isolated captures with explicit gates; keep disabled by default. |
| Runtime debug control | Experimental | Marker-triggered post-start probes for short debug windows; stable posture rejects `OBELISK_ENABLE_DEBUG_CONTROL`. |
| Binary-hash-gated module observers | Experimental | Internal observation paths for exact candidate functions; metadata logging is gated by env, supported binary SHA, `OBELISK_WRAPPER_PROFILE=observer-debug`, `allow-observer-debug-window`, `allow-experimental-observers`, and the observer marker on the same instance. Outside the promoted `GameplayPolicyEvent` bridge, module observers have no plugin dispatch or public ABI yet. Chat is one historical observer in this family, not the center of the SDK. |
| Reflection snapshot tooling | Experimental | Sanitized UFunction and ScriptStruct fixtures, manifest regeneration, dry-run UFunction target-set regeneration planning, and offline comparison support second-source research. Named target sets support isolated second-source research and promotion review; they are not part of the default core-first release gate unless a release or PR names them explicitly. Fixtures and plans are candidate-only evidence, not SDK contracts. |
| Raw FString/FName inference | Experimental | Evidence gathering only until reflection-backed decoding replaces it. |
| GNames/FNamePool resolution | Not ready | Priority research item. |
| GObjects/GUObjectArray enumeration | Not ready | Validate object shapes in isolation before accepting offsets. |
| General reflected UFunction parameter decoding | Not ready | Candidate-only module recognizers exist, but SDK-facing decoding remains unpromoted. |
| Higher-level SDK APIs | Not ready | Outside the first promoted `GameplayPolicyEvent` surface, Inventory, players, chat, tribes, dinos, missions, transfers, permissions, timers, admin, commands, and public `StructureEvents` remain roadmap items until each has copied payloads, ABI tests, privacy policy, and accepted target-set evidence. |

## Current Game Interaction Boundary

The first stable line should prove the Linux runtime, hook, plugin ABI, install layout, and
safe observation model before promising gameplay-authoritative behavior.

Current safe interaction shape:

- observe a narrow `ProcessEvent` target by exact `FName` index;
- keep callbacks filtered, non-blocking, and instance-gated;
- record metadata or plugin-local state only;
- consume `GameplayPolicyEvent` as copied POD policy data, including inventory-backed
  policy signals, without identity, lookup, mutation, return override, or UE internals;
- restore stable posture after any approved debug-server experiment.

Blocked from stable plugin APIs until promoted with evidence:

- mutating UE4 parameter buffers or return values;
- blocking the original `ProcessEvent` from plugin callbacks except in an explicit
  debug/experimental gate;
- calling arbitrary UE4 functions or replaying events through `CallProcessEvent`;
- exposing borrowed `UObject`, `FString`, `UFunction`, or raw parameter memory to plugins;
- publishing gameplay module APIs for players, chat, tribes, buffs, inventory, items,
  dinos, structures, missions, transfers, permissions, timers, admin, or commands.

## Harness Safety Baseline

For any shared or player-facing validation adapter, the documented stable markers are:

```text
state/instances/<instance-id>/enable-process-event-hook
state/instances/<instance-id>/disable-plugins
```

Do not enable native exec probes on validation adapter servers. Keep experimental
plugins in the repository or another staging location until isolated validation
passes.

Do not restart, change markers, or run Obelisk tests on shared or player-facing instances
without explicit operator approval for the target, rollback plan, and shutdown
expectations. For `gcore`, `ptrace`, ReflectionScanner, broad tracing, or scanner-like
probes, use only a specifically approved debug/development run window with rollback.

After any scanner/plugin capture or runtime redeploy on an approved debug target, run
`scripts/check_obelisk_server_posture.sh --expect-stable --map <map> --instance
<instance-id>` before treating the harness as stable. The check is read-only and should
fail closed rather than depending on a live experiment to reveal stale runtime state.
