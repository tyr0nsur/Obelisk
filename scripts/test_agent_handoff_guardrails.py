#!/usr/bin/env python3
"""Guardrails for Obelisk agent handoff files."""

from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HANDOFF_DIR = REPO_ROOT / "docs" / "agent-handoff"
CURRENT = HANDOFF_DIR / "CURRENT.md"
README = HANDOFF_DIR / "README.md"
COMPACT_CONTEXT = HANDOFF_DIR / "COMPACT_CONTEXT.md"
GITHUB_WORKFLOW_SKILL = REPO_ROOT / "agent-skills" / "obelisk-github-research-workflow" / "SKILL.md"
MAX_CURRENT_LINES = 220
MAX_SKILL_LINES = 260


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
        self.assertIn("standing debug approval", current)
        self.assertIn("standing operator approval for Obelisk debug/development tests", compact)
        self.assertIn("server-safety decisions", current)
        self.assertIn("two on Obelisk engineering/audit/development", current)
        self.assertIn("on research/knowledge/reversing/dump", current)
        self.assertIn("two on Obelisk engineering/audit/development", compact)
        self.assertIn("four on research/knowledge/reversing/dump", workflow_skill)

        self.assertIn("documented next actions", workflow_skill)
        self.assertNotIn("queued next tasks", workflow_skill)

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
