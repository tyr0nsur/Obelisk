---
name: obelisk-github-research-workflow
description: Use when coordinating Obelisk agents that should commit to GitHub, improve their own skills, and document reverse-engineering or runtime findings under docs/research.
---

# Obelisk GitHub Research Workflow

Use this skill when an Obelisk task involves GitHub hygiene, agent handoff, research notes,
skill updates, or making work reproducible for contributors.

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
  `api/ObeliskApi.h`, make one agent read-only or sequence the work in separate rounds.
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

## Pre-Push Checklist

- [ ] `git diff --check` is clean.
- [ ] Only intended files are staged.
- [ ] No binaries, logs, server config, or runtime state files are staged.
- [ ] Research findings that matter later are in `docs/research/`.
- [ ] Skills reflect new safety rules or workflow changes.
- [ ] Commit message explains the change without claiming unverified stability.
