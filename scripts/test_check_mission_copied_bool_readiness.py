#!/usr/bin/env python3
"""Tests for check_mission_copied_bool_readiness.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_mission_copied_bool_readiness.py"
DEFAULT_ROOT = Path(
    "/home/flowcommunity-ark/obelisk-artifacts/mission-copied-bool-tail-policy-slice-20260530T090211Z"
)
DEFAULT_MANIFEST = DEFAULT_ROOT / "mission-copied-bool-policy-slice.json"


class CheckMissionCopiedBoolReadinessTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def copy_pack(self, root: Path) -> Path:
        shutil.copytree(DEFAULT_ROOT, root, dirs_exist_ok=True)
        return root / "mission-copied-bool-policy-slice.json"

    def test_default_pack_is_candidate_ready_but_not_public_or_runtime_ready(self) -> None:
        result = self.run_checker("--json")
        payload = json.loads(result.stdout)

        self.assertEqual(payload["schema"], "obelisk.mission-copied-bool-readiness-check.v1")
        self.assertEqual(payload["status"], "candidate_ready")
        self.assertTrue(payload["ready"])
        self.assertTrue(payload["accepted_for_internal_planning"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["promotion_ready"])
        self.assertEqual(payload["consume_gate"]["status"], "accepted")
        self.assertEqual(payload["promote_gate"]["status"], "blocked")
        self.assertEqual(
            set(payload["promote_gate"]["blocker_reasons"]),
            {
                "promote_mode_manifest_has_non_claims",
                "promote_mode_mission_copied_bool_policy_slice_evidence_only",
            },
        )
        self.assertEqual(len(payload["summary"]["input_targets"]), 4)
        self.assertEqual(len(payload["summary"]["copied_targets"]), 3)
        self.assertEqual(len(payload["summary"]["copied_fields"]), 5)
        self.assertEqual(len(payload["summary"]["redacted_fields"]), 6)
        self.assertEqual(payload["summary"]["copied_bool_count"], 5)
        self.assertIn("candidate readiness is internal planning evidence only", " ".join(payload["non_claims"]))

    def test_get_player_usable_items_copied_field_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest = self.copy_pack(root)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["coverage"]["copied_targets"].append("MissionType.GetPlayerUsableItems")
            payload["coverage"]["copied_fields"].append("MissionType.GetPlayerUsableItems.OutItemIDs")
            payload["copied_bools"].append(
                {
                    **payload["copied_bools"][0],
                    "target": "MissionType.GetPlayerUsableItems",
                    "copied_field": "MissionType.GetPlayerUsableItems.OutItemIDs",
                    "field": "OutItemIDs",
                }
            )
            manifest.write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_checker("--root", str(root), "--manifest", str(manifest), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("copied_target_coverage_mismatch", reasons)
        self.assertIn("copied_field_coverage_mismatch", reasons)
        self.assertIn("forbidden_copied_field", reasons)
        self.assertIn("get_player_usable_items_copied_target_not_allowed", reasons)
        self.assertIn("get_player_usable_items_copied_field_not_allowed", reasons)

    def test_noncanonical_bool_tail_metadata_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest = self.copy_pack(root)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["copied_bools"][0]["native_bool"] = True
            payload["copied_bools"][0]["byte_mask"] = "0xff"
            manifest.write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_checker("--root", str(root), "--manifest", str(manifest), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("copied_bool_entry_metadata_mismatch", reasons)

    def test_promote_gate_must_stay_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest = self.copy_pack(root)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["non_claims"] = []
            manifest.write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_checker("--root", str(root), "--manifest", str(manifest), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("required_non_claim_missing", reasons)
        self.assertIn("promote_gate_missing_required_blockers", reasons)
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_protected_and_symlink_inputs_are_rejected(self) -> None:
        result = self.run_checker(
            "--root",
            "/servidor/ark/obelisk/artifacts/mission",
            "--manifest",
            "/servidor/ark/obelisk/artifacts/mission/manifest.json",
            check=False,
        )
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("path_rejected", {blocker["reason"] for blocker in report["blockers"]})

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest = self.copy_pack(root)
            link = Path(temp_dir) / "manifest-link.json"
            link.symlink_to(manifest)
            result = self.run_checker("--root", str(root), "--manifest", str(link), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("path_rejected", {blocker["reason"] for blocker in report["blockers"]})


if __name__ == "__main__":
    unittest.main()
