---
name: obelisk-github-research-workflow
description: "Use for Obelisk lead-owned integration policy, scoped sub-agent coordination, publication boundaries, skill updates, ARK reverse-engineering research, and durable docs/research handoff."
---

# Obelisk GitHub Research Workflow

Use this skill for lead-owned integration, scoped agent rounds, publication boundaries,
or handoff policy. Do not hand it wholesale to sub-agents; pass only the rules that
change their concrete task. For ordinary research-note capture, use
`obelisk-continuous-learning` plus the relevant subsystem skill.

## Project Vision

Obelisk is being built as a Linux runtime with gated API/SDK surfaces for ARK modding.
Coordinate work toward a robust general modding substrate: UE4 reflection, safe runtime
hooks, stable C ABI, plugin lifecycle, install layout, live-ops safety, reproducible
reversing evidence, and public SDK promotion gates. Treat identity/principal,
permissions/admin, command response, chat, inventory, structures, buffs, dinos, tribes,
missions, transfers, and other module surfaces as areas on top of the same core, not as
the center of the project.

Treat `v1.0` stable as the complete public SDK contract for plugin authors, not just a
stable internal runtime. Use `docs/SDK_V1_COMPATIBILITY.md` and
`docs/public_sdk_surfaces.json` as the current surface map when planning promotion work,
while remembering that those documents are a planning contract until a release gate
packages or supersedes them.
Treat `docs/public_sdk_surfaces.json::v1_sdk_completion_blockers` as the lead-owned list
of high-demand blockers that prevent a complete v1 SDK claim. Installed-SDK examples are
contributor smoke/package-shape evidence only; they are not Plugin Hub work and cannot
declare v1 complete while blockers remain planning or post-v1. Plugin Hub work remains
post-SDK-complete. Explicitly excluded blockers require a reviewed v1 release
statement with scoped wording; exclusions do not permit claiming a complete SDK for the
excluded capability.

Compatibility research may consult ArkServerApi/AseApi and local NextGenPlugins clones
only as names and demand signals for familiar ARK plugin concepts. They are not architecture,
ergonomics, behavior, porting, or implementation sources. Obelisk must not copy ArkServerApi/AseApi,
NextGenPlugins, or other ArkApi plugin offsets, vtables, layouts, `.lib` artifacts,
MSVC/Windows ABI assumptions, direct
`GetNativePointerField`/`NativeCall` wrappers, raw UE pointer APIs, constants, schemas,
control flow, command parsers, return semantics, or algorithmic implementations; Linux
support is rebuilt from Obelisk reflection and ProcessEvent copied-data evidence.
Plugin Hub work is post-SDK-complete planning. Do not spend current rounds on
Plugin Hub-specific packaging, catalog/example packages, intake tooling, or package
hardening while the complete SDK blocker chain remains open, unless the user explicitly
asks to inspect archived planning. Current priority is the SDK itself:
identity/principal, permissions/admin, command/response, storage/mutation, gameplay
module surfaces, and their promotion evidence.
Identity/principal work must be blocker-driven and targeted: use the named lifecycle
anchors, evidence gaps, and runtime-capture preflight instead of broad rediscovery unless
a new binary/hash or explicit SDK blocker contradicts the current evidence. Structure
build-policy work defaults to offline snapshot/intake evidence before any runtime or
release-policy claim. Treat `ResourceHandle` and object identity/lifetime as a
cross-cutting SDK blocker for any surface that needs post-callback object correlation,
lookup, mutation, or persistent handles.

Keep leader-only strategy, cadence, and active goal text out of sub-agent prompts. Pass
only the blocker context that changes the agent's concrete task.

## Working Contract

- The team lead owns GitHub integration. Sub-agents must not commit, amend, rebase,
  tag, push, or update GitHub state unless the lead explicitly delegates that action for
  one turn.
- If a sub-agent commits or pushes without explicit delegation, treat it as a protocol
  violation even when the technical content is useful. The lead must audit the commit,
  record or correct the deviation, and restate ownership before launching more agents.
- Sub-agents deliver scoped file edits, evidence, validation output, and risks. The lead
  reviews, stages, commits, closes agents, updates shared handoff state, and may push
  only when publication is explicitly authorized for the current scope.
