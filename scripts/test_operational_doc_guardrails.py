#!/usr/bin/env python3
"""Guardrails for operational docs and skills that must not invite unsafe live actions."""

from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECK_ROOTS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs",
    REPO_ROOT / "agent-skills",
]
SKIP_DIRS = {
    REPO_ROOT / "docs" / "research",
}
FORBIDDEN_ACTIVE_LINES = [
    "touch /servidor/ark/obelisk/state/",
    "mkdir -p /servidor/ark/obelisk/state/",
    "rm -f /servidor/ark/obelisk/state/",
    "/servidor/ark/arkserver2 restart",
    "./arkserver2 restart",
    "./arkserver restart",
    "./arkserver start",
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


if __name__ == "__main__":
    unittest.main()
