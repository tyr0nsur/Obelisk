---
name: obelisk-ue4-reversing
description: "Operational reversing workflow for maintaining Obelisk against ARK Linux ShooterGameServer updates, signatures, FName/object globals, and safe experiments."
---

# Obelisk UE4 Reversing Skill

Use this skill when an ARK update changes signatures, ProcessEvent discovery fails,
gameplay module recognizers need validation, reflection globals need validation, or a
server crash may be tied to native hooks.

## Ground Truth First

Record this before accepting a new offset or pattern:

- Absolute path to `ShooterGameServer`.
- Binary hash: `sha256sum ShooterGameServer`.
- Server/map tested, for example Ragnarok or TheIsland.
- Obelisk commit hash and build type.
- Whether plugins were enabled or disabled.
- Exact env/config gates used for the test.

## Static Toolkit

Use Linux-native inspection first:

```bash
readelf -Ws ShooterGameServer
nm -D ShooterGameServer
nm -C ShooterGameServer
objdump -d --start-address=0xADDR --stop-address=0xADDR ShooterGameServer
c++filt '<mangled-name>'
sha256sum ShooterGameServer
```

Use `/proc/<pid>/maps` to confirm loaded ranges for the live process. Prefer stable evidence
from the ELF executable segment plus runtime maps over guesses from one crash log.

## ProcessEvent Maintenance

- Current binary-hash-scoped ProcessEvent candidate: `0x1d34e20` on the validated
  non-PIE ARK Linux binary where ELF image base was `0x400000`. Treat this as
  build-specific evidence, not as permission to touch Ragnarok or as a universal offset.
- Previous false positive: `0x1d11cb0`. Do not reuse it just because a pattern finds it.
- Pattern scanning should produce exactly one strong candidate. Multiple candidates means
  the signature is not precise enough.
- Fallbacks like `base + 0x1D34E20` are unsafe unless the binary hash and prologue are
  validated for that exact build.
- Before installing the hook, verify the target is executable, inside the expected module,
  and has a known compatible prologue.
- Manual trampolines must account for instruction boundaries and RIP-relative relocation.
  If the prologue changes, use a decoder such as Capstone/Zydis or refuse to hook.

## Reflection Research

Known research targets:

- ArkServerApi/AseApi can accelerate target discovery by naming ARK functions,
  properties, command/timer concepts, and plugin expectations. Treat it as a name and
  demand dictionary only; reject copied offsets, vtables, Windows/MSVC ABI assumptions,
  and direct memory access patterns. Linux support must be rebuilt through Obelisk
  `ReflectionScanner` evidence and the native `ProcessEventHook`.
- Maintain the current FName/GObjects/UFunction evidence against future binary updates.
- Re-run `scripts/enumerate_core_uobjects.py` and `scripts/inspect_core_ufunctions.py`
  when the ARK binary hash changes.
- Treat historical chat work as one module-recognizer example, not the roadmap center.
  For normal incoming player chat, prior evidence favors
  `ShooterPlayerController.ServerSendChatMessage` over `ServerChat*`; the latter currently
  looks like `ShooterCheatManager` command coverage. Keep this evidence internal until the
  common module promotion gates pass.
- Recover event families by repeating the same reflection path for each module: object,
  function, property chain, bounded params, copied-data ownership, callback lifecycle, then
  decoder/API surface.
- Use copied logs with `scripts/analyze_reflectionscanner_capture.py`; `--strict` requires
  repeat-confirmed exact FName table clues and should fail on single-hit candidates.

`ReflectionScanner` may scan UTF-32 names for approved module-recognizer targets such as
chat, inventory, structures, buffs, dinos, tribes, transfers, missions, and admin flows,
plus mov-immediate and RIP-relative references. Treat results as candidates until
cross-validated by object and property metadata.

## Live Server Safety

- A safe runtime validation posture is explicit ProcessEvent hook enablement plus the
  `enable-process-event-hook` marker and plugins disabled on the approved instance. This
  is not a standing permission to restart or probe any player-facing server.
- Current instance posture belongs in `docs/agent-handoff/CURRENT.md`. Read it before
  server-backed reversing, then require explicit approval for the exact target, marker
  changes, restart window, rollback plan, and shutdown expectations.
- Experimental module recognizers belong only on an explicitly approved debug/development
  target. The historical chat gate (`OBELISK_ENABLE_CHAT_REFLECTION=1`) additionally
  requires `allow-experimental-observers`, the matching
  `OBELISK_CHAT_REFLECTION_BINARY_SHA256` gate, and a small log limit.
- Do not enable `OBELISK_ENABLE_NATIVE_EXEC_PROBES=1` plus
  `enable-native-exec-probes` on live servers.
- Do not enable broad event discovery on a production map until it has survived an
  isolated server test.
- Do not run `ReflectionScanner`, `gcore`/`ptrace`, broad tracing, native exec probes, or
  scanner-like captures on protected production/shared instances. Run them only for a
  specifically approved debug window with plugins disabled, copied-log evidence, rollback,
  and shutdown at the end when required.
- Use small `OBELISK_PE_TRACE_LIMIT` windows only when capturing evidence; default should
  remain quiet.
- Prefer per-instance markers over ad hoc environment edits for approved debug captures.
  Rollback is removing the approved marker and restarting the approved debug/development
  server during the same run window.
- If a plugin crashes during load/init, disable plugins first and preserve logs/core files
  for analysis.

## Checklist

- [ ] Did you hash and identify the exact server binary before accepting the result?
- [ ] Did the pattern produce one candidate and reject known false positives?
- [ ] Did you validate executable range and prologue before hook installation?
- [ ] Did you avoid native exec probes on live servers?
- [ ] Are candidate globals/functions confirmed by more than string proximity?
- [ ] Are new offsets documented with commit, binary hash, and observed map/server?
