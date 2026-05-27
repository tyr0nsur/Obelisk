---
name: obelisk-agent-handoff
description: Use when Obelisk work is delegated between agents and they need to transfer valuable context through repo files, current state notes, and structured handoff updates.
---

# Obelisk Agent Handoff

Use this skill whenever multiple agents work on Obelisk or when a task may continue in a
later session.

## Shared Memory Files

Read these before starting delegated work:

- `docs/agent-handoff/CURRENT.md`: current active state, blockers, next tasks.
- `docs/agent-handoff/COMPACT_CONTEXT.md`: compact resume state after long sessions.
- `docs/research/`: durable investigation notes and evidence.
- `docs/SERVER_RESTORE.md`: recovery flow for ARK config after SteamCMD/LinuxGSM rewrites.
- `agent-skills/`: operational rules that future agents must follow.

Update these before finishing:

- `docs/agent-handoff/CURRENT.md` for short-lived active context.
- `docs/agent-handoff/COMPACT_CONTEXT.md` when the stable baseline or hard rules change.
- `docs/research/YYYY-MM-DD-topic.md` for reusable evidence.
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

1. Read `docs/agent-handoff/CURRENT.md`.
2. Check `git status --short --ignored`.
3. Identify your owned files and avoid editing outside that scope.
4. Read the relevant skills for the subsystem.
5. Note any stale or conflicting handoff state before changing files.

## Before Finishing

1. Update `docs/agent-handoff/CURRENT.md` with what changed.
2. Add or update a research note if the work produced reusable evidence.
3. Update skills if a rule, risk, or workflow changed.
4. Commit and push stable documentation/code when appropriate.
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
