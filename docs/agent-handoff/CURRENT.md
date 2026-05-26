# Current Agent Handoff

Updated: 2026-05-27

## Stable Baseline

- fact: Obelisk central install root is `/servidor/ark/obelisk`.
- fact: Ragnarok stable baseline is ProcessEvent hook enabled with plugins disabled:
  `/servidor/ark/obelisk/state/enable-process-event-hook-ragnarok` and
  `/servidor/ark/obelisk/state/disable-plugins-ragnarok`.
- fact: Runtime/chat baseline is documented in
  `docs/research/2026-05-27-runtime-and-chat-baseline.md`.
- fact: Reflection/chat metadata audit added shared UE probe layouts and gated
  ReflectionScanner object/UFunction tail logging; see
  `docs/research/2026-05-27-reflection-chat-metadata-audit.md`.

## Rejected Or Unsafe

- rejected: ProcessEvent candidate `0x1d11cb0` did not receive gameplay events.
- risk: ChatPlugin raw FString scanning/discovery must not be enabled on live Ragnarok as
  the normal test path.
- risk: Native exec probes must remain disabled on live servers.

## Priority Next Steps

- fact: Plugin ProcessEvent callbacks now carry owner tokens and are unregistered on init
  failure and before unload/`dlclose`; see
  `docs/research/2026-05-27-plugin-callback-ownership-hardening.md`.
- fact: `ObeliskApi` now appends `abi_version`, `struct_size`, and `capabilities` without
  shifting existing function-pointer offsets; front-loaded ABI headers remain a future
  major-version plan.
- fact: Full build completed after fixing `ue/ReflectionScanner.cpp` pointer formatting in
  the reflection/chat metadata audit.
- next-step: Resolve `FName` indices through `GNames` or `FNamePool`.
- next-step: Locate `GUObjectArray`/`GObjects` and enumerate `UFunction` metadata.
- next-step: Use isolated ReflectionScanner captures to validate candidate object shapes
  before accepting any `GObjects`, `GNames`, or `UFunction` offset.
- next-step: Replace ChatPlugin raw parameter probing with reflected parameter decoding.

## Agent Protocol

- fact: Agents should read `agent-skills/obelisk-agent-handoff/SKILL.md`,
  `agent-skills/obelisk-continuous-learning/SKILL.md`, and the subsystem-specific skill
  before starting multi-agent work.
- next-step: After each investigation, update this file only with concise active context and
  put detailed evidence in `docs/research/`.
