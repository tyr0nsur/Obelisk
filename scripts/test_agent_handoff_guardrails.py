#!/usr/bin/env python3
"""Guardrails for Obelisk agent handoff files."""

from __future__ import annotations

import unittest
from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
HANDOFF_DIR = REPO_ROOT / "docs" / "agent-handoff"
CURRENT = HANDOFF_DIR / "CURRENT.md"
README = HANDOFF_DIR / "README.md"
COMPACT_CONTEXT = HANDOFF_DIR / "COMPACT_CONTEXT.md"
GITHUB_WORKFLOW_SKILL = REPO_ROOT / "agent-skills" / "obelisk-github-research-workflow" / "SKILL.md"
REVERSING_RESEARCH_SKILL = REPO_ROOT / "agent-skills" / "obelisk-reversing-research" / "SKILL.md"
MAX_CURRENT_LINES = 220
MAX_SKILL_LINES = 260
SCOPED_GUARDRAIL_FILES = [
    CURRENT,
    COMPACT_CONTEXT,
    REPO_ROOT / "docs" / "research" / "2026-05-30-mission-copied-bool-observer-plan.md",
    REPO_ROOT / "scripts" / "test_release_scope_guardrails.py",
    REPO_ROOT / "scripts" / "test_agent_handoff_guardrails.py",
    REPO_ROOT / "scripts" / "test_send_discord_embed.py",
]


def normalized(text: str) -> str:
    return " ".join(text.split())


