# Current Agent Handoff

Updated: 2026-05-28

This file is the active routing table for the next Obelisk agent or leader round. It keeps
only current posture, hard rules, and immediate priorities. Historical detail from the
pre-compaction handoff is preserved in
`docs/agent-handoff/HISTORY-2026-05-28-pre-current-compaction.md`; durable evidence belongs
in `docs/research/` and stable resume facts belong in `docs/agent-handoff/COMPACT_CONTEXT.md`.

## Active Operating Objective

- fact: The persistent leader objective is tracked in the goal tool, not repeated in skills
  or default sub-agent prompts.
- priority: move Obelisk toward a production-stable Linux runtime/API/SDK core for ARK
  modding: safe hooks, stable C ABI, plugin lifecycle, install layout, UE4 reflection,
  second-source evidence, and public SDK promotion gates.
- scope rule: treat chat, inventory, structures, buffs, dinos, tribes, missions,
  transfers, and admin surfaces as module areas on top of the same core, not as the center
  of the project.
- agent rule: pass sub-agents only scoped objective, ownership, relevant skills, safety
  baseline, and deliverable. Do not pass leader cadence, Discord policy, or unrelated
  long-term strategy.
- agent lifecycle rule: every supervised round starts by checking for stale stand-by
  agents; close completed/obsolete agents before spawning replacements and record any
  intentionally active agent with a polling/integration plan.

## Live Ops Guardrails

- guardrail: do not restart servers, edit `/servidor/ark`, change markers, run
  ReflectionScanner, attach ptrace/gcore, enable broad `ProcessEvent` tracing, or publish
  runtime observations without explicit operator approval for that exact run.
- fact: Obelisk central install root is `/servidor/ark/obelisk`.
- fact: ARK config restore notes are in `docs/SERVER_RESTORE.md`; latest config backup
  symlink is `/home/flowcommunity-ark/backups/ark-config-latest`.
- fact: `arkserver` / Ragnarok has users and must be protected. Do not restart it, change
  markers, or use it for Obelisk validation while users are active.
- fact: read-only audit on 2026-05-28 found active Ragnarok PID `3412724` still carrying
  experimental chat/inventory/structure reflection env and markers. Stable posture check
  fails in that state. Do not fix by restart without an approved maintenance window.
- fact: user-provided live log evidence confirmed reflected `ServerSendChatMessage` events
  on Ragnarok. Treat this as operational evidence only; do not publish player payloads or
  enable payload logging.
- fact: `arkserver2` / TheIsland is the fallback debug target but is powered off. Start it
  only with explicit operator approval for a scoped test, then restore posture and shut it
  down afterward.
- fact: stable posture rejects ReflectionScanner, native exec probes, ptrace/debug-control,
  broad ProcessEvent tracing, global callbacks, public `CallProcessEvent`, ProcessEvent
  blocking, and observer/debug-window markers unless a specific approved debug workflow
  says otherwise.

## Stable Runtime Baseline

- fact: latest pushed checkpoint is `c40a997 Harden hook removal and reflection intake`.
- fact: core-first release readiness passed after `c40a997`: configure/build, 31 CTest
  tests, script tests, install layout/SDK consumer validation, dry-run install checks,
  `git diff --check`, and clean tracked worktree.
- fact: stable installer deploys runtime libraries only. Plugins activate only when their
  `.so` is published into `/servidor/ark/obelisk/plugins/` with
  `scripts/install_obelisk_plugin.sh`.
- fact: stable plugin loading requires a safe `OBELISK_INSTANCE_ID` and real non-symlink
  plugin/config/log roots. Operator CLI read-only views should surface unsafe entries
  instead of hiding them.
- fact: global ProcessEvent callbacks, public `CallProcessEvent`, and pre-callback
  blocking are runtime default-deny behind env + safe per-instance markers + capability
  bits where applicable.
- fact: `ProcessEventHook::Remove()` is fail-closed after `c40a997`: removal failures
  preserve hook state/trampoline ownership and report failure instead of clearing state
  while patched bytes may still execute.
- fact: `oBaseEvents` requires owner-token callback handle support for its ProcessEvent
  example and defensively rejects unsafe `instance_allowlist` entries before callback
  registration.
