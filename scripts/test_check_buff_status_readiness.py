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
        snapshot_root = root / "snapshots"
        snapshot_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FIXTURE_ROOT / "manifest.json", snapshot_root / "manifest.json")
        dst = snapshot_root / "7e7ded49e0c6" / "sdk_buffs"
        dst.mkdir(parents=True, exist_ok=True)
        for source in BUFF_FIXTURE_DIR.glob("*.snapshot.json"):
            shutil.copy2(source, dst / source.name)
        return snapshot_root

    def manifest_path(self, root: Path) -> Path:
        return root / "manifest.json"

    def read_manifest(self, root: Path) -> dict:
        return json.loads(self.manifest_path(root).read_text(encoding="utf-8"))

    def write_manifest(self, root: Path, payload: dict) -> None:
        self.manifest_path(root).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

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
        self.assertEqual(readiness.NON_AUTHORIZING_READY_SCOPE, payload["ready_scope"])
        self.assertTrue(
            set(readiness.NON_AUTHORIZING_READY_DOES_NOT_SATISFY)
            <= set(payload["does_not_satisfy_readiness"])
        )
        self.assertTrue(payload["accepted_for_internal_planning"])
        self.assertTrue(payload["candidate_only"])
        self.assertEqual("candidate-only", payload["artifact_status"])
        self.assertEqual("internal_layout_only", payload["readiness_classification"])
        self.assertTrue(payload["offline_only"])
        self.assertTrue(payload["fixture_only"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertEqual("approved_runtime_evidence_missing", payload["current_sdk_blocker"])
        self.assertEqual(["approved_runtime_evidence_missing"], payload["remaining_blockers"])
        self.assertFalse(payload["approved_runtime_evidence_ready"])
        self.assertFalse(payload["runtime_evidence_ready"])
        self.assertFalse(payload["player_principal_runtime_evidence_ready"])
        self.assertFalse(payload["clears_approved_runtime_evidence_missing"])
        self.assertFalse(payload["counts_as_approved_runtime_evidence"])
        self.assertFalse(payload["replaces_player_principal_evidence"])
        beta_capture = payload["beta_capture_prep"]
        self.assertEqual("future_capture_targets_only", beta_capture["status"])
        self.assertEqual("buff_status", beta_capture["surface"])
        self.assertEqual("dedicated_beta_capture_check_required", beta_capture["capture_gate"])
        self.assertFalse(beta_capture["approved_runtime_evidence_ready"])
        self.assertFalse(beta_capture["runtime_evidence_ready"])
        self.assertFalse(beta_capture["clears_approved_runtime_evidence_missing"])
        self.assertFalse(beta_capture["player_principal_runtime_evidence_ready"])
        self.assertFalse(beta_capture["replaces_player_principal_evidence"])
        self.assertFalse(beta_capture["public_sdk_ready"])
        self.assertFalse(beta_capture["runtime_ready"])
        self.assertFalse(beta_capture["p0_dependency_chain_ready"])
        self.assertFalse(beta_capture["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(0, beta_capture["sdk_progress"])
        self.assertEqual(6, len(beta_capture["targets"]))
        self.assertTrue(payload["buff_status_candidate_ready"])
        self.assertTrue(payload["copied_bool_boundary_ready"])
        self.assertTrue(payload["class_object_redaction_ready"])
        self.assertTrue(payload["zero_param_lifecycle_shape_ready"])
        self.assertFalse(payload["copied_payload_policy_ready"])
        self.assertFalse(payload["lifecycle_semantics_ready"])
        self.assertFalse(payload["buff_status_sdk_ready"])
        self.assertFalse(payload["public_buff_status_sdk_ready"])
        self.assertFalse(payload["buff_public_module_ready"])
        self.assertFalse(payload["buff_public_module_sdk_ready"])
        self.assertFalse(payload["public_buff_module_ready"])
        self.assertFalse(payload["buff_status_public_abi_ready"])
        self.assertFalse(payload["buff_status_public_c_abi_ready"])
        self.assertFalse(payload["buff_status_callback_ready"])
        self.assertFalse(payload["buff_status_sdk_available"])
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
        self.assertFalse(payload["candidate_capture_evidence_ready"])
        self.assertFalse(payload["debug_capture_evidence_ready"])
        self.assertEqual(0, payload["candidate_capture_progress_contribution"])
        self.assertFalse(payload["v1_accounted"])
        self.assertFalse(payload["v1_completion"])
        self.assertFalse(payload["v1_completion_ready"])
        self.assertEqual(0, payload["v1_completion_contribution"])
        self.assertFalse(payload["complete_sdk_ready"])
        self.assertFalse(payload["stable_claim_allowed"])
        self.assertFalse(payload["complete_sdk_claim_allowed"])
        self.assertFalse(payload["counts_toward_complete_sdk_claim"])
        self.assertEqual(0, payload["complete_sdk_claim_progress_contribution"])
        self.assertFalse(payload["p0_ready"])
        self.assertFalse(payload["p0_dependency_chain_accounted"])
        self.assertFalse(payload["p0_dependency_chain_ready"])
        self.assertFalse(payload["counts_toward_p0_dependency_chain_claim"])
        self.assertFalse(payload["counts_toward_public_sdk"])
        self.assertFalse(payload["counts_toward_runtime"])
        self.assertFalse(payload["counts_toward_v1_completion"])
        self.assertEqual(0, payload["p0_dependency_chain_claim_progress_contribution"])
        self.assertFalse(payload["promotion_ready"])
        self.assertEqual("obelisk.ufunction-snapshot-manifest.v1", payload["source_manifest"]["schema"])
        self.assertEqual("candidate-only", payload["source_manifest"]["status"])
        self.assertEqual("offline_core", payload["source_manifest"]["source"])
        self.assertEqual(6, payload["source_manifest"]["sdk_buffs_target_count"])
        self.assertEqual(6, payload["source_manifest"]["bound_target_count"])
        self.assertEqual(6, payload["summary"]["source_binding_count"])
        for binding in payload["summary"]["source_bindings"]:
            self.assertEqual("sdk_buffs", binding["manifest_module"])
            self.assertTrue(binding["fixture_path"].startswith("7e7ded49e0c6/sdk_buffs/"))
            self.assertEqual("offline_core", binding["evidence_source"])
            self.assertEqual("candidate-only", binding["evidence_status"])
            self.assertEqual("offline_core", binding["artifact_kind"])
            self.assertRegex(binding["source_snapshot_sha256"], r"^[0-9a-f]{64}$")
            self.assertIn(binding["target_sets"][0], {"buff-compact-intake", "buff-breadth-intake"})
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
        self.assertIn(
            "candidate/debug captures before checker acceptance are non-evidence and non-progress",
            " ".join(payload["non_claims"]),
        )
        self.assertIn("beta capture prep is future target planning only", " ".join(payload["non_claims"]))
        self.assertIn("does not clear approved_runtime_evidence_missing", " ".join(payload["non_claims"]))

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

    def test_missing_manifest_entry_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            manifest = self.read_manifest(root)
            manifest["targets"] = [
                entry
                for entry in manifest["targets"]
                if not (
                    entry.get("module") == "sdk_buffs"
                    and entry.get("outer") == "PrimalBuff"
                    and entry.get("name") == "BPBuffPreventUploading"
                )
            ]
            self.write_manifest(root, manifest)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("manifest_target_missing", reasons)
        self.assertIn("snapshot_without_manifest_entry", reasons)
        self.assertIn("required_target_snapshot_missing", reasons)
        self.assertFalse(payload["ready"])

    def test_manifest_sdk_buffs_module_binding_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            manifest = self.read_manifest(root)
            for entry in manifest["targets"]:
                if entry.get("module") == "sdk_buffs" and entry.get("name") == "AllowPostProcessEffect":
                    entry["module"] = "sdk_items"
                    break
            self.write_manifest(root, manifest)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("manifest_target_module_mismatch", reasons)
        self.assertIn("misplaced_target_snapshot", reasons)
        self.assertIn("required_target_snapshot_missing", reasons)
        self.assertFalse(payload["public_buff_status_sdk_ready"])

    def test_misplaced_snapshot_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            source = self.snapshot_path(root, "PrimalBuff.BPCustomAllowAddBuff")
            misplaced = root / "7e7ded49e0c6" / "not_sdk_buffs" / source.name
            misplaced.parent.mkdir(parents=True)
            shutil.move(str(source), misplaced)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("misplaced_target_snapshot", reasons)
        self.assertIn("required_target_snapshot_missing", reasons)
        self.assertFalse(payload["ready"])

    def test_duplicate_manifest_entry_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            manifest = self.read_manifest(root)
            duplicate = next(
                entry
                for entry in manifest["targets"]
                if entry.get("module") == "sdk_buffs" and entry.get("name") == "AllowPostProcessEffect"
            )
            manifest["targets"].append(dict(duplicate))
            self.write_manifest(root, manifest)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("manifest_target_duplicate", reasons)
        self.assertFalse(payload["ready"])

    def test_duplicate_target_snapshot_copy_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            source = self.snapshot_path(root, "PrimalBuff.AllowPostProcessEffect")
            duplicate = source.parent / "zz_duplicate" / source.name
            duplicate.parent.mkdir()
            shutil.copy2(source, duplicate)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        payload = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("duplicate_target_snapshot", reasons)
        self.assertIn("misplaced_target_snapshot", reasons)
        self.assertFalse(payload["ready"])

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

    def test_noncanonical_bool_payload_value_in_snapshot_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "PrimalBuff.AllowPostProcessEffect")
            prop = payload["targets"][0]["property_chain"]["properties"][0]
            prop["sampleBoolBytes"] = [0, 2]
            self.write_snapshot(root, "PrimalBuff.AllowPostProcessEffect", payload)
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
        self.assertTrue(any(path.endswith(".sampleBoolBytes[1]") for path in paths))
        self.assertFalse(output["runtime_ready"])
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
            payload["p0_dependency_chain_ready"] = True
            payload["counts_toward_p0_dependency_chain_claim"] = True
            payload["complete_sdk_claim_progress_contribution"] = 1
            payload["buff_public_module_ready"] = True
            payload["public_module"] = {
                "status": "accepted",
                "result": "validated",
                "outcome": "ready",
                "progress": 1,
                "credits": 1,
                "unlocked": True,
            }
            payload["runtime_capture"] = {"outcome": "enabled", "progress": 1, "unblocked": True}
            payload["live_ops"] = {"result": "stable", "stable": True}
            payload["source"] = {"ready": True, "status": "accepted", "progress": 1}
            payload["sourceReady"] = True
            payload["sourceStatus"] = "accepted"
            self.write_snapshot(root, "PrimalBuff.AllowPostProcessEffect", payload)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("forbidden_readiness_claim", reasons)
        paths = {
            blocker["path"]
            for blocker in output["blockers"]
            if blocker["reason"] in {"forbidden_readiness_claim", "forbidden_text_claim"}
        }
        self.assertIn("$.snapshots.PrimalBuff.AllowPostProcessEffect.public_module.status", paths)
        self.assertIn("$.snapshots.PrimalBuff.AllowPostProcessEffect.public_module.result", paths)
        self.assertIn("$.snapshots.PrimalBuff.AllowPostProcessEffect.public_module.outcome", paths)
        self.assertIn("$.snapshots.PrimalBuff.AllowPostProcessEffect.public_module.progress", paths)
        self.assertIn("$.snapshots.PrimalBuff.AllowPostProcessEffect.public_module.credits", paths)
        self.assertIn("$.snapshots.PrimalBuff.AllowPostProcessEffect.public_module.unlocked", paths)
        self.assertIn("$.snapshots.PrimalBuff.AllowPostProcessEffect.runtime_capture.outcome", paths)
        self.assertIn("$.snapshots.PrimalBuff.AllowPostProcessEffect.runtime_capture.progress", paths)
        self.assertIn("$.snapshots.PrimalBuff.AllowPostProcessEffect.runtime_capture.unblocked", paths)
        self.assertIn("$.snapshots.PrimalBuff.AllowPostProcessEffect.live_ops.result", paths)
        self.assertIn("$.snapshots.PrimalBuff.AllowPostProcessEffect.live_ops.stable", paths)
        self.assertIn("$.snapshots.PrimalBuff.AllowPostProcessEffect.source.ready", paths)
        self.assertIn("$.snapshots.PrimalBuff.AllowPostProcessEffect.source.status", paths)
        self.assertIn("$.snapshots.PrimalBuff.AllowPostProcessEffect.source.progress", paths)
        self.assertIn("$.snapshots.PrimalBuff.AllowPostProcessEffect.sourceReady", paths)
        self.assertIn("$.snapshots.PrimalBuff.AllowPostProcessEffect.sourceStatus", paths)
        self.assertFalse(output["public_sdk_ready"])
        self.assertFalse(output["runtime_ready"])
        self.assertFalse(output["v1_completion_ready"])
        self.assertFalse(output["counts_toward_complete_sdk_claim"])
        self.assertFalse(output["p0_dependency_chain_ready"])
        self.assertFalse(output["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(0, output["complete_sdk_claim_progress_contribution"])
        self.assertFalse(output["buff_public_module_ready"])

    def test_textual_public_runtime_or_v1_claims_in_fixtures_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "PrimalBuff.AllowPostProcessEffect")
            payload["interpretation"]["note"] = (
                "Public Buff/status SDK is unlocked. Buff/status SDK is available. Runtime observer is unblocked. "
                "This credits toward the complete SDK claim."
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
        self.assertIn("credits toward the complete SDK claim", claims)
        self.assertFalse(output["public_sdk_ready"])
        self.assertFalse(output["runtime_ready"])
        self.assertFalse(output["v1_accounted"])

    def test_support_status_and_umbrella_leaf_claims_in_fixtures_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "PrimalBuff.AllowPostProcessEffect")
            payload["support_tier"] = "active"
            payload["runtime_support"] = "enabled"
            payload["v1_support"] = "release-supported"
            payload["interpretation"]["note"] = (
                "Runtime support is active. V1 support is enabled. "
                "Umbrella leaf promotion is ready."
            )
            self.write_snapshot(root, "PrimalBuff.AllowPostProcessEffect", payload)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        claims = {
            blocker["claim"]
            for blocker in output["blockers"]
            if blocker["reason"] == "forbidden_text_claim"
        }
        self.assertIn("support_tier=active", claims)
        self.assertIn("runtime_support=enabled", claims)
        self.assertIn("v1_support=release-supported", claims)
        self.assertTrue(any("Runtime support" in claim for claim in claims))
        self.assertTrue(any("V1 support" in claim for claim in claims))
        self.assertTrue(any("Umbrella leaf promotion" in claim for claim in claims))
        self.assertFalse(output["runtime_ready"])
        self.assertFalse(output["v1_completion"])

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

    def test_candidate_debug_capture_claims_in_fixtures_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "PrimalBuff.AllowPostProcessEffect")
            payload["candidate_capture_ready"] = True
            payload["debug_capture_evidence_ready"] = True
            payload["candidate_capture_progress_contribution"] = 1
            payload["interpretation"]["note"] = (
                "Candidate capture is ready evidence. Debug capture counts toward public SDK claim. "
                "Candidate capture enables ResourceHandle."
            )
            self.write_snapshot(root, "PrimalBuff.AllowPostProcessEffect", payload)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("forbidden_readiness_claim", reasons)
        self.assertIn("forbidden_text_claim", reasons)
        paths = {blocker["path"] for blocker in output["blockers"] if blocker["reason"] == "forbidden_readiness_claim"}
        self.assertIn("$.snapshots.PrimalBuff.AllowPostProcessEffect.candidate_capture_ready", paths)
        self.assertIn("$.snapshots.PrimalBuff.AllowPostProcessEffect.debug_capture_evidence_ready", paths)
        self.assertIn(
            "$.snapshots.PrimalBuff.AllowPostProcessEffect.candidate_capture_progress_contribution",
            paths,
        )
        claims = {blocker.get("claim") for blocker in output["blockers"] if blocker["reason"] == "forbidden_text_claim"}
        self.assertTrue(any("Candidate capture is ready" in str(claim) for claim in claims))
        self.assertTrue(any("Debug capture counts toward" in str(claim) for claim in claims))
        self.assertIn("ResourceHandle", claims)
        self.assertFalse(output["candidate_capture_evidence_ready"])
        self.assertEqual(0, output["candidate_capture_progress_contribution"])

    def test_multi_surface_beta_capture_plan_overclaims_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "PrimalBuff.AllowPostProcessEffect")
            payload["multi_surface_beta_capture_plan"] = {
                "status": "future_capture_targets_only",
                "surface": "buff_status",
                "capture_gate": "dedicated_beta_capture_check_required",
                "approved_runtime_evidence_ready": True,
                "clears_approved_runtime_evidence_missing": True,
                "player_principal_runtime_evidence_ready": True,
                "replaces_player_principal_evidence": True,
                "resource_handle_ready": True,
                "mutation_authority_ready": True,
                "return_value_override_ready": True,
                "counts_toward_p0_dependency_chain_claim": True,
                "sdk_progress": 1,
                "targets": [
                    {
                        "target": "PrimalBuff.AllowPostProcessEffect",
                        "status": "future_capture_target",
                        "approved_runtime_evidence_ready": True,
                        "replaces_player_principal_evidence": True,
                        "sdk_progress": 1,
                    }
                ],
            }
            payload["interpretation"]["note"] = (
                "Multi-surface beta capture pack is approved runtime evidence. "
                "Buff beta capture clears approved_runtime_evidence_missing and replaces player-principal lifecycle evidence. "
                "Beta capture counts toward P0 dependency chain and enables return value override."
            )
            self.write_snapshot(root, "PrimalBuff.AllowPostProcessEffect", payload)
            result = self.run_checker("--snapshot-root", str(root), check=False)

        output = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in output["blockers"]}
        self.assertIn("beta_capture_readiness_overclaim", reasons)
        self.assertIn("forbidden_readiness_claim", reasons)
        self.assertIn("forbidden_text_claim", reasons)
        paths = {
            blocker.get("path")
            for blocker in output["blockers"]
            if blocker["reason"] in {"beta_capture_readiness_overclaim", "forbidden_readiness_claim"}
        }
        self.assertIn(
            "$.snapshots.PrimalBuff.AllowPostProcessEffect.multi_surface_beta_capture_plan.approved_runtime_evidence_ready",
            paths,
        )
        self.assertIn(
            "$.snapshots.PrimalBuff.AllowPostProcessEffect.multi_surface_beta_capture_plan.clears_approved_runtime_evidence_missing",
            paths,
        )
        self.assertIn(
            "$.snapshots.PrimalBuff.AllowPostProcessEffect.multi_surface_beta_capture_plan.sdk_progress",
            paths,
        )
        claims = {blocker.get("claim") for blocker in output["blockers"] if blocker["reason"] == "forbidden_text_claim"}
        self.assertTrue(any("Multi-surface beta capture pack is approved" in str(claim) for claim in claims))
        self.assertTrue(any("Beta capture counts toward" in str(claim) for claim in claims))
        self.assertIn("clears approved_runtime_evidence_missing", claims)
        self.assertFalse(output["approved_runtime_evidence_ready"])
        self.assertFalse(output["clears_approved_runtime_evidence_missing"])
        self.assertFalse(output["replaces_player_principal_evidence"])
        self.assertFalse(output["resource_handle_ready"])
        self.assertFalse(output["return_override_ready"])
        self.assertFalse(output["p0_dependency_chain_ready"])

    def test_side_lane_source_artifacts_and_target_aliases_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self.copy_fixture_root(Path(temp_dir))
            payload = self.read_snapshot(root, "PrimalBuff.AllowPostProcessEffect")
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
            payload["target_sets"] = ["buff-public-sdk-ready"]
            payload["target_set_alias"] = "buff-runtime-ready"
            self.write_snapshot(root, "PrimalBuff.AllowPostProcessEffect", payload)
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
