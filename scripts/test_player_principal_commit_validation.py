#!/usr/bin/env python3
"""Tests for player-principal reviewed commit validation."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent

import sys

sys.path.insert(0, str(SCRIPT_DIR))

import player_principal_commit_validation as commit_validation  # noqa: E402


class PlayerPrincipalCommitValidationTests(unittest.TestCase):
    def test_reviewed_commit_must_exist_in_repo(self) -> None:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=SCRIPT_DIR.parents[0],
            text=True,
        ).strip()

        self.assertTrue(commit_validation.is_reviewed_obelisk_commit(head))
        self.assertFalse(commit_validation.is_reviewed_obelisk_commit("a" * 40))
        self.assertFalse(commit_validation.is_reviewed_obelisk_commit("0" * 40))
        self.assertFalse(commit_validation.is_reviewed_obelisk_commit("test-commit"))


if __name__ == "__main__":
    unittest.main()