- fact: operator CLI lifecycle/mutation commands such as `obelisk start/stop/restart` and
  per-plugin start/stop/restart are post-first-stable TODOs. Keep the first stable release
  focused on runtime/API/install safety.

## Reflection And Reversing State

- fact: current binary hash used by committed evidence is
  `7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520`.
- fact: `ProcessEvent` candidate is `0x1d34e20` for the validated non-PIE ARK Linux
  binary. Historical `0x1d11cb0` is rejected.
- fact: confirmed FName clues for the current binary include `4884 -> ClientMessage`,
  `9619 -> ServerChat`, and `9622 -> SetActiveMissionDebugFlags`; older index mappings are
  obsolete historical evidence.
- fact: `0x595b7e0` is a binary-hash-scoped `GUObjectArray` research-candidate, not a
  production contract. Do not restart broad GObjects hunting; repeat classified checks on a
  second isolated core or independent static path.
- fact: primary UFunction and ScriptStruct fixtures are comparable but single-source.
  Promotion requires accepted distinct second-source evidence.
- fact: `docs/research/2026-05-28-second-source-core-intake-runbook.md` is the current
  minimal approved-artifact path: build an evidence pack, verify per-artifact FName and
  GObjects data, regenerate `minimal-second-source-intake`, compare snapshots, and require
  four accepted targets with distinct artifact identity.
- fact: shared target sets live in `scripts/reflection_target_sets.py` and are accepted by
  comparison plus UFunction/ScriptStruct regeneration tooling. Use `--target-set
  minimal-second-source-intake` for the first UFunction second-source gate and
  `--target-set transfer-scriptstruct` for transfer ScriptStruct checks.
- fact: internal recognizers for chat, inventory, structures, and buffs remain
  candidate-only. No public SDK gameplay callbacks, raw UE pointers, return overrides,
  mutation, or payload logging until reflected layouts, copied-data ownership, callback
  lifecycle, ABI, docs, and second-source gates are complete.

## Canonical References

- `docs/STATUS.md`: contributor-facing stability matrix.
- `docs/RELEASE.md`: release and second-source gate usage.
- `docs/PLUGIN_ARCHITECTURE.md`: plugin lifecycle and promotion rules.
- `docs/research/2026-05-28-reversing-objective-map.md`: broad reversing objective.
- `docs/research/2026-05-28-second-source-reversing-gap-matrix.md`: evidence gaps and
  target-set promotion matrix.
- `docs/research/2026-05-28-second-source-core-intake-runbook.md`: shortest offline intake
  for an approved independent core artifact.
- `docs/agent-handoff/COMPACT_CONTEXT.md`: compact resume facts after context compaction.
- `docs/agent-handoff/HISTORY-2026-05-28-pre-current-compaction.md`: full historical handoff
  snapshot before this file was compacted.

## Priority Next Steps

- next-step: keep the next engineering rounds offline unless the operator approves a
  specific debug instance window.
- next-step: reduce remaining handoff/documentation debt by moving historical detail from
  active routing files into dated research notes or the handoff history archive.
- next-step: strengthen second-source tooling/readiness around the minimal intake and
  ensure all runbooks use executable commands.
- next-step: continue runtime/API hardening around plugin lifecycle, owner cleanup,
  install layout, and SDK consumer validation.
- next-step: prepare for an approved independent core/evidence artifact, but do not capture
  one without explicit operator approval for target, method, markers, restart window,
  rollback, and shutdown.

## Agent Protocol

- fact: lead owns commits, pushes, handoff integration, and Discord decisions.
- fact: sub-agents must not commit, amend, rebase, tag, push, or update GitHub state unless
  explicitly delegated for one turn.
- fact: split agent rounds by expert focus and file ownership: runtime/core, reversing,
  ABI/API, build/SDK, ops/docs.
- fact: read-only reviewers must not edit files. Documentation/skills agents must not edit
  runtime C++ or `/servidor/ark` unless explicitly assigned.
- next-step: after each investigation, update this file only with concise active context;
  put detailed evidence in `docs/research/` and stable resume facts in
  `COMPACT_CONTEXT.md`.
