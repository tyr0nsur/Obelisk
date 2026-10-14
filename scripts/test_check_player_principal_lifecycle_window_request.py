#!/usr/bin/env python3
"""Tests for check_player_principal_lifecycle_window_request.py."""

from __future__ import annotations

import json
import hashlib
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PREPARE = SCRIPT_DIR / "prepare_player_principal_lifecycle_window_request.py"
CHECK = SCRIPT_DIR / "check_player_principal_lifecycle_window_request.py"
TEST_COMMIT = "1" * 40
_FAKE_GIT_DIR = tempfile.TemporaryDirectory()
_FAKE_GIT = Path(_FAKE_GIT_DIR.name) / "git"
_FAKE_GIT.write_text(
    f"""#!/bin/sh
if [ "$1" = "rev-parse" ]; then
  printf '%s\\n' "{TEST_COMMIT}"
  exit 0
fi
if [ "$1" = "cat-file" ] && [ "$2" = "-e" ]; then
  commit="$3"
  commit="${{commit%%^*}}"
  if [ "$commit" = "{TEST_COMMIT}" ]; then
    exit 0
  fi
fi
exit 1
""",
    encoding="utf-8",
)
_FAKE_GIT.chmod(0o755)
_FAKE_GIT_ENV = {
    **os.environ,
    "PATH": f"{_FAKE_GIT_DIR.name}{os.pathsep}{os.environ['PATH']}",
}

sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("check_player_principal_lifecycle_window_request", CHECK)
assert SPEC is not None and SPEC.loader is not None
REQUEST_CHECKER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REQUEST_CHECKER
SPEC.loader.exec_module(REQUEST_CHECKER)
from prepare_player_principal_lifecycle_window_request import (  # noqa: E402
    APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY,
    APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY,
    APPROVAL_SCOPE_STATUS,
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
    operator_approval_receipt_payload,
)


SHA = EXPECTED_BINARY_SHA256


