---
name: obelisk-reversing-research
description: "Use when researching ARK/UE4 internals for Obelisk: FName/GNames/GObjects, UFunction discovery, ProcessEvent fname_index mapping, ReflectionScanner analysis, chat/event decoding, and safe live-server experiments."
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
- Confirmed core FName clues for the current ARK binary hash:
  - `4884 -> ClientMessage`
  - `9619 -> ServerChat`
  - `9622 -> SetActiveMissionDebugFlags`
- Older notes that used `9619 -> ClientMessage` and `9622 -> ServerChat` are obsolete
  historical evidence.
- Core evidence promotes `0x595b7e0` to `GUObjectArray research-candidate`; first object
  resolves to `/Script/CoreUObject` and class resolves to `Package`.
- Native exec field patching was unsafe and must remain disabled. Do not use
  `OBELISK_ENABLE_NATIVE_EXEC_PROBES=1` unless a future written plan proves a separate
  throwaway process can tolerate crashes.
- The ReflectionScanner analyzer strict mode now requires a repeat-confirmed exact
  `matched_clues=3/3` table candidate; a single exact row is only a clue.
- Runtime debug control can trigger bounded probes after the process is alive. The first
  post-start `request-static-fname-probe` for `0x5956f30` executed correctly but still
  rejected the slot (`table=0x13733660`, `implausible_num_elements`). Do not keep waiting
  for bootstrap retries or promote `0x5956f30` from a single core-dump session.

## Research Principles

- Prefer reflection-backed decoding over raw memory scanning in plugins.
- Do not scan arbitrary params on every `ProcessEvent` in live servers.
- Use filtered callbacks by `fname_index` whenever possible.
- Treat `ReflectionScanner` as an offline/debug tool, not a production startup feature.
- Prefer post-start or offline evidence over blind startup waits. If a server is joinable
  and the scanner still reads zero/invalid tables, change the method instead of extending
  sleep/retry windows.
- Every new offset or signature must include how it was derived and what binary/version it was tested against.
- Run scanner captures only on a confirmed isolated/debug instance. Current operator
  direction designates `arkserver2` / TheIsland as the Obelisk debug/development target for
  controlled runtime validation, but scanner/native-exec/ptrace/gcore and broad tracing
  should prefer a dedicated `arkserver-obelisk-debug` instance. Use TheIsland for those
  high-risk captures only as an explicit approved fallback with a rollback plan.

## Safe Experiment Pattern

Do not use Ragnarok for new reversing/runtime experiments while player performance testing
is active. For low-risk controlled runtime validation, start with TheIsland core stable and
plugins disabled:

```bash
mkdir -p /servidor/ark/obelisk/state/instances/arkserver2
touch /servidor/ark/obelisk/state/instances/arkserver2/enable-process-event-hook
touch /servidor/ark/obelisk/state/instances/arkserver2/disable-plugins
./arkserver2 restart
```

On production Ragnarok, stop unless there is an explicit maintenance window. Chat
discovery has been unstable and must not be enabled on the live map as the normal
experiment path.

For scanner, `gcore`/`ptrace`, native exec experiments, or broad event discovery, use a
confirmed isolated/debug instance and enable one experiment at a time. Prefer
`arkserver-obelisk-debug`; use `arkserver2` / TheIsland only during an approved fallback
window. The debug wrapper should set explicit environment variables such as:

```bash
export OBELISK_ENABLE_PROCESS_EVENT_HOOK=1
export OBELISK_DISABLE_PLUGINS=1
export OBELISK_INSTANCE_ID=arkserver2
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

For live-like development captures authorized by the operator, keep the run short and
restore stable posture immediately:

```bash
scripts/check_obelisk_server_posture.sh --expect-stable --map TheIsland --instance arkserver2
```

Use explicit target flags for the approved debug instance. If this fails, fix the server
posture before doing more code or agent work.

## Test Strictness

- Analyzer tests must include accepted, rejected, and strict-mode failure fixtures for every
  new ReflectionScanner log family.
- Runtime probes must have explicit env gates and default to off.
- A sample, weak probe, or partial match must not satisfy analyzer `--strict`.
- Every capture note should include the post-capture stable posture check result.

## Next Research Goals

1. Resolve `fname_index -> name` through GNames/FNamePool.
2. Add a bounded live data-mapping scanner or offline core scanner for FName-table-shaped
   pointers instead of relying on one static slot.
3. Locate GObjects and enumerate UFunction objects.
4. Register callbacks by function name, not raw index.
5. Decode function params from UProperty metadata.
6. Replace raw FString probing with reflected param decoding.
