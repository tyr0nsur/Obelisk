#!/usr/bin/env python3
"""Guardrails for operational docs and skills that must not invite unsafe live actions."""

from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECK_ROOTS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "CONTRIBUTING.md",
    REPO_ROOT / ".github",
    REPO_ROOT / "docs",
    REPO_ROOT / "agent-skills",
]
SKIP_DIRS = {
    REPO_ROOT / "docs" / "research",
}
RESEARCH_ROOT = REPO_ROOT / "docs" / "research"
FORBIDDEN_ACTIVE_LINES = [
    "touch /servidor/ark/obelisk/state/",
    "mkdir -p /servidor/ark/obelisk/state/",
    "rm -f /servidor/ark/obelisk/state/",
    "/servidor/ark/arkserver2 restart",
    "./arkserver2 restart",
    "./arkserver restart",
    "./arkserver start",
]
FORBIDDEN_STALE_PHRASES = [
    "current TheIsland debug baseline",
    "Ragnarok is the current development/test harness",
    "Ragnarok is the current debug/development harness",
    "use `arkserver` / Ragnarok as the Obelisk development/test harness",
    "use `arkserver` / Ragnarok as the Obelisk debug/development harness",
    "Active debug target is now `arkserver` / Ragnarok",
    "Current routine debug uses Ragnarok",
    "Current core/runtime captures should\n  use the operator-approved `arkserver` window",
    "Current default validation uses",
    "default read-only validation target",
    "default validation target is",
    "Under the current RAM\n  constraint",
    "`arkserver` / Ragnarok available for Obelisk tests",
    "`arkserver` / Ragnarok is available as the Obelisk debug/development",
    "`arkserver` / Ragnarok is now available as the Obelisk",
    "keep `arkserver2` stopped for RAM",
    "while RAM is constrained",
]
RESEARCH_RUNBOOK_MARKERS = [
    "Historical/superseded",
    "operator-approved",
    "approved-window",
    "approved debug",
    "does not authorize",
]


def candidate_paths() -> list[Path]:
    paths: list[Path] = []
    for root in CHECK_ROOTS:
        if root.is_file():
            paths.append(root)
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in {".md"}:
                continue
            if any(skip in path.parents for skip in SKIP_DIRS):
                continue
            paths.append(path)
    return sorted(paths)


def is_comment_or_example(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("#") or stripped.startswith("//")


class OperationalDocGuardrailTests(unittest.TestCase):
    def test_no_active_marker_or_restart_commands_outside_research_docs(self) -> None:
        offenders: list[str] = []
        for path in candidate_paths():
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if is_comment_or_example(line):
                    continue
                for forbidden in FORBIDDEN_ACTIVE_LINES:
                    if forbidden in line:
                        offenders.append(f"{path.relative_to(REPO_ROOT)}:{number}: {forbidden}")

        self.assertEqual(offenders, [])

    def test_no_stale_operational_baseline_phrases_outside_research_docs(self) -> None:
        offenders: list[str] = []
        for path in candidate_paths():
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                for forbidden in FORBIDDEN_STALE_PHRASES:
                    if forbidden in line:
                        offenders.append(f"{path.relative_to(REPO_ROOT)}:{number}: {forbidden}")

        self.assertEqual(offenders, [])

    def test_research_live_commands_are_marked_historical_or_approved_runbook(self) -> None:
        offenders: list[str] = []
        for path in sorted(RESEARCH_ROOT.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            header = "\n".join(text.splitlines()[:20])
            header_lower = header.lower()
            has_marker = any(marker.lower() in header_lower for marker in RESEARCH_RUNBOOK_MARKERS)
            for number, line in enumerate(text.splitlines(), start=1):
                if is_comment_or_example(line):
                    continue
                if any(forbidden in line for forbidden in FORBIDDEN_ACTIVE_LINES) and not has_marker:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}:{number}")

        self.assertEqual(offenders, [])

    def test_operator_cli_scope_stays_read_only_before_stable_lifecycle(self) -> None:
        cli_doc = (REPO_ROOT / "docs" / "OPERATOR_CLI.md").read_text(encoding="utf-8")
        cli_script = (REPO_ROOT / "scripts" / "obelisk.py").read_text(encoding="utf-8")

        self.assertIn("read-only", cli_doc)
        self.assertIn("Post-Stable Lifecycle TODO", cli_doc)
        self.assertIn("Hot Reload Boundary", cli_doc)
        self.assertIn("plugin restart must\nmean an operational restart", cli_doc)
        self.assertIn('description="Read-only Obelisk operator CLI."', cli_script)

        for mutable_command in ("start", "stop", "restart", "enable", "disable", "install", "rollback"):
            self.assertNotIn(f'add_parser("{mutable_command}"', cli_script)


if __name__ == "__main__":
    unittest.main()
