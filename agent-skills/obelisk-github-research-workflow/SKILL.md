---
name: obelisk-github-research-workflow
description: "Use when leading Obelisk toward production stability through supervised agent coordination, GitHub checkpoints, skill updates, ARK reverse-engineering research, and durable docs/research handoff."
---

# Obelisk GitHub Research Workflow

Use this skill when an Obelisk task involves GitHub hygiene, agent handoff, research notes,
skill updates, or making work reproducible for contributors.

## Project Vision

Obelisk is a Linux runtime/API/SDK core for ARK modding. Coordinate work toward a robust
general modding substrate: UE4 reflection, safe runtime hooks, stable C ABI, plugin
lifecycle, install layout, live-ops safety, reproducible reversing evidence, and public SDK
promotion gates. Treat chat, inventory, structures, buffs, dinos, tribes, missions,
transfers, and admin surfaces as module areas on top of the same core, not as the center of
the project.

Keep leader-only strategy, cadence, and active goal text outside this skill. The active
leader objective belongs in the goal tool and short-lived handoff state, not in prompts sent
to every sub-agent.

## Working Contract

- The team lead owns GitHub integration. Sub-agents must not commit, amend, rebase,
  tag, push, or update GitHub state unless the lead explicitly delegates that action for
  one turn.
- If a sub-agent commits or pushes without explicit delegation, treat it as a protocol
  violation even when the technical content is useful. The lead must audit the commit,
  record or correct the deviation, and restate ownership before launching more agents.
- Sub-agents deliver scoped file edits, evidence, validation output, and risks. The lead
  reviews, stages, commits, pushes, closes agents, and updates shared handoff state.
- Keep each commit focused: runtime code, docs, skills, or deployment scripts should not be
  mixed unless the change requires it.
- Push stable checkpoints to `origin/main` after validation.
- Do not commit server artifacts: `.so`, logs, core files, local configs, state markers, or
  build directories.
- Server restore documentation is allowed, but never stage copied `/servidor/ark` config
  files themselves. Link to `docs/SERVER_RESTORE.md` instead.
- If a discovery changes how future agents should work, update the relevant
  `agent-skills/*/SKILL.md` in the same or next commit.
- If a discovery is not ready for code, write it under `docs/research/`.
- Research notes that depend on server behavior should record instance id, map, binary
  hash, runtime flags, and active instance markers.

## Agent Coordination

- Mandatory round preflight: at the start of every new supervised agent round, verify there
  are no stale stand-by agents from the previous round. Close completed or obsolete agents
  before spawning new ones, and record any still-active agent with a concrete
  polling/integration plan.
- Pass sub-agents only the context they need: task objective, ownership scope, files they
  may edit, files they must not edit, relevant skills to read, current safety baseline, and
  expected deliverable.
- Do not pass broad leader cadence, long-term goal wording, Discord policy, commit flow, or
  unrelated module history unless that information changes the agent's concrete task.
- Before spawning agents, define disjoint ownership:
  - runtime/core: hooks, loader, EventManager, PluginManager, ABI
  - reversing/research: FName, GNames, GObjects, UFunction, event decoding experiments
  - ops/docs: install layout, server markers, logs, research notes, contributor docs
- Separate agents by expert focus, not only by file paths. Examples:
  - ABI/API engineer owns public headers, plugin entry points, layout assertions, and ABI docs.
  - Build/SDK engineer owns CMake targets, install/include layout, examples, and package shape.
  - UE4 reflection engineer owns FName/GNames/GObjects/UFunction research and analyzers.
  - Live-ops engineer owns `/servidor/ark`, wrappers, markers, backups, and rollback notes.
- Do not assign two editing agents to the same focus area in the same round. If two tasks
  need the same shared file such as `CMakeLists.txt`, `.github/workflows/ci.yml`, or
  `include/obelisk/ObeliskApi.h`, make one agent read-only or sequence the work in
  separate rounds.
- If shared-file edits are unavoidable, name a single integration owner. Other agents should
  return plans or patches scoped to their own files instead of editing the shared file.
- Tell agents whether they may edit files. Read-only reviewers should not change the tree.
- Tell agents they must not manage GitHub. They may leave working-tree changes in their
  owned scope, but the lead is the only integration owner.
