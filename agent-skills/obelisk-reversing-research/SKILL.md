---
name: obelisk-reversing-research
description: Use when researching ARK/UE4 internals for Obelisk: FName/GNames/GObjects, UFunction discovery, ProcessEvent fname_index mapping, ReflectionScanner analysis, chat/event decoding, and safe live-server experiments.
---

# Obelisk Reversing Research

Use this skill for UE4/ARK research and experimental plugin work. Keep runtime-core edits out of scope unless the research proves a required ABI or hook change.

## Scope

Own these areas:

- `ue/ReflectionScanner.*`
- `ue/Memory.*`
- `ue/Reflection.h`
- `plugins/chat/ChatPlugin.cpp`
- docs describing offsets, signatures, and experiments

## Known Findings

- Current `UObject::ProcessEvent` candidate: runtime address `0x1d34e20` on the tested
  non-PIE binary where the ELF image base is `0x400000`. Treat this as build-specific
  evidence, not a universal formula.
- Previous candidate `0x1d11cb0` was a false positive and did not receive gameplay events.
- Vtable-derived ProcessEvent slot observed around slot 61.
- Raw scanner found likely chat-related FName/object indices:
  - `ClientMessageIndex`: `9619`
  - `ServerChatIndex`: `9622`
- Native exec field patching was unsafe and must remain disabled unless explicitly isolated.

## Research Principles

- Prefer reflection-backed decoding over raw memory scanning in plugins.
- Do not scan arbitrary params on every `ProcessEvent` in live servers.
- Use filtered callbacks by `fname_index` whenever possible.
- Treat `ReflectionScanner` as an offline/debug tool, not a production startup feature.
- Every new offset or signature must include how it was derived and what binary/version it was tested against.

## Safe Experiment Pattern

Start with the core stable and plugins disabled:

```bash
touch /servidor/ark/obelisk/state/enable-process-event-hook-ragnarok
touch /servidor/ark/obelisk/state/disable-plugins-ragnarok
./arkserver restart
```

On production Ragnarok, stop here unless the goal is only to validate the core hook.
Chat discovery has been unstable and must not be enabled on the live map as the normal
experiment path.

For chat discovery, use an isolated or non-critical instance and enable only one experiment
at a time:

```bash
rm -f /servidor/ark/obelisk/state/disable-plugins-ragnarok
touch /servidor/ark/obelisk/state/enable-chat-discovery-ragnarok
./arkserver restart
```

If the test instance crashes, immediately restore:

```bash
touch /servidor/ark/obelisk/state/disable-plugins-ragnarok
rm -f /servidor/ark/obelisk/state/enable-chat-discovery-ragnarok
./arkserver start
```

## Next Research Goals

1. Resolve `fname_index -> name` through GNames/FNamePool.
2. Locate GObjects and enumerate UFunction objects.
3. Register callbacks by function name, not raw index.
4. Decode function params from UProperty metadata.
5. Replace ChatPlugin FString probing with reflected param decoding.
