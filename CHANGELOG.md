# Changelog

## Unreleased

- Promoted the owner-token timer API as the first non-UE-dependent v0.1 core primitive:
  process-local one-shot/repeating callbacks, zero-failure handles, explicit owner-scoped
  unregister, plugin init-failure/unload cleanup, and ABI/layout tests. Timer handles are
  not persistent, shared-cluster state, UE identity, lookup, mutation, or command routing.

## 0.1.0-rc.1

Published release candidate. RC public scope remains limited to
`GameplayPolicyEvent`, the minimal copied `ChatMessageEvent`, `DescribeResourceKind`, and
`DescribeGameplayPolicyEventKind`. This entry is not a production-stable release claim.
Post-RC development should target the broader `v1.0` production core and eventual
ArkApi-style plugin replacement without retroactively expanding this RC scope.

## 0.1.0-dev

Active development toward a future `v0.1.0`. This is not a release tag and does not promise
stable plugin or reflection compatibility yet. See `docs/VERSIONING.md`.

Current baseline:

- Linux `LD_PRELOAD` runtime bootstrap validated through the ARK: Survival Evolved
  dedicated server debug harness.
- Absolute x86_64 `UObject::ProcessEvent` hook with guarded validation.
- C plugin ABI with logging, debug-gated filtered ProcessEvent callbacks, owner cleanup,
  owner-token callback handles, owner-scoped unregister, and optional plugin shutdown.
- Public plugin C ABI v1 is the intended first-stable compatibility contract for
  `v0.1.0`; any ABI v2 must ship with an explicit migration plan.
- Runtime default-deny gates for filtered/global ProcessEvent callbacks, the unpromoted
  `CallProcessEvent` escape hatch, and plugin callback blocking of the original
  ProcessEvent path. These require explicit debug-window env, marker, and capability
  posture before they behave as active features.
- Fail-closed ProcessEvent hook removal: restore/reprotect failures now preserve hook
  state and trampoline ownership instead of claiming a clean removal.
- Central install layout under an operator-chosen Obelisk root, with runtime libraries
  staged before atomic publication.
- Plugin publication through `scripts/install_obelisk_plugin.sh`, using a staged non-`.so`
  copy before atomic rename into the shared plugin directory.
- Multi-instance shared-root posture: plugin binaries and configs may be shared, while
  `OBELISK_INSTANCE_ID` scopes logs, markers, plugin activation, and process-local runtime
  handles.
- LinuxGSM wrapper templates for the current ARK debug harness.
- `oBaseEvents` as the first official plugin example, including owner-token handle
  registration and safe `instance_allowlist` validation.
- `GameplayPolicyEvent` as the promoted v0.1 gameplay policy callback family, exposing
  copied POD scalar policy signals through owner-token handle registration without
  resource identity, lookup, mutation, or return override authority.
- Internal inventory policy recognizers for `PrimalItem.CanUse` and
  `PrimalItem.AllowRemoteAddToInventory` now fail closed on exact UFunction class,
  outer object index, property class object index, and property flag mismatches before
  feeding copied scalar policy events.
- `DescribeResourceKind` as metadata-only descriptors for known resource categories,
  explicitly not `ResourceHandle`, object identity, lookup, or cross-event correlation.
- `DescribeGameplayPolicyEventKind` as metadata-only descriptors for promoted
  `GameplayPolicyEvent` kinds, explicitly not a module SDK, UE lookup, mutation, or
  return-override surface.
- `ChatMessageEvent` as a minimal v0.1-rc chat plugin event ABI surface with copied UTF-8
  message bytes, send mode, copied-payload flag, and process-local sequence only;
  explicitly not a command SDK, sender identity API, chat send/moderation surface, UE
  lookup, raw `FString`, raw params, UE pointers, mutation, or return-override surface.
  Actual plugin-facing delivery from real chat messages has accepted copied-log
  `enable-chat-events` validation with 18 accepted delivery events from an approved
  operator-selected beta-test window, covering send modes `0,1,2,3` with no privacy
  blockers.
- First-stable plugin scope now excludes background workers, sockets, HTTP
  listeners/clients, long-lived file readers, and other external ingress unless a future
  plugin passes explicit shutdown, unregister, drain, join, and close gates.
- Read-only operator CLI for install, instance, and plugin state inspection.
- Release readiness script covering build, CTest, script tests, second-source readiness
  when required, install layout validation, installed SDK consumer builds, read-only CLI
  status, installer dry-runs, and whitespace/clean-tree checks.
- Offline reflection capture analyzer, shared target-set snapshot comparison/regeneration,
  evidence-pack tooling, and dry-run UFunction target-set regeneration planning for
  second-source reflection research. The refreshed default `minimal-second-source-intake`
  remains layout-only with `promotion_ready=false` and does not promote public
  Inventory/Structure SDKs, `ResourceHandle`, GObjects lookup, mutation, or return
  overrides.
- Static-only global candidate evidence tooling for FName/GNames/GObjects promotion
  research, with fail-closed promotion gates, explicit candidate-kind handling,
  copied/generated artifact hashes, and per-target ELF/xref provenance.
- CTest coverage for plugin config, ABI layout, plugin lifecycle, callback ownership,
  runtime markers, module recognizers, and external SDK consumers.

Breaking/development changes:

- Legacy binary-local plugin fallback and map-marker fallback paths were removed.
- Legacy chat/monitor prototype code was removed from the release tree.
- Public plugin config is now runtime-owned under
  `${OBELISK_CONFIG_DIR}/<plugin-id>/config.json`.
- Enabled plugin configs fail closed unless scoped to the current `OBELISK_INSTANCE_ID` or
  explicit `allow_all_instances=true`.
- Global `ProcessEvent` callbacks are default-denied and require explicit runtime and
  marker gates.

Not included yet:

- GNames/GObjects-backed reflection layer.
- `ResourceHandle`, public `StructureEvents`, public Inventory SDK, and player, tribe,
  inventory, item, structure, dino, buff, mission, transfer, admin, permission, command, or
  gameplay/module timer SDKs, including richer chat APIs and command APIs beyond
  `ChatMessageEvent`.
- Gameplay mutation, return override APIs, and public `CallProcessEvent`-based plugin
  behavior.
- Mutable operator lifecycle commands such as `obelisk restart` and
  `obelisk plugins enable/disable`; these are post-first-stable TODOs.
- Production-ready HTTP plugins.
- Background-work plugins without idempotent shutdown and worker/ingress cleanup evidence.
