#!/usr/bin/env python3
"""Tests for check_dino_scalar_readiness.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_dino_scalar_readiness.py"
sys.path.insert(0, str(SCRIPT_DIR))
import check_dino_scalar_readiness as readiness  # noqa: E402
import build_redacted_ufunction_signatures as build_tool  # noqa: E402


class CheckDinoScalarReadinessTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def copy_minimal_repo(self, root: Path) -> Path:
        dst = root / "repo"
        for relative in (
            "ue/DinoReflection.cpp",
            "ue/DinoReflection.h",
            "hooks/ProcessEventDinoReflection.cpp",
            "hooks/ProcessEventDinoReflection.h",
            "tests/core/DinoReflectionTests.cpp",
            "tests/core/ProcessEventDinoReflectionTests.cpp",
            "docs/research/2026-05-31-dino-scalar-policy-planning.md",
            "scripts/reflection_target_sets.py",
        ):
            target = dst / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO_ROOT / relative, target)
        return dst

    def write_report(self, root: Path, payload: dict) -> Path:
        report = root / "dino-report.json"
        report.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return report

    def make_report(self) -> dict:
        return build_tool.build_report(
            snapshot_root=REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots",
            target_sets=["dino-compact-intake"],
        )

    def test_current_tree_is_candidate_ready_but_not_public_runtime_or_v1_ready(self) -> None:
        result = self.run_checker("--json")

        payload = json.loads(result.stdout)
        self.assertEqual("obelisk.dino-scalar-readiness-check.v1", payload["schema"])
        self.assertTrue(payload["ready"])
        self.assertEqual(readiness.NON_AUTHORIZING_READY_SCOPE, payload["ready_scope"])
        self.assertTrue(
            set(readiness.NON_AUTHORIZING_READY_DOES_NOT_SATISFY)
            <= set(payload["does_not_satisfy_readiness"])
        )
        self.assertTrue(payload["accepted_for_internal_planning"])
        self.assertTrue(payload["offline_only"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertEqual(0, payload["sdk_progress"])
        beta_capture = payload["beta_capture_prep"]
        self.assertEqual("future_capture_targets_only", beta_capture["status"])
        self.assertEqual("dino", beta_capture["surface"])
        self.assertEqual("dino-compact-intake", beta_capture["target_set"])
        self.assertEqual("dedicated_beta_capture_check_required", beta_capture["capture_gate"])
        self.assertFalse(beta_capture["public_sdk_ready"])
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
        self.assertEqual(
            {
                "PrimalDinoCharacter.AddPassenger",
                "PrimalDinoCharacter.AllowCarryCharacter",
            },
            {entry["target"] for entry in beta_capture["targets"]},
        )
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
        self.assertFalse(payload["dino_sdk_ready"])
        self.assertFalse(payload["sdk_ready"])
        self.assertFalse(payload["module_sdk_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["public_dino_sdk_ready"])
        self.assertFalse(payload["public_abi_ready"])
        self.assertFalse(payload["public_api_ready"])
        self.assertFalse(payload["public_callback_ready"])
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
        self.assertFalse(payload["runtime_hook_ready"])
        self.assertFalse(payload["runtime_wiring_ready"])
        self.assertFalse(payload["runtime_observer_approved"])
        self.assertFalse(payload["dispatcher_ready"])
        self.assertFalse(payload["callback_ready"])
        self.assertFalse(payload["descriptor_ready"])
        self.assertFalse(payload["capability_ready"])
        self.assertFalse(payload["identity_ready"])
        self.assertFalse(payload["lookup_ready"])
        self.assertFalse(payload["mutation_ready"])
        self.assertFalse(payload["return_override_ready"])
        self.assertFalse(payload["resource_handle_ready"])
        self.assertFalse(payload["v1_accounted"])
        self.assertFalse(payload["v1_completion"])
        self.assertFalse(payload["v1_completion_ready"])
        self.assertFalse(payload["p0_dependency_chain_accounted"])
        self.assertFalse(payload["p0_dependency_chain_ready"])
        self.assertFalse(payload["public_or_runtime_accounting_allowed"])
        self.assertFalse(payload["counts_toward_public_sdk"])
        self.assertFalse(payload["counts_toward_runtime"])
        self.assertFalse(payload["counts_toward_v1_completion"])
        self.assertFalse(payload["counts_toward_complete_sdk_claim"])
        self.assertFalse(payload["counts_toward_p0_dependency_chain_claim"])
        self.assertFalse(payload["complete_sdk_claim_allowed"])
        self.assertFalse(payload["stable_claim_allowed"])
        self.assertEqual(0, payload["complete_sdk_claim_progress_contribution"])
        self.assertEqual(0, payload["p0_dependency_chain_claim_progress_contribution"])
        self.assertFalse(payload["promotion_ready"])
        self.assertTrue(payload["scalar_only_ready"])
        self.assertTrue(payload["precall_scalar_ready"])
        self.assertFalse(payload["postcall_return_ready"])
        self.assertEqual(
            {
                "PrimalDinoCharacter.AddPassenger.bAllowFlyersAndWaterDinos",
                "PrimalDinoCharacter.AddPassenger.bForcePassenger",
                "PrimalDinoCharacter.AddPassenger.bSkipLineTrace",
                "PrimalDinoCharacter.AddPassenger.PassengerSeatIndex",
            },
            set(payload["summary"]["precall_copied_fields"]),
        )
        self.assertEqual(
            {
                "PrimalDinoCharacter.AddPassenger.ReturnValue",
                "PrimalDinoCharacter.AllowCarryCharacter.ReturnValue",
            },
            set(payload["summary"]["deferred_return_fields"]),
        )
        self.assertEqual("isolated", payload["source_isolation"]["status"])

    def test_detects_public_or_runtime_dino_wiring(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self.copy_minimal_repo(Path(temp_dir))
            public_header = repo / "include" / "obelisk" / "ObeliskApi.h"
            public_header.parent.mkdir(parents=True, exist_ok=True)
            public_header.write_text("typedef struct DinoEvent DinoEvent;\n", encoding="utf-8")
            result = self.run_checker("--repo-root", str(repo), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("public_or_runtime_dino_wiring_detected", reasons)
        self.assertFalse(payload["public_dino_sdk_ready"])

    def test_object_ref_in_copied_scalars_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            preflight = report["descriptor_preflight"]
            object_ref = dict(preflight["excluded_object_refs"][0])
            object_ref["copied_field"] = object_ref.pop("excluded_field")
            object_ref["type"] = "redacted_uobject_ref"
            object_ref["direction"] = "in"
            preflight["copied_scalars"].append(object_ref)
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("copied_scalar_coverage_mismatch", reasons)
        self.assertIn("forbidden_copied_scalar_field", reasons)

    def test_return_values_cannot_be_promoted_to_precall_or_runtime_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            for entry in report["descriptor_preflight"]["copied_scalars"]:
                if entry["copied_field"].endswith(".ReturnValue"):
                    entry["direction"] = "in"
            report["descriptor_preflight"]["public_surface"] = True
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("precall_scalar_coverage_mismatch", reasons)
        self.assertIn("deferred_return_coverage_mismatch", reasons)
        self.assertIn("public_surface_overclaim", reasons)

    def test_bool_shape_native_or_bad_masks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            for entry in report["descriptor_preflight"]["copied_scalars"]:
                if entry.get("type") == "bool":
                    entry["native_bool"] = True
                    entry["byte_mask"] = "0xff"
                    break
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("bool_scalar_metadata_mismatch", reasons)

    def test_noncanonical_bool_payload_value_in_external_report_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            for entry in report["descriptor_preflight"]["copied_scalars"]:
                if entry.get("type") == "bool":
                    entry["observedBoolValue"] = 2
                    break
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("noncanonical_bool_payload", reasons)
        paths = {
            blocker["path"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "noncanonical_bool_payload"
        }
        self.assertTrue(any(path.endswith(".observedBoolValue") for path in paths))
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["public_dino_sdk_ready"])

    def test_descriptor_assignment_public_claims_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            preflight = report["descriptor_preflight"]
            preflight["assigned_resource_kind"] = "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_DINO"
            preflight["descriptors"][0]["assigned_event_kind"] = "OBELISK_DINO_EVENT_KIND_ADD_PASSENGER"
            preflight["safety_summary"]["promotion_ready"] = True
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("assigned_resource_or_event_kind", reasons)
        self.assertIn("runtime_public_readiness_overclaim", reasons)

    def test_future_beta_capture_targets_are_allowed_as_candidate_only_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            report["beta_capture_prep"] = readiness.build_beta_capture_prep()
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path))

        payload = json.loads(result.stdout)
        self.assertEqual(0, result.returncode)
        self.assertTrue(payload["ready"])
        self.assertFalse(payload["beta_capture_prep"]["runtime_capture_ready"])
        self.assertEqual(0, payload["beta_capture_prep"]["sdk_progress"])
        self.assertFalse(payload["beta_capture_prep"]["replaces_player_principal_evidence"])

    def test_public_runtime_or_v1_readiness_claims_in_external_report_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            report["beta_capture_prep"] = readiness.build_beta_capture_prep()
            report["beta_capture_prep"]["public_sdk_ready"] = True
            report["beta_capture_prep"]["runtime_ready"] = True
            report["beta_capture_prep"]["sdk_progress"] = 1
            report["beta_capture_prep"]["replaces_player_principal_evidence"] = True
            report["beta_capture_prep"]["approved_runtime_evidence_missing"] = False
            report["beta_capture_prep"]["clears_approved_runtime_evidence_missing"] = "cleared"
            report["beta_capture_prep"]["prior_blocker"] = "identity_public_contract_gate_missing"
            report["beta_capture_prep"]["required_first_artifact"] = "dino_beta_capture_pack"
            report["beta_capture_prep"]["targets"][0]["debug_capture_ready"] = True
            report["beta_capture_prep"]["targets"][0]["sdk_progress"] = 1
            report["beta_capture_prep"]["targets"][0]["replaces_player_principal_evidence"] = True
            report["multi_surface_beta_capture_plan_queue"] = {
                "schema": "obelisk.multi-surface-beta-capture-plan-queue.v1",
                "ready_scope": "multi_surface_beta_capture_plan_queue",
                "status": "ready",
                "queueStatus": "ready",
                "approved_runtime_evidence_missing": False,
                "approvedRuntimeEvidenceMissingCleared": True,
                "current_route_blocker": "identity_public_contract_gate_missing",
                "remaining_route_blockers": [],
                "required_first_artifact": "dino_beta_capture_pack",
                "completeSdkClaimProgressContribution": "1/12",
                "candidate_surfaces": [
                    {
                        "surface": "dino_policy",
                        "captureReady": True,
                        "countsTowardSdk": True,
                        "mutationAuthorityReady": True,
                    }
                ],
            }
            report["public_sdk_ready"] = True
            report["public_dino_sdk_ready"] = True
            report["runtime_ready"] = True
            report["v1_completion_ready"] = True
            report["stable_claim_allowed"] = True
            report["counts_toward_complete_sdk_claim"] = 1
            report["complete_sdk_claim_progress_contribution"] = 1
            report["descriptor_preflight"]["public_module"] = {
                "status": "accepted",
                "result": "validated",
                "outcome": "ready",
                "progress": 1,
                "credits": 1,
                "unlocked": True,
            }
            report["descriptor_preflight"]["runtime_capture"] = {
                "outcome": "enabled",
                "progress": 1,
                "unblocked": True,
            }
            report["descriptor_preflight"]["live_ops"] = {"result": "stable", "stable": True}
            report["descriptor_preflight"]["source"] = {"ready": True, "status": "accepted", "progress": 1}
            report["descriptor_preflight"]["publicSdkStatus"] = "supported"
            report["descriptor_preflight"]["runtimeSupport"] = "enabled"
            report["descriptor_preflight"]["v1CompletionStatus"] = "release-supported"
            report["non_claims"] = ["Dino SDK unlocked for v1."]
            report["replacement_claim"] = "Dino beta capture replaces player-principal lifecycle evidence."
            report["sourceReady"] = True
            report["sourceStatus"] = "accepted"
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("forbidden_readiness_claim", reasons)
        self.assertIn("forbidden_text_claim", reasons)
        self.assertIn("beta_capture_readiness_overclaim", reasons)
        self.assertIn("approved_runtime_evidence_missing_not_preserved", reasons)
        self.assertIn("approved_runtime_evidence_missing_clearance_overclaim", reasons)
        self.assertIn("required_runtime_evidence_artifact_mismatch", reasons)
        paths = {
            blocker["path"]
            for blocker in payload["blockers"]
            if blocker["reason"]
            in {
                "approved_runtime_evidence_missing_clearance_overclaim",
                "approved_runtime_evidence_missing_not_preserved",
                "forbidden_readiness_claim",
                "forbidden_text_claim",
                "required_runtime_evidence_artifact_mismatch",
            }
        }
        self.assertIn("$.beta_capture_prep.public_sdk_ready", paths)
        self.assertIn("$.beta_capture_prep.runtime_ready", paths)
        self.assertIn("$.beta_capture_prep.sdk_progress", paths)
        self.assertIn("$.beta_capture_prep.replaces_player_principal_evidence", paths)
        self.assertIn("$.beta_capture_prep.approved_runtime_evidence_missing", paths)
        self.assertIn("$.beta_capture_prep.clears_approved_runtime_evidence_missing", paths)
        self.assertIn("$.beta_capture_prep.prior_blocker", paths)
        self.assertIn("$.beta_capture_prep.required_first_artifact", paths)
        self.assertIn("$.beta_capture_prep.targets[0].debug_capture_ready", paths)
        self.assertIn("$.beta_capture_prep.targets[0].sdk_progress", paths)
        self.assertIn("$.beta_capture_prep.targets[0].replaces_player_principal_evidence", paths)
        self.assertIn("$.multi_surface_beta_capture_plan_queue.status", paths)
        self.assertIn("$.multi_surface_beta_capture_plan_queue.queueStatus", paths)
        self.assertIn("$.multi_surface_beta_capture_plan_queue.approved_runtime_evidence_missing", paths)
        self.assertIn("$.multi_surface_beta_capture_plan_queue.approvedRuntimeEvidenceMissingCleared", paths)
        self.assertIn("$.multi_surface_beta_capture_plan_queue.current_route_blocker", paths)
        self.assertIn("$.multi_surface_beta_capture_plan_queue.remaining_route_blockers", paths)
        self.assertIn("$.multi_surface_beta_capture_plan_queue.required_first_artifact", paths)
        self.assertIn("$.multi_surface_beta_capture_plan_queue.completeSdkClaimProgressContribution", paths)
        self.assertIn("$.multi_surface_beta_capture_plan_queue.candidate_surfaces[0].captureReady", paths)
        self.assertIn("$.multi_surface_beta_capture_plan_queue.candidate_surfaces[0].countsTowardSdk", paths)
        self.assertIn("$.multi_surface_beta_capture_plan_queue.candidate_surfaces[0].mutationAuthorityReady", paths)
        self.assertIn("$.replacement_claim", paths)
        self.assertIn("$.descriptor_preflight.public_module.status", paths)
        self.assertIn("$.descriptor_preflight.public_module.result", paths)
        self.assertIn("$.descriptor_preflight.public_module.outcome", paths)
        self.assertIn("$.descriptor_preflight.public_module.progress", paths)
        self.assertIn("$.descriptor_preflight.public_module.credits", paths)
        self.assertIn("$.descriptor_preflight.public_module.unlocked", paths)
        self.assertIn("$.descriptor_preflight.runtime_capture.outcome", paths)
        self.assertIn("$.descriptor_preflight.runtime_capture.progress", paths)
        self.assertIn("$.descriptor_preflight.runtime_capture.unblocked", paths)
        self.assertIn("$.descriptor_preflight.live_ops.result", paths)
        self.assertIn("$.descriptor_preflight.live_ops.stable", paths)
        self.assertIn("$.descriptor_preflight.source.ready", paths)
        self.assertIn("$.descriptor_preflight.source.status", paths)
        self.assertIn("$.descriptor_preflight.source.progress", paths)
        self.assertIn("$.descriptor_preflight.publicSdkStatus", paths)
        self.assertIn("$.descriptor_preflight.runtimeSupport", paths)
        self.assertIn("$.descriptor_preflight.v1CompletionStatus", paths)
        self.assertIn("$.sourceReady", paths)
        self.assertIn("$.sourceStatus", paths)
        self.assertFalse(payload["public_dino_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])
        self.assertFalse(payload["counts_toward_complete_sdk_claim"])
        self.assertEqual(0, payload["complete_sdk_claim_progress_contribution"])

    def test_side_lane_source_artifacts_and_target_aliases_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            report["source_overclaim_total_flag_count"] = 0
            report["principal_start_end_runtime_evidence"] = {
                "ready_scope": "principal_start_end_runtime_evidence_only",
                "principal_start_end_runtime_evidence_ready": False,
                "resolved_inputs": ["runtime.lifecycle_start_end_evidence"],
            }
            report["passive_snapshot"] = {
                "status": "passive_snapshot_non_evidence",
                "passive_snapshot_evidence_allowed": False,
            }
            report["target_sets"] = ["dino-public-sdk-ready"]
            report["target_set_alias"] = "dino-runtime-ready"
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("source_overclaim_zero_not_allowed", reasons)
        self.assertIn("copied_start_end_player_evidence_not_allowed", reasons)
        self.assertIn("passive_snapshot_source_not_allowed", reasons)
        self.assertIn("non_current_target_alias", reasons)
        self.assertFalse(payload["ready"])

    def test_package_support_and_plugin_labels_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            report["package_shape"] = {"passed": True, "status": "release-supported"}
            report["support_tier"] = {"active": True, "status": "supported"}
            report["plugin_hub"] = {"ready": True, "status": "published"}
            report["release_note"] = "Dino package shape passed and support tier is active."
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("forbidden_readiness_claim", reasons)
        self.assertIn("forbidden_text_claim", reasons)
        paths = {
            blocker["path"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "forbidden_readiness_claim"
        }
        self.assertIn("$.package_shape.passed", paths)
        self.assertIn("$.package_shape.status", paths)
        self.assertIn("$.support_tier.active", paths)
        self.assertIn("$.support_tier.status", paths)
        self.assertIn("$.plugin_hub.ready", paths)
        self.assertIn("$.plugin_hub.status", paths)
        text_paths = {
            blocker["path"]
            for blocker in payload["blockers"]
            if blocker["reason"] == "forbidden_text_claim"
        }
        self.assertIn("$.release_note", text_paths)
        self.assertFalse(payload["public_dino_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])

    def test_missing_redacted_object_ref_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            report["descriptor_preflight"]["excluded_object_refs"] = report["descriptor_preflight"]["excluded_object_refs"][:1]
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("redacted_object_ref_coverage_mismatch", reasons)

    def test_copied_scalar_source_snapshot_must_be_known(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            report["descriptor_preflight"]["copied_scalars"][0]["source_snapshot"] = "snapshot-9999"
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("copied_scalar_source_snapshot_unknown", reasons)

    def test_report_source_snapshots_are_revalidated_against_snapshot_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            renamed = {
                snapshot["id"]: f"fabricated-{index}"
                for index, snapshot in enumerate(report["generated_from"]["input_snapshots"], start=1)
            }
            for snapshot in report["generated_from"]["input_snapshots"]:
                snapshot["id"] = renamed[snapshot["id"]]
            for collection in ("copied_scalars", "excluded_object_refs"):
                for entry in report["descriptor_preflight"][collection]:
                    entry["source_snapshot"] = renamed[entry["source_snapshot"]]
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("report_source_snapshot_revalidation_mismatch", reasons)
        self.assertFalse(payload["public_dino_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["v1_completion_ready"])

    def test_report_generated_from_current_snapshot_root_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = self.write_report(root, self.make_report())
            result = self.run_checker("--report", str(report_path))

        payload = json.loads(result.stdout)
        self.assertEqual(0, result.returncode)
        self.assertTrue(payload["ready"])
        self.assertFalse(payload["public_dino_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])

    def test_report_path_must_not_use_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = self.write_report(root, self.make_report())
            symlink = root / "linked-report.json"
            symlink.symlink_to(report_path)
            result = self.run_checker("--report", str(symlink), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("path_rejected", reasons)

    def test_report_revalidation_rejects_protected_snapshot_root_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = self.write_report(root, self.make_report())
            result = self.run_checker(
                "--report",
                str(report_path),
                "--snapshot-root",
                "/servidor/ark/live",
                "--json",
                check=False,
            )

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("path_rejected", {blocker["reason"] for blocker in payload["blockers"]})
        self.assertTrue(any(blocker.get("label") == "--snapshot-root" for blocker in payload["blockers"]))
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["public_dino_sdk_ready"])

    def test_repo_root_protected_path_is_rejected_before_source_scan(self) -> None:
        original_reject = readiness.reject_protected_input_path

        def reject_repo_root(path: Path, label: str) -> Path:
            if label == "--repo-root":
                raise SystemExit("simulated protected repo root")
            return original_reject(path, label)

        with mock.patch.object(readiness, "reject_protected_input_path", side_effect=reject_repo_root):
            with mock.patch.object(readiness, "validate_target_set") as validate_target_set:
                with mock.patch.object(readiness, "validate_source_isolation") as validate_source_isolation:
                    report = readiness.build_report(Path("/servidor/ark"))

        self.assertFalse(report["ready"])
        self.assertIn("path_rejected", {blocker["reason"] for blocker in report["blockers"]})
        self.assertTrue(any(blocker.get("label") == "--repo-root" for blocker in report["blockers"]))
        validate_target_set.assert_not_called()
        validate_source_isolation.assert_not_called()

    def test_copied_scalar_source_snapshot_sha_must_match_generated_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            report["descriptor_preflight"]["copied_scalars"][0]["source_snapshot_sha256"] = "0" * 64
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("copied_scalar_source_snapshot_sha256_mismatch", reasons)

    def test_excluded_object_ref_source_snapshot_sha_must_be_well_formed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            report["descriptor_preflight"]["excluded_object_refs"][0]["source_snapshot_sha256"] = "not-a-sha"
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("excluded_object_ref_source_snapshot_sha256_malformed", reasons)

    def test_same_target_cannot_mix_source_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            snapshots = report["generated_from"]["input_snapshots"]
            second_snapshot = snapshots[1]
            for entry in report["descriptor_preflight"]["copied_scalars"]:
                if entry["copied_field"] == "PrimalDinoCharacter.AddPassenger.bForcePassenger":
                    entry["source_snapshot"] = second_snapshot["id"]
                    entry["source_snapshot_sha256"] = second_snapshot["sha256"]
                    break
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("target_source_snapshot_inconsistent", reasons)

    def test_detects_missing_target_set_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self.copy_minimal_repo(Path(temp_dir))
            target_sets = repo / "scripts" / "reflection_target_sets.py"
            text = target_sets.read_text(encoding="utf-8")
            target_sets.write_text(text.replace("PrimalDinoCharacter.AllowCarryCharacter", "PrimalDinoCharacter.Missing"), encoding="utf-8")
            result = self.run_checker("--repo-root", str(repo), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("target_set_target_missing", reasons)

    def test_build_report_can_be_called_directly(self) -> None:
        report = readiness.build_report(REPO_ROOT)
        self.assertTrue(report["ready"])
        self.assertEqual("dino-compact-intake", report["target_set"]["target_set"])


if __name__ == "__main__":
    unittest.main()
