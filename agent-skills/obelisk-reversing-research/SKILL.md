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
- Native exec field patching was unsafe and must remain disabled. Do not use
  `OBELISK_ENABLE_NATIVE_EXEC_PROBES=1` unless a future written plan proves a separate
  throwaway process can tolerate crashes.
- The ReflectionScanner analyzer strict mode now requires a repeat-confirmed exact
  `matched_clues=3/3` table candidate; a single exact row is only a clue.

## Research Principles

- Prefer reflection-backed decoding over raw memory scanning in plugins.
- Do not scan arbitrary params on every `ProcessEvent` in live servers.
- Use filtered callbacks by `fname_index` whenever possible.
- Treat `ReflectionScanner` as an offline/debug tool, not a production startup feature.
- Every new offset or signature must include how it was derived and what binary/version it was tested against.
- Run scanner captures only on a confirmed isolated/debug instance. The preferred plan is
  `arkserver-obelisk-debug`; do not reuse live Ragnarok/TheIsland marker posture.

## Safe Experiment Pattern

Start with the core stable and plugins disabled:

```bash
mkdir -p /servidor/ark/obelisk/state/instances/arkserver
touch /servidor/ark/obelisk/state/instances/arkserver/enable-process-event-hook
touch /servidor/ark/obelisk/state/instances/arkserver/disable-plugins
./arkserver restart
```

On production Ragnarok, stop here unless the goal is only to validate the core hook.
Chat discovery has been unstable and must not be enabled on the live map as the normal
experiment path.

For scanner or event discovery, use only a confirmed isolated/debug instance and enable one
experiment at a time. The debug wrapper should set explicit environment variables such as:

```bash
export OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
export OBELISK_DISABLE_PLUGINS=1
export OBELISK_INSTANCE_ID=arkserver-obelisk-debug
export OBELISK_PE_TRACE_LIMIT=0
unset OBELISK_ENABLE_NATIVE_EXEC_PROBES
```

Set `OBELISK_ENABLE_REFLECTION_SCANNER=1` only for the specific scanner capture start, then
copy the log and analyze it offline:

```bash
python3 scripts/analyze_reflectionscanner_capture.py /path/to/isolated/Obelisk.log
python3 scripts/analyze_reflectionscanner_capture.py --strict /path/to/isolated/Obelisk.log
```

Strict success is still research evidence, not a committed offset. Require either a second
isolated capture or static xref validation before promoting a candidate.

## Next Research Goals

1. Resolve `fname_index -> name` through GNames/FNamePool.
2. Locate GObjects and enumerate UFunction objects.
3. Register callbacks by function name, not raw index.
4. Decode function params from UProperty metadata.
5. Replace raw FString probing with reflected param decoding.
