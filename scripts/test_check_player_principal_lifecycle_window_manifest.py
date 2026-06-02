#!/usr/bin/env python3
"""Tests for the short player-principal lifecycle window manifest checker entry point."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "check_player_principal_lifecycle_window_manifest.py"
LONG_SCRIPT = SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_window_manifest.py"
sys.path.insert(0, str(SCRIPT_DIR))
import check_player_principal_lifecycle_window_manifest as short_checker  # noqa: E402
import check_player_identity_runtime_principal_lifecycle_window_manifest as long_checker  # noqa: E402


class PlayerPrincipalLifecycleWindowManifestAliasTests(unittest.TestCase):
    def test_short_module_reexports_replay_api(self) -> None:
        self.assertIs(short_checker.load_manifest, long_checker.load_manifest)
        self.assertIs(short_checker.validate_manifest, long_checker.validate_manifest)
        self.assertIs(short_checker.Validation, long_checker.Validation)
        self.assertIs(short_checker.build_report, long_checker.build_report)

    def test_short_entrypoint_matches_long_checker_for_invalid_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = Path(temp_dir) / "window-manifest.env"
            manifest.write_text(
                "run_id=20260601T120000Z-player-principal-lifecycle\n",
                encoding="utf-8",
            )
            short = subprocess.run(
                [sys.executable, str(SCRIPT), str(manifest), "--json"],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            long = subprocess.run(
                [sys.executable, str(LONG_SCRIPT), str(manifest), "--json"],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertEqual(short.returncode, long.returncode)
        self.assertNotEqual(short.returncode, 0)
        self.assertEqual(json.loads(short.stdout), json.loads(long.stdout))

    def test_short_entrypoint_matches_long_checker_for_rejected_emit_template_copied_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            copied_log = root / "live-validation-logs" / "20260601T120000Z-player-principal-lifecycle" / "Obelisk.log"
            copied_log.parent.mkdir(parents=True)
            copied_log.write_text("copied player principal lifecycle observer log\n", encoding="utf-8")
            template = root / "window-manifest.env"

            short = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--emit-template",
                    str(template),
                    "--copied-log",
                    str(copied_log),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            long = subprocess.run(
                [
                    sys.executable,
                    str(LONG_SCRIPT),
                    "--emit-template",
                    str(template),
                    "--copied-log",
                    str(copied_log),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertEqual(short.returncode, long.returncode)
        self.assertNotEqual(short.returncode, 0)
        self.assertEqual(short.stdout, long.stdout)
        self.assertEqual(short.stderr, long.stderr)


if __name__ == "__main__":
    unittest.main()
