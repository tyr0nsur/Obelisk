#!/usr/bin/env python3
"""Prepare an offline closure request for player-principal lifecycle evidence.

The report is intentionally read-only for the evidence tree. It inspects only the
supplied evidence directory and emits a plan/request describing which closure artifacts
are present, which are missing, and which follow-up operations need exact operator
authority. That authority can be a fresh current-turn approval or a recorded standing
launch authority receipt bound to this run/target. It does not create sidecars,
approved bundles, marker files, or server state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

import protected_paths
from prepare_player_principal_lifecycle_window_request import (
    APPROVAL_ATTESTATION_CURRENT_TURN,
    APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY,
    APPROVAL_TEXT,
    APPROVAL_SOURCE_CURRENT_TURN,
    APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY,
    STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT,
)


SCHEMA = "obelisk.player-principal-lifecycle-evidence-closure-request.v1"
MACHINE_NEXT_ACTIONS_SCHEMA = "obelisk.player-principal-lifecycle-closure-machine-next-actions.v1"
POST_WINDOW_ACTION_CONTRACT_SCHEMA = "obelisk.player-principal-lifecycle-post-window-action-contract.v1"
ARTIFACT_BINDINGS_SCHEMA = "obelisk.player-principal-lifecycle-closure-artifact-bindings.v1"
REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-player-principal-lifecycle$")
GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
PASSIVE_MONITOR_RUN_ID_RE = re.compile(
    r"[0-9]{8}T[0-9]{6}Z",
    re.IGNORECASE,
)
EXPECTED_EVIDENCE_PARENT = "live-validation-logs"
DEFAULT_BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
SERVER_ROOT = Path("/servidor/ark")
APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH = (
    "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
)
EVIDENCE_COMMAND_SEQUENCE_SCHEMA = (
    "obelisk.player-principal-lifecycle-evidence-command-sequence.v1"
)
COMMAND_PATH_BINDING_SCHEMA = (
    "obelisk.player-principal-lifecycle-command-path-binding.v1"
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
READY_LOG_COPY_RELATIVE_PATH = "ready-log-copy.json"
READY_LOG_COPY_SCHEMA = "obelisk.player-principal-lifecycle-ready-log-copy.v1"
OPERATOR_APPROVAL_RECEIPT_TEMPLATE_RELATIVE_PATH = "operator-approval-receipt.template.json"
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
WINDOW_REQUEST_SCHEMA = "obelisk.player-principal-lifecycle-window-request.v1"
OPERATOR_APPROVAL_RECEIPT_SCHEMA = "obelisk.player-principal-lifecycle-operator-approval-receipt.v1"
PREFLIGHT_SCHEMA = "obelisk.player-principal-lifecycle-preflight.v1"
APPROVED_RUNTIME_EVIDENCE_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1"
APPROVED_RUNTIME_EVIDENCE_ARTIFACT_STATUS = "approved_runtime_observer_summary"
APPROVED_RUNTIME_EVIDENCE_CLASSIFICATION = "runtime_evidence_only"
RUNTIME_OBSERVER_SUMMARY_SCHEMA = "obelisk.runtime-observer-log-summary.v1"
WINDOW_MANIFEST_CHECK_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-window-manifest-check.v1"
APPROVED_RUNTIME_SOURCE_MODULE = "player_principal_lifecycle"
GENERATED_RECEIPT_MARKER_RE = re.compile(r"(?:generated|template|stub|draft)", re.IGNORECASE)
GENERATED_RECEIPT_MARKER_KEYS = frozenset(
    {
        "receipt_kind",
        "kind",
        "mode",
        "source",
        "generation_status",
        "generated_template",
        "template_generated",
        "draft",
        "stub",
        "is_template",
        "generated_by",
    }
)
UTC_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
PLAYER_PRINCIPAL_LIFECYCLE_EVENT_RE = re.compile(
    r"PlayerPrincipalLifecycleObserver event sequence=(?P<sequence>\d+) "
    r"role=(?P<role>session_start|session_start_rejected|session_end)\b"
)
PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_RE = re.compile(
    r"PlayerPrincipalLifecycleObserver\s+diagnostic\b|"
    r"\bdiagnostic_only=true\b|"
    r"\bdiagnostic_candidate\b|"
    r"\broute_sample\b",
    re.IGNORECASE,
)
LOG_KEY_VALUE_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)=([^ \t.]+)")
REQUIRED_LIFECYCLE_EVENT_ROLES = (
    "session_start",
    "session_start_rejected",
    "session_end",
)
REQUIRED_LIFECYCLE_STATUS_PROOFS = {
    "session_start": {
        "apply_status": "session_start_created",
        "correlation_status": "not_applicable",
    },
    "session_start_rejected": {
        "apply_status": "session_start_rejected_noop",
        "correlation_status": "not_applicable",
    },
    "session_end": {
        "apply_status": "session_end_invalidated",
        "correlation_status": "matched",
    },
}
REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET = (
    {
        "label": "HandleNewPlayer(1,1)",
        "role": "session_start",
        "target": "ShooterGameMode.HandleNewPlayer",
        "post_original": "true",
        "copied_bool_fields": ("bIsFromLogin", "ReturnValue"),
        "copied_bool_values": ("1", "1"),
        "redacted_count": "3",
        "redacted_fields": ("NewPlayer", "PlayerData", "PlayerCharacter"),
        "apply_status": "session_start_created",
        "principal_action": "candidate_created",
        "correlation_status": "not_applicable",
        "principal_id_logged": "false",
        "principal_generation_logged": "false",
        "delivery_claim": "none",
    },
    {
        "label": "CheckJoinInProgress(1,0)",
        "role": "session_start_rejected",
        "target": "ShooterGameMode.CheckJoinInProgress",
        "post_original": "true",
        "copied_bool_fields": ("bIsFromLogin", "ReturnValue"),
        "copied_bool_values": ("1", "0"),
        "redacted_count": "1",
        "redacted_fields": ("NewPlayer",),
        "apply_status": "session_start_rejected_noop",
        "principal_action": "none",
        "correlation_status": "not_applicable",
        "principal_id_logged": "false",
        "principal_generation_logged": "false",
        "delivery_claim": "none",
    },
    {
        "label": "OnLogout matched",
        "role": "session_end",
        "target": "ShooterGameMode.OnLogout",
        "post_original": "true",
        "copied_bool_fields": (),
        "copied_bool_values": (),
        "redacted_count": "1",
        "redacted_fields": ("Exiting",),
        "apply_status": "session_end_invalidated",
        "principal_action": "candidate_invalidated",
        "correlation_status": "matched",
        "principal_id_logged": "false",
        "principal_generation_logged": "false",
        "delivery_claim": "none",
    },
)
REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_BY_ROLE = {
    str(case["role"]): case for case in REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET
}
REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS = tuple(
    str(case["label"]) for case in REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET
)
STRICT_REJECTED_START_EXPECTED_SHAPE = "ShooterGameMode.CheckJoinInProgress(1,0)"
NOTICE_PATH_NOT_APPLICABLE = "not_applicable"
SAFE_NOTICE_PATH_RE = re.compile(r"^[A-Za-z0-9_.:/ -]+$")
FORBIDDEN_NOTICE_PATH_VALUE_RE = re.compile(r"(?:https?://|webhook|token)", re.IGNORECASE)
DEFAULT_QUERY_PORTS = {
    ("arkserver", "Ragnarok"): "27015",
    ("arkserver2", "TheIsland"): "27016",
    ("arkserver3", "Genesis2"): "27017",
}

EXPECTED_SIBLINGS = (
    ("copied_log", "Obelisk.log"),
    ("window_request", "window-request.json"),
    ("observer_env", "observer-window.env"),
    ("operator_approval_request", "operator-approval-request.md"),
    ("operator_approval_receipt", "operator-approval-receipt.json"),
    ("preflight_pre", "preflight-pre.json"),
    ("preflight_post", "preflight-post.json"),
    ("window_manifest", "window-manifest.env"),
    (
        "approved_runtime_manifest",
        APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
    ),
)
REQUIRED_SIDECARS = tuple(rel for _, rel in EXPECTED_SIBLINGS if rel != "Obelisk.log")
REQUIRED_CLOSURE_ARTIFACTS = (
    "window-manifest.env",
    "preflight-post.json",
    "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
)
EXPECTED_RELATIVE_PATHS = frozenset(rel for _, rel in EXPECTED_SIBLINGS)
APPROVED_RUNTIME_MANIFEST_REQUIRED_OPERATIONAL_ARTIFACTS = (
    ("manifest", ("manifest",), "window-manifest.env", "approved_runtime_manifest_window_manifest"),
    ("copied_log", ("copied_log",), "Obelisk.log", "approved_runtime_manifest_copied_log"),
    ("request_pack", ("request_pack",), "window-request.json", "approved_runtime_manifest_request_pack"),
    ("observer_env", ("observer_env",), "observer-window.env", "approved_runtime_manifest_observer_env"),
    (
        "operator_approval_receipt",
        ("operator_approval_receipt",),
        "operator-approval-receipt.json",
        "approved_runtime_manifest_operator_approval_receipt",
    ),
    ("preflight.pre", ("preflight", "pre"), "preflight-pre.json", "approved_runtime_manifest_preflight_pre"),
    ("preflight.post", ("preflight", "post"), "preflight-post.json", "approved_runtime_manifest_preflight_post"),
)
EXPECTED_TOP_LEVEL_SIDECAR_FILENAMES = frozenset(
    rel for rel in EXPECTED_RELATIVE_PATHS if "/" not in rel and rel != "Obelisk.log"
)
EXPECTED_AUXILIARY_TOP_LEVEL_JSON_SIDECARS = frozenset(
    (
        READY_LOG_COPY_RELATIVE_PATH,
    )
)
NO_AUTHORIZATION_FLAGS = {
    "server_operations_authorized": False,
    "runtime_work_authorized": False,
    "live_ops_authorized": False,
    "live_log_read_authorized": False,
    "live_log_reads_authorized": False,
    "live_server_log_reads_authorized": False,
    "runtime_capture_authorized": False,
    "workspace_writes_authorized": False,
    "reads_live_logs": False,
    "marker_env_changes_authorized": False,
    "starts_restarts_stops_authorized": False,
    "discord_authorized": False,
    "discord_sent_by_this_report": False,
    "discord_command_emitted_by_this_report": False,
    "github_publication_authorized": False,
    "publication_authorized": False,
    "approved_runtime_evidence": False,
    "approved_runtime_evidence_present": False,
    "approved_runtime_evidence_created": False,
    "approved_runtime_evidence_ready": False,
    "counts_as_approved_runtime_evidence": False,
    "counts_as_runtime_evidence": False,
    "counts_as_sdk_evidence": False,
    "passive_snapshots_as_evidence": False,
    "passive_snapshots_count_as_evidence": False,
    "passive_snapshot_evidence_allowed": False,
    "candidate_sidecars_count_as_approved_runtime_evidence": False,
    "passive_complete_triplets_count_as_approved_runtime_evidence": False,
    "request_pack_preflight_window_manifest_count_as_approved_runtime_evidence": False,
    "copied_log_presence_counts_as_approved_runtime_evidence": False,
    "dry_run_success_counts_as_approved_runtime_evidence": False,
    "historical_target_names_authorize_runtime": False,
    "marker_env_readiness_counts_as_approved_runtime_evidence": False,
    "player_notice_counts_as_approved_runtime_evidence": False,
    "public_reachability_counts_as_approved_runtime_evidence": False,
    "status_report_paths_authorize_current_turn": False,
    "status_report_paths_count_as_approved_runtime_evidence": False,
    "counts_toward_sdk": False,
    "counts_toward_p0_dependency_chain": False,
    "counts_toward_v1": False,
    "counts_toward_v1_completion": False,
    "counts_toward_complete_sdk_claim_now": False,
    "counts_toward_p0_dependency_chain_claim_now": False,
    "closure_request_ready": False,
    "closure_request_counts_as_approved_runtime_evidence": False,
    "closure_request_counts_as_runtime_evidence": False,
    "closure_request_counts_as_sdk_evidence": False,
    "closure_request_counts_toward_sdk": False,
    "closure_request_counts_toward_p0_dependency_chain": False,
    "approved_runtime_evidence_accepted_by_checker": False,
    "copied_bundle_checker_acceptance_recorded": False,
    "sdk_p0_changes_authorized": False,
    "promotion_ready": False,
    "public_header_allowed": False,
    "public_abi_ready": False,
    "public_sdk_ready": False,
    "runtime_ready": False,
    "v1_completion_ready": False,
    "stable_claim_allowed": False,
}
SIDECAR_FALSE_CLAIM_KEYS = frozenset(NO_AUTHORIZATION_FLAGS) | {
    "accepted_runtime_evidence",
    "activation_allowed",
    "activation_authorized_by_this_report",
    "approved_runtime_evidence_accepted",
    "bundle_report_counts_as_approved_runtime_evidence",
    "complete_sdk_allowed",
    "complete_sdk_ready",
    "counts_toward_complete_sdk_claim",
    "counts_toward_complete_sdk_claim_now",
    "counts_toward_p0_dependency_chain",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_p0_dependency_chain_claim_now",
    "current_turn_authorized",
    "current_turn_runtime_authorized",
    "operator_approval_authorizes_runtime",
    "operator_approval_recorded_authorizes_runtime",
    "public_readiness_claim",
    "runtime_evidence_present",
    "runtime_evidence_ready",
    "runtime_window_authorized",
    "sdk_evidence_ready",
    "sdk_ready",
    "source_material_counts_as_approved_runtime_evidence",
    "source_material_counts_as_runtime_evidence",
    "source_material_counts_as_sdk_evidence",
}
SIDECAR_NONZERO_PROGRESS_KEYS = {
    "claim_progress_contribution",
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_progress_contribution",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_progress_contribution",
    "p0_progress",
    "runtime_progress",
    "sdk_progress",
    "source_overclaim_total_flag_count",
    "v1_progress",
}
REQUIRED_PREFLIGHT_FALSE_FLAGS = frozenset(
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
SIDECAR_CLAIM_DOMAIN_TOKENS = {
    "activation",
    "claim",
    "discord",
    "evidence",
    "label",
    "live",
    "ops",
    "p0",
    "package",
    "public",
    "readiness",
    "route",
    "runtime",
    "sdk",
    "server",
    "stable",
    "support",
    "v1",
    "workspace",
}
SIDECAR_CLAIM_COMPLETION_TOKENS = {
    "accepted",
    "allowed",
    "approved",
    "available",
    "complete",
    "completed",
    "completion",
    "enabled",
    "present",
    "promoted",
    "ready",
    "readiness",
    "supported",
    "unlocked",
    "validated",
}
SIDECAR_GENERIC_STATUS_KEYS = {
    "classification",
    "claim",
    "evidence",
    "label",
    "package",
    "readiness",
    "result",
    "state",
    "status",
    "support",
    "support_level",
    "tier",
}
SIDECAR_SPLIT_CLAIM_NAME_KEYS = {
    "alias",
    "claim",
    "field",
    "flag",
    "key",
    "name",
    "property",
}
SIDECAR_SPLIT_CLAIM_VALUE_KEYS = {
    "allowed",
    "classification",
    "enabled",
    "label",
    "package",
    "ready",
    "state",
    "status",
    "support",
    "support_level",
    "tier",
    "value",
}
SIDECAR_SUPPORT_PACKAGE_ALIAS_TOKENS = {
    "classification",
    "label",
    "package",
    "support",
    "supported",
    "tier",
}
SIDECAR_NON_EVIDENCE_SCHEMAS = {
    "obelisk.runtime-observer-log-summary.v1",
    "obelisk.player-principal-lifecycle-evidence-closure-request.v1",
    "obelisk.player-principal-lifecycle-activation-preconditions.v1",
    "obelisk.player-principal-lifecycle-window-request-check.v1",
    "obelisk.player-principal-lifecycle-beta-notice-prep.v1",
    "obelisk.player-principal-lifecycle-player-notice-action.v1",
    "obelisk.player-principal-passive-snapshot.v1",
    "obelisk.player-principal-passive-snapshot-diff.v1",
    "obelisk.player-principal-passive-snapshot-latest.v1",
    "obelisk.player-principal-passive-observer-event-triage.v1",
    "obelisk.player-principal-passive-activity-triage.v1",
    "obelisk.player-principal-passive-actionability.v1",
    "obelisk.player-principal-passive-target-triplet-candidate-summary.v1",
    "obelisk.player-principal-passive-server-activity-summary.v1",
    "obelisk.player-principal-passive-wait-metadata.v1",
    "obelisk.player-principal-public-reachability-check.v1",
    "obelisk.sdk-status-report.v1",
    "obelisk.sdk-status-side-lane-summary.v1",
    "obelisk.command-permission-route-post-evidence-p0-lock-simulation.v1",
    "obelisk.public-sdk-v1-completion-check.v1",
    "obelisk.public-sdk-v1-completion-summary.v1",
    "obelisk.public-sdk-v1-fastest-next-unblock.v1",
    "obelisk.public-sdk-v1-progress-normalization-trace.v1",
    "obelisk.public-sdk-v1-approved-in-game-evidence-status.v1",
    "obelisk.approved-in-game-evidence-status.v1",
    "obelisk.player-principal-lifecycle-player-notice-action.v1",
    "obelisk.player-notice-action.v1",
    "obelisk.player-principal-lifecycle-guarded-beta-notice-action.v1",
    "obelisk.scoped-release-statement-outcomes.v1",
    "obelisk.installed-sdk-package-shape.v1",
    "obelisk.internal-module-readiness.v1",
    "obelisk.passive-monitor-log-metadata.v1",
    "obelisk.passive-organic-player-detection.v1",
    "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
    "obelisk.players-identity-runtime-principal-lifecycle-window-manifest-check.v1",
    "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle-preflight.v1",
    "obelisk.players-identity-runtime-principal-lifecycle-evidence-bundle.v1",
}
STRAY_BETA_SIDECAR_SCHEMA_RE = re.compile(
    r"(?:beta[._-]?notice|discord[._-]?beta|discord[._-]?bridge|notice[._-]?action)",
    re.IGNORECASE,
)
STRAY_BETA_SIDECAR_NAME_RE = re.compile(
    r"(?:beta|discord|notice).*(?:sidecar|confirmed|receipt|action|prep)|"
    r"(?:sidecar|confirmed|receipt|action|prep).*(?:beta|discord|notice)",
    re.IGNORECASE,
)
PREACTIVATION_EXECUTOR_SCHEMA_RE = re.compile(
    r"(?:pre[._-]?activation|activation[._-]?preconditions?|executor)",
    re.IGNORECASE,
)
PREACTIVATION_EXECUTOR_SCHEMA_REASON = (
    "preactivation_or_executor_artifact_is_not_approved_runtime_evidence"
)
APPROVED_BUNDLE_NON_EVIDENCE_SCHEMA_ALIAS_BLOCKERS = (
    (
        PREACTIVATION_EXECUTOR_SCHEMA_RE,
        PREACTIVATION_EXECUTOR_SCHEMA_REASON,
    ),
    (
        re.compile(r"(?:progress[._-]?normalization[._-]?trace|source[._-]?overclaim)", re.IGNORECASE),
        "progress_or_source_overclaim_trace_is_not_approved_runtime_evidence",
    ),
    (
        re.compile(r"(?:passive|snapshot|watch(?:er|[._-]?only)|monitor[._-]?tick|triplet)", re.IGNORECASE),
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
    (
        re.compile(r"(?:request[._-]?pack|window[._-]?request)", re.IGNORECASE),
        "request_pack_or_window_request_schema_is_not_approved_runtime_evidence",
    ),
)
FORBIDDEN_SHORTCUT_ALIAS_CLASSES = (
    "passive_snapshot_or_triplet_shortcut",
    "notice_or_discord_shortcut",
    "status_or_summary_shortcut",
)
NON_CLAIMS = (
    "closure request only; does not authorize server operations",
    "does not authorize marker/env changes, starts, restarts, or stops",
    "does not create window-manifest.env, preflight-post.json, or approved runtime bundle artifacts",
    "does not claim approved runtime evidence readiness",
    "closure requests are non-evidence even when every sibling artifact is present",
    "SDK/P0 changes require copied-bundle checker acceptance, not closure request input completeness",
    "historical candidate sidecars, passive complete triplets, request packs, preflight outputs, window manifests, and status report paths do not authorize current-turn operations or count as approved runtime evidence",
    "does not claim public readiness, public SDK readiness, runtime readiness, v1 completion, or stable SDK status",
    "does not promote player identity/principal, permissions/admin, commands, lookup, mutation, return override, or ResourceHandle",
    "does not send Discord; if a future player-dependent window names a beta testers notice path, a real current-turn approved notice action must happen before activation",
)
FRESH_CURRENT_TURN_OPERATOR_MESSAGE_SOURCE = "fresh_current_turn_operator_message"
NO_OPERATOR_AUTHORITY_SOURCE = "not_applicable"
READY_LOG_COPY_POST_WINDOW_EXECUTE_FLAGS = (
    "--allow-post-window-sidecar-generation",
    "--allow-post-window-preflight-live-read",
)
READY_LOG_COPY_SIDECAR_GUIDANCE_KEYS = (
    "copy_helper_execute_sidecar_flags",
    "copy_helper_execute_sidecar_flags_scope",
    "copy_helper_execute_sidecar_flags_authorize_this_report",
    "copy_helper_execute_sidecar_flags_count_as_evidence",
    "post_window_sidecar_generation_authorized_by_this_report",
    "post_window_preflight_live_read_authorized_by_this_report",
    "post_window_sidecar_generation_counts_as_approved_runtime_evidence",
    "post_window_preflight_live_read_counts_as_approved_runtime_evidence",
)
POST_WINDOW_ACTION_CONTRACT_KEYS = (
    "post_window_action_contract",
    "post_window_copy_bundle_preconditions",
    "dry_run_first_required",
    "dry_run_must_complete_before_execute",
    "dry_run_report_path",
    "required_dry_run_artifacts",
    "dry_run_report_counts_as_approved_runtime_evidence",
    "dry_run_report_authorizes_runtime",
    "sidecar_generation_required",
    "sidecar_generation_authorized_by_this_report",
    "sidecar_generation_counts_as_approved_runtime_evidence",
)
EXACT_COPIED_TRIPLET_ACTION_GUIDANCE_KEYS = (
    "required_copied_lifecycle_event_triplet",
    "required_copied_lifecycle_event_triplet_labels",
    "required_copied_lifecycle_event_triplet_case",
    "required_copied_lifecycle_event_triplet_label",
    "exact_copied_lifecycle_event_triplet_required_before_actionable",
    "exact_copied_lifecycle_event_triplet_matched",
    "matched_copied_lifecycle_event_triplet",
    "missing_copied_lifecycle_event_triplet",
    "missing_copied_lifecycle_event_triplet_labels",
    "copied_lifecycle_triplet_match_failures",
    "partial_start_end_present",
    "missing_strict_rejected_start",
    "strict_rejected_start_expected_shape",
    "strict_rejected_start_observed_shape",
    "strict_rejected_start_observed_shape_counts_as_approved_runtime_evidence",
    "duplicate_accepted_role_events",
    "lifecycle_event_ambiguity_blockers",
    "actionable_without_exact_copied_triplet",
)


def jsonable_triplet_case(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": case["label"],
        "role": case["role"],
        "target": case["target"],
        "post_original": case["post_original"],
        "copied_bool_fields": list(case["copied_bool_fields"]),
        "copied_bool_values": list(case["copied_bool_values"]),
        "redacted_count": case["redacted_count"],
        "redacted_fields": list(case["redacted_fields"]),
        "apply_status": case["apply_status"],
        "principal_action": case["principal_action"],
        "correlation_status": case["correlation_status"],
        "principal_id_logged": case["principal_id_logged"],
        "principal_generation_logged": case["principal_generation_logged"],
        "delivery_claim": case["delivery_claim"],
    }


def required_copied_lifecycle_event_triplet() -> list[dict[str, Any]]:
    return [
        jsonable_triplet_case(case)
        for case in REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET
    ]


def csv_log_values(value: str | None) -> list[str]:
    if value is None or value == "":
        return []
    return value.split(",")


def object_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def log_key_values(line: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for token in line.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        values[key] = value.rstrip(".")
    return values


def observed_copied_lifecycle_event_case(
    *,
    role: str,
    line_number: int,
    sequence: str,
    values: dict[str, str],
) -> dict[str, Any]:
    return {
        "line": line_number,
        "sequence": sequence,
        "role": role,
        "target": values.get("target"),
        "post_original": values.get("post_original"),
        "copied_bool_fields": csv_log_values(values.get("copied_bool_fields")),
        "copied_bool_values": csv_log_values(values.get("copied_bool_values")),
        "redacted_count": values.get("redacted_count"),
        "redacted_fields": csv_log_values(values.get("redacted_fields")),
        "apply_status": values.get("apply_status"),
        "principal_action": values.get("principal_action"),
        "correlation_status": values.get("correlation_status"),
        "principal_id_logged": values.get("principal_id_logged"),
        "principal_generation_logged": values.get("principal_generation_logged"),
        "delivery_claim": values.get("delivery_claim"),
    }


def copied_lifecycle_triplet_failure_reason(
    observed: dict[str, Any],
    expected: dict[str, Any],
) -> str | None:
    if observed.get("target") != expected["target"]:
        return "copied_lifecycle_event_target_mismatch"
    if observed.get("post_original") != expected["post_original"]:
        return "copied_lifecycle_event_post_original_mismatch"
    if tuple(observed.get("copied_bool_fields", [])) != tuple(expected["copied_bool_fields"]):
        return "copied_lifecycle_event_bool_fields_mismatch"
    if tuple(observed.get("copied_bool_values", [])) != tuple(expected["copied_bool_values"]):
        return "copied_lifecycle_event_bool_values_mismatch"
    if observed.get("redacted_count") != expected["redacted_count"]:
        return "copied_lifecycle_event_redacted_count_mismatch"
    if tuple(observed.get("redacted_fields", [])) != tuple(expected["redacted_fields"]):
        return "copied_lifecycle_event_redacted_fields_mismatch"
    expected_status = REQUIRED_LIFECYCLE_STATUS_PROOFS[str(expected["role"])]
    if observed.get("apply_status") != expected_status["apply_status"]:
        return "copied_lifecycle_event_apply_status_mismatch"
    if observed.get("correlation_status") != expected_status["correlation_status"]:
        return "copied_lifecycle_event_correlation_status_mismatch"
    if observed.get("principal_action") != expected["principal_action"]:
        return "copied_lifecycle_event_principal_action_mismatch"
    if observed.get("principal_id_logged") != expected["principal_id_logged"]:
        return "copied_lifecycle_event_principal_id_logged_mismatch"
    if observed.get("principal_generation_logged") != expected["principal_generation_logged"]:
        return "copied_lifecycle_event_principal_generation_logged_mismatch"
    if observed.get("delivery_claim") != expected["delivery_claim"]:
        return "copied_lifecycle_event_delivery_claim_mismatch"
    return None


def copied_lifecycle_event_shape(observed: dict[str, Any]) -> str:
    values = observed.get("copied_bool_values")
    copied_bool_values = values if isinstance(values, list) else []
    return f"{observed.get('target')}({','.join(str(value) for value in copied_bool_values)})"


def strict_rejected_start_observed_shape(
    observed: dict[str, Any],
    *,
    accepted_as_lifecycle_role: bool,
    reason: str | None,
) -> dict[str, Any]:
    return {
        "shape": copied_lifecycle_event_shape(observed),
        "line": observed.get("line"),
        "sequence": observed.get("sequence"),
        "inside_capture_window": None,
        "timestamp_prefix": None,
        "timestamp_error": "not_evaluated_by_closure_request",
        "target": observed.get("target"),
        "role": observed.get("role"),
        "copied_bool_fields": observed.get("copied_bool_fields"),
        "copied_bool_values": observed.get("copied_bool_values"),
        "principal_action": observed.get("principal_action"),
        "apply_status": observed.get("apply_status"),
        "correlation_status": observed.get("correlation_status"),
        "expected_shape": STRICT_REJECTED_START_EXPECTED_SHAPE,
        "reason": reason,
        "accepted_as_lifecycle_role": accepted_as_lifecycle_role,
        "accepted_as_strict_rejected_start": accepted_as_lifecycle_role,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "passive_snapshots_as_evidence": False,
    }


def copied_triplet_action_requirements(
    role_state: dict[str, Any] | None = None,
    *,
    required_case: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if role_state is None:
        matched = False
        matched_cases: list[dict[str, Any]] = []
        missing_cases = required_copied_lifecycle_event_triplet()
        missing_labels = list(REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS)
        failures: list[dict[str, Any]] = []
    else:
        matched = role_state.get("exact_copied_lifecycle_event_triplet_complete") is True
        matched_cases = object_list(role_state.get("matched_copied_lifecycle_event_triplet"))
        missing_cases = object_list(role_state.get("missing_copied_lifecycle_event_triplet"))
        missing_labels = [
            str(label)
            for label in role_state.get("missing_copied_lifecycle_event_triplet_labels", [])
        ]
        failures = object_list(role_state.get("copied_lifecycle_triplet_match_failures"))
        partial_start_end_present = role_state.get("partial_start_end_present", False) is True
        missing_strict_rejected_start = role_state.get("missing_strict_rejected_start", True) is True
        strict_rejected_start_observed = role_state.get("strict_rejected_start_observed_shape")
        strict_rejected_start_observed_shape_counts = role_state.get(
            "strict_rejected_start_observed_shape_counts_as_approved_runtime_evidence",
            False,
        ) is True
    if role_state is None:
        partial_start_end_present = False
        missing_strict_rejected_start = True
        strict_rejected_start_observed = None
        strict_rejected_start_observed_shape_counts = False
    payload: dict[str, Any] = {
        "required_copied_lifecycle_event_triplet": required_copied_lifecycle_event_triplet(),
        "required_copied_lifecycle_event_triplet_labels": list(
            REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS
        ),
        "exact_copied_lifecycle_event_triplet_required_before_actionable": True,
        "exact_copied_lifecycle_event_triplet_matched": matched,
        "matched_copied_lifecycle_event_triplet": matched_cases,
        "missing_copied_lifecycle_event_triplet": missing_cases,
        "missing_copied_lifecycle_event_triplet_labels": missing_labels,
        "copied_lifecycle_triplet_match_failures": failures,
        "partial_start_end_present": partial_start_end_present,
        "missing_strict_rejected_start": missing_strict_rejected_start,
        "strict_rejected_start_expected_shape": STRICT_REJECTED_START_EXPECTED_SHAPE,
        "strict_rejected_start_observed_shape": strict_rejected_start_observed,
        "strict_rejected_start_observed_shape_counts_as_approved_runtime_evidence": (
            strict_rejected_start_observed_shape_counts
        ),
        "duplicate_accepted_role_events": object_list(
            role_state.get("duplicate_accepted_role_events")
        )
        if role_state is not None
        else [],
        "lifecycle_event_ambiguity_blockers": list(
            role_state.get("lifecycle_event_ambiguity_blockers", [])
        )
        if role_state is not None
        else [],
        "actionable_without_exact_copied_triplet": False,
    }
    if required_case is not None:
        payload["required_copied_lifecycle_event_triplet_case"] = jsonable_triplet_case(required_case)
        payload["required_copied_lifecycle_event_triplet_label"] = required_case["label"]
    return payload


def copied_triplet_blockers(role_state: dict[str, Any] | None = None) -> list[str]:
    if role_state is None:
        labels = REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS
    else:
        labels = role_state.get("missing_copied_lifecycle_event_triplet_labels", [])
    return [f"copied-lifecycle-triplet/{label}" for label in labels]


def false_authorization_and_evidence_flags() -> dict[str, bool]:
    return dict(NO_AUTHORIZATION_FLAGS)


def machine_false_claim_flags() -> dict[str, bool]:
    return {
        **false_authorization_and_evidence_flags(),
        "authorized_by_this_report": False,
        "approved_runtime_evidence_accepted_by_checker": False,
        "checker_acceptance_recorded_by_this_report": False,
        "grants_readiness_claims": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", required=True, type=Path, help="Copied evidence directory to inspect.")
    parser.add_argument("--instance", help="Exact target instance for approval-scope text, if known.")
    parser.add_argument("--map", dest="map_name", help="Exact target map for approval-scope text, if known.")
    parser.add_argument("--query-port", help="Exact Steam query port for target-bound passive-wait text, if known.")
    parser.add_argument(
        "--expected-binary-sha256",
        default=DEFAULT_BINARY_SHA256,
        help="Expected ShooterGameServer SHA256 to include in planned command text.",
    )
    parser.add_argument("--obelisk-commit", help="Reviewed Obelisk commit/build id for bundle command text.")
    parser.add_argument("--reviewed-by", help="Reviewer token/name placeholder for bundle command text.")
    parser.add_argument("--review-note", help="Short review note placeholder for bundle command text.")
    parser.add_argument(
        "--the-island-off",
        action="store_true",
        help="Record that TheIsland is currently off and must stay off unless separately approved.",
    )
    parser.add_argument(
        "--two-server-cap-preserved",
        action="store_true",
        help="Record that any future operation must preserve the two-server cap.",
    )
    parser.add_argument(
        "--future-window-needs-players",
        action="store_true",
        help="Record that a future current-turn evidence window would need player participation.",
    )
    parser.add_argument(
        "--notice-path",
        default=NOTICE_PATH_NOT_APPLICABLE,
        help="Current-turn notice path label to preserve in the request, or not_applicable.",
    )
    parser.add_argument(
        "--post-reboot-monitor-log",
        type=Path,
        help="Optional passive monitor log path to record as post-reboot non-evidence context.",
    )
    parser.add_argument(
        "--confirmed-beta-notice-json",
        type=Path,
        help="Optional confirmed beta notice JSON path to record as notice-action non-evidence context.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Stdout format.",
    )
    parser.add_argument("--json-output", type=Path, help="Optional repo-local JSON report path.")
    parser.add_argument("--markdown-output", type=Path, help="Optional repo-local Markdown report path.")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.notice_path != NOTICE_PATH_NOT_APPLICABLE and not SAFE_NOTICE_PATH_RE.fullmatch(args.notice_path):
        raise SystemExit("--notice-path contains unsafe characters")
    if args.notice_path != NOTICE_PATH_NOT_APPLICABLE and FORBIDDEN_NOTICE_PATH_VALUE_RE.search(args.notice_path):
        raise SystemExit("--notice-path must be a label, not a URL, webhook, or token")


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


def command_binding_blocker(
    blockers: list[dict[str, Any]],
    reason: str,
    *,
    label: str = "bundle_command_commit_binding",
    **extra: Any,
) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def bundle_command_commit_binding(window_manifest: Path, args: argparse.Namespace) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    current_commit = current_obelisk_commit()
    if current_commit is None:
        command_binding_blocker(blockers, "current_obelisk_commit_unavailable")

    manifest_commit: str | None = None
    if window_manifest.is_file():
        parse_blockers: list[dict[str, Any]] = []
        fields = parse_env_sidecar(window_manifest, "window-manifest.env", parse_blockers)
        blockers.extend(parse_blockers)
        raw_commit = fields.get("obelisk_commit")
        if raw_commit is None:
            command_binding_blocker(
                blockers,
                "window_manifest_obelisk_commit_missing",
                label="window-manifest.env",
            )
        elif GIT_COMMIT_RE.fullmatch(raw_commit) is None:
            command_binding_blocker(
                blockers,
                "window_manifest_obelisk_commit_invalid",
                label="window-manifest.env",
                actual=raw_commit,
            )
        else:
            manifest_commit = raw_commit
            if current_commit is not None and manifest_commit != current_commit:
                command_binding_blocker(
                    blockers,
                    "window_manifest_obelisk_commit_not_current_head",
                    label="window-manifest.env",
                    expected=current_commit,
                    actual=manifest_commit,
                )
    else:
        command_binding_blocker(
            blockers,
            "window_manifest_missing_for_bundle_command_commit_binding",
            label="window-manifest.env",
            path=str(window_manifest),
        )

    requested_commit = args.obelisk_commit
    if requested_commit is not None:
        if GIT_COMMIT_RE.fullmatch(requested_commit) is None:
            command_binding_blocker(
                blockers,
                "bundle_command_obelisk_commit_argument_invalid",
                actual=requested_commit,
            )
        elif manifest_commit is not None and requested_commit != manifest_commit:
            command_binding_blocker(
                blockers,
                "bundle_command_obelisk_commit_argument_mismatch",
                expected=manifest_commit,
                actual=requested_commit,
            )
        elif current_commit is not None and requested_commit != current_commit:
            command_binding_blocker(
                blockers,
                "bundle_command_obelisk_commit_argument_not_current_head",
                expected=current_commit,
                actual=requested_commit,
            )

    command_commit = manifest_commit if not blockers else None
    return {
        "ready": command_commit is not None,
        "current_obelisk_commit": current_commit,
        "window_manifest_obelisk_commit": manifest_commit,
        "requested_obelisk_commit": requested_commit,
        "command_obelisk_commit": command_commit,
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_claim": "bundle command commit binding only; does not create or approve runtime evidence",
    }


def is_under_path(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def reject_server_root_output(path: Path, label: str) -> Path:
    expanded = path.expanduser()
    symlink = protected_paths.first_symlink_component(expanded)
    if symlink is not None:
        raise SystemExit(f"{label} must not use a symlink component: {symlink}")
    resolved = expanded.resolve()
    server_root = SERVER_ROOT.resolve()
    direct_under_server_root = expanded.is_absolute() and is_under_path(expanded, SERVER_ROOT)
    resolved_under_server_root = is_under_path(resolved, server_root)
    if direct_under_server_root or resolved_under_server_root:
        raise SystemExit(f"{label} must not write under {SERVER_ROOT}: {resolved}")
    return resolved


def resolve_output_paths(args: argparse.Namespace) -> dict[str, Path]:
    outputs: dict[str, Path] = {}
    for key, label in (("json_output", "--json-output"), ("markdown_output", "--markdown-output")):
        value = getattr(args, key)
        if value is None:
            continue
        outputs[key] = reject_server_root_output(value, label)
    return outputs


def resolve_evidence_dir(path: Path) -> tuple[Path, list[dict[str, str]]]:
    blockers: list[dict[str, str]] = []
    expanded = path.expanduser()
    symlink = protected_paths.first_symlink_component(expanded)
    if symlink is not None:
        blockers.append(
            {
                "reason": "evidence_dir_symlink_component",
                "path": str(symlink),
            }
        )
        return expanded.absolute(), blockers
    status = protected_paths.protected_path_status(
        expanded,
        protected_root=SERVER_ROOT,
        approved_roots=protected_paths.approved_offline_workspace_roots(),
    )
    if status.protected:
        blockers.append(
            {
                "reason": "evidence_dir_under_live_server_root",
                "path": str(status.resolved),
            }
        )
    return status.resolved, blockers


def closure_compatible_run_id_hint(run_id: str) -> str | None:
    if "passive" not in run_id.casefold() and "monitor" not in run_id.casefold():
        return None
    match = PASSIVE_MONITOR_RUN_ID_RE.search(run_id)
    if match is None:
        return None
    return f"{match.group(0)}-player-principal-lifecycle"


def closure_compatible_copy_guidance(evidence_dir: Path) -> dict[str, Any]:
    run_id = evidence_dir.name
    suggested_run_id = closure_compatible_run_id_hint(run_id)
    suggested_dir = evidence_dir.parent / suggested_run_id if suggested_run_id else None
    passive_monitor_root = suggested_run_id is not None
    source_valid = RUN_ID_RE.fullmatch(run_id) is not None
    return {
        "schema": "obelisk.player-principal-lifecycle-closure-compatible-copy-guidance.v1",
        "source_evidence_dir": str(evidence_dir),
        "source_root_role": "source_evidence_root_supplied_to_closure_helper",
        "source_run_id": run_id,
        "source_run_id_valid_for_closure": source_valid,
        "source_root_valid_for_closure": source_valid,
        "source_looks_like_passive_monitor_root": passive_monitor_root,
        "required_run_id_pattern": RUN_ID_RE.pattern,
        "suggested_closure_run_id": suggested_run_id,
        "suggested_closure_evidence_dir": str(suggested_dir) if suggested_dir else None,
        "suggested_valid_closure_run_id": suggested_run_id,
        "suggested_valid_closure_evidence_dir": str(suggested_dir) if suggested_dir else None,
        "suggested_valid_closure_root_role": (
            "suggested_valid_closure_root_for_manual_staging"
            if suggested_dir
            else "not_available_from_source_run_id"
        ),
        "source_accepted_as_closure_evidence_dir": False if passive_monitor_root else None,
        "source_becomes_closure_root": False if passive_monitor_root else None,
        "passive_monitor_root_accepted_as_closure_evidence_dir": False,
        "passive_monitor_root_accepted_by_closure_request": False,
        "passive_monitor_root_must_not_be_used_as_closure_evidence_dir": True,
        "copy_or_stage_into_closure_compatible_run_required_before_closure": True,
        "explicit_execution_write_flags_required": True,
        "copy_or_stage_authorized_by_this_report": False,
        "server_operations_authorized": False,
        "workspace_writes_authorized": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "non_authorization": (
            "source-shape guidance only; passive monitor roots are diagnostic context and "
            "must be copied or replaced by a closure-compatible lifecycle evidence root before closure"
        ),
    }


def evidence_source_state(evidence_dir: Path) -> dict[str, Any]:
    run_id = evidence_dir.name
    parent_name = evidence_dir.parent.name
    run_id_valid = RUN_ID_RE.fullmatch(run_id) is not None
    parent_valid = parent_name == EXPECTED_EVIDENCE_PARENT
    copy_guidance = closure_compatible_copy_guidance(evidence_dir)
    blockers: list[dict[str, Any]] = []
    if not run_id_valid:
        blockers.append(
            {
                "reason": "invalid_player_principal_lifecycle_run_id",
                "path": str(evidence_dir),
                "observed_run_id": run_id,
                "expected_pattern": RUN_ID_RE.pattern,
                "closure_compatible_copy_guidance": copy_guidance,
                "source_looks_like_passive_monitor_root": copy_guidance[
                    "source_looks_like_passive_monitor_root"
                ],
                "suggested_closure_run_id": copy_guidance["suggested_closure_run_id"],
                "suggested_closure_evidence_dir": copy_guidance["suggested_closure_evidence_dir"],
                "suggested_valid_closure_run_id": copy_guidance["suggested_valid_closure_run_id"],
                "suggested_valid_closure_evidence_dir": copy_guidance[
                    "suggested_valid_closure_evidence_dir"
                ],
                "source_root_role": copy_guidance["source_root_role"],
                "suggested_valid_closure_root_role": copy_guidance[
                    "suggested_valid_closure_root_role"
                ],
                "copy_or_stage_into_closure_compatible_run_required_before_closure": True,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_evidence": False,
            }
        )
    if not parent_valid:
        blockers.append(
            {
                "reason": "evidence_dir_parent_not_live_validation_logs",
                "path": str(evidence_dir),
                "observed_parent": parent_name,
                "expected_parent": EXPECTED_EVIDENCE_PARENT,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_evidence": False,
                "passive_snapshots_as_evidence": False,
            }
        )
    return {
        "run_id": run_id,
        "run_id_valid": run_id_valid,
        "parent": parent_name,
        "expected_parent": EXPECTED_EVIDENCE_PARENT,
        "parent_valid": parent_valid,
        "shape_valid": not blockers,
        "closure_compatible_copy_guidance": copy_guidance,
        "blockers": blockers,
        "classification": "copied_live_validation_run_directory" if not blockers else "non_evidence_source_directory",
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
    }


def sibling_state(evidence_dir: Path, label: str, relative_path: str, *, inspect: bool = True) -> dict[str, Any]:
    path = evidence_dir / relative_path
    if not inspect:
        return {
            "label": label,
            "relative_path": relative_path,
            "path": str(path),
            "resolved_path": str(path),
            "present": False,
            "symlink_component": None,
            "sha256": None,
            "size_bytes": None,
            "hash_path_bound": False,
        }
    symlink = protected_paths.first_symlink_component(path)
    present = symlink is None and path.is_file()
    sha256_value = sha256_file(path) if present else None
    size_bytes = path.stat().st_size if present else None
    return {
        "label": label,
        "relative_path": relative_path,
        "path": str(path),
        "resolved_path": str(path.resolve()) if symlink is None else str(path),
        "present": present,
        "symlink_component": None if symlink is None else str(symlink),
        "sha256": sha256_value,
        "size_bytes": size_bytes,
        "hash_path_bound": present and sha256_value is not None,
    }


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binding_from_sibling_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": state["label"],
        "relative_path": state["relative_path"],
        "path": state["path"],
        "resolved_path": state.get("resolved_path"),
        "present": state.get("present") is True,
        "symlink_component": state.get("symlink_component"),
        "sha256": state.get("sha256"),
        "size_bytes": state.get("size_bytes"),
        "hash_path_bound": state.get("hash_path_bound") is True,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
    }


def artifact_binding_report(
    evidence_dir: Path,
    sibling_states: list[dict[str, Any]],
) -> dict[str, Any]:
    bindings = [binding_from_sibling_state(state) for state in sibling_states]
    by_relative_path = {
        str(binding["relative_path"]): binding for binding in bindings
    }
    copied_log = by_relative_path.get("Obelisk.log")
    sidecars = [
        by_relative_path[relative_path]
        for relative_path in REQUIRED_SIDECARS
        if relative_path in by_relative_path
    ]
    bundle_inputs = [
        binding
        for binding in bindings
        if binding["relative_path"] != APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH
    ]
    approved_bundle = by_relative_path.get(APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH)
    missing = [
        str(binding["relative_path"])
        for binding in bindings
        if binding["hash_path_bound"] is not True
    ]
    return {
        "schema": ARTIFACT_BINDINGS_SCHEMA,
        "evidence_dir": str(evidence_dir),
        "copied_log": copied_log,
        "required_sidecars": sidecars,
        "bundle_input_artifacts": bundle_inputs,
        "approved_runtime_manifest": approved_bundle,
        "all_artifacts": bindings,
        "by_relative_path": by_relative_path,
        "copied_log_hash_path_bound": (
            isinstance(copied_log, dict) and copied_log.get("hash_path_bound") is True
        ),
        "required_sidecars_hash_path_bound": all(
            binding["hash_path_bound"] is True for binding in sidecars
        ),
        "bundle_input_artifacts_hash_path_bound": all(
            binding["hash_path_bound"] is True for binding in bundle_inputs
        ),
        "complete_sibling_set_hash_path_bound": all(
            binding["hash_path_bound"] is True for binding in bindings
        ),
        "missing_hash_path_bindings": missing,
        "hash_path_binding_counts_as_approved_runtime_evidence": False,
        "hash_path_binding_counts_as_runtime_evidence": False,
        "hash_path_binding_counts_as_sdk_evidence": False,
    }


def nested_mapping(value: Any, *keys: str) -> dict[str, Any] | None:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current if isinstance(current, dict) else None


def sidecar_blocker(blockers: list[dict[str, Any]], reason: str, relative_path: str, **extra: Any) -> None:
    blockers.append({"reason": reason, "relative_path": relative_path, **extra})


def load_json_sidecar(path: Path, relative_path: str, blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sidecar_blocker(blockers, "sidecar_json_invalid", relative_path, detail=str(exc))
        return None
    except OSError as exc:
        sidecar_blocker(blockers, "sidecar_unreadable", relative_path, detail=str(exc))
        return None
    if not isinstance(payload, dict):
        sidecar_blocker(blockers, "sidecar_json_not_object", relative_path)
        return None
    return payload


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def ready_log_copy_report_context(evidence_dir: Path, *, inspect: bool) -> dict[str, Any]:
    relative_path = READY_LOG_COPY_RELATIVE_PATH
    path = evidence_dir / relative_path
    context: dict[str, Any] = {
        "relative_path": relative_path,
        "path": str(path),
        "present": False,
        "checked": False,
        "classification": (
            "ready_log_copy_report_not_inspected"
            if not inspect
            else "ready_log_copy_report_absent"
        ),
        "schema": None,
        "schema_valid": False,
        "status": None,
        "ready": False,
        "reported_ready": None,
        "ready_to_copy": None,
        "copy_readiness": "not_provided",
        "copied": False,
        "execute_requested": None,
        "target_log": None,
        "roles_present": [],
        "missing_roles": [],
        "analysis_missing_roles": [],
        "reported_blockers": [],
        "validation_blockers": [],
        "blockers": [],
        "source_input": {},
        "source_log_safety": {},
        "source_log_not_ready": {},
        "observer_only_no_role_window": {},
        "observer_only_no_role_window_detected": False,
        "active_observer_only_no_role_window": False,
        "post_window_observer_only_no_role_window": False,
        "observer_only_no_role_window_state": None,
        "post_window_closure_action": None,
        "accepted_by_approved_sibling_set_checker": False,
        "approved_sibling_set_checker_acceptance_recorded": False,
        "copied_log_approved_runtime_evidence_requires_sibling_set_checker": True,
        "counts_as_approved_runtime_evidence": False,
        "copy_report_counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "runtime_evidence_ready": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "dry_run_success_counts_as_approved_runtime_evidence": False,
        "json_output_counts_as_approved_runtime_evidence": False,
        "report_output_counts_as_approved_runtime_evidence": False,
    }
    if not inspect:
        return context

    symlink = protected_paths.first_symlink_component(path)
    if symlink is not None:
        blocker = {
            "reason": "ready_log_copy_report_path_symlink_component",
            "relative_path": relative_path,
            "symlink": str(symlink),
        }
        context.update(
            {
                "checked": True,
                "classification": "invalid_ready_log_copy_report_non_evidence",
                "validation_blockers": [blocker],
                "blockers": [blocker["reason"]],
            }
        )
        return context
    if not path.is_file():
        return context

    context["present"] = True
    context["checked"] = True
    validation_blockers: list[dict[str, Any]] = []
    payload = load_json_sidecar(path, relative_path, validation_blockers)
    if payload is None:
        context.update(
            {
                "classification": "invalid_ready_log_copy_report_non_evidence",
                "validation_blockers": validation_blockers,
                "blockers": [blocker["reason"] for blocker in validation_blockers],
            }
        )
        return context

    schema = payload.get("schema")
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    source_input = payload.get("source_input")
    source_log_safety = payload.get("source_log_safety")
    source_log_not_ready = payload.get("source_log_not_ready")
    if not isinstance(source_log_not_ready, dict):
        source_log_not_ready = payload.get("observer_only_no_role_window")
    if not isinstance(source_log_not_ready, dict):
        source_log_not_ready = {}
    reported_blockers = string_list(payload.get("blockers"))
    roles_present = string_list(payload.get("roles_present"))
    missing_roles = string_list(payload.get("missing_roles"))
    analysis_missing_roles = string_list(analysis.get("missing_roles"))
    if not missing_roles and analysis_missing_roles:
        missing_roles = analysis_missing_roles
    if schema != READY_LOG_COPY_SCHEMA:
        validation_blockers.append(
            {
                "reason": "ready_log_copy_report_schema_mismatch",
                "relative_path": relative_path,
                "expected": READY_LOG_COPY_SCHEMA,
                "actual": schema,
            }
        )
    for key in (
        "ready",
        "approved_runtime_evidence",
        "approved_runtime_evidence_present",
        "approved_runtime_evidence_ready",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_evidence",
        "runtime_ready",
        "public_sdk_ready",
    ):
        if payload.get(key, False) is not False:
            validation_blockers.append(
                {
                    "reason": f"ready_log_copy_report_{key}_not_false",
                    "relative_path": relative_path,
                    "actual": payload.get(key),
                }
            )
    classification = (
        "invalid_ready_log_copy_report_non_evidence"
        if validation_blockers
        else "ready_log_copy_report_non_evidence_requires_approved_sibling_set_checker"
        if payload.get("ready_to_copy") is True
        else "blocked_ready_log_copy_report_non_evidence"
    )
    context.update(
        {
            "classification": classification,
            "schema": schema,
            "schema_valid": schema == READY_LOG_COPY_SCHEMA,
            "status": payload.get("status"),
            "ready": False,
            "reported_ready": payload.get("ready"),
            "ready_to_copy": payload.get("ready_to_copy"),
            "copy_readiness": payload.get("copy_readiness", "not_provided"),
            "copied": payload.get("copied") is True,
            "execute_requested": payload.get("execute_requested"),
            "target_log": payload.get("target_log") if isinstance(payload.get("target_log"), str) else None,
            "roles_present": roles_present,
            "missing_roles": missing_roles,
            "analysis_missing_roles": analysis_missing_roles,
            "reported_blockers": reported_blockers,
            "validation_blockers": validation_blockers,
            "blockers": [
                *[blocker["reason"] for blocker in validation_blockers],
                *reported_blockers,
            ],
            "source_input": source_input if isinstance(source_input, dict) else {},
            "source_log_safety": source_log_safety if isinstance(source_log_safety, dict) else {},
            "source_log_not_ready": source_log_not_ready,
            "observer_only_no_role_window": source_log_not_ready,
            "observer_only_no_role_window_detected": (
                payload.get("observer_only_no_role_window_detected") is True
                or source_log_not_ready.get("observer_only_no_role_window_detected") is True
            ),
            "active_observer_only_no_role_window": (
                payload.get("active_observer_only_no_role_window") is True
                or source_log_not_ready.get("active_observer_only_no_role_window") is True
            ),
            "post_window_observer_only_no_role_window": (
                payload.get("post_window_observer_only_no_role_window") is True
                or source_log_not_ready.get("post_window_observer_only_no_role_window") is True
            ),
            "observer_only_no_role_window_state": (
                payload.get("observer_only_no_role_window_state")
                if isinstance(payload.get("observer_only_no_role_window_state"), str)
                else source_log_not_ready.get("window_state")
            ),
            "post_window_closure_action": (
                payload.get("post_window_closure_action")
                if isinstance(payload.get("post_window_closure_action"), str)
                else source_log_not_ready.get("post_window_closure_action")
            ),
        }
    )
    return context


def ready_log_copy_post_window_no_triplet(report: dict[str, Any]) -> bool:
    if report.get("present") is not True or report.get("ready_to_copy") is True:
        return False
    required_roles = set(REQUIRED_LIFECYCLE_EVENT_ROLES)
    roles_present = set(string_list(report.get("roles_present")))
    missing_roles = set(string_list(report.get("missing_roles")))
    if roles_present or missing_roles != required_roles:
        return False
    if report.get("copy_readiness") != "blocked_missing_lifecycle_roles":
        return False
    source_state = report.get("source_log_not_ready")
    if not isinstance(source_state, dict):
        source_state = report.get("observer_only_no_role_window")
    if not isinstance(source_state, dict):
        source_state = {}
    return (
        report.get("post_window_observer_only_no_role_window") is True
        or source_state.get("post_window_observer_only_no_role_window") is True
        or report.get("observer_only_no_role_window_state") == "post_window"
        or source_state.get("window_state") == "post_window"
    )


def ready_log_copy_active_no_triplet(report: dict[str, Any]) -> bool:
    if report.get("present") is not True or report.get("ready_to_copy") is True:
        return False
    required_roles = set(REQUIRED_LIFECYCLE_EVENT_ROLES)
    roles_present = set(string_list(report.get("roles_present")))
    missing_roles = set(string_list(report.get("missing_roles")))
    if roles_present or missing_roles != required_roles:
        return False
    if report.get("copy_readiness") != "blocked_missing_lifecycle_roles":
        return False
    source_state = report.get("source_log_not_ready")
    if not isinstance(source_state, dict):
        source_state = report.get("observer_only_no_role_window")
    if not isinstance(source_state, dict):
        source_state = {}
    return (
        report.get("active_observer_only_no_role_window") is True
        or source_state.get("active_observer_only_no_role_window") is True
        or report.get("observer_only_no_role_window_state") == "in_progress"
        or source_state.get("window_state") == "in_progress"
    )


def ready_log_copy_active_or_post_window_no_triplet(report: dict[str, Any]) -> bool:
    return ready_log_copy_active_no_triplet(report) or ready_log_copy_post_window_no_triplet(report)


def parse_env_sidecar(path: Path, relative_path: str, blockers: list[dict[str, Any]]) -> dict[str, str]:
    fields: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        sidecar_blocker(blockers, "sidecar_unreadable", relative_path, detail=str(exc))
        return fields
    for line_number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            sidecar_blocker(blockers, "sidecar_env_line_not_key_value", relative_path, line=line_number)
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", key):
            sidecar_blocker(blockers, "sidecar_env_key_unsafe", relative_path, line=line_number, key=key)
            continue
        if key in fields:
            sidecar_blocker(blockers, "sidecar_env_duplicate_key", relative_path, line=line_number, key=key)
            continue
        fields[key] = value
    return fields


def sidecar_key_tokens(key: str) -> set[str]:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key)
    separated = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", separated)
    return {token for token in re.split(r"[^A-Za-z0-9]+", separated.lower()) if token}


def normalized_sidecar_key(key: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
    separated = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", separated)
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


NORMALIZED_SIDECAR_FALSE_CLAIM_KEYS = {
    normalized_sidecar_key(key) for key in SIDECAR_FALSE_CLAIM_KEYS
}
NORMALIZED_SIDECAR_NONZERO_PROGRESS_KEYS = {
    normalized_sidecar_key(key) for key in SIDECAR_NONZERO_PROGRESS_KEYS
}
NORMALIZED_SIDECAR_GENERIC_STATUS_KEYS = {
    normalized_sidecar_key(key) for key in SIDECAR_GENERIC_STATUS_KEYS
}
SIDECAR_PATH_CONTEXT_DOMAIN_TOKENS = {
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
}
SIDECAR_PATH_CONTEXT_POSITIVE_LEAF_TOKENS = {
    "accepted",
    "approved",
    "complete",
    "completed",
    "observed",
    "ready",
    "validated",
}
SIDECAR_PATH_CONTEXT_NON_EVIDENCE_TOKENS = {
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
}
SIDECAR_NEGATIVE_STATUS_TOKENS = {
    "blocked",
    "candidate",
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
SIDECAR_POSITIVE_STATUS_TOKENS = {
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
    "validated",
    "yes",
}


def sidecar_negative_claim_context(key: object, value: Any) -> bool:
    key_tokens = sidecar_key_tokens(str(key))
    if key_tokens & {"non", "no", "not"}:
        return True
    if key_tokens & {"blocker", "blocked", "missing", "must", "required", "requires"}:
        return True
    if isinstance(value, str):
        value_tokens = sidecar_key_tokens(value)
        if value_tokens & SIDECAR_NEGATIVE_STATUS_TOKENS and not (
            value_tokens & SIDECAR_POSITIVE_STATUS_TOKENS
        ):
            return True
        if {"not", "authorized"}.issubset(value_tokens):
            return True
        if {"request", "only"}.issubset(value_tokens) and "authorized" in value_tokens:
            return True
    return False


def sidecar_positive_claim_key(key: str) -> bool:
    tokens = sidecar_key_tokens(key)
    normalized = "_".join(sorted(tokens))
    if not tokens:
        return False
    if "authoriz" in key.lower() or "authoris" in key.lower():
        return True
    if "ready" in tokens or "readiness" in tokens or "accepted" in tokens:
        return True
    if "sent" in tokens and tokens & {"discord", "notice", "report", "request", "this"}:
        return True
    if {"current", "turn"}.issubset(tokens) and not (tokens & {"required", "requires"}) and (
        tokens & {"accepted", "approval", "approved", "authorized", "ready", "recorded", "sent"}
        or "authoriz" in normalized
        or "authoris" in normalized
    ):
        return True
    if "counts" in tokens and tokens & SIDECAR_CLAIM_DOMAIN_TOKENS:
        return True
    if "evidence" in tokens and tokens & (SIDECAR_CLAIM_COMPLETION_TOKENS | {"approved", "runtime", "sdk"}):
        return True
    if tokens & SIDECAR_SUPPORT_PACKAGE_ALIAS_TOKENS and not (tokens & {"not", "only", "path"}):
        if tokens & (SIDECAR_CLAIM_COMPLETION_TOKENS | SIDECAR_CLAIM_DOMAIN_TOKENS):
            return True
        if tokens <= SIDECAR_SUPPORT_PACKAGE_ALIAS_TOKENS:
            return True
    if tokens & SIDECAR_CLAIM_DOMAIN_TOKENS and tokens & SIDECAR_CLAIM_COMPLETION_TOKENS:
        return True
    return False


def sidecar_positive_status_value(value: str) -> bool:
    tokens = sidecar_key_tokens(value)
    if not tokens:
        return False
    if tokens & SIDECAR_NEGATIVE_STATUS_TOKENS and not (tokens & SIDECAR_POSITIVE_STATUS_TOKENS):
        return False
    if {"not", "authorized"}.issubset(tokens):
        return False
    if {"request", "only"}.issubset(tokens) and "authorized" in tokens:
        return False
    if tokens & SIDECAR_POSITIVE_STATUS_TOKENS:
        return True
    if tokens & {"complete", "completed"} and tokens & SIDECAR_CLAIM_DOMAIN_TOKENS:
        return True
    if {"current", "turn"}.issubset(tokens) and tokens & {"approval", "authorized", "accepted", "ready"}:
        return True
    return False


def sidecar_positive_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return sidecar_positive_status_value(value)
    if isinstance(value, dict):
        return any(sidecar_positive_claim_value(child) for child in value.values())
    if isinstance(value, list):
        return any(sidecar_positive_claim_value(child) for child in value)
    return False


def sidecar_path_context_positive_claim(key: object, value: Any, parent_trail: str) -> bool:
    if not sidecar_positive_claim_value(value):
        return False
    key_tokens = sidecar_key_tokens(str(key))
    if key_tokens & SIDECAR_PATH_CONTEXT_NON_EVIDENCE_TOKENS:
        return False
    parent_tokens = sidecar_key_tokens(parent_trail)
    if not parent_tokens & SIDECAR_PATH_CONTEXT_DOMAIN_TOKENS:
        return False
    if key_tokens & SIDECAR_PATH_CONTEXT_POSITIVE_LEAF_TOKENS:
        return True
    return (
        normalized_sidecar_key(key) in NORMALIZED_SIDECAR_GENERIC_STATUS_KEYS
        or "status" in key_tokens
    )


def sidecar_claim_path_allowed(path: str, allowed_positive_paths: frozenset[str]) -> bool:
    if path in allowed_positive_paths:
        return True
    return path.endswith(".receipt_completed") or path.endswith(".operator_current_turn_approval_recorded")


def collect_forbidden_sidecar_claims(
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
            if normalized_sidecar_key(key) in SIDECAR_SPLIT_CLAIM_NAME_KEYS
            and isinstance(child, str)
        ]
        declared_claim_values = [
            child
            for key, child in value.items()
            if normalized_sidecar_key(key) in SIDECAR_SPLIT_CLAIM_VALUE_KEYS
        ]
        for claim_name in declared_claim_names:
            normalized_claim_name = normalized_sidecar_key(claim_name)
            if (
                normalized_claim_name in NORMALIZED_SIDECAR_FALSE_CLAIM_KEYS
                or sidecar_positive_claim_key(claim_name)
            ):
                if not declared_claim_values:
                    matches.append(trail)
                else:
                    for claim_value in declared_claim_values:
                        if sidecar_positive_claim_value(claim_value):
                            matches.append(trail)
                            break
            if normalized_claim_name in NORMALIZED_SIDECAR_NONZERO_PROGRESS_KEYS:
                if not declared_claim_values:
                    matches.append(trail)
                else:
                    for claim_value in declared_claim_values:
                        if sidecar_positive_claim_value(claim_value):
                            matches.append(trail)
                            break
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            normalized_key = normalized_sidecar_key(key)
            if sidecar_negative_claim_context(key, child):
                if isinstance(child, (dict, list)):
                    matches.extend(
                        collect_forbidden_sidecar_claims(
                            child,
                            allowed_positive_paths=allowed_positive_paths,
                            trail=child_trail,
                        )
                    )
                continue
            if normalized_key in NORMALIZED_SIDECAR_FALSE_CLAIM_KEYS and child is not False:
                if not sidecar_claim_path_allowed(child_trail, allowed_positive_paths):
                    matches.append(child_trail)
            if normalized_key in NORMALIZED_SIDECAR_NONZERO_PROGRESS_KEYS:
                if not isinstance(child, (int, float)) or child != 0:
                    matches.append(child_trail)
            if (
                isinstance(child, bool)
                and child is True
                and not sidecar_claim_path_allowed(child_trail, allowed_positive_paths)
                and sidecar_positive_claim_key(str(key))
            ):
                matches.append(child_trail)
            if (
                isinstance(child, str)
                and not sidecar_claim_path_allowed(child_trail, allowed_positive_paths)
                and sidecar_positive_claim_key(str(key))
                and sidecar_positive_claim_value(child)
            ):
                matches.append(child_trail)
            if (
                isinstance(child, str)
                and normalized_key in NORMALIZED_SIDECAR_GENERIC_STATUS_KEYS
                and not sidecar_claim_path_allowed(child_trail, allowed_positive_paths)
                and sidecar_positive_status_value(child)
            ):
                matches.append(child_trail)
            if (
                sidecar_path_context_positive_claim(key, child, trail)
                and not sidecar_claim_path_allowed(child_trail, allowed_positive_paths)
            ):
                matches.append(child_trail)
            matches.extend(
                collect_forbidden_sidecar_claims(
                    child,
                    allowed_positive_paths=allowed_positive_paths,
                    trail=child_trail,
                )
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            matches.extend(
                collect_forbidden_sidecar_claims(
                    child,
                    allowed_positive_paths=allowed_positive_paths,
                    trail=f"{trail}[{index}]",
                )
            )
    return list(dict.fromkeys(matches))


def validate_no_sidecar_overclaims(
    payload: dict[str, Any],
    relative_path: str,
    blockers: list[dict[str, Any]],
    *,
    allowed_positive_paths: frozenset[str] = frozenset(),
) -> None:
    for schema_path in collect_nested_approved_runtime_manifest_schema_paths(payload):
        sidecar_blocker(
            blockers,
            "sidecar_nested_approved_runtime_manifest_schema",
            relative_path,
            claim_path=schema_path,
            schema=APPROVED_RUNTIME_EVIDENCE_SCHEMA,
        )
    for claim_path in collect_forbidden_sidecar_claims(
        payload,
        allowed_positive_paths=allowed_positive_paths,
    ):
        sidecar_blocker(
            blockers,
            "sidecar_forbidden_authorization_or_readiness_claim",
            relative_path,
            claim_path=claim_path,
        )


def collect_nested_approved_runtime_manifest_schema_paths(value: Any, trail: str = "$") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        if trail != "$" and value.get("schema") == APPROVED_RUNTIME_EVIDENCE_SCHEMA:
            paths.append(f"{trail}.schema")
        for key, child in value.items():
            paths.extend(
                collect_nested_approved_runtime_manifest_schema_paths(child, f"{trail}.{key}")
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(
                collect_nested_approved_runtime_manifest_schema_paths(child, f"{trail}[{index}]")
            )
    return paths


def validate_non_evidence_schema(payload: dict[str, Any], relative_path: str, blockers: list[dict[str, Any]]) -> None:
    schema = payload.get("schema")
    if isinstance(schema, str) and schema in SIDECAR_NON_EVIDENCE_SCHEMAS:
        sidecar_blocker(
            blockers,
            "sidecar_schema_is_non_evidence_or_status_snapshot",
            relative_path,
            schema=schema,
        )
    if isinstance(schema, str) and PREACTIVATION_EXECUTOR_SCHEMA_RE.search(schema):
        sidecar_blocker(
            blockers,
            PREACTIVATION_EXECUTOR_SCHEMA_REASON,
            relative_path,
            schema=schema,
        )


def validate_approved_bundle_schema_alias(
    payload: dict[str, Any],
    relative_path: str,
    blockers: list[dict[str, Any]],
) -> None:
    schema = payload.get("schema")
    if not isinstance(schema, str) or schema == APPROVED_RUNTIME_EVIDENCE_SCHEMA:
        return
    for pattern, reason in APPROVED_BUNDLE_NON_EVIDENCE_SCHEMA_ALIAS_BLOCKERS:
        if pattern.search(schema):
            sidecar_blocker(blockers, reason, relative_path, schema=schema)


def resolve_declared_artifact_path(value: Any, *, base_dir: Path) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    declared = Path(value).expanduser()
    if not declared.is_absolute():
        declared = base_dir / declared
    return declared.resolve()


def validate_declared_path_binding(
    *,
    blockers: list[dict[str, Any]],
    relative_path: str,
    field: str,
    declared_value: Any,
    expected_path: Path,
    base_dir: Path,
    reason: str,
) -> None:
    declared = resolve_declared_artifact_path(declared_value, base_dir=base_dir)
    if declared is None:
        return
    expected = expected_path.resolve()
    if declared != expected:
        sidecar_blocker(
            blockers,
            reason,
            relative_path,
            field=field,
            expected=str(expected),
            actual=str(declared),
        )


def validate_declared_sha256_binding(
    *,
    blockers: list[dict[str, Any]],
    relative_path: str,
    field: str,
    declared_value: Any,
    expected_path: Path,
    reason: str,
) -> None:
    if declared_value is None:
        return
    if not isinstance(declared_value, str) or re.fullmatch(r"[0-9a-f]{64}", declared_value) is None:
        sidecar_blocker(blockers, f"{reason}_invalid", relative_path, field=field)
        return
    if expected_path.is_file() and declared_value != sha256_file(expected_path):
        sidecar_blocker(
            blockers,
            reason,
            relative_path,
            field=field,
            expected=sha256_file(expected_path),
            actual=declared_value,
        )


def validate_required_declared_artifact_binding(
    *,
    blockers: list[dict[str, Any]],
    relative_path: str,
    field: str,
    artifact: Any,
    expected_path: Path,
    base_dir: Path,
    reason_prefix: str,
) -> None:
    if not isinstance(artifact, dict):
        sidecar_blocker(blockers, f"{reason_prefix}_missing", relative_path, field=field)
        return
    path_value = artifact.get("path")
    if not isinstance(path_value, str) or not path_value:
        sidecar_blocker(blockers, f"{reason_prefix}_path_missing", relative_path, field=f"{field}.path")
    else:
        validate_declared_path_binding(
            blockers=blockers,
            relative_path=relative_path,
            field=f"{field}.path",
            declared_value=path_value,
            expected_path=expected_path,
            base_dir=base_dir,
            reason=f"{reason_prefix}_path_mismatch",
        )
    sha_value = artifact.get("sha256")
    if not isinstance(sha_value, str) or not sha_value:
        sidecar_blocker(blockers, f"{reason_prefix}_sha256_missing", relative_path, field=f"{field}.sha256")
    elif re.fullmatch(r"[0-9a-f]{64}", sha_value) is None or sha_value == "0" * 64:
        sidecar_blocker(
            blockers,
            f"{reason_prefix}_sha256_invalid",
            relative_path,
            field=f"{field}.sha256",
            actual=sha_value,
        )
    else:
        validate_declared_sha256_binding(
            blockers=blockers,
            relative_path=relative_path,
            field=f"{field}.sha256",
            declared_value=sha_value,
            expected_path=expected_path,
            reason=f"{reason_prefix}_sha256_mismatch",
        )


def validate_window_request_sidecar(
    path: Path,
    relative_path: str,
    evidence_dir: Path,
    run_id: str,
    args: argparse.Namespace,
    blockers: list[dict[str, Any]],
) -> None:
    payload = load_json_sidecar(path, relative_path, blockers)
    if payload is None:
        return
    validate_non_evidence_schema(payload, relative_path, blockers)
    validate_no_sidecar_overclaims(payload, relative_path, blockers)
    if payload.get("schema") != WINDOW_REQUEST_SCHEMA:
        sidecar_blocker(blockers, "window_request_schema_mismatch", relative_path, expected=WINDOW_REQUEST_SCHEMA)
    if payload.get("status") != "candidate_only_request_pack":
        sidecar_blocker(blockers, "window_request_status_not_candidate_only", relative_path, actual=payload.get("status"))
    if payload.get("run_id") != run_id:
        sidecar_blocker(blockers, "window_request_run_id_mismatch", relative_path, expected=run_id, actual=payload.get("run_id"))
    target = payload.get("target")
    if not isinstance(target, dict):
        sidecar_blocker(blockers, "window_request_target_missing", relative_path)
    else:
        if args.instance and target.get("instance") != args.instance:
            sidecar_blocker(
                blockers,
                "window_request_instance_mismatch",
                relative_path,
                expected=args.instance,
                actual=target.get("instance"),
            )
        if args.map_name and target.get("map") != args.map_name:
            sidecar_blocker(
                blockers,
                "window_request_map_mismatch",
                relative_path,
                expected=args.map_name,
                actual=target.get("map"),
            )
    path_fields = {
        "copied_evidence_dir": evidence_dir,
        "copied_log_path": evidence_dir / "Obelisk.log",
        "window_manifest_path": evidence_dir / "window-manifest.env",
    }
    for field, expected in path_fields.items():
        validate_declared_path_binding(
            blockers=blockers,
            relative_path=relative_path,
            field=field,
            declared_value=payload.get(field),
            expected_path=expected,
            base_dir=path.parent,
            reason=f"window_request_{field}_mismatch",
        )
    flags = payload.get("authorization_flags")
    if not isinstance(flags, dict):
        sidecar_blocker(blockers, "window_request_authorization_flags_missing", relative_path)
    else:
        for key, value in sorted(flags.items()):
            if value is not False:
                sidecar_blocker(blockers, f"window_request_authorization_flag_{key}_not_false", relative_path)
    window = payload.get("approved_window")
    if not isinstance(window, dict):
        sidecar_blocker(blockers, "window_request_approved_window_missing", relative_path)
    else:
        for key in ("start_utc", "end_utc"):
            value = window.get(key)
            if not isinstance(value, str) or UTC_RE.fullmatch(value) is None:
                sidecar_blocker(
                    blockers,
                    f"window_request_approved_window_{key}_invalid",
                    relative_path,
                    actual=value,
                )


def approved_window_from_request(evidence_dir: Path) -> dict[str, Any]:
    path = evidence_dir / "window-request.json"
    result: dict[str, Any] = {
        "source": "window-request.json",
        "path": str(path),
        "present": path.is_file(),
        "valid": False,
        "start_utc": None,
        "end_utc": None,
        "blockers": [],
    }
    if not path.is_file():
        result["blockers"].append("window_request_missing")
        return result
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result["blockers"].append("window_request_unreadable_or_invalid_json")
        result["error"] = str(exc)
        return result
    window = payload.get("approved_window") if isinstance(payload, dict) else None
    if not isinstance(window, dict):
        result["blockers"].append("approved_window_missing")
        return result
    start_utc = window.get("start_utc")
    end_utc = window.get("end_utc")
    if not isinstance(start_utc, str) or UTC_RE.fullmatch(start_utc) is None:
        result["blockers"].append("approved_window_start_utc_invalid")
    if not isinstance(end_utc, str) or UTC_RE.fullmatch(end_utc) is None:
        result["blockers"].append("approved_window_end_utc_invalid")
    if result["blockers"]:
        return result
    result.update(
        {
            "valid": True,
            "start_utc": start_utc,
            "end_utc": end_utc,
        }
    )
    return result


def validate_observer_env_sidecar(
    path: Path,
    relative_path: str,
    args: argparse.Namespace,
    blockers: list[dict[str, Any]],
) -> None:
    fields = parse_env_sidecar(path, relative_path, blockers)
    expected = {
        "OBELISK_ENABLE_PROCESS_EVENT_HOOK": "1",
        "OBELISK_DISABLE_PLUGINS": "1",
        "OBELISK_WRAPPER_PROFILE": "observer-debug",
        "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER": "1",
        "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256": args.expected_binary_sha256,
        "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT": "10",
        "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT": "0",
        "OBELISK_PE_TRACE_LIMIT": "0",
    }
    if args.instance:
        expected["OBELISK_INSTANCE_ID"] = args.instance
    for key, expected_value in expected.items():
        if fields.get(key) != expected_value:
            sidecar_blocker(
                blockers,
                f"observer_env_{key.lower()}_mismatch",
                relative_path,
                expected=expected_value,
                actual=fields.get(key),
            )
    for key in (
        "OBELISK_ENABLE_REFLECTION_SCANNER",
        "OBELISK_ENABLE_NATIVE_EXEC_PROBES",
        "OBELISK_ENABLE_DEBUG_CONTROL",
        "OBELISK_DEBUG_ALLOW_PTRACE",
    ):
        if fields.get(key) not in (None, "", "0"):
            sidecar_blocker(blockers, f"observer_env_forbidden_{key.lower()}_present", relative_path)


def validate_operator_request_sidecar(path: Path, relative_path: str, blockers: list[dict[str, Any]]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        sidecar_blocker(blockers, "operator_approval_request_unreadable", relative_path, detail=str(exc))
        return
    if not text.strip():
        sidecar_blocker(blockers, "operator_approval_request_empty", relative_path)
    if "does not authorize" not in text.lower():
        sidecar_blocker(blockers, "operator_approval_request_non_authorization_text_missing", relative_path)


def expected_bound_artifact(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return {
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def validate_bound_artifact(
    *,
    blockers: list[dict[str, Any]],
    relative_path: str,
    artifact_key: str,
    artifact: Any,
    expected_path: Path,
) -> None:
    expected = expected_bound_artifact(expected_path)
    if expected is None:
        return
    if artifact != expected:
        sidecar_blocker(
            blockers,
            f"operator_approval_receipt_{artifact_key}_artifact_mismatch",
            relative_path,
            expected=expected,
            actual=artifact,
        )


def generated_operator_receipt_marker(payload: dict[str, Any]) -> str | None:
    for key in sorted(GENERATED_RECEIPT_MARKER_KEYS):
        if key not in payload:
            continue
        value = payload.get(key)
        if value is True:
            return key
        if isinstance(value, str) and GENERATED_RECEIPT_MARKER_RE.search(value):
            return key
    return None


def validate_operator_receipt_sidecar(
    path: Path,
    relative_path: str,
    run_id: str,
    evidence_dir: Path,
    args: argparse.Namespace,
    blockers: list[dict[str, Any]],
) -> None:
    payload = load_json_sidecar(path, relative_path, blockers)
    if payload is None:
        return
    validate_non_evidence_schema(payload, relative_path, blockers)
    validate_no_sidecar_overclaims(
        payload,
        relative_path,
        blockers,
        allowed_positive_paths=frozenset(
            {"$.status", "$.receipt_completed", "$.operator_current_turn_approval_recorded"}
        ),
    )
    generated_marker = generated_operator_receipt_marker(payload)
    if path.name.endswith(".template.json") or payload.get("status") == "generated_template" or generated_marker:
        sidecar_blocker(
            blockers,
            "operator_approval_receipt_template_not_completed",
            relative_path,
            marker=generated_marker,
        )
    if payload.get("schema") != OPERATOR_APPROVAL_RECEIPT_SCHEMA:
        sidecar_blocker(blockers, "operator_approval_receipt_schema_mismatch", relative_path)
    if payload.get("status") != "completed_operator_receipt":
        sidecar_blocker(blockers, "operator_approval_receipt_status_not_completed", relative_path, actual=payload.get("status"))
    completion = payload.get("operator_completion")
    standing_launch_authority_recorded = (
        payload.get("standing_launch_authority_recorded") is True
        and payload.get("standing_launch_authority_satisfies_operator_approval") is True
        and isinstance(completion, dict)
        and completion.get("approval_source") == APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY
        and completion.get("attestation") == APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY
    )
    if payload.get("receipt_completed") is not True:
        sidecar_blocker(blockers, "operator_approval_receipt_completed_not_true", relative_path)
    if payload.get("operator_current_turn_approval_recorded") is not True and not standing_launch_authority_recorded:
        sidecar_blocker(blockers, "operator_approval_receipt_current_turn_not_recorded", relative_path)
    if not isinstance(completion, dict):
        sidecar_blocker(blockers, "operator_approval_receipt_completion_missing", relative_path)
    else:
        if not isinstance(completion.get("approval_recorded_at_utc"), str) or UTC_RE.fullmatch(
            completion.get("approval_recorded_at_utc", "")
        ) is None:
            sidecar_blocker(blockers, "operator_approval_receipt_approved_at_invalid", relative_path)
        approval_source = completion.get("approval_source")
        if approval_source not in (APPROVAL_SOURCE_CURRENT_TURN, APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY):
            sidecar_blocker(blockers, "operator_approval_receipt_approval_source_mismatch", relative_path)
        expected_attestation = (
            APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY
            if approval_source == APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY
            else APPROVAL_ATTESTATION_CURRENT_TURN
        )
        if completion.get("attestation") != expected_attestation:
            sidecar_blocker(blockers, "operator_approval_receipt_attestation_mismatch", relative_path)
    bound = payload.get("bound_request_pack")
    if not isinstance(bound, dict):
        sidecar_blocker(blockers, "operator_approval_receipt_run_id_mismatch", relative_path)
        bound = {}
    elif bound.get("run_id") != run_id:
        sidecar_blocker(blockers, "operator_approval_receipt_run_id_mismatch", relative_path)
    target = bound.get("target")
    if args.instance and (not isinstance(target, dict) or target.get("instance") != args.instance):
        sidecar_blocker(blockers, "operator_approval_receipt_instance_mismatch", relative_path)
    if args.map_name and (not isinstance(target, dict) or target.get("map") != args.map_name):
        sidecar_blocker(blockers, "operator_approval_receipt_map_mismatch", relative_path)
    for field, expected in {
        "copied_evidence_dir": evidence_dir,
        "copied_log_path": evidence_dir / "Obelisk.log",
        "window_manifest_path": evidence_dir / "window-manifest.env",
    }.items():
        validate_declared_path_binding(
            blockers=blockers,
            relative_path=relative_path,
            field=f"bound_request_pack.{field}",
            declared_value=bound.get(field),
            expected_path=expected,
            base_dir=path.parent,
            reason=f"operator_approval_receipt_{field}_mismatch",
        )
    bound_artifacts = payload.get("bound_artifacts")
    if not isinstance(bound_artifacts, dict):
        sidecar_blocker(blockers, "operator_approval_receipt_bound_artifacts_missing", relative_path)
    else:
        for key, expected_path in {
            "window_request_json": evidence_dir / "window-request.json",
            "observer_window_env": evidence_dir / "observer-window.env",
            "operator_approval_request_md": evidence_dir / "operator-approval-request.md",
        }.items():
            validate_bound_artifact(
                blockers=blockers,
                relative_path=relative_path,
                artifact_key=key,
                artifact=bound_artifacts.get(key),
                expected_path=expected_path,
            )
    flags = payload.get("non_authorization_flags")
    if not isinstance(flags, dict):
        sidecar_blocker(blockers, "operator_approval_receipt_non_authorization_flags_missing", relative_path)
    else:
        for key, value in sorted(flags.items()):
            if value is not False:
                sidecar_blocker(blockers, f"operator_approval_receipt_{key}_not_false", relative_path)


def validate_preflight_sidecar(
    path: Path,
    relative_path: str,
    run_id: str,
    args: argparse.Namespace,
    blockers: list[dict[str, Any]],
) -> None:
    payload = load_json_sidecar(path, relative_path, blockers)
    if payload is None:
        return
    validate_non_evidence_schema(payload, relative_path, blockers)
    validate_no_sidecar_overclaims(
        payload,
        relative_path,
        blockers,
        allowed_positive_paths=frozenset(
            {
                "$.ready",
                "$.preflight_passed",
                "$.current_turn_operator_approval_required",
                "$.deployment_intent.request_only",
            }
        ),
    )
    schema = payload.get("schema")
    if schema != PREFLIGHT_SCHEMA:
        sidecar_blocker(blockers, "preflight_schema_mismatch", relative_path)
        if isinstance(schema, str):
            if schema.startswith("obelisk.player-principal-lifecycle-preflight."):
                sidecar_blocker(blockers, "preflight_stale_schema_is_not_accepted", relative_path, schema=schema)
            for pattern, reason in APPROVED_BUNDLE_NON_EVIDENCE_SCHEMA_ALIAS_BLOCKERS:
                if pattern.search(schema):
                    sidecar_blocker(blockers, f"preflight_{reason}", relative_path, schema=schema)
                    break
    if payload.get("ready") is not True or payload.get("preflight_passed") is not True:
        sidecar_blocker(blockers, "preflight_not_passed", relative_path)
    for key in sorted(REQUIRED_PREFLIGHT_FALSE_FLAGS):
        if payload.get(key) is not False:
            sidecar_blocker(
                blockers,
                f"preflight_{key}_not_false",
                relative_path,
                expected=False,
                actual=payload.get(key),
            )
    expected_mode = "observer-window" if relative_path == "preflight-pre.json" else "stable"
    if payload.get("mode") != expected_mode:
        sidecar_blocker(blockers, "preflight_mode_mismatch", relative_path, expected=expected_mode, actual=payload.get("mode"))
    if payload.get("run_id") != run_id:
        sidecar_blocker(blockers, "preflight_run_id_mismatch", relative_path, expected=run_id, actual=payload.get("run_id"))
    target = payload.get("target")
    if args.instance and (not isinstance(target, dict) or target.get("instance") != args.instance):
        sidecar_blocker(blockers, "preflight_instance_mismatch", relative_path)
    if args.map_name and (not isinstance(target, dict) or target.get("map") != args.map_name):
        sidecar_blocker(blockers, "preflight_map_mismatch", relative_path)
    path_fields = {
        "copied_evidence_dir": path.parent,
        "copied_log_path": path.parent / "Obelisk.log",
        "window_manifest_path": path.parent / "window-manifest.env",
    }
    for field, expected in path_fields.items():
        validate_declared_path_binding(
            blockers=blockers,
            relative_path=relative_path,
            field=field,
            declared_value=payload.get(field),
            expected_path=expected,
            base_dir=path.parent,
            reason=f"preflight_{field}_mismatch",
        )
    server_binary = payload.get("server_binary")
    if isinstance(server_binary, dict) and server_binary.get("sha256") != args.expected_binary_sha256:
        sidecar_blocker(
            blockers,
            "preflight_server_binary_sha256_mismatch",
            relative_path,
            expected=args.expected_binary_sha256,
            actual=server_binary.get("sha256"),
        )


def validate_window_manifest_sidecar(
    path: Path,
    relative_path: str,
    evidence_dir: Path,
    run_id: str,
    blockers: list[dict[str, Any]],
) -> None:
    fields = parse_env_sidecar(path, relative_path, blockers)
    required = (
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
        "single_module_summary",
        "delivery_claim",
        "principal_claim",
        "log_budget",
        "plugins_disabled",
        "scanner_disabled",
        "dispatch_limit",
    )
    for key in required:
        if key not in fields:
            sidecar_blocker(blockers, f"window_manifest_{key}_missing", relative_path)
    if fields.get("run_id") != run_id:
        sidecar_blocker(blockers, "window_manifest_run_id_mismatch", relative_path, expected=run_id, actual=fields.get("run_id"))
    manifest_commit = fields.get("obelisk_commit")
    current_commit = current_obelisk_commit()
    if manifest_commit is None:
        sidecar_blocker(blockers, "window_manifest_obelisk_commit_missing", relative_path)
    elif GIT_COMMIT_RE.fullmatch(manifest_commit) is None:
        sidecar_blocker(
            blockers,
            "window_manifest_obelisk_commit_invalid",
            relative_path,
            actual=manifest_commit,
        )
    elif current_commit is None:
        sidecar_blocker(blockers, "current_obelisk_commit_unavailable", relative_path)
    elif manifest_commit != current_commit:
        sidecar_blocker(
            blockers,
            "window_manifest_obelisk_commit_not_current_head",
            relative_path,
            expected=current_commit,
            actual=manifest_commit,
        )
    approval = fields.get("approval", "")
    if (
        "current_turn" not in approval
        and approval not in (APPROVAL_TEXT, STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT)
    ):
        sidecar_blocker(blockers, "window_manifest_approval_not_exact_operator_authority", relative_path)
    expected_paths = {
        "copied_log_path": evidence_dir / "Obelisk.log",
        "request_pack_path": evidence_dir / "window-request.json",
        "observer_env_path": evidence_dir / "observer-window.env",
        "operator_approval_receipt_path": evidence_dir / "operator-approval-receipt.json",
        "preflight_pre_path": evidence_dir / "preflight-pre.json",
        "preflight_post_path": evidence_dir / "preflight-post.json",
    }
    for key, expected in expected_paths.items():
        if key not in fields:
            continue
        declared = Path(fields[key]).expanduser()
        if not declared.is_absolute():
            declared = path.parent / declared
        if declared.resolve() != expected.resolve():
            sidecar_blocker(blockers, f"window_manifest_{key}_mismatch", relative_path, expected=str(expected.resolve()), actual=str(declared.resolve()))
    sha_bindings = {
        "copied_log_sha256": evidence_dir / "Obelisk.log",
        "request_pack_sha256": evidence_dir / "window-request.json",
        "observer_env_sha256": evidence_dir / "observer-window.env",
        "operator_approval_receipt_sha256": evidence_dir / "operator-approval-receipt.json",
        "preflight_pre_sha256": evidence_dir / "preflight-pre.json",
        "preflight_post_sha256": evidence_dir / "preflight-post.json",
    }
    for key, source in sha_bindings.items():
        value = fields.get(key)
        if value is None:
            continue
        if re.fullmatch(r"[0-9a-f]{64}", value) is None or value == "0" * 64:
            sidecar_blocker(blockers, f"window_manifest_{key}_invalid", relative_path)
        elif source.is_file() and value != sha256_file(source):
            sidecar_blocker(blockers, f"window_manifest_{key}_mismatch", relative_path)
    expected_values = {
        "single_module_summary": "player_principal_lifecycle",
        "delivery_claim": "none",
        "principal_claim": "none",
        "log_budget": "10",
        "plugins_disabled": "true",
        "scanner_disabled": "true",
        "dispatch_limit": "0",
    }
    for key, expected in expected_values.items():
        if fields.get(key) != expected:
            sidecar_blocker(blockers, f"window_manifest_{key}_mismatch", relative_path, expected=expected, actual=fields.get(key))


def validate_approved_runtime_manifest_operational_window(
    *,
    operational_window: Any,
    relative_path: str,
    path: Path,
    run_id: str,
    evidence_dir: Path,
    args: argparse.Namespace,
    blockers: list[dict[str, Any]],
) -> None:
    if not isinstance(operational_window, dict):
        sidecar_blocker(blockers, "approved_runtime_manifest_operational_window_missing", relative_path)
        return
    if operational_window.get("schema") != WINDOW_MANIFEST_CHECK_SCHEMA:
        sidecar_blocker(
            blockers,
            "approved_runtime_manifest_operational_window_schema_mismatch",
            relative_path,
            expected=WINDOW_MANIFEST_CHECK_SCHEMA,
            actual=operational_window.get("schema"),
        )
    if operational_window.get("ready") is not True:
        sidecar_blocker(blockers, "approved_runtime_manifest_operational_window_not_ready", relative_path)
    if operational_window.get("operational_window_manifest_ready") is not True:
        sidecar_blocker(
            blockers,
            "approved_runtime_manifest_operational_window_manifest_not_ready",
            relative_path,
        )
    if operational_window.get("run_id") != run_id:
        sidecar_blocker(
            blockers,
            "approved_runtime_manifest_run_id_mismatch",
            relative_path,
            expected=run_id,
            actual=operational_window.get("run_id"),
        )
    manifest_commit = operational_window.get("obelisk_commit")
    current_commit = current_obelisk_commit()
    if manifest_commit is None:
        sidecar_blocker(blockers, "approved_runtime_manifest_obelisk_commit_missing", relative_path)
    elif not isinstance(manifest_commit, str) or GIT_COMMIT_RE.fullmatch(manifest_commit) is None:
        sidecar_blocker(
            blockers,
            "approved_runtime_manifest_obelisk_commit_invalid",
            relative_path,
            actual=manifest_commit,
        )
    elif current_commit is None:
        sidecar_blocker(blockers, "current_obelisk_commit_unavailable", relative_path)
    elif manifest_commit != current_commit:
        sidecar_blocker(
            blockers,
            "approved_runtime_manifest_obelisk_commit_not_current_head",
            relative_path,
            expected=current_commit,
            actual=manifest_commit,
        )
    for field, nested_keys, expected_relative_path, reason_prefix in APPROVED_RUNTIME_MANIFEST_REQUIRED_OPERATIONAL_ARTIFACTS:
        artifact = nested_mapping(operational_window, *nested_keys)
        validate_required_declared_artifact_binding(
            blockers=blockers,
            relative_path=relative_path,
            field=f"operational_window.{field}",
            artifact=artifact,
            expected_path=evidence_dir / expected_relative_path,
            base_dir=path.parent,
            reason_prefix=reason_prefix,
        )
    target = operational_window.get("target")
    if not isinstance(target, dict):
        sidecar_blocker(blockers, "approved_runtime_manifest_target_missing", relative_path)
    else:
        if args.instance and target.get("instance") != args.instance:
            sidecar_blocker(
                blockers,
                "approved_runtime_manifest_instance_mismatch",
                relative_path,
                expected=args.instance,
                actual=target.get("instance"),
            )
        if args.map_name and target.get("map") != args.map_name:
            sidecar_blocker(
                blockers,
                "approved_runtime_manifest_map_mismatch",
                relative_path,
                expected=args.map_name,
                actual=target.get("map"),
            )


def source_summary_diagnostic_fields(module: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostic_fields: list[dict[str, Any]] = []
    for key, value in sorted(module.items()):
        if not key.startswith("diagnostic_"):
            continue
        if isinstance(value, bool) and value is True:
            diagnostic_fields.append({"field": key, "actual": value})
        elif isinstance(value, int) and value > 0:
            diagnostic_fields.append({"field": key, "actual": value})
        elif isinstance(value, (list, dict)) and value:
            if any(token in key for token in ("candidate", "line", "route", "drift")):
                diagnostic_fields.append({"field": key, "actual": "non_empty"})
    return diagnostic_fields


def validate_approved_runtime_manifest_source_summary(
    *,
    source_summary: Any,
    relative_path: str,
    path: Path,
    evidence_dir: Path,
    blockers: list[dict[str, Any]],
) -> None:
    if not isinstance(source_summary, dict):
        sidecar_blocker(blockers, "approved_runtime_manifest_source_summary_missing", relative_path)
        return
    if source_summary.get("schema") != RUNTIME_OBSERVER_SUMMARY_SCHEMA:
        sidecar_blocker(
            blockers,
            "approved_runtime_manifest_source_summary_schema_mismatch",
            relative_path,
            expected=RUNTIME_OBSERVER_SUMMARY_SCHEMA,
            actual=source_summary.get("schema"),
        )
    evidence = source_summary.get("evidence")
    if not isinstance(evidence, dict):
        sidecar_blocker(blockers, "approved_runtime_manifest_source_summary_evidence_missing", relative_path)
    else:
        if evidence.get("kind") != "runtime-observer-log":
            sidecar_blocker(
                blockers,
                "approved_runtime_manifest_source_summary_evidence_kind_mismatch",
                relative_path,
                expected="runtime-observer-log",
                actual=evidence.get("kind"),
            )
        if evidence.get("server_paths_allowed") is not False:
            sidecar_blocker(
                blockers,
                "approved_runtime_manifest_source_summary_server_paths_allowed_not_false",
                relative_path,
                actual=evidence.get("server_paths_allowed"),
            )
        sources = evidence.get("sources")
        if not isinstance(sources, list) or len(sources) != 1:
            sidecar_blocker(blockers, "approved_runtime_manifest_source_summary_sources_not_exactly_one", relative_path)
        else:
            validate_required_declared_artifact_binding(
                blockers=blockers,
                relative_path=relative_path,
                field="source_summary.evidence.sources[0]",
                artifact=sources[0],
                expected_path=evidence_dir / "Obelisk.log",
                base_dir=path.parent,
                reason_prefix="approved_runtime_manifest_source_summary_copied_log",
            )
        summary_commit = evidence.get("obelisk_commit")
        current_commit = current_obelisk_commit()
        if summary_commit is not None:
            if not isinstance(summary_commit, str) or GIT_COMMIT_RE.fullmatch(summary_commit) is None:
                sidecar_blocker(
                    blockers,
                    "approved_runtime_manifest_source_summary_obelisk_commit_invalid",
                    relative_path,
                    actual=summary_commit,
                )
            elif current_commit is None:
                sidecar_blocker(blockers, "current_obelisk_commit_unavailable", relative_path)
            elif summary_commit != current_commit:
                sidecar_blocker(
                    blockers,
                    "approved_runtime_manifest_source_summary_obelisk_commit_not_current_head",
                    relative_path,
                    expected=current_commit,
                    actual=summary_commit,
                )
    modules = source_summary.get("modules")
    if not isinstance(modules, dict):
        sidecar_blocker(blockers, "approved_runtime_manifest_source_summary_modules_missing", relative_path)
        return
    unexpected_modules = sorted(key for key in modules if key != APPROVED_RUNTIME_SOURCE_MODULE)
    if unexpected_modules:
        sidecar_blocker(
            blockers,
            "approved_runtime_manifest_source_summary_unexpected_modules_present",
            relative_path,
            actual=unexpected_modules,
        )
    module = modules.get(APPROVED_RUNTIME_SOURCE_MODULE)
    if not isinstance(module, dict):
        sidecar_blocker(blockers, "approved_runtime_manifest_source_summary_lifecycle_module_missing", relative_path)
        return
    diagnostic_fields = source_summary_diagnostic_fields(module)
    if diagnostic_fields:
        sidecar_blocker(
            blockers,
            "approved_runtime_manifest_source_summary_diagnostic_material_present",
            relative_path,
            fields=diagnostic_fields,
        )


def validate_approved_bundle_sidecar(
    path: Path,
    relative_path: str,
    run_id: str,
    evidence_dir: Path,
    args: argparse.Namespace,
    blockers: list[dict[str, Any]],
) -> None:
    payload = load_json_sidecar(path, relative_path, blockers)
    if payload is None:
        return
    validate_non_evidence_schema(payload, relative_path, blockers)
    validate_approved_bundle_schema_alias(payload, relative_path, blockers)
    validate_no_sidecar_overclaims(
        payload,
        relative_path,
        blockers,
        allowed_positive_paths=frozenset(
            {
                "$.approved_runtime_evidence_present",
                "$.runtime_evidence_ready",
                "$.approval.runtime_evidence_reviewed",
                "$.operational_window.ready",
                "$.operational_window.operational_window_manifest_ready",
                "$.operational_window.operator_approval_receipt.verified",
                "$.operational_window.posture.plugins_disabled",
                "$.operational_window.posture.scanner_disabled",
                "$.operational_window.posture.native_exec_disabled",
                "$.operational_window.posture.ptrace_disabled",
                "$.operational_window.rollback.completed",
            }
        ),
    )
    if payload.get("schema") != APPROVED_RUNTIME_EVIDENCE_SCHEMA:
        sidecar_blocker(blockers, "approved_runtime_manifest_schema_mismatch", relative_path, expected=APPROVED_RUNTIME_EVIDENCE_SCHEMA)
    if payload.get("artifact_status") != APPROVED_RUNTIME_EVIDENCE_ARTIFACT_STATUS:
        sidecar_blocker(
            blockers,
            "approved_runtime_manifest_artifact_status_mismatch",
            relative_path,
            expected=APPROVED_RUNTIME_EVIDENCE_ARTIFACT_STATUS,
            actual=payload.get("artifact_status"),
        )
    if payload.get("readiness_classification") != APPROVED_RUNTIME_EVIDENCE_CLASSIFICATION:
        sidecar_blocker(
            blockers,
            "approved_runtime_manifest_readiness_classification_mismatch",
            relative_path,
            expected=APPROVED_RUNTIME_EVIDENCE_CLASSIFICATION,
            actual=payload.get("readiness_classification"),
        )
    if payload.get("approved_runtime_evidence_present") is not True:
        sidecar_blocker(blockers, "approved_runtime_manifest_evidence_present_not_true", relative_path)
    if payload.get("runtime_evidence_ready") is not True:
        sidecar_blocker(blockers, "approved_runtime_manifest_runtime_evidence_ready_not_true", relative_path)
    approval = payload.get("approval")
    if not isinstance(approval, dict):
        sidecar_blocker(blockers, "approved_runtime_manifest_approval_missing", relative_path)
    else:
        if approval.get("runtime_evidence_reviewed") is not True:
            sidecar_blocker(blockers, "approved_runtime_manifest_approval_runtime_evidence_reviewed_not_true", relative_path)
        for key in (
            "runtime_work_authorized_by_this_manifest",
            "server_operations_authorized_by_this_manifest",
            "publication_authorized_by_this_manifest",
            "discord_authorized_by_this_manifest",
        ):
            if approval.get(key) is not False:
                sidecar_blocker(blockers, f"approved_runtime_manifest_approval_{key}_not_false", relative_path)
    validate_approved_runtime_manifest_operational_window(
        operational_window=payload.get("operational_window"),
        relative_path=relative_path,
        path=path,
        run_id=run_id,
        evidence_dir=evidence_dir,
        args=args,
        blockers=blockers,
    )
    validate_approved_runtime_manifest_source_summary(
        source_summary=payload.get("source_summary"),
        relative_path=relative_path,
        path=path,
        evidence_dir=evidence_dir,
        blockers=blockers,
    )
    for key in (
        "promotion_ready",
        "public_header_allowed",
        "public_abi_ready",
        "public_sdk_ready",
        "v1_completion_ready",
        "runtime_ready",
        "stable_claim_allowed",
        "complete_sdk_ready",
    ):
        if payload.get(key) is not False:
            sidecar_blocker(blockers, f"approved_runtime_manifest_{key}_not_false", relative_path)


def validate_unexpected_receipt_template_or_beta_sidecar(
    payload: dict[str, Any],
    relative_path: str,
    blockers: list[dict[str, Any]],
) -> None:
    schema = payload.get("schema")
    generated_marker = generated_operator_receipt_marker(payload)
    if (
        relative_path == OPERATOR_APPROVAL_RECEIPT_TEMPLATE_RELATIVE_PATH
        or "operator-approval-receipt" in relative_path
        and (
            "template" in relative_path
            or payload.get("status") == "generated_template"
            or generated_marker is not None
        )
    ):
        sidecar_blocker(
            blockers,
            "operator_approval_receipt_template_not_evidence_input",
            relative_path,
            marker=generated_marker,
        )
    if (
        isinstance(schema, str)
        and STRAY_BETA_SIDECAR_SCHEMA_RE.search(schema) is not None
    ) or STRAY_BETA_SIDECAR_NAME_RE.search(relative_path) is not None:
        sidecar_blocker(
            blockers,
            "stray_beta_notice_sidecar_not_evidence_input",
            relative_path,
            schema=schema,
        )


def validate_unexpected_json_sidecar(
    path: Path,
    relative_path: str,
    blockers: list[dict[str, Any]],
) -> None:
    symlink = protected_paths.first_symlink_component(path)
    if symlink is not None:
        sidecar_blocker(
            blockers,
            "unexpected_json_sidecar_symlink_component",
            relative_path,
            path=str(symlink),
        )
        return
    payload = load_json_sidecar(path, relative_path, blockers)
    if payload is None:
        return
    sidecar_blocker(
        blockers,
        "unexpected_json_sidecar_not_bound_to_expected_sibling_set",
        relative_path,
        expected_relative_paths=sorted(EXPECTED_RELATIVE_PATHS),
    )
    validate_unexpected_receipt_template_or_beta_sidecar(payload, relative_path, blockers)
    validate_non_evidence_schema(payload, relative_path, blockers)
    validate_approved_bundle_schema_alias(payload, relative_path, blockers)
    if payload.get("schema") == APPROVED_RUNTIME_EVIDENCE_SCHEMA:
        sidecar_blocker(
            blockers,
            "approved_runtime_manifest_not_exact_approved_bundle_relative_path",
            relative_path,
            expected=APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
        )
    validate_no_sidecar_overclaims(payload, relative_path, blockers)


def validate_unexpected_approved_bundle_json_sidecar(
    path: Path,
    relative_path: str,
    blockers: list[dict[str, Any]],
) -> None:
    symlink = protected_paths.first_symlink_component(path)
    if symlink is not None:
        sidecar_blocker(
            blockers,
            "unexpected_approved_bundle_sidecar_symlink_component",
            relative_path,
            path=str(symlink),
        )
        return
    payload = load_json_sidecar(path, relative_path, blockers)
    if payload is None:
        return
    sidecar_blocker(
        blockers,
        "unexpected_approved_bundle_sidecar_not_exact_relative_path",
        relative_path,
        expected=APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
    )
    validate_unexpected_receipt_template_or_beta_sidecar(payload, relative_path, blockers)
    validate_non_evidence_schema(payload, relative_path, blockers)
    validate_approved_bundle_schema_alias(payload, relative_path, blockers)
    if payload.get("schema") == APPROVED_RUNTIME_EVIDENCE_SCHEMA:
        sidecar_blocker(
            blockers,
            "approved_runtime_manifest_not_exact_approved_bundle_relative_path",
            relative_path,
            expected=APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
        )
    validate_no_sidecar_overclaims(payload, relative_path, blockers)


def unexpected_json_sidecar_states(evidence_dir: Path) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    try:
        entries = list(evidence_dir.iterdir())
    except OSError:
        return states
    for entry in sorted(entries):
        if entry.name == "approved-bundle":
            continue
        if entry.name in EXPECTED_TOP_LEVEL_SIDECAR_FILENAMES:
            continue
        if entry.name in EXPECTED_AUXILIARY_TOP_LEVEL_JSON_SIDECARS:
            continue
        if entry.suffix.casefold() != ".json":
            continue
        if not entry.is_file() and not entry.is_symlink():
            continue
        states.append(
            {
                "label": "unexpected_json_sidecar",
                "relative_path": entry.name,
                "path": str(entry),
                "present": True,
                "unexpected": True,
                "approved_bundle_sidecar": False,
            }
        )

    approved_bundle_dir = evidence_dir / "approved-bundle"
    try:
        bundle_entries = list(approved_bundle_dir.iterdir())
    except FileNotFoundError:
        return states
    except OSError:
        return states
    for entry in sorted(bundle_entries):
        if (
            entry.name == "approved-runtime-principal-lifecycle-evidence.json"
            or entry.name in EXPECTED_APPROVED_BUNDLE_GENERATED_JSON_OUTPUTS
        ):
            continue
        if entry.suffix.casefold() != ".json":
            continue
        if not entry.is_file() and not entry.is_symlink():
            continue
        relative_path = f"approved-bundle/{entry.name}"
        states.append(
            {
                "label": "unexpected_approved_bundle_json_sidecar",
                "relative_path": relative_path,
                "path": str(entry),
                "present": True,
                "unexpected": True,
                "approved_bundle_sidecar": True,
            }
        )
    return states


def validate_sidecar_contents(
    evidence_dir: Path,
    sibling_states: list[dict[str, Any]],
    *,
    inspect: bool,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    states: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    invalid: list[str] = []
    if not inspect:
        return states, blockers, invalid
    for state in [*sibling_states, *unexpected_json_sidecar_states(evidence_dir)]:
        relative_path = state["relative_path"]
        if relative_path == "Obelisk.log":
            continue
        entry: dict[str, Any] = {
            "label": state["label"],
            "relative_path": relative_path,
            "path": state["path"],
            "present": state["present"],
            "valid": False,
            "blockers": [],
        }
        states.append(entry)
        if not state["present"]:
            entry["inspection_blocked_by"] = "sidecar_missing_or_symlink"
            continue
        path = Path(state["path"])
        before = len(blockers)
        if relative_path == "window-request.json":
            validate_window_request_sidecar(path, relative_path, evidence_dir, evidence_dir.name, args, blockers)
        elif relative_path == "observer-window.env":
            validate_observer_env_sidecar(path, relative_path, args, blockers)
        elif relative_path == "operator-approval-request.md":
            validate_operator_request_sidecar(path, relative_path, blockers)
        elif relative_path == "operator-approval-receipt.json":
            validate_operator_receipt_sidecar(path, relative_path, evidence_dir.name, evidence_dir, args, blockers)
        elif relative_path in {"preflight-pre.json", "preflight-post.json"}:
            validate_preflight_sidecar(path, relative_path, evidence_dir.name, args, blockers)
        elif relative_path == "window-manifest.env":
            validate_window_manifest_sidecar(path, relative_path, evidence_dir, evidence_dir.name, blockers)
        elif relative_path == "approved-bundle/approved-runtime-principal-lifecycle-evidence.json":
            validate_approved_bundle_sidecar(path, relative_path, evidence_dir.name, evidence_dir, args, blockers)
        elif state.get("approved_bundle_sidecar") is True:
            validate_unexpected_approved_bundle_json_sidecar(path, relative_path, blockers)
        elif state.get("unexpected") is True:
            validate_unexpected_json_sidecar(path, relative_path, blockers)
        entry_blockers = blockers[before:]
        entry["blockers"] = entry_blockers
        entry["valid"] = not entry_blockers
        if entry_blockers:
            invalid.append(relative_path)
    return states, blockers, invalid


def closure_artifact_status(state: dict[str, Any], validation: dict[str, Any] | None) -> str:
    if state.get("symlink_component") is not None:
        return "blocked_symlink_component"
    if state.get("present") is not True:
        return "missing"
    if validation is not None and validation.get("valid") is not True:
        return "present_but_invalid"
    return "present"


def closure_artifact_required_for(relative_path: str) -> str:
    if relative_path == "Obelisk.log":
        return "copied_log_lifecycle_role_triplet_and_bundle_input"
    if relative_path == APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH:
        return "approved_runtime_principal_lifecycle_evidence_bundle_output"
    return "approved_bundle_builder_sidecar_input"


def closure_artifact_checklist(
    evidence_dir: Path,
    sibling_states: list[dict[str, Any]],
    sidecar_validation_states: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    validation_by_relative_path = {
        state["relative_path"]: state for state in sidecar_validation_states
    }
    checklist: list[dict[str, Any]] = []
    for state in sibling_states:
        relative_path = state["relative_path"]
        validation = validation_by_relative_path.get(relative_path)
        status = closure_artifact_status(state, validation)
        blockers = [] if validation is None else list(validation.get("blockers", []))
        if status == "missing":
            blockers = [{"reason": "required_artifact_missing", "relative_path": relative_path}]
        elif status == "blocked_symlink_component":
            blockers = [
                {
                    "reason": "required_artifact_symlink_component",
                    "relative_path": relative_path,
                    "path": state.get("symlink_component"),
                }
            ]
        checklist.append(
            {
                "label": state["label"],
                "relative_path": relative_path,
                "path": str(evidence_dir / relative_path),
                "resolved_path": state.get("resolved_path"),
                "present": state["present"] is True,
                "valid": status == "present",
                "status": status,
                "sha256": state.get("sha256"),
                "size_bytes": state.get("size_bytes"),
                "hash_path_bound": state.get("hash_path_bound") is True,
                "hash_path_binding": binding_from_sibling_state(state),
                "required_for": closure_artifact_required_for(relative_path),
                "required_before_approved_bundle_builder": (
                    relative_path != APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH
                ),
                "required_to_close_approved_runtime_evidence": True,
                "counts_as_approved_runtime_evidence_by_this_report": False,
                "counts_as_runtime_evidence_by_this_report": False,
                "counts_as_sdk_evidence_by_this_report": False,
                "blockers": blockers,
            }
        )
    return checklist


def value_or_placeholder(value: str | None, placeholder: str) -> str:
    return value if value else placeholder


def target_scope(args: argparse.Namespace) -> dict[str, str | None]:
    query_port = args.query_port or DEFAULT_QUERY_PORTS.get((args.instance, args.map_name))
    target_key = None
    if args.instance and args.map_name:
        target_key = f"{args.instance}:{args.map_name}"
        if query_port:
            target_key = f"{target_key}:{query_port}"
    return {
        "instance": args.instance,
        "map": args.map_name,
        "query_port": query_port,
        "target_key": target_key,
    }


def passive_target_spec(args: argparse.Namespace) -> str:
    target = target_scope(args)
    instance = value_or_placeholder(target["instance"], "<instance>")
    map_name = value_or_placeholder(target["map"], "<map>")
    query_port = target["query_port"]
    if query_port:
        return f"{instance}:{map_name}:{query_port}"
    return f"{instance}:{map_name}"


def standing_launch_authority_receipt_state(
    evidence_dir: Path,
    *,
    run_id: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    receipt_path = evidence_dir / "operator-approval-receipt.json"
    target = target_scope(args)
    state: dict[str, Any] = {
        "receipt_relative_path": "operator-approval-receipt.json",
        "receipt_path": str(receipt_path),
        "recorded": False,
        "satisfies_operator_approval": False,
        "covers_target_run": False,
        "source_required": FRESH_CURRENT_TURN_OPERATOR_MESSAGE_SOURCE,
        "requires_fresh_current_turn_operator_approval": True,
        "approval_recorded_at_utc": None,
        "approval_source": None,
        "attestation": None,
        "bound_run_id": None,
        "bound_target": None,
        "target": target,
        "blockers": [],
    }

    def add_blocker(reason: str, **extra: Any) -> None:
        state["blockers"].append({"reason": reason, **extra})

    symlink = protected_paths.first_symlink_component(receipt_path)
    if symlink is not None:
        add_blocker("standing_launch_authority_receipt_symlink_component", path=str(symlink))
        return state
    if not receipt_path.is_file():
        add_blocker("standing_launch_authority_receipt_missing")
        return state
    try:
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        add_blocker("standing_launch_authority_receipt_json_invalid", detail=str(exc))
        return state
    except OSError as exc:
        add_blocker("standing_launch_authority_receipt_unreadable", detail=str(exc))
        return state
    if not isinstance(payload, dict):
        add_blocker("standing_launch_authority_receipt_json_not_object")
        return state

    completion = payload.get("operator_completion")
    if isinstance(completion, dict):
        state["approval_recorded_at_utc"] = completion.get("approval_recorded_at_utc")
        state["approval_source"] = completion.get("approval_source")
        state["attestation"] = completion.get("attestation")
    bound = payload.get("bound_request_pack")
    if isinstance(bound, dict):
        state["bound_run_id"] = bound.get("run_id")
        state["bound_target"] = bound.get("target")

    state["recorded"] = payload.get("standing_launch_authority_recorded") is True
    state["satisfies_operator_approval"] = (
        payload.get("standing_launch_authority_satisfies_operator_approval") is True
    )

    if payload.get("schema") != OPERATOR_APPROVAL_RECEIPT_SCHEMA:
        add_blocker("standing_launch_authority_receipt_schema_mismatch")
    if payload.get("status") != "completed_operator_receipt":
        add_blocker("standing_launch_authority_receipt_status_not_completed")
    if payload.get("receipt_completed") is not True:
        add_blocker("standing_launch_authority_receipt_completed_not_true")
    if payload.get("operator_current_turn_approval_recorded") is not False:
        add_blocker("standing_launch_authority_receipt_current_turn_flag_not_false")
    if not state["recorded"]:
        add_blocker("standing_launch_authority_not_recorded")
    if not state["satisfies_operator_approval"]:
        add_blocker("standing_launch_authority_not_bound_to_operator_approval")
    if not isinstance(completion, dict):
        add_blocker("standing_launch_authority_receipt_completion_missing")
    else:
        if not isinstance(completion.get("approval_recorded_at_utc"), str) or UTC_RE.fullmatch(
            completion.get("approval_recorded_at_utc", "")
        ) is None:
            add_blocker("standing_launch_authority_receipt_approved_at_invalid")
        if completion.get("approval_source") != APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY:
            add_blocker("standing_launch_authority_receipt_approval_source_mismatch")
        if completion.get("attestation") != APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY:
            add_blocker("standing_launch_authority_receipt_attestation_mismatch")
    if not isinstance(bound, dict):
        add_blocker("standing_launch_authority_receipt_bound_request_pack_missing")
        bound = {}
    if bound.get("run_id") != run_id:
        add_blocker(
            "standing_launch_authority_receipt_run_id_mismatch",
            expected=run_id,
            actual=bound.get("run_id"),
        )
    bound_target = bound.get("target")
    if not args.instance or not args.map_name:
        add_blocker("standing_launch_authority_target_args_missing")
    elif not isinstance(bound_target, dict):
        add_blocker("standing_launch_authority_receipt_target_missing")
    else:
        if bound_target.get("instance") != args.instance:
            add_blocker(
                "standing_launch_authority_receipt_instance_mismatch",
                expected=args.instance,
                actual=bound_target.get("instance"),
            )
        if bound_target.get("map") != args.map_name:
            add_blocker(
                "standing_launch_authority_receipt_map_mismatch",
                expected=args.map_name,
                actual=bound_target.get("map"),
            )
    for field, expected in {
        "copied_evidence_dir": evidence_dir,
        "copied_log_path": evidence_dir / "Obelisk.log",
        "window_manifest_path": evidence_dir / "window-manifest.env",
    }.items():
        declared = resolve_declared_artifact_path(bound.get(field), base_dir=receipt_path.parent)
        if declared is None:
            add_blocker(f"standing_launch_authority_receipt_{field}_missing")
        elif declared != expected.resolve():
            add_blocker(
                f"standing_launch_authority_receipt_{field}_mismatch",
                expected=str(expected.resolve()),
                actual=str(declared),
            )

    if not state["blockers"]:
        state["covers_target_run"] = True
        state["source_required"] = APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY
        state["requires_fresh_current_turn_operator_approval"] = False
    return state


def operator_authority_requirement_fields(
    standing_authority: dict[str, Any] | None,
    *,
    requires_operator_authority: bool = True,
) -> dict[str, Any]:
    standing_covers = bool(
        standing_authority and standing_authority.get("covers_target_run") is True
    )
    source_required = (
        APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY
        if standing_covers
        else FRESH_CURRENT_TURN_OPERATOR_MESSAGE_SOURCE
    )
    if not requires_operator_authority:
        source_required = NO_OPERATOR_AUTHORITY_SOURCE
    return {
        "requires_operator_authority_before_execution": requires_operator_authority,
        "operator_authority_source_required": source_required,
        "requires_current_turn_operator_approval": requires_operator_authority and not standing_covers,
        "requires_fresh_current_turn_operator_approval": requires_operator_authority and not standing_covers,
        "requires_bound_standing_launch_authority_receipt_before_execution": (
            requires_operator_authority and standing_covers
        ),
        "standing_launch_authority_covers_target_run": standing_covers,
        "standing_launch_authority_satisfies_operator_approval": standing_covers,
        "standing_launch_authority_receipt_path": (
            standing_authority.get("receipt_path") if standing_covers and standing_authority else None
        ),
    }


def ready_log_copy_post_window_flags(authority_fields: dict[str, Any]) -> list[str]:
    if authority_fields.get("requires_operator_authority_before_execution") is not True:
        return []
    if authority_fields.get("operator_authority_source_required") not in {
        FRESH_CURRENT_TURN_OPERATOR_MESSAGE_SOURCE,
        APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY,
    }:
        return []
    return list(READY_LOG_COPY_POST_WINDOW_EXECUTE_FLAGS)


def ready_log_copy_sidecar_guidance(sidecar_flags: list[str]) -> dict[str, Any]:
    return {
        "copy_helper_execute_sidecar_flags": sidecar_flags,
        "copy_helper_execute_sidecar_flags_scope": (
            "active_operator_followup_command_only"
            if sidecar_flags
            else "not_included_without_current_or_standing_operator_authority"
        ),
        "copy_helper_execute_sidecar_flags_authorize_this_report": False,
        "copy_helper_execute_sidecar_flags_count_as_evidence": False,
        "post_window_sidecar_generation_authorized_by_this_report": False,
        "post_window_preflight_live_read_authorized_by_this_report": False,
        "post_window_sidecar_generation_counts_as_approved_runtime_evidence": False,
        "post_window_preflight_live_read_counts_as_approved_runtime_evidence": False,
    }


def is_beta_testers_notice_path(value: str) -> bool:
    if value == NOTICE_PATH_NOT_APPLICABLE:
        return False
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    compact = normalized.replace(" ", "")
    tokens = set(normalized.split())
    if "beta" in tokens and ({"test", "tester", "testers", "users"} & tokens):
        return True
    return any(alias in compact for alias in ("betatest", "betatester", "betatesters", "betausers"))


def provided_operational_constraints(args: argparse.Namespace) -> list[dict[str, Any]]:
    constraints: list[dict[str, Any]] = []
    if args.the_island_off:
        constraints.append(
            {
                "constraint": "the_island_off",
                "provided": True,
                "must_preserve": True,
                "the_island_start_authorized_by_this_report": False,
            }
        )
    if args.two_server_cap_preserved:
        constraints.append(
            {
                "constraint": "two_server_cap",
                "provided": True,
                "must_preserve": True,
                "max_running_servers": 2,
                "server_concurrency_change_authorized_by_this_report": False,
            }
        )
    return constraints


def non_evidence_context_false_flags() -> dict[str, bool]:
    return {
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "live_ops_authorized": False,
        "live_log_reads_authorized": False,
        "runtime_capture_authorized": False,
        "workspace_writes_authorized": False,
        "discord_authorized": False,
        "discord_sent_by_this_report": False,
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "counts_toward_v1": False,
        "counts_toward_v1_completion": False,
        "counts_toward_p0_dependency_chain_claim_now": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "v1_completion_ready": False,
        "stable_claim_allowed": False,
        "sdk_progress": 0,
        "p0_progress": 0,
    }


def post_reboot_monitor_context(args: argparse.Namespace) -> dict[str, Any]:
    supplied = args.post_reboot_monitor_log is not None
    return {
        "schema": "obelisk.player-principal-lifecycle-post-reboot-monitor-context.v1",
        "path": str(args.post_reboot_monitor_log) if supplied else None,
        "path_supplied": supplied,
        "context_kind": "post_reboot_passive_monitor_log_path",
        "classification": "non_evidence_context",
        "stale_pid_safety_context_recorded": supplied,
        "current_passive_monitor_context_recorded": supplied,
        "read_by_this_report": False,
        "path_existence_checked_by_this_report": False,
        "process_control_authorized_by_this_report": False,
        "old_monitor_signal_authorized_by_this_report": False,
        "old_monitor_stop_authorized_by_this_report": False,
        "active_monitor_replacement_authorized_by_this_report": False,
        "notes": [
            "path is recorded for stale-PID safety and passive-monitor continuity only",
            "this closure report does not read the monitor log, signal old PIDs, or control monitor processes",
            "passive monitor context does not count as approved runtime evidence or SDK/P0 progress",
        ],
        **non_evidence_context_false_flags(),
    }


def confirmed_beta_notice_context(args: argparse.Namespace) -> dict[str, Any]:
    supplied = args.confirmed_beta_notice_json is not None
    payload: dict[str, Any] | None = None
    read_error: str | None = None
    if supplied:
        try:
            loaded = json.loads(args.confirmed_beta_notice_json.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                payload = loaded
            else:
                read_error = "confirmed_beta_notice_json_not_object"
        except FileNotFoundError:
            read_error = "confirmed_beta_notice_json_missing"
        except json.JSONDecodeError:
            read_error = "confirmed_beta_notice_json_invalid"
        except OSError:
            read_error = "confirmed_beta_notice_json_unreadable"
    completion_accepted = (
        payload is not None
        and payload.get("schema") == "obelisk.player-principal-lifecycle-beta-notice-prep.v1"
        and payload.get("mode") == "confirmed_send"
        and payload.get("discord_sent") is True
    )
    return {
        "schema": "obelisk.player-principal-lifecycle-confirmed-beta-notice-context.v1",
        "path": str(args.confirmed_beta_notice_json) if supplied else None,
        "path_supplied": supplied,
        "context_kind": "confirmed_beta_notice_json_path",
        "classification": "notice_action_context_only_non_evidence",
        "read_by_this_report": supplied,
        "path_existence_checked_by_this_report": supplied,
        "confirmed_notice_json_path_supplied": supplied,
        "confirmed_notice_action_context_recorded": supplied,
        "notice_completion_accepted_by_this_report": completion_accepted,
        "notice_completion_status": (
            "confirmed_beta_notice_completed"
            if completion_accepted
            else "not_confirmed_by_supplied_json"
            if supplied
            else "not_supplied"
        ),
        "source_schema": payload.get("schema") if payload is not None else None,
        "source_mode": payload.get("mode") if payload is not None else None,
        "source_discord_sent": payload.get("discord_sent") if payload is not None else None,
        "read_error": read_error,
        "activation_allowed_by_this_report": False,
        "notes": [
            "path is recorded as notice-action context only",
            "confirmed notice metadata does not authorize activation, runtime capture, live ops, or Discord by this report",
            "confirmed notice metadata does not count as approved runtime evidence or SDK/P0 progress",
        ],
        **non_evidence_context_false_flags(),
    }


def player_notice_requirements(args: argparse.Namespace, missing_roles: list[str]) -> dict[str, Any]:
    missing_roles_need_players = bool(missing_roles)
    future_window_needs_players = bool(args.future_window_needs_players or missing_roles_need_players)
    beta_notice_path_named = is_beta_testers_notice_path(args.notice_path)
    beta_notice_context = confirmed_beta_notice_context(args)
    confirmed_notice_completed = bool(beta_notice_context["notice_completion_accepted_by_this_report"])
    real_notice_required = future_window_needs_players and beta_notice_path_named and not confirmed_notice_completed
    required_action = (
        "send_current_turn_approved_beta_testers_notice_before_activation"
        if real_notice_required
        else None
    )
    return {
        "future_window_needs_players": future_window_needs_players,
        "future_window_needs_players_supplied": bool(args.future_window_needs_players),
        "missing_lifecycle_roles_need_players": missing_roles_need_players,
        "notice_path": args.notice_path,
        "notice_path_named": args.notice_path != NOTICE_PATH_NOT_APPLICABLE,
        "beta_testers_notice_path_named": beta_notice_path_named,
        "real_beta_testers_notice_action_required_before_activation": real_notice_required,
        "required_action": required_action,
        "must_be_real_notice_not_documentation": real_notice_required,
        "must_complete_after_dry_run_before_activation": real_notice_required,
        "confirmed_notice_action_completed": confirmed_notice_completed,
        "sent_by_this_report": False,
        "discord_sent_by_this_report": False,
        "discord_authorized_by_this_report": False,
        "discord_command_emitted_by_this_report": False,
        "server_operations_authorized_by_this_notice": False,
        "runtime_capture_authorized_by_this_notice": False,
        "workspace_writes_authorized_by_this_notice": False,
        "live_log_reads_authorized_by_this_notice": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_toward_sdk": False,
        "confirmed_beta_notice_context": beta_notice_context,
        "notes": [
            "this offline report records notice requirements only and sends no Discord message",
            "a beta testers notice path is an action requirement before activation, not passive documentation",
            "notice completion does not authorize server operations, runtime capture, live-log reads, workspace writes, or SDK progress",
        ],
    }


def required_notice_actions(
    notice_requirements: dict[str, Any],
    *,
    standing_authority: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not notice_requirements["real_beta_testers_notice_action_required_before_activation"]:
        return []
    return [
        {
            "operation": notice_requirements["required_action"],
            "notice_path": notice_requirements["notice_path"],
            "confirmed_beta_notice_context": notice_requirements["confirmed_beta_notice_context"],
            "notice_path_label_only": True,
            "required_before_activation": True,
            "authorized_to_run_now": False,
            **operator_authority_requirement_fields(standing_authority),
            "command_status": "NOT EMITTED",
            "command_text_not_emitted": True,
            "sent_by_this_report": False,
            "must_be_real_notice_not_documentation": True,
            "must_complete_after_dry_run_before_activation": True,
            **false_authorization_and_evidence_flags(),
            "blocker": "future player-dependent evidence activation named a beta testers notice path",
        }
    ]


def lifecycle_status_proof_failure_reason(
    role: str,
    observed_apply_status: str | None,
    observed_correlation_status: str | None,
) -> str:
    if role == "session_end":
        if observed_apply_status in {
            "session_end_unresolved_noop",
            "session_end_duplicate_noop",
            "session_end_stale_noop",
        }:
            return f"{observed_apply_status}_outcome"
        if observed_apply_status == "registry_failure":
            return "registry_failure_outcome"
        if observed_apply_status == "unsupported_observation":
            return "unsupported_observation_outcome"
        if observed_apply_status == "session_end_invalidated" and observed_correlation_status not in (
            "matched",
            None,
        ):
            return f"session_end_correlation_status_{observed_correlation_status}"
    return "lifecycle_event_status_proof_mismatch"


def lifecycle_status_proof_stale_material(
    role: str,
    observed_apply_status: str | None,
    observed_correlation_status: str | None,
) -> bool:
    return role == "session_end" and (
        observed_apply_status == "session_end_stale_noop"
        or observed_correlation_status == "stale"
    )


def command_string(parts: list[str], *, stdout_path: Path | None = None) -> str:
    command = shlex.join(parts)
    if stdout_path is None:
        return command
    return f"{command} > {shlex.quote(str(stdout_path))}"


def runner_command(argv: list[str], *, redirect_stdout: Path | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "argv": argv,
        "execution_mode": "no_shell_offline_helper",
        "shell": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
    }
    if redirect_stdout is not None:
        payload["redirect_stdout"] = str(redirect_stdout)
    return payload


def command_artifact_binding(
    path: Path,
    *,
    role: str,
    relative_path: str | None = None,
    argv_flags: tuple[str, ...] = (),
    argv_position: int | None = None,
    redirect_stdout: bool = False,
    required: bool = True,
    must_exist: bool | None = None,
) -> dict[str, Any]:
    symlink = protected_paths.first_symlink_component(path)
    expects_dir = role.endswith("_dir")
    exists = symlink is None and (path.is_dir() if expects_dir else path.is_file())
    if must_exist is None:
        must_exist = role == "input"
    payload: dict[str, Any] = {
        "role": role,
        "path": str(path),
        "resolved_path": str(path.expanduser().resolve()),
        "relative_path": relative_path,
        "required": required,
        "must_exist": must_exist,
        "exists": exists,
        "symlink_component": None if symlink is None else str(symlink),
    }
    if argv_flags:
        payload["argv_flags"] = list(argv_flags)
    if argv_position is not None:
        payload["argv_position"] = argv_position
    if redirect_stdout:
        payload["redirect_stdout"] = True
    if exists and not expects_dir:
        payload["sha256"] = sha256_file(path)
        payload["size_bytes"] = path.stat().st_size
    return payload


def command_path_binding(
    *,
    evidence_dir: Path,
    inputs: list[dict[str, Any]] | None = None,
    outputs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "schema": COMMAND_PATH_BINDING_SCHEMA,
        "evidence_dir": str(evidence_dir),
        "inputs": inputs or [],
        "outputs": outputs or [],
        "path_hash_bound": True,
        "fail_closed_on_missing_or_hash_mismatch": True,
        "authorized_by_this_binding": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "approved_runtime_evidence_accepted_by_checker": False,
        "copied_bundle_checker_acceptance_recorded": False,
    }


def post_window_next_actions_dry_run_report_path(evidence_dir: Path) -> Path:
    return evidence_dir.parent / f"{evidence_dir.name}.post-window-next-actions.dry-run.json"


def post_window_copy_bundle_preconditions(
    *,
    evidence_dir: Path,
    artifact: str,
    operation: str,
    blocked_until: list[str],
    sidecar_generation_required: bool,
) -> dict[str, Any]:
    dry_run_report = post_window_next_actions_dry_run_report_path(evidence_dir)
    sibling_set = [rel for _, rel in EXPECTED_SIBLINGS]
    payload = {
        "schema": POST_WINDOW_ACTION_CONTRACT_SCHEMA,
        "artifact": artifact,
        "operation": operation,
        "evidence_dir": str(evidence_dir),
        "expected_sibling_set": sibling_set,
        "required_sidecars": list(REQUIRED_SIDECARS),
        "required_closure_artifacts": list(REQUIRED_CLOSURE_ARTIFACTS),
        "copied_log_relative_path": "Obelisk.log",
        "approved_runtime_manifest_relative_path": APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
        "blocked_until": blocked_until,
        "dry_run_first_required": True,
        "dry_run_must_complete_before_execute": True,
        "dry_run_report_path": str(dry_run_report),
        "required_dry_run_artifacts": [str(dry_run_report)],
        "dry_run_report_counts_as_approved_runtime_evidence": False,
        "dry_run_report_authorizes_runtime": False,
        "runner_execute_requires_existing_dry_run_report": True,
        "sidecar_generation_required": sidecar_generation_required,
        "sidecar_generation_authorized_by_this_report": False,
        "sidecar_generation_counts_as_approved_runtime_evidence": False,
        "standing_authority_authorizes_execution": False,
        "standing_authority_counts_as_approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "copied_bundle_checker_acceptance_required_before_sdk_p0_changes": True,
        "accepted_checker_required_before_status_claim": True,
        "approved_runtime_evidence_accepted_by_checker": False,
        "copied_bundle_checker_acceptance_recorded": False,
        "sdk_p0_changes_authorized": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
    }
    return payload


def post_window_action_contract_fields(
    *,
    evidence_dir: Path,
    artifact: str,
    operation: str,
    blocked_until: list[str],
    sidecar_generation_required: bool,
) -> dict[str, Any]:
    contract = post_window_copy_bundle_preconditions(
        evidence_dir=evidence_dir,
        artifact=artifact,
        operation=operation,
        blocked_until=blocked_until,
        sidecar_generation_required=sidecar_generation_required,
    )
    return {
        "post_window_action_contract": contract,
        "post_window_copy_bundle_preconditions": contract,
        "dry_run_first_required": True,
        "dry_run_must_complete_before_execute": True,
        "dry_run_report_path": contract["dry_run_report_path"],
        "required_dry_run_artifacts": list(contract["required_dry_run_artifacts"]),
        "dry_run_report_counts_as_approved_runtime_evidence": False,
        "dry_run_report_authorizes_runtime": False,
        "sidecar_generation_required": sidecar_generation_required,
        "sidecar_generation_authorized_by_this_report": False,
        "sidecar_generation_counts_as_approved_runtime_evidence": False,
    }


def lifecycle_event_role_state(evidence_dir: Path, *, inspect: bool) -> dict[str, Any]:
    copied_log = evidence_dir / "Obelisk.log"
    state: dict[str, Any] = {
        "copied_log": str(copied_log),
        "copied_log_present": False,
        "copied_log_symlink_component": None,
        "roles_required": list(REQUIRED_LIFECYCLE_EVENT_ROLES),
        "required_copied_lifecycle_event_triplet": required_copied_lifecycle_event_triplet(),
        "required_copied_lifecycle_event_triplet_labels": list(
            REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS
        ),
        "roles_seen": [],
        "candidate_roles_seen": [],
        "matched_copied_lifecycle_event_triplet": [],
        "missing_copied_lifecycle_event_triplet": required_copied_lifecycle_event_triplet(),
        "missing_copied_lifecycle_event_triplet_labels": list(
            REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS
        ),
        "missing_roles": list(REQUIRED_LIFECYCLE_EVENT_ROLES),
        "complete_triplet_candidate": False,
        "exact_copied_lifecycle_event_triplet_complete": False,
        "partial_start_end_present": False,
        "missing_strict_rejected_start": True,
        "strict_rejected_start_expected_shape": STRICT_REJECTED_START_EXPECTED_SHAPE,
        "strict_rejected_start_observed_shape": None,
        "strict_rejected_start_observed_shape_counts_as_approved_runtime_evidence": False,
        "event_line_count": 0,
        "accepted_event_line_count": 0,
        "status_proof_required": REQUIRED_LIFECYCLE_STATUS_PROOFS,
        "status_proof_failures": [],
        "copied_lifecycle_triplet_match_failures": [],
        "duplicate_accepted_role_event_count": 0,
        "duplicate_accepted_roles": [],
        "duplicate_accepted_role_events": [],
        "lifecycle_event_ambiguity_blockers": [],
        "invalid_lifecycle_event_roles": [],
        "partial_accepted_lifecycle_role_set": False,
        "partial_accepted_lifecycle_roles_count_as_complete_closure_material": False,
        "partial_accepted_lifecycle_roles_count_as_approved_runtime_evidence": False,
        "diagnostic_or_rejected_lifecycle_lines_count_as_complete_closure_material": False,
        "diagnostic_or_rejected_lifecycle_lines_count_as_approved_runtime_evidence": False,
        "diagnostic_or_rejected_lifecycle_lines_count_as_sdk_or_p0_progress": False,
        "inspection_blocked_by": None,
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "counts_as_approved_runtime_evidence": False,
        "passive_snapshots_as_evidence": False,
        "passive_snapshots_count_as_evidence": False,
        "passive_snapshot_evidence_allowed": False,
        "passive_complete_triplet_counts_as_evidence": False,
        "runtime_capture_authorized": False,
        "reads_live_logs": False,
        "ready": False,
        "runtime_ready": False,
        "evidence_classification": "closure_request_role_presence_only_non_evidence",
    }
    if not inspect:
        state["inspection_blocked_by"] = "evidence_dir_not_inspected"
        return state
    symlink = protected_paths.first_symlink_component(copied_log)
    if symlink is not None:
        state["copied_log_symlink_component"] = str(symlink)
        state["inspection_blocked_by"] = "copied_log_symlink_component"
        return state
    if not copied_log.is_file():
        state["inspection_blocked_by"] = "copied_log_missing"
        return state

    state["copied_log_present"] = True
    roles_seen: list[str] = []
    candidate_roles_seen: list[str] = []
    matched_triplet_cases: list[dict[str, Any]] = []
    status_proof_failures: list[dict[str, Any]] = []
    copied_triplet_failures: list[dict[str, Any]] = []
    duplicate_accepted_role_events: list[dict[str, Any]] = []
    strict_rejected_start_observed: dict[str, Any] | None = None
    event_line_count = 0
    accepted_event_line_count = 0
    try:
        with copied_log.open("r", encoding="utf-8", errors="replace") as handle:
            for line_number, line in enumerate(handle, start=1):
                match = PLAYER_PRINCIPAL_LIFECYCLE_EVENT_RE.search(line)
                if match is None:
                    continue
                event_line_count += 1
                role = match.group("role")
                if role not in candidate_roles_seen:
                    candidate_roles_seen.append(role)
                values = log_key_values(line)
                expected = REQUIRED_LIFECYCLE_STATUS_PROOFS[role]
                observed_apply_status = values.get("apply_status")
                observed_correlation_status = values.get("correlation_status")
                observed_case = observed_copied_lifecycle_event_case(
                    role=role,
                    line_number=line_number,
                    sequence=match.group("sequence"),
                    values=values,
                )
                if (
                    observed_apply_status != expected["apply_status"]
                    or observed_correlation_status != expected["correlation_status"]
                ):
                    failure_reason = lifecycle_status_proof_failure_reason(
                        role,
                        observed_apply_status,
                        observed_correlation_status,
                    )
                    status_proof_failures.append(
                        {
                            "line": line_number,
                            "sequence": match.group("sequence"),
                            "role": role,
                            "reason": failure_reason,
                            "expected_apply_status": expected["apply_status"],
                            "observed_apply_status": observed_apply_status,
                            "expected_correlation_status": expected["correlation_status"],
                            "observed_correlation_status": observed_correlation_status,
                            "accepted_as_lifecycle_role": False,
                            "stale_missing_role_material": lifecycle_status_proof_stale_material(
                                role,
                                observed_apply_status,
                                observed_correlation_status,
                            ),
                            "counts_as_missing_role_material": False,
                            "counts_as_approved_runtime_evidence": False,
                            "counts_as_runtime_evidence": False,
                            "counts_as_sdk_evidence": False,
                            "passive_snapshots_as_evidence": False,
                        }
                    )
                    if role == "session_start_rejected" and strict_rejected_start_observed is None:
                        strict_rejected_start_observed = strict_rejected_start_observed_shape(
                            observed_case,
                            accepted_as_lifecycle_role=False,
                            reason=failure_reason,
                        )
                    continue
                expected_case = REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_BY_ROLE[role]
                triplet_failure_reason = copied_lifecycle_triplet_failure_reason(
                    observed_case,
                    expected_case,
                )
                if triplet_failure_reason is not None:
                    copied_triplet_failures.append(
                        {
                            **observed_case,
                            "reason": triplet_failure_reason,
                            "expected_label": expected_case["label"],
                            "expected_target": expected_case["target"],
                            "expected_copied_bool_fields": list(
                                expected_case["copied_bool_fields"]
                            ),
                            "observed_copied_bool_fields": observed_case["copied_bool_fields"],
                            "expected_copied_bool_values": list(
                                expected_case["copied_bool_values"]
                            ),
                            "observed_copied_bool_values": observed_case["copied_bool_values"],
                            "accepted_as_lifecycle_role": False,
                            "counts_as_approved_runtime_evidence": False,
                            "counts_as_runtime_evidence": False,
                            "counts_as_sdk_evidence": False,
                            "passive_snapshots_as_evidence": False,
                        }
                    )
                    if role == "session_start_rejected" and strict_rejected_start_observed is None:
                        strict_rejected_start_observed = strict_rejected_start_observed_shape(
                            observed_case,
                            accepted_as_lifecycle_role=False,
                            reason=triplet_failure_reason,
                        )
                    continue
                accepted_event_line_count += 1
                if role not in roles_seen:
                    roles_seen.append(role)
                    matched_triplet_cases.append(
                        {
                            **observed_case,
                            "label": expected_case["label"],
                            "expected_target": expected_case["target"],
                            "expected_copied_bool_fields": list(
                                expected_case["copied_bool_fields"]
                            ),
                            "expected_copied_bool_values": list(
                                expected_case["copied_bool_values"]
                            ),
                            "accepted_as_lifecycle_role": True,
                            "counts_as_approved_runtime_evidence": False,
                            "counts_as_runtime_evidence": False,
                            "counts_as_sdk_evidence": False,
                        }
                    )
                    if role == "session_start_rejected" and strict_rejected_start_observed is None:
                        strict_rejected_start_observed = strict_rejected_start_observed_shape(
                            observed_case,
                            accepted_as_lifecycle_role=True,
                            reason=None,
                        )
                else:
                    duplicate_accepted_role_events.append(
                        {
                            **observed_case,
                            "reason": "copied_lifecycle_event_duplicate_role_proof",
                            "expected_label": expected_case["label"],
                            "accepted_as_lifecycle_role": False,
                            "counts_as_approved_runtime_evidence": False,
                            "counts_as_runtime_evidence": False,
                            "counts_as_sdk_evidence": False,
                            "passive_snapshots_as_evidence": False,
                        }
                    )
    except OSError as exc:
        state["inspection_blocked_by"] = f"copied_log_read_error:{exc.__class__.__name__}"
        return state

    ordered_roles_seen = [role for role in REQUIRED_LIFECYCLE_EVENT_ROLES if role in roles_seen]
    invalid_roles = [
        role
        for role in REQUIRED_LIFECYCLE_EVENT_ROLES
        if any(failure["role"] == role for failure in status_proof_failures)
        or any(failure["role"] == role for failure in copied_triplet_failures)
        or any(event["role"] == role for event in duplicate_accepted_role_events)
    ]
    duplicate_roles = [
        role
        for role in REQUIRED_LIFECYCLE_EVENT_ROLES
        if any(event["role"] == role for event in duplicate_accepted_role_events)
    ]
    missing_roles = [
        role
        for role in REQUIRED_LIFECYCLE_EVENT_ROLES
        if role not in ordered_roles_seen or role in invalid_roles
    ]
    missing_triplet_cases = [
        jsonable_triplet_case(REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_BY_ROLE[role])
        for role in REQUIRED_LIFECYCLE_EVENT_ROLES
        if role in missing_roles
    ]
    missing_triplet_labels = [case["label"] for case in missing_triplet_cases]
    exact_triplet_complete = (
        bool(ordered_roles_seen)
        and not missing_roles
        and not status_proof_failures
        and not copied_triplet_failures
        and not duplicate_accepted_role_events
    )
    partial_accepted_role_set = bool(ordered_roles_seen) and bool(missing_roles)
    missing_strict_rejected_start = "session_start_rejected" in missing_roles
    partial_start_end_present = (
        "session_start" in ordered_roles_seen
        and "session_end" in ordered_roles_seen
        and missing_strict_rejected_start
    )
    state.update(
        {
            "roles_seen": ordered_roles_seen,
            "candidate_roles_seen": [
                role for role in REQUIRED_LIFECYCLE_EVENT_ROLES if role in candidate_roles_seen
            ],
            "matched_copied_lifecycle_event_triplet": matched_triplet_cases,
            "missing_copied_lifecycle_event_triplet": missing_triplet_cases,
            "missing_copied_lifecycle_event_triplet_labels": missing_triplet_labels,
            "missing_roles": missing_roles,
            "complete_triplet_candidate": exact_triplet_complete,
            "exact_copied_lifecycle_event_triplet_complete": exact_triplet_complete,
            "partial_start_end_present": partial_start_end_present,
            "missing_strict_rejected_start": missing_strict_rejected_start,
            "strict_rejected_start_expected_shape": STRICT_REJECTED_START_EXPECTED_SHAPE,
            "strict_rejected_start_observed_shape": strict_rejected_start_observed,
            "strict_rejected_start_observed_shape_counts_as_approved_runtime_evidence": False,
            "event_line_count": event_line_count,
            "accepted_event_line_count": accepted_event_line_count,
            "status_proof_failures": status_proof_failures,
            "copied_lifecycle_triplet_match_failures": copied_triplet_failures,
            "duplicate_accepted_role_event_count": len(duplicate_accepted_role_events),
            "duplicate_accepted_roles": duplicate_roles,
            "duplicate_accepted_role_events": duplicate_accepted_role_events,
            "lifecycle_event_ambiguity_blockers": [
                f"copied-lifecycle-triplet-ambiguous/{role}" for role in duplicate_roles
            ],
            "invalid_lifecycle_event_roles": invalid_roles,
            "partial_accepted_lifecycle_role_set": partial_accepted_role_set,
            "partial_accepted_lifecycle_roles_count_as_complete_closure_material": False,
            "partial_accepted_lifecycle_roles_count_as_approved_runtime_evidence": False,
            "diagnostic_or_rejected_lifecycle_lines_count_as_complete_closure_material": False,
            "diagnostic_or_rejected_lifecycle_lines_count_as_approved_runtime_evidence": False,
            "diagnostic_or_rejected_lifecycle_lines_count_as_sdk_or_p0_progress": False,
            "inspection_blocked_by": None,
        }
    )
    return state


def missing_operation(
    *,
    relative_path: str,
    evidence_dir: Path,
    run_id: str,
    args: argparse.Namespace,
    standing_authority: dict[str, Any] | None,
    role_state: dict[str, Any],
) -> dict[str, Any]:
    instance = value_or_placeholder(args.instance, "<instance>")
    map_name = value_or_placeholder(args.map_name, "<map>")
    window_manifest = evidence_dir / "window-manifest.env"
    copied_log = evidence_dir / "Obelisk.log"
    exact_triplet_ready = role_state.get("exact_copied_lifecycle_event_triplet_complete") is True
    if relative_path == "window-manifest.env":
        blocked_until = [
            *copied_triplet_blockers(role_state),
            "Obelisk.log",
            "window-request.json",
            "observer-window.env",
            "operator-approval-request.md",
            "operator-approval-receipt.json",
            "preflight-pre.json",
        ]
        template_argv = [
            "scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py",
            "--emit-template",
            str(window_manifest),
            "--copied-log",
            str(copied_log),
        ]
        validation_argv = [
            "scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py",
            "--json",
            "--post-window-replay",
            str(window_manifest),
        ]
        template_command = command_string(template_argv)
        validation_command = command_string(validation_argv)
        template_binding = command_path_binding(
            evidence_dir=evidence_dir,
            inputs=[
                command_artifact_binding(
                    copied_log,
                    role="input",
                    relative_path="Obelisk.log",
                    argv_flags=("--copied-log",),
                )
            ],
            outputs=[
                command_artifact_binding(
                    window_manifest,
                    role="output",
                    relative_path="window-manifest.env",
                    argv_flags=("--emit-template",),
                    must_exist=False,
                )
            ],
        )
        validation_binding = command_path_binding(
            evidence_dir=evidence_dir,
            inputs=[
                command_artifact_binding(
                    window_manifest,
                    role="input",
                    relative_path="window-manifest.env",
                    argv_flags=("--post-window-replay",),
                )
            ],
        )
        return {
            "artifact": relative_path,
            "operation": "provide_completed_window_manifest_env_sibling",
            "post_reboot_monitor_context": post_reboot_monitor_context(args),
            "confirmed_beta_notice_context": confirmed_beta_notice_context(args),
            "authorized_to_run_now": False,
            **operator_authority_requirement_fields(standing_authority),
            "writes_under_evidence_dir": True,
            "command_status": "NOT EXECUTED" if exact_triplet_ready else "NOT PROVIDED",
            **(
                {
                    "command_text_not_executed": template_command,
                    "validation_command_text_not_executed": validation_command,
                    "runner_command": runner_command(template_argv),
                    "validation_runner_command": runner_command(validation_argv),
                    "command_path_binding": template_binding,
                    "validation_command_path_binding": validation_binding,
                    "command_path_hash_bound": True,
                }
                if exact_triplet_ready
                else {}
            ),
            "command_text_not_emitted": not exact_triplet_ready,
            "runner_command_available": exact_triplet_ready,
            "machine_executable": exact_triplet_ready,
            "blocked_until": blocked_until,
            **post_window_action_contract_fields(
                evidence_dir=evidence_dir,
                artifact=relative_path,
                operation="provide_completed_window_manifest_env_sibling",
                blocked_until=blocked_until,
                sidecar_generation_required=True,
            ),
            **copied_triplet_action_requirements(role_state),
            **false_authorization_and_evidence_flags(),
            "blocker": (
                "missing operational window manifest sibling"
                if exact_triplet_ready
                else "missing operational window manifest sibling; command withheld until exact copied lifecycle triplet is present"
            ),
        }
    if relative_path == "preflight-post.json":
        blocked_until = [
            *copied_triplet_blockers(role_state),
            "Obelisk.log",
            "window-manifest.env",
        ]
        preflight_argv = [
            "scripts/check_player_principal_lifecycle_preflight.sh",
            "--instance",
            instance,
            "--map",
            map_name,
            "--mode",
            "stable",
            "--expected-binary-sha256",
            args.expected_binary_sha256,
            "--run-id",
            run_id,
            "--window-manifest",
            str(window_manifest),
            "--copied-log",
            str(copied_log),
            "--evidence-dir",
            str(evidence_dir),
            "--allow-live-procfs-read",
            "--allow-protected-root",
            "--json",
        ]
        preflight_stdout = evidence_dir / "preflight-post.json"
        command = command_string(preflight_argv, stdout_path=preflight_stdout)
        preflight_binding = command_path_binding(
            evidence_dir=evidence_dir,
            inputs=[
                command_artifact_binding(
                    window_manifest,
                    role="input",
                    relative_path="window-manifest.env",
                    argv_flags=("--window-manifest",),
                ),
                command_artifact_binding(
                    copied_log,
                    role="input",
                    relative_path="Obelisk.log",
                    argv_flags=("--copied-log",),
                ),
            ],
            outputs=[
                command_artifact_binding(
                    preflight_stdout,
                    role="output",
                    relative_path="preflight-post.json",
                    redirect_stdout=True,
                    must_exist=False,
                )
            ],
        )
        return {
            "artifact": relative_path,
            "operation": "capture_post_window_stable_preflight_json",
            "post_reboot_monitor_context": post_reboot_monitor_context(args),
            "confirmed_beta_notice_context": confirmed_beta_notice_context(args),
            "authorized_to_run_now": False,
            **operator_authority_requirement_fields(standing_authority),
            "writes_under_evidence_dir": True,
            "command_status": "NOT EXECUTED" if exact_triplet_ready else "NOT PROVIDED",
            **(
                {
                    "command_text_not_executed": command,
                    "command_path_binding": preflight_binding,
                    "command_path_hash_bound": True,
                }
                if exact_triplet_ready
                else {}
            ),
            "command_text_not_emitted": not exact_triplet_ready,
            "runner_command_available": False,
            "machine_executable": False,
            "blocked_until": blocked_until,
            **post_window_action_contract_fields(
                evidence_dir=evidence_dir,
                artifact=relative_path,
                operation="capture_post_window_stable_preflight_json",
                blocked_until=blocked_until,
                sidecar_generation_required=True,
            ),
            **copied_triplet_action_requirements(role_state),
            **false_authorization_and_evidence_flags(),
            "blocker": (
                "missing post-window stable preflight sibling"
                if exact_triplet_ready
                else "missing post-window stable preflight sibling; command withheld until exact copied lifecycle triplet is present"
            ),
        }
    if relative_path == "approved-bundle/approved-runtime-principal-lifecycle-evidence.json":
        blocked_until = [
            *copied_triplet_blockers(role_state),
            "Obelisk.log",
            *[
                rel
                for rel in REQUIRED_SIDECARS
                if rel != APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH
            ],
        ]
        commit_binding = bundle_command_commit_binding(window_manifest, args)
        reviewer_blockers: list[str] = []
        if not args.reviewed_by:
            reviewer_blockers.append("reviewed_by_required_for_direct_bundle_command")
        if not args.review_note:
            reviewer_blockers.append("review_note_required_for_direct_bundle_command")
        triplet_command_blockers = (
            []
            if role_state.get("exact_copied_lifecycle_event_triplet_complete") is True
            else ["exact_copied_lifecycle_event_triplet_required_before_bundle_command"]
        )
        command_ready = (
            commit_binding["ready"]
            and not reviewer_blockers
            and not triplet_command_blockers
        )
        bundle_argv = [
            "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py",
            "--copied-log",
            str(copied_log),
            "--window-manifest",
            str(window_manifest),
            "--output-dir",
            str(evidence_dir / "approved-bundle"),
            "--obelisk-commit",
            str(commit_binding["command_obelisk_commit"]),
            "--reviewed-by",
            str(args.reviewed_by),
            "--review-note",
            str(args.review_note),
        ]
        bundle_binding = command_path_binding(
            evidence_dir=evidence_dir,
            inputs=[
                command_artifact_binding(
                    copied_log,
                    role="input",
                    relative_path="Obelisk.log",
                    argv_flags=("--copied-log",),
                ),
                command_artifact_binding(
                    window_manifest,
                    role="input",
                    relative_path="window-manifest.env",
                    argv_flags=("--window-manifest",),
                ),
            ],
            outputs=[
                command_artifact_binding(
                    evidence_dir / "approved-bundle",
                    role="output_dir",
                    relative_path="approved-bundle",
                    argv_flags=("--output-dir",),
                    must_exist=False,
                ),
                command_artifact_binding(
                    evidence_dir / APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
                    role="output",
                    relative_path=APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
                    must_exist=False,
                ),
            ],
        )
        command = command_string(bundle_argv) if command_ready else None
        command_blockers = [
            *triplet_command_blockers,
            *commit_binding["blockers"],
            *reviewer_blockers,
        ]
        return {
            "artifact": relative_path,
            "operation": "build_approved_runtime_principal_lifecycle_evidence_bundle",
            "post_reboot_monitor_context": post_reboot_monitor_context(args),
            "confirmed_beta_notice_context": confirmed_beta_notice_context(args),
            "authorized_to_run_now": False,
            **operator_authority_requirement_fields(standing_authority),
            "writes_under_evidence_dir": True,
            "command_status": "NOT EXECUTED" if command is not None else "NOT PROVIDED",
            **(
                {
                    "command_text_not_executed": command,
                    "runner_command": runner_command(bundle_argv),
                    "command_path_binding": bundle_binding,
                    "command_path_hash_bound": True,
                }
                if command is not None
                else {}
            ),
            "command_text_not_emitted": command is None,
            "runner_command_available": command is not None,
            "machine_executable": command is not None,
            "blocked_until": [
                *blocked_until,
                *[f"bundle-command/{reason}" for reason in command_blockers],
            ],
            "bundle_command_commit_binding": commit_binding,
            "bundle_command_blockers": command_blockers,
            **post_window_action_contract_fields(
                evidence_dir=evidence_dir,
                artifact=relative_path,
                operation="build_approved_runtime_principal_lifecycle_evidence_bundle",
                blocked_until=[
                    *blocked_until,
                    *[f"bundle-command/{reason}" for reason in command_blockers],
                ],
                sidecar_generation_required=False,
            ),
            **copied_triplet_action_requirements(role_state),
            **false_authorization_and_evidence_flags(),
            "blocker": (
                "missing approved runtime manifest bundle output"
                if command is not None
                else "missing approved runtime manifest bundle output; direct bundle command blocked until exact copied lifecycle event triplet is present"
                if triplet_command_blockers
                else "missing approved runtime manifest bundle output; direct bundle command blocked by commit or reviewer metadata binding"
            ),
        }
    return {
        "artifact": relative_path,
        "operation": "provide_missing_required_sibling",
        "post_reboot_monitor_context": post_reboot_monitor_context(args),
        "confirmed_beta_notice_context": confirmed_beta_notice_context(args),
        "authorized_to_run_now": False,
        **operator_authority_requirement_fields(standing_authority),
        "writes_under_evidence_dir": True,
        **copied_triplet_action_requirements(role_state),
        **false_authorization_and_evidence_flags(),
        "blocker": "missing required sibling",
    }


def missing_copied_log_operation(
    *,
    evidence_dir: Path,
    args: argparse.Namespace,
    standing_authority: dict[str, Any] | None,
    ready_log_copy_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    instance = value_or_placeholder(args.instance, "<instance>")
    approved_window = approved_window_from_request(evidence_dir)
    authority_fields = operator_authority_requirement_fields(standing_authority)
    sidecar_flags = ready_log_copy_post_window_flags(authority_fields)
    if ready_log_copy_report is not None and ready_log_copy_active_no_triplet(
        ready_log_copy_report
    ):
        source_state = ready_log_copy_report.get("source_log_not_ready")
        if not isinstance(source_state, dict):
            source_state = ready_log_copy_report.get("observer_only_no_role_window")
        if not isinstance(source_state, dict):
            source_state = {}
        blocked_until = copied_triplet_blockers()
        return {
            "artifact": "Obelisk.log",
            "missing_kind": "observer_only_no_role_window_wait_state",
            "operation": "wait_for_active_observer_only_no_role_window_exact_triplet_or_end",
            "post_reboot_monitor_context": post_reboot_monitor_context(args),
            "confirmed_beta_notice_context": confirmed_beta_notice_context(args),
            "approved_window": approved_window,
            "authorized_to_run_now": False,
            "requires_operator_authority_before_execution": False,
            "operator_authority_source_required": NO_OPERATOR_AUTHORITY_SOURCE,
            "requires_current_turn_operator_approval": False,
            "requires_fresh_current_turn_operator_approval": False,
            "requires_bound_standing_launch_authority_receipt_before_execution": False,
            "standing_launch_authority_covers_target_run": False,
            "standing_approval_allowed": False,
            "writes_under_evidence_dir": False,
            "writes_under_server_root": False,
            "reads_live_logs": False,
            "command_status": "NOT PROVIDED",
            "command_text_not_emitted": (
                "active observer-only/no-role source log is still in wait-state; "
                "copy command is withheld until the exact copied lifecycle triplet appears or the window expires"
            ),
            "runner_command_available": False,
            "machine_executable": False,
            "blocked_until": blocked_until,
            "source_log_not_ready": source_state,
            "observer_only_no_role_window": source_state,
            "observer_only_no_role_window_detected": True,
            "active_observer_only_no_role_window": True,
            "post_window_observer_only_no_role_window": False,
            "observer_only_no_role_window_state": "in_progress",
            "post_window_closure_action": None,
            "active_window_not_closure_ready": True,
            "source_log_ready_to_copy": False,
            "manual_offline_next_steps": string_list(
                source_state.get("manual_offline_next_steps")
            ),
            **copied_triplet_action_requirements(),
            **false_authorization_and_evidence_flags(),
            "blocker": (
                "active observer-only/no-role source log remains wait-state; copy, "
                "bundle, and checker commands require an exact accepted lifecycle triplet"
            ),
            "notes": [
                "do not close or copy an active observer-enable-only/no-role window",
                "rerun the copy-readiness dry-run if lifecycle events arrive before the window ends",
                "classify the window after it expires if only observer-enable/no-role material is present",
            ],
        }
    if ready_log_copy_report is not None and ready_log_copy_post_window_no_triplet(
        ready_log_copy_report
    ):
        source_state = ready_log_copy_report.get("source_log_not_ready")
        if not isinstance(source_state, dict):
            source_state = ready_log_copy_report.get("observer_only_no_role_window")
        if not isinstance(source_state, dict):
            source_state = {}
        blocked_until = copied_triplet_blockers()
        return {
            "artifact": "Obelisk.log",
            "missing_kind": "observer_only_no_role_window_non_evidence",
            "operation": "close_observer_only_no_role_window_as_non_evidence",
            "post_reboot_monitor_context": post_reboot_monitor_context(args),
            "confirmed_beta_notice_context": confirmed_beta_notice_context(args),
            "approved_window": approved_window,
            "authorized_to_run_now": False,
            "requires_operator_authority_before_execution": False,
            "operator_authority_source_required": NO_OPERATOR_AUTHORITY_SOURCE,
            "requires_current_turn_operator_approval": False,
            "requires_fresh_current_turn_operator_approval": False,
            "requires_bound_standing_launch_authority_receipt_before_execution": False,
            "standing_launch_authority_covers_target_run": False,
            "standing_approval_allowed": False,
            "writes_under_evidence_dir": False,
            "writes_under_server_root": False,
            "reads_live_logs": False,
            "command_status": "NOT PROVIDED",
            "command_text_not_emitted": (
                "post-window observer-only/no-role source log has no exact copied "
                "lifecycle triplet; copy command is not emitted"
            ),
            "runner_command_available": False,
            "machine_executable": False,
            "blocked_until": blocked_until,
            "source_log_not_ready": source_state,
            "observer_only_no_role_window": source_state,
            "observer_only_no_role_window_detected": True,
            "active_observer_only_no_role_window": False,
            "post_window_observer_only_no_role_window": True,
            "observer_only_no_role_window_state": "post_window",
            "post_window_closure_action": (
                source_state.get("post_window_closure_action")
                or "close_observer_only_no_role_window_as_non_evidence"
            ),
            "manual_offline_next_steps": string_list(
                source_state.get("manual_offline_next_steps")
            ),
            **copied_triplet_action_requirements(),
            **false_authorization_and_evidence_flags(),
            "blocker": (
                "post-window observer-only/no-role source log is non-evidence; "
                "copy and bundle commands require a fresh exact copied lifecycle triplet"
            ),
            "notes": [
                "no copied Obelisk.log is produced from an observer-enable-only/no-role window",
                "copy and bundle commands stay unavailable until an exact accepted lifecycle triplet is present",
                "prepare a fresh player-backed window under separate current-turn scope if evidence is still needed",
            ],
        }
    command_parts = [
        "scripts/copy_player_principal_lifecycle_ready_log.py",
        "--instance",
        instance,
        "--evidence-dir",
        str(evidence_dir),
        "--expected-binary-sha256",
        args.expected_binary_sha256,
    ]
    if approved_window["valid"]:
        command_parts.extend(
            [
                "--fresh-window-start-utc",
                str(approved_window["start_utc"]),
                "--fresh-window-end-utc",
                str(approved_window["end_utc"]),
            ]
        )
    command_parts.extend(sidecar_flags)
    command_parts.extend(
        [
            "--allow-live-log-read",
            "--allow-evidence-dir-write",
            "--execute",
            "--json-output",
            str(evidence_dir / READY_LOG_COPY_RELATIVE_PATH),
        ]
    )
    command = command_string(command_parts)
    copy_binding = command_path_binding(
        evidence_dir=evidence_dir,
        outputs=[
            command_artifact_binding(
                evidence_dir / "Obelisk.log",
                role="output",
                relative_path="Obelisk.log",
                must_exist=False,
            ),
            command_artifact_binding(
                evidence_dir / READY_LOG_COPY_RELATIVE_PATH,
                role="output",
                relative_path=READY_LOG_COPY_RELATIVE_PATH,
                argv_flags=("--json-output",),
                must_exist=False,
            ),
        ],
    )
    blocked_until = [
        *(
            []
            if approved_window["valid"]
            else [f"fresh-window/{reason}" for reason in approved_window["blockers"]]
        ),
        *copied_triplet_blockers(),
    ]
    return {
        "artifact": "Obelisk.log",
        "operation": "copy_ready_player_principal_lifecycle_obelisk_log",
        "post_reboot_monitor_context": post_reboot_monitor_context(args),
        "confirmed_beta_notice_context": confirmed_beta_notice_context(args),
        "approved_window": approved_window,
        "authorized_to_run_now": False,
        **authority_fields,
        "writes_under_evidence_dir": True,
        "writes_under_server_root": False,
        "reads_live_logs": False,
        "command_status": "NOT EXECUTED",
        "command_text_not_executed": command,
        "command_path_binding": copy_binding,
        "command_path_hash_bound": True,
        "runner_command_available": False,
        "machine_executable": False,
        "blocked_until": blocked_until,
        **post_window_action_contract_fields(
            evidence_dir=evidence_dir,
            artifact="Obelisk.log",
            operation="copy_ready_player_principal_lifecycle_obelisk_log",
            blocked_until=blocked_until,
            sidecar_generation_required=True,
        ),
        **ready_log_copy_sidecar_guidance(sidecar_flags),
        **copied_triplet_action_requirements(),
        **false_authorization_and_evidence_flags(),
        "blocker": "copied Obelisk.log missing; copy only after live log has exact copied lifecycle event triplet",
        "notes": [
            "copy helper requires explicit live-log-read and evidence-dir-write flags",
            "copy helper may become actionable only after HandleNewPlayer(1,1), CheckJoinInProgress(1,0), and OnLogout matched are present in the approved runtime window",
            "post-window sidecar flags are copy-helper execute prerequisites only and do not authorize this report",
            "copy helper also requires the approved window start/end from window-request.json",
            "copied log remains non-evidence until sibling-set bundle checkers accept it",
        ],
    }


def invalid_evidence_source_operation(
    *,
    evidence_dir: Path,
    args: argparse.Namespace,
    standing_authority: dict[str, Any] | None,
    evidence_source_blockers: list[dict[str, Any]],
    missing_required: list[str],
    missing_sidecars: list[str],
    role_state: dict[str, Any],
) -> dict[str, Any]:
    guidance = closure_compatible_copy_guidance(evidence_dir)
    suggested_closure_dir = guidance["suggested_closure_evidence_dir"]
    after_manual_staging_command = None
    if suggested_closure_dir is not None:
        after_manual_staging_command = closure_request_rerun_command(
            args,
            Path(str(suggested_closure_dir)),
        )
    missing_roles = list(role_state.get("missing_roles", []))
    return {
        "artifact": str(evidence_dir),
        "missing_kind": "invalid_evidence_source",
        "operation": "stage_closure_compatible_player_principal_lifecycle_evidence_root",
        "source_evidence_dir": str(evidence_dir),
        "invalid_source_evidence_dir": str(evidence_dir),
        "source_root_role": guidance["source_root_role"],
        "source_run_id": guidance["source_run_id"],
        "source_root_valid_for_closure": False,
        "source_looks_like_passive_monitor_root": guidance["source_looks_like_passive_monitor_root"],
        "closure_compatible_evidence_dir": suggested_closure_dir,
        "suggested_closure_evidence_dir": suggested_closure_dir,
        "suggested_valid_closure_run_id": guidance["suggested_valid_closure_run_id"],
        "suggested_valid_closure_evidence_dir": guidance["suggested_valid_closure_evidence_dir"],
        "suggested_valid_closure_root_role": guidance["suggested_valid_closure_root_role"],
        "source_accepted_as_closure_evidence_dir": False,
        "source_becomes_closure_root": False,
        "passive_monitor_root_accepted_as_closure_evidence_dir": False,
        "machine_action_suggested_for_invalid_passive_root": False,
        "machine_executable": False,
        "runner_command_available": False,
        "manual_staging_required_before_machine_actions": True,
        "copy_or_stage_into_closure_compatible_run_required_before_closure": True,
        "explicit_execution_write_flags_required": True,
        "post_reboot_monitor_context": post_reboot_monitor_context(args),
        "confirmed_beta_notice_context": confirmed_beta_notice_context(args),
        "authorized_to_run_now": False,
        **operator_authority_requirement_fields(standing_authority),
        "writes_under_evidence_dir": False,
        "writes_under_server_root": False,
        "command_status": "NOT PROVIDED",
        "command_text_not_emitted": (
            "stage exact copied Obelisk.log and required sibling sidecars into the "
            "suggested closure-compatible lifecycle evidence directory before rerunning closure"
        ),
        "after_manual_staging_closure_request_command_text_not_executed": after_manual_staging_command,
        "closure_compatible_copy_guidance": guidance,
        "evidence_source_blockers": evidence_source_blockers,
        "missing_required_artifacts_at_source_root": missing_required,
        "missing_sidecars_at_source_root": missing_sidecars,
        "missing_lifecycle_event_roles_at_source_root": missing_roles,
        "missing_copied_lifecycle_event_triplet_at_source_root": role_state.get(
            "missing_copied_lifecycle_event_triplet", []
        ),
        "missing_copied_lifecycle_event_triplet_labels_at_source_root": role_state.get(
            "missing_copied_lifecycle_event_triplet_labels", []
        ),
        "manual_offline_next_steps": [
            "do not use the passive monitor root as --evidence-dir for closure",
            "create or select the suggested YYYYMMDDThhmmssZ-player-principal-lifecycle root",
            "stage the copied Obelisk.log plus window request, observer env, operator approval request/receipt, preflight, manifest, and approved-bundle sidecars into that valid root",
            "rerun the closure helper against the valid root before deriving any role, copy, bundle, or checker action",
        ],
        "deferred_missing_role_offline_next_steps": [
            (
                f"role {role} is unresolved in the source root only; rerun closure on "
                "the valid staged root before requesting runtime observation for this role"
            )
            for role in missing_roles
        ],
        "blocked_until": [
            "closure-compatible run id",
            "exact copied Obelisk.log and required sibling sidecars staged in that run",
        ],
        **false_authorization_and_evidence_flags(),
        "blocker": "evidence source is not a closure-compatible player-principal lifecycle run",
        "notes": [
            "do not submit passive monitor roots as --evidence-dir for closure",
            "passive monitor roots are diagnostic context only and are not approved runtime evidence",
            "copy/stage work is not authorized by this closure request",
        ],
    }


def missing_role_operation(
    *,
    role: str,
    args: argparse.Namespace,
    standing_authority: dict[str, Any] | None,
    role_state: dict[str, Any],
) -> dict[str, Any]:
    required_case = REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_BY_ROLE[role]
    command = command_string(
        [
            "scripts/monitor_ark_player_presence_passive.sh",
            "--interval",
            "10",
            "--linger-after-detect",
            "900",
            "--no-details",
            passive_target_spec(args),
        ]
    )
    return {
        "artifact": f"lifecycle-role/{role}",
        "role": role,
        "missing_kind": "lifecycle_event_role",
        "operation": "continue_or_request_passive_wait_for_missing_lifecycle_role",
        "post_reboot_monitor_context": post_reboot_monitor_context(args),
        "confirmed_beta_notice_context": confirmed_beta_notice_context(args),
        "authorized_to_run_now": False,
        **operator_authority_requirement_fields(standing_authority),
        "writes_under_evidence_dir": False,
        "writes_under_server_root": False,
        "target": target_scope(args),
        "command_status": "NOT EXECUTED",
        "command_text_not_executed": command,
        "runner_command_available": False,
        "machine_executable": False,
        "blocked_until": [
            f"copied-lifecycle-triplet/{required_case['label']}",
            *role_state.get("lifecycle_event_ambiguity_blockers", []),
        ],
        **copied_triplet_action_requirements(role_state, required_case=required_case),
        "non_evidence_context": {
            "diagnostic_only_handle_new_player_or_k2_post_login_lines_count_as_evidence": False,
            "player_presence_context_counts_as_approved_runtime_evidence": False,
            "accepted_input_only": (
                "same-run copied Obelisk.log with exact "
                "PlayerPrincipalLifecycleObserver event triplet and checked sibling set"
            ),
        },
        **false_authorization_and_evidence_flags(),
        "blocker": (
            "missing accepted copied player-principal lifecycle event triplet case: "
            f"{required_case['label']}"
        ),
        "notes": [
            "passive wait/log tail is runtime observation and still needs exact operator authority",
            "do not start TheIsland or exceed the two-server cap from this request",
            "diagnostic-only HandleNewPlayer/K2_PostLogin lines and player presence context do not satisfy the copied lifecycle triplet",
            "accepted passive lines remain non-evidence until copied sibling-set checkers accept a bundle",
        ],
    }


def not_executed_commands(operations: list[dict[str, Any]]) -> list[dict[str, str]]:
    commands: list[dict[str, str]] = []
    for operation in operations:
        artifact = str(operation.get("artifact") or operation.get("role") or "unknown")
        command = operation.get("command_text_not_executed")
        if command:
            commands.append(
                {
                    "artifact": artifact,
                    "command_kind": "primary",
                    "status": "NOT EXECUTED",
                    "command": str(command),
                }
            )
        validation = operation.get("validation_command_text_not_executed")
        if validation:
            commands.append(
                {
                    "artifact": artifact,
                    "command_kind": "validation",
                    "status": "NOT EXECUTED",
                    "command": str(validation),
                }
            )
    return commands


def machine_action_id(prefix: str, value: str) -> str:
    normalized = re.sub(r"[^a-z0-9_.:-]+", "_", value.casefold()).strip("_")
    return f"{prefix}:{normalized or 'none'}"


def closure_request_rerun_command(args: argparse.Namespace, evidence_dir: Path) -> str:
    parts = [
        "scripts/prepare_player_principal_lifecycle_evidence_closure_request.py",
        "--evidence-dir",
        str(evidence_dir),
        "--format",
        "json",
    ]
    for flag, value in (
        ("--instance", args.instance),
        ("--map", args.map_name),
        ("--query-port", args.query_port),
    ):
        if value:
            parts.extend([flag, str(value)])
    if args.expected_binary_sha256 != DEFAULT_BINARY_SHA256:
        parts.extend(["--expected-binary-sha256", args.expected_binary_sha256])
    for flag, value in (
        ("--obelisk-commit", args.obelisk_commit),
        ("--reviewed-by", args.reviewed_by),
        ("--review-note", args.review_note),
        ("--post-reboot-monitor-log", args.post_reboot_monitor_log),
        ("--confirmed-beta-notice-json", args.confirmed_beta_notice_json),
    ):
        if value:
            parts.extend([flag, str(value)])
    for flag, enabled in (
        ("--the-island-off", args.the_island_off),
        ("--two-server-cap-preserved", args.two_server_cap_preserved),
        ("--future-window-needs-players", args.future_window_needs_players),
    ):
        if enabled:
            parts.append(flag)
    if args.notice_path != NOTICE_PATH_NOT_APPLICABLE:
        parts.extend(["--notice-path", args.notice_path])
    return command_string(parts)


def approved_runtime_evidence_checker_command(evidence_dir: Path) -> str:
    return command_string(
        [
            "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
            "--json",
            str(evidence_dir / APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH),
        ]
    )


def copied_bundle_checker_acceptance_gate(
    *,
    evidence_dir: Path,
    closure_inputs_complete: bool,
    complete_sibling_set_present: bool,
    missing_expected_sibling_artifacts: list[str],
    missing_roles: list[str],
    invalid_sidecars: list[str],
    evidence_source_blockers: list[dict[str, Any]],
    sidecar_validation_blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    blockers = [
        *missing_expected_sibling_artifacts,
        *(f"lifecycle-role/{role}" for role in missing_roles),
        *invalid_sidecars,
        *(str(blocker.get("reason")) for blocker in evidence_source_blockers),
        *(str(blocker.get("reason")) for blocker in sidecar_validation_blockers),
    ]
    checker_command = approved_runtime_evidence_checker_command(evidence_dir)
    return {
        "schema": "obelisk.player-principal-lifecycle-copied-bundle-checker-acceptance-gate.v1",
        "status": (
            "checker_acceptance_required"
            if closure_inputs_complete
            else "blocked_until_complete_sibling_set_exact_triplet_and_valid_sidecars"
        ),
        "evidence_dir": str(evidence_dir),
        "manifest_relative_path": APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
        "manifest_path": str(evidence_dir / APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH),
        "complete_sibling_set_present": complete_sibling_set_present,
        "required_sibling_set": [rel for _, rel in EXPECTED_SIBLINGS],
        "missing_expected_sibling_artifacts": missing_expected_sibling_artifacts,
        "missing_lifecycle_event_roles": missing_roles,
        "invalid_sidecars": invalid_sidecars,
        "evidence_source_blockers": evidence_source_blockers,
        "sidecar_validation_blockers": sidecar_validation_blockers,
        "blockers": blockers,
        "checker_command_status": "NOT EXECUTED" if closure_inputs_complete else "NOT PROVIDED",
        "checker_command_text_not_executed": checker_command if closure_inputs_complete else None,
        "recommended_next_action": (
            "run_approved_runtime_evidence_checker_on_copied_manifest"
            if closure_inputs_complete
            else "complete_exact_sibling_set_and_lifecycle_triplet_before_checker"
        ),
        "copied_bundle_checker_acceptance_required": True,
        "copied_bundle_checker_acceptance_required_before_sdk_p0_changes": True,
        "accepted_checker_required_before_status_claim": True,
        "accepted_checker_required_before_sdk_p0_changes": True,
        "next_status_input_needed": "accepted_approved_runtime_evidence_checker_json",
        "sdk_p0_changes_blocked_until": [
            "accepted_approved_runtime_evidence_checker_json",
        ],
        "closure_request_counts_as_approved_runtime_evidence": False,
        "closure_request_counts_as_runtime_evidence": False,
        "closure_request_counts_as_sdk_evidence": False,
        "closure_request_counts_toward_sdk": False,
        "closure_request_counts_toward_p0_dependency_chain": False,
        "approved_runtime_evidence_accepted_by_checker": False,
        "copied_bundle_checker_acceptance_recorded": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "sdk_p0_changes_authorized": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "v1_completion_ready": False,
    }


def evidence_command_sequence(
    *,
    evidence_dir: Path,
    args: argparse.Namespace,
    role_state: dict[str, Any] | None = None,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    approved_bundle_dir = evidence_dir / "approved-bundle"
    copied_log = evidence_dir / "Obelisk.log"
    summary_path = approved_bundle_dir / "runtime-observer-summary.json"
    window_manifest = evidence_dir / "window-manifest.env"
    window_manifest_check = approved_bundle_dir / "player-principal-lifecycle-window-manifest.check.json"
    approved_manifest = evidence_dir / APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH
    commit = args.obelisk_commit or "<reviewed-obelisk-commit>"
    reviewed_by = args.reviewed_by or "<reviewer>"
    review_note = args.review_note or "<consume-only-review-note>"
    analyzer_command = [
        RUNTIME_OBSERVER_ANALYZER,
        "--obelisk-commit",
        commit,
        "--fail-on-quality-blockers",
        str(copied_log),
    ]
    strict_selector_command = [
        APPROVED_RUNTIME_MANIFEST_BUILDER,
        "--source-summary",
        str(summary_path),
        "--window-manifest-check",
        str(window_manifest_check),
        "--output",
        str(approved_manifest),
        "--reviewed-by",
        reviewed_by,
        "--review-note",
        review_note,
    ]
    preflight_command = [
        APPROVED_RUNTIME_EVIDENCE_BUNDLE_BUILDER,
        "--preflight-only",
        "--evidence-dir",
        str(evidence_dir),
    ]
    checker_command = [
        APPROVED_RUNTIME_EVIDENCE_CHECKER,
        "--json",
        str(approved_manifest),
    ]
    exact_triplet_ready = (
        role_state is not None
        and role_state.get("exact_copied_lifecycle_event_triplet_complete") is True
    )
    sequence_blockers = list(blockers or [])
    if role_state is not None and not exact_triplet_ready:
        sequence_blockers.extend(copied_triplet_blockers(role_state))
    commands = [
        {
            "order": 1,
            "id": "analyze_runtime_observer_log",
            "kind": "analyzer",
            "command_text_not_executed": command_string(
                analyzer_command,
                stdout_path=summary_path,
            ),
            "command_path_binding": command_path_binding(
                evidence_dir=evidence_dir,
                inputs=[
                    command_artifact_binding(
                        copied_log,
                        role="input",
                        relative_path="Obelisk.log",
                        argv_position=4,
                    )
                ],
                outputs=[
                    command_artifact_binding(
                        summary_path,
                        role="output",
                        relative_path="approved-bundle/runtime-observer-summary.json",
                        redirect_stdout=True,
                        must_exist=False,
                    )
                ],
            ),
            "command_path_hash_bound": True,
            "stdout_path": str(summary_path),
        },
        {
            "order": 2,
            "id": "strict_lifecycle_triplet_selector",
            "kind": "strict_selector",
            "command_text_not_executed": command_string(strict_selector_command),
            "command_path_binding": command_path_binding(
                evidence_dir=evidence_dir,
                inputs=[
                    command_artifact_binding(
                        summary_path,
                        role="input",
                        relative_path="approved-bundle/runtime-observer-summary.json",
                        argv_flags=("--source-summary",),
                    ),
                    command_artifact_binding(
                        window_manifest_check,
                        role="input",
                        relative_path=(
                            "approved-bundle/player-principal-lifecycle-window-manifest.check.json"
                        ),
                        argv_flags=("--window-manifest-check",),
                    ),
                ],
                outputs=[
                    command_artifact_binding(
                        approved_manifest,
                        role="output",
                        relative_path=APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
                        argv_flags=("--output",),
                        must_exist=False,
                    )
                ],
            ),
            "command_path_hash_bound": True,
            "requires_window_manifest_check": str(window_manifest_check),
            "required_triplet": "HandleNewPlayer(1,1) -> CheckJoinInProgress(1,0) -> matched OnLogout",
        },
        {
            "order": 3,
            "id": "bundle_preflight",
            "kind": "preflight",
            "command_text_not_executed": command_string(preflight_command),
            "command_path_binding": command_path_binding(
                evidence_dir=evidence_dir,
                inputs=[
                    command_artifact_binding(
                        evidence_dir,
                        role="input_dir",
                        argv_flags=("--evidence-dir",),
                    )
                ],
            ),
            "command_path_hash_bound": True,
        },
        {
            "order": 4,
            "id": "approved_runtime_evidence_checker",
            "kind": "checker",
            "command_text_not_executed": command_string(checker_command),
            "command_path_binding": command_path_binding(
                evidence_dir=evidence_dir,
                inputs=[
                    command_artifact_binding(
                        approved_manifest,
                        role="input",
                        relative_path=APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
                        argv_position=2,
                    )
                ],
            ),
            "command_path_hash_bound": True,
            "manifest": str(approved_manifest),
        },
    ]
    command_text_available = role_state is None or exact_triplet_ready
    if not command_text_available:
        commands = [
            {
                "order": order,
                "id": step_id,
                "kind": kind,
                "command_status": "NOT PROVIDED",
                "command_text_not_emitted": (
                    "exact copied lifecycle triplet must be complete before analyzer, "
                    "strict selector, preflight, or checker commands are emitted"
                ),
            }
            for order, step_id, kind in (
                (1, "analyze_runtime_observer_log", "analyzer"),
                (2, "strict_lifecycle_triplet_selector", "strict_selector"),
                (3, "bundle_preflight", "preflight"),
                (4, "approved_runtime_evidence_checker", "checker"),
            )
        ]
    return {
        "schema": EVIDENCE_COMMAND_SEQUENCE_SCHEMA,
        "status": "not_executed",
        "ordered_step_ids": [
            "analyze_runtime_observer_log",
            "strict_lifecycle_triplet_selector",
            "bundle_preflight",
            "approved_runtime_evidence_checker",
        ],
        "commands": commands,
        "command_text_available": command_text_available,
        "artifacts": {
            "copied_log": str(copied_log),
            "runtime_observer_summary": str(summary_path),
            "window_manifest": str(window_manifest),
            "window_manifest_check": str(window_manifest_check),
            "approved_runtime_manifest": str(approved_manifest),
        },
        "exact_copied_lifecycle_event_triplet_complete": exact_triplet_ready,
        "available_after_required_sibling_set": not sequence_blockers,
        "blockers": sequence_blockers,
        "restart_policy": "no_restart_unless_concrete_deploy_or_gate_change_requires_it",
        "restart_recommended": False,
        "start_or_restart_recommended": False,
        "copied_bundle_checker_acceptance_required_before_sdk_p0_changes": True,
        "accepted_checker_required_before_status_claim": True,
        "accepted_checker_required_before_sdk_p0_changes": True,
        "approved_runtime_evidence_accepted_by_checker": False,
        "copied_bundle_checker_acceptance_recorded": False,
        "sdk_p0_changes_authorized": False,
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
            "approved_runtime_evidence_accepted_by_checker": False,
            "copied_bundle_checker_acceptance_recorded": False,
            "sdk_p0_changes_authorized": False,
        },
        "non_authorization": (
            "ordered commands are offline follow-up guidance only; this report does not "
            "authorize server operations, restarts, live-log reads, Discord sends, marker/env "
            "changes, evidence acceptance, SDK progress, or readiness claims"
        ),
    }


def machine_routing_after_completion(rerun_command: str) -> dict[str, Any]:
    return {
        "next_action": "rerun_closure_request_and_status_report",
        "closure_request_command_text_not_executed": rerun_command,
        "status_input_after_rerun": "updated_closure_request_json",
    }


def machine_next_action_from_missing_operation(
    operation: dict[str, Any],
    *,
    index: int,
    run_id: str,
    evidence_dir: Path,
    target: dict[str, str | None],
    rerun_command: str,
) -> dict[str, Any]:
    artifact = str(operation.get("artifact") or operation.get("role") or f"operation-{index}")
    command = operation.get("command_text_not_executed")
    validation = operation.get("validation_command_text_not_executed")
    action_kind = str(operation.get("missing_kind", "missing_artifact"))
    action_evidence_dir = str(evidence_dir)
    if action_kind == "invalid_evidence_source" and isinstance(
        operation.get("closure_compatible_evidence_dir"),
        str,
    ):
        action_evidence_dir = str(operation["closure_compatible_evidence_dir"])
    sidecar_guidance = {
        key: operation[key]
        for key in READY_LOG_COPY_SIDECAR_GUIDANCE_KEYS
        if key in operation
    }
    post_window_contract = {
        key: operation[key]
        for key in POST_WINDOW_ACTION_CONTRACT_KEYS
        if key in operation
    }
    triplet_guidance = {
        key: operation[key]
        for key in EXACT_COPIED_TRIPLET_ACTION_GUIDANCE_KEYS
        if key in operation
    }
    return {
        "action_id": machine_action_id("closure.missing", artifact),
        "action": operation.get("operation", "complete_missing_closure_input"),
        "operation": operation.get("operation", "complete_missing_closure_input"),
        "action_kind": action_kind,
        "missing_kind": operation.get("missing_kind"),
        "source": "closure_request.exact_missing_operations",
        "source_index": index,
        "blocking": True,
        "run_id": run_id,
        "evidence_dir": action_evidence_dir,
        "source_evidence_dir": operation.get("source_evidence_dir"),
        "invalid_source_evidence_dir": operation.get("invalid_source_evidence_dir"),
        "source_root_role": operation.get("source_root_role"),
        "source_run_id": operation.get("source_run_id"),
        "source_root_valid_for_closure": operation.get("source_root_valid_for_closure"),
        "source_looks_like_passive_monitor_root": operation.get(
            "source_looks_like_passive_monitor_root"
        ),
        "closure_compatible_evidence_dir": operation.get("closure_compatible_evidence_dir"),
        "suggested_closure_evidence_dir": operation.get("suggested_closure_evidence_dir"),
        "suggested_valid_closure_run_id": operation.get("suggested_valid_closure_run_id"),
        "suggested_valid_closure_evidence_dir": operation.get(
            "suggested_valid_closure_evidence_dir"
        ),
        "suggested_valid_closure_root_role": operation.get(
            "suggested_valid_closure_root_role"
        ),
        "source_accepted_as_closure_evidence_dir": operation.get(
            "source_accepted_as_closure_evidence_dir"
        ),
        "source_becomes_closure_root": operation.get("source_becomes_closure_root"),
        "passive_monitor_root_accepted_as_closure_evidence_dir": operation.get(
            "passive_monitor_root_accepted_as_closure_evidence_dir",
            False,
        ),
        "machine_action_suggested_for_invalid_passive_root": operation.get(
            "machine_action_suggested_for_invalid_passive_root",
            True,
        ),
        "machine_executable": operation.get("machine_executable", True),
        "runner_command_available": operation.get("runner_command_available", command is not None),
        "manual_staging_required_before_machine_actions": operation.get(
            "manual_staging_required_before_machine_actions",
            False,
        ),
        "copy_or_stage_into_closure_compatible_run_required_before_closure": operation.get(
            "copy_or_stage_into_closure_compatible_run_required_before_closure",
            False,
        ),
        "explicit_execution_write_flags_required": operation.get(
            "explicit_execution_write_flags_required",
            False,
        ),
        "target": operation.get("target", target),
        "artifact": artifact,
        "role": operation.get("role"),
        "items": [artifact],
        "authorized_to_run_now": False,
        "requires_operator_authority_before_execution": operation.get(
            "requires_operator_authority_before_execution",
            operation.get("requires_current_turn_operator_approval") is True
            or operation.get("requires_bound_standing_launch_authority_receipt_before_execution") is True,
        ),
        "operator_authority_source_required": operation.get(
            "operator_authority_source_required",
            NO_OPERATOR_AUTHORITY_SOURCE,
        ),
        "requires_current_turn_operator_approval": operation.get(
            "requires_current_turn_operator_approval",
            False,
        ),
        "requires_fresh_current_turn_operator_approval": operation.get(
            "requires_fresh_current_turn_operator_approval",
            False,
        ),
        "requires_bound_standing_launch_authority_receipt_before_execution": operation.get(
            "requires_bound_standing_launch_authority_receipt_before_execution",
            False,
        ),
        "standing_launch_authority_covers_target_run": operation.get(
            "standing_launch_authority_covers_target_run",
            False,
        ),
        "writes_under_evidence_dir": operation.get("writes_under_evidence_dir", False),
        "writes_under_server_root": operation.get("writes_under_server_root", False),
        "command_status": operation.get(
            "command_status",
            "NOT EXECUTED" if command else "NOT PROVIDED",
        ),
        **({"command_text_not_executed": command} if command else {}),
        **(
            {"runner_command": operation["runner_command"]}
            if isinstance(operation.get("runner_command"), dict)
            else {}
        ),
        **(
            {"command_path_binding": operation["command_path_binding"]}
            if isinstance(operation.get("command_path_binding"), dict)
            else {}
        ),
        "command_path_hash_bound": operation.get("command_path_hash_bound") is True,
        "command_text_not_emitted": operation.get("command_text_not_emitted"),
        "validation_command_status": "NOT EXECUTED" if validation else None,
        "validation_command_text_not_executed": validation,
        **(
            {"validation_runner_command": operation["validation_runner_command"]}
            if isinstance(operation.get("validation_runner_command"), dict)
            else {}
        ),
        **(
            {"validation_command_path_binding": operation["validation_command_path_binding"]}
            if isinstance(operation.get("validation_command_path_binding"), dict)
            else {}
        ),
        "blocked_until": operation.get("blocked_until", []),
        "blocker": operation.get("blocker"),
        "notes": operation.get("notes", []),
        "post_reboot_monitor_context": operation.get("post_reboot_monitor_context"),
        "confirmed_beta_notice_context": operation.get("confirmed_beta_notice_context"),
        "non_evidence_context": operation.get("non_evidence_context"),
        "source_log_not_ready": operation.get("source_log_not_ready"),
        "observer_only_no_role_window": operation.get("observer_only_no_role_window"),
        "observer_only_no_role_window_detected": operation.get(
            "observer_only_no_role_window_detected",
            False,
        ),
        "active_observer_only_no_role_window": operation.get(
            "active_observer_only_no_role_window",
            False,
        ),
        "post_window_observer_only_no_role_window": operation.get(
            "post_window_observer_only_no_role_window",
            False,
        ),
        "observer_only_no_role_window_state": operation.get(
            "observer_only_no_role_window_state"
        ),
        "post_window_closure_action": operation.get("post_window_closure_action"),
        "active_window_not_closure_ready": operation.get(
            "active_window_not_closure_ready",
            False,
        ),
        "source_log_ready_to_copy": operation.get("source_log_ready_to_copy", False),
        "closure_compatible_copy_guidance": operation.get("closure_compatible_copy_guidance"),
        "manual_offline_next_steps": operation.get("manual_offline_next_steps", []),
        "deferred_missing_role_offline_next_steps": operation.get(
            "deferred_missing_role_offline_next_steps",
            [],
        ),
        "after_manual_staging": {
            "next_action": "rerun_closure_request_on_suggested_valid_root",
            "closure_request_command_text_not_executed": operation.get(
                "after_manual_staging_closure_request_command_text_not_executed"
            ),
        }
        if operation.get("after_manual_staging_closure_request_command_text_not_executed")
        else None,
        "after_completion": machine_routing_after_completion(
            operation.get("after_manual_staging_closure_request_command_text_not_executed")
            or rerun_command
        ),
        **post_window_contract,
        **sidecar_guidance,
        **triplet_guidance,
        **machine_false_claim_flags(),
    }


def machine_next_action_for_invalid_sidecar(
    relative_path: str,
    *,
    index: int,
    evidence_dir: Path,
    run_id: str,
    args: argparse.Namespace,
    standing_authority: dict[str, Any],
    blockers: list[dict[str, Any]],
    rerun_command: str,
) -> dict[str, Any]:
    return {
        "action_id": machine_action_id("closure.invalid_sidecar", relative_path),
        "action": "replace_invalid_sidecar_with_exact_required_artifact",
        "operation": "replace_invalid_sidecar_with_exact_required_artifact",
        "action_kind": "invalid_sidecar",
        "source": "closure_request.sidecar_validation_blockers",
        "source_index": index,
        "blocking": True,
        "run_id": run_id,
        "evidence_dir": str(evidence_dir),
        "target": target_scope(args),
        "artifact": relative_path,
        "relative_path": relative_path,
        "items": [relative_path],
        "authorized_to_run_now": False,
        **operator_authority_requirement_fields(standing_authority),
        "writes_under_evidence_dir": relative_path in EXPECTED_RELATIVE_PATHS,
        "writes_under_server_root": False,
        "command_status": "NOT PROVIDED",
        "sidecar_validation_blockers": blockers,
        "forbidden_shortcut_alias_classes": list(FORBIDDEN_SHORTCUT_ALIAS_CLASSES),
        "accepted_input_only": "exact required sidecar or approved runtime manifest bound to this run, target, copied log, and sibling set",
        "after_completion": machine_routing_after_completion(rerun_command),
        **machine_false_claim_flags(),
    }


def machine_next_action_for_notice(
    notice_action: dict[str, Any],
    *,
    index: int,
    evidence_dir: Path,
    run_id: str,
    target: dict[str, str | None],
    rerun_command: str,
) -> dict[str, Any]:
    action = str(notice_action.get("operation") or notice_action.get("required_action") or "complete_notice_action")
    authority_fields = {
        key: notice_action.get(key)
        for key in (
            "requires_operator_authority_before_execution",
            "operator_authority_source_required",
            "requires_current_turn_operator_approval",
            "requires_fresh_current_turn_operator_approval",
            "requires_bound_standing_launch_authority_receipt_before_execution",
            "standing_launch_authority_covers_target_run",
            "standing_launch_authority_satisfies_operator_approval",
            "standing_launch_authority_receipt_path",
        )
        if key in notice_action
    }
    return {
        "action_id": machine_action_id("closure.notice", action),
        "action": action,
        "operation": action,
        "action_kind": "notice_action_required",
        "source": "closure_request.required_notice_actions",
        "source_index": index,
        "blocking": True,
        "run_id": run_id,
        "evidence_dir": str(evidence_dir),
        "target": target,
        "notice_path": notice_action.get("notice_path"),
        "confirmed_beta_notice_context": notice_action.get("confirmed_beta_notice_context"),
        "notice_path_label_only": True,
        "required_before_activation": True,
        "authorized_to_run_now": False,
        "command_status": notice_action.get("command_status", "NOT EMITTED"),
        "command_text_not_emitted": notice_action.get("command_text_not_emitted", True),
        "must_be_real_notice_not_documentation": True,
        "after_completion": machine_routing_after_completion(rerun_command),
        **authority_fields,
        **machine_false_claim_flags(),
    }


def machine_next_action_for_checker(
    *,
    evidence_dir: Path,
    run_id: str,
    target: dict[str, str | None],
    role_state: dict[str, Any],
) -> dict[str, Any]:
    manifest = evidence_dir / APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH
    checker_argv = [
        "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
        "--json",
        str(manifest),
    ]
    checker_binding = command_path_binding(
        evidence_dir=evidence_dir,
        inputs=[
            command_artifact_binding(
                manifest,
                role="input",
                relative_path=APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
                argv_position=2,
            )
        ],
    )
    return {
        "action_id": "closure.checker:approved_runtime_principal_lifecycle_evidence",
        "action": "run_approved_runtime_evidence_checker_on_copied_manifest",
        "operation": "run_approved_runtime_evidence_checker_on_copied_manifest",
        "action_kind": "checker",
        "source": "closure_request.closure_inputs_complete",
        "blocking": True,
        "run_id": run_id,
        "evidence_dir": str(evidence_dir),
        "target": target,
        "artifact": APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
        "manifest_path": str(manifest),
        "items": [APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH],
        "authorized_to_run_now": False,
        **operator_authority_requirement_fields(None, requires_operator_authority=False),
        "writes_under_evidence_dir": False,
        "writes_under_server_root": False,
        "command_status": "NOT EXECUTED",
        "command_text_not_executed": command_string(checker_argv),
        "runner_command": runner_command(checker_argv),
        "runner_command_available": True,
        "machine_executable": True,
        "command_path_binding": checker_binding,
        "command_path_hash_bound": True,
        "next_status_input_needed": "accepted_approved_runtime_evidence_checker_json",
        "accepted_checker_required_before_status_claim": True,
        "accepted_checker_required_before_sdk_p0_changes": True,
        "copied_bundle_checker_acceptance_required_before_sdk_p0_changes": True,
        "recommended_before_sdk_p0_changes": True,
        "sdk_p0_changes_blocked_until": [
            "accepted_approved_runtime_evidence_checker_json",
        ],
        **copied_triplet_action_requirements(role_state),
        **machine_false_claim_flags(),
    }


def closure_machine_next_actions(
    *,
    exact_missing_operations: list[dict[str, Any]],
    invalid_sidecars: list[str],
    sidecar_validation_blockers: list[dict[str, Any]],
    notice_actions: list[dict[str, Any]],
    closure_inputs_complete: bool,
    evidence_dir: Path,
    run_id: str,
    args: argparse.Namespace,
    standing_authority: dict[str, Any],
    target: dict[str, str | None],
    role_state: dict[str, Any],
) -> list[dict[str, Any]]:
    rerun_command = closure_request_rerun_command(args, evidence_dir)
    actions: list[dict[str, Any]] = []
    pipeline_blockers: list[str] = []
    if not closure_inputs_complete:
        pipeline_blockers.extend(
            str(operation.get("artifact") or operation.get("role") or operation.get("operation"))
            for operation in exact_missing_operations
        )
        pipeline_blockers.extend(invalid_sidecars)
        pipeline_blockers.extend(
            str(action.get("operation") or action.get("required_action"))
            for action in notice_actions
        )
    invalid_source_operations = [
        operation
        for operation in exact_missing_operations
        if operation.get("missing_kind") == "invalid_evidence_source"
    ]
    remaining_missing_operations = [
        operation
        for operation in exact_missing_operations
        if operation.get("missing_kind") != "invalid_evidence_source"
    ]
    for index, operation in enumerate(invalid_source_operations):
        actions.append(
            machine_next_action_from_missing_operation(
                operation,
                index=index,
                run_id=run_id,
                evidence_dir=evidence_dir,
                target=target,
                rerun_command=rerun_command,
            )
        )
    for index, relative_path in enumerate(invalid_sidecars):
        blockers = [
            blocker
            for blocker in sidecar_validation_blockers
            if blocker.get("relative_path") == relative_path
        ]
        actions.append(
            machine_next_action_for_invalid_sidecar(
                relative_path,
                index=index,
                evidence_dir=evidence_dir,
                run_id=run_id,
                args=args,
                standing_authority=standing_authority,
                blockers=blockers,
                rerun_command=rerun_command,
            )
        )
    for index, notice_action in enumerate(notice_actions):
        actions.append(
            machine_next_action_for_notice(
                notice_action,
                index=index,
                evidence_dir=evidence_dir,
                run_id=run_id,
                target=target,
                rerun_command=rerun_command,
            )
        )
    for index, operation in enumerate(remaining_missing_operations, start=len(invalid_source_operations)):
        actions.append(
            machine_next_action_from_missing_operation(
                operation,
                index=index,
                run_id=run_id,
                evidence_dir=evidence_dir,
                target=target,
                rerun_command=rerun_command,
            )
        )
    if not actions and closure_inputs_complete:
        actions.append(
            machine_next_action_for_checker(
                evidence_dir=evidence_dir,
                run_id=run_id,
                target=target,
                role_state=role_state,
            )
        )
    pipeline = evidence_command_sequence(
        evidence_dir=evidence_dir,
        args=args,
        role_state=role_state,
        blockers=pipeline_blockers,
    )
    for action in actions:
        action["evidence_pipeline_command_sequence"] = pipeline
        action["ordered_runtime_evidence_commands"] = pipeline["commands"]
        action["authorization"] = pipeline["authorization"]
        action["evidence_boundary"] = pipeline["evidence"]
    return actions


def first_machine_next_action_summary(actions: list[dict[str, Any]]) -> dict[str, Any]:
    if not actions:
        return {
            "present": False,
            "action_id": None,
            "action": None,
            "action_kind": None,
            "artifact": None,
            "role": None,
            "command_status": "NOT PROVIDED",
            "command_text_not_executed": None,
            "command_text_not_emitted": None,
            "exact_command_available": False,
            **machine_false_claim_flags(),
        }
    first = actions[0]
    command = first.get("command_text_not_executed")
    return {
        "present": True,
        "action_id": first.get("action_id"),
        "action": first.get("action"),
        "action_kind": first.get("action_kind"),
        "artifact": first.get("artifact"),
        "role": first.get("role"),
        "command_status": first.get("command_status", "NOT PROVIDED"),
        "command_text_not_executed": command,
        "command_text_not_emitted": first.get("command_text_not_emitted"),
        "exact_command_available": isinstance(command, str) and bool(command),
        "authorized_to_run_now": False,
        **machine_false_claim_flags(),
    }


def approval_requirements(
    *,
    evidence_dir: Path,
    run_id: str,
    evidence_source_blockers: list[dict[str, Any]],
    missing_required: list[str],
    missing_sidecars: list[str],
    required_sibling_set: list[str],
    missing_expected_sibling_artifacts: list[str],
    complete_sibling_set_present: bool,
    missing_roles: list[str],
    role_state: dict[str, Any],
    sidecar_validation_blockers: list[dict[str, Any]],
    args: argparse.Namespace,
    standing_authority: dict[str, Any],
) -> dict[str, Any]:
    target = target_scope(args)
    context_notes: list[str] = []
    if args.the_island_off:
        context_notes.append("TheIsland is off; do not turn it on from this closure request.")
    if args.two_server_cap_preserved:
        context_notes.append("Two-server cap must be preserved for any separately approved operation.")
    monitor_context = post_reboot_monitor_context(args)
    beta_notice_context = confirmed_beta_notice_context(args)
    if monitor_context["path_supplied"]:
        context_notes.append(
            "Post-reboot passive monitor log path is recorded as stale-PID safety/current-monitor context only; it is not evidence or authorization."
        )
    if beta_notice_context["path_supplied"]:
        context_notes.append(
            "Confirmed beta notice JSON path is recorded as notice-action context only; it is not evidence or authorization."
        )
    notice_requirements = player_notice_requirements(args, missing_roles)
    notice_actions = required_notice_actions(notice_requirements, standing_authority=standing_authority)
    if notice_requirements["real_beta_testers_notice_action_required_before_activation"]:
        context_notes.append(
            "Future player-dependent evidence activation must complete a real beta testers notice action before activation."
        )
    standing_covers = standing_authority.get("covers_target_run") is True
    source_required = (
        APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY
        if standing_covers
        else FRESH_CURRENT_TURN_OPERATOR_MESSAGE_SOURCE
    )
    required_before = bool(
        missing_required
        or missing_expected_sibling_artifacts
        or missing_roles
        or role_state.get("missing_copied_lifecycle_event_triplet_labels")
        or evidence_source_blockers
        or sidecar_validation_blockers
        or notice_requirements["real_beta_testers_notice_action_required_before_activation"]
    )
    if standing_covers:
        context_notes.append(
            "Recorded standing launch authority is bound to this exact run/target; this closure output does not require a separate fresh current-turn approval for that same scope."
        )
    return {
        "required_before_missing_operations": required_before,
        "source_required": source_required,
        "operator_authority_source_required": source_required,
        "current_turn_operator_approval_required": required_before and not standing_covers,
        "fresh_current_turn_operator_approval_required": required_before and not standing_covers,
        "requires_bound_standing_launch_authority_receipt_before_execution": (
            required_before and standing_covers
        ),
        "standing_approval_allowed": standing_covers,
        "standing_launch_authority_covers_target_run": standing_covers,
        "standing_launch_authority_satisfies_operator_approval": standing_covers,
        "standing_launch_authority": standing_authority,
        "approval_recorded_by_this_report": False,
        "server_authorization_granted_by_this_report": False,
        "live_ops_authorization_granted_by_this_report": False,
        "runtime_capture_authorization_granted_by_this_report": False,
        "workspace_write_authorization_granted_by_this_report": False,
        "live_log_reads_authorized_by_this_report": False,
        "approved_runtime_evidence_granted_by_this_report": False,
        "passive_snapshots_count_as_evidence_by_this_report": False,
        "status_report_paths_authorize_current_turn": False,
        "discord_authorization_granted_by_this_report": False,
        "discord_sent_by_this_report": False,
        "post_reboot_monitor_context": monitor_context,
        "confirmed_beta_notice_context": beta_notice_context,
        "notice_requirements": notice_requirements,
        "required_notice_actions": notice_actions,
        "required_scope": {
            "evidence_dir": str(evidence_dir),
            "run_id": run_id,
            "target": target if any(target.values()) else None,
            "missing_artifacts": missing_required,
            "required_sibling_set": required_sibling_set,
            "missing_expected_sibling_artifacts": missing_expected_sibling_artifacts,
            "complete_sibling_set_present": complete_sibling_set_present,
            "evidence_source_blockers": evidence_source_blockers,
            "sidecar_validation_blockers": sidecar_validation_blockers,
            "required_sidecars": list(REQUIRED_SIDECARS),
            "missing_sidecars": missing_sidecars,
            "required_lifecycle_event_role_triplet": list(REQUIRED_LIFECYCLE_EVENT_ROLES),
            "required_copied_lifecycle_event_triplet": required_copied_lifecycle_event_triplet(),
            "required_copied_lifecycle_event_triplet_labels": list(
                REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS
            ),
            "missing_lifecycle_event_roles": missing_roles,
            "missing_copied_lifecycle_event_triplet": role_state.get(
                "missing_copied_lifecycle_event_triplet", []
            ),
            "missing_copied_lifecycle_event_triplet_labels": role_state.get(
                "missing_copied_lifecycle_event_triplet_labels", []
            ),
            "partial_start_end_present": role_state.get("partial_start_end_present", False),
            "missing_strict_rejected_start": role_state.get("missing_strict_rejected_start", True),
            "strict_rejected_start_expected_shape": STRICT_REJECTED_START_EXPECTED_SHAPE,
            "strict_rejected_start_observed_shape": role_state.get(
                "strict_rejected_start_observed_shape"
            ),
            "strict_rejected_start_observed_shape_counts_as_approved_runtime_evidence": False,
            "exact_copied_lifecycle_event_triplet_required_before_actionable": True,
            "operator_authority_source_required": source_required,
            "current_turn_operator_approval_required": required_before and not standing_covers,
            "fresh_current_turn_operator_approval_required": required_before and not standing_covers,
            "requires_bound_standing_launch_authority_receipt_before_execution": (
                required_before and standing_covers
            ),
            "standing_launch_authority_covers_target_run": standing_covers,
            "standing_launch_authority_satisfies_operator_approval": standing_covers,
            "must_name_exact_missing_file_writes": True,
            "must_name_exact_target": True,
            "must_bind_missing_roles_when_runtime_observation_is_requested": True,
            "must_preserve_the_island_off_when_supplied": bool(args.the_island_off),
            "must_preserve_two_server_cap": True,
            "two_server_cap_max_running_servers": 2,
            "must_preserve_two_server_cap_when_supplied": bool(args.two_server_cap_preserved),
            "provided_operational_constraints": provided_operational_constraints(args),
            "must_preserve_supplied_operational_constraints": bool(provided_operational_constraints(args)),
            "notice_requirements": notice_requirements,
            "required_notice_actions": notice_actions,
            "post_reboot_monitor_context": monitor_context,
            "confirmed_beta_notice_context": beta_notice_context,
            "must_not_claim_readiness": True,
            "context_notes": context_notes,
        },
    }


def closure_case_id(
    *,
    args: argparse.Namespace,
    missing_required: list[str],
    missing_roles: list[str],
    evidence_source_blockers: list[dict[str, Any]],
    sidecar_validation_blockers: list[dict[str, Any]],
    closure_inputs_complete: bool,
) -> str:
    if evidence_source_blockers:
        if any(blocker["reason"] == "evidence_dir_parent_not_live_validation_logs" for blocker in evidence_source_blockers):
            return "non_live_validation_source_directory"
        return "invalid_evidence_run_id"
    if args.map_name == "TheIsland" and args.the_island_off and missing_required:
        return "historical_theisland_missing_sidecars"
    if args.map_name == "Genesis2" and missing_roles:
        return "active_genesis2_triplet_incomplete"
    if missing_required and missing_roles:
        return "missing_sidecars_and_lifecycle_roles"
    if missing_required:
        return "missing_sidecars"
    if missing_roles:
        return "missing_lifecycle_roles"
    if sidecar_validation_blockers:
        return "invalid_or_incomplete_sidecars"
    if closure_inputs_complete:
        return "closure_inputs_complete_no_readiness"
    return "closure_inputs_incomplete"


def report_status(
    *,
    closure_inputs_complete: bool,
    missing_required: list[str],
    missing_roles: list[str],
    evidence_source_blockers: list[dict[str, Any]],
    sidecar_validation_blockers: list[dict[str, Any]],
) -> str:
    if closure_inputs_complete:
        return "closure_inputs_complete_bundle_checker_required"
    if evidence_source_blockers:
        return "non_ready_invalid_evidence_source"
    if missing_required and missing_roles:
        return "non_ready_missing_required_artifacts_and_lifecycle_roles"
    if missing_roles:
        return "non_ready_missing_lifecycle_roles"
    if sidecar_validation_blockers:
        return "non_ready_invalid_sidecars"
    return "non_ready_missing_required_artifacts"


def closure_acceptance_state(
    *,
    closure_inputs_complete: bool,
    ready_log_copy_report: dict[str, Any],
    missing_required: list[str],
    missing_roles: list[str],
    sidecar_validation_blockers: list[dict[str, Any]],
    evidence_source_blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    expired_no_evidence = ready_log_copy_post_window_no_triplet(ready_log_copy_report)
    active_wait = ready_log_copy_active_no_triplet(ready_log_copy_report)
    if expired_no_evidence:
        classification = "expired_observer_only_window_closed_as_non_evidence"
    elif active_wait:
        classification = "active_observer_only_window_waiting_for_exact_triplet"
    elif closure_inputs_complete:
        classification = "accepted_ready_for_checker_not_approved_evidence"
    else:
        classification = "not_ready_missing_inputs_or_invalid_sidecars"
    return {
        "schema": "obelisk.player-principal-lifecycle-closure-acceptance-state.v1",
        "classification": classification,
        "expired_no_evidence": expired_no_evidence,
        "active_window_waiting_not_ready": active_wait,
        "accepted_ready": False,
        "accepted_ready_for_checker": closure_inputs_complete and not expired_no_evidence,
        "checker_accepted_ready": False,
        "approved_runtime_evidence_accepted_by_checker": False,
        "closure_inputs_complete": closure_inputs_complete,
        "missing_required_artifacts": missing_required,
        "missing_lifecycle_event_roles": missing_roles,
        "sidecar_validation_blockers": sidecar_validation_blockers,
        "evidence_source_blockers": evidence_source_blockers,
        "ready_log_copy_report_classification": ready_log_copy_report.get("classification"),
        "ready_log_copy_observer_only_window_state": ready_log_copy_report.get(
            "observer_only_no_role_window_state"
        ),
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "v1_completion_ready": False,
        "sdk_progress": 0,
        "p0_progress": 0,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    evidence_dir, input_blockers = resolve_evidence_dir(args.evidence_dir)
    run_id = evidence_dir.name
    source_state = evidence_source_state(evidence_dir)
    evidence_source_blockers = list(source_state["blockers"])
    inspect_siblings = not input_blockers
    evidence_dir_exists = inspect_siblings and evidence_dir.is_dir()
    sibling_states = [
        sibling_state(evidence_dir, label, rel, inspect=inspect_siblings)
        for label, rel in EXPECTED_SIBLINGS
    ]
    present_siblings = [state["relative_path"] for state in sibling_states if state["present"]]
    raw_missing_siblings = [state["relative_path"] for state in sibling_states if not state["present"]]
    required_sibling_set = [rel for _, rel in EXPECTED_SIBLINGS]
    complete_sibling_set_present = evidence_dir_exists and not raw_missing_siblings
    missing_expected_sibling_artifacts = list(raw_missing_siblings)
    missing_required = [
        *[rel for rel in REQUIRED_CLOSURE_ARTIFACTS if rel in raw_missing_siblings],
        *[
            rel
            for rel in REQUIRED_SIDECARS
            if rel in raw_missing_siblings and rel not in REQUIRED_CLOSURE_ARTIFACTS
        ],
    ]
    missing_siblings = [
        *missing_required,
        *(rel for rel in raw_missing_siblings if rel not in missing_required),
    ]
    exact_missing_sidecars = [rel for rel in missing_siblings if rel in REQUIRED_SIDECARS]
    role_state = lifecycle_event_role_state(evidence_dir, inspect=inspect_siblings and evidence_dir_exists)
    ready_log_copy_report = ready_log_copy_report_context(
        evidence_dir,
        inspect=inspect_siblings and evidence_dir_exists,
    )
    sidecar_validation_states, sidecar_validation_blockers, invalid_sidecars = validate_sidecar_contents(
        evidence_dir,
        sibling_states,
        inspect=inspect_siblings and evidence_dir_exists,
        args=args,
    )
    standing_authority = standing_launch_authority_receipt_state(evidence_dir, run_id=run_id, args=args)
    artifact_checklist = closure_artifact_checklist(
        evidence_dir,
        sibling_states,
        sidecar_validation_states,
    )
    artifact_bindings = artifact_binding_report(evidence_dir, sibling_states)
    missing_roles = list(role_state["missing_roles"])
    missing_triplet_cases = list(role_state["missing_copied_lifecycle_event_triplet"])
    missing_triplet_labels = list(role_state["missing_copied_lifecycle_event_triplet_labels"])
    lifecycle_triplet_complete = bool(role_state["exact_copied_lifecycle_event_triplet_complete"])
    closure_inputs_complete = (
        complete_sibling_set_present
        and not missing_required
        and not missing_roles
        and not sidecar_validation_blockers
        and not input_blockers
        and not evidence_source_blockers
        and evidence_dir_exists
        and lifecycle_triplet_complete
    )
    exact_missing_operations: list[dict[str, Any]] = []
    source_valid_for_followup_operations = not evidence_source_blockers and not input_blockers
    ready_log_copy_no_triplet_wait_or_close = ready_log_copy_active_or_post_window_no_triplet(
        ready_log_copy_report
    )
    if source_valid_for_followup_operations:
        if not ready_log_copy_no_triplet_wait_or_close:
            exact_missing_operations.extend(
                missing_role_operation(
                    role=role,
                    args=args,
                    standing_authority=standing_authority,
                    role_state=role_state,
                )
                for role in missing_roles
            )
        if "Obelisk.log" in raw_missing_siblings:
            exact_missing_operations.append(
                missing_copied_log_operation(
                    evidence_dir=evidence_dir,
                    args=args,
                    standing_authority=standing_authority,
                    ready_log_copy_report=ready_log_copy_report,
                ),
            )
        exact_missing_operations.extend(
            missing_operation(
                relative_path=rel,
                evidence_dir=evidence_dir,
                run_id=run_id,
                args=args,
                standing_authority=standing_authority,
                role_state=role_state,
            )
            for rel in missing_required
        )
    approval = approval_requirements(
        evidence_dir=evidence_dir,
        run_id=run_id,
        evidence_source_blockers=evidence_source_blockers,
        missing_required=missing_required,
        missing_sidecars=exact_missing_sidecars,
        required_sibling_set=required_sibling_set,
        missing_expected_sibling_artifacts=missing_expected_sibling_artifacts,
        complete_sibling_set_present=complete_sibling_set_present,
        missing_roles=missing_roles,
        role_state=role_state,
        sidecar_validation_blockers=sidecar_validation_blockers,
        args=args,
        standing_authority=standing_authority,
    )
    if input_blockers:
        exact_missing_operations.insert(
            0,
            {
                "artifact": str(evidence_dir),
                "operation": "copy_or_select_an_offline_evidence_directory",
                "authorized_to_run_now": False,
                "requires_current_turn_operator_approval": False,
                "writes_under_evidence_dir": False,
                **false_authorization_and_evidence_flags(),
                "blockers": input_blockers,
            },
        )
    elif evidence_source_blockers:
        exact_missing_operations.insert(
            0,
            invalid_evidence_source_operation(
                evidence_dir=evidence_dir,
                args=args,
                standing_authority=standing_authority,
                evidence_source_blockers=evidence_source_blockers,
                missing_required=missing_required,
                missing_sidecars=exact_missing_sidecars,
                role_state=role_state,
            ),
        )
    if not input_blockers and not evidence_dir_exists:
        exact_missing_operations.insert(
            0,
            {
                "artifact": str(evidence_dir),
                "operation": "provide_existing_evidence_directory",
                "authorized_to_run_now": False,
                "requires_current_turn_operator_approval": False,
                "writes_under_evidence_dir": False,
                **false_authorization_and_evidence_flags(),
                "blocker": "evidence directory does not exist",
            },
        )
    commands = not_executed_commands(exact_missing_operations)
    target = target_scope(args)
    case_id = closure_case_id(
        args=args,
        missing_required=missing_required,
        missing_roles=missing_roles,
        evidence_source_blockers=evidence_source_blockers,
        sidecar_validation_blockers=sidecar_validation_blockers,
        closure_inputs_complete=closure_inputs_complete,
    )
    notice_requirements = approval["notice_requirements"]
    notice_actions = approval["required_notice_actions"]
    constraints = provided_operational_constraints(args)
    monitor_context = approval["post_reboot_monitor_context"]
    beta_notice_context = approval["confirmed_beta_notice_context"]
    machine_actions = closure_machine_next_actions(
        exact_missing_operations=exact_missing_operations,
        invalid_sidecars=invalid_sidecars,
        sidecar_validation_blockers=sidecar_validation_blockers,
        notice_actions=notice_actions,
        closure_inputs_complete=closure_inputs_complete,
        evidence_dir=evidence_dir,
        run_id=run_id,
        args=args,
        standing_authority=standing_authority,
        target=target,
        role_state=role_state,
    )
    first_machine_action = first_machine_next_action_summary(machine_actions)
    pipeline_blockers = [
        *missing_required,
        *(f"lifecycle-role/{role}" for role in missing_roles),
        *(str(blocker.get("reason")) for blocker in evidence_source_blockers),
        *invalid_sidecars,
        *(str(blocker.get("reason")) for blocker in sidecar_validation_blockers),
        *(str(action.get("operation")) for action in notice_actions),
    ]
    pipeline = evidence_command_sequence(
        evidence_dir=evidence_dir,
        args=args,
        role_state=role_state,
        blockers=pipeline_blockers,
    )
    checker_acceptance_gate = copied_bundle_checker_acceptance_gate(
        evidence_dir=evidence_dir,
        closure_inputs_complete=closure_inputs_complete,
        complete_sibling_set_present=complete_sibling_set_present,
        missing_expected_sibling_artifacts=missing_expected_sibling_artifacts,
        missing_roles=missing_roles,
        invalid_sidecars=invalid_sidecars,
        evidence_source_blockers=evidence_source_blockers,
        sidecar_validation_blockers=sidecar_validation_blockers,
    )
    acceptance_state = closure_acceptance_state(
        closure_inputs_complete=closure_inputs_complete,
        ready_log_copy_report=ready_log_copy_report,
        missing_required=missing_required,
        missing_roles=missing_roles,
        sidecar_validation_blockers=sidecar_validation_blockers,
        evidence_source_blockers=evidence_source_blockers,
    )
    return {
        "schema": SCHEMA,
        "status": report_status(
            closure_inputs_complete=closure_inputs_complete,
            missing_required=missing_required,
            missing_roles=missing_roles,
            evidence_source_blockers=evidence_source_blockers,
            sidecar_validation_blockers=sidecar_validation_blockers,
        ),
        "case_id": case_id,
        "closure_case": case_id,
        "target": target,
        "ready": False,
        "closure_request_ready": False,
        "ready_scope": "not_ready_closure_request_is_non_evidence_checker_required_before_any_readiness_claim",
        "closure_request_success_scope": "input_completeness_only_checker_acceptance_still_required",
        "closure_acceptance_state": acceptance_state,
        "runtime_evidence_acceptance_state": acceptance_state,
        "evidence_closure_inputs_complete": closure_inputs_complete,
        "closure_inputs_complete_but_checker_required": closure_inputs_complete,
        "complete_sibling_set_present": complete_sibling_set_present,
        "evidence_dir": str(evidence_dir),
        "evidence_dir_exists": evidence_dir_exists,
        "approved_bundle_manifest_relative_path": APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
        "approved_bundle_path": str(evidence_dir / APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH),
        "approved_bundle_path_checklist": artifact_checklist,
        "artifact_hash_path_bindings": artifact_bindings,
        "copied_log_hash_path_binding": artifact_bindings["copied_log"],
        "required_sidecar_hash_path_bindings": artifact_bindings["required_sidecars"],
        "bundle_input_artifact_hash_path_bindings": artifact_bindings["bundle_input_artifacts"],
        "copied_log_hash_path_bound": artifact_bindings["copied_log_hash_path_bound"],
        "required_sidecars_hash_path_bound": artifact_bindings[
            "required_sidecars_hash_path_bound"
        ],
        "bundle_input_artifacts_hash_path_bound": artifact_bindings[
            "bundle_input_artifacts_hash_path_bound"
        ],
        "complete_sibling_set_hash_path_bound": artifact_bindings[
            "complete_sibling_set_hash_path_bound"
        ],
        "artifact_hash_path_bindings_count_as_approved_runtime_evidence": False,
        "run_id": run_id,
        "run_id_valid": source_state["run_id_valid"],
        "evidence_dir_parent": source_state["parent"],
        "evidence_dir_expected_parent": source_state["expected_parent"],
        "evidence_dir_parent_valid": source_state["parent_valid"],
        "evidence_source_state": source_state,
        "evidence_source_blockers": evidence_source_blockers,
        "source_material_counts_as_approved_runtime_evidence": False,
        "source_material_counts_as_runtime_evidence": False,
        "source_material_counts_as_sdk_evidence": False,
        "ready_log_copy_report": ready_log_copy_report,
        "ready_log_copy_report_present": ready_log_copy_report["present"],
        "blocked_ready_log_copy_report": (
            ready_log_copy_report["present"] and ready_log_copy_report["ready_to_copy"] is not True
        ),
        "ready_log_copy_report_counts_as_approved_runtime_evidence": False,
        "json_output_report_counts_as_approved_runtime_evidence": False,
        "present_siblings": present_siblings,
        "required_sibling_set": required_sibling_set,
        "missing_expected_sibling_artifacts": missing_expected_sibling_artifacts,
        "required_sidecars": list(REQUIRED_SIDECARS),
        "exact_missing_sidecars": exact_missing_sidecars,
        "missing_siblings": missing_siblings,
        "missing_required_artifacts": missing_required,
        "required_lifecycle_event_role_triplet": list(REQUIRED_LIFECYCLE_EVENT_ROLES),
        "required_copied_lifecycle_event_triplet": required_copied_lifecycle_event_triplet(),
        "required_copied_lifecycle_event_triplet_labels": list(
            REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS
        ),
        "lifecycle_event_role_state": role_state,
        "lifecycle_event_triplet_complete": lifecycle_triplet_complete,
        "exact_copied_lifecycle_event_triplet_complete": lifecycle_triplet_complete,
        "partial_start_end_present": role_state["partial_start_end_present"],
        "missing_strict_rejected_start": role_state["missing_strict_rejected_start"],
        "strict_rejected_start_expected_shape": STRICT_REJECTED_START_EXPECTED_SHAPE,
        "strict_rejected_start_observed_shape": role_state["strict_rejected_start_observed_shape"],
        "strict_rejected_start_observed_shape_counts_as_approved_runtime_evidence": False,
        "missing_lifecycle_event_roles": missing_roles,
        "missing_copied_lifecycle_event_triplet": missing_triplet_cases,
        "missing_copied_lifecycle_event_triplet_labels": missing_triplet_labels,
        "missing_artifacts_and_roles": {
            "missing_required_artifacts": missing_required,
            "required_sibling_set": required_sibling_set,
            "complete_sibling_set_present": complete_sibling_set_present,
            "missing_expected_sibling_artifacts": missing_expected_sibling_artifacts,
            "required_sidecars": list(REQUIRED_SIDECARS),
            "exact_missing_sidecars": exact_missing_sidecars,
            "required_lifecycle_event_role_triplet": list(REQUIRED_LIFECYCLE_EVENT_ROLES),
            "required_copied_lifecycle_event_triplet": required_copied_lifecycle_event_triplet(),
            "required_copied_lifecycle_event_triplet_labels": list(
                REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS
            ),
            "missing_siblings": missing_siblings,
            "missing_lifecycle_event_roles": missing_roles,
            "missing_copied_lifecycle_event_triplet": missing_triplet_cases,
            "missing_copied_lifecycle_event_triplet_labels": missing_triplet_labels,
            "partial_start_end_present": role_state["partial_start_end_present"],
            "missing_strict_rejected_start": role_state["missing_strict_rejected_start"],
            "strict_rejected_start_expected_shape": STRICT_REJECTED_START_EXPECTED_SHAPE,
            "strict_rejected_start_observed_shape": role_state["strict_rejected_start_observed_shape"],
            "strict_rejected_start_observed_shape_counts_as_approved_runtime_evidence": False,
            "ready_log_copy_report": ready_log_copy_report,
            "ready_log_copy_report_counts_as_approved_runtime_evidence": False,
            "evidence_source_blockers": evidence_source_blockers,
            "invalid_sidecars": invalid_sidecars,
            "sidecar_validation_blockers": sidecar_validation_blockers,
        },
        "closure_requirements": {
            "required_sibling_set": required_sibling_set,
            "complete_sibling_set_present": complete_sibling_set_present,
            "missing_expected_sibling_artifacts": missing_expected_sibling_artifacts,
            "required_sidecars": list(REQUIRED_SIDECARS),
            "exact_missing_sidecars": exact_missing_sidecars,
            "required_closure_artifacts": list(REQUIRED_CLOSURE_ARTIFACTS),
            "approved_bundle_manifest_relative_path": APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH,
            "approved_bundle_path": str(evidence_dir / APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH),
            "missing_required_artifacts": missing_required,
            "required_lifecycle_event_role_triplet": list(REQUIRED_LIFECYCLE_EVENT_ROLES),
            "required_copied_lifecycle_event_triplet": required_copied_lifecycle_event_triplet(),
            "required_copied_lifecycle_event_triplet_labels": list(
                REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS
            ),
            "missing_lifecycle_event_roles": missing_roles,
            "missing_copied_lifecycle_event_triplet": missing_triplet_cases,
            "missing_copied_lifecycle_event_triplet_labels": missing_triplet_labels,
            "lifecycle_event_triplet_complete": lifecycle_triplet_complete,
            "exact_copied_lifecycle_event_triplet_complete": lifecycle_triplet_complete,
            "partial_start_end_present": role_state["partial_start_end_present"],
            "missing_strict_rejected_start": role_state["missing_strict_rejected_start"],
            "strict_rejected_start_expected_shape": STRICT_REJECTED_START_EXPECTED_SHAPE,
            "strict_rejected_start_observed_shape": role_state["strict_rejected_start_observed_shape"],
            "strict_rejected_start_observed_shape_counts_as_approved_runtime_evidence": False,
            "ready_log_copy_report": ready_log_copy_report,
            "ready_log_copy_report_counts_as_approved_runtime_evidence": False,
            "evidence_source_blockers": evidence_source_blockers,
            "invalid_sidecars": invalid_sidecars,
            "sidecar_validation_blockers": sidecar_validation_blockers,
        },
        "post_window_copy_bundle_preconditions": post_window_copy_bundle_preconditions(
            evidence_dir=evidence_dir,
            artifact="post_window_closure",
            operation="copy_sidecars_build_bundle_and_run_checker",
            blocked_until=[
                "Obelisk.log",
                *[
                    rel
                    for rel in REQUIRED_SIDECARS
                    if rel != APPROVED_RUNTIME_MANIFEST_RELATIVE_PATH
                ],
            ],
            sidecar_generation_required=True,
        ),
        "closure_artifact_checklist": artifact_checklist,
        "sibling_state": sibling_states,
        "sidecar_validation_state": sidecar_validation_states,
        "invalid_sidecars": invalid_sidecars,
        "sidecar_validation_blockers": sidecar_validation_blockers,
        "machine_next_actions_schema": MACHINE_NEXT_ACTIONS_SCHEMA,
        "machine_next_actions": machine_actions,
        "machine_next_action_ids": [action["action_id"] for action in machine_actions],
        "first_machine_next_action": first_machine_action,
        "exact_next_command": first_machine_action,
        "evidence_pipeline_command_sequence": pipeline,
        "ordered_runtime_evidence_commands": pipeline["commands"],
        "copied_bundle_checker_acceptance_gate": checker_acceptance_gate,
        "approved_runtime_evidence_checker_acceptance_gate": checker_acceptance_gate,
        "copied_bundle_checker_acceptance_required_before_sdk_p0_changes": True,
        "accepted_checker_required_before_sdk_p0_changes": True,
        "sdk_p0_changes_blocked_until": [
            "accepted_approved_runtime_evidence_checker_json",
        ],
        "sdk_p0_changes_authorized": False,
        "authorization_evidence_boundary": {
            "authorization": pipeline["authorization"],
            "evidence": pipeline["evidence"],
            "authorization_is_not_evidence": True,
            "evidence_requires_checker_acceptance": True,
            "copied_bundle_checker_acceptance_required_before_sdk_p0_changes": True,
            "accepted_checker_required_before_sdk_p0_changes": True,
            "approved_runtime_evidence_accepted_by_checker": False,
            "copied_bundle_checker_acceptance_recorded": False,
            "sdk_p0_changes_authorized": False,
            "counts_as_approved_runtime_evidence": False,
        },
        "exact_missing_operations": exact_missing_operations,
        "not_executed_commands": commands,
        "current_turn_approval_requirements": approval,
        "operator_authority_requirements": approval,
        "standing_launch_authority": standing_authority,
        "standing_launch_authority_covers_target_run": standing_authority["covers_target_run"],
        "player_notice_requirements": notice_requirements,
        "required_notice_actions": notice_actions,
        "operational_context": {
            "target": target,
            "the_island_off_supplied": bool(args.the_island_off),
            "the_island_off": True if args.the_island_off else None,
            "the_island_must_remain_off_without_current_turn_approval": True,
            "the_island_start_authorized_by_this_report": False,
            "two_server_cap_preserved_supplied": bool(args.two_server_cap_preserved),
            "two_server_cap_preserved": True if args.two_server_cap_preserved else None,
            "two_server_cap_required": True,
            "two_server_cap_max_running_servers": 2,
            "server_concurrency_change_authorized_by_this_report": False,
            "provided_operational_constraints": constraints,
            "must_preserve_supplied_operational_constraints": bool(constraints),
            "post_reboot_monitor_context": monitor_context,
            "confirmed_beta_notice_context": beta_notice_context,
            "context_notes": approval["required_scope"]["context_notes"],
        },
        "authorization": dict(NO_AUTHORIZATION_FLAGS),
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "workspace_writes_authorized": False,
        **false_authorization_and_evidence_flags(),
        "no_server_authorization": "this report does not authorize server operations or writes under /servidor/ark",
        "no_readiness_claim": True,
        "readiness_claims": {
            "public_readiness_claim": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "runtime_evidence_present": False,
            "runtime_evidence_ready": False,
            "approved_runtime_evidence": False,
            "approved_runtime_evidence_present": False,
            "approved_runtime_evidence_ready": False,
            "counts_as_approved_runtime_evidence": False,
            "passive_snapshots_as_evidence": False,
            "counts_toward_sdk": False,
            "counts_toward_v1": False,
            "promotion_ready": False,
            "v1_completion_ready": False,
            "stable_claim_allowed": False,
        },
        "non_claims": list(NON_CLAIMS),
        "input_blockers": input_blockers,
    }


def markdown_report(report: dict[str, Any]) -> str:
    approval = report["current_turn_approval_requirements"]
    required_scope = approval["required_scope"]
    context = report["operational_context"]
    role_state = report["lifecycle_event_role_state"]
    copy_report = report["ready_log_copy_report"]
    notice = report["player_notice_requirements"]
    monitor_context = context["post_reboot_monitor_context"]
    beta_notice_context = context["confirmed_beta_notice_context"]
    strict_rejected_start_observed = role_state["strict_rejected_start_observed_shape"]
    strict_rejected_start_observed_shape = (
        strict_rejected_start_observed.get("shape")
        if isinstance(strict_rejected_start_observed, dict)
        else None
    )

    def markdown_scalar(value: Any) -> str:
        if isinstance(value, bool):
            return str(value).lower()
        if value is None:
            return "not_supplied"
        return str(value)

    def markdown_list(items: list[str]) -> list[str]:
        if not items:
            return ["- none"]
        return [f"- {item}" for item in items]

    target = required_scope["target"] or {}
    authority_heading = (
        "## Operator Authority Requirements"
        if approval["standing_launch_authority_covers_target_run"]
        else "## Current-Turn Approval Requirements"
    )
    lines = [
        "# Player Principal Lifecycle Evidence Closure Request",
        "",
        f"status={report['status']}",
        f"closure_case={report['closure_case']}",
        f"ready={str(report['ready']).lower()}",
        f"closure_request_ready={str(report['closure_request_ready']).lower()}",
        f"ready_scope={report['ready_scope']}",
        f"evidence_closure_inputs_complete={str(report['evidence_closure_inputs_complete']).lower()}",
        f"closure_inputs_complete_but_checker_required={str(report['closure_inputs_complete_but_checker_required']).lower()}",
        f"complete_sibling_set_present={str(report['complete_sibling_set_present']).lower()}",
        f"copied_bundle_checker_acceptance_required_before_sdk_p0_changes={str(report['copied_bundle_checker_acceptance_required_before_sdk_p0_changes']).lower()}",
        f"accepted_checker_required_before_sdk_p0_changes={str(report['accepted_checker_required_before_sdk_p0_changes']).lower()}",
        f"sdk_p0_changes_authorized={str(report['sdk_p0_changes_authorized']).lower()}",
        f"evidence_dir={report['evidence_dir']}",
        f"run_id={report['run_id']}",
        f"run_id_valid={str(report['run_id_valid']).lower()}",
        f"evidence_dir_parent={report['evidence_dir_parent']}",
        f"evidence_dir_expected_parent={report['evidence_dir_expected_parent']}",
        f"evidence_dir_parent_valid={str(report['evidence_dir_parent_valid']).lower()}",
        f"source_material_counts_as_approved_runtime_evidence={str(report['source_material_counts_as_approved_runtime_evidence']).lower()}",
        f"source_material_counts_as_runtime_evidence={str(report['source_material_counts_as_runtime_evidence']).lower()}",
        f"source_material_counts_as_sdk_evidence={str(report['source_material_counts_as_sdk_evidence']).lower()}",
        f"server_operations_authorized={str(report['server_operations_authorized']).lower()}",
        f"runtime_work_authorized={str(report['runtime_work_authorized']).lower()}",
        f"workspace_writes_authorized={str(report['workspace_writes_authorized']).lower()}",
        f"live_ops_authorized={str(report['live_ops_authorized']).lower()}",
        f"runtime_capture_authorized={str(report['runtime_capture_authorized']).lower()}",
        f"reads_live_logs={str(report['reads_live_logs']).lower()}",
        f"discord_authorized={str(report['discord_authorized']).lower()}",
        f"discord_sent_by_this_report={str(report['discord_sent_by_this_report']).lower()}",
        f"discord_command_emitted_by_this_report={str(report['discord_command_emitted_by_this_report']).lower()}",
        f"approved_runtime_evidence={str(report['approved_runtime_evidence']).lower()}",
        f"approved_runtime_evidence_present={str(report['approved_runtime_evidence_present']).lower()}",
        f"counts_as_approved_runtime_evidence={str(report['counts_as_approved_runtime_evidence']).lower()}",
        f"passive_snapshots_as_evidence={str(report['passive_snapshots_as_evidence']).lower()}",
        f"counts_toward_sdk={str(report['counts_toward_sdk']).lower()}",
        f"counts_toward_v1={str(report['counts_toward_v1']).lower()}",
        f"status_report_paths_authorize_current_turn={str(report['status_report_paths_authorize_current_turn']).lower()}",
        f"no_server_authorization={report['no_server_authorization']}",
        "no_readiness_claim=true",
        "does_not_claim_public_runtime_v1_readiness=true",
        "no_public_runtime_v1_readiness=does not claim public/runtime/v1 readiness",
        "public_abi_ready=false",
        "public_sdk_ready=false",
        "runtime_ready=false",
        "v1_completion_ready=false",
        "approved_runtime_evidence_ready=false",
        "promotion_ready=false",
        "stable_claim_allowed=false",
        "",
        "## No Server Authorization",
        "",
        "- This request does not authorize server operations.",
        "- This request does not authorize writes under /servidor/ark.",
        "- This request does not authorize marker/env changes, starts, restarts, or stops.",
        "- This request does not send Discord notices or authorize Discord delivery.",
        "",
        "## Operational Context",
        "",
        f"target_instance={context['target']['instance']}",
        f"target_map={context['target']['map']}",
        f"target_query_port={markdown_scalar(context['target']['query_port'])}",
        f"target_key={markdown_scalar(context['target']['target_key'])}",
        f"the_island_off_supplied={str(context['the_island_off_supplied']).lower()}",
        f"the_island_off={markdown_scalar(context['the_island_off'])}",
        f"the_island_must_remain_off_without_current_turn_approval={str(context['the_island_must_remain_off_without_current_turn_approval']).lower()}",
        f"the_island_start_authorized_by_this_report={str(context['the_island_start_authorized_by_this_report']).lower()}",
        f"two_server_cap_preserved_supplied={str(context['two_server_cap_preserved_supplied']).lower()}",
        f"two_server_cap_preserved={markdown_scalar(context['two_server_cap_preserved'])}",
        f"two_server_cap_required={str(context['two_server_cap_required']).lower()}",
        f"two_server_cap_max_running_servers={context['two_server_cap_max_running_servers']}",
        f"server_concurrency_change_authorized_by_this_report={str(context['server_concurrency_change_authorized_by_this_report']).lower()}",
        f"post_reboot_monitor_log_path={markdown_scalar(monitor_context['path'])}",
        f"post_reboot_monitor_log_path_supplied={str(monitor_context['path_supplied']).lower()}",
        f"post_reboot_monitor_stale_pid_safety_context_recorded={str(monitor_context['stale_pid_safety_context_recorded']).lower()}",
        f"post_reboot_monitor_current_passive_monitor_context_recorded={str(monitor_context['current_passive_monitor_context_recorded']).lower()}",
        f"post_reboot_monitor_read_by_this_report={str(monitor_context['read_by_this_report']).lower()}",
        f"post_reboot_monitor_counts_as_approved_runtime_evidence={str(monitor_context['counts_as_approved_runtime_evidence']).lower()}",
        f"post_reboot_monitor_counts_toward_sdk={str(monitor_context['counts_toward_sdk']).lower()}",
        f"post_reboot_monitor_counts_toward_p0_dependency_chain_claim_now={str(monitor_context['counts_toward_p0_dependency_chain_claim_now']).lower()}",
        f"confirmed_beta_notice_json_path={markdown_scalar(beta_notice_context['path'])}",
        f"confirmed_beta_notice_json_path_supplied={str(beta_notice_context['path_supplied']).lower()}",
        f"confirmed_beta_notice_read_by_this_report={str(beta_notice_context['read_by_this_report']).lower()}",
        f"confirmed_beta_notice_notice_completion_accepted_by_this_report={str(beta_notice_context['notice_completion_accepted_by_this_report']).lower()}",
        f"confirmed_beta_notice_counts_as_approved_runtime_evidence={str(beta_notice_context['counts_as_approved_runtime_evidence']).lower()}",
        f"confirmed_beta_notice_counts_toward_sdk={str(beta_notice_context['counts_toward_sdk']).lower()}",
        f"confirmed_beta_notice_counts_toward_p0_dependency_chain_claim_now={str(beta_notice_context['counts_toward_p0_dependency_chain_claim_now']).lower()}",
        *(f"context_note={note}" for note in context["context_notes"]),
        "",
        "## Evidence Source Blockers",
        "",
    ]
    if report["evidence_source_blockers"]:
        for blocker in report["evidence_source_blockers"]:
            lines.extend(
                [
                    f"- reason={blocker['reason']}",
                    f"  path={blocker['path']}",
                    f"  counts_as_approved_runtime_evidence={str(blocker['counts_as_approved_runtime_evidence']).lower()}",
                    f"  counts_as_runtime_evidence={str(blocker['counts_as_runtime_evidence']).lower()}",
                    f"  counts_as_sdk_evidence={str(blocker['counts_as_sdk_evidence']).lower()}",
                ]
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Ready Log Copy Report",
            "",
            f"path={copy_report['path']}",
            f"present={str(copy_report['present']).lower()}",
            f"checked={str(copy_report['checked']).lower()}",
            f"classification={copy_report['classification']}",
            f"schema={markdown_scalar(copy_report['schema'])}",
            f"schema_valid={str(copy_report['schema_valid']).lower()}",
            f"status={markdown_scalar(copy_report['status'])}",
            f"reported_ready={markdown_scalar(copy_report['reported_ready'])}",
            f"ready_to_copy={markdown_scalar(copy_report['ready_to_copy'])}",
            f"copy_readiness={copy_report['copy_readiness']}",
            f"copied={str(copy_report['copied']).lower()}",
            f"observer_only_no_role_window_detected={str(copy_report['observer_only_no_role_window_detected']).lower()}",
            f"active_observer_only_no_role_window={str(copy_report['active_observer_only_no_role_window']).lower()}",
            f"post_window_observer_only_no_role_window={str(copy_report['post_window_observer_only_no_role_window']).lower()}",
            f"observer_only_no_role_window_state={markdown_scalar(copy_report['observer_only_no_role_window_state'])}",
            f"post_window_closure_action={markdown_scalar(copy_report['post_window_closure_action'])}",
            f"accepted_by_approved_sibling_set_checker={str(copy_report['accepted_by_approved_sibling_set_checker']).lower()}",
            f"copy_report_counts_as_approved_runtime_evidence={str(copy_report['copy_report_counts_as_approved_runtime_evidence']).lower()}",
            f"counts_as_approved_runtime_evidence={str(copy_report['counts_as_approved_runtime_evidence']).lower()}",
            "",
            "roles_present:",
            *markdown_list(copy_report["roles_present"]),
            "missing_roles:",
            *markdown_list(copy_report["missing_roles"]),
            "reported_blockers:",
            *markdown_list(copy_report["reported_blockers"]),
            "blockers:",
            *markdown_list(copy_report["blockers"]),
        ]
    )
    lines.extend(
        [
        "",
        "## Present Siblings",
        "",
        ]
    )
    lines.extend(markdown_list(report["present_siblings"]))
    lines.extend(["", "## Required Sibling Set", ""])
    lines.extend(markdown_list(report["required_sibling_set"]))
    lines.extend(["", "## Missing Expected Sibling Artifacts", ""])
    lines.extend(markdown_list(report["missing_expected_sibling_artifacts"]))
    lines.extend(["", "## Required Sidecars", ""])
    lines.extend(markdown_list(report["required_sidecars"]))
    lines.extend(["", "## Exact Missing Sidecars", ""])
    lines.extend(markdown_list(report["exact_missing_sidecars"]))
    lines.extend(["", "## Missing Required Artifacts", ""])
    lines.extend(markdown_list(report["missing_required_artifacts"]))
    lines.extend(["", "## Missing Siblings", ""])
    lines.extend(markdown_list(report["missing_siblings"]))
    checker_gate = report["copied_bundle_checker_acceptance_gate"]
    lines.extend(
        [
            "",
            "## Copied Bundle Checker Gate",
            "",
            f"status={checker_gate['status']}",
            f"recommended_next_action={checker_gate['recommended_next_action']}",
            f"checker_command_status={checker_gate['checker_command_status']}",
            f"copied_bundle_checker_acceptance_required_before_sdk_p0_changes={str(checker_gate['copied_bundle_checker_acceptance_required_before_sdk_p0_changes']).lower()}",
            f"accepted_checker_required_before_status_claim={str(checker_gate['accepted_checker_required_before_status_claim']).lower()}",
            f"accepted_checker_required_before_sdk_p0_changes={str(checker_gate['accepted_checker_required_before_sdk_p0_changes']).lower()}",
            f"approved_runtime_evidence_accepted_by_checker={str(checker_gate['approved_runtime_evidence_accepted_by_checker']).lower()}",
            f"copied_bundle_checker_acceptance_recorded={str(checker_gate['copied_bundle_checker_acceptance_recorded']).lower()}",
            f"counts_as_approved_runtime_evidence={str(checker_gate['counts_as_approved_runtime_evidence']).lower()}",
            f"counts_toward_sdk={str(checker_gate['counts_toward_sdk']).lower()}",
            f"counts_toward_p0_dependency_chain={str(checker_gate['counts_toward_p0_dependency_chain']).lower()}",
            f"sdk_p0_changes_authorized={str(checker_gate['sdk_p0_changes_authorized']).lower()}",
            "blockers:",
            *markdown_list(checker_gate["blockers"]),
        ]
    )
    if checker_gate.get("checker_command_text_not_executed"):
        lines.append(
            f"checker_command_text_not_executed={checker_gate['checker_command_text_not_executed']}"
        )
    lines.extend(
        [
            "",
            "## Closure Checklist",
            "",
            f"approved_bundle_path={report['approved_bundle_path']}",
        ]
    )
    for item in report["closure_artifact_checklist"]:
        lines.extend(
            [
                f"- relative_path={item['relative_path']}",
                f"  status={item['status']}",
                f"  present={str(item['present']).lower()}",
                f"  valid={str(item['valid']).lower()}",
                f"  required_for={item['required_for']}",
                f"  counts_as_approved_runtime_evidence_by_this_report={str(item['counts_as_approved_runtime_evidence_by_this_report']).lower()}",
            ]
        )
    lines.extend(["", "## Lifecycle Event Roles", ""])
    lines.extend(
        [
            f"copied_log_present={str(role_state['copied_log_present']).lower()}",
            f"complete_triplet_candidate={str(role_state['complete_triplet_candidate']).lower()}",
            f"partial_start_end_present={str(role_state['partial_start_end_present']).lower()}",
            f"missing_strict_rejected_start={str(role_state['missing_strict_rejected_start']).lower()}",
            f"strict_rejected_start_expected_shape={role_state['strict_rejected_start_expected_shape']}",
            f"strict_rejected_start_observed_shape={markdown_scalar(strict_rejected_start_observed_shape)}",
            "strict_rejected_start_observed_shape_counts_as_approved_runtime_evidence=false",
            f"event_line_count={role_state['event_line_count']}",
            f"inspection_blocked_by={markdown_scalar(role_state['inspection_blocked_by'])}",
            "",
            "### Required Role Triplet",
            "",
            *markdown_list(report["required_lifecycle_event_role_triplet"]),
            "",
            "### Roles Seen",
            "",
            *markdown_list(role_state["roles_seen"]),
            "",
            "### Missing Roles",
            "",
            *markdown_list(report["missing_lifecycle_event_roles"]),
        ]
    )
    lines.extend(["", "## Missing Artifacts/Roles", ""])
    lines.extend(["missing_required_artifacts:"])
    lines.extend(markdown_list(report["missing_artifacts_and_roles"]["missing_required_artifacts"]))
    lines.extend(["required_sidecars:"])
    lines.extend(markdown_list(report["missing_artifacts_and_roles"]["required_sidecars"]))
    lines.extend(["exact_missing_sidecars:"])
    lines.extend(markdown_list(report["missing_artifacts_and_roles"]["exact_missing_sidecars"]))
    lines.extend(["required_lifecycle_event_role_triplet:"])
    lines.extend(markdown_list(report["missing_artifacts_and_roles"]["required_lifecycle_event_role_triplet"]))
    lines.extend(["missing_lifecycle_event_roles:"])
    lines.extend(markdown_list(report["missing_artifacts_and_roles"]["missing_lifecycle_event_roles"]))
    lines.extend(["", "## Exact Missing Operations", ""])
    if report["exact_missing_operations"]:
        for operation in report["exact_missing_operations"]:
            lines.extend(
                [
                    f"- artifact={operation['artifact']}",
                    f"  operation={operation['operation']}",
                    f"  authorized_to_run_now={str(operation['authorized_to_run_now']).lower()}",
                    f"  requires_current_turn_operator_approval={str(operation['requires_current_turn_operator_approval']).lower()}",
                    f"  requires_fresh_current_turn_operator_approval={str(operation.get('requires_fresh_current_turn_operator_approval', False)).lower()}",
                    f"  requires_bound_standing_launch_authority_receipt_before_execution={str(operation.get('requires_bound_standing_launch_authority_receipt_before_execution', False)).lower()}",
                    f"  operator_authority_source_required={operation.get('operator_authority_source_required', NO_OPERATOR_AUTHORITY_SOURCE)}",
                ]
            )
            if operation.get("role"):
                lines.append(f"  role={operation['role']}")
            operation_target = operation.get("target")
            if isinstance(operation_target, dict):
                lines.append(f"  target_key={markdown_scalar(operation_target.get('target_key'))}")
            command = operation.get("command_text_not_executed")
            if command:
                lines.append("  command_status=NOT EXECUTED")
                lines.append(f"  command_text_not_executed={command}")
            validation = operation.get("validation_command_text_not_executed")
            if validation:
                lines.append("  validation_command_status=NOT EXECUTED")
                lines.append(f"  validation_command_text_not_executed={validation}")
    else:
        lines.append("- none")
    lines.extend(["", "## NOT EXECUTED Commands", ""])
    if report["not_executed_commands"]:
        for command in report["not_executed_commands"]:
            lines.extend(
                [
                    f"- artifact={command['artifact']}",
                    f"  command_kind={command['command_kind']}",
                    f"  command_status={command['status']}",
                    f"  command_text={command['command']}",
                ]
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            authority_heading,
            "",
            f"required_before_missing_operations={str(approval['required_before_missing_operations']).lower()}",
            f"source_required={approval['source_required']}",
            f"operator_authority_source_required={approval['operator_authority_source_required']}",
            f"current_turn_operator_approval_required={str(approval['current_turn_operator_approval_required']).lower()}",
            f"fresh_current_turn_operator_approval_required={str(approval['fresh_current_turn_operator_approval_required']).lower()}",
            f"requires_bound_standing_launch_authority_receipt_before_execution={str(approval['requires_bound_standing_launch_authority_receipt_before_execution']).lower()}",
            f"standing_approval_allowed={str(approval['standing_approval_allowed']).lower()}",
            f"standing_launch_authority_covers_target_run={str(approval['standing_launch_authority_covers_target_run']).lower()}",
            f"standing_launch_authority_satisfies_operator_approval={str(approval['standing_launch_authority_satisfies_operator_approval']).lower()}",
            f"approval_recorded_by_this_report={str(approval['approval_recorded_by_this_report']).lower()}",
            f"server_authorization_granted_by_this_report={str(approval['server_authorization_granted_by_this_report']).lower()}",
            f"live_ops_authorization_granted_by_this_report={str(approval['live_ops_authorization_granted_by_this_report']).lower()}",
            f"runtime_capture_authorization_granted_by_this_report={str(approval['runtime_capture_authorization_granted_by_this_report']).lower()}",
            f"workspace_write_authorization_granted_by_this_report={str(approval['workspace_write_authorization_granted_by_this_report']).lower()}",
            f"live_log_reads_authorized_by_this_report={str(approval['live_log_reads_authorized_by_this_report']).lower()}",
            f"approved_runtime_evidence_granted_by_this_report={str(approval['approved_runtime_evidence_granted_by_this_report']).lower()}",
            f"passive_snapshots_count_as_evidence_by_this_report={str(approval['passive_snapshots_count_as_evidence_by_this_report']).lower()}",
            f"status_report_paths_authorize_current_turn={str(approval['status_report_paths_authorize_current_turn']).lower()}",
            f"discord_authorization_granted_by_this_report={str(approval['discord_authorization_granted_by_this_report']).lower()}",
            f"discord_sent_by_this_report={str(approval['discord_sent_by_this_report']).lower()}",
            f"post_reboot_monitor_required_scope_path={markdown_scalar(required_scope['post_reboot_monitor_context']['path'])}",
            f"post_reboot_monitor_required_scope_counts_as_approved_runtime_evidence={str(required_scope['post_reboot_monitor_context']['counts_as_approved_runtime_evidence']).lower()}",
            f"confirmed_beta_notice_required_scope_path={markdown_scalar(required_scope['confirmed_beta_notice_context']['path'])}",
            f"confirmed_beta_notice_required_scope_counts_as_approved_runtime_evidence={str(required_scope['confirmed_beta_notice_context']['counts_as_approved_runtime_evidence']).lower()}",
            f"required_scope_evidence_dir={required_scope['evidence_dir']}",
            f"required_scope_run_id={required_scope['run_id']}",
            f"required_scope_target_instance={markdown_scalar(target.get('instance'))}",
            f"required_scope_target_map={markdown_scalar(target.get('map'))}",
            f"required_scope_target_query_port={markdown_scalar(target.get('query_port'))}",
            f"required_scope_target_key={markdown_scalar(target.get('target_key'))}",
            f"required_scope_operator_authority_source_required={required_scope['operator_authority_source_required']}",
            f"required_scope_current_turn_operator_approval_required={str(required_scope['current_turn_operator_approval_required']).lower()}",
            f"required_scope_fresh_current_turn_operator_approval_required={str(required_scope['fresh_current_turn_operator_approval_required']).lower()}",
            f"required_scope_requires_bound_standing_launch_authority_receipt_before_execution={str(required_scope['requires_bound_standing_launch_authority_receipt_before_execution']).lower()}",
            f"required_scope_standing_launch_authority_covers_target_run={str(required_scope['standing_launch_authority_covers_target_run']).lower()}",
            f"must_name_exact_missing_file_writes={str(required_scope['must_name_exact_missing_file_writes']).lower()}",
            f"must_name_exact_target={str(required_scope['must_name_exact_target']).lower()}",
            f"must_bind_missing_roles_when_runtime_observation_is_requested={str(required_scope['must_bind_missing_roles_when_runtime_observation_is_requested']).lower()}",
            f"must_preserve_the_island_off_when_supplied={str(required_scope['must_preserve_the_island_off_when_supplied']).lower()}",
            f"must_preserve_two_server_cap={str(required_scope['must_preserve_two_server_cap']).lower()}",
            f"two_server_cap_max_running_servers={required_scope['two_server_cap_max_running_servers']}",
            f"must_preserve_two_server_cap_when_supplied={str(required_scope['must_preserve_two_server_cap_when_supplied']).lower()}",
            f"must_preserve_supplied_operational_constraints={str(required_scope['must_preserve_supplied_operational_constraints']).lower()}",
            f"future_window_needs_players={str(notice['future_window_needs_players']).lower()}",
            f"notice_path={notice['notice_path']}",
            f"notice_path_named={str(notice['notice_path_named']).lower()}",
            f"beta_testers_notice_path_named={str(notice['beta_testers_notice_path_named']).lower()}",
            f"real_beta_testers_notice_action_required_before_activation={str(notice['real_beta_testers_notice_action_required_before_activation']).lower()}",
            f"notice_required_action={markdown_scalar(notice['required_action'])}",
            f"notice_sent_by_this_report={str(notice['sent_by_this_report']).lower()}",
            f"notice_discord_sent_by_this_report={str(notice['discord_sent_by_this_report']).lower()}",
            f"notice_discord_authorized_by_this_report={str(notice['discord_authorized_by_this_report']).lower()}",
            f"notice_discord_command_emitted_by_this_report={str(notice['discord_command_emitted_by_this_report']).lower()}",
            f"must_not_claim_readiness={str(required_scope['must_not_claim_readiness']).lower()}",
            "",
            "### Required Missing Artifact Writes",
            "",
            *markdown_list(required_scope["missing_artifacts"]),
            "",
            "### Required Missing Sidecars",
            "",
            *markdown_list(required_scope["missing_sidecars"]),
            "",
            "### Required Missing Lifecycle Roles",
            "",
            *markdown_list(required_scope["missing_lifecycle_event_roles"]),
            "",
            "### Notice Requirements",
            "",
            *markdown_list(notice["notes"]),
            "",
            "### Required Notice Actions",
            "",
        ]
    )
    if report["required_notice_actions"]:
        for action in report["required_notice_actions"]:
            lines.extend(
                [
                    f"- operation={action['operation']}",
                    f"  notice_path={action['notice_path']}",
                    f"  authorized_to_run_now={str(action['authorized_to_run_now']).lower()}",
                    f"  requires_current_turn_operator_approval={str(action['requires_current_turn_operator_approval']).lower()}",
                    f"  requires_fresh_current_turn_operator_approval={str(action.get('requires_fresh_current_turn_operator_approval', False)).lower()}",
                    f"  requires_bound_standing_launch_authority_receipt_before_execution={str(action.get('requires_bound_standing_launch_authority_receipt_before_execution', False)).lower()}",
                    f"  operator_authority_source_required={action.get('operator_authority_source_required', NO_OPERATOR_AUTHORITY_SOURCE)}",
                    f"  command_status={action['command_status']}",
                    f"  sent_by_this_report={str(action['sent_by_this_report']).lower()}",
                ]
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Non-Claims",
            "",
        ]
    )
    lines.extend(f"- {claim}" for claim in report["non_claims"])
    return "\n".join(lines) + "\n"


def write_outputs(report: dict[str, Any], outputs: dict[str, Path]) -> None:
    if "json_output" in outputs:
        outputs["json_output"].parent.mkdir(parents=True, exist_ok=True)
        outputs["json_output"].write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if "markdown_output" in outputs:
        outputs["markdown_output"].parent.mkdir(parents=True, exist_ok=True)
        outputs["markdown_output"].write_text(markdown_report(report), encoding="utf-8")


def main() -> int:
    args = parse_args()
    validate_args(args)
    outputs = resolve_output_paths(args)
    report = build_report(args)
    write_outputs(report, outputs)
    if args.format == "markdown":
        print(markdown_report(report), end="")
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["evidence_closure_inputs_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
