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


class PlayerPrincipalLifecycleWindowManifestAliasTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
