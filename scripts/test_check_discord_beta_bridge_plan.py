#!/usr/bin/env python3
"""Tests for check_discord_beta_bridge_plan.py."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "check_discord_beta_bridge_plan.py"
sys.path.insert(0, str(SCRIPT_DIR))

from check_discord_beta_bridge_plan import canonical_plan  # noqa: E402


class DiscordBetaBridgePlanTests(unittest.TestCase):
    def run_checker(self, payload: dict[str, object] | None = None) -> subprocess.CompletedProcess[str]:
        if payload is None:
            return subprocess.run(
                [sys.executable, str(SCRIPT), "--json"],
                cwd=SCRIPT_DIR.parent,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp) / "discord-beta-bridge-plan.json"
            plan.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(plan), "--json"],
                cwd=SCRIPT_DIR.parent,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

    def test_canonical_plan_is_valid_and_non_authorizing(self) -> None:
        result = self.run_checker()
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report["valid"])
        self.assertTrue(report["bot_required_for_interaction"])
        self.assertEqual(report["bot_channel_id"], "1513238083741683934")
        self.assertTrue(report["bot_channel_required_for_real_send"])
        self.assertFalse(report["webhook_outbound_only"])
        self.assertTrue(report["webhook_deprecated"])
        self.assertFalse(report["webhook_real_send_allowed"])
        self.assertTrue(report["webhook_fail_closed_for_real_sends"])
        self.assertTrue(report["rotated_token_required"])
        self.assertEqual(
            report["token_rotation_attestation_env_var"],
            "OBELISK_DISCORD_BOT_TOKEN_ROTATED_AT_UTC",
        )
        self.assertFalse(report["freeform_channel_scraping_allowed"])
        self.assertEqual(
            report["commands"],
            ["status", "ready", "joined", "logout-ready", "issue", "done"],
        )
        self.assertTrue(report["privacy_boundary"]["redacted_jsonl_events"])
        self.assertFalse(report["privacy_boundary"]["raw_message_content_retention_allowed"])
        self.assertTrue(report["event_sink_semantics"]["metadata_only"])
        self.assertFalse(report["event_sink_semantics"]["raw_discord_payload_retention_allowed"])
        self.assertFalse(report["event_sink_semantics"]["event_sink_counts_as_evidence"])
        self.assertTrue(report["live_run_preflight"]["requires_bot_token"])
        self.assertTrue(report["live_run_preflight"]["requires_rotated_token_attestation"])
        self.assertTrue(report["live_run_preflight"]["requires_discord_py_dependency"])
        self.assertFalse(report["live_run_preflight"]["discord_connection_allowed_by_plan_check"])
        self.assertFalse(report["live_run_preflight"]["token_value_output_allowed"])
        self.assertEqual(
            report["local_offline_workflow"]["dependency_interpreter"],
            "local/discord-bridge-venv/bin/python",
        )
        self.assertEqual(
            report["local_offline_workflow"]["config_check_command"],
            [
                "local/discord-bridge-venv/bin/python",
                "scripts/discord_beta_bridge.py",
                "--check-config",
                "--json",
                "--require-token",
            ],
        )
        self.assertTrue(
            report["local_offline_workflow"]["use_local_venv_when_system_python_lacks_discord_py"]
        )
        self.assertFalse(
            report["local_offline_workflow"]["discord_connection_allowed_by_config_check"]
        )
        self.assertFalse(report["local_offline_workflow"]["token_value_output_allowed"])
        notice_path = report["notice_send_path"]
        self.assertEqual(notice_path["default_transport"], "discord_bot_channel")
        self.assertEqual(notice_path["operational_message_workflow"], "single_active_bot_notice")
        self.assertEqual(
            notice_path["operational_message_style"],
            "single_updated_embed_buttons_operational_message",
        )
        self.assertEqual(notice_path["bot_channel_id"], "1513238083741683934")
        self.assertEqual(notice_path["expected_channel_id"], "1513238083741683934")
        self.assertEqual(notice_path["bot_channel_env_var"], "OBELISK_DISCORD_BETA_CHANNEL_ID")
        self.assertEqual(
            notice_path["active_notice_state_env_var"],
            "OBELISK_DISCORD_ACTIVE_NOTICE_STATE",
        )
        self.assertEqual(notice_path["existing_active_notice_http_method"], "PATCH")
        self.assertEqual(notice_path["missing_active_notice_http_method"], "POST")
        self.assertTrue(notice_path["single_editable_notice_required"])
        self.assertTrue(notice_path["with_beta_controls_required"])
        self.assertTrue(notice_path["update_active_notice_required"])
        self.assertIn("--send-beta-notice", notice_path["helper_command"])
        self.assertIn("--with-beta-controls", notice_path["helper_command"])
        self.assertIn("--update-active-notice", notice_path["helper_command"])
        self.assertIn("obelisk_beta:started", notice_path["button_custom_ids"])
        self.assertIn("obelisk_beta:cluster_transfer", notice_path["button_custom_ids"])
        self.assertIn("obelisk_beta:joined:Genesis2", notice_path["button_custom_ids"])
        self.assertIn("obelisk_beta:issue:crash", notice_path["button_custom_ids"])
        self.assertIn("obelisk_beta:issue:other", notice_path["button_custom_ids"])
        self.assertIn("obelisk_beta:status_summary", notice_path["button_custom_ids"])
        self.assertEqual(
            notice_path["button_interaction_result_schema"],
            "obelisk.discord-beta-bridge-button-interaction-result.v1",
        )
        self.assertEqual(notice_path["button_action_count"], len(notice_path["button_action_map"]))
        action_by_id = {
            action["custom_id"]: action for action in notice_path["button_action_map"]
        }
        self.assertEqual(action_by_id["obelisk_beta:joined:Ragnarok"]["event_type"], "joined")
        self.assertEqual(action_by_id["obelisk_beta:joined:Ragnarok"]["map"], "Ragnarok")
        self.assertEqual(action_by_id["obelisk_beta:issue:timeout"]["issue_type"], "timeout")
        self.assertTrue(action_by_id["obelisk_beta:issue:crash"]["writes_event"])
        self.assertFalse(action_by_id["obelisk_beta:status_summary"]["writes_event"])
        self.assertEqual(
            action_by_id["obelisk_beta:status_summary"]["response_mode"],
            "ephemeral_local_event_summary",
        )
        self.assertEqual(notice_path["status_summary_button_custom_id"], "obelisk_beta:status_summary")
        self.assertEqual(
            notice_path["status_summary_response_mode"],
            "ephemeral_local_event_summary",
        )
        self.assertTrue(notice_path["status_summary_button_required"])
        self.assertTrue(notice_path["status_summary_ephemeral_response_only"])
        self.assertTrue(notice_path["status_summary_uses_local_event_sink_only"])
        self.assertTrue(notice_path["status_summary_metadata_only"])
        self.assertFalse(notice_path["status_summary_button_writes_event"])
        self.assertFalse(notice_path["status_summary_reads_discord"])
        self.assertFalse(notice_path["status_summary_sends_discord"])
        self.assertFalse(notice_path["status_summary_creates_channel_message"])
        self.assertFalse(notice_path["status_summary_updates_operational_message"])
        self.assertFalse(notice_path["status_summary_creates_event"])
        self.assertFalse(notice_path["status_summary_claims_evidence"])
        self.assertFalse(notice_path["status_summary_claims_progress"])
        self.assertFalse(notice_path["status_summary_claims_readiness"])
        self.assertFalse(notice_path["status_summary_counts_as_approved_runtime_evidence"])
        self.assertFalse(notice_path["status_summary_counts_as_sdk_progress"])
        self.assertFalse(notice_path["status_summary_counts_as_readiness"])
        self.assertTrue(notice_path["single_operational_message_required"])
        self.assertTrue(notice_path["active_notice_state_required_for_beta_controls"])
        self.assertTrue(notice_path["single_updated_embed_buttons_message_preferred"])
        self.assertTrue(notice_path["edit_existing_message_when_active_notice_state_present"])
        self.assertTrue(notice_path["post_only_when_active_notice_state_missing"])
        self.assertEqual(
            notice_path["active_notice_reuse_policy"]["bot_channel_id"],
            "1513238083741683934",
        )
        self.assertEqual(
            notice_path["active_notice_reuse_policy"]["expected_channel_id"],
            "1513238083741683934",
        )
        self.assertEqual(
            notice_path["button_interaction_response_mode"],
            "ephemeral_ack_and_local_event_write",
        )
        self.assertTrue(notice_path["button_interactions_ephemeral_ack_only"])
        self.assertTrue(notice_path["button_interactions_metadata_only"])
        self.assertTrue(notice_path["button_interactions_write_local_redacted_events_only"])
        self.assertTrue(notice_path["button_interactions_local_event_acknowledgement_only"])
        self.assertTrue(notice_path["button_interactions_require_expected_channel"])
        self.assertTrue(notice_path["button_interactions_validate_metadata_only_result"])
        self.assertFalse(notice_path["button_interactions_create_channel_messages"])
        self.assertFalse(notice_path["button_interactions_create_followup_messages"])
        self.assertFalse(notice_path["button_interactions_read_discord"])
        self.assertFalse(notice_path["button_interactions_send_discord"])
        self.assertFalse(notice_path["button_interactions_use_network"])
        self.assertFalse(notice_path["button_interactions_retain_raw_user_id"])
        self.assertFalse(notice_path["button_interactions_retain_raw_player_text"])
        self.assertFalse(notice_path["button_interactions_retain_secrets"])
        self.assertFalse(notice_path["button_events_count_as_sdk_progress"])
        self.assertFalse(notice_path["button_events_claim_readiness"])
        self.assertFalse(notice_path["embed_claims_readiness"])
        self.assertFalse(notice_path["uses_webhook"])
        self.assertFalse(notice_path["webhook_real_send_allowed"])
        self.assertTrue(notice_path["webhook_fail_closed_for_real_sends"])
        self.assertFalse(notice_path["counts_as_approved_runtime_evidence"])
        self.assertFalse(notice_path["counts_as_sdk_progress"])
        self.assertFalse(notice_path["counts_as_readiness"])
        boundary = notice_path["discord_beta_non_promotion"]
        self.assertEqual(
            boundary["schema"],
            "obelisk.discord-beta-bridge-non-promotion-boundary.v1",
        )
        self.assertTrue(boundary["accepted_copied_sibling_set_required_before_runtime_claims"])
        self.assertFalse(boundary["discord_or_beta_interactions_count_as_approved_runtime_evidence"])
        self.assertFalse(boundary["discord_or_beta_interactions_count_as_runtime_evidence"])
        self.assertFalse(boundary["discord_or_beta_interactions_count_as_sdk_progress"])
        self.assertFalse(boundary["discord_or_beta_interactions_count_as_p0_progress"])
        self.assertFalse(boundary["discord_or_beta_interactions_count_as_public_sdk_readiness"])
        self.assertFalse(boundary["discord_or_beta_interactions_count_as_stable_sdk_readiness"])
        self.assertFalse(boundary["discord_or_beta_interactions_authorize_live_actions"])
        self.assertFalse(boundary["discord_or_beta_interactions_approve_live_actions"])
        self.assertFalse(notice_path["discord_or_beta_interactions_count_as_sdk_progress"])
        self.assertFalse(notice_path["discord_or_beta_interactions_approve_live_actions"])
        for key, value in report["non_authorization"].items():
            with self.subTest(non_authorization=key):
                self.assertIs(value, False)

    def test_rejects_live_ops_and_readiness_authorization_aliases(self) -> None:
        plan = canonical_plan()
        plan["non_authorization"]["authorizes_rcon"] = True
        plan["non_authorization"]["authorizes_server_restart"] = True
        plan["non_authorization"]["counts_as_approved_runtime_evidence"] = True
        plan["non_authorization"]["public_sdk_ready"] = True

        result = self.run_checker(plan)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["valid"])
        self.assertIn("authorizes_rcon_not_false", report["blockers"])
        self.assertIn("authorizes_server_restart_not_false", report["blockers"])
        self.assertIn("counts_as_approved_runtime_evidence_not_false", report["blockers"])
        self.assertIn("public_sdk_ready_not_false", report["blockers"])
        self.assertIn("authorization_progress_evidence_alias_not_false", report["blockers"])

    def test_rejects_webhook_real_send_and_missing_editable_bot_notice_controls(self) -> None:
        plan = canonical_plan()
        plan["webhook_outbound_only"] = True
        plan["webhook_deprecated"] = False
        plan["webhook_real_send_allowed"] = True
        plan["webhook_fail_closed_for_real_sends"] = False
        plan["notice_send_path"]["default_transport"] = "webhook"
        plan["notice_send_path"]["required_helper_args"] = [
            "--send-beta-notice",
            "--with-beta-controls",
        ]
        plan["notice_send_path"]["helper_command"] = [
            "local/discord-bridge-venv/bin/python",
            "scripts/discord_beta_bridge.py",
            "--send-beta-notice",
            "--with-beta-controls",
            "--json",
        ]
        plan["notice_send_path"]["single_editable_notice_required"] = False
        plan["notice_send_path"]["with_beta_controls_required"] = False
        plan["notice_send_path"]["update_active_notice_required"] = False
        plan["notice_send_path"]["uses_webhook"] = True
        plan["notice_send_path"]["webhook_outbound_only"] = True
        plan["notice_send_path"]["webhook_real_send_allowed"] = True
        plan["notice_send_path"]["webhook_fail_closed_for_real_sends"] = False

        result = self.run_checker(plan)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("webhook_outbound_only_not_false", report["blockers"])
        self.assertIn("webhook_deprecated_not_true", report["blockers"])
        self.assertIn("webhook_real_send_allowed_not_false", report["blockers"])
        self.assertIn("webhook_fail_closed_for_real_sends_not_true", report["blockers"])
        self.assertIn("notice_default_transport_mismatch", report["blockers"])
        self.assertIn("notice_required_helper_args_mismatch", report["blockers"])
        self.assertIn("notice_helper_command_mismatch", report["blockers"])
        self.assertIn("notice_single_editable_notice_required_not_true", report["blockers"])
        self.assertIn("notice_with_beta_controls_required_not_true", report["blockers"])
        self.assertIn("notice_update_active_notice_required_not_true", report["blockers"])
        self.assertIn("notice_uses_webhook_not_false", report["blockers"])
        self.assertIn("notice_webhook_real_send_allowed_not_false", report["blockers"])
        self.assertIn("notice_webhook_fail_closed_for_real_sends_not_true", report["blockers"])

    def test_rejects_wrong_bot_channel_binding(self) -> None:
        plan = canonical_plan()
        plan["bot_channel_id"] = "1513238083741683935"
        plan["bot_channel_required_for_real_send"] = False
        plan["notice_send_path"]["bot_channel_id"] = "1513238083741683935"
        plan["notice_send_path"]["expected_channel_id"] = "1513238083741683935"
        plan["notice_send_path"]["active_notice_reuse_policy"][
            "bot_channel_id"
        ] = "1513238083741683935"
        plan["notice_send_path"]["active_notice_reuse_policy"][
            "expected_channel_id"
        ] = "1513238083741683935"

        result = self.run_checker(plan)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("bot_channel_id_mismatch", report["blockers"])
        self.assertIn("bot_channel_required_for_real_send_not_true", report["blockers"])
        self.assertIn("notice_bot_channel_id_mismatch", report["blockers"])
        self.assertIn("notice_expected_channel_id_mismatch", report["blockers"])
        self.assertIn("notice_active_notice_reuse_bot_channel_id_mismatch", report["blockers"])
        self.assertIn(
            "notice_active_notice_reuse_expected_channel_id_mismatch",
            report["blockers"],
        )

    def test_rejects_status_summary_button_drift(self) -> None:
        plan = canonical_plan()
        plan["notice_send_path"]["button_custom_ids"] = [
            item
            for item in plan["notice_send_path"]["button_custom_ids"]
            if item != "obelisk_beta:status_summary"
        ]
        plan["notice_send_path"]["status_summary_button_custom_id"] = "obelisk_beta:status"
        plan["notice_send_path"]["status_summary_response_mode"] = "channel_message"
        plan["notice_send_path"]["status_summary_button_required"] = False
        plan["notice_send_path"]["status_summary_ephemeral_response_only"] = False
        plan["notice_send_path"]["status_summary_uses_local_event_sink_only"] = False
        plan["notice_send_path"]["status_summary_metadata_only"] = False
        plan["notice_send_path"]["status_summary_button_writes_event"] = True
        plan["notice_send_path"]["status_summary_reads_discord"] = True
        plan["notice_send_path"]["status_summary_sends_discord"] = True
        plan["notice_send_path"]["status_summary_counts_as_approved_runtime_evidence"] = True
        plan["notice_send_path"]["status_summary_counts_as_sdk_progress"] = True

        result = self.run_checker(plan)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("notice_button_custom_ids_mismatch", report["blockers"])
        self.assertIn("notice_status_summary_button_custom_id_mismatch", report["blockers"])
        self.assertIn("notice_status_summary_response_mode_mismatch", report["blockers"])
        self.assertIn("notice_status_summary_button_required_not_true", report["blockers"])
        self.assertIn("notice_status_summary_ephemeral_response_only_not_true", report["blockers"])
        self.assertIn("notice_status_summary_uses_local_event_sink_only_not_true", report["blockers"])
        self.assertIn("notice_status_summary_metadata_only_not_true", report["blockers"])
        self.assertIn("notice_status_summary_button_writes_event_not_false", report["blockers"])
        self.assertIn("notice_status_summary_reads_discord_not_false", report["blockers"])
        self.assertIn("notice_status_summary_sends_discord_not_false", report["blockers"])
        self.assertIn(
            "notice_status_summary_counts_as_approved_runtime_evidence_not_false",
            report["blockers"],
        )
        self.assertIn("notice_status_summary_counts_as_sdk_progress_not_false", report["blockers"])

    def test_rejects_missing_button_action_metadata(self) -> None:
        plan = canonical_plan()
        plan["notice_send_path"]["button_custom_ids"] = [
            item
            for item in plan["notice_send_path"]["button_custom_ids"]
            if item != "obelisk_beta:issue:crash"
        ]
        plan["notice_send_path"]["button_action_count"] = 1
        plan["notice_send_path"]["button_action_map"] = [
            {
                "custom_id": "obelisk_beta:status_summary",
                "event_type": "status",
                "response_mode": "channel_message",
                "writes_event": True,
            }
        ]

        result = self.run_checker(plan)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("notice_button_custom_ids_mismatch", report["blockers"])
        self.assertIn("notice_button_action_count_mismatch", report["blockers"])
        self.assertIn("notice_button_action_map_mismatch", report["blockers"])

    def test_rejects_operational_message_flood_and_readiness_drift(self) -> None:
        plan = canonical_plan()
        notice_path = plan["notice_send_path"]
        notice_path["operational_message_workflow"] = "new_message_per_update"
        notice_path["operational_message_style"] = "new_plain_message"
        notice_path["single_operational_message_required"] = False
        notice_path["active_notice_state_required_for_beta_controls"] = False
        notice_path["single_updated_embed_buttons_message_preferred"] = False
        notice_path["edit_existing_message_when_active_notice_state_present"] = False
        notice_path["post_only_when_active_notice_state_missing"] = False
        notice_path["button_interaction_result_schema"] = "legacy"
        notice_path["button_interaction_response_mode"] = "channel_message"
        notice_path["button_interactions_ephemeral_ack_only"] = False
        notice_path["button_interactions_write_local_redacted_events_only"] = False
        notice_path["button_interactions_local_event_acknowledgement_only"] = False
        notice_path["button_interactions_validate_metadata_only_result"] = False
        notice_path["button_interactions_create_channel_messages"] = True
        notice_path["button_interactions_create_followup_messages"] = True
        notice_path["button_interactions_update_operational_message"] = True
        notice_path["button_interactions_read_discord"] = True
        notice_path["button_interactions_send_discord"] = True
        notice_path["button_interactions_use_network"] = True
        notice_path["button_interactions_retain_raw_user_id"] = True
        notice_path["button_interactions_retain_raw_player_text"] = True
        notice_path["button_interactions_retain_secrets"] = True
        notice_path["status_summary_creates_channel_message"] = True
        notice_path["status_summary_updates_operational_message"] = True
        notice_path["status_summary_creates_event"] = True
        notice_path["status_summary_claims_readiness"] = True
        notice_path["status_summary_counts_as_readiness"] = True
        notice_path["button_events_claim_readiness"] = True
        notice_path["button_events_count_as_sdk_progress"] = True
        notice_path["embed_claims_readiness"] = True
        notice_path["operational_message_counts_as_readiness"] = True
        notice_path["discord_or_beta_interactions_count_as_sdk_progress"] = True
        notice_path["discord_or_beta_interactions_approve_live_actions"] = True
        notice_path["discord_beta_non_promotion"][
            "discord_or_beta_interactions_grant_public_sdk_readiness"
        ] = True

        result = self.run_checker(plan)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("notice_operational_message_workflow_mismatch", report["blockers"])
        self.assertIn("notice_operational_message_style_mismatch", report["blockers"])
        self.assertIn("notice_single_operational_message_required_not_true", report["blockers"])
        self.assertIn(
            "notice_active_notice_state_required_for_beta_controls_not_true",
            report["blockers"],
        )
        self.assertIn(
            "notice_single_updated_embed_buttons_message_preferred_not_true",
            report["blockers"],
        )
        self.assertIn(
            "notice_edit_existing_message_when_active_notice_state_present_not_true",
            report["blockers"],
        )
        self.assertIn(
            "notice_post_only_when_active_notice_state_missing_not_true",
            report["blockers"],
        )
        self.assertIn("notice_button_interaction_result_schema_mismatch", report["blockers"])
        self.assertIn("notice_button_interaction_response_mode_mismatch", report["blockers"])
        self.assertIn("notice_button_interactions_ephemeral_ack_only_not_true", report["blockers"])
        self.assertIn(
            "notice_button_interactions_write_local_redacted_events_only_not_true",
            report["blockers"],
        )
        self.assertIn(
            "notice_button_interactions_local_event_acknowledgement_only_not_true",
            report["blockers"],
        )
        self.assertIn(
            "notice_button_interactions_validate_metadata_only_result_not_true",
            report["blockers"],
        )
        self.assertIn(
            "notice_button_interactions_create_channel_messages_not_false",
            report["blockers"],
        )
        self.assertIn(
            "notice_button_interactions_create_followup_messages_not_false",
            report["blockers"],
        )
        self.assertIn(
            "notice_button_interactions_update_operational_message_not_false",
            report["blockers"],
        )
        self.assertIn("notice_button_interactions_read_discord_not_false", report["blockers"])
        self.assertIn("notice_button_interactions_send_discord_not_false", report["blockers"])
        self.assertIn("notice_button_interactions_use_network_not_false", report["blockers"])
        self.assertIn(
            "notice_button_interactions_retain_raw_user_id_not_false",
            report["blockers"],
        )
        self.assertIn(
            "notice_button_interactions_retain_raw_player_text_not_false",
            report["blockers"],
        )
        self.assertIn("notice_button_interactions_retain_secrets_not_false", report["blockers"])
        self.assertIn("notice_status_summary_creates_channel_message_not_false", report["blockers"])
        self.assertIn("notice_status_summary_updates_operational_message_not_false", report["blockers"])
        self.assertIn("notice_status_summary_creates_event_not_false", report["blockers"])
        self.assertIn("notice_status_summary_claims_readiness_not_false", report["blockers"])
        self.assertIn("notice_status_summary_counts_as_readiness_not_false", report["blockers"])
        self.assertIn("notice_button_events_claim_readiness_not_false", report["blockers"])
        self.assertIn("notice_button_events_count_as_sdk_progress_not_false", report["blockers"])
        self.assertIn("notice_embed_claims_readiness_not_false", report["blockers"])
        self.assertIn("notice_operational_message_counts_as_readiness_not_false", report["blockers"])
        self.assertIn(
            "notice_discord_or_beta_interactions_count_as_sdk_progress_not_false",
            report["blockers"],
        )
        self.assertIn(
            "notice_discord_or_beta_interactions_approve_live_actions_not_false",
            report["blockers"],
        )
        self.assertIn("notice_discord_beta_non_promotion_mismatch", report["blockers"])
        self.assertIn("authorization_progress_evidence_alias_not_false", report["blockers"])

    def test_rejects_authorization_progress_and_evidence_aliases_outside_non_authorization(self) -> None:
        plan = canonical_plan()
        plan["discord_authorized"] = True
        plan["runtime_evidence_ready"] = "yes"
        plan["sdk_p0_progress"] = 1
        plan["authorization"] = True
        plan["evidence"] = "approved"
        plan["progress"] = 1
        plan["nested"] = {"clearsApprovedRuntimeEvidenceMissing": True}

        result = self.run_checker(plan)
        report = json.loads(result.stdout)
        details = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "authorization_progress_evidence_alias_not_false"
        }

        self.assertEqual(result.returncode, 1)
        self.assertIn("authorization_progress_evidence_alias_not_false", report["blockers"])
        self.assertIn("$.discord_authorized", details)
        self.assertIn("$.runtime_evidence_ready", details)
        self.assertIn("$.sdk_p0_progress", details)
        self.assertIn("$.authorization", details)
        self.assertIn("$.evidence", details)
        self.assertIn("$.progress", details)
        self.assertIn("$.nested.clearsApprovedRuntimeEvidenceMissing", details)

    def test_rejects_event_sink_and_live_run_preflight_drift(self) -> None:
        plan = canonical_plan()
        plan["event_sink_semantics"]["metadata_only"] = False
        plan["event_sink_semantics"]["raw_user_id_retention_allowed"] = True
        plan["event_sink_semantics"]["event_sink_counts_as_progress"] = True
        plan["live_run_preflight"]["requires_discord_py_dependency"] = False
        plan["live_run_preflight"]["discord_connection_allowed_by_plan_check"] = True
        plan["live_run_preflight"]["token_value_output_allowed"] = True

        result = self.run_checker(plan)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("event_sink_metadata_only_not_true", report["blockers"])
        self.assertIn("raw_user_id_retention_allowed_not_false", report["blockers"])
        self.assertIn("event_sink_counts_as_progress_not_false", report["blockers"])
        self.assertIn("requires_discord_py_dependency_not_true", report["blockers"])
        self.assertIn("discord_connection_allowed_by_plan_check_not_false", report["blockers"])
        self.assertIn("token_value_output_allowed_not_false", report["blockers"])

    def test_rejects_local_offline_workflow_drift(self) -> None:
        plan = canonical_plan()
        plan["local_offline_workflow"]["dependency_interpreter"] = "python3"
        plan["local_offline_workflow"]["config_check_command"] = [
            "python3",
            "scripts/discord_beta_bridge.py",
            "--check-config",
            "--json",
        ]
        plan["local_offline_workflow"]["use_local_venv_when_system_python_lacks_discord_py"] = False
        plan["local_offline_workflow"]["discord_connection_allowed_by_config_check"] = True
        plan["local_offline_workflow"]["token_value_output_allowed"] = True

        result = self.run_checker(plan)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("dependency_interpreter_mismatch", report["blockers"])
        self.assertIn("config_check_command_mismatch", report["blockers"])
        self.assertIn(
            "use_local_venv_when_system_python_lacks_discord_py_not_true",
            report["blockers"],
        )
        self.assertIn("discord_connection_allowed_by_config_check_not_false", report["blockers"])
        self.assertIn("token_value_output_allowed_not_false", report["blockers"])

    def test_rejects_raw_message_content_and_freeform_scraping(self) -> None:
        plan = canonical_plan()
        plan["freeform_channel_scraping_allowed"] = True
        plan["privacy_boundary"]["raw_message_content_retention_allowed"] = True
        plan["privacy_boundary"]["message_content_intent_required_by_default"] = True

        result = self.run_checker(plan)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("freeform_channel_scraping_allowed_not_false", report["blockers"])
        self.assertIn("raw_message_content_retention_allowed_not_false", report["blockers"])
        self.assertIn("message_content_intent_required_by_default_not_false", report["blockers"])

    def test_rejects_missing_rotated_token_run_guardrail(self) -> None:
        plan = canonical_plan()
        plan["rotated_token_required"] = False
        plan["token_rotation_attestation_env_var"] = "OBELISK_DISCORD_BOT_TOKEN"

        result = self.run_checker(plan)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("rotated_token_required_not_true", report["blockers"])
        self.assertIn("token_rotation_attestation_env_var_mismatch", report["blockers"])

    def test_rejects_webhook_or_token_secret_text(self) -> None:
        plan = canonical_plan()
        plan["operator_note"] = "bot_token=abc123 should never be stored"

        result = self.run_checker(plan)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("forbidden_secret_or_identifier_text", report["blockers"])

        plan = canonical_plan()
        plan["operator_note"] = "https://discord.com\x2fapi/webhooks/1/secret"
        result = self.run_checker(plan)
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("forbidden_secret_or_identifier_text", report["blockers"])

        plan = canonical_plan()
        plan["operator_note"] = f"{'A' * 24}.{'B' * 8}.{'C' * 32}"
        result = self.run_checker(plan)
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("forbidden_secret_or_identifier_text", report["blockers"])

    def test_rejects_non_minimal_permissions_and_command_drift(self) -> None:
        plan = canonical_plan()
        plan["permissions"] = [*plan["permissions"], "Administrator"]
        commands = copy.deepcopy(plan["commands"])
        commands.append({"id": "restart-server"})
        plan["commands"] = commands

        result = self.run_checker(plan)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("permissions_not_minimal", report["blockers"])
        self.assertIn("forbidden_permission_requested", report["blockers"])
        self.assertIn("command_sequence_mismatch", report["blockers"])


if __name__ == "__main__":
    unittest.main()
