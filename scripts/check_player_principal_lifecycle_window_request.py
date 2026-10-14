#!/usr/bin/env python3
"""Validate an offline player-principal lifecycle window request pack.

This checker is pre-window strict by default. It validates a secret-free request pack before an
operator decides whether to approve a runtime evidence window. Post-window replay may tolerate
only a completed window whose sole stale condition is approved_window_expired. Acceptance does not
authorize server operations, marker/env changes, runtime capture, Discord, publication,
public identity, permissions/admin, commands, or SDK readiness.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import protected_paths
from player_principal_commit_validation import is_reviewed_obelisk_commit
from snapshot_evidence_pack import first_symlink_component, reject_symlink_component
from prepare_player_principal_lifecycle_window_request import (
    APPROVAL_RECEIPT_SCHEMA,
    APPROVAL_ATTESTATION_CURRENT_TURN,
    APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY,
    APPROVAL_SOURCE_CURRENT_TURN,
    APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY,
    APPROVAL_SCOPE_NON_AUTHORIZATION,
    APPROVAL_SCOPE_SCHEMA,
    APPROVAL_SCOPE_SOURCE_REQUIRED,
    APPROVAL_SCOPE_SOURCE_REQUIRED_STANDING_LAUNCH_AUTHORITY,
    APPROVAL_SCOPE_STATUS,
    APPROVAL_TEXT,
    APPROVED_BETA_NOTICE_PATH,
    AUTHORIZATION_FLAGS,
    BETA_RUNTIME_CHOREOGRAPHY_NON_AUTHORIZATION,
    BETA_RUNTIME_CHOREOGRAPHY_SCHEMA,
    BRIEF_NON_AUTHORIZATION,
    CHECKJOIN_STIMULUS_BOUNDARY_NON_AUTHORIZATION,
    CHECKJOIN_STIMULUS_BOUNDARY_SCHEMA,
    EXACT_TARGET_SCOPE_NON_AUTHORIZATION,
    EXACT_TARGET_SCOPE_SCHEMA,
    CURRENT_TURN_APPROVAL_REQUIRED_FIELDS,
    DIRECT_JOIN_PLAN_NON_AUTHORIZATION,
    DIRECT_JOIN_PLAN_SCHEMA,
    DRIFT_FIX_DEPLOYMENT_INTENT_NON_AUTHORIZATION,
    DRIFT_FIX_DEPLOYMENT_INTENT_TYPE,
    EXPECTED_BINARY_SHA256,
    EXPECTED_SERVER_BINARY_PATH,
    FORBIDDEN_MARKERS,
    HANDLE_NEW_PLAYER_FUNCTION,
    MAX_APPROVED_WINDOW_SECONDS,
    MAX_OPERATOR_APPROVAL_LEAD_SECONDS,
    MAX_REQUEST_PREPARATION_LEAD_SECONDS,
    MIN_APPROVED_WINDOW_SECONDS,
    NON_CLAIMS,
    OPERATOR_APPROVAL_RECEIPT_NON_CLAIMS,
    PASSIVE_WAIT_BOUNDARY_NON_AUTHORIZATION,
    PASSIVE_WAIT_BOUNDARY_SCHEMA,
    PLAYER_NOTICE_ACTION_NON_AUTHORIZATION,
    PLAYER_NOTICE_ACTION_SCHEMA,
    PLAYER_PRESENCE_SAFETY_NON_AUTHORIZATION,
    PLAYER_PRESENCE_SAFETY_SCHEMA,
    PLANNED_OBELISK_BUILD_ARTIFACT_KIND,
    PLANNED_OBELISK_BUILD_IDENTITY_NON_AUTHORIZATION,
    PLANNED_OBELISK_BUILD_IDENTITY_SCHEMA,
    PUBLIC_SDK_READY_ALIAS_RE,
    REQUIRED_ENV,
    REQUEST_ROLLBACK_DELTA,
    REPLAY_NON_AUTHORIZATION,
    RUNTIME_TRIPLET_CONTRACT_NON_AUTHORIZATION,
    RUNTIME_TRIPLET_CONTRACT_SCHEMA,
    RUN_ID_RE,
    SCHEMA,
    SESSION_START_REJECTED_REQUIRED_ARGUMENTS,
    SESSION_START_REJECTED_REQUIRED_CALL,
    SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS,
    SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES,
    SESSION_START_REJECTED_REQUIRED_FUNCTION,
    STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT,
    UTC_RE,
    WINDOW_MARKERS,
    artifact_binding,
    beta_runtime_choreography,
    bound_artifact,
    checkjoin_stimulus_boundary,
    contains_forbidden_public_sdk_alias,
    current_turn_approval_scope,
    deployment_intent,
    diagnostic_candidates_enabled,
    direct_join_plan,
    env_lines,
    exact_target_scope,
    is_forbidden_exact_target_alias,
    markdown_request,
    passive_wait_boundary,
    player_notice_action,
    player_presence_safety,
    post_window_replay_contract,
    post_run_verification_commands,
    request_pack_digest,
    requested_wait_window_seconds,
    rollback_plan,
    run_id_for_window_start,
    runtime_triplet_contract,
)


REPORT_SCHEMA = "obelisk.player-principal-lifecycle-window-request-check.v1"
SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = protected_paths.approved_offline_workspace_roots()
EVIDENCE_ROOT = APPROVED_OFFLINE_WORKSPACE_ROOTS[0] / "live-validation-logs"
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_TOP_LEVEL_KEYS = frozenset(
    (
        "schema",
        "status",
        "approval_required",
        "prepared_at_utc",
        "target",
        "exact_target_scope",
        "run_id",
        "ark_binary_sha256",
        "server_binary_path",
        "obelisk_commit",
        "planned_obelisk_build_identity",
        "approved_window",
        "restart_expectation",
        "final_posture",
        "diagnostic_candidates_enabled",
        "authorization_flags",
        "user_policy",
        "notice_path",
        "player_notice_action",
        "direct_join_plan",
        "player_presence_safety",
        "copied_evidence_dir",
        "copied_log_path",
        "window_manifest_path",
        "observer_env_file",
        "runtime_triplet_contract",
        "post_window_replay_contract",
        "current_turn_approval_scope",
        "deployment_intent",
        "passive_wait_boundary",
        "marker_set",
        "forbidden_markers",
        "operator_live_ops_brief",
        "rollback",
        "non_claims",
    )
)
EXPECTED_TARGET_KEYS = frozenset(("instance", "map"))
EXPECTED_WINDOW_KEYS = frozenset(("start_utc", "end_utc"))
EXPECTED_ROLLBACK_KEYS = frozenset(
    ("owner", "delta", "marker_state_dir", "stable_marker_paths", "observer_marker_paths")
)
EXPECTED_ROLLBACK_STABLE_MARKER_PATH_KEYS = frozenset(("enable_process_event_hook", "disable_plugins"))
EXPECTED_ROLLBACK_OBSERVER_MARKER_PATH_KEYS = frozenset(
    (
        "allow_observer_debug_window",
        "allow_experimental_observers",
        "enable_player_principal_lifecycle_observer",
    )
)
EXPECTED_OPERATOR_BRIEF_KEYS = frozenset(
    (
        "target",
        "exact_target_scope",
        "feature_gates",
        "server_binary",
        "marker_changes",
        "env_snapshot",
        "start_restart_stop_window",
        "notice_path",
        "player_notice_action",
        "direct_join_plan",
        "player_presence_safety",
        "user_policy",
        "evidence_capture",
        "artifact_binding",
        "deployment_intent",
        "runtime_triplet_contract",
        "passive_wait_boundary",
        "rollback",
        "post_run_stable_posture",
        "approval_boundary",
        "non_authorization",
    )
)
EXPECTED_SERVER_BINARY_KEYS = frozenset(("path", "sha256"))
EXPECTED_FEATURE_GATE_KEYS = frozenset(
    (
        "observer",
        "plugins_disabled",
        "process_event_hook",
        "dispatch_limit",
        "log_limit",
        "candidate_diagnostics",
        "scanner_debug_and_callback_escape_gates",
    )
)
EXPECTED_MARKER_CHANGE_KEYS = frozenset(("set", "forbidden"))
EXPECTED_WINDOW_BRIEF_KEYS = frozenset(("start_utc", "end_utc", "expectation", "final_posture"))
EXPECTED_EVIDENCE_CAPTURE_KEYS = frozenset(
    (
        "request_pack_path",
        "copied_evidence_dir",
        "copied_log_path",
        "window_manifest_path",
        "observer_env_file",
        "observer_env_path",
        "operator_approval_request_path",
        "operator_approval_receipt_path",
        "operator_approval_receipt_required",
        "preflight_pre_path",
        "preflight_post_path",
        "single_module_summary",
        "copied_log_only",
    )
)
EXPECTED_ARTIFACT_BINDING_KEYS = frozenset(
    (
        "run_id",
        "copied_evidence_dir",
        "copied_log_path",
        "window_manifest_path",
        "required_sidecars",
        "binding_claim",
        "non_authorization",
    )
)
EXPECTED_ARTIFACT_BINDING_SIDECAR_KEYS = frozenset(
    (
        "window_request_json",
        "observer_window_env",
        "operator_approval_request_md",
        "operator_approval_receipt_json",
        "preflight_pre_json",
        "preflight_post_json",
        "window_manifest_env",
        "copied_obelisk_log",
    )
)
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
EXPECTED_PASSIVE_WAIT_BOUNDARY_KEYS = frozenset(
    (
        "schema",
        "target",
        "requested_wait_window_seconds",
        "max_requested_wait_window_seconds",
        "requested_wait_window_seconds_checked_only",
        "requested_wait_window_authorizes_current_turn_approval",
        "requested_wait_window_authorizes_deploy_or_restart",
        "requested_wait_window_authorizes_runtime_capture",
        "requested_wait_window_counts_as_approved_runtime_evidence",
        "wait_only_or_passive_monitor_authorizes_deploy_or_restart",
        "passive_monitor_ticks_authorize_runtime_capture",
        "player_presence_detection_authorizes_followup",
        "snapshots_or_diagnostics_count_as_approved_runtime_evidence",
        "active_followup_requires_fresh_exact_current_turn_scope",
        "active_followup_requires_recorded_standing_launch_authority",
        "non_authorization",
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
EXPECTED_BETA_RUNTIME_CHOREOGRAPHY_KEYS = frozenset(
    (
        "schema",
        "classification",
        "target",
        "tester_count_required",
        "exactly_one_tester_required",
        "single_tester_only",
        "direct_target_join_required",
        "direct_join_route",
        "cluster_transfer_required",
        "cluster_transfer_allowed",
        "extra_transfer_server_required",
        "reconnect_before_exact_checkjoin_allowed",
        "logout_before_exact_checkjoin_allowed",
        "wait_for_exact_checkjoin_before_logout_required",
        "logout_or_cluster_transfer_or_reconnect_before_exact_checkjoin_allowed",
        "logout_cluster_transfer_reconnect_before_exact_checkjoin_or_window_close_allowed",
        "mixed_transfer_reconnect_same_approved_window_allowed",
        "approved_window_must_not_mix_direct_join_transfer_or_reconnect",
        "observer_gate_required_before_logout",
        "observer_gate",
        "tester_instruction",
        "forbidden_same_window_actions",
        "stale_or_diagnostic_exact_checkjoin_boundary",
        "choreography_authorizes_discord",
        "choreography_authorizes_runtime_capture",
        "choreography_authorizes_server_operations",
        "approved_runtime_evidence",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_evidence",
        "counts_toward_sdk",
        "counts_toward_p0_dependency_chain",
        "runtime_ready",
        "public_sdk_ready",
        "non_authorization",
    )
)
EXPECTED_BETA_RUNTIME_CHOREOGRAPHY_OBSERVER_GATE_KEYS = frozenset(
    (
        "required_role",
        "required_function",
        "required_call",
        "required_copied_bool_fields",
        "required_copied_bool_values",
        "wait_until_observer_sees_exact_checkjoin_or_window_closes",
        "logout_before_observer_gate_or_window_close_allowed",
    )
)
EXPECTED_BETA_RUNTIME_CHOREOGRAPHY_FORBIDDEN_ACTIONS = [
    "second_tester_join",
    "cluster_transfer",
    "logout_before_exact_checkjoin_or_window_close",
    "reconnect_before_exact_checkjoin_or_window_close",
    "mixed_transfer_and_reconnect_flow",
]
EXPECTED_CHECKJOIN_STIMULUS_BOUNDARY_KEYS = frozenset(
    (
        "schema",
        "classification",
        "exact_call",
        "accepted_observer_line_without_current_window_sibling_set_is_promotable",
        "diagnostic_tail_without_approved_sibling_set_is_promotable",
        "stale_or_order_mismatched_line_is_promotable",
        "stimulus_clue_for_future_choreography",
        "approved_sibling_set_required",
        "approved_sibling_set_roles_required",
        "approved_runtime_evidence",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_evidence",
        "runtime_ready",
        "public_sdk_ready",
        "non_authorization",
    )
)
EXPECTED_CHECKJOIN_STIMULUS_BOUNDARY_ROLES = [
    "session_start",
    "session_start_rejected",
    "session_end",
]
EXPECTED_CURRENT_TURN_APPROVAL_SCOPE_KEYS = frozenset(
    (
        "schema",
        "status",
        "source_required",
        "standing_approval_allowed",
        "request_pack_authorizes_deploy_or_runtime",
        "missing_or_ambiguous_scope_blocks_window",
        "required_operator_approval_fields",
        "required_named_scope",
        "non_authorization",
    )
)
EXPECTED_REQUIRED_NAMED_SCOPE_KEYS = frozenset(
    (
        "target",
        "exact_target_instance_map",
        "marker_env_gates",
        "restart_window",
        "player_presence_safety",
        "player_notice_action",
        "direct_join_plan",
        "rollback",
        "evidence_paths",
        "runtime_triplet_contract",
        "passive_wait_boundary",
        "final_posture",
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
EXPECTED_PLAYER_NOTICE_ACTION_KEYS = frozenset(
    (
        "schema",
        "required",
        "notice_path",
        "approved_notice_path_must_be_named",
        "dry_run_required_before_send",
        "real_notice_send_required_before_activation",
        "send_performed_by_request_pack",
        "request_pack_authorizes_discord",
        "activation_allowed_before_notice_sent",
        "evidence_required",
        "activation_blocker",
        "non_authorization",
    )
)
EXPECTED_PLAYER_PRESENCE_SAFETY_KEYS = frozenset(
    (
        "schema",
        "target",
        "restart_expectation",
        "connected_player_check_required_before_restart",
        "rcon_broadcast_required_if_players_connected",
        "restart_must_be_cancelled_or_rescheduled_if_players_remain_connected",
        "passive_wait_preferred_after_activation",
        "linuxgsm_monitor_forbidden",
        "player_check_or_broadcast_authorized_by_request_pack",
        "non_authorization",
    )
)
EXPECTED_MARKER_ENV_GATE_KEYS = frozenset(("markers", "env_snapshot"))
EXPECTED_RESTART_SCOPE_KEYS = frozenset(("start_utc", "end_utc", "expectation"))
EXPECTED_DEPLOYMENT_INTENT_KEYS = frozenset(
    (
        "intent_type",
        "status",
        "planned_obelisk_commit",
        "planned_obelisk_build_identity",
        "target",
        "request_only",
        "deployment_authorized",
        "restart_authorized",
        "runtime_capture_authorized",
        "counts_as_approved_runtime_evidence",
        "non_authorization",
    )
)
EXPECTED_PLANNED_OBELISK_BUILD_IDENTITY_KEYS = frozenset(
    (
        "schema",
        "obelisk_commit",
        "build_artifact",
        "non_authorization",
    )
)
EXPECTED_PLANNED_OBELISK_BUILD_ARTIFACT_KEYS = frozenset(
    (
        "available",
        "source",
        "artifact_kind",
        "artifact_name",
        "artifact_sha256",
        "size_bytes",
    )
)
ALLOWED_PLANNED_OBELISK_BUILD_ARTIFACT_SOURCES = frozenset(
    ("not_provided", "path_sha256", "operator_supplied_sha256")
)
EXPECTED_POST_RUN_KEYS = frozenset(
    (
        "required",
        "expected",
        "stable_markers_preserved",
        "observer_markers_removed",
        "verification_commands",
    )
)
EXPECTED_REPLAY_CONTRACT_KEYS = frozenset(("required", "offline_only", "sidecars", "checks", "non_authorization"))
EXPECTED_REPLAY_CONTRACT_SIDECAR_KEYS = frozenset(
    (
        "request_pack_path",
        "observer_env_path",
        "operator_approval_request_path",
        "operator_approval_receipt_path",
        "preflight_pre_path",
        "preflight_post_path",
        "window_manifest_path",
        "copied_log_path",
    )
)
POST_WINDOW_REPLAY_REQUIRED_SIDECAR_FILES = (
    ("preflight_pre", "preflight-pre.json"),
    ("preflight_post", "preflight-post.json"),
    ("window_manifest", "window-manifest.env"),
    ("copied_obelisk_log", "Obelisk.log"),
)
EXPECTED_AUTHORIZATION_FLAG_KEYS = frozenset(AUTHORIZATION_FLAGS)
EXPECTED_REPLAY_CONTRACT_CHECK_KEYS = frozenset(("window_manifest_replay",))
EXPECTED_OPERATOR_APPROVAL_RECEIPT_TOP_LEVEL_KEYS = frozenset(
    (
        "schema",
        "status",
        "receipt_completed",
        "operator_current_turn_approval_recorded",
        "standing_launch_authority_recorded",
        "standing_launch_authority_satisfies_operator_approval",
        "approval_scope",
        "bound_request_pack",
        "bound_artifacts",
        "request_pack_digest",
        "operator_completion",
        "non_authorization_flags",
        "non_claims",
    )
)
EXPECTED_OPERATOR_APPROVAL_RECEIPT_SCOPE_KEYS = frozenset(
    (
        "scope_type",
        "standing_approval",
        "reusable",
        "future_windows_authorized",
        "scope_expansion_authorized",
        "unbound_artifacts_authorized",
    )
)
EXPECTED_OPERATOR_APPROVAL_RECEIPT_BOUND_REQUEST_KEYS = frozenset(
    (
        "run_id",
        "prepared_at_utc",
        "target",
        "exact_target_scope",
        "approved_window",
        "obelisk_commit",
        "planned_obelisk_build_identity",
        "ark_binary_sha256",
        "server_binary_path",
        "restart_expectation",
        "final_posture",
        "user_policy",
        "notice_path",
        "player_notice_action",
        "direct_join_plan",
        "player_presence_safety",
        "copied_evidence_dir",
        "copied_log_path",
        "window_manifest_path",
        "rollback",
        "passive_wait_boundary",
        "current_turn_approval_scope",
        "runtime_triplet_contract",
        "deployment_intent",
    )
)
EXPECTED_OPERATOR_APPROVAL_RECEIPT_BOUND_ARTIFACTS_KEYS = frozenset(
    ("window_request_json", "observer_window_env", "operator_approval_request_md")
)
EXPECTED_OPERATOR_APPROVAL_RECEIPT_ARTIFACT_KEYS = frozenset(("path", "sha256", "size_bytes"))
EXPECTED_OPERATOR_APPROVAL_RECEIPT_COMPLETION_KEYS = frozenset(
    ("approval_recorded_at_utc", "approved_by_role", "approval_source", "attestation")
)
EXPECTED_OPERATOR_APPROVAL_RECEIPT_FLAG_KEYS = frozenset(
    (
        "request_pack_acceptance_authorizes_runtime",
        "generated_template_authorizes_runtime",
        "server_operations_authorized_by_template",
        "runtime_work_authorized_by_template",
        "discord_authorized",
        "discord_send_authorized",
        "current_turn_scope_authorized",
        "marker_env_changes_authorized",
        "runtime_capture_authorized",
        "runtime_window_authorized",
        "github_publication_authorized",
        "publication_authorized",
        "promotion_ready",
        "public_abi_ready",
        "public_sdk_ready",
        "runtime_ready",
        "route_ready",
        "v1_completion_ready",
        "sdk_accounting_counts_as_completed_surface",
        "p0_accounting_counts_as_promoted_surface",
        "secrets_included",
        "player_private_data_included",
    )
)
EXPECTED_OPERATOR_APPROVAL_RECEIPT_NON_CLAIMS = OPERATOR_APPROVAL_RECEIPT_NON_CLAIMS
ALLOWED_RESTART_EXPECTATIONS = frozenset(("none", "start", "restart"))
ALLOWED_FINAL_POSTURES = frozenset(("stable",))
ALLOWED_USER_POLICIES = frozenset(("no_regular_users", "operator_approved_beta_users"))
FORBIDDEN_VALUE_RE = re.compile(
    r"(?:steam|eos|unique[_-]?net|player[_-]?(?:id|name|data)|\bip(?:v4|v6)?\b|tribe[_-]?id|"
    r"platform[_-]?ids?|transfer[_-]?ids?|private[_-]?(?:identifier|user[_-]?data)|"
    r"chat[_-]?(?:text|message|payload)|command[_-]?(?:text|message|payload)|"
    r"permission[_-]?state|admin[_-]?state|"
    r"resourcehandle|gobjects?|fnames?|fname[_-]?(?:index|id)|gobject[_-]?(?:index|id)|"
    r"uobject|ue[_-]?pointer|raw[_-]?(?:params?|payload|pointer|trace|buffers?)|"
    r"object[_-]?(?:address|name|coordinates?|coords)|"
    r"(?:identity|identifier|player|steam|eos)[_-]?hash|hashed[_-]?(?:private|identity|identifier|player))",
    re.IGNORECASE,
)
POSITIVE_CAPABILITY_RE = re.compile(
    r"(?:public[_ -]?(?:sdk|abi|player[_ -]?identity)|"
    r"(?:(?:request[_ -]?pack|window[_ -]?request|preflight|(?:completed[_ -]?)?receipt|"
    r"operator[_ -]?approval[_ -]?(?:request|receipt)|operator[_ -]?request|"
    r"approval[_ -]?request|window[_ -]?manifest|observer[_ -]?(?:window[_ -]?)?env|"
    r"window[_ -]?env|env(?:ironment)?|(?:source[_ -]?)?markers?|copied[_ -]?(?:log|bundle)|"
    r"stale[_ -]?bundle|(?:evidence[_ -]?)?closure[_ -]?request|sidecars?|artifacts?)[_ -]?"
    r"(?:counts?[_ -]?as|is|are|proves?|provides?|authorizes?|approves?)[_ -]?"
    r"approved[_ -]?runtime[_ -]?evidence)|"
    r"(?:(?:dry[_ -]?run[_ -]?notice|sent[_ -]?notice|confirmed[_ -]?notice|"
    r"beta[_ -]?notice|notice[_ -]?report|guarded[_ -]?beta[_ -]?notice[_ -]?action|"
    r"(?:evidence[_ -]?)?closure[_ -]?request)[_ -]?"
    r"(?:counts?[_ -]?as|is|are|proves?|provides?|authorizes?|approves?|records?|"
    r"constitutes|grants?|contributes?[_ -]?to)[_ -]?"
    r"(?:approved[_ -]?runtime[_ -]?evidence|runtime[_ -]?(?:work|capture|window)|"
    r"server[_ -]?operations?|live[_ -]?log[_ -]?(?:read|permission|access)|"
    r"public[_ -]?sdk|sdk[_ -]?progress|v1[_ -]?completion|p0[_ -]?progress|"
    r"current[_ -]?turn[_ -]?(?:operator[_ -]?)?(?:approval|authorization)))|"
    r"(?:stable|complete|full|production)[_ -]?(?:v1[_ -]?)?(?:sdk[_ -]?)?claim[_ -]?"
    r"(?:(?:is|are)[_ -]?)?(?:allowed|ready|enabled|supported)|"
    r"(?:stable|complete|full|production)[_ -]?sdk[_ -]?(?:(?:is|are)[_ -]?)?(?:ready|allowed|claim)|"
    r"(?:v1[_ -]?(?:sdk[_ -]?)?(?:completion|complete)|sdk[_ -]?v1[_ -]?completion)[_ -]?"
    r"(?:(?:is|are)[_ -]?)?(?:ready|readiness|complete|completed|allowed|enabled|supported)|"
    r"stable[_ -]?release[_ -]?contract[_ -]?claim[_ -]?(?:(?:is|are)[_ -]?)?allowed|"
    r"player[_ -]?identity[_ -]?(?:(?:is|are)[_ -]?)?(?:promotion|ready|readiness)|"
    r"(?:sdk|runtime|runtime[_ -]?work|route|lookup|permissions?|admin|command(?:s|[_ -]?(?:reply|response|routing|support))?|"
    r"plugin[_ -]?delivery|mutation|return[_ -]?override|resourcehandle)[_ -]?(?:(?:is|are)[_ -]?)?"
    r"(?:ready|readiness|enabled|allowed|authorized|supported|promoted|delivered)|"
    r"command[_ -]?(?:reply|response|routing|support)|"
    r"(?:lookup|mutation|return[_ -]?override)[_ -]?(?:(?:is|are)[_ -]?)?allowed)",
    re.IGNORECASE,
)
OPERATIONAL_AUTHORIZATION_CLAIM_RE = re.compile(
    r"(?:(?:server|runtime)[_ -]?(?:operations?|work|capture|observation)[_ -]?"
    r"(?:(?:is|are)[_ -]?)?(?:ready|readiness|enabled|allowed|authorized|approved)|"
    r"(?:(?:live|server|obelisk)[_ -]?logs?[_ -]?(?:reads?|tails?|access|permission|"
    r"capture|collection)?|(?:reads?|tails?)[_ -]?(?:live|server|obelisk)[_ -]?logs?)[_ -]?"
    r"(?:(?:is|are)[_ -]?)?(?:allowed|authorized|approved|ready|enabled)|"
    r"(?:server[_ -]?)?(?:starts?|stops?|restarts?)[_ -]?(?:(?:is|are)[_ -]?)?"
    r"(?:allowed|authorized|approved|ready|enabled)|"
    r"(?:marker|env|environment|state)[_ -]?(?:changes?|edits?|ops|operations?)[_ -]?"
    r"(?:(?:is|are)[_ -]?)?(?:allowed|authorized|approved|ready|enabled)|"
    r"(?:discord|github|publication|publishing|release|tag)[_ -]?(?:(?:is|are)[_ -]?)?"
    r"(?:allowed|authorized|approved|ready|enabled|published))",
    re.IGNORECASE,
)
CURRENT_TURN_APPROVAL_CLAIM_RE = re.compile(
    r"(?:(?:request[_ -]?pack|window[_ -]?request|preflight|(?:completed[_ -]?)?receipt|"
    r"operator[_ -]?approval[_ -]?(?:request|receipt)|operator[_ -]?request|"
    r"approval[_ -]?request|window[_ -]?manifest|observer[_ -]?(?:window[_ -]?)?env|"
    r"window[_ -]?env|env(?:ironment)?|(?:source[_ -]?)?markers?|copied[_ -]?(?:log|bundle)|"
    r"stale[_ -]?bundle|(?:evidence[_ -]?)?closure[_ -]?request|sidecars?|artifacts?|"
    r"generated[_ -]?template|operator[_ -]?live[_ -]?ops[_ -]?brief)"
    r"[_ -]?(?:counts?[_ -]?as|is|are|proves?|provides?|authorizes?|approves?|records?|constitutes|grants?)"
    r"[_ -]?(?:current[_ -]?turn[_ -]?(?:operator[_ -]?)?(?:approval|authorization)|"
    r"operator[_ -]?approval|runtime[_ -]?window[_ -]?approval)|"
    r"(?:current[_ -]?turn[_ -]?(?:operator[_ -]?)?(?:approval|authorization)|operator[_ -]?approval)"
    r"[_ -]?(?:(?:is|are)[_ -]?)?(?:recorded|complete|completed|granted|approved|authorized))",
    re.IGNORECASE,
)
PASSIVE_WAIT_APPROVAL_CLAIM_RE = re.compile(
    r"(?:(?:passive(?:[_ -]?(?:wait|monitor|tick|snapshot|detection))?|wait[_ -]?only|"
    r"player[_ -]?presence|diagnostic[_ -]?summar(?:y|ies))"
    r"(?:[_ -]?(?:counts?[_ -]?as|is|are|provides?|grants?|authorizes?|approves?|records?|constitutes))?"
    r"[_ -]?(?!not\b)(?:current[_ -]?turn[_ -]?(?:operator[_ -]?)?(?:approval|authorization)|"
    r"operator[_ -]?approval|runtime[_ -]?window[_ -]?approval|approval|authorization|authorized|approved|"
    r"deploy(?:ment)?|restart|runtime[_ -]?capture|approved[_ -]?runtime[_ -]?evidence))",
    re.IGNORECASE,
)
NEGATED_CAPABILITY_ACTION_RE = re.compile(
    r"\b(?:does\s+not|do\s+not|doesn't|don't|cannot|can't|must\s+not|never|no|not)\s+"
    r"(?:claim|promote|authorize|enable|allow|support|deliver|provide|expose|log|make|mark|"
    r"report|treat|set|capture|collect|record)\b",
    re.IGNORECASE,
)
NEGATION_SCOPE_SPLIT_RE = re.compile(r"[,.;\n]|\s+\b(?:and|but|then|however|unless)\b\s+", re.IGNORECASE)
NEGATED_BOUNDARY_PREFIX_RE = re.compile(
    r"\b(?:without|forbidden|reject(?:ed|s)?|fail[-_ ]closed(?:\s+on)?)\s*:?\s*$",
    re.IGNORECASE,
)
NEGATED_CAPABILITY_SUFFIX_RE = re.compile(
    r"^\s+(?:remains?|stays?|is|are)?\s*(?:blocked|not\s+(?:ready|enabled|authorized|allowed)|"
    r"unauthorized|unsupported)\b",
    re.IGNORECASE,
)
FORBIDDEN_POSITIVE_SIDECAR_STATUS_KEYS = frozenset(
    (
        "accepted",
        "approved",
        "complete",
        "completed",
        "current_turn_authorized",
        "current_turn_runtime_authorized",
        "current_turn_scope_authorized",
        "current_turn_scope_ready",
        "ready",
        "runtime_authorized",
    )
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


@dataclass
class Validation:
    blockers: list[dict[str, Any]]
    payload: dict[str, Any] | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request_json", type=Path, help="window-request.json from the request pack.")
    parser.add_argument("--env-file", type=Path, required=True, help="observer-window.env from the same request pack.")
    parser.add_argument(
        "--operator-request",
        type=Path,
        help="operator-approval-request.md from the same request pack; defaults to the sibling file.",
    )
    parser.add_argument(
        "--operator-approval-receipt",
        type=Path,
        help="Completed operator-approval-receipt.json from the same request pack; required for post-window replay.",
    )
    parser.add_argument(
        "--post-window-replay",
        action="store_true",
        help="Replay completed evidence after the window; tolerates only approved_window_expired.",
    )
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def approved_offline_workspace_roots() -> tuple[Path, ...]:
    return protected_paths.approved_offline_workspace_roots()


def evidence_root() -> Path:
    return approved_offline_workspace_roots()[0] / "live-validation-logs"


def parse_utc(value: str) -> datetime | None:
    if not UTC_RE.fullmatch(value):
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def read_json(path: Path) -> dict[str, Any]:
    reject_symlink_component(path, "request_json")
    resolved = protected_paths.reject_protected_input_path(
        path,
        "request_json",
        protected_root=SERVER_ROOT,
        approved_roots=approved_offline_workspace_roots(),
    )
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"request_json is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("request_json must be a JSON object")
    return payload


def read_env(path: Path, blockers: list[dict[str, Any]]) -> list[str]:
    reject_symlink_component(path, "env_file")
    resolved = protected_paths.reject_protected_input_path(
        path,
        "env_file",
        protected_root=SERVER_ROOT,
        approved_roots=approved_offline_workspace_roots(),
    )
    lines: list[str] = []
    seen: set[str] = set()
    for line_number, raw in enumerate(resolved.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            add(blockers, "env_line_not_key_value", f"env_file:{line_number}")
            continue
        key, value = line.split("=", 1)
        if key in seen:
            add(blockers, "env_key_duplicate", key)
        seen.add(key)
        if not re.fullmatch(r"[A-Z0-9_]+", key):
            add(blockers, "env_key_unsafe", key)
        if "\n" in value or "\r" in value:
            add(blockers, "env_value_multiline", key)
        lines.append(f"{key}={value}")
    return lines


def read_text_sidecar(path: Path, label: str, blockers: list[dict[str, Any]]) -> str | None:
    try:
        reject_symlink_component(path, label)
        resolved = protected_paths.reject_protected_input_path(
            path,
            label,
            protected_root=SERVER_ROOT,
            approved_roots=approved_offline_workspace_roots(),
        )
        return resolved.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        add(blockers, f"{label}_unreadable", label, path=str(path), error=str(exc))
        return None


def validate_request_pack_sidecar_paths(
    *,
    request_json_path: Path,
    env_file_path: Path,
    operator_request_path: Path,
    blockers: list[dict[str, Any]],
) -> None:
    expected_names = {
        "request_json": "window-request.json",
        "env_file": "observer-window.env",
        "operator_request": "operator-approval-request.md",
    }
    paths = {
        "request_json": request_json_path,
        "env_file": env_file_path,
        "operator_request": operator_request_path,
    }
    resolved: dict[str, Path] = {}
    for label, path in paths.items():
        if path.name != expected_names[label]:
            add(
                blockers,
                f"{label}_filename_mismatch",
                label,
                expected=expected_names[label],
                actual=path.name,
            )
        try:
            resolved[label] = path.expanduser().resolve(strict=True)
        except OSError as exc:
            add(blockers, f"{label}_path_unresolved", label, path=str(path), error=str(exc))
    request_parent = resolved.get("request_json")
    if request_parent is None:
        return
    request_dir = request_parent.parent
    for label in ("env_file", "operator_request"):
        sidecar = resolved.get(label)
        if sidecar is not None and sidecar.parent != request_dir:
            add(
                blockers,
                f"{label}_not_sibling_of_request_json",
                label,
                expected_dir=str(request_dir),
                actual_dir=str(sidecar.parent),
            )


def payload_uses_standing_launch_authority(payload: dict[str, Any]) -> bool:
    return (
        payload.get("approval_required") == STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT
        or (
            isinstance(payload.get("current_turn_approval_scope"), dict)
            and payload["current_turn_approval_scope"].get("source_required")
            == APPROVAL_SCOPE_SOURCE_REQUIRED_STANDING_LAUNCH_AUTHORITY
        )
    )


def validate_operator_approval_receipt_path(
    *,
    request_json_path: Path,
    receipt_path: Path,
    blockers: list[dict[str, Any]],
) -> None:
    if receipt_path.name == "operator-approval-receipt.template.json":
        add(
            blockers,
            "operator_approval_receipt_template_path_not_completed_receipt",
            "operator_approval_receipt",
            expected="operator-approval-receipt.json",
            actual=receipt_path.name,
        )
    if receipt_path.name != "operator-approval-receipt.json":
        add(
            blockers,
            "operator_approval_receipt_filename_mismatch",
            "operator_approval_receipt",
            expected="operator-approval-receipt.json",
            actual=receipt_path.name,
        )
    try:
        request_dir = request_json_path.expanduser().resolve(strict=True).parent
        resolved_receipt = receipt_path.expanduser().resolve(strict=True)
    except OSError as exc:
        add(blockers, "operator_approval_receipt_path_unresolved", "operator_approval_receipt", path=str(receipt_path), error=str(exc))
        return
    if resolved_receipt.parent != request_dir:
        add(
            blockers,
            "operator_approval_receipt_not_sibling_of_request_json",
            "operator_approval_receipt",
            expected_dir=str(request_dir),
            actual_dir=str(resolved_receipt.parent),
        )


def require_keys(
    obj: Any,
    *,
    required: frozenset[str],
    label: str,
    blockers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not isinstance(obj, dict):
        add(blockers, f"{label}_not_object", label)
        return None
    missing = required - set(obj)
    unexpected = set(obj) - required
    if missing:
        add(blockers, f"{label}_missing_required", label, missing=sorted(missing))
    if unexpected:
        add(blockers, f"{label}_unexpected_keys", label, unexpected=sorted(unexpected))
    return obj


def string_at(payload: dict[str, Any], key: str, blockers: list[dict[str, Any]]) -> str | None:
    value = payload.get(key)
    if not isinstance(value, str):
        add(blockers, f"{key}_not_string", key)
        return None
    return value


def contains_unnegated_positive_capability_claim(value: str) -> bool:
    for pattern in (
        POSITIVE_CAPABILITY_RE,
        OPERATIONAL_AUTHORIZATION_CLAIM_RE,
        CURRENT_TURN_APPROVAL_CLAIM_RE,
        PASSIVE_WAIT_APPROVAL_CLAIM_RE,
        PUBLIC_SDK_READY_ALIAS_RE,
    ):
        for match in pattern.finditer(value):
            if not is_negated_for_match(value, match.start()) and not is_negated_after_match(value, match.end()):
                return True
    return False


def normalized_sidecar_status_token(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).casefold()).strip("_")


def preceding_negation_scope(value: str, start: int) -> str:
    return NEGATION_SCOPE_SPLIT_RE.split(value[:start])[-1]


def is_negated_for_match(value: str, start: int) -> bool:
    prefix = preceding_negation_scope(value, start)
    return bool(NEGATED_CAPABILITY_ACTION_RE.search(prefix) or NEGATED_BOUNDARY_PREFIX_RE.search(prefix))


def is_negated_after_match(value: str, end: int) -> bool:
    return bool(NEGATED_CAPABILITY_SUFFIX_RE.match(value[end:]))


def find_forbidden_claim(value: Any, trail: str = "$") -> tuple[str, str] | None:
    if trail in ("$.non_claims", "$.operator_live_ops_brief.marker_changes.forbidden"):
        return None
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if (
                normalized_sidecar_status_token(key) in FORBIDDEN_POSITIVE_SIDECAR_STATUS_KEYS
                and sidecar_status_value_is_positive(child)
            ):
                return str(child), child_trail
            found = find_forbidden_claim(child, child_trail)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_forbidden_claim(child, f"{trail}[{index}]")
            if found is not None:
                return found
    elif isinstance(value, str) and contains_unnegated_positive_capability_claim(value):
        return value, trail
    return None


def sidecar_status_value_is_positive(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return normalized_sidecar_status_token(value) in {
            "1",
            "accepted",
            "allowed",
            "approved",
            "authorized",
            "complete",
            "completed",
            "done",
            "enabled",
            "present",
            "ready",
            "true",
            "yes",
        }
    if isinstance(value, dict):
        return any(sidecar_status_value_is_positive(child) for child in value.values())
    if isinstance(value, list):
        return any(sidecar_status_value_is_positive(child) for child in value)
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
                and sidecar_status_value_is_positive(child)
            ):
                matches.append(child_trail)
            if (
                mentions_handle_new_player(child)
                and normalized_sidecar_status_token(key)
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


def validate_secret_free(value: Any, blockers: list[dict[str, Any]], trail: str = "$") -> None:
    if trail in (
        "$.forbidden_markers",
        "$.non_claims",
        "$.operator_live_ops_brief.marker_changes.forbidden",
        "$.post_window_replay_contract",
    ):
        return
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if FORBIDDEN_VALUE_RE.search(str(key)) and child not in (False, None, [], {}):
                add(blockers, "forbidden_private_or_ue_key", child_trail, value=str(key))
            validate_secret_free(child, blockers, child_trail)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_secret_free(child, blockers, f"{trail}[{index}]")
    elif isinstance(value, str):
        for match in FORBIDDEN_VALUE_RE.finditer(value):
            if not is_negated_for_match(value, match.start()):
                add(blockers, "forbidden_private_or_ue_value", trail, value=value)
                break


def validate_paths(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    run_id = payload.get("run_id")
    if not isinstance(run_id, str):
        return
    approved_roots = approved_offline_workspace_roots()
    expected_dir = evidence_root() / run_id
    if os.environ.get("OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES") == "1":
        for key in ("copied_evidence_dir", "copied_log_path", "window_manifest_path"):
            value = payload.get(key)
            if not isinstance(value, str):
                continue
            path = Path(value).expanduser()
            status = protected_paths.protected_path_status(
                path,
                protected_root=SERVER_ROOT,
                approved_roots=approved_roots,
            )
            try:
                relative = status.resolved.relative_to(approved_roots[0].resolve())
            except ValueError:
                continue
            if relative.parts and relative.parts[0].startswith("obelisk-test-player-principal-"):
                expected_dir = approved_roots[0] / relative.parts[0] / "live-validation-logs" / run_id
                break
    expected_paths = {
        "copied_evidence_dir": expected_dir,
        "copied_log_path": expected_dir / "Obelisk.log",
        "window_manifest_path": expected_dir / "window-manifest.env",
    }
    for key, expected in expected_paths.items():
        value = payload.get(key)
        if not isinstance(value, str):
            add(blockers, f"{key}_not_string", key)
            continue
        path = Path(value).expanduser()
        symlink = first_symlink_component(path)
        if symlink is not None:
            add(blockers, f"{key}_symlink_component", key, symlink=str(symlink))
        status = protected_paths.protected_path_status(
            path,
            protected_root=SERVER_ROOT,
            approved_roots=approved_roots,
        )
        if status.protected:
            add(blockers, f"{key}_under_protected_server_root", key, resolved=str(status.resolved))
        if not status.approved_offline_workspace:
            add(blockers, f"{key}_not_approved_offline_workspace", key, resolved=str(status.resolved))
        if status.resolved != expected.resolve():
            add(blockers, f"{key}_not_exact_expected_path", key, expected=str(expected), resolved=str(status.resolved))


def validate_post_window_replay_contract(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    contract = require_keys(
        payload.get("post_window_replay_contract"),
        required=EXPECTED_REPLAY_CONTRACT_KEYS,
        label="post_window_replay_contract",
        blockers=blockers,
    )
    if contract is None:
        return
    require_keys(
        contract.get("sidecars"),
        required=EXPECTED_REPLAY_CONTRACT_SIDECAR_KEYS,
        label="post_window_replay_contract_sidecars",
        blockers=blockers,
    )
    require_keys(
        contract.get("checks"),
        required=EXPECTED_REPLAY_CONTRACT_CHECK_KEYS,
        label="post_window_replay_contract_checks",
        blockers=blockers,
    )
    try:
        expected = post_window_replay_contract(payload)
    except (KeyError, TypeError):
        return
    if contract != expected:
        add(blockers, "post_window_replay_contract_mismatch", "post_window_replay_contract", expected=expected, actual=contract)
    if contract.get("non_authorization") != REPLAY_NON_AUTHORIZATION:
        add(
            blockers,
            "post_window_replay_contract_non_authorization_mismatch",
            "post_window_replay_contract.non_authorization",
            expected=REPLAY_NON_AUTHORIZATION,
            actual=contract.get("non_authorization"),
        )
    sidecars = contract.get("sidecars")
    if not isinstance(sidecars, dict):
        return
    for key, expected_name in (
        ("request_pack_path", "window-request.json"),
        ("observer_env_path", "observer-window.env"),
        ("operator_approval_request_path", "operator-approval-request.md"),
        ("operator_approval_receipt_path", "operator-approval-receipt.json"),
        ("preflight_pre_path", "preflight-pre.json"),
        ("preflight_post_path", "preflight-post.json"),
        ("window_manifest_path", "window-manifest.env"),
        ("copied_log_path", "Obelisk.log"),
    ):
        value = sidecars.get(key)
        if not isinstance(value, str):
            add(blockers, f"post_window_replay_contract_{key}_not_string", f"post_window_replay_contract.sidecars.{key}")
            continue
        path = Path(value).expanduser()
        symlink = first_symlink_component(path)
        if symlink is not None:
            add(blockers, f"post_window_replay_contract_{key}_symlink_component", f"post_window_replay_contract.sidecars.{key}", symlink=str(symlink))
        status = protected_paths.protected_path_status(
            path,
            protected_root=SERVER_ROOT,
            approved_roots=approved_offline_workspace_roots(),
        )
        if status.protected:
            add(blockers, f"post_window_replay_contract_{key}_under_protected_server_root", f"post_window_replay_contract.sidecars.{key}", resolved=str(status.resolved))
        if not status.approved_offline_workspace:
            add(blockers, f"post_window_replay_contract_{key}_not_approved_offline_workspace", f"post_window_replay_contract.sidecars.{key}", resolved=str(status.resolved))
        if status.resolved.name != expected_name:
            add(blockers, f"post_window_replay_contract_{key}_filename_mismatch", f"post_window_replay_contract.sidecars.{key}", expected=expected_name, actual=status.resolved.name)
        expected_path = Path(expected["sidecars"][key]).resolve()
        if status.resolved != expected_path:
            add(
                blockers,
                f"post_window_replay_contract_{key}_not_exact_expected_path",
                f"post_window_replay_contract.sidecars.{key}",
                expected=str(expected_path),
                resolved=str(status.resolved),
            )


def validate_exact_target_scope(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    scope = require_keys(
        payload.get("exact_target_scope"),
        required=EXPECTED_EXACT_TARGET_SCOPE_KEYS,
        label="exact_target_scope",
        blockers=blockers,
    )
    if scope is None:
        return
    if scope.get("schema") != EXACT_TARGET_SCOPE_SCHEMA:
        add(blockers, "exact_target_scope_schema_mismatch", "exact_target_scope.schema")
    target = payload.get("target")
    if isinstance(target, dict):
        if scope.get("instance") != target.get("instance"):
            add(blockers, "exact_target_scope_instance_mismatch", "exact_target_scope.instance")
        if scope.get("map") != target.get("map"):
            add(blockers, "exact_target_scope_map_mismatch", "exact_target_scope.map")
    for key in ("instance_alias_allowed", "map_alias_allowed"):
        if scope.get(key) is not False:
            add(blockers, f"exact_target_scope_{key}_not_false", f"exact_target_scope.{key}")
    for key in ("approval_must_name_exact_instance_and_map", "target_matches_request_target"):
        if scope.get(key) is not True:
            add(blockers, f"exact_target_scope_{key}_not_true", f"exact_target_scope.{key}")
    if scope.get("non_authorization") != EXACT_TARGET_SCOPE_NON_AUTHORIZATION:
        add(
            blockers,
            "exact_target_scope_non_authorization_mismatch",
            "exact_target_scope.non_authorization",
            expected=EXACT_TARGET_SCOPE_NON_AUTHORIZATION,
            actual=scope.get("non_authorization"),
        )
    try:
        expected = exact_target_scope(payload)
    except (KeyError, TypeError):
        return
    if scope != expected:
        add(blockers, "exact_target_scope_mismatch", "exact_target_scope", expected=expected, actual=scope)


def validate_passive_wait_boundary(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    boundary = require_keys(
        payload.get("passive_wait_boundary"),
        required=EXPECTED_PASSIVE_WAIT_BOUNDARY_KEYS,
        label="passive_wait_boundary",
        blockers=blockers,
    )
    if boundary is None:
        return
    require_keys(
        boundary.get("target"),
        required=EXPECTED_TARGET_KEYS,
        label="passive_wait_boundary_target",
        blockers=blockers,
    )
    if boundary.get("schema") != PASSIVE_WAIT_BOUNDARY_SCHEMA:
        add(blockers, "passive_wait_boundary_schema_mismatch", "passive_wait_boundary.schema")
    if boundary.get("target") != payload.get("target"):
        add(blockers, "passive_wait_boundary_target_mismatch", "passive_wait_boundary.target")
    wait_seconds = boundary.get("requested_wait_window_seconds")
    expected_wait_seconds = requested_wait_window_seconds(payload)
    if not isinstance(wait_seconds, int):
        add(blockers, "passive_wait_boundary_requested_wait_window_seconds_not_int", "passive_wait_boundary.requested_wait_window_seconds")
    elif wait_seconds != expected_wait_seconds:
        add(
            blockers,
            "passive_wait_boundary_requested_wait_window_seconds_mismatch",
            "passive_wait_boundary.requested_wait_window_seconds",
            expected=expected_wait_seconds,
            actual=wait_seconds,
        )
    if isinstance(wait_seconds, int) and wait_seconds > MAX_APPROVED_WINDOW_SECONDS:
        add(
            blockers,
            "passive_wait_boundary_requested_wait_window_seconds_too_long",
            "passive_wait_boundary.requested_wait_window_seconds",
            max_seconds=MAX_APPROVED_WINDOW_SECONDS,
            actual=wait_seconds,
        )
    if boundary.get("max_requested_wait_window_seconds") != MAX_APPROVED_WINDOW_SECONDS:
        add(
            blockers,
            "passive_wait_boundary_max_requested_wait_window_seconds_mismatch",
            "passive_wait_boundary.max_requested_wait_window_seconds",
            expected=MAX_APPROVED_WINDOW_SECONDS,
            actual=boundary.get("max_requested_wait_window_seconds"),
        )
    if boundary.get("requested_wait_window_seconds_checked_only") is not True:
        add(
            blockers,
            "passive_wait_boundary_requested_wait_window_seconds_checked_only_not_true",
            "passive_wait_boundary.requested_wait_window_seconds_checked_only",
        )
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
            add(blockers, f"passive_wait_boundary_{key}_not_false", f"passive_wait_boundary.{key}")
    standing_authority = payload_uses_standing_launch_authority(payload)
    if boundary.get("active_followup_requires_fresh_exact_current_turn_scope") is not (not standing_authority):
        add(
            blockers,
            "passive_wait_boundary_active_followup_requires_fresh_exact_current_turn_scope_mismatch",
            "passive_wait_boundary.active_followup_requires_fresh_exact_current_turn_scope",
            expected=not standing_authority,
            actual=boundary.get("active_followup_requires_fresh_exact_current_turn_scope"),
        )
    if boundary.get("active_followup_requires_recorded_standing_launch_authority") is not standing_authority:
        add(
            blockers,
            "passive_wait_boundary_active_followup_requires_recorded_standing_launch_authority_mismatch",
            "passive_wait_boundary.active_followup_requires_recorded_standing_launch_authority",
            expected=standing_authority,
            actual=boundary.get("active_followup_requires_recorded_standing_launch_authority"),
        )
    if boundary.get("non_authorization") != PASSIVE_WAIT_BOUNDARY_NON_AUTHORIZATION:
        add(
            blockers,
            "passive_wait_boundary_non_authorization_mismatch",
            "passive_wait_boundary.non_authorization",
            expected=PASSIVE_WAIT_BOUNDARY_NON_AUTHORIZATION,
            actual=boundary.get("non_authorization"),
        )
    try:
        expected = passive_wait_boundary(payload)
    except (KeyError, TypeError):
        return
    if boundary != expected:
        add(blockers, "passive_wait_boundary_mismatch", "passive_wait_boundary", expected=expected, actual=boundary)


def validate_checkjoin_stimulus_boundary(
    boundary_value: Any,
    blockers: list[dict[str, Any]],
) -> None:
    boundary = require_keys(
        boundary_value,
        required=EXPECTED_CHECKJOIN_STIMULUS_BOUNDARY_KEYS,
        label="direct_join_plan_beta_runtime_choreography_checkjoin_stimulus_boundary",
        blockers=blockers,
    )
    if boundary is None:
        return
    if boundary.get("schema") != CHECKJOIN_STIMULUS_BOUNDARY_SCHEMA:
        add(
            blockers,
            "direct_join_plan_checkjoin_stimulus_boundary_schema_mismatch",
            "direct_join_plan.beta_runtime_choreography.stale_or_diagnostic_exact_checkjoin_boundary.schema",
        )
    if boundary.get("classification") != "stale_or_diagnostic_exact_checkjoin_is_stimulus_only":
        add(
            blockers,
            "direct_join_plan_checkjoin_stimulus_boundary_classification_mismatch",
            "direct_join_plan.beta_runtime_choreography.stale_or_diagnostic_exact_checkjoin_boundary.classification",
        )
    if boundary.get("exact_call") != "ShooterGameMode.CheckJoinInProgress(1,0)":
        add(
            blockers,
            "direct_join_plan_checkjoin_stimulus_boundary_exact_call_mismatch",
            "direct_join_plan.beta_runtime_choreography.stale_or_diagnostic_exact_checkjoin_boundary.exact_call",
        )
    for key in (
        "accepted_observer_line_without_current_window_sibling_set_is_promotable",
        "diagnostic_tail_without_approved_sibling_set_is_promotable",
        "stale_or_order_mismatched_line_is_promotable",
        "approved_runtime_evidence",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_evidence",
        "runtime_ready",
        "public_sdk_ready",
    ):
        if boundary.get(key) is not False:
            add(
                blockers,
                f"direct_join_plan_checkjoin_stimulus_boundary_{key}_not_false",
                f"direct_join_plan.beta_runtime_choreography.stale_or_diagnostic_exact_checkjoin_boundary.{key}",
            )
    for key in ("stimulus_clue_for_future_choreography", "approved_sibling_set_required"):
        if boundary.get(key) is not True:
            add(
                blockers,
                f"direct_join_plan_checkjoin_stimulus_boundary_{key}_not_true",
                f"direct_join_plan.beta_runtime_choreography.stale_or_diagnostic_exact_checkjoin_boundary.{key}",
            )
    if boundary.get("approved_sibling_set_roles_required") != EXPECTED_CHECKJOIN_STIMULUS_BOUNDARY_ROLES:
        add(
            blockers,
            "direct_join_plan_checkjoin_stimulus_boundary_roles_mismatch",
            "direct_join_plan.beta_runtime_choreography.stale_or_diagnostic_exact_checkjoin_boundary.approved_sibling_set_roles_required",
            expected=EXPECTED_CHECKJOIN_STIMULUS_BOUNDARY_ROLES,
            actual=boundary.get("approved_sibling_set_roles_required"),
        )
    if boundary.get("non_authorization") != CHECKJOIN_STIMULUS_BOUNDARY_NON_AUTHORIZATION:
        add(
            blockers,
            "direct_join_plan_checkjoin_stimulus_boundary_non_authorization_mismatch",
            "direct_join_plan.beta_runtime_choreography.stale_or_diagnostic_exact_checkjoin_boundary.non_authorization",
            expected=CHECKJOIN_STIMULUS_BOUNDARY_NON_AUTHORIZATION,
            actual=boundary.get("non_authorization"),
        )
    expected = checkjoin_stimulus_boundary()
    if boundary != expected:
        add(
            blockers,
            "direct_join_plan_checkjoin_stimulus_boundary_mismatch",
            "direct_join_plan.beta_runtime_choreography.stale_or_diagnostic_exact_checkjoin_boundary",
            expected=expected,
            actual=boundary,
        )


def validate_beta_runtime_choreography(
    payload: dict[str, Any],
    choreography_value: Any,
    blockers: list[dict[str, Any]],
) -> None:
    choreography = require_keys(
        choreography_value,
        required=EXPECTED_BETA_RUNTIME_CHOREOGRAPHY_KEYS,
        label="direct_join_plan_beta_runtime_choreography",
        blockers=blockers,
    )
    if choreography is None:
        return
    require_keys(
        choreography.get("target"),
        required=EXPECTED_TARGET_KEYS,
        label="direct_join_plan_beta_runtime_choreography_target",
        blockers=blockers,
    )
    observer_gate = require_keys(
        choreography.get("observer_gate"),
        required=EXPECTED_BETA_RUNTIME_CHOREOGRAPHY_OBSERVER_GATE_KEYS,
        label="direct_join_plan_beta_runtime_choreography_observer_gate",
        blockers=blockers,
    )
    validate_checkjoin_stimulus_boundary(
        choreography.get("stale_or_diagnostic_exact_checkjoin_boundary"),
        blockers,
    )
    if choreography.get("schema") != BETA_RUNTIME_CHOREOGRAPHY_SCHEMA:
        add(
            blockers,
            "direct_join_plan_beta_runtime_choreography_schema_mismatch",
            "direct_join_plan.beta_runtime_choreography.schema",
        )
    if choreography.get("classification") != "single_tester_direct_join_choreography_non_authorizing":
        add(
            blockers,
            "direct_join_plan_beta_runtime_choreography_classification_mismatch",
            "direct_join_plan.beta_runtime_choreography.classification",
        )
    if choreography.get("target") != payload.get("target"):
        add(
            blockers,
            "direct_join_plan_beta_runtime_choreography_target_mismatch",
            "direct_join_plan.beta_runtime_choreography.target",
        )
    if choreography.get("tester_count_required") != 1:
        add(
            blockers,
            "direct_join_plan_beta_runtime_choreography_tester_count_required_mismatch",
            "direct_join_plan.beta_runtime_choreography.tester_count_required",
            expected=1,
            actual=choreography.get("tester_count_required"),
        )
    for key in (
        "exactly_one_tester_required",
        "single_tester_only",
        "direct_target_join_required",
        "wait_for_exact_checkjoin_before_logout_required",
        "approved_window_must_not_mix_direct_join_transfer_or_reconnect",
    ):
        if choreography.get(key) is not True:
            add(
                blockers,
                f"direct_join_plan_beta_runtime_choreography_{key}_not_true",
                f"direct_join_plan.beta_runtime_choreography.{key}",
            )
    if choreography.get("direct_join_route") != "direct_join_exact_server_map":
        add(
            blockers,
            "direct_join_plan_beta_runtime_choreography_direct_join_route_mismatch",
            "direct_join_plan.beta_runtime_choreography.direct_join_route",
        )
    for key in (
        "cluster_transfer_required",
        "cluster_transfer_allowed",
        "extra_transfer_server_required",
        "reconnect_before_exact_checkjoin_allowed",
        "logout_before_exact_checkjoin_allowed",
        "logout_or_cluster_transfer_or_reconnect_before_exact_checkjoin_allowed",
        "logout_cluster_transfer_reconnect_before_exact_checkjoin_or_window_close_allowed",
        "mixed_transfer_reconnect_same_approved_window_allowed",
        "choreography_authorizes_discord",
        "choreography_authorizes_runtime_capture",
        "choreography_authorizes_server_operations",
        "approved_runtime_evidence",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_evidence",
        "counts_toward_sdk",
        "counts_toward_p0_dependency_chain",
        "runtime_ready",
        "public_sdk_ready",
    ):
        if choreography.get(key) is not False:
            add(
                blockers,
                f"direct_join_plan_beta_runtime_choreography_{key}_not_false",
                f"direct_join_plan.beta_runtime_choreography.{key}",
            )
    if choreography.get("observer_gate_required_before_logout") != "ShooterGameMode.CheckJoinInProgress(1,0)":
        add(
            blockers,
            "direct_join_plan_beta_runtime_choreography_observer_gate_required_before_logout_mismatch",
            "direct_join_plan.beta_runtime_choreography.observer_gate_required_before_logout",
        )
    expected_instruction = (
        "one tester direct-joins the exact target, waits in that session until the "
        "observer reports exact CheckJoinInProgress(1,0) or the approved window closes, "
        "then logs out once only when told"
    )
    if choreography.get("tester_instruction") != expected_instruction:
        add(
            blockers,
            "direct_join_plan_beta_runtime_choreography_tester_instruction_mismatch",
            "direct_join_plan.beta_runtime_choreography.tester_instruction",
        )
    if choreography.get("forbidden_same_window_actions") != EXPECTED_BETA_RUNTIME_CHOREOGRAPHY_FORBIDDEN_ACTIONS:
        add(
            blockers,
            "direct_join_plan_beta_runtime_choreography_forbidden_same_window_actions_mismatch",
            "direct_join_plan.beta_runtime_choreography.forbidden_same_window_actions",
            expected=EXPECTED_BETA_RUNTIME_CHOREOGRAPHY_FORBIDDEN_ACTIONS,
            actual=choreography.get("forbidden_same_window_actions"),
        )
    if choreography.get("non_authorization") != BETA_RUNTIME_CHOREOGRAPHY_NON_AUTHORIZATION:
        add(
            blockers,
            "direct_join_plan_beta_runtime_choreography_non_authorization_mismatch",
            "direct_join_plan.beta_runtime_choreography.non_authorization",
            expected=BETA_RUNTIME_CHOREOGRAPHY_NON_AUTHORIZATION,
            actual=choreography.get("non_authorization"),
        )
    if isinstance(observer_gate, dict):
        if observer_gate.get("required_role") != "session_start_rejected":
            add(
                blockers,
                "direct_join_plan_beta_runtime_choreography_observer_gate_required_role_mismatch",
                "direct_join_plan.beta_runtime_choreography.observer_gate.required_role",
            )
        if observer_gate.get("required_function") != "ShooterGameMode.CheckJoinInProgress":
            add(
                blockers,
                "direct_join_plan_beta_runtime_choreography_observer_gate_required_function_mismatch",
                "direct_join_plan.beta_runtime_choreography.observer_gate.required_function",
            )
        if observer_gate.get("required_call") != SESSION_START_REJECTED_REQUIRED_CALL:
            add(
                blockers,
                "direct_join_plan_beta_runtime_choreography_observer_gate_required_call_mismatch",
                "direct_join_plan.beta_runtime_choreography.observer_gate.required_call",
                expected=SESSION_START_REJECTED_REQUIRED_CALL,
                actual=observer_gate.get("required_call"),
            )
        if observer_gate.get("required_copied_bool_fields") != SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS:
            add(
                blockers,
                "direct_join_plan_beta_runtime_choreography_observer_gate_copied_bool_fields_mismatch",
                "direct_join_plan.beta_runtime_choreography.observer_gate.required_copied_bool_fields",
                expected=SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS,
                actual=observer_gate.get("required_copied_bool_fields"),
            )
        if observer_gate.get("required_copied_bool_values") != SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES:
            add(
                blockers,
                "direct_join_plan_beta_runtime_choreography_observer_gate_copied_bool_values_mismatch",
                "direct_join_plan.beta_runtime_choreography.observer_gate.required_copied_bool_values",
                expected=SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES,
                actual=observer_gate.get("required_copied_bool_values"),
            )
        if observer_gate.get("wait_until_observer_sees_exact_checkjoin_or_window_closes") is not True:
            add(
                blockers,
                "direct_join_plan_beta_runtime_choreography_observer_gate_wait_until_exact_checkjoin_or_window_closes_not_true",
                "direct_join_plan.beta_runtime_choreography.observer_gate.wait_until_observer_sees_exact_checkjoin_or_window_closes",
            )
        if observer_gate.get("logout_before_observer_gate_or_window_close_allowed") is not False:
            add(
                blockers,
                "direct_join_plan_beta_runtime_choreography_observer_gate_logout_before_gate_or_window_close_not_false",
                "direct_join_plan.beta_runtime_choreography.observer_gate.logout_before_observer_gate_or_window_close_allowed",
            )
    try:
        expected = beta_runtime_choreography(payload)
    except (KeyError, TypeError):
        return
    if choreography != expected:
        add(
            blockers,
            "direct_join_plan_beta_runtime_choreography_mismatch",
            "direct_join_plan.beta_runtime_choreography",
            expected=expected,
            actual=choreography,
        )


def validate_direct_join_plan(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    plan = require_keys(
        payload.get("direct_join_plan"),
        required=EXPECTED_DIRECT_JOIN_PLAN_KEYS,
        label="direct_join_plan",
        blockers=blockers,
    )
    if plan is None:
        return
    require_keys(
        plan.get("target"),
        required=EXPECTED_TARGET_KEYS,
        label="direct_join_plan_target",
        blockers=blockers,
    )
    if plan.get("schema") != DIRECT_JOIN_PLAN_SCHEMA:
        add(blockers, "direct_join_plan_schema_mismatch", "direct_join_plan.schema")
    if plan.get("target") != payload.get("target"):
        add(blockers, "direct_join_plan_target_mismatch", "direct_join_plan.target")
    target = payload.get("target")
    if isinstance(target, dict):
        if plan.get("target_instance") != target.get("instance"):
            add(blockers, "direct_join_plan_target_instance_mismatch", "direct_join_plan.target_instance")
        if plan.get("target_map") != target.get("map"):
            add(blockers, "direct_join_plan_target_map_mismatch", "direct_join_plan.target_map")
        target_is_theisland = target.get("map") == "TheIsland"
        for key in ("target_map_is_theisland", "fastest_clean_theisland_direct_join"):
            if plan.get(key) is not target_is_theisland:
                add(blockers, f"direct_join_plan_{key}_mismatch", f"direct_join_plan.{key}")
    if plan.get("route") != "direct_join_exact_server_map":
        add(blockers, "direct_join_plan_route_mismatch", "direct_join_plan.route")
    if plan.get("direct_join_required") is not True:
        add(blockers, "direct_join_plan_direct_join_required_not_true", "direct_join_plan.direct_join_required")
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
            add(blockers, f"direct_join_plan_{key}_not_false", f"direct_join_plan.{key}")
    if plan.get("max_running_ark_servers") != 2:
        add(blockers, "direct_join_plan_max_running_ark_servers_mismatch", "direct_join_plan.max_running_ark_servers")
    if plan.get("approved_notice_path") != payload.get("notice_path"):
        add(blockers, "direct_join_plan_approved_notice_path_mismatch", "direct_join_plan.approved_notice_path")
    validate_beta_runtime_choreography(payload, plan.get("beta_runtime_choreography"), blockers)
    expected_wait_seconds = requested_wait_window_seconds(payload)
    if plan.get("organic_wait_window_seconds") != expected_wait_seconds:
        add(
            blockers,
            "direct_join_plan_organic_wait_window_seconds_mismatch",
            "direct_join_plan.organic_wait_window_seconds",
            expected=expected_wait_seconds,
            actual=plan.get("organic_wait_window_seconds"),
        )
    if plan.get("max_organic_wait_window_seconds") != MAX_APPROVED_WINDOW_SECONDS:
        add(
            blockers,
            "direct_join_plan_max_organic_wait_window_seconds_mismatch",
            "direct_join_plan.max_organic_wait_window_seconds",
            expected=MAX_APPROVED_WINDOW_SECONDS,
            actual=plan.get("max_organic_wait_window_seconds"),
        )
    for key in ("receipt_before_activation_required", "post_window_replay_requires_receipt"):
        if plan.get(key) is not True:
            add(blockers, f"direct_join_plan_{key}_not_true", f"direct_join_plan.{key}")
    if plan.get("non_authorization") != DIRECT_JOIN_PLAN_NON_AUTHORIZATION:
        add(
            blockers,
            "direct_join_plan_non_authorization_mismatch",
            "direct_join_plan.non_authorization",
            expected=DIRECT_JOIN_PLAN_NON_AUTHORIZATION,
            actual=plan.get("non_authorization"),
        )
    try:
        expected = direct_join_plan(payload)
    except (KeyError, TypeError):
        return
    if plan != expected:
        add(blockers, "direct_join_plan_mismatch", "direct_join_plan", expected=expected, actual=plan)


def validate_player_notice_action(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    action = require_keys(
        payload.get("player_notice_action"),
        required=EXPECTED_PLAYER_NOTICE_ACTION_KEYS,
        label="player_notice_action",
        blockers=blockers,
    )
    if action is None:
        return
    if action.get("schema") != PLAYER_NOTICE_ACTION_SCHEMA:
        add(blockers, "player_notice_action_schema_mismatch", "player_notice_action.schema")
    user_policy = payload.get("user_policy")
    notice_path = payload.get("notice_path")
    required = user_policy == "operator_approved_beta_users"
    if action.get("required") is not required:
        add(blockers, "player_notice_action_required_mismatch", "player_notice_action.required")
    if action.get("notice_path") != notice_path:
        add(blockers, "player_notice_action_notice_path_mismatch", "player_notice_action.notice_path")
    for key in (
        "approved_notice_path_must_be_named",
        "dry_run_required_before_send",
        "real_notice_send_required_before_activation",
    ):
        if action.get(key) is not required:
            add(blockers, f"player_notice_action_{key}_mismatch", f"player_notice_action.{key}")
    if action.get("send_performed_by_request_pack") is not False:
        add(blockers, "player_notice_action_send_performed_by_request_pack_not_false", "player_notice_action")
    if action.get("request_pack_authorizes_discord") is not False:
        add(blockers, "player_notice_action_request_pack_authorizes_discord_not_false", "player_notice_action")
    if action.get("activation_allowed_before_notice_sent") is not (not required):
        add(blockers, "player_notice_action_activation_allowed_before_notice_sent_mismatch", "player_notice_action")
    expected_evidence = "dry_run_output_and_send_confirmation_reference" if required else "not_applicable"
    if action.get("evidence_required") != expected_evidence:
        add(
            blockers,
            "player_notice_action_evidence_required_mismatch",
            "player_notice_action.evidence_required",
            expected=expected_evidence,
            actual=action.get("evidence_required"),
        )
    expected_blocker = "approved_dry_run_checked_beta_testers_notice_sent" if required else "no_player_notice_required"
    if action.get("activation_blocker") != expected_blocker:
        add(
            blockers,
            "player_notice_action_activation_blocker_mismatch",
            "player_notice_action.activation_blocker",
            expected=expected_blocker,
            actual=action.get("activation_blocker"),
        )
    if action.get("non_authorization") != PLAYER_NOTICE_ACTION_NON_AUTHORIZATION:
        add(
            blockers,
            "player_notice_action_non_authorization_mismatch",
            "player_notice_action.non_authorization",
            expected=PLAYER_NOTICE_ACTION_NON_AUTHORIZATION,
            actual=action.get("non_authorization"),
        )
    if required and notice_path != APPROVED_BETA_NOTICE_PATH:
        add(
            blockers,
            "player_notice_action_beta_notice_path_not_approved_beta_testers",
            "player_notice_action.notice_path",
            expected=APPROVED_BETA_NOTICE_PATH,
            actual=notice_path,
        )
    if not required and notice_path != "not_applicable":
        add(
            blockers,
            "player_notice_action_notice_path_set_for_no_regular_users",
            "player_notice_action.notice_path",
            expected="not_applicable",
            actual=notice_path,
        )
    try:
        expected = player_notice_action(payload)
    except (KeyError, TypeError):
        expected = None
    if expected is not None and action != expected:
        add(blockers, "player_notice_action_mismatch", "player_notice_action", expected=expected, actual=action)


def validate_player_presence_safety(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    safety = require_keys(
        payload.get("player_presence_safety"),
        required=EXPECTED_PLAYER_PRESENCE_SAFETY_KEYS,
        label="player_presence_safety",
        blockers=blockers,
    )
    if safety is None:
        return
    restart_expected = payload.get("restart_expectation") == "restart"
    if safety.get("schema") != PLAYER_PRESENCE_SAFETY_SCHEMA:
        add(blockers, "player_presence_safety_schema_mismatch", "player_presence_safety.schema")
    if safety.get("target") != payload.get("target"):
        add(blockers, "player_presence_safety_target_mismatch", "player_presence_safety.target")
    if safety.get("restart_expectation") != payload.get("restart_expectation"):
        add(blockers, "player_presence_safety_restart_expectation_mismatch", "player_presence_safety.restart_expectation")
    for key in (
        "connected_player_check_required_before_restart",
        "rcon_broadcast_required_if_players_connected",
        "restart_must_be_cancelled_or_rescheduled_if_players_remain_connected",
    ):
        if safety.get(key) is not restart_expected:
            add(blockers, f"player_presence_safety_{key}_mismatch", f"player_presence_safety.{key}")
    if safety.get("passive_wait_preferred_after_activation") is not True:
        add(blockers, "player_presence_safety_passive_wait_preferred_after_activation_not_true", "player_presence_safety")
    if safety.get("linuxgsm_monitor_forbidden") is not True:
        add(blockers, "player_presence_safety_linuxgsm_monitor_forbidden_not_true", "player_presence_safety")
    if safety.get("player_check_or_broadcast_authorized_by_request_pack") is not False:
        add(
            blockers,
            "player_presence_safety_player_check_or_broadcast_authorized_by_request_pack_not_false",
            "player_presence_safety",
        )
    if safety.get("non_authorization") != PLAYER_PRESENCE_SAFETY_NON_AUTHORIZATION:
        add(
            blockers,
            "player_presence_safety_non_authorization_mismatch",
            "player_presence_safety.non_authorization",
            expected=PLAYER_PRESENCE_SAFETY_NON_AUTHORIZATION,
            actual=safety.get("non_authorization"),
        )
    try:
        expected = player_presence_safety(payload)
    except (KeyError, TypeError):
        return
    if safety != expected:
        add(blockers, "player_presence_safety_mismatch", "player_presence_safety", expected=expected, actual=safety)


def validate_current_turn_approval_scope(payload: dict[str, Any], env: list[str], blockers: list[dict[str, Any]]) -> None:
    scope = require_keys(
        payload.get("current_turn_approval_scope"),
        required=EXPECTED_CURRENT_TURN_APPROVAL_SCOPE_KEYS,
        label="current_turn_approval_scope",
        blockers=blockers,
    )
    if scope is None:
        return
    named_scope = require_keys(
        scope.get("required_named_scope"),
        required=EXPECTED_REQUIRED_NAMED_SCOPE_KEYS,
        label="current_turn_approval_scope_required_named_scope",
        blockers=blockers,
    )
    if isinstance(named_scope, dict):
        require_keys(
            named_scope.get("target"),
            required=EXPECTED_TARGET_KEYS,
            label="current_turn_approval_scope_target",
            blockers=blockers,
        )
        require_keys(
            named_scope.get("exact_target_instance_map"),
            required=EXPECTED_EXACT_TARGET_SCOPE_KEYS,
            label="current_turn_approval_scope_exact_target_instance_map",
            blockers=blockers,
        )
        require_keys(
            named_scope.get("marker_env_gates"),
            required=EXPECTED_MARKER_ENV_GATE_KEYS,
            label="current_turn_approval_scope_marker_env_gates",
            blockers=blockers,
        )
        require_keys(
            named_scope.get("restart_window"),
            required=EXPECTED_RESTART_SCOPE_KEYS,
            label="current_turn_approval_scope_restart_window",
            blockers=blockers,
        )
        require_keys(
            named_scope.get("player_presence_safety"),
            required=EXPECTED_PLAYER_PRESENCE_SAFETY_KEYS,
            label="current_turn_approval_scope_player_presence_safety",
            blockers=blockers,
        )
        require_keys(
            named_scope.get("player_notice_action"),
            required=EXPECTED_PLAYER_NOTICE_ACTION_KEYS,
            label="current_turn_approval_scope_player_notice_action",
            blockers=blockers,
        )
        require_keys(
            named_scope.get("direct_join_plan"),
            required=EXPECTED_DIRECT_JOIN_PLAN_KEYS,
            label="current_turn_approval_scope_direct_join_plan",
            blockers=blockers,
        )
        require_keys(
            named_scope.get("rollback"),
            required=EXPECTED_ROLLBACK_KEYS,
            label="current_turn_approval_scope_rollback",
            blockers=blockers,
        )
        evidence_paths = require_keys(
            named_scope.get("evidence_paths"),
            required=EXPECTED_ARTIFACT_BINDING_SIDECAR_KEYS,
            label="current_turn_approval_scope_evidence_paths",
            blockers=blockers,
        )
        if isinstance(evidence_paths, dict):
            for key, value in evidence_paths.items():
                if not isinstance(value, str) or not value:
                    add(
                        blockers,
                        f"current_turn_approval_scope_evidence_path_{key}_not_named",
                        f"current_turn_approval_scope.required_named_scope.evidence_paths.{key}",
                    )
        require_keys(
            named_scope.get("runtime_triplet_contract"),
            required=EXPECTED_RUNTIME_TRIPLET_CONTRACT_KEYS,
            label="current_turn_approval_scope_runtime_triplet_contract",
            blockers=blockers,
        )
        require_keys(
            named_scope.get("passive_wait_boundary"),
            required=EXPECTED_PASSIVE_WAIT_BOUNDARY_KEYS,
            label="current_turn_approval_scope_passive_wait_boundary",
            blockers=blockers,
        )
    if scope.get("schema") != APPROVAL_SCOPE_SCHEMA:
        add(blockers, "current_turn_approval_scope_schema_mismatch", "current_turn_approval_scope.schema")
    try:
        expected = current_turn_approval_scope(payload, env)
    except (KeyError, TypeError):
        expected = None
    expected_status = expected.get("status") if isinstance(expected, dict) else APPROVAL_SCOPE_STATUS
    expected_source = (
        expected.get("source_required") if isinstance(expected, dict) else APPROVAL_SCOPE_SOURCE_REQUIRED
    )
    expected_standing_allowed = (
        expected.get("standing_approval_allowed") if isinstance(expected, dict) else False
    )
    if scope.get("status") != expected_status:
        add(
            blockers,
            "current_turn_approval_scope_status_mismatch",
            "current_turn_approval_scope.status",
            expected=expected_status,
            actual=scope.get("status"),
        )
    if scope.get("source_required") != expected_source:
        add(
            blockers,
            "current_turn_approval_scope_source_required_mismatch",
            "current_turn_approval_scope.source_required",
            expected=expected_source,
            actual=scope.get("source_required"),
        )
    if expected_standing_allowed is False and scope.get("standing_approval_allowed") is not False:
        add(blockers, "current_turn_approval_scope_standing_approval_allowed_not_false", "current_turn_approval_scope")
    elif expected_standing_allowed is True and scope.get("standing_approval_allowed") is not True:
        add(blockers, "current_turn_approval_scope_standing_approval_allowed_mismatch", "current_turn_approval_scope")
    if scope.get("request_pack_authorizes_deploy_or_runtime") is not False:
        add(
            blockers,
            "current_turn_approval_scope_request_pack_authorizes_deploy_or_runtime_not_false",
            "current_turn_approval_scope",
        )
    if scope.get("missing_or_ambiguous_scope_blocks_window") is not True:
        add(
            blockers,
            "current_turn_approval_scope_missing_or_ambiguous_scope_blocks_window_not_true",
            "current_turn_approval_scope",
        )
    if scope.get("required_operator_approval_fields") != CURRENT_TURN_APPROVAL_REQUIRED_FIELDS:
        add(
            blockers,
            "current_turn_approval_scope_required_fields_mismatch",
            "current_turn_approval_scope.required_operator_approval_fields",
            expected=CURRENT_TURN_APPROVAL_REQUIRED_FIELDS,
            actual=scope.get("required_operator_approval_fields"),
        )
    if scope.get("non_authorization") != APPROVAL_SCOPE_NON_AUTHORIZATION:
        add(
            blockers,
            "current_turn_approval_scope_non_authorization_mismatch",
            "current_turn_approval_scope.non_authorization",
            expected=APPROVAL_SCOPE_NON_AUTHORIZATION,
            actual=scope.get("non_authorization"),
        )
    if expected is None:
        return
    if scope != expected:
        add(blockers, "current_turn_approval_scope_mismatch", "current_turn_approval_scope", expected=expected, actual=scope)


def validate_planned_obelisk_build_identity(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    identity = require_keys(
        payload.get("planned_obelisk_build_identity"),
        required=EXPECTED_PLANNED_OBELISK_BUILD_IDENTITY_KEYS,
        label="planned_obelisk_build_identity",
        blockers=blockers,
    )
    if identity is None:
        return
    build_artifact = require_keys(
        identity.get("build_artifact"),
        required=EXPECTED_PLANNED_OBELISK_BUILD_ARTIFACT_KEYS,
        label="planned_obelisk_build_identity_build_artifact",
        blockers=blockers,
    )
    if identity.get("schema") != PLANNED_OBELISK_BUILD_IDENTITY_SCHEMA:
        add(blockers, "planned_obelisk_build_identity_schema_mismatch", "planned_obelisk_build_identity.schema")
    if identity.get("obelisk_commit") != payload.get("obelisk_commit"):
        add(
            blockers,
            "planned_obelisk_build_identity_commit_mismatch",
            "planned_obelisk_build_identity.obelisk_commit",
        )
    if identity.get("non_authorization") != PLANNED_OBELISK_BUILD_IDENTITY_NON_AUTHORIZATION:
        add(
            blockers,
            "planned_obelisk_build_identity_non_authorization_mismatch",
            "planned_obelisk_build_identity.non_authorization",
            expected=PLANNED_OBELISK_BUILD_IDENTITY_NON_AUTHORIZATION,
            actual=identity.get("non_authorization"),
        )
    if not isinstance(build_artifact, dict):
        return
    available = build_artifact.get("available")
    source = build_artifact.get("source")
    if available not in (True, False):
        add(blockers, "planned_obelisk_build_artifact_available_not_boolean", "planned_obelisk_build_identity.build_artifact.available")
    if source not in ALLOWED_PLANNED_OBELISK_BUILD_ARTIFACT_SOURCES:
        add(
            blockers,
            "planned_obelisk_build_artifact_source_invalid",
            "planned_obelisk_build_identity.build_artifact.source",
        )
    if available is False:
        if source != "not_provided":
            add(
                blockers,
                "planned_obelisk_build_artifact_unavailable_source_mismatch",
                "planned_obelisk_build_identity.build_artifact.source",
            )
        for key in ("artifact_kind", "artifact_name", "artifact_sha256", "size_bytes"):
            if build_artifact.get(key) is not None:
                add(
                    blockers,
                    f"planned_obelisk_build_artifact_unavailable_{key}_not_null",
                    f"planned_obelisk_build_identity.build_artifact.{key}",
                )
        return
    if available is True:
        if source == "not_provided":
            add(
                blockers,
                "planned_obelisk_build_artifact_available_source_not_provided",
                "planned_obelisk_build_identity.build_artifact.source",
            )
        if build_artifact.get("artifact_kind") != PLANNED_OBELISK_BUILD_ARTIFACT_KIND:
            add(
                blockers,
                "planned_obelisk_build_artifact_kind_mismatch",
                "planned_obelisk_build_identity.build_artifact.artifact_kind",
            )
        artifact_name = build_artifact.get("artifact_name")
        if not isinstance(artifact_name, str) or SAFE_TOKEN_RE.fullmatch(artifact_name) is None:
            add(
                blockers,
                "planned_obelisk_build_artifact_name_invalid",
                "planned_obelisk_build_identity.build_artifact.artifact_name",
            )
        elif contains_forbidden_public_sdk_alias(artifact_name):
            add(
                blockers,
                "planned_obelisk_build_artifact_name_alias_not_allowed",
                "planned_obelisk_build_identity.build_artifact.artifact_name",
                value=artifact_name,
            )
        artifact_sha256 = build_artifact.get("artifact_sha256")
        if not isinstance(artifact_sha256, str) or SHA256_RE.fullmatch(artifact_sha256) is None:
            add(
                blockers,
                "planned_obelisk_build_artifact_sha256_invalid",
                "planned_obelisk_build_identity.build_artifact.artifact_sha256",
            )
        size_bytes = build_artifact.get("size_bytes")
        if source == "path_sha256":
            if not isinstance(size_bytes, int) or size_bytes < 0:
                add(
                    blockers,
                    "planned_obelisk_build_artifact_size_bytes_invalid",
                    "planned_obelisk_build_identity.build_artifact.size_bytes",
                )
        elif source == "operator_supplied_sha256" and size_bytes is not None:
            add(
                blockers,
                "planned_obelisk_build_artifact_supplied_sha_size_bytes_not_null",
                "planned_obelisk_build_identity.build_artifact.size_bytes",
            )


def validate_deployment_intent(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    intent = require_keys(
        payload.get("deployment_intent"),
        required=EXPECTED_DEPLOYMENT_INTENT_KEYS,
        label="deployment_intent",
        blockers=blockers,
    )
    if intent is None:
        return
    require_keys(intent.get("target"), required=EXPECTED_TARGET_KEYS, label="deployment_intent_target", blockers=blockers)
    if intent.get("intent_type") != DRIFT_FIX_DEPLOYMENT_INTENT_TYPE:
        add(
            blockers,
            "deployment_intent_type_mismatch",
            "deployment_intent.intent_type",
            expected=DRIFT_FIX_DEPLOYMENT_INTENT_TYPE,
            actual=intent.get("intent_type"),
        )
    if intent.get("status") != "request_only_not_authorized":
        add(blockers, "deployment_intent_status_mismatch", "deployment_intent.status")
    if intent.get("planned_obelisk_commit") != payload.get("obelisk_commit"):
        add(blockers, "deployment_intent_obelisk_commit_mismatch", "deployment_intent.planned_obelisk_commit")
    if intent.get("planned_obelisk_build_identity") != payload.get("planned_obelisk_build_identity"):
        add(
            blockers,
            "deployment_intent_planned_obelisk_build_identity_mismatch",
            "deployment_intent.planned_obelisk_build_identity",
        )
    if intent.get("request_only") is not True:
        add(blockers, "deployment_intent_request_only_not_true", "deployment_intent.request_only")
    for key in (
        "deployment_authorized",
        "restart_authorized",
        "runtime_capture_authorized",
        "counts_as_approved_runtime_evidence",
    ):
        if intent.get(key) is not False:
            add(blockers, f"deployment_intent_{key}_not_false", f"deployment_intent.{key}")
    if intent.get("non_authorization") != DRIFT_FIX_DEPLOYMENT_INTENT_NON_AUTHORIZATION:
        add(
            blockers,
            "deployment_intent_non_authorization_mismatch",
            "deployment_intent.non_authorization",
            expected=DRIFT_FIX_DEPLOYMENT_INTENT_NON_AUTHORIZATION,
            actual=intent.get("non_authorization"),
        )
    try:
        expected = deployment_intent(payload)
    except (KeyError, TypeError):
        return
    if intent != expected:
        add(blockers, "deployment_intent_mismatch", "deployment_intent", expected=expected, actual=intent)


def validate_runtime_triplet_contract(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    contract = require_keys(
        payload.get("runtime_triplet_contract"),
        required=EXPECTED_RUNTIME_TRIPLET_CONTRACT_KEYS,
        label="runtime_triplet_contract",
        blockers=blockers,
    )
    if contract is None:
        return
    session_start = require_keys(
        contract.get("session_start_rejected"),
        required=EXPECTED_RUNTIME_TRIPLET_SESSION_START_KEYS,
        label="runtime_triplet_contract_session_start_rejected",
        blockers=blockers,
    )
    handle_new_player = require_keys(
        contract.get("handle_new_player_rejected_tuples"),
        required=EXPECTED_RUNTIME_TRIPLET_HANDLE_NEW_PLAYER_KEYS,
        label="runtime_triplet_contract_handle_new_player_rejected_tuples",
        blockers=blockers,
    )
    if contract.get("schema") != RUNTIME_TRIPLET_CONTRACT_SCHEMA:
        add(blockers, "runtime_triplet_contract_schema_mismatch", "runtime_triplet_contract.schema")
    if contract.get("planning_only") is not True:
        add(blockers, "runtime_triplet_contract_planning_only_not_true", "runtime_triplet_contract.planning_only")
    if contract.get("non_authorization") != RUNTIME_TRIPLET_CONTRACT_NON_AUTHORIZATION:
        add(
            blockers,
            "runtime_triplet_contract_non_authorization_mismatch",
            "runtime_triplet_contract.non_authorization",
            expected=RUNTIME_TRIPLET_CONTRACT_NON_AUTHORIZATION,
            actual=contract.get("non_authorization"),
        )
    if isinstance(session_start, dict):
        if session_start.get("event") != "session_start_rejected":
            add(blockers, "runtime_triplet_contract_session_start_event_mismatch", "runtime_triplet_contract.session_start_rejected.event")
        if session_start.get("required_function") != SESSION_START_REJECTED_REQUIRED_FUNCTION:
            add(
                blockers,
                "runtime_triplet_contract_session_start_function_mismatch",
                "runtime_triplet_contract.session_start_rejected.required_function",
                expected=SESSION_START_REJECTED_REQUIRED_FUNCTION,
                actual=session_start.get("required_function"),
            )
        if session_start.get("required_argument_tuple") != SESSION_START_REJECTED_REQUIRED_ARGUMENTS:
            add(
                blockers,
                "runtime_triplet_contract_session_start_argument_tuple_mismatch",
                "runtime_triplet_contract.session_start_rejected.required_argument_tuple",
                expected=SESSION_START_REJECTED_REQUIRED_ARGUMENTS,
                actual=session_start.get("required_argument_tuple"),
            )
        if session_start.get("required_call") != SESSION_START_REJECTED_REQUIRED_CALL:
            add(
                blockers,
                "runtime_triplet_contract_session_start_required_call_mismatch",
                "runtime_triplet_contract.session_start_rejected.required_call",
                expected=SESSION_START_REJECTED_REQUIRED_CALL,
                actual=session_start.get("required_call"),
            )
        if session_start.get("required_copied_bool_fields") != SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS:
            add(
                blockers,
                "runtime_triplet_contract_session_start_copied_bool_fields_mismatch",
                "runtime_triplet_contract.session_start_rejected.required_copied_bool_fields",
                expected=SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS,
                actual=session_start.get("required_copied_bool_fields"),
            )
        if session_start.get("required_copied_bool_values") != SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES:
            add(
                blockers,
                "runtime_triplet_contract_session_start_copied_bool_values_mismatch",
                "runtime_triplet_contract.session_start_rejected.required_copied_bool_values",
                expected=SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES,
                actual=session_start.get("required_copied_bool_values"),
            )
        for key in (
            "handle_new_player_rejected_tuple_allowed",
            "handle_new_player_rejected_tuple_alternative_allowed",
        ):
            if session_start.get(key) is not False:
                add(blockers, f"runtime_triplet_contract_session_start_{key}_not_false", f"runtime_triplet_contract.session_start_rejected.{key}")
    if isinstance(handle_new_player, dict):
        if handle_new_player.get("function") != HANDLE_NEW_PLAYER_FUNCTION:
            add(
                blockers,
                "runtime_triplet_contract_handle_new_player_function_mismatch",
                "runtime_triplet_contract.handle_new_player_rejected_tuples.function",
                expected=HANDLE_NEW_PLAYER_FUNCTION,
                actual=handle_new_player.get("function"),
            )
        for key in ("allowed_for_session_start_rejected", "alternative_for_session_start_rejected"):
            if handle_new_player.get(key) is not False:
                add(blockers, f"runtime_triplet_contract_handle_new_player_{key}_not_false", f"runtime_triplet_contract.handle_new_player_rejected_tuples.{key}")
        if handle_new_player.get("classification") != "stale_rejected_start_rule_only":
            add(
                blockers,
                "runtime_triplet_contract_handle_new_player_classification_mismatch",
                "runtime_triplet_contract.handle_new_player_rejected_tuples.classification",
            )
    expected = runtime_triplet_contract()
    if contract != expected:
        add(blockers, "runtime_triplet_contract_mismatch", "runtime_triplet_contract", expected=expected, actual=contract)
    for path in collect_stale_handle_new_player_rejected_start_rules(contract):
        add(blockers, "stale_handle_new_player_rejected_start_rule", path)


def args_for_env(payload: dict[str, Any]) -> argparse.Namespace:
    window = payload["approved_window"]
    return argparse.Namespace(
        instance=payload["target"]["instance"],
        map_name=payload["target"]["map"],
        run_id=payload["run_id"],
        obelisk_commit=payload["obelisk_commit"],
        approved_window_start_utc=window["start_utc"],
        approved_window_end_utc=window["end_utc"],
        binary_sha256=payload["ark_binary_sha256"],
        server_binary_path=payload["server_binary_path"],
        restart_expectation=payload["restart_expectation"],
        final_posture=payload["final_posture"],
        diagnostic_candidates_enabled=diagnostic_candidates_enabled(payload),
        user_policy=payload["user_policy"],
        notice_path=payload["notice_path"],
        rollback_owner=payload["rollback"]["owner"],
        output_dir=Path("."),
        json=True,
    )


def expected_operator_live_ops_brief(payload: dict[str, Any], env: list[str]) -> dict[str, Any] | None:
    try:
        window = payload["approved_window"]
        return {
            "target": payload["target"],
            "exact_target_scope": payload["exact_target_scope"],
            "feature_gates": {
                "observer": "player_principal_lifecycle_only",
                "plugins_disabled": True,
                "process_event_hook": True,
                "dispatch_limit": 0,
                "log_limit": 10,
                "candidate_diagnostics": "candidate_only_non_evidence"
                if payload.get("diagnostic_candidates_enabled")
                else False,
                "scanner_debug_and_callback_escape_gates": "forbidden",
            },
            "server_binary": {
                "path": payload["server_binary_path"],
                "sha256": payload["ark_binary_sha256"],
            },
            "marker_changes": {
                "set": payload["marker_set"],
                "forbidden": payload["forbidden_markers"],
            },
            "env_snapshot": env,
            "start_restart_stop_window": {
                "start_utc": window["start_utc"],
                "end_utc": window["end_utc"],
                "expectation": payload["restart_expectation"],
                "final_posture": payload["final_posture"],
            },
            "notice_path": payload["notice_path"],
            "player_notice_action": payload["player_notice_action"],
            "direct_join_plan": payload["direct_join_plan"],
            "player_presence_safety": payload["player_presence_safety"],
            "user_policy": payload["user_policy"],
            "evidence_capture": {
                "request_pack_path": payload["post_window_replay_contract"]["sidecars"]["request_pack_path"],
                "copied_evidence_dir": payload["copied_evidence_dir"],
                "copied_log_path": payload["copied_log_path"],
                "window_manifest_path": payload["window_manifest_path"],
                "observer_env_file": payload["observer_env_file"],
                "observer_env_path": payload["post_window_replay_contract"]["sidecars"]["observer_env_path"],
                "operator_approval_request_path": payload["post_window_replay_contract"]["sidecars"][
                    "operator_approval_request_path"
                ],
                "operator_approval_receipt_path": payload["post_window_replay_contract"]["sidecars"][
                    "operator_approval_receipt_path"
                ],
                "operator_approval_receipt_required": "completed_operator_receipt",
                "preflight_pre_path": payload["post_window_replay_contract"]["sidecars"]["preflight_pre_path"],
                "preflight_post_path": payload["post_window_replay_contract"]["sidecars"]["preflight_post_path"],
                "single_module_summary": "player_principal_lifecycle",
                "copied_log_only": True,
            },
            "artifact_binding": artifact_binding(payload),
            "deployment_intent": deployment_intent(payload),
            "runtime_triplet_contract": payload["runtime_triplet_contract"],
            "passive_wait_boundary": payload["passive_wait_boundary"],
            "rollback": payload["rollback"],
            "post_run_stable_posture": {
                "required": True,
                "expected": payload["final_posture"],
                "stable_markers_preserved": ["enable-process-event-hook", "disable-plugins"],
                "observer_markers_removed": True,
                "verification_commands": post_run_verification_commands(payload),
            },
            "approval_boundary": payload["approval_required"],
            "non_authorization": BRIEF_NON_AUTHORIZATION,
        }
    except (KeyError, TypeError):
        return None


def validate_operator_live_ops_brief(payload: dict[str, Any], env: list[str], blockers: list[dict[str, Any]]) -> None:
    brief = require_keys(
        payload.get("operator_live_ops_brief"),
        required=EXPECTED_OPERATOR_BRIEF_KEYS,
        label="operator_live_ops_brief",
        blockers=blockers,
    )
    if brief is None:
        return
    require_keys(
        brief.get("exact_target_scope"),
        required=EXPECTED_EXACT_TARGET_SCOPE_KEYS,
        label="operator_live_ops_brief_exact_target_scope",
        blockers=blockers,
    )
    require_keys(brief.get("feature_gates"), required=EXPECTED_FEATURE_GATE_KEYS, label="operator_live_ops_brief_feature_gates", blockers=blockers)
    require_keys(brief.get("server_binary"), required=EXPECTED_SERVER_BINARY_KEYS, label="operator_live_ops_brief_server_binary", blockers=blockers)
    require_keys(brief.get("marker_changes"), required=EXPECTED_MARKER_CHANGE_KEYS, label="operator_live_ops_brief_marker_changes", blockers=blockers)
    require_keys(brief.get("start_restart_stop_window"), required=EXPECTED_WINDOW_BRIEF_KEYS, label="operator_live_ops_brief_window", blockers=blockers)
    evidence_capture = require_keys(brief.get("evidence_capture"), required=EXPECTED_EVIDENCE_CAPTURE_KEYS, label="operator_live_ops_brief_evidence_capture", blockers=blockers)
    binding = require_keys(brief.get("artifact_binding"), required=EXPECTED_ARTIFACT_BINDING_KEYS, label="operator_live_ops_brief_artifact_binding", blockers=blockers)
    require_keys(
        brief.get("deployment_intent"),
        required=EXPECTED_DEPLOYMENT_INTENT_KEYS,
        label="operator_live_ops_brief_deployment_intent",
        blockers=blockers,
    )
    require_keys(
        brief.get("runtime_triplet_contract"),
        required=EXPECTED_RUNTIME_TRIPLET_CONTRACT_KEYS,
        label="operator_live_ops_brief_runtime_triplet_contract",
        blockers=blockers,
    )
    require_keys(
        brief.get("passive_wait_boundary"),
        required=EXPECTED_PASSIVE_WAIT_BOUNDARY_KEYS,
        label="operator_live_ops_brief_passive_wait_boundary",
        blockers=blockers,
    )
    require_keys(
        brief.get("direct_join_plan"),
        required=EXPECTED_DIRECT_JOIN_PLAN_KEYS,
        label="operator_live_ops_brief_direct_join_plan",
        blockers=blockers,
    )
    if isinstance(binding, dict):
        require_keys(
            binding.get("required_sidecars"),
            required=EXPECTED_ARTIFACT_BINDING_SIDECAR_KEYS,
            label="operator_live_ops_brief_artifact_binding_required_sidecars",
            blockers=blockers,
        )
    require_keys(brief.get("post_run_stable_posture"), required=EXPECTED_POST_RUN_KEYS, label="operator_live_ops_brief_post_run_stable_posture", blockers=blockers)
    if isinstance(evidence_capture, dict):
        if evidence_capture.get("operator_approval_receipt_required") != "completed_operator_receipt":
            add(
                blockers,
                "operator_live_ops_brief_receipt_required_not_completed_receipt",
                "operator_live_ops_brief.evidence_capture.operator_approval_receipt_required",
                expected="completed_operator_receipt",
                actual=evidence_capture.get("operator_approval_receipt_required"),
            )
        receipt_path = evidence_capture.get("operator_approval_receipt_path")
        if isinstance(receipt_path, str) and receipt_path.endswith(".template.json"):
            add(
                blockers,
                "operator_live_ops_brief_receipt_path_points_to_template",
                "operator_live_ops_brief.evidence_capture.operator_approval_receipt_path",
                value=receipt_path,
            )
    if brief.get("non_authorization") != BRIEF_NON_AUTHORIZATION:
        add(
            blockers,
            "operator_live_ops_brief_non_authorization_mismatch",
            "operator_live_ops_brief.non_authorization",
            expected=BRIEF_NON_AUTHORIZATION,
            actual=brief.get("non_authorization"),
        )
    if isinstance(binding, dict):
        try:
            expected_binding = artifact_binding(payload)
        except (KeyError, TypeError):
            expected_binding = None
        if expected_binding is not None and binding != expected_binding:
            add(
                blockers,
                "operator_live_ops_brief_artifact_binding_mismatch",
                "operator_live_ops_brief.artifact_binding",
                expected=expected_binding,
                actual=binding,
            )
    expected = expected_operator_live_ops_brief(payload, env)
    if expected is not None and brief != expected:
        add(blockers, "operator_live_ops_brief_mismatch", "operator_live_ops_brief", expected=expected, actual=brief)


def validate_payload(payload: dict[str, Any], env: list[str]) -> Validation:
    blockers: list[dict[str, Any]] = []
    require_keys(payload, required=EXPECTED_TOP_LEVEL_KEYS, label="request", blockers=blockers)
    if payload.get("schema") != SCHEMA:
        add(blockers, "schema_mismatch", "schema", expected=SCHEMA)
    if payload.get("status") != "candidate_only_request_pack":
        add(blockers, "status_not_candidate_only_request_pack", "status")
    if payload.get("approval_required") not in (APPROVAL_TEXT, STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT):
        add(
            blockers,
            "approval_required_mismatch",
            "approval_required",
            expected=[APPROVAL_TEXT, STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT],
        )
    if payload.get("marker_set") != WINDOW_MARKERS:
        add(blockers, "marker_set_mismatch", "marker_set")
    if payload.get("forbidden_markers") != FORBIDDEN_MARKERS:
        add(blockers, "forbidden_markers_mismatch", "forbidden_markers")
    if payload.get("non_claims") != NON_CLAIMS:
        add(blockers, "non_claims_mismatch", "non_claims")
    authorization_flags = require_keys(
        payload.get("authorization_flags"),
        required=EXPECTED_AUTHORIZATION_FLAG_KEYS,
        label="authorization_flags",
        blockers=blockers,
    )
    if authorization_flags is not None:
        if authorization_flags != AUTHORIZATION_FLAGS:
            add(
                blockers,
                "authorization_flags_mismatch",
                "authorization_flags",
                expected=AUTHORIZATION_FLAGS,
                actual=authorization_flags,
            )
        for key in EXPECTED_AUTHORIZATION_FLAG_KEYS:
            if authorization_flags.get(key) is not False:
                add(blockers, f"authorization_flag_{key}_not_false", f"authorization_flags.{key}")
    if payload.get("observer_env_file") != "observer-window.env":
        add(blockers, "observer_env_file_mismatch", "observer_env_file")
    validate_post_window_replay_contract(payload, blockers)
    validate_exact_target_scope(payload, blockers)
    validate_passive_wait_boundary(payload, blockers)
    validate_direct_join_plan(payload, blockers)
    validate_player_notice_action(payload, blockers)
    validate_player_presence_safety(payload, blockers)
    validate_runtime_triplet_contract(payload, blockers)
    validate_current_turn_approval_scope(payload, env, blockers)
    validate_planned_obelisk_build_identity(payload, blockers)
    validate_deployment_intent(payload, blockers)
    validate_operator_live_ops_brief(payload, env, blockers)
    target = require_keys(payload.get("target"), required=EXPECTED_TARGET_KEYS, label="target", blockers=blockers)
    if target:
        for key in ("instance", "map"):
            value = target.get(key)
            if not isinstance(value, str) or not SAFE_TOKEN_RE.fullmatch(value):
                add(blockers, f"target_{key}_invalid", f"target.{key}")
            elif is_forbidden_exact_target_alias(value):
                add(blockers, f"target_{key}_alias_not_exact", f"target.{key}", value=value)
    window = require_keys(payload.get("approved_window"), required=EXPECTED_WINDOW_KEYS, label="approved_window", blockers=blockers)
    prepared_at_dt: datetime | None = None
    prepared_at = payload.get("prepared_at_utc")
    if not isinstance(prepared_at, str):
        add(blockers, "prepared_at_utc_not_string", "prepared_at_utc")
    else:
        prepared_at_dt = parse_utc(prepared_at)
        if prepared_at_dt is None:
            add(blockers, "prepared_at_utc_invalid", "prepared_at_utc")
    now = datetime.now(timezone.utc)
    if prepared_at_dt is not None and (prepared_at_dt - now).total_seconds() > 5:
        add(blockers, "prepared_at_utc_in_future", "prepared_at_utc", value=prepared_at)
    if window:
        start = window.get("start_utc")
        end = window.get("end_utc")
        start_dt = parse_utc(start) if isinstance(start, str) else None
        end_dt = parse_utc(end) if isinstance(end, str) else None
        if start_dt is None:
            add(blockers, "approved_window_start_utc_invalid", "approved_window.start_utc")
        if end_dt is None:
            add(blockers, "approved_window_end_utc_invalid", "approved_window.end_utc")
        if start_dt is not None and end_dt is not None and not start_dt < end_dt:
            add(blockers, "approved_window_order_invalid", "approved_window")
        if prepared_at_dt is not None and start_dt is not None and prepared_at_dt >= start_dt:
            add(blockers, "prepared_at_utc_not_before_approved_window", "prepared_at_utc")
        if (
            prepared_at_dt is not None
            and start_dt is not None
            and prepared_at_dt < start_dt
            and (start_dt - prepared_at_dt).total_seconds() > MAX_REQUEST_PREPARATION_LEAD_SECONDS
        ):
            add(
                blockers,
                "prepared_at_utc_too_far_before_approved_window",
                "prepared_at_utc",
                max_seconds=MAX_REQUEST_PREPARATION_LEAD_SECONDS,
            )
        if start_dt is not None and start_dt <= now and (end_dt is None or end_dt > now):
            add(
                blockers,
                "approved_window_already_started",
                "approved_window.start_utc",
                value=start,
                stale_condition="already_started",
            )
        if (
            start_dt is not None
            and end_dt is not None
            and start_dt < end_dt
            and (
                int((end_dt - start_dt).total_seconds()) < MIN_APPROVED_WINDOW_SECONDS
                or int((end_dt - start_dt).total_seconds()) > MAX_APPROVED_WINDOW_SECONDS
            )
        ):
            duration_seconds = int((end_dt - start_dt).total_seconds())
            if duration_seconds > MAX_APPROVED_WINDOW_SECONDS:
                add(
                    blockers,
                    "approved_window_duration_too_long",
                    "approved_window",
                    max_seconds=MAX_APPROVED_WINDOW_SECONDS,
                )
            elif duration_seconds < MIN_APPROVED_WINDOW_SECONDS:
                add(
                    blockers,
                    "approved_window_duration_too_short",
                    "approved_window",
                    min_seconds=MIN_APPROVED_WINDOW_SECONDS,
                    actual_seconds=duration_seconds,
                )
        if end_dt is not None and end_dt <= now:
            add(
                blockers,
                "approved_window_expired",
                "approved_window.end_utc",
                value=end,
                stale_condition="expired",
            )
    rollback = require_keys(payload.get("rollback"), required=EXPECTED_ROLLBACK_KEYS, label="rollback", blockers=blockers)
    if rollback:
        if not isinstance(rollback.get("owner"), str) or not re.fullmatch(r"[A-Za-z0-9_.@ -]+", rollback["owner"]):
            add(blockers, "rollback_owner_invalid", "rollback.owner")
        if rollback.get("delta") != REQUEST_ROLLBACK_DELTA:
            add(blockers, "rollback_delta_mismatch", "rollback.delta", expected=REQUEST_ROLLBACK_DELTA)
        stable_paths = require_keys(
            rollback.get("stable_marker_paths"),
            required=EXPECTED_ROLLBACK_STABLE_MARKER_PATH_KEYS,
            label="rollback_stable_marker_paths",
            blockers=blockers,
        )
        observer_paths = require_keys(
            rollback.get("observer_marker_paths"),
            required=EXPECTED_ROLLBACK_OBSERVER_MARKER_PATH_KEYS,
            label="rollback_observer_marker_paths",
            blockers=blockers,
        )
        if isinstance(stable_paths, dict):
            for key, value in stable_paths.items():
                if not isinstance(value, str) or not value:
                    add(blockers, f"rollback_stable_marker_path_{key}_not_named", f"rollback.stable_marker_paths.{key}")
        if isinstance(observer_paths, dict):
            for key, value in observer_paths.items():
                if not isinstance(value, str) or not value:
                    add(blockers, f"rollback_observer_marker_path_{key}_not_named", f"rollback.observer_marker_paths.{key}")
        if isinstance(target, dict) and isinstance(rollback.get("owner"), str):
            try:
                expected_rollback = rollback_plan(target, rollback["owner"])
            except (KeyError, TypeError):
                expected_rollback = None
            if expected_rollback is not None and rollback != expected_rollback:
                add(blockers, "rollback_mismatch", "rollback", expected=expected_rollback, actual=rollback)
    run_id = string_at(payload, "run_id", blockers)
    if run_id is not None and not RUN_ID_RE.fullmatch(run_id):
        add(blockers, "run_id_invalid", "run_id")
    if run_id is not None and RUN_ID_RE.fullmatch(run_id) and window:
        start = window.get("start_utc")
        start_dt = parse_utc(start) if isinstance(start, str) else None
        if start_dt is not None:
            expected_run_id = run_id_for_window_start(start_dt)
            if run_id != expected_run_id:
                add(
                    blockers,
                    "run_id_window_start_mismatch",
                    "run_id",
                    expected=expected_run_id,
                    actual=run_id,
                    approved_window_start_utc=start,
                )
    sha = string_at(payload, "ark_binary_sha256", blockers)
    if sha is not None and (not SHA256_RE.fullmatch(sha) or sha != EXPECTED_BINARY_SHA256):
        add(blockers, "ark_binary_sha256_not_reviewed", "ark_binary_sha256", expected=EXPECTED_BINARY_SHA256)
    server_binary_path = string_at(payload, "server_binary_path", blockers)
    if server_binary_path is not None and server_binary_path != EXPECTED_SERVER_BINARY_PATH:
        add(
            blockers,
            "server_binary_path_not_reviewed",
            "server_binary_path",
            expected=EXPECTED_SERVER_BINARY_PATH,
        )
    commit = string_at(payload, "obelisk_commit", blockers)
    if commit is not None and not is_reviewed_obelisk_commit(commit):
        add(blockers, "obelisk_commit_invalid", "obelisk_commit")
    if payload.get("restart_expectation") not in ALLOWED_RESTART_EXPECTATIONS:
        add(blockers, "restart_expectation_invalid", "restart_expectation")
    if payload.get("final_posture") not in ALLOWED_FINAL_POSTURES:
        add(blockers, "final_posture_invalid", "final_posture")
    if payload.get("restart_expectation") == "stop-after-window" and payload.get("final_posture") != "stopped":
        add(blockers, "restart_expectation_final_posture_mismatch", "final_posture")
    if payload.get("restart_expectation") in {"none", "start", "restart"} and payload.get("final_posture") != "stable":
        add(blockers, "restart_expectation_final_posture_mismatch", "final_posture")
    if payload.get("diagnostic_candidates_enabled") not in (True, False):
        add(blockers, "diagnostic_candidates_enabled_not_boolean", "diagnostic_candidates_enabled")
    user_policy = payload.get("user_policy")
    if user_policy not in ALLOWED_USER_POLICIES:
        add(blockers, "user_policy_invalid", "user_policy")
    notice_path = payload.get("notice_path")
    if user_policy == "operator_approved_beta_users" and notice_path != APPROVED_BETA_NOTICE_PATH:
        add(
            blockers,
            "beta_user_policy_requires_approved_beta_testers_notice_path",
            "notice_path",
            expected=APPROVED_BETA_NOTICE_PATH,
            actual=notice_path,
        )
    if user_policy == "no_regular_users" and notice_path != "not_applicable":
        add(
            blockers,
            "no_regular_users_requires_notice_path_not_applicable",
            "notice_path",
            expected="not_applicable",
            actual=notice_path,
        )
    if not isinstance(notice_path, str) or not re.fullmatch(r"[A-Za-z0-9_.:/ -]+", notice_path):
        add(blockers, "notice_path_invalid", "notice_path")
    validate_paths(payload, blockers)
    validate_secret_free(payload, blockers)
    forbidden_claim = find_forbidden_claim(payload)
    if forbidden_claim is not None:
        value, trail = forbidden_claim
        add(blockers, "forbidden_public_capability_or_readiness_claim", trail, value=value)
    for path in collect_stale_handle_new_player_rejected_start_rules(payload):
        add(blockers, "stale_handle_new_player_rejected_start_rule", path)
    try:
        expected_env = env_lines(args_for_env(payload))
        if env != expected_env:
            add(blockers, "observer_env_snapshot_mismatch", "env_file", expected=expected_env, actual=env)
    except (KeyError, TypeError):
        pass
    for key, expected in REQUIRED_ENV.items():
        if f"{key}={expected}" not in env:
            add(blockers, "observer_env_required_key_missing_or_mismatch", key, expected=expected)
    diagnostic_env_prefix = "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES="
    diagnostic_env = f"{diagnostic_env_prefix}1"
    if payload.get("diagnostic_candidates_enabled") is True:
        if diagnostic_env not in env:
            add(
                blockers,
                "observer_env_diagnostic_candidates_missing_or_mismatch",
                "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES",
                expected="1",
            )
    elif any(line.startswith(diagnostic_env_prefix) for line in env):
        add(
            blockers,
            "observer_env_diagnostic_candidates_unexpected",
            "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES",
        )
    if "OBELISK_ENABLE_REFLECTION_SCANNER=1" in env or "OBELISK_ENABLE_NATIVE_EXEC_PROBES=1" in env:
        add(blockers, "observer_env_forbidden_debug_gate_present", "env_file")
    return Validation(blockers=blockers, payload=payload)


def validate_operator_request_markdown(
    payload: dict[str, Any],
    env: list[str],
    markdown: str | None,
    blockers: list[dict[str, Any]],
) -> bool:
    if markdown is None:
        return False
    try:
        expected = markdown_request(payload, env)
    except (KeyError, TypeError) as exc:
        add(blockers, "operator_request_markdown_projection_failed", "operator_request", error=str(exc))
        return False
    if markdown != expected:
        add(blockers, "operator_request_markdown_mismatch", "operator_request")
        return False
    return True


def expected_bound_request_pack(payload: dict[str, Any]) -> dict[str, Any] | None:
    try:
        return {
            "run_id": payload["run_id"],
            "prepared_at_utc": payload["prepared_at_utc"],
            "target": payload["target"],
            "exact_target_scope": payload["exact_target_scope"],
            "approved_window": payload["approved_window"],
            "obelisk_commit": payload["obelisk_commit"],
            "planned_obelisk_build_identity": payload["planned_obelisk_build_identity"],
            "ark_binary_sha256": payload["ark_binary_sha256"],
            "server_binary_path": payload["server_binary_path"],
            "restart_expectation": payload["restart_expectation"],
            "final_posture": payload["final_posture"],
            "user_policy": payload["user_policy"],
            "notice_path": payload["notice_path"],
            "player_notice_action": payload["player_notice_action"],
            "direct_join_plan": payload["direct_join_plan"],
            "player_presence_safety": payload["player_presence_safety"],
            "copied_evidence_dir": payload["copied_evidence_dir"],
            "copied_log_path": payload["copied_log_path"],
            "window_manifest_path": payload["window_manifest_path"],
            "rollback": payload["rollback"],
            "passive_wait_boundary": payload["passive_wait_boundary"],
            "runtime_triplet_contract": payload["runtime_triplet_contract"],
            "current_turn_approval_scope": payload["current_turn_approval_scope"],
            "deployment_intent": payload["deployment_intent"],
        }
    except (KeyError, TypeError):
        return None


def validate_operator_approval_receipt(
    *,
    payload: dict[str, Any],
    request_json_path: Path,
    env_file_path: Path,
    operator_request_path: Path,
    receipt_path: Path,
    blockers: list[dict[str, Any]],
) -> bool:
    initial_blocker_count = len(blockers)
    try:
        reject_symlink_component(receipt_path, "operator_approval_receipt")
        resolved = protected_paths.reject_protected_input_path(
            receipt_path,
            "operator_approval_receipt",
            protected_root=SERVER_ROOT,
            approved_roots=approved_offline_workspace_roots(),
        )
        receipt = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        add(blockers, "operator_approval_receipt_json_invalid", "operator_approval_receipt", error=str(exc))
        return False
    except (OSError, ValueError) as exc:
        add(blockers, "operator_approval_receipt_unreadable", "operator_approval_receipt", path=str(receipt_path), error=str(exc))
        return False
    if not isinstance(receipt, dict):
        add(blockers, "operator_approval_receipt_not_object", "operator_approval_receipt")
        return False

    require_keys(
        receipt,
        required=EXPECTED_OPERATOR_APPROVAL_RECEIPT_TOP_LEVEL_KEYS,
        label="operator_approval_receipt",
        blockers=blockers,
    )
    if receipt.get("schema") != APPROVAL_RECEIPT_SCHEMA:
        add(blockers, "operator_approval_receipt_schema_mismatch", "operator_approval_receipt")
    if receipt.get("status") == "generated_template":
        add(
            blockers,
            "operator_approval_receipt_generated_template_not_completed_receipt",
            "operator_approval_receipt",
        )
    if receipt.get("status") != "completed_operator_receipt":
        add(blockers, "operator_approval_receipt_status_not_completed", "operator_approval_receipt")
    if receipt.get("receipt_completed") is not True:
        add(blockers, "operator_approval_receipt_receipt_completed_not_true", "operator_approval_receipt")

    if receipt.get("non_claims") != EXPECTED_OPERATOR_APPROVAL_RECEIPT_NON_CLAIMS:
        add(blockers, "operator_approval_receipt_non_claims_mismatch", "operator_approval_receipt")

    scope = require_keys(
        receipt.get("approval_scope"),
        required=EXPECTED_OPERATOR_APPROVAL_RECEIPT_SCOPE_KEYS,
        label="operator_approval_receipt_scope",
        blockers=blockers,
    ) or {}
    if scope.get("scope_type") != "exact_bound_player_principal_lifecycle_window_only":
        add(blockers, "operator_approval_receipt_scope_type_mismatch", "operator_approval_receipt")
    completion = require_keys(
        receipt.get("operator_completion"),
        required=EXPECTED_OPERATOR_APPROVAL_RECEIPT_COMPLETION_KEYS,
        label="operator_approval_receipt_completion",
        blockers=blockers,
    ) or {}
    approval_source = completion.get("approval_source")
    standing_authority_receipt = approval_source == APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY
    if standing_authority_receipt:
        if scope.get("standing_approval") is not True:
            add(blockers, "operator_approval_receipt_scope_standing_approval_not_true", "operator_approval_receipt")
        if receipt.get("operator_current_turn_approval_recorded") is not False:
            add(
                blockers,
                "operator_approval_receipt_current_turn_approval_not_false_for_standing_authority",
                "operator_approval_receipt",
            )
        if receipt.get("standing_launch_authority_recorded") is not True:
            add(blockers, "operator_approval_receipt_standing_launch_authority_not_recorded", "operator_approval_receipt")
        if receipt.get("standing_launch_authority_satisfies_operator_approval") is not True:
            add(
                blockers,
                "operator_approval_receipt_standing_launch_authority_not_bound",
                "operator_approval_receipt",
            )
    elif scope.get("standing_approval") is not False:
        add(blockers, "operator_approval_receipt_scope_standing_approval_not_false", "operator_approval_receipt")
    else:
        if receipt.get("operator_current_turn_approval_recorded") is not True:
            add(blockers, "operator_approval_receipt_current_turn_approval_not_recorded", "operator_approval_receipt")
        if receipt.get("standing_launch_authority_recorded") is not False:
            add(
                blockers,
                "operator_approval_receipt_standing_launch_authority_not_false_for_current_turn",
                "operator_approval_receipt",
            )
        if receipt.get("standing_launch_authority_satisfies_operator_approval") is not False:
            add(
                blockers,
                "operator_approval_receipt_standing_launch_authority_bound_for_current_turn",
                "operator_approval_receipt",
            )
    for key in (
        "reusable",
        "future_windows_authorized",
        "scope_expansion_authorized",
        "unbound_artifacts_authorized",
    ):
        if scope.get(key) is not False:
            add(blockers, f"operator_approval_receipt_scope_{key}_not_false", "operator_approval_receipt")

    approval_recorded_at = completion.get("approval_recorded_at_utc")
    approval_recorded_dt = parse_utc(approval_recorded_at) if isinstance(approval_recorded_at, str) else None
    if approval_recorded_dt is None:
        add(blockers, "operator_approval_receipt_approved_at_utc_invalid", "operator_approval_receipt")
    elif (approval_recorded_dt - datetime.now(timezone.utc)).total_seconds() > 5:
        add(
            blockers,
            "operator_approval_receipt_approved_in_future",
            "operator_approval_receipt",
            approval_recorded_at_utc=approval_recorded_at,
        )
    request_prepared_dt = parse_utc(payload.get("prepared_at_utc")) if isinstance(payload.get("prepared_at_utc"), str) else None
    approved_window = payload.get("approved_window")
    window_start_dt = None
    if isinstance(approved_window, dict) and isinstance(approved_window.get("start_utc"), str):
        window_start_dt = parse_utc(approved_window["start_utc"])
    if approval_recorded_dt is not None and request_prepared_dt is not None and approval_recorded_dt <= request_prepared_dt:
        add(
            blockers,
            "operator_approval_receipt_approved_before_request_prepared",
            "operator_approval_receipt",
            prepared_at_utc=payload.get("prepared_at_utc"),
            approval_recorded_at_utc=approval_recorded_at,
        )
    if approval_recorded_dt is not None and window_start_dt is not None and approval_recorded_dt >= window_start_dt:
        add(
            blockers,
            "operator_approval_receipt_approved_at_or_after_window_start",
            "operator_approval_receipt",
            approved_window_start_utc=approved_window.get("start_utc") if isinstance(approved_window, dict) else None,
            approval_recorded_at_utc=approval_recorded_at,
        )
    if (
        approval_recorded_dt is not None
        and window_start_dt is not None
        and approval_recorded_dt < window_start_dt
        and (window_start_dt - approval_recorded_dt).total_seconds() > MAX_OPERATOR_APPROVAL_LEAD_SECONDS
    ):
        add(
            blockers,
            "operator_approval_receipt_approved_too_far_before_window_start",
            "operator_approval_receipt",
            max_seconds=MAX_OPERATOR_APPROVAL_LEAD_SECONDS,
            approved_window_start_utc=approved_window.get("start_utc") if isinstance(approved_window, dict) else None,
            approval_recorded_at_utc=approval_recorded_at,
        )
    if not isinstance(completion.get("approved_by_role"), str) or not completion.get("approved_by_role", "").strip():
        add(blockers, "operator_approval_receipt_approved_by_role_invalid", "operator_approval_receipt")
    if approval_source not in (APPROVAL_SOURCE_CURRENT_TURN, APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY):
        add(blockers, "operator_approval_receipt_approval_source_mismatch", "operator_approval_receipt")
    expected_attestation = (
        APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY
        if standing_authority_receipt
        else APPROVAL_ATTESTATION_CURRENT_TURN
    )
    if completion.get("attestation") != expected_attestation:
        add(blockers, "operator_approval_receipt_attestation_mismatch", "operator_approval_receipt")
    forbidden_receipt_claim = find_forbidden_claim(receipt)
    if forbidden_receipt_claim is not None:
        value, trail = forbidden_receipt_claim
        add(
            blockers,
            "operator_approval_receipt_forbidden_public_capability_or_readiness_claim",
            "operator_approval_receipt",
            trail=trail,
            value=value,
        )

    bound_request = require_keys(
        receipt.get("bound_request_pack"),
        required=EXPECTED_OPERATOR_APPROVAL_RECEIPT_BOUND_REQUEST_KEYS,
        label="operator_approval_receipt_bound_request_pack",
        blockers=blockers,
    ) or {}
    if isinstance(bound_request.get("target"), dict):
        require_keys(
            bound_request["target"],
            required=EXPECTED_TARGET_KEYS,
            label="operator_approval_receipt_bound_request_pack_target",
            blockers=blockers,
        )
    if isinstance(bound_request.get("exact_target_scope"), dict):
        require_keys(
            bound_request["exact_target_scope"],
            required=EXPECTED_EXACT_TARGET_SCOPE_KEYS,
            label="operator_approval_receipt_bound_request_pack_exact_target_scope",
            blockers=blockers,
        )
    if isinstance(bound_request.get("approved_window"), dict):
        require_keys(
            bound_request["approved_window"],
            required=EXPECTED_WINDOW_KEYS,
            label="operator_approval_receipt_bound_request_pack_window",
            blockers=blockers,
        )
    if isinstance(bound_request.get("rollback"), dict):
        require_keys(
            bound_request["rollback"],
            required=EXPECTED_ROLLBACK_KEYS,
            label="operator_approval_receipt_bound_request_pack_rollback",
            blockers=blockers,
        )
    if isinstance(bound_request.get("passive_wait_boundary"), dict):
        require_keys(
            bound_request["passive_wait_boundary"],
            required=EXPECTED_PASSIVE_WAIT_BOUNDARY_KEYS,
            label="operator_approval_receipt_bound_request_pack_passive_wait_boundary",
            blockers=blockers,
        )
    if isinstance(bound_request.get("player_presence_safety"), dict):
        require_keys(
            bound_request["player_presence_safety"],
            required=EXPECTED_PLAYER_PRESENCE_SAFETY_KEYS,
            label="operator_approval_receipt_bound_request_pack_player_presence_safety",
            blockers=blockers,
        )
    expected_bound = expected_bound_request_pack(payload)
    if expected_bound is not None and bound_request != expected_bound:
        for key, expected_value in expected_bound.items():
            if bound_request.get(key) != expected_value:
                add(
                    blockers,
                    f"operator_approval_receipt_{key}_mismatch",
                    "operator_approval_receipt",
                    expected=expected_value,
                    actual=bound_request.get(key),
                )

    bound_artifacts = require_keys(
        receipt.get("bound_artifacts"),
        required=EXPECTED_OPERATOR_APPROVAL_RECEIPT_BOUND_ARTIFACTS_KEYS,
        label="operator_approval_receipt_bound_artifacts",
        blockers=blockers,
    ) or {}
    try:
        expected_artifacts = {
            "window_request_json": bound_artifact(request_json_path),
            "observer_window_env": bound_artifact(env_file_path),
            "operator_approval_request_md": bound_artifact(operator_request_path),
        }
    except OSError as exc:
        add(blockers, "operator_approval_receipt_bound_artifact_unreadable", "operator_approval_receipt", error=str(exc))
        expected_artifacts = {}
    for key, expected in expected_artifacts.items():
        actual = bound_artifacts.get(key)
        if isinstance(actual, dict):
            require_keys(
                actual,
                required=EXPECTED_OPERATOR_APPROVAL_RECEIPT_ARTIFACT_KEYS,
                label=f"operator_approval_receipt_bound_artifacts_{key}",
                blockers=blockers,
            )
        if actual != expected:
            add(
                blockers,
                f"operator_approval_receipt_{key}_artifact_mismatch",
                "operator_approval_receipt",
                expected=expected,
                actual=actual,
            )

    try:
        expected_digest = request_pack_digest(
            request_json_path=request_json_path,
            request_md_path=operator_request_path,
            env_path=env_file_path,
        )
    except OSError as exc:
        add(blockers, "operator_approval_receipt_digest_unreadable", "operator_approval_receipt", error=str(exc))
    else:
        if receipt.get("request_pack_digest") != expected_digest:
            add(
                blockers,
                "operator_approval_receipt_digest_mismatch",
                "operator_approval_receipt",
                expected=expected_digest,
                actual=receipt.get("request_pack_digest"),
            )

    flags = require_keys(
        receipt.get("non_authorization_flags"),
        required=EXPECTED_OPERATOR_APPROVAL_RECEIPT_FLAG_KEYS,
        label="operator_approval_receipt_non_authorization_flags",
        blockers=blockers,
    ) or {}
    for key in EXPECTED_OPERATOR_APPROVAL_RECEIPT_FLAG_KEYS:
        if flags.get(key) is not False:
            add(blockers, f"operator_approval_receipt_{key}_not_false", "operator_approval_receipt")

    return len(blockers) == initial_blocker_count


def build_report(
    validation: Validation,
    *,
    operator_request_verified: bool = False,
    operator_approval_receipt_verified: bool = False,
    request_pack_artifacts: dict[str, Any] | None = None,
    request_pack_digest_report: dict[str, Any] | None = None,
    operator_approval_receipt_completion: dict[str, Any] | None = None,
) -> dict[str, Any]:
    accepted = not validation.blockers
    payload = validation.payload or {}
    standing_launch_authority_recorded = payload_uses_standing_launch_authority(payload)
    try:
        report_deployment_intent = deployment_intent(payload) if payload else None
    except (KeyError, TypeError):
        report_deployment_intent = payload.get("deployment_intent") if isinstance(payload, dict) else None
    return {
        "schema": REPORT_SCHEMA,
        "ready": accepted,
        "request_pack_ready": accepted,
        "ready_scope": "offline_request_pack_validation_only",
        "prepared_at_utc": payload.get("prepared_at_utc"),
        "approved_window": payload.get("approved_window"),
        "restart_expectation": payload.get("restart_expectation"),
        "final_posture": payload.get("final_posture"),
        "user_policy": payload.get("user_policy"),
        "notice_path": payload.get("notice_path"),
        "request_pack_artifacts": request_pack_artifacts or {},
        "request_pack_digest": request_pack_digest_report,
        "operator_approval_receipt_completion": operator_approval_receipt_completion,
        "current_turn_operator_approval_required": not standing_launch_authority_recorded,
        "current_turn_approval_recorded": (
            bool(operator_approval_receipt_verified)
            and not standing_launch_authority_recorded
        ),
        "request_pack_records_current_turn_approval": False,
        "standing_launch_authority_recorded": standing_launch_authority_recorded,
        "standing_launch_authority_satisfies_operator_approval": (
            standing_launch_authority_recorded and bool(operator_approval_receipt_verified)
        ),
        "operator_runtime_authority_source": (
            APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY
            if standing_launch_authority_recorded
            else APPROVAL_SOURCE_CURRENT_TURN
        ),
        "authorization_source": "none_request_pack_check_only",
        "approved_runtime_evidence_source": "none_request_pack_check_only",
        "planning_only": True,
        "exact_target_scope": payload.get("exact_target_scope") if isinstance(payload, dict) else None,
        "runtime_triplet_contract": payload.get("runtime_triplet_contract") if isinstance(payload, dict) else None,
        "passive_wait_boundary": payload.get("passive_wait_boundary") if isinstance(payload, dict) else None,
        "direct_join_plan": payload.get("direct_join_plan") if isinstance(payload, dict) else None,
        "requested_wait_window_seconds": (
            payload.get("passive_wait_boundary", {}).get("requested_wait_window_seconds")
            if isinstance(payload.get("passive_wait_boundary"), dict)
            else None
        ),
        "max_requested_wait_window_seconds": MAX_APPROVED_WINDOW_SECONDS,
        "requested_wait_window_seconds_checked_only": True,
        "requested_wait_window_authorizes_current_turn_approval": False,
        "requested_wait_window_authorizes_runtime_capture": False,
        "passive_wait_or_watch_only_authorizes_deploy_or_restart": False,
        "current_turn_scope_authorized": False,
        "discord_authorized": False,
        "discord_send_authorized": False,
        "discord_sent": False,
        "marker_env_changes_authorized": False,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "runtime_capture_authorized": False,
        "runtime_window_authorized": False,
        "read_live_logs": False,
        "reads_live_logs": False,
        "live_log_reads_authorized": False,
        "live_log_permission_granted": False,
        "publication_authorized": False,
        "promotion_ready": False,
        "public_abi_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "v1_completion_ready": False,
        "stable_claim_allowed": False,
        "request_pack_counts_as_approved_runtime_evidence": False,
        "observer_env_counts_as_approved_runtime_evidence": False,
        "operator_request_counts_as_approved_runtime_evidence": False,
        "copied_log_metadata_counts_as_approved_runtime_evidence": False,
        "bundle_output_counts_as_approved_runtime_evidence": False,
        "preflight_counts_as_approved_runtime_evidence": False,
        "window_manifest_counts_as_approved_runtime_evidence": False,
        "completed_receipt_counts_as_approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "route_ready": False,
        "sdk_accounting_counts_as_completed_surface": False,
        "p0_accounting_counts_as_promoted_surface": False,
        "current_turn_approval_required_fields": CURRENT_TURN_APPROVAL_REQUIRED_FIELDS,
        "current_turn_approval_scope_status": (
            payload.get("current_turn_approval_scope", {}).get("status")
            if isinstance(payload.get("current_turn_approval_scope"), dict)
            else APPROVAL_SCOPE_STATUS
        ),
        "deployment_intent": report_deployment_intent,
        "planned_obelisk_build_identity": payload.get("planned_obelisk_build_identity") if isinstance(payload, dict) else None,
        "blockers": [blocker["reason"] for blocker in validation.blockers],
        "blocker_details": validation.blockers,
        "next_blocker": (
            "runtime_window_preflight_required"
            if accepted and standing_launch_authority_recorded
            else (
                "operator_current_turn_runtime_window_approval_required"
                if accepted
                else "request_pack_not_accepted"
            )
        ),
        "operator_request_verified": operator_request_verified,
        "operator_approval_receipt_verified": operator_approval_receipt_verified,
        "target": payload.get("target"),
        "run_id": payload.get("run_id"),
        "approval_required": payload.get("approval_required"),
        "non_claims": [
            "request-pack acceptance is pre-window planning only",
            "does not authorize server operations, marker/env changes, starts, restarts, stops, Discord, GitHub publication, runtime capture, public SDK readiness, or v1 completion",
            "does not promote public player identity, permissions/admin, command response, lookup, mutation, return override, or ResourceHandle",
        ],
    }


def report_artifact(
    path: Path,
    *,
    label: str,
    blockers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    try:
        return bound_artifact(path)
    except OSError as exc:
        add(blockers, f"{label}_report_artifact_unreadable", label, path=str(path), error=str(exc))
        return None


def request_pack_artifact_report(
    *,
    request_json_path: Path,
    env_file_path: Path,
    operator_request_path: Path,
    operator_approval_receipt_path: Path | None,
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "window_request_json": report_artifact(
            request_json_path,
            label="window_request_json",
            blockers=blockers,
        ),
        "observer_window_env": report_artifact(
            env_file_path,
            label="observer_window_env",
            blockers=blockers,
        ),
        "operator_approval_request_md": report_artifact(
            operator_request_path,
            label="operator_approval_request_md",
            blockers=blockers,
        ),
        "operator_approval_receipt_json": (
            report_artifact(
                operator_approval_receipt_path,
                label="operator_approval_receipt_json",
                blockers=blockers,
            )
            if operator_approval_receipt_path is not None
            else None
        ),
    }


def request_pack_digest_report(
    *,
    request_json_path: Path,
    env_file_path: Path,
    operator_request_path: Path,
    blockers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    try:
        return request_pack_digest(
            request_json_path=request_json_path,
            request_md_path=operator_request_path,
            env_path=env_file_path,
        )
    except OSError as exc:
        add(blockers, "request_pack_digest_report_unreadable", "request_pack_digest", error=str(exc))
        return None


def operator_approval_receipt_completion_report(
    receipt_path: Path | None,
    *,
    blockers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if receipt_path is None:
        return None
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        add(blockers, "operator_approval_receipt_completion_report_json_invalid", "operator_approval_receipt", error=str(exc))
        return None
    except OSError as exc:
        add(blockers, "operator_approval_receipt_completion_report_unreadable", "operator_approval_receipt", error=str(exc))
        return None
    if not isinstance(receipt, dict):
        add(blockers, "operator_approval_receipt_completion_report_not_object", "operator_approval_receipt")
        return None
    completion = receipt.get("operator_completion")
    if not isinstance(completion, dict):
        return None
    return {
        "approval_recorded_at_utc": completion.get("approval_recorded_at_utc"),
        "approval_source": completion.get("approval_source"),
        "attestation": completion.get("attestation"),
    }


def tolerate_post_window_expiry_only(blockers: list[dict[str, Any]]) -> bool:
    if len(blockers) != 1:
        return False
    if blockers[0].get("reason") != "approved_window_expired":
        return False
    blockers.clear()
    return True


def validate_post_window_replay_window_completed(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    approved_window = payload.get("approved_window")
    if not isinstance(approved_window, dict):
        return
    end_utc = approved_window.get("end_utc")
    end_dt = parse_utc(end_utc) if isinstance(end_utc, str) else None
    if end_dt is not None and end_dt > datetime.now(timezone.utc):
        add(
            blockers,
            "post_window_replay_window_not_completed",
            "approved_window.end_utc",
            value=end_utc,
        )


def validate_post_window_replay_required_sidecar_files(
    request_json_path: Path,
    blockers: list[dict[str, Any]],
) -> None:
    try:
        request_dir = request_json_path.expanduser().resolve(strict=True).parent
    except OSError as exc:
        add(
            blockers,
            "post_window_replay_request_dir_unresolved",
            "request_json",
            path=str(request_json_path),
            error=str(exc),
        )
        return
    for label, filename in POST_WINDOW_REPLAY_REQUIRED_SIDECAR_FILES:
        sidecar = request_dir / filename
        try:
            reject_symlink_component(sidecar, f"post_window_replay_{label}")
            if not sidecar.exists():
                add(
                    blockers,
                    f"post_window_replay_{label}_sidecar_missing",
                    f"post_window_replay.{label}",
                    path=str(sidecar),
                )
                continue
            resolved = protected_paths.reject_protected_input_path(
                sidecar,
                f"post_window_replay_{label}",
                protected_root=SERVER_ROOT,
                approved_roots=approved_offline_workspace_roots(),
            )
        except (OSError, ValueError) as exc:
            add(
                blockers,
                f"post_window_replay_{label}_sidecar_unreadable",
                f"post_window_replay.{label}",
                path=str(sidecar),
                error=str(exc),
            )
            continue
        if resolved.name != filename:
            add(
                blockers,
                f"post_window_replay_{label}_filename_mismatch",
                f"post_window_replay.{label}",
                expected=filename,
                actual=resolved.name,
            )
        if resolved.parent != request_dir:
            add(
                blockers,
                f"post_window_replay_{label}_not_sibling_of_request_json",
                f"post_window_replay.{label}",
                expected_dir=str(request_dir),
                actual_dir=str(resolved.parent),
            )
        if not resolved.is_file():
            add(
                blockers,
                f"post_window_replay_{label}_not_file",
                f"post_window_replay.{label}",
                path=str(resolved),
            )


def main() -> int:
    args = parse_args()
    blockers: list[dict[str, Any]] = []
    operator_request_path = args.operator_request or (args.request_json.parent / "operator-approval-request.md")
    validate_request_pack_sidecar_paths(
        request_json_path=args.request_json,
        env_file_path=args.env_file,
        operator_request_path=operator_request_path,
        blockers=blockers,
    )
    payload = read_json(args.request_json)
    standing_payload = payload_uses_standing_launch_authority(payload)
    if args.operator_approval_receipt is not None:
        validate_operator_approval_receipt_path(
            request_json_path=args.request_json,
            receipt_path=args.operator_approval_receipt,
            blockers=blockers,
        )
        if not args.post_window_replay and not standing_payload:
            add(
                blockers,
                "operator_approval_receipt_requires_post_window_replay",
                "operator_approval_receipt",
            )
    elif args.post_window_replay:
        add(
            blockers,
            "operator_approval_receipt_required_for_post_window_replay",
            "operator_approval_receipt",
        )
    env = read_env(args.env_file, blockers)
    operator_request_markdown = read_text_sidecar(operator_request_path, "operator_request", blockers)
    validation = validate_payload(payload, env)
    validation.blockers[:0] = blockers
    operator_request_verified = validate_operator_request_markdown(
        payload,
        env,
        operator_request_markdown,
        validation.blockers,
    )
    if any(blocker.get("label") == "operator_request" for blocker in validation.blockers):
        operator_request_verified = False
    receipt_valid = False
    if args.operator_approval_receipt is not None:
        receipt_valid = validate_operator_approval_receipt(
            payload=payload,
            request_json_path=args.request_json,
            env_file_path=args.env_file,
            operator_request_path=operator_request_path,
            receipt_path=args.operator_approval_receipt,
            blockers=validation.blockers,
        )
    if args.post_window_replay:
        validate_post_window_replay_window_completed(payload, validation.blockers)
        validate_post_window_replay_required_sidecar_files(args.request_json, validation.blockers)
    post_window_replay_expiry_tolerated = False
    if args.post_window_replay:
        post_window_replay_expiry_tolerated = tolerate_post_window_expiry_only(validation.blockers)
    report_artifacts = request_pack_artifact_report(
        request_json_path=args.request_json,
        env_file_path=args.env_file,
        operator_request_path=operator_request_path,
        operator_approval_receipt_path=args.operator_approval_receipt,
        blockers=validation.blockers,
    )
    report_digest = request_pack_digest_report(
        request_json_path=args.request_json,
        env_file_path=args.env_file,
        operator_request_path=operator_request_path,
        blockers=validation.blockers,
    )
    standing_authority_prewindow_receipt = (
        standing_payload and args.operator_approval_receipt is not None and not args.post_window_replay
    )
    operator_approval_receipt_verified = bool(
        (args.post_window_replay or standing_authority_prewindow_receipt)
        and receipt_valid
        and not validation.blockers
    )
    receipt_completion = operator_approval_receipt_completion_report(
        args.operator_approval_receipt if operator_approval_receipt_verified else None,
        blockers=validation.blockers,
    )
    report = build_report(
        validation,
        operator_request_verified=operator_request_verified,
        operator_approval_receipt_verified=operator_approval_receipt_verified,
        request_pack_artifacts=report_artifacts,
        request_pack_digest_report=report_digest,
        operator_approval_receipt_completion=receipt_completion,
    )
    report["post_window_replay"] = bool(args.post_window_replay)
    report["post_window_replay_expiry_tolerated"] = post_window_replay_expiry_tolerated
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"player_principal_lifecycle_window_request_ready={str(report['ready']).lower()}")
        if not report["ready"]:
            print("blockers=" + ",".join(report["blockers"]), file=sys.stderr)
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
