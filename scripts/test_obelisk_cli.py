#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "scripts" / "obelisk.py"


def run_cli(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "--root", str(root), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class ObeliskCliTests(unittest.TestCase):
    def test_status_reports_root_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative in ("lib", "plugins", "config", "logs", "state/instances"):
                (root / relative).mkdir(parents=True)

            result = run_cli(root, "status")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"root: {root}", result.stdout)
            self.assertIn("plugins: 0", result.stdout)
            self.assertIn("instances: 0", result.stdout)

    def test_instances_list_reports_safe_marker_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            instance = root / "state" / "instances" / "arkserver"
            instance.mkdir(parents=True)
            (instance / "enable-process-event-hook").write_text("", encoding="utf-8")
            (instance / "disable-plugins").write_text("", encoding="utf-8")
            (instance / "marker-dir").mkdir()

            result = run_cli(root, "instances", "list")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("arkserver", result.stdout)
            self.assertIn("disable-plugins,enable-process-event-hook", result.stdout)
            self.assertNotIn("marker-dir", result.stdout)

    def test_plugins_list_merges_published_so_and_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "plugins").mkdir()
            (root / "plugins" / "oBaseEvents.so").write_text("fixture", encoding="utf-8")
            config_dir = root / "config" / "oBaseEvents"
            config_dir.mkdir(parents=True)
            (config_dir / "config.json").write_text(
                json.dumps(
                    {
                        "enabled": True,
                        "allow_all_instances": False,
                        "instance_allowlist": ["arkserver"],
                    }
                ),
                encoding="utf-8",
            )
            (root / "config" / "config_only").mkdir(parents=True)

            result = run_cli(root, "plugins", "list")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("oBaseEvents", result.stdout)
            self.assertIn("arkserver", result.stdout)
            self.assertIn("config_only", result.stdout)
            self.assertIn("missing", result.stdout)

    def test_plugins_show_reports_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "config" / "bad"
            config_dir.mkdir(parents=True)
            (config_dir / "config.json").write_text("{", encoding="utf-8")

            result = run_cli(root, "plugins", "show", "bad")

            self.assertEqual(result.returncode, 1)
            self.assertIn("config_state: invalid JSON", result.stdout)


if __name__ == "__main__":
    unittest.main()
