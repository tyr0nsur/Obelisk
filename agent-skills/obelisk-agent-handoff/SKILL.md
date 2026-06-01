---
name: obelisk-agent-handoff
description: "Use when Obelisk work is delegated between agents and they need to transfer valuable context through repo files, current state notes, and structured handoff updates."
---

# Obelisk Agent Handoff

Use this skill whenever multiple agents work on Obelisk or when a task may continue in a
later session.

## Shared Memory Files

Lead agents should read these before planning or delegating work:

- `docs/agent-handoff/CURRENT.md`: current active state, blockers, next tasks.
- `docs/agent-handoff/COMPACT_CONTEXT.md`: compact resume state after long sessions.
- `docs/research/README.md`: curated research index, then only the specific dated
  research notes relevant to the current scope.
- `docs/SERVER_RESTORE.md`: recovery flow for ARK config after SteamCMD/LinuxGSM rewrites.
- only the `agent-skills/*/SKILL.md` files relevant to the current scope.

Treat handoff files as lead-owned source material for a scoped prompt, not as text to
forward wholesale. Do not pass the full leader objective, leader cadence,
community/announcement policy, GitHub flow, agent balance, or unrelated module history to
a sub-agent unless that detail changes its specific task.

Sub-agents should not read `CURRENT.md` or `COMPACT_CONTEXT.md` by default. Give them a
distilled task brief containing only the facts, risks, allowed paths, required skills, and
expected decision for their scope. Ask a worker to read or edit handoff files only when
handoff review/editing is its explicit ownership scope.

For lead or explicitly assigned integration turns, update these before finishing:

- `docs/agent-handoff/CURRENT.md` for short-lived active context.
- `docs/agent-handoff/COMPACT_CONTEXT.md` when the stable baseline or hard rules change.
- A dated research note under `docs/research/` for reusable evidence.
- `agent-skills/*/SKILL.md` when the way agents should work changes.

## Handoff Categories

Classify each transferred item:

- `fact`: directly observed and reproducible.
- `hypothesis`: plausible but not proven.
- `rejected`: tested and shown false or unsafe.
- `risk`: can crash servers, corrupt state, or mislead future agents.
- `next-step`: concrete action recommended for the next agent.
- `owner`: files or subsystem the agent was responsible for.

Do not pass vague claims as facts. Include evidence or mark them as hypotheses.

## Before Starting

1. If you are the lead after compaction, resume, or a new supervised round, read
   `docs/agent-handoff/CURRENT.md` and `docs/agent-handoff/COMPACT_CONTEXT.md`.
   For a narrow same-turn continuation, `CURRENT.md` is sufficient unless the task needs
   stable resume context.
2. Check `git status --short --ignored` unless the current instruction explicitly
   prohibits Git.
3. Identify your owned files and avoid editing outside that scope.
4. Read the relevant skills for the subsystem.
5. Note any stale or conflicting handoff state before changing files.
6. When delegating, distill only the relevant facts, risks, allowed paths, required skills,
   and expected decision for that agent's scope.

## Before Finishing

For sub-agents:

1. Report what changed, validation run, files touched, and remaining risks.
2. Add or update a research note only if that was inside the assigned ownership scope.
3. Do not commit, amend, rebase, tag, push, or update GitHub state.
4. Do not update handoff files unless the lead explicitly assigned that scope.
5. If you accidentally committed or pushed, say so explicitly in your final report with the
   commit hash and do no further GitHub operations.

For the lead:

1. Review and integrate sub-agent findings.
2. Update `docs/agent-handoff/CURRENT.md` with what changed.
3. Add or update research notes and skills when the evidence changes future behavior.
4. Commit locally only when the accumulated documentation/code is a useful stable
   checkpoint for contributors, release behavior, or integration. Push/GitHub publication
   is a separate lead-owned step and requires current direction that allows publication;
   release tags also require current release-manager/lead authorization and a fresh gate
   on the intended ref.
5. Report uncommitted files, skipped validation, and remaining risks.

## CURRENT.md Rules

Keep `CURRENT.md` concise. It is a routing table, not a full research log.

Good entries:

- `fact: Ragnarok core hook is stable with plugins disabled; see research note X.`
- `rejected: ProcessEvent candidate 0x1d11cb0 does not receive gameplay events.`
- `risk: raw FString scanning must stay off live Ragnarok.`
- `next-step: implement plugin-owned callback unregister before enabling plugins.`

Bad entries:

- Long pasted logs.
- Undated guesses.
- Claims without file paths, commits, logs, or reproduction context.
