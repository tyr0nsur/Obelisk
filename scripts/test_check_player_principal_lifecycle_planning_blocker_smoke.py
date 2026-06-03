#!/usr/bin/env python3
"""Tests for check_player_principal_lifecycle_planning_blocker_smoke.py."""

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
SCRIPT = SCRIPT_DIR / "check_player_principal_lifecycle_planning_blocker_smoke.py"
SOURCE_ROOT = REPO_ROOT / "docs/research/player-identity-planning-sources"
POLICY_NAME = "players-identity-principal-invalidation-policy.json"
REPORT_NAME = "player-identity-planning-source-manifests-report.json"


def copy_planning_sources(dst: Path) -> None:
    dst.mkdir(parents=True)
    for path in SOURCE_ROOT.glob("*.json"):
        shutil.copy2(path, dst / path.name)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


class PlayerPrincipalLifecyclePlanningBlockerSmokeTests(unittest.TestCase):
    def run_checker(self, root: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), "--json"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def test_accepts_committed_planning_sources_without_runtime_authority(self) -> None:
        result = self.run_checker(SOURCE_ROOT)
        report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertTrue(report["planning_sources_ready"])
        self.assertTrue(report["offline_only"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["runtime_evidence_ready"])
        self.assertFalse(report["runtime_work_authorized"])
        self.assertFalse(report["server_operations_authorized"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertEqual(report["remaining_blockers"], ["approved_runtime_evidence_missing"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["accepted_start_targets"], ["ShooterGameMode.HandleNewPlayer"])
        self.assertEqual(report["accepted_end_targets"], ["ShooterGameMode.OnLogout"])

    def test_rejects_policy_blocker_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "planning"
            copy_planning_sources(root)
            policy_path = root / POLICY_NAME
            policy = load_json(policy_path)
            policy["promotion_gate"]["blockers"][0] = "operator_current_turn_runtime_window_approval_required"
            write_json(policy_path, policy)

            result = self.run_checker(root, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ready"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_missing")
        self.assertIn("policy_promotion_gate_blockers_mismatch", report["blockers"])
        self.assertIn("planning_report_outputs_principal_invalidation_policy_sha256_mismatch", report["blockers"])
        self.assertIn("planning_report_sources_principal_invalidation_policy_sha256_mismatch", report["blockers"])

    def test_rejects_readiness_overclaim_in_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "planning"
            copy_planning_sources(root)
            report_path = root / REPORT_NAME
            payload = load_json(report_path)
            payload["stable_claim_allowed"] = True
            payload["runtime_work_authorized"] = True
            write_json(report_path, payload)

            result = self.run_checker(root, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("report_stable_claim_allowed_not_false", report["blockers"])
        self.assertIn("report_runtime_work_authorized_not_false", report["blockers"])
        self.assertEqual(report["remaining_blockers"], ["approved_runtime_evidence_missing"])

    def test_rejects_missing_public_sdk_non_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "planning"
            copy_planning_sources(root)
            report_path = root / REPORT_NAME
            payload = load_json(report_path)
            payload["binding_report"]["non_claims"] = [
                claim
                for claim in payload["binding_report"]["non_claims"]
                if "public SDK" not in claim
            ]
            write_json(report_path, payload)

            result = self.run_checker(root, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("planning_report_public_sdk_non_claim_missing", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])


if __name__ == "__main__":
    unittest.main()
