#!/usr/bin/env python3
"""Validate approved runtime principal lifecycle observer evidence.

This checker consumes a copied/sanitized `analyze_runtime_observer_log.py` summary plus
fail-closed consumer boundary cases. Acceptance means only that runtime lifecycle evidence
is reviewable for the player-principal lane; it does not promote public identity,
permissions, commands, lookup, mutation, or SDK readiness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import protected_paths
import analyze_runtime_observer_log as runtime_observer_analyzer
import check_player_identity_runtime_principal_lifecycle_window_manifest as window_manifest_checker
from check_player_identity_runtime_principal_lifecycle_window_manifest import (
    EXPECTED_PREFLIGHT_NON_CLAIM,
    EXPECTED_ROLLBACK_DELTA,
    PREFLIGHT_SCHEMA as EXPECTED_PREFLIGHT_SCHEMA,
    REPORT_SCHEMA as WINDOW_CHECK_SCHEMA,
    REQUIRED_OPERATIONAL_WINDOW_NON_CLAIMS,
)
from prepare_player_principal_lifecycle_window_request import (
    APPROVAL_ATTESTATION_CURRENT_TURN,
    APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY,
    APPROVAL_RECEIPT_SCHEMA as EXPECTED_OPERATOR_APPROVAL_RECEIPT_SCHEMA,
    APPROVAL_SOURCE_CURRENT_TURN,
    APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY,
    APPROVAL_TEXT as EXPECTED_APPROVAL,
    APPROVAL_SCOPE_NON_AUTHORIZATION,
    APPROVED_BETA_NOTICE_PATH,
    ARTIFACT_BINDING_NON_AUTHORIZATION,
    BETA_RUNTIME_CHOREOGRAPHY_NON_AUTHORIZATION,
    BRIEF_NON_AUTHORIZATION,
    DIRECT_JOIN_PLAN_NON_AUTHORIZATION,
    DRIFT_FIX_DEPLOYMENT_INTENT_NON_AUTHORIZATION,
    EXPECTED_BINARY_SHA256,
    EXPECTED_SERVER_BINARY_PATH,
    NON_CLAIMS as EXPECTED_REQUEST_PACK_NON_CLAIMS,
    OPERATOR_APPROVAL_RECEIPT_NON_CLAIMS,
    OBSERVER_ENV_KEYS,
    PLAYER_NOTICE_ACTION_NON_AUTHORIZATION,
    PLAYER_PRESENCE_SAFETY_NON_AUTHORIZATION,
    PLAYER_PRESENCE_SAFETY_SCHEMA,
    REPLAY_NON_AUTHORIZATION,
    REQUIRED_ENV,
    REQUEST_ROLLBACK_DELTA as EXPECTED_REQUEST_ROLLBACK_DELTA,
    SCHEMA as EXPECTED_REQUEST_SCHEMA,
    STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT,
    player_presence_safety,
    request_pack_digest,
)
from artifact_identity import canonical_json_bytes, complete_artifact_identity
from snapshot_evidence_pack import first_symlink_component, reject_protected_input_path, reject_symlink_component


SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1"
REPORT_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1"
SHAPE_FIXTURE_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-evidence.v1"
PRINCIPAL_START_END_EVIDENCE_CHECK_SCHEMA = (
    "obelisk.players-identity-runtime-principal-start-end-evidence-check.v1"
)
MULTI_SURFACE_BETA_CAPTURE_PLAN_SCHEMA = "obelisk.multi-surface-beta-capture-plan.v1"
MULTI_SURFACE_BETA_CAPTURE_PACK_SCHEMA = "obelisk.multi-surface-beta-capture-pack.v1"
MULTI_SURFACE_BETA_CAPTURE_CHECKER_MATRIX_SCHEMA = "obelisk.multi-surface-beta-capture-checker-matrix.v1"
MULTI_SURFACE_BETA_CAPTURE_NON_CLAIM_MANIFEST_SCHEMA = (
    "obelisk.multi-surface-beta-capture-non-claim-manifest.v1"
)
NOTICE_PREP_SCHEMA = "obelisk.player-principal-lifecycle-beta-notice-prep.v1"
CLOSURE_REQUEST_SCHEMA = "obelisk.player-principal-lifecycle-evidence-closure-request.v1"
PASSIVE_SNAPSHOT_SCHEMA = "obelisk.player-principal-passive-snapshot.v1"
PASSIVE_SNAPSHOT_DIFF_SCHEMA = "obelisk.player-principal-passive-snapshot-diff.v1"
PASSIVE_SNAPSHOT_LATEST_SCHEMA = "obelisk.player-principal-passive-snapshot-latest.v1"
PASSIVE_OBSERVER_EVENT_TRIAGE_SCHEMA = "obelisk.player-principal-passive-observer-event-triage.v1"
PASSIVE_ACTIVITY_TRIAGE_SCHEMA = "obelisk.player-principal-passive-activity-triage.v1"
PASSIVE_ACTIONABILITY_SCHEMA = "obelisk.player-principal-passive-actionability.v1"
PASSIVE_TARGET_TRIPLET_SCHEMA = "obelisk.player-principal-passive-target-triplet-candidate-summary.v1"
PASSIVE_SERVER_ACTIVITY_SCHEMA = "obelisk.player-principal-passive-server-activity-summary.v1"
PASSIVE_MONITOR_ONLY_SUMMARY_SCHEMA = "obelisk.player-principal-passive-monitor-only-summary.v1"
PASSIVE_EXTENDED_MONITOR_TRIAGE_SCHEMA = "obelisk.player-principal-passive-extended-monitor-triage.v1"
PASSIVE_WAIT_SCHEMA = "obelisk.player-principal-passive-wait-metadata.v1"
PUBLIC_REACHABILITY_SCHEMA = "obelisk.player-principal-public-reachability-check.v1"
SDK_STATUS_REPORT_SCHEMA = "obelisk.sdk-status-report.v1"
SDK_STATUS_SIDE_LANE_SUMMARY_SCHEMA = "obelisk.sdk-status-side-lane-summary.v1"
SDK_STATUS_CRITICAL_PATH_SUMMARY_SCHEMA = "obelisk.sdk-status-critical-path-summary.v1"
POST_EVIDENCE_P0_LOCK_SIMULATION_SCHEMA = "obelisk.command-permission-route-post-evidence-p0-lock-simulation.v1"
RUNTIME_WINDOW_PLAN_SCHEMA = "obelisk.player-principal-lifecycle-runtime-window-plan.v1"
RUNTIME_WINDOW_EXECUTION_SCHEMA = "obelisk.player-principal-lifecycle-runtime-window-execution.v1"
RUNTIME_WINDOW_POST_WINDOW_STATE_SCHEMA = "obelisk.player-principal-lifecycle-runtime-window-post-window-state.v1"
RUNTIME_EVIDENCE_STATUS_SCHEMA = "obelisk.player-principal-lifecycle-runtime-evidence-status.v1"
PLANNING_BLOCKER_SMOKE_SCHEMA = "obelisk.player-principal-lifecycle-planning-blocker-smoke.v1"
PLANNING_SOURCE_MANIFESTS_BUILD_REPORT_SCHEMA = "obelisk.player-identity-planning-source-manifests-build-report.v1"
LIFECYCLE_ANCHOR_CANDIDATES_SCHEMA = "obelisk.players-identity-lifecycle-anchor-candidates.v1"
PRINCIPAL_INVALIDATION_POLICY_SCHEMA = "obelisk.players-identity-principal-invalidation-policy.v1"
FIRST_EVIDENCE_SCHEMA = "obelisk.players-identity-first-evidence.v1"
PASSIVE_SNAPSHOT_ROLLUP_SCHEMA = "obelisk.player-principal-passive-snapshot-rollup.v1"
COMMAND_PERMISSION_ROUTE_GATE_CHECK_SCHEMA = "obelisk.command-permission-route-gate-check.v1"
COMMAND_PERMISSION_ROUTE_BOUND_IDENTITY_SOURCE_FORWARDING_SCHEMA = (
    "obelisk.command-permission-route-bound-identity-source-forwarding.v1"
)
COMMAND_PERMISSION_ROUTE_SIMULATION_SCHEMA = "obelisk.command-permission-route-simulation.v1"
COMMAND_PERMISSION_ROUTE_POST_EVIDENCE_IDENTITY_LOCK_SCHEMA = (
    "obelisk.command-permission-route-post-evidence-identity-lock.v1"
)
COMMAND_PERMISSION_ROUTE_SNAPSHOT_SCHEMA = "obelisk.command-permission-route-snapshot.v1"
PUBLIC_SDK_SURFACES_SCHEMA = "obelisk.public-sdk-surfaces.v1"
PUBLIC_SDK_V1_COMPLETION_READY_SCHEMA_ID_SCHEMA = "obelisk.public-sdk-v1-completion-ready-schema-id.v1"
PUBLIC_SDK_V1_COMPLETION_CHECK_SCHEMA = "obelisk.public-sdk-v1-completion-check.v1"
PUBLIC_SDK_V1_COMPLETION_SUMMARY_SCHEMA = "obelisk.public-sdk-v1-completion-summary.v1"
PUBLIC_SDK_V1_FASTEST_NEXT_UNBLOCK_SCHEMA = "obelisk.public-sdk-v1-fastest-next-unblock.v1"
PUBLIC_SDK_V1_APPROVED_IN_GAME_EVIDENCE_STATUS_SCHEMA = (
    "obelisk.public-sdk-v1-approved-in-game-evidence-status.v1"
)
PUBLIC_SDK_V1_PROGRESS_NORMALIZATION_TRACE_SCHEMA = (
    "obelisk.public-sdk-v1-progress-normalization-trace.v1"
)
APPROVED_IN_GAME_EVIDENCE_STATUS_SCHEMA = "obelisk.approved-in-game-evidence-status.v1"
PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISIONS_SCHEMA = "obelisk.player-identity-public-contract-decisions.v1"
PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_SCHEMA = (
    "obelisk.player-identity-public-contract-decision-record.v1"
)
PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_CHECK_SCHEMA = (
    "obelisk.player-identity-public-contract-decision-record-check.v1"
)
PLAYER_IDENTITY_PUBLIC_CONTRACT_GAP_REPORT_SCHEMA = (
    "obelisk.player-identity-public-contract-gap-report.v1"
)
PLAYER_IDENTITY_PUBLIC_CONTRACT_READINESS_CHECK_SCHEMA = (
    "obelisk.player-identity-public-contract-readiness-check.v1"
)
PLAYER_NOTICE_ACTION_SCHEMA = "obelisk.player-principal-lifecycle-player-notice-action.v1"
GENERIC_PLAYER_NOTICE_ACTION_SCHEMA = "obelisk.player-notice-action.v1"
GUARDED_BETA_NOTICE_ACTION_SCHEMA = "obelisk.player-principal-lifecycle-guarded-beta-notice-action.v1"
BETA_NOTICE_AUTHORITY_BOUNDARY_SCHEMA = "obelisk.player-principal-lifecycle-beta-notice-authority-boundary.v1"
DISCORD_BETA_BRIDGE_ACTIVE_NOTICE_SCHEMA = "obelisk.discord-beta-bridge-active-notice.v1"
DISCORD_BETA_BRIDGE_BOT_NOTICE_SCHEMA = "obelisk.discord-beta-bridge-bot-notice.v1"
DISCORD_BETA_BRIDGE_DRY_RUN_RECEIPT_SCHEMA = "obelisk.discord-beta-bridge-dry-run-receipt.v1"
DISCORD_BETA_BRIDGE_EVENT_SUMMARY_SCHEMA = "obelisk.discord-beta-bridge-event-summary.v1"
DISCORD_BETA_BRIDGE_TESTER_STATUS_SUMMARY_SCHEMA = "obelisk.discord-beta-bridge-tester-status-summary.v1"
ACTIVATION_PRECONDITIONS_SCHEMA = "obelisk.player-principal-lifecycle-activation-preconditions.v1"
WINDOW_REQUEST_CHECK_SCHEMA = "obelisk.player-principal-lifecycle-window-request-check.v1"
BUNDLE_PREFLIGHT_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle-preflight.v1"
BUNDLE_REPORT_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle.v1"
SCOPED_RELEASE_STATEMENT_OUTCOMES_SCHEMA = "obelisk.scoped-release-statement-outcomes.v1"
INSTALLED_SDK_PACKAGE_SHAPE_SCHEMA = "obelisk.installed-sdk-package-shape.v1"
INTERNAL_MODULE_READINESS_SCHEMA = "obelisk.internal-module-readiness.v1"
PASSIVE_MONITOR_LOG_METADATA_SCHEMA = "obelisk.passive-monitor-log-metadata.v1"
PASSIVE_ORGANIC_PLAYER_DETECTION_SCHEMA = "obelisk.passive-organic-player-detection.v1"
READY_LOG_COPY_SCHEMA = "obelisk.player-principal-lifecycle-ready-log-copy.v1"
APPROVED_RUNTIME_EVIDENCE_ARTIFACT_STATUS = "approved_runtime_observer_summary"
APPROVED_RUNTIME_EVIDENCE_CLASSIFICATION = "runtime_evidence_only"
SUMMARY_SCHEMA = "obelisk.runtime-observer-log-summary.v1"
EXPECTED_PROCESS_EVENT_ADDRESS = "0x1d34e20"
MODULE = "player_principal_lifecycle"
CHECK_JOIN_IN_PROGRESS_DIAGNOSTIC_TARGET = "ShooterGameMode.CheckJoinInProgress"
NEXT_BLOCKER_AFTER_RUNTIME_EVIDENCE = "identity_public_contract_gate_missing"
APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER = "approved_runtime_evidence_missing"
APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_EVIDENCE_BUNDLE = (
    "approved_runtime_principal_lifecycle_evidence_bundle"
)
SESSION_END_MISSING_CORRELATION_REASON_KEYS = frozenset(
    (
        "session_end_correlation_status_missing",
        "session_end_unresolved_noop_outcome",
    )
)
SERVER_ROOT = Path("/servidor/ark")
REPO_ROOT = Path(__file__).resolve().parents[1]
APPROVED_OFFLINE_WORKSPACE_ROOTS = protected_paths.approved_offline_workspace_roots()
REQUIRED_TOP_LEVEL_KEYS = frozenset(
    (
        "schema",
        "artifact_status",
        "readiness_classification",
        "approved_runtime_evidence_present",
        "runtime_evidence_ready",
        "promotion_ready",
        "public_header_allowed",
        "public_abi_ready",
        "public_sdk_ready",
        "v1_completion_ready",
        "runtime_ready",
        "public_capability_bits_now",
        "public_callback_abi_now",
        "output_artifact_identity",
        "approval",
        "operational_window",
        "source_summary",
        "consumer_boundary_cases",
        "privacy_boundary",
        "promotion_gate",
        "non_claims",
    )
)
EXPECTED_COPIED_LOG_PARENT = "live-validation-logs"
EXPECTED_COPIED_LOG_PATH_STATUS = "approved_offline_workspace"
EXPECTED_REQUEST_STATUS = "candidate_only_request_pack"
EXPECTED_OPERATOR_APPROVAL_RECEIPT_NON_CLAIMS = OPERATOR_APPROVAL_RECEIPT_NON_CLAIMS
EXPECTED_OBSERVER_ENV_KEYS = OBSERVER_ENV_KEYS
REQUIRED_OBSERVER_ENV_VALUES = {
    **REQUIRED_ENV,
    "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256": EXPECTED_BINARY_SHA256,
}
FORBIDDEN_POSITIVE_FLAG_KEYS = frozenset(
    (
        "complete_sdk_allowed",
        "complete_sdk_ready",
        "live_log_read_authorized",
        "live_log_reads_authorized",
        "live_logs_read",
        "live_ops_authorized",
        "public_header_ready",
        "reads_live_logs",
        "runtime_work_authorized",
        "runtime_capture_authorized",
        "server_operations_authorized",
        "live_server_log_reads_authorized",
        "runtime_ready",
        "stable_sdk_ready",
        "stable_claim_allowed",
        "stable_release_contract_claim_allowed",
        "stable_v1_sdk_claim",
        "stable_v1_sdk_claim_allowed",
        "plugin_hub_ready",
        "publication_ready",
        "public_sdk_ready",
        "public_abi_ready",
        "public_header_allowed",
        "route_ready",
        "promotion_ready",
        "v1_completion_ready",
        "sdk_accounting_counts_as_completed_surface",
        "p0_accounting_counts_as_promoted_surface",
        "server_operations_authorized_by_template",
        "runtime_work_authorized_by_template",
        "generated_template_authorizes_runtime",
        "request_pack_acceptance_authorizes_runtime",
        "authorizes_server_restart",
        "authorizes_marker_or_env_changes",
        "authorizes_discord_send",
        "touches_live_servers",
        "approved_runtime_evidence",
        "approved_runtime_evidence_present",
        "approved_runtime_evidence_ready",
        "runtime_evidence_ready",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_progress",
        "counts_as_p0_progress",
        "clears_approved_runtime_evidence_missing",
        "request_output_counts_as_approved_runtime_evidence",
        "window_request_counts_as_approved_runtime_evidence",
        "window_request_output_counts_as_approved_runtime_evidence",
        "runtime_window_request_counts_as_approved_runtime_evidence",
        "runtime_window_request_output_counts_as_approved_runtime_evidence",
        "passive_complete_triplets_count_as_approved_runtime_evidence",
        "passive_complete_triplet_counts_as_evidence",
        "passive_snapshots_as_evidence",
        "passive_snapshots_count_as_evidence",
        "passive_snapshot_rollup_counts_as_approved_runtime_evidence",
        "copied_log_presence_counts_as_approved_runtime_evidence",
        "copy_report_counts_as_approved_runtime_evidence",
        "dry_run_success_counts_as_approved_runtime_evidence",
        "historical_target_names_authorize_runtime",
        "marker_env_readiness_counts_as_approved_runtime_evidence",
        "player_notice_counts_as_approved_runtime_evidence",
        "public_reachability_counts_as_approved_runtime_evidence",
        "public_reachability_ready",
        "public_reachability_satisfies_runtime_evidence",
        "completion_status_counts_as_approved_runtime_evidence",
        "status_report_counts_as_approved_runtime_evidence",
        "planning_artifact_counts_as_approved_runtime_evidence",
        "planning_snapshot_counts_as_approved_runtime_evidence",
        "activation_preconditions_counts_as_approved_runtime_evidence",
        "player_notice_action_counts_as_approved_runtime_evidence",
        "guarded_beta_notice_action_counts_as_approved_runtime_evidence",
        "multi_surface_beta_capture_counts_as_approved_runtime_evidence",
        "multi_surface_beta_capture_replaces_player_principal_triplet",
        "multi_surface_candidate_queue_counts_as_approved_runtime_evidence",
        "beta_capture_counts_as_approved_runtime_evidence",
        "candidate_queue_counts_as_approved_runtime_evidence",
        "debug_capture_counts_as_approved_runtime_evidence",
        "debug_capture_evidence_ready",
        "candidate_debug_capture_ready",
        "start_end_only_counts_as_approved_runtime_evidence",
        "start_end_only_satisfies_requirement",
        "start_end_evidence_counts_as_approved_runtime_evidence",
        "principal_start_end_runtime_evidence_counts_as_approved_runtime_evidence",
        "check_join_in_progress_candidate_counts_as_approved_runtime_evidence",
        "check_join_in_progress_offline_counts_as_approved_runtime_evidence",
        "session_start_rejected_candidate_counts_as_approved_runtime_evidence",
        "session_start_rejected_role_satisfied",
        "replaces_player_principal_triplet",
        "replaces_player_principal_evidence",
        "replaces_approved_runtime_evidence",
        "replaces_strict_player_principal_triplet",
        "replaces_strict_runtime_triplet",
        "player_principal_triplet_replaced",
        "strict_player_principal_triplet_replaced",
        "accepted_for_contract_review",
        "accepted_for_contract_review_input",
        "contract_review_input_present",
        "contract_review_inputs_resolved",
        "contract_review_only",
        "contract_review_ready",
        "contract_reviewed",
        "reviewed_hash_current_contract_review_only",
        "reviewed_identity_public_contract",
        "reviewed_identity_public_contract_decision_record",
        "identity_public_contract_decision_record_accepted",
        "identity_public_contract_gate_resolved",
        "identity_public_contract_ready",
        "can_unlock_identity_public_contract_gate_missing",
        "can_unlock_public_identity_contract_readiness",
        "can_replace_reviewed_identity_public_contract_decision_record",
    )
)
GENERATED_BUNDLE_SIDECAR_ALLOWED_TRUE_STATUS_KEYS = frozenset(
    (
        "approved_runtime_evidence_present",
        "runtime_evidence_ready",
    )
)
GENERATED_BUNDLE_SIDECAR_REQUIRED_FALSE_KEYS = (
    FORBIDDEN_POSITIVE_FLAG_KEYS - GENERATED_BUNDLE_SIDECAR_ALLOWED_TRUE_STATUS_KEYS
) | frozenset(
    (
        "approved_runtime_evidence_granted_by_this_report",
        "bundle_report_counts_as_approved_runtime_evidence",
        "current_turn_authorized",
        "current_turn_runtime_authorized",
        "current_turn_scope_authorized",
        "current_turn_scope_ready",
        "live_ops_authorization_granted_by_this_report",
        "runtime_capture_authorization_granted_by_this_report",
        "server_authorization_granted_by_this_report",
        "status_report_paths_authorize_current_turn",
        "workspace_write_authorization_granted_by_this_report",
    )
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
UTC_TIMESTAMP_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z$")
LIFECYCLE_EVENT_LINE_RE = re.compile(
    r"\bPlayerPrincipalLifecycleObserver event sequence=(?P<sequence>\d+) "
    r"role=(?P<role>session_start|session_start_rejected|session_end)\b"
)
LOG_KEY_VALUE_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)=([^ \t.]+)")
PASSIVE_MONITOR_METADATA_RE = re.compile(
    r"^(?:\[[^\]]+\]\s+)*(?:passive_monitor_session\b|tick utc=|query(?:_warning)? instance=|"
    r"linuxgsm_skipped instance=|rcon_listplayers instance=|player_presence_context\b|"
    r"player_presence_detected instance=|observer_tail instance=|"
    r"observer instance=|player_presence_linger_(?:start|extend|complete)\b|"
    r"passive_snapshot_(?:captured|failed)\b|runtime_window(?:_|\b)|"
    r"(?:player_)?notice(?:_|\b)|beta_notice(?:_|\b)|confirmed_(?:beta_)?notice(?:_|\b))"
)
ALLOWED_SOURCE_KEYS = frozenset(("path", "sha256", "line_count"))
ALLOWED_APPROVAL_KEYS = frozenset(
    (
        "runtime_evidence_reviewed",
        "reviewed_by",
        "review_note",
        "runtime_work_authorized_by_this_manifest",
        "server_operations_authorized_by_this_manifest",
        "publication_authorized_by_this_manifest",
        "discord_authorized_by_this_manifest",
    )
)
ALLOWED_OPERATIONAL_WINDOW_KEYS = frozenset(
    (
        "schema",
        "ready",
        "operational_window_manifest_ready",
        "run_id",
        "obelisk_commit",
        "approval",
        "approved_window",
        "actual_capture",
        "rollback_window",
        "target",
        "manifest",
        "copied_log",
        "request_pack",
        "observer_env",
        "operator_approval_receipt",
        "preflight",
        "posture",
        "rollback",
        "log_budget",
        "claims",
        "user_policy",
        "notice_sent",
        "promotion_ready",
        "public_header_allowed",
        "public_abi_ready",
        "public_sdk_ready",
        "v1_completion_ready",
        "runtime_ready",
        "stable_claim_allowed",
        "request_pack_counts_as_approved_runtime_evidence",
        "preflight_counts_as_approved_runtime_evidence",
        "window_manifest_counts_as_approved_runtime_evidence",
        "completed_receipt_counts_as_approved_runtime_evidence",
        "approved_runtime_evidence_present",
        "approved_runtime_evidence_ready",
        "non_claims",
    )
)
REQUIRED_OPERATIONAL_WINDOW_FALSE_FLAGS = (
    "promotion_ready",
    "public_header_allowed",
    "public_abi_ready",
    "public_sdk_ready",
    "v1_completion_ready",
    "runtime_ready",
    "stable_claim_allowed",
    "request_pack_counts_as_approved_runtime_evidence",
    "preflight_counts_as_approved_runtime_evidence",
    "window_manifest_counts_as_approved_runtime_evidence",
    "completed_receipt_counts_as_approved_runtime_evidence",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
)
ALLOWED_OPERATIONAL_WINDOW_COPIED_LOG_KEYS = frozenset(("path", "path_status", "sha256"))
ALLOWED_OPERATIONAL_WINDOW_ARTIFACT_KEYS = frozenset(("path", "sha256", "verified"))
ALLOWED_OPERATIONAL_WINDOW_PREFLIGHT_KEYS = frozenset(("pre", "post"))
ALLOWED_OPERATIONAL_WINDOW_POSTURE_KEYS = frozenset(
    (
        "pre_check",
        "post_check",
        "pre_posture",
        "post_posture",
        "plugins_disabled",
        "scanner_disabled",
        "dispatch_limit",
        "wrapper_profile",
        "observer_exclusivity",
        "sibling_marker_entries",
        "sibling_observer_env",
        "debug_escape_markers",
        "callback_escape_markers",
        "native_exec_disabled",
        "ptrace_disabled",
        "single_module_summary",
    )
)
ALLOWED_OPERATIONAL_WINDOW_ROLLBACK_KEYS = frozenset(
    ("completed", "observer_env_survived", "observer_marker_survived", "delta")
)
ALLOWED_OPERATIONAL_WINDOW_CLAIMS_KEYS = frozenset(("delivery_claim", "principal_claim"))
REQUIRED_OPERATIONAL_WINDOW_SIBLING_FILENAMES = {
    "manifest": "window-manifest.env",
    "request_pack": "window-request.json",
    "observer_env": "observer-window.env",
    "operator_approval_receipt": "operator-approval-receipt.json",
    "preflight.pre": "preflight-pre.json",
    "preflight.post": "preflight-post.json",
}
REQUIRED_IMPLICIT_OPERATIONAL_WINDOW_SIDECARS = {
    "operator_approval_request_md": "operator-approval-request.md",
}
EXPECTED_OPERATIONAL_WINDOW_TOP_LEVEL_JSON_SIDECARS = frozenset(
    (
        "window-request.json",
        "operator-approval-receipt.json",
        "preflight-pre.json",
        "preflight-post.json",
        "ready-log-copy.json",
    )
)
READY_LOG_COPY_FILENAME = "ready-log-copy.json"
CONFIRMED_BETA_NOTICE_FILENAME = "beta-notice.confirmed.json"
CONFIRMED_NOTICE_SCHEMA = NOTICE_PREP_SCHEMA
INSTALLED_LIBOBELISK_SIDECAR_FILENAME = "installed-libobelisk.env"
POST_RESTART_PREFLIGHT_SIDECAR_FILENAME = "post-restart-preflight.env"
INSTALLED_LIBOBELISK_SIDECAR_SCHEMA = "obelisk.installed-libobelisk-artifact.v1"
POST_RESTART_PREFLIGHT_SIDECAR_SCHEMA = "obelisk.player-principal-lifecycle-post-restart-preflight.v1"
EXPECTED_INSTALLED_LIBOBELISK_PATH = "/servidor/ark/obelisk/lib/libobelisk.so"
RUNTIME_REPLACEMENT_SIDECAR_FALSE_FLAGS = frozenset(
    (
        "server_operations_authorized",
        "runtime_work_authorized",
        "runtime_capture_authorized",
        "live_ops_authorized",
        "approved_runtime_evidence_present",
        "approved_runtime_evidence_ready",
        "runtime_evidence_ready",
        "counts_as_approved_runtime_evidence",
        "installed_libobelisk_counts_as_approved_runtime_evidence",
        "post_restart_preflight_counts_as_approved_runtime_evidence",
        "promotion_ready",
        "public_header_allowed",
        "public_abi_ready",
        "public_sdk_ready",
        "v1_completion_ready",
        "runtime_ready",
        "stable_claim_allowed",
    )
)
READY_LOG_COPY_REQUIRED_ROLES = ("session_start", "session_start_rejected", "session_end")
ALLOWED_DUPLICATE_CONTEXT_ROLES = frozenset(("session_start", "session_end"))
READY_LOG_COPY_ALLOWED_READINESS = frozenset(
    (
        "ready_complete_role_triplet",
        "blocked_ambiguous_duplicate_lifecycle_roles",
        "blocked_invalid_fresh_window",
        "blocked_lifecycle_events_outside_fresh_window",
        "blocked_lifecycle_roles_outside_fresh_window",
        "blocked_lifecycle_triplet_order_mismatch",
        "blocked_missing_observer_enable",
        "blocked_missing_fresh_window",
        "blocked_binary_sha256_mismatch",
        "blocked_missing_lifecycle_roles",
        "blocked_before_source_analysis",
        "blocked_observer_enable_outside_fresh_window",
        "blocked_observer_lifecycle_timestamp_not_utc",
        "blocked_diagnostic_or_rejected_lifecycle_lines",
    )
)
READY_LOG_COPY_REQUIRED_FALSE_KEYS = frozenset(
    (
        "approved_runtime_evidence",
        "approved_runtime_evidence_present",
        "approved_runtime_evidence_ready",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_evidence",
        "runtime_ready",
        "public_sdk_ready",
        "public_abi_ready",
        "public_header_allowed",
        "promotion_ready",
        "v1_completion_ready",
        "stable_claim_allowed",
        "publication_authorized",
        "discord_sent_by_this_report",
        "server_operations_authorized_by_this_report",
        "marker_env_changes_authorized_by_this_report",
    )
)
READY_LOG_COPY_ALLOWED_NON_CLAIMS = frozenset(
    (
        "ready-log copy is operational copy readiness only",
        "copied Obelisk.log is still not approved runtime evidence until sibling-set bundle checkers accept it",
        "this helper does not start, stop, restart, send Discord, edit markers/env, publish, or claim SDK readiness",
    )
)
CONFIRMED_NOTICE_REQUIRED_FALSE_KEYS = frozenset(
    (
        "activation_allowed",
        "activation_allowed_before_notice_sent",
        "activation_preconditions_met",
        "approved_runtime_evidence",
        "approved_runtime_evidence_present",
        "approved_runtime_evidence_ready",
        "authorizes_discord",
        "authorizes_runtime_work",
        "authorizes_server_operations",
        "confirmed_send_authorizes_activation",
        "confirmed_send_authorizes_runtime_capture",
        "confirmed_send_authorizes_server_operations",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_evidence",
        "counts_toward_p0_dependency_chain",
        "counts_toward_public_sdk",
        "counts_toward_runtime",
        "counts_toward_sdk",
        "counts_toward_v1_completion",
        "discord_authorized",
        "discord_authorized_by_request",
        "discord_authorized_by_this_report",
        "discord_notice_authorized",
        "discord_send_authorized",
        "live_log_permission_granted",
        "live_log_reads_authorized",
        "live_ops_authorized",
        "marker_env_changes_authorized",
        "promotion_ready",
        "public_abi_ready",
        "public_or_runtime_accounting_allowed",
        "public_sdk_ready",
        "read_live_logs",
        "reads_live_logs",
        "request_pack_authorizes_discord",
        "route_ready",
        "runtime_capture_authorized",
        "runtime_evidence_present",
        "runtime_evidence_ready",
        "runtime_ready",
        "runtime_window_authorized",
        "runtime_work_authorized",
        "sdk_evidence_ready",
        "send_performed_by_request_pack",
        "server_operations_authorized",
        "stable_claim_allowed",
        "v1_completion_ready",
        "workspace_writes_authorized",
    )
)
APPROVED_BUNDLE_DIRNAME = "approved-bundle"
APPROVED_BUNDLE_MANIFEST_FILENAME = "approved-runtime-principal-lifecycle-evidence.json"
EXPECTED_APPROVED_BUNDLE_GENERATED_JSON_OUTPUTS = frozenset(
    (
        "runtime-observer-summary.json",
        "player-principal-lifecycle-window-manifest.check.json",
        "approved-runtime-principal-lifecycle-evidence.check.json",
        "approved-runtime-principal-lifecycle-evidence.promote-check.json",
        "approved-runtime-principal-lifecycle-evidence.public-readiness-check.json",
        "approved-runtime-principal-lifecycle-evidence.runtime-readiness-check.json",
        "approved-runtime-principal-lifecycle-evidence.consume-gate.json",
        "evidence-bundle-report.json",
    )
)
OFFLINE_ARTIFACT_GATE_RESULT_SCHEMA = "obelisk.offline-artifact-gate-result.v1"
EXPECTED_APPROVED_BUNDLE_GENERATED_OUTPUT_SCHEMAS = {
    "runtime-observer-summary.json": SUMMARY_SCHEMA,
    "player-principal-lifecycle-window-manifest.check.json": WINDOW_CHECK_SCHEMA,
    "approved-runtime-principal-lifecycle-evidence.check.json": REPORT_SCHEMA,
    "approved-runtime-principal-lifecycle-evidence.promote-check.json": REPORT_SCHEMA,
    "approved-runtime-principal-lifecycle-evidence.public-readiness-check.json": REPORT_SCHEMA,
    "approved-runtime-principal-lifecycle-evidence.runtime-readiness-check.json": REPORT_SCHEMA,
    "approved-runtime-principal-lifecycle-evidence.consume-gate.json": OFFLINE_ARTIFACT_GATE_RESULT_SCHEMA,
    "evidence-bundle-report.json": BUNDLE_REPORT_SCHEMA,
}
REQUIRED_REQUEST_PACK_REPLAY_SIDECAR_KEYS = frozenset(
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
OPERATOR_APPROVAL_RECEIPT_SCOPE_FALSE_FLAGS = (
    "standing_approval",
    "reusable",
    "future_windows_authorized",
    "scope_expansion_authorized",
    "unbound_artifacts_authorized",
)
OPERATOR_APPROVAL_RECEIPT_NON_AUTHORIZATION_FLAGS = (
    "request_pack_acceptance_authorizes_runtime",
    "generated_template_authorizes_runtime",
    "server_operations_authorized_by_template",
    "runtime_work_authorized_by_template",
    "discord_authorized",
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
APPROVED_OPERATOR_ROLES = frozenset(("operator",))
OPERATIONAL_WINDOW_REPLAY_KEYS = (
    "schema",
    "ready",
    "operational_window_manifest_ready",
    "run_id",
    "obelisk_commit",
    "approval",
    "approved_window",
    "actual_capture",
    "rollback_window",
    "target",
    "manifest",
    "copied_log",
    "request_pack",
    "observer_env",
    "operator_approval_receipt",
    "preflight",
    "posture",
    "rollback",
    "log_budget",
    "claims",
    "user_policy",
    "notice_sent",
    "promotion_ready",
    "public_header_allowed",
    "public_abi_ready",
    "public_sdk_ready",
    "v1_completion_ready",
    "runtime_ready",
    "stable_claim_allowed",
    "request_pack_counts_as_approved_runtime_evidence",
    "preflight_counts_as_approved_runtime_evidence",
    "window_manifest_counts_as_approved_runtime_evidence",
    "completed_receipt_counts_as_approved_runtime_evidence",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "non_claims",
)
ALLOWED_CONSUMER_CASE_KEYS = frozenset(
    (
        "case",
        "result",
        "provenance",
        "runtime_observed",
        "lookup_allowed",
        "mutation_allowed",
        "return_override_allowed",
        "public_sdk_surface",
    )
)
ALLOWED_PROMOTION_GATE_KEYS = frozenset(
    ("runtime_evidence_ready", "ready", "promotion_ready", "public_sdk_ready", "runtime_ready")
)
REQUIRED_CONSUMER_CASES = frozenset(("stale_after_logout", "malformed_or_unsupported_evidence"))
REQUIRED_SESSION_START_EVENT_CASE = {
    "target": "ShooterGameMode.HandleNewPlayer",
    "role": "session_start",
    "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
    "copied_bool_values": ["1", "1"],
    "principal_action": "candidate_created",
    "apply_status": "session_start_created",
    "correlation_status": "not_applicable",
}
REQUIRED_CHECK_JOIN_IN_PROGRESS_REJECTED_EVENT_CASE = {
    "target": "ShooterGameMode.CheckJoinInProgress",
    "role": "session_start_rejected",
    "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
    "copied_bool_values": ["1", "0"],
    "principal_action": "none",
    "apply_status": "session_start_rejected_noop",
    "correlation_status": "not_applicable",
}
STRICT_REJECTED_START_EXPECTED_SHAPE = "ShooterGameMode.CheckJoinInProgress(1,0)"
REQUIRED_SESSION_END_EVENT_CASE = {
    "target": "ShooterGameMode.OnLogout",
    "role": "session_end",
    "copied_bool_fields": [],
    "copied_bool_values": [],
    "principal_action": "candidate_invalidated",
    "apply_status": "session_end_invalidated",
    "correlation_status": "matched",
}
REQUIRED_OBSERVED_EVENT_CASES = (
    REQUIRED_SESSION_START_EVENT_CASE,
    REQUIRED_CHECK_JOIN_IN_PROGRESS_REJECTED_EVENT_CASE,
    REQUIRED_SESSION_END_EVENT_CASE,
)
REQUIRED_OBSERVED_EVENT_CASE_BY_ROLE = {
    str(case["role"]): case for case in REQUIRED_OBSERVED_EVENT_CASES
}
APPROVED_RUNTIME_BUNDLE_BUILDER_COMMAND_TEMPLATE = (
    "python3 scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py "
    "--copied-log <approved-offline>/live-validation-logs/<run-id>/Obelisk.log "
    "--window-manifest <same-dir>/window-manifest.env "
    "--output-dir <same-dir>/approved-bundle "
    "--obelisk-commit <reviewed-obelisk-commit> "
    "--reviewed-by <reviewer> "
    "--review-note <consume-only-review-note>"
)
REQUIRED_OBSERVED_EVENT_CASE_ALTERNATIVES = (
    {
        "id": "check_join_in_progress_rejected_start",
        "cases": (
            REQUIRED_SESSION_START_EVENT_CASE,
            REQUIRED_CHECK_JOIN_IN_PROGRESS_REJECTED_EVENT_CASE,
            REQUIRED_SESSION_END_EVENT_CASE,
        ),
    },
)
REQUIRED_OBSERVED_EVENT_CASE_SET = frozenset(
    tuple((key, tuple(value) if isinstance(value, list) else value) for key, value in case.items())
    for alternative in REQUIRED_OBSERVED_EVENT_CASE_ALTERNATIVES
    for case in alternative["cases"]
)
EXPECTED_LIFECYCLE_EVENT_STATUS_PROOFS = {
    str(case["role"]): {
        "apply_status": case["apply_status"],
        "correlation_status": case["correlation_status"],
    }
    for case in REQUIRED_OBSERVED_EVENT_CASES
}
OBSERVED_EVENT_CASE_KEYS = frozenset(
    (
        "sequence",
        "target",
        "role",
        "copied_bool_fields",
        "copied_bool_values",
        "principal_action",
        "apply_status",
        "correlation_status",
    )
)
EXPECTED_DETAIL_VALUES = {
    "observer_gate": {
        "target_set": {"players-lifecycle-anchor-candidates"},
        "limit": {10},
        "dispatch_limit": {0},
        "delivery_claim": {"none"},
        "principal_claim": {"none"},
    },
    "ShooterGameMode.HandleNewPlayer": {
        "role": {"session_start"},
        "post_original": {"true"},
        "copied_bool_fields": {"bIsFromLogin,ReturnValue"},
        "copied_bool_values": {"1,1"},
        "redacted_count": {3},
        "redacted_fields": {"NewPlayer,PlayerData,PlayerCharacter"},
        "principal_action": {"candidate_created"},
        "apply_status": {"session_start_created"},
        "correlation_status": {"not_applicable"},
        "principal_id_logged": {"false"},
        "principal_generation_logged": {"false"},
        "delivery_claim": {"none"},
    },
    "ShooterGameMode.CheckJoinInProgress": {
        "role": {"session_start_rejected"},
        "post_original": {"true"},
        "copied_bool_fields": {"bIsFromLogin,ReturnValue"},
        "copied_bool_values": {"1,0"},
        "redacted_count": {1},
        "redacted_fields": {"NewPlayer"},
        "principal_action": {"none"},
        "apply_status": {"session_start_rejected_noop"},
        "correlation_status": {"not_applicable"},
        "principal_id_logged": {"false"},
        "principal_generation_logged": {"false"},
        "delivery_claim": {"none"},
    },
    "ShooterGameMode.OnLogout": {
        "role": {"session_end"},
        "post_original": {"true"},
        "copied_bool_fields": {""},
        "copied_bool_values": {""},
        "redacted_count": {1},
        "redacted_fields": {"Exiting"},
        "principal_action": {"candidate_invalidated"},
        "apply_status": {"session_end_invalidated"},
        "correlation_status": {"matched"},
        "principal_id_logged": {"false"},
        "principal_generation_logged": {"false"},
        "delivery_claim": {"none"},
    },
}
HANDLE_NEW_PLAYER_SESSION_START_DETAIL_VALUES = {
    "role": {"session_start"},
    "post_original": {"true"},
    "copied_bool_fields": {"bIsFromLogin,ReturnValue"},
    "copied_bool_values": {"1,1"},
    "redacted_count": {3},
    "redacted_fields": {"NewPlayer,PlayerData,PlayerCharacter"},
    "principal_action": {"candidate_created"},
    "apply_status": {"session_start_created"},
    "correlation_status": {"not_applicable"},
    "principal_id_logged": {"false"},
    "principal_generation_logged": {"false"},
    "delivery_claim": {"none"},
}
CHECK_JOIN_IN_PROGRESS_REJECTED_DETAIL_VALUES = {
    "role": {"session_start_rejected"},
    "post_original": {"true"},
    "copied_bool_fields": {"bIsFromLogin,ReturnValue"},
    "copied_bool_values": {"1,0"},
    "redacted_count": {1},
    "redacted_fields": {"NewPlayer"},
    "principal_action": {"none"},
    "apply_status": {"session_start_rejected_noop"},
    "correlation_status": {"not_applicable"},
    "principal_id_logged": {"false"},
    "principal_generation_logged": {"false"},
    "delivery_claim": {"none"},
}
EXPECTED_DETAIL_VALUES_BY_OBSERVED_EVENT_ALTERNATIVE = {
    "check_join_in_progress_rejected_start": {
        "observer_gate": EXPECTED_DETAIL_VALUES["observer_gate"],
        "ShooterGameMode.HandleNewPlayer": HANDLE_NEW_PLAYER_SESSION_START_DETAIL_VALUES,
        "ShooterGameMode.CheckJoinInProgress": CHECK_JOIN_IN_PROGRESS_REJECTED_DETAIL_VALUES,
        "ShooterGameMode.OnLogout": EXPECTED_DETAIL_VALUES["ShooterGameMode.OnLogout"],
    },
}
EXPECTED_RUNTIME_SUMMARY_FUNCTIONS = frozenset(
    function
    for values in EXPECTED_DETAIL_VALUES_BY_OBSERVED_EVENT_ALTERNATIVE.values()
    for function in values
)


def required_lifecycle_triplet_for_next_action() -> list[dict[str, Any]]:
    shapes = {
        "session_start": "ShooterGameMode.HandleNewPlayer(1,1)",
        "session_start_rejected": STRICT_REJECTED_START_EXPECTED_SHAPE,
        "session_end": "ShooterGameMode.OnLogout()",
    }
    return [
        {
            **case,
            "shape": shapes[str(case["role"])],
            "safe_status_proof": {
                "apply_status": case["apply_status"],
                "correlation_status": case["correlation_status"],
            },
        }
        for case in REQUIRED_OBSERVED_EVENT_CASES
    ]


def approved_runtime_evidence_missing_next_action(
    strict_rejected_start_diagnostics: dict[str, Any] | None = None,
    observer_no_lifecycle_role_diagnostics: dict[str, Any] | None = None,
    session_end_missing_correlation_diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    action: dict[str, Any] = {
        "action": "create_checker_accepted_approved_runtime_principal_lifecycle_evidence_bundle",
        "current_route_blocker": APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER,
        "required_artifact": APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_EVIDENCE_BUNDLE,
        "builder_command_template": APPROVED_RUNTIME_BUNDLE_BUILDER_COMMAND_TEMPLATE,
        "required_copied_log_lifecycle_sequence": required_lifecycle_triplet_for_next_action(),
        "required_sibling_sidecars": [
            "window-request.json",
            "observer-window.env",
            "operator-approval-request.md",
            "operator-approval-receipt.json",
            "preflight-pre.json",
            "preflight-post.json",
            "window-manifest.env",
            "Obelisk.log",
        ],
        "checker_acceptance_required": {
            "schema": SCHEMA,
            "check_report_schema": REPORT_SCHEMA,
            "ready": True,
            "approved_runtime_evidence_present": True,
            "runtime_evidence_ready": True,
            "next_blocker_after_acceptance": NEXT_BLOCKER_AFTER_RUNTIME_EVIDENCE,
        },
        "sdk_p0_progress_before_checker_accepted_bundle": "0",
        "non_claim": (
            "Only the checker-accepted copied lifecycle bundle can clear approved_runtime_evidence_missing; "
            "request packs, window manifests, passive snapshots, start/end-only artifacts, contract-review "
            "records, and status reports do not count."
        ),
    }
    if strict_rejected_start_diagnostics is not None:
        action["strict_rejected_start_diagnostics"] = {
            key: strict_rejected_start_diagnostics.get(key)
            for key in (
                "partial_start_end_present",
                "missing_strict_rejected_start",
                "strict_rejected_start_expected_shape",
                "strict_rejected_start_observed_shape",
            )
        }
    if observer_no_lifecycle_role_diagnostics is not None:
        action["observer_no_lifecycle_role_diagnostics"] = {
            key: observer_no_lifecycle_role_diagnostics.get(key)
            for key in (
                "observer_only_no_role_window_detected",
                "player_present_but_no_lifecycle_roles",
                "source_log_not_ready_reason",
                "source_log_not_ready_blockers",
                "roles_present",
                "missing_roles",
                "copy_readiness",
                "reported_blockers",
                "player_presence_context",
                "approved_runtime_evidence",
                "counts_as_approved_runtime_evidence",
            )
        }
    if session_end_missing_correlation_diagnostics is not None:
        action["session_end_missing_correlation_diagnostics"] = {
            key: session_end_missing_correlation_diagnostics.get(key)
            for key in (
                "classification",
                "copied_log_material",
                "accepted_lifecycle_event_count",
                "malformed_observer_lines",
                "unsafe_lifecycle_event_reasons",
                "roles_present",
                "missing_accepted_lifecycle_roles",
                "required_next_material",
                "approved_runtime_evidence",
                "counts_as_approved_runtime_evidence",
                "counts_as_runtime_evidence",
            )
        }
    return action
ALLOWED_SOURCE_SUMMARY_PROMOTION_GATE_KEYS = frozenset(("gate_type", "ready", "blockers", "approval_authority"))
EXPECTED_SOURCE_SUMMARY_PROMOTION_GATE = {
    "gate_type": "runtime_observer_observational_only",
    "ready": False,
    "approval_authority": "downstream_bundle_checker_only",
    "blockers": [
        "runtime_observer_evidence_only",
        "requires_isolated_capture_or_second_source_for_promotion",
    ],
}
FORBIDDEN_READINESS_ALIAS_VALUES = frozenset(
    (
        "ready",
        "complete",
        "completed",
        "stable",
        "sdk",
        "sdk_ready",
        "sdk_complete",
        "sdk_completed",
        "sdk_stable",
        "public_sdk",
        "public_sdk_ready",
        "public_sdk_complete",
        "public_sdk_completed",
        "public_sdk_stable",
        "runtime_ready",
        "runtime_complete",
        "runtime_completed",
        "runtime_stable",
        "v1_ready",
        "v1_complete",
        "v1_completed",
        "v1_stable",
        "v1_sdk_ready",
        "v1_sdk_complete",
        "v1_sdk_completed",
        "v1_sdk_stable",
        "public_ready",
        "public_readiness",
        "promotion_ready",
        "release_ready",
        "accepted",
        "allowed",
        "approved",
        "available",
        "enabled",
        "present",
        "supported",
        "validated",
    )
)
READINESS_ALIAS_CONTEXT_RE = re.compile(
    r"(?:^|[._\-\[\]])(?:artifact_status|status|classification|readiness|ready|"
    r"completion|complete|sdk|claim|promotion|release|support|package|label|tier)"
    r"(?:$|[._\-\[\]])",
    re.IGNORECASE,
)
PRIVACY_BOUNDARY_KEYS = frozenset(
    (
        "copied_opaque_principal_only",
        "redacted_runtime_observer",
        "player_identifiers_logged",
        "lookup_allowed",
        "resource_handle_allowed",
        "mutation_allowed",
        "return_override_allowed",
    )
)
REQUIRED_NON_CLAIMS = frozenset(
    (
        "approved runtime observer evidence only",
        "does not promote public player identity, lookup, permissions, commands, moderation, admin authority, mutation, return override, ResourceHandle, or v1 SDK readiness",
        "does not expose Steam/EOS ids, player names, IPs, tribe ids, UE pointers, FNames, GObjects, raw params, or persistent lookup keys",
        "does not authorize server operations, Discord updates, GitHub publication, tags, or release claims",
    )
)
STRICT_TRIPLET_CANDIDATE_SUMMARY_PATH = (
    f"$.source_summary.modules.{MODULE}.strict_lifecycle_triplet_candidate_summary"
)
STRICT_TRIPLET_CANDIDATE_SUMMARY_NON_CLAIM = (
    "Analyzer strict triplet candidate summaries are copied-log routing signals only. "
    "They do not approve runtime evidence, runtime readiness, public SDK readiness, "
    "SDK/P0 progress, publication, or stable SDK claims."
)
ALLOWED_POSITIVE_MATCH_NON_CLAIMS = frozenset(
    (
        ARTIFACT_BINDING_NON_AUTHORIZATION,
        BRIEF_NON_AUTHORIZATION,
        APPROVAL_SCOPE_NON_AUTHORIZATION,
        BETA_RUNTIME_CHOREOGRAPHY_NON_AUTHORIZATION,
        DIRECT_JOIN_PLAN_NON_AUTHORIZATION,
        DRIFT_FIX_DEPLOYMENT_INTENT_NON_AUTHORIZATION,
        *EXPECTED_REQUEST_PACK_NON_CLAIMS,
        *EXPECTED_OPERATOR_APPROVAL_RECEIPT_NON_CLAIMS,
        *REQUIRED_OPERATIONAL_WINDOW_NON_CLAIMS,
        *REQUIRED_NON_CLAIMS,
        STRICT_TRIPLET_CANDIDATE_SUMMARY_NON_CLAIM,
        PLAYER_PRESENCE_SAFETY_NON_AUTHORIZATION,
        REPLAY_NON_AUTHORIZATION,
    )
)
FORBIDDEN_KEY_RE = re.compile(
    r"(?:steam|eos|unique[_-]?net|player[_-]?(?:id|name|data)|ip(?:v4|v6)?|tribe[_-]?id|"
    r"platform[_-]?ids?|transfer[_-]?ids?|private[_-]?(?:identifier|user[_-]?data)|"
    r"chat[_-]?(?:text|message|payload)|command[_-]?(?:text|message|payload)|"
    r"permission[_-]?state|admin[_-]?state|"
    r"resourcehandle|gobjects?|fnames?|fname[_-]?(?:index|id)|gobject[_-]?(?:index|id)|"
    r"uobject|ue[_-]?pointer|raw[_-]?(?:params?|payload|pointer|trace|buffers?)|"
    r"object[_-]?(?:address|name|coordinates?|coords)|"
    r"(?:identity|identifier|player|steam|eos)[_-]?hash|hashed[_-]?(?:private|identity|identifier|player))",
    re.IGNORECASE,
)
COPIED_LOG_UNSAFE_TEXT_RE = re.compile(
    r"\b(?:steam(?:id|[_ -]?id)|eos[_ -]?id|unique[_ -]?net[_ -]?id|"
    r"player[_ -]?(?:id|name)|ip(?:v4|v6)?[_ -]?(?:address)?|tribe[_ -]?id|"
    r"chat[_ -]?(?:text|message|payload)|command[_ -]?(?:text|message|payload)|"
    r"permission[_ -]?state|admin[_ -]?state|resourcehandle|"
    r"uobject|ue[_ -]?pointer|raw[_ -]?(?:params?|payload|pointer|trace|buffers?)|"
    r"object[_ -]?(?:address|name|coordinates?|coords)|"
    r"(?:identity|identifier|player|steam|eos)[_ -]?hash|"
    r"hashed[_ -]?(?:private|identity|identifier|player))\b",
    re.IGNORECASE,
)
COPIED_LOG_UNSAFE_KEY_RE = re.compile(
    r"^(?:steam(?:id|[_-]?id)?|eos(?:[_-]?id)?|unique[_-]?net[_-]?id|"
    r"player[_-]?(?:id|name|data)|ip(?:v4|v6)?(?:[_-]?address)?|tribe[_-]?id|"
    r"platform[_-]?ids?|transfer[_-]?ids?|private[_-]?(?:identifier|user[_-]?data)|"
    r"chat[_-]?(?:text|message|payload)|command[_-]?(?:text|message|payload)|"
    r"permission[_-]?state|admin[_-]?state|resourcehandle|"
    r"gobjects?|fnames?|fname[_-]?(?:index|id)|gobject[_-]?(?:index|id)|"
    r"uobject|ue[_-]?pointer|raw[_-]?(?:params?|payload|pointer|trace|buffers?)|"
    r"object[_-]?(?:address|name|coordinates?|coords)|"
    r"(?:identity|identifier|player|steam|eos)[_-]?hash|"
    r"hashed[_-]?(?:private|identity|identifier|player))$",
    re.IGNORECASE,
)
COPIED_LOG_ALLOWED_PRIVACY_KEYS = frozenset(
    (
        "principal_id_logged",
        "principal_generation_logged",
        "redacted_fields",
        "redacted_count",
    )
)
POSITIVE_CAPABILITY_CLAIM_RE = re.compile(
    r"(?:public[_ -]?ready|identity[_ -]?ready|permissions?[_ -]?unlocked|"
    r"command[_ -]?route[_ -]?ready|counts?[_ -]?towards?[_ -]?sdk|"
    r"public[_ -]?(?:sdk|player[_ -]?identity|header)|"
    r"(?:public|runtime|sdk|public[_ -]?sdk|player[_ -]?identity|identity)[_ -]?"
    r"(?:ready|readiness|enabled|allowed|supported|complete|completed|completion|available|active|validated|accepted)|"
    r"(?:(?:request[_ -]?pack|window[_ -]?request|preflight|(?:completed[_ -]?)?receipt|"
    r"operator[_ -]?approval[_ -]?(?:request|receipt)|operator[_ -]?request|"
    r"approval[_ -]?request|window[_ -]?manifest|observer[_ -]?(?:window[_ -]?)?env|"
    r"window[_ -]?env|env(?:ironment)?|(?:source[_ -]?)?markers?|copied[_ -]?(?:log|bundle)|"
    r"stale[_ -]?bundle|sidecars?|artifacts?)[_ -]?"
    r"(?:counts?[_ -]?as|is|are|proves?|provides?|authorizes?|approves?)[_ -]?"
    r"approved[_ -]?runtime[_ -]?evidence)|"
    r"(?:public[_ -]?)?(?:runtime[_ -]?)?v1[_ -]?(?:sdk[_ -]?)?"
    r"(?:ready|readiness|enabled|allowed|supported|complete|completed|completion)|"
    r"(?:stable|complete|full|production)[_ -]?(?:v1[_ -]?)?(?:sdk[_ -]?)?claim[_ -]?(?:allowed|ready|enabled|supported)|"
    r"(?:stable|complete|full|production)[_ -]?sdk[_ -]?(?:ready|allowed|claim)|"
    r"stable[_ -]?release[_ -]?contract[_ -]?claim[_ -]?allowed|"
    r"player[_ -]?identity[_ -]?(?:promotion|ready|readiness)|"
    r"(?:sdk|runtime|lookup|permissions?|admin|command(?:s|[_ -]?(?:reply|response|routing|support))?|"
    r"plugin[_ -]?delivery|mutation|return[_ -]?override|resourcehandle)[_ -]?"
    r"(?:ready|readiness|enabled|allowed|supported|promoted|delivered)|"
    r"(?:route|routing|sdk[_ -]?accounting|sdk[_ -]?route[_ -]?accounting)[_ -]?"
    r"(?:ready|readiness|enabled|allowed|support(?:ed)?|promoted|delivered|accepted|count(?:s|ed)?)|"
    r"(?:support|package|support[_ -]?package|package[_ -]?label|support[_ -]?label|"
    r"support[_ -]?tier|package[_ -]?tier)[_ -]?"
    r"(?:ready|readiness|enabled|allowed|approved|accepted|supported|complete|completed|validated|present)|"
    r"command[_ -]?(?:reply|response|routing|support)|"
    r"(?:lookup|mutation|return[_ -]?override)[_ -]?allowed)",
    re.IGNORECASE,
)
OPERATIONAL_AUTHORIZATION_CLAIM_RE = re.compile(
    r"(?:(?:server|runtime)[_ -]?(?:operations?|work|capture|observation)[_ -]?"
    r"(?:ready|readiness|enabled|allowed|authorized|approved)|"
    r"(?:live[_ -]?(?:ops?|logs?)|live[_ -]?server[_ -]?logs?)[_ -]?"
    r"(?:reads?|reading|access|capture|tail|tails|watch|authorized|approved|allowed|enabled)[_ -]?"
    r"(?:ready|readiness|enabled|allowed|authorized|approved|granted)?|"
    r"(?:server[_ -]?)?(?:starts?|stops?|restarts?)[_ -]?(?:allowed|authorized|approved|ready|enabled)|"
    r"(?:marker|env|environment|state)[_ -]?(?:changes?|edits?|ops|operations?)[_ -]?"
    r"(?:allowed|authorized|approved|ready|enabled)|"
    r"(?:discord|github|publication|publishing|release|tag)[_ -]?"
    r"(?:allowed|authorized|approved|ready|enabled|published))",
    re.IGNORECASE,
)
NEGATIVE_CLAIM_CONTEXT_RE = re.compile(
    r"\b(?:does\s+not|do\s+not|not|no|never|without|blocked|forbidden|reject(?:ed|s)?|fail[-_ ]closed)\b",
    re.IGNORECASE,
)
NEGATED_CAPABILITY_ACTION_RE = re.compile(
    r"\b(?:does\s+not|do\s+not|doesn't|don't|cannot|can't|must\s+not|never|no|not)\s+"
    r"(?:claim|promote|authorize|enable|allow|support|deliver|provide|expose|make|mark|report|treat|set)\b",
    re.IGNORECASE,
)
NEGATED_CAPABILITY_BOUNDARY_RE = re.compile(
    r"\b(?:without|blocked|forbidden|reject(?:ed|s)?|fail[-_ ]closed)\b",
    re.IGNORECASE,
)
NEGATION_SCOPE_SPLIT_RE = re.compile(
    r"[,.;\n]|\s+\b(?:and|but|then|however|unless|while)\b\s+",
    re.IGNORECASE,
)
ALLOWED_FORBIDDEN_KEY_PATHS = (
    "$.schema",
    "$.privacy_boundary.copied_opaque_principal_only",
    "$.privacy_boundary.redacted_runtime_observer",
    "$.privacy_boundary.player_identifiers_logged",
    "$.privacy_boundary.lookup_allowed",
    "$.privacy_boundary.resource_handle_allowed",
    "$.privacy_boundary.mutation_allowed",
    "$.privacy_boundary.return_override_allowed",
    "$.source_summary.modules.player_principal_lifecycle",
    "$.source_summary.modules.player_principal_lifecycle.diagnostic_lifecycle_property_fname_mismatch_summary",
    "$.source_summary.modules.player_principal_lifecycle.diagnostic_lifecycle_property_fname_mismatch_target_summary",
    "$.source_summary.modules.player_principal_lifecycle.player_principal_lifecycle_event_split_summary",
    STRICT_TRIPLET_CANDIDATE_SUMMARY_PATH,
    "$.operational_window.operator_approval_receipt",
    "$.operational_window.completed_receipt_counts_as_approved_runtime_evidence",
    "$.source_summary.modules.player_principal_lifecycle.functions.ShooterGameMode.HandleNewPlayer.details.principal_id_logged",
    "$.source_summary.modules.player_principal_lifecycle.functions.ShooterGameMode.OnLogout.details.principal_id_logged",
)
ALLOWED_FORBIDDEN_LEAF_PATHS = (
    "$.schema",
    "$.operational_window.schema",
    "$.output_artifact_identity.artifact_kind",
    "$.output_artifact_identity.capture_id",
    "$.output_artifact_identity.evidence_pack_id",
    "$.operational_window.run_id",
    "$.operational_window.approval",
    "$.operational_window.manifest.path",
    "$.operational_window.copied_log.path",
    "$.operational_window.request_pack.path",
    "$.operational_window.observer_env.path",
    "$.operational_window.operator_approval_receipt.path",
    "$.operational_window.preflight.pre.path",
    "$.operational_window.preflight.post.path",
    "$.operational_window.posture.observer_exclusivity",
    "$.operational_window.posture.single_module_summary",
    "$.operational_window.completed_receipt_counts_as_approved_runtime_evidence",
    "$.source_summary.evidence.sources[0].path",
    "$.source_summary.modules.player_principal_lifecycle.diagnostic_lifecycle_property_fname_mismatch_summary.evidence_classification",
    "$.source_summary.modules.player_principal_lifecycle.diagnostic_lifecycle_property_fname_mismatch_target_summary.evidence_classification",
    "$.source_summary.modules.player_principal_lifecycle.player_principal_lifecycle_event_split_summary.evidence_classification",
    f"{STRICT_TRIPLET_CANDIDATE_SUMMARY_PATH}.schema",
    f"{STRICT_TRIPLET_CANDIDATE_SUMMARY_PATH}.status",
    f"{STRICT_TRIPLET_CANDIDATE_SUMMARY_PATH}.approval_authority",
    f"{STRICT_TRIPLET_CANDIDATE_SUMMARY_PATH}.strict_rejected_start_expected_shape",
    f"{STRICT_TRIPLET_CANDIDATE_SUMMARY_PATH}.next_action",
    f"{STRICT_TRIPLET_CANDIDATE_SUMMARY_PATH}.next_checker",
    f"{STRICT_TRIPLET_CANDIDATE_SUMMARY_PATH}.next_builder",
    f"{STRICT_TRIPLET_CANDIDATE_SUMMARY_PATH}.non_claim",
    "$.source_summary.modules.player_principal_lifecycle.functions.ShooterGameMode.HandleNewPlayer.details.principal_id_logged",
    "$.source_summary.modules.player_principal_lifecycle.functions.ShooterGameMode.OnLogout.details.principal_id_logged",
)
EXPECTED_OPERATIONAL_WINDOW_APPROVALS = frozenset(
    (EXPECTED_APPROVAL, STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT)
)
ALLOWED_FORBIDDEN_KEY_NAMES = frozenset(
    (
        "accepted_lifecycle_role_set_present",
        "accepted_or_rejected_observer_lines_present",
        "can_satisfy_complete_triplet",
        "can_satisfy_lifecycle_role",
        "complete_accepted_lifecycle_role_triplet_present",
        "complete_lifecycle_event_triplet_candidate_present",
        "player_principal_lifecycle",
        "principal_action",
        "principal_claim",
        "principal_generation_logged",
        "principal_id_logged",
    )
)
DIAGNOSTIC_PROPERTY_FNAME_CHAIN_METADATA_PATH = (
    f"$.source_summary.modules.{MODULE}.diagnostic_candidate_property_fname_chain_metadata"
)
DIAGNOSTIC_PROPERTY_FNAME_CHAIN_ALLOWED_KEY_PATH_RE = re.compile(
    r"^"
    + re.escape(DIAGNOSTIC_PROPERTY_FNAME_CHAIN_METADATA_PATH)
    + r"(?:$|\.entries\[\d+\]\.fname_indices)$"
)
DIAGNOSTIC_PROPERTY_FNAME_CHAIN_ALLOWED_LEAF_PATH_RE = re.compile(
    r"^(?:"
    + re.escape(DIAGNOSTIC_PROPERTY_FNAME_CHAIN_METADATA_PATH)
    + r"(?:\.evidence_classification|\.entries\[\d+\]\.(?:field|evidence_classification)|"
    r"\.entries\[\d+\]\.source_keys\[\d+\])|"
    + re.escape(f"$.source_summary.modules.{MODULE}.diagnostic_candidate_guardrails")
    + r"\[\d+\]\.code)$"
)
STRICT_TRIPLET_CANDIDATE_SUMMARY_ALLOWED_LEAF_PATH_RE = re.compile(
    r"^"
    + re.escape(STRICT_TRIPLET_CANDIDATE_SUMMARY_PATH)
    + r"\.(?:required_event_roles|accepted_event_roles|missing_event_roles|quality_blockers)\[\d+\]$"
)
SOURCE_SUMMARY_LIFECYCLE_METADATA_POSITIVE_KEYS = frozenset(
    (
        "accepted_lifecycle_role_set_present",
        "accepted_or_rejected_observer_lines_present",
        "complete_accepted_lifecycle_role_triplet_present",
    )
)
NON_APPROVED_RUNTIME_EVIDENCE_SCHEMA_BLOCKERS = {
    SUMMARY_SCHEMA: "runtime_observer_summary_is_not_approved_runtime_evidence",
    SHAPE_FIXTURE_SCHEMA: "synthetic_shape_fixture_is_not_approved_runtime_evidence",
    PRINCIPAL_START_END_EVIDENCE_CHECK_SCHEMA: "start_end_only_evidence_is_not_approved_runtime_evidence",
    MULTI_SURFACE_BETA_CAPTURE_PLAN_SCHEMA: "multi_surface_beta_capture_plan_is_not_approved_runtime_evidence",
    MULTI_SURFACE_BETA_CAPTURE_PACK_SCHEMA: "multi_surface_beta_capture_pack_is_not_approved_runtime_evidence",
    MULTI_SURFACE_BETA_CAPTURE_CHECKER_MATRIX_SCHEMA: (
        "multi_surface_beta_capture_checker_matrix_is_not_approved_runtime_evidence"
    ),
    MULTI_SURFACE_BETA_CAPTURE_NON_CLAIM_MANIFEST_SCHEMA: (
        "multi_surface_beta_capture_non_claim_manifest_is_not_approved_runtime_evidence"
    ),
    EXPECTED_REQUEST_SCHEMA: "window_request_manifest_is_not_approved_runtime_evidence",
    EXPECTED_PREFLIGHT_SCHEMA: "preflight_manifest_is_not_approved_runtime_evidence",
    WINDOW_CHECK_SCHEMA: "window_manifest_check_is_not_approved_runtime_evidence",
    EXPECTED_OPERATOR_APPROVAL_RECEIPT_SCHEMA: "operator_approval_receipt_is_not_approved_runtime_evidence",
    NOTICE_PREP_SCHEMA: "notice_prep_manifest_is_not_approved_runtime_evidence",
    CLOSURE_REQUEST_SCHEMA: "closure_request_manifest_is_not_approved_runtime_evidence",
    PASSIVE_SNAPSHOT_SCHEMA: "passive_snapshot_manifest_is_not_approved_runtime_evidence",
    PASSIVE_SNAPSHOT_DIFF_SCHEMA: "passive_snapshot_diff_is_not_approved_runtime_evidence",
    PASSIVE_SNAPSHOT_LATEST_SCHEMA: "passive_snapshot_latest_is_not_approved_runtime_evidence",
    PASSIVE_SNAPSHOT_ROLLUP_SCHEMA: "passive_snapshot_rollup_is_not_approved_runtime_evidence",
    PASSIVE_OBSERVER_EVENT_TRIAGE_SCHEMA: "passive_event_triage_is_not_approved_runtime_evidence",
    PASSIVE_ACTIVITY_TRIAGE_SCHEMA: "passive_activity_triage_is_not_approved_runtime_evidence",
    PASSIVE_ACTIONABILITY_SCHEMA: "passive_actionability_is_not_approved_runtime_evidence",
    PASSIVE_TARGET_TRIPLET_SCHEMA: "passive_target_triplet_is_not_approved_runtime_evidence",
    PASSIVE_SERVER_ACTIVITY_SCHEMA: "passive_server_activity_is_not_approved_runtime_evidence",
    PASSIVE_MONITOR_ONLY_SUMMARY_SCHEMA: "passive_monitor_only_summary_is_not_approved_runtime_evidence",
    PASSIVE_EXTENDED_MONITOR_TRIAGE_SCHEMA: "passive_extended_monitor_triage_is_not_approved_runtime_evidence",
    PASSIVE_WAIT_SCHEMA: "passive_wait_is_not_approved_runtime_evidence",
    PUBLIC_REACHABILITY_SCHEMA: "public_reachability_manifest_is_not_approved_runtime_evidence",
    SDK_STATUS_REPORT_SCHEMA: "sdk_status_report_is_not_approved_runtime_evidence",
    SDK_STATUS_SIDE_LANE_SUMMARY_SCHEMA: "sdk_status_side_lane_summary_is_not_approved_runtime_evidence",
    SDK_STATUS_CRITICAL_PATH_SUMMARY_SCHEMA: "sdk_status_critical_path_summary_is_not_approved_runtime_evidence",
    POST_EVIDENCE_P0_LOCK_SIMULATION_SCHEMA: "post_evidence_p0_lock_simulation_is_not_approved_runtime_evidence",
    RUNTIME_WINDOW_PLAN_SCHEMA: "next_action_plan_is_not_approved_runtime_evidence",
    RUNTIME_WINDOW_EXECUTION_SCHEMA: "runtime_window_execution_is_not_approved_runtime_evidence",
    RUNTIME_WINDOW_POST_WINDOW_STATE_SCHEMA: "runtime_window_post_window_state_is_not_approved_runtime_evidence",
    RUNTIME_EVIDENCE_STATUS_SCHEMA: "runtime_evidence_status_report_is_not_approved_runtime_evidence",
    PLANNING_BLOCKER_SMOKE_SCHEMA: "planning_blocker_smoke_is_not_approved_runtime_evidence",
    PLANNING_SOURCE_MANIFESTS_BUILD_REPORT_SCHEMA: (
        "planning_source_manifests_build_report_is_not_approved_runtime_evidence"
    ),
    LIFECYCLE_ANCHOR_CANDIDATES_SCHEMA: "lifecycle_anchor_candidates_is_not_approved_runtime_evidence",
    PRINCIPAL_INVALIDATION_POLICY_SCHEMA: "principal_invalidation_policy_is_not_approved_runtime_evidence",
    FIRST_EVIDENCE_SCHEMA: "first_evidence_planning_artifact_is_not_approved_runtime_evidence",
    COMMAND_PERMISSION_ROUTE_GATE_CHECK_SCHEMA: "command_permission_route_gate_check_is_not_approved_runtime_evidence",
    COMMAND_PERMISSION_ROUTE_BOUND_IDENTITY_SOURCE_FORWARDING_SCHEMA: (
        "command_permission_route_bound_identity_source_forwarding_is_not_approved_runtime_evidence"
    ),
    COMMAND_PERMISSION_ROUTE_SIMULATION_SCHEMA: "command_permission_route_simulation_is_not_approved_runtime_evidence",
    COMMAND_PERMISSION_ROUTE_POST_EVIDENCE_IDENTITY_LOCK_SCHEMA: (
        "command_permission_route_post_evidence_identity_lock_is_not_approved_runtime_evidence"
    ),
    COMMAND_PERMISSION_ROUTE_SNAPSHOT_SCHEMA: "command_permission_route_snapshot_is_not_approved_runtime_evidence",
    PUBLIC_SDK_SURFACES_SCHEMA: "public_sdk_surfaces_is_not_approved_runtime_evidence",
    PUBLIC_SDK_V1_COMPLETION_READY_SCHEMA_ID_SCHEMA: (
        "public_sdk_completion_ready_schema_id_is_not_approved_runtime_evidence"
    ),
    PUBLIC_SDK_V1_COMPLETION_CHECK_SCHEMA: "public_sdk_completion_check_is_not_approved_runtime_evidence",
    PUBLIC_SDK_V1_COMPLETION_SUMMARY_SCHEMA: "public_sdk_completion_summary_is_not_approved_runtime_evidence",
    PUBLIC_SDK_V1_FASTEST_NEXT_UNBLOCK_SCHEMA: "public_sdk_fastest_next_unblock_is_not_approved_runtime_evidence",
    PUBLIC_SDK_V1_PROGRESS_NORMALIZATION_TRACE_SCHEMA: (
        "public_sdk_progress_normalization_trace_is_not_approved_runtime_evidence"
    ),
    PUBLIC_SDK_V1_APPROVED_IN_GAME_EVIDENCE_STATUS_SCHEMA: (
        "public_sdk_approved_in_game_evidence_status_is_not_approved_runtime_evidence"
    ),
    APPROVED_IN_GAME_EVIDENCE_STATUS_SCHEMA: "approved_in_game_evidence_status_is_not_approved_runtime_evidence",
    PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISIONS_SCHEMA: "contract_review_artifact_is_not_approved_runtime_evidence",
    PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_SCHEMA: (
        "contract_review_artifact_is_not_approved_runtime_evidence"
    ),
    PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_CHECK_SCHEMA: (
        "contract_review_artifact_is_not_approved_runtime_evidence"
    ),
    PLAYER_IDENTITY_PUBLIC_CONTRACT_GAP_REPORT_SCHEMA: (
        "contract_review_artifact_is_not_approved_runtime_evidence"
    ),
    PLAYER_IDENTITY_PUBLIC_CONTRACT_READINESS_CHECK_SCHEMA: (
        "contract_review_artifact_is_not_approved_runtime_evidence"
    ),
    PLAYER_NOTICE_ACTION_SCHEMA: "player_notice_action_is_not_approved_runtime_evidence",
    GENERIC_PLAYER_NOTICE_ACTION_SCHEMA: "player_notice_action_is_not_approved_runtime_evidence",
    GUARDED_BETA_NOTICE_ACTION_SCHEMA: "guarded_beta_notice_action_is_not_approved_runtime_evidence",
    BETA_NOTICE_AUTHORITY_BOUNDARY_SCHEMA: "beta_notice_authority_boundary_is_not_approved_runtime_evidence",
    DISCORD_BETA_BRIDGE_ACTIVE_NOTICE_SCHEMA: "discord_bridge_state_is_not_approved_runtime_evidence",
    DISCORD_BETA_BRIDGE_BOT_NOTICE_SCHEMA: "discord_bridge_state_is_not_approved_runtime_evidence",
    DISCORD_BETA_BRIDGE_DRY_RUN_RECEIPT_SCHEMA: "discord_bridge_state_is_not_approved_runtime_evidence",
    DISCORD_BETA_BRIDGE_EVENT_SUMMARY_SCHEMA: "discord_bridge_state_is_not_approved_runtime_evidence",
    DISCORD_BETA_BRIDGE_TESTER_STATUS_SUMMARY_SCHEMA: "discord_bridge_state_is_not_approved_runtime_evidence",
    PLAYER_PRESENCE_SAFETY_SCHEMA: "player_presence_safety_is_not_approved_runtime_evidence",
    ACTIVATION_PRECONDITIONS_SCHEMA: "activation_preconditions_is_not_approved_runtime_evidence",
    WINDOW_REQUEST_CHECK_SCHEMA: "window_request_check_is_not_approved_runtime_evidence",
    REPORT_SCHEMA: "approved_evidence_check_report_is_not_approved_runtime_evidence",
    BUNDLE_PREFLIGHT_SCHEMA: "bundle_preflight_is_not_approved_runtime_evidence",
    BUNDLE_REPORT_SCHEMA: "bundle_report_is_not_approved_runtime_evidence",
    SCOPED_RELEASE_STATEMENT_OUTCOMES_SCHEMA: "scoped_release_statement_is_not_approved_runtime_evidence",
    INSTALLED_SDK_PACKAGE_SHAPE_SCHEMA: "installed_sdk_package_shape_is_not_approved_runtime_evidence",
    INTERNAL_MODULE_READINESS_SCHEMA: "internal_module_readiness_is_not_approved_runtime_evidence",
    PASSIVE_MONITOR_LOG_METADATA_SCHEMA: "passive_monitor_metadata_is_not_approved_runtime_evidence",
    PASSIVE_ORGANIC_PLAYER_DETECTION_SCHEMA: "passive_organic_player_detection_is_not_approved_runtime_evidence",
    READY_LOG_COPY_SCHEMA: "ready_log_copy_is_not_approved_runtime_evidence",
}
NON_EVIDENCE_SIDECAR_SCHEMA_BLOCKERS = {
    SCHEMA: "approved_runtime_manifest_sidecar_not_checked_bundle_output",
    SUMMARY_SCHEMA: "runtime_observer_summary_sidecar_not_approved_runtime_evidence",
    SHAPE_FIXTURE_SCHEMA: "synthetic_shape_fixture_sidecar_not_approved_runtime_evidence",
    PRINCIPAL_START_END_EVIDENCE_CHECK_SCHEMA: "start_end_only_evidence_sidecar_not_approved_runtime_evidence",
    MULTI_SURFACE_BETA_CAPTURE_PLAN_SCHEMA: "multi_surface_beta_capture_plan_sidecar_not_approved_runtime_evidence",
    MULTI_SURFACE_BETA_CAPTURE_PACK_SCHEMA: "multi_surface_beta_capture_pack_sidecar_not_approved_runtime_evidence",
    MULTI_SURFACE_BETA_CAPTURE_CHECKER_MATRIX_SCHEMA: (
        "multi_surface_beta_capture_checker_matrix_sidecar_not_approved_runtime_evidence"
    ),
    MULTI_SURFACE_BETA_CAPTURE_NON_CLAIM_MANIFEST_SCHEMA: (
        "multi_surface_beta_capture_non_claim_manifest_sidecar_not_approved_runtime_evidence"
    ),
    NOTICE_PREP_SCHEMA: "notice_prep_sidecar_not_approved_runtime_evidence",
    CLOSURE_REQUEST_SCHEMA: "closure_request_sidecar_not_approved_runtime_evidence",
    PASSIVE_SNAPSHOT_SCHEMA: "passive_snapshot_sidecar_not_approved_runtime_evidence",
    PASSIVE_SNAPSHOT_DIFF_SCHEMA: "passive_snapshot_diff_sidecar_not_approved_runtime_evidence",
    PASSIVE_SNAPSHOT_LATEST_SCHEMA: "passive_snapshot_latest_sidecar_not_approved_runtime_evidence",
    PASSIVE_SNAPSHOT_ROLLUP_SCHEMA: "passive_snapshot_rollup_sidecar_not_approved_runtime_evidence",
    PASSIVE_OBSERVER_EVENT_TRIAGE_SCHEMA: "passive_event_triage_sidecar_not_approved_runtime_evidence",
    PASSIVE_ACTIVITY_TRIAGE_SCHEMA: "passive_activity_triage_sidecar_not_approved_runtime_evidence",
    PASSIVE_ACTIONABILITY_SCHEMA: "passive_actionability_sidecar_not_approved_runtime_evidence",
    PASSIVE_TARGET_TRIPLET_SCHEMA: "passive_target_triplet_sidecar_not_approved_runtime_evidence",
    PASSIVE_SERVER_ACTIVITY_SCHEMA: "passive_server_activity_sidecar_not_approved_runtime_evidence",
    PASSIVE_MONITOR_ONLY_SUMMARY_SCHEMA: "passive_monitor_only_summary_sidecar_not_approved_runtime_evidence",
    PASSIVE_EXTENDED_MONITOR_TRIAGE_SCHEMA: "passive_extended_monitor_triage_sidecar_not_approved_runtime_evidence",
    PASSIVE_WAIT_SCHEMA: "passive_wait_sidecar_not_approved_runtime_evidence",
    PUBLIC_REACHABILITY_SCHEMA: "public_reachability_sidecar_not_approved_runtime_evidence",
    SDK_STATUS_REPORT_SCHEMA: "sdk_status_report_sidecar_not_approved_runtime_evidence",
    SDK_STATUS_SIDE_LANE_SUMMARY_SCHEMA: "sdk_status_side_lane_summary_sidecar_not_approved_runtime_evidence",
    SDK_STATUS_CRITICAL_PATH_SUMMARY_SCHEMA: "sdk_status_critical_path_summary_sidecar_not_approved_runtime_evidence",
    POST_EVIDENCE_P0_LOCK_SIMULATION_SCHEMA: "post_evidence_p0_lock_simulation_sidecar_not_approved_runtime_evidence",
    RUNTIME_WINDOW_PLAN_SCHEMA: "next_action_plan_sidecar_not_approved_runtime_evidence",
    RUNTIME_WINDOW_EXECUTION_SCHEMA: "runtime_window_execution_sidecar_not_approved_runtime_evidence",
    RUNTIME_WINDOW_POST_WINDOW_STATE_SCHEMA: "runtime_window_post_window_state_sidecar_not_approved_runtime_evidence",
    RUNTIME_EVIDENCE_STATUS_SCHEMA: "runtime_evidence_status_report_sidecar_not_approved_runtime_evidence",
    PLANNING_BLOCKER_SMOKE_SCHEMA: "planning_blocker_smoke_sidecar_not_approved_runtime_evidence",
    PLANNING_SOURCE_MANIFESTS_BUILD_REPORT_SCHEMA: (
        "planning_source_manifests_build_report_sidecar_not_approved_runtime_evidence"
    ),
    LIFECYCLE_ANCHOR_CANDIDATES_SCHEMA: "lifecycle_anchor_candidates_sidecar_not_approved_runtime_evidence",
    PRINCIPAL_INVALIDATION_POLICY_SCHEMA: "principal_invalidation_policy_sidecar_not_approved_runtime_evidence",
    FIRST_EVIDENCE_SCHEMA: "first_evidence_planning_artifact_sidecar_not_approved_runtime_evidence",
    COMMAND_PERMISSION_ROUTE_GATE_CHECK_SCHEMA: "command_permission_route_gate_check_sidecar_not_approved_runtime_evidence",
    COMMAND_PERMISSION_ROUTE_BOUND_IDENTITY_SOURCE_FORWARDING_SCHEMA: (
        "command_permission_route_bound_identity_source_forwarding_sidecar_not_approved_runtime_evidence"
    ),
    COMMAND_PERMISSION_ROUTE_SIMULATION_SCHEMA: "command_permission_route_simulation_sidecar_not_approved_runtime_evidence",
    COMMAND_PERMISSION_ROUTE_POST_EVIDENCE_IDENTITY_LOCK_SCHEMA: (
        "command_permission_route_post_evidence_identity_lock_sidecar_not_approved_runtime_evidence"
    ),
    COMMAND_PERMISSION_ROUTE_SNAPSHOT_SCHEMA: "command_permission_route_snapshot_sidecar_not_approved_runtime_evidence",
    PUBLIC_SDK_SURFACES_SCHEMA: "public_sdk_surfaces_sidecar_not_approved_runtime_evidence",
    PUBLIC_SDK_V1_COMPLETION_READY_SCHEMA_ID_SCHEMA: (
        "public_sdk_completion_ready_schema_id_sidecar_not_approved_runtime_evidence"
    ),
    PUBLIC_SDK_V1_COMPLETION_CHECK_SCHEMA: "public_sdk_completion_check_sidecar_not_approved_runtime_evidence",
    PUBLIC_SDK_V1_COMPLETION_SUMMARY_SCHEMA: "public_sdk_completion_summary_sidecar_not_approved_runtime_evidence",
    PUBLIC_SDK_V1_FASTEST_NEXT_UNBLOCK_SCHEMA: (
        "public_sdk_fastest_next_unblock_sidecar_not_approved_runtime_evidence"
    ),
    PUBLIC_SDK_V1_PROGRESS_NORMALIZATION_TRACE_SCHEMA: (
        "public_sdk_progress_normalization_trace_sidecar_not_approved_runtime_evidence"
    ),
    PUBLIC_SDK_V1_APPROVED_IN_GAME_EVIDENCE_STATUS_SCHEMA: (
        "public_sdk_approved_in_game_evidence_status_sidecar_not_approved_runtime_evidence"
    ),
    APPROVED_IN_GAME_EVIDENCE_STATUS_SCHEMA: (
        "approved_in_game_evidence_status_sidecar_not_approved_runtime_evidence"
    ),
    PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISIONS_SCHEMA: (
        "contract_review_artifact_sidecar_not_approved_runtime_evidence"
    ),
    PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_SCHEMA: (
        "contract_review_artifact_sidecar_not_approved_runtime_evidence"
    ),
    PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_CHECK_SCHEMA: (
        "contract_review_artifact_sidecar_not_approved_runtime_evidence"
    ),
    PLAYER_IDENTITY_PUBLIC_CONTRACT_GAP_REPORT_SCHEMA: (
        "contract_review_artifact_sidecar_not_approved_runtime_evidence"
    ),
    PLAYER_IDENTITY_PUBLIC_CONTRACT_READINESS_CHECK_SCHEMA: (
        "contract_review_artifact_sidecar_not_approved_runtime_evidence"
    ),
    PLAYER_NOTICE_ACTION_SCHEMA: "player_notice_action_sidecar_not_approved_runtime_evidence",
    GENERIC_PLAYER_NOTICE_ACTION_SCHEMA: "player_notice_action_sidecar_not_approved_runtime_evidence",
    GUARDED_BETA_NOTICE_ACTION_SCHEMA: "guarded_beta_notice_action_sidecar_not_approved_runtime_evidence",
    BETA_NOTICE_AUTHORITY_BOUNDARY_SCHEMA: "beta_notice_authority_boundary_sidecar_not_approved_runtime_evidence",
    DISCORD_BETA_BRIDGE_ACTIVE_NOTICE_SCHEMA: "discord_bridge_state_sidecar_not_approved_runtime_evidence",
    DISCORD_BETA_BRIDGE_BOT_NOTICE_SCHEMA: "discord_bridge_state_sidecar_not_approved_runtime_evidence",
    DISCORD_BETA_BRIDGE_DRY_RUN_RECEIPT_SCHEMA: "discord_bridge_state_sidecar_not_approved_runtime_evidence",
    DISCORD_BETA_BRIDGE_EVENT_SUMMARY_SCHEMA: "discord_bridge_state_sidecar_not_approved_runtime_evidence",
    DISCORD_BETA_BRIDGE_TESTER_STATUS_SUMMARY_SCHEMA: "discord_bridge_state_sidecar_not_approved_runtime_evidence",
    PLAYER_PRESENCE_SAFETY_SCHEMA: "player_presence_safety_sidecar_not_approved_runtime_evidence",
    ACTIVATION_PRECONDITIONS_SCHEMA: "activation_preconditions_sidecar_not_approved_runtime_evidence",
    WINDOW_REQUEST_CHECK_SCHEMA: "window_request_check_sidecar_not_approved_runtime_evidence",
    REPORT_SCHEMA: "approved_evidence_check_report_sidecar_not_approved_runtime_evidence",
    WINDOW_CHECK_SCHEMA: "window_manifest_check_report_sidecar_not_approved_runtime_evidence",
    BUNDLE_PREFLIGHT_SCHEMA: "bundle_preflight_sidecar_not_approved_runtime_evidence",
    BUNDLE_REPORT_SCHEMA: "bundle_report_sidecar_not_approved_runtime_evidence",
    SCOPED_RELEASE_STATEMENT_OUTCOMES_SCHEMA: "scoped_release_statement_sidecar_not_approved_runtime_evidence",
    INSTALLED_SDK_PACKAGE_SHAPE_SCHEMA: "installed_sdk_package_shape_sidecar_not_approved_runtime_evidence",
    INTERNAL_MODULE_READINESS_SCHEMA: "internal_module_readiness_sidecar_not_approved_runtime_evidence",
    PASSIVE_MONITOR_LOG_METADATA_SCHEMA: "passive_monitor_metadata_sidecar_not_approved_runtime_evidence",
    PASSIVE_ORGANIC_PLAYER_DETECTION_SCHEMA: "passive_organic_player_detection_sidecar_not_approved_runtime_evidence",
    READY_LOG_COPY_SCHEMA: "ready_log_copy_sidecar_not_approved_runtime_evidence",
}
NON_APPROVED_RUNTIME_EVIDENCE_INPUT_PATH_NAME_BLOCKERS = {
    "manifest.json": "input_path_candidate_manifest_artifact_is_not_approved_runtime_evidence",
    "multi-surface-capture-plan.json": (
        "input_path_multi_surface_beta_capture_plan_artifact_is_not_approved_runtime_evidence"
    ),
    "checker-command-matrix.json": (
        "input_path_multi_surface_beta_capture_checker_matrix_artifact_is_not_approved_runtime_evidence"
    ),
    "non-claim-manifest.json": (
        "input_path_multi_surface_beta_capture_non_claim_manifest_artifact_is_not_approved_runtime_evidence"
    ),
}
NON_APPROVED_RUNTIME_EVIDENCE_SCHEMA_ALIAS_BLOCKERS = (
    (
        re.compile(
            r"(?:multi[._-]?surface(?:[._-]?(?:beta[._-]?capture|candidate[._-]?queue|"
            r"capture[._-]?(?:plan|pack|queue)|plan[._-]?queue))?|"
            r"beta[._-]?capture(?:[._-]?(?:plan|pack|queue|artifact|bundle))?)",
            re.IGNORECASE,
        ),
        "multi_surface_beta_capture_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:candidate[._-]?queue|candidate[._-]?(?:pack|artifact)[._-]?queue)", re.IGNORECASE),
        "candidate_queue_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:debug[._-]?capture|candidate[._-]?debug[._-]?capture|diagnostic[._-]?capture)", re.IGNORECASE),
        "debug_capture_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:(?:principal[._-])?(?:session[._-]?start(?:[._-]?and)?[._-]?end|"
            r"start[._-]?end)(?:[._-]?only)?(?:[._-]?(?:evidence|artifact|report|check|summary))?)",
            re.IGNORECASE,
        ),
        "start_end_only_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:(?:lifecycle|principal|session|event|triplet|role)[._-]?"
            r"(?:role[._-]?)?(?:alias|aliases|substitutes?|equivalents?|"
            r"replacements?|proxy|proxies|credit|credits)|"
            r"(?:session[._-]?start(?:[._-]?rejected)?|session[._-]?end)"
            r"[._-]?(?:role[._-]?)?(?:alias|substitutes?|equivalents?|"
            r"replacements?|credit|credits|counts?[._-]?as[._-]?role))",
            re.IGNORECASE,
        ),
        "role_alias_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:(?:check[._-]?join[._-]?in[._-]?progress|checkjoininprogress|check[._-]?join|checkjoin)"
            r"(?:[._-]?(?:1[._-]?0|bool[._-]?order|bool[._-]?tuple|copied[._-]?bool|"
            r"diagnostic|offline|candidate|accepted|acceptance|planning|readiness|evidence|"
            r"report|summary|artifact|source|copy))?|"
            r"(?:session[._-]?start[._-]?rejected|rejected[._-]?session[._-]?start)"
            r"(?:[._-]?(?:diagnostic|offline|candidate|accepted|acceptance|planning|"
            r"readiness|evidence|report|summary|artifact|source|check[._-]?join[._-]?in[._-]?progress))*)",
            re.IGNORECASE,
        ),
        "rejected_start_candidate_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:request[._-]?pack|pack[._-]?(?:ready|accepted|approved|evidence|sidecar))",
            re.IGNORECASE,
        ),
        "request_pack_or_approval_sidecar_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:standing[._-]?(?:launch[._-]?)?(?:authority|approval)|standing[._-]?approval|"
            r"(?:operator[._-]?)?approval[._-]?(?:authority|receipt|sidecar|artifact)|"
            r"operator[._-]?approval[._-]?(?:request|receipt)|"
            r"launch[._-]?authority[._-]?(?:receipt|artifact|status))",
            re.IGNORECASE,
        ),
        "approval_or_standing_authority_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:(?:copied|copied[._-]?log|copy|log[._-]?copy|ready[._-]?log[._-]?copy)"
            r"[._-]?(?:status|report|summary|artifact|bundle|evidence|source)?|"
            r"(?:copy|copied)[._-]?(?:status|report|artifact))",
            re.IGNORECASE,
        ),
        "copied_status_or_report_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:window[._-]?manifest|manifest[._-]?window|operational[._-]?window[._-]?manifest)",
            re.IGNORECASE,
        ),
        "window_manifest_alias_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:contract[._-]?review|public[._-]?contract|identity[._-]?public[._-]?contract|"
            r"player[._-]?identity[._-]?public[._-]?contract|reviewed[._-]?identity[._-]?"
            r"public[._-]?contract|identity[._-]?contract[._-]?(?:decision|record|review|gate)|"
            r"public[._-]?contract[._-]?(?:decision|decisions|record|readiness|gap|gate|review)|"
            r"decision[._-]?record[._-]?(?:contract|identity))",
            re.IGNORECASE,
        ),
        "contract_review_artifact_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:next[._-]?actions?|action[._-]?plan|runtime[._-]?window[._-]?"
            r"(?:plan|execution|post[._-]?window[._-]?state)|window[._-]?plan)",
            re.IGNORECASE,
        ),
        "next_action_plan_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:progress[._-]?normalization[._-]?trace|source[._-]?overclaim)", re.IGNORECASE),
        "progress_or_source_overclaim_trace_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:source[._-]?bound(?:[._-]?(?:planning|manifest|drift|verification|"
            r"lifecycle|anchor|evidence|committed[._-]?manifests?))?|"
            r"(?:planning[._-]?source|source[._-]?planning)(?:[._-]?"
            r"(?:manifests?|verification|report|build))*|"
            r"(?:fname|f[._-]?name|fname[._-]?index|name[._-]?index)[._-]?"
            r"(?:drift|mismatch)|"
            r"lifecycle[._-]?anchor[._-]?(?:candidates?|planning|manifest|evidence))",
            re.IGNORECASE,
        ),
        "source_bound_drift_manifest_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:route[._-]?status|status[._-]?snapshot)", re.IGNORECASE),
        "status_summary_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:passive|snapshot|watch[._-]?only|monitor[._-]?tick|triplet)", re.IGNORECASE),
        "passive_or_triplet_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:notice|beta[._-]?notice|discord)", re.IGNORECASE),
        "notice_action_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:reachability|public[._-]?query|steam[._-]?query|gamedig)", re.IGNORECASE),
        "public_reachability_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:release[._-]?readiness|release[._-]?pass|scoped[._-]?release)", re.IGNORECASE),
        "release_readiness_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:package[._-]?shape|installed[._-]?sdk[._-]?package|package[._-]?install|"
            r"install[._-]?success|find[._-]?package|cmake[._-]?package)",
            re.IGNORECASE,
        ),
        "package_shape_or_install_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:handoff|compact[._-]?context|compact[._-]?checkpoint|checkpoint|"
            r"codex[._-]?cleanup|cleanup[._-]?report)",
            re.IGNORECASE,
        ),
        "handoff_or_cleanup_checkpoint_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:generated(?:[._-][a-z0-9]+)*[._-](?:artifact|bundle|manifest|sidecar)|"
            r"(?:artifact|bundle|manifest|sidecar)[._-]?generated)",
            re.IGNORECASE,
        ),
        "generated_artifact_or_bundle_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:status|report|summary|readiness[._-]?check|completion[._-]?check)", re.IGNORECASE),
        "status_summary_schema_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:histor|stale|prior|previous|old[._-]?window|candidate|closure|partial|incomplete|"
            r"bundle[._-]?preflight|preflight[._-]?only)",
            re.IGNORECASE,
        ),
        "historical_or_candidate_schema_is_not_approved_runtime_evidence",
    ),
)
NON_APPROVED_RUNTIME_EVIDENCE_INPUT_PATH_ALIAS_BLOCKERS = (
    (
        re.compile(
            r"(?:multi[._-]?surface(?:[._-]?(?:beta[._-]?capture|candidate[._-]?queue|"
            r"capture[._-]?(?:plan|pack|queue)|plan[._-]?queue))?|"
            r"beta[._-]?capture(?:[._-]?(?:plan|pack|queue|artifact|bundle))?)",
            re.IGNORECASE,
        ),
        "input_path_multi_surface_beta_capture_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:candidate[._-]?queue|candidate[._-]?(?:pack|artifact)[._-]?queue)", re.IGNORECASE),
        "input_path_candidate_queue_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:debug[._-]?capture|candidate[._-]?debug[._-]?capture|diagnostic[._-]?capture)", re.IGNORECASE),
        "input_path_debug_capture_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:(?:principal[._-])?(?:session[._-]?start(?:[._-]?and)?[._-]?end|"
            r"start[._-]?end)(?:[._-]?only)?(?:[._-]?(?:evidence|artifact|report|check|summary))?)",
            re.IGNORECASE,
        ),
        "input_path_start_end_only_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:(?:lifecycle|principal|session|event|triplet|role)[._-]?"
            r"(?:role[._-]?)?(?:alias|aliases|substitutes?|equivalents?|"
            r"replacements?|proxy|proxies|credit|credits)|"
            r"(?:session[._-]?start(?:[._-]?rejected)?|session[._-]?end)"
            r"[._-]?(?:role[._-]?)?(?:alias|substitutes?|equivalents?|"
            r"replacements?|credit|credits|counts?[._-]?as[._-]?role))",
            re.IGNORECASE,
        ),
        "input_path_role_alias_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:(?:check[._-]?join[._-]?in[._-]?progress|checkjoininprogress|check[._-]?join|checkjoin)"
            r"(?:[._-]?(?:1[._-]?0|bool[._-]?order|bool[._-]?tuple|copied[._-]?bool|"
            r"diagnostic|offline|candidate|accepted|acceptance|planning|readiness|evidence|"
            r"report|summary|artifact|source|copy))?|"
            r"(?:session[._-]?start[._-]?rejected|rejected[._-]?session[._-]?start)"
            r"(?:[._-]?(?:diagnostic|offline|candidate|accepted|acceptance|planning|"
            r"readiness|evidence|report|summary|artifact|source|check[._-]?join[._-]?in[._-]?progress))*)",
            re.IGNORECASE,
        ),
        "input_path_rejected_start_candidate_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:request[._-]?pack|pack[._-]?(?:ready|accepted|approved|evidence|sidecar))",
            re.IGNORECASE,
        ),
        "input_path_request_pack_or_approval_sidecar_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:standing[._-]?(?:launch[._-]?)?(?:authority|approval)|standing[._-]?approval|"
            r"(?:operator[._-]?)?approval[._-]?(?:authority|receipt|sidecar|artifact)|"
            r"operator[._-]?approval[._-]?(?:request|receipt)|"
            r"launch[._-]?authority[._-]?(?:receipt|artifact|status))",
            re.IGNORECASE,
        ),
        "input_path_approval_or_standing_authority_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:(?:copied|copied[._-]?log|copy|log[._-]?copy|ready[._-]?log[._-]?copy)"
            r"[._-]?(?:status|report|summary|artifact|bundle|evidence|source)?|"
            r"(?:copy|copied)[._-]?(?:status|report|artifact))",
            re.IGNORECASE,
        ),
        "input_path_copied_status_or_report_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:window[._-]?manifest|manifest[._-]?window|operational[._-]?window[._-]?manifest)",
            re.IGNORECASE,
        ),
        "input_path_window_manifest_alias_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:contract[._-]?review|public[._-]?contract|identity[._-]?public[._-]?contract|"
            r"player[._-]?identity[._-]?public[._-]?contract|reviewed[._-]?identity[._-]?"
            r"public[._-]?contract|identity[._-]?contract[._-]?(?:decision|record|review|gate)|"
            r"public[._-]?contract[._-]?(?:decision|decisions|record|readiness|gap|gate|review)|"
            r"decision[._-]?record[._-]?(?:contract|identity))",
            re.IGNORECASE,
        ),
        "input_path_contract_review_artifact_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:next[._-]?actions?|action[._-]?plan|runtime[._-]?window[._-]?"
            r"(?:plan|execution|post[._-]?window[._-]?state)|window[._-]?plan)",
            re.IGNORECASE,
        ),
        "input_path_next_action_plan_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:progress[._-]?normalization[._-]?trace|source[._-]?overclaim)", re.IGNORECASE),
        "input_path_progress_or_source_overclaim_trace_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:source[._-]?bound(?:[._-]?(?:planning|manifest|drift|verification|"
            r"lifecycle|anchor|evidence|committed[._-]?manifests?))?|"
            r"(?:planning[._-]?source|source[._-]?planning)(?:[._-]?"
            r"(?:manifests?|verification|report|build))*|"
            r"(?:fname|f[._-]?name|fname[._-]?index|name[._-]?index)[._-]?"
            r"(?:drift|mismatch)|"
            r"lifecycle[._-]?anchor[._-]?(?:candidates?|planning|manifest|evidence))",
            re.IGNORECASE,
        ),
        "input_path_source_bound_drift_manifest_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:route[._-]?status|status[._-]?snapshot)", re.IGNORECASE),
        "input_path_status_summary_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:passive|snapshot|watch[._-]?only|monitor[._-]?tick|triplet)", re.IGNORECASE),
        "input_path_passive_or_triplet_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:notice|beta[._-]?notice|discord)", re.IGNORECASE),
        "input_path_notice_action_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:reachability|public[._-]?query|steam[._-]?query|gamedig)", re.IGNORECASE),
        "input_path_public_reachability_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:release[._-]?readiness|release[._-]?pass|scoped[._-]?release)", re.IGNORECASE),
        "input_path_release_readiness_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:package[._-]?shape|installed[._-]?sdk[._-]?package|package[._-]?install|"
            r"install[._-]?success|find[._-]?package|cmake[._-]?package)",
            re.IGNORECASE,
        ),
        "input_path_package_shape_or_install_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:handoff|compact[._-]?context|compact[._-]?checkpoint|checkpoint|"
            r"codex[._-]?cleanup|cleanup[._-]?report)",
            re.IGNORECASE,
        ),
        "input_path_handoff_or_cleanup_checkpoint_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:generated(?:[._-][a-z0-9]+)*[._-](?:artifact|bundle|manifest|sidecar)|"
            r"(?:artifact|bundle|manifest|sidecar)[._-]?generated)",
            re.IGNORECASE,
        ),
        "input_path_generated_artifact_or_bundle_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:status|report|summary|readiness[._-]?check|completion[._-]?check)", re.IGNORECASE),
        "input_path_status_summary_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:histor|stale|prior|previous|old[._-]?window|candidate|closure|partial|incomplete|"
            r"bundle[._-]?preflight|preflight[._-]?only)",
            re.IGNORECASE,
        ),
        "input_path_historical_or_candidate_is_not_approved_runtime_evidence",
    ),
)


def is_allowed_non_claim_value(value: str) -> bool:
    return (
        value in REQUIRED_NON_CLAIMS
        or value in REQUIRED_OPERATIONAL_WINDOW_NON_CLAIMS
        or value in runtime_observer_analyzer.RUNTIME_OBSERVER_NON_CLAIMS
        or value == STRICT_TRIPLET_CANDIDATE_SUMMARY_NON_CLAIM
    )


def normalized_alias_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def expected_notice_path_for_user_policy(user_policy: Any) -> str | None:
    if user_policy == "operator_approved_beta_users":
        return APPROVED_BETA_NOTICE_PATH
    if user_policy == "no_regular_users":
        return "not_applicable"
    return None


def expected_player_notice_action_values(user_policy: Any) -> dict[str, Any] | None:
    expected_notice_path = expected_notice_path_for_user_policy(user_policy)
    if expected_notice_path is None:
        return None
    required = user_policy == "operator_approved_beta_users"
    return {
        "schema": PLAYER_NOTICE_ACTION_SCHEMA,
        "required": required,
        "notice_path": expected_notice_path,
        "approved_notice_path_must_be_named": required,
        "dry_run_required_before_send": required,
        "real_notice_send_required_before_activation": required,
        "send_performed_by_request_pack": False,
        "request_pack_authorizes_discord": False,
        "activation_allowed_before_notice_sent": not required,
        "evidence_required": "dry_run_output_and_send_confirmation_reference" if required else "not_applicable",
        "activation_blocker": (
            "approved_dry_run_checked_beta_testers_notice_sent"
            if required
            else "no_player_notice_required"
        ),
        "non_authorization": PLAYER_NOTICE_ACTION_NON_AUTHORIZATION,
    }


def validate_player_notice_action_contract(
    notice_action: Any,
    *,
    user_policy: Any,
    notice_path: Any,
    blockers: list[dict[str, Any]],
    label: str,
    reason_prefix: str,
) -> None:
    expected_notice_path = expected_notice_path_for_user_policy(user_policy)
    if expected_notice_path is not None and notice_path != expected_notice_path:
        add(
            blockers,
            f"{reason_prefix}_notice_path_mismatch",
            label,
            expected=expected_notice_path,
            actual=notice_path,
        )
    if not isinstance(notice_action, dict):
        add(blockers, f"{reason_prefix}_player_notice_action_missing", label)
        return
    expected_action = expected_player_notice_action_values(user_policy)
    if expected_action is None:
        if notice_action.get("schema") != PLAYER_NOTICE_ACTION_SCHEMA:
            add(blockers, f"{reason_prefix}_player_notice_action_schema_mismatch", label)
        return
    for key, expected in expected_action.items():
        if notice_action.get(key) != expected:
            add(
                blockers,
                f"{reason_prefix}_player_notice_action_{key}_mismatch",
                label,
                key_path=f"player_notice_action.{key}",
                expected=expected,
                actual=notice_action.get(key),
            )


def validate_player_presence_safety_contract(
    value: Any,
    *,
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
    label: str,
    reason_prefix: str,
) -> None:
    action_label = f"{label}.player_presence_safety"
    if not isinstance(value, dict):
        add(blockers, f"{reason_prefix}_player_presence_safety_missing", action_label, value=value)
        return

    if value.get("schema") != PLAYER_PRESENCE_SAFETY_SCHEMA:
        add(
            blockers,
            f"{reason_prefix}_player_presence_safety_schema_mismatch",
            f"{action_label}.schema",
            expected=PLAYER_PRESENCE_SAFETY_SCHEMA,
            actual=value.get("schema"),
        )
    try:
        expected = player_presence_safety(payload)
    except KeyError as exc:
        add(
            blockers,
            f"{reason_prefix}_player_presence_safety_source_field_missing",
            action_label,
            missing=str(exc),
        )
        return
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            add(
                blockers,
                f"{reason_prefix}_player_presence_safety_{key}_mismatch",
                f"{action_label}.{key}",
                expected=expected_value,
                actual=value.get(key),
            )
    unexpected = sorted(set(value) - set(expected))
    if unexpected:
        add(
            blockers,
            f"{reason_prefix}_player_presence_safety_keys_unexpected",
            action_label,
            unexpected=unexpected,
        )
    if value.get("non_authorization") != PLAYER_PRESENCE_SAFETY_NON_AUTHORIZATION:
        add(
            blockers,
            f"{reason_prefix}_player_presence_safety_non_authorization_mismatch",
            f"{action_label}.non_authorization",
            expected=PLAYER_PRESENCE_SAFETY_NON_AUTHORIZATION,
            actual=value.get("non_authorization"),
        )


def is_forbidden_readiness_alias(value: str) -> bool:
    return normalized_alias_token(value) in FORBIDDEN_READINESS_ALIAS_VALUES


def is_readiness_alias_context(trail: str) -> bool:
    return READINESS_ALIAS_CONTEXT_RE.search(trail) is not None


GENERIC_STATUS_ALIAS_KEYS = frozenset(
    (
        "classification",
        "claim",
        "label",
        "package",
        "readiness",
        "result",
        "state",
        "status",
        "support",
        "support_level",
        "tier",
    )
)
SPLIT_CLAIM_NAME_KEYS = frozenset(("alias", "claim", "field", "flag", "key", "name", "property"))
SPLIT_CLAIM_VALUE_KEYS = frozenset(
    (
        "allowed",
        "classification",
        "enabled",
        "label",
        "package",
        "ready",
        "result",
        "state",
        "status",
        "support",
        "support_level",
        "tier",
        "value",
    )
)
PROGRESS_ALIAS_DOMAIN_TOKENS = frozenset(
    (
        "claim",
        "complete",
        "completion",
        "dependency",
        "evidence",
        "identity",
        "p0",
        "package",
        "player",
        "principal",
        "public",
        "readiness",
        "route",
        "runtime",
        "sdk",
        "support",
        "v1",
    )
)
SUPPORT_PACKAGE_ALIAS_KEY_TOKENS = frozenset(
    ("classification", "label", "package", "support", "supported", "tier")
)
POSITIVE_ALIAS_VALUES = frozenset(
    (
        "1",
        "accepted",
        "allowed",
        "approved",
        "authorized",
        "complete",
        "completed",
        "enabled",
        "present",
        "promoted",
        "ready",
        "supported",
        "true",
        "unlocked",
        "yes",
    )
)
PATH_CONTEXT_ALIAS_DOMAIN_TOKENS = frozenset(
    (
        "artifact",
        "bundle",
        "evidence",
        "lifecycle",
        "observer",
        "player",
        "players",
        "principal",
        "proof",
        "runtime",
        "session",
        "sessions",
        "sidecar",
    )
)
PATH_CONTEXT_POSITIVE_LEAF_TOKENS = frozenset(
    (
        "accepted",
        "approved",
        "complete",
        "completed",
        "observed",
        "ready",
        "validated",
    )
)
PATH_CONTEXT_NON_EVIDENCE_TOKENS = frozenset(
    (
        "blocker",
        "blocked",
        "boundary",
        "candidate",
        "case",
        "cases",
        "count",
        "counts",
        "event",
        "events",
        "missing",
        "no",
        "non",
        "not",
        "only",
        "required",
        "requires",
    )
)
ACCEPTANCE_ALIAS_TOKENS = frozenset(("accepted", "acceptance", "approved", "approval", "validated", "validation"))
ACCEPTANCE_ALIAS_DOMAIN_TOKENS = frozenset(
    (
        "artifact",
        "bundle",
        "claim",
        "completion",
        "evidence",
        "manifest",
        "package",
        "public",
        "readiness",
        "report",
        "runtime",
        "sdk",
        "sidecar",
        "source",
        "status",
        "summary",
        "support",
        "v1",
    )
)
ACCEPTANCE_ALIAS_NEUTRAL_TOKENS = PATH_CONTEXT_NON_EVIDENCE_TOKENS | frozenset(
    (
        "dir",
        "directory",
        "file",
        "filename",
        "hash",
        "id",
        "name",
        "path",
        "relative",
        "rel",
        "sha",
        "sha256",
    )
)
ACCEPTANCE_ALIAS_ALLOWED_KEYS = frozenset(
    (
        "approved_runtime_evidence_present",
        "runtime_evidence_reviewed",
    )
)


def normalized_guardrail_alias_key(value: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    separated = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", separated)
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def source_overclaim_alias_key_is_forbidden(value: object) -> bool:
    normalized = normalized_guardrail_alias_key(value)
    return (
        "source_overclaim" in normalized
        or "source_overclaims" in normalized
        or "progress_normalization_trace" in normalized
    )


def guardrail_alias_tokens(value: object) -> set[str]:
    return {token for token in normalized_guardrail_alias_key(value).split("_") if token}


def guardrail_path_context_implies_positive_claim(key: object, value: Any, parent_trail: str) -> bool:
    if not guardrail_alias_value_is_positive(value):
        return False
    if (
        parent_trail == f"$.source_summary.modules.{MODULE}"
        and normalized_guardrail_alias_key(key) in SOURCE_SUMMARY_LIFECYCLE_METADATA_POSITIVE_KEYS
    ):
        return False
    key_tokens = guardrail_alias_tokens(key)
    if key_tokens & PATH_CONTEXT_NON_EVIDENCE_TOKENS:
        return False
    parent_tokens = guardrail_alias_tokens(parent_trail)
    if key_tokens == {"accepted"} and "functions" in parent_tokens and (
        {"source", "summary"}.issubset(parent_tokens) or "modules" in parent_tokens
    ):
        return False
    if "diagnostic" in parent_tokens and (
        {"source", "summary"}.issubset(parent_tokens) or "modules" in parent_tokens
    ):
        return False
    if not parent_tokens & PATH_CONTEXT_ALIAS_DOMAIN_TOKENS:
        return False
    if key_tokens & PATH_CONTEXT_POSITIVE_LEAF_TOKENS:
        return True
    return (
        normalized_guardrail_alias_key(key) in GENERIC_STATUS_ALIAS_KEYS
        or "status" in key_tokens
    )


def guardrail_alias_value_is_positive(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        normalized = normalized_guardrail_alias_key(value)
        if normalized in POSITIVE_ALIAS_VALUES:
            return True
        tokens = {token for token in normalized.split("_") if token}
        negative_tokens = {"blocked", "candidate", "missing", "none", "not", "only", "required", "requires"}
        if tokens & negative_tokens:
            return False
        positive_tokens = tokens & POSITIVE_ALIAS_VALUES
        domain_tokens = tokens & (
            PROGRESS_ALIAS_DOMAIN_TOKENS
            | SUPPORT_PACKAGE_ALIAS_KEY_TOKENS
            | {"approved", "contract", "evidence", "identity", "principal", "surface"}
        )
        return bool(positive_tokens and domain_tokens)
    if isinstance(value, dict):
        return any(guardrail_alias_value_is_positive(child) for child in value.values())
    if isinstance(value, list):
        return any(guardrail_alias_value_is_positive(child) for child in value)
    return False


def guardrail_alias_key_is_forbidden(value: object) -> bool:
    normalized = normalized_guardrail_alias_key(value)
    tokens = guardrail_alias_tokens(value)
    if guardrail_contract_review_alias_key_is_forbidden(value):
        return True
    if normalized == "is_ready":
        return True
    if normalized == "progress":
        return True
    if normalized in GENERIC_STATUS_ALIAS_KEYS and tokens & SUPPORT_PACKAGE_ALIAS_KEY_TOKENS:
        return True
    if tokens & SUPPORT_PACKAGE_ALIAS_KEY_TOKENS:
        domain_tokens = PROGRESS_ALIAS_DOMAIN_TOKENS | {
            "approved",
            "contract",
            "evidence",
            "identity",
            "principal",
            "public",
            "runtime",
            "sdk",
            "surface",
            "v1",
        }
        if tokens & domain_tokens:
            return True
    return "progress" in tokens and bool(tokens & PROGRESS_ALIAS_DOMAIN_TOKENS)


def guardrail_contract_review_alias_key_is_forbidden(value: object) -> bool:
    tokens = guardrail_alias_tokens(value)
    if "contract" not in tokens:
        return False
    return bool(tokens & {"decision", "gate", "identity", "public", "record", "review", "reviewed"})


def guardrail_acceptance_alias_key_is_forbidden(value: object, parent_trail: str = "") -> bool:
    normalized = normalized_guardrail_alias_key(value)
    if normalized in ACCEPTANCE_ALIAS_ALLOWED_KEYS:
        return False
    if (
        parent_trail == f"$.source_summary.modules.{MODULE}"
        and normalized in SOURCE_SUMMARY_LIFECYCLE_METADATA_POSITIVE_KEYS
    ):
        return False
    tokens = guardrail_alias_tokens(value)
    if not tokens or tokens & ACCEPTANCE_ALIAS_NEUTRAL_TOKENS:
        return False
    parent_tokens = guardrail_alias_tokens(parent_trail)
    if tokens == {"accepted"} and "functions" in parent_tokens and (
        {"source", "summary"}.issubset(parent_tokens) or "modules" in parent_tokens
    ):
        return False
    if tokens == {"accepted"}:
        return True
    return bool(tokens & ACCEPTANCE_ALIAS_TOKENS and tokens & ACCEPTANCE_ALIAS_DOMAIN_TOKENS)


def split_guardrail_alias_claim(value: dict[Any, Any]) -> bool:
    names = [
        child
        for key, child in value.items()
        if normalized_guardrail_alias_key(key) in SPLIT_CLAIM_NAME_KEYS
        and isinstance(child, str)
    ]
    values = [
        child
        for key, child in value.items()
        if normalized_guardrail_alias_key(key) in SPLIT_CLAIM_VALUE_KEYS
    ]
    if not names:
        return False
    positive_value_present = not values or any(guardrail_alias_value_is_positive(child) for child in values)
    if not positive_value_present:
        return False
    return any(
        guardrail_alias_key_is_forbidden(name)
        or contains_unnegated_positive_capability_claim(name)
        or is_forbidden_readiness_alias(name)
        for name in names
    )


LIFECYCLE_ROLE_ALIAS_MARKER_TOKENS = frozenset(
    (
        "alias",
        "aliases",
        "claim",
        "claims",
        "credit",
        "credits",
        "equivalent",
        "equivalents",
        "proxy",
        "proxies",
        "replace",
        "replaced",
        "replacement",
        "replacements",
        "replaces",
        "satisfied",
        "satisfies",
        "satisfy",
        "substitute",
        "substitutes",
    )
)
LIFECYCLE_ROLE_ALIAS_COUNT_MARKER_TOKENS = frozenset(("counting", "counts"))
LIFECYCLE_ROLE_ALIAS_DOMAIN_TOKENS = frozenset(
    (
        "anchor",
        "anchors",
        "event",
        "events",
        "lifecycle",
        "role",
        "roles",
        "triplet",
    )
)
LIFECYCLE_ROLE_ALIAS_NEGATIVE_VALUES = frozenset(
    (
        "blocked",
        "candidate",
        "context_only",
        "false",
        "missing",
        "no",
        "non_evidence",
        "none",
        "not_applicable",
        "rejected",
        "required",
        "requires",
    )
)
LIFECYCLE_ROLE_ALIAS_ROLE_VALUES = frozenset(READY_LOG_COPY_REQUIRED_ROLES)


def lifecycle_role_alias_key_claims_role(value: object) -> bool:
    normalized = normalized_guardrail_alias_key(value)
    return any(role in normalized for role in LIFECYCLE_ROLE_ALIAS_ROLE_VALUES)


def lifecycle_role_alias_value_claims_role(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_guardrail_alias_key(value)
        return any(role in normalized for role in LIFECYCLE_ROLE_ALIAS_ROLE_VALUES)
    if isinstance(value, dict):
        return any(lifecycle_role_alias_value_claims_role(child) for child in value.values())
    if isinstance(value, list):
        return any(lifecycle_role_alias_value_claims_role(child) for child in value)
    return False


def lifecycle_role_alias_value_has_material(value: Any) -> bool:
    if value in (False, None, [], {}):
        return False
    if isinstance(value, str):
        normalized = normalized_guardrail_alias_key(value)
        return normalized not in LIFECYCLE_ROLE_ALIAS_NEGATIVE_VALUES
    if isinstance(value, dict):
        return any(lifecycle_role_alias_value_has_material(child) for child in value.values())
    if isinstance(value, list):
        return any(lifecycle_role_alias_value_has_material(child) for child in value)
    return True


def lifecycle_role_alias_claim_is_forbidden(key: object, value: Any) -> bool:
    tokens = guardrail_alias_tokens(key)
    count_as_claim = bool(
        tokens & LIFECYCLE_ROLE_ALIAS_COUNT_MARKER_TOKENS
        and "as" in tokens
        and lifecycle_role_alias_value_has_material(value)
        and (
            tokens & LIFECYCLE_ROLE_ALIAS_DOMAIN_TOKENS
            or lifecycle_role_alias_key_claims_role(key)
            or lifecycle_role_alias_value_claims_role(value)
        )
    )
    if count_as_claim:
        return True
    if not tokens & LIFECYCLE_ROLE_ALIAS_MARKER_TOKENS:
        return False
    if lifecycle_role_alias_value_claims_role(value):
        return True
    key_claims_role = lifecycle_role_alias_key_claims_role(key)
    if key_claims_role and lifecycle_role_alias_value_has_material(value):
        return True
    if (
        tokens & LIFECYCLE_ROLE_ALIAS_DOMAIN_TOKENS
        and lifecycle_role_alias_value_has_material(value)
    ):
        return True
    return False


def find_lifecycle_role_alias_claim(value: Any, trail: str = "$") -> tuple[str, str] | None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if lifecycle_role_alias_claim_is_forbidden(key, child):
                return str(key), child_trail
            found = find_lifecycle_role_alias_claim(child, child_trail)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_lifecycle_role_alias_claim(child, f"{trail}[{index}]")
            if found is not None:
                return found
    return None


def validate_approved_intake_classification(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    expected_fields = {
        "artifact_status": APPROVED_RUNTIME_EVIDENCE_ARTIFACT_STATUS,
        "readiness_classification": APPROVED_RUNTIME_EVIDENCE_CLASSIFICATION,
    }
    for key, expected in expected_fields.items():
        value = payload.get(key)
        label = f"$.{key}"
        if value != expected:
            add(blockers, f"{key}_mismatch", label, expected=expected, actual=value)
        if isinstance(value, str) and is_forbidden_readiness_alias(value):
            add(
                blockers,
                "approved_evidence_intake_alias_not_allowed",
                label,
                expected=APPROVED_RUNTIME_EVIDENCE_CLASSIFICATION,
                actual=value,
            )
NEGATIVE_CONTEXT_TOKENS = (
    "blocker",
    "non_evidence",
    "non_claim",
    "privacy_boundary",
    "redacted",
)


@dataclass
class Validation:
    blockers: list[dict[str, Any]]
    observed_runtime_cases: list[str]
    consumer_cases: list[str]
    strict_rejected_start_diagnostics: dict[str, Any]
    strict_lifecycle_triplet_selection: dict[str, Any]
    session_end_missing_correlation_diagnostics: dict[str, Any] | None
    lifecycle_correlation_proof: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Approved runtime lifecycle evidence manifest.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    parser.add_argument("--promote", action="store_true", help="Fail closed for public promotion checks.")
    parser.add_argument("--public-readiness", action="store_true", help="Fail closed for public SDK readiness checks.")
    parser.add_argument("--runtime-readiness", action="store_true", help="Fail closed for runtime readiness checks.")
    return parser.parse_args()


def mode(args: argparse.Namespace) -> str:
    requested = [
        name
        for name, enabled in (
            ("promote", args.promote),
            ("public_readiness", args.public_readiness),
            ("runtime_readiness", args.runtime_readiness),
        )
        if enabled
    ]
    if len(requested) > 1:
        raise SystemExit("--promote, --public-readiness, and --runtime-readiness are mutually exclusive")
    return requested[0] if requested else "consume"


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def ready_log_copy_allowed_positive_trail(trail: str) -> bool:
    if trail in {
        "$.status",
        "$.ready_to_copy",
        "$.copy_readiness",
        "$.copied",
        "$.execute_requested",
        "$.allow_live_log_read",
        "$.allow_evidence_dir_write",
        "$.overwrite",
        "$.source_log_safety.accepted",
        "$.analysis.observer_enabled",
        "$.analysis.binary_sha256_match",
        "$.analysis.observer_enable_in_fresh_window",
        "$.analysis.ready_to_copy",
        "$.analysis.copy_readiness",
        "$.analysis.exact_copied_runtime_triplet.accepted",
    }:
        return True
    if trail.startswith("$.analysis.accepted_role_events.") and trail.endswith(
        (".status_proof_ok", ".inside_fresh_window", ".approved_copy_shape_ok")
    ):
        return True
    if trail.startswith("$.analysis.accepted_lifecycle_events[") and trail.endswith(".inside_fresh_window"):
        return True
    if trail.startswith("$.analysis.observer_enable_lines[") and trail.endswith(".inside_fresh_window"):
        return True
    return False


def validate_ready_log_copy_no_evidence_overclaims(
    value: Any,
    label: str,
    blockers: list[dict[str, Any]],
    *,
    reason_prefix: str,
    trail: str = "$",
) -> None:
    false_keys = {
        normalized_guardrail_alias_key(key)
        for key in (READY_LOG_COPY_REQUIRED_FALSE_KEYS | FORBIDDEN_POSITIVE_FLAG_KEYS)
    }
    if isinstance(value, dict):
        if trail != "$" and value.get("schema") == SCHEMA:
            add(
                blockers,
                f"{reason_prefix}_nested_approved_runtime_manifest_schema",
                label,
                key_path=f"{trail}.schema",
                schema=SCHEMA,
            )
        if split_guardrail_alias_claim(value):
            add(
                blockers,
                f"{reason_prefix}_authorization_or_readiness_key_overclaim",
                label,
                key_path=trail,
                actual=value,
            )
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            key_name = normalized_guardrail_alias_key(key)
            allowed_positive = ready_log_copy_allowed_positive_trail(child_trail)
            if source_overclaim_alias_key_is_forbidden(key):
                add(
                    blockers,
                    f"{reason_prefix}_source_overclaim_alias_is_not_approved_runtime_evidence",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            if lifecycle_role_alias_claim_is_forbidden(key, child):
                add(
                    blockers,
                    f"{reason_prefix}_lifecycle_role_alias_is_not_approved_runtime_evidence",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            if key_name in false_keys and child is not False:
                add(
                    blockers,
                    f"{reason_prefix}_readiness_flag_overclaim",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            if key in ("public_capability_bits_now", "public_callback_abi_now") and child != []:
                add(
                    blockers,
                    f"{reason_prefix}_public_surface_overclaim",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            if not allowed_positive:
                if (
                    child not in (False, None, [], {})
                    and contains_unnegated_positive_capability_claim(str(key))
                ):
                    add(
                        blockers,
                        f"{reason_prefix}_authorization_or_readiness_key_overclaim",
                        label,
                        key_path=child_trail,
                        actual=child,
                    )
                if guardrail_alias_key_is_forbidden(key) and guardrail_alias_value_is_positive(child):
                    add(
                        blockers,
                        f"{reason_prefix}_authorization_or_readiness_key_overclaim",
                        label,
                        key_path=child_trail,
                        actual=child,
                    )
                if guardrail_acceptance_alias_key_is_forbidden(key, trail) and guardrail_alias_value_is_positive(child):
                    add(
                        blockers,
                        f"{reason_prefix}_authorization_or_readiness_key_overclaim",
                        label,
                        key_path=child_trail,
                        actual=child,
                    )
                if guardrail_path_context_implies_positive_claim(key, child, trail):
                    add(
                        blockers,
                        f"{reason_prefix}_authorization_or_readiness_key_overclaim",
                        label,
                        key_path=child_trail,
                        actual=child,
                    )
                if (
                    normalized_guardrail_alias_key(key) in GENERIC_STATUS_ALIAS_KEYS
                    and guardrail_alias_value_is_positive(child)
                ):
                    add(
                        blockers,
                        f"{reason_prefix}_authorization_or_readiness_key_overclaim",
                        label,
                        key_path=child_trail,
                        actual=child,
                    )
            validate_ready_log_copy_no_evidence_overclaims(
                child,
                label,
                blockers,
                reason_prefix=reason_prefix,
                trail=child_trail,
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_ready_log_copy_no_evidence_overclaims(
                child,
                label,
                blockers,
                reason_prefix=reason_prefix,
                trail=f"{trail}[{index}]",
            )
    elif (
        isinstance(value, str)
        and not ready_log_copy_allowed_positive_trail(trail)
        and value not in READY_LOG_COPY_ALLOWED_NON_CLAIMS
        and value not in ALLOWED_POSITIVE_MATCH_NON_CLAIMS
        and (
            contains_unnegated_positive_capability_claim(value)
            or (is_readiness_alias_context(trail) and is_forbidden_readiness_alias(value))
        )
    ):
        add(
            blockers,
            f"{reason_prefix}_forbidden_public_capability_or_readiness_claim",
            label,
            key_path=trail,
            value=value,
        )


def validate_ready_log_copy_fresh_window(
    payload: dict[str, Any],
    analysis: dict[str, Any],
    expected_copied_log: Path,
    label: str,
    blockers: list[dict[str, Any]],
    *,
    reason_prefix: str,
) -> dict[str, Any]:
    claims_copy_ready = (
        payload.get("ready_to_copy") is True
        or payload.get("copy_readiness") == "ready_complete_role_triplet"
        or payload.get("status") in {"copied", "dry_run_ready"}
    )
    state: dict[str, Any] = {
        "fresh_window": {},
        "accepted": False,
        "observer_enable_in_fresh_window": False,
        "accepted_lifecycle_event_count": 0,
        "historical_accepted_role_event_count": 0,
        "strict_lifecycle_triplet_selection": strict_lifecycle_triplet_selection([]),
    }
    start_text = payload.get("fresh_window_start_utc")
    end_text = payload.get("fresh_window_end_utc")
    if not isinstance(start_text, str) or UTC_TIMESTAMP_RE.fullmatch(start_text) is None:
        if claims_copy_ready:
            add(blockers, f"{reason_prefix}_fresh_window_start_utc_invalid", label, actual=start_text)
        start = None
    else:
        start = parse_utc_timestamp(start_text)
    if not isinstance(end_text, str) or UTC_TIMESTAMP_RE.fullmatch(end_text) is None:
        if claims_copy_ready:
            add(blockers, f"{reason_prefix}_fresh_window_end_utc_invalid", label, actual=end_text)
        end = None
    else:
        end = parse_utc_timestamp(end_text)
    if start is not None and end is not None and start >= end:
        if claims_copy_ready:
            add(blockers, f"{reason_prefix}_fresh_window_not_forward", label)

    analysis_fresh_window = analysis.get("fresh_window")
    if isinstance(analysis_fresh_window, dict):
        if analysis_fresh_window.get("start_utc") != start_text:
            if claims_copy_ready:
                add(
                    blockers,
                    f"{reason_prefix}_analysis_fresh_window_start_mismatch",
                    label,
                    expected=start_text,
                    actual=analysis_fresh_window.get("start_utc"),
                )
        if analysis_fresh_window.get("end_utc") != end_text:
            if claims_copy_ready:
                add(
                    blockers,
                    f"{reason_prefix}_analysis_fresh_window_end_mismatch",
                    label,
                    expected=end_text,
                    actual=analysis_fresh_window.get("end_utc"),
                )
    elif claims_copy_ready:
        add(blockers, f"{reason_prefix}_analysis_fresh_window_missing", label)

    state["fresh_window"] = {"start_utc": start_text, "end_utc": end_text}
    if start is None or end is None or start >= end:
        return state

    try:
        lines = expected_copied_log.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        if claims_copy_ready:
            add(blockers, f"{reason_prefix}_target_log_missing_for_fresh_window_check", label)
        return state
    except OSError as exc:
        if claims_copy_ready:
            add(blockers, f"{reason_prefix}_target_log_unreadable_for_fresh_window_check", label, error=str(exc))
        return state

    accepted_in_window_events: list[dict[str, Any]] = []
    historical_accepted_events: list[dict[str, Any]] = []
    observer_enable_in_fresh_window = False
    observer_enable_seen = False
    for line_number, line in enumerate(lines, start=1):
        if "PlayerPrincipalLifecycleObserver enabled " in line:
            observer_enable_seen = True
            inside_window, timestamp_prefix, timestamp_error = timestamp_inside_capture_window(line, start, end)
            if timestamp_error is not None and claims_copy_ready:
                add(
                    blockers,
                    f"{reason_prefix}_observer_enable_timestamp_not_fresh_window_utc",
                    label,
                    line=line_number,
                    timestamp_prefix=timestamp_prefix,
                    timestamp_error=timestamp_error,
                )
            elif inside_window:
                observer_enable_in_fresh_window = True

        match = LIFECYCLE_EVENT_LINE_RE.search(line)
        if match is None:
            continue
        role = match.group("role")
        event_case = copied_log_lifecycle_event_case(line)
        full_shape_mismatches = copied_log_lifecycle_event_full_shape_mismatches(line)
        event_shape_allowed = (
            event_case is not None
            and freeze_case(event_case) in REQUIRED_OBSERVED_EVENT_CASE_SET
            and not full_shape_mismatches
        )
        values = dict(LOG_KEY_VALUE_RE.findall(line))
        expected_status = EXPECTED_LIFECYCLE_EVENT_STATUS_PROOFS[role]
        status_ok = (
            values.get("apply_status") == expected_status["apply_status"]
            and values.get("correlation_status") == expected_status["correlation_status"]
        )
        inside_window, timestamp_prefix, timestamp_error = timestamp_inside_capture_window(line, start, end)
        if full_shape_mismatches and claims_copy_ready:
            add(
                blockers,
                f"{reason_prefix}_copied_log_lifecycle_event_full_shape_mismatch",
                label,
                line=line_number,
                role=role,
                mismatches=full_shape_mismatches,
            )
        if not event_shape_allowed or not status_ok:
            if claims_copy_ready:
                add(
                    blockers,
                    f"{reason_prefix}_copied_log_lifecycle_event_unapproved_for_copy",
                    label,
                    line=line_number,
                    role=role,
                    observed=event_case,
                )
            continue
        event = {
            **event_case,
            "index": len(accepted_in_window_events),
            "line_number": line_number,
            "sequence": int(match.group("sequence")),
            "timestamp_prefix": timestamp_prefix,
        }
        if timestamp_error is not None:
            if claims_copy_ready:
                add(
                    blockers,
                    f"{reason_prefix}_copied_log_lifecycle_event_timestamp_not_fresh_window_utc",
                    label,
                    line=line_number,
                    role=role,
                    timestamp_prefix=timestamp_prefix,
                    timestamp_error=timestamp_error,
                )
            continue
        if not inside_window:
            historical_accepted_events.append(event)
            if claims_copy_ready:
                add(
                    blockers,
                    f"{reason_prefix}_copied_log_lifecycle_event_outside_fresh_window",
                    label,
                    line=line_number,
                    role=role,
                    timestamp_prefix=timestamp_prefix,
                    fresh_window_start_utc=start_text,
                    fresh_window_end_utc=end_text,
                )
            continue
        accepted_in_window_events.append(event)

    if not observer_enable_seen and claims_copy_ready:
        add(blockers, f"{reason_prefix}_observer_enable_missing_for_fresh_window", label)
    elif not observer_enable_in_fresh_window and claims_copy_ready:
        add(blockers, f"{reason_prefix}_observer_enable_outside_fresh_window", label)

    selection = strict_lifecycle_triplet_selection(
        accepted_in_window_events,
        order_keys=("sequence", "line_number"),
    )
    if selection.get("accepted") is not True:
        if claims_copy_ready:
            add(
                blockers,
                f"{reason_prefix}_copied_log_exact_triplet_not_accepted",
                label,
                selection=selection,
            )
    elif not strict_lifecycle_triplet_is_exact(selection):
        if claims_copy_ready:
            add(
                blockers,
                f"{reason_prefix}_copied_log_exact_triplet_not_exact",
                label,
                selection=selection,
            )

    if analysis.get("observer_enable_in_fresh_window") is not True and claims_copy_ready:
        add(
            blockers,
            f"{reason_prefix}_analysis_observer_enable_in_fresh_window_not_true",
            label,
            actual=analysis.get("observer_enable_in_fresh_window"),
        )
    if isinstance(analysis.get("accepted_lifecycle_event_count"), int):
        if analysis.get("accepted_lifecycle_event_count") != len(accepted_in_window_events):
            if claims_copy_ready:
                add(
                    blockers,
                    f"{reason_prefix}_analysis_accepted_lifecycle_event_count_mismatch",
                    label,
                    expected=len(accepted_in_window_events),
                    actual=analysis.get("accepted_lifecycle_event_count"),
                )
    elif claims_copy_ready:
        add(
            blockers,
            f"{reason_prefix}_analysis_accepted_lifecycle_event_count_missing",
            label,
        )
    if isinstance(analysis.get("historical_accepted_role_event_count"), int):
        if analysis.get("historical_accepted_role_event_count") != len(historical_accepted_events):
            if claims_copy_ready:
                add(
                    blockers,
                    f"{reason_prefix}_analysis_historical_accepted_role_event_count_mismatch",
                    label,
                    expected=len(historical_accepted_events),
                    actual=analysis.get("historical_accepted_role_event_count"),
                )

    exact_triplet = analysis.get("exact_copied_runtime_triplet")
    if not isinstance(exact_triplet, dict):
        if claims_copy_ready:
            add(blockers, f"{reason_prefix}_exact_copied_runtime_triplet_missing", label)
    else:
        if exact_triplet.get("accepted") is not True and claims_copy_ready:
            add(
                blockers,
                f"{reason_prefix}_exact_copied_runtime_triplet_not_accepted",
                label,
                exact_copied_runtime_triplet=exact_triplet,
            )
        exact_blockers = exact_triplet.get("blockers")
        if exact_blockers not in (None, []) and claims_copy_ready:
            add(
                blockers,
                f"{reason_prefix}_exact_copied_runtime_triplet_blockers_present",
                label,
                exact_copied_runtime_triplet_blockers=exact_blockers,
            )
        if strict_lifecycle_triplet_is_exact(selection):
            expected_selection_fields = {
                "selected_indices": selection.get("selected_indices"),
                "selected_sequences": selection.get("selected_sequences"),
                "selected_roles": selection.get("selected_roles"),
            }
            for key, expected in expected_selection_fields.items():
                actual = exact_triplet.get(key)
                if actual is not None and actual != expected and claims_copy_ready:
                    add(
                        blockers,
                        f"{reason_prefix}_exact_copied_runtime_triplet_{key}_mismatch",
                        label,
                        expected=expected,
                        actual=actual,
                    )

    state.update(
        {
            "accepted": (
                selection.get("accepted") is True
                and strict_lifecycle_triplet_is_exact(selection)
                and observer_enable_in_fresh_window
            ),
            "observer_enable_in_fresh_window": observer_enable_in_fresh_window,
            "accepted_lifecycle_event_count": len(accepted_in_window_events),
            "historical_accepted_role_event_count": len(historical_accepted_events),
            "strict_lifecycle_triplet_selection": selection,
        }
    )
    return state


def ready_log_copy_report_state(
    path: Path,
    expected_copied_log: Path,
    *,
    label: str = "ready_log_copy",
    reason_prefix: str = "ready_log_copy",
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    state: dict[str, Any] = {
        "path": str(path.expanduser().resolve()),
        "exists": False,
        "checked": False,
        "accepted": False,
        "schema": None,
        "status": None,
        "evidence_dir": None,
        "ready_to_copy": None,
        "copy_readiness": "not_provided",
        "roles_present": [],
        "missing_roles": [],
        "analysis": {},
        "fresh_window": {},
        "fresh_window_triplet": {},
        "reported_blockers": [],
        "source_log_safety": {},
        "source_log_not_ready": {},
        "source_log_not_ready_reason": None,
        "source_log_not_ready_blockers": [],
        "observer_only_no_role_window_detected": False,
        "player_present_but_no_lifecycle_roles": False,
        "player_presence_context": {},
        "player_presence_context_counts_as_approved_runtime_evidence": False,
        "copy_report_counts_as_approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "blockers": [],
        "blocker_details": [],
    }
    symlink_component = first_symlink_component(path)
    if symlink_component is not None:
        add(blockers, f"{reason_prefix}_path_symlink_component", label, symlink=str(symlink_component))
        state["blockers"] = [blocker["reason"] for blocker in blockers]
        state["blocker_details"] = blockers
        return state
    status = protected_paths.protected_path_status(
        path.expanduser(),
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    state["path"] = str(status.resolved)
    if not status.resolved.exists():
        return state
    state["exists"] = status.resolved.is_file()
    state["checked"] = True
    if status.protected or not status.approved_offline_workspace:
        add(blockers, f"{reason_prefix}_not_approved_offline_workspace", label, path=str(status.resolved))
    if not status.resolved.is_file():
        add(blockers, f"{reason_prefix}_not_file", label, path=str(status.resolved))
    if blockers:
        state["blockers"] = [blocker["reason"] for blocker in blockers]
        state["blocker_details"] = blockers
        return state

    try:
        payload = json.loads(status.resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        add(blockers, f"{reason_prefix}_json_invalid", label, path=str(status.resolved), error=str(exc))
        state["blockers"] = [blocker["reason"] for blocker in blockers]
        state["blocker_details"] = blockers
        return state
    except OSError as exc:
        add(blockers, f"{reason_prefix}_unreadable", label, path=str(status.resolved), error=str(exc))
        state["blockers"] = [blocker["reason"] for blocker in blockers]
        state["blocker_details"] = blockers
        return state
    if not isinstance(payload, dict):
        add(blockers, f"{reason_prefix}_json_not_object", label, path=str(status.resolved))
        state["blockers"] = [blocker["reason"] for blocker in blockers]
        state["blocker_details"] = blockers
        return state

    state["schema"] = payload.get("schema")
    state["status"] = payload.get("status")
    state["ready_to_copy"] = payload.get("ready_to_copy")
    state["copy_readiness"] = payload.get("copy_readiness", "not_provided")
    state["roles_present"] = payload.get("roles_present", [])
    state["missing_roles"] = payload.get("missing_roles", [])
    reported_blockers = payload.get("blockers")
    if isinstance(reported_blockers, list) and all(isinstance(blocker, str) for blocker in reported_blockers):
        state["reported_blockers"] = reported_blockers
    source_log_safety = payload.get("source_log_safety")
    if isinstance(source_log_safety, dict):
        state["source_log_safety"] = source_log_safety
        safety_presence = source_log_safety.get("player_presence_context")
        if isinstance(safety_presence, dict):
            state["player_presence_context"] = safety_presence
    source_log_not_ready = payload.get("source_log_not_ready")
    if not isinstance(source_log_not_ready, dict):
        source_log_not_ready = payload.get("observer_only_no_role_window")
    if isinstance(source_log_not_ready, dict):
        state["source_log_not_ready"] = source_log_not_ready
        source_blockers = source_log_not_ready.get("blockers")
        if isinstance(source_blockers, list) and all(isinstance(blocker, str) for blocker in source_blockers):
            state["source_log_not_ready_blockers"] = source_blockers
        state["source_log_not_ready_reason"] = source_log_not_ready.get("source_log_not_ready_reason")
        state["observer_only_no_role_window_detected"] = (
            source_log_not_ready.get("observer_only_no_role_window_detected") is True
        )
        state["player_present_but_no_lifecycle_roles"] = (
            source_log_not_ready.get("player_present_but_no_lifecycle_roles") is True
        )
        presence_context = source_log_not_ready.get("player_presence_context")
        if isinstance(presence_context, dict):
            state["player_presence_context"] = presence_context
    state["observer_only_no_role_window_detected"] = (
        state["observer_only_no_role_window_detected"]
        or payload.get("observer_only_no_role_window_detected") is True
    )
    state["player_present_but_no_lifecycle_roles"] = (
        state["player_present_but_no_lifecycle_roles"]
        or payload.get("player_present_but_no_lifecycle_roles") is True
    )
    analysis = payload.get("analysis")
    if isinstance(analysis, dict):
        state["analysis"] = {
            "ready_to_copy": analysis.get("ready_to_copy"),
            "copy_readiness": analysis.get("copy_readiness"),
            "roles_present": analysis.get("roles_present", []),
            "missing_roles": analysis.get("missing_roles", []),
            "observer_enabled": analysis.get("observer_enabled"),
            "observer_enable_in_fresh_window": analysis.get("observer_enable_in_fresh_window"),
            "binary_sha256_match": analysis.get("binary_sha256_match"),
            "duplicate_accepted_role_event_count": analysis.get("duplicate_accepted_role_event_count"),
            "duplicate_accepted_roles": analysis.get("duplicate_accepted_roles", []),
            "accepted_lifecycle_event_count": analysis.get("accepted_lifecycle_event_count"),
            "accepted_lifecycle_events": analysis.get("accepted_lifecycle_events", []),
            "accepted_role_events": analysis.get("accepted_role_events", {}),
            "historical_accepted_role_event_count": analysis.get("historical_accepted_role_event_count"),
            "historical_accepted_role_events": analysis.get("historical_accepted_role_events", []),
            "rejected_or_incomplete_role_event_count": analysis.get("rejected_or_incomplete_role_event_count"),
            "exact_copied_runtime_triplet": analysis.get("exact_copied_runtime_triplet", {}),
            "malformed_observer_lines": analysis.get("malformed_observer_lines"),
            "unsafe_lifecycle_event_reasons": analysis.get("unsafe_lifecycle_event_reasons", {}),
            "invalid_lifecycle_event_non_evidence_reasons": analysis.get(
                "invalid_lifecycle_event_non_evidence_reasons",
                {},
            ),
            "fresh_window": analysis.get("fresh_window", {}),
        }
    else:
        add(blockers, f"{reason_prefix}_analysis_missing", label)
        analysis = {}

    if payload.get("schema") != READY_LOG_COPY_SCHEMA:
        add(blockers, f"{reason_prefix}_schema_mismatch", label, expected=READY_LOG_COPY_SCHEMA, actual=payload.get("schema"))
    if payload.get("ready") is not False:
        add(blockers, f"{reason_prefix}_ready_not_false", label, actual=payload.get("ready"))
    for key in sorted(READY_LOG_COPY_REQUIRED_FALSE_KEYS):
        if payload.get(key, False) is not False:
            add(blockers, f"{reason_prefix}_{key}_not_false", label, actual=payload.get(key))
    validate_ready_log_copy_no_evidence_overclaims(
        payload,
        label,
        blockers,
        reason_prefix=reason_prefix,
    )

    copy_readiness = payload.get("copy_readiness")
    analysis_copy_readiness = analysis.get("copy_readiness")
    if copy_readiness not in READY_LOG_COPY_ALLOWED_READINESS:
        add(blockers, f"{reason_prefix}_copy_readiness_invalid", label, actual=copy_readiness)
    if analysis_copy_readiness not in (None, copy_readiness):
        add(
            blockers,
            f"{reason_prefix}_analysis_copy_readiness_mismatch",
            label,
            expected=copy_readiness,
            actual=analysis_copy_readiness,
        )

    roles_present = payload.get("roles_present")
    missing_roles = payload.get("missing_roles")
    analysis_roles_present = analysis.get("roles_present")
    analysis_missing_roles = analysis.get("missing_roles")
    if not isinstance(roles_present, list) or not all(isinstance(role, str) for role in roles_present):
        add(blockers, f"{reason_prefix}_roles_present_invalid", label, actual=roles_present)
        roles_present = []
    if not isinstance(missing_roles, list) or not all(isinstance(role, str) for role in missing_roles):
        add(blockers, f"{reason_prefix}_missing_roles_invalid", label, actual=missing_roles)
        missing_roles = []
    unknown_roles = sorted((set(roles_present) | set(missing_roles)) - set(READY_LOG_COPY_REQUIRED_ROLES))
    if unknown_roles:
        add(blockers, f"{reason_prefix}_role_unknown", label, roles=unknown_roles)
    expected_missing = [role for role in READY_LOG_COPY_REQUIRED_ROLES if role not in set(roles_present)]
    if missing_roles != expected_missing:
        add(blockers, f"{reason_prefix}_missing_roles_mismatch", label, expected=expected_missing, actual=missing_roles)
    if isinstance(analysis_roles_present, list) and analysis_roles_present != roles_present:
        add(
            blockers,
            f"{reason_prefix}_analysis_roles_present_mismatch",
            label,
            expected=roles_present,
            actual=analysis_roles_present,
        )
    if isinstance(analysis_missing_roles, list) and analysis_missing_roles != missing_roles:
        add(
            blockers,
            f"{reason_prefix}_analysis_missing_roles_mismatch",
            label,
            expected=missing_roles,
            actual=analysis_missing_roles,
        )
    if payload.get("ready_to_copy") is True and copy_readiness != "ready_complete_role_triplet":
        add(blockers, f"{reason_prefix}_ready_to_copy_without_complete_triplet", label, actual=copy_readiness)
    if copy_readiness == "ready_complete_role_triplet" and missing_roles:
        add(blockers, f"{reason_prefix}_complete_triplet_with_missing_roles", label, missing=missing_roles)

    expected_log = expected_copied_log.expanduser().resolve()
    actual_sha256 = sha256_file(expected_log) if expected_log.is_file() else None
    expected_evidence_dir = expected_log.parent
    evidence_dir_text = payload.get("evidence_dir")
    if not isinstance(evidence_dir_text, str) or not evidence_dir_text:
        add(blockers, f"{reason_prefix}_evidence_dir_missing", label)
    else:
        evidence_dir = Path(evidence_dir_text).expanduser().resolve()
        state["evidence_dir"] = str(evidence_dir)
        if evidence_dir != expected_evidence_dir:
            add(
                blockers,
                f"{reason_prefix}_evidence_dir_mismatch",
                label,
                expected=str(expected_evidence_dir),
                actual=str(evidence_dir),
            )
    target_log_text = payload.get("target_log")
    if not isinstance(target_log_text, str) or not target_log_text:
        add(blockers, f"{reason_prefix}_target_log_missing", label)
    elif Path(target_log_text).expanduser().resolve() != expected_log:
        add(
            blockers,
            f"{reason_prefix}_target_log_mismatch",
            label,
            expected=str(expected_log),
            actual=str(Path(target_log_text).expanduser().resolve()),
        )
    target_copied_sha256 = payload.get("target_copied_sha256")
    if payload.get("status") == "copied":
        if payload.get("copied") is not True:
            add(blockers, f"{reason_prefix}_copied_not_true_for_copied_status", label)
        if target_copied_sha256 != actual_sha256:
            add(
                blockers,
                f"{reason_prefix}_target_copied_sha256_mismatch",
                label,
                expected=actual_sha256,
                actual=target_copied_sha256,
            )
    else:
        if payload.get("copied") is True:
            add(blockers, f"{reason_prefix}_copied_true_without_copied_status", label, actual=payload.get("status"))
        if expected_log.is_file() and payload.get("ready_to_copy") is True:
            add(blockers, f"{reason_prefix}_ready_to_copy_without_copied_execution_not_evidence", label)
    if payload.get("source_sha256") is not None and actual_sha256 is not None and payload.get("status") == "copied":
        if payload.get("source_sha256") != actual_sha256:
            add(
                blockers,
                f"{reason_prefix}_source_sha256_mismatch",
                label,
                expected=actual_sha256,
                actual=payload.get("source_sha256"),
            )

    fresh_window_triplet = validate_ready_log_copy_fresh_window(
        payload,
        analysis if isinstance(analysis, dict) else {},
        expected_log,
        label,
        blockers,
        reason_prefix=reason_prefix,
    )
    state["fresh_window"] = fresh_window_triplet.get("fresh_window", {})
    state["fresh_window_triplet"] = fresh_window_triplet
    if payload.get("ready_to_copy") is True and fresh_window_triplet.get("accepted") is not True:
        add(
            blockers,
            f"{reason_prefix}_ready_to_copy_without_accepted_fresh_window_triplet",
            label,
            fresh_window_triplet=fresh_window_triplet,
        )
    if (
        isinstance(source_log_safety, dict)
        and payload.get("ready_to_copy") is True
        and source_log_safety.get("accepted") is not True
    ):
        add(
            blockers,
            f"{reason_prefix}_ready_to_copy_with_source_log_safety_blockers",
            label,
            source_log_safety=source_log_safety,
        )

    state["accepted"] = not blockers
    state["blockers"] = [blocker["reason"] for blocker in blockers]
    state["blocker_details"] = blockers
    return state


def add_non_evidence_schema_blocker(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    reason_prefix: str,
    label: str,
) -> None:
    schema = payload.get("schema")
    if not isinstance(schema, str):
        return
    if (
        schema == EXPECTED_OPERATOR_APPROVAL_RECEIPT_SCHEMA
        and reason_prefix == "operational_window_operator_approval_receipt"
    ):
        return
    reason = NON_EVIDENCE_SIDECAR_SCHEMA_BLOCKERS.get(schema)
    if reason is None:
        reason = non_approved_runtime_evidence_schema_alias_reason(schema)
    if reason is None:
        return
    add(blockers, f"{reason_prefix}_{reason}", label, schema=schema)


def non_approved_runtime_evidence_schema_alias_reason(schema: str) -> str | None:
    for pattern, reason in NON_APPROVED_RUNTIME_EVIDENCE_SCHEMA_ALIAS_BLOCKERS:
        if pattern.search(schema):
            return reason
    return None


def non_approved_runtime_evidence_input_path_alias_reasons(path: Path) -> list[str]:
    path_text = str(path)
    reasons: list[str] = []
    filename_reason = NON_APPROVED_RUNTIME_EVIDENCE_INPUT_PATH_NAME_BLOCKERS.get(path.name.casefold())
    if filename_reason is not None:
        reasons.append(filename_reason)
    for pattern, reason in NON_APPROVED_RUNTIME_EVIDENCE_INPUT_PATH_ALIAS_BLOCKERS:
        if pattern.search(path_text) and reason not in reasons:
            reasons.append(reason)
    return reasons


def load_json(path: Path) -> dict[str, Any]:
    reject_symlink_component(path, "manifest")
    path = reject_protected_input_path(path, "manifest")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: top-level JSON must be an object")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_obelisk_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    commit = result.stdout.strip()
    if result.returncode != 0 or GIT_COMMIT_RE.fullmatch(commit) is None:
        return None
    return commit


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_utc_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError:
        return None


def parsed_window_timestamp(
    value: Any,
    *,
    reason: str,
    label: str,
    blockers: list[dict[str, Any]],
) -> datetime | None:
    if not isinstance(value, str) or UTC_TIMESTAMP_RE.fullmatch(value) is None:
        add(blockers, reason, label)
        return None
    parsed = parse_utc_timestamp(value)
    if parsed is None:
        add(blockers, reason, label)
    return parsed


def expected_output_artifact_sha256(payload: dict[str, Any], identity: dict[str, str]) -> str:
    identity_without_hash = {
        "artifact_kind": identity["artifact_kind"],
        "capture_id": identity["capture_id"],
        "evidence_pack_id": identity["evidence_pack_id"],
    }
    manifest_without_identity = {
        key: value
        for key, value in payload.items()
        if key != "output_artifact_identity"
    }
    material = {
        "artifact_identity": identity_without_hash,
        "report": manifest_without_identity,
    }
    return hashlib.sha256(canonical_json_bytes(material)).hexdigest()


def validate_output_artifact_identity(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    identity, errors = complete_artifact_identity(
        payload,
        container_key="output_artifact_identity",
        expected_artifact_kind=SCHEMA,
    )
    if errors or identity is None:
        add(
            blockers,
            "output_artifact_identity_invalid",
            "$.output_artifact_identity",
            errors=errors,
        )
        return
    run_id = payload.get("operational_window", {}).get("run_id")
    if identity["capture_id"] != run_id:
        add(
            blockers,
            "output_artifact_identity_capture_id_mismatch",
            "$.output_artifact_identity.capture_id",
            expected=run_id,
            observed=identity["capture_id"],
        )
    expected_sha256 = expected_output_artifact_sha256(payload, identity)
    if identity["artifact_sha256"] != expected_sha256:
        add(
            blockers,
            "output_artifact_identity_hash_mismatch",
            "$.output_artifact_identity.artifact_sha256",
            expected=expected_sha256,
            observed=identity["artifact_sha256"],
        )


def source_path_is_copied_or_offline(path_text: Any) -> bool:
    if not isinstance(path_text, str) or not path_text:
        return False
    status = protected_paths.protected_path_status(
        Path(path_text).expanduser(),
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    return not status.protected


def source_path_is_approved_offline_workspace(path_text: Any) -> bool:
    if not isinstance(path_text, str) or not path_text:
        return False
    status = protected_paths.protected_path_status(
        Path(path_text).expanduser(),
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    return not status.protected and status.approved_offline_workspace


def path_from_text(path_text: str, *, base_dir: Path | None = None) -> Path:
    path = Path(path_text).expanduser()
    if base_dir is not None and not path.is_absolute():
        return base_dir / path
    return path


def symlink_component_for_path_text(path_text: Any, *, base_dir: Path | None = None) -> Path | None:
    if not isinstance(path_text, str) or not path_text:
        return None
    return first_symlink_component(path_from_text(path_text, base_dir=base_dir))


def validate_copied_source_file(source: dict[str, Any], label: str, blockers: list[dict[str, Any]]) -> None:
    path_text = source.get("path")
    expected_sha256 = source.get("sha256")
    if not isinstance(expected_sha256, str) or SHA256_RE.fullmatch(expected_sha256) is None:
        add(blockers, "source_summary_source_sha256_invalid", f"{label}.sha256")
        return
    if not isinstance(path_text, str) or not path_text:
        add(blockers, "source_summary_source_path_missing", f"{label}.path")
        return
    path = Path(path_text).expanduser()
    try:
        actual_sha256 = sha256_file(path)
    except FileNotFoundError:
        add(
            blockers,
            "source_summary_source_file_missing",
            f"{label}.path",
            expected=str(path),
            path=str(path),
        )
        return
    except OSError as exc:
        add(blockers, "source_summary_source_file_unreadable", f"{label}.path", error=str(exc))
        return
    if actual_sha256 != expected_sha256:
        add(
            blockers,
            "source_summary_source_sha256_mismatch",
            f"{label}.sha256",
            expected=expected_sha256,
            actual=actual_sha256,
            path=str(path),
        )


def validate_operational_window_artifact(
    artifact: Any,
    label: str,
    blockers: list[dict[str, Any]],
    *,
    run_id: str | None,
    expected_name: str | None = None,
    base_dir: Path | None = None,
) -> None:
    expected_path = str(base_dir / expected_name) if base_dir is not None and expected_name is not None else None
    if not isinstance(artifact, dict):
        extra = {"expected": expected_path} if expected_path is not None else {}
        add(blockers, "operational_window_artifact_missing", label, **extra)
        return
    unexpected_keys = set(artifact) - ALLOWED_OPERATIONAL_WINDOW_ARTIFACT_KEYS
    if unexpected_keys:
        add(blockers, "operational_window_artifact_keys_unexpected", label, unexpected=sorted(unexpected_keys))
    path_text = artifact.get("path")
    sha256 = artifact.get("sha256")
    if not isinstance(sha256, str) or SHA256_RE.fullmatch(sha256) is None or sha256 == "0" * 64:
        add(blockers, "operational_window_artifact_sha256_invalid", f"{label}.sha256")
    if not isinstance(path_text, str) or not path_text:
        extra = {"expected": expected_path} if expected_path is not None else {}
        add(blockers, "operational_window_artifact_path_missing", f"{label}.path", **extra)
        return
    symlink_component = symlink_component_for_path_text(path_text, base_dir=base_dir)
    path_safe_for_hash = True
    if symlink_component is not None:
        add(
            blockers,
            "operational_window_artifact_path_symlink_component",
            f"{label}.path",
            symlink=str(symlink_component),
        )
        path_safe_for_hash = False
    status = protected_paths.protected_path_status(
        path_from_text(path_text, base_dir=base_dir),
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected:
        add(blockers, "operational_window_artifact_path_not_copied_or_offline", f"{label}.path")
        path_safe_for_hash = False
    elif not status.approved_offline_workspace:
        add(blockers, "operational_window_artifact_path_not_approved_offline_workspace", f"{label}.path")
        path_safe_for_hash = False
    path = path_from_text(path_text, base_dir=base_dir)
    if run_id and run_id not in path.parts:
        add(blockers, "operational_window_artifact_run_id_mismatch", f"{label}.path", run_id=run_id)
    if expected_name is not None and path.name != expected_name:
        add(blockers, "operational_window_artifact_filename_mismatch", f"{label}.path", expected=expected_name)
    if not path_safe_for_hash:
        return
    try:
        actual_sha256 = sha256_file(path)
    except FileNotFoundError:
        add(
            blockers,
            "operational_window_artifact_file_missing",
            f"{label}.path",
            expected=str(path),
            path=str(path),
        )
        return
    except OSError as exc:
        add(blockers, "operational_window_artifact_file_unreadable", f"{label}.path", error=str(exc))
        return
    if isinstance(sha256, str) and SHA256_RE.fullmatch(sha256) and actual_sha256 != sha256:
        add(
            blockers,
            "operational_window_artifact_sha256_mismatch",
            f"{label}.sha256",
            expected=sha256,
            actual=actual_sha256,
            path=str(path),
        )


def approved_artifact_status(
    artifact: Any,
    *,
    base_dir: Path | None = None,
) -> protected_paths.ProtectedPathStatus | None:
    if not isinstance(artifact, dict):
        return None
    path_text = artifact.get("path")
    if not isinstance(path_text, str) or not path_text:
        return None
    if symlink_component_for_path_text(path_text, base_dir=base_dir) is not None:
        return None
    status = protected_paths.protected_path_status(
        path_from_text(path_text, base_dir=base_dir),
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected or not status.approved_offline_workspace:
        return None
    return status


def bound_artifact_from_status(status: protected_paths.ProtectedPathStatus) -> dict[str, Any] | None:
    try:
        return {
            "path": str(status.resolved),
            "sha256": sha256_file(status.resolved),
            "size_bytes": status.resolved.stat().st_size,
        }
    except (FileNotFoundError, OSError):
        return None


def resolved_artifact_path(artifact: Any, *, base_dir: Path | None = None) -> str | None:
    status = approved_artifact_status(artifact, base_dir=base_dir)
    return None if status is None else str(status.resolved)


def operational_window_sidecar_dir(window: dict[str, Any]) -> Path | None:
    copied_status = approved_artifact_status(window.get("copied_log"))
    return None if copied_status is None else copied_status.resolved.parent


def parse_sidecar_bool(value: Any) -> bool | None:
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def load_runtime_replacement_env_sidecar(
    path: Path,
    *,
    label: str,
    blockers: list[dict[str, Any]],
    required: bool = False,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "path": str(path),
        "exists": False,
        "fields": {},
        "sha256": None,
    }
    symlink_component = first_symlink_component(path)
    if symlink_component is not None:
        add(
            blockers,
            f"{label}_path_symlink_component",
            f"$.operational_window.{label}.path",
            expected=str(path),
            symlink=str(symlink_component),
        )
        return state
    status = protected_paths.protected_path_status(
        path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    state["path"] = str(status.resolved)
    if status.protected or not status.approved_offline_workspace:
        add(
            blockers,
            f"{label}_not_approved_offline_workspace",
            f"$.operational_window.{label}.path",
            expected=str(path),
            actual=str(status.resolved),
        )
        return state
    if not status.resolved.is_file():
        if required:
            add(
                blockers,
                f"{label}_missing",
                f"$.operational_window.{label}.path",
                expected=str(status.resolved),
            )
        return state

    state["exists"] = True
    try:
        data = status.resolved.read_bytes()
    except OSError as exc:
        add(blockers, f"{label}_unreadable", f"$.operational_window.{label}.path", error=str(exc))
        return state
    state["sha256"] = hashlib.sha256(data).hexdigest()
    fields: dict[str, str] = {}
    for line_number, raw in enumerate(data.decode("utf-8", errors="replace").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            add(
                blockers,
                f"{label}_line_not_key_value",
                f"$.operational_window.{label}.path",
                line=line_number,
            )
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", key):
            add(
                blockers,
                f"{label}_key_unsafe",
                f"$.operational_window.{label}.path",
                line=line_number,
                key=key,
            )
            continue
        if key in fields:
            add(
                blockers,
                f"{label}_duplicate_key",
                f"$.operational_window.{label}.path",
                line=line_number,
                key=key,
            )
            continue
        fields[key] = value
    state["fields"] = fields
    return state


def require_runtime_sidecar_false_flags(
    fields: dict[str, str],
    *,
    label: str,
    reason_prefix: str,
    blockers: list[dict[str, Any]],
) -> None:
    for key in sorted(RUNTIME_REPLACEMENT_SIDECAR_FALSE_FLAGS):
        value = fields.get(key)
        if parse_sidecar_bool(value) is not False:
            add(
                blockers,
                f"{reason_prefix}_{key}_not_false",
                f"$.operational_window.{label}.{key}",
                expected=False,
                actual=value,
            )


def validate_runtime_sidecar_common_binding(
    fields: dict[str, str],
    *,
    label: str,
    reason_prefix: str,
    expected_schema: str,
    run_id: str | None,
    copied_log_path: Path,
    copied_log_sha256: str,
    blockers: list[dict[str, Any]],
) -> None:
    if fields.get("schema") != expected_schema:
        add(
            blockers,
            f"{reason_prefix}_schema_mismatch",
            f"$.operational_window.{label}.schema",
            expected=expected_schema,
            actual=fields.get("schema"),
        )
    if run_id is not None and fields.get("run_id") != run_id:
        add(
            blockers,
            f"{reason_prefix}_run_id_mismatch",
            f"$.operational_window.{label}.run_id",
            expected=run_id,
            actual=fields.get("run_id"),
        )
    copied_path_text = fields.get("copied_log_path")
    actual_copied_path = (
        str(Path(copied_path_text).expanduser().resolve())
        if isinstance(copied_path_text, str) and copied_path_text
        else None
    )
    expected_copied_path = str(copied_log_path.expanduser().resolve())
    if actual_copied_path != expected_copied_path:
        add(
            blockers,
            f"{reason_prefix}_copied_log_path_mismatch",
            f"$.operational_window.{label}.copied_log_path",
            expected=expected_copied_path,
            actual=actual_copied_path,
        )
    sidecar_copied_sha = fields.get("copied_log_sha256")
    if sidecar_copied_sha != copied_log_sha256:
        add(
            blockers,
            f"{reason_prefix}_copied_log_sha256_mismatch",
            f"$.operational_window.{label}.copied_log_sha256",
            expected=copied_log_sha256,
            actual=sidecar_copied_sha,
        )
    require_runtime_sidecar_false_flags(
        fields,
        label=label,
        reason_prefix=reason_prefix,
        blockers=blockers,
    )


def require_runtime_sidecar_sha256(
    fields: dict[str, str],
    key: str,
    *,
    label: str,
    reason_prefix: str,
    blockers: list[dict[str, Any]],
) -> str | None:
    value = fields.get(key)
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        add(
            blockers,
            f"{reason_prefix}_{key}_invalid",
            f"$.operational_window.{label}.{key}",
            actual=value,
        )
        return None
    if value == "0" * 64:
        add(
            blockers,
            f"{reason_prefix}_{key}_placeholder",
            f"$.operational_window.{label}.{key}",
        )
        return None
    return value


def validate_runtime_sidecar_checked_at(
    fields: dict[str, str],
    *,
    label: str,
    reason_prefix: str,
    actual_capture_end_utc: datetime | None,
    rollback_end_utc: datetime | None,
    blockers: list[dict[str, Any]],
) -> None:
    checked_at = fields.get("checked_at_utc")
    if not isinstance(checked_at, str) or UTC_TIMESTAMP_RE.fullmatch(checked_at) is None:
        add(blockers, f"{reason_prefix}_checked_at_utc_invalid", f"$.operational_window.{label}.checked_at_utc")
        return
    parsed = parse_utc_timestamp(checked_at)
    if parsed is None:
        add(blockers, f"{reason_prefix}_checked_at_utc_invalid", f"$.operational_window.{label}.checked_at_utc")
        return
    if parsed > now_utc():
        add(
            blockers,
            f"{reason_prefix}_checked_at_utc_in_future",
            f"$.operational_window.{label}.checked_at_utc",
            checked_at_utc=checked_at,
        )
    if actual_capture_end_utc is not None and parsed < actual_capture_end_utc:
        add(
            blockers,
            f"{reason_prefix}_checked_at_before_capture_end",
            f"$.operational_window.{label}.checked_at_utc",
            checked_at_utc=checked_at,
        )
    if rollback_end_utc is not None and parsed > rollback_end_utc:
        add(
            blockers,
            f"{reason_prefix}_checked_at_after_rollback_end",
            f"$.operational_window.{label}.checked_at_utc",
            checked_at_utc=checked_at,
        )


def runtime_sidecar_replacement_flag(fields: dict[str, str]) -> bool:
    return (
        parse_sidecar_bool(fields.get("installed_runtime_replaced")) is True
        or parse_sidecar_bool(fields.get("runtime_replaced")) is True
    )


def validate_installed_libobelisk_sidecar(
    state: dict[str, Any],
    *,
    run_id: str | None,
    copied_log_path: Path,
    copied_log_sha256: str,
    expected_post_restart_path: Path,
    post_restart_state: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> tuple[bool, str | None]:
    fields = state.get("fields")
    if not isinstance(fields, dict) or state.get("exists") is not True:
        return False, None
    label = "installed_libobelisk"
    reason_prefix = "operational_window_installed_libobelisk_sidecar"
    validate_runtime_sidecar_common_binding(
        fields,
        label=label,
        reason_prefix=reason_prefix,
        expected_schema=INSTALLED_LIBOBELISK_SIDECAR_SCHEMA,
        run_id=run_id,
        copied_log_path=copied_log_path,
        copied_log_sha256=copied_log_sha256,
        blockers=blockers,
    )
    if fields.get("installed_libobelisk_path") != EXPECTED_INSTALLED_LIBOBELISK_PATH:
        add(
            blockers,
            f"{reason_prefix}_path_mismatch",
            "$.operational_window.installed_libobelisk.installed_libobelisk_path",
            expected=EXPECTED_INSTALLED_LIBOBELISK_PATH,
            actual=fields.get("installed_libobelisk_path"),
        )
    installed_sha = require_runtime_sidecar_sha256(
        fields,
        "installed_libobelisk_sha256",
        label=label,
        reason_prefix=reason_prefix,
        blockers=blockers,
    )
    if parse_sidecar_bool(fields.get("installed_runtime_replaced")) is None:
        add(
            blockers,
            f"{reason_prefix}_installed_runtime_replaced_invalid",
            "$.operational_window.installed_libobelisk.installed_runtime_replaced",
            actual=fields.get("installed_runtime_replaced"),
        )
    for deleted_key in ("deleted_libobelisk_mapping_present", "mapped_libobelisk_deleted"):
        if parse_sidecar_bool(fields.get(deleted_key)) is not False:
            add(
                blockers,
                f"{reason_prefix}_{deleted_key}",
                f"$.operational_window.installed_libobelisk.{deleted_key}",
                expected=False,
                actual=fields.get(deleted_key),
            )
    if runtime_sidecar_replacement_flag(fields):
        expected_path = str(expected_post_restart_path.expanduser().resolve())
        actual_path = (
            str(Path(fields["post_restart_preflight_path"]).expanduser().resolve())
            if isinstance(fields.get("post_restart_preflight_path"), str)
            and fields.get("post_restart_preflight_path")
            else None
        )
        if actual_path != expected_path:
            add(
                blockers,
                f"{reason_prefix}_post_restart_preflight_path_mismatch",
                "$.operational_window.installed_libobelisk.post_restart_preflight_path",
                expected=expected_path,
                actual=actual_path,
            )
        post_sha = fields.get("post_restart_preflight_sha256")
        if post_restart_state.get("exists") is True and post_sha != post_restart_state.get("sha256"):
            add(
                blockers,
                f"{reason_prefix}_post_restart_preflight_sha256_mismatch",
                "$.operational_window.installed_libobelisk.post_restart_preflight_sha256",
                expected=post_restart_state.get("sha256"),
                actual=post_sha,
            )
    return runtime_sidecar_replacement_flag(fields), installed_sha


def validate_post_restart_preflight_sidecar(
    state: dict[str, Any],
    *,
    run_id: str | None,
    copied_log_path: Path,
    copied_log_sha256: str,
    installed_libobelisk_sha256: str | None,
    actual_capture_end_utc: datetime | None,
    rollback_end_utc: datetime | None,
    blockers: list[dict[str, Any]],
) -> bool:
    fields = state.get("fields")
    if not isinstance(fields, dict) or state.get("exists") is not True:
        return False
    label = "post_restart_preflight"
    reason_prefix = "operational_window_post_restart_preflight_sidecar"
    validate_runtime_sidecar_common_binding(
        fields,
        label=label,
        reason_prefix=reason_prefix,
        expected_schema=POST_RESTART_PREFLIGHT_SIDECAR_SCHEMA,
        run_id=run_id,
        copied_log_path=copied_log_path,
        copied_log_sha256=copied_log_sha256,
        blockers=blockers,
    )
    if parse_sidecar_bool(fields.get("post_restart_preflight")) is not True:
        add(
            blockers,
            f"{reason_prefix}_post_restart_preflight_not_true",
            "$.operational_window.post_restart_preflight.post_restart_preflight",
            actual=fields.get("post_restart_preflight"),
        )
    expected_values = {
        "post_restart_posture": "stable",
        "posture_check": "accepted",
        "sibling_marker_entries": "absent",
        "sibling_observer_env": "absent",
        "debug_escape_markers": "absent",
        "callback_escape_markers": "absent",
    }
    for key, expected in expected_values.items():
        if fields.get(key) != expected:
            add(
                blockers,
                f"{reason_prefix}_{key}_mismatch",
                f"$.operational_window.post_restart_preflight.{key}",
                expected=expected,
                actual=fields.get(key),
            )
    for key in ("plugins_disabled", "scanner_disabled", "native_exec_disabled", "ptrace_disabled"):
        if parse_sidecar_bool(fields.get(key)) is not True:
            add(
                blockers,
                f"{reason_prefix}_{key}_not_true",
                f"$.operational_window.post_restart_preflight.{key}",
                expected=True,
                actual=fields.get(key),
            )
    for key in ("observer_env_survived", "observer_marker_survived"):
        if parse_sidecar_bool(fields.get(key)) is not False:
            add(
                blockers,
                f"{reason_prefix}_{key}_not_false",
                f"$.operational_window.post_restart_preflight.{key}",
                expected=False,
                actual=fields.get(key),
            )
    for deleted_key in ("deleted_libobelisk_mapping_present", "mapped_libobelisk_deleted"):
        if parse_sidecar_bool(fields.get(deleted_key)) is not False:
            add(
                blockers,
                f"{reason_prefix}_{deleted_key}",
                f"$.operational_window.post_restart_preflight.{deleted_key}",
                expected=False,
                actual=fields.get(deleted_key),
            )
    post_sha = require_runtime_sidecar_sha256(
        fields,
        "installed_libobelisk_sha256",
        label=label,
        reason_prefix=reason_prefix,
        blockers=blockers,
    )
    if installed_libobelisk_sha256 is not None and post_sha != installed_libobelisk_sha256:
        add(
            blockers,
            f"{reason_prefix}_installed_libobelisk_sha256_mismatch",
            "$.operational_window.post_restart_preflight.installed_libobelisk_sha256",
            expected=installed_libobelisk_sha256,
            actual=post_sha,
        )
    validate_runtime_sidecar_checked_at(
        fields,
        label=label,
        reason_prefix=reason_prefix,
        actual_capture_end_utc=actual_capture_end_utc,
        rollback_end_utc=rollback_end_utc,
        blockers=blockers,
    )
    return runtime_sidecar_replacement_flag(fields)


def validate_runtime_replacement_sidecar_files(
    sidecar_dir: Path,
    *,
    copied_log_path: Path,
    copied_log_sha256: str,
    run_id: str | None,
    actual_capture_end_utc: datetime | None = None,
    rollback_end_utc: datetime | None = None,
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    installed_path = sidecar_dir / INSTALLED_LIBOBELISK_SIDECAR_FILENAME
    post_restart_path = sidecar_dir / POST_RESTART_PREFLIGHT_SIDECAR_FILENAME
    installed_state = load_runtime_replacement_env_sidecar(
        installed_path,
        label="installed_libobelisk",
        blockers=blockers,
    )
    post_restart_state = load_runtime_replacement_env_sidecar(
        post_restart_path,
        label="post_restart_preflight",
        blockers=blockers,
    )
    installed_replaced, installed_sha = validate_installed_libobelisk_sidecar(
        installed_state,
        run_id=run_id,
        copied_log_path=copied_log_path,
        copied_log_sha256=copied_log_sha256,
        expected_post_restart_path=post_restart_path,
        post_restart_state=post_restart_state,
        blockers=blockers,
    )
    post_replaced = validate_post_restart_preflight_sidecar(
        post_restart_state,
        run_id=run_id,
        copied_log_path=copied_log_path,
        copied_log_sha256=copied_log_sha256,
        installed_libobelisk_sha256=installed_sha,
        actual_capture_end_utc=actual_capture_end_utc,
        rollback_end_utc=rollback_end_utc,
        blockers=blockers,
    )
    replacement_required = installed_replaced or post_replaced
    if replacement_required and installed_state.get("exists") is not True:
        add(
            blockers,
            "operational_window_installed_libobelisk_sidecar_missing_for_replacement",
            "$.operational_window.installed_libobelisk.path",
            expected=str(installed_path),
        )
    if replacement_required and post_restart_state.get("exists") is not True:
        add(
            blockers,
            "operational_window_post_restart_preflight_sidecar_missing",
            "$.operational_window.post_restart_preflight.path",
            expected=str(post_restart_path),
        )
    return {
        "installed_libobelisk": installed_state,
        "post_restart_preflight": post_restart_state,
        "installed_runtime_replaced": replacement_required,
        "post_restart_preflight_required": replacement_required,
    }


def nested_operational_window_artifact(window: dict[str, Any], key: str) -> Any:
    current: Any = window
    for part in key.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def confirmed_notice_required_for_window(window: dict[str, Any]) -> bool:
    return (
        window.get("user_policy") == "operator_approved_beta_users"
        or window.get("notice_sent") == "true"
    )


def validate_confirmed_notice_request_binding(
    payload: dict[str, Any],
    window: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    base_dir: Path,
    label: str,
) -> None:
    request_ref = payload.get("request_json")
    if not isinstance(request_ref, dict):
        add(blockers, "operational_window_confirmed_notice_request_json_missing", label)
        return

    request_status = approved_artifact_status(window.get("request_pack"), base_dir=base_dir)
    if request_status is None:
        add(blockers, "operational_window_confirmed_notice_request_pack_unavailable", label)
        return

    expected_path = str(request_status.resolved)
    expected_sha256 = sha256_file(request_status.resolved) if request_status.resolved.is_file() else None
    request_path = request_ref.get("path")
    request_sha256 = request_ref.get("sha256")
    actual_path = (
        str(Path(request_path).expanduser().resolve())
        if isinstance(request_path, str) and request_path
        else None
    )
    if actual_path != expected_path:
        add(
            blockers,
            "operational_window_confirmed_notice_request_json_path_mismatch",
            f"{label}.request_json.path",
            expected=expected_path,
            actual=actual_path,
        )
    if request_sha256 != expected_sha256:
        add(
            blockers,
            "operational_window_confirmed_notice_request_json_sha256_mismatch",
            f"{label}.request_json.sha256",
            expected=expected_sha256,
            actual=request_sha256,
        )


def validate_confirmed_notice_sidecar(window: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if not confirmed_notice_required_for_window(window):
        return
    expected_dir = operational_window_sidecar_dir(window)
    label = "$.operational_window.confirmed_notice_report"
    if expected_dir is None:
        add(blockers, "operational_window_confirmed_notice_copied_log_unavailable", label)
        return

    expected_path = expected_dir / CONFIRMED_BETA_NOTICE_FILENAME
    symlink_component = first_symlink_component(expected_path)
    if symlink_component is not None:
        add(
            blockers,
            "operational_window_confirmed_notice_path_symlink_component",
            label,
            expected=str(expected_path),
            symlink=str(symlink_component),
        )
        return

    status = protected_paths.protected_path_status(
        expected_path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected or not status.approved_offline_workspace:
        add(
            blockers,
            "operational_window_confirmed_notice_not_approved_offline_workspace",
            label,
            expected=str(expected_path),
            actual=str(status.resolved),
        )
        return
    if not status.resolved.is_file():
        add(
            blockers,
            "operational_window_confirmed_notice_sidecar_missing",
            label,
            expected=str(expected_path),
        )
        return

    try:
        payload = json.loads(status.resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        add(blockers, "operational_window_confirmed_notice_json_invalid", label, error=str(exc))
        return
    except OSError as exc:
        add(blockers, "operational_window_confirmed_notice_unreadable", label, error=str(exc))
        return
    if not isinstance(payload, dict):
        add(blockers, "operational_window_confirmed_notice_json_not_object", label)
        return

    validate_no_sidecar_overclaims(payload, label, blockers)
    expected_fields = {
        "schema": CONFIRMED_NOTICE_SCHEMA,
        "mode": "confirmed_send",
        "ready": True,
        "discord_sent": True,
        "run_id": window.get("run_id"),
        "target": window.get("target"),
        "notice_path": APPROVED_BETA_NOTICE_PATH,
    }
    for key, expected in expected_fields.items():
        if payload.get(key) != expected:
            add(
                blockers,
                f"operational_window_confirmed_notice_{key}_mismatch",
                f"{label}.{key}",
                expected=expected,
                actual=payload.get(key),
            )

    for key in sorted(CONFIRMED_NOTICE_REQUIRED_FALSE_KEYS):
        if payload.get(key, False) is not False:
            add(
                blockers,
                f"operational_window_confirmed_notice_{key}_not_false",
                f"{label}.{key}",
                actual=payload.get(key),
            )

    validate_player_notice_action_contract(
        payload.get("player_notice_action"),
        user_policy="operator_approved_beta_users",
        notice_path=payload.get("notice_path"),
        blockers=blockers,
        label=label,
        reason_prefix="operational_window_confirmed_notice",
    )
    validate_confirmed_notice_request_binding(
        payload,
        window,
        blockers,
        base_dir=expected_dir,
        label=label,
    )
    guarded = payload.get("guarded_beta_notice_action")
    if not isinstance(guarded, dict):
        add(blockers, "operational_window_confirmed_notice_guarded_action_missing", label)
    elif guarded.get("schema") != GUARDED_BETA_NOTICE_ACTION_SCHEMA:
        add(
            blockers,
            "operational_window_confirmed_notice_guarded_action_schema_mismatch",
            f"{label}.guarded_beta_notice_action.schema",
            expected=GUARDED_BETA_NOTICE_ACTION_SCHEMA,
            actual=guarded.get("schema"),
        )


def validate_operational_window_sibling_set(
    window: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    timestamps: dict[str, dict[str, datetime]] | None = None,
) -> None:
    copied_status = approved_artifact_status(window.get("copied_log"))
    if copied_status is None:
        return
    expected_dir = copied_status.resolved.parent

    for key, expected_name in REQUIRED_OPERATIONAL_WINDOW_SIBLING_FILENAMES.items():
        expected_path = expected_dir / expected_name
        symlink_component = first_symlink_component(expected_path)
        if symlink_component is not None:
            add(
                blockers,
                "operational_window_required_sibling_path_symlink_component",
                f"$.operational_window.{key}.path",
                expected=str(expected_path),
                symlink=str(symlink_component),
            )
        else:
            status = protected_paths.protected_path_status(
                expected_path,
                protected_root=SERVER_ROOT,
                approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
            )
            if status.protected or not status.approved_offline_workspace:
                add(
                    blockers,
                    "operational_window_required_sibling_not_approved_offline_workspace",
                    f"$.operational_window.{key}.path",
                    expected=str(expected_path),
                    actual=str(status.resolved),
                )
            elif not status.resolved.is_file():
                add(
                    blockers,
                    "operational_window_required_sibling_artifact_missing",
                    f"$.operational_window.{key}.path",
                    expected=str(expected_path),
                )
        artifact = nested_operational_window_artifact(window, key)
        artifact_status = approved_artifact_status(artifact, base_dir=expected_dir)
        if artifact_status is None:
            continue
        if artifact_status.resolved != expected_path:
            add(
                blockers,
                "operational_window_sidecar_not_exact_copied_log_sibling",
                f"$.operational_window.{key}.path",
                expected=str(expected_path),
                actual=str(artifact_status.resolved),
            )

    for key, expected_name in REQUIRED_IMPLICIT_OPERATIONAL_WINDOW_SIDECARS.items():
        expected_path = expected_dir / expected_name
        symlink_component = first_symlink_component(expected_path)
        if symlink_component is not None:
            add(
                blockers,
                "operational_window_implicit_sidecar_path_symlink_component",
                f"$.operational_window.{key}.path",
                expected=str(expected_path),
                symlink=str(symlink_component),
            )
            continue
        status = protected_paths.protected_path_status(
            expected_path,
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        )
        if status.protected or not status.approved_offline_workspace:
            add(
                blockers,
                "operational_window_implicit_sidecar_not_approved_offline_workspace",
                f"$.operational_window.{key}.path",
                expected=str(expected_path),
                actual=str(status.resolved),
            )
            continue
        if not status.resolved.is_file():
            add(
                blockers,
                "operational_window_implicit_sidecar_missing",
                f"$.operational_window.{key}.path",
                expected=str(expected_path),
            )

    ready_log_copy = ready_log_copy_report_state(
        expected_dir / READY_LOG_COPY_FILENAME,
        copied_status.resolved,
        label="$.operational_window.ready_log_copy",
        reason_prefix="operational_window_ready_log_copy",
    )
    blockers.extend(ready_log_copy["blocker_details"])
    if (
        ready_log_copy.get("exists")
        and ready_log_copy.get("ready_to_copy") is not True
    ):
        add(
            blockers,
            "operational_window_ready_log_copy_not_ready_to_copy",
            "$.operational_window.ready_log_copy",
            status=ready_log_copy.get("status"),
            copy_readiness=str(ready_log_copy.get("copy_readiness", "not_provided")),
            roles_present=ready_log_copy.get("roles_present", []),
            missing_roles=ready_log_copy.get("missing_roles", []),
            reported_blockers=ready_log_copy.get("reported_blockers", []),
            source_log_not_ready_reason=ready_log_copy.get("source_log_not_ready_reason"),
            source_log_not_ready_blockers=ready_log_copy.get("source_log_not_ready_blockers", []),
            observer_only_no_role_window_detected=ready_log_copy.get("observer_only_no_role_window_detected") is True,
            player_present_but_no_lifecycle_roles=ready_log_copy.get("player_present_but_no_lifecycle_roles") is True,
            player_presence_context=ready_log_copy.get("player_presence_context", {}),
        )
    validate_confirmed_notice_sidecar(window, blockers)
    copied = window.get("copied_log")
    copied_sha256 = copied.get("sha256") if isinstance(copied, dict) else None
    if isinstance(copied_sha256, str):
        actual_capture = timestamps.get("actual_capture", {}) if isinstance(timestamps, dict) else {}
        rollback = timestamps.get("rollback_window", {}) if isinstance(timestamps, dict) else {}
        validate_runtime_replacement_sidecar_files(
            expected_dir,
            copied_log_path=copied_status.resolved,
            copied_log_sha256=copied_sha256,
            run_id=window.get("run_id") if isinstance(window.get("run_id"), str) else None,
            actual_capture_end_utc=actual_capture.get("end_utc"),
            rollback_end_utc=rollback.get("end_utc"),
            blockers=blockers,
        )
    validate_operational_window_unexpected_json_sidecars(expected_dir, blockers, window=window)


def resolved_path_text(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return str(Path(value).expanduser().resolve())


def expected_bundle_report_identity(payload: dict[str, Any]) -> dict[str, str]:
    report = {
        key: value
        for key, value in payload.items()
        if key != "bundle_report_identity"
    }
    run_id = str(report.get("operational_window", {}).get("run_id"))
    identity = {
        "artifact_kind": BUNDLE_REPORT_SCHEMA,
        "capture_id": run_id,
        "evidence_pack_id": f"player-principal-lifecycle-bundle-{run_id}",
    }
    material = {
        "artifact_identity": identity,
        "report": report,
    }
    return {
        **identity,
        "artifact_sha256": hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        ).hexdigest(),
    }


def add_generated_runtime_summary_binding_blockers(
    payload: dict[str, Any],
    filename: str,
    label: str,
    blockers: list[dict[str, Any]],
    *,
    expected_source_log: str | None,
) -> None:
    if filename != "runtime-observer-summary.json" or expected_source_log is None:
        return
    evidence = payload.get("evidence")
    sources = evidence.get("sources") if isinstance(evidence, dict) else None
    if not isinstance(sources, list) or len(sources) != 1 or not isinstance(sources[0], dict):
        add(
            blockers,
            "approved_bundle_generated_sidecar_source_log_not_exactly_one",
            label,
            filename=filename,
        )
        return
    source = sources[0]
    expected_path = resolved_path_text(expected_source_log)
    actual_path = resolved_path_text(source.get("path"))
    if actual_path != expected_path:
        add(
            blockers,
            "approved_bundle_generated_sidecar_source_log_mismatch",
            label,
            filename=filename,
            expected=expected_path,
            actual=actual_path,
        )
    source_sha256 = source.get("sha256")
    if not isinstance(source_sha256, str) or SHA256_RE.fullmatch(source_sha256) is None:
        add(
            blockers,
            "approved_bundle_generated_sidecar_source_log_sha256_invalid",
            label,
            filename=filename,
            actual=source_sha256,
        )
        return
    try:
        expected_sha256 = sha256_file(Path(expected_source_log).expanduser())
    except OSError as exc:
        add(
            blockers,
            "approved_bundle_generated_sidecar_expected_source_log_unreadable",
            label,
            filename=filename,
            expected=expected_path,
            error=str(exc),
        )
        return
    if source_sha256 != expected_sha256:
        add(
            blockers,
            "approved_bundle_generated_sidecar_source_log_sha256_mismatch",
            label,
            filename=filename,
            expected=expected_sha256,
            actual=source_sha256,
        )


def generated_bundle_sidecar_blockers(
    payload: dict[str, Any],
    filename: str,
    label: str,
    *,
    expected_run_id: str | None = None,
    expected_source_log: str | None = None,
    expected_approved_bundle_path: str | None = None,
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    expected_schema = EXPECTED_APPROVED_BUNDLE_GENERATED_OUTPUT_SCHEMAS.get(filename)
    if expected_schema is None:
        return blockers
    if payload.get("schema") != expected_schema:
        add(
            blockers,
            "approved_bundle_generated_sidecar_schema_mismatch",
            label,
            filename=filename,
            expected=expected_schema,
            actual=payload.get("schema"),
        )

    required_false_keys = {
        normalized_guardrail_alias_key(key)
        for key in GENERATED_BUNDLE_SIDECAR_REQUIRED_FALSE_KEYS
    }

    def generated_false_flag_value_is_false(value: Any) -> bool:
        if value is False:
            return True
        if isinstance(value, str):
            return normalized_guardrail_alias_key(value) in {"false", "no", "none", "not_applicable", "0"}
        return False

    def generated_output_ref_value(value: Any) -> bool:
        return (
            isinstance(value, dict)
            and set(value.keys()) <= {"path", "sha256"}
            and isinstance(value.get("path"), str)
            and isinstance(value.get("sha256"), str)
        )

    def generated_sidecar_non_claim_value(trail: str, value: Any) -> bool:
        if generated_false_flag_value_is_false(value):
            return True
        normalized_trail = normalized_guardrail_alias_key(trail)
        if normalized_trail.endswith("approved_offline_workspace") and value is True:
            return True
        if trail.startswith("$.outputs.") and generated_output_ref_value(value):
            return True
        if trail == "$.post_runtime_contract_gate_required" and value is True:
            return True
        if trail == "$.post_runtime_contract_gate" and value == NEXT_BLOCKER_AFTER_RUNTIME_EVIDENCE:
            return True
        if trail.startswith("$.lifecycle_correlation_proof."):
            allowed_suffixes = (
                ".accepted",
                ".selection.accepted",
                ".single_complete_sibling_set",
                ".copied_log_triplet.accepted",
                ".copied_log_triplet.selection.accepted",
                ".copied_log_triplet.single_complete_sibling_set",
                ".source_summary.accepted",
                ".source_summary.selection.accepted",
                ".source_summary.single_complete_sibling_set",
            )
            if trail.endswith(allowed_suffixes) and value is True:
                return True
        if trail == "$.strict_lifecycle_triplet_selection.accepted" and value is True:
            return True
        return False

    def walk(value: Any, trail: str) -> None:
        if trail == "$.blocker_details" or trail.startswith("$.blocker_details["):
            return
        if isinstance(value, dict):
            for key, child in value.items():
                child_trail = f"{trail}.{key}"
                normalized = normalized_guardrail_alias_key(key)
                non_claim_value = generated_sidecar_non_claim_value(child_trail, child)
                if normalized in required_false_keys and not generated_false_flag_value_is_false(child):
                    add(
                        blockers,
                        "approved_bundle_generated_sidecar_false_flag_overclaim",
                        label,
                        filename=filename,
                        key_path=child_trail,
                        actual=child,
                    )
                if (
                    guardrail_contract_review_alias_key_is_forbidden(key)
                    and guardrail_alias_value_is_positive(child)
                    and not non_claim_value
                ):
                    add(
                        blockers,
                        "approved_bundle_generated_sidecar_contract_review_alias_overclaim",
                        label,
                        filename=filename,
                        key_path=child_trail,
                        actual=child,
                    )
                if (
                    filename == "evidence-bundle-report.json"
                    and normalized not in GENERATED_BUNDLE_SIDECAR_ALLOWED_TRUE_STATUS_KEYS
                    and not non_claim_value
                    and (
                        (
                            child not in (False, None, [], {})
                            and contains_unnegated_positive_capability_claim(str(key))
                        )
                        or (
                            guardrail_alias_key_is_forbidden(key)
                            and guardrail_alias_value_is_positive(child)
                        )
                        or (
                            guardrail_acceptance_alias_key_is_forbidden(key, trail)
                            and guardrail_alias_value_is_positive(child)
                        )
                        or guardrail_path_context_implies_positive_claim(key, child, trail)
                    )
                ):
                    add(
                        blockers,
                        "approved_bundle_generated_sidecar_authorization_or_readiness_alias_overclaim",
                        label,
                        filename=filename,
                        key_path=child_trail,
                        actual=child,
                    )
                if key in ("public_capability_bits_now", "public_callback_abi_now") and child != []:
                    add(
                        blockers,
                        "approved_bundle_generated_sidecar_public_surface_overclaim",
                        label,
                        filename=filename,
                        key_path=child_trail,
                        actual=child,
                    )
                if trail.startswith("$.outputs.") and generated_output_ref_value(child):
                    continue
                walk(child, child_trail)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{trail}[{index}]")

    walk(payload, "$")
    add_generated_runtime_summary_binding_blockers(
        payload,
        filename,
        label,
        blockers,
        expected_source_log=expected_source_log,
    )

    if filename != "evidence-bundle-report.json":
        return blockers

    identity = payload.get("bundle_report_identity")
    expected_identity = expected_bundle_report_identity(payload)
    if identity != expected_identity:
        add(
            blockers,
            "approved_bundle_generated_sidecar_identity_mismatch",
            label,
            filename=filename,
            expected=expected_identity,
            actual=identity,
        )
    if payload.get("status") != "accepted":
        add(
            blockers,
            "approved_bundle_generated_sidecar_status_mismatch",
            label,
            filename=filename,
            expected="accepted",
            actual=payload.get("status"),
        )
    if payload.get("next_blocker") != NEXT_BLOCKER_AFTER_RUNTIME_EVIDENCE:
        add(
            blockers,
            "approved_bundle_generated_sidecar_next_blocker_mismatch",
            label,
            filename=filename,
            expected=NEXT_BLOCKER_AFTER_RUNTIME_EVIDENCE,
            actual=payload.get("next_blocker"),
        )
    if payload.get("current_route_blocker") is not None:
        add(
            blockers,
            "approved_bundle_generated_sidecar_current_route_blocker_not_none",
            label,
            filename=filename,
            actual=payload.get("current_route_blocker"),
        )
    if payload.get("remaining_blockers") != []:
        add(
            blockers,
            "approved_bundle_generated_sidecar_remaining_blockers_not_empty",
            label,
            filename=filename,
            actual=payload.get("remaining_blockers"),
        )
    if payload.get("required_artifact_status") != "accepted":
        add(
            blockers,
            "approved_bundle_generated_sidecar_required_artifact_status_mismatch",
            label,
            filename=filename,
            expected="accepted",
            actual=payload.get("required_artifact_status"),
        )
    operational_window = payload.get("operational_window")
    observed_run_id = operational_window.get("run_id") if isinstance(operational_window, dict) else None
    if expected_run_id is not None and observed_run_id != expected_run_id:
        add(
            blockers,
            "approved_bundle_generated_sidecar_run_id_mismatch",
            label,
            filename=filename,
            expected=expected_run_id,
            actual=observed_run_id,
        )
    if expected_source_log is not None:
        observed_source_log = resolved_path_text(payload.get("source_log"))
        if observed_source_log != resolved_path_text(expected_source_log):
            add(
                blockers,
                "approved_bundle_generated_sidecar_source_log_mismatch",
                label,
                filename=filename,
                expected=resolved_path_text(expected_source_log),
                actual=observed_source_log,
            )
    if expected_approved_bundle_path is not None:
        observed_bundle_path = resolved_path_text(payload.get("approved_bundle_path"))
        if observed_bundle_path != resolved_path_text(expected_approved_bundle_path):
            add(
                blockers,
                "approved_bundle_generated_sidecar_bundle_path_mismatch",
                label,
                filename=filename,
                expected=resolved_path_text(expected_approved_bundle_path),
                actual=observed_bundle_path,
            )
    return blockers


def validate_expected_approved_bundle_generated_json_sidecar(
    path: Path,
    *,
    label: str,
    blockers: list[dict[str, Any]],
    expected_run_id: str | None = None,
    expected_source_log: str | None = None,
    expected_approved_bundle_path: str | None = None,
) -> None:
    symlink_component = first_symlink_component(path)
    if symlink_component is not None:
        add(
            blockers,
            "approved_bundle_generated_sidecar_path_symlink_component",
            label,
            path=str(path),
            symlink=str(symlink_component),
        )
        return
    status = protected_paths.protected_path_status(
        path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected or not status.approved_offline_workspace:
        add(
            blockers,
            "approved_bundle_generated_sidecar_not_approved_offline_workspace",
            label,
            path=str(status.resolved),
        )
        return
    if not status.resolved.is_file():
        return
    try:
        if status.resolved.stat().st_size == 0:
            return
    except OSError as exc:
        add(blockers, "approved_bundle_generated_sidecar_unreadable", label, path=str(status.resolved), error=str(exc))
        return
    try:
        payload = json.loads(status.resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        add(blockers, "approved_bundle_generated_sidecar_json_invalid", label, path=str(status.resolved), error=str(exc))
        return
    except OSError as exc:
        add(blockers, "approved_bundle_generated_sidecar_unreadable", label, path=str(status.resolved), error=str(exc))
        return
    if not isinstance(payload, dict):
        add(blockers, "approved_bundle_generated_sidecar_json_not_object", label, path=str(status.resolved))
        return
    blockers.extend(
        generated_bundle_sidecar_blockers(
            payload,
            path.name,
            label,
            expected_run_id=expected_run_id,
            expected_source_log=expected_source_log,
            expected_approved_bundle_path=expected_approved_bundle_path,
        )
    )


def add_unexpected_json_sidecar_blockers(
    path: Path,
    *,
    label: str,
    reason_prefix: str,
    blockers: list[dict[str, Any]],
) -> None:
    symlink_component = first_symlink_component(path)
    if symlink_component is not None:
        add(
            blockers,
            f"{reason_prefix}_path_symlink_component",
            label,
            path=str(path),
            symlink=str(symlink_component),
        )
        return
    status = protected_paths.protected_path_status(
        path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected or not status.approved_offline_workspace:
        add(
            blockers,
            f"{reason_prefix}_not_approved_offline_workspace",
            label,
            path=str(status.resolved),
        )
        return
    if not status.resolved.is_file():
        return
    try:
        payload = json.loads(status.resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        add(blockers, f"{reason_prefix}_json_invalid", label, path=str(status.resolved), error=str(exc))
        return
    except OSError as exc:
        add(blockers, f"{reason_prefix}_unreadable", label, path=str(status.resolved), error=str(exc))
        return
    if not isinstance(payload, dict):
        add(blockers, f"{reason_prefix}_json_not_object", label, path=str(status.resolved))
        return
    schema = payload.get("schema")
    reason = NON_EVIDENCE_SIDECAR_SCHEMA_BLOCKERS.get(schema) if isinstance(schema, str) else None
    if reason is None and isinstance(schema, str):
        reason = non_approved_runtime_evidence_schema_alias_reason(schema)
    if reason is not None:
        add(blockers, f"{reason_prefix}_{reason}", label, path=str(status.resolved), schema=schema)
    elif isinstance(schema, str):
        add(
            blockers,
            f"{reason_prefix}_schema_not_bound_to_checked_sibling_set",
            label,
            path=str(status.resolved),
            schema=schema,
        )
    else:
        add(blockers, f"{reason_prefix}_schema_missing", label, path=str(status.resolved))
    for path_reason in non_approved_runtime_evidence_input_path_alias_reasons(status.resolved):
        add(
            blockers,
            f"{reason_prefix}_{path_reason}",
            label,
            path=str(status.resolved),
            schema=schema,
        )
    validate_no_sidecar_overclaims(payload, label, blockers)


def validate_operational_window_unexpected_json_sidecars(
    expected_dir: Path,
    blockers: list[dict[str, Any]],
    *,
    window: dict[str, Any] | None = None,
) -> None:
    try:
        entries = list(expected_dir.iterdir())
    except FileNotFoundError:
        return
    except OSError as exc:
        add(blockers, "operational_window_sidecar_scan_failed", "$.operational_window", error=str(exc))
        return
    for entry in sorted(entries):
        if entry.name == APPROVED_BUNDLE_DIRNAME:
            continue
        if entry.name in EXPECTED_OPERATIONAL_WINDOW_TOP_LEVEL_JSON_SIDECARS:
            continue
        if entry.suffix.casefold() != ".json":
            continue
        if not entry.is_file() and not entry.is_symlink():
            continue
        add_unexpected_json_sidecar_blockers(
            entry,
            label=f"$.operational_window.unexpected_json_sidecars.{entry.name}",
            reason_prefix="operational_window_unexpected_json_sidecar",
            blockers=blockers,
        )

    approved_bundle_dir = expected_dir / APPROVED_BUNDLE_DIRNAME
    try:
        bundle_entries = list(approved_bundle_dir.iterdir())
    except FileNotFoundError:
        return
    except NotADirectoryError:
        add(
            blockers,
            "operational_window_approved_bundle_path_not_directory",
            "$.operational_window.approved_bundle",
            path=str(approved_bundle_dir),
        )
        return
    except OSError as exc:
        add(
            blockers,
            "operational_window_approved_bundle_sidecar_scan_failed",
            "$.operational_window.approved_bundle",
            error=str(exc),
        )
        return
    for entry in sorted(bundle_entries):
        if entry.name == APPROVED_BUNDLE_MANIFEST_FILENAME:
            continue
        if entry.name in EXPECTED_APPROVED_BUNDLE_GENERATED_JSON_OUTPUTS:
            validate_expected_approved_bundle_generated_json_sidecar(
                entry,
                label=f"$.operational_window.approved_bundle.generated_json_sidecars.{entry.name}",
                blockers=blockers,
                expected_run_id=window.get("run_id") if isinstance(window, dict) else None,
                expected_source_log=resolved_artifact_path(window.get("copied_log")) if isinstance(window, dict) else None,
                expected_approved_bundle_path=(
                    str(approved_bundle_dir / APPROVED_BUNDLE_MANIFEST_FILENAME)
                    if isinstance(window, dict)
                    else None
                ),
            )
            continue
        if entry.suffix.casefold() != ".json":
            continue
        if not entry.is_file() and not entry.is_symlink():
            continue
        add_unexpected_json_sidecar_blockers(
            entry,
            label=f"$.operational_window.approved_bundle.unexpected_json_sidecars.{entry.name}",
            reason_prefix="operational_window_unexpected_approved_bundle_json_sidecar",
            blockers=blockers,
        )


def artifact_status_for_read(
    artifact: Any,
    label: str,
    blockers: list[dict[str, Any]],
    *,
    base_dir: Path | None = None,
) -> protected_paths.ProtectedPathStatus | None:
    if not isinstance(artifact, dict):
        add(blockers, "operational_window_artifact_missing", label)
        return None
    path_text = artifact.get("path")
    if not isinstance(path_text, str) or not path_text:
        add(blockers, "operational_window_artifact_path_missing", label)
        return None
    symlink_component = symlink_component_for_path_text(path_text, base_dir=base_dir)
    if symlink_component is not None:
        add(
            blockers,
            "operational_window_artifact_path_symlink_component",
            label,
            symlink=str(symlink_component),
        )
        return None
    status = protected_paths.protected_path_status(
        path_from_text(path_text, base_dir=base_dir),
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected:
        add(blockers, "operational_window_artifact_path_not_copied_or_offline", label)
        return None
    if not status.approved_offline_workspace:
        add(blockers, "operational_window_artifact_path_not_approved_offline_workspace", label)
        return None
    return status


def load_json_artifact(
    artifact: Any,
    label: str,
    blockers: list[dict[str, Any]],
    *,
    base_dir: Path | None = None,
) -> dict[str, Any] | None:
    status = artifact_status_for_read(artifact, label, blockers, base_dir=base_dir)
    if status is None:
        return None
    try:
        payload = json.loads(status.resolved.read_text(encoding="utf-8"))
    except OSError as exc:
        add(blockers, "operational_window_json_artifact_unreadable", label, error=str(exc))
        return None
    except json.JSONDecodeError as exc:
        add(blockers, "operational_window_json_artifact_invalid", label, error=str(exc))
        return None
    if not isinstance(payload, dict):
        add(blockers, "operational_window_json_artifact_not_object", label)
        return None
    return payload


def load_text_artifact(
    artifact: Any,
    label: str,
    blockers: list[dict[str, Any]],
    *,
    base_dir: Path | None = None,
) -> str | None:
    status = artifact_status_for_read(artifact, label, blockers, base_dir=base_dir)
    if status is None:
        return None
    try:
        return status.resolved.read_text(encoding="utf-8")
    except OSError as exc:
        add(blockers, "operational_window_text_artifact_unreadable", label, error=str(exc))
        return None


def validate_no_sidecar_overclaims(value: Any, label: str, blockers: list[dict[str, Any]], trail: str = "$") -> None:
    def normalized_claim_key(key: object) -> str:
        return normalized_guardrail_alias_key(key)

    forbidden_keys = {normalized_claim_key(key) for key in FORBIDDEN_POSITIVE_FLAG_KEYS}

    if isinstance(value, dict):
        if trail != "$" and value.get("schema") == SCHEMA:
            add(
                blockers,
                "operational_window_sidecar_nested_approved_runtime_manifest_schema",
                label,
                key_path=f"{trail}.schema",
                schema=SCHEMA,
            )
        if split_guardrail_alias_claim(value):
            add(
                blockers,
                "operational_window_sidecar_authorization_or_readiness_key_overclaim",
                label,
                key_path=trail,
                actual=value,
            )
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            key_name = normalized_claim_key(key)
            if source_overclaim_alias_key_is_forbidden(key):
                add(
                    blockers,
                    "operational_window_sidecar_source_overclaim_alias_is_not_approved_runtime_evidence",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            if lifecycle_role_alias_claim_is_forbidden(key, child):
                add(
                    blockers,
                    "operational_window_sidecar_lifecycle_role_alias_is_not_approved_runtime_evidence",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            if key_name in forbidden_keys and child is not False:
                add(
                    blockers,
                    "operational_window_sidecar_readiness_flag_overclaim",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            if (
                child not in (False, None, [], {})
                and contains_unnegated_positive_capability_claim(str(key))
            ):
                add(
                    blockers,
                    "operational_window_sidecar_authorization_or_readiness_key_overclaim",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            if guardrail_alias_key_is_forbidden(key) and guardrail_alias_value_is_positive(child):
                add(
                    blockers,
                    "operational_window_sidecar_authorization_or_readiness_key_overclaim",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            if guardrail_path_context_implies_positive_claim(key, child, trail):
                add(
                    blockers,
                    "operational_window_sidecar_authorization_or_readiness_key_overclaim",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            if (
                normalized_guardrail_alias_key(key) in GENERIC_STATUS_ALIAS_KEYS
                and guardrail_alias_value_is_positive(child)
            ):
                add(
                    blockers,
                    "operational_window_sidecar_authorization_or_readiness_key_overclaim",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            if key in ("public_capability_bits_now", "public_callback_abi_now") and child != []:
                add(
                    blockers,
                    "operational_window_sidecar_public_surface_overclaim",
                    label,
                    key_path=child_trail,
                    actual=child,
                )
            validate_no_sidecar_overclaims(child, label, blockers, child_trail)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_no_sidecar_overclaims(child, label, blockers, f"{trail}[{index}]")
    elif (
        isinstance(value, str)
        and (
            contains_unnegated_positive_capability_claim(value)
            or (is_readiness_alias_context(trail) and is_forbidden_readiness_alias(value))
        )
        and not value in ALLOWED_POSITIVE_MATCH_NON_CLAIMS
    ):
        add(
            blockers,
            "operational_window_sidecar_forbidden_public_capability_or_readiness_claim",
            label,
            key_path=trail,
            value=value,
        )


def parse_observer_env(text: str, label: str, blockers: list[dict[str, Any]]) -> dict[str, str]:
    env: dict[str, str] = {}
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            add(blockers, "operational_window_observer_env_line_invalid", label, line=line_number)
            continue
        key, value = line.split("=", 1)
        if key in env:
            add(blockers, "operational_window_observer_env_key_duplicate", label, line=line_number, key=key)
            continue
        env[key] = value
    return env


def validate_observer_env_binding(
    window: dict[str, Any],
    request_payload: dict[str, Any] | None,
    blockers: list[dict[str, Any]],
) -> None:
    label = "$.operational_window.observer_env.path"
    base_dir = operational_window_sidecar_dir(window)
    text = load_text_artifact(window.get("observer_env"), label, blockers, base_dir=base_dir)
    if text is None:
        return
    env = parse_observer_env(text, label, blockers)
    target = window.get("target") if isinstance(window.get("target"), dict) else {}
    expected = {
        "OBELISK_INSTANCE_ID": target.get("instance"),
        **REQUIRED_OBSERVER_ENV_VALUES,
    }
    observed_order = [
        line.split("=", 1)[0]
        for raw in text.splitlines()
        if (line := raw.strip()) and not line.startswith("#") and "=" in line
    ]
    if tuple(observed_order) != EXPECTED_OBSERVER_ENV_KEYS:
        add(
            blockers,
            "operational_window_observer_env_key_order_or_set_mismatch",
            label,
            expected=list(EXPECTED_OBSERVER_ENV_KEYS),
            actual=observed_order,
        )
    for key, expected_value in expected.items():
        if env.get(key) != expected_value:
            add(
                blockers,
                "operational_window_observer_env_value_mismatch",
                label,
                key=key,
                expected=expected_value,
                actual=env.get(key),
            )
    if request_payload is not None and request_payload.get("observer_env_file") != "observer-window.env":
        add(
            blockers,
            "operational_window_request_observer_env_file_mismatch",
            "$.operational_window.request_pack.path",
            expected="observer-window.env",
            actual=request_payload.get("observer_env_file"),
        )


def validate_request_pack_binding(window: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    label = "$.operational_window.request_pack.path"
    base_dir = operational_window_sidecar_dir(window)
    payload = load_json_artifact(window.get("request_pack"), label, blockers, base_dir=base_dir)
    if payload is None:
        return None
    add_non_evidence_schema_blocker(
        payload,
        blockers,
        reason_prefix="operational_window_request_pack",
        label=label,
    )
    validate_no_sidecar_overclaims(payload, label, blockers)
    if payload.get("schema") != EXPECTED_REQUEST_SCHEMA:
        add(blockers, "operational_window_request_pack_schema_mismatch", label)
    if payload.get("status") != EXPECTED_REQUEST_STATUS:
        add(blockers, "operational_window_request_pack_status_mismatch", label)
    if payload.get("approval_required") not in (EXPECTED_APPROVAL, STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT):
        add(blockers, "operational_window_request_pack_approval_required_mismatch", label)
    if payload.get("diagnostic_candidates_enabled") is not False:
        add(
            blockers,
            "operational_window_request_pack_diagnostic_candidates_not_allowed",
            label,
            expected=False,
            actual=payload.get("diagnostic_candidates_enabled"),
        )
    expected_values = {
        "run_id": window.get("run_id"),
        "obelisk_commit": window.get("obelisk_commit"),
        "target": window.get("target"),
        "approved_window": window.get("approved_window"),
        "ark_binary_sha256": EXPECTED_BINARY_SHA256,
        "server_binary_path": EXPECTED_SERVER_BINARY_PATH,
        "final_posture": "stable",
    }
    for key, expected in expected_values.items():
        if payload.get(key) != expected:
            add(
                blockers,
                f"operational_window_request_pack_{key}_mismatch",
                label,
                expected=expected,
                actual=payload.get(key),
            )
    if payload.get("restart_expectation") not in {"none", "start", "restart"}:
        add(blockers, "operational_window_request_pack_restart_expectation_invalid", label)
    if payload.get("user_policy") != window.get("user_policy"):
        add(
            blockers,
            "operational_window_request_pack_user_policy_mismatch",
            label,
            expected=window.get("user_policy"),
            actual=payload.get("user_policy"),
        )
    validate_player_notice_action_contract(
        payload.get("player_notice_action"),
        user_policy=payload.get("user_policy"),
        notice_path=payload.get("notice_path"),
        blockers=blockers,
        label=label,
        reason_prefix="operational_window_request_pack",
    )
    validate_player_presence_safety_contract(
        payload.get("player_presence_safety"),
        payload=payload,
        blockers=blockers,
        label=label,
        reason_prefix="operational_window_request_pack",
    )
    expected_paths = {
        "copied_log_path": resolved_artifact_path(window.get("copied_log")),
        "window_manifest_path": resolved_artifact_path(window.get("manifest"), base_dir=base_dir),
    }
    copied_log_path = expected_paths["copied_log_path"]
    if copied_log_path is not None:
        expected_paths["copied_evidence_dir"] = str(Path(copied_log_path).parent)
    for key, expected in expected_paths.items():
        if expected is not None and payload.get(key) != expected:
            add(
                blockers,
                f"operational_window_request_pack_{key}_mismatch",
                label,
                expected=expected,
                actual=payload.get(key),
            )
    rollback = payload.get("rollback")
    if not isinstance(rollback, dict) or rollback.get("delta") != EXPECTED_REQUEST_ROLLBACK_DELTA:
        add(
            blockers,
            "operational_window_request_pack_rollback_delta_mismatch",
            label,
            expected=EXPECTED_REQUEST_ROLLBACK_DELTA,
        )
    contract = payload.get("post_window_replay_contract")
    sidecars = contract.get("sidecars") if isinstance(contract, dict) else None
    if not isinstance(sidecars, dict):
        add(blockers, "operational_window_request_pack_post_window_replay_contract_missing", label)
    else:
        for key in sorted(set(sidecars) - REQUIRED_REQUEST_PACK_REPLAY_SIDECAR_KEYS):
            add(
                blockers,
                "operational_window_request_pack_replay_contract_unexpected_sidecar",
                label,
                sidecar=key,
            )
        request_status = approved_artifact_status(window.get("request_pack"), base_dir=base_dir)
        operator_request_path = (
            str(request_status.resolved.parent / "operator-approval-request.md")
            if request_status is not None
            else None
        )
        expected_sidecars = {
            "request_pack_path": resolved_artifact_path(window.get("request_pack"), base_dir=base_dir),
            "observer_env_path": resolved_artifact_path(window.get("observer_env"), base_dir=base_dir),
            "operator_approval_request_path": operator_request_path,
            "operator_approval_receipt_path": resolved_artifact_path(
                window.get("operator_approval_receipt"),
                base_dir=base_dir,
            ),
            "preflight_pre_path": resolved_artifact_path(
                window.get("preflight", {}).get("pre") if isinstance(window.get("preflight"), dict) else None,
                base_dir=base_dir,
            ),
            "preflight_post_path": resolved_artifact_path(
                window.get("preflight", {}).get("post") if isinstance(window.get("preflight"), dict) else None,
                base_dir=base_dir,
            ),
            "window_manifest_path": resolved_artifact_path(window.get("manifest"), base_dir=base_dir),
            "copied_log_path": resolved_artifact_path(window.get("copied_log")),
        }
        for key, expected in expected_sidecars.items():
            actual = sidecars.get(key)
            if not isinstance(actual, str):
                add(
                    blockers,
                    f"operational_window_request_pack_replay_contract_{key}_mismatch",
                    label,
                    expected=expected,
                    actual=actual,
                )
            elif expected is not None and actual != expected:
                add(
                    blockers,
                    f"operational_window_request_pack_replay_contract_{key}_mismatch",
                    label,
                    expected=expected,
                    actual=sidecars.get(key),
                )
    return payload


def validate_preflight_payload(
    payload: dict[str, Any],
    *,
    label: str,
    window: dict[str, Any],
    expected_mode: str,
    require_env_file: bool,
    blockers: list[dict[str, Any]],
) -> None:
    add_non_evidence_schema_blocker(
        payload,
        blockers,
        reason_prefix=label.strip("$.").replace(".", "_").replace("[", "_").replace("]", ""),
        label=label,
    )
    validate_no_sidecar_overclaims(payload, label, blockers)
    if payload.get("schema") != EXPECTED_PREFLIGHT_SCHEMA:
        add(
            blockers,
            "operational_window_preflight_schema_mismatch",
            label,
            expected=EXPECTED_PREFLIGHT_SCHEMA,
            actual=payload.get("schema"),
        )
    if payload.get("ready") is not True:
        add(blockers, "operational_window_preflight_ready_not_true", label)
    if payload.get("diagnostic_candidates_enabled") is not False:
        add(
            blockers,
            "operational_window_preflight_diagnostic_candidates_not_allowed",
            label,
            expected=False,
            actual=payload.get("diagnostic_candidates_enabled"),
        )
    required_false_flags = getattr(
        window_manifest_checker,
        "PREFLIGHT_REQUIRED_FALSE_AUTHORIZATION_FLAGS",
        frozenset(),
    )
    for key in sorted(required_false_flags):
        if payload.get(key) is not False:
            add(
                blockers,
                f"operational_window_preflight_{key}_not_false",
                label,
                expected=False,
                actual=payload.get(key),
            )
    if payload.get("mode") != expected_mode:
        add(blockers, "operational_window_preflight_mode_mismatch", label, expected=expected_mode, actual=payload.get("mode"))
    target = window.get("target") if isinstance(window.get("target"), dict) else {}
    expected_values = {
        "run_id": window.get("run_id"),
        "instance": target.get("instance"),
        "map": target.get("map"),
        "target": target,
        "window_manifest_path": resolved_artifact_path(
            window.get("manifest"),
            base_dir=operational_window_sidecar_dir(window),
        ),
        "copied_log_path": resolved_artifact_path(window.get("copied_log")),
    }
    copied_log_path = expected_values["copied_log_path"]
    if copied_log_path is not None:
        expected_values["copied_evidence_dir"] = str(Path(copied_log_path).parent)
    for key, expected in expected_values.items():
        if expected is not None and payload.get(key) != expected:
            add(
                blockers,
                f"operational_window_preflight_{key}_mismatch",
                label,
                expected=expected,
                actual=payload.get(key),
            )
    server_binary = payload.get("server_binary")
    if not isinstance(server_binary, dict):
        add(blockers, "operational_window_preflight_server_binary_missing", label)
    else:
        if server_binary.get("path") != EXPECTED_SERVER_BINARY_PATH:
            add(blockers, "operational_window_preflight_server_binary_path_mismatch", label)
        if server_binary.get("sha256") != EXPECTED_BINARY_SHA256:
            add(blockers, "operational_window_preflight_server_binary_sha256_mismatch", label)
    env_file = payload.get("env_file")
    if require_env_file:
        observer_env = window.get("observer_env") if isinstance(window.get("observer_env"), dict) else {}
        expected_env_file = {
            "path": resolved_artifact_path(observer_env, base_dir=operational_window_sidecar_dir(window)),
            "sha256": observer_env.get("sha256"),
        }
        if env_file != expected_env_file:
            add(
                blockers,
                "operational_window_preflight_env_file_mismatch",
                label,
                expected=expected_env_file,
                actual=env_file,
            )
    elif env_file is not None:
        add(blockers, "operational_window_preflight_post_env_file_not_none", label, actual=env_file)
    checked_at_utc = payload.get("checked_at_utc")
    if not isinstance(checked_at_utc, str) or UTC_TIMESTAMP_RE.fullmatch(checked_at_utc) is None:
        add(blockers, "operational_window_preflight_checked_at_utc_invalid", label)
    else:
        checked_at_dt = parse_utc_timestamp(checked_at_utc)
        if checked_at_dt is None:
            add(blockers, "operational_window_preflight_checked_at_utc_invalid", label)
        elif checked_at_dt > now_utc():
            add(
                blockers,
                "operational_window_preflight_checked_at_utc_in_future",
                label,
                checked_at_utc=checked_at_utc,
            )
    if payload.get("posture_check") != "accepted":
        add(blockers, "operational_window_preflight_posture_check_mismatch", label)
    if payload.get("non_claim") != EXPECTED_PREFLIGHT_NON_CLAIM:
        add(
            blockers,
            "operational_window_preflight_non_claim_mismatch",
            label,
            expected=EXPECTED_PREFLIGHT_NON_CLAIM,
            actual=payload.get("non_claim"),
        )


def validate_preflight_bindings(window: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    preflight = window.get("preflight")
    if not isinstance(preflight, dict):
        return
    base_dir = operational_window_sidecar_dir(window)
    pre_payload = load_json_artifact(
        preflight.get("pre"),
        "$.operational_window.preflight.pre.path",
        blockers,
        base_dir=base_dir,
    )
    post_payload = load_json_artifact(
        preflight.get("post"),
        "$.operational_window.preflight.post.path",
        blockers,
        base_dir=base_dir,
    )
    if pre_payload is not None:
        validate_preflight_payload(
            pre_payload,
            label="$.operational_window.preflight.pre.path",
            window=window,
            expected_mode="observer-window",
            require_env_file=True,
            blockers=blockers,
        )
    if post_payload is not None:
        validate_preflight_payload(
            post_payload,
            label="$.operational_window.preflight.post.path",
            window=window,
            expected_mode="stable",
            require_env_file=False,
            blockers=blockers,
        )


def operator_request_sidecar_artifact(
    window: dict[str, Any],
    *,
    base_dir: Path | None = None,
) -> dict[str, Any] | None:
    request_status = approved_artifact_status(window.get("request_pack"), base_dir=base_dir)
    if request_status is None:
        return None
    operator_request_path = request_status.resolved.parent / "operator-approval-request.md"
    if first_symlink_component(operator_request_path) is not None:
        return None
    operator_request_status = protected_paths.protected_path_status(
        operator_request_path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if operator_request_status.protected or not operator_request_status.approved_offline_workspace:
        return None
    return bound_artifact_from_status(operator_request_status)


def load_operator_approval_receipt_payload(
    window: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    receipt = window.get("operator_approval_receipt")
    base_dir = operational_window_sidecar_dir(window)
    if not isinstance(receipt, dict):
        artifact_status_for_read(
            receipt,
            "$.operational_window.operator_approval_receipt.path",
            blockers,
            base_dir=base_dir,
        )
        return None
    if receipt.get("verified") is not True:
        add(
            blockers,
            "operational_window_operator_approval_receipt_verified_not_true",
            "$.operational_window.operator_approval_receipt.verified",
        )
    status = artifact_status_for_read(
        receipt,
        "$.operational_window.operator_approval_receipt.path",
        blockers,
        base_dir=base_dir,
    )
    if status is None:
        return None
    try:
        payload = json.loads(status.resolved.read_text(encoding="utf-8"))
    except OSError as exc:
        add(
            blockers,
            "operational_window_operator_approval_receipt_unreadable",
            "$.operational_window.operator_approval_receipt.path",
            error=str(exc),
        )
        return None
    except json.JSONDecodeError as exc:
        add(
            blockers,
            "operational_window_operator_approval_receipt_json_invalid",
            "$.operational_window.operator_approval_receipt.path",
            error=str(exc),
        )
        return None
    if not isinstance(payload, dict):
        add(
            blockers,
            "operational_window_operator_approval_receipt_not_object",
            "$.operational_window.operator_approval_receipt.path",
        )
        return None
    return payload


def validate_operator_approval_receipt_binding(
    window: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    base_dir = operational_window_sidecar_dir(window)
    payload = load_operator_approval_receipt_payload(window, blockers)
    if payload is None:
        return
    add_non_evidence_schema_blocker(
        payload,
        blockers,
        reason_prefix="operational_window_operator_approval_receipt",
        label="$.operational_window.operator_approval_receipt.path",
    )
    validate_no_sidecar_overclaims(payload, "$.operational_window.operator_approval_receipt.path", blockers)

    if payload.get("schema") != EXPECTED_OPERATOR_APPROVAL_RECEIPT_SCHEMA:
        add(
            blockers,
            "operational_window_operator_approval_receipt_schema_mismatch",
            "$.operational_window.operator_approval_receipt.path",
        )
    if payload.get("status") != "completed_operator_receipt":
        add(
            blockers,
            "operational_window_operator_approval_receipt_status_not_completed",
            "$.operational_window.operator_approval_receipt.path",
        )
    if payload.get("receipt_completed") is not True:
        add(
            blockers,
            "operational_window_operator_approval_receipt_receipt_completed_not_true",
            "$.operational_window.operator_approval_receipt.path",
        )
    if payload.get("non_claims") != EXPECTED_OPERATOR_APPROVAL_RECEIPT_NON_CLAIMS:
        add(
            blockers,
            "operational_window_operator_approval_receipt_non_claims_mismatch",
            "$.operational_window.operator_approval_receipt.path",
        )

    completion = payload.get("operator_completion")
    if not isinstance(completion, dict):
        add(
            blockers,
            "operational_window_operator_approval_receipt_completion_missing",
            "$.operational_window.operator_approval_receipt.path",
        )
        completion = {}
    if not isinstance(completion.get("approval_recorded_at_utc"), str) or UTC_TIMESTAMP_RE.fullmatch(
        completion.get("approval_recorded_at_utc", "")
    ) is None:
        add(
            blockers,
            "operational_window_operator_approval_receipt_approved_at_utc_invalid",
            "$.operational_window.operator_approval_receipt.path",
        )
        approved_at_dt = None
    else:
        approved_at = completion["approval_recorded_at_utc"]
        approved_at_dt = parse_utc_timestamp(approved_at)
        if approved_at_dt is None:
            add(
                blockers,
                "operational_window_operator_approval_receipt_approved_at_utc_invalid",
                "$.operational_window.operator_approval_receipt.path",
            )
        elif approved_at_dt > now_utc():
            add(
                blockers,
                "operational_window_operator_approval_receipt_approved_at_utc_in_future",
                "$.operational_window.operator_approval_receipt.path",
                approval_recorded_at_utc=approved_at,
            )
    approved_by_role = completion.get("approved_by_role")
    if not isinstance(approved_by_role, str) or not approved_by_role.strip():
        add(
            blockers,
            "operational_window_operator_approval_receipt_approved_by_role_invalid",
            "$.operational_window.operator_approval_receipt.path",
        )
    elif approved_by_role not in APPROVED_OPERATOR_ROLES:
        add(
            blockers,
            "operational_window_operator_approval_receipt_approved_by_role_unapproved",
            "$.operational_window.operator_approval_receipt.path",
            accepted_roles=sorted(APPROVED_OPERATOR_ROLES),
            actual=approved_by_role,
        )
    approval_source = completion.get("approval_source")
    if approval_source not in (APPROVAL_SOURCE_CURRENT_TURN, APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY):
        add(
            blockers,
            "operational_window_operator_approval_receipt_approval_source_mismatch",
            "$.operational_window.operator_approval_receipt.path",
        )
    standing_receipt = approval_source == APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY
    if standing_receipt:
        if payload.get("operator_current_turn_approval_recorded") is not False:
            add(
                blockers,
                "operational_window_operator_approval_receipt_current_turn_approval_not_false_for_standing_authority",
                "$.operational_window.operator_approval_receipt.path",
            )
        if payload.get("standing_launch_authority_recorded") is not True:
            add(
                blockers,
                "operational_window_operator_approval_receipt_standing_launch_authority_not_recorded",
                "$.operational_window.operator_approval_receipt.path",
            )
        if payload.get("standing_launch_authority_satisfies_operator_approval") is not True:
            add(
                blockers,
                "operational_window_operator_approval_receipt_standing_launch_authority_not_bound",
                "$.operational_window.operator_approval_receipt.path",
            )
    else:
        if payload.get("operator_current_turn_approval_recorded") is not True:
            add(
                blockers,
                "operational_window_operator_approval_receipt_operator_current_turn_approval_recorded_not_true",
                "$.operational_window.operator_approval_receipt.path",
            )
        if payload.get("standing_launch_authority_recorded") is not False:
            add(
                blockers,
                "operational_window_operator_approval_receipt_standing_launch_authority_not_false_for_current_turn",
                "$.operational_window.operator_approval_receipt.path",
            )
        if payload.get("standing_launch_authority_satisfies_operator_approval") is not False:
            add(
                blockers,
                "operational_window_operator_approval_receipt_standing_launch_authority_bound_for_current_turn",
                "$.operational_window.operator_approval_receipt.path",
            )
    expected_attestation = (
        APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY
        if standing_receipt
        else APPROVAL_ATTESTATION_CURRENT_TURN
    )
    if completion.get("attestation") != expected_attestation:
        add(
            blockers,
            "operational_window_operator_approval_receipt_attestation_mismatch",
            "$.operational_window.operator_approval_receipt.path",
        )

    scope = payload.get("approval_scope")
    if not isinstance(scope, dict):
        add(
            blockers,
            "operational_window_operator_approval_receipt_scope_missing",
            "$.operational_window.operator_approval_receipt.path",
        )
        scope = {}
    if approval_source == APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY:
        if scope.get("standing_approval") is not True:
            add(
                blockers,
                "operational_window_operator_approval_receipt_scope_standing_approval_not_true",
                "$.operational_window.operator_approval_receipt.path",
            )
    elif scope.get("standing_approval") is not False:
        add(
            blockers,
            "operational_window_operator_approval_receipt_scope_standing_approval_not_false",
            "$.operational_window.operator_approval_receipt.path",
        )
    for key in OPERATOR_APPROVAL_RECEIPT_SCOPE_FALSE_FLAGS:
        if key == "standing_approval":
            continue
        if scope.get(key) is not False:
            add(
                blockers,
                f"operational_window_operator_approval_receipt_scope_{key}_not_false",
                "$.operational_window.operator_approval_receipt.path",
            )

    flags = payload.get("non_authorization_flags")
    if not isinstance(flags, dict):
        add(
            blockers,
            "operational_window_operator_approval_receipt_non_authorization_flags_missing",
            "$.operational_window.operator_approval_receipt.path",
        )
        flags = {}
    for key in OPERATOR_APPROVAL_RECEIPT_NON_AUTHORIZATION_FLAGS:
        if flags.get(key) is not False:
            add(
                blockers,
                f"operational_window_operator_approval_receipt_{key}_not_false",
                "$.operational_window.operator_approval_receipt.path",
            )

    bound_request = payload.get("bound_request_pack")
    if not isinstance(bound_request, dict):
        add(
            blockers,
            "operational_window_operator_approval_receipt_bound_request_pack_missing",
            "$.operational_window.operator_approval_receipt.path",
        )
        bound_request = {}
    expected_bound_values = {
        "run_id": window.get("run_id"),
        "obelisk_commit": window.get("obelisk_commit"),
        "target": window.get("target"),
        "approved_window": window.get("approved_window"),
        "user_policy": window.get("user_policy"),
        "copied_log_path": resolved_artifact_path(window.get("copied_log")),
        "window_manifest_path": resolved_artifact_path(window.get("manifest"), base_dir=base_dir),
    }
    for key, expected in expected_bound_values.items():
        if expected is not None and bound_request.get(key) != expected:
            add(
                blockers,
                f"operational_window_operator_approval_receipt_bound_request_{key}_mismatch",
                "$.operational_window.operator_approval_receipt.path",
                expected=expected,
                actual=bound_request.get(key),
            )
    validate_player_notice_action_contract(
        bound_request.get("player_notice_action"),
        user_policy=bound_request.get("user_policy"),
        notice_path=bound_request.get("notice_path"),
        blockers=blockers,
        label="$.operational_window.operator_approval_receipt.path",
        reason_prefix="operational_window_operator_approval_receipt_bound_request",
    )
    validate_player_presence_safety_contract(
        bound_request.get("player_presence_safety"),
        payload=bound_request,
        blockers=blockers,
        label="$.operational_window.operator_approval_receipt.path",
        reason_prefix="operational_window_operator_approval_receipt_bound_request",
    )

    approved_window = window.get("approved_window")
    if isinstance(approved_window, dict) and approved_at_dt is not None:
        approved_start = (
            parse_utc_timestamp(approved_window["start_utc"])
            if isinstance(approved_window.get("start_utc"), str)
            and UTC_TIMESTAMP_RE.fullmatch(approved_window["start_utc"])
            else None
        )
        approved_end = (
            parse_utc_timestamp(approved_window["end_utc"])
            if isinstance(approved_window.get("end_utc"), str)
            and UTC_TIMESTAMP_RE.fullmatch(approved_window["end_utc"])
            else None
        )
        if approved_start is not None and approved_at_dt >= approved_start:
            add(
                blockers,
                "operational_window_operator_approval_receipt_approved_at_or_after_window_start",
                "$.operational_window.operator_approval_receipt.path",
                approval_recorded_at_utc=completion.get("approval_recorded_at_utc"),
                approved_window_start_utc=approved_window.get("start_utc"),
            )
        if approved_end is not None and approved_at_dt >= approved_end:
            add(
                blockers,
                "operational_window_operator_approval_receipt_approved_at_or_after_window_end",
                "$.operational_window.operator_approval_receipt.path",
                approval_recorded_at_utc=completion.get("approval_recorded_at_utc"),
                approved_window_end_utc=approved_window.get("end_utc"),
            )

    bound_artifacts = payload.get("bound_artifacts")
    if not isinstance(bound_artifacts, dict):
        add(
            blockers,
            "operational_window_operator_approval_receipt_bound_artifacts_missing",
            "$.operational_window.operator_approval_receipt.path",
        )
        return
    expected_artifacts = {
        "window_request_json": bound_artifact_from_status(status)
        if (status := approved_artifact_status(window.get("request_pack"), base_dir=base_dir)) is not None
        else None,
        "observer_window_env": bound_artifact_from_status(status)
        if (status := approved_artifact_status(window.get("observer_env"), base_dir=base_dir)) is not None
        else None,
        "operator_approval_request_md": operator_request_sidecar_artifact(window, base_dir=base_dir),
    }
    for key, expected in expected_artifacts.items():
        if expected is not None and bound_artifacts.get(key) != expected:
            add(
                blockers,
                f"operational_window_operator_approval_receipt_{key}_artifact_mismatch",
                "$.operational_window.operator_approval_receipt.path",
                expected=expected,
                actual=bound_artifacts.get(key),
            )

    request_status = approved_artifact_status(window.get("request_pack"), base_dir=base_dir)
    observer_env_status = approved_artifact_status(window.get("observer_env"), base_dir=base_dir)
    operator_request = operator_request_sidecar_artifact(window, base_dir=base_dir)
    if request_status is not None and observer_env_status is not None and operator_request is not None:
        try:
            expected_digest = request_pack_digest(
                request_json_path=request_status.resolved,
                request_md_path=Path(operator_request["path"]),
                env_path=observer_env_status.resolved,
            )
        except OSError as exc:
            add(
                blockers,
                "operational_window_operator_approval_receipt_digest_unreadable",
                "$.operational_window.operator_approval_receipt.path",
                error=str(exc),
            )
        else:
            if payload.get("request_pack_digest") != expected_digest:
                add(
                    blockers,
                    "operational_window_operator_approval_receipt_digest_mismatch",
                    "$.operational_window.operator_approval_receipt.path",
                    expected=expected_digest,
                    actual=payload.get("request_pack_digest"),
                )


def replay_operational_window_manifest(window: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    manifest = window.get("manifest")
    path_text = manifest.get("path") if isinstance(manifest, dict) else None
    if not isinstance(path_text, str) or not path_text:
        return

    manifest_path = path_from_text(path_text, base_dir=operational_window_sidecar_dir(window))
    old_window_server_root = window_manifest_checker.SERVER_ROOT
    old_window_roots = window_manifest_checker.APPROVED_OFFLINE_WORKSPACE_ROOTS
    old_receipt_bound_request_keys = getattr(
        window_manifest_checker,
        "EXPECTED_OPERATOR_APPROVAL_RECEIPT_BOUND_REQUEST_KEYS",
        None,
    )
    old_request_pack_top_level_keys = getattr(
        window_manifest_checker,
        "EXPECTED_REQUEST_PACK_TOP_LEVEL_KEYS",
        None,
    )
    window_manifest_checker.SERVER_ROOT = SERVER_ROOT
    window_manifest_checker.APPROVED_OFFLINE_WORKSPACE_ROOTS = APPROVED_OFFLINE_WORKSPACE_ROOTS
    if isinstance(old_receipt_bound_request_keys, frozenset):
        window_manifest_checker.EXPECTED_OPERATOR_APPROVAL_RECEIPT_BOUND_REQUEST_KEYS = (
            old_receipt_bound_request_keys
            | {
                "planned_obelisk_build_identity",
                "player_notice_action",
                "direct_join_plan",
                "player_presence_safety",
            }
        )
    if isinstance(old_request_pack_top_level_keys, frozenset):
        window_manifest_checker.EXPECTED_REQUEST_PACK_TOP_LEVEL_KEYS = (
            old_request_pack_top_level_keys | {"direct_join_plan"}
        )
    try:
        try:
            fields = window_manifest_checker.load_manifest(manifest_path)
            validation = window_manifest_checker.validate_manifest(
                fields,
                manifest_path,
                post_window_replay=True,
            )
        except (OSError, SystemExit) as exc:
            add(
                blockers,
                "operational_window_manifest_check_failed",
                "$.operational_window.manifest.path",
                error=str(exc),
            )
            return
    finally:
        window_manifest_checker.SERVER_ROOT = old_window_server_root
        window_manifest_checker.APPROVED_OFFLINE_WORKSPACE_ROOTS = old_window_roots
        if old_receipt_bound_request_keys is not None:
            window_manifest_checker.EXPECTED_OPERATOR_APPROVAL_RECEIPT_BOUND_REQUEST_KEYS = (
                old_receipt_bound_request_keys
            )
        if old_request_pack_top_level_keys is not None:
            window_manifest_checker.EXPECTED_REQUEST_PACK_TOP_LEVEL_KEYS = (
                old_request_pack_top_level_keys
            )

    if validation.blockers:
        add(
            blockers,
            "operational_window_manifest_check_failed",
            "$.operational_window.manifest",
            replay_blockers=[blocker["reason"] for blocker in validation.blockers],
            replay_blocker_details=validation.blockers,
        )

    replay_report = window_manifest_checker.build_report(
        fields,
        validation,
        manifest_path,
        post_window_replay=True,
    )
    replay_projection = {
        key: replay_report.get(key)
        for key in OPERATIONAL_WINDOW_REPLAY_KEYS
    }
    embedded_projection = {
        key: window.get(key)
        for key in OPERATIONAL_WINDOW_REPLAY_KEYS
    }
    if canonical_json_bytes(replay_projection) != canonical_json_bytes(embedded_projection):
        add(
            blockers,
            "operational_window_manifest_replay_mismatch",
            "$.operational_window",
        )


def expected_summary_from_copied_source(
    evidence: dict[str, Any],
    source: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    path_text = source.get("path")
    if not isinstance(path_text, str) or not path_text:
        return None
    if symlink_component_for_path_text(path_text) is not None:
        return None
    status = protected_paths.protected_path_status(
        Path(path_text).expanduser(),
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected or not status.approved_offline_workspace:
        return None
    try:
        text = status.resolved.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        add(
            blockers,
            "source_summary_source_file_unreadable",
            "$.source_summary.evidence.sources[0].path",
            error=str(exc),
        )
        return None

    lines = text.splitlines()
    validate_copied_log_has_no_passive_monitor_metadata(lines, blockers)
    validate_copied_log_has_no_unsafe_player_text(lines, blockers)
    validate_copied_log_has_no_diagnostic_lifecycle_lines(lines, blockers)
    summary = runtime_observer_analyzer.analyze_source_lines([lines])
    summary["evidence"] = {
        "kind": "runtime-observer-log",
        "obelisk_commit": evidence.get("obelisk_commit"),
        "sources": [
            {
                "path": str(status.resolved),
                "sha256": sha256_file(status.resolved),
                "line_count": len(lines),
            }
        ],
        "server_paths_allowed": False,
    }
    return summary


def player_principal_lifecycle_module(summary: Any) -> dict[str, Any] | None:
    if not isinstance(summary, dict):
        return None
    modules = summary.get("modules")
    if not isinstance(modules, dict):
        return None
    module = modules.get(MODULE)
    return module if isinstance(module, dict) else None


def positive_int_counts(values: Any) -> dict[str, int]:
    if not isinstance(values, dict):
        return {}
    return {
        str(key): value
        for key, value in values.items()
        if isinstance(value, int) and value > 0
    }


def positive_int(value: Any) -> bool:
    return isinstance(value, int) and value > 0


def positive_count_map(value: Any) -> bool:
    return bool(positive_int_counts(value))


def nonempty_json_collection(value: Any) -> bool:
    return isinstance(value, (dict, list)) and bool(value)


def session_end_missing_correlation_diagnostics_from_module(
    module: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(module, dict):
        return None
    unsafe_reasons = {
        **positive_int_counts(module.get("unsafe_lifecycle_event_reasons")),
        **positive_int_counts(module.get("invalid_lifecycle_event_non_evidence_reasons")),
    }
    reason_keys = set(unsafe_reasons)
    missing_correlation_keys = reason_keys & SESSION_END_MISSING_CORRELATION_REASON_KEYS
    if not missing_correlation_keys:
        return None
    accepted_count = module.get("accepted_count")
    if accepted_count is None:
        accepted_count = module.get("accepted_lifecycle_event_count")
    observed_cases = module.get("observed_event_cases")
    only_missing_correlation_logout = (
        accepted_count == 0
        and observed_cases in (None, [])
        and reason_keys.issubset(SESSION_END_MISSING_CORRELATION_REASON_KEYS)
    )
    if not only_missing_correlation_logout:
        return None
    return {
        "classification": "session_end_missing_correlation_only_non_evidence",
        "copied_log_material": "session_end_only_without_matched_correlation",
        "accepted_lifecycle_event_count": accepted_count,
        "malformed_observer_lines": module.get("malformed_observer_lines"),
        "unsafe_lifecycle_event_reasons": {
            key: unsafe_reasons[key] for key in sorted(missing_correlation_keys)
        },
        "roles_present": ["session_end"],
        "missing_accepted_lifecycle_roles": list(READY_LOG_COPY_REQUIRED_ROLES),
        "required_next_material": {
            "same_run_exact_triplet_required": True,
            "required_roles": list(READY_LOG_COPY_REQUIRED_ROLES),
            "required_session_end_status_proof": {
                "apply_status": "session_end_invalidated",
                "correlation_status": "matched",
            },
            "session_end_correlation_status_missing_counts_as_evidence": False,
        },
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
    }


def session_end_missing_correlation_diagnostics_from_summary(
    summary: Any,
) -> dict[str, Any] | None:
    return session_end_missing_correlation_diagnostics_from_module(
        player_principal_lifecycle_module(summary)
    )


def diagnostic_material_present(module: dict[str, Any]) -> bool:
    diagnostic_reason_counts = module.get("diagnostic_candidate_reason_counts")
    diagnostic_read_status_counts = module.get("diagnostic_candidate_read_status_counts")
    diagnostic_target_counts = module.get("diagnostic_candidate_target_counts")
    diagnostic_count = module.get("diagnostic_candidate_count")
    return (
        (isinstance(diagnostic_count, int) and diagnostic_count > 0)
        or (isinstance(diagnostic_reason_counts, dict) and bool(diagnostic_reason_counts))
        or (isinstance(diagnostic_read_status_counts, dict) and bool(diagnostic_read_status_counts))
        or (isinstance(diagnostic_target_counts, dict) and bool(diagnostic_target_counts))
        or diagnostic_check_join_context_present(module)
        or diagnostic_lifecycle_property_fname_mismatch_present(module)
        or diagnostic_lifecycle_property_fname_drift_present(module)
        or diagnostic_property_fname_chain_present(module)
        or diagnostic_guardrails_present(module)
    )


def diagnostic_reason_counts_for_prefix(module: dict[str, Any], prefix: str) -> dict[str, int]:
    reason_counts = module.get("diagnostic_candidate_reason_counts")
    if not isinstance(reason_counts, dict):
        return {}
    return {
        str(reason): count
        for reason, count in reason_counts.items()
        if isinstance(reason, str)
        and reason.startswith(prefix)
        and isinstance(count, int)
        and count > 0
    }


def diagnostic_check_join_context_present(module: dict[str, Any]) -> bool:
    summary = module.get("diagnostic_check_join_in_progress_summary")
    if not isinstance(summary, dict):
        return False
    return (
        positive_int(summary.get("count"))
        or positive_int(summary.get("strict_shape_candidate_count"))
        or positive_int(summary.get("strict_shape_copy_rejected_count"))
        or positive_count_map(summary.get("shape_counts"))
        or positive_count_map(summary.get("accepted_lifecycle_target_counts"))
        or positive_count_map(summary.get("reflection_status_counts"))
        or positive_count_map(summary.get("copy_status_counts"))
        or summary.get("latest_strict_shape_candidate") is not None
    )


def diagnostic_lifecycle_property_fname_mismatch_present(module: dict[str, Any]) -> bool:
    mismatch_entries = module.get("diagnostic_candidate_lifecycle_property_fname_mismatches")
    summary = module.get("diagnostic_lifecycle_property_fname_mismatch_summary")
    target_summary = module.get("diagnostic_lifecycle_property_fname_mismatch_target_summary")
    summary_present = (
        isinstance(summary, dict)
        and (
            positive_int(summary.get("count"))
            or nonempty_json_collection(summary.get("patterns"))
        )
    )
    target_summary_present = (
        isinstance(target_summary, dict)
        and (
            positive_int(target_summary.get("count"))
            or positive_int(target_summary.get("target_count"))
            or nonempty_json_collection(target_summary.get("targets"))
        )
    )
    return (
        nonempty_json_collection(mismatch_entries)
        or summary_present
        or target_summary_present
        or bool(
            diagnostic_reason_counts_for_prefix(
                module,
                "lifecycle_property_FName_mismatch",
            )
        )
    )


def diagnostic_lifecycle_property_fname_drift_present(module: dict[str, Any]) -> bool:
    return (
        positive_int(module.get("diagnostic_candidate_rejected_drift_count"))
        or positive_count_map(module.get("diagnostic_candidate_rejected_drift_target_counts"))
        or nonempty_json_collection(module.get("diagnostic_candidate_latest_rejected_drift_by_target"))
        or bool(
            diagnostic_reason_counts_for_prefix(
                module,
                "lifecycle_property_FName_drift",
            )
        )
    )


def diagnostic_property_fname_chain_present(module: dict[str, Any]) -> bool:
    metadata = module.get("diagnostic_candidate_property_fname_chain_metadata")
    if not isinstance(metadata, dict):
        return False
    return (
        positive_int(metadata.get("count"))
        or positive_int(metadata.get("chain_count"))
        or nonempty_json_collection(metadata.get("entries"))
    )


def diagnostic_guardrails_present(module: dict[str, Any]) -> bool:
    guardrails = module.get("diagnostic_candidate_guardrails")
    return isinstance(guardrails, list) and bool(guardrails)


def add_runtime_summary_diagnostic_context_blockers(
    module: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    if diagnostic_check_join_context_present(module):
        add(
            blockers,
            "runtime_summary_check_join_in_progress_diagnostic_context_not_approved_lifecycle_evidence",
            f"$.source_summary.modules.{MODULE}.diagnostic_check_join_in_progress_summary",
            diagnostic_check_join_in_progress_summary=module.get(
                "diagnostic_check_join_in_progress_summary"
            ),
        )
    if diagnostic_lifecycle_property_fname_mismatch_present(module):
        add(
            blockers,
            "runtime_summary_lifecycle_property_fname_mismatch_not_approved_lifecycle_evidence",
            f"$.source_summary.modules.{MODULE}.diagnostic_lifecycle_property_fname_mismatch_summary",
            diagnostic_lifecycle_property_fname_mismatch_summary=module.get(
                "diagnostic_lifecycle_property_fname_mismatch_summary"
            ),
            diagnostic_lifecycle_property_fname_mismatch_target_summary=module.get(
                "diagnostic_lifecycle_property_fname_mismatch_target_summary"
            ),
            diagnostic_reason_counts=diagnostic_reason_counts_for_prefix(
                module,
                "lifecycle_property_FName_mismatch",
            ),
        )
    if diagnostic_lifecycle_property_fname_drift_present(module):
        add(
            blockers,
            "runtime_summary_lifecycle_property_fname_drift_not_approved_lifecycle_evidence",
            f"$.source_summary.modules.{MODULE}.diagnostic_candidate_rejected_drift_count",
            diagnostic_candidate_rejected_drift_count=module.get(
                "diagnostic_candidate_rejected_drift_count"
            ),
            diagnostic_candidate_rejected_drift_target_counts=module.get(
                "diagnostic_candidate_rejected_drift_target_counts"
            ),
            diagnostic_candidate_latest_rejected_drift_by_target=module.get(
                "diagnostic_candidate_latest_rejected_drift_by_target"
            ),
            diagnostic_reason_counts=diagnostic_reason_counts_for_prefix(
                module,
                "lifecycle_property_FName_drift",
            ),
        )
    if diagnostic_property_fname_chain_present(module):
        add(
            blockers,
            "runtime_summary_diagnostic_property_fname_chain_not_approved_lifecycle_evidence",
            f"$.source_summary.modules.{MODULE}.diagnostic_candidate_property_fname_chain_metadata",
            diagnostic_candidate_property_fname_chain_metadata=module.get(
                "diagnostic_candidate_property_fname_chain_metadata"
            ),
        )
    if diagnostic_guardrails_present(module):
        add(
            blockers,
            "runtime_summary_diagnostic_guardrail_not_approved_lifecycle_evidence",
            f"$.source_summary.modules.{MODULE}.diagnostic_candidate_guardrails",
            diagnostic_candidate_guardrails=module.get("diagnostic_candidate_guardrails"),
        )


def add_diagnostic_candidate_blocker(
    blockers: list[dict[str, Any]],
    reason: str,
    label: str,
    module: dict[str, Any],
) -> None:
    add(
        blockers,
        reason,
        label,
        expected_lifecycle_event_count=len(REQUIRED_OBSERVED_EVENT_CASES),
        observed_lifecycle_event_count=module.get("accepted_count"),
        diagnostic_candidate_count=module.get("diagnostic_candidate_count"),
        diagnostic_target_counts=module.get("diagnostic_candidate_target_counts"),
        diagnostic_reason_counts=module.get("diagnostic_candidate_reason_counts"),
        diagnostic_read_status_counts=module.get("diagnostic_candidate_read_status_counts"),
    )


def validate_copied_log_has_no_diagnostic_candidates(
    expected: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    module = player_principal_lifecycle_module(expected)
    if module is None or not diagnostic_material_present(module):
        return
    add_diagnostic_candidate_blocker(
        blockers,
        "source_summary_copied_log_contains_diagnostic_candidates",
        "$.source_summary.evidence.sources[0].path",
        module,
    )


def validate_copied_log_not_diagnostic_only(expected: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    module = player_principal_lifecycle_module(expected)
    if module is None or not diagnostic_material_present(module):
        return
    accepted_count = module.get("accepted_count")
    if accepted_count == len(REQUIRED_OBSERVED_EVENT_CASES):
        return
    add_diagnostic_candidate_blocker(
        blockers,
        "source_summary_copied_log_diagnostic_only_not_approved_lifecycle_evidence",
        "$.source_summary.evidence.sources[0].path",
        module,
    )


def validate_copied_log_has_no_passive_monitor_metadata(
    lines: list[str],
    blockers: list[dict[str, Any]],
) -> None:
    passive_lines = [
        {"line": line_number, "prefix": line.strip().split(" ", 1)[0]}
        for line_number, line in enumerate(lines, start=1)
        if PASSIVE_MONITOR_METADATA_RE.match(line.strip())
    ]
    if passive_lines:
        add(
            blockers,
            "source_summary_copied_log_contains_passive_monitor_metadata",
            "$.source_summary.evidence.sources[0].path",
            passive_monitor_lines=passive_lines[:10],
            passive_monitor_line_count=len(passive_lines),
        )


def validate_copied_log_has_no_unsafe_player_text(
    lines: list[str],
    blockers: list[dict[str, Any]],
) -> None:
    unsafe_lines: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        unsafe_keys = sorted(
            {
                key
                for key, _value in LOG_KEY_VALUE_RE.findall(line)
                if key not in COPIED_LOG_ALLOWED_PRIVACY_KEYS and COPIED_LOG_UNSAFE_KEY_RE.fullmatch(key)
            }
        )
        text_match = COPIED_LOG_UNSAFE_TEXT_RE.search(line)
        if not unsafe_keys and text_match is None:
            continue
        line_detail: dict[str, Any] = {"line": line_number}
        if unsafe_keys:
            line_detail["unsafe_keys"] = unsafe_keys
        if text_match is not None:
            line_detail["unsafe_text_indicator"] = text_match.group(0)
        unsafe_lines.append(line_detail)

    if unsafe_lines:
        add(
            blockers,
            "source_summary_copied_log_contains_unsafe_player_text",
            "$.source_summary.evidence.sources[0].path",
            unsafe_player_text_lines=unsafe_lines[:10],
            unsafe_player_text_line_count=len(unsafe_lines),
        )


def validate_copied_log_has_no_diagnostic_lifecycle_lines(
    lines: list[str],
    blockers: list[dict[str, Any]],
) -> None:
    diagnostic_lines = [
        {"line": line_number, "indicator": "PlayerPrincipalLifecycleDiagnostic"}
        for line_number, line in enumerate(lines, start=1)
        if "PlayerPrincipalLifecycleDiagnostic " in line
    ]
    if diagnostic_lines:
        add(
            blockers,
            "source_summary_copied_log_contains_diagnostic_lifecycle_lines",
            "$.source_summary.evidence.sources[0].path",
            diagnostic_lifecycle_lines=diagnostic_lines[:10],
            diagnostic_lifecycle_line_count=len(diagnostic_lines),
        )


def copied_log_lifecycle_event_case(line: str) -> dict[str, Any] | None:
    match = runtime_observer_analyzer.PLAYER_PRINCIPAL_LIFECYCLE_EVENT_RE.search(line)
    if match is None:
        return None
    copied_bool_fields = runtime_observer_analyzer.csv_values(
        match.group("copied_bool_fields"),
        allowed={"bIsFromLogin", "ReturnValue"},
    )
    copied_bool_values = runtime_observer_analyzer.csv_values(
        match.group("copied_bool_values"),
        allowed={"0", "1"},
        allow_duplicates=True,
    )
    if copied_bool_fields is None or copied_bool_values is None:
        return None
    return {
        "target": match.group("target"),
        "role": match.group("role"),
        "copied_bool_fields": copied_bool_fields,
        "copied_bool_values": copied_bool_values,
        "principal_action": match.group("principal_action"),
        "apply_status": match.group("apply_status"),
        "correlation_status": match.group("correlation_status"),
    }


def copied_log_lifecycle_event_detail_values(line: str) -> dict[str, Any] | None:
    match = runtime_observer_analyzer.PLAYER_PRINCIPAL_LIFECYCLE_EVENT_RE.search(line)
    if match is None:
        return None
    return {
        "role": match.group("role"),
        "post_original": match.group("post_original"),
        "copied_bool_fields": match.group("copied_bool_fields"),
        "copied_bool_values": match.group("copied_bool_values"),
        "redacted_count": int(match.group("redacted_count")),
        "redacted_fields": match.group("redacted_fields"),
        "principal_action": match.group("principal_action"),
        "apply_status": match.group("apply_status"),
        "correlation_status": match.group("correlation_status"),
        "principal_id_logged": match.group("principal_id_logged"),
        "principal_generation_logged": match.group("principal_generation_logged"),
        "delivery_claim": match.group("delivery_claim"),
    }


def copied_log_lifecycle_event_full_shape_mismatches(line: str) -> dict[str, dict[str, Any]]:
    match = runtime_observer_analyzer.PLAYER_PRINCIPAL_LIFECYCLE_EVENT_RE.search(line)
    if match is None:
        return {}
    details = copied_log_lifecycle_event_detail_values(line)
    expected = EXPECTED_DETAIL_VALUES.get(match.group("target"))
    if details is None or expected is None:
        return {}
    mismatches: dict[str, dict[str, Any]] = {}
    for key, expected_values in expected.items():
        if key == "target_set":
            continue
        actual = details.get(key)
        if actual not in expected_values:
            mismatches[key] = {
                "expected": sorted(expected_values, key=str),
                "actual": actual,
            }
    return mismatches


def timestamp_inside_capture_window(line: str, start: datetime, end: datetime) -> tuple[bool, str | None, str | None]:
    prefix = runtime_observer_analyzer.extract_log_timestamp_prefix(line)
    if prefix is None:
        return False, None, "missing"
    if UTC_TIMESTAMP_RE.fullmatch(prefix) is None:
        return False, prefix, "not_utc"
    observed = parse_utc_timestamp(prefix)
    if observed is None:
        return False, prefix, "invalid"
    return start <= observed <= end, prefix, None


def validate_copied_log_observer_enable_inside_capture_window(
    lines: list[str],
    *,
    start: datetime,
    end: datetime,
    blockers: list[dict[str, Any]],
) -> None:
    observer_enable_lines = [
        (line_number, line)
        for line_number, line in enumerate(lines, start=1)
        if "PlayerPrincipalLifecycleObserver enabled " in line
    ]
    if not observer_enable_lines:
        add(
            blockers,
            "source_summary_copied_log_observer_enable_missing",
            "$.source_summary.evidence.sources[0].path",
        )
        return
    for line_number, line in observer_enable_lines:
        inside_window, timestamp_prefix, timestamp_error = timestamp_inside_capture_window(line, start, end)
        if timestamp_error == "missing":
            add(
                blockers,
                "source_summary_copied_log_observer_enable_timestamp_missing",
                "$.source_summary.evidence.sources[0].path",
                line=line_number,
            )
            continue
        if timestamp_error is not None:
            add(
                blockers,
                "source_summary_copied_log_observer_enable_timestamp_not_utc",
                "$.source_summary.evidence.sources[0].path",
                line=line_number,
                timestamp_prefix=timestamp_prefix,
                expected="UTC timestamp prefix like [2026-06-01T12:01:30Z]",
            )
            continue
        if not inside_window:
            add(
                blockers,
                "source_summary_copied_log_observer_enable_outside_actual_capture_window",
                "$.source_summary.evidence.sources[0].path",
                line=line_number,
                timestamp_prefix=timestamp_prefix,
                actual_capture_start_utc=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                actual_capture_end_utc=end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )


def default_strict_rejected_start_diagnostics() -> dict[str, Any]:
    return {
        "partial_start_end_present": False,
        "missing_strict_rejected_start": False,
        "strict_rejected_start_expected_shape": STRICT_REJECTED_START_EXPECTED_SHAPE,
        "strict_rejected_start_observed_shape": None,
    }


def rejected_start_observed_shape(
    event_case: dict[str, Any],
    *,
    line_number: int,
    inside_capture_window: bool | None,
    timestamp_prefix: str | None,
    timestamp_error: str | None,
) -> dict[str, Any]:
    copied_bool_values = event_case.get("copied_bool_values")
    values = copied_bool_values if isinstance(copied_bool_values, list) else []
    target = event_case.get("target")
    return {
        "shape": f"{target}({','.join(str(value) for value in values)})",
        "line": line_number,
        "inside_capture_window": inside_capture_window,
        "timestamp_prefix": timestamp_prefix,
        "timestamp_error": timestamp_error,
        "target": target,
        "role": event_case.get("role"),
        "copied_bool_fields": event_case.get("copied_bool_fields"),
        "copied_bool_values": copied_bool_values,
        "principal_action": event_case.get("principal_action"),
        "apply_status": event_case.get("apply_status"),
        "correlation_status": event_case.get("correlation_status"),
    }


def validate_copied_log_lifecycle_events_inside_capture_window(
    lines: list[str],
    *,
    actual_capture: dict[str, datetime],
    blockers: list[dict[str, Any]],
    strict_rejected_start_diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    proof: dict[str, Any] = {
        "accepted": False,
        "source": "copied_log",
        "single_complete_sibling_set": False,
        "selection": strict_lifecycle_triplet_selection([]),
        "selected_line_numbers": [],
        "selected_sequences": [],
        "selected_roles": [],
        "selected_timestamp_prefixes": [],
        "selected_cases": [],
        "status_proof": [],
        "safe_copied_fields": [],
        "session_end_correlation_status": None,
        "blockers": ["runtime_lifecycle_correlation_proof_not_computed"],
    }
    start = actual_capture.get("start_utc")
    end = actual_capture.get("end_utc")
    if start is None or end is None:
        return proof
    validate_copied_log_observer_enable_inside_capture_window(
        lines,
        start=start,
        end=end,
        blockers=blockers,
    )

    in_window_roles: set[str] = set()
    in_window_role_lines: dict[str, list[int]] = {}
    observed_rejected_start_shape: dict[str, Any] | None = None
    accepted_event_count = 0
    accepted_in_window_events: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        match = LIFECYCLE_EVENT_LINE_RE.search(line)
        if match is None:
            continue
        role = match.group("role")
        expected_status = EXPECTED_LIFECYCLE_EVENT_STATUS_PROOFS[role]
        event_case = copied_log_lifecycle_event_case(line)
        full_shape_mismatches = copied_log_lifecycle_event_full_shape_mismatches(line)
        inside_window, timestamp_prefix, timestamp_error = timestamp_inside_capture_window(line, start, end)
        if (
            role == "session_start_rejected"
            and event_case is not None
            and observed_rejected_start_shape is None
        ):
            observed_rejected_start_shape = rejected_start_observed_shape(
                event_case,
                line_number=line_number,
                inside_capture_window=inside_window if timestamp_error is None else False,
                timestamp_prefix=timestamp_prefix,
                timestamp_error=timestamp_error,
            )
        event_shape_allowed = (
            event_case is not None
            and freeze_case(event_case) in REQUIRED_OBSERVED_EVENT_CASE_SET
            and not full_shape_mismatches
        )
        if full_shape_mismatches:
            add(
                blockers,
                "source_summary_copied_log_lifecycle_event_full_shape_mismatch",
                "$.source_summary.evidence.sources[0].path",
                line=line_number,
                role=role,
                mismatches=full_shape_mismatches,
            )
        if not event_shape_allowed:
            add(
                blockers,
                "source_summary_copied_log_lifecycle_event_unapproved_shape",
                "$.source_summary.evidence.sources[0].path",
                line=line_number,
                role=role,
                observed=event_case,
                accepted_alternatives=[
                    str(alternative["id"])
                    for alternative in REQUIRED_OBSERVED_EVENT_CASE_ALTERNATIVES
                ],
            )
        values = dict(LOG_KEY_VALUE_RE.findall(line))
        if (
            values.get("apply_status") != expected_status["apply_status"]
            or values.get("correlation_status") != expected_status["correlation_status"]
        ):
            add(
                blockers,
                "source_summary_copied_log_lifecycle_event_status_proof_mismatch",
                "$.source_summary.evidence.sources[0].path",
                line=line_number,
                role=role,
                expected_apply_status=expected_status["apply_status"],
                expected_correlation_status=expected_status["correlation_status"],
                actual_apply_status=values.get("apply_status"),
                actual_correlation_status=values.get("correlation_status"),
            )
            continue
        if not event_shape_allowed:
            continue
        accepted_event_count += 1
        label = "$.source_summary.evidence.sources[0].path"
        if timestamp_error == "missing":
            add(
                blockers,
                "source_summary_copied_log_lifecycle_event_timestamp_missing",
                label,
                line=line_number,
                role=role,
            )
            continue
        if timestamp_error is not None:
            add(
                blockers,
                "source_summary_copied_log_lifecycle_event_timestamp_not_utc",
                label,
                line=line_number,
                role=role,
                timestamp_prefix=timestamp_prefix,
                expected="UTC timestamp prefix like [2026-06-01T12:02:00Z]",
            )
            continue
        if not inside_window:
            add(
                blockers,
                "source_summary_copied_log_lifecycle_event_outside_actual_capture_window",
                label,
                line=line_number,
                role=role,
                timestamp_prefix=timestamp_prefix,
                actual_capture_start_utc=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                actual_capture_end_utc=end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            continue
        role_lines = in_window_role_lines.setdefault(role, [])
        role_lines.append(line_number)
        in_window_roles.add(role)
        accepted_in_window_events.append(
            {
                **event_case,
                "index": len(accepted_in_window_events),
                "line_number": line_number,
                "sequence": int(match.group("sequence")),
                "timestamp_prefix": timestamp_prefix,
            }
        )

    missing_roles = sorted(
        set(EXPECTED_LIFECYCLE_EVENT_STATUS_PROOFS) - in_window_roles,
        key=lambda role: list(EXPECTED_LIFECYCLE_EVENT_STATUS_PROOFS).index(role),
    )
    if missing_roles:
        add(
            blockers,
            "source_summary_copied_log_lifecycle_event_roles_not_in_actual_capture_window",
            "$.source_summary.evidence.sources[0].path",
            missing=missing_roles,
            accepted_event_line_count=accepted_event_count,
        )
    partial_start_end_present = (
        "session_start" in in_window_roles
        and "session_end" in in_window_roles
        and "session_start_rejected" not in in_window_roles
    )
    missing_strict_rejected_start = "session_start_rejected" not in in_window_roles
    if strict_rejected_start_diagnostics is not None:
        strict_rejected_start_diagnostics.update(
            {
                "partial_start_end_present": partial_start_end_present,
                "missing_strict_rejected_start": missing_strict_rejected_start,
                "strict_rejected_start_expected_shape": STRICT_REJECTED_START_EXPECTED_SHAPE,
                "strict_rejected_start_observed_shape": observed_rejected_start_shape,
            }
        )
    if missing_strict_rejected_start:
        add(
            blockers,
            "runtime_summary_strict_rejected_start_missing",
            "$.source_summary.modules.player_principal_lifecycle.observed_event_cases",
            partial_start_end_present=partial_start_end_present,
            missing_strict_rejected_start=True,
            strict_rejected_start_expected_shape=STRICT_REJECTED_START_EXPECTED_SHAPE,
            strict_rejected_start_observed_shape=observed_rejected_start_shape,
        )
    selection = strict_lifecycle_triplet_selection(
        accepted_in_window_events,
        order_keys=("sequence", "line_number"),
    )
    if selection.get("accepted") is not True:
        if selection.get("status") == "ambiguous":
            add(
                blockers,
                "source_summary_copied_log_strict_lifecycle_triplet_ambiguous",
                "$.source_summary.evidence.sources[0].path",
                candidate_count=selection.get("candidate_count"),
                candidate_triplets=selection.get("candidate_triplets"),
                non_counting_context_roles=selection.get("non_counting_context_roles"),
            )
        elif not missing_strict_rejected_start:
            add(
                blockers,
                "source_summary_copied_log_strict_lifecycle_triplet_not_selected",
                "$.source_summary.evidence.sources[0].path",
                selection=selection,
            )
    elif not strict_lifecycle_triplet_is_exact(selection):
        add(
            blockers,
            "source_summary_copied_log_strict_lifecycle_triplet_not_exact",
            "$.source_summary.evidence.sources[0].path",
            selection=selection,
        )
    proof = lifecycle_correlation_proof_from_selection(
        selection,
        accepted_in_window_events,
        source="copied_log",
    )
    return proof


def validate_source_summary_matches_copied_log(summary: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    evidence = summary.get("evidence")
    sources = evidence.get("sources") if isinstance(evidence, dict) else None
    if not isinstance(evidence, dict) or not isinstance(sources, list) or len(sources) != 1:
        return
    source = sources[0]
    if not isinstance(source, dict):
        return
    expected = expected_summary_from_copied_source(evidence, source, blockers)
    if expected is None:
        return
    validate_copied_log_has_no_diagnostic_candidates(expected, blockers)
    validate_copied_log_not_diagnostic_only(expected, blockers)
    if canonical_json_bytes(summary) != canonical_json_bytes(expected):
        add(
            blockers,
            "source_summary_not_derived_from_copied_log",
            "$.source_summary",
        )


def detail_values(functions: dict[str, Any], function: str, key: str) -> list[Any]:
    details = functions.get(function, {}).get("details", {})
    value = details.get(key, [])
    return value if isinstance(value, list) else []


def require_values(
    blockers: list[dict[str, Any]],
    functions: dict[str, Any],
    function: str,
    key: str,
    expected: set[Any],
) -> None:
    values = set(detail_values(functions, function, key))
    if not expected.issubset(values):
        add(
            blockers,
            "runtime_summary_detail_values_missing",
            f"$.source_summary.modules.{MODULE}.functions.{function}.details.{key}",
            expected=sorted(expected, key=str),
            observed=sorted(values, key=str),
        )
    extra_values = values - expected
    if extra_values:
        add(
            blockers,
            "runtime_summary_detail_values_unexpected",
            f"$.source_summary.modules.{MODULE}.functions.{function}.details.{key}",
            expected=sorted(expected, key=str),
            observed=sorted(values, key=str),
            unexpected=sorted(extra_values, key=str),
        )


def require_expected_detail_values(
    blockers: list[dict[str, Any]],
    functions: dict[str, Any],
    function: str,
    expected_detail_values: dict[str, set[Any]],
) -> None:
    function_payload = functions.get(function)
    label = f"$.source_summary.modules.{MODULE}.functions.{function}"
    if not isinstance(function_payload, dict):
        add(blockers, "runtime_summary_function_missing", label)
        return
    details = function_payload.get("details")
    if not isinstance(details, dict):
        add(blockers, "runtime_summary_function_details_missing", f"{label}.details")
        return

    expected_keys = frozenset(expected_detail_values)
    observed_keys = set(details)
    unexpected_keys = observed_keys - expected_keys
    if unexpected_keys:
        add(
            blockers,
            "runtime_summary_detail_keys_unexpected",
            f"{label}.details",
            unexpected=sorted(unexpected_keys),
        )
    for key, expected in expected_detail_values.items():
        require_values(blockers, functions, function, key, expected)


def case_without_sequence(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "target": case.get("target"),
        "role": case.get("role"),
        "copied_bool_fields": case.get("copied_bool_fields"),
        "copied_bool_values": case.get("copied_bool_values"),
        "principal_action": case.get("principal_action"),
        "apply_status": case.get("apply_status"),
        "correlation_status": case.get("correlation_status"),
    }


def freeze_case(case: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    return tuple(
        (key, tuple(value) if isinstance(value, list) else value)
        for key, value in case.items()
    )


def strict_triplet_candidate_summary(
    candidate: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            key: event.get(key)
            for key in (
                "index",
                "line_number",
                "sequence",
                "timestamp_prefix",
                "role",
                "target",
            )
            if key in event
        }
        for event in candidate
    ]


def strict_lifecycle_triplet_selection(
    cases: Any,
    *,
    order_keys: tuple[str, ...] = ("sequence",),
) -> dict[str, Any]:
    if not isinstance(cases, list):
        return {
            "status": "invalid_input",
            "selected": False,
            "accepted": False,
            "candidate_count": 0,
            "selected_indices": [],
            "selected_sequences": [],
            "selected_roles": [],
            "selected_cases": [],
            "non_counting_context_event_count": 0,
            "non_counting_context_roles": [],
            "candidate_triplets": [],
            "missing_roles": list(READY_LOG_COPY_REQUIRED_ROLES),
            "blockers": ["strict_lifecycle_triplet_observed_event_cases_not_list"],
        }

    exact_events: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            continue
        compact_case = case_without_sequence(case)
        role = compact_case.get("role")
        expected = REQUIRED_OBSERVED_EVENT_CASE_BY_ROLE.get(str(role))
        if expected is None or compact_case != expected:
            continue
        exact_events.append(
            {
                **case,
                "index": index,
                "role": role,
                "target": compact_case.get("target"),
            }
        )

    by_role: dict[str, list[dict[str, Any]]] = {
        role: [] for role in READY_LOG_COPY_REQUIRED_ROLES
    }
    for event in exact_events:
        role = event.get("role")
        if isinstance(role, str) and role in by_role:
            by_role[role].append(event)

    def strictly_ordered(candidate: list[dict[str, Any]]) -> bool:
        for key in order_keys:
            values = [event.get(key) for event in candidate]
            if not all(isinstance(value, int) for value in values):
                return False
            if any(current <= previous for previous, current in zip(values, values[1:])):
                return False
        return True

    candidates: list[list[dict[str, Any]]] = []
    for start in by_role["session_start"]:
        for rejected in by_role["session_start_rejected"]:
            for end in by_role["session_end"]:
                candidate = [start, rejected, end]
                if strictly_ordered(candidate):
                    candidates.append(candidate)

    missing_roles = [
        role for role in READY_LOG_COPY_REQUIRED_ROLES if not by_role[role]
    ]
    exact_context_roles = [
        role for role in READY_LOG_COPY_REQUIRED_ROLES if len(by_role[role]) > 1
    ]
    def candidate_rank(candidate: list[dict[str, Any]]) -> tuple[int, ...]:
        rejected = tuple(int(candidate[1].get(key, 0)) for key in order_keys)
        start = tuple(-int(candidate[0].get(key, 0)) for key in order_keys)
        end = tuple(int(candidate[2].get(key, 0)) for key in order_keys)
        return (*rejected, *start, *end)

    selected: list[dict[str, Any]] | None = None
    status = "selected"
    forced_ambiguous = len(by_role["session_start_rejected"]) > 1
    if forced_ambiguous:
        selected = None
    elif len(candidates) == 1:
        selected = candidates[0]
    elif candidates and set(exact_context_roles).issubset(ALLOWED_DUPLICATE_CONTEXT_ROLES):
        selected = min(candidates, key=candidate_rank)
        status = "selected_with_duplicate_start_end_context"

    if selected is None:
        return {
            "status": "ambiguous" if forced_ambiguous or len(candidates) > 1 else "missing",
            "selected": False,
            "accepted": False,
            "candidate_count": len(candidates),
            "selected_indices": [],
            "selected_sequences": [],
            "selected_roles": [],
            "selected_cases": [],
            "non_counting_context_event_count": len(exact_events),
            "non_counting_context_roles": exact_context_roles,
            "candidate_triplets": [
                strict_triplet_candidate_summary(candidate)
                for candidate in candidates[:5]
            ],
            "missing_roles": missing_roles,
            "blockers": (
                ["strict_lifecycle_triplet_ambiguous"]
                if forced_ambiguous or len(candidates) > 1
                else ["strict_lifecycle_triplet_missing"]
            ),
        }

    selected_indices = {event["index"] for event in selected}
    non_counting_context_events = [
        event for event in exact_events if event["index"] not in selected_indices
    ]
    return {
        "status": status,
        "selected": True,
        "accepted": status == "selected",
        "selected_context_only": status != "selected",
        "candidate_count": len(candidates),
        "selected_indices": [event["index"] for event in selected],
        "selected_sequences": [event.get("sequence") for event in selected],
        "selected_roles": [event.get("role") for event in selected],
        "selected_cases": [case_without_sequence(event) for event in selected],
        "non_counting_context_event_count": len(non_counting_context_events),
        "non_counting_context_roles": [
            role
            for role in READY_LOG_COPY_REQUIRED_ROLES
            if any(event.get("role") == role for event in non_counting_context_events)
        ],
        "candidate_triplets": [
            strict_triplet_candidate_summary(selected),
        ],
        "missing_roles": [],
        "blockers": [],
    }


def strict_lifecycle_triplet_is_exact(selection: dict[str, Any]) -> bool:
    return (
        selection.get("accepted") is True
        and selection.get("status") == "selected"
        and selection.get("candidate_count") == 1
        and selection.get("non_counting_context_event_count") == 0
        and selection.get("selected_roles") == list(READY_LOG_COPY_REQUIRED_ROLES)
    )


def lifecycle_correlation_proof_from_selection(
    selection: dict[str, Any],
    events: list[dict[str, Any]],
    *,
    source: str,
    run_id: str | None = None,
    copied_log_path: str | None = None,
    copied_log_sha256: str | None = None,
) -> dict[str, Any]:
    selected_indices = {
        index for index in selection.get("selected_indices", []) if isinstance(index, int)
    }
    selected_events = [
        event
        for event in events
        if isinstance(event.get("index"), int) and event["index"] in selected_indices
    ]
    session_end = next(
        (event for event in selected_events if event.get("role") == "session_end"),
        {},
    )
    proof: dict[str, Any] = {
        "accepted": strict_lifecycle_triplet_is_exact(selection),
        "source": source,
        "run_id": run_id,
        "copied_log": {
            "path": copied_log_path,
            "sha256": copied_log_sha256,
        },
        "single_complete_sibling_set": strict_lifecycle_triplet_is_exact(selection),
        "selection": selection,
        "selected_line_numbers": [
            event.get("line_number") for event in selected_events if "line_number" in event
        ],
        "selected_sequences": [event.get("sequence") for event in selected_events],
        "selected_roles": [event.get("role") for event in selected_events],
        "selected_timestamp_prefixes": [
            event.get("timestamp_prefix")
            for event in selected_events
            if "timestamp_prefix" in event
        ],
        "selected_cases": [case_without_sequence(event) for event in selected_events],
        "status_proof": [
            {
                "role": event.get("role"),
                "apply_status": event.get("apply_status"),
                "correlation_status": event.get("correlation_status"),
            }
            for event in selected_events
        ],
        "safe_copied_fields": [
            {
                "role": event.get("role"),
                "target": event.get("target"),
                "copied_bool_fields": event.get("copied_bool_fields"),
                "copied_bool_values": event.get("copied_bool_values"),
            }
            for event in selected_events
        ],
        "session_end_correlation_status": session_end.get("correlation_status"),
        "blockers": [] if strict_lifecycle_triplet_is_exact(selection) else selection.get("blockers", []),
        "non_claim": (
            "correlation proof binds only the approved copied runtime lifecycle triplet "
            "to one checked sibling set; it does not promote public identity or SDK readiness"
        ),
    }
    return proof


def lifecycle_correlation_proof_from_summary(
    summary: Any,
    *,
    run_id: str | None,
    copied_log_path: str | None,
    copied_log_sha256: str | None,
) -> dict[str, Any]:
    module = player_principal_lifecycle_module(summary)
    cases = module.get("observed_event_cases") if isinstance(module, dict) else None
    selection = strict_lifecycle_triplet_selection(cases)
    events = [
        {**case, "index": index}
        for index, case in enumerate(cases)
        if isinstance(case, dict)
    ] if isinstance(cases, list) else []
    return lifecycle_correlation_proof_from_selection(
        selection,
        events,
        source="source_summary",
        run_id=run_id,
        copied_log_path=copied_log_path,
        copied_log_sha256=copied_log_sha256,
    )


def validate_lifecycle_correlation_proof(
    *,
    summary: Any,
    window: dict[str, Any],
    copied_log_proof: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    copied = window.get("copied_log") if isinstance(window.get("copied_log"), dict) else {}
    run_id = window.get("run_id") if isinstance(window.get("run_id"), str) else None
    copied_log_path = copied.get("path") if isinstance(copied.get("path"), str) else None
    copied_log_sha256 = copied.get("sha256") if isinstance(copied.get("sha256"), str) else None
    summary_proof = lifecycle_correlation_proof_from_summary(
        summary,
        run_id=run_id,
        copied_log_path=copied_log_path,
        copied_log_sha256=copied_log_sha256,
    )
    proof: dict[str, Any] = {
        "accepted": False,
        "run_id": run_id,
        "copied_log": {
            "path": copied_log_path,
            "sha256": copied_log_sha256,
        },
        "source_summary": summary_proof,
        "copied_log_triplet": copied_log_proof,
        "selected_line_numbers": copied_log_proof.get("selected_line_numbers", []),
        "selected_sequences": copied_log_proof.get("selected_sequences", []),
        "selected_roles": copied_log_proof.get("selected_roles", []),
        "selected_timestamp_prefixes": copied_log_proof.get("selected_timestamp_prefixes", []),
        "selected_cases": copied_log_proof.get("selected_cases", []),
        "status_proof": copied_log_proof.get("status_proof", []),
        "safe_copied_fields": copied_log_proof.get("safe_copied_fields", []),
        "matched_selected_sequences": False,
        "matched_selected_roles": False,
        "matched_selected_cases": False,
        "session_end_correlation_status": copied_log_proof.get("session_end_correlation_status"),
        "single_complete_sibling_set": False,
        "blockers": [],
    }
    if summary_proof.get("accepted") is not True:
        add(
            blockers,
            "runtime_lifecycle_correlation_proof_source_summary_not_exact",
            f"$.source_summary.modules.{MODULE}.observed_event_cases",
            proof=summary_proof,
        )
        proof["blockers"].append("runtime_lifecycle_correlation_proof_source_summary_not_exact")
    if copied_log_proof.get("accepted") is not True:
        add(
            blockers,
            "runtime_lifecycle_correlation_proof_copied_log_not_exact",
            "$.source_summary.evidence.sources[0].path",
            proof=copied_log_proof,
        )
        proof["blockers"].append("runtime_lifecycle_correlation_proof_copied_log_not_exact")

    for key, reason in (
        ("selected_sequences", "runtime_lifecycle_correlation_proof_selected_sequences_mismatch"),
        ("selected_roles", "runtime_lifecycle_correlation_proof_selected_roles_mismatch"),
        ("selected_cases", "runtime_lifecycle_correlation_proof_selected_cases_mismatch"),
    ):
        summary_value = summary_proof.get(key)
        copied_value = copied_log_proof.get(key)
        matched_key = f"matched_{key}"
        proof[matched_key] = summary_value == copied_value and bool(summary_value)
        if summary_proof.get("accepted") is True and copied_log_proof.get("accepted") is True and not proof[matched_key]:
            add(
                blockers,
                reason,
                "$.source_summary.modules.player_principal_lifecycle.observed_event_cases",
                expected=copied_value,
                actual=summary_value,
            )
            proof["blockers"].append(reason)

    if copied_log_proof.get("session_end_correlation_status") != "matched":
        add(
            blockers,
            "runtime_lifecycle_correlation_proof_session_end_not_matched",
            "$.source_summary.evidence.sources[0].path",
            actual=copied_log_proof.get("session_end_correlation_status"),
        )
        proof["blockers"].append("runtime_lifecycle_correlation_proof_session_end_not_matched")

    proof["single_complete_sibling_set"] = (
        copied_log_path is not None
        and copied_log_sha256 is not None
        and summary_proof.get("accepted") is True
        and copied_log_proof.get("accepted") is True
        and proof.get("matched_selected_sequences") is True
        and proof.get("matched_selected_roles") is True
        and proof.get("matched_selected_cases") is True
        and copied_log_proof.get("session_end_correlation_status") == "matched"
    )
    proof["accepted"] = proof["single_complete_sibling_set"] and not proof["blockers"]
    return proof


def observed_event_case_label(case: dict[str, Any]) -> str:
    role = str(case.get("role"))
    return {
        "session_start": "session_start_anchor",
        "session_start_rejected": "session_start_rejected_anchor",
        "session_end": "session_end_anchor",
    }.get(role, f"{role}_anchor")


def compact_observed_event_cases(cases: Any) -> list[dict[str, Any]]:
    if not isinstance(cases, list):
        return []
    compact_cases: list[dict[str, Any]] = []
    for case in cases:
        if isinstance(case, dict):
            compact_cases.append(case_without_sequence(case))
    return compact_cases


def matching_observed_event_alternative(cases: Any) -> dict[str, Any] | None:
    selection = strict_lifecycle_triplet_selection(cases)
    compact_cases = (
        selection.get("selected_cases")
        if selection.get("accepted") is True
        else compact_observed_event_cases(cases)
    )
    if not isinstance(compact_cases, list):
        compact_cases = compact_observed_event_cases(cases)
    for alternative in REQUIRED_OBSERVED_EVENT_CASE_ALTERNATIVES:
        expected_cases = [dict(case) for case in alternative["cases"]]
        if compact_cases == expected_cases:
            return alternative
    return None


def best_observed_event_alternative(compact_cases: list[dict[str, Any]]) -> dict[str, Any]:
    def score(alternative: dict[str, Any]) -> tuple[int, int]:
        expected_cases = [dict(case) for case in alternative["cases"]]
        positional_matches = sum(
            1
            for observed, expected in zip(compact_cases, expected_cases)
            if observed == expected
        )
        shape_matches = sum(1 for observed in compact_cases if observed in expected_cases)
        return (positional_matches, shape_matches)

    return max(REQUIRED_OBSERVED_EVENT_CASE_ALTERNATIVES, key=score)


def validate_observed_event_cases(module: dict[str, Any], blockers: list[dict[str, Any]]) -> list[str]:
    cases = module.get("observed_event_cases")
    label = f"$.source_summary.modules.{MODULE}.observed_event_cases"
    if not isinstance(cases, list):
        add(blockers, "runtime_summary_observed_event_cases_missing", label)
        return []

    observed_runtime_cases: list[str] = []
    previous_sequence = 0
    compact_cases = compact_observed_event_cases(cases)
    selection = strict_lifecycle_triplet_selection(cases)
    selected_indices = set(selection.get("selected_indices", []))

    for index, case in enumerate(cases):
        case_label = f"{label}[{index}]"
        if not isinstance(case, dict):
            add(blockers, "runtime_summary_observed_event_case_invalid", case_label)
            continue
        unexpected_keys = set(case) - OBSERVED_EVENT_CASE_KEYS
        if unexpected_keys:
            add(
                blockers,
                "runtime_summary_observed_event_case_keys_unexpected",
                case_label,
                unexpected=sorted(unexpected_keys),
            )
        sequence = case.get("sequence")
        if not isinstance(sequence, int) or sequence <= previous_sequence:
            add(blockers, "runtime_summary_observed_event_case_sequence_invalid", f"{case_label}.sequence")
        if isinstance(sequence, int):
            previous_sequence = sequence
        compact_case = case_without_sequence(case)
        case_is_required_shape = freeze_case(compact_case) in REQUIRED_OBSERVED_EVENT_CASE_SET
        if not case_is_required_shape:
            add(
                blockers,
                "runtime_summary_observed_event_case_unexpected",
                case_label,
                observed=compact_case,
            )
        elif index in selected_indices:
            observed_runtime_cases.append(observed_event_case_label(compact_case))

    if selection.get("accepted") is not True:
        if selection.get("status") == "ambiguous":
            add(
                blockers,
                "runtime_summary_strict_lifecycle_triplet_ambiguous",
                label,
                candidate_count=selection.get("candidate_count"),
                candidate_triplets=selection.get("candidate_triplets"),
                non_counting_context_roles=selection.get("non_counting_context_roles"),
            )
        else:
            best_alternative = best_observed_event_alternative(compact_cases)
            expected_cases = [dict(case) for case in best_alternative["cases"]]
            remaining_expected = [
                expected for expected in expected_cases if expected not in compact_cases
            ]
            if not remaining_expected and selection.get("missing_roles"):
                remaining_expected = expected_cases
            if not selection.get("missing_roles") and selection.get("candidate_count") == 0:
                add(
                    blockers,
                    "runtime_summary_observed_event_case_order_mismatch",
                    label,
                    expected=expected_cases,
                    observed=compact_cases,
                )
            add(
                blockers,
                "runtime_summary_required_observed_event_cases_missing",
                label,
                missing=remaining_expected,
                missing_roles=selection.get("missing_roles", []),
                candidate_count=selection.get("candidate_count"),
            )
    return observed_runtime_cases


def validate_runtime_summary(summary: Any, blockers: list[dict[str, Any]]) -> list[str]:
    if not isinstance(summary, dict):
        add(blockers, "source_summary_missing", "$.source_summary")
        return []
    if summary.get("schema") != SUMMARY_SCHEMA:
        add(blockers, "source_summary_schema_mismatch", "$.source_summary.schema")
    if summary.get("review_scope") != "runtime_observer_evidence_summary":
        add(blockers, "source_summary_review_scope_mismatch", "$.source_summary.review_scope")
    if summary.get("readiness_gate") != "none":
        add(
            blockers,
            "source_summary_readiness_gate_mismatch",
            "$.source_summary.readiness_gate",
            expected="none",
            actual=summary.get("readiness_gate"),
        )
    source_promotion_gate = summary.get("promotion_gate")
    if not isinstance(source_promotion_gate, dict):
        add(blockers, "source_summary_promotion_gate_missing", "$.source_summary.promotion_gate")
    else:
        unexpected_keys = set(source_promotion_gate) - ALLOWED_SOURCE_SUMMARY_PROMOTION_GATE_KEYS
        if unexpected_keys:
            add(
                blockers,
                "source_summary_promotion_gate_keys_unexpected",
                "$.source_summary.promotion_gate",
                unexpected=sorted(unexpected_keys),
            )
        for key, expected in EXPECTED_SOURCE_SUMMARY_PROMOTION_GATE.items():
            if source_promotion_gate.get(key) != expected:
                add(
                    blockers,
                    f"source_summary_promotion_gate_{key}_mismatch",
                    f"$.source_summary.promotion_gate.{key}",
                    expected=expected,
                    actual=source_promotion_gate.get(key),
                )
    evidence = summary.get("evidence")
    if not isinstance(evidence, dict):
        add(blockers, "source_summary_evidence_missing", "$.source_summary.evidence")
    else:
        if evidence.get("kind") != "runtime-observer-log":
            add(blockers, "source_summary_evidence_kind_mismatch", "$.source_summary.evidence.kind")
        if evidence.get("server_paths_allowed") is not False:
            add(blockers, "source_summary_server_paths_allowed", "$.source_summary.evidence.server_paths_allowed")
        if not evidence.get("obelisk_commit"):
            add(blockers, "source_summary_obelisk_commit_missing", "$.source_summary.evidence.obelisk_commit")
        else:
            current_commit = current_obelisk_commit()
            if current_commit is None:
                add(
                    blockers,
                    "current_obelisk_commit_unavailable",
                    "$.source_summary.evidence.obelisk_commit",
                )
            elif evidence.get("obelisk_commit") != current_commit:
                add(
                    blockers,
                    "source_summary_obelisk_commit_not_current_head",
                    "$.source_summary.evidence.obelisk_commit",
                    expected=current_commit,
                    actual=evidence.get("obelisk_commit"),
                )
        sources = evidence.get("sources")
        if not isinstance(sources, list) or len(sources) != 1:
            add(blockers, "source_summary_sources_not_exactly_one", "$.source_summary.evidence.sources")
        else:
            for index, source in enumerate(sources):
                label = f"$.source_summary.evidence.sources[{index}]"
                if not isinstance(source, dict):
                    add(blockers, "source_summary_source_invalid", label)
                    continue
                unexpected_source_keys = set(source) - ALLOWED_SOURCE_KEYS
                if unexpected_source_keys:
                    add(
                        blockers,
                        "source_summary_source_keys_unexpected",
                        label,
                        unexpected=sorted(unexpected_source_keys),
                    )
                symlink_component = symlink_component_for_path_text(source.get("path"))
                if symlink_component is not None:
                    add(
                        blockers,
                        "source_summary_source_path_symlink_component",
                        f"{label}.path",
                        symlink=str(symlink_component),
                    )
                    continue
                if not source_path_is_copied_or_offline(source.get("path")):
                    add(blockers, "source_summary_source_path_not_copied_or_offline", f"{label}.path")
                elif not source_path_is_approved_offline_workspace(source.get("path")):
                    add(blockers, "source_summary_source_path_not_approved_offline_workspace", f"{label}.path")
                else:
                    validate_copied_source_file(source, label, blockers)
        validate_source_summary_matches_copied_log(summary, blockers)

    runtime = summary.get("runtime")
    if not isinstance(runtime, dict):
        add(blockers, "source_summary_runtime_missing", "$.source_summary.runtime")
    else:
        expected_runtime = {
            "loaded_native_ld_preload": True,
            "process_event_candidate_count": 1,
            "process_event_candidates": [{"index": 0, "address": EXPECTED_PROCESS_EVENT_ADDRESS}],
            "process_event_address": EXPECTED_PROCESS_EVENT_ADDRESS,
            "process_event_hook_installed": True,
            "process_event_hook_patch_size": 18,
            "broad_process_event_trace_lines": 0,
            "reflection_scanner_disabled": True,
            "plugins_disabled": True,
        }
        for key, expected in expected_runtime.items():
            if runtime.get(key) != expected:
                add(blockers, "source_summary_runtime_posture_mismatch", f"$.source_summary.runtime.{key}", expected=expected)

    modules = summary.get("modules")
    if not isinstance(modules, dict) or MODULE not in modules:
        add(blockers, "player_principal_lifecycle_module_missing", "$.source_summary.modules")
        return []
    module_names = set(modules)
    if module_names != {MODULE}:
        add(
            blockers,
            "source_summary_unexpected_modules_present",
            "$.source_summary.modules",
            expected=[MODULE],
            observed=sorted(module_names),
        )
    module = modules[MODULE]
    if not isinstance(module, dict):
        add(blockers, "player_principal_lifecycle_module_invalid", f"$.source_summary.modules.{MODULE}")
        return []
    if module.get("gate_sha256") != [EXPECTED_BINARY_SHA256]:
        add(blockers, "runtime_summary_gate_sha256_mismatch", f"$.source_summary.modules.{MODULE}.gate_sha256")
    if module.get("observer_gate_count") != 1:
        add(
            blockers,
            "runtime_summary_observer_gate_count_mismatch",
            f"$.source_summary.modules.{MODULE}.observer_gate_count",
            expected=1,
            observed=module.get("observer_gate_count"),
        )
    if module.get("blockers") != ["runtime_observer_evidence_only"]:
        add(blockers, "runtime_summary_quality_blockers_present", f"$.source_summary.modules.{MODULE}.blockers")
    for key in (
        "malformed_observer_lines",
        "orphan_field_lines",
        "out_of_order_field_lines",
        "field_count_mismatches",
        "sequence_quality_violations",
        "timestamp_quality_violations",
        "event_before_gate_lines",
        "non_observer_lifecycle_lines",
        "passive_monitor_metadata_lines",
    ):
        if module.get(key) != 0:
            add(blockers, "runtime_summary_quality_counter_nonzero", f"$.source_summary.modules.{MODULE}.{key}")
    if module.get("redacted_detail_keys") != {}:
        add(blockers, "runtime_summary_unapproved_detail_keys", f"$.source_summary.modules.{MODULE}.redacted_detail_keys")
    accepted_count = module.get("accepted_count")
    observed_event_cases = module.get("observed_event_cases")
    observed_event_case_count = len(observed_event_cases) if isinstance(observed_event_cases, list) else None
    strict_triplet_selection = strict_lifecycle_triplet_selection(observed_event_cases)
    if (
        not isinstance(accepted_count, int)
        or accepted_count < len(REQUIRED_OBSERVED_EVENT_CASES)
        or (
            observed_event_case_count is not None
            and accepted_count != observed_event_case_count
        )
    ):
        add(
            blockers,
            "runtime_summary_accepted_event_count_mismatch",
            f"$.source_summary.modules.{MODULE}.accepted_count",
            expected={
                "minimum": len(REQUIRED_OBSERVED_EVENT_CASES),
                "matches_observed_event_cases": observed_event_case_count,
            },
            observed=accepted_count,
        )
    if strict_triplet_selection.get("accepted") is not True:
        add(
            blockers,
            "runtime_summary_strict_lifecycle_triplet_not_selected",
            f"$.source_summary.modules.{MODULE}.observed_event_cases",
            selection=strict_triplet_selection,
        )
    elif not strict_lifecycle_triplet_is_exact(strict_triplet_selection):
        add(
            blockers,
            "runtime_summary_strict_lifecycle_triplet_not_exact",
            f"$.source_summary.modules.{MODULE}.observed_event_cases",
            selection=strict_triplet_selection,
        )
    if module.get("complete_lifecycle_event_triplet_candidate_present") is not True:
        add(
            blockers,
            "runtime_summary_complete_lifecycle_event_triplet_missing",
            f"$.source_summary.modules.{MODULE}.complete_lifecycle_event_triplet_candidate_present",
            expected=True,
            observed=module.get("complete_lifecycle_event_triplet_candidate_present"),
        )
    if module.get("metadata_only_count") != 0:
        add(
            blockers,
            "runtime_summary_metadata_only_not_approved_lifecycle_evidence",
            f"$.source_summary.modules.{MODULE}.metadata_only_count",
            expected=0,
            observed=module.get("metadata_only_count"),
        )
    reject_reasons = module.get("reject_reasons")
    if module.get("rejected_count") != 0 or (isinstance(reject_reasons, dict) and reject_reasons):
        add(
            blockers,
            "runtime_summary_rejected_or_reason_only_not_approved_lifecycle_evidence",
            f"$.source_summary.modules.{MODULE}.rejected_count",
            expected=0,
            observed=module.get("rejected_count"),
            reject_reasons=reject_reasons if isinstance(reject_reasons, dict) else None,
        )
    diagnostic_reason_counts = module.get("diagnostic_candidate_reason_counts")
    diagnostic_read_status_counts = module.get("diagnostic_candidate_read_status_counts")
    diagnostic_target_counts = module.get("diagnostic_candidate_target_counts")
    diagnostic_count = module.get("diagnostic_candidate_count")
    if diagnostic_material_present(module):
        add_diagnostic_candidate_blocker(
            blockers,
            "runtime_summary_diagnostic_candidates_not_approved_lifecycle_evidence",
            f"$.source_summary.modules.{MODULE}.diagnostic_candidate_count",
            module,
        )
    add_runtime_summary_diagnostic_context_blockers(module, blockers)
    if diagnostic_material_present(module) and accepted_count != len(REQUIRED_OBSERVED_EVENT_CASES):
        add(
            blockers,
            "runtime_summary_diagnostic_candidate_only_not_approved_lifecycle_evidence",
            f"$.source_summary.modules.{MODULE}.diagnostic_candidate_count",
            expected_lifecycle_event_count=len(REQUIRED_OBSERVED_EVENT_CASES),
            observed_lifecycle_event_count=accepted_count,
            diagnostic_candidate_count=diagnostic_count,
            diagnostic_reason_counts=diagnostic_reason_counts if isinstance(diagnostic_reason_counts, dict) else None,
        )
    check_join_diagnostic_count = (
        diagnostic_target_counts.get(CHECK_JOIN_IN_PROGRESS_DIAGNOSTIC_TARGET)
        if isinstance(diagnostic_target_counts, dict)
        else None
    )
    if check_join_diagnostic_count and accepted_count != len(REQUIRED_OBSERVED_EVENT_CASES):
        add(
            blockers,
            "runtime_summary_check_join_in_progress_diagnostic_only_not_approved_lifecycle_evidence",
            f"$.source_summary.modules.{MODULE}.diagnostic_candidate_target_counts.{CHECK_JOIN_IN_PROGRESS_DIAGNOSTIC_TARGET}",
            expected_lifecycle_event_count=len(REQUIRED_OBSERVED_EVENT_CASES),
            observed_lifecycle_event_count=accepted_count,
            diagnostic_target=CHECK_JOIN_IN_PROGRESS_DIAGNOSTIC_TARGET,
            diagnostic_target_count=check_join_diagnostic_count,
        )
    if (
        module.get("observer_gate_count") == 1
        and accepted_count == 0
        and module.get("metadata_only_count") == 0
        and module.get("rejected_count") == 0
        and not diagnostic_material_present(module)
    ):
        add(
            blockers,
            "runtime_summary_observer_gate_only_not_approved_lifecycle_evidence",
            f"$.source_summary.modules.{MODULE}.observer_gate_count",
            expected_lifecycle_event_count=len(REQUIRED_OBSERVED_EVENT_CASES),
            observed_lifecycle_event_count=accepted_count,
        )

    matched_observed_event_alternative = matching_observed_event_alternative(
        module.get("observed_event_cases")
    )
    expected_detail_values = EXPECTED_DETAIL_VALUES_BY_OBSERVED_EVENT_ALTERNATIVE.get(
        str(matched_observed_event_alternative.get("id")) if matched_observed_event_alternative else "",
        EXPECTED_DETAIL_VALUES,
    )

    functions = module.get("functions")
    if not isinstance(functions, dict):
        add(blockers, "runtime_summary_functions_missing", f"$.source_summary.modules.{MODULE}.functions")
        return []
    unexpected_functions = set(functions) - set(expected_detail_values)
    if unexpected_functions:
        add(
            blockers,
            "runtime_summary_functions_unexpected",
            f"$.source_summary.modules.{MODULE}.functions",
            unexpected=sorted(unexpected_functions),
        )
    for function, detail_values_for_function in expected_detail_values.items():
        require_expected_detail_values(
            blockers,
            functions,
            function,
            detail_values_for_function,
        )
    observed_runtime_cases = validate_observed_event_cases(module, blockers)
    if module.get("observer_gate_count") == 1:
        observed_runtime_cases.insert(0, "observer_enable")
    return observed_runtime_cases


def validate_operational_window(
    window: Any,
    summary: Any,
    blockers: list[dict[str, Any]],
    *,
    strict_rejected_start_diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lifecycle_correlation_proof: dict[str, Any] = {
        "accepted": False,
        "run_id": None,
        "copied_log": {},
        "source_summary": {},
        "copied_log_triplet": {},
        "single_complete_sibling_set": False,
        "blockers": ["operational_window_not_validated"],
    }
    label = "$.operational_window"
    if not isinstance(window, dict):
        add(blockers, "operational_window_missing", label)
        return lifecycle_correlation_proof
    unexpected_window_keys = set(window) - ALLOWED_OPERATIONAL_WINDOW_KEYS
    if unexpected_window_keys:
        add(
            blockers,
            "operational_window_keys_unexpected",
            label,
            unexpected=sorted(unexpected_window_keys),
        )
    if window.get("schema") != WINDOW_CHECK_SCHEMA:
        add(blockers, "operational_window_schema_mismatch", f"{label}.schema")
    if window.get("ready") is not True or window.get("operational_window_manifest_ready") is not True:
        add(blockers, "operational_window_not_ready", label)
    for key in REQUIRED_OPERATIONAL_WINDOW_FALSE_FLAGS:
        if window.get(key) is not False:
            add(blockers, f"operational_window_{key}_not_false", f"{label}.{key}")
    if window.get("approval") not in EXPECTED_OPERATIONAL_WINDOW_APPROVALS:
        add(
            blockers,
            "operational_window_approval_mismatch",
            f"{label}.approval",
            expected=sorted(EXPECTED_OPERATIONAL_WINDOW_APPROVALS),
            actual=window.get("approval"),
        )
    timestamps: dict[str, dict[str, datetime]] = {}
    for key in ("approved_window", "actual_capture", "rollback_window"):
        value = window.get(key)
        if not isinstance(value, dict):
            add(blockers, f"operational_window_{key}_missing", f"{label}.{key}")
            continue
        unexpected_keys = set(value) - {"start_utc", "end_utc"}
        if unexpected_keys:
            add(blockers, f"operational_window_{key}_keys_unexpected", f"{label}.{key}", unexpected=sorted(unexpected_keys))
        for timestamp_key in ("start_utc", "end_utc"):
            parsed = parsed_window_timestamp(
                value.get(timestamp_key),
                reason=f"operational_window_{key}_{timestamp_key}_invalid",
                label=f"{label}.{key}.{timestamp_key}",
                blockers=blockers,
            )
            if parsed is not None:
                timestamps.setdefault(key, {})[timestamp_key] = parsed
    current_time = now_utc()
    for key, parsed in timestamps.items():
        start = parsed.get("start_utc")
        end = parsed.get("end_utc")
        if start is not None and end is not None:
            if start >= end:
                add(blockers, f"operational_window_{key}_not_forward", f"{label}.{key}.end_utc")
            if end > current_time:
                add(
                    blockers,
                    f"operational_window_{key}_ends_in_future",
                    f"{label}.{key}.end_utc",
                    end_utc=window.get(key, {}).get("end_utc") if isinstance(window.get(key), dict) else None,
                )
    approved = timestamps.get("approved_window", {})
    actual = timestamps.get("actual_capture", {})
    rollback_timestamps = timestamps.get("rollback_window", {})
    if actual.get("start_utc") is not None and approved.get("start_utc") is not None:
        if actual["start_utc"] < approved["start_utc"]:
            add(blockers, "operational_window_actual_capture_starts_before_approved_window", f"{label}.actual_capture.start_utc")
    if actual.get("end_utc") is not None and approved.get("end_utc") is not None:
        if actual["end_utc"] > approved["end_utc"]:
            add(blockers, "operational_window_actual_capture_ends_after_approved_window", f"{label}.actual_capture.end_utc")
    if rollback_timestamps.get("start_utc") is not None and actual.get("end_utc") is not None:
        if rollback_timestamps["start_utc"] < actual["end_utc"]:
            add(blockers, "operational_window_rollback_starts_before_capture_end", f"{label}.rollback_window.start_utc")
    target = window.get("target")
    if not isinstance(target, dict) or not target.get("instance") or not target.get("map"):
        add(blockers, "operational_window_target_missing", f"{label}.target")
    copied = window.get("copied_log")
    if not isinstance(copied, dict):
        add(blockers, "operational_window_copied_log_missing", f"{label}.copied_log")
        return lifecycle_correlation_proof
    unexpected_copied_keys = set(copied) - ALLOWED_OPERATIONAL_WINDOW_COPIED_LOG_KEYS
    if unexpected_copied_keys:
        add(
            blockers,
            "operational_window_copied_log_keys_unexpected",
            f"{label}.copied_log",
            unexpected=sorted(unexpected_copied_keys),
        )
    if copied.get("path_status") != EXPECTED_COPIED_LOG_PATH_STATUS:
        add(
            blockers,
            "operational_window_copied_log_path_status_mismatch",
            f"{label}.copied_log.path_status",
            expected=EXPECTED_COPIED_LOG_PATH_STATUS,
        )
    copied_symlink_component = symlink_component_for_path_text(copied.get("path"))
    if copied_symlink_component is not None:
        add(
            blockers,
            "operational_window_copied_log_path_symlink_component",
            f"{label}.copied_log.path",
            symlink=str(copied_symlink_component),
        )
    if not source_path_is_copied_or_offline(copied.get("path")):
        add(blockers, "operational_window_copied_log_path_not_copied_or_offline", f"{label}.copied_log.path")
    elif not source_path_is_approved_offline_workspace(copied.get("path")):
        add(
            blockers,
            "operational_window_copied_log_path_not_approved_offline_workspace",
            f"{label}.copied_log.path",
        )
    evidence = summary.get("evidence") if isinstance(summary, dict) else None
    sources = evidence.get("sources") if isinstance(evidence, dict) else None
    if not isinstance(sources, list) or not sources or not isinstance(sources[0], dict):
        add(blockers, "operational_window_source_summary_source_missing", "$.source_summary.evidence.sources")
        return lifecycle_correlation_proof
    source = sources[0]
    copied_path_text = copied.get("path")
    source_path_text = source.get("path")
    copied_path: Path | None = None
    if not isinstance(copied_path_text, str) or not copied_path_text:
        add(blockers, "operational_window_copied_log_path_missing", f"{label}.copied_log.path")
    else:
        copied_path = Path(copied_path_text).expanduser()
    if not isinstance(source_path_text, str) or not source_path_text:
        add(
            blockers,
            "operational_window_source_summary_source_path_missing",
            "$.source_summary.evidence.sources[0].path",
        )
    elif copied_path is not None:
        source_path = Path(source_path_text).expanduser()
        if copied_path.resolve() != source_path.resolve():
            add(blockers, "operational_window_copied_log_path_mismatch", f"{label}.copied_log.path")
    run_id = window.get("run_id")
    if isinstance(run_id, str) and copied_path is not None:
        expected_tail = (EXPECTED_COPIED_LOG_PARENT, run_id, "Obelisk.log")
        if copied_path.parts[-3:] != expected_tail:
            add(
                blockers,
                "operational_window_copied_log_path_not_live_validation_run_log",
                f"{label}.copied_log.path",
                expected="/".join(expected_tail),
            )
    copied_status = approved_artifact_status(copied)
    if copied_status is not None and copied_status.resolved.is_file():
        try:
            copied_lines = copied_status.resolved.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            add(blockers, "operational_window_copied_log_unreadable", f"{label}.copied_log.path", error=str(exc))
        else:
            copied_log_proof = validate_copied_log_lifecycle_events_inside_capture_window(
                copied_lines,
                actual_capture=timestamps.get("actual_capture", {}),
                blockers=blockers,
                strict_rejected_start_diagnostics=strict_rejected_start_diagnostics,
            )
            lifecycle_correlation_proof = validate_lifecycle_correlation_proof(
                summary=summary,
                window=window,
                copied_log_proof=copied_log_proof,
                blockers=blockers,
            )
    if copied.get("sha256") != source.get("sha256"):
        add(blockers, "operational_window_copied_log_sha256_mismatch", f"{label}.copied_log.sha256")
    window_commit = window.get("obelisk_commit")
    if window_commit != evidence.get("obelisk_commit"):
        add(blockers, "operational_window_obelisk_commit_mismatch", f"{label}.obelisk_commit")
    if not isinstance(window_commit, str) or GIT_COMMIT_RE.fullmatch(window_commit) is None:
        add(blockers, "operational_window_obelisk_commit_invalid", f"{label}.obelisk_commit")
    else:
        current_commit = current_obelisk_commit()
        if current_commit is None:
            add(
                blockers,
                "operational_window_current_obelisk_commit_unavailable",
                f"{label}.obelisk_commit",
            )
        elif window_commit != current_commit:
            add(
                blockers,
                "operational_window_obelisk_commit_not_current_head",
                f"{label}.obelisk_commit",
                expected=current_commit,
                actual=window_commit,
            )
    run_id = window.get("run_id") if isinstance(window.get("run_id"), str) else None
    sidecar_base_dir = operational_window_sidecar_dir(window)
    validate_operational_window_artifact(
        window.get("manifest"),
        f"{label}.manifest",
        blockers,
        run_id=run_id,
        expected_name="window-manifest.env",
        base_dir=sidecar_base_dir,
    )
    validate_operational_window_artifact(
        window.get("request_pack"),
        f"{label}.request_pack",
        blockers,
        run_id=run_id,
        expected_name="window-request.json",
        base_dir=sidecar_base_dir,
    )
    validate_operational_window_artifact(
        window.get("observer_env"),
        f"{label}.observer_env",
        blockers,
        run_id=run_id,
        expected_name="observer-window.env",
        base_dir=sidecar_base_dir,
    )
    validate_operational_window_artifact(
        window.get("operator_approval_receipt"),
        f"{label}.operator_approval_receipt",
        blockers,
        run_id=run_id,
        expected_name="operator-approval-receipt.json",
        base_dir=sidecar_base_dir,
    )
    request_payload = validate_request_pack_binding(window, blockers)
    validate_observer_env_binding(window, request_payload, blockers)
    validate_operator_approval_receipt_binding(window, blockers)
    preflight = window.get("preflight")
    if not isinstance(preflight, dict):
        add(blockers, "operational_window_preflight_missing", f"{label}.preflight")
    else:
        unexpected_preflight_keys = set(preflight) - ALLOWED_OPERATIONAL_WINDOW_PREFLIGHT_KEYS
        if unexpected_preflight_keys:
            add(
                blockers,
                "operational_window_preflight_keys_unexpected",
                f"{label}.preflight",
                unexpected=sorted(unexpected_preflight_keys),
            )
        validate_operational_window_artifact(
            preflight.get("pre"),
            f"{label}.preflight.pre",
            blockers,
            run_id=run_id,
            expected_name="preflight-pre.json",
            base_dir=sidecar_base_dir,
        )
        validate_operational_window_artifact(
            preflight.get("post"),
            f"{label}.preflight.post",
            blockers,
            run_id=run_id,
            expected_name="preflight-post.json",
            base_dir=sidecar_base_dir,
        )
        validate_preflight_bindings(window, blockers)
    validate_operational_window_sibling_set(window, blockers, timestamps=timestamps)

    posture = window.get("posture")
    if not isinstance(posture, dict):
        add(blockers, "operational_window_posture_missing", f"{label}.posture")
    else:
        unexpected_posture_keys = set(posture) - ALLOWED_OPERATIONAL_WINDOW_POSTURE_KEYS
        if unexpected_posture_keys:
            add(
                blockers,
                "operational_window_posture_keys_unexpected",
                f"{label}.posture",
                unexpected=sorted(unexpected_posture_keys),
            )
        expected_posture = {
            "pre_check": "passed",
            "post_check": "passed",
            "pre_posture": "stable",
            "post_posture": "stable",
            "plugins_disabled": True,
            "scanner_disabled": True,
            "dispatch_limit": "0",
            "wrapper_profile": "observer-debug",
            "observer_exclusivity": "player_principal_lifecycle_only",
            "sibling_marker_entries": "absent",
            "sibling_observer_env": "absent",
            "debug_escape_markers": "absent",
            "callback_escape_markers": "absent",
            "native_exec_disabled": True,
            "ptrace_disabled": True,
            "single_module_summary": MODULE,
        }
        for key, expected in expected_posture.items():
            if posture.get(key) != expected:
                add(blockers, "operational_window_posture_mismatch", f"{label}.posture.{key}", expected=expected)
    rollback = window.get("rollback")
    if not isinstance(rollback, dict):
        add(blockers, "operational_window_rollback_missing", f"{label}.rollback")
    else:
        unexpected_rollback_keys = set(rollback) - ALLOWED_OPERATIONAL_WINDOW_ROLLBACK_KEYS
        if unexpected_rollback_keys:
            add(
                blockers,
                "operational_window_rollback_keys_unexpected",
                f"{label}.rollback",
                unexpected=sorted(unexpected_rollback_keys),
            )
        for key in ("completed",):
            if rollback.get(key) is not True:
                add(blockers, "operational_window_rollback_not_complete", f"{label}.rollback.{key}")
        for key in ("observer_env_survived", "observer_marker_survived"):
            if rollback.get(key) is not False:
                add(blockers, "operational_window_rollback_marker_survived", f"{label}.rollback.{key}")
        if rollback.get("delta") != EXPECTED_ROLLBACK_DELTA:
            add(
                blockers,
                "operational_window_rollback_delta_mismatch",
                f"{label}.rollback.delta",
                expected=EXPECTED_ROLLBACK_DELTA,
            )
    claims = window.get("claims")
    if not isinstance(claims, dict) or claims.get("delivery_claim") != "none" or claims.get("principal_claim") != "none":
        add(blockers, "operational_window_claims_not_none", f"{label}.claims")
    elif set(claims) - ALLOWED_OPERATIONAL_WINDOW_CLAIMS_KEYS:
        add(
            blockers,
            "operational_window_claims_keys_unexpected",
            f"{label}.claims",
            unexpected=sorted(set(claims) - ALLOWED_OPERATIONAL_WINDOW_CLAIMS_KEYS),
        )
    if window.get("user_policy") not in {"no_regular_users", "operator_approved_beta_users"}:
        add(blockers, "operational_window_user_policy_unapproved", f"{label}.user_policy")
    if window.get("notice_sent") not in {"true", "false", "not_applicable"}:
        add(blockers, "operational_window_notice_sent_invalid", f"{label}.notice_sent")
    if window.get("user_policy") == "operator_approved_beta_users" and window.get("notice_sent") != "true":
        add(blockers, "operational_window_beta_user_policy_requires_notice_sent", f"{label}.notice_sent")
    if window.get("user_policy") == "no_regular_users" and window.get("notice_sent") != "not_applicable":
        add(blockers, "operational_window_no_regular_users_notice_must_be_not_applicable", f"{label}.notice_sent")
    if window.get("log_budget") != "10":
        add(blockers, "operational_window_log_budget_mismatch", f"{label}.log_budget", expected="10")
    non_claims = window.get("non_claims")
    if not isinstance(non_claims, list) or set(non_claims) != set(REQUIRED_OPERATIONAL_WINDOW_NON_CLAIMS):
        add(
            blockers,
            "operational_window_non_claims_mismatch",
            f"{label}.non_claims",
            expected=sorted(REQUIRED_OPERATIONAL_WINDOW_NON_CLAIMS),
        )
    replay_operational_window_manifest(window, blockers)
    return lifecycle_correlation_proof


def validate_consumer_boundary(cases: Any, blockers: list[dict[str, Any]]) -> list[str]:
    if not isinstance(cases, list):
        add(blockers, "consumer_boundary_cases_not_list", "$.consumer_boundary_cases")
        return []
    seen: list[str] = []
    for index, case in enumerate(cases):
        label = f"$.consumer_boundary_cases[{index}]"
        if not isinstance(case, dict):
            add(blockers, "consumer_boundary_case_invalid", label)
            continue
        unexpected_case_keys = set(case) - ALLOWED_CONSUMER_CASE_KEYS
        if unexpected_case_keys:
            add(
                blockers,
                "consumer_boundary_case_keys_unexpected",
                label,
                unexpected=sorted(unexpected_case_keys),
            )
        name = case.get("case")
        if not isinstance(name, str):
            add(blockers, "consumer_boundary_case_missing", f"{label}.case")
            continue
        seen.append(name)
        if name not in REQUIRED_CONSUMER_CASES:
            add(blockers, "consumer_boundary_case_unexpected", f"{label}.case", case=name)
        if case.get("result") != "fail_closed":
            add(blockers, "consumer_boundary_case_not_fail_closed", f"{label}.result", case=name)
        if case.get("provenance") != "consumer_boundary_assertion_not_runtime_observation":
            add(
                blockers,
                "consumer_boundary_case_provenance_mismatch",
                f"{label}.provenance",
                case=name,
            )
        if case.get("runtime_observed") is not False:
            add(
                blockers,
                "consumer_boundary_runtime_observed_not_false",
                f"{label}.runtime_observed",
                case=name,
            )
        for key in ("lookup_allowed", "mutation_allowed", "return_override_allowed", "public_sdk_surface"):
            if case.get(key) is not False:
                add(blockers, f"consumer_boundary_{key}_not_false", f"{label}.{key}", case=name)
    missing = REQUIRED_CONSUMER_CASES - set(seen)
    if missing:
        add(blockers, "consumer_boundary_cases_missing", "$.consumer_boundary_cases", missing=sorted(missing))
    return sorted(set(seen))


def validate_privacy(boundary: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(boundary, dict):
        add(blockers, "privacy_boundary_missing", "$.privacy_boundary")
        return
    unexpected_keys = set(boundary) - PRIVACY_BOUNDARY_KEYS
    if unexpected_keys:
        add(
            blockers,
            "privacy_boundary_keys_unexpected",
            "$.privacy_boundary",
            unexpected=sorted(unexpected_keys),
        )
    for key in ("copied_opaque_principal_only", "redacted_runtime_observer", "player_identifiers_logged"):
        expected = False if key == "player_identifiers_logged" else True
        if boundary.get(key) is not expected:
            add(blockers, f"privacy_boundary_{key}_mismatch", f"$.privacy_boundary.{key}")
    for key in ("lookup_allowed", "resource_handle_allowed", "mutation_allowed", "return_override_allowed"):
        if boundary.get(key) is not False:
            add(blockers, f"privacy_boundary_{key}_not_false", f"$.privacy_boundary.{key}")


def validate_approval(approval: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(approval, dict):
        add(blockers, "approval_missing", "$.approval")
        return
    unexpected_keys = set(approval) - ALLOWED_APPROVAL_KEYS
    if unexpected_keys:
        add(blockers, "approval_keys_unexpected", "$.approval", unexpected=sorted(unexpected_keys))
    if approval.get("runtime_evidence_reviewed") is not True:
        add(blockers, "approval_runtime_evidence_reviewed_not_true", "$.approval.runtime_evidence_reviewed")
    for key in ("reviewed_by", "review_note"):
        value = approval.get(key)
        if not isinstance(value, str) or not value.strip():
            add(blockers, f"approval_{key}_missing_or_empty", f"$.approval.{key}")
        elif FORBIDDEN_KEY_RE.search(value):
            add(blockers, f"approval_{key}_forbidden_identity_or_ue_text", f"$.approval.{key}")
    for key in (
        "runtime_work_authorized_by_this_manifest",
        "server_operations_authorized_by_this_manifest",
        "publication_authorized_by_this_manifest",
        "discord_authorized_by_this_manifest",
    ):
        if approval.get(key) is not False:
            add(blockers, f"approval_{key}_not_false", f"$.approval.{key}")


def validate_promotion_gate(gate: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(gate, dict):
        add(blockers, "promotion_gate_missing", "$.promotion_gate")
        return
    unexpected_keys = set(gate) - ALLOWED_PROMOTION_GATE_KEYS
    if unexpected_keys:
        add(blockers, "promotion_gate_keys_unexpected", "$.promotion_gate", unexpected=sorted(unexpected_keys))
    if gate.get("runtime_evidence_ready") is not True:
        add(blockers, "promotion_gate_runtime_evidence_ready_not_true", "$.promotion_gate.runtime_evidence_ready")
    for key in ("ready", "promotion_ready", "public_sdk_ready", "runtime_ready"):
        if gate.get(key) is not False:
            add(blockers, f"promotion_gate_{key}_not_false", f"$.promotion_gate.{key}")


def validate_no_public_contract_surface(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    for key in (
        "promotion_ready",
        "public_header_allowed",
        "public_abi_ready",
        "public_sdk_ready",
        "v1_completion_ready",
        "runtime_ready",
    ):
        if payload.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.{key}")
    for key in ("public_capability_bits_now", "public_callback_abi_now"):
        value = payload.get(key)
        if value != []:
            add(blockers, f"{key}_not_empty", f"$.{key}")


def find_forbidden_key(value: Any, trail: str = "$") -> tuple[str, str] | None:
    if (
        trail in ALLOWED_FORBIDDEN_LEAF_PATHS
        or DIAGNOSTIC_PROPERTY_FNAME_CHAIN_ALLOWED_LEAF_PATH_RE.fullmatch(trail) is not None
        or STRICT_TRIPLET_CANDIDATE_SUMMARY_ALLOWED_LEAF_PATH_RE.fullmatch(trail) is not None
    ):
        return None
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if (
                child_trail not in ALLOWED_FORBIDDEN_KEY_PATHS
                and DIAGNOSTIC_PROPERTY_FNAME_CHAIN_ALLOWED_KEY_PATH_RE.fullmatch(child_trail) is None
                and str(key) not in ALLOWED_FORBIDDEN_KEY_NAMES
                and FORBIDDEN_KEY_RE.search(str(key))
                and child not in ([], {}, None)
            ):
                return str(key), child_trail
            found = find_forbidden_key(child, child_trail)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_forbidden_key(child, f"{trail}[{index}]")
            if found is not None:
                return found
    elif (
        isinstance(value, str)
        and not any(token in trail for token in NEGATIVE_CONTEXT_TOKENS)
        and FORBIDDEN_KEY_RE.search(value)
        and "does not expose" not in value
    ):
        return value, trail
    return None


def find_positive_capability_claim(value: Any, trail: str = "$") -> tuple[str, str] | None:
    if isinstance(value, dict):
        if split_guardrail_alias_claim(value):
            return "split_positive_readiness_or_progress_alias", trail
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if (
                trail == f"$.source_summary.modules.{MODULE}"
                and normalized_guardrail_alias_key(key) in SOURCE_SUMMARY_LIFECYCLE_METADATA_POSITIVE_KEYS
            ):
                found = find_positive_capability_claim(child, child_trail)
                if found is not None:
                    return found
                continue
            if (
                child is not False
                and child is not None
                and contains_unnegated_positive_capability_claim(str(key))
            ):
                return str(key), child_trail
            if guardrail_alias_key_is_forbidden(key) and guardrail_alias_value_is_positive(child):
                return str(key), child_trail
            if (
                guardrail_acceptance_alias_key_is_forbidden(key, trail)
                and guardrail_alias_value_is_positive(child)
            ):
                return str(key), child_trail
            if guardrail_path_context_implies_positive_claim(key, child, trail):
                return str(key), child_trail
            if (
                normalized_guardrail_alias_key(key) in GENERIC_STATUS_ALIAS_KEYS
                and guardrail_alias_value_is_positive(child)
            ):
                return str(key), child_trail
            found = find_positive_capability_claim(child, child_trail)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_positive_capability_claim(child, f"{trail}[{index}]")
            if found is not None:
                return found
    elif (
        isinstance(value, str)
        and not is_allowed_non_claim_value(value)
        and (
            contains_unnegated_positive_capability_claim(value)
            or (is_readiness_alias_context(trail) and is_forbidden_readiness_alias(value))
        )
    ):
        return value, trail
    return None


def find_nested_approved_runtime_manifest_schema(value: Any, trail: str = "$") -> str | None:
    if isinstance(value, dict):
        if trail != "$" and value.get("schema") == SCHEMA:
            return f"{trail}.schema"
        for key, child in value.items():
            found = find_nested_approved_runtime_manifest_schema(child, f"{trail}.{key}")
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_nested_approved_runtime_manifest_schema(child, f"{trail}[{index}]")
            if found is not None:
                return found
    return None


def contains_unnegated_positive_capability_claim(value: str) -> bool:
    normalized = normalize_capability_claim_text(value)
    for pattern in (POSITIVE_CAPABILITY_CLAIM_RE, OPERATIONAL_AUTHORIZATION_CLAIM_RE):
        for match in pattern.finditer(normalized):
            if not positive_capability_claim_is_negated(normalized, match.start()):
                return True
    return False


def normalize_capability_claim_text(value: str) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    separated = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", separated)
    return re.sub(r"\s+", " ", separated)


def positive_capability_claim_is_negated(value: str, claim_start: int) -> bool:
    preceding_clause = NEGATION_SCOPE_SPLIT_RE.split(value[:claim_start])[-1]
    return bool(
        NEGATED_CAPABILITY_ACTION_RE.search(preceding_clause)
        or NEGATED_CAPABILITY_BOUNDARY_RE.search(preceding_clause)
    )


def validate_manifest(
    payload: dict[str, Any],
    *,
    check_mode: str,
    input_path: Path | None = None,
) -> Validation:
    blockers: list[dict[str, Any]] = []
    strict_rejected_start_diagnostics = default_strict_rejected_start_diagnostics()
    input_path_alias_reasons = (
        non_approved_runtime_evidence_input_path_alias_reasons(input_path)
        if input_path is not None
        else []
    )
    if payload.get("schema") != SCHEMA:
        add(blockers, "schema_mismatch", "$.schema")
        schema = payload.get("schema")
        if isinstance(schema, str):
            reason = NON_APPROVED_RUNTIME_EVIDENCE_SCHEMA_BLOCKERS.get(schema)
            if reason is None:
                reason = non_approved_runtime_evidence_schema_alias_reason(schema)
            if reason is not None:
                add(blockers, reason, "$.schema", schema=schema)
        for reason in input_path_alias_reasons:
            add(blockers, reason, "$input_path", path=str(input_path))
        return Validation(
            blockers,
            [],
            [],
            strict_rejected_start_diagnostics,
            strict_lifecycle_triplet_selection(None),
            None,
            {},
        )
    for reason in input_path_alias_reasons:
        add(blockers, reason, "$input_path", path=str(input_path))
    missing = REQUIRED_TOP_LEVEL_KEYS - set(payload)
    unexpected = set(payload) - REQUIRED_TOP_LEVEL_KEYS
    if missing:
        add(blockers, "top_level_fields_missing_required", "$", missing=sorted(missing))
    if unexpected:
        add(blockers, "top_level_fields_unexpected", "$", unexpected=sorted(unexpected))
    validate_approved_intake_classification(payload, blockers)
    if payload.get("approved_runtime_evidence_present") is not True:
        add(blockers, "approved_runtime_evidence_present_not_true", "$.approved_runtime_evidence_present")
    if payload.get("runtime_evidence_ready") is not True:
        add(blockers, "runtime_evidence_ready_not_true", "$.runtime_evidence_ready")
    validate_no_public_contract_surface(payload, blockers)
    validate_approval(payload.get("approval"), blockers)
    validate_output_artifact_identity(payload, blockers)
    source_summary = payload.get("source_summary")
    observed_runtime_cases = validate_runtime_summary(source_summary, blockers)
    module = player_principal_lifecycle_module(source_summary)
    strict_lifecycle_selection = strict_lifecycle_triplet_selection(
        module.get("observed_event_cases") if isinstance(module, dict) else None
    )
    session_end_missing_correlation_diagnostics = (
        session_end_missing_correlation_diagnostics_from_module(module)
    )
    lifecycle_correlation_proof = validate_operational_window(
        payload.get("operational_window"),
        source_summary,
        blockers,
        strict_rejected_start_diagnostics=strict_rejected_start_diagnostics,
    )
    if lifecycle_correlation_proof.get("accepted") is not True:
        add(
            blockers,
            "runtime_lifecycle_correlation_proof_missing",
            "$.source_summary.modules.player_principal_lifecycle.observed_event_cases",
            proof=lifecycle_correlation_proof,
        )
    consumer_cases = validate_consumer_boundary(payload.get("consumer_boundary_cases"), blockers)
    validate_privacy(payload.get("privacy_boundary"), blockers)
    validate_promotion_gate(payload.get("promotion_gate"), blockers)
    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_NON_CLAIMS.issubset(set(non_claims)):
        add(blockers, "non_claims_missing_required", "$.non_claims")
    forbidden = find_forbidden_key(payload)
    if forbidden is not None:
        value, trail = forbidden
        add(blockers, "forbidden_identity_or_ue_internal_leakage", trail, value=value)
    positive_claim = find_positive_capability_claim(payload)
    if positive_claim is not None:
        value, trail = positive_claim
        add(blockers, "forbidden_public_capability_or_readiness_claim", trail, value=value)
    role_alias_claim = find_lifecycle_role_alias_claim(payload)
    if role_alias_claim is not None:
        value, trail = role_alias_claim
        add(blockers, "forbidden_lifecycle_role_alias_claim", trail, value=value)
    nested_approved_schema = find_nested_approved_runtime_manifest_schema(payload)
    if nested_approved_schema is not None:
        add(
            blockers,
            "nested_approved_runtime_manifest_schema_duplicate",
            nested_approved_schema,
            schema=SCHEMA,
        )
    if check_mode != "consume":
        add(blockers, f"{check_mode}_blocked_until_identity_public_contract_gate", "$.promotion_gate")
    return Validation(
        blockers,
        observed_runtime_cases,
        consumer_cases,
        strict_rejected_start_diagnostics,
        strict_lifecycle_selection,
        session_end_missing_correlation_diagnostics,
        lifecycle_correlation_proof,
    )


NON_EVIDENCE_REASON_FRAGMENTS = (
    "not_approved_lifecycle_evidence",
    "is_not_approved_runtime_evidence",
    "contains_diagnostic_candidates",
    "contains_diagnostic_lifecycle_lines",
    "contains_passive_monitor_metadata",
    "contains_unsafe_player_text",
    "synthetic_shape_fixture",
)
ARTIFACT_PATH_ISSUE_REASONS = frozenset(
    (
        "source_summary_source_file_missing",
        "source_summary_source_sha256_mismatch",
        "operational_window_artifact_file_missing",
        "operational_window_artifact_sha256_mismatch",
        "operational_window_required_sibling_artifact_missing",
        "operational_window_implicit_sidecar_missing",
        "operational_window_sidecar_not_exact_copied_log_sibling",
        "operational_window_installed_libobelisk_sidecar_missing_for_replacement",
        "operational_window_post_restart_preflight_sidecar_missing",
    )
)


def non_evidence_reasons(blockers: list[dict[str, Any]]) -> list[str]:
    return [
        str(blocker["reason"])
        for blocker in blockers
        if any(fragment in str(blocker["reason"]) for fragment in NON_EVIDENCE_REASON_FRAGMENTS)
    ]


def artifact_path_issues(blockers: list[dict[str, Any]]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for blocker in blockers:
        if blocker.get("reason") not in ARTIFACT_PATH_ISSUE_REASONS:
            continue
        issue = {
            "reason": str(blocker["reason"]),
            "label": str(blocker["label"]),
        }
        for key in ("expected", "actual", "path"):
            value = blocker.get(key)
            if isinstance(value, str):
                issue[key] = value
        issues.append(issue)
    return issues


def build_report(payload: dict[str, Any], validation: Validation, *, check_mode: str) -> dict[str, Any]:
    readiness_mode_blockers = {
        "promote_blocked_until_identity_public_contract_gate",
        "public_readiness_blocked_until_identity_public_contract_gate",
        "runtime_readiness_blocked_until_identity_public_contract_gate",
    }
    evidence_blockers = [
        blocker
        for blocker in validation.blockers
        if blocker["reason"] not in readiness_mode_blockers
    ]
    evidence_accepted = not evidence_blockers
    accepted = not validation.blockers
    missing_lifecycle_event_roles = validation.strict_lifecycle_triplet_selection.get(
        "missing_roles",
        [],
    )
    if not isinstance(missing_lifecycle_event_roles, list):
        missing_lifecycle_event_roles = []
    observer_no_lifecycle_role_diagnostics = None
    if (
        not evidence_accepted
        and missing_lifecycle_event_roles == list(READY_LOG_COPY_REQUIRED_ROLES)
    ):
        observer_no_lifecycle_role_diagnostics = {
            "observer_only_no_role_window_detected": "observer_enable" in validation.observed_runtime_cases,
            "player_present_but_no_lifecycle_roles": False,
            "source_log_not_ready_reason": "approved_manifest_missing_lifecycle_roles",
            "source_log_not_ready_blockers": ["approved_manifest_missing_lifecycle_roles"],
            "roles_present": [],
            "missing_roles": missing_lifecycle_event_roles,
            "copy_readiness": "blocked_missing_lifecycle_roles",
            "reported_blockers": ["approved_runtime_evidence_not_accepted"],
            "player_presence_context": {},
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
        }
    return {
        "schema": REPORT_SCHEMA,
        "input_schema": payload.get("schema"),
        "mode": check_mode,
        "ready": accepted,
        "ready_scope": "runtime_evidence_only",
        "approved_runtime_evidence_present": evidence_accepted,
        "runtime_evidence_ready": evidence_accepted,
        "promotion_ready": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_sdk_ready": False,
        "v1_completion_ready": False,
        "runtime_ready": False,
        "stable_claim_allowed": False,
        "complete_sdk_allowed": False,
        "complete_sdk_ready": False,
        "sdk_surfaces_promoted_by_this_checker": 0,
        "p0_surfaces_promoted_by_this_checker": 0,
        "accepted_runtime_evidence_counts_as_sdk_progress": False,
        "accepted_runtime_evidence_counts_as_p0_progress": False,
        "post_runtime_contract_gate_required": True,
        "post_runtime_contract_gate": NEXT_BLOCKER_AFTER_RUNTIME_EVIDENCE,
        "public_capability_bits_now": [],
        "public_callback_abi_now": [],
        "remaining_blockers": [] if evidence_accepted else ["approved_runtime_evidence_not_accepted"],
        "next_blocker": (
            NEXT_BLOCKER_AFTER_RUNTIME_EVIDENCE
            if evidence_accepted
            else "approved_runtime_evidence_not_accepted"
        ),
        "current_route_blocker": None if evidence_accepted else APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER,
        "next_required_artifact": (
            None
            if evidence_accepted
            else APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_EVIDENCE_BUNDLE
        ),
        "missing_required_artifact": (
            None
            if evidence_accepted
            else APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_EVIDENCE_BUNDLE
        ),
        "required_artifact_status": "accepted" if evidence_accepted else "missing_or_not_accepted",
        "fastest_next_action": (
            None
            if evidence_accepted
            else approved_runtime_evidence_missing_next_action(
                validation.strict_rejected_start_diagnostics,
                observer_no_lifecycle_role_diagnostics,
                validation.session_end_missing_correlation_diagnostics,
            )
        ),
        "observed_runtime_cases": validation.observed_runtime_cases,
        "required_lifecycle_event_role_triplet": list(READY_LOG_COPY_REQUIRED_ROLES),
        "missing_lifecycle_event_roles": missing_lifecycle_event_roles,
        "strict_lifecycle_triplet_selection": validation.strict_lifecycle_triplet_selection,
        "strict_lifecycle_triplet_selected": (
            validation.strict_lifecycle_triplet_selection.get("accepted") is True
        ),
        "strict_lifecycle_triplet_non_counting_context_event_count": (
            validation.strict_lifecycle_triplet_selection.get("non_counting_context_event_count", 0)
        ),
        "strict_lifecycle_triplet_non_counting_context_roles": (
            validation.strict_lifecycle_triplet_selection.get("non_counting_context_roles", [])
        ),
        "lifecycle_correlation_proof": validation.lifecycle_correlation_proof,
        "session_end_missing_correlation_diagnostics": (
            validation.session_end_missing_correlation_diagnostics
        ),
        "consumer_cases": validation.consumer_cases,
        "consumer_boundary_assertions": validation.consumer_cases,
        "partial_start_end_present": validation.strict_rejected_start_diagnostics.get(
            "partial_start_end_present",
            False,
        ),
        "missing_strict_rejected_start": validation.strict_rejected_start_diagnostics.get(
            "missing_strict_rejected_start",
            False,
        ),
        "strict_rejected_start_expected_shape": validation.strict_rejected_start_diagnostics.get(
            "strict_rejected_start_expected_shape",
            STRICT_REJECTED_START_EXPECTED_SHAPE,
        ),
        "strict_rejected_start_observed_shape": validation.strict_rejected_start_diagnostics.get(
            "strict_rejected_start_observed_shape",
        ),
        "non_evidence_reasons": non_evidence_reasons(validation.blockers),
        "artifact_path_issues": artifact_path_issues(validation.blockers),
        "blockers": [blocker["reason"] for blocker in validation.blockers],
        "blocker_details": validation.blockers,
        "non_claims": [
            "runtime evidence acceptance does not promote public SDK identity, permissions, commands, lookup, mutation, or v1 readiness",
        ],
    }


def main() -> int:
    args = parse_args()
    check_mode = mode(args)
    payload = load_json(args.manifest)
    validation = validate_manifest(payload, check_mode=check_mode, input_path=args.manifest)
    report = build_report(payload, validation, check_mode=check_mode)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif validation.blockers:
        for blocker in validation.blockers:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    return 0 if not validation.blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
