#!/usr/bin/env python3
"""Tests for check_player_identity_runtime_principal_start_end_evidence.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts" / "check_player_identity_runtime_principal_start_end_evidence.py"
SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"


def event(sequence: int, role: str, target: str, values: list[str]) -> dict[str, object]:
    if role == "session_start":
        return {
            "sequence": sequence,
            "target": target,
            "role": role,
            "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
            "copied_bool_values": values,
            "principal_action": "candidate_created",
            "apply_status": "session_start_created",
            "correlation_status": "not_applicable",
        }
    if role == "session_end":
        return {
            "sequence": sequence,
            "target": target,
            "role": role,
            "copied_bool_fields": [],
            "copied_bool_values": [],
            "principal_action": "candidate_invalidated",
            "apply_status": "session_end_invalidated",
            "correlation_status": "matched",
        }
    raise AssertionError(role)


def summary(*, server_paths_allowed: bool = False, events: list[dict[str, object]] | None = None) -> dict[str, object]:
    events = events or [
        event(1, "session_start", "ShooterGameMode.HandleNewPlayer", ["1", "1"]),
        event(2, "session_end", "ShooterGameMode.OnLogout", []),
    ]
    return {
        "schema": "obelisk.runtime-observer-log-summary.v1",
        "evidence": {
            "kind": "runtime-observer-log",
            "server_paths_allowed": server_paths_allowed,
            "obelisk_commit": "test",
            "sources": [
                {
                    "path": "/tmp/obelisk-start-end/Obelisk.log",
                    "sha256": "0" * 64,
                    "line_count": 10,
                }
            ],
        },
        "runtime": {
            "loaded_native_ld_preload": True,
            "process_event_candidate_count": 1,
            "process_event_candidates": [{"index": 0, "address": "0x1d34e20"}],
            "process_event_address": "0x1d34e20",
            "process_event_hook_installed": True,
            "process_event_hook_patch_size": 18,
            "broad_process_event_trace_lines": 0,
            "reflection_scanner_disabled": True,
            "plugins_disabled": True,
        },
        "modules": {
            "player_principal_lifecycle": {
                "observer_enabled": True,
                "observer_gate_count": 1,
                "gate_sha256": [SHA],
                "diagnostic_candidate_target_counts": {
                    "ShooterGameMode.CheckJoinInProgress": 1,
                },
                "observed_event_cases": events,
                "functions": {
                    "ShooterGameMode.HandleNewPlayer": {
                        "details": {
                            "role": ["session_start"],
                            "post_original": ["true"],
                            "copied_bool_fields": ["bIsFromLogin,ReturnValue"],
                            "copied_bool_values": ["1,1"],
                            "redacted_count": [3],
                            "redacted_fields": ["NewPlayer,PlayerData,PlayerCharacter"],
                            "principal_action": ["candidate_created"],
                            "apply_status": ["session_start_created"],
                            "correlation_status": ["not_applicable"],
                            "principal_id_logged": ["false"],
                            "principal_generation_logged": ["false"],
                            "delivery_claim": ["none"],
                        },
                    },
                    "ShooterGameMode.OnLogout": {
                        "details": {
                            "role": ["session_end"],
                            "post_original": ["true"],
                            "copied_bool_fields": [""],
                            "copied_bool_values": [""],
                            "redacted_count": [1],
                            "redacted_fields": ["Exiting"],
                            "principal_action": ["candidate_invalidated"],
                            "apply_status": ["session_end_invalidated"],
                            "correlation_status": ["matched"],
                            "principal_id_logged": ["false"],
                            "principal_generation_logged": ["false"],
                            "delivery_claim": ["none"],
                        },
                    },
                },
            },
        },
    }


def ready_log_role_event(sequence: int, role: str) -> dict[str, object]:
    base: dict[str, object] = {
        "role": role,
        "line_number": sequence + 1,
        "sequence": sequence,
        "timestamp_status": "utc",
        "timestamp_prefix": f"2026-06-07T12:51:{sequence:02d}Z",
        "inside_fresh_window": True,
        "status_proof_ok": True,
        "approved_copy_shape_ok": True,
        "approved_copy_shape_mismatches": [],
        "principal_id_logged": "false",
        "principal_generation_logged": "false",
        "delivery_claim": "none",
    }
    if role == "session_start":
        base.update(
            {
                "target": "ShooterGameMode.HandleNewPlayer",
                "post_original": "true",
                "copied_bool_fields": "bIsFromLogin,ReturnValue",
                "copied_bool_values": "1,1",
                "redacted_count": "3",
                "redacted_fields": "NewPlayer,PlayerData,PlayerCharacter",
                "principal_action": "candidate_created",
                "apply_status": "session_start_created",
                "correlation_status": "not_applicable",
            }
        )
        return base
    if role == "session_end":
        base.update(
            {
                "target": "ShooterGameMode.OnLogout",
                "post_original": "true",
                "copied_bool_fields": "",
                "copied_bool_values": "",
                "redacted_count": "1",
                "redacted_fields": "Exiting",
                "principal_action": "candidate_invalidated",
                "apply_status": "session_end_invalidated",
                "correlation_status": "matched",
            }
        )
        return base
    raise AssertionError(role)


def ready_log_dry_run_report() -> dict[str, object]:
    start = ready_log_role_event(1, "session_start")
    end = ready_log_role_event(3, "session_end")
    roles_present = ["session_start", "session_end"]
    missing_roles = ["session_start_rejected"]
    exact_triplet = {
        "accepted": False,
        "status": "missing",
        "blockers": [
            "exact_copied_runtime_triplet_missing_session_start_rejected",
            "exact_copied_runtime_triplet_not_selected",
        ],
        "required_roles": ["session_start", "session_start_rejected", "session_end"],
        "accepted_roles": roles_present,
        "start_end_only_detected": True,
        "copied_log_only_counts_as_approved_runtime_evidence": False,
        "copied_log_only_counts_as_runtime_evidence": False,
        "start_end_only_counts_as_approved_runtime_evidence": False,
        "start_end_only_counts_as_runtime_evidence": False,
        "passive_or_diagnostic_material_counts_as_approved_runtime_evidence": False,
    }
    analysis = {
        "observer_enabled": True,
        "observer_enable_in_fresh_window": True,
        "observer_binary_sha256": SHA,
        "expected_binary_sha256": SHA,
        "binary_sha256_match": True,
        "roles_present": roles_present,
        "missing_roles": missing_roles,
        "accepted_role_events": {
            "session_start": start,
            "session_end": end,
        },
        "accepted_lifecycle_event_count": 2,
        "accepted_lifecycle_events": [
            {
                "role": "session_start",
                "line_number": 2,
                "sequence": 1,
                "target": "ShooterGameMode.HandleNewPlayer",
                "timestamp_prefix": "2026-06-07T12:51:01Z",
                "inside_fresh_window": True,
            },
            {
                "role": "session_end",
                "line_number": 4,
                "sequence": 3,
                "target": "ShooterGameMode.OnLogout",
                "timestamp_prefix": "2026-06-07T12:51:03Z",
                "inside_fresh_window": True,
            },
        ],
        "lifecycle_triplet_order": {
            "status": "incomplete",
            "expected_roles": ["session_start", "session_start_rejected", "session_end"],
            "observed_roles_by_line": roles_present,
            "blockers": [],
            "missing_roles": missing_roles,
        },
        "exact_copied_runtime_triplet": exact_triplet,
        "rejected_or_incomplete_role_event_count": 0,
        "rejected_or_incomplete_role_events": [],
        "historical_roles_present": [],
        "historical_accepted_role_event_count": 0,
        "historical_accepted_role_events": [],
        "missing_roles_with_historical_only": [],
        "missing_roles_with_unapproved_shape": [],
        "timestamp_violation_count": 0,
        "timestamp_violations": [],
        "ready_to_copy": False,
        "copy_readiness": "blocked_missing_lifecycle_roles",
        "partial_accepted_lifecycle_role_set": True,
        "partial_accepted_lifecycle_roles_count_as_ready_to_copy": False,
        "partial_accepted_lifecycle_roles_count_as_approved_runtime_evidence": False,
        "diagnostic_or_rejected_lifecycle_lines_count_as_ready_to_copy": False,
        "diagnostic_or_rejected_lifecycle_lines_count_as_approved_runtime_evidence": False,
        "diagnostic_or_rejected_lifecycle_lines_count_as_sdk_or_p0_progress": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "copied_log_only_counts_as_approved_runtime_evidence": False,
        "copied_log_only_counts_as_runtime_evidence": False,
        "start_end_only_counts_as_approved_runtime_evidence": False,
        "start_end_only_counts_as_runtime_evidence": False,
    }
    return {
        "schema": "obelisk.player-principal-lifecycle-ready-log-copy.v1",
        "status": "blocked",
        "ready": False,
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "v1_completion_ready": False,
        "stable_claim_allowed": False,
        "instance": "arkserver3",
        "source_log": "/tmp/Obelisk.log",
        "evidence_dir": "/tmp/evidence",
        "target_log": "/tmp/evidence/Obelisk.log",
        "execute_requested": False,
        "allow_live_log_read": True,
        "allow_evidence_dir_write": False,
        "allow_post_window_sidecar_generation": False,
        "allow_post_window_preflight_live_read": False,
        "overwrite": False,
        "ready_to_copy": False,
        "copy_readiness": "blocked_missing_lifecycle_roles",
        "copied": False,
        "post_window_sidecars_ready": False,
        "current_route_blocker": "approved_runtime_evidence_missing",
        "approved_runtime_evidence_checker_required": (
            "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
        ),
        "copied_artifacts_count_as_approved_runtime_evidence_until_checker_accepts": False,
        "analysis": analysis,
        "roles_present": roles_present,
        "missing_roles": missing_roles,
        "blockers": ["blocked_missing_lifecycle_roles"],
        "non_claims": [
            "ready-log copy is operational copy readiness only",
            "copied Obelisk.log is still not approved runtime evidence until sibling-set bundle checkers accept it",
            "this helper does not start, stop, restart, send Discord, edit markers/env, publish, or claim SDK readiness",
        ],
    }


class PrincipalStartEndEvidenceTests(unittest.TestCase):
    def run_checker(self, payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "summary.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(CHECKER), "--source-summary", str(path), "--json"],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    def test_accepts_ordered_start_end_without_promoting_approved_runtime_evidence(self) -> None:
        result = self.run_checker(summary())
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertEqual(report["ready_scope"], "principal_start_end_runtime_evidence_only")
        self.assertTrue(report["principal_start_end_runtime_evidence_ready"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["approved_runtime_principal_lifecycle_evidence_ready"])
        self.assertFalse(report["counts_as_approved_runtime_principal_lifecycle_evidence"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["runtime_readiness"])
        self.assertFalse(report["counts_toward_runtime_readiness"])
        self.assertFalse(report["public_readiness"])
        self.assertFalse(report["counts_toward_public_readiness"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["counts_as_sdk_or_p0_progress"])
        self.assertFalse(report["counts_toward_complete_sdk_claim"])
        self.assertFalse(report["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(report["resolved_inputs"], ["runtime.lifecycle_start_end_evidence"])
        self.assertEqual(
            report["remaining_runtime_inputs"],
            [
                "runtime.lifecycle_rejected_start_evidence",
                "approved_runtime_principal_lifecycle_evidence_bundle",
            ],
        )
        self.assertEqual(report["next_review_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(
            report["strict_approved_runtime_evidence_blockers"],
            ["missing_exact_CheckJoinInProgress_1_0_session_start_rejected"],
        )
        self.assertFalse(report["contract_review_input_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["exact_check_join_in_progress_1_0_triplet_satisfied"])
        self.assertFalse(report["start_end_only_replaces_exact_check_join_in_progress_1_0_triplet"])
        self.assertFalse(report["exact_check_join_in_progress_1_0_triplet"]["satisfied"])
        self.assertFalse(report["exact_check_join_in_progress_1_0_triplet"]["replaced_by_principal_start_end_only"])
        self.assertIn("approved_runtime_principal_lifecycle_evidence_bundle", report["does_not_resolve"])
        self.assertEqual(report["diagnostic_coverage"]["check_join_in_progress_diagnostic_count"], 1)
        self.assertFalse(
            report["diagnostic_coverage"][
                "diagnostic_candidates_count_as_exact_check_join_in_progress_1_0_triplet"
            ]
        )

    def test_accepts_ready_log_dry_run_start_end_context_without_counting_it(self) -> None:
        result = self.run_checker(ready_log_dry_run_report())
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertEqual(report["source_kind"], "player_principal_lifecycle_ready_log_copy_dry_run")
        self.assertEqual(report["ready_scope"], "principal_start_end_runtime_evidence_only")
        self.assertTrue(report["accepted_for_contract_review"])
        self.assertTrue(report["principal_start_end_runtime_evidence_ready"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["remaining_route_blockers"], ["approved_runtime_evidence_missing"])
        self.assertEqual(report["next_review_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(
            report["approved_runtime_evidence_blockers"],
            ["missing_exact_CheckJoinInProgress_1_0_session_start_rejected"],
        )
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["approved_runtime_principal_lifecycle_evidence_ready"])
        self.assertFalse(report["accepted_as_approved_runtime_principal_lifecycle_evidence"])
        self.assertFalse(report["counts_as_approved_runtime_principal_lifecycle_evidence"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["runtime_readiness"])
        self.assertFalse(report["counts_toward_runtime_readiness"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["public_readiness"])
        self.assertFalse(report["counts_toward_public_readiness"])
        self.assertFalse(report["counts_as_sdk_progress"])
        self.assertFalse(report["counts_as_sdk_or_p0_progress"])
        self.assertFalse(report["counts_as_p0_progress"])
        self.assertFalse(report["counts_toward_complete_sdk_claim"])
        self.assertFalse(report["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(report["resolved_inputs"], ["runtime.lifecycle_start_end_evidence"])
        self.assertIn("runtime.lifecycle_rejected_start_evidence", report["does_not_resolve"])
        self.assertIn("approved_runtime_principal_lifecycle_evidence_bundle", report["does_not_resolve"])
        self.assertTrue(report["diagnostic_coverage"]["session_start_rejected_explicitly_missing"])
        self.assertEqual(report["matched_events"]["session_start"]["apply_status"], "session_start_created")
        self.assertEqual(report["matched_events"]["session_end"]["correlation_status"], "matched")
        self.assertFalse(report["exact_check_join_in_progress_1_0_triplet"]["satisfied"])
        self.assertFalse(report["start_end_only_replaces_exact_check_join_in_progress_1_0_triplet"])
        self.assertFalse(report["source_ready_log_copy"]["ready_to_copy"])
        self.assertEqual(report["source_ready_log_copy"]["missing_roles"], ["session_start_rejected"])
        self.assertEqual(report["source_overclaimed_readiness_or_authorization_flags"], [])
        self.assertEqual(report["source_overclaimed_progress_flags"], [])

    def test_rejects_ready_log_dry_run_approved_or_readiness_overclaims(self) -> None:
        payload = ready_log_dry_run_report()
        payload["approved_runtime_evidence"] = True
        payload["public_sdk_ready"] = True
        payload["analysis"]["counts_as_approved_runtime_evidence"] = True
        payload["analysis"]["start_end_only_counts_as_approved_runtime_evidence"] = True
        payload["analysis"]["diagnostic_or_rejected_lifecycle_lines_count_as_sdk_or_p0_progress"] = True
        payload["complete_sdk_claim_progress_contribution"] = "1/12"

        result = self.run_checker(payload)
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)

        self.assertFalse(report["ready"])
        self.assertFalse(report["principal_start_end_runtime_evidence_ready"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertEqual(report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertIn("ready_log_copy_approved_runtime_evidence_not_false", report["blockers"])
        self.assertIn("ready_log_copy_public_sdk_ready_not_false", report["blockers"])
        self.assertIn(
            "ready_log_copy_analysis_counts_as_approved_runtime_evidence_not_false",
            report["blockers"],
        )
        self.assertIn(
            "source_alias_overclaim:$.approved_runtime_evidence",
            report["blockers"],
        )
        self.assertIn("source_alias_overclaim:$.public_sdk_ready", report["blockers"])
        self.assertIn(
            "source_alias_overclaim:$.analysis.counts_as_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertIn(
            "source_alias_overclaim:$.analysis.start_end_only_counts_as_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertIn(
            "source_alias_overclaim:$.analysis.diagnostic_or_rejected_lifecycle_lines_count_as_sdk_or_p0_progress",
            report["blockers"],
        )
        self.assertIn(
            "source_progress_overclaim:$.complete_sdk_claim_progress_contribution",
            report["blockers"],
        )
        self.assertIn(
            "missing_exact_CheckJoinInProgress_1_0_session_start_rejected",
            report["blockers"],
        )

    def test_rejects_camelcase_and_dashed_source_overclaim_aliases(self) -> None:
        payload = ready_log_dry_run_report()
        payload["approvedRuntimeEvidencePresent"] = True
        payload["publicSdkReady"] = True
        payload["runtimeReady"] = True
        payload["sdkProgress"] = 1
        payload["p0Progress"] = "1/4"
        payload["analysis"]["countsAsApprovedRuntimeEvidence"] = True
        payload["analysis"]["counts-as-runtime-evidence"] = True
        payload["analysis"]["startEndOnlyCountsAsApprovedRuntimeEvidence"] = "ready"
        payload["analysis"]["completeSdkProgressRatio"] = "1/12"
        payload["analysis"]["exactCopiedRuntimeTriplet"] = {"ready": True}

        result = self.run_checker(payload)
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)

        self.assertFalse(report["ready"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertIn(
            "source_alias_overclaim:$.approvedRuntimeEvidencePresent",
            report["blockers"],
        )
        self.assertIn("source_alias_overclaim:$.publicSdkReady", report["blockers"])
        self.assertIn("source_alias_overclaim:$.runtimeReady", report["blockers"])
        self.assertIn(
            "source_alias_overclaim:$.analysis.countsAsApprovedRuntimeEvidence",
            report["blockers"],
        )
        self.assertIn(
            "source_alias_overclaim:$.analysis.counts-as-runtime-evidence",
            report["blockers"],
        )
        self.assertIn(
            "source_alias_overclaim:$.analysis.startEndOnlyCountsAsApprovedRuntimeEvidence",
            report["blockers"],
        )
        self.assertIn(
            "source_alias_overclaim:$.analysis.exactCopiedRuntimeTriplet.ready",
            report["blockers"],
        )
        self.assertIn("source_progress_overclaim:$.sdkProgress", report["blockers"])
        self.assertIn("source_progress_overclaim:$.p0Progress", report["blockers"])
        self.assertIn(
            "source_progress_overclaim:$.analysis.completeSdkProgressRatio",
            report["blockers"],
        )
        self.assertIn(
            "missing_exact_CheckJoinInProgress_1_0_session_start_rejected",
            report["blockers"],
        )

    def test_rejects_role_alias_for_rejected_start_as_start_end_context(self) -> None:
        payload = summary()
        payload["modules"]["player_principal_lifecycle"]["role_alias"] = {
            "alias": "session_start_rejected",
            "target": "ShooterGameMode.CheckJoinInProgress",
            "counts_as_role": True,
        }

        result = self.run_checker(payload)
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)

        self.assertFalse(report["ready"])
        self.assertFalse(report["principal_start_end_runtime_evidence_ready"])
        self.assertIn(
            "source_lifecycle_role_alias:$.modules.player_principal_lifecycle.role_alias",
            report["blockers"],
        )
        self.assertIn(
            "missing_exact_CheckJoinInProgress_1_0_session_start_rejected",
            report["blockers"],
        )
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["public_sdk_ready"])

    def test_rejects_principal_lifecycle_triplet_and_readiness_overclaims(self) -> None:
        payload = ready_log_dry_run_report()
        payload["approved_runtime_principal_lifecycle_evidence_ready"] = True
        payload["approved_runtime_principal_lifecycle_evidence_bundle_accepted"] = True
        payload["counts_as_approved_runtime_principal_lifecycle_evidence"] = True
        payload["counts_as_sdk_or_p0_progress"] = True
        payload["public_readiness"] = True
        payload["runtime_readiness"] = True
        payload["exact_check_join_in_progress_1_0_triplet_satisfied"] = True
        payload["start_end_only_replaces_exact_check_join_in_progress_1_0_triplet"] = True
        payload["analysis"]["exact_copied_runtime_triplet"]["accepted"] = True

        result = self.run_checker(payload)
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)

        self.assertFalse(report["ready"])
        self.assertFalse(report["approved_runtime_principal_lifecycle_evidence_ready"])
        self.assertFalse(report["counts_as_approved_runtime_principal_lifecycle_evidence"])
        self.assertFalse(report["counts_as_sdk_or_p0_progress"])
        self.assertFalse(report["public_readiness"])
        self.assertFalse(report["runtime_readiness"])
        self.assertFalse(report["exact_check_join_in_progress_1_0_triplet_satisfied"])
        self.assertFalse(report["start_end_only_replaces_exact_check_join_in_progress_1_0_triplet"])
        self.assertIn("ready_log_copy_exact_triplet_accepted_not_false", report["blockers"])
        self.assertIn(
            "source_alias_overclaim:$.approved_runtime_principal_lifecycle_evidence_ready",
            report["blockers"],
        )
        self.assertIn(
            "source_alias_overclaim:$.approved_runtime_principal_lifecycle_evidence_bundle_accepted",
            report["blockers"],
        )
        self.assertIn(
            "source_alias_overclaim:$.counts_as_approved_runtime_principal_lifecycle_evidence",
            report["blockers"],
        )
        self.assertIn(
            "source_alias_overclaim:$.counts_as_sdk_or_p0_progress",
            report["blockers"],
        )
        self.assertIn("source_alias_overclaim:$.public_readiness", report["blockers"])
        self.assertIn("source_alias_overclaim:$.runtime_readiness", report["blockers"])
        self.assertIn(
            "source_alias_overclaim:$.exact_check_join_in_progress_1_0_triplet_satisfied",
            report["blockers"],
        )
        self.assertIn(
            "source_alias_overclaim:$.start_end_only_replaces_exact_check_join_in_progress_1_0_triplet",
            report["blockers"],
        )
        self.assertIn(
            "source_alias_overclaim:$.analysis.exact_copied_runtime_triplet.accepted",
            report["blockers"],
        )
        self.assertIn(
            "missing_exact_CheckJoinInProgress_1_0_session_start_rejected",
            report["blockers"],
        )

    def test_rejects_ready_log_ready_to_copy_alias_as_start_end_context(self) -> None:
        payload = ready_log_dry_run_report()
        payload["ready_to_copy"] = True
        payload["analysis"]["ready_to_copy"] = True

        result = self.run_checker(payload)
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)

        self.assertFalse(report["ready"])
        self.assertIn("ready_log_copy_ready_to_copy_not_false", report["blockers"])
        self.assertIn("ready_log_copy_analysis_ready_to_copy_not_false", report["blockers"])
        self.assertIn("source_alias_overclaim:$.ready_to_copy", report["blockers"])
        self.assertIn("source_alias_overclaim:$.analysis.ready_to_copy", report["blockers"])

    def test_rejects_live_server_path_summary(self) -> None:
        result = self.run_checker(summary(server_paths_allowed=True))
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("source_summary_not_copied_or_offline", report["blockers"])
        self.assertFalse(report["principal_start_end_runtime_evidence_ready"])

    def test_rejects_missing_end(self) -> None:
        result = self.run_checker(
            summary(events=[event(1, "session_start", "ShooterGameMode.HandleNewPlayer", ["1", "1"])])
        )
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("session_end_case_missing_or_not_after_start", report["blockers"])

    def test_rejects_wrong_start_shape(self) -> None:
        result = self.run_checker(
            summary(
                events=[
                    event(1, "session_start", "ShooterGameMode.HandleNewPlayer", ["0", "1"]),
                    event(2, "session_end", "ShooterGameMode.OnLogout", []),
                ]
            )
        )
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("session_start_case_missing", report["blockers"])

    def test_rejects_missing_apply_or_correlation_statuses(self) -> None:
        start = event(1, "session_start", "ShooterGameMode.HandleNewPlayer", ["1", "1"])
        start.pop("apply_status")
        end = event(2, "session_end", "ShooterGameMode.OnLogout", [])
        end.pop("correlation_status")

        result = self.run_checker(summary(events=[start, end]))
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)

        self.assertIn("session_start_apply_status_missing", report["blockers"])
        self.assertIn("session_end_correlation_status_missing", report["blockers"])
        self.assertIn("observed_event_case_not_exact_start_end_shape", report["blockers"])

    def test_rejects_raw_player_text_or_principal_ids_in_summary(self) -> None:
        payload = summary()
        module = payload["modules"]["player_principal_lifecycle"]
        module["observed_event_cases"][0]["player_name"] = "SurvivorAlice"
        module["functions"]["ShooterGameMode.HandleNewPlayer"]["details"]["principal_id"] = [
            "principal-1"
        ]

        result = self.run_checker(payload)
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)

        self.assertIn(
            "source_raw_player_identity_or_text:$.modules.player_principal_lifecycle.observed_event_cases[0].player_name",
            report["blockers"],
        )
        self.assertIn(
            "source_raw_player_identity_or_text:$.modules.player_principal_lifecycle.functions.ShooterGameMode.HandleNewPlayer.details.principal_id",
            report["blockers"],
        )
        self.assertIn("observed_event_case_keys_unexpected", report["blockers"])

    def test_rejects_summary_approved_runtime_overclaim_with_explicit_checkjoin_blocker(self) -> None:
        payload = summary()
        payload["approved_runtime_evidence_present"] = True

        result = self.run_checker(payload)
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)

        self.assertIn(
            "source_alias_overclaim:$.approved_runtime_evidence_present",
            report["blockers"],
        )
        self.assertIn(
            "missing_exact_CheckJoinInProgress_1_0_session_start_rejected",
            report["blockers"],
        )

    def test_rejects_ready_log_missing_exact_safe_end_fields(self) -> None:
        payload = ready_log_dry_run_report()
        payload["analysis"]["accepted_role_events"]["session_end"].pop("redacted_fields")

        result = self.run_checker(payload)
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)

        self.assertIn("ready_log_copy_session_end_case_missing", report["blockers"])


if __name__ == "__main__":
    unittest.main()
