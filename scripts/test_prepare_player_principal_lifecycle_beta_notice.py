#!/usr/bin/env python3
"""Tests for prepare_player_principal_lifecycle_beta_notice.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "prepare_player_principal_lifecycle_beta_notice.py"
sys.path.insert(0, str(SCRIPT_DIR))

from prepare_player_principal_lifecycle_window_request import (  # noqa: E402
    APPROVED_BETA_NOTICE_PATH,
    EXACT_TARGET_SCOPE_NON_AUTHORIZATION,
    EXACT_TARGET_SCOPE_SCHEMA,
    PLAYER_NOTICE_ACTION_NON_AUTHORIZATION,
    direct_join_plan,
)
from discord_beta_bridge import (  # noqa: E402
    DISCORD_BETA_NON_PROMOTION_FLAGS,
    DISCORD_BETA_NON_PROMOTION_SCHEMA,
    SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE,
)
from prepare_player_principal_lifecycle_beta_notice import (  # noqa: E402
    BETA_NOTICE_REQUIRED_HELPER_ARGS,
    BETA_TEST_ACTIVE_NOTICE_STATE_ENV,
    BETA_TEST_BOT_CHANNEL_ID,
    BETA_TEST_BOT_ENV_VARS,
    BETA_TEST_CHANNEL,
    BETA_TEST_EVENT_SINK_ENV,
    BETA_STATUS_SUMMARY_CUSTOM_ID,
    BETA_STATUS_SUMMARY_RESPONSE_MODE,
    BETA_TESTER_STATUS_WORKFLOW_SCHEMA,
    BETA_TEST_WEBHOOK_ENV,
    DISCORD_SEND_SCOPE_BLOCKER,
    NOTICE_ACTION_ARTIFACT_SCHEMA,
    SIDECAR_NON_EVIDENCE_FLAGS,
    STALE_WINDOW_BLOCKER,
    validate_beta_notice_helper_args,
)

EXACT_TESTER_EVIDENCE_OBJECTIVE = (
    "produce session_start, exact CheckJoinInProgress(1,0) session_start_rejected, "
    "and matched session_end"
)


def assert_discord_beta_non_promotion(
    testcase: unittest.TestCase,
    boundary: dict[str, object],
) -> None:
    testcase.assertEqual(boundary["schema"], DISCORD_BETA_NON_PROMOTION_SCHEMA)
    testcase.assertEqual(
        boundary["single_operational_message_style"],
        SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE,
    )
    testcase.assertTrue(boundary["accepted_copied_sibling_set_required_before_runtime_claims"])
    for key, expected in DISCORD_BETA_NON_PROMOTION_FLAGS.items():
        with testcase.subTest(discord_beta_non_promotion=key):
            testcase.assertIs(boundary[key], expected)


def assert_single_updated_notice_boundary(
    testcase: unittest.TestCase,
    value: dict[str, object],
) -> None:
    testcase.assertEqual(value["operational_message_style"], SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE)
    testcase.assertTrue(value["single_updated_embed_buttons_message_preferred"])
    testcase.assertTrue(value["edit_existing_message_when_active_notice_state_present"])
    testcase.assertTrue(value["post_only_when_active_notice_state_missing"])
    testcase.assertFalse(value["discord_or_beta_interactions_count_as_sdk_progress"])
    testcase.assertFalse(value["discord_or_beta_interactions_count_as_p0_progress"])
    testcase.assertFalse(value["discord_or_beta_interactions_count_as_public_sdk_readiness"])
    testcase.assertFalse(value["discord_or_beta_interactions_count_as_stable_sdk_readiness"])
    testcase.assertFalse(value["discord_or_beta_interactions_authorize_discord_send"])
    testcase.assertFalse(value["discord_or_beta_interactions_authorize_live_actions"])
    testcase.assertFalse(value["discord_or_beta_interactions_approve_live_actions"])
    testcase.assertFalse(value["public_sdk_ready"])
    testcase.assertFalse(value["stable_sdk_ready"])
    assert_discord_beta_non_promotion(testcase, value["discord_beta_non_promotion"])


def future_window() -> tuple[str, str, str]:
    start = (datetime.now(timezone.utc) + timedelta(minutes=20)).replace(microsecond=0)
    end = start + timedelta(minutes=15)
    return (
        start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle",
        start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def request_payload(
    *,
    required: bool = True,
    notice_path: str = APPROVED_BETA_NOTICE_PATH,
    standing_authority: bool = False,
    run_id: str | None = None,
    start_utc: str | None = None,
    end_utc: str | None = None,
) -> dict[str, object]:
    if run_id is None or start_utc is None or end_utc is None:
        run_id, start_utc, end_utc = future_window()
    target = {"instance": "arkserver3", "map": "Genesis2"}
    exact_target_scope = {
        "schema": EXACT_TARGET_SCOPE_SCHEMA,
        "instance": target["instance"],
        "map": target["map"],
        "instance_alias_allowed": False,
        "map_alias_allowed": False,
        "approval_must_name_exact_instance_and_map": True,
        "target_matches_request_target": True,
        "non_authorization": EXACT_TARGET_SCOPE_NON_AUTHORIZATION,
    }
    payload: dict[str, object] = {
        "schema": "obelisk.player-principal-lifecycle-window-request.v1",
        "user_policy": "operator_approved_beta_users" if required else "no_regular_users",
        "notice_path": notice_path,
        "target": target,
        "exact_target_scope": exact_target_scope,
        "run_id": run_id,
        "approved_window": {
            "start_utc": start_utc,
            "end_utc": end_utc,
        },
        "player_notice_action": {
            "schema": "obelisk.player-principal-lifecycle-player-notice-action.v1",
            "required": required,
            "notice_path": notice_path,
            "approved_notice_path_must_be_named": required,
            "dry_run_required_before_send": required,
            "real_notice_send_required_before_activation": required,
            "send_performed_by_request_pack": False,
            "request_pack_authorizes_discord": False,
            "activation_allowed_before_notice_sent": not required,
            "evidence_required": "dry_run_output_and_send_confirmation_reference"
            if required
            else "not_applicable",
            "activation_blocker": "approved_dry_run_checked_beta_testers_notice_sent"
            if required
            else "no_player_notice_required",
            "non_authorization": PLAYER_NOTICE_ACTION_NON_AUTHORIZATION if required else "not_applicable",
        },
    }
    payload["direct_join_plan"] = direct_join_plan(payload)
    if standing_authority:
        payload["current_turn_approval_scope"] = {
            "source_required": "standing_launch_authority",
            "required_named_scope": {
                "target": target,
                "exact_target_instance_map": exact_target_scope,
                "direct_join_plan": payload["direct_join_plan"],
            },
        }
    return payload


def write_request(path: Path, payload: dict[str, object] | None = None) -> Path:
    path.write_text(json.dumps(payload or request_payload(), sort_keys=True) + "\n", encoding="utf-8")
    return path


def default_notice_sidecar(request_json: Path, mode: str) -> Path:
    return request_json.parent / f"beta-notice.{mode.replace('_', '-')}.sidecar.json"


def write_strict_receipt_helper(
    helper: Path,
    called: Path,
    *,
    confirm_stderr: str | None = None,
) -> None:
    helper.write_text(
        "import hashlib, json, sys\n"
        f"called = {str(called)!r}\n"
        f"confirm_stderr = {confirm_stderr!r}\n"
        "args = sys.argv[1:]\n"
        "\n"
        "def option_value(name):\n"
        "    if name not in args:\n"
        "        return None\n"
        "    index = args.index(name)\n"
        "    return args[index + 1] if index + 1 < len(args) else None\n"
        "\n"
        "content = option_value('--content') or ''\n"
        "receipt_inputs = {\n"
        "    'content_sha256': hashlib.sha256(content.encode('utf-8')).hexdigest(),\n"
        "    'with_beta_controls': '--with-beta-controls' in args,\n"
        "    'update_active_notice_requested': '--update-active-notice' in args,\n"
        "}\n"
        "receipt = 'strict-dry-run:' + hashlib.sha256(\n"
        "    json.dumps(receipt_inputs, sort_keys=True, separators=(',', ':')).encode('utf-8')\n"
        ").hexdigest()\n"
        "try:\n"
        "    calls = json.loads(open(called, encoding='utf-8').read())\n"
        "except Exception:\n"
        "    calls = []\n"
        "calls.append(args)\n"
        "open(called, 'w', encoding='utf-8').write(json.dumps(calls))\n"
        "\n"
        "for required in ('--send-beta-notice', '--with-beta-controls', '--update-active-notice'):\n"
        "    if required not in args:\n"
        "        print('missing ' + required, file=sys.stderr)\n"
        "        sys.exit(10)\n"
        "\n"
        "if '--dry-run' in args:\n"
        "    if '--confirm-approved-send' in args or '--dry-run-receipt' in args:\n"
        "        print('dry run must not include confirm or receipt', file=sys.stderr)\n"
        "        sys.exit(11)\n"
        "    print(json.dumps({\n"
        "        'schema': 'strict-helper-dry-run.v1',\n"
        "        'dry_run_receipt': receipt,\n"
        "        'dry_run_receipt_inputs': receipt_inputs,\n"
        "        'dry_run_receipt_validated': False,\n"
        "        'content': content,\n"
        "        'with_beta_controls': True,\n"
        "        'update_active_notice_requested': True,\n"
        "        'discord_sent': False,\n"
        "    }, sort_keys=True))\n"
        "    sys.exit(0)\n"
        "\n"
        "if '--confirm-approved-send' not in args:\n"
        "    print('missing --confirm-approved-send', file=sys.stderr)\n"
        "    sys.exit(12)\n"
        "supplied = option_value('--dry-run-receipt')\n"
        "if not supplied:\n"
        "    print('missing --dry-run-receipt', file=sys.stderr)\n"
        "    sys.exit(13)\n"
        "if supplied != receipt:\n"
        "    print('dry-run receipt mismatch', file=sys.stderr)\n"
        "    sys.exit(14)\n"
        "if confirm_stderr:\n"
        "    print(confirm_stderr, file=sys.stderr)\n"
        "print(json.dumps({\n"
        "    'schema': 'strict-helper-confirmed-send.v1',\n"
        "    'dry_run_receipt': supplied,\n"
        "    'dry_run_receipt_inputs': receipt_inputs,\n"
        "    'dry_run_receipt_validated': True,\n"
        "    'content': content,\n"
        "    'with_beta_controls': True,\n"
        "    'update_active_notice_requested': True,\n"
        "    'send_performed': True,\n"
        "    'discord_sent': True,\n"
        "}, sort_keys=True))\n",
        encoding="utf-8",
    )


class PreparePlayerPrincipalLifecycleBetaNoticeTests(unittest.TestCase):
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

    def run_script(
        self,
        request_json: Path,
        *extra: str,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        merged_env = {
            **os.environ,
            "OBELISK_DISCORD_ACTIVE_NOTICE_STATE": str(request_json.parent / "active-notice.json"),
        }
        if env is not None:
            merged_env.update(env)
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--request-json", str(request_json), "--json", *extra],
            cwd=SCRIPT_DIR.parents[0],
            env=merged_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_beta_notice_helper_args_require_bot_controls_and_reject_webhook_options(self) -> None:
        validate_beta_notice_helper_args(
            [
                "--send-beta-notice",
                "--with-beta-controls",
                "--update-active-notice",
                "--content",
                "@everyone",
            ]
        )

        with self.assertRaises(SystemExit) as missing:
            validate_beta_notice_helper_args(
                [
                    "--send-beta-notice",
                    "--with-beta-controls",
                    "--content",
                    "@everyone",
                ]
            )
        self.assertIn("--update-active-notice", str(missing.exception))

        with self.assertRaises(SystemExit) as webhook:
            validate_beta_notice_helper_args(
                [
                    "--send-beta-notice",
                    "--with-beta-controls",
                    "--update-active-notice",
                    "--webhook-url",
                    "https://example.invalid/not-used",
                    "--content",
                    "@everyone",
                ]
            )
        self.assertIn("forbidden_webhook_helper_args", str(webhook.exception))

    def test_dry_run_builds_beta_notice_without_authorizing_discord_or_sdk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json")
            result = self.run_script(request_json, "--dry-run")
            report = json.loads(result.stdout)
            sidecar = json.loads(
                default_notice_sidecar(request_json, "dry_run").read_text(encoding="utf-8")
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report["ready"])
        self.assertTrue(report["prepared"])
        self.assertTrue(report["notice_prepared"])
        self.assertTrue(report["prepared_notice_action"])
        self.assertTrue(report["prepared_metadata_only"])
        self.assertEqual(report["preparation_status"], "prepared_metadata_only")
        self.assertTrue(report["ready_field_is_helper_success_gate_only"])
        self.assertFalse(report["ready_field_is_readiness_claim"])
        self.assertEqual(report["tester_evidence_objective"], EXACT_TESTER_EVIDENCE_OBJECTIVE)
        self.assertFalse(report["readiness_claim_allowed"])
        self.assertFalse(report["progress_claim_allowed"])
        self.assertFalse(report["preparation_counts_as_readiness"])
        self.assertFalse(report["preparation_counts_as_progress"])
        self.assertEqual(report["mode"], "dry_run")
        self.assertEqual(sidecar["schema"], NOTICE_ACTION_ARTIFACT_SCHEMA)
        self.assertEqual(sidecar["mode"], "dry_run")
        self.assertEqual(sidecar["notice_report"], report)
        self.assertFalse(sidecar["stdout_only_confirmation_accepted"])
        self.assertTrue(sidecar["sidecar_required_for_confirmed_send_consumption"])
        for key, expected in SIDECAR_NON_EVIDENCE_FLAGS.items():
            with self.subTest(sidecar_flag=key):
                self.assertIs(sidecar[key], expected)
        self.assertEqual(report["notice_action_sidecar_json"], str(default_notice_sidecar(Path(tmp) / "window-request.json", "dry_run")))
        self.assertEqual(report["target"], {"instance": "arkserver3", "map": "Genesis2"})
        self.assertEqual(report["notice_path"], APPROVED_BETA_NOTICE_PATH)
        self.assertTrue(report["dry_run_required_before_send"])
        self.assertTrue(report["real_notice_send_required_before_activation"])
        self.assertEqual(report["activation_blocker_until_sent"], "approved_dry_run_checked_beta_testers_notice_sent")
        self.assertFalse(report["activation_allowed"])
        self.assertFalse(report["activation_allowed_before_notice_sent"])
        self.assertFalse(report["activation_preconditions_met"])
        self.assertFalse(report["server_operations_authorized"])
        self.assertFalse(report["authorizes_server_operations"])
        self.assertFalse(report["authorizes_discord"])
        self.assertFalse(report["discord_authorized"])
        self.assertFalse(report["publication_authorized"])
        self.assertFalse(report["live_ops_authorized"])
        self.assertFalse(report["live_log_reads_authorized"])
        self.assertFalse(report["live_log_permission_granted"])
        self.assertFalse(report["runtime_capture_authorized"])
        self.assertFalse(report["runtime_window_authorized"])
        self.assertFalse(report["discord_sent"])
        self.assertFalse(report["discord_send_authorized"])
        self.assertFalse(report["current_turn_approval_recorded"])
        self.assertFalse(report["current_turn_scope_authorized"])
        self.assertFalse(report["default_sends_discord"])
        self.assertFalse(report["default_touches_ark"])
        self.assertFalse(report["default_reads_live_logs"])
        self.assertFalse(report["default_edits_markers_or_env"])
        self.assertFalse(report["dry_run_sends_discord"])
        self.assertFalse(report["dry_run_touches_ark"])
        self.assertEqual(report["channel"], BETA_TEST_CHANNEL)
        self.assertEqual(report["bot_channel_id"], BETA_TEST_BOT_CHANNEL_ID)
        self.assertEqual(report["expected_channel_id"], BETA_TEST_BOT_CHANNEL_ID)
        self.assertEqual(report["bot_channel_env_var"], "OBELISK_DISCORD_BETA_CHANNEL_ID")
        self.assertTrue(report["bot_channel_required_for_real_send"])
        self.assertFalse(report["standing_launch_authority_recorded"])
        self.assertFalse(report["standing_authority_satisfies_guarded_beta_notice_send_scope"])
        self.assertFalse(report["guarded_beta_notice_send_scope_satisfied_by_standing_authority"])
        self.assertFalse(report["guarded_discord_send_scope_satisfied"])
        self.assertFalse(report["standing_authority_authorizes_discord_send"])
        self.assertFalse(report["standing_authority_authorizes_marker_env_changes"])
        self.assertFalse(report["standing_authority_authorizes_server_restart"])
        self.assertEqual(report["two_server_cap_policy"]["max_running_ark_servers"], 2)
        self.assertTrue(report["two_server_cap_policy"]["never_keep_three_ark_servers_running"])
        self.assertFalse(report["two_server_cap_policy"]["three_ark_servers_allowed"])
        self.assertEqual(
            report["lifecycle_missing_role_objectives"]["objective_ids"],
            ["session_start", "CheckJoinInProgress(1,0)", "session_end"],
        )
        self.assert_lifecycle_objective(report["lifecycle_missing_role_objectives"])
        recommended = report["recommended_notice_text"]
        self.assertEqual(recommended["tester_evidence_objective"], EXACT_TESTER_EVIDENCE_OBJECTIVE)
        self.assertFalse(recommended["readiness_claim_allowed"])
        self.assertFalse(recommended["progress_claim_allowed"])
        self.assertFalse(recommended["preparation_counts_as_readiness"])
        self.assertFalse(recommended["preparation_counts_as_progress"])
        self.assertTrue(recommended["recommended_text_already_redacted"])
        self.assertFalse(recommended["raw_player_text_or_identity_allowed"])
        self.assertFalse(recommended["secret_or_webhook_output_allowed"])
        self.assertFalse(recommended["direct_join_plan"]["third_ark_server_allowed"])
        self.assertEqual(recommended["direct_join_plan"]["organic_wait_window_seconds"], 900)
        self.assertFalse(recommended["broad_discord_or_community_notice_allowed"])
        self.assertTrue(recommended["beta_runtime_choreography"]["single_tester_only"])
        self.assertTrue(recommended["beta_runtime_choreography"]["direct_target_join_required"])
        self.assertFalse(
            recommended["beta_runtime_choreography"][
                "logout_or_cluster_transfer_or_reconnect_before_exact_checkjoin_allowed"
            ]
        )
        self.assertFalse(recommended["mixed_transfer_reconnect_same_approved_window_allowed"])
        self.assertIn("direct-join", recommended["recommended_discord_text_redacted"])
        self.assertIn("One selected tester only", recommended["recommended_discord_text_redacted"])
        self.assertIn("Do not cluster-transfer, reconnect", recommended["recommended_discord_text_redacted"])
        self.assertIn("Started, Loading, In-server", recommended["recommended_discord_text_redacted"])
        self.assertIn("Status summary", recommended["recommended_discord_text_redacted"])
        self.assertIn("CheckJoinInProgress(1,0)", recommended["recommended_discord_text_redacted"])
        self.assertIn(EXACT_TESTER_EVIDENCE_OBJECTIVE, recommended["recommended_discord_text_redacted"])
        self.assertNotIn("discord.com/api/webhooks", recommended["recommended_discord_text_redacted"])
        self.assertTrue(report["request_window_sendable"])
        self.assertTrue(report["current_request_window"])
        self.assertFalse(report["stale_request_window"])
        self.assertFalse(report["send_blocked_by_stale_window"])
        self.assertEqual(report["request_window_blocker"], "none")
        self.assertEqual(report["request_window_sendability"]["status"], "sendable_current_window")
        self.assertTrue(report["request_window_sendability"]["confirmed_send_allowed_by_request_window"])
        self.assertTrue(report["request_window_sendability"]["helper_invocation_allowed_by_request_window"])
        self.assertFalse(report["request_window_sendability"]["request_window_must_be_regenerated"])
        self.assertEqual(report["current_window_workflow"]["status"], "current_window_prepared")
        self.assertTrue(report["current_window_workflow"]["current_window_prepared"])
        self.assertTrue(report["current_window_workflow"]["prepared_metadata_only"])
        self.assertFalse(report["current_window_workflow"]["readiness_claim_allowed"])
        self.assertFalse(report["current_window_workflow"]["progress_claim_allowed"])
        self.assertFalse(report["current_window_workflow"]["current_window_request_must_be_regenerated"])
        self.assertFalse(report["current_window_workflow"]["plan_writes_files"])
        self.assertFalse(report["current_window_workflow"]["plan_touches_ark"])
        self.assertFalse(report["current_window_workflow"]["plan_sends_discord"])
        self.assertFalse(report["current_window_workflow"]["plan_authorizes_runtime"])
        self.assertTrue(report["notice_authority_boundary"]["separate_operator_authorization_required_before_confirmed_send"])
        self.assertTrue(report["notice_authority_boundary"]["fresh_separate_notice_approval_required"])
        self.assertFalse(report["notice_authority_boundary"]["default_sends_discord"])
        self.assertFalse(report["notice_authority_boundary"]["default_touches_ark"])
        self.assertFalse(report["notice_authority_boundary"]["default_reads_live_logs"])
        self.assertFalse(report["notice_authority_boundary"]["default_edits_markers_or_env"])
        dry_run_boundary = report["dry_run_consumption_boundary"]
        self.assertFalse(dry_run_boundary["dry_run_output_consumable_under_recorded_standing_launch_authority"])
        self.assertTrue(dry_run_boundary["fresh_separate_notice_approval_required"])
        self.assertTrue(dry_run_boundary["dry_run_output_is_notice_metadata_only"])
        self.assertFalse(dry_run_boundary["default_sends_discord"])
        self.assertFalse(dry_run_boundary["default_touches_ark"])
        self.assertFalse(dry_run_boundary["dry_run_sends_discord"])
        self.assertFalse(dry_run_boundary["dry_run_touches_ark"])
        self.assertFalse(dry_run_boundary["dry_run_counts_as_approved_runtime_evidence"])
        self.assertFalse(dry_run_boundary["dry_run_counts_toward_sdk"])
        ready_to_send = report["dry_run_ready_to_send"]
        self.assertEqual(
            ready_to_send["schema"],
            "obelisk.player-principal-lifecycle-beta-notice-dry-run-ready-to-send.v1",
        )
        self.assertTrue(ready_to_send["ready_to_send"])
        self.assertTrue(ready_to_send["prepared_notice_action"])
        self.assertTrue(ready_to_send["prepared_metadata_only"])
        self.assertEqual(ready_to_send["preparation_status"], "prepared_metadata_only")
        self.assertTrue(ready_to_send["ready_fields_are_sendability_gates_only"])
        self.assertFalse(ready_to_send["ready_fields_are_readiness_claims"])
        self.assertEqual(ready_to_send["tester_evidence_objective"], EXACT_TESTER_EVIDENCE_OBJECTIVE)
        self.assertTrue(ready_to_send["ready_to_send_via_discord_bot_channel"])
        self.assertFalse(ready_to_send["ready_to_send_via_obelisk_beta_test_webhook_url"])
        self.assertEqual(ready_to_send["ready_to_send_via_env_var"], "OBELISK_DISCORD_BETA_CHANNEL_ID")
        self.assertEqual(ready_to_send["bot_channel_id"], BETA_TEST_BOT_CHANNEL_ID)
        self.assertEqual(ready_to_send["expected_channel_id"], BETA_TEST_BOT_CHANNEL_ID)
        self.assertEqual(ready_to_send["approval_scope_required"], BETA_TEST_BOT_CHANNEL_ID)
        self.assertEqual(ready_to_send["approval_scope_label"], BETA_TEST_CHANNEL)
        self.assertEqual(ready_to_send["bot_env_vars"], BETA_TEST_BOT_ENV_VARS)
        self.assertEqual(ready_to_send["webhook_env_var"], BETA_TEST_WEBHOOK_ENV)
        self.assertTrue(ready_to_send["webhook_deprecated"])
        self.assertFalse(ready_to_send["webhook_real_send_allowed"])
        self.assertTrue(ready_to_send["webhook_fail_closed_for_real_sends"])
        self.assertFalse(ready_to_send["webhook_fallback_allowed"])
        self.assertEqual(ready_to_send["configured_send_path"], "discord_bot_channel")
        self.assertEqual(ready_to_send["operational_message_workflow"], "single_active_bot_notice")
        assert_single_updated_notice_boundary(self, ready_to_send)
        self.assertTrue(ready_to_send["single_operational_message_required"])
        self.assertTrue(ready_to_send["active_notice_state_required_for_beta_controls"])
        self.assertTrue(ready_to_send["single_editable_notice_required"])
        self.assertTrue(ready_to_send["single_editable_embed_required"])
        self.assertTrue(ready_to_send["with_beta_controls_required"])
        self.assertTrue(ready_to_send["update_active_notice_required"])
        self.assertTrue(ready_to_send["new_message_only_when_active_notice_state_missing"])
        self.assertTrue(ready_to_send["existing_active_notice_updates_in_place"])
        self.assertEqual(
            ready_to_send["required_helper_args"],
            list(BETA_NOTICE_REQUIRED_HELPER_ARGS),
        )
        self.assertEqual(ready_to_send["required_env_vars"], BETA_TEST_BOT_ENV_VARS)
        self.assertEqual(ready_to_send["channel"], BETA_TEST_CHANNEL)
        self.assertTrue(ready_to_send["request_window_sendable"])
        self.assertFalse(ready_to_send["stale_request_window"])
        self.assertFalse(ready_to_send["send_blocked_by_stale_window"])
        self.assertEqual(ready_to_send["request_window_sendability"]["status"], "sendable_current_window")
        self.assertTrue(ready_to_send["mentions_everyone"])
        self.assertEqual(ready_to_send["content"], "@everyone")
        self.assertIn("--confirm-approved-send", ready_to_send["argv"])
        self.assertIn("--json", ready_to_send["argv"])
        self.assertFalse(ready_to_send["webhook_url_embedded"])
        self.assertFalse(ready_to_send["webhook_secret_embedded"])
        self.assertFalse(ready_to_send["secret_values_embedded"])
        self.assertEqual(
            ready_to_send["button_interaction_response_mode"],
            "ephemeral_ack_and_local_event_write",
        )
        self.assertTrue(ready_to_send["button_interactions_ephemeral_ack_only"])
        self.assertFalse(ready_to_send["button_interactions_create_channel_messages"])
        self.assertFalse(ready_to_send["button_interactions_create_followup_messages"])
        self.assertFalse(ready_to_send["button_events_claim_readiness"])
        self.assertFalse(ready_to_send["status_summary_creates_channel_message"])
        self.assertFalse(ready_to_send["status_summary_updates_operational_message"])
        self.assertFalse(ready_to_send["status_summary_claims_readiness"])
        self.assertFalse(ready_to_send["embed_claims_readiness"])
        update_policy = ready_to_send["active_notice_update_policy"]
        self.assertEqual(update_policy["expected_channel_id"], BETA_TEST_BOT_CHANNEL_ID)
        assert_single_updated_notice_boundary(self, update_policy)
        self.assertTrue(update_policy["bot_channel_required_for_real_send"])
        self.assertEqual(update_policy["existing_active_notice_http_method"], "PATCH")
        self.assertEqual(update_policy["missing_active_notice_http_method"], "POST")
        self.assertTrue(update_policy["new_message_only_when_active_notice_state_missing"])
        self.assertTrue(update_policy["repeat_everyone_mentions_suppressed_on_update"])
        self.assertTrue(update_policy["interactive_buttons_preserved_on_update"])
        self.assertEqual(update_policy["active_notice_state_env_var"], BETA_TEST_ACTIVE_NOTICE_STATE_ENV)
        self.assertEqual(update_policy["event_sink_env_var"], BETA_TEST_EVENT_SINK_ENV)
        self.assertEqual(update_policy["operational_message_workflow"], "single_active_bot_notice")
        self.assertTrue(update_policy["single_operational_message_required"])
        self.assertTrue(update_policy["active_notice_state_required_for_beta_controls"])
        self.assertTrue(update_policy["single_editable_notice_required"])
        self.assertTrue(update_policy["single_editable_embed_required"])
        self.assertTrue(update_policy["with_beta_controls_required"])
        self.assertTrue(update_policy["update_active_notice_required"])
        self.assertEqual(update_policy["status_summary_button_custom_id"], BETA_STATUS_SUMMARY_CUSTOM_ID)
        self.assertEqual(update_policy["status_summary_response_mode"], BETA_STATUS_SUMMARY_RESPONSE_MODE)
        self.assertTrue(update_policy["status_summary_button_required"])
        self.assertFalse(update_policy["status_summary_button_writes_event"])
        self.assertTrue(update_policy["status_summary_ephemeral_response_only"])
        self.assertTrue(update_policy["status_summary_uses_local_event_sink_only"])
        self.assertFalse(update_policy["status_summary_reads_discord"])
        self.assertFalse(update_policy["status_summary_sends_discord"])
        self.assertFalse(update_policy["status_summary_creates_channel_message"])
        self.assertFalse(update_policy["status_summary_updates_operational_message"])
        self.assertFalse(update_policy["status_summary_creates_event"])
        self.assertFalse(update_policy["status_summary_claims_evidence"])
        self.assertFalse(update_policy["status_summary_claims_progress"])
        self.assertFalse(update_policy["status_summary_claims_readiness"])
        self.assertFalse(update_policy["status_summary_counts_as_approved_runtime_evidence"])
        self.assertFalse(update_policy["status_summary_counts_toward_sdk"])
        self.assertFalse(update_policy["status_summary_counts_as_readiness"])
        self.assertEqual(
            update_policy["button_interaction_response_mode"],
            "ephemeral_ack_and_local_event_write",
        )
        self.assertTrue(update_policy["button_interactions_ephemeral_ack_only"])
        self.assertFalse(update_policy["button_interactions_create_channel_messages"])
        self.assertFalse(update_policy["button_interactions_create_followup_messages"])
        self.assertFalse(update_policy["button_events_claim_readiness"])
        self.assertFalse(update_policy["embed_claims_readiness"])
        self.assertTrue(update_policy["real_send_uses_bot_channel"])
        self.assertFalse(update_policy["real_send_uses_webhook"])
        self.assertFalse(update_policy["uses_webhook"])
        self.assertFalse(update_policy["old_webhook_path_allowed"])
        self.assertFalse(update_policy["webhook_real_send_allowed"])
        self.assertTrue(update_policy["webhook_fail_closed_for_real_sends"])
        send_path = report["bot_notice_send_path"]
        self.assertEqual(send_path["configured_send_path"], "discord_bot_channel")
        self.assertEqual(send_path["default_send_path"], "discord_bot_channel")
        self.assertEqual(send_path["required_helper_args"], list(BETA_NOTICE_REQUIRED_HELPER_ARGS))
        self.assertTrue(send_path["required_helper_args_present"])
        self.assertEqual(send_path["operational_message_workflow"], "single_active_bot_notice")
        assert_single_updated_notice_boundary(self, send_path)
        self.assertTrue(send_path["single_operational_message_required"])
        self.assertTrue(send_path["active_notice_state_required_for_beta_controls"])
        self.assertEqual(send_path["forbidden_webhook_args_present"], [])
        self.assertTrue(send_path["send_beta_notice_arg_present"])
        self.assertTrue(send_path["with_beta_controls_arg_present"])
        self.assertTrue(send_path["update_active_notice_arg_present"])
        self.assertTrue(send_path["single_editable_notice_required"])
        self.assertTrue(send_path["single_editable_embed_required"])
        self.assertFalse(send_path["button_interactions_create_channel_messages"])
        self.assertFalse(send_path["status_summary_creates_channel_message"])
        self.assertFalse(send_path["embed_claims_readiness"])
        self.assertFalse(send_path["uses_webhook"])
        self.assertFalse(send_path["real_send_uses_webhook"])
        self.assertFalse(send_path["webhook_real_send_allowed"])
        self.assertTrue(send_path["webhook_fail_closed_for_real_sends"])
        self.assertFalse(send_path["webhook_fallback_allowed"])
        self.assertFalse(send_path["counts_as_approved_runtime_evidence"])
        self.assertFalse(send_path["counts_toward_sdk"])
        self.assertFalse(send_path["counts_as_readiness"])
        status_workflow = ready_to_send["tester_status_workflow"]
        self.assertEqual(status_workflow["expected_channel_id"], BETA_TEST_BOT_CHANNEL_ID)
        self.assertEqual(status_workflow["schema"], BETA_TESTER_STATUS_WORKFLOW_SCHEMA)
        assert_single_updated_notice_boundary(self, status_workflow)
        self.assertEqual(
            status_workflow["tester_reportable_states"],
            ["started", "loading", "in_server", "logged_out", "cluster_transfer"],
        )
        self.assertIn("obelisk_beta:started", status_workflow["status_custom_ids"])
        self.assertIn("obelisk_beta:loading", status_workflow["status_custom_ids"])
        self.assertIn("obelisk_beta:in_server:Genesis2", status_workflow["status_custom_ids"])
        self.assertIn("obelisk_beta:logged_out", status_workflow["status_custom_ids"])
        self.assertIn("obelisk_beta:cluster_transfer", status_workflow["status_custom_ids"])
        self.assertEqual(status_workflow["status_summary_custom_id"], BETA_STATUS_SUMMARY_CUSTOM_ID)
        self.assertEqual(
            status_workflow["status_summary_action"]["custom_id"],
            BETA_STATUS_SUMMARY_CUSTOM_ID,
        )
        self.assertFalse(status_workflow["status_summary_button_writes_event"])
        self.assertEqual(status_workflow["status_summary_response_mode"], BETA_STATUS_SUMMARY_RESPONSE_MODE)
        self.assertTrue(status_workflow["status_summary_uses_local_event_sink_only"])
        self.assertFalse(status_workflow["status_summary_reads_discord"])
        self.assertFalse(status_workflow["status_summary_sends_discord"])
        self.assertFalse(status_workflow["status_summary_creates_channel_message"])
        self.assertFalse(status_workflow["status_summary_updates_operational_message"])
        self.assertFalse(status_workflow["status_summary_claims_readiness"])
        self.assertFalse(status_workflow["status_summary_counts_as_approved_runtime_evidence"])
        self.assertFalse(status_workflow["status_summary_counts_toward_sdk"])
        self.assertTrue(status_workflow["one_editable_notice"])
        self.assertTrue(status_workflow["single_operational_message_required"])
        self.assertTrue(status_workflow["active_notice_state_required_for_beta_controls"])
        self.assertEqual(
            status_workflow["button_interaction_response_mode"],
            "ephemeral_ack_and_local_event_write",
        )
        self.assertFalse(status_workflow["button_interactions_create_channel_messages"])
        self.assertFalse(status_workflow["button_events_claim_readiness"])
        self.assertTrue(status_workflow["repeat_everyone_mentions_suppressed_on_update"])
        self.assertFalse(status_workflow["cluster_transfer_button_authorizes_transfer"])
        self.assertFalse(status_workflow["counts_as_approved_runtime_evidence"])
        self.assertFalse(status_workflow["discord_send_authorized"])
        self.assertFalse(ready_to_send["send_performed_by_dry_run"])
        self.assertFalse(ready_to_send["discord_sent"])
        self.assertTrue(ready_to_send["lead_input_required_before_send"])
        self.assertTrue(ready_to_send["fresh_separate_notice_approval_required"])
        self.assertTrue(ready_to_send["send_next_action_requires_fresh_user_each_time"])
        self.assertFalse(ready_to_send["send_next_action_satisfied_by_recorded_standing_authority"])
        self.assertFalse(ready_to_send["runtime_window_should_not_wait_for_lead_notice_authorization"])
        self.assertEqual(ready_to_send["blocker"], DISCORD_SEND_SCOPE_BLOCKER)
        self.assertFalse(ready_to_send["counts_as_approved_runtime_evidence"])
        self.assertFalse(ready_to_send["counts_as_sdk_evidence"])
        self.assertFalse(ready_to_send["counts_toward_sdk"])
        self.assertFalse(ready_to_send["readiness_claim_allowed"])
        self.assertFalse(ready_to_send["progress_claim_allowed"])
        self.assertFalse(ready_to_send["preparation_counts_as_readiness"])
        self.assertFalse(ready_to_send["preparation_counts_as_progress"])
        self.assertFalse(ready_to_send["public_sdk_ready"])
        self.assertFalse(ready_to_send["runtime_ready"])
        self.assertTrue(ready_to_send["beta_runtime_choreography"]["single_tester_only"])
        self.assertFalse(
            ready_to_send["beta_runtime_choreography"][
                "mixed_transfer_reconnect_same_approved_window_allowed"
            ]
        )
        self.assertTrue(
            ready_to_send[
                "stale_or_diagnostic_exact_checkjoin_lines_are_stimulus_clues_only"
            ]
        )
        self.assertTrue(report["beta_runtime_choreography"]["single_tester_only"])
        self.assertTrue(report["beta_runtime_choreography"]["direct_target_join_required"])
        self.assertFalse(report["beta_runtime_choreography"]["logout_before_exact_checkjoin_allowed"])
        self.assertFalse(
            report["beta_runtime_choreography"][
                "mixed_transfer_reconnect_same_approved_window_allowed"
            ]
        )
        self.assertFalse(report["beta_runtime_choreography"]["counts_as_approved_runtime_evidence"])
        self.assertTrue(report["checkjoin_stimulus_boundary"]["stimulus_clue_for_future_choreography"])
        self.assertFalse(
            report["checkjoin_stimulus_boundary"][
                "diagnostic_tail_without_approved_sibling_set_is_promotable"
            ]
        )
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["discord_authorized"])
        self.assertFalse(report["counts_as_sdk_progress"])
        self.assertFalse(report["notice_action_counts_as_sdk_progress"])
        self.assertFalse(report["counts_toward_public_sdk"])
        self.assertFalse(report["counts_toward_runtime"])
        self.assertFalse(report["counts_toward_v1_completion"])
        self.assertFalse(report["counts_toward_sdk"])
        self.assertFalse(report["counts_toward_p0_dependency_chain"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["sdk_evidence_ready"])
        self.assertTrue(report["send_helper_returncode_zero"])
        self.assertFalse(report["notice_action_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["notice_action_counts_toward_sdk"])
        self.assertFalse(report["notice_action_counts_toward_p0_dependency_chain"])
        self.assertFalse(report["confirmed_send_authorizes_activation"])
        self.assertFalse(report["confirmed_send_authorizes_runtime_capture"])
        self.assertFalse(report["confirmed_send_authorizes_server_operations"])
        self.assertEqual(report["configured_send_path"], "discord_bot_channel")
        self.assertEqual(report["operational_message_workflow"], "single_active_bot_notice")
        assert_single_updated_notice_boundary(self, report)
        self.assertTrue(report["single_operational_message_required"])
        self.assertTrue(report["active_notice_state_required_for_beta_controls"])
        self.assertTrue(report["single_editable_notice_required"])
        self.assertTrue(report["single_editable_embed_required"])
        self.assertTrue(report["with_beta_controls_required"])
        self.assertTrue(report["update_active_notice_required"])
        self.assertFalse(report["button_interactions_create_channel_messages"])
        self.assertFalse(report["status_summary_creates_channel_message"])
        self.assertFalse(report["status_summary_claims_readiness"])
        self.assertFalse(report["embed_claims_readiness"])
        self.assertTrue(report["webhook_deprecated"])
        self.assertFalse(report["webhook_real_send_allowed"])
        self.assertTrue(report["webhook_fail_closed_for_real_sends"])
        self.assertFalse(report["webhook_fallback_allowed"])
        self.assertFalse(report["notice_action_covered_by_standing_launch_authority"])
        self.assertTrue(report["confirmed_send_requires_separate_explicit_discord_send_approval"])
        self.assertFalse(report["standing_authority_authorizes_discord_send"])
        guarded = report["guarded_beta_notice_action"]
        self.assertEqual(guarded["mode"], "dry_run")
        self.assertEqual(guarded["player_notice_action"], report["player_notice_action"])
        self.assertFalse(guarded["real_beta_test_notice_action_completed"])
        self.assertFalse(guarded["send_performed_by_request_pack"])
        self.assertFalse(guarded["guarded_helper_invocation"])
        self.assertFalse(guarded["confirm_approved_send_arg_used"])
        self.assertFalse(guarded["approval_scope_arg_used"])
        self.assertEqual(guarded["approval_scope"], "dry_run_only")
        self.assertEqual(guarded["configured_send_path"], "discord_bot_channel")
        self.assertEqual(guarded["operational_message_workflow"], "single_active_bot_notice")
        assert_single_updated_notice_boundary(self, guarded)
        self.assertTrue(guarded["single_operational_message_required"])
        self.assertTrue(guarded["active_notice_state_required_for_beta_controls"])
        self.assertTrue(guarded["send_beta_notice_arg_used"])
        self.assertTrue(guarded["with_beta_controls_arg_used"])
        self.assertTrue(guarded["update_active_notice_arg_used"])
        self.assertTrue(guarded["single_editable_notice_required"])
        self.assertTrue(guarded["single_editable_embed_required"])
        self.assertFalse(guarded["button_interactions_create_channel_messages"])
        self.assertFalse(guarded["status_summary_creates_channel_message"])
        self.assertFalse(guarded["status_summary_claims_readiness"])
        self.assertFalse(guarded["embed_claims_readiness"])
        self.assertFalse(guarded["uses_webhook"])
        self.assertTrue(guarded["webhook_deprecated"])
        self.assertFalse(guarded["webhook_real_send_allowed"])
        self.assertTrue(guarded["webhook_fail_closed_for_real_sends"])
        self.assertFalse(guarded["discord_authorized"])
        self.assertFalse(guarded["discord_send_authorized"])
        self.assertFalse(guarded["current_turn_approval_recorded"])
        self.assertFalse(guarded["current_turn_scope_authorized"])
        self.assertFalse(guarded["runtime_capture_authorized"])
        self.assertFalse(guarded["server_operations_authorized"])
        self.assertTrue(guarded["beta_runtime_choreography"]["single_tester_only"])
        self.assertFalse(
            guarded["beta_runtime_choreography"][
                "mixed_transfer_reconnect_same_approved_window_allowed"
            ]
        )
        self.assertEqual(
            [item["id"] for item in report["next_action_sequence"]],
            [
                "review_beta_notice_dry_run",
                "send_guarded_beta_notice_after_fresh_authorization",
            ],
        )
        self.assertTrue(report["next_action_sequence"][0]["fresh_separate_notice_approval_required"])
        assert_single_updated_notice_boundary(self, report["next_action_sequence"][0])
        self.assertFalse(report["next_action_sequence"][0]["discord_send_performed_by_this_action"])
        self.assertFalse(report["next_action_sequence"][0]["ark_touched_by_this_action"])
        self.assertFalse(report["next_action_sequence"][0]["counts_as_approved_runtime_evidence"])
        self.assertEqual(
            report["next_action_sequence"][0]["tester_status_workflow"]["schema"],
            BETA_TESTER_STATUS_WORKFLOW_SCHEMA,
        )
        self.assertTrue(report["next_action_sequence"][0]["beta_runtime_choreography"]["single_tester_only"])
        self.assertFalse(report["next_action_sequence"][1]["default_invocation"])
        self.assertTrue(report["next_action_sequence"][1]["explicit_confirm_approved_send_invocation_required"])
        self.assertTrue(report["next_action_sequence"][1]["fresh_separate_notice_approval_required"])
        self.assertEqual(report["next_action_sequence"][1]["bot_channel_id"], BETA_TEST_BOT_CHANNEL_ID)
        self.assertEqual(report["next_action_sequence"][1]["bot_env_vars"], BETA_TEST_BOT_ENV_VARS)
        self.assertEqual(report["next_action_sequence"][1]["webhook_env_var"], BETA_TEST_WEBHOOK_ENV)
        self.assertTrue(report["next_action_sequence"][1]["webhook_deprecated"])
        self.assertFalse(report["next_action_sequence"][1]["webhook_real_send_allowed"])
        self.assertTrue(report["next_action_sequence"][1]["webhook_fail_closed_for_real_sends"])
        self.assertFalse(report["next_action_sequence"][1]["webhook_fallback_allowed"])
        self.assertEqual(report["next_action_sequence"][1]["required_env_vars"], BETA_TEST_BOT_ENV_VARS)
        self.assertTrue(report["next_action_sequence"][1]["mentions_everyone"])
        self.assertEqual(report["next_action_sequence"][1]["content"], "@everyone")
        self.assertFalse(report["next_action_sequence"][1]["webhook_url_embedded"])
        self.assertFalse(report["next_action_sequence"][1]["secret_values_embedded"])
        self.assertEqual(report["next_action_sequence"][1]["configured_send_path"], "discord_bot_channel")
        self.assertEqual(
            report["next_action_sequence"][1]["operational_message_workflow"],
            "single_active_bot_notice",
        )
        assert_single_updated_notice_boundary(self, report["next_action_sequence"][1])
        self.assertTrue(report["next_action_sequence"][1]["single_operational_message_required"])
        self.assertTrue(
            report["next_action_sequence"][1]["active_notice_state_required_for_beta_controls"]
        )
        self.assertTrue(report["next_action_sequence"][1]["single_editable_notice_required"])
        self.assertTrue(report["next_action_sequence"][1]["single_editable_embed_required"])
        self.assertTrue(report["next_action_sequence"][1]["with_beta_controls_required"])
        self.assertTrue(report["next_action_sequence"][1]["update_active_notice_required"])
        self.assertFalse(report["next_action_sequence"][1]["button_interactions_create_channel_messages"])
        self.assertFalse(report["next_action_sequence"][1]["button_events_claim_readiness"])
        self.assertFalse(report["next_action_sequence"][1]["status_summary_creates_channel_message"])
        self.assertFalse(report["next_action_sequence"][1]["status_summary_claims_readiness"])
        self.assertFalse(report["next_action_sequence"][1]["embed_claims_readiness"])
        self.assertFalse(report["next_action_sequence"][1]["send_next_action_satisfied_by_recorded_standing_authority"])
        self.assertFalse(report["next_action_sequence"][1]["standing_authority_authorizes_discord_send"])
        self.assertEqual(report["next_action_sequence"][1]["blocker"], DISCORD_SEND_SCOPE_BLOCKER)
        self.assertTrue(
            report["next_action_sequence"][1]["beta_runtime_choreography"][
                "observer_gate"
            ]["wait_until_observer_sees_exact_checkjoin_or_window_closes"]
        )
        self.assertEqual(report["dry_run_payload"]["schema"], "obelisk.discord-beta-bridge-bot-notice.v1")
        self.assertEqual(report["dry_run_payload"]["channel_id"], BETA_TEST_BOT_CHANNEL_ID)
        assert_single_updated_notice_boundary(self, report["dry_run_payload"])
        assert_discord_beta_non_promotion(
            self,
            report["dry_run_payload"]["dry_run_receipt_inputs"]["discord_beta_non_promotion"],
        )
        self.assertFalse(report["dry_run_payload"]["uses_webhook"])
        self.assertEqual(report["dry_run_payload"]["discord_http_method"], "POST")
        self.assertEqual(report["dry_run_payload"]["discord_endpoint_kind"], "channel_message_create")
        self.assertTrue(report["dry_run_payload"]["would_create_new_message"])
        self.assertFalse(report["dry_run_payload"]["active_notice_state_present"])
        self.assertTrue(report["dry_run_payload"]["single_operational_message_required"])
        self.assertEqual(
            report["dry_run_payload"]["operational_message_kind"],
            "single_active_beta_notice",
        )
        self.assertTrue(report["dry_run_payload"]["active_notice_update_requested"])
        self.assertTrue(report["dry_run_payload"]["active_notice_state_required_for_beta_controls"])
        self.assertTrue(report["dry_run_payload"]["new_message_only_when_active_notice_state_missing"])
        self.assertFalse(report["dry_run_payload"]["button_interactions_create_channel_messages"])
        self.assertFalse(report["dry_run_payload"]["button_events_claim_readiness"])
        self.assertFalse(report["dry_run_payload"]["status_summary_creates_channel_message"])
        self.assertFalse(report["dry_run_payload"]["status_summary_claims_readiness"])
        self.assertFalse(report["dry_run_payload"]["embed_claims_readiness"])
        self.assertTrue(report["dry_run_payload"]["content_mentions_everyone"])
        self.assertEqual(report["tester_status_workflow"]["schema"], BETA_TESTER_STATUS_WORKFLOW_SCHEMA)
        self.assertTrue(report["tester_status_workflow"]["one_editable_notice"])
        self.assertFalse(report["tester_status_workflow"]["counts_toward_sdk"])
        rendered = json.dumps(report["dry_run_payload"])
        self.assertIn("Genesis2", rendered)
        self.assertIn("Estado: sendable_current_window", report["dry_run_payload"]["content"])
        self.assertIn("Started, Loading, In-server", report["dry_run_payload"]["content"])
        self.assertIn("Status summary", report["dry_run_payload"]["content"])
        self.assertIn("obelisk_beta:started", report["dry_run_payload"]["component_custom_ids"])
        self.assertIn("obelisk_beta:loading", report["dry_run_payload"]["component_custom_ids"])
        self.assertIn("obelisk_beta:in_server:Genesis2", report["dry_run_payload"]["component_custom_ids"])
        self.assertIn("obelisk_beta:logged_out", report["dry_run_payload"]["component_custom_ids"])
        self.assertIn("obelisk_beta:cluster_transfer", report["dry_run_payload"]["component_custom_ids"])
        self.assertIn("obelisk_beta:status_summary", report["dry_run_payload"]["component_custom_ids"])
        self.assertEqual(
            report["dry_run_payload"]["tester_status_workflow"]["schema"],
            "obelisk.discord-beta-bridge-tester-status-workflow.v1",
        )
        self.assertEqual(
            report["dry_run_payload"]["tester_status_workflow"]["status_summary_button_custom_id"],
            BETA_STATUS_SUMMARY_CUSTOM_ID,
        )
        self.assertFalse(
            report["dry_run_payload"]["tester_status_workflow"]["status_summary_button_writes_event"]
        )
        self.assertFalse(
            report["dry_run_payload"]["tester_status_workflow"]["status_summary_creates_channel_message"]
        )
        self.assertFalse(
            report["dry_run_payload"]["tester_status_workflow"]["status_summary_claims_readiness"]
        )
        self.assertFalse(report["dry_run_payload"]["tester_status_workflow"]["counts_as_runtime_evidence"])
        self.assertTrue(
            report["dry_run_payload"]["editable_notice_workflow"][
                "new_message_only_when_active_notice_state_missing"
            ]
        )
        self.assertIn("obelisk_beta:logout_ready", report["dry_run_payload"]["component_custom_ids"])
        self.assertNotIn("discord.com/" + "api/webhooks", rendered)
        self.assertNotIn("player text", rendered.lower())
        self.assertIn("notice preparation only", report["non_authorization"])
        self.assertIn("notice-action metadata only", report["non_authorization"])

    def test_dry_run_uses_recorded_standing_authority_for_preparation_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(
                Path(tmp) / "window-request.json",
                request_payload(standing_authority=True),
            )
            result = self.run_script(request_json, "--dry-run")
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report["ready"])
        self.assertTrue(report["standing_launch_authority_recorded"])
        self.assertFalse(report["standing_launch_authority_satisfies_notice_scope"])
        self.assertTrue(report["standing_launch_authority_satisfies_dry_run_notice_preparation_scope"])
        self.assertTrue(report["standing_authority_satisfies_guarded_beta_notice_send_scope"])
        self.assertTrue(report["guarded_beta_notice_send_scope_satisfied_by_standing_authority"])
        self.assertTrue(report["guarded_discord_send_scope_satisfied"])
        self.assertTrue(report["standing_authority_authorizes_discord_send"])
        self.assertFalse(report["discord_authorized"])
        self.assertFalse(report["counts_as_sdk_progress"])
        self.assertFalse(report["standing_authority_authorizes_marker_env_changes"])
        self.assertFalse(report["standing_authority_authorizes_server_restart"])
        self.assertFalse(
            report["standing_authority_non_progress_boundary"][
                "standing_authority_grants_runtime_readiness"
            ]
        )
        self.assertFalse(
            report["standing_authority_non_progress_boundary"][
                "authorization_for_scoped_operator_actions_only"
            ]
        )
        self.assertTrue(
            report["standing_authority_non_progress_boundary"][
                "recorded_standing_authority_applies_to_scoped_operator_actions_only"
            ]
        )
        self.assertFalse(
            report["standing_authority_non_progress_boundary"][
                "standing_authority_counts_as_sdk_progress"
            ]
        )
        self.assertTrue(report["request_window_sendable"])
        self.assertFalse(report["stale_request_window"])
        self.assertFalse(report["send_blocked_by_stale_window"])
        self.assertFalse(report["default_sends_discord"])
        self.assertFalse(report["default_touches_ark"])
        self.assertFalse(report["dry_run_sends_discord"])
        self.assertFalse(report["dry_run_touches_ark"])
        self.assertFalse(
            report["notice_authority_boundary"][
                "fresh_current_turn_operator_authorization_required_before_confirmed_send"
            ]
        )
        self.assertFalse(
            report["notice_authority_boundary"]["separate_operator_authorization_required_before_confirmed_send"]
        )
        self.assertFalse(report["notice_authority_boundary"]["fresh_separate_notice_approval_required"])
        self.assertTrue(
            report["notice_authority_boundary"][
                "standing_launch_authority_satisfies_dry_run_notice_preparation_scope"
            ]
        )
        self.assertTrue(
            report["notice_authority_boundary"][
                "standing_launch_authority_satisfies_confirmed_discord_send_scope"
            ]
        )
        self.assertTrue(report["notice_authority_boundary"]["standing_authority_authorizes_discord_send"])
        self.assertTrue(
            report["notice_authority_boundary"][
                "standing_authority_satisfies_guarded_beta_notice_send_scope"
            ]
        )
        self.assertFalse(report["notice_authority_boundary"]["discord_authorized"])
        self.assertFalse(report["notice_authority_boundary"]["counts_as_sdk_progress"])
        self.assertFalse(report["notice_authority_boundary"]["default_sends_discord"])
        self.assertFalse(report["notice_authority_boundary"]["default_touches_ark"])
        dry_run_boundary = report["dry_run_consumption_boundary"]
        self.assertTrue(dry_run_boundary["dry_run_output_consumable_under_recorded_standing_launch_authority"])
        self.assertFalse(dry_run_boundary["fresh_separate_notice_approval_required"])
        self.assertTrue(dry_run_boundary["standing_authority_authorizes_discord_send"])
        self.assertTrue(
            dry_run_boundary["standing_authority_satisfies_guarded_beta_notice_send_scope"]
        )
        self.assertFalse(dry_run_boundary["discord_authorized"])
        self.assertFalse(dry_run_boundary["counts_as_sdk_progress"])
        self.assertTrue(dry_run_boundary["dry_run_output_is_notice_metadata_only"])
        self.assertFalse(dry_run_boundary["default_sends_discord"])
        self.assertFalse(dry_run_boundary["default_touches_ark"])
        self.assertFalse(dry_run_boundary["dry_run_sends_discord"])
        self.assertFalse(dry_run_boundary["dry_run_touches_ark"])
        self.assertFalse(dry_run_boundary["dry_run_counts_as_approved_runtime_evidence"])
        self.assertFalse(dry_run_boundary["dry_run_counts_toward_sdk"])
        ready_to_send = report["dry_run_ready_to_send"]
        self.assertTrue(ready_to_send["ready_to_send"])
        self.assertTrue(ready_to_send["ready_to_send_via_discord_bot_channel"])
        self.assertFalse(ready_to_send["ready_to_send_via_obelisk_beta_test_webhook_url"])
        self.assertTrue(ready_to_send["request_window_sendable"])
        self.assertFalse(ready_to_send["stale_request_window"])
        self.assertFalse(ready_to_send["send_blocked_by_stale_window"])
        self.assertEqual(ready_to_send["bot_channel_id"], BETA_TEST_BOT_CHANNEL_ID)
        self.assertEqual(ready_to_send["bot_env_vars"], BETA_TEST_BOT_ENV_VARS)
        self.assertEqual(ready_to_send["webhook_env_var"], BETA_TEST_WEBHOOK_ENV)
        self.assertTrue(ready_to_send["webhook_deprecated"])
        self.assertEqual(ready_to_send["required_env_vars"], BETA_TEST_BOT_ENV_VARS)
        self.assertTrue(ready_to_send["mentions_everyone"])
        self.assertEqual(ready_to_send["content"], "@everyone")
        self.assertFalse(ready_to_send["webhook_url_embedded"])
        self.assertFalse(ready_to_send["secret_values_embedded"])
        self.assertTrue(ready_to_send["standing_launch_authority_recorded"])
        self.assertTrue(ready_to_send["standing_debug_authority_recorded"])
        self.assertFalse(ready_to_send["recorded_standing_debug_authority_satisfies_notice_scope"])
        self.assertTrue(ready_to_send["recorded_standing_debug_authority_satisfies_dry_run_notice_preparation_scope"])
        self.assertTrue(ready_to_send["send_next_action_satisfied_by_recorded_standing_authority"])
        self.assertTrue(ready_to_send["standing_authority_authorizes_discord_send"])
        self.assertTrue(ready_to_send["standing_authority_satisfies_guarded_beta_notice_send_scope"])
        self.assertTrue(ready_to_send["guarded_beta_notice_send_scope_satisfied_by_standing_authority"])
        self.assertFalse(ready_to_send["discord_authorized"])
        self.assertFalse(ready_to_send["counts_as_sdk_progress"])
        self.assertFalse(ready_to_send["lead_input_required_before_send"])
        self.assertFalse(ready_to_send["fresh_separate_notice_approval_required"])
        self.assertFalse(ready_to_send["send_next_action_requires_fresh_user_each_time"])
        self.assertTrue(ready_to_send["runtime_window_should_not_wait_for_lead_notice_authorization"])
        self.assertEqual(ready_to_send["blocker"], "none")
        self.assertFalse(ready_to_send["runtime_or_server_scope_satisfied_by_notice"])
        self.assertFalse(ready_to_send["discord_send_authorized"])
        self.assertFalse(ready_to_send["server_operations_authorized"])
        self.assertFalse(ready_to_send["counts_as_approved_runtime_evidence"])
        self.assertFalse(ready_to_send["counts_toward_sdk"])
        self.assertFalse(report["discord_sent"])
        self.assertFalse(report["discord_send_authorized"])
        self.assertEqual(
            [item["id"] for item in report["next_action_sequence"]],
            [
                "review_beta_notice_dry_run",
                "send_guarded_beta_notice_after_fresh_authorization",
            ],
        )
        self.assertFalse(report["next_action_sequence"][1]["separate_operator_authorization_required"])
        self.assertFalse(report["next_action_sequence"][0]["fresh_separate_notice_approval_required"])
        self.assertTrue(
            report["next_action_sequence"][0][
                "dry_run_output_consumable_under_recorded_standing_launch_authority"
            ]
        )
        self.assertFalse(report["next_action_sequence"][0]["discord_send_performed_by_this_action"])
        self.assertFalse(report["next_action_sequence"][0]["ark_touched_by_this_action"])
        self.assertFalse(report["next_action_sequence"][0]["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["next_action_sequence"][0]["counts_toward_sdk"])
        self.assertFalse(report["next_action_sequence"][1]["fresh_separate_notice_approval_required"])
        self.assertFalse(report["next_action_sequence"][1]["default_invocation"])
        self.assertTrue(report["next_action_sequence"][1]["explicit_confirm_approved_send_invocation_required"])
        self.assertEqual(report["next_action_sequence"][1]["bot_channel_id"], BETA_TEST_BOT_CHANNEL_ID)
        self.assertEqual(report["next_action_sequence"][1]["webhook_env_var"], BETA_TEST_WEBHOOK_ENV)
        self.assertTrue(report["next_action_sequence"][1]["mentions_everyone"])
        self.assertEqual(report["next_action_sequence"][1]["content"], "@everyone")
        self.assertTrue(report["next_action_sequence"][1]["ready_to_send_via_discord_bot_channel"])
        self.assertEqual(report["next_action_sequence"][1]["expected_channel_id"], BETA_TEST_BOT_CHANNEL_ID)
        self.assertFalse(report["next_action_sequence"][1]["ready_to_send_via_obelisk_beta_test_webhook_url"])
        self.assertFalse(report["next_action_sequence"][1]["lead_input_required_before_send"])
        self.assertTrue(report["next_action_sequence"][1]["send_next_action_satisfied_by_recorded_standing_authority"])
        self.assertTrue(
            report["next_action_sequence"][1][
                "standing_authority_satisfies_guarded_beta_notice_send_scope"
            ]
        )
        self.assertTrue(report["next_action_sequence"][1]["standing_authority_authorizes_discord_send"])
        self.assertFalse(report["next_action_sequence"][1]["discord_authorized"])
        self.assertFalse(report["next_action_sequence"][1]["counts_as_sdk_progress"])
        self.assertTrue(report["next_action_sequence"][1]["runtime_window_should_not_wait_for_lead_notice_authorization"])
        self.assertEqual(report["next_action_sequence"][1]["blocker"], "none")
        self.assertFalse(report["next_action_sequence"][1]["discord_send_performed_by_dry_run"])
        self.assertFalse(report["next_action_sequence"][1]["ark_touched_by_this_action"])
        self.assertFalse(report["next_action_sequence"][1]["counts_as_approved_runtime_evidence"])
        self.assertIn("--confirm-approved-send", report["next_action_sequence"][1]["argv"])

    def test_dry_run_does_not_embed_beta_webhook_secret_from_environment(self) -> None:
        secret = "https://discord.com/api/webhooks/123/SECRET"
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json")
            result = self.run_script(
                request_json,
                "--dry-run",
                env={BETA_TEST_WEBHOOK_ENV: secret},
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(BETA_TEST_WEBHOOK_ENV, result.stdout)
        self.assertNotIn(secret, result.stdout)
        self.assertNotIn("discord.com/api/webhooks/123", result.stdout)
        self.assertFalse(report["dry_run_ready_to_send"]["webhook_url_embedded"])
        self.assertFalse(report["dry_run_ready_to_send"]["secret_values_embedded"])
        self.assertEqual(report["dry_run_ready_to_send"]["webhook_env_var"], BETA_TEST_WEBHOOK_ENV)

    def test_rejects_secret_material_in_dry_run_helper_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            request_json = write_request(tmp_path / "window-request.json")
            fake_helper = tmp_path / "fake_send_helper.py"
            fake_helper.write_text(
                "print('{\"url\": \"https://discord.com/api/webhooks/123/SECRET\"}')\n",
                encoding="utf-8",
            )
            result = self.run_script(
                request_json,
                "--send-helper",
                str(fake_helper),
                "--dry-run",
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("refusing helper dry-run stdout containing webhook or secret material", result.stderr)
        self.assertNotIn("SECRET", result.stderr)

    def test_default_mode_is_dry_run_and_does_not_confirm_send(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            request_json = write_request(tmp_path / "window-request.json")
            called = tmp_path / "called.json"
            fake_helper = tmp_path / "fake_send_helper.py"
            fake_helper.write_text(
                "import json, sys\n"
                f"open({str(called)!r}, 'w', encoding='utf-8').write(json.dumps(sys.argv[1:]))\n"
                "print(json.dumps({'embeds': [{'title': 'dry run'}]}))\n",
                encoding="utf-8",
            )
            result = self.run_script(request_json, "--send-helper", str(fake_helper))
            report = json.loads(result.stdout)
            helper_args = json.loads(called.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["mode"], "dry_run")
        self.assertFalse(report["discord_sent"])
        self.assertFalse(report["discord_send_authorized"])
        self.assertFalse(report["default_sends_discord"])
        self.assertFalse(report["default_touches_ark"])
        self.assertIn("--dry-run", helper_args)
        self.assertIn("--send-beta-notice", helper_args)
        self.assertIn("--with-beta-controls", helper_args)
        self.assertIn("--update-active-notice", helper_args)
        self.assertNotIn("--confirm-approved-send", helper_args)
        self.assertNotIn("--dry-run-receipt", helper_args)
        self.assertNotIn("--webhook-url", helper_args)
        self.assertNotIn("--webhook-env", helper_args)
        self.assertNotIn("--use-webhook", helper_args)
        self.assertNotIn("--approval-scope", helper_args)
        self.assertLess(helper_args.index("--with-beta-controls"), helper_args.index("--content"))
        self.assertLess(helper_args.index("--update-active-notice"), helper_args.index("--content"))
        self.assertIn("@everyone", helper_args[helper_args.index("--content") + 1])

    def test_dry_run_existing_active_notice_updates_without_ping_or_new_message(self) -> None:
        token = "unit-test-active-notice-token"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            request_json = write_request(tmp_path / "window-request.json")
            active_state = tmp_path / "active-notice.json"
            active_state.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.discord-beta-bridge-active-notice.v1",
                        "guild_id": "1032660680668622969",
                        "channel_id": BETA_TEST_BOT_CHANNEL_ID,
                        "message_id": "777",
                        "source": "unit-test",
                        "updated_at_utc": "2026-06-07T00:00:00Z",
                        "redacted_metadata_only": True,
                        "communication_posture_only": True,
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            result = self.run_script(
                request_json,
                "--dry-run",
                env={
                    "OBELISK_DISCORD_BOT_TOKEN": token,
                    "OBELISK_DISCORD_GUILD_ID": "1032660680668622969",
                    "OBELISK_DISCORD_BETA_CHANNEL_ID": BETA_TEST_BOT_CHANNEL_ID,
                    BETA_TEST_ACTIVE_NOTICE_STATE_ENV: str(active_state),
                },
            )
            report = json.loads(result.stdout)
            payload = report["dry_run_payload"]

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(token, result.stdout)
        self.assertNotIn(token, result.stderr)
        self.assertTrue(report["ready"])
        self.assertTrue(payload["updates_existing_message"])
        assert_single_updated_notice_boundary(self, payload)
        assert_discord_beta_non_promotion(
            self,
            payload["dry_run_receipt_inputs"]["discord_beta_non_promotion"],
        )
        self.assertFalse(payload["creates_new_message"])
        self.assertFalse(payload["would_create_new_message"])
        self.assertEqual(payload["active_message_id"], "777")
        self.assertTrue(payload["single_operational_message_required"])
        self.assertEqual(payload["operational_message_kind"], "single_active_beta_notice")
        self.assertTrue(payload["active_notice_state_required_for_beta_controls"])
        self.assertFalse(payload["operational_message_policy"]["would_create_new_message"])
        self.assertTrue(payload["operational_message_policy"]["updates_existing_message"])
        self.assertEqual(payload["discord_http_method"], "PATCH")
        self.assertEqual(payload["discord_endpoint_kind"], "channel_message_update")
        self.assertEqual(payload["allowed_mentions_parse"], [])
        self.assertTrue(payload["requested_content_mentions_everyone"])
        self.assertFalse(payload["content_mentions_everyone"])
        self.assertTrue(payload["mention_everyone_suppressed_on_update"])
        self.assertNotIn("@everyone", payload["content"])
        self.assertTrue(payload["interactive_buttons_preserved_on_update"])
        self.assertFalse(payload["button_interactions_create_channel_messages"])
        self.assertFalse(payload["status_summary_creates_channel_message"])
        self.assertFalse(payload["status_summary_claims_readiness"])
        self.assertFalse(payload["embed_claims_readiness"])
        self.assertTrue(payload["editable_notice_workflow"]["updates_existing_message"])
        self.assertFalse(payload["editable_notice_workflow"]["would_create_new_message"])
        self.assertIn("obelisk_beta:cluster_transfer", payload["tester_status_workflow"]["status_custom_ids"])
        self.assertEqual(
            payload["tester_status_workflow"]["status_summary_button_custom_id"],
            BETA_STATUS_SUMMARY_CUSTOM_ID,
        )
        self.assertFalse(payload["tester_status_workflow"]["status_summary_button_writes_event"])
        self.assertFalse(payload["tester_status_workflow"]["counts_as_approved_runtime_evidence"])
        self.assertIn("obelisk_beta:logout_ready", payload["component_custom_ids"])
        self.assertIn("obelisk_beta:status_summary", payload["component_custom_ids"])
        self.assertFalse(payload["uses_webhook"])
        self.assertFalse(report["active_notice_update_policy"]["old_webhook_path_allowed"])

    def test_no_send_mode_persists_artifact_without_invoking_helper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            request_json = write_request(tmp_path / "window-request.json")
            called = tmp_path / "called.json"
            fake_helper = tmp_path / "fake_send_helper.py"
            fake_helper.write_text(
                "import pathlib\n"
                f"pathlib.Path({str(called)!r}).write_text('called', encoding='utf-8')\n",
                encoding="utf-8",
            )
            result = self.run_script(request_json, "--send-helper", str(fake_helper), "--no-send")
            report = json.loads(result.stdout)
            called_exists = called.exists()
            sidecar = json.loads(
                default_notice_sidecar(request_json, "no_send").read_text(encoding="utf-8")
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(called_exists)
        self.assertFalse(report["ready"])
        self.assertEqual(report["mode"], "no_send")
        self.assertFalse(report["helper_invoked"])
        self.assertEqual(report["helper_args"], [])
        self.assertFalse(report["discord_sent"])
        self.assertEqual(report["next_blocker"], "no_send_mode_notice_not_attempted")
        self.assertEqual(report["next_action_sequence"][0]["id"], "notice_no_send_mode_recorded")
        self.assertEqual(sidecar["schema"], NOTICE_ACTION_ARTIFACT_SCHEMA)
        self.assertEqual(sidecar["mode"], "no_send")
        self.assertEqual(sidecar["notice_report"], report)
        self.assertFalse(sidecar["stdout_only_confirmation_accepted"])
        for key, expected in SIDECAR_NON_EVIDENCE_FLAGS.items():
            with self.subTest(sidecar_flag=key):
                self.assertIs(sidecar[key], expected)

    def test_stale_request_window_dry_run_is_non_sendable_and_does_not_invoke_helper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            request_json = write_request(
                tmp_path / "window-request.json",
                request_payload(
                    standing_authority=True,
                    run_id="20260606T203359Z-player-principal-lifecycle",
                    start_utc="2026-06-06T20:33:59Z",
                    end_utc="2026-06-06T20:48:59Z",
                ),
            )
            called = tmp_path / "called.json"
            fake_helper = tmp_path / "fake_send_helper.py"
            fake_helper.write_text(
                "import json, sys\n"
                f"open({str(called)!r}, 'w', encoding='utf-8').write(json.dumps(sys.argv[1:]))\n"
                "print(json.dumps({'embeds': [{'title': 'stale dry run'}], 'content': '@everyone'}))\n",
                encoding="utf-8",
            )
            result = self.run_script(request_json, "--send-helper", str(fake_helper), "--dry-run")
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(called.exists())
        self.assertFalse(report["ready"])
        self.assertEqual(report["mode"], "dry_run")
        self.assertFalse(report["helper_invoked"])
        self.assertEqual(report["helper_args"], [])
        self.assertIsNone(report["dry_run_payload"])
        self.assertFalse(report["request_window_sendable"])
        self.assertFalse(report["current_request_window"])
        self.assertTrue(report["stale_request_window"])
        self.assertTrue(report["send_blocked_by_stale_window"])
        self.assertEqual(report["request_window_blocker"], STALE_WINDOW_BLOCKER)
        self.assertEqual(report["next_blocker"], STALE_WINDOW_BLOCKER)
        sendability = report["request_window_sendability"]
        self.assertEqual(sendability["status"], "stale_request_window")
        self.assertEqual(sendability["blocker"], STALE_WINDOW_BLOCKER)
        self.assertFalse(sendability["confirmed_send_allowed_by_request_window"])
        self.assertFalse(sendability["helper_invocation_allowed_by_request_window"])
        self.assertTrue(sendability["request_window_must_be_regenerated"])
        ready_to_send = report["dry_run_ready_to_send"]
        self.assertFalse(ready_to_send["ready_to_send"])
        self.assertFalse(ready_to_send["ready_to_send_via_obelisk_beta_test_webhook_url"])
        self.assertFalse(ready_to_send["mentions_everyone"])
        self.assertIsNone(ready_to_send["content"])
        self.assertEqual(ready_to_send["blocker"], STALE_WINDOW_BLOCKER)
        self.assertIn("scripts/plan_player_principal_lifecycle_runtime_window.py", ready_to_send["argv"])
        self.assertNotIn("--confirm-approved-send", ready_to_send["argv"])
        workflow = report["current_window_workflow"]
        self.assertEqual(workflow["status"], "fresh_current_window_required")
        self.assertTrue(workflow["current_window_request_must_be_regenerated"])
        self.assertFalse(workflow["plan_writes_files"])
        self.assertFalse(workflow["plan_touches_ark"])
        self.assertFalse(workflow["plan_sends_discord"])
        self.assertFalse(workflow["plan_authorizes_runtime"])
        self.assertIn(
            "scripts/plan_player_principal_lifecycle_runtime_window.py",
            workflow["next_fresh_window_plan_argv"],
        )
        self.assertIn("--instance arkserver3", workflow["next_fresh_window_plan_shell"])
        self.assertIn("--map Genesis2", workflow["next_fresh_window_plan_shell"])
        self.assertEqual(
            [item["id"] for item in report["next_action_sequence"]],
            ["prepare_fresh_current_window_request"],
        )
        self.assertFalse(report["discord_sent"])
        self.assertFalse(report["discord_send_authorized"])
        self.assertFalse(report["confirmed_send_authorizes_activation"])
        self.assertFalse(report["notice_action_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["counts_toward_sdk"])

    def test_stale_active_notice_overclaim_requires_fresh_window_and_state_repair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            request_json = write_request(
                tmp_path / "window-request.json",
                request_payload(
                    standing_authority=True,
                    run_id="20260606T203359Z-player-principal-lifecycle",
                    start_utc="2026-06-06T20:33:59Z",
                    end_utc="2026-06-06T20:48:59Z",
                ),
            )
            active_state = tmp_path / "active-notice.json"
            active_state.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.discord-beta-bridge-active-notice.v1",
                        "guild_id": "1032660680668622969",
                        "channel_id": BETA_TEST_BOT_CHANNEL_ID,
                        "message_id": "777",
                        "source": "unit-test",
                        "updated_at_utc": "2026-06-07T00:00:00Z",
                        "redacted_metadata_only": True,
                        "communication_posture_only": True,
                        "counts_as_readiness": True,
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            called = tmp_path / "called.json"
            fake_helper = tmp_path / "fake_send_helper.py"
            fake_helper.write_text(
                "import pathlib\n"
                f"pathlib.Path({str(called)!r}).write_text('called', encoding='utf-8')\n",
                encoding="utf-8",
            )
            result = self.run_script(
                request_json,
                "--send-helper",
                str(fake_helper),
                "--dry-run",
                env={BETA_TEST_ACTIVE_NOTICE_STATE_ENV: str(active_state)},
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(called.exists())
        self.assertFalse(report["ready"])
        decision = report["active_notice_window_decision"]
        self.assertEqual(
            decision["decision"],
            "create_fresh_window_repair_active_notice_state_before_notice",
        )
        self.assertTrue(decision["fresh_window_required"])
        self.assertTrue(decision["fresh_window_required_after_stale_request"])
        self.assertFalse(decision["wait_allowed_for_current_window_notice_scope"])
        self.assertFalse(decision["wait_without_fresh_window_allowed"])
        self.assertFalse(decision["active_notice_can_be_reused_only_after_fresh_window_notice"])
        self.assertFalse(decision["reuse_existing_active_notice_message_only"])
        active_summary = decision["active_notice_state"]
        self.assertTrue(active_summary["present"])
        self.assertFalse(active_summary["valid"])
        self.assertFalse(active_summary["metadata_only"])
        self.assertIn(
            "forbidden_notice_request_claim:$.active_notice_state.counts_as_readiness",
            active_summary["metadata_blockers"],
        )
        self.assertEqual(report["request_window_blocker"], STALE_WINDOW_BLOCKER)
        self.assertFalse(report["helper_invoked"])
        self.assertFalse(report["discord_sent"])

    def test_confirmed_send_rejects_stale_request_window_before_helper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            request_json = write_request(
                tmp_path / "window-request.json",
                request_payload(
                    standing_authority=True,
                    run_id="20260606T203359Z-player-principal-lifecycle",
                    start_utc="2026-06-06T20:33:59Z",
                    end_utc="2026-06-06T20:48:59Z",
                ),
            )
            called = tmp_path / "called.json"
            fake_helper = tmp_path / "fake_send_helper.py"
            fake_helper.write_text(
                "import json, sys\n"
                f"open({str(called)!r}, 'w', encoding='utf-8').write(json.dumps(sys.argv[1:]))\n",
                encoding="utf-8",
            )
            result = self.run_script(
                request_json,
                "--send-helper",
                str(fake_helper),
                "--confirm-approved-send",
            )
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(called.exists())
        self.assertFalse(report["ready"])
        self.assertEqual(report["mode"], "confirmed_send")
        self.assertFalse(report["helper_invoked"])
        self.assertFalse(report["discord_sent"])
        self.assertFalse(report["send_helper_returncode_zero"])
        self.assertFalse(report["confirmed_send_dry_run_receipt_preflight_invoked"])
        self.assertFalse(report["confirmed_send_dry_run_receipt_supplied_to_helper"])
        self.assertIsNone(report["confirmed_send_dry_run_receipt"])
        self.assertFalse(report["request_window_sendable"])
        self.assertTrue(report["stale_request_window"])
        self.assertTrue(report["send_blocked_by_stale_window"])
        self.assertEqual(report["request_window_blocker"], STALE_WINDOW_BLOCKER)
        guarded = report["guarded_beta_notice_action"]
        self.assertFalse(guarded["helper_invoked"])
        self.assertFalse(guarded["guarded_helper_invocation"])
        self.assertTrue(guarded["confirm_approved_send_arg_used"])
        self.assertFalse(guarded["approval_scope_arg_used"])
        self.assertFalse(guarded["real_beta_test_notice_action_completed"])
        self.assertEqual(guarded["blocker"], STALE_WINDOW_BLOCKER)
        self.assertFalse(guarded["discord_send_authorized"])
        self.assertFalse(guarded["counts_as_approved_runtime_evidence"])
        self.assertEqual(report["next_blocker"], STALE_WINDOW_BLOCKER)

    def test_rejects_notice_action_not_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json", request_payload(required=False))
            result = self.run_script(request_json, "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("player_notice_action.required must be true", result.stderr)

    def test_rejects_not_applicable_notice_path(self) -> None:
        payload = request_payload(notice_path="not_applicable")
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json", payload)
            result = self.run_script(request_json, "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"notice_path must be {APPROVED_BETA_NOTICE_PATH}", result.stderr)

    def test_rejects_unapproved_notice_path_label(self) -> None:
        payload = request_payload(notice_path="other-discord-channel")
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json", payload)
            result = self.run_script(request_json, "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"notice_path must be {APPROVED_BETA_NOTICE_PATH}", result.stderr)

    def test_standing_authority_still_rejects_unapproved_notice_path_label(self) -> None:
        payload = request_payload(
            notice_path="other-discord-channel",
            standing_authority=True,
        )
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json", payload)
            result = self.run_script(request_json, "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"notice_path must be {APPROVED_BETA_NOTICE_PATH}", result.stderr)

    def test_rejects_request_without_exact_target_binding(self) -> None:
        payload = request_payload()
        payload["target"] = {"instance": "public-sdk", "map": "current"}
        payload["exact_target_scope"] = {
            **payload["exact_target_scope"],
            "instance": "arkserver3",
            "map": "Genesis2",
            "instance_alias_allowed": True,
            "map_alias_allowed": True,
        }
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json", payload)
            result = self.run_script(request_json, "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("target_instance_alias_not_exact", result.stderr)
        self.assertIn("target_map_alias_not_exact", result.stderr)
        self.assertIn("exact_target_scope_instance_mismatch", result.stderr)
        self.assertIn("exact_target_scope_map_mismatch", result.stderr)
        self.assertIn("exact_target_scope_instance_alias_allowed_not_false", result.stderr)
        self.assertIn("exact_target_scope_map_alias_allowed_not_false", result.stderr)

    def test_rejects_request_run_id_not_bound_to_window_start(self) -> None:
        payload = request_payload()
        payload["run_id"] = "20260605T091000Z-player-principal-lifecycle"
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json", payload)
            result = self.run_script(request_json, "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("run_id_window_start_mismatch", result.stderr)

    def test_rejects_request_without_exact_direct_join_plan(self) -> None:
        payload = request_payload()
        payload["direct_join_plan"]["third_ark_server_allowed"] = True
        payload["direct_join_plan"]["organic_wait_window_seconds"] = 600
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json", payload)
            result = self.run_script(request_json, "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("direct_join_plan_third_ark_server_allowed_not_false", result.stderr)
        self.assertIn("direct_join_plan_organic_wait_window_seconds_mismatch", result.stderr)
        self.assertIn("direct_join_plan_mismatch", result.stderr)

    def test_rejects_notice_action_that_claims_authorization(self) -> None:
        payload = request_payload()
        payload["player_notice_action"]["non_authorization"] = "notice action authorizes Discord and runtime"
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json", payload)
            result = self.run_script(request_json, "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("non_authorization mismatch", result.stderr)

    def test_rejects_notice_action_with_nested_evidence_or_sdk_claims(self) -> None:
        payload = request_payload()
        payload["player_notice_action"]["nested_claims"] = {
            "approved_runtime_evidence": True,
            "counts_toward_sdk": True,
            "complete_sdk_progress_contribution": 1,
        }
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json", payload)
            result = self.run_script(request_json, "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "forbidden_notice_request_claim:$.player_notice_action.nested_claims.approved_runtime_evidence",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_claim:$.player_notice_action.nested_claims.counts_toward_sdk",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_progress_claim:$.player_notice_action.nested_claims.complete_sdk_progress_contribution",
            result.stderr,
        )

    def test_rejects_request_with_nested_status_or_process_control_claims(self) -> None:
        payload = request_payload()
        payload["route_snapshot"] = {
            "public_sdk_ready": True,
            "runtime_capture_authorized": True,
            "process_control": "restart",
            "readiness_gate": "approved_runtime_bundle",
        }
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json", payload)
            result = self.run_script(request_json, "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "forbidden_notice_request_claim:$.route_snapshot.public_sdk_ready",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_claim:$.route_snapshot.runtime_capture_authorized",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_process_control:$.route_snapshot.process_control",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_readiness_gate:$.route_snapshot.readiness_gate",
            result.stderr,
        )

    def test_rejects_camelcase_notice_request_claim_aliases(self) -> None:
        payload = request_payload()
        payload["routeSnapshot"] = {
            "publicSdkReady": True,
            "runtimeCaptureAuthorized": True,
            "processControl": "restart",
            "readinessGate": "approved_runtime_bundle",
        }
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json", payload)
            result = self.run_script(request_json, "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "forbidden_notice_request_claim:$.routeSnapshot.publicSdkReady",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_claim:$.routeSnapshot.runtimeCaptureAuthorized",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_process_control:$.routeSnapshot.processControl",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_readiness_gate:$.routeSnapshot.readinessGate",
            result.stderr,
        )

    def test_rejects_split_notice_request_claim_aliases(self) -> None:
        payload = request_payload()
        payload["route_snapshot"] = {
            "claims": [
                {"field": "publicSdkReady", "state": "ready"},
                {"name": "completeSdkProgressContribution", "value": 1},
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json", payload)
            result = self.run_script(request_json, "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "forbidden_notice_request_claim:$.route_snapshot.claims[0]",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_progress_claim:$.route_snapshot.claims[1]",
            result.stderr,
        )

    def test_rejects_generic_ready_status_and_progress_aliases(self) -> None:
        payload = request_payload()
        payload["route_status_aliases"] = {
            "isReady": True,
            "result": "ready",
            "status": "accepted",
            "runtimeProgress": 1,
        }
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json", payload)
            result = self.run_script(request_json, "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "forbidden_notice_request_claim:$.route_status_aliases.isReady",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_claim:$.route_status_aliases.result",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_claim:$.route_status_aliases.status",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_progress_claim:$.route_status_aliases.runtimeProgress",
            result.stderr,
        )

    def test_rejects_unblocked_status_and_sdk_credit_aliases(self) -> None:
        payload = request_payload()
        payload["route_credit_aliases"] = {
            "routeStatus": "unblocked",
            "sdkCredits": 1,
            "completeSdkCredit": "1/12",
            "p0DependencyChainCredits": [0, 1],
            "splitClaims": [
                {"field": "sdkCredits", "value": 1},
                {"field": "p0DependencyChainCredit", "value": "1/4"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json", payload)
            result = self.run_script(request_json, "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "forbidden_notice_request_claim:$.route_credit_aliases.routeStatus",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_progress_claim:$.route_credit_aliases.sdkCredits",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_progress_claim:$.route_credit_aliases.completeSdkCredit",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_progress_claim:$.route_credit_aliases.p0DependencyChainCredits",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_progress_claim:$.route_credit_aliases.splitClaims[0]",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_progress_claim:$.route_credit_aliases.splitClaims[1]",
            result.stderr,
        )

    def test_rejects_notice_delivered_sent_or_accepted_aliases_as_evidence(self) -> None:
        payload = request_payload()
        payload["notice_delivery_aliases"] = {
            "noticeDelivered": True,
            "playerNoticeDeliveryStatus": "delivered",
            "acceptedNoticeAction": True,
            "noticeSentAsRuntimeEvidence": True,
        }
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json", payload)
            result = self.run_script(request_json, "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "forbidden_notice_request_claim:$.notice_delivery_aliases.noticeDelivered",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_claim:$.notice_delivery_aliases.playerNoticeDeliveryStatus",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_claim:$.notice_delivery_aliases.acceptedNoticeAction",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_claim:$.notice_delivery_aliases.noticeSentAsRuntimeEvidence",
            result.stderr,
        )

    def test_rejects_passive_status_notice_and_public_readiness_aliases(self) -> None:
        payload = request_payload()
        payload["flow_aliases"] = {
            "passiveMonitorStatus": "ready",
            "publicReadiness": True,
            "noticeStatus": "sent",
            "runtimeStatus": "ready",
        }
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json", payload)
            result = self.run_script(request_json, "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "forbidden_notice_request_claim:$.flow_aliases.passiveMonitorStatus",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_claim:$.flow_aliases.publicReadiness",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_claim:$.flow_aliases.noticeStatus",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_claim:$.flow_aliases.runtimeStatus",
            result.stderr,
        )

    def test_rejects_false_only_aliases_with_non_false_values(self) -> None:
        payload = request_payload()
        payload["false_only_aliases"] = {
            "publicSdkReady": 0,
            "runtimeReady": None,
            "currentTurnScopeAuthorized": "false",
            "splitClaims": [
                {"field": "runtimeReady", "value": 0},
                {"field": "publicSdkReady", "value": "false"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json", payload)
            result = self.run_script(request_json, "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "forbidden_notice_request_claim:$.false_only_aliases.publicSdkReady",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_claim:$.false_only_aliases.runtimeReady",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_claim:$.false_only_aliases.currentTurnScopeAuthorized",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_claim:$.false_only_aliases.splitClaims[0]",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_claim:$.false_only_aliases.splitClaims[1]",
            result.stderr,
        )

    def test_rejects_notice_current_turn_closure_and_live_log_aliases(self) -> None:
        payload = request_payload()
        payload["offline_aliases"] = {
            "dryRunNoticeStatus": "ready",
            "sentNoticeAuthorizesRuntime": "yes",
            "closureRequestStatus": "approved",
            "closureRequestProgress": 1,
            "liveLogPermission": "allowed",
            "currentTurnScopeAuthorized": "yes",
        }
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json", payload)
            result = self.run_script(request_json, "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "forbidden_notice_request_claim:$.offline_aliases.dryRunNoticeStatus",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_claim:$.offline_aliases.sentNoticeAuthorizesRuntime",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_claim:$.offline_aliases.closureRequestStatus",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_progress_claim:$.offline_aliases.closureRequestProgress",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_claim:$.offline_aliases.liveLogPermission",
            result.stderr,
        )
        self.assertIn(
            "forbidden_notice_request_claim:$.offline_aliases.currentTurnScopeAuthorized",
            result.stderr,
        )

    def test_rejects_live_server_request_json(self) -> None:
        result = self.run_script(Path("/servidor/ark/obelisk/window-request.json"), "--dry-run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("protected server root", result.stderr)

    def test_rejects_live_server_send_helper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_json = write_request(Path(tmp) / "window-request.json")
            result = self.run_script(
                request_json,
                "--send-helper",
                "/servidor/ark/obelisk/send_discord_embed.py",
                "--dry-run",
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("protected server root", result.stderr)

    def test_confirmed_send_delegates_to_helper_with_matching_beta_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            request_json = write_request(tmp_path / "window-request.json")
            called = tmp_path / "called.json"
            fake_helper = tmp_path / "fake_send_helper.py"
            write_strict_receipt_helper(fake_helper, called)
            result = self.run_script(
                request_json,
                "--send-helper",
                str(fake_helper),
                "--confirm-approved-send",
            )
            report = json.loads(result.stdout)
            helper_calls = json.loads(called.read_text(encoding="utf-8"))
            dry_run_args = helper_calls[0]
            helper_args = helper_calls[1]
            sidecar = json.loads(
                default_notice_sidecar(request_json, "confirmed_send").read_text(encoding="utf-8")
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(helper_calls), 2)
        self.assertIn("--dry-run", dry_run_args)
        self.assertNotIn("--confirm-approved-send", dry_run_args)
        self.assertNotIn("--dry-run-receipt", dry_run_args)
        self.assertTrue(report["ready"])
        self.assertEqual(report["mode"], "confirmed_send")
        self.assertTrue(report["discord_sent"])
        self.assertTrue(report["confirmed_send_dry_run_receipt_preflight_invoked"])
        self.assertTrue(report["confirmed_send_dry_run_receipt_preflight_returncode_zero"])
        self.assertIsNotNone(report["confirmed_send_dry_run_receipt"])
        self.assertEqual(
            report["confirmed_send_dry_run_receipt"],
            report["confirmed_send_dry_run_receipt_preflight_payload"]["dry_run_receipt"],
        )
        self.assertTrue(report["confirmed_send_dry_run_receipt_supplied_to_helper"])
        self.assertTrue(report["confirmed_send_dry_run_receipt_validated_by_helper"])
        self.assertEqual(sidecar["schema"], NOTICE_ACTION_ARTIFACT_SCHEMA)
        self.assertEqual(sidecar["mode"], "confirmed_send")
        self.assertEqual(sidecar["notice_report"], report)
        self.assertFalse(sidecar["stdout_only_confirmation_accepted"])
        for key, expected in SIDECAR_NON_EVIDENCE_FLAGS.items():
            with self.subTest(sidecar_flag=key):
                self.assertIs(sidecar[key], expected)
        self.assertTrue(report["send_helper_returncode_zero"])
        self.assertFalse(report["discord_send_authorized"])
        self.assertFalse(report["current_turn_approval_recorded"])
        self.assertFalse(report["current_turn_scope_authorized"])
        self.assertFalse(report["notice_action_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["notice_action_counts_toward_sdk"])
        self.assertFalse(report["notice_action_counts_toward_p0_dependency_chain"])
        self.assertFalse(report["confirmed_send_authorizes_activation"])
        self.assertFalse(report["confirmed_send_authorizes_runtime_capture"])
        self.assertFalse(report["confirmed_send_authorizes_server_operations"])
        guarded = report["guarded_beta_notice_action"]
        self.assertEqual(guarded["mode"], "confirmed_send")
        self.assertEqual(guarded["player_notice_action"], report["player_notice_action"])
        self.assertTrue(guarded["real_beta_test_notice_action_completed"])
        self.assertFalse(guarded["send_performed_by_request_pack"])
        self.assertFalse(guarded["discord_authorized"])
        self.assertFalse(guarded["discord_send_authorized"])
        self.assertFalse(guarded["current_turn_approval_recorded"])
        self.assertFalse(guarded["current_turn_scope_authorized"])
        self.assertFalse(guarded["runtime_capture_authorized"])
        self.assertFalse(guarded["server_operations_authorized"])
        self.assertFalse(guarded["notice_action_covered_by_standing_launch_authority"])
        self.assertFalse(guarded["standing_authority_authorizes_discord_send"])
        self.assertEqual(guarded["configured_send_path"], "discord_bot_channel")
        self.assertEqual(guarded["operational_message_workflow"], "single_active_bot_notice")
        self.assertTrue(guarded["single_operational_message_required"])
        self.assertTrue(guarded["active_notice_state_required_for_beta_controls"])
        self.assertTrue(guarded["send_beta_notice_arg_used"])
        self.assertTrue(guarded["with_beta_controls_arg_used"])
        self.assertTrue(guarded["update_active_notice_arg_used"])
        self.assertTrue(guarded["dry_run_receipt_arg_used"])
        self.assertTrue(guarded["dry_run_receipt_supplied_to_helper"])
        self.assertTrue(guarded["dry_run_receipt_from_exact_helper_dry_run"])
        self.assertFalse(guarded["button_interactions_create_channel_messages"])
        self.assertFalse(guarded["status_summary_creates_channel_message"])
        self.assertFalse(guarded["status_summary_claims_readiness"])
        self.assertFalse(guarded["embed_claims_readiness"])
        self.assertFalse(guarded["uses_webhook"])
        self.assertFalse(guarded["webhook_real_send_allowed"])
        self.assertTrue(guarded["webhook_fail_closed_for_real_sends"])
        self.assertIn("--send-beta-notice", helper_args)
        self.assertIn("--with-beta-controls", helper_args)
        self.assertIn("--update-active-notice", helper_args)
        self.assertIn("--confirm-approved-send", helper_args)
        self.assertIn("--dry-run-receipt", helper_args)
        self.assertEqual(
            helper_args[helper_args.index("--dry-run-receipt") + 1],
            report["confirmed_send_dry_run_receipt"],
        )
        self.assertNotIn("--webhook-url", helper_args)
        self.assertNotIn("--webhook-env", helper_args)
        self.assertNotIn("--use-webhook", helper_args)
        self.assertNotIn("--approval-scope", helper_args)
        self.assertIn("--content", helper_args)
        self.assertLess(helper_args.index("--with-beta-controls"), helper_args.index("--content"))
        self.assertLess(helper_args.index("--update-active-notice"), helper_args.index("--content"))
        self.assertIn("@everyone", helper_args[helper_args.index("--content") + 1])

    def test_confirmed_send_redacts_helper_stderr_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            request_json = write_request(tmp_path / "window-request.json")
            called = tmp_path / "called.json"
            fake_helper = tmp_path / "fake_send_helper.py"
            write_strict_receipt_helper(
                fake_helper,
                called,
                confirm_stderr="failed discord.com/api/webhooks/123/SECRET WEBHOOK_TOKEN=abc123",
            )
            result = self.run_script(
                request_json,
                "--send-helper",
                str(fake_helper),
                "--confirm-approved-send",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("discord.com/api/webhooks/<redacted>", report["helper_stderr"])
        self.assertIn("WEBHOOK_TOKEN=<redacted>", report["helper_stderr"])
        self.assertNotIn("SECRET", report["helper_stderr"])
        self.assertNotIn("abc123", report["helper_stderr"])


if __name__ == "__main__":
    unittest.main()
