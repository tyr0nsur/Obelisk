# Runtime and Chat Baseline

## Objective

Capture the current stable Obelisk baseline and the known chat/reversing direction after
the initial live-server investigation.

## Environment

- Obelisk root: `/servidor/ark/obelisk`
- Runtime install: `/servidor/ark/obelisk/lib/libobelisk.so`
- Plugin directory: `/servidor/ark/obelisk/plugins`
- Config directory: `/servidor/ark/obelisk/config`
- Logs: `/servidor/ark/obelisk/logs/arkserver`
- Convenient log links: `/home/flowcommunity-ark/logs/ark`
- Validated instance/map: `arkserver` / Ragnarok
- Stable development markers:
  - `/servidor/ark/obelisk/state/instances/arkserver/enable-process-event-hook`
  - `/servidor/ark/obelisk/state/instances/arkserver/disable-plugins`

## Evidence

- The runtime loads through `LD_PRELOAD`.
- The ProcessEvent hook is installed with an absolute x64 jump.
- The validated Ragnarok ProcessEvent signature candidate was observed at runtime address
  `0x1d34e20` on the tested non-PIE binary.
- The earlier `0x1d11cb0` candidate was a false positive and did not receive gameplay
  events.
- With plugins disabled, players can join Ragnarok with the core hook active.
- The removed ChatPlugin prototype remains historical only; new chat work should be rebuilt
  on reflected metadata and the release plugin ABI.

## Current Risks

- Plugin callbacks now carry owner tokens and unregister before init failure cleanup,
  unload, or `dlclose`; see `2026-05-27-plugin-callback-ownership-hardening.md`.
- The public plugin API now appends `abi_version`, `struct_size`, and capabilities as an
  ABI v1 compatibility bridge. A future ABI-major layout should put version metadata at the
  front and reject incompatible plugins explicitly.
- Manual ProcessEvent trampoline logic must be hardened against prologue changes and
  RIP-relative instructions.
- ChatPlugin still relies on raw parameter scanning and FString heuristics.

## Next Steps

1. Resolve `FName` indices to strings through `GNames` or `FNamePool`.
2. Locate `GUObjectArray`/`GObjects` and enumerate `UFunction` metadata.
3. Replace ChatPlugin raw memory probing with reflected parameter decoding.
4. Design a future ABI v2 with front-loaded version metadata and explicit rejection of
   incompatible plugins.
