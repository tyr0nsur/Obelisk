# Runtime and Chat Baseline

## Objective

Capture the current stable Obelisk baseline and the known chat/reversing direction after
the initial live-server investigation.

## Environment

- Obelisk root: `/servidor/ark/obelisk`
- Runtime install: `/servidor/ark/obelisk/lib/libobelisk.so`
- Plugin directory: `/servidor/ark/obelisk/plugins`
- Config directory: `/servidor/ark/obelisk/config/plugins`
- Logs: `/servidor/ark/obelisk/logs`
- Convenient log links: `/home/flowcommunity-ark/logs/ark`
- Validated map: Ragnarok
- Stable production markers:
  - `/servidor/ark/obelisk/state/enable-process-event-hook-ragnarok`
  - `/servidor/ark/obelisk/state/disable-plugins-ragnarok`

## Evidence

- The runtime loads through `LD_PRELOAD`.
- The ProcessEvent hook is installed with an absolute x64 jump.
- The validated Ragnarok ProcessEvent candidate was observed at runtime address
  `0x1d34e20` on the tested non-PIE binary.
- The earlier `0x1d11cb0` candidate was a false positive and did not receive gameplay
  events.
- With plugins disabled, players can join Ragnarok with the core hook active.
- ChatPlugin remains experimental and must not be enabled on the live map as the normal
  test path.

## Current Risks

- Plugin callbacks are raw function pointers and need plugin-owned unregister handling
  before init failure, unload, or `dlclose`.
- The public plugin API needs `abi_version`, `struct_size`, and capabilities before being
  treated as stable.
- Manual ProcessEvent trampoline logic must be hardened against prologue changes and
  RIP-relative instructions.
- ChatPlugin still relies on raw parameter scanning and FString heuristics.

## Next Steps

1. Add callback ownership and unregister paths in the runtime.
2. Add ABI version/size validation to `ObeliskApi`.
3. Resolve `FName` indices to strings through `GNames` or `FNamePool`.
4. Locate `GUObjectArray`/`GObjects` and enumerate `UFunction` metadata.
5. Replace ChatPlugin raw memory probing with reflected parameter decoding.
