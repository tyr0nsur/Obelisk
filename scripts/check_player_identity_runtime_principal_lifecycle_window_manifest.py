#!/usr/bin/env python3
"""Validate an offline player-principal lifecycle runtime window manifest.

The manifest is the secret-free `key=value` sidecar kept beside a copied Obelisk log.
This checker validates operational posture only. It does not approve public identity,
plugin delivery, permissions, commands, lookup, mutation, or runtime SDK readiness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import protected_paths
from player_principal_commit_validation import is_reviewed_obelisk_commit
from prepare_player_principal_lifecycle_window_request import (
    APPROVAL_RECEIPT_SCHEMA,
    APPROVAL_ATTESTATION_CURRENT_TURN,
    APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY,
    APPROVAL_SOURCE_CURRENT_TURN,
    APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY,
    APPROVAL_TEXT,
    STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT,
    APPROVED_BETA_NOTICE_PATH,
    AUTHORIZATION_FLAGS,
    NON_CLAIMS,
    OPERATOR_APPROVAL_RECEIPT_NON_CLAIMS,
    PASSIVE_WAIT_BOUNDARY_SCHEMA,
    PLAYER_NOTICE_ACTION_NON_AUTHORIZATION,
    PLAYER_NOTICE_ACTION_SCHEMA,
    PLAYER_PRESENCE_SAFETY_NON_AUTHORIZATION,
    PLAYER_PRESENCE_SAFETY_SCHEMA,
    PLANNED_OBELISK_BUILD_IDENTITY_SCHEMA,
    EXPECTED_BINARY_SHA256,
    EXPECTED_SERVER_BINARY_PATH,
    MAX_OPERATOR_APPROVAL_LEAD_SECONDS,
    REPLAY_NON_AUTHORIZATION,
    RUN_ID_RE,
    SCHEMA as WINDOW_REQUEST_SCHEMA,
    SESSION_START_REJECTED_REQUIRED_CALL,
    SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS,
    SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES,
    player_presence_safety,
    request_pack_digest,
    runtime_triplet_contract,
)
from snapshot_evidence_pack import reject_symlink_component


REPORT_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-window-manifest-check.v1"
NEXT_BLOCKER_AFTER_WINDOW_MANIFEST = "approved_runtime_observer_log_summary_and_manifest_missing"
NEXT_REQUIRED_ARTIFACT_AFTER_WINDOW_MANIFEST = "approved_runtime_principal_lifecycle_evidence_bundle"
NEXT_STEP_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-window-manifest-next-step.v1"
NEXT_STEP_AFTER_WINDOW_MANIFEST = "build_and_check_approved_runtime_principal_lifecycle_evidence_bundle"
NEXT_STEP_WHEN_BLOCKED = "fix_window_manifest_blockers"
WINDOW_REQUEST_CHECKER = Path(__file__).resolve().parent / "check_player_principal_lifecycle_window_request.py"
SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = protected_paths.approved_offline_workspace_roots()
EXPECTED_COPIED_LOG_PARENT = "live-validation-logs"
EXPECTED_OBELISK_ROOT = "/servidor/ark/obelisk"
EXPECTED_INSTALLED_WRAPPER_PATH = "/servidor/ark/serverfiles/ShooterGame/Binaries/Linux/ObeliskRun.sh"
ROLLBACK_MARKER_STATE_ROOT = "/servidor/ark/obelisk/state/instances"

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PREFLIGHT_SCHEMA = "obelisk.player-principal-lifecycle-preflight.v1"
APPROVED_EVIDENCE_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1"
SHAPE_FIXTURE_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-evidence.v1"
SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
UTC_TIMESTAMP_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
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
POSITIVE_CAPABILITY_VALUE_RE = re.compile(
    r"(?:public[_ -]?(?:sdk|player[_ -]?identity)|"
    r"public[_ -]?headers?[_ -]?(?:allowed|ready|enabled|supported)|"
    r"(?:(?:request[_ -]?pack|window[_ -]?request|preflight|(?:completed[_ -]?)?receipt|"
    r"operator[_ -]?approval[_ -]?(?:request|receipt)|operator[_ -]?request|"
    r"approval[_ -]?request|window[_ -]?manifest|observer[_ -]?(?:window[_ -]?)?env|"
    r"window[_ -]?env|env(?:ironment)?|(?:source[_ -]?)?markers?|copied[_ -]?(?:log|bundle)|"
    r"stale[_ -]?bundle|sidecars?|artifacts?)[_ -]?"
    r"(?:counts?[_ -]?as|is|are|proves?|provides?|authorizes?|approves?)[_ -]?"
    r"approved[_ -]?runtime[_ -]?evidence)|"
    r"(?:public[_ -]?)?(?:runtime[_ -]?)?v1[_ -]?(?:sdk[_ -]?)?"
    r"(?:ready|readiness|enabled|allowed|supported|complete|completed|completion)|"
    r"player[_ -]?identity[_ -]?(?:promotion|ready|readiness)|"
    r"(?:sdk|runtime|lookup|permissions?|admin|command(?:s|[_ -]?(?:reply|response|routing|support))?|"
    r"plugin[_ -]?delivery|mutation|return[_ -]?override|resourcehandle|live[_ -]?(?:ops?|logs?)|"
    r"live[_ -]?server[_ -]?logs?)[_ -]?"
    r"(?:ready|readiness|enabled|allowed|supported|promoted|delivered)|"
    r"command[_ -]?(?:reply|response|routing|support)|"
    r"(?:lookup|mutation|return[_ -]?override)[_ -]?allowed)",
    re.IGNORECASE,
)
FORBIDDEN_RECEIPT_AUTHORIZATION_CLAIM_RE = re.compile(
    r"(?:(?:request[_ -]?pack|window[_ -]?request|preflight|(?:completed[_ -]?)?receipt|"
    r"operator[_ -]?approval[_ -]?(?:request|receipt)|operator[_ -]?request|"
    r"approval[_ -]?request|window[_ -]?manifest|observer[_ -]?(?:window[_ -]?)?env|"
    r"window[_ -]?env|env(?:ironment)?|(?:source[_ -]?)?markers?|copied[_ -]?(?:log|bundle)|"
    r"stale[_ -]?bundle|sidecars?|artifacts?)[_ -]?"
    r"(?:counts?[_ -]?as|is|are|proves?|provides?|authorizes?|approves?)[_ -]?"
    r"approved[_ -]?runtime[_ -]?evidence|"
    r"\b(?:server[_ -]?operations?|runtime(?:[_ -]?(?:work|capture|window|sdk))?|"
    r"live[_ -]?(?:ops?|logs?)|live[_ -]?server[_ -]?logs?|"
    r"public[_ -]?(?:sdk|headers?)|v1(?:[_ -]?sdk)?(?:[_ -]?completion)?|player[_ -]?identity|"
    r"promotion|sdk|lookup|permissions?|admin|commands?)\b.{0,80}"
    r"\b(?:authorized|authorizes|approved|allowed|enabled|supported|promoted|promotion|"
    r"ready|readiness|complete|completed|completion|delivered)\b|"
    r"\b(?:authorizes?|approves?|allows?|permits?)\b.{0,80}"
    r"\b(?:server|runtime|live[_ -]?(?:ops?|logs?)|marker|env|starts?|restarts?|stops?|public[_ -]?sdk|v1|"
    r"player[_ -]?identity|promotion|lookup|permissions?|admin|commands?)\b)",
    re.IGNORECASE,
)
RECEIPT_NEGATED_AUTHORIZATION_ACTION_RE = re.compile(
    r"\b(?:does\s+not|do\s+not|doesn't|don't|cannot|can't|must\s+not|never|no|not)\s+"
    r"(?:authorize|authorise|approve|allow|enable|permit|promote|support|claim|make|mark|"
    r"treat|count|provide|record)\b",
    re.IGNORECASE,
)
RECEIPT_NEGATED_PREFIX_RE = re.compile(
    r"\b(?:does\s+not|do\s+not|doesn't|don't|cannot|can't|must\s+not|never|no|not)\s*$",
    re.IGNORECASE,
)
EXPECTED_OPERATOR_APPROVAL_RECEIPT_NON_CLAIMS = OPERATOR_APPROVAL_RECEIPT_NON_CLAIMS
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
        "player_presence_safety",
        "copied_evidence_dir",
        "copied_log_path",
        "window_manifest_path",
        "exact_target_scope",
        "passive_wait_boundary",
        "direct_join_plan",
        "runtime_triplet_contract",
        "rollback",
        "current_turn_approval_scope",
        "deployment_intent",
    )
)
EXPECTED_OPERATOR_APPROVAL_RECEIPT_TARGET_KEYS = frozenset(("instance", "map"))
EXPECTED_OPERATOR_APPROVAL_RECEIPT_WINDOW_KEYS = frozenset(("start_utc", "end_utc"))
EXPECTED_OPERATOR_APPROVAL_RECEIPT_ROLLBACK_KEYS = frozenset(
    (
        "owner",
        "delta",
        "marker_state_dir",
        "stable_marker_paths",
        "observer_marker_paths",
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
EXPECTED_REQUEST_PACK_REPLAY_SIDECAR_KEYS = frozenset(
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
EXPECTED_REQUEST_PACK_TOP_LEVEL_KEYS = frozenset(
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
        "direct_join_plan",
        "marker_set",
        "forbidden_markers",
        "operator_live_ops_brief",
        "rollback",
        "non_claims",
    )
)
NON_EVIDENCE_SIDECAR_SCHEMA_BLOCKERS = {
    APPROVED_EVIDENCE_SCHEMA: "approved_runtime_manifest_sidecar_not_checked_bundle_output",
    SHAPE_FIXTURE_SCHEMA: "synthetic_shape_fixture_sidecar_not_approved_runtime_evidence",
    "obelisk.multi-surface-beta-capture-pack.v1": (
        "multi_surface_beta_capture_pack_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.multi-surface-beta-capture-plan.v1": (
        "multi_surface_beta_capture_plan_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.multi-surface-beta-capture-checker-matrix.v1": (
        "multi_surface_beta_capture_checker_matrix_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.multi-surface-beta-capture-non-claim-manifest.v1": (
        "multi_surface_beta_capture_non_claim_manifest_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.multi-surface-beta-capture-plan-queue.v1": (
        "multi_surface_beta_capture_plan_queue_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.player-principal-lifecycle-beta-notice-prep.v1": "notice_prep_sidecar_not_approved_runtime_evidence",
    "obelisk.discord-beta-bridge-active-notice.v1": "discord_bridge_state_sidecar_not_approved_runtime_evidence",
    "obelisk.discord-beta-bridge-bot-notice.v1": "discord_bridge_state_sidecar_not_approved_runtime_evidence",
    "obelisk.discord-beta-bridge-dry-run-receipt.v1": "discord_bridge_state_sidecar_not_approved_runtime_evidence",
    "obelisk.discord-beta-bridge-event-summary.v1": "discord_bridge_state_sidecar_not_approved_runtime_evidence",
    "obelisk.discord-beta-bridge-tester-status-summary.v1": "discord_bridge_state_sidecar_not_approved_runtime_evidence",
    "obelisk.player-principal-lifecycle-evidence-closure-request.v1": "closure_request_sidecar_not_approved_runtime_evidence",
    "obelisk.player-principal-passive-snapshot.v1": "passive_snapshot_sidecar_not_approved_runtime_evidence",
    "obelisk.player-principal-passive-snapshot-diff.v1": "passive_snapshot_diff_sidecar_not_approved_runtime_evidence",
    "obelisk.player-principal-passive-snapshot-latest.v1": "passive_snapshot_latest_sidecar_not_approved_runtime_evidence",
    "obelisk.player-principal-passive-monitor-only-summary.v1": (
        "passive_monitor_only_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.player-principal-passive-observer-event-triage.v1": "passive_event_triage_sidecar_not_approved_runtime_evidence",
    "obelisk.player-principal-passive-activity-triage.v1": (
        "passive_activity_triage_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.player-principal-passive-extended-monitor-triage.v1": (
        "passive_extended_monitor_triage_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.player-principal-passive-actionability.v1": "passive_actionability_sidecar_not_approved_runtime_evidence",
    "obelisk.player-principal-passive-runner-action-hint.v1": (
        "passive_runner_action_hint_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.player-principal-passive-target-triplet-candidate-summary.v1": (
        "passive_target_triplet_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.player-principal-passive-server-activity-summary.v1": (
        "passive_server_activity_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.player-principal-passive-wait-metadata.v1": "passive_wait_sidecar_not_approved_runtime_evidence",
    "obelisk.player-principal-public-reachability-check.v1": (
        "public_reachability_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.sdk-status-report.v1": "sdk_status_report_sidecar_not_approved_runtime_evidence",
    "obelisk.sdk-status-side-lane-summary.v1": (
        "sdk_status_side_lane_summary_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.command-permission-route-post-evidence-p0-lock-simulation.v1": (
        "post_evidence_p0_lock_simulation_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.public-sdk-v1-completion-check.v1": (
        "public_sdk_completion_check_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.public-sdk-v1-completion-summary.v1": (
        "public_sdk_completion_summary_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.public-sdk-v1-fastest-next-unblock.v1": (
        "public_sdk_fastest_next_unblock_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.public-sdk-v1-approved-in-game-evidence-status.v1": (
        "public_sdk_approved_in_game_evidence_status_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.approved-in-game-evidence-status.v1": (
        "approved_in_game_evidence_status_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.player-principal-lifecycle-runtime-evidence-status.v1": (
        "runtime_evidence_status_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.player-principal-lifecycle-runtime-evidence-status-machine-next-actions.v1": (
        "runtime_evidence_status_machine_next_actions_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.player-principal-lifecycle-closure-machine-next-actions.v1": (
        "closure_machine_next_actions_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.player-principal-lifecycle-next-action-plan.v1": (
        "next_action_plan_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.player-principal-lifecycle-normalized-action-queue.v1": (
        "normalized_action_queue_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.player-principal-lifecycle-next-action-runner.v1": (
        "next_action_runner_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-plan.v1": (
        "runtime_window_plan_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-execution.v1": (
        "runtime_window_execution_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-next-action.v1": (
        "runtime_window_next_action_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-next-action-runner-contract.v1": (
        "runtime_window_next_action_runner_contract_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-next-action-runner-command.v1": (
        "runtime_window_next_action_runner_command_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-next-action-runner-operation.v1": (
        "runtime_window_next_action_runner_operation_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-post-window-state.v1": (
        "runtime_window_post_window_state_sidecar_not_approved_runtime_evidence"
    ),
    PLAYER_NOTICE_ACTION_SCHEMA: "player_notice_action_sidecar_not_approved_runtime_evidence",
    "obelisk.player-principal-lifecycle-activation-preconditions.v1": (
        "activation_preconditions_sidecar_not_approved_runtime_evidence"
    ),
    REPORT_SCHEMA: "window_manifest_check_report_sidecar_not_approved_runtime_evidence",
    "obelisk.player-principal-lifecycle-window-request-check.v1": (
        "window_request_check_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1": (
        "approved_evidence_check_report_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle-preflight.v1": (
        "bundle_preflight_sidecar_not_approved_runtime_evidence"
    ),
    "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle.v1": (
        "bundle_report_sidecar_not_approved_runtime_evidence"
    ),
}
EXPECTED_POST_WINDOW_JSON_SIDECAR_NAMES = frozenset(
    (
        "window-request.json",
        "operator-approval-receipt.json",
        "preflight-pre.json",
        "preflight-post.json",
    )
)
UNEXPECTED_JSON_SIDECAR_NAME_BLOCKERS = (
    (
        re.compile(
            r"(?:multi[._-]?surface[._-]?beta[._-]?capture|"
            r"beta[._-]?capture|capture[._-]?(?:pack|plan)|"
            r"checker[._-]?command[._-]?matrix|non[._-]?claim[._-]?manifest)",
            re.IGNORECASE,
        ),
        "unexpected_json_sidecar_multi_surface_beta_capture_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:receipt[._-]?template|operator[._-]?approval[._-]?receipt[._-]?template)", re.IGNORECASE),
        "unexpected_json_sidecar_generated_receipt_template_not_post_window_replay_evidence",
    ),
    (
        re.compile(r"(?:notice|beta[._-]?notice|discord)", re.IGNORECASE),
        "unexpected_json_sidecar_notice_or_discord_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:partial|incomplete|candidate|closure|bundle[._-]?preflight|preflight[._-]?only)", re.IGNORECASE),
        "unexpected_json_sidecar_partial_evidence_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:histor|stale|prior|previous|old[._-]?window)", re.IGNORECASE),
        "unexpected_json_sidecar_historical_evidence_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:passive|snapshot|watch[._-]?only|monitor[._-]?tick)", re.IGNORECASE),
        "unexpected_json_sidecar_passive_snapshot_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:reachability|public[._-]?query|steam[._-]?query|gamedig)", re.IGNORECASE),
        "unexpected_json_sidecar_public_reachability_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:status|report|summary|readiness[._-]?check|completion[._-]?check)", re.IGNORECASE),
        "unexpected_json_sidecar_status_report_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:next[._-]?actions?|action[._-]?queue|"
            r"runtime[._-]?window[._-]?(?:plan|execution|runner))",
            re.IGNORECASE,
        ),
        "unexpected_json_sidecar_next_action_or_runtime_plan_not_approved_runtime_evidence",
    ),
)
UNEXPECTED_JSON_SIDECAR_SCHEMA_BLOCKERS = (
    (
        re.compile(r"(?:multi[._-]?surface[._-]?beta[._-]?capture|beta[._-]?capture)", re.IGNORECASE),
        "unexpected_json_sidecar_multi_surface_beta_capture_schema_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:notice|beta[._-]?notice|discord)", re.IGNORECASE),
        "unexpected_json_sidecar_notice_or_discord_schema_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:passive|snapshot|watch[._-]?only|monitor[._-]?tick)", re.IGNORECASE),
        "unexpected_json_sidecar_passive_snapshot_schema_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:reachability|public[._-]?query|steam[._-]?query|gamedig)", re.IGNORECASE),
        "unexpected_json_sidecar_public_reachability_schema_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:status|report|summary|readiness[._-]?check|completion[._-]?check)", re.IGNORECASE),
        "unexpected_json_sidecar_status_report_schema_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:histor|stale|prior|previous|old[._-]?window)", re.IGNORECASE),
        "unexpected_json_sidecar_historical_schema_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:partial|incomplete|candidate|closure|bundle[._-]?preflight|preflight[._-]?only)", re.IGNORECASE),
        "unexpected_json_sidecar_partial_schema_not_approved_runtime_evidence",
    ),
    (
        re.compile(
            r"(?:next[._-]?actions?|action[._-]?queue|"
            r"runtime[._-]?window[._-]?(?:plan|execution|runner)|runtime[._-]?evidence[._-]?status)",
            re.IGNORECASE,
        ),
        "unexpected_json_sidecar_next_action_or_runtime_plan_schema_not_approved_runtime_evidence",
    ),
)
PREFLIGHT_FORBIDDEN_POSITIVE_FLAG_KEYS = frozenset(
    (
        "runtime_work_authorized",
        "server_operations_authorized",
        "live_log_read_authorized",
        "live_log_reads_authorized",
        "live_logs_read",
        "live_ops_authorized",
        "live_operations_authorized",
        "live_server_operations_authorized",
        "live_server_log_reads_authorized",
        "marker_env_changes_authorized",
        "reads_live_logs",
        "runtime_capture_authorized",
        "runtime_window_authorized",
        "runtime_ready",
        "public_sdk_ready",
        "public_abi_ready",
        "stable_sdk_ready",
        "plugin_hub_ready",
        "publication_ready",
        "promotion_ready",
        "public_header_allowed",
        "v1_completion_ready",
        "authorizes_server_restart",
        "authorizes_marker_or_env_changes",
        "authorizes_discord_send",
        "server_operations_authorized_by_template",
        "runtime_work_authorized_by_template",
        "generated_template_authorizes_runtime",
        "request_pack_acceptance_authorizes_runtime",
        "request_pack_counts_as_approved_runtime_evidence",
        "preflight_counts_as_approved_runtime_evidence",
        "window_manifest_counts_as_approved_runtime_evidence",
        "completed_receipt_counts_as_approved_runtime_evidence",
        "observer_env_counts_as_approved_runtime_evidence",
        "operator_request_counts_as_approved_runtime_evidence",
        "copied_log_metadata_counts_as_approved_runtime_evidence",
        "copied_log_presence_counts_as_approved_runtime_evidence",
        "bundle_output_counts_as_approved_runtime_evidence",
        "dry_run_success_counts_as_approved_runtime_evidence",
        "historical_target_names_authorize_runtime",
        "marker_env_readiness_counts_as_approved_runtime_evidence",
        "player_notice_counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_progress",
        "counts_as_p0_progress",
        "clears_approved_runtime_evidence_missing",
        "approved_runtime_evidence_present",
        "approved_runtime_evidence_ready",
        "counts_as_approved_runtime_evidence",
        "passive_complete_triplets_count_as_approved_runtime_evidence",
        "public_reachability_counts_as_approved_runtime_evidence",
        "public_reachability_ready",
        "public_reachability_satisfies_runtime_evidence",
        "route_ready",
        "stable_claim_allowed",
        "sdk_accounting_counts_as_completed_surface",
        "p0_accounting_counts_as_promoted_surface",
    )
)
PREFLIGHT_REQUIRED_FALSE_AUTHORIZATION_FLAGS = frozenset(
    (
        "server_operations_authorized",
        "runtime_work_authorized",
        "runtime_ready",
        "public_sdk_ready",
        "public_abi_ready",
        "promotion_ready",
        "public_header_allowed",
        "v1_completion_ready",
        "request_pack_counts_as_approved_runtime_evidence",
        "preflight_counts_as_approved_runtime_evidence",
        "window_manifest_counts_as_approved_runtime_evidence",
        "completed_receipt_counts_as_approved_runtime_evidence",
        "observer_env_counts_as_approved_runtime_evidence",
        "operator_request_counts_as_approved_runtime_evidence",
        "copied_log_metadata_counts_as_approved_runtime_evidence",
        "copied_log_presence_counts_as_approved_runtime_evidence",
        "bundle_output_counts_as_approved_runtime_evidence",
        "dry_run_success_counts_as_approved_runtime_evidence",
        "historical_target_names_authorize_runtime",
        "marker_env_readiness_counts_as_approved_runtime_evidence",
        "player_notice_counts_as_approved_runtime_evidence",
        "approved_runtime_evidence_present",
        "approved_runtime_evidence_ready",
        "public_reachability_counts_as_approved_runtime_evidence",
        "route_ready",
        "stable_claim_allowed",
        "sdk_accounting_counts_as_completed_surface",
        "p0_accounting_counts_as_promoted_surface",
    )
)
PREFLIGHT_POSITIVE_TEXT_VALUES = frozenset(
    (
        "1",
        "accepted",
        "allowed",
        "approved",
        "authorized",
        "available",
        "complete",
        "completed",
        "enabled",
        "present",
        "promoted",
        "ready",
        "supported",
        "true",
        "yes",
    )
)
REQUEST_PACK_REQUIRED_FALSE_AUTHORIZATION_FLAGS = frozenset(
    (
        "server_operations_authorized",
        "runtime_work_authorized",
        "request_pack_counts_as_approved_runtime_evidence",
        "observer_env_counts_as_approved_runtime_evidence",
        "operator_request_counts_as_approved_runtime_evidence",
        "copied_log_metadata_counts_as_approved_runtime_evidence",
        "bundle_output_counts_as_approved_runtime_evidence",
        "publication_authorized",
        "promotion_ready",
        "public_abi_ready",
        "public_sdk_ready",
        "runtime_ready",
        "route_ready",
        "v1_completion_ready",
        "stable_claim_allowed",
        "sdk_accounting_counts_as_completed_surface",
        "p0_accounting_counts_as_promoted_surface",
    )
)
REQUEST_PACK_PASSIVE_WAIT_FALSE_KEYS = frozenset(
    (
        "wait_only_or_passive_monitor_authorizes_deploy_or_restart",
        "passive_monitor_ticks_authorize_runtime_capture",
        "player_presence_detection_authorizes_followup",
        "snapshots_or_diagnostics_count_as_approved_runtime_evidence",
    )
)
REQUEST_PACK_PLAYER_NOTICE_FALSE_KEYS = frozenset(
    (
        "send_performed_by_request_pack",
        "request_pack_authorizes_discord",
        "counts_as_approved_runtime_evidence",
        "approved_runtime_evidence",
        "approved_runtime_evidence_ready",
    )
)
REQUEST_PACK_DEPLOYMENT_INTENT_FALSE_KEYS = frozenset(
    (
        "deployment_authorized",
        "restart_authorized",
        "runtime_capture_authorized",
        "counts_as_approved_runtime_evidence",
    )
)
EXPECTED_PREFLIGHT_NON_CLAIM = (
    "preflight only; not runtime approval, not approved runtime evidence, "
    "and not permission to touch servers"
)

REQUIRED_TIMESTAMP_FIELDS = (
    "approved_window_start_utc",
    "approved_window_end_utc",
    "actual_capture_start_utc",
    "actual_capture_end_utc",
    "rollback_start_utc",
    "rollback_end_utc",
)
REQUIRED_SIMPLE_FIELDS = (
    "run_id",
    "obelisk_commit",
    "approval",
    "copied_log_path",
    "copied_log_sha256",
    "request_pack_path",
    "request_pack_sha256",
    "observer_env_path",
    "observer_env_sha256",
    "operator_approval_receipt_path",
    "operator_approval_receipt_sha256",
    "preflight_pre_path",
    "preflight_pre_sha256",
    "preflight_post_path",
    "preflight_post_sha256",
    "pre_posture",
    "post_posture",
    "pre_check",
    "post_check",
    "rollback_completed",
    "rollback_delta",
    "observer_env_survived",
    "observer_marker_survived",
    "sibling_marker_entries",
    "sibling_observer_env",
    "log_budget",
    "plugins_disabled",
    "scanner_disabled",
    "dispatch_limit",
    "wrapper_profile",
    "observer_exclusivity",
    "debug_escape_markers",
    "callback_escape_markers",
    "native_exec_disabled",
    "ptrace_disabled",
    "single_module_summary",
    "delivery_claim",
    "principal_claim",
)
ACCEPTED_USER_POLICIES = frozenset(("no_regular_users", "operator_approved_beta_users"))
APPROVED_OPERATOR_ROLES = frozenset(("operator",))
EXPECTED_APPROVAL = APPROVAL_TEXT
EXPECTED_APPROVALS = frozenset((APPROVAL_TEXT, STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT))
EXPECTED_ROLLBACK_DELTA = "removed_observer_env_and_markers_preserved_disable_plugins"
REQUIRED_OPERATIONAL_WINDOW_NON_CLAIMS = (
    "window manifest acceptance is operational posture only",
    "does not promote player identity, lookup, permissions, commands, ResourceHandle, mutation, return override, plugin delivery, public SDK, or runtime readiness",
    "does not authorize server operations, Discord updates, GitHub publication, tags, or release claims",
)
ALLOWED_FIELDS = frozenset(
    (
        *REQUIRED_TIMESTAMP_FIELDS,
        *REQUIRED_SIMPLE_FIELDS,
        "target",
        "instance",
        "instance_id",
        "map",
        "map_name",
        "user_policy",
        "users_policy",
        "notice_sent",
    )
)
PATH_VALUE_FIELDS = frozenset(
    key
    for key in REQUIRED_SIMPLE_FIELDS
    if key.endswith("_path")
)


@dataclass
class Target:
    instance: str | None
    map_name: str | None


@dataclass
class Validation:
    blockers: list[dict[str, Any]]
    target: Target
    user_policy: str | None
    copied_log_status: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, nargs="?", help="Offline key=value window manifest.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    parser.add_argument(
        "--emit-template",
        type=Path,
        help="Write a canonical secret-free key=value window manifest template and exit.",
    )
    parser.add_argument(
        "--copied-log",
        type=Path,
        help=(
            "When used with --emit-template, fill copied_log_path, copied_log_sha256, "
            "and run_id from an existing approved-workspace live-validation log copy."
        ),
    )
    parser.add_argument(
        "--post-window-replay",
        action="store_true",
        help=(
            "Validate a completed copied evidence window after its approved runtime window "
            "has expired. This tolerates only the nested approved_window_expired request "
            "checker blocker; pre-window approval checks remain strict by default."
        ),
    )
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def add_once(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    if any(blocker.get("reason") == reason and blocker.get("label") == label for blocker in blockers):
        return
    add(blockers, reason, label, **extra)


def load_manifest(path: Path) -> dict[str, str]:
    reject_symlink_component(path, "manifest")
    path = protected_paths.reject_protected_input_path(
        path,
        "manifest",
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    fields: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise SystemExit(f"{path}:{line_number}: expected key=value")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not SAFE_COMPONENT_RE.fullmatch(key):
            raise SystemExit(f"{path}:{line_number}: unsafe manifest key: {key}")
        if key in fields:
            raise SystemExit(f"{path}:{line_number}: duplicate manifest key: {key}")
        fields[key] = value
    return fields


def manifest_relative_path(value: str, manifest_path: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return manifest_path.parent / path


def parse_bool(value: str | None) -> bool | None:
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def parse_utc_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.removesuffix("Z") + "+00:00").astimezone(timezone.utc)
    except ValueError:
        return None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def is_exact_or_test_fixture_run_log(path: Path, run_id: str) -> bool:
    expected_tail = (EXPECTED_COPIED_LOG_PARENT, run_id, "Obelisk.log")
    for root in APPROVED_OFFLINE_WORKSPACE_ROOTS:
        try:
            relative = path.relative_to(root.resolve())
        except ValueError:
            continue
        parts = relative.parts
        if parts == expected_tail:
            return True
        if (
            os.environ.get("OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES") == "1"
            and len(parts) == 4
            and parts[0].startswith("obelisk-test-player-principal-")
            and parts[1:] == expected_tail
        ):
            return True
    return False


def is_test_fixture_workspace_path(path: Path) -> bool:
    if os.environ.get("OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES") != "1":
        return False
    for root in APPROVED_OFFLINE_WORKSPACE_ROOTS:
        try:
            relative = path.relative_to(root.resolve())
        except ValueError:
            continue
        return bool(relative.parts and relative.parts[0].startswith("obelisk-test-player-principal-"))
    return False


def content_readable_status(status: Any) -> bool:
    return not status.protected and status.approved_offline_workspace and status.resolved.is_file()


def add_unreadable_sidecar_status(
    blockers: list[dict[str, Any]],
    status: Any,
    *,
    label: str,
    protected_reason: str,
    unapproved_reason: str,
    missing_reason: str,
) -> bool:
    if status.protected:
        add_once(blockers, protected_reason, label, resolved=str(status.resolved))
        return False
    if not status.approved_offline_workspace:
        add_once(blockers, unapproved_reason, label, resolved=str(status.resolved))
        return False
    if not status.resolved.is_file():
        add_once(blockers, missing_reason, label, resolved=str(status.resolved))
        return False
    return True


def validate_target(fields: dict[str, str], blockers: list[dict[str, Any]]) -> Target:
    instance = fields.get("instance") or fields.get("instance_id")
    map_name = fields.get("map") or fields.get("map_name")
    target = fields.get("target")

    if target:
        parts = target.split("/")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            add(blockers, "target_must_be_instance_slash_map", "target")
        else:
            target_instance, target_map = parts
            if instance and instance != target_instance:
                add(blockers, "target_instance_mismatch", "target", target=target_instance, instance=instance)
            if map_name and map_name != target_map:
                add(blockers, "target_map_mismatch", "target", target=target_map, map=map_name)
            instance = instance or target_instance
            map_name = map_name or target_map

    if not instance:
        add(blockers, "instance_missing", "instance")
    elif not SAFE_COMPONENT_RE.fullmatch(instance):
        add(blockers, "instance_invalid", "instance")

    if not map_name:
        add(blockers, "map_missing", "map")
    elif not SAFE_COMPONENT_RE.fullmatch(map_name):
        add(blockers, "map_invalid", "map")

    return Target(instance=instance, map_name=map_name)


def validate_copied_log_path(fields: dict[str, str], manifest_path: Path, blockers: list[dict[str, Any]]) -> str | None:
    path_text = fields.get("copied_log_path")
    if not path_text:
        return None
    copied_log_path = manifest_relative_path(path_text, manifest_path)
    reject_symlink_component(copied_log_path, "copied_log_path")
    status = protected_paths.protected_path_status(
        copied_log_path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected:
        add(
            blockers,
            "copied_log_path_under_protected_server_root",
            "copied_log_path",
            resolved=str(status.resolved),
        )
        return "protected"
    run_id = fields.get("run_id")
    if run_id and run_id not in copied_log_path.parts:
        add(blockers, "copied_log_path_run_id_mismatch", "copied_log_path", run_id=run_id)
    if run_id:
        expected_tail = (EXPECTED_COPIED_LOG_PARENT, run_id, "Obelisk.log")
        if copied_log_path.parts[-3:] != expected_tail:
            add(
                blockers,
                "copied_log_path_not_live_validation_run_log",
                "copied_log_path",
                expected="/".join(expected_tail),
            )
        expected_path = APPROVED_OFFLINE_WORKSPACE_ROOTS[0].resolve() / EXPECTED_COPIED_LOG_PARENT / run_id / "Obelisk.log"
        if status.approved_offline_workspace and not is_exact_or_test_fixture_run_log(status.resolved, run_id):
            add(
                blockers,
                "copied_log_path_not_exact_approved_run_log",
                "copied_log_path",
                expected=str(expected_path),
                resolved=str(status.resolved),
            )
        manifest_status = protected_paths.protected_path_status(
            manifest_path,
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        )
        allow_test_fixture_manifest = is_test_fixture_workspace_path(manifest_status.resolved)
        if manifest_path.name != "window-manifest.env" and not allow_test_fixture_manifest:
            add(blockers, "window_manifest_filename_mismatch", "manifest", expected="window-manifest.env")
        if manifest_status.resolved.parent != status.resolved.parent and not allow_test_fixture_manifest:
            add(
                blockers,
                "window_manifest_not_beside_copied_log",
                "manifest",
                expected=str(status.resolved.parent / "window-manifest.env"),
                resolved=str(manifest_status.resolved),
            )

    expected_sha256 = fields.get("copied_log_sha256")
    if expected_sha256 == "0" * 64:
        add(blockers, "copied_log_sha256_placeholder", "copied_log_sha256")
    if status.approved_offline_workspace:
        if not status.resolved.is_file():
            add(blockers, "copied_log_file_missing", "copied_log_path", resolved=str(status.resolved))
        elif expected_sha256 and SHA256_RE.fullmatch(expected_sha256):
            actual_sha256 = hashlib.sha256(status.resolved.read_bytes()).hexdigest()
            if actual_sha256 != expected_sha256:
                add(
                    blockers,
                    "copied_log_sha256_mismatch",
                    "copied_log_sha256",
                    expected=expected_sha256,
                    actual=actual_sha256,
                )
        return "approved_offline_workspace"
    add(
        blockers,
        "copied_log_path_not_under_approved_offline_workspace",
        "copied_log_path",
        expected="/servidor/ark/workspace-offline/live-validation-logs/<run-id>/Obelisk.log",
        resolved=str(status.resolved),
    )
    return "unprotected_offline"


def validate_sidecar_file(
    fields: dict[str, str],
    manifest_path: Path,
    blockers: list[dict[str, Any]],
    *,
    path_key: str,
    sha_key: str,
    expected_name: str | None = None,
) -> str | None:
    path_text = fields.get(path_key)
    sha_text = fields.get(sha_key)
    if not path_text:
        return None
    path = manifest_relative_path(path_text, manifest_path)
    reject_symlink_component(path, path_key)
    status = protected_paths.protected_path_status(
        path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected:
        add(blockers, f"{path_key}_under_protected_server_root", path_key, resolved=str(status.resolved))
        return "protected"
    if not status.approved_offline_workspace:
        add(blockers, f"{path_key}_not_under_approved_offline_workspace", path_key, resolved=str(status.resolved))
    if expected_name is not None and status.resolved.name != expected_name:
        add(blockers, f"{path_key}_filename_mismatch", path_key, expected=expected_name, resolved=str(status.resolved))
    run_id = fields.get("run_id")
    if run_id and run_id not in status.resolved.parts:
        add(blockers, f"{path_key}_run_id_mismatch", path_key, run_id=run_id, resolved=str(status.resolved))
    if status.approved_offline_workspace:
        expected_dir = manifest_path.expanduser().resolve().parent
        if status.resolved.parent != expected_dir:
            add(
                blockers,
                f"{path_key}_not_beside_window_manifest",
                path_key,
                expected_dir=str(expected_dir),
                resolved=str(status.resolved),
            )
    if not sha_text:
        add(blockers, f"{sha_key}_missing", sha_key)
    elif SHA256_RE.fullmatch(sha_text) is None:
        add(blockers, f"{sha_key}_invalid", sha_key)
    elif sha_text == "0" * 64:
        add(blockers, f"{sha_key}_placeholder", sha_key)
    if not status.approved_offline_workspace:
        return "unprotected_offline"
    if not status.resolved.is_file():
        add(blockers, f"{path_key}_file_missing", path_key, resolved=str(status.resolved))
    elif sha_text and SHA256_RE.fullmatch(sha_text):
        actual_sha256 = hashlib.sha256(status.resolved.read_bytes()).hexdigest()
        if actual_sha256 != sha_text:
            add(blockers, f"{sha_key}_mismatch", sha_key, expected=sha_text, actual=actual_sha256)
    return "approved_offline_workspace" if status.approved_offline_workspace else "unprotected_offline"


def artifact_from_fields(
    fields: dict[str, str],
    manifest_path: Path,
    *,
    path_key: str,
    sha_key: str,
) -> dict[str, str] | None:
    path_text = fields.get(path_key)
    sha_text = fields.get(sha_key)
    if not path_text or not sha_text:
        return None
    path = manifest_relative_path(path_text, manifest_path)
    status = protected_paths.protected_path_status(
        path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    return {"path": str(status.resolved), "sha256": sha_text}


def bound_artifact_from_file(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
    }


def bound_artifact_from_status(status: Any) -> dict[str, Any]:
    return bound_artifact_from_file(status.resolved)


def rollback_marker_path(instance: str, marker: str) -> str:
    return f"{ROLLBACK_MARKER_STATE_ROOT}/{instance}/{marker}"


def normalized_receipt_rollback(value: Any, target: Target) -> Any:
    if not isinstance(value, dict):
        return value
    fallback = {
        "owner": value.get("owner"),
        "delta": value.get("delta"),
        "marker_state_dir": f"{ROLLBACK_MARKER_STATE_ROOT}/{target.instance}",
        "stable_marker_paths": {
            "enable_process_event_hook": rollback_marker_path(target.instance, "enable-process-event-hook"),
            "disable_plugins": rollback_marker_path(target.instance, "disable-plugins"),
        },
        "observer_marker_paths": {
            "allow_observer_debug_window": rollback_marker_path(target.instance, "allow-observer-debug-window"),
            "allow_experimental_observers": rollback_marker_path(target.instance, "allow-experimental-observers"),
            "enable_player_principal_lifecycle_observer": rollback_marker_path(
                target.instance,
                "enable-player-principal-lifecycle-observer",
            ),
        },
    }
    normalized = {**fallback, **value}
    for key in ("stable_marker_paths", "observer_marker_paths"):
        source_paths = value.get(key)
        if isinstance(source_paths, dict):
            normalized[key] = {**fallback[key], **source_paths}
        else:
            normalized[key] = fallback[key]
    return normalized


def add_unexpected_receipt_keys(
    blockers: list[dict[str, Any]],
    obj: dict[str, Any],
    allowed_keys: frozenset[str],
    path: str,
) -> None:
    for key in sorted(obj):
        if key not in allowed_keys:
            key_path = f"{path}.{key}" if path else key
            add(
                blockers,
                "operator_approval_receipt_unexpected_key",
                "operator_approval_receipt_path",
                key_path=key_path,
            )


def receipt_string_values(value: Any, path: str = "") -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(path, value)]
    if isinstance(value, dict):
        values: list[tuple[str, str]] = []
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            values.extend(receipt_string_values(child, child_path))
        return values
    if isinstance(value, list):
        values = []
        for index, child in enumerate(value):
            values.extend(receipt_string_values(child, f"{path}[{index}]"))
        return values
    return []


def receipt_string_has_forbidden_authorization_claim(value: str) -> bool:
    for segment in re.split(r"(?:[\n.;]|\bbut\b|\bhowever\b)+", value):
        match = FORBIDDEN_RECEIPT_AUTHORIZATION_CLAIM_RE.search(segment)
        if match is None:
            continue
        prefix = segment[: match.start()]
        if RECEIPT_NEGATED_AUTHORIZATION_ACTION_RE.search(prefix) or RECEIPT_NEGATED_PREFIX_RE.search(prefix):
            continue
        return True
    return False


def iter_json_object_entries(value: Any, path: str = "") -> list[tuple[str, str, Any]]:
    if isinstance(value, dict):
        entries: list[tuple[str, str, Any]] = []
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            entries.append((child_path, key_text, child))
            entries.extend(iter_json_object_entries(child, child_path))
        return entries
    if isinstance(value, list):
        entries = []
        for index, child in enumerate(value):
            entries.extend(iter_json_object_entries(child, f"{path}[{index}]"))
        return entries
    return []


def preflight_flag_value_is_positive(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in PREFLIGHT_POSITIVE_TEXT_VALUES
    if isinstance(value, dict):
        return any(preflight_flag_value_is_positive(child) for child in value.values())
    if isinstance(value, list):
        return any(preflight_flag_value_is_positive(child) for child in value)
    return False


def normalized_preflight_flag_key(key: str) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key)
    separated = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", separated)
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


GENERIC_STATUS_CLAIM_KEYS = frozenset(("claim", "evidence", "readiness", "result", "state", "status"))
SPLIT_CLAIM_NAME_KEYS = frozenset(("alias", "claim", "field", "flag", "key", "name", "property"))
SPLIT_CLAIM_VALUE_KEYS = frozenset(("allowed", "enabled", "ready", "result", "state", "status", "value"))
SIDECAR_POSITIVE_ALIAS_KEYS = frozenset(
    (
        "accepted",
        "approved",
        "complete",
        "completed",
        "current_turn_authorized",
        "current_turn_runtime_authorized",
        "current_turn_scope_authorized",
        "current_turn_scope_ready",
        "runtime_authorized",
    )
)
SIDECAR_ALLOWED_READY_PATHS = frozenset(("ready",))
PROGRESS_ALIAS_DOMAIN_TOKENS = frozenset(
    (
        "claim",
        "complete",
        "completion",
        "dependency",
        "p0",
        "public",
        "readiness",
        "route",
        "runtime",
        "sdk",
        "v1",
    )
)


def preflight_flag_key_tokens(key: str) -> set[str]:
    return {token for token in normalized_preflight_flag_key(key).split("_") if token}


def forbidden_preflight_alias_key(key: str) -> bool:
    normalized = normalized_preflight_flag_key(key)
    tokens = preflight_flag_key_tokens(key)
    if normalized == "is_ready":
        return True
    if normalized in SIDECAR_POSITIVE_ALIAS_KEYS:
        return True
    if normalized == "progress":
        return True
    return "progress" in tokens and bool(tokens & PROGRESS_ALIAS_DOMAIN_TOKENS)


def forbidden_sidecar_positive_alias(key_path: str, key: str) -> bool:
    normalized = normalized_preflight_flag_key(key)
    if normalized == "ready":
        return key_path not in SIDECAR_ALLOWED_READY_PATHS
    return False


def split_preflight_alias_claim(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    names = [
        child
        for key, child in value.items()
        if normalized_preflight_flag_key(str(key)) in SPLIT_CLAIM_NAME_KEYS
        and isinstance(child, str)
    ]
    values = [
        child
        for key, child in value.items()
        if normalized_preflight_flag_key(str(key)) in SPLIT_CLAIM_VALUE_KEYS
    ]
    if not names:
        return False
    positive_value_present = not values or any(preflight_flag_value_is_positive(child) for child in values)
    if not positive_value_present:
        return False
    return any(
        normalized_preflight_flag_key(name) in PREFLIGHT_FORBIDDEN_POSITIVE_FLAG_KEYS
        or forbidden_preflight_alias_key(name)
        or POSITIVE_CAPABILITY_VALUE_RE.search(name) is not None
        for name in names
    )


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
    if notice_action.get("schema") != PLAYER_NOTICE_ACTION_SCHEMA:
        add(blockers, f"{reason_prefix}_player_notice_action_schema_mismatch", label)
    for key in sorted(REQUEST_PACK_PLAYER_NOTICE_FALSE_KEYS):
        if notice_action.get(key) is not False and key in notice_action:
            add(
                blockers,
                f"{reason_prefix}_player_notice_action_{key}_not_false",
                label,
                key_path=f"player_notice_action.{key}",
                actual=notice_action.get(key),
            )
    expected_action = expected_player_notice_action_values(user_policy)
    if expected_action is None:
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
    reason = NON_EVIDENCE_SIDECAR_SCHEMA_BLOCKERS.get(schema)
    if reason is None:
        return
    add(blockers, f"{reason_prefix}_{reason}", label, schema=schema)


def add_unexpected_json_sidecar_schema_blockers(
    payload: Any,
    blockers: list[dict[str, Any]],
    *,
    label: str,
) -> None:
    if not isinstance(payload, dict):
        return
    add_non_evidence_schema_blocker(
        payload,
        blockers,
        reason_prefix="unexpected_json_sidecar",
        label=label,
    )
    schema = payload.get("schema")
    if not isinstance(schema, str):
        return
    for pattern, reason in UNEXPECTED_JSON_SIDECAR_SCHEMA_BLOCKERS:
        if pattern.search(schema):
            add_once(blockers, reason, label, schema=schema)


def validate_unexpected_post_window_json_sidecars(
    sidecar_dir: Path,
    blockers: list[dict[str, Any]],
    *,
    post_window_replay: bool,
) -> None:
    if not post_window_replay:
        return
    try:
        entries = sorted(sidecar_dir.iterdir(), key=lambda entry: entry.name)
    except OSError as exc:
        add(
            blockers,
            "post_window_replay_sidecar_dir_unreadable",
            "manifest",
            path=str(sidecar_dir),
            detail=str(exc),
        )
        return

    for entry in entries:
        if entry.name in EXPECTED_POST_WINDOW_JSON_SIDECAR_NAMES:
            continue
        if entry.suffix.casefold() != ".json":
            continue

        label = f"unexpected_json_sidecar.{entry.name}"
        symlink = protected_paths.first_symlink_component(entry)
        if symlink is not None:
            add_once(blockers, "unexpected_json_sidecar_symlink", label, symlink=str(symlink))
            continue

        for pattern, reason in UNEXPECTED_JSON_SIDECAR_NAME_BLOCKERS:
            if pattern.search(entry.name):
                add_once(blockers, reason, label, path=str(entry))

        if not entry.is_file():
            add_once(blockers, "unexpected_json_sidecar_not_file", label, path=str(entry))
            continue
        try:
            payload = json.loads(entry.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        except OSError as exc:
            add_once(blockers, "unexpected_json_sidecar_unreadable", label, path=str(entry), detail=str(exc))
            continue
        add_unexpected_json_sidecar_schema_blockers(payload, blockers, label=label)


def add_request_pack_current_schema_blockers(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    missing = sorted(EXPECTED_REQUEST_PACK_TOP_LEVEL_KEYS - set(payload))
    for key in missing:
        add(
            blockers,
            "request_pack_current_schema_key_missing",
            "request_pack_path",
            key_path=key,
        )
    unexpected = sorted(set(payload) - EXPECTED_REQUEST_PACK_TOP_LEVEL_KEYS)
    for key in unexpected:
        add(
            blockers,
            "request_pack_unexpected_key",
            "request_pack_path",
            key_path=key,
        )


def validate_player_notice_action_contract(
    value: Any,
    *,
    user_policy: Any,
    notice_path: Any,
    blockers: list[dict[str, Any]],
    label: str,
    reason_prefix: str,
) -> None:
    action_label = f"{label}.player_notice_action"
    if not isinstance(value, dict):
        add(blockers, f"{reason_prefix}_player_notice_action_missing", action_label, value=value)
        return

    if value.get("schema") != PLAYER_NOTICE_ACTION_SCHEMA:
        add(
            blockers,
            f"{reason_prefix}_player_notice_action_schema_mismatch",
            f"{action_label}.schema",
            expected=PLAYER_NOTICE_ACTION_SCHEMA,
            actual=value.get("schema"),
        )

    expected_required = user_policy == "operator_approved_beta_users"
    if user_policy not in {"no_regular_users", "operator_approved_beta_users"}:
        add(
            blockers,
            f"{reason_prefix}_player_notice_action_user_policy_invalid",
            action_label,
            actual=user_policy,
        )

    expected_notice_path = APPROVED_BETA_NOTICE_PATH if expected_required else "not_applicable"
    if value.get("notice_path") != notice_path:
        add(
            blockers,
            f"{reason_prefix}_player_notice_action_notice_path_drift",
            f"{action_label}.notice_path",
            expected=notice_path,
            actual=value.get("notice_path"),
        )
    if value.get("notice_path") != expected_notice_path:
        add(
            blockers,
            f"{reason_prefix}_player_notice_action_notice_path_mismatch",
            f"{action_label}.notice_path",
            expected=expected_notice_path,
            actual=value.get("notice_path"),
        )

    expected = {
        "required": expected_required,
        "approved_notice_path_must_be_named": expected_required,
        "dry_run_required_before_send": expected_required,
        "real_notice_send_required_before_activation": expected_required,
        "send_performed_by_request_pack": False,
        "request_pack_authorizes_discord": False,
        "activation_allowed_before_notice_sent": not expected_required,
        "evidence_required": (
            "dry_run_output_and_send_confirmation_reference" if expected_required else "not_applicable"
        ),
        "activation_blocker": (
            "approved_dry_run_checked_beta_testers_notice_sent"
            if expected_required
            else "no_player_notice_required"
        ),
        "non_authorization": PLAYER_NOTICE_ACTION_NON_AUTHORIZATION,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            add(
                blockers,
                f"{reason_prefix}_player_notice_action_{key}_mismatch",
                f"{action_label}.{key}",
                expected=expected_value,
                actual=value.get(key),
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


def add_request_pack_non_authorization_blockers(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    authorization_flags = payload.get("authorization_flags")
    if not isinstance(authorization_flags, dict):
        add(blockers, "request_pack_authorization_flags_missing", "request_pack_path")
    else:
        if authorization_flags != AUTHORIZATION_FLAGS:
            add(
                blockers,
                "request_pack_authorization_flags_mismatch",
                "request_pack_path",
                expected=AUTHORIZATION_FLAGS,
                actual=authorization_flags,
            )
        for key in sorted(REQUEST_PACK_REQUIRED_FALSE_AUTHORIZATION_FLAGS):
            if authorization_flags.get(key) is not False:
                add(
                    blockers,
                    f"request_pack_authorization_flag_{key}_not_false",
                    "request_pack_path",
                    key_path=f"authorization_flags.{key}",
                    actual=authorization_flags.get(key),
                )
    if payload.get("non_claims") != NON_CLAIMS:
        add(blockers, "request_pack_non_claims_mismatch", "request_pack_path")

    validate_player_notice_action_contract(
        payload.get("player_notice_action"),
        user_policy=payload.get("user_policy"),
        notice_path=payload.get("notice_path"),
        blockers=blockers,
        label="request_pack_path",
        reason_prefix="request_pack",
    )

    validate_player_presence_safety_contract(
        payload.get("player_presence_safety"),
        payload=payload,
        blockers=blockers,
        label="request_pack_path",
        reason_prefix="request_pack",
    )

    passive_wait = payload.get("passive_wait_boundary")
    if not isinstance(passive_wait, dict):
        add(blockers, "request_pack_passive_wait_boundary_missing", "request_pack_path")
    else:
        standing_request = payload.get("approval_required") == STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT
        if passive_wait.get("schema") != PASSIVE_WAIT_BOUNDARY_SCHEMA:
            add(blockers, "request_pack_passive_wait_boundary_schema_mismatch", "request_pack_path")
        for key in sorted(REQUEST_PACK_PASSIVE_WAIT_FALSE_KEYS):
            if passive_wait.get(key) is not False:
                add(
                    blockers,
                    f"request_pack_passive_wait_boundary_{key}_not_false",
                    "request_pack_path",
                    key_path=f"passive_wait_boundary.{key}",
                    actual=passive_wait.get(key),
                )
        if standing_request:
            if passive_wait.get("active_followup_requires_fresh_exact_current_turn_scope") is not False:
                add(
                    blockers,
                    "request_pack_passive_wait_boundary_active_followup_requires_fresh_exact_current_turn_scope_not_false_for_standing_authority",
                    "request_pack_path",
                )
            if passive_wait.get("active_followup_requires_recorded_standing_launch_authority") is not True:
                add(
                    blockers,
                    "request_pack_passive_wait_boundary_active_followup_requires_recorded_standing_launch_authority_not_true",
                    "request_pack_path",
                )
        else:
            if passive_wait.get("active_followup_requires_fresh_exact_current_turn_scope") is not True:
                add(
                    blockers,
                    "request_pack_passive_wait_boundary_active_followup_requires_fresh_exact_current_turn_scope_not_true",
                    "request_pack_path",
                )
            if passive_wait.get("active_followup_requires_recorded_standing_launch_authority") is not False:
                add(
                    blockers,
                    "request_pack_passive_wait_boundary_active_followup_requires_recorded_standing_launch_authority_not_false_for_current_turn",
                    "request_pack_path",
                )

    deployment = payload.get("deployment_intent")
    if isinstance(deployment, dict):
        for key in sorted(REQUEST_PACK_DEPLOYMENT_INTENT_FALSE_KEYS):
            if deployment.get(key) is not False:
                add(
                    blockers,
                    f"request_pack_deployment_intent_{key}_not_false",
                    "request_pack_path",
                    key_path=f"deployment_intent.{key}",
                    actual=deployment.get(key),
                )
        if deployment.get("request_only") is not True:
            add(
                blockers,
                "request_pack_deployment_intent_request_only_not_true",
                "request_pack_path",
            )
    else:
        add(blockers, "request_pack_deployment_intent_missing", "request_pack_path")

    planned_build = payload.get("planned_obelisk_build_identity")
    if not isinstance(planned_build, dict):
        add(blockers, "request_pack_planned_obelisk_build_identity_missing", "request_pack_path")
    elif planned_build.get("schema") != PLANNED_OBELISK_BUILD_IDENTITY_SCHEMA:
        add(blockers, "request_pack_planned_obelisk_build_identity_schema_mismatch", "request_pack_path")

    for key_path, key, value in iter_json_object_entries(payload):
        if (
            normalized_preflight_flag_key(key) in PREFLIGHT_FORBIDDEN_POSITIVE_FLAG_KEYS
            and preflight_flag_value_is_positive(value)
        ):
            add(
                blockers,
                f"request_pack_{normalized_preflight_flag_key(key)}_not_false",
                "request_pack_path",
                key_path=key_path,
                actual=value,
            )
        if forbidden_preflight_alias_key(key) and preflight_flag_value_is_positive(value):
            add(
                blockers,
                f"request_pack_{normalized_preflight_flag_key(key)}_not_false",
                "request_pack_path",
                key_path=key_path,
                actual=value,
            )
        if forbidden_sidecar_positive_alias(key_path, key) and preflight_flag_value_is_positive(value):
            add(
                blockers,
                f"request_pack_{normalized_preflight_flag_key(key)}_not_false",
                "request_pack_path",
                key_path=key_path,
                actual=value,
            )
        if (
            normalized_preflight_flag_key(key) in GENERIC_STATUS_CLAIM_KEYS
            and preflight_flag_value_is_positive(value)
        ):
            add(
                blockers,
                f"request_pack_{normalized_preflight_flag_key(key)}_not_false",
                "request_pack_path",
                key_path=key_path,
                actual=value,
            )
        if split_preflight_alias_claim(value):
            add(
                blockers,
                "request_pack_split_authorization_or_readiness_claim",
                "request_pack_path",
                key_path=key_path,
                actual=value,
            )


def validate_preflight_non_authorization_claims(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    path_key: str,
) -> None:
    for key in sorted(PREFLIGHT_REQUIRED_FALSE_AUTHORIZATION_FLAGS):
        if payload.get(key) is not False:
            add(
                blockers,
                f"{path_key}_{key}_missing_or_not_false",
                path_key,
                key_path=key,
                actual=payload.get(key),
            )
    if payload.get("non_claim") != EXPECTED_PREFLIGHT_NON_CLAIM:
        add(
            blockers,
            f"{path_key}_non_claim_mismatch",
            path_key,
            expected=EXPECTED_PREFLIGHT_NON_CLAIM,
            actual=payload.get("non_claim"),
        )
    for key_path, key, value in iter_json_object_entries(payload):
        if (
            normalized_preflight_flag_key(key) in PREFLIGHT_FORBIDDEN_POSITIVE_FLAG_KEYS
            and preflight_flag_value_is_positive(value)
        ):
            add(
                blockers,
                f"{path_key}_{normalized_preflight_flag_key(key)}_not_false",
                path_key,
                key_path=key_path,
                actual=value,
            )
        if forbidden_preflight_alias_key(key) and preflight_flag_value_is_positive(value):
            add(
                blockers,
                f"{path_key}_{normalized_preflight_flag_key(key)}_not_false",
                path_key,
                key_path=key_path,
                actual=value,
            )
        if forbidden_sidecar_positive_alias(key_path, key) and preflight_flag_value_is_positive(value):
            add(
                blockers,
                f"{path_key}_{normalized_preflight_flag_key(key)}_not_false",
                path_key,
                key_path=key_path,
                actual=value,
            )
        if (
            normalized_preflight_flag_key(key) in GENERIC_STATUS_CLAIM_KEYS
            and preflight_flag_value_is_positive(value)
        ):
            add(
                blockers,
                f"{path_key}_{normalized_preflight_flag_key(key)}_not_false",
                path_key,
                key_path=key_path,
                actual=value,
            )
        if split_preflight_alias_claim(value):
            add(
                blockers,
                f"{path_key}_split_authorization_or_readiness_claim",
                path_key,
                key_path=key_path,
                actual=value,
            )
    for string_path, value in receipt_string_values(payload):
        if (
            receipt_string_has_forbidden_authorization_claim(value)
            or POSITIVE_CAPABILITY_VALUE_RE.search(value) is not None
        ):
            add(
                blockers,
                f"{path_key}_forbidden_authorization_claim",
                path_key,
                key_path=string_path,
            )


def validate_operator_approval_receipt_shape(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    add_unexpected_receipt_keys(
        blockers,
        payload,
        EXPECTED_OPERATOR_APPROVAL_RECEIPT_TOP_LEVEL_KEYS,
        "",
    )
    scope = payload.get("approval_scope")
    if isinstance(scope, dict):
        add_unexpected_receipt_keys(
            blockers,
            scope,
            EXPECTED_OPERATOR_APPROVAL_RECEIPT_SCOPE_KEYS,
            "approval_scope",
        )
    bound_request = payload.get("bound_request_pack")
    if isinstance(bound_request, dict):
        add_unexpected_receipt_keys(
            blockers,
            bound_request,
            EXPECTED_OPERATOR_APPROVAL_RECEIPT_BOUND_REQUEST_KEYS,
            "bound_request_pack",
        )
        receipt_target = bound_request.get("target")
        if isinstance(receipt_target, dict):
            add_unexpected_receipt_keys(
                blockers,
                receipt_target,
                EXPECTED_OPERATOR_APPROVAL_RECEIPT_TARGET_KEYS,
                "bound_request_pack.target",
            )
        receipt_window = bound_request.get("approved_window")
        if isinstance(receipt_window, dict):
            add_unexpected_receipt_keys(
                blockers,
                receipt_window,
                EXPECTED_OPERATOR_APPROVAL_RECEIPT_WINDOW_KEYS,
                "bound_request_pack.approved_window",
            )
        rollback = bound_request.get("rollback")
        if isinstance(rollback, dict):
            add_unexpected_receipt_keys(
                blockers,
                rollback,
                EXPECTED_OPERATOR_APPROVAL_RECEIPT_ROLLBACK_KEYS,
                "bound_request_pack.rollback",
            )
    bound = payload.get("bound_artifacts")
    if isinstance(bound, dict):
        add_unexpected_receipt_keys(
            blockers,
            bound,
            EXPECTED_OPERATOR_APPROVAL_RECEIPT_BOUND_ARTIFACTS_KEYS,
            "bound_artifacts",
        )
        for key, artifact in bound.items():
            if isinstance(artifact, dict):
                add_unexpected_receipt_keys(
                    blockers,
                    artifact,
                    EXPECTED_OPERATOR_APPROVAL_RECEIPT_ARTIFACT_KEYS,
                    f"bound_artifacts.{key}",
                )
    completion = payload.get("operator_completion")
    if isinstance(completion, dict):
        add_unexpected_receipt_keys(
            blockers,
            completion,
            EXPECTED_OPERATOR_APPROVAL_RECEIPT_COMPLETION_KEYS,
            "operator_completion",
        )
    flags = payload.get("non_authorization_flags")
    if isinstance(flags, dict):
        add_unexpected_receipt_keys(
            blockers,
            flags,
            EXPECTED_OPERATOR_APPROVAL_RECEIPT_FLAG_KEYS,
            "non_authorization_flags",
        )


def validate_operator_approval_receipt(
    fields: dict[str, str],
    manifest_path: Path,
    target: Target,
    blockers: list[dict[str, Any]],
) -> None:
    receipt_text = fields.get("operator_approval_receipt_path")
    if not receipt_text:
        return
    receipt_path = manifest_relative_path(receipt_text, manifest_path)
    status = protected_paths.protected_path_status(
        receipt_path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if not add_unreadable_sidecar_status(
        blockers,
        status,
        label="operator_approval_receipt_path",
        protected_reason="operator_approval_receipt_path_under_protected_server_root",
        unapproved_reason="operator_approval_receipt_path_not_under_approved_offline_workspace",
        missing_reason="operator_approval_receipt_path_file_missing",
    ):
        return
    try:
        payload = json.loads(status.resolved.read_text(encoding="utf-8"))
    except OSError as exc:
        add(blockers, "operator_approval_receipt_unreadable", "operator_approval_receipt_path", detail=str(exc))
        return
    except json.JSONDecodeError as exc:
        add(blockers, "operator_approval_receipt_json_invalid", "operator_approval_receipt_path", detail=str(exc))
        return
    if not isinstance(payload, dict):
        add(blockers, "operator_approval_receipt_not_object", "operator_approval_receipt_path")
        return

    add_non_evidence_schema_blocker(
        payload,
        blockers,
        reason_prefix="operator_approval_receipt",
        label="operator_approval_receipt_path",
    )
    validate_operator_approval_receipt_shape(payload, blockers)
    for string_path, value in receipt_string_values(payload):
        if receipt_string_has_forbidden_authorization_claim(value):
            add(
                blockers,
                "operator_approval_receipt_forbidden_authorization_claim",
                "operator_approval_receipt_path",
                key_path=string_path,
            )
    if payload.get("non_claims") != EXPECTED_OPERATOR_APPROVAL_RECEIPT_NON_CLAIMS:
        add(blockers, "operator_approval_receipt_non_claims_mismatch", "operator_approval_receipt_path")

    if payload.get("schema") != APPROVAL_RECEIPT_SCHEMA:
        add(blockers, "operator_approval_receipt_schema_mismatch", "operator_approval_receipt_path")
    if payload.get("status") != "completed_operator_receipt":
        add(blockers, "operator_approval_receipt_status_not_completed", "operator_approval_receipt_path")
    if payload.get("receipt_completed") is not True:
        add(blockers, "operator_approval_receipt_receipt_completed_not_true", "operator_approval_receipt_path")
    completion = payload.get("operator_completion")
    if not isinstance(completion, dict):
        add(blockers, "operator_approval_receipt_operator_completion_missing", "operator_approval_receipt_path")
        completion = {}
    approved_at = completion.get("approval_recorded_at_utc")
    approved_at_dt = None
    if not isinstance(approved_at, str) or UTC_TIMESTAMP_RE.fullmatch(approved_at) is None:
        add(blockers, "operator_approval_receipt_approved_at_utc_invalid", "operator_approval_receipt_path")
    else:
        approved_at_dt = parse_utc_timestamp(approved_at)
        if approved_at_dt is None:
            add(blockers, "operator_approval_receipt_approved_at_utc_invalid", "operator_approval_receipt_path")
    approved_by_role = completion.get("approved_by_role")
    if not isinstance(approved_by_role, str) or not approved_by_role.strip():
        add(blockers, "operator_approval_receipt_approved_by_role_invalid", "operator_approval_receipt_path")
    elif approved_by_role not in APPROVED_OPERATOR_ROLES:
        add(
            blockers,
            "operator_approval_receipt_approved_by_role_unapproved",
            "operator_approval_receipt_path",
            accepted_roles=sorted(APPROVED_OPERATOR_ROLES),
            actual=approved_by_role,
        )
    approval_source = completion.get("approval_source")
    if approval_source not in (APPROVAL_SOURCE_CURRENT_TURN, APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY):
        add(blockers, "operator_approval_receipt_approval_source_mismatch", "operator_approval_receipt_path")
    standing_receipt = approval_source == APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY
    if standing_receipt:
        if payload.get("operator_current_turn_approval_recorded") is not False:
            add(
                blockers,
                "operator_approval_receipt_current_turn_approval_not_false_for_standing_authority",
                "operator_approval_receipt_path",
            )
        if payload.get("standing_launch_authority_recorded") is not True:
            add(blockers, "operator_approval_receipt_standing_launch_authority_not_recorded", "operator_approval_receipt_path")
        if payload.get("standing_launch_authority_satisfies_operator_approval") is not True:
            add(blockers, "operator_approval_receipt_standing_launch_authority_not_bound", "operator_approval_receipt_path")
    else:
        if payload.get("operator_current_turn_approval_recorded") is not True:
            add(blockers, "operator_approval_receipt_current_turn_approval_not_recorded", "operator_approval_receipt_path")
        if payload.get("standing_launch_authority_recorded") is not False:
            add(
                blockers,
                "operator_approval_receipt_standing_launch_authority_not_false_for_current_turn",
                "operator_approval_receipt_path",
            )
        if payload.get("standing_launch_authority_satisfies_operator_approval") is not False:
            add(
                blockers,
                "operator_approval_receipt_standing_launch_authority_bound_for_current_turn",
                "operator_approval_receipt_path",
            )
    expected_attestation = (
        APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY
        if standing_receipt
        else APPROVAL_ATTESTATION_CURRENT_TURN
    )
    if completion.get("attestation") != expected_attestation:
        add(blockers, "operator_approval_receipt_attestation_mismatch", "operator_approval_receipt_path")

    scope = payload.get("approval_scope")
    if not isinstance(scope, dict):
        add(blockers, "operator_approval_receipt_scope_missing", "operator_approval_receipt_path")
        scope = {}
    if scope.get("scope_type") != "exact_bound_player_principal_lifecycle_window_only":
        add(blockers, "operator_approval_receipt_scope_type_mismatch", "operator_approval_receipt_path")
    if standing_receipt:
        if scope.get("standing_approval") is not True:
            add(blockers, "operator_approval_receipt_scope_standing_approval_not_true", "operator_approval_receipt_path")
    elif scope.get("standing_approval") is not False:
        add(blockers, "operator_approval_receipt_scope_standing_approval_not_false", "operator_approval_receipt_path")
    for key in ("reusable", "future_windows_authorized", "scope_expansion_authorized", "unbound_artifacts_authorized"):
        if scope.get(key) is not False:
            add(blockers, f"operator_approval_receipt_scope_{key}_not_false", "operator_approval_receipt_path")

    bound_request = payload.get("bound_request_pack")
    if not isinstance(bound_request, dict):
        add(blockers, "operator_approval_receipt_bound_request_pack_missing", "operator_approval_receipt_path")
        bound_request = {}
    request_payload: dict[str, Any] = {}
    request_path_text = fields.get("request_pack_path")
    if request_path_text:
        request_path = manifest_relative_path(request_path_text, manifest_path)
        request_status = protected_paths.protected_path_status(
            request_path,
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        )
        if content_readable_status(request_status):
            try:
                loaded_request = json.loads(request_status.resolved.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                loaded_request = None
            if isinstance(loaded_request, dict):
                request_payload = loaded_request
        else:
            add_unreadable_sidecar_status(
                blockers,
                request_status,
                label="request_pack_path",
                protected_reason="operator_approval_receipt_request_pack_under_protected_server_root",
                unapproved_reason="operator_approval_receipt_request_pack_not_under_approved_offline_workspace",
                missing_reason="operator_approval_receipt_request_pack_file_missing",
            )
    if bound_request.get("run_id") != fields.get("run_id"):
        add(blockers, "operator_approval_receipt_run_id_mismatch", "operator_approval_receipt_path")
    prepared_at = request_payload.get("prepared_at_utc") if request_payload else None
    prepared_at_dt = None
    if not isinstance(prepared_at, str) or UTC_TIMESTAMP_RE.fullmatch(prepared_at) is None:
        add(blockers, "operator_approval_receipt_prepared_at_utc_invalid", "operator_approval_receipt_path")
    else:
        prepared_at_dt = parse_utc_timestamp(prepared_at)
        if prepared_at_dt is None:
            add(blockers, "operator_approval_receipt_prepared_at_utc_invalid", "operator_approval_receipt_path")
    if request_payload and bound_request.get("prepared_at_utc") != prepared_at:
        add(blockers, "operator_approval_receipt_prepared_at_utc_mismatch", "operator_approval_receipt_path")
    approved_window_start = (
        request_payload.get("approved_window", {}).get("start_utc")
        if isinstance(request_payload.get("approved_window"), dict)
        else None
    )
    approved_window_start_dt = (
        parse_utc_timestamp(approved_window_start)
        if isinstance(approved_window_start, str) and UTC_TIMESTAMP_RE.fullmatch(approved_window_start)
        else None
    )
    if approved_at_dt is not None and prepared_at_dt is not None and approved_at_dt <= prepared_at_dt:
        add(
            blockers,
            "operator_approval_receipt_approved_before_request_prepared",
            "operator_approval_receipt_path",
            prepared_at_utc=prepared_at,
            approval_recorded_at_utc=approved_at,
        )
    if approved_at_dt is not None and approved_window_start_dt is not None and approved_at_dt >= approved_window_start_dt:
        add(
            blockers,
            "operator_approval_receipt_approved_at_or_after_window_start",
            "operator_approval_receipt_path",
            approved_window_start_utc=approved_window_start,
            approval_recorded_at_utc=approved_at,
        )
    if (
        approved_at_dt is not None
        and approved_window_start_dt is not None
        and approved_at_dt < approved_window_start_dt
        and (approved_window_start_dt - approved_at_dt).total_seconds() > MAX_OPERATOR_APPROVAL_LEAD_SECONDS
    ):
        add(
            blockers,
            "operator_approval_receipt_approved_too_far_before_window_start",
            "operator_approval_receipt_path",
            max_seconds=MAX_OPERATOR_APPROVAL_LEAD_SECONDS,
            approved_window_start_utc=approved_window_start,
            approval_recorded_at_utc=approved_at,
        )
    if bound_request.get("obelisk_commit") != fields.get("obelisk_commit"):
        add(blockers, "operator_approval_receipt_obelisk_commit_mismatch", "operator_approval_receipt_path")
    if request_payload and bound_request.get("planned_obelisk_build_identity") != request_payload.get(
        "planned_obelisk_build_identity"
    ):
        add(
            blockers,
            "operator_approval_receipt_planned_obelisk_build_identity_mismatch",
            "operator_approval_receipt_path",
        )
    if bound_request.get("ark_binary_sha256") != EXPECTED_BINARY_SHA256:
        add(blockers, "operator_approval_receipt_ark_binary_sha256_mismatch", "operator_approval_receipt_path")
    if bound_request.get("server_binary_path") != EXPECTED_SERVER_BINARY_PATH:
        add(blockers, "operator_approval_receipt_server_binary_path_mismatch", "operator_approval_receipt_path")
    expected_copied_log_path = (
        str(
            protected_paths.protected_path_status(
                manifest_relative_path(fields["copied_log_path"], manifest_path),
                protected_root=SERVER_ROOT,
                approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
            ).resolved
        )
        if fields.get("copied_log_path")
        else None
    )
    if expected_copied_log_path and bound_request.get("copied_log_path") != expected_copied_log_path:
        add(blockers, "operator_approval_receipt_copied_log_path_mismatch", "operator_approval_receipt_path")
    expected_manifest_path = str(
        protected_paths.protected_path_status(
            manifest_path,
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        ).resolved
    )
    if bound_request.get("window_manifest_path") != expected_manifest_path:
        add(blockers, "operator_approval_receipt_window_manifest_path_mismatch", "operator_approval_receipt_path")
    for key in (
        "restart_expectation",
        "final_posture",
        "user_policy",
        "notice_path",
        "player_notice_action",
        "player_presence_safety",
    ):
        if request_payload and bound_request.get(key) != request_payload.get(key):
            add(blockers, f"operator_approval_receipt_{key}_mismatch", "operator_approval_receipt_path")
    validate_player_presence_safety_contract(
        bound_request.get("player_presence_safety"),
        payload=bound_request,
        blockers=blockers,
        label="operator_approval_receipt_path",
        reason_prefix="operator_approval_receipt_bound_request",
    )
    if request_payload and normalized_receipt_rollback(bound_request.get("rollback"), target) != normalized_receipt_rollback(
        request_payload.get("rollback"),
        target,
    ):
        add(blockers, "operator_approval_receipt_rollback_mismatch", "operator_approval_receipt_path")

    receipt_target = bound_request.get("target")
    if not isinstance(receipt_target, dict):
        add(blockers, "operator_approval_receipt_target_missing", "operator_approval_receipt_path")
    else:
        if receipt_target.get("instance") != target.instance:
            add(blockers, "operator_approval_receipt_instance_mismatch", "operator_approval_receipt_path")
        if receipt_target.get("map") != target.map_name:
            add(blockers, "operator_approval_receipt_map_mismatch", "operator_approval_receipt_path")

    receipt_window = bound_request.get("approved_window")
    if not isinstance(receipt_window, dict):
        add(blockers, "operator_approval_receipt_window_missing", "operator_approval_receipt_path")
    else:
        if receipt_window.get("start_utc") != fields.get("approved_window_start_utc"):
            add(blockers, "operator_approval_receipt_window_start_mismatch", "operator_approval_receipt_path")
        if receipt_window.get("end_utc") != fields.get("approved_window_end_utc"):
            add(blockers, "operator_approval_receipt_window_end_mismatch", "operator_approval_receipt_path")

    bound = payload.get("bound_artifacts")
    if not isinstance(bound, dict):
        add(blockers, "operator_approval_receipt_bound_artifacts_missing", "operator_approval_receipt_path")
        return
    env_path_text = fields.get("observer_env_path")
    expected_operator_request = None
    request_status = None
    env_status = None
    if request_path_text:
        request_path = manifest_relative_path(request_path_text, manifest_path)
        request_status = protected_paths.protected_path_status(
            request_path,
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        )
        operator_request = request_status.resolved.parent / "operator-approval-request.md"
        if content_readable_status(request_status):
            operator_request_status = protected_paths.protected_path_status(
                operator_request,
                protected_root=SERVER_ROOT,
                approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
            )
            if add_unreadable_sidecar_status(
                blockers,
                operator_request_status,
                label="operator_approval_receipt_path",
                protected_reason="operator_approval_request_sidecar_under_protected_server_root",
                unapproved_reason="operator_approval_request_sidecar_not_under_approved_offline_workspace",
                missing_reason="operator_approval_request_sidecar_missing",
            ):
                expected_operator_request = bound_artifact_from_status(operator_request_status)
        else:
            add_unreadable_sidecar_status(
                blockers,
                request_status,
                label="request_pack_path",
                protected_reason="operator_approval_receipt_request_pack_under_protected_server_root",
                unapproved_reason="operator_approval_receipt_request_pack_not_under_approved_offline_workspace",
                missing_reason="operator_approval_receipt_request_pack_file_missing",
            )
    if env_path_text:
        env_status = protected_paths.protected_path_status(
            manifest_relative_path(env_path_text, manifest_path),
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        )
    expected_request = None
    if request_status and content_readable_status(request_status):
        expected_request = bound_artifact_from_status(request_status)
    expected_env = None
    if env_status:
        if add_unreadable_sidecar_status(
            blockers,
            env_status,
            label="observer_env_path",
            protected_reason="operator_approval_receipt_observer_env_under_protected_server_root",
            unapproved_reason="operator_approval_receipt_observer_env_not_under_approved_offline_workspace",
            missing_reason="operator_approval_receipt_observer_env_file_missing",
        ):
            expected_env = bound_artifact_from_status(env_status)
    for key, expected in (
        ("window_request_json", expected_request),
        ("observer_window_env", expected_env),
        ("operator_approval_request_md", expected_operator_request),
    ):
        actual = bound.get(key)
        if expected is None:
            continue
        if actual != expected:
            add(blockers, f"operator_approval_receipt_{key}_artifact_mismatch", "operator_approval_receipt_path", expected=expected, actual=actual)

    if (
        request_status
        and env_status
        and content_readable_status(request_status)
        and content_readable_status(env_status)
        and expected_operator_request is not None
    ):
        expected_digest = request_pack_digest(
            request_json_path=request_status.resolved,
            env_path=env_status.resolved,
            request_md_path=Path(expected_operator_request["path"]),
        )
        if payload.get("request_pack_digest") != expected_digest:
            add(
                blockers,
                "operator_approval_receipt_digest_mismatch",
                "operator_approval_receipt_path",
                expected=expected_digest,
                actual=payload.get("request_pack_digest"),
            )

    flags = payload.get("non_authorization_flags")
    if not isinstance(flags, dict):
        add(blockers, "operator_approval_receipt_non_authorization_flags_missing", "operator_approval_receipt_path")
        flags = {}
    for key in EXPECTED_OPERATOR_APPROVAL_RECEIPT_FLAG_KEYS:
        if flags.get(key) is not False:
            add(blockers, f"operator_approval_receipt_{key}_not_false", "operator_approval_receipt_path")


def validate_preflight_content(
    fields: dict[str, str],
    manifest_path: Path,
    blockers: list[dict[str, Any]],
    *,
    path_key: str,
    expected_mode: str,
    target: Target,
) -> None:
    path_text = fields.get(path_key)
    if not path_text or not target.instance:
        return
    path = manifest_relative_path(path_text, manifest_path)
    status = protected_paths.protected_path_status(
        path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if not add_unreadable_sidecar_status(
        blockers,
        status,
        label=path_key,
        protected_reason=f"{path_key}_under_protected_server_root",
        unapproved_reason=f"{path_key}_not_under_approved_offline_workspace",
        missing_reason=f"{path_key}_file_missing",
    ):
        return
    try:
        payload = json.loads(status.resolved.read_text(encoding="utf-8"))
    except OSError as exc:
        add(blockers, f"{path_key}_unreadable", path_key, detail=str(exc))
        return
    except json.JSONDecodeError as exc:
        add(blockers, f"{path_key}_json_invalid", path_key, detail=str(exc))
        return
    if not isinstance(payload, dict):
        add(blockers, f"{path_key}_not_object", path_key)
        return

    add_non_evidence_schema_blocker(payload, blockers, reason_prefix=path_key, label=path_key)
    validate_preflight_non_authorization_claims(payload, blockers, path_key=path_key)

    if payload.get("schema") != PREFLIGHT_SCHEMA:
        add(blockers, f"{path_key}_schema_mismatch", path_key, expected=PREFLIGHT_SCHEMA, actual=payload.get("schema"))
    if payload.get("ready") is not True:
        add(blockers, f"{path_key}_ready_not_true", path_key)
    if payload.get("posture_check") != "accepted":
        add(blockers, f"{path_key}_posture_check_not_accepted", path_key)
    if payload.get("offline_only") is not False:
        add(blockers, f"{path_key}_offline_only_not_false", path_key, actual=payload.get("offline_only"))
    if payload.get("allow_stopped") is not False:
        add(blockers, f"{path_key}_allow_stopped_not_false", path_key, actual=payload.get("allow_stopped"))
    if payload.get("mode") != expected_mode:
        add(blockers, f"{path_key}_mode_mismatch", path_key, expected=expected_mode, actual=payload.get("mode"))
    if payload.get("instance") != target.instance:
        add(blockers, f"{path_key}_instance_mismatch", path_key, expected=target.instance, actual=payload.get("instance"))
    if payload.get("run_id") != fields.get("run_id"):
        add(blockers, f"{path_key}_run_id_mismatch", path_key, expected=fields.get("run_id"), actual=payload.get("run_id"))
    if payload.get("map") != target.map_name:
        add(blockers, f"{path_key}_map_mismatch", path_key, expected=target.map_name, actual=payload.get("map"))

    preflight_target = payload.get("target")
    if not isinstance(preflight_target, dict):
        add(blockers, f"{path_key}_target_missing", path_key)
    else:
        if preflight_target.get("instance") != target.instance:
            add(
                blockers,
                f"{path_key}_target_instance_mismatch",
                path_key,
                expected=target.instance,
                actual=preflight_target.get("instance"),
            )
        if preflight_target.get("map") != target.map_name:
            add(
                blockers,
                f"{path_key}_target_map_mismatch",
                path_key,
                expected=target.map_name,
                actual=preflight_target.get("map"),
            )

    checked_at_utc = payload.get("checked_at_utc")
    if not isinstance(checked_at_utc, str) or UTC_TIMESTAMP_RE.fullmatch(checked_at_utc) is None:
        add(blockers, f"{path_key}_checked_at_utc_invalid", path_key, actual=checked_at_utc)
    elif parse_utc_timestamp(checked_at_utc) is None:
        add(blockers, f"{path_key}_checked_at_utc_invalid", path_key, actual=checked_at_utc)

    manifest_status = protected_paths.protected_path_status(
        manifest_path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    expected_manifest_path = str(manifest_status.resolved)
    if payload.get("window_manifest_path") != expected_manifest_path:
        add(
            blockers,
            f"{path_key}_window_manifest_path_mismatch",
            path_key,
            expected=expected_manifest_path,
            actual=payload.get("window_manifest_path"),
        )

    copied_log_text = fields.get("copied_log_path")
    if copied_log_text:
        copied_log_status = protected_paths.protected_path_status(
            manifest_relative_path(copied_log_text, manifest_path),
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        )
        expected_copied_log_path = str(copied_log_status.resolved)
        expected_evidence_dir = str(copied_log_status.resolved.parent)
        if payload.get("copied_log_path") != expected_copied_log_path:
            add(
                blockers,
                f"{path_key}_copied_log_path_mismatch",
                path_key,
                expected=expected_copied_log_path,
                actual=payload.get("copied_log_path"),
            )
        if payload.get("copied_evidence_dir") != expected_evidence_dir:
            add(
                blockers,
                f"{path_key}_copied_evidence_dir_mismatch",
                path_key,
                expected=expected_evidence_dir,
                actual=payload.get("copied_evidence_dir"),
            )

    server_binary = payload.get("server_binary")
    if not isinstance(server_binary, dict):
        add(blockers, f"{path_key}_server_binary_missing", path_key)
    else:
        if server_binary.get("path") != EXPECTED_SERVER_BINARY_PATH:
            add(
                blockers,
                f"{path_key}_server_binary_path_mismatch",
                path_key,
                expected=EXPECTED_SERVER_BINARY_PATH,
                actual=server_binary.get("path"),
            )
        if server_binary.get("sha256") != EXPECTED_BINARY_SHA256:
            add(
                blockers,
                f"{path_key}_binary_sha256_mismatch",
                path_key,
                expected=EXPECTED_BINARY_SHA256,
                actual=server_binary.get("sha256"),
            )

    if payload.get("obelisk_root") != EXPECTED_OBELISK_ROOT:
        add(
            blockers,
            f"{path_key}_obelisk_root_mismatch",
            path_key,
            expected=EXPECTED_OBELISK_ROOT,
            actual=payload.get("obelisk_root"),
        )

    installed_wrapper = payload.get("installed_wrapper")
    if not isinstance(installed_wrapper, dict):
        add(blockers, f"{path_key}_installed_wrapper_missing", path_key)
    else:
        if installed_wrapper.get("path") != EXPECTED_INSTALLED_WRAPPER_PATH:
            add(
                blockers,
                f"{path_key}_installed_wrapper_path_mismatch",
                path_key,
                expected=EXPECTED_INSTALLED_WRAPPER_PATH,
                actual=installed_wrapper.get("path"),
            )
        if SHA256_RE.fullmatch(str(installed_wrapper.get("sha256", ""))) is None:
            add(blockers, f"{path_key}_installed_wrapper_sha256_invalid", path_key)

    marker_dir = payload.get("marker_dir")
    expected_marker_dir = f"{EXPECTED_OBELISK_ROOT}/state/instances/{target.instance}"
    if marker_dir != expected_marker_dir:
        add(
            blockers,
            f"{path_key}_marker_dir_instance_mismatch",
            path_key,
            expected=expected_marker_dir,
            actual=marker_dir,
        )

    env_file = payload.get("env_file")
    if expected_mode == "observer-window":
        observer_env_text = fields.get("observer_env_path")
        observer_env_sha256 = fields.get("observer_env_sha256")
        if not isinstance(env_file, dict):
            add(blockers, f"{path_key}_env_file_missing", path_key)
        else:
            observer_env_path = manifest_relative_path(observer_env_text, manifest_path) if observer_env_text else None
            if observer_env_path is None:
                add(blockers, f"{path_key}_observer_env_path_missing", path_key)
            else:
                observer_env_status = protected_paths.protected_path_status(
                    observer_env_path,
                    protected_root=SERVER_ROOT,
                    approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
                )
                if env_file.get("path") != str(observer_env_status.resolved):
                    add(
                        blockers,
                        f"{path_key}_env_file_path_mismatch",
                        path_key,
                        expected=str(observer_env_status.resolved),
                        actual=env_file.get("path"),
                    )
            if env_file.get("sha256") != observer_env_sha256:
                add(
                    blockers,
                    f"{path_key}_env_file_sha256_mismatch",
                    path_key,
                    expected=observer_env_sha256,
                    actual=env_file.get("sha256"),
                )
    elif env_file is not None:
        add(blockers, f"{path_key}_env_file_unexpected", path_key)


def read_preflight_checked_at_utc(
    fields: dict[str, str],
    manifest_path: Path,
    *,
    path_key: str,
) -> datetime | None:
    path_text = fields.get(path_key)
    if not path_text:
        return None
    path = manifest_relative_path(path_text, manifest_path)
    status = protected_paths.protected_path_status(
        path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected or not status.approved_offline_workspace or not status.resolved.is_file():
        return None
    try:
        payload = json.loads(status.resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    checked_at_utc = payload.get("checked_at_utc")
    if not isinstance(checked_at_utc, str) or UTC_TIMESTAMP_RE.fullmatch(checked_at_utc) is None:
        return None
    return parse_utc_timestamp(checked_at_utc)


def validate_request_pack_replay_contract(
    fields: dict[str, str],
    manifest_path: Path,
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    contract = payload.get("post_window_replay_contract")
    if not isinstance(contract, dict):
        add(blockers, "request_pack_post_window_replay_contract_missing", "request_pack_path")
        return
    if contract.get("required") is not True:
        add(blockers, "request_pack_post_window_replay_contract_required_mismatch", "request_pack_path")
    if contract.get("offline_only") is not True:
        add(blockers, "request_pack_post_window_replay_contract_offline_only_mismatch", "request_pack_path")
    if contract.get("non_authorization") != REPLAY_NON_AUTHORIZATION:
        add(blockers, "request_pack_post_window_replay_contract_non_authorization_mismatch", "request_pack_path")
    sidecars = contract.get("sidecars")
    if not isinstance(sidecars, dict):
        add(blockers, "request_pack_post_window_replay_contract_sidecars_missing", "request_pack_path")
        return
    checks = contract.get("checks")
    if not isinstance(checks, dict):
        add(blockers, "request_pack_post_window_replay_contract_checks_missing", "request_pack_path")
    else:
        expected_command = [
            "scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py",
            "--json",
            "--post-window-replay",
            str(
                protected_paths.protected_path_status(
                    manifest_path,
                    protected_root=SERVER_ROOT,
                    approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
                ).resolved
            ),
        ]
        if checks.get("window_manifest_replay") != expected_command:
            add(
                blockers,
                "request_pack_post_window_replay_contract_check_mismatch",
                "request_pack_path",
                expected=expected_command,
                actual=checks.get("window_manifest_replay"),
            )
    expected_manifest_path = protected_paths.protected_path_status(
        manifest_path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    ).resolved
    expected_by_contract_key: dict[str, Path | None] = {
        "request_pack_path": manifest_relative_path(fields["request_pack_path"], manifest_path)
        if fields.get("request_pack_path")
        else None,
        "observer_env_path": manifest_relative_path(fields["observer_env_path"], manifest_path)
        if fields.get("observer_env_path")
        else None,
        "operator_approval_request_path": (
            manifest_relative_path(fields["request_pack_path"], manifest_path).parent / "operator-approval-request.md"
            if fields.get("request_pack_path")
            else None
        ),
        "operator_approval_receipt_path": manifest_relative_path(fields["operator_approval_receipt_path"], manifest_path)
        if fields.get("operator_approval_receipt_path")
        else None,
        "preflight_pre_path": manifest_relative_path(fields["preflight_pre_path"], manifest_path)
        if fields.get("preflight_pre_path")
        else None,
        "preflight_post_path": manifest_relative_path(fields["preflight_post_path"], manifest_path)
        if fields.get("preflight_post_path")
        else None,
        "window_manifest_path": expected_manifest_path,
        "copied_log_path": manifest_relative_path(fields["copied_log_path"], manifest_path)
        if fields.get("copied_log_path")
        else None,
    }
    for key in sorted(set(sidecars) - EXPECTED_REQUEST_PACK_REPLAY_SIDECAR_KEYS):
        add(
            blockers,
            "request_pack_post_window_replay_contract_unexpected_sidecar",
            "request_pack_path",
            sidecar=key,
        )
    for key, expected_path in expected_by_contract_key.items():
        actual = sidecars.get(key)
        if not isinstance(actual, str):
            add(blockers, "request_pack_post_window_replay_contract_mismatch", "request_pack_path", sidecar=key, actual=actual)
            continue
        if expected_path is None:
            add(blockers, "request_pack_post_window_replay_contract_mismatch", "request_pack_path", sidecar=key, actual=actual)
            continue
        symlink = protected_paths.first_symlink_component(Path(actual))
        if symlink is not None:
            add(
                blockers,
                "request_pack_post_window_replay_contract_sidecar_symlink",
                "request_pack_path",
                sidecar=key,
                symlink=str(symlink),
            )
        status = protected_paths.protected_path_status(
            Path(actual),
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        )
        expected_status = protected_paths.protected_path_status(
            expected_path,
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        )
        expected_text = str(expected_status.resolved)
        if actual != expected_text:
            add(
                blockers,
                "request_pack_post_window_replay_contract_alias",
                "request_pack_path",
                sidecar=key,
                expected=expected_text,
                actual=actual,
                resolved=str(status.resolved),
            )
        if status.resolved != expected_status.resolved:
            add(
                blockers,
                "request_pack_post_window_replay_contract_mismatch",
                "request_pack_path",
                sidecar=key,
                expected=str(expected_status.resolved),
                actual=str(status.resolved),
            )


def validate_request_pack_runtime_triplet_contract(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    expected = runtime_triplet_contract()
    contract = payload.get("runtime_triplet_contract")
    if contract != expected:
        add(blockers, "request_pack_runtime_triplet_contract_mismatch", "request_pack_path")
    if not isinstance(contract, dict):
        add(blockers, "request_pack_runtime_triplet_contract_missing", "request_pack_path")
        return

    rejected = contract.get("session_start_rejected")
    if not isinstance(rejected, dict):
        add(blockers, "request_pack_runtime_triplet_contract_session_start_rejected_missing", "request_pack_path")
        return
    if rejected.get("required_call") != SESSION_START_REJECTED_REQUIRED_CALL:
        add(
            blockers,
            "request_pack_runtime_triplet_contract_session_start_rejected_call_mismatch",
            "request_pack_path",
            expected=SESSION_START_REJECTED_REQUIRED_CALL,
            actual=rejected.get("required_call"),
        )
    if rejected.get("required_copied_bool_fields") != SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS:
        add(
            blockers,
            "request_pack_runtime_triplet_contract_session_start_copied_bool_fields_mismatch",
            "request_pack_path",
            expected=SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_FIELDS,
            actual=rejected.get("required_copied_bool_fields"),
        )
    if rejected.get("required_copied_bool_values") != SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES:
        add(
            blockers,
            "request_pack_runtime_triplet_contract_session_start_copied_bool_values_mismatch",
            "request_pack_path",
            expected=SESSION_START_REJECTED_REQUIRED_COPIED_BOOL_VALUES,
            actual=rejected.get("required_copied_bool_values"),
        )


def validate_request_pack(
    fields: dict[str, str],
    manifest_path: Path,
    blockers: list[dict[str, Any]],
    *,
    post_window_replay: bool = False,
) -> None:
    path_text = fields.get("request_pack_path")
    if not path_text:
        return
    request_path = manifest_relative_path(path_text, manifest_path)
    status = protected_paths.protected_path_status(
        request_path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if not add_unreadable_sidecar_status(
        blockers,
        status,
        label="request_pack_path",
        protected_reason="request_pack_path_under_protected_server_root",
        unapproved_reason="request_pack_path_not_under_approved_offline_workspace",
        missing_reason="request_pack_path_file_missing",
    ):
        return
    try:
        payload = json.loads(status.resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        add(blockers, "request_pack_json_invalid", "request_pack_path", detail=str(exc))
        return
    if not isinstance(payload, dict):
        add(blockers, "request_pack_not_object", "request_pack_path")
        return
    add_non_evidence_schema_blocker(
        payload,
        blockers,
        reason_prefix="request_pack",
        label="request_pack_path",
    )
    add_request_pack_current_schema_blockers(payload, blockers)
    add_request_pack_non_authorization_blockers(payload, blockers)
    validate_request_pack_runtime_triplet_contract(payload, blockers)
    if payload.get("schema") != WINDOW_REQUEST_SCHEMA:
        add(blockers, "request_pack_schema_mismatch", "request_pack_path", expected=WINDOW_REQUEST_SCHEMA)
    if payload.get("run_id") != fields.get("run_id"):
        add(blockers, "request_pack_run_id_mismatch", "request_pack_path")
    if payload.get("obelisk_commit") != fields.get("obelisk_commit"):
        add(
            blockers,
            "request_pack_obelisk_commit_mismatch",
            "request_pack_path",
            expected=fields.get("obelisk_commit"),
            actual=payload.get("obelisk_commit"),
        )
    if payload.get("ark_binary_sha256") != EXPECTED_BINARY_SHA256:
        add(
            blockers,
            "request_pack_ark_binary_sha256_mismatch",
            "request_pack_path",
            expected=EXPECTED_BINARY_SHA256,
            actual=payload.get("ark_binary_sha256"),
        )
    copied_log_text = fields.get("copied_log_path")
    if copied_log_text:
        copied_log_status = protected_paths.protected_path_status(
            manifest_relative_path(copied_log_text, manifest_path),
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        )
        expected_log_path = str(copied_log_status.resolved)
        expected_evidence_dir = str(copied_log_status.resolved.parent)
        if payload.get("copied_log_path") != expected_log_path:
            add(
                blockers,
                "request_pack_copied_log_path_manifest_mismatch",
                "request_pack_path",
                expected=expected_log_path,
                actual=payload.get("copied_log_path"),
            )
        if payload.get("copied_evidence_dir") != expected_evidence_dir:
            add(
                blockers,
                "request_pack_copied_evidence_dir_manifest_mismatch",
                "request_pack_path",
                expected=expected_evidence_dir,
                actual=payload.get("copied_evidence_dir"),
            )
    manifest_status = protected_paths.protected_path_status(
        manifest_path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    expected_manifest_path = str(manifest_status.resolved)
    if payload.get("window_manifest_path") != expected_manifest_path:
        add(
            blockers,
            "request_pack_window_manifest_path_manifest_mismatch",
            "request_pack_path",
            expected=expected_manifest_path,
            actual=payload.get("window_manifest_path"),
        )
    target = payload.get("target")
    if isinstance(target, dict):
        instance = fields.get("instance") or fields.get("instance_id")
        map_name = fields.get("map") or fields.get("map_name")
        if fields.get("target") and "/" in fields["target"]:
            instance, map_name = fields["target"].split("/", 1)
        if target.get("instance") != instance:
            add(blockers, "request_pack_instance_mismatch", "request_pack_path")
        if target.get("map") != map_name:
            add(blockers, "request_pack_map_mismatch", "request_pack_path")
    else:
        add(blockers, "request_pack_target_missing", "request_pack_path")
    approved_window = payload.get("approved_window")
    if isinstance(approved_window, dict):
        if approved_window.get("start_utc") != fields.get("approved_window_start_utc"):
            add(blockers, "request_pack_approved_window_start_mismatch", "request_pack_path")
        if approved_window.get("end_utc") != fields.get("approved_window_end_utc"):
            add(blockers, "request_pack_approved_window_end_mismatch", "request_pack_path")
    else:
        add(blockers, "request_pack_approved_window_missing", "request_pack_path")
    validate_request_pack_replay_contract(fields, manifest_path, payload, blockers)

    observer_env_text = fields.get("observer_env_path")
    if not observer_env_text:
        return
    observer_env_path = manifest_relative_path(observer_env_text, manifest_path)
    observer_env_status = protected_paths.protected_path_status(
        observer_env_path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if not add_unreadable_sidecar_status(
        blockers,
        observer_env_status,
        label="observer_env_path",
        protected_reason="request_pack_observer_env_under_protected_server_root",
        unapproved_reason="request_pack_observer_env_not_under_approved_offline_workspace",
        missing_reason="request_pack_observer_env_file_missing",
    ):
        return
    command = [
        sys.executable,
        str(WINDOW_REQUEST_CHECKER),
        "--json",
        str(status.resolved),
        "--env-file",
        str(observer_env_status.resolved),
    ]
    if post_window_replay:
        command.append("--post-window-replay")
        receipt_text = fields.get("operator_approval_receipt_path")
        if receipt_text:
            receipt_status = protected_paths.protected_path_status(
                manifest_relative_path(receipt_text, manifest_path),
                protected_root=SERVER_ROOT,
                approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
            )
            if content_readable_status(receipt_status):
                command.extend(["--operator-approval-receipt", str(receipt_status.resolved)])
    result = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    payload_check: dict[str, Any] | None = None
    if result.stdout.strip():
        try:
            parsed = json.loads(result.stdout)
            if isinstance(parsed, dict):
                payload_check = parsed
        except json.JSONDecodeError:
            payload_check = None
    request_check_blockers = (payload_check or {}).get("blockers", [])
    if (
        result.returncode != 0
        or not isinstance(payload_check, dict)
        or payload_check.get("ready") is not True
        or payload_check.get("request_pack_ready") is not True
        or (post_window_replay and payload_check.get("post_window_replay") is not True)
        or (post_window_replay and payload_check.get("post_window_replay_expiry_tolerated") is not True)
    ):
        add(
            blockers,
            "request_pack_window_request_check_failed",
            "request_pack_path",
            exit_code=result.returncode,
            request_check_blockers=request_check_blockers,
        )


def validate_user_policy(fields: dict[str, str], blockers: list[dict[str, Any]]) -> str | None:
    has_new = "user_policy" in fields
    has_legacy = "users_policy" in fields
    if has_new and has_legacy:
        add(blockers, "user_policy_alias_ambiguous", "user_policy")
        return fields.get("user_policy")
    value = fields.get("user_policy") or fields.get("users_policy")
    if value is None:
        add(blockers, "user_policy_missing", "user_policy")
        return None
    if value not in ACCEPTED_USER_POLICIES:
        add(blockers, "user_policy_not_accepted", "user_policy", accepted=sorted(ACCEPTED_USER_POLICIES))
    notice_sent = fields.get("notice_sent")
    if notice_sent not in {"true", "false", "not_applicable"}:
        add(blockers, "notice_sent_invalid", "notice_sent")
    if value == "operator_approved_beta_users" and fields.get("notice_sent") != "true":
        add(blockers, "beta_user_policy_requires_notice_sent", "notice_sent")
    if value == "no_regular_users" and fields.get("notice_sent") != "not_applicable":
        add(blockers, "no_regular_users_notice_must_be_not_applicable", "notice_sent")
    return value


def validate_manifest(
    fields: dict[str, str],
    manifest_path: Path,
    *,
    post_window_replay: bool = False,
) -> Validation:
    blockers: list[dict[str, Any]] = []
    timestamps: dict[str, datetime] = {}
    for key in sorted(fields):
        if key not in ALLOWED_FIELDS:
            add(blockers, "unexpected_field", key)
        if key not in ALLOWED_FIELDS and FORBIDDEN_KEY_RE.search(key):
            add(blockers, "forbidden_identity_or_ue_field", key)
        if key not in PATH_VALUE_FIELDS:
            if FORBIDDEN_VALUE_RE.search(fields[key]):
                add(blockers, "forbidden_identity_or_ue_value", key)
            if POSITIVE_CAPABILITY_VALUE_RE.search(fields[key]):
                add(blockers, "forbidden_public_capability_or_readiness_value", key)
    for key in REQUIRED_SIMPLE_FIELDS:
        if key not in fields:
            add(blockers, "required_field_missing", key)
    for key in REQUIRED_TIMESTAMP_FIELDS:
        value = fields.get(key)
        if value is None:
            add(blockers, "required_field_missing", key)
        elif not UTC_TIMESTAMP_RE.fullmatch(value):
            add(blockers, "utc_timestamp_invalid", key)
        else:
            parsed = parse_utc_timestamp(value)
            if parsed is None:
                add(blockers, "utc_timestamp_invalid", key)
            else:
                timestamps[key] = parsed

    run_id = fields.get("run_id")
    if run_id is not None and RUN_ID_RE.fullmatch(run_id) is None:
        add(blockers, "run_id_invalid", "run_id")
    obelisk_commit = fields.get("obelisk_commit")
    if obelisk_commit is not None and not is_reviewed_obelisk_commit(obelisk_commit):
        add(blockers, "obelisk_commit_invalid", "obelisk_commit")

    copied_log_sha256 = fields.get("copied_log_sha256")
    if copied_log_sha256 is not None and SHA256_RE.fullmatch(copied_log_sha256) is None:
        add(blockers, "copied_log_sha256_invalid", "copied_log_sha256")
    if fields.get("approval") not in EXPECTED_APPROVALS:
        add(
            blockers,
            "approval_not_bound_runtime_window",
            "approval",
            expected=sorted(EXPECTED_APPROVALS),
        )

    target = validate_target(fields, blockers)
    copied_log_status = validate_copied_log_path(fields, manifest_path, blockers)
    validate_sidecar_file(
        fields,
        manifest_path,
        blockers,
        path_key="request_pack_path",
        sha_key="request_pack_sha256",
        expected_name="window-request.json",
    )
    validate_sidecar_file(
        fields,
        manifest_path,
        blockers,
        path_key="observer_env_path",
        sha_key="observer_env_sha256",
        expected_name="observer-window.env",
    )
    validate_sidecar_file(
        fields,
        manifest_path,
        blockers,
        path_key="operator_approval_receipt_path",
        sha_key="operator_approval_receipt_sha256",
        expected_name="operator-approval-receipt.json",
    )
    validate_sidecar_file(
        fields,
        manifest_path,
        blockers,
        path_key="preflight_pre_path",
        sha_key="preflight_pre_sha256",
        expected_name="preflight-pre.json",
    )
    validate_preflight_content(
        fields,
        manifest_path,
        blockers,
        path_key="preflight_pre_path",
        expected_mode="observer-window",
        target=target,
    )
    validate_sidecar_file(
        fields,
        manifest_path,
        blockers,
        path_key="preflight_post_path",
        sha_key="preflight_post_sha256",
        expected_name="preflight-post.json",
    )
    validate_preflight_content(
        fields,
        manifest_path,
        blockers,
        path_key="preflight_post_path",
        expected_mode="stable",
        target=target,
    )
    validate_request_pack(fields, manifest_path, blockers, post_window_replay=post_window_replay)
    validate_operator_approval_receipt(fields, manifest_path, target, blockers)
    manifest_status = protected_paths.protected_path_status(
        manifest_path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if manifest_status.approved_offline_workspace and not manifest_status.protected:
        validate_unexpected_post_window_json_sidecars(
            manifest_status.resolved.parent,
            blockers,
            post_window_replay=post_window_replay,
        )
    user_policy = validate_user_policy(fields, blockers)

    for key in ("pre_posture", "post_posture"):
        if fields.get(key) != "stable":
            add(blockers, f"{key}_not_stable", key, expected="stable")
    for key in ("pre_check", "post_check"):
        if fields.get(key) != "passed":
            add(blockers, f"{key}_not_passed", key, expected="passed")
    for key in ("rollback_completed", "plugins_disabled", "scanner_disabled"):
        if parse_bool(fields.get(key)) is not True:
            add(blockers, f"{key}_not_true", key, expected=True)
    for key in ("observer_env_survived", "observer_marker_survived"):
        if parse_bool(fields.get(key)) is not False:
            add(blockers, f"{key}_not_false", key, expected=False)
    if fields.get("rollback_delta") != EXPECTED_ROLLBACK_DELTA:
        add(
            blockers,
            "rollback_delta_mismatch",
            "rollback_delta",
            expected=EXPECTED_ROLLBACK_DELTA,
            actual=fields.get("rollback_delta"),
        )

    if len(timestamps) == len(REQUIRED_TIMESTAMP_FIELDS):
        if timestamps["approved_window_start_utc"] >= timestamps["approved_window_end_utc"]:
            add(blockers, "approved_window_not_forward", "approved_window_end_utc")
        if timestamps["actual_capture_start_utc"] >= timestamps["actual_capture_end_utc"]:
            add(blockers, "actual_capture_not_forward", "actual_capture_end_utc")
        if timestamps["actual_capture_start_utc"] < timestamps["approved_window_start_utc"]:
            add(blockers, "actual_capture_starts_before_approved_window", "actual_capture_start_utc")
        if timestamps["actual_capture_end_utc"] > timestamps["approved_window_end_utc"]:
            add(blockers, "actual_capture_ends_after_approved_window", "actual_capture_end_utc")
        if timestamps["rollback_start_utc"] < timestamps["actual_capture_end_utc"]:
            add(blockers, "rollback_starts_before_capture_end", "rollback_start_utc")
        if timestamps["rollback_start_utc"] > timestamps["rollback_end_utc"]:
            add(blockers, "rollback_window_not_forward", "rollback_end_utc")
        if post_window_replay:
            current_time = now_utc()
            if timestamps["approved_window_end_utc"] > current_time:
                add(blockers, "approved_window_ends_in_future", "approved_window_end_utc")
            if timestamps["actual_capture_end_utc"] > current_time:
                add(blockers, "actual_capture_ends_in_future", "actual_capture_end_utc")
            if timestamps["rollback_end_utc"] > current_time:
                add(blockers, "rollback_window_ends_in_future", "rollback_end_utc")
        preflight_pre_checked_at = read_preflight_checked_at_utc(
            fields,
            manifest_path,
            path_key="preflight_pre_path",
        )
        preflight_post_checked_at = read_preflight_checked_at_utc(
            fields,
            manifest_path,
            path_key="preflight_post_path",
        )
        if preflight_pre_checked_at is not None:
            if preflight_pre_checked_at < timestamps["approved_window_start_utc"]:
                add(
                    blockers,
                    "preflight_pre_path_checked_at_before_approved_window",
                    "preflight_pre_path",
                )
            if preflight_pre_checked_at > timestamps["actual_capture_start_utc"]:
                add(
                    blockers,
                    "preflight_pre_path_checked_at_after_capture_start",
                    "preflight_pre_path",
                )
        if preflight_post_checked_at is not None:
            if preflight_post_checked_at < timestamps["actual_capture_end_utc"]:
                add(
                    blockers,
                    "preflight_post_path_checked_at_before_capture_end",
                    "preflight_post_path",
                )
            if preflight_post_checked_at > timestamps["rollback_end_utc"]:
                add(
                    blockers,
                    "preflight_post_path_checked_at_after_rollback_end",
                    "preflight_post_path",
                )
        if (
            preflight_pre_checked_at is not None
            and preflight_post_checked_at is not None
            and preflight_pre_checked_at >= preflight_post_checked_at
        ):
            add(blockers, "preflight_checked_at_order_invalid", "preflight_post_path")

    try:
        log_budget = int(fields.get("log_budget", ""))
    except ValueError:
        add(blockers, "log_budget_not_integer", "log_budget")
    else:
        if log_budget != 10:
            add(blockers, "log_budget_not_exact_first_window_limit", "log_budget", expected=10)

    if fields.get("dispatch_limit") != "0":
        add(blockers, "dispatch_limit_not_zero", "dispatch_limit", expected="0")
    if fields.get("wrapper_profile") != "observer-debug":
        add(blockers, "wrapper_profile_not_observer_debug", "wrapper_profile", expected="observer-debug")
    if fields.get("observer_exclusivity") != "player_principal_lifecycle_only":
        add(
            blockers,
            "observer_exclusivity_not_player_principal_lifecycle_only",
            "observer_exclusivity",
            expected="player_principal_lifecycle_only",
        )
    for key in (
        "sibling_marker_entries",
        "sibling_observer_env",
        "debug_escape_markers",
        "callback_escape_markers",
    ):
        if fields.get(key) != "absent":
            add(blockers, f"{key}_not_absent", key, expected="absent")
    for key in ("native_exec_disabled", "ptrace_disabled"):
        if parse_bool(fields.get(key)) is not True:
            add(blockers, f"{key}_not_true", key, expected=True)
    if fields.get("single_module_summary") != "player_principal_lifecycle":
        add(
            blockers,
            "single_module_summary_not_player_principal_lifecycle",
            "single_module_summary",
            expected="player_principal_lifecycle",
        )
    if fields.get("delivery_claim") != "none":
        add(blockers, "delivery_claim_not_none", "delivery_claim", expected="none")
    if fields.get("principal_claim") != "none":
        add(blockers, "principal_claim_not_none", "principal_claim", expected="none")

    return Validation(
        blockers=blockers,
        target=target,
        user_policy=user_policy,
        copied_log_status=copied_log_status,
    )


def build_template_fields() -> dict[str, str]:
    return {
        "run_id": "20260601T120000Z-player-principal-lifecycle",
        "obelisk_commit": "<reviewed-40-character-lowercase-git-sha>",
        "target": "arkserver2/TheIsland",
        "approval": EXPECTED_APPROVAL,
        "approved_window_start_utc": "2026-06-01T12:00:00Z",
        "approved_window_end_utc": "2026-06-01T12:10:00Z",
        "actual_capture_start_utc": "2026-06-01T12:01:00Z",
        "actual_capture_end_utc": "2026-06-01T12:09:00Z",
        "copied_log_path": (
            "/servidor/ark/workspace-offline/live-validation-logs/"
            "20260601T120000Z-player-principal-lifecycle/Obelisk.log"
        ),
        "copied_log_sha256": "0" * 64,
        "request_pack_path": (
            "/servidor/ark/workspace-offline/live-validation-logs/"
            "20260601T120000Z-player-principal-lifecycle/window-request.json"
        ),
        "request_pack_sha256": "0" * 64,
        "observer_env_path": (
            "/servidor/ark/workspace-offline/live-validation-logs/"
            "20260601T120000Z-player-principal-lifecycle/observer-window.env"
        ),
        "observer_env_sha256": "0" * 64,
        "operator_approval_receipt_path": (
            "/servidor/ark/workspace-offline/live-validation-logs/"
            "20260601T120000Z-player-principal-lifecycle/operator-approval-receipt.json"
        ),
        "operator_approval_receipt_sha256": "0" * 64,
        "preflight_pre_path": (
            "/servidor/ark/workspace-offline/live-validation-logs/"
            "20260601T120000Z-player-principal-lifecycle/preflight-pre.json"
        ),
        "preflight_pre_sha256": "0" * 64,
        "preflight_post_path": (
            "/servidor/ark/workspace-offline/live-validation-logs/"
            "20260601T120000Z-player-principal-lifecycle/preflight-post.json"
        ),
        "preflight_post_sha256": "0" * 64,
        "pre_posture": "stable",
        "post_posture": "stable",
        "pre_check": "passed",
        "post_check": "passed",
        "rollback_start_utc": "2026-06-01T12:09:00Z",
        "rollback_end_utc": "2026-06-01T12:10:00Z",
        "rollback_completed": "true",
        "rollback_delta": "removed_observer_env_and_markers_preserved_disable_plugins",
        "observer_env_survived": "false",
        "observer_marker_survived": "false",
        "sibling_marker_entries": "absent",
        "sibling_observer_env": "absent",
        "user_policy": "no_regular_users",
        "notice_sent": "not_applicable",
        "log_budget": "10",
        "plugins_disabled": "true",
        "scanner_disabled": "true",
        "dispatch_limit": "0",
        "wrapper_profile": "observer-debug",
        "observer_exclusivity": "player_principal_lifecycle_only",
        "debug_escape_markers": "absent",
        "callback_escape_markers": "absent",
        "native_exec_disabled": "true",
        "ptrace_disabled": "true",
        "single_module_summary": "player_principal_lifecycle",
        "delivery_claim": "none",
        "principal_claim": "none",
    }


def template_fields_from_copied_log(copied_log: Path) -> dict[str, str]:
    reject_symlink_component(copied_log, "--copied-log")
    status = protected_paths.protected_path_status(
        copied_log,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected:
        raise SystemExit(f"--copied-log must not read from protected server root {SERVER_ROOT}: {status.resolved}")
    if not any(
        copied_log.expanduser().is_absolute()
        and protected_paths.is_under_path(copied_log.expanduser(), root)
        and protected_paths.is_under_path(status.resolved, root.resolve())
        for root in APPROVED_OFFLINE_WORKSPACE_ROOTS
    ):
        raise SystemExit("--copied-log must be under /servidor/ark/workspace-offline")
    if not status.resolved.is_file():
        raise SystemExit(f"--copied-log does not exist: {status.resolved}")
    if len(status.resolved.parts) < 3:
        raise SystemExit("--copied-log must be live-validation-logs/<run-id>/Obelisk.log")
    expected_parent = status.resolved.parts[-3]
    run_id = status.resolved.parts[-2]
    file_name = status.resolved.parts[-1]
    if expected_parent != EXPECTED_COPIED_LOG_PARENT or file_name != "Obelisk.log":
        raise SystemExit("--copied-log must be live-validation-logs/<run-id>/Obelisk.log")
    if RUN_ID_RE.fullmatch(run_id) is None:
        raise SystemExit(f"--copied-log run id is invalid: {run_id}")
    sidecar_dir = status.resolved.parent
    return {
        "run_id": run_id,
        "copied_log_path": str(status.resolved),
        "copied_log_sha256": hashlib.sha256(status.resolved.read_bytes()).hexdigest(),
        "request_pack_path": str(sidecar_dir / "window-request.json"),
        "observer_env_path": str(sidecar_dir / "observer-window.env"),
        "operator_approval_receipt_path": str(sidecar_dir / "operator-approval-receipt.json"),
    }


def write_template(path: Path, copied_log: Path | None = None) -> None:
    reject_symlink_component(path, "--emit-template")
    protected_paths.reject_server_root_write_without_opt_in(path, "--emit-template", protected_root=SERVER_ROOT)
    resolved = protected_paths.reject_protected_input_path(
        path,
        "--emit-template",
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    resolved.parent.mkdir(parents=True, exist_ok=True)
    fields = build_template_fields()
    if copied_log is not None:
        fields.update(template_fields_from_copied_log(copied_log))
    lines = [
        "# Secret-free operational manifest for a future approved player-principal lifecycle window.",
        "# Replace timestamps, run_id, copied_log_path, copied_log_sha256, and target with the reviewed window values.",
    ]
    lines.extend(f"{key}={value}" for key, value in fields.items())
    resolved.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_report(
    fields: dict[str, str],
    validation: Validation,
    manifest_path: Path,
    *,
    post_window_replay: bool = False,
) -> dict[str, Any]:
    accepted = not validation.blockers
    next_blocker = NEXT_BLOCKER_AFTER_WINDOW_MANIFEST if accepted else "window_manifest_not_accepted"
    next_required_artifact = (
        NEXT_REQUIRED_ARTIFACT_AFTER_WINDOW_MANIFEST
        if accepted
        else "accepted_player_principal_lifecycle_window_manifest"
    )
    next_step = NEXT_STEP_AFTER_WINDOW_MANIFEST if accepted else NEXT_STEP_WHEN_BLOCKED
    required_artifact_status = "missing_or_not_accepted" if accepted else "window_manifest_not_accepted"
    manifest_status = protected_paths.protected_path_status(
        manifest_path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    resolved_manifest_path = str(manifest_status.resolved)

    def resolved_field_path(key: str) -> str | None:
        value = fields.get(key)
        if not value:
            return None
        path = manifest_relative_path(value, manifest_path)
        status = protected_paths.protected_path_status(
            path,
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        )
        return str(status.resolved)

    try:
        manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    except OSError:
        manifest_sha256 = None
    copied_log_path = fields.get("copied_log_path")
    resolved_copied_log_path = None
    if copied_log_path:
        try:
            resolved_copied_log_path = str(manifest_relative_path(copied_log_path, manifest_path).expanduser().resolve())
        except OSError:
            resolved_copied_log_path = str(manifest_relative_path(copied_log_path, manifest_path).expanduser())
    return {
        "schema": REPORT_SCHEMA,
        "ready": accepted,
        "operational_window_manifest_ready": accepted,
        "post_window_replay": post_window_replay,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "promotion_ready": False,
        "public_header_allowed": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "v1_completion_ready": False,
        "runtime_ready": False,
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
        "remaining_blockers": [] if accepted else ["window_manifest_not_accepted"],
        "next_blocker": next_blocker,
        "current_route_blocker": None if accepted else "window_manifest_not_accepted",
        "next_required_artifact": next_required_artifact,
        "missing_required_artifact": next_required_artifact,
        "required_artifact_status": required_artifact_status,
        "next_step": next_step,
        "machine_next_step": {
            "schema": NEXT_STEP_SCHEMA,
            "step": next_step,
            "next_blocker": next_blocker,
            "next_required_artifact": next_required_artifact,
            "required_artifact_status": required_artifact_status,
            "authorized_by_this_report": False,
            "server_operations_authorized": False,
            "runtime_work_authorized": False,
            "discord_authorized": False,
            "marker_env_changes_authorized": False,
            "runtime_capture_authorized": False,
            "approved_runtime_evidence": False,
            "approved_runtime_evidence_ready": False,
            "public_sdk_ready": False,
            "v1_completion_ready": False,
        },
        "run_id": fields.get("run_id"),
        "obelisk_commit": fields.get("obelisk_commit"),
        "approval": fields.get("approval"),
        "approved_window": {
            "start_utc": fields.get("approved_window_start_utc"),
            "end_utc": fields.get("approved_window_end_utc"),
        },
        "actual_capture": {
            "start_utc": fields.get("actual_capture_start_utc"),
            "end_utc": fields.get("actual_capture_end_utc"),
        },
        "rollback_window": {
            "start_utc": fields.get("rollback_start_utc"),
            "end_utc": fields.get("rollback_end_utc"),
        },
        "target": {
            "instance": validation.target.instance,
            "map": validation.target.map_name,
        },
        "manifest": {
            "path": resolved_manifest_path,
            "sha256": manifest_sha256,
        },
        "copied_log": {
            "path": resolved_copied_log_path,
            "sha256": fields.get("copied_log_sha256"),
            "path_status": validation.copied_log_status,
        },
        "request_pack": {
            "path": resolved_field_path("request_pack_path"),
            "sha256": fields.get("request_pack_sha256"),
        },
        "observer_env": {
            "path": resolved_field_path("observer_env_path"),
            "sha256": fields.get("observer_env_sha256"),
        },
        "operator_approval_receipt": {
            "path": resolved_field_path("operator_approval_receipt_path"),
            "sha256": fields.get("operator_approval_receipt_sha256"),
            "verified": bool(accepted and post_window_replay),
        },
        "preflight": {
            "pre": {
                "path": resolved_field_path("preflight_pre_path"),
                "sha256": fields.get("preflight_pre_sha256"),
            },
            "post": {
                "path": resolved_field_path("preflight_post_path"),
                "sha256": fields.get("preflight_post_sha256"),
            },
        },
        "posture": {
            "pre_posture": fields.get("pre_posture"),
            "post_posture": fields.get("post_posture"),
            "pre_check": fields.get("pre_check"),
            "post_check": fields.get("post_check"),
            "plugins_disabled": parse_bool(fields.get("plugins_disabled")),
            "scanner_disabled": parse_bool(fields.get("scanner_disabled")),
            "dispatch_limit": fields.get("dispatch_limit"),
            "wrapper_profile": fields.get("wrapper_profile"),
            "observer_exclusivity": fields.get("observer_exclusivity"),
            "sibling_marker_entries": fields.get("sibling_marker_entries"),
            "sibling_observer_env": fields.get("sibling_observer_env"),
            "debug_escape_markers": fields.get("debug_escape_markers"),
            "callback_escape_markers": fields.get("callback_escape_markers"),
            "native_exec_disabled": parse_bool(fields.get("native_exec_disabled")),
            "ptrace_disabled": parse_bool(fields.get("ptrace_disabled")),
            "single_module_summary": fields.get("single_module_summary"),
        },
        "rollback": {
            "completed": parse_bool(fields.get("rollback_completed")),
            "observer_env_survived": parse_bool(fields.get("observer_env_survived")),
            "observer_marker_survived": parse_bool(fields.get("observer_marker_survived")),
            "delta": fields.get("rollback_delta"),
        },
        "user_policy": validation.user_policy,
        "notice_sent": fields.get("notice_sent"),
        "log_budget": fields.get("log_budget"),
        "claims": {
            "delivery_claim": fields.get("delivery_claim"),
            "principal_claim": fields.get("principal_claim"),
        },
        "blockers": [blocker["reason"] for blocker in validation.blockers],
        "blocker_details": validation.blockers,
        "non_claims": list(REQUIRED_OPERATIONAL_WINDOW_NON_CLAIMS),
    }


def main() -> int:
    args = parse_args()
    if args.emit_template is not None:
        write_template(args.emit_template, args.copied_log)
        return 0
    if args.copied_log is not None:
        raise SystemExit("--copied-log is only valid with --emit-template")
    if args.manifest is None:
        raise SystemExit("manifest is required unless --emit-template is used")
    fields = load_manifest(args.manifest)
    validation = validate_manifest(fields, args.manifest, post_window_replay=args.post_window_replay)
    report = build_report(fields, validation, args.manifest, post_window_replay=args.post_window_replay)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif validation.blockers:
        for blocker in validation.blockers:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    return 0 if not validation.blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
