#!/usr/bin/env python3

from __future__ import annotations

import io
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_release_tag_state as checker


class CheckReleaseTagStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.repo, check=True)
        self.previous_cwd = Path.cwd()
        os.chdir(self.repo)
        self.addCleanup(lambda: os.chdir(self.previous_cwd))

    def commit(self, name: str) -> str:
        path = self.repo / f"{name}.txt"
        path.write_text(f"{name}\n", encoding="utf-8")
        subprocess.run(["git", "add", path.name], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", name], cwd=self.repo, check=True, stdout=subprocess.DEVNULL)
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repo,
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()

    def run_main(self, *args: str) -> tuple[int, str, str]:
        with (
            mock.patch("sys.argv", ["check_release_tag_state.py", *args]),
            redirect_stdout(io.StringIO()) as stdout,
            redirect_stderr(io.StringIO()) as stderr,
        ):
            code = checker.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def test_accepts_tag_that_matches_ref(self) -> None:
        commit = self.commit("release")
        subprocess.run(["git", "tag", "-a", "v0.1.0-rc.1", "-m", "fixture"], cwd=self.repo, check=True)

        code, stdout, stderr = self.run_main("--tag", "v0.1.0-rc.1", "--ref", "HEAD")

        self.assertEqual(code, 0)
        self.assertIn(commit, stdout)
        self.assertEqual(stderr, "")

    def test_rejects_stale_tag(self) -> None:
        old_commit = self.commit("old")
        subprocess.run(["git", "tag", "-a", "v0.1.0-rc.1", "-m", "fixture"], cwd=self.repo, check=True)
        new_commit = self.commit("new")

        code, stdout, stderr = self.run_main("--tag", "v0.1.0-rc.1", "--ref", "HEAD")

        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("tag/ref mismatch", stderr)
        self.assertIn(old_commit, stderr)
        self.assertIn(new_commit, stderr)

    def test_rejects_missing_tag_by_default(self) -> None:
        self.commit("release")

        code, stdout, stderr = self.run_main("--tag", "v0.1.0-rc.1")

        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("does not exist", stderr)

    def test_allow_missing_verifies_ref_for_pre_tag_stage(self) -> None:
        commit = self.commit("release")

        code, stdout, stderr = self.run_main("--tag", "v0.1.0-rc.1", "--allow-missing")

        self.assertEqual(code, 0)
        self.assertIn(commit, stdout)
        self.assertEqual(stderr, "")

    def test_invalid_ref_is_usage_error(self) -> None:
        self.commit("release")

        code, stdout, stderr = self.run_main("--tag", "v0.1.0-rc.1", "--ref", "missing-ref")

        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("cannot resolve ref", stderr)


if __name__ == "__main__":
    unittest.main()
