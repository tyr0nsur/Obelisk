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
        self.assertIn("build_core_dump_evidence_pack.py", recipe["build_core_evidence_pack"])
        self.assertIn("--binary", recipe["build_core_evidence_pack"])
        self.assertIn("--core", recipe["build_core_evidence_pack"])
        self.assertIn("--output-dir", recipe["build_core_evidence_pack"])
        self.assertIn("--fname-root-slot verified_fname_root_slot=0x5956f30", recipe["build_core_evidence_pack"])
        self.assertIn("--gobjects-candidate gobjects=0x595b7e0", recipe["build_core_evidence_pack"])
        self.assertIn("--gobjects-sample-index 25447", recipe["build_core_evidence_pack"])
        self.assertNotIn("--skip-core-sha256", recipe["build_core_evidence_pack"])
        self.assertNotIn("--allow-partial-gdb", recipe["build_core_evidence_pack"])
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
        self.assertEqual(
            payload["artifact_chain"]["offline_inputs"]["status"],
            "offline_binary_and_core_like_inputs_missing",
        )
        self.assertTrue(payload["artifact_chain"]["offline_inputs"]["artifact_root_only"])
        self.assertEqual(payload["artifact_chain"]["offline_inputs"]["server_root_excluded"], "/servidor/ark")
        self.assertFalse(payload["artifact_chain"]["offline_inputs"]["ready_to_build_core_evidence_pack"])
        self.assertTrue(payload["artifact_chain"]["blocked_before_focal_planning"])
        self.assertFalse(payload["artifact_chain"]["ready_to_plan_admin_snapshots"])
        self.assertTrue(payload["static_orientation"]["valid"])
        self.assertTrue(payload["static_orientation"]["accepted_for_orientation"])
        self.assertTrue(payload["static_orientation"]["not_artifact_gate"])
        self.assertFalse(payload["static_orientation"]["promotion_ready"])
        self.assertFalse(payload["static_orientation"]["public_sdk_ready"])
        self.assertFalse(payload["static_orientation"]["runtime_ready"])
        self.assertEqual(payload["static_orientation"]["blockers"], [])
        self.assertIn(
            "candidate-only navigation evidence",
            " ".join(payload["static_orientation"]["non_claims"]),
        )
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

    def test_json_flag_is_accepted_for_handoff_and_release_gate_callers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_checker(["--artifact-root", temp_dir, "--json"], check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["schema"], "obelisk.player-identity-first-evidence-readiness.v1")
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("missing_reflection_inventory_pack_or_core_evidence_pack", payload["blockers"])
        self.assertTrue(payload["static_orientation"]["valid"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])

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

    def test_offline_input_diagnosis_reports_binary_and_core_like_files_without_accepting_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary_dir = root / "offline-binaries" / "fake"
            binary_dir.mkdir(parents=True)
            (binary_dir / "ShooterGameServer").write_bytes(b"not the real server")
            (root / "core.1234").write_bytes(b"not a real core")

            result = self.run_checker(["--artifact-root", str(root)], check=False)

        payload = json.loads(result.stdout)
        offline_inputs = payload["artifact_chain"]["offline_inputs"]
        self.assertEqual(offline_inputs["status"], "offline_binary_present_hash_mismatch")
        self.assertEqual(len(offline_inputs["shooter_game_server_candidates"]), 1)
        self.assertFalse(offline_inputs["shooter_game_server_candidates"][0]["matches_current_binary"])
        self.assertEqual(len(offline_inputs["core_like_candidates"]), 1)
        self.assertFalse(offline_inputs["ready_to_build_core_evidence_pack"])
        self.assertIn("file presence only", " ".join(offline_inputs["non_claims"]))


if __name__ == "__main__":
    unittest.main()
