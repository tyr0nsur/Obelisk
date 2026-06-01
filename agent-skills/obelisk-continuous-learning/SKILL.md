---
name: obelisk-continuous-learning
description: "Use when Obelisk agents should turn investigations into durable knowledge by updating research notes, revising skills, recording rejected hypotheses, and preserving evidence for future agents."
---

# Obelisk Continuous Learning

Use this skill after investigations, debugging sessions, live-server experiments, reverse
engineering work, or failed attempts that teach something useful.

## Learning Loop

Every serious investigation or explicitly assigned docs/research task should end with one
of these outcomes:

- Code change with tests or live validation.
- Research note under `docs/research/`.
- Skill update under `agent-skills/`.
- Explicit rejected hypothesis documented so future agents do not repeat it.

If the finding changes how agents should behave, update a skill. If it only records one
experiment or evidence trail, update `docs/research/`.
If a skill update changes release, publication, safety, or promotion policy, add or update
a guardrail test in the same checkpoint, or explicitly document why the rule is not
machine-checkable.

Adopted knowledge should not remain only in chat or an agent result. Promote it to the
smallest durable place that will help the next worker:

- skill rule when it changes repeatable behavior;
- research note when it records evidence, rejected hypotheses, or a design investigation;
- active handoff only when it changes the next turn's routing or immediate priorities.

Learning/documentation rounds leave changes local and unpublished unless the current turn
explicitly authorizes publication. Do not push, tag, or publish release refs without
current lead/release-manager direction and matching validation evidence.

Keep the promoted form concise. Avoid copying full agent transcripts, leader cadence, or
coordination chatter into skills or contributor docs.

Sub-agents may recommend skill changes in their final report or in an assigned research
note. An explicitly assigned docs/skills worker may edit the named skill files; otherwise
the lead owns process-rule edits and publication. Leave changes unstaged/uncommitted
unless the current turn says otherwise.

## What To Capture

Capture facts that are expensive to rediscover:

- ARK binary path and SHA256.
- Map/server tested.
- Obelisk commit.
- Environment variables and state markers.
- Exact addresses, signatures, offsets, and why they are trusted or rejected.
- Logs that prove a hook loaded, a plugin crashed, or an event was observed.
- Negative results, especially false positives like bad ProcessEvent candidates.

Do not capture speculation as fact. Label uncertain findings as hypotheses.

## Evidence Packs

For any accepted or promoted offset, signature, global, UE4 type field, or hook target,
capture an evidence pack before code promotion:

- binary path and SHA256,
- Obelisk commit and build type,
- exact commands or scripts used,
- static xrefs or runtime log lines supporting the claim,
- reject conditions and known false positives checked,
- second-source validation plan or result,
- rollback/safety posture if runtime probing was involved.

If an evidence pack is incomplete, mark the result as `hypothesis` or
`research-candidate`, not `fact`.

## Research Note Pattern

Create or update:

```text
docs/research/YYYY-MM-DD-topic.md
```

Use `docs/research/README.md` as the canonical template. Keep raw logs out of Git;
summarize the important lines and reference local paths.

## Skill Update Pattern

The lead, or an explicitly assigned docs/skills worker, updates `agent-skills/` when a
research result changes future behavior:

- `obelisk-core-runtime`: runtime safety, plugin lifecycle, API ownership.
- `obelisk-linux-hooking`: hook mechanism, trampolines, memory protection.
- `obelisk-ue4-reversing`: signatures, offsets, binary validation.
- `obelisk-ue4-reflection`: FName, GNames, GObjects, UFunction, params.
- `obelisk-static-binary-analysis`: offline ELF analysis, objdump/Ghidra/rizin evidence,
  and candidate promotion gates.
- `obelisk-ue4-type-reconstruction`: UE4 type field reconstruction and promotion rules.
- `obelisk-tooling-discipline`: safe tool selection for offline, isolated-debug, and live
  contexts.
- `obelisk-reversing-research`: active research strategy and unsafe experiments.
- `obelisk-live-ops`: production server operation and rollback.
- `obelisk-github-research-workflow`: lead-only integration, scoped delegation,
  publication boundaries, and handoff policy.

Keep skills operational and short. Move detailed experiment logs to `docs/research/`.

Use this escalation rule:

- New evidence about one experiment: write or update `docs/research/`.
- New repeatable workflow or safety rule: update the relevant `agent-skills/*/SKILL.md`.
- New team coordination rule: update `obelisk-github-research-workflow` or
  `obelisk-agent-handoff`.
- Uncertain idea: record as a `hypothesis` in research notes, not as a skill rule.

## Agent Handoff

When handing work to another agent, include:

- Current objective.
- Files they own.
- What they must not edit.
- Current stable baseline.
- Known false positives and unsafe flags.
- Where to write research notes.

After the agent returns, integrate useful findings into skills or research notes before
starting a new round.

## End-of-Turn Checklist

- [ ] Did this work produce a reusable fact?
- [ ] Did any previous instruction become unsafe, stale, or false?
- [ ] Is there a rejected hypothesis worth saving?
- [ ] Did a sub-agent suggest a skill update that must be accepted, rejected, or deferred?
- [ ] Did a live-server rule change?
- [ ] Did a release, publication, safety, or promotion policy skill change also update a
      guardrail test, or record why no machine check applies?
- [ ] Did a long-running or unattended workflow get reduced to read-only snapshots plus
      explicit next actions?
- [ ] Did the relevant skill get updated?
- [ ] Did `docs/research/` get updated when the evidence is too detailed for a skill?
- [ ] Are changes intentionally batched for later lead integration, or ready for the lead
      to checkpoint?
