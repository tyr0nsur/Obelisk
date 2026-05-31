#!/usr/bin/env python3
"""Repository hygiene guardrails for generated/local artifacts."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLISHABLE_MARKDOWN_PATHS = [
    ".github/pull_request_template.md",
    "docs/INSTALL.md",
    "docs/OFFLINE_ARTIFACT_PACKS.md",
    "docs/RELEASE.md",
    "docs/STATUS.md",
]


class RepoHygieneTests(unittest.TestCase):
    def test_generated_artifacts_are_gitignored(self) -> None:
        paths = [
            "build/",
            "scripts/__pycache__/",
            "compile_commands.json",
            "Obelisk.log",
            "Obelisk-unknown.log",
            "logs/arkserver/Obelisk.log",
            "build/libobelisk.so",
            "local/discord-webhooks.env",
            "arkserver.core",
            "core.12345",
            "dumps/ShooterGameServer.core",
            "tmp/local.txt",
        ]
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "check-ignore", "--stdin"],
            input="\n".join(paths) + "\n",
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )

        ignored = set(result.stdout.splitlines())
        self.assertEqual(ignored, set(paths))

    def test_publishable_markdown_fences_are_balanced(self) -> None:
        offenders: list[str] = []
        for relative_path in PUBLISHABLE_MARKDOWN_PATHS:
            path = REPO_ROOT / relative_path
            fence_count = 0
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("```"):
                    fence_count += 1
            if fence_count % 2 != 0:
                offenders.append(relative_path)

        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
