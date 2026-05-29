# Agent Handoff

This directory is the shared short-term memory for Obelisk agents.

Use it for active state and coordination. Use `docs/research/` for detailed evidence and
longer investigation notes.

## Files

- `CURRENT.md`: current state, risks, blockers, and next steps.
- `COMPACT_CONTEXT.md`: compact resume baseline for context compaction or a fresh lead
  session.
- `HISTORY-*.md`: archived handoff snapshots kept only to preserve older coordination
  detail after compaction. Do not use history files as the active source of truth.

These files are internal coordination notes for agents and the project lead. Public
contributor workflow belongs in `CONTRIBUTING.md`.

When assigning sub-agent work, use these files to extract only the scoped facts, risks,
allowed paths, required skills, and expected decision. Do not copy the full active
objective, agent balance, GitHub flow, Discord policy, or unrelated module history into
default sub-agent prompts.

## Rules

- Keep entries concise and dated.
- Mark each item as `fact`, `hypothesis`, `rejected`, `risk`, or `next-step`.
- Reference commits, files, logs, or research notes when possible.
- Do not paste raw logs here.
- The lead updates the relevant handoff file before closing an agent or handing work to
  another agent. Sub-agents report status and touched paths unless handoff edits are
  explicitly delegated.
- Keep `CURRENT.md` as a routing table. Move durable evidence to `docs/research/` and
  archive stale handoff detail instead of letting active state grow into a research log.
