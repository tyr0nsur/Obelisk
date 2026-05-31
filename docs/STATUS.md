# Status Matrix

This matrix separates the stable baseline from experimental work. It is a
contributor-facing summary for the Obelisk runtime/API/SDK, not a replacement
for detailed research notes.

Current published release-candidate baseline is core-first `v0.1.0-rc.2` at `1a7cd98`; see
[VERSIONING.md](VERSIONING.md). This is not a production-stable `v1.0` release claim.

Current RC validation checkpoint as of 2026-05-30: the published `v0.1.0-rc.2` tag was
checked against the intended release ref with exact tag/ref verification after the
canonical release gate, including refreshed second-source readiness for the documented RC
target sets. This was a clean release gate for the intended ref. See
[`2026-05-30-head-rc-second-source-refresh-gap.md`](research/2026-05-30-head-rc-second-source-refresh-gap.md)
for the refreshed RC evidence root and gate result. RC public scope remains limited to
`GameplayPolicyEvent`, the minimal copied `ChatMessageEvent`, `DescribeResourceKind`, and
`DescribeGameplayPolicyEventKind`. It does not promote a public Inventory/Items SDK,
`ResourceHandle`, identity, lookup, mutation, return override, or live-server claim.
`v0.1.0-rc.2` also includes process-local owner-token timers as core runtime API without
promoting gameplay/module timers.
Post-RC development continues toward the broader `v1.0` core-stability track: general
reflection evidence, copied-data module APIs, operator lifecycle safety, metadata-only
reference plugins such as `oDescriptorCatalog`, and ArkApi-demand-informed
Obelisk-native plugin replacement capacity without copying or porting ArkApi/NextGen
implementations or retroactively expanding the published RC tag.

The intended `v1.0` stable milestone is a complete Obelisk SDK milestone, not just a
stable loader/runtime milestone. `v1.0` should give plugin authors a coherent Linux-native
SDK for common ARK server modding categories with documented ABI, examples, lifecycle
rules, copied payload ownership, privacy boundaries, installed-SDK validation, and
promotion evidence for each public surface. Until those gates are met, individual core
primitives such as timers, descriptors, copied chat notifications, or copied policy events
remain useful foundations rather than a complete SDK claim.

Scope terms used here:

- published RC baseline: the frozen `v0.1.0-rc.2` tag and its public contract;
- current post-RC candidate: `HEAD` work that still needs a fresh clean release gate before
  publication;
- Plugin Hub seed: narrow examples that consume only existing ABI surfaces, start from
  `docs/PLUGIN_HUB_FOUNDATION_V1.md` plus `docs/PLUGIN_HUB_CAPABILITY_MATRIX.md`, and do
  not gain new support tier or public SDK scope merely by being installed as a plugin `.so`;
- planning-only lane: guidance/demand work that is not release evidence or public SDK
  surface.

Contributor reading guide:

