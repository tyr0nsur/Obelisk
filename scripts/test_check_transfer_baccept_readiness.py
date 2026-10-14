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
from unittest import mock


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
        self.assertEqual(readiness.NON_AUTHORIZING_READY_SCOPE, payload["ready_scope"])
        self.assertTrue(
            set(readiness.NON_AUTHORIZING_READY_DOES_NOT_SATISFY)
            <= set(payload["does_not_satisfy_readiness"])
        )
        self.assertTrue(payload["accepted_for_internal_planning"])
        self.assertTrue(payload["offline_only"])
        self.assertTrue(payload["candidate_only"])
        self.assertTrue(payload["candidate_only_mode"])
        self.assertEqual("approved_runtime_evidence_missing", payload["current_route_blocker"])
        self.assertEqual(
            "approved_runtime_principal_lifecycle_evidence_bundle",
            payload["required_runtime_evidence"],
        )
        guardrail = payload["multi_surface_beta_capture_guardrail"]
        self.assertEqual("candidate_only_non_counting", guardrail["status"])
        self.assertEqual("approved_runtime_evidence_missing", guardrail["current_route_blocker"])
        self.assertFalse(guardrail["counts_as_approved_runtime_evidence"])
        self.assertFalse(guardrail["counts_as_runtime_evidence"])
        self.assertFalse(guardrail["clears_approved_runtime_evidence_missing"])
        self.assertFalse(guardrail["replaces_player_principal_triplet"])
        self.assertFalse(guardrail["sdk_p0_unlock_allowed"])
        self.assertFalse(guardrail["side_lane_counts_toward_sdk"])
        self.assertFalse(guardrail["side_lane_counts_toward_p0"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertTrue(payload["consume_only"])
        self.assertFalse(payload["sdk_p0_unlock_allowed"])
        self.assertFalse(payload["side_lane_counts_toward_sdk"])
        self.assertFalse(payload["side_lane_counts_toward_p0"])
        for key in readiness.REPORT_FALSE_FLAGS:
            self.assertIn(key, payload)
            self.assertFalse(payload[key], key)
        for key, expected in readiness.REPORT_ZERO_FIELDS.items():
            self.assertIn(key, payload)
            self.assertEqual(expected, payload[key], key)
        non_claims_text = "\n".join(payload["non_claims"])
        self.assertIn("internal offline planning evidence only", non_claims_text)
        self.assertIn("does not claim runtime validation", non_claims_text)
        self.assertIn("public Transfer SDK", non_claims_text)
        self.assertIn("does not claim v1 completion", non_claims_text)
        self.assertIn("P0 dependency-chain credit", non_claims_text)
        self.assertIn("does not replace approved player-principal lifecycle runtime evidence", non_claims_text)
        self.assertIn("multi-surface beta capture pack and plan artifacts are prep only", non_claims_text)
        self.assertEqual(1, payload["summary"]["copied_bool_count"])
        self.assertEqual(
            ["ShooterPlayerController.ServerTransferredPlayerConfirmationResult.bAccept"],
            payload["summary"]["copied_fields"],
        )
        self.assertEqual(10, len(payload["summary"]["forbidden_fields"]))

    def test_symlinked_root_and_manifest_paths_are_rejected_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest, sha256 = self.write_pack(root)
            root_link = Path(temp_dir) / "pack-link"
            root_link.symlink_to(root, target_is_directory=True)

            result = self.run_checker(
                "--root",
                str(root_link),
                "--manifest",
                str(root_link / manifest.name),
                "--expected-manifest-sha256",
                sha256,
                "--skip-artifact-gates",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        path_blockers = [blocker for blocker in report["blockers"] if blocker["reason"] == "path_rejected"]
        self.assertTrue(any(blocker.get("label") == "--root" for blocker in path_blockers))
        self.assertTrue(any(blocker.get("label") == "--manifest" for blocker in path_blockers))
        self.assertTrue(all("symlink" in blocker.get("detail", "") for blocker in path_blockers))

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest, sha256 = self.write_pack(root)
            manifest_link = Path(temp_dir) / "manifest-link.json"
            manifest_link.symlink_to(manifest)
            result = self.run_checker(*self.checker_args(root, manifest_link, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("path_rejected", {blocker["reason"] for blocker in report["blockers"]})
        self.assertTrue(any(blocker.get("label") == "--manifest" for blocker in report["blockers"]))

    def test_manifest_symlink_swap_after_path_precheck_is_rejected_before_content_read(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest, sha256 = self.write_pack(root)
            swapped_target = Path(temp_dir) / "swapped-policy.json"
            swapped_target.write_text('{"schema": "swapped"}', encoding="utf-8")
            original_safe_path = readiness.safe_path
            swapped = False

            def race_safe_path(path: Path, label: str, blockers: list[dict]) -> Path | None:
                nonlocal swapped
                resolved = original_safe_path(path, label, blockers)
                if label == "--manifest" and resolved is not None and not swapped:
                    swapped = True
                    manifest.unlink()
                    manifest.symlink_to(swapped_target)
                return resolved

            with mock.patch.object(readiness, "safe_path", side_effect=race_safe_path):
                report = readiness.build_report(root, manifest, sha256, skip_artifact_gates=True)

        self.assertFalse(report["ready"])
        self.assertIn("manifest_path_is_symlink", {blocker["reason"] for blocker in report["blockers"]})
        self.assertNotIn("schema_mismatch", {blocker["reason"] for blocker in report["blockers"]})

    def test_protected_manifest_path_is_rejected_before_policy_read(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest, sha256 = self.write_pack(root)
            original_reject = readiness.reject_protected_input_path

            def reject_manifest(path: Path, label: str) -> Path:
                if label == "--manifest":
                    raise SystemExit("simulated protected input path")
                return original_reject(path, label)

            with mock.patch.object(readiness, "reject_protected_input_path", side_effect=reject_manifest):
                with mock.patch.object(readiness, "read_policy") as read_policy:
                    report = readiness.build_report(root, manifest, sha256, skip_artifact_gates=True)

        self.assertFalse(report["ready"])
        self.assertIn("path_rejected", {blocker["reason"] for blocker in report["blockers"]})
        self.assertTrue(any(blocker.get("label") == "--manifest" for blocker in report["blockers"]))
        read_policy.assert_not_called()

    def test_policy_fixture_requires_consume_accept_and_promote_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest, sha256 = self.write_pack(root)
            gate_results = [
                (0, {"status": "accepted"}, ""),
                (
                    1,
                    {
                        "status": "blocked",
                        "blockers": [
                            {"reason": "promote_mode_manifest_has_non_claims"},
                            {"reason": "promote_mode_transfer_baccept_policy_slice_evidence_only"},
                        ],
                    },
                    "",
                ),
            ]
            with mock.patch.object(readiness, "run_gate", side_effect=gate_results) as run_gate:
                report = readiness.build_report(root, manifest, sha256)

        self.assertTrue(report["ready"])
        self.assertTrue(report["accepted_for_internal_planning"])
        self.assertTrue(report["consume_only"])
        self.assertEqual("accepted", report["consume_gate"]["status"])
        self.assertEqual("blocked", report["promote_gate"]["status"])
        self.assertIn("promote_mode_manifest_has_non_claims", report["promote_gate"]["blocker_reasons"])
        self.assertIn("promote_mode_transfer_baccept_policy_slice_evidence_only", report["promote_gate"]["blocker_reasons"])
        run_gate.assert_has_calls(
            [
                mock.call(root, manifest, "consume"),
                mock.call(root, manifest, "promote"),
            ]
        )

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
            payload["generated_from"]["input_snapshots"][1]["resource_handle_public_contract"] = True
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

    def test_policy_rejects_public_contract_claims_for_transfer_payload_surfaces(self) -> None:
        public_contract_claims = (
            "transfer payload is a public contract",
            "downloaded characters are public API ready",
            "dino payload decoding is available",
            "player identity is exposed as a public contract",
            "cross-map state is ready",
            "ResourceHandle is available as a public contract",
        )
        for claim in public_contract_claims:
            with self.subTest(claim=claim):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir) / "pack"
                    payload = self.make_policy()
                    payload["non_claims"].append(claim)
                    manifest, sha256 = self.write_pack(root, payload)
                    result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

                report = json.loads(result.stdout)
                self.assertEqual(1, result.returncode)
                reasons = {blocker["reason"] for blocker in report["blockers"]}
                self.assertIn("forbidden_public_contract_claim_value", reasons)

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

    def test_policy_rejects_readiness_alias_overclaims(self) -> None:
        cases = (
            ("ready_for_public_sdk", True),
            ("publicReady", True),
            ("sdkReady", True),
            ("p0Ready", True),
            ("publicStatus", "enabled"),
            ("sdkStatus", "supported"),
            ("p0Status", "ready"),
            ("counts_toward_v1_completion", True),
            ("runtimeValidated", True),
            ("transferPayloadPublicContractReady", True),
            ("release_candidate_ready", True),
            ("source_ready", True),
            ("source_status", True),
            ("readiness_status", "ready"),
        )
        for key, value in cases:
            with self.subTest(key=key):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir) / "pack"
                    payload = self.make_policy()
                    payload["coverage"][key] = value
                    manifest, sha256 = self.write_pack(root, payload)
                    result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

                report = json.loads(result.stdout)
                self.assertEqual(1, result.returncode)
                reasons = {blocker["reason"] for blocker in report["blockers"]}
                self.assertIn("readiness_alias_overclaim", reasons)

    def test_policy_rejects_source_label_positive_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["sourceLabel"] = "ready"
            payload["sourceLabels"] = ["candidate-only", "supported"]
            manifest, sha256 = self.write_pack(root, payload)
            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("policy_unexpected_field", reasons)
        self.assertIn("readiness_alias_overclaim", reasons)
        paths = {
            blocker["path"]
            for blocker in report["blockers"]
            if blocker["reason"] == "readiness_alias_overclaim"
        }
        self.assertIn("$.sourceLabel", paths)
        self.assertIn("$.sourceLabels[1]", paths)
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(0, report["complete_sdk_claim_progress_contribution"])
        self.assertTrue(report["candidate_only"])
        self.assertFalse(report["sdk_p0_unlock_allowed"])

    def test_policy_rejects_nested_status_result_outcome_and_count_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["public_module"] = {
                "status": "accepted",
                "result": "validated",
                "outcome": "ready",
                "public_transfer_sdk_surface_count": 1,
                "target_count": 1,
            }
            payload["runtime_capture"] = {"outcome": "enabled", "progress": 1}
            payload["v1_readiness"] = {"result": "v1-ready"}
            payload["p0_dependency_chain"] = {"status": "supported"}
            payload["readiness"] = {"approved": True}
            payload["v1"] = {"complete": True}
            payload["public_sdk"] = {"enabled": True}
            payload["runtime"] = {"validated": True}
            payload["candidate"] = {"accepted": True}
            payload["package_shape"] = {"passed": True}
            payload["support_tier"] = {"active": True}
            payload["plugin_hub"] = {"ready": True}
            payload["target_set"] = {"promoted": True}
            manifest, sha256 = self.write_pack(root, payload)
            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("policy_unexpected_field", reasons)
        self.assertIn("readiness_alias_overclaim", reasons)
        paths = {
            blocker["path"]
            for blocker in report["blockers"]
            if blocker["reason"] == "readiness_alias_overclaim"
        }
        self.assertIn("$.public_module.status", paths)
        self.assertIn("$.public_module.result", paths)
        self.assertIn("$.public_module.outcome", paths)
        self.assertIn("$.public_module.public_transfer_sdk_surface_count", paths)
        self.assertNotIn("$.public_module.target_count", paths)
        self.assertIn("$.runtime_capture.outcome", paths)
        self.assertIn("$.runtime_capture.progress", paths)
        self.assertIn("$.v1_readiness.result", paths)
        self.assertIn("$.p0_dependency_chain.status", paths)
        self.assertIn("$.readiness.approved", paths)
        self.assertIn("$.v1.complete", paths)
        self.assertIn("$.public_sdk.enabled", paths)
        self.assertIn("$.runtime.validated", paths)
        self.assertIn("$.candidate.accepted", paths)
        self.assertIn("$.package_shape.passed", paths)
        self.assertIn("$.support_tier.active", paths)
        self.assertIn("$.plugin_hub.ready", paths)
        self.assertIn("$.target_set.promoted", paths)
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(0, report["p0_dependency_chain_claim_progress_contribution"])

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
