#!/usr/bin/env python3
"""Tests for plan_player_principal_lifecycle_next_actions.py."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "plan_player_principal_lifecycle_next_actions.py"

EXECUTOR_SCHEMA = "obelisk.player-principal-lifecycle-runtime-window-execution.v1"
ACTIVATION_SCHEMA = "obelisk.player-principal-lifecycle-activation-preconditions.v1"
STATUS_SCHEMA = "obelisk.player-principal-lifecycle-runtime-evidence-status.v1"
NEXT_PLAN_SCHEMA = "obelisk.player-principal-lifecycle-next-action-plan.v1"
OBSERVER_LOG_SCHEMA = "obelisk.runtime-observer-log-summary.v1"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_path_binding(evidence_dir: Path, manifest: Path) -> dict:
    return {
        "schema": "obelisk.player-principal-lifecycle-command-path-binding.v1",
        "evidence_dir": str(evidence_dir),
        "inputs": [
            {
                "role": "input",
                "path": str(manifest),
                "relative_path": "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                "argv_position": 1,
                "required": True,
                "must_exist": True,
                "sha256": sha256(manifest),
            }
        ],
        "outputs": [],
        "path_hash_bound": True,
        "counts_as_approved_runtime_evidence": False,
    }


def base_false_flags() -> dict:
    return {
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_claim_allowed": False,
        "server_operations_authorized": False,
        "runtime_capture_authorized": False,
        "discord_authorized": False,
        "counts_toward_sdk": False,
        "counts_toward_v1_completion": False,
    }


def post_reboot_monitor_context() -> dict:
    return {
        "schema": "obelisk.player-principal-lifecycle-post-reboot-monitor-context.v1",
        "path": "/tmp/obelisk-test-passive-monitor-post-reboot.log",
        "path_supplied": True,
        "classification": "non_evidence_context",
        "stale_pid_safety_context_recorded": True,
        "current_passive_monitor_context_recorded": True,
        "read_by_this_report": False,
        "server_operations_authorized": False,
        "live_ops_authorized": False,
        "runtime_capture_authorized": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "sdk_progress": 0,
        "p0_progress": 0,
    }


def confirmed_beta_notice_context() -> dict:
    return {
        "schema": "obelisk.player-principal-lifecycle-confirmed-beta-notice-context.v1",
        "path": "/tmp/obelisk-test-beta-notice.confirmed.json",
        "path_supplied": True,
        "classification": "notice_action_context_only_non_evidence",
        "confirmed_notice_action_context_recorded": True,
        "completed": True,
        "standing_launch_authority_recorded": True,
        "read_by_this_report": False,
        "notice_completion_accepted_by_this_report": False,
        "activation_allowed_by_this_report": False,
        "discord_authorized": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "sdk_progress": 0,
        "p0_progress": 0,
    }


def player_presence_context() -> dict:
    return {
        "classification": "players_detected_operator_context_non_evidence",
        "known_player_counts_by_target": {"arkserver3:Genesis2:27017": 2},
        "targets_with_players_detected": ["arkserver3:Genesis2:27017"],
        "players_detected": True,
        "operator_context_only": True,
        "authorizes_runtime_capture": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
    }


def exact_triplet_bundle_route_payload() -> dict:
    return {
        "schema": "obelisk.player-principal-lifecycle-exact-triplet-bundle-route.v1",
        "status": "blocked_approved_runtime_evidence_missing",
        "route_name": "same_run_exact_copied_lifecycle_triplet_bundle",
        "current_route_blocker": "approved_runtime_evidence_missing",
        "next_action_target": "exact_copied_lifecycle_triplet_bundle",
        "first_missing_kind": "copied_lifecycle_triplet_role",
        "first_missing_role": "session_start",
        "first_missing_copied_lifecycle_event_label": "HandleNewPlayer(1,1)",
        "first_missing_runtime_evidence_path": "copied-lifecycle-triplet/HandleNewPlayer(1,1)",
        "accepted_lifecycle_event_roles": ["session_start_rejected"],
        "reported_missing_lifecycle_event_roles": ["session_start", "session_end"],
        "missing_lifecycle_event_roles": ["session_start", "session_end"],
        "missing_copied_lifecycle_event_triplet_labels": [
            "HandleNewPlayer(1,1)",
            "OnLogout matched",
        ],
        "missing_required_artifacts": [
            "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
        ],
        "fastest_missing_role_artifact_path": [
            {
                "stage": "copied_lifecycle_triplet_role",
                "role": "session_start",
                "label": "HandleNewPlayer(1,1)",
                "status": "missing",
                "counts_as_approved_runtime_evidence": False,
            },
            {
                "stage": "copied_lifecycle_triplet_role",
                "role": "session_start_rejected",
                "label": "CheckJoinInProgress(1,0)",
                "status": "accepted",
                "counts_as_approved_runtime_evidence": False,
            },
            {
                "stage": "copied_lifecycle_triplet_role",
                "role": "session_end",
                "label": "OnLogout matched",
                "status": "missing",
                "counts_as_approved_runtime_evidence": False,
            },
        ],
        "partial_lifecycle_material_counts_as_approved_runtime_evidence": False,
        "copied_log_presence_counts_as_approved_runtime_evidence": False,
        "stale_passive_tail_counts_as_approved_runtime_evidence": False,
        "direct_discord_send_counts_as_approved_runtime_evidence": False,
        "active_notice_state_counts_as_approved_runtime_evidence": False,
        "diagnostic_samples_count_as_approved_runtime_evidence": False,
        "helper_command_authorized_by_route": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "sdk_progress": 0,
        "p0_progress": 0,
    }


def observer_log_route_sample_payload() -> dict:
    return {
        "schema": OBSERVER_LOG_SCHEMA,
        "ready": False,
        "runtime_evidence_ready": False,
        "approved_runtime_evidence": False,
        "modules": {
            "player_principal_lifecycle": {
                "diagnostic_route_sample_count": 4,
                "diagnostic_route_sample_max_sequence": 4,
                "diagnostic_route_sample_limits": [500],
                "diagnostic_route_sample_budget_reached": False,
                "diagnostic_route_sample_fname_index_counts": {
                    "1845": 2,
                    "2170": 1,
                    "9999": 1,
                },
                "accepted_lifecycle_event_roles": [],
                "missing_lifecycle_event_roles": [
                    "session_start",
                    "session_start_rejected",
                    "session_end",
                ],
                "approved_runtime_evidence": False,
                "runtime_ready": False,
                "public_sdk_ready": False,
            }
        },
    }


def executor_payload() -> dict:
    return {
        "schema": EXECUTOR_SCHEMA,
        "status": "offline_preactivation_prepared_notice_send_pending",
        "run_id": "20260606T100000Z-player-principal-lifecycle",
        "approved_window": {
            "start_utc": "2026-06-06T10:00:00Z",
            "end_utc": "2026-06-06T10:15:00Z",
            "duration_seconds": 900,
        },
        "target": {"instance": "arkserver3", "map": "Genesis2"},
        "next_blocker": "approved_dry_run_checked_beta_testers_notice_sent",
        "external_execution_authority": {
            "standing_launch_authority_recorded": True,
            "separate_operator_authorization_required": False,
        },
        "next_action_sequence": [
            {
                "order": 1,
                "id": "review_offline_outputs",
                "owner": "lead",
                "status": "manual_external_not_executed_by_executor",
                "action": "Review the request pack and dry-run notice.",
                "authority_source": "recorded_standing_launch_authority",
                "separate_operator_authorization_required": False,
            },
            {
                "order": 2,
                "id": "send_guarded_beta_notice_with_recorded_standing_authority",
                "owner": "lead",
                "status": "manual_external_not_executed_by_executor",
                "action": "Send the guarded beta notice with the recorded standing authority.",
                "authority_source": "recorded_standing_launch_authority",
                "separate_operator_authorization_required": False,
            },
        ],
        **base_false_flags(),
    }


def no_users_executor_payload() -> dict:
    payload = executor_payload()
    diagnostic_candidates = {
        "mode": "candidate_only_non_evidence",
        "requested_by_executor": True,
        "enabled_in_request_pack": False,
        "recommended_for_next_player_backed_window": True,
        "should_enable_in_next_request_pack": True,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
    }
    passive_wait = {
        "schema": "obelisk.player-principal-lifecycle-no-users-passive-wait-recommendation.v1",
        "status": "no_users_passive_wait_recommended",
        "no_users_detected": True,
        "passive_wait_preferred": True,
        "process_control": "passive_wait_without_restart",
        "repeated_restart_for_no_users_forbidden": True,
        "restart_recommended": False,
        "start_or_restart_recommended": False,
        "monitor_command_not_executed": (
            "scripts/monitor_ark_player_presence_passive.sh --once --no-details arkserver3:Genesis2"
        ),
        "diagnostic_candidates": diagnostic_candidates,
        "counts_as_approved_runtime_evidence": False,
    }
    next_window = {
        "schema": "obelisk.player-principal-lifecycle-next-player-backed-window-preparation.v1",
        "status": "prepare_next_player_backed_diagnostic_window_without_restart",
        "restart_expectation": "none",
        "diagnostic_candidates": diagnostic_candidates,
        "diagnostic_candidates_recommended": True,
        "should_enable_diagnostic_candidates_in_next_request_pack": True,
        "repeated_restart_for_no_users_forbidden": True,
        "start_or_restart_recommended": False,
        "command_text_not_executed": (
            "python3 scripts/prepare_player_principal_lifecycle_runtime_window_execution.py "
            "--instance arkserver3 --map Genesis2 --restart-expectation none "
            "--diagnostic-candidates --json"
        ),
        "server_operations_authorized": False,
        "counts_as_approved_runtime_evidence": False,
    }
    payload["status"] = "post_window_state_consumed_non_evidence"
    payload["next_blocker"] = "no_users_passive_wait_for_player_backed_evidence"
    payload["next_action_sequence"] = [
        {
            "order": 1,
            "id": "continue_no_users_passive_wait_for_player_backed_evidence",
            "owner": "lead",
            "status": "manual_external_not_executed_by_executor",
            "action": "continue_no_users_passive_wait_for_player_backed_evidence",
            "action_kind": "no_users_passive_wait",
            "target": {"instance": "arkserver3", "map": "Genesis2"},
            "no_users_passive_wait": passive_wait,
            "diagnostic_candidates": diagnostic_candidates,
            "command_text_not_executed": passive_wait["monitor_command_not_executed"],
            "process_control": "passive_wait_without_restart",
            "passive_wait_preferred": True,
            "repeated_restart_for_no_users_forbidden": True,
            "restart_recommended": False,
            "start_or_restart_recommended": False,
            "authorized_by_this_report": False,
            "counts_as_approved_runtime_evidence": False,
        },
        {
            "order": 2,
            "id": "prepare_next_player_backed_diagnostic_window_without_restart",
            "owner": "lead",
            "status": "manual_external_not_executed_by_executor",
            "action": "prepare_next_player_backed_diagnostic_window_without_restart",
            "action_kind": "offline_next_window_preparation",
            "target": {"instance": "arkserver3", "map": "Genesis2"},
            "next_player_backed_window": next_window,
            "diagnostic_candidates": diagnostic_candidates,
            "command_text_not_executed": next_window["command_text_not_executed"],
            "restart_expectation": "none",
            "diagnostic_candidates_recommended": True,
            "should_enable_diagnostic_candidates_in_next_request_pack": True,
            "repeated_restart_for_no_users_forbidden": True,
            "start_or_restart_recommended": False,
            "authorized_by_this_report": False,
            "counts_as_approved_runtime_evidence": False,
        },
    ]
    return payload


def activation_payload() -> dict:
    return {
        "schema": ACTIVATION_SCHEMA,
        "ready": True,
        "run_id": "20260606T100000Z-player-principal-lifecycle",
        "approved_window": {
            "start_utc": "2026-06-06T10:00:00Z",
            "end_utc": "2026-06-06T10:15:00Z",
            "duration_seconds": 900,
        },
        "target": {"instance": "arkserver3", "map": "Genesis2"},
        "next_blocker": "runtime_window_activation_ready_under_recorded_standing_launch_authority",
        "standing_launch_authority_recorded": True,
        "activation_next_action_sequence": [
            {
                "order": 1,
                "id": "safe_restart_warn_or_reschedule",
                "owner": "lead",
                "status": "manual_external_not_executed_by_checker",
                "action": "Check players and warn before restart if required.",
                "authority_source": "recorded_standing_launch_authority",
                "separate_operator_authorization_required": False,
            },
            {
                "order": 2,
                "id": "active_observation_window",
                "owner": "lead",
                "status": "manual_external_not_executed_by_checker",
                "action": "Run the exact player-principal lifecycle observer window.",
                "authority_source": "recorded_standing_launch_authority",
                "separate_operator_authorization_required": False,
            },
        ],
        **base_false_flags(),
    }


def status_payload() -> dict:
    monitor_context = post_reboot_monitor_context()
    notice_context = confirmed_beta_notice_context()
    return {
        "schema": STATUS_SCHEMA,
        "status": "blocked_missing_lifecycle_roles",
        "ready": False,
        "post_reboot_passive_monitor": {
            "present": True,
            "source_path": monitor_context["path"],
            "monitor_latest_tick_utc": "2026-06-06T10:00:00Z",
            "operator_context_only": True,
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
        },
        "confirmed_beta_notice": {
            "present": True,
            "source_path": notice_context["path"],
            "completed": True,
            "standing_launch_authority_recorded": True,
            "operator_context_only": True,
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
        },
        "machine_next_actions_schema": "obelisk.player-principal-lifecycle-runtime-evidence-status-machine-next-actions.v1",
        "machine_next_actions": [
            {
                "action": "continue_or_request_passive_wait_for_missing_lifecycle_role",
                "action_id": "closure.missing:lifecycle-role_session_start",
                "artifact": "lifecycle-role/session_start",
                "items": ["lifecycle-role/session_start"],
                "role": "session_start",
                "source": "closure_request.exact_missing_operations",
                "status_report_source": "closure.machine_next_actions",
                "requires_operator_authority_before_execution": True,
                "operator_authority_source_required": "standing_launch_authority",
                "requires_current_turn_operator_approval": False,
                "requires_fresh_current_turn_operator_approval": False,
                "requires_bound_standing_launch_authority_receipt_before_execution": True,
                "standing_launch_authority_covers_target_run": True,
                "standing_launch_authority_satisfies_operator_approval": True,
                "authorized_by_this_report": False,
                "counts_as_approved_runtime_evidence": False,
                "post_reboot_monitor_context": monitor_context,
                "confirmed_beta_notice_context": notice_context,
            },
            {
                "action": "provide_completed_window_manifest_env_sibling",
                "action_id": "closure.missing:window-manifest.env",
                "artifact": "window-manifest.env",
                "evidence_dir": "/tmp/obelisk-test-player-principal-lifecycle",
                "items": ["window-manifest.env"],
                "source": "closure_request.exact_missing_operations",
                "status_report_source": "closure.machine_next_actions",
                "requires_operator_authority_before_execution": True,
                "operator_authority_source_required": "standing_launch_authority",
                "requires_current_turn_operator_approval": False,
                "requires_fresh_current_turn_operator_approval": False,
                "requires_bound_standing_launch_authority_receipt_before_execution": True,
                "standing_launch_authority_covers_target_run": True,
                "standing_launch_authority_satisfies_operator_approval": True,
                "authorized_by_this_report": False,
                "counts_as_approved_runtime_evidence": False,
                "post_reboot_monitor_context": monitor_context,
                "confirmed_beta_notice_context": notice_context,
            },
        ],
        "operator_action_summary": {
            "run_id": "20260606T100000Z-player-principal-lifecycle",
            "recorded_standing_debug_authority": {
                "recorded": True,
                "authorized_by_this_report": False,
                "counts_as_approved_runtime_evidence": False,
            },
            "actions_allowed_under_recorded_standing_debug_authority": [
                {
                    "action": "continue_exact_player_principal_lifecycle_runtime_observation_for_missing_roles",
                    "items": ["session_start", "session_start_rejected", "session_end"],
                    "allowed_under_recorded_standing_debug_authority": True,
                    "authorized_by_this_report": False,
                    "counts_as_approved_runtime_evidence": False,
                }
            ],
        },
        "next_actions": [
            {
                "action": "wait_for_or_capture_missing_lifecycle_roles",
                "items": ["session_start"],
                "authorized_by_this_report": False,
            }
        ],
        **base_false_flags(),
    }


def runtime_window_lifecycle_action(*, expired: bool) -> dict:
    lifecycle = {
        "schema": "obelisk.player-principal-lifecycle-runtime-window-lifecycle.v1",
        "classification": (
            "expired_runtime_window_non_evidence_prepare_fresh_player_backed_window"
            if expired
            else "active_runtime_window_waiting_for_exact_copied_triplet_or_window_end"
        ),
        "window_state": "post_window" if expired else "in_progress",
        "expired_runtime_window": expired,
        "active_runtime_window": not expired,
        "non_evidence_only_material": True,
        "observer_gate_only": True,
        "exact_copied_lifecycle_event_triplet_complete": False,
        "close_or_classify_as_non_evidence": expired,
        "active_waiting_not_closure_ready": not expired,
        "copy_bundle_commands_suppressed_until_exact_triplet": True,
        "fresh_player_backed_window_required": expired,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
    }
    fresh_window = {
        "schema": "obelisk.player-principal-lifecycle-fresh-player-backed-window-prep.v1",
        "status": "fresh_player_backed_window_required_after_non_evidence_close",
        "diagnostic_candidates": "disabled",
        "requires_separate_current_turn_operator_scope": True,
        "runner_command_available": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
    }
    return {
        "action_id": (
            "status.next_action:close_expired_player_principal_lifecycle_window_as_non_evidence"
            if expired
            else "status.next_action:wait_for_active_player_principal_lifecycle_window_exact_triplet_or_end"
        ),
        "action": (
            "close_expired_player_principal_lifecycle_window_as_non_evidence"
            if expired
            else "wait_for_active_player_principal_lifecycle_window_exact_triplet_or_end"
        ),
        "action_kind": (
            "expired_runtime_window_non_evidence_closure"
            if expired
            else "active_runtime_window_waiting_for_exact_triplet"
        ),
        "status_report_source": "status.next_actions",
        "command_status": "NOT PROVIDED",
        "runtime_window_lifecycle": lifecycle,
        "fresh_player_backed_window": fresh_window,
        "next_player_backed_window": fresh_window,
        "expired_runtime_window_non_evidence": expired,
        "active_runtime_window_waiting_for_exact_triplet": not expired,
        "active_window_not_closure_ready": not expired,
        "prepare_fresh_player_backed_window_required": expired,
        "copy_bundle_commands_suppressed_until_exact_triplet": True,
        "copy_bundle_commands_allowed_before_exact_triplet": False,
        "exact_accepted_triplet_required_before_copy_bundle": True,
        "runner_command_available": False,
        "authorized_by_this_report": False,
        "counts_as_approved_runtime_evidence": False,
    }


def run_script(*args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class PlanPlayerPrincipalLifecycleNextActionsTests(unittest.TestCase):
    def test_preserves_structured_checker_runner_command_from_status_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = root / "status.json"
            manifest = root / "run" / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"schema":"fixture"}\n', encoding="utf-8")
            payload = status_payload()
            payload["status"] = "closure_inputs_complete_bundle_checker_required"
            payload["machine_next_actions"] = [
                {
                    "action_id": "status.checker:approved_runtime_principal_lifecycle_evidence",
                    "action": "run_approved_runtime_evidence_checker_on_copied_manifest",
                    "action_kind": "checker",
                    "artifact": "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                    "manifest_path": str(manifest),
                    "items": ["approved-bundle/approved-runtime-principal-lifecycle-evidence.json"],
                    "command_status": "NOT EXECUTED",
                    "command_text_not_executed": (
                        "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py "
                        f"{manifest} --json"
                    ),
                    "runner_command_available": True,
                    "runner_command": {
                        "argv": [
                            "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
                            str(manifest),
                            "--json",
                        ],
                        "execution_mode": "no_shell_offline_helper",
                    },
                    "command_path_binding": command_path_binding(manifest.parents[1], manifest),
                    "command_path_hash_bound": True,
                    "machine_executable": True,
                    "writes_under_evidence_dir": False,
                    "accepted_checker_required_before_status_claim": True,
                    "exact_copied_lifecycle_event_triplet_required_before_actionable": True,
                    "exact_copied_lifecycle_event_triplet_matched": True,
                    "authorized_by_this_report": False,
                    "counts_as_approved_runtime_evidence": False,
                }
            ]
            write_json(status, payload)
            expected_manifest_sha = sha256(manifest)
            expected_status_sha = sha256(status)

            result = run_script("--source-json", str(status), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        action = report["next_action_sequence"][0]
        self.assertEqual(action["action"], "run_approved_runtime_evidence_checker_on_copied_manifest")
        self.assertEqual(
            action["runner_command"]["argv"],
            [
                "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
                str(manifest),
                "--json",
            ],
        )
        self.assertEqual(action["command_path_binding"]["inputs"][0]["sha256"], expected_manifest_sha)
        self.assertEqual(action["source_json_sha256"], expected_status_sha)
        self.assertEqual(action["source"]["sha256"], expected_status_sha)
        self.assertTrue(action["command_path_hash_bound"])
        self.assertTrue(action["runner_command_available"])
        self.assertFalse(action["authorized_by_this_report"])
        self.assertFalse(action["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence"])

    def test_preserves_runtime_artifact_blocker_metadata_from_status_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = root / "status.json"
            payload = status_payload()
            blocker = {
                "artifact": "preflight-post.json",
                "reason": "preflight_post_json_missing",
                "action": "capture_post_window_stable_preflight_json",
                "required_script": "scripts/check_player_principal_lifecycle_preflight.sh",
                "runner_command_available": False,
                "counts_as_approved_runtime_evidence": False,
            }
            payload["machine_next_actions"] = [
                {
                    "action_id": "status.missing:preflight-post.json",
                    "action": "capture_post_window_stable_preflight_json",
                    "action_kind": "missing_artifact",
                    "artifact": "preflight-post.json",
                    "items": ["preflight-post.json"],
                    "missing_artifact_blocker": blocker,
                    "missing_artifact_blocker_reason": "preflight_post_json_missing",
                    "missing_artifact_reasons": ["preflight_post_json_missing"],
                    "required_script": "scripts/check_player_principal_lifecycle_preflight.sh",
                    "runtime_evidence_artifact_blockers": {
                        "schema": "obelisk.player-principal-lifecycle-runtime-evidence-artifact-blockers.v1",
                        "first_missing_artifact": "preflight-post.json",
                        "first_blocker_reason": "preflight_post_json_missing",
                        "missing_artifact_blockers": [blocker],
                        "missing_artifact_reasons": ["preflight_post_json_missing"],
                        "approved_runtime_evidence": False,
                    },
                    "authorized_by_this_report": False,
                    "counts_as_approved_runtime_evidence": False,
                }
            ]
            write_json(status, payload)

            result = run_script("--source-json", str(status), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        action = report["next_action_sequence"][0]
        self.assertEqual(action["missing_artifact_blocker_reason"], "preflight_post_json_missing")
        self.assertEqual(action["required_script"], "scripts/check_player_principal_lifecycle_preflight.sh")
        self.assertEqual(action["missing_artifact_blocker"]["artifact"], "preflight-post.json")
        summary = report["runtime_evidence_artifact_plan_summary"]
        self.assertEqual(summary["first_missing_artifact"], "preflight-post.json")
        self.assertEqual(summary["first_blocker_reason"], "preflight_post_json_missing")
        self.assertFalse(summary["approved_runtime_evidence"])
        self.assertFalse(action["counts_as_approved_runtime_evidence"])

    def test_merges_executor_activation_and_status_actions_without_claiming_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executor = root / "executor.json"
            activation = root / "activation.json"
            status = root / "status.json"
            write_json(executor, executor_payload())
            write_json(activation, activation_payload())
            write_json(status, status_payload())

            result = run_script(
                "--source-json",
                str(executor),
                "--source-json",
                str(activation),
                "--source-json",
                str(status),
                "--json",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["schema"], NEXT_PLAN_SCHEMA)
        self.assertEqual(report["status"], "next_actions_planned")
        self.assertFalse(report["ready"])
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["server_operations_authorized"])
        route_audit = report["route_audit"]
        self.assertEqual(
            route_audit["schema"],
            "obelisk.player-principal-lifecycle-offline-route-audit.v1",
        )
        self.assertEqual(route_audit["current_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(
            route_audit["current_source_bound_route_blocker"],
            "source_bound_drift_blocks_accepted_lifecycle_events",
        )
        self.assertTrue(route_audit["source_bound_drift_blocker_is_primary_route"])
        self.assertFalse(route_audit["waiting_for_exact_check_join_in_progress_1_0_is_fastest_valid_route"])
        self.assertFalse(route_audit["blind_wait_or_restart_or_logout_instruction_allowed"])
        self.assertIn("resolve or source-bind", route_audit["recommended_next_action"])
        self.assertTrue(route_audit["clean_theisland_non_diagnostic_window_is_candidate_only_next_action"])
        self.assertTrue(route_audit["diagnostic_candidates_should_be_disabled_for_fastest_candidate"])
        current_blockers = route_audit["current_live_diagnostic_blockers"]
        self.assertEqual(
            current_blockers["classification"],
            "source_bound_drift_blockers_non_evidence",
        )
        self.assertEqual(current_blockers["source_freshness"], "stale_operator_supplied")
        self.assertTrue(current_blockers["stale_operator_supplied_context"])
        self.assertTrue(current_blockers["stale_operator_supplied_blockers_suppressed"])
        self.assertEqual(
            current_blockers["stale_operator_supplied_next_blocker_ids"],
            current_blockers["next_blocker_ids"],
        )
        self.assertTrue(current_blockers["source_bound_blocker"])
        self.assertFalse(current_blockers["blind_wait_recommended"])
        self.assertFalse(current_blockers["restart_recommended"])
        self.assertFalse(current_blockers["wait_or_restart_or_logout_instruction_allowed"])
        self.assertFalse(current_blockers["logout_or_reconnect_instruction_allowed"])
        candidate_action = route_audit["candidate_only_next_action"]
        self.assertEqual(candidate_action["id"], "clean_theisland_fresh_window_without_diagnostics")
        self.assertEqual(candidate_action["status"], "candidate_only_non_evidence")
        self.assertEqual(candidate_action["target_hint"], {"instance": "arkserver2", "map": "TheIsland"})
        self.assertEqual(candidate_action["diagnostic_candidates"], "disabled")
        self.assertTrue(candidate_action["blocked_by_current_source_bound_drift_context"])
        self.assertFalse(candidate_action["blind_wait_or_restart_or_logout_instruction_allowed"])
        self.assertTrue(candidate_action["beta_runtime_choreography"]["single_tester_only"])
        self.assertTrue(candidate_action["beta_runtime_choreography"]["direct_target_join_required"])
        self.assertFalse(candidate_action["beta_runtime_choreography"]["blind_wait_instruction"])
        self.assertFalse(candidate_action["beta_runtime_choreography"]["logout_instruction_allowed_now"])
        self.assertTrue(
            candidate_action["beta_runtime_choreography"]["observer_gate"][
                "wait_until_observer_sees_exact_checkjoin_or_window_closes"
            ]
        )
        self.assertFalse(
            candidate_action["beta_runtime_choreography"][
                "mixed_transfer_reconnect_same_approved_window_allowed"
            ]
        )
        self.assertFalse(candidate_action["authorized_by_this_report"])
        self.assertFalse(candidate_action["counts_as_approved_runtime_evidence"])
        runtime_gap = route_audit["latest_runtime_gap_from_logs"]
        self.assertEqual(runtime_gap["status"], "blocked_no_approved_runtime_evidence")
        self.assertTrue(runtime_gap["planner_did_not_read_live_logs"])
        self.assertEqual(
            [observation["id"] for observation in runtime_gap["observations"]],
            [
                "theisland_active_player_observer_only_no_accepted_lifecycle_event",
                "ragnarok_diagnostic_fname_drift_blocks_accepted_events",
                "theisland_clean_window_start_end_only_missing_checkjoin",
                "ragnarok_diagnostic_tail_exact_checkjoin_1_0_stimulus_only",
                "stale_or_order_mismatched_exact_checkjoin_1_0_stimulus_only",
                "ragnarok_fresh_window_diagnostics_checkjoin_0_0",
            ],
        )
        self.assertIn(
            "stale/order-mismatched exact CheckJoinInProgress(1,0) can be reused",
            runtime_gap["rejected_hypotheses"],
        )
        self.assertIn(
            "diagnostic/non-promotable Ragnarok exact CheckJoinInProgress(1,0) can be promoted",
            runtime_gap["rejected_hypotheses"],
        )
        self.assertTrue(runtime_gap["stale_or_diagnostic_exact_checkjoin_boundary"]["stimulus_clue_for_future_choreography"])
        self.assertFalse(
            runtime_gap["stale_or_diagnostic_exact_checkjoin_boundary"][
                "diagnostic_tail_without_approved_sibling_set_is_promotable"
            ]
        )
        self.assertEqual(
            runtime_gap["candidate_only_fastest_hypothesis"],
            "clean_theisland_fresh_window_without_diagnostics",
        )
        self.assertFalse(runtime_gap["counts_as_approved_runtime_evidence"])
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
        self.assertFalse(route_audit["one_tester_direct_join_wait_for_exact_checkjoin_required"])
        self.assertTrue(
            route_audit[
                "one_tester_direct_join_wait_for_exact_checkjoin_candidate_only_after_blocker_clear"
            ]
        )
        self.assertFalse(route_audit["mixed_transfer_reconnect_same_approved_window_allowed"])
        self.assertTrue(route_audit["stale_or_diagnostic_exact_checkjoin_lines_are_stimulus_clues_only"])
        self.assertFalse(route_audit["counts_as_approved_runtime_evidence"])
        self.assertTrue(report["beta_runtime_choreography"]["single_tester_only"])
        self.assertTrue(report["beta_runtime_choreography"]["direct_target_join_required"])
        self.assertFalse(report["beta_runtime_choreography"]["logout_before_exact_checkjoin_allowed"])
        self.assertTrue(
            report["beta_runtime_choreography"][
                "source_bound_blockers_must_be_clear_before_choreography"
            ]
        )
        self.assertFalse(report["beta_runtime_choreography"]["blind_wait_instruction"])
        self.assertFalse(report["beta_runtime_choreography"]["logout_instruction_allowed_now"])
        self.assertFalse(
            report["beta_runtime_choreography"][
                "mixed_transfer_reconnect_same_approved_window_allowed"
            ]
        )
        self.assertFalse(report["beta_runtime_choreography"]["counts_as_approved_runtime_evidence"])
        self.assertEqual(report["source_count"], 3)
        self.assertEqual(report["action_count"], 6)
        self.assertEqual(
            report["stale_or_too_late_action_ids"],
            [
                "send_guarded_beta_notice_with_recorded_standing_authority",
                "safe_restart_warn_or_reschedule",
                "active_observation_window",
            ],
        )
        self.assertFalse(
            report["runtime_window_stale_prevention_summary"][
                "activation_or_restart_from_stale_request_allowed"
            ]
        )
        self.assertEqual(
            [action["id"] for action in report["next_action_sequence"]],
            [
                "review_offline_outputs",
                "send_guarded_beta_notice_with_recorded_standing_authority",
                "safe_restart_warn_or_reschedule",
                "active_observation_window",
                "closure_missing_lifecycle_role_session_start",
                "closure_missing_window_manifest_env",
            ],
        )
        self.assertEqual(report["sources"][2]["action_key"], "machine_next_actions")
        self.assertTrue(report["sources"][2]["operator_context"]["post_reboot_monitor_context_present"])
        self.assertTrue(report["sources"][2]["operator_context"]["confirmed_beta_notice_context_present"])
        self.assertEqual(
            report["next_action_sequence"][5]["evidence_dir"],
            "/tmp/obelisk-test-player-principal-lifecycle",
        )
        self.assertTrue(report["operator_context_summary"]["post_reboot_monitor_context_present"])
        self.assertEqual(
            report["operator_context_summary"]["post_reboot_monitor_paths"],
            ["/tmp/obelisk-test-passive-monitor-post-reboot.log"],
        )
        self.assertTrue(report["operator_context_summary"]["confirmed_beta_notice_context_present"])
        self.assertEqual(
            report["operator_context_summary"]["confirmed_beta_notice_paths"],
            ["/tmp/obelisk-test-beta-notice.confirmed.json"],
        )
        self.assertTrue(report["operator_context_summary"]["confirmed_beta_notice_completed"])
        self.assertFalse(report["operator_context_summary"]["context_inputs_authorize_runner"])
        self.assertFalse(report["operator_context_summary"]["approved_runtime_evidence"])
        self.assertFalse(report["operator_context_summary"]["counts_as_approved_runtime_evidence"])
        self.assertTrue(report["action_plan"]["recorded_standing_authority_observed"])
        self.assertTrue(report["action_plan"]["external_actions_may_use_recorded_authority_for_exact_scope"])
        self.assertGreater(report["action_plan"]["external_action_count_with_exact_standing_scope"], 0)
        self.assertEqual(
            report["action_plan"]["stale_or_too_late_action_ids"],
            report["stale_or_too_late_action_ids"],
        )
        self.assertFalse(report["action_plan"]["activation_or_restart_from_stale_request_allowed"])
        self.assertFalse(report["action_plan"]["authorized_by_this_report"])
        self.assertFalse(report["action_plan"]["server_operations_authorized_by_this_report"])
        self.assertFalse(report["action_plan"]["counts_as_approved_runtime_evidence"])
        self.assertEqual(report["action_plan"]["route_audit"], route_audit)
        stale_by_id = {
            action["id"]: action
            for action in report["next_action_sequence"]
            if action["id"] in report["stale_or_too_late_action_ids"]
        }
        self.assertTrue(
            all(action["separate_operator_authorization_required"] for action in stale_by_id.values())
        )
        self.assertTrue(all(action["runtime_window_stale_or_too_late"] for action in stale_by_id.values()))
        self.assertTrue(
            all(
                "runtime_window_start_already_passed_prepare_fresh_window"
                in action["runtime_window_stale_blockers"]
                for action in stale_by_id.values()
            )
        )
        self.assertTrue(
            all(not action["allowed_under_recorded_standing_authority"] for action in stale_by_id.values())
        )
        self.assertFalse(
            stale_by_id["safe_restart_warn_or_reschedule"][
                "activation_or_restart_from_stale_request_allowed"
            ]
        )
        self.assertTrue(
            all(not action["authorized_by_this_report"] for action in report["next_action_sequence"])
        )
        self.assertEqual(report["next_action_sequence"][4]["items"], ["lifecycle-role/session_start"])
        role_action = report["next_action_sequence"][4]
        self.assertEqual(
            role_action["post_reboot_monitor_context"]["path"],
            "/tmp/obelisk-test-passive-monitor-post-reboot.log",
        )
        self.assertEqual(
            role_action["confirmed_beta_notice_context"]["path"],
            "/tmp/obelisk-test-beta-notice.confirmed.json",
        )
        self.assertTrue(role_action["operator_context"]["confirmed_beta_notice_completed"])
        self.assertTrue(role_action["standing_authority_scope_represented_for_action"])
        self.assertTrue(role_action["allowed_operator_context_under_recorded_standing_authority"])
        self.assertTrue(role_action["allowed_under_recorded_standing_authority"])
        self.assertFalse(role_action["standing_authority_authorizes_this_plan"])
        self.assertFalse(role_action["operator_context"]["context_inputs_authorize_runner"])
        self.assertFalse(role_action["operator_context"]["approved_runtime_evidence"])
        self.assertFalse(role_action["counts_as_approved_runtime_evidence"])
        self.assertTrue(role_action["beta_runtime_choreography"]["single_tester_only"])
        self.assertFalse(
            role_action["beta_runtime_choreography"][
                "logout_or_cluster_transfer_or_reconnect_before_exact_checkjoin_allowed"
            ]
        )

    def test_run_id_without_explicit_approved_window_blocks_as_missing_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            activation = root / "activation.json"
            payload = activation_payload()
            payload.pop("approved_window")
            write_json(activation, payload)

            result = run_script("--source-json", str(activation), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            report["stale_or_too_late_action_ids"],
            ["safe_restart_warn_or_reschedule", "active_observation_window"],
        )
        self.assertFalse(
            report["runtime_window_stale_prevention_summary"][
                "activation_or_restart_from_stale_request_allowed"
            ]
        )
        stale_actions = [
            action
            for action in report["next_action_sequence"]
            if action["id"] in report["stale_or_too_late_action_ids"]
        ]
        self.assertTrue(
            all(
                "runtime_window_approved_window_missing_for_action"
                in action.get("runtime_window_stale_blockers", [])
                for action in stale_actions
            )
        )
        self.assertTrue(
            all(
                "runtime_window_start_already_passed_prepare_fresh_window"
                not in action.get("runtime_window_stale_blockers", [])
                for action in stale_actions
            )
        )
    def test_source_standing_authority_does_not_override_action_fresh_scope_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = root / "status.json"
            payload = status_payload()
            source_dir = "/tmp/20260607T071833Z-postpatch-ragnarok-theisland-monitor"
            closure_dir = "/tmp/20260607T071833Z-player-principal-lifecycle"
            guidance = {
                "schema": "obelisk.player-principal-lifecycle-closure-compatible-copy-guidance.v1",
                "source_evidence_dir": source_dir,
                "source_root_role": "source_evidence_root_supplied_to_closure_helper",
                "source_run_id": "20260607T071833Z-postpatch-ragnarok-theisland-monitor",
                "source_looks_like_passive_monitor_root": True,
                "suggested_valid_closure_run_id": "20260607T071833Z-player-principal-lifecycle",
                "suggested_valid_closure_evidence_dir": closure_dir,
                "suggested_valid_closure_root_role": "suggested_valid_closure_root_for_manual_staging",
                "passive_monitor_root_accepted_as_closure_evidence_dir": False,
                "counts_as_approved_runtime_evidence": False,
            }
            payload["machine_next_actions"] = [
                {
                    "action": "stage_closure_compatible_player_principal_lifecycle_evidence_root",
                    "action_id": "closure.missing:invalid_source",
                    "action_kind": "invalid_evidence_source",
                    "missing_kind": "invalid_evidence_source",
                    "artifact": source_dir,
                    "items": [source_dir],
                    "source_evidence_dir": source_dir,
                    "invalid_source_evidence_dir": source_dir,
                    "source_root_role": "source_evidence_root_supplied_to_closure_helper",
                    "source_run_id": "20260607T071833Z-postpatch-ragnarok-theisland-monitor",
                    "source_root_valid_for_closure": False,
                    "source_looks_like_passive_monitor_root": True,
                    "closure_compatible_evidence_dir": closure_dir,
                    "suggested_valid_closure_run_id": "20260607T071833Z-player-principal-lifecycle",
                    "suggested_valid_closure_evidence_dir": closure_dir,
                    "suggested_valid_closure_root_role": "suggested_valid_closure_root_for_manual_staging",
                    "closure_compatible_copy_guidance": guidance,
                    "command_status": "NOT PROVIDED",
                    "command_text_not_emitted": "manual staging required before rerun",
                    "manual_offline_next_steps": [
                        "do not use the passive monitor root as --evidence-dir for closure",
                        "stage a valid player-principal lifecycle closure root",
                    ],
                    "requires_operator_authority_before_execution": True,
                    "operator_authority_source_required": "fresh_current_turn_operator_message",
                    "requires_current_turn_operator_approval": True,
                    "requires_fresh_current_turn_operator_approval": True,
                    "standing_launch_authority_covers_target_run": False,
                    "copy_or_stage_into_closure_compatible_run_required_before_closure": True,
                    "explicit_execution_write_flags_required": True,
                    "machine_action_suggested_for_invalid_passive_root": False,
                    "machine_executable": False,
                    "runner_command_available": False,
                    "manual_staging_required_before_machine_actions": True,
                    "authorized_by_this_report": False,
                    "counts_as_approved_runtime_evidence": False,
                }
            ]
            write_json(status, payload)

            result = run_script("--source-json", str(status), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        action = report["next_action_sequence"][0]
        self.assertTrue(action["recorded_standing_authority_observed"])
        self.assertFalse(action["standing_authority_scope_represented_for_action"])
        self.assertFalse(action["allowed_operator_context_under_recorded_standing_authority"])
        self.assertFalse(action["allowed_under_recorded_standing_authority"])
        self.assertTrue(action["standing_authority_fresh_message_still_required_for_action"])
        self.assertTrue(action["separate_operator_authorization_required"])
        self.assertEqual(action["operator_authority_source_required"], "fresh_current_turn_operator_message")
        self.assertEqual(action["source_evidence_dir"], source_dir)
        self.assertEqual(action["invalid_source_evidence_dir"], source_dir)
        self.assertEqual(action["source_root_role"], "source_evidence_root_supplied_to_closure_helper")
        self.assertFalse(action["source_root_valid_for_closure"])
        self.assertTrue(action["source_looks_like_passive_monitor_root"])
        self.assertEqual(action["suggested_valid_closure_evidence_dir"], closure_dir)
        self.assertEqual(
            action["suggested_valid_closure_root_role"],
            "suggested_valid_closure_root_for_manual_staging",
        )
        self.assertFalse(action["machine_action_suggested_for_invalid_passive_root"])
        self.assertFalse(action["machine_executable"])
        self.assertFalse(action["runner_command_available"])
        self.assertTrue(action["manual_staging_required_before_machine_actions"])
        self.assertNotIn("command_text_not_executed", action)
        self.assertEqual(action["manual_offline_next_steps"][0], "do not use the passive monitor root as --evidence-dir for closure")
        self.assertFalse(report["action_plan"]["external_actions_may_use_recorded_authority_for_exact_scope"])
        self.assertFalse(action["counts_as_approved_runtime_evidence"])
        self.assertEqual(report["sdk_progress"], 0)
        self.assertEqual(report["p0_progress"], 0)
        self.assertEqual(action["sdk_progress"], 0)
        self.assertFalse(action["standing_authority_counts_toward_sdk"])

    def test_closure_style_confirmed_notice_context_is_completed_but_non_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = root / "status.json"
            payload = status_payload()
            closure_notice_context = {
                "schema": "obelisk.player-principal-lifecycle-confirmed-beta-notice-context.v1",
                "path": "/tmp/obelisk-test-beta-notice.confirmed.json",
                "path_supplied": True,
                "classification": "notice_action_context_only_non_evidence",
                "notice_completion_accepted_by_this_report": True,
                "notice_completion_status": "confirmed_beta_notice_completed",
                "source_mode": "confirmed_send",
                "source_discord_sent": True,
                "approved_runtime_evidence": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_sdk_evidence": False,
                "counts_toward_sdk": False,
            }
            payload["confirmed_beta_notice"] = dict(closure_notice_context)
            for action in payload["machine_next_actions"]:
                action["confirmed_beta_notice_context"] = dict(closure_notice_context)
            write_json(status, payload)

            result = run_script("--source-json", str(status), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report["operator_context_summary"]["confirmed_beta_notice_completed"])
        first_action = report["next_action_sequence"][0]
        self.assertTrue(first_action["operator_context"]["confirmed_beta_notice_completed"])
        self.assertFalse(first_action["operator_context"]["context_inputs_authorize_runner"])
        self.assertFalse(first_action["operator_context"]["approved_runtime_evidence"])
        self.assertFalse(first_action["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence"])

    def test_preserves_no_users_passive_wait_and_diagnostic_candidate_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "executor-no-users.json"
            write_json(source, no_users_executor_payload())

            result = run_script("--source-json", str(source), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["action_count"], 2)
        wait_action = report["next_action_sequence"][0]
        self.assertEqual(wait_action["id"], "continue_no_users_passive_wait_for_player_backed_evidence")
        self.assertEqual(wait_action["process_control"], "passive_wait_without_restart")
        self.assertTrue(wait_action["passive_wait_preferred"])
        self.assertTrue(wait_action["repeated_restart_for_no_users_forbidden"])
        self.assertFalse(wait_action["restart_recommended"])
        self.assertTrue(wait_action["diagnostic_candidates"]["should_enable_in_next_request_pack"])
        self.assertTrue(wait_action["no_users_passive_wait"]["no_users_detected"])
        self.assertIn("monitor_ark_player_presence_passive.sh", wait_action["command_text_not_executed"])
        prep_action = report["next_action_sequence"][1]
        self.assertEqual(prep_action["restart_expectation"], "none")
        self.assertTrue(prep_action["diagnostic_candidates_recommended"])
        self.assertTrue(prep_action["should_enable_diagnostic_candidates_in_next_request_pack"])
        self.assertTrue(prep_action["next_player_backed_window"]["diagnostic_candidates_recommended"])
        self.assertIn("--diagnostic-candidates", prep_action["command_text_not_executed"])
        self.assertFalse(prep_action["start_or_restart_recommended"])
        self.assertFalse(prep_action["counts_as_approved_runtime_evidence"])
        route_audit = report["route_audit"]
        self.assertEqual(
            route_audit["candidate_only_next_action"]["id"],
            "clean_theisland_fresh_window_without_diagnostics",
        )
        self.assertEqual(route_audit["candidate_only_next_action"]["diagnostic_candidates"], "disabled")
        self.assertFalse(route_audit["candidate_only_next_action"]["counts_as_approved_runtime_evidence"])
        self.assertTrue(route_audit["diagnostic_candidates_should_be_disabled_for_fastest_candidate"])
        self.assertIn(
            "diagnostic candidate lines can substitute for accepted copied observer events",
            route_audit["latest_runtime_gap_from_logs"]["rejected_hypotheses"],
        )
        self.assertFalse(report["approved_runtime_evidence"])

    def test_plans_route_sample_review_from_observer_log_summary_as_non_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "observer-summary.json"
            write_json(source, observer_log_route_sample_payload())

            result = run_script("--source-json", str(source), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["schema"], NEXT_PLAN_SCHEMA)
        self.assertEqual(report["source_count"], 1)
        self.assertEqual(report["sources"][0]["schema"], OBSERVER_LOG_SCHEMA)
        self.assertEqual(report["action_count"], 1)
        action = report["next_action_sequence"][0]
        self.assertEqual(action["id"], "review_player_principal_lifecycle_route_samples")
        self.assertEqual(action["action_kind"], "diagnostic_route_sample_review")
        self.assertFalse(action["authorized_by_this_report"])
        self.assertFalse(action["counts_as_approved_runtime_evidence"])
        self.assertFalse(action["runtime_ready"])
        analysis = action["diagnostic_route_sample_analysis"]
        self.assertEqual(analysis["sample_count"], 4)
        self.assertEqual(
            [target["target"] for target in analysis["observed_known_lifecycle_targets"]],
            [
                "ShooterGameMode.CheckJoinInProgress",
                "ShooterGameMode.HandleNewPlayer",
            ],
        )
        self.assertEqual(analysis["unknown_fname_index_counts"], {"9999": 1})
        self.assertFalse(analysis["route_samples_are_promotable"])
        summary = report["route_sample_plan_summary"]
        self.assertTrue(summary["present"])
        self.assertEqual(summary["sample_count"], 4)
        self.assertIn(
            "ShooterGameMode.CheckJoinInProgress",
            summary["observed_known_lifecycle_target_names"],
        )
        self.assertEqual(
            report["route_audit"]["route_sample_plan_summary"],
            summary,
        )
        self.assertFalse(summary["approved_runtime_evidence"])
        self.assertEqual(report["sdk_progress"], 0)
        self.assertEqual(report["p0_progress"], 0)

    def test_preserves_player_presence_context_as_non_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = root / "status.json"
            payload = status_payload()
            presence = player_presence_context()
            payload["runtime_player_availability"] = dict(presence)
            payload["machine_next_actions"][0]["player_presence_context"] = dict(presence)
            write_json(status, payload)

            result = run_script("--source-json", str(status), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report["operator_context_summary"]["player_presence_context_present"])
        self.assertTrue(report["operator_context_summary"]["player_presence_players_detected"])
        self.assertEqual(
            report["operator_context_summary"]["player_presence_targets"],
            ["arkserver3:Genesis2:27017"],
        )
        self.assertFalse(report["operator_context_summary"]["player_presence_context_authorizes_runner"])
        self.assertFalse(
            report["operator_context_summary"][
                "player_presence_context_counts_as_approved_runtime_evidence"
            ]
        )
        first_action = report["next_action_sequence"][0]
        self.assertEqual(
            first_action["player_presence_context"]["classification"],
            "players_detected_operator_context_non_evidence",
        )
        self.assertTrue(first_action["operator_context"]["player_presence_context_present"])
        self.assertFalse(first_action["operator_context"]["player_presence_context_authorizes_runner"])
        self.assertFalse(first_action["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence"])

    def test_expired_runtime_window_non_evidence_action_is_planned_without_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = root / "status.json"
            payload = status_payload()
            payload["status"] = "blocked_expired_runtime_window_non_evidence_prepare_fresh_player_backed_window"
            payload["machine_next_actions"] = [runtime_window_lifecycle_action(expired=True)]
            write_json(status, payload)

            result = run_script("--source-json", str(status), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["action_count"], 1)
        summary = report["runtime_window_lifecycle_summary"]
        self.assertTrue(summary["present"])
        self.assertEqual(
            summary["classification"],
            "expired_non_evidence_windows_prepare_fresh_player_backed_window",
        )
        self.assertEqual(
            summary["expired_non_evidence_action_ids"],
            ["status_next_action_close_expired_player_principal_lifecycle_window_as_non_evidence"],
        )
        self.assertTrue(summary["fresh_player_backed_window_required"])
        lanes_summary = report["offline_parallel_evidence_lanes_summary"]
        self.assertTrue(lanes_summary["present"])
        self.assertIn(
            "runtime_evidence_closure_status",
            lanes_summary["lane_ids"],
        )
        self.assertIn(
            "single_player_multi_surface_candidate_pack",
            lanes_summary["lane_ids"],
        )
        self.assertFalse(lanes_summary["counts_as_approved_runtime_evidence"])
        self.assertEqual(lanes_summary["sdk_progress"], 0)
        action = report["next_action_sequence"][0]
        self.assertEqual(action["action_kind"], "expired_runtime_window_non_evidence_closure")
        self.assertTrue(action["expired_runtime_window_non_evidence"])
        self.assertTrue(action["prepare_fresh_player_backed_window_required"])
        self.assertTrue(action["copy_bundle_commands_suppressed_until_exact_triplet"])
        self.assertTrue(action["offline_parallel_evidence_lanes"]["present"])
        self.assertEqual(action["offline_parallel_evidence_lanes"]["parallel_lane_count"], 4)
        self.assertEqual(
            action["offline_parallel_evidence_lanes"]["runtime_window_state"],
            "expired_non_evidence",
        )
        for lane in action["offline_parallel_evidence_lanes"]["lanes"]:
            with self.subTest(lane=lane["id"]):
                self.assertFalse(lane["counts_as_approved_runtime_evidence"])
                self.assertFalse(lane["counts_as_runtime_evidence"])
                self.assertFalse(lane["counts_as_sdk_evidence"])
                self.assertFalse(lane["counts_toward_sdk"])
                self.assertFalse(lane["counts_toward_p0_dependency_chain"])
                self.assertFalse(lane["runtime_ready"])
                self.assertFalse(lane["public_sdk_ready"])
                self.assertFalse(lane["stable_claim_allowed"])
                self.assertEqual(lane["sdk_progress"], 0)
                self.assertEqual(lane["p0_progress"], 0)
                self.assertFalse(lane["runner_command_available"])
                self.assertTrue(lane["runner_must_not_execute_lane"])
        self.assertFalse(action["offline_parallel_evidence_lanes"]["runner_command_available"])
        self.assertFalse(action["runner_command_available"])
        self.assertNotIn("command_text_not_executed", action)
        self.assertFalse(report["approved_runtime_evidence"])

    def test_active_runtime_window_action_remains_waiting_not_closure_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = root / "status.json"
            payload = status_payload()
            payload["status"] = "blocked_active_runtime_window_waiting_for_exact_copied_triplet"
            payload["machine_next_actions"] = [runtime_window_lifecycle_action(expired=False)]
            write_json(status, payload)

            result = run_script("--source-json", str(status), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        summary = report["runtime_window_lifecycle_summary"]
        self.assertEqual(summary["classification"], "active_windows_waiting_not_closure_ready")
        self.assertEqual(
            summary["active_waiting_action_ids"],
            ["status_next_action_wait_for_active_player_principal_lifecycle_window_exact_triplet_or_end"],
        )
        self.assertTrue(summary["active_windows_remain_waiting"])
        self.assertFalse(summary["fresh_player_backed_window_required"])
        lanes_summary = report["offline_parallel_evidence_lanes_summary"]
        self.assertTrue(lanes_summary["present"])
        self.assertIn(
            "post_runtime_identity_public_contract_gate",
            lanes_summary["lane_ids"],
        )
        self.assertFalse(lanes_summary["counts_as_approved_runtime_evidence"])
        action = report["next_action_sequence"][0]
        self.assertEqual(action["action_kind"], "active_runtime_window_waiting_for_exact_triplet")
        self.assertTrue(action["active_runtime_window_waiting_for_exact_triplet"])
        self.assertTrue(action["active_window_not_closure_ready"])
        self.assertFalse(action["prepare_fresh_player_backed_window_required"])
        self.assertEqual(
            action["offline_parallel_evidence_lanes"]["runtime_window_state"],
            "active_waiting",
        )
        self.assertEqual(action["offline_parallel_evidence_lanes"]["parallel_lane_count"], 4)
        self.assertIn(
            "post_identity_p0_chain_certificates",
            [lane["id"] for lane in action["offline_parallel_evidence_lanes"]["lanes"]],
        )
        for lane in action["offline_parallel_evidence_lanes"]["lanes"]:
            with self.subTest(lane=lane["id"]):
                self.assertFalse(lane["counts_as_approved_runtime_evidence"])
                self.assertFalse(lane["counts_as_runtime_evidence"])
                self.assertFalse(lane["counts_as_sdk_evidence"])
                self.assertFalse(lane["counts_toward_sdk"])
                self.assertFalse(lane["counts_toward_p0_dependency_chain"])
                self.assertFalse(lane["runtime_ready"])
                self.assertFalse(lane["public_sdk_ready"])
                self.assertEqual(lane["sdk_progress"], 0)
                self.assertEqual(lane["p0_progress"], 0)
        self.assertFalse(action["offline_parallel_evidence_lanes"]["counts_toward_sdk"])
        self.assertNotIn("command_text_not_executed", action)
        self.assertFalse(report["approved_runtime_evidence"])

    def test_planner_preserves_partial_live_like_exact_triplet_bundle_route_non_authorizing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = root / "status.json"
            route = exact_triplet_bundle_route_payload()
            payload = status_payload()
            payload["status"] = "blocked_active_runtime_window_waiting_for_exact_copied_triplet"
            payload["exact_triplet_bundle_route"] = route
            payload["machine_next_actions"] = [
                {
                    "action_id": "status.next_action:wait_for_active_player_principal_lifecycle_window_exact_triplet_or_end",
                    "action": "wait_for_active_player_principal_lifecycle_window_exact_triplet_or_end",
                    "action_kind": "active_runtime_window_waiting_for_exact_triplet",
                    "items": ["session_start", "session_end"],
                    "role": "session_start",
                    "exact_triplet_bundle_route": route,
                    "next_action_target": "exact_copied_lifecycle_triplet_bundle",
                    "first_missing_runtime_evidence_path": "copied-lifecycle-triplet/HandleNewPlayer(1,1)",
                    "fastest_missing_role_artifact_path": route["fastest_missing_role_artifact_path"],
                    "command_status": "NOT PROVIDED",
                    "runner_command_available": False,
                    "authorized_by_this_report": False,
                    "counts_as_approved_runtime_evidence": False,
                    "partial_lifecycle_material_counts_as_approved_runtime_evidence": False,
                    "copied_log_presence_counts_as_approved_runtime_evidence": False,
                    "direct_discord_send_counts_as_approved_runtime_evidence": False,
                    "active_notice_state_counts_as_approved_runtime_evidence": False,
                    "diagnostic_samples_count_as_approved_runtime_evidence": False,
                }
            ]
            write_json(status, payload)

            result = run_script("--source-json", str(status), "--json")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        action = report["next_action_sequence"][0]
        self.assertEqual(action["next_action_target"], "exact_copied_lifecycle_triplet_bundle")
        self.assertEqual(
            action["first_missing_runtime_evidence_path"],
            "copied-lifecycle-triplet/HandleNewPlayer(1,1)",
        )
        self.assertEqual(
            action["exact_triplet_bundle_route"]["accepted_lifecycle_event_roles"],
            ["session_start_rejected"],
        )
        self.assertFalse(action["partial_lifecycle_material_counts_as_approved_runtime_evidence"])
        self.assertFalse(action["copied_log_presence_counts_as_approved_runtime_evidence"])
        self.assertFalse(action["direct_discord_send_counts_as_approved_runtime_evidence"])
        self.assertFalse(action["active_notice_state_counts_as_approved_runtime_evidence"])
        summary = report["exact_triplet_bundle_plan_summary"]
        self.assertTrue(summary["present"])
        self.assertEqual(summary["first_missing_role"], "session_start")
        self.assertEqual(
            summary["first_missing_runtime_evidence_path"],
            "copied-lifecycle-triplet/HandleNewPlayer(1,1)",
        )
        self.assertFalse(summary["planner_accepts_partial_lifecycle_material_as_evidence"])
        self.assertFalse(summary["planner_accepts_copied_log_presence_as_evidence"])
        self.assertFalse(summary["planner_accepts_direct_discord_send_as_evidence"])
        self.assertFalse(summary["planner_accepts_active_notice_state_as_evidence"])
        self.assertFalse(summary["planner_accepts_diagnostic_samples_as_evidence"])
        self.assertFalse(summary["helper_command_authorized_by_plan"])
        self.assertEqual(report["action_plan"]["exact_triplet_bundle_plan_summary"], summary)
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertEqual(report["sdk_progress"], 0)
        self.assertEqual(report["p0_progress"], 0)

    def test_json_output_dash_writes_stdout_not_root_dash_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "executor.json"
            write_json(source, executor_payload())

            result = run_script(
                "--source-json",
                str(source),
                "--json-output",
                "-",
                cwd=root,
            )
            report = json.loads(result.stdout)

            self.assertFalse((root / "-").exists())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["schema"], NEXT_PLAN_SCHEMA)
        self.assertEqual(report["action_count"], 2)

    def test_rejects_runtime_evidence_and_readiness_shortcut_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "executor-overclaim.json"
            payload = executor_payload()
            payload["approved_runtime_evidence_ready"] = True
            payload["approved_in_game_evidence_ready"] = True
            payload["runtime_evidence_ready"] = "ready"
            write_json(source, payload)

            result = run_script("--source-json", str(source), "--json")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime-evidence/readiness shortcut aliases", result.stderr)
        self.assertIn("$.approved_runtime_evidence_ready", result.stderr)
        self.assertIn("$.approved_in_game_evidence_ready", result.stderr)
        self.assertIn("$.runtime_evidence_ready", result.stderr)

    def test_rejects_unsupported_status_or_public_readiness_alias_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "public-readiness.json"
            write_json(source, {"schema": "obelisk.player-principal-public-readiness-status.v1"})

            result = run_script("--source-json", str(source), "--json")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported schema", result.stderr)


if __name__ == "__main__":
    unittest.main()
