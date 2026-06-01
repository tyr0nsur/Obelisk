#!/usr/bin/env python3
"""Tests for check_offline_workspace_inventory.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_offline_workspace_inventory.py"


class OfflineWorkspaceInventoryTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def write_json(self, path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_classifies_small_workspace_json_and_skips_heavy_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_json(
                root / "run-a" / "accepted.manifest.json",
                {"schema": "obelisk.example.v1", "valid": True, "status": "ok"},
            )
            self.write_json(
                root / "run-b" / "candidate-readiness.json",
                {"schema": "obelisk.example.v1", "planning_only": True, "promotion_ready": False},
            )
            self.write_json(
                root / "run-c" / "blocked-gate.json",
                {"schema": "obelisk.example.v1", "blockers": ["missing_second_source"]},
            )
            (root / "run-d").mkdir()
            (root / "run-d" / "core.1234").write_bytes(b"not-read")
            (root / "run-d" / "ShooterGameServer").write_bytes(b"not-read")

            result = self.run_checker("--root", str(root), "--json", check=False)
            report = json.loads(result.stdout)

            self.assertEqual(2, result.returncode)
            self.assertTrue(report["valid"])
            self.assertFalse(report["inventory_clean"])
            self.assertEqual(1, report["summary"]["artifacts_by_bucket"]["reusable"])
            self.assertEqual(1, report["summary"]["artifacts_by_bucket"]["candidate"])
            self.assertEqual(1, report["summary"]["artifacts_by_bucket"]["blocked"])
            self.assertEqual(2, report["summary"]["heavy_files_skipped"])

    def test_invalid_json_returns_schema_error_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "bad-readiness.json"
            path.write_text("{", encoding="utf-8")

            result = self.run_checker("--root", str(root), "--json", check=False)
            report = json.loads(result.stdout)

            self.assertEqual(4, result.returncode)
            self.assertFalse(report["valid"])
            self.assertEqual({"blocked": 1}, report["summary"]["artifacts_by_bucket"])
            self.assertEqual(1, report["summary"]["blockers_by_reason"]["invalid_json"])

    def test_symlinks_are_blocked_without_following(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target"
            target.mkdir()
            (target / "ok.manifest.json").write_text(
                json.dumps({"schema": "obelisk.example.v1", "valid": True}),
                encoding="utf-8",
            )
            (root / "link-dir").symlink_to(target, target_is_directory=True)
            (root / "link-file.manifest.json").symlink_to(target / "ok.manifest.json")

            result = self.run_checker("--root", str(root), "--json", check=False)
            report = json.loads(result.stdout)

            self.assertEqual(2, result.returncode)
            self.assertTrue(report["valid"])
            self.assertEqual(2, report["summary"]["symlinks_blocked"])
            artifact_paths = [artifact["path"] for artifact in report["roots"][0]["artifacts"]]
            self.assertEqual(["target/ok.manifest.json"], artifact_paths)

    def test_non_default_dumps_root_is_blocked_without_reading_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            dumps = Path(tmp) / "dumps"
            self.write_json(workspace / "ok.manifest.json", {"schema": "obelisk.example.v1", "valid": True})
            self.write_json(dumps / "raw.manifest.json", {"schema": "obelisk.example.v1", "valid": True})
            (dumps / "core").write_bytes(b"not-read")

            result = self.run_checker(
                "--root",
                str(workspace),
                "--include-dumps-root",
                str(dumps),
                "--json",
                check=False,
            )
            report = json.loads(result.stdout)

            self.assertEqual(2, result.returncode)
            self.assertEqual(1, report["summary"]["artifacts_by_bucket"]["reusable"])
            self.assertNotIn("blocked", report["summary"]["artifacts_by_bucket"])
            self.assertEqual(0, report["summary"]["heavy_files_skipped"])
            dumps_root = report["roots"][1]
            self.assertEqual(["include_dumps_root_not_default_dumps_path"], dumps_root["blockers"])
            self.assertEqual([], dumps_root["artifacts"])
            self.assertEqual(0, dumps_root["files_seen"])

    def test_non_default_include_dumps_root_does_not_walk_or_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            dumps = Path(tmp) / "not-default-dumps"
            self.write_json(workspace / "ok.manifest.json", {"schema": "obelisk.example.v1", "valid": True})
            self.write_json(dumps / "raw.manifest.json", {"schema": "obelisk.example.v1", "valid": True})

            result = self.run_checker(
                "--root",
                str(workspace),
                "--include-dumps-root",
                str(dumps),
                "--json",
                check=False,
            )
            report = json.loads(result.stdout)

            self.assertEqual(2, result.returncode)
            dumps_root = report["roots"][1]
            self.assertEqual(["include_dumps_root_not_default_dumps_path"], dumps_root["blockers"])
            self.assertEqual([], dumps_root["artifacts"])
            self.assertEqual(0, dumps_root["files_seen"])

    def test_include_dumps_root_blocks_symlink_component_before_walk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            real_dumps = root / "real-dumps"
            link = root / "linked-dumps"
            self.write_json(workspace / "ok.manifest.json", {"schema": "obelisk.example.v1", "valid": True})
            self.write_json(real_dumps / "raw.manifest.json", {"schema": "obelisk.example.v1", "valid": True})
            link.symlink_to(real_dumps, target_is_directory=True)

            result = self.run_checker(
                "--root",
                str(workspace),
                "--include-dumps-root",
                str(link / "nested"),
                "--json",
                check=False,
            )
            report = json.loads(result.stdout)

            self.assertEqual(2, result.returncode)
            dumps_root = report["roots"][1]
            self.assertIn("root_has_symlink_component", dumps_root["blockers"])
            self.assertEqual([], dumps_root["artifacts"])
            self.assertEqual(0, dumps_root["files_seen"])

    def test_raw_workspace_metadata_is_candidate_not_reusable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_json(root / "raw" / "raw.manifest.json", {"schema": "obelisk.example.v1", "valid": True})
            (root / "raw" / "core").write_bytes(b"not-read")
            (root / "raw" / "ShooterGameServer").write_bytes(b"not-read")

            result = self.run_checker("--root", str(root), "--json", check=False)
            report = json.loads(result.stdout)

            self.assertEqual(0, result.returncode)
            self.assertEqual({"candidate": 1}, report["summary"]["artifacts_by_bucket"])
            self.assertEqual(2, report["summary"]["heavy_files_skipped"])
            artifact = report["roots"][0]["artifacts"][0]
            self.assertEqual("raw_workspace_metadata_requires_gate_before_reuse", artifact["reason"])

    def test_protected_path_reference_is_candidate_not_reusable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_json(
                root / "ok.manifest.json",
                {
                    "schema": "obelisk.example.v1",
                    "valid": True,
                    "source": {"path": "/servidor/ark/obelisk/dumps/core"},
                },
            )

            result = self.run_checker("--root", str(root), "--json", check=False)
            report = json.loads(result.stdout)

            self.assertEqual(0, result.returncode)
            self.assertEqual({"candidate": 1}, report["summary"]["artifacts_by_bucket"])
            artifact = report["roots"][0]["artifacts"][0]
            self.assertEqual("protected_path_reference_requires_manual_review", artifact["reason"])


if __name__ == "__main__":
    unittest.main()
