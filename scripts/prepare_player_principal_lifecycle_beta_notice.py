#!/usr/bin/env python3
"""Prepare or send the beta-test notice for a player-principal evidence window.

Dry-run is the default operational path. A real Discord send still requires the guarded
`discord_beta_bridge.py` confirmation flags and either the recorded standing launch
authority or exact current-turn operator approval outside this tool.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import protected_paths
from prepare_player_principal_lifecycle_window_request import (
    APPROVED_BETA_NOTICE_PATH,
    DIRECT_JOIN_PLAN_NON_AUTHORIZATION,
    DIRECT_JOIN_PLAN_SCHEMA,
    EXACT_TARGET_SCOPE_NON_AUTHORIZATION,
    EXACT_TARGET_SCOPE_SCHEMA,
    HANDLE_NEW_PLAYER_FUNCTION,
    MAX_APPROVED_WINDOW_SECONDS,
    MAX_REQUEST_PREPARATION_LEAD_SECONDS,
    MIN_APPROVED_WINDOW_SECONDS,
    PLAYER_NOTICE_ACTION_NON_AUTHORIZATION,
    PLAYER_NOTICE_ACTION_SCHEMA,
    RUN_ID_RE,
    SAFE_TOKEN_RE,
    SCHEMA as WINDOW_REQUEST_SCHEMA,
    requested_wait_window_seconds,
    SESSION_START_REJECTED_REQUIRED_ARGUMENTS,
    SESSION_START_REJECTED_REQUIRED_CALL,
    SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS,
    SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES,
    SESSION_START_REJECTED_REQUIRED_FUNCTION,
    UTC_RE,
    direct_join_plan,
    is_forbidden_exact_target_alias,
    run_id_for_window_start,
)
from discord_beta_bridge import (
    DISCORD_BETA_NON_PROMOTION_FLAGS,
    SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE,
    discord_beta_non_promotion_boundary,
)


SCHEMA = "obelisk.player-principal-lifecycle-beta-notice-prep.v1"
GUARDED_BETA_NOTICE_ACTION_SCHEMA = "obelisk.player-principal-lifecycle-guarded-beta-notice-action.v1"
DRY_RUN_CONSUMPTION_BOUNDARY_SCHEMA = (
    "obelisk.player-principal-lifecycle-beta-notice-dry-run-consumption-boundary.v1"
)
DRY_RUN_READY_TO_SEND_SCHEMA = (
    "obelisk.player-principal-lifecycle-beta-notice-dry-run-ready-to-send.v1"
)
NOTICE_ACTION_ARTIFACT_SCHEMA = (
    "obelisk.player-principal-lifecycle-beta-notice-action-artifact.v1"
)
REQUEST_WINDOW_SENDABILITY_SCHEMA = (
    "obelisk.player-principal-lifecycle-beta-notice-request-window-sendability.v1"
)
CURRENT_WINDOW_WORKFLOW_SCHEMA = (
    "obelisk.player-principal-lifecycle-beta-notice-current-window-workflow.v1"
)
TWO_SERVER_CAP_SCHEMA = "obelisk.player-principal-lifecycle-two-server-cap.v1"
LIFECYCLE_ROLE_OBJECTIVES_SCHEMA = (
    "obelisk.player-principal-lifecycle-missing-role-objectives.v1"
)
RECOMMENDED_NOTICE_TEXT_SCHEMA = (
    "obelisk.player-principal-lifecycle-redacted-recommended-notice-text.v1"
)
BETA_RUNTIME_CHOREOGRAPHY_SCHEMA = (
    "obelisk.player-principal-lifecycle-beta-runtime-choreography.v1"
)
CHECKJOIN_STIMULUS_BOUNDARY_SCHEMA = (
    "obelisk.player-principal-lifecycle-checkjoin-stimulus-boundary.v1"
)
ACTIVE_PLAYER_NO_ACCEPTED_EVENTS_SCHEMA = (
    "obelisk.player-principal-lifecycle-active-player-no-accepted-events-window-policy.v1"
)
ACTIVE_NOTICE_UPDATE_POLICY_SCHEMA = (
    "obelisk.player-principal-lifecycle-beta-active-notice-update-policy.v1"
)
ACTIVE_NOTICE_WINDOW_DECISION_SCHEMA = (
    "obelisk.player-principal-lifecycle-beta-active-notice-window-decision.v1"
)
BETA_TESTER_STATUS_WORKFLOW_SCHEMA = (
    "obelisk.player-principal-lifecycle-beta-tester-status-workflow.v1"
)
SEND_HELPER = Path(__file__).resolve().parent / "discord_beta_bridge.py"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACTIVE_NOTICE_STATE = REPO_ROOT / "local" / "discord-beta-bridge" / "active-notice.json"
SERVER_ROOT = Path("/servidor/ark")
BETA_TEST_CHANNEL = "beta-test"
BETA_TEST_WEBHOOK_ENV = "OBELISK_BETA_TEST_WEBHOOK_URL"
BETA_TEST_BOT_CHANNEL_ID = "1513238083741683934"
BETA_TEST_ACTIVE_NOTICE_STATE_ENV = "OBELISK_DISCORD_ACTIVE_NOTICE_STATE"
BETA_TEST_EVENT_SINK_ENV = "OBELISK_DISCORD_BRIDGE_EVENT_SINK"
BETA_TEST_BOT_ENV_VARS = [
    "OBELISK_DISCORD_BOT_TOKEN",
    "OBELISK_DISCORD_BOT_TOKEN_ROTATED_AT_UTC",
    "OBELISK_DISCORD_GUILD_ID",
    "OBELISK_DISCORD_BETA_CHANNEL_ID",
]
BETA_NOTICE_REQUIRED_HELPER_ARGS = (
    "--send-beta-notice",
    "--with-beta-controls",
    "--update-active-notice",
)
BETA_STATUS_SUMMARY_CUSTOM_ID = "obelisk_beta:status_summary"
BETA_STATUS_SUMMARY_RESPONSE_MODE = "ephemeral_local_event_summary"
BETA_NOTICE_FORBIDDEN_WEBHOOK_ARGS = frozenset(
    (
        "--legacy-webhook",
        "--use-webhook",
        "--webhook",
        "--webhook-env",
        "--webhook-url",
        "--webhook-url-env",
    )
)
NOTICE_ACTION_BLOCKER = "approved_dry_run_checked_beta_testers_notice_sent"
STALE_WINDOW_BLOCKER = "stale_request_window_prepare_fresh_current_window"
DISCORD_SEND_SCOPE_BLOCKER = "fresh_current_turn_operator_discord_send_scope_required"
REQUIRED_LIFECYCLE_EVENT_ROLES = (
    "session_start",
    "session_start_rejected",
    "session_end",
)
EXACT_TESTER_EVIDENCE_OBJECTIVE = (
    "produce session_start, exact CheckJoinInProgress(1,0) session_start_rejected, "
    "and matched session_end"
)
EXACT_TESTER_EVIDENCE_OBJECTIVE_ITEMS = (
    "session_start",
    "exact CheckJoinInProgress(1,0) session_start_rejected",
    "matched session_end",
)
SIDECAR_NON_EVIDENCE_FLAGS = {
    "sidecar_is_notice_action_metadata_only": True,
    "sidecar_counts_as_approved_runtime_evidence": False,
    "sidecar_counts_as_runtime_evidence": False,
    "sidecar_counts_as_sdk_evidence": False,
    "sidecar_counts_toward_sdk": False,
    "sidecar_counts_toward_p0_dependency_chain": False,
    "sidecar_grants_readiness_claims": False,
    "sidecar_authorizes_runtime_work": False,
    "sidecar_authorizes_server_operations": False,
    "sidecar_authorizes_discord": False,
    "stale_sidecar_counts_as_readiness": False,
}
NON_AUTHORIZATION = (
    "notice preparation only; dry-run output and confirmed-send helper results are "
    "notice-action metadata only. This report does not grant Discord authorization, "
    "standing launch authority or current-turn approval, server operations, marker/env "
    "changes, starts, restarts, "
    "runtime capture, approved runtime evidence, public readiness, SDK completion, "
    "activation, or P0 progress"
)
FALSE_FLAGS = {
    "activation_allowed": False,
    "activation_allowed_before_notice_sent": False,
    "activation_preconditions_met": False,
    "authorizes_discord": False,
    "authorizes_runtime_work": False,
    "authorizes_server_operations": False,
    "authorizes_server_work": False,
    "authorizes_workspace_work": False,
    "authorizes_workspace_writes": False,
    "current_turn_approval_recorded": False,
    "current_turn_scope_authorized": False,
    "discord_authorized": False,
    "discord_notice_authorized": False,
    "discord_send_authorized": False,
    "live_ops_authorized": False,
    "live_log_reads_authorized": False,
    "live_log_permission_granted": False,
    "publication_authorized": False,
    "read_live_logs": False,
    "reads_live_logs": False,
    "server_operations_authorized": False,
    "runtime_work_authorized": False,
    "discord_sent": False,
    "discord_authorized_by_request": False,
    "discord_authorized_by_this_report": False,
    "marker_env_changes_authorized": False,
    "runtime_capture_authorized": False,
    "runtime_window_authorized": False,
    "approved_runtime_evidence": False,
    "approved_runtime_evidence_present": False,
    "approved_runtime_evidence_ready": False,
    "counts_as_approved_runtime_evidence": False,
    "counts_as_runtime_evidence": False,
    "counts_as_sdk_evidence": False,
    "counts_as_sdk_progress": False,
    "counts_as_p0_progress": False,
    "counts_toward_public_sdk": False,
    "counts_toward_runtime": False,
    "counts_toward_v1_completion": False,
    "counts_toward_sdk": False,
    "counts_toward_p0_dependency_chain": False,
    "public_or_runtime_accounting_allowed": False,
    "promotion_ready": False,
    "public_abi_ready": False,
    "public_sdk_ready": False,
    "stable_sdk_ready": False,
    "plugin_hub_ready": False,
    "publication_ready": False,
    "route_ready": False,
    "runtime_evidence_present": False,
    "runtime_evidence_ready": False,
    "runtime_ready": False,
    "sdk_evidence_ready": False,
    "v1_completion_ready": False,
    "stable_claim_allowed": False,
    "workspace_writes_authorized": False,
}


def discord_beta_notice_operational_boundary(scope: str) -> dict[str, Any]:
    return {
        "operational_message_style": SINGLE_UPDATED_OPERATIONAL_MESSAGE_STYLE,
        "single_updated_embed_buttons_message_preferred": True,
        "edit_existing_message_when_active_notice_state_present": True,
        "post_only_when_active_notice_state_missing": True,
        "discord_beta_non_promotion": discord_beta_non_promotion_boundary(
            f"player_principal_lifecycle_beta_notice:{scope}"
        ),
        **DISCORD_BETA_NON_PROMOTION_FLAGS,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "plugin_hub_ready": False,
        "publication_ready": False,
        "counts_as_p0_progress": False,
    }
FORBIDDEN_REQUEST_TRUE_CLAIM_KEYS = set(FALSE_FLAGS) | {
    "accepted_bundle",
    "accepted_notice_action",
    "accepted_player_notice_action",
    "accepted_runtime_evidence",
    "activation_preconditions_met",
    "approved_bundle_accepted",
    "approved_bundle_request_accepted",
    "approved_notice_action",
    "approved_player_notice_action",
    "approved_runtime_bundle_request_accepted",
    "beta_notice_delivered",
    "beta_notice_sent",
    "bundle_accepted",
    "closure_request_authorizes_runtime",
    "closure_request_counts_as_approved_runtime_evidence",
    "closure_request_counts_toward_sdk",
    "complete_sdk_allowed",
    "complete_sdk_claim_allowed",
    "complete_sdk_ready",
    "confirmed_beta_notice_delivered",
    "confirmed_beta_notice_sent",
    "confirmed_notice_delivered",
    "confirmed_notice_sent",
    "counts_as_approved_runtime_evidence",
    "counts_as_public_sdk",
    "counts_as_runtime",
    "counts_as_runtime_evidence",
    "counts_as_sdk_evidence",
    "counts_as_v1_completion",
    "current_turn_approval_recorded",
    "current_turn_accepted",
    "current_turn_authorized",
    "current_turn_scope_authorized",
    "current_turn_scope_ready",
    "dry_run_notice_authorizes_runtime",
    "dry_run_notice_counts_as_approved_runtime_evidence",
    "dry_run_notice_ready",
    "evidence_bundle_accepted",
    "live_log_access_allowed",
    "live_log_permission",
    "live_log_permission_granted",
    "live_log_read_allowed",
    "live_log_read_permission",
    "live_log_reads_authorized",
    "live_logs_permission",
    "live_logs_read_allowed",
    "live_logs_read_permission",
    "operator_current_turn_approval_recorded",
    "notice_delivered",
    "notice_sent",
    "player_notice_delivered",
    "player_notice_sent",
    "request_pack_authorizes_discord",
    "request_pack_records_current_turn_approval",
    "send_performed_by_request_pack",
}
FORBIDDEN_REQUEST_PROGRESS_CLAIM_KEYS = {
    "claim_progress_contribution",
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_claim_credit",
    "complete_sdk_claim_credits",
    "complete_sdk_credit",
    "complete_sdk_credits",
    "complete_sdk_progress_contribution",
    "closure_request_progress_contribution",
    "credit",
    "credits",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_credit",
    "p0_dependency_chain_credits",
    "p0_dependency_chain_progress_contribution",
    "p0_dependency_progress_contribution",
    "progress",
    "public_sdk_progress_contribution",
    "runtime_progress_contribution",
    "sdk_credit",
    "sdk_credits",
    "v1_completion_contribution",
    "v1_completion_credit",
    "v1_completion_credits",
}
SPLIT_CLAIM_NAME_KEYS = {
    "alias",
    "claim",
    "field",
    "flag",
    "key",
    "name",
    "property",
}
SPLIT_CLAIM_VALUE_KEYS = {
    "allowed",
    "enabled",
    "ready",
    "result",
    "state",
    "status",
    "value",
}
GENERIC_STATUS_CLAIM_KEYS = {"claim", "evidence", "readiness", "result", "state", "status"}
CLAIM_DOMAIN_TOKENS = {
    "activation",
    "claim",
    "discord",
    "evidence",
    "live",
    "notice",
    "ops",
    "p0",
    "passive",
    "public",
    "readiness",
    "route",
    "runtime",
    "sdk",
    "server",
    "stable",
    "status",
    "v1",
    "workspace",
}
SECRET_TEXT_RE = re.compile(
    r"(discord(?:app)?\.com/api/webhooks/)[^\s\"']+|"
    r"((?:WEBHOOK|TOKEN|SECRET|PASSWORD|KEY)[A-Z0-9_]*=)[^\s\"']+",
    re.IGNORECASE,
)
FLOW_ALIAS_TOKENS = frozenset(
    (
        "notice",
        "notice_only",
        "passive",
        "passive_monitor",
        "passive_only",
        "public_readiness",
        "public_ready",
        "readiness",
        "status",
        "status_only",
    )
)
FLOW_ALIAS_RE = re.compile(
    r"(^|[_ .:-])(?:notice|passive|status|readiness)(?:$|[_ .:-])|"
    r"public[_ .:-]?readiness",
    re.IGNORECASE,
)


def redact_helper_text(value: str) -> str:
    return SECRET_TEXT_RE.sub(lambda match: f"{match.group(1) or match.group(2)}<redacted>", value)


def contains_secret_text(value: str) -> bool:
    return SECRET_TEXT_RE.search(value) is not None


def two_server_cap_policy() -> dict[str, Any]:
    return {
        "schema": TWO_SERVER_CAP_SCHEMA,
        "max_running_ark_servers": 2,
        "current_two_server_cap_preserved": True,
        "never_keep_three_ark_servers_running": True,
        "three_ark_servers_allowed": False,
        "must_confirm_one_instance_off_before_starting_another": True,
        "standing_authority_authorizes_extra_transfer_server": False,
        "standing_authority_authorizes_server_restart": False,
        "server_restart_authorized_by_notice": False,
        "message": (
            "Preserve the current two-server cap: never keep three ARK servers running; "
            "confirm one instance is off before starting another."
        ),
        "non_authorization": NON_AUTHORIZATION,
    }


def lifecycle_role_objectives(
    missing_roles: list[str] | None = None,
) -> dict[str, Any]:
    roles = list(missing_roles or REQUIRED_LIFECYCLE_EVENT_ROLES)
    objectives = [
        {
            "objective_id": "session_start",
            "role": "session_start",
            "required_function": HANDLE_NEW_PLAYER_FUNCTION,
            "required_call": "HandleNewPlayer(1,1)",
            "required_copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
            "required_copied_bool_values": ["1", "1"],
            "objective": "produce session_start from copied Obelisk.log",
        },
        {
            "objective_id": SESSION_START_REJECTED_REQUIRED_CALL,
            "role": "session_start_rejected",
            "required_function": SESSION_START_REJECTED_REQUIRED_FUNCTION,
            "required_argument_tuple": SESSION_START_REJECTED_REQUIRED_ARGUMENTS,
            "required_call": SESSION_START_REJECTED_REQUIRED_CALL,
            "required_copied_bool_fields": SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS,
            "required_copied_bool_values": SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES,
            "handle_new_player_rejected_tuple_allowed": False,
            "handle_new_player_rejected_tuple_alternative_allowed": False,
            "objective": (
                "produce exact CheckJoinInProgress(1,0) session_start_rejected from "
                "copied Obelisk.log"
            ),
        },
        {
            "objective_id": "session_end",
            "role": "session_end",
            "required_function": "OnLogout",
            "correlation_status": "matched",
            "objective": "produce matched session_end for the same player session",
        },
    ]
    return {
        "schema": LIFECYCLE_ROLE_OBJECTIVES_SCHEMA,
        "tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "exact_tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "tester_evidence_objective_items": list(EXACT_TESTER_EVIDENCE_OBJECTIVE_ITEMS),
        "required_lifecycle_event_roles": list(REQUIRED_LIFECYCLE_EVENT_ROLES),
        "missing_lifecycle_event_roles": roles,
        "next_missing_lifecycle_event_role": roles[0] if roles else None,
        "objective_ids": [item["objective_id"] for item in objectives],
        "objectives": objectives,
        "exact_session_start_rejected_required": True,
        "matched_session_end_required": True,
        "requires_copied_log_bundle_checker_acceptance": True,
        "standing_authority_satisfies_missing_roles": False,
        "beta_notice_satisfies_missing_roles": False,
        "objectives_are_preparation_only": True,
        "readiness_claim_allowed": False,
        "progress_claim_allowed": False,
        "preparation_counts_as_readiness": False,
        "preparation_counts_as_progress": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def checkjoin_stimulus_boundary() -> dict[str, Any]:
    return {
        "schema": CHECKJOIN_STIMULUS_BOUNDARY_SCHEMA,
        "classification": "stale_or_diagnostic_exact_checkjoin_is_stimulus_only",
        "exact_call": "ShooterGameMode.CheckJoinInProgress(1,0)",
        "tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "accepted_observer_line_without_current_window_sibling_set_is_promotable": False,
        "diagnostic_tail_without_approved_sibling_set_is_promotable": False,
        "stale_or_order_mismatched_line_is_promotable": False,
        "stimulus_clue_for_future_choreography": True,
        "approved_sibling_set_required": True,
        "approved_sibling_set_roles_required": [
            "session_start",
            "session_start_rejected",
            "session_end",
        ],
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "readiness_claim_allowed": False,
        "progress_claim_allowed": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def active_player_no_accepted_events_policy(request: dict[str, Any]) -> dict[str, Any]:
    target = request_target(request)
    restart_expectation = request.get("restart_expectation")
    if restart_expectation not in {"none", "start", "restart"}:
        restart_expectation = "none"
    return {
        "schema": ACTIVE_PLAYER_NO_ACCEPTED_EVENTS_SCHEMA,
        "status": "conditional_if_player_present_observer_enabled_no_accepted_events",
        "classification": "likely_drift_non_evidence",
        "target": target,
        "exact_state_preconditions": [
            "exact_target_matches_request",
            "player_count_on_exact_target_greater_than_zero",
            "player_principal_lifecycle_observer_enabled_on_exact_target",
            "accepted_lifecycle_event_count_on_exact_target_equals_zero",
            "no_accepted_session_start_session_start_rejected_or_session_end_for_target",
        ],
        "restart_expectation": restart_expectation,
        "restart_recommended": False,
        "start_or_restart_recommended": False,
        "restart_requires_concrete_deploy_or_gate_change": True,
        "restart_without_concrete_deploy_or_gate_change_recommended": False,
        "wait_or_player_prompt_requires_exact_preconditions": True,
        "wait_preconditions": [
            "fresh_current_window_request",
            "confirmed_notice_report_consumed",
            "activation_preconditions_ready",
            "observer_enabled_on_exact_target",
            "no_lifecycle_drift_blocker",
        ],
        "ask_reconnect_or_logout_now": False,
        "ask_reconnect_or_logout_preconditions": [
            "player_still_present_on_exact_target",
            "accepted_session_start_or_exact_CheckJoinInProgress_1_0_seen_for_same_session",
            "same_window_observer_gate_matched",
            "no_drift_blocker_pending",
        ],
        "defer_until_drift_fix_when_no_accepted_events": True,
        "server_operations_authorized": False,
        "runtime_capture_authorized": False,
        "standing_authority_metadata_only": True,
        "standing_authority_authorizes_server_restart": False,
        "standing_authority_authorizes_marker_env_changes": False,
        "standing_authority_authorizes_runtime_evidence": False,
        "two_server_cap_policy": two_server_cap_policy(),
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def beta_runtime_choreography(request: dict[str, Any]) -> dict[str, Any]:
    no_accepted_policy = active_player_no_accepted_events_policy(request)
    return {
        "schema": BETA_RUNTIME_CHOREOGRAPHY_SCHEMA,
        "classification": "single_tester_direct_join_choreography_non_authorizing",
        "target": request_target(request),
        "tester_count_required": 1,
        "exactly_one_tester_required": True,
        "single_tester_only": True,
        "direct_target_join_required": True,
        "direct_join_route": "direct_join_exact_server_map",
        "cluster_transfer_required": False,
        "cluster_transfer_allowed": False,
        "extra_transfer_server_required": False,
        "reconnect_before_exact_checkjoin_allowed": False,
        "logout_before_exact_checkjoin_allowed": False,
        "wait_for_exact_checkjoin_before_logout_required": True,
        "logout_or_cluster_transfer_or_reconnect_before_exact_checkjoin_allowed": False,
        "logout_cluster_transfer_reconnect_before_exact_checkjoin_or_window_close_allowed": False,
        "mixed_transfer_reconnect_same_approved_window_allowed": False,
        "approved_window_must_not_mix_direct_join_transfer_or_reconnect": True,
        "tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "exact_tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "active_player_no_accepted_events_policy": no_accepted_policy,
        "no_restart_when_player_present_observer_enabled_no_accepted_events": True,
        "ask_reconnect_or_logout_without_accepted_gate_allowed": False,
        "defer_until_drift_fix_when_no_accepted_events": True,
        "observer_gate_required_before_logout": "ShooterGameMode.CheckJoinInProgress(1,0)",
        "observer_gate": {
            "required_role": "session_start_rejected",
            "required_function": "ShooterGameMode.CheckJoinInProgress",
            "required_call": "CheckJoinInProgress(1,0)",
            "objective": "produce exact CheckJoinInProgress(1,0) session_start_rejected",
            "required_copied_bool_fields": SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS,
            "required_copied_bool_values": SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES,
            "wait_until_observer_sees_exact_checkjoin_or_window_closes": True,
            "logout_before_observer_gate_or_window_close_allowed": False,
        },
        "tester_instruction": (
            "one tester direct-joins the exact target, waits in that session until the "
            "observer reports exact CheckJoinInProgress(1,0) or the approved window closes, "
            "then logs out once only when told"
        ),
        "forbidden_same_window_actions": [
            "second_tester_join",
            "cluster_transfer",
            "logout_before_exact_checkjoin_or_window_close",
            "reconnect_before_exact_checkjoin_or_window_close",
            "mixed_transfer_and_reconnect_flow",
        ],
        "stale_or_diagnostic_exact_checkjoin_boundary": checkjoin_stimulus_boundary(),
        "choreography_authorizes_discord": False,
        "choreography_authorizes_runtime_capture": False,
        "choreography_authorizes_server_operations": False,
        "standing_authority_metadata_only": True,
        "standing_authority_authorizes_server_restart": False,
        "standing_authority_authorizes_runtime_evidence": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "readiness_claim_allowed": False,
        "progress_claim_allowed": False,
        "preparation_counts_as_readiness": False,
        "preparation_counts_as_progress": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def recommended_notice_text(request: dict[str, Any]) -> dict[str, Any]:
    target = request_target(request)
    window = window_text(request)
    join_plan = request.get("direct_join_plan")
    if not isinstance(join_plan, dict):
        join_plan = direct_join_plan(request)
    objective_text = EXACT_TESTER_EVIDENCE_OBJECTIVE
    choreography = beta_runtime_choreography(request)
    discord_text = (
        f"Obelisk beta window for {target['map']} on {target['instance']} ({window}). "
        f"One selected tester only: direct-join that exact server/map, stay in that session, "
        f"and wait until the observer reports exact CheckJoinInProgress(1,0) or the window "
        f"closes before logging out once when told. Do not cluster-transfer, reconnect, or "
        f"mix transfer/reconnect/logout flows in this approved window. Do not post player "
        f"names, chat, Steam IDs, private credentials. Use the bot buttons for Started, "
        f"Loading, In-server, Logged-out, Cluster-transfer, and Status summary "
        f"coordination only. Status summary reads redacted local bridge metadata only. "
        f"Objectives: {objective_text}."
    )
    broadcast_text = (
        "Obelisk beta validation window starting now. One selected tester direct-joins "
        "the exact target, waits for observer confirmation of exact CheckJoinInProgress(1,0) "
        "or window close before one logout when told, and does not transfer or reconnect."
    )
    redacted_discord = redact_helper_text(discord_text)
    redacted_broadcast = redact_helper_text(broadcast_text)
    return {
        "schema": RECOMMENDED_NOTICE_TEXT_SCHEMA,
        "discord_channel": BETA_TEST_CHANNEL,
        "discord_content": "@everyone",
        "recommended_discord_text_redacted": redacted_discord,
        "recommended_rcon_broadcast_text_redacted": redacted_broadcast,
        "recommended_text_already_redacted": True,
        "raw_player_text_allowed": False,
        "raw_player_identity_allowed": False,
        "raw_player_text_or_identity_allowed": False,
        "secret_or_webhook_output_allowed": False,
        "contains_secret_or_webhook_after_redaction": (
            contains_secret_text(redacted_discord) or contains_secret_text(redacted_broadcast)
        ),
        "redaction_policy": (
            "Use only the recommended sanitized text; do not paste player names, chat, "
            "Steam IDs, private credentials into Discord or RCON broadcast."
        ),
        "direct_join_plan": join_plan,
        "approved_beta_test_channel_only": True,
        "broad_discord_or_community_notice_allowed": False,
        "two_server_cap_policy": two_server_cap_policy(),
        "lifecycle_role_objectives": lifecycle_role_objectives(),
        "tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "exact_tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "beta_runtime_choreography": choreography,
        "active_player_no_accepted_events_policy": choreography[
            "active_player_no_accepted_events_policy"
        ],
        "one_tester_direct_join_wait_for_exact_checkjoin_required": True,
        "mixed_transfer_reconnect_same_approved_window_allowed": False,
        "ask_reconnect_or_logout_without_accepted_gate_allowed": False,
        "defer_until_drift_fix_when_no_accepted_events": True,
        "stale_or_diagnostic_exact_checkjoin_lines_are_stimulus_clues_only": True,
        "counts_as_approved_runtime_evidence": False,
        "counts_toward_sdk": False,
        "readiness_claim_allowed": False,
        "progress_claim_allowed": False,
        "preparation_counts_as_readiness": False,
        "preparation_counts_as_progress": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-json", required=True, type=Path, help="Offline window-request.json.")
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    parser.add_argument(
        "--send-helper",
        type=Path,
        default=SEND_HELPER,
        help="Guarded Discord helper to invoke.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Render the beta-test embed only.")
    mode.add_argument(
        "--no-send",
        action="store_true",
        help="Persist a no-send notice artifact without invoking the Discord helper.",
    )
    mode.add_argument(
        "--confirm-approved-send",
        action="store_true",
        help="After standing launch authority or current-turn approval and dry-run review, send via the guarded helper.",
    )
    parser.add_argument(
        "--artifact-json",
        type=Path,
        help=(
            "Persist the sanitized notice-action sidecar JSON. Defaults to a sibling "
            "sidecar beside --request-json."
        ),
    )
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    protected_paths.reject_symlink_component(path, "--request-json")
    resolved = protected_paths.reject_protected_input_path(
        path.expanduser(),
        "--request-json",
        protected_root=SERVER_ROOT,
        approved_roots=protected_paths.approved_offline_workspace_roots(),
    )
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--request-json is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("--request-json must contain a JSON object")
    payload["_resolved_request_json_path"] = str(resolved)
    payload["_request_json_sha256"] = hashlib.sha256(resolved.read_bytes()).hexdigest()
    return payload


def protected_output_file(path: Path, label: str) -> Path:
    protected_paths.reject_symlink_component(path, label)
    return protected_paths.reject_protected_output_path(
        path.expanduser(),
        label,
        protected_root=SERVER_ROOT,
        approved_roots=protected_paths.approved_offline_workspace_roots(),
    )


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def notice_artifact_default_filename(mode: str) -> str:
    slug = mode.replace("_", "-")
    return f"beta-notice.{slug}.sidecar.json"


def default_notice_artifact_path(request: dict[str, Any], mode: str) -> Path:
    return Path(request["_resolved_request_json_path"]).parent / notice_artifact_default_filename(mode)


def notice_artifact_path(args: argparse.Namespace, request: dict[str, Any], mode: str) -> Path:
    raw_path = (
        args.artifact_json
        if args.artifact_json is not None
        else default_notice_artifact_path(request, mode)
    )
    return protected_output_file(raw_path, "--artifact-json")


def protected_default_notice_artifact_path(request: dict[str, Any], mode: str) -> Path:
    return protected_output_file(default_notice_artifact_path(request, mode), "--artifact-json")


def write_notice_action_artifact(report: dict[str, Any], artifact_path: Path) -> None:
    artifact = {
        "schema": NOTICE_ACTION_ARTIFACT_SCHEMA,
        "mode": report["mode"],
        "ready": report["ready"],
        "target": report["target"],
        "run_id": report["run_id"],
        "notice_path": report["notice_path"],
        "request_json": report["request_json"],
        "notice_report_sha256": hashlib.sha256(canonical_json_bytes(report)).hexdigest(),
        "notice_report": report,
        "artifact_contains_full_sanitized_notice_report": True,
        "sidecar_required_for_confirmed_send_consumption": True,
        "stdout_only_confirmation_accepted": False,
        "secret_or_webhook_output_allowed": False,
        "discord_send_performed_by_artifact_write": False,
        **SIDECAR_NON_EVIDENCE_FLAGS,
        "non_authorization": NON_AUTHORIZATION,
    }
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def zero_progress_alias_value(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == 0


def normalized_claim_key(value: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    separated = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", separated)
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def is_forbidden_flow_alias(value: str) -> bool:
    normalized = normalized_claim_key(value)
    return (
        normalized in FLOW_ALIAS_TOKENS
        or FLOW_ALIAS_RE.search(value) is not None
        or is_forbidden_exact_target_alias(value)
    )


def claim_key_tokens(value: object) -> set[str]:
    normalized = normalized_claim_key(value)
    return {token for token in normalized.split("_") if token}


NORMALIZED_FORBIDDEN_REQUEST_TRUE_CLAIM_KEYS = {
    normalized_claim_key(key) for key in FORBIDDEN_REQUEST_TRUE_CLAIM_KEYS
}
NORMALIZED_FORBIDDEN_REQUEST_PROGRESS_CLAIM_KEYS = {
    normalized_claim_key(key) for key in FORBIDDEN_REQUEST_PROGRESS_CLAIM_KEYS
}


def positive_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return normalized_claim_key(value) in {
            "accepted",
            "allowed",
            "approved",
            "authorized",
            "complete",
            "delivered",
            "enabled",
            "present",
            "progress",
            "ready",
            "sent",
            "supported",
            "true",
            "unblocked",
            "unlocked",
            "yes",
            "in_progress",
        }
    if isinstance(value, dict):
        return any(positive_claim_value(item) for item in value.values())
    if isinstance(value, list):
        return any(positive_claim_value(item) for item in value)
    return False


def generic_positive_claim_alias_key(value: object) -> bool:
    normalized = normalized_claim_key(value)
    tokens = claim_key_tokens(value)
    if normalized in {"ready", "is_ready", "current_turn_accepted"}:
        return True
    if "authoriz" in normalized or "authoris" in normalized:
        return True
    if tokens & {"delivered", "sent"} and tokens & {"discord", "notice", "report", "request", "this"}:
        return True
    if "status" in tokens and tokens & CLAIM_DOMAIN_TOKENS:
        return True
    if "readiness" in tokens and tokens & CLAIM_DOMAIN_TOKENS:
        return True
    if "passive" in tokens and tokens & {
        "accepted",
        "allowed",
        "approved",
        "authorized",
        "complete",
        "completed",
        "evidence",
        "monitor",
        "progress",
        "ready",
        "readiness",
        "result",
        "snapshot",
        "state",
        "status",
    }:
        return True
    if "progress" in tokens:
        return True
    if tokens & {"live", "server", "obelisk"} and tokens & {"log", "logs"} and tokens & {
        "access",
        "allowed",
        "enabled",
        "permission",
        "permissions",
        "read",
        "reads",
        "ready",
        "tail",
        "tails",
    }:
        return True
    if "notice" in tokens and tokens & {"delivered", "delivery", "discord", "dry", "run", "sent"} and tokens & {
        "accepted",
        "allowed",
        "approved",
        "authorized",
        "complete",
        "completed",
        "delivered",
        "progress",
        "ready",
        "readiness",
        "result",
        "sent",
        "state",
        "status",
    }:
        return True
    if {"closure", "request"}.issubset(tokens) and tokens & {
        "accepted",
        "allowed",
        "approved",
        "authorized",
        "complete",
        "completed",
        "counts",
        "evidence",
        "p0",
        "progress",
        "ready",
        "result",
        "runtime",
        "sdk",
        "state",
        "status",
        "v1",
    }:
        return True
    if {"current", "turn"}.issubset(tokens) and (
        tokens & {"accepted", "approved", "authorized", "ready", "recorded", "sent"}
        or "authoriz" in normalized
        or "authoris" in normalized
    ):
        return True
    if tokens & CLAIM_DOMAIN_TOKENS and tokens & {
        "accepted",
        "allowed",
        "complete",
        "delivered",
        "enabled",
        "present",
        "ready",
        "supported",
        "unblocked",
        "unlocked",
    }:
        return True
    return False


def validate_no_forbidden_notice_request_claims(value: Any, path: str, blockers: list[str]) -> None:
    if isinstance(value, dict):
        declared_claim_names = [
            child
            for key, child in value.items()
            if normalized_claim_key(key) in SPLIT_CLAIM_NAME_KEYS
            and isinstance(child, str)
        ]
        declared_claim_values = [
            child
            for key, child in value.items()
            if normalized_claim_key(key) in SPLIT_CLAIM_VALUE_KEYS
        ]
        for claim_name in declared_claim_names:
            normalized_claim_name = normalized_claim_key(claim_name)
            if (
                normalized_claim_name in NORMALIZED_FORBIDDEN_REQUEST_PROGRESS_CLAIM_KEYS
                or (
                    "progress" in claim_key_tokens(claim_name)
                    and (
                        claim_key_tokens(claim_name) & CLAIM_DOMAIN_TOKENS
                        or {"closure", "request"}.issubset(claim_key_tokens(claim_name))
                        or "notice" in claim_key_tokens(claim_name)
                    )
                )
            ):
                if not declared_claim_values or any(not zero_progress_alias_value(item) for item in declared_claim_values):
                    blockers.append(f"forbidden_notice_request_progress_claim:{path or '$'}")
                continue
            if (
                normalized_claim_name in NORMALIZED_FORBIDDEN_REQUEST_TRUE_CLAIM_KEYS
                or generic_positive_claim_alias_key(claim_name)
            ):
                if not declared_claim_values or any(item is not False for item in declared_claim_values):
                    blockers.append(f"forbidden_notice_request_claim:{path or '$'}")
        for key, child in value.items():
            if key.startswith("_"):
                continue
            child_path = f"{path}.{key}" if path else str(key)
            normalized_key = normalized_claim_key(key)
            if normalized_key == "non_authorization":
                continue
            progress_key = (
                normalized_key in NORMALIZED_FORBIDDEN_REQUEST_PROGRESS_CLAIM_KEYS
                or (
                    "progress" in claim_key_tokens(key)
                    and (
                        claim_key_tokens(key) & CLAIM_DOMAIN_TOKENS
                        or {"closure", "request"}.issubset(claim_key_tokens(key))
                        or "notice" in claim_key_tokens(key)
                    )
                )
            )
            if normalized_key in NORMALIZED_FORBIDDEN_REQUEST_TRUE_CLAIM_KEYS and child is not False:
                blockers.append(f"forbidden_notice_request_claim:{child_path}")
            if generic_positive_claim_alias_key(key) and not progress_key and positive_claim_value(child):
                blockers.append(f"forbidden_notice_request_claim:{child_path}")
            if normalized_key in GENERIC_STATUS_CLAIM_KEYS and positive_claim_value(child):
                blockers.append(f"forbidden_notice_request_claim:{child_path}")
            if progress_key and not zero_progress_alias_value(child):
                blockers.append(f"forbidden_notice_request_progress_claim:{child_path}")
            if normalized_key == "readiness_gate" and child not in (None, "none"):
                blockers.append(f"forbidden_notice_request_readiness_gate:{child_path}")
            if normalized_key == "process_control" and child not in (None, "none"):
                blockers.append(f"forbidden_notice_request_process_control:{child_path}")
            validate_no_forbidden_notice_request_claims(child, child_path, blockers)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_no_forbidden_notice_request_claims(child, f"{path}[{index}]", blockers)


def require_notice_action(request: dict[str, Any]) -> dict[str, Any]:
    if request.get("schema") != WINDOW_REQUEST_SCHEMA:
        raise SystemExit("--request-json is not a player-principal lifecycle window request")
    action = request.get("player_notice_action")
    if not isinstance(action, dict):
        raise SystemExit("window request is missing player_notice_action")
    if action.get("schema") != PLAYER_NOTICE_ACTION_SCHEMA:
        raise SystemExit("player_notice_action schema mismatch")
    if action.get("required") is not True:
        raise SystemExit("player_notice_action.required must be true for a beta notice")
    if action.get("dry_run_required_before_send") is not True:
        raise SystemExit("player_notice_action must require dry-run before send")
    if action.get("real_notice_send_required_before_activation") is not True:
        raise SystemExit("player_notice_action must require real send before activation")
    if action.get("send_performed_by_request_pack") is not False:
        raise SystemExit("request pack must not claim it sent Discord")
    if action.get("request_pack_authorizes_discord") is not False:
        raise SystemExit("request pack must not authorize Discord")
    if action.get("activation_allowed_before_notice_sent") is not False:
        raise SystemExit("player_notice_action must block activation before notice send")
    if action.get("activation_blocker") != NOTICE_ACTION_BLOCKER:
        raise SystemExit("player_notice_action activation blocker mismatch")
    if action.get("non_authorization") != PLAYER_NOTICE_ACTION_NON_AUTHORIZATION:
        raise SystemExit("player_notice_action non_authorization mismatch")
    notice_path = action.get("notice_path")
    if notice_path != APPROVED_BETA_NOTICE_PATH:
        raise SystemExit(f"player_notice_action notice_path must be {APPROVED_BETA_NOTICE_PATH}")
    if request.get("user_policy") != "operator_approved_beta_users":
        raise SystemExit("window request user_policy must be operator_approved_beta_users")
    validate_exact_run_target_binding(request)
    validate_direct_join_plan_binding(request)
    blockers: list[str] = []
    validate_no_forbidden_notice_request_claims(request, "$", blockers)
    if blockers:
        raise SystemExit(
            "--request-json contains forbidden authorization/evidence/readiness claims: "
            + ", ".join(blockers)
        )
    return action


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or UTC_RE.fullmatch(value) is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def require_approved_window_bounds(request: dict[str, Any]) -> tuple[datetime, datetime]:
    window = request.get("approved_window")
    if not isinstance(window, dict):
        raise SystemExit("window request approved_window missing")
    start = parse_utc(window.get("start_utc"))
    end = parse_utc(window.get("end_utc"))
    if start is None or end is None:
        raise SystemExit("window request approved_window must name valid UTC start/end")
    return start, end


def validate_exact_run_target_binding(request: dict[str, Any]) -> None:
    blockers: list[str] = []
    target = request.get("target")
    if not isinstance(target, dict):
        raise SystemExit("window request exact run/target binding invalid: target_missing")
    for key in ("instance", "map"):
        value = target.get(key)
        if not isinstance(value, str) or SAFE_TOKEN_RE.fullmatch(value) is None:
            blockers.append(f"target_{key}_invalid")
        elif is_forbidden_flow_alias(value):
            blockers.append(f"target_{key}_alias_not_exact")

    scope = request.get("exact_target_scope")
    if not isinstance(scope, dict):
        blockers.append("exact_target_scope_missing")
    else:
        if scope.get("schema") != EXACT_TARGET_SCOPE_SCHEMA:
            blockers.append("exact_target_scope_schema_mismatch")
        if scope.get("instance") != target.get("instance"):
            blockers.append("exact_target_scope_instance_mismatch")
        if scope.get("map") != target.get("map"):
            blockers.append("exact_target_scope_map_mismatch")
        for key in ("instance_alias_allowed", "map_alias_allowed"):
            if scope.get(key) is not False:
                blockers.append(f"exact_target_scope_{key}_not_false")
        for key in ("approval_must_name_exact_instance_and_map", "target_matches_request_target"):
            if scope.get(key) is not True:
                blockers.append(f"exact_target_scope_{key}_not_true")
        if scope.get("non_authorization") != EXACT_TARGET_SCOPE_NON_AUTHORIZATION:
            blockers.append("exact_target_scope_non_authorization_mismatch")

    run_id = request.get("run_id")
    if not isinstance(run_id, str) or RUN_ID_RE.fullmatch(run_id) is None:
        blockers.append("run_id_invalid")
    window = request.get("approved_window")
    if not isinstance(window, dict):
        blockers.append("approved_window_missing")
    else:
        start = parse_utc(window.get("start_utc"))
        end = parse_utc(window.get("end_utc"))
        if start is None:
            blockers.append("approved_window_start_utc_invalid")
        if end is None:
            blockers.append("approved_window_end_utc_invalid")
        if start is not None and end is not None and not start < end:
            blockers.append("approved_window_order_invalid")
        if isinstance(run_id, str) and RUN_ID_RE.fullmatch(run_id) is not None and start is not None:
            expected_run_id = run_id_for_window_start(start)
            if run_id != expected_run_id:
                blockers.append("run_id_window_start_mismatch")

    approval_scope = request.get("current_turn_approval_scope")
    named_scope = approval_scope.get("required_named_scope") if isinstance(approval_scope, dict) else None
    if isinstance(named_scope, dict):
        expected_target = {"instance": target.get("instance"), "map": target.get("map")}
        if named_scope.get("target") != expected_target:
            blockers.append("current_turn_approval_target_mismatch")
        if isinstance(scope, dict) and named_scope.get("exact_target_instance_map") != scope:
            blockers.append("current_turn_approval_exact_target_scope_mismatch")

    if blockers:
        raise SystemExit("window request exact run/target binding invalid: " + ", ".join(blockers))


def validate_direct_join_plan_binding(request: dict[str, Any]) -> None:
    blockers: list[str] = []
    plan = request.get("direct_join_plan")
    if not isinstance(plan, dict):
        blockers.append("direct_join_plan_missing")
    else:
        expected = direct_join_plan(request)
        if plan.get("schema") != DIRECT_JOIN_PLAN_SCHEMA:
            blockers.append("direct_join_plan_schema_mismatch")
        if plan.get("target") != request.get("target"):
            blockers.append("direct_join_plan_target_mismatch")
        if plan.get("route") != "direct_join_exact_server_map":
            blockers.append("direct_join_plan_route_mismatch")
        if plan.get("direct_join_required") is not True:
            blockers.append("direct_join_plan_direct_join_required_not_true")
        for key in (
            "cluster_transfer_required",
            "extra_transfer_server_required",
            "third_ark_server_allowed",
            "broad_discord_or_community_notice_allowed",
            "raw_player_text_allowed",
            "raw_player_identity_allowed",
            "raw_player_text_or_identity_allowed",
            "secret_or_webhook_output_allowed",
            "diagnostic_candidates_allowed_for_approved_evidence",
            "organic_wait_window_authorizes_current_turn_approval",
            "organic_wait_window_authorizes_deploy_or_restart",
            "organic_wait_window_authorizes_runtime_capture",
            "organic_wait_window_counts_as_approved_runtime_evidence",
        ):
            if plan.get(key) is not False:
                blockers.append(f"direct_join_plan_{key}_not_false")
        for key in ("receipt_before_activation_required", "post_window_replay_requires_receipt"):
            if plan.get(key) is not True:
                blockers.append(f"direct_join_plan_{key}_not_true")
        if plan.get("max_running_ark_servers") != 2:
            blockers.append("direct_join_plan_max_running_ark_servers_mismatch")
        if plan.get("organic_wait_window_seconds") != requested_wait_window_seconds(request):
            blockers.append("direct_join_plan_organic_wait_window_seconds_mismatch")
        if plan.get("max_organic_wait_window_seconds") != MAX_APPROVED_WINDOW_SECONDS:
            blockers.append("direct_join_plan_max_organic_wait_window_seconds_mismatch")
        if plan.get("non_authorization") != DIRECT_JOIN_PLAN_NON_AUTHORIZATION:
            blockers.append("direct_join_plan_non_authorization_mismatch")
        if plan != expected:
            blockers.append("direct_join_plan_mismatch")
    if blockers:
        raise SystemExit("window request direct-join plan invalid: " + ", ".join(blockers))


def request_window_sendability(
    request: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    now_utc = (now or datetime.now(timezone.utc)).replace(microsecond=0).astimezone(timezone.utc)
    start, end = require_approved_window_bounds(request)
    duration_seconds = int((end - start).total_seconds())
    seconds_until_start = int((start - now_utc).total_seconds())
    seconds_until_end = int((end - now_utc).total_seconds())
    blockers: list[str] = []
    if start <= now_utc:
        blockers.append("approved_window_start_not_in_future")
    if end <= now_utc:
        blockers.append("approved_window_end_not_in_future")
    if duration_seconds <= 0:
        blockers.append("approved_window_order_invalid")
    if 0 < duration_seconds < MIN_APPROVED_WINDOW_SECONDS:
        blockers.append("approved_window_duration_below_minimum")
    if duration_seconds > MAX_APPROVED_WINDOW_SECONDS:
        blockers.append("approved_window_duration_exceeds_limit")
    if seconds_until_start > MAX_REQUEST_PREPARATION_LEAD_SECONDS:
        blockers.append("approved_window_start_too_far_from_notice_preparation")
    stale = start <= now_utc or end <= now_utc
    sendable = not blockers
    return {
        "schema": REQUEST_WINDOW_SENDABILITY_SCHEMA,
        "status": (
            "sendable_current_window"
            if sendable
            else ("stale_request_window" if stale else "not_current_window")
        ),
        "sendable": sendable,
        "current_window": sendable,
        "stale_request_window": stale,
        "confirmed_send_allowed_by_request_window": sendable,
        "dry_run_ready_to_send_allowed_by_request_window": sendable,
        "helper_invocation_allowed_by_request_window": sendable,
        "send_blocked_by_stale_window": stale,
        "send_blocked_by_non_current_window": not sendable,
        "blocker": "none" if sendable else STALE_WINDOW_BLOCKER,
        "blockers": blockers,
        "now_utc": format_utc(now_utc),
        "start_utc": format_utc(start),
        "end_utc": format_utc(end),
        "seconds_until_start": seconds_until_start,
        "seconds_until_end": seconds_until_end,
        "duration_seconds": duration_seconds,
        "max_duration_seconds": MAX_APPROVED_WINDOW_SECONDS,
        "max_start_lead_seconds": MAX_REQUEST_PREPARATION_LEAD_SECONDS,
        "request_window_must_be_regenerated": not sendable,
        "prepared_metadata_only": sendable,
        "readiness_claim_allowed": False,
        "progress_claim_allowed": False,
        "preparation_counts_as_readiness": False,
        "preparation_counts_as_progress": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def current_window_workflow(
    request: dict[str, Any],
    sendability: dict[str, Any],
) -> dict[str, Any]:
    target = request_target(request)
    restart_expectation = request.get("restart_expectation")
    if restart_expectation not in {"none", "start", "restart"}:
        restart_expectation = "restart"
    argv = [
        "python3",
        "scripts/plan_player_principal_lifecycle_runtime_window.py",
        "--instance",
        target["instance"],
        "--map",
        target["map"],
        "--start-delay-minutes",
        "5",
        "--duration-minutes",
        "15",
        "--restart-expectation",
        str(restart_expectation),
        "--user-policy",
        "operator_approved_beta_users",
        "--notice-path",
        APPROVED_BETA_NOTICE_PATH,
        "--json",
    ]
    return {
        "schema": CURRENT_WINDOW_WORKFLOW_SCHEMA,
        "status": "current_window_prepared"
        if sendability["sendable"]
        else "fresh_current_window_required",
        "request_window_sendable": sendability["sendable"],
        "stale_request_window": sendability["stale_request_window"],
        "current_window_request_must_be_regenerated": not sendability["sendable"],
        "current_window_prepared": sendability["sendable"],
        "prepared_metadata_only": sendability["sendable"],
        "readiness_claim_allowed": False,
        "progress_claim_allowed": False,
        "preparation_counts_as_readiness": False,
        "preparation_counts_as_progress": False,
        "next_exact_command_kind": "fresh_current_window_plan",
        "next_fresh_window_plan_argv": argv,
        "next_fresh_window_plan_shell": " ".join(shlex.quote(part) for part in argv),
        "plan_writes_files": False,
        "plan_touches_ark": False,
        "plan_sends_discord": False,
        "plan_authorizes_runtime": False,
        "confirmed_send_requires_current_window": True,
        "confirmed_send_requires_guarded_helper": True,
        "dry_run_or_send_metadata_counts_as_evidence": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def request_target(request: dict[str, Any]) -> dict[str, str]:
    target = request.get("target")
    if not isinstance(target, dict):
        raise SystemExit("window request target missing")
    instance = target.get("instance")
    map_name = target.get("map")
    if not isinstance(instance, str) or not isinstance(map_name, str):
        raise SystemExit("window request target must name instance and map")
    return {"instance": instance, "map": map_name}


def window_text(request: dict[str, Any]) -> str:
    window = request.get("approved_window")
    if not isinstance(window, dict):
        raise SystemExit("window request approved_window missing")
    start = window.get("start_utc")
    end = window.get("end_utc")
    if not isinstance(start, str) or not isinstance(end, str):
        raise SystemExit("window request approved_window must name start/end")
    return f"{start} a {end} UTC"


def active_notice_update_policy(helper_path: Path | None = None) -> dict[str, Any]:
    helper = helper_path if helper_path is not None else SEND_HELPER
    return {
        "schema": ACTIVE_NOTICE_UPDATE_POLICY_SCHEMA,
        "helper": str(helper),
        "channel": BETA_TEST_CHANNEL,
        "bot_channel_id": BETA_TEST_BOT_CHANNEL_ID,
        "expected_channel_id": BETA_TEST_BOT_CHANNEL_ID,
        "bidirectional_channel_env_var": "OBELISK_DISCORD_BETA_CHANNEL_ID",
        "event_sink_env_var": BETA_TEST_EVENT_SINK_ENV,
        "active_notice_state_env_var": BETA_TEST_ACTIVE_NOTICE_STATE_ENV,
        "send_helper_arg": "--send-beta-notice",
        "with_beta_controls_arg": "--with-beta-controls",
        "update_active_notice_arg": "--update-active-notice",
        "operational_message_workflow": "single_active_bot_notice",
        **discord_beta_notice_operational_boundary("active_notice_update_policy"),
        "button_custom_id_prefix": "obelisk_beta:",
        "status_summary_button_custom_id": BETA_STATUS_SUMMARY_CUSTOM_ID,
        "status_summary_response_mode": BETA_STATUS_SUMMARY_RESPONSE_MODE,
        "status_summary_button_required": True,
        "status_summary_button_writes_event": False,
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
        "status_summary_counts_as_approved_runtime_evidence": False,
        "status_summary_counts_toward_sdk": False,
        "status_summary_counts_as_readiness": False,
        "existing_active_notice_http_method": "PATCH",
        "missing_active_notice_http_method": "POST",
        "existing_active_notice_updates_in_place": True,
        "new_message_only_when_active_notice_state_missing": True,
        "repeat_everyone_mentions_suppressed_on_update": True,
        "everyone_mentions_allowed_only_on_create": True,
        "interactive_buttons_preserved_on_update": True,
        "button_interaction_response_mode": "ephemeral_ack_and_local_event_write",
        "button_interactions_ephemeral_ack_only": True,
        "button_interactions_create_channel_messages": False,
        "button_interactions_create_followup_messages": False,
        "button_interactions_update_operational_message": False,
        "button_events_claim_evidence": False,
        "button_events_claim_progress": False,
        "button_events_claim_readiness": False,
        "single_editable_notice_required": True,
        "single_editable_embed_required": True,
        "single_operational_message_required": True,
        "active_notice_state_required_for_beta_controls": True,
        "with_beta_controls_required": True,
        "update_active_notice_required": True,
        "embed_claims_evidence": False,
        "embed_claims_progress": False,
        "embed_claims_readiness": False,
        "uses_webhook": False,
        "real_send_uses_bot_channel": True,
        "bot_channel_required_for_real_send": True,
        "real_send_uses_webhook": False,
        "webhook_deprecated": True,
        "webhook_real_send_allowed": False,
        "webhook_fail_closed_for_real_sends": True,
        "old_webhook_path_allowed": False,
        "configured_send_path": "discord_bot_channel",
        "discord_bot_channel_path_enabled": True,
        "webhook_send_path_enabled": False,
        "secret_values_embedded": False,
        "communication_posture_only": True,
        "counts_as_approved_runtime_evidence": False,
        "counts_toward_sdk": False,
        "counts_as_readiness": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def beta_tester_status_workflow_plan(helper_path: Path | None = None) -> dict[str, Any]:
    status_actions = [
        {
            "state": "started",
            "button_label": "Started",
            "custom_id": "obelisk_beta:started",
            "event_type": "started",
            "map_scoped": False,
        },
        {
            "state": "loading",
            "button_label": "Loading",
            "custom_id": "obelisk_beta:loading",
            "event_type": "loading",
            "map_scoped": False,
        },
        {
            "state": "in_server",
            "button_label": "In Ragnarok / In TheIsland / In Genesis2",
            "custom_id_pattern": "obelisk_beta:in_server:<map>",
            "custom_ids": [
                "obelisk_beta:in_server:Ragnarok",
                "obelisk_beta:in_server:TheIsland",
                "obelisk_beta:in_server:Genesis2",
            ],
            "event_type": "in_server",
            "map_scoped": True,
            "allowed_maps": ["Ragnarok", "TheIsland", "Genesis2"],
        },
        {
            "state": "logged_out",
            "button_label": "Logged out",
            "custom_id": "obelisk_beta:logged_out",
            "event_type": "logged_out",
            "map_scoped": False,
        },
        {
            "state": "cluster_transfer",
            "button_label": "Cluster transfer",
            "custom_id": "obelisk_beta:cluster_transfer",
            "event_type": "cluster_transfer",
            "map_scoped": False,
        },
    ]
    summary_action = {
        "state": "status_summary",
        "button_label": "Resumen estado",
        "custom_id": BETA_STATUS_SUMMARY_CUSTOM_ID,
        "event_type": "status",
        "writes_event": False,
        "response_mode": BETA_STATUS_SUMMARY_RESPONSE_MODE,
        "uses_local_event_sink_only": True,
        "reads_discord": False,
        "sends_discord": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_toward_sdk": False,
    }
    custom_ids: list[str] = []
    for action in status_actions:
        if "custom_ids" in action:
            custom_ids.extend(action["custom_ids"])
        else:
            custom_ids.append(action["custom_id"])
    return {
        "schema": BETA_TESTER_STATUS_WORKFLOW_SCHEMA,
        "workflow": "single_editable_bot_notice_with_buttons",
        "channel": BETA_TEST_CHANNEL,
        "bot_channel_id": BETA_TEST_BOT_CHANNEL_ID,
        "expected_channel_id": BETA_TEST_BOT_CHANNEL_ID,
        "helper": str(helper_path if helper_path is not None else SEND_HELPER),
        "active_notice_update_policy": active_notice_update_policy(helper_path),
        "operational_message_workflow": "single_active_bot_notice",
        **discord_beta_notice_operational_boundary("tester_status_workflow"),
        "tester_reportable_states": [
            "started",
            "loading",
            "in_server",
            "logged_out",
            "cluster_transfer",
        ],
        "status_actions": status_actions,
        "status_custom_ids": custom_ids,
        "status_summary_action": summary_action,
        "status_summary_custom_id": BETA_STATUS_SUMMARY_CUSTOM_ID,
        "status_summary_button_required": True,
        "status_summary_button_writes_event": False,
        "status_summary_response_mode": BETA_STATUS_SUMMARY_RESPONSE_MODE,
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
        "status_summary_counts_as_approved_runtime_evidence": False,
        "status_summary_counts_toward_sdk": False,
        "status_summary_counts_as_readiness": False,
        "one_editable_notice": True,
        "single_operational_message_required": True,
        "active_notice_state_required_for_beta_controls": True,
        "new_message_only_when_active_notice_state_missing": True,
        "updates_existing_notice_when_state_present": True,
        "repeat_everyone_mentions_suppressed_on_update": True,
        "button_interaction_response_mode": "ephemeral_ack_and_local_event_write",
        "button_interactions_ephemeral_ack_only": True,
        "button_interactions_create_channel_messages": False,
        "button_interactions_create_followup_messages": False,
        "button_interactions_update_operational_message": False,
        "button_events_are_metadata_only": True,
        "button_events_claim_evidence": False,
        "button_events_claim_progress": False,
        "button_events_claim_readiness": False,
        "raw_player_text_or_identity_allowed": False,
        "secret_or_webhook_output_allowed": False,
        "cluster_transfer_button_authorizes_transfer": False,
        "cluster_transfer_button_counts_as_evidence": False,
        "embed_claims_evidence": False,
        "embed_claims_progress": False,
        "embed_claims_readiness": False,
        "send_performed_by_dry_run": False,
        "authorizes_discord": False,
        "discord_send_authorized": False,
        "discord_authorized": False,
        "authorizes_runtime_work": False,
        "runtime_capture_authorized": False,
        "server_operations_authorized": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "counts_as_readiness": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def embed_args(request: dict[str, Any], sendability: dict[str, Any]) -> list[str]:
    target = request_target(request)
    run_id = request.get("run_id")
    if not isinstance(run_id, str):
        raise SystemExit("window request run_id missing")
    notice_text = recommended_notice_text(request)
    content = (
        "@everyone\n"
        "Prueba beta Obelisk: ciclo de sesion.\n"
        f"Objetivo: {target['instance']} / {target['map']} - run {run_id}.\n"
        f"Ventana: {window_text(request)}.\n"
        f"Estado: {sendability['status']} (coordinacion solamente).\n"
        "Botones: Started, Loading, In-server, Logged-out, Cluster-transfer y "
        "Status summary (coordinacion y metadata local solamente).\n"
        f"{notice_text['recommended_discord_text_redacted']}"
    )
    return [
        "--send-beta-notice",
        "--with-beta-controls",
        "--update-active-notice",
        "--content",
        content,
    ]


def helper_option_name(value: str) -> str:
    return value.split("=", 1)[0] if value.startswith("--") else value


def validate_beta_notice_helper_args(args: list[str]) -> None:
    options = {helper_option_name(arg) for arg in args if arg.startswith("--")}
    missing = [arg for arg in BETA_NOTICE_REQUIRED_HELPER_ARGS if arg not in options]
    forbidden = sorted(options & BETA_NOTICE_FORBIDDEN_WEBHOOK_ARGS)
    if missing or forbidden:
        blockers = []
        if missing:
            blockers.append("missing_bot_notice_helper_args:" + ",".join(missing))
        if forbidden:
            blockers.append("forbidden_webhook_helper_args:" + ",".join(forbidden))
        raise SystemExit("beta notice helper args must use bot editable-notice path: " + "; ".join(blockers))


def bot_notice_send_path_report(
    helper_args: list[str],
    helper_path: Path | None = None,
) -> dict[str, Any]:
    options = {helper_option_name(arg) for arg in helper_args if arg.startswith("--")}
    required_args_present = all(arg in options for arg in BETA_NOTICE_REQUIRED_HELPER_ARGS)
    webhook_args_present = sorted(options & BETA_NOTICE_FORBIDDEN_WEBHOOK_ARGS)
    return {
        "schema": "obelisk.player-principal-lifecycle-beta-notice-bot-send-path.v1",
        "configured_send_path": "discord_bot_channel",
        "default_send_path": "discord_bot_channel",
        "real_send_path": "discord_bot_channel",
        "operational_message_workflow": "single_active_bot_notice",
        **discord_beta_notice_operational_boundary("bot_notice_send_path"),
        "channel": BETA_TEST_CHANNEL,
        "bot_channel_id": BETA_TEST_BOT_CHANNEL_ID,
        "expected_channel_id": BETA_TEST_BOT_CHANNEL_ID,
        "bot_channel_env_var": "OBELISK_DISCORD_BETA_CHANNEL_ID",
        "bot_env_vars": BETA_TEST_BOT_ENV_VARS,
        "required_helper_args": list(BETA_NOTICE_REQUIRED_HELPER_ARGS),
        "required_helper_args_present": required_args_present,
        "forbidden_webhook_args_present": webhook_args_present,
        "send_beta_notice_arg_present": "--send-beta-notice" in options,
        "with_beta_controls_arg_present": "--with-beta-controls" in options,
        "update_active_notice_arg_present": "--update-active-notice" in options,
        "single_operational_message_required": True,
        "active_notice_state_required_for_beta_controls": True,
        "single_editable_notice_required": True,
        "single_editable_embed_required": True,
        "with_beta_controls_required": True,
        "update_active_notice_required": True,
        "active_notice_update_policy": active_notice_update_policy(helper_path),
        "new_message_only_when_active_notice_state_missing": True,
        "existing_active_notice_updates_in_place": True,
        "button_interaction_response_mode": "ephemeral_ack_and_local_event_write",
        "button_interactions_ephemeral_ack_only": True,
        "button_interactions_create_channel_messages": False,
        "button_interactions_create_followup_messages": False,
        "button_interactions_update_operational_message": False,
        "button_events_claim_evidence": False,
        "button_events_claim_progress": False,
        "button_events_claim_readiness": False,
        "status_summary_response_mode": BETA_STATUS_SUMMARY_RESPONSE_MODE,
        "status_summary_creates_channel_message": False,
        "status_summary_updates_operational_message": False,
        "status_summary_creates_event": False,
        "status_summary_claims_evidence": False,
        "status_summary_claims_progress": False,
        "status_summary_claims_readiness": False,
        "embed_claims_evidence": False,
        "embed_claims_progress": False,
        "embed_claims_readiness": False,
        "uses_webhook": False,
        "real_send_uses_webhook": False,
        "webhook_env_var": BETA_TEST_WEBHOOK_ENV,
        "webhook_deprecated": True,
        "webhook_real_send_allowed": False,
        "webhook_fail_closed_for_real_sends": True,
        "webhook_fallback_allowed": False,
        "webhook_send_path_enabled": False,
        "old_webhook_path_allowed": False,
        "webhook_url_embedded": False,
        "webhook_secret_embedded": False,
        "secret_values_embedded": False,
        "send_performed_by_path_report": False,
        "authorizes_discord": False,
        "discord_send_authorized": False,
        "discord_authorized": False,
        "authorizes_runtime_work": False,
        "runtime_capture_authorized": False,
        "server_operations_authorized": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "counts_as_readiness": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def helper_script_path(helper: Path) -> Path:
    protected_paths.reject_symlink_component(helper, "--send-helper")
    return protected_paths.reject_protected_input_path(
        helper.expanduser(),
        "--send-helper",
        protected_root=SERVER_ROOT,
        approved_roots=protected_paths.approved_offline_workspace_roots(),
    )


def run_helper(
    helper: Path,
    args: list[str],
    *,
    dry_run: bool,
    dry_run_receipt: str | None = None,
) -> subprocess.CompletedProcess[str]:
    helper_path = helper_script_path(helper)
    validate_beta_notice_helper_args(args)
    command = [sys.executable, str(helper_path)]
    if dry_run:
        command.append("--dry-run")
    command.extend(args)
    if dry_run_receipt is not None:
        command.extend(["--dry-run-receipt", dry_run_receipt])
    if not dry_run:
        command.append("--confirm-approved-send")
    return subprocess.run(
        command,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def parse_helper_payload(stdout: str) -> dict[str, Any] | None:
    if not stdout.strip():
        return None
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def helper_dry_run_receipt(payload: dict[str, Any] | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    receipt = payload.get("dry_run_receipt")
    return receipt if isinstance(receipt, str) and receipt else None


def receipt_blocked_result(
    dry_run_result: subprocess.CompletedProcess[str],
    blocker: str,
) -> subprocess.CompletedProcess[str]:
    stderr = "\n".join(item for item in (dry_run_result.stderr.strip(), blocker) if item)
    return subprocess.CompletedProcess(
        args=dry_run_result.args,
        returncode=1,
        stdout="",
        stderr=stderr,
    )


def run_confirmed_helper_with_dry_run_receipt(
    helper_path: Path,
    helper_args: list[str],
) -> tuple[
    subprocess.CompletedProcess[str],
    subprocess.CompletedProcess[str],
    dict[str, Any] | None,
    str | None,
    str,
]:
    dry_run_result = run_helper(helper_path, helper_args, dry_run=True)
    if contains_secret_text(dry_run_result.stdout):
        raise SystemExit("refusing helper dry-run stdout containing webhook or secret material")
    dry_run_payload = parse_helper_payload(dry_run_result.stdout)
    if dry_run_result.returncode != 0:
        return (
            receipt_blocked_result(dry_run_result, "confirmed_send_dry_run_not_accepted"),
            dry_run_result,
            dry_run_payload,
            None,
            "inline_helper_dry_run_failed",
        )
    receipt = helper_dry_run_receipt(dry_run_payload)
    if receipt is None:
        return (
            receipt_blocked_result(dry_run_result, "confirmed_send_dry_run_receipt_missing"),
            dry_run_result,
            dry_run_payload,
            None,
            "inline_helper_dry_run_missing_receipt",
        )
    confirmed_result = run_helper(
        helper_path,
        helper_args,
        dry_run=False,
        dry_run_receipt=receipt,
    )
    return confirmed_result, dry_run_result, dry_run_payload, receipt, "inline_helper_dry_run"


def standing_launch_authority_recorded(request: dict[str, Any]) -> bool:
    return (
        isinstance(request.get("current_turn_approval_scope"), dict)
        and request["current_turn_approval_scope"].get("source_required")
        == "standing_launch_authority"
    )


def standing_authority_non_progress_boundary(
    *,
    standing: bool,
    scope: str,
) -> dict[str, Any]:
    return {
        "schema": "obelisk.player-principal-lifecycle-standing-authority-non-progress-boundary.v1",
        "scope": scope,
        "standing_launch_authority_recorded": standing,
        "recorded_standing_authority_applies_to_scoped_operator_actions_only": standing,
        "authorization_for_scoped_operator_actions_only": False,
        "authorized_by_this_report": False,
        "standing_authority_counts_as_approved_runtime_evidence": False,
        "standing_authority_counts_as_runtime_evidence": False,
        "standing_authority_counts_as_sdk_evidence": False,
        "standing_authority_counts_as_runtime_progress": False,
        "standing_authority_counts_as_sdk_progress": False,
        "standing_authority_counts_toward_p0_dependency_chain": False,
        "standing_authority_satisfies_guarded_operator_scope": standing,
        "standing_authority_grants_runtime_readiness": False,
        "standing_authority_grants_public_sdk_readiness": False,
        "standing_authority_grants_activation_readiness": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "activation_preconditions_met": False,
        "grants_readiness_claims": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def notice_authority_boundary(
    request: dict[str, Any],
    *,
    mode: str,
    completed: bool,
) -> dict[str, Any]:
    standing = standing_launch_authority_recorded(request)
    dry_run = mode == "dry_run"
    fresh_send_scope_required = not standing
    return {
        "schema": "obelisk.player-principal-lifecycle-beta-notice-authority-boundary.v1",
        "mode": mode,
        "standing_launch_authority_recorded": standing,
        "standing_launch_authority_satisfies_notice_scope": False,
        "standing_launch_authority_satisfies_dry_run_notice_preparation_scope": standing,
        "standing_launch_authority_satisfies_confirmed_discord_send_scope": standing,
        "standing_authority_satisfies_guarded_beta_notice_send_scope": standing,
        "guarded_beta_notice_send_scope_satisfied_by_standing_authority": standing,
        "guarded_discord_send_scope_satisfied": standing,
        "standing_authority_authorizes_discord_send": standing,
        "standing_authority_authorizes_marker_env_changes": False,
        "standing_authority_authorizes_server_restart": False,
        "broad_discord_authorized": False,
        "discord_authorized": False,
        "counts_as_sdk_progress": False,
        "fresh_current_turn_operator_authorization_required_before_confirmed_send": fresh_send_scope_required,
        "separate_operator_authorization_required_before_confirmed_send": fresh_send_scope_required,
        "fresh_separate_notice_approval_required": fresh_send_scope_required,
        "confirmed_send_requires_separate_explicit_discord_send_approval": fresh_send_scope_required,
        "confirm_approved_send_flag_required": True,
        "confirmed_send_performed_by_this_invocation": completed,
        "dry_run_performed_by_this_invocation": dry_run,
        "no_send_performed_by_this_invocation": mode == "no_send",
        "discord_send_performed_by_request_pack": False,
        "discord_send_performed_by_dry_run": False,
        "discord_send_performed_by_no_send": False,
        "default_sends_discord": False,
        "default_touches_ark": False,
        "default_reads_live_logs": False,
        "default_edits_markers_or_env": False,
        "runtime_or_server_scope_satisfied_by_notice": False,
        "two_server_cap_policy": two_server_cap_policy(),
        "standing_authority_non_progress_boundary": standing_authority_non_progress_boundary(
            standing=standing,
            scope="beta_notice",
        ),
        "non_authorization": NON_AUTHORIZATION,
    }


def dry_run_consumption_boundary(
    request: dict[str, Any],
    *,
    mode: str,
    accepted: bool,
    sendability: dict[str, Any],
) -> dict[str, Any]:
    standing = standing_launch_authority_recorded(request)
    sendable = bool(sendability["sendable"])
    dry_run = mode == "dry_run"
    return {
        "schema": DRY_RUN_CONSUMPTION_BOUNDARY_SCHEMA,
        "mode": mode,
        "standing_launch_authority_recorded": standing,
        "standing_launch_authority_satisfies_notice_scope": False,
        "standing_launch_authority_satisfies_dry_run_notice_preparation_scope": standing,
        "standing_launch_authority_satisfies_confirmed_discord_send_scope": standing,
        "standing_authority_satisfies_guarded_beta_notice_send_scope": standing,
        "guarded_beta_notice_send_scope_satisfied_by_standing_authority": standing,
        "guarded_discord_send_scope_satisfied": standing,
        "standing_authority_authorizes_discord_send": standing,
        "dry_run_output_consumable_under_recorded_standing_launch_authority": (
            dry_run and accepted and standing and sendable
        ),
        "broad_discord_authorized": False,
        "discord_authorized": False,
        "counts_as_sdk_progress": False,
        "fresh_separate_notice_approval_required": dry_run and accepted and sendable and not standing,
        "fresh_separate_notice_approval_required_before_confirmed_send": (
            dry_run and accepted and sendable and not standing
        ),
        "confirmed_send_requires_separate_explicit_discord_send_approval": not standing,
        "request_window_sendable": sendable,
        "stale_request_window": sendability["stale_request_window"],
        "dry_run_output_sendable": dry_run and accepted and sendable,
        "send_blocked_by_stale_window": sendability["send_blocked_by_stale_window"],
        "blocker": "none" if sendable else STALE_WINDOW_BLOCKER,
        "dry_run_output_is_notice_metadata_only": True,
        "default_sends_discord": False,
        "default_touches_ark": False,
        "default_reads_live_logs": False,
        "default_edits_markers_or_env": False,
        "dry_run_sends_discord": False,
        "no_send_sends_discord": False,
        "dry_run_touches_ark": False,
        "no_send_touches_ark": False,
        "dry_run_counts_as_approved_runtime_evidence": False,
        "dry_run_counts_toward_sdk": False,
        "dry_run_counts_toward_p0_dependency_chain": False,
        "two_server_cap_policy": two_server_cap_policy(),
        "standing_authority_non_progress_boundary": standing_authority_non_progress_boundary(
            standing=standing,
            scope="dry_run_notice_consumption",
        ),
        "non_authorization": NON_AUTHORIZATION,
    }


def notice_next_action_sequence(
    request: dict[str, Any],
    *,
    mode: str,
    completed: bool,
    accepted: bool,
    sendability: dict[str, Any],
    workflow: dict[str, Any],
    artifact_path: Path,
    active_notice_decision: dict[str, Any],
) -> list[dict[str, Any]]:
    standing = standing_launch_authority_recorded(request)
    dry_run = mode == "dry_run"
    sendable = bool(sendability["sendable"])
    ready_to_send = dry_run and accepted and sendable
    choreography = beta_runtime_choreography(request)
    if mode == "no_send":
        return [
            {
                "id": "notice_no_send_mode_recorded",
                "status": "complete_no_helper_invoked",
                "action": (
                    "No Discord helper was invoked. Review this no-send artifact, then run "
                    "a dry-run before any guarded confirmed send."
                ),
                "artifact_json": str(artifact_path),
                "discord_send_performed_by_this_action": False,
                "ark_touched_by_this_action": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_toward_sdk": False,
                **discord_beta_notice_operational_boundary("no_send_next_action"),
                "next_required_action": "beta_notice_dry_run",
                "active_notice_window_decision": active_notice_decision,
                "tester_status_workflow": beta_tester_status_workflow_plan(),
                "beta_runtime_choreography": choreography,
                "non_authorization": NON_AUTHORIZATION,
            }
        ]
    if dry_run and not sendable:
        return [
            {
                "order": 1,
                "id": "prepare_fresh_current_window_request",
                "owner": "lead",
                "status": "blocked_stale_or_non_current_request_window",
                "action": (
                    "Prepare a fresh current-window plan and request pack before any beta "
                    "notice dry-run can be treated as sendable."
                ),
                "argv": workflow["next_fresh_window_plan_argv"],
                "shell": workflow["next_fresh_window_plan_shell"],
                "request_window_sendable": False,
                "stale_request_window": sendability["stale_request_window"],
                "send_blocked_by_stale_window": sendability["send_blocked_by_stale_window"],
                "blocker": STALE_WINDOW_BLOCKER,
                "active_notice_window_decision": active_notice_decision,
                "tester_status_workflow": beta_tester_status_workflow_plan(),
                "discord_send_performed_by_this_action": False,
                "ark_touched_by_this_action": False,
                "counts_as_approved_runtime_evidence": False,
                **discord_beta_notice_operational_boundary("fresh_window_next_action"),
                "counts_toward_sdk": False,
                "counts_toward_p0_dependency_chain": False,
                "beta_runtime_choreography": choreography,
                "non_authorization": NON_AUTHORIZATION,
            }
        ]
    if dry_run:
        fresh_send_scope_required = not standing
        return [
            {
                "order": 1,
                "id": "review_beta_notice_dry_run",
                "owner": "lead",
                "status": "manual_external_not_executed_by_notice_tool",
                "action": "Review the rendered beta-test notice payload before any real send.",
                "separate_operator_authorization_required": fresh_send_scope_required,
                "authority_source": (
                    "recorded_standing_launch_authority"
                    if standing
                    else "fresh_current_turn_operator_scope_required_for_send"
                ),
                "non_authorization": NON_AUTHORIZATION,
                "dry_run_output_consumable_under_recorded_standing_launch_authority": standing,
                "active_notice_window_decision": active_notice_decision,
                "standing_launch_authority_satisfies_dry_run_notice_preparation_scope": standing,
                "standing_authority_satisfies_guarded_beta_notice_send_scope": standing,
                "guarded_beta_notice_send_scope_satisfied_by_standing_authority": standing,
                "standing_authority_authorizes_discord_send": standing,
                "discord_authorized": False,
                "fresh_separate_notice_approval_required": fresh_send_scope_required,
                "fresh_separate_notice_approval_required_before_confirmed_send": fresh_send_scope_required,
                "discord_send_performed_by_this_action": False,
                "ark_touched_by_this_action": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_sdk_progress": False,
                **discord_beta_notice_operational_boundary("review_beta_notice_dry_run_next_action"),
                "counts_toward_sdk": False,
                "counts_toward_p0_dependency_chain": False,
                "tester_status_workflow": beta_tester_status_workflow_plan(),
                "beta_runtime_choreography": choreography,
            },
            {
                "order": 2,
                "id": "send_guarded_beta_notice_after_fresh_authorization",
                "owner": "lead",
                "status": "manual_external_not_executed_by_notice_tool",
                "action": (
                    "Invoke this tool with --confirm-approved-send and --json under the "
                    "recorded standing launch authority."
                    if standing
                    else "Invoke this tool with --confirm-approved-send and --json only after "
                    "fresh exact operator notice scope is present."
                ),
                "argv": [
                    str(Path(sys.executable).name or "python3"),
                    str(Path(__file__).name),
                    "--request-json",
                    request["_resolved_request_json_path"],
                    "--confirm-approved-send",
                    "--artifact-json",
                    str(artifact_path),
                    "--json",
                ],
                "channel": BETA_TEST_CHANNEL,
                "bot_channel_id": BETA_TEST_BOT_CHANNEL_ID,
                "expected_channel_id": BETA_TEST_BOT_CHANNEL_ID,
                "bot_env_vars": BETA_TEST_BOT_ENV_VARS,
                "required_env_vars": BETA_TEST_BOT_ENV_VARS,
                "webhook_env_var": BETA_TEST_WEBHOOK_ENV,
                "webhook_deprecated": True,
                "webhook_real_send_allowed": False,
                "webhook_fail_closed_for_real_sends": True,
                "webhook_fallback_allowed": False,
                "mentions_everyone": True,
                "content": "@everyone",
                "webhook_url_embedded": False,
                "secret_values_embedded": False,
                "configured_send_path": "discord_bot_channel",
                "operational_message_workflow": "single_active_bot_notice",
                **discord_beta_notice_operational_boundary("send_guarded_beta_notice_next_action"),
                "single_operational_message_required": True,
                "active_notice_state_required_for_beta_controls": True,
                "single_editable_embed_required": True,
                "single_editable_notice_required": True,
                "with_beta_controls_required": True,
                "update_active_notice_required": True,
                "new_message_only_when_active_notice_state_missing": True,
                "existing_active_notice_updates_in_place": True,
                "button_interaction_response_mode": "ephemeral_ack_and_local_event_write",
                "button_interactions_create_channel_messages": False,
                "button_events_claim_evidence": False,
                "button_events_claim_progress": False,
                "button_events_claim_readiness": False,
                "status_summary_creates_channel_message": False,
                "status_summary_claims_evidence": False,
                "status_summary_claims_progress": False,
                "status_summary_claims_readiness": False,
                "embed_claims_evidence": False,
                "embed_claims_progress": False,
                "embed_claims_readiness": False,
                "ready_to_send_via_discord_bot_channel": ready_to_send,
                "ready_to_send_via_obelisk_beta_test_webhook_url": False,
                "request_window_sendable": sendable,
                "stale_request_window": sendability["stale_request_window"],
                "send_blocked_by_stale_window": sendability["send_blocked_by_stale_window"],
                "active_notice_window_decision": active_notice_decision,
                "lead_input_required_before_send": ready_to_send and fresh_send_scope_required,
                "send_next_action_satisfied_by_recorded_standing_authority": ready_to_send and standing,
                "standing_authority_satisfies_guarded_beta_notice_send_scope": standing,
                "guarded_beta_notice_send_scope_satisfied_by_standing_authority": standing,
                "standing_authority_authorizes_discord_send": standing,
                "runtime_window_should_not_wait_for_lead_notice_authorization": ready_to_send and standing,
                "separate_operator_authorization_required": fresh_send_scope_required,
                "fresh_separate_notice_approval_required": ready_to_send and fresh_send_scope_required,
                "fresh_separate_notice_approval_required_before_confirmed_send": (
                    ready_to_send and fresh_send_scope_required
                ),
                "explicit_confirm_approved_send_invocation_required": True,
                "default_invocation": False,
                "guarded_helper_invocation_required": True,
                "discord_send_performed_by_dry_run": False,
                "blocker": (
                    "none"
                    if ready_to_send and standing
                    else DISCORD_SEND_SCOPE_BLOCKER
                    if ready_to_send
                    else request_window_blocker(sendability)
                ),
                "discord_authorized": False,
                "ark_touched_by_this_action": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_sdk_progress": False,
                "counts_toward_sdk": False,
                "counts_toward_p0_dependency_chain": False,
                "tester_status_workflow": beta_tester_status_workflow_plan(),
                "beta_runtime_choreography": choreography,
                "non_authorization": NON_AUTHORIZATION,
            },
        ]
    return [
        {
            "order": 1,
            "id": "consume_confirmed_notice_in_activation_preconditions",
            "owner": "lead",
            "status": "manual_external_not_executed_by_notice_tool",
            "action": (
                "Use this confirmed notice report as input to the offline activation-preconditions checker."
            ),
            "notice_report_mode": "confirmed_send" if completed else "not_confirmed",
            "active_notice_window_decision": active_notice_decision,
            "separate_operator_authorization_required": not standing,
            "fresh_separate_notice_approval_required": not standing,
            "standing_authority_satisfies_guarded_beta_notice_send_scope": standing,
            "guarded_beta_notice_send_scope_satisfied_by_standing_authority": standing,
            "standing_authority_authorizes_discord_send": standing,
            "notice_action_covered_by_standing_launch_authority": standing,
            "discord_authorized": False,
            "runtime_or_server_scope_satisfied_by_notice": False,
            "discord_send_performed_by_this_action": False,
            "ark_touched_by_this_action": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_sdk_progress": False,
            **discord_beta_notice_operational_boundary("confirmed_notice_consumption_next_action"),
            "counts_toward_sdk": False,
            "counts_toward_p0_dependency_chain": False,
            "tester_status_workflow": beta_tester_status_workflow_plan(),
            "beta_runtime_choreography": choreography,
            "non_authorization": NON_AUTHORIZATION,
        }
    ]


def confirmed_send_argv(request: dict[str, Any]) -> list[str]:
    return [
        str(Path(sys.executable).name or "python3"),
        str(Path(__file__).name),
        "--request-json",
        request["_resolved_request_json_path"],
        "--confirm-approved-send",
        "--json",
    ]


def confirmed_send_argv_with_artifact(request: dict[str, Any], artifact_path: Path) -> list[str]:
    argv = confirmed_send_argv(request)
    index = argv.index("--json")
    return [*argv[:index], "--artifact-json", str(artifact_path), *argv[index:]]


def dry_run_ready_to_send_report(
    request: dict[str, Any],
    *,
    mode: str,
    dry_run_accepted: bool,
    helper_path: Path,
    sendability: dict[str, Any],
    workflow: dict[str, Any],
    artifact_path: Path,
    active_notice_decision: dict[str, Any],
) -> dict[str, Any]:
    standing = standing_launch_authority_recorded(request)
    sendable = bool(sendability["sendable"])
    dry_run = mode == "dry_run"
    ready = dry_run and dry_run_accepted and sendable
    lead_input_required = ready and not standing
    return {
        "schema": DRY_RUN_READY_TO_SEND_SCHEMA,
        "mode": mode,
        "ready_to_send": ready,
        "ready_to_send_via_discord_bot_channel": ready,
        "ready_to_send_via_obelisk_beta_test_webhook_url": False,
        "ready_to_send_via_env_var": "OBELISK_DISCORD_BETA_CHANNEL_ID",
        "prepared_notice_action": ready,
        "prepared_metadata_only": ready,
        "preparation_status": (
            "prepared_metadata_only" if ready else "not_prepared"
        ),
        "ready_fields_are_sendability_gates_only": True,
        "ready_fields_are_readiness_claims": False,
        "bot_channel_id": BETA_TEST_BOT_CHANNEL_ID,
        "expected_channel_id": BETA_TEST_BOT_CHANNEL_ID,
        "bot_env_vars": BETA_TEST_BOT_ENV_VARS,
        "channel": BETA_TEST_CHANNEL,
        "helper": str(helper_path),
        "configured_send_path": "discord_bot_channel",
        "operational_message_workflow": "single_active_bot_notice",
        **discord_beta_notice_operational_boundary("dry_run_ready_to_send"),
        "single_operational_message_required": True,
        "active_notice_state_required_for_beta_controls": True,
        "single_editable_notice_required": True,
        "single_editable_embed_required": True,
        "with_beta_controls_required": True,
        "update_active_notice_required": True,
        "new_message_only_when_active_notice_state_missing": True,
        "existing_active_notice_updates_in_place": True,
        "required_helper_args": list(BETA_NOTICE_REQUIRED_HELPER_ARGS),
        "argv": confirmed_send_argv_with_artifact(request, artifact_path)
        if ready
        else workflow["next_fresh_window_plan_argv"],
        "confirmed_send_artifact_json": str(artifact_path) if ready else None,
        "required_env_vars": BETA_TEST_BOT_ENV_VARS,
        "webhook_env_var": BETA_TEST_WEBHOOK_ENV,
        "webhook_deprecated": True,
        "webhook_real_send_allowed": False,
        "webhook_fail_closed_for_real_sends": True,
        "webhook_fallback_allowed": False,
        "mentions_everyone": ready,
        "content": "@everyone" if ready else None,
        "webhook_url_embedded": False,
        "webhook_secret_embedded": False,
        "secret_values_embedded": False,
        "active_notice_update_policy": active_notice_update_policy(helper_path),
        "active_notice_window_decision": active_notice_decision,
        "tester_status_workflow": beta_tester_status_workflow_plan(helper_path),
        "button_interaction_response_mode": "ephemeral_ack_and_local_event_write",
        "button_interactions_ephemeral_ack_only": True,
        "button_interactions_create_channel_messages": False,
        "button_interactions_create_followup_messages": False,
        "button_interactions_update_operational_message": False,
        "button_events_claim_evidence": False,
        "button_events_claim_progress": False,
        "button_events_claim_readiness": False,
        "status_summary_response_mode": BETA_STATUS_SUMMARY_RESPONSE_MODE,
        "status_summary_creates_channel_message": False,
        "status_summary_updates_operational_message": False,
        "status_summary_creates_event": False,
        "status_summary_claims_evidence": False,
        "status_summary_claims_progress": False,
        "status_summary_claims_readiness": False,
        "embed_claims_evidence": False,
        "embed_claims_progress": False,
        "embed_claims_readiness": False,
        "send_performed_by_dry_run": False,
        "discord_sent": False,
        "guarded_helper_invocation_required": True,
        "explicit_confirm_approved_send_invocation_required": True,
        "approval_scope_required": BETA_TEST_BOT_CHANNEL_ID,
        "approval_scope_label": BETA_TEST_CHANNEL,
        "standing_launch_authority_recorded": standing,
        "standing_launch_authority_satisfies_notice_scope": False,
        "standing_launch_authority_satisfies_dry_run_notice_preparation_scope": standing,
        "standing_launch_authority_satisfies_confirmed_discord_send_scope": standing,
        "standing_authority_satisfies_guarded_beta_notice_send_scope": standing,
        "guarded_beta_notice_send_scope_satisfied_by_standing_authority": standing,
        "standing_authority_authorizes_discord_send": standing,
        "standing_authority_authorizes_marker_env_changes": False,
        "standing_authority_authorizes_server_restart": False,
        "standing_debug_authority_recorded": standing,
        "recorded_standing_debug_authority_satisfies_notice_scope": False,
        "recorded_standing_debug_authority_satisfies_dry_run_notice_preparation_scope": standing,
        "request_window_sendable": sendable,
        "stale_request_window": sendability["stale_request_window"],
        "send_blocked_by_stale_window": sendability["send_blocked_by_stale_window"],
        "request_window_sendability": sendability,
        "current_window_workflow": workflow,
        "notice_send_is_explicit_next_action": ready,
        "send_next_action_satisfied_by_recorded_standing_authority": ready and standing,
        "lead_input_required_before_send": lead_input_required,
        "fresh_separate_notice_approval_required": lead_input_required,
        "fresh_separate_notice_approval_required_before_confirmed_send": lead_input_required,
        "send_next_action_requires_fresh_user_each_time": lead_input_required,
        "runtime_window_should_not_wait_for_lead_notice_authorization": ready and standing,
        "runtime_or_server_scope_satisfied_by_notice": False,
        "authorizes_discord": False,
        "discord_authorized": False,
        "broad_discord_authorized": False,
        "discord_send_authorized": False,
        "authorizes_runtime_work": False,
        "runtime_capture_authorized": False,
        "runtime_window_authorized": False,
        "server_operations_authorized": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_toward_public_sdk": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "counts_as_readiness": False,
        "readiness_claim_allowed": False,
        "progress_claim_allowed": False,
        "preparation_counts_as_readiness": False,
        "preparation_counts_as_progress": False,
        "publication_authorized": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "recommended_notice_text": recommended_notice_text(request),
        "tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "exact_tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
        "beta_runtime_choreography": beta_runtime_choreography(request),
        "one_tester_direct_join_wait_for_exact_checkjoin_required": True,
        "mixed_transfer_reconnect_same_approved_window_allowed": False,
        "stale_or_diagnostic_exact_checkjoin_lines_are_stimulus_clues_only": True,
        "two_server_cap_policy": two_server_cap_policy(),
        "standing_authority_non_progress_boundary": standing_authority_non_progress_boundary(
            standing=standing,
            scope="dry_run_ready_to_send",
        ),
        "blocker": (
            "none"
            if ready and standing
            else DISCORD_SEND_SCOPE_BLOCKER
            if ready
            else (
                STALE_WINDOW_BLOCKER
                if not sendable
                else (
                    "dry_run_not_accepted"
                    if dry_run
                    else ("no_send_mode_notice_not_attempted" if mode == "no_send" else "not_dry_run")
                )
            )
        ),
        "non_authorization": NON_AUTHORIZATION,
    }


def helper_blocked_result(sendability: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="",
        stderr=sendability["blocker"],
    )


def helper_no_send_result() -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="",
        stderr="no_send_mode_notice_not_attempted",
    )


def helper_was_invoked(helper_result: subprocess.CompletedProcess[str]) -> bool:
    return bool(helper_result.args)


def helper_ready_status(
    *,
    dry_run: bool,
    helper_result: subprocess.CompletedProcess[str],
    helper_payload: dict[str, Any] | None,
    sendability: dict[str, Any],
) -> tuple[bool, bool, bool]:
    if not sendability["sendable"]:
        return False, False, False
    accepted = helper_result.returncode == 0 and (not dry_run or helper_payload is None)
    dry_run_accepted = helper_result.returncode == 0 and dry_run and isinstance(helper_payload, dict)
    completed = (not dry_run) and helper_result.returncode == 0
    return accepted, dry_run_accepted, completed


def request_window_blocker(sendability: dict[str, Any]) -> str:
    return (
        "none"
        if sendability["sendable"]
        else STALE_WINDOW_BLOCKER
    )


def configured_active_notice_state_path() -> Path:
    raw = os.environ.get(BETA_TEST_ACTIVE_NOTICE_STATE_ENV) or str(DEFAULT_ACTIVE_NOTICE_STATE)
    path = Path(raw).expanduser()
    return path if path.is_absolute() else REPO_ROOT / path


def active_notice_state_summary() -> dict[str, Any]:
    path = configured_active_notice_state_path()
    summary: dict[str, Any] = {
        "path": str(path),
        "present": False,
        "valid": False,
        "metadata_only": False,
        "schema": None,
        "message_id": None,
        "blockers": [],
        "metadata_blockers": [],
    }
    try:
        protected_paths.reject_symlink_component(path, "active_notice_state")
    except SystemExit as exc:
        summary["blockers"].append(f"active_notice_state_path_rejected:{exc}")
        return summary
    if not path.exists():
        return summary
    summary["present"] = True
    try:
        resolved = protected_paths.reject_protected_input_path(
            path,
            "active_notice_state",
            protected_root=SERVER_ROOT,
            approved_roots=protected_paths.approved_offline_workspace_roots(),
        )
    except SystemExit as exc:
        summary["blockers"].append(f"active_notice_state_path_protected:{exc}")
        return summary
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        summary["blockers"].append(f"active_notice_state_unreadable:{exc}")
        return summary
    if not isinstance(payload, dict):
        summary["blockers"].append("active_notice_state_not_object")
        return summary
    summary["schema"] = payload.get("schema")
    summary["message_id"] = payload.get("message_id")
    if payload.get("schema") != "obelisk.discord-beta-bridge-active-notice.v1":
        summary["blockers"].append("active_notice_state_schema_mismatch")
    if payload.get("channel_id") != BETA_TEST_BOT_CHANNEL_ID:
        summary["blockers"].append("active_notice_state_channel_mismatch")
    message_id = payload.get("message_id")
    if not isinstance(message_id, str) or not message_id.isdigit():
        summary["blockers"].append("active_notice_state_message_id_invalid")
    metadata_blockers: list[str] = []
    validate_no_forbidden_notice_request_claims(
        payload,
        "$.active_notice_state",
        metadata_blockers,
    )
    if metadata_blockers:
        summary["metadata_blockers"] = metadata_blockers
        summary["blockers"].extend(metadata_blockers)
    summary["metadata_only"] = not metadata_blockers
    summary["valid"] = not summary["blockers"]
    return summary


def active_notice_window_decision(
    *,
    sendability: dict[str, Any],
    mode: str,
    report_ready: bool,
) -> dict[str, Any]:
    active_state = active_notice_state_summary()
    sendable = bool(sendability["sendable"])
    present = bool(active_state["present"])
    valid_present = bool(active_state["valid"])
    if not sendable and valid_present:
        decision = "create_fresh_window_reuse_active_notice_message_only"
    elif not sendable and present:
        decision = "create_fresh_window_repair_active_notice_state_before_notice"
    elif not sendable:
        decision = "create_fresh_window_then_create_active_notice"
    elif report_ready:
        decision = "wait_for_separate_discord_send_scope_then_send_guarded_notice"
    else:
        decision = "wait_for_current_window_notice_preconditions"
    return {
        "schema": ACTIVE_NOTICE_WINDOW_DECISION_SCHEMA,
        "mode": mode,
        "decision": decision,
        "request_window_sendability_status": sendability["status"],
        "request_window_sendable": sendable,
        "request_window_blockers": list(sendability["blockers"]),
        "approved_window_start_not_in_future": "approved_window_start_not_in_future"
        in sendability["blockers"],
        "stale_request_window": sendability["stale_request_window"],
        "send_blocked_by_stale_window": sendability["send_blocked_by_stale_window"],
        "fresh_window_required": not sendable,
        "fresh_window_required_after_stale_request": not sendable,
        "wait_allowed_for_current_window_notice_scope": sendable and not report_ready,
        "wait_without_fresh_window_allowed": sendable,
        "active_notice_state": active_state,
        "active_notice_state_present": present,
        "active_notice_state_valid": bool(active_state["valid"]),
        "active_notice_state_is_notice_report": False,
        "active_notice_reuse_scope": "communication_state_only",
        "active_notice_can_be_reused_only_after_fresh_window_notice": (
            not sendable and valid_present
        ),
        "reuse_existing_active_notice_message_only": not sendable and valid_present,
        "direct_helper_patch_changes_communication_state_only": True,
        "active_notice_state_counts_as_confirmed_notice": False,
        "active_notice_state_counts_as_approved_runtime_evidence": False,
        "active_notice_state_counts_as_runtime_evidence": False,
        "active_notice_state_counts_as_sdk_evidence": False,
        "active_notice_state_counts_toward_sdk": False,
        "active_notice_state_counts_toward_p0_dependency_chain": False,
        "active_notice_state_counts_as_readiness": False,
        "active_notice_state_authorizes_activation": False,
        "runtime_or_server_scope_satisfied_by_active_notice_state": False,
        "confirmed_beta_notice_report_required_before_activation": True,
        "activation_preconditions_required_before_activation": True,
        "non_authorization": NON_AUTHORIZATION,
    }


def report_next_blocker(
    *,
    mode: str,
    ready: bool,
    standing_authority: bool,
    sendability: dict[str, Any],
) -> str:
    if ready:
        return "none" if standing_authority else DISCORD_SEND_SCOPE_BLOCKER
    if not sendability["sendable"]:
        return STALE_WINDOW_BLOCKER
    if mode == "dry_run":
        return "dry_run_not_accepted"
    if mode == "no_send":
        return "no_send_mode_notice_not_attempted"
    return "confirmed_send_not_completed"


def report_sendability_flags(sendability: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_window_sendable": sendability["sendable"],
        "current_request_window": sendability["current_window"],
        "stale_request_window": sendability["stale_request_window"],
        "send_blocked_by_stale_window": sendability["send_blocked_by_stale_window"],
        "send_blocked_by_non_current_window": sendability["send_blocked_by_non_current_window"],
        "request_window_blocker": request_window_blocker(sendability),
    }


def dry_run_blocker_for_ready_report(
    *,
    ready: bool,
    standing: bool,
    mode: str,
    sendability: dict[str, Any],
) -> str:
    if ready:
        return "none" if standing else DISCORD_SEND_SCOPE_BLOCKER
    if not sendability["sendable"]:
        return STALE_WINDOW_BLOCKER
    if mode == "dry_run":
        return "dry_run_not_accepted"
    if mode == "no_send":
        return "no_send_mode_notice_not_attempted"
    return "not_dry_run"


def guarded_beta_notice_action_report(
    request: dict[str, Any],
    notice_action: dict[str, Any],
    *,
    mode: str,
    helper_path: Path,
    helper_result: subprocess.CompletedProcess[str],
    sendability: dict[str, Any],
) -> dict[str, Any]:
    helper_invoked = helper_was_invoked(helper_result)
    completed = mode == "confirmed_send" and helper_invoked and helper_result.returncode == 0
    standing_authority = standing_launch_authority_recorded(request)
    helper_options = {
        helper_option_name(str(arg))
        for arg in helper_result.args
        if isinstance(arg, str) and arg.startswith("--")
    }
    return {
        "schema": GUARDED_BETA_NOTICE_ACTION_SCHEMA,
        "mode": mode,
        "request_json": {
            "path": request["_resolved_request_json_path"],
            "sha256": request["_request_json_sha256"],
        },
        "target": request_target(request),
        "run_id": request.get("run_id"),
        "notice_path": notice_action.get("notice_path"),
        "player_notice_action": notice_action,
        "helper": str(helper_path),
        "helper_returncode": helper_result.returncode,
        "helper_returncode_zero": helper_result.returncode == 0,
        "helper_invoked": helper_invoked,
        "guarded_helper_invocation": "--confirm-approved-send" in helper_options,
        "confirm_approved_send_arg_used": mode == "confirmed_send",
        "approval_scope_arg_used": False,
        "approval_scope": BETA_TEST_BOT_CHANNEL_ID if helper_invoked and mode == "confirmed_send" else "dry_run_only",
        "dry_run_receipt_required_for_real_send": True,
        "dry_run_receipt_arg_used": "--dry-run-receipt" in helper_options,
        "dry_run_receipt_supplied_to_helper": "--dry-run-receipt" in helper_options,
        "dry_run_receipt_from_exact_helper_dry_run": (
            mode == "confirmed_send" and "--dry-run-receipt" in helper_options
        ),
        "bot_notice_helper": True,
        "bot_channel_id": BETA_TEST_BOT_CHANNEL_ID,
        "expected_channel_id": BETA_TEST_BOT_CHANNEL_ID,
        "configured_send_path": "discord_bot_channel",
        "operational_message_workflow": "single_active_bot_notice",
        **discord_beta_notice_operational_boundary("guarded_beta_notice_action"),
        "single_operational_message_required": True,
        "active_notice_state_required_for_beta_controls": True,
        "single_editable_notice_required": True,
        "single_editable_embed_required": True,
        "with_beta_controls_required": True,
        "update_active_notice_required": True,
        "new_message_only_when_active_notice_state_missing": True,
        "existing_active_notice_updates_in_place": True,
        "button_interaction_response_mode": "ephemeral_ack_and_local_event_write",
        "button_interactions_ephemeral_ack_only": True,
        "button_interactions_create_channel_messages": False,
        "button_interactions_create_followup_messages": False,
        "button_interactions_update_operational_message": False,
        "button_events_claim_evidence": False,
        "button_events_claim_progress": False,
        "button_events_claim_readiness": False,
        "status_summary_response_mode": BETA_STATUS_SUMMARY_RESPONSE_MODE,
        "status_summary_creates_channel_message": False,
        "status_summary_updates_operational_message": False,
        "status_summary_creates_event": False,
        "status_summary_claims_evidence": False,
        "status_summary_claims_progress": False,
        "status_summary_claims_readiness": False,
        "embed_claims_evidence": False,
        "embed_claims_progress": False,
        "embed_claims_readiness": False,
        "send_beta_notice_arg_used": "--send-beta-notice" in helper_options,
        "with_beta_controls_arg_used": "--with-beta-controls" in helper_options,
        "update_active_notice_arg_used": "--update-active-notice" in helper_options,
        "uses_webhook": False,
        "webhook_deprecated": True,
        "webhook_real_send_allowed": False,
        "webhook_fail_closed_for_real_sends": True,
        "webhook_fallback_allowed": False,
        "real_beta_test_notice_action_completed": completed,
        "no_send_mode": mode == "no_send",
        "dry_run_required_before_send": True,
        "real_notice_send_required_before_activation": True,
        "send_performed_by_request_pack": False,
        "request_pack_authorizes_discord": False,
        "authorizes_discord": False,
        "discord_authorized": False,
        "discord_send_authorized": False,
        "discord_authorized_by_this_report": False,
        "current_turn_approval_recorded": False,
        "current_turn_scope_authorized": False,
        "standing_launch_authority_recorded": standing_authority,
        "standing_launch_authority_satisfies_notice_scope": False,
        "standing_launch_authority_satisfies_dry_run_notice_preparation_scope": standing_authority,
        "standing_launch_authority_satisfies_confirmed_discord_send_scope": standing_authority,
        "standing_authority_satisfies_guarded_beta_notice_send_scope": standing_authority,
        "guarded_beta_notice_send_scope_satisfied_by_standing_authority": standing_authority,
        "guarded_discord_send_scope_satisfied": standing_authority,
        "standing_authority_authorizes_discord_send": standing_authority,
        "standing_authority_authorizes_marker_env_changes": False,
        "standing_authority_authorizes_server_restart": False,
        "confirmed_send_requires_separate_explicit_discord_send_approval": not standing_authority,
        "notice_action_covered_by_standing_launch_authority": standing_authority,
        "request_window_sendable": sendability["sendable"],
        "stale_request_window": sendability["stale_request_window"],
        "send_blocked_by_stale_window": sendability["send_blocked_by_stale_window"],
        "blocker": request_window_blocker(sendability),
        "authorizes_runtime_work": False,
        "runtime_capture_authorized": False,
        "runtime_window_authorized": False,
        "marker_env_changes_authorized": False,
        "server_operations_authorized": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_toward_v1_completion": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "counts_as_readiness": False,
        "beta_runtime_choreography": beta_runtime_choreography(request),
        "active_player_no_accepted_events_policy": active_player_no_accepted_events_policy(request),
        "one_tester_direct_join_wait_for_exact_checkjoin_required": True,
        "mixed_transfer_reconnect_same_approved_window_allowed": False,
        "stale_or_diagnostic_exact_checkjoin_lines_are_stimulus_clues_only": True,
        "two_server_cap_policy": two_server_cap_policy(),
        "standing_authority_non_progress_boundary": standing_authority_non_progress_boundary(
            standing=standing_authority,
            scope="guarded_beta_notice_action",
        ),
        "non_authorization": NON_AUTHORIZATION,
    }


def main() -> int:
    args = parse_args()
    mode = "confirmed_send" if args.confirm_approved_send else "no_send" if args.no_send else "dry_run"
    dry_run = mode == "dry_run"
    request = read_json(args.request_json)
    standing_authority = standing_launch_authority_recorded(request)
    notice_action = require_notice_action(request)
    helper_path = helper_script_path(args.send_helper)
    sendability = request_window_sendability(request)
    workflow = current_window_workflow(request, sendability)
    artifact_path = notice_artifact_path(args, request, mode)
    confirmed_artifact_path = (
        artifact_path if mode == "confirmed_send" else protected_default_notice_artifact_path(request, "confirmed_send")
    )
    helper_args = embed_args(request, sendability) if sendability["sendable"] and mode != "no_send" else []
    receipt_dry_run_result: subprocess.CompletedProcess[str] | None = None
    receipt_dry_run_payload: dict[str, Any] | None = None
    confirmed_dry_run_receipt: str | None = None
    confirmed_dry_run_receipt_source = "not_confirmed_send"
    if mode == "no_send":
        helper_result = helper_no_send_result()
    elif sendability["sendable"]:
        if mode == "confirmed_send":
            (
                helper_result,
                receipt_dry_run_result,
                receipt_dry_run_payload,
                confirmed_dry_run_receipt,
                confirmed_dry_run_receipt_source,
            ) = run_confirmed_helper_with_dry_run_receipt(helper_path, helper_args)
        else:
            helper_result = run_helper(helper_path, helper_args, dry_run=dry_run)
    else:
        helper_result = helper_blocked_result(sendability)
    if dry_run and helper_was_invoked(helper_result) and contains_secret_text(helper_result.stdout):
        raise SystemExit("refusing helper dry-run stdout containing webhook or secret material")
    helper_payload = parse_helper_payload(helper_result.stdout)
    accepted, dry_run_accepted, completed = helper_ready_status(
        dry_run=dry_run,
        helper_result=helper_result,
        helper_payload=helper_payload,
        sendability=sendability,
    )
    confirmed_dry_run_receipt_validated = (
        mode == "confirmed_send"
        and completed
        and isinstance(helper_payload, dict)
        and helper_payload.get("dry_run_receipt_validated") is True
        and helper_payload.get("dry_run_receipt") == confirmed_dry_run_receipt
    )
    report_ready = dry_run_accepted if dry_run else accepted if mode == "confirmed_send" else False
    active_notice_decision = active_notice_window_decision(
        sendability=sendability,
        mode=mode,
        report_ready=report_ready,
    )
    report = {
        "schema": SCHEMA,
        "ready": report_ready,
        "prepared": report_ready,
        "notice_prepared": report_ready,
        "prepared_notice_action": report_ready,
        "prepared_metadata_only": report_ready,
        "preparation_status": (
            "prepared_metadata_only"
            if report_ready
            else "preparation_blocked_metadata_only"
        ),
        "ready_field_is_helper_success_gate_only": True,
        "ready_field_is_readiness_claim": False,
        "mode": mode,
        "request_json": {
            "path": request["_resolved_request_json_path"],
            "sha256": request["_request_json_sha256"],
        },
        "notice_action_artifact_schema": NOTICE_ACTION_ARTIFACT_SCHEMA,
        "notice_action_sidecar_json": str(artifact_path),
        "confirmed_notice_sidecar_json_expected": str(confirmed_artifact_path),
        "sidecar_required_for_confirmed_send_consumption": True,
        "stdout_only_confirmation_accepted": False,
        "target": request_target(request),
        "run_id": request.get("run_id"),
        "notice_path": notice_action.get("notice_path"),
        "player_notice_action": notice_action,
        "dry_run_required_before_send": True,
        "real_notice_send_required_before_activation": True,
        "activation_blocker_until_sent": NOTICE_ACTION_BLOCKER,
        "recommended_notice_text": recommended_notice_text(request),
        "tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "exact_tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
        "beta_runtime_choreography": beta_runtime_choreography(request),
        "active_player_no_accepted_events_policy": active_player_no_accepted_events_policy(request),
        "checkjoin_stimulus_boundary": checkjoin_stimulus_boundary(),
        "one_tester_direct_join_wait_for_exact_checkjoin_required": True,
        "mixed_transfer_reconnect_same_approved_window_allowed": False,
        "stale_or_diagnostic_exact_checkjoin_lines_are_stimulus_clues_only": True,
        "two_server_cap_policy": two_server_cap_policy(),
        "helper": str(args.send_helper),
        "helper_returncode": helper_result.returncode,
        "helper_stderr": redact_helper_text(helper_result.stderr),
        "helper_args": helper_args,
        "helper_invoked": helper_was_invoked(helper_result),
        "bot_notice_send_path": bot_notice_send_path_report(helper_args, helper_path),
        "dry_run_payload": helper_payload if dry_run else None,
        "confirmed_send_dry_run_receipt_required": True,
        "confirmed_send_dry_run_receipt": confirmed_dry_run_receipt,
        "confirmed_send_dry_run_receipt_source": confirmed_dry_run_receipt_source,
        "confirmed_send_dry_run_receipt_preflight_invoked": (
            receipt_dry_run_result is not None and helper_was_invoked(receipt_dry_run_result)
        ),
        "confirmed_send_dry_run_receipt_preflight_returncode": (
            receipt_dry_run_result.returncode if receipt_dry_run_result is not None else None
        ),
        "confirmed_send_dry_run_receipt_preflight_returncode_zero": (
            receipt_dry_run_result.returncode == 0 if receipt_dry_run_result is not None else False
        ),
        "confirmed_send_dry_run_receipt_preflight_payload": receipt_dry_run_payload
        if mode == "confirmed_send"
        else None,
        "confirmed_send_dry_run_receipt_supplied_to_helper": (
            mode == "confirmed_send" and confirmed_dry_run_receipt is not None
        ),
        "confirmed_send_dry_run_receipt_validated_by_helper": confirmed_dry_run_receipt_validated,
        "confirmed_send_helper_payload": helper_payload if mode == "confirmed_send" else None,
        "request_window_sendability": sendability,
        "current_window_workflow": workflow,
        "active_notice_window_decision": active_notice_decision,
        "active_notice_update_policy": active_notice_update_policy(helper_path),
        "tester_status_workflow": beta_tester_status_workflow_plan(helper_path),
        "next_blocker": report_next_blocker(
            mode=mode,
            ready=report_ready,
            standing_authority=standing_authority,
            sendability=sendability,
        ),
        "dry_run_ready_to_send": dry_run_ready_to_send_report(
            request,
            mode=mode,
            dry_run_accepted=dry_run_accepted,
            helper_path=helper_path,
            sendability=sendability,
            workflow=workflow,
            artifact_path=confirmed_artifact_path,
            active_notice_decision=active_notice_decision,
        ),
        "guarded_beta_notice_action": guarded_beta_notice_action_report(
            request,
            notice_action,
            mode=mode,
            helper_path=helper_path,
            helper_result=helper_result,
            sendability=sendability,
        ),
        "notice_authority_boundary": notice_authority_boundary(
            request,
            mode=mode,
            completed=completed,
        ),
        "dry_run_consumption_boundary": dry_run_consumption_boundary(
            request,
            mode=mode,
            accepted=dry_run_accepted if dry_run else accepted,
            sendability=sendability,
        ),
        "next_action_sequence": notice_next_action_sequence(
            request,
            mode=mode,
            completed=completed,
            accepted=dry_run_accepted if dry_run else accepted,
            sendability=sendability,
            workflow=workflow,
            artifact_path=artifact_path if mode == "no_send" else confirmed_artifact_path,
            active_notice_decision=active_notice_decision,
        ),
        "send_helper_returncode_zero": helper_result.returncode == 0,
        "send_performed_by_request_pack": False,
        "request_pack_authorizes_discord": False,
        "discord_send_authorized": False,
        "current_turn_approval_recorded": False,
        "current_turn_scope_authorized": False,
        "standing_launch_authority_recorded": standing_authority,
        "standing_launch_authority_satisfies_notice_scope": False,
        "standing_launch_authority_satisfies_dry_run_notice_preparation_scope": standing_authority,
        "standing_launch_authority_satisfies_confirmed_discord_send_scope": standing_authority,
        "standing_authority_satisfies_guarded_beta_notice_send_scope": standing_authority,
        "guarded_beta_notice_send_scope_satisfied_by_standing_authority": standing_authority,
        "guarded_discord_send_scope_satisfied": standing_authority,
        "standing_authority_authorizes_discord_send": standing_authority,
        "standing_authority_authorizes_runtime_evidence": False,
        "standing_authority_authorizes_marker_env_changes": False,
        "standing_authority_authorizes_server_restart": False,
        "confirmed_send_requires_separate_explicit_discord_send_approval": not standing_authority,
        "notice_action_covered_by_standing_launch_authority": standing_authority,
        "notice_action_counts_as_approved_runtime_evidence": False,
        "notice_action_counts_as_sdk_progress": False,
        "notice_action_counts_toward_sdk": False,
        "notice_action_counts_toward_p0_dependency_chain": False,
        "confirmed_send_authorizes_activation": False,
        "confirmed_send_authorizes_runtime_capture": False,
        "confirmed_send_authorizes_server_operations": False,
        "configured_send_path": "discord_bot_channel",
        "operational_message_workflow": "single_active_bot_notice",
        **discord_beta_notice_operational_boundary("beta_notice_report"),
        "channel": BETA_TEST_CHANNEL,
        "bot_channel_id": BETA_TEST_BOT_CHANNEL_ID,
        "expected_channel_id": BETA_TEST_BOT_CHANNEL_ID,
        "bot_channel_env_var": "OBELISK_DISCORD_BETA_CHANNEL_ID",
        "bot_channel_required_for_real_send": True,
        "single_operational_message_required": True,
        "active_notice_state_required_for_beta_controls": True,
        "single_editable_notice_required": True,
        "single_editable_embed_required": True,
        "with_beta_controls_required": True,
        "update_active_notice_required": True,
        "new_message_only_when_active_notice_state_missing": True,
        "existing_active_notice_updates_in_place": True,
        "button_interaction_response_mode": "ephemeral_ack_and_local_event_write",
        "button_interactions_ephemeral_ack_only": True,
        "button_interactions_create_channel_messages": False,
        "button_interactions_create_followup_messages": False,
        "button_interactions_update_operational_message": False,
        "button_events_claim_evidence": False,
        "button_events_claim_progress": False,
        "button_events_claim_readiness": False,
        "status_summary_response_mode": BETA_STATUS_SUMMARY_RESPONSE_MODE,
        "status_summary_creates_channel_message": False,
        "status_summary_updates_operational_message": False,
        "status_summary_creates_event": False,
        "status_summary_claims_evidence": False,
        "status_summary_claims_progress": False,
        "status_summary_claims_readiness": False,
        "embed_claims_evidence": False,
        "embed_claims_progress": False,
        "embed_claims_readiness": False,
        "webhook_deprecated": True,
        "webhook_real_send_allowed": False,
        "webhook_fail_closed_for_real_sends": True,
        "webhook_fallback_allowed": False,
        "default_sends_discord": False,
        "default_touches_ark": False,
        "default_reads_live_logs": False,
        "default_edits_markers_or_env": False,
        "dry_run_sends_discord": False,
        "dry_run_touches_ark": False,
        "counts_as_readiness": False,
        "readiness_claim_allowed": False,
        "progress_claim_allowed": False,
        "preparation_counts_as_readiness": False,
        "preparation_counts_as_progress": False,
        "sidecar_non_evidence_flags": SIDECAR_NON_EVIDENCE_FLAGS,
        "standing_authority_non_progress_boundary": standing_authority_non_progress_boundary(
            standing=standing_authority,
            scope="beta_notice_report",
        ),
        "non_authorization": NON_AUTHORIZATION,
        **report_sendability_flags(sendability),
        **FALSE_FLAGS,
    }
    if mode == "confirmed_send":
        report["discord_sent"] = completed
    write_notice_action_artifact(report, artifact_path)
    if args.json or dry_run or mode == "no_send":
        print(json.dumps(report, indent=2, sort_keys=True))
    elif helper_result.returncode == 0:
        print("player_principal_lifecycle_beta_notice_sent=true")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
