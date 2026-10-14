#!/usr/bin/env python3
"""Tests for build_player_identity_lifecycle_anchor_static_report.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "build_player_identity_lifecycle_anchor_static_report.py"
SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
ANCHOR_BINDING_TARGET_SET = "players-identity-lifecycle-intake"
ANCHOR_BINDING_TARGET_SET_REVISION = f"reflection_target_sets.py:{ANCHOR_BINDING_TARGET_SET}"
TRIPLET_SOURCE_TARGET_SET = "players-lifecycle-anchor-candidates"
TRIPLET_SOURCE_TARGET_SET_REVISION = f"reflection_target_sets.py:{TRIPLET_SOURCE_TARGET_SET}"
SOURCE_ROLE_POLICY = {
    "policy_scope": "source_names_only_not_runtime_evidence",
    "approved_runtime_triplet_source_names": [
        "ShooterGameMode.HandleNewPlayer",
        "ShooterGameMode.CheckJoinInProgress",
        "ShooterGameMode.OnLogout",
    ],
    "approved_triplet_sources": [
        "ShooterGameMode.HandleNewPlayer",
        "ShooterGameMode.CheckJoinInProgress",
        "ShooterGameMode.OnLogout",
    ],
    "runtime_triplet_evidence_status": "approved_source_names_only_runtime_evidence_missing",
    "approved_runtime_evidence_present": False,
    "static_lifecycle_anchor_source_names": [
        "ShooterGameMode.HandleNewPlayer",
        "ShooterGameMode.OnLogout",
    ],
    "static_lifecycle_anchor_sources": [
        "ShooterGameMode.HandleNewPlayer",
        "ShooterGameMode.OnLogout",
    ],
    "observer_rejected_start_source_names": ["ShooterGameMode.CheckJoinInProgress"],
    "observer_rejected_start_sources": ["ShooterGameMode.CheckJoinInProgress"],
    "chronology_guidance_only_source_names": ["GameMode.K2_PostLogin"],
    "chronology_only_non_anchor_sources": ["GameMode.K2_PostLogin"],
    "delegate_guidance_only_source_names": [
        "ShooterGameMode.OnPostLogin__DelegateSignature",
        "ShooterGameMode.OnStartNewPlayer__DelegateSignature",
    ],
    "delegate_guidance_only_sources": [
        "ShooterGameMode.OnPostLogin__DelegateSignature",
        "ShooterGameMode.OnStartNewPlayer__DelegateSignature",
    ],
    "guidance_only_non_triplet_source_names": [
        "GameMode.K2_PostLogin",
        "ShooterGameMode.OnPostLogin__DelegateSignature",
        "ShooterGameMode.OnStartNewPlayer__DelegateSignature",
    ],
    "all_six_planning_gap_evidence_status": "non_evidence",
    "runtime_ready": False,
    "public_sdk_ready": False,
    "promotion_ready": False,
}
ALL_SIX_PLANNING_GAP_POLICY = {
    "target_set": TRIPLET_SOURCE_TARGET_SET,
    "all_six_planning_gap_evidence_status": "non_evidence",
    "planning_gap_records_count_as_runtime_proof": False,
    "accepted_targets_fields_count_as_runtime_proof": False,
    "approved_runtime_evidence_present": False,
    "runtime_ready": False,
    "public_sdk_ready": False,
    "promotion_ready": False,
}


APPROVED_RUNTIME_TRIPLET_REQUIREMENT = {
    "approved_runtime_evidence_present": False,
    "approved_runtime_evidence_ready": False,
    "static_evidence_can_replace_runtime_triplet": False,
    "required_exact_triplet": [
        {
            "required_runtime_shape": "ShooterGameMode.HandleNewPlayer(1,1)",
            "required_source_target": "ShooterGameMode.HandleNewPlayer",
            "required_copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
            "required_copied_bool_values": ["1", "1"],
        },
        {
            "required_runtime_shape": "ShooterGameMode.CheckJoinInProgress(1,0)",
            "required_source_target": "ShooterGameMode.CheckJoinInProgress",
            "required_copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
            "required_copied_bool_values": ["1", "0"],
            "rejected_aliases": [
                "ShooterGameMode.CheckJoinInProgress",
                "CheckJoinInProgress",
            ],
        },
        {
            "required_runtime_shape": "ShooterGameMode.OnLogout(matched)",
            "required_source_target": "ShooterGameMode.OnLogout",
            "required_correlation_status": "matched",
        },
    ],
    "non_claim": (
        "static source orientation identifies source UFunctions only; approved runtime "
        "evidence still requires one copied session_start, exact CheckJoinInProgress(1,0) "
        "session_start_rejected, and matched session_end sibling set"
    ),
}


def static_report() -> dict:
    return {
        "schema": "obelisk.player-identity-static-lifecycle-orientation-check.v1",
        "status": "valid",
        "valid": True,
        "accepted_for_orientation": True,
        "accepted_lifecycle_anchors": False,
        "not_artifact_gate": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "approved_runtime_lifecycle_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_lifecycle_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_lifecycle_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "public_readiness_ready": False,
        "binary_sha256": SHA,
        "target_set": ANCHOR_BINDING_TARGET_SET,
        "checked_targets": [
            {
                "target": "ShooterGameMode.CheckJoinInProgress",
                "role_hint": "session_start_rejected",
                "status": "candidate_orientation_valid",
                "target_set_status": "known_lifecycle_orientation_not_in_closed_target_set",
                "required_runtime_shape": "ShooterGameMode.CheckJoinInProgress(1,0)",
                "required_source_target": "ShooterGameMode.CheckJoinInProgress",
                "required_copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "required_copied_bool_values": ["1", "0"],
                "source_name_only": True,
                "bare_source_alias_counts_as_runtime_evidence": False,
                "static_evidence_can_replace_runtime_triplet": False,
                "source_policy_scope": "source_names_only_not_runtime_evidence",
                "runtime_evidence_status": "approved_source_names_only_runtime_evidence_missing",
                "accepted_runtime_triplet_source_name": True,
                "static_lifecycle_anchor_source_name": False,
                "rejected_start_triplet_source_name": True,
                "anchor_binding_status": "observer_only_rejected_start_source_not_anchor",
                "accepted_target_name_scope": "source_name_only_not_runtime_evidence",
                "anchor_binding_label_scope": "source_name_only_not_runtime_evidence",
                "accepted_target_name_counts_as_runtime_proof": False,
                "anchor_binding_label_counts_as_runtime_proof": False,
                "counts_as_approved_runtime_lifecycle_evidence": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_lifecycle_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_progress": False,
                "runtime_ready": False,
                "public_sdk_ready": False,
                "promotion_ready": False,
            },
            {
                "target": "ShooterGameMode.HandleNewPlayer",
                "role_hint": "session_start",
                "status": "candidate_orientation_valid",
                "target_set_status": "known_lifecycle_orientation_not_in_closed_target_set",
                "required_runtime_shape": "ShooterGameMode.HandleNewPlayer(1,1)",
                "required_source_target": "ShooterGameMode.HandleNewPlayer",
                "required_copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "required_copied_bool_values": ["1", "1"],
                "source_name_only": True,
                "bare_source_alias_counts_as_runtime_evidence": False,
                "static_evidence_can_replace_runtime_triplet": False,
                "source_policy_scope": "source_names_only_not_runtime_evidence",
                "runtime_evidence_status": "approved_source_names_only_runtime_evidence_missing",
                "accepted_runtime_triplet_source_name": True,
                "static_lifecycle_anchor_source_name": True,
                "rejected_start_triplet_source_name": False,
                "anchor_binding_status": "static_anchor_source_name_only_not_runtime_evidence",
                "accepted_target_name_scope": "source_name_only_not_runtime_evidence",
                "anchor_binding_label_scope": "source_name_only_not_runtime_evidence",
                "accepted_target_name_counts_as_runtime_proof": False,
                "anchor_binding_label_counts_as_runtime_proof": False,
                "counts_as_approved_runtime_lifecycle_evidence": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_lifecycle_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_progress": False,
                "runtime_ready": False,
                "public_sdk_ready": False,
                "promotion_ready": False,
            },
            {
                "target": "ShooterGameMode.OnLogout",
                "role_hint": "session_end",
                "status": "candidate_orientation_valid",
                "target_set_status": "known_lifecycle_orientation_not_in_closed_target_set",
                "required_runtime_shape": "ShooterGameMode.OnLogout(matched)",
                "required_source_target": "ShooterGameMode.OnLogout",
                "required_correlation_status": "matched",
                "source_name_only": True,
                "bare_source_alias_counts_as_runtime_evidence": False,
                "static_evidence_can_replace_runtime_triplet": False,
                "source_policy_scope": "source_names_only_not_runtime_evidence",
                "runtime_evidence_status": "approved_source_names_only_runtime_evidence_missing",
                "accepted_runtime_triplet_source_name": True,
                "static_lifecycle_anchor_source_name": True,
                "rejected_start_triplet_source_name": False,
                "anchor_binding_status": "static_anchor_source_name_only_not_runtime_evidence",
                "accepted_target_name_scope": "source_name_only_not_runtime_evidence",
                "anchor_binding_label_scope": "source_name_only_not_runtime_evidence",
                "accepted_target_name_counts_as_runtime_proof": False,
                "anchor_binding_label_counts_as_runtime_proof": False,
                "counts_as_approved_runtime_lifecycle_evidence": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_lifecycle_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_progress": False,
                "runtime_ready": False,
                "public_sdk_ready": False,
                "promotion_ready": False,
            },
        ],
        "approved_runtime_triplet_requirement": json.loads(json.dumps(APPROVED_RUNTIME_TRIPLET_REQUIREMENT)),
        "lifecycle_source_policy": json.loads(json.dumps(SOURCE_ROLE_POLICY)),
        "all_six_planning_gap_policy": json.loads(json.dumps(ALL_SIX_PLANNING_GAP_POLICY)),
        "blockers": [],
    }


class BuildPlayerIdentityLifecycleAnchorStaticReportTests(unittest.TestCase):
    def run_tool(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
            self.fail(f"tool failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def test_builds_static_report_from_repo_fixtures_and_static_orientation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_path = root / "static-orientation.json"
            output_path = root / "lifecycle-static-report.json"
            static_path.write_text(json.dumps(static_report()), encoding="utf-8")

            result = self.run_tool(
                [
                    "--static-orientation-report",
                    str(static_path),
                    "--output",
                    str(output_path),
                    "--json",
                ]
            )

            stdout_payload = json.loads(result.stdout)
            output_payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, output_payload)
        self.assertEqual("obelisk.players-identity-lifecycle-anchor-static-report.v1", output_payload["schema"])
        self.assertTrue(output_payload["ready"])
        self.assertTrue(output_payload["accepted_for_lifecycle_anchor_binding"])
        self.assertEqual("static_accepted", output_payload["corroboration_status"])
        self.assertEqual(ANCHOR_BINDING_TARGET_SET, output_payload["anchor_binding_target_set"])
        self.assertEqual(ANCHOR_BINDING_TARGET_SET_REVISION, output_payload["anchor_binding_target_set_revision"])
        self.assertEqual(TRIPLET_SOURCE_TARGET_SET, output_payload["triplet_source_target_set"])
        self.assertEqual(TRIPLET_SOURCE_TARGET_SET_REVISION, output_payload["triplet_source_target_set_revision"])
        self.assertFalse(output_payload["promotion_ready"])
        self.assertFalse(output_payload["public_sdk_ready"])
        self.assertFalse(output_payload["runtime_ready"])
        self.assertFalse(output_payload["approved_runtime_lifecycle_evidence"])
        self.assertFalse(output_payload["approved_runtime_evidence_present"])
        self.assertFalse(output_payload["approved_runtime_evidence_ready"])
        self.assertFalse(output_payload["counts_as_approved_runtime_lifecycle_evidence"])
        self.assertFalse(output_payload["counts_as_runtime_lifecycle_evidence"])
        self.assertFalse(output_payload["counts_as_sdk_progress"])
        self.assertEqual(
            "static_source_binding_only_not_runtime_proof",
            output_payload["accepted_for_lifecycle_anchor_binding_scope"],
        )
        self.assertFalse(output_payload["accepted_for_lifecycle_anchor_binding_counts_as_runtime_proof"])
        self.assertFalse(output_payload["accepted_target_names_count_as_runtime_proof"])
        self.assertFalse(output_payload["anchor_binding_labels_count_as_runtime_proof"])
        self.assertIn("not approved runtime evidence", output_payload["accepted_target_names_meaning"])
        self.assertFalse(output_payload["server_operations_authorized"])
        source_policy = output_payload["lifecycle_source_policy"]
        self.assertEqual(source_policy["policy_scope"], "source_names_only_not_runtime_evidence")
        self.assertEqual(
            source_policy["runtime_triplet_evidence_status"],
            "approved_source_names_only_runtime_evidence_missing",
        )
        self.assertEqual(
            source_policy["static_lifecycle_anchor_sources"],
            ["ShooterGameMode.HandleNewPlayer", "ShooterGameMode.OnLogout"],
        )
        self.assertEqual(
            source_policy["observer_rejected_start_sources"],
            ["ShooterGameMode.CheckJoinInProgress"],
        )
        self.assertEqual(source_policy["all_six_planning_gap_evidence_status"], "non_evidence")
        self.assertFalse(source_policy["approved_runtime_evidence_present"])
        self.assertFalse(source_policy["runtime_ready"])
        self.assertFalse(source_policy["public_sdk_ready"])
        self.assertFalse(source_policy["promotion_ready"])
        all_six_policy = output_payload["all_six_planning_gap_policy"]
        self.assertEqual(all_six_policy["all_six_planning_gap_evidence_status"], "non_evidence")
        self.assertFalse(all_six_policy["planning_gap_records_count_as_runtime_proof"])
        self.assertFalse(all_six_policy["accepted_targets_fields_count_as_runtime_proof"])
        self.assertFalse(all_six_policy["approved_runtime_evidence_present"])
        self.assertFalse(all_six_policy["runtime_ready"])
        self.assertFalse(all_six_policy["public_sdk_ready"])
        self.assertFalse(all_six_policy["promotion_ready"])
        self.assertEqual(
            {"ShooterGameMode.HandleNewPlayer", "ShooterGameMode.OnLogout"},
            {target["target"] for target in output_payload["accepted_targets"]},
        )
        for target in output_payload["accepted_targets"]:
            self.assertEqual(target["accepted_target_name_scope"], "source_name_only_not_runtime_evidence")
            self.assertEqual(target["anchor_binding_label_scope"], "source_name_only_not_runtime_evidence")
            self.assertFalse(target["accepted_target_name_counts_as_runtime_proof"])
            self.assertFalse(target["anchor_binding_label_counts_as_runtime_proof"])
            self.assertFalse(target["counts_as_approved_runtime_lifecycle_evidence"])
            self.assertFalse(target["counts_as_runtime_lifecycle_evidence"])
            self.assertFalse(target["counts_as_sdk_progress"])
            self.assertFalse(target["runtime_ready"])
            self.assertFalse(target["public_sdk_ready"])
            self.assertFalse(target["promotion_ready"])
        self.assertEqual(
            {
                "ShooterGameMode.HandleNewPlayer",
                "ShooterGameMode.CheckJoinInProgress",
                "ShooterGameMode.OnLogout",
            },
            {target["target"] for target in output_payload["accepted_triplet_sources"]},
        )
        self.assertEqual(
            {
                "session_start": "ShooterGameMode.HandleNewPlayer",
                "session_start_rejected": "ShooterGameMode.CheckJoinInProgress(1,0)",
                "session_start_rejected_source": "ShooterGameMode.CheckJoinInProgress",
                "session_end": "ShooterGameMode.OnLogout",
                "evidence_boundary": "runtime copied sibling-set checker still required",
                "approved_runtime_evidence": False,
                "runtime_evidence_ready": False,
                "counts_toward_sdk": False,
                "counts_toward_p0_dependency_chain": False,
                "bare_check_join_in_progress_alias_accepted": False,
                "static_evidence_can_replace_runtime_triplet": False,
            },
            output_payload["required_runtime_triplet_sources"],
        )
        self.assertEqual(APPROVED_RUNTIME_TRIPLET_REQUIREMENT, output_payload["approved_runtime_triplet_requirement"])
        self.assertEqual(
            {
                "ShooterGameMode.HandleNewPlayer": "a9b3049dc221f128924ff0c6eb45287bf630dfaea4e4ab33bbf93647a5d3361b",
                "ShooterGameMode.OnLogout": "e79e416a408bbe652a31f58c710cfeb03daa0acf2e0ebef55a7ba61c83a414aa",
            },
            {target["target"]: target["source_snapshot_sha256"] for target in output_payload["accepted_targets"]},
        )
        self.assertEqual(
            {
                "ShooterGameMode.HandleNewPlayer": "a9b3049dc221f128924ff0c6eb45287bf630dfaea4e4ab33bbf93647a5d3361b",
                "ShooterGameMode.CheckJoinInProgress": "3b38ce4d991cb28e547850128412e78e11eac1f32b6fdd15fd756fc485552ef2",
                "ShooterGameMode.OnLogout": "e79e416a408bbe652a31f58c710cfeb03daa0acf2e0ebef55a7ba61c83a414aa",
            },
            {
                target["target"]: target["source_snapshot_sha256"]
                for target in output_payload["accepted_triplet_sources"]
            },
        )
        checkjoin_triplet_source = next(
            target
            for target in output_payload["accepted_triplet_sources"]
            if target["target"] == "ShooterGameMode.CheckJoinInProgress"
        )
        self.assertEqual(checkjoin_triplet_source["required_runtime_shape"], "ShooterGameMode.CheckJoinInProgress(1,0)")
        self.assertEqual(checkjoin_triplet_source["required_copied_bool_fields"], ["bIsFromLogin", "ReturnValue"])
        self.assertEqual(checkjoin_triplet_source["required_copied_bool_values"], ["1", "0"])
        self.assertEqual(checkjoin_triplet_source["source_binary_sha256"], SHA)
        self.assertEqual(checkjoin_triplet_source["target_set"], TRIPLET_SOURCE_TARGET_SET)
        self.assertEqual(
            checkjoin_triplet_source["anchor_binding_status"],
            "observer_only_rejected_start_source_not_anchor",
        )
        self.assertIn("capture_id:base-identity-core", checkjoin_triplet_source["source_artifact_ids"])
        self.assertFalse(checkjoin_triplet_source["bare_source_alias_counts_as_runtime_evidence"])
        self.assertFalse(checkjoin_triplet_source["static_evidence_can_replace_runtime_triplet"])
        self.assertEqual(checkjoin_triplet_source["source_policy_scope"], "source_names_only_not_runtime_evidence")
        self.assertEqual(
            checkjoin_triplet_source["runtime_evidence_status"],
            "approved_source_names_only_runtime_evidence_missing",
        )
        self.assertFalse(checkjoin_triplet_source["static_lifecycle_anchor_source_name"])
        self.assertTrue(checkjoin_triplet_source["rejected_start_triplet_source_name"])
        self.assertEqual(checkjoin_triplet_source["accepted_target_name_scope"], "source_name_only_not_runtime_evidence")
        self.assertEqual(checkjoin_triplet_source["anchor_binding_label_scope"], "source_name_only_not_runtime_evidence")
        self.assertFalse(checkjoin_triplet_source["accepted_target_name_counts_as_runtime_proof"])
        self.assertFalse(checkjoin_triplet_source["anchor_binding_label_counts_as_runtime_proof"])
        self.assertFalse(checkjoin_triplet_source["counts_as_approved_runtime_lifecycle_evidence"])
        self.assertFalse(checkjoin_triplet_source["counts_as_runtime_lifecycle_evidence"])
        self.assertFalse(checkjoin_triplet_source["runtime_ready"])
        self.assertFalse(checkjoin_triplet_source["public_sdk_ready"])
        self.assertFalse(checkjoin_triplet_source["promotion_ready"])
        artifact_identity = output_payload["artifact_identity"]
        self.assertEqual(ANCHOR_BINDING_TARGET_SET, artifact_identity["anchor_binding_target_set"])
        self.assertEqual(ANCHOR_BINDING_TARGET_SET_REVISION, artifact_identity["anchor_binding_target_set_revision"])
        self.assertEqual(TRIPLET_SOURCE_TARGET_SET, artifact_identity["triplet_source_target_set"])
        self.assertEqual(TRIPLET_SOURCE_TARGET_SET_REVISION, artifact_identity["triplet_source_target_set_revision"])
        self.assertEqual(
            [
                "artifact_sha256:62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78",
                "capture_id:base-identity-core",
                "evidence_pack_id:player-identity-base-core-evidence-pack",
            ],
            artifact_identity["source_artifact_ids"],
        )
        self.assertIn("does not fabricate runtime evidence", " ".join(output_payload["non_claims"]))
        self.assertIn("CheckJoinInProgress is recorded only as the rejected-start triplet source", " ".join(output_payload["non_claims"]))
        self.assertIn("bare CheckJoinInProgress without copied bool values", " ".join(output_payload["non_claims"]))

    def test_fails_closed_without_static_evidence(self) -> None:
        result = self.run_tool(["--json"], check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertFalse(payload["accepted_for_lifecycle_anchor_binding"])
        self.assertIn("static_orientation_report_missing", payload["blockers"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["runtime_ready"])

    def test_rejects_protected_static_orientation_report_path(self) -> None:
        result = self.run_tool(
            ["--static-orientation-report", "/servidor/ark/workspace-offline/static-orientation.json"],
            check=False,
        )

        self.assertEqual(1, result.returncode)
        self.assertIn("must not read from protected server root", result.stderr)

    def test_rejects_static_orientation_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_payload = static_report()
            static_payload["runtime_ready"] = True
            static_path = root / "static-orientation.json"
            static_path.write_text(json.dumps(static_payload), encoding="utf-8")

            result = self.run_tool(["--static-orientation-report", str(static_path), "--json"], check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("static_orientation_runtime_ready_not_false", payload["blockers"])
        self.assertFalse(payload["ready"])

    def test_rejects_static_orientation_bare_checkjoin_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_payload = static_report()
            checkjoin = next(
                target
                for target in static_payload["checked_targets"]
                if target["target"] == "ShooterGameMode.CheckJoinInProgress"
            )
            checkjoin["required_runtime_shape"] = "ShooterGameMode.CheckJoinInProgress"
            checkjoin["required_copied_bool_values"] = []
            static_payload["approved_runtime_triplet_requirement"]["required_exact_triplet"][1][
                "required_runtime_shape"
            ] = "ShooterGameMode.CheckJoinInProgress"
            static_path = root / "static-orientation.json"
            static_path.write_text(json.dumps(static_payload), encoding="utf-8")

            result = self.run_tool(["--static-orientation-report", str(static_path), "--json"], check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "static_orientation_required_runtime_shape_mismatch:ShooterGameMode.CheckJoinInProgress",
            payload["blockers"],
        )
        self.assertIn("static_orientation_rejected_start_copied_bool_values_mismatch", payload["blockers"])
        self.assertIn("static_orientation_approved_runtime_triplet_requirement_mismatch", payload["blockers"])
        self.assertFalse(payload["ready"])

    def test_rejects_static_orientation_checkjoin_target_set_role_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_payload = static_report()
            checkjoin = next(
                target
                for target in static_payload["checked_targets"]
                if target["target"] == "ShooterGameMode.CheckJoinInProgress"
            )
            checkjoin["target_set_status"] = "accepted_lifecycle_anchor_binding"
            checkjoin["anchor_binding_status"] = "static_anchor_source_name_only_not_runtime_evidence"
            checkjoin["static_lifecycle_anchor_source_name"] = True
            checkjoin["accepted_target_name_counts_as_runtime_proof"] = True
            static_path = root / "static-orientation.json"
            static_path.write_text(json.dumps(static_payload), encoding="utf-8")

            result = self.run_tool(["--static-orientation-report", str(static_path), "--json"], check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn(
            "static_orientation_target_set_status_mismatch:ShooterGameMode.CheckJoinInProgress",
            payload["blockers"],
        )
        self.assertIn(
            "static_orientation_anchor_binding_status_mismatch:ShooterGameMode.CheckJoinInProgress",
            payload["blockers"],
        )
        self.assertIn(
            "static_orientation_static_anchor_source_role_mismatch:ShooterGameMode.CheckJoinInProgress",
            payload["blockers"],
        )
        self.assertIn(
            "static_orientation_row_accepted_target_name_counts_as_runtime_proof_not_false:ShooterGameMode.CheckJoinInProgress",
            payload["blockers"],
        )
        self.assertFalse(payload["ready"])


if __name__ == "__main__":
    unittest.main()
