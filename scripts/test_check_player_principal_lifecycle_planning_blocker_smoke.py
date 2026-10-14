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
        self.assertFalse(report["runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["runtime_work_authorized"])
        self.assertFalse(report["server_operations_authorized"])
        self.assertFalse(report["live_ops_authorized"])
        self.assertFalse(report["runtime_capture_authorized"])
        self.assertFalse(report["workspace_writes_authorized"])
        self.assertFalse(report["reads_live_logs"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["passive_snapshots_as_evidence"])
        self.assertFalse(report["passive_snapshots_count_as_evidence"])
        self.assertFalse(report["passive_snapshot_evidence_allowed"])
        self.assertFalse(report["candidate_sidecars_count_as_approved_runtime_evidence"])
        self.assertFalse(report["passive_complete_triplets_count_as_approved_runtime_evidence"])
        self.assertFalse(report["request_pack_preflight_window_manifest_count_as_approved_runtime_evidence"])
        self.assertFalse(report["request_pack_ready"])
        self.assertFalse(report["preflight_ready"])
        self.assertFalse(report["window_manifest_ready"])
        self.assertFalse(report["status_report_ready"])
        self.assertFalse(report["status_report_paths_authorize_current_turn"])
        self.assertFalse(report["status_report_paths_count_as_approved_runtime_evidence"])
        self.assertFalse(report["counts_toward_sdk"])
        self.assertFalse(report["counts_toward_v1"])
        self.assertFalse(report["counts_toward_v1_completion"])
        self.assertEqual(report["remaining_blockers"], ["approved_runtime_evidence_missing"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_missing")
        route_audit = report["route_audit"]
        self.assertEqual(
            route_audit["schema"],
            "obelisk.player-principal-lifecycle-offline-route-audit.v1",
        )
        self.assertEqual(route_audit["current_blocker"], "approved_runtime_evidence_missing")
        self.assertTrue(route_audit["waiting_for_exact_check_join_in_progress_1_0_is_fastest_valid_route"])
        self.assertEqual(
            route_audit["primary_missing_runtime_shape"],
            {
                "role": "session_start_rejected",
                "target": "ShooterGameMode.CheckJoinInProgress",
                "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "copied_bool_values": ["1", "0"],
                "principal_action": "none",
                "apply_status": "session_start_rejected_noop",
                "correlation_status": "not_applicable",
            },
        )
        self.assertFalse(route_audit["extra_diagnostic_shape_logging_should_be_primary_next_action"])
        self.assertFalse(route_audit["different_map_or_tester_flow_should_be_primary_next_action"])
        self.assertFalse(route_audit["offline_layout_or_static_discovery_should_be_primary_next_action"])
        self.assertFalse(route_audit["counts_as_approved_runtime_evidence"])
        self.assertEqual(report["accepted_start_targets"], ["ShooterGameMode.HandleNewPlayer"])
        self.assertEqual(report["accepted_end_targets"], ["ShooterGameMode.OnLogout"])
        self.assertEqual(
            report["approved_manifest_checker"],
            "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
        )
        self.assertEqual(
            report["next_runtime_artifact_contract"]["required_artifact"],
            "approved_runtime_principal_lifecycle_evidence",
        )
        self.assertEqual(
            report["next_runtime_artifact_contract"]["required_window_replay"],
            "--post-window-replay",
        )
        self.assertIn(
            "player_presence_safety",
            report["next_runtime_artifact_contract"]["required_request_sections"],
        )
        self.assertEqual(report["next_runtime_artifact_contract"]["route_audit"], route_audit)
        player_presence_contract = report["next_runtime_artifact_contract"]["player_presence_safety_contract"]
        self.assertTrue(player_presence_contract["required"])
        self.assertEqual(
            player_presence_contract["schema"],
            "obelisk.player-principal-lifecycle-player-presence-safety.v1",
        )
        self.assertEqual(player_presence_contract["source"], "window-request.json.player_presence_safety")
        self.assertEqual(
            player_presence_contract["restart_expectation_restart_requires"],
            {
                "connected_player_check_required_before_restart": True,
                "rcon_broadcast_required_if_players_connected": True,
                "restart_must_be_cancelled_or_rescheduled_if_players_remain_connected": True,
            },
        )
        self.assertTrue(player_presence_contract["passive_wait_preferred_after_activation"])
        self.assertTrue(player_presence_contract["linuxgsm_monitor_forbidden"])
        self.assertFalse(player_presence_contract["player_check_or_broadcast_authorized_by_request_pack"])
        self.assertIn("does not authorize player queries", player_presence_contract["non_authorization"])
        self.assertEqual(
            [case["case"] for case in report["required_runtime_event_cases"]],
            [
                "observer_enable",
                "session_start_anchor",
                "session_start_rejected_anchor",
                "session_end_anchor",
            ],
        )
        rejected_case = report["required_runtime_event_cases"][2]
        self.assertEqual(
            rejected_case["accepted_alternatives"],
            [
                {
                    "target": "ShooterGameMode.CheckJoinInProgress",
                    "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                    "copied_bool_values": ["1", "0"],
                },
            ],
        )
        self.assertEqual(
            rejected_case["superseded_non_evidence_alternatives"],
            [
                {
                    "target": "ShooterGameMode.HandleNewPlayer",
                    "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                    "copied_bool_values": ["0", "1"],
                    "status": "superseded_non_evidence",
                    "reason": (
                        "historical HandleNewPlayer rejected-start tuple is ambiguous and no longer satisfies "
                        "approved runtime evidence"
                    ),
                },
                {
                    "target": "ShooterGameMode.HandleNewPlayer",
                    "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                    "copied_bool_values": ["1", "0"],
                    "status": "superseded_non_evidence",
                    "reason": (
                        "historical HandleNewPlayer rejected-start tuple is ambiguous and no longer satisfies "
                        "approved runtime evidence"
                    ),
                },
                {
                    "target": "ShooterGameMode.HandleNewPlayer",
                    "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                    "copied_bool_values": ["0", "0"],
                    "status": "superseded_non_evidence",
                    "reason": (
                        "historical HandleNewPlayer rejected-start tuple is ambiguous and no longer satisfies "
                        "approved runtime evidence"
                    ),
                },
            ],
        )
        session_start_case = report["required_runtime_event_cases"][1]
        self.assertEqual(
            {
                key: session_start_case[key]
                for key in (
                    "case",
                    "target",
                    "role",
                    "copied_bool_fields",
                    "copied_bool_values",
                    "principal_action",
                )
            },
            {
                "case": "session_start_anchor",
                "target": "ShooterGameMode.HandleNewPlayer",
                "role": "session_start",
                "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "copied_bool_values": ["1", "1"],
                "principal_action": "candidate_created",
            },
        )
        self.assertEqual(
            [case["case"] for case in report["required_consumer_cases"]],
            ["malformed_or_unsupported_evidence", "stale_after_logout"],
        )
        self.assertTrue(all(case["result"] == "fail_closed" for case in report["required_consumer_cases"]))

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
            payload["live_ops_authorized"] = True
            payload["runtime_capture_authorized"] = True
            payload["workspace_writes_authorized"] = True
            payload["reads_live_logs"] = True
            payload["approved_runtime_evidence"] = True
            payload["passive_snapshots_as_evidence"] = True
            payload["candidate_sidecars_count_as_approved_runtime_evidence"] = True
            payload["passive_complete_triplets_count_as_approved_runtime_evidence"] = True
            payload["request_pack_preflight_window_manifest_count_as_approved_runtime_evidence"] = True
            payload["status_report_paths_authorize_current_turn"] = True
            payload["status_report_paths_count_as_approved_runtime_evidence"] = True
            payload["counts_toward_sdk"] = True
            payload["counts_toward_v1"] = True
            write_json(report_path, payload)

            result = self.run_checker(root, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("report_stable_claim_allowed_not_false", report["blockers"])
        self.assertIn("report_runtime_work_authorized_not_false", report["blockers"])
        self.assertIn("report_live_ops_authorized_not_false", report["blockers"])
        self.assertIn("report_runtime_capture_authorized_not_false", report["blockers"])
        self.assertIn("report_workspace_writes_authorized_not_false", report["blockers"])
        self.assertIn("report_reads_live_logs_not_false", report["blockers"])
        self.assertIn("report_approved_runtime_evidence_not_false", report["blockers"])
        self.assertIn("report_passive_snapshots_as_evidence_not_false", report["blockers"])
        self.assertIn("report_candidate_sidecars_count_as_approved_runtime_evidence_not_false", report["blockers"])
        self.assertIn("report_passive_complete_triplets_count_as_approved_runtime_evidence_not_false", report["blockers"])
        self.assertIn(
            "report_request_pack_preflight_window_manifest_count_as_approved_runtime_evidence_not_false",
            report["blockers"],
        )
        self.assertIn("report_status_report_paths_authorize_current_turn_not_false", report["blockers"])
        self.assertIn("report_status_report_paths_count_as_approved_runtime_evidence_not_false", report["blockers"])
        self.assertIn("report_counts_toward_sdk_not_false", report["blockers"])
        self.assertIn("report_counts_toward_v1_not_false", report["blockers"])
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

    def test_rejects_nested_positive_claim_alias_in_planning_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "planning"
            copy_planning_sources(root)
            policy_path = root / POLICY_NAME
            payload = load_json(policy_path)
            payload["candidate_summary"] = {
                "runtime_v1_ready": True,
                "counts_toward_public_sdk": True,
                "live_ops_authorized": True,
                "runtimeCaptureAuthorized": True,
                "workspace_writes_authorized": True,
                "readsLiveLogs": True,
                "approved_runtime_evidence": True,
                "passive_snapshots_as_evidence": True,
                "candidate_sidecars_count_as_approved_runtime_evidence": True,
                "passive_complete_triplets_count_as_approved_runtime_evidence": True,
                "request_pack_preflight_window_manifest_count_as_approved_runtime_evidence": True,
                "status_report_paths_authorize_current_turn": True,
                "stable_claim_allowed": True,
                "counts_toward_sdk": True,
                "countsTowardV1": True,
            }
            write_json(policy_path, payload)

            result = self.run_checker(root, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("planning_manifest_nested_positive_claim", report["blockers"])
        labels = {detail["label"] for detail in report["blocker_details"]}
        self.assertIn("policy.candidate_summary.runtime_v1_ready", labels)
        self.assertIn("policy.candidate_summary.counts_toward_public_sdk", labels)
        self.assertIn("policy.candidate_summary.live_ops_authorized", labels)
        self.assertIn("policy.candidate_summary.runtimeCaptureAuthorized", labels)
        self.assertIn("policy.candidate_summary.workspace_writes_authorized", labels)
        self.assertIn("policy.candidate_summary.readsLiveLogs", labels)
        self.assertIn("policy.candidate_summary.approved_runtime_evidence", labels)
        self.assertIn("policy.candidate_summary.passive_snapshots_as_evidence", labels)
        self.assertIn("policy.candidate_summary.candidate_sidecars_count_as_approved_runtime_evidence", labels)
        self.assertIn("policy.candidate_summary.passive_complete_triplets_count_as_approved_runtime_evidence", labels)
        self.assertIn(
            "policy.candidate_summary.request_pack_preflight_window_manifest_count_as_approved_runtime_evidence",
            labels,
        )
        self.assertIn("policy.candidate_summary.status_report_paths_authorize_current_turn", labels)
        self.assertIn("policy.candidate_summary.stable_claim_allowed", labels)
        self.assertIn("policy.candidate_summary.counts_toward_sdk", labels)
        self.assertIn("policy.candidate_summary.countsTowardV1", labels)
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_missing")

    def test_rejects_nested_camel_case_positive_claim_alias_in_planning_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "planning"
            copy_planning_sources(root)
            policy_path = root / POLICY_NAME
            payload = load_json(policy_path)
            payload["candidate_summary"] = {
                "approvedRuntimeEvidencePresent": True,
                "publicSdkReady": True,
                "stableClaimAllowed": "yes",
                "v1CompletionReady": {"ready": True},
            }
            write_json(policy_path, payload)

            result = self.run_checker(root, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        claim_details = [
            detail
            for detail in report["blocker_details"]
            if detail["reason"] == "planning_manifest_nested_positive_claim"
        ]
        labels = {detail["label"] for detail in claim_details}
        self.assertIn("policy.candidate_summary.approvedRuntimeEvidencePresent", labels)
        self.assertIn("policy.candidate_summary.publicSdkReady", labels)
        self.assertIn("policy.candidate_summary.stableClaimAllowed", labels)
        self.assertIn("policy.candidate_summary.v1CompletionReady", labels)

    def test_rejects_text_positive_claim_in_planning_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "planning"
            copy_planning_sources(root)
            policy_path = root / POLICY_NAME
            payload = load_json(policy_path)
            payload["candidate_summary"] = {
                "summary": "approved runtime evidence present; SDK complete",
            }
            write_json(policy_path, payload)

            result = self.run_checker(root, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        text_details = [
            detail
            for detail in report["blocker_details"]
            if detail["reason"] == "planning_manifest_text_positive_claim"
        ]
        self.assertEqual([detail["label"] for detail in text_details], ["policy.candidate_summary.summary"])

    def test_allows_nested_negative_claim_context_in_planning_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "planning"
            copy_planning_sources(root)
            policy_path = root / POLICY_NAME
            payload = load_json(policy_path)
            payload["non_claims_detail"] = {
                "runtime_v1_ready": "blocked",
                "counts_toward_public_sdk": False,
            }
            write_json(policy_path, payload)

            result = self.run_checker(root, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("planning_manifest_nested_positive_claim", report["blockers"])
        self.assertIn("planning_report_outputs_principal_invalidation_policy_sha256_mismatch", report["blockers"])


if __name__ == "__main__":
    unittest.main()
