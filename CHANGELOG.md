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
- Runtime default-deny gates for global ProcessEvent callbacks, public `CallProcessEvent`,
  and plugin callback blocking of the original ProcessEvent path. These require explicit
  debug-window env, marker, and capability posture before they behave as active features.
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
- Read-only operator CLI for install, instance, and plugin state inspection.
- Release readiness script covering build, CTest, script tests, installed SDK layout,
  read-only CLI status, installer dry-runs, and whitespace checks.
- Offline reflection capture analyzer, shared target-set snapshot comparison/regeneration,
  and evidence-pack tooling for second-source reflection research.
- Agent handoff guardrails that keep active coordination concise and archive historical
  context outside the current routing table.
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
- Player, tribe, inventory, item, structure, dino, transfer, admin, permission, command, or
  timer SDKs, including chat/command APIs.
- Mutable operator lifecycle commands such as `obelisk restart` and
  `obelisk plugins enable/disable`; these are post-first-stable TODOs.
- Production-ready HTTP plugins.