- use the matrix below for current public SDK status;
- use `docs/RELEASE.md` only when preparing or auditing a release candidate;
- use `docs/research/` for evidence trails, rejected hypotheses, and promotion blockers;
- keep operator deployment details outside public SDK docs unless they define a stable
  runtime contract.

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
| ARK/LinuxGSM validation adapter | Stable baseline | Versioned wrappers live under `packaging/linuxgsm/`; copying or deploying them into an ARK binary directory requires a current approved adapter-validation window with rollback. Use `scripts/check_linuxgsm_wrapper_drift.sh` before maintenance restarts. |
| Installer plugin posture | Stable baseline | `scripts/install_obelisk.sh` installs runtime/SDK artifacts; plugins are published with `scripts/install_obelisk_plugin.sh`, which stages under a non-`.so` name before atomic rename into `plugins/`. |
| Operator CLI | Experimental | `scripts/obelisk.py` exposes read-only `status`, `instances list`, `plugins list`, and `plugins show`; lifecycle commands are planned after LinuxGSM integration and explicit restart safety gates. |
| Per-instance runtime flags | Stable baseline | `OBELISK_INSTANCE_ID` selects logs and markers under `state/instances/<id>/`; map markers are obsolete. |
| ProcessEvent hook | Stable baseline | Stable validation enables the hook while plugin loading is disabled through `OBELISK_DISABLE_PLUGINS=1`; live posture must be verified with `check_obelisk_server_posture.sh` before making claims. |
| Server posture check | Stable baseline | `scripts/check_obelisk_server_posture.sh --expect-stable --map <map> --instance <instance-id>` validates stable env flags, central runtime mapping, safe instance id, non-symlink marker roots, and absence of forbidden experimental markers. Covered by offline procfs-fixture tests. |
| Plugin C ABI loading | Stable baseline | ABI is C-compatible and currently append-only for new metadata fields; the first stable `v0.1.0` line freezes the current `ObeliskApi` ABI v1 layout, and any ABI v2 requires an explicit migration plan. ABI guardrails include layout validation, in-tree and installed SDK consumer checks, capability-snapshot tests for owner-token public registrations, and the canonical release gate rejecting production `libobelisk.so` builds that expose test-only/internal symbol patterns. |
| Filtered ProcessEvent callbacks | Debug-gated raw ABI | Runtime infrastructure only: callbacks scoped by `FName` index still receive borrowed UE pointers and raw params, so they are rejected unless `OBELISK_ALLOW_FILTERED_PROCESS_EVENT_CALLBACKS=1` and `allow-filtered-process-event-callbacks` are active. This is not public module dispatch, gameplay mutation, return override, or a stable parameter API. |
| Plugin callback ownership | Stable baseline | Callback owner tokens are unregistered on init failure and before plugin unload; owner-token handle registration supports helper/background-thread callbacks and explicit owner-scoped unregister without creating ownerless registrations. Owner-token callback registration uses the plugin owner's init-time capability snapshot, so later manager construction cannot widen an already-loaded plugin. Unregister/owner cleanup initiated from gameplay callbacks avoids dispatcher cleanup waits to prevent callback-to-callback deadlocks, while non-callback owner/plugin cleanup still waits for in-flight dispatch and deferred `DestroyUserData` cleanup. If unload callback cleanup fails, the runtime skips `dlclose`, retains the plugin for retry, and does not repeat plugin shutdown on the retry. |
| Process-local timers | Promoted v0.1 core primitive | Append-only core scheduler with owner-token one-shot/repeating callbacks, process-local handles, explicit unregister, exception containment, and owner cleanup on init failure/unload. This is not a UE/gameplay timer, persistent cluster state, object identity, command API, or permission API. `oProcessTimer` is the first-party release example. |
| Plugin architecture policy | Stable baseline | See `docs/PLUGIN_ARCHITECTURE.md`; examples must stay small and experimental plugins stay out of top-level build. Plugins with background workers, sockets, HTTP, long-lived file readers, or other external ingress are experimental until they pass a promotion gate for idempotent shutdown, owner-token unregister, queue drain, thread join, socket/file close, and no detached workers or persisted runtime handles. |
| `oBaseEvents` | Release example | First official example plugin; demonstrates ABI validation, config creation, debug-gated filtered callback handle lifecycle, and shutdown unregister. It is not gameplay dispatch or a stable parameter API. |
| `oDescriptorCatalog` | Post-RC release example | Metadata-only descriptor discovery example over `DescribeResourceKind` and `DescribeGameplayPolicyEventKind`; validates routing metadata without callbacks, timers, identity, lookup, mutation, return override, chat, or raw `ProcessEvent`. Added after the frozen `v0.1.0-rc.2` tag. |
| `oPolicyAudit` | Experimental | First-party `GameplayPolicyEvent` audit example excluded from the default build and release scope unless `OBELISK_BUILD_EXPERIMENTAL_PLUGINS=ON`; not published by `scripts/check_release_readiness.sh`. |
| `oChatLogger` | Experimental | First-party `ChatMessageEvent` smoke-test example excluded from the default build and release scope unless `OBELISK_BUILD_EXPERIMENTAL_PLUGINS=ON`; safe-disabled by default, requires active config before chat registration, and logs event metadata plus copied message size only, not player identity or raw chat text. |
| `oChatAudit` | Experimental | First-party `ChatMessageEvent` digest/audit example excluded from the default build and release scope unless `OBELISK_BUILD_EXPERIMENTAL_PLUGINS=ON`; safe-disabled by default and never logs raw chat text or player identity. |
| Game interaction surface | Experimental | Obelisk can observe selected UE4 `ProcessEvent` calls through debug-gated filtered callbacks when the target `FName` index is known. Outside the promoted `GameplayPolicyEvent` surface and the minimal `ChatMessageEvent` RC notification surface, gameplay mutation, return overrides, arbitrary UE4 calls, and public module SDK dispatch remain blocked until reflection-backed parameter decoding, ownership policy, and isolated runtime evidence exist. |
| GameplayPolicyEvent | Promoted v0.1 SDK surface | Public copied POD policy event backed by accepted `structure-observer-intake` evidence, accepted ReturnValue-only `item-return-only-policy-slice` evidence, plus accepted compact inventory/structure layouts from `minimal-second-source-intake`; the structure-backed claim points to fresh [`structure-observer-intake` evidence](research/2026-05-29-structure-observer-intake-refresh.md) and remains layout-only support for copied/redacted policy backing. Plugins use owner-token handle registration, event-kind masks, and owner-scoped unregister. Payloads expose only approved scalar fields through `field_mask`, `bool_values`, and `int32_values`; pincode values, player identity, object/item/inventory identity, lookup, `ResourceHandle`, raw params, FName/GObjects indices, UE pointers, mutation, and return overrides remain blocked. Inventory-backed signals use the same `GameplayPolicyEvent` family, not a separate Inventory SDK. |
| ChatMessageEvent | v0.1-rc SDK ABI surface | Minimal copied UTF-8 chat notification contract for plugins that parse text locally. Plugins use owner-token handle registration and owner-scoped unregister. Payloads expose `send_mode`, copied-payload flags, a process-local sequence, and message bytes only; sender/player identity, resource identity, raw `FString`, raw params, FName/GObjects indices, UE pointers, chat send/moderation/blocking, command routing, mutation, and return overrides remain blocked. The target layout has accepted second-source evidence, and the `enable-chat-events` producer path has approved copied-log plugin-facing delivery validation with 18 accepted events covering all four known send modes (`0..3`) and no privacy blockers. Historical `enable-chat-reflection` observer logs still do not satisfy delivery evidence. |
| Resource kind descriptors | Promoted v0.1 SDK metadata | `DescribeResourceKind` exposes metadata-only category descriptors for known resource kinds, currently `STRUCTURE` and `INVENTORY_ITEM`: stable category name, supported `GameplayPolicyEvent` masks, supported field masks, and explicit flags that the category has no identity or lookup. It is not a `ResourceHandle`, object identity, lookup API, persistent handle, or proof that two events refer to the same game object. |
| Gameplay policy event descriptors | Promoted v0.1 SDK metadata | `DescribeGameplayPolicyEventKind` exposes metadata-only descriptors for promoted `GameplayPolicyEvent` kinds: stable event name, resource category, event-kind mask, supported field mask, and copied-payload/backing flags. It is metadata for promoted kinds only, not a complete gameplay inventory, separate module SDK, object identity, UE lookup, mutation path, or return-override API. |
| Resources API | Not ready | Real resource identity, lookup, mutation, coordinates, ownership, and cross-event correlation remain postponed until identity stability, privacy, lifecycle, validity, and cross-instance semantics are proven. Current ResourceHandle semantic work remains blocked until helper predicates, caller mode, mutation windows, rejected-object samples, strict serial reuse/wraparound policy, and a fail-closed lookup contract pass promotion gates. The first strict serial-policy artifacts are internal candidate-only contracts; they do not prove runtime reuse semantics, public lookup safety, persistent handles, identity, mutation, or return overrides. |
| Internal copied structure events | Internal bridge | `core/StructureEventDispatcher` remains the internal copied-scalar bridge that feeds `GameplayPolicyEvent` and participates in plugin-owner cleanup on init failure/unload. It is not a public `StructureEvents` SDK. |
| Internal copied inventory policy events | Internal bridge | `core/InventoryPolicyEventDispatcher` remains an internal copied-scalar bridge for inventory policy observation and feeds inventory-backed `GameplayPolicyEvent` dispatch. It is not a public Inventory SDK, public callback ABI, capability bit, mutation surface, return override, or resource identity API. |
| ReflectionScanner | Experimental | Use for isolated captures with explicit gates; keep disabled by default. |
| Runtime debug control | Experimental | Marker-triggered post-start probes for short debug windows; stable posture rejects `OBELISK_ENABLE_DEBUG_CONTROL`. |
| Binary-hash-gated module observers | Experimental | Internal observation paths for exact candidate functions; metadata logging is gated by env, supported binary SHA, `OBELISK_WRAPPER_PROFILE=observer-debug`, `allow-observer-debug-window`, `allow-experimental-observers`, and the observer marker on the same instance. Outside the promoted `GameplayPolicyEvent` bridge, module observers have no plugin dispatch or public ABI yet. Chat is one historical observer in this family, not the center of the SDK. |
| Reflection snapshot tooling | Experimental | Sanitized UFunction and ScriptStruct fixtures, manifest regeneration, focal/batch snapshot command planning, dry-run UFunction target-set regeneration planning, and offline comparison support second-source research. Focal/batch snapshot plans are pre-target-set, candidate-only command plans from reviewed offline inputs; they are not snapshot extraction, command execution, layout acceptance, runtime approval, or SDK promotion. The public RC default UFunction target sets are `minimal-second-source-intake`, `structure-observer-intake`, `item-return-only-policy-slice`, and `chat-message-intake`; additional named target sets support isolated second-source research and promotion review only when a release or PR names them explicitly. When second-source readiness is required, `scripts/check_release_readiness.sh` preflights the configured UFunction root before build/test/install work so missing roots, stale or incomplete artifact identity, missing current `BoolProperty` tail metadata, and ambiguous RC target coverage fail closed. The refreshed default `minimal-second-source-intake` evidence remains layout-only with `promotion_ready=false`; accepted transfer evidence for `transfer-ufunction-intake` and `transfer-scriptstruct` is also layout-only/offline and does not promote a public Transfer SDK, payload decoding, object identity, runtime hooks, mutation, return overrides, or `ResourceHandle`. Fixtures, redacted signatures, and plans are candidate-only evidence, not SDK contracts. |
| Raw FString/FName inference | Experimental | Evidence gathering only until reflection-backed decoding replaces it. |
| GNames/FNamePool resolution | Not ready | Priority research item. |
| GObjects/GUObjectArray enumeration | Not ready | Validate object shapes in isolation before accepting offsets. |
| UObject flag validity policy | Not ready | Static flag-policy reports, transition matrices, and strict serial-policy artifacts that pass the offline artifact gate in consume mode are candidate-only evidence. They do not prove lifecycle/validity or serial reuse semantics, do not satisfy promote-mode gates, and do not unlock `ResourceHandle`, object lookup, GObjects promotion, persistent handles, identity, mutation, or return overrides. |
| General reflected UFunction parameter decoding | Not ready | Candidate-only module recognizers exist, but SDK-facing decoding remains unpromoted. |
| Higher-level SDK APIs | Not ready | Outside the promoted `GameplayPolicyEvent` surface, the minimal `ChatMessageEvent` RC notification surface, and process-local core timers, Inventory, Items, players, richer chat, tribes, dinos, missions, transfers, permissions, gameplay/module timers, admin, commands, and public `StructureEvents` remain roadmap items until each has copied payloads, ABI tests, privacy policy, and accepted target-set evidence. The three item return-only checks are public only as copied `GameplayPolicyEvent` `ReturnValue` kinds; remaining item producer/runtime validation, Mission copied-bool observer, and Transfer `bAccept` work stay internal. Transfer `bAccept` internal work is offline/test-only only: no runtime target source, `PluginManager` wiring, marker/env activation, installed plugin path, public manifest, docs, or examples. Public Inventory SDK, Items SDK, Mission SDK, and Transfer SDK surfaces remain absent. |

