---
name: obelisk-tooling-discipline
description: "Use when choosing or operating reverse-engineering tools for Obelisk, especially deciding what is safe offline, what requires an isolated debug server, and what must not run on live ARK instances."
---

# Obelisk Tooling Discipline

Use this skill before introducing new tools, probes, debuggers, instrumenters, or scripts
into Obelisk research.

## Tool Classes

Offline-safe:

- `sha256sum`, `readelf`, `objdump`, `nm`, `c++filt`, `strings`
- copied Obelisk logs
- `scripts/analyze_reflectionscanner_capture.py` with copied logs, copied objdump output,
  and `--binary` pointed at an offline copy of `ShooterGameServer`
- Ghidra/rizin/radare2 on copied binaries
- CMake/CTest validation against copied or installed SDK artifacts

Isolated-debug only:

- `gdb` attach,
- `rr` record/replay,
- Frida,
- dynamic binary instrumentation,
- `ReflectionScanner`,
- `OBELISK_ENABLE_DEBUG_CONTROL=1` marker-triggered runtime probes,
- broad `ProcessEvent` tracing.

Development-server gated:

- `OBELISK_ENABLE_CHAT_REFLECTION=1` only when paired with the exact supported
  `OBELISK_CHAT_REFLECTION_BINARY_SHA256`, a small log limit, plugins disabled, and a
  post-change `scripts/check_obelisk_server_posture.sh --expect-stable`.

Forbidden on live/shared instances:

- `OBELISK_ENABLE_NATIVE_EXEC_PROBES=1`,
- raw chat/FString discovery loops,
- broad unbounded ProcessEvent logging,
- decoded chat text logging without reflected `UFunction`/`UProperty` validation and a
  confirmed `FString` layout,
- patching unknown UE function pointers,
- external instrumentation that changes thread/process behavior.

## Selection Rules

- Prefer offline static analysis before runtime probes.
- Prefer copied logs over live attach.
- Prefer deterministic scripts over manual UI-only conclusions.
- Use Ghidra for decompilation and manual xref reasoning, but summarize evidence in text.
- Use Frida/rr only after there is an isolated debug instance and a rollback plan.
- Do not introduce `/dev/null` write probes as memory-readability checks on Linux; current
  evidence shows they can report invalid mappings as readable.

## Adding A Tool

Before adopting a tool into the workflow:

1. State the question it answers better than existing tools.
2. Define whether it is offline-safe, isolated-debug only, or forbidden on live.
3. Add exact commands or scripts.
4. Document expected output and reject conditions.
5. Record where results belong: `docs/research/`, analyzer fixture, or code test.

## Evidence Discipline

- Prefer analyzer JSON evidence packs over hand-written offset summaries.
- Every runtime capture should have both a capture artifact and a post-capture posture
  check. Use `scripts/check_obelisk_server_posture.sh --expect-stable` after returning
  the server to normal mode.
- A tool result is not accepted unless another engineer can reproduce it from the command,
  binary hash, Obelisk commit, and copied artifacts.
- UI-only Ghidra conclusions must be translated into text: function/address, xref path,
  decompiled shape, and reject conditions. Do not rely on screenshots.

## Agent Rule

Sub-agents may recommend tools and commands, but the lead decides whether the tool becomes
part of the official workflow or skill set.

Sub-agents must not publish to GitHub or update handoff/versioning. They may edit their
assigned scope, but the lead performs integration, commits, pushes, and durable process
updates.

## Unattended Automation Rule

Cron or overnight jobs may run read-only observation scripts only. Allowed outputs are
timestamped snapshots under `/servidor/ark/obelisk/dumps/` or local text summaries.

Forbidden unattended actions:

- restarts,
- marker edits,
- runtime installs,
- scanner/debug-control enablement,
- debugger/core dump attach,
- broad tracing,
- commits, pushes, or GitHub changes.

If an unattended snapshot finds a bad posture, it should record the failure and stop. The
lead fixes posture in an active turn.
