#!/usr/bin/env python3
"""Tests for prepare_player_principal_lifecycle_window_request.py."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "prepare_player_principal_lifecycle_window_request.py"
sys.path.insert(0, str(SCRIPT_DIR))
from prepare_player_principal_lifecycle_window_request import (  # noqa: E402
    APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY,
    APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY,
    APPROVAL_SCOPE_STATUS,
    APPROVAL_SCOPE_STATUS_STANDING_LAUNCH_AUTHORITY,
    APPROVAL_SCOPE_SOURCE_REQUIRED_STANDING_LAUNCH_AUTHORITY,
    APPROVED_BETA_NOTICE_PATH,
    AUTHORIZATION_FLAGS,
    BETA_RUNTIME_CHOREOGRAPHY_NON_AUTHORIZATION,
    BETA_RUNTIME_CHOREOGRAPHY_SCHEMA,
    CHECKJOIN_STIMULUS_BOUNDARY_NON_AUTHORIZATION,
    CHECKJOIN_STIMULUS_BOUNDARY_SCHEMA,
    CURRENT_TURN_APPROVAL_REQUIRED_FIELDS,
    DEFAULT_APPROVED_WINDOW_SECONDS,
    DIRECT_JOIN_PLAN_SCHEMA,
    DRIFT_FIX_DEPLOYMENT_INTENT_TYPE,
    EXACT_TARGET_SCOPE_SCHEMA,
    EXPECTED_BINARY_SHA256,
    MAX_APPROVED_WINDOW_SECONDS,
    PASSIVE_WAIT_BOUNDARY_SCHEMA,
    PLAYER_NOTICE_ACTION_SCHEMA,
    PLAYER_PRESENCE_SAFETY_SCHEMA,
    PLANNED_OBELISK_BUILD_ARTIFACT_KIND,
    RUNTIME_TRIPLET_CONTRACT_SCHEMA,
    SESSION_START_REJECTED_REQUIRED_ARGUMENTS,
    SESSION_START_REJECTED_REQUIRED_CALL,
    SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS,
    SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES,
    SESSION_START_REJECTED_REQUIRED_FUNCTION,
    STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT,
    HANDLE_NEW_PLAYER_FUNCTION,
    runtime_triplet_contract,
)


SHA = EXPECTED_BINARY_SHA256
TEST_COMMIT = subprocess.check_output(
    ["git", "rev-parse", "HEAD"],
    cwd=SCRIPT_DIR.parents[0],
    text=True,
).strip()


def future_window() -> tuple[str, str, str]:
    start = (datetime.now(timezone.utc) + timedelta(hours=1)).replace(microsecond=0)
    end = start + timedelta(minutes=15)
    return (
        start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle",
        start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def base_args(output_dir: Path) -> list[str]:
    run_id, start, end = future_window()
    return [
        sys.executable,
        str(SCRIPT),
        "--instance",
        "arkserver2",
        "--map",
        "TheIsland",
        "--run-id",
        run_id,
        "--obelisk-commit",
        TEST_COMMIT,
        "--approved-window-start-utc",
        start,
        "--approved-window-end-utc",
        end,
        "--binary-sha256",
        SHA,
        "--restart-expectation",
        "restart",
        "--final-posture",
        "stable",
        "--user-policy",
        "no_regular_users",
        "--rollback-owner",
        "operator",
        "--output-dir",
        str(output_dir),
        "--json",
    ]


def fenced_section(markdown: str, title: str) -> list[str]:
    start = f"{title}\n\n```text\n"
    section = markdown.split(start, 1)[1].split("\n```", 1)[0]
    return section.splitlines()


class PreparePlayerPrincipalLifecycleWindowRequestTests(unittest.TestCase):
    def test_rejects_server_root_output_without_explicit_write_opt_in(self) -> None:
        result = subprocess.run(
            base_args(Path("/servidor/ark/workspace-offline/obelisk-test-player-principal-guard")),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OBELISK_ALLOW_SERVER_ROOT_WRITES=1", result.stderr)

    def test_rejects_beta_user_window_without_approved_beta_testers_notice_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp) / "request")
            args[args.index("--user-policy") + 1] = "operator_approved_beta_users"
            args.extend(["--notice-path", "other-discord-channel"])
            result = subprocess.run(
                args,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"--notice-path must be {APPROVED_BETA_NOTICE_PATH}", result.stderr)

    def test_rejects_notice_path_when_no_regular_users_policy_does_not_need_notice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp) / "request")
            args.extend(["--notice-path", APPROVED_BETA_NOTICE_PATH])
            result = subprocess.run(
                args,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--notice-path must be not_applicable", result.stderr)

    def test_prepares_secret_free_request_pack_without_authorizing_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            result = subprocess.run(
                base_args(output_dir),
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            report = json.loads(result.stdout)
            request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))
            env_file = (output_dir / "observer-window.env").read_text(encoding="utf-8").splitlines()
            env = [line for line in env_file if not line.startswith("#")]
            markdown = (output_dir / "operator-approval-request.md").read_text(encoding="utf-8")
            receipt_template = json.loads(
                (output_dir / "operator-approval-receipt.template.json").read_text(encoding="utf-8")
            )
            output_sha256 = {
                filename: hashlib.sha256((output_dir / filename).read_bytes()).hexdigest()
                for filename in (
                    "observer-window.env",
                    "window-request.json",
                    "operator-approval-request.md",
                    "operator-approval-receipt.template.json",
                )
            }

        self.assertEqual(report["status"], "prepared")
        self.assertEqual(report["ready_scope"], "offline_request_pack_generation_only")
        self.assertTrue(report["current_turn_operator_approval_required"])
        self.assertFalse(report["current_turn_approval_recorded"])
        self.assertFalse(report["request_pack_records_current_turn_approval"])
        self.assertEqual(report["authorization_source"], "none_request_pack_only")
        self.assertEqual(report["approved_runtime_evidence_source"], "none_request_pack_only")
        self.assertEqual(report["target"], {"instance": "arkserver2", "map": "TheIsland"})
        self.assertEqual(report["exact_target_scope"]["schema"], EXACT_TARGET_SCOPE_SCHEMA)
        self.assertEqual(report["exact_target_scope"]["instance"], "arkserver2")
        self.assertEqual(report["exact_target_scope"]["map"], "TheIsland")
        self.assertFalse(report["exact_target_scope"]["instance_alias_allowed"])
        self.assertFalse(report["exact_target_scope"]["map_alias_allowed"])
        self.assertEqual(report["runtime_triplet_contract"], runtime_triplet_contract())
        self.assertEqual(report["passive_wait_boundary"]["schema"], PASSIVE_WAIT_BOUNDARY_SCHEMA)
        self.assertEqual(report["direct_join_plan"]["schema"], DIRECT_JOIN_PLAN_SCHEMA)
        self.assertEqual(report["direct_join_plan"]["target"], report["target"])
        self.assertEqual(report["direct_join_plan"]["target_map"], "TheIsland")
        self.assertTrue(report["direct_join_plan"]["fastest_clean_theisland_direct_join"])
        self.assertTrue(report["direct_join_plan"]["direct_join_required"])
        self.assertFalse(report["direct_join_plan"]["cluster_transfer_required"])
        self.assertFalse(report["direct_join_plan"]["extra_transfer_server_required"])
        self.assertFalse(report["direct_join_plan"]["third_ark_server_allowed"])
        self.assertFalse(report["direct_join_plan"]["broad_discord_or_community_notice_allowed"])
        self.assertFalse(report["direct_join_plan"]["raw_player_text_or_identity_allowed"])
        self.assertFalse(report["direct_join_plan"]["diagnostic_candidates_allowed_for_approved_evidence"])
        self.assertEqual(report["direct_join_plan"]["organic_wait_window_seconds"], DEFAULT_APPROVED_WINDOW_SECONDS)
        self.assertEqual(report["direct_join_plan"]["max_organic_wait_window_seconds"], MAX_APPROVED_WINDOW_SECONDS)
        self.assertFalse(report["direct_join_plan"]["organic_wait_window_counts_as_approved_runtime_evidence"])
        self.assertTrue(report["direct_join_plan"]["receipt_before_activation_required"])
        self.assertTrue(report["direct_join_plan"]["post_window_replay_requires_receipt"])
        choreography = report["direct_join_plan"]["beta_runtime_choreography"]
        self.assertEqual(choreography, request["direct_join_plan"]["beta_runtime_choreography"])
        self.assertEqual(choreography["schema"], BETA_RUNTIME_CHOREOGRAPHY_SCHEMA)
        self.assertEqual(choreography["target"], request["target"])
        self.assertEqual(choreography["tester_count_required"], 1)
        self.assertTrue(choreography["exactly_one_tester_required"])
        self.assertTrue(choreography["single_tester_only"])
        self.assertTrue(choreography["direct_target_join_required"])
        self.assertEqual(choreography["direct_join_route"], "direct_join_exact_server_map")
        self.assertFalse(choreography["cluster_transfer_required"])
        self.assertFalse(choreography["cluster_transfer_allowed"])
        self.assertFalse(choreography["extra_transfer_server_required"])
        self.assertFalse(choreography["reconnect_before_exact_checkjoin_allowed"])
        self.assertFalse(choreography["logout_before_exact_checkjoin_allowed"])
        self.assertTrue(choreography["wait_for_exact_checkjoin_before_logout_required"])
        self.assertFalse(choreography["logout_or_cluster_transfer_or_reconnect_before_exact_checkjoin_allowed"])
        self.assertFalse(
            choreography["logout_cluster_transfer_reconnect_before_exact_checkjoin_or_window_close_allowed"]
        )
        self.assertFalse(choreography["mixed_transfer_reconnect_same_approved_window_allowed"])
        self.assertTrue(choreography["approved_window_must_not_mix_direct_join_transfer_or_reconnect"])
        observer_gate = choreography["observer_gate"]
        self.assertEqual(observer_gate["required_role"], "session_start_rejected")
        self.assertEqual(observer_gate["required_function"], "ShooterGameMode.CheckJoinInProgress")
        self.assertEqual(observer_gate["required_call"], SESSION_START_REJECTED_REQUIRED_CALL)
        self.assertEqual(
            observer_gate["required_copied_bool_fields"],
            SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS,
        )
        self.assertEqual(
            observer_gate["required_copied_bool_values"],
            SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES,
        )
        self.assertTrue(observer_gate["wait_until_observer_sees_exact_checkjoin_or_window_closes"])
        self.assertFalse(observer_gate["logout_before_observer_gate_or_window_close_allowed"])
        self.assertIn("then logs out once only when told", choreography["tester_instruction"])
        self.assertIn("second_tester_join", choreography["forbidden_same_window_actions"])
        self.assertIn("mixed_transfer_and_reconnect_flow", choreography["forbidden_same_window_actions"])
        stimulus = choreography["stale_or_diagnostic_exact_checkjoin_boundary"]
        self.assertEqual(stimulus["schema"], CHECKJOIN_STIMULUS_BOUNDARY_SCHEMA)
        self.assertEqual(stimulus["exact_call"], "ShooterGameMode.CheckJoinInProgress(1,0)")
        self.assertTrue(stimulus["stimulus_clue_for_future_choreography"])
        self.assertFalse(stimulus["counts_as_approved_runtime_evidence"])
        self.assertEqual(stimulus["non_authorization"], CHECKJOIN_STIMULUS_BOUNDARY_NON_AUTHORIZATION)
        self.assertFalse(choreography["choreography_authorizes_discord"])
        self.assertFalse(choreography["choreography_authorizes_runtime_capture"])
        self.assertFalse(choreography["choreography_authorizes_server_operations"])
        self.assertFalse(choreography["approved_runtime_evidence"])
        self.assertFalse(choreography["counts_as_approved_runtime_evidence"])
        self.assertFalse(choreography["counts_as_runtime_evidence"])
        self.assertFalse(choreography["counts_as_sdk_evidence"])
        self.assertFalse(choreography["runtime_ready"])
        self.assertFalse(choreography["public_sdk_ready"])
        self.assertEqual(choreography["non_authorization"], BETA_RUNTIME_CHOREOGRAPHY_NON_AUTHORIZATION)
        self.assertEqual(
            report["passive_wait_boundary"]["requested_wait_window_seconds"],
            DEFAULT_APPROVED_WINDOW_SECONDS,
        )
        self.assertEqual(
            report["passive_wait_boundary"]["max_requested_wait_window_seconds"],
            MAX_APPROVED_WINDOW_SECONDS,
        )
        self.assertTrue(report["passive_wait_boundary"]["requested_wait_window_seconds_checked_only"])
        self.assertFalse(report["passive_wait_boundary"]["requested_wait_window_authorizes_current_turn_approval"])
        self.assertFalse(report["passive_wait_boundary"]["requested_wait_window_authorizes_runtime_capture"])
        self.assertFalse(report["passive_wait_boundary"]["wait_only_or_passive_monitor_authorizes_deploy_or_restart"])
        self.assertEqual(report["requested_wait_window_seconds"], DEFAULT_APPROVED_WINDOW_SECONDS)
        self.assertEqual(report["max_requested_wait_window_seconds"], MAX_APPROVED_WINDOW_SECONDS)
        self.assertTrue(report["requested_wait_window_seconds_checked_only"])
        self.assertFalse(report["requested_wait_window_authorizes_current_turn_approval"])
        self.assertFalse(report["requested_wait_window_authorizes_runtime_capture"])
        self.assertFalse(report["passive_wait_or_watch_only_authorizes_deploy_or_restart"])
        self.assertIn("no server operation", report["non_claim"])
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["discord_authorized"])
        self.assertFalse(report["discord_send_authorized"])
        self.assertFalse(report["discord_sent"])
        self.assertFalse(report["marker_env_changes_authorized"])
        self.assertFalse(report["server_operations_authorized"])
        self.assertFalse(report["runtime_work_authorized"])
        self.assertFalse(report["runtime_capture_authorized"])
        self.assertFalse(report["runtime_window_authorized"])
        self.assertFalse(report["read_live_logs"])
        self.assertFalse(report["reads_live_logs"])
        self.assertFalse(report["live_log_reads_authorized"])
        self.assertFalse(report["live_log_permission_granted"])
        self.assertFalse(report["publication_authorized"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["v1_completion_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["request_pack_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["observer_env_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["operator_request_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["copied_log_metadata_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["bundle_output_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["preflight_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["window_manifest_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["completed_receipt_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["diagnostic_candidates_enabled"])
        self.assertEqual(report["current_turn_approval_scope_status"], APPROVAL_SCOPE_STATUS)
        self.assertEqual(report["current_turn_approval_required_fields"], CURRENT_TURN_APPROVAL_REQUIRED_FIELDS)
        self.assertEqual(report["deployment_intent"]["intent_type"], DRIFT_FIX_DEPLOYMENT_INTENT_TYPE)
        self.assertTrue(report["deployment_intent"]["request_only"])
        self.assertFalse(report["deployment_intent"]["deployment_authorized"])
        self.assertFalse(report["deployment_intent"]["counts_as_approved_runtime_evidence"])
        self.assertEqual(report["planned_obelisk_build_identity"]["obelisk_commit"], TEST_COMMIT)
        self.assertFalse(report["planned_obelisk_build_identity"]["build_artifact"]["available"])
        self.assertEqual(report["planned_obelisk_build_identity"]["build_artifact"]["source"], "not_provided")
        self.assertFalse(report["sdk_accounting_counts_as_completed_surface"])
        self.assertFalse(report["p0_accounting_counts_as_promoted_surface"])
        self.assertEqual(report["next_blocker"], "operator_current_turn_runtime_window_approval_required")
        for name, filename in (
            ("observer_env", "observer-window.env"),
            ("request_json", "window-request.json"),
            ("operator_request", "operator-approval-request.md"),
            ("operator_approval_receipt_template", "operator-approval-receipt.template.json"),
        ):
            self.assertEqual(report["outputs"][name]["path"], str(output_dir / filename))
            self.assertEqual(
                report["outputs"][name]["sha256"],
                output_sha256[filename],
            )
        self.assertFalse((output_dir / "operator-approval-receipt.json").exists())
        self.assertEqual(
            receipt_template["schema"],
            "obelisk.player-principal-lifecycle-operator-approval-receipt.v1",
        )
        self.assertEqual(receipt_template["status"], "generated_template")
        self.assertFalse(receipt_template["receipt_completed"])
        self.assertFalse(receipt_template["operator_current_turn_approval_recorded"])
        self.assertFalse(receipt_template["standing_launch_authority_recorded"])
        self.assertFalse(receipt_template["standing_launch_authority_satisfies_operator_approval"])
        self.assertFalse(receipt_template["approval_scope"]["standing_approval"])
        self.assertFalse(receipt_template["approval_scope"]["reusable"])
        for value in receipt_template["non_authorization_flags"].values():
            self.assertFalse(value)
        self.assertEqual(request["schema"], "obelisk.player-principal-lifecycle-window-request.v1")
        self.assertEqual(request["status"], "candidate_only_request_pack")
        self.assertEqual(request["authorization_flags"], AUTHORIZATION_FLAGS)
        self.assertFalse(request["authorization_flags"]["read_live_logs"])
        self.assertFalse(request["authorization_flags"]["reads_live_logs"])
        self.assertFalse(request["authorization_flags"]["live_log_reads_authorized"])
        self.assertFalse(request["authorization_flags"]["live_log_permission_granted"])
        self.assertFalse(request["authorization_flags"]["discord_authorized"])
        self.assertFalse(request["authorization_flags"]["discord_send_authorized"])
        self.assertFalse(request["authorization_flags"]["discord_sent"])
        self.assertFalse(request["authorization_flags"]["marker_env_changes_authorized"])
        self.assertFalse(request["authorization_flags"]["runtime_capture_authorized"])
        self.assertFalse(request["authorization_flags"]["runtime_window_authorized"])
        self.assertFalse(request["authorization_flags"]["current_turn_approval_recorded"])
        self.assertFalse(request["authorization_flags"]["current_turn_scope_authorized"])
        self.assertFalse(request["diagnostic_candidates_enabled"])
        self.assertEqual(request["exact_target_scope"]["schema"], EXACT_TARGET_SCOPE_SCHEMA)
        self.assertEqual(request["exact_target_scope"]["instance"], "arkserver2")
        self.assertEqual(request["exact_target_scope"]["map"], "TheIsland")
        self.assertFalse(request["exact_target_scope"]["instance_alias_allowed"])
        self.assertFalse(request["exact_target_scope"]["map_alias_allowed"])
        self.assertTrue(request["exact_target_scope"]["approval_must_name_exact_instance_and_map"])
        triplet = request["runtime_triplet_contract"]
        self.assertEqual(triplet["schema"], RUNTIME_TRIPLET_CONTRACT_SCHEMA)
        self.assertTrue(triplet["planning_only"])
        self.assertEqual(triplet["session_start_rejected"]["required_function"], SESSION_START_REJECTED_REQUIRED_FUNCTION)
        self.assertEqual(triplet["session_start_rejected"]["required_argument_tuple"], SESSION_START_REJECTED_REQUIRED_ARGUMENTS)
        self.assertEqual(triplet["session_start_rejected"]["required_call"], SESSION_START_REJECTED_REQUIRED_CALL)
        self.assertEqual(
            triplet["session_start_rejected"]["required_copied_bool_fields"],
            SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS,
        )
        self.assertEqual(
            triplet["session_start_rejected"]["required_copied_bool_values"],
            SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES,
        )
        self.assertFalse(triplet["session_start_rejected"]["handle_new_player_rejected_tuple_allowed"])
        self.assertFalse(triplet["session_start_rejected"]["handle_new_player_rejected_tuple_alternative_allowed"])
        self.assertEqual(triplet["handle_new_player_rejected_tuples"]["function"], HANDLE_NEW_PLAYER_FUNCTION)
        self.assertFalse(triplet["handle_new_player_rejected_tuples"]["allowed_for_session_start_rejected"])
        self.assertFalse(triplet["handle_new_player_rejected_tuples"]["alternative_for_session_start_rejected"])
        self.assertEqual(request["passive_wait_boundary"]["schema"], PASSIVE_WAIT_BOUNDARY_SCHEMA)
        self.assertEqual(request["direct_join_plan"], report["direct_join_plan"])
        self.assertEqual(request["direct_join_plan"]["schema"], DIRECT_JOIN_PLAN_SCHEMA)
        self.assertEqual(request["direct_join_plan"]["target"], request["target"])
        self.assertTrue(request["direct_join_plan"]["fastest_clean_theisland_direct_join"])
        self.assertFalse(request["direct_join_plan"]["third_ark_server_allowed"])
        self.assertFalse(request["direct_join_plan"]["broad_discord_or_community_notice_allowed"])
        self.assertEqual(request["direct_join_plan"]["organic_wait_window_seconds"], 900)
        self.assertEqual(request["passive_wait_boundary"]["target"], request["target"])
        self.assertEqual(request["passive_wait_boundary"]["requested_wait_window_seconds"], 900)
        self.assertEqual(request["passive_wait_boundary"]["max_requested_wait_window_seconds"], MAX_APPROVED_WINDOW_SECONDS)
        self.assertTrue(request["passive_wait_boundary"]["requested_wait_window_seconds_checked_only"])
        self.assertFalse(request["passive_wait_boundary"]["requested_wait_window_authorizes_current_turn_approval"])
        self.assertFalse(request["passive_wait_boundary"]["requested_wait_window_authorizes_deploy_or_restart"])
        self.assertFalse(request["passive_wait_boundary"]["requested_wait_window_authorizes_runtime_capture"])
        self.assertFalse(request["passive_wait_boundary"]["requested_wait_window_counts_as_approved_runtime_evidence"])
        self.assertFalse(request["passive_wait_boundary"]["wait_only_or_passive_monitor_authorizes_deploy_or_restart"])
        self.assertFalse(request["passive_wait_boundary"]["passive_monitor_ticks_authorize_runtime_capture"])
        self.assertFalse(request["passive_wait_boundary"]["player_presence_detection_authorizes_followup"])
        self.assertFalse(request["passive_wait_boundary"]["snapshots_or_diagnostics_count_as_approved_runtime_evidence"])
        self.assertTrue(request["passive_wait_boundary"]["active_followup_requires_fresh_exact_current_turn_scope"])
        player_safety = request["player_presence_safety"]
        self.assertEqual(player_safety["schema"], PLAYER_PRESENCE_SAFETY_SCHEMA)
        self.assertEqual(player_safety["target"], request["target"])
        self.assertEqual(player_safety["restart_expectation"], "restart")
        self.assertTrue(player_safety["connected_player_check_required_before_restart"])
        self.assertTrue(player_safety["rcon_broadcast_required_if_players_connected"])
        self.assertTrue(player_safety["restart_must_be_cancelled_or_rescheduled_if_players_remain_connected"])
        self.assertTrue(player_safety["passive_wait_preferred_after_activation"])
        self.assertTrue(player_safety["linuxgsm_monitor_forbidden"])
        self.assertFalse(player_safety["player_check_or_broadcast_authorized_by_request_pack"])
        notice_action = request["player_notice_action"]
        self.assertEqual(notice_action["schema"], PLAYER_NOTICE_ACTION_SCHEMA)
        self.assertFalse(notice_action["required"])
        self.assertEqual(notice_action["notice_path"], "not_applicable")
        self.assertFalse(notice_action["approved_notice_path_must_be_named"])
        self.assertFalse(notice_action["dry_run_required_before_send"])
        self.assertFalse(notice_action["real_notice_send_required_before_activation"])
        self.assertFalse(notice_action["send_performed_by_request_pack"])
        self.assertFalse(notice_action["request_pack_authorizes_discord"])
        self.assertTrue(notice_action["activation_allowed_before_notice_sent"])
        self.assertEqual(notice_action["activation_blocker"], "no_player_notice_required")
        self.assertEqual(request["approval_required"], "current-turn operator-approved runtime window, not standing approval")
        self.assertEqual(request["current_turn_approval_scope"]["status"], APPROVAL_SCOPE_STATUS)
        self.assertEqual(
            request["current_turn_approval_scope"]["required_operator_approval_fields"],
            CURRENT_TURN_APPROVAL_REQUIRED_FIELDS,
        )
        self.assertFalse(request["current_turn_approval_scope"]["standing_approval_allowed"])
        self.assertFalse(request["current_turn_approval_scope"]["request_pack_authorizes_deploy_or_runtime"])
        self.assertTrue(request["current_turn_approval_scope"]["missing_or_ambiguous_scope_blocks_window"])
        named_scope = request["current_turn_approval_scope"]["required_named_scope"]
        self.assertEqual(named_scope["target"], request["target"])
        self.assertEqual(named_scope["exact_target_instance_map"], request["exact_target_scope"])
        self.assertEqual(named_scope["marker_env_gates"]["markers"], request["marker_set"])
        self.assertEqual(named_scope["marker_env_gates"]["env_snapshot"], env)
        self.assertEqual(
            named_scope["restart_window"],
            {
                "start_utc": request["approved_window"]["start_utc"],
                "end_utc": request["approved_window"]["end_utc"],
                "expectation": request["restart_expectation"],
            },
        )
        self.assertEqual(named_scope["rollback"], request["rollback"])
        self.assertEqual(named_scope["player_presence_safety"], request["player_presence_safety"])
        self.assertEqual(named_scope["player_notice_action"], request["player_notice_action"])
        self.assertEqual(named_scope["direct_join_plan"], request["direct_join_plan"])
        self.assertEqual(named_scope["runtime_triplet_contract"], request["runtime_triplet_contract"])
        self.assertEqual(named_scope["passive_wait_boundary"], request["passive_wait_boundary"])
        self.assertEqual(named_scope["final_posture"], "stable")
        self.assertEqual(
            named_scope["evidence_paths"]["operator_approval_receipt_json"],
            f"/servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/operator-approval-receipt.json",
        )
        deployment = request["deployment_intent"]
        self.assertEqual(deployment["intent_type"], DRIFT_FIX_DEPLOYMENT_INTENT_TYPE)
        self.assertEqual(deployment["planned_obelisk_commit"], TEST_COMMIT)
        self.assertEqual(deployment["planned_obelisk_build_identity"], request["planned_obelisk_build_identity"])
        self.assertEqual(deployment["target"], request["target"])
        self.assertTrue(deployment["request_only"])
        self.assertFalse(deployment["deployment_authorized"])
        self.assertFalse(deployment["restart_authorized"])
        self.assertFalse(deployment["runtime_capture_authorized"])
        self.assertFalse(deployment["counts_as_approved_runtime_evidence"])
        build_identity = request["planned_obelisk_build_identity"]
        self.assertEqual(build_identity["obelisk_commit"], TEST_COMMIT)
        self.assertIn("does not claim public readiness", build_identity["non_authorization"])
        self.assertIn("does not claim SDK readiness", build_identity["non_authorization"])
        self.assertIn("does not claim operator approval or authorization", request["non_claims"])
        self.assertFalse(build_identity["build_artifact"]["available"])
        self.assertEqual(build_identity["build_artifact"]["source"], "not_provided")
        self.assertIsNone(build_identity["build_artifact"]["artifact_sha256"])
        self.assertRegex(request["prepared_at_utc"], r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
        self.assertLess(request["prepared_at_utc"], request["approved_window"]["start_utc"])
        self.assertEqual(receipt_template["bound_request_pack"]["prepared_at_utc"], request["prepared_at_utc"])
        self.assertEqual(receipt_template["bound_request_pack"]["exact_target_scope"], request["exact_target_scope"])
        self.assertEqual(receipt_template["bound_request_pack"]["passive_wait_boundary"], request["passive_wait_boundary"])
        self.assertEqual(receipt_template["bound_request_pack"]["direct_join_plan"], request["direct_join_plan"])
        self.assertEqual(receipt_template["bound_request_pack"]["player_notice_action"], request["player_notice_action"])
        self.assertEqual(receipt_template["bound_request_pack"]["player_presence_safety"], request["player_presence_safety"])
        self.assertEqual(receipt_template["bound_request_pack"]["runtime_triplet_contract"], request["runtime_triplet_contract"])
        self.assertEqual(receipt_template["bound_request_pack"]["current_turn_approval_scope"], request["current_turn_approval_scope"])
        self.assertEqual(receipt_template["bound_request_pack"]["deployment_intent"], request["deployment_intent"])
        self.assertEqual(
            receipt_template["bound_request_pack"]["planned_obelisk_build_identity"],
            request["planned_obelisk_build_identity"],
        )
        self.assertIn(f"prepared_at_utc={request['prepared_at_utc']}", markdown)
        self.assertEqual(request["copied_log_path"], f"/servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/Obelisk.log")
        replay_contract = request["post_window_replay_contract"]
        self.assertTrue(replay_contract["required"])
        self.assertTrue(replay_contract["offline_only"])
        self.assertEqual(
            replay_contract["sidecars"]["request_pack_path"],
            f"/servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/window-request.json",
        )
        self.assertEqual(
            replay_contract["sidecars"]["preflight_pre_path"],
            f"/servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/preflight-pre.json",
        )
        self.assertEqual(
            replay_contract["sidecars"]["operator_approval_receipt_path"],
            f"/servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/operator-approval-receipt.json",
        )
        self.assertEqual(
            replay_contract["sidecars"]["operator_approval_request_path"],
            f"/servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/operator-approval-request.md",
        )
        self.assertEqual(
            replay_contract["sidecars"]["copied_log_path"],
            f"/servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/Obelisk.log",
        )
        self.assertIn("--post-window-replay", replay_contract["checks"]["window_manifest_replay"])
        self.assertIn("does not authorize runtime work, server operations", replay_contract["non_authorization"])
        binding = request["operator_live_ops_brief"]["artifact_binding"]
        self.assertEqual(binding["run_id"], request["run_id"])
        self.assertEqual(binding["copied_evidence_dir"], request["copied_evidence_dir"])
        self.assertEqual(binding["copied_log_path"], request["copied_log_path"])
        self.assertEqual(binding["window_manifest_path"], request["window_manifest_path"])
        self.assertEqual(binding["binding_claim"], "exact_run_id_window_artifacts_only")
        self.assertIn("does not authorize runtime work", binding["non_authorization"])
        self.assertIn("server operations", binding["non_authorization"])
        self.assertEqual(
            binding["required_sidecars"]["operator_approval_receipt_json"],
            replay_contract["sidecars"]["operator_approval_receipt_path"],
        )
        self.assertEqual(
            binding["required_sidecars"]["operator_approval_request_md"],
            replay_contract["sidecars"]["operator_approval_request_path"],
        )
        self.assertEqual(
            binding["required_sidecars"]["preflight_post_json"],
            replay_contract["sidecars"]["preflight_post_path"],
        )
        self.assertEqual(binding["required_sidecars"]["copied_obelisk_log"], replay_contract["sidecars"]["copied_log_path"])
        self.assertIn("enable-player-principal-lifecycle-observer", request["marker_set"])
        self.assertIn("enable-reflection-scanner", request["forbidden_markers"])
        self.assertIn("does not claim stable principal identity", request["non_claims"])
        self.assertEqual(
            request["rollback"]["marker_state_dir"],
            "/servidor/ark/obelisk/state/instances/arkserver2",
        )
        self.assertEqual(
            request["rollback"]["stable_marker_paths"]["enable_process_event_hook"],
            "/servidor/ark/obelisk/state/instances/arkserver2/enable-process-event-hook",
        )
        self.assertEqual(
            request["rollback"]["observer_marker_paths"]["enable_player_principal_lifecycle_observer"],
            "/servidor/ark/obelisk/state/instances/arkserver2/enable-player-principal-lifecycle-observer",
        )
        evidence_capture = request["operator_live_ops_brief"]["evidence_capture"]
        self.assertEqual(request["operator_live_ops_brief"]["exact_target_scope"], request["exact_target_scope"])
        self.assertEqual(request["operator_live_ops_brief"]["runtime_triplet_contract"], request["runtime_triplet_contract"])
        self.assertFalse(request["operator_live_ops_brief"]["feature_gates"]["candidate_diagnostics"])
        self.assertEqual(request["operator_live_ops_brief"]["deployment_intent"], deployment)
        self.assertEqual(request["operator_live_ops_brief"]["passive_wait_boundary"], request["passive_wait_boundary"])
        self.assertEqual(request["operator_live_ops_brief"]["player_notice_action"], request["player_notice_action"])
        self.assertEqual(
            evidence_capture["request_pack_path"],
            f"/servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/window-request.json",
        )
        self.assertEqual(
            evidence_capture["observer_env_path"],
            f"/servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/observer-window.env",
        )
        self.assertEqual(
            evidence_capture["operator_approval_request_path"],
            f"/servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/operator-approval-request.md",
        )
        self.assertEqual(
            evidence_capture["preflight_pre_path"],
            f"/servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/preflight-pre.json",
        )
        self.assertEqual(
            evidence_capture["preflight_post_path"],
            f"/servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/preflight-post.json",
        )
        self.assertIn(
            "does not authorize server operations, marker/env changes",
            request["operator_live_ops_brief"]["non_authorization"],
        )
        self.assertEqual(
            request["operator_live_ops_brief"]["post_run_stable_posture"]["verification_commands"],
            [
                [
                    "scripts/check_player_principal_lifecycle_preflight.sh",
                    "--instance",
                    "arkserver2",
                    "--map",
                    "TheIsland",
                    "--mode",
                    "stable",
                    "--expected-binary-sha256",
                    SHA,
                ],
                [
                    "scripts/check_obelisk_server_posture.sh",
                    "--expect-stable",
                    "--map",
                    "TheIsland",
                    "--instance",
                    "arkserver2",
                ],
            ],
        )
        self.assertEqual(
            env,
            [
                "OBELISK_INSTANCE_ID=arkserver2",
                "OBELISK_ENABLE_PROCESS_EVENT_HOOK=1",
                "OBELISK_DISABLE_PLUGINS=1",
                "OBELISK_WRAPPER_PROFILE=observer-debug",
                "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER=1",
                f"OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256={SHA}",
                "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10",
                "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0",
                "OBELISK_PE_TRACE_LIMIT=0",
            ],
        )
        self.assertFalse(any(line.startswith("OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=") for line in env))
        self.assertIn("# request-pack-only; does not authorize marker/env changes, runtime work, or server operations", env_file)
        self.assertIn("# request_pack_counts_as_approved_runtime_evidence=false", env_file)
        self.assertIn("# stable_claim_allowed=false", env_file)
        self.assertIn("# public_readiness_claim=false", env_file)
        self.assertIn("# sdk_readiness_claim=false", env_file)
        self.assertIn("# operator_approval_or_authorization_claim=false", env_file)
        self.assertIn("This is a request pack only. It does not authorize server operations.", markdown)
        self.assertIn("Wait-only/passive monitoring is not approval and does not authorize deploy or restart.", markdown)
        self.assertIn("target exact instance/map required=true", markdown)
        self.assertIn("target aliases allowed=false", markdown)
        self.assertIn("rollback marker_state_dir=/servidor/ark/obelisk/state/instances/arkserver2", markdown)
        self.assertIn(
            "rollback stable_marker_path.enable_process_event_hook="
            "/servidor/ark/obelisk/state/instances/arkserver2/enable-process-event-hook",
            markdown,
        )
        self.assertIn("requested organic wait window seconds=900", markdown)
        self.assertIn(f"requested organic wait window max seconds={MAX_APPROVED_WINDOW_SECONDS}", markdown)
        self.assertIn("requested organic wait window checked only=true", markdown)
        self.assertIn("requested organic wait window authorizes current-turn approval=false", markdown)
        self.assertIn("direct join route=direct_join_exact_server_map", markdown)
        self.assertIn("direct join target instance=arkserver2", markdown)
        self.assertIn("direct join target map=TheIsland", markdown)
        self.assertIn("fastest clean TheIsland direct join=true", markdown)
        self.assertIn("direct join cluster transfer required=false", markdown)
        self.assertIn("direct join extra transfer server required=false", markdown)
        self.assertIn("third ARK server allowed=false", markdown)
        self.assertIn("broad Discord/community notice allowed=false", markdown)
        self.assertIn("beta runtime choreography single tester only=true", markdown)
        self.assertIn("beta runtime choreography direct target join required=true", markdown)
        self.assertIn(
            "beta runtime choreography observer gate=ShooterGameMode.CheckJoinInProgress(1,0)",
            markdown,
        )
        self.assertIn("beta runtime choreography waits for exact checkjoin or window close=true", markdown)
        self.assertIn("beta runtime choreography logout once when asked after gate/window close=true", markdown)
        self.assertIn("beta runtime choreography cluster transfer allowed=false", markdown)
        self.assertIn("beta runtime choreography reconnect before exact checkjoin allowed=false", markdown)
        self.assertIn("beta runtime choreography logout before exact checkjoin allowed=false", markdown)
        self.assertIn(
            "beta runtime choreography mixed transfer/reconnect same approved window allowed=false",
            markdown,
        )
        self.assertIn("beta runtime choreography counts as approved runtime evidence=false", markdown)
        self.assertIn("passive wait authorizes deploy/restart=false", markdown)
        self.assertIn("passive monitor ticks authorize runtime capture=false", markdown)
        self.assertTrue(request["passive_wait_boundary"]["active_followup_requires_fresh_exact_current_turn_scope"])
        self.assertFalse(request["passive_wait_boundary"]["active_followup_requires_recorded_standing_launch_authority"])
        self.assertIn("connected player check before restart required=true", markdown)
        self.assertIn("RCON broadcast if players connected required=true", markdown)
        self.assertIn("restart cancel/reschedule if players remain connected=true", markdown)
        self.assertIn("player presence check or broadcast authorized by request pack=false", markdown)
        self.assertIn("dispatch limit=0", markdown)
        self.assertIn("log limit=10", markdown)
        self.assertIn("diagnostic candidates enabled=false", markdown)
        self.assertIn("session_start_rejected required call=CheckJoinInProgress(1,0)", markdown)
        self.assertIn("session_start_rejected copied bools=bIsFromLogin,ReturnValue=1,0", markdown)
        self.assertIn("HandleNewPlayer rejected tuples allowed as session_start_rejected alternatives=false", markdown)
        self.assertIn("planned Obelisk build artifact available=false", markdown)
        self.assertIn("planned_obelisk_build_artifact_available=false", markdown)
        self.assertIn("planned_obelisk_build_artifact_source=not_provided", markdown)
        self.assertNotIn("--allow-diagnostic-candidates", markdown)
        self.assertIn("Exact approval scope required before any deploy or runtime evidence:", markdown)
        self.assertIn("scope_status=requires_exact_current_turn_operator_approval", markdown)
        self.assertIn("standing_approval_allowed=false", markdown)
        self.assertIn("request_pack_authorizes_deploy_or_runtime=false", markdown)
        self.assertIn(
            "required_operator_approval_fields=target,exact_target_instance_map,marker_env_gates,"
            "restart_window,player_presence_safety,player_notice_action,direct_join_plan,rollback,evidence_paths,"
            "runtime_triplet_contract,passive_wait_boundary,final_posture",
            markdown,
        )
        self.assertIn("player_presence_safety=restart_check_required:true broadcast_if_players:true request_pack_authorizes:false", markdown)
        self.assertIn("exact_target_instance_map=arkserver2/TheIsland aliases_allowed=false", markdown)
        self.assertIn(
            "direct_join_plan=direct_join_exact_server_map target=arkserver2/TheIsland third_server_allowed=false organic_wait_seconds=900",
            markdown,
        )
        self.assertIn(
            "beta_runtime_choreography=single_tester_direct_join "
            "observer_gate=ShooterGameMode.CheckJoinInProgress(1,0) "
            "mixed_transfer_reconnect_same_window_allowed=false "
            "counts_as_approved_runtime_evidence=false",
            markdown,
        )
        self.assertIn(
            f"evidence_path.window_request_json=/servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/window-request.json",
            markdown,
        )
        self.assertIn("runtime_triplet_contract.session_start_rejected=CheckJoinInProgress(1,0)", markdown)
        self.assertIn("runtime_triplet_contract.session_start_rejected.copied_bools=bIsFromLogin,ReturnValue=1,0", markdown)
        self.assertIn("runtime_triplet_contract.HandleNewPlayer_rejected_alternative=false", markdown)
        self.assertIn(
            "passive_wait_boundary=wait-only/passive is not approval; requested wait window checked only; active follow-up requires fresh exact current-turn scope",
            markdown,
        )
        self.assertIn("Drift-fix deployment intent:", markdown)
        self.assertIn("intent_type=lifecycle_anchor_drift_fix_deploy_request_only", markdown)
        self.assertIn("deployment_authorized=false", markdown)
        self.assertIn("counts_as_approved_runtime_evidence=false", markdown)
        self.assertIn("Post-window replay contract:", markdown)
        self.assertIn("preflight_pre_path=/servidor/ark/workspace-offline/live-validation-logs/", markdown)
        self.assertIn("operator_approval_request_path=/servidor/ark/workspace-offline/live-validation-logs/", markdown)
        self.assertIn("operator_approval_receipt_path=/servidor/ark/workspace-offline/live-validation-logs/", markdown)
        self.assertIn("copied_log_path=/servidor/ark/workspace-offline/live-validation-logs/", markdown)
        self.assertIn("completed operator-approval-receipt.json", markdown)
        self.assertIn("Required evidence sidecar commands:", markdown)
        post_run_lines = fenced_section(markdown, "Post-run verification commands:")
        self.assertEqual(post_run_lines[0], "requires_current_turn_operator_approval_before_execution=true")
        self.assertEqual(post_run_lines[1], "commands_authorize_runtime_or_public_readiness=false")
        sidecar_lines = fenced_section(markdown, "Required evidence sidecar commands:")
        self.assertEqual(sidecar_lines[0], "requires_current_turn_operator_approval_before_execution=true")
        self.assertEqual(sidecar_lines[1], "commands_authorize_runtime_or_public_readiness=false")
        self.assertTrue(sidecar_lines[2].startswith("scripts/check_player_principal_lifecycle_preflight.sh "))
        self.assertEqual(
            sidecar_lines[3],
            "# The ready-log copy helper copies Obelisk.log and generates/checks preflight-post.json plus window-manifest.env.",
        )
        self.assertTrue(sidecar_lines[4].startswith("scripts/copy_player_principal_lifecycle_ready_log.py "))
        self.assertEqual(sidecar_lines[5], "# Manual stable preflight fallback if the copy helper is not used:")
        self.assertTrue(sidecar_lines[6].startswith("scripts/check_player_principal_lifecycle_preflight.sh "))
        self.assertFalse(any(line.endswith("=true") for line in sidecar_lines if "authorize" in line or "readiness" in line))
        self.assertIn(
            "scripts/check_player_principal_lifecycle_preflight.sh --instance arkserver2 --target-map TheIsland "
            "--mode observer-window --env-file "
            f"/servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/observer-window.env "
            f"--expected-binary-sha256 {SHA} --run-id {request['run_id']} "
            f"--window-manifest /servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/window-manifest.env "
            f"--copied-log /servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/Obelisk.log "
            f"--evidence-dir /servidor/ark/workspace-offline/live-validation-logs/{request['run_id']} --json > "
            f"/servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/preflight-pre.json",
            markdown,
        )
        self.assertIn(
            "scripts/copy_player_principal_lifecycle_ready_log.py --instance arkserver2 "
            f"--evidence-dir /servidor/ark/workspace-offline/live-validation-logs/{request['run_id']} "
            f"--expected-binary-sha256 {SHA} "
            f"--fresh-window-start-utc {request['approved_window']['start_utc']} "
            f"--fresh-window-end-utc {request['approved_window']['end_utc']} "
            "--allow-live-log-read --allow-evidence-dir-write "
            "--allow-post-window-sidecar-generation --allow-post-window-preflight-live-read "
            "--execute --json",
            markdown,
        )
        self.assertIn(
            "scripts/check_player_principal_lifecycle_preflight.sh --instance arkserver2 --map TheIsland "
            f"--mode stable --expected-binary-sha256 {SHA} --run-id {request['run_id']} "
            f"--window-manifest /servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/window-manifest.env "
            f"--copied-log /servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/Obelisk.log "
            f"--evidence-dir /servidor/ark/workspace-offline/live-validation-logs/{request['run_id']} --json > "
            f"/servidor/ark/workspace-offline/live-validation-logs/{request['run_id']}/preflight-post.json",
            markdown,
        )
        self.assertIn("--post-window-replay", markdown)
        self.assertIn(
            "scripts/check_player_principal_lifecycle_preflight.sh --instance arkserver2 --map TheIsland "
            f"--mode stable --expected-binary-sha256 {SHA}",
            markdown,
        )
        self.assertIn(
            "scripts/check_obelisk_server_posture.sh --expect-stable --map TheIsland --instance arkserver2",
            markdown,
        )

    def test_prepares_standing_launch_authority_receipt_bound_to_exact_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            args = base_args(output_dir)
            args.insert(args.index("--json"), "--standing-launch-authority")
            result = subprocess.run(
                args,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            report = json.loads(result.stdout)
            request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))
            receipt = json.loads((output_dir / "operator-approval-receipt.json").read_text(encoding="utf-8"))
            markdown = (output_dir / "operator-approval-request.md").read_text(encoding="utf-8")

        self.assertTrue(report["standing_launch_authority_recorded"])
        self.assertTrue(report["operator_approval_receipt_written"])
        self.assertEqual(report["next_blocker"], "runtime_window_preflight_required")
        self.assertEqual(report["outputs"]["operator_approval_receipt"]["path"], str(output_dir / "operator-approval-receipt.json"))
        self.assertFalse(report["current_turn_operator_approval_required"])
        self.assertFalse(report["current_turn_approval_recorded"])
        self.assertTrue(report["standing_launch_authority_satisfies_operator_approval"])
        self.assertEqual(request["approval_required"], STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT)
        self.assertEqual(request["current_turn_approval_scope"]["status"], APPROVAL_SCOPE_STATUS_STANDING_LAUNCH_AUTHORITY)
        self.assertEqual(
            request["current_turn_approval_scope"]["source_required"],
            APPROVAL_SCOPE_SOURCE_REQUIRED_STANDING_LAUNCH_AUTHORITY,
        )
        self.assertTrue(request["current_turn_approval_scope"]["standing_approval_allowed"])
        self.assertFalse(request["current_turn_approval_scope"]["request_pack_authorizes_deploy_or_runtime"])
        self.assertFalse(request["passive_wait_boundary"]["active_followup_requires_fresh_exact_current_turn_scope"])
        self.assertTrue(request["passive_wait_boundary"]["active_followup_requires_recorded_standing_launch_authority"])
        self.assertEqual(receipt["status"], "completed_operator_receipt")
        self.assertTrue(receipt["receipt_completed"])
        self.assertFalse(receipt["operator_current_turn_approval_recorded"])
        self.assertTrue(receipt["standing_launch_authority_recorded"])
        self.assertTrue(receipt["standing_launch_authority_satisfies_operator_approval"])
        self.assertTrue(receipt["approval_scope"]["standing_approval"])
        self.assertFalse(receipt["approval_scope"]["reusable"])
        self.assertFalse(receipt["approval_scope"]["future_windows_authorized"])
        self.assertEqual(receipt["operator_completion"]["approved_by_role"], "operator")
        self.assertEqual(receipt["operator_completion"]["approval_source"], APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY)
        self.assertEqual(receipt["operator_completion"]["attestation"], APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY)
        self.assertEqual(receipt["bound_request_pack"]["current_turn_approval_scope"], request["current_turn_approval_scope"])
        for value in receipt["non_authorization_flags"].values():
            self.assertFalse(value)
        self.assertIn("standing_approval_allowed=true", markdown)
        self.assertIn("requires_bound_standing_launch_authority_receipt_before_execution=true", markdown)
        self.assertIn(
            "active follow-up requires completed receipt binding standing launch authority to this exact window",
            markdown,
        )
        self.assertNotIn("active follow-up requires fresh exact current-turn scope", markdown)

    def test_prepares_diagnostic_candidate_request_pack_without_evidence_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            args = base_args(output_dir)
            args.insert(args.index("--json"), "--diagnostic-candidates")
            result = subprocess.run(
                args,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            report = json.loads(result.stdout)
            request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))
            env_file = (output_dir / "observer-window.env").read_text(encoding="utf-8").splitlines()
            env = [line for line in env_file if not line.startswith("#")]
            markdown = (output_dir / "operator-approval-request.md").read_text(encoding="utf-8")

        self.assertTrue(report["diagnostic_candidates_enabled"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["deployment_intent"]["deployment_authorized"])
        self.assertFalse(report["deployment_intent"]["counts_as_approved_runtime_evidence"])
        self.assertTrue(request["diagnostic_candidates_enabled"])
        self.assertEqual(
            request["operator_live_ops_brief"]["feature_gates"]["candidate_diagnostics"],
            "candidate_only_non_evidence",
        )
        self.assertIn("diagnostic candidate lines do not count as approved runtime evidence", request["non_claims"])
        self.assertIn("OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1", env)
        self.assertEqual(env[-1], "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1")
        self.assertIn("diagnostic candidates enabled=true", markdown)
        self.assertIn("diagnostic candidate lines are non-evidence", markdown)
        self.assertIn("--allow-diagnostic-candidates --json", markdown)

    def test_prepares_planned_build_artifact_identity_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact_path = Path(tmp) / "libobelisk.so"
            artifact_bytes = b"planned obelisk runtime build\n"
            artifact_path.write_bytes(artifact_bytes)
            output_dir = Path(tmp) / "request"
            args = base_args(output_dir)
            args.insert(args.index("--json"), "--obelisk-build-artifact")
            args.insert(args.index("--json"), str(artifact_path))
            result = subprocess.run(
                args,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            report = json.loads(result.stdout)
            request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))
            markdown = (output_dir / "operator-approval-request.md").read_text(encoding="utf-8")

        expected_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
        build_artifact = request["planned_obelisk_build_identity"]["build_artifact"]
        self.assertTrue(build_artifact["available"])
        self.assertEqual(build_artifact["source"], "path_sha256")
        self.assertEqual(build_artifact["artifact_kind"], PLANNED_OBELISK_BUILD_ARTIFACT_KIND)
        self.assertEqual(build_artifact["artifact_name"], "libobelisk.so")
        self.assertEqual(build_artifact["artifact_sha256"], expected_sha256)
        self.assertEqual(build_artifact["size_bytes"], len(artifact_bytes))
        self.assertEqual(report["planned_obelisk_build_identity"], request["planned_obelisk_build_identity"])
        self.assertEqual(
            request["deployment_intent"]["planned_obelisk_build_identity"],
            request["planned_obelisk_build_identity"],
        )
        self.assertFalse(request["deployment_intent"]["deployment_authorized"])
        self.assertIn("planned Obelisk build artifact available=true", markdown)
        self.assertIn(f"planned_obelisk_build_artifact_sha256={expected_sha256}", markdown)

    def test_beta_user_policy_requires_notice_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp) / "request")
            args[args.index("--user-policy") + 1] = "operator_approved_beta_users"
            result = subprocess.run(args, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"--notice-path must be {APPROVED_BETA_NOTICE_PATH}", result.stderr)

    def test_beta_user_policy_records_notice_action_before_activation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            args = base_args(output_dir)
            args[args.index("--user-policy") + 1] = "operator_approved_beta_users"
            args.insert(args.index("--rollback-owner"), "--notice-path")
            args.insert(args.index("--rollback-owner"), "discord-beta-testers")
            result = subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            report = json.loads(result.stdout)
            request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))
            markdown = (output_dir / "operator-approval-request.md").read_text(encoding="utf-8")

        notice_action = request["player_notice_action"]
        self.assertEqual(report["status"], "prepared")
        self.assertTrue(notice_action["required"])
        self.assertEqual(notice_action["notice_path"], "discord-beta-testers")
        self.assertTrue(notice_action["approved_notice_path_must_be_named"])
        self.assertTrue(notice_action["dry_run_required_before_send"])
        self.assertTrue(notice_action["real_notice_send_required_before_activation"])
        self.assertFalse(notice_action["send_performed_by_request_pack"])
        self.assertFalse(notice_action["request_pack_authorizes_discord"])
        self.assertFalse(notice_action["activation_allowed_before_notice_sent"])
        self.assertEqual(notice_action["activation_blocker"], "approved_dry_run_checked_beta_testers_notice_sent")
        self.assertEqual(
            request["current_turn_approval_scope"]["required_named_scope"]["player_notice_action"],
            notice_action,
        )
        self.assertEqual(request["operator_live_ops_brief"]["player_notice_action"], notice_action)
        self.assertEqual(request["operator_live_ops_brief"]["notice_path"], "discord-beta-testers")
        self.assertIn("player notice real send required before activation=true", markdown)
        self.assertIn("player_notice_action=approved_dry_run_checked_beta_testers_notice_sent", markdown)

    def test_rejects_target_aliases_instead_of_exact_instance_and_map(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            public_identity_instance = base_args(Path(tmp) / "public-identity-instance")
            public_identity_instance[public_identity_instance.index("--instance") + 1] = "public-identity"
            public_identity_result = subprocess.run(
                public_identity_instance,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            sdk_ready_map = base_args(Path(tmp) / "sdk-ready-map")
            sdk_ready_map[sdk_ready_map.index("--map") + 1] = "sdk-ready"
            sdk_ready_result = subprocess.run(
                sdk_ready_map,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertNotEqual(public_identity_result.returncode, 0)
        self.assertIn("--instance must name an exact instance/map, not an alias", public_identity_result.stderr)
        self.assertNotEqual(sdk_ready_result.returncode, 0)
        self.assertIn("--map must name an exact instance/map, not an alias", sdk_ready_result.stderr)

    def test_rejects_bad_run_id_and_window_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_run = base_args(Path(tmp) / "bad-run")
            bad_run[bad_run.index("--run-id") + 1] = "latest"
            bad_run_result = subprocess.run(bad_run, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            bad_window = base_args(Path(tmp) / "bad-window")
            start = datetime.now(timezone.utc) + timedelta(hours=1)
            bad_window[bad_window.index("--run-id") + 1] = (
                start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle"
            )
            bad_window[bad_window.index("--approved-window-start-utc") + 1] = start.strftime("%Y-%m-%dT%H:%M:%SZ")
            bad_window[bad_window.index("--approved-window-end-utc") + 1] = (
                start - timedelta(minutes=1)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
            bad_window_result = subprocess.run(bad_window, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(bad_run_result.returncode, 0)
        self.assertIn("--run-id must match", bad_run_result.stderr)
        self.assertNotEqual(bad_window_result.returncode, 0)
        self.assertIn("must be before", bad_window_result.stderr)

    def test_rejects_expired_approved_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp) / "request")
            args[args.index("--run-id") + 1] = "20260101T120000Z-player-principal-lifecycle"
            args[args.index("--approved-window-start-utc") + 1] = "2026-01-01T12:00:00Z"
            args[args.index("--approved-window-end-utc") + 1] = "2026-01-01T12:10:00Z"
            result = subprocess.run(args, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be in the future", result.stderr)

    def test_rejects_approved_window_too_far_after_request_preparation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp) / "request")
            start = (datetime.now(timezone.utc) + timedelta(hours=2)).replace(microsecond=0)
            args[args.index("--run-id") + 1] = start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle"
            args[args.index("--approved-window-start-utc") + 1] = start.strftime("%Y-%m-%dT%H:%M:%SZ")
            args[args.index("--approved-window-end-utc") + 1] = (
                start + timedelta(minutes=10)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
            result = subprocess.run(args, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be within 1 hour of request preparation", result.stderr)

    def test_rejects_already_started_approved_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp) / "request")
            start = (datetime.now(timezone.utc) - timedelta(seconds=60)).replace(microsecond=0)
            end = (datetime.now(timezone.utc) + timedelta(minutes=5)).replace(microsecond=0)
            args[args.index("--run-id") + 1] = start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle"
            args[args.index("--approved-window-start-utc") + 1] = start.strftime("%Y-%m-%dT%H:%M:%SZ")
            args[args.index("--approved-window-end-utc") + 1] = end.strftime("%Y-%m-%dT%H:%M:%SZ")
            result = subprocess.run(args, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--approved-window-start-utc must be in the future", result.stderr)

    def test_rejects_run_id_window_start_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp) / "request")
            args[args.index("--run-id") + 1] = "20260601T120001Z-player-principal-lifecycle"
            result = subprocess.run(args, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must match --approved-window-start-utc exactly", result.stderr)

    def test_rejects_approved_window_longer_than_first_window_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp) / "request")
            start = datetime.strptime(
                args[args.index("--approved-window-start-utc") + 1],
                "%Y-%m-%dT%H:%M:%SZ",
            ).replace(tzinfo=timezone.utc)
            args[args.index("--approved-window-end-utc") + 1] = (
                start + timedelta(minutes=121)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
            result = subprocess.run(args, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duration must not exceed 120 minutes", result.stderr)

    def test_rejects_approved_window_shorter_than_exact_organic_wait(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp) / "request")
            start = datetime.strptime(
                args[args.index("--approved-window-start-utc") + 1],
                "%Y-%m-%dT%H:%M:%SZ",
            ).replace(tzinfo=timezone.utc)
            args[args.index("--approved-window-end-utc") + 1] = (
                start + timedelta(minutes=10)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
            result = subprocess.run(args, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duration must be at least 15 minutes", result.stderr)

    def test_rejects_stopped_posture_and_stop_after_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stop_after_window = base_args(Path(tmp) / "stop-after-window")
            stop_after_window[stop_after_window.index("--restart-expectation") + 1] = "stop-after-window"
            stop_after_window_result = subprocess.run(
                stop_after_window,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            stopped_posture = base_args(Path(tmp) / "stopped-posture")
            stopped_posture[stopped_posture.index("--final-posture") + 1] = "stopped"
            stopped_posture_result = subprocess.run(
                stopped_posture,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        guardrail = "downstream manifest and approved evidence checks require stable post posture"
        self.assertNotEqual(stop_after_window_result.returncode, 0)
        self.assertIn(guardrail, stop_after_window_result.stderr)
        self.assertNotEqual(stopped_posture_result.returncode, 0)
        self.assertIn(guardrail, stopped_posture_result.stderr)

    def test_accepts_stable_posture_for_non_stop_restart_expectations(self) -> None:
        for restart_expectation in ("none", "start", "restart"):
            with self.subTest(restart_expectation=restart_expectation):
                with tempfile.TemporaryDirectory() as tmp:
                    output_dir = Path(tmp) / "request"
                    args = base_args(output_dir)
                    args[args.index("--restart-expectation") + 1] = restart_expectation
                    subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))

                self.assertEqual(restart_expectation, request["restart_expectation"])
                self.assertEqual("stable", request["final_posture"])

    def test_stable_posture_never_emits_allow_stopped_post_run_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            args = base_args(output_dir)
            subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))

        self.assertEqual(
            request["operator_live_ops_brief"]["post_run_stable_posture"]["verification_commands"],
            [
                [
                    "scripts/check_player_principal_lifecycle_preflight.sh",
                    "--instance",
                    "arkserver2",
                    "--map",
                    "TheIsland",
                    "--mode",
                    "stable",
                    "--expected-binary-sha256",
                    SHA,
                ],
                [
                    "scripts/check_obelisk_server_posture.sh",
                    "--expect-stable",
                    "--map",
                    "TheIsland",
                    "--instance",
                    "arkserver2",
                ],
            ],
        )
        commands = request["operator_live_ops_brief"]["post_run_stable_posture"]["verification_commands"]
        self.assertFalse(any("--allow-stopped" in command for command in commands))

    def test_rejects_wrong_binary_sha_and_live_output_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wrong_sha = base_args(Path(tmp) / "wrong-sha")
            wrong_sha[wrong_sha.index("--binary-sha256") + 1] = "0" * 64
            wrong_sha_result = subprocess.run(wrong_sha, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(wrong_sha_result.returncode, 0)
        self.assertIn("must match reviewed ARK SHA256", wrong_sha_result.stderr)

        live_output = base_args(Path("/servidor/ark/obelisk/request-pack"))
        live_output_result = subprocess.run(live_output, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(live_output_result.returncode, 0)
        self.assertIn("OBELISK_ALLOW_SERVER_ROOT_WRITES=1", live_output_result.stderr)

    def test_rejects_placeholder_obelisk_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp) / "request")
            args[args.index("--obelisk-commit") + 1] = "test-commit"
            result = subprocess.run(args, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--obelisk-commit must be a reviewed 40-character lowercase Git SHA", result.stderr)

    def test_rejects_planned_build_artifact_sha_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact_path = Path(tmp) / "libobelisk.so"
            artifact_path.write_bytes(b"planned build\n")
            args = base_args(Path(tmp) / "request")
            args.insert(args.index("--json"), "--obelisk-build-artifact")
            args.insert(args.index("--json"), str(artifact_path))
            args.insert(args.index("--json"), "--obelisk-build-artifact-sha256")
            args.insert(args.index("--json"), "0" * 64)
            result = subprocess.run(args, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--obelisk-build-artifact-sha256 must match --obelisk-build-artifact", result.stderr)

    def test_rejects_planned_build_artifact_public_or_sdk_alias_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact_path = Path(tmp) / "libobelisk.so"
            artifact_path.write_bytes(b"planned build\n")
            args = base_args(Path(tmp) / "request")
            args.insert(args.index("--json"), "--obelisk-build-artifact")
            args.insert(args.index("--json"), str(artifact_path))
            args.insert(args.index("--json"), "--obelisk-build-artifact-label")
            args.insert(args.index("--json"), "sdk-ready")
            result = subprocess.run(args, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--obelisk-build-artifact-label must not use SDK-ready/public-identity aliases", result.stderr)


if __name__ == "__main__":
    unittest.main()
