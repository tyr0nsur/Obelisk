# Changelog

## 0.1.0 - Unreleased

Initial release scope:

- Linux `LD_PRELOAD` runtime bootstrap for ARK: Survival Evolved dedicated servers.
- Absolute x86_64 `UObject::ProcessEvent` hook with guarded validation.
- C plugin ABI with logging, filtered ProcessEvent callbacks, owner cleanup, and optional
  plugin shutdown.
- Central install layout under an operator-chosen Obelisk root.
- LinuxGSM wrapper templates.
- `oBaseEvents` as the first official plugin example.
- Offline reflection capture analyzer tooling.

Not included yet:

- Stable chat command API.
- GNames/GObjects-backed reflection layer.
- Player, tribe, inventory, dino, permission, or timer SDKs.
- Production-ready HTTP plugins.
