#!/usr/bin/env python3

from __future__ import annotations

import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_staged_paths as checker


class CheckStagedPathsTests(unittest.TestCase):
    def test_normalizes_relative_paths_and_deduplicates(self) -> None:
        self.assertEqual(
            checker.normalize_paths(["./b.txt", "a.txt", "b.txt", "", " ./c.txt "]),
            ["a.txt", "b.txt", "c.txt"],
        )

    def test_rejects_absolute_and_parent_relative_paths(self) -> None:
        for path in ["/tmp/file", "C:/tmp/file", "C:\\tmp\\file", "../file", "a/../file", "."]:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    checker.normalize_paths([path])

    def test_paths_from_name_status_includes_rename_source_and_target(self) -> None:
        output = "M\0scripts/a.py\0D\0scripts/old.py\0R100\0scripts/before.py\0scripts/after.py\0"

        self.assertEqual(
            checker.paths_from_name_status(output),
            ["scripts/a.py", "scripts/old.py", "scripts/before.py", "scripts/after.py"],
        )

    def test_paths_from_name_status_reports_copy_target_only(self) -> None:
        output = "C100\0scripts/template.py\0scripts/new.py\0"

        self.assertEqual(checker.paths_from_name_status(output), ["scripts/new.py"])

    def test_path_mismatches_reports_missing_and_extra(self) -> None:
        missing, extra = checker.path_mismatches(
            ["scripts/a.py", "scripts/b.py"],
            ["scripts/b.py", "scripts/c.py"],
        )

        self.assertEqual(missing, ["scripts/a.py"])
        self.assertEqual(extra, ["scripts/c.py"])

    def test_main_prints_exact_paths_when_staged_set_matches(self) -> None:
        with (
            mock.patch("sys.argv", ["check_staged_paths.py", "scripts/a.py", "scripts/b.py"]),
            mock.patch.object(checker, "staged_paths", return_value=["scripts/b.py", "scripts/a.py"]),
            redirect_stdout(io.StringIO()) as stdout,
        ):
            self.assertEqual(checker.main(), 0)

        self.assertEqual(stdout.getvalue(), "scripts/a.py\nscripts/b.py\n")

    def test_main_returns_one_and_lists_missing_and_extra_paths(self) -> None:
        with (
            mock.patch("sys.argv", ["check_staged_paths.py", "scripts/a.py", "scripts/b.py"]),
            mock.patch.object(checker, "staged_paths", return_value=["scripts/b.py", "scripts/c.py"]),
            redirect_stderr(io.StringIO()) as stderr,
        ):
            self.assertEqual(checker.main(), 1)

        output = stderr.getvalue()
        self.assertIn("staged checkpoint paths do not match expected paths", output)
        self.assertIn("missing expected paths:", output)
        self.assertIn("  scripts/a.py", output)
        self.assertIn("unexpected staged paths:", output)
        self.assertIn("  scripts/c.py", output)

    def test_staged_paths_includes_deletes_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
            deleted = repo / "delete-me.txt"
            deleted.write_text("staged delete fixture\n", encoding="utf-8")
            subprocess.run(["git", "add", "delete-me.txt"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "fixture"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
            subprocess.run(["git", "rm", "delete-me.txt"], cwd=repo, check=True, stdout=subprocess.DEVNULL)

            with mock.patch.object(checker.subprocess, "run", wraps=subprocess.run):
                previous_cwd = Path.cwd()
                try:
                    import os

                    os.chdir(repo)
                    self.assertEqual(checker.staged_paths(), ["delete-me.txt"])
                finally:
                    os.chdir(previous_cwd)

    def test_staged_paths_includes_both_sides_of_renames_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
            renamed = repo / "before.txt"
            renamed.write_text("staged rename fixture\n", encoding="utf-8")
            subprocess.run(["git", "add", "before.txt"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "fixture"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
            subprocess.run(["git", "mv", "before.txt", "after.txt"], cwd=repo, check=True)

            previous_cwd = Path.cwd()
            try:
                import os

                os.chdir(repo)
                self.assertEqual(checker.staged_paths(), ["after.txt", "before.txt"])
            finally:
                os.chdir(previous_cwd)


if __name__ == "__main__":
    unittest.main()