- Keep each commit focused: runtime code, docs, skills, or deployment scripts should not be
  mixed unless the change requires it.
- Batch small internal documentation, skill, handoff, and guardrail cleanups. Do not commit
  and push after every routine round; create a checkpoint when the accumulated work is
  useful to contributors, changes runtime/release behavior, or needs to be shared as a
  stable integration point.
- Push or delegate GitHub publication only for an evidenced, stable milestone after
  validation when it meets that usefulness threshold and handoff/user direction allows
  publication. Routine rounds, internal research, and unbatched guardrail edits should stay
  local.
- If current user direction or handoff state says GitHub publication is closed for the
  current work, do not run `git push`; report the validated local checkpoint state instead.
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

- After conversation compaction or a resumed Obelisk lead/integration turn, first read
  `docs/agent-handoff/COMPACT_CONTEXT.md` and `docs/agent-handoff/CURRENT.md`, then check
  `git status --short --ignored` before spawning or reusing agents unless the current
  instruction explicitly prohibits Git.
- Mandatory round preflight: at the start of every new supervised agent round, verify there
  are no stale stand-by agents from the previous round. Close completed or obsolete agents
  before spawning new ones, and record any still-active agent with a concrete
  polling/integration plan.
- Pass sub-agents only the context they need: task objective, ownership scope, files they
  may edit, files they must not edit, relevant skills to read, current safety baseline, and
  expected deliverable.
- Pass only the skills required by that task's scope. Do not send the full skill set to a
  sub-agent by default.
- Assign agents as scope experts, not generic helpers. Name the expert role in the task
  prompt, such as ABI/API engineer, UE4 reflection engineer, static binary analysis
  engineer, build/SDK engineer, live-ops engineer, or release-readiness auditor.
- Do not pass broad leader cadence, active goal wording, long-term strategy,
  community/announcement policy, commit flow, or unrelated module history unless that
  information changes the agent's concrete task.
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
  touched paths"; do not ask sub-agents to create integration checkpoints unless delegating
  GitHub for exactly that turn.
- Close old agents after their findings are integrated so stale context does not keep
  influencing new work.
- Follow explicit lead-provided routing only when it is included in the current task
  prompt.
- Relaunch agents after major skill updates when their next task depends on the new rules.
- Documentation/skills workers must not edit runtime C++ or `/servidor/ark` unless their
  prompt explicitly widens scope.
- The lead must remain the integration owner while agents are active. Do not end a
  supervised round by leaving active agents without a recorded handoff or polling plan.
- Reused agents are useful only if the platform preserves their context and they are still
  aligned with current skills. After major skill or research changes, relaunch fresh agents
  and give them the updated relevant skills plus a distilled handoff brief unless handoff
  review/editing is their explicit scope.
- Coordinate sub-agents directly with scoped ownership, safety baseline, allowed paths,
  required skills, expert role, and expected decision. Do not introduce separate
  repo-local task-queue machinery for this workflow.

## Long-Running Supervision

Codex should not promise autonomous development for hours without an active supervising
turn. Convert long-running work into:

- focused agent rounds with explicit owners,
- read-only cron snapshots,
- research notes,
- handoff updates,
- documented next actions.

Unattended automation must not commit, push, restart servers, change markers, run scanners,
or attach debuggers. It can collect status snapshots for the lead to review later.

## Lead Local Integration Flow

Only the lead runs this local integration flow:

```bash
git status --short --ignored
git diff --check
cmake --build build -j"$(nproc)"
git add <focused paths>
git diff --cached --stat
git commit -m "Short imperative summary"
```

Skip the build only for docs-only or skills-only commits, and say so in the final report.

Publication is a separate lead-only step. Run `git push` only when the current user
direction allows publication and the checkpoint is an evidenced, stable milestone. Release
tags additionally require a clean release gate on the intended ref and exact tag/ref
verification.

## Release Alignment

- Treat `scripts/check_release_readiness.sh` as the single release-readiness entry point.
  CI may keep fast build/test jobs, but install/package and SDK-completion validation
  should not drift into separate ad hoc CI commands with different defaults.
