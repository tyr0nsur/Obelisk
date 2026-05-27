# Changelog

## 0.1.0-dev

Active development toward a future `v0.1.0`. This is not a release tag and does not promise
stable plugin or reflection compatibility yet. See `docs/VERSIONING.md`.

Current baseline:

- Linux `LD_PRELOAD` runtime bootstrap validated through the ARK: Survival Evolved
  dedicated server debug harness.
- Absolute x86_64 `UObject::ProcessEvent` hook with guarded validation.
- C plugin ABI with logging, filtered ProcessEvent callbacks, owner cleanup, and optional
  plugin shutdown.
- Central install layout under an operator-chosen Obelisk root.
- Per-instance logs and preferred state markers via `OBELISK_INSTANCE_ID`.
- LinuxGSM wrapper templates for the current ARK debug harness.
- `oBaseEvents` as the first official plugin example.
- Offline reflection capture analyzer tooling.
- CTest coverage for plugin config, ABI layout, and a minimal external SDK consumer.

Breaking/development changes:

- Legacy binary-local plugin fallback and map-marker fallback paths were removed.
- Legacy chat/monitor prototype code was removed from the release tree.
- Public plugin config is now runtime-owned under
  `${OBELISK_CONFIG_DIR}/<plugin-id>/config.json`.

Not included yet:

- Stable chat command API.
- GNames/GObjects-backed reflection layer.
- Player, tribe, inventory, dino, permission, or timer SDKs.
- Production-ready HTTP plugins.
