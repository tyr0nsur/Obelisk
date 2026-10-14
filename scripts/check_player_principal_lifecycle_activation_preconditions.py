#!/usr/bin/env python3
"""Check offline preconditions before activating a player-principal evidence window.

This checker consumes already generated reports. It does not send Discord messages, touch
servers, edit markers/env, read live logs, capture runtime evidence, or promote SDK state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import protected_paths
from prepare_player_principal_lifecycle_beta_notice import (
    GUARDED_BETA_NOTICE_ACTION_SCHEMA,
    NON_AUTHORIZATION as BETA_NOTICE_NON_AUTHORIZATION,
    NOTICE_ACTION_ARTIFACT_SCHEMA,
    NOTICE_ACTION_BLOCKER,
    SCHEMA as BETA_NOTICE_SCHEMA,
    SIDECAR_NON_EVIDENCE_FLAGS,
)
from prepare_player_principal_lifecycle_window_request import (
    APPROVAL_ATTESTATION_CURRENT_TURN,
    APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY,
    APPROVAL_SOURCE_CURRENT_TURN,
    APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY,
    APPROVAL_SCOPE_SCHEMA,
    APPROVAL_SCOPE_SOURCE_REQUIRED,
    APPROVAL_SCOPE_SOURCE_REQUIRED_STANDING_LAUNCH_AUTHORITY,
    APPROVAL_SCOPE_STATUS,
    APPROVAL_SCOPE_STATUS_STANDING_LAUNCH_AUTHORITY,
    AUTHORIZATION_FLAGS,
    CURRENT_TURN_APPROVAL_REQUIRED_FIELDS,
    DIAGNOSTIC_CANDIDATES_ENV_KEY,
    DIRECT_JOIN_PLAN_NON_AUTHORIZATION,
    DIRECT_JOIN_PLAN_SCHEMA,
    EXACT_TARGET_SCOPE_NON_AUTHORIZATION,
    EXACT_TARGET_SCOPE_SCHEMA,
    EXPECTED_BINARY_SHA256,
    EXPECTED_SERVER_BINARY_PATH,
    FORBIDDEN_MARKERS,
    HANDLE_NEW_PLAYER_FUNCTION,
    MAX_APPROVED_WINDOW_SECONDS,
    MAX_OPERATOR_APPROVAL_LEAD_SECONDS,
    MAX_REQUEST_PREPARATION_LEAD_SECONDS,
    MIN_APPROVED_WINDOW_SECONDS,
    PLAYER_NOTICE_ACTION_NON_AUTHORIZATION,
    PLAYER_NOTICE_ACTION_SCHEMA,
    PASSIVE_WAIT_BOUNDARY_NON_AUTHORIZATION,
    PASSIVE_WAIT_BOUNDARY_SCHEMA,
    PLAYER_PRESENCE_SAFETY_NON_AUTHORIZATION,
    PLAYER_PRESENCE_SAFETY_SCHEMA,
    REQUIRED_ENV,
    RUNTIME_TRIPLET_CONTRACT_NON_AUTHORIZATION,
    RUNTIME_TRIPLET_CONTRACT_SCHEMA,
    RUN_ID_RE,
    SCHEMA as WINDOW_REQUEST_SCHEMA,
    SESSION_START_REJECTED_REQUIRED_ARGUMENTS,
    SESSION_START_REJECTED_REQUIRED_CALL,
    SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS,
    SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES,
    SESSION_START_REJECTED_REQUIRED_FUNCTION,
    UTC_RE,
    WINDOW_MARKERS,
    diagnostic_candidates_enabled,
    direct_join_plan,
    is_forbidden_exact_target_alias,
    observer_env_keys,
    requested_wait_window_seconds,
    run_id_for_window_start,
    runtime_triplet_contract,
)


SCHEMA = "obelisk.player-principal-lifecycle-activation-preconditions.v1"
REQUEST_CHECK_SCHEMA = "obelisk.player-principal-lifecycle-window-request-check.v1"
ROUTE_GATE_SCHEMA = "obelisk.command-permission-route-gate-check.v1"
AUTHORITY_PRECONDITION_SCHEMA = (
    "obelisk.player-principal-lifecycle-activation-authority-precondition.v1"
)
SAFETY_LIMITS_SCHEMA = "obelisk.player-principal-lifecycle-standing-debug-safety-limits.v1"
APPROVED_EVIDENCE_BUNDLE_ACCEPTANCE_SCHEMA = (
    "obelisk.player-principal-lifecycle-approved-evidence-bundle-acceptance-required.v1"
)
DIAGNOSTIC_CANDIDATES_APPROVED_EVIDENCE_POLICY_SCHEMA = (
    "obelisk.player-principal-lifecycle-diagnostic-candidates-approved-evidence-policy.v1"
)
TWO_SERVER_CAP_SCHEMA = "obelisk.player-principal-lifecycle-two-server-cap.v1"
LIFECYCLE_ROLE_OBJECTIVES_SCHEMA = (
    "obelisk.player-principal-lifecycle-missing-role-objectives.v1"
)
RECOMMENDED_NOTICE_TEXT_SCHEMA = (
    "obelisk.player-principal-lifecycle-redacted-recommended-notice-text.v1"
)
DIRECT_BOT_NOTICE_SCHEMA = "obelisk.discord-beta-bridge-bot-notice.v1"
ACTIVE_NOTICE_STATE_SCHEMA = "obelisk.discord-beta-bridge-active-notice.v1"
BETA_TEST_BOT_CHANNEL_ID = "1513238083741683934"
SERVER_ROOT = Path("/servidor/ark")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
FALSE_FLAGS = {
    "activation_allowed": False,
    "activation_allowed_before_notice_sent": False,
    "activation_preconditions_met": False,
    "activation_authorized_by_this_report": False,
    "authorizes_discord": False,
    "authorizes_runtime_work": False,
    "authorizes_server_operations": False,
    "authorizes_server_work": False,
    "authorizes_workspace_work": False,
    "authorizes_workspace_writes": False,
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
    "marker_env_changes_authorized": False,
    "runtime_capture_authorized": False,
    "runtime_window_authorized": False,
    "runtime_activation_authorized": False,
    "current_turn_scope_authorized": False,
    "operator_may_activate_by_this_report": False,
    "discord_authorized_by_this_report": False,
    "approved_runtime_evidence": False,
    "approved_runtime_evidence_present": False,
    "approved_runtime_evidence_ready": False,
    "counts_as_approved_runtime_evidence": False,
    "counts_as_runtime_evidence": False,
    "counts_as_sdk_evidence": False,
    "counts_toward_public_sdk": False,
    "counts_toward_runtime": False,
    "counts_toward_v1_completion": False,
    "counts_toward_sdk": False,
    "counts_toward_p0_dependency_chain": False,
    "public_or_runtime_accounting_allowed": False,
    "promotion_ready": False,
    "public_abi_ready": False,
    "public_sdk_ready": False,
    "runtime_evidence_present": False,
    "runtime_evidence_ready": False,
    "runtime_ready": False,
    "route_ready": False,
    "sdk_evidence_ready": False,
    "v1_completion_ready": False,
    "stable_claim_allowed": False,
    "workspace_writes_authorized": False,
}
NON_AUTHORIZATION = (
    "offline pre-activation consistency check only; this report does not authorize Discord, "
    "server operations, marker/env changes, starts, restarts, runtime capture, approved "
    "runtime evidence, public readiness, SDK completion, or P0 progress"
)
DIAGNOSTIC_CANDIDATES_APPROVED_EVIDENCE_NON_AUTHORIZATION = (
    "diagnostic candidate logging is debug-only and non-promotable; an approved "
    "player-principal lifecycle evidence window must explicitly disable "
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES and reject copied logs "
    "with lifecycle diagnostic candidate lines"
)
DIAGNOSTIC_CANDIDATES_APPROVED_EVIDENCE_BLOCKER = (
    "diagnostic_candidates_for_approved_evidence_window"
)
DIAGNOSTIC_CANDIDATES_NOT_EXPLICITLY_DISABLED_BLOCKER = (
    "diagnostic_candidates_not_explicitly_disabled_for_approved_evidence_window"
)
OBSERVER_ENV_DIAGNOSTIC_CANDIDATES_BLOCKER = (
    "observer_env_diagnostic_candidates_for_approved_evidence_window"
)
OBSERVER_ENV_DIAGNOSTIC_KEYS_BLOCKER = (
    "observer_env_diagnostic_keys_for_approved_evidence_window"
)
DIAGNOSTIC_APPROVED_EVIDENCE_ENV_KEYS = (
    DIAGNOSTIC_CANDIDATES_ENV_KEY,
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_DIAGNOSTICS",
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_FUNCTION_FNAME_NEAR_MISS_SCAN_LIMIT",
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING",
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT",
)
READY_NEXT_BLOCKER = "fresh_current_turn_operator_authorization_required_before_activation"
STANDING_READY_NEXT_BLOCKER = (
    "offline_preconditions_consistent_recorded_standing_authority_scoped_operations_next"
)
ROUTE_GATE_FORBIDDEN_FALSE_CLAIM_KEYS = frozenset(FALSE_FLAGS) | {
    "accepted_runtime_evidence",
    "accepted_runtime_evidence_context",
    "accepted_runtime_evidence_ready",
    "approved_runtime_evidence_accepted",
    "bundle_output_counts_as_approved_runtime_evidence",
    "completed_receipt_counts_as_approved_runtime_evidence",
    "copied_log_metadata_counts_as_approved_runtime_evidence",
    "counts_toward_complete_sdk_claim",
    "counts_toward_complete_sdk_claim_now",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_p0_dependency_chain_claim_now",
    "observer_env_counts_as_approved_runtime_evidence",
    "operator_request_counts_as_approved_runtime_evidence",
    "preflight_counts_as_approved_runtime_evidence",
    "public_header_allowed",
    "request_pack_counts_as_approved_runtime_evidence",
    "route_gate_counts_toward_v1_completion",
    "window_manifest_counts_as_approved_runtime_evidence",
    "beta_notice_delivered",
    "confirmed_beta_notice_delivered",
    "confirmed_notice_delivered",
    "notice_delivered",
    "player_notice_delivered",
}
ROUTE_GATE_FORBIDDEN_NONZERO_PROGRESS_KEYS = frozenset(
    {
        "claim_progress_contribution",
        "complete_sdk_claim_progress_contribution",
        "complete_sdk_progress_contribution",
        "p0_dependency_chain_claim_progress_contribution",
        "p0_dependency_chain_progress_contribution",
    }
)
FORBIDDEN_FALSE_CLAIM_KEYS = frozenset(FALSE_FLAGS) | ROUTE_GATE_FORBIDDEN_FALSE_CLAIM_KEYS | {
    "accepted_runtime_evidence",
    "activation_preconditions_authorize_runtime",
    "activation_preconditions_authorized",
    "approved_runtime_evidence_accepted",
    "closure_request_authorizes_runtime",
    "closure_request_counts_as_approved_runtime_evidence",
    "closure_request_counts_toward_sdk",
    "current_turn_authorized",
    "current_turn_runtime_authorized",
    "current_turn_scope_authorized",
    "current_turn_scope_ready",
    "discord_sent_by_this_report",
    "dry_run_notice_authorizes_runtime",
    "dry_run_notice_counts_as_approved_runtime_evidence",
    "dry_run_notice_ready",
    "live_log_access_allowed",
    "live_log_permission",
    "live_log_permission_granted",
    "live_log_read_allowed",
    "live_log_read_permission",
    "live_log_reads_authorized",
    "live_logs_permission",
    "live_logs_read_allowed",
    "live_logs_read_permission",
    "operator_approval_authorizes_runtime",
    "operator_approval_recorded_authorizes_runtime",
    "p0_accounting_counts_as_promoted_surface",
    "request_pack_ready_authorizes_runtime",
    "runtime_evidence_accepted",
    "sdk_accounting_counts_as_completed_surface",
    "sdk_ready",
    "status_snapshot_authorizes_runtime",
}
FORBIDDEN_NONZERO_PROGRESS_KEYS = ROUTE_GATE_FORBIDDEN_NONZERO_PROGRESS_KEYS | {
    "progress",
    "sdk_progress",
    "p0_progress",
    "v1_progress",
    "runtime_progress",
    "closure_request_progress_contribution",
}
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
    "tester",
    "testers",
    "user",
    "users",
    "v1",
    "wait",
    "workspace",
}
CLAIM_COMPLETION_TOKENS = {
    "accepted",
    "allowed",
    "complete",
    "completed",
    "completion",
    "delivered",
    "enabled",
    "present",
    "promoted",
    "ready",
    "readiness",
    "supported",
    "unlocked",
}
GENERIC_STATUS_KEYS = {"claim", "evidence", "readiness", "result", "state", "status"}
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
    "state",
    "status",
    "value",
}
FORBIDDEN_STATUS_VALUE_TOKENS = {
    "accepted",
    "approved",
    "authorized",
    "complete",
    "completed",
    "current",
    "ready",
    "sent",
    "delivered",
}
FORBIDDEN_POSITIVE_STATUS_ALIAS_KEYS = {
    "accepted",
    "approved",
    "complete",
    "completed",
    "current_turn_authorized",
    "current_turn_runtime_authorized",
    "current_turn_scope_authorized",
    "current_turn_scope_ready",
    "delivered",
    "ready",
    "runtime_authorized",
}
REQUEST_CHECK_ALLOWED_POSITIVE_CLAIM_PATHS = frozenset(
    {
        "$.ready",
        "$.request_pack_ready",
        "$.operator_approval_receipt_verified",
        "$.current_turn_approval_recorded",
        "$.current_turn_operator_approval_required",
        "$.planning_only",
    }
)
NOTICE_POLICY_POSITIVE_CONTAINER_PATHS = (
    "$",
    "$.beta_runtime_choreography",
    "$.dry_run_ready_to_send.beta_runtime_choreography",
    "$.dry_run_ready_to_send.recommended_notice_text",
    "$.dry_run_ready_to_send.recommended_notice_text.beta_runtime_choreography",
    "$.guarded_beta_notice_action",
    "$.guarded_beta_notice_action.beta_runtime_choreography",
    "$.next_action_sequence[*].beta_runtime_choreography",
    "$.recommended_notice_text",
    "$.recommended_notice_text.beta_runtime_choreography",
)
NOTICE_POLICY_POSITIVE_FIELDS = (
    "defer_until_drift_fix_when_no_accepted_events",
    "no_restart_when_player_present_observer_enabled_no_accepted_events",
)
NOTICE_STATUS_COORDINATION_CONTAINER_PATHS = (
    "$.active_notice_update_policy",
    "$.tester_status_workflow",
    "$.tester_status_workflow.active_notice_update_policy",
    "$.dry_run_ready_to_send.active_notice_update_policy",
    "$.dry_run_ready_to_send.tester_status_workflow",
    "$.dry_run_ready_to_send.tester_status_workflow.active_notice_update_policy",
    "$.next_action_sequence[*].tester_status_workflow",
    "$.next_action_sequence[*].tester_status_workflow.active_notice_update_policy",
    "$.bot_notice_send_path.active_notice_update_policy",
)
NOTICE_STATUS_COORDINATION_POSITIVE_FIELDS = (
    "status_summary_button_required",
    "status_summary_uses_local_event_sink_only",
    "status_summary_ephemeral_response_only",
)
NOTICE_BOT_HELPER_PAYLOAD_PATHS = (
    "$.confirmed_send_dry_run_receipt_preflight_payload",
    "$.confirmed_send_helper_payload",
)
NOTICE_BOT_HELPER_METADATA_CONTAINER_PATHS = tuple(
    f"{path}.{container}"
    for path in NOTICE_BOT_HELPER_PAYLOAD_PATHS
    for container in (
        "active_notice_reuse_diagnostic",
        "editable_notice_workflow",
        "operational_message_policy",
    )
)
NOTICE_BOT_HELPER_STATUS_WORKFLOW_PATHS = tuple(
    f"{path}.tester_status_workflow" for path in NOTICE_BOT_HELPER_PAYLOAD_PATHS
)
NOTICE_BOT_HELPER_ROOT_POSITIVE_FIELDS = (
    "active_notice_state_present",
    "discord_sent",
    "http_status",
    "status_summary_action_count",
    "status_summary_ephemeral_response_only",
    "status_summary_metadata_only",
    "status_summary_uses_local_event_sink_only",
)
NOTICE_BOT_HELPER_METADATA_POSITIVE_FIELDS = (
    "active_notice_state_present",
    "status_summary_action_count",
    "status_summary_ephemeral_response_only",
    "status_summary_metadata_only",
    "status_summary_uses_local_event_sink_only",
)
NOTICE_BOT_HELPER_STATUS_WORKFLOW_POSITIVE_FIELDS = (
    "cluster_transfer_is_coordination_status_only",
    "status_summary_uses_local_event_sink_only",
    "updates_existing_notice_when_state_present",
)
NOTICE_ALLOWED_POSITIVE_CLAIM_PATHS = frozenset(
    {
        "$.ready",
        "$.discord_sent",
        "$.guarded_beta_notice_action.real_beta_test_notice_action_completed",
        "$.next_action_sequence[*].separate_operator_authorization_required",
        "$.dry_run_required_before_send",
        "$.real_notice_send_required_before_activation",
        "$.notice_authority_boundary.fresh_current_turn_operator_authorization_required_before_confirmed_send",
        "$.notice_authority_boundary.separate_operator_authorization_required_before_confirmed_send",
        "$.notice_authority_boundary.standing_launch_authority_satisfies_confirmed_discord_send_scope",
        "$.notice_authority_boundary.standing_authority_authorizes_discord_send",
        "$.dry_run_consumption_boundary.standing_launch_authority_satisfies_confirmed_discord_send_scope",
        "$.dry_run_consumption_boundary.standing_authority_authorizes_discord_send",
        "$.dry_run_ready_to_send.standing_launch_authority_satisfies_confirmed_discord_send_scope",
        "$.dry_run_ready_to_send.send_next_action_satisfied_by_recorded_standing_authority",
        "$.dry_run_ready_to_send.standing_authority_authorizes_discord_send",
        "$.dry_run_ready_to_send.runtime_window_should_not_wait_for_lead_notice_authorization",
        "$.guarded_beta_notice_action.notice_action_covered_by_standing_launch_authority",
        "$.guarded_beta_notice_action.standing_authority_authorizes_discord_send",
        "$.notice_action_covered_by_standing_launch_authority",
        "$.standing_launch_authority_satisfies_confirmed_discord_send_scope",
        "$.standing_authority_authorizes_discord_send",
        "$.next_action_sequence[*].notice_action_covered_by_standing_launch_authority",
        "$.next_action_sequence[*].send_next_action_satisfied_by_recorded_standing_authority",
        "$.next_action_sequence[*].standing_authority_authorizes_discord_send",
        "$.next_action_sequence[*].runtime_window_should_not_wait_for_lead_notice_authorization",
        "$.current_window_workflow.status",
        "$.dry_run_ready_to_send.current_window_workflow.status",
        "$.dry_run_ready_to_send.request_window_sendability.dry_run_ready_to_send_allowed_by_request_window",
        "$.dry_run_ready_to_send.ready_fields_are_sendability_gates_only",
        "$.request_window_sendability.dry_run_ready_to_send_allowed_by_request_window",
        "$.ready_field_is_helper_success_gate_only",
        "$.active_notice_update_policy.discord_bot_channel_path_enabled",
        "$.dry_run_ready_to_send.active_notice_update_policy.discord_bot_channel_path_enabled",
        "$.tester_status_workflow.active_notice_update_policy.discord_bot_channel_path_enabled",
        "$.tester_status_workflow.updates_existing_notice_when_state_present",
        "$.dry_run_ready_to_send.tester_status_workflow.active_notice_update_policy.discord_bot_channel_path_enabled",
        "$.dry_run_ready_to_send.tester_status_workflow.updates_existing_notice_when_state_present",
        "$.next_action_sequence[*].tester_status_workflow.active_notice_update_policy.discord_bot_channel_path_enabled",
        "$.next_action_sequence[*].tester_status_workflow.updates_existing_notice_when_state_present",
        "$.bot_notice_send_path.active_notice_update_policy.discord_bot_channel_path_enabled",
        "$.bot_notice_send_path.required_helper_args_present",
        "$.bot_notice_send_path.send_beta_notice_arg_present",
        "$.bot_notice_send_path.with_beta_controls_arg_present",
        "$.bot_notice_send_path.update_active_notice_arg_present",
        "$.active_notice_window_decision.active_notice_state_present",
        "$.active_notice_window_decision.wait_without_fresh_window_allowed",
        "$.dry_run_ready_to_send.active_notice_window_decision.active_notice_state_present",
        "$.dry_run_ready_to_send.active_notice_window_decision.wait_without_fresh_window_allowed",
        "$.next_action_sequence[*].active_notice_window_decision.active_notice_state_present",
        "$.next_action_sequence[*].active_notice_window_decision.wait_without_fresh_window_allowed",
    }
) | frozenset(
    f"{path}.active_player_no_accepted_events_policy.{field}"
    for path in NOTICE_POLICY_POSITIVE_CONTAINER_PATHS
    for field in ("defer_until_drift_fix_when_no_accepted_events", "status")
) | frozenset(
    f"{path}.{field}"
    for path in NOTICE_POLICY_POSITIVE_CONTAINER_PATHS
    for field in NOTICE_POLICY_POSITIVE_FIELDS
    if path != "$"
) | frozenset(
    f"{path}.{field}"
    for path in NOTICE_STATUS_COORDINATION_CONTAINER_PATHS
    for field in NOTICE_STATUS_COORDINATION_POSITIVE_FIELDS
) | frozenset(
    f"{path}.{field}"
    for path in NOTICE_BOT_HELPER_PAYLOAD_PATHS
    for field in NOTICE_BOT_HELPER_ROOT_POSITIVE_FIELDS
) | frozenset(
    f"{path}.{field}"
    for path in NOTICE_BOT_HELPER_METADATA_CONTAINER_PATHS
    for field in NOTICE_BOT_HELPER_METADATA_POSITIVE_FIELDS
) | frozenset(
    f"{path}.{field}"
    for path in NOTICE_BOT_HELPER_STATUS_WORKFLOW_PATHS
    for field in NOTICE_BOT_HELPER_STATUS_WORKFLOW_POSITIVE_FIELDS
)
ROUTE_GATE_ALLOWED_POSITIVE_CLAIM_PATHS = frozenset(
    {
        "$.valid",
        "$.planning_only",
        "$.accepted_for_planning",
        "$.route_blocked",
        "$.dependency_chain_locked",
        "$.post_evidence_p0_lock_simulation.simulation_only",
    }
)
REQUEST_ALLOWED_POSITIVE_CLAIM_PATHS = frozenset(
    {
        "$.deployment_intent.status",
        "$.operator_live_ops_brief.deployment_intent.status",
    }
)
REQUEST_CHECK_ALLOWED_POSITIVE_CLAIM_PATHS = REQUEST_CHECK_ALLOWED_POSITIVE_CLAIM_PATHS | {
    "$.deployment_intent.status",
}
EXPECTED_EXACT_TARGET_SCOPE_KEYS = frozenset(
    (
        "schema",
        "instance",
        "map",
        "instance_alias_allowed",
        "map_alias_allowed",
        "approval_must_name_exact_instance_and_map",
        "target_matches_request_target",
        "non_authorization",
    )
)
EXPECTED_RUNTIME_TRIPLET_CONTRACT_KEYS = frozenset(
    (
        "schema",
        "planning_only",
        "session_start_rejected",
        "handle_new_player_rejected_tuples",
        "non_authorization",
    )
)
EXPECTED_RUNTIME_TRIPLET_SESSION_START_KEYS = frozenset(
    (
        "event",
        "required_function",
        "required_argument_tuple",
        "required_call",
        "required_copied_bool_fields",
        "required_copied_bool_values",
        "handle_new_player_rejected_tuple_allowed",
        "handle_new_player_rejected_tuple_alternative_allowed",
    )
)
EXPECTED_RUNTIME_TRIPLET_HANDLE_NEW_PLAYER_KEYS = frozenset(
    (
        "function",
        "allowed_for_session_start_rejected",
        "alternative_for_session_start_rejected",
        "classification",
    )
)
EXPECTED_DIRECT_JOIN_PLAN_KEYS = frozenset(
    (
        "schema",
        "target",
        "route",
        "target_instance",
        "target_map",
        "target_map_is_theisland",
        "fastest_clean_theisland_direct_join",
        "direct_join_required",
        "cluster_transfer_required",
        "extra_transfer_server_required",
        "third_ark_server_allowed",
        "max_running_ark_servers",
        "broad_discord_or_community_notice_allowed",
        "approved_notice_path",
        "raw_player_text_allowed",
        "raw_player_identity_allowed",
        "raw_player_text_or_identity_allowed",
        "secret_or_webhook_output_allowed",
        "diagnostic_candidates_allowed_for_approved_evidence",
        "beta_runtime_choreography",
        "organic_wait_window_seconds",
        "max_organic_wait_window_seconds",
        "organic_wait_window_authorizes_current_turn_approval",
        "organic_wait_window_authorizes_deploy_or_restart",
        "organic_wait_window_authorizes_runtime_capture",
        "organic_wait_window_counts_as_approved_runtime_evidence",
        "receipt_before_activation_required",
        "post_window_replay_requires_receipt",
        "non_authorization",
    )
)
FLOW_ALIAS_TOKENS = frozenset(
    (
        "no_tester",
        "no_testers",
        "no_user",
        "no_users",
        "notester",
        "notesters",
        "nouser",
        "nousers",
        "notice",
        "notice_only",
        "organic_wait",
        "passive",
        "passive_monitor",
        "passive_only",
        "passive_wait",
        "public_readiness",
        "public_ready",
        "readiness",
        "status",
        "status_only",
        "wait_only",
    )
)
FLOW_ALIAS_RE = re.compile(
    r"(^|[_ .:-])(?:notice|passive|status|readiness)(?:$|[_ .:-])|"
    r"(?:no[_ .:-]?(?:users?|testers?)|passive[_ .:-]?wait|wait[_ .:-]?only|organic[_ .:-]?wait)|"
    r"public[_ .:-]?readiness",
    re.IGNORECASE,
)
PASSIVE_STATUS_ARTIFACT_RE = re.compile(
    r"(?:passive|status|snapshot|summary|readiness|monitor)",
    re.IGNORECASE,
)
REJECTED_START_CONTEXT_RE = re.compile(
    r"(?:session[_ -]?start[_ -]?rejected|rejected[_ -]?(?:start|tuple)|start[_ -]?rejected)",
    re.IGNORECASE,
)
APPROVED_ALTERNATIVE_RE = re.compile(
    r"(?:approved|accepted|allowed|valid)[_ -]?(?:alternative|substitute|fallback)|"
    r"(?:alternative|substitute|fallback)[_ -]?(?:approved|accepted|allowed|valid)",
    re.IGNORECASE,
)
STANDING_AUTHORITY_MARKER_KEYS = {
    "standing_debug_authority_recorded",
    "standing_launch_authority_recorded",
}
STANDING_AUTHORITY_OBJECT_KEYS = {
    "recorded_standing_debug_authority",
    "standing_debug_authority",
    "standing_launch_authority",
}
CHECK_JOIN_IN_PROGRESS_FUNCTION = SESSION_START_REJECTED_REQUIRED_FUNCTION
ON_LOGOUT_FUNCTION = "ShooterGameMode.OnLogout"
HANDLE_NEW_PLAYER_TARGETS = {HANDLE_NEW_PLAYER_FUNCTION, "ShooterGameMode.HandleNewPlayer"}
CHECK_JOIN_IN_PROGRESS_TARGETS = {
    CHECK_JOIN_IN_PROGRESS_FUNCTION,
    "ShooterGameMode.CheckJoinInProgress",
}
ON_LOGOUT_TARGETS = {ON_LOGOUT_FUNCTION, "OnLogout"}
START_END_ONLY_RUNTIME_EVIDENCE_SCHEMA = (
    "obelisk.players-identity-runtime-principal-start-end-evidence-check.v1"
)
START_END_ONLY_READY_SCOPE = "principal_start_end_runtime_evidence_only"
START_END_ONLY_RESOLVED_INPUT = "runtime.lifecycle_start_end_evidence"
EXPECTED_COPIED_BOOL_SHAPES = {
    "session_start": {
        "target": HANDLE_NEW_PLAYER_FUNCTION,
        "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
        "copied_bool_values": ["1", "1"],
    },
    "session_start_rejected": {
        "target": CHECK_JOIN_IN_PROGRESS_FUNCTION,
        "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
        "copied_bool_values": ["1", "0"],
    },
    "session_end": {
        "target": ON_LOGOUT_FUNCTION,
        "copied_bool_fields": [],
        "copied_bool_values": [],
        "correlation_status": "matched",
    },
}
SECRET_TEXT_RE = re.compile(
    r"(discord(?:app)?\.com/api/webhooks/)[^\s\"']+|"
    r"((?:WEBHOOK|TOKEN|SECRET|PASSWORD|KEY)[A-Z0-9_]*=)[^\s\"']+",
    re.IGNORECASE,
)


def claim_key_tokens(key: str) -> set[str]:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key)
    separated = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", separated)
    return {token for token in re.split(r"[^A-Za-z0-9]+", separated.lower()) if token}


def normalized_claim_key(key: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
    separated = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", separated)
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def is_forbidden_flow_alias(value: str) -> bool:
    normalized = normalized_claim_key(value)
    return (
        normalized in FLOW_ALIAS_TOKENS
        or FLOW_ALIAS_RE.search(value) is not None
        or is_forbidden_exact_target_alias(value)
    )


NORMALIZED_FORBIDDEN_FALSE_CLAIM_KEYS = {
    normalized_claim_key(key) for key in FORBIDDEN_FALSE_CLAIM_KEYS
}
NORMALIZED_FORBIDDEN_NONZERO_PROGRESS_KEYS = {
    normalized_claim_key(key) for key in FORBIDDEN_NONZERO_PROGRESS_KEYS
}
NORMALIZED_GENERIC_STATUS_KEYS = {
    normalized_claim_key(key) for key in GENERIC_STATUS_KEYS
}
NOTICE_NEGATIVE_POLICY_TRUE_KEYS = {
    "accepted_copied_sibling_set_required_before_runtime_claims",
    "edit_existing_message_when_active_notice_state_present",
}


def notice_negative_policy_true_key(key: object) -> bool:
    return normalized_claim_key(key) in NOTICE_NEGATIVE_POLICY_TRUE_KEYS


def claim_path_allowed(path: str, allowed_positive_paths: frozenset[str]) -> bool:
    if path in allowed_positive_paths:
        return True
    for pattern in allowed_positive_paths:
        if "[*]" not in pattern:
            continue
        regex = re.escape(pattern).replace(r"\[\*\]", r"\[\d+\]")
        if re.fullmatch(regex, path):
            return True
    if "$.checks[*].accepted_for_planning" in allowed_positive_paths and re.fullmatch(
        r"\$\.checks\[\d+\]\.accepted_for_planning",
        path,
    ):
        return True
    if "$.checks[*].name" in allowed_positive_paths and re.fullmatch(
        r"\$\.checks\[\d+\]\.name",
        path,
    ):
        return True
    if "$.post_evidence_p0_lock_simulation.p0_child_checks[*].name" in allowed_positive_paths and re.fullmatch(
        r"\$\.post_evidence_p0_lock_simulation\.p0_child_checks\[\d+\]\.name",
        path,
    ):
        return True
    return False


def claim_container_allowed(path: str, allowed_positive_paths: frozenset[str]) -> bool:
    if "$.checks[*].name" in allowed_positive_paths and re.fullmatch(r"\$\.checks\[\d+\]", path):
        return True
    if "$.post_evidence_p0_lock_simulation.p0_child_checks[*].name" in allowed_positive_paths and re.fullmatch(
        r"\$\.post_evidence_p0_lock_simulation\.p0_child_checks\[\d+\]",
        path,
    ):
        return True
    return False


def positive_claim_alias_key(key: str) -> bool:
    tokens = claim_key_tokens(key)
    normalized = "_".join(sorted(tokens))
    if not tokens:
        return False
    if normalized_claim_key(key) in FORBIDDEN_POSITIVE_STATUS_ALIAS_KEYS:
        return True
    if "authoriz" in key.lower() or "authoris" in key.lower():
        return True
    if no_user_passive_alias_tokens(tokens) and tokens & (
        CLAIM_COMPLETION_TOKENS
        | {
            "authorization",
            "authorized",
            "available",
            "counts",
            "delivered",
            "evidence",
            "notice",
            "progress",
            "readiness",
            "sent",
            "state",
            "status",
        }
    ):
        return True
    if "ready" in tokens or "readiness" in tokens or "accepted" in tokens:
        return True
    if "progress" in tokens:
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
        tokens & {"accepted", "approval", "approved", "authorized", "ready", "recorded", "sent"}
        or "authoriz" in normalized
        or "authoris" in normalized
    ):
        return True
    if "counts" in tokens and tokens & CLAIM_DOMAIN_TOKENS:
        return True
    if "evidence" in tokens and tokens & (CLAIM_COMPLETION_TOKENS | {"approved", "runtime", "sdk"}):
        return True
    if tokens & CLAIM_DOMAIN_TOKENS and tokens & CLAIM_COMPLETION_TOKENS:
        return True
    return False


def no_user_passive_alias_tokens(tokens: set[str]) -> bool:
    no_user_or_tester = bool(
        tokens & {"no", "none", "zero"}
        and tokens & {"tester", "testers", "user", "users"}
    )
    passive_wait = {"passive", "wait"}.issubset(tokens)
    wait_only = {"wait", "only"}.issubset(tokens)
    organic_wait = {"organic", "wait"}.issubset(tokens)
    return no_user_or_tester or passive_wait or wait_only or organic_wait


def positive_status_alias_value(value: str) -> bool:
    tokens = claim_key_tokens(value)
    if not tokens:
        return False
    if tokens & {"blocked", "candidate", "missing", "none", "not", "only", "required", "requires"} and not (
        tokens & {"accepted", "approved", "authorized", "delivered", "ready", "sent"}
    ):
        return False
    if tokens & {
        "ready",
        "accepted",
        "allowed",
        "approved",
        "authorized",
        "delivered",
        "enabled",
        "present",
        "progress",
        "sent",
        "supported",
        "true",
        "unlocked",
        "yes",
    }:
        return True
    if tokens & {"complete", "completed"} and tokens & CLAIM_DOMAIN_TOKENS:
        return True
    if {"current", "turn"}.issubset(tokens) and tokens & {"approval", "authorized", "accepted", "ready"}:
        return True
    return False


def positive_claim_alias_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return positive_status_alias_value(value)
    if isinstance(value, dict):
        return any(positive_claim_alias_value(child) for child in value.values())
    if isinstance(value, list):
        return any(positive_claim_alias_value(child) for child in value)
    return False


def scalar_text(value: Any) -> str | None:
    if isinstance(value, (str, int, float, bool)) and value is not None:
        return str(value)
    return None


def mentions_handle_new_player(value: Any) -> bool:
    text = scalar_text(value)
    return text is not None and HANDLE_NEW_PLAYER_FUNCTION in text


def mentions_rejected_start_context(value: Any) -> bool:
    text = scalar_text(value)
    return text is not None and REJECTED_START_CONTEXT_RE.search(text) is not None


def mentions_approved_alternative(value: Any) -> bool:
    text = scalar_text(value)
    return text is not None and APPROVED_ALTERNATIVE_RE.search(text) is not None


def collect_stale_handle_new_player_rejected_start_rules(value: Any, trail: str = "$") -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        local_scalars: list[Any] = []
        for key, child in value.items():
            local_scalars.append(key)
            if scalar_text(child) is not None:
                local_scalars.append(child)
        local_mentions_handle = any(mentions_handle_new_player(item) for item in local_scalars)
        local_mentions_rejected = any(mentions_rejected_start_context(item) for item in local_scalars)
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if (
                local_mentions_handle
                and local_mentions_rejected
                and mentions_approved_alternative(key)
                and positive_claim_alias_value(child)
            ):
                matches.append(child_trail)
            if (
                mentions_handle_new_player(child)
                and normalized_claim_key(key)
                in {"function", "required_function", "ufunction", "required_ufunction"}
                and "session_start_rejected" in child_trail.casefold()
            ):
                matches.append(child_trail)
            if isinstance(child, str) and (
                HANDLE_NEW_PLAYER_FUNCTION in child
                and REJECTED_START_CONTEXT_RE.search(child) is not None
                and APPROVED_ALTERNATIVE_RE.search(child) is not None
            ):
                matches.append(child_trail)
            matches.extend(collect_stale_handle_new_player_rejected_start_rules(child, child_trail))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            matches.extend(collect_stale_handle_new_player_rejected_start_rules(child, f"{trail}[{index}]"))
    return matches


def zero_progress_alias_value(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == 0


def collect_forbidden_claim_aliases(
    value: Any,
    *,
    allowed_positive_paths: frozenset[str] = frozenset(),
    trail: str = "$",
) -> list[str]:
    matches: list[str] = []
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
            normalized_name = normalized_claim_key(claim_name)
            if normalized_name in NORMALIZED_FORBIDDEN_NONZERO_PROGRESS_KEYS:
                if not declared_claim_values:
                    matches.append(trail)
                else:
                    for claim_value in declared_claim_values:
                        if not zero_progress_alias_value(claim_value):
                            matches.append(trail)
                            break
                continue
            if normalized_name in NORMALIZED_FORBIDDEN_FALSE_CLAIM_KEYS or positive_claim_alias_key(claim_name):
                if claim_container_allowed(trail, allowed_positive_paths):
                    continue
                if not declared_claim_values or any(claim_value is not False for claim_value in declared_claim_values):
                    matches.append(trail)
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            normalized_key = normalized_claim_key(key)
            if normalized_key == "non_authorization":
                continue
            if notice_negative_policy_true_key(key):
                matches.extend(
                    collect_forbidden_claim_aliases(
                        child,
                        allowed_positive_paths=allowed_positive_paths,
                        trail=child_trail,
                    )
                )
                continue
            if normalized_key in NORMALIZED_FORBIDDEN_FALSE_CLAIM_KEYS and child is not False:
                if child is None and claim_path_allowed(child_trail, allowed_positive_paths):
                    pass
                else:
                    matches.append(child_trail)
            if normalized_key in NORMALIZED_FORBIDDEN_NONZERO_PROGRESS_KEYS:
                if not zero_progress_alias_value(child):
                    matches.append(child_trail)
            if (
                not isinstance(child, (dict, list))
                and not claim_path_allowed(child_trail, allowed_positive_paths)
                and normalized_key not in NORMALIZED_FORBIDDEN_NONZERO_PROGRESS_KEYS
                and positive_claim_alias_key(str(key))
                and positive_claim_alias_value(child)
            ):
                matches.append(child_trail)
            if (
                normalized_key in NORMALIZED_GENERIC_STATUS_KEYS
                and positive_claim_alias_value(child)
                and not claim_path_allowed(child_trail, allowed_positive_paths)
            ):
                matches.append(child_trail)
            if (
                isinstance(child, str)
                and str(key) in {"authorization_source", "approved_runtime_evidence_source"}
                and child not in {"none_request_pack_check_only", "none_request_pack_only", "none_preflight_sidecar_only"}
            ):
                matches.append(child_trail)
            matches.extend(
                collect_forbidden_claim_aliases(
                    child,
                    allowed_positive_paths=allowed_positive_paths,
                    trail=child_trail,
                )
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            matches.extend(
                collect_forbidden_claim_aliases(
                    child,
                    allowed_positive_paths=allowed_positive_paths,
                    trail=f"{trail}[{index}]",
                )
            )
    return matches


def contains_standing_authority_marker(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = normalized_claim_key(key)
            if normalized in STANDING_AUTHORITY_MARKER_KEYS and child is True:
                return True
            if normalized in STANDING_AUTHORITY_OBJECT_KEYS:
                if isinstance(child, dict) and child.get("recorded") is True:
                    return True
                if child is True:
                    return True
            if contains_standing_authority_marker(child):
                return True
    elif isinstance(value, list):
        return any(contains_standing_authority_marker(child) for child in value)
    return False


def collect_non_authorizing_passive_status_authority_artifacts(
    value: Any,
    *,
    trail: str = "$",
) -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if PASSIVE_STATUS_ARTIFACT_RE.search(str(key)) and contains_standing_authority_marker(child):
                matches.append(child_trail)
            matches.extend(
                collect_non_authorizing_passive_status_authority_artifacts(
                    child,
                    trail=child_trail,
                )
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            matches.extend(
                collect_non_authorizing_passive_status_authority_artifacts(
                    child,
                    trail=f"{trail}[{index}]",
                )
            )
    return matches


def get_by_normalized_key(value: dict[str, Any], name: str) -> Any:
    for key, child in value.items():
        if normalized_claim_key(key) == name:
            return child
    return None


def normalized_scalar_sequence(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        if not value.strip():
            return []
        return [part.strip() for part in re.split(r"[, ]+", value.strip()) if part.strip()]
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value]
    return [str(value).strip()]


def copied_event_shape(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    target = None
    for key_name in ("target", "function", "ufunction"):
        candidate = get_by_normalized_key(value, key_name)
        if isinstance(candidate, str):
            target = candidate
            break
    if target in HANDLE_NEW_PLAYER_TARGETS:
        target = HANDLE_NEW_PLAYER_FUNCTION
    elif target in CHECK_JOIN_IN_PROGRESS_TARGETS:
        target = CHECK_JOIN_IN_PROGRESS_FUNCTION
    elif target in ON_LOGOUT_TARGETS:
        target = ON_LOGOUT_FUNCTION
    else:
        return None
    role = None
    for key_name in ("role", "event", "lifecycle_event_role"):
        candidate = get_by_normalized_key(value, key_name)
        if isinstance(candidate, str):
            role = normalized_claim_key(candidate)
            break
    copied_fields = get_by_normalized_key(value, "copied_bool_fields")
    copied_values = get_by_normalized_key(value, "copied_bool_values")
    has_copied_bool_shape = copied_fields is not None or copied_values is not None
    if not has_copied_bool_shape and role not in EXPECTED_COPIED_BOOL_SHAPES:
        return None
    return {
        "role": role,
        "target": target,
        "copied_bool_fields": normalized_scalar_sequence(copied_fields),
        "copied_bool_values": normalized_scalar_sequence(copied_values),
        "correlation_status": get_by_normalized_key(value, "correlation_status"),
    }


def copied_event_matches_expected_shape(shape: dict[str, Any]) -> bool:
    role = shape.get("role")
    if role not in EXPECTED_COPIED_BOOL_SHAPES:
        return False
    expected = EXPECTED_COPIED_BOOL_SHAPES[role]
    if shape.get("target") != expected["target"]:
        return False
    if shape.get("copied_bool_fields") != expected["copied_bool_fields"]:
        return False
    if shape.get("copied_bool_values") != expected["copied_bool_values"]:
        return False
    expected_correlation = expected.get("correlation_status")
    if expected_correlation is not None and shape.get("correlation_status") != expected_correlation:
        return False
    return True


def copied_triplet_context(path: str) -> bool:
    tokens = claim_key_tokens(path)
    return (
        "triplet" in tokens
        or {"approved", "evidence"}.issubset(tokens)
        or {"runtime", "evidence"}.issubset(tokens)
        or {"copied", "lifecycle"}.issubset(tokens)
    )


def copied_triplet_shapes_blocked(shapes: list[dict[str, Any]], *, path: str) -> bool:
    if not shapes:
        return False
    if len(shapes) < 2 and not copied_triplet_context(path):
        return False
    by_role = {
        shape.get("role"): shape
        for shape in shapes
        if isinstance(shape.get("role"), str)
    }
    if set(EXPECTED_COPIED_BOOL_SHAPES) - set(by_role):
        return True
    return any(not copied_event_matches_expected_shape(by_role[role]) for role in EXPECTED_COPIED_BOOL_SHAPES)


def check_join_copied_bool_shape_mismatch(value: Any) -> bool:
    shape = copied_event_shape(value)
    if shape is None or shape.get("target") != CHECK_JOIN_IN_PROGRESS_FUNCTION:
        return False
    return (
        shape.get("copied_bool_fields") != ["bIsFromLogin", "ReturnValue"]
        or shape.get("copied_bool_values") != ["1", "0"]
    )


def triplet_blocker_value(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    tokens = claim_key_tokens(value)
    if "triplet" not in tokens:
        return False
    return bool(tokens & {"blocked", "blocker", "invalid", "incomplete", "mismatch", "missing", "without"})


def collect_triplet_blocker_values(value: Any, trail: str) -> list[str]:
    matches: list[str] = []
    if triplet_blocker_value(value):
        matches.append(trail)
    elif isinstance(value, dict):
        for key, child in value.items():
            matches.extend(collect_triplet_blocker_values(child, f"{trail}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            matches.extend(collect_triplet_blocker_values(child, f"{trail}[{index}]"))
    return matches


def blocker_key(key: object) -> bool:
    tokens = claim_key_tokens(str(key))
    return "blocker" in tokens or "blockers" in tokens


def start_end_only_runtime_evidence_active(value: Any, trail: str) -> bool:
    if not isinstance(value, dict):
        return False
    normalized_path = normalized_claim_key(trail)
    if (
        value.get("schema") != START_END_ONLY_RUNTIME_EVIDENCE_SCHEMA
        and value.get("ready_scope") != START_END_ONLY_READY_SCOPE
        and "principal_start_end_runtime_evidence" not in normalized_path
    ):
        return False
    resolved_inputs = value.get("resolved_inputs")
    return (
        value.get("source_present") is True
        or value.get("provided") is True
        or value.get("accepted_for_contract_review") is True
        or value.get("principal_start_end_runtime_evidence_present") is True
        or value.get("principal_start_end_runtime_evidence_ready") is True
        or value.get("ready") is True
        or (
            isinstance(resolved_inputs, list)
            and START_END_ONLY_RESOLVED_INPUT in resolved_inputs
        )
    )


def approval_artifact_key(key: object) -> bool:
    tokens = claim_key_tokens(str(key))
    return (
        "receipt" in tokens
        or "attestation" in tokens
        or {"approval", "artifact"}.issubset(tokens)
        or {"approval", "report"}.issubset(tokens)
        or {"approval", "receipt"}.issubset(tokens)
        or {"approval", "scope"}.issubset(tokens)
        or {"current", "turn", "approval"}.issubset(tokens)
        or {"standing", "launch", "authority"}.issubset(tokens)
        or {"standing", "debug", "authority"}.issubset(tokens)
    )


def approval_artifact_context(value: Any, trail: str) -> bool:
    if approval_artifact_key(trail):
        return True
    if not isinstance(value, dict):
        return False
    normalized_keys = {normalized_claim_key(key) for key in value}
    return bool(
        normalized_keys
        & {
            "approval_source",
            "attestation",
            "approval_recorded_at_utc",
            "standing_launch_authority_recorded",
            "current_turn_approval_recorded",
        }
    )


def approval_artifact_claim_key(key: object) -> bool:
    normalized = normalized_claim_key(key)
    if normalized in NOTICE_NEGATIVE_POLICY_TRUE_KEYS:
        return False
    if normalized in NORMALIZED_FORBIDDEN_FALSE_CLAIM_KEYS:
        return True
    if normalized in NORMALIZED_FORBIDDEN_NONZERO_PROGRESS_KEYS:
        return True
    tokens = claim_key_tokens(str(key))
    if {"non", "progress", "boundary"}.issubset(tokens):
        return False
    if "progress" in tokens:
        return True
    if "counts" in tokens and tokens & {"complete", "completion", "evidence", "p0", "public", "runtime", "sdk", "v1"}:
        return True
    if "evidence" in tokens and tokens & {"accepted", "approved", "present", "ready", "readiness", "runtime", "sdk"}:
        return True
    if tokens & {"p0", "public", "runtime", "sdk", "v1"} and tokens & CLAIM_COMPLETION_TOKENS:
        return True
    if "readiness" in tokens:
        return True
    return False


def collect_activation_evidence_contract_violations(
    value: Any,
    *,
    trail: str = "$",
    approval_context: bool = False,
) -> list[tuple[str, str]]:
    matches: list[tuple[str, str]] = []
    if isinstance(value, dict):
        local_approval_context = approval_context or approval_artifact_context(value, trail)
        if start_end_only_runtime_evidence_active(value, trail):
            matches.append(("start_end_only_runtime_evidence_not_activation_ready", trail))
        if check_join_copied_bool_shape_mismatch(value):
            matches.append(("copied_check_join_in_progress_bool_shape_mismatch", trail))

        child_shapes = [copied_event_shape(child) for child in value.values()]
        direct_shapes = [shape for shape in child_shapes if shape is not None]
        if copied_triplet_shapes_blocked(direct_shapes, path=trail):
            matches.append(("copied_lifecycle_triplet_shape_mismatch", trail))

        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            child_approval_context = local_approval_context or approval_artifact_key(key)
            if blocker_key(key):
                for blocker_path in collect_triplet_blocker_values(child, child_trail):
                    matches.append(("exact_copied_triplet_blocker_present", blocker_path))
            if (
                child_approval_context
                and approval_artifact_claim_key(key)
                and positive_claim_alias_value(child)
            ):
                matches.append(("approval_artifact_claims_evidence_progress_or_readiness", child_trail))
            matches.extend(
                collect_activation_evidence_contract_violations(
                    child,
                    trail=child_trail,
                    approval_context=child_approval_context,
                )
            )
    elif isinstance(value, list):
        direct_shapes = [copied_event_shape(child) for child in value]
        direct_shapes = [shape for shape in direct_shapes if shape is not None]
        if copied_triplet_shapes_blocked(direct_shapes, path=trail):
            matches.append(("copied_lifecycle_triplet_shape_mismatch", trail))
        for index, child in enumerate(value):
            child_trail = f"{trail}[{index}]"
            matches.extend(
                collect_activation_evidence_contract_violations(
                    child,
                    trail=child_trail,
                    approval_context=approval_context,
                )
            )
    return matches


def add_activation_evidence_contract_blockers(
    value: Any,
    blockers: list[str],
    *,
    prefix: str,
) -> None:
    for reason, path in collect_activation_evidence_contract_violations(value):
        add(blockers, f"{prefix}_{reason}:{path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-json", required=True, type=Path, help="Offline window-request.json.")
    parser.add_argument(
        "--request-check-json",
        required=True,
        type=Path,
        help="JSON output from check_player_principal_lifecycle_window_request.py.",
    )
    parser.add_argument(
        "--notice-report-json",
        required=True,
        type=Path,
        help="JSON output from prepare_player_principal_lifecycle_beta_notice.py.",
    )
    parser.add_argument(
        "--route-gate-json",
        required=True,
        type=Path,
        help="JSON output from check_command_permission_route_gate.py.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    return parser.parse_args()


def read_json(path: Path, label: str) -> tuple[dict[str, Any], Path, str]:
    protected_paths.reject_symlink_component(path, label)
    resolved = protected_paths.reject_protected_input_path(
        path.expanduser(),
        label,
        protected_root=SERVER_ROOT,
        approved_roots=protected_paths.approved_offline_workspace_roots(),
    )
    try:
        raw = resolved.read_bytes()
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} must contain a JSON object")
    return payload, resolved, hashlib.sha256(raw).hexdigest()


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def canonical_json_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def add(blockers: list[str], reason: str) -> None:
    if reason not in blockers:
        blockers.append(reason)


def collect_forbidden_route_gate_claims(value: Any, trail: str = "$") -> list[str]:
    return collect_forbidden_claim_aliases(
        value,
        allowed_positive_paths=ROUTE_GATE_ALLOWED_POSITIVE_CLAIM_PATHS
        | {
            "$.checks[*].accepted_for_planning",
            "$.checks[*].counts_toward_public_sdk",
            "$.checks[*].counts_toward_runtime",
            "$.checks[*].counts_toward_v1_completion",
            "$.checks[*].name",
            "$.checks[*].public_or_runtime_accounting_allowed",
            "$.post_evidence_p0_lock_simulation.p0_child_checks[*].name",
        },
        trail=trail,
    )


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or UTC_RE.fullmatch(value) is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def expected_env_snapshot(request: dict[str, Any], target: dict[str, str]) -> list[str] | None:
    sha = request.get("ark_binary_sha256")
    if not isinstance(sha, str):
        return None
    values = {
        "OBELISK_INSTANCE_ID": target["instance"],
        **REQUIRED_ENV,
        "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256": sha,
    }
    if diagnostic_candidates_enabled(request):
        values[DIAGNOSTIC_CANDIDATES_ENV_KEY] = "1"
    try:
        return [f"{key}={values[key]}" for key in observer_env_keys(request)]
    except KeyError:
        return None


def diagnostic_candidates_for_approved_evidence_policy(
    request: dict[str, Any],
    *,
    observer_env_contains_diagnostic_candidates: bool | None = None,
    observer_env_diagnostic_keys_present: list[str] | None = None,
) -> dict[str, Any]:
    request_explicitly_disabled = request.get("diagnostic_candidates_enabled") is False
    request_enabled = request.get("diagnostic_candidates_enabled") is True
    diagnostic_keys_present = sorted(observer_env_diagnostic_keys_present or [])
    blockers: list[str] = []
    if request_enabled:
        add(blockers, DIAGNOSTIC_CANDIDATES_APPROVED_EVIDENCE_BLOCKER)
    elif not request_explicitly_disabled:
        add(blockers, DIAGNOSTIC_CANDIDATES_NOT_EXPLICITLY_DISABLED_BLOCKER)
    if observer_env_contains_diagnostic_candidates is True:
        add(blockers, OBSERVER_ENV_DIAGNOSTIC_CANDIDATES_BLOCKER)
    if diagnostic_keys_present:
        add(blockers, OBSERVER_ENV_DIAGNOSTIC_KEYS_BLOCKER)
    return {
        "schema": DIAGNOSTIC_CANDIDATES_APPROVED_EVIDENCE_POLICY_SCHEMA,
        "diagnostic_env_key": DIAGNOSTIC_CANDIDATES_ENV_KEY,
        "diagnostic_env_keys": list(DIAGNOSTIC_APPROVED_EVIDENCE_ENV_KEYS),
        "request_field": "diagnostic_candidates_enabled",
        "request_explicitly_disabled": request_explicitly_disabled,
        "request_enabled": request_enabled,
        "observer_env_contains_diagnostic_candidates": observer_env_contains_diagnostic_candidates,
        "observer_env_diagnostic_keys_present": diagnostic_keys_present,
        "approved_evidence_window_rejected": bool(blockers),
        "approved_evidence_blockers": blockers,
        "approved_evidence_requires_explicit_disable": True,
        "diagnostic_candidate_lines_are_debug_only": True,
        "diagnostic_route_sample_lines_are_debug_only": True,
        "diagnostic_candidate_lines_promotable_for_approved_evidence": False,
        "diagnostic_route_sample_lines_promotable_for_approved_evidence": False,
        "source_log_contains_lifecycle_diagnostic_lines_blocks_approved_evidence": True,
        "observer_env_diagnostic_keys_block_approved_evidence": True,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_claim_allowed": False,
        "non_authorization": DIAGNOSTIC_CANDIDATES_APPROVED_EVIDENCE_NON_AUTHORIZATION,
    }


def observer_env_contains_diagnostic_candidates(path: Path, blockers: list[str]) -> bool | None:
    present = observer_env_diagnostic_keys_present(path, blockers)
    if present is None:
        return None
    return DIAGNOSTIC_CANDIDATES_ENV_KEY in present


def observer_env_diagnostic_keys_present(path: Path, blockers: list[str]) -> list[str] | None:
    if not path.exists() or not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        add(blockers, "observer_env_unreadable_for_diagnostic_candidate_check")
        return None
    present: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in DIAGNOSTIC_APPROVED_EVIDENCE_ENV_KEYS:
            add(present, key)
    return present


def validate_diagnostic_candidates_for_approved_evidence(
    request: dict[str, Any],
    blockers: list[str],
    *,
    request_path: Path | None = None,
) -> dict[str, Any]:
    observer_env_contains = None
    if request_path is not None:
        observer_env_path = request_path.parent / "observer-window.env"
        observer_env_contains = observer_env_contains_diagnostic_candidates(
            observer_env_path,
            blockers,
        )
        observer_env_diagnostic_keys = observer_env_diagnostic_keys_present(
            observer_env_path,
            blockers,
        )
    else:
        observer_env_diagnostic_keys = None
    policy = diagnostic_candidates_for_approved_evidence_policy(
        request,
        observer_env_contains_diagnostic_candidates=observer_env_contains,
        observer_env_diagnostic_keys_present=observer_env_diagnostic_keys,
    )
    for blocker in policy["approved_evidence_blockers"]:
        add(blockers, str(blocker))
    return policy


def validate_authorization_flags(request: dict[str, Any], blockers: list[str]) -> None:
    flags = request.get("authorization_flags")
    if not isinstance(flags, dict):
        add(blockers, "request_authorization_flags_missing")
        return
    if flags != AUTHORIZATION_FLAGS:
        add(blockers, "request_authorization_flags_mismatch")
    for key in AUTHORIZATION_FLAGS:
        if flags.get(key) is not False:
            add(blockers, f"request_authorization_flag_{key}_not_false")


def validate_request_window(
    request: dict[str, Any],
    blockers: list[str],
) -> tuple[datetime | None, datetime | None, datetime | None]:
    prepared_at = parse_utc(request.get("prepared_at_utc"))
    if prepared_at is None:
        add(blockers, "request_prepared_at_utc_invalid")
    window = request.get("approved_window")
    if not isinstance(window, dict):
        add(blockers, "request_approved_window_missing")
        return prepared_at, None, None
    start = parse_utc(window.get("start_utc"))
    end = parse_utc(window.get("end_utc"))
    if start is None:
        add(blockers, "request_approved_window_start_utc_invalid")
    if end is None:
        add(blockers, "request_approved_window_end_utc_invalid")
    if start is not None and end is not None:
        if not start < end:
            add(blockers, "request_approved_window_order_invalid")
        else:
            duration_seconds = int((end - start).total_seconds())
            if duration_seconds > MAX_APPROVED_WINDOW_SECONDS:
                add(blockers, "request_approved_window_duration_too_long")
            if duration_seconds < MIN_APPROVED_WINDOW_SECONDS:
                add(blockers, "request_approved_window_duration_too_short")
    now = datetime.now(timezone.utc)
    if start is not None and start <= now:
        add(blockers, "request_approved_window_already_started_or_stale")
    if end is not None and end <= now:
        add(blockers, "request_approved_window_expired")
    if prepared_at is not None and start is not None:
        if prepared_at >= start:
            add(blockers, "request_prepared_at_not_before_window")
        elif (start - prepared_at).total_seconds() > MAX_REQUEST_PREPARATION_LEAD_SECONDS:
            add(blockers, "request_prepared_at_too_far_before_window")
    run_id = request.get("run_id")
    if not isinstance(run_id, str) or RUN_ID_RE.fullmatch(run_id) is None:
        add(blockers, "request_run_id_invalid")
    elif start is not None and run_id != run_id_for_window_start(start):
        add(blockers, "request_run_id_window_start_mismatch")
    return prepared_at, start, end


def validate_exact_target_scope(
    request: dict[str, Any],
    blockers: list[str],
    target: dict[str, str] | None,
) -> None:
    if target is None:
        return
    for key in ("instance", "map"):
        value = target.get(key)
        if not isinstance(value, str) or SAFE_TOKEN_RE.fullmatch(value) is None:
            add(blockers, f"request_target_{key}_invalid")
        elif is_forbidden_flow_alias(value):
            add(blockers, f"request_target_{key}_alias_not_exact")

    scope = request.get("exact_target_scope")
    if not isinstance(scope, dict):
        add(blockers, "request_exact_target_scope_missing")
        scope = None
    else:
        missing = EXPECTED_EXACT_TARGET_SCOPE_KEYS - set(scope)
        unexpected = set(scope) - EXPECTED_EXACT_TARGET_SCOPE_KEYS
        if missing:
            add(blockers, "request_exact_target_scope_missing_required")
        if unexpected:
            add(blockers, "request_exact_target_scope_unexpected_keys")
        if scope.get("schema") != EXACT_TARGET_SCOPE_SCHEMA:
            add(blockers, "request_exact_target_scope_schema_mismatch")
        if scope.get("instance") != target.get("instance"):
            add(blockers, "request_exact_target_scope_instance_mismatch")
        if scope.get("map") != target.get("map"):
            add(blockers, "request_exact_target_scope_map_mismatch")
        for key in ("instance_alias_allowed", "map_alias_allowed"):
            if scope.get(key) is not False:
                add(blockers, f"request_exact_target_scope_{key}_not_false")
        for key in ("approval_must_name_exact_instance_and_map", "target_matches_request_target"):
            if scope.get(key) is not True:
                add(blockers, f"request_exact_target_scope_{key}_not_true")
        if scope.get("non_authorization") != EXACT_TARGET_SCOPE_NON_AUTHORIZATION:
            add(blockers, "request_exact_target_scope_non_authorization_mismatch")

    approval_scope = request.get("current_turn_approval_scope")
    named_scope = approval_scope.get("required_named_scope") if isinstance(approval_scope, dict) else None
    if isinstance(named_scope, dict) and named_scope.get("exact_target_instance_map") != scope:
        add(blockers, "request_current_turn_approval_exact_target_scope_mismatch")


def validate_marker_env_scope(
    request: dict[str, Any],
    blockers: list[str],
    target: dict[str, str] | None,
) -> None:
    if request.get("marker_set") != WINDOW_MARKERS:
        add(blockers, "request_marker_set_mismatch")
    if request.get("forbidden_markers") != FORBIDDEN_MARKERS:
        add(blockers, "request_forbidden_markers_mismatch")
    scope = request.get("current_turn_approval_scope")
    if not isinstance(scope, dict):
        add(blockers, "request_current_turn_approval_scope_missing")
        return
    if scope.get("schema") != APPROVAL_SCOPE_SCHEMA:
        add(blockers, "request_current_turn_approval_scope_schema_mismatch")
    standing_scope = scope.get("source_required") == APPROVAL_SCOPE_SOURCE_REQUIRED_STANDING_LAUNCH_AUTHORITY
    expected_status = APPROVAL_SCOPE_STATUS_STANDING_LAUNCH_AUTHORITY if standing_scope else APPROVAL_SCOPE_STATUS
    expected_source = (
        APPROVAL_SCOPE_SOURCE_REQUIRED_STANDING_LAUNCH_AUTHORITY
        if standing_scope
        else APPROVAL_SCOPE_SOURCE_REQUIRED
    )
    expected_standing_allowed = standing_scope
    if scope.get("status") != expected_status:
        add(blockers, "request_current_turn_approval_scope_status_mismatch")
    if scope.get("source_required") != expected_source:
        add(blockers, "request_current_turn_approval_scope_source_mismatch")
    if expected_standing_allowed is False and scope.get("standing_approval_allowed") is not False:
        add(blockers, "request_current_turn_approval_scope_standing_approval_not_false")
    elif expected_standing_allowed is True and scope.get("standing_approval_allowed") is not True:
        add(blockers, "request_current_turn_approval_scope_standing_approval_not_true")
    if scope.get("request_pack_authorizes_deploy_or_runtime") is not False:
        add(blockers, "request_current_turn_approval_scope_authorizes_runtime_not_false")
    if scope.get("required_operator_approval_fields") != CURRENT_TURN_APPROVAL_REQUIRED_FIELDS:
        add(blockers, "request_current_turn_approval_scope_required_fields_mismatch")
    named_scope = scope.get("required_named_scope")
    if not isinstance(named_scope, dict):
        add(blockers, "request_current_turn_approval_named_scope_missing")
        return
    if target is not None and named_scope.get("target") != target:
        add(blockers, "request_current_turn_approval_target_mismatch")
    if named_scope.get("final_posture") != "stable":
        add(blockers, "request_current_turn_approval_final_posture_not_stable")
    gates = named_scope.get("marker_env_gates")
    if not isinstance(gates, dict):
        add(blockers, "request_current_turn_approval_marker_env_gates_missing")
        return
    if gates.get("markers") != WINDOW_MARKERS:
        add(blockers, "request_current_turn_approval_markers_mismatch")
    env_snapshot = gates.get("env_snapshot")
    if not isinstance(env_snapshot, list) or not all(isinstance(item, str) for item in env_snapshot):
        add(blockers, "request_current_turn_approval_env_snapshot_invalid")
        return
    expected_env = expected_env_snapshot(request, target) if target is not None else None
    if expected_env is None or env_snapshot != expected_env:
        add(blockers, "request_current_turn_approval_env_snapshot_mismatch")
    expected_keys = tuple(observer_env_keys(request))
    observed_keys = tuple(line.split("=", 1)[0] for line in env_snapshot if "=" in line)
    if observed_keys != expected_keys:
        add(blockers, "request_current_turn_approval_env_exclusivity_mismatch")
    forbidden_env_keys = {
        "OBELISK_ENABLE_REFLECTION_SCANNER",
        "OBELISK_ENABLE_NATIVE_EXEC_PROBES",
        "OBELISK_ENABLE_DEBUG_CONTROL",
        "OBELISK_DEBUG_ALLOW_PTRACE",
    }
    if any(line.split("=", 1)[0] in forbidden_env_keys for line in env_snapshot if "=" in line):
        add(blockers, "request_current_turn_approval_forbidden_env_present")


def validate_player_presence_safety(
    request: dict[str, Any],
    blockers: list[str],
    target: dict[str, str] | None,
) -> None:
    safety = request.get("player_presence_safety")
    if not isinstance(safety, dict):
        add(blockers, "player_presence_safety_missing")
        return
    if safety.get("schema") != PLAYER_PRESENCE_SAFETY_SCHEMA:
        add(blockers, "player_presence_safety_schema_mismatch")
    if target is not None and safety.get("target") != target:
        add(blockers, "player_presence_safety_target_mismatch")
    if safety.get("restart_expectation") != request.get("restart_expectation"):
        add(blockers, "player_presence_safety_restart_expectation_mismatch")

    restart_requested = request.get("restart_expectation") == "restart"
    for key in (
        "connected_player_check_required_before_restart",
        "rcon_broadcast_required_if_players_connected",
        "restart_must_be_cancelled_or_rescheduled_if_players_remain_connected",
    ):
        if safety.get(key) is not restart_requested:
            add(blockers, f"player_presence_safety_{key}_mismatch")
    if safety.get("passive_wait_preferred_after_activation") is not True:
        add(blockers, "player_presence_safety_passive_wait_preferred_after_activation_not_true")
    if safety.get("linuxgsm_monitor_forbidden") is not True:
        add(blockers, "player_presence_safety_linuxgsm_monitor_forbidden_not_true")
    if safety.get("player_check_or_broadcast_authorized_by_request_pack") is not False:
        add(blockers, "player_presence_safety_player_check_or_broadcast_authorized_by_request_pack_not_false")
    if safety.get("non_authorization") != PLAYER_PRESENCE_SAFETY_NON_AUTHORIZATION:
        add(blockers, "player_presence_safety_non_authorization_mismatch")

    scope = request.get("current_turn_approval_scope")
    named_scope = scope.get("required_named_scope") if isinstance(scope, dict) else None
    if isinstance(named_scope, dict) and named_scope.get("player_presence_safety") != safety:
        add(blockers, "request_current_turn_approval_player_presence_safety_mismatch")


def validate_passive_wait_boundary(
    request: dict[str, Any],
    blockers: list[str],
    target: dict[str, str] | None,
) -> None:
    boundary = request.get("passive_wait_boundary")
    if not isinstance(boundary, dict):
        add(blockers, "passive_wait_boundary_missing")
        return
    if boundary.get("schema") != PASSIVE_WAIT_BOUNDARY_SCHEMA:
        add(blockers, "passive_wait_boundary_schema_mismatch")
    if target is not None and boundary.get("target") != target:
        add(blockers, "passive_wait_boundary_target_mismatch")
    expected_wait_seconds = requested_wait_window_seconds(request)
    wait_seconds = boundary.get("requested_wait_window_seconds")
    if not isinstance(wait_seconds, int):
        add(blockers, "passive_wait_boundary_requested_wait_window_seconds_not_int")
    elif wait_seconds != expected_wait_seconds:
        add(blockers, "passive_wait_boundary_requested_wait_window_seconds_mismatch")
    if isinstance(wait_seconds, int) and wait_seconds > MAX_APPROVED_WINDOW_SECONDS:
        add(blockers, "passive_wait_boundary_requested_wait_window_seconds_too_long")
    if boundary.get("max_requested_wait_window_seconds") != MAX_APPROVED_WINDOW_SECONDS:
        add(blockers, "passive_wait_boundary_max_requested_wait_window_seconds_mismatch")
    if boundary.get("requested_wait_window_seconds_checked_only") is not True:
        add(blockers, "passive_wait_boundary_requested_wait_window_seconds_checked_only_not_true")
    for key in (
        "requested_wait_window_authorizes_current_turn_approval",
        "requested_wait_window_authorizes_deploy_or_restart",
        "requested_wait_window_authorizes_runtime_capture",
        "requested_wait_window_counts_as_approved_runtime_evidence",
        "wait_only_or_passive_monitor_authorizes_deploy_or_restart",
        "passive_monitor_ticks_authorize_runtime_capture",
        "player_presence_detection_authorizes_followup",
        "snapshots_or_diagnostics_count_as_approved_runtime_evidence",
    ):
        if boundary.get(key) is not False:
            add(blockers, f"passive_wait_boundary_{key}_not_false")
    scope = request.get("current_turn_approval_scope")
    standing_scope = (
        isinstance(scope, dict)
        and scope.get("source_required") == APPROVAL_SCOPE_SOURCE_REQUIRED_STANDING_LAUNCH_AUTHORITY
    )
    if boundary.get("active_followup_requires_fresh_exact_current_turn_scope") is not (not standing_scope):
        add(blockers, "passive_wait_boundary_active_followup_requires_fresh_exact_current_turn_scope_mismatch")
    if boundary.get("active_followup_requires_recorded_standing_launch_authority") is not standing_scope:
        add(blockers, "passive_wait_boundary_active_followup_requires_recorded_standing_launch_authority_mismatch")
    if boundary.get("non_authorization") != PASSIVE_WAIT_BOUNDARY_NON_AUTHORIZATION:
        add(blockers, "passive_wait_boundary_non_authorization_mismatch")

    named_scope = scope.get("required_named_scope") if isinstance(scope, dict) else None
    if isinstance(named_scope, dict) and named_scope.get("passive_wait_boundary") != boundary:
        add(blockers, "request_current_turn_approval_passive_wait_boundary_mismatch")


def validate_direct_join_plan(
    request: dict[str, Any],
    blockers: list[str],
    target: dict[str, str] | None,
) -> None:
    plan = request.get("direct_join_plan")
    if not isinstance(plan, dict):
        add(blockers, "request_direct_join_plan_missing")
        return
    missing = EXPECTED_DIRECT_JOIN_PLAN_KEYS - set(plan)
    unexpected = set(plan) - EXPECTED_DIRECT_JOIN_PLAN_KEYS
    if missing:
        add(blockers, "request_direct_join_plan_missing_required")
    if unexpected:
        add(blockers, "request_direct_join_plan_unexpected_keys")
    if plan.get("schema") != DIRECT_JOIN_PLAN_SCHEMA:
        add(blockers, "request_direct_join_plan_schema_mismatch")
    if target is not None and plan.get("target") != target:
        add(blockers, "request_direct_join_plan_target_mismatch")
    if target is not None:
        if plan.get("target_instance") != target.get("instance"):
            add(blockers, "request_direct_join_plan_target_instance_mismatch")
        if plan.get("target_map") != target.get("map"):
            add(blockers, "request_direct_join_plan_target_map_mismatch")
        target_is_theisland = target.get("map") == "TheIsland"
        for key in ("target_map_is_theisland", "fastest_clean_theisland_direct_join"):
            if plan.get(key) is not target_is_theisland:
                add(blockers, f"request_direct_join_plan_{key}_mismatch")
    if plan.get("route") != "direct_join_exact_server_map":
        add(blockers, "request_direct_join_plan_route_mismatch")
    if plan.get("direct_join_required") is not True:
        add(blockers, "request_direct_join_plan_direct_join_required_not_true")
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
            add(blockers, f"request_direct_join_plan_{key}_not_false")
    if plan.get("max_running_ark_servers") != 2:
        add(blockers, "request_direct_join_plan_max_running_ark_servers_mismatch")
    if plan.get("approved_notice_path") != request.get("notice_path"):
        add(blockers, "request_direct_join_plan_approved_notice_path_mismatch")
    wait_seconds = requested_wait_window_seconds(request)
    if plan.get("organic_wait_window_seconds") != wait_seconds:
        add(blockers, "request_direct_join_plan_organic_wait_window_seconds_mismatch")
    if plan.get("max_organic_wait_window_seconds") != MAX_APPROVED_WINDOW_SECONDS:
        add(blockers, "request_direct_join_plan_max_organic_wait_window_seconds_mismatch")
    for key in ("receipt_before_activation_required", "post_window_replay_requires_receipt"):
        if plan.get(key) is not True:
            add(blockers, f"request_direct_join_plan_{key}_not_true")
    if plan.get("non_authorization") != DIRECT_JOIN_PLAN_NON_AUTHORIZATION:
        add(blockers, "request_direct_join_plan_non_authorization_mismatch")
    try:
        expected = direct_join_plan(request)
    except (KeyError, TypeError):
        expected = None
    if expected is not None and plan != expected:
        add(blockers, "request_direct_join_plan_mismatch")
    scope = request.get("current_turn_approval_scope")
    named_scope = scope.get("required_named_scope") if isinstance(scope, dict) else None
    if isinstance(named_scope, dict) and named_scope.get("direct_join_plan") != plan:
        add(blockers, "request_current_turn_approval_direct_join_plan_mismatch")


def validate_runtime_triplet_contract(request: dict[str, Any], blockers: list[str]) -> None:
    contract = request.get("runtime_triplet_contract")
    if not isinstance(contract, dict):
        add(blockers, "request_runtime_triplet_contract_missing")
        return
    missing = EXPECTED_RUNTIME_TRIPLET_CONTRACT_KEYS - set(contract)
    unexpected = set(contract) - EXPECTED_RUNTIME_TRIPLET_CONTRACT_KEYS
    if missing:
        add(blockers, "request_runtime_triplet_contract_missing_required")
    if unexpected:
        add(blockers, "request_runtime_triplet_contract_unexpected_keys")
    session_start = contract.get("session_start_rejected")
    if not isinstance(session_start, dict):
        add(blockers, "request_runtime_triplet_contract_session_start_missing")
    else:
        if EXPECTED_RUNTIME_TRIPLET_SESSION_START_KEYS - set(session_start):
            add(blockers, "request_runtime_triplet_contract_session_start_missing_required")
        if set(session_start) - EXPECTED_RUNTIME_TRIPLET_SESSION_START_KEYS:
            add(blockers, "request_runtime_triplet_contract_session_start_unexpected_keys")
        if session_start.get("event") != "session_start_rejected":
            add(blockers, "request_runtime_triplet_contract_session_start_event_mismatch")
        if session_start.get("required_function") != SESSION_START_REJECTED_REQUIRED_FUNCTION:
            add(blockers, "request_runtime_triplet_contract_session_start_function_mismatch")
        if session_start.get("required_argument_tuple") != SESSION_START_REJECTED_REQUIRED_ARGUMENTS:
            add(blockers, "request_runtime_triplet_contract_session_start_argument_tuple_mismatch")
        if session_start.get("required_call") != SESSION_START_REJECTED_REQUIRED_CALL:
            add(blockers, "request_runtime_triplet_contract_session_start_required_call_mismatch")
        if session_start.get("required_copied_bool_fields") != ["bIsFromLogin", "ReturnValue"]:
            add(blockers, "request_runtime_triplet_contract_session_start_copied_bool_fields_mismatch")
        if normalized_scalar_sequence(session_start.get("required_copied_bool_values")) != ["1", "0"]:
            add(blockers, "request_runtime_triplet_contract_session_start_copied_bool_values_mismatch")
        for key in (
            "handle_new_player_rejected_tuple_allowed",
            "handle_new_player_rejected_tuple_alternative_allowed",
        ):
            if session_start.get(key) is not False:
                add(blockers, f"request_runtime_triplet_contract_session_start_{key}_not_false")
    handle_new_player = contract.get("handle_new_player_rejected_tuples")
    if not isinstance(handle_new_player, dict):
        add(blockers, "request_runtime_triplet_contract_handle_new_player_missing")
    else:
        if EXPECTED_RUNTIME_TRIPLET_HANDLE_NEW_PLAYER_KEYS - set(handle_new_player):
            add(blockers, "request_runtime_triplet_contract_handle_new_player_missing_required")
        if set(handle_new_player) - EXPECTED_RUNTIME_TRIPLET_HANDLE_NEW_PLAYER_KEYS:
            add(blockers, "request_runtime_triplet_contract_handle_new_player_unexpected_keys")
        if handle_new_player.get("function") != HANDLE_NEW_PLAYER_FUNCTION:
            add(blockers, "request_runtime_triplet_contract_handle_new_player_function_mismatch")
        for key in ("allowed_for_session_start_rejected", "alternative_for_session_start_rejected"):
            if handle_new_player.get(key) is not False:
                add(blockers, f"request_runtime_triplet_contract_handle_new_player_{key}_not_false")
        if handle_new_player.get("classification") != "stale_rejected_start_rule_only":
            add(blockers, "request_runtime_triplet_contract_handle_new_player_classification_mismatch")
    if contract.get("schema") != RUNTIME_TRIPLET_CONTRACT_SCHEMA:
        add(blockers, "request_runtime_triplet_contract_schema_mismatch")
    if contract.get("planning_only") is not True:
        add(blockers, "request_runtime_triplet_contract_planning_only_not_true")
    if contract.get("non_authorization") != RUNTIME_TRIPLET_CONTRACT_NON_AUTHORIZATION:
        add(blockers, "request_runtime_triplet_contract_non_authorization_mismatch")
    if contract != runtime_triplet_contract():
        add(blockers, "request_runtime_triplet_contract_mismatch")
    for path in collect_stale_handle_new_player_rejected_start_rules(contract):
        add(blockers, f"request_stale_handle_new_player_rejected_start_rule:{path}")
    scope = request.get("current_turn_approval_scope")
    named_scope = scope.get("required_named_scope") if isinstance(scope, dict) else None
    if isinstance(named_scope, dict) and named_scope.get("runtime_triplet_contract") != contract:
        add(blockers, "request_current_turn_approval_runtime_triplet_contract_mismatch")


def request_identity(request: dict[str, Any]) -> tuple[dict[str, str] | None, str | None]:
    target = request.get("target")
    run_id = request.get("run_id")
    if not isinstance(target, dict) or not isinstance(target.get("instance"), str) or not isinstance(target.get("map"), str):
        return None, run_id if isinstance(run_id, str) else None
    return {"instance": target["instance"], "map": target["map"]}, run_id if isinstance(run_id, str) else None


def request_standing_launch_authority_requirement(request: dict[str, Any]) -> bool | None:
    scope = request.get("current_turn_approval_scope")
    if not isinstance(scope, dict):
        return None
    source = scope.get("source_required")
    if source == APPROVAL_SCOPE_SOURCE_REQUIRED_STANDING_LAUNCH_AUTHORITY:
        return True
    if source == APPROVAL_SCOPE_SOURCE_REQUIRED:
        return False
    return None


def request_check_records_standing_launch_authority(request_check: dict[str, Any]) -> bool:
    return request_check.get("standing_launch_authority_recorded") is True


def standing_launch_authority_satisfies_activation_scope(
    *,
    ready: bool,
    standing_launch_authority_recorded: bool,
) -> bool:
    return ready and standing_launch_authority_recorded


def validate_request(
    request: dict[str, Any],
    blockers: list[str],
    *,
    request_path: Path | None = None,
) -> tuple[dict[str, str] | None, str | None, dict[str, Any] | None]:
    for claim_path in collect_forbidden_claim_aliases(
        request,
        allowed_positive_paths=REQUEST_ALLOWED_POSITIVE_CLAIM_PATHS,
    ):
        add(blockers, f"request_forbidden_authorization_or_evidence_claim:{claim_path}")
    add_activation_evidence_contract_blockers(request, blockers, prefix="request")
    for stale_path in collect_stale_handle_new_player_rejected_start_rules(request):
        add(blockers, f"request_stale_handle_new_player_rejected_start_rule:{stale_path}")
    if request.get("schema") != WINDOW_REQUEST_SCHEMA:
        add(blockers, "request_schema_mismatch")
    if request.get("status") != "candidate_only_request_pack":
        add(blockers, "request_status_not_candidate_only")
    target, run_id = request_identity(request)
    if target is None:
        add(blockers, "request_target_missing")
    if not run_id:
        add(blockers, "request_run_id_missing")
    validate_diagnostic_candidates_for_approved_evidence(
        request,
        blockers,
        request_path=request_path,
    )
    validate_exact_target_scope(request, blockers, target)
    prepared_at, window_start, window_end = validate_request_window(request, blockers)
    if request.get("ark_binary_sha256") != EXPECTED_BINARY_SHA256:
        add(blockers, "request_ark_binary_sha256_mismatch")
    if request.get("server_binary_path") != EXPECTED_SERVER_BINARY_PATH:
        add(blockers, "request_server_binary_path_mismatch")
    if request.get("restart_expectation") not in ("none", "start", "restart"):
        add(blockers, "request_restart_expectation_invalid")
    if request.get("final_posture") != "stable":
        add(blockers, "request_final_posture_not_stable")
    if request.get("user_policy") != "operator_approved_beta_users":
        add(blockers, "request_user_policy_not_beta_users")
    if request.get("notice_path") != "discord-beta-testers":
        add(blockers, "request_notice_path_not_approved_beta_testers")
    validate_authorization_flags(request, blockers)
    validate_marker_env_scope(request, blockers, target)
    scope = request.get("current_turn_approval_scope")
    action = request.get("player_notice_action")
    if not isinstance(action, dict):
        add(blockers, "player_notice_action_missing")
        validate_player_presence_safety(request, blockers, target)
        return target, run_id, None
    if action.get("schema") != PLAYER_NOTICE_ACTION_SCHEMA:
        add(blockers, "player_notice_action_schema_mismatch")
    expected_booleans = {
        "required": True,
        "approved_notice_path_must_be_named": True,
        "dry_run_required_before_send": True,
        "real_notice_send_required_before_activation": True,
        "send_performed_by_request_pack": False,
        "request_pack_authorizes_discord": False,
        "activation_allowed_before_notice_sent": False,
    }
    for key, expected in expected_booleans.items():
        if action.get(key) is not expected:
            add(blockers, f"player_notice_action_{key}_mismatch")
    if action.get("activation_blocker") != NOTICE_ACTION_BLOCKER:
        add(blockers, "player_notice_action_activation_blocker_mismatch")
    if action.get("evidence_required") != "dry_run_output_and_send_confirmation_reference":
        add(blockers, "player_notice_action_evidence_required_mismatch")
    if action.get("non_authorization") != PLAYER_NOTICE_ACTION_NON_AUTHORIZATION:
        add(blockers, "player_notice_action_non_authorization_mismatch")
    notice_path = action.get("notice_path")
    if notice_path != "discord-beta-testers":
        add(blockers, "player_notice_action_notice_path_not_named")
    if isinstance(scope, dict) and isinstance(scope.get("required_named_scope"), dict):
        if scope["required_named_scope"].get("player_notice_action") != action:
            add(blockers, "request_current_turn_approval_player_notice_action_mismatch")
    validate_player_presence_safety(request, blockers, target)
    validate_passive_wait_boundary(request, blockers, target)
    validate_direct_join_plan(request, blockers, target)
    validate_runtime_triplet_contract(request, blockers)
    restart_scope = None
    if isinstance(scope, dict) and isinstance(scope.get("required_named_scope"), dict):
        restart_scope = scope["required_named_scope"].get("restart_window")
    if isinstance(restart_scope, dict) and window_start is not None and window_end is not None:
        if restart_scope.get("start_utc") != request["approved_window"]["start_utc"]:
            add(blockers, "request_current_turn_approval_restart_window_start_mismatch")
        if restart_scope.get("end_utc") != request["approved_window"]["end_utc"]:
            add(blockers, "request_current_turn_approval_restart_window_end_mismatch")
        if restart_scope.get("expectation") != request.get("restart_expectation"):
            add(blockers, "request_current_turn_approval_restart_expectation_mismatch")
    return target, run_id, action


def validate_report_artifact(
    artifact: Any,
    blockers: list[str],
    *,
    label: str,
    expected_sha256: str | None = None,
    required: bool = True,
) -> None:
    if artifact is None and not required:
        return
    if not isinstance(artifact, dict):
        add(blockers, f"{label}_artifact_missing")
        return
    path = artifact.get("path")
    sha256 = artifact.get("sha256")
    size_bytes = artifact.get("size_bytes")
    if not isinstance(path, str) or not path:
        add(blockers, f"{label}_artifact_path_missing")
    if not isinstance(sha256, str) or re.fullmatch(r"[0-9a-f]{64}", sha256) is None:
        add(blockers, f"{label}_artifact_sha256_invalid")
    elif expected_sha256 is not None and sha256 != expected_sha256:
        add(blockers, f"{label}_artifact_sha256_mismatch")
    if not isinstance(size_bytes, int) or size_bytes < 0:
        add(blockers, f"{label}_artifact_size_bytes_invalid")


def validate_artifact_path_binding(
    artifact: Any,
    blockers: list[str],
    *,
    label: str,
    expected_path: Path,
    base_dir: Path,
) -> None:
    if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str) or not artifact.get("path"):
        return
    path = Path(artifact["path"])
    candidate = path if path.is_absolute() else base_dir / path
    status = protected_paths.protected_path_status(
        candidate,
        protected_root=SERVER_ROOT,
        approved_roots=protected_paths.approved_offline_workspace_roots(),
    )
    if status.protected:
        add(blockers, f"{label}_artifact_path_protected")
    if status.resolved != expected_path:
        add(blockers, f"{label}_artifact_path_mismatch")
    if not status.resolved.exists():
        add(blockers, f"{label}_artifact_file_missing")
    elif not status.resolved.is_file():
        add(blockers, f"{label}_artifact_not_file")


def validate_request_check_bindings(
    request_check: dict[str, Any],
    blockers: list[str],
    *,
    request: dict[str, Any],
    request_path: Path,
    request_sha256: str,
) -> None:
    if request_check.get("prepared_at_utc") != request.get("prepared_at_utc"):
        add(blockers, "request_check_prepared_at_mismatch")
    if request_check.get("approved_window") != request.get("approved_window"):
        add(blockers, "request_check_approved_window_mismatch")
    if request_check.get("restart_expectation") != request.get("restart_expectation"):
        add(blockers, "request_check_restart_expectation_mismatch")
    if request_check.get("final_posture") != request.get("final_posture"):
        add(blockers, "request_check_final_posture_mismatch")
    if request_check.get("user_policy") != request.get("user_policy"):
        add(blockers, "request_check_user_policy_mismatch")
    if request_check.get("notice_path") != request.get("notice_path"):
        add(blockers, "request_check_notice_path_mismatch")
    if request_check.get("direct_join_plan") != request.get("direct_join_plan"):
        add(blockers, "request_check_direct_join_plan_mismatch")
    artifacts = request_check.get("request_pack_artifacts")
    if not isinstance(artifacts, dict):
        add(blockers, "request_check_artifact_bindings_missing")
        return
    validate_report_artifact(
        artifacts.get("window_request_json"),
        blockers,
        label="request_check_window_request_json",
        expected_sha256=request_sha256,
    )
    validate_artifact_path_binding(
        artifacts.get("window_request_json"),
        blockers,
        label="request_check_window_request_json",
        expected_path=request_path,
        base_dir=request_path.parent,
    )
    validate_report_artifact(
        artifacts.get("observer_window_env"),
        blockers,
        label="request_check_observer_window_env",
    )
    validate_artifact_path_binding(
        artifacts.get("observer_window_env"),
        blockers,
        label="request_check_observer_window_env",
        expected_path=request_path.parent / "observer-window.env",
        base_dir=request_path.parent,
    )
    validate_report_artifact(
        artifacts.get("operator_approval_request_md"),
        blockers,
        label="request_check_operator_approval_request_md",
    )
    validate_artifact_path_binding(
        artifacts.get("operator_approval_request_md"),
        blockers,
        label="request_check_operator_approval_request_md",
        expected_path=request_path.parent / "operator-approval-request.md",
        base_dir=request_path.parent,
    )
    validate_report_artifact(
        artifacts.get("operator_approval_receipt_json"),
        blockers,
        label="request_check_operator_approval_receipt_json",
    )
    validate_artifact_path_binding(
        artifacts.get("operator_approval_receipt_json"),
        blockers,
        label="request_check_operator_approval_receipt_json",
        expected_path=request_path.parent / "operator-approval-receipt.json",
        base_dir=request_path.parent,
    )
    digest = request_check.get("request_pack_digest")
    if not isinstance(digest, dict):
        add(blockers, "request_check_request_pack_digest_missing")
    else:
        if digest.get("algorithm") != "sha256":
            add(blockers, "request_check_request_pack_digest_algorithm_mismatch")
        if digest.get("domain") != "obelisk.player-principal-lifecycle.request-pack.v1":
            add(blockers, "request_check_request_pack_digest_domain_mismatch")
        if not isinstance(digest.get("sha256"), str) or re.fullmatch(r"[0-9a-f]{64}", digest.get("sha256", "")) is None:
            add(blockers, "request_check_request_pack_digest_sha256_invalid")


def validate_request_check_receipt_freshness(
    request_check: dict[str, Any],
    blockers: list[str],
    *,
    request: dict[str, Any],
) -> None:
    completion = request_check.get("operator_approval_receipt_completion")
    if not isinstance(completion, dict):
        add(blockers, "request_check_operator_approval_receipt_completion_missing")
        return
    approval_dt = parse_utc(completion.get("approval_recorded_at_utc"))
    if approval_dt is None:
        add(blockers, "request_check_operator_approval_receipt_approved_at_invalid")
        return
    approval_source = completion.get("approval_source")
    if approval_source not in (APPROVAL_SOURCE_CURRENT_TURN, APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY):
        add(blockers, "request_check_operator_approval_receipt_source_mismatch")
    request_standing_authority = request_standing_launch_authority_requirement(request)
    if request_standing_authority is True and approval_source != APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY:
        add(blockers, "request_check_operator_approval_receipt_standing_source_required")
    if request_standing_authority is False and approval_source == APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY:
        add(blockers, "request_check_operator_approval_receipt_unexpected_standing_source")
    expected_attestation = (
        APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY
        if approval_source == APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY
        else APPROVAL_ATTESTATION_CURRENT_TURN
    )
    if completion.get("attestation") != expected_attestation:
        add(blockers, "request_check_operator_approval_receipt_attestation_mismatch")
    prepared_at = parse_utc(request.get("prepared_at_utc"))
    window = request.get("approved_window")
    window_start = parse_utc(window.get("start_utc")) if isinstance(window, dict) else None
    if prepared_at is not None and approval_dt <= prepared_at:
        add(blockers, "request_check_operator_approval_receipt_before_request_prepared")
    if window_start is not None:
        if approval_dt >= window_start:
            add(blockers, "request_check_operator_approval_receipt_at_or_after_window_start")
        elif (window_start - approval_dt).total_seconds() > MAX_OPERATOR_APPROVAL_LEAD_SECONDS:
            add(blockers, "request_check_operator_approval_receipt_too_far_before_window_start")
    if (approval_dt - datetime.now(timezone.utc)).total_seconds() > 5:
        add(blockers, "request_check_operator_approval_receipt_in_future")


def validate_request_check(
    request_check: dict[str, Any],
    blockers: list[str],
    target: dict[str, str] | None,
    run_id: str | None,
    request_path: Path,
    request: dict[str, Any],
    request_sha256: str,
) -> None:
    for claim_path in collect_forbidden_claim_aliases(
        request_check,
        allowed_positive_paths=REQUEST_CHECK_ALLOWED_POSITIVE_CLAIM_PATHS,
    ):
        add(blockers, f"request_check_forbidden_authorization_or_evidence_claim:{claim_path}")
    add_activation_evidence_contract_blockers(request_check, blockers, prefix="request_check")
    for artifact_path in collect_non_authorizing_passive_status_authority_artifacts(request_check):
        add(blockers, f"request_check_non_authorizing_passive_status_authority_artifact:{artifact_path}")
    for stale_path in collect_stale_handle_new_player_rejected_start_rules(request_check):
        add(blockers, f"request_check_stale_handle_new_player_rejected_start_rule:{stale_path}")
    if request_check.get("schema") != REQUEST_CHECK_SCHEMA:
        add(blockers, "request_check_schema_mismatch")
    if request_check.get("ready") is not True or request_check.get("request_pack_ready") is not True:
        add(blockers, "request_check_not_ready")
    if request_check.get("operator_approval_receipt_verified") is not True:
        add(blockers, "operator_approval_receipt_not_verified")
    request_standing_authority = request_standing_launch_authority_requirement(request)
    standing_launch_authority_recorded = request_check_records_standing_launch_authority(request_check)
    if (
        request_standing_authority is not None
        and standing_launch_authority_recorded is not request_standing_authority
    ):
        add(blockers, "request_check_standing_launch_authority_scope_mismatch")
    if request_standing_authority is True:
        if request_check.get("standing_launch_authority_recorded") is not True:
            add(blockers, "request_check_standing_launch_authority_recorded_not_true")
        if request_check.get("operator_runtime_authority_source") != APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY:
            add(blockers, "request_check_operator_runtime_authority_source_standing_required")
        if request_check.get("current_turn_approval_recorded") is not False:
            add(
                blockers,
                "request_check_current_turn_approval_recorded_not_false_for_standing_authority",
            )
    elif request_standing_authority is False:
        if request_check.get("standing_launch_authority_recorded") is not False:
            add(blockers, "request_check_standing_launch_authority_recorded_not_false")
        if request_check.get("standing_launch_authority_satisfies_operator_approval") is not False:
            add(blockers, "request_check_standing_launch_authority_satisfies_operator_approval_not_false")
        if request_check.get("operator_runtime_authority_source") == APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY:
            add(blockers, "request_check_operator_runtime_authority_source_unexpected_standing")
    if (
        not standing_launch_authority_recorded
        and request_check.get("current_turn_approval_recorded") is not True
    ):
        add(blockers, "current_turn_approval_not_recorded")
    if (
        not standing_launch_authority_recorded
        and request_check.get("current_turn_operator_approval_required") is not True
    ):
        add(blockers, "request_check_current_turn_operator_approval_required_not_true")
    if standing_launch_authority_recorded:
        if request_check.get("standing_launch_authority_satisfies_operator_approval") is not True:
            add(blockers, "request_check_standing_launch_authority_not_bound")
        if request_check.get("current_turn_operator_approval_required") is not False:
            add(
                blockers,
                "request_check_current_turn_operator_approval_required_not_false_for_standing_authority",
            )
    if request_check.get("request_pack_records_current_turn_approval") is not False:
        add(blockers, "request_check_request_pack_records_current_turn_approval_not_false")
    if request_check.get("authorization_source") != "none_request_pack_check_only":
        add(blockers, "request_check_authorization_source_mismatch")
    if request_check.get("approved_runtime_evidence_source") != "none_request_pack_check_only":
        add(blockers, "request_check_approved_runtime_evidence_source_mismatch")
    if request_check.get("planning_only") is not True:
        add(blockers, "request_check_planning_only_not_true")
    if target is not None and request_check.get("target") != target:
        add(blockers, "request_check_target_mismatch")
    if run_id is not None and request_check.get("run_id") != run_id:
        add(blockers, "request_check_run_id_mismatch")
    validate_request_check_bindings(
        request_check,
        blockers,
        request=request,
        request_path=request_path,
        request_sha256=request_sha256,
    )
    validate_request_check_receipt_freshness(
        request_check,
        blockers,
        request=request,
    )
    for key in (
        "server_operations_authorized",
        "runtime_work_authorized",
        "read_live_logs",
        "reads_live_logs",
        "live_log_reads_authorized",
        "live_log_permission_granted",
        "publication_authorized",
        "promotion_ready",
        "public_abi_ready",
        "public_sdk_ready",
        "runtime_ready",
        "v1_completion_ready",
        "stable_claim_allowed",
        "request_pack_counts_as_approved_runtime_evidence",
        "observer_env_counts_as_approved_runtime_evidence",
        "operator_request_counts_as_approved_runtime_evidence",
        "copied_log_metadata_counts_as_approved_runtime_evidence",
        "bundle_output_counts_as_approved_runtime_evidence",
        "preflight_counts_as_approved_runtime_evidence",
        "window_manifest_counts_as_approved_runtime_evidence",
        "completed_receipt_counts_as_approved_runtime_evidence",
        "approved_runtime_evidence_present",
        "approved_runtime_evidence_ready",
        "route_ready",
        "sdk_accounting_counts_as_completed_surface",
        "p0_accounting_counts_as_promoted_surface",
        "current_turn_scope_authorized",
        "discord_authorized",
        "discord_send_authorized",
        "discord_sent",
        "marker_env_changes_authorized",
        "runtime_capture_authorized",
        "runtime_window_authorized",
    ):
        if request_check.get(key) is not False:
            add(blockers, f"request_check_{key}_not_false")


def validate_guarded_beta_notice_action(
    guarded_action: Any,
    blockers: list[str],
    *,
    notice_report: dict[str, Any],
    target: dict[str, str] | None,
    run_id: str | None,
    request_path: Path,
    request_sha256: str,
    expected_notice_action: dict[str, Any] | None,
    request_standing_authority: bool,
) -> None:
    if not isinstance(guarded_action, dict):
        add(blockers, "guarded_beta_notice_action_missing")
        return
    if guarded_action.get("schema") != GUARDED_BETA_NOTICE_ACTION_SCHEMA:
        add(blockers, "guarded_beta_notice_action_schema_mismatch")
    if guarded_action.get("mode") != notice_report.get("mode"):
        add(blockers, "guarded_beta_notice_action_mode_mismatch")
    if target is not None and guarded_action.get("target") != target:
        add(blockers, "guarded_beta_notice_action_target_mismatch")
    if run_id is not None and guarded_action.get("run_id") != run_id:
        add(blockers, "guarded_beta_notice_action_run_id_mismatch")
    if guarded_action.get("notice_path") != notice_report.get("notice_path"):
        add(blockers, "guarded_beta_notice_action_notice_path_mismatch")
    if expected_notice_action is not None and guarded_action.get("player_notice_action") != expected_notice_action:
        add(blockers, "guarded_beta_notice_action_player_notice_action_mismatch")
    request_ref = guarded_action.get("request_json")
    if not isinstance(request_ref, dict) or request_ref.get("sha256") != request_sha256:
        add(blockers, "guarded_beta_notice_action_request_sha256_mismatch")
    if not isinstance(request_ref, dict) or not isinstance(request_ref.get("path"), str) or not request_ref.get("path"):
        add(blockers, "guarded_beta_notice_action_request_path_missing")
    else:
        request_ref_path = Path(request_ref["path"])
        status = protected_paths.protected_path_status(
            request_ref_path,
            protected_root=SERVER_ROOT,
            approved_roots=protected_paths.approved_offline_workspace_roots(),
        )
        if status.protected:
            add(blockers, "guarded_beta_notice_action_request_path_protected")
        if status.resolved != request_path:
            add(blockers, "guarded_beta_notice_action_request_path_mismatch")
    if notice_report.get("mode") == "confirmed_send":
        if guarded_action.get("real_beta_test_notice_action_completed") is not True:
            add(blockers, "guarded_beta_notice_action_completed_not_true")
        if guarded_action.get("guarded_helper_invocation") is not True:
            add(blockers, "guarded_beta_notice_action_guarded_helper_invocation_not_true")
        if guarded_action.get("confirm_approved_send_arg_used") is not True:
            add(blockers, "guarded_beta_notice_action_confirm_approved_send_arg_missing")
        legacy_helper_scope = (
            guarded_action.get("approval_scope_arg_used") is True
            and guarded_action.get("approval_scope") == "beta-test"
        )
        bot_channel_id = guarded_action.get("bot_channel_id")
        bot_helper_scope = (
            guarded_action.get("bot_notice_helper") is True
            and guarded_action.get("approval_scope_arg_used") is False
            and bot_channel_id == BETA_TEST_BOT_CHANNEL_ID
            and guarded_action.get("approval_scope") == BETA_TEST_BOT_CHANNEL_ID
        )
        if not (legacy_helper_scope or bot_helper_scope):
            add(blockers, "guarded_beta_notice_action_approval_scope_arg_missing")
            add(blockers, "guarded_beta_notice_action_approval_scope_mismatch")
        if guarded_action.get("bot_notice_helper") is True:
            if bot_channel_id != BETA_TEST_BOT_CHANNEL_ID:
                add(blockers, "guarded_beta_notice_action_bot_channel_id_mismatch")
            expected_channel_id = guarded_action.get("expected_channel_id")
            if expected_channel_id not in (None, BETA_TEST_BOT_CHANNEL_ID):
                add(blockers, "guarded_beta_notice_action_expected_channel_id_mismatch")
    else:
        if guarded_action.get("real_beta_test_notice_action_completed") is not False:
            add(blockers, "guarded_beta_notice_action_dry_run_completed_not_false")
        if guarded_action.get("guarded_helper_invocation") is not False:
            add(blockers, "guarded_beta_notice_action_dry_run_guarded_helper_invocation_not_false")
        if guarded_action.get("confirm_approved_send_arg_used") is not False:
            add(blockers, "guarded_beta_notice_action_dry_run_confirm_arg_not_false")
        if guarded_action.get("approval_scope_arg_used") is not False:
            add(blockers, "guarded_beta_notice_action_dry_run_approval_scope_arg_not_false")
        if guarded_action.get("approval_scope") != "dry_run_only":
            add(blockers, "guarded_beta_notice_action_dry_run_approval_scope_mismatch")
    expected_standing_coverage = request_standing_authority and notice_report.get("mode") == "confirmed_send"
    if guarded_action.get("standing_launch_authority_recorded") is not request_standing_authority:
        add(blockers, "guarded_beta_notice_action_standing_launch_authority_recorded_mismatch")
    if (
        guarded_action.get("notice_action_covered_by_standing_launch_authority")
        is not expected_standing_coverage
    ):
        add(blockers, "guarded_beta_notice_action_standing_launch_authority_coverage_mismatch")
    for key in (
        "send_performed_by_request_pack",
        "request_pack_authorizes_discord",
        "authorizes_discord",
        "discord_authorized",
        "discord_send_authorized",
        "discord_authorized_by_this_report",
        "current_turn_approval_recorded",
        "current_turn_scope_authorized",
        "authorizes_runtime_work",
        "runtime_capture_authorized",
        "runtime_window_authorized",
        "marker_env_changes_authorized",
        "server_operations_authorized",
        "counts_as_approved_runtime_evidence",
        "counts_toward_v1_completion",
        "counts_toward_sdk",
        "counts_toward_p0_dependency_chain",
    ):
        if guarded_action.get(key) is not False:
            add(blockers, f"guarded_beta_notice_action_{key}_not_false")
    if guarded_action.get("non_authorization") != BETA_NOTICE_NON_AUTHORIZATION:
        add(blockers, "guarded_beta_notice_action_non_authorization_mismatch")


def default_notice_action_sidecar_path(notice_report_path: Path) -> Path:
    if notice_report_path.suffix:
        return notice_report_path.with_suffix(".sidecar.json")
    return notice_report_path.parent / f"{notice_report_path.name}.sidecar.json"


def notice_action_sidecar_path(notice_report: dict[str, Any], notice_report_path: Path) -> Path:
    path_value = notice_report.get("notice_action_sidecar_json")
    if isinstance(path_value, str) and path_value:
        candidate = Path(path_value)
        return candidate if candidate.is_absolute() else notice_report_path.parent / candidate
    return default_notice_action_sidecar_path(notice_report_path)


def read_notice_report_input(
    path: Path,
    label: str,
    blockers: list[str],
) -> tuple[dict[str, Any], Path, str, dict[str, Any] | None, Path | None]:
    payload, resolved, input_sha256 = read_json(path, label)
    if payload.get("schema") != NOTICE_ACTION_ARTIFACT_SCHEMA:
        return payload, resolved, input_sha256, None, None
    notice_report = payload.get("notice_report")
    if not isinstance(notice_report, dict):
        add(blockers, "beta_notice_action_sidecar_notice_report_missing")
        notice_report = {}
    return notice_report, resolved, canonical_json_sha256(notice_report), payload, resolved


def load_notice_action_sidecar(
    notice_report: dict[str, Any],
    notice_report_path: Path,
    blockers: list[str],
) -> tuple[dict[str, Any] | None, Path | None]:
    sidecar_path = notice_action_sidecar_path(notice_report, notice_report_path)
    try:
        protected_paths.reject_symlink_component(sidecar_path, "notice_action_sidecar_json")
        resolved = protected_paths.reject_protected_input_path(
            sidecar_path.expanduser(),
            "notice_action_sidecar_json",
            protected_root=SERVER_ROOT,
            approved_roots=protected_paths.approved_offline_workspace_roots(),
        )
    except SystemExit:
        add(blockers, "beta_notice_action_sidecar_path_protected")
        return None, None
    if not resolved.exists():
        add(blockers, "beta_notice_action_sidecar_missing")
        return None, resolved
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        add(blockers, "beta_notice_action_sidecar_unreadable")
        return None, resolved
    if not isinstance(payload, dict):
        add(blockers, "beta_notice_action_sidecar_not_object")
        return None, resolved
    return payload, resolved


def validate_notice_action_sidecar(
    sidecar: dict[str, Any] | None,
    blockers: list[str],
    *,
    notice_report: dict[str, Any],
    sidecar_path: Path | None,
) -> None:
    if sidecar is None:
        return
    if sidecar.get("schema") != NOTICE_ACTION_ARTIFACT_SCHEMA:
        add(blockers, "beta_notice_action_sidecar_schema_mismatch")
    embedded = sidecar.get("notice_report")
    if not isinstance(embedded, dict):
        add(blockers, "beta_notice_action_sidecar_notice_report_missing")
        return
    if embedded != notice_report:
        add(blockers, "beta_notice_action_sidecar_notice_report_mismatch")
    if sidecar.get("notice_report_sha256") != canonical_json_sha256(embedded):
        add(blockers, "beta_notice_action_sidecar_notice_report_sha256_mismatch")
    for key in ("mode", "ready", "target", "run_id", "notice_path", "request_json"):
        if sidecar.get(key) != notice_report.get(key):
            add(blockers, f"beta_notice_action_sidecar_{key}_mismatch")
    if sidecar.get("artifact_contains_full_sanitized_notice_report") is not True:
        add(blockers, "beta_notice_action_sidecar_full_report_not_embedded")
    if sidecar.get("sidecar_required_for_confirmed_send_consumption") is not True:
        add(blockers, "beta_notice_action_sidecar_required_flag_missing")
    if sidecar.get("stdout_only_confirmation_accepted") is not False:
        add(blockers, "beta_notice_action_sidecar_stdout_only_not_false")
    if sidecar.get("discord_send_performed_by_artifact_write") is not False:
        add(blockers, "beta_notice_action_sidecar_discord_send_by_artifact_not_false")
    if sidecar.get("secret_or_webhook_output_allowed") is not False:
        add(blockers, "beta_notice_action_sidecar_secret_output_not_false")
    for key, expected in SIDECAR_NON_EVIDENCE_FLAGS.items():
        if sidecar.get(key) is not expected:
            add(blockers, f"beta_notice_action_sidecar_{key}_mismatch")
    if sidecar.get("non_authorization") != BETA_NOTICE_NON_AUTHORIZATION:
        add(blockers, "beta_notice_action_sidecar_non_authorization_mismatch")
    if sidecar_path is not None and not sidecar_path.is_file():
        add(blockers, "beta_notice_action_sidecar_not_file")


def validate_confirmed_notice_sidecar(
    notice_report: dict[str, Any],
    blockers: list[str],
    *,
    notice_report_path: Path,
    input_sidecar: dict[str, Any] | None,
    input_sidecar_path: Path | None,
) -> None:
    guarded_action = notice_report.get("guarded_beta_notice_action")
    claimed_confirmed = (
        notice_report.get("mode") == "confirmed_send"
        or notice_report.get("discord_sent") is True
        or (
            isinstance(guarded_action, dict)
            and guarded_action.get("real_beta_test_notice_action_completed") is True
        )
    )
    if not claimed_confirmed:
        return
    if input_sidecar is not None:
        validate_notice_action_sidecar(
            input_sidecar,
            blockers,
            notice_report=notice_report,
            sidecar_path=input_sidecar_path,
        )
        return
    sidecar, sidecar_path = load_notice_action_sidecar(notice_report, notice_report_path, blockers)
    validate_notice_action_sidecar(
        sidecar,
        blockers,
        notice_report=notice_report,
        sidecar_path=sidecar_path,
    )


def validate_notice_report(
    notice_report: dict[str, Any],
    blockers: list[str],
    target: dict[str, str] | None,
    run_id: str | None,
    request_path: Path,
    request_sha256: str,
    expected_notice_action: dict[str, Any] | None,
    request_standing_authority: bool,
) -> None:
    notice_schema = notice_report.get("schema")
    if notice_schema == DIRECT_BOT_NOTICE_SCHEMA:
        add(blockers, "direct_bot_notice_report_not_activation_notice")
    if notice_schema == ACTIVE_NOTICE_STATE_SCHEMA:
        add(blockers, "active_notice_state_not_activation_notice")
    for claim_path in collect_forbidden_claim_aliases(
        notice_report,
        allowed_positive_paths=NOTICE_ALLOWED_POSITIVE_CLAIM_PATHS,
    ):
        add(blockers, f"notice_report_forbidden_authorization_or_evidence_claim:{claim_path}")
    add_activation_evidence_contract_blockers(notice_report, blockers, prefix="notice_report")
    for artifact_path in collect_non_authorizing_passive_status_authority_artifacts(notice_report):
        add(blockers, f"notice_report_non_authorizing_passive_status_authority_artifact:{artifact_path}")
    for stale_path in collect_stale_handle_new_player_rejected_start_rules(notice_report):
        add(blockers, f"notice_report_stale_handle_new_player_rejected_start_rule:{stale_path}")
    if notice_schema != BETA_NOTICE_SCHEMA:
        add(blockers, "notice_report_schema_mismatch")
    if notice_report.get("mode") != "confirmed_send":
        add(blockers, "beta_notice_confirmed_send_required")
        if notice_report.get("discord_sent") is not False:
            add(blockers, "beta_notice_dry_run_discord_sent_not_false")
    if notice_report.get("ready") is not True:
        add(blockers, "beta_notice_not_ready")
    if notice_report.get("discord_sent") is not True:
        add(blockers, "beta_notice_sent_attestation_missing")
    if notice_report.get("non_authorization") != BETA_NOTICE_NON_AUTHORIZATION:
        add(blockers, "beta_notice_non_authorization_mismatch")
    request_ref = notice_report.get("request_json")
    if not isinstance(request_ref, dict) or request_ref.get("sha256") != request_sha256:
        add(blockers, "beta_notice_request_sha256_mismatch")
    if not isinstance(request_ref, dict) or not isinstance(request_ref.get("path"), str) or not request_ref.get("path"):
        add(blockers, "beta_notice_request_path_missing")
    else:
        request_ref_path = Path(request_ref["path"])
        status = protected_paths.protected_path_status(
            request_ref_path,
            protected_root=SERVER_ROOT,
            approved_roots=protected_paths.approved_offline_workspace_roots(),
        )
        if status.protected:
            add(blockers, "beta_notice_request_path_protected")
        if status.resolved != request_path:
            add(blockers, "beta_notice_request_path_mismatch")
    if expected_notice_action is not None:
        if notice_report.get("notice_path") != expected_notice_action.get("notice_path"):
            add(blockers, "beta_notice_notice_path_mismatch")
        if notice_report.get("player_notice_action") != expected_notice_action:
            add(blockers, "beta_notice_player_notice_action_mismatch")
    if notice_report.get("dry_run_required_before_send") is not True:
        add(blockers, "beta_notice_dry_run_required_before_send_not_true")
    if notice_report.get("real_notice_send_required_before_activation") is not True:
        add(blockers, "beta_notice_real_notice_send_required_before_activation_not_true")
    if notice_report.get("activation_blocker_until_sent") != NOTICE_ACTION_BLOCKER:
        add(blockers, "beta_notice_activation_blocker_until_sent_mismatch")
    if target is not None and notice_report.get("target") != target:
        add(blockers, "beta_notice_target_mismatch")
    if run_id is not None and notice_report.get("run_id") != run_id:
        add(blockers, "beta_notice_run_id_mismatch")
    expected_standing_coverage = request_standing_authority and notice_report.get("mode") == "confirmed_send"
    if notice_report.get("standing_launch_authority_recorded") is not request_standing_authority:
        add(blockers, "beta_notice_standing_launch_authority_recorded_mismatch")
    if notice_report.get("notice_action_covered_by_standing_launch_authority") is not expected_standing_coverage:
        add(blockers, "beta_notice_standing_launch_authority_coverage_mismatch")
    validate_guarded_beta_notice_action(
        notice_report.get("guarded_beta_notice_action"),
        blockers,
        notice_report=notice_report,
        target=target,
        run_id=run_id,
        request_path=request_path,
        request_sha256=request_sha256,
        expected_notice_action=expected_notice_action,
        request_standing_authority=request_standing_authority,
    )
    for key in (
        "authorizes_discord",
        "activation_allowed",
        "activation_allowed_before_notice_sent",
        "activation_preconditions_met",
        "authorizes_runtime_work",
        "authorizes_server_operations",
        "authorizes_server_work",
        "authorizes_workspace_work",
        "authorizes_workspace_writes",
        "discord_authorized",
        "discord_notice_authorized",
        "discord_send_authorized",
        "discord_authorized_by_this_report",
        "live_log_reads_authorized",
        "live_log_permission_granted",
        "live_ops_authorized",
        "publication_authorized",
        "read_live_logs",
        "reads_live_logs",
        "server_operations_authorized",
        "runtime_work_authorized",
        "discord_authorized_by_request",
        "current_turn_approval_recorded",
        "current_turn_scope_authorized",
        "marker_env_changes_authorized",
        "runtime_capture_authorized",
        "runtime_window_authorized",
        "approved_runtime_evidence",
        "approved_runtime_evidence_present",
        "approved_runtime_evidence_ready",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_evidence",
        "counts_toward_public_sdk",
        "counts_toward_runtime",
        "counts_toward_v1_completion",
        "counts_toward_sdk",
        "counts_toward_p0_dependency_chain",
        "public_or_runtime_accounting_allowed",
        "promotion_ready",
        "public_abi_ready",
        "public_sdk_ready",
        "route_ready",
        "runtime_evidence_present",
        "runtime_evidence_ready",
        "runtime_ready",
        "sdk_evidence_ready",
        "v1_completion_ready",
        "stable_claim_allowed",
        "workspace_writes_authorized",
    ):
        if notice_report.get(key) is not False:
            add(blockers, f"notice_report_{key}_not_false")


def validate_route_gate(route_gate: dict[str, Any], blockers: list[str]) -> None:
    for claim_path in collect_forbidden_route_gate_claims(route_gate):
        add(blockers, f"route_gate_forbidden_authorization_or_evidence_claim:{claim_path}")
    add_activation_evidence_contract_blockers(route_gate, blockers, prefix="route_gate")
    for artifact_path in collect_non_authorizing_passive_status_authority_artifacts(route_gate):
        add(blockers, f"route_gate_non_authorizing_passive_status_authority_artifact:{artifact_path}")
    for stale_path in collect_stale_handle_new_player_rejected_start_rules(route_gate):
        add(blockers, f"route_gate_stale_handle_new_player_rejected_start_rule:{stale_path}")
    if route_gate.get("schema") != ROUTE_GATE_SCHEMA:
        add(blockers, "route_gate_schema_mismatch")
    if route_gate.get("valid") is not True:
        add(blockers, "route_gate_not_valid")
    if route_gate.get("planning_only") is not True:
        add(blockers, "route_gate_not_planning_only")
    if route_gate.get("route_blocked") is not True:
        add(blockers, "route_gate_route_blocked_not_true")
    if route_gate.get("dependency_chain_locked") is not True:
        add(blockers, "route_gate_dependency_chain_locked_not_true")
    if route_gate.get("current_route_blocker") != "approved_runtime_evidence_missing":
        add(blockers, "route_gate_current_blocker_not_runtime_evidence_missing")
    remaining = route_gate.get("remaining_route_blockers")
    if remaining != ["approved_runtime_evidence_missing"]:
        add(blockers, "route_gate_remaining_blockers_mismatch")
    if route_gate.get("next_route_blocker_after_runtime_evidence") != "identity_public_contract_gate_missing":
        add(blockers, "route_gate_next_after_runtime_evidence_mismatch")
    for key in (
        "counts_toward_public_sdk",
        "counts_toward_runtime",
        "counts_toward_v1_completion",
        "public_or_runtime_accounting_allowed",
        "promotion_ready",
        "public_abi_ready",
        "public_sdk_ready",
        "runtime_ready",
    ):
        if route_gate.get(key) is not False:
            add(blockers, f"route_gate_{key}_not_false")
    simulation = route_gate.get("post_evidence_p0_lock_simulation")
    if not isinstance(simulation, dict):
        add(blockers, "route_gate_post_evidence_simulation_missing")
        return
    if simulation.get("simulation_only") is not True:
        add(blockers, "route_gate_post_evidence_simulation_only_not_true")
    if simulation.get("current_route_blocker") != "approved_runtime_evidence_missing":
        add(blockers, "route_gate_post_evidence_current_blocker_mismatch")
    if simulation.get("simulated_route_blocker_after_accepted_runtime_evidence") != "identity_public_contract_gate_missing":
        add(blockers, "route_gate_post_evidence_next_blocker_mismatch")
    for key in (
        "approved_runtime_evidence_accepted",
        "permissions_admin_unlocked",
        "command_response_unlocked",
        "commands_replies_unlocked",
        "public_sdk_ready",
        "runtime_ready",
        "counts_toward_complete_sdk_claim",
        "counts_toward_p0_dependency_chain_claim",
    ):
        if simulation.get(key) is not False:
            add(blockers, f"route_gate_post_evidence_{key}_not_false")
    for key in ("complete_sdk_claim_progress_contribution", "p0_dependency_chain_claim_progress_contribution"):
        if simulation.get(key) != 0:
            add(blockers, f"route_gate_post_evidence_{key}_not_zero")


def nested_dict(value: Any, *keys: str) -> dict[str, Any]:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}


def approved_evidence_bundle_acceptance_requirement() -> dict[str, Any]:
    return {
        "schema": APPROVED_EVIDENCE_BUNDLE_ACCEPTANCE_SCHEMA,
        "checker": "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
        "accepted_bundle_required_before_any_readiness_or_progress_claim": True,
        "approved_evidence_bundle_checker_accepted": False,
        "required_lifecycle_event_role_triplet": [
            "session_start",
            "session_start_rejected",
            "session_end",
        ],
        "session_start_rejected": {
            "required_function": SESSION_START_REJECTED_REQUIRED_FUNCTION,
            "required_argument_tuple": SESSION_START_REJECTED_REQUIRED_ARGUMENTS,
            "required_call": SESSION_START_REJECTED_REQUIRED_CALL,
            "required_exact_call": SESSION_START_REJECTED_REQUIRED_CALL,
            "exact_check_join_in_progress_requirement": SESSION_START_REJECTED_REQUIRED_CALL,
            "handle_new_player_rejected_tuple_allowed": False,
            "handle_new_player_rejected_tuple_alternative_allowed": False,
        },
        "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
        "passive_or_no_user_state_counts_as_evidence": False,
        "passive_or_no_user_state_counts_as_readiness": False,
        "passive_or_no_user_state_counts_as_progress": False,
        "passive_or_no_user_state_counts_as_authorization": False,
        "passive_or_no_user_state_counts_as_notice_sent": False,
        "prepared_actions_remain": "notice_only_or_request_only",
        "non_authorization": NON_AUTHORIZATION,
    }


def redact_recommended_text(value: str) -> str:
    return SECRET_TEXT_RE.sub(lambda match: f"{match.group(1) or match.group(2)}<redacted>", value)


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
        "server_restart_authorized_by_checker": False,
        "message": (
            "Preserve the current two-server cap: never keep three ARK servers running; "
            "confirm one instance is off before starting another."
        ),
        "non_authorization": NON_AUTHORIZATION,
    }


def lifecycle_role_objectives(
    missing_roles: list[str] | None = None,
) -> dict[str, Any]:
    roles = list(missing_roles or ("session_start", "session_start_rejected", "session_end"))
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
            "required_exact_call": SESSION_START_REJECTED_REQUIRED_CALL,
            "exact_check_join_in_progress_requirement": SESSION_START_REJECTED_REQUIRED_CALL,
            "required_copied_bool_fields": SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS,
            "required_copied_bool_values": SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES,
            "handle_new_player_rejected_tuple_allowed": False,
            "handle_new_player_rejected_tuple_alternative_allowed": False,
            "objective": "capture exact CheckJoinInProgress(1,0) rejection from copied Obelisk.log",
        },
        {
            "objective_id": "session_end",
            "role": "session_end",
            "required_function": ON_LOGOUT_FUNCTION,
            "correlation_status": "matched",
            "objective": "capture matched session_end for the same player session",
        },
    ]
    return {
        "schema": LIFECYCLE_ROLE_OBJECTIVES_SCHEMA,
        "required_lifecycle_event_roles": ["session_start", "session_start_rejected", "session_end"],
        "missing_lifecycle_event_roles": roles,
        "next_missing_lifecycle_event_role": roles[0] if roles else None,
        "objective_ids": [item["objective_id"] for item in objectives],
        "objectives": objectives,
        "exact_check_join_in_progress_requirement": SESSION_START_REJECTED_REQUIRED_CALL,
        "requires_copied_log_bundle_checker_acceptance": True,
        "standing_authority_satisfies_missing_roles": False,
        "checker_satisfies_missing_roles": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def recommended_notice_text(request: dict[str, Any]) -> dict[str, Any]:
    target = request.get("target") if isinstance(request.get("target"), dict) else {}
    window = request.get("approved_window") if isinstance(request.get("approved_window"), dict) else {}
    join_plan = request.get("direct_join_plan")
    if not isinstance(join_plan, dict):
        try:
            join_plan = direct_join_plan(request)
        except (KeyError, TypeError):
            join_plan = {}
    instance = target.get("instance", "target")
    map_name = target.get("map", "map")
    start_utc = window.get("start_utc", "scheduled window")
    end_utc = window.get("end_utc", "scheduled window")
    objective_text = "session_start, CheckJoinInProgress(1,0), session_end"
    discord_text = (
        f"Obelisk beta window for {map_name} on {instance} ({start_utc} to {end_utc} UTC). "
        f"Please direct-join that exact server/map, let the session settle, and leave once "
        f"when asked so we can validate {objective_text}. Do not post player names, chat, "
        f"Steam IDs, private credentials."
    )
    broadcast_text = (
        "Obelisk beta validation window starting now. Please finish current action, "
        "direct-join the exact target and leave once if participating, and avoid sharing "
        "names, chat, IDs or private credentials."
    )
    return {
        "schema": RECOMMENDED_NOTICE_TEXT_SCHEMA,
        "discord_channel": "beta-test",
        "discord_content": "@everyone",
        "recommended_discord_text_redacted": redact_recommended_text(discord_text),
        "recommended_rcon_broadcast_text_redacted": redact_recommended_text(broadcast_text),
        "recommended_text_already_redacted": True,
        "raw_player_text_allowed": False,
        "raw_player_identity_allowed": False,
        "raw_player_text_or_identity_allowed": False,
        "secret_or_webhook_output_allowed": False,
        "direct_join_plan": join_plan,
        "approved_beta_test_channel_only": True,
        "broad_discord_or_community_notice_allowed": False,
        "two_server_cap_policy": two_server_cap_policy(),
        "lifecycle_role_objectives": lifecycle_role_objectives(),
        "counts_as_approved_runtime_evidence": False,
        "counts_toward_sdk": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def standing_authority_non_progress_boundary(
    *,
    ready: bool,
    standing_launch_authority_recorded: bool,
    scope: str,
) -> dict[str, Any]:
    standing_scope_satisfied = standing_launch_authority_satisfies_activation_scope(
        ready=ready,
        standing_launch_authority_recorded=standing_launch_authority_recorded,
    )
    return {
        "schema": "obelisk.player-principal-lifecycle-standing-authority-non-progress-boundary.v1",
        "scope": scope,
        "offline_preconditions_consistent": ready,
        "standing_launch_authority_recorded": standing_launch_authority_recorded,
        "standing_launch_authority_satisfies_activation_authority": standing_scope_satisfied,
        "recorded_standing_authority_applies_to_preparation_only": (
            standing_launch_authority_recorded and not standing_scope_satisfied
        ),
        "recorded_standing_authority_applies_to_scoped_operator_actions_only": standing_scope_satisfied,
        "authorization_for_scoped_operator_actions_only": standing_scope_satisfied,
        "standing_authority_authorizes_discord_send": False,
        "standing_authority_authorizes_runtime_evidence": standing_scope_satisfied,
        "standing_authority_authorizes_marker_env_changes": standing_scope_satisfied,
        "standing_authority_authorizes_server_restart": standing_scope_satisfied,
        "standing_authority_counts_as_approved_runtime_evidence": False,
        "standing_authority_counts_as_runtime_evidence": False,
        "standing_authority_counts_as_sdk_evidence": False,
        "standing_authority_counts_as_runtime_progress": False,
        "standing_authority_counts_as_sdk_progress": False,
        "standing_authority_counts_toward_p0_dependency_chain": False,
        "standing_authority_grants_runtime_readiness": False,
        "standing_authority_grants_public_sdk_readiness": False,
        "standing_authority_grants_activation_readiness": False,
        "approved_runtime_evidence_ready": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "grants_readiness_claims": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def prepared_action_mode(action: dict[str, Any]) -> str:
    text = " ".join(
        str(action.get(key, ""))
        for key in ("id", "action_kind", "side_effect_domain", "phase")
    ).casefold()
    if "notice" in text or "discord" in text:
        return "notice_only"
    return "request_only"


def attach_prepared_action_boundary(
    action: dict[str, Any],
) -> dict[str, Any]:
    mode = str(action.get("prepared_action_mode") or prepared_action_mode(action))
    action["prepared_action_mode"] = mode
    action["prepared_action_scope"] = "notice_only_or_request_only"
    action["notice_only_or_request_only_until_approved_evidence_bundle_accepted"] = True
    action["approved_evidence_bundle_checker_accepted"] = False
    action["approved_evidence_bundle_acceptance_required"] = True
    action["approved_evidence_bundle_acceptance_requirement"] = (
        approved_evidence_bundle_acceptance_requirement()
    )
    action["passive_or_no_user_state_counts_as_approved_runtime_evidence"] = False
    action["no_users_no_testers_passive_wait_counts_as_readiness"] = False
    action["no_users_no_testers_passive_wait_counts_as_progress"] = False
    action["no_users_no_testers_passive_wait_counts_as_authorization"] = False
    action["no_users_no_testers_passive_wait_counts_as_notice_sent"] = False
    return action


def activation_external_execution_authority(
    *,
    ready: bool,
    standing_launch_authority_recorded: bool,
) -> dict[str, Any]:
    allowed_by_standing = standing_launch_authority_satisfies_activation_scope(
        ready=ready,
        standing_launch_authority_recorded=standing_launch_authority_recorded,
    )
    still_missing_current_scope = not allowed_by_standing
    return {
        "schema": "obelisk.player-principal-lifecycle-activation-external-execution-authority.v1",
        "standing_launch_authority_recorded": standing_launch_authority_recorded,
        "standing_debug_authority_recorded": standing_launch_authority_recorded,
        "standing_launch_authority_satisfies_beta_notice_scope": False,
        "standing_launch_authority_satisfies_dry_run_notice_preparation_scope": (
            ready and standing_launch_authority_recorded
        ),
        "standing_launch_authority_satisfies_active_observation_scope": allowed_by_standing,
        "recorded_standing_debug_authority_satisfies_scope": allowed_by_standing,
        "allowed_by_recorded_standing_debug_authority": allowed_by_standing,
        "still_missing_current_scope": still_missing_current_scope,
        "still_missing_current_turn_scope": still_missing_current_scope,
        "fresh_current_turn_operator_authorization_required": ready and not allowed_by_standing,
        "separate_operator_authorization_required": ready and not allowed_by_standing,
        "fresh_separate_activation_approval_required": ready and not allowed_by_standing,
        "activation_next_action_sequence_consumable_under_recorded_standing_launch_authority": allowed_by_standing,
        "standing_authority_preparation_only": (
            standing_launch_authority_recorded and not allowed_by_standing
        ),
        "standing_authority_authorizes_discord_send": False,
        "standing_authority_authorizes_runtime_evidence": allowed_by_standing,
        "standing_authority_authorizes_marker_env_changes": allowed_by_standing,
        "standing_authority_authorizes_server_restart": allowed_by_standing,
        "checker_sends_discord": False,
        "checker_touches_ark": False,
        "checker_reads_live_logs": False,
        "checker_edits_markers_or_env": False,
        "checker_default_sends_discord": False,
        "checker_default_touches_ark": False,
        "checker_default_reads_live_logs": False,
        "checker_default_edits_markers_or_env": False,
        "prepared_actions_remain_notice_only_or_request_only": True,
        "two_server_cap_policy": two_server_cap_policy(),
        "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
        "standing_authority_non_progress_boundary": standing_authority_non_progress_boundary(
            ready=ready,
            standing_launch_authority_recorded=standing_launch_authority_recorded,
            scope="external_execution_authority",
        ),
        "standing_authority_counts_as_runtime_progress": False,
        "standing_authority_counts_as_sdk_progress": False,
        "standing_authority_grants_runtime_readiness": False,
        "approved_evidence_bundle_checker_accepted": False,
        "approved_evidence_bundle_acceptance_required": True,
        "approved_evidence_bundle_acceptance_requirement": approved_evidence_bundle_acceptance_requirement(),
        "non_authorization": NON_AUTHORIZATION,
    }


def required_evidence_paths(request: dict[str, Any]) -> dict[str, Any]:
    return nested_dict(
        request,
        "current_turn_approval_scope",
        "required_named_scope",
        "evidence_paths",
    )


def standing_debug_safety_limits(request: dict[str, Any]) -> dict[str, Any]:
    safety = request.get("player_presence_safety")
    if not isinstance(safety, dict):
        safety = {}
    restart_requested = request.get("restart_expectation") == "restart"
    return {
        "schema": SAFETY_LIMITS_SCHEMA,
        "max_running_ark_servers": 2,
        "three_ark_servers_allowed": False,
        "two_server_cap_policy": two_server_cap_policy(),
        "must_confirm_one_instance_off_before_starting_another": True,
        "restart_expectation": request.get("restart_expectation"),
        "restart_with_connected_players_allowed_without_warning": False,
        "restart_must_warn_or_reschedule_if_players_connected": restart_requested,
        "connected_player_check_required_before_restart": (
            safety.get("connected_player_check_required_before_restart") is True
        ),
        "rcon_broadcast_required_if_players_connected": (
            safety.get("rcon_broadcast_required_if_players_connected") is True
        ),
        "restart_must_be_cancelled_or_rescheduled_if_players_remain_connected": (
            safety.get("restart_must_be_cancelled_or_rescheduled_if_players_remain_connected")
            is True
        ),
        "raw_player_text_capture_allowed": False,
        "raw_player_text_logging_allowed": False,
        "secret_capture_allowed": False,
        "secret_or_webhook_output_allowed": False,
        "recommended_notice_text": recommended_notice_text(request),
        "recommended_rcon_broadcast_text_redacted": recommended_notice_text(request)[
            "recommended_rcon_broadcast_text_redacted"
        ],
        "recommended_discord_text_redacted": recommended_notice_text(request)[
            "recommended_discord_text_redacted"
        ],
        "recommended_text_already_redacted": True,
        "approved_runtime_evidence_claim_allowed": False,
        "runtime_readiness_claim_allowed": False,
        "public_sdk_readiness_claim_allowed": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def activation_authority_precondition(
    *,
    ready: bool,
    standing_launch_authority_recorded: bool,
    safety_limits: dict[str, Any],
) -> dict[str, Any]:
    allowed_by_standing = standing_launch_authority_satisfies_activation_scope(
        ready=ready,
        standing_launch_authority_recorded=standing_launch_authority_recorded,
    )
    still_missing_current_scope = not allowed_by_standing
    if allowed_by_standing:
        status = STANDING_READY_NEXT_BLOCKER
    elif ready and standing_launch_authority_recorded:
        status = "offline_preconditions_consistent_external_action_scope_required"
    elif still_missing_current_scope:
        status = "still_missing_current_scope"
    else:
        status = "offline_preconditions_missing"
    return {
        "schema": AUTHORITY_PRECONDITION_SCHEMA,
        "status": status,
        "offline_preconditions_consistent": ready,
        "standing_launch_authority_recorded": standing_launch_authority_recorded,
        "standing_debug_authority_recorded": standing_launch_authority_recorded,
        "recorded_standing_launch_authority_satisfies_exact_scope": allowed_by_standing,
        "recorded_standing_debug_authority_satisfies_exact_scope": allowed_by_standing,
        "allowed_by_recorded_standing_launch_authority": allowed_by_standing,
        "allowed_by_recorded_standing_debug_authority": allowed_by_standing,
        "standing_authority_allowed_for_planning_activation_preconditions": (
            ready and standing_launch_authority_recorded
        ),
        "standing_authority_preparation_only": (
            standing_launch_authority_recorded and not allowed_by_standing
        ),
        "standing_authority_authorizes_discord_send": False,
        "standing_authority_authorizes_runtime_evidence": allowed_by_standing,
        "standing_authority_authorizes_marker_env_changes": allowed_by_standing,
        "standing_authority_authorizes_server_restart": allowed_by_standing,
        "still_missing_current_scope": still_missing_current_scope,
        "still_missing_current_turn_scope": still_missing_current_scope,
        "current_turn_scope_required_before_activation": still_missing_current_scope,
        "current_turn_scope_missing_fields": (
            list(CURRENT_TURN_APPROVAL_REQUIRED_FIELDS) if still_missing_current_scope else []
        ),
        "active_runtime_window_requires_standing_or_current_scope": True,
        "activation_authorized_by_this_report": False,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "runtime_capture_authorized": False,
        "runtime_window_authorized": False,
        "marker_env_changes_authorized": False,
        "discord_authorized": False,
        "discord_send_authorized": False,
        "read_live_logs": False,
        "live_log_reads_authorized": False,
        "publication_authorized": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "grants_readiness_claims": False,
        "standing_authority_non_progress_boundary": standing_authority_non_progress_boundary(
            ready=ready,
            standing_launch_authority_recorded=standing_launch_authority_recorded,
            scope="activation_authority_precondition",
        ),
        "standing_authority_counts_as_runtime_progress": False,
        "standing_authority_counts_as_sdk_progress": False,
        "standing_authority_grants_runtime_readiness": False,
        "standing_authority_grants_activation_readiness": False,
        "prepared_actions_remain_notice_only_or_request_only": True,
        "two_server_cap_policy": two_server_cap_policy(),
        "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
        "approved_evidence_bundle_checker_accepted": False,
        "approved_evidence_bundle_acceptance_required": True,
        "approved_evidence_bundle_acceptance_requirement": approved_evidence_bundle_acceptance_requirement(),
        "safety_limits": safety_limits,
        "non_authorization": NON_AUTHORIZATION,
    }


def attach_action_authority_boundaries(
    actions: list[dict[str, Any]],
    *,
    standing_launch_authority_recorded: bool,
    standing_scope_satisfied: bool,
) -> list[dict[str, Any]]:
    for action in actions:
        action["allowed_under_recorded_standing_launch_authority"] = standing_scope_satisfied
        action["allowed_under_recorded_standing_debug_authority"] = standing_scope_satisfied
        action["recorded_standing_launch_authority_satisfies_activation_scope"] = (
            standing_scope_satisfied
        )
        action["consumable_under_recorded_standing_launch_authority"] = standing_scope_satisfied
        if standing_scope_satisfied:
            action["separate_operator_authorization_required"] = False
            action["fresh_separate_activation_approval_required"] = False
        action.setdefault(
            "recorded_standing_launch_authority_satisfies_preparation_scope",
            standing_launch_authority_recorded and not standing_scope_satisfied,
        )
        action.setdefault("standing_authority_authorizes_discord_send", False)
        action_id = str(action.get("id", ""))
        if action_id in {"active_observation_window", "capture_required_sibling_sidecars"}:
            action["standing_authority_authorizes_runtime_evidence"] = standing_scope_satisfied
        else:
            action.setdefault("standing_authority_authorizes_runtime_evidence", False)
        if action_id in {"active_observation_window", "restore_stable_posture_and_verify"}:
            action["standing_authority_authorizes_marker_env_changes"] = standing_scope_satisfied
        else:
            action.setdefault("standing_authority_authorizes_marker_env_changes", False)
        if action_id in {"safe_restart_warn_or_reschedule", "restore_stable_posture_and_verify"}:
            action["standing_authority_authorizes_server_restart"] = standing_scope_satisfied
        else:
            action.setdefault("standing_authority_authorizes_server_restart", False)
        action.setdefault("two_server_cap_policy", two_server_cap_policy())
        action.setdefault("lifecycle_missing_role_objectives", lifecycle_role_objectives())
        action.setdefault("requires_exact_run_target_and_recorded_safety_limits", True)
        action.setdefault("authorized_by_this_report", False)
        action.setdefault("server_operations_authorized_by_this_report", False)
        action.setdefault("runtime_work_authorized_by_this_report", False)
        action.setdefault("marker_env_changes_authorized_by_this_report", False)
        action.setdefault("workspace_writes_authorized_by_this_report", False)
        action.setdefault("discord_authorized_by_this_report", False)
        action.setdefault("creates_sidecars_by_this_report", False)
        action.setdefault("grants_readiness_claims", False)
        action.setdefault("standing_authority_counts_as_runtime_progress", False)
        action.setdefault("standing_authority_counts_as_sdk_progress", False)
        action.setdefault("standing_authority_grants_runtime_readiness", False)
        attach_prepared_action_boundary(action)
    return actions


def activation_operator_action_summary(
    *,
    ready: bool,
    target: dict[str, str] | None,
    run_id: str | None,
    blockers: list[str],
    standing_launch_authority_recorded: bool,
    authority_precondition: dict[str, Any],
    next_actions: list[dict[str, Any]],
) -> dict[str, Any]:
    standing_scope_satisfied = standing_launch_authority_satisfies_activation_scope(
        ready=ready,
        standing_launch_authority_recorded=standing_launch_authority_recorded,
    )
    allowed_actions = [
        action
        for action in next_actions
        if action.get("allowed_under_recorded_standing_debug_authority") is True
    ]
    return {
        "schema": "obelisk.player-principal-lifecycle-activation-operator-action-summary.v1",
        "target": target,
        "run_id": run_id,
        "status": authority_precondition.get("status"),
        "offline_preconditions_consistent": ready,
        "blockers": blockers,
        "recorded_standing_debug_authority": {
            "recorded": standing_launch_authority_recorded,
            "source": "standing_launch_authority" if standing_launch_authority_recorded else None,
            "applies_to_preparation_only": (
                standing_launch_authority_recorded and not standing_scope_satisfied
            ),
            "applies_to_operator_actions_only": standing_scope_satisfied,
            "must_match_exact_run_target_evidence_paths_and_safety_limits": True,
            "authorized_by_this_report": False,
            "server_operations_authorized_by_this_report": False,
            "runtime_work_authorized_by_this_report": False,
            "marker_env_changes_authorized_by_this_report": False,
            "workspace_writes_authorized_by_this_report": False,
            "discord_authorized_by_this_report": False,
            "standing_authority_authorizes_discord_send": False,
            "standing_authority_authorizes_runtime_evidence": standing_scope_satisfied,
            "standing_authority_authorizes_marker_env_changes": standing_scope_satisfied,
            "standing_authority_authorizes_server_restart": standing_scope_satisfied,
            "publication_authorized_by_this_report": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_evidence": False,
            "grants_readiness_claims": False,
            "standing_authority_counts_as_runtime_progress": False,
            "standing_authority_counts_as_sdk_progress": False,
            "standing_authority_grants_runtime_readiness": False,
        },
        "actions_allowed_under_recorded_standing_debug_authority": allowed_actions,
        "still_missing_current_scope": not standing_scope_satisfied,
        "allowed_by_recorded_standing_debug_authority": standing_scope_satisfied,
        "two_server_cap_policy": two_server_cap_policy(),
        "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
        "standing_authority_non_progress_boundary": standing_authority_non_progress_boundary(
            ready=ready,
            standing_launch_authority_recorded=standing_launch_authority_recorded,
            scope="operator_action_summary",
        ),
        "non_authorization": NON_AUTHORIZATION,
    }


def activation_next_action_sequence(
    *,
    request: dict[str, Any],
    notice_report: dict[str, Any],
    ready: bool,
    standing_launch_authority_recorded: bool,
    blockers: list[str],
) -> list[dict[str, Any]]:
    if not ready:
        return attach_action_authority_boundaries(
            [
                {
                    "order": 1,
                    "id": "resolve_activation_precondition_blockers",
                    "owner": "lead",
                    "status": "manual_external_not_executed_by_checker",
                    "action": "Resolve the exact offline blocker list before any beta notice or runtime window action.",
                    "blockers": blockers,
                    "non_authorization": NON_AUTHORIZATION,
                }
            ],
            standing_launch_authority_recorded=False,
            standing_scope_satisfied=False,
        )

    authority_source = (
        "recorded_standing_launch_authority"
        if standing_launch_authority_recorded
        else "fresh_current_turn_operator_scope"
    )
    standing_scope_satisfied = standing_launch_authority_satisfies_activation_scope(
        ready=ready,
        standing_launch_authority_recorded=standing_launch_authority_recorded,
    )
    separate_auth_required = not standing_scope_satisfied
    target = request.get("target")
    approved_window = request.get("approved_window")
    named_scope = nested_dict(request, "current_turn_approval_scope", "required_named_scope")
    player_safety = request.get("player_presence_safety")
    restart_expectation = request.get("restart_expectation")
    restart_requested = restart_expectation == "restart"
    brief = request.get("operator_live_ops_brief")
    if not isinstance(brief, dict):
        brief = {}
    actions = [
        {
            "order": 1,
            "id": "confirmed_beta_notice_consumed",
            "owner": "lead",
            "status": "complete_offline_input",
            "action": (
                "Use the confirmed beta notice report already bound to this request; no additional "
                "notice authorization is required for this exact standing-authorized window."
                if standing_launch_authority_recorded
                else "Use the confirmed beta notice report already bound to this request."
            ),
            "notice_path": notice_report.get("notice_path"),
            "notice_report_mode": notice_report.get("mode"),
            "authority_source": authority_source,
            "separate_operator_authorization_required": False,
            "fresh_separate_activation_approval_required": False,
            "consumable_under_recorded_standing_launch_authority": False,
            "standing_authority_prepares_notice_only": standing_launch_authority_recorded,
            "discord_send_performed_by_checker": False,
            "standing_authority_authorizes_discord_send": False,
            "recommended_notice_text": recommended_notice_text(request),
            "ark_touched_by_checker": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_toward_sdk": False,
            "counts_toward_p0_dependency_chain": False,
            "non_authorization": NON_AUTHORIZATION,
        },
        {
            "order": 2,
            "id": "safe_restart_warn_or_reschedule",
            "owner": "lead",
            "status": "manual_external_not_executed_by_checker",
            "action": (
                "Before restart, check connected players on the exact target, warn through the "
                "approved player-safe path if players are connected, and cancel or reschedule "
                "if players remain connected."
                if restart_requested
                else "No restart warning is required by this request; preserve stable posture checks."
            ),
            "target": target,
            "restart_expectation": restart_expectation,
            "player_presence_safety": player_safety,
            "authority_source": authority_source,
            "separate_operator_authorization_required": separate_auth_required,
            "fresh_separate_activation_approval_required": separate_auth_required,
            "consumable_under_recorded_standing_launch_authority": False,
            "request_pack_authorizes_player_check_or_broadcast": False,
            "server_operations_performed_by_checker": False,
            "standing_authority_authorizes_server_restart": False,
            "standing_authority_authorizes_discord_send": False,
            "recommended_notice_text": recommended_notice_text(request),
            "two_server_cap_policy": two_server_cap_policy(),
            "ark_touched_by_checker": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_toward_sdk": False,
            "counts_toward_p0_dependency_chain": False,
            "non_authorization": NON_AUTHORIZATION,
        },
        {
            "order": 3,
            "id": "active_observation_window",
            "owner": "lead",
            "status": "manual_external_not_executed_by_checker",
            "action": (
                "Use the exact observer marker/env scope for the approved window, keep plugins "
                "disabled, dispatch limit 0, log limit 10, and perform only the named "
                "player_principal_lifecycle observation."
            ),
            "target": target,
            "approved_window": approved_window,
            "direct_join_plan": request.get("direct_join_plan"),
            "marker_env_gates": nested_dict(named_scope, "marker_env_gates"),
            "runtime_triplet_contract": request.get("runtime_triplet_contract"),
            "forbidden_markers": request.get("forbidden_markers"),
            "authority_source": authority_source,
            "separate_operator_authorization_required": separate_auth_required,
            "fresh_separate_activation_approval_required": separate_auth_required,
            "consumable_under_recorded_standing_launch_authority": False,
            "standing_authority_authorizes_marker_env_changes": False,
            "standing_authority_authorizes_runtime_evidence": False,
            "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
            "two_server_cap_policy": two_server_cap_policy(),
            "marker_env_changes_performed_by_checker": False,
            "runtime_capture_performed_by_checker": False,
            "ark_touched_by_checker": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_toward_sdk": False,
            "counts_toward_p0_dependency_chain": False,
            "non_authorization": NON_AUTHORIZATION,
        },
        {
            "order": 4,
            "id": "capture_required_sibling_sidecars",
            "owner": "lead",
            "status": "manual_external_not_executed_by_checker",
            "action": (
                "Preserve the checked sibling set beside the copied log: request pack, observer "
                "env, approval request, completed receipt, preflight-pre, preflight-post, "
                "window manifest, and copied Obelisk.log."
            ),
            "required_evidence_paths": required_evidence_paths(request),
            "counts_as_approved_runtime_evidence": False,
            "counts_toward_sdk": False,
            "counts_toward_p0_dependency_chain": False,
            "separate_operator_authorization_required": separate_auth_required,
            "fresh_separate_activation_approval_required": separate_auth_required,
            "consumable_under_recorded_standing_launch_authority": False,
            "standing_authority_authorizes_runtime_evidence": False,
            "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
            "runtime_capture_performed_by_checker": False,
            "ark_touched_by_checker": False,
            "non_authorization": (
                "sidecar paths are exact follow-up requirements; this checker does not copy live logs "
                "or build approved runtime evidence"
            ),
        },
        {
            "order": 5,
            "id": "restore_stable_posture_and_verify",
            "owner": "lead",
            "status": "manual_external_not_executed_by_checker",
            "action": (
                "After the window, remove observer-only markers/env, preserve the stable "
                "process-event-hook and disable-plugins posture, and run stable-posture checks."
            ),
            "rollback": request.get("rollback"),
            "post_run_stable_posture": brief.get("post_run_stable_posture"),
            "authority_source": authority_source,
            "separate_operator_authorization_required": separate_auth_required,
            "fresh_separate_activation_approval_required": separate_auth_required,
            "consumable_under_recorded_standing_launch_authority": False,
            "standing_authority_authorizes_marker_env_changes": False,
            "standing_authority_authorizes_server_restart": False,
            "two_server_cap_policy": two_server_cap_policy(),
            "server_operations_performed_by_checker": False,
            "ark_touched_by_checker": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_toward_sdk": False,
            "counts_toward_p0_dependency_chain": False,
            "non_authorization": NON_AUTHORIZATION,
        },
    ]
    return attach_action_authority_boundaries(
        actions,
        standing_launch_authority_recorded=standing_launch_authority_recorded,
        standing_scope_satisfied=standing_scope_satisfied,
    )


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    blockers: list[str] = []
    request, request_path, request_sha256 = read_json(args.request_json, "--request-json")
    request_check, request_check_path, request_check_sha256 = read_json(
        args.request_check_json,
        "--request-check-json",
    )
    (
        notice_report,
        notice_report_path,
        notice_report_sha256,
        notice_action_sidecar,
        notice_action_sidecar_path_value,
    ) = read_notice_report_input(
        args.notice_report_json,
        "--notice-report-json",
        blockers,
    )
    route_gate, route_gate_path, route_gate_sha256 = read_json(args.route_gate_json, "--route-gate-json")

    target, run_id, expected_notice_action = validate_request(
        request,
        blockers,
        request_path=request_path,
    )
    diagnostic_candidates_policy = diagnostic_candidates_for_approved_evidence_policy(
        request,
        observer_env_contains_diagnostic_candidates=observer_env_contains_diagnostic_candidates(
            request_path.parent / "observer-window.env",
            blockers,
        ),
        observer_env_diagnostic_keys_present=observer_env_diagnostic_keys_present(
            request_path.parent / "observer-window.env",
            blockers,
        ),
    )
    request_standing_authority = request_standing_launch_authority_requirement(request) is True
    validate_request_check(request_check, blockers, target, run_id, request_path, request, request_sha256)
    validate_notice_report(
        notice_report,
        blockers,
        target,
        run_id,
        request_path,
        request_sha256,
        expected_notice_action,
        request_standing_authority,
    )
    validate_confirmed_notice_sidecar(
        notice_report,
        blockers,
        notice_report_path=notice_report_path,
        input_sidecar=notice_action_sidecar,
        input_sidecar_path=notice_action_sidecar_path_value,
    )
    validate_route_gate(route_gate, blockers)

    ready = not blockers
    request_check_authority = request_check if isinstance(request_check, dict) else {}
    standing_launch_authority_recorded = (
        request_standing_authority
        and request_check_records_standing_launch_authority(request_check_authority)
    )
    standing_scope_satisfied = standing_launch_authority_satisfies_activation_scope(
        ready=ready,
        standing_launch_authority_recorded=standing_launch_authority_recorded,
    )
    safety_limits = standing_debug_safety_limits(request)
    authority_precondition = activation_authority_precondition(
        ready=ready,
        standing_launch_authority_recorded=standing_launch_authority_recorded,
        safety_limits=safety_limits,
    )
    external_authority = activation_external_execution_authority(
        ready=ready,
        standing_launch_authority_recorded=standing_launch_authority_recorded,
    )
    standing_non_progress = standing_authority_non_progress_boundary(
        ready=ready,
        standing_launch_authority_recorded=standing_launch_authority_recorded,
        scope="activation_preconditions_report",
    )
    next_actions = activation_next_action_sequence(
        request=request,
        notice_report=notice_report,
        ready=ready,
        standing_launch_authority_recorded=standing_launch_authority_recorded,
        blockers=blockers,
    )
    operator_summary = activation_operator_action_summary(
        ready=ready,
        target=target,
        run_id=run_id,
        blockers=blockers,
        standing_launch_authority_recorded=standing_launch_authority_recorded,
        authority_precondition=authority_precondition,
        next_actions=next_actions,
    )
    return {
        "schema": SCHEMA,
        "ready": ready,
        "offline_preconditions_consistent": ready,
        "activation_preconditions_checked": ready,
        "activation_preconditions_met": False,
        "ready_scope": "offline_pre_activation_consistency_only",
        "target": target,
        "run_id": run_id,
        "runtime_triplet_contract": request.get("runtime_triplet_contract"),
        "direct_join_plan": request.get("direct_join_plan"),
        "diagnostic_candidates_for_approved_evidence": diagnostic_candidates_policy,
        "inputs": {
            "request_json": {"path": str(request_path), "sha256": request_sha256},
            "request_check_json": {"path": str(request_check_path), "sha256": request_check_sha256},
            "notice_report_json": {"path": str(notice_report_path), "sha256": notice_report_sha256},
            "notice_action_sidecar_json": (
                {"path": str(notice_action_sidecar_path_value)}
                if notice_action_sidecar_path_value is not None
                else {
                    "path": str(notice_action_sidecar_path(notice_report, notice_report_path)),
                    "required_for_confirmed_send": True,
                }
            ),
            "route_gate_json": {"path": str(route_gate_path), "sha256": route_gate_sha256},
        },
        "blockers": blockers,
        "next_blocker": (
            (STANDING_READY_NEXT_BLOCKER if standing_scope_satisfied else READY_NEXT_BLOCKER)
            if ready
            else "activation_preconditions_missing"
        ),
        "non_authorization": NON_AUTHORIZATION,
        "activation_authority_precondition": authority_precondition,
        "standing_debug_authority_safety_limits": safety_limits,
        "external_execution_authority": external_authority,
        "operator_action_summary": operator_summary,
        "standing_authority_non_progress_boundary": standing_non_progress,
        "activation_next_action_sequence": next_actions,
        "next_action_sequence": next_actions,
        "fresh_current_turn_operator_authorization_required_before_activation": (
            ready and not standing_scope_satisfied
        ),
        "standing_launch_authority_recorded": standing_launch_authority_recorded,
        "standing_debug_authority_recorded": standing_launch_authority_recorded,
        "standing_launch_authority_satisfies_activation_authority": (
            standing_scope_satisfied
        ),
        "recorded_standing_debug_authority_satisfies_activation_preconditions": (
            standing_scope_satisfied
        ),
        "allowed_by_recorded_standing_launch_authority": (
            standing_scope_satisfied
        ),
        "allowed_by_recorded_standing_debug_authority": (
            standing_scope_satisfied
        ),
        "standing_authority_allowed_for_planning_activation_preconditions": (
            standing_launch_authority_recorded and ready
        ),
        "standing_authority_preparation_only": (
            standing_launch_authority_recorded and not standing_scope_satisfied
        ),
        "still_missing_current_scope": not standing_scope_satisfied,
        "still_missing_current_turn_scope": not standing_scope_satisfied,
        "current_turn_scope_missing_fields": (
            [] if standing_scope_satisfied else list(CURRENT_TURN_APPROVAL_REQUIRED_FIELDS)
        ),
        "activation_next_action_sequence_consumable_under_recorded_standing_launch_authority": (
            standing_scope_satisfied
        ),
        "activation_next_action_sequence_consumable_under_recorded_standing_debug_authority": (
            standing_scope_satisfied
        ),
        "fresh_separate_activation_approval_required": (
            ready and not standing_scope_satisfied
        ),
        "active_runtime_window_requires_standing_or_current_scope": True,
        "max_running_ark_servers": 2,
        "three_ark_servers_allowed": False,
        "two_server_cap_policy": two_server_cap_policy(),
        "restart_with_connected_players_allowed_without_warning": False,
        "raw_player_text_capture_allowed": False,
        "raw_player_text_logging_allowed": False,
        "secret_capture_allowed": False,
        "secret_or_webhook_output_allowed": False,
        "recommended_notice_text": recommended_notice_text(request),
        "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
        "approved_evidence_bundle_checker_accepted": False,
        "approved_evidence_bundle_acceptance_required": True,
        "approved_evidence_bundle_acceptance_requirement": approved_evidence_bundle_acceptance_requirement(),
        "prepared_actions_remain_notice_only_or_request_only": True,
        "standing_launch_authority_counts_as_approved_runtime_evidence": False,
        "standing_debug_authority_counts_as_approved_runtime_evidence": False,
        "standing_launch_authority_counts_toward_sdk": False,
        "standing_debug_authority_counts_toward_sdk": False,
        "standing_authority_counts_as_runtime_progress": False,
        "standing_authority_counts_as_sdk_progress": False,
        "standing_authority_grants_runtime_readiness": False,
        "standing_authority_grants_public_sdk_readiness": False,
        "standing_authority_grants_activation_readiness": False,
        "standing_authority_authorizes_discord_send": False,
        "standing_authority_authorizes_runtime_evidence": standing_scope_satisfied,
        "standing_authority_authorizes_marker_env_changes": standing_scope_satisfied,
        "standing_authority_authorizes_server_restart": standing_scope_satisfied,
        "grants_readiness_claims": False,
        "checker_default_sends_discord": False,
        "checker_default_touches_ark": False,
        "checker_default_reads_live_logs": False,
        "checker_default_edits_markers_or_env": False,
        "activation_authority_requirement": (
            "recorded standing launch authority or fresh exact current-turn operator authorization"
        ),
        **FALSE_FLAGS,
    }


def main() -> int:
    args = parse_args()
    report = build_report(args)
    if args.json or not report["ready"]:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "player_principal_lifecycle_activation_preconditions_ready=true "
            "activation_authorized_by_this_report=false "
            "server_operations_authorized=false "
            "runtime_capture_authorized=false "
            "discord_authorized=false "
            "counts_toward_sdk=false "
            "counts_toward_p0_dependency_chain=false "
            "fresh_current_turn_operator_authorization_required_before_activation="
            f"{str(report['fresh_current_turn_operator_authorization_required_before_activation']).lower()} "
            "standing_launch_authority_recorded="
            f"{str(report['standing_launch_authority_recorded']).lower()} "
            "standing_debug_authority_recorded="
            f"{str(report['standing_debug_authority_recorded']).lower()} "
            "allowed_by_recorded_standing_debug_authority="
            f"{str(report['allowed_by_recorded_standing_debug_authority']).lower()} "
            "still_missing_current_scope="
            f"{str(report['still_missing_current_scope']).lower()}"
        )
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
