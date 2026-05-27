#!/usr/bin/env python3
"""Tests for regenerate_scriptstruct_snapshots.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from test_inspect_core_ufunctions import build_core_fixture  # noqa: E402


class RegenerateScriptStructSnapshotsTests(unittest.TestCase):
    def write_manifest(self, path: Path, *, module: str = "sdk_test", name: str = "ARKTributeDino") -> None:
        manifest = {
            "schema": "obelisk.scriptstruct-snapshot-manifest.v1",
            "ark_binary_sha256": "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
            "sha_prefix": "7e7ded49e0c6",
            "source": "offline_core",
            "status": "candidate-only",
            "max_object_scan": 128,
            "targets": [
                {
                    "module": module,
                    "outer": "/Script/ShooterGame",
                    "safe_outer": "Script.ShooterGame",
                    "name": name,
                    "file": f"Script.ShooterGame.{name}.snapshot.json",
                }
            ],
        }
        path.write_text(json.dumps(manifest), encoding="utf-8")

    def test_write_generates_scriptstruct_snapshot_from_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            manifest = root / "manifest.json"
            output_root = root / "out"
            output = output_root / "7e7ded49e0c6" / "sdk_test" / "Script.ShooterGame.ARKTributeDino.snapshot.json"
            addrs = build_core_fixture(core)
            self.write_manifest(manifest)

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "regenerate_scriptstruct_snapshots.py"),
                    "--core",
                    str(core),
                    "--manifest",
                    str(manifest),
                    "--output-root",
                    str(output_root),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--obelisk-commit",
                    "abcdef1",
                    "--write",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(payload["schema"], "obelisk.scriptstruct-chain.snapshot.v1")
        self.assertEqual(payload["targets"][0]["inspection_mode"], "script_struct")
        self.assertEqual(payload["targets"][0]["target"]["name"], "ARKTributeDino")
        self.assertEqual(payload["targets"][0]["target"]["class_name"], "ScriptStruct")
        self.assertEqual(payload["targets"][0]["properties_size"], 288)

    def test_empty_manifest_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            manifest = root / "manifest.json"
            output_root = root / "out"
            addrs = build_core_fixture(core)
            empty = {
                "schema": "obelisk.scriptstruct-snapshot-manifest.v1",
                "ark_binary_sha256": "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                "sha_prefix": "7e7ded49e0c6",
                "source": "offline_core",
                "status": "candidate-only",
                "max_object_scan": 128,
                "targets": [],
            }
            manifest.write_text(json.dumps(empty), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "regenerate_scriptstruct_snapshots.py"),
                    "--core",
                    str(core),
                    "--manifest",
                    str(manifest),
                    "--output-root",
                    str(output_root),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--obelisk-commit",
                    "abcdef1",
                    "--check",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
