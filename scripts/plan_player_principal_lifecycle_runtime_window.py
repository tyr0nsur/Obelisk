#!/usr/bin/env python3
"""Plan an offline player-principal runtime evidence window command sequence.

This helper is intentionally offline. It calculates a fresh bounded request
window and emits the exact preactivation commands that prepare/check/dry-run the
beta notice and route-gate the window. It does not write files, touch ARK
servers, read live logs, send Discord, or claim SDK readiness.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import protected_paths
from player_principal_commit_validation import is_reviewed_obelisk_commit
from prepare_player_principal_lifecycle_window_request import (
    APPROVED_BETA_NOTICE_PATH,
    EXPECTED_BINARY_SHA256,
    HANDLE_NEW_PLAYER_FUNCTION,
    MAX_APPROVED_WINDOW_SECONDS,
    MAX_REQUEST_PREPARATION_LEAD_SECONDS,
    MIN_APPROVED_WINDOW_SECONDS,
    RUN_ID_SUFFIX,
    SESSION_START_REJECTED_REQUIRED_ARGUMENTS,
    SESSION_START_REJECTED_REQUIRED_CALL,
    SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS,
    SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES,
    SESSION_START_REJECTED_REQUIRED_FUNCTION,
)


SCHEMA = "obelisk.player-principal-lifecycle-runtime-window-plan.v1"
CURRENT_WINDOW_WORKFLOW_SCHEMA = "obelisk.player-principal-lifecycle-runtime-window-current-workflow.v1"
TWO_SERVER_CAP_SCHEMA = "obelisk.player-principal-lifecycle-two-server-cap.v1"
LIFECYCLE_ROLE_OBJECTIVES_SCHEMA = (
    "obelisk.player-principal-lifecycle-missing-role-objectives.v1"
)
RECOMMENDED_NOTICE_TEXT_SCHEMA = (
    "obelisk.player-principal-lifecycle-redacted-recommended-notice-text.v1"
)
FRESH_RETRY_AFTER_CLOSED_NON_EVIDENCE_WINDOW_SCHEMA = (
    "obelisk.player-principal-lifecycle-fresh-retry-after-closed-non-evidence-window.v1"
)
ACTIVE_PLAYER_NO_ACCEPTED_EVENTS_SCHEMA = (
    "obelisk.player-principal-lifecycle-active-player-no-accepted-events-window-policy.v1"
)
NEXT_ACTION_POLICY_SCHEMA = (
    "obelisk.player-principal-lifecycle-runtime-window-next-action-policy.v1"
)
COPIED_LOG_ROUTE_CONTRACT_SCHEMA = (
    "obelisk.player-principal-lifecycle-copied-log-route-contract.v1"
)
DEFAULT_OUTPUT_ROOT = Path("/servidor/ark/workspace-offline/live-validation-logs")
DEFAULT_REVIEWED_BY = "lead"
DEFAULT_STANDING_AUTHORITY_REFERENCE = "operator-2026-06-06-standing-launch-authority"
DEFAULT_REVIEW_NOTE = "standing-authority consume-only runtime lifecycle evidence"
BETA_TEST_CHANNEL = "beta-test"
BETA_TEST_BOT_CHANNEL_ID = "1513238083741683934"
BETA_TEST_BOT_CHANNEL_ENV = "OBELISK_DISCORD_BETA_CHANNEL_ID"
BETA_NOTICE_TRANSPORT_SCHEMA = "obelisk.player-principal-lifecycle-beta-notice-bot-transport.v1"
BETA_NOTICE_REQUIRED_HELPER_ARGS = (
    "--send-beta-notice",
    "--with-beta-controls",
    "--update-active-notice",
)
MIN_RUNTIME_WINDOW_LEAD_SECONDS = 300
UTC_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
SAFE_MAP_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
STRICT_COPIED_BOOL_TRIPLET_TEXT = "HandleNewPlayer(1,1) -> CheckJoinInProgress(1,0) -> matched OnLogout"
CLOSURE_COMPATIBLE_RUN_ID_PATTERN = r"^[0-9]{8}T[0-9]{6}Z-player-principal-lifecycle$"
REQUIRED_LIFECYCLE_EVENT_ROLES = (
    "session_start",
    "session_start_rejected",
    "session_end",
)
PREVIOUS_THEISLAND_NON_EVIDENCE_RUN_ID_STEM = "20260607T134929Z"
PREVIOUS_THEISLAND_NON_EVIDENCE_RUN_ID = (
    PREVIOUS_THEISLAND_NON_EVIDENCE_RUN_ID_STEM + RUN_ID_SUFFIX
)
PREVIOUS_THEISLAND_NON_EVIDENCE_TARGET = {
    "instance": "arkserver2",
    "map": "TheIsland",
}
PREVIOUS_THEISLAND_NON_EVIDENCE_TARGET_KEY = "arkserver2:TheIsland:27016"
PREVIOUS_THEISLAND_NON_EVIDENCE_START_UTC = "2026-06-07T13:49:29Z"
PREVIOUS_THEISLAND_NON_EVIDENCE_END_UTC = "2026-06-07T15:49:29Z"
FRESH_WINDOW_REQUIRED_SIBLING_SET = (
    "window-request.json",
    "observer-window.env",
    "operator-approval-request.md",
    "operator-approval-receipt.json",
    "preflight-pre.json",
    "preflight-post.json",
    "window-manifest.env",
    "Obelisk.log",
    "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
)
FRESH_WINDOW_NOTICE_SIDECAR_FILENAMES = (
    "beta-notice.dry-run.sidecar.json",
    "beta-notice.confirmed.sidecar.json",
)
RUNTIME_OBSERVER_ANALYZER = "scripts/analyze_runtime_observer_log.py"
APPROVED_RUNTIME_MANIFEST_BUILDER = (
    "scripts/build_player_identity_runtime_principal_lifecycle_approved_manifest.py"
)
APPROVED_RUNTIME_EVIDENCE_BUNDLE_BUILDER = (
    "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py"
)
APPROVED_RUNTIME_EVIDENCE_CHECKER = (
    "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
)
STRICT_LIFECYCLE_TRIPLET_CANDIDATE_SUMMARY_STEP_ID = (
    "strict_lifecycle_triplet_candidate_summary"
)
STRICT_LIFECYCLE_TRIPLET_CANDIDATE_SUMMARY_JSON_PATH = (
    "modules.player_principal_lifecycle.strict_lifecycle_triplet_candidate_summary"
)
COPIED_LOG_ROUTE_STEP_IDS = (
    "analyze_runtime_observer_log",
    STRICT_LIFECYCLE_TRIPLET_CANDIDATE_SUMMARY_STEP_ID,
    "bundle_preflight",
    "approved_runtime_evidence_checker",
)
NON_CLAIM_FLAGS: dict[str, bool] = {
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


def closure_compatible_evidence_root(run_id: str, evidence_dir: Path) -> dict[str, Any]:
    return {
        "schema": "obelisk.player-principal-lifecycle-closure-compatible-evidence-root.v1",
        "run_id": run_id,
        "evidence_dir": str(evidence_dir),
        "required_run_id_pattern": CLOSURE_COMPATIBLE_RUN_ID_PATTERN,
        "run_id_matches_closure_request": re.fullmatch(CLOSURE_COMPATIBLE_RUN_ID_PATTERN, run_id)
        is not None,
        "passive_monitor_root_accepted_by_closure_request": False,
        "passive_monitor_roots_must_not_be_used_as_closure_evidence_dir": True,
        "passive_monitor_context_must_be_copied_or_replaced_before_evidence_closure": True,
        "copy_or_stage_action_authorized_by_this_plan": False,
        "server_operations_authorized": False,
        "workspace_writes_authorized": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "non_authorization": (
            "run-id shape guidance only; passive monitor roots are diagnostic context and "
            "must not be submitted to closure as lifecycle evidence"
        ),
    }


def copied_bool_triplet_requirement() -> dict[str, Any]:
    return {
        "requirement": STRICT_COPIED_BOOL_TRIPLET_TEXT,
        "source": "future_player_backed_copied_obelisk_log_only",
        "required_sequence": [
            {"event": "HandleNewPlayer", "copied_bool_values": [1, 1]},
            {"event": "CheckJoinInProgress", "copied_bool_values": [1, 0]},
            {"event": "OnLogout", "correlation_status": "matched"},
        ],
        "requires_same_player_correlation": True,
        "requires_copied_log_bundle_checker_acceptance": True,
        "future_player_backed_required": True,
        "standing_launch_authority_satisfies_requirement": False,
        "plan_or_request_pack_satisfies_requirement": False,
        "beta_notice_satisfies_requirement": False,
        "passive_wait_satisfies_requirement": False,
        "public_query_satisfies_requirement": False,
        "start_end_only_satisfies_requirement": False,
        "clears_approved_runtime_evidence_missing": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_progress": False,
        "counts_as_runtime_readiness": False,
    }


def copied_log_route_contract() -> dict[str, Any]:
    return {
        "schema": COPIED_LOG_ROUTE_CONTRACT_SCHEMA,
        "ordered_step_ids": list(COPIED_LOG_ROUTE_STEP_IDS),
        "route": (
            "copied Obelisk.log -> analyzer -> strict_lifecycle_triplet_candidate_summary "
            "-> bundle preflight -> approved-evidence checker"
        ),
        "copied_log_source": "offline_copied_obelisk_log_only",
        "analyzer": RUNTIME_OBSERVER_ANALYZER,
        "strict_lifecycle_triplet_candidate_summary_json_path": (
            STRICT_LIFECYCLE_TRIPLET_CANDIDATE_SUMMARY_JSON_PATH
        ),
        "bundle_preflight": APPROVED_RUNTIME_EVIDENCE_BUNDLE_BUILDER,
        "approved_evidence_checker": APPROVED_RUNTIME_EVIDENCE_CHECKER,
        "checker_acceptance_required_before_evidence_state_change": True,
        "all_prior_outputs_non_authorizing_and_non_evidence": True,
        "approved_evidence_checker_accepted_by_this_plan": False,
        "authorized_by_this_plan": False,
        "server_operations_authorized": False,
        "runtime_capture_authorized": False,
        "live_log_reads_authorized": False,
        "marker_env_changes_authorized": False,
        "discord_authorized": False,
        "restart_recommended": False,
        "raw_player_text_allowed": False,
        "raw_player_identity_allowed": False,
        "raw_player_text_or_identity_allowed": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "clears_approved_runtime_evidence_missing": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "non_authorization": (
            "copied-log route planning is offline follow-up guidance only; analyzer "
            "summaries, strict triplet candidate summaries, and bundle preflight outputs "
            "remain non-authorizing and non-evidence unless the approved-evidence checker "
            "is run later and accepts the approved manifest"
        ),
    }


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
        "server_restart_authorized_by_plan": False,
        "message": (
            "Preserve the current two-server cap: never keep three ARK servers running; "
            "confirm one instance is off before starting another."
        ),
    }


def beta_notice_transport_policy() -> dict[str, Any]:
    return {
        "schema": BETA_NOTICE_TRANSPORT_SCHEMA,
        "default_transport": "discord_bot_channel",
        "channel": BETA_TEST_CHANNEL,
        "bot_channel_id": BETA_TEST_BOT_CHANNEL_ID,
        "bot_channel_env_var": BETA_TEST_BOT_CHANNEL_ENV,
        "bot_channel_required_for_real_send": True,
        "required_helper_args": list(BETA_NOTICE_REQUIRED_HELPER_ARGS),
        "with_beta_controls_required": True,
        "update_active_notice_required": True,
        "single_active_bot_notice_required": True,
        "active_notice_state_required_for_beta_controls": True,
        "active_notice_state_counts_as_confirmed_notice": False,
        "active_notice_state_counts_as_approved_runtime_evidence": False,
        "webhook_notice_path_allowed": False,
        "webhook_fallback_allowed": False,
        "authorizes_discord_send": False,
        "authorizes_server_operations": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
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
            "objective": "capture player-backed session_start from copied Obelisk.log",
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
            "objective": "capture exact CheckJoinInProgress(1,0) rejection from copied Obelisk.log",
        },
        {
            "objective_id": "session_end",
            "role": "session_end",
            "required_function": "OnLogout",
            "correlation_status": "matched",
            "objective": "capture matched session_end for the same player session",
        },
    ]
    return {
        "schema": LIFECYCLE_ROLE_OBJECTIVES_SCHEMA,
        "required_lifecycle_event_roles": list(REQUIRED_LIFECYCLE_EVENT_ROLES),
        "missing_lifecycle_event_roles": roles,
        "next_missing_lifecycle_event_role": roles[0] if roles else None,
        "objective_ids": [item["objective_id"] for item in objectives],
        "objectives": objectives,
        "requires_copied_log_bundle_checker_acceptance": True,
        "standing_authority_satisfies_missing_roles": False,
        "plan_or_request_pack_satisfies_missing_roles": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_toward_sdk": False,
    }


def recommended_notice_text(
    *,
    instance: str,
    map_name: str,
    start_utc: str,
    end_utc: str,
) -> dict[str, Any]:
    objective_text = "session_start, CheckJoinInProgress(1,0), session_end"
    return {
        "schema": RECOMMENDED_NOTICE_TEXT_SCHEMA,
        "discord_channel": BETA_TEST_CHANNEL,
        "discord_bot_channel_id": BETA_TEST_BOT_CHANNEL_ID,
        "discord_bot_channel_env_var": BETA_TEST_BOT_CHANNEL_ENV,
        "bot_first_notice_path": True,
        "webhook_notice_path_allowed": False,
        "single_active_bot_notice_required": True,
        "active_notice_update_required": True,
        "active_notice_state_counts_as_confirmed_notice": False,
        "discord_content": "@everyone",
        "recommended_discord_text_redacted": (
            f"Obelisk beta window for {map_name} on {instance} "
            f"({start_utc} to {end_utc} UTC). Please join, let the session settle, "
            f"and leave once when asked so we can validate {objective_text}. Do not "
            "post player names, chat, Steam IDs, private credentials."
        ),
        "recommended_rcon_broadcast_text_redacted": (
            "Obelisk beta validation window starting now. Please finish current action, "
            "join/leave once if participating, and avoid sharing names, chat, IDs or private credentials."
        ),
        "recommended_text_already_redacted": True,
        "raw_player_text_allowed": False,
        "raw_player_identity_allowed": False,
        "raw_player_text_or_identity_allowed": False,
        "secret_or_webhook_output_allowed": False,
        "bot_notice_counts_as_approved_runtime_evidence": False,
        "beta_notice_transport_policy": beta_notice_transport_policy(),
        "two_server_cap_policy": two_server_cap_policy(),
        "lifecycle_role_objectives": lifecycle_role_objectives(),
        "counts_as_approved_runtime_evidence": False,
        "counts_toward_sdk": False,
    }


def active_player_no_accepted_events_policy(
    *,
    target: dict[str, Any],
    observed: bool,
    requested_restart_expectation: str,
    effective_restart_expectation: str,
    concrete_deploy_or_gate_change: str | None,
) -> dict[str, Any]:
    concrete_change_present = concrete_deploy_or_gate_change is not None
    status = (
        "player_present_observer_enabled_no_accepted_events_likely_drift"
        if observed
        else "state_not_observed_by_offline_plan"
    )
    return {
        "schema": ACTIVE_PLAYER_NO_ACCEPTED_EVENTS_SCHEMA,
        "status": status,
        "classification": (
            "source_bound_drift_blocker_non_evidence"
            if observed
            else "conditional_guidance"
        ),
        "target": target,
        "state_observed_from_supplied_snapshot": observed,
        "source_bound_blocker": observed,
        "source_bound_blocker_kind": (
            "active_player_observer_enabled_no_accepted_lifecycle_events"
            if observed
            else None
        ),
        "route_to_drift_or_source_bound_blocker": observed,
        "current_route_blocker": (
            "source_bound_active_player_no_accepted_lifecycle_events"
            if observed
            else None
        ),
        "exact_state_preconditions": [
            "exact_target_matches_snapshot",
            "player_count_on_exact_target_greater_than_zero",
            "player_principal_lifecycle_observer_enabled_on_exact_target",
            "accepted_lifecycle_event_count_on_exact_target_equals_zero",
            "no_accepted_session_start_session_start_rejected_or_session_end_for_target",
        ],
        "players_present": True if observed else None,
        "observer_enabled_on_exact_target": True if observed else None,
        "accepted_lifecycle_event_roles": [] if observed else None,
        "accepted_lifecycle_event_count": 0 if observed else None,
        "likely_drift": observed,
        "requested_restart_expectation": requested_restart_expectation,
        "effective_restart_expectation": effective_restart_expectation,
        "restart_expectation_changed_to_none": (
            observed
            and requested_restart_expectation == "restart"
            and effective_restart_expectation == "none"
        ),
        "concrete_deploy_or_gate_change": concrete_deploy_or_gate_change,
        "concrete_deploy_or_gate_change_present": concrete_change_present,
        "restart_requires_concrete_deploy_or_gate_change": True,
        "restart_blocked_without_concrete_deploy_or_gate_change": observed
        and not concrete_change_present,
        "restart_recommended": False if observed and not concrete_change_present else requested_restart_expectation == "restart",
        "start_or_restart_recommended": False
        if observed and not concrete_change_present
        else requested_restart_expectation in {"start", "restart"},
        "server_restart_authorized_by_plan": False,
        "server_operations_authorized": False,
        "runtime_capture_authorized": False,
        "blind_wait_recommended": False,
        "wait_or_restart_or_logout_instruction_allowed": False,
        "logout_or_reconnect_instruction_allowed": False,
        "player_logout_instruction_allowed_now": False,
        "standing_authority_metadata_only": True,
        "standing_authority_authorizes_server_restart": False,
        "standing_authority_authorizes_marker_env_changes": False,
        "standing_authority_authorizes_runtime_evidence": False,
        "next_status_input_needed": (
            "source-bound drift resolution or a same-window accepted lifecycle "
            "event triplet after the drift/source blocker is cleared; otherwise "
            "classify the window as non-evidence"
            if observed
            else "fresh checked source-bound lifecycle evidence window"
        ),
        "two_server_cap_policy": two_server_cap_policy(),
        "next_steps": [
            {
                "id": "preserve_two_server_cap_and_do_not_restart_for_state_only",
                "action": (
                    "Keep the current two-server cap and do not restart only because a "
                    "player is present while the observer has no accepted lifecycle events."
                ),
                "blocked_until": [
                    "concrete_deploy_or_gate_change_named",
                    "separate_current_scope_for_restart_if_restart_is_needed",
                ],
                "restart_recommended": False,
                "server_operations_authorized": False,
            },
            {
                "id": "defer_until_drift_fix_or_gate_change",
                "action": (
                    "Defer another player-backed validation until the lifecycle drift is "
                    "fixed offline or a concrete deploy/gate change is named."
                ),
                "blocked_until": [
                    "drift_fix_identified",
                    "fresh_checked_request_pack_after_fix",
                    "approved_window_preconditions_rechecked",
                ],
                "server_operations_authorized": False,
            },
            {
                "id": "wait_only_after_exact_preconditions",
                "action": (
                    "Wait only inside a fresh approved window after exact target binding, "
                    "observer gate health, notice sequence, and activation preconditions "
                    "are all checked."
                ),
                "preconditions": [
                    "fresh_current_window_request",
                    "confirmed_notice_report_consumed",
                    "activation_preconditions_ready",
                    "observer_enabled_on_exact_target",
                    "no_lifecycle_drift_blocker",
                ],
                "wait_authorized_by_plan": False,
                "server_operations_authorized": False,
            },
            {
                "id": "ask_reconnect_or_logout_only_after_observer_gate",
                "action": (
                    "Ask a tester to reconnect or logout only after the observer accepts "
                    "the required same-window lifecycle gate for the exact target."
                ),
                "preconditions": [
                    "fresh_current_window_request",
                    "player_notice_completed",
                    "player_still_present_on_exact_target",
                    "accepted_session_start_or_exact_CheckJoinInProgress_1_0_seen_for_same_session",
                    "no_drift_blocker_pending",
                ],
                "ask_reconnect_or_logout_now": False,
                "server_operations_authorized": False,
            },
        ],
        "approved_runtime_evidence_present": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_as_progress": False,
        "counts_as_p0_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "non_authorization": (
            "active-player/no-accepted-events planning is offline drift metadata only; "
            "it does not authorize Discord, live ops, marker/env changes, restarts, live "
            "log reads, runtime capture, evidence acceptance, readiness, progress, or publication"
        ),
    }


def runtime_window_next_action_policy(
    *,
    target: dict[str, Any],
    requested_restart_expectation: str,
    effective_restart_expectation: str,
    source_discrepancy: str,
    session_end_only_no_start: bool,
    active_player_no_accepted_events: bool,
    concrete_deploy_or_gate_change: str | None,
) -> dict[str, Any]:
    rcon_present_query_zero = source_discrepancy == "rcon_present_query_zero"
    query_present_rcon_zero = source_discrepancy == "query_present_rcon_zero"
    any_discrepancy = source_discrepancy != "none"
    players_present_or_ambiguous = (
        rcon_present_query_zero
        or query_present_rcon_zero
        or active_player_no_accepted_events
    )
    concrete_change_present = concrete_deploy_or_gate_change is not None
    if rcon_present_query_zero:
        next_action_id = "keep_waiting_rcon_present_query_zero"
        lead_message = (
            "Keep waiting and do not restart blindly: redacted RCON ListPlayers reports "
            "presence while ASE query reports zero. Treat the discrepancy as non-evidence "
            "and ask the lead to keep the window open or prepare a clean window after players clear."
        )
    elif active_player_no_accepted_events:
        next_action_id = "broadcast_then_prepare_clean_window_after_drift"
        lead_message = (
            "Tell lead the player-present/no-accepted-events state is source-bound drift metadata. "
            "Do not restart unless a concrete deploy or gate change is named; prepare a clean "
            "window after the blocker is cleared."
        )
    elif session_end_only_no_start:
        next_action_id = "prepare_clean_window_session_end_only_no_start"
        lead_message = (
            "Prepare a clean future window: a session_end-only/no-start signal is non-evidence "
            "and should not trigger a restart or close the lifecycle objective."
        )
    elif requested_restart_expectation == "restart":
        next_action_id = "broadcast_before_clean_window"
        lead_message = (
            "Prepare a clean window and broadcast before any separately approved restart; "
            "if players remain connected, reschedule instead of forcing a blind restart."
        )
    else:
        next_action_id = "prepare_clean_window"
        lead_message = "Prepare the next clean checked runtime window with no restart implied by this plan."

    broadcast_recommended = (
        active_player_no_accepted_events
        or (
            requested_restart_expectation == "restart"
            and not rcon_present_query_zero
            and not session_end_only_no_start
        )
    )
    return {
        "schema": NEXT_ACTION_POLICY_SCHEMA,
        "target": target,
        "source_discrepancy": source_discrepancy,
        "source_discrepancy_detected": any_discrepancy,
        "rcon_present_query_zero_discrepancy": rcon_present_query_zero,
        "query_present_rcon_zero_discrepancy": query_present_rcon_zero,
        "session_end_only_no_start": session_end_only_no_start,
        "active_player_no_accepted_events": active_player_no_accepted_events,
        "players_present_or_ambiguous": players_present_or_ambiguous,
        "requested_restart_expectation": requested_restart_expectation,
        "effective_restart_expectation": effective_restart_expectation,
        "concrete_deploy_or_gate_change": concrete_deploy_or_gate_change,
        "concrete_deploy_or_gate_change_present": concrete_change_present,
        "next_action_id": next_action_id,
        "lead_message": lead_message,
        "keep_waiting_recommended": rcon_present_query_zero,
        "broadcast_recommended": broadcast_recommended,
        "prepare_clean_window_recommended": (
            session_end_only_no_start
            or active_player_no_accepted_events
            or not rcon_present_query_zero
        ),
        "clean_window_required_before_next_evidence_attempt": (
            session_end_only_no_start or active_player_no_accepted_events
        ),
        "blind_restart_allowed": False,
        "blind_restart_blocked": True,
        "restart_recommended": False
        if players_present_or_ambiguous and not concrete_change_present
        else effective_restart_expectation == "restart",
        "broadcast_or_reschedule_before_restart": requested_restart_expectation == "restart",
        "server_operations_authorized": False,
        "discord_send_authorized": False,
        "runtime_capture_authorized": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "next_action_order": [
            "keep_waiting_if_rcon_present_query_zero",
            "broadcast_only_with_separate_approval_if_players_need_notice",
            "prepare_clean_future_window_after_session_end_only_or_drift",
        ],
    }


def non_claim_flags() -> dict[str, bool]:
    return dict(NON_CLAIM_FLAGS)


def parse_utc(value: str, label: str) -> datetime:
    if not UTC_RE.fullmatch(value):
        raise SystemExit(f"{label} must use YYYY-MM-DDThh:mm:ssZ: {value}")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def window_lifecycle_state(
    *,
    now: datetime,
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    if now < start:
        state = "pending"
    elif now < end:
        state = "active"
    else:
        state = "expired"
    return {
        "state": state,
        "active": state == "active",
        "expired": state == "expired",
        "closed": state == "expired",
        "start_utc": format_utc(start),
        "end_utc": format_utc(end),
        "checked_at_utc": format_utc(now),
    }


def retry_target_key(target: dict[str, Any]) -> str:
    if target == PREVIOUS_THEISLAND_NON_EVIDENCE_TARGET:
        return PREVIOUS_THEISLAND_NON_EVIDENCE_TARGET_KEY
    instance = str(target.get("instance") or "unknown")
    map_name = str(target.get("map") or "unknown")
    return f"{instance}:{map_name}"


def sibling_paths(evidence_dir: Path) -> dict[str, str]:
    return {
        item.replace("/", "_").replace(".", "_").replace("-", "_"): str(evidence_dir / item)
        for item in FRESH_WINDOW_REQUIRED_SIBLING_SET
    }


def notice_sidecar_paths(report_dir: Path) -> dict[str, str]:
    return {
        item.replace(".", "_").replace("-", "_"): str(report_dir / item)
        for item in FRESH_WINDOW_NOTICE_SIDECAR_FILENAMES
    }


def fresh_retry_after_closed_non_evidence_window(
    *,
    now: datetime,
    run_id: str,
    target: dict[str, Any],
    approved_window: dict[str, Any],
    evidence_dir: Path,
    report_dir: Path,
) -> dict[str, Any]:
    previous_start = parse_utc(PREVIOUS_THEISLAND_NON_EVIDENCE_START_UTC, "previous window start")
    previous_end = parse_utc(PREVIOUS_THEISLAND_NON_EVIDENCE_END_UTC, "previous window end")
    current_start = parse_utc(str(approved_window.get("start_utc")), "approved window start")
    current_end = parse_utc(str(approved_window.get("end_utc")), "approved window end")
    previous_state = window_lifecycle_state(
        now=now,
        start=previous_start,
        end=previous_end,
    )
    fresh_state = window_lifecycle_state(now=now, start=current_start, end=current_end)
    target_matches_previous = target == PREVIOUS_THEISLAND_NON_EVIDENCE_TARGET
    fresh_run_distinct = run_id != PREVIOUS_THEISLAND_NON_EVIDENCE_RUN_ID
    fresh_root_distinct = PREVIOUS_THEISLAND_NON_EVIDENCE_RUN_ID not in str(evidence_dir)
    fresh_sibling_set_distinct = fresh_run_distinct and fresh_root_distinct
    fresh_window_start_end_distinct = (
        approved_window.get("start_utc") != PREVIOUS_THEISLAND_NON_EVIDENCE_START_UTC
        and approved_window.get("end_utc") != PREVIOUS_THEISLAND_NON_EVIDENCE_END_UTC
    )
    retry_ready = (
        target_matches_previous
        and previous_state["expired"]
        and fresh_sibling_set_distinct
        and fresh_window_start_end_distinct
        and not fresh_state["expired"]
    )
    return {
        "schema": FRESH_RETRY_AFTER_CLOSED_NON_EVIDENCE_WINDOW_SCHEMA,
        "status": (
            "fresh_theisland_retry_prepared_after_expired_non_evidence_window"
            if retry_ready
            else "fresh_window_planned_no_closed_theisland_retry_promotion"
        ),
        "checked_at_utc": format_utc(now),
        "exact_target_required": True,
        "target_aliases_allowed": False,
        "target": target,
        "target_key": retry_target_key(target),
        "target_matches_previous_theisland_window": target_matches_previous,
        "previous_window": {
            "run_id_stem": PREVIOUS_THEISLAND_NON_EVIDENCE_RUN_ID_STEM,
            "run_id": PREVIOUS_THEISLAND_NON_EVIDENCE_RUN_ID,
            "target": dict(PREVIOUS_THEISLAND_NON_EVIDENCE_TARGET),
            "target_key": PREVIOUS_THEISLAND_NON_EVIDENCE_TARGET_KEY,
            "lifecycle_state": previous_state["state"],
            "active": previous_state["active"],
            "expired": previous_state["expired"],
            "closed": previous_state["closed"],
            "post_restart_closed_non_evidence_window": previous_state["expired"],
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_evidence": False,
            "clears_approved_runtime_evidence_missing": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "start_utc": previous_state["start_utc"],
            "end_utc": previous_state["end_utc"],
        },
        "fresh_window": {
            "run_id": run_id,
            "target": target,
            "target_key": retry_target_key(target),
            "lifecycle_state_at_plan_time": fresh_state["state"],
            "active_at_plan_time": fresh_state["active"],
            "expired_at_plan_time": fresh_state["expired"],
            "start_utc": fresh_state["start_utc"],
            "end_utc": fresh_state["end_utc"],
            "evidence_dir": str(evidence_dir),
            "report_dir": str(report_dir),
            "sibling_set_root": str(evidence_dir),
            "required_sibling_set": list(FRESH_WINDOW_REQUIRED_SIBLING_SET),
            "sibling_paths": sibling_paths(evidence_dir),
            "notice_sidecar_paths": notice_sidecar_paths(report_dir),
            "uses_own_sibling_set": fresh_sibling_set_distinct,
            "start_end_bound_to_fresh_run": fresh_window_start_end_distinct,
            "exact_target_bound": True,
            "previous_sibling_set_reuse_allowed": False,
            "previous_notice_sidecars_reuse_allowed": False,
            "previous_start_end_reuse_allowed": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
        },
        "fresh_retry_allowed_without_reusing_previous_window": retry_ready,
        "previous_window_preserved_as_non_evidence": True,
        "previous_window_reuse_allowed": False,
        "previous_sibling_set_reuse_allowed": False,
        "previous_notice_sidecars_reuse_allowed": False,
        "previous_start_end_reuse_allowed": False,
        "previous_run_counts_as_approved_runtime_evidence": False,
        "previous_run_counts_as_runtime_evidence": False,
        "previous_run_counts_as_sdk_progress": False,
        "fresh_window_counts_as_approved_runtime_evidence": False,
        "fresh_window_counts_as_runtime_evidence": False,
        "fresh_window_authorizes_runtime_work": False,
        "fresh_window_authorizes_discord_send": False,
        "fresh_window_authorizes_marker_env_changes": False,
        "fresh_window_authorizes_server_restart": False,
        "non_authorization": (
            "fresh retry metadata only; the expired 20260607T134929Z TheIsland window "
            "remains non-evidence, and the fresh window still requires its own checked "
            "sibling set, notice sidecars, exact target, and accepted copied-log bundle"
        ),
    }


def runtime_window_stale_prevention(
    *,
    now: datetime,
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    seconds_until_start = int((start - now).total_seconds())
    seconds_until_end = int((end - now).total_seconds())
    enough_lead = seconds_until_start >= MIN_RUNTIME_WINDOW_LEAD_SECONDS
    blockers: list[str] = []
    if start <= now:
        blockers.append("runtime_window_start_already_passed_prepare_fresh_window")
    if end <= now:
        blockers.append("runtime_window_end_already_passed_prepare_fresh_window")
    if start > now and not enough_lead:
        blockers.append("runtime_window_insufficient_future_lead_for_notice_and_activation")
    return {
        "schema": "obelisk.player-principal-lifecycle-runtime-window-stale-prevention.v1",
        "checked_at_utc": format_utc(now),
        "start_utc": format_utc(start),
        "end_utc": format_utc(end),
        "seconds_until_start": seconds_until_start,
        "seconds_until_end": seconds_until_end,
        "minimum_required_lead_seconds": MIN_RUNTIME_WINDOW_LEAD_SECONDS,
        "enough_future_lead_time": enough_lead,
        "window_start_in_future": start > now,
        "window_end_in_future": end > now,
        "stale_request_window": bool(start <= now or end <= now),
        "request_window_stale_or_too_late": bool(blockers),
        "blockers": blockers,
        "beta_notice_dry_run_required_before_activation": True,
        "confirmed_beta_notice_required_before_activation": True,
        "confirmed_send_must_complete_before_window_start": True,
        "activation_preconditions_required_before_activation_or_restart": True,
        "activation_or_restart_from_stale_request_allowed": False,
        "monitor_or_restart_activation_after_window_start_allowed": False,
        "fresh_current_window_required_when_blocked": bool(blockers),
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "non_authorization": (
            "freshness metadata only; it does not authorize Discord, marker/env changes, "
            "server operations, monitor/restart activation, runtime capture, approved "
            "runtime evidence, readiness, or progress"
        ),
    }


def run_id_for_start(start: datetime) -> str:
    return start.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + RUN_ID_SUFFIX


def git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"could not resolve current git commit: {result.stderr.strip()}")
    return result.stdout.strip()


def validate_safe_token(value: str, label: str, pattern: re.Pattern[str] = SAFE_TOKEN_RE) -> str:
    if not pattern.fullmatch(value):
        raise SystemExit(f"{label} contains unsafe characters: {value}")
    return value


def validate_output_root(path: Path) -> Path:
    expanded = path.expanduser()
    status = protected_paths.protected_path_status(expanded)
    if status.protected:
        raise SystemExit(
            "--output-root must be outside /servidor/ark or under "
            f"/servidor/ark/workspace-offline: {status.resolved}"
        )
    return status.resolved


def shell_command(argv: list[str], *, env: dict[str, str] | None = None, redirect: Path | None = None) -> str:
    parts: list[str] = []
    if env:
        parts.extend(f"{key}={shlex.quote(value)}" for key, value in sorted(env.items()))
    parts.extend(shlex.quote(part) for part in argv)
    command = " ".join(parts)
    if redirect is not None:
        command = f"{command} > {shlex.quote(str(redirect))}"
    return command


def command_entry(
    step_id: str,
    title: str,
    argv: list[str],
    *,
    env: dict[str, str] | None = None,
    redirect: Path | None = None,
    note: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry = {
        "id": step_id,
        "title": title,
        "argv": argv,
        "env": env or {},
        "redirect_stdout": str(redirect) if redirect is not None else None,
        "shell": shell_command(argv, env=env, redirect=redirect),
        "note": note,
        **non_claim_flags(),
        "strict_copied_bool_triplet_requirement": copied_bool_triplet_requirement(),
        "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
        "two_server_cap_policy": two_server_cap_policy(),
    }
    if metadata is not None:
        entry["metadata"] = {**non_claim_flags(), **metadata}
    return entry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Emit a fresh offline command plan for a standing-authorized "
            "player-principal lifecycle runtime evidence window."
        )
    )
    parser.add_argument("--instance", required=True, help="Exact ARK/Obelisk instance id, e.g. arkserver3.")
    parser.add_argument("--map", dest="map_name", required=True, help="Exact ARK map, e.g. Genesis2.")
    parser.add_argument(
        "--start-delay-minutes",
        type=int,
        default=5,
        help="Minutes from now until the requested window starts; must be 5-60.",
    )
    parser.add_argument(
        "--duration-minutes",
        type=int,
        default=15,
        help="Requested window duration; minimum is 15 minutes and maximum is 120 minutes.",
    )
    parser.add_argument(
        "--restart-expectation",
        choices=("none", "start", "restart"),
        default="none",
        help="Expected server lifecycle action for the evidence window.",
    )
    parser.add_argument(
        "--user-policy",
        choices=("no_regular_users", "operator_approved_beta_users"),
        default="operator_approved_beta_users",
    )
    parser.add_argument(
        "--notice-path",
        default=APPROVED_BETA_NOTICE_PATH,
        help="Notice path label. Beta-user windows must use discord-beta-testers.",
    )
    parser.add_argument("--rollback-owner", default="operator")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--obelisk-commit", help="Reviewed Obelisk git commit; defaults to HEAD.")
    parser.add_argument("--binary-sha256", default=EXPECTED_BINARY_SHA256)
    parser.add_argument("--reviewed-by", default=DEFAULT_REVIEWED_BY)
    parser.add_argument("--review-note", default=DEFAULT_REVIEW_NOTE)
    parser.add_argument(
        "--diagnostic-candidates",
        action="store_true",
        help="Pass candidate-only diagnostic metadata into the request pack; non-authorizing and non-evidence.",
    )
    parser.add_argument(
        "--active-player-no-accepted-events",
        action="store_true",
        help=(
            "Record the offline redacted state where a player is present, the lifecycle "
            "observer is enabled, and no lifecycle events were accepted; plans no restart "
            "unless --concrete-deploy-or-gate-change is supplied."
        ),
    )
    parser.add_argument(
        "--presence-source-discrepancy",
        choices=("none", "rcon_present_query_zero", "query_present_rcon_zero"),
        default="none",
        help=(
            "Offline redacted source comparison from passive monitor context; metadata "
            "only and never evidence or operation authority."
        ),
    )
    parser.add_argument(
        "--session-end-only-no-start",
        action="store_true",
        help=(
            "Record that the passive observer saw accepted session_end without an "
            "accepted session_start for the same window; metadata only."
        ),
    )
    parser.add_argument(
        "--concrete-deploy-or-gate-change",
        help=(
            "Safe label for a concrete offline deploy or gate change that justifies keeping "
            "a requested start/restart expectation in the active-player/no-accepted-events state."
        ),
    )
    parser.add_argument(
        "--standing-launch-authority-reference",
        default=DEFAULT_STANDING_AUTHORITY_REFERENCE,
    )
    parser.add_argument(
        "--now-utc",
        help="Testing override for current UTC time, YYYY-MM-DDThh:mm:ssZ.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    return parser.parse_args()


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    instance = validate_safe_token(args.instance, "--instance")
    map_name = validate_safe_token(args.map_name, "--map", SAFE_MAP_RE)
    rollback_owner = validate_safe_token(args.rollback_owner, "--rollback-owner")
    reviewed_by = validate_safe_token(args.reviewed_by, "--reviewed-by")
    authority_ref = validate_safe_token(
        args.standing_launch_authority_reference,
        "--standing-launch-authority-reference",
    )
    concrete_change = getattr(args, "concrete_deploy_or_gate_change", None)
    if concrete_change is not None:
        concrete_change = validate_safe_token(concrete_change, "--concrete-deploy-or-gate-change")
    active_player_no_accepted_events = bool(
        getattr(args, "active_player_no_accepted_events", False)
    )
    effective_restart_expectation = (
        "none"
        if (
            active_player_no_accepted_events
            and concrete_change is None
            and args.restart_expectation in {"start", "restart"}
        )
        else args.restart_expectation
    )

    if args.start_delay_minutes * 60 < MIN_RUNTIME_WINDOW_LEAD_SECONDS:
        raise SystemExit(
            "--start-delay-minutes must be at least 5 so beta notice dry-run and "
            "confirmed-send can complete before activation/restart"
        )
    if args.start_delay_minutes * 60 > MAX_REQUEST_PREPARATION_LEAD_SECONDS:
        raise SystemExit("--start-delay-minutes must be within 1 hour")
    if args.duration_minutes * 60 < MIN_APPROVED_WINDOW_SECONDS:
        raise SystemExit("--duration-minutes must be at least 15 minutes")
    if args.duration_minutes * 60 > MAX_APPROVED_WINDOW_SECONDS:
        raise SystemExit("--duration-minutes must not exceed 120 minutes")
    if args.user_policy == "operator_approved_beta_users" and args.notice_path != APPROVED_BETA_NOTICE_PATH:
        raise SystemExit(f"--notice-path must be {APPROVED_BETA_NOTICE_PATH} for beta-user windows")
    if args.user_policy == "no_regular_users" and args.notice_path != "not_applicable":
        raise SystemExit("--notice-path must be not_applicable for no_regular_users windows")

    now = parse_utc(args.now_utc, "--now-utc") if args.now_utc else datetime.now(timezone.utc).replace(microsecond=0)
    start = now + timedelta(minutes=args.start_delay_minutes)
    end = start + timedelta(minutes=args.duration_minutes)
    stale_prevention = runtime_window_stale_prevention(now=now, start=start, end=end)
    run_id = run_id_for_start(start)
    output_root = validate_output_root(args.output_root)
    evidence_dir = output_root / run_id
    closure_root = closure_compatible_evidence_root(run_id, evidence_dir)
    report_dir = Path("/tmp") / f"obelisk-player-principal-{instance}-{map_name}-{run_id}"
    approved_manifest = evidence_dir / "approved-bundle" / "approved-runtime-principal-lifecycle-evidence.json"
    fresh_retry = fresh_retry_after_closed_non_evidence_window(
        now=now,
        run_id=run_id,
        target={"instance": instance, "map": map_name},
        approved_window={
            "start_utc": format_utc(start),
            "end_utc": format_utc(end),
        },
        evidence_dir=evidence_dir,
        report_dir=report_dir,
    )
    active_player_policy = active_player_no_accepted_events_policy(
        target={"instance": instance, "map": map_name},
        observed=active_player_no_accepted_events,
        requested_restart_expectation=args.restart_expectation,
        effective_restart_expectation=effective_restart_expectation,
        concrete_deploy_or_gate_change=concrete_change,
    )
    next_action_policy = runtime_window_next_action_policy(
        target={"instance": instance, "map": map_name},
        requested_restart_expectation=args.restart_expectation,
        effective_restart_expectation=effective_restart_expectation,
        source_discrepancy=args.presence_source_discrepancy,
        session_end_only_no_start=bool(args.session_end_only_no_start),
        active_player_no_accepted_events=active_player_no_accepted_events,
        concrete_deploy_or_gate_change=concrete_change,
    )

    commit = args.obelisk_commit or git_head()
    if not is_reviewed_obelisk_commit(commit):
        raise SystemExit("--obelisk-commit must be a non-zero commit present in this repo")

    common_env = {"PYTHONDONTWRITEBYTECODE": "1"}
    write_env = {**common_env, "OBELISK_ALLOW_SERVER_ROOT_WRITES": "1"}
    notice_report = report_dir / "beta-notice.confirmed.json"
    request_check = report_dir / "window-request.check.json"
    route_gate = report_dir / "route-gate.json"

    prepare_argv = [
        "python3",
        "scripts/prepare_player_principal_lifecycle_window_request.py",
        "--instance",
        instance,
        "--map",
        map_name,
        "--run-id",
        run_id,
        "--obelisk-commit",
        commit,
        "--approved-window-start-utc",
        format_utc(start),
        "--approved-window-end-utc",
        format_utc(end),
        "--binary-sha256",
        args.binary_sha256,
        "--restart-expectation",
        effective_restart_expectation,
        "--final-posture",
        "stable",
        "--user-policy",
        args.user_policy,
        "--notice-path",
        args.notice_path,
        "--rollback-owner",
        rollback_owner,
        "--output-dir",
        str(evidence_dir),
        "--standing-launch-authority",
        "--standing-launch-authority-reference",
        authority_ref,
        "--json",
    ]
    if args.diagnostic_candidates:
        prepare_argv.insert(prepare_argv.index("--json"), "--diagnostic-candidates")
    check_request_argv = [
        "python3",
        "scripts/check_player_principal_lifecycle_window_request.py",
        str(evidence_dir / "window-request.json"),
        "--env-file",
        str(evidence_dir / "observer-window.env"),
        "--operator-request",
        str(evidence_dir / "operator-approval-request.md"),
        "--operator-approval-receipt",
        str(evidence_dir / "operator-approval-receipt.json"),
        "--json",
    ]
    beta_dry_run_argv = [
        "python3",
        "scripts/prepare_player_principal_lifecycle_beta_notice.py",
        "--request-json",
        str(evidence_dir / "window-request.json"),
        "--dry-run",
        "--json",
    ]
    route_gate_argv = ["python3", "scripts/check_command_permission_route_gate.py", "--json"]
    activation_argv = [
        "python3",
        "scripts/check_player_principal_lifecycle_activation_preconditions.py",
        "--request-json",
        str(evidence_dir / "window-request.json"),
        "--request-check-json",
        str(request_check),
        "--notice-report-json",
        str(notice_report),
        "--route-gate-json",
        str(route_gate),
        "--json",
    ]
    approved_bundle_dir = evidence_dir / "approved-bundle"
    runtime_observer_summary = approved_bundle_dir / "runtime-observer-summary.json"
    window_manifest_check = (
        approved_bundle_dir / "player-principal-lifecycle-window-manifest.check.json"
    )
    bundle_preflight_report = report_dir / "approved-runtime-bundle.preflight.json"
    analyzer_argv = [
        "python3",
        RUNTIME_OBSERVER_ANALYZER,
        "--obelisk-commit",
        commit,
        "--fail-on-quality-blockers",
        str(evidence_dir / "Obelisk.log"),
    ]
    strict_candidate_summary_argv = [
        "python3",
        APPROVED_RUNTIME_MANIFEST_BUILDER,
        "--source-summary",
        str(runtime_observer_summary),
        "--window-manifest-check",
        str(window_manifest_check),
        "--output",
        str(approved_manifest),
        "--reviewed-by",
        reviewed_by,
        "--review-note",
        args.review_note,
    ]
    bundle_preflight_argv = [
        "python3",
        APPROVED_RUNTIME_EVIDENCE_BUNDLE_BUILDER,
        "--preflight-only",
        "--evidence-dir",
        str(evidence_dir),
    ]
    approved_check_argv = [
        "python3",
        APPROVED_RUNTIME_EVIDENCE_CHECKER,
        str(approved_manifest),
        "--json",
    ]
    public_contract_argv = [
        "python3",
        "scripts/check_player_identity_public_contract_readiness.py",
        "--approved-runtime-evidence",
        str(approved_manifest),
        "--identity-public-contract-decision-record",
        "docs/research/player-identity-planning-sources/reviewed-identity-public-contract-decision-record.json",
        "--json",
    ]
    status_argv = ["python3", "scripts/report_obelisk_sdk_status.py", "--compact"]
    diagnostic_candidate_metadata = {
        **non_claim_flags(),
        "enabled": bool(args.diagnostic_candidates),
        "classification": "candidate_only_non_evidence" if args.diagnostic_candidates else "disabled",
        "propagated_to_prepare_request_pack": bool(args.diagnostic_candidates),
    }

    return {
        "schema": SCHEMA,
        "status": "planned_offline_only",
        "run_id": run_id,
        "target": {"instance": instance, "map": map_name},
        "fresh_retry_after_closed_non_evidence_window": fresh_retry,
        "active_player_no_accepted_events_policy": active_player_policy,
        "next_action_policy": next_action_policy,
        "requested_restart_expectation": args.restart_expectation,
        "effective_restart_expectation": effective_restart_expectation,
        "presence_source_discrepancy": args.presence_source_discrepancy,
        "session_end_only_no_start": bool(args.session_end_only_no_start),
        "diagnostic_candidates_enabled": bool(args.diagnostic_candidates),
        "diagnostic_candidate_metadata": diagnostic_candidate_metadata,
        "recommended_notice_text": recommended_notice_text(
            instance=instance,
            map_name=map_name,
            start_utc=format_utc(start),
            end_utc=format_utc(end),
        ),
        "beta_notice_transport_policy": beta_notice_transport_policy(),
        "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
        "two_server_cap_policy": two_server_cap_policy(),
        "approved_window": {
            "start_utc": format_utc(start),
            "end_utc": format_utc(end),
            "duration_seconds": int((end - start).total_seconds()),
            "max_duration_seconds": MAX_APPROVED_WINDOW_SECONDS,
            "minimum_pre_activation_lead_seconds": MIN_RUNTIME_WINDOW_LEAD_SECONDS,
            "seconds_until_start_at_plan_time": stale_prevention["seconds_until_start"],
            "enough_future_lead_time_at_plan_time": stale_prevention["enough_future_lead_time"],
        },
        "runtime_window_stale_prevention": stale_prevention,
        "evidence_dir": str(evidence_dir),
        "closure_compatible_evidence_root": closure_root,
        "report_dir": str(report_dir),
        "standing_launch_authority": {
            "recorded": True,
            "reference": authority_ref,
            "bound_by_prepare_command": True,
            "authorizes_scoped_runtime_window_preparation": True,
            "authorizes_window_request_preparation": True,
            "authorizes_dry_run_notice_preparation": True,
            "authorizes_guarded_beta_notice_send": True,
            "authorizes_beta_notice_send": True,
            "preparation_authority_only": False,
            "authorizes_discord_send": True,
            "authorizes_runtime_capture": False,
            "authorizes_runtime_evidence": False,
            "authorizes_marker_env_changes": False,
            "authorizes_server_operations": False,
            "authorizes_server_restart": False,
            "authorizes_publication": False,
            "authorizes_readiness": False,
            "authorizes_p0_progress": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_evidence": False,
            "counts_as_progress": False,
            "counts_as_p0_progress": False,
            "counts_as_runtime_readiness": False,
            "counts_as_public_readiness": False,
            "clears_approved_runtime_evidence_missing": False,
            "strict_copied_bool_triplet_requirement": copied_bool_triplet_requirement(),
            "copied_log_route_required": copied_log_route_contract(),
            "ordered_copied_log_route_step_ids": list(COPIED_LOG_ROUTE_STEP_IDS),
            "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
            "two_server_cap_policy": two_server_cap_policy(),
        },
        "strict_copied_bool_triplet_requirement": {
            **copied_bool_triplet_requirement(),
            "accepted_evidence_requires": (
                "future player-backed copied log containing "
                f"{STRICT_COPIED_BOOL_TRIPLET_TEXT}"
            ),
        },
        "copied_log_route_required": copied_log_route_contract(),
        "ordered_copied_log_route_step_ids": list(COPIED_LOG_ROUTE_STEP_IDS),
        "current_window_workflow": {
            "schema": CURRENT_WINDOW_WORKFLOW_SCHEMA,
            "status": "fresh_current_window_planned",
            "planned_at_utc": format_utc(now),
            "fresh_window_computed_from_current_utc": True,
            "fresh_retry_after_closed_non_evidence_window": fresh_retry,
            "active_player_no_accepted_events_policy": active_player_policy,
            "next_action_policy": next_action_policy,
            "requested_restart_expectation": args.restart_expectation,
            "effective_restart_expectation": effective_restart_expectation,
            "stale_request_window_reuse_allowed": False,
            "stale_beta_notice_sendable": False,
            "minimum_pre_activation_lead_seconds": MIN_RUNTIME_WINDOW_LEAD_SECONDS,
            "seconds_until_start": stale_prevention["seconds_until_start"],
            "enough_future_lead_time": stale_prevention["enough_future_lead_time"],
            "runtime_window_stale_prevention": stale_prevention,
            "next_exact_command_id": "prepare_request_pack",
            "next_exact_command_shell": shell_command(prepare_argv, env=write_env),
            "next_exact_command_argv": prepare_argv,
            "closure_compatible_evidence_root": closure_root,
            "next_exact_command_writes_only_offline_request_pack": True,
            "next_exact_command_sends_discord": False,
            "next_exact_command_touches_live_ark": False,
            "next_exact_command_authorizes_runtime": False,
            "restart_recommended": active_player_policy["restart_recommended"],
            "next_action_id": next_action_policy["next_action_id"],
            "blind_restart_allowed": False,
            "keep_waiting_recommended": next_action_policy["keep_waiting_recommended"],
            "broadcast_recommended": next_action_policy["broadcast_recommended"],
            "prepare_clean_window_recommended": next_action_policy[
                "prepare_clean_window_recommended"
            ],
            "start_or_restart_recommended": active_player_policy["start_or_restart_recommended"],
            "restart_blocked_without_concrete_deploy_or_gate_change": active_player_policy[
                "restart_blocked_without_concrete_deploy_or_gate_change"
            ],
            "beta_notice_dry_run_required_before_activation": True,
            "confirmed_beta_notice_required_before_activation": True,
            "beta_notice_transport_policy": beta_notice_transport_policy(),
            "confirmed_send_must_complete_before_window_start": True,
            "activation_or_restart_from_stale_request_allowed": False,
            "monitor_or_restart_activation_after_window_start_allowed": False,
            "approved_runtime_evidence_missing_cleared": False,
            "dry_run_or_send_metadata_counts_as_evidence": False,
            "passive_wait_counts_as_approved_runtime_evidence": False,
            "start_end_only_counts_as_approved_runtime_evidence": False,
            "plan_counts_as_progress": False,
            "plan_counts_as_runtime_readiness": False,
            "plan_counts_as_public_readiness": False,
            "strict_copied_bool_triplet_requirement": copied_bool_triplet_requirement(),
            "copied_log_route_required": copied_log_route_contract(),
            "ordered_copied_log_route_step_ids": list(COPIED_LOG_ROUTE_STEP_IDS),
            "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
            "two_server_cap_policy": two_server_cap_policy(),
            "non_authorization": (
                "current-window workflow metadata only; does not authorize Discord, "
                "server operations, marker/env changes, runtime capture, approved runtime "
                "evidence, public readiness, SDK completion, publication, or P0 progress"
            ),
        },
        "server_safety": {
            "two_server_cap_policy": two_server_cap_policy(),
            "active_player_no_accepted_events_policy": active_player_policy,
            "next_action_policy": next_action_policy,
            "never_keep_three_ark_servers_running": True,
            "max_running_ark_servers": 2,
            "three_ark_servers_allowed": False,
            "requested_restart_expectation": args.restart_expectation,
            "effective_restart_expectation": effective_restart_expectation,
            "check_player_presence_before_restart": effective_restart_expectation == "restart",
            "broadcast_and_reschedule_if_players_remain_connected": effective_restart_expectation == "restart",
            "blind_restart_allowed": False,
            "next_action_id": next_action_policy["next_action_id"],
            "keep_waiting_recommended": next_action_policy["keep_waiting_recommended"],
            "broadcast_recommended": next_action_policy["broadcast_recommended"],
            "prepare_clean_window_recommended": next_action_policy[
                "prepare_clean_window_recommended"
            ],
            "restart_recommended": active_player_policy["restart_recommended"],
            "start_or_restart_recommended": active_player_policy["start_or_restart_recommended"],
            "restart_requires_concrete_deploy_or_gate_change": active_player_policy[
                "restart_requires_concrete_deploy_or_gate_change"
            ],
            "restart_blocked_without_concrete_deploy_or_gate_change": active_player_policy[
                "restart_blocked_without_concrete_deploy_or_gate_change"
            ],
            "minimum_pre_activation_lead_seconds": MIN_RUNTIME_WINDOW_LEAD_SECONDS,
            "activation_or_restart_from_stale_request_allowed": False,
            "monitor_or_restart_activation_after_window_start_allowed": False,
            "standing_authority_authorizes_server_restart": False,
            "standing_authority_authorizes_marker_env_changes": False,
            "restore_final_posture": "stable",
        },
        "non_claims": [
            "plan emits preactivation commands only; it does not write files or touch live servers",
            "beta notice dry-run must be reviewed before any separate standing-authorized send step",
            "request/check/notice/activation readiness is not approved runtime evidence",
            "diagnostic candidate metadata is non-authorizing and not approved runtime evidence",
            "active-player/no-accepted-events state is drift metadata only; do not restart unless a concrete deploy or gate change is named",
            "RCON/query discrepancies and session_end-only/no-start signals are non-evidence next-action inputs only; keep waiting, broadcast, or prepare a clean window without blind restarts",
            "copied logs must route through analyzer -> strict_lifecycle_triplet_candidate_summary -> bundle preflight -> approved-evidence checker before any accepted evidence state can change",
            "approved runtime evidence remains valid only after copied-log bundle checkers accept it",
            f"future player-backed copied log must contain {STRICT_COPIED_BOOL_TRIPLET_TEXT}",
            "standing launch authority prepares a scoped request window only; it is not evidence, progress, readiness, or publication authority",
            "passive waits, public queries, beta notices, request packs, and start/end-only windows do not clear approved_runtime_evidence_missing",
            "public SDK, runtime readiness, stable SDK, P0 progress, Plugin Hub, publication, tag, and push claims remain forbidden",
        ],
        "artifacts": {
            "window_request": str(evidence_dir / "window-request.json"),
            "observer_env": str(evidence_dir / "observer-window.env"),
            "operator_receipt": str(evidence_dir / "operator-approval-receipt.json"),
            "request_check": str(request_check),
            "beta_notice_dry_run": str(report_dir / "beta-notice.dry-run.json"),
            "beta_notice_dry_run_sidecar": str(report_dir / "beta-notice.dry-run.sidecar.json"),
            "beta_notice_confirmed": str(notice_report),
            "beta_notice_confirmed_sidecar": str(report_dir / "beta-notice.confirmed.sidecar.json"),
            "route_gate": str(route_gate),
            "activation_preconditions": str(report_dir / "activation-preconditions.json"),
            "runtime_observer_summary": str(runtime_observer_summary),
            "strict_lifecycle_triplet_candidate_summary": (
                STRICT_LIFECYCLE_TRIPLET_CANDIDATE_SUMMARY_JSON_PATH
            ),
            "bundle_preflight": str(bundle_preflight_report),
            "window_manifest_check": str(window_manifest_check),
            "approved_runtime_manifest": str(approved_manifest),
            "public_contract_readiness": str(report_dir / "public-contract-readiness.json"),
        },
        "commands": [
            command_entry(
                "prepare_request_pack",
                "Prepare exact standing-authorized request pack",
                prepare_argv,
                env=write_env,
                note="Writes only under the offline evidence directory.",
                metadata={
                    "diagnostic_candidates_enabled": bool(args.diagnostic_candidates),
                    "diagnostic_candidates_classification": diagnostic_candidate_metadata["classification"],
                    "non_authorizing": True,
                    "non_evidence": True,
                    "counts_as_approved_runtime_evidence": False,
                    "counts_as_runtime_readiness": False,
                },
            ),
            command_entry(
                "check_request_pack",
                "Validate request pack",
                check_request_argv,
                env=common_env,
                redirect=request_check,
                note="Must pass before any beta notice send or marker/env activation.",
            ),
            command_entry(
                "beta_notice_dry_run",
                "Render beta tester notice dry-run",
                beta_dry_run_argv,
                env=common_env,
                redirect=report_dir / "beta-notice.dry-run.json",
                note="Review this before a separate confirmed send; this command never sends Discord.",
            ),
            command_entry(
                "route_gate",
                "Capture canonical route gate report",
                route_gate_argv,
                env=common_env,
                redirect=route_gate,
                note="Expected route remains planning-only until runtime evidence is accepted.",
            ),
            command_entry(
                "activation_preconditions",
                "Check offline activation preconditions",
                activation_argv,
                env=common_env,
                redirect=report_dir / "activation-preconditions.json",
                note="Requires a real confirmed-notice report at the recorded path; not run by the offline executor unless supplied.",
            ),
        ],
        "manual_followup_steps": [
            {
                "id": "beta_notice_confirmed_send",
                "title": "Send guarded beta tester notice after dry-run review",
                "argv": [
                    "python3",
                    "scripts/prepare_player_principal_lifecycle_beta_notice.py",
                    "--request-json",
                    str(evidence_dir / "window-request.json"),
                    "--confirm-approved-send",
                    "--json",
                ],
                "redirect_stdout": str(notice_report),
                "non_claim": "separate guarded beta action; not an offline preactivation command and not evidence",
                "manual_external_only": True,
                "blocked_until": [
                    "beta_notice_dry_run_reviewed",
                    "request_window_start_in_future",
                    "confirmed_send_before_window_start",
                ],
                "required_before_activation": True,
                "must_be_real_notice_not_documentation": True,
                "confirmed_send_must_complete_before_window_start": True,
                "runtime_window_stale_prevention": stale_prevention,
                "beta_notice_transport_policy": beta_notice_transport_policy(),
                "activation_or_restart_from_stale_request_allowed": False,
                "monitor_or_restart_activation_after_window_start_allowed": False,
                **non_claim_flags(),
                "strict_copied_bool_triplet_requirement": copied_bool_triplet_requirement(),
                "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
                "two_server_cap_policy": two_server_cap_policy(),
                "standing_authority_satisfies_guarded_beta_notice_send_scope": True,
                "guarded_beta_notice_send_scope_satisfied_by_standing_authority": True,
                "standing_authority_authorizes_discord_send": True,
                "confirmed_send_requires_separate_explicit_discord_send_approval": False,
            },
            {
                "id": "analyze_runtime_observer_log",
                "title": "Analyze copied Obelisk log into runtime observer summary",
                "argv": analyzer_argv,
                "redirect_stdout": str(runtime_observer_summary),
                "non_claim": "post-window analyzer summary only; non-authorizing and non-evidence until checker acceptance",
                "manual_external_only": True,
                "copied_log_route_required": copied_log_route_contract(),
                "ordered_copied_log_route_step_ids": list(COPIED_LOG_ROUTE_STEP_IDS),
                "route_step_id": "analyze_runtime_observer_log",
                "emits_summary_field": STRICT_LIFECYCLE_TRIPLET_CANDIDATE_SUMMARY_JSON_PATH,
                **non_claim_flags(),
                "strict_copied_bool_triplet_requirement": copied_bool_triplet_requirement(),
                "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
                "two_server_cap_policy": two_server_cap_policy(),
            },
            {
                "id": STRICT_LIFECYCLE_TRIPLET_CANDIDATE_SUMMARY_STEP_ID,
                "title": "Gate on strict lifecycle triplet candidate summary",
                "argv": strict_candidate_summary_argv,
                "non_claim": "strict candidate summary route step only; builds a consume-only manifest candidate, not accepted evidence",
                "manual_external_only": True,
                "copied_log_route_required": copied_log_route_contract(),
                "ordered_copied_log_route_step_ids": list(COPIED_LOG_ROUTE_STEP_IDS),
                "route_step_id": STRICT_LIFECYCLE_TRIPLET_CANDIDATE_SUMMARY_STEP_ID,
                "source_summary_path": str(runtime_observer_summary),
                "consumes_summary_field": STRICT_LIFECYCLE_TRIPLET_CANDIDATE_SUMMARY_JSON_PATH,
                "candidate_ready_for_bundle_preflight_required": True,
                "approved_manifest_output": str(approved_manifest),
                **non_claim_flags(),
                "strict_copied_bool_triplet_requirement": copied_bool_triplet_requirement(),
                "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
                "two_server_cap_policy": two_server_cap_policy(),
            },
            {
                "id": "bundle_preflight",
                "title": "Run bundle preflight before approved-evidence checker",
                "argv": bundle_preflight_argv,
                "redirect_stdout": str(bundle_preflight_report),
                "non_claim": "bundle preflight classifies copied sibling inputs only; it is not evidence acceptance",
                "manual_external_only": True,
                "copied_log_route_required": copied_log_route_contract(),
                "ordered_copied_log_route_step_ids": list(COPIED_LOG_ROUTE_STEP_IDS),
                "route_step_id": "bundle_preflight",
                "must_follow": STRICT_LIFECYCLE_TRIPLET_CANDIDATE_SUMMARY_STEP_ID,
                **non_claim_flags(),
                "strict_copied_bool_triplet_requirement": copied_bool_triplet_requirement(),
                "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
                "two_server_cap_policy": two_server_cap_policy(),
            },
            {
                "id": "check_approved_runtime_bundle",
                "title": "Validate approved runtime evidence manifest",
                "argv": approved_check_argv,
                "redirect_stdout": str(report_dir / "approved-runtime-principal-lifecycle-evidence.check.json"),
                "non_claim": "future copied bundle evaluation only; this plan step is not evidence",
                "manual_external_only": True,
                "copied_log_route_required": copied_log_route_contract(),
                "ordered_copied_log_route_step_ids": list(COPIED_LOG_ROUTE_STEP_IDS),
                "route_step_id": "approved_runtime_evidence_checker",
                "must_follow": "bundle_preflight",
                "checker_acceptance_can_change_evidence_state_when_executed": True,
                "accepted_by_this_plan": False,
                **non_claim_flags(),
                "strict_copied_bool_triplet_requirement": copied_bool_triplet_requirement(),
                "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
                "two_server_cap_policy": two_server_cap_policy(),
            },
            {
                "id": "post_runtime_public_contract_readiness",
                "title": "Consume reviewed identity public-contract decision record",
                "argv": public_contract_argv,
                "redirect_stdout": str(report_dir / "public-contract-readiness.json"),
                "non_claim": "contract-review-only follow-up; public/header/runtime readiness remains false",
                "manual_external_only": True,
                **non_claim_flags(),
                "strict_copied_bool_triplet_requirement": copied_bool_triplet_requirement(),
                "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
                "two_server_cap_policy": two_server_cap_policy(),
            },
            {
                "id": "status_after_bundle",
                "title": "Refresh compact SDK status",
                "argv": status_argv,
                "non_claim": "status report only; no readiness claim unless gates allow it",
                "manual_external_only": True,
                **non_claim_flags(),
                "strict_copied_bool_triplet_requirement": copied_bool_triplet_requirement(),
                "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
                "two_server_cap_policy": two_server_cap_policy(),
            },
        ],
    }


def print_human(plan: dict[str, Any]) -> None:
    print(f"Runtime window plan: {plan['run_id']}")
    print(f"Target: {plan['target']['instance']} / {plan['target']['map']}")
    print(f"Window UTC: {plan['approved_window']['start_utc']} -> {plan['approved_window']['end_utc']}")
    print(f"Evidence dir: {plan['evidence_dir']}")
    print(f"Strict copied bool triplet: {plan['strict_copied_bool_triplet_requirement']['requirement']}")
    print(
        "Missing-role objectives: "
        + ", ".join(plan["lifecycle_missing_role_objectives"]["objective_ids"])
    )
    print("Plan non-claim flags: evidence=false progress=false readiness=false clears_approved_runtime_evidence_missing=false")
    print("Safety: never keep three ARK servers running; broadcast/reschedule if restart sees players.")
    print("Next exact command:")
    print(plan["current_window_workflow"]["next_exact_command_shell"])
    print("")
    for index, command in enumerate(plan["commands"], start=1):
        print(f"{index}. {command['title']}")
        print(command["shell"])
        print(
            "Non-claim flags: evidence=false progress=false readiness=false "
            "clears_approved_runtime_evidence_missing=false"
        )
        print(f"Strict copied bool triplet: {command['strict_copied_bool_triplet_requirement']['requirement']}")
        print("")
    print("Manual follow-up steps:")
    for index, step in enumerate(plan["manual_followup_steps"], start=1):
        print(f"{index}. {step['title']}")
        print(
            "Non-claim flags: evidence=false progress=false readiness=false "
            "clears_approved_runtime_evidence_missing=false"
        )
        print(f"Strict copied bool triplet: {step['strict_copied_bool_triplet_requirement']['requirement']}")
        print("")


def main() -> int:
    args = parse_args()
    plan = build_plan(args)
    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print_human(plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
