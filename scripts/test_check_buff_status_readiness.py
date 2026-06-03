#!/usr/bin/env python3
"""Tests for check_buff_status_readiness.py."""

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
SCRIPT = SCRIPT_DIR / "check_buff_status_readiness.py"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"
BUFF_FIXTURE_DIR = FIXTURE_ROOT / "7e7ded49e0c6" / "sdk_buffs"
sys.path.insert(0, str(SCRIPT_DIR))
import check_buff_status_readiness as readiness  # noqa: E402


class CheckBuffStatusReadinessTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def copy_fixture_root(self, root: Path) -> Path:
        dst = root / "snapshots" / "7e7ded49e0c6" / "sdk_buffs"
        dst.mkdir(parents=True, exist_ok=True)
        for source in BUFF_FIXTURE_DIR.glob("*.snapshot.json"):
            shutil.copy2(source, dst / source.name)
        return root / "snapshots"

    def snapshot_path(self, root: Path, target: str) -> Path:
        return root / "7e7ded49e0c6" / "sdk_buffs" / f"{target}.snapshot.json"

    def read_snapshot(self, root: Path, target: str) -> dict:
        return json.loads(self.snapshot_path(root, target).read_text(encoding="utf-8"))

    def write_snapshot(self, root: Path, target: str, payload: dict) -> None:
        self.snapshot_path(root, target).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def test_current_tree_is_internal_candidate_only_not_public_runtime_or_v1_ready(self) -> None:
        result = self.run_checker("--json")

        payload = json.loads(result.stdout)
        self.assertEqual("obelisk.buff-status-readiness-check.v1", payload["schema"])
        self.assertTrue(payload["ready"])
        self.assertTrue(payload["accepted_for_internal_planning"])
        self.assertTrue(payload["offline_only"])
        self.assertTrue(payload["fixture_only"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertTrue(payload["buff_status_candidate_ready"])
        self.assertTrue(payload["copied_bool_boundary_ready"])
        self.assertTrue(payload["class_object_redaction_ready"])
        self.assertTrue(payload["zero_param_lifecycle_shape_ready"])
        self.assertFalse(payload["copied_payload_policy_ready"])
        self.assertFalse(payload["lifecycle_semantics_ready"])
        self.assertFalse(payload["buff_status_sdk_ready"])
        self.assertFalse(payload["module_sdk_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["public_buff_sdk_ready"])
        self.assertFalse(payload["public_abi_ready"])
        self.assertFalse(payload["public_api_ready"])
        self.assertFalse(payload["public_callback_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["runtime_hook_ready"])
        self.assertFalse(payload["runtime_wiring_ready"])
        self.assertFalse(payload["runtime_observer_approved"])
        self.assertFalse(payload["dispatcher_ready"])
        self.assertFalse(payload["identity_ready"])
        self.assertFalse(payload["lookup_ready"])
        self.assertFalse(payload["mutation_ready"])
        self.assertFalse(payload["return_override_ready"])
        self.assertFalse(payload["resource_handle_ready"])
        self.assertFalse(payload["v1_accounted"])
        self.assertFalse(payload["v1_completion"])
        self.assertFalse(payload["v1_completion_ready"])
        self.assertFalse(payload["stable_claim_allowed"])
        self.assertFalse(payload["complete_sdk_claim_allowed"])
        self.assertFalse(payload["counts_toward_complete_sdk_claim"])
        self.assertFalse(payload["promotion_ready"])
        self.assertEqual(6, payload["summary"]["copied_bool_count"])
        self.assertEqual(4, payload["summary"]["redacted_field_count"])
        self.assertEqual(
            {
                "PrimalBuff.AllowPostProcessEffect.ReturnValue",
                "PrimalBuff.BPBuffPreventUploading.ReturnValue",
                "PrimalBuff.BuffOverrideInventoryAccessInput.bInputPressed",
                "PrimalBuff.BuffOverrideInventoryAccessInput.ReturnValue",
                "PrimalBuff.BPCustomAllowAddBuff.ReturnValue",
                "PrimalBuff.BPPreventAddingOtherBuff.ReturnValue",
            },
            set(payload["summary"]["copied_bool_fields"]),
        )
        self.assertEqual(
            {
                "PrimalBuff.BuffOverrideInventoryAccessInput.InController",
                "PrimalBuff.BPCustomAllowAddBuff.DamageCauser",
                "PrimalBuff.BPCustomAllowAddBuff.forCharacter",
                "PrimalBuff.BPPreventAddingOtherBuff.anotherBuffClass",
            },
            set(payload["summary"]["redacted_fields"]),
        )

    def test_build_report_can_be_called_directly(self) -> None:
        report = readiness.build_report(FIXTURE_ROOT)
        self.assertTrue(report["ready"])
        self.assertEqual(
            ["buff-breadth-intake", "buff-compact-intake"],
            sorted(report["summary"]["target_sets"]),
        )

    def test_missing_required_snapshot_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            self.snapshot_path(root, "PrimalBuff.BPBuffPreventUploading").unlink()
            result = self.run_checker("--snapshot-root", str(root), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("required_target_snapshot_missing", reasons)
        self.assertIn("copied_bool_field_missing", reasons)
        self.assertFalse(payload["public_buff_sdk_ready"])

    def test_required_object_and_class_redactions_must_remain_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "PrimalBuff.BPCustomAllowAddBuff")
            target = payload["targets"][0]
            target["property_chain"]["properties"] = [
                prop for prop in target["property_chain"]["properties"] if prop["name"] != "DamageCauser"
            ]
            target["property_chain"]["expected_count"] = 2
            target["property_chain"]["observed_count"] = 2
            target["num_parms"] = 2
            self.write_snapshot(root, "PrimalBuff.BPCustomAllowAddBuff", payload)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("required_redacted_field_missing", reasons)
        self.assertFalse(output["identity_ready"])
        self.assertFalse(output["resource_handle_ready"])

    def test_class_ref_shape_must_not_be_scalarized(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "PrimalBuff.BPPreventAddingOtherBuff")
            prop = payload["targets"][0]["property_chain"]["properties"][0]
            prop["class_name"] = "BoolProperty"
            prop["element_size"] = 1
            prop["bool_byte_offset"] = 0
            prop["bool_field_size"] = 1
            prop["byte_mask"] = "0x1"
            prop["field_mask"] = "0xff"
            prop["native_bool"] = False
            prop["bool_property_semantics"] = {"status": "candidate", "bool_byte_offset": 0, "bool_field_size": 1}
            self.write_snapshot(root, "PrimalBuff.BPPreventAddingOtherBuff", payload)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("buff_class_redaction_shape_mismatch", reasons)
        self.assertFalse(output["public_buff_sdk_ready"])

    def test_zero_param_lifecycle_target_does_not_promote_lifecycle_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "PrimalBuff.BP_OnBuffLifetimeUpdated")
            target = payload["targets"][0]
            target["num_parms"] = 1
            target["parms_size"] = 1
            target["return_value_offset"] = "0x0"
            target["property_chain"]["expected_count"] = 1
            target["property_chain"]["observed_count"] = 1
            target["property_chain"]["parms_size"] = 1
            target["property_chain"]["properties"] = [
                {
                    "array_dim": 1,
                    "bool_byte_offset": 0,
                    "bool_field_size": 1,
                    "bool_property_semantics": {
                        "bool_byte_offset": 0,
                        "bool_field_size": 1,
                        "reject_reasons": [],
                        "status": "candidate",
                    },
                    "byte_mask": "0x1",
                    "class_membership_status": "candidate-uobject",
                    "class_name": "BoolProperty",
                    "depth": 0,
                    "element_size": 1,
                    "field_mask": "0xff",
                    "membership_status": "candidate-uobject",
                    "name": "ReturnValue",
                    "native_bool": False,
                    "offset_internal": 0,
                    "outer_membership_status": "candidate-uobject",
                    "property_flags": "0x80",
                    "reject_reasons": [],
                    "status": "candidate",
                }
            ]
            self.write_snapshot(root, "PrimalBuff.BP_OnBuffLifetimeUpdated", payload)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("zero_param_lifecycle_shape_mismatch", reasons)
        self.assertIn("unexpected_buff_scalar", reasons)
        self.assertFalse(output["lifecycle_semantics_ready"])

    def test_public_runtime_or_v1_readiness_claims_in_fixtures_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "PrimalBuff.AllowPostProcessEffect")
            payload["public_buff_sdk_ready"] = True
            payload["runtime_ready"] = True
            payload["v1_completion_ready"] = True
            payload["counts_toward_complete_sdk_claim"] = True
            self.write_snapshot(root, "PrimalBuff.AllowPostProcessEffect", payload)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("forbidden_readiness_claim", reasons)
        self.assertFalse(output["public_sdk_ready"])
        self.assertFalse(output["runtime_ready"])
        self.assertFalse(output["v1_completion_ready"])
        self.assertFalse(output["counts_toward_complete_sdk_claim"])

    def test_textual_public_runtime_or_v1_claims_in_fixtures_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "PrimalBuff.AllowPostProcessEffect")
            payload["interpretation"]["note"] = (
                "Public Buff/status SDK is ready. Buff/status SDK is available. Runtime observer is approved. "
                "This counts toward the complete SDK claim."
            )
            self.write_snapshot(root, "PrimalBuff.AllowPostProcessEffect", payload)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("forbidden_text_claim", reasons)
        claims = {blocker["claim"] for blocker in output["blockers"] if blocker["reason"] == "forbidden_text_claim"}
        self.assertIn("Public Buff/status SDK", claims)
        self.assertIn("Buff/status SDK", claims)
        self.assertIn("Runtime observer", claims)
        self.assertIn("counts toward the complete SDK claim", claims)
        self.assertFalse(output["public_sdk_ready"])
        self.assertFalse(output["runtime_ready"])
        self.assertFalse(output["v1_accounted"])

    def test_negated_textual_non_claims_in_fixtures_are_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "PrimalBuff.AllowPostProcessEffect")
            payload["interpretation"]["note"] = (
                "No public Buff/status SDK is ready; runtime observer remains blocked; "
                "v1 completion is not included."
            )
            self.write_snapshot(root, "PrimalBuff.AllowPostProcessEffect", payload)
            result = self.run_checker("--snapshot-root", str(root))

        output = json.loads(result.stdout)
        self.assertTrue(output["ready"])
        self.assertEqual([], output["blockers"])

    def test_snapshot_root_must_not_be_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            symlink = Path(temp_dir) / "linked-snapshots"
            symlink.symlink_to(root, target_is_directory=True)
            result = self.run_checker("--snapshot-root", str(symlink), check=False)

        output = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("path_rejected", reasons)

    def test_snapshot_file_must_not_be_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            snapshot = self.snapshot_path(root, "PrimalBuff.AllowPostProcessEffect")
            real_snapshot = Path(temp_dir) / "outside.snapshot.json"
            shutil.copy2(snapshot, real_snapshot)
            snapshot.unlink()
            snapshot.symlink_to(real_snapshot)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("path_rejected", reasons)
        self.assertIn("required_target_snapshot_missing", reasons)


if __name__ == "__main__":
    unittest.main()