## v1.0 SDK Completion Bar

`v1.0` should not be used for a partial runtime-only release. A stable SDK release needs:

- installed SDK package validation for every promoted public surface;
- plugin lifecycle, config, logging, timers, descriptors, chat, policy, identity, command,
  inventory/item, structure, dino, tribe/player, mission/transfer, and operator-facing
  extension paths to be either promoted with evidence or explicitly excluded from the
  `v1.0` compatibility statement;
- copied C ABI payloads with ownership, unregister, shutdown, privacy, and multi-instance
  behavior documented and tested;
- no public dependency on UE4 internals, raw `ProcessEvent` params, borrowed `UObject`,
  raw `FString`, raw FName/GObjects indices, ArkApi offsets, MSVC layouts, or vtable
  assumptions.

## Current Game Interaction Boundary

The first stable line should prove the Linux runtime, hook, plugin ABI, install layout, and
safe observation model before promising gameplay-authoritative behavior.

Current safe interaction shape:

- consume copied Obelisk-level events first; raw filtered `ProcessEvent` callbacks require
  an explicit debug gate;
- keep callbacks filtered, non-blocking, and instance-gated;
- record metadata or plugin-local state only;
- consume `GameplayPolicyEvent` as copied POD policy data, including inventory-backed
  policy signals, without identity, lookup, mutation, return override, or UE internals;
- consume `ChatMessageEvent` as copied UTF-8 notification data without sender identity,
  command routing, chat mutation, return override, or UE internals;
- restore stable posture after any approved debug-server experiment.

Blocked from stable plugin APIs until promoted with evidence:

- mutating UE4 parameter buffers or return values;
- blocking the original `ProcessEvent` from plugin callbacks except in an explicit
  debug/experimental gate;
- calling arbitrary UE4 functions or replaying events through `CallProcessEvent`;
- exposing borrowed `UObject`, `FString`, `UFunction`, or raw parameter memory to plugins;
- publishing gameplay module APIs for players, richer chat, tribes, buffs, inventory,
  items, dinos, structures, missions, transfers, permissions, gameplay/module timers,
  admin, or commands.

## Harness Safety Baseline

For any shared or player-facing validation adapter, the documented stable markers are:

```text
state/instances/<instance-id>/enable-process-event-hook
state/instances/<instance-id>/disable-plugins
```

`disable-plugins` is a supported wrapper marker. It is not a runtime gate by itself; the
runtime disables plugin loading when the wrapper or launcher sets
`OBELISK_DISABLE_PLUGINS=1`.

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
