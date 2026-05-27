#!/usr/bin/env python3
"""Guardrails for Obelisk research docs that encode live-server safety rules."""

from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class ResearchDocGuardrailTests(unittest.TestCase):
    def test_no_obsolete_theisland_second_core_runbook_references(self) -> None:
        forbidden = [
            "theisland-second-core",
            "TheIsland second core",
            "run the existing isolated capture runbook only against\n",
            "0x12d1400 group is the best next decompiler target",
        ]
        offenders: list[str] = []
        for path in (REPO_ROOT / "docs").rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            for phrase in forbidden:
                if phrase in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {phrase}")

        self.assertEqual(offenders, [])

    def test_second_core_runbook_prefers_dedicated_debug_instance(self) -> None:
        runbook = REPO_ROOT / "docs/research/2026-05-27-isolated-second-core-runbook.md"
        text = runbook.read_text(encoding="utf-8")

        self.assertIn("Preferred target:", text)
        self.assertIn("arkserver-obelisk-debug", text)
        self.assertIn("Fallback target:", text)
        self.assertIn("arkserver2", text)
        self.assertIn("Protected target:", text)
        self.assertIn("arkserver` / Ragnarok", text)

    def test_historical_core_dump_runbook_is_not_ragnarok_executable(self) -> None:
        runbook = REPO_ROOT / "docs/research/2026-05-27-arkserver-core-dump-runbook.md"
        text = runbook.read_text(encoding="utf-8")

        self.assertIn("Historical runbook", text)
        self.assertIn("arkserver-obelisk-debug", text)
        self.assertNotIn("/servidor/ark/arkserver restart", text)
        self.assertNotIn("state/instances/arkserver/allow-ptrace", text)
        self.assertNotIn("ShooterGameServer Ragnarok", text)

    def test_runtime_debug_control_prefers_dedicated_debug_instance(self) -> None:
        runbook = REPO_ROOT / "docs/research/2026-05-27-runtime-debug-control.md"
        text = runbook.read_text(encoding="utf-8")

        self.assertIn("arkserver-obelisk-debug", text)
        self.assertNotIn("/servidor/ark/arkserver restart", text)
        self.assertNotIn("state/instances/arkserver/enable-debug-control", text)

    def test_reflectionscanner_runbook_separates_debug_and_theisland_fallback(self) -> None:
        runbook = REPO_ROOT / "docs/research/2026-05-27-reflectionscanner-isolated-capture-runbook.md"
        text = runbook.read_text(encoding="utf-8")

        self.assertIn("Preferred dedicated-debug profile", text)
        self.assertIn("Fallback TheIsland profile", text)
        self.assertIn("only with explicit operator approval", text)
        self.assertNotIn("touch /servidor/ark/obelisk/state/instances/arkserver-obelisk-debug/disable-plugins\n./arkserver2 restart", text)

    def test_static_fname_capture_is_historical_not_ragnarok_retry(self) -> None:
        note = REPO_ROOT / "docs/research/2026-05-27-static-fname-root-live-capture.md"
        text = note.read_text(encoding="utf-8")

        self.assertIn("Historical capture note", text)
        self.assertIn("arkserver-obelisk-debug", text)
        self.assertNotIn("/servidor/ark/arkserver start", text)


if __name__ == "__main__":
    unittest.main()
