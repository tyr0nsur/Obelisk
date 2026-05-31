#!/usr/bin/env python3
"""Tests for check_structure_census_readiness.py."""

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
SCRIPT = SCRIPT_DIR / "check_structure_census_readiness.py"
DEFAULT_ROOT = Path(
    "/home/flowcommunity-ark/obelisk-artifacts/structure-aggregate-census-policy-slice-20260531T034715Z"
)
DEFAULT_MANIFEST = DEFAULT_ROOT / "structure-aggregate-census-policy-slice.json"


class CheckStructureCensusReadinessTests(unittest.TestCase):
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
        return root / "structure-aggregate-census-policy-slice.json"

    def test_default_pack_is_candidate_ready_but_not_public_or_runtime_ready(self) -> None:
        result = self.run_checker("--json")
        payload = json.loads(result.stdout)

        self.assertEqual(payload["schema"], "obelisk.structure-census-readiness-check.v1")
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
                "promote_mode_structure_aggregate_census_policy_slice_consume_only",
            },
        )
        self.assertEqual(len(payload["summary"]["input_targets"]), 6)
        self.assertEqual(len(payload["summary"]["copied_fields"]), 8)
        self.assertEqual(len(payload["summary"]["redacted_fields"]), 5)
        self.assertEqual(len(payload["summary"]["explicitly_excluded_fields"]), 2)
        self.assertIn("candidate readiness is internal planning evidence only", " ".join(payload["non_claims"]))

    def test_missing_consume_only_flag_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest = self.copy_pack(root)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["consume_only"] = False
            manifest.write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_checker("--root", str(root), "--manifest", str(manifest), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("consume_only_not_true", reasons)
        self.assertIn("consume_gate_not_accepted", reasons)

    def test_copied_pin_field_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest = self.copy_pack(root)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            coverage = payload["coverage"]
            coverage["copied_fields_permitted"].append(
                "PrimalStructureItemContainer.VerifyPinCode.ReturnValue"
            )
            payload["copied_fields_permitted"].append(
                {
                    **payload["copied_fields_permitted"][0],
                    "copied_field": "PrimalStructureItemContainer.VerifyPinCode.ReturnValue",
                    "target": "PrimalStructureItemContainer.VerifyPinCode",
                    "field": "ReturnValue",
                }
            )
            manifest.write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_checker("--root", str(root), "--manifest", str(manifest), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("copied_field_coverage_mismatch", reasons)
        self.assertIn("forbidden_copied_field", reasons)

    def test_promote_gate_must_stay_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest = self.copy_pack(root)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["non_claims"] = []
            payload["consume_only"] = False
            payload["safety_summary"]["consume_only"] = False
            payload["safety_summary"]["promotion_ready"] = True
            manifest.write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_checker("--root", str(root), "--manifest", str(manifest), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("safety_promotion_ready_not_false", reasons)
        self.assertIn("promote_gate_missing_required_blockers", reasons)
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_protected_and_symlink_inputs_are_rejected(self) -> None:
        result = self.run_checker(
            "--root",
            "/servidor/ark/obelisk/artifacts/structure",
            "--manifest",
            "/servidor/ark/obelisk/artifacts/structure/manifest.json",
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