- For release gates that require second-source UFunction evidence, never trust a reused
  `/tmp` root by name. Smoke or regenerate the second-source root for the intended ref with
  current snapshot metadata, then pass that exact root to
  `scripts/check_release_readiness.sh --require-second-source-readiness`.
- When release-scope behavior changes, keep `docs/RELEASE.md`, `docs/STATUS.md`,
  `CHANGELOG.md`, `.github/pull_request_template.md`, and release-scope guardrail tests in
  agreement.
- Public release sinks such as README, changelog, release notes, GitHub release bodies,
  tag annotations, package metadata, installer text, community updates, and Plugin Hub
  planning must not use broad phrases like `v1.0 stable`, `complete SDK`, `full SDK`, or
  `production SDK` unless `scripts/check_public_sdk_v1_completion.py --json` reports the
  stable SDK claim is allowed. Otherwise the wording must be explicitly scoped as
  candidate, planning, RC, foundation, or post-v1.
- A local or unpublished RC tag does not validate publication. Before pushing a release
  tag, rerun the release gate on the intended ref and verify the tag dereferences exactly
  to that ref; resolve stale local tags instead of reusing or pushing them.
- Do not duplicate moving commit hashes as "latest checkpoint" facts in
  `docs/agent-handoff/CURRENT.md`; use `git log --oneline -1` for the current head and
  reserve handoff entries for stable facts, risks, and next steps.
- Prefer adding guardrail tests when fixing coordination drift so the same stale state does
  not return in later rounds.

## Discord Boundary

Do not draft or send Discord updates unless explicitly approved for the current turn.
Do not draft or send community announcements unless explicitly delegated. Endpoints are
operator secrets in ignored `local/discord-webhooks.env`; use only
`OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL` and `OBELISK_BETA_TEST_WEBHOOK_URL` variable
names. Use Discord only for major public, modder-facing milestones or operator-approved
beta-test windows. Never use Discord for routine validation, internal agent status,
speculative reversing notes, private live-ops detail, raw player text, or secrets.
Operators should prefer the guarded helper instead of hand-written webhook calls. Always
run `scripts/send_discord_embed.py --dry-run` first and send one concise professional
embed with title, description, status/scope, and 2-5 public-safe fields.

Example dry-run command: `python3 scripts/send_discord_embed.py --channel community --title "..." --description "..." --status "..." --scope "..." --field "Cambio=..." --field "Impacto=..."`.
After current-turn approval and dry-run review, repeat with `--confirm-approved-send
--approval-scope community` or `--approval-scope beta-test`; the approval scope must match `--channel`.

## Research And Skills

Use `docs/research/YYYY-MM-DD-topic.md` for non-trivial investigation and
`obelisk-continuous-learning` for research-note and skill-update criteria. Keep this
skill focused on lead-only integration, scoped delegation, publication boundaries, and
handoff policy.

## Release Promotion Gates

- Promotion PRs for reflected gameplay/module surfaces must name every promoted
  second-source target set explicitly. Do not treat the default minimal intake as a broad
  module promotion gate.
- Runtime-observer summaries are review artifacts only. Module-level field aggregates are
  not promotable layouts; new observer families need per-function analyzer fixture coverage
  and/or approved sanitized observer capture/research-note coverage before captures are
  accepted for review, then second-source/static evidence before promotion.
- Public docs, release notes, community updates, and Plugin Hub planning must not present
  Mission, Dino, Buff, Structure, or adjacent planning/internal evidence as public SDK
  availability unless the promoted surface names its target set and passes the required
  promotion gate. Use internal/planning/candidate wording for research-only module lanes.

## Pre-Push Checklist

- [ ] `git diff --check` is clean.
- [ ] Only intended files are staged.
- [ ] No binaries, logs, server config, or runtime state files are staged.
- [ ] Research findings that matter later are in `docs/research/`.
- [ ] Skills reflect new safety rules or workflow changes.
- [ ] Commit message explains the change without claiming unverified stability.
- [ ] Public-facing text was scanned for broad `v1.0 stable` / `complete SDK` / `full SDK`
      claims, and any such claim is backed by the v1 completion checker or scoped down.
