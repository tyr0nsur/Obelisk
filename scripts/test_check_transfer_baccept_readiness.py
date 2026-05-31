#!/usr/bin/env python3
"""Tests for check_transfer_baccept_readiness.py."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_transfer_baccept_readiness.py"
sys.path.insert(0, str(SCRIPT_DIR))
import build_redacted_ufunction_signatures as build_tool  # noqa: E402
import check_transfer_baccept_readiness as readiness  # noqa: E402


class CheckTransferBacceptReadinessTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def make_policy(self) -> dict:
        return build_tool.build_transfer_baccept_only_policy_slice(
            snapshot_root=REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"
        )

    def write_pack(self, root: Path, payload: dict | None = None) -> tuple[Path, str]:
        root.mkdir(parents=True, exist_ok=True)
        manifest = root / "transfer-baccept-only-policy-slice.json"
        content = json.dumps(payload if payload is not None else self.make_policy(), sort_keys=True).encode("utf-8")
        manifest.write_bytes(content)
        return manifest, hashlib.sha256(content).hexdigest()

    def checker_args(self, root: Path, manifest: Path, sha256: str) -> list[str]:
        return [
            "--root",
            str(root),
            "--manifest",
            str(manifest),
            "--expected-manifest-sha256",
            sha256,
            "--skip-artifact-gates",
        ]

    def test_policy_fixture_is_candidate_ready_but_not_sdk_runtime_or_v1_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest, sha256 = self.write_pack(root)
            result = self.run_checker(*self.checker_args(root, manifest, sha256), "--json")

        payload = json.loads(result.stdout)
        self.assertEqual("obelisk.transfer-baccept-readiness-check.v1", payload["schema"])
        self.assertTrue(payload["ready"])
        self.assertTrue(payload["accepted_for_internal_planning"])
        self.assertTrue(payload["consume_only"])
        self.assertFalse(payload["public_transfer_sdk_ready"])
        self.assertFalse(payload["public_abi_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["identity_ready"])
        self.assertFalse(payload["ownership_ready"])
        self.assertFalse(payload["mutation_ready"])
        self.assertFalse(payload["return_override_ready"])
        self.assertFalse(payload["v1_completion_ready"])
        self.assertFalse(payload["promotion_ready"])
        self.assertEqual(1, payload["summary"]["copied_bool_count"])
        self.assertEqual(
            ["ShooterPlayerController.ServerTransferredPlayerConfirmationResult.bAccept"],
            payload["summary"]["copied_fields"],
        )
        self.assertEqual(10, len(payload["summary"]["forbidden_fields"]))

    def test_policy_rejects_sdk_identity_ownership_runtime_abi_and_v1_claim_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["public_abi_ready"] = True
            payload["coverage"]["ownership_ready"] = True
            payload["safety_summary"]["public_transfer_sdk_ready"] = True
            payload["copied_bool"]["identity"] = "player identity available"
            payload["forbidden_transfer_fields"][0]["return_override"] = False
            payload["generated_from"]["v1_completion"] = "ready"
            payload["generated_from"]["input_snapshots"][0]["runtime_wiring"] = "hooked"
            manifest, sha256 = self.write_pack(root, payload)
            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("policy_unexpected_field", reasons)
        self.assertIn("coverage_unexpected_field", reasons)
        self.assertIn("safety_summary_unexpected_field", reasons)
        self.assertIn("copied_bool_unexpected_field", reasons)
        self.assertIn("forbidden_transfer_field_unexpected_field", reasons)
        self.assertIn("generated_from_unexpected_field", reasons)
        self.assertIn("input_snapshot_unexpected_field", reasons)

    def test_policy_rejects_positive_transfer_sdk_claim_inside_non_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["non_claims"].append("public Transfer SDK is ready")
            manifest, sha256 = self.write_pack(root, payload)
            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("forbidden_positive_claim_value", reasons)

    def test_policy_rejects_extra_or_wrong_copied_bool(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["coverage"]["copied_fields"] = [
                "ShooterPlayerController.ServerTransferredPlayerConfirmationResult.bAccept",
                "ShooterPlayerController.ServerDownloadTransferredPlayer.SpawnPointID",
            ]
            payload["copied_bool"]["copied_field"] = "ShooterPlayerController.ServerDownloadTransferredPlayer.SpawnPointID"
            payload["copied_bool"]["field"] = "SpawnPointID"
            manifest, sha256 = self.write_pack(root, payload)
            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("copied_field_coverage_mismatch", reasons)
        self.assertIn("copied_bool_metadata_mismatch", reasons)
        self.assertIn("transfer_baccept_policy_copied_field_mismatch", reasons)


if __name__ == "__main__":
    unittest.main()
