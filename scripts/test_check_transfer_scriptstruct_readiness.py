#!/usr/bin/env python3
"""Tests for check_transfer_scriptstruct_readiness.py."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_transfer_scriptstruct_readiness.py"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "scriptstruct_snapshots"
sys.path.insert(0, str(SCRIPT_DIR))
import build_redacted_scriptstruct_signatures as build_tool  # noqa: E402
import check_transfer_scriptstruct_readiness as readiness  # noqa: E402


class CheckTransferScriptStructReadinessTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def make_source_report(self) -> dict:
        return build_tool.build_report(snapshot_root=FIXTURE_ROOT, target_sets=[readiness.TARGET_SET])

    def copy_fixture_root(self, destination: Path) -> None:
        shutil.copytree(FIXTURE_ROOT, destination)

    def first_manifest_snapshot(self, snapshot_root: Path) -> Path:
        manifest = json.loads((snapshot_root / "manifest.json").read_text(encoding="utf-8"))
        first = manifest["targets"][0]
        return snapshot_root / manifest["sha_prefix"] / first["module"] / first["file"]

    def test_fixture_is_candidate_ready_but_not_public_runtime_or_sdk_ready(self) -> None:
        result = self.run_checker("--json")

        payload = json.loads(result.stdout)
        self.assertEqual(readiness.REPORT_SCHEMA, payload["schema"])
        self.assertTrue(payload["ready"])
        self.assertEqual("candidate_only_accepted", payload["status"])
        self.assertEqual("approved_runtime_evidence_missing", payload["current_route_blocker"])
        self.assertEqual(["approved_runtime_evidence_missing"], payload["remaining_route_blockers"])
        self.assertEqual(
            "approved_runtime_principal_lifecycle_evidence_bundle",
            payload["required_runtime_evidence"],
        )
        self.assertEqual(readiness.NON_AUTHORIZING_READY_SCOPE, payload["ready_scope"])
        self.assertTrue(
            set(readiness.NON_AUTHORIZING_READY_DOES_NOT_SATISFY)
            <= set(payload["does_not_satisfy_readiness"])
        )
        self.assertTrue(payload["accepted_for_candidate_review"])
        self.assertTrue(payload["accepted_for_internal_planning"])
        self.assertTrue(payload["offline_only"])
        self.assertTrue(payload["candidate_only"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertEqual([], payload["blockers"])
        self.assertEqual(readiness.EXPECTED_TARGETS, payload["summary"]["targets"])
        self.assertEqual(2, payload["summary"]["snapshot_count"])
        self.assertEqual(2, payload["summary"]["signature_count"])
        self.assertEqual(21, payload["summary"]["field_count_total"])
        self.assertEqual(21, payload["summary"]["redacted_payload_field_count"])
        self.assertEqual(0, payload["summary"]["copied_scalar_count_total"])
        self.assertEqual(2, payload["summary"]["source_binding_count"])
        self.assertEqual(readiness.EXPECTED_TARGETS, payload["summary"]["source_manifest_targets"])
        self.assertEqual(readiness.MANIFEST_SCHEMA, payload["source_manifest"]["schema"])
        self.assertEqual("offline_core", payload["source_manifest"]["source"])
        self.assertEqual("candidate-only", payload["source_manifest"]["status"])
        self.assertEqual([readiness.EXPECTED_MANIFEST_MODULE], payload["source_manifest"]["modules"])
        self.assertEqual(2, payload["source_manifest"]["source_binding_count"])
        bindings = payload["source_manifest"]["source_bindings"]
        self.assertEqual(
            ["snapshot-0001", "snapshot-0002"],
            [binding["id"] for binding in bindings],
        )
        self.assertTrue(all(len(binding["sha256"]) == 64 for binding in bindings))
        self.assertEqual(
            {
                "PrimalLocalProfile.ArkTributePlayerData.bForServerTransfer",
                "PrimalLocalProfile.ArkTributePlayerData.bWasAllowDPCUpload",
                "PrimalLocalProfile.ArkTributePlayerData.bWithItems",
            },
            set(payload["summary"]["bool_tail_fields"]),
        )
        self.assertEqual(["ItemNetInfo"], payload["explicitly_excluded"])
        self.assertTrue(payload["item_net_info_excluded"])
        self.assertFalse(
            payload["multi_surface_beta_capture_guardrail"][
                "counts_as_approved_runtime_evidence"
            ]
        )
        self.assertFalse(
            payload["multi_surface_beta_capture_guardrail"][
                "clears_approved_runtime_evidence_missing"
            ]
        )
        self.assertFalse(
            payload["multi_surface_beta_capture_guardrail"][
                "replaces_player_principal_evidence"
            ]
        )
        self.assertFalse(payload["multi_surface_beta_capture_guardrail"]["sdk_p0_unlock_allowed"])
        self.assertFalse(payload["multi_surface_beta_capture_guardrail"]["side_lane_counts_toward_sdk"])
        self.assertFalse(payload["multi_surface_beta_capture_guardrail"]["side_lane_counts_toward_p0"])
        self.assertEqual(
            "approved_runtime_principal_lifecycle_evidence_bundle",
            payload["multi_surface_beta_capture_guardrail"]["required_first_artifact"],
        )
        self.assertFalse(payload["sdk_p0_unlock_allowed"])
        self.assertFalse(payload["side_lane_counts_toward_sdk"])
        self.assertFalse(payload["side_lane_counts_toward_p0"])
        for key in readiness.REPORT_FALSE_FLAGS:
            self.assertIn(key, payload)
            self.assertFalse(payload[key], key)
        for key in readiness.REPORT_ZERO_FIELDS:
            self.assertIn(key, payload)
            self.assertEqual(0, payload[key], key)

    def test_candidate_capture_bundle_non_counting_metadata_is_allowed(self) -> None:
        source_report = self.make_source_report()
        source_report["candidate_capture_bundle"] = {
            "schema": "obelisk.beta-capture-bundle.v1",
            "status": "candidate-only",
            "candidate_only": True,
            "candidateOnly": True,
            "scriptstruct_capture_candidate_only": True,
            "offline_only": True,
            "consume_only": True,
            "not_artifact_gate": True,
            "non_counting": True,
            "scriptstruct_capture_non_counting": True,
            "counts_toward_public_sdk": False,
            "counts_toward_public_transfer_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "counts_toward_v1_completion": False,
            "public_sdk_progress_contribution": 0,
            "public_transfer_sdk_progress_contribution": 0,
            "runtime_progress_contribution": 0,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
            "v1_completion_progress_contribution": 0,
            "runtime_capture_ready": False,
            "public_transfer_sdk_ready": False,
            "transfer_payload_decoding_ready": False,
            "mutation_ready": False,
            "return_override_ready": False,
            "resource_handle_ready": False,
            "source_binding_count": 2,
            "target_count": 2,
            "surfaces": [
                readiness.TARGET_SET,
                "obelisk.inventory_item_copied_signals.v1",
            ],
            "review_notes": [
                "candidate-only non-counting ScriptStruct capture bundle for offline beta evidence review"
            ],
        }

        report = readiness.build_report(source_report=source_report)

        self.assertTrue(report["ready"], report["blockers"])
        self.assertTrue(report["candidate_only"])
        self.assertFalse(report["runtime_capture_ready"])
        self.assertFalse(report["public_transfer_sdk_ready"])
        self.assertFalse(report["sdk_p0_unlock_allowed"])
        self.assertEqual(0, report["public_transfer_sdk_progress_contribution"])
        self.assertEqual(0, report["p0_dependency_chain_claim_progress_contribution"])

    def test_multi_surface_beta_capture_plan_is_candidate_prep_only(self) -> None:
        source_report = self.make_source_report()
        non_claim_flags = {
            "candidate_only": True,
            "touches_live_servers": False,
            "authorizes_server_restart": False,
            "authorizes_marker_or_env_changes": False,
            "authorizes_discord_send": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_progress": False,
            "counts_as_p0_progress": False,
            "clears_approved_runtime_evidence_missing": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "stable_sdk_ready": False,
            "plugin_hub_ready": False,
            "publication_ready": False,
        }
        source_report["multi_surface_beta_capture_plan"] = {
            "schema": "obelisk.multi-surface-beta-capture-plan.v1",
            "status": "candidate_capture_plan",
            "target": {"instance": "arkserver", "map": "TheIsland"},
            "server_policy": {
                "keep_servers_running_when_practical": True,
                "max_ark_servers_running": 2,
                "restart_only_for_obelisk_update_or_gate_change": True,
                "broadcast_before_restart_if_players_connected": True,
                "keep_transfer_server_when_practical": True,
            },
            "required_primary_evidence": {
                "surface": "player_principal_lifecycle",
                "strict_triplet": "HandleNewPlayer(1,1) -> CheckJoinInProgress(1,0) -> matched OnLogout",
                "must_be_checker_accepted": True,
            },
            "capture_surfaces": [
                {
                    "id": "transfer_scriptstruct",
                    "checker": "scripts/check_transfer_scriptstruct_readiness.py",
                    "objective": "transfer ScriptStruct candidate observations only",
                    "operator_action": "attempt normal cluster transfer only if a transfer server is available",
                    "priority": 9,
                    "candidate_capture_only": True,
                    "requires_checker_acceptance": True,
                    "replaces_player_principal_triplet": False,
                    "non_claim_flags": dict(non_claim_flags),
                }
            ],
            "non_claim_flags": non_claim_flags,
        }

        report = readiness.build_report(source_report=source_report)

        self.assertTrue(report["ready"], report["blockers"])
        self.assertEqual("approved_runtime_evidence_missing", report["current_route_blocker"])
        self.assertFalse(report["multi_surface_beta_capture_guardrail"]["public_transfer_sdk_ready"])
        self.assertFalse(report["multi_surface_beta_capture_guardrail"]["sdk_p0_unlock_allowed"])
        self.assertFalse(
            report["multi_surface_beta_capture_guardrail"][
                "counts_as_approved_runtime_evidence"
            ]
        )
        self.assertEqual(0, report["p0_dependency_chain_claim_progress_contribution"])

    def test_multi_surface_beta_capture_pack_overclaims_fail_closed(self) -> None:
        source_report = self.make_source_report()
        source_report["multi_surface_beta_capture_plan_queue"] = {
            "schema": "obelisk.multi-surface-beta-capture-plan-queue.v1",
            "ready_scope": "multi_surface_beta_capture_plan_queue",
            "status": "ready",
            "queueStatus": "ready",
            "approvedRuntimeEvidenceMissingCleared": True,
            "approvedRuntimeEvidenceReady": True,
            "authorizesRuntimeCapture": True,
            "authorizesServerRestart": True,
            "clearsApprovedRuntimeEvidenceMissing": True,
            "evidenceBundleAccepted": True,
            "primaryEvidenceSubstitutionAllowed": True,
            "publicTransferSdkReady": True,
            "runtimeReady": True,
            "sdkAccountingCountsAsCompletedSurface": True,
            "sideLaneSubstitutesForPlayerPrincipalLifecycleEvidence": True,
            "p0AccountingCountsAsPromotedSurface": True,
            "completeSdkClaimProgressContribution": "1/12",
            "p0DependencyChainClaimProgressRatio": "1/4",
            "replacement_claim": "transfer beta capture replaces player-principal lifecycle evidence",
            "candidate_surfaces": [
                {
                    "surface": "transfer_scriptstruct",
                    "captureReady": True,
                    "countsTowardSdk": True,
                }
            ],
        }

        report = readiness.build_report(source_report=source_report)

        self.assertFalse(report["ready"])
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("readiness_alias_overclaim", reasons)
        self.assertIn("positive_status_alias_overclaim", reasons)
        paths = {
            blocker["path"]
            for blocker in report["blockers"]
            if blocker["reason"] in {
                "readiness_alias_overclaim",
                "positive_status_alias_overclaim",
            }
        }
        prefix = "$.multi_surface_beta_capture_plan_queue"
        self.assertIn(f"{prefix}.status", paths)
        self.assertIn(f"{prefix}.queueStatus", paths)
        self.assertIn(f"{prefix}.approvedRuntimeEvidenceMissingCleared", paths)
        self.assertIn(f"{prefix}.approvedRuntimeEvidenceReady", paths)
        self.assertIn(f"{prefix}.authorizesRuntimeCapture", paths)
        self.assertIn(f"{prefix}.authorizesServerRestart", paths)
        self.assertIn(f"{prefix}.clearsApprovedRuntimeEvidenceMissing", paths)
        self.assertIn(f"{prefix}.evidenceBundleAccepted", paths)
        self.assertIn(f"{prefix}.primaryEvidenceSubstitutionAllowed", paths)
        self.assertIn(f"{prefix}.publicTransferSdkReady", paths)
        self.assertIn(f"{prefix}.runtimeReady", paths)
        self.assertIn(f"{prefix}.sdkAccountingCountsAsCompletedSurface", paths)
        self.assertIn(f"{prefix}.sideLaneSubstitutesForPlayerPrincipalLifecycleEvidence", paths)
        self.assertIn(f"{prefix}.p0AccountingCountsAsPromotedSurface", paths)
        self.assertIn(f"{prefix}.completeSdkClaimProgressContribution", paths)
        self.assertIn(f"{prefix}.p0DependencyChainClaimProgressRatio", paths)
        self.assertIn(f"{prefix}.replacement_claim", paths)
        self.assertIn(f"{prefix}.candidate_surfaces[0].captureReady", paths)
        self.assertIn(f"{prefix}.candidate_surfaces[0].countsTowardSdk", paths)
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertEqual("approved_runtime_evidence_missing", report["current_route_blocker"])

    def test_candidate_capture_bundle_overclaims_fail_closed(self) -> None:
        source_report = self.make_source_report()
        source_report["candidate_capture_bundle"] = {
            "status": "candidate-only",
            "candidate_only": True,
            "offline_only": True,
            "consume_only": True,
            "non_counting": True,
            "runtime_capture_ready": True,
            "public_transfer_sdk_ready": True,
            "transfer_payload_decoding_ready": True,
            "mutation_ready": True,
            "return_override_ready": True,
            "resource_handle_ready": True,
            "counts_toward_public_transfer_sdk": True,
            "counts_toward_runtime": True,
            "public_transfer_sdk_progress_contribution": 1,
            "runtime_progress_contribution": 1,
            "complete_sdk_claim_progress_contribution": 1,
            "p0_dependency_chain_claim_progress_contribution": 1,
            "review_notes": [
                "public Transfer SDK readiness from debug capture",
                "ResourceHandle ready for transfer payload callbacks",
                "return override support is ready for transfer payload callbacks",
            ],
        }

        report = readiness.build_report(source_report=source_report)

        self.assertFalse(report["ready"])
        self.assertIn("readiness_alias_overclaim", {blocker["reason"] for blocker in report["blockers"]})
        paths = {
            blocker["path"]
            for blocker in report["blockers"]
            if blocker["reason"] == "readiness_alias_overclaim"
        }
        prefix = "$.candidate_capture_bundle"
        self.assertIn(f"{prefix}.runtime_capture_ready", paths)
        self.assertIn(f"{prefix}.public_transfer_sdk_ready", paths)
        self.assertIn(f"{prefix}.transfer_payload_decoding_ready", paths)
        self.assertIn(f"{prefix}.mutation_ready", paths)
        self.assertIn(f"{prefix}.return_override_ready", paths)
        self.assertIn(f"{prefix}.resource_handle_ready", paths)
        self.assertIn(f"{prefix}.counts_toward_public_transfer_sdk", paths)
        self.assertIn(f"{prefix}.counts_toward_runtime", paths)
        self.assertIn(f"{prefix}.public_transfer_sdk_progress_contribution", paths)
        self.assertIn(f"{prefix}.runtime_progress_contribution", paths)
        self.assertIn(f"{prefix}.complete_sdk_claim_progress_contribution", paths)
        self.assertIn(f"{prefix}.p0_dependency_chain_claim_progress_contribution", paths)
        self.assertIn(f"{prefix}.review_notes[0]", paths)
        self.assertIn(f"{prefix}.review_notes[1]", paths)
        self.assertIn(f"{prefix}.review_notes[2]", paths)

    def test_missing_fixture_and_replaced_target_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_root = Path(temp_dir) / "scriptstruct_snapshots"
            self.copy_fixture_root(snapshot_root)
            self.first_manifest_snapshot(snapshot_root).unlink()

            result = self.run_checker("--snapshot-root", str(snapshot_root), "--json", check=False)

        missing_payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(missing_payload["ready"])
        missing_reasons = {blocker["reason"] for blocker in missing_payload["blockers"]}
        self.assertIn("missing_targets_present", missing_reasons)
        self.assertIn("target_set_coverage_incomplete", missing_reasons)

        source_report = self.make_source_report()
        replaced_report = copy.deepcopy(source_report)
        replaced_report["signatures"][0]["target"] = "PrimalLocalProfile.TransferReplacement"
        replaced = readiness.build_report(source_report=replaced_report)

        self.assertFalse(replaced["ready"])
        replaced_reasons = {blocker["reason"] for blocker in replaced["blockers"]}
        self.assertIn("signature_target_coverage_mismatch", replaced_reasons)
        self.assertIn("expected_signature_missing", replaced_reasons)

    def test_unknown_schemas_and_missing_target_set_coverage_fail_closed(self) -> None:
        source_report = self.make_source_report()
        source_report["schema"] = "obelisk.unknown-scriptstruct-signatures.v1"

        schema_report = readiness.build_report(source_report=source_report)

        self.assertFalse(schema_report["ready"])
        self.assertIn("source_schema_mismatch", {blocker["reason"] for blocker in schema_report["blockers"]})

        coverage_report = self.make_source_report()
        coverage_report["target_set_coverage"]["observed_targets"] = coverage_report["target_set_coverage"][
            "observed_targets"
        ][:-1]
        coverage = readiness.build_report(source_report=coverage_report)

        self.assertFalse(coverage["ready"])
        self.assertIn(
            "target_set_observed_coverage_mismatch",
            {blocker["reason"] for blocker in coverage["blockers"]},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_root = Path(temp_dir) / "scriptstruct_snapshots"
            self.copy_fixture_root(snapshot_root)
            manifest_path = snapshot_root / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["schema"] = "obelisk.unknown-scriptstruct-manifest.v1"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result = self.run_checker("--snapshot-root", str(snapshot_root), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("snapshot_manifest_schema_mismatch", {blocker["reason"] for blocker in payload["blockers"]})

    def test_target_set_alias_and_declared_coverage_mismatch_fail_closed(self) -> None:
        source_report = self.make_source_report()
        source_report["target_sets"] = ["transfer-public-sdk-ready"]
        source_report["target_set_coverage"]["declared_target_sets"] = [
            "transfer-public-sdk-ready"
        ]

        report = readiness.build_report(source_report=source_report)

        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertFalse(report["ready"])
        self.assertIn("target_set_mismatch", reasons)
        self.assertIn("target_set_declared_coverage_mismatch", reasons)
        self.assertIn("forbidden_positive_claim_value", reasons)
        self.assertIn("non_current_target_alias", reasons)

    def test_side_lane_source_artifacts_and_target_aliases_fail_closed(self) -> None:
        source_report = self.make_source_report()
        source_report["source_overclaim_total_flag_count"] = 0
        source_report["principal_start_end_runtime_evidence"] = {
            "ready_scope": "principal_start_end_runtime_evidence_only",
            "principal_start_end_runtime_evidence_ready": False,
            "resolved_inputs": ["runtime.lifecycle_start_end_evidence"],
        }
        source_report["passive_snapshot"] = {
            "status": "passive_snapshot_non_evidence",
            "passive_snapshot_evidence_allowed": False,
        }
        source_report["target_set_alias"] = "transfer-runtime-ready"

        report = readiness.build_report(source_report=source_report)

        self.assertFalse(report["ready"])
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("source_overclaim_zero_not_allowed", reasons)
        self.assertIn("copied_start_end_player_evidence_not_allowed", reasons)
        self.assertIn("passive_snapshot_source_not_allowed", reasons)
        self.assertIn("non_current_target_alias", reasons)

    def test_accidental_item_net_info_inclusion_fails_closed(self) -> None:
        source_report = self.make_source_report()
        source_report["signatures"].append(
            {
                "target": "PrimalLocalProfile.ItemNetInfo",
                "name": "ItemNetInfo",
                "fields": [],
            }
        )

        report = readiness.build_report(source_report=source_report)

        self.assertFalse(report["ready"])
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("item_net_info_in_source_report", reasons)

    def test_public_runtime_sdk_and_ready_overclaims_fail_closed(self) -> None:
        cases = (
            ("public_sdk_ready", True, "readiness_alias_overclaim"),
            ("runtime_readiness", "ready", "readiness_alias_overclaim"),
            ("runtime_ready", "runtime-ready", "readiness_alias_overclaim"),
            ("runtime_validation", "passed", "readiness_alias_overclaim"),
            ("runtime_unlocked", True, "readiness_alias_overclaim"),
            ("runtime_state", "unblocked", "readiness_alias_overclaim"),
            ("complete_sdk_ready", True, "readiness_alias_overclaim"),
            ("complete_sdk_status", "complete", "readiness_alias_overclaim"),
            ("complete_sdk_credit", 1, "readiness_alias_overclaim"),
            ("p0_dependency_chain_ready", True, "readiness_alias_overclaim"),
            ("counts_toward_v1_completion", True, "readiness_alias_overclaim"),
            ("v1_completion_ready", True, "readiness_alias_overclaim"),
            ("v1_completion_status", "complete", "readiness_alias_overclaim"),
            ("v1_completion_credit", 1, "readiness_alias_overclaim"),
            ("v1_completion_progress_contribution", 1, "readiness_alias_overclaim"),
            ("resource_handle_ready", True, "readiness_alias_overclaim"),
            ("resource_handle_status", "approved", "readiness_alias_overclaim"),
            ("mutation_outcome", "complete", "readiness_alias_overclaim"),
            ("return_override_result", "approved", "readiness_alias_overclaim"),
            ("source_status", "complete", "readiness_alias_overclaim"),
            ("source_label", "approved", "readiness_alias_overclaim"),
            ("status", "sdk-ready", "positive_status_alias_overclaim"),
        )
        for key, value, reason in cases:
            with self.subTest(key=key):
                source_report = self.make_source_report()
                source_report[key] = value

                report = readiness.build_report(source_report=source_report)

                self.assertFalse(report["ready"])
                self.assertIn(reason, {blocker["reason"] for blocker in report["blockers"]})

        source_report = self.make_source_report()
        source_report["non_claims"].append("public Transfer SDK is ready")
        report = readiness.build_report(source_report=source_report)

        self.assertFalse(report["ready"])
        self.assertIn("forbidden_positive_claim_value", {blocker["reason"] for blocker in report["blockers"]})

        source_report = self.make_source_report()
        source_report["public_module"] = {
            "status": "accepted",
            "result": "validated",
            "outcome": "ready",
            "progress": 1,
            "credits": 1,
            "unlocked": True,
            "public_transfer_sdk_surface_count": 1,
            "target_count": 2,
        }
        source_report["runtime_capture"] = {"outcome": "enabled", "progress": 1, "unblocked": True}
        source_report["live_ops"] = {"result": "stable", "stable": True}
        report = readiness.build_report(source_report=source_report)

        self.assertFalse(report["ready"])
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("readiness_alias_overclaim", reasons)
        paths = {
            blocker["path"]
            for blocker in report["blockers"]
            if blocker["reason"] == "readiness_alias_overclaim"
        }
        self.assertIn("$.public_module.status", paths)
        self.assertIn("$.public_module.result", paths)
        self.assertIn("$.public_module.outcome", paths)
        self.assertIn("$.public_module.progress", paths)
        self.assertIn("$.public_module.credits", paths)
        self.assertIn("$.public_module.unlocked", paths)
        self.assertIn("$.public_module.public_transfer_sdk_surface_count", paths)
        self.assertNotIn("$.public_module.target_count", paths)
        self.assertIn("$.runtime_capture.outcome", paths)
        self.assertIn("$.runtime_capture.progress", paths)
        self.assertIn("$.runtime_capture.unblocked", paths)
        self.assertIn("$.live_ops.result", paths)
        self.assertIn("$.live_ops.stable", paths)

    def test_candidate_consume_promotion_alias_paths_fail_closed(self) -> None:
        source_report = self.make_source_report()
        source_report["target_set"] = {"promoted": True}
        source_report["artifact_identity"] = {"approved": True}
        source_report["consume_gate"] = {"ready": True}
        source_report["static_evidence"] = {"validated": True}
        source_report["side_lane"] = {"counts_toward_v1": True}
        source_report["inventory"] = {"public_contract": True}
        source_report["transfer"] = {"runtime_ready": True}
        source_report["readiness"] = {"approved": True}
        source_report["v1"] = {"complete": True}
        source_report["public_sdk"] = {"enabled": True}
        source_report["runtime"] = {"validated": True}
        source_report["candidate"] = {"accepted": True}
        source_report["package_shape"] = {"passed": True}
        source_report["support_tier"] = {"active": True}
        source_report["plugin_hub"] = {"ready": True}

        report = readiness.build_report(source_report=source_report)

        self.assertFalse(report["ready"])
        paths = {
            blocker["path"]
            for blocker in report["blockers"]
            if blocker["reason"] == "readiness_alias_overclaim"
        }
        self.assertIn("$.target_set.promoted", paths)
        self.assertIn("$.artifact_identity.approved", paths)
        self.assertIn("$.consume_gate.ready", paths)
        self.assertIn("$.static_evidence.validated", paths)
        self.assertIn("$.side_lane.counts_toward_v1", paths)
        self.assertIn("$.inventory.public_contract", paths)
        self.assertIn("$.transfer.runtime_ready", paths)
        self.assertIn("$.readiness.approved", paths)
        self.assertIn("$.v1.complete", paths)
        self.assertIn("$.public_sdk.enabled", paths)
        self.assertIn("$.runtime.validated", paths)
        self.assertIn("$.candidate.accepted", paths)
        self.assertIn("$.package_shape.passed", paths)
        self.assertIn("$.support_tier.active", paths)
        self.assertIn("$.plugin_hub.ready", paths)

    def test_redacted_fields_reject_hidden_payload_and_noncanonical_bool_values(self) -> None:
        source_report = self.make_source_report()
        for signature in source_report["signatures"]:
            for field in signature["fields"]:
                if field.get("type") == "redacted_array":
                    field["decoded_payload"] = ["raw transfer bytes"]
                if field.get("type") == "redacted_transfer_payload_bool":
                    field["observedBoolValue"] = 2
                    break

        report = readiness.build_report(source_report=source_report)

        self.assertFalse(report["ready"])
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("redacted_field_unexpected_keys", reasons)
        self.assertIn("noncanonical_bool_payload", reasons)
        unexpected_key_sets = [
            blocker["keys"]
            for blocker in report["blockers"]
            if blocker["reason"] == "redacted_field_unexpected_keys"
        ]
        self.assertTrue(any("decoded_payload" in keys for keys in unexpected_key_sets))
        self.assertTrue(any("observedBoolValue" in keys for keys in unexpected_key_sets))
        noncanonical_paths = {
            blocker["path"]
            for blocker in report["blockers"]
            if blocker["reason"] == "noncanonical_bool_payload"
        }
        self.assertTrue(any(path.endswith(".observedBoolValue") for path in noncanonical_paths))
        self.assertFalse(report["transfer_payload_decoding_ready"])
        self.assertFalse(report["public_transfer_sdk_ready"])

    def test_manifest_source_binding_mismatch_fails_closed(self) -> None:
        source_report = self.make_source_report()
        source_report["generated_from"]["input_snapshots"][0]["sha256"] = "0" * 64

        report = readiness.build_report(source_report=source_report)

        self.assertFalse(report["ready"])
        self.assertIn(
            "source_manifest_input_snapshot_binding_mismatch",
            {blocker["reason"] for blocker in report["blockers"]},
        )

    def test_rejects_symlinked_snapshot_root_and_snapshot_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            real_root = temp / "real_snapshots"
            self.copy_fixture_root(real_root)
            linked_root = temp / "linked_snapshots"
            linked_root.symlink_to(real_root, target_is_directory=True)

            result = self.run_checker("--snapshot-root", str(linked_root), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("snapshot_input_path_rejected", {blocker["reason"] for blocker in payload["blockers"]})

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_root = Path(temp_dir) / "scriptstruct_snapshots"
            self.copy_fixture_root(snapshot_root)
            snapshot_path = self.first_manifest_snapshot(snapshot_root)
            real_snapshot = snapshot_path.with_suffix(".real.json")
            snapshot_path.rename(real_snapshot)
            snapshot_path.symlink_to(real_snapshot)

            result = self.run_checker("--snapshot-root", str(snapshot_root), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertIn("snapshot_input_path_rejected", {blocker["reason"] for blocker in payload["blockers"]})


if __name__ == "__main__":
    unittest.main()
