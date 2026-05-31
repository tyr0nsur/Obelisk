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
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertEqual(payload["target_set"], "players-identity-lifecycle-intake")
        self.assertIn("missing_reflection_inventory_pack_or_core_evidence_pack", payload["blockers"])
        self.assertNotIn("fixture_coverage_incomplete", payload["blockers"])
        self.assertNotIn("second_source_evidence_missing", payload["blockers"])
        self.assertNotIn("players_identity_first_evidence_not_buildable", payload["blockers"])
        self.assertNotIn("accepted_lifecycle_anchors_missing", payload["blockers"])
        self.assertIn("fixture_coverage_incomplete", payload["deferred_until_reflection_inventory_ready"])
        self.assertIn("second_source_evidence_missing", payload["deferred_until_reflection_inventory_ready"])
        self.assertIn("players_identity_first_evidence_not_buildable", payload["deferred_until_reflection_inventory_ready"])
        self.assertIn("accepted_lifecycle_anchors_missing", payload["deferred_until_reflection_inventory_ready"])
        self.assertEqual(
            [artifact["schema"] for artifact in payload["next_required_artifacts"]],
            [
                "obelisk.core-dump-evidence-pack.v1",
                "obelisk.reflection-inventory-pack.v1",
            ],
        )
        recipe = payload["next_operator_recipe"]
        self.assertEqual(recipe["blocked_until"], "accepted_reflection_inventory_pack")
        self.assertIn("build_reflection_inventory_pack.py", recipe["build_reflection_inventory_pack"])
        self.assertIn("--target-set players-identity-lifecycle-intake", recipe["build_reflection_inventory_pack"])
        self.assertIn("check_reflection_inventory_pack_readiness.py", recipe["check_reflection_inventory_pack"])
        self.assertIn("plan_ufunction_focal_snapshots.py", recipe["plan_admin_focal_snapshots"])
        self.assertIn("--target ShooterPlayerController.ServerListPlayers", recipe["plan_admin_focal_snapshots"])
        self.assertIn("--target ShooterPlayerController.ServerKickPlayer", recipe["plan_admin_focal_snapshots"])
        self.assertNotIn("--target-set players-identity-lifecycle-intake", recipe["plan_admin_focal_snapshots"])
        self.assertIn("do not read from or write to /servidor/ark", " ".join(recipe["forbidden_next_commands"]))
        self.assertIn(
            "do not use --target-set players-identity-lifecycle-intake",
            " ".join(recipe["forbidden_next_commands"]),
        )
        self.assertIn("do not use direct --core mode", " ".join(recipe["forbidden_next_commands"]))
        self.assertIn("does not execute commands", " ".join(recipe["non_claims"]))
        self.assertEqual(
            payload["artifact_chain"]["required_admin_targets"],
            [
                "ShooterPlayerController.ServerKickPlayer",
                "ShooterPlayerController.ServerListPlayers",
            ],
        )
        self.assertTrue(payload["artifact_chain"]["blocked_before_focal_planning"])
        self.assertFalse(payload["artifact_chain"]["ready_to_plan_admin_snapshots"])
        self.assertEqual(
            payload["reflection_inventory"]["artifact_root_diagnosis"]["status"],
            "no_manifest_files_found",
        )
        self.assertEqual(payload["reflection_inventory"]["artifact_root_diagnosis"]["candidate_pack_count"], 0)
        self.assertEqual(payload["fixture_coverage"]["targets"], 12)
        self.assertEqual(payload["fixture_coverage"]["comparable"], 10)
        self.assertEqual(payload["fixture_coverage"]["blocked"], 2)
        self.assertEqual(payload["fixture_coverage"]["second_source_missing"], 10)
        self.assertEqual(payload["fixture_coverage"]["second_source_inconclusive"], 0)
        self.assertEqual(payload["fixture_coverage"]["second_source_rejected"], 0)
        self.assertIsNone(payload["candidate_root"])
        self.assertEqual(
            payload["first_evidence"]["missing_required_targets"],
            [
                "ShooterPlayerController.ServerKickPlayer",
                "ShooterPlayerController.ServerListPlayers",
            ],
        )
        self.assertFalse(payload["first_evidence"]["lifecycle_anchors"]["session_start_accepted"])
        self.assertFalse(payload["first_evidence"]["lifecycle_anchors"]["session_end_accepted"])
        self.assertIn(
            "accepted_session_start_anchor_missing",
            payload["first_evidence"]["lifecycle_anchors"]["blockers"],
        )
        self.assertIn(
            "accepted_session_end_anchor_missing",
            payload["first_evidence"]["lifecycle_anchors"]["blockers"],
        )
        self.assertEqual(
            payload["next_step"],
            "produce_or_approve_non_protected_core_evidence_pack_then_reflection_inventory_pack",
        )
        self.assertIn("does not touch servers", " ".join(payload["non_claims"]))
        self.assertIn("candidate-only planning evidence", " ".join(payload["non_claims"]))

    def test_candidate_root_reports_second_source_not_accepted_separately_from_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_checker(
                [
                    "--artifact-root",
                    temp_dir,
                    "--candidate-root",
                    str(REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"),
                ],
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["blockers"], ["missing_reflection_inventory_pack_or_core_evidence_pack"])
        self.assertEqual(
            payload["candidate_root"],
            str(REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"),
        )
        self.assertNotIn("second_source_evidence_missing", payload["deferred_until_reflection_inventory_ready"])
        self.assertIn("second_source_evidence_not_accepted", payload["deferred_until_reflection_inventory_ready"])
        self.assertEqual(payload["fixture_coverage"]["second_source_missing"], 0)
        self.assertEqual(payload["fixture_coverage"]["second_source_inconclusive"], 10)
        self.assertEqual(payload["fixture_coverage"]["second_source_rejected"], 0)
        self.assertEqual(payload["fixture_coverage"]["second_source_status"], "compared")

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
