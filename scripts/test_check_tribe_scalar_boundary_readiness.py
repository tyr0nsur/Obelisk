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

    def beta_capture_prep_for_target(self, target: str) -> dict:
        entry = next(item for item in readiness.build_beta_capture_prep()["targets"] if item["target"] == target)
        return {
            "status": readiness.BETA_CAPTURE_STATUS,
            "target_status": entry["status"],
            "surface": entry["surface"],
            "target_set": entry["target_set"],
            "target": target,
            "target_role": entry["target_role"],
            "source_evidence": entry["source_evidence"],
            "capture_gate": entry["capture_gate"],
            "public_sdk_ready": False,
            "public_tribe_sdk_ready": False,
            "runtime_ready": False,
            "runtime_capture_ready": False,
            "debug_capture_ready": False,
            "sdk_ready": False,
            "sdk_progress": 0,
            "replaces_player_principal_evidence": False,
            "non_claims": ["does not replace player-principal lifecycle evidence"],
        }

    def test_current_tree_is_internal_candidate_only_not_public_runtime_or_v1_ready(self) -> None:
        result = self.run_checker("--json")

        payload = json.loads(result.stdout)
        self.assertEqual("obelisk.tribe-scalar-boundary-readiness-check.v1", payload["schema"])
        self.assertTrue(payload["ready"])
        self.assertEqual(readiness.NON_AUTHORIZING_READY_SCOPE, payload["ready_scope"])
        self.assertTrue(
            set(readiness.NON_AUTHORIZING_READY_DOES_NOT_SATISFY)
            <= set(payload["does_not_satisfy_readiness"])
        )
        self.assertTrue(payload["accepted_for_internal_planning"])
        self.assertTrue(payload["offline_only"])
        self.assertTrue(payload["fixture_only"])
        self.assertTrue(payload["tribe_scalar_boundary_ready"])
        self.assertEqual("tribe-compact-intake", payload["target_set"])
        self.assertEqual(0, payload["sdk_progress"])
        beta_capture = payload["beta_capture_prep"]
        self.assertEqual("future_capture_targets_only", beta_capture["status"])
        self.assertEqual("tribe", beta_capture["surface"])
        self.assertEqual("tribe-compact-intake", beta_capture["target_set"])
        self.assertEqual("dedicated_beta_capture_check_required", beta_capture["capture_gate"])
        self.assertFalse(beta_capture["public_sdk_ready"])
        self.assertFalse(beta_capture["public_tribe_sdk_ready"])
        self.assertFalse(beta_capture["runtime_ready"])
        self.assertFalse(beta_capture["runtime_capture_ready"])
        self.assertFalse(beta_capture["debug_capture_ready"])
        self.assertFalse(beta_capture["sdk_ready"])
        self.assertEqual(0, beta_capture["sdk_progress"])
        self.assertFalse(beta_capture["approved_runtime_evidence"])
        self.assertFalse(beta_capture["approved_runtime_evidence_ready"])
        self.assertTrue(beta_capture["approved_runtime_evidence_missing"])
        self.assertFalse(beta_capture["approved_runtime_evidence_missing_cleared"])
        self.assertFalse(beta_capture["clears_approved_runtime_evidence_missing"])
        self.assertFalse(beta_capture["counts_as_approved_runtime_evidence"])
        self.assertFalse(beta_capture["counts_as_runtime_evidence"])
        self.assertEqual("approved_runtime_evidence_missing", beta_capture["prior_blocker"])
        self.assertEqual(
            "approved_runtime_principal_lifecycle_evidence_bundle",
            beta_capture["required_first_artifact"],
        )
        self.assertFalse(beta_capture["replaces_player_principal_evidence"])
        self.assertEqual(readiness.CONSIDERED_TARGETS, {entry["target"] for entry in beta_capture["targets"]})
        for entry in beta_capture["targets"]:
            self.assertEqual("future_capture_target", entry["status"])
            self.assertFalse(entry["public_sdk_ready"])
            self.assertFalse(entry["runtime_ready"])
            self.assertFalse(entry["runtime_capture_ready"])
            self.assertFalse(entry["sdk_ready"])
            self.assertEqual(0, entry["sdk_progress"])
            self.assertTrue(entry["approved_runtime_evidence_missing"])
            self.assertFalse(entry["clears_approved_runtime_evidence_missing"])
            self.assertEqual("approved_runtime_evidence_missing", entry["prior_blocker"])
            self.assertFalse(entry["replaces_player_principal_evidence"])
        self.assertTrue(payload["server_request_tribe_log_control_ready"])
        self.assertEqual(
            [
                {
                    "present": True,
                    "ready": True,
                    "required": True,
                    "target": "ShooterPlayerController.ServerRequestTribeLog",
                    "zero_param": True,
                }
            ],
            payload["summary"]["required_controls"],
        )
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
        self.assertFalse(payload["approved_runtime_evidence"])
        self.assertFalse(payload["approved_runtime_evidence_ready"])
        self.assertTrue(payload["approved_runtime_evidence_missing"])
        self.assertFalse(payload["clears_approved_runtime_evidence_missing"])
        self.assertFalse(payload["counts_as_approved_runtime_evidence"])
        self.assertEqual("approved_runtime_evidence_missing", payload["current_route_blocker"])
        self.assertEqual(["approved_runtime_evidence_missing"], payload["remaining_route_blockers"])
        self.assertEqual(
            "approved_runtime_principal_lifecycle_evidence_bundle",
            payload["required_first_artifact"],
        )
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

    def test_future_beta_capture_target_metadata_is_allowed_as_candidate_only_fixture_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            target_name = "ShooterPlayerController.IsInTribe"
            payload = self.read_snapshot(root, target_name)
            payload["beta_capture_prep"] = self.beta_capture_prep_for_target(target_name)
            self.write_snapshot(root, target_name, payload)
            result = self.run_checker("--snapshot-root", str(root))

        output = json.loads(result.stdout)
        self.assertEqual(0, result.returncode)
        self.assertTrue(output["ready"])
        self.assertFalse(output["beta_capture_prep"]["runtime_capture_ready"])
        self.assertEqual(0, output["beta_capture_prep"]["sdk_progress"])
        self.assertFalse(output["beta_capture_prep"]["replaces_player_principal_evidence"])

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

    def test_required_tribe_log_control_must_be_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            self.snapshot_path(root, "ShooterPlayerController.ServerRequestTribeLog").unlink()
            result = self.run_checker("--snapshot-root", str(root), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertFalse(payload["server_request_tribe_log_control_ready"])
        self.assertEqual(
            [
                {
                    "present": False,
                    "ready": False,
                    "required": True,
                    "target": "ShooterPlayerController.ServerRequestTribeLog",
                    "zero_param": None,
                }
            ],
            payload["summary"]["required_controls"],
        )
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("required_target_snapshot_missing", reasons)

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

    def test_noncanonical_bool_payload_value_in_snapshot_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "ShooterPlayerController.IsInTribe")
            prop = payload["targets"][0]["property_chain"]["properties"][0]
            prop["observedBoolValue"] = 2
            self.write_snapshot(root, "ShooterPlayerController.IsInTribe", payload)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("noncanonical_bool_payload", reasons)
        paths = {
            blocker["path"]
            for blocker in output["blockers"]
            if blocker["reason"] == "noncanonical_bool_payload"
        }
        self.assertTrue(any(path.endswith(".observedBoolValue") for path in paths))
        self.assertFalse(output["runtime_ready"])
        self.assertFalse(output["public_tribe_sdk_ready"])

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
            payload["beta_capture_prep"] = self.beta_capture_prep_for_target("ShooterPlayerController.IsInTribe")
            payload["beta_capture_prep"]["public_sdk_ready"] = True
            payload["beta_capture_prep"]["runtime_ready"] = True
            payload["beta_capture_prep"]["debug_capture_ready"] = True
            payload["beta_capture_prep"]["sdk_progress"] = 1
            payload["beta_capture_prep"]["replaces_player_principal_evidence"] = True
            payload["beta_capture_prep"]["approved_runtime_evidence_missing"] = False
            payload["beta_capture_prep"]["clears_approved_runtime_evidence_missing"] = "cleared"
            payload["beta_capture_prep"]["prior_blocker"] = "identity_public_contract_gate_missing"
            payload["beta_capture_prep"]["required_first_artifact"] = "tribe_beta_capture_pack"
            payload["beta_capture_prep"]["notes"] = (
                "Tribe beta capture replaces player-principal lifecycle evidence."
            )
            payload["multi_surface_beta_capture_plan_queue"] = {
                "schema": "obelisk.multi-surface-beta-capture-plan-queue.v1",
                "ready_scope": "multi_surface_beta_capture_plan_queue",
                "status": "ready",
                "queueStatus": "ready",
                "approved_runtime_evidence_missing": False,
                "approvedRuntimeEvidenceMissingCleared": True,
                "current_route_blocker": "identity_public_contract_gate_missing",
                "remaining_route_blockers": [],
                "required_first_artifact": "tribe_beta_capture_pack",
                "completeSdkClaimProgressContribution": "1/12",
                "candidate_surfaces": [
                    {
                        "surface": "tribe_policy",
                        "captureReady": True,
                        "countsTowardSdk": True,
                        "mutationAuthorityReady": True,
                    }
                ],
            }
            payload["public_sdk_ready"] = True
            payload["runtime_ready"] = True
            payload["v1_completion_ready"] = True
            payload["counts_toward_p0_dependency_chain_claim"] = True
            payload["public_module"] = {
                "status": "accepted",
                "result": "validated",
                "outcome": "ready",
                "progress": 1,
            }
            payload["runtime_capture"] = {"outcome": "enabled", "progress": 1}
            payload["live_ops"] = {"result": "stable", "stable": True}
            payload["source"] = {"ready": True, "status": "accepted", "progress": 1}
            payload["publicSdkStatus"] = "supported"
            payload["runtimeSupport"] = "enabled"
            payload["v1CompletionStatus"] = "release-supported"
            payload["sourceReady"] = True
            payload["sourceStatus"] = "accepted"
            self.write_snapshot(root, "ShooterPlayerController.IsInTribe", payload)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("forbidden_readiness_claim", reasons)
        self.assertIn("forbidden_text_claim", reasons)
        self.assertIn("beta_capture_readiness_overclaim", reasons)
        self.assertIn("approved_runtime_evidence_missing_not_preserved", reasons)
        self.assertIn("approved_runtime_evidence_missing_clearance_overclaim", reasons)
        self.assertIn("required_runtime_evidence_artifact_mismatch", reasons)
        paths = {
            blocker["path"]
            for blocker in output["blockers"]
            if blocker["reason"]
            in {
                "approved_runtime_evidence_missing_clearance_overclaim",
                "approved_runtime_evidence_missing_not_preserved",
                "forbidden_readiness_claim",
                "forbidden_text_claim",
                "required_runtime_evidence_artifact_mismatch",
            }
        }
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.beta_capture_prep.public_sdk_ready", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.beta_capture_prep.runtime_ready", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.beta_capture_prep.debug_capture_ready", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.beta_capture_prep.sdk_progress", paths)
        self.assertIn(
            "$.snapshots.ShooterPlayerController.IsInTribe.beta_capture_prep.replaces_player_principal_evidence",
            paths,
        )
        self.assertIn(
            "$.snapshots.ShooterPlayerController.IsInTribe.beta_capture_prep.approved_runtime_evidence_missing",
            paths,
        )
        self.assertIn(
            "$.snapshots.ShooterPlayerController.IsInTribe.beta_capture_prep.clears_approved_runtime_evidence_missing",
            paths,
        )
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.beta_capture_prep.prior_blocker", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.beta_capture_prep.required_first_artifact", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.beta_capture_prep.notes", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.multi_surface_beta_capture_plan_queue.status", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.multi_surface_beta_capture_plan_queue.queueStatus", paths)
        self.assertIn(
            "$.snapshots.ShooterPlayerController.IsInTribe.multi_surface_beta_capture_plan_queue.approved_runtime_evidence_missing",
            paths,
        )
        self.assertIn(
            "$.snapshots.ShooterPlayerController.IsInTribe.multi_surface_beta_capture_plan_queue.approvedRuntimeEvidenceMissingCleared",
            paths,
        )
        self.assertIn(
            "$.snapshots.ShooterPlayerController.IsInTribe.multi_surface_beta_capture_plan_queue.current_route_blocker",
            paths,
        )
        self.assertIn(
            "$.snapshots.ShooterPlayerController.IsInTribe.multi_surface_beta_capture_plan_queue.remaining_route_blockers",
            paths,
        )
        self.assertIn(
            "$.snapshots.ShooterPlayerController.IsInTribe.multi_surface_beta_capture_plan_queue.required_first_artifact",
            paths,
        )
        self.assertIn(
            "$.snapshots.ShooterPlayerController.IsInTribe.multi_surface_beta_capture_plan_queue.completeSdkClaimProgressContribution",
            paths,
        )
        self.assertIn(
            "$.snapshots.ShooterPlayerController.IsInTribe.multi_surface_beta_capture_plan_queue.candidate_surfaces[0].captureReady",
            paths,
        )
        self.assertIn(
            "$.snapshots.ShooterPlayerController.IsInTribe.multi_surface_beta_capture_plan_queue.candidate_surfaces[0].countsTowardSdk",
            paths,
        )
        self.assertIn(
            "$.snapshots.ShooterPlayerController.IsInTribe.multi_surface_beta_capture_plan_queue.candidate_surfaces[0].mutationAuthorityReady",
            paths,
        )
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.counts_toward_p0_dependency_chain_claim", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.public_module.status", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.public_module.result", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.public_module.outcome", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.public_module.progress", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.runtime_capture.outcome", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.runtime_capture.progress", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.live_ops.result", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.live_ops.stable", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.source.ready", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.source.status", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.source.progress", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.publicSdkStatus", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.runtimeSupport", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.v1CompletionStatus", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.sourceReady", paths)
        self.assertIn("$.snapshots.ShooterPlayerController.IsInTribe.sourceStatus", paths)
        self.assertFalse(output["public_sdk_ready"])
        self.assertFalse(output["runtime_ready"])
        self.assertFalse(output["v1_completion_ready"])

    def test_side_lane_source_artifacts_and_target_aliases_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "ShooterPlayerController.IsInTribe")
            payload["source_overclaim_total_flag_count"] = 0
            payload["principal_start_end_runtime_evidence"] = {
                "ready_scope": "principal_start_end_runtime_evidence_only",
                "principal_start_end_runtime_evidence_ready": False,
                "resolved_inputs": ["runtime.lifecycle_start_end_evidence"],
            }
            payload["passive_snapshot"] = {
                "status": "passive_snapshot_non_evidence",
                "passive_snapshot_evidence_allowed": False,
            }
            payload["target_sets"] = ["players-lifecycle-anchor-candidates"]
            payload["target_set_alias"] = "tribe-runtime-ready"
            self.write_snapshot(root, "ShooterPlayerController.IsInTribe", payload)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("source_overclaim_zero_not_allowed", reasons)
        self.assertIn("copied_start_end_player_evidence_not_allowed", reasons)
        self.assertIn("passive_snapshot_source_not_allowed", reasons)
        self.assertIn("non_current_target_alias", reasons)
        self.assertFalse(output["ready"])

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
            snapshot = self.snapshot_path(root, "ShooterPlayerController.IsInTribe")
            real_snapshot = Path(temp_dir) / "outside.snapshot.json"
            shutil.copy2(snapshot, real_snapshot)
            snapshot.unlink()
            snapshot.symlink_to(real_snapshot)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("path_rejected", reasons)
        self.assertIn("required_target_snapshot_missing", reasons)


if __name__ == "__main__":
    unittest.main()
