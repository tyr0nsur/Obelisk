#!/usr/bin/env python3
"""Tests for build_player_identity_planning_source_manifests.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "build_player_identity_planning_source_manifests.py"


class BuildPlayerIdentityPlanningSourceManifestsTests(unittest.TestCase):
    def run_tool(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
            self.fail(f"tool failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def assert_planning_generation_binds_static_lifecycle_report(
        self,
        result: subprocess.CompletedProcess[str],
        *,
        expected_mode: str | None = None,
    ) -> None:
        self.assertEqual(0, result.returncode)
        payload = json.loads(result.stdout)

        self.assertEqual("obelisk.player-identity-planning-source-manifests-build-report.v1", payload["schema"])
        if expected_mode is not None:
            self.assertEqual(expected_mode, payload["mode"])
        self.assertTrue(payload["valid"])
        self.assertTrue(payload["accepted_for_planning"])
        self.assertTrue(payload["planning_only"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["server_operations_authorized"])
        self.assertFalse(payload["runtime_work_authorized"])
        if "binding_report" in payload:
            lifecycle = payload["binding_report"]["planning_provenance"]["lifecycle_anchor_candidates"]
            self.assertTrue(lifecycle["static_anchor_provenance_bound"])
            self.assertEqual(lifecycle["blockers"], [])
            self.assertEqual(
                {
                    "ShooterGameMode.HandleNewPlayer": "static_accepted",
                    "ShooterGameMode.OnLogout": "static_accepted",
                },
                lifecycle["accepted_anchor_corroboration_status_by_target"],
            )
            self.assertEqual(
                {
                    "ShooterGameMode.HandleNewPlayer": "03acc0573b680d3e0b19937b30cc73028c5fd833e3796fe839006941b8779cf4",
                    "ShooterGameMode.OnLogout": "03acc0573b680d3e0b19937b30cc73028c5fd833e3796fe839006941b8779cf4",
                },
                lifecycle["accepted_anchor_static_report_sha256_by_target"],
            )
            self.assertEqual(payload["binding_report"]["blockers"], [])
        else:
            self.assertTrue(payload["generated_report_valid"])
            self.assertEqual(payload["blockers"], [])

    def write_blocked_static_report(self, path: Path) -> None:
        report = json.loads(
            (REPO_ROOT / "docs/research/player-identity-planning-sources/players-lifecycle-anchor-static-report.json").read_text(
                encoding="utf-8"
            )
        )
        report["ready"] = False
        report["accepted_for_lifecycle_anchor_binding"] = False
        path.write_text(json.dumps(report), encoding="utf-8")

    def write_static_report(self, path: Path, mutate) -> None:
        report = json.loads(
            (REPO_ROOT / "docs/research/player-identity-planning-sources/players-lifecycle-anchor-static-report.json").read_text(
                encoding="utf-8"
            )
        )
        mutate(report)
        path.write_text(json.dumps(report), encoding="utf-8")

    def test_build_binds_static_lifecycle_anchor_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "planning"
            result = self.run_tool(["--output-dir", str(output_dir), "--json"])
            lifecycle = json.loads((output_dir / "players-identity-lifecycle-anchor-candidates.json").read_text(encoding="utf-8"))

        self.assert_planning_generation_binds_static_lifecycle_report(result)
        self.assertIn(
            "capture_id:base-identity-core",
            lifecycle["artifact_identity"]["source_artifact_ids"],
        )
        for anchor in lifecycle["candidate_anchors"]:
            if anchor["target"] in {"ShooterGameMode.HandleNewPlayer", "ShooterGameMode.OnLogout"}:
                self.assertEqual(anchor["corroboration"]["status"], "static_accepted")
                self.assertEqual(
                    anchor["corroboration"]["static_report_sha256"],
                    "03acc0573b680d3e0b19937b30cc73028c5fd833e3796fe839006941b8779cf4",
                )

    def test_build_fails_closed_when_static_lifecycle_report_is_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_report = root / "static-report.json"
            self.write_blocked_static_report(static_report)
            result = self.run_tool(
                [
                    "--output-dir",
                    str(root / "planning"),
                    "--lifecycle-static-report",
                    str(static_report),
                    "--json",
                ],
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("lifecycle-static-report is not accepted", result.stderr)

    def test_build_rejects_static_lifecycle_report_snapshot_sha_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_report = root / "static-report.json"

            def mutate(report: dict) -> None:
                report["accepted_targets"][0]["source_snapshot_sha256"] = "0" * 64

            self.write_static_report(static_report, mutate)

            result = self.run_tool(
                [
                    "--output-dir",
                    str(root / "planning"),
                    "--lifecycle-static-report",
                    str(static_report),
                    "--json",
                ],
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("lifecycle-static-report source snapshot SHA mismatch", result.stderr)

    def test_build_rejects_admin_target_as_lifecycle_static_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_report = root / "static-report.json"

            def mutate(report: dict) -> None:
                admin_target = dict(report["accepted_targets"][0])
                admin_target["target"] = "ShooterPlayerController.ServerListPlayers"
                report["accepted_targets"].append(admin_target)

            self.write_static_report(static_report, mutate)

            result = self.run_tool(
                [
                    "--output-dir",
                    str(root / "planning"),
                    "--lifecycle-static-report",
                    str(static_report),
                    "--json",
                ],
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("admin target as lifecycle anchor", result.stderr)
        self.assertIn("ServerListPlayers/ServerKickPlayer are admin targets, not lifecycle anchors", result.stderr)

    def test_verify_existing_dir_accepts_committed_static_lifecycle_provenance(self) -> None:
        result = self.run_tool(
            [
                "--verify-existing-dir",
                str(REPO_ROOT / "docs/research/player-identity-planning-sources"),
                "--json",
            ],
        )

        self.assert_planning_generation_binds_static_lifecycle_report(result, expected_mode="verify_existing")

    def test_verify_existing_dir_detects_stale_lifecycle_manifest_after_static_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            existing = Path(temp_dir) / "planning"
            subprocess.run(
                [
                    "cp",
                    "-a",
                    str(REPO_ROOT / "docs/research/player-identity-planning-sources"),
                    str(existing),
                ],
                check=True,
            )
            stale_path = existing / "players-identity-lifecycle-anchor-candidates.json"
            stale = json.loads(stale_path.read_text(encoding="utf-8"))
            stale["candidate_anchors"] = []
            stale_path.write_text(json.dumps(stale, sort_keys=True) + "\n", encoding="utf-8")

            result = self.run_tool(["--verify-existing-dir", str(existing), "--json"], check=False)

        self.assertEqual(1, result.returncode)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["valid"])
        self.assertIn("stale_or_mismatched_planning_manifest", [entry["reason"] for entry in payload["blockers"]])

    def test_rejects_protected_output_dir_before_writing(self) -> None:
        result = self.run_tool(
            ["--output-dir", "/servidor/ark/player-identity-planning-source-manifests"],
            check=False,
        )

        self.assertEqual(1, result.returncode)
        self.assertIn("must not write under protected server root", result.stderr)

    def test_rejects_symlink_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            real = root / "real"
            real.mkdir()
            link = root / "link"
            link.symlink_to(real, target_is_directory=True)

            result = self.run_tool(["--output-dir", str(link)], check=False)

        self.assertEqual(1, result.returncode)
        self.assertIn("output-dir must not be a symlink", result.stderr)

    def test_rejects_missing_focal_lifecycle_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot_root = root / "snapshots"
            subprocess.run(
                ["cp", "-a", str(REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"), str(snapshot_root)],
                check=True,
            )
            manifest_path = snapshot_root / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["targets"] = [
                target
                for target in manifest["targets"]
                if f"{target.get('outer')}.{target.get('name')}" != "ShooterGameMode.OnLogout"
            ]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = self.run_tool(
                ["--snapshot-root", str(snapshot_root), "--output-dir", str(root / "out")],
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("snapshot manifest does not contain required lifecycle target", result.stderr)

    def test_rejects_duplicate_focal_lifecycle_snapshot_manifest_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot_root = root / "snapshots"
            subprocess.run(
                ["cp", "-a", str(REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"), str(snapshot_root)],
                check=True,
            )
            manifest_path = snapshot_root / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for target in manifest["targets"]:
                if f"{target.get('outer')}.{target.get('name')}" == "ShooterGameMode.HandleNewPlayer":
                    manifest["targets"].append(dict(target))
                    break
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = self.run_tool(
                ["--snapshot-root", str(snapshot_root), "--output-dir", str(root / "out")],
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("duplicate snapshot manifest target: ShooterGameMode.HandleNewPlayer", result.stderr)

    def test_rejects_snapshot_manifest_path_outside_snapshot_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot_root = root / "snapshots"
            subprocess.run(
                ["cp", "-a", str(REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"), str(snapshot_root)],
                check=True,
            )
            manifest_path = snapshot_root / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for target in manifest["targets"]:
                if f"{target.get('outer')}.{target.get('name')}" == "ShooterGameMode.HandleNewPlayer":
                    target["module"] = "../../../outside"
                    break
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = self.run_tool(
                ["--snapshot-root", str(snapshot_root), "--output-dir", str(root / "out")],
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("resolves outside snapshot-root", result.stderr)


if __name__ == "__main__":
    unittest.main()
