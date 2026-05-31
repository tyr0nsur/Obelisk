#!/usr/bin/env python3
"""Guardrails against committing operational secrets."""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WEBHOOK_HOST_PATTERN = r"discord(?:app)?\.com/" + "api/webhooks"
DISCORD_WEBHOOK_RE = re.compile(
    r"https://(?:canary\.|ptb\.)?" + WEBHOOK_HOST_PATTERN + r"/\d+/[A-Za-z0-9_\-]+"
)
DISCORD_WEBHOOK_LITERAL_RE = re.compile(r"discord(?:app)?\.com/" + "api/webhooks")
OPERATOR_ABSOLUTE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:/home/[A-Za-z0-9._-]+|/Users/[A-Za-z0-9._-]+|/root(?:/|$)|[A-Za-z]:\\Users\\[A-Za-z0-9._-]+)"
)
PUBLISHABLE_TEXT_PATHS = [
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/plugin_proposal.yml",
    ".github/ISSUE_TEMPLATE/research_finding.yml",
    ".github/pull_request_template.md",
    ".github/workflows/ci.yml",
    "docs/INSTALL.md",
    "docs/OFFLINE_ARTIFACT_PACKS.md",
    "docs/RELEASE.md",
    "docs/STATUS.md",
]


def tracked_text_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z"],
        text=False,
    )
    paths: list[Path] = []
    for raw in output.split(b"\0"):
        if not raw:
            continue
        path = REPO_ROOT / raw.decode("utf-8")
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            continue
        if b"\0" not in data:
            paths.append(path)
    return paths


class SecretGuardrailTests(unittest.TestCase):
    def test_no_discord_webhook_urls_are_committed(self) -> None:
        offenders: list[str] = []
        for path in tracked_text_files():
            text = path.read_text(encoding="utf-8", errors="replace")
            if DISCORD_WEBHOOK_RE.search(text):
                offenders.append(str(path.relative_to(REPO_ROOT)))

        self.assertEqual(offenders, [])

    def test_no_discord_webhook_literal_patterns_are_committed(self) -> None:
        offenders: list[str] = []
        for path in tracked_text_files():
            text = path.read_text(encoding="utf-8", errors="replace")
            if DISCORD_WEBHOOK_LITERAL_RE.search(text):
                offenders.append(str(path.relative_to(REPO_ROOT)))

        self.assertEqual(offenders, [])

    def test_publishable_release_docs_do_not_expose_operator_absolute_paths(self) -> None:
        offenders: list[str] = []
        for relative_path in PUBLISHABLE_TEXT_PATHS:
            path = REPO_ROOT / relative_path
            text = path.read_text(encoding="utf-8", errors="replace")
            if OPERATOR_ABSOLUTE_PATH_RE.search(text):
                offenders.append(relative_path)

        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
