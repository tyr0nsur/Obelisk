---
name: obelisk-tooling-discipline
description: Use when choosing or operating reverse-engineering tools for Obelisk, especially deciding what is safe offline, what requires an isolated debug server, and what must not run on live ARK instances.
---

# Obelisk Tooling Discipline

Use this skill before introducing new tools, probes, debuggers, instrumenters, or scripts
into Obelisk research.

## Tool Classes

Offline-safe:

- `sha256sum`, `readelf`, `objdump`, `nm`, `c++filt`, `strings`
- copied Obelisk logs
- `scripts/analyze_reflectionscanner_capture.py`
- Ghidra/rizin/radare2 on copied binaries

Isolated-debug only:

- `gdb` attach,
- `rr` record/replay,
- Frida,
- dynamic binary instrumentation,
- `ReflectionScanner`,
- broad `ProcessEvent` tracing.

Forbidden on live/shared instances:

- `OBELISK_ENABLE_NATIVE_EXEC_PROBES=1`,
- raw chat/FString discovery loops,
- broad unbounded ProcessEvent logging,
- patching unknown UE function pointers,
- external instrumentation that changes thread/process behavior.

## Selection Rules

- Prefer offline static analysis before runtime probes.
- Prefer copied logs over live attach.
- Prefer deterministic scripts over manual UI-only conclusions.
- Use Ghidra for decompilation and manual xref reasoning, but summarize evidence in text.
- Use Frida/rr only after there is an isolated debug instance and a rollback plan.

## Adding A Tool

Before adopting a tool into the workflow:

1. State the question it answers better than existing tools.
2. Define whether it is offline-safe, isolated-debug only, or forbidden on live.
3. Add exact commands or scripts.
4. Document expected output and reject conditions.
5. Record where results belong: `docs/research/`, analyzer fixture, or code test.

## Agent Rule

Sub-agents may recommend tools and commands, but the lead decides whether the tool becomes
part of the official workflow or skill set.
