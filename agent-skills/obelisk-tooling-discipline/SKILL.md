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
- `scripts/compare_reflection_snapshots.py --list-target-sets`, `--list-target-guidance`,
  and fixture-root readiness reports against `tests/fixtures/ufunction_snapshots`
- `scripts/build_redacted_ufunction_signatures.py` against committed sanitized fixtures,
  followed by `scripts/validate_offline_artifact_gate.py --strict-target-set-coverage`
- Ghidra/rizin/radare2 on copied binaries
- CMake/CTest validation against copied or installed SDK artifacts

Protected-path validation for offline tools must check both the direct expanded path and
the symlink-resolved path. A path textually under `/servidor/ark` is rejected even if it is
a symlink to an outside workspace, and a path outside `/servidor/ark` is rejected if it
resolves back under the protected server tree. The approved exception is
`/servidor/ark/workspace-offline`, which may hold hardlinks or copied artifacts for
offline analysis; do not point tools directly at `/servidor/ark/obelisk/dumps`.

Isolated-debug only:

- `gdb` attach,
- `rr` record/replay,
- Frida,
- dynamic binary instrumentation,
- `ReflectionScanner`,
- `OBELISK_ENABLE_DEBUG_CONTROL=1` plus `enable-debug-control` marker-triggered runtime probes,
- broad `ProcessEvent` tracing.

Development-server gated:

- Experimental module recognizers only when paired with explicit operator approval for
  the target, marker/env changes, restart window, and rollback. Historical chat reflection
  additionally requires the exact supported `OBELISK_CHAT_REFLECTION_BINARY_SHA256`, a
  small log limit, plugins disabled, and a post-change stable posture check for the exact
  approved target. Do not rely on posture-check defaults in agent rounds; pass explicit
  `--map <map> --instance <instance-id>` for the operator-approved target.
- Player-principal lifecycle evidence is a consume-only copied-log route, not a public
  identity route. It requires an exact single observer window with dispatch limit `0`,
  plugins disabled, no scanner/debug/callback escape markers, and an analyzed summary
  containing only the `player_principal_lifecycle` module. It must not be mixed with
  broad tracing, ReflectionScanner, ptrace/gcore, raw parameter exploration, plugin
  callbacks, or any public identity/lookup/promotion claim. Evidence bundle tooling must
  require `--window-manifest`, source path/SHA agreement with the copied log, rollback and
  stable-posture evidence, and no-public/no-promotion semantics.

Forbidden on live/shared instances:

- `OBELISK_ENABLE_NATIVE_EXEC_PROBES=1` plus `enable-native-exec-probes`,
- raw FString/text or arbitrary gameplay-param discovery loops,
- broad unbounded ProcessEvent logging,
- decoded player text or gameplay payload logging without reflected `UFunction`/
  `UProperty` validation, copied-data ownership, and a confirmed layout,
- patching unknown UE function pointers,
- external instrumentation that changes thread/process behavior.

## Selection Rules

- Prefer offline static analysis before runtime probes.
- Prefer copied logs over live attach.
- Prefer deterministic scripts over manual UI-only conclusions.
- Treat local Ghidra/rizin/radare2 availability as optional enrichment, not permission to
  rerun broad FName/GObjects/core/serial discovery. Reuse accepted roots and no-scan
  artifacts for the current binary hash unless new evidence contradicts them.
- For UFunction redacted-signature fixture work, list target sets and guidance first, then
  generate from `tests/fixtures/ufunction_snapshots` and validate with
  `validate_offline_artifact_gate.py --root <scratch-root> --mode consume
  --strict-target-set-coverage`. Treat non-zero exits as blockers; do not downgrade to
  promote mode for layout/signature-only artifacts.
- Do not rely on `check_obelisk_server_posture.sh` defaults in agent rounds. Use explicit
  `--map <map> --instance <instance-id>` for the approved target, and do not use protected
  production instances as validation targets without a specific operator-approved
  maintenance window.
- Use Ghidra for decompilation and manual xref reasoning, but summarize evidence in text.
- Current instance posture belongs in `docs/agent-handoff/CURRENT.md`. Read it before
  any server-backed work, then require explicit approval for the exact target, restart or
  marker changes, rollback plan, and shutdown expectations.
- For `gcore`, `ptrace`, `ReflectionScanner`, Frida/rr, broad event tracing, or
  scanner-like probes, require explicit approval for the exact debug instance run window
  and rollback plan. ReflectionScanner/native-exec activations require both env vars and
  their per-instance markers.
- Use Frida/rr only after there is a specifically approved debug window and a rollback
  plan.
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
  check. Use an explicit map/instance for the approved debug target; do not use defaults
  or protected live instances as a convenience validation target.
- Raw captures may live under `/servidor/ark/obelisk/dumps` for disk space and server-local
  collection. Promotion, snapshot regeneration, static evidence, and second-source intake
  tools must consume hardlinked or copied artifacts from `/servidor/ark/workspace-offline`
  or another approved offline root, not direct `dumps` paths.
- Provenance sidecars are path evidence too. Resolve relative path fields against the
  sidecar directory before applying protected-root checks; do not ignore relative
  `../...` values just because the artifact argument was relative.
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

Cron or overnight jobs may run read-only observation scripts only. Allowed outputs should
be local text summaries or an explicitly approved offline snapshot path. Writing under
`/servidor/ark/obelisk/dumps/` requires current operator approval.

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
