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

    def assert_lifecycle_provenance_guardrail_blocks_generation(
        self,
        result: subprocess.CompletedProcess[str],
    ) -> None:
        self.assertEqual(1, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("generated lifecycle-anchor candidates failed validation", result.stderr)
        self.assertIn("accepted_anchor_artifact_identity_obelisk_commit_placeholder", result.stderr)
        self.assertIn("accepted_anchor_artifact_identity_source_id_placeholder", result.stderr)
        self.assertIn("accepted_anchor_second_source_report_hash_missing", result.stderr)

    def test_build_fails_closed_on_placeholder_lifecycle_anchor_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "planning"
            result = self.run_tool(["--output-dir", str(output_dir), "--json"], check=False)

        self.assert_lifecycle_provenance_guardrail_blocks_generation(result)

    def test_verify_existing_dir_fails_closed_on_committed_placeholder_lifecycle_provenance(self) -> None:
        result = self.run_tool(
            [
                "--verify-existing-dir",
                str(REPO_ROOT / "docs/research/player-identity-planning-sources"),
                "--json",
            ],
            check=False,
        )

        self.assert_lifecycle_provenance_guardrail_blocks_generation(result)

    def test_verify_existing_dir_stops_before_stale_check_when_generated_lifecycle_is_blocked(self) -> None:
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

        self.assert_lifecycle_provenance_guardrail_blocks_generation(result)

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
