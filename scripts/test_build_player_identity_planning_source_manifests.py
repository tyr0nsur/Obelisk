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
BOUND_ROUTE = SCRIPT_DIR / "check_command_permission_route_gate_bound_identity_sources.py"


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

    def test_builds_source_aligned_manifests_and_bound_route_stops_at_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "planning"
            result = self.run_tool(["--output-dir", str(output_dir), "--json"])
            report = json.loads(result.stdout)

            first_path = output_dir / "players-identity-first-evidence.json"
            lifecycle_path = output_dir / "players-identity-lifecycle-anchor-candidates.json"
            principal_path = output_dir / "players-identity-principal-invalidation-policy.json"
            first_evidence = json.loads(first_path.read_text(encoding="utf-8"))
            lifecycle = json.loads(lifecycle_path.read_text(encoding="utf-8"))
            principal = json.loads(principal_path.read_text(encoding="utf-8"))

            self.assertEqual(0, result.returncode)
            self.assertTrue(report["valid"])
            self.assertTrue(report["accepted_for_planning"])
            self.assertTrue(report["planning_only"])
            self.assertFalse(report["promotion_ready"])
            self.assertFalse(report["public_sdk_ready"])
            self.assertFalse(report["runtime_ready"])
            self.assertEqual([], report["blockers"])
            self.assertEqual(
                first_evidence["artifact_identity"]["source_artifact_ids"],
                lifecycle["artifact_identity"]["source_artifact_ids"],
            )
            self.assertEqual(
                lifecycle["artifact_identity"]["source_artifact_ids"],
                principal["lifecycle_layout_source"]["source_binding"]["artifact_identity_source_artifact_ids"],
            )
            self.assertEqual(
                ["ShooterGameMode.HandleNewPlayer"],
                principal["lifecycle_layout_source"]["source_binding"]["accepted_start_targets"],
            )
            self.assertEqual(
                ["ShooterGameMode.OnLogout"],
                principal["lifecycle_layout_source"]["source_binding"]["accepted_end_targets"],
            )
            snapshot_binding = report["source_alignment"]["lifecycle_snapshot_root_binding"]
            self.assertTrue(snapshot_binding["ready"])
            self.assertEqual([], snapshot_binding["blockers"])
            self.assertEqual(
                ["ShooterGameMode.HandleNewPlayer", "ShooterGameMode.OnLogout"],
                snapshot_binding["required_targets"],
            )

            bound = subprocess.run(
                [
                    sys.executable,
                    str(BOUND_ROUTE),
                    "--lifecycle-anchor-candidates-manifest",
                    str(lifecycle_path),
                    "--principal-invalidation-policy",
                    str(principal_path),
                    "--json",
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(0, bound.returncode, bound.stderr)
        bound_report = json.loads(bound.stdout)
        self.assertTrue(bound_report["valid"])
        self.assertTrue(bound_report["accepted_for_planning"])
        self.assertFalse(bound_report["promotion_ready"])
        self.assertFalse(bound_report["public_sdk_ready"])
        self.assertFalse(bound_report["runtime_ready"])
        self.assertEqual("approved_runtime_evidence_missing", bound_report["critical_path_phase"]["current_blocker"])
        self.assertEqual([], bound_report["blockers"])

    def test_verifies_committed_source_aligned_manifests(self) -> None:
        result = self.run_tool(
            [
                "--verify-existing-dir",
                str(REPO_ROOT / "docs/research/player-identity-planning-sources"),
                "--json",
            ]
        )
        report = json.loads(result.stdout)

        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["server_operations_authorized"])
        self.assertFalse(report["runtime_work_authorized"])
        self.assertEqual([], report["blockers"])
        for record in report["checked_outputs"].values():
            self.assertTrue(record["matches_generated"])

    def test_verify_existing_dir_rejects_stale_manifest(self) -> None:
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
        report = json.loads(result.stdout)

        self.assertEqual(1, result.returncode)
        self.assertFalse(report["valid"])
        self.assertIn(
            "stale_or_mismatched_planning_manifest",
            [blocker["reason"] for blocker in report["blockers"]],
        )

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


if __name__ == "__main__":
    unittest.main()