- In agent prompts, prefer explicit wording: "leave changes unstaged/uncommitted and report
  touched paths"; do not ask sub-agents to create "stable commits" unless delegating GitHub
  for exactly that turn.
- Close old agents after their findings are integrated so stale context does not keep
  influencing new work.
- Relaunch agents after major skill updates when their next task depends on the new rules.
- Documentation/skills workers must not edit runtime C++ or `/servidor/ark` unless their
  prompt explicitly widens scope.
- The lead must remain the integration owner while agents are active. Do not end a
  supervised round by leaving active agents without a recorded handoff or polling plan.
- Reused agents are useful only if the platform preserves their context and they are still
  aligned with current skills. After major skill or research changes, relaunch fresh agents
  and make them read the updated handoff/skills.

## Long-Running Supervision

Codex should not promise autonomous development for hours without an active supervising
turn. Convert long-running work into:

- focused agent rounds with explicit owners,
- read-only cron snapshots,
- research notes,
- handoff updates,
- queued next tasks.

Unattended automation must not commit, push, restart servers, change markers, run scanners,
or attach debuggers. It can collect status snapshots for the lead to review later.

## Lead Commit Flow

Only the lead runs this flow:

```bash
git status --short --ignored
git diff --check
cmake --build build -j"$(nproc)"
git add <focused paths>
git diff --cached --stat
git commit -m "Short imperative summary"
git push origin main
```

Skip the build only for docs-only or skills-only commits, and say so in the final report.

## Community Discord Updates

Do not send Discord updates for routine commits, internal validation, research bookkeeping,
agent coordination, refactors, or developer-only checkpoints.

Send a short community update to the configured Obelisk Discord webhook only when a change
is important to future mod creators using the Obelisk core. The audience is modders and
server/plugin creators, not the internal development team.

Examples that qualify:

- a new or meaningfully expanded public SDK/API capability;
- a major runtime safety or compatibility milestone that affects plugin authors;
- a documented module surface becoming ready for external experimentation;
- a release, preview, migration notice, or breaking/important behavior change.

Examples that do not qualify:

- docs-only research notes;
- internal recognizers that remain candidate-only;
- fixture regeneration, guardrail updates, benchmark/test-only work;
- ordinary commits, pushes, validations, or agent round summaries.

Update style:

- Use Markdown.
- Write for mod creators who will build against Obelisk.
- Focus on what they can eventually use, test, migrate to, or rely on.
- Keep validation details brief and only include them when they explain confidence or
  compatibility.
- Do not publish secrets, player chat contents, private server details, full logs, core
  paths, or sensitive operational data.
- Be explicit when something is experimental, gated, not deployed, or not yet public SDK.

Suggested shape:

```text
**Obelisk Dev Update**

<1-2 short paragraphs about what changed for mod creators and why it matters.>

**For modders:** <what is available, experimental, or coming next>
```

## Research Notes

Use `docs/research/YYYY-MM-DD-topic.md` for non-trivial investigation.

Every note should include:

- Objective
- Environment: ARK binary path, SHA256, map/server, Obelisk commit, plugins state
- Hypothesis
- Evidence: logs, addresses, signatures, command output summaries
- Result: confirmed, rejected, or inconclusive
- Risks
- Next steps

Do not paste huge logs. Summarize the signal and link or name the log file.

## Skill Update Rules

Update skills when:

- a previous instruction becomes unsafe or false
- a new stable workflow exists
- a new live-server safety rule is discovered
- an offset/signature is accepted or rejected with evidence
- contributor workflow changes

Keep skills short and operational. Put detailed experiment records in `docs/research/`.

## Release Promotion Gates

- Promotion PRs for reflected gameplay/module surfaces must name every promoted
  second-source target set explicitly. Do not treat the default minimal intake as a broad
  module promotion gate.
- Runtime-observer summaries are review artifacts only. Module-level field aggregates are
  not promotable layouts; new observer families need per-function analyzer fixture coverage
  and/or supervisor snapshot coverage before captures are accepted for review, then
  second-source/static evidence before promotion.

## Pre-Push Checklist

- [ ] `git diff --check` is clean.
- [ ] Only intended files are staged.
- [ ] No binaries, logs, server config, or runtime state files are staged.
- [ ] Research findings that matter later are in `docs/research/`.
- [ ] Skills reflect new safety rules or workflow changes.
- [ ] Commit message explains the change without claiming unverified stability.
