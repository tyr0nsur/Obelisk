#!/usr/bin/env python3
"""Tests for prepare_player_principal_lifecycle_runtime_window_execution.py."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from prepare_player_principal_lifecycle_window_request import (
    SESSION_START_REJECTED_REQUIRED_ARGUMENTS,
    SESSION_START_REJECTED_REQUIRED_CALL,
    SESSION_START_REJECTED_REQUIRED_FUNCTION,
)


REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "prepare_player_principal_lifecycle_runtime_window_execution.py"
BETA_NOTICE = SCRIPT_DIR / "prepare_player_principal_lifecycle_beta_notice.py"
TEST_COMMIT = subprocess.check_output(
    ["git", "rev-parse", "HEAD"],
    cwd=REPO_ROOT,
    text=True,
).strip()
CLOSURE_SCHEMA = "obelisk.player-principal-lifecycle-evidence-closure-request.v1"
PASSIVE_LATEST_SCHEMA = "obelisk.player-principal-passive-snapshot-latest.v1"
PASSIVE_MONITOR_ONLY_SCHEMA = "obelisk.player-principal-passive-monitor-only-summary.v1"
NOTICE_SCHEMA = "obelisk.player-principal-lifecycle-beta-notice-prep.v1"
EXECUTOR_SCHEMA = "obelisk.player-principal-lifecycle-runtime-window-execution.v1"
STATUS_SCHEMA = "obelisk.sdk-status-report.v1"
NEXT_ACTION_SCHEMA = "obelisk.player-principal-lifecycle-runtime-window-next-action.v1"
RUNNER_CONTRACT_SCHEMA = (
    "obelisk.player-principal-lifecycle-runtime-window-next-action-runner-contract.v1"
)
RUNNER_COMMAND_SCHEMA = (
    "obelisk.player-principal-lifecycle-runtime-window-next-action-runner-command.v1"
)
MULTI_SURFACE_PACK_BOUNDARY_SCHEMA = "obelisk.multi-surface-beta-capture-pack-family-boundary.v1"
MULTI_SURFACE_PACK_SCHEMA = "obelisk.multi-surface-beta-capture-pack.v1"
MULTI_SURFACE_PLAN_SCHEMA = "obelisk.multi-surface-beta-capture-plan.v1"
MULTI_SURFACE_CHECKER_MATRIX_SCHEMA = "obelisk.multi-surface-beta-capture-checker-matrix.v1"
MULTI_SURFACE_NON_CLAIM_MANIFEST_SCHEMA = (
    "obelisk.multi-surface-beta-capture-non-claim-manifest.v1"
)
MULTI_SURFACE_FALSE_FLAGS = (
    "touches_live_servers",
    "authorizes_runtime_work",
    "authorizes_discord",
    "authorizes_discord_send",
    "authorizes_live_ops",
    "authorizes_server_operations",
    "authorizes_server_restart",
    "authorizes_live_log_reads",
    "authorizes_marker_env_writes",
    "authorizes_marker_or_env_changes",
    "counts_as_approved_runtime_evidence",
    "counts_as_runtime_evidence",
    "counts_as_sdk_progress",
    "counts_as_p0_progress",
    "clears_approved_runtime_evidence_missing",
    "runtime_ready",
    "public_sdk_ready",
    "stable_sdk_ready",
    "plugin_hub_ready",
    "publication_ready",
)
MULTI_SURFACE_ACTION_FALSE_FLAGS = (
    "multi_surface_beta_capture_pack_authorizes_runtime_work",
    "multi_surface_beta_capture_pack_authorizes_discord",
    "multi_surface_beta_capture_pack_authorizes_discord_send",
    "multi_surface_beta_capture_pack_authorizes_live_ops",
    "multi_surface_beta_capture_pack_authorizes_server_operations",
    "multi_surface_beta_capture_pack_authorizes_server_restart",
    "multi_surface_beta_capture_pack_authorizes_live_log_reads",
    "multi_surface_beta_capture_pack_authorizes_marker_env_writes",
    "multi_surface_beta_capture_pack_authorizes_marker_or_env_changes",
    "multi_surface_beta_capture_pack_counts_as_approved_runtime_evidence",
    "multi_surface_beta_capture_pack_counts_as_runtime_evidence",
    "multi_surface_beta_capture_pack_counts_as_sdk_progress",
    "multi_surface_beta_capture_pack_counts_as_p0_progress",
    "multi_surface_beta_capture_pack_clears_approved_runtime_evidence_missing",
)
REQUIRED_ROLES = ["session_start", "session_start_rejected", "session_end"]
EXACT_TESTER_EVIDENCE_OBJECTIVE = (
    "produce session_start, exact CheckJoinInProgress(1,0) session_start_rejected, "
    "and matched session_end"
)
DIAGNOSTIC_ENV_LINE = "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1"
PREVIOUS_THEISLAND_RUN_ID_STEM = "20260607T134929Z"
PREVIOUS_THEISLAND_RUN_ID = f"{PREVIOUS_THEISLAND_RUN_ID_STEM}-player-principal-lifecycle"
FRESH_RETRY_SCHEMA = (
    "obelisk.player-principal-lifecycle-fresh-retry-after-closed-non-evidence-window.v1"
)
COPIED_LOG_ROUTE_STEPS = [
    "build_approved_runtime_evidence_bundle_from_evidence_dir",
]
STRICT_CANDIDATE_SUMMARY_JSON_PATH = (
    "modules.player_principal_lifecycle.strict_lifecycle_triplet_candidate_summary"
)


def future_now_utc() -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=1)).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def run_id_for_now_utc(now_utc: str) -> str:
    start = datetime.strptime(now_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) + timedelta(
        minutes=5
    )
    return start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle"


def base_args(output_root: Path, report_dir: Path, *, now_utc: str) -> list[str]:
    return [
        sys.executable,
        str(SCRIPT),
        "--instance",
        "arkserver3",
        "--map",
        "Genesis2",
        "--now-utc",
        now_utc,
        "--start-delay-minutes",
        "5",
        "--duration-minutes",
        "15",
        "--restart-expectation",
        "restart",
        "--output-root",
        str(output_root),
        "--report-dir",
        str(report_dir),
        "--obelisk-commit",
        TEST_COMMIT,
        "--json",
    ]


def run_executor(
    output_root: Path,
    report_dir: Path,
    *extra: str,
    now_utc: str | None = None,
) -> subprocess.CompletedProcess[str]:
    now_utc = now_utc or future_now_utc()
    return subprocess.run(
        [*base_args(output_root, report_dir, now_utc=now_utc), *extra],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def executor_args_without_report_dir(
    output_root: Path,
    *,
    instance: str,
    map_name: str,
    now_utc: str,
) -> list[str]:
    args = base_args(output_root, Path("/unused-report-dir"), now_utc=now_utc)
    report_dir_index = args.index("--report-dir")
    del args[report_dir_index : report_dir_index + 2]
    args[args.index("--instance") + 1] = instance
    args[args.index("--map") + 1] = map_name
    return args


def write_confirmed_notice(
    *,
    root: Path,
    request_json: Path,
    confirmed_notice: Path,
) -> None:
    fake_helper = root / "fake_send_helper.py"
    fake_helper.write_text(
        "import json, sys\n"
        "args = sys.argv[1:]\n"
        "receipt = 'test-confirmed-send-dry-run-receipt'\n"
        "if '--dry-run' in args:\n"
        "    print(json.dumps({\n"
        "        'dry_run_receipt': receipt,\n"
        "        'dry_run_receipt_inputs': {'helper_args': args},\n"
        "        'dry_run_receipt_validated': False,\n"
        "    }))\n"
        "    raise SystemExit(0)\n"
        "supplied = None\n"
        "if '--dry-run-receipt' in args:\n"
        "    index = args.index('--dry-run-receipt')\n"
        "    if index + 1 < len(args):\n"
        "        supplied = args[index + 1]\n"
        "print(json.dumps({\n"
        "    'dry_run_receipt': supplied,\n"
        "    'dry_run_receipt_inputs': {'helper_args': args},\n"
        "    'dry_run_receipt_validated': supplied == receipt,\n"
        "}))\n"
        "raise SystemExit(0 if supplied == receipt else 1)\n",
        encoding="utf-8",
    )
    with confirmed_notice.open("w", encoding="utf-8") as handle:
        subprocess.run(
            [
                sys.executable,
                str(BETA_NOTICE),
                "--request-json",
                str(request_json),
                "--send-helper",
                str(fake_helper),
                "--confirm-approved-send",
                "--artifact-json",
                str(confirmed_notice.with_suffix(".sidecar.json")),
                "--json",
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=handle,
            stderr=subprocess.PIPE,
            check=True,
        )


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_direct_bot_notice_stdout(*, request_json: Path, notice_path: Path) -> None:
    request = json.loads(request_json.read_text(encoding="utf-8"))
    payload = {
        "schema": "obelisk.discord-beta-bridge-bot-notice.v1",
        "ready": True,
        "sent": True,
        "discord_sent": True,
        "target": request["target"],
        "run_id": request["run_id"],
        "notice_path": request["notice_path"],
        "request_json": {
            "path": str(request_json),
            "sha256": hashlib.sha256(request_json.read_bytes()).hexdigest(),
        },
        "active_notice_state_present": True,
        "active_notice_state_required_for_beta_controls": True,
        "active_notice_update_requested": True,
        "operational_message_kind": "single_active_beta_notice",
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
    }
    write_json(notice_path, payload)


def write_active_notice_state(path: Path) -> None:
    write_json(
        path,
        {
            "schema": "obelisk.discord-beta-bridge-active-notice.v1",
            "guild_id": "1032660680668622969",
            "channel_id": "1513238083741683934",
            "message_id": "123456789012345678",
            "operational_message_kind": "single_active_beta_notice",
            "active_notice_state_pointer_only": True,
            "active_notice_state_is_notice_report": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_progress": False,
            "counts_as_p0_progress": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
        },
    )


def closure_report_payload(*, evidence_dir: Path) -> dict:
    missing_roles = ["session_end"]
    return {
        "schema": CLOSURE_SCHEMA,
        "status": "non_ready_missing_lifecycle_roles",
        "closure_case": "active_genesis2_triplet_incomplete",
        "target": {
            "instance": "arkserver3",
            "map": "Genesis2",
            "query_port": "27017",
            "target_key": "arkserver3:Genesis2:27017",
        },
        "ready": False,
        "evidence_closure_inputs_complete": False,
        "evidence_dir": str(evidence_dir),
        "approved_bundle_path": str(
            evidence_dir
            / "approved-bundle"
            / "approved-runtime-principal-lifecycle-evidence.json"
        ),
        "missing_required_artifacts": [],
        "required_lifecycle_event_role_triplet": REQUIRED_ROLES,
        "missing_lifecycle_event_roles": missing_roles,
        "missing_artifacts_and_roles": {
            "missing_required_artifacts": [],
            "required_sidecars": [
                "window-request.json",
                "observer-window.env",
                "operator-approval-request.md",
                "operator-approval-receipt.json",
                "preflight-pre.json",
                "preflight-post.json",
                "window-manifest.env",
                "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
            ],
            "exact_missing_sidecars": [],
            "required_lifecycle_event_role_triplet": REQUIRED_ROLES,
            "missing_lifecycle_event_roles": missing_roles,
            "evidence_source_blockers": [],
            "invalid_sidecars": [],
            "sidecar_validation_blockers": [],
        },
        "evidence_source_blockers": [],
        "invalid_sidecars": [],
        "sidecar_validation_blockers": [],
        "server_operations_authorized": False,
        "runtime_capture_authorized": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
    }


def passive_latest_payload() -> dict:
    target_key = "arkserver3:Genesis2:27017"
    return {
        "schema": PASSIVE_LATEST_SCHEMA,
        "classification": "passive_snapshot_non_evidence",
        "passive_server_activity_summary": {
            "schema": "obelisk.player-principal-passive-server-activity-summary.v1",
            "player_principal_triplet_candidates_by_target": {
                target_key: {
                    "schema": "obelisk.player-principal-passive-target-triplet-candidate-summary.v1",
                    "target_key": target_key,
                    "instance": "arkserver3",
                    "map": "Genesis2",
                    "query_port": "27017",
                    "roles_seen": ["session_start", "session_start_rejected"],
                    "missing_roles": ["session_end"],
                    "complete_triplet_candidate": False,
                    "approved_runtime_evidence": False,
                    "ready": False,
                    "route_ready": False,
                    "readiness_gate": "none",
                    "process_control": "none",
                },
            },
            "targets_with_complete_player_principal_triplet_candidate": [],
            "approved_runtime_evidence": False,
            "ready": False,
            "route_ready": False,
            "readiness_gate": "none",
            "process_control": "none",
        },
        "passive_actionability": {
            "schema": "obelisk.player-principal-passive-actionability.v1",
            "priority": "accepted_observer_event_triplet_candidate",
            "reason_kind": "partial_accepted_observer_event_triplet_candidate_present",
            "next_reason": "partial_accepted_observer_event_triplet_candidate_present_non_evidence",
            "process_control": "none",
            "approved_runtime_evidence": False,
            "ready": False,
            "route_ready": False,
            "readiness_gate": "none",
            "evidence_classification": "passive_actionability_non_evidence",
        },
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
        "readiness_gate": "none",
        "non_claims": [
            "accepted observer event triplet candidates remain passive non-evidence until approved evidence checkers accept a copied sibling-set bundle"
        ],
    }


def passive_no_users_payload() -> dict:
    target_key = "arkserver3:Genesis2:27017"
    return {
        "schema": PASSIVE_MONITOR_ONLY_SCHEMA,
        "classification": "no_snapshots_no_passive_detections_no_complete_triplets_non_evidence",
        "passive_monitor_activity_summary": {
            "schema": "obelisk.player-principal-passive-monitor-activity-summary.v1",
            "players_current_by_target": {target_key: 0},
            "targets_with_players_detected": [],
            "observer_enabled_targets": [target_key],
            "complete_observer_event_triplet_targets": [],
            "approved_runtime_evidence": False,
            "ready": False,
            "route_ready": False,
            "process_control": "none",
        },
        "passive_actionability": {
            "schema": "obelisk.player-principal-passive-actionability.v1",
            "priority": "no_users_wait_for_organic_player",
            "reason_kind": "no_users_observed",
            "next_reason": "no_users_passive_wait_for_player_backed_evidence",
            "process_control": "passive_wait_without_restart",
            "evidence_classification": "passive_actionability_non_evidence",
            "approved_runtime_evidence": False,
            "ready": False,
        },
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
        "readiness_gate": "none",
    }


class PreparePlayerPrincipalLifecycleRuntimeWindowExecutionTests(unittest.TestCase):
    def assert_lifecycle_objective(self, objectives: dict) -> None:
        self.assertEqual(objectives["tester_evidence_objective"], EXACT_TESTER_EVIDENCE_OBJECTIVE)
        self.assertEqual(
            objectives["tester_evidence_objective_items"],
            [
                "session_start",
                "exact CheckJoinInProgress(1,0) session_start_rejected",
                "matched session_end",
            ],
        )
        self.assertTrue(objectives["exact_session_start_rejected_required"])
        self.assertTrue(objectives["matched_session_end_required"])
        self.assertTrue(objectives["objectives_are_preparation_only"])
        self.assertFalse(objectives["readiness_claim_allowed"])
        self.assertFalse(objectives["progress_claim_allowed"])
        self.assertFalse(objectives["preparation_counts_as_readiness"])
        self.assertFalse(objectives["preparation_counts_as_progress"])

    def assert_multi_surface_boundary(self, boundary: dict) -> None:
        self.assertEqual(boundary["schema"], MULTI_SURFACE_PACK_BOUNDARY_SCHEMA)
        self.assertEqual(boundary["status"], "offline_candidate_metadata_only")
        self.assertIn(MULTI_SURFACE_PACK_SCHEMA, boundary["family_schemas"])
        self.assertIn(MULTI_SURFACE_PLAN_SCHEMA, boundary["family_schemas"])
        self.assertIn(MULTI_SURFACE_CHECKER_MATRIX_SCHEMA, boundary["family_schemas"])
        self.assertIn(MULTI_SURFACE_NON_CLAIM_MANIFEST_SCHEMA, boundary["family_schemas"])
        self.assertTrue(boundary["metadata_reference_allowed"])
        self.assertFalse(boundary["post_window_state_input_accepted"])
        self.assertFalse(boundary["approved_evidence_bundle_checker_accepted"])
        self.assertTrue(boundary["approved_evidence_bundle_acceptance_required"])
        self.assertEqual(
            boundary["candidate_pack_integrity_validation_scope"],
            "candidate_capture_pack_integrity_only",
        )
        self.assertFalse(
            boundary[
                "candidate_pack_integrity_validated_counts_as_approved_runtime_evidence"
            ]
        )
        self.assertFalse(boundary["candidate_pack_integrity_validated_counts_as_runtime_evidence"])
        self.assertFalse(boundary["candidate_pack_integrity_validated_counts_as_sdk_progress"])
        self.assertFalse(boundary["candidate_pack_integrity_validated_counts_as_p0_progress"])
        self.assertTrue(boundary["non_claim_flags"]["candidate_only"])
        self.assertTrue(boundary["non_claim_flags"]["offline_candidate_metadata_only"])
        self.assertTrue(boundary["multi_surface_beta_capture_pack_metadata_only"])
        self.assertTrue(boundary["multi_surface_beta_capture_pack_offline_candidate_metadata_only"])
        for key in MULTI_SURFACE_FALSE_FLAGS:
            with self.subTest(boundary_flag=key):
                self.assertFalse(boundary["non_claim_flags"][key])
        for key in MULTI_SURFACE_ACTION_FALSE_FLAGS:
            with self.subTest(boundary_action_flag=key):
                self.assertFalse(boundary[key])

    def assert_approved_bundle_requirement(self, requirement: dict) -> None:
        self.assertTrue(requirement["accepted_bundle_required_before_any_readiness_or_progress_claim"])
        self.assertFalse(requirement["approved_evidence_bundle_checker_accepted"])
        self.assertEqual(requirement["tester_evidence_objective"], EXACT_TESTER_EVIDENCE_OBJECTIVE)
        self.assertEqual(requirement["ordered_copied_log_route_step_ids"], COPIED_LOG_ROUTE_STEPS)
        self.assert_copied_log_route(requirement["copied_log_route_required"])
        self.assertEqual(requirement["required_lifecycle_event_role_triplet"], REQUIRED_ROLES)
        self.assertEqual(
            requirement["session_start_rejected"],
            {
                "required_function": SESSION_START_REJECTED_REQUIRED_FUNCTION,
                "required_argument_tuple": SESSION_START_REJECTED_REQUIRED_ARGUMENTS,
                "required_call": SESSION_START_REJECTED_REQUIRED_CALL,
                "required_exact_call": SESSION_START_REJECTED_REQUIRED_CALL,
                "exact_check_join_in_progress_requirement": SESSION_START_REJECTED_REQUIRED_CALL,
                "handle_new_player_rejected_tuple_allowed": False,
                "handle_new_player_rejected_tuple_alternative_allowed": False,
            },
        )
        self.assertEqual(
            requirement["session_start_rejected"]["exact_check_join_in_progress_requirement"],
            "CheckJoinInProgress(1,0)",
        )
        self.assertEqual(
            requirement["lifecycle_missing_role_objectives"][
                "exact_check_join_in_progress_requirement"
            ],
            "CheckJoinInProgress(1,0)",
        )
        self.assert_lifecycle_objective(requirement["lifecycle_missing_role_objectives"])
        self.assertFalse(requirement["passive_or_no_user_state_counts_as_evidence"])
        self.assertFalse(requirement["passive_or_no_user_state_counts_as_readiness"])
        self.assertFalse(requirement["passive_or_no_user_state_counts_as_progress"])
        self.assertFalse(requirement["passive_or_no_user_state_counts_as_authorization"])
        self.assertFalse(requirement["passive_or_no_user_state_counts_as_notice_sent"])
        self.assertFalse(requirement["readiness_claim_allowed"])
        self.assertFalse(requirement["progress_claim_allowed"])
        self.assertFalse(requirement["preparation_counts_as_readiness"])
        self.assertFalse(requirement["preparation_counts_as_progress"])
        self.assertTrue(requirement["multi_surface_beta_capture_pack_metadata_only"])
        for key in MULTI_SURFACE_ACTION_FALSE_FLAGS:
            with self.subTest(requirement_flag=key):
                self.assertFalse(requirement[key])

    def assert_copied_log_route(self, route: dict) -> None:
        self.assertEqual(route["ordered_step_ids"], COPIED_LOG_ROUTE_STEPS)
        self.assertEqual(route["tester_evidence_objective"], EXACT_TESTER_EVIDENCE_OBJECTIVE)
        self.assertIn("one-shot approved runtime evidence bundle builder", route["route"])
        self.assertEqual(
            route["strict_lifecycle_triplet_candidate_summary_json_path"],
            STRICT_CANDIDATE_SUMMARY_JSON_PATH,
        )
        self.assertTrue(route["checker_acceptance_required_before_evidence_state_change"])
        self.assertTrue(route["all_prior_outputs_non_authorizing_and_non_evidence"])
        self.assertFalse(route["restart_recommended"])
        self.assertFalse(route["raw_player_text_or_identity_allowed"])
        self.assertFalse(route["server_operations_authorized"])
        self.assertFalse(route["runtime_capture_authorized"])
        self.assertFalse(route["live_log_reads_authorized"])
        self.assertFalse(route["counts_as_approved_runtime_evidence"])
        self.assertFalse(route["readiness_claim_allowed"])
        self.assertFalse(route["progress_claim_allowed"])
        self.assertFalse(route["preparation_counts_as_readiness"])
        self.assertFalse(route["preparation_counts_as_progress"])
        self.assertFalse(route["runtime_ready"])
        self.assertFalse(route["public_sdk_ready"])

    def assert_evidence_pipeline(self, pipeline: dict) -> None:
        self.assertEqual(pipeline["ordered_step_ids"], COPIED_LOG_ROUTE_STEPS)
        self.assertEqual(pipeline["ordered_copied_log_route_step_ids"], COPIED_LOG_ROUTE_STEPS)
        self.assert_copied_log_route(pipeline["copied_log_route"])
        self.assertTrue(pipeline["checker_acceptance_required_before_evidence_state_change"])
        self.assertTrue(pipeline["all_prior_outputs_non_authorizing_and_non_evidence"])
        commands = {item["id"]: item for item in pipeline["commands"]}
        self.assertEqual(list(commands), COPIED_LOG_ROUTE_STEPS)
        bundle_step = commands["build_approved_runtime_evidence_bundle_from_evidence_dir"]
        self.assertIn(
            "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py",
            bundle_step["command_text_not_executed"],
        )
        self.assertIn("--evidence-dir", bundle_step["command_text_not_executed"])
        self.assertNotIn("--preflight-only", bundle_step["command_text_not_executed"])
        self.assertIn(
            "scripts/analyze_runtime_observer_log.py",
            bundle_step["internal_analyzer"],
        )
        self.assertIn(
            "scripts/build_player_identity_runtime_principal_lifecycle_approved_manifest.py",
            bundle_step["internal_manifest_builder"],
        )
        self.assertIn(
            "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
            bundle_step["internal_checker"],
        )
        self.assertEqual(bundle_step["emits_summary_field"], STRICT_CANDIDATE_SUMMARY_JSON_PATH)
        self.assertTrue(bundle_step["candidate_ready_for_bundle_preflight_required"])
        for command in commands.values():
            self.assertFalse(command["restart_recommended"])
            self.assertFalse(command["raw_player_text_or_identity_allowed"])
            self.assertFalse(command["server_operations_authorized"])
            self.assertFalse(command["runtime_capture_authorized"])
            self.assertFalse(command["counts_as_approved_runtime_evidence"])
            self.assertFalse(command["runtime_ready"])
            self.assertFalse(command["public_sdk_ready"])
        self.assertEqual(
            pipeline["artifacts"]["strict_lifecycle_triplet_candidate_summary_json_path"],
            STRICT_CANDIDATE_SUMMARY_JSON_PATH,
        )
        self.assertFalse(pipeline["restart_recommended"])
        self.assertFalse(pipeline["raw_player_text_or_identity_allowed"])
        self.assertFalse(pipeline["authorization"]["server_operations_authorized"])
        self.assertFalse(pipeline["evidence"]["counts_as_approved_runtime_evidence"])

    def assert_runner_actions_common(self, report: dict) -> None:
        actions = report["next_action_sequence"]
        self.assertEqual([item["order"] for item in actions], list(range(1, len(actions) + 1)))
        for item in actions:
            with self.subTest(action=item["id"]):
                self.assertEqual(item["schema"], NEXT_ACTION_SCHEMA)
                self.assertEqual(item["status"], "manual_external_not_executed_by_executor")
                contract = item["runner_contract"]
                self.assertEqual(contract["schema"], RUNNER_CONTRACT_SCHEMA)
                self.assertEqual(contract["runner"], "lead_runtime_runner")
                self.assertTrue(contract["deterministic"])
                self.assertFalse(contract["execute_by_default"])
                self.assertFalse(contract["side_effects_performed_by_executor"])
                self.assertTrue(contract["manual_external_execution_required"])
                self.assertEqual(contract["target"], report["target"])
                self.assertEqual(contract["run_id"], report["run_id"])
                self.assertEqual(contract["approved_window"], report["approved_window"])
                self.assertEqual(contract["authority_source"], "recorded_standing_launch_authority")
                guarded_beta_send = item["id"] == "send_guarded_beta_notice_with_recorded_standing_authority"
                self.assertEqual(
                    contract["runner_may_use_recorded_standing_authority"],
                    guarded_beta_send,
                )
                self.assertEqual(
                    contract["runner_may_use_recorded_standing_authority_for_preparation_only"],
                    not guarded_beta_send,
                )
                self.assertEqual(
                    contract["recorded_standing_launch_authority_satisfies_scope"],
                    guarded_beta_send,
                )
                self.assertFalse(contract["recorded_standing_debug_authority_satisfies_scope"])
                self.assertTrue(contract["recorded_standing_launch_authority_satisfies_preparation_scope"])
                self.assertTrue(contract["recorded_standing_debug_authority_satisfies_preparation_scope"])
                self.assertEqual(
                    contract["separate_operator_authorization_required"],
                    not guarded_beta_send,
                )
                self.assertEqual(
                    contract["standing_authority_authorizes_discord_send"],
                    guarded_beta_send,
                )
                if guarded_beta_send:
                    self.assertTrue(
                        contract["standing_authority_satisfies_guarded_beta_notice_send_scope"]
                    )
                    self.assertTrue(
                        contract[
                            "guarded_beta_notice_send_scope_satisfied_by_standing_authority"
                        ]
                    )
                self.assertFalse(contract["standing_authority_authorizes_runtime_evidence"])
                self.assertFalse(contract["standing_authority_authorizes_marker_env_changes"])
                self.assertFalse(contract["standing_authority_authorizes_server_restart"])
                self.assertFalse(contract["standing_authority_counts_as_runtime_progress"])
                self.assertFalse(contract["standing_authority_counts_as_sdk_progress"])
                self.assertFalse(contract["standing_authority_grants_runtime_readiness"])
                self.assertEqual(contract["two_server_cap_policy"]["max_running_ark_servers"], 2)
                self.assertEqual(
                    contract["lifecycle_missing_role_objectives"]["objective_ids"],
                    ["session_start", "CheckJoinInProgress(1,0)", "session_end"],
                )
                self.assert_lifecycle_objective(contract["lifecycle_missing_role_objectives"])
                self.assertIn(item["prepared_action_mode"], {"notice_only", "request_only"})
                self.assertEqual(item["prepared_action_scope"], "notice_only_or_request_only")
                self.assertTrue(item["notice_only_or_request_only_until_approved_evidence_bundle_accepted"])
                self.assertFalse(item["prepared_actions_count_as_readiness"])
                self.assertFalse(item["prepared_actions_count_as_progress"])
                self.assertFalse(item["readiness_claim_allowed"])
                self.assertFalse(item["progress_claim_allowed"])
                self.assertFalse(item["approved_evidence_bundle_checker_accepted"])
                self.assert_approved_bundle_requirement(item["approved_evidence_bundle_acceptance_requirement"])
                self.assertEqual(contract["prepared_action_mode"], item["prepared_action_mode"])
                self.assertFalse(contract["prepared_actions_count_as_readiness"])
                self.assertFalse(contract["prepared_actions_count_as_progress"])
                self.assertFalse(contract["readiness_claim_allowed"])
                self.assertFalse(contract["progress_claim_allowed"])
                self.assertFalse(contract["approved_evidence_bundle_checker_accepted"])
                self.assert_approved_bundle_requirement(contract["approved_evidence_bundle_acceptance_requirement"])
                self.assertTrue(item["multi_surface_beta_capture_pack_metadata_only"])
                self.assertTrue(contract["multi_surface_beta_capture_pack_metadata_only"])
                operation = item["runner_operation"]
                self.assertFalse(operation["execute_by_default"])
                self.assertFalse(operation["performed_by_executor"])
                self.assertEqual(operation["prepared_action_mode"], item["prepared_action_mode"])
                self.assertFalse(operation["prepared_actions_count_as_readiness"])
                self.assertFalse(operation["prepared_actions_count_as_progress"])
                self.assertFalse(operation["readiness_claim_allowed"])
                self.assertFalse(operation["progress_claim_allowed"])
                self.assertFalse(operation["approved_evidence_bundle_checker_accepted"])
                self.assert_approved_bundle_requirement(operation["approved_evidence_bundle_acceptance_requirement"])
                self.assertTrue(operation["multi_surface_beta_capture_pack_metadata_only"])
                for key in MULTI_SURFACE_ACTION_FALSE_FLAGS:
                    with self.subTest(action=item["id"], multi_surface_flag=key):
                        self.assertFalse(item[key])
                        self.assertFalse(contract[key])
                        self.assertFalse(operation[key])
                command = item["runner_command"]
                if command is not None:
                    self.assertEqual(command["schema"], RUNNER_COMMAND_SCHEMA)
                    self.assertFalse(command["execute_by_default"])
                    self.assertFalse(command["performed_by_executor"])

    def test_prepares_offline_preactivation_without_discord_send_or_runtime_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "live-validation-logs"
            report_dir = root / "reports"
            now_utc = future_now_utc()
            result = run_executor(output_root, report_dir, now_utc=now_utc)
            report = json.loads(result.stdout)

            evidence_dir = Path(report["evidence_dir"])

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(report["status"], "offline_preactivation_prepared_notice_send_pending")
            self.assertTrue(report["preactivation_prepared"])
            self.assertTrue(report["runtime_window_prepared"])
            self.assertTrue(report["prepared_metadata_only"])
            self.assertEqual(report["preparation_status"], "prepared_metadata_only")
            self.assertEqual(report["tester_evidence_objective"], EXACT_TESTER_EVIDENCE_OBJECTIVE)
            self.assertFalse(report["readiness_claim_allowed"])
            self.assertFalse(report["progress_claim_allowed"])
            self.assertFalse(report["preparation_counts_as_readiness"])
            self.assertFalse(report["preparation_counts_as_progress"])
            self.assertEqual(report["run_id"], run_id_for_now_utc(now_utc))
            self.assertEqual(report["target"], {"instance": "arkserver3", "map": "Genesis2"})
            self.assertTrue(report["report_dir_deterministic"])
            self.assertTrue(report["report_dir_collision_resistant"])
            self.assertEqual(report["executed_step_ids"], [
                "prepare_request_pack",
                "check_request_pack",
                "beta_notice_dry_run",
                "route_gate",
            ])
            self.assertTrue((evidence_dir / "window-request.json").is_file())
            self.assertTrue((evidence_dir / "observer-window.env").is_file())
            self.assertTrue((evidence_dir / "operator-approval-receipt.json").is_file())
            request = json.loads((evidence_dir / "window-request.json").read_text(encoding="utf-8"))
            observer_env = (evidence_dir / "observer-window.env").read_text(encoding="utf-8").splitlines()
            self.assertFalse(request["diagnostic_candidates_enabled"])
            self.assertFalse(report["diagnostic_candidates_requested"])
            self.assertFalse(report["diagnostic_candidates_enabled_in_request_pack"])
            self.assertFalse(report["diagnostic_candidates"]["enabled_in_request_pack"])
            diagnostic_policy = report["diagnostic_candidates_for_approved_evidence"]
            self.assertFalse(diagnostic_policy["approved_evidence_window_rejected"])
            self.assertTrue(diagnostic_policy["request_explicitly_disabled"])
            self.assertEqual(diagnostic_policy["approved_evidence_blockers"], [])
            self.assertFalse(diagnostic_policy["observer_env_contains_diagnostic_candidates"])
            self.assertEqual(diagnostic_policy["observer_env_diagnostic_keys_present"], [])
            self.assertEqual(report["two_server_cap_policy"]["max_running_ark_servers"], 2)
            self.assertTrue(report["two_server_cap_policy"]["never_keep_three_ark_servers_running"])
            self.assertEqual(
                report["lifecycle_missing_role_objectives"]["objective_ids"],
                ["session_start", "CheckJoinInProgress(1,0)", "session_end"],
            )
            self.assert_lifecycle_objective(report["lifecycle_missing_role_objectives"])
            self.assertTrue(report["recommended_notice_text"]["recommended_text_already_redacted"])
            self.assertFalse(report["recommended_notice_text"]["raw_player_text_or_identity_allowed"])
            self.assertEqual(
                report["recommended_notice_text"]["tester_evidence_objective"],
                EXACT_TESTER_EVIDENCE_OBJECTIVE,
            )
            self.assertIn(
                EXACT_TESTER_EVIDENCE_OBJECTIVE,
                report["recommended_notice_text"]["recommended_discord_text_redacted"],
            )
            self.assertIn(
                "CheckJoinInProgress(1,0)",
                report["recommended_notice_text"]["recommended_discord_text_redacted"],
            )
            self.assertNotIn(DIAGNOSTIC_ENV_LINE, observer_env)
            self.assertTrue((report_dir / "window-request.check.json").is_file())
            self.assertTrue((report_dir / "beta-notice.dry-run.json").is_file())
            self.assertTrue((report_dir / "beta-notice.dry-run.sidecar.json").is_file())
            self.assertTrue((report_dir / "route-gate.json").is_file())
            self.assertTrue((report_dir / "runtime-window-execution.json").is_file())
            self.assertEqual(
                report["request_pack_paths"],
                {
                    "directory": str(evidence_dir),
                    "window_request": str(evidence_dir / "window-request.json"),
                    "observer_env": str(evidence_dir / "observer-window.env"),
                    "operator_approval_request": str(evidence_dir / "operator-approval-request.md"),
                    "operator_approval_receipt": str(evidence_dir / "operator-approval-receipt.json"),
                },
            )
            self.assertEqual(report["output_paths"]["dry_run_report"], str(report_dir / "beta-notice.dry-run.json"))
            self.assertEqual(
                report["output_paths"]["dry_run_notice_sidecar"],
                str(report_dir / "beta-notice.dry-run.sidecar.json"),
            )
            self.assertEqual(report["output_paths"]["route_gate_report"], str(report_dir / "route-gate.json"))
            self.assertEqual(
                report["output_paths"]["activation_preconditions_report"],
                str(report_dir / "activation-preconditions.json"),
            )
            self.assertEqual(report["activation_preconditions_json"], str(report_dir / "activation-preconditions.json"))
            self.assertEqual(
                report["runtime_window_execution_report_json"],
                str(report_dir / "runtime-window-execution.json"),
            )
            self.assertFalse(report["stdout_only_confirmation_accepted"])
            self.assertFalse((evidence_dir / "beta-notice.dry-run.json").exists())
            self.assertFalse((evidence_dir / "route-gate.json").exists())
            self.assertFalse(report["activation_preconditions_checked"])
            self.assertFalse(report["activation_preconditions_ready"])
            self.assertFalse(report["activation_preconditions_offline_ready"])
            self.assertFalse(report["activation_preconditions_ready_claim_allowed"])
            self.assertFalse(report["activation_preconditions_progress_claim_allowed"])
            self.assertEqual(report["activation_preconditions_ready_scope"], "not_checked")
            self.assertTrue(report["confirmed_notice_required_before_activation"])
            self.assertEqual(report["next_blocker"], "approved_dry_run_checked_beta_testers_notice_sent")
            stale_prevention = report["runtime_window_stale_prevention"]
            self.assertEqual(
                stale_prevention["schema"],
                "obelisk.player-principal-lifecycle-runtime-window-stale-prevention.v1",
            )
            self.assertEqual(stale_prevention["minimum_required_lead_seconds"], 300)
            self.assertEqual(stale_prevention["blockers"], [])
            self.assertTrue(stale_prevention["enough_future_lead_time"])
            self.assertTrue(stale_prevention["confirmed_send_must_complete_before_window_start"])
            self.assertFalse(stale_prevention["activation_or_restart_from_stale_request_allowed"])
            self.assertFalse(stale_prevention["monitor_or_restart_activation_after_window_start_allowed"])
            notice_sequence = report["beta_notice_sequence_enforcement"]
            self.assertTrue(notice_sequence["beta_notice_dry_run_required_before_activation"])
            self.assertTrue(notice_sequence["confirmed_beta_notice_required_before_activation"])
            self.assertFalse(notice_sequence["confirmed_notice_counts_as_approved_runtime_evidence"])
            self.assert_multi_surface_boundary(report["multi_surface_beta_capture_pack_boundary"])
            self.assertEqual(
                report["external_execution_authority"]["multi_surface_beta_capture_pack_boundary"],
                report["multi_surface_beta_capture_pack_boundary"],
            )
            self.assertFalse(report["multi_surface_beta_capture_pack_counts_as_approved_runtime_evidence"])
            self.assertFalse(report["multi_surface_beta_capture_pack_authorizes_live_ops"])
            self.assertFalse(report["multi_surface_beta_capture_pack_authorizes_live_log_reads"])
            self.assertFalse(report["multi_surface_beta_capture_pack_authorizes_marker_env_writes"])
            boundaries = report["execution_boundaries"]
            self.assertEqual(
                boundaries["classification"],
                "offline_boundaries_no_automatic_side_effects",
            )
            self.assertEqual(
                report["prepared_artifacts"],
                boundaries["prepared_artifacts"],
            )
            self.assertEqual(
                boundaries["prepared_artifacts"]["request_pack"],
                report["request_pack_paths"],
            )
            self.assertFalse(
                boundaries["prepared_artifacts"]["prepared_artifacts_authorize_machine_actions"]
            )
            self.assertIn(
                "send_guarded_beta_notice_with_recorded_standing_authority",
                boundaries["human_lead_actions"]["side_effect_action_ids"],
            )
            self.assertFalse(boundaries["human_lead_actions"]["automatic_discord_send_allowed"])
            self.assertFalse(boundaries["human_lead_actions"]["automatic_start_or_restart_allowed"])
            self.assertEqual(boundaries["runtime_window_stale_prevention"], stale_prevention)
            self.assertEqual(boundaries["beta_notice_sequence_enforcement"], notice_sequence)
            self.assertTrue(
                boundaries["standing_authority_metadata"]["standing_launch_authority_recorded"]
            )
            self.assertFalse(
                boundaries["standing_authority_metadata"][
                    "standing_authority_converted_to_machine_action"
                ]
            )
            self.assertFalse(
                boundaries["standing_authority_metadata"][
                    "standing_authority_authorizes_runner_execution"
                ]
            )
            pipeline = report["evidence_pipeline_command_sequence"]
            self.assert_evidence_pipeline(pipeline)
            self.assertEqual(boundaries["evidence_pipeline_command_sequence"], pipeline)
            checker_replay = boundaries["checker_required_post_window_replay"]
            self.assertTrue(checker_replay["post_window_replay_required"])
            self.assertEqual(checker_replay["ordered_copied_log_route_step_ids"], COPIED_LOG_ROUTE_STEPS)
            self.assert_copied_log_route(checker_replay["copied_log_route_required"])
            self.assertFalse(checker_replay["accepted_by_this_report"])
            self.assertFalse(checker_replay["clears_approved_runtime_evidence_missing"])
            self.assertTrue(report["external_execution_authority"]["standing_launch_authority_recorded"])
            self.assertTrue(report["external_execution_authority"]["standing_launch_authority_satisfies_dry_run_notice_preparation_scope"])
            self.assertTrue(report["external_execution_authority"]["standing_launch_authority_satisfies_beta_notice_scope"])
            self.assertTrue(
                report["external_execution_authority"][
                    "standing_authority_satisfies_guarded_beta_notice_send_scope"
                ]
            )
            self.assertTrue(
                report["external_execution_authority"][
                    "guarded_beta_notice_send_scope_satisfied_by_standing_authority"
                ]
            )
            self.assertFalse(report["external_execution_authority"]["standing_launch_authority_satisfies_active_observation_scope"])
            self.assertFalse(report["external_execution_authority"]["separate_operator_authorization_required"])
            self.assertTrue(report["external_execution_authority"]["standing_authority_authorizes_discord_send"])
            self.assertFalse(report["external_execution_authority"]["discord_send_performed_by_executor"])
            self.assertFalse(report["external_execution_authority"]["standing_authority_authorizes_marker_env_changes"])
            self.assertFalse(report["external_execution_authority"]["standing_authority_authorizes_server_restart"])
            self.assertFalse(report["external_execution_authority"]["standing_authority_counts_as_runtime_progress"])
            self.assertFalse(report["external_execution_authority"]["standing_authority_counts_as_sdk_progress"])
            self.assertFalse(report["external_execution_authority"]["standing_authority_grants_runtime_readiness"])
            self.assertEqual(
                [item["id"] for item in report["next_action_sequence"]],
                [
                    "review_offline_outputs",
                    "send_guarded_beta_notice_with_recorded_standing_authority",
                    "consume_confirmed_notice_offline",
                    "active_observation_waits_for_activation_preconditions",
                ],
            )
            self.assert_runner_actions_common(report)
            notice_action = report["next_action_sequence"][1]
            self.assertFalse(notice_action["separate_operator_authorization_required"])
            self.assertEqual(notice_action["authority_source"], "recorded_standing_launch_authority")
            self.assertFalse(notice_action["discord_send_performed_by_executor"])
            self.assertTrue(
                notice_action["standing_authority_satisfies_guarded_beta_notice_send_scope"]
            )
            self.assertTrue(
                notice_action["guarded_beta_notice_send_scope_satisfied_by_standing_authority"]
            )
            self.assertTrue(notice_action["standing_authority_authorizes_discord_send"])
            self.assertFalse(notice_action["confirmed_send_requires_separate_explicit_discord_send_approval"])
            self.assertEqual(
                notice_action["blocked_until"],
                [
                    "beta_notice_dry_run_reviewed",
                    "request_window_start_in_future",
                    "confirmed_send_before_window_start",
                ],
            )
            self.assertTrue(notice_action["required_before_activation"])
            self.assertTrue(notice_action["confirmed_send_must_complete_before_window_start"])
            self.assertFalse(notice_action["activation_or_restart_from_stale_request_allowed"])
            self.assertEqual(notice_action["runtime_window_stale_prevention"], stale_prevention)
            self.assertTrue(notice_action["recommended_notice_text"]["recommended_text_already_redacted"])
            self.assertIn("--confirm-approved-send", notice_action["argv"])
            self.assertEqual(notice_action["runner_contract"]["side_effect_domain"], "discord_notice")
            self.assertEqual(notice_action["runner_command"]["argv"], notice_action["argv"])
            self.assertEqual(
                notice_action["runner_command"]["redirect_stdout"],
                str(report_dir / "beta-notice.confirmed.json"),
            )
            consume_action = report["next_action_sequence"][2]
            self.assertEqual(
                consume_action["blocked_until"],
                [
                    "confirmed_beta_notice_report_exists",
                    "confirmed_notice_sidecar_exists",
                    "request_window_start_in_future",
                ],
            )
            self.assertTrue(consume_action["required_before_activation"])
            self.assertFalse(consume_action["monitor_or_restart_activation_after_window_start_allowed"])
            self.assertEqual(consume_action["runner_contract"]["side_effect_domain"], "offline_report_write")
            self.assertEqual(
                consume_action["runner_command"]["argv"],
                [
                    "python3",
                    "scripts/check_player_principal_lifecycle_activation_preconditions.py",
                    "--request-json",
                    str(evidence_dir / "window-request.json"),
                    "--request-check-json",
                    str(report_dir / "window-request.check.json"),
                    "--notice-report-json",
                    str(report_dir / "beta-notice.confirmed.json"),
                    "--route-gate-json",
                    str(report_dir / "route-gate.json"),
                    "--json",
                ],
            )
            self.assertEqual(consume_action["runner_command"]["env"], {"PYTHONDONTWRITEBYTECODE": "1"})
            self.assertEqual(
                consume_action["runner_command"]["redirect_stdout"],
                str(report_dir / "activation-preconditions.json"),
            )
            self.assertEqual(
                report["route_gate_expected"],
                {
                    "valid": True,
                    "planning_only": True,
                    "route_blocked": True,
                    "current_route_blocker": "approved_runtime_evidence_missing",
                },
            )
            self.assertTrue(report["prepared_actions_remain_notice_only_or_request_only"])
            self.assertFalse(report["approved_evidence_bundle_checker_accepted"])
            self.assertTrue(report["approved_evidence_bundle_acceptance_required"])
            self.assert_approved_bundle_requirement(report["approved_evidence_bundle_acceptance_requirement"])
            for key in (
                "discord_sent",
                "server_operations_authorized",
                "runtime_capture_authorized",
                "approved_runtime_evidence_present",
                "public_sdk_ready",
                "stable_claim_allowed",
            ):
                with self.subTest(key=key):
                    self.assertFalse(report[key])
            dry_run = json.loads((report_dir / "beta-notice.dry-run.json").read_text(encoding="utf-8"))
            dry_run_sidecar = json.loads(
                (report_dir / "beta-notice.dry-run.sidecar.json").read_text(encoding="utf-8")
            )
            persisted_report = json.loads(
                (report_dir / "runtime-window-execution.json").read_text(encoding="utf-8")
            )
            self.assertEqual(dry_run["mode"], "dry_run")
            self.assertFalse(dry_run["discord_sent"])
            self.assertTrue(dry_run["ready"])
            self.assertEqual(dry_run_sidecar["notice_report"], dry_run)
            self.assertEqual(persisted_report, report)

    def test_prepare_multi_surface_beta_pack_flag_prepares_and_checks_candidate_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "live-validation-logs"
            report_dir = root / "reports"
            result = run_executor(
                output_root,
                report_dir,
                "--prepare-multi-surface-beta-pack",
            )
            report = json.loads(result.stdout)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                report["executed_step_ids"],
                [
                    "prepare_request_pack",
                    "check_request_pack",
                    "beta_notice_dry_run",
                    "route_gate",
                    "prepare_multi_surface_beta_pack",
                    "check_multi_surface_beta_pack",
                ],
            )
            self.assertTrue(report["multi_surface_beta_capture_pack_requested"])
            self.assertTrue(report["multi_surface_beta_capture_pack_prepared"])
            self.assertTrue(report["multi_surface_beta_capture_pack_checked"])
            self.assertTrue(
                report["multi_surface_beta_capture_pack_candidate_integrity_validated"]
            )

            paths = report["multi_surface_beta_capture_pack_paths"]
            pack_dir = Path(paths["pack_dir"])
            manifest_path = pack_dir / "manifest.json"
            prepare_report = Path(paths["prepare_report"])
            check_report = Path(paths["check_report"])
            self.assertTrue(manifest_path.is_file())
            self.assertTrue(prepare_report.is_file())
            self.assertTrue(check_report.is_file())
            self.assertEqual(
                report["output_paths"]["multi_surface_beta_capture_pack"],
                paths,
            )
            self.assertEqual(
                report["execution_boundaries"]["prepared_artifacts"][
                    "multi_surface_beta_capture_pack"
                ],
                paths,
            )
            self.assertEqual(
                report["next_action_sequence"][0]["paths"]["multi_surface_beta_capture_pack"],
                paths,
            )

            prepare_payload = json.loads(prepare_report.read_text(encoding="utf-8"))
            check_payload = json.loads(check_report.read_text(encoding="utf-8"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(prepare_payload["schema"], MULTI_SURFACE_PACK_SCHEMA)
            self.assertEqual(prepare_payload["status"], "candidate_capture_pack")
            self.assertEqual(check_payload["schema"], "obelisk.multi-surface-beta-capture-pack-check.v1")
            self.assertEqual(check_payload["status"], "candidate_pack_validated")
            self.assertTrue(check_payload["ready"])
            self.assertEqual(check_payload["ready_scope"], "candidate_capture_pack_integrity_only")
            self.assertEqual(check_payload["pack_root"], str(pack_dir))
            self.assertEqual(prepare_payload["target"], report["target"])
            self.assertEqual(check_payload["target"], report["target"])
            self.assertEqual(manifest["target"], report["target"])
            self.assertEqual(manifest["schema"], MULTI_SURFACE_PACK_SCHEMA)
            self.assertIn(MULTI_SURFACE_PLAN_SCHEMA, report["multi_surface_beta_capture_pack_boundary"]["family_schemas"])

            execution = report["multi_surface_beta_capture_pack_execution"]
            self.assertEqual(
                execution["schema"],
                "obelisk.multi-surface-beta-capture-pack-executor-preparation.v1",
            )
            self.assertEqual(execution["status"], "candidate_pack_prepared_and_checked")
            self.assertEqual(
                execution["step_ids"],
                ["prepare_multi_surface_beta_pack", "check_multi_surface_beta_pack"],
            )
            self.assertEqual(execution["check_status"], "candidate_pack_validated")
            self.assertEqual(
                execution["check_ready_scope"],
                "candidate_capture_pack_integrity_only",
            )
            self.assertTrue(execution["candidate_pack_integrity_only"])
            self.assertEqual(
                execution["candidate_pack_integrity_validation_scope"],
                "candidate_capture_pack_integrity_only",
            )
            self.assertFalse(
                execution[
                    "candidate_pack_integrity_validated_counts_as_approved_runtime_evidence"
                ]
            )
            self.assertFalse(execution["candidate_pack_integrity_validated_counts_as_runtime_evidence"])
            self.assertFalse(execution["candidate_pack_integrity_validated_counts_as_sdk_progress"])
            self.assertFalse(execution["candidate_pack_integrity_validated_counts_as_p0_progress"])
            self.assertFalse(execution["counts_as_approved_runtime_evidence"])
            self.assertFalse(execution["counts_as_sdk_progress"])
            self.assertFalse(execution["authorizes_live_ops"])
            self.assertFalse(execution["authorizes_live_log_reads"])
            self.assertFalse(execution["authorizes_marker_env_writes"])
            self.assertFalse(report["multi_surface_beta_capture_pack_counts_as_approved_runtime_evidence"])
            self.assertFalse(report["multi_surface_beta_capture_pack_authorizes_live_ops"])
            self.assertFalse(report["multi_surface_beta_capture_pack_authorizes_live_log_reads"])
            self.assertFalse(report["runtime_capture_authorized"])
            self.assertFalse(report["approved_runtime_evidence_ready"])
            self.assert_multi_surface_boundary(execution["boundary"])

    def test_default_report_dir_is_disambiguated_by_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            now_utc = future_now_utc()
            first = subprocess.run(
                executor_args_without_report_dir(
                    root / "ragnarok-live-validation-logs",
                    instance="arkserver",
                    map_name="Ragnarok",
                    now_utc=now_utc,
                ),
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            second = subprocess.run(
                executor_args_without_report_dir(
                    root / "theisland-live-validation-logs",
                    instance="arkserver2",
                    map_name="TheIsland",
                    now_utc=now_utc,
                ),
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            first_report = json.loads(first.stdout)
            second_report = json.loads(second.stdout)
            first_report_dir = Path(first_report["report_dir"])
            second_report_dir = Path(second_report["report_dir"])
            self.addCleanup(shutil.rmtree, first_report_dir, ignore_errors=True)
            self.addCleanup(shutil.rmtree, second_report_dir, ignore_errors=True)

            self.assertEqual(first_report["run_id"], second_report["run_id"])
            self.assertNotEqual(first_report_dir, second_report_dir)
            self.assertIn("arkserver-ragnarok", first_report_dir.name)
            self.assertIn("arkserver2-theisland", second_report_dir.name)
            self.assertTrue((first_report_dir / "window-request.check.json").is_file())
            self.assertTrue((second_report_dir / "window-request.check.json").is_file())

    def test_theisland_retry_after_closed_window_uses_fresh_execution_sidecars_and_sibling_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "live-validation-logs"
            report_dir = root / "theisland-reports"
            now_utc = future_now_utc()
            args = base_args(output_root, report_dir, now_utc=now_utc)
            args[args.index("--instance") + 1] = "arkserver2"
            args[args.index("--map") + 1] = "TheIsland"
            result = subprocess.run(
                args,
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["target"], {"instance": "arkserver2", "map": "TheIsland"})
        self.assertEqual(report["run_id"], run_id_for_now_utc(now_utc))
        self.assertNotEqual(report["run_id"], PREVIOUS_THEISLAND_RUN_ID)
        retry = report["fresh_retry_after_closed_non_evidence_window"]
        self.assertEqual(retry["schema"], FRESH_RETRY_SCHEMA)
        self.assertEqual(
            retry["status"],
            "fresh_theisland_retry_prepared_after_expired_non_evidence_window",
        )
        self.assertTrue(retry["target_matches_previous_theisland_window"])
        self.assertTrue(retry["previous_window_preserved_as_non_evidence"])
        self.assertTrue(retry["fresh_retry_allowed_without_reusing_previous_window"])
        self.assertFalse(retry["previous_window_reuse_allowed"])
        self.assertFalse(retry["previous_sibling_set_reuse_allowed"])
        self.assertFalse(retry["previous_notice_sidecars_reuse_allowed"])
        self.assertFalse(retry["previous_start_end_reuse_allowed"])
        self.assertFalse(retry["previous_run_counts_as_approved_runtime_evidence"])
        previous = retry["previous_window"]
        self.assertEqual(previous["run_id_stem"], PREVIOUS_THEISLAND_RUN_ID_STEM)
        self.assertEqual(previous["run_id"], PREVIOUS_THEISLAND_RUN_ID)
        self.assertEqual(previous["target"], {"instance": "arkserver2", "map": "TheIsland"})
        self.assertEqual(previous["target_key"], "arkserver2:TheIsland:27016")
        self.assertEqual(previous["lifecycle_state"], "expired")
        self.assertFalse(previous["active"])
        self.assertTrue(previous["expired"])
        self.assertTrue(previous["closed"])
        self.assertTrue(previous["post_restart_closed_non_evidence_window"])
        self.assertFalse(previous["counts_as_approved_runtime_evidence"])
        fresh = retry["fresh_window"]
        self.assertEqual(fresh["run_id"], report["run_id"])
        self.assertEqual(fresh["target"], report["target"])
        self.assertEqual(fresh["target_key"], "arkserver2:TheIsland:27016")
        self.assertEqual(fresh["sibling_set_root"], report["evidence_dir"])
        self.assertEqual(fresh["evidence_dir"], report["evidence_dir"])
        self.assertEqual(fresh["report_dir"], report["report_dir"])
        self.assertTrue(fresh["uses_own_sibling_set"])
        self.assertTrue(fresh["start_end_bound_to_fresh_run"])
        self.assertTrue(fresh["exact_target_bound"])
        self.assertEqual(fresh["start_utc"], report["approved_window"]["start_utc"])
        self.assertEqual(fresh["end_utc"], report["approved_window"]["end_utc"])
        self.assertFalse(fresh["previous_sibling_set_reuse_allowed"])
        self.assertFalse(fresh["previous_notice_sidecars_reuse_allowed"])
        self.assertFalse(fresh["previous_start_end_reuse_allowed"])
        self.assertNotIn(PREVIOUS_THEISLAND_RUN_ID, fresh["evidence_dir"])
        for required in (
            "window-request.json",
            "observer-window.env",
            "operator-approval-request.md",
            "operator-approval-receipt.json",
            "preflight-pre.json",
            "preflight-post.json",
            "window-manifest.env",
            "Obelisk.log",
            "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
        ):
            self.assertIn(required, fresh["required_sibling_set"])
        self.assertEqual(
            fresh["sibling_paths"]["window_request_json"],
            str(Path(report["evidence_dir"]) / "window-request.json"),
        )
        self.assertEqual(
            fresh["notice_sidecar_paths"]["beta_notice_dry_run_sidecar_json"],
            report["output_paths"]["dry_run_notice_sidecar"],
        )
        self.assertEqual(
            fresh["notice_sidecar_paths"]["beta_notice_confirmed_sidecar_json"],
            report["output_paths"]["confirmed_notice_sidecar_expected"],
        )
        self.assertEqual(
            report["execution_boundaries"]["fresh_retry_after_closed_non_evidence_window"],
            retry,
        )
        self.assertEqual(
            report["prepared_artifacts"]["fresh_retry_after_closed_non_evidence_window"],
            retry,
        )

    def test_next_action_sequence_is_deterministic_when_request_pack_is_reused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "live-validation-logs"
            report_dir = root / "reports"
            now_utc = future_now_utc()
            first = run_executor(output_root, report_dir, now_utc=now_utc)
            second = run_executor(output_root, report_dir, now_utc=now_utc)
            first_report = json.loads(first.stdout)
            second_report = json.loads(second.stdout)

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertTrue(second_report["steps"][0]["reused_existing_request_pack"])
        self.assertEqual(first_report["next_action_sequence"], second_report["next_action_sequence"])

    def test_diagnostic_candidates_request_pack_is_rejected_for_approved_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "live-validation-logs"
            report_dir = root / "reports"
            now_utc = future_now_utc()
            result = run_executor(
                output_root,
                report_dir,
                "--diagnostic-candidates",
                now_utc=now_utc,
            )
            report = json.loads(result.stdout)
            evidence_dir = Path(report["evidence_dir"])
            request_json = Path(report["request_pack_path"])
            request = json.loads(request_json.read_text(encoding="utf-8"))
            observer_env = (evidence_dir / "observer-window.env").read_text(encoding="utf-8").splitlines()

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(report["status"], "offline_preactivation_failed")
        self.assertEqual(report["next_blocker"], "diagnostic_candidates_for_approved_evidence_window")
        self.assertTrue(report["diagnostic_candidates_requested"])
        self.assertTrue(report["diagnostic_candidates_enabled_in_request_pack"])
        self.assertTrue(report["diagnostic_candidates"]["enabled_in_request_pack"])
        self.assertTrue(request["diagnostic_candidates_enabled"])
        self.assertIn(DIAGNOSTIC_ENV_LINE, observer_env)
        diagnostic = report["diagnostic_candidates"]
        self.assertEqual(diagnostic["mode"], "candidate_only_non_evidence")
        self.assertEqual(diagnostic["bounds"]["max_duration_seconds"], 900)
        self.assertEqual(diagnostic["bounds"]["dispatch_limit"], 0)
        self.assertEqual(diagnostic["bounds"]["log_limit"], 10)
        self.assertFalse(diagnostic["raw_player_text_allowed"])
        self.assertFalse(diagnostic["raw_player_identity_allowed"])
        self.assertFalse(diagnostic["raw_player_text_or_identity_allowed"])
        self.assertTrue(diagnostic["approved_evidence_window_rejected"])
        self.assertEqual(
            diagnostic["approved_evidence_blockers"],
            [
                "diagnostic_candidates_for_approved_evidence_window",
                "observer_env_diagnostic_candidates_for_approved_evidence_window",
                "observer_env_diagnostic_keys_for_approved_evidence_window",
            ],
        )
        self.assertTrue(diagnostic["approved_evidence_policy"]["observer_env_contains_diagnostic_candidates"])
        self.assertEqual(
            diagnostic["approved_evidence_policy"]["observer_env_diagnostic_keys_present"],
            ["OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES"],
        )
        self.assertFalse(diagnostic["diagnostic_candidate_lines_promotable_for_approved_evidence"])
        self.assertTrue(diagnostic["source_log_contains_lifecycle_diagnostic_lines_blocks_approved_evidence"])
        self.assertFalse(diagnostic["counts_as_runtime_evidence"])
        self.assertFalse(diagnostic["counts_as_approved_runtime_evidence"])
        self.assertFalse(diagnostic["readiness_claim_allowed"])
        diagnostic_policy = report["diagnostic_candidates_for_approved_evidence"]
        self.assertTrue(diagnostic_policy["approved_evidence_window_rejected"])
        self.assertTrue(diagnostic_policy["request_enabled"])
        self.assertFalse(diagnostic_policy["request_explicitly_disabled"])
        self.assertTrue(diagnostic_policy["observer_env_contains_diagnostic_candidates"])
        self.assertEqual(
            diagnostic_policy["observer_env_diagnostic_keys_present"],
            ["OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES"],
        )
        self.assertEqual(
            report["diagnostic_candidates_approved_evidence_blockers"],
            [
                "diagnostic_candidates_for_approved_evidence_window",
                "observer_env_diagnostic_candidates_for_approved_evidence_window",
                "observer_env_diagnostic_keys_for_approved_evidence_window",
            ],
        )
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["stable_claim_allowed"])

    def test_request_pack_reuse_requires_matching_diagnostic_candidate_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "live-validation-logs"
            report_dir = root / "reports"
            now_utc = future_now_utc()
            first = run_executor(
                output_root,
                report_dir,
                "--diagnostic-candidates",
                now_utc=now_utc,
            )
            self.assertEqual(first.returncode, 1, first.stderr)

            second = run_executor(output_root, report_dir, now_utc=now_utc)
            report = json.loads(second.stdout)
            evidence_dir = Path(report["evidence_dir"])
            request = json.loads((evidence_dir / "window-request.json").read_text(encoding="utf-8"))
            observer_env = (evidence_dir / "observer-window.env").read_text(encoding="utf-8").splitlines()

            third = run_executor(
                output_root,
                report_dir,
                "--diagnostic-candidates",
                now_utc=now_utc,
            )
            diagnostic_report = json.loads(third.stdout)
            diagnostic_evidence_dir = Path(diagnostic_report["evidence_dir"])
            diagnostic_request = json.loads(
                (diagnostic_evidence_dir / "window-request.json").read_text(encoding="utf-8")
            )
            diagnostic_env = (
                diagnostic_evidence_dir / "observer-window.env"
            ).read_text(encoding="utf-8").splitlines()

        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertNotIn("reused_existing_request_pack", report["steps"][0])
        self.assertFalse(report["diagnostic_candidates_requested"])
        self.assertFalse(report["diagnostic_candidates_enabled_in_request_pack"])
        self.assertFalse(request["diagnostic_candidates_enabled"])
        self.assertNotIn(DIAGNOSTIC_ENV_LINE, observer_env)
        self.assertEqual(third.returncode, 1, third.stderr)
        self.assertNotIn("reused_existing_request_pack", diagnostic_report["steps"][0])
        self.assertEqual(
            diagnostic_report["next_blocker"],
            "diagnostic_candidates_for_approved_evidence_window",
        )
        self.assertTrue(diagnostic_report["diagnostic_candidates_requested"])
        self.assertTrue(diagnostic_report["diagnostic_candidates_enabled_in_request_pack"])
        self.assertTrue(diagnostic_request["diagnostic_candidates_enabled"])
        self.assertIn(DIAGNOSTIC_ENV_LINE, diagnostic_env)

    def test_runs_activation_preconditions_with_supplied_confirmed_notice_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "live-validation-logs"
            report_dir = root / "reports"
            now_utc = future_now_utc()
            first = run_executor(output_root, report_dir, now_utc=now_utc)
            self.assertEqual(first.returncode, 0, first.stderr)
            first_report = json.loads(first.stdout)
            request_json = Path(first_report["request_pack_path"])
            confirmed_notice = report_dir / "beta-notice.confirmed.json"
            write_confirmed_notice(root=root, request_json=request_json, confirmed_notice=confirmed_notice)

            second = run_executor(
                output_root,
                report_dir,
                "--confirmed-notice-report-json",
                str(confirmed_notice),
                now_utc=now_utc,
            )
            report = json.loads(second.stdout)

            self.assertTrue(report["activation_preconditions_attempted"])
            self.assertTrue(report["steps"][0]["reused_existing_request_pack"])
            if second.returncode != 0:
                activation = json.loads(
                    (report_dir / "activation-preconditions.json").read_text(encoding="utf-8")
                )
                self.assertEqual(report["status"], "offline_activation_preconditions_blocked")
                self.assertFalse(report["activation_preconditions_checked"])
                self.assertFalse(report["activation_preconditions_ready"])
                self.assertFalse(report["activation_preconditions_offline_ready"])
                self.assertEqual(
                    report["activation_preconditions_ready_scope"],
                    "blocked_notice_binding_not_checked",
                )
                allowed_blockers = {
                    "route_gate_not_valid",
                    "beta_notice_standing_launch_authority_coverage_mismatch",
                    "guarded_beta_notice_action_standing_launch_authority_coverage_mismatch",
                }
                self.assertTrue(activation["blockers"])
                self.assertTrue(set(activation["blockers"]).issubset(allowed_blockers))
                self.assertFalse(report["runtime_capture_authorized"])
                self.assertFalse(report["approved_runtime_evidence_ready"])
                return

            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(report["status"], "offline_activation_preconditions_satisfied")
            self.assertTrue(report["activation_preconditions_checked"])
            self.assertTrue(report["activation_preconditions_ready"])
            self.assertTrue(report["activation_preconditions_offline_ready"])
            self.assertEqual(report["activation_preconditions_ready_scope"], "offline_pre_activation_consistency_only")
            self.assertEqual(
                report["next_blocker"],
                "offline_preconditions_consistent_external_action_scope_required",
            )
            self.assertIn("activation_preconditions", report["executed_step_ids"])
            self.assertTrue((report_dir / "activation-preconditions.json").is_file())
            self.assertEqual(report["activation_preconditions_json"], str(report_dir / "activation-preconditions.json"))
            self.assertEqual(
                [item["id"] for item in report["next_action_sequence"]],
                [
                    "review_offline_outputs",
                    "safe_restart_warn_or_reschedule",
                    "active_observation_window",
                    "capture_required_sibling_sidecars",
                    "restore_stable_posture_and_verify",
                ],
            )
            self.assert_runner_actions_common(report)
            stale_prevention = report["runtime_window_stale_prevention"]
            self.assertEqual(stale_prevention["blockers"], [])
            self.assertTrue(stale_prevention["enough_future_lead_time"])
            self.assertTrue(report["beta_notice_sequence_enforcement"]["confirmed_beta_notice_required_before_activation"])
            restart_action = report["next_action_sequence"][1]
            self.assertTrue(restart_action["separate_operator_authorization_required"])
            self.assertEqual(restart_action["authority_source"], "recorded_standing_launch_authority")
            self.assertFalse(restart_action["standing_authority_authorizes_server_restart"])
            self.assertFalse(restart_action["standing_authority_authorizes_discord_send"])
            self.assertEqual(
                restart_action["blocked_until"],
                [
                    "beta_notice_dry_run_reviewed",
                    "confirmed_beta_notice_report_consumed",
                    "activation_preconditions_ready",
                    "request_window_start_in_future",
                ],
            )
            self.assertTrue(restart_action["beta_notice_dry_run_required_before_activation"])
            self.assertTrue(restart_action["confirmed_beta_notice_required_before_activation"])
            self.assertTrue(restart_action["activation_preconditions_required_before_activation_or_restart"])
            self.assertFalse(restart_action["activation_or_restart_from_stale_request_allowed"])
            self.assertFalse(restart_action["monitor_or_restart_activation_after_window_start_allowed"])
            self.assertEqual(restart_action["runtime_window_stale_prevention"], stale_prevention)
            self.assertEqual(restart_action["two_server_cap_policy"]["max_running_ark_servers"], 2)
            self.assertTrue(restart_action["player_presence_safety"]["connected_player_check_required_before_restart"])
            broadcast = restart_action["player_warning_broadcast_recommendation"]
            self.assertTrue(broadcast["connected_player_check_required_before_restart"])
            self.assertTrue(broadcast["broadcast_recommended_if_players_connected"])
            self.assertTrue(broadcast["cancel_or_reschedule_if_players_remain_connected"])
            self.assertFalse(broadcast["request_pack_authorizes_player_check_or_broadcast"])
            self.assertFalse(broadcast["broadcast_performed_by_executor"])
            self.assertTrue(broadcast["recommended_text_already_redacted"])
            self.assertFalse(broadcast["raw_player_text_allowed"])
            self.assertFalse(broadcast["secret_or_webhook_output_allowed"])
            self.assertIn("CheckJoinInProgress(1,0)", broadcast["recommended_discord_text_redacted"])
            self.assertNotIn("discord.com\x2fapi/webhooks", broadcast["recommended_discord_text_redacted"])
            self.assertIn("monitor_ark_player_presence_passive.sh", broadcast["connected_player_check_command_not_executed"])
            self.assertEqual(
                restart_action["runner_contract"]["side_effect_domain"],
                "player_presence_restart_safety",
            )
            self.assertEqual(
                restart_action["runner_operation"]["safety"]["player_warning_broadcast_recommendation"],
                broadcast,
            )
            observation_action = report["next_action_sequence"][2]
            self.assertEqual(observation_action["target"], {"instance": "arkserver3", "map": "Genesis2"})
            self.assertTrue(observation_action["separate_operator_authorization_required"])
            self.assertFalse(observation_action["standing_authority_authorizes_marker_env_changes"])
            self.assertFalse(observation_action["standing_authority_authorizes_runtime_evidence"])
            self.assertEqual(observation_action["blocked_until"], restart_action["blocked_until"])
            self.assertFalse(observation_action["activation_or_restart_from_stale_request_allowed"])
            self.assertEqual(observation_action["runtime_window_stale_prevention"], stale_prevention)
            self.assertEqual(
                observation_action["lifecycle_missing_role_objectives"]["objective_ids"],
                ["session_start", "CheckJoinInProgress(1,0)", "session_end"],
            )
            self.assertIn(
                "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10",
                observation_action["marker_env_gates"]["env_snapshot"],
            )
            self.assertEqual(
                observation_action["runner_operation"]["inputs"]["marker_env_gates"],
                observation_action["marker_env_gates"],
            )
            self.assertFalse(
                observation_action["runner_operation"]["safety"]["marker_env_changes_performed_by_executor"]
            )
            sidecar_action = report["next_action_sequence"][3]
            self.assertIn("preflight_pre_json", sidecar_action["required_evidence_paths"])
            self.assertIn("copied_obelisk_log", sidecar_action["required_evidence_paths"])
            preconditions = sidecar_action["post_window_copy_bundle_preconditions"]
            self.assertTrue(sidecar_action["dry_run_first_required"])
            self.assertTrue(sidecar_action["dry_run_must_complete_before_execute"])
            self.assertEqual(
                sidecar_action["required_dry_run_artifacts"],
                [report["output_paths"]["post_window_next_actions_dry_run_report"]],
            )
            self.assertEqual(preconditions["schema"], "obelisk.player-principal-lifecycle-post-window-action-contract.v1")
            self.assertIn("Obelisk.log", preconditions["expected_sibling_set"])
            self.assertIn("window-manifest.env", preconditions["expected_sibling_set"])
            self.assertIn(
                "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
                preconditions["expected_sibling_set"],
            )
            self.assertEqual(sidecar_action["ordered_copied_log_route_step_ids"], COPIED_LOG_ROUTE_STEPS)
            self.assert_copied_log_route(sidecar_action["copied_log_route_required"])
            self.assertEqual(preconditions["ordered_copied_log_route_step_ids"], COPIED_LOG_ROUTE_STEPS)
            self.assert_copied_log_route(preconditions["copied_log_route_required"])
            pipeline = preconditions["evidence_pipeline_command_sequence"]
            self.assert_evidence_pipeline(pipeline)
            self.assertEqual(sidecar_action["evidence_pipeline_command_sequence"], pipeline)
            self.assertEqual(
                report["execution_boundaries"]["evidence_pipeline_command_sequence"][
                    "ordered_step_ids"
                ],
                pipeline["ordered_step_ids"],
            )
            self.assertFalse(preconditions["sidecar_generation_authorized_by_this_report"])
            self.assertFalse(preconditions["dry_run_report_authorizes_runtime"])
            self.assertFalse(preconditions["counts_as_approved_runtime_evidence"])
            self.assertEqual(
                sidecar_action["runner_operation"]["inputs"]["required_evidence_paths"],
                sidecar_action["required_evidence_paths"],
            )
            self.assertEqual(
                sidecar_action["runner_operation"]["inputs"]["evidence_pipeline_command_sequence"],
                pipeline,
            )
            self.assertEqual(
                sidecar_action["runner_operation"]["inputs"]["post_window_action_contract"],
                preconditions,
            )
            self.assertFalse(sidecar_action["runner_operation"]["safety"]["counts_as_approved_runtime_evidence"])
            self.assertTrue(sidecar_action["runner_operation"]["safety"]["dry_run_first_required"])
            self.assertFalse(sidecar_action["runner_operation"]["safety"]["restart_recommended"])
            self.assertFalse(sidecar_action["runner_operation"]["safety"]["raw_player_text_or_identity_allowed"])
            self.assertFalse(report["runtime_capture_authorized"])
            self.assertFalse(report["approved_runtime_evidence_ready"])

    def test_executor_rejects_direct_bot_stdout_and_active_notice_state_as_activation_inputs(
        self,
    ) -> None:
        cases = [
            (
                "direct-bot-stdout.json",
                write_direct_bot_notice_stdout,
                "direct_bot_notice_report_not_activation_notice",
            ),
            (
                "active-notice-state.json",
                lambda *, request_json, notice_path: write_active_notice_state(notice_path),
                "active_notice_state_not_activation_notice",
            ),
        ]
        for filename, writer, blocker in cases:
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                output_root = root / "live-validation-logs"
                report_dir = root / "reports"
                now_utc = future_now_utc()
                first = run_executor(output_root, report_dir, now_utc=now_utc)
                self.assertEqual(first.returncode, 0, first.stderr)
                first_report = json.loads(first.stdout)
                request_json = Path(first_report["request_pack_path"])
                supplied_notice = report_dir / filename
                writer(request_json=request_json, notice_path=supplied_notice)

                second = run_executor(
                    output_root,
                    report_dir,
                    "--confirmed-notice-report-json",
                    str(supplied_notice),
                    now_utc=now_utc,
                )
                report = json.loads(second.stdout)
                activation = json.loads(
                    (report_dir / "activation-preconditions.json").read_text(encoding="utf-8")
                )

                self.assertNotEqual(second.returncode, 0)
                self.assertEqual(report["status"], "offline_activation_preconditions_blocked")
                self.assertTrue(report["activation_preconditions_attempted"])
                self.assertFalse(report["activation_preconditions_checked"])
                self.assertFalse(report["activation_preconditions_ready"])
                self.assertFalse(report["activation_preconditions_offline_ready"])
                self.assertEqual(
                    report["activation_preconditions_ready_scope"],
                    "blocked_notice_binding_not_checked",
                )
                self.assertEqual(report["next_blocker"], "activation_preconditions_missing")
                self.assertIn("activation_preconditions", report["executed_step_ids"])
                self.assertEqual(report["notice_report_json_for_activation"], str(supplied_notice))
                self.assertFalse(report["runtime_capture_authorized"])
                self.assertFalse(report["approved_runtime_evidence_ready"])
                self.assertFalse(activation["activation_preconditions_checked"])
                self.assertIn(blocker, activation["blockers"])

    def test_refuses_to_overwrite_request_pack_bound_to_confirmed_notice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "live-validation-logs"
            report_dir = root / "reports"
            now_utc = future_now_utc()
            first = run_executor(output_root, report_dir, now_utc=now_utc)
            self.assertEqual(first.returncode, 0, first.stderr)
            first_report = json.loads(first.stdout)
            request_json = Path(first_report["request_pack_path"])
            confirmed_notice = report_dir / "beta-notice.confirmed.json"
            write_confirmed_notice(root=root, request_json=request_json, confirmed_notice=confirmed_notice)
            original_request = request_json.read_text(encoding="utf-8")

            second = subprocess.run(
                [
                    *base_args(output_root, report_dir, now_utc=now_utc),
                    "--map",
                    "Ragnarok",
                    "--confirmed-notice-report-json",
                    str(confirmed_notice),
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(second.returncode, 0)
            self.assertIn("refusing to mutate existing request pack bound to confirmed notice", second.stderr)
            self.assertEqual(request_json.read_text(encoding="utf-8"), original_request)

    def test_refuses_to_overwrite_request_pack_bound_to_confirmed_notice_sidecar_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "live-validation-logs"
            report_dir = root / "reports"
            now_utc = future_now_utc()
            first = run_executor(output_root, report_dir, now_utc=now_utc)
            self.assertEqual(first.returncode, 0, first.stderr)
            first_report = json.loads(first.stdout)
            request_json = Path(first_report["request_pack_path"])
            confirmed_notice = report_dir / "beta-notice.confirmed.json"
            write_confirmed_notice(root=root, request_json=request_json, confirmed_notice=confirmed_notice)
            confirmed_sidecar = confirmed_notice.with_suffix(".sidecar.json")
            self.assertTrue(confirmed_sidecar.is_file())
            confirmed_notice.unlink()
            original_request = request_json.read_text(encoding="utf-8")

            second = subprocess.run(
                [
                    *base_args(output_root, report_dir, now_utc=now_utc),
                    "--map",
                    "Ragnarok",
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(second.returncode, 0)
            self.assertIn("refusing to mutate existing request pack bound to confirmed notice", second.stderr)
            self.assertEqual(request_json.read_text(encoding="utf-8"), original_request)

    def test_stdout_only_confirmed_notice_does_not_bind_request_pack_for_reuse_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "live-validation-logs"
            report_dir = root / "reports"
            now_utc = future_now_utc()
            first = run_executor(output_root, report_dir, now_utc=now_utc)
            self.assertEqual(first.returncode, 0, first.stderr)
            first_report = json.loads(first.stdout)
            request_json = Path(first_report["request_pack_path"])
            confirmed_notice = report_dir / "beta-notice.confirmed.json"
            write_confirmed_notice(root=root, request_json=request_json, confirmed_notice=confirmed_notice)
            confirmed_notice.with_suffix(".sidecar.json").unlink()
            original_request = request_json.read_text(encoding="utf-8")

            second = subprocess.run(
                [
                    *base_args(output_root, report_dir, now_utc=now_utc),
                    "--map",
                    "Ragnarok",
                    "--confirmed-notice-report-json",
                    str(confirmed_notice),
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotIn("refusing to mutate existing request pack bound to confirmed notice", second.stderr)
            self.assertNotEqual(request_json.read_text(encoding="utf-8"), original_request)

    def test_rejects_protected_report_dir_outside_offline_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_executor(
                Path(tmp) / "live-validation-logs",
                Path("/servidor/ark/serverfiles/runtime-window-reports"),
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--report-dir must be outside /servidor/ark or under /servidor/ark/workspace-offline", result.stderr)

    def test_post_window_state_only_consumes_closure_report_exact_missing_roles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "live-validation-logs"
            report_dir = root / "reports"
            closure_path = root / "closure.json"
            evidence_dir = output_root / "20260606T100000Z-player-principal-lifecycle"
            write_json(closure_path, closure_report_payload(evidence_dir=evidence_dir))

            result = run_executor(
                output_root,
                report_dir,
                "--post-window-state-json",
                str(closure_path),
                "--post-window-state-only",
            )
            report = json.loads(result.stdout)
            state = report["post_window_state"]

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(report_dir.exists())
        self.assertEqual(report["status"], "post_window_state_consumed_non_evidence")
        self.assertTrue(report["post_window_state_checked"])
        self.assertEqual(state["source_kind"], "closure_request_report")
        self.assertEqual(state["source_schema"], CLOSURE_SCHEMA)
        self.assertEqual(state["exact_missing_required_artifacts"], [])
        self.assertEqual(state["exact_missing_lifecycle_event_roles"], ["session_end"])
        self.assertEqual(state["lifecycle_missing_role_objectives"]["missing_lifecycle_event_roles"], ["session_end"])
        self.assertEqual(
            state["lifecycle_missing_role_objectives"]["objective_ids"],
            ["session_start", "CheckJoinInProgress(1,0)", "session_end"],
        )
        self.assertEqual(
            state["manual_step"]["lifecycle_missing_role_objectives"]["missing_lifecycle_event_roles"],
            ["session_end"],
        )
        self.assertEqual(state["manual_step"]["ordered_copied_log_route_step_ids"], COPIED_LOG_ROUTE_STEPS)
        self.assert_copied_log_route(state["manual_step"]["copied_log_route_required"])
        self.assertEqual(state["next_blocker"], "post_window_lifecycle_event_roles_missing")
        self.assertEqual(report["next_blocker"], "post_window_lifecycle_event_roles_missing")
        self.assertEqual(
            [action["id"] for action in report["next_action_sequence"]],
            ["review_post_window_state_input", "manual_post_window_followup"],
        )
        for action in report["next_action_sequence"]:
            self.assertEqual(action["ordered_copied_log_route_step_ids"], COPIED_LOG_ROUTE_STEPS)
            self.assert_copied_log_route(action["copied_log_route_required"])
        self.assertFalse(state["approved_runtime_evidence_present"])
        self.assertFalse(state["closure_report_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["current_turn_approval_claimed_by_executor"])
        self.assertFalse(state["authority_boundary"]["current_turn_approval_claimed_by_executor"])

    def test_post_window_state_only_preserves_previous_theisland_window_as_stale_non_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "live-validation-logs"
            report_dir = root / "reports"
            previous_evidence_dir = output_root / PREVIOUS_THEISLAND_RUN_ID
            closure_path = root / "previous-theisland-closure.json"
            closure = closure_report_payload(evidence_dir=previous_evidence_dir)
            closure["closure_case"] = "post_restart_closed_theisland_non_evidence"
            closure["target"] = {
                "instance": "arkserver2",
                "map": "TheIsland",
                "query_port": "27016",
                "target_key": "arkserver2:TheIsland:27016",
            }
            write_json(closure_path, closure)
            args = base_args(output_root, report_dir, now_utc=future_now_utc())
            args[args.index("--instance") + 1] = "arkserver2"
            args[args.index("--map") + 1] = "TheIsland"
            args.extend([
                "--post-window-state-json",
                str(closure_path),
                "--post-window-state-only",
            ])
            result = subprocess.run(
                args,
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            report = json.loads(result.stdout)
            state = report["post_window_state"]
            source = state["post_window_source_boundary"]

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(report_dir.exists())
        retry = report["fresh_retry_after_closed_non_evidence_window"]
        self.assertEqual(retry["schema"], FRESH_RETRY_SCHEMA)
        self.assertTrue(retry["target_matches_previous_theisland_window"])
        self.assertTrue(retry["previous_window_preserved_as_non_evidence"])
        self.assertFalse(retry["previous_run_counts_as_approved_runtime_evidence"])
        self.assertEqual(retry["previous_window"]["run_id"], PREVIOUS_THEISLAND_RUN_ID)
        self.assertEqual(retry["previous_window"]["lifecycle_state"], "expired")
        self.assertTrue(retry["previous_window"]["expired"])
        self.assertFalse(retry["previous_window"]["active"])
        self.assertEqual(source["classification"], "stale_post_window_source_only_non_evidence")
        self.assertEqual(source["source_run_ids"], [PREVIOUS_THEISLAND_RUN_ID])
        self.assertTrue(source["source_run_id_mismatches_plan"])
        self.assertTrue(source["source_is_stale"])
        self.assertTrue(source["source_only_non_evidence"])
        self.assertFalse(source["source_accepted_as_closure_evidence_dir"])
        self.assertFalse(source["source_counts_as_approved_runtime_evidence"])
        self.assertFalse(state["closure_report_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertEqual(state["target"], closure["target"])

    def test_post_window_state_only_consumes_passive_summary_without_artifact_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "live-validation-logs"
            report_dir = root / "reports"
            passive_path = root / "passive-summary.json"
            write_json(passive_path, passive_latest_payload())

            result = run_executor(
                output_root,
                report_dir,
                "--post-window-state-json",
                str(passive_path),
                "--post-window-state-only",
            )
            report = json.loads(result.stdout)
            state = report["post_window_state"]

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(state["source_kind"], "passive_summary")
        self.assertEqual(state["source_classification"], "passive_monitor_source_only_non_evidence")
        self.assertTrue(state["source_only_non_evidence"])
        self.assertTrue(state["post_window_source_boundary"]["source_is_passive_summary"])
        self.assertFalse(
            state["post_window_source_boundary"]["source_counts_as_approved_runtime_evidence"]
        )
        self.assertTrue(state["passive_target_found"])
        self.assertEqual(state["artifact_gap_scope"], "not_inspected_by_passive_summary")
        self.assertEqual(state["role_gap_scope"], "passive_summary_exact_target")
        self.assertEqual(state["exact_missing_required_artifacts"], [])
        self.assertEqual(state["next_required_artifact"], "closure_report_or_bundle_preflight_required_for_exact_artifact_gaps")
        self.assertEqual(state["exact_missing_lifecycle_event_roles"], ["session_end"])
        self.assertEqual(state["lifecycle_missing_role_objectives"]["missing_lifecycle_event_roles"], ["session_end"])
        self.assertEqual(
            state["lifecycle_missing_role_objectives"]["objective_ids"],
            ["session_start", "CheckJoinInProgress(1,0)", "session_end"],
        )
        self.assertEqual(state["next_blocker"], "post_window_lifecycle_event_roles_missing")
        self.assertFalse(state["passive_summary_counts_as_approved_runtime_evidence"])
        self.assertFalse(state["passive_complete_triplets_count_as_approved_runtime_evidence"])
        self.assertFalse(report["passive_monitor_counts_as_approved_runtime_evidence"])

    def test_post_window_state_only_no_users_prepares_passive_wait_diagnostic_window_without_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "live-validation-logs"
            report_dir = root / "reports"
            passive_path = root / "passive-no-users.json"
            write_json(passive_path, passive_no_users_payload())

            result = run_executor(
                output_root,
                report_dir,
                "--post-window-state-json",
                str(passive_path),
                "--post-window-state-only",
                "--diagnostic-candidates",
            )
            report = json.loads(result.stdout)
            state = report["post_window_state"]
            passive_wait = state["no_users_passive_wait"]
            next_window = state["next_player_backed_window"]
            actions = report["next_action_sequence"]

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(state["source_kind"], "passive_summary")
        self.assertTrue(state["passive_player_presence"]["no_users_detected"])
        self.assertTrue(state["passive_player_presence"]["no_users_confirmed"])
        self.assertFalse(state["passive_player_presence"]["unknown_player_context"])
        self.assertEqual(state["role_gap_scope"], "target_present_no_users_observed")
        self.assertEqual(state["exact_missing_lifecycle_event_roles"], [])
        self.assertEqual(state["next_blocker"], "no_users_passive_wait_for_player_backed_evidence")
        closure_root = state["closure_compatible_evidence_root"]
        self.assertTrue(closure_root["run_id_matches_closure_request"])
        self.assertEqual(closure_root["run_id"], report["run_id"])
        self.assertEqual(closure_root["evidence_dir"], report["evidence_dir"])
        self.assertTrue(closure_root["passive_monitor_roots_must_not_be_used_as_closure_evidence_dir"])
        self.assertTrue(closure_root["copy_required_before_evidence_closure"])
        self.assertFalse(closure_root["counts_as_approved_runtime_evidence"])
        self.assertTrue(passive_wait["passive_wait_preferred"])
        self.assertEqual(passive_wait["process_control"], "passive_wait_without_restart")
        self.assertTrue(passive_wait["repeated_restart_for_no_users_forbidden"])
        self.assertFalse(passive_wait["restart_recommended"])
        self.assertIn("--no-details", passive_wait["monitor_command_not_executed"])
        self.assertFalse(passive_wait["counts_as_approved_runtime_evidence"])
        self.assertEqual(passive_wait["closure_compatible_evidence_root"], closure_root)
        self.assertFalse(passive_wait["no_users_no_testers_passive_wait_counts_as_approved_runtime_evidence"])
        self.assertFalse(passive_wait["no_users_no_testers_passive_wait_counts_as_readiness"])
        self.assertFalse(passive_wait["no_users_no_testers_passive_wait_counts_as_progress"])
        self.assertFalse(passive_wait["no_users_no_testers_passive_wait_counts_as_authorization"])
        self.assertFalse(passive_wait["no_users_no_testers_passive_wait_counts_as_notice_sent"])
        self.assertEqual(next_window["restart_expectation"], "none")
        self.assertTrue(next_window["diagnostic_candidates_recommended"])
        self.assertTrue(next_window["should_enable_diagnostic_candidates_in_next_request_pack"])
        self.assertIn("--diagnostic-candidates", next_window["command_text_not_executed"])
        self.assertIn("--restart-expectation none", next_window["command_text_not_executed"])
        self.assertFalse(next_window["server_operations_authorized"])
        self.assertEqual(next_window["closure_compatible_evidence_root"], closure_root)
        self.assertFalse(next_window["no_users_no_testers_passive_wait_counts_as_approved_runtime_evidence"])
        self.assertFalse(next_window["no_users_no_testers_passive_wait_counts_as_readiness"])
        self.assertFalse(next_window["no_users_no_testers_passive_wait_counts_as_progress"])
        self.assertFalse(next_window["no_users_no_testers_passive_wait_counts_as_authorization"])
        self.assertFalse(next_window["no_users_no_testers_passive_wait_counts_as_notice_sent"])
        self.assertFalse(state["approved_evidence_bundle_checker_accepted"])
        self.assert_approved_bundle_requirement(state["approved_evidence_bundle_acceptance_requirement"])
        self.assertEqual(
            [action["id"] for action in actions],
            [
                "review_post_window_state_input",
                "continue_no_users_passive_wait_for_player_backed_evidence",
                "prepare_next_player_backed_diagnostic_window_without_restart",
            ],
        )
        wait_action = actions[1]
        self.assertEqual(wait_action["process_control"], "passive_wait_without_restart")
        self.assertTrue(wait_action["repeated_restart_for_no_users_forbidden"])
        self.assertFalse(wait_action["restart_recommended"])
        self.assertFalse(wait_action["authorized_by_this_report"])
        self.assertEqual(wait_action["closure_compatible_evidence_root"], closure_root)
        self.assertEqual(wait_action["prepared_action_mode"], "request_only")
        self.assertFalse(wait_action["no_users_no_testers_passive_wait_counts_as_notice_sent"])
        self.assert_approved_bundle_requirement(wait_action["approved_evidence_bundle_acceptance_requirement"])
        prep_action = actions[2]
        self.assertEqual(prep_action["restart_expectation"], "none")
        self.assertTrue(prep_action["diagnostic_candidates"]["should_enable_in_next_request_pack"])
        self.assertFalse(prep_action["start_or_restart_recommended"])
        self.assertEqual(prep_action["closure_compatible_evidence_root"], closure_root)
        self.assertEqual(prep_action["prepared_action_mode"], "request_only")
        self.assertFalse(prep_action["approved_evidence_bundle_checker_accepted"])
        self.assert_approved_bundle_requirement(prep_action["approved_evidence_bundle_acceptance_requirement"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["runtime_capture_authorized"])
        self.assertIn(
            "continue_no_users_passive_wait_for_player_backed_evidence",
            report["execution_boundaries"]["passive_waits"]["passive_wait_action_ids"],
        )
        self.assertFalse(
            report["execution_boundaries"]["passive_waits"][
                "passive_wait_counts_as_approved_runtime_evidence"
            ]
        )

    def test_post_window_state_labels_stale_passive_monitor_source_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "live-validation-logs"
            report_dir = root / "reports"
            stale_monitor_root = (
                root
                / "live-validation-logs"
                / "20260607T071833Z-postpatch-ragnarok-theisland-monitor"
            )
            passive_path = stale_monitor_root / "passive-summary.json"
            write_json(passive_path, passive_no_users_payload())

            result = run_executor(
                output_root,
                report_dir,
                "--post-window-state-json",
                str(passive_path),
                "--post-window-state-only",
            )
            report = json.loads(result.stdout)
            state = report["post_window_state"]
            source = state["post_window_source_boundary"]

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            source["classification"],
            "stale_passive_monitor_source_only_non_evidence",
        )
        self.assertTrue(source["source_looks_like_passive_monitor_root"])
        self.assertTrue(source["source_is_stale"])
        self.assertTrue(source["source_only_non_evidence"])
        self.assertFalse(source["source_authorizes_machine_action"])
        self.assertFalse(source["source_counts_as_approved_runtime_evidence"])
        self.assertFalse(source["passive_monitor_root_accepted_as_closure_evidence_dir"])
        self.assertEqual(state["source_classification"], source["classification"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(
            report["checker_required_post_window_replay"]["accepted_by_this_report"]
        )

    def test_post_window_state_only_query_warning_does_not_confirm_no_users(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "live-validation-logs"
            report_dir = root / "reports"
            passive_path = root / "passive-query-warning.json"
            payload = passive_no_users_payload()
            target_key = "arkserver3:Genesis2:27017"
            activity = payload["passive_monitor_activity_summary"]
            activity["targets_with_query_warning"] = [target_key]
            activity["query_warnings_by_target"] = {
                target_key: {"status": "timeout", "source": "rcon_listplayers"}
            }
            write_json(passive_path, payload)

            result = run_executor(
                output_root,
                report_dir,
                "--post-window-state-json",
                str(passive_path),
                "--post-window-state-only",
            )
            report = json.loads(result.stdout)
            presence = report["post_window_state"]["passive_player_presence"]

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(presence["unknown_player_context"])
        self.assertEqual(presence["unknown_player_count_targets"], [target_key])
        self.assertFalse(presence["no_users_detected"])
        self.assertFalse(presence["no_users_confirmed"])
        self.assertEqual(
            report["post_window_state"]["next_blocker"],
            "closure_report_required_for_exact_artifact_gaps",
        )

    def test_rejects_passive_notice_status_and_public_readiness_target_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--instance",
                    "passive-monitor",
                    "--map",
                    "public-readiness",
                    "--output-root",
                    str(root / "live-validation-logs"),
                    "--report-dir",
                    str(root / "reports"),
                    "--obelisk-commit",
                    TEST_COMMIT,
                    "--now-utc",
                    future_now_utc(),
                    "--json",
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "no-users, no-testers, passive-wait, notice, status, readiness, and public-readiness aliases are rejected",
            result.stderr,
        )
        self.assertIn("--instance=passive-monitor", result.stderr)
        self.assertIn("--map=public-readiness", result.stderr)

    def test_rejects_no_users_no_testers_and_passive_wait_target_aliases(self) -> None:
        cases = (
            ("no-users", "Genesis2"),
            ("arkserver3", "no-testers"),
            ("passive-wait", "Genesis2"),
        )
        for instance, map_name in cases:
            with self.subTest(instance=instance, map=map_name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                result = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--instance",
                        instance,
                        "--map",
                        map_name,
                        "--output-root",
                        str(root / "live-validation-logs"),
                        "--report-dir",
                        str(root / "reports"),
                        "--obelisk-commit",
                        TEST_COMMIT,
                        "--now-utc",
                        future_now_utc(),
                        "--json",
                    ],
                    cwd=REPO_ROOT,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "no-users, no-testers, passive-wait, notice, status, readiness, and public-readiness aliases are rejected",
                result.stderr,
            )

    def test_post_window_state_rejects_notice_executor_status_passive_and_public_readiness_aliases(self) -> None:
        schemas_and_reasons = (
            (NOTICE_SCHEMA, "notice_report_schema_is_not_post_window_state"),
            (EXECUTOR_SCHEMA, "executor_report_schema_is_not_post_window_state"),
            (STATUS_SCHEMA, "status_or_readiness_schema_is_not_post_window_state"),
            ("obelisk.player-principal-passive-status.v1", "passive_alias_schema_is_not_post_window_state"),
            (
                "obelisk.player-principal-public-readiness-status.v1",
                "public_readiness_schema_is_not_post_window_state",
            ),
        )
        for schema, reason in schemas_and_reasons:
            with self.subTest(schema=schema), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                payload_path = root / "alias.json"
                write_json(payload_path, {"schema": schema, "approved_runtime_evidence_ready": True})

                result = run_executor(
                    root / "live-validation-logs",
                    root / "reports",
                    "--post-window-state-json",
                    str(payload_path),
                    "--post-window-state-only",
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(reason, result.stderr)

    def test_post_window_state_rejects_closure_and_passive_monitor_evidence_shortcuts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "live-validation-logs"
            report_dir = root / "reports"
            closure_path = root / "closure-overclaim.json"
            closure = closure_report_payload(evidence_dir=output_root / "20260606T100000Z-player-principal-lifecycle")
            closure["approved_runtime_evidence_ready"] = True
            write_json(closure_path, closure)

            closure_result = run_executor(
                output_root,
                report_dir,
                "--post-window-state-json",
                str(closure_path),
                "--post-window-state-only",
            )

            passive_path = root / "passive-monitor-overclaim.json"
            passive = {
                "schema": PASSIVE_MONITOR_ONLY_SCHEMA,
                "approved_runtime_evidence": True,
            }
            write_json(passive_path, passive)
            passive_result = run_executor(
                output_root,
                report_dir,
                "--post-window-state-json",
                str(passive_path),
                "--post-window-state-only",
            )

        self.assertNotEqual(closure_result.returncode, 0)
        self.assertIn("runtime-evidence/authorization shortcut aliases", closure_result.stderr)
        self.assertNotEqual(passive_result.returncode, 0)
        self.assertIn("runtime-evidence/authorization shortcut aliases", passive_result.stderr)

    def test_post_window_state_rejects_generic_authority_readiness_aliases(self) -> None:
        cases = (
            (
                "closure-runtime-allowed.json",
                {
                    **closure_report_payload(evidence_dir=Path("/tmp") / "evidence"),
                    "runtimeAllowed": True,
                },
            ),
            (
                "closure-sdk-ready.json",
                {
                    **closure_report_payload(evidence_dir=Path("/tmp") / "evidence"),
                    "sdkReady": True,
                },
            ),
            (
                "passive-discord-send-allowed.json",
                {
                    "schema": PASSIVE_MONITOR_ONLY_SCHEMA,
                    "discordSendAllowed": True,
                },
            ),
            (
                "passive-notice-sent.json",
                {
                    "schema": PASSIVE_MONITOR_ONLY_SCHEMA,
                    "noticeDeliveryStatus": "sent",
                },
            ),
            (
                "passive-no-users-evidence.json",
                {
                    **passive_no_users_payload(),
                    "noUsersEvidence": True,
                },
            ),
            (
                "passive-no-testers-readiness.json",
                {
                    "schema": PASSIVE_MONITOR_ONLY_SCHEMA,
                    "noTestersReadiness": "ready",
                },
            ),
            (
                "passive-wait-progress.json",
                {
                    "schema": PASSIVE_MONITOR_ONLY_SCHEMA,
                    "passiveWaitProgress": 1,
                },
            ),
            (
                "passive-no-users-notice-sent.json",
                {
                    "schema": PASSIVE_MONITOR_ONLY_SCHEMA,
                    "noUsersNoticeSent": True,
                },
            ),
        )
        for filename, payload in cases:
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                payload_path = root / filename
                write_json(payload_path, payload)

                result = run_executor(
                    root / "live-validation-logs",
                    root / "reports",
                    "--post-window-state-json",
                    str(payload_path),
                    "--post-window-state-only",
                )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("runtime-evidence/authorization shortcut aliases", result.stderr)

    def test_post_window_state_rejects_multi_surface_capture_pack_family_as_state(self) -> None:
        schemas = (
            MULTI_SURFACE_PACK_SCHEMA,
            MULTI_SURFACE_PLAN_SCHEMA,
            MULTI_SURFACE_CHECKER_MATRIX_SCHEMA,
            MULTI_SURFACE_NON_CLAIM_MANIFEST_SCHEMA,
        )
        for schema in schemas:
            with self.subTest(schema=schema), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                payload_path = root / "multi-surface-candidate.json"
                write_json(
                    payload_path,
                    {
                        "schema": schema,
                        "status": "candidate_capture_pack",
                        "non_claim_flags": {
                            "candidate_only": True,
                            "counts_as_approved_runtime_evidence": False,
                            "authorizes_discord_send": False,
                            "authorizes_marker_or_env_changes": False,
                            "touches_live_servers": False,
                        },
                    },
                )

                result = run_executor(
                    root / "live-validation-logs",
                    root / "reports",
                    "--post-window-state-json",
                    str(payload_path),
                    "--post-window-state-only",
                )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "multi_surface_beta_capture_pack_family_is_candidate_metadata_not_post_window_state",
                result.stderr,
            )

    def test_post_window_state_rejects_nested_multi_surface_candidate_pack_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "live-validation-logs"
            report_dir = root / "reports"
            closure_path = root / "closure-with-candidate-pack-overclaim.json"
            closure = closure_report_payload(evidence_dir=output_root / "20260606T100000Z-player-principal-lifecycle")
            closure["multi_surface_beta_capture_pack_metadata"] = {
                "schema": MULTI_SURFACE_PACK_SCHEMA,
                "status": "candidate_capture_pack",
                "non_claim_flags": {
                    "candidate_only": True,
                    "touches_live_servers": True,
                    "counts_as_approved_runtime_evidence": False,
                },
            }
            write_json(closure_path, closure)

            result = run_executor(
                output_root,
                report_dir,
                "--post-window-state-json",
                str(closure_path),
                "--post-window-state-only",
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime-evidence/authorization shortcut aliases", result.stderr)
        self.assertIn("touches_live_servers", result.stderr)

    def test_post_window_state_allows_candidate_pack_metadata_reference_without_promoting_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "live-validation-logs"
            report_dir = root / "reports"
            closure_path = root / "closure-with-candidate-pack-reference.json"
            closure = closure_report_payload(evidence_dir=output_root / "20260606T100000Z-player-principal-lifecycle")
            closure["multi_surface_beta_capture_pack_metadata"] = {
                "schema": MULTI_SURFACE_PACK_SCHEMA,
                "status": "candidate_capture_pack",
                "non_claim_flags": {
                    "candidate_only": True,
                    "offline_candidate_metadata_only": True,
                    "touches_live_servers": False,
                    "authorizes_discord_send": False,
                    "authorizes_marker_or_env_changes": False,
                    "authorizes_live_log_reads": False,
                    "counts_as_approved_runtime_evidence": False,
                    "counts_as_sdk_progress": False,
                    "counts_as_p0_progress": False,
                    "clears_approved_runtime_evidence_missing": False,
                },
            }
            write_json(closure_path, closure)

            result = run_executor(
                output_root,
                report_dir,
                "--post-window-state-json",
                str(closure_path),
                "--post-window-state-only",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "post_window_state_consumed_non_evidence")
        self.assert_multi_surface_boundary(report["multi_surface_beta_capture_pack_boundary"])
        self.assertFalse(report["multi_surface_beta_capture_pack_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["multi_surface_beta_capture_pack_authorizes_discord_send"])
        self.assertFalse(report["multi_surface_beta_capture_pack_authorizes_live_ops"])
        self.assertFalse(report["multi_surface_beta_capture_pack_authorizes_live_log_reads"])
        self.assertFalse(report["multi_surface_beta_capture_pack_authorizes_marker_env_writes"])
        self.assertFalse(report["multi_surface_beta_capture_pack_clears_approved_runtime_evidence_missing"])


if __name__ == "__main__":
    unittest.main()
