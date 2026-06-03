#!/usr/bin/env python3
"""Tests for check_tribe_scalar_boundary_readiness.py."""

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
SCRIPT = SCRIPT_DIR / "check_tribe_scalar_boundary_readiness.py"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"
TRIBE_FIXTURE_DIR = FIXTURE_ROOT / "7e7ded49e0c6" / "sdk_tribes"
sys.path.insert(0, str(SCRIPT_DIR))
import check_tribe_scalar_boundary_readiness as readiness  # noqa: E402


class CheckTribeScalarBoundaryReadinessTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def copy_fixture_root(self, root: Path) -> Path:
        dst = root / "snapshots" / "7e7ded49e0c6" / "sdk_tribes"
        dst.mkdir(parents=True, exist_ok=True)
        for source in TRIBE_FIXTURE_DIR.glob("*.snapshot.json"):
            shutil.copy2(source, dst / source.name)
        return root / "snapshots"

    def snapshot_path(self, root: Path, target: str) -> Path:
        return root / "7e7ded49e0c6" / "sdk_tribes" / f"{target}.snapshot.json"

    def read_snapshot(self, root: Path, target: str) -> dict:
        return json.loads(self.snapshot_path(root, target).read_text(encoding="utf-8"))

    def write_snapshot(self, root: Path, target: str, payload: dict) -> None:
        self.snapshot_path(root, target).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def test_current_tree_is_internal_candidate_only_not_public_runtime_or_v1_ready(self) -> None:
        result = self.run_checker("--json")

        payload = json.loads(result.stdout)
        self.assertEqual("obelisk.tribe-scalar-boundary-readiness-check.v1", payload["schema"])
        self.assertTrue(payload["ready"])
        self.assertTrue(payload["accepted_for_internal_planning"])
        self.assertTrue(payload["offline_only"])
        self.assertTrue(payload["fixture_only"])
        self.assertTrue(payload["tribe_scalar_boundary_ready"])
        self.assertEqual("tribe-compact-intake", payload["target_set"])
        self.assertEqual(
            {
                "ShooterPlayerController.AllowTribeGroupPermission.TribeGroupPermission",
                "ShooterPlayerController.AllowTribeGroupPermission.ReturnValue",
                "ShooterPlayerController.IsInTribe.ReturnValue",
            },
            set(payload["summary"]["accepted_scalar_fields"]),
        )
        self.assertIn("ShooterPlayerController.AllowTribeGroupPermission.OnObject", payload["summary"]["redacted_fields"])
        self.assertIn("ShooterPlayerController.ClientReceiveMyTribeOnlineList.OnlinePlayerIDs", payload["summary"]["redacted_fields"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["public_tribe_sdk_ready"])
        self.assertFalse(payload["public_abi_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["identity_ready"])
        self.assertFalse(payload["lookup_ready"])
        self.assertFalse(payload["mutation_ready"])
        self.assertFalse(payload["return_override_ready"])
        self.assertFalse(payload["resource_handle_ready"])
        self.assertFalse(payload["v1_completion_ready"])
        self.assertFalse(payload["promotion_ready"])

    def test_build_report_can_be_called_directly(self) -> None:
        report = readiness.build_report(FIXTURE_ROOT)
        self.assertTrue(report["ready"])
        self.assertIn(
            "ShooterPlayerController.AllowTribeGroupPermission.TribeGroupPermission",
            report["summary"]["accepted_scalar_fields"],
        )

    def test_missing_required_snapshot_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            self.snapshot_path(root, "ShooterPlayerController.IsInTribe").unlink()
            result = self.run_checker("--snapshot-root", str(root), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("required_target_snapshot_missing", reasons)
        self.assertFalse(payload["public_tribe_sdk_ready"])

    def test_optional_tribe_log_control_may_be_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            self.snapshot_path(root, "ShooterPlayerController.ServerRequestTribeLog").unlink()
            result = self.run_checker("--snapshot-root", str(root))

        payload = json.loads(result.stdout)
        self.assertEqual(0, result.returncode)
        self.assertTrue(payload["ready"])
        self.assertIsNone(payload["server_request_tribe_log_control_ready"])

    def test_onobject_must_remain_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "ShooterPlayerController.AllowTribeGroupPermission")
            properties = payload["targets"][0]["property_chain"]["properties"]
            payload["targets"][0]["property_chain"]["properties"] = [
                prop for prop in properties if prop["name"] != "OnObject"
            ]
            payload["targets"][0]["property_chain"]["expected_count"] = 2
            payload["targets"][0]["property_chain"]["observed_count"] = 2
            payload["targets"][0]["num_parms"] = 2
            self.write_snapshot(root, "ShooterPlayerController.AllowTribeGroupPermission", payload)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("required_redacted_field_missing", reasons)

    def test_online_list_array_shape_must_not_be_scalarized(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "ShooterPlayerController.ClientReceiveMyTribeOnlineList")
            prop = payload["targets"][0]["property_chain"]["properties"][0]
            prop["class_name"] = "BoolProperty"
            prop["element_size"] = 1
            prop["bool_byte_offset"] = 0
            prop["bool_field_size"] = 1
            prop["byte_mask"] = "0x1"
            prop["field_mask"] = "0xff"
            prop["native_bool"] = False
            prop["bool_property_semantics"] = {"status": "candidate", "bool_byte_offset": 0, "bool_field_size": 1}
            self.write_snapshot(root, "ShooterPlayerController.ClientReceiveMyTribeOnlineList", payload)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("online_list_array_shape_mismatch", reasons)
        self.assertFalse(output["identity_ready"])

    def test_string_or_log_payload_on_control_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "ShooterPlayerController.ServerRequestTribeLog")
            target = payload["targets"][0]
            target["num_parms"] = 1
            target["parms_size"] = 16
            target["return_value_offset"] = "0xffff"
            target["property_chain"]["expected_count"] = 1
            target["property_chain"]["observed_count"] = 1
            target["property_chain"]["parms_size"] = 16
            target["property_chain"]["properties"] = [
                {
                    "array_dim": 1,
                    "class_membership_status": "candidate-uobject",
                    "class_name": "StrProperty",
                    "depth": 0,
                    "element_size": 16,
                    "membership_status": "candidate-uobject",
                    "name": "TribeLogText",
                    "offset_internal": 0,
                    "outer_membership_status": "candidate-uobject",
                    "property_flags": "0x80",
                    "reject_reasons": [],
                    "status": "candidate",
                }
            ]
            self.write_snapshot(root, "ShooterPlayerController.ServerRequestTribeLog", payload)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("server_request_tribe_log_not_zero_param", reasons)
        self.assertIn("string_or_log_payload_present", reasons)

    def test_identity_scalar_in_required_target_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "ShooterPlayerController.IsInTribe")
            target = payload["targets"][0]
            target["num_parms"] = 2
            target["parms_size"] = 5
            target["property_chain"]["expected_count"] = 2
            target["property_chain"]["observed_count"] = 2
            target["property_chain"]["properties"].append(
                {
                    "array_dim": 1,
                    "class_membership_status": "candidate-uobject",
                    "class_name": "IntProperty",
                    "depth": 1,
                    "element_size": 4,
                    "membership_status": "candidate-uobject",
                    "name": "TribeID",
                    "offset_internal": 1,
                    "outer_membership_status": "candidate-uobject",
                    "property_flags": "0x80",
                    "reject_reasons": [],
                    "status": "candidate",
                }
            )
            self.write_snapshot(root, "ShooterPlayerController.IsInTribe", payload)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("forbidden_identity_field_in_required_target", reasons)
        self.assertFalse(output["identity_ready"])
        self.assertFalse(output["lookup_ready"])

    def test_bool_return_shape_must_be_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "ShooterPlayerController.IsInTribe")
            prop = payload["targets"][0]["property_chain"]["properties"][0]
            prop["native_bool"] = True
            prop["byte_mask"] = "0xff"
            self.write_snapshot(root, "ShooterPlayerController.IsInTribe", payload)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("bool_scalar_metadata_mismatch", reasons)

    def test_permission_enum_shape_must_match_expected_byte_property(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "ShooterPlayerController.AllowTribeGroupPermission")
            prop = payload["targets"][0]["property_chain"]["properties"][0]
            prop["class_name"] = "IntProperty"
            prop["element_size"] = 4
            prop.pop("enum_candidate", None)
            self.write_snapshot(root, "ShooterPlayerController.AllowTribeGroupPermission", payload)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("accepted_scalar_shape_mismatch", reasons)
        self.assertIn("byte_enum_candidate_missing", reasons)

    def test_public_runtime_or_v1_readiness_claims_in_fixtures_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "ShooterPlayerController.IsInTribe")
            payload["public_sdk_ready"] = True
            payload["runtime_ready"] = True
            payload["v1_completion_ready"] = True
            self.write_snapshot(root, "ShooterPlayerController.IsInTribe", payload)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("forbidden_readiness_claim", reasons)
        self.assertFalse(output["public_sdk_ready"])
        self.assertFalse(output["runtime_ready"])
        self.assertFalse(output["v1_completion_ready"])

    def test_snapshot_root_must_not_be_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            symlink = Path(temp_dir) / "linked-snapshots"
            symlink.symlink_to(root, target_is_directory=True)
            result = self.run_checker("--snapshot-root", str(symlink), check=False)

        output = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("path_rejected", reasons)


if __name__ == "__main__":
    unittest.main()