def prepare_args(output_dir: Path) -> list[str]:
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    end = start + timedelta(minutes=15)
    run_id = start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle"
    return [
        sys.executable,
        str(PREPARE),
        "--instance",
        "arkserver2",
        "--map",
        "TheIsland",
        "--run-id",
        run_id,
        "--obelisk-commit",
        TEST_COMMIT,
        "--approved-window-start-utc",
        start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "--approved-window-end-utc",
        end.strftime("%Y-%m-%dT%H:%M:%SZ"),
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


def prepare_beta_args(output_dir: Path) -> list[str]:
    args = prepare_args(output_dir)
    args[args.index("--user-policy") + 1] = "operator_approved_beta_users"
    args.extend(["--notice-path", APPROVED_BETA_NOTICE_PATH])
    return args


def prepare_pack(output_dir: Path) -> None:
    subprocess.run(
        prepare_args(output_dir),
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_FAKE_GIT_ENV,
    )


def prepare_beta_pack(output_dir: Path) -> None:
    subprocess.run(
        prepare_beta_args(output_dir),
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_FAKE_GIT_ENV,
    )


def prepare_standing_launch_authority_pack(output_dir: Path) -> None:
    args = prepare_args(output_dir)
    args.insert(args.index("--json"), "--standing-launch-authority")
    subprocess.run(
        args,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_FAKE_GIT_ENV,
    )


def add_seconds(timestamp: str, seconds: int) -> str:
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(timezone.utc)
    return (dt + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_completed_receipt(
    output_dir: Path,
    receipt_path: Path | None = None,
    *,
    approved_at_utc: str | None = None,
) -> Path:
    request_path = output_dir / "window-request.json"
    env_path = output_dir / "observer-window.env"
    operator_request_path = output_dir / "operator-approval-request.md"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    approval_time = approved_at_utc or add_seconds(request["prepared_at_utc"], 1)
    receipt = operator_approval_receipt_payload(
        request,
        request_json_path=request_path,
        request_md_path=operator_request_path,
        env_path=env_path,
        operator_approved=True,
        operator_reference="operator",
        approved_at_utc=approval_time,
    )
    path = receipt_path or (output_dir / "operator-approval-receipt.json")
    path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_post_window_replay_sidecars(output_dir: Path) -> None:
    (output_dir / "preflight-pre.json").write_text('{"schema":"test.preflight-pre"}\n', encoding="utf-8")
    (output_dir / "preflight-post.json").write_text('{"schema":"test.preflight-post"}\n', encoding="utf-8")
    (output_dir / "window-manifest.env").write_text("RUN_ID=test\n", encoding="utf-8")
    (output_dir / "Obelisk.log").write_text("[test] copied obelisk log\n", encoding="utf-8")


class CheckPlayerPrincipalLifecycleWindowRequestTests(unittest.TestCase):
    def run_checker(
        self,
        output_dir: Path,
        *,
        check: bool = True,
        extra_args: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [
                sys.executable,
                str(CHECK),
                str(output_dir / "window-request.json"),
                "--env-file",
                str(output_dir / "observer-window.env"),
                *(extra_args or []),
                "--json",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_FAKE_GIT_ENV,
        )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def test_accepts_prepared_request_pack_without_authorizing_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            result = self.run_checker(output_dir)
            report = json.loads(result.stdout)
            request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))
            request_sha256 = hashlib.sha256((output_dir / "window-request.json").read_bytes()).hexdigest()
            env_sha256 = hashlib.sha256((output_dir / "observer-window.env").read_bytes()).hexdigest()
            operator_request_sha256 = hashlib.sha256(
                (output_dir / "operator-approval-request.md").read_bytes()
            ).hexdigest()

        self.assertTrue(report["ready"])
        self.assertTrue(report["request_pack_ready"])
        self.assertEqual(report["ready_scope"], "offline_request_pack_validation_only")
        self.assertEqual(
            report["request_pack_artifacts"]["window_request_json"]["sha256"],
            request_sha256,
        )
        self.assertEqual(
            report["request_pack_artifacts"]["observer_window_env"]["sha256"],
            env_sha256,
        )
        self.assertEqual(
            report["request_pack_artifacts"]["operator_approval_request_md"]["sha256"],
            operator_request_sha256,
        )
        self.assertIsNone(report["request_pack_artifacts"]["operator_approval_receipt_json"])
        self.assertEqual(report["request_pack_digest"]["algorithm"], "sha256")
        self.assertEqual(
            report["request_pack_digest"]["domain"],
            "obelisk.player-principal-lifecycle.request-pack.v1",
        )
        self.assertTrue(report["current_turn_operator_approval_required"])
        self.assertFalse(report["current_turn_approval_recorded"])
        self.assertFalse(report["request_pack_records_current_turn_approval"])
        self.assertEqual(report["authorization_source"], "none_request_pack_check_only")
        self.assertEqual(report["approved_runtime_evidence_source"], "none_request_pack_check_only")
        self.assertTrue(report["planning_only"])
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
        self.assertEqual(report["exact_target_scope"]["schema"], EXACT_TARGET_SCOPE_SCHEMA)
        self.assertFalse(report["exact_target_scope"]["instance_alias_allowed"])
        self.assertFalse(report["exact_target_scope"]["map_alias_allowed"])
        self.assertEqual(report["passive_wait_boundary"]["schema"], PASSIVE_WAIT_BOUNDARY_SCHEMA)
        self.assertEqual(report["direct_join_plan"]["schema"], DIRECT_JOIN_PLAN_SCHEMA)
        self.assertEqual(report["direct_join_plan"], request["direct_join_plan"])
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
        self.assertFalse(report["direct_join_plan"]["organic_wait_window_counts_as_approved_runtime_evidence"])
        self.assertTrue(report["direct_join_plan"]["receipt_before_activation_required"])
        self.assertTrue(report["direct_join_plan"]["post_window_replay_requires_receipt"])
        choreography = report["direct_join_plan"]["beta_runtime_choreography"]
        self.assertEqual(choreography, request["direct_join_plan"]["beta_runtime_choreography"])
        self.assertEqual(choreography["schema"], BETA_RUNTIME_CHOREOGRAPHY_SCHEMA)
        self.assertEqual(choreography["target"], report["target"])
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
        self.assertEqual(
            choreography["observer_gate_required_before_logout"],
            "ShooterGameMode.CheckJoinInProgress(1,0)",
        )
        observer_gate = choreography["observer_gate"]
        self.assertEqual(observer_gate["required_role"], "session_start_rejected")
        self.assertEqual(observer_gate["required_function"], "ShooterGameMode.CheckJoinInProgress")
        self.assertEqual(observer_gate["required_call"], "CheckJoinInProgress(1,0)")
        self.assertEqual(observer_gate["required_copied_bool_fields"], ["bIsFromLogin", "ReturnValue"])
        self.assertEqual(observer_gate["required_copied_bool_values"], ["1", "0"])
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
        self.assertFalse(report["discord_authorized"])
        self.assertFalse(report["discord_send_authorized"])
        self.assertFalse(report["discord_sent"])
        self.assertFalse(report["marker_env_changes_authorized"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["sdk_accounting_counts_as_completed_surface"])
        self.assertFalse(report["p0_accounting_counts_as_promoted_surface"])
        self.assertEqual(report["next_blocker"], "operator_current_turn_runtime_window_approval_required")
        self.assertEqual(report["current_turn_approval_scope_status"], APPROVAL_SCOPE_STATUS)
        self.assertEqual(report["current_turn_approval_required_fields"], CURRENT_TURN_APPROVAL_REQUIRED_FIELDS)
        self.assertEqual(report["deployment_intent"]["intent_type"], DRIFT_FIX_DEPLOYMENT_INTENT_TYPE)
        self.assertTrue(report["deployment_intent"]["request_only"])
        self.assertFalse(report["deployment_intent"]["deployment_authorized"])
        self.assertFalse(report["deployment_intent"]["restart_authorized"])
        self.assertFalse(report["deployment_intent"]["runtime_capture_authorized"])
        self.assertFalse(report["deployment_intent"]["counts_as_approved_runtime_evidence"])
        self.assertEqual(report["planned_obelisk_build_identity"], request["planned_obelisk_build_identity"])
        self.assertEqual(
            report["runtime_triplet_contract"]["session_start_rejected"]["required_copied_bool_fields"],
            ["bIsFromLogin", "ReturnValue"],
        )
        self.assertEqual(
            report["runtime_triplet_contract"]["session_start_rejected"]["required_copied_bool_values"],
            ["1", "0"],
        )
        self.assertFalse(report["planned_obelisk_build_identity"]["build_artifact"]["available"])
        self.assertEqual(report["planned_obelisk_build_identity"]["build_artifact"]["source"], "not_provided")
        self.assertRegex(request["prepared_at_utc"], r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
        self.assertLess(request["prepared_at_utc"], request["approved_window"]["start_utc"])
        self.assertEqual(AUTHORIZATION_FLAGS, request["authorization_flags"])
        self.assertEqual(request["exact_target_scope"]["schema"], EXACT_TARGET_SCOPE_SCHEMA)
        self.assertEqual(request["exact_target_scope"]["instance"], "arkserver2")
        self.assertEqual(request["exact_target_scope"]["map"], "TheIsland")
        self.assertFalse(request["exact_target_scope"]["instance_alias_allowed"])
        self.assertFalse(request["exact_target_scope"]["map_alias_allowed"])
        self.assertEqual(request["passive_wait_boundary"]["schema"], PASSIVE_WAIT_BOUNDARY_SCHEMA)
        self.assertEqual(request["direct_join_plan"]["schema"], DIRECT_JOIN_PLAN_SCHEMA)
        self.assertEqual(request["direct_join_plan"]["target"], request["target"])
        self.assertTrue(request["direct_join_plan"]["fastest_clean_theisland_direct_join"])
        self.assertFalse(request["direct_join_plan"]["third_ark_server_allowed"])
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
        self.assertFalse(request["passive_wait_boundary"]["active_followup_requires_recorded_standing_launch_authority"])
        player_safety = request["player_presence_safety"]
        self.assertEqual(player_safety["schema"], PLAYER_PRESENCE_SAFETY_SCHEMA)
        self.assertEqual(player_safety["target"], request["target"])
        self.assertEqual(player_safety["restart_expectation"], "restart")
        self.assertTrue(player_safety["connected_player_check_required_before_restart"])
        self.assertTrue(player_safety["rcon_broadcast_required_if_players_connected"])
        self.assertTrue(player_safety["restart_must_be_cancelled_or_rescheduled_if_players_remain_connected"])
        self.assertFalse(player_safety["player_check_or_broadcast_authorized_by_request_pack"])
        notice_action = request["player_notice_action"]
        self.assertEqual(notice_action["schema"], PLAYER_NOTICE_ACTION_SCHEMA)
        self.assertFalse(notice_action["required"])
        self.assertEqual(notice_action["notice_path"], "not_applicable")
        self.assertFalse(notice_action["dry_run_required_before_send"])
        self.assertFalse(notice_action["real_notice_send_required_before_activation"])
        self.assertFalse(notice_action["send_performed_by_request_pack"])
        self.assertFalse(notice_action["request_pack_authorizes_discord"])
        self.assertTrue(notice_action["activation_allowed_before_notice_sent"])
        self.assertEqual(notice_action["activation_blocker"], "no_player_notice_required")
        self.assertEqual(request["current_turn_approval_scope"]["status"], APPROVAL_SCOPE_STATUS)
        self.assertEqual(
            request["current_turn_approval_scope"]["required_operator_approval_fields"],
            CURRENT_TURN_APPROVAL_REQUIRED_FIELDS,
        )
        self.assertFalse(request["current_turn_approval_scope"]["standing_approval_allowed"])
        self.assertFalse(request["current_turn_approval_scope"]["request_pack_authorizes_deploy_or_runtime"])
        self.assertTrue(request["current_turn_approval_scope"]["missing_or_ambiguous_scope_blocks_window"])
        self.assertEqual(request["deployment_intent"], report["deployment_intent"])
        self.assertEqual(request["deployment_intent"]["planned_obelisk_build_identity"], request["planned_obelisk_build_identity"])
        self.assertEqual(request["planned_obelisk_build_identity"]["obelisk_commit"], TEST_COMMIT)
        self.assertIn("does not claim public readiness", request["planned_obelisk_build_identity"]["non_authorization"])
        self.assertIn("does not claim SDK readiness", request["planned_obelisk_build_identity"]["non_authorization"])
        self.assertIn("does not claim operator approval or authorization", request["non_claims"])
        self.assertTrue(report["operator_request_verified"])
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertEqual(report["target"], {"instance": "arkserver2", "map": "TheIsland"})
        self.assertIn("does not authorize server operations", report["non_claims"][1])
        brief = request["operator_live_ops_brief"]
        self.assertEqual({"instance": "arkserver2", "map": "TheIsland"}, brief["target"])
        self.assertEqual(request["exact_target_scope"], brief["exact_target_scope"])
        self.assertEqual(request["passive_wait_boundary"], brief["passive_wait_boundary"])
        self.assertEqual(
            request["rollback"]["marker_state_dir"],
            "/servidor/ark/obelisk/state/instances/arkserver2",
        )
        self.assertEqual(
            request["rollback"]["stable_marker_paths"]["disable_plugins"],
            "/servidor/ark/obelisk/state/instances/arkserver2/disable-plugins",
        )
        self.assertEqual(
            request["rollback"]["observer_marker_paths"]["allow_observer_debug_window"],
            "/servidor/ark/obelisk/state/instances/arkserver2/allow-observer-debug-window",
        )
        self.assertEqual(SHA, brief["server_binary"]["sha256"])
        self.assertEqual("player_principal_lifecycle_only", brief["feature_gates"]["observer"])
        self.assertEqual(0, brief["feature_gates"]["dispatch_limit"])
        self.assertEqual(10, brief["feature_gates"]["log_limit"])
        self.assertEqual(brief["player_notice_action"], request["player_notice_action"])
        self.assertEqual(brief["direct_join_plan"], request["direct_join_plan"])
        self.assertEqual(brief["player_presence_safety"], request["player_presence_safety"])
        self.assertEqual("stable", brief["post_run_stable_posture"]["expected"])
        self.assertEqual(
            request["post_window_replay_contract"]["sidecars"]["operator_approval_receipt_path"],
            brief["evidence_capture"]["operator_approval_receipt_path"],
        )
        self.assertEqual(
            request["post_window_replay_contract"]["sidecars"]["request_pack_path"],
            brief["evidence_capture"]["request_pack_path"],
        )
        self.assertEqual(
            request["post_window_replay_contract"]["sidecars"]["observer_env_path"],
            brief["evidence_capture"]["observer_env_path"],
        )
        self.assertEqual(
            request["post_window_replay_contract"]["sidecars"]["operator_approval_request_path"],
            brief["evidence_capture"]["operator_approval_request_path"],
        )
        self.assertEqual(
            request["post_window_replay_contract"]["sidecars"]["preflight_pre_path"],
            brief["evidence_capture"]["preflight_pre_path"],
        )
        self.assertEqual(
            request["post_window_replay_contract"]["sidecars"]["preflight_post_path"],
            brief["evidence_capture"]["preflight_post_path"],
        )
        self.assertEqual(request["run_id"], brief["artifact_binding"]["run_id"])
        self.assertEqual(
            request["post_window_replay_contract"]["sidecars"]["window_manifest_path"],
            brief["artifact_binding"]["required_sidecars"]["window_manifest_env"],
        )
        self.assertEqual(
            request["post_window_replay_contract"]["sidecars"]["operator_approval_request_path"],
            brief["artifact_binding"]["required_sidecars"]["operator_approval_request_md"],
        )
        self.assertEqual(
            request["post_window_replay_contract"]["sidecars"]["copied_log_path"],
            brief["artifact_binding"]["required_sidecars"]["copied_obelisk_log"],
        )
        self.assertEqual("exact_run_id_window_artifacts_only", brief["artifact_binding"]["binding_claim"])
        self.assertEqual(request["deployment_intent"], brief["deployment_intent"])
        self.assertEqual("completed_operator_receipt", brief["evidence_capture"]["operator_approval_receipt_required"])
        self.assertIn("does not authorize server operations, marker/env changes", brief["non_authorization"])
        self.assertEqual(
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
            brief["post_run_stable_posture"]["verification_commands"],
        )

    def test_rejects_beta_user_notice_path_that_is_not_approved_beta_testers_channel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_beta_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["notice_path"] = "other-discord-channel"
            request["player_notice_action"]["notice_path"] = "other-discord-channel"
            request_path.write_text(json.dumps(request, sort_keys=True) + "\n", encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("beta_user_policy_requires_approved_beta_testers_notice_path", report["blockers"])
        self.assertIn("player_notice_action_beta_notice_path_not_approved_beta_testers", report["blockers"])

    def test_rejects_notice_path_set_when_no_regular_users_policy_does_not_need_notice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["notice_path"] = APPROVED_BETA_NOTICE_PATH
            request["player_notice_action"]["notice_path"] = APPROVED_BETA_NOTICE_PATH
            request_path.write_text(json.dumps(request, sort_keys=True) + "\n", encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no_regular_users_requires_notice_path_not_applicable", report["blockers"])
        self.assertIn("player_notice_action_notice_path_set_for_no_regular_users", report["blockers"])

    def test_rejects_env_snapshot_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            env_path = output_dir / "observer-window.env"
            env_path.write_text(
                env_path.read_text(encoding="utf-8").replace(
                    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=0",
                    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT=1",
                ),
                encoding="utf-8",
            )
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("observer_env_snapshot_mismatch", report["blockers"])
        self.assertIn("observer_env_required_key_missing_or_mismatch", report["blockers"])
        self.assertIn("operator_live_ops_brief_mismatch", report["blockers"])

    def test_accepts_planned_build_artifact_identity_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact_path = Path(tmp) / "libobelisk.so"
            artifact_bytes = b"planned obelisk runtime build\n"
            artifact_path.write_bytes(artifact_bytes)
            output_dir = Path(tmp) / "request"
            args = prepare_args(output_dir)
            args.insert(args.index("--json"), "--obelisk-build-artifact")
            args.insert(args.index("--json"), str(artifact_path))
            subprocess.run(
                args,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=_FAKE_GIT_ENV,
            )
            result = self.run_checker(output_dir)
            report = json.loads(result.stdout)
            request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))

        expected_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
        build_artifact = report["planned_obelisk_build_identity"]["build_artifact"]
        self.assertTrue(report["ready"])
        self.assertTrue(build_artifact["available"])
        self.assertEqual(build_artifact["source"], "path_sha256")
        self.assertEqual(build_artifact["artifact_kind"], PLANNED_OBELISK_BUILD_ARTIFACT_KIND)
        self.assertEqual(build_artifact["artifact_sha256"], expected_sha256)
        self.assertEqual(report["deployment_intent"], request["deployment_intent"])

    def test_rejects_operator_live_ops_brief_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["operator_live_ops_brief"]["feature_gates"]["dispatch_limit"] = 1
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operator_live_ops_brief_mismatch", report["blockers"])

    def test_rejects_authorization_flags_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["authorization_flags"]["runtime_work_authorized"] = True
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("authorization_flags_mismatch", report["blockers"])
        self.assertIn("authorization_flag_runtime_work_authorized_not_false", report["blockers"])

    def test_rejects_missing_current_turn_approval_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request.pop("current_turn_approval_scope")
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_missing_required", report["blockers"])
        self.assertIn("current_turn_approval_scope_not_object", report["blockers"])
        self.assertIn("operator_request_markdown_projection_failed", report["blockers"])

    def test_rejects_ambiguous_current_turn_approval_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["current_turn_approval_scope"]["status"] = "standing_or_prior_operator_approval"
            request["current_turn_approval_scope"]["standing_approval_allowed"] = True
            request["current_turn_approval_scope"]["required_operator_approval_fields"] = ["target"]
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("current_turn_approval_scope_status_mismatch", report["blockers"])
        self.assertIn("current_turn_approval_scope_standing_approval_allowed_not_false", report["blockers"])
        self.assertIn("current_turn_approval_scope_required_fields_mismatch", report["blockers"])
        self.assertIn("current_turn_approval_scope_mismatch", report["blockers"])

    def test_rejects_target_public_identity_or_sdk_ready_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["target"]["instance"] = "public-identity"
            request["target"]["map"] = "sdk-ready"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("target_instance_alias_not_exact", report["blockers"])
        self.assertIn("target_map_alias_not_exact", report["blockers"])
        self.assertIn("exact_target_scope_instance_mismatch", report["blockers"])
        self.assertIn("passive_wait_boundary_target_mismatch", report["blockers"])
        self.assertIn("forbidden_public_capability_or_readiness_claim", report["blockers"])

    def test_rejects_generic_positive_sidecar_status_aliases(self) -> None:
        cases = (
            ("approved", True),
            ("accepted", "yes"),
            ("ready", 1),
            ("complete", {"value": "true"}),
            ("current_turn_authorized", True),
        )
        for key, value in cases:
            with self.subTest(key=key):
                with tempfile.TemporaryDirectory() as tmp:
                    output_dir = Path(tmp) / "request"
                    prepare_pack(output_dir)
                    request_path = output_dir / "window-request.json"
                    request = json.loads(request_path.read_text(encoding="utf-8"))
                    request["sidecar_shortcut"] = {key: value}
                    request_path.write_text(json.dumps(request), encoding="utf-8")
                    result = self.run_checker(output_dir, check=False)
                    report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("forbidden_public_capability_or_readiness_claim", report["blockers"])
                details = [
                    item
                    for item in report["blocker_details"]
                    if item["reason"] == "forbidden_public_capability_or_readiness_claim"
                ]
                self.assertEqual(details[0]["label"], f"$.sidecar_shortcut.{key}")
                self.assertFalse(report["runtime_ready"])
                self.assertFalse(report["approved_runtime_evidence_ready"])

    def test_rejects_passive_wait_boundary_authorization_or_approval_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["passive_wait_boundary"]["requested_wait_window_seconds"] = MAX_APPROVED_WINDOW_SECONDS + 1
            request["passive_wait_boundary"]["requested_wait_window_authorizes_current_turn_approval"] = True
            request["passive_wait_boundary"]["wait_only_or_passive_monitor_authorizes_deploy_or_restart"] = True
            request["passive_wait_boundary"]["non_authorization"] = "passive wait is approval"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "passive_wait_boundary_requested_wait_window_seconds_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "passive_wait_boundary_requested_wait_window_seconds_too_long",
            report["blockers"],
        )
        self.assertIn(
            "passive_wait_boundary_requested_wait_window_authorizes_current_turn_approval_not_false",
            report["blockers"],
        )
        self.assertIn(
            "passive_wait_boundary_wait_only_or_passive_monitor_authorizes_deploy_or_restart_not_false",
            report["blockers"],
        )
        self.assertIn("passive_wait_boundary_non_authorization_mismatch", report["blockers"])
        self.assertIn("passive_wait_boundary_mismatch", report["blockers"])
        self.assertIn("forbidden_public_capability_or_readiness_claim", report["blockers"])

    def test_rejects_direct_join_plan_drift_or_transfer_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["direct_join_plan"]["cluster_transfer_required"] = True
            request["direct_join_plan"]["third_ark_server_allowed"] = True
            request["direct_join_plan"]["organic_wait_window_seconds"] = 600
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("direct_join_plan_cluster_transfer_required_not_false", report["blockers"])
        self.assertIn("direct_join_plan_third_ark_server_allowed_not_false", report["blockers"])
        self.assertIn("direct_join_plan_organic_wait_window_seconds_mismatch", report["blockers"])
        self.assertIn("direct_join_plan_mismatch", report["blockers"])
        self.assertIn("current_turn_approval_scope_mismatch", report["blockers"])
        self.assertIn("operator_live_ops_brief_mismatch", report["blockers"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["approved_runtime_evidence_ready"])

    def test_rejects_malformed_or_overclaiming_beta_runtime_choreography(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_beta_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            choreography = request["direct_join_plan"]["beta_runtime_choreography"]
            choreography["tester_count_required"] = 2
            choreography["single_tester_only"] = False
            choreography["cluster_transfer_allowed"] = True
            choreography["reconnect_before_exact_checkjoin_allowed"] = True
            choreography["mixed_transfer_reconnect_same_approved_window_allowed"] = True
            choreography["counts_as_approved_runtime_evidence"] = True
            choreography["runtime_ready"] = True
            choreography["observer_gate"]["required_call"] = "CheckJoinInProgress(1,1)"
            choreography["stale_or_diagnostic_exact_checkjoin_boundary"]["counts_as_runtime_evidence"] = True
            request_path.write_text(json.dumps(request, sort_keys=True) + "\n", encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "direct_join_plan_beta_runtime_choreography_tester_count_required_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "direct_join_plan_beta_runtime_choreography_single_tester_only_not_true",
            report["blockers"],
        )
        self.assertIn(
            "direct_join_plan_beta_runtime_choreography_cluster_transfer_allowed_not_false",
            report["blockers"],
        )
        self.assertIn(
            "direct_join_plan_beta_runtime_choreography_reconnect_before_exact_checkjoin_allowed_not_false",
            report["blockers"],
        )
        self.assertIn(
            "direct_join_plan_beta_runtime_choreography_mixed_transfer_reconnect_same_approved_window_allowed_not_false",
            report["blockers"],
        )
        self.assertIn(
            "direct_join_plan_beta_runtime_choreography_counts_as_approved_runtime_evidence_not_false",
            report["blockers"],
        )
        self.assertIn(
            "direct_join_plan_beta_runtime_choreography_runtime_ready_not_false",
            report["blockers"],
        )
        self.assertIn(
            "direct_join_plan_beta_runtime_choreography_observer_gate_required_call_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "direct_join_plan_checkjoin_stimulus_boundary_counts_as_runtime_evidence_not_false",
            report["blockers"],
        )
        self.assertIn("direct_join_plan_beta_runtime_choreography_mismatch", report["blockers"])
        self.assertIn("direct_join_plan_mismatch", report["blockers"])
        self.assertIn("current_turn_approval_scope_mismatch", report["blockers"])
        self.assertIn("operator_live_ops_brief_mismatch", report["blockers"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["approved_runtime_evidence_ready"])

    def test_rejects_runtime_triplet_contract_without_exact_copied_bool_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            rejected = request["runtime_triplet_contract"]["session_start_rejected"]
            rejected["required_copied_bool_values"] = ["0", "0"]
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "runtime_triplet_contract_session_start_copied_bool_values_mismatch",
            report["blockers"],
        )
        self.assertIn("runtime_triplet_contract_mismatch", report["blockers"])
        self.assertIn("current_turn_approval_scope_mismatch", report["blockers"])
        self.assertIn("operator_live_ops_brief_mismatch", report["blockers"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_rollback_without_named_marker_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["rollback"]["stable_marker_paths"]["disable_plugins"] = ""
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("rollback_stable_marker_path_disable_plugins_not_named", report["blockers"])
        self.assertIn("rollback_mismatch", report["blockers"])
        self.assertIn("current_turn_approval_scope_mismatch", report["blockers"])

    def test_rejects_approval_scope_without_named_evidence_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["current_turn_approval_scope"]["required_named_scope"]["evidence_paths"][
                "copied_obelisk_log"
            ] = ""
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("current_turn_approval_scope_evidence_path_copied_obelisk_log_not_named", report["blockers"])
        self.assertIn("current_turn_approval_scope_mismatch", report["blockers"])

    def test_rejects_drift_fix_deployment_intent_authorization_or_evidence_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["deployment_intent"]["request_only"] = False
            request["deployment_intent"]["deployment_authorized"] = True
            request["deployment_intent"]["runtime_capture_authorized"] = True
            request["deployment_intent"]["counts_as_approved_runtime_evidence"] = True
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("deployment_intent_request_only_not_true", report["blockers"])
        self.assertIn("deployment_intent_deployment_authorized_not_false", report["blockers"])
        self.assertIn("deployment_intent_runtime_capture_authorized_not_false", report["blockers"])
        self.assertIn("deployment_intent_counts_as_approved_runtime_evidence_not_false", report["blockers"])
        self.assertIn("deployment_intent_mismatch", report["blockers"])

    def test_rejects_player_presence_safety_authorization_or_missing_restart_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            safety = request["player_presence_safety"]
            safety["connected_player_check_required_before_restart"] = False
            safety["rcon_broadcast_required_if_players_connected"] = False
            safety["restart_must_be_cancelled_or_rescheduled_if_players_remain_connected"] = False
            safety["player_check_or_broadcast_authorized_by_request_pack"] = True
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("player_presence_safety_connected_player_check_required_before_restart_mismatch", report["blockers"])
        self.assertIn("player_presence_safety_rcon_broadcast_required_if_players_connected_mismatch", report["blockers"])
        self.assertIn(
            "player_presence_safety_restart_must_be_cancelled_or_rescheduled_if_players_remain_connected_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "player_presence_safety_player_check_or_broadcast_authorized_by_request_pack_not_false",
            report["blockers"],
        )
        self.assertIn("player_presence_safety_mismatch", report["blockers"])
        self.assertIn("current_turn_approval_scope_mismatch", report["blockers"])
        self.assertIn("operator_live_ops_brief_mismatch", report["blockers"])

    def test_rejects_missing_planned_obelisk_build_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request.pop("planned_obelisk_build_identity")
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_missing_required", report["blockers"])
        self.assertIn("planned_obelisk_build_identity_not_object", report["blockers"])
        self.assertIn("operator_request_markdown_projection_failed", report["blockers"])

    def test_rejects_invalid_planned_build_artifact_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            build_artifact = request["planned_obelisk_build_identity"]["build_artifact"]
            build_artifact["available"] = True
            build_artifact["source"] = "not_provided"
            build_artifact["artifact_kind"] = PLANNED_OBELISK_BUILD_ARTIFACT_KIND
            build_artifact["artifact_name"] = "libobelisk.so"
            build_artifact["artifact_sha256"] = "not-a-sha"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("planned_obelisk_build_artifact_available_source_not_provided", report["blockers"])
        self.assertIn("planned_obelisk_build_artifact_sha256_invalid", report["blockers"])
        self.assertIn("deployment_intent_planned_obelisk_build_identity_mismatch", report["blockers"])

    def test_rejects_planned_build_artifact_public_or_sdk_alias_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            build_artifact = request["planned_obelisk_build_identity"]["build_artifact"]
            build_artifact["available"] = True
            build_artifact["source"] = "operator_supplied_sha256"
            build_artifact["artifact_kind"] = PLANNED_OBELISK_BUILD_ARTIFACT_KIND
            build_artifact["artifact_name"] = "public-identity"
            build_artifact["artifact_sha256"] = "1" * 64
            build_artifact["size_bytes"] = None
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("planned_obelisk_build_artifact_name_alias_not_allowed", report["blockers"])
        self.assertIn("forbidden_public_capability_or_readiness_claim", report["blockers"])

    def test_rejects_planned_build_identity_auth_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["planned_obelisk_build_identity"]["non_authorization"] = "SDK readiness is ready"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("planned_obelisk_build_identity_non_authorization_mismatch", report["blockers"])
        self.assertIn("forbidden_public_capability_or_readiness_claim", report["blockers"])

    def test_rejects_deployment_intent_missing_planned_build_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["deployment_intent"].pop("planned_obelisk_build_identity")
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("deployment_intent_missing_required", report["blockers"])
        self.assertIn("deployment_intent_planned_obelisk_build_identity_mismatch", report["blockers"])
        self.assertIn("deployment_intent_mismatch", report["blockers"])

    def test_rejects_operator_live_ops_brief_artifact_binding_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["operator_live_ops_brief"]["artifact_binding"]["required_sidecars"][
                "preflight_post_json"
            ] = "/servidor/ark/workspace-offline/live-validation-logs/other/preflight-post.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operator_live_ops_brief_artifact_binding_mismatch", report["blockers"])
        self.assertIn("operator_live_ops_brief_mismatch", report["blockers"])

    def test_rejects_operator_live_ops_brief_template_receipt_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["operator_live_ops_brief"]["evidence_capture"][
                "operator_approval_receipt_required"
            ] = "generated_template"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operator_live_ops_brief_receipt_required_not_completed_receipt", report["blockers"])
        self.assertIn("operator_live_ops_brief_mismatch", report["blockers"])

    def test_rejects_operator_live_ops_brief_runtime_authorization_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["operator_live_ops_brief"]["non_authorization"] = "brief says runtime work authorized"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operator_live_ops_brief_non_authorization_mismatch", report["blockers"])
        self.assertIn("forbidden_public_capability_or_readiness_claim", report["blockers"])

    def test_rejects_request_pack_approved_runtime_evidence_text_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["operator_live_ops_brief"]["non_authorization"] = (
                "request pack counts as approved runtime evidence"
            )
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operator_live_ops_brief_non_authorization_mismatch", report["blockers"])
        self.assertIn("forbidden_public_capability_or_readiness_claim", report["blockers"])

    def test_rejects_request_pack_missing_prepared_at_utc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request.pop("prepared_at_utc")
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_missing_required", report["blockers"])
        self.assertIn("prepared_at_utc_not_string", report["blockers"])

    def test_rejects_request_pack_prepared_too_far_before_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            start = datetime.fromisoformat(
                request["approved_window"]["start_utc"].replace("Z", "+00:00")
            ).astimezone(timezone.utc)
            request["prepared_at_utc"] = (start - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
            request_path.write_text(json.dumps(request), encoding="utf-8")
            (output_dir / "operator-approval-request.md").write_text(
                REQUEST_CHECKER.markdown_request(
                    request,
                    (output_dir / "observer-window.env").read_text(encoding="utf-8").splitlines(),
                ),
                encoding="utf-8",
            )
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("prepared_at_utc_too_far_before_approved_window", report["blockers"])
        self.assertFalse(report["runtime_work_authorized"])

    def test_rejects_request_pack_prepared_in_future(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            start = datetime.fromisoformat(
                request["approved_window"]["start_utc"].replace("Z", "+00:00")
            ).astimezone(timezone.utc)
            request["prepared_at_utc"] = (start - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
            request_path.write_text(json.dumps(request), encoding="utf-8")
            (output_dir / "operator-approval-request.md").write_text(
                REQUEST_CHECKER.markdown_request(
                    request,
                    (output_dir / "observer-window.env").read_text(encoding="utf-8").splitlines(),
                ),
                encoding="utf-8",
            )
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("prepared_at_utc_in_future", report["blockers"])

    def test_rejects_receipt_approved_before_request_prepared(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            receipt_path = write_completed_receipt(output_dir, approved_at_utc="2026-06-01T00:00:00Z")
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn("operator_approval_receipt_approved_before_request_prepared", report["blockers"])

    def test_rejects_receipt_approved_at_request_prepared(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))
            receipt_path = write_completed_receipt(
                output_dir,
                approved_at_utc=request["prepared_at_utc"],
            )
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn("operator_approval_receipt_approved_before_request_prepared", report["blockers"])

    def test_rejects_receipt_approved_at_or_after_window_start(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))
            receipt_path = write_completed_receipt(
                output_dir,
                approved_at_utc=request["approved_window"]["start_utc"],
            )
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn("operator_approval_receipt_approved_at_or_after_window_start", report["blockers"])

    def test_rejects_receipt_approved_too_far_before_window_start(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))
            start = datetime.fromisoformat(
                request["approved_window"]["start_utc"].replace("Z", "+00:00")
            ).astimezone(timezone.utc)
            receipt_path = write_completed_receipt(
                output_dir,
                approved_at_utc=(start - timedelta(minutes=11)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn("operator_approval_receipt_approved_too_far_before_window_start", report["blockers"])

    def test_rejects_receipt_approved_in_future(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))
            start = datetime.fromisoformat(
                request["approved_window"]["start_utc"].replace("Z", "+00:00")
            ).astimezone(timezone.utc)
            receipt_path = write_completed_receipt(
                output_dir,
                approved_at_utc=(start - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn("operator_approval_receipt_approved_in_future", report["blockers"])

    def test_rejects_operator_request_markdown_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            markdown_path = output_dir / "operator-approval-request.md"
            markdown_path.write_text(
                markdown_path.read_text(encoding="utf-8").replace("dispatch limit=0", "dispatch limit=1"),
                encoding="utf-8",
            )
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_request_verified"])
        self.assertIn("operator_request_markdown_mismatch", report["blockers"])

    def test_rejects_missing_post_window_replay_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request.pop("post_window_replay_contract")
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_missing_required", report["blockers"])

    def test_rejects_post_window_replay_contract_path_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["post_window_replay_contract"]["sidecars"]["observer_env_path"] = "/tmp/observer-window.env"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            (output_dir / "operator-approval-request.md").write_text(
                REQUEST_CHECKER.markdown_request(
                    request,
                    (output_dir / "observer-window.env").read_text(encoding="utf-8").splitlines(),
                ),
                encoding="utf-8",
            )
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("post_window_replay_contract_mismatch", report["blockers"])
        self.assertIn("post_window_replay_contract_observer_env_path_not_approved_offline_workspace", report["blockers"])
        self.assertIn("post_window_replay_contract_observer_env_path_not_exact_expected_path", report["blockers"])

    def test_rejects_post_window_replay_contract_receipt_path_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["post_window_replay_contract"]["sidecars"][
                "operator_approval_receipt_path"
            ] = "/tmp/operator-approval-receipt.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            (output_dir / "operator-approval-request.md").write_text(
                REQUEST_CHECKER.markdown_request(
                    request,
                    (output_dir / "observer-window.env").read_text(encoding="utf-8").splitlines(),
                ),
                encoding="utf-8",
            )
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("post_window_replay_contract_mismatch", report["blockers"])
        self.assertIn(
            "post_window_replay_contract_operator_approval_receipt_path_not_approved_offline_workspace",
            report["blockers"],
        )
        self.assertIn(
            "post_window_replay_contract_operator_approval_receipt_path_not_exact_expected_path",
            report["blockers"],
        )

    def test_rejects_post_window_replay_contract_sidecar_in_wrong_run_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["post_window_replay_contract"]["sidecars"]["preflight_post_path"] = (
                "/servidor/ark/workspace-offline/live-validation-logs/"
                f"{request['run_id']}-other/preflight-post.json"
            )
            request_path.write_text(json.dumps(request), encoding="utf-8")
            (output_dir / "operator-approval-request.md").write_text(
                REQUEST_CHECKER.markdown_request(
                    request,
                    (output_dir / "observer-window.env").read_text(encoding="utf-8").splitlines(),
                ),
                encoding="utf-8",
            )
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("post_window_replay_contract_mismatch", report["blockers"])
        self.assertIn(
            "post_window_replay_contract_preflight_post_path_not_exact_expected_path",
            report["blockers"],
        )

    def test_rejects_post_window_replay_contract_missing_bound_operator_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["post_window_replay_contract"]["sidecars"].pop("operator_approval_request_path")
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("post_window_replay_contract_sidecars_missing_required", report["blockers"])
        self.assertIn("post_window_replay_contract_mismatch", report["blockers"])
        self.assertIn("operator_request_markdown_projection_failed", report["blockers"])

    def test_post_window_replay_rejects_window_not_completed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            receipt_path = write_completed_receipt(output_dir)
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ready"])
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertFalse(report["current_turn_approval_recorded"])
        self.assertIn("post_window_replay_window_not_completed", report["blockers"])

    def test_post_window_replay_tolerates_expired_window_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            old_run_id = request["run_id"]
            request = json.loads(json.dumps(request).replace(old_run_id, "20260101T000000Z-player-principal-lifecycle"))
            request["approved_window"]["start_utc"] = "2026-01-01T00:00:00Z"
            request["approved_window"]["end_utc"] = "2026-01-01T00:15:00Z"
            request["prepared_at_utc"] = "2025-12-31T23:55:00Z"
            request["run_id"] = "20260101T000000Z-player-principal-lifecycle"
            request["operator_live_ops_brief"]["start_restart_stop_window"]["start_utc"] = "2026-01-01T00:00:00Z"
            request["operator_live_ops_brief"]["start_restart_stop_window"]["end_utc"] = "2026-01-01T00:15:00Z"
            request["current_turn_approval_scope"]["required_named_scope"]["restart_window"] = {
                "start_utc": "2026-01-01T00:00:00Z",
                "end_utc": "2026-01-01T00:15:00Z",
                "expectation": request["restart_expectation"],
            }
            request_path.write_text(json.dumps(request), encoding="utf-8")
            (output_dir / "observer-window.env").write_text(
                "\n".join(REQUEST_CHECKER.env_lines(REQUEST_CHECKER.args_for_env(request))) + "\n",
                encoding="utf-8",
            )
            (output_dir / "operator-approval-request.md").write_text(
                REQUEST_CHECKER.markdown_request(
                    request,
                    (output_dir / "observer-window.env").read_text(encoding="utf-8").splitlines(),
                ),
                encoding="utf-8",
            )
            write_post_window_replay_sidecars(output_dir)
            receipt_path = write_completed_receipt(output_dir, approved_at_utc="2025-12-31T23:56:00Z")
            result = self.run_checker(
                output_dir,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)
            receipt_sha256 = hashlib.sha256(receipt_path.read_bytes()).hexdigest()

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["ready"])
        self.assertTrue(report["post_window_replay"])
        self.assertTrue(report["post_window_replay_expiry_tolerated"])
        self.assertTrue(report["operator_approval_receipt_verified"])
        self.assertEqual(
            report["request_pack_artifacts"]["operator_approval_receipt_json"]["sha256"],
            receipt_sha256,
        )
        self.assertEqual(
            report["operator_approval_receipt_completion"]["approval_recorded_at_utc"],
            "2025-12-31T23:56:00Z",
        )
        self.assertEqual(
            report["operator_approval_receipt_completion"]["approval_source"],
            "current_turn_operator_message",
        )
        self.assertTrue(report["current_turn_approval_recorded"])
        self.assertFalse(report["request_pack_records_current_turn_approval"])
        self.assertEqual([], report["blockers"])

    def test_post_window_replay_accepts_standing_launch_authority_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_standing_launch_authority_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            old_run_id = request["run_id"]
            request = json.loads(json.dumps(request).replace(old_run_id, "20260101T000000Z-player-principal-lifecycle"))
            request["approved_window"]["start_utc"] = "2026-01-01T00:00:00Z"
            request["approved_window"]["end_utc"] = "2026-01-01T00:15:00Z"
            request["prepared_at_utc"] = "2025-12-31T23:55:00Z"
            request["run_id"] = "20260101T000000Z-player-principal-lifecycle"
            request["passive_wait_boundary"]["requested_wait_window_seconds"] = 900
            request["operator_live_ops_brief"]["start_restart_stop_window"]["start_utc"] = "2026-01-01T00:00:00Z"
            request["operator_live_ops_brief"]["start_restart_stop_window"]["end_utc"] = "2026-01-01T00:15:00Z"
            request["operator_live_ops_brief"]["passive_wait_boundary"]["requested_wait_window_seconds"] = 900
            request["current_turn_approval_scope"]["required_named_scope"]["restart_window"] = {
                "start_utc": "2026-01-01T00:00:00Z",
                "end_utc": "2026-01-01T00:15:00Z",
                "expectation": request["restart_expectation"],
            }
            request["current_turn_approval_scope"]["required_named_scope"]["passive_wait_boundary"][
                "requested_wait_window_seconds"
            ] = 900
            request_path.write_text(json.dumps(request), encoding="utf-8")
            (output_dir / "observer-window.env").write_text(
                "\n".join(REQUEST_CHECKER.env_lines(REQUEST_CHECKER.args_for_env(request))) + "\n",
                encoding="utf-8",
            )
            (output_dir / "operator-approval-request.md").write_text(
                REQUEST_CHECKER.markdown_request(
                    request,
                    (output_dir / "observer-window.env").read_text(encoding="utf-8").splitlines(),
                ),
                encoding="utf-8",
            )
            write_post_window_replay_sidecars(output_dir)
            receipt_path = write_completed_receipt(output_dir, approved_at_utc="2025-12-31T23:56:00Z")
            result = self.run_checker(
                output_dir,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["operator_approval_receipt_verified"])
        self.assertEqual(
            report["operator_approval_receipt_completion"]["approval_source"],
            APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY,
        )
        self.assertEqual(
            report["operator_approval_receipt_completion"]["attestation"],
            APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY,
        )
        self.assertFalse(report["current_turn_operator_approval_required"])
        self.assertFalse(report["current_turn_approval_recorded"])
        self.assertTrue(report["standing_launch_authority_recorded"])
        self.assertTrue(report["standing_launch_authority_satisfies_operator_approval"])
        self.assertEqual(report["next_blocker"], "runtime_window_preflight_required")
        self.assertNotIn("operator_approval_receipt_approval_source_mismatch", report["blockers"])
        self.assertNotIn("operator_approval_receipt_scope_standing_approval_not_false", report["blockers"])
        self.assertEqual([], report["blockers"])

    def test_post_window_replay_rejects_standing_receipt_that_claims_current_turn_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_standing_launch_authority_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            old_run_id = request["run_id"]
            request = json.loads(json.dumps(request).replace(old_run_id, "20260101T000000Z-player-principal-lifecycle"))
            request["approved_window"]["start_utc"] = "2026-01-01T00:00:00Z"
            request["approved_window"]["end_utc"] = "2026-01-01T00:15:00Z"
            request["prepared_at_utc"] = "2025-12-31T23:55:00Z"
            request["run_id"] = "20260101T000000Z-player-principal-lifecycle"
            request["passive_wait_boundary"]["requested_wait_window_seconds"] = 900
            request["operator_live_ops_brief"]["start_restart_stop_window"]["start_utc"] = "2026-01-01T00:00:00Z"
            request["operator_live_ops_brief"]["start_restart_stop_window"]["end_utc"] = "2026-01-01T00:15:00Z"
            request["operator_live_ops_brief"]["passive_wait_boundary"]["requested_wait_window_seconds"] = 900
            request["current_turn_approval_scope"]["required_named_scope"]["restart_window"] = {
                "start_utc": "2026-01-01T00:00:00Z",
                "end_utc": "2026-01-01T00:15:00Z",
                "expectation": request["restart_expectation"],
            }
            request["current_turn_approval_scope"]["required_named_scope"]["passive_wait_boundary"][
                "requested_wait_window_seconds"
            ] = 900
            request_path.write_text(json.dumps(request), encoding="utf-8")
            (output_dir / "observer-window.env").write_text(
                "\n".join(REQUEST_CHECKER.env_lines(REQUEST_CHECKER.args_for_env(request))) + "\n",
                encoding="utf-8",
            )
            (output_dir / "operator-approval-request.md").write_text(
                REQUEST_CHECKER.markdown_request(
                    request,
                    (output_dir / "observer-window.env").read_text(encoding="utf-8").splitlines(),
                ),
                encoding="utf-8",
            )
            write_post_window_replay_sidecars(output_dir)
            receipt_path = write_completed_receipt(output_dir, approved_at_utc="2025-12-31T23:56:00Z")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["operator_current_turn_approval_recorded"] = True
            receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertFalse(report["current_turn_approval_recorded"])
        self.assertIn(
            "operator_approval_receipt_current_turn_approval_not_false_for_standing_authority",
            report["blockers"],
        )

    def test_post_window_replay_rejects_missing_preflight_manifest_and_log_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            old_run_id = request["run_id"]
            request = json.loads(json.dumps(request).replace(old_run_id, "20260101T000000Z-player-principal-lifecycle"))
            request["approved_window"]["start_utc"] = "2026-01-01T00:00:00Z"
            request["approved_window"]["end_utc"] = "2026-01-01T00:15:00Z"
            request["prepared_at_utc"] = "2025-12-31T23:55:00Z"
            request["run_id"] = "20260101T000000Z-player-principal-lifecycle"
            request["passive_wait_boundary"]["requested_wait_window_seconds"] = 900
            request["operator_live_ops_brief"]["start_restart_stop_window"]["start_utc"] = "2026-01-01T00:00:00Z"
            request["operator_live_ops_brief"]["start_restart_stop_window"]["end_utc"] = "2026-01-01T00:15:00Z"
            request["operator_live_ops_brief"]["passive_wait_boundary"]["requested_wait_window_seconds"] = 900
            request["current_turn_approval_scope"]["required_named_scope"]["restart_window"] = {
                "start_utc": "2026-01-01T00:00:00Z",
                "end_utc": "2026-01-01T00:15:00Z",
                "expectation": request["restart_expectation"],
            }
            request["current_turn_approval_scope"]["required_named_scope"]["passive_wait_boundary"][
                "requested_wait_window_seconds"
            ] = 900
            request_path.write_text(json.dumps(request), encoding="utf-8")
            (output_dir / "observer-window.env").write_text(
                "\n".join(REQUEST_CHECKER.env_lines(REQUEST_CHECKER.args_for_env(request))) + "\n",
                encoding="utf-8",
            )
            (output_dir / "operator-approval-request.md").write_text(
                REQUEST_CHECKER.markdown_request(
                    request,
                    (output_dir / "observer-window.env").read_text(encoding="utf-8").splitlines(),
                ),
                encoding="utf-8",
            )
            receipt_path = write_completed_receipt(output_dir, approved_at_utc="2025-12-31T23:56:00Z")
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ready"])
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertFalse(report["current_turn_approval_recorded"])
        self.assertFalse(report["post_window_replay_expiry_tolerated"])
        self.assertIn("approved_window_expired", report["blockers"])
        self.assertIn("post_window_replay_preflight_pre_sidecar_missing", report["blockers"])
        self.assertIn("post_window_replay_preflight_post_sidecar_missing", report["blockers"])
        self.assertIn("post_window_replay_window_manifest_sidecar_missing", report["blockers"])
        self.assertIn("post_window_replay_copied_obelisk_log_sidecar_missing", report["blockers"])

    def test_post_window_replay_rejects_expired_window_plus_markdown_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            old_run_id = request["run_id"]
            request = json.loads(json.dumps(request).replace(old_run_id, "20260101T000000Z-player-principal-lifecycle"))
            request["approved_window"]["start_utc"] = "2026-01-01T00:00:00Z"
            request["approved_window"]["end_utc"] = "2026-01-01T00:15:00Z"
            request["prepared_at_utc"] = "2025-12-31T23:55:00Z"
            request["run_id"] = "20260101T000000Z-player-principal-lifecycle"
            request["passive_wait_boundary"]["requested_wait_window_seconds"] = 900
            request["operator_live_ops_brief"]["start_restart_stop_window"]["start_utc"] = "2026-01-01T00:00:00Z"
            request["operator_live_ops_brief"]["start_restart_stop_window"]["end_utc"] = "2026-01-01T00:15:00Z"
            request["operator_live_ops_brief"]["passive_wait_boundary"]["requested_wait_window_seconds"] = 900
            request["current_turn_approval_scope"]["required_named_scope"]["passive_wait_boundary"][
                "requested_wait_window_seconds"
            ] = 900
            request_path.write_text(json.dumps(request), encoding="utf-8")
            (output_dir / "observer-window.env").write_text(
                "\n".join(REQUEST_CHECKER.env_lines(REQUEST_CHECKER.args_for_env(request))) + "\n",
                encoding="utf-8",
            )
            markdown_path = output_dir / "operator-approval-request.md"
            markdown_path.write_text(
                REQUEST_CHECKER.markdown_request(
                    request,
                    (output_dir / "observer-window.env").read_text(encoding="utf-8").splitlines(),
                ).replace("dispatch limit=0", "dispatch limit=1"),
                encoding="utf-8",
            )
            receipt_path = write_completed_receipt(output_dir, approved_at_utc="2025-12-31T23:56:00Z")
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ready"])
        self.assertFalse(report["post_window_replay_expiry_tolerated"])
        self.assertIn("approved_window_expired", report["blockers"])
        self.assertIn("operator_request_markdown_mismatch", report["blockers"])

    def test_post_window_replay_requires_completed_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            result = self.run_checker(output_dir, check=False, extra_args=["--post-window-replay"])
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn("operator_approval_receipt_required_for_post_window_replay", report["blockers"])

    def test_post_window_replay_rejects_generated_receipt_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            receipt_path = output_dir / "operator-approval-receipt.json"
            receipt_path.write_text(
                (output_dir / "operator-approval-receipt.template.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn("operator_approval_receipt_generated_template_not_completed_receipt", report["blockers"])
        self.assertIn("operator_approval_receipt_status_not_completed", report["blockers"])

    def test_rejects_operator_approval_receipt_runtime_readiness_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            receipt_path = write_completed_receipt(output_dir)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["operator_completion"]["approved_by_role"] = "operator runtime ready"
            receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn(
            "operator_approval_receipt_forbidden_public_capability_or_readiness_claim",
            report["blockers"],
        )

    def test_rejects_operator_approval_receipt_server_restart_authorization_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            receipt_path = write_completed_receipt(output_dir)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["operator_completion"]["approved_by_role"] = "operator server restart authorized"
            receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn(
            "operator_approval_receipt_forbidden_public_capability_or_readiness_claim",
            report["blockers"],
        )

    def test_rejects_operator_approval_receipt_current_turn_approval_alias_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            receipt_path = write_completed_receipt(output_dir)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["operator_completion"]["approved_by_role"] = (
                "operator approval receipt records current-turn approval"
            )
            receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn(
            "operator_approval_receipt_forbidden_public_capability_or_readiness_claim",
            report["blockers"],
        )

    def test_rejects_operator_approval_receipt_complete_sdk_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            receipt_path = write_completed_receipt(output_dir)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["operator_completion"]["approved_by_role"] = "operator complete SDK claim"
            receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn(
            "operator_approval_receipt_forbidden_public_capability_or_readiness_claim",
            report["blockers"],
        )

    def test_rejects_operator_approval_receipt_approved_runtime_evidence_text_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            receipt_path = write_completed_receipt(output_dir)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["operator_completion"]["approved_by_role"] = (
                "completed receipt counts as approved runtime evidence"
            )
            receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn(
            "operator_approval_receipt_forbidden_public_capability_or_readiness_claim",
            report["blockers"],
        )

    def test_nested_receipt_shape_blocker_clears_receipt_verified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            receipt_path = write_completed_receipt(output_dir)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["approval_scope"]["unexpected_runtime_authorization_note"] = False
            receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn("operator_approval_receipt_scope_unexpected_keys", report["blockers"])

    def test_rejects_completed_receipt_without_post_window_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            receipt_path = write_completed_receipt(output_dir)
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ready"])
        self.assertFalse(report["post_window_replay"])
        self.assertFalse(report["post_window_replay_expiry_tolerated"])
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn("operator_approval_receipt_requires_post_window_replay", report["blockers"])

    def test_rejects_receipt_replay_across_request_pack_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            other_dir = Path(tmp) / "other-request"
            other_dir.mkdir()
            prepare_pack(output_dir)
            receipt_path = write_completed_receipt(output_dir)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["bound_request_pack"]["run_id"] = "20260101T000000Z-player-principal-lifecycle"
            receipt["bound_request_pack"]["final_posture"] = "stopped"
            receipt["bound_artifacts"]["observer_window_env"]["sha256"] = "0" * 64
            receipt["bound_artifacts"]["operator_approval_request_md"]["sha256"] = "0" * 64
            receipt["request_pack_digest"]["sha256"] = "0" * 64
            replayed_receipt_path = other_dir / "operator-approval-receipt.json"
            replayed_receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--operator-approval-receipt", str(replayed_receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        for reason in (
            "operator_approval_receipt_not_sibling_of_request_json",
            "operator_approval_receipt_run_id_mismatch",
            "operator_approval_receipt_final_posture_mismatch",
            "operator_approval_receipt_observer_window_env_artifact_mismatch",
            "operator_approval_receipt_operator_approval_request_md_artifact_mismatch",
            "operator_approval_receipt_digest_mismatch",
        ):
            self.assertIn(reason, report["blockers"])

    def test_rejects_completed_receipt_planned_build_identity_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            receipt_path = write_completed_receipt(output_dir)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["bound_request_pack"]["planned_obelisk_build_identity"]["obelisk_commit"] = "2" * 40
            receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--post-window-replay", "--operator-approval-receipt", str(receipt_path)],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_approval_receipt_verified"])
        self.assertIn("operator_approval_receipt_planned_obelisk_build_identity_mismatch", report["blockers"])

    def test_rejects_missing_operator_request_markdown_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            (output_dir / "operator-approval-request.md").unlink()
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_request_verified"])
        self.assertIn("operator_request_unreadable", report["blockers"])

    def test_rejects_env_file_from_different_request_pack_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            other_output_dir = Path(tmp) / "other-request"
            prepare_pack(output_dir)
            prepare_pack(other_output_dir)
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--env-file", str(other_output_dir / "observer-window.env")],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("env_file_not_sibling_of_request_json", report["blockers"])

    def test_rejects_operator_request_from_different_request_pack_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            other_output_dir = Path(tmp) / "other-request"
            prepare_pack(output_dir)
            other_output_dir.mkdir()
            (other_output_dir / "operator-approval-request.md").write_text(
                (output_dir / "operator-approval-request.md").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            result = self.run_checker(
                output_dir,
                check=False,
                extra_args=["--operator-request", str(other_output_dir / "operator-approval-request.md")],
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["operator_request_verified"])
        self.assertIn("operator_request_not_sibling_of_request_json", report["blockers"])

    def test_rejects_already_started_approved_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            start = (datetime.now(timezone.utc) - timedelta(seconds=60)).replace(microsecond=0)
            end = (datetime.now(timezone.utc) + timedelta(minutes=5)).replace(microsecond=0)
            request["run_id"] = start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle"
            request["approved_window"]["start_utc"] = start.strftime("%Y-%m-%dT%H:%M:%SZ")
            request["approved_window"]["end_utc"] = end.strftime("%Y-%m-%dT%H:%M:%SZ")
            request_path.write_text(json.dumps(request), encoding="utf-8")
            markdown_path = output_dir / "operator-approval-request.md"
            markdown_path.write_text(
                REQUEST_CHECKER.markdown_request(
                    request,
                    (output_dir / "observer-window.env").read_text(encoding="utf-8").splitlines(),
                ),
                encoding="utf-8",
            )
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approved_window_already_started", report["blockers"])
        self.assertNotIn("approved_window_expired", report["blockers"])
        details = {
            item["reason"]: item
            for item in report["blocker_details"]
            if item["reason"] == "approved_window_already_started"
        }
        self.assertEqual("already_started", details["approved_window_already_started"]["stale_condition"])

    def test_rejects_post_run_verification_command_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["operator_live_ops_brief"]["post_run_stable_posture"]["verification_commands"][0][2] = "arkserver3"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operator_live_ops_brief_mismatch", report["blockers"])

    def test_rejects_restart_final_posture_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["restart_expectation"] = "stop-after-window"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("restart_expectation_final_posture_mismatch", report["blockers"])

    def test_rejects_nested_live_validation_alias_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["copied_log_path"] = (
                "/servidor/ark/workspace-offline/tmp/live-validation-logs/"
                f"{request['run_id']}/Obelisk.log"
            )
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("copied_log_path_not_exact_expected_path", report["blockers"])

    def test_rejects_run_id_window_start_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            start = datetime.strptime(
                request["approved_window"]["start_utc"],
                "%Y-%m-%dT%H:%M:%SZ",
            ).replace(tzinfo=timezone.utc)
            request["approved_window"]["start_utc"] = (start + timedelta(minutes=1)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("run_id_window_start_mismatch", report["blockers"])

    def test_rejects_expired_approved_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["approved_window"]["start_utc"] = "2026-01-01T12:00:00Z"
            request["approved_window"]["end_utc"] = "2026-01-01T12:10:00Z"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approved_window_expired", report["blockers"])
        details = {
            item["reason"]: item
            for item in report["blocker_details"]
            if item["reason"] == "approved_window_expired"
        }
        self.assertEqual("expired", details["approved_window_expired"]["stale_condition"])

    def test_rejects_approved_window_duration_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            start = datetime.strptime(
                request["approved_window"]["start_utc"],
                "%Y-%m-%dT%H:%M:%SZ",
            ).replace(tzinfo=timezone.utc)
            request["approved_window"]["end_utc"] = (start + timedelta(minutes=121)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approved_window_duration_too_long", report["blockers"])
        self.assertEqual(report["next_blocker"], "request_pack_not_accepted")

    def test_rejects_beta_policy_without_notice_and_public_readiness_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["user_policy"] = "operator_approved_beta_users"
            request["notice_path"] = "not_applicable"
            request["approval_required"] = "does not authorize server operations; public SDK ready"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("beta_user_policy_requires_approved_beta_testers_notice_path", report["blockers"])
        self.assertIn("player_notice_action_required_mismatch", report["blockers"])
        self.assertIn("player_notice_action_beta_notice_path_not_approved_beta_testers", report["blockers"])
        self.assertIn("approval_required_mismatch", report["blockers"])
        self.assertIn("forbidden_public_capability_or_readiness_claim", report["blockers"])

    def test_accepts_beta_policy_with_real_notice_action_pending_activation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            args = prepare_args(output_dir)
            args[args.index("--user-policy") + 1] = "operator_approved_beta_users"
            args.insert(args.index("--rollback-owner"), "--notice-path")
            args.insert(args.index("--rollback-owner"), "discord-beta-testers")
            subprocess.run(
                args,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=_FAKE_GIT_ENV,
            )
            result = self.run_checker(output_dir)
            report = json.loads(result.stdout)
            request = json.loads((output_dir / "window-request.json").read_text(encoding="utf-8"))

        notice_action = request["player_notice_action"]
        self.assertTrue(report["ready"])
        self.assertTrue(notice_action["required"])
        self.assertEqual(notice_action["notice_path"], "discord-beta-testers")
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

    def test_rejects_beta_notice_action_that_allows_activation_before_send(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            args = prepare_args(output_dir)
            args[args.index("--user-policy") + 1] = "operator_approved_beta_users"
            args.insert(args.index("--rollback-owner"), "--notice-path")
            args.insert(args.index("--rollback-owner"), "discord-beta-testers")
            subprocess.run(
                args,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=_FAKE_GIT_ENV,
            )
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["player_notice_action"]["real_notice_send_required_before_activation"] = False
            request["player_notice_action"]["activation_allowed_before_notice_sent"] = True
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "player_notice_action_real_notice_send_required_before_activation_mismatch",
            report["blockers"],
        )
        self.assertIn("player_notice_action_activation_allowed_before_notice_sent_mismatch", report["blockers"])
        self.assertIn("player_notice_action_mismatch", report["blockers"])

    def test_accepts_negated_private_or_ue_boundary_text(self) -> None:
        blockers: list[dict[str, object]] = []
        REQUEST_CHECKER.validate_secret_free(
            {
                "privacy_boundary": [
                    "must not expose raw_params",
                    "do not log player_id",
                    "does not capture player_id",
                    "does not collect player_id",
                    "does not record raw_params",
                    "never report ue_pointer values",
                    "forbidden: raw_params",
                    "without fname_index output",
                ]
            },
            blockers,
        )

        self.assertEqual([], blockers)

    def test_rejects_unnegated_private_or_ue_boundary_text(self) -> None:
        blockers: list[dict[str, object]] = []
        REQUEST_CHECKER.validate_secret_free(
            {
                "privacy_boundary": [
                    "logs raw_params",
                    "captures player_id",
                ]
            },
            blockers,
        )

        self.assertEqual(["forbidden_private_or_ue_value", "forbidden_private_or_ue_value"], [
            item["reason"] for item in blockers
        ])

    def test_rejects_mixed_negated_and_unnegated_private_or_ue_text(self) -> None:
        blockers: list[dict[str, object]] = []
        REQUEST_CHECKER.validate_secret_free(
            {"privacy_boundary": "must not expose raw_params; captures player_id"},
            blockers,
        )

        self.assertEqual(["forbidden_private_or_ue_value"], [item["reason"] for item in blockers])

    def test_rejects_mixed_negation_with_but_then_private_or_ue_text(self) -> None:
        for text in (
            "must not expose raw_params but captures player_id",
            "does not record raw_params then captures player_id",
        ):
            with self.subTest(text=text):
                blockers: list[dict[str, object]] = []
                REQUEST_CHECKER.validate_secret_free({"privacy_boundary": text}, blockers)

                self.assertEqual(["forbidden_private_or_ue_value"], [item["reason"] for item in blockers])

    def test_rejects_mixed_negation_with_but_runtime_readiness_claim(self) -> None:
        self.assertTrue(
            REQUEST_CHECKER.contains_unnegated_positive_capability_claim(
                "does not authorize runtime readiness but runtime ready"
            )
        )

    def test_rejects_split_operational_authorization_claim_aliases(self) -> None:
        for text in (
            "runtime work is authorized",
            "server operations are authorized",
            "server restart is approved",
            "marker changes are enabled",
            "publication is approved",
            "live log permission is allowed",
            "read live logs is authorized",
        ):
            with self.subTest(text=text):
                self.assertTrue(REQUEST_CHECKER.contains_unnegated_positive_capability_claim(text))

    def test_rejects_split_readiness_claim_aliases(self) -> None:
        for text in (
            "runtime is ready",
            "complete v1 SDK claim is supported",
            "production SDK is ready",
            "v1 completion is ready",
            "route is ready",
            "public ABI is ready",
            "stable release contract claim is allowed",
            "lookup is allowed",
        ):
            with self.subTest(text=text):
                self.assertTrue(REQUEST_CHECKER.contains_unnegated_positive_capability_claim(text))

    def test_rejects_runtime_evidence_claim_source_aliases(self) -> None:
        for text in (
            "window request counts as approved runtime evidence",
            "operator approval request proves approved runtime evidence",
            "observer window env is approved runtime evidence",
            "source marker counts as approved runtime evidence",
            "evidence closure request counts as approved runtime evidence",
            "closure request provides SDK progress",
        ):
            with self.subTest(text=text):
                self.assertTrue(REQUEST_CHECKER.contains_unnegated_positive_capability_claim(text))

    def test_rejects_current_turn_approval_claim_source_aliases(self) -> None:
        for text in (
            "request pack is current-turn approval",
            "operator approval request approves current turn authorization",
            "observer window env provides operator approval",
            "generated template records current-turn approval",
            "sidecar constitutes runtime window approval",
            "closure request records current-turn approval",
        ):
            with self.subTest(text=text):
                self.assertTrue(REQUEST_CHECKER.contains_unnegated_positive_capability_claim(text))

    def test_rejects_nested_operator_live_ops_brief_split_authorization_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["operator_live_ops_brief"]["evidence_capture"]["single_module_summary"] = (
                "runtime work is authorized"
            )
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operator_live_ops_brief_mismatch", report["blockers"])
        self.assertIn("forbidden_public_capability_or_readiness_claim", report["blockers"])

    def test_rejects_nested_request_pack_current_turn_approval_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["operator_live_ops_brief"]["evidence_capture"]["single_module_summary"] = (
                "request pack is current-turn approval"
            )
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operator_live_ops_brief_mismatch", report["blockers"])
        self.assertIn("forbidden_public_capability_or_readiness_claim", report["blockers"])

    def test_accepts_negated_runtime_readiness_suffix_claims(self) -> None:
        for text in ("runtime readiness remains blocked", "runtime ready remains blocked"):
            with self.subTest(text=text):
                self.assertFalse(REQUEST_CHECKER.contains_unnegated_positive_capability_claim(text))

    def test_rejects_blocked_prefix_as_private_or_ue_negation(self) -> None:
        blockers: list[dict[str, object]] = []
        REQUEST_CHECKER.validate_secret_free(
            {"privacy_boundary": "blocked player_id raw_params"},
            blockers,
        )

        self.assertEqual(["forbidden_private_or_ue_value"], [item["reason"] for item in blockers])

    def test_rejects_blocked_prefix_as_runtime_readiness_negation_in_request_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["user_policy"] = "operator_approved_beta_users"
            request["notice_path"] = "blocked runtime readiness enabled"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden_public_capability_or_readiness_claim", report["blockers"])

    def test_rejects_live_server_request_path(self) -> None:
        live_result = subprocess.run(
            [
                sys.executable,
                str(CHECK),
                "/servidor/ark/obelisk/window-request.json",
                "--env-file",
                "/servidor/ark/obelisk/observer-window.env",
                "--json",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(live_result.returncode, 0)
        self.assertIn("must not read from protected server root", live_result.stderr)

    def test_rejects_placeholder_obelisk_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["obelisk_commit"] = "reviewed-obelisk-commit"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("obelisk_commit_invalid", report["blockers"])

    def test_rejects_nonexistent_forty_hex_obelisk_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "request"
            prepare_pack(output_dir)
            request_path = output_dir / "window-request.json"
            request = json.loads(request_path.read_text(encoding="utf-8"))
            request["obelisk_commit"] = "a" * 40
            request_path.write_text(json.dumps(request), encoding="utf-8")

            result = self.run_checker(output_dir, check=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("obelisk_commit_invalid", report["blockers"])


if __name__ == "__main__":
    unittest.main()
