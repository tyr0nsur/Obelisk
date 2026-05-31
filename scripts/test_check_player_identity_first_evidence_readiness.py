#!/usr/bin/env python3
"""Tests for check_player_identity_first_evidence_readiness.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent


class CheckPlayerIdentityFirstEvidenceReadinessTests(unittest.TestCase):
    def run_checker(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "check_player_identity_first_evidence_readiness.py"),
                *args,
            ],
            check=check,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

    def test_current_fixture_gap_reports_exact_next_step_without_promoting_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_checker(["--artifact-root", temp_dir], check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["schema"], "obelisk.player-identity-first-evidence-readiness.v1")
        self.assertEqual(payload["status"], "blocked")
        self.assertFalse(payload["ready"])
        self.assertEqual(payload["target_set"], "players-identity-lifecycle-intake")
        self.assertIn("missing_reflection_inventory_pack_or_core_evidence_pack", payload["blockers"])
        self.assertIn("fixture_coverage_incomplete", payload["blockers"])
        self.assertIn("players_identity_first_evidence_not_buildable", payload["blockers"])
        self.assertEqual(
            payload["reflection_inventory"]["artifact_root_diagnosis"]["status"],
            "no_manifest_files_found",
        )
        self.assertEqual(payload["reflection_inventory"]["artifact_root_diagnosis"]["candidate_pack_count"], 0)
        self.assertEqual(payload["fixture_coverage"]["targets"], 12)
        self.assertEqual(payload["fixture_coverage"]["comparable"], 10)
        self.assertEqual(payload["fixture_coverage"]["blocked"], 2)
        self.assertEqual(
            payload["first_evidence"]["missing_required_targets"],
            [
                "ShooterPlayerController.ServerKickPlayer",
                "ShooterPlayerController.ServerListPlayers",
            ],
        )
        self.assertEqual(
            payload["next_step"],
            "produce_or_approve_non_protected_core_evidence_pack_then_reflection_inventory_pack",
        )
        self.assertIn("does not touch servers", " ".join(payload["non_claims"]))
        self.assertIn("candidate-only planning evidence", " ".join(payload["non_claims"]))

    def test_artifact_root_diagnosis_summarizes_non_matching_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "scriptstruct-pack").mkdir()
            (root / "scriptstruct-pack" / "manifest.json").write_text(
                json.dumps({"schema": "obelisk.scriptstruct-inventory-pack.v1"}),
                encoding="utf-8",
            )
            (root / "container").mkdir()
            (root / "container" / "artifact-pack.manifest.json").write_text(
                json.dumps({"schema": "obelisk.offline-artifact-pack.v1"}),
                encoding="utf-8",
            )

            result = self.run_checker(["--artifact-root", str(root)], check=False)

        payload = json.loads(result.stdout)
        diagnosis = payload["reflection_inventory"]["artifact_root_diagnosis"]
        self.assertEqual(diagnosis["status"], "no_obelisk_reflection_inventory_pack_manifests_found")
        self.assertEqual(diagnosis["candidate_pack_count"], 0)
        self.assertEqual(diagnosis["reason_counts"]["missing_reflection_inventory_pack"], 1)
        self.assertEqual(diagnosis["reason_counts"]["scriptstruct_pack_not_reflection_inventory"], 1)
        self.assertEqual(diagnosis["reason_counts"]["artifact_pack_container_not_reflection_inventory"], 1)
        self.assertIn("scanned_paths", diagnosis["reason_examples"]["scriptstruct_pack_not_reflection_inventory"])
        self.assertIn("check_reflection_inventory_pack_readiness.py", diagnosis["next_useful_command"])


if __name__ == "__main__":
    unittest.main()
