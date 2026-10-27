#!/usr/bin/env python3
"""Tests for plan_player_principal_lifecycle_runtime_window.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "plan_player_principal_lifecycle_runtime_window.py"
TEST_COMMIT = subprocess.check_output(
    ["git", "rev-parse", "HEAD"],
    cwd=SCRIPT_DIR.parents[0],
    text=True,
).strip()
STRICT_TRIPLET_TEXT = "HandleNewPlayer(1,1) -> CheckJoinInProgress(1,0) -> matched OnLogout"
PREVIOUS_THEISLAND_RUN_ID_STEM = "20260607T134929Z"
PREVIOUS_THEISLAND_RUN_ID = f"{PREVIOUS_THEISLAND_RUN_ID_STEM}-player-principal-lifecycle"
FRESH_RETRY_SCHEMA = (
    "obelisk.player-principal-lifecycle-fresh-retry-after-closed-non-evidence-window.v1"
)
COPIED_LOG_ROUTE_STEPS = [
    "analyze_runtime_observer_log",
    "strict_lifecycle_triplet_candidate_summary",
    "bundle_preflight",
    "approved_runtime_evidence_checker",
]
STRICT_CANDIDATE_SUMMARY_JSON_PATH = (
    "modules.player_principal_lifecycle.strict_lifecycle_triplet_candidate_summary"
)
EXPECTED_NON_CLAIM_FLAGS = {
    "authorized_by_this_plan": False,
    "non_authorizing": True,
    "non_evidence": True,
    "counts_as_approved_runtime_evidence": False,
    "counts_as_evidence": False,
    "counts_as_progress": False,
    "counts_as_p0_progress": False,
    "counts_as_runtime_readiness": False,
    "counts_as_public_readiness": False,
    "clears_approved_runtime_evidence_missing": False,
    "public_sdk_ready": False,
    "runtime_ready": False,
    "publication_ready": False,
}
CLAIM_FLAG_KEYS_MUST_STAY_FALSE = {
    "approved_runtime_evidence_missing_cleared",
    "beta_notice_satisfies_requirement",
    "clears_approved_runtime_evidence_missing",
    "counts_as_approved_runtime_evidence",
    "counts_as_evidence",
    "counts_as_p0_progress",
    "counts_as_progress",
    "counts_as_public_readiness",
    "counts_as_runtime_readiness",
    "dry_run_or_send_metadata_counts_as_evidence",
    "passive_wait_counts_as_approved_runtime_evidence",
    "passive_wait_satisfies_requirement",
    "plan_counts_as_progress",
    "plan_counts_as_public_readiness",
    "plan_counts_as_runtime_readiness",
    "plan_or_request_pack_satisfies_requirement",
    "public_query_satisfies_requirement",
    "public_sdk_ready",
    "publication_ready",
    "runtime_ready",
    "standing_launch_authority_satisfies_requirement",
    "start_end_only_counts_as_approved_runtime_evidence",
    "start_end_only_satisfies_requirement",
}


def base_args(output_root: Path) -> list[str]:
    return [
        sys.executable,
        str(SCRIPT),
        "--instance",
        "arkserver3",
        "--map",
        "Genesis2",
        "--now-utc",
        "2026-06-06T04:00:00Z",
        "--start-delay-minutes",
        "5",
        "--duration-minutes",
        "15",
        "--restart-expectation",
        "restart",
        "--output-root",
        str(output_root),
        "--obelisk-commit",
        TEST_COMMIT,
        "--json",
    ]


def load_plan(output_root: Path) -> dict[str, Any]:
    result = subprocess.run(
        base_args(output_root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return json.loads(result.stdout)


def iter_tree(value: Any) -> Any:
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from iter_tree(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_tree(child)


def iter_key_values(value: Any) -> Any:
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from iter_key_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_key_values(child)


def all_strings(value: Any) -> list[str]:
    return [node for node in iter_tree(value) if isinstance(node, str)]


def assert_non_claim_flags(testcase: unittest.TestCase, entry: dict[str, Any], label: str) -> None:
    for key, expected in EXPECTED_NON_CLAIM_FLAGS.items():
        testcase.assertIn(key, entry, label)
        testcase.assertIs(entry[key], expected, f"{label}.{key}")


def assert_strict_triplet(testcase: unittest.TestCase, requirement: dict[str, Any], label: str) -> None:
    testcase.assertEqual(requirement["requirement"], STRICT_TRIPLET_TEXT, label)
    testcase.assertEqual(requirement["source"], "future_player_backed_copied_obelisk_log_only", label)
    testcase.assertEqual(
        requirement["required_sequence"],
        [
            {"event": "HandleNewPlayer", "copied_bool_values": [1, 1]},
            {"event": "CheckJoinInProgress", "copied_bool_values": [1, 0]},
            {"event": "OnLogout", "correlation_status": "matched"},
        ],
        label,
    )
    testcase.assertTrue(requirement["requires_same_player_correlation"], label)
    testcase.assertTrue(requirement["requires_copied_log_bundle_checker_acceptance"], label)
    testcase.assertTrue(requirement["future_player_backed_required"], label)
    for key in (
        "standing_launch_authority_satisfies_requirement",
        "plan_or_request_pack_satisfies_requirement",
        "beta_notice_satisfies_requirement",
        "passive_wait_satisfies_requirement",
        "public_query_satisfies_requirement",
        "start_end_only_satisfies_requirement",
        "clears_approved_runtime_evidence_missing",
        "counts_as_approved_runtime_evidence",
        "counts_as_progress",
        "counts_as_runtime_readiness",
    ):
        testcase.assertIs(requirement[key], False, f"{label}.{key}")


def assert_role_objectives(testcase: unittest.TestCase, objectives: dict[str, Any], label: str) -> None:
    testcase.assertEqual(
        objectives["objective_ids"],
        ["session_start", "CheckJoinInProgress(1,0)", "session_end"],
        label,
    )
    testcase.assertEqual(objectives["required_lifecycle_event_roles"], [
        "session_start",
        "session_start_rejected",
        "session_end",
    ])
    testcase.assertFalse(objectives["standing_authority_satisfies_missing_roles"])
    testcase.assertFalse(objectives["counts_as_approved_runtime_evidence"])
    testcase.assertFalse(objectives["counts_toward_sdk"])


def assert_copied_log_route(testcase: unittest.TestCase, route: dict[str, Any], label: str) -> None:
    testcase.assertEqual(route["ordered_step_ids"], COPIED_LOG_ROUTE_STEPS, label)
    testcase.assertIn("analyzer -> strict_lifecycle_triplet_candidate_summary", route["route"])
    testcase.assertEqual(
        route["strict_lifecycle_triplet_candidate_summary_json_path"],
        STRICT_CANDIDATE_SUMMARY_JSON_PATH,
        label,
    )
    testcase.assertTrue(route["checker_acceptance_required_before_evidence_state_change"], label)
    testcase.assertTrue(route["all_prior_outputs_non_authorizing_and_non_evidence"], label)
    testcase.assertFalse(route["approved_evidence_checker_accepted_by_this_plan"], label)
    testcase.assertFalse(route["restart_recommended"], label)
    testcase.assertFalse(route["raw_player_text_or_identity_allowed"], label)
    testcase.assertFalse(route["server_operations_authorized"], label)
    testcase.assertFalse(route["runtime_capture_authorized"], label)
    testcase.assertFalse(route["live_log_reads_authorized"], label)
    testcase.assertFalse(route["counts_as_approved_runtime_evidence"], label)
    testcase.assertFalse(route["runtime_ready"], label)
    testcase.assertFalse(route["public_sdk_ready"], label)


class PlanPlayerPrincipalLifecycleRuntimeWindowTests(unittest.TestCase):
    def test_emits_standing_authorized_beta_window_command_sequence_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "live-validation-logs"
            result = subprocess.run(
                base_args(output_root),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

            plan = json.loads(result.stdout)

        self.assertEqual(plan["schema"], "obelisk.player-principal-lifecycle-runtime-window-plan.v1")
        self.assertEqual(plan["status"], "planned_offline_only")
        self.assertEqual(plan["run_id"], "20260606T040500Z-player-principal-lifecycle")
        self.assertEqual(plan["target"], {"instance": "arkserver3", "map": "Genesis2"})
        closure_root = plan["closure_compatible_evidence_root"]
        self.assertTrue(closure_root["run_id_matches_closure_request"])
        self.assertEqual(closure_root["run_id"], plan["run_id"])
        self.assertEqual(closure_root["evidence_dir"], plan["evidence_dir"])
        self.assertTrue(closure_root["passive_monitor_roots_must_not_be_used_as_closure_evidence_dir"])
        self.assertTrue(
            closure_root[
                "passive_monitor_context_must_be_copied_or_replaced_before_evidence_closure"
            ]
        )
        self.assertFalse(closure_root["counts_as_approved_runtime_evidence"])
        self.assertFalse(plan["diagnostic_candidates_enabled"])
        self.assertEqual(plan["approved_window"]["duration_seconds"], 900)
        self.assertEqual(plan["approved_window"]["minimum_pre_activation_lead_seconds"], 300)
        self.assertEqual(plan["approved_window"]["seconds_until_start_at_plan_time"], 300)
        self.assertTrue(plan["approved_window"]["enough_future_lead_time_at_plan_time"])
        stale_prevention = plan["runtime_window_stale_prevention"]
        self.assertEqual(
            stale_prevention["schema"],
            "obelisk.player-principal-lifecycle-runtime-window-stale-prevention.v1",
        )
        self.assertEqual(stale_prevention["minimum_required_lead_seconds"], 300)
        self.assertEqual(stale_prevention["blockers"], [])
        self.assertTrue(stale_prevention["enough_future_lead_time"])
        self.assertTrue(stale_prevention["window_start_in_future"])
        self.assertTrue(stale_prevention["confirmed_send_must_complete_before_window_start"])
        self.assertFalse(stale_prevention["activation_or_restart_from_stale_request_allowed"])
        self.assertFalse(stale_prevention["monitor_or_restart_activation_after_window_start_allowed"])
        self.assertFalse(stale_prevention["counts_as_approved_runtime_evidence"])
        self.assertFalse(stale_prevention["runtime_ready"])
        assert_role_objectives(self, plan["lifecycle_missing_role_objectives"], "top_level_objectives")
        self.assertEqual(plan["two_server_cap_policy"]["max_running_ark_servers"], 2)
        self.assertTrue(plan["two_server_cap_policy"]["never_keep_three_ark_servers_running"])
        self.assertFalse(plan["two_server_cap_policy"]["three_ark_servers_allowed"])
        recommended = plan["recommended_notice_text"]
        self.assertEqual(recommended["discord_bot_channel_id"], "1513238083741683934")
        self.assertEqual(recommended["discord_bot_channel_env_var"], "OBELISK_DISCORD_BETA_CHANNEL_ID")
        self.assertTrue(recommended["bot_first_notice_path"])
        self.assertFalse(recommended["webhook_notice_path_allowed"])
        self.assertTrue(recommended["single_active_bot_notice_required"])
        self.assertFalse(recommended["active_notice_state_counts_as_confirmed_notice"])
        self.assertFalse(recommended["bot_notice_counts_as_approved_runtime_evidence"])
        transport = recommended["beta_notice_transport_policy"]
        self.assertEqual(
            transport["schema"],
            "obelisk.player-principal-lifecycle-beta-notice-bot-transport.v1",
        )
        self.assertEqual(transport["bot_channel_id"], "1513238083741683934")
        self.assertEqual(transport["bot_channel_env_var"], "OBELISK_DISCORD_BETA_CHANNEL_ID")
        self.assertTrue(transport["bot_channel_required_for_real_send"])
        self.assertFalse(transport["webhook_notice_path_allowed"])
        self.assertFalse(transport["active_notice_state_counts_as_confirmed_notice"])
        self.assertFalse(transport["counts_as_approved_runtime_evidence"])
        self.assertFalse(transport["runtime_ready"])
        self.assertEqual(plan["beta_notice_transport_policy"], transport)
        self.assertTrue(recommended["recommended_text_already_redacted"])
        self.assertFalse(recommended["raw_player_text_or_identity_allowed"])
        self.assertFalse(recommended["secret_or_webhook_output_allowed"])
        self.assertIn("CheckJoinInProgress(1,0)", recommended["recommended_discord_text_redacted"])
        self.assertNotIn("discord.com\x2fapi/webhooks", recommended["recommended_discord_text_redacted"])
        self.assertTrue(plan["standing_launch_authority"]["recorded"])
        self.assertTrue(plan["standing_launch_authority"]["authorizes_scoped_runtime_window_preparation"])
        self.assertTrue(plan["standing_launch_authority"]["authorizes_window_request_preparation"])
        self.assertTrue(plan["standing_launch_authority"]["authorizes_dry_run_notice_preparation"])
        self.assertTrue(plan["standing_launch_authority"]["authorizes_guarded_beta_notice_send"])
        self.assertTrue(plan["standing_launch_authority"]["authorizes_beta_notice_send"])
        self.assertFalse(plan["standing_launch_authority"]["preparation_authority_only"])
        self.assertTrue(plan["standing_launch_authority"]["authorizes_discord_send"])
        self.assertFalse(plan["standing_launch_authority"]["authorizes_runtime_capture"])
        self.assertFalse(plan["standing_launch_authority"]["authorizes_runtime_evidence"])
        self.assertFalse(plan["standing_launch_authority"]["authorizes_marker_env_changes"])
        self.assertFalse(plan["standing_launch_authority"]["authorizes_server_restart"])
        self.assertFalse(plan["standing_launch_authority"]["authorizes_publication"])
        self.assertFalse(plan["standing_launch_authority"]["authorizes_readiness"])
        self.assertFalse(plan["standing_launch_authority"]["counts_as_approved_runtime_evidence"])
        self.assertFalse(plan["standing_launch_authority"]["counts_as_progress"])
        self.assertFalse(plan["standing_launch_authority"]["clears_approved_runtime_evidence_missing"])
        assert_strict_triplet(
            self,
            plan["standing_launch_authority"]["strict_copied_bool_triplet_requirement"],
            "standing_launch_authority",
        )
        assert_role_objectives(
            self,
            plan["standing_launch_authority"]["lifecycle_missing_role_objectives"],
            "standing_launch_authority_objectives",
        )
        assert_strict_triplet(self, plan["strict_copied_bool_triplet_requirement"], "top_level")
        self.assertIn(STRICT_TRIPLET_TEXT, plan["strict_copied_bool_triplet_requirement"]["accepted_evidence_requires"])
        workflow = plan["current_window_workflow"]
        self.assertEqual(
            workflow["schema"],
            "obelisk.player-principal-lifecycle-runtime-window-current-workflow.v1",
        )
        self.assertEqual(workflow["status"], "fresh_current_window_planned")
        self.assertTrue(workflow["fresh_window_computed_from_current_utc"])
        self.assertFalse(workflow["stale_request_window_reuse_allowed"])
        self.assertFalse(workflow["stale_beta_notice_sendable"])
        self.assertEqual(workflow["minimum_pre_activation_lead_seconds"], 300)
        self.assertEqual(workflow["seconds_until_start"], 300)
        self.assertTrue(workflow["enough_future_lead_time"])
        self.assertEqual(workflow["runtime_window_stale_prevention"], stale_prevention)
        self.assertTrue(workflow["beta_notice_dry_run_required_before_activation"])
        self.assertTrue(workflow["confirmed_beta_notice_required_before_activation"])
        self.assertEqual(workflow["beta_notice_transport_policy"], transport)
        self.assertTrue(workflow["confirmed_send_must_complete_before_window_start"])
        self.assertFalse(workflow["activation_or_restart_from_stale_request_allowed"])
        self.assertFalse(workflow["monitor_or_restart_activation_after_window_start_allowed"])
        self.assertEqual(workflow["next_exact_command_id"], "prepare_request_pack")
        self.assertTrue(workflow["closure_compatible_evidence_root"]["run_id_matches_closure_request"])
        self.assertIn("prepare_player_principal_lifecycle_window_request.py", workflow["next_exact_command_shell"])
        self.assertIn("--approved-window-start-utc 2026-06-06T04:05:00Z", workflow["next_exact_command_shell"])
        self.assertTrue(workflow["next_exact_command_writes_only_offline_request_pack"])
        self.assertFalse(workflow["next_exact_command_sends_discord"])
        self.assertFalse(workflow["next_exact_command_touches_live_ark"])
        self.assertFalse(workflow["next_exact_command_authorizes_runtime"])
        self.assertFalse(workflow["approved_runtime_evidence_missing_cleared"])
        self.assertFalse(workflow["dry_run_or_send_metadata_counts_as_evidence"])
        self.assertFalse(workflow["passive_wait_counts_as_approved_runtime_evidence"])
        self.assertFalse(workflow["start_end_only_counts_as_approved_runtime_evidence"])
        self.assertFalse(workflow["plan_counts_as_progress"])
        self.assertFalse(workflow["plan_counts_as_runtime_readiness"])
        self.assertFalse(workflow["plan_counts_as_public_readiness"])
        assert_strict_triplet(self, workflow["strict_copied_bool_triplet_requirement"], "current_window_workflow")
        assert_role_objectives(
            self,
            workflow["lifecycle_missing_role_objectives"],
            "current_window_workflow_objectives",
        )
        self.assertIn("does not authorize Discord", workflow["non_authorization"])
        self.assertTrue(plan["server_safety"]["never_keep_three_ark_servers_running"])
        self.assertEqual(plan["server_safety"]["max_running_ark_servers"], 2)
        self.assertFalse(plan["server_safety"]["standing_authority_authorizes_server_restart"])
        self.assertFalse(plan["server_safety"]["standing_authority_authorizes_marker_env_changes"])
        self.assertTrue(plan["server_safety"]["check_player_presence_before_restart"])
        self.assertEqual(plan["server_safety"]["minimum_pre_activation_lead_seconds"], 300)
        self.assertFalse(plan["server_safety"]["activation_or_restart_from_stale_request_allowed"])
        self.assertFalse(plan["server_safety"]["monitor_or_restart_activation_after_window_start_allowed"])
        self.assertIn(
            "request/check/notice/activation readiness is not approved runtime evidence",
            plan["non_claims"],
        )
        self.assertIn(
            "diagnostic candidate metadata is non-authorizing and not approved runtime evidence",
            plan["non_claims"],
        )
        self.assertIn(
            f"future player-backed copied log must contain {STRICT_TRIPLET_TEXT}",
            plan["non_claims"],
        )
        self.assertIn(
            "standing launch authority prepares a scoped request window only; "
            "it is not evidence, progress, readiness, or publication authority",
            plan["non_claims"],
        )
        self.assertIn(
            "passive waits, public queries, beta notices, request packs, and start/end-only windows "
            "do not clear approved_runtime_evidence_missing",
            plan["non_claims"],
        )
        self.assertIn(
            "copied logs must route through analyzer -> strict_lifecycle_triplet_candidate_summary -> bundle preflight -> approved-evidence checker before any accepted evidence state can change",
            plan["non_claims"],
        )
        self.assertEqual(plan["ordered_copied_log_route_step_ids"], COPIED_LOG_ROUTE_STEPS)
        assert_copied_log_route(self, plan["copied_log_route_required"], "top_level_copied_log_route")
        self.assertEqual(workflow["ordered_copied_log_route_step_ids"], COPIED_LOG_ROUTE_STEPS)
        assert_copied_log_route(
            self,
            workflow["copied_log_route_required"],
            "current_window_workflow_copied_log_route",
        )
        command_by_id = {command["id"]: command for command in plan["commands"]}
        self.assertEqual(
            list(command_by_id),
            [
                "prepare_request_pack",
                "check_request_pack",
                "beta_notice_dry_run",
                "route_gate",
                "activation_preconditions",
            ],
        )
        self.assertEqual(
            [step["id"] for step in plan["manual_followup_steps"]],
            [
                "beta_notice_confirmed_send",
                "analyze_runtime_observer_log",
                "strict_lifecycle_triplet_candidate_summary",
                "bundle_preflight",
                "check_approved_runtime_bundle",
                "post_runtime_public_contract_readiness",
                "status_after_bundle",
            ],
        )
        for command in plan["commands"]:
            assert_non_claim_flags(self, command, command["id"])
            assert_strict_triplet(
                self,
                command["strict_copied_bool_triplet_requirement"],
                command["id"],
            )
            assert_role_objectives(
                self,
                command["lifecycle_missing_role_objectives"],
                command["id"],
            )
            self.assertEqual(command["two_server_cap_policy"]["max_running_ark_servers"], 2)
        for step in plan["manual_followup_steps"]:
            self.assertTrue(step["manual_external_only"], step["id"])
            assert_non_claim_flags(self, step, step["id"])
            assert_strict_triplet(
                self,
                step["strict_copied_bool_triplet_requirement"],
                step["id"],
            )
            assert_role_objectives(
                self,
                step["lifecycle_missing_role_objectives"],
                step["id"],
            )
            self.assertEqual(step["two_server_cap_policy"]["max_running_ark_servers"], 2)
            if step["id"] in COPIED_LOG_ROUTE_STEPS:
                self.assertEqual(step["ordered_copied_log_route_step_ids"], COPIED_LOG_ROUTE_STEPS)
                assert_copied_log_route(self, step["copied_log_route_required"], step["id"])
                self.assertEqual(step["route_step_id"], step["id"])
        manual_by_id = {step["id"]: step for step in plan["manual_followup_steps"]}
        analyzer_step = manual_by_id["analyze_runtime_observer_log"]
        self.assertIn("scripts/analyze_runtime_observer_log.py", " ".join(analyzer_step["argv"]))
        self.assertEqual(analyzer_step["emits_summary_field"], STRICT_CANDIDATE_SUMMARY_JSON_PATH)
        strict_summary_step = manual_by_id["strict_lifecycle_triplet_candidate_summary"]
        self.assertIn(
            "scripts/build_player_identity_runtime_principal_lifecycle_approved_manifest.py",
            " ".join(strict_summary_step["argv"]),
        )
        self.assertEqual(strict_summary_step["consumes_summary_field"], STRICT_CANDIDATE_SUMMARY_JSON_PATH)
        self.assertTrue(strict_summary_step["candidate_ready_for_bundle_preflight_required"])
        bundle_preflight_step = manual_by_id["bundle_preflight"]
        self.assertIn("--preflight-only", bundle_preflight_step["argv"])
        self.assertEqual(bundle_preflight_step["must_follow"], "strict_lifecycle_triplet_candidate_summary")
        check_step = manual_by_id["check_approved_runtime_bundle"]
        self.assertEqual(check_step["must_follow"], "bundle_preflight")
        self.assertTrue(check_step["checker_acceptance_can_change_evidence_state_when_executed"])
        self.assertFalse(check_step["accepted_by_this_plan"])
        self.assertTrue(
            plan["manual_followup_steps"][0][
                "standing_authority_satisfies_guarded_beta_notice_send_scope"
            ]
        )
        self.assertTrue(
            plan["manual_followup_steps"][0][
                "guarded_beta_notice_send_scope_satisfied_by_standing_authority"
            ]
        )
        self.assertTrue(plan["manual_followup_steps"][0]["standing_authority_authorizes_discord_send"])
        self.assertEqual(plan["manual_followup_steps"][0]["beta_notice_transport_policy"], transport)
        self.assertEqual(
            plan["manual_followup_steps"][0]["blocked_until"],
            [
                "beta_notice_dry_run_reviewed",
                "request_window_start_in_future",
                "confirmed_send_before_window_start",
            ],
        )
        self.assertTrue(plan["manual_followup_steps"][0]["required_before_activation"])
        self.assertTrue(plan["manual_followup_steps"][0]["must_be_real_notice_not_documentation"])
        self.assertTrue(plan["manual_followup_steps"][0]["confirmed_send_must_complete_before_window_start"])
        self.assertFalse(
            plan["manual_followup_steps"][0]["activation_or_restart_from_stale_request_allowed"]
        )
        self.assertFalse(
            plan["manual_followup_steps"][0][
                "confirmed_send_requires_separate_explicit_discord_send_approval"
            ]
        )
        self.assertTrue(plan["standing_launch_authority"]["authorizes_guarded_beta_notice_send"])
        self.assertTrue(plan["standing_launch_authority"]["authorizes_beta_notice_send"])
        self.assertFalse(plan["standing_launch_authority"]["preparation_authority_only"])
        prepare_shell = command_by_id["prepare_request_pack"]["shell"]
        self.assertEqual(workflow["next_exact_command_shell"], prepare_shell)
        self.assertIn("OBELISK_ALLOW_SERVER_ROOT_WRITES=1", prepare_shell)
        self.assertIn("--standing-launch-authority", prepare_shell)
        self.assertIn("--user-policy operator_approved_beta_users", prepare_shell)
        self.assertIn("--notice-path discord-beta-testers", prepare_shell)
        self.assertIn("--approved-window-start-utc 2026-06-06T04:05:00Z", prepare_shell)
        self.assertIn("--approved-window-end-utc 2026-06-06T04:20:00Z", prepare_shell)
        self.assertNotIn("--diagnostic-candidates", prepare_shell)
        executable_shells = "\n".join(command["shell"] for command in plan["commands"])
        self.assertNotIn("--confirm-approved-send", executable_shells)
        self.assertNotIn("build_player_identity_runtime_principal_lifecycle_evidence_bundle.py", executable_shells)
        self.assertNotIn("check_player_identity_public_contract_readiness.py", executable_shells)
        self.assertNotIn("report_obelisk_sdk_status.py", executable_shells)
        self.assertIn("--confirm-approved-send", " ".join(plan["manual_followup_steps"][0]["argv"]))
        self.assertFalse(output_root.exists())

    def test_default_diagnostic_candidates_metadata_is_false_and_not_forwarded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "live-validation-logs"
            result = subprocess.run(
                base_args(output_root),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

            plan = json.loads(result.stdout)

        prepare_command = {command["id"]: command for command in plan["commands"]}["prepare_request_pack"]
        self.assertFalse(plan["diagnostic_candidates_enabled"])
        self.assertEqual(
            plan["diagnostic_candidate_metadata"],
            {
                **EXPECTED_NON_CLAIM_FLAGS,
                "enabled": False,
                "classification": "disabled",
                "propagated_to_prepare_request_pack": False,
            },
        )
        self.assertFalse(prepare_command["metadata"]["diagnostic_candidates_enabled"])
        self.assertEqual(prepare_command["metadata"]["diagnostic_candidates_classification"], "disabled")
        assert_non_claim_flags(self, prepare_command["metadata"], "prepare_request_pack.metadata")
        self.assertNotIn("--diagnostic-candidates", prepare_command["argv"])
        self.assertNotIn("--diagnostic-candidates", prepare_command["shell"])

    def test_diagnostic_candidates_opt_in_is_forwarded_as_non_evidence_prepare_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "live-validation-logs"
            args = base_args(output_root)
            args.insert(args.index("--json"), "--diagnostic-candidates")
            result = subprocess.run(
                args,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

            plan = json.loads(result.stdout)

        prepare_command = {command["id"]: command for command in plan["commands"]}["prepare_request_pack"]
        self.assertTrue(plan["diagnostic_candidates_enabled"])
        self.assertEqual(
            plan["diagnostic_candidate_metadata"],
            {
                **EXPECTED_NON_CLAIM_FLAGS,
                "enabled": True,
                "classification": "candidate_only_non_evidence",
                "propagated_to_prepare_request_pack": True,
            },
        )
        self.assertTrue(prepare_command["metadata"]["diagnostic_candidates_enabled"])
        self.assertEqual(
            prepare_command["metadata"]["diagnostic_candidates_classification"],
            "candidate_only_non_evidence",
        )
        assert_non_claim_flags(self, prepare_command["metadata"], "prepare_request_pack.metadata")
        self.assertIn("--diagnostic-candidates", prepare_command["argv"])
        self.assertLess(prepare_command["argv"].index("--diagnostic-candidates"), prepare_command["argv"].index("--json"))
        self.assertIn("--diagnostic-candidates --json", prepare_command["shell"])
        self.assertFalse(output_root.exists())

    def test_theisland_retry_after_closed_window_gets_fresh_sibling_set_and_notice_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "live-validation-logs"
            args = base_args(output_root)
            args[args.index("--instance") + 1] = "arkserver2"
            args[args.index("--map") + 1] = "TheIsland"
            args[args.index("--now-utc") + 1] = "2026-06-07T16:00:00Z"
            result = subprocess.run(
                args,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

            plan = json.loads(result.stdout)

        self.assertEqual(plan["run_id"], "20260607T160500Z-player-principal-lifecycle")
        self.assertEqual(plan["target"], {"instance": "arkserver2", "map": "TheIsland"})
        retry = plan["fresh_retry_after_closed_non_evidence_window"]
        self.assertEqual(retry["schema"], FRESH_RETRY_SCHEMA)
        self.assertEqual(
            retry["status"],
            "fresh_theisland_retry_prepared_after_expired_non_evidence_window",
        )
        self.assertTrue(retry["exact_target_required"])
        self.assertFalse(retry["target_aliases_allowed"])
        self.assertTrue(retry["target_matches_previous_theisland_window"])
        self.assertTrue(retry["fresh_retry_allowed_without_reusing_previous_window"])
        self.assertTrue(retry["previous_window_preserved_as_non_evidence"])
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
        self.assertEqual(previous["start_utc"], "2026-06-07T13:49:29Z")
        self.assertEqual(previous["end_utc"], "2026-06-07T15:49:29Z")
        self.assertEqual(previous["lifecycle_state"], "expired")
        self.assertFalse(previous["active"])
        self.assertTrue(previous["expired"])
        self.assertTrue(previous["closed"])
        self.assertTrue(previous["post_restart_closed_non_evidence_window"])
        self.assertFalse(previous["counts_as_approved_runtime_evidence"])
        fresh = retry["fresh_window"]
        self.assertEqual(fresh["run_id"], plan["run_id"])
        self.assertNotEqual(fresh["run_id"], previous["run_id"])
        self.assertEqual(fresh["target"], plan["target"])
        self.assertEqual(fresh["target_key"], "arkserver2:TheIsland:27016")
        self.assertEqual(fresh["start_utc"], "2026-06-07T16:05:00Z")
        self.assertEqual(fresh["end_utc"], "2026-06-07T16:20:00Z")
        self.assertEqual(fresh["sibling_set_root"], plan["evidence_dir"])
        self.assertTrue(fresh["uses_own_sibling_set"])
        self.assertTrue(fresh["start_end_bound_to_fresh_run"])
        self.assertTrue(fresh["exact_target_bound"])
        self.assertFalse(fresh["previous_sibling_set_reuse_allowed"])
        self.assertFalse(fresh["previous_notice_sidecars_reuse_allowed"])
        self.assertFalse(fresh["previous_start_end_reuse_allowed"])
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
            str(Path(plan["evidence_dir"]) / "window-request.json"),
        )
        dry_sidecar = fresh["notice_sidecar_paths"]["beta_notice_dry_run_sidecar_json"]
        confirmed_sidecar = fresh["notice_sidecar_paths"]["beta_notice_confirmed_sidecar_json"]
        self.assertIn("arkserver2-TheIsland", dry_sidecar)
        self.assertIn(plan["run_id"], dry_sidecar)
        self.assertTrue(dry_sidecar.endswith("beta-notice.dry-run.sidecar.json"))
        self.assertTrue(confirmed_sidecar.endswith("beta-notice.confirmed.sidecar.json"))
        self.assertEqual(plan["current_window_workflow"]["fresh_retry_after_closed_non_evidence_window"], retry)
        self.assertEqual(plan["artifacts"]["beta_notice_dry_run_sidecar"], dry_sidecar)
        self.assertEqual(plan["artifacts"]["beta_notice_confirmed_sidecar"], confirmed_sidecar)

    def test_theisland_previous_window_active_state_is_not_marked_expired(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "live-validation-logs"
            args = base_args(output_root)
            args[args.index("--instance") + 1] = "arkserver2"
            args[args.index("--map") + 1] = "TheIsland"
            args[args.index("--now-utc") + 1] = "2026-06-07T14:00:00Z"
            result = subprocess.run(
                args,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

            plan = json.loads(result.stdout)

        retry = plan["fresh_retry_after_closed_non_evidence_window"]
        previous = retry["previous_window"]
        self.assertEqual(previous["lifecycle_state"], "active")
        self.assertTrue(previous["active"])
        self.assertFalse(previous["expired"])
        self.assertFalse(previous["closed"])
        self.assertFalse(previous["post_restart_closed_non_evidence_window"])
        self.assertFalse(retry["fresh_retry_allowed_without_reusing_previous_window"])
        self.assertTrue(retry["previous_window_preserved_as_non_evidence"])
        self.assertFalse(retry["previous_run_counts_as_approved_runtime_evidence"])

    def test_no_positive_claim_flags_for_authority_readiness_beta_passive_or_start_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = load_plan(Path(tmp) / "live-validation-logs")

        for key, value in iter_key_values(plan):
            if key in CLAIM_FLAG_KEYS_MUST_STAY_FALSE:
                self.assertIs(value, False, key)

        authority = plan["standing_launch_authority"]
        self.assertTrue(authority["authorizes_scoped_runtime_window_preparation"])
        self.assertFalse(authority["authorizes_runtime_capture"])
        self.assertFalse(authority["authorizes_publication"])
        self.assertFalse(authority["authorizes_readiness"])
        self.assertFalse(authority["authorizes_p0_progress"])

        workflow = plan["current_window_workflow"]
        self.assertFalse(workflow["plan_counts_as_progress"])
        self.assertFalse(workflow["plan_counts_as_runtime_readiness"])
        self.assertFalse(workflow["plan_counts_as_public_readiness"])
        self.assertFalse(workflow["dry_run_or_send_metadata_counts_as_evidence"])
        self.assertFalse(workflow["passive_wait_counts_as_approved_runtime_evidence"])
        self.assertFalse(workflow["start_end_only_counts_as_approved_runtime_evidence"])

        requirement = plan["strict_copied_bool_triplet_requirement"]
        self.assertFalse(requirement["standing_launch_authority_satisfies_requirement"])
        self.assertFalse(requirement["plan_or_request_pack_satisfies_requirement"])
        self.assertFalse(requirement["beta_notice_satisfies_requirement"])
        self.assertFalse(requirement["passive_wait_satisfies_requirement"])
        self.assertFalse(requirement["public_query_satisfies_requirement"])
        self.assertFalse(requirement["start_end_only_satisfies_requirement"])

    def test_output_strings_do_not_claim_shortcut_evidence_or_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = load_plan(Path(tmp) / "live-validation-logs")

        text = "\n".join(all_strings(plan)).lower()
        forbidden_phrases = [
            "standing launch authority clears",
            "standing launch authority counts as",
            "standing launch authority is evidence",
            "standing launch authority is progress",
            "standing launch authority is readiness",
            "standing authority clears",
            "standing authority counts as",
            "plan is ready",
            "plan ready",
            "plan clears approved_runtime_evidence_missing",
            "request pack clears approved_runtime_evidence_missing",
            "beta notice clears",
            "beta notice counts as",
            "beta notice is evidence",
            "beta notices clear approved_runtime_evidence_missing",
            "passive wait clears",
            "passive wait counts",
            "passive wait is evidence",
            "passive waits clear approved_runtime_evidence_missing",
            "public query clears approved_runtime_evidence_missing",
            "start/end-only evidence accepted",
            "start/end-only evidence clears",
            "start/end-only evidence counts",
            "start/end-only window accepted",
            "start/end-only windows clear approved_runtime_evidence_missing",
        ]
        for phrase in forbidden_phrases:
            self.assertNotIn(phrase, text)

    def test_active_player_no_accepted_events_routes_to_source_bound_drift_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp) / "live-validation-logs")
            args.insert(args.index("--json"), "--active-player-no-accepted-events")
            result = subprocess.run(
                args,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            plan = json.loads(result.stdout)

        policy = plan["active_player_no_accepted_events_policy"]
        self.assertEqual(policy["classification"], "source_bound_drift_blocker_non_evidence")
        self.assertTrue(policy["source_bound_blocker"])
        self.assertTrue(policy["route_to_drift_or_source_bound_blocker"])
        self.assertEqual(
            policy["current_route_blocker"],
            "source_bound_active_player_no_accepted_lifecycle_events",
        )
        self.assertEqual(plan["effective_restart_expectation"], "none")
        self.assertFalse(policy["restart_recommended"])
        self.assertFalse(policy["start_or_restart_recommended"])
        self.assertFalse(policy["blind_wait_recommended"])
        self.assertFalse(policy["wait_or_restart_or_logout_instruction_allowed"])
        self.assertFalse(policy["logout_or_reconnect_instruction_allowed"])
        self.assertFalse(policy["counts_as_approved_runtime_evidence"])
        self.assertFalse(policy["counts_as_progress"])
        self.assertFalse(plan["current_window_workflow"]["restart_recommended"])
        self.assertFalse(plan["server_safety"]["check_player_presence_before_restart"])

    def test_rcon_present_query_zero_next_action_keeps_waiting_without_blind_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp) / "live-validation-logs")
            args.extend(["--presence-source-discrepancy", "rcon_present_query_zero"])
            result = subprocess.run(
                args,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            plan = json.loads(result.stdout)

        policy = plan["next_action_policy"]
        self.assertEqual(policy["schema"], "obelisk.player-principal-lifecycle-runtime-window-next-action-policy.v1")
        self.assertEqual(policy["next_action_id"], "keep_waiting_rcon_present_query_zero")
        self.assertTrue(policy["source_discrepancy_detected"])
        self.assertTrue(policy["rcon_present_query_zero_discrepancy"])
        self.assertTrue(policy["keep_waiting_recommended"])
        self.assertFalse(policy["broadcast_recommended"])
        self.assertFalse(policy["blind_restart_allowed"])
        self.assertTrue(policy["blind_restart_blocked"])
        self.assertFalse(policy["server_operations_authorized"])
        self.assertFalse(policy["discord_send_authorized"])
        self.assertFalse(policy["counts_as_approved_runtime_evidence"])
        self.assertEqual(plan["current_window_workflow"]["next_action_id"], policy["next_action_id"])
        self.assertTrue(plan["current_window_workflow"]["keep_waiting_recommended"])
        self.assertFalse(plan["server_safety"]["blind_restart_allowed"])

    def test_session_end_only_no_start_next_action_prepares_clean_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp) / "live-validation-logs")
            args.insert(args.index("--json"), "--session-end-only-no-start")
            result = subprocess.run(
                args,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            plan = json.loads(result.stdout)

        policy = plan["next_action_policy"]
        self.assertEqual(policy["next_action_id"], "prepare_clean_window_session_end_only_no_start")
        self.assertTrue(policy["session_end_only_no_start"])
        self.assertFalse(policy["keep_waiting_recommended"])
        self.assertTrue(policy["prepare_clean_window_recommended"])
        self.assertTrue(policy["clean_window_required_before_next_evidence_attempt"])
        self.assertFalse(policy["blind_restart_allowed"])
        self.assertFalse(policy["server_operations_authorized"])
        self.assertFalse(policy["counts_as_progress"])
        self.assertFalse(policy["clears_approved_runtime_evidence_missing"])
        self.assertEqual(plan["server_safety"]["next_action_id"], policy["next_action_id"])
        self.assertTrue(plan["server_safety"]["prepare_clean_window_recommended"])

    def test_human_output_includes_non_claim_flags_and_strict_triplet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp) / "live-validation-logs")
            args.remove("--json")
            result = subprocess.run(
                args,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

        self.assertIn(f"Strict copied bool triplet: {STRICT_TRIPLET_TEXT}", result.stdout)
        self.assertIn("Missing-role objectives: session_start, CheckJoinInProgress(1,0), session_end", result.stdout)
        self.assertIn(
            "evidence=false progress=false readiness=false "
            "clears_approved_runtime_evidence_missing=false",
            result.stdout,
        )
        self.assertGreaterEqual(result.stdout.count("Non-claim flags:"), 10)

    def test_rejects_beta_window_without_beta_notice_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp))
            args.extend(["--notice-path", "other-channel"])
            result = subprocess.run(
                args,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--notice-path must be discord-beta-testers", result.stderr)

    def test_rejects_runtime_window_with_too_little_lead_time(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp))
            args[args.index("--start-delay-minutes") + 1] = "1"
            result = subprocess.run(
                args,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--start-delay-minutes must be at least 5", result.stderr)

    def test_accepts_two_hour_runtime_window_without_claiming_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp))
            args[args.index("--duration-minutes") + 1] = "120"
            result = subprocess.run(
                args,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            plan = json.loads(result.stdout)

        self.assertEqual(plan["approved_window"]["duration_seconds"], 7200)
        self.assertEqual(plan["approved_window"]["max_duration_seconds"], 7200)
        self.assertFalse(plan["strict_copied_bool_triplet_requirement"]["counts_as_approved_runtime_evidence"])
        self.assertFalse(plan["server_safety"]["monitor_or_restart_activation_after_window_start_allowed"])

    def test_rejects_window_longer_than_two_hours(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = base_args(Path(tmp))
            args[args.index("--duration-minutes") + 1] = "121"
            result = subprocess.run(
                args,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--duration-minutes must not exceed 120 minutes", result.stderr)

    def test_rejects_live_server_root_output_outside_offline_workspace(self) -> None:
        args = base_args(Path("/servidor/ark/serverfiles/live-validation-logs"))
        result = subprocess.run(
            args,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--output-root must be outside /servidor/ark or under /servidor/ark/workspace-offline", result.stderr)


if __name__ == "__main__":
    unittest.main()
