#!/usr/bin/env python3
"""Tests for check_player_identity_static_orientation.py."""

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
SCRIPT = SCRIPT_DIR / "check_player_identity_static_orientation.py"
DEFAULT_ORIENTATION = (
    REPO_ROOT / "docs" / "research" / "2026-05-31-player-identity-static-target-orientation.json"
)


class CheckPlayerIdentityStaticOrientationTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def test_default_orientation_is_valid_candidate_only_navigation_evidence(self) -> None:
        result = self.run_checker("--json")
        payload = json.loads(result.stdout)

        self.assertEqual(payload["schema"], "obelisk.player-identity-static-orientation-check.v1")
        self.assertEqual(payload["status"], "valid")
        self.assertTrue(payload["valid"])
        self.assertTrue(payload["accepted_for_orientation"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertEqual(payload["target_set"], "players-identity-lifecycle-intake")
        self.assertEqual(payload["blockers"], [])
        self.assertEqual(
            payload["static_candidate_orientation_contract"]["schema"],
            "obelisk.static-candidate-orientation-contract.v1",
        )
        self.assertFalse(payload["static_candidate_orientation_contract"]["promotion_ready"])
        self.assertTrue(payload["static_candidate_orientation_contract"]["not_artifact_gate"])
        self.assertIn("candidate-only navigation evidence", " ".join(payload["non_claims"]))

    def test_promotional_gate_state_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate = Path(temp_dir) / "orientation.json"
            payload = json.loads(DEFAULT_ORIENTATION.read_text(encoding="utf-8"))
            payload["gate"]["promotion_ready"] = True
            candidate.write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_checker(str(candidate), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["status"], "blocked")
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("gate_promotion_ready_not_false", reasons)
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_missing_target_and_registration_mismatch_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate = Path(temp_dir) / "orientation.json"
            payload = json.loads(DEFAULT_ORIENTATION.read_text(encoding="utf-8"))
            payload["candidates"] = payload["candidates"][:-1]
            payload["candidates"][0]["registration_vma"] = "0xdeadbeef"
            candidate.write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_checker(str(candidate), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("candidate_target_coverage_mismatch", reasons)
        self.assertIn("candidate_registration_vma_not_in_xrefs", reasons)

    def test_server_root_and_symlink_inputs_are_rejected(self) -> None:
        result = self.run_checker("/servidor/ark/obelisk/dumps/orientation.json", check=False)
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("orientation_path_rejected", {blocker["reason"] for blocker in report["blockers"]})

        with tempfile.TemporaryDirectory() as temp_dir:
            link = Path(temp_dir) / "orientation-link.json"
            link.symlink_to(DEFAULT_ORIENTATION)
            result = self.run_checker(str(link), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("orientation_path_rejected", {blocker["reason"] for blocker in report["blockers"]})

    def test_copied_payload_with_readiness_fields_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate = Path(temp_dir) / "orientation.json"
            shutil.copyfile(DEFAULT_ORIENTATION, candidate)
            payload = json.loads(candidate.read_text(encoding="utf-8"))
            payload["public_sdk_ready"] = True
            candidate.write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_checker(str(candidate), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("orientation_payload_contains_readiness_overclaim", reasons)
        self.assertFalse(report["accepted_for_orientation"])
        self.assertFalse(report["public_sdk_ready"])


if __name__ == "__main__":
    unittest.main()
