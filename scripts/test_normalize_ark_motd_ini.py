#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "normalize_ark_motd_ini.py"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import normalize_ark_motd_ini as normalizer
from scripts.normalize_ark_motd_ini import normalize_motd_text


class NormalizeArkMotdIniTests(unittest.TestCase):
    def test_collapses_physical_motd_lines_only(self) -> None:
        source = (
            "[ServerSettings]\n"
            "ServerPVE=False\n"
            "\n"
            "[MessageOfTheDay]\n"
            'Message=<RichColor Color="0, 1, 1, 1">Welcome\n'
            "ERRORS MAY OCCUR</>\n"
            '<RichColor Color="1, 1, 0, 1">Bienvenido\n'
            "POSIBLES ERRORES</>\n"
            "Duration=20\n"
            "\n"
            "[Other]\n"
            "Message=not a motd\n"
        )

        result = normalize_motd_text(source)

        self.assertTrue(result.changed)
        self.assertEqual(result.message_entries, 1)
        self.assertEqual(result.continuation_lines_collapsed, 3)
        self.assertIn(
            'Message=<RichColor Color="0, 1, 1, 1">Welcome\\n'
            'ERRORS MAY OCCUR</>\\n'
            '<RichColor Color="1, 1, 0, 1">Bienvenido\\n'
            "POSIBLES ERRORES</>\n",
            result.normalized_text,
        )
        self.assertIn("Duration=20\n", result.normalized_text)
        self.assertIn("[Other]\nMessage=not a motd\n", result.normalized_text)

    def test_literal_backslash_n_message_is_unchanged(self) -> None:
        source = (
            "[MessageOfTheDay]\n"
            'Message=<RichColor Color="0, 1, 1, 1">Welcome\\nERRORS MAY OCCUR</>\n'
            "Duration=20\n"
        )

        result = normalize_motd_text(source)

        self.assertFalse(result.changed)
        self.assertEqual(result.continuation_lines_collapsed, 0)
        self.assertEqual(result.normalized_text, source)

    def test_mixed_escaped_and_physical_newline_boundaries_are_not_duplicated(self) -> None:
        source = "[MessageOfTheDay]\nMessage=Line 1\\n\nLine 2\\\nnLine 3\nDuration=20\n"

        result = normalize_motd_text(source)

        self.assertTrue(result.changed)
        self.assertEqual(result.continuation_lines_collapsed, 2)
        self.assertEqual(result.escaped_newline_boundaries_preserved, 2)
        self.assertEqual(
            result.normalized_text,
            "[MessageOfTheDay]\nMessage=Line 1\\nLine 2\\nLine 3\nDuration=20\n",
        )

    def test_comments_and_blank_lines_are_not_folded_into_message(self) -> None:
        source = (
            "[MessageOfTheDay]\n"
            "Message=Line 1\n"
            "Line 2\n"
            "; keep this comment\n"
            "\n"
            "Duration=20\n"
        )

        result = normalize_motd_text(source)

        self.assertTrue(result.changed)
        self.assertEqual(result.continuation_lines_collapsed, 1)
        self.assertEqual(
            result.normalized_text,
            "[MessageOfTheDay]\n"
            "Message=Line 1\\nLine 2\n"
            "; keep this comment\n"
            "\n"
            "Duration=20\n",
        )

    def test_check_fails_without_writing_when_normalization_is_needed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "GameUserSettings.ini"
            path.write_text("[MessageOfTheDay]\nMessage=Line 1\nLine 2\nDuration=20\n")

            result = subprocess.run(
                ["python3", str(SCRIPT), str(path), "--check", "--json"],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["schema"], "obelisk.ark-motd-normalizer.v1")
            self.assertTrue(payload["changed"])
            self.assertFalse(payload["wrote"])
            self.assertEqual(payload["continuation_lines_collapsed"], 1)
            self.assertEqual(
                path.read_text(),
                "[MessageOfTheDay]\nMessage=Line 1\nLine 2\nDuration=20\n",
            )

    def test_write_normalizes_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "GameUserSettings.ini"
            path.write_text("[MessageOfTheDay]\nMessage=Line 1\nLine 2\nDuration=20\n")

            result = subprocess.run(
                ["python3", str(SCRIPT), str(path), "--write", "--json"],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["changed"])
            self.assertTrue(payload["wrote"])
            self.assertEqual(
                path.read_text(),
                "[MessageOfTheDay]\nMessage=Line 1\\nLine 2\nDuration=20\n",
            )

    def test_protected_path_is_rejected_before_reading_without_allow_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected_root = Path(tmp) / "protected-ark"
            protected_root.mkdir()
            path = protected_root / "GameUserSettings.ini"
            path.write_text("[MessageOfTheDay]\nMessage=Line 1\nLine 2\nDuration=20\n")

            with mock.patch.object(normalizer, "PROTECTED_SERVER_ROOT", protected_root):
                stderr = StringIO()
                with redirect_stderr(stderr):
                    exit_code = normalizer.main([str(path), "--check", "--json"])

            self.assertEqual(exit_code, 2)
            self.assertIn("refusing protected path", stderr.getvalue())
            self.assertEqual(
                path.read_text(),
                "[MessageOfTheDay]\nMessage=Line 1\nLine 2\nDuration=20\n",
            )

    def test_allow_flag_permits_protected_path_but_check_still_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protected_root = Path(tmp) / "protected-ark"
            protected_root.mkdir()
            path = protected_root / "GameUserSettings.ini"
            path.write_text("[MessageOfTheDay]\nMessage=Line 1\nLine 2\nDuration=20\n")

            with mock.patch.object(normalizer, "PROTECTED_SERVER_ROOT", protected_root):
                stdout = StringIO()
                with redirect_stdout(stdout):
                    exit_code = normalizer.main(
                        [str(path), "--check", "--json", "--allow-protected-path"]
                    )

            self.assertEqual(exit_code, 1)
            payload = json.loads(stdout.getvalue())
            self.assertTrue(payload["protected_path"])
            self.assertTrue(payload["protected_path_allowed"])
            self.assertFalse(payload["wrote"])
            self.assertEqual(
                path.read_text(),
                "[MessageOfTheDay]\nMessage=Line 1\nLine 2\nDuration=20\n",
            )

    def test_symlink_resolved_protected_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            protected_root = tmp_path / "protected-ark"
            protected_root.mkdir()
            link = tmp_path / "linked-ini"
            link.symlink_to(protected_root, target_is_directory=True)

            with mock.patch.object(normalizer, "PROTECTED_SERVER_ROOT", protected_root):
                with self.assertRaises(ValueError):
                    normalizer.resolve_path_safety(
                        link / "GameUserSettings.ini",
                        allow_protected_path=False,
                    )


if __name__ == "__main__":
    unittest.main()
