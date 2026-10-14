#!/usr/bin/env python3
"""Execute the offline preactivation steps for a runtime evidence window.

This tool intentionally stops before live operations. It can create the request
pack, validate it, render the beta-test notice dry-run, capture the route gate,
and optionally run activation preconditions against a separately supplied
confirmed beta-notice report. It does not send Discord, touch ARK servers, edit
markers/env, read live logs, copy runtime logs, build approved runtime evidence,
or claim SDK readiness.
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
from plan_player_principal_lifecycle_runtime_window import (
    DEFAULT_OUTPUT_ROOT,
    MIN_RUNTIME_WINDOW_LEAD_SECONDS,
    SCHEMA as PLAN_SCHEMA,
    build_plan,
    fresh_retry_after_closed_non_evidence_window,
)
from prepare_player_principal_lifecycle_window_request import (
    DIAGNOSTIC_CANDIDATES_ENV_KEY,
    HANDLE_NEW_PLAYER_FUNCTION,
    SESSION_START_REJECTED_REQUIRED_ARGUMENTS,
    SESSION_START_REJECTED_REQUIRED_CALL,
    SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS,
    SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES,
    SESSION_START_REJECTED_REQUIRED_FUNCTION,
)


SCHEMA = "obelisk.player-principal-lifecycle-runtime-window-execution.v1"
REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = Path("/servidor/ark")
FALSE_FLAGS = {
    "activation_allowed": False,
    "authorizes_discord": False,
    "authorizes_discord_send": False,
    "authorizes_live_log_reads": False,
    "authorizes_live_ops": False,
    "authorizes_marker_env_writes": False,
    "authorizes_marker_or_env_changes": False,
    "authorizes_runtime_work": False,
    "authorizes_server_restart": False,
    "authorizes_server_operations": False,
    "discord_sent": False,
    "live_log_read_authorized": False,
    "live_log_reads_authorized": False,
    "live_ops_authorized": False,
    "marker_env_changes_authorized": False,
    "marker_or_env_changes_authorized": False,
    "runtime_capture_authorized": False,
    "runtime_window_authorized": False,
    "server_operations_authorized": False,
    "touches_live_servers": False,
    "workspace_writes_authorized": False,
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
    "clears_approved_runtime_evidence_missing": False,
    "plugin_hub_ready": False,
    "promotion_ready": False,
    "publication_ready": False,
    "public_abi_ready": False,
    "public_sdk_ready": False,
    "runtime_ready": False,
    "sdk_evidence_ready": False,
    "stable_sdk_ready": False,
    "v1_completion_ready": False,
    "stable_claim_allowed": False,
}
NON_AUTHORIZATION = (
    "offline preactivation execution only; this report does not authorize Discord, "
    "server operations, marker/env changes, starts, restarts, live log reads, runtime "
    "capture, approved runtime evidence, public readiness, SDK completion, or P0 progress"
)
DIAGNOSTIC_CANDIDATES_NON_AUTHORIZATION = (
    "diagnostic candidates are request-pack observer diagnostics only; they are bounded by "
    "the approved window, log limit, and dispatch limit, must not include raw player text or "
    "player identity, and do not authorize runtime work or count as evidence/readiness"
)
DIAGNOSTIC_CANDIDATES_APPROVED_EVIDENCE_POLICY_SCHEMA = (
    "obelisk.player-principal-lifecycle-diagnostic-candidates-approved-evidence-policy.v1"
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
NEXT_ACTION_SCHEMA = "obelisk.player-principal-lifecycle-runtime-window-next-action.v1"
NEXT_ACTION_RUNNER_CONTRACT_SCHEMA = (
    "obelisk.player-principal-lifecycle-runtime-window-next-action-runner-contract.v1"
)
NEXT_ACTION_RUNNER_COMMAND_SCHEMA = (
    "obelisk.player-principal-lifecycle-runtime-window-next-action-runner-command.v1"
)
NEXT_ACTION_RUNNER_OPERATION_SCHEMA = (
    "obelisk.player-principal-lifecycle-runtime-window-next-action-runner-operation.v1"
)
NO_USERS_PASSIVE_WAIT_SCHEMA = (
    "obelisk.player-principal-lifecycle-no-users-passive-wait-recommendation.v1"
)
NEXT_PLAYER_BACKED_WINDOW_SCHEMA = (
    "obelisk.player-principal-lifecycle-next-player-backed-window-preparation.v1"
)
PLAYER_WARNING_BROADCAST_SCHEMA = (
    "obelisk.player-principal-lifecycle-player-warning-broadcast-recommendation.v1"
)
TWO_SERVER_CAP_SCHEMA = "obelisk.player-principal-lifecycle-two-server-cap.v1"
LIFECYCLE_ROLE_OBJECTIVES_SCHEMA = (
    "obelisk.player-principal-lifecycle-missing-role-objectives.v1"
)
RECOMMENDED_NOTICE_TEXT_SCHEMA = (
    "obelisk.player-principal-lifecycle-redacted-recommended-notice-text.v1"
)
APPROVED_EVIDENCE_BUNDLE_ACCEPTANCE_SCHEMA = (
    "obelisk.player-principal-lifecycle-approved-evidence-bundle-acceptance-required.v1"
)
POST_WINDOW_ACTION_CONTRACT_SCHEMA = "obelisk.player-principal-lifecycle-post-window-action-contract.v1"
MULTI_SURFACE_BETA_CAPTURE_PACK_BOUNDARY_SCHEMA = (
    "obelisk.multi-surface-beta-capture-pack-family-boundary.v1"
)
MULTI_SURFACE_BETA_CAPTURE_PACK_SCHEMA = "obelisk.multi-surface-beta-capture-pack.v1"
MULTI_SURFACE_BETA_CAPTURE_PLAN_SCHEMA = "obelisk.multi-surface-beta-capture-plan.v1"
MULTI_SURFACE_BETA_CAPTURE_CHECKER_MATRIX_SCHEMA = (
    "obelisk.multi-surface-beta-capture-checker-matrix.v1"
)
MULTI_SURFACE_BETA_CAPTURE_NON_CLAIM_MANIFEST_SCHEMA = (
    "obelisk.multi-surface-beta-capture-non-claim-manifest.v1"
)
MULTI_SURFACE_BETA_CAPTURE_EXECUTOR_PREPARATION_SCHEMA = (
    "obelisk.multi-surface-beta-capture-pack-executor-preparation.v1"
)
MULTI_SURFACE_BETA_CAPTURE_PREPARE_STEP_ID = "prepare_multi_surface_beta_pack"
MULTI_SURFACE_BETA_CAPTURE_CHECK_STEP_ID = "check_multi_surface_beta_pack"
MULTI_SURFACE_BETA_CAPTURE_FAMILY_SCHEMAS = frozenset(
    (
        MULTI_SURFACE_BETA_CAPTURE_PACK_SCHEMA,
        MULTI_SURFACE_BETA_CAPTURE_PLAN_SCHEMA,
        MULTI_SURFACE_BETA_CAPTURE_CHECKER_MATRIX_SCHEMA,
        MULTI_SURFACE_BETA_CAPTURE_NON_CLAIM_MANIFEST_SCHEMA,
    )
)
MULTI_SURFACE_BETA_CAPTURE_NON_AUTHORIZATION = (
    "multi-surface beta capture pack artifacts are offline candidate metadata only; "
    "they do not authorize Discord, live ops, server operations, live log reads, "
    "marker/env writes, starts, restarts, runtime capture, approved runtime evidence, "
    "SDK/P0 progress, readiness, Plugin Hub, publication, or release claims"
)
MULTI_SURFACE_BETA_CAPTURE_FALSE_FLAGS = {
    "touches_live_servers": False,
    "authorizes_runtime_work": False,
    "authorizes_discord": False,
    "authorizes_discord_send": False,
    "authorizes_live_ops": False,
    "authorizes_server_operations": False,
    "authorizes_server_restart": False,
    "authorizes_live_log_reads": False,
    "authorizes_marker_env_writes": False,
    "authorizes_marker_or_env_changes": False,
    "counts_as_approved_runtime_evidence": False,
    "counts_as_runtime_evidence": False,
    "counts_as_sdk_progress": False,
    "counts_as_p0_progress": False,
    "clears_approved_runtime_evidence_missing": False,
    "runtime_ready": False,
    "public_sdk_ready": False,
    "stable_sdk_ready": False,
    "plugin_hub_ready": False,
    "publication_ready": False,
}
EXECUTED_STEP_IDS = (
    "prepare_request_pack",
    "check_request_pack",
    "beta_notice_dry_run",
    "route_gate",
)
REQUEST_PACK_FILENAMES = (
    "window-request.json",
    "observer-window.env",
    "operator-approval-request.md",
    "operator-approval-receipt.json",
)
CONFIRMED_NOTICE_SCHEMA = "obelisk.player-principal-lifecycle-beta-notice-prep.v1"
NOTICE_ACTION_ARTIFACT_SCHEMA = (
    "obelisk.player-principal-lifecycle-beta-notice-action-artifact.v1"
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
POST_WINDOW_STATE_SCHEMA = "obelisk.player-principal-lifecycle-runtime-window-post-window-state.v1"
CLOSURE_REQUEST_SCHEMA = "obelisk.player-principal-lifecycle-evidence-closure-request.v1"
PASSIVE_LATEST_SCHEMA = "obelisk.player-principal-passive-snapshot-latest.v1"
PASSIVE_DIFF_SCHEMA = "obelisk.player-principal-passive-snapshot-diff.v1"
PASSIVE_MONITOR_ONLY_SCHEMA = "obelisk.player-principal-passive-monitor-only-summary.v1"
PASSIVE_SUMMARY_SCHEMAS = frozenset(
    (
        PASSIVE_LATEST_SCHEMA,
        PASSIVE_DIFF_SCHEMA,
        PASSIVE_MONITOR_ONLY_SCHEMA,
    )
)
EXECUTION_BOUNDARIES_SCHEMA = (
    "obelisk.player-principal-lifecycle-runtime-window-execution-boundaries.v1"
)
PREPARED_ARTIFACT_BOUNDARY_SCHEMA = (
    "obelisk.player-principal-lifecycle-prepared-artifact-boundary.v1"
)
HUMAN_LEAD_ACTION_BOUNDARY_SCHEMA = (
    "obelisk.player-principal-lifecycle-human-lead-action-boundary.v1"
)
STANDING_AUTHORITY_METADATA_SCHEMA = (
    "obelisk.player-principal-lifecycle-standing-authority-metadata-boundary.v1"
)
PASSIVE_WAIT_BOUNDARY_SCHEMA = (
    "obelisk.player-principal-lifecycle-passive-wait-boundary.v1"
)
ACTIVE_PLAYER_NO_ACCEPTED_EVENTS_SCHEMA = (
    "obelisk.player-principal-lifecycle-active-player-no-accepted-events-window-policy.v1"
)
ACTIVE_PLAYER_NO_ACCEPTED_EVENTS_BOUNDARY_SCHEMA = (
    "obelisk.player-principal-lifecycle-active-player-no-accepted-events-boundary.v1"
)
CHECKER_REQUIRED_POST_WINDOW_REPLAY_SCHEMA = (
    "obelisk.player-principal-lifecycle-checker-required-post-window-replay.v1"
)
POST_WINDOW_SOURCE_BOUNDARY_SCHEMA = (
    "obelisk.player-principal-lifecycle-post-window-source-boundary.v1"
)
RUNTIME_WINDOW_STALE_PREVENTION_SCHEMA = (
    "obelisk.player-principal-lifecycle-runtime-window-stale-prevention.v1"
)
BETA_NOTICE_SEQUENCE_ENFORCEMENT_SCHEMA = (
    "obelisk.player-principal-lifecycle-beta-notice-sequence-enforcement.v1"
)
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
SECRET_TEXT_RE = re.compile(
    r"(discord(?:app)?\.com/api/webhooks/)[^\s\"']+|"
    r"((?:WEBHOOK|TOKEN|SECRET|PASSWORD|KEY)[A-Z0-9_]*=)[^\s\"']+",
    re.IGNORECASE,
)
APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH = (
    "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
)
EVIDENCE_COMMAND_SEQUENCE_SCHEMA = (
    "obelisk.player-principal-lifecycle-evidence-command-sequence.v1"
)
COPIED_LOG_ROUTE_CONTRACT_SCHEMA = (
    "obelisk.player-principal-lifecycle-copied-log-route-contract.v1"
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
    "build_approved_runtime_evidence_bundle_from_evidence_dir",
)
POST_WINDOW_STATE_NON_AUTHORIZATION = (
    "post-window state consumption is diagnostic only; closure reports, passive summaries, "
    "monitor summaries, notice reports, executor reports, and status reports do not count as "
    "approved runtime evidence or authorize Discord, server operations, marker/env changes, "
    "starts, restarts, live log reads, runtime capture, SDK readiness, or P0 progress"
)
CLOSURE_COMPATIBLE_RUN_ID_PATTERN = r"^[0-9]{8}T[0-9]{6}Z-player-principal-lifecycle$"
RUN_ID_TEXT_RE = re.compile(r"[0-9]{8}T[0-9]{6}Z-[A-Za-z0-9_.-]+")
PASSIVE_MONITOR_SOURCE_RE = re.compile(
    r"(?:passive(?:[_ .:-]?monitor)?|monitor|post[_ .:-]?reboot|postpatch|"
    r"no[_ .:-]?(?:users?|testers?)|wait[_ .:-]?only)",
    re.IGNORECASE,
)
STALE_SOURCE_RE = re.compile(
    r"(?:stale|historical|previous|prior|old[_ .:-]?window|postpatch)",
    re.IGNORECASE,
)
NO_USERS_PASSIVE_WAIT_NON_AUTHORIZATION = (
    "no-users/passive-wait planning is wait-only operator metadata; it does not authorize "
    "server operations, marker/env changes, starts, restarts, live log reads, runtime capture, "
    "Discord, approved runtime evidence, SDK readiness, or P0 progress"
)
POST_WINDOW_FORBIDDEN_TRUE_ALIASES = {
    "accepted_runtime_evidence",
    "activation_allowed",
    "activation_authorized_by_this_report",
    "approved_bundle_accepted",
    "approved_runtime_bundle_request_accepted",
    "approved_runtime_evidence",
    "approved_runtime_evidence_accepted",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "authorizes_discord",
    "authorizes_runtime_work",
    "authorizes_server_operations",
    "authorizes_server_work",
    "authorizes_workspace_work",
    "authorizes_workspace_writes",
    "bundle_accepted",
    "bundle_report_counts_as_approved_runtime_evidence",
    "candidate_sidecars_count_as_approved_runtime_evidence",
    "candidate_pack_authorizes_discord",
    "candidate_pack_authorizes_live_log_reads",
    "candidate_pack_authorizes_live_ops",
    "candidate_pack_authorizes_marker_env_writes",
    "candidate_pack_authorizes_marker_or_env_changes",
    "candidate_pack_authorizes_runtime",
    "candidate_pack_authorizes_server_operations",
    "candidate_pack_authorizes_server_restart",
    "candidate_pack_clears_approved_runtime_evidence_missing",
    "candidate_pack_counts_as_approved_runtime_evidence",
    "candidate_pack_counts_as_runtime_evidence",
    "candidate_pack_counts_as_sdk_progress",
    "candidate_pack_counts_as_p0_progress",
    "complete_sdk_allowed",
    "complete_sdk_claim_allowed",
    "complete_sdk_ready",
    "confirmed_beta_notice_sent",
    "confirmed_notice_sent",
    "counts_as_approved_runtime_evidence",
    "counts_as_public_sdk",
    "counts_as_runtime",
    "counts_as_runtime_evidence",
    "counts_as_sdk_evidence",
    "counts_as_v1_completion",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_sdk",
    "counts_toward_v1_completion",
    "discord_authorized",
    "discord_command_emitted_by_this_report",
    "discord_sent",
    "discord_sent_by_this_report",
    "dry_run_success_counts_as_approved_runtime_evidence",
    "evidence_bundle_accepted",
    "github_publication_authorized",
    "historical_target_names_authorize_runtime",
    "live_log_read_authorized",
    "live_log_reads_authorized",
    "live_ops_authorized",
    "marker_env_changes_authorized",
    "marker_env_readiness_counts_as_approved_runtime_evidence",
    "notice_action_sent",
    "notice_sent",
    "operator_approval_authorizes_runtime",
    "operator_approval_recorded_authorizes_runtime",
    "passive_complete_triplet_counts_as_evidence",
    "passive_complete_triplets_count_as_approved_runtime_evidence",
    "passive_snapshot_evidence_allowed",
    "passive_snapshot_rollup_counts_as_approved_runtime_evidence",
    "passive_snapshots_as_evidence",
    "passive_snapshots_count_as_evidence",
    "planning_artifact_counts_as_approved_runtime_evidence",
    "planning_snapshot_counts_as_approved_runtime_evidence",
    "player_notice_action_sent",
    "player_notice_counts_as_approved_runtime_evidence",
    "player_notice_sent",
    "promotion_ready",
    "public_abi_ready",
    "public_readiness",
    "public_readiness_status",
    "public_ready",
    "public_header_allowed",
    "public_readiness_claim",
    "public_reachability_counts_as_approved_runtime_evidence",
    "public_sdk_ready",
    "publication_authorized",
    "request_pack_preflight_window_manifest_count_as_approved_runtime_evidence",
    "route_ready",
    "runtime_capture_authorized",
    "runtime_evidence_present",
    "runtime_evidence_ready",
    "runtime_ready",
    "runtime_window_authorized",
    "runtime_work_authorized",
    "sdk_evidence_ready",
    "server_operations_authorized",
    "source_material_counts_as_approved_runtime_evidence",
    "source_material_counts_as_runtime_evidence",
    "source_material_counts_as_sdk_evidence",
    "stable_claim_allowed",
    "stable_sdk_claim_allowed",
    "stable_sdk_ready",
    "status_report_counts_as_approved_runtime_evidence",
    "status_report_paths_authorize_current_turn",
    "status_report_paths_count_as_approved_runtime_evidence",
    "touches_live_servers",
    "multi_surface_beta_capture_pack_authorizes_discord",
    "multi_surface_beta_capture_pack_authorizes_live_log_reads",
    "multi_surface_beta_capture_pack_authorizes_live_ops",
    "multi_surface_beta_capture_pack_authorizes_marker_env_writes",
    "multi_surface_beta_capture_pack_authorizes_marker_or_env_changes",
    "multi_surface_beta_capture_pack_authorizes_runtime",
    "multi_surface_beta_capture_pack_authorizes_server_operations",
    "multi_surface_beta_capture_pack_authorizes_server_restart",
    "multi_surface_beta_capture_pack_clears_approved_runtime_evidence_missing",
    "multi_surface_beta_capture_pack_counts_as_approved_runtime_evidence",
    "multi_surface_beta_capture_pack_counts_as_runtime_evidence",
    "multi_surface_beta_capture_pack_counts_as_sdk_progress",
    "multi_surface_beta_capture_pack_counts_as_p0_progress",
    "multi_surface_beta_capture_pack_ready",
    "notice_status",
    "passive_monitor_status",
    "passive_observation_status",
    "passive_readiness",
    "passive_status",
    "v1_completion",
    "v1_completion_ready",
    "workspace_writes_authorized",
}
POST_WINDOW_FORBIDDEN_PROGRESS_ALIASES = {
    "claim_progress_contribution",
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_progress_contribution",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_progress_contribution",
    "p0_progress",
    "progress",
    "public_sdk_progress_contribution",
    "runtime_progress",
    "runtime_progress_contribution",
    "sdk_progress",
    "source_overclaim_total_flag_count",
    "v1_completion_contribution",
    "v1_progress",
}
POST_WINDOW_POSITIVE_STATUS_TOKENS = {
    "accepted",
    "allowed",
    "approved",
    "authorized",
    "available",
    "complete",
    "completed",
    "enabled",
    "present",
    "ready",
    "sent",
    "supported",
    "true",
    "unlocked",
    "yes",
}
POST_WINDOW_NEGATIVE_STATUS_TOKENS = {
    "blocked",
    "false",
    "missing",
    "no",
    "non",
    "none",
    "not",
    "only",
    "refused",
    "rejected",
    "required",
    "requires",
    "unsupported",
}
POST_WINDOW_CLAIM_DOMAIN_TOKENS = {
    "activation",
    "capture",
    "claim",
    "discord",
    "env",
    "environment",
    "evidence",
    "live",
    "log",
    "logs",
    "marker",
    "markers",
    "notice",
    "ops",
    "p0",
    "pack",
    "passive",
    "public",
    "readiness",
    "restart",
    "restarts",
    "route",
    "runtime",
    "sdk",
    "server",
    "stable",
    "tester",
    "testers",
    "user",
    "users",
    "v1",
    "wait",
    "write",
    "writes",
    "workspace",
}
POST_WINDOW_CLAIM_COMPLETION_TOKENS = POST_WINDOW_POSITIVE_STATUS_TOKENS | {
    "authorized",
    "authorization",
    "counts",
    "delivered",
    "progress",
}
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--map", dest="map_name", required=True)
    parser.add_argument("--start-delay-minutes", type=int, default=5)
    parser.add_argument("--duration-minutes", type=int, default=15)
    parser.add_argument(
        "--restart-expectation",
        choices=("none", "start", "restart"),
        default="none",
    )
    parser.add_argument(
        "--user-policy",
        choices=("operator_approved_beta_users",),
        default="operator_approved_beta_users",
        help="Executor is only for player-backed beta windows.",
    )
    parser.add_argument("--notice-path", default="discord-beta-testers")
    parser.add_argument("--rollback-owner", default="operator")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--obelisk-commit")
    parser.add_argument("--binary-sha256")
    parser.add_argument("--reviewed-by", default="lead")
    parser.add_argument(
        "--review-note",
        default="standing-authority consume-only runtime lifecycle evidence",
    )
    parser.add_argument(
        "--standing-launch-authority-reference",
        default="operator-2026-06-06-standing-launch-authority",
    )
    parser.add_argument("--now-utc")
    parser.add_argument(
        "--confirmed-notice-report-json",
        type=Path,
        help=(
            "Existing confirmed beta-notice report. If omitted, activation "
            "preconditions are intentionally skipped after dry-run."
        ),
    )
    parser.add_argument(
        "--post-window-state-json",
        type=Path,
        help=(
            "Existing closure report or passive summary to consume as diagnostic "
            "post-window state. This never counts as runtime evidence."
        ),
    )
    parser.add_argument(
        "--post-window-state-only",
        action="store_true",
        help=(
            "Only consume --post-window-state-json and print the diagnostic state; "
            "do not run preactivation commands or write reports."
        ),
    )
    parser.add_argument(
        "--diagnostic-candidates",
        action="store_true",
        help=(
            "Request candidate-only diagnostic observer env through the request pack. "
            "Diagnostics remain bounded, identity-free, non-evidence, and non-readiness."
        ),
    )
    parser.add_argument(
        "--prepare-multi-surface-beta-pack",
        action="store_true",
        help=(
            "Prepare and validate the offline multi-surface beta capture candidate pack "
            "under --report-dir. This remains non-authorizing and non-evidence."
        ),
    )
    parser.add_argument(
        "--active-player-no-accepted-events",
        action="store_true",
        help=(
            "Record the offline state where a player is present, the observer is enabled, "
            "and no lifecycle events were accepted; plans no restart unless a concrete "
            "deploy/gate change is supplied."
        ),
    )
    parser.add_argument(
        "--concrete-deploy-or-gate-change",
        help="Safe label for a concrete deploy/gate change that justifies requested process control.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def protected_output_dir(path: Path, label: str) -> Path:
    expanded = path.expanduser()
    status = protected_paths.protected_path_status(expanded)
    if status.protected:
        raise SystemExit(
            f"{label} must be outside /servidor/ark or under /servidor/ark/workspace-offline: "
            f"{status.resolved}"
        )
    return status.resolved


def protected_input_file(path: Path, label: str) -> Path:
    protected_paths.reject_symlink_component(path, label)
    return protected_paths.reject_protected_input_path(
        path.expanduser(),
        label,
        protected_root=SERVER_ROOT,
        approved_roots=protected_paths.approved_offline_workspace_roots(),
    )


def observer_env_diagnostic_keys_present(path: Path | str | None) -> list[str] | None:
    if path is None:
        return []
    env_path = Path(path)
    if not env_path.exists() or not env_path.is_file():
        return []
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    present: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in DIAGNOSTIC_APPROVED_EVIDENCE_ENV_KEYS and key not in present:
            present.append(key)
    return sorted(present)


def plan_args(args: argparse.Namespace) -> argparse.Namespace:
    binary_sha256 = args.binary_sha256
    if binary_sha256 is None:
        from plan_player_principal_lifecycle_runtime_window import EXPECTED_BINARY_SHA256

        binary_sha256 = EXPECTED_BINARY_SHA256
    return argparse.Namespace(
        instance=args.instance,
        map_name=args.map_name,
        start_delay_minutes=args.start_delay_minutes,
        duration_minutes=args.duration_minutes,
        restart_expectation=args.restart_expectation,
        user_policy=args.user_policy,
        notice_path=args.notice_path,
        rollback_owner=args.rollback_owner,
        output_root=args.output_root,
        obelisk_commit=args.obelisk_commit,
        binary_sha256=binary_sha256,
        reviewed_by=args.reviewed_by,
        review_note=args.review_note,
        standing_launch_authority_reference=args.standing_launch_authority_reference,
        now_utc=args.now_utc,
        diagnostic_candidates=args.diagnostic_candidates,
        presence_source_discrepancy=getattr(args, "presence_source_discrepancy", "none"),
        session_end_only_no_start=getattr(args, "session_end_only_no_start", False),
        active_player_no_accepted_events=args.active_player_no_accepted_events,
        concrete_deploy_or_gate_change=args.concrete_deploy_or_gate_change,
        json=True,
    )


def command_by_id(plan: dict[str, Any], step_id: str) -> dict[str, Any]:
    for command in plan["commands"]:
        if command["id"] == step_id:
            return command
    raise SystemExit(f"plan missing command id {step_id}")


def shell_command(argv: list[str], *, env: dict[str, str] | None = None) -> str:
    parts: list[str] = []
    if env:
        parts.extend(f"{key}={shlex.quote(value)}" for key, value in sorted(env.items()))
    parts.extend(shlex.quote(part) for part in argv)
    return " ".join(parts)


def argv_with_flag_before_json(argv: list[Any], flag: str) -> list[str]:
    normalized = [str(item) for item in argv]
    if flag in normalized:
        return normalized
    try:
        index = normalized.index("--json")
    except ValueError:
        return [*normalized, flag]
    return [*normalized[:index], flag, *normalized[index:]]


def apply_executor_request_pack_options(plan: dict[str, Any], args: argparse.Namespace) -> None:
    if not args.diagnostic_candidates:
        return
    command = command_by_id(plan, "prepare_request_pack")
    command["argv"] = argv_with_flag_before_json(command.get("argv") or [], "--diagnostic-candidates")
    command["shell"] = shell_command(command["argv"], env=command.get("env") or {})
    command["executor_request_pack_options"] = {
        "diagnostic_candidates": True,
        "non_authorization": DIAGNOSTIC_CANDIDATES_NON_AUTHORIZATION,
    }


def run_command(command: dict[str, Any], *, redirect: Path | None = None) -> dict[str, Any]:
    env = os.environ.copy()
    env.update(command.get("env") or {})
    stdout_target = redirect
    if stdout_target is not None:
        stdout_target.parent.mkdir(parents=True, exist_ok=True)
        with stdout_target.open("w", encoding="utf-8") as handle:
            result = subprocess.run(
                command["argv"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=handle,
                stderr=subprocess.PIPE,
                check=False,
            )
        stdout_text = None
    else:
        result = subprocess.run(
            command["argv"],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        stdout_text = result.stdout
    return {
        "id": command["id"],
        "title": command["title"],
        "returncode": result.returncode,
        "ok": result.returncode == 0,
        "stdout_path": str(stdout_target) if stdout_target is not None else None,
        "stdout": stdout_text,
        "stderr": result.stderr,
        "note": command.get("note"),
    }


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} did not contain a JSON object")
    return payload


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_post_window_key(value: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def post_window_key_tokens(value: object) -> set[str]:
    normalized = normalized_post_window_key(value)
    return {token for token in normalized.split("_") if token}


def is_forbidden_flow_alias(value: str) -> bool:
    normalized = normalized_post_window_key(value)
    return normalized in FLOW_ALIAS_TOKENS or FLOW_ALIAS_RE.search(value) is not None


def reject_flow_target_aliases(args: argparse.Namespace) -> None:
    blockers: list[str] = []
    for label, value in (("--instance", args.instance), ("--map", args.map_name)):
        if is_forbidden_flow_alias(value):
            blockers.append(f"{label}={value}")
    if blockers:
        raise SystemExit(
            "runtime-window executor requires exact instance/map names; "
            "no-users, no-testers, passive-wait, notice, status, readiness, and public-readiness aliases are rejected: "
            + ", ".join(blockers)
        )


NORMALIZED_POST_WINDOW_FORBIDDEN_TRUE_ALIASES = {
    normalized_post_window_key(key) for key in POST_WINDOW_FORBIDDEN_TRUE_ALIASES
}
NORMALIZED_POST_WINDOW_FORBIDDEN_PROGRESS_ALIASES = {
    normalized_post_window_key(key) for key in POST_WINDOW_FORBIDDEN_PROGRESS_ALIASES
}


def post_window_positive_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        tokens = {
            token
            for token in re.split(r"[^A-Za-z0-9]+", value.casefold())
            if token
        }
        if tokens & POST_WINDOW_NEGATIVE_STATUS_TOKENS and not (
            tokens & POST_WINDOW_POSITIVE_STATUS_TOKENS
        ):
            return False
        if {"not", "authorized"}.issubset(tokens):
            return False
        if {"request", "only"}.issubset(tokens) and "authorized" in tokens:
            return False
        return bool(tokens & POST_WINDOW_POSITIVE_STATUS_TOKENS)
    if isinstance(value, dict):
        return any(post_window_positive_claim_value(child) for child in value.values())
    if isinstance(value, list):
        return any(post_window_positive_claim_value(child) for child in value)
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


def post_window_positive_claim_alias_key(value: object) -> bool:
    normalized = normalized_post_window_key(value)
    tokens = post_window_key_tokens(value)
    if not tokens:
        return False
    if normalized in NORMALIZED_POST_WINDOW_FORBIDDEN_TRUE_ALIASES:
        return True
    if "authoriz" in normalized or "authoris" in normalized:
        return True
    if no_user_passive_alias_tokens(tokens) and tokens & (
        POST_WINDOW_CLAIM_COMPLETION_TOKENS
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
    if "progress" in tokens and tokens & POST_WINDOW_CLAIM_DOMAIN_TOKENS:
        return True
    if "counts" in tokens and tokens & POST_WINDOW_CLAIM_DOMAIN_TOKENS:
        return True
    if tokens & {"delivered", "sent"} and tokens & {"discord", "notice", "player"}:
        return True
    if "evidence" in tokens and (
        tokens & POST_WINDOW_CLAIM_DOMAIN_TOKENS
        or tokens & POST_WINDOW_CLAIM_COMPLETION_TOKENS
    ):
        return True
    if tokens & POST_WINDOW_CLAIM_DOMAIN_TOKENS and tokens & POST_WINDOW_CLAIM_COMPLETION_TOKENS:
        return True
    if "status" in tokens and tokens & POST_WINDOW_CLAIM_DOMAIN_TOKENS:
        return True
    if "readiness" in tokens and tokens & POST_WINDOW_CLAIM_DOMAIN_TOKENS:
        return True
    return False


def collect_post_window_shortcut_aliases(value: Any, trail: str = "$") -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}" if trail != "$" else f"$.{key}"
            normalized = normalized_post_window_key(key)
            if normalized == "non_authorization":
                continue
            if (
                normalized in NORMALIZED_POST_WINDOW_FORBIDDEN_TRUE_ALIASES
                and post_window_positive_claim_value(child)
            ):
                matches.append(child_trail)
            elif (
                post_window_positive_claim_alias_key(key)
                and post_window_positive_claim_value(child)
            ):
                matches.append(child_trail)
            if normalized in NORMALIZED_POST_WINDOW_FORBIDDEN_PROGRESS_ALIASES:
                if not isinstance(child, (int, float)) or isinstance(child, bool) or child != 0:
                    matches.append(child_trail)
            matches.extend(collect_post_window_shortcut_aliases(child, child_trail))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            matches.extend(collect_post_window_shortcut_aliases(child, f"{trail}[{index}]"))
    return matches


def reject_runtime_evidence_shortcuts(payload: dict[str, Any], label: str) -> None:
    matches = collect_post_window_shortcut_aliases(payload)
    if matches:
        preview = ", ".join(matches[:8])
        if len(matches) > 8:
            preview = f"{preview}, ..."
        raise SystemExit(
            f"{label} contains runtime-evidence/authorization shortcut aliases: {preview}"
        )


def as_string_list(value: Any, *, allowed: tuple[str, ...] | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    allowed_values = set(allowed or ())
    seen: set[str] = set()
    output: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        if allowed is not None and item not in allowed_values:
            continue
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    if allowed is not None:
        return [item for item in allowed if item in seen]
    return output


def first_string_list(*values: Any, allowed: tuple[str, ...] | None = None) -> list[str]:
    for value in values:
        items = as_string_list(value, allowed=allowed)
        if items:
            return items
        if isinstance(value, list):
            return []
    return []


def source_text_values(value: Any) -> list[str]:
    if isinstance(value, str) and value:
        return [value]
    if isinstance(value, Path):
        return [str(value)]
    if isinstance(value, list):
        output: list[str] = []
        for item in value:
            output.extend(source_text_values(item))
        return output
    if isinstance(value, dict):
        output = []
        for key in (
            "path",
            "source_path",
            "evidence_dir",
            "source_evidence_dir",
            "invalid_source_evidence_dir",
            "source_run_id",
            "source_root_role",
            "suggested_valid_closure_run_id",
            "suggested_valid_closure_evidence_dir",
        ):
            output.extend(source_text_values(value.get(key)))
        return output
    return []


def source_run_ids(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        for match in RUN_ID_TEXT_RE.findall(value):
            if match in seen:
                continue
            seen.add(match)
            output.append(match)
    return output


def post_window_source_boundary(
    *,
    source_kind: str,
    source_path: Path,
    payload: dict[str, Any],
    plan: dict[str, Any],
    evidence_source_blockers: list[Any] | None = None,
    invalid_sidecars: list[str] | None = None,
) -> dict[str, Any]:
    values = [str(source_path)]
    for key in (
        "evidence_dir",
        "source_evidence_dir",
        "invalid_source_evidence_dir",
        "source_run_id",
    ):
        values.extend(source_text_values(payload.get(key)))
    source_state = payload.get("evidence_source_state")
    if isinstance(source_state, dict):
        values.extend(source_text_values(source_state))
        guidance = source_state.get("closure_compatible_copy_guidance")
        if isinstance(guidance, dict):
            values.extend(source_text_values(guidance))
    for blocker in evidence_source_blockers or []:
        values.extend(source_text_values(blocker))
    source_text = " ".join(values)
    run_ids = source_run_ids(values)
    plan_run_id = str(plan.get("run_id") or "")
    run_id_matches_plan = bool(plan_run_id and plan_run_id in run_ids)
    run_id_mismatches_plan = bool(run_ids and not run_id_matches_plan)
    source_is_passive_summary = source_kind.startswith("passive")
    guidance_or_payload_marks_passive = any(
        isinstance(item, dict)
        and (
            item.get("source_looks_like_passive_monitor_root") is True
            or item.get("passive_monitor_root_accepted_as_closure_evidence_dir") is False
        )
        for item in [payload, source_state if isinstance(source_state, dict) else {}]
    )
    source_looks_like_passive_monitor_root = bool(
        source_is_passive_summary
        or guidance_or_payload_marks_passive
        or PASSIVE_MONITOR_SOURCE_RE.search(source_text)
    )
    source_is_invalid = bool(evidence_source_blockers or invalid_sidecars)
    source_is_stale = bool(run_id_mismatches_plan or STALE_SOURCE_RE.search(source_text))
    source_only = bool(
        source_is_passive_summary
        or source_looks_like_passive_monitor_root
        or source_is_invalid
        or source_is_stale
    )
    if source_is_invalid and source_looks_like_passive_monitor_root:
        classification = "invalid_passive_monitor_root_source_only_non_evidence"
    elif source_is_invalid:
        classification = "invalid_post_window_source_only_non_evidence"
    elif source_is_stale and source_looks_like_passive_monitor_root:
        classification = "stale_passive_monitor_source_only_non_evidence"
    elif source_is_stale:
        classification = "stale_post_window_source_only_non_evidence"
    elif source_looks_like_passive_monitor_root:
        classification = "passive_monitor_source_only_non_evidence"
    else:
        classification = "post_window_source_diagnostic_non_evidence"
    return {
        "schema": POST_WINDOW_SOURCE_BOUNDARY_SCHEMA,
        "source_kind": source_kind,
        "source_path": str(source_path),
        "source_schema": payload.get("schema"),
        "source_status": payload.get("status"),
        "classification": classification,
        "source_only_non_evidence": True,
        "source_is_passive_summary": source_is_passive_summary,
        "source_looks_like_passive_monitor_root": source_looks_like_passive_monitor_root,
        "source_is_invalid": source_is_invalid,
        "source_is_stale": source_is_stale,
        "source_run_ids": run_ids,
        "plan_run_id": plan_run_id,
        "source_run_id_matches_plan": run_id_matches_plan,
        "source_run_id_mismatches_plan": run_id_mismatches_plan,
        "stale_or_passive_monitor_source_only": source_only,
        "source_accepted_as_closure_evidence_dir": False,
        "passive_monitor_root_accepted_as_closure_evidence_dir": False,
        "source_becomes_evidence": False,
        "source_authorizes_machine_action": False,
        "source_authorizes_discord": False,
        "source_authorizes_server_operations": False,
        "source_authorizes_runtime_capture": False,
        "source_counts_as_approved_runtime_evidence": False,
        "source_counts_as_runtime_evidence": False,
        "source_counts_as_sdk_evidence": False,
        "checker_required_before_acceptance": True,
        "approved_evidence_bundle_checker_accepted": False,
        "non_authorization": POST_WINDOW_STATE_NON_AUTHORIZATION,
    }


def standing_launch_authority_boundary(args: argparse.Namespace, plan: dict[str, Any]) -> dict[str, Any]:
    authority = plan.get("standing_launch_authority")
    if not isinstance(authority, dict):
        authority = {}
    standing_recorded = (
        authority.get("recorded") is True
        and authority.get("bound_by_prepare_command") is True
    )
    return {
        "schema": "obelisk.player-principal-lifecycle-runtime-window-authority-boundary.v1",
        "standing_launch_authority_recorded_in_plan": authority.get("recorded") is True,
        "standing_launch_authority_reference": authority.get(
            "reference",
            args.standing_launch_authority_reference,
        ),
        "standing_launch_authority_bound_by_prepare_command": (
            authority.get("bound_by_prepare_command") is True
        ),
        "standing_launch_authority_preserved": True,
        "standing_launch_authority_satisfies_external_runtime_scope": False,
        "standing_launch_authority_satisfies_preparation_scope": standing_recorded,
        "standing_authority_authorizes_discord_send": False,
        "standing_authority_authorizes_runtime_evidence": False,
        "standing_authority_authorizes_marker_env_changes": False,
        "standing_authority_authorizes_server_restart": False,
        "fresh_current_turn_operator_authorization_required_for_external_runtime_scope": True,
        "separate_operator_authorization_required_for_external_runtime_scope": True,
        "external_runtime_steps_executed_by_executor": False,
        "current_turn_approval_claimed_by_executor": False,
        "post_window_state_source_authorizes_current_turn": False,
        "post_window_state_source_authorizes_discord": False,
        "post_window_state_source_authorizes_server_operations": False,
        "post_window_state_source_authorizes_runtime_capture": False,
        "post_window_state_source_counts_as_runtime_evidence": False,
        "two_server_cap_policy": two_server_cap_policy(),
        "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
        "non_authorization": POST_WINDOW_STATE_NON_AUTHORIZATION,
    }


def closure_missing_section(payload: dict[str, Any]) -> dict[str, Any]:
    section = payload.get("missing_artifacts_and_roles")
    return section if isinstance(section, dict) else {}


def next_post_window_blocker(
    *,
    source_kind: str,
    exact_missing_required_artifacts: list[str],
    exact_missing_lifecycle_event_roles: list[str],
    invalid_sidecars: list[str],
    evidence_source_blockers: list[Any],
    artifact_gap_scope: str,
    role_gap_scope: str,
    closure_inputs_complete: bool,
    passive_target_found: bool,
) -> str:
    if evidence_source_blockers:
        return "post_window_evidence_source_invalid"
    if invalid_sidecars:
        return "post_window_sidecar_validation_blockers"
    if exact_missing_required_artifacts:
        return "post_window_required_artifacts_missing"
    if exact_missing_lifecycle_event_roles:
        return "post_window_lifecycle_event_roles_missing"
    if source_kind.startswith("passive") and not passive_target_found:
        return "passive_summary_target_not_observed_non_evidence"
    if artifact_gap_scope != "closure_report_exact":
        return "closure_report_required_for_exact_artifact_gaps"
    if role_gap_scope != "closure_report_exact" and source_kind.startswith("passive"):
        return "closure_report_required_for_exact_lifecycle_role_gaps"
    if closure_inputs_complete:
        return "approved_runtime_bundle_checker_acceptance_required"
    return "post_window_state_non_ready_without_runtime_evidence"


def post_window_manual_step(
    *,
    source_kind: str,
    next_blocker: str,
    exact_missing_required_artifacts: list[str],
    exact_missing_lifecycle_event_roles: list[str],
) -> dict[str, Any]:
    if next_blocker == "no_users_passive_wait_for_player_backed_evidence":
        action = (
            "Continue a wait-only passive player-presence window and prepare the next "
            "player-backed diagnostic-candidate request with restart expectation none; "
            "do not restart again only because no users joined."
        )
    elif next_blocker == "active_player_no_accepted_events_likely_drift_defer_until_fix":
        action = (
            "A player is present and the lifecycle observer is enabled, but no accepted "
            "lifecycle events were seen; defer until the drift is fixed or a concrete "
            "deploy/gate change is named. Do not restart for this state alone, and ask "
            "for reconnect/logout only after exact observer-gate preconditions are met."
        )
    elif next_blocker == "post_window_required_artifacts_missing":
        action = (
            "Produce or copy the exact missing sidecar/artifact set outside this executor, "
            "then run the one-shot approved runtime evidence bundle builder with "
            "--evidence-dir against the copied sibling-set directory."
        )
    elif next_blocker == "post_window_lifecycle_event_roles_missing":
        action = (
            "Use the lead-owned recorded-authority/current-scope runtime path for the exact missing lifecycle roles; "
            "this executor does not start, restart, monitor live logs, or capture runtime evidence."
        )
    elif source_kind.startswith("passive"):
        action = (
            "Generate a closure report or evidence-dir preflight from copied live-validation evidence "
            "to classify exact artifact gaps, then keep the copied-log route bound to "
            "the one-shot approved runtime evidence bundle builder; passive summaries "
            "remain non-evidence."
        )
    else:
        action = (
            "Run the copied-log route outside this executor with the one-shot approved "
            "runtime evidence bundle builder using --evidence-dir; only accepted checker "
            "output can change approved runtime evidence state."
        )
    return {
        "schema": "obelisk.player-principal-lifecycle-post-window-manual-step.v1",
        "next_blocker": next_blocker,
        "action": action,
        "missing_required_artifacts": exact_missing_required_artifacts,
        "missing_lifecycle_event_roles": exact_missing_lifecycle_event_roles,
        "lifecycle_missing_role_objectives": lifecycle_role_objectives(
            exact_missing_lifecycle_event_roles
        ),
        "status": "manual_external_not_executed_by_executor",
        "server_operations_authorized": False,
        "runtime_capture_authorized": False,
        "discord_authorized": False,
        "counts_as_approved_runtime_evidence": False,
        "approved_evidence_bundle_checker_accepted": False,
        "approved_evidence_bundle_acceptance_required": True,
        "approved_evidence_bundle_acceptance_requirement": approved_evidence_bundle_acceptance_requirement(),
        "copied_log_route_required": copied_log_route_contract(),
        "ordered_copied_log_route_step_ids": list(COPIED_LOG_ROUTE_STEP_IDS),
        "non_authorization": POST_WINDOW_STATE_NON_AUTHORIZATION,
    }


def post_window_state_from_closure(
    *,
    source_path: Path,
    payload: dict[str, Any],
    args: argparse.Namespace,
    plan: dict[str, Any],
) -> dict[str, Any]:
    missing = closure_missing_section(payload)
    exact_missing_required_artifacts = first_string_list(
        missing.get("missing_required_artifacts"),
        payload.get("missing_required_artifacts"),
    )
    exact_missing_lifecycle_event_roles = first_string_list(
        missing.get("missing_lifecycle_event_roles"),
        payload.get("missing_lifecycle_event_roles"),
        allowed=REQUIRED_LIFECYCLE_EVENT_ROLES,
    )
    exact_missing_sidecars = first_string_list(
        missing.get("exact_missing_sidecars"),
        payload.get("exact_missing_sidecars"),
    )
    invalid_sidecars = first_string_list(
        missing.get("invalid_sidecars"),
        payload.get("invalid_sidecars"),
    )
    required_sidecars = first_string_list(
        missing.get("required_sidecars"),
        payload.get("required_sidecars"),
    )
    required_roles = first_string_list(
        missing.get("required_lifecycle_event_role_triplet"),
        payload.get("required_lifecycle_event_role_triplet"),
        allowed=REQUIRED_LIFECYCLE_EVENT_ROLES,
    )
    if not required_roles:
        required_roles = list(REQUIRED_LIFECYCLE_EVENT_ROLES)
    evidence_source_blockers = payload.get("evidence_source_blockers")
    if not isinstance(evidence_source_blockers, list):
        evidence_source_blockers = []
    closure_inputs_complete = payload.get("evidence_closure_inputs_complete") is True
    next_blocker = next_post_window_blocker(
        source_kind="closure_request_report",
        exact_missing_required_artifacts=exact_missing_required_artifacts,
        exact_missing_lifecycle_event_roles=exact_missing_lifecycle_event_roles,
        invalid_sidecars=invalid_sidecars,
        evidence_source_blockers=evidence_source_blockers,
        artifact_gap_scope="closure_report_exact",
        role_gap_scope="closure_report_exact",
        closure_inputs_complete=closure_inputs_complete,
        passive_target_found=True,
    )
    target = payload.get("target") if isinstance(payload.get("target"), dict) else plan["target"]
    source_boundary = post_window_source_boundary(
        source_kind="closure_request_report",
        source_path=source_path,
        payload=payload,
        plan=plan,
        evidence_source_blockers=evidence_source_blockers,
        invalid_sidecars=invalid_sidecars,
    )
    return {
        "schema": POST_WINDOW_STATE_SCHEMA,
        "checked": True,
        "source_kind": "closure_request_report",
        "source_path": str(source_path),
        "source_schema": payload.get("schema"),
        "source_status": payload.get("status"),
        "post_window_source_boundary": source_boundary,
        "source_classification": source_boundary["classification"],
        "source_only_non_evidence": source_boundary["source_only_non_evidence"],
        "stale_or_passive_monitor_source_only": source_boundary[
            "stale_or_passive_monitor_source_only"
        ],
        "passive_monitor_root_accepted_as_closure_evidence_dir": False,
        "closure_case": payload.get("closure_case") or payload.get("case_id"),
        "target": target,
        "evidence_dir": payload.get("evidence_dir"),
        "closure_inputs_complete": closure_inputs_complete,
        "artifact_gap_scope": "closure_report_exact",
        "role_gap_scope": "closure_report_exact",
        "exact_missing_required_artifacts": exact_missing_required_artifacts,
        "exact_missing_sidecars": exact_missing_sidecars,
        "exact_missing_lifecycle_event_roles": exact_missing_lifecycle_event_roles,
        "lifecycle_missing_role_objectives": lifecycle_role_objectives(
            exact_missing_lifecycle_event_roles
        ),
        "required_sidecars": required_sidecars,
        "required_lifecycle_event_role_triplet": required_roles,
        "invalid_sidecars": invalid_sidecars,
        "evidence_source_blockers": evidence_source_blockers,
        "approved_bundle_manifest_relative_path": payload.get(
            "approved_bundle_manifest_relative_path",
            APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
        ),
        "approved_bundle_path": payload.get("approved_bundle_path"),
        "approved_evidence_bundle_checker_accepted": False,
        "approved_evidence_bundle_acceptance_required": True,
        "approved_evidence_bundle_acceptance_requirement": approved_evidence_bundle_acceptance_requirement(),
        "next_required_artifact": (
            exact_missing_required_artifacts[0]
            if exact_missing_required_artifacts
            else None
        ),
        "next_missing_lifecycle_event_role": (
            exact_missing_lifecycle_event_roles[0]
            if exact_missing_lifecycle_event_roles
            else None
        ),
        "next_blocker": next_blocker,
        "manual_step": post_window_manual_step(
            source_kind="closure_request_report",
            next_blocker=next_blocker,
            exact_missing_required_artifacts=exact_missing_required_artifacts,
            exact_missing_lifecycle_event_roles=exact_missing_lifecycle_event_roles,
        ),
        "authority_boundary": standing_launch_authority_boundary(args, plan),
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "source_material_counts_as_approved_runtime_evidence": False,
        "passive_snapshots_as_evidence": False,
        "closure_report_counts_as_approved_runtime_evidence": False,
        "runtime_capture_authorized": False,
        "server_operations_authorized": False,
        "discord_sent": False,
        "current_turn_approval_claimed_by_executor": False,
        "non_authorization": POST_WINDOW_STATE_NON_AUTHORIZATION,
    }


def passive_activity_summary(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    for key in (
        "passive_server_activity_summary",
        "passive_monitor_activity_summary",
        "candidate_passive_server_activity_summary",
        "candidate_passive_monitor_activity_summary",
    ):
        value = payload.get(key)
        if isinstance(value, dict):
            return key, value
    latest = payload.get("latest")
    if isinstance(latest, dict):
        for key in ("passive_server_activity_summary", "passive_monitor_activity_summary"):
            value = latest.get(key)
            if isinstance(value, dict):
                return f"latest.{key}", value
    return "not_found", {}


def passive_triplet_candidates_for_plan(
    summary: dict[str, Any],
    plan: dict[str, Any],
) -> tuple[bool, list[dict[str, Any]], list[str]]:
    candidates = summary.get("player_principal_triplet_candidates_by_target")
    if not isinstance(candidates, dict):
        return False, [], []
    target = plan["target"]
    matched: list[dict[str, Any]] = []
    for key, value in candidates.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        if (
            value.get("instance") == target["instance"]
            and value.get("map") == target["map"]
        ):
            matched.append({"target_key": key, **value})
    roles_seen: set[str] = set()
    for item in matched:
        roles_seen.update(
            as_string_list(
                item.get("roles_seen"),
                allowed=REQUIRED_LIFECYCLE_EVENT_ROLES,
            )
        )
    missing_roles = [
        role for role in REQUIRED_LIFECYCLE_EVENT_ROLES if role not in roles_seen
    ]
    return bool(matched), matched, missing_roles


def next_window_prepare_argv(args: argparse.Namespace, plan: dict[str, Any]) -> list[str]:
    target = plan["target"]
    argv = [
        "python3",
        "scripts/prepare_player_principal_lifecycle_runtime_window_execution.py",
        "--instance",
        str(target["instance"]),
        "--map",
        str(target["map"]),
        "--start-delay-minutes",
        str(args.start_delay_minutes),
        "--duration-minutes",
        str(args.duration_minutes),
        "--restart-expectation",
        "none",
        "--user-policy",
        args.user_policy,
        "--notice-path",
        args.notice_path,
        "--rollback-owner",
        args.rollback_owner,
        "--output-root",
        str(args.output_root),
        "--reviewed-by",
        args.reviewed_by,
        "--review-note",
        args.review_note,
        "--standing-launch-authority-reference",
        args.standing_launch_authority_reference,
    ]
    if args.obelisk_commit:
        argv.extend(["--obelisk-commit", args.obelisk_commit])
    if args.binary_sha256:
        argv.extend(["--binary-sha256", args.binary_sha256])
    argv.extend(["--diagnostic-candidates", "--json"])
    return argv


def no_users_passive_wait_recommendation(
    *,
    args: argparse.Namespace,
    plan: dict[str, Any],
    presence: dict[str, Any],
) -> dict[str, Any]:
    diagnostic_candidates = diagnostic_candidate_next_window_policy(
        requested=args.diagnostic_candidates,
        plan=plan,
        request=None,
        recommend_enable=presence.get("no_users_detected") is True,
    )
    return {
        "schema": NO_USERS_PASSIVE_WAIT_SCHEMA,
        "status": (
            "no_users_passive_wait_recommended"
            if presence.get("no_users_detected") is True
            else "passive_wait_context_non_evidence"
        ),
        "target": plan["target"],
        "passive_player_presence": presence,
        "no_users_detected": presence.get("no_users_detected") is True,
        "players_present": presence.get("players_present") is True,
        "passive_wait_preferred": True,
        "process_control": "passive_wait_without_restart",
        "repeated_restart_for_no_users_forbidden": True,
        "restart_recommended": False,
        "start_or_restart_recommended": False,
        "linuxgsm_monitor_forbidden": True,
        "monitor_command_not_executed": passive_monitor_command(plan),
        "closure_compatible_evidence_root": closure_compatible_evidence_root(plan),
        "linger_after_detect_recommended": True,
        "diagnostic_candidates": diagnostic_candidates,
        "player_presence_detection_authorizes_followup": False,
        "passive_monitor_ticks_authorize_runtime_capture": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "readiness_claim_allowed": False,
        "progress_claim_allowed": False,
        "authorization_claim_allowed": False,
        "notice_sent_claim_allowed": False,
        "no_users_no_testers_passive_wait_counts_as_approved_runtime_evidence": False,
        "no_users_no_testers_passive_wait_counts_as_readiness": False,
        "no_users_no_testers_passive_wait_counts_as_progress": False,
        "no_users_no_testers_passive_wait_counts_as_authorization": False,
        "no_users_no_testers_passive_wait_counts_as_notice_sent": False,
        "non_authorization": NO_USERS_PASSIVE_WAIT_NON_AUTHORIZATION,
    }


def next_player_backed_window_preparation(
    *,
    args: argparse.Namespace,
    plan: dict[str, Any],
    presence: dict[str, Any],
) -> dict[str, Any]:
    recommended = presence.get("no_users_detected") is True
    diagnostic_candidates = diagnostic_candidate_next_window_policy(
        requested=recommended,
        plan=plan,
        request=None,
        recommend_enable=recommended,
    )
    argv = next_window_prepare_argv(args, plan) if recommended else []
    return {
        "schema": NEXT_PLAYER_BACKED_WINDOW_SCHEMA,
        "status": (
            "prepare_next_player_backed_diagnostic_window_without_restart"
            if recommended
            else "not_recommended_without_no_users_passive_signal"
        ),
        "target": plan["target"],
        "restart_expectation": "none",
        "user_policy": args.user_policy,
        "notice_path": args.notice_path,
        "diagnostic_candidates": diagnostic_candidates,
        "diagnostic_candidates_recommended": recommended,
        "should_enable_diagnostic_candidates_in_next_request_pack": recommended,
        "no_users_detected": presence.get("no_users_detected") is True,
        "passive_wait_first": recommended,
        "start_or_restart_recommended": False,
        "repeated_restart_for_no_users_forbidden": True,
        "command_text_not_executed": shell_command(argv) if argv else None,
        "argv_not_executed": argv,
        "closure_compatible_evidence_root": closure_compatible_evidence_root(plan),
        "authorized_by_this_report": False,
        "server_operations_authorized": False,
        "runtime_capture_authorized": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "readiness_claim_allowed": False,
        "progress_claim_allowed": False,
        "authorization_claim_allowed": False,
        "notice_sent_claim_allowed": False,
        "no_users_no_testers_passive_wait_counts_as_approved_runtime_evidence": False,
        "no_users_no_testers_passive_wait_counts_as_readiness": False,
        "no_users_no_testers_passive_wait_counts_as_progress": False,
        "no_users_no_testers_passive_wait_counts_as_authorization": False,
        "no_users_no_testers_passive_wait_counts_as_notice_sent": False,
        "non_authorization": NO_USERS_PASSIVE_WAIT_NON_AUTHORIZATION,
    }


def post_window_state_from_passive(
    *,
    source_path: Path,
    payload: dict[str, Any],
    args: argparse.Namespace,
    plan: dict[str, Any],
) -> dict[str, Any]:
    summary_key, summary = passive_activity_summary(payload)
    passive_target_found, target_triplets, exact_missing_lifecycle_event_roles = (
        passive_triplet_candidates_for_plan(summary, plan)
    )
    passive_presence = passive_player_presence(summary, plan)
    active_no_accepted = active_player_no_accepted_events_policy(
        plan=plan,
        summary=summary,
        presence=passive_presence,
        target_triplets=target_triplets,
    )
    if active_no_accepted["state_detected"]:
        passive_target_found = True
        exact_missing_lifecycle_event_roles = list(REQUIRED_LIFECYCLE_EVENT_ROLES)
    elif passive_presence["target_presence_known"]:
        passive_target_found = True
    if passive_presence["no_users_detected"]:
        exact_missing_lifecycle_event_roles = []
    elif not passive_target_found:
        exact_missing_lifecycle_event_roles = []
    actionability = payload.get("passive_actionability")
    if not isinstance(actionability, dict):
        actionability = {}
    role_gap_scope = (
        "target_present_no_users_observed"
        if passive_presence["no_users_detected"]
        else "active_player_no_accepted_events_likely_drift"
        if active_no_accepted["state_detected"]
        else "passive_summary_exact_target"
        if passive_target_found
        else "target_not_present_in_passive_summary"
    )
    next_blocker = next_post_window_blocker(
        source_kind="passive_summary",
        exact_missing_required_artifacts=[],
        exact_missing_lifecycle_event_roles=exact_missing_lifecycle_event_roles,
        invalid_sidecars=[],
        evidence_source_blockers=[],
        artifact_gap_scope="not_inspected_by_passive_summary",
        role_gap_scope=role_gap_scope,
        closure_inputs_complete=False,
        passive_target_found=passive_target_found,
    )
    if passive_presence["no_users_detected"]:
        next_blocker = "no_users_passive_wait_for_player_backed_evidence"
    elif active_no_accepted["state_detected"]:
        next_blocker = str(active_no_accepted["next_blocker"])
    passive_wait = no_users_passive_wait_recommendation(
        args=args,
        plan=plan,
        presence=passive_presence,
    )
    next_window = next_player_backed_window_preparation(
        args=args,
        plan=plan,
        presence=passive_presence,
    )
    source_boundary = post_window_source_boundary(
        source_kind="passive_summary",
        source_path=source_path,
        payload=payload,
        plan=plan,
        evidence_source_blockers=[],
        invalid_sidecars=[],
    )
    return {
        "schema": POST_WINDOW_STATE_SCHEMA,
        "checked": True,
        "source_kind": "passive_summary",
        "source_path": str(source_path),
        "source_schema": payload.get("schema"),
        "source_status": payload.get("status"),
        "post_window_source_boundary": source_boundary,
        "source_classification": source_boundary["classification"],
        "source_only_non_evidence": source_boundary["source_only_non_evidence"],
        "stale_or_passive_monitor_source_only": source_boundary[
            "stale_or_passive_monitor_source_only"
        ],
        "passive_monitor_root_accepted_as_closure_evidence_dir": False,
        "target": plan["target"],
        "passive_summary_key": summary_key,
        "passive_target_found": passive_target_found,
        "target_triplet_candidates": target_triplets,
        "passive_player_presence": passive_presence,
        "active_player_no_accepted_events_policy": active_no_accepted,
        "likely_lifecycle_drift": active_no_accepted["likely_drift"],
        "no_users_passive_wait": passive_wait,
        "next_player_backed_window": next_window,
        "passive_actionability": {
            "priority": actionability.get("priority"),
            "reason_kind": actionability.get("reason_kind"),
            "next_reason": actionability.get("next_reason"),
            "process_control": actionability.get("process_control"),
            "evidence_classification": actionability.get("evidence_classification"),
        },
        "closure_compatible_evidence_root": closure_compatible_evidence_root(plan),
        "artifact_gap_scope": "not_inspected_by_passive_summary",
        "role_gap_scope": role_gap_scope,
        "exact_missing_required_artifacts": [],
        "exact_missing_sidecars": [],
        "exact_missing_lifecycle_event_roles": exact_missing_lifecycle_event_roles,
        "lifecycle_missing_role_objectives": lifecycle_role_objectives(
            exact_missing_lifecycle_event_roles
        ),
        "required_sidecars": [],
        "required_lifecycle_event_role_triplet": list(REQUIRED_LIFECYCLE_EVENT_ROLES),
        "invalid_sidecars": [],
        "evidence_source_blockers": [],
        "approved_bundle_manifest_relative_path": APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
        "approved_bundle_path": None,
        "approved_evidence_bundle_checker_accepted": False,
        "approved_evidence_bundle_acceptance_required": True,
        "approved_evidence_bundle_acceptance_requirement": approved_evidence_bundle_acceptance_requirement(),
        "next_required_artifact": "closure_report_or_bundle_preflight_required_for_exact_artifact_gaps",
        "next_missing_lifecycle_event_role": (
            exact_missing_lifecycle_event_roles[0]
            if exact_missing_lifecycle_event_roles
            else None
        ),
        "next_blocker": next_blocker,
        "manual_step": post_window_manual_step(
            source_kind="passive_summary",
            next_blocker=next_blocker,
            exact_missing_required_artifacts=[],
            exact_missing_lifecycle_event_roles=exact_missing_lifecycle_event_roles,
        ),
        "authority_boundary": standing_launch_authority_boundary(args, plan),
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "source_material_counts_as_approved_runtime_evidence": False,
        "passive_snapshots_as_evidence": False,
        "passive_summary_counts_as_approved_runtime_evidence": False,
        "passive_complete_triplets_count_as_approved_runtime_evidence": False,
        "runtime_capture_authorized": False,
        "server_operations_authorized": False,
        "discord_sent": False,
        "current_turn_approval_claimed_by_executor": False,
        "non_authorization": POST_WINDOW_STATE_NON_AUTHORIZATION,
    }


def unsupported_post_window_state_schema_reason(schema: Any) -> str:
    if not isinstance(schema, str) or not schema:
        return "missing_schema"
    lowered = schema.casefold()
    normalized = normalized_post_window_key(schema)
    if (
        schema in MULTI_SURFACE_BETA_CAPTURE_FAMILY_SCHEMAS
        or "multi_surface_beta_capture" in normalized
    ):
        return "multi_surface_beta_capture_pack_family_is_candidate_metadata_not_post_window_state"
    if "public_readiness" in normalized or "public_ready" in normalized:
        return "public_readiness_schema_is_not_post_window_state"
    if "notice" in lowered:
        return "notice_report_schema_is_not_post_window_state"
    if "passive" in lowered:
        return "passive_alias_schema_is_not_post_window_state"
    if "runtime-window-execution" in lowered or "executor" in lowered:
        return "executor_report_schema_is_not_post_window_state"
    if "status" in lowered or "readiness" in lowered or "completion" in lowered:
        return "status_or_readiness_schema_is_not_post_window_state"
    return "unsupported_post_window_state_schema"


def default_post_window_state(args: argparse.Namespace, plan: dict[str, Any]) -> dict[str, Any]:
    source_boundary = {
        "schema": POST_WINDOW_SOURCE_BOUNDARY_SCHEMA,
        "source_kind": None,
        "source_path": None,
        "classification": "post_window_source_not_supplied",
        "source_only_non_evidence": True,
        "stale_or_passive_monitor_source_only": False,
        "source_authorizes_machine_action": False,
        "source_counts_as_approved_runtime_evidence": False,
        "checker_required_before_acceptance": True,
        "approved_evidence_bundle_checker_accepted": False,
        "non_authorization": POST_WINDOW_STATE_NON_AUTHORIZATION,
    }
    return {
        "schema": POST_WINDOW_STATE_SCHEMA,
        "checked": False,
        "source_kind": None,
        "source_path": None,
        "source_schema": None,
        "post_window_source_boundary": source_boundary,
        "source_classification": source_boundary["classification"],
        "source_only_non_evidence": True,
        "stale_or_passive_monitor_source_only": False,
        "passive_monitor_root_accepted_as_closure_evidence_dir": False,
        "target": plan["target"],
        "artifact_gap_scope": "not_checked",
        "role_gap_scope": "not_checked",
        "exact_missing_required_artifacts": [],
        "exact_missing_sidecars": [],
        "exact_missing_lifecycle_event_roles": [],
        "required_lifecycle_event_role_triplet": list(REQUIRED_LIFECYCLE_EVENT_ROLES),
        "approved_evidence_bundle_checker_accepted": False,
        "approved_evidence_bundle_acceptance_required": True,
        "approved_evidence_bundle_acceptance_requirement": approved_evidence_bundle_acceptance_requirement(),
        "next_required_artifact": None,
        "next_missing_lifecycle_event_role": None,
        "next_blocker": "post_window_state_not_supplied",
        "authority_boundary": standing_launch_authority_boundary(args, plan),
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "source_material_counts_as_approved_runtime_evidence": False,
        "runtime_capture_authorized": False,
        "server_operations_authorized": False,
        "discord_sent": False,
        "current_turn_approval_claimed_by_executor": False,
        "non_authorization": POST_WINDOW_STATE_NON_AUTHORIZATION,
    }


def consume_post_window_state(args: argparse.Namespace, plan: dict[str, Any]) -> dict[str, Any]:
    if args.post_window_state_json is None:
        return default_post_window_state(args, plan)
    source_path = protected_input_file(args.post_window_state_json, "--post-window-state-json")
    try:
        payload = load_json(source_path)
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"--post-window-state-json is not readable JSON: {exc}") from exc
    schema = payload.get("schema")
    if schema == CLOSURE_REQUEST_SCHEMA:
        reject_runtime_evidence_shortcuts(payload, "--post-window-state-json closure report")
        return post_window_state_from_closure(
            source_path=source_path,
            payload=payload,
            args=args,
            plan=plan,
        )
    if schema in PASSIVE_SUMMARY_SCHEMAS:
        reject_runtime_evidence_shortcuts(payload, "--post-window-state-json passive summary")
        return post_window_state_from_passive(
            source_path=source_path,
            payload=payload,
            args=args,
            plan=plan,
        )
    reason = unsupported_post_window_state_schema_reason(schema)
    raise SystemExit(
        f"--post-window-state-json rejected {schema!r}: {reason}; supply a closure "
        "report or passive summary, and use the approved bundle checker for runtime evidence"
    )


def existing_request_pack_matches_plan(
    plan: dict[str, Any],
    *,
    diagnostic_candidates_requested: bool,
) -> tuple[bool, list[str]]:
    evidence_dir = Path(plan["evidence_dir"])
    missing = [
        name
        for name in REQUEST_PACK_FILENAMES
        if not (evidence_dir / name).is_file()
    ]
    if missing:
        return False, [f"missing:{name}" for name in missing]
    try:
        request = load_json(evidence_dir / "window-request.json")
    except (OSError, json.JSONDecodeError, SystemExit) as exc:
        return False, [f"window_request_unreadable:{exc}"]

    expected_window = {
        "start_utc": plan["approved_window"]["start_utc"],
        "end_utc": plan["approved_window"]["end_utc"],
    }
    mismatches: list[str] = []
    if request.get("run_id") != plan.get("run_id"):
        mismatches.append("run_id")
    if request.get("target") != plan.get("target"):
        mismatches.append("target")
    if request.get("approved_window") != expected_window:
        mismatches.append("approved_window")
    if request.get("notice_path") != "discord-beta-testers":
        mismatches.append("notice_path")
    if request.get("approval_required") != (
        "operator runtime authority must be bound by completed receipt; standing launch authority source allowed"
    ):
        mismatches.append("approval_required")
    if request.get("status") != "candidate_only_request_pack":
        mismatches.append("status")
    if request.get("diagnostic_candidates_enabled") is not diagnostic_candidates_requested:
        mismatches.append("diagnostic_candidates_enabled")
    return not mismatches, mismatches


def confirmed_notice_candidates(
    *,
    report_dir: Path,
    supplied_notice_report: Path | None,
) -> list[Path]:
    candidates: list[Path] = []
    if supplied_notice_report is not None:
        candidates.append(supplied_notice_report)
        if supplied_notice_report.suffix:
            candidates.append(supplied_notice_report.with_suffix(".sidecar.json"))
    candidates.append(report_dir / "beta-notice.confirmed.json")
    candidates.append(report_dir / "beta-notice.confirmed.sidecar.json")
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc)


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def retry_report_dir(
    plan: dict[str, Any],
    *,
    output_paths: dict[str, Any] | None = None,
    report_dir: Path | None = None,
) -> Path:
    if report_dir is not None:
        return report_dir
    if output_paths:
        sidecar_path = output_paths.get("dry_run_notice_sidecar")
        if isinstance(sidecar_path, str) and sidecar_path:
            return Path(sidecar_path).parent
    plan_report_dir = plan.get("report_dir")
    if isinstance(plan_report_dir, str) and plan_report_dir:
        return Path(plan_report_dir)
    return Path("/tmp") / f"obelisk-player-principal-{plan.get('run_id', 'unknown')}"


def runtime_fresh_retry_after_closed_non_evidence_window(
    plan: dict[str, Any],
    *,
    output_paths: dict[str, Any] | None = None,
    report_dir: Path | None = None,
) -> dict[str, Any]:
    target = plan.get("target") if isinstance(plan.get("target"), dict) else {}
    approved_window = (
        plan.get("approved_window") if isinstance(plan.get("approved_window"), dict) else {}
    )
    planned_at = parse_utc(nested_dict(plan, "current_window_workflow").get("planned_at_utc"))
    now = planned_at or datetime.now(timezone.utc).replace(microsecond=0)
    return fresh_retry_after_closed_non_evidence_window(
        now=now,
        run_id=str(plan.get("run_id") or ""),
        target=dict(target),
        approved_window=dict(approved_window),
        evidence_dir=Path(str(plan.get("evidence_dir") or "")),
        report_dir=retry_report_dir(plan, output_paths=output_paths, report_dir=report_dir),
    )


def runtime_window_stale_prevention_from_plan(plan: dict[str, Any]) -> dict[str, Any]:
    existing = plan.get("runtime_window_stale_prevention")
    if isinstance(existing, dict) and existing.get("schema") == RUNTIME_WINDOW_STALE_PREVENTION_SCHEMA:
        return existing
    workflow = plan.get("current_window_workflow")
    if isinstance(workflow, dict):
        existing = workflow.get("runtime_window_stale_prevention")
        if isinstance(existing, dict) and existing.get("schema") == RUNTIME_WINDOW_STALE_PREVENTION_SCHEMA:
            return existing
    window = plan.get("approved_window")
    if not isinstance(window, dict):
        return {
            "schema": RUNTIME_WINDOW_STALE_PREVENTION_SCHEMA,
            "classification": "approved_window_missing",
            "minimum_required_lead_seconds": MIN_RUNTIME_WINDOW_LEAD_SECONDS,
            "enough_future_lead_time": False,
            "window_start_in_future": False,
            "window_end_in_future": False,
            "stale_request_window": True,
            "request_window_stale_or_too_late": True,
            "blockers": ["runtime_window_approved_window_missing"],
            "activation_or_restart_from_stale_request_allowed": False,
            "monitor_or_restart_activation_after_window_start_allowed": False,
            "counts_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "non_authorization": NON_AUTHORIZATION,
        }
    start = parse_utc(window.get("start_utc"))
    end = parse_utc(window.get("end_utc"))
    if start is None or end is None:
        return {
            "schema": RUNTIME_WINDOW_STALE_PREVENTION_SCHEMA,
            "classification": "approved_window_time_invalid",
            "start_utc": window.get("start_utc"),
            "end_utc": window.get("end_utc"),
            "minimum_required_lead_seconds": MIN_RUNTIME_WINDOW_LEAD_SECONDS,
            "enough_future_lead_time": False,
            "window_start_in_future": False,
            "window_end_in_future": False,
            "stale_request_window": True,
            "request_window_stale_or_too_late": True,
            "blockers": ["runtime_window_approved_window_time_invalid"],
            "activation_or_restart_from_stale_request_allowed": False,
            "monitor_or_restart_activation_after_window_start_allowed": False,
            "counts_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "non_authorization": NON_AUTHORIZATION,
        }
    planned_at = parse_utc(nested_dict(plan, "current_window_workflow").get("planned_at_utc"))
    now = planned_at or datetime.now(timezone.utc).replace(microsecond=0)
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
        "schema": RUNTIME_WINDOW_STALE_PREVENTION_SCHEMA,
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
        "non_authorization": NON_AUTHORIZATION,
    }


def beta_notice_sequence_enforcement(plan: dict[str, Any]) -> dict[str, Any]:
    stale_prevention = runtime_window_stale_prevention_from_plan(plan)
    return {
        "schema": BETA_NOTICE_SEQUENCE_ENFORCEMENT_SCHEMA,
        "run_id": plan.get("run_id"),
        "target": plan.get("target"),
        "approved_window": plan.get("approved_window"),
        "runtime_window_stale_prevention": stale_prevention,
        "minimum_required_lead_seconds": MIN_RUNTIME_WINDOW_LEAD_SECONDS,
        "beta_notice_dry_run_required_before_confirmed_send": True,
        "beta_notice_dry_run_required_before_activation": True,
        "confirmed_beta_notice_required_before_activation": True,
        "confirmed_send_must_complete_before_window_start": True,
        "activation_preconditions_required_before_activation_or_restart": True,
        "activation_or_restart_from_stale_request_allowed": False,
        "monitor_or_restart_activation_after_window_start_allowed": False,
        "dry_run_or_confirmed_send_counts_as_approved_runtime_evidence": False,
        "confirmed_notice_counts_as_approved_runtime_evidence": False,
        "confirmed_notice_grants_readiness": False,
        "server_operations_authorized": False,
        "runtime_capture_authorized": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def request_window_current_for_confirmed_notice_binding(request: dict[str, Any]) -> bool:
    window = request.get("approved_window")
    if not isinstance(window, dict):
        return False
    start = parse_utc(window.get("start_utc"))
    end = parse_utc(window.get("end_utc"))
    if start is None or end is None or not start < end:
        return False
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return start > now and end > now


def confirmed_notice_sidecar_path(notice_report: dict[str, Any], notice_path: Path) -> Path:
    path_value = notice_report.get("notice_action_sidecar_json")
    if isinstance(path_value, str) and path_value:
        candidate = Path(path_value)
        return candidate if candidate.is_absolute() else notice_path.parent / candidate
    return notice_path.with_suffix(".sidecar.json") if notice_path.suffix else notice_path.parent / f"{notice_path.name}.sidecar.json"


def confirmed_notice_sidecar_report(sidecar: dict[str, Any]) -> dict[str, Any] | None:
    if sidecar.get("schema") != NOTICE_ACTION_ARTIFACT_SCHEMA:
        return None
    embedded_report = sidecar.get("notice_report")
    if not isinstance(embedded_report, dict):
        return None
    if sidecar.get("notice_report_sha256") != hashlib.sha256(
        canonical_json_bytes(embedded_report)
    ).hexdigest():
        return None
    for key in ("mode", "ready", "target", "run_id", "notice_path", "request_json"):
        if sidecar.get(key) != embedded_report.get(key):
            return None
    if sidecar.get("artifact_contains_full_sanitized_notice_report") is not True:
        return None
    if sidecar.get("sidecar_required_for_confirmed_send_consumption") is not True:
        return None
    if sidecar.get("stdout_only_confirmation_accepted") is not False:
        return None
    if sidecar.get("discord_send_performed_by_artifact_write") is not False:
        return None
    if sidecar.get("secret_or_webhook_output_allowed") is not False:
        return None
    for key, expected in SIDECAR_NON_EVIDENCE_FLAGS.items():
        if sidecar.get(key) is not expected:
            return None
    return embedded_report


def load_confirmed_notice_sidecar(
    notice_report: dict[str, Any],
    notice_path: Path,
) -> tuple[dict[str, Any], Path] | None:
    sidecar_path = confirmed_notice_sidecar_path(notice_report, notice_path)
    if not sidecar_path.exists():
        return None
    try:
        resolved_sidecar = protected_input_file(sidecar_path, "--confirmed-notice-report-json sidecar")
        payload = load_json(resolved_sidecar)
    except (OSError, json.JSONDecodeError, SystemExit):
        return None
    embedded = confirmed_notice_sidecar_report(payload)
    if embedded != notice_report:
        return None
    return payload, resolved_sidecar


def confirmed_notice_binds_request_pack(notice_path: Path, request_path: Path) -> dict[str, Any] | None:
    if not notice_path.exists():
        return None
    resolved_notice = protected_input_file(notice_path, "--confirmed-notice-report-json")
    try:
        payload = load_json(resolved_notice)
    except (OSError, json.JSONDecodeError, SystemExit):
        return None
    sidecar_path: str | None = None
    if payload.get("schema") == NOTICE_ACTION_ARTIFACT_SCHEMA:
        sidecar_path = str(resolved_notice)
        embedded_report = confirmed_notice_sidecar_report(payload)
        if embedded_report is None:
            return None
        payload = embedded_report
    else:
        sidecar_binding = load_confirmed_notice_sidecar(payload, resolved_notice)
        if sidecar_binding is None:
            return None
        _, resolved_sidecar = sidecar_binding
        sidecar_path = str(resolved_sidecar)
    if (
        payload.get("schema") != CONFIRMED_NOTICE_SCHEMA
        or payload.get("mode") != "confirmed_send"
        or payload.get("ready") is not True
        or payload.get("discord_sent") is not True
    ):
        return None
    request_ref = payload.get("request_json")
    if not isinstance(request_ref, dict):
        return None
    if not isinstance(request_ref.get("path"), str) or not isinstance(request_ref.get("sha256"), str):
        return None
    if not request_path.is_file():
        return None
    try:
        resolved_request = protected_input_file(request_path, "request-pack window-request.json")
    except SystemExit:
        return None
    referenced_request = Path(request_ref["path"])
    try:
        referenced_status = protected_paths.protected_path_status(
            referenced_request,
            protected_root=SERVER_ROOT,
            approved_roots=protected_paths.approved_offline_workspace_roots(),
        )
    except OSError:
        return None
    if referenced_status.protected or referenced_status.resolved != resolved_request:
        return None
    request_sha256 = file_sha256(resolved_request)
    if request_ref["sha256"] != request_sha256:
        return None
    try:
        request_payload = load_json(resolved_request)
    except (OSError, json.JSONDecodeError, SystemExit):
        return None
    if not request_window_current_for_confirmed_notice_binding(request_payload):
        return None
    binding = {
        "notice_report_json": str(resolved_notice),
        "request_pack_path": str(resolved_request),
        "request_pack_sha256": request_sha256,
    }
    if sidecar_path is not None:
        binding["notice_report_sidecar_json"] = sidecar_path
    return binding


def existing_request_pack_confirmed_notice_binding(
    plan: dict[str, Any],
    *,
    report_dir: Path,
    supplied_notice_report: Path | None,
) -> dict[str, Any] | None:
    request_path = Path(plan["artifacts"]["window_request"])
    for candidate in confirmed_notice_candidates(
        report_dir=report_dir,
        supplied_notice_report=supplied_notice_report,
    ):
        binding = confirmed_notice_binds_request_pack(candidate, request_path)
        if binding is not None:
            return binding
    return None


def guard_against_bound_request_pack_mutation(
    plan: dict[str, Any],
    *,
    report_dir: Path,
    supplied_notice_report: Path | None,
    mismatches: list[str],
) -> None:
    binding = existing_request_pack_confirmed_notice_binding(
        plan,
        report_dir=report_dir,
        supplied_notice_report=supplied_notice_report,
    )
    if binding is None:
        return
    mismatch_text = ",".join(mismatches) if mismatches else "unknown"
    raise SystemExit(
        "refusing to mutate existing request pack bound to confirmed notice: "
        f"request_pack={binding['request_pack_path']} "
        f"confirmed_notice={binding['notice_report_json']} "
        f"mismatches={mismatch_text}"
    )


def skipped_prepare_step(command: dict[str, Any], output_path: Path, plan: dict[str, Any]) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "obelisk.player-principal-lifecycle-runtime-window-request-pack-reuse.v1",
        "status": "reused_existing_request_pack",
        "run_id": plan["run_id"],
        "evidence_dir": plan["evidence_dir"],
        "request_pack_path": plan["artifacts"]["window_request"],
        "validated_by_next_step": "check_request_pack",
        "non_claim": (
            "request pack reuse avoids mutating preactivation artifacts; it does not "
            "authorize Discord, server operations, runtime capture, approved runtime "
            "evidence, public readiness, or SDK completion"
        ),
    }
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "id": command["id"],
        "title": command["title"],
        "returncode": 0,
        "ok": True,
        "stdout_path": str(output_path),
        "stdout": None,
        "stderr": "",
        "note": command.get("note"),
        "reused_existing_request_pack": True,
    }


def accept_expected_route_gate_block(step: dict[str, Any], output_path: Path) -> None:
    if step["id"] != "route_gate" or step["ok"]:
        return
    try:
        payload = load_json(output_path)
    except (OSError, json.JSONDecodeError, SystemExit):
        return
    forbidden_true = [
        key
        for key in FALSE_FLAGS
        if payload.get(key) is True
    ]
    if (
        payload.get("schema") == "obelisk.command-permission-route-gate-check.v1"
        and payload.get("planning_only") is True
        and payload.get("route_blocked") is True
        and payload.get("current_route_blocker") == "approved_runtime_evidence_missing"
        and not forbidden_true
    ):
        step["ok"] = True
        step["accepted_expected_blocked_route_gate"] = True
        step["accepted_default_deny_route_gate"] = True
        step["route_gate_valid"] = payload.get("valid") is True
        step["route_gate_forbidden_true_flags"] = forbidden_true


def path_in_report_dir(report_dir: Path, filename: str) -> Path:
    return report_dir / filename


def report_dir_slug(value: object) -> str:
    text = str(value or "").strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "-", text).strip("-._")
    return slug or "unknown"


def default_report_dir_for_plan(plan: dict[str, Any]) -> Path:
    target = plan.get("target")
    if not isinstance(target, dict):
        target = {}
    instance = report_dir_slug(target.get("instance"))
    map_name = report_dir_slug(target.get("map"))
    run_id = report_dir_slug(plan.get("run_id"))
    digest_input = {
        "schema": SCHEMA,
        "target": plan.get("target"),
        "run_id": plan.get("run_id"),
        "approved_window": plan.get("approved_window"),
        "evidence_dir": plan.get("evidence_dir"),
        "obelisk_commit": plan.get("obelisk_commit"),
        "restart_expectation": plan.get("restart_expectation"),
        "notice_path": plan.get("notice_path"),
    }
    digest = hashlib.sha256(canonical_json_bytes(digest_input)).hexdigest()[:16]
    return Path("/tmp") / f"obelisk-player-principal-{instance}-{map_name}-{run_id}-{digest}"


def notice_sidecar_path(report_dir: Path, filename: str) -> Path:
    return report_dir / filename


def command_with_notice_artifact(command: dict[str, Any], artifact_path: Path) -> dict[str, Any]:
    updated = dict(command)
    argv = [str(item) for item in updated.get("argv") or []]
    if "--artifact-json" not in argv:
        try:
            index = argv.index("--json")
        except ValueError:
            argv.extend(["--artifact-json", str(artifact_path)])
        else:
            argv = [*argv[:index], "--artifact-json", str(artifact_path), *argv[index:]]
    updated["argv"] = argv
    updated["shell"] = shell_command(argv, env=updated.get("env") or {})
    updated["executor_notice_artifact"] = {
        "schema": NOTICE_ACTION_ARTIFACT_SCHEMA,
        "path": str(artifact_path),
        "stdout_only_confirmation_accepted": False,
        "sidecar_required_for_confirmed_send_consumption": True,
    }
    return updated


def activation_command_from_plan(
    plan: dict[str, Any],
    *,
    request_check: Path,
    notice_report: Path,
    route_gate: Path,
) -> dict[str, Any]:
    command = dict(command_by_id(plan, "activation_preconditions"))
    argv = list(command["argv"])
    replacements = {
        "--request-check-json": str(request_check),
        "--notice-report-json": str(notice_report),
        "--route-gate-json": str(route_gate),
    }
    for flag, value in replacements.items():
        index = argv.index(flag)
        argv[index + 1] = value
    command["argv"] = argv
    return command


def request_pack_paths(plan: dict[str, Any]) -> dict[str, str]:
    evidence_dir = Path(plan["evidence_dir"])
    return {
        "directory": str(evidence_dir),
        "window_request": plan["artifacts"]["window_request"],
        "observer_env": plan["artifacts"]["observer_env"],
        "operator_approval_request": str(evidence_dir / "operator-approval-request.md"),
        "operator_approval_receipt": plan["artifacts"]["operator_receipt"],
    }


def multi_surface_beta_capture_pack_run_id(plan: dict[str, Any]) -> str:
    text = str(plan.get("run_id") or "runtime-window").strip()
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", text).strip("-._")
    return f"{slug or 'runtime-window'}-multi-surface-beta-capture"


def multi_surface_beta_capture_pack_paths(
    plan: dict[str, Any],
    report_dir: Path,
) -> dict[str, str]:
    run_id = multi_surface_beta_capture_pack_run_id(plan)
    output_root = path_in_report_dir(report_dir, "multi-surface-beta-capture-packs")
    pack_dir = output_root / run_id
    return {
        "output_root": str(output_root),
        "run_id": run_id,
        "pack_dir": str(pack_dir),
        "manifest": str(pack_dir / "manifest.json"),
        "prepare_report": str(
            path_in_report_dir(report_dir, "multi-surface-beta-pack.prepare.json")
        ),
        "check_report": str(path_in_report_dir(report_dir, "multi-surface-beta-pack.check.json")),
    }


def multi_surface_beta_capture_prepare_command(
    plan: dict[str, Any],
    paths: dict[str, str],
) -> dict[str, Any]:
    target = plan["target"]
    argv = [
        sys.executable,
        "scripts/prepare_obelisk_multi_surface_beta_capture_pack.py",
        "--instance",
        str(target["instance"]),
        "--map",
        str(target["map"]),
        "--output-root",
        paths["output_root"],
        "--run-id",
        paths["run_id"],
        "--json",
    ]
    return {
        "id": MULTI_SURFACE_BETA_CAPTURE_PREPARE_STEP_ID,
        "title": "Prepare offline multi-surface beta capture candidate pack",
        "argv": argv,
        "shell": shell_command(argv),
        "note": MULTI_SURFACE_BETA_CAPTURE_NON_AUTHORIZATION,
    }


def multi_surface_beta_capture_check_command(
    plan: dict[str, Any],
    paths: dict[str, str],
) -> dict[str, Any]:
    target = plan["target"]
    argv = [
        sys.executable,
        "scripts/check_obelisk_multi_surface_beta_capture_pack.py",
        paths["pack_dir"],
        "--expected-instance",
        str(target["instance"]),
        "--expected-map",
        str(target["map"]),
        "--json",
    ]
    return {
        "id": MULTI_SURFACE_BETA_CAPTURE_CHECK_STEP_ID,
        "title": "Validate offline multi-surface beta capture candidate pack",
        "argv": argv,
        "shell": shell_command(argv),
        "note": MULTI_SURFACE_BETA_CAPTURE_NON_AUTHORIZATION,
    }


def multi_surface_beta_capture_command(
    step_id: str,
    *,
    plan: dict[str, Any],
    paths: dict[str, str],
) -> dict[str, Any]:
    if step_id == MULTI_SURFACE_BETA_CAPTURE_PREPARE_STEP_ID:
        return multi_surface_beta_capture_prepare_command(plan, paths)
    if step_id == MULTI_SURFACE_BETA_CAPTURE_CHECK_STEP_ID:
        return multi_surface_beta_capture_check_command(plan, paths)
    raise SystemExit(f"unknown multi-surface beta capture step id {step_id}")


def report_output_paths(
    plan: dict[str, Any],
    *,
    report_dir: Path,
    request_check: Path,
    dry_run_notice: Path,
    route_gate: Path,
    activation_report: Path,
    dry_run_notice_sidecar: Path,
    confirmed_notice_sidecar: Path,
    executor_report: Path,
    post_window_next_actions_dry_run: Path,
    notice_report_path: str | None,
    multi_surface_pack_paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    paths = {
        "request_pack": request_pack_paths(plan),
        "request_check_report": str(request_check),
        "dry_run_report": str(dry_run_notice),
        "dry_run_notice_sidecar": str(dry_run_notice_sidecar),
        "route_gate_report": str(route_gate),
        "activation_preconditions_report": str(activation_report),
        "confirmed_notice_report_expected": str(report_dir / "beta-notice.confirmed.json"),
        "confirmed_notice_sidecar_expected": str(confirmed_notice_sidecar),
        "confirmed_notice_report_used": notice_report_path,
        "runtime_window_execution_report": str(executor_report),
        "post_window_next_actions_dry_run_report": str(post_window_next_actions_dry_run),
    }
    if multi_surface_pack_paths is not None:
        paths["multi_surface_beta_capture_pack"] = multi_surface_pack_paths
    return paths


def step_by_id(steps: list[dict[str, Any]], step_id: str) -> dict[str, Any] | None:
    for step in steps:
        if step.get("id") == step_id:
            return step
    return None


def load_optional_json(path_value: str | None) -> dict[str, Any]:
    if not path_value:
        return {}
    path = Path(path_value)
    if not path.is_file():
        return {}
    try:
        return load_json(protected_input_file(path, path.name))
    except (OSError, json.JSONDecodeError, SystemExit):
        return {}


def multi_surface_beta_capture_pack_execution_summary(
    *,
    requested: bool,
    paths: dict[str, str] | None,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    prepare_step = step_by_id(steps, MULTI_SURFACE_BETA_CAPTURE_PREPARE_STEP_ID)
    check_step = step_by_id(steps, MULTI_SURFACE_BETA_CAPTURE_CHECK_STEP_ID)
    check_payload = load_optional_json(paths.get("check_report") if paths else None)
    prepare_ok = prepare_step is not None and prepare_step.get("ok") is True
    check_ok = check_step is not None and check_step.get("ok") is True
    candidate_integrity_validated = (
        check_ok and check_payload.get("status") == "candidate_pack_validated"
    )
    if not requested:
        status = "not_requested"
    elif candidate_integrity_validated:
        status = "candidate_pack_prepared_and_checked"
    elif prepare_step is None:
        status = "not_executed"
    elif not prepare_ok:
        status = "candidate_pack_prepare_failed"
    elif check_step is None:
        status = "candidate_pack_check_not_executed"
    else:
        status = "candidate_pack_check_failed"
    return {
        "schema": MULTI_SURFACE_BETA_CAPTURE_EXECUTOR_PREPARATION_SCHEMA,
        "status": status,
        "requested": requested,
        "executed_by_executor": prepare_step is not None or check_step is not None,
        "offline_only": True,
        "candidate_only": True,
        "pack_paths": paths or {},
        "step_ids": [
            step_id
            for step_id in (
                MULTI_SURFACE_BETA_CAPTURE_PREPARE_STEP_ID,
                MULTI_SURFACE_BETA_CAPTURE_CHECK_STEP_ID,
            )
            if step_by_id(steps, step_id) is not None
        ],
        "prepare_step_ok": prepare_ok,
        "check_step_ok": check_ok,
        "check_status": check_payload.get("status"),
        "check_ready_scope": check_payload.get("ready_scope"),
        "candidate_pack_integrity_validated": candidate_integrity_validated,
        "candidate_pack_integrity_only": True,
        "candidate_pack_integrity_validation_scope": "candidate_capture_pack_integrity_only",
        "candidate_pack_integrity_validated_counts_as_approved_runtime_evidence": False,
        "candidate_pack_integrity_validated_counts_as_runtime_evidence": False,
        "candidate_pack_integrity_validated_counts_as_sdk_progress": False,
        "candidate_pack_integrity_validated_counts_as_p0_progress": False,
        "approved_evidence_bundle_checker_accepted": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "authorizes_runtime_work": False,
        "authorizes_discord": False,
        "authorizes_live_ops": False,
        "authorizes_server_operations": False,
        "authorizes_live_log_reads": False,
        "authorizes_marker_env_writes": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "plugin_hub_ready": False,
        "publication_ready": False,
        "boundary": multi_surface_beta_capture_pack_boundary(),
        "non_authorization": MULTI_SURFACE_BETA_CAPTURE_NON_AUTHORIZATION,
    }


def plan_has_standing_launch_authority(plan: dict[str, Any]) -> bool:
    authority = plan.get("standing_launch_authority")
    return (
        isinstance(authority, dict)
        and authority.get("recorded") is True
        and authority.get("bound_by_prepare_command") is True
    )


def standing_launch_authority_reference(plan: dict[str, Any]) -> str | None:
    authority = plan.get("standing_launch_authority")
    if not isinstance(authority, dict):
        return None
    reference = authority.get("reference")
    return reference if isinstance(reference, str) and reference else None


def multi_surface_beta_capture_action_boundary_fields() -> dict[str, Any]:
    return {
        "multi_surface_beta_capture_pack_metadata_only": True,
        "multi_surface_beta_capture_pack_offline_candidate_metadata_only": True,
        "multi_surface_beta_capture_pack_authorizes_runtime_work": False,
        "multi_surface_beta_capture_pack_authorizes_discord": False,
        "multi_surface_beta_capture_pack_authorizes_discord_send": False,
        "multi_surface_beta_capture_pack_authorizes_live_ops": False,
        "multi_surface_beta_capture_pack_authorizes_server_operations": False,
        "multi_surface_beta_capture_pack_authorizes_server_restart": False,
        "multi_surface_beta_capture_pack_authorizes_live_log_reads": False,
        "multi_surface_beta_capture_pack_authorizes_marker_env_writes": False,
        "multi_surface_beta_capture_pack_authorizes_marker_or_env_changes": False,
        "multi_surface_beta_capture_pack_counts_as_approved_runtime_evidence": False,
        "multi_surface_beta_capture_pack_counts_as_runtime_evidence": False,
        "multi_surface_beta_capture_pack_counts_as_sdk_progress": False,
        "multi_surface_beta_capture_pack_counts_as_p0_progress": False,
        "multi_surface_beta_capture_pack_clears_approved_runtime_evidence_missing": False,
    }


def multi_surface_beta_capture_pack_boundary() -> dict[str, Any]:
    return {
        "schema": MULTI_SURFACE_BETA_CAPTURE_PACK_BOUNDARY_SCHEMA,
        "status": "offline_candidate_metadata_only",
        "family_schemas": sorted(MULTI_SURFACE_BETA_CAPTURE_FAMILY_SCHEMAS),
        "candidate_pack_generator": "scripts/prepare_obelisk_multi_surface_beta_capture_pack.py",
        "candidate_plan_generator": "scripts/plan_obelisk_multi_surface_beta_capture.py",
        "metadata_reference_allowed": True,
        "post_window_state_input_accepted": False,
        "accepted_post_window_state_schemas": sorted(
            (CLOSURE_REQUEST_SCHEMA, *PASSIVE_SUMMARY_SCHEMAS)
        ),
        "approved_runtime_evidence_checker": (
            "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
        ),
        "approved_evidence_bundle_checker_accepted": False,
        "approved_evidence_bundle_acceptance_required": True,
        "candidate_pack_integrity_validation_scope": "candidate_capture_pack_integrity_only",
        "candidate_pack_integrity_validated_counts_as_approved_runtime_evidence": False,
        "candidate_pack_integrity_validated_counts_as_runtime_evidence": False,
        "candidate_pack_integrity_validated_counts_as_sdk_progress": False,
        "candidate_pack_integrity_validated_counts_as_p0_progress": False,
        "non_claim_flags": {
            "candidate_only": True,
            "offline_candidate_metadata_only": True,
            **MULTI_SURFACE_BETA_CAPTURE_FALSE_FLAGS,
        },
        **multi_surface_beta_capture_action_boundary_fields(),
        "non_authorization": MULTI_SURFACE_BETA_CAPTURE_NON_AUTHORIZATION,
    }


def standing_authority_non_progress_boundary(
    *,
    standing: bool,
    scope: str,
) -> dict[str, Any]:
    return {
        "schema": "obelisk.player-principal-lifecycle-standing-authority-non-progress-boundary.v1",
        "scope": scope,
        "standing_launch_authority_recorded": standing,
        "recorded_standing_authority_applies_to_preparation_only": standing,
        "authorization_for_scoped_operator_actions_only": False,
        "standing_authority_authorizes_discord_send": False,
        "standing_authority_authorizes_runtime_evidence": False,
        "standing_authority_authorizes_marker_env_changes": False,
        "standing_authority_authorizes_server_restart": False,
        "standing_authority_counts_as_approved_runtime_evidence": False,
        "standing_authority_counts_as_runtime_evidence": False,
        "standing_authority_counts_as_sdk_evidence": False,
        "standing_authority_counts_as_runtime_progress": False,
        "standing_authority_counts_as_sdk_progress": False,
        "standing_authority_counts_toward_p0_dependency_chain": False,
        "standing_authority_grants_runtime_readiness": False,
        "standing_authority_grants_public_sdk_readiness": False,
        "approved_runtime_evidence_ready": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "grants_readiness_claims": False,
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
        "server_restart_authorized_by_executor": False,
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
            "required_exact_call": SESSION_START_REJECTED_REQUIRED_CALL,
            "exact_check_join_in_progress_requirement": SESSION_START_REJECTED_REQUIRED_CALL,
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
        "exact_check_join_in_progress_requirement": SESSION_START_REJECTED_REQUIRED_CALL,
        "exact_session_start_rejected_required": True,
        "matched_session_end_required": True,
        "requires_copied_log_bundle_checker_acceptance": True,
        "standing_authority_satisfies_missing_roles": False,
        "executor_satisfies_missing_roles": False,
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


def recommended_notice_text(
    *,
    target: dict[str, Any],
    approved_window: dict[str, Any] | None = None,
) -> dict[str, Any]:
    window = approved_window if isinstance(approved_window, dict) else {}
    start_utc = window.get("start_utc", "scheduled window")
    end_utc = window.get("end_utc", "scheduled window")
    instance = target.get("instance", "target")
    map_name = target.get("map", "map")
    objective_text = EXACT_TESTER_EVIDENCE_OBJECTIVE
    discord_text = (
        f"Obelisk beta window for {map_name} on {instance} ({start_utc} to {end_utc} UTC). "
        f"Please direct-join the exact target, stay in that session, and leave once when "
        f"asked so testers can {objective_text}. Do not post player names, chat, Steam "
        f"IDs, private credentials."
    )
    broadcast_text = (
        "Obelisk beta validation window starting now. Selected tester direct-joins the "
        f"exact target and follows the lead so the copied evidence can {objective_text}."
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
        "two_server_cap_policy": two_server_cap_policy(),
        "lifecycle_role_objectives": lifecycle_role_objectives(),
        "tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "exact_tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "readiness_claim_allowed": False,
        "progress_claim_allowed": False,
        "preparation_counts_as_readiness": False,
        "preparation_counts_as_progress": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_toward_sdk": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def external_execution_authority(plan: dict[str, Any]) -> dict[str, Any]:
    standing = plan_has_standing_launch_authority(plan)
    authority = plan.get("standing_launch_authority")
    if not isinstance(authority, dict):
        authority = {}
    return {
        "schema": "obelisk.player-principal-lifecycle-external-execution-authority.v1",
        "standing_launch_authority_recorded": standing,
        "standing_launch_authority_reference": authority.get("reference"),
        "standing_launch_authority_satisfies_beta_notice_scope": standing,
        "standing_authority_satisfies_guarded_beta_notice_send_scope": standing,
        "guarded_beta_notice_send_scope_satisfied_by_standing_authority": standing,
        "standing_launch_authority_satisfies_dry_run_notice_preparation_scope": standing,
        "standing_launch_authority_satisfies_active_observation_scope": False,
        "standing_authority_preparation_only": False,
        "standing_authority_authorizes_discord_send": standing,
        "standing_authority_authorizes_runtime_evidence": False,
        "standing_authority_authorizes_marker_env_changes": False,
        "standing_authority_authorizes_server_restart": False,
        "fresh_current_turn_operator_authorization_required": not standing,
        "separate_operator_authorization_required": not standing,
        "offline_executor_sends_discord": False,
        "discord_send_performed_by_executor": False,
        "offline_executor_touches_ark": False,
        "offline_executor_reads_live_logs": False,
        "offline_executor_edits_markers_or_env": False,
        "prepared_actions_remain_notice_only_or_request_only": True,
        "two_server_cap_policy": two_server_cap_policy(),
        "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
        "recommended_notice_text": recommended_notice_text(
            target=plan.get("target", {}),
            approved_window=plan.get("approved_window"),
        ),
        "standing_authority_non_progress_boundary": standing_authority_non_progress_boundary(
            standing=standing,
            scope="external_execution_authority",
        ),
        "standing_authority_counts_as_runtime_progress": False,
        "standing_authority_counts_as_sdk_progress": False,
        "standing_authority_grants_runtime_readiness": False,
        "approved_evidence_bundle_checker_accepted": False,
        "approved_evidence_bundle_acceptance_required": True,
        "approved_evidence_bundle_acceptance_requirement": approved_evidence_bundle_acceptance_requirement(),
        **multi_surface_beta_capture_action_boundary_fields(),
        "multi_surface_beta_capture_pack_boundary": multi_surface_beta_capture_pack_boundary(),
        "non_authorization": NON_AUTHORIZATION,
    }


def copied_log_route_contract() -> dict[str, Any]:
    return {
        "schema": COPIED_LOG_ROUTE_CONTRACT_SCHEMA,
        "ordered_step_ids": list(COPIED_LOG_ROUTE_STEP_IDS),
        "tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "exact_tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "route": (
            "copied sibling-set evidence dir -> one-shot approved runtime evidence bundle "
            "builder with internal analyzer, strict_lifecycle_triplet_candidate_summary, "
            "bundle checks, and approved-evidence checker"
        ),
        "copied_log_source": "offline_copied_obelisk_log_only",
        "analyzer": RUNTIME_OBSERVER_ANALYZER,
        "strict_lifecycle_triplet_candidate_summary_json_path": (
            STRICT_LIFECYCLE_TRIPLET_CANDIDATE_SUMMARY_JSON_PATH
        ),
        "one_shot_bundle_builder": APPROVED_RUNTIME_EVIDENCE_BUNDLE_BUILDER,
        "approved_evidence_checker": APPROVED_RUNTIME_EVIDENCE_CHECKER,
        "checker_acceptance_required_before_evidence_state_change": True,
        "all_prior_outputs_non_authorizing_and_non_evidence": True,
        "approved_evidence_checker_accepted_by_this_report": False,
        "authorized_by_this_report": False,
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
        "readiness_claim_allowed": False,
        "progress_claim_allowed": False,
        "preparation_counts_as_readiness": False,
        "preparation_counts_as_progress": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "non_authorization": (
            "copied-log route metadata is offline follow-up guidance only; the one-shot "
            "bundle builder must run against a copied sibling-set evidence dir and its "
            "internal approved-evidence checker must accept the approved manifest before "
            "any runtime-evidence state can change"
        ),
    }


def approved_evidence_bundle_acceptance_requirement() -> dict[str, Any]:
    return {
        "schema": APPROVED_EVIDENCE_BUNDLE_ACCEPTANCE_SCHEMA,
        "checker": "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
        "accepted_bundle_required_before_any_readiness_or_progress_claim": True,
        "approved_evidence_bundle_checker_accepted": False,
        "tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "exact_tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "copied_log_route_required": copied_log_route_contract(),
        "ordered_copied_log_route_step_ids": list(COPIED_LOG_ROUTE_STEP_IDS),
        "required_lifecycle_event_role_triplet": list(REQUIRED_LIFECYCLE_EVENT_ROLES),
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
        "readiness_claim_allowed": False,
        "progress_claim_allowed": False,
        "preparation_counts_as_readiness": False,
        "preparation_counts_as_progress": False,
        **multi_surface_beta_capture_action_boundary_fields(),
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


def prepared_action_boundary_fields(mode: str) -> dict[str, Any]:
    return {
        "prepared_action_mode": mode,
        "prepared_action_scope": "notice_only_or_request_only",
        "notice_only_or_request_only_until_approved_evidence_bundle_accepted": True,
        "automatic_execution_allowed": False,
        "automatic_start_or_restart_allowed": False,
        "automatic_discord_send_allowed": False,
        "automatic_evidence_acceptance_allowed": False,
        "human_or_lead_action_required_for_side_effects": True,
        "standing_authority_metadata_only": True,
        "approved_evidence_bundle_checker_accepted": False,
        "approved_evidence_bundle_acceptance_required": True,
        "approved_evidence_bundle_acceptance_requirement": approved_evidence_bundle_acceptance_requirement(),
        "passive_or_no_user_state_counts_as_approved_runtime_evidence": False,
        "prepared_actions_count_as_readiness": False,
        "prepared_actions_count_as_progress": False,
        "readiness_claim_allowed": False,
        "progress_claim_allowed": False,
        "no_users_no_testers_passive_wait_counts_as_readiness": False,
        "no_users_no_testers_passive_wait_counts_as_progress": False,
        "no_users_no_testers_passive_wait_counts_as_authorization": False,
        "no_users_no_testers_passive_wait_counts_as_notice_sent": False,
        "two_server_cap_policy": two_server_cap_policy(),
        "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
        **multi_surface_beta_capture_action_boundary_fields(),
    }


def attach_prepared_action_boundaries(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for action in actions:
        mode = str(action.get("prepared_action_mode") or prepared_action_mode(action))
        action.update(prepared_action_boundary_fields(mode))
    return actions


def prepared_artifact_boundary(
    *,
    plan: dict[str, Any],
    output_paths: dict[str, Any],
    post_window_state: dict[str, Any],
) -> dict[str, Any]:
    boundary = {
        "schema": PREPARED_ARTIFACT_BOUNDARY_SCHEMA,
        "classification": "prepared_artifacts_only",
        "run_id": plan.get("run_id"),
        "fresh_retry_after_closed_non_evidence_window": runtime_fresh_retry_after_closed_non_evidence_window(
            plan,
            output_paths=output_paths,
        ),
        "request_pack": request_pack_paths(plan),
        "offline_reports": output_paths,
        "post_window_state_source_json": post_window_state.get("source_path"),
        "prepared_artifacts_authorize_machine_actions": False,
        "prepared_artifacts_authorize_discord_send": False,
        "prepared_artifacts_authorize_server_operations": False,
        "prepared_artifacts_authorize_runtime_capture": False,
        "prepared_artifacts_count_as_approved_runtime_evidence": False,
        "prepared_artifacts_count_toward_sdk": False,
        "non_authorization": NON_AUTHORIZATION,
    }
    multi_surface_pack_paths = output_paths.get("multi_surface_beta_capture_pack")
    if isinstance(multi_surface_pack_paths, dict):
        boundary["multi_surface_beta_capture_pack"] = multi_surface_pack_paths
        boundary["multi_surface_beta_capture_pack_metadata_only"] = True
        boundary["multi_surface_beta_capture_pack_counts_as_approved_runtime_evidence"] = False
    return boundary


def action_side_effect_domain(action: dict[str, Any]) -> str:
    contract = action.get("runner_contract")
    if isinstance(contract, dict) and isinstance(contract.get("side_effect_domain"), str):
        return contract["side_effect_domain"]
    return str(action.get("side_effect_domain") or "none")


def action_ids_with_predicate(
    actions: list[dict[str, Any]],
    predicate: Any,
) -> list[str]:
    return [
        str(action.get("id"))
        for action in actions
        if isinstance(action.get("id"), str) and predicate(action)
    ]


def human_lead_action_boundary(actions: list[dict[str, Any]]) -> dict[str, Any]:
    side_effect_action_ids = action_ids_with_predicate(
        actions,
        lambda action: action_side_effect_domain(action)
        not in {"none", "offline_report_write"},
    )
    manual_action_ids = action_ids_with_predicate(
        actions,
        lambda action: action.get("status") == "manual_external_not_executed_by_executor",
    )
    return {
        "schema": HUMAN_LEAD_ACTION_BOUNDARY_SCHEMA,
        "classification": "human_or_lead_actions_not_automatic",
        "action_ids": manual_action_ids,
        "side_effect_action_ids": side_effect_action_ids,
        "side_effects_require_human_or_lead_execution": True,
        "automatic_start_or_restart_allowed": False,
        "automatic_discord_send_allowed": False,
        "automatic_marker_env_changes_allowed": False,
        "automatic_live_log_reads_allowed": False,
        "automatic_evidence_acceptance_allowed": False,
        "server_operations_performed_by_executor": False,
        "discord_send_performed_by_executor": False,
        "approved_evidence_accepted_by_executor": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def standing_authority_metadata_boundary(plan: dict[str, Any]) -> dict[str, Any]:
    standing = plan_has_standing_launch_authority(plan)
    return {
        "schema": STANDING_AUTHORITY_METADATA_SCHEMA,
        "classification": "standing_authority_metadata_only",
        "standing_launch_authority_recorded": standing,
        "standing_launch_authority_reference": standing_launch_authority_reference(plan),
        "standing_authority_preserved_as_metadata": True,
        "standing_authority_converted_to_machine_action": False,
        "standing_authority_authorizes_runner_execution": False,
        "standing_authority_authorizes_discord_send": False,
        "standing_authority_authorizes_server_restart": False,
        "standing_authority_authorizes_marker_env_changes": False,
        "standing_authority_authorizes_runtime_capture": False,
        "standing_authority_counts_as_approved_runtime_evidence": False,
        "standing_authority_counts_as_runtime_evidence": False,
        "standing_authority_counts_as_sdk_progress": False,
        "standing_authority_grants_runtime_readiness": False,
        "standing_authority_grants_public_sdk_readiness": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def passive_wait_boundary(
    *,
    post_window_state: dict[str, Any],
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    passive_wait = post_window_state.get("no_users_passive_wait")
    passive_action_ids = action_ids_with_predicate(
        actions,
        lambda action: "passive_wait" in str(
            action.get("action_kind") or action.get("id") or action.get("action") or ""
        ),
    )
    return {
        "schema": PASSIVE_WAIT_BOUNDARY_SCHEMA,
        "classification": "passive_wait_source_only_non_evidence",
        "passive_wait_present": isinstance(passive_wait, dict),
        "passive_wait_action_ids": passive_action_ids,
        "passive_wait": passive_wait if isinstance(passive_wait, dict) else None,
        "process_control": (
            passive_wait.get("process_control") if isinstance(passive_wait, dict) else "none"
        ),
        "passive_wait_is_wait_only": True,
        "restart_recommended": False,
        "start_or_restart_recommended": False,
        "monitor_command_executed_by_report": False,
        "monitor_command_authorized_by_report": False,
        "passive_wait_counts_as_approved_runtime_evidence": False,
        "passive_wait_counts_as_runtime_evidence": False,
        "passive_wait_counts_as_sdk_progress": False,
        "passive_wait_authorizes_runtime_capture": False,
        "non_authorization": NO_USERS_PASSIVE_WAIT_NON_AUTHORIZATION,
    }


def active_player_no_accepted_events_boundary(
    *,
    post_window_state: dict[str, Any],
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    policy = post_window_state.get("active_player_no_accepted_events_policy")
    if not isinstance(policy, dict):
        policy = {}
    action_ids = action_ids_with_predicate(
        actions,
        lambda action: "active_player_no_accepted_events" in str(
            action.get("action_kind") or action.get("id") or action.get("action") or ""
        )
        or "drift" in str(action.get("action_kind") or action.get("id") or action.get("action") or "")
        or "wait_or_prompt" in str(action.get("action_kind") or action.get("id") or action.get("action") or ""),
    )
    return {
        "schema": ACTIVE_PLAYER_NO_ACCEPTED_EVENTS_BOUNDARY_SCHEMA,
        "classification": "active_player_no_accepted_events_metadata_only",
        "state_detected": policy.get("state_detected") is True,
        "policy": policy if policy else None,
        "action_ids": action_ids,
        "restart_recommended": False,
        "start_or_restart_recommended": False,
        "restart_requires_concrete_deploy_or_gate_change": True,
        "ask_reconnect_or_logout_now": False,
        "wait_or_player_prompt_requires_exact_preconditions": True,
        "standing_authority_metadata_only": True,
        "standing_authority_authorizes_server_restart": False,
        "standing_authority_authorizes_marker_env_changes": False,
        "standing_authority_authorizes_runtime_evidence": False,
        "two_server_cap_policy": two_server_cap_policy(),
        "server_operations_authorized": False,
        "runtime_capture_authorized": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_as_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "non_authorization": POST_WINDOW_STATE_NON_AUTHORIZATION,
    }


def checker_required_post_window_replay_boundary(
    post_window_state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": CHECKER_REQUIRED_POST_WINDOW_REPLAY_SCHEMA,
        "classification": "checker_required_before_evidence_acceptance",
        "post_window_replay_required": True,
        "checker_required_before_any_readiness_or_progress_claim": True,
        "checker": "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
        "bundle_builder": "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py",
        "copied_log_route_required": copied_log_route_contract(),
        "ordered_copied_log_route_step_ids": list(COPIED_LOG_ROUTE_STEP_IDS),
        "post_window_replay_flag": "--post-window-replay",
        "approved_bundle_manifest_relative_path": APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
        "source_path": post_window_state.get("source_path"),
        "source_classification": post_window_state.get("source_classification"),
        "required_lifecycle_event_role_triplet": list(REQUIRED_LIFECYCLE_EVENT_ROLES),
        "missing_lifecycle_event_roles": post_window_state.get(
            "exact_missing_lifecycle_event_roles",
            [],
        ),
        "approved_evidence_bundle_checker_accepted": False,
        "accepted_by_this_report": False,
        "clears_approved_runtime_evidence_missing": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "non_authorization": POST_WINDOW_STATE_NON_AUTHORIZATION,
    }


def runtime_execution_boundaries(
    *,
    plan: dict[str, Any],
    output_paths: dict[str, Any],
    next_actions: list[dict[str, Any]],
    post_window_next_actions: list[dict[str, Any]],
    post_window_state: dict[str, Any],
) -> dict[str, Any]:
    all_actions = [*next_actions, *post_window_next_actions]
    return {
        "schema": EXECUTION_BOUNDARIES_SCHEMA,
        "classification": "offline_boundaries_no_automatic_side_effects",
        "prepared_artifacts": prepared_artifact_boundary(
            plan=plan,
            output_paths=output_paths,
            post_window_state=post_window_state,
        ),
        "human_lead_actions": human_lead_action_boundary(all_actions),
        "standing_authority_metadata": standing_authority_metadata_boundary(plan),
        "passive_waits": passive_wait_boundary(
            post_window_state=post_window_state,
            actions=all_actions,
        ),
        "active_player_no_accepted_events": active_player_no_accepted_events_boundary(
            post_window_state=post_window_state,
            actions=all_actions,
        ),
        "checker_required_post_window_replay": checker_required_post_window_replay_boundary(
            post_window_state
        ),
        "evidence_pipeline_command_sequence": runtime_evidence_command_sequence(
            plan=plan,
            blockers=[] if output_paths else ["executor_output_paths_not_available"],
        ),
        "fresh_retry_after_closed_non_evidence_window": runtime_fresh_retry_after_closed_non_evidence_window(
            plan,
            output_paths=output_paths,
        ),
        "runtime_window_stale_prevention": runtime_window_stale_prevention_from_plan(plan),
        "beta_notice_sequence_enforcement": beta_notice_sequence_enforcement(plan),
        "automatic_start_or_restart_allowed": False,
        "automatic_discord_send_allowed": False,
        "automatic_evidence_acceptance_allowed": False,
        "standing_authority_converted_to_machine_action": False,
        "approved_evidence_bundle_checker_accepted": False,
        "approved_runtime_evidence_ready": False,
        "current_route_blocker": "approved_runtime_evidence_missing",
        "non_authorization": NON_AUTHORIZATION,
    }


def runner_authority_fields(plan: dict[str, Any]) -> dict[str, Any]:
    standing = plan_has_standing_launch_authority(plan)
    authority_source = (
        "recorded_standing_launch_authority"
        if standing
        else "fresh_current_turn_operator_scope"
    )
    return {
        "authority_source": authority_source,
        "standing_launch_authority_reference": standing_launch_authority_reference(plan),
        "recorded_standing_launch_authority_satisfies_scope": False,
        "recorded_standing_debug_authority_satisfies_scope": False,
        "recorded_standing_launch_authority_satisfies_preparation_scope": standing,
        "recorded_standing_debug_authority_satisfies_preparation_scope": standing,
        "runner_may_use_recorded_standing_authority": False,
        "runner_may_use_recorded_standing_authority_for_preparation_only": standing,
        "separate_operator_authorization_required": True,
        "standing_authority_authorizes_discord_send": False,
        "standing_authority_authorizes_runtime_evidence": False,
        "standing_authority_authorizes_marker_env_changes": False,
        "standing_authority_authorizes_server_restart": False,
        "two_server_cap_policy": two_server_cap_policy(),
        "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
        "standing_authority_non_progress_boundary": standing_authority_non_progress_boundary(
            standing=standing,
            scope="runner_authority_fields",
        ),
        "standing_authority_counts_as_runtime_progress": False,
        "standing_authority_counts_as_sdk_progress": False,
        "standing_authority_grants_runtime_readiness": False,
    }


def runner_contract(
    plan: dict[str, Any],
    *,
    phase: str,
    operation_kind: str,
    side_effect_domain: str,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stale_prevention = runtime_window_stale_prevention_from_plan(plan)
    notice_sequence = beta_notice_sequence_enforcement(plan)
    authority = runner_authority_fields(plan)
    standing = plan_has_standing_launch_authority(plan)
    if operation_kind == "guarded_beta_notice_send" and standing:
        authority.update(
            {
                "recorded_standing_launch_authority_satisfies_scope": True,
                "runner_may_use_recorded_standing_authority": True,
                "runner_may_use_recorded_standing_authority_for_preparation_only": False,
                "separate_operator_authorization_required": False,
                "standing_authority_satisfies_guarded_beta_notice_send_scope": True,
                "guarded_beta_notice_send_scope_satisfied_by_standing_authority": True,
                "standing_authority_authorizes_discord_send": True,
            }
        )
    return {
        "schema": NEXT_ACTION_RUNNER_CONTRACT_SCHEMA,
        "runner": "lead_runtime_runner",
        "phase": phase,
        "operation_kind": operation_kind,
        "side_effect_domain": side_effect_domain,
        "deterministic": True,
        "execute_by_default": False,
        "manual_external_execution_required": True,
        "side_effects_performed_by_executor": False,
        "run_id": plan.get("run_id"),
        "target": plan.get("target"),
        "approved_window": plan.get("approved_window"),
        "fresh_retry_after_closed_non_evidence_window": runtime_fresh_retry_after_closed_non_evidence_window(
            plan
        ),
        "runtime_window_stale_prevention": stale_prevention,
        "beta_notice_sequence_enforcement": notice_sequence,
        "inputs": inputs or {},
        "outputs": outputs or {},
        **authority,
        "non_authorization": NON_AUTHORIZATION,
    }


def runner_command(
    argv: Any,
    *,
    redirect_stdout: str | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    normalized_argv = [str(item) for item in argv] if isinstance(argv, list) else []
    return {
        "schema": NEXT_ACTION_RUNNER_COMMAND_SCHEMA,
        "cwd": str(REPO_ROOT),
        "argv": normalized_argv,
        "env": dict(sorted((env or {}).items())),
        "redirect_stdout": redirect_stdout,
        "stdout_json_expected": True,
        "execute_by_default": False,
        "performed_by_executor": False,
    }


def runner_operation(
    kind: str,
    *,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    safety: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema": NEXT_ACTION_RUNNER_OPERATION_SCHEMA,
        "kind": kind,
        "inputs": inputs or {},
        "outputs": outputs or {},
        "safety": safety or {},
        "execute_by_default": False,
        "performed_by_executor": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def action_with_runner(
    action: dict[str, Any],
    plan: dict[str, Any],
    *,
    phase: str,
    operation_kind: str,
    side_effect_domain: str,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    command: dict[str, Any] | None = None,
    operation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mode = str(action.get("prepared_action_mode") or prepared_action_mode(action))
    stale_prevention = runtime_window_stale_prevention_from_plan(plan)
    notice_sequence = beta_notice_sequence_enforcement(plan)
    contract = runner_contract(
        plan,
        phase=phase,
        operation_kind=operation_kind,
        side_effect_domain=side_effect_domain,
        inputs=inputs,
        outputs=outputs,
    )
    contract.update(prepared_action_boundary_fields(mode))
    resolved_operation = operation or runner_operation(operation_kind, inputs=inputs, outputs=outputs)
    if isinstance(resolved_operation, dict):
        resolved_operation = {
            **resolved_operation,
            "runtime_window_stale_prevention": stale_prevention,
            "beta_notice_sequence_enforcement": notice_sequence,
            **prepared_action_boundary_fields(mode),
        }
    return {
        "schema": NEXT_ACTION_SCHEMA,
        "status": action.get("status", "manual_external_not_executed_by_executor"),
        **action,
        "runtime_window_stale_prevention": stale_prevention,
        "beta_notice_sequence_enforcement": notice_sequence,
        **prepared_action_boundary_fields(mode),
        "runner_contract": contract,
        "runner_command": command,
        "runner_operation": resolved_operation,
    }


def manual_followup_step(plan: dict[str, Any], step_id: str) -> dict[str, Any]:
    steps = plan.get("manual_followup_steps")
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict) and step.get("id") == step_id:
                return step
    return {}


def load_request_pack_payload(plan: dict[str, Any]) -> dict[str, Any]:
    path = Path(plan["artifacts"]["window_request"])
    if not path.is_file():
        return {}
    try:
        return load_json(protected_input_file(path, "request-pack window-request.json"))
    except (OSError, json.JSONDecodeError, SystemExit):
        return {}


def nested_dict(value: Any, *keys: str) -> dict[str, Any]:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}


def required_evidence_paths(request: dict[str, Any], output_paths: dict[str, Any]) -> dict[str, Any]:
    paths = nested_dict(
        request,
        "current_turn_approval_scope",
        "required_named_scope",
        "evidence_paths",
    )
    if paths:
        return paths
    return {
        "window_request_json": output_paths["request_pack"]["window_request"],
        "observer_window_env": output_paths["request_pack"]["observer_env"],
        "operator_approval_request_md": output_paths["request_pack"]["operator_approval_request"],
        "operator_approval_receipt_json": output_paths["request_pack"]["operator_approval_receipt"],
    }


def target_key_prefix(plan: dict[str, Any]) -> str:
    target = plan["target"]
    return f"{target['instance']}:{target['map']}"


def target_key_matches_plan(key: str, plan: dict[str, Any]) -> bool:
    prefix = target_key_prefix(plan)
    return key == prefix or key.startswith(f"{prefix}:")


def passive_player_presence(summary: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    players_by_target = summary.get("players_current_by_target")
    if not isinstance(players_by_target, dict):
        players_by_target = {}
    matched_players: dict[str, int | None] = {}
    for key, value in players_by_target.items():
        if not isinstance(key, str) or not target_key_matches_plan(key, plan):
            continue
        matched_players[key] = value if isinstance(value, int) and not isinstance(value, bool) else None

    detected_targets = [
        key
        for key in as_string_list(summary.get("targets_with_players_detected"))
        if target_key_matches_plan(key, plan)
    ]
    warning_targets = [
        key
        for key in as_string_list(summary.get("targets_with_query_warning"))
        if target_key_matches_plan(key, plan)
    ]
    query_warnings = summary.get("query_warnings_by_target")
    if isinstance(query_warnings, dict):
        for key in query_warnings:
            if isinstance(key, str) and target_key_matches_plan(key, plan) and key not in warning_targets:
                warning_targets.append(key)

    positive_counts = [
        value for value in matched_players.values() if isinstance(value, int) and value > 0
    ]
    zero_counts = [
        value for value in matched_players.values() if isinstance(value, int) and value == 0
    ]
    unknown_targets = [
        key for key, value in matched_players.items() if not isinstance(value, int)
    ]
    target_presence_known = bool(matched_players or detected_targets or warning_targets)
    players_present = bool(positive_counts or detected_targets)
    unknown_player_context = bool(unknown_targets or warning_targets)
    no_users_detected = (
        bool(matched_players)
        and not players_present
        and not unknown_player_context
        and len(zero_counts) == len(matched_players)
    )
    return {
        "schema": "obelisk.player-principal-lifecycle-passive-player-presence.v1",
        "target": plan["target"],
        "target_key_prefix": target_key_prefix(plan),
        "target_presence_known": target_presence_known,
        "players_current_by_target": matched_players,
        "targets_with_players_detected": detected_targets,
        "targets_with_query_warning": warning_targets,
        "unknown_player_count_targets": sorted(set(unknown_targets + warning_targets)),
        "unknown_player_context": unknown_player_context,
        "players_present": players_present,
        "no_users_detected": no_users_detected,
        "no_users_confirmed": no_users_detected,
        "query_warning_present": bool(warning_targets),
        "player_presence_detected_authorizes_followup": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "no_users_detected_counts_as_approved_runtime_evidence": False,
        "no_users_detected_counts_as_readiness": False,
        "no_users_detected_counts_as_progress": False,
        "no_users_detected_counts_as_authorization": False,
        "no_users_detected_counts_as_notice_sent": False,
        "non_authorization": NO_USERS_PASSIVE_WAIT_NON_AUTHORIZATION,
    }


def matching_target_list(summary: dict[str, Any], plan: dict[str, Any], *keys: str) -> list[str]:
    matched: list[str] = []
    for key in keys:
        for value in as_string_list(summary.get(key)):
            if target_key_matches_plan(value, plan) and value not in matched:
                matched.append(value)
    return matched


def matching_truthy_target_map(summary: dict[str, Any], plan: dict[str, Any], *keys: str) -> list[str]:
    matched: list[str] = []
    truthy_strings = {"1", "true", "yes", "enabled", "observer_enabled"}
    for key in keys:
        values = summary.get(key)
        if not isinstance(values, dict):
            continue
        for target_key, value in values.items():
            if not isinstance(target_key, str) or not target_key_matches_plan(target_key, plan):
                continue
            truthy = (
                value is True
                or (isinstance(value, int) and not isinstance(value, bool) and value > 0)
                or (isinstance(value, str) and normalized_post_window_key(value) in truthy_strings)
            )
            if truthy and target_key not in matched:
                matched.append(target_key)
    return matched


def observer_enabled_targets_for_plan(summary: dict[str, Any], plan: dict[str, Any]) -> list[str]:
    targets = matching_target_list(
        summary,
        plan,
        "observer_enabled_targets",
        "lifecycle_observer_enabled_targets",
        "player_principal_lifecycle_observer_enabled_targets",
        "targets_with_observer_enabled",
    )
    for target_key in matching_truthy_target_map(
        summary,
        plan,
        "observer_enabled_by_target",
        "lifecycle_observer_enabled_by_target",
        "player_principal_lifecycle_observer_enabled_by_target",
    ):
        if target_key not in targets:
            targets.append(target_key)
    return targets


def diagnostic_mismatch_targets_for_plan(summary: dict[str, Any], plan: dict[str, Any]) -> list[str]:
    return matching_target_list(
        summary,
        plan,
        "diagnostic_mismatch_targets",
        "diagnostic_only_mismatch_targets",
        "targets_with_diagnostic_mismatch",
        "lifecycle_diagnostic_mismatch_targets",
        "player_principal_lifecycle_diagnostic_mismatch_targets",
    )


def accepted_lifecycle_roles_for_plan(
    summary: dict[str, Any],
    plan: dict[str, Any],
    target_triplets: list[dict[str, Any]],
) -> list[str]:
    roles_seen: set[str] = set()
    for item in target_triplets:
        roles_seen.update(
            as_string_list(
                item.get("roles_seen"),
                allowed=REQUIRED_LIFECYCLE_EVENT_ROLES,
            )
        )
    for key in (
        "accepted_lifecycle_roles_by_target",
        "accepted_observer_roles_by_target",
        "accepted_lifecycle_event_roles_by_target",
        "lifecycle_roles_seen_by_target",
        "roles_seen_by_target",
    ):
        values = summary.get(key)
        if not isinstance(values, dict):
            continue
        for target_key, roles in values.items():
            if isinstance(target_key, str) and target_key_matches_plan(target_key, plan):
                roles_seen.update(as_string_list(roles, allowed=REQUIRED_LIFECYCLE_EVENT_ROLES))
    return [role for role in REQUIRED_LIFECYCLE_EVENT_ROLES if role in roles_seen]


def accepted_lifecycle_event_count_for_plan(
    summary: dict[str, Any],
    plan: dict[str, Any],
) -> tuple[int | None, bool]:
    matched_counts: list[int] = []
    for key in (
        "accepted_lifecycle_event_counts_by_target",
        "accepted_lifecycle_events_by_target",
        "accepted_observer_event_counts_by_target",
        "accepted_player_principal_lifecycle_event_counts_by_target",
    ):
        values = summary.get(key)
        if not isinstance(values, dict):
            continue
        for target_key, value in values.items():
            if not isinstance(target_key, str) or not target_key_matches_plan(target_key, plan):
                continue
            if isinstance(value, int) and not isinstance(value, bool):
                matched_counts.append(max(value, 0))
    if not matched_counts:
        return None, False
    return sum(matched_counts), True


def active_player_no_accepted_events_policy(
    *,
    plan: dict[str, Any],
    summary: dict[str, Any],
    presence: dict[str, Any],
    target_triplets: list[dict[str, Any]],
) -> dict[str, Any]:
    observer_enabled_targets = observer_enabled_targets_for_plan(summary, plan)
    diagnostic_mismatch_targets = diagnostic_mismatch_targets_for_plan(summary, plan)
    accepted_roles = accepted_lifecycle_roles_for_plan(summary, plan, target_triplets)
    accepted_count, accepted_count_known = accepted_lifecycle_event_count_for_plan(summary, plan)
    no_accepted_events = not accepted_roles and (
        accepted_count == 0 or accepted_count is None
    )
    state_detected = (
        presence.get("players_present") is True
        and bool(observer_enabled_targets)
        and no_accepted_events
    )
    status = (
        "player_present_observer_enabled_no_accepted_events_likely_drift"
        if state_detected
        else "state_not_detected"
    )
    return {
        "schema": ACTIVE_PLAYER_NO_ACCEPTED_EVENTS_SCHEMA,
        "status": status,
        "classification": "likely_drift_non_evidence" if state_detected else "passive_context_non_evidence",
        "target": plan["target"],
        "passive_player_presence": presence,
        "state_detected": state_detected,
        "player_present": presence.get("players_present") is True,
        "observer_enabled_on_exact_target": bool(observer_enabled_targets),
        "observer_enabled_targets": observer_enabled_targets,
        "diagnostic_mismatch_targets": diagnostic_mismatch_targets,
        "diagnostic_only_mismatch_lines_present": bool(diagnostic_mismatch_targets),
        "accepted_lifecycle_event_roles": accepted_roles,
        "accepted_lifecycle_event_count": accepted_count,
        "accepted_lifecycle_event_count_known": accepted_count_known,
        "no_accepted_lifecycle_events": no_accepted_events,
        "likely_drift": state_detected,
        "exact_state_preconditions": [
            "exact_target_matches_passive_summary",
            "player_count_on_exact_target_greater_than_zero",
            "player_principal_lifecycle_observer_enabled_on_exact_target",
            "accepted_lifecycle_event_count_on_exact_target_equals_zero_or_absent",
            "no_accepted_session_start_session_start_rejected_or_session_end_for_target",
        ],
        "next_blocker": (
            "active_player_no_accepted_events_likely_drift_defer_until_fix"
            if state_detected
            else None
        ),
        "restart_recommended": False,
        "start_or_restart_recommended": False,
        "restart_requires_concrete_deploy_or_gate_change": True,
        "restart_without_concrete_deploy_or_gate_change_recommended": False,
        "process_control": (
            "defer_until_drift_fix_without_restart" if state_detected else "none"
        ),
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
        "defer_until_drift_fix_when_no_accepted_events": state_detected,
        "standing_authority_metadata_only": True,
        "standing_authority_authorizes_server_restart": False,
        "standing_authority_authorizes_marker_env_changes": False,
        "standing_authority_authorizes_runtime_evidence": False,
        "two_server_cap_policy": two_server_cap_policy(),
        "server_operations_authorized": False,
        "runtime_capture_authorized": False,
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
            "active-player/no-accepted-events state is passive diagnostic drift metadata only; "
            "it does not authorize Discord, server operations, marker/env changes, restarts, "
            "live log reads, runtime capture, approved runtime evidence, readiness, progress, "
            "or publication"
        ),
    }


def passive_monitor_command(plan: dict[str, Any]) -> str:
    return shell_command(
        [
            "scripts/monitor_ark_player_presence_passive.sh",
            "--once",
            "--no-details",
            target_key_prefix(plan),
        ]
    )


def closure_compatible_evidence_root(plan: dict[str, Any]) -> dict[str, Any]:
    run_id = str(plan.get("run_id") or "")
    evidence_dir = str(plan.get("evidence_dir") or "")
    target = plan.get("target") if isinstance(plan.get("target"), dict) else {}
    closure_argv = [
        "scripts/prepare_player_principal_lifecycle_evidence_closure_request.py",
        "--evidence-dir",
        evidence_dir,
        "--format",
        "json",
    ]
    if target.get("instance"):
        closure_argv.extend(["--instance", str(target["instance"])])
    if target.get("map"):
        closure_argv.extend(["--map", str(target["map"])])
    return {
        "schema": "obelisk.player-principal-lifecycle-closure-compatible-evidence-root.v1",
        "run_id": run_id,
        "evidence_dir": evidence_dir,
        "required_run_id_pattern": CLOSURE_COMPATIBLE_RUN_ID_PATTERN,
        "run_id_matches_closure_request": re.fullmatch(CLOSURE_COMPATIBLE_RUN_ID_PATTERN, run_id)
        is not None,
        "passive_monitor_root_accepted_by_closure_request": False,
        "passive_monitor_roots_must_not_be_used_as_closure_evidence_dir": True,
        "copy_required_before_evidence_closure": True,
        "copy_target_evidence_dir": evidence_dir,
        "closure_request_command_after_staging_not_executed": shell_command(closure_argv),
        "server_operations_authorized": False,
        "runtime_capture_authorized": False,
        "workspace_writes_authorized": False,
        "copy_or_stage_action_authorized_by_this_report": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "non_authorization": (
            "closure root guidance only; passive monitor roots are diagnostic context and "
            "must be copied or replaced by a closure-compatible lifecycle evidence root"
        ),
    }


def diagnostic_candidate_next_window_policy(
    *,
    requested: bool,
    plan: dict[str, Any],
    request: dict[str, Any] | None = None,
    recommend_enable: bool = False,
) -> dict[str, Any]:
    policy = diagnostic_candidates_policy(requested=requested, plan=plan, request=request)
    policy["recommended_for_next_player_backed_window"] = recommend_enable
    policy["should_enable_in_next_request_pack"] = recommend_enable
    policy["next_request_pack_flag"] = "--diagnostic-candidates" if recommend_enable else None
    return policy


def diagnostic_candidates_for_approved_evidence_policy(
    request: dict[str, Any] | None,
    *,
    observer_env_path: Path | str | None = None,
    observer_env_diagnostic_keys_present_value: list[str] | None = None,
) -> dict[str, Any]:
    request_present = isinstance(request, dict)
    request_value = request.get("diagnostic_candidates_enabled") if request_present else None
    request_explicitly_disabled = request_present and request_value is False
    request_enabled = request_present and request_value is True
    diagnostic_keys_present = (
        observer_env_diagnostic_keys_present_value
        if observer_env_diagnostic_keys_present_value is not None
        else observer_env_diagnostic_keys_present(observer_env_path)
    )
    diagnostic_keys = sorted(diagnostic_keys_present or [])
    blockers: list[str] = []
    if request_enabled:
        blockers.append(DIAGNOSTIC_CANDIDATES_APPROVED_EVIDENCE_BLOCKER)
    elif request_present and not request_explicitly_disabled:
        blockers.append(DIAGNOSTIC_CANDIDATES_NOT_EXPLICITLY_DISABLED_BLOCKER)
    if DIAGNOSTIC_CANDIDATES_ENV_KEY in diagnostic_keys:
        blockers.append(OBSERVER_ENV_DIAGNOSTIC_CANDIDATES_BLOCKER)
    if diagnostic_keys:
        blockers.append(OBSERVER_ENV_DIAGNOSTIC_KEYS_BLOCKER)
    return {
        "schema": DIAGNOSTIC_CANDIDATES_APPROVED_EVIDENCE_POLICY_SCHEMA,
        "diagnostic_env_key": DIAGNOSTIC_CANDIDATES_ENV_KEY,
        "diagnostic_env_keys": list(DIAGNOSTIC_APPROVED_EVIDENCE_ENV_KEYS),
        "request_field": "diagnostic_candidates_enabled",
        "request_pack_present": request_present,
        "request_explicitly_disabled": request_explicitly_disabled,
        "request_enabled": request_enabled,
        "observer_env_path": str(observer_env_path) if observer_env_path is not None else None,
        "observer_env_contains_diagnostic_candidates": (
            DIAGNOSTIC_CANDIDATES_ENV_KEY in diagnostic_keys
        ),
        "observer_env_diagnostic_keys_present": diagnostic_keys,
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


def player_warning_broadcast_recommendation(
    *,
    plan: dict[str, Any],
    request: dict[str, Any] | None = None,
    restart_expectation: str | None = None,
) -> dict[str, Any]:
    request = request if isinstance(request, dict) else {}
    safety = request.get("player_presence_safety")
    if not isinstance(safety, dict):
        safety = {}
    restart_expectation = restart_expectation or request.get("restart_expectation") or plan.get(
        "restart_expectation"
    )
    restart_requested = restart_expectation == "restart"
    broadcast_required = bool(
        safety.get("rcon_broadcast_required_if_players_connected", restart_requested)
    )
    reschedule_required = bool(
        safety.get(
            "restart_must_be_cancelled_or_rescheduled_if_players_remain_connected",
            restart_requested,
        )
    )
    return {
        "schema": PLAYER_WARNING_BROADCAST_SCHEMA,
        "target": plan["target"],
        "restart_expectation": restart_expectation,
        "recommended_notice_text": recommended_notice_text(
            target=plan["target"],
            approved_window=plan.get("approved_window"),
        ),
        "recommended_rcon_broadcast_text_redacted": recommended_notice_text(
            target=plan["target"],
            approved_window=plan.get("approved_window"),
        )["recommended_rcon_broadcast_text_redacted"],
        "recommended_discord_text_redacted": recommended_notice_text(
            target=plan["target"],
            approved_window=plan.get("approved_window"),
        )["recommended_discord_text_redacted"],
        "recommended_text_already_redacted": True,
        "raw_player_text_allowed": False,
        "raw_player_identity_allowed": False,
        "secret_or_webhook_output_allowed": False,
        "two_server_cap_policy": two_server_cap_policy(),
        "connected_player_check_command_not_executed": passive_monitor_command(plan),
        "connected_player_check_required_before_restart": bool(
            safety.get("connected_player_check_required_before_restart", restart_requested)
        ),
        "broadcast_recommended_if_players_connected": broadcast_required,
        "rcon_broadcast_required_if_players_connected": broadcast_required,
        "cancel_or_reschedule_if_players_remain_connected": reschedule_required,
        "restart_must_be_cancelled_or_rescheduled_if_players_remain_connected": reschedule_required,
        "no_users_result_recommendation": "passive_wait_without_restart",
        "request_pack_authorizes_player_check_or_broadcast": False,
        "broadcast_performed_by_executor": False,
        "player_presence_check_performed_by_executor": False,
        "server_operations_authorized": False,
        "standing_authority_authorizes_server_restart": False,
        "standing_authority_authorizes_discord_send": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "non_authorization": NO_USERS_PASSIVE_WAIT_NON_AUTHORIZATION,
    }


def diagnostic_candidates_policy(
    *,
    requested: bool,
    plan: dict[str, Any],
    request: dict[str, Any] | None = None,
    observer_env_path: Path | str | None = None,
) -> dict[str, Any]:
    request_payload = request if isinstance(request, dict) else None
    request = request_payload or {}
    enabled = request.get("diagnostic_candidates_enabled") is True
    feature_gates = nested_dict(request, "operator_live_ops_brief", "feature_gates")
    approved_evidence_policy = diagnostic_candidates_for_approved_evidence_policy(
        request_payload,
        observer_env_path=observer_env_path,
    )
    return {
        "requested_by_executor": requested,
        "enabled_in_request_pack": enabled,
        "mode": "candidate_only_non_evidence" if enabled else "disabled",
        "bounded": True,
        "bounds": {
            "approved_window_duration_seconds": nested_dict(plan, "approved_window").get(
                "duration_seconds"
            ),
            "max_duration_seconds": nested_dict(plan, "approved_window").get(
                "duration_seconds"
            ),
            "dispatch_limit": feature_gates.get("dispatch_limit", 0),
            "log_limit": feature_gates.get("log_limit", 10),
        },
        "raw_player_text_allowed": False,
        "raw_player_identity_allowed": False,
        "raw_player_text_or_identity_allowed": False,
        "approved_evidence_policy": approved_evidence_policy,
        "approved_evidence_window_rejected": approved_evidence_policy[
            "approved_evidence_window_rejected"
        ],
        "approved_evidence_blockers": approved_evidence_policy["approved_evidence_blockers"],
        "diagnostic_candidate_lines_promotable_for_approved_evidence": False,
        "source_log_contains_lifecycle_diagnostic_lines_blocks_approved_evidence": True,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "readiness_claim_allowed": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "stable_claim_allowed": False,
        "non_authorization": DIAGNOSTIC_CANDIDATES_NON_AUTHORIZATION,
    }


def beta_notice_confirmed_action(
    *,
    order: int,
    plan: dict[str, Any],
    output_paths: dict[str, Any],
) -> dict[str, Any]:
    standing = plan_has_standing_launch_authority(plan)
    followup = manual_followup_step(plan, "beta_notice_confirmed_send")
    redirect_stdout = output_paths["confirmed_notice_report_expected"]
    paths = {
        "expected_confirmed_notice_report": output_paths["confirmed_notice_report_expected"],
        "expected_confirmed_notice_sidecar": output_paths["confirmed_notice_sidecar_expected"],
        "dry_run_report": output_paths["dry_run_report"],
        "dry_run_notice_sidecar": output_paths["dry_run_notice_sidecar"],
    }
    argv = list(followup.get("argv") or [])
    if argv and "--artifact-json" not in argv:
        try:
            index = argv.index("--json")
        except ValueError:
            argv.extend(["--artifact-json", output_paths["confirmed_notice_sidecar_expected"]])
        else:
            argv = [
                *argv[:index],
                "--artifact-json",
                output_paths["confirmed_notice_sidecar_expected"],
                *argv[index:],
            ]
    action = {
        "order": order,
        "id": (
            "send_guarded_beta_notice_with_recorded_standing_authority"
            if standing
            else "produce_confirmed_notice_report_outside_executor"
        ),
        "owner": "lead",
        "status": "manual_external_not_executed_by_executor",
        "action": (
            "Review the dry-run report, then run the guarded beta notice send and write "
            "the confirmed notice report at the expected path using the recorded standing "
            "authority for this exact beta-notice scope. This executor still does not send "
            "Discord automatically."
            if standing
            else (
                "Use the lead-owned approved notice path outside this executor and write "
                "the confirmed notice report at the expected path after exact operator scope is present."
            )
        ),
        "argv": argv,
        "redirect_stdout": redirect_stdout,
        "paths": paths,
        "sidecar_required_for_confirmed_send_consumption": True,
        "stdout_only_confirmation_accepted": False,
        "blocked_until": [
            "beta_notice_dry_run_reviewed",
            "request_window_start_in_future",
            "confirmed_send_before_window_start",
        ],
        "required_before_activation": True,
        "must_be_real_notice_not_documentation": True,
        "confirmed_send_must_complete_before_window_start": True,
        "activation_or_restart_from_stale_request_allowed": False,
        "monitor_or_restart_activation_after_window_start_allowed": False,
        "authority_source": "recorded_standing_launch_authority" if standing else "fresh_current_turn_operator_scope",
        "separate_operator_authorization_required": not standing,
        "standing_authority_satisfies_guarded_beta_notice_send_scope": standing,
        "guarded_beta_notice_send_scope_satisfied_by_standing_authority": standing,
        "standing_authority_authorizes_discord_send": standing,
        "confirmed_send_requires_separate_explicit_discord_send_approval": not standing,
        "recommended_notice_text": recommended_notice_text(
            target=plan.get("target", {}),
            approved_window=plan.get("approved_window"),
        ),
        "two_server_cap_policy": two_server_cap_policy(),
        "discord_send_performed_by_executor": False,
        "non_authorization": (
            "this executor does not send Discord; the guarded helper must be invoked explicitly"
        ),
    }
    return action_with_runner(
        action,
        plan,
        phase="confirmed_beta_notice",
        operation_kind="guarded_beta_notice_send",
        side_effect_domain="discord_notice",
        inputs={"dry_run_report": output_paths["dry_run_report"]},
        outputs={"confirmed_notice_report": output_paths["confirmed_notice_report_expected"]},
        command=runner_command(argv, redirect_stdout=redirect_stdout),
        operation=runner_operation(
            "guarded_beta_notice_send",
            inputs=paths,
            outputs={
                "confirmed_notice_report": output_paths["confirmed_notice_report_expected"],
                "confirmed_notice_sidecar": output_paths["confirmed_notice_sidecar_expected"],
            },
            safety={
                "dry_run_review_required": True,
                "discord_send_performed_by_executor": False,
                "standing_authority_authorizes_discord_send": False,
                "confirmed_send_requires_separate_explicit_discord_send_approval": True,
                "sidecar_required_for_confirmed_send_consumption": True,
                "stdout_only_confirmation_accepted": False,
            },
        ),
    )


def consume_confirmed_notice_action(
    *,
    order: int,
    output_paths: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    standing = plan_has_standing_launch_authority(plan)
    paths = {
        "activation_preconditions_report": output_paths["activation_preconditions_report"],
        "confirmed_notice_report": output_paths["confirmed_notice_report_expected"],
        "confirmed_notice_sidecar": output_paths["confirmed_notice_sidecar_expected"],
    }
    argv = [
        "python3",
        "scripts/check_player_principal_lifecycle_activation_preconditions.py",
        "--request-json",
        output_paths["request_pack"]["window_request"],
        "--request-check-json",
        output_paths["request_check_report"],
        "--notice-report-json",
        output_paths["confirmed_notice_report_expected"],
        "--route-gate-json",
        output_paths["route_gate_report"],
        "--json",
    ]
    action = {
        "order": order,
        "id": "consume_confirmed_notice_offline",
        "owner": "lead",
        "status": "manual_external_not_executed_by_executor",
        "action": (
            "Rerun this executor with --confirmed-notice-report-json pointing at the "
            "confirmed notice report to write the offline activation-preconditions report."
        ),
        "argv": argv,
        "redirect_stdout": output_paths["activation_preconditions_report"],
        "paths": paths,
        "blocked_until": [
            "confirmed_beta_notice_report_exists",
            "confirmed_notice_sidecar_exists",
            "request_window_start_in_future",
        ],
        "required_before_activation": True,
        "confirmed_beta_notice_required_before_activation": True,
        "activation_or_restart_from_stale_request_allowed": False,
        "monitor_or_restart_activation_after_window_start_allowed": False,
        "authority_source": "recorded_standing_launch_authority" if standing else "fresh_current_turn_operator_scope",
        "separate_operator_authorization_required": False,
        "standing_authority_prepares_offline_report_only": standing,
        "non_authorization": (
            "activation precondition checking consumes reports only; it does not touch servers"
        ),
    }
    return action_with_runner(
        action,
        plan,
        phase="activation_preconditions",
        operation_kind="consume_confirmed_notice_offline",
        side_effect_domain="offline_report_write",
        inputs={
            "request_json": output_paths["request_pack"]["window_request"],
            "request_check_report": output_paths["request_check_report"],
            "confirmed_notice_report": output_paths["confirmed_notice_report_expected"],
            "confirmed_notice_sidecar": output_paths["confirmed_notice_sidecar_expected"],
            "route_gate_report": output_paths["route_gate_report"],
        },
        outputs={"activation_preconditions_report": output_paths["activation_preconditions_report"]},
        command=runner_command(
            argv,
            redirect_stdout=output_paths["activation_preconditions_report"],
            env={"PYTHONDONTWRITEBYTECODE": "1"},
        ),
        operation=runner_operation(
            "consume_confirmed_notice_offline",
            inputs=paths,
            outputs={"activation_preconditions_report": output_paths["activation_preconditions_report"]},
        ),
    )


def safe_restart_warn_action(
    *,
    order: int,
    plan: dict[str, Any],
    request: dict[str, Any],
) -> dict[str, Any]:
    standing = plan_has_standing_launch_authority(plan)
    safety = request.get("player_presence_safety")
    if not isinstance(safety, dict):
        safety = {}
    restart_expectation = request.get("restart_expectation", plan.get("restart_expectation"))
    restart_requested = restart_expectation == "restart"
    warning_broadcast = player_warning_broadcast_recommendation(
        plan=plan,
        request=request,
        restart_expectation=restart_expectation,
    )
    action = {
        "order": order,
        "id": "safe_restart_warn_or_reschedule",
        "owner": "lead",
        "status": "manual_external_not_executed_by_executor",
        "action": (
            "Before restart, check connected players on the exact target, warn through the "
            "approved player-safe path if players are connected, and cancel or reschedule "
            "if players remain connected."
            if restart_requested
            else "No restart warning is required by this request; preserve stable posture checks."
        ),
        "target": plan["target"],
        "restart_expectation": restart_expectation,
        "player_presence_safety": safety,
        "player_warning_broadcast_recommendation": warning_broadcast,
        "blocked_until": [
            "beta_notice_dry_run_reviewed",
            "confirmed_beta_notice_report_consumed",
            "activation_preconditions_ready",
            "request_window_start_in_future",
        ],
        "required_before_activation": True,
        "beta_notice_dry_run_required_before_activation": True,
        "confirmed_beta_notice_required_before_activation": True,
        "activation_preconditions_required_before_activation_or_restart": True,
        "activation_or_restart_from_stale_request_allowed": False,
        "monitor_or_restart_activation_after_window_start_allowed": False,
        "authority_source": "recorded_standing_launch_authority" if standing else "fresh_current_turn_operator_scope",
        "separate_operator_authorization_required": True,
        "standing_authority_authorizes_server_restart": False,
        "standing_authority_authorizes_discord_send": False,
        "two_server_cap_policy": two_server_cap_policy(),
        "request_pack_authorizes_player_check_or_broadcast": False,
        "server_operations_performed_by_executor": False,
        "non_authorization": NON_AUTHORIZATION,
    }
    return action_with_runner(
        action,
        plan,
        phase="runtime_window",
        operation_kind="safe_restart_warn_or_reschedule",
        side_effect_domain="player_presence_restart_safety",
        inputs={
            "target": plan["target"],
            "restart_expectation": restart_expectation,
            "player_presence_safety": safety,
            "player_warning_broadcast_recommendation": warning_broadcast,
        },
        operation=runner_operation(
            "safe_restart_warn_or_reschedule",
            inputs={
                "target": plan["target"],
                "restart_expectation": restart_expectation,
                "player_presence_safety": safety,
                "player_warning_broadcast_recommendation": warning_broadcast,
            },
            safety={
                "connected_player_check_required_before_restart": bool(
                    safety.get("connected_player_check_required_before_restart")
                ),
                "request_pack_authorizes_player_check_or_broadcast": False,
                "server_operations_performed_by_executor": False,
                "standing_authority_authorizes_server_restart": False,
                "player_warning_broadcast_recommendation": warning_broadcast,
            },
        ),
    )


def active_observation_action(
    *,
    order: int,
    plan: dict[str, Any],
    request: dict[str, Any],
) -> dict[str, Any]:
    standing = plan_has_standing_launch_authority(plan)
    named_scope = nested_dict(request, "current_turn_approval_scope", "required_named_scope")
    marker_env_gates = nested_dict(named_scope, "marker_env_gates")
    diagnostic_candidates = diagnostic_candidates_policy(
        requested=request.get("diagnostic_candidates_enabled") is True,
        plan=plan,
        request=request,
        observer_env_path=plan.get("artifacts", {}).get("observer_env"),
    )
    action = {
        "order": order,
        "id": "active_observation_window",
        "owner": "lead",
        "status": "manual_external_not_executed_by_executor",
        "action": (
            "Use the exact observer marker/env scope for the approved window, keep plugins "
            "disabled, dispatch limit 0, log limit 10, and perform only the named "
            "player_principal_lifecycle observation."
        ),
        "target": plan["target"],
        "approved_window": plan["approved_window"],
        "marker_env_gates": marker_env_gates,
        "forbidden_markers": request.get("forbidden_markers"),
        "diagnostic_candidates": diagnostic_candidates,
        "blocked_until": [
            "beta_notice_dry_run_reviewed",
            "confirmed_beta_notice_report_consumed",
            "activation_preconditions_ready",
            "request_window_start_in_future",
        ],
        "required_before_activation": True,
        "beta_notice_dry_run_required_before_activation": True,
        "confirmed_beta_notice_required_before_activation": True,
        "activation_preconditions_required_before_activation_or_restart": True,
        "activation_or_restart_from_stale_request_allowed": False,
        "monitor_or_restart_activation_after_window_start_allowed": False,
        "authority_source": "recorded_standing_launch_authority" if standing else "fresh_current_turn_operator_scope",
        "separate_operator_authorization_required": True,
        "standing_authority_authorizes_marker_env_changes": False,
        "standing_authority_authorizes_runtime_evidence": False,
        "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
        "two_server_cap_policy": two_server_cap_policy(),
        "marker_env_changes_performed_by_executor": False,
        "runtime_capture_performed_by_executor": False,
        "non_authorization": NON_AUTHORIZATION,
    }
    return action_with_runner(
        action,
        plan,
        phase="runtime_window",
        operation_kind="active_observation_window",
        side_effect_domain="marker_env_runtime_observation",
        inputs={
            "target": plan["target"],
            "approved_window": plan["approved_window"],
            "marker_env_gates": marker_env_gates,
            "forbidden_markers": request.get("forbidden_markers"),
            "diagnostic_candidates": diagnostic_candidates,
        },
        operation=runner_operation(
            "active_observation_window",
            inputs={
                "target": plan["target"],
                "approved_window": plan["approved_window"],
                "marker_env_gates": marker_env_gates,
                "forbidden_markers": request.get("forbidden_markers"),
                "diagnostic_candidates": diagnostic_candidates,
            },
            safety={
                "plugins_disabled_required": True,
                "dispatch_limit_required": "0",
                "log_limit_required": "10",
                "diagnostic_candidates": diagnostic_candidates,
                "marker_env_changes_performed_by_executor": False,
                "runtime_capture_performed_by_executor": False,
                "standing_authority_authorizes_marker_env_changes": False,
                "standing_authority_authorizes_runtime_evidence": False,
            },
        ),
    )


def runtime_evidence_command_sequence(
    *,
    plan: dict[str, Any],
    request: dict[str, Any] | None = None,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    request_payload = request if isinstance(request, dict) else {}
    evidence_dir = Path(str(plan.get("evidence_dir") or ""))
    approved_bundle_dir = evidence_dir / "approved-bundle"
    copied_log = evidence_dir / "Obelisk.log"
    summary_path = approved_bundle_dir / "runtime-observer-summary.json"
    window_manifest = evidence_dir / "window-manifest.env"
    window_manifest_check = approved_bundle_dir / "player-principal-lifecycle-window-manifest.check.json"
    approved_manifest = evidence_dir / APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH
    bundle_command = [
        APPROVED_RUNTIME_EVIDENCE_BUNDLE_BUILDER,
        "--evidence-dir",
        str(evidence_dir),
    ]
    sequence_blockers = list(blockers or [])
    route_contract = copied_log_route_contract()
    step_non_claims = {
        "authorized_by_this_report": False,
        "server_operations_authorized": False,
        "runtime_capture_authorized": False,
        "live_log_reads_authorized": False,
        "marker_env_changes_authorized": False,
        "discord_authorized": False,
        "restart_recommended": False,
        "raw_player_text_allowed": False,
        "raw_player_identity_allowed": False,
        "raw_player_text_or_identity_allowed": False,
        "approved_evidence_bundle_checker_accepted": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "clears_approved_runtime_evidence_missing": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
    }
    return {
        "schema": EVIDENCE_COMMAND_SEQUENCE_SCHEMA,
        "status": "not_executed",
        "ordered_step_ids": list(COPIED_LOG_ROUTE_STEP_IDS),
        "copied_log_route": route_contract,
        "ordered_copied_log_route_step_ids": list(COPIED_LOG_ROUTE_STEP_IDS),
        "checker_acceptance_required_before_evidence_state_change": True,
        "all_prior_outputs_non_authorizing_and_non_evidence": True,
        "commands": [
            {
                "order": 1,
                "id": "build_approved_runtime_evidence_bundle_from_evidence_dir",
                "kind": "one_shot_bundle_builder",
                "command_text_not_executed": shell_command(bundle_command),
                "evidence_dir": str(evidence_dir),
                "copied_log": str(copied_log),
                "window_manifest": str(window_manifest),
                "approved_bundle_dir": str(approved_bundle_dir),
                "internal_analyzer": RUNTIME_OBSERVER_ANALYZER,
                "internal_manifest_builder": APPROVED_RUNTIME_MANIFEST_BUILDER,
                "internal_checker": APPROVED_RUNTIME_EVIDENCE_CHECKER,
                "stdout_report_path": str(approved_bundle_dir / "evidence-bundle-report.json"),
                "source_summary_path": str(summary_path),
                "emits_summary_field": STRICT_LIFECYCLE_TRIPLET_CANDIDATE_SUMMARY_JSON_PATH,
                "candidate_ready_for_bundle_preflight_required": True,
                "requires_window_manifest_check": str(window_manifest_check),
                "required_triplet": "HandleNewPlayer(1,1) -> CheckJoinInProgress(1,0) -> matched OnLogout",
                "approved_manifest_output": str(approved_manifest),
                "manifest": str(approved_manifest),
                "checker_acceptance_can_change_evidence_state_when_executed": True,
                "accepted_by_this_report": False,
                **step_non_claims,
            },
        ],
        "artifacts": {
            "copied_log": str(copied_log),
            "runtime_observer_summary": str(summary_path),
            "strict_lifecycle_triplet_candidate_summary_json_path": (
                STRICT_LIFECYCLE_TRIPLET_CANDIDATE_SUMMARY_JSON_PATH
            ),
            "window_manifest": str(window_manifest),
            "window_manifest_check": str(window_manifest_check),
            "approved_runtime_manifest": str(approved_manifest),
        },
        "available_after_required_sibling_set": not sequence_blockers,
        "blockers": sequence_blockers,
        "restart_policy": "no_restart_unless_concrete_deploy_or_gate_change_requires_it",
        "restart_recommended": False,
        "start_or_restart_recommended": False,
        "raw_player_text_allowed": False,
        "raw_player_identity_allowed": False,
        "raw_player_text_or_identity_allowed": False,
        "authorization": {
            "authorized_by_this_report": False,
            "server_operations_authorized": False,
            "runtime_capture_authorized": False,
            "marker_env_changes_authorized": False,
            "discord_authorized": False,
            "discord_sent_by_this_report": False,
        },
        "evidence": {
            "approved_runtime_evidence": False,
            "approved_runtime_evidence_ready": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_evidence": False,
            "counts_toward_sdk": False,
            "counts_toward_p0_dependency_chain": False,
        },
        "non_authorization": (
            "ordered commands are offline follow-up guidance only; this report does not "
            "authorize server operations, restarts, live-log reads, Discord sends, marker/env "
            "changes, evidence acceptance, SDK progress, or readiness claims; the one-shot "
            "bundle builder output remains non-evidence unless its approved-evidence checker "
            "accepts the copied sibling-set bundle"
        ),
    }


def sibling_sidecar_action(
    *,
    order: int,
    plan: dict[str, Any],
    request: dict[str, Any],
    output_paths: dict[str, Any],
) -> dict[str, Any]:
    paths = required_evidence_paths(request, output_paths)
    fresh_retry = runtime_fresh_retry_after_closed_non_evidence_window(
        plan,
        output_paths=output_paths,
    )
    pipeline = runtime_evidence_command_sequence(plan=plan, request=request)
    expected_sibling_set = [
        "Obelisk.log",
        "window-request.json",
        "observer-window.env",
        "operator-approval-request.md",
        "operator-approval-receipt.json",
        "preflight-pre.json",
        "preflight-post.json",
        "window-manifest.env",
        APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
    ]
    post_window_contract = {
        "schema": POST_WINDOW_ACTION_CONTRACT_SCHEMA,
        "run_id": plan.get("run_id"),
        "target": plan.get("target"),
        "fresh_retry_after_closed_non_evidence_window": fresh_retry,
        "artifact": "post_window_sibling_set",
        "operation": "capture_sidecars_copy_log_build_bundle_and_run_checker",
        "required_evidence_paths": paths,
        "expected_sibling_set": expected_sibling_set,
        "required_sidecars": [item for item in expected_sibling_set if item != "Obelisk.log"],
        "copied_log_relative_path": "Obelisk.log",
        "approved_runtime_manifest_relative_path": APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
        "dry_run_first_required": True,
        "dry_run_must_complete_before_execute": True,
        "dry_run_report_path": output_paths["post_window_next_actions_dry_run_report"],
        "required_dry_run_artifacts": [
            output_paths["post_window_next_actions_dry_run_report"],
        ],
        "runner_execute_requires_existing_dry_run_report": True,
        "sidecar_generation_required": True,
        "sidecar_generation_authorized_by_this_report": False,
        "sidecar_generation_counts_as_approved_runtime_evidence": False,
        "copied_log_copy_authorized_by_this_report": False,
        "dry_run_report_authorizes_runtime": False,
        "dry_run_report_counts_as_approved_runtime_evidence": False,
        "standing_authority_authorizes_execution": False,
        "standing_authority_counts_as_approved_runtime_evidence": False,
        "copied_log_route_required": pipeline["copied_log_route"],
        "ordered_copied_log_route_step_ids": pipeline["ordered_step_ids"],
        "evidence_pipeline_command_sequence": pipeline,
        "ordered_runtime_evidence_commands": pipeline["commands"],
        "authorization": pipeline["authorization"],
        "evidence_boundary": pipeline["evidence"],
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "non_authorization": NON_AUTHORIZATION,
    }
    action = {
        "order": order,
        "id": "capture_required_sibling_sidecars",
        "owner": "lead",
        "status": "manual_external_not_executed_by_executor",
        "action": (
            "Preserve the checked sibling set beside the copied log: request pack, observer "
            "env, approval request, completed receipt, preflight-pre, preflight-post, "
            "window manifest, and copied Obelisk.log; then run the one-shot approved "
            "runtime evidence bundle builder with --evidence-dir."
        ),
        "required_evidence_paths": paths,
        "fresh_retry_after_closed_non_evidence_window": fresh_retry,
        "post_window_action_contract": post_window_contract,
        "post_window_copy_bundle_preconditions": post_window_contract,
        "copied_log_route_required": pipeline["copied_log_route"],
        "ordered_copied_log_route_step_ids": pipeline["ordered_step_ids"],
        "dry_run_first_required": True,
        "dry_run_must_complete_before_execute": True,
        "dry_run_report_path": post_window_contract["dry_run_report_path"],
        "required_dry_run_artifacts": list(post_window_contract["required_dry_run_artifacts"]),
        "dry_run_report_authorizes_runtime": False,
        "dry_run_report_counts_as_approved_runtime_evidence": False,
        "sidecar_generation_required": True,
        "sidecar_generation_authorized_by_this_report": False,
        "sidecar_generation_counts_as_approved_runtime_evidence": False,
        "approved_runtime_manifest_relative_path": APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
        "evidence_pipeline_command_sequence": pipeline,
        "ordered_runtime_evidence_commands": pipeline["commands"],
        "authorization": pipeline["authorization"],
        "evidence_boundary": pipeline["evidence"],
        **runner_authority_fields(plan),
        "counts_as_approved_runtime_evidence": False,
        "runtime_capture_performed_by_executor": False,
        "non_authorization": (
            "sidecar paths are exact follow-up requirements; this executor does not copy live logs "
            "or build approved runtime evidence"
        ),
    }
    return action_with_runner(
        action,
        plan,
        phase="post_window_capture",
        operation_kind="capture_required_sibling_sidecars",
        side_effect_domain="copied_log_and_sidecar_capture",
        inputs={
            "required_evidence_paths": paths,
            "post_window_action_contract": post_window_contract,
            "evidence_pipeline_command_sequence": pipeline,
        },
        outputs={"approved_runtime_manifest_relative_path": APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH},
        operation=runner_operation(
            "capture_required_sibling_sidecars",
            inputs={
                "required_evidence_paths": paths,
                "post_window_action_contract": post_window_contract,
                "evidence_pipeline_command_sequence": pipeline,
            },
            outputs={"approved_runtime_manifest_relative_path": APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH},
            safety={
                "counts_as_approved_runtime_evidence": False,
                "runtime_capture_performed_by_executor": False,
                "dry_run_first_required": True,
                "sidecar_generation_authorized_by_this_report": False,
                "sidecar_generation_counts_as_approved_runtime_evidence": False,
                "restart_recommended": False,
                "raw_player_text_or_identity_allowed": False,
                "checker_acceptance_required_before_evidence_state_change": True,
            },
        ),
    )


def stable_rollback_action(
    *,
    order: int,
    plan: dict[str, Any],
    request: dict[str, Any],
) -> dict[str, Any]:
    brief = request.get("operator_live_ops_brief")
    if not isinstance(brief, dict):
        brief = {}
    post_run = brief.get("post_run_stable_posture")
    if not isinstance(post_run, dict):
        post_run = {}
    action = {
        "order": order,
        "id": "restore_stable_posture_and_verify",
        "owner": "lead",
        "status": "manual_external_not_executed_by_executor",
        "action": (
            "After the window, remove observer-only markers/env, preserve the stable "
            "process-event-hook and disable-plugins posture, and run stable-posture checks."
        ),
        "rollback": request.get("rollback"),
        "post_run_stable_posture": post_run,
        **runner_authority_fields(plan),
        "standing_authority_authorizes_marker_env_changes": False,
        "standing_authority_authorizes_server_restart": False,
        "two_server_cap_policy": two_server_cap_policy(),
        "server_operations_performed_by_executor": False,
        "non_authorization": NON_AUTHORIZATION,
    }
    return action_with_runner(
        action,
        plan,
        phase="stable_rollback",
        operation_kind="restore_stable_posture_and_verify",
        side_effect_domain="stable_marker_env_rollback",
        inputs={
            "rollback": request.get("rollback"),
            "post_run_stable_posture": post_run,
        },
        operation=runner_operation(
            "restore_stable_posture_and_verify",
            inputs={
                "rollback": request.get("rollback"),
                "post_run_stable_posture": post_run,
            },
            safety={
                "server_operations_performed_by_executor": False,
                "stable_posture_required": True,
            },
        ),
    )


def offline_next_blocker(
    *,
    activation_checked: bool,
    activation_ready: bool,
    standing_launch_authority_recorded: bool,
    activation_checker_blocker: str,
) -> str:
    if not activation_checked:
        return "approved_dry_run_checked_beta_testers_notice_sent"
    if activation_ready:
        if standing_launch_authority_recorded:
            return "offline_preconditions_consistent_external_action_scope_required"
        return "offline_preconditions_consistent_fresh_authority_scoped_operations_next"
    return activation_checker_blocker or "offline_activation_preconditions_blocked"


def next_action_sequence(
    *,
    status: str,
    output_paths: dict[str, Any],
    activation_checked: bool,
    activation_ready: bool,
    plan: dict[str, Any],
    request: dict[str, Any],
) -> list[dict[str, Any]]:
    request_pack = output_paths["request_pack"]
    standing = plan_has_standing_launch_authority(plan)
    review_paths = {
        "request_pack": request_pack,
        "request_check_report": output_paths["request_check_report"],
        "dry_run_report": output_paths["dry_run_report"],
        "route_gate_report": output_paths["route_gate_report"],
    }
    multi_surface_pack_paths = output_paths.get("multi_surface_beta_capture_pack")
    if isinstance(multi_surface_pack_paths, dict):
        review_paths["multi_surface_beta_capture_pack"] = multi_surface_pack_paths
    diagnostic_candidates = diagnostic_candidates_policy(
        requested=request.get("diagnostic_candidates_enabled") is True,
        plan=plan,
        request=request,
        observer_env_path=plan.get("artifacts", {}).get("observer_env"),
    )
    base_review = action_with_runner(
        {
        "order": 1,
        "id": "review_offline_outputs",
        "owner": "lead",
        "action": (
            "Review the request pack, request check, dry-run notice, and planning-only route gate."
        ),
        "paths": review_paths,
        "non_authorization": NON_AUTHORIZATION,
        },
        plan,
        phase="offline_preactivation",
        operation_kind="review_offline_outputs",
        side_effect_domain="none",
        inputs=review_paths,
        operation=runner_operation("review_offline_outputs", inputs=review_paths),
    )
    if status == "offline_preactivation_prepared_notice_send_pending":
        return [
            base_review,
            beta_notice_confirmed_action(order=2, plan=plan, output_paths=output_paths),
            consume_confirmed_notice_action(order=3, output_paths=output_paths, plan=plan),
            action_with_runner(
                {
                "order": 4,
                "id": "active_observation_waits_for_activation_preconditions",
                "owner": "lead",
                "status": "manual_external_not_executed_by_executor",
                "action": (
                    "After the confirmed notice is consumed and activation preconditions are satisfied, "
                    "use the exact active-observation, sidecar, and restart/warn steps from this report."
                ),
                "paths": {
                    "activation_preconditions_report": output_paths["activation_preconditions_report"],
                },
                "diagnostic_candidates": diagnostic_candidates,
                "blocked_until": [
                    "beta_notice_dry_run_reviewed",
                    "confirmed_beta_notice_report_consumed",
                    "activation_preconditions_ready",
                    "request_window_start_in_future",
                ],
                "required_before_activation": True,
                "beta_notice_dry_run_required_before_activation": True,
                "confirmed_beta_notice_required_before_activation": True,
                "activation_preconditions_required_before_activation_or_restart": True,
                "activation_or_restart_from_stale_request_allowed": False,
                "monitor_or_restart_activation_after_window_start_allowed": False,
                "authority_source": "recorded_standing_launch_authority" if standing else "fresh_current_turn_operator_scope",
                "separate_operator_authorization_required": True,
                "standing_authority_authorizes_marker_env_changes": False,
                "standing_authority_authorizes_runtime_evidence": False,
                "lifecycle_missing_role_objectives": lifecycle_role_objectives(),
                "two_server_cap_policy": two_server_cap_policy(),
                "non_authorization": NON_AUTHORIZATION,
                },
                plan,
                phase="runtime_window",
                operation_kind="active_observation_waits_for_activation_preconditions",
                side_effect_domain="none",
                inputs={
                    "activation_preconditions_report": output_paths["activation_preconditions_report"],
                    "diagnostic_candidates": diagnostic_candidates,
                },
                operation=runner_operation(
                    "active_observation_waits_for_activation_preconditions",
                    inputs={
                        "activation_preconditions_report": output_paths["activation_preconditions_report"],
                        "diagnostic_candidates": diagnostic_candidates,
                    },
                    safety={
                        "activation_preconditions_ready_required": True,
                        "diagnostic_candidates": diagnostic_candidates,
                        "standing_authority_authorizes_marker_env_changes": False,
                        "standing_authority_authorizes_runtime_evidence": False,
                    },
                ),
            ),
        ]
    if activation_checked and activation_ready:
        return [
            {
                **base_review,
                "paths": {
                    **base_review["paths"],
                    "activation_preconditions_report": output_paths["activation_preconditions_report"],
                },
                "runner_contract": {
                    **base_review["runner_contract"],
                    "inputs": {
                        **base_review["runner_contract"]["inputs"],
                        "activation_preconditions_report": output_paths["activation_preconditions_report"],
                    },
                },
                "runner_operation": {
                    **base_review["runner_operation"],
                    "inputs": {
                        **base_review["runner_operation"]["inputs"],
                        "activation_preconditions_report": output_paths["activation_preconditions_report"],
                    },
                },
            },
            safe_restart_warn_action(order=2, plan=plan, request=request),
            active_observation_action(order=3, plan=plan, request=request),
            sibling_sidecar_action(order=4, plan=plan, request=request, output_paths=output_paths),
            stable_rollback_action(order=5, plan=plan, request=request),
        ]
    return [
        {
            **base_review,
            "paths": {
                **base_review["paths"],
                "activation_preconditions_report": output_paths["activation_preconditions_report"],
            },
            "runner_contract": {
                **base_review["runner_contract"],
                "inputs": {
                    **base_review["runner_contract"]["inputs"],
                    "activation_preconditions_report": output_paths["activation_preconditions_report"],
                },
            },
            "runner_operation": {
                **base_review["runner_operation"],
                "inputs": {
                    **base_review["runner_operation"]["inputs"],
                    "activation_preconditions_report": output_paths["activation_preconditions_report"],
                },
            },
        },
        action_with_runner(
            {
            "order": 2,
            "id": "resolve_offline_activation_blockers",
            "owner": "lead",
            "action": (
                "Inspect the activation-preconditions report blockers and regenerate only the offline "
                "reports that failed binding or consistency checks."
            ),
            "paths": {
                "activation_preconditions_report": output_paths["activation_preconditions_report"],
                "confirmed_notice_report": output_paths["confirmed_notice_report_used"],
            },
            "non_authorization": NON_AUTHORIZATION,
            },
            plan,
            phase="activation_preconditions",
            operation_kind="resolve_offline_activation_blockers",
            side_effect_domain="none",
            inputs={
                "activation_preconditions_report": output_paths["activation_preconditions_report"],
                "confirmed_notice_report": output_paths["confirmed_notice_report_used"],
            },
            operation=runner_operation(
                "resolve_offline_activation_blockers",
                inputs={
                    "activation_preconditions_report": output_paths["activation_preconditions_report"],
                    "confirmed_notice_report": output_paths["confirmed_notice_report_used"],
                },
            ),
        ),
    ]


def post_window_next_action_sequence(post_window_state: dict[str, Any]) -> list[dict[str, Any]]:
    if post_window_state.get("checked") is not True:
        return []
    manual_step = post_window_state.get("manual_step")
    if not isinstance(manual_step, dict):
        manual_step = {}
    review_action = {
        "order": 1,
        "id": "review_post_window_state_input",
        "owner": "lead",
        "status": "manual_external_not_executed_by_executor",
        "action": (
            "Review the consumed post-window state as diagnostic-only output; do not treat "
            "the source report as runtime evidence or current-turn approval."
        ),
        "paths": {"post_window_state_source": post_window_state.get("source_path")},
        "copied_log_route_required": copied_log_route_contract(),
        "ordered_copied_log_route_step_ids": list(COPIED_LOG_ROUTE_STEP_IDS),
        "authorized_by_this_report": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "non_authorization": POST_WINDOW_STATE_NON_AUTHORIZATION,
    }
    passive_wait = post_window_state.get("no_users_passive_wait")
    next_window = post_window_state.get("next_player_backed_window")
    active_no_accepted = post_window_state.get("active_player_no_accepted_events_policy")
    if isinstance(active_no_accepted, dict) and active_no_accepted.get("state_detected") is True:
        return attach_prepared_action_boundaries([
            review_action,
            {
                "order": 2,
                "id": "defer_until_lifecycle_drift_fix_without_restart",
                "owner": "lead",
                "status": "manual_external_not_executed_by_executor",
                "action": "defer_until_lifecycle_drift_fix_without_restart",
                "action_kind": "active_player_no_accepted_events_drift",
                "target": post_window_state.get("target"),
                "active_player_no_accepted_events_policy": active_no_accepted,
                "process_control": "defer_until_drift_fix_without_restart",
                "blocked_until": [
                    "drift_fix_identified",
                    "concrete_deploy_or_gate_change_named_if_restart_is_needed",
                    "fresh_checked_request_pack_after_fix",
                ],
                "restart_recommended": False,
                "start_or_restart_recommended": False,
                "restart_requires_concrete_deploy_or_gate_change": True,
                "server_operations_authorized_by_this_report": False,
                "runtime_work_authorized_by_this_report": False,
                "runtime_capture_authorized": False,
                "standing_authority_metadata_only": True,
                "standing_authority_authorizes_server_restart": False,
                "standing_authority_authorizes_marker_env_changes": False,
                "standing_authority_authorizes_runtime_evidence": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_evidence": False,
                "counts_as_progress": False,
                "clears_approved_runtime_evidence_missing": False,
                "non_authorization": POST_WINDOW_STATE_NON_AUTHORIZATION,
            },
            {
                "order": 3,
                "id": "wait_or_prompt_only_after_exact_observer_preconditions",
                "owner": "lead",
                "status": "manual_external_not_executed_by_executor",
                "action": "wait_or_prompt_only_after_exact_observer_preconditions",
                "action_kind": "conditional_wait_or_player_prompt",
                "target": post_window_state.get("target"),
                "wait_preconditions": active_no_accepted.get("wait_preconditions"),
                "ask_reconnect_or_logout_preconditions": active_no_accepted.get(
                    "ask_reconnect_or_logout_preconditions"
                ),
                "ask_reconnect_or_logout_now": False,
                "wait_authorized_by_this_report": False,
                "blocked_until": [
                    "fresh_current_window_request",
                    "confirmed_notice_report_consumed",
                    "activation_preconditions_ready",
                    "accepted_session_start_or_exact_CheckJoinInProgress_1_0_seen_for_same_session",
                    "no_drift_blocker_pending",
                ],
                "restart_recommended": False,
                "start_or_restart_recommended": False,
                "server_operations_authorized_by_this_report": False,
                "runtime_work_authorized_by_this_report": False,
                "runtime_capture_authorized": False,
                "authorized_by_this_report": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_evidence": False,
                "counts_as_progress": False,
                "clears_approved_runtime_evidence_missing": False,
                "non_authorization": POST_WINDOW_STATE_NON_AUTHORIZATION,
            },
        ])
    if (
        isinstance(passive_wait, dict)
        and isinstance(next_window, dict)
        and passive_wait.get("no_users_detected") is True
    ):
        return attach_prepared_action_boundaries([
            review_action,
            {
                "order": 2,
                "id": "continue_no_users_passive_wait_for_player_backed_evidence",
                "owner": "lead",
                "status": "manual_external_not_executed_by_executor",
                "action": "continue_no_users_passive_wait_for_player_backed_evidence",
                "action_kind": "no_users_passive_wait",
                "target": post_window_state.get("target"),
                "no_users_passive_wait": passive_wait,
                "passive_player_presence": post_window_state.get("passive_player_presence"),
                "diagnostic_candidates": passive_wait.get("diagnostic_candidates"),
                "command_text_not_executed": passive_wait.get("monitor_command_not_executed"),
                "closure_compatible_evidence_root": passive_wait.get("closure_compatible_evidence_root"),
                "process_control": "passive_wait_without_restart",
                "passive_wait_preferred": True,
                "repeated_restart_for_no_users_forbidden": True,
                "restart_recommended": False,
                "start_or_restart_recommended": False,
                "blocked_until": ["organic_player_presence_detected"],
                "authorized_by_this_report": False,
                "server_operations_authorized_by_this_report": False,
                "runtime_work_authorized_by_this_report": False,
                "runtime_capture_authorized": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "non_authorization": NO_USERS_PASSIVE_WAIT_NON_AUTHORIZATION,
            },
            {
                "order": 3,
                "id": "prepare_next_player_backed_diagnostic_window_without_restart",
                "owner": "lead",
                "status": "manual_external_not_executed_by_executor",
                "action": "prepare_next_player_backed_diagnostic_window_without_restart",
                "action_kind": "offline_next_window_preparation",
                "target": post_window_state.get("target"),
                "next_player_backed_window": next_window,
                "diagnostic_candidates": next_window.get("diagnostic_candidates"),
                "command_text_not_executed": next_window.get("command_text_not_executed"),
                "closure_compatible_evidence_root": next_window.get("closure_compatible_evidence_root"),
                "restart_expectation": "none",
                "diagnostic_candidates_recommended": True,
                "should_enable_diagnostic_candidates_in_next_request_pack": True,
                "repeated_restart_for_no_users_forbidden": True,
                "start_or_restart_recommended": False,
                "writes_under_server_root": False,
                "writes_under_evidence_dir": False,
                "authorized_by_this_report": False,
                "server_operations_authorized_by_this_report": False,
                "runtime_work_authorized_by_this_report": False,
                "runtime_capture_authorized": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "non_authorization": NO_USERS_PASSIVE_WAIT_NON_AUTHORIZATION,
            },
        ])
    return attach_prepared_action_boundaries([
        review_action,
        {
            "order": 2,
            "id": "manual_post_window_followup",
            "owner": "lead",
            "action": manual_step.get("action"),
            "paths": {
                "approved_bundle_path": post_window_state.get("approved_bundle_path"),
                "source": post_window_state.get("source_path"),
            },
            "next_blocker": post_window_state.get("next_blocker"),
            "copied_log_route_required": manual_step.get(
                "copied_log_route_required",
                copied_log_route_contract(),
            ),
            "ordered_copied_log_route_step_ids": manual_step.get(
                "ordered_copied_log_route_step_ids",
                list(COPIED_LOG_ROUTE_STEP_IDS),
            ),
            "status": "manual_external_not_executed_by_executor",
            "authorized_by_this_report": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "non_authorization": POST_WINDOW_STATE_NON_AUTHORIZATION,
        },
    ])


def server_steps_remaining_for_state(post_window_state: dict[str, Any]) -> list[str]:
    active_no_accepted = post_window_state.get("active_player_no_accepted_events_policy")
    if isinstance(active_no_accepted, dict) and active_no_accepted.get("state_detected") is True:
        return [
            "preserve two-server cap",
            "defer until lifecycle drift fix or concrete deploy/gate change",
            "prepare fresh checked request pack after fix with restart expectation none unless the concrete change requires process control",
            "wait or ask reconnect/logout only after exact observer-gate preconditions",
            "approved runtime bundle build/check requiring session_start, exact CheckJoinInProgress(1,0) session_start_rejected, and session_end",
        ]
    return [
        "two-server posture decision",
        "player-safe warning/schedule before restart",
        "marker/env activation",
        "ARK start/restart inside approved window",
        "copied-log capture",
        "stable rollback/posture check",
        "approved runtime bundle build/check requiring session_start, exact CheckJoinInProgress(1,0) session_start_rejected, and session_end",
    ]


def build_state_only_report(
    *,
    args: argparse.Namespace,
    plan: dict[str, Any],
    post_window_state: dict[str, Any],
) -> dict[str, Any]:
    diagnostic_candidates = diagnostic_candidates_policy(
        requested=args.diagnostic_candidates,
        plan=plan,
        request=None,
    )
    post_window_actions = post_window_next_action_sequence(post_window_state)
    execution_boundaries = runtime_execution_boundaries(
        plan=plan,
        output_paths={},
        next_actions=post_window_actions,
        post_window_next_actions=[],
        post_window_state=post_window_state,
    )
    fresh_retry = runtime_fresh_retry_after_closed_non_evidence_window(plan)
    return {
        "schema": SCHEMA,
        "status": "post_window_state_consumed_non_evidence",
        "plan_schema": plan.get("schema"),
        "run_id": plan["run_id"],
        "target": plan["target"],
        "fresh_retry_after_closed_non_evidence_window": fresh_retry,
        "approved_window": plan["approved_window"],
        "evidence_dir": plan["evidence_dir"],
        "report_dir": None,
        "steps": [],
        "executed_step_ids": [],
        "preactivation_prepared": False,
        "runtime_window_prepared": False,
        "prepared_metadata_only": False,
        "preparation_status": "post_window_state_consumed_metadata_only",
        "request_pack_path": plan["artifacts"]["window_request"],
        "request_pack_paths": request_pack_paths(plan),
        "request_check_json": None,
        "beta_notice_dry_run_json": None,
        "notice_report_json_for_activation": None,
        "route_gate_json": None,
        "activation_preconditions_json": None,
        "activation_preconditions_checked": False,
        "activation_preconditions_ready": False,
        "activation_preconditions_offline_ready": False,
        "activation_preconditions_ready_claim_allowed": False,
        "activation_preconditions_progress_claim_allowed": False,
        "activation_preconditions_ready_scope": "not_checked_post_window_state_only",
        "diagnostic_candidates": diagnostic_candidates,
        "diagnostic_candidates_requested": args.diagnostic_candidates,
        "diagnostic_candidates_enabled_in_request_pack": False,
        "recommended_notice_text": recommended_notice_text(
            target=plan["target"],
            approved_window=plan["approved_window"],
        ),
        "tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "exact_tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "lifecycle_missing_role_objectives": lifecycle_role_objectives(
            post_window_state.get("exact_missing_lifecycle_event_roles")
            if isinstance(post_window_state.get("exact_missing_lifecycle_event_roles"), list)
            else None
        ),
        "two_server_cap_policy": two_server_cap_policy(),
        "runtime_window_stale_prevention": runtime_window_stale_prevention_from_plan(plan),
        "beta_notice_sequence_enforcement": beta_notice_sequence_enforcement(plan),
        "standing_launch_authority": plan.get("standing_launch_authority"),
        "authority_boundary": standing_launch_authority_boundary(args, plan),
        "external_execution_authority": external_execution_authority(plan),
        "standing_authority_non_progress_boundary": standing_authority_non_progress_boundary(
            standing=plan_has_standing_launch_authority(plan),
            scope="runtime_window_execution_state_only_report",
        ),
        "multi_surface_beta_capture_pack_boundary": multi_surface_beta_capture_pack_boundary(),
        "post_window_state_checked": True,
        "post_window_state_source_json": post_window_state.get("source_path"),
        "post_window_state": post_window_state,
        "post_window_next_blocker": post_window_state.get("next_blocker"),
        "post_window_next_action_sequence": post_window_actions,
        "active_player_no_accepted_events_policy": post_window_state.get(
            "active_player_no_accepted_events_policy"
        )
        or plan.get("active_player_no_accepted_events_policy"),
        "next_blocker": post_window_state.get("next_blocker"),
        "output_paths": {},
        "next_action_sequence": post_window_actions,
        "execution_boundaries": execution_boundaries,
        "evidence_pipeline_command_sequence": execution_boundaries[
            "evidence_pipeline_command_sequence"
        ],
        "ordered_runtime_evidence_commands": execution_boundaries[
            "evidence_pipeline_command_sequence"
        ]["commands"],
        "prepared_artifacts": execution_boundaries["prepared_artifacts"],
        "human_lead_actions": execution_boundaries["human_lead_actions"],
        "standing_authority_metadata": execution_boundaries["standing_authority_metadata"],
        "passive_waits": execution_boundaries["passive_waits"],
        "checker_required_post_window_replay": execution_boundaries[
            "checker_required_post_window_replay"
        ],
        "route_gate_expected": {
            "valid": True,
            "planning_only": True,
            "route_blocked": True,
            "current_route_blocker": "approved_runtime_evidence_missing",
        },
        "confirmed_notice_required_before_activation": True,
        "approved_evidence_bundle_checker_accepted": False,
        "approved_evidence_bundle_acceptance_required": True,
        "approved_evidence_bundle_acceptance_requirement": approved_evidence_bundle_acceptance_requirement(),
        "prepared_actions_remain_notice_only_or_request_only": True,
        "preparation_counts_as_readiness": False,
        "preparation_counts_as_progress": False,
        "readiness_claim_allowed": False,
        "progress_claim_allowed": False,
        "sidecar_non_evidence_flags": SIDECAR_NON_EVIDENCE_FLAGS,
        "standing_authority_counts_as_runtime_progress": False,
        "standing_authority_counts_as_sdk_progress": False,
        "standing_authority_grants_runtime_readiness": False,
        "server_steps_remaining": server_steps_remaining_for_state(post_window_state),
        "non_claims": [
            "post-window state-only mode consumes JSON diagnostics only",
            "closure reports and passive summaries are not approved runtime evidence",
            "passive monitor summaries do not authorize process control or evidence promotion",
            "active-player/no-accepted-events summaries are drift metadata only and do not recommend restart without a concrete deploy/gate change",
            "approved runtime evidence remains false until copied-log bundle checkers accept it",
            "standing launch authority reference is preserved but this report does not claim current-turn approval",
            "multi-surface beta capture pack artifacts are offline candidate metadata only and do not clear approved_runtime_evidence_missing",
        ],
        **multi_surface_beta_capture_action_boundary_fields(),
        **FALSE_FLAGS,
        "closure_report_counts_as_approved_runtime_evidence": False,
        "passive_summary_counts_as_approved_runtime_evidence": False,
        "passive_monitor_counts_as_approved_runtime_evidence": False,
        "notice_report_counts_as_approved_runtime_evidence": False,
        "executor_report_counts_as_approved_runtime_evidence": False,
        "status_report_counts_as_approved_runtime_evidence": False,
        "passive_complete_triplets_count_as_approved_runtime_evidence": False,
        "current_turn_approval_claimed_by_executor": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    reject_flow_target_aliases(args)
    plan = build_plan(plan_args(args))
    if plan.get("schema") != PLAN_SCHEMA:
        raise SystemExit("runtime window planner returned an unexpected schema")
    apply_executor_request_pack_options(plan, args)
    post_window_state = consume_post_window_state(args, plan)
    if args.post_window_state_only:
        if args.post_window_state_json is None:
            raise SystemExit("--post-window-state-only requires --post-window-state-json")
        return build_state_only_report(
            args=args,
            plan=plan,
            post_window_state=post_window_state,
        )
    evidence_dir = Path(plan["evidence_dir"])
    default_report_dir = default_report_dir_for_plan(plan)
    report_dir = protected_output_dir(args.report_dir or default_report_dir, "--report-dir")
    report_dir.mkdir(parents=True, exist_ok=True)

    request_check = path_in_report_dir(report_dir, "window-request.check.json")
    dry_run_notice = path_in_report_dir(report_dir, "beta-notice.dry-run.json")
    dry_run_notice_sidecar = notice_sidecar_path(report_dir, "beta-notice.dry-run.sidecar.json")
    confirmed_notice_sidecar = notice_sidecar_path(report_dir, "beta-notice.confirmed.sidecar.json")
    route_gate = path_in_report_dir(report_dir, "route-gate.json")
    activation_report = path_in_report_dir(report_dir, "activation-preconditions.json")
    prepare_report = path_in_report_dir(report_dir, "request-pack.prepare.json")
    executor_report = path_in_report_dir(report_dir, "runtime-window-execution.json")
    post_window_next_actions_dry_run = path_in_report_dir(
        report_dir,
        "post-window-next-actions.dry-run.json",
    )
    multi_surface_pack_paths = (
        multi_surface_beta_capture_pack_paths(plan, report_dir)
        if args.prepare_multi_surface_beta_pack
        else None
    )

    steps: list[dict[str, Any]] = []
    step_specs: list[tuple[str, Path]] = [
        ("prepare_request_pack", prepare_report),
        ("check_request_pack", request_check),
        ("beta_notice_dry_run", dry_run_notice),
        ("route_gate", route_gate),
    ]
    if multi_surface_pack_paths is not None:
        step_specs.extend(
            [
                (
                    MULTI_SURFACE_BETA_CAPTURE_PREPARE_STEP_ID,
                    Path(multi_surface_pack_paths["prepare_report"]),
                ),
                (
                    MULTI_SURFACE_BETA_CAPTURE_CHECK_STEP_ID,
                    Path(multi_surface_pack_paths["check_report"]),
                ),
            ]
        )
    for step_id, output_path in step_specs:
        if step_id in {
            MULTI_SURFACE_BETA_CAPTURE_PREPARE_STEP_ID,
            MULTI_SURFACE_BETA_CAPTURE_CHECK_STEP_ID,
        }:
            if multi_surface_pack_paths is None:
                raise SystemExit(f"{step_id} requested without multi-surface pack paths")
            command = multi_surface_beta_capture_command(
                step_id,
                plan=plan,
                paths=multi_surface_pack_paths,
            )
        else:
            command = command_by_id(plan, step_id)
        if step_id == "beta_notice_dry_run":
            command = command_with_notice_artifact(command, dry_run_notice_sidecar)
        if step_id == "prepare_request_pack":
            pack_matches, mismatches = existing_request_pack_matches_plan(
                plan,
                diagnostic_candidates_requested=args.diagnostic_candidates,
            )
            if pack_matches:
                result = skipped_prepare_step(command, output_path, plan)
            else:
                guard_against_bound_request_pack_mutation(
                    plan,
                    report_dir=report_dir,
                    supplied_notice_report=args.confirmed_notice_report_json,
                    mismatches=mismatches,
                )
                result = run_command(command, redirect=output_path)
        else:
            result = run_command(command, redirect=output_path)
        accept_expected_route_gate_block(result, output_path)
        steps.append(result)
        if not result["ok"]:
            break

    activation_attempted = False
    activation_checked = False
    activation_ready = False
    activation_checker_next_blocker = "approved_dry_run_checked_beta_testers_notice_sent"
    notice_report_path: str | None = None
    if all(step["ok"] for step in steps):
        if args.confirmed_notice_report_json is not None:
            confirmed_notice = protected_input_file(
                args.confirmed_notice_report_json,
                "--confirmed-notice-report-json",
            )
            notice_report_path = str(confirmed_notice)
            activation_command = activation_command_from_plan(
                plan,
                request_check=request_check,
                notice_report=confirmed_notice,
                route_gate=route_gate,
            )
            activation_step = run_command(activation_command, redirect=activation_report)
            steps.append(activation_step)
            activation_attempted = True
            try:
                activation_payload = load_json(activation_report)
                activation_checker_next_blocker = str(activation_payload.get("next_blocker") or "")
                activation_ready = activation_step["ok"] and activation_payload.get("ready") is True
                activation_checked = activation_ready
            except (OSError, json.JSONDecodeError, SystemExit):
                activation_checker_next_blocker = "activation_preconditions_report_unreadable"
        else:
            notice_report_path = str(dry_run_notice)

    request_pack_payload = load_request_pack_payload(plan)
    observer_env_path = plan.get("artifacts", {}).get("observer_env")
    diagnostic_candidates = diagnostic_candidates_policy(
        requested=args.diagnostic_candidates,
        plan=plan,
        request=request_pack_payload,
        observer_env_path=observer_env_path,
    )
    diagnostic_approved_evidence = diagnostic_candidates_for_approved_evidence_policy(
        request_pack_payload,
        observer_env_path=observer_env_path,
    )
    diagnostic_approved_evidence_blockers = list(
        diagnostic_approved_evidence["approved_evidence_blockers"]
    )
    if diagnostic_approved_evidence_blockers:
        activation_ready = False
        activation_checker_next_blocker = str(diagnostic_approved_evidence_blockers[0])
    preactivation_prepared = (
        all(step["ok"] for step in steps)
        and not activation_attempted
        and not diagnostic_approved_evidence_blockers
    )
    prepared_metadata_only = (
        all(step["ok"] for step in steps) and not diagnostic_approved_evidence_blockers
    )
    status = (
        "offline_activation_preconditions_satisfied"
        if activation_checked and activation_ready
        else "offline_activation_preconditions_blocked"
        if activation_attempted
        else "offline_preactivation_prepared_notice_send_pending"
        if preactivation_prepared
        else "offline_preactivation_failed"
    )
    output_paths = report_output_paths(
        plan,
        report_dir=report_dir,
        request_check=request_check,
        dry_run_notice=dry_run_notice,
        route_gate=route_gate,
        activation_report=activation_report,
        dry_run_notice_sidecar=dry_run_notice_sidecar,
        confirmed_notice_sidecar=confirmed_notice_sidecar,
        executor_report=executor_report,
        post_window_next_actions_dry_run=post_window_next_actions_dry_run,
        notice_report_path=notice_report_path,
        multi_surface_pack_paths=multi_surface_pack_paths,
    )
    multi_surface_pack_execution = multi_surface_beta_capture_pack_execution_summary(
        requested=args.prepare_multi_surface_beta_pack,
        paths=multi_surface_pack_paths,
        steps=steps,
    )
    next_blocker = (
        str(diagnostic_approved_evidence_blockers[0])
        if diagnostic_approved_evidence_blockers
        else offline_next_blocker(
            activation_checked=activation_checked or activation_attempted,
            activation_ready=activation_ready,
            standing_launch_authority_recorded=plan_has_standing_launch_authority(plan),
            activation_checker_blocker=activation_checker_next_blocker,
        )
    )
    next_actions = next_action_sequence(
        status=status,
        output_paths=output_paths,
        activation_checked=activation_checked,
        activation_ready=activation_ready,
        plan=plan,
        request=request_pack_payload,
    )
    post_window_actions = post_window_next_action_sequence(post_window_state)
    execution_boundaries = runtime_execution_boundaries(
        plan=plan,
        output_paths=output_paths,
        next_actions=next_actions,
        post_window_next_actions=post_window_actions,
        post_window_state=post_window_state,
    )
    fresh_retry = runtime_fresh_retry_after_closed_non_evidence_window(
        plan,
        output_paths=output_paths,
        report_dir=report_dir,
    )
    return {
        "schema": SCHEMA,
        "status": status,
        "plan_schema": plan.get("schema"),
        "run_id": plan["run_id"],
        "target": plan["target"],
        "fresh_retry_after_closed_non_evidence_window": fresh_retry,
        "approved_window": plan["approved_window"],
        "evidence_dir": str(evidence_dir),
        "report_dir": str(report_dir),
        "report_dir_deterministic": True,
        "report_dir_collision_resistant": True,
        "runtime_window_execution_report_json": str(executor_report),
        "steps": steps,
        "executed_step_ids": [step["id"] for step in steps],
        "preactivation_prepared": preactivation_prepared,
        "runtime_window_prepared": prepared_metadata_only,
        "prepared_metadata_only": prepared_metadata_only,
        "preparation_status": (
            "prepared_metadata_only"
            if prepared_metadata_only
            else "preparation_blocked_metadata_only"
        ),
        "request_pack_path": plan["artifacts"]["window_request"],
        "request_pack_paths": output_paths["request_pack"],
        "request_check_json": str(request_check),
        "beta_notice_dry_run_json": str(dry_run_notice),
        "notice_report_json_for_activation": notice_report_path,
        "route_gate_json": str(route_gate),
        "activation_preconditions_json": str(activation_report),
        "activation_preconditions_attempted": activation_attempted,
        "activation_preconditions_checked": activation_checked,
        "activation_preconditions_ready": activation_ready,
        "activation_preconditions_offline_ready": activation_ready,
        "activation_preconditions_ready_claim_allowed": False,
        "activation_preconditions_progress_claim_allowed": False,
        "activation_preconditions_ready_scope": (
            "offline_pre_activation_consistency_only"
            if activation_checked
            else "blocked_notice_binding_not_checked"
            if activation_attempted
            else "not_checked"
        ),
        "diagnostic_candidates": diagnostic_candidates,
        "diagnostic_candidates_for_approved_evidence": diagnostic_approved_evidence,
        "diagnostic_candidates_approved_evidence_blockers": diagnostic_approved_evidence_blockers,
        "diagnostic_candidates_requested": args.diagnostic_candidates,
        "diagnostic_candidates_enabled_in_request_pack": (
            request_pack_payload.get("diagnostic_candidates_enabled") is True
        ),
        "recommended_notice_text": recommended_notice_text(
            target=plan["target"],
            approved_window=plan["approved_window"],
        ),
        "tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "exact_tester_evidence_objective": EXACT_TESTER_EVIDENCE_OBJECTIVE,
        "lifecycle_missing_role_objectives": lifecycle_role_objectives(
            post_window_state.get("exact_missing_lifecycle_event_roles")
            if isinstance(post_window_state.get("exact_missing_lifecycle_event_roles"), list)
            else None
        ),
        "two_server_cap_policy": two_server_cap_policy(),
        "runtime_window_stale_prevention": runtime_window_stale_prevention_from_plan(plan),
        "beta_notice_sequence_enforcement": beta_notice_sequence_enforcement(plan),
        "standing_launch_authority": plan.get("standing_launch_authority"),
        "authority_boundary": standing_launch_authority_boundary(args, plan),
        "external_execution_authority": external_execution_authority(plan),
        "standing_authority_non_progress_boundary": standing_authority_non_progress_boundary(
            standing=plan_has_standing_launch_authority(plan),
            scope="runtime_window_execution_report",
        ),
        "multi_surface_beta_capture_pack_requested": args.prepare_multi_surface_beta_pack,
        "multi_surface_beta_capture_pack_paths": multi_surface_pack_paths or {},
        "multi_surface_beta_capture_pack_execution": multi_surface_pack_execution,
        "multi_surface_beta_capture_pack_prepared": multi_surface_pack_execution[
            "prepare_step_ok"
        ],
        "multi_surface_beta_capture_pack_checked": multi_surface_pack_execution["check_step_ok"],
        "multi_surface_beta_capture_pack_candidate_integrity_validated": (
            multi_surface_pack_execution["candidate_pack_integrity_validated"]
        ),
        "multi_surface_beta_capture_pack_boundary": multi_surface_beta_capture_pack_boundary(),
        "post_window_state_checked": post_window_state.get("checked") is True,
        "post_window_state_source_json": post_window_state.get("source_path"),
        "post_window_state": post_window_state,
        "post_window_next_blocker": post_window_state.get("next_blocker"),
        "post_window_next_action_sequence": post_window_actions,
        "active_player_no_accepted_events_policy": post_window_state.get(
            "active_player_no_accepted_events_policy"
        )
        or plan.get("active_player_no_accepted_events_policy"),
        "next_blocker": next_blocker,
        "output_paths": output_paths,
        "dry_run_notice_sidecar_json": str(dry_run_notice_sidecar),
        "confirmed_notice_sidecar_json_expected": str(confirmed_notice_sidecar),
        "sidecar_required_for_confirmed_send_consumption": True,
        "stdout_only_confirmation_accepted": False,
        "sidecar_non_evidence_flags": SIDECAR_NON_EVIDENCE_FLAGS,
        "next_action_sequence": next_actions,
        "execution_boundaries": execution_boundaries,
        "evidence_pipeline_command_sequence": execution_boundaries[
            "evidence_pipeline_command_sequence"
        ],
        "ordered_runtime_evidence_commands": execution_boundaries[
            "evidence_pipeline_command_sequence"
        ]["commands"],
        "prepared_artifacts": execution_boundaries["prepared_artifacts"],
        "human_lead_actions": execution_boundaries["human_lead_actions"],
        "standing_authority_metadata": execution_boundaries["standing_authority_metadata"],
        "passive_waits": execution_boundaries["passive_waits"],
        "checker_required_post_window_replay": execution_boundaries[
            "checker_required_post_window_replay"
        ],
        "route_gate_expected": {
            "valid": True,
            "planning_only": True,
            "route_blocked": True,
            "current_route_blocker": "approved_runtime_evidence_missing",
        },
        "confirmed_notice_required_before_activation": not activation_checked,
        "approved_evidence_bundle_checker_accepted": False,
        "approved_evidence_bundle_acceptance_required": True,
        "approved_evidence_bundle_acceptance_requirement": approved_evidence_bundle_acceptance_requirement(),
        "prepared_actions_remain_notice_only_or_request_only": True,
        "preparation_counts_as_readiness": False,
        "preparation_counts_as_progress": False,
        "readiness_claim_allowed": False,
        "progress_claim_allowed": False,
        "standing_authority_counts_as_runtime_progress": False,
        "standing_authority_counts_as_sdk_progress": False,
        "standing_authority_grants_runtime_readiness": False,
        "standing_authority_authorizes_discord_send": False,
        "standing_authority_authorizes_runtime_evidence": False,
        "standing_authority_authorizes_marker_env_changes": False,
        "standing_authority_authorizes_server_restart": False,
        "server_steps_remaining": server_steps_remaining_for_state(post_window_state),
        "non_claims": [
            "offline executor only; no Discord send is performed",
            "dry-run notice is not activation evidence",
            "request/check/route/activation reports are not approved runtime evidence",
            "active-player/no-accepted-events summaries are drift metadata only and do not recommend restart without a concrete deploy/gate change",
            "server marker/env and ARK process changes remain external live-ops steps; recorded standing authority is preserved when bound",
            "multi-surface beta capture pack artifacts are offline candidate metadata only and do not clear approved_runtime_evidence_missing",
        ],
        **multi_surface_beta_capture_action_boundary_fields(),
        **FALSE_FLAGS,
        "closure_report_counts_as_approved_runtime_evidence": False,
        "passive_summary_counts_as_approved_runtime_evidence": False,
        "passive_monitor_counts_as_approved_runtime_evidence": False,
        "notice_report_counts_as_approved_runtime_evidence": False,
        "executor_report_counts_as_approved_runtime_evidence": False,
        "status_report_counts_as_approved_runtime_evidence": False,
        "passive_complete_triplets_count_as_approved_runtime_evidence": False,
        "current_turn_approval_claimed_by_executor": False,
        "non_authorization": NON_AUTHORIZATION,
    }


def print_human(report: dict[str, Any]) -> None:
    print(f"Runtime window execution: {report['status']}")
    print(f"Run: {report['run_id']}")
    print(f"Target: {report['target']['instance']} / {report['target']['map']}")
    print(f"Evidence dir: {report['evidence_dir']}")
    print(f"Report dir: {report['report_dir']}")
    print(f"Request pack: {report['request_pack_path']}")
    print(f"Dry-run report: {report['beta_notice_dry_run_json']}")
    print(f"Route gate: {report['route_gate_json']}")
    print(f"Activation preconditions: {report['activation_preconditions_json']}")
    post_window_state = report.get("post_window_state")
    if isinstance(post_window_state, dict) and post_window_state.get("checked") is True:
        print(f"Post-window source: {post_window_state.get('source_path')}")
        print(f"Post-window blocker: {post_window_state.get('next_blocker')}")
        missing_artifacts = post_window_state.get("exact_missing_required_artifacts") or []
        artifact_gap_scope = post_window_state.get("artifact_gap_scope")
        artifact_text = (
            ", ".join(missing_artifacts)
            if missing_artifacts
            else "none reported"
            if artifact_gap_scope == "closure_report_exact"
            else f"not classified ({artifact_gap_scope})"
        )
        print(f"Missing artifacts: {artifact_text}")
        print(
            "Missing lifecycle roles: "
            + (
                ", ".join(post_window_state.get("exact_missing_lifecycle_event_roles") or [])
                or "none reported"
            )
        )
    print(f"Next blocker: {report['next_blocker']}")
    print("Next actions:")
    for item in report["next_action_sequence"]:
        print(f"{item['order']}. {item['id']}: {item['action']}")


def persist_runtime_window_execution_report(report: dict[str, Any]) -> None:
    path_value = report.get("runtime_window_execution_report_json")
    if not isinstance(path_value, str) or not path_value:
        return
    path = Path(path_value)
    output_dir = protected_output_dir(path.parent, "runtime_window_execution_report_json")
    output_path = output_dir / path.name
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    report = build_report(args)
    persist_runtime_window_execution_report(report)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human(report)
    return 0 if report["status"] in {
        "offline_preactivation_prepared_notice_send_pending",
        "offline_activation_preconditions_satisfied",
        "post_window_state_consumed_non_evidence",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
