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


if __name__ == "__main__":
    unittest.main()
