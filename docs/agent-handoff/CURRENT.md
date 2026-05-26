# Current Agent Handoff

Updated: 2026-05-27

## Stable Baseline

- fact: Obelisk central install root is `/servidor/ark/obelisk`.
- fact: Ragnarok stable baseline is ProcessEvent hook enabled with plugins disabled:
  `/servidor/ark/obelisk/state/enable-process-event-hook-ragnarok` and
  `/servidor/ark/obelisk/state/disable-plugins-ragnarok`.
- fact: Runtime/chat baseline is documented in
  `docs/research/2026-05-27-runtime-and-chat-baseline.md`.

## Rejected Or Unsafe

- rejected: ProcessEvent candidate `0x1d11cb0` did not receive gameplay events.
- risk: ChatPlugin raw FString scanning/discovery must not be enabled on live Ragnarok as
  the normal test path.
- risk: Native exec probes must remain disabled on live servers.

## Priority Next Steps

- next-step: Implement plugin-owned callback unregister before plugin unload or `dlclose`.
- next-step: Add `abi_version`, `struct_size`, and capabilities to `ObeliskApi`.
- next-step: Resolve `FName` indices through `GNames` or `FNamePool`.
- next-step: Locate `GUObjectArray`/`GObjects` and enumerate `UFunction` metadata.
- next-step: Replace ChatPlugin raw parameter probing with reflected parameter decoding.

## Agent Protocol

- fact: Agents should read `agent-skills/obelisk-agent-handoff/SKILL.md`,
  `agent-skills/obelisk-continuous-learning/SKILL.md`, and the subsystem-specific skill
  before starting multi-agent work.
- next-step: After each investigation, update this file only with concise active context and
  put detailed evidence in `docs/research/`.
