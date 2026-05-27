#!/usr/bin/env python3
"""Repository hygiene guardrails for generated/local artifacts."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class RepoHygieneTests(unittest.TestCase):
    def test_generated_artifacts_are_gitignored(self) -> None:
        paths = [
            "build/",
            "scripts/__pycache__/",
            "compile_commands.json",
            "Obelisk.log",
            "logs/arkserver/Obelisk.log",
            "build/libobelisk.so",
            "arkserver.core",
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


if __name__ == "__main__":
    unittest.main()
