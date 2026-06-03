# ProcessEvent Target Validation Hardening

## Objective

Harden the runtime ProcessEvent hook against unsafe fallback installation and unvalidated
prologue changes without rewriting the hook mechanism.

## Environment

- Workspace: `/home/flowcommunity-ark/Obelisk`
- Date: 2026-05-27
- Scope: `hooks/ProcessEventHook.cpp`
- Validation: local CMake build only; no live server restart in this round.

## Hypothesis

The existing hook can be made safer by refusing to install unless the selected target is
inside the ShooterGameServer executable segment and begins with the known 18-byte
instruction-boundary prologue used by the current trampoline copy size.

## Method

- Added a single expected ProcessEvent prologue byte array matching the first 18 bytes of
  the existing vtable-derived signature.
- Validated candidate targets before installation:
  - non-null target
  - target range fully inside the ShooterGameServer executable segment
  - target bytes readable
  - first 18 bytes match the expected prologue
- Required the pattern path to produce exactly one accepted candidate before using it.
- Superseded on 2026-06-03: the direct `base + 0x1D34E20` fallback described by this
  historical note is no longer active runtime behavior. Current hook code fails closed when
  pattern candidates are absent and requires ProcessEvent to be rediscovered for the
  current binary instead of installing from a direct offset.
- Added a defensive readability check immediately before trampoline byte copying.

## Evidence

- `cmake --build build -j"$(nproc)"` completed and built `obelisk`.
- Build emitted existing `fmt/spdlog` header warnings, but no compile or link failure.

## Result

The hook no longer blindly installs on the first pattern match. A changed prologue,
unreadable target, target outside executable text, ambiguous pattern result, or missing
pattern candidate prevents installation. The historical direct-offset fallback is
superseded and must not be used in active runtime or operator briefs.

## Rejected paths

- Did not add Capstone/Zydis or rewrite trampoline relocation logic.
- Did not change UE reflection/chat paths.
- Did not alter plugin callback ABI or ownership behavior.

## Risks

- The manual trampoline still assumes the first 18 bytes are safe to copy and do not need
  RIP-relative relocation. The new guard refuses changed prologues but does not decode
  arbitrary future prologues.
- If future ARK builds keep semantics but change the prologue, the hook will refuse to
  install until the signature/trampoline validation is deliberately updated.

## Next steps

- Keep direct offsets out of active hook installation paths; if a future binary requires a
  new target, rediscover and promote it with an evidence pack rather than reusing a
  fallback offset.
- Replace fixed-size prologue copying with an instruction decoder before supporting changed
  ProcessEvent prologues.

## Skill updates needed

- Updated `agent-skills/obelisk-linux-hooking/SKILL.md` to require executable range and
  known prologue validation before installing ProcessEvent hooks or direct-offset
  fallbacks.