class AgentHandoffGuardrailsTests(unittest.TestCase):
    def test_current_stays_concise_routing_table(self) -> None:
        text = CURRENT.read_text(encoding="utf-8")
        line_count = len(text.splitlines())
        self.assertLessEqual(
            line_count,
            MAX_CURRENT_LINES,
            "CURRENT.md should remain a concise routing table; move detail to docs/research/ "
            "or docs/agent-handoff/HISTORY-*.md",
        )
        self.assertIn("active routing table", text)
        self.assertIn("Priority Next Steps", text)
        self.assertIn("Agent Protocol", text)
        self.assertNotIn(
            "latest pushed checkpoint",
            text,
            "CURRENT.md should not duplicate the moving HEAD hash; use git log instead",
        )
        try:
            priority = text.split("## Priority Next Steps", 1)[1].split("## Agent Protocol", 1)[0]
        except IndexError:
            self.fail("CURRENT.md must include Priority Next Steps before Agent Protocol")
        priority_items = [line.strip() for line in priority.splitlines() if line.startswith("- ")]
        self.assertEqual(
            len(priority_items),
            len(set(priority_items)),
            "Priority Next Steps should not contain duplicate top-level routing items",
        )

    def test_handoff_history_files_are_archives(self) -> None:
        history_files = sorted(HANDOFF_DIR.glob("HISTORY-*.md"))
        self.assertTrue(history_files, "expected at least one archived handoff history file")
        for path in history_files:
            text = path.read_text(encoding="utf-8")
            self.assertIn("preserves the full `docs/agent-handoff/CURRENT.md` content", text)
            self.assertIn("before", text)

    def test_docs_point_agents_to_current_not_history(self) -> None:
        readme = README.read_text(encoding="utf-8")
        compact = COMPACT_CONTEXT.read_text(encoding="utf-8")
        self.assertIn("Do not use history files as the active source of truth", readme)
        self.assertIn("Current routing table only", compact)

    def test_direct_subagent_handoff_keeps_lead_integration_boundary(self) -> None:
        readme = README.read_text(encoding="utf-8")
        current = CURRENT.read_text(encoding="utf-8")
        compact = COMPACT_CONTEXT.read_text(encoding="utf-8")
        workflow_skill = GITHUB_WORKFLOW_SKILL.read_text(encoding="utf-8")

        retired_terms = (
            "EXTERNAL" + "_AGENT" + "_QUEUE",
            "agent" + "_task" + "_queue",
            ".obelisk" + "-agent" + "-queue",
            "external " + "queue",
            "external " + "coordinator",
            "stale" + "-after",
        )
        for text in (readme, current, compact, workflow_skill):
            for term in retired_terms:
                self.assertNotIn(term, text)

        for text in (current, compact):
            self.assertIn("scoped", text)
            self.assertIn("safety", text)
            self.assertIn("baseline", text)
            self.assertIn("allowed paths", text)
            self.assertIn("required skills", text)
            self.assertIn("expert role", text)
            self.assertIn("expected decision", text)
            self.assertIn("sub-agent", text)
        for text in (current, compact):
            lowered = text.lower()
            self.assertIn("only the skills", lowered)
            self.assertIn("sub-agents", lowered)
            self.assertIn("expert", lowered)
        self.assertIn("GitHub work may be delegated only for an evidenced, stable milestone", current)
        self.assertNotIn("forbids GitHub pushes", current)
        self.assertNotIn("Do not push unless the operator reopens pushing", current)
        self.assertIn("No server target has standing approval", " ".join(current.split()))
        self.assertIn("Technical progress is only a reason to request a scoped run", " ".join(current.split()))
        self.assertIn("No standing operator approval for Obelisk debug/development or beta tests", compact)
        self.assertIn("server-safety decisions", current)
        normalized_workflow = normalized(workflow_skill)
        self.assertRegex(normalized_workflow, r"Follow explicit .* routing only")
        for text in (current, compact, workflow_skill):
            self.assertNotIn("two on Obelisk engineering/audit/development", text)
            self.assertNotIn("four on research/knowledge/reversing/dump", text)
            self.assertNotIn("six-agent split", text)
            self.assertNotIn("local critical-path task", text)
            self.assertNotIn("parallel sub-agents", text)
            self.assertIsNone(re.search(r"\b\d+\s+tests passed\b", text))

        self.assertRegex(normalized_workflow, r"(documented|recorded) next actions")
        self.assertNotIn("queued next tasks", workflow_skill)

    def test_discord_policy_stays_embed_helper_and_approval_scoped(self) -> None:
        current = CURRENT.read_text(encoding="utf-8")
        workflow_skill = GITHUB_WORKFLOW_SKILL.read_text(encoding="utf-8")

        for path, text in (
            ("docs/agent-handoff/CURRENT.md", current),
            ("agent-skills/obelisk-github-research-workflow/SKILL.md", workflow_skill),
        ):
            with self.subTest(file=path, item="webhook variables only"):
                self.assertIn("OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL", text)
                self.assertIn("OBELISK_BETA_TEST_WEBHOOK_URL", text)
                self.assertNotIn("discord.com/" + "api/webhooks", text)
                self.assertNotIn("discordapp.com/" + "api/webhooks", text)
            with self.subTest(file=path, item="approval scope"):
                self.assertIn("approved", text)
                self.assertIn("public", text)
                self.assertIn("modder-facing", text)
                self.assertIn("milestones", text)
                self.assertIn("beta-test", text)
            with self.subTest(file=path, item="embed shape"):
                lowered = text.lower()
                self.assertIn("embed", lowered)
                self.assertIn("routine validation", lowered)
                self.assertIn("speculative", lowered)

        normalized_workflow = normalized(workflow_skill)
        self.assertIn("Do not draft or send Discord updates unless explicitly approved", workflow_skill)
        self.assertIn("Do not draft or send community announcements unless explicitly delegated", workflow_skill)
        self.assertIn("Always dry-run before any approved send", current)
        self.assertIn("prefer the guarded helper instead of hand-written", workflow_skill)
        self.assertIn("python3 scripts/send_discord_embed.py --channel community", workflow_skill)
        self.assertIn("--confirm-approved-send", workflow_skill)
        self.assertIn("--approval-scope community", workflow_skill)
        self.assertIn("--approval-scope beta-test", workflow_skill)
        self.assertRegex(normalized_workflow, r"run .*send_discord_embed\.py --dry-run.*first")
        self.assertRegex(normalized_workflow, r"approved .* current turn|current-turn approval")

    def test_scoped_guardrail_files_do_not_store_secret_webhook_urls(self) -> None:
        forbidden_literals = [
            "discord.com/" + "api/webhooks",
            "discordapp.com/" + "api/webhooks",
            "https://" + "discord.com",
            "https://" + "discordapp.com",
            "OBELISK_COMMUNITY_UPDATES_WEBHOOK_URL" + "=",
            "OBELISK_BETA_TEST_WEBHOOK_URL" + "=",
        ]

        for path in SCOPED_GUARDRAIL_FILES:
            text = path.read_text(encoding="utf-8")
            for literal in forbidden_literals:
                with self.subTest(file=str(path.relative_to(REPO_ROOT)), literal=literal):
                    self.assertNotIn(literal, text)

    def test_scoped_guardrail_files_do_not_authorize_real_servers_or_discord(self) -> None:
        current = CURRENT.read_text(encoding="utf-8")
        compact = COMPACT_CONTEXT.read_text(encoding="utf-8")
        mission_plan = (REPO_ROOT / "docs" / "research" / "2026-05-30-mission-copied-bool-observer-plan.md").read_text(
            encoding="utf-8"
        )
        send_discord_tests = (REPO_ROOT / "scripts" / "test_send_discord_embed.py").read_text(encoding="utf-8")

        self.assertIn("No server target has standing approval", " ".join(current.split()))
        self.assertIn("no Discord for internal rounds or agent status", " ".join(current.split()))
        self.assertIn("No standing operator approval", compact)
        self.assertIn("No run is approved by this note", mission_plan)
        self.assertIn("This plan is not approval to add or enable gates", mission_plan)
        self.assertNotIn("arkserver " + "ventana aprobada", send_discord_tests)

    def test_call_process_event_handoff_stays_owner_scoped_init_window_only(self) -> None:
        for path in (CURRENT, COMPACT_CONTEXT):
            text = normalized(path.read_text(encoding="utf-8"))
            with self.subTest(file=str(path.relative_to(REPO_ROOT))):
                self.assertIn("CallProcessEvent", text)
                self.assertIn("init-window debug escape hatch", text)
                self.assertRegex(
                    text,
                    r"(current plugin owner is inside|calling plugin is currently inside) `?ObeliskPlugin_Init`?",
                )
                self.assertIn("OBELISK_API_CAPABILITY_CALL_PROCESS_EVENT", text)
                self.assertIn("Post-init calls through captured API tables", text)
                self.assertRegex(text, r"future .* owner[- ]token ABI|future replacement must carry an owner token")
                self.assertNotRegex(text, r"\bglobal CallProcessEvent\b")
                self.assertNotRegex(text, r"\bCallProcessEvent (?:is |remains |stays )?(?:global|ownerless|unowned)\b")
                self.assertNotRegex(text, r"\bCallProcessEvent\b.{0,80}\b(?:not owner[- ]scoped|no owner scope)\b")
                self.assertNotRegex(text, r"\bpost-init CallProcessEvent\b.{0,80}\b(?:supported|allowed|callable)\b")

    def test_resourcehandle_followup_does_not_restart_broad_scans(self) -> None:
        current = normalized(CURRENT.read_text(encoding="utf-8"))
        compact = normalized(COMPACT_CONTEXT.read_text(encoding="utf-8"))
        reversing_skill = normalized(REVERSING_RESEARCH_SKILL.read_text(encoding="utf-8"))

        for text in (current, compact, reversing_skill):
            self.assertIn("ResourceHandle", text)
            self.assertRegex(text, r"broad (FName, GObjects, or core scans|FName, GObjects, or core scan)")
        self.assertIn("rejected runtime object samples", reversing_skill)
        self.assertIn("runtime serial reuse/wraparound semantics", reversing_skill)

    def test_release_handoff_routing_stays_post_f33dc34_aligned(self) -> None:
        current = normalized(CURRENT.read_text(encoding="utf-8"))
        compact = normalized(COMPACT_CONTEXT.read_text(encoding="utf-8"))
        readme = normalized((REPO_ROOT / "README.md").read_text(encoding="utf-8"))
        status = normalized((REPO_ROOT / "docs" / "STATUS.md").read_text(encoding="utf-8"))

        for text in (current, compact, readme, status):
            self.assertIn("Plugin Hub", text)
        for text in (current, readme, status):
            self.assertRegex(text, r"v1(?:\.0)? .*complete|complete .*v1")
            self.assertRegex(text, r"blocked|not .*claim|not .*authorize")

        self.assertIn("post-SDK-complete planning only", current)
        self.assertIn("post-SDK-complete planning only", readme)
        self.assertIn("post-SDK-complete planning only", status)
        self.assertIn("archived boundaries only until SDK completion", compact)
        self.assertNotIn("Plugin Hub seed review requires", compact)

        for text in (current, readme, status):
            self.assertIn("approved copied runtime principal lifecycle evidence", text)
        self.assertIn("approved copied runtime principal lifecycle evidence", compact)
        self.assertNotIn("Current identity next step is accepted login/logout", current)
        self.assertNotIn("stays blocked on lifecycle-anchor evidence unless", current)

        for text in (current, readme):
            self.assertIn("rejected runtime object samples", text)
            self.assertIn("runtime serial reuse/wraparound semantics", text)
        self.assertIn("rejected object samples plus runtime serial reuse/wraparound semantics", status)

    def test_player_identity_focal_plans_require_exact_targets(self) -> None:
        current = normalized(CURRENT.read_text(encoding="utf-8"))
        compact = normalized(COMPACT_CONTEXT.read_text(encoding="utf-8"))
        obsolete_plan = (
            "scripts/plan_ufunction_focal_snapshots.py "
            "--target-set players-identity-lifecycle-intake"
        )

        for text in (current, compact):
            self.assertIn("12-target `players-identity-lifecycle-intake`", text)
            self.assertIn("ShooterPlayerController.ServerListPlayers", text)
            self.assertIn("ShooterPlayerController.ServerKickPlayer", text)
            self.assertIn("exact", text)
            self.assertNotIn(obsolete_plan, text)

    def test_learning_skill_keeps_adopted_knowledge_compact(self) -> None:
        skill = (REPO_ROOT / "agent-skills/obelisk-continuous-learning/SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertLessEqual(len(skill.splitlines()), MAX_SKILL_LINES)
        self.assertIn("Adopted knowledge should not remain only in chat or an agent result", skill)
        self.assertIn("smallest durable place", skill)
        self.assertIn("skill rule when it changes repeatable behavior", skill)
        self.assertIn("research note when it records evidence", skill)
        self.assertIn("active handoff only when it changes the next turn's routing", skill)
        self.assertIn("Keep the promoted form concise", skill)
        self.assertIn("Avoid copying full agent transcripts", skill)


if __name__ == "__main__":
    unittest.main()
