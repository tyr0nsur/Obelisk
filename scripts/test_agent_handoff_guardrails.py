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
MAX_CURRENT_LINES = 220


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


if __name__ == "__main__":
    unittest.main()
