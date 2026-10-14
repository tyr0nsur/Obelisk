#!/usr/bin/env python3
"""Validate the offline Discord beta bridge plan.

This checker never connects to Discord and never reads bot tokens. It exists so the
interactive beta-tester workflow stays structured, redacted, and non-authorizing before
any implementation is allowed to run.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import protected_paths


SCHEMA = "obelisk.discord-beta-bridge-plan-check.v1"
PLAN_SCHEMA = "obelisk.discord-beta-bridge-plan.v1"
ACTIVE_NOTICE_REUSE_POLICY_SCHEMA = (
    "obelisk.discord-beta-bridge-active-notice-reuse-policy.v1"
)
DISCORD_BETA_NON_PROMOTION_SCHEMA = "obelisk.discord-beta-bridge-non-promotion-boundary.v1"
TOKEN_ENV_VAR = "OBELISK_DISCORD_BOT_TOKEN"
ROTATED_TOKEN_AT_ENV_VAR = "OBELISK_DISCORD_BOT_TOKEN_ROTATED_AT_UTC"
EVENT_SINK = "local/discord-beta-bridge/events.jsonl"
CHANNEL = "obelisk-beta-testers"
BOT_CHANNEL_ID = "1513238083741683934"
LOCAL_BRIDGE_PYTHON = "local/discord-bridge-venv/bin/python"
BOT_CHANNEL_ENV_VAR = "OBELISK_DISCORD_BETA_CHANNEL_ID"
ACTIVE_NOTICE_STATE_ENV_VAR = "OBELISK_DISCORD_ACTIVE_NOTICE_STATE"
CONFIG_CHECK_COMMAND = (
    LOCAL_BRIDGE_PYTHON,
    "scripts/discord_beta_bridge.py",
    "--check-config",
    "--json",
    "--require-token",
)
BETA_NOTICE_REQUIRED_HELPER_ARGS = (
    "--send-beta-notice",
    "--with-beta-controls",
    "--update-active-notice",
)
STATUS_SUMMARY_CUSTOM_ID = "obelisk_beta:status_summary"
STATUS_SUMMARY_RESPONSE_MODE = "ephemeral_local_event_summary"
SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE = "single_updated_embed_buttons_operational_message"
BUTTON_INTERACTION_RESULT_SCHEMA = "obelisk.discord-beta-bridge-button-interaction-result.v1"
BETA_NOTICE_SEND_COMMAND = (
    LOCAL_BRIDGE_PYTHON,
    "scripts/discord_beta_bridge.py",
    *BETA_NOTICE_REQUIRED_HELPER_ARGS,
    "--json",
)
BETA_NOTICE_BUTTON_CUSTOM_IDS = (
    "obelisk_beta:started",
    "obelisk_beta:loading",
    "obelisk_beta:in_server:Ragnarok",
    "obelisk_beta:in_server:TheIsland",
    "obelisk_beta:in_server:Genesis2",
    "obelisk_beta:logged_out",
    "obelisk_beta:cluster_transfer",
    "obelisk_beta:ready",
    "obelisk_beta:logout_ready",
    "obelisk_beta:done",
    "obelisk_beta:joined:Ragnarok",
    "obelisk_beta:joined:TheIsland",
    "obelisk_beta:joined:Genesis2",
    "obelisk_beta:issue:cluster",
    "obelisk_beta:issue:timeout",
    "obelisk_beta:issue:crash",
    "obelisk_beta:issue:other",
    STATUS_SUMMARY_CUSTOM_ID,
)
BETA_NOTICE_BUTTON_ACTION_MAP = (
    {
        "custom_id": "obelisk_beta:started",
        "event_type": "started",
        "response_mode": "ephemeral_ack_and_local_event_write",
        "writes_event": True,
    },
    {
        "custom_id": "obelisk_beta:loading",
        "event_type": "loading",
        "response_mode": "ephemeral_ack_and_local_event_write",
        "writes_event": True,
    },
    {
        "custom_id": "obelisk_beta:in_server:Ragnarok",
        "event_type": "in_server",
        "map": "Ragnarok",
        "response_mode": "ephemeral_ack_and_local_event_write",
        "writes_event": True,
    },
    {
        "custom_id": "obelisk_beta:in_server:TheIsland",
        "event_type": "in_server",
        "map": "TheIsland",
        "response_mode": "ephemeral_ack_and_local_event_write",
        "writes_event": True,
    },
    {
        "custom_id": "obelisk_beta:in_server:Genesis2",
        "event_type": "in_server",
        "map": "Genesis2",
        "response_mode": "ephemeral_ack_and_local_event_write",
        "writes_event": True,
    },
    {
        "custom_id": "obelisk_beta:logged_out",
        "event_type": "logged_out",
        "response_mode": "ephemeral_ack_and_local_event_write",
        "writes_event": True,
    },
    {
        "custom_id": "obelisk_beta:cluster_transfer",
        "event_type": "cluster_transfer",
        "response_mode": "ephemeral_ack_and_local_event_write",
        "writes_event": True,
    },
    {
        "custom_id": "obelisk_beta:ready",
        "event_type": "ready",
        "response_mode": "ephemeral_ack_and_local_event_write",
        "writes_event": True,
    },
    {
        "custom_id": "obelisk_beta:logout_ready",
        "event_type": "logout_ready",
        "response_mode": "ephemeral_ack_and_local_event_write",
        "writes_event": True,
    },
    {
        "custom_id": "obelisk_beta:done",
        "event_type": "done",
        "response_mode": "ephemeral_ack_and_local_event_write",
        "writes_event": True,
    },
    {
        "custom_id": "obelisk_beta:joined:Ragnarok",
        "event_type": "joined",
        "map": "Ragnarok",
        "response_mode": "ephemeral_ack_and_local_event_write",
        "writes_event": True,
    },
    {
        "custom_id": "obelisk_beta:joined:TheIsland",
        "event_type": "joined",
        "map": "TheIsland",
        "response_mode": "ephemeral_ack_and_local_event_write",
        "writes_event": True,
    },
    {
        "custom_id": "obelisk_beta:joined:Genesis2",
        "event_type": "joined",
        "map": "Genesis2",
        "response_mode": "ephemeral_ack_and_local_event_write",
        "writes_event": True,
    },
    {
        "custom_id": "obelisk_beta:issue:cluster",
        "event_type": "issue",
        "issue_type": "cluster",
        "response_mode": "ephemeral_ack_and_local_event_write",
        "writes_event": True,
    },
    {
        "custom_id": "obelisk_beta:issue:timeout",
        "event_type": "issue",
        "issue_type": "timeout",
        "response_mode": "ephemeral_ack_and_local_event_write",
        "writes_event": True,
    },
    {
        "custom_id": "obelisk_beta:issue:crash",
        "event_type": "issue",
        "issue_type": "crash",
        "response_mode": "ephemeral_ack_and_local_event_write",
        "writes_event": True,
    },
    {
        "custom_id": "obelisk_beta:issue:other",
        "event_type": "issue",
        "issue_type": "other",
        "response_mode": "ephemeral_ack_and_local_event_write",
        "writes_event": True,
    },
    {
        "custom_id": STATUS_SUMMARY_CUSTOM_ID,
        "event_type": "status",
        "response_mode": STATUS_SUMMARY_RESPONSE_MODE,
        "writes_event": False,
    },
)
REQUIRED_COMMAND_IDS = (
    "status",
    "ready",
    "joined",
    "logout-ready",
    "issue",
    "done",
)
ALLOWED_PERMISSIONS = frozenset(
    (
        "View Channel",
        "Send Messages",
        "Read Message History",
        "Use Application Commands",
    )
)
FORBIDDEN_PERMISSIONS = frozenset(
    (
        "Administrator",
        "Manage Channels",
        "Manage Guild",
        "Manage Messages",
        "Manage Webhooks",
    )
)
FORBIDDEN_RE = re.compile(
    r"(?:https?://)?discord(?:app)?\.com/api/webhooks|webhook[_ -]?url|"
    r"(?:bot[_ -]?)?token\s*[:=]|secret\s*[:=]|unique[_ -]?net\s*[:=]|"
    r"steam[_ -]?id\s*[:=]|eos[_ -]?id\s*[:=]|ip(?:v4|v6)?\s*[:=]",
    re.IGNORECASE,
)
DISCORD_TOKEN_SHAPE_RE = re.compile(
    r"\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{20,}\b"
)
FALSEY_ALIAS_VALUES = frozenset(
    ("", "0", "false", "no", "none", "null", "n/a", "na", "blocked", "missing")
)
FORBIDDEN_EXACT_ALIAS_KEYS = frozenset(
    (
        "authorization",
        "authorized",
        "evidence",
        "progress",
        "readiness",
        "ready",
        "sdkevidence",
        "runtimeevidence",
        "approvedevidence",
        "approvedingameevidence",
    )
)
FORBIDDEN_ALIAS_KEY_RE = re.compile(
    r"(?:authori[sz]|discordauthori[sz]|liveopauthori[sz]|rcon|"
    r"server(?:start|stop|restart)|markerorenv|livelog|runtimecapture|"
    r"approvedruntimeevidence|runtimeevidence|approvedingameevidence|"
    r"countsas(?:approved)?(?:runtime)?evidence|countsas(?:sdk|p0|progress|readiness)|"
    r"(?:claims?|countsas)(?:public|runtime|sdk|p0|stable|pluginhub|publication)?readiness|"
    r"sdkp0progress|sdkprogress|p0progress|publicsdkready|runtimeready|"
    r"stablesdkready|stableclaim|pluginhubready|publicationready|"
    r"v1(?:completion|complete)|clearsapprovedruntimeevidencemissing)"
)
FALSE_NON_AUTHORIZATION_FLAGS = (
    "authorizes_discord_read",
    "authorizes_discord_send",
    "authorizes_rcon",
    "authorizes_server_start",
    "authorizes_server_stop",
    "authorizes_server_restart",
    "authorizes_marker_or_env_changes",
    "authorizes_live_log_reads",
    "authorizes_runtime_capture",
    "approves_live_actions",
    "counts_as_approved_runtime_evidence",
    "counts_as_runtime_evidence",
    "counts_as_sdk_progress",
    "counts_as_p0_progress",
    "counts_as_readiness",
    "counts_as_public_sdk_readiness",
    "counts_as_stable_sdk_readiness",
    "public_sdk_ready",
    "runtime_ready",
    "stable_sdk_ready",
    "plugin_hub_ready",
    "publication_ready",
)
FALSE_PRIVACY_FLAGS = (
    "raw_message_content_retention_allowed",
    "raw_in_game_chat_retention_allowed",
    "private_player_data_retention_allowed",
    "secret_or_webhook_retention_allowed",
    "steam_or_eos_id_retention_allowed",
    "ip_address_retention_allowed",
    "message_content_intent_required_by_default",
)
FALSE_EVENT_SINK_FLAGS = (
    "raw_discord_payload_retention_allowed",
    "raw_user_id_retention_allowed",
    "authorization_or_evidence_aliases_allowed",
    "event_sink_counts_as_evidence",
    "event_sink_counts_as_progress",
)
FALSE_LIVE_RUN_PREFLIGHT_FLAGS = (
    "discord_connection_allowed_by_plan_check",
    "discord_read_allowed_by_plan_check",
    "discord_send_allowed_by_plan_check",
    "token_value_output_allowed",
)
FALSE_LOCAL_OFFLINE_WORKFLOW_FLAGS = (
    "discord_connection_allowed_by_config_check",
    "discord_read_allowed_by_config_check",
    "discord_send_allowed_by_config_check",
    "token_value_output_allowed",
)
TRUE_NOTICE_SEND_PATH_FLAGS = (
    "bot_channel_required_for_real_send",
    "single_operational_message_required",
    "active_notice_state_required_for_beta_controls",
    "single_editable_notice_required",
    "single_editable_embed_required",
    "existing_active_notice_updates_in_place",
    "new_message_only_when_active_notice_state_missing",
    "single_updated_embed_buttons_message_preferred",
    "edit_existing_message_when_active_notice_state_present",
    "post_only_when_active_notice_state_missing",
    "repeat_everyone_mentions_suppressed_on_update",
    "interactive_buttons_required",
    "button_interactions_ephemeral_ack_only",
    "button_interactions_metadata_only",
    "button_interactions_write_local_redacted_events_only",
    "button_interactions_local_event_acknowledgement_only",
    "button_interactions_require_expected_channel",
    "button_interactions_validate_metadata_only_result",
    "with_beta_controls_required",
    "update_active_notice_required",
    "status_summary_button_required",
    "status_summary_ephemeral_response_only",
    "status_summary_uses_local_event_sink_only",
    "status_summary_metadata_only",
    "confirm_approved_send_flag_required_for_real_send",
    "webhook_deprecated",
    "webhook_fail_closed_for_real_sends",
)
FALSE_NOTICE_SEND_PATH_FLAGS = (
    "uses_webhook",
    "webhook_outbound_only",
    "webhook_real_send_allowed",
    "webhook_fallback_allowed",
    "webhook_send_path_enabled",
    "status_summary_button_writes_event",
    "status_summary_reads_discord",
    "status_summary_sends_discord",
    "status_summary_creates_channel_message",
    "status_summary_updates_operational_message",
    "status_summary_creates_event",
    "status_summary_claims_evidence",
    "status_summary_claims_progress",
    "status_summary_claims_readiness",
    "status_summary_counts_as_approved_runtime_evidence",
    "status_summary_counts_as_runtime_evidence",
    "status_summary_counts_as_sdk_progress",
    "status_summary_counts_as_p0_progress",
    "status_summary_counts_as_readiness",
    "discord_or_beta_interactions_count_as_approved_runtime_evidence",
    "discord_or_beta_interactions_count_as_runtime_evidence",
    "discord_or_beta_interactions_count_as_sdk_progress",
    "discord_or_beta_interactions_count_as_p0_progress",
    "discord_or_beta_interactions_count_as_public_sdk_readiness",
    "discord_or_beta_interactions_count_as_stable_sdk_readiness",
    "discord_or_beta_interactions_authorize_live_actions",
    "discord_or_beta_interactions_approve_live_actions",
    "button_interactions_create_channel_messages",
    "button_interactions_create_followup_messages",
    "button_interactions_update_operational_message",
    "button_interactions_read_discord",
    "button_interactions_send_discord",
    "button_interactions_use_network",
    "button_interactions_retain_raw_user_id",
    "button_interactions_retain_raw_player_text",
    "button_interactions_retain_secrets",
    "button_events_claim_evidence",
    "button_events_claim_progress",
    "button_events_claim_readiness",
    "button_events_count_as_sdk_progress",
    "embed_claims_evidence",
    "embed_claims_progress",
    "embed_claims_readiness",
    "operational_message_counts_as_readiness",
    "authorizes_discord_send",
    "counts_as_approved_runtime_evidence",
    "counts_as_runtime_evidence",
    "counts_as_sdk_progress",
    "counts_as_p0_progress",
    "counts_as_readiness",
)
TRUE_ACTIVE_NOTICE_REUSE_POLICY_FLAGS = (
    "active_notice_state_pointer_only",
    "active_notice_state_required_for_beta_controls",
    "fresh_window_required_after_stale_request",
    "existing_active_notice_updates_in_place",
    "new_message_only_when_active_notice_state_missing",
    "direct_helper_patch_changes_communication_state_only",
    "wait_requires_fresh_window_preconditions",
)

DISCORD_BETA_NON_PROMOTION_FLAGS = {
    "discord_or_beta_interactions_count_as_approved_runtime_evidence": False,
    "discord_or_beta_interactions_count_as_runtime_evidence": False,
    "discord_or_beta_interactions_count_as_sdk_progress": False,
    "discord_or_beta_interactions_count_as_p0_progress": False,
    "discord_or_beta_interactions_count_as_public_sdk_readiness": False,
    "discord_or_beta_interactions_count_as_stable_sdk_readiness": False,
    "discord_or_beta_interactions_authorize_live_actions": False,
    "discord_or_beta_interactions_approve_live_actions": False,
}


def discord_beta_non_promotion_boundary(scope: str) -> dict[str, Any]:
    return {
        "schema": DISCORD_BETA_NON_PROMOTION_SCHEMA,
        "scope": scope,
        "interaction_surface": "discord_beta_coordination_only",
        "event_sink_semantics": "metadata_only",
        "single_operational_message_style": SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE,
        "accepted_copied_sibling_set_required_before_runtime_claims": True,
        "discord_beta_interactions_are_runtime_evidence": False,
        "discord_beta_interactions_are_sdk_progress": False,
        "discord_beta_interactions_are_p0_progress": False,
        "discord_beta_interactions_grant_public_sdk_readiness": False,
        "discord_beta_interactions_grant_stable_readiness": False,
        "discord_beta_interactions_approve_live_actions": False,
        **DISCORD_BETA_NON_PROMOTION_FLAGS,
    }


FALSE_ACTIVE_NOTICE_REUSE_POLICY_FLAGS = (
    "active_notice_state_is_notice_report",
    "active_notice_state_is_confirmed_beta_notice_report",
    "active_notice_state_satisfies_activation_preconditions",
    "active_notice_state_counts_as_confirmed_notice",
    "active_notice_state_counts_as_approved_runtime_evidence",
    "active_notice_state_counts_as_runtime_evidence",
    "active_notice_state_counts_as_sdk_progress",
    "active_notice_state_counts_as_p0_progress",
    "active_notice_state_counts_as_readiness",
    "wait_only_without_fresh_window_allowed",
    "runtime_capture_allowed_by_active_notice_state",
    "server_restart_allowed_by_active_notice_state",
    "discord_send_allowed_by_active_notice_state",
)


def canonical_plan() -> dict[str, Any]:
    return {
        "schema": PLAN_SCHEMA,
        "channel": CHANNEL,
        "bot_channel_id": BOT_CHANNEL_ID,
        "bot_channel_required_for_real_send": True,
        "bot_required_for_interaction": True,
        "webhook_outbound_only": False,
        "webhook_deprecated": True,
        "webhook_real_send_allowed": False,
        "webhook_fail_closed_for_real_sends": True,
        "slash_commands_preferred": True,
        "freeform_channel_scraping_allowed": False,
        "event_sink": EVENT_SINK,
        "token_env_var": TOKEN_ENV_VAR,
        "rotated_token_required": True,
        "token_rotation_attestation_env_var": ROTATED_TOKEN_AT_ENV_VAR,
        "permissions": sorted(ALLOWED_PERMISSIONS),
        "forbidden_permissions": sorted(FORBIDDEN_PERMISSIONS),
        "commands": [
            {"id": "status", "description": "current beta-test instruction"},
            {"id": "ready", "required_fields": ["map"]},
            {"id": "joined", "required_fields": ["map"]},
            {"id": "logout-ready", "required_fields": []},
            {"id": "issue", "required_fields": ["type"], "optional_fields": ["redacted_note"]},
            {"id": "done", "required_fields": []},
        ],
        "privacy_boundary": {
            "redacted_jsonl_events": True,
            "raw_message_content_retention_allowed": False,
            "raw_in_game_chat_retention_allowed": False,
            "private_player_data_retention_allowed": False,
            "secret_or_webhook_retention_allowed": False,
            "steam_or_eos_id_retention_allowed": False,
            "ip_address_retention_allowed": False,
            "message_content_intent_required_by_default": False,
        },
        "event_sink_semantics": {
            "metadata_only": True,
            "redacted_jsonl_events": True,
            "raw_discord_payload_retention_allowed": False,
            "raw_user_id_retention_allowed": False,
            "authorization_or_evidence_aliases_allowed": False,
            "event_sink_counts_as_evidence": False,
            "event_sink_counts_as_progress": False,
        },
        "live_run_preflight": {
            "requires_bot_token": True,
            "requires_rotated_token_attestation": True,
            "requires_discord_py_dependency": True,
            "discord_connection_allowed_by_plan_check": False,
            "discord_read_allowed_by_plan_check": False,
            "discord_send_allowed_by_plan_check": False,
            "token_value_output_allowed": False,
        },
        "local_offline_workflow": {
            "dependency_interpreter": LOCAL_BRIDGE_PYTHON,
            "config_check_command": list(CONFIG_CHECK_COMMAND),
            "use_local_venv_when_system_python_lacks_discord_py": True,
            "discord_connection_allowed_by_config_check": False,
            "discord_read_allowed_by_config_check": False,
            "discord_send_allowed_by_config_check": False,
            "token_value_output_allowed": False,
        },
        "notice_send_path": {
            "default_transport": "discord_bot_channel",
            "operational_message_workflow": "single_active_bot_notice",
            "operational_message_style": SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE,
            "bot_channel_id": BOT_CHANNEL_ID,
            "expected_channel_id": BOT_CHANNEL_ID,
            "bot_channel_env_var": BOT_CHANNEL_ENV_VAR,
            "active_notice_state_env_var": ACTIVE_NOTICE_STATE_ENV_VAR,
            "event_sink": EVENT_SINK,
            "helper_command": list(BETA_NOTICE_SEND_COMMAND),
            "required_helper_args": list(BETA_NOTICE_REQUIRED_HELPER_ARGS),
            "button_custom_id_prefix": "obelisk_beta:",
            "button_interaction_result_schema": BUTTON_INTERACTION_RESULT_SCHEMA,
            "button_custom_ids": list(BETA_NOTICE_BUTTON_CUSTOM_IDS),
            "button_action_count": len(BETA_NOTICE_BUTTON_ACTION_MAP),
            "button_action_map": [dict(item) for item in BETA_NOTICE_BUTTON_ACTION_MAP],
            "status_summary_button_custom_id": STATUS_SUMMARY_CUSTOM_ID,
            "status_summary_response_mode": STATUS_SUMMARY_RESPONSE_MODE,
            "status_summary_button_required": True,
            "status_summary_ephemeral_response_only": True,
            "status_summary_uses_local_event_sink_only": True,
            "status_summary_metadata_only": True,
            "status_summary_button_writes_event": False,
            "status_summary_reads_discord": False,
            "status_summary_sends_discord": False,
            "status_summary_creates_channel_message": False,
            "status_summary_updates_operational_message": False,
            "status_summary_creates_event": False,
            "status_summary_claims_evidence": False,
            "status_summary_claims_progress": False,
            "status_summary_claims_readiness": False,
            "status_summary_counts_as_approved_runtime_evidence": False,
            "status_summary_counts_as_runtime_evidence": False,
            "status_summary_counts_as_sdk_progress": False,
            "status_summary_counts_as_p0_progress": False,
            "status_summary_counts_as_readiness": False,
            **DISCORD_BETA_NON_PROMOTION_FLAGS,
            "discord_beta_non_promotion": discord_beta_non_promotion_boundary(
                "notice_send_path"
            ),
            "bot_channel_required_for_real_send": True,
            "single_operational_message_required": True,
            "active_notice_state_required_for_beta_controls": True,
            "single_editable_notice_required": True,
            "single_editable_embed_required": True,
            "existing_active_notice_http_method": "PATCH",
            "missing_active_notice_http_method": "POST",
            "existing_active_notice_updates_in_place": True,
            "new_message_only_when_active_notice_state_missing": True,
            "single_updated_embed_buttons_message_preferred": True,
            "edit_existing_message_when_active_notice_state_present": True,
            "post_only_when_active_notice_state_missing": True,
            "repeat_everyone_mentions_suppressed_on_update": True,
            "interactive_buttons_required": True,
            "button_interaction_response_mode": "ephemeral_ack_and_local_event_write",
            "button_interactions_ephemeral_ack_only": True,
            "button_interactions_metadata_only": True,
            "button_interactions_write_local_redacted_events_only": True,
            "button_interactions_local_event_acknowledgement_only": True,
            "button_interactions_require_expected_channel": True,
            "button_interactions_validate_metadata_only_result": True,
            "button_interactions_create_channel_messages": False,
            "button_interactions_create_followup_messages": False,
            "button_interactions_update_operational_message": False,
            "button_interactions_read_discord": False,
            "button_interactions_send_discord": False,
            "button_interactions_use_network": False,
            "button_interactions_retain_raw_user_id": False,
            "button_interactions_retain_raw_player_text": False,
            "button_interactions_retain_secrets": False,
            "button_events_claim_evidence": False,
            "button_events_claim_progress": False,
            "button_events_claim_readiness": False,
            "button_events_count_as_sdk_progress": False,
            "embed_claims_evidence": False,
            "embed_claims_progress": False,
            "embed_claims_readiness": False,
            "with_beta_controls_required": True,
            "update_active_notice_required": True,
            "confirm_approved_send_flag_required_for_real_send": True,
            "uses_webhook": False,
            "webhook_outbound_only": False,
            "webhook_deprecated": True,
            "webhook_real_send_allowed": False,
            "webhook_fail_closed_for_real_sends": True,
            "webhook_fallback_allowed": False,
            "webhook_send_path_enabled": False,
            "authorizes_discord_send": False,
            "operational_message_counts_as_readiness": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_progress": False,
            "counts_as_p0_progress": False,
            "counts_as_readiness": False,
            "active_notice_reuse_policy": {
                "schema": ACTIVE_NOTICE_REUSE_POLICY_SCHEMA,
                "reuse_scope": "communication_state_only",
                "bot_channel_id": BOT_CHANNEL_ID,
                "expected_channel_id": BOT_CHANNEL_ID,
                "active_notice_state_pointer_only": True,
                "active_notice_state_required_for_beta_controls": True,
                "fresh_window_required_after_stale_request": True,
                "wrapper_stale_blocker": "approved_window_start_not_in_future",
                "existing_active_notice_updates_in_place": True,
                "new_message_only_when_active_notice_state_missing": True,
                "direct_helper_patch_changes_communication_state_only": True,
                "wait_requires_fresh_window_preconditions": True,
                "active_notice_state_is_notice_report": False,
                "active_notice_state_is_confirmed_beta_notice_report": False,
                "active_notice_state_satisfies_activation_preconditions": False,
                "active_notice_state_counts_as_confirmed_notice": False,
                "active_notice_state_counts_as_approved_runtime_evidence": False,
                "active_notice_state_counts_as_runtime_evidence": False,
                "active_notice_state_counts_as_sdk_progress": False,
                "active_notice_state_counts_as_p0_progress": False,
                "active_notice_state_counts_as_readiness": False,
                "wait_only_without_fresh_window_allowed": False,
                "runtime_capture_allowed_by_active_notice_state": False,
                "server_restart_allowed_by_active_notice_state": False,
                "discord_send_allowed_by_active_notice_state": False,
            },
        },
        "non_authorization": {
            key: False for key in FALSE_NON_AUTHORIZATION_FLAGS
        },
    }


def add(blockers: list[dict[str, str]], reason: str, label: str) -> None:
    blockers.append({"reason": reason, "label": label})


def strings_in(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for key, child in value.items():
            out.extend(strings_in(key))
            out.extend(strings_in(child))
        return out
    if isinstance(value, list):
        out = []
        for child in value:
            out.extend(strings_in(child))
        return out
    return []


def normalized_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def alias_value_is_positive(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().casefold() not in FALSEY_ALIAS_VALUES
    return False


def collect_alias_overclaims(value: Any, *, path: str = "$") -> list[str]:
    blockers: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"
            compact_key = normalized_key(key_text)
            if (
                compact_key in FORBIDDEN_EXACT_ALIAS_KEYS
                or FORBIDDEN_ALIAS_KEY_RE.search(compact_key)
            ) and alias_value_is_positive(child):
                blockers.append(child_path)
            blockers.extend(collect_alias_overclaims(child, path=child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            blockers.extend(collect_alias_overclaims(child, path=f"{path}[{index}]"))
    return blockers


def load_plan(path: Path) -> dict[str, Any]:
    protected_paths.reject_symlink_component(path, "plan")
    resolved = protected_paths.reject_protected_input_path(path, "plan")
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("plan must be a JSON object")
    return payload


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    blockers: list[dict[str, str]] = []

    if plan.get("schema") != PLAN_SCHEMA:
        add(blockers, "schema_mismatch", "$.schema")
    if plan.get("channel") != CHANNEL:
        add(blockers, "channel_mismatch", "$.channel")
    if plan.get("bot_channel_id") != BOT_CHANNEL_ID:
        add(blockers, "bot_channel_id_mismatch", "$.bot_channel_id")
    if plan.get("bot_channel_required_for_real_send") is not True:
        add(
            blockers,
            "bot_channel_required_for_real_send_not_true",
            "$.bot_channel_required_for_real_send",
        )
    if plan.get("bot_required_for_interaction") is not True:
        add(blockers, "bot_required_for_interaction_not_true", "$.bot_required_for_interaction")
    if plan.get("webhook_outbound_only") is not False:
        add(blockers, "webhook_outbound_only_not_false", "$.webhook_outbound_only")
    if plan.get("webhook_deprecated") is not True:
        add(blockers, "webhook_deprecated_not_true", "$.webhook_deprecated")
    if plan.get("webhook_real_send_allowed") is not False:
        add(blockers, "webhook_real_send_allowed_not_false", "$.webhook_real_send_allowed")
    if plan.get("webhook_fail_closed_for_real_sends") is not True:
        add(
            blockers,
            "webhook_fail_closed_for_real_sends_not_true",
            "$.webhook_fail_closed_for_real_sends",
        )
    if plan.get("slash_commands_preferred") is not True:
        add(blockers, "slash_commands_preferred_not_true", "$.slash_commands_preferred")
    if plan.get("freeform_channel_scraping_allowed") is not False:
        add(blockers, "freeform_channel_scraping_allowed_not_false", "$.freeform_channel_scraping_allowed")
    if plan.get("event_sink") != EVENT_SINK:
        add(blockers, "event_sink_mismatch", "$.event_sink")
    if plan.get("token_env_var") != TOKEN_ENV_VAR:
        add(blockers, "token_env_var_mismatch", "$.token_env_var")
    if plan.get("rotated_token_required") is not True:
        add(blockers, "rotated_token_required_not_true", "$.rotated_token_required")
    if plan.get("token_rotation_attestation_env_var") != ROTATED_TOKEN_AT_ENV_VAR:
        add(
            blockers,
            "token_rotation_attestation_env_var_mismatch",
            "$.token_rotation_attestation_env_var",
        )

    permissions = set(plan.get("permissions", []))
    if permissions != ALLOWED_PERMISSIONS:
        add(blockers, "permissions_not_minimal", "$.permissions")
    forbidden_permissions = set(plan.get("forbidden_permissions", []))
    if not FORBIDDEN_PERMISSIONS.issubset(forbidden_permissions):
        add(blockers, "forbidden_permissions_missing", "$.forbidden_permissions")
    if permissions & FORBIDDEN_PERMISSIONS:
        add(blockers, "forbidden_permission_requested", "$.permissions")

    command_ids = tuple(command.get("id") for command in plan.get("commands", []) if isinstance(command, dict))
    if command_ids != REQUIRED_COMMAND_IDS:
        add(blockers, "command_sequence_mismatch", "$.commands")

    privacy = plan.get("privacy_boundary", {})
    if not isinstance(privacy, dict):
        add(blockers, "privacy_boundary_missing", "$.privacy_boundary")
        privacy = {}
    if privacy.get("redacted_jsonl_events") is not True:
        add(blockers, "redacted_jsonl_events_not_true", "$.privacy_boundary.redacted_jsonl_events")
    for key in FALSE_PRIVACY_FLAGS:
        if privacy.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.privacy_boundary.{key}")

    event_sink_semantics = plan.get("event_sink_semantics", {})
    if not isinstance(event_sink_semantics, dict):
        add(blockers, "event_sink_semantics_missing", "$.event_sink_semantics")
        event_sink_semantics = {}
    if event_sink_semantics.get("metadata_only") is not True:
        add(blockers, "event_sink_metadata_only_not_true", "$.event_sink_semantics.metadata_only")
    if event_sink_semantics.get("redacted_jsonl_events") is not True:
        add(
            blockers,
            "event_sink_redacted_jsonl_events_not_true",
            "$.event_sink_semantics.redacted_jsonl_events",
        )
    for key in FALSE_EVENT_SINK_FLAGS:
        if event_sink_semantics.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.event_sink_semantics.{key}")

    live_run_preflight = plan.get("live_run_preflight", {})
    if not isinstance(live_run_preflight, dict):
        add(blockers, "live_run_preflight_missing", "$.live_run_preflight")
        live_run_preflight = {}
    for key in (
        "requires_bot_token",
        "requires_rotated_token_attestation",
        "requires_discord_py_dependency",
    ):
        if live_run_preflight.get(key) is not True:
            add(blockers, f"{key}_not_true", f"$.live_run_preflight.{key}")
    for key in FALSE_LIVE_RUN_PREFLIGHT_FLAGS:
        if live_run_preflight.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.live_run_preflight.{key}")

    local_offline_workflow = plan.get("local_offline_workflow", {})
    if not isinstance(local_offline_workflow, dict):
        add(blockers, "local_offline_workflow_missing", "$.local_offline_workflow")
        local_offline_workflow = {}
    if local_offline_workflow.get("dependency_interpreter") != LOCAL_BRIDGE_PYTHON:
        add(
            blockers,
            "dependency_interpreter_mismatch",
            "$.local_offline_workflow.dependency_interpreter",
        )
    if local_offline_workflow.get("config_check_command") != list(CONFIG_CHECK_COMMAND):
        add(
            blockers,
            "config_check_command_mismatch",
            "$.local_offline_workflow.config_check_command",
        )
    if local_offline_workflow.get("use_local_venv_when_system_python_lacks_discord_py") is not True:
        add(
            blockers,
            "use_local_venv_when_system_python_lacks_discord_py_not_true",
            "$.local_offline_workflow.use_local_venv_when_system_python_lacks_discord_py",
        )
    for key in FALSE_LOCAL_OFFLINE_WORKFLOW_FLAGS:
        if local_offline_workflow.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.local_offline_workflow.{key}")

    notice_send_path = plan.get("notice_send_path", {})
    if not isinstance(notice_send_path, dict):
        add(blockers, "notice_send_path_missing", "$.notice_send_path")
        notice_send_path = {}
    if notice_send_path.get("default_transport") != "discord_bot_channel":
        add(blockers, "notice_default_transport_mismatch", "$.notice_send_path.default_transport")
    if notice_send_path.get("operational_message_workflow") != "single_active_bot_notice":
        add(
            blockers,
            "notice_operational_message_workflow_mismatch",
            "$.notice_send_path.operational_message_workflow",
        )
    if notice_send_path.get("operational_message_style") != SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE:
        add(
            blockers,
            "notice_operational_message_style_mismatch",
            "$.notice_send_path.operational_message_style",
        )
    if notice_send_path.get("bot_channel_id") != BOT_CHANNEL_ID:
        add(blockers, "notice_bot_channel_id_mismatch", "$.notice_send_path.bot_channel_id")
    if notice_send_path.get("expected_channel_id") != BOT_CHANNEL_ID:
        add(
            blockers,
            "notice_expected_channel_id_mismatch",
            "$.notice_send_path.expected_channel_id",
        )
    if notice_send_path.get("bot_channel_env_var") != BOT_CHANNEL_ENV_VAR:
        add(blockers, "notice_bot_channel_env_var_mismatch", "$.notice_send_path.bot_channel_env_var")
    if notice_send_path.get("active_notice_state_env_var") != ACTIVE_NOTICE_STATE_ENV_VAR:
        add(
            blockers,
            "notice_active_notice_state_env_var_mismatch",
            "$.notice_send_path.active_notice_state_env_var",
        )
    if notice_send_path.get("event_sink") != EVENT_SINK:
        add(blockers, "notice_event_sink_mismatch", "$.notice_send_path.event_sink")
    if notice_send_path.get("helper_command") != list(BETA_NOTICE_SEND_COMMAND):
        add(blockers, "notice_helper_command_mismatch", "$.notice_send_path.helper_command")
    if notice_send_path.get("required_helper_args") != list(BETA_NOTICE_REQUIRED_HELPER_ARGS):
        add(
            blockers,
            "notice_required_helper_args_mismatch",
            "$.notice_send_path.required_helper_args",
        )
    if notice_send_path.get("button_custom_id_prefix") != "obelisk_beta:":
        add(
            blockers,
            "notice_button_custom_id_prefix_mismatch",
            "$.notice_send_path.button_custom_id_prefix",
        )
    if notice_send_path.get("button_interaction_result_schema") != BUTTON_INTERACTION_RESULT_SCHEMA:
        add(
            blockers,
            "notice_button_interaction_result_schema_mismatch",
            "$.notice_send_path.button_interaction_result_schema",
        )
    if notice_send_path.get("button_custom_ids") != list(BETA_NOTICE_BUTTON_CUSTOM_IDS):
        add(blockers, "notice_button_custom_ids_mismatch", "$.notice_send_path.button_custom_ids")
    if notice_send_path.get("button_action_count") != len(BETA_NOTICE_BUTTON_ACTION_MAP):
        add(
            blockers,
            "notice_button_action_count_mismatch",
            "$.notice_send_path.button_action_count",
        )
    if notice_send_path.get("button_action_map") != [dict(item) for item in BETA_NOTICE_BUTTON_ACTION_MAP]:
        add(blockers, "notice_button_action_map_mismatch", "$.notice_send_path.button_action_map")
    if notice_send_path.get("status_summary_button_custom_id") != STATUS_SUMMARY_CUSTOM_ID:
        add(
            blockers,
            "notice_status_summary_button_custom_id_mismatch",
            "$.notice_send_path.status_summary_button_custom_id",
        )
    if notice_send_path.get("status_summary_response_mode") != STATUS_SUMMARY_RESPONSE_MODE:
        add(
            blockers,
            "notice_status_summary_response_mode_mismatch",
            "$.notice_send_path.status_summary_response_mode",
        )
    if notice_send_path.get("button_interaction_response_mode") != "ephemeral_ack_and_local_event_write":
        add(
            blockers,
            "notice_button_interaction_response_mode_mismatch",
            "$.notice_send_path.button_interaction_response_mode",
        )
    if notice_send_path.get("existing_active_notice_http_method") != "PATCH":
        add(
            blockers,
            "notice_existing_active_notice_http_method_mismatch",
            "$.notice_send_path.existing_active_notice_http_method",
        )
    if notice_send_path.get("missing_active_notice_http_method") != "POST":
        add(
            blockers,
            "notice_missing_active_notice_http_method_mismatch",
            "$.notice_send_path.missing_active_notice_http_method",
        )
    for key in TRUE_NOTICE_SEND_PATH_FLAGS:
        if notice_send_path.get(key) is not True:
            add(blockers, f"notice_{key}_not_true", f"$.notice_send_path.{key}")
    for key in FALSE_NOTICE_SEND_PATH_FLAGS:
        if notice_send_path.get(key) is not False:
            add(blockers, f"notice_{key}_not_false", f"$.notice_send_path.{key}")
    expected_non_promotion = discord_beta_non_promotion_boundary("notice_send_path")
    if notice_send_path.get("discord_beta_non_promotion") != expected_non_promotion:
        add(
            blockers,
            "notice_discord_beta_non_promotion_mismatch",
            "$.notice_send_path.discord_beta_non_promotion",
        )
    reuse_policy = notice_send_path.get("active_notice_reuse_policy", {})
    if not isinstance(reuse_policy, dict):
        add(
            blockers,
            "notice_active_notice_reuse_policy_missing",
            "$.notice_send_path.active_notice_reuse_policy",
        )
        reuse_policy = {}
    if reuse_policy.get("schema") != ACTIVE_NOTICE_REUSE_POLICY_SCHEMA:
        add(
            blockers,
            "notice_active_notice_reuse_policy_schema_mismatch",
            "$.notice_send_path.active_notice_reuse_policy.schema",
        )
    if reuse_policy.get("reuse_scope") != "communication_state_only":
        add(
            blockers,
            "notice_active_notice_reuse_scope_mismatch",
            "$.notice_send_path.active_notice_reuse_policy.reuse_scope",
        )
    if reuse_policy.get("bot_channel_id") != BOT_CHANNEL_ID:
        add(
            blockers,
            "notice_active_notice_reuse_bot_channel_id_mismatch",
            "$.notice_send_path.active_notice_reuse_policy.bot_channel_id",
        )
    if reuse_policy.get("expected_channel_id") != BOT_CHANNEL_ID:
        add(
            blockers,
            "notice_active_notice_reuse_expected_channel_id_mismatch",
            "$.notice_send_path.active_notice_reuse_policy.expected_channel_id",
        )
    if reuse_policy.get("wrapper_stale_blocker") != "approved_window_start_not_in_future":
        add(
            blockers,
            "notice_active_notice_reuse_wrapper_stale_blocker_mismatch",
            "$.notice_send_path.active_notice_reuse_policy.wrapper_stale_blocker",
        )
    for key in TRUE_ACTIVE_NOTICE_REUSE_POLICY_FLAGS:
        if reuse_policy.get(key) is not True:
            add(
                blockers,
                f"notice_active_notice_reuse_{key}_not_true",
                f"$.notice_send_path.active_notice_reuse_policy.{key}",
            )
    for key in FALSE_ACTIVE_NOTICE_REUSE_POLICY_FLAGS:
        if reuse_policy.get(key) is not False:
            add(
                blockers,
                f"notice_active_notice_reuse_{key}_not_false",
                f"$.notice_send_path.active_notice_reuse_policy.{key}",
            )

    non_authorization = plan.get("non_authorization", {})
    if not isinstance(non_authorization, dict):
        add(blockers, "non_authorization_missing", "$.non_authorization")
        non_authorization = {}
    for key in FALSE_NON_AUTHORIZATION_FLAGS:
        if non_authorization.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.non_authorization.{key}")

    for path in collect_alias_overclaims(plan):
        add(blockers, "authorization_progress_evidence_alias_not_false", path)

    for text in strings_in(plan):
        if FORBIDDEN_RE.search(text) or DISCORD_TOKEN_SHAPE_RE.search(text):
            add(blockers, "forbidden_secret_or_identifier_text", "$")
            break

    return {
        "schema": SCHEMA,
        "valid": not blockers,
        "blockers": [item["reason"] for item in blockers],
        "blocker_details": blockers,
        "plan_schema": plan.get("schema"),
        "channel": plan.get("channel"),
        "bot_channel_id": plan.get("bot_channel_id"),
        "bot_channel_required_for_real_send": plan.get("bot_channel_required_for_real_send") is True,
        "event_sink": plan.get("event_sink"),
        "rotated_token_required": plan.get("rotated_token_required") is True,
        "token_rotation_attestation_env_var": plan.get("token_rotation_attestation_env_var"),
        "commands": list(command_ids),
        "webhook_outbound_only": plan.get("webhook_outbound_only") is True,
        "webhook_deprecated": plan.get("webhook_deprecated") is True,
        "webhook_real_send_allowed": plan.get("webhook_real_send_allowed") is True,
        "webhook_fail_closed_for_real_sends": plan.get("webhook_fail_closed_for_real_sends") is True,
        "bot_required_for_interaction": plan.get("bot_required_for_interaction") is True,
        "freeform_channel_scraping_allowed": plan.get("freeform_channel_scraping_allowed") is True,
        "privacy_boundary": privacy,
        "event_sink_semantics": event_sink_semantics,
        "live_run_preflight": live_run_preflight,
        "local_offline_workflow": local_offline_workflow,
        "notice_send_path": notice_send_path,
        "non_authorization": non_authorization,
        "non_claim": (
            "Discord bridge plan validation is offline communication workflow metadata only; "
            "it does not read Discord, send Discord, authorize live ops, or count as runtime "
            "evidence, SDK/P0 progress, public readiness, stable readiness, Plugin Hub "
            "readiness, or publication."
        ),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", nargs="?", type=Path, help="Optional JSON plan to validate.")
    parser.add_argument("--emit-template", action="store_true")
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.emit_template:
        print(json.dumps(canonical_plan(), indent=2, sort_keys=True))
        return 0
    plan = load_plan(args.plan) if args.plan else canonical_plan()
    report = validate_plan(plan)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
