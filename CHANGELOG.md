# Changelog

## 0.1.0-dev

Active development toward a future `v0.1.0`. This is not a release tag and does not promise
stable plugin or reflection compatibility yet. See `docs/VERSIONING.md`.

Current baseline:

- Linux `LD_PRELOAD` runtime bootstrap validated through the ARK: Survival Evolved
  dedicated server debug harness.
- Absolute x86_64 `UObject::ProcessEvent` hook with guarded validation.
- C plugin ABI with logging, filtered ProcessEvent callbacks, owner cleanup, owner-token
  callback handles, owner-scoped unregister, and optional plugin shutdown.
- Public plugin C ABI v1 is the intended first-stable compatibility contract for
  `v0.1.0`; any ABI v2 must ship with an explicit migration plan.
- Runtime default-deny gates for global ProcessEvent callbacks, the unpromoted
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
- `GameplayPolicyEvent` as the only promoted v0.1 gameplay callback family, exposing
  copied POD scalar policy signals through owner-token handle registration without
  resource identity, lookup, mutation, or return override authority.
- `DescribeResourceKind` as metadata-only descriptors for known resource categories,
  explicitly not `ResourceHandle`, object identity, lookup, or cross-event correlation.
- `DescribeGameplayPolicyEventKind` as metadata-only descriptors for promoted
  `GameplayPolicyEvent` kinds, explicitly not a module SDK, UE lookup, mutation, or
  return-override surface.
- First-stable plugin scope now excludes background workers, sockets, HTTP
  listeners/clients, long-lived file readers, and other external ingress unless a future
  plugin passes explicit shutdown, unregister, drain, join, and close gates.
- Read-only operator CLI for install, instance, and plugin state inspection.
- Release readiness script covering build, CTest, script tests, installed SDK layout,
  read-only CLI status, installer dry-runs, and whitespace checks.
- Offline reflection capture analyzer, shared target-set snapshot comparison/regeneration,
  evidence-pack tooling, and dry-run UFunction target-set regeneration planning for
  second-source reflection research.
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
  timer SDKs, including chat/command APIs.
- Gameplay mutation, return override APIs, and public `CallProcessEvent`-based plugin
  behavior.
- Mutable operator lifecycle commands such as `obelisk restart` and
  `obelisk plugins enable/disable`; these are post-first-stable TODOs.
- Production-ready HTTP plugins.
- Background-work plugins without idempotent shutdown and worker/ingress cleanup evidence.
