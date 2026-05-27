---
name: obelisk-ue4-reversing
description: Operational reversing workflow for maintaining Obelisk against ARK Linux ShooterGameServer updates, signatures, FName/object globals, and safe experiments.
---

# Obelisk UE4 Reversing Skill

Use this skill when an ARK update changes signatures, ProcessEvent discovery fails, chat
events are not detected, reflection globals need validation, or a server crash may be tied
to native hooks.

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

- Current validated Ragnarok candidate: `0x1d34e20`.
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

- Maintain the current FName/GObjects/UFunction evidence against future binary updates.
- Re-run `scripts/enumerate_core_uobjects.py` and `scripts/inspect_core_ufunctions.py`
  when the ARK binary hash changes.
- Confirm deployed chat reflection with a real in-game chat message before promoting text
  decoding or plugin-facing events.
- Recover additional event families only after repeating the reflection path: object,
  function, property chain, bounded params, then decoder.
- Use copied logs with `scripts/analyze_reflectionscanner_capture.py`; `--strict` requires
  repeat-confirmed exact FName table clues and should fail on single-hit candidates.

`ReflectionScanner` may scan UTF-32 names such as `ServerSendChatMessage`, `ServerChat`,
`ClientServerChatMessage`, `ClientChatMessage`, and `ClientMessage`, plus mov-immediate and
RIP-relative references. Treat results as candidates until cross-validated by object and
property metadata.

## Live Server Safety

- Keep `OBELISK_ENABLE_PROCESS_EVENT_HOOK=1` plus plugins disabled as the baseline safe
  runtime test.
- `OBELISK_ENABLE_CHAT_REFLECTION=1` is allowed on the current development `arkserver`
  only with the matching `OBELISK_CHAT_REFLECTION_BINARY_SHA256` gate and small log limit.
- Do not enable `OBELISK_ENABLE_NATIVE_EXEC_PROBES=1` on live servers.
- Do not enable broad event discovery on a production map until it has survived an
  isolated server test.
- Do not run `ReflectionScanner` on `arkserver` or `arkserver2` unless one has been
  explicitly converted into an isolated debug target. Preferred path:
  `arkserver-obelisk-debug`.
- Use small `OBELISK_PE_TRACE_LIMIT` windows only when capturing evidence; default should
  remain quiet.
- Prefer the `enable-chat-reflection` marker over ad hoc environment edits; rollback is
  removing the marker and restarting the debug/development server.
- If a plugin crashes during load/init, disable plugins first and preserve logs/core files
  for analysis.

## Checklist

- [ ] Did you hash and identify the exact server binary before accepting the result?
- [ ] Did the pattern produce one candidate and reject known false positives?
- [ ] Did you validate executable range and prologue before hook installation?
- [ ] Did you avoid native exec probes on live servers?
- [ ] Are candidate globals/functions confirmed by more than string proximity?
- [ ] Are new offsets documented with commit, binary hash, and observed map/server?
