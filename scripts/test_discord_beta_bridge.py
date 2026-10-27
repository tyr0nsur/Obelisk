#!/usr/bin/env python3
"""Tests for discord_beta_bridge.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "discord_beta_bridge.py"
sys.path.insert(0, str(SCRIPT_DIR))

import discord_beta_bridge  # noqa: E402
from discord_beta_bridge import (  # noqa: E402
    BETA_CHANNEL_ENV,
    BOT_NOTICE_SCHEMA,
    EVENT_SINK_ENV,
    EVENT_SUMMARY_SCHEMA,
    EXPECTED_CHANNEL_ID,
    EXPECTED_GUILD_ID,
    GUILD_ENV,
    ROTATED_TOKEN_AT_ENV,
    TOKEN_ENV,
    ACTIVE_NOTICE_STATE_ENV,
    BUTTON_INTERACTION_RESULT_SCHEMA,
    beta_control_action_map,
    beta_control_components,
    beta_operational_embed_metadata,
    beta_tester_status_workflow,
    parse_beta_control_custom_id,
    build_event,
    format_tester_status_summary,
    handle_beta_control_interaction,
    send_bot_notice,
    check_config,
    summarize_event_sink,
    validate_metadata_only_button_interaction_result,
    validate_metadata_only_event,
    validate_metadata_only_event_summary,
    write_event,
)


DISCORD_ENV_KEYS = (
    TOKEN_ENV,
    ROTATED_TOKEN_AT_ENV,
    GUILD_ENV,
    BETA_CHANNEL_ENV,
    EVENT_SINK_ENV,
    ACTIVE_NOTICE_STATE_ENV,
    discord_beta_bridge.SALT_ENV,
)


def assert_discord_beta_non_promotion(
    testcase: unittest.TestCase,
    boundary: dict[str, object],
) -> None:
    testcase.assertEqual(
        boundary["schema"],
        discord_beta_bridge.DISCORD_BETA_NON_PROMOTION_SCHEMA,
    )
    testcase.assertEqual(
        boundary["single_operational_message_style"],
        discord_beta_bridge.SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE,
    )
    testcase.assertTrue(boundary["accepted_copied_sibling_set_required_before_runtime_claims"])
    for key, expected in discord_beta_bridge.DISCORD_BETA_NON_PROMOTION_FLAGS.items():
        with testcase.subTest(discord_beta_non_promotion=key):
            testcase.assertIs(boundary[key], expected)


def scrubbed_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    for key in DISCORD_ENV_KEYS:
        env.pop(key, None)
    if extra:
        env.update(extra)
    return env


def write_env(path: Path, *, token: str = "", rotated_token_at: str = "") -> Path:
    path.write_text(
        "\n".join(
            [
                f"{TOKEN_ENV}={token}",
                f"{ROTATED_TOKEN_AT_ENV}={rotated_token_at}",
                f"{GUILD_ENV}={EXPECTED_GUILD_ID}",
                f"{BETA_CHANNEL_ENV}={EXPECTED_CHANNEL_ID}",
                f"{EVENT_SINK_ENV}=local/discord-beta-bridge/events.jsonl",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


class DiscordBetaBridgeTests(unittest.TestCase):
    def test_check_config_is_valid_without_token_when_not_running(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = write_env(Path(tmp) / "discord-bot.env")
            with mock.patch.dict(os.environ, scrubbed_env(), clear=True):
                report = check_config(env_file)

        self.assertTrue(report["valid"])
        self.assertFalse(report["token_present"])
        self.assertEqual(report["token_value_redacted"], "<missing>")
        self.assertFalse(report["token_rotation_required"])
        self.assertFalse(report["token_rotation_attestation_present"])
        self.assertFalse(report["token_rotation_attestation_valid"])
        self.assertFalse(report["discord_py_required"])
        self.assertEqual(report["event_sink_semantics"], "metadata_only_redacted_jsonl")
        self.assertTrue(report["communication_posture_only"])
        self.assertEqual(report["guild_id"], EXPECTED_GUILD_ID)
        self.assertEqual(report["beta_channel_id"], EXPECTED_CHANNEL_ID)
        self.assertFalse(report["non_authorization"]["authorizes_rcon"])
        self.assertFalse(report["non_authorization"]["counts_as_approved_runtime_evidence"])

    def test_require_token_reports_missing_token_and_dependency_without_leaking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = write_env(Path(tmp) / "discord-bot.env")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--env-file", str(env_file), "--check-config", "--require-token"],
                cwd=SCRIPT_DIR.parent,
                env=scrubbed_env(),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["valid"])
        self.assertIn("bot_token_missing", report["blockers"])
        self.assertNotIn("discord.com\x2fapi/webhooks", result.stdout)
        self.assertNotIn("abc123", result.stdout)

    def test_present_token_requires_rotation_attestation_without_leaking_token(self) -> None:
        placeholder_token = "unit-test-placeholder-token"
        with tempfile.TemporaryDirectory() as tmp:
            env_file = write_env(Path(tmp) / "discord-bot.env", token=placeholder_token)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--env-file",
                    str(env_file),
                    "--check-config",
                    "--require-token",
                ],
                cwd=SCRIPT_DIR.parent,
                env=scrubbed_env(),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["valid"])
        self.assertTrue(report["token_present"])
        self.assertEqual(report["token_value_redacted"], "<present>")
        self.assertEqual(report["token_rotation_attestation_value_redacted"], "<missing>")
        self.assertIn("bot_token_rotation_attestation_missing", report["blockers"])
        self.assertNotIn(placeholder_token, result.stdout)
        self.assertNotIn(placeholder_token, result.stderr)

    def test_present_token_missing_rotation_is_sole_blocker_when_dependency_exists(self) -> None:
        placeholder_token = "unit-test-placeholder-token"
        with tempfile.TemporaryDirectory() as tmp:
            env_file = write_env(Path(tmp) / "discord-bot.env", token=placeholder_token)
            with (
                mock.patch.dict(os.environ, scrubbed_env(), clear=True),
                mock.patch.object(
                    discord_beta_bridge,
                    "discord_dependency_available",
                    return_value=(True, "discord.py unit-test"),
                ),
            ):
                report = check_config(env_file, require_token=True)

        rendered = json.dumps(report, sort_keys=True)
        self.assertFalse(report["valid"])
        self.assertEqual(report["blockers"], ["bot_token_rotation_attestation_missing"])
        self.assertTrue(report["discord_py_available"])
        self.assertNotIn(placeholder_token, rendered)

    def test_present_rotated_token_requires_discord_dependency_without_importing_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = write_env(
                Path(tmp) / "discord-bot.env",
                token="unit-test-placeholder-token",
                rotated_token_at="2026-06-07T00:00:00Z",
            )
            active_state = Path(tmp) / "active-notice.json"
            with (
                mock.patch.dict(
                    os.environ,
                    scrubbed_env({ACTIVE_NOTICE_STATE_ENV: str(active_state)}),
                    clear=True,
                ),
                mock.patch.object(
                    discord_beta_bridge,
                    "discord_dependency_available",
                    return_value=(False, "discord module not importable"),
                ),
            ):
                report = check_config(env_file)

        self.assertFalse(report["valid"])
        self.assertTrue(report["token_present"])
        self.assertTrue(report["token_rotation_required"])
        self.assertTrue(report["token_rotation_attestation_valid"])
        self.assertTrue(report["discord_py_required"])
        self.assertFalse(report["discord_py_available"])
        self.assertIn("discord_py_missing", report["blockers"])
        self.assertNotIn("bot_token_rotation_attestation", " ".join(report["blockers"]))

    def test_rotated_token_and_dependency_mock_allow_run_preflight_without_leaking_token(self) -> None:
        placeholder_token = "unit-test-placeholder-token"
        with tempfile.TemporaryDirectory() as tmp:
            env_file = write_env(
                Path(tmp) / "discord-bot.env",
                token=placeholder_token,
                rotated_token_at="2026-06-07T00:00:00Z",
            )
            with (
                mock.patch.dict(os.environ, scrubbed_env(), clear=True),
                mock.patch.object(
                    discord_beta_bridge,
                    "discord_dependency_available",
                    return_value=(True, "discord.py unit-test"),
                ),
            ):
                report = check_config(env_file, require_token=True)

        rendered = json.dumps(report, sort_keys=True)
        self.assertTrue(report["valid"], rendered)
        self.assertTrue(report["token_rotation_attestation_valid"])
        self.assertTrue(report["discord_py_required"])
        self.assertTrue(report["discord_py_available"])
        self.assertNotIn(placeholder_token, rendered)

    def test_present_token_rejects_stale_rotation_attestation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = write_env(
                Path(tmp) / "discord-bot.env",
                token="unit-test-placeholder-token",
                rotated_token_at="2026-06-06T23:59:59Z",
            )
            with mock.patch.dict(os.environ, scrubbed_env(), clear=True):
                report = check_config(env_file)

        self.assertFalse(report["valid"])
        self.assertIn("bot_token_rotation_attestation_before_required_floor", report["blockers"])
        self.assertEqual(report["token_rotation_attestation_value_redacted"], "<present>")

    def test_check_config_redacts_token_from_environment_without_leaking(self) -> None:
        placeholder_token = "unit-test-env-token-value"
        with tempfile.TemporaryDirectory() as tmp:
            env_file = write_env(Path(tmp) / "discord-bot.env")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--env-file", str(env_file), "--check-config"],
                cwd=SCRIPT_DIR.parent,
                env=scrubbed_env({TOKEN_ENV: placeholder_token}),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(report["token_present"])
        self.assertEqual(report["token_value_redacted"], "<present>")
        self.assertNotIn(placeholder_token, result.stdout)
        self.assertNotIn(placeholder_token, result.stderr)

    def test_config_report_redaction_guard_fails_closed_on_token_value(self) -> None:
        placeholder_token = "unit-test-token-value"
        with self.assertRaisesRegex(RuntimeError, "bot token"):
            discord_beta_bridge.reject_token_leak(
                {"accidental": placeholder_token},
                {TOKEN_ENV: placeholder_token},
            )
        with self.assertRaisesRegex(RuntimeError, "bot token"):
            discord_beta_bridge.reject_token_leak(
                {"nested": {placeholder_token: "accidental"}},
                {TOKEN_ENV: placeholder_token},
            )

    def test_build_event_redacts_actor_and_forbidden_note(self) -> None:
        event = build_event(
            "issue",
            user_id=123456789012345678,
            issue_type="crash",
            note="bot_token=abc123",
            config={},
        )

        self.assertEqual(event["schema"], "obelisk.discord-beta-bridge-event.v1")
        self.assertEqual(event["event_type"], "issue")
        self.assertEqual(event["issue_type"], "crash")
        self.assertEqual(event["note"], "<redacted-forbidden-content>")
        self.assertFalse(event["raw_user_id_retained"])
        self.assertEqual(event["event_sink_semantics"], "metadata_only")
        self.assertTrue(event["communication_posture_only"])
        self.assertNotIn("123456789012345678", json.dumps(event))
        self.assertFalse(event["non_authorization"]["authorizes_discord_read"])
        self.assertFalse(event["non_authorization"]["authorizes_server_restart"])
        self.assertFalse(event["non_authorization"]["public_sdk_ready"])
        validate_metadata_only_event(event)

    def test_build_event_redacts_discord_token_shaped_note(self) -> None:
        shaped_token = f"{'A' * 24}.{'B' * 8}.{'C' * 32}"
        event = build_event(
            "issue",
            user_id=123,
            issue_type="other",
            note=f"synthetic compromised token {shaped_token}",
            config={},
        )

        rendered = json.dumps(event, sort_keys=True)
        self.assertEqual(event["note"], "<redacted-forbidden-content>")
        self.assertNotIn(shaped_token, rendered)

    def test_build_event_redacts_free_text_note_without_retaining_player_text(self) -> None:
        event = build_event(
            "issue",
            user_id=123,
            issue_type="other",
            note="My character is stuck near the blue obelisk.",
            config={},
        )

        rendered = json.dumps(event, sort_keys=True)
        self.assertEqual(event["note"], "<redacted-free-text>")
        self.assertFalse(event["raw_player_text_retained"])
        self.assertNotIn("My character", rendered)
        self.assertNotIn("blue obelisk", rendered)
        validate_metadata_only_event(event)

    def test_write_event_rejects_raw_fields_and_authorization_progress_aliases(self) -> None:
        event = build_event("status", user_id=123, config={})
        event["user_id"] = "123"
        event["counts_as_sdk_progress"] = True
        event["evidence"] = "approved"
        event["progress"] = 1
        event["non_authorization"]["counts_as_runtime_evidence"] = True

        with tempfile.TemporaryDirectory() as tmp:
            sink = Path(tmp) / "events.jsonl"
            with self.assertRaisesRegex(ValueError, "metadata-only"):
                write_event(event, sink)

            self.assertFalse(sink.exists())

    def test_write_event_accepts_generated_metadata_only_event(self) -> None:
        event = build_event("joined", user_id=123, map_name="TheIsland", config={})
        with tempfile.TemporaryDirectory() as tmp:
            sink = Path(tmp) / "events.jsonl"
            write_event(event, sink)
            rows = sink.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(rows), 1)
        persisted = json.loads(rows[0])
        self.assertEqual(persisted["event_sink_semantics"], "metadata_only")
        self.assertTrue(persisted["redacted_metadata_only"])
        self.assertNotIn("user_id", persisted)

    def test_new_tester_milestone_events_are_metadata_only(self) -> None:
        in_server = build_event("in_server", user_id=123, map_name="Genesis2", config={})
        cluster_transfer = build_event(
            "cluster_transfer",
            user_id=123,
            note="steam_id=76561198000000000",
            config={},
        )

        self.assertEqual(in_server["event_type"], "in_server")
        self.assertEqual(in_server["map"], "Genesis2")
        self.assertFalse(in_server["raw_user_id_retained"])
        self.assertTrue(in_server["communication_posture_only"])
        validate_metadata_only_event(in_server)
        self.assertEqual(cluster_transfer["event_type"], "cluster_transfer")
        self.assertEqual(cluster_transfer["note"], "<redacted-forbidden-content>")
        self.assertFalse(cluster_transfer["non_authorization"]["counts_as_runtime_evidence"])
        validate_metadata_only_event(cluster_transfer)

    def test_beta_control_components_map_to_redacted_events(self) -> None:
        components = beta_control_components()
        custom_ids = [
            component["custom_id"]
            for row in components
            for component in row["components"]
        ]
        action_map = beta_control_action_map(components)
        action_by_id = {item["custom_id"]: item for item in action_map}

        self.assertIn("obelisk_beta:ready", custom_ids)
        self.assertIn("obelisk_beta:started", custom_ids)
        self.assertIn("obelisk_beta:loading", custom_ids)
        self.assertIn("obelisk_beta:in_server:Genesis2", custom_ids)
        self.assertIn("obelisk_beta:logged_out", custom_ids)
        self.assertIn("obelisk_beta:cluster_transfer", custom_ids)
        self.assertIn("obelisk_beta:status_summary", custom_ids)
        self.assertIn("obelisk_beta:joined:TheIsland", custom_ids)
        self.assertIn("obelisk_beta:logout_ready", custom_ids)
        self.assertEqual(set(custom_ids), set(action_by_id))
        self.assertEqual(action_by_id["obelisk_beta:started"]["event_type"], "started")
        self.assertEqual(action_by_id["obelisk_beta:loading"]["tester_status"], "loading")
        self.assertEqual(action_by_id["obelisk_beta:in_server:Genesis2"]["event_type"], "in_server")
        self.assertEqual(action_by_id["obelisk_beta:in_server:Genesis2"]["map"], "Genesis2")
        self.assertTrue(action_by_id["obelisk_beta:cluster_transfer"]["tester_milestone"])
        self.assertFalse(action_by_id["obelisk_beta:cluster_transfer"]["creates_channel_message"])
        self.assertFalse(action_by_id["obelisk_beta:cluster_transfer"]["claims_readiness"])
        self.assertEqual(action_by_id["obelisk_beta:ready"]["event_type"], "ready")
        self.assertEqual(action_by_id["obelisk_beta:joined:Genesis2"]["map"], "Genesis2")
        self.assertEqual(action_by_id["obelisk_beta:issue:crash"]["issue_type"], "crash")
        self.assertTrue(action_by_id["obelisk_beta:status_summary"]["summary_only"])
        self.assertFalse(action_by_id["obelisk_beta:status_summary"]["writes_event"])
        self.assertFalse(action_by_id["obelisk_beta:status_summary"]["creates_channel_message"])
        self.assertFalse(action_by_id["obelisk_beta:status_summary"]["updates_operational_message"])
        self.assertFalse(action_by_id["obelisk_beta:status_summary"]["claims_evidence"])
        self.assertFalse(action_by_id["obelisk_beta:status_summary"]["claims_progress"])
        self.assertFalse(action_by_id["obelisk_beta:status_summary"]["claims_readiness"])
        self.assertEqual(
            action_by_id["obelisk_beta:status_summary"]["response_mode"],
            "ephemeral_local_event_summary",
        )
        self.assertFalse(action_by_id["obelisk_beta:ready"]["raw_user_id_retained"])
        self.assertEqual(
            action_by_id["obelisk_beta:ready"]["event_sink_semantics"],
            "metadata_only",
        )
        joined = parse_beta_control_custom_id("obelisk_beta:joined:TheIsland")
        in_server = parse_beta_control_custom_id("obelisk_beta:in_server:TheIsland")
        logout = parse_beta_control_custom_id("obelisk_beta:logout_ready")
        transfer = parse_beta_control_custom_id("obelisk_beta:cluster_transfer")
        status_summary = parse_beta_control_custom_id("obelisk_beta:status_summary")
        workflow = beta_tester_status_workflow(components)

        self.assertEqual(joined["event_type"], "joined")
        self.assertEqual(joined["map_name"], "TheIsland")
        self.assertEqual(in_server["event_type"], "in_server")
        self.assertEqual(in_server["tester_status"], "in_server")
        self.assertEqual(logout["event_type"], "logout_ready")
        self.assertIn("Mantente dentro", logout["response"])
        self.assertEqual(transfer["event_type"], "cluster_transfer")
        self.assertIn("coordinacion solamente", transfer["response"])
        self.assertEqual(status_summary["event_type"], "status")
        self.assertTrue(status_summary["summary_only"])
        self.assertEqual(workflow["schema"], discord_beta_bridge.TESTER_STATUS_WORKFLOW_SCHEMA)
        self.assertEqual(
            workflow["tester_reportable_states"],
            ["started", "loading", "in_server", "logged_out", "cluster_transfer"],
        )
        self.assertIn("obelisk_beta:in_server:Ragnarok", workflow["status_custom_ids"])
        self.assertIn("obelisk_beta:cluster_transfer", workflow["status_custom_ids"])
        self.assertEqual(workflow["status_summary_button_custom_id"], "obelisk_beta:status_summary")
        self.assertTrue(workflow["single_operational_message_required"])
        self.assertTrue(workflow["active_notice_state_required_for_beta_controls"])
        self.assertFalse(workflow["button_interactions_create_channel_messages"])
        self.assertFalse(workflow["button_events_claim_readiness"])
        self.assertFalse(workflow["status_summary_button_writes_event"])
        self.assertEqual(workflow["status_summary_response_mode"], "ephemeral_local_event_summary")
        self.assertFalse(workflow["status_summary_reads_discord"])
        self.assertFalse(workflow["status_summary_sends_discord"])
        self.assertFalse(workflow["status_summary_creates_channel_message"])
        self.assertFalse(workflow["status_summary_claims_readiness"])
        assert_discord_beta_non_promotion(self, workflow["discord_beta_non_promotion"])
        self.assertTrue(workflow["cluster_transfer_is_coordination_status_only"])
        self.assertFalse(workflow["counts_as_approved_runtime_evidence"])
        self.assertFalse(workflow["non_authorization"]["counts_as_sdk_progress"])

    def test_button_interaction_writes_only_redacted_local_event_and_ephemeral_ack(self) -> None:
        raw_user_id = "123456789012345678"
        with tempfile.TemporaryDirectory() as tmp:
            sink = Path(tmp) / "events.jsonl"
            result = handle_beta_control_interaction(
                "obelisk_beta:in_server:Genesis2",
                user_id=raw_user_id,
                config={discord_beta_bridge.SALT_ENV: "unit-test-salt"},
                event_sink=sink,
            )
            rows = sink.read_text(encoding="utf-8").splitlines()

        rendered = json.dumps(result, sort_keys=True)
        self.assertEqual(result["schema"], BUTTON_INTERACTION_RESULT_SCHEMA)
        self.assertEqual(result["custom_id"], "obelisk_beta:in_server:Genesis2")
        self.assertEqual(result["event_type"], "in_server")
        self.assertEqual(result["map"], "Genesis2")
        self.assertTrue(result["writes_event"])
        self.assertTrue(result["local_event_written"])
        self.assertEqual(len(rows), 1)
        persisted = json.loads(rows[0])
        self.assertEqual(persisted, result["local_event"])
        self.assertEqual(persisted["event_type"], "in_server")
        self.assertEqual(persisted["map"], "Genesis2")
        self.assertTrue(result["ephemeral_acknowledgement"])
        self.assertEqual(result["response_mode"], "ephemeral_ack_and_local_event_write")
        self.assertFalse(result["creates_channel_message"])
        self.assertFalse(result["creates_followup_message"])
        self.assertFalse(result["updates_operational_message"])
        self.assertFalse(result["reads_discord"])
        self.assertFalse(result["sends_discord"])
        self.assertFalse(result["uses_network"])
        self.assertFalse(result["uses_webhook"])
        self.assertFalse(result["retains_raw_user_id"])
        self.assertFalse(result["retains_raw_player_text"])
        self.assertFalse(result["retains_secret_values"])
        self.assertFalse(result["claims_evidence"])
        self.assertFalse(result["claims_progress"])
        self.assertFalse(result["claims_readiness"])
        self.assertFalse(result["discord_authorized"])
        self.assertFalse(result["counts_as_sdk_progress"])
        self.assertFalse(result["counts_as_readiness"])
        self.assertFalse(result["non_authorization"]["counts_as_sdk_progress"])
        assert_discord_beta_non_promotion(self, result["discord_beta_non_promotion"])
        self.assertNotIn(raw_user_id, rendered)
        self.assertNotIn("player text", rendered.lower())
        validate_metadata_only_button_interaction_result(result)

    def test_status_summary_button_reads_local_sink_without_appending_event(self) -> None:
        raw_user_id = "123456789012345678"
        with tempfile.TemporaryDirectory() as tmp:
            sink = Path(tmp) / "events.jsonl"
            config = {discord_beta_bridge.SALT_ENV: "unit-test-salt"}
            write_event(build_event("started", user_id=raw_user_id, config=config), sink)
            before = sink.read_text(encoding="utf-8").splitlines()
            result = handle_beta_control_interaction(
                "obelisk_beta:status_summary",
                user_id=raw_user_id,
                config=config,
                event_sink=sink,
            )
            after = sink.read_text(encoding="utf-8").splitlines()

        rendered = json.dumps(result, sort_keys=True)
        self.assertEqual(result["schema"], BUTTON_INTERACTION_RESULT_SCHEMA)
        self.assertEqual(result["event_type"], "status")
        self.assertTrue(result["summary_only"])
        self.assertFalse(result["writes_event"])
        self.assertFalse(result["local_event_written"])
        self.assertEqual(before, after)
        self.assertEqual(result["response_mode"], "ephemeral_local_event_summary")
        self.assertTrue(result["ephemeral_acknowledgement"])
        self.assertFalse(result["creates_channel_message"])
        self.assertFalse(result["creates_followup_message"])
        self.assertFalse(result["updates_operational_message"])
        self.assertFalse(result["reads_discord"])
        self.assertFalse(result["sends_discord"])
        self.assertFalse(result["uses_network"])
        self.assertFalse(result["claims_evidence"])
        self.assertFalse(result["claims_progress"])
        self.assertFalse(result["claims_readiness"])
        self.assertFalse(result["counts_as_sdk_progress"])
        self.assertFalse(result["stable_sdk_ready"])
        assert_discord_beta_non_promotion(self, result["discord_beta_non_promotion"])
        self.assertEqual(
            result["tester_status_summary"]["schema"],
            discord_beta_bridge.TESTER_STATUS_SUMMARY_SCHEMA,
        )
        self.assertTrue(result["tester_status_summary"]["summary_does_not_append_event_row"])
        self.assertIn("metadata redacted", result["acknowledgement_text"])
        self.assertIn("no evidencia", result["acknowledgement_text"])
        self.assertNotIn(raw_user_id, rendered)
        validate_metadata_only_button_interaction_result(result)

    def test_button_interaction_validation_rejects_channel_or_progress_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = Path(tmp) / "events.jsonl"
            result = handle_beta_control_interaction(
                "obelisk_beta:cluster_transfer",
                user_id=123,
                config={},
                event_sink=sink,
            )

        result["creates_channel_message"] = True
        result["counts_as_sdk_progress"] = True
        result["raw_player_text"] = "tester said a private thing"

        with self.assertRaisesRegex(ValueError, "metadata-only"):
            validate_metadata_only_button_interaction_result(result)

    def test_emit_test_event_keeps_non_claim_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = write_env(Path(tmp) / "discord-bot.env")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--env-file",
                    str(env_file),
                    "--emit-test-event",
                    "ready",
                    "--user-id",
                    "123",
                    "--map",
                    "Ragnarok",
                ],
                cwd=SCRIPT_DIR.parent,
                env=scrubbed_env(),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        event = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(event["event_type"], "ready")
        self.assertEqual(event["map"], "Ragnarok")
        self.assertTrue(event["redacted_metadata_only"])
        self.assertEqual(event["event_sink_semantics"], "metadata_only")
        self.assertFalse(event["non_authorization"]["authorizes_rcon"])
        self.assertFalse(event["non_authorization"]["counts_as_sdk_progress"])

    def test_bot_notice_dry_run_uses_expected_channel_without_webhook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = write_env(
                Path(tmp) / "discord-bot.env",
                token="unit-test-placeholder-token",
                rotated_token_at="2026-06-07T00:00:00Z",
            )
            active_state = Path(tmp) / "active-notice.json"
            with (
                mock.patch.dict(
                    os.environ,
                    scrubbed_env({ACTIVE_NOTICE_STATE_ENV: str(active_state)}),
                    clear=True,
                ),
                mock.patch.object(
                    discord_beta_bridge,
                    "discord_dependency_available",
                    return_value=(True, "discord.py unit-test"),
                ),
            ):
                report = send_bot_notice(
                    env_file,
                    content="@everyone Prueba beta Obelisk: entrad a Ragnarok para validar ciclo de sesion.",
                    dry_run=True,
                    confirmed_send=False,
                    with_beta_controls=True,
                    update_active_notice=True,
                )

        self.assertEqual(report["schema"], BOT_NOTICE_SCHEMA)
        self.assertEqual(report["channel_id"], EXPECTED_CHANNEL_ID)
        self.assertTrue(report["content_mentions_everyone"])
        self.assertTrue(report["webhook_deprecated"])
        self.assertTrue(report["webhook_real_sends_deprecated"])
        self.assertFalse(report["uses_webhook"])
        self.assertFalse(report["send_performed"])
        self.assertFalse(report["discord_sent"])
        self.assertEqual(report["discord_http_method"], "POST")
        self.assertEqual(report["discord_endpoint_kind"], "channel_message_create")
        self.assertEqual(report["allowed_mentions_parse"], ["everyone"])
        self.assertTrue(report["single_operational_message_required"])
        self.assertTrue(report["no_flood_single_message_enforced"])
        self.assertEqual(report["bidirectional_channel_id"], EXPECTED_CHANNEL_ID)
        self.assertEqual(report["bot_send_channel_id"], EXPECTED_CHANNEL_ID)
        self.assertEqual(report["tester_interaction_channel_id"], EXPECTED_CHANNEL_ID)
        self.assertEqual(report["operational_message_kind"], "single_active_beta_notice")
        self.assertTrue(report["active_notice_update_requested"])
        self.assertEqual(report["active_notice_state_path"], str(active_state))
        self.assertTrue(report["active_notice_state_required_for_beta_controls"])
        self.assertTrue(report["real_send_requires_active_notice_update"])
        self.assertTrue(report["real_send_requires_beta_controls"])
        self.assertTrue(report["single_editable_embed_required"])
        self.assertTrue(report["single_editable_embed"])
        self.assertEqual(report["embed_count"], 1)
        self.assertFalse(report["embed_claims_readiness"])
        self.assertFalse(report["active_notice_state_present"])
        self.assertTrue(report["would_create_new_message"])
        self.assertTrue(report["new_message_only_when_active_notice_state_missing"])
        self.assertTrue(report["existing_active_notice_updates_in_place"])
        self.assertFalse(report["button_interactions_create_channel_messages"])
        self.assertFalse(report["button_events_claim_readiness"])
        self.assertFalse(report["status_summary_creates_channel_message"])
        self.assertFalse(report["status_summary_updates_operational_message"])
        self.assertFalse(report["status_summary_claims_readiness"])
        self.assertTrue(report["embed_enabled"])
        self.assertTrue(report["button_controls_enabled"])
        self.assertTrue(report["button_control_metadata_locally_representable"])
        self.assertTrue(report["preserves_interactive_buttons"])
        self.assertEqual(report["status_summary_action_count"], 1)
        self.assertIn("obelisk_beta:started", report["component_custom_ids"])
        self.assertIn("obelisk_beta:loading", report["component_custom_ids"])
        self.assertIn("obelisk_beta:in_server:Genesis2", report["component_custom_ids"])
        self.assertIn("obelisk_beta:logged_out", report["component_custom_ids"])
        self.assertIn("obelisk_beta:cluster_transfer", report["component_custom_ids"])
        self.assertIn("obelisk_beta:logout_ready", report["component_custom_ids"])
        self.assertIn("obelisk_beta:status_summary", report["component_custom_ids"])
        self.assertIn("obelisk_beta:done", [item["custom_id"] for item in report["component_action_map"]])
        embed_metadata = report["operational_embed_metadata"]
        self.assertEqual(
            embed_metadata["schema"],
            discord_beta_bridge.OPERATIONAL_EMBED_METADATA_SCHEMA,
        )
        self.assertTrue(embed_metadata["single_editable_embed"])
        self.assertEqual(embed_metadata["button_action_count"], report["component_count"])
        self.assertEqual(embed_metadata["button_custom_ids"], report["component_custom_ids"])
        self.assertIn("obelisk_beta:issue:crash", embed_metadata["button_custom_ids"])
        self.assertFalse(embed_metadata["status_summary_writes_event"])
        self.assertFalse(embed_metadata["button_interactions_create_channel_messages"])
        self.assertFalse(embed_metadata["embed_claims_readiness"])
        workflow = report["tester_status_workflow"]
        self.assertEqual(workflow["schema"], discord_beta_bridge.TESTER_STATUS_WORKFLOW_SCHEMA)
        self.assertIn("obelisk_beta:cluster_transfer", workflow["status_custom_ids"])
        self.assertEqual(workflow["status_summary_button_custom_id"], "obelisk_beta:status_summary")
        self.assertFalse(workflow["status_summary_button_writes_event"])
        self.assertFalse(workflow["counts_as_runtime_evidence"])
        editable = report["editable_notice_workflow"]
        self.assertEqual(editable["schema"], discord_beta_bridge.EDITABLE_NOTICE_WORKFLOW_SCHEMA)
        self.assertTrue(editable["single_operational_message_required"])
        self.assertTrue(editable["active_notice_state_required_for_beta_controls"])
        self.assertTrue(editable["no_flood_single_message_enforced"])
        self.assertTrue(editable["dry_run_required_before_real_send"])
        self.assertTrue(editable["dry_run_receipt_required_for_real_send"])
        self.assertTrue(editable["new_message_only_when_active_notice_state_missing"])
        self.assertFalse(editable["button_interactions_create_channel_messages"])
        self.assertFalse(editable["status_summary_creates_channel_message"])
        policy = report["operational_message_policy"]
        self.assertEqual(policy["schema"], discord_beta_bridge.OPERATIONAL_MESSAGE_POLICY_SCHEMA)
        self.assertEqual(policy["workflow"], "single_active_beta_notice")
        self.assertTrue(policy["single_operational_message_required"])
        self.assertTrue(policy["no_flood_single_message_enforced"])
        self.assertTrue(policy["dry_run_required_before_real_send"])
        self.assertTrue(policy["dry_run_receipt_required_for_real_send"])
        self.assertTrue(policy["active_notice_update_requested"])
        self.assertFalse(policy["status_summary_creates_channel_message"])
        self.assertFalse(policy["button_events_claim_readiness"])
        self.assertEqual(editable["missing_active_notice_http_method"], "POST")
        self.assertEqual(editable["existing_active_notice_http_method"], "PATCH")
        self.assertFalse(editable["send_performed_by_dry_run"])
        self.assertTrue(report["dry_run_required_before_real_send"])
        self.assertTrue(report["dry_run_receipt_required_for_real_send"])
        self.assertEqual(report["dry_run_receipt_schema"], discord_beta_bridge.DRY_RUN_RECEIPT_SCHEMA)
        self.assertTrue(report["dry_run_receipt"].startswith("obelisk-beta-dry-run:"))
        self.assertFalse(report["dry_run_receipt_validated"])
        self.assertEqual(
            report["dry_run_receipt_inputs"]["discord_endpoint_kind"],
            "channel_message_create",
        )
        self.assertEqual(
            report["dry_run_receipt_inputs"]["operational_embed_metadata"]["button_custom_ids"],
            report["component_custom_ids"],
        )
        self.assertFalse(report["non_authorization"]["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["non_authorization"]["counts_as_sdk_progress"])
        self.assertEqual(
            report["operational_message_style"],
            discord_beta_bridge.SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE,
        )
        self.assertTrue(report["single_updated_embed_buttons_message_preferred"])
        self.assertTrue(report["edit_existing_message_when_active_notice_state_present"])
        self.assertTrue(report["post_only_when_active_notice_state_missing"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["stable_sdk_ready"])
        assert_discord_beta_non_promotion(self, report["discord_beta_non_promotion"])
        assert_discord_beta_non_promotion(
            self,
            report["dry_run_receipt_inputs"]["discord_beta_non_promotion"],
        )

    def test_operational_embed_metadata_lists_button_actions_without_evidence_claims(self) -> None:
        metadata = beta_operational_embed_metadata()

        self.assertEqual(
            metadata["schema"],
            discord_beta_bridge.OPERATIONAL_EMBED_METADATA_SCHEMA,
        )
        self.assertTrue(metadata["single_operational_message_required"])
        self.assertTrue(metadata["single_editable_embed_required"])
        self.assertTrue(metadata["single_editable_embed"])
        self.assertEqual(metadata["embed_count"], 1)
        self.assertEqual(metadata["button_action_count"], len(metadata["button_action_map"]))
        self.assertIn("obelisk_beta:joined:Genesis2", metadata["button_custom_ids"])
        self.assertIn("obelisk_beta:issue:other", metadata["button_custom_ids"])
        status_summary = [
            item
            for item in metadata["button_action_map"]
            if item["custom_id"] == "obelisk_beta:status_summary"
        ]
        self.assertEqual(len(status_summary), 1)
        self.assertFalse(status_summary[0]["writes_event"])
        self.assertEqual(
            status_summary[0]["response_mode"],
            "ephemeral_local_event_summary",
        )
        self.assertFalse(metadata["button_interactions_create_channel_messages"])
        self.assertFalse(metadata["button_events_claim_evidence"])
        self.assertFalse(metadata["counts_as_sdk_progress"])
        self.assertFalse(metadata["stable_sdk_ready"])
        assert_discord_beta_non_promotion(self, metadata["discord_beta_non_promotion"])

    def test_bot_notice_beta_controls_require_active_notice_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = write_env(Path(tmp) / "discord-bot.env")
            with mock.patch.dict(os.environ, scrubbed_env(), clear=True):
                with self.assertRaisesRegex(SystemExit, "--update-active-notice"):
                    send_bot_notice(
                        env_file,
                        content="@everyone Prueba beta Obelisk.",
                        dry_run=True,
                        confirmed_send=False,
                        with_beta_controls=True,
                        update_active_notice=False,
                    )

    def test_bot_notice_rejects_real_send_without_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = write_env(
                Path(tmp) / "discord-bot.env",
                token="unit-test-placeholder-token",
                rotated_token_at="2026-06-07T00:00:00Z",
            )
            with (
                mock.patch.dict(os.environ, scrubbed_env(), clear=True),
                mock.patch.object(
                    discord_beta_bridge,
                    "discord_dependency_available",
                    return_value=(True, "discord.py unit-test"),
                ),
            ):
                with self.assertRaisesRegex(SystemExit, "--confirm-approved-send"):
                    send_bot_notice(
                        env_file,
                        content="@everyone Entrad a Ragnarok para prueba beta.",
                        dry_run=False,
                        confirmed_send=False,
                    )

    def test_bot_notice_confirmed_send_requires_reviewed_dry_run_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = write_env(
                Path(tmp) / "discord-bot.env",
                token="unit-test-placeholder-token",
                rotated_token_at="2026-06-07T00:00:00Z",
            )
            active_state = Path(tmp) / "active-notice.json"
            with (
                mock.patch.dict(
                    os.environ,
                    scrubbed_env({ACTIVE_NOTICE_STATE_ENV: str(active_state)}),
                    clear=True,
                ),
                mock.patch.object(
                    discord_beta_bridge,
                    "discord_dependency_available",
                    return_value=(True, "discord.py unit-test"),
                ),
                mock.patch.object(discord_beta_bridge.urllib.request, "urlopen") as urlopen,
            ):
                with self.assertRaisesRegex(SystemExit, "--dry-run-receipt"):
                    send_bot_notice(
                        env_file,
                        content="@everyone Entrad a Ragnarok para prueba beta Obelisk.",
                        dry_run=False,
                        confirmed_send=True,
                        with_beta_controls=True,
                        update_active_notice=True,
                    )

            self.assertFalse(urlopen.called)
            self.assertFalse(active_state.exists())

    def test_bot_notice_rejects_plain_real_send_to_prevent_flood(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = write_env(
                Path(tmp) / "discord-bot.env",
                token="unit-test-placeholder-token",
                rotated_token_at="2026-06-07T00:00:00Z",
            )
            with (
                mock.patch.dict(os.environ, scrubbed_env(), clear=True),
                mock.patch.object(
                    discord_beta_bridge,
                    "discord_dependency_available",
                    return_value=(True, "discord.py unit-test"),
                ),
                mock.patch.object(discord_beta_bridge.urllib.request, "urlopen") as urlopen,
            ):
                with self.assertRaisesRegex(SystemExit, "--update-active-notice"):
                    send_bot_notice(
                        env_file,
                        content="@everyone Entrad a Ragnarok para prueba beta Obelisk.",
                        dry_run=False,
                        confirmed_send=True,
                    )

            self.assertFalse(urlopen.called)

    def test_bot_notice_rejects_secrets_and_readiness_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = write_env(
                Path(tmp) / "discord-bot.env",
                token="unit-test-placeholder-token",
                rotated_token_at="2026-06-07T00:00:00Z",
            )
            with (
                mock.patch.dict(os.environ, scrubbed_env(), clear=True),
                mock.patch.object(
                    discord_beta_bridge,
                    "discord_dependency_available",
                    return_value=(True, "discord.py unit-test"),
                ),
            ):
                with self.assertRaisesRegex(ValueError, "forbidden"):
                    send_bot_notice(
                        env_file,
                        content="public SDK ready, token=abc123",
                        dry_run=True,
                        confirmed_send=False,
                    )

    def test_bot_notice_confirmed_send_posts_to_expected_channel_without_leaking_token(self) -> None:
        class FakeResponse:
            status = 200

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return b'{"id":"555"}'

        placeholder_token = "unit-test-placeholder-token"
        captured: dict[str, object] = {}

        def fake_urlopen(request: object, timeout: int = 0) -> FakeResponse:
            captured["url"] = request.full_url  # type: ignore[attr-defined]
            captured["headers"] = dict(request.header_items())  # type: ignore[attr-defined]
            captured["data"] = request.data  # type: ignore[attr-defined]
            captured["timeout"] = timeout
            return FakeResponse()

        with tempfile.TemporaryDirectory() as tmp:
            env_file = write_env(
                Path(tmp) / "discord-bot.env",
                token=placeholder_token,
                rotated_token_at="2026-06-07T00:00:00Z",
            )
            active_state = Path(tmp) / "active-notice.json"
            with (
                mock.patch.dict(
                    os.environ,
                    scrubbed_env({ACTIVE_NOTICE_STATE_ENV: str(active_state)}),
                    clear=True,
                ),
                mock.patch.object(
                    discord_beta_bridge,
                    "discord_dependency_available",
                    return_value=(True, "discord.py unit-test"),
                ),
                mock.patch.object(discord_beta_bridge.urllib.request, "urlopen", side_effect=fake_urlopen),
            ):
                dry_run_report = send_bot_notice(
                    env_file,
                    content="@everyone Entrad a Ragnarok para prueba beta Obelisk.",
                    dry_run=True,
                    confirmed_send=False,
                    with_beta_controls=True,
                    update_active_notice=True,
                )
                report = send_bot_notice(
                    env_file,
                    content="@everyone Entrad a Ragnarok para prueba beta Obelisk.",
                    dry_run=False,
                    confirmed_send=True,
                    with_beta_controls=True,
                    update_active_notice=True,
                    dry_run_receipt=dry_run_report["dry_run_receipt"],
                )
                active_state_exists = active_state.exists()
                active_state_payload = json.loads(active_state.read_text(encoding="utf-8"))

        self.assertEqual(
            captured["url"],
            f"https://discord.com/api/v10/channels/{EXPECTED_CHANNEL_ID}/messages",
        )
        self.assertNotIn("/api/webhooks/", str(captured["url"]))
        payload = json.loads(captured["data"].decode("utf-8"))  # type: ignore[union-attr]
        self.assertEqual(payload["allowed_mentions"], {"parse": ["everyone"]})
        self.assertIn("components", payload)
        self.assertIn("embeds", payload)
        self.assertEqual(report["discord_http_method"], "POST")
        self.assertTrue(report["single_operational_message_required"])
        self.assertTrue(report["active_notice_update_requested"])
        self.assertFalse(report["active_notice_state_present"])
        self.assertTrue(report["would_create_new_message"])
        self.assertEqual(report["active_message_id"], "555")
        self.assertTrue(active_state_exists)
        self.assertEqual(active_state_payload["message_id"], "555")
        self.assertTrue(active_state_payload["single_operational_message_required"])
        self.assertFalse(active_state_payload["counts_as_readiness"])
        self.assertEqual(report["allowed_mentions_parse"], ["everyone"])
        self.assertFalse(report["button_interactions_create_channel_messages"])
        self.assertFalse(report["status_summary_creates_channel_message"])
        self.assertFalse(report["embed_claims_readiness"])
        self.assertFalse(report["uses_webhook"])
        self.assertNotIn(placeholder_token, json.dumps(report, sort_keys=True))
        self.assertTrue(report["send_performed"])
        self.assertTrue(report["discord_sent"])
        self.assertTrue(report["dry_run_receipt_validated"])
        self.assertEqual(report["dry_run_receipt"], dry_run_report["dry_run_receipt"])
        self.assertEqual(report["http_status"], 200)

    def test_bot_notice_dry_run_active_update_previews_without_everyone_ping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = write_env(Path(tmp) / "discord-bot.env")
            active_state = Path(tmp) / "active-notice.json"
            active_state.write_text(
                json.dumps(
                    {
                        "schema": discord_beta_bridge.ACTIVE_NOTICE_STATE_SCHEMA,
                        "guild_id": EXPECTED_GUILD_ID,
                        "channel_id": EXPECTED_CHANNEL_ID,
                        "message_id": "999",
                        "source": "unit-test",
                        "updated_at_utc": "2026-06-07T00:00:00Z",
                        "redacted_metadata_only": True,
                        "communication_posture_only": True,
                        "non_authorization": dict(discord_beta_bridge.NON_AUTHORIZATION_FLAGS),
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.dict(
                os.environ,
                scrubbed_env({discord_beta_bridge.ACTIVE_NOTICE_STATE_ENV: str(active_state)}),
                clear=True,
            ):
                report = send_bot_notice(
                    env_file,
                    content="@everyone Actualizacion beta Obelisk.\nRecordatorio para @everyone sin repetir ping.",
                    dry_run=True,
                    confirmed_send=False,
                    with_beta_controls=True,
                    update_active_notice=True,
                )

        self.assertTrue(report["dry_run"])
        self.assertFalse(report["send_performed"])
        self.assertTrue(report["updates_existing_message"])
        self.assertEqual(report["active_message_id"], "999")
        self.assertTrue(report["single_operational_message_required"])
        self.assertEqual(report["operational_message_kind"], "single_active_beta_notice")
        self.assertTrue(report["active_notice_state_required_for_beta_controls"])
        self.assertFalse(report["content_mentions_everyone"])
        self.assertEqual(report["requested_content_mentions_everyone"], True)
        self.assertEqual(report["allowed_mentions_parse"], [])
        self.assertEqual(report["discord_http_method"], "PATCH")
        self.assertEqual(report["discord_endpoint_kind"], "channel_message_update")
        self.assertNotIn("@everyone", report["content"])
        self.assertTrue(report["mention_everyone_suppressed_on_update"])
        self.assertTrue(report["interactive_buttons_preserved_on_update"])
        self.assertFalse(report["button_interactions_create_channel_messages"])
        self.assertFalse(report["status_summary_creates_channel_message"])
        self.assertFalse(report["status_summary_claims_readiness"])
        self.assertTrue(report["editable_notice_workflow"]["updates_existing_message"])
        self.assertFalse(report["editable_notice_workflow"]["would_create_new_message"])
        self.assertTrue(
            report["editable_notice_workflow"]["repeat_everyone_mentions_suppressed_on_update"]
        )
        self.assertIn("obelisk_beta:cluster_transfer", report["tester_status_workflow"]["status_custom_ids"])
        self.assertEqual(
            report["tester_status_workflow"]["status_summary_button_custom_id"],
            "obelisk_beta:status_summary",
        )
        self.assertFalse(report["would_create_new_message"])
        self.assertFalse(report["operational_message_policy"]["would_create_new_message"])
        self.assertTrue(report["operational_message_policy"]["updates_existing_message"])
        self.assertEqual(
            report["operational_message_style"],
            discord_beta_bridge.SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE,
        )
        self.assertTrue(report["single_updated_embed_buttons_message_preferred"])
        self.assertTrue(report["edit_existing_message_when_active_notice_state_present"])
        self.assertTrue(report["operational_message_policy"]["single_updated_embed_buttons_message_preferred"])
        self.assertTrue(report["redacted_metadata_only"])
        self.assertEqual(report["event_sink_semantics"], "metadata_only")
        self.assertFalse(report["non_authorization"]["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["non_authorization"]["counts_as_runtime_evidence"])
        assert_discord_beta_non_promotion(self, report["discord_beta_non_promotion"])

    def test_bot_notice_rejects_dangling_symlink_active_notice_before_post_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = write_env(Path(tmp) / "discord-bot.env")
            active_state = Path(tmp) / "active-notice.json"
            active_state.symlink_to(Path(tmp) / "missing-active-notice.json")
            with mock.patch.dict(
                os.environ,
                scrubbed_env({discord_beta_bridge.ACTIVE_NOTICE_STATE_ENV: str(active_state)}),
                clear=True,
            ):
                with self.assertRaisesRegex(SystemExit, "active notice state path rejected"):
                    send_bot_notice(
                        env_file,
                        content="@everyone Entrad a Ragnarok para prueba beta Obelisk.",
                        dry_run=True,
                        confirmed_send=False,
                        with_beta_controls=True,
                        update_active_notice=True,
                    )

    def test_bot_notice_updates_active_message_without_everyone_ping(self) -> None:
        class FakeResponse:
            status = 200

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return b'{"id":"999"}'

        placeholder_token = "unit-test-placeholder-token"
        captured: dict[str, object] = {}

        def fake_urlopen(request: object, timeout: int = 0) -> FakeResponse:
            captured["url"] = request.full_url  # type: ignore[attr-defined]
            captured["method"] = request.get_method()  # type: ignore[attr-defined]
            captured["data"] = request.data  # type: ignore[attr-defined]
            return FakeResponse()

        with tempfile.TemporaryDirectory() as tmp:
            env_file = write_env(
                Path(tmp) / "discord-bot.env",
                token=placeholder_token,
                rotated_token_at="2026-06-07T00:00:00Z",
            )
            active_state = Path(tmp) / "active-notice.json"
            active_state.write_text(
                json.dumps(
                    {
                        "schema": discord_beta_bridge.ACTIVE_NOTICE_STATE_SCHEMA,
                        "guild_id": EXPECTED_GUILD_ID,
                        "channel_id": EXPECTED_CHANNEL_ID,
                        "message_id": "999",
                        "source": "unit-test",
                        "updated_at_utc": "2026-06-07T00:00:00Z",
                        "redacted_metadata_only": True,
                        "communication_posture_only": True,
                        "non_authorization": dict(discord_beta_bridge.NON_AUTHORIZATION_FLAGS),
                    }
                ),
                encoding="utf-8",
            )
            with (
                mock.patch.dict(
                    os.environ,
                    scrubbed_env({discord_beta_bridge.ACTIVE_NOTICE_STATE_ENV: str(active_state)}),
                    clear=True,
                ),
                mock.patch.object(
                    discord_beta_bridge,
                    "discord_dependency_available",
                    return_value=(True, "discord.py unit-test"),
                ),
                mock.patch.object(discord_beta_bridge.urllib.request, "urlopen", side_effect=fake_urlopen),
            ):
                dry_run_report = send_bot_notice(
                    env_file,
                    content="@everyone Actualizacion beta Obelisk.\nRecordatorio para @everyone sin repetir ping.",
                    dry_run=True,
                    confirmed_send=False,
                    with_beta_controls=True,
                    update_active_notice=True,
                )
                report = send_bot_notice(
                    env_file,
                    content="@everyone Actualizacion beta Obelisk.\nRecordatorio para @everyone sin repetir ping.",
                    dry_run=False,
                    confirmed_send=True,
                    with_beta_controls=True,
                    update_active_notice=True,
                    dry_run_receipt=dry_run_report["dry_run_receipt"],
                )
                refreshed_state = json.loads(active_state.read_text(encoding="utf-8"))

        self.assertEqual(captured["method"], "PATCH")
        self.assertEqual(
            captured["url"],
            f"https://discord.com/api/v10/channels/{EXPECTED_CHANNEL_ID}/messages/999",
        )
        payload = json.loads(captured["data"].decode("utf-8"))  # type: ignore[union-attr]
        self.assertEqual(payload["allowed_mentions"], {"parse": []})
        self.assertNotIn("@everyone", payload["content"])
        self.assertIn("components", payload)
        self.assertIn("obelisk_beta:logout_ready", json.dumps(payload["components"]))
        self.assertFalse(report["content_mentions_everyone"])
        self.assertEqual(report["requested_content_mentions_everyone"], True)
        self.assertEqual(report["allowed_mentions_parse"], [])
        self.assertEqual(report["discord_http_method"], "PATCH")
        self.assertFalse(report["uses_webhook"])
        self.assertTrue(report["updates_existing_message"])
        self.assertFalse(report["creates_new_message"])
        self.assertFalse(report["would_create_new_message"])
        self.assertTrue(report["single_operational_message_required"])
        self.assertTrue(report["active_notice_state_required_for_beta_controls"])
        self.assertFalse(report["button_interactions_create_channel_messages"])
        self.assertFalse(report["status_summary_creates_channel_message"])
        self.assertFalse(report["embed_claims_readiness"])
        self.assertTrue(report["mention_everyone_suppressed_on_update"])
        self.assertTrue(report["interactive_buttons_preserved_on_update"])
        self.assertEqual(report["active_message_id"], "999")
        self.assertTrue(report["dry_run_receipt_validated"])
        self.assertEqual(report["dry_run_receipt"], dry_run_report["dry_run_receipt"])
        self.assertEqual(refreshed_state["message_id"], "999")
        self.assertEqual(refreshed_state["source"], "send_bot_notice")
        self.assertNotEqual(refreshed_state["updated_at_utc"], "2026-06-07T00:00:00Z")
        self.assertFalse(refreshed_state["non_authorization"]["counts_as_readiness"])

    def test_summarize_event_sink_reports_latest_tester_status_without_evidence_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = Path(tmp) / "events.jsonl"
            config = {discord_beta_bridge.SALT_ENV: "unit-test-salt"}
            first_user = "123456789012345678"
            second_user = "223456789012345678"
            third_user = "323456789012345678"
            write_event(build_event("started", user_id=first_user, config=config), sink)
            write_event(build_event("loading", user_id=first_user, config=config), sink)
            write_event(
                build_event("in_server", user_id=second_user, map_name="Genesis2", config=config),
                sink,
            )
            write_event(
                build_event(
                    "issue",
                    user_id=third_user,
                    issue_type="timeout",
                    note="still loading",
                    config=config,
                ),
                sink,
            )
            summary = summarize_event_sink(sink, recent_limit=3)

        rendered = json.dumps(summary, sort_keys=True)
        self.assertEqual(summary["schema"], EVENT_SUMMARY_SCHEMA)
        self.assertTrue(summary["event_sink_exists"])
        self.assertEqual(summary["valid_event_count"], 4)
        self.assertEqual(summary["invalid_event_count"], 0)
        self.assertEqual(summary["actor_alias_count"], 3)
        status_summary = summary["tester_status_summary"]
        self.assertEqual(status_summary["schema"], discord_beta_bridge.TESTER_STATUS_SUMMARY_SCHEMA)
        self.assertEqual(status_summary["status_summary_button_custom_id"], "obelisk_beta:status_summary")
        self.assertTrue(status_summary["single_operational_message_required"])
        self.assertFalse(status_summary["status_summary_button_writes_event"])
        self.assertEqual(status_summary["status_summary_response_mode"], "ephemeral_local_event_summary")
        self.assertFalse(status_summary["status_summary_reads_discord"])
        self.assertFalse(status_summary["status_summary_sends_discord"])
        self.assertFalse(status_summary["status_summary_creates_channel_message"])
        self.assertFalse(status_summary["status_summary_updates_operational_message"])
        self.assertFalse(status_summary["status_summary_claims_readiness"])
        self.assertTrue(status_summary["summary_does_not_append_event_row"])
        self.assertEqual(status_summary["active_tester_alias_count"], 2)
        counts = {item["event_type"]: item["count"] for item in summary["event_type_counts"]}
        self.assertEqual(counts["started"], 1)
        self.assertEqual(counts["loading"], 1)
        self.assertEqual(counts["in_server"], 1)
        self.assertEqual(counts["issue"], 1)
        latest_by_actor = summary["latest_event_by_actor"]
        self.assertEqual(len(latest_by_actor), 3)
        self.assertIn("loading", [item["event_type"] for item in latest_by_actor])
        self.assertIn("issue", [item["event_type"] for item in latest_by_actor])
        milestones = summary["latest_tester_milestone_by_actor"]
        self.assertEqual(len(milestones), 2)
        self.assertIn("in_server", [item["event_type"] for item in milestones])
        state_counts = {
            item["state"]: item["count"]
            for item in status_summary["state_counts"]
        }
        self.assertEqual(state_counts["loading"], 1)
        self.assertEqual(state_counts["in_server"], 1)
        map_counts = {
            item["map"]: item["count"]
            for item in status_summary["in_server_by_map"]
        }
        self.assertEqual(map_counts["Genesis2"], 1)
        rendered_status = format_tester_status_summary(summary)
        self.assertIn("Activos=2", rendered_status)
        self.assertIn("in_server=1", rendered_status)
        self.assertIn("Genesis2=1", rendered_status)
        self.assertIn("no evidencia", rendered_status)
        self.assertEqual(summary["attention_hint_count"], 2)
        self.assertIn(
            "review_redacted_issue_before_relying_on_tester",
            [item["hint"] for item in summary["attention_hints"]],
        )
        self.assertFalse(summary["discord_events_are_evidence"])
        self.assertTrue(summary["single_operational_message_required"])
        self.assertFalse(summary["status_summary_creates_channel_message"])
        self.assertFalse(summary["status_summary_claims_readiness"])
        self.assertFalse(summary["non_authorization"]["counts_as_approved_runtime_evidence"])
        self.assertFalse(summary["non_authorization"]["counts_as_sdk_progress"])
        self.assertEqual(summary["event_sink_semantics"], "metadata_only")
        self.assertTrue(summary["redacted_metadata_only"])
        self.assertNotIn(first_user, rendered)
        self.assertNotIn(second_user, rendered)
        self.assertNotIn(third_user, rendered)
        validate_metadata_only_event_summary(summary)

    def test_status_summary_validation_rejects_readiness_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = Path(tmp) / "events.jsonl"
            write_event(build_event("started", user_id=123, config={}), sink)
            summary = summarize_event_sink(sink)

        summary["tester_status_summary"]["status_summary_counts_as_readiness"] = True

        with self.assertRaisesRegex(ValueError, "authorization_progress_evidence_alias_not_false"):
            validate_metadata_only_event_summary(summary)

    def test_summarize_event_sink_accepts_legacy_missing_non_authorization_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = Path(tmp) / "events.jsonl"
            event = build_event("loading", user_id=123, config={})
            event["non_authorization"].pop("counts_as_readiness")
            with sink.open("w", encoding="utf-8") as handle:
                handle.write(json.dumps(event, sort_keys=True) + "\n")

            summary = summarize_event_sink(sink)

        self.assertEqual(summary["valid_event_count"], 1)
        self.assertEqual(summary["invalid_event_count"], 0)
        self.assertFalse(summary["recent_events"][0]["raw_user_id_retained"])
        self.assertFalse(summary["non_authorization"]["counts_as_readiness"])
        validate_metadata_only_event_summary(summary)

    def test_summarize_event_sink_keeps_invalid_rows_redacted_and_non_authorizing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = Path(tmp) / "events.jsonl"
            write_event(build_event("cluster_transfer", user_id=404, config={}), sink)
            with sink.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "schema": discord_beta_bridge.EVENT_SCHEMA,
                            "event_type": "joined",
                            "user_id": "76561198000000000",
                            "raw_user_id_retained": True,
                            "redacted_metadata_only": True,
                            "event_sink_semantics": "metadata_only",
                            "non_authorization": dict(discord_beta_bridge.NON_AUTHORIZATION_FLAGS),
                        }
                    )
                    + "\n"
                )
            summary = summarize_event_sink(sink)

        rendered = json.dumps(summary, sort_keys=True)
        self.assertEqual(summary["valid_event_count"], 1)
        self.assertEqual(summary["invalid_event_count"], 1)
        self.assertEqual(summary["invalid_rows"][0]["line_number"], 2)
        self.assertFalse(summary["invalid_rows"][0]["raw_line_retained"])
        self.assertIn("ValueError", summary["invalid_rows"][0]["reason"])
        self.assertIn("cluster_transfer", [item["event_type"] for item in summary["recent_events"]])
        self.assertEqual(summary["attention_hints"][0]["hint"], "confirm_target_map_before_runtime_window_instruction")
        self.assertFalse(summary["non_authorization"]["authorizes_discord_send"])
        self.assertFalse(summary["non_authorization"]["authorizes_server_restart"])
        self.assertNotIn("76561198000000000", rendered)
        validate_metadata_only_event_summary(summary)

    def test_summarize_events_cli_returns_nonzero_for_invalid_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = write_env(Path(tmp) / "discord-bot.env")
            sink = Path(tmp) / "events.jsonl"
            write_event(build_event("loading", user_id=123, config={}), sink)
            with sink.open("a", encoding="utf-8") as handle:
                handle.write('{"schema":"bad","raw_user_id_retained":true}\n')
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--env-file",
                    str(env_file),
                    "--summarize-events",
                    "--recent-limit",
                    "1",
                ],
                cwd=SCRIPT_DIR.parent,
                env=scrubbed_env({EVENT_SINK_ENV: str(sink)}),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        summary = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(summary["schema"], EVENT_SUMMARY_SCHEMA)
        self.assertEqual(summary["valid_event_count"], 1)
        self.assertEqual(summary["invalid_event_count"], 1)
        self.assertEqual(len(summary["recent_events"]), 1)
        self.assertFalse(summary["discord_events_are_evidence"])
        self.assertFalse(summary["non_authorization"]["counts_as_runtime_evidence"])


if __name__ == "__main__":
    unittest.main()
