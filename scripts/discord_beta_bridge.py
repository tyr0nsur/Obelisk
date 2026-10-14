#!/usr/bin/env python3
"""Discord beta tester bridge for Obelisk.

The bridge is intentionally narrow:

- configuration is read from environment or local/discord-bot.env;
- events are written as redacted local JSONL;
- no RCON, ARK server control, marker/env mutation, or evidence promotion is performed;
- running the Discord bot requires the optional discord.py dependency.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

import protected_paths


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = REPO_ROOT / "local" / "discord-bot.env"
DEFAULT_EVENT_SINK = REPO_ROOT / "local" / "discord-beta-bridge" / "events.jsonl"
DEFAULT_ACTIVE_NOTICE_STATE = REPO_ROOT / "local" / "discord-beta-bridge" / "active-notice.json"
EVENT_SCHEMA = "obelisk.discord-beta-bridge-event.v1"
CONFIG_SCHEMA = "obelisk.discord-beta-bridge-config-check.v1"
BOT_NOTICE_SCHEMA = "obelisk.discord-beta-bridge-bot-notice.v1"
ACTIVE_NOTICE_STATE_SCHEMA = "obelisk.discord-beta-bridge-active-notice.v1"
ACTIVE_NOTICE_REUSE_DIAGNOSTIC_SCHEMA = (
    "obelisk.discord-beta-bridge-active-notice-reuse-diagnostic.v1"
)
OPERATIONAL_MESSAGE_POLICY_SCHEMA = "obelisk.discord-beta-bridge-operational-message-policy.v1"
TESTER_STATUS_WORKFLOW_SCHEMA = "obelisk.discord-beta-bridge-tester-status-workflow.v1"
EDITABLE_NOTICE_WORKFLOW_SCHEMA = "obelisk.discord-beta-bridge-editable-notice-workflow.v1"
OPERATIONAL_EMBED_METADATA_SCHEMA = "obelisk.discord-beta-bridge-operational-embed-metadata.v1"
DISCORD_BETA_NON_PROMOTION_SCHEMA = "obelisk.discord-beta-bridge-non-promotion-boundary.v1"
BUTTON_INTERACTION_RESULT_SCHEMA = (
    "obelisk.discord-beta-bridge-button-interaction-result.v1"
)
DRY_RUN_RECEIPT_SCHEMA = "obelisk.discord-beta-bridge-dry-run-receipt.v1"
EVENT_SUMMARY_SCHEMA = "obelisk.discord-beta-bridge-event-summary.v1"
TESTER_STATUS_SUMMARY_SCHEMA = "obelisk.discord-beta-bridge-tester-status-summary.v1"
DRY_RUN_RECEIPT_PREFIX = "obelisk-beta-dry-run:"
TOKEN_ENV = "OBELISK_DISCORD_BOT_TOKEN"
ROTATED_TOKEN_AT_ENV = "OBELISK_DISCORD_BOT_TOKEN_ROTATED_AT_UTC"
GUILD_ENV = "OBELISK_DISCORD_GUILD_ID"
BETA_CHANNEL_ENV = "OBELISK_DISCORD_BETA_CHANNEL_ID"
EVENT_SINK_ENV = "OBELISK_DISCORD_BRIDGE_EVENT_SINK"
ACTIVE_NOTICE_STATE_ENV = "OBELISK_DISCORD_ACTIVE_NOTICE_STATE"
SALT_ENV = "OBELISK_DISCORD_BRIDGE_SALT"
EXPECTED_GUILD_ID = "1032660680668622969"
EXPECTED_CHANNEL_ID = "1513238083741683934"
ALLOWED_MAPS = ("Ragnarok", "TheIsland", "Genesis2")
ALLOWED_ISSUE_TYPES = ("crash", "timeout", "cluster", "other")
REDACTED_FREE_TEXT_NOTE = "<redacted-free-text>"
REDACTED_FORBIDDEN_NOTE = "<redacted-forbidden-content>"
REDACTED_NOTE_VALUES = frozenset((REDACTED_FREE_TEXT_NOTE, REDACTED_FORBIDDEN_NOTE))
EVENT_TYPES = (
    "ready",
    "started",
    "loading",
    "joined",
    "in_server",
    "logout_ready",
    "logged_out",
    "cluster_transfer",
    "issue",
    "done",
    "status",
)
TESTER_STATUS_EVENT_TYPES = (
    "started",
    "loading",
    "in_server",
    "logged_out",
    "cluster_transfer",
)
BETA_CONTROL_CUSTOM_ID_PREFIX = "obelisk_beta:"
BETA_STATUS_SUMMARY_CUSTOM_ID = f"{BETA_CONTROL_CUSTOM_ID_PREFIX}status_summary"
STATUS_SUMMARY_RESPONSE_MODE = "ephemeral_local_event_summary"
SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE = "single_updated_embed_buttons_operational_message"
MENTION_EVERYONE_RE = re.compile(r"@everyone\b")
TOKEN_ROTATION_NOT_BEFORE_UTC = datetime(2026, 6, 7, tzinfo=UTC)
TOKEN_ROTATION_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
FORBIDDEN_NOTE_RE = re.compile(
    r"(?:https?://)?discord(?:app)?\.com/api/webhooks|webhook[_ -]?url|"
    r"(?:bot[_ -]?)?token\s*[:=]|secret\s*[:=]|unique[_ -]?net\s*[:=]|"
    r"steam[_ -]?id\s*[:=]|eos[_ -]?id\s*[:=]|ip(?:v4|v6)?\s*[:=]",
    re.IGNORECASE,
)
DISCORD_TOKEN_SHAPE_RE = re.compile(
    r"\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{20,}\b"
)
FORBIDDEN_NOTICE_TEXT_RE = re.compile(
    r"(?:https?://)?discord(?:app)?\.com/api/webhooks|webhook[_ -]?url|"
    r"(?:bot[_ -]?)?token\s*[:=]|secret\s*[:=]|password\s*[:=]|"
    r"unique[_ -]?net\s*[:=]|steam[_ -]?id\s*[:=]|eos[_ -]?id\s*[:=]|"
    r"ip(?:v4|v6)?\s*[:=]|raw\s+log|player\s+text|approved\s+runtime\s+evidence|"
    r"\b(?:evidence|evidencia|progress|progreso|readiness)\b|"
    r"public\s+sdk\s+ready|stable\s+sdk\s+ready|plugin\s+hub\s+ready",
    re.IGNORECASE,
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
RAW_METADATA_KEYS = frozenset(
    (
        "userid",
        "rawuserid",
        "discorduserid",
        "discordsnowflake",
        "username",
        "displayname",
        "globalname",
        "messagecontent",
        "rawmessagecontent",
        "ingamechat",
        "playertext",
        "steamid",
        "eosid",
        "uniquenetid",
        "ipaddress",
        "ipv4",
        "ipv6",
    )
)
NON_AUTHORIZATION_FLAGS = {
    "authorizes_discord_read": False,
    "authorizes_discord_send": False,
    "authorizes_rcon": False,
    "authorizes_server_start": False,
    "authorizes_server_stop": False,
    "authorizes_server_restart": False,
    "authorizes_marker_or_env_changes": False,
    "authorizes_live_log_reads": False,
    "authorizes_runtime_capture": False,
    "approves_live_actions": False,
    "counts_as_approved_runtime_evidence": False,
    "counts_as_runtime_evidence": False,
    "counts_as_sdk_progress": False,
    "counts_as_p0_progress": False,
    "counts_as_readiness": False,
    "counts_as_public_sdk_readiness": False,
    "counts_as_stable_sdk_readiness": False,
    "public_sdk_ready": False,
    "runtime_ready": False,
    "stable_sdk_ready": False,
    "plugin_hub_ready": False,
    "publication_ready": False,
}

DISCORD_BETA_NON_PROMOTION_FLAGS = {
    "discord_or_beta_interactions_count_as_approved_runtime_evidence": False,
    "discord_or_beta_interactions_count_as_runtime_evidence": False,
    "discord_or_beta_interactions_count_as_sdk_progress": False,
    "discord_or_beta_interactions_count_as_p0_progress": False,
    "discord_or_beta_interactions_count_as_public_sdk_readiness": False,
    "discord_or_beta_interactions_count_as_stable_sdk_readiness": False,
    "discord_or_beta_interactions_count_as_plugin_hub_readiness": False,
    "discord_or_beta_interactions_count_as_publication_readiness": False,
    "discord_or_beta_interactions_authorize_discord_send": False,
    "discord_or_beta_interactions_authorize_live_actions": False,
    "discord_or_beta_interactions_approve_live_actions": False,
    "discord_or_beta_interactions_clear_runtime_evidence_blockers": False,
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


def beta_control_custom_id(action: str, value: str | None = None) -> str:
    suffix = action if value is None else f"{action}:{value}"
    custom_id = f"{BETA_CONTROL_CUSTOM_ID_PREFIX}{suffix}"
    if len(custom_id) > 100:
        raise ValueError("Discord custom_id is too long")
    return custom_id


def beta_button(label: str, action: str, *, style: int = 2, value: str | None = None) -> dict[str, Any]:
    return {
        "type": 2,
        "style": style,
        "label": label,
        "custom_id": beta_control_custom_id(action, value),
    }


def beta_control_components() -> list[dict[str, Any]]:
    return [
        {
            "type": 1,
            "components": [
                beta_button("Started", "started", style=3),
                beta_button("Loading", "loading", style=2),
                beta_button("In Ragnarok", "in_server", style=1, value="Ragnarok"),
                beta_button("In TheIsland", "in_server", style=1, value="TheIsland"),
                beta_button("In Genesis2", "in_server", style=1, value="Genesis2"),
            ],
        },
        {
            "type": 1,
            "components": [
                beta_button("Logged out", "logged_out", style=2),
                beta_button("Cluster transfer", "cluster_transfer", style=4),
                beta_button("Disponible", "ready", style=3),
                beta_button("Listo logout", "logout_ready", style=2),
                beta_button("Ciclo hecho", "done", style=3),
            ],
        },
        {
            "type": 1,
            "components": [
                beta_button("Dentro Ragnarok", "joined", style=1, value="Ragnarok"),
                beta_button("Dentro TheIsland", "joined", style=1, value="TheIsland"),
                beta_button("Dentro Genesis2", "joined", style=1, value="Genesis2"),
                beta_button("Fallo cluster", "issue", style=2, value="cluster"),
                beta_button("Timeout", "issue", style=2, value="timeout"),
            ],
        },
        {
            "type": 1,
            "components": [
                beta_button("Crash", "issue", style=4, value="crash"),
                beta_button("Otro issue", "issue", style=2, value="other"),
                beta_button("Resumen estado", "status_summary", style=1),
            ],
        },
    ]


def beta_control_action_map(
    components: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows = components if components is not None else beta_control_components()
    mapping: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        for component_index, component in enumerate(row.get("components", [])):
            if not isinstance(component, dict):
                continue
            custom_id = component.get("custom_id")
            if not isinstance(custom_id, str):
                continue
            parsed = parse_beta_control_custom_id(custom_id)
            if parsed is None:
                continue
            mapping.append(
                {
                    "row": row_index,
                    "position": component_index,
                    "label": component.get("label"),
                    "custom_id": custom_id,
                    "event_type": parsed["event_type"],
                    "tester_status": parsed.get("tester_status"),
                    "tester_milestone": parsed["event_type"] in TESTER_STATUS_EVENT_TYPES,
                    "summary_only": bool(parsed.get("summary_only")),
                    "writes_event": not bool(parsed.get("summary_only")),
                    "response_mode": (
                        STATUS_SUMMARY_RESPONSE_MODE
                        if parsed.get("summary_only")
                        else "ephemeral_ack_and_local_event_write"
                    ),
                    "creates_channel_message": False,
                    "creates_followup_message": False,
                    "updates_operational_message": False,
                    "claims_evidence": False,
                    "claims_progress": False,
                    "claims_readiness": False,
                    "stable_sdk_ready": False,
                    "discord_beta_non_promotion": discord_beta_non_promotion_boundary(
                        "button_action_map"
                    ),
                    "map": parsed.get("map_name"),
                    "issue_type": parsed.get("issue_type"),
                    "raw_user_id_retained": False,
                    "event_sink_semantics": "metadata_only",
                    "communication_posture_only": True,
                    "non_authorization": dict(NON_AUTHORIZATION_FLAGS),
                }
            )
    return mapping


def beta_tester_status_workflow(
    components: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    action_map = beta_control_action_map(components)
    status_actions = [
        item for item in action_map if item.get("event_type") in TESTER_STATUS_EVENT_TYPES
    ]
    return {
        "schema": TESTER_STATUS_WORKFLOW_SCHEMA,
        "workflow": "single_editable_bot_notice_with_persistent_buttons",
        "operational_message_style": SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE,
        "button_custom_id_prefix": BETA_CONTROL_CUSTOM_ID_PREFIX,
        "tester_reportable_states": list(TESTER_STATUS_EVENT_TYPES),
        "tester_reportable_state_count": len(TESTER_STATUS_EVENT_TYPES),
        "status_actions": status_actions,
        "status_custom_ids": [item["custom_id"] for item in status_actions],
        "status_summary_button_custom_id": BETA_STATUS_SUMMARY_CUSTOM_ID,
        "status_summary_actions": [
            item for item in action_map if item.get("summary_only") is True
        ],
        "one_editable_notice": True,
        "single_operational_message_required": True,
        "active_notice_state_required_for_beta_controls": True,
        "no_flood_single_message_enforced": True,
        "bidirectional_channel_id": EXPECTED_CHANNEL_ID,
        "bot_send_channel_id": EXPECTED_CHANNEL_ID,
        "tester_interaction_channel_id": EXPECTED_CHANNEL_ID,
        "button_control_metadata_locally_representable": True,
        "new_message_only_when_active_notice_state_missing": True,
        "updates_existing_notice_when_state_present": True,
        "button_interaction_response_mode": "ephemeral_ack_and_local_event_write",
        "button_interactions_ephemeral_ack_only": True,
        "button_interactions_create_channel_messages": False,
        "button_interactions_create_followup_messages": False,
        "button_interactions_update_operational_message": False,
        "status_summary_button_writes_event": False,
        "status_summary_response_mode": STATUS_SUMMARY_RESPONSE_MODE,
        "status_summary_uses_local_event_sink_only": True,
        "status_summary_reads_discord": False,
        "status_summary_sends_discord": False,
        "status_summary_creates_channel_message": False,
        "status_summary_updates_operational_message": False,
        "status_summary_creates_event": False,
        "status_summary_claims_evidence": False,
        "status_summary_claims_progress": False,
        "status_summary_claims_readiness": False,
        "map_scoped_status": "in_server",
        "map_scoped_status_values": list(ALLOWED_MAPS),
        "cluster_transfer_is_coordination_status_only": True,
        "button_events_claim_evidence": False,
        "button_events_claim_progress": False,
        "button_events_claim_readiness": False,
        "raw_user_id_retained": False,
        "event_sink_semantics": "metadata_only",
        "redacted_metadata_only": True,
        "communication_posture_only": True,
        "discord_events_are_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "counts_as_readiness": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "stable_sdk_ready": False,
        "discord_beta_non_promotion": discord_beta_non_promotion_boundary(
            "tester_status_workflow"
        ),
        "non_authorization": dict(NON_AUTHORIZATION_FLAGS),
    }


def beta_operational_embed_metadata(
    *,
    embeds: list[dict[str, Any]] | None = None,
    components: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rows = components if components is not None else beta_control_components()
    notice_embeds = embeds if embeds is not None else beta_notice_embeds()
    action_map = beta_control_action_map(rows)
    metadata = {
        "schema": OPERATIONAL_EMBED_METADATA_SCHEMA,
        "workflow": "single_editable_bot_notice_with_button_actions",
        "operational_message_style": SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE,
        "single_operational_message_required": True,
        "single_editable_embed_required": True,
        "single_editable_embed": len(notice_embeds) == 1,
        "embed_count": len(notice_embeds),
        "button_row_count": len(rows),
        "button_action_count": len(action_map),
        "button_custom_ids": [item["custom_id"] for item in action_map],
        "button_action_map": action_map,
        "status_summary_button_custom_id": BETA_STATUS_SUMMARY_CUSTOM_ID,
        "status_summary_response_mode": STATUS_SUMMARY_RESPONSE_MODE,
        "status_summary_writes_event": False,
        "status_summary_creates_channel_message": False,
        "button_interaction_response_mode": "ephemeral_ack_and_local_event_write",
        "button_interactions_ephemeral_ack_only": True,
        "button_interactions_create_channel_messages": False,
        "button_interactions_create_followup_messages": False,
        "button_interactions_update_operational_message": False,
        "embed_claims_evidence": False,
        "embed_claims_progress": False,
        "embed_claims_readiness": False,
        "button_events_claim_evidence": False,
        "button_events_claim_progress": False,
        "button_events_claim_readiness": False,
        "redacted_metadata_only": True,
        "event_sink_semantics": "metadata_only",
        "communication_posture_only": True,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "counts_as_readiness": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "discord_beta_non_promotion": discord_beta_non_promotion_boundary(
            "operational_embed_metadata"
        ),
        "non_authorization": dict(NON_AUTHORIZATION_FLAGS),
    }
    blockers = collect_metadata_guardrail_blockers(metadata)
    if blockers:
        raise ValueError("operational embed metadata is not metadata-only: " + ", ".join(blockers))
    return metadata


def editable_notice_workflow(
    *,
    dry_run: bool,
    with_beta_controls: bool,
    update_active_notice_requested: bool,
    active_notice_state_present: bool,
    update_existing: bool,
) -> dict[str, Any]:
    return {
        "schema": EDITABLE_NOTICE_WORKFLOW_SCHEMA,
        "workflow": "single_active_bot_notice",
        "operational_message_style": SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE,
        "dry_run": dry_run,
        "send_performed_by_dry_run": False,
        "with_beta_controls": with_beta_controls,
        "update_active_notice_requested": update_active_notice_requested,
        "active_notice_state_present": active_notice_state_present,
        "single_operational_message_required": True,
        "active_notice_state_required_for_beta_controls": True,
        "no_flood_single_message_enforced": True,
        "real_send_requires_active_notice_update": True,
        "real_send_requires_beta_controls": True,
        "dry_run_required_before_real_send": True,
        "dry_run_receipt_required_for_real_send": True,
        "bidirectional_channel_id": EXPECTED_CHANNEL_ID,
        "bot_send_channel_id": EXPECTED_CHANNEL_ID,
        "tester_interaction_channel_id": EXPECTED_CHANNEL_ID,
        "updates_existing_message": update_existing,
        "would_create_new_message": not update_existing,
        "new_message_only_when_active_notice_state_missing": True,
        "existing_active_notice_updates_in_place": True,
        "single_updated_embed_buttons_message_preferred": True,
        "edit_existing_message_when_active_notice_state_present": True,
        "post_only_when_active_notice_state_missing": True,
        "existing_active_notice_http_method": "PATCH",
        "missing_active_notice_http_method": "POST",
        "discord_http_method": "PATCH" if update_existing else "POST",
        "repeat_everyone_mentions_suppressed_on_update": True,
        "everyone_mentions_allowed_only_on_create": True,
        "interactive_buttons_preserved_on_update": (
            update_existing and with_beta_controls
        ),
        "button_interactions_create_channel_messages": False,
        "button_interactions_create_followup_messages": False,
        "button_interactions_update_operational_message": False,
        "status_summary_creates_channel_message": False,
        "status_summary_updates_operational_message": False,
        "status_summary_creates_event": False,
        "embed_claims_evidence": False,
        "embed_claims_progress": False,
        "embed_claims_readiness": False,
        "button_events_claim_evidence": False,
        "button_events_claim_progress": False,
        "button_events_claim_readiness": False,
        "status_summary_claims_evidence": False,
        "status_summary_claims_progress": False,
        "status_summary_claims_readiness": False,
        "uses_webhook": False,
        "webhook_deprecated": True,
        "webhook_real_sends_deprecated": True,
        "old_webhook_path_allowed": False,
        "redacted_metadata_only": True,
        "event_sink_semantics": "metadata_only",
        "communication_posture_only": True,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "counts_as_readiness": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "discord_beta_non_promotion": discord_beta_non_promotion_boundary(
            "editable_notice_workflow"
        ),
        "non_authorization": dict(NON_AUTHORIZATION_FLAGS),
    }


def operational_message_policy(
    *,
    dry_run: bool,
    with_beta_controls: bool,
    update_active_notice_requested: bool,
    active_notice_state_present: bool,
    update_existing: bool,
    component_count: int,
    embed_count: int,
) -> dict[str, Any]:
    return {
        "schema": OPERATIONAL_MESSAGE_POLICY_SCHEMA,
        "workflow": "single_active_beta_notice",
        "operational_message_style": SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE,
        "dry_run": dry_run,
        "with_beta_controls": with_beta_controls,
        "single_operational_message_required": True,
        "single_editable_embed_required": True,
        "active_notice_state_required_for_beta_controls": True,
        "no_flood_single_message_enforced": True,
        "real_send_requires_active_notice_update": True,
        "real_send_requires_beta_controls": True,
        "dry_run_required_before_real_send": True,
        "dry_run_receipt_required_for_real_send": True,
        "bidirectional_channel_id": EXPECTED_CHANNEL_ID,
        "bot_send_channel_id": EXPECTED_CHANNEL_ID,
        "tester_interaction_channel_id": EXPECTED_CHANNEL_ID,
        "button_control_metadata_locally_representable": True,
        "active_notice_update_requested": update_active_notice_requested,
        "active_notice_state_present": active_notice_state_present,
        "updates_existing_message": update_existing,
        "would_create_new_message": not update_existing,
        "new_message_only_when_active_notice_state_missing": True,
        "existing_active_notice_updates_in_place": True,
        "single_updated_embed_buttons_message_preferred": True,
        "edit_existing_message_when_active_notice_state_present": True,
        "post_only_when_active_notice_state_missing": True,
        "discord_http_method": "PATCH" if update_existing else "POST",
        "embed_count": embed_count,
        "component_count": component_count,
        "button_interaction_response_mode": "ephemeral_ack_and_local_event_write",
        "button_interactions_ephemeral_ack_only": True,
        "button_interactions_create_channel_messages": False,
        "button_interactions_create_followup_messages": False,
        "button_interactions_update_operational_message": False,
        "status_summary_button_custom_id": BETA_STATUS_SUMMARY_CUSTOM_ID,
        "status_summary_response_mode": STATUS_SUMMARY_RESPONSE_MODE,
        "status_summary_ephemeral_response_only": True,
        "status_summary_uses_local_event_sink_only": True,
        "status_summary_metadata_only": True,
        "status_summary_button_writes_event": False,
        "status_summary_creates_channel_message": False,
        "status_summary_updates_operational_message": False,
        "status_summary_creates_event": False,
        "embed_claims_evidence": False,
        "embed_claims_progress": False,
        "embed_claims_readiness": False,
        "button_events_claim_evidence": False,
        "button_events_claim_progress": False,
        "button_events_claim_readiness": False,
        "status_summary_claims_evidence": False,
        "status_summary_claims_progress": False,
        "status_summary_claims_readiness": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "counts_as_readiness": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "discord_beta_non_promotion": discord_beta_non_promotion_boundary(
            "operational_message_policy"
        ),
        "non_authorization": dict(NON_AUTHORIZATION_FLAGS),
    }


def beta_notice_embeds() -> list[dict[str, Any]]:
    return [
        {
            "title": "Obelisk beta runtime",
            "description": (
                "Usa los botones para informar Started, Loading, In-server, Logged out o "
                "Cluster transfer al bridge, o Resumen estado para ver el resumen local "
                "sin escribir otro evento. Si pulsas Listo logout, espera confirmacion del "
                "observer o del equipo antes de salir durante una ventana de captura."
            ),
            "color": 3447003,
            "fields": [
                {
                    "name": "Flujo",
                    "value": "Disponible -> Dentro mapa -> Listo logout -> Ciclo hecho",
                    "inline": False,
                },
                {
                    "name": "Estado",
                    "value": "Resumen estado responde en ephemeral con metadata local redacted.",
                    "inline": False,
                },
                {
                    "name": "Privacidad",
                    "value": "No publiques IDs, chat, credenciales ni datos privados.",
                    "inline": False,
                },
            ],
            "footer": {"text": "Eventos redacted; coordinacion solamente."},
        }
    ]


def parse_beta_control_custom_id(custom_id: str | None) -> dict[str, Any] | None:
    if not custom_id or not custom_id.startswith(BETA_CONTROL_CUSTOM_ID_PREFIX):
        return None
    payload = custom_id[len(BETA_CONTROL_CUSTOM_ID_PREFIX) :]
    parts = payload.split(":")
    action = parts[0]
    value = parts[1] if len(parts) > 1 else None
    if len(parts) > 2:
        raise ValueError("unsupported beta control custom_id")
    if action == "started" and value is None:
        return {
            "event_type": "started",
            "tester_status": "started",
            "response": "Started registrado como coordinacion solamente.",
        }
    if action == "loading" and value is None:
        return {
            "event_type": "loading",
            "tester_status": "loading",
            "response": "Loading registrado como coordinacion solamente.",
        }
    if action == "ready" and value is None:
        return {"event_type": "ready", "response": "Disponibilidad registrada."}
    if action == "in_server" and value in ALLOWED_MAPS:
        return {
            "event_type": "in_server",
            "tester_status": "in_server",
            "map_name": value,
            "response": f"In-server registrado en {value} como coordinacion solamente.",
        }
    if action == "joined" and value in ALLOWED_MAPS:
        return {
            "event_type": "joined",
            "map_name": value,
            "response": f"Entrada registrada en {value}.",
        }
    if action == "logout_ready" and value is None:
        return {
            "event_type": "logout_ready",
            "response": (
                "Listo para logout registrado. Mantente dentro hasta confirmacion del "
                "observer o del equipo si estas en ventana de captura."
            ),
        }
    if action == "logged_out" and value is None:
        return {
            "event_type": "logged_out",
            "tester_status": "logged_out",
            "response": "Logged-out registrado como coordinacion solamente.",
        }
    if action == "cluster_transfer" and value is None:
        return {
            "event_type": "cluster_transfer",
            "tester_status": "cluster_transfer",
            "response": "Cluster-transfer registrado como coordinacion solamente.",
        }
    if action == "status_summary" and value is None:
        return {
            "event_type": "status",
            "summary_only": True,
            "response": "Resumen local de estados beta.",
        }
    if action == "done" and value is None:
        return {"event_type": "done", "response": "Ciclo completado registrado."}
    if action == "issue" and value in ALLOWED_ISSUE_TYPES:
        return {
            "event_type": "issue",
            "issue_type": value,
            "response": "Issue registrado de forma redacted.",
        }
    raise ValueError("unsupported beta control custom_id")


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def merged_config(env_file: Path = DEFAULT_ENV_PATH) -> dict[str, str]:
    file_values = parse_env_file(env_file)
    return {
        key: os.environ.get(key, file_values.get(key, ""))
        for key in (
            TOKEN_ENV,
            ROTATED_TOKEN_AT_ENV,
            GUILD_ENV,
            BETA_CHANNEL_ENV,
            EVENT_SINK_ENV,
            ACTIVE_NOTICE_STATE_ENV,
            SALT_ENV,
        )
    }


def configured_event_sink(config: dict[str, str]) -> Path:
    raw = config.get(EVENT_SINK_ENV) or str(DEFAULT_EVENT_SINK)
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def configured_active_notice_state(config: dict[str, str]) -> Path:
    raw = config.get(ACTIVE_NOTICE_STATE_ENV) or str(DEFAULT_ACTIVE_NOTICE_STATE)
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def add(blockers: list[dict[str, str]], reason: str, label: str) -> None:
    blockers.append({"reason": reason, "label": label})


def report_contains_secret(value: Any, secret: str) -> bool:
    if not secret:
        return False
    if isinstance(value, str):
        return value == secret or (len(secret) >= 8 and secret in value)
    if isinstance(value, dict):
        return any(
            report_contains_secret(str(key), secret) or report_contains_secret(child, secret)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(report_contains_secret(child, secret) for child in value)
    return False


def reject_token_leak(report: dict[str, Any], config: dict[str, str]) -> None:
    if report_contains_secret(report, config.get(TOKEN_ENV, "")):
        raise RuntimeError("config report would expose bot token")


def discord_dependency_available() -> tuple[bool, str | None]:
    spec = importlib.util.find_spec("discord")
    if spec is None:
        return False, "discord module not importable"
    for distribution in ("discord.py", "discord"):
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            continue
        return True, f"{distribution} {version}"
    return True, "discord module importable; package version unknown"


def token_rotation_status(config: dict[str, str]) -> tuple[bool, str | None]:
    value = config.get(ROTATED_TOKEN_AT_ENV, "").strip()
    if not value:
        return False, "missing"
    if not TOKEN_ROTATION_AT_RE.fullmatch(value):
        return False, "invalid_format"
    try:
        rotated_at = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError:
        return False, "invalid_format"
    if rotated_at < TOKEN_ROTATION_NOT_BEFORE_UTC:
        return False, "before_required_floor"
    return True, None


def check_config(env_file: Path = DEFAULT_ENV_PATH, *, require_token: bool = False) -> dict[str, Any]:
    config = merged_config(env_file)
    blockers: list[dict[str, str]] = []
    token_present = bool(config[TOKEN_ENV])
    token_rotation_required = token_present
    if require_token and not token_present:
        add(blockers, "bot_token_missing", f"${TOKEN_ENV}")
        token_rotation_required = True
    rotation_valid, rotation_error = token_rotation_status(config)
    if token_present and not rotation_valid:
        add(
            blockers,
            f"bot_token_rotation_attestation_{rotation_error}",
            f"${ROTATED_TOKEN_AT_ENV}",
        )
    if config[GUILD_ENV] != EXPECTED_GUILD_ID:
        add(blockers, "guild_id_mismatch", f"${GUILD_ENV}")
    if config[BETA_CHANNEL_ENV] != EXPECTED_CHANNEL_ID:
        add(blockers, "beta_channel_id_mismatch", f"${BETA_CHANNEL_ENV}")
    event_sink = configured_event_sink(config)
    try:
        protected_paths.reject_protected_output_path(event_sink, "event_sink")
    except SystemExit as exc:
        add(blockers, "event_sink_protected_path", "$event_sink")
        event_sink_error = str(exc)
    else:
        event_sink_error = None
    discord_available, discord_detail = discord_dependency_available()
    discord_required = require_token or token_present
    if discord_required and not discord_available:
        add(blockers, "discord_py_missing", "discord.py")
    report = {
        "schema": CONFIG_SCHEMA,
        "valid": not blockers,
        "blockers": [item["reason"] for item in blockers],
        "blocker_details": blockers,
        "env_file": str(env_file),
        "token_present": token_present,
        "token_value_redacted": "<present>" if token_present else "<missing>",
        "token_rotation_required": token_rotation_required,
        "token_rotation_attestation_env_var": ROTATED_TOKEN_AT_ENV,
        "token_rotation_attestation_present": bool(config[ROTATED_TOKEN_AT_ENV]),
        "token_rotation_attestation_valid": rotation_valid,
        "token_rotation_attestation_error": rotation_error,
        "token_rotation_attestation_value_redacted": (
            "<present>" if config[ROTATED_TOKEN_AT_ENV] else "<missing>"
        ),
        "token_rotation_not_before_utc": TOKEN_ROTATION_NOT_BEFORE_UTC.isoformat().replace(
            "+00:00", "Z"
        ),
        "guild_id": config[GUILD_ENV],
        "beta_channel_id": config[BETA_CHANNEL_ENV],
        "event_sink": str(event_sink),
        "event_sink_error": event_sink_error,
        "discord_py_required": discord_required,
        "discord_py_available": discord_available,
        "discord_py_detail": discord_detail,
        "event_sink_semantics": "metadata_only_redacted_jsonl",
        "communication_posture_only": True,
        "non_authorization": dict(NON_AUTHORIZATION_FLAGS),
        "non_claim": (
            "Configuration check only; it does not connect to Discord, read Discord, send "
            "Discord, authorize live ops, or count as runtime evidence, SDK/P0 progress, "
            "public readiness, stable readiness, Plugin Hub readiness, or publication."
        ),
    }
    reject_token_leak(report, config)
    return report


def redacted_note(note: str | None) -> str | None:
    if note is None:
        return None
    cleaned = " ".join(note.strip().split())
    if not cleaned:
        return None
    if FORBIDDEN_NOTE_RE.search(cleaned) or DISCORD_TOKEN_SHAPE_RE.search(cleaned):
        return REDACTED_FORBIDDEN_NOTE
    return REDACTED_FREE_TEXT_NOTE


def actor_alias(user_id: int | str, salt: str = "") -> str:
    salt = salt or "obelisk-discord-beta-bridge-local"
    digest = hashlib.sha256(f"{salt}:{user_id}".encode("utf-8")).hexdigest()
    return digest[:16]


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


def collect_metadata_guardrail_blockers(value: Any, *, path: str = "$") -> list[str]:
    blockers: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"
            compact_key = normalized_key(key_text)
            if compact_key in RAW_METADATA_KEYS and alias_value_is_positive(child):
                blockers.append(f"raw_identifier_or_message_field_retained:{child_path}")
            if (
                compact_key in FORBIDDEN_EXACT_ALIAS_KEYS
                or FORBIDDEN_ALIAS_KEY_RE.search(compact_key)
            ) and alias_value_is_positive(child):
                blockers.append(f"authorization_progress_evidence_alias_not_false:{child_path}")
            if compact_key == "note" and child is not None and child not in REDACTED_NOTE_VALUES:
                blockers.append(f"raw_player_text_retained:{child_path}")
            blockers.extend(collect_metadata_guardrail_blockers(child, path=child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            blockers.extend(collect_metadata_guardrail_blockers(child, path=f"{path}[{index}]"))
    elif isinstance(value, str):
        if FORBIDDEN_NOTE_RE.search(value) or DISCORD_TOKEN_SHAPE_RE.search(value):
            blockers.append(f"forbidden_secret_or_identifier_text:{path}")
    return blockers


def validate_metadata_only_event(event: dict[str, Any]) -> None:
    blockers: list[str] = []
    if event.get("schema") != EVENT_SCHEMA:
        blockers.append("$.schema")
    if event.get("redacted_metadata_only") is not True:
        blockers.append("$.redacted_metadata_only")
    if event.get("event_sink_semantics") != "metadata_only":
        blockers.append("$.event_sink_semantics")
    if event.get("raw_user_id_retained") is not False:
        blockers.append("$.raw_user_id_retained")

    non_authorization = event.get("non_authorization")
    if not isinstance(non_authorization, dict):
        blockers.append("$.non_authorization")
    else:
        for key in NON_AUTHORIZATION_FLAGS:
            if non_authorization.get(key) is not False:
                blockers.append(f"$.non_authorization.{key}")

    blockers.extend(collect_metadata_guardrail_blockers(event))
    if blockers:
        raise ValueError("event is not metadata-only: " + ", ".join(sorted(set(blockers))))


def normalize_metadata_only_event(event: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(event)
    non_authorization = normalized.get("non_authorization")
    if isinstance(non_authorization, dict):
        merged_non_authorization = dict(NON_AUTHORIZATION_FLAGS)
        merged_non_authorization.update(non_authorization)
        normalized["non_authorization"] = merged_non_authorization
    validate_metadata_only_event(normalized)
    return normalized


def active_notice_state(
    *,
    config: dict[str, str],
    message_id: str,
    source: str,
) -> dict[str, Any]:
    state = {
        "schema": ACTIVE_NOTICE_STATE_SCHEMA,
        "guild_id": config.get(GUILD_ENV, ""),
        "channel_id": config.get(BETA_CHANNEL_ENV, ""),
        "message_id": str(message_id),
        "source": source,
        "updated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "operational_message_kind": "single_active_beta_notice",
        "single_operational_message_required": True,
        "active_notice_state_pointer_only": True,
        "active_notice_state_is_notice_report": False,
        "active_notice_reuse_scope": "communication_state_only",
        "fresh_window_required_after_stale_request": True,
        "updates_existing_message": True,
        "new_message_only_when_active_notice_state_missing": True,
        "direct_helper_patch_changes_communication_state_only": True,
        "status_summary_button_writes_event": False,
        "status_summary_creates_channel_message": False,
        "button_interactions_create_channel_messages": False,
        "active_notice_state_satisfies_activation_preconditions": False,
        "active_notice_state_counts_as_confirmed_notice": False,
        "active_notice_state_counts_toward_sdk": False,
        "active_notice_state_counts_toward_p0_dependency_chain": False,
        "counts_as_readiness": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "redacted_metadata_only": True,
        "communication_posture_only": True,
        "discord_beta_non_promotion": discord_beta_non_promotion_boundary(
            "active_notice_state"
        ),
        "non_authorization": dict(NON_AUTHORIZATION_FLAGS),
        "non_claim": (
            "Active Discord message pointer only; it does not authorize live ops, "
            "prove runtime evidence, satisfy activation preconditions, or count as SDK/P0 progress."
        ),
    }
    blockers = collect_metadata_guardrail_blockers(state)
    if blockers:
        raise ValueError("active notice state is not metadata-only: " + ", ".join(blockers))
    if report_contains_secret(state, config.get(TOKEN_ENV, "")):
        raise RuntimeError("active notice state would expose bot token")
    return state


def read_active_notice_state(path: Path, config: dict[str, str]) -> dict[str, Any] | None:
    protected_paths.reject_symlink_component(path, "active_notice_state")
    if not path.exists():
        return None
    resolved = protected_paths.reject_protected_input_path(path, "active_notice_state")
    try:
        state = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"active notice state is not valid JSON: {exc}") from exc
    if not isinstance(state, dict):
        raise SystemExit("active notice state must be a JSON object")
    if state.get("schema") != ACTIVE_NOTICE_STATE_SCHEMA:
        raise SystemExit("active notice state schema mismatch")
    if state.get("guild_id") != config.get(GUILD_ENV):
        raise SystemExit("active notice state guild mismatch")
    if state.get("channel_id") != config.get(BETA_CHANNEL_ENV):
        raise SystemExit("active notice state channel mismatch")
    message_id = state.get("message_id")
    if not isinstance(message_id, str) or not message_id.isdigit():
        raise SystemExit("active notice state message_id invalid")
    if collect_metadata_guardrail_blockers(state):
        raise SystemExit("active notice state is not metadata-only")
    if report_contains_secret(state, config.get(TOKEN_ENV, "")):
        raise RuntimeError("active notice state would expose bot token")
    return state


def write_active_notice_state(path: Path, state: dict[str, Any]) -> None:
    protected_paths.reject_symlink_component(path, "active_notice_state")
    resolved = protected_paths.reject_protected_output_path(path, "active_notice_state")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def active_notice_reuse_diagnostic(
    *,
    active_notice_state_path: Path | None,
    active_notice_state_present: bool,
    active_message_id: str | None,
    update_existing: bool,
    dry_run: bool,
    confirmed_send: bool,
) -> dict[str, Any]:
    diagnostic = {
        "schema": ACTIVE_NOTICE_REUSE_DIAGNOSTIC_SCHEMA,
        "reuse_scope": "communication_state_only",
        "dry_run": dry_run,
        "confirmed_send": confirmed_send,
        "active_notice_state_path": (
            str(active_notice_state_path) if active_notice_state_path is not None else None
        ),
        "active_notice_state_present": active_notice_state_present,
        "active_message_id": active_message_id,
        "updates_existing_message": update_existing,
        "discord_http_method": "PATCH" if update_existing else "POST",
        "lead_decision": (
            "reuse_existing_active_notice_for_new_fresh_window_notice_only"
            if active_notice_state_present
            else "create_new_active_notice_only_after_guarded_fresh_window_notice"
        ),
        "when_wrapper_reports_approved_window_start_not_in_future": (
            "create_fresh_window; existing active notice may be patched only by a "
            "separately approved fresh-window notice"
        ),
        "fresh_window_required_after_stale_request": True,
        "active_notice_may_be_reused_for_new_window_notice": active_notice_state_present,
        "active_notice_may_suppress_everyone_on_patch": update_existing,
        "create_new_message_only_when_state_missing": True,
        "direct_helper_patch_changes_communication_state_only": True,
        "wait_requires_fresh_window_preconditions": True,
        "wait_only_decision_available_from_active_notice_state": False,
        "active_notice_state_is_notice_report": False,
        "active_notice_state_is_confirmed_beta_notice_report": False,
        "active_notice_state_satisfies_activation_preconditions": False,
        "active_notice_state_counts_as_confirmed_notice": False,
        "active_notice_state_counts_as_approved_runtime_evidence": False,
        "active_notice_state_counts_as_runtime_evidence": False,
        "active_notice_state_counts_toward_sdk": False,
        "active_notice_state_counts_toward_p0_dependency_chain": False,
        "active_notice_state_counts_as_readiness": False,
        "runtime_capture_allowed_by_active_notice_state": False,
        "server_operations_allowed_by_active_notice_state": False,
        "discord_send_allowed_by_active_notice_state": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "discord_beta_non_promotion": discord_beta_non_promotion_boundary(
            "active_notice_reuse_diagnostic"
        ),
        "non_authorization": dict(NON_AUTHORIZATION_FLAGS),
    }
    blockers = collect_metadata_guardrail_blockers(diagnostic)
    if blockers:
        raise ValueError("active notice reuse diagnostic is not metadata-only: " + ", ".join(blockers))
    return diagnostic


def build_event(
    event_type: str,
    *,
    user_id: int | str,
    map_name: str | None = None,
    issue_type: str | None = None,
    note: str | None = None,
    config: dict[str, str] | None = None,
) -> dict[str, Any]:
    if event_type not in EVENT_TYPES:
        raise ValueError(f"unsupported event_type: {event_type}")
    if map_name is not None and map_name not in ALLOWED_MAPS:
        raise ValueError(f"unsupported map: {map_name}")
    if issue_type is not None and issue_type not in ALLOWED_ISSUE_TYPES:
        raise ValueError(f"unsupported issue type: {issue_type}")
    if config is None:
        config = merged_config()
    event = {
        "schema": EVENT_SCHEMA,
        "event_type": event_type,
        "created_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "actor_alias": actor_alias(user_id, config.get(SALT_ENV, "")),
        "raw_user_id_retained": False,
        "raw_player_text_retained": False,
        "map": map_name,
        "issue_type": issue_type,
        "note": redacted_note(note),
        "redacted_metadata_only": True,
        "event_sink_semantics": "metadata_only",
        "communication_posture_only": True,
        "discord_beta_non_promotion": discord_beta_non_promotion_boundary("event"),
        "non_authorization": dict(NON_AUTHORIZATION_FLAGS),
    }
    compact_event = {key: value for key, value in event.items() if value is not None}
    validate_metadata_only_event(compact_event)
    return compact_event


def write_event(event: dict[str, Any], sink: Path) -> None:
    validate_metadata_only_event(event)
    protected_paths.reject_protected_output_path(sink, "event_sink")
    sink.parent.mkdir(parents=True, exist_ok=True)
    with sink.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")


def event_type_counts(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = {event_type: 0 for event_type in EVENT_TYPES}
    for event in events:
        event_type = event.get("event_type")
        if isinstance(event_type, str) and event_type in counts:
            counts[event_type] += 1
    return [
        {"event_type": event_type, "count": count}
        for event_type, count in counts.items()
        if count > 0
    ]


def event_sort_key(event: dict[str, Any]) -> tuple[str, int]:
    created_at = event.get("created_at_utc")
    line_number = event.get("line_number")
    return (
        created_at if isinstance(created_at, str) else "",
        line_number if isinstance(line_number, int) else 0,
    )


def latest_events_by_actor(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for event in sorted(events, key=event_sort_key):
        actor_alias_value = event.get("actor_alias")
        if not isinstance(actor_alias_value, str) or not actor_alias_value:
            continue
        latest[actor_alias_value] = event
    return [
        {
            "actor_alias": actor_alias,
            "event_type": event.get("event_type"),
            "map": event.get("map"),
            "issue_type": event.get("issue_type"),
            "created_at_utc": event.get("created_at_utc"),
            "line_number": event.get("line_number"),
            "raw_user_id_retained": False,
            "event_sink_semantics": "metadata_only",
            "communication_posture_only": True,
        }
        for actor_alias, event in sorted(
            latest.items(),
            key=lambda item: event_sort_key(item[1]),
            reverse=True,
        )
    ]


def latest_tester_milestones_by_actor(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    milestone_events = [
        event for event in events if event.get("event_type") in TESTER_STATUS_EVENT_TYPES
    ]
    return latest_events_by_actor(milestone_events)


def tester_status_summary(
    events: list[dict[str, Any]],
    latest_milestones: list[dict[str, Any]],
    hints: list[dict[str, Any]],
) -> dict[str, Any]:
    state_counts = {event_type: 0 for event_type in TESTER_STATUS_EVENT_TYPES}
    in_server_by_map = {map_name: 0 for map_name in ALLOWED_MAPS}
    active_tester_aliases: set[str] = set()
    for event in latest_milestones:
        event_type = event.get("event_type")
        if event_type in state_counts:
            state_counts[event_type] += 1
        if event_type == "in_server" and event.get("map") in in_server_by_map:
            in_server_by_map[str(event["map"])] += 1
        if event_type in {"started", "loading", "in_server"}:
            actor_alias_value = event.get("actor_alias")
            if isinstance(actor_alias_value, str):
                active_tester_aliases.add(actor_alias_value)

    summary = {
        "schema": TESTER_STATUS_SUMMARY_SCHEMA,
        "workflow": "single_editable_notice_status_summary_button",
        "single_operational_message_required": True,
        "one_editable_notice": True,
        "status_summary_button_custom_id": BETA_STATUS_SUMMARY_CUSTOM_ID,
        "status_summary_button_writes_event": False,
        "status_summary_response_mode": STATUS_SUMMARY_RESPONSE_MODE,
        "status_summary_uses_local_event_sink_only": True,
        "status_summary_reads_discord": False,
        "status_summary_sends_discord": False,
        "status_summary_ephemeral_response_only": True,
        "status_summary_creates_channel_message": False,
        "status_summary_updates_operational_message": False,
        "status_summary_creates_event": False,
        "status_summary_claims_evidence": False,
        "status_summary_claims_progress": False,
        "status_summary_claims_readiness": False,
        "summary_does_not_append_event_row": True,
        "latest_tester_milestone_count": len(latest_milestones),
        "active_tester_alias_count": len(active_tester_aliases),
        "state_counts": [
            {"state": event_type, "count": state_counts[event_type]}
            for event_type in TESTER_STATUS_EVENT_TYPES
        ],
        "in_server_by_map": [
            {"map": map_name, "count": in_server_by_map[map_name]}
            for map_name in ALLOWED_MAPS
        ],
        "issue_event_count": sum(1 for event in events if event.get("event_type") == "issue"),
        "attention_hint_count": len(hints),
        "raw_user_id_retained": False,
        "raw_discord_payload_retention_allowed": False,
        "event_sink_semantics": "metadata_only",
        "redacted_metadata_only": True,
        "communication_posture_only": True,
        "discord_events_are_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "counts_as_readiness": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "stable_sdk_ready": False,
        "discord_beta_non_promotion": discord_beta_non_promotion_boundary(
            "tester_status_summary"
        ),
        "non_authorization": dict(NON_AUTHORIZATION_FLAGS),
    }
    blockers = collect_metadata_guardrail_blockers(summary)
    if blockers:
        raise ValueError("tester status summary is not metadata-only: " + ", ".join(blockers))
    return summary


def count_by_name(rows: list[dict[str, Any]], key: str, name: str) -> int:
    for row in rows:
        if row.get(key) == name and isinstance(row.get("count"), int):
            return int(row["count"])
    return 0


def format_tester_status_summary(summary: dict[str, Any]) -> str:
    status = summary.get("tester_status_summary", summary)
    if not isinstance(status, dict) or status.get("schema") != TESTER_STATUS_SUMMARY_SCHEMA:
        return "Resumen beta local no disponible. Coordinacion solamente; no evidencia."
    state_counts = status.get("state_counts")
    map_counts = status.get("in_server_by_map")
    if not isinstance(state_counts, list):
        state_counts = []
    if not isinstance(map_counts, list):
        map_counts = []
    state_line = " | ".join(
        f"{event_type}={count_by_name(state_counts, 'state', event_type)}"
        for event_type in TESTER_STATUS_EVENT_TYPES
    )
    map_line = " | ".join(
        f"{map_name}={count_by_name(map_counts, 'map', map_name)}"
        for map_name in ALLOWED_MAPS
    )
    return "\n".join(
        [
            "Resumen beta local: metadata redacted; coordinacion solamente.",
            (
                f"Activos={status.get('active_tester_alias_count', 0)}; "
                f"milestones={status.get('latest_tester_milestone_count', 0)}; "
                f"issues={status.get('issue_event_count', 0)}; "
                f"atencion={status.get('attention_hint_count', 0)}."
            ),
            f"Estados: {state_line}",
            f"En mapa: {map_line}",
            "No autoriza Discord sends, RCON, runtime capture; no evidencia, SDK/P0 ni readiness.",
        ]
    )[:1900]


def attention_hints(latest_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    for event in latest_events:
        event_type = event.get("event_type")
        hint: str | None = None
        if event_type == "issue":
            hint = "review_redacted_issue_before_relying_on_tester"
        elif event_type == "cluster_transfer":
            hint = "confirm_target_map_before_runtime_window_instruction"
        elif event_type == "loading":
            hint = "wait_or_check_timeout_before_requesting_logout_cycle"
        if hint is None:
            continue
        hints.append(
            {
                "actor_alias": event.get("actor_alias"),
                "latest_event_type": event_type,
                "map": event.get("map"),
                "issue_type": event.get("issue_type"),
                "hint": hint,
                "process_control": "none",
                "event_sink_semantics": "metadata_only",
                "communication_posture_only": True,
                "non_authorization": dict(NON_AUTHORIZATION_FLAGS),
            }
        )
    return hints


def validate_metadata_only_event_summary(summary: dict[str, Any]) -> None:
    blockers: list[str] = []
    if summary.get("schema") != EVENT_SUMMARY_SCHEMA:
        blockers.append("$.schema")
    if summary.get("redacted_metadata_only") is not True:
        blockers.append("$.redacted_metadata_only")
    if summary.get("event_sink_semantics") != "metadata_only":
        blockers.append("$.event_sink_semantics")
    if summary.get("raw_user_id_retention_allowed") is not False:
        blockers.append("$.raw_user_id_retention_allowed")
    if summary.get("discord_events_are_evidence") is not False:
        blockers.append("$.discord_events_are_evidence")

    non_authorization = summary.get("non_authorization")
    if not isinstance(non_authorization, dict):
        blockers.append("$.non_authorization")
    else:
        for key in NON_AUTHORIZATION_FLAGS:
            if non_authorization.get(key) is not False:
                blockers.append(f"$.non_authorization.{key}")

    blockers.extend(collect_metadata_guardrail_blockers(summary))
    if blockers:
        raise ValueError(
            "event summary is not metadata-only: " + ", ".join(sorted(set(blockers)))
        )


def summarize_event_sink(
    sink: Path,
    *,
    recent_limit: int = 10,
) -> dict[str, Any]:
    if recent_limit < 1:
        raise ValueError("recent_limit must be positive")
    protected_paths.reject_symlink_component(sink, "event_sink")
    source_exists = sink.exists()
    events: list[dict[str, Any]] = []
    invalid_rows: list[dict[str, Any]] = []
    resolved = sink
    if source_exists:
        resolved = protected_paths.reject_protected_input_path(sink, "event_sink")
        if not resolved.is_file():
            raise SystemExit(f"event_sink is not a regular file: {resolved}")
        for line_number, raw_line in enumerate(resolved.read_text(encoding="utf-8").splitlines(), 1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise ValueError("event row must be a JSON object")
                event = normalize_metadata_only_event(event)
            except (json.JSONDecodeError, ValueError) as exc:
                invalid_rows.append(
                    {
                        "line_number": line_number,
                        "reason": exc.__class__.__name__,
                        "detail": str(exc)[:240],
                        "raw_line_retained": False,
                        "event_sink_semantics": "metadata_only",
                    }
                )
                continue
            copied = dict(event)
            copied["line_number"] = line_number
            events.append(copied)

    latest_actor_events = latest_events_by_actor(events)
    latest_milestones = latest_tester_milestones_by_actor(events)
    hints = attention_hints(latest_actor_events)
    status_summary = tester_status_summary(events, latest_milestones, hints)
    recent_events = [
        {
            "event_type": event.get("event_type"),
            "actor_alias": event.get("actor_alias"),
            "map": event.get("map"),
            "issue_type": event.get("issue_type"),
            "created_at_utc": event.get("created_at_utc"),
            "line_number": event.get("line_number"),
            "raw_user_id_retained": False,
            "event_sink_semantics": "metadata_only",
            "communication_posture_only": True,
        }
        for event in sorted(events, key=event_sort_key, reverse=True)[:recent_limit]
    ]
    summary = {
        "schema": EVENT_SUMMARY_SCHEMA,
        "event_sink": str(resolved),
        "event_sink_exists": source_exists,
        "event_sink_semantics": "metadata_only",
        "redacted_metadata_only": True,
        "raw_user_id_retention_allowed": False,
        "raw_discord_payload_retention_allowed": False,
        "communication_posture_only": True,
        "discord_events_are_evidence": False,
        "single_operational_message_required": True,
        "operational_message_style": SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE,
        "status_summary_response_mode": STATUS_SUMMARY_RESPONSE_MODE,
        "status_summary_creates_channel_message": False,
        "status_summary_updates_operational_message": False,
        "status_summary_creates_event": False,
        "status_summary_claims_evidence": False,
        "status_summary_claims_progress": False,
        "status_summary_claims_readiness": False,
        "valid_event_count": len(events),
        "invalid_event_count": len(invalid_rows),
        "actor_alias_count": len({event.get("actor_alias") for event in events if event.get("actor_alias")}),
        "event_type_counts": event_type_counts(events),
        "latest_event_by_actor": latest_actor_events,
        "latest_tester_milestone_by_actor": latest_milestones,
        "tester_status_summary": status_summary,
        "recent_events": recent_events,
        "attention_hint_count": len(hints),
        "attention_hints": hints,
        "invalid_rows": invalid_rows,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "discord_beta_non_promotion": discord_beta_non_promotion_boundary(
            "event_summary"
        ),
        "non_authorization": dict(NON_AUTHORIZATION_FLAGS),
        "non_claim": (
            "Discord beta bridge event summary only; it does not authorize Discord, "
            "RCON, server operations, live-log reads, runtime capture, runtime "
            "evidence, SDK/P0 progress, public readiness, stable readiness, Plugin "
            "Hub readiness, or publication."
        ),
    }
    validate_metadata_only_event_summary(summary)
    return summary


def validate_metadata_only_button_interaction_result(result: dict[str, Any]) -> None:
    blockers: list[str] = []
    if result.get("schema") != BUTTON_INTERACTION_RESULT_SCHEMA:
        blockers.append("$.schema")
    if result.get("redacted_metadata_only") is not True:
        blockers.append("$.redacted_metadata_only")
    if result.get("event_sink_semantics") != "metadata_only":
        blockers.append("$.event_sink_semantics")
    if result.get("ephemeral_acknowledgement") is not True:
        blockers.append("$.ephemeral_acknowledgement")
    for key in (
        "creates_channel_message",
        "creates_followup_message",
        "updates_operational_message",
        "reads_discord",
        "sends_discord",
        "uses_network",
        "uses_webhook",
        "retains_raw_user_id",
        "retains_raw_player_text",
        "retains_secret_values",
        "claims_evidence",
        "claims_progress",
        "claims_readiness",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_progress",
        "counts_as_p0_progress",
        "counts_as_readiness",
        "public_sdk_ready",
        "runtime_ready",
        "stable_sdk_ready",
        "plugin_hub_ready",
        "publication_ready",
        "discord_authorized",
    ):
        if result.get(key) is not False:
            blockers.append(f"$.{key}")

    non_authorization = result.get("non_authorization")
    if not isinstance(non_authorization, dict):
        blockers.append("$.non_authorization")
    else:
        for key in NON_AUTHORIZATION_FLAGS:
            if non_authorization.get(key) is not False:
                blockers.append(f"$.non_authorization.{key}")

    blockers.extend(collect_metadata_guardrail_blockers(result))
    if blockers:
        raise ValueError(
            "button interaction result is not metadata-only: "
            + ", ".join(sorted(set(blockers)))
        )


def handle_beta_control_interaction(
    custom_id: str,
    *,
    user_id: int | str,
    config: dict[str, str] | None = None,
    event_sink: Path | None = None,
    recent_limit: int = 5,
) -> dict[str, Any]:
    """Apply a beta button interaction locally and return the ephemeral response plan."""
    parsed = parse_beta_control_custom_id(custom_id)
    if parsed is None:
        raise ValueError("unsupported beta control custom_id")
    if config is None:
        config = merged_config()
    sink = event_sink if event_sink is not None else configured_event_sink(config)
    summary_only = parsed.get("summary_only") is True
    event: dict[str, Any] | None = None
    event_summary: dict[str, Any] | None = None
    if summary_only:
        event_summary = summarize_event_sink(sink, recent_limit=recent_limit)
        acknowledgement_text = format_tester_status_summary(event_summary)
    else:
        event = build_event(
            parsed["event_type"],
            user_id=user_id,
            map_name=parsed.get("map_name"),
            issue_type=parsed.get("issue_type"),
            note=None,
            config=config,
        )
        write_event(event, sink)
        acknowledgement_text = str(parsed["response"])

    result = {
        "schema": BUTTON_INTERACTION_RESULT_SCHEMA,
        "custom_id": custom_id,
        "button_custom_id_prefix": BETA_CONTROL_CUSTOM_ID_PREFIX,
        "event_type": parsed["event_type"],
        "tester_status": parsed.get("tester_status"),
        "map": parsed.get("map_name"),
        "issue_type": parsed.get("issue_type"),
        "summary_only": summary_only,
        "writes_event": not summary_only,
        "local_event_written": not summary_only,
        "local_event": event,
        "event_sink": str(sink),
        "event_summary": event_summary,
        "tester_status_summary": (
            event_summary.get("tester_status_summary")
            if isinstance(event_summary, dict)
            else None
        ),
        "response_mode": (
            STATUS_SUMMARY_RESPONSE_MODE
            if summary_only
            else "ephemeral_ack_and_local_event_write"
        ),
        "acknowledgement_text": acknowledgement_text,
        "ephemeral_acknowledgement": True,
        "creates_channel_message": False,
        "creates_followup_message": False,
        "updates_operational_message": False,
        "single_operational_message_required": True,
        "one_editable_notice": True,
        "operational_message_style": SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE,
        "reads_discord": False,
        "sends_discord": False,
        "uses_network": False,
        "uses_webhook": False,
        "retains_raw_user_id": False,
        "retains_raw_player_text": False,
        "retains_secret_values": False,
        "redacted_metadata_only": True,
        "event_sink_semantics": "metadata_only",
        "communication_posture_only": True,
        "claims_evidence": False,
        "claims_progress": False,
        "claims_readiness": False,
        "discord_events_are_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "counts_as_readiness": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "stable_sdk_ready": False,
        "plugin_hub_ready": False,
        "publication_ready": False,
        "discord_authorized": False,
        "discord_beta_non_promotion": discord_beta_non_promotion_boundary(
            "button_interaction_result"
        ),
        "non_authorization": dict(NON_AUTHORIZATION_FLAGS),
    }
    compact_result = {key: value for key, value in result.items() if value is not None}
    validate_metadata_only_button_interaction_result(compact_result)
    return compact_result


def sanitized_notice_content(content: str) -> str:
    cleaned = "\n".join(line.rstrip() for line in content.strip().splitlines()).strip()
    if not cleaned:
        raise ValueError("bot notice content must be non-empty")
    if len(cleaned) > 1800:
        raise ValueError("bot notice content must be <= 1800 characters")
    if FORBIDDEN_NOTICE_TEXT_RE.search(cleaned) or DISCORD_TOKEN_SHAPE_RE.search(cleaned):
        raise ValueError("bot notice content contains forbidden secret/evidence/readiness text")
    return cleaned


def content_mentions_everyone(content: str) -> bool:
    return MENTION_EVERYONE_RE.search(content) is not None


def allowed_mentions_parse_for_content(content: str) -> list[str]:
    return ["everyone"] if content_mentions_everyone(content) else []


def strip_everyone_mentions_for_update(content: str) -> str:
    return MENTION_EVERYONE_RE.sub("", content).strip()


def bot_notice_plan_receipt(
    *,
    content: str,
    config: dict[str, str],
    with_beta_controls: bool,
    update_active_notice_requested: bool,
    update_existing: bool,
    active_message_id: str | None,
) -> tuple[str, dict[str, Any]]:
    components = beta_control_components() if with_beta_controls else []
    component_custom_ids = [
        component["custom_id"]
        for row in components
        for component in row.get("components", [])
        if isinstance(component, dict) and isinstance(component.get("custom_id"), str)
    ]
    embeds = beta_notice_embeds() if with_beta_controls else []
    operational_embed_metadata = (
        beta_operational_embed_metadata(embeds=embeds, components=components)
        if with_beta_controls
        else None
    )
    http_method = "PATCH" if update_existing else "POST"
    endpoint_kind = "channel_message_update" if update_existing else "channel_message_create"
    payload = {
        "schema": DRY_RUN_RECEIPT_SCHEMA,
        "guild_id": config.get(GUILD_ENV, ""),
        "channel_id": config.get(BETA_CHANNEL_ENV, ""),
        "expected_guild_id": EXPECTED_GUILD_ID,
        "expected_channel_id": EXPECTED_CHANNEL_ID,
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "content_length": len(content),
        "content_mentions_everyone": content_mentions_everyone(content),
        "allowed_mentions_parse": allowed_mentions_parse_for_content(content),
        "with_beta_controls": with_beta_controls,
        "component_custom_ids": component_custom_ids,
        "component_count": len(component_custom_ids),
        "operational_embed_metadata": operational_embed_metadata,
        "embed_count": len(embeds),
        "update_active_notice_requested": update_active_notice_requested,
        "update_existing": update_existing,
        "active_message_id": active_message_id if update_existing else None,
        "discord_http_method": http_method,
        "discord_endpoint_kind": endpoint_kind,
        "operational_message_style": SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE,
        "single_updated_embed_buttons_message_preferred": True,
        "edit_existing_message_when_active_notice_state_present": True,
        "post_only_when_active_notice_state_missing": True,
        "single_operational_message_required": True,
        "single_editable_embed_required": True,
        "no_flood_single_message_enforced": True,
        "webhook_real_sends_deprecated": True,
        "uses_webhook": False,
        "redacted_metadata_only": True,
        "event_sink_semantics": "metadata_only",
        "communication_posture_only": True,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        **DISCORD_BETA_NON_PROMOTION_FLAGS,
        "discord_beta_non_promotion": discord_beta_non_promotion_boundary(
            "dry_run_receipt"
        ),
        "non_authorization": dict(NON_AUTHORIZATION_FLAGS),
    }
    blockers = collect_metadata_guardrail_blockers(payload)
    if blockers:
        raise ValueError("dry-run receipt payload is not metadata-only: " + ", ".join(blockers))
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    receipt = DRY_RUN_RECEIPT_PREFIX + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return receipt, payload


def bot_notice_report(
    *,
    content: str,
    config: dict[str, str],
    dry_run: bool,
    confirmed_send: bool,
    with_beta_controls: bool = False,
    active_notice_state_path: Path | None = None,
    active_message_id: str | None = None,
    update_existing: bool = False,
    active_notice_state_present: bool = False,
    requested_content_mentions_everyone: bool | None = None,
    dry_run_receipt_validated: bool = False,
    sent: bool = False,
    http_status: int | None = None,
) -> dict[str, Any]:
    embeds = beta_notice_embeds() if with_beta_controls else []
    components = beta_control_components() if with_beta_controls else []
    component_custom_ids = [
        component["custom_id"]
        for row in components
        for component in row.get("components", [])
        if isinstance(component, dict) and isinstance(component.get("custom_id"), str)
    ]
    component_action_map = beta_control_action_map(components)
    status_summary_actions = [
        item for item in component_action_map if item.get("summary_only") is True
    ]
    operational_embed_metadata = (
        beta_operational_embed_metadata(embeds=embeds, components=components)
        if with_beta_controls
        else None
    )
    if with_beta_controls and active_notice_state_path is None:
        raise ValueError("beta control notice requires active notice update state")
    if with_beta_controls and len(embeds) != 1:
        raise ValueError("beta control notice requires exactly one embed")
    if with_beta_controls and len(status_summary_actions) != 1:
        raise ValueError("beta control notice requires exactly one status summary button")
    if len(set(component_custom_ids)) != len(component_custom_ids):
        raise ValueError("beta control custom_id values must be unique")
    if FORBIDDEN_NOTICE_TEXT_RE.search(content) or DISCORD_TOKEN_SHAPE_RE.search(content):
        raise ValueError("bot notice content contains forbidden secret/evidence/readiness text")
    http_method = "PATCH" if update_existing else "POST"
    allowed_mentions_parse = allowed_mentions_parse_for_content(content)
    requested_mentions_everyone = (
        content_mentions_everyone(content)
        if requested_content_mentions_everyone is None
        else requested_content_mentions_everyone
    )
    dry_run_receipt, dry_run_receipt_inputs = bot_notice_plan_receipt(
        content=content,
        config=config,
        with_beta_controls=with_beta_controls,
        update_active_notice_requested=active_notice_state_path is not None,
        update_existing=update_existing,
        active_message_id=active_message_id,
    )
    notice = {
        "schema": BOT_NOTICE_SCHEMA,
        "target": "discord_beta_bot_channel",
        "guild_id": config.get(GUILD_ENV, ""),
        "channel_id": config.get(BETA_CHANNEL_ENV, ""),
        "expected_guild_id": EXPECTED_GUILD_ID,
        "expected_channel_id": EXPECTED_CHANNEL_ID,
        "bidirectional_channel_id": EXPECTED_CHANNEL_ID,
        "bot_send_channel_id": EXPECTED_CHANNEL_ID,
        "tester_interaction_channel_id": EXPECTED_CHANNEL_ID,
        "content": content,
        "content_mentions_everyone": content_mentions_everyone(content),
        "requested_content_mentions_everyone": requested_mentions_everyone,
        "allowed_mentions_parse": allowed_mentions_parse,
        "single_operational_message_required": True,
        "operational_message_kind": "single_active_beta_notice",
        "operational_message_style": SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE,
        "active_notice_state_required_for_beta_controls": True,
        "no_flood_single_message_enforced": True,
        "real_send_requires_active_notice_update": True,
        "real_send_requires_beta_controls": True,
        "single_editable_embed_required": True,
        "single_editable_embed": (len(embeds) == 1) if with_beta_controls else False,
        "embed_enabled": with_beta_controls,
        "embed_count": len(embeds),
        "embed_claims_evidence": False,
        "embed_claims_progress": False,
        "embed_claims_readiness": False,
        "button_controls_enabled": with_beta_controls,
        "embeds": embeds,
        "components": components,
        "component_custom_ids": component_custom_ids,
        "component_custom_ids_unique": len(set(component_custom_ids)) == len(component_custom_ids),
        "component_action_map": component_action_map,
        "operational_embed_metadata": operational_embed_metadata,
        "component_count": len(component_custom_ids),
        "button_control_metadata_locally_representable": True,
        "button_interaction_response_mode": "ephemeral_ack_and_local_event_write",
        "button_interactions_ephemeral_ack_only": True,
        "button_interactions_create_channel_messages": False,
        "button_interactions_create_followup_messages": False,
        "button_interactions_update_operational_message": False,
        "button_events_claim_evidence": False,
        "button_events_claim_progress": False,
        "button_events_claim_readiness": False,
        "status_summary_action_count": len(status_summary_actions),
        "status_summary_button_custom_id": BETA_STATUS_SUMMARY_CUSTOM_ID,
        "status_summary_response_mode": STATUS_SUMMARY_RESPONSE_MODE,
        "status_summary_ephemeral_response_only": True,
        "status_summary_uses_local_event_sink_only": True,
        "status_summary_metadata_only": True,
        "status_summary_button_writes_event": False,
        "status_summary_creates_channel_message": False,
        "status_summary_updates_operational_message": False,
        "status_summary_creates_event": False,
        "status_summary_claims_evidence": False,
        "status_summary_claims_progress": False,
        "status_summary_claims_readiness": False,
        "tester_status_workflow": (
            beta_tester_status_workflow(components) if with_beta_controls else None
        ),
        "editable_notice_workflow": editable_notice_workflow(
            dry_run=dry_run,
            with_beta_controls=with_beta_controls,
            update_active_notice_requested=active_notice_state_path is not None,
            active_notice_state_present=active_notice_state_present,
            update_existing=update_existing,
        ),
        "operational_message_policy": operational_message_policy(
            dry_run=dry_run,
            with_beta_controls=with_beta_controls,
            update_active_notice_requested=active_notice_state_path is not None,
            active_notice_state_present=active_notice_state_present,
            update_existing=update_existing,
            component_count=len(component_custom_ids),
            embed_count=len(embeds),
        ),
        "preserves_interactive_buttons": with_beta_controls and bool(component_custom_ids),
        "interactive_buttons_preserved_on_update": (
            update_existing and with_beta_controls and bool(component_custom_ids)
        ),
        "delivery": "bot_channel_message",
        "discord_http_method": http_method,
        "discord_endpoint_kind": (
            "channel_message_update" if update_existing else "channel_message_create"
        ),
        "webhook_deprecated": True,
        "webhook_real_sends_deprecated": True,
        "uses_webhook": False,
        "webhook_url_embedded": False,
        "secret_values_embedded": False,
        "dry_run": dry_run,
        "confirmed_send": confirmed_send,
        "dry_run_required_before_real_send": True,
        "dry_run_receipt_required_for_real_send": True,
        "dry_run_receipt_schema": DRY_RUN_RECEIPT_SCHEMA,
        "dry_run_receipt": dry_run_receipt,
        "dry_run_receipt_inputs": dry_run_receipt_inputs,
        "dry_run_receipt_validated": dry_run_receipt_validated,
        "active_notice_update_requested": active_notice_state_path is not None,
        "active_notice_state_path": str(active_notice_state_path) if active_notice_state_path else None,
        "active_notice_state_present": active_notice_state_present,
        "active_message_id": active_message_id,
        "active_notice_reuse_diagnostic": active_notice_reuse_diagnostic(
            active_notice_state_path=active_notice_state_path,
            active_notice_state_present=active_notice_state_present,
            active_message_id=active_message_id,
            update_existing=update_existing,
            dry_run=dry_run,
            confirmed_send=confirmed_send,
        ),
        "updates_existing_message": update_existing,
        "creates_new_message": sent and not update_existing,
        "would_create_new_message": not update_existing,
        "new_message_only_when_active_notice_state_missing": True,
        "existing_active_notice_updates_in_place": True,
        "single_updated_embed_buttons_message_preferred": True,
        "edit_existing_message_when_active_notice_state_present": True,
        "post_only_when_active_notice_state_missing": True,
        "mention_everyone_only_on_create": with_beta_controls,
        "mention_everyone_suppressed_on_update": (
            update_existing
            and requested_mentions_everyone
            and not content_mentions_everyone(content)
        ),
        "send_performed": sent,
        "discord_sent": sent,
        "http_status": http_status,
        "redacted_metadata_only": True,
        "raw_player_text_retained": False,
        "event_sink_semantics": "metadata_only",
        "communication_posture_only": True,
        "counts_as_readiness": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "plugin_hub_ready": False,
        "publication_ready": False,
        **DISCORD_BETA_NON_PROMOTION_FLAGS,
        "discord_beta_non_promotion": discord_beta_non_promotion_boundary(
            "bot_notice_report"
        ),
        "non_authorization": dict(NON_AUTHORIZATION_FLAGS),
        "non_claim": (
            "Bot notice metadata only; it does not authorize live ops, prove runtime "
            "evidence, or count as SDK/P0 progress, readiness, Plugin Hub readiness, "
            "or publication."
        ),
    }
    blockers = collect_metadata_guardrail_blockers(notice)
    if blockers:
        raise ValueError("bot notice report is not metadata-only: " + ", ".join(blockers))
    if report_contains_secret(notice, config.get(TOKEN_ENV, "")):
        raise RuntimeError("bot notice report would expose bot token")
    return notice


def send_bot_notice(
    env_file: Path,
    *,
    content: str,
    dry_run: bool,
    confirmed_send: bool,
    with_beta_controls: bool = False,
    update_active_notice: bool = False,
    dry_run_receipt: str | None = None,
) -> dict[str, Any]:
    config = merged_config(env_file)
    if with_beta_controls and not update_active_notice:
        raise SystemExit(
            "refusing beta control notice without --update-active-notice; "
            "single active operational message is required"
        )
    if dry_run:
        blockers: list[str] = []
        if config[GUILD_ENV] != EXPECTED_GUILD_ID:
            blockers.append("guild_id_mismatch")
        if config[BETA_CHANNEL_ENV] != EXPECTED_CHANNEL_ID:
            blockers.append("beta_channel_id_mismatch")
        if blockers:
            raise SystemExit(json.dumps({"valid": False, "blockers": blockers}, indent=2))
    else:
        report = check_config(env_file, require_token=True)
        if not report["valid"]:
            raise SystemExit(json.dumps(report, indent=2, sort_keys=True))
    if not dry_run and not confirmed_send:
        raise SystemExit("refusing bot Discord send without --confirm-approved-send after dry-run review")
    if not dry_run and not update_active_notice:
        raise SystemExit(
            "refusing bot Discord send without --update-active-notice; "
            "single editable beta notice is required"
        )
    if not dry_run and not with_beta_controls:
        raise SystemExit(
            "refusing bot Discord send without --with-beta-controls; "
            "beta tester flow requires the editable status/control embed"
        )

    cleaned = sanitized_notice_content(content)
    active_state_path = configured_active_notice_state(config)
    update_state = None
    if update_active_notice:
        try:
            protected_paths.reject_symlink_component(active_state_path, "active_notice_state")
            protected_paths.reject_protected_output_path(active_state_path, "active_notice_state")
        except SystemExit as exc:
            raise SystemExit(f"active notice state path rejected: {exc}") from exc
        update_state = read_active_notice_state(active_state_path, config)
    if dry_run:
        active_state_present = isinstance(update_state, dict)
        report_content = (
            strip_everyone_mentions_for_update(cleaned)
            if active_state_present
            else cleaned
        )
        return bot_notice_report(
            content=report_content,
            config=config,
            dry_run=True,
            confirmed_send=False,
            with_beta_controls=with_beta_controls,
            active_notice_state_path=active_state_path if update_active_notice else None,
            active_message_id=(
                str(update_state["message_id"]) if active_state_present else None
            ),
            update_existing=active_state_present,
            active_notice_state_present=active_state_present,
            requested_content_mentions_everyone=content_mentions_everyone(cleaned),
        )

    update_existing = update_active_notice and isinstance(update_state, dict)
    outgoing_content = cleaned
    if update_existing:
        outgoing_content = strip_everyone_mentions_for_update(outgoing_content)
    expected_receipt, _receipt_inputs = bot_notice_plan_receipt(
        content=outgoing_content,
        config=config,
        with_beta_controls=with_beta_controls,
        update_active_notice_requested=update_active_notice,
        update_existing=update_existing,
        active_message_id=str(update_state["message_id"]) if update_existing else None,
    )
    if not dry_run_receipt:
        raise SystemExit(
            "refusing bot Discord send without --dry-run-receipt from reviewed dry run"
        )
    if dry_run_receipt != expected_receipt:
        raise SystemExit("refusing bot Discord send because --dry-run-receipt does not match")
    payload = {
        "content": outgoing_content,
        "allowed_mentions": {"parse": allowed_mentions_parse_for_content(outgoing_content)},
    }
    if with_beta_controls:
        payload["embeds"] = beta_notice_embeds()
        payload["components"] = beta_control_components()
    if update_existing:
        endpoint = (
            f"https://discord.com/api/v10/channels/{config[BETA_CHANNEL_ENV]}/messages/"
            f"{update_state['message_id']}"
        )
        method = "PATCH"
    else:
        endpoint = f"https://discord.com/api/v10/channels/{config[BETA_CHANNEL_ENV]}/messages"
        method = "POST"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "ObeliskDiscordBetaBot/1",
            "Authorization": f"Bot {config[TOKEN_ENV]}",
        },
        method=method,
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status >= 300:
            raise SystemExit(f"discord bot returned HTTP {response.status}")
        status = int(response.status)
        response_body = response.read().decode("utf-8") if update_active_notice else ""
    active_message_id = str(update_state["message_id"]) if update_existing else None
    if update_active_notice and not update_existing:
        try:
            body = json.loads(response_body) if response_body else {}
        except json.JSONDecodeError:
            body = {}
        message_id = body.get("id")
        if not isinstance(message_id, str) or not message_id.isdigit():
            raise SystemExit("discord bot response missing message id for active notice state")
        active_message_id = message_id
        write_active_notice_state(
            active_state_path,
            active_notice_state(config=config, message_id=message_id, source="send_bot_notice"),
        )
    elif update_active_notice and update_existing:
        write_active_notice_state(
            active_state_path,
            active_notice_state(config=config, message_id=active_message_id, source="send_bot_notice"),
        )
    return bot_notice_report(
        content=outgoing_content,
        config=config,
        dry_run=False,
        confirmed_send=True,
        with_beta_controls=with_beta_controls,
        active_notice_state_path=active_state_path if update_active_notice else None,
        active_message_id=active_message_id,
        update_existing=update_existing,
        active_notice_state_present=isinstance(update_state, dict),
        requested_content_mentions_everyone=content_mentions_everyone(cleaned),
        dry_run_receipt_validated=True,
        sent=True,
        http_status=status,
    )


def run_bot(env_file: Path) -> int:
    report = check_config(env_file, require_token=True)
    if not report["valid"]:
        print(json.dumps(report, indent=2, sort_keys=True), file=sys.stderr)
        return 1

    try:
        import discord  # type: ignore
        from discord import app_commands  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on optional dependency
        raise SystemExit(f"discord.py is required for --run: {exc}") from exc

    config = merged_config(env_file)
    event_sink = configured_event_sink(config)
    guild = discord.Object(id=int(config[GUILD_ENV]))
    channel_id = int(config[BETA_CHANNEL_ENV])
    intents = discord.Intents.none()
    intents.guilds = True
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)

    async def reject_wrong_channel(interaction: discord.Interaction) -> bool:
        if interaction.channel_id != channel_id:
            await interaction.response.send_message(
                "Usa el canal beta configurado para Obelisk.", ephemeral=True
            )
            return True
        return False

    async def record(
        interaction: discord.Interaction,
        event_type: str,
        *,
        map_name: str | None = None,
        issue_type: str | None = None,
        note: str | None = None,
        response: str,
    ) -> None:
        if await reject_wrong_channel(interaction):
            return
        event = build_event(
            event_type,
            user_id=interaction.user.id,
            map_name=map_name,
            issue_type=issue_type,
            note=note,
            config=config,
        )
        write_event(event, event_sink)
        await interaction.response.send_message(response, ephemeral=True)

    async def send_status_summary(interaction: discord.Interaction) -> None:
        if await reject_wrong_channel(interaction):
            return
        summary = summarize_event_sink(event_sink, recent_limit=5)
        await interaction.response.send_message(
            format_tester_status_summary(summary),
            ephemeral=True,
        )

    @client.event
    async def on_interaction(interaction: discord.Interaction) -> None:
        if await reject_wrong_channel(interaction):
            return
        data = getattr(interaction, "data", {}) or {}
        custom_id = data.get("custom_id") if isinstance(data, dict) else None
        if not isinstance(custom_id, str) or not custom_id.startswith(BETA_CONTROL_CUSTOM_ID_PREFIX):
            return
        try:
            result = handle_beta_control_interaction(
                custom_id,
                user_id=interaction.user.id,
                config=config,
                event_sink=event_sink,
            )
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.send_message(
            result["acknowledgement_text"],
            ephemeral=True,
        )

    @tree.command(name="obelisk_status", description="Muestra el estado operativo beta.", guild=guild)
    async def obelisk_status(interaction: discord.Interaction) -> None:
        await send_status_summary(interaction)

    @tree.command(name="obelisk_ready", description="Estoy disponible para probar.", guild=guild)
    async def obelisk_ready(interaction: discord.Interaction, map_name: str) -> None:
        await record(interaction, "ready", map_name=map_name, response="Disponibilidad registrada.")

    @tree.command(name="obelisk_joined", description="Estoy dentro del mapa.", guild=guild)
    async def obelisk_joined(interaction: discord.Interaction, map_name: str) -> None:
        await record(interaction, "joined", map_name=map_name, response="Entrada registrada.")

    @tree.command(name="obelisk_logout_ready", description="Estoy listo para desconectar.", guild=guild)
    async def obelisk_logout_ready(interaction: discord.Interaction) -> None:
        await record(
            interaction,
            "logout_ready",
            response=(
                "Listo para logout registrado. Mantente dentro hasta confirmacion del "
                "observer o del equipo si estas en ventana de captura."
            ),
        )

    @tree.command(name="obelisk_issue", description="Reporta un problema redacted.", guild=guild)
    async def obelisk_issue(interaction: discord.Interaction, issue_type: str, note: str = "") -> None:
        await record(
            interaction,
            "issue",
            issue_type=issue_type,
            note=note,
            response="Issue registrado de forma redacted.",
        )

    @tree.command(name="obelisk_done", description="Accion completada.", guild=guild)
    async def obelisk_done(interaction: discord.Interaction) -> None:
        await record(interaction, "done", response="Completado registrado.")

    @client.event
    async def on_ready() -> None:
        await tree.sync(guild=guild)
        print(f"discord beta bridge ready guild={config[GUILD_ENV]} channel={config[BETA_CHANNEL_ENV]}")

    client.run(config[TOKEN_ENV])
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_PATH)
    parser.add_argument("--check-config", action="store_true")
    parser.add_argument("--require-token", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--send-beta-notice", action="store_true")
    parser.add_argument("--content", help="Sanitized beta-channel content for --send-beta-notice.")
    parser.add_argument(
        "--with-beta-controls",
        action="store_true",
        help="Send a beta notice embed with persistent tester action buttons.",
    )
    parser.add_argument(
        "--update-active-notice",
        action="store_true",
        help="Edit the active beta notice message when possible instead of sending a new one.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--dry-run-receipt",
        help="Receipt emitted by a reviewed --dry-run for the exact beta notice send plan.",
    )
    parser.add_argument("--confirm-approved-send", action="store_true")
    parser.add_argument("--emit-test-event", choices=EVENT_TYPES)
    parser.add_argument(
        "--summarize-events",
        action="store_true",
        help="Summarize the redacted local beta bridge event sink without Discord access.",
    )
    parser.add_argument(
        "--recent-limit",
        type=int,
        default=10,
        help="Maximum recent metadata-only events included in --summarize-events output.",
    )
    parser.add_argument("--user-id", default="0")
    parser.add_argument("--map", choices=ALLOWED_MAPS)
    parser.add_argument("--issue-type", choices=ALLOWED_ISSUE_TYPES)
    parser.add_argument("--note")
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.run:
        return run_bot(args.env_file)
    if args.send_beta_notice:
        if args.content is None:
            raise SystemExit("--send-beta-notice requires --content")
        report = send_bot_notice(
            args.env_file,
            content=args.content,
            dry_run=args.dry_run,
            confirmed_send=args.confirm_approved_send,
            with_beta_controls=args.with_beta_controls,
            update_active_notice=args.update_active_notice,
            dry_run_receipt=args.dry_run_receipt,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    if args.emit_test_event:
        event = build_event(
            args.emit_test_event,
            user_id=args.user_id,
            map_name=args.map,
            issue_type=args.issue_type,
            note=args.note,
            config=merged_config(args.env_file),
        )
        print(json.dumps(event, indent=2, sort_keys=True))
        return 0
    if args.summarize_events:
        summary = summarize_event_sink(
            configured_event_sink(merged_config(args.env_file)),
            recent_limit=args.recent_limit,
        )
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if summary["invalid_event_count"] == 0 else 1
    report = check_config(args.env_file, require_token=args.require_token)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
