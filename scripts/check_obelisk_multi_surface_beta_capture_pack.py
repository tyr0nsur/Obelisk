#!/usr/bin/env python3
"""Validate an offline multi-surface beta capture pack.

This checker verifies pack integrity and non-claim boundaries. It does not execute
surface checkers, read live ARK logs, touch servers, send Discord, or convert candidate
material into approved runtime evidence.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

import protected_paths
from plan_obelisk_multi_surface_beta_capture import (
    ARTIFACT_INTAKE_CONSTRAINTS,
    ARTIFACT_TEMPLATE_ROOT,
    BROAD_BETA_CAPTURE_ACTION_GROUP_IDS,
    BROAD_BETA_CAPTURE_PACK_PATH_ID,
    BROAD_BETA_CAPTURE_SURFACE_IDS,
    BROAD_BETA_CAPTURE_WORKSHEET_FILE,
    BROAD_BETA_CAPTURE_WORKSHEET_ID,
    BROAD_BETA_CAPTURE_WORKSHEET_SCHEMA,
    CAPTURE_ARTIFACTS_BY_SURFACE,
    CURRENT_ROUTE_BLOCKER as PLAN_CURRENT_ROUTE_BLOCKER,
    LIFECYCLE_CORRELATION_FIELD_IDS,
    LIFECYCLE_CORRELATION_SCHEMA,
    LIFECYCLE_CORRELATION_STATUS,
    LIFECYCLE_PHASE_ANCHOR_VALUES,
    NO_RESTART_ACTION_BOUNDARY,
    NON_CLAIM_FLAGS,
    NON_SUBSTITUTION_FLAGS,
    PARALLEL_CAPTURE_BOUNDARY,
    PARALLEL_BETA_CAPTURE_ACTION_GROUP_IDS,
    PARALLEL_BETA_CAPTURE_DOMAINS,
    PARALLEL_BETA_CAPTURE_MATRIX_ID,
    PARALLEL_BETA_CAPTURE_SURFACE_IDS,
    PLAYER_PRINCIPAL_WINDOW_COMPOSITION,
    PRIMARY_LIFECYCLE_EVENT_REFERENCE_VALUES,
    REDACTION_POLICY,
    REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
    SAFE_MAP_RE,
    SAFE_TOKEN_RE,
    SCHEMA as PLAN_SCHEMA,
    SINGLE_PLAYER_PARALLEL_CAPTURE_ACTION_GROUP_IDS,
    SINGLE_PLAYER_PARALLEL_CAPTURE_DOMAIN_IDS,
    SINGLE_PLAYER_PARALLEL_CAPTURE_SEQUENCE_ID,
    SINGLE_PLAYER_PARALLEL_CAPTURE_SURFACE_IDS,
    SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE,
    SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_ID,
    SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_SCHEMA,
    SINGLE_PLAYER_PHASE_DOMAIN_IDS_BY_ACTION_GROUP,
    SINGLE_PLAYER_ROUTE_EXCLUDED_SURFACE_IDS,
    SINGLE_PLAYER_ROUTE_NON_CLAIM,
    SIMULTANEOUS_BETA_CAPTURE_ACTION_GROUP_IDS,
    SIMULTANEOUS_BETA_CAPTURE_SURFACE_IDS,
    SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE,
    SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_ID,
    SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_SCHEMA,
    STRICT_PLAYER_PRINCIPAL_TRIPLET,
    SIDE_LANE_CAPTURE_QUEUE_ID,
    SIDE_LANE_CAPTURE_QUEUE_STATUS,
    SOURCE_METADATA_FIELD_IDS,
    SOURCE_METADATA_INSTRUCTIONS,
    SOURCE_METADATA_SCHEMA,
    SOURCE_METADATA_STATUS,
    TARGET_BOUND_CHECKER_COMMAND_MATRIX_ID,
    TARGET_BOUND_CHECKER_COMMAND_MATRIX_STATUS,
    approved_runtime_window_binding,
    attach_source_metadata,
    SURFACES as PLAN_SURFACES,
    beta_capture_interaction_boundary,
    beta_tester_next_action_groups,
    broad_beta_capture_pack_path,
    capture_artifacts_for,
    candidate_only_metadata,
    checker_command_bindings,
    exact_capture_objectives,
    lifecycle_correlation_field_ids,
    lifecycle_correlation_metadata,
    no_flood_capture_policy,
    no_restart_action_boundary,
    non_substitution_flags,
    operator_tester_action_metadata,
    parallel_beta_capture_side_lane_matrix,
    parallel_capture_boundary,
    player_principal_window_composition,
    redaction_policy,
    resolved_checker_command_template,
    side_lane_capture_queue,
    source_metadata_template,
    single_player_route_constraints,
    single_player_parallel_capture_sequence,
    surface_entry,
    target_binding,
    target_binding_id,
    target_bound_checker_command_matrix,
    target_bound_checker_command_row,
    text_privacy_boundary,
)
from prepare_obelisk_multi_surface_beta_capture_pack import (
    INTAKE_SCHEMA,
    NON_AUTHORIZATION,
    PERMISSIONS_ADMIN_BETA_CAPTURE_CANDIDATE_TEMPLATE,
    SCHEMA as PACK_SCHEMA,
    broad_beta_capture_candidate_worksheet,
    json_bytes,
    sha256_file,
    single_player_parallel_capture_candidate_worksheet,
    simultaneous_beta_capture_candidate_worksheet,
)


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
REPORT_SCHEMA = "obelisk.multi-surface-beta-capture-pack-check.v1"
CHECKER_MATRIX_SCHEMA = "obelisk.multi-surface-beta-capture-checker-matrix.v1"
NON_CLAIM_MANIFEST_SCHEMA = "obelisk.multi-surface-beta-capture-non-claim-manifest.v1"
CURRENT_ROUTE_BLOCKER = PLAN_CURRENT_ROUTE_BLOCKER
NEXT_REQUIRED_ARTIFACT = REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE
EXPECTED_ARTIFACTS = {
    "README.md",
    "candidate-artifact-intake.json",
    "checker-command-matrix.json",
    "multi-surface-capture-plan.json",
    "non-claim-manifest.json",
    "operator-runbook.md",
    BROAD_BETA_CAPTURE_WORKSHEET_FILE,
    SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE,
    SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE,
    PERMISSIONS_ADMIN_BETA_CAPTURE_CANDIDATE_TEMPLATE,
}
EXPECTED_FILES = EXPECTED_ARTIFACTS | {"manifest.json"}
EXPECTED_SURFACES = {surface["id"] for surface in PLAN_SURFACES}
EXPECTED_SURFACE_BY_ID = {surface["id"]: dict(surface) for surface in PLAN_SURFACES}
EXPECTED_SURFACE_CHECKERS = {
    surface_id: surface["checker"] for surface_id, surface in EXPECTED_SURFACE_BY_ID.items()
}
EXPECTED_SURFACE_COMMANDS = {
    surface_id: ["python3", surface["checker"], *surface.get("checker_args", ["--json"])]
    for surface_id, surface in EXPECTED_SURFACE_BY_ID.items()
}
EXPECTED_SURFACE_OBJECTIVES = {
    surface_id: surface["objective"] for surface_id, surface in EXPECTED_SURFACE_BY_ID.items()
}
EXPECTED_SURFACE_OPERATOR_ACTIONS = {
    surface_id: surface["operator_action"] for surface_id, surface in EXPECTED_SURFACE_BY_ID.items()
}
EXPECTED_SURFACE_TESTER_ACTIONS = {
    surface_id: surface["tester_action"] for surface_id, surface in EXPECTED_SURFACE_BY_ID.items()
}
EXPECTED_CANDIDATE_ONLY_METADATA = candidate_only_metadata()
EXPECTED_NO_FLOOD_CAPTURE_POLICY = no_flood_capture_policy()
EXPECTED_PARALLEL_CAPTURE_BOUNDARY = parallel_capture_boundary()
EXPECTED_PLAYER_PRINCIPAL_WINDOW_COMPOSITION = player_principal_window_composition()
EXPECTED_TEXT_PRIVACY_BOUNDARY = text_privacy_boundary()
EXPECTED_BETA_CAPTURE_INTERACTION_BOUNDARY = beta_capture_interaction_boundary()
EXPECTED_SINGLE_PLAYER_ROUTE_CONSTRAINTS = single_player_route_constraints()
EXPECTED_LIFECYCLE_CORRELATION_FIELD_IDS = lifecycle_correlation_field_ids()
EXPECTED_CAPTURE_ARTIFACTS_BY_SURFACE = {
    surface_id: [dict(artifact) for artifact in artifacts]
    for surface_id, artifacts in CAPTURE_ARTIFACTS_BY_SURFACE.items()
}
EXPECTED_SURFACE_PRIORITIES = {
    surface_id: index for index, surface_id in enumerate((surface["id"] for surface in PLAN_SURFACES), start=1)
}
if len(EXPECTED_SURFACE_BY_ID) != len(PLAN_SURFACES):
    raise RuntimeError("pack checker expected surface bindings contain duplicate ids")
if set(EXPECTED_SURFACE_BY_ID) != EXPECTED_SURFACES:
    raise RuntimeError("pack checker expected surface set drifted from plan")
if set(EXPECTED_CAPTURE_ARTIFACTS_BY_SURFACE) != EXPECTED_SURFACES:
    raise RuntimeError("pack checker expected capture artifact set drifted from plan")
REQUIRED_FALSE_FLAGS = {
    key
    for key, value in NON_CLAIM_FLAGS.items()
    if value is False
}
REQUIRED_TRUE_FLAGS = {
    key
    for key, value in NON_CLAIM_FLAGS.items()
    if value is True
}
EXPECTED_NON_SUBSTITUTION_FLAGS = non_substitution_flags()
REQUIRED_TRUE_SURFACE_FLAGS = (
    "candidate_capture_only",
    "requires_checker_acceptance",
    "requires_player_principal_triplet",
    "blocked_by_player_principal_evidence",
)
REQUIRED_FALSE_SURFACE_FLAGS = (
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "counts_as_approved_runtime_evidence",
    "counts_as_runtime_evidence",
    "counts_as_sdk_progress",
    "counts_as_p0_progress",
    "clears_approved_runtime_evidence_missing",
    "replaces_player_principal_evidence",
    "replaces_player_principal_triplet",
    "substitutes_for_player_principal_lifecycle_evidence",
    "substitutes_for_player_principal_lifecycle_triplet",
    "side_lane_substitutes_for_player_principal_lifecycle_evidence",
    "player_principal_lifecycle_evidence_substitution_allowed",
    "approved_runtime_evidence_substitution_allowed",
    "primary_evidence_substitution_allowed",
    "runtime_ready",
    "public_sdk_ready",
    "stable_sdk_ready",
    "v1_completion_ready",
)
REQUIRED_TRUE_ARTIFACT_FLAGS = (
    "candidate_artifact_only",
    "copy_to_offline_workspace",
    "must_not_be_live_server_path",
    "redaction_required",
)
REQUIRED_FALSE_ARTIFACT_FLAGS = (
    "counts_as_approved_runtime_evidence",
    "counts_as_runtime_evidence",
    "counts_as_sdk_progress",
    "counts_as_p0_progress",
    "clears_approved_runtime_evidence_missing",
    "replaces_player_principal_evidence",
    "replaces_player_principal_triplet",
    "substitutes_for_player_principal_lifecycle_evidence",
    "substitutes_for_player_principal_lifecycle_triplet",
    "side_lane_substitutes_for_player_principal_lifecycle_evidence",
    "player_principal_lifecycle_evidence_substitution_allowed",
    "runtime_ready",
    "public_sdk_ready",
    "stable_sdk_ready",
)
EXPECTED_INTAKE_CONSTRAINTS = {
    "single_beta_session_intent",
    "copy_to_offline_workspace_before_analysis",
    "do_not_read_live_server_paths_from_pack",
    "do_not_send_discord",
    "do_not_restart_servers_from_pack",
    "do_not_change_markers_or_env_from_pack",
    "requires_checker_acceptance_before_any_surface_claim",
    "side_lanes_non_counting_before_player_principal",
    "artifacts_must_keep_target_binding",
    "artifact_templates_only",
    "artifact_templates_must_stay_relative",
    "artifact_templates_must_stay_under_candidate_artifacts",
    "artifact_templates_must_not_name_live_server_paths",
    "redaction_required_before_checker_intake",
    "candidate_artifact_presence_never_implies_checker_acceptance",
    "candidate_artifact_intake_cannot_replace_primary_runtime_evidence",
    "side_lane_artifacts_cannot_substitute_for_player_principal_lifecycle_evidence",
    "parallel_with_player_principal_lifecycle_window_planned",
    "side_surfaces_grouped_as_optional_parallel_candidate_observations",
    "side_surfaces_non_evidence_until_own_checker_acceptance",
    "separate_player_backed_window_approval_required",
    "same_approved_runtime_window_required",
    "side_lane_artifacts_must_share_player_principal_window",
    "operator_tester_action_metadata_required",
    "lifecycle_correlation_metadata_required",
    "lifecycle_correlation_metadata_is_non_evidence",
    "no_flood_single_request_row_per_surface",
    "operator_request_dedupe_required",
    "source_present_false_never_implies_runtime_evidence",
}
ARTIFACT_TEMPLATE_ROOT_COMPONENT = ARTIFACT_TEMPLATE_ROOT.rstrip("/")
EXPECTED_FALSE_INTAKE_CONSTRAINTS = {
    "pack_authorizes_approved_runtime_window",
    "pack_authorizes_player_backed_window",
}
FORBIDDEN_LIVE_PATH_FRAGMENTS = (
    "/servidor/ark",
    "servidor/ark",
    "ShooterGame/Saved",
    "Saved/Logs",
)
REQUIRED_REDACTION_TOKENS = (
    "raw player text",
    "secrets",
    "webhook URLs",
    "private player data",
)
DISCORD_WEBHOOK_URL_RE = re.compile(
    r"https?://(?:canary\.|ptb\.)?(?:discord(?:app)?\.com)/api/webhooks/[A-Za-z0-9_.~:/?#\[\]@!$&'()*+,;=%-]+",
    re.IGNORECASE,
)
TEXT_RETENTION_ASSIGNMENT_RE = re.compile(
    r"\b(?:raw[_ -]?(?:player[_ -]?text|chat(?:[_ -]?payload)?)|private[_ -]?player[_ -]?data|"
    r"(?:discord[_ -]?)?webhook(?:[_ -]?url)?|"
    r"(?:[A-Za-z0-9]+[_ -]+)*(?:secret|token|api[_ -]?key|password))"
    r"[A-Za-z0-9_-]*"
    r"[\"']?\s*[:=]\s*[\"']?"
    r"(?!false\b|0\b|none\b|null\b|redacted\b|<redacted>|disabled\b|not[_ -]?allowed\b)"
    r"[^,\s`\"'}]{4,}",
    re.IGNORECASE,
)
BLOCKER_CLEARANCE_CLAIM_RE = re.compile(
    r"\b(?:clear|clears|cleared|clearing|satisfy|satisfies|satisfied|satisfying|"
    r"resolve|resolves|resolved|resolving|remove|removes|removed|removing|"
    r"unblock|unblocks|unblocked|unblocking)\b(?:[\s_-]+\w+){0,6}"
    r"[\s_-]+approved_runtime_evidence_missing\b|"
    r"\bapproved_runtime_evidence_missing\b(?:[\s_-]+\w+){0,6}[\s_-]+"
    r"\b(?:clear|clears|cleared|clearing|satisfy|satisfies|satisfied|satisfying|"
    r"resolve|resolves|resolved|resolving|remove|removes|removed|removing|"
    r"unblock|unblocks|unblocked|unblocking)\b",
    re.IGNORECASE,
)
BLOCKER_CLEARANCE_NEGATION_RE = re.compile(
    r"\b(?:cannot|can\s+not|does\s+not|do\s+not|must\s+not|never|not|no|false)\b",
    re.IGNORECASE,
)
PROMOTIONAL_CLAIM_TEXT_RE = re.compile(
    r"\b(?:is|are|becomes?|accepted\s+as|approved\s+as|status\s*[:=])\b"
    r"(?:[\s,/_-]+\w+){0,4}"
    r"[\s,/_-]+(?:approved\s+runtime\s+evidence|runtime\s+evidence)\b|"
    r"\b(?:counts?\s+(?:as|toward)|contributes?\s+(?:to|toward)|adds?\s+to)\b"
    r"(?:[\s,/_-]+\w+){0,8}"
    r"[\s,/_-]+(?:approved\s+runtime\s+evidence|runtime\s+evidence|sdk\s+progress|"
    r"sdk|p0\s+progress|p0|v1\s+completion)\b|"
    r"\b(?:approved\s+runtime\s+evidence|runtime\s+evidence|sdk|p0|public\s+sdk|"
    r"stable\s+sdk|runtime|release|publication|plugin\s+hub)\b"
    r"(?:[\s,/_-]+\w+){0,8}"
    r"[\s,/_-]+(?:ready|accepted|complete|satisfied|cleared|unblocked|"
    r"authorized)\b|"
    r"\b(?:authorizes?|authorized|authorization\s+(?:granted|ready|approved))\b"
    r"(?:[\s,/_-]+\w+){0,8}"
    r"[\s,/_-]+(?:live|server|runtime\s+capture|discord|rcon|restart|marker|env|"
    r"log\s+read)\b|"
    r"\b(?:live|server|runtime\s+capture|discord|rcon|restart|marker|env|log\s+read)"
    r"\b(?:[\s,/_-]+\w+){0,8}"
    r"[\s,/_-]+(?:authorized|authorization\s+(?:granted|ready|approved))\b",
    re.IGNORECASE,
)
SENSITIVE_RETENTION_KEY_ALIASES = {
    "apikey",
    "apitoken",
    "discordwebhook",
    "discordwebhookurl",
    "password",
    "privateplayerdata",
    "privateplayerdatasample",
    "rawchat",
    "rawchatpayload",
    "rawchatpayloadsample",
    "rawplayertext",
    "rawplayertextsample",
    "secret",
    "secretvalue",
    "token",
    "webhook",
    "webhookurl",
}
SENSITIVE_RETENTION_KEY_PARTS = (
    "apikey",
    "apitoken",
    "discordwebhook",
    "password",
    "privateplayerdata",
    "rawchatpayload",
    "rawplayertext",
    "secret",
    "secretvalue",
    "webhookurl",
)
ALLOWED_REDACTED_SENTINELS = {
    "",
    "<redacted>",
    "<redacted-value>",
    "<redacted-secret>",
    "<redacted-webhook-url>",
    "redacted",
    "none",
    "null",
    "not_allowed",
    "not allowed",
    "disabled",
    "prohibited",
}
FALSE_PROGRESS_READINESS_KEYS = {
    "approved_runtime_evidence",
    "approved_runtime_evidence_accepted",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_progress",
    "approved_runtime_evidence_progress_contribution",
    "approved_runtime_evidence_ready",
    "approved_runtime_evidence_status",
    "approved_runtime_evidence_substitution_allowed",
    "approvedRuntimeEvidenceAccepted",
    "approvedRuntimeEvidencePresent",
    "approvedRuntimeEvidenceProgress",
    "approvedRuntimeEvidenceProgressContribution",
    "approvedRuntimeEvidenceReady",
    "approvedRuntimeEvidenceStatus",
    "approvedRuntimeEvidenceSubstitutionAllowed",
    "approvedRuntimeEvidenceMissingCleared",
    "approvesLiveActions",
    "approves_live_actions",
    "authorizationClaimAllowed",
    "authorizationReady",
    "authorizesArkStartStop",
    "authorizesBetaSession",
    "authorizesDiscordSend",
    "authorizesEvidenceWindow",
    "authorizesLiveLogRead",
    "authorizesLiveLogReads",
    "authorizesLiveOperations",
    "authorizesLiveServerAccess",
    "authorizesLiveServerPathReads",
    "authorizesLiveServerReads",
    "authorizesMarkerOrEnvChanges",
    "authorizesPlayerBackedRuntimeWindow",
    "authorizesPlayerBackedWindow",
    "authorizesRuntimeCapture",
    "authorizesRuntimeObserver",
    "authorizesServerRestart",
    "authorizesServerStart",
    "authorizesServerStop",
    "authorizes_server_restart",
    "authorizes_server_start",
    "authorizes_server_stop",
    "authorizes_ark_start_stop",
    "authorizes_beta_session",
    "authorizes_discord_send",
    "authorizes_evidence_window",
    "authorizes_live_log_read",
    "authorizes_live_log_reads",
    "authorizes_live_operations",
    "authorizes_live_server_access",
    "authorizes_live_server_path_reads",
    "authorizes_live_server_reads",
    "authorizes_marker_or_env_changes",
    "authorizes_player_backed_runtime_window",
    "authorizes_player_backed_window",
    "authorizes_runtime_capture",
    "authorizes_runtime_observer",
    "betaNoticesCountAsApprovedRuntimeEvidence",
    "betaNoticesCountAsRuntimeEvidence",
    "betaNoticesCountAsSdkProgress",
    "betaNoticesCountAsP0Progress",
    "beta_notices_count_as_approved_runtime_evidence",
    "beta_notices_count_as_runtime_evidence",
    "beta_notices_count_as_sdk_progress",
    "beta_notices_count_as_p0_progress",
    "buttonClicksCountAsApprovedRuntimeEvidence",
    "buttonClicksCountAsRuntimeEvidence",
    "buttonClicksCountAsSdkProgress",
    "buttonClicksCountAsP0Progress",
    "button_clicks_count_as_approved_runtime_evidence",
    "button_clicks_count_as_runtime_evidence",
    "button_clicks_count_as_sdk_progress",
    "button_clicks_count_as_p0_progress",
    "captureReady",
    "candidateCaptureReady",
    "candidateReady",
    "clearsApprovedRuntimeEvidenceMissing",
    "clears_approved_runtime_evidence_missing",
    "collectionCanReplacePlayerPrincipalEvidence",
    "collectionCountsBeforeCheckerAcceptance",
    "collection_can_replace_player_principal_evidence",
    "collection_counts_before_checker_acceptance",
    "completeSdkClaimProgressContribution",
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_ready",
    "completionReady",
    "completionStatus",
    "completion_ready",
    "completion_status",
    "discordRequestFanoutAllowed",
    "discordOrBetaInteractionsApproveLiveActions",
    "discordOrBetaInteractionsAuthorizeLiveActions",
    "discordOrBetaInteractionsGrantPublicSdkReadiness",
    "discordOrBetaInteractionsGrantStableReadiness",
    "discord_or_beta_interactions_approve_live_actions",
    "discord_or_beta_interactions_authorize_live_actions",
    "discord_or_beta_interactions_grant_public_sdk_readiness",
    "discord_or_beta_interactions_grant_stable_readiness",
    "discord_request_fanout_allowed",
    "floodCaptureAllowed",
    "flood_capture_allowed",
    "countsTowardP0",
    "countsTowardSdk",
    "counts_as_approved_runtime_evidence",
    "counts_as_p0_progress",
    "counts_as_runtime_evidence",
    "counts_as_sdk_progress",
    "counts_toward_p0",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_sdk",
    "discordSendRequired",
    "discordSendStatus",
    "discord_send_required",
    "discord_send_status",
    "artifactAccepted",
    "artifactReady",
    "betaCaptureReady",
    "checkerAccepted",
    "checkerReady",
    "p0DependencyChainClaimProgressContribution",
    "p0DependencyChainClaimProgressRatio",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_claim_progress_ratio",
    "p0_progress",
    "p0_progress_contribution",
    "p0_progress_status",
    "p0_ready",
    "p0_status",
    "p0Progress",
    "p0ProgressContribution",
    "p0ProgressStatus",
    "p0Ready",
    "p0Status",
    "packageShapeAccepted",
    "packageShapeReady",
    "package_shape_accepted",
    "package_shape_ready",
    "markerOrEnvChangeRequired",
    "markerOrEnvChangeStatus",
    "marker_or_env_change_required",
    "marker_or_env_change_status",
    "multiSurfacePlanCountsAsApprovedRuntimeEvidence",
    "multiSurfacePlanCountsAsSdkProgress",
    "multi_surface_plan_counts_as_approved_runtime_evidence",
    "multi_surface_plan_counts_as_sdk_progress",
    "liveAuthorizationReady",
    "liveAuthorizationStatus",
    "live_authorization_ready",
    "live_authorization_status",
    "liveLogReadRequired",
    "liveLogReadStatus",
    "live_log_read_required",
    "live_log_read_status",
    "operatorActionRequiresRestart",
    "operator_action_requires_restart",
    "packAuthorizesDiscord",
    "packAuthorizesApprovedRuntimeWindow",
    "packAuthorizesMarkerOrEnvChange",
    "packAuthorizesPlayerBackedWindow",
    "packAuthorizesRestart",
    "packAuthorizesRuntimeObserver",
    "pack_authorizes_discord",
    "pack_authorizes_approved_runtime_window",
    "pack_authorizes_marker_or_env_change",
    "pack_authorizes_player_backed_window",
    "pack_authorizes_restart",
    "pack_authorizes_runtime_observer",
    "passiveAccepted",
    "passiveCaptureAccepted",
    "passiveCapturePresent",
    "passiveCaptureReady",
    "passiveEvidenceAccepted",
    "passiveEvidencePresent",
    "passiveEvidenceReady",
    "passiveObserverAccepted",
    "passiveObserverReady",
    "passiveReadiness",
    "passiveReadinessAccepted",
    "passiveRuntimeEvidence",
    "passiveSnapshotAccepted",
    "passiveSnapshotPresent",
    "passiveSnapshotReady",
    "passiveSourceReady",
    "passiveStatus",
    "passive_accepted",
    "passive_capture_accepted",
    "passive_capture_present",
    "passive_capture_ready",
    "passive_evidence_accepted",
    "passive_evidence_present",
    "passive_evidence_ready",
    "passive_observer_accepted",
    "passive_observer_ready",
    "passive_readiness",
    "passive_readiness_accepted",
    "passive_runtime_evidence",
    "passive_snapshot_accepted",
    "passive_snapshot_present",
    "passive_snapshot_ready",
    "passive_source_ready",
    "passive_status",
    "pluginHubReady",
    "plugin_hub_ready",
    "privatePlayerDataRetentionAllowed",
    "private_player_data_retention_allowed",
    "primaryEvidenceSubstitutionAllowed",
    "primary_evidence_substitution_allowed",
    "playerPrincipalLifecycleEvidenceSubstitutionAllowed",
    "player_principal_lifecycle_evidence_substitution_allowed",
    "pluginHubStatus",
    "plugin_hub_status",
    "publicReady",
    "publicReachabilityCountsAsRuntimeEvidence",
    "publicReachabilityCountsAsSdkProgress",
    "public_reachability_counts_as_runtime_evidence",
    "public_reachability_counts_as_sdk_progress",
    "public_ready",
    "publicSdkReady",
    "publicSdkStatus",
    "public_sdk_ready",
    "public_sdk_status",
    "publicationReady",
    "publicationStatus",
    "publication_ready",
    "publication_status",
    "rawChatPayloadCaptureAllowed",
    "rawPlayerTextCaptureAllowed",
    "rawPlayerTextRetentionAllowed",
    "raw_chat_payload_capture_allowed",
    "raw_player_text_capture_allowed",
    "raw_player_text_retention_allowed",
    "ready",
    "releaseReady",
    "release_ready",
    "releaseStatus",
    "release_status",
    "releaseSupported",
    "release_supported",
    "restartRequired",
    "restart_required",
    "readinessAccepted",
    "readinessProgress",
    "readinessReady",
    "readinessStatus",
    "readiness_accepted",
    "readiness_progress",
    "readiness_ready",
    "readiness_status",
    "replacesPlayerPrincipalEvidence",
    "replacesPlayerPrincipalTriplet",
    "replaces_player_principal_evidence",
    "replaces_player_principal_triplet",
    "routeReady",
    "runtimeReady",
    "runtimeStatus",
    "runtime_ready",
    "runtime_status",
    "runtimeCaptureReady",
    "runtimeCaptureStatus",
    "runtime_capture_ready",
    "runtime_capture_status",
    "runtimeEvidenceAccepted",
    "runtimeEvidencePresent",
    "runtimeEvidenceProgress",
    "runtimeEvidenceProgressContribution",
    "runtimeEvidenceReady",
    "runtimeEvidenceStatus",
    "runtime_evidence_accepted",
    "runtime_evidence_present",
    "runtime_evidence_progress",
    "runtime_evidence_progress_contribution",
    "runtime_evidence_ready",
    "runtime_evidence_status",
    "sdkP0ProgressReady",
    "sdkReady",
    "sdkProgress",
    "sdkProgressContribution",
    "sdkProgressStatus",
    "sdkStatus",
    "sdk_p0_progress_ready",
    "sdk_progress",
    "sdk_progress_contribution",
    "sdk_progress_status",
    "sdk_status",
    "serverRestartRequired",
    "serverRestartStatus",
    "server_restart_required",
    "server_restart_status",
    "serverStartStatus",
    "server_start_status",
    "serverStopStatus",
    "server_stop_status",
    "sideLaneArtifactsClearApprovedRuntimeEvidenceMissing",
    "sideLaneCandidatesClearApprovedRuntimeEvidenceMissing",
    "side_lane_counts_toward_p0",
    "side_lane_counts_toward_sdk",
    "side_lane_artifacts_clear_approved_runtime_evidence_missing",
    "side_lane_candidates_clear_approved_runtime_evidence_missing",
    "sideLaneCollectionCanReplacePlayerPrincipalEvidence",
    "sideLaneCollectionCountsBeforeCheckerAcceptance",
    "sideLaneCollectionBeforePrimaryRouteActiveAllowed",
    "sideLaneSubstitutesForPlayerPrincipalLifecycleEvidence",
    "sideLaneWindowSubstitutionAllowed",
    "side_lane_collection_can_replace_player_principal_evidence",
    "side_lane_collection_counts_before_checker_acceptance",
    "side_lane_collection_before_primary_route_active_allowed",
    "side_lane_substitutes_for_player_principal_lifecycle_evidence",
    "side_lane_window_substitution_allowed",
    "sourceAccepted",
    "source_accepted",
    "sourceReady",
    "source_ready",
    "sourcePresent",
    "sourceMaterialPresent",
    "sourceMaterialCountsAsEvidence",
    "sourceStatus",
    "source_status",
    "source_present",
    "source_material_present",
    "source_material_counts_as_evidence",
    "secretsOrWebhookRetentionAllowed",
    "secrets_or_webhook_retention_allowed",
    "staleAccepted",
    "staleArtifactAccepted",
    "staleCaptureAccepted",
    "staleEvidenceAccepted",
    "staleEvidencePresent",
    "staleEvidenceReady",
    "stalePackReady",
    "staleReadiness",
    "staleReadinessAccepted",
    "staleRuntimeEvidence",
    "staleSourceStatus",
    "stale_accepted",
    "stale_artifact_accepted",
    "stale_capture_accepted",
    "stale_evidence_accepted",
    "stale_evidence_present",
    "stale_evidence_ready",
    "stale_pack_ready",
    "stale_readiness",
    "stale_readiness_accepted",
    "stale_runtime_evidence",
    "stale_source_status",
    "stableSdkReady",
    "stableSdkStatus",
    "stable_sdk_ready",
    "stable_sdk_status",
    "stableReady",
    "stableStatus",
    "stable_ready",
    "stable_status",
    "supportTierReady",
    "supportTierSupported",
    "support_tier_ready",
    "support_tier_supported",
    "testerActionRequiresRestart",
    "tester_action_requires_restart",
    "unboundedTesterRequestsAllowed",
    "unbounded_tester_requests_allowed",
    "targetSetAccepted",
    "targetSetProgress",
    "targetSetReadiness",
    "targetSetReady",
    "targetSetStatus",
    "target_set_accepted",
    "target_set_progress",
    "target_set_readiness",
    "target_set_ready",
    "target_set_status",
    "substitutesForPlayerPrincipalLifecycleEvidence",
    "substitutesForPlayerPrincipalLifecycleTriplet",
    "substitutes_for_player_principal_lifecycle_evidence",
    "substitutes_for_player_principal_lifecycle_triplet",
    "windowSubstitutionAllowed",
    "window_substitution_allowed",
    "v1CompletionReady",
    "v1CompletionProgress",
    "v1CompletionStatus",
    "v1_completion_ready",
    "v1_completion_progress",
    "v1_completion_status",
    "v1Ready",
    "v1Status",
    "v1_ready",
    "v1_status",
}
FALSE_PROGRESS_READINESS_KEY_ALIASES = {
    "".join(ch for ch in key.lower() if ch.isalnum())
    for key in FALSE_PROGRESS_READINESS_KEYS
}
TARGET_BINDING_ALIAS_KEY_ALIASES = {
    "artifacttargetbinding",
    "artifacttargetbindingid",
    "bindingid",
    "packtargetbinding",
    "packtargetbindingid",
    "plantargetbinding",
    "plantargetbindingid",
    "surfacetargetbinding",
    "surfacetargetbindingid",
    "targetbinding",
    "targetbindingid",
}
ALLOWED_TARGET_BINDING_KEYS = {
    "binding_id",
    "plan_target_binding",
    "plan_target_binding_id",
    "target_binding",
    "target_binding_id",
}


def add(blockers: list[dict[str, Any]], reason: str, path: str, **extra: Any) -> None:
    blockers.append({"reason": reason, "path": path, **extra})


def load_json(path: Path, blockers: list[dict[str, Any]], label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        add(blockers, "json_artifact_missing", label, file=str(path))
        return {}
    except json.JSONDecodeError as exc:
        add(blockers, "json_artifact_invalid", label, file=str(path), error=str(exc))
        return {}
    if not isinstance(payload, dict):
        add(blockers, "json_artifact_not_object", label, file=str(path))
        return {}
    return payload


def resolve_pack_root(path: Path) -> Path:
    candidate = path.expanduser()
    if candidate.name == "manifest.json":
        candidate = candidate.parent
    protected_paths.reject_symlink_component(candidate, "pack root")
    return protected_paths.reject_protected_input_path(candidate, "pack root")


def check_non_claim_flags(
    value: Any,
    blockers: list[dict[str, Any]],
    path: str,
    *,
    required_false_flags: set[str] = REQUIRED_FALSE_FLAGS,
    required_true_flags: set[str] = REQUIRED_TRUE_FLAGS,
) -> None:
    if not isinstance(value, dict):
        add(blockers, "non_claim_flags_missing_or_invalid", path)
        return
    unexpected = sorted(set(value) - set(NON_CLAIM_FLAGS))
    if unexpected:
        add(blockers, "non_claim_flags_unexpected_keys", path, keys=unexpected)
    missing = sorted(set(NON_CLAIM_FLAGS) - set(value))
    if missing:
        add(blockers, "non_claim_flags_missing_keys", path, keys=missing)
    for key in required_true_flags:
        if value.get(key) is not True:
            add(blockers, "non_claim_flag_not_true", f"{path}.{key}", value=value.get(key))
    for key in required_false_flags:
        if value.get(key) is not False:
            add(blockers, "non_claim_flag_not_false", f"{path}.{key}", value=value.get(key))


def validate_target(
    target: Any,
    blockers: list[dict[str, Any]],
    path: str,
    *,
    expected_target: dict[str, str] | None = None,
    reason_prefix: str = "target",
) -> dict[str, str] | None:
    if not isinstance(target, dict):
        add(blockers, f"{reason_prefix}_missing_or_invalid", path, value=target)
        return None
    allowed_keys = {"instance", "map"}
    extra_keys = sorted(set(target) - allowed_keys)
    if extra_keys:
        add(blockers, f"{reason_prefix}_unexpected_keys", path, keys=extra_keys)
    instance = target.get("instance")
    map_name = target.get("map")
    if not isinstance(instance, str) or not SAFE_TOKEN_RE.fullmatch(instance):
        add(blockers, f"{reason_prefix}_instance_invalid", f"{path}.instance", value=instance)
    if not isinstance(map_name, str) or not SAFE_MAP_RE.fullmatch(map_name):
        add(blockers, f"{reason_prefix}_map_invalid", f"{path}.map", value=map_name)
    if not isinstance(instance, str) or not isinstance(map_name, str):
        return None
    normalized = {"instance": instance, "map": map_name}
    if expected_target is not None and normalized != expected_target:
        add(blockers, f"{reason_prefix}_expected_target_mismatch", path, expected=expected_target, actual=normalized)
    return normalized


def validate_target_binding_id(
    value: Any,
    blockers: list[dict[str, Any]],
    path: str,
    *,
    expected_target: dict[str, str] | None,
    reason_prefix: str = "target_binding_id",
) -> None:
    if not isinstance(value, str):
        add(blockers, f"{reason_prefix}_missing_or_invalid", path, value=value)
        return
    if expected_target is None:
        return
    expected = target_binding_id(expected_target)
    if value != expected:
        add(blockers, f"{reason_prefix}_mismatch", path, expected=expected, actual=value)


def validate_target_binding(
    binding: Any,
    blockers: list[dict[str, Any]],
    path: str,
    *,
    expected_target: dict[str, str] | None,
    expected_source: str = "operator_cli_plan_target",
    reason_prefix: str = "target_binding",
) -> dict[str, str] | None:
    if not isinstance(binding, dict):
        add(blockers, f"{reason_prefix}_missing_or_invalid", path, value=binding)
        return None
    allowed_keys = {
        "source",
        "binding_id",
        "instance",
        "map",
        "all_artifacts_must_match",
        "mismatched_target_rejects_pack",
    }
    extra_keys = sorted(set(binding) - allowed_keys)
    if extra_keys:
        add(blockers, f"{reason_prefix}_unexpected_keys", path, keys=extra_keys)
    if binding.get("source") != expected_source:
        add(blockers, f"{reason_prefix}_source_mismatch", f"{path}.source", expected=expected_source, actual=binding.get("source"))
    validate_target_binding_id(
        binding.get("binding_id"),
        blockers,
        f"{path}.binding_id",
        expected_target=expected_target,
        reason_prefix=f"{reason_prefix}_binding_id",
    )
    if binding.get("all_artifacts_must_match") is not True:
        add(blockers, f"{reason_prefix}_all_artifacts_must_match_not_true", f"{path}.all_artifacts_must_match", value=binding.get("all_artifacts_must_match"))
    if binding.get("mismatched_target_rejects_pack") is not True:
        add(blockers, f"{reason_prefix}_mismatched_target_rejects_pack_not_true", f"{path}.mismatched_target_rejects_pack", value=binding.get("mismatched_target_rejects_pack"))
    return validate_target(
        {"instance": binding.get("instance"), "map": binding.get("map")},
        blockers,
        path,
        expected_target=expected_target,
        reason_prefix=reason_prefix,
    )


def validate_approved_runtime_window_binding(
    value: Any,
    blockers: list[dict[str, Any]],
    path: str,
    *,
    expected_target: dict[str, str] | None,
    reason_prefix: str = "approved_runtime_window_binding",
) -> None:
    if not isinstance(value, dict):
        add(blockers, f"{reason_prefix}_missing_or_invalid", path, value=value)
        return
    if expected_target is None:
        add(blockers, f"{reason_prefix}_expected_target_missing", path)
        return
    expected = approved_runtime_window_binding(expected_target)
    extra_keys = sorted(set(value) - set(expected))
    missing_keys = sorted(set(expected) - set(value))
    if extra_keys:
        add(blockers, f"{reason_prefix}_unexpected_keys", path, keys=extra_keys)
    if missing_keys:
        add(blockers, f"{reason_prefix}_missing_keys", path, keys=missing_keys)
    if value != expected:
        add(blockers, f"{reason_prefix}_mismatch", path, expected=expected, actual=value)
    validate_target_binding(
        value.get("target_binding"),
        blockers,
        f"{path}.target_binding",
        expected_target=expected_target,
        reason_prefix=f"{reason_prefix}_target_binding",
    )
    validate_target_binding_id(
        value.get("target_binding_id"),
        blockers,
        f"{path}.target_binding_id",
        expected_target=expected_target,
        reason_prefix=f"{reason_prefix}_target_binding_id",
    )
    for key in (
        "same_window_as_player_principal_lifecycle",
        "side_surfaces_must_share_primary_window",
        "candidate_artifacts_must_match_window",
        "separate_operator_approval_required",
    ):
        if value.get(key) is not True:
            add(blockers, f"{reason_prefix}_true_flag_missing", f"{path}.{key}", value=value.get(key))
    for key in (
        "pack_authorizes_window",
        "window_substitution_allowed",
        "side_lane_window_substitution_allowed",
        "counts_as_runtime_evidence",
        "counts_as_sdk_progress",
        "counts_as_p0_progress",
    ):
        if value.get(key) is not False:
            add(blockers, f"{reason_prefix}_false_flag_overclaim", f"{path}.{key}", value=value.get(key))


def validate_lifecycle_correlation_field_ids(
    value: Any,
    blockers: list[dict[str, Any]],
    path: str,
    *,
    reason_prefix: str,
) -> None:
    if value != EXPECTED_LIFECYCLE_CORRELATION_FIELD_IDS:
        add(
            blockers,
            f"{reason_prefix}_field_ids_mismatch",
            path,
            expected=EXPECTED_LIFECYCLE_CORRELATION_FIELD_IDS,
            actual=value,
        )
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        add(blockers, f"{reason_prefix}_field_ids_invalid", path, value=value)
        return
    duplicates = sorted({item for item in value if value.count(item) > 1})
    if duplicates:
        add(blockers, f"{reason_prefix}_field_ids_duplicate", path, duplicates=duplicates)
    missing = sorted(set(LIFECYCLE_CORRELATION_FIELD_IDS) - set(value))
    if missing:
        add(blockers, f"{reason_prefix}_required_fields_missing", path, fields=missing)


def validate_lifecycle_correlation_metadata(
    value: Any,
    blockers: list[dict[str, Any]],
    path: str,
    *,
    expected_target: dict[str, str] | None,
    reason_prefix: str = "lifecycle_correlation_metadata",
) -> None:
    if not isinstance(value, dict):
        add(blockers, f"{reason_prefix}_missing_or_invalid", path, value=value)
        return
    if expected_target is None:
        add(blockers, f"{reason_prefix}_expected_target_missing", path)
        return
    expected = lifecycle_correlation_metadata(expected_target)
    extra_keys = sorted(set(value) - set(expected))
    missing_keys = sorted(set(expected) - set(value))
    if extra_keys:
        add(blockers, f"{reason_prefix}_unexpected_keys", path, keys=extra_keys)
    if missing_keys:
        add(blockers, f"{reason_prefix}_missing_keys", path, keys=missing_keys)
    if value != expected:
        add(blockers, f"{reason_prefix}_mismatch", path, expected=expected, actual=value)
    if value.get("schema") != LIFECYCLE_CORRELATION_SCHEMA:
        add(blockers, f"{reason_prefix}_schema_mismatch", f"{path}.schema", value=value.get("schema"))
    if value.get("status") != LIFECYCLE_CORRELATION_STATUS:
        add(blockers, f"{reason_prefix}_status_mismatch", f"{path}.status", value=value.get("status"))
    validate_target(
        value.get("target"),
        blockers,
        f"{path}.target",
        expected_target=expected_target,
        reason_prefix=f"{reason_prefix}_target",
    )
    validate_target_binding(
        value.get("target_binding"),
        blockers,
        f"{path}.target_binding",
        expected_target=expected_target,
        reason_prefix=f"{reason_prefix}_target_binding",
    )
    validate_target_binding_id(
        value.get("target_binding_id"),
        blockers,
        f"{path}.target_binding_id",
        expected_target=expected_target,
        reason_prefix=f"{reason_prefix}_target_binding_id",
    )
    validate_approved_runtime_window_binding(
        value.get("approved_runtime_window_binding"),
        blockers,
        f"{path}.approved_runtime_window_binding",
        expected_target=expected_target,
        reason_prefix=f"{reason_prefix}_approved_runtime_window_binding",
    )
    validate_lifecycle_correlation_field_ids(
        value.get("field_ids"),
        blockers,
        f"{path}.field_ids",
        reason_prefix=reason_prefix,
    )
    if value.get("lifecycle_phase_anchor_allowed_values") != list(
        LIFECYCLE_PHASE_ANCHOR_VALUES
    ):
        add(
            blockers,
            f"{reason_prefix}_phase_anchor_values_mismatch",
            f"{path}.lifecycle_phase_anchor_allowed_values",
            value=value.get("lifecycle_phase_anchor_allowed_values"),
        )
    if value.get("primary_lifecycle_event_reference_allowed_values") != list(
        PRIMARY_LIFECYCLE_EVENT_REFERENCE_VALUES
    ):
        add(
            blockers,
            f"{reason_prefix}_event_reference_values_mismatch",
            f"{path}.primary_lifecycle_event_reference_allowed_values",
            value=value.get("primary_lifecycle_event_reference_allowed_values"),
        )
    instructions = value.get("instructions")
    if not isinstance(instructions, list) or len(instructions) < 3:
        add(blockers, f"{reason_prefix}_instructions_missing", f"{path}.instructions", value=instructions)
    else:
        joined = " ".join(item for item in instructions if isinstance(item, str))
        for token in (
            "side_lane_correlation_id",
            "primary_lifecycle_phase_anchor",
            "raw log lines",
            "never count",
        ):
            if token not in joined:
                add(
                    blockers,
                    f"{reason_prefix}_instruction_token_missing",
                    f"{path}.instructions",
                    token=token,
                )
    for key in (
        "same_approved_runtime_window_required",
        "exact_target_binding_required",
        "blank_by_default",
        "redacted_metadata_only",
        "candidate_only",
        "non_evidence",
        "metadata_only",
    ):
        if value.get(key) is not True:
            add(blockers, f"{reason_prefix}_true_flag_missing", f"{path}.{key}", value=value.get(key))
    for key in (
        "raw_player_text_retention_allowed",
        "raw_player_text_capture_allowed",
        "raw_chat_payload_capture_allowed",
        "private_player_data_retention_allowed",
        "secrets_or_webhook_retention_allowed",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_progress",
        "counts_as_p0_progress",
        "clears_approved_runtime_evidence_missing",
        "runtime_ready",
        "public_sdk_ready",
        "stable_sdk_ready",
    ):
        if value.get(key) is not False:
            add(blockers, f"{reason_prefix}_false_flag_overclaim", f"{path}.{key}", value=value.get(key))


def validate_operator_tester_action_metadata(
    value: Any,
    surface: dict[str, Any],
    blockers: list[dict[str, Any]],
    path: str,
    *,
    expected_target: dict[str, str] | None,
    reason_prefix: str = "surface_operator_tester_action_metadata",
) -> None:
    if not isinstance(value, dict):
        add(blockers, f"{reason_prefix}_missing_or_invalid", path, value=value)
        return
    surface_id = surface.get("id")
    expected_surface = EXPECTED_SURFACE_BY_ID.get(surface_id) if isinstance(surface_id, str) else None
    if expected_target is None or expected_surface is None:
        add(blockers, f"{reason_prefix}_expected_binding_missing", path, surface=surface_id)
        return
    expected = operator_tester_action_metadata(
        expected_surface,
        expected_target,
        side_lane=surface_id != "player_principal_lifecycle",
    )
    expected = attach_source_metadata(expected, expected_target)
    extra_keys = sorted(set(value) - set(expected))
    missing_keys = sorted(set(expected) - set(value))
    if extra_keys:
        add(blockers, f"{reason_prefix}_unexpected_keys", path, keys=extra_keys)
    if missing_keys:
        add(blockers, f"{reason_prefix}_missing_keys", path, keys=missing_keys)
    if value != expected:
        add(blockers, f"{reason_prefix}_mismatch", path, expected=expected, actual=value)
    validate_approved_runtime_window_binding(
        value.get("approved_runtime_window_binding"),
        blockers,
        f"{path}.approved_runtime_window_binding",
        expected_target=expected_target,
        reason_prefix=f"{reason_prefix}_approved_runtime_window_binding",
    )
    validate_lifecycle_correlation_metadata(
        value.get("lifecycle_correlation_metadata"),
        blockers,
        f"{path}.lifecycle_correlation_metadata",
        expected_target=expected_target,
        reason_prefix=f"{reason_prefix}_lifecycle_correlation_metadata",
    )
    validate_lifecycle_correlation_field_ids(
        value.get("correlation_field_ids"),
        blockers,
        f"{path}.correlation_field_ids",
        reason_prefix=f"{reason_prefix}_correlation",
    )
    for key in (
        "same_approved_runtime_window_required",
        "exact_approved_runtime_window_required",
        "same_instance_and_map_required",
        "separate_operator_approval_required_before_collection",
        "operator_must_record_approval_receipt",
        "tester_must_stay_on_bound_target",
        "correlation_metadata_required",
        "correlation_metadata_non_evidence",
        "candidate_observation_only",
        "non_evidence_until_checker_acceptance",
        "no_restart_required",
        "operator_actions_do_not_require_restart",
        "tester_actions_do_not_require_restart",
        "no_marker_or_env_change_required",
    ):
        if value.get(key) is not True:
            add(blockers, f"{reason_prefix}_true_flag_missing", f"{path}.{key}", value=value.get(key))
    expected_side_lane = surface_id != "player_principal_lifecycle"
    for key in ("optional_parallel_candidate_observation", "side_lane"):
        if value.get(key) is not expected_side_lane:
            add(
                blockers,
                f"{reason_prefix}_side_lane_flag_mismatch",
                f"{path}.{key}",
                expected=expected_side_lane,
                actual=value.get(key),
            )
    for key in (
        "substitution_allowed",
        "raw_player_text_retention_allowed",
        "raw_player_text_capture_allowed",
        "raw_chat_payload_capture_allowed",
        "private_player_data_retention_allowed",
        "secrets_or_webhook_retention_allowed",
        "counts_as_runtime_evidence",
        "counts_as_sdk_progress",
        "counts_as_p0_progress",
        "pack_authorizes_restart",
        "restart_required",
        "server_restart_required",
        "operator_action_requires_restart",
        "tester_action_requires_restart",
        "marker_or_env_change_required",
    ):
        if value.get(key) is not False:
            add(blockers, f"{reason_prefix}_false_flag_overclaim", f"{path}.{key}", value=value.get(key))
    if value.get("action_boundary") != NO_RESTART_ACTION_BOUNDARY:
        add(
            blockers,
            f"{reason_prefix}_action_boundary_mismatch",
            f"{path}.action_boundary",
            expected=NO_RESTART_ACTION_BOUNDARY,
            actual=value.get("action_boundary"),
        )
    if value.get("operator_next_action") != value.get("lead_next_action"):
        add(
            blockers,
            f"{reason_prefix}_operator_next_action_mismatch",
            f"{path}.operator_next_action",
            expected=value.get("lead_next_action"),
            actual=value.get("operator_next_action"),
        )
    for key in ("operator_action", "tester_action", "operator_next_action", "lead_next_action", "tester_brief"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            add(blockers, f"{reason_prefix}_text_missing", f"{path}.{key}", value=value.get(key))


def validate_no_restart_action_fields(
    value: dict[str, Any],
    blockers: list[dict[str, Any]],
    path: str,
    *,
    reason_prefix: str,
    text_keys: tuple[str, ...] = (),
    list_keys: tuple[str, ...] = (),
) -> None:
    expected_flags = no_restart_action_boundary()
    for key, expected in expected_flags.items():
        actual = value.get(key)
        if actual is not expected:
            reason = (
                f"{reason_prefix}_true_flag_missing"
                if expected is True
                else f"{reason_prefix}_false_flag_overclaim"
            )
            add(blockers, reason, f"{path}.{key}", expected=expected, actual=actual)
    if value.get("action_boundary") != NO_RESTART_ACTION_BOUNDARY:
        add(
            blockers,
            f"{reason_prefix}_action_boundary_mismatch",
            f"{path}.action_boundary",
            expected=NO_RESTART_ACTION_BOUNDARY,
            actual=value.get("action_boundary"),
        )
    for key in text_keys:
        if not isinstance(value.get(key), str) or not value[key].strip():
            add(blockers, f"{reason_prefix}_text_missing", f"{path}.{key}", value=value.get(key))
    for key in list_keys:
        items = value.get(key)
        if not isinstance(items, list) or not items or not all(isinstance(item, str) and item.strip() for item in items):
            add(blockers, f"{reason_prefix}_action_list_missing", f"{path}.{key}", value=items)


def validate_single_player_route_constraints(
    value: Any,
    blockers: list[dict[str, Any]],
    path: str,
    *,
    reason_prefix: str,
) -> None:
    if not isinstance(value, dict):
        add(blockers, f"{reason_prefix}_missing_or_invalid", path, value=value)
        return
    expected = EXPECTED_SINGLE_PLAYER_ROUTE_CONSTRAINTS
    extra_keys = sorted(set(value) - set(expected))
    missing_keys = sorted(set(expected) - set(value))
    if extra_keys:
        add(blockers, f"{reason_prefix}_unexpected_keys", path, keys=extra_keys)
    if missing_keys:
        add(blockers, f"{reason_prefix}_missing_keys", path, keys=missing_keys)
    if value != expected:
        add(blockers, f"{reason_prefix}_mismatch", path, expected=expected, actual=value)
    for key, expected_value in expected.items():
        if value.get(key) is not expected_value:
            reason = (
                f"{reason_prefix}_true_flag_missing"
                if expected_value is True
                else f"{reason_prefix}_false_flag_overclaim"
            )
            add(
                blockers,
                reason,
                f"{path}.{key}",
                expected=expected_value,
                actual=value.get(key),
            )


def validate_non_substitution_flags(value: Any, blockers: list[dict[str, Any]], path: str) -> None:
    if not isinstance(value, dict):
        add(blockers, "non_substitution_flags_missing_or_invalid", path, value=value)
        return
    extra_keys = sorted(set(value) - set(NON_SUBSTITUTION_FLAGS))
    missing_keys = sorted(set(NON_SUBSTITUTION_FLAGS) - set(value))
    if extra_keys:
        add(blockers, "non_substitution_flags_unexpected_keys", path, keys=extra_keys)
    if missing_keys:
        add(blockers, "non_substitution_flags_missing_keys", path, keys=missing_keys)
    for key in sorted(NON_SUBSTITUTION_FLAGS):
        if value.get(key) is not False:
            add(blockers, "non_substitution_flag_not_false", f"{path}.{key}", value=value.get(key))


def validate_artifact_intake_constraints(
    constraints: Any,
    blockers: list[dict[str, Any]],
    path: str,
) -> None:
    if not isinstance(constraints, dict):
        add(blockers, "artifact_intake_constraints_missing_or_invalid", path, value=constraints)
        return
    expected = set(ARTIFACT_INTAKE_CONSTRAINTS)
    extra_keys = sorted(set(constraints) - expected)
    missing_keys = sorted(expected - set(constraints))
    if extra_keys:
        add(blockers, "artifact_intake_constraints_unexpected_keys", path, keys=extra_keys)
    if missing_keys:
        add(blockers, "artifact_intake_constraints_missing_keys", path, keys=missing_keys)
    for key in sorted(expected):
        if constraints.get(key) is not True:
            add(blockers, "artifact_intake_constraint_not_true", f"{path}.{key}", value=constraints.get(key))


def validate_redaction_policy(policy: Any, blockers: list[dict[str, Any]], path: str) -> None:
    if not isinstance(policy, dict):
        add(blockers, "redaction_policy_missing_or_invalid", path, value=policy)
        return
    expected = redaction_policy()
    if policy != expected:
        add(blockers, "redaction_policy_mismatch", path, expected=expected, actual=policy)
    if policy.get("required") is not True:
        add(blockers, "redaction_policy_required_not_true", f"{path}.required", value=policy.get("required"))
    must_redact = policy.get("must_redact")
    if not isinstance(must_redact, list) or set(must_redact) != set(REDACTION_POLICY["must_redact"]):
        add(blockers, "redaction_policy_must_redact_mismatch", f"{path}.must_redact", value=must_redact)
    for key in ("retain_only_redacted_offline_copies", "checker_inputs_must_be_redacted"):
        if policy.get(key) is not True:
            add(blockers, "redaction_policy_constraint_not_true", f"{path}.{key}", value=policy.get(key))


def validate_text_privacy_boundary(value: Any, blockers: list[dict[str, Any]], path: str) -> None:
    if not isinstance(value, dict):
        add(blockers, "text_privacy_boundary_missing_or_invalid", path, value=value)
        return
    if value != EXPECTED_TEXT_PRIVACY_BOUNDARY:
        add(
            blockers,
            "text_privacy_boundary_mismatch",
            path,
            expected=EXPECTED_TEXT_PRIVACY_BOUNDARY,
            actual=value,
        )
    for key in (
        "redacted_metadata_only",
        "redaction_required_before_checker_intake",
    ):
        if value.get(key) is not True:
            add(blockers, "text_privacy_boundary_true_flag_missing", f"{path}.{key}", value=value.get(key))
    for key in (
        "raw_player_text_retention_allowed",
        "raw_player_text_capture_allowed",
        "raw_chat_payload_capture_allowed",
        "private_player_data_retention_allowed",
        "secrets_or_webhook_retention_allowed",
    ):
        if value.get(key) is not False:
            add(blockers, "text_privacy_boundary_false_flag_overclaim", f"{path}.{key}", value=value.get(key))
    if value.get("boundary") != EXPECTED_TEXT_PRIVACY_BOUNDARY["boundary"]:
        add(blockers, "text_privacy_boundary_text_mismatch", f"{path}.boundary", value=value.get("boundary"))
    if set(value.get("must_redact", [])) != set(REDACTION_POLICY["must_redact"]):
        add(blockers, "text_privacy_boundary_must_redact_mismatch", f"{path}.must_redact", value=value.get("must_redact"))


def validate_beta_capture_interaction_boundary(
    value: Any,
    blockers: list[dict[str, Any]],
    path: str,
) -> None:
    if not isinstance(value, dict):
        add(blockers, "beta_capture_interaction_boundary_missing_or_invalid", path, value=value)
        return
    if value != EXPECTED_BETA_CAPTURE_INTERACTION_BOUNDARY:
        add(
            blockers,
            "beta_capture_interaction_boundary_mismatch",
            path,
            expected=EXPECTED_BETA_CAPTURE_INTERACTION_BOUNDARY,
            actual=value,
        )
    for key in (
        "accepted_copied_sibling_set_required_before_runtime_claims",
        "accepted_copied_sibling_sets_required_for_runtime_evidence",
        "beta_notice_is_coordination_only",
        "button_clicks_are_coordination_only",
        "public_reachability_is_non_evidence",
        "multi_surface_capture_plan_is_candidate_only",
    ):
        if value.get(key) is not True:
            add(
                blockers,
                "beta_capture_interaction_boundary_true_flag_missing",
                f"{path}.{key}",
                value=value.get(key),
            )
    false_flags = value.get("non_claim_flags")
    if not isinstance(false_flags, dict):
        add(
            blockers,
            "beta_capture_interaction_boundary_non_claim_flags_missing",
            f"{path}.non_claim_flags",
            value=false_flags,
        )
        false_flags = {}
    for key, expected in EXPECTED_BETA_CAPTURE_INTERACTION_BOUNDARY.items():
        if isinstance(expected, bool) and expected is False and value.get(key) is not False:
            add(
                blockers,
                "beta_capture_interaction_boundary_false_flag_overclaim",
                f"{path}.{key}",
                value=value.get(key),
            )
    expected_false_flags = EXPECTED_BETA_CAPTURE_INTERACTION_BOUNDARY["non_claim_flags"]
    for key, expected in expected_false_flags.items():
        if false_flags.get(key) is not expected:
            add(
                blockers,
                "beta_capture_interaction_boundary_non_claim_flag_overclaim",
                f"{path}.non_claim_flags.{key}",
                value=false_flags.get(key),
            )


def validate_capture_artifact_path_template(
    path_template: Any,
    blockers: list[dict[str, Any]],
    path: str,
) -> None:
    if not isinstance(path_template, str):
        add(blockers, "capture_artifact_path_template_invalid", path, value=path_template)
        return
    template_path = PurePosixPath(path_template)
    parts = template_path.parts
    if template_path.is_absolute() or ".." in parts or "\\" in path_template:
        add(blockers, "capture_artifact_path_template_unsafe", path, value=path_template)
    if len(parts) < 2 or parts[0] != ARTIFACT_TEMPLATE_ROOT_COMPONENT:
        add(blockers, "capture_artifact_path_template_root_mismatch", path, value=path_template)
    if any(fragment in path_template for fragment in FORBIDDEN_LIVE_PATH_FRAGMENTS):
        add(blockers, "capture_artifact_path_template_live_path_fragment", path, value=path_template)


def validate_candidate_only_metadata(value: Any, blockers: list[dict[str, Any]], path: str) -> None:
    if not isinstance(value, dict):
        add(blockers, "candidate_only_metadata_missing_or_invalid", path, value=value)
        return
    comparable_value = {
        key: child
        for key, child in value.items()
        if key not in {"source_metadata", "source_metadata_required"}
    }
    comparable_expected = {
        key: child
        for key, child in EXPECTED_CANDIDATE_ONLY_METADATA.items()
        if key not in {"source_metadata", "source_metadata_required"}
    }
    if comparable_value != comparable_expected:
        add(
            blockers,
            "candidate_only_metadata_mismatch",
            path,
            expected=comparable_expected,
            actual=comparable_value,
        )
    validate_non_substitution_flags(
        value.get("non_substitution_flags"),
        blockers,
        f"{path}.non_substitution_flags",
    )


def validate_source_metadata(
    value: Any,
    blockers: list[dict[str, Any]],
    path: str,
    *,
    expected_target: dict[str, str] | None,
) -> None:
    if not isinstance(value, dict):
        add(blockers, "source_metadata_missing_or_invalid", path, value=value)
        return
    expected_keys = set(source_metadata_template(expected_target or {"instance": "unknown", "map": "unknown"}))
    extra_keys = sorted(set(value) - expected_keys)
    missing_keys = sorted(expected_keys - set(value))
    if extra_keys:
        add(blockers, "source_metadata_unexpected_keys", path, keys=extra_keys)
    if missing_keys:
        add(blockers, "source_metadata_missing_keys", path, keys=missing_keys)
    if value.get("schema") != SOURCE_METADATA_SCHEMA:
        add(blockers, "source_metadata_schema_mismatch", f"{path}.schema", value=value.get("schema"))
    if value.get("status") != SOURCE_METADATA_STATUS:
        add(blockers, "source_metadata_status_mismatch", f"{path}.status", value=value.get("status"))
    if value.get("field_ids") != list(SOURCE_METADATA_FIELD_IDS):
        add(blockers, "source_metadata_field_ids_mismatch", f"{path}.field_ids", value=value.get("field_ids"))
    if value.get("instructions") != list(SOURCE_METADATA_INSTRUCTIONS):
        add(blockers, "source_metadata_instructions_mismatch", f"{path}.instructions", value=value.get("instructions"))
    if value.get("required") is not True or value.get("source_metadata_required") is not True:
        add(blockers, "source_metadata_required_flag_missing", path, value=value)
    if value.get("source_required_for_checker_intake") is not True:
        add(blockers, "source_metadata_checker_intake_required_missing", f"{path}.source_required_for_checker_intake", value=value.get("source_required_for_checker_intake"))
    validate_target(
        value.get("target"),
        blockers,
        f"{path}.target",
        expected_target=expected_target,
        reason_prefix="source_metadata_target",
    )
    validate_target_binding(
        value.get("target_binding"),
        blockers,
        f"{path}.target_binding",
        expected_target=expected_target,
        reason_prefix="source_metadata_target_binding",
    )
    validate_target_binding_id(
        value.get("target_binding_id"),
        blockers,
        f"{path}.target_binding_id",
        expected_target=expected_target,
        reason_prefix="source_metadata_target_binding_id",
    )
    validate_approved_runtime_window_binding(
        value.get("approved_runtime_window_binding"),
        blockers,
        f"{path}.approved_runtime_window_binding",
        expected_target=expected_target,
        reason_prefix="source_metadata_approved_runtime_window_binding",
    )
    for key in (
        "copy_to_offline_workspace_required",
        "redaction_required",
    ):
        if value.get(key) is not True:
            add(blockers, "source_metadata_true_flag_missing", f"{path}.{key}", value=value.get(key))
    for key in (
        "source_present",
        "source_material_present",
        "source_material_counts_as_evidence",
        "source_accepted",
        "source_ready",
        "live_server_path_allowed",
        "discord_or_rcon_source_allowed",
        "raw_player_text_retention_allowed",
        "raw_chat_payload_capture_allowed",
        "private_player_data_retention_allowed",
        "secrets_or_webhook_retention_allowed",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_progress",
        "counts_as_p0_progress",
        "clears_approved_runtime_evidence_missing",
        "runtime_ready",
        "public_sdk_ready",
        "stable_sdk_ready",
    ):
        if value.get(key) is not False:
            add(blockers, "source_metadata_false_flag_overclaim", f"{path}.{key}", value=value.get(key))


def validate_explicit_source_metadata(
    value: Any,
    blockers: list[dict[str, Any]],
    path: str,
    *,
    expected_target: dict[str, str] | None,
    inside_source_metadata: bool = False,
) -> None:
    if isinstance(value, dict):
        if not inside_source_metadata and (
            "source_present" in value
            or "source_material_present" in value
            or value.get("source_metadata_required") is True
        ):
            if value.get("source_metadata_required") is not True:
                add(blockers, "source_metadata_required_flag_missing", f"{path}.source_metadata_required", value=value.get("source_metadata_required"))
            validate_source_metadata(
                value.get("source_metadata"),
                blockers,
                f"{path}.source_metadata",
                expected_target=expected_target,
            )
        for key, child in value.items():
            if key in {
                "artifact_intake_constraints",
                "candidate_only_metadata",
                "no_flood_capture_policy",
                "non_claim_flags",
                "non_substitution_flags",
                "parallel_capture_boundary",
                "player_principal_window_composition",
                "redaction_policy",
                "single_player_route_constraints",
                "source_metadata",
                "text_privacy_boundary",
            }:
                continue
            validate_explicit_source_metadata(
                child,
                blockers,
                f"{path}.{key}",
                expected_target=expected_target,
                inside_source_metadata=inside_source_metadata,
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_explicit_source_metadata(
                child,
                blockers,
                f"{path}[{index}]",
                expected_target=expected_target,
                inside_source_metadata=inside_source_metadata,
            )


def validate_parallel_capture_boundary(value: Any, blockers: list[dict[str, Any]], path: str) -> None:
    if not isinstance(value, dict):
        add(blockers, "parallel_capture_boundary_missing_or_invalid", path, value=value)
        return
    expected_keys = set(PARALLEL_CAPTURE_BOUNDARY)
    extra_keys = sorted(set(value) - expected_keys)
    missing_keys = sorted(expected_keys - set(value))
    if extra_keys:
        add(blockers, "parallel_capture_boundary_unexpected_keys", path, keys=extra_keys)
    if missing_keys:
        add(blockers, "parallel_capture_boundary_missing_keys", path, keys=missing_keys)
    if value != EXPECTED_PARALLEL_CAPTURE_BOUNDARY:
        add(
            blockers,
            "parallel_capture_boundary_mismatch",
            path,
            expected=EXPECTED_PARALLEL_CAPTURE_BOUNDARY,
            actual=value,
        )
    for key, expected in EXPECTED_PARALLEL_CAPTURE_BOUNDARY.items():
        if value.get(key) is not expected:
            add(
                blockers,
                "parallel_capture_boundary_flag_mismatch",
                f"{path}.{key}",
                expected=expected,
                actual=value.get(key),
            )


def validate_player_principal_window_composition(
    value: Any,
    blockers: list[dict[str, Any]],
    path: str,
) -> None:
    if not isinstance(value, dict):
        add(blockers, "player_principal_window_composition_missing_or_invalid", path, value=value)
        return
    expected_keys = set(PLAYER_PRINCIPAL_WINDOW_COMPOSITION)
    extra_keys = sorted(set(value) - expected_keys)
    missing_keys = sorted(expected_keys - set(value))
    if extra_keys:
        add(blockers, "player_principal_window_composition_unexpected_keys", path, keys=extra_keys)
    if missing_keys:
        add(blockers, "player_principal_window_composition_missing_keys", path, keys=missing_keys)
    if value != EXPECTED_PLAYER_PRINCIPAL_WINDOW_COMPOSITION:
        add(
            blockers,
            "player_principal_window_composition_mismatch",
            path,
            expected=EXPECTED_PLAYER_PRINCIPAL_WINDOW_COMPOSITION,
            actual=value,
        )
    for key, expected in EXPECTED_PLAYER_PRINCIPAL_WINDOW_COMPOSITION.items():
        if isinstance(expected, bool) and value.get(key) is not expected:
            reason = (
                "player_principal_window_composition_false_flag_overclaim"
                if expected is False
                else "player_principal_window_composition_true_flag_missing"
            )
            add(
                blockers,
                reason,
                f"{path}.{key}",
                expected=expected,
                actual=value.get(key),
            )


def validate_next_action_groups(
    value: Any,
    expected: Any,
    blockers: list[dict[str, Any]],
    path: str,
) -> None:
    if not isinstance(value, list):
        add(blockers, "next_action_groups_missing_or_invalid", path, value=value)
        return
    if value != expected:
        add(blockers, "next_action_groups_mismatch", path, expected=expected, actual=value)
        return
    seen: list[str] = []
    for group_index, group in enumerate(value):
        if not isinstance(group, dict):
            add(blockers, "next_action_group_entry_invalid", f"{path}[{group_index}]", value=group)
            continue
        if group.get("candidate_only") is not True or group.get("non_evidence") is not True:
            add(blockers, "next_action_group_candidate_only_metadata_missing", f"{path}[{group_index}]")
        validate_parallel_capture_boundary(
            group.get("parallel_capture_boundary"),
            blockers,
            f"{path}[{group_index}].parallel_capture_boundary",
        )
        validate_player_principal_window_composition(
            group.get("player_principal_window_composition"),
            blockers,
            f"{path}[{group_index}].player_principal_window_composition",
        )
        validate_non_substitution_flags(
            group.get("non_substitution_flags"),
            blockers,
            f"{path}[{group_index}].non_substitution_flags",
        )
        expected_optional = group.get("id") != "primary_player_principal_gate"
        expected_role = (
            "optional_parallel_candidate_observations"
            if expected_optional
            else "primary_player_principal_lifecycle_window"
        )
        if group.get("composition_role") != expected_role:
            add(
                blockers,
                "next_action_group_composition_role_mismatch",
                f"{path}[{group_index}].composition_role",
                expected=expected_role,
                actual=group.get("composition_role"),
            )
        if group.get("optional_parallel_candidate_observations") is not expected_optional:
            add(
                blockers,
                "next_action_group_optional_parallel_candidate_observations_mismatch",
                f"{path}[{group_index}].optional_parallel_candidate_observations",
                expected=expected_optional,
                actual=group.get("optional_parallel_candidate_observations"),
            )
        if not isinstance(group.get("beta_session_objective"), str):
            add(blockers, "next_action_group_beta_session_objective_missing", f"{path}[{group_index}].beta_session_objective")
        for key in (
            "counts_as_approved_runtime_evidence",
            "counts_as_runtime_evidence",
            "counts_as_sdk_progress",
            "counts_as_p0_progress",
            "clears_approved_runtime_evidence_missing",
            "readiness_claim_allowed",
            "downstream_unlock_allowed",
        ):
            if group.get(key) is not False:
                add(blockers, "next_action_group_false_flag_overclaim", f"{path}[{group_index}].{key}", value=group.get(key))
        surface_ids = group.get("surface_ids")
        if isinstance(surface_ids, list):
            seen.extend(surface_id for surface_id in surface_ids if isinstance(surface_id, str))
    duplicates = sorted({surface_id for surface_id in seen if seen.count(surface_id) > 1})
    if duplicates:
        add(blockers, "next_action_groups_duplicate_surface_ids", path, duplicates=duplicates)
    if set(seen) != EXPECTED_SURFACES:
        add(blockers, "next_action_groups_surface_set_mismatch", path, expected=sorted(EXPECTED_SURFACES), actual=sorted(seen))


def validate_broad_beta_capture_pack_path(
    value: Any,
    expected: Any,
    blockers: list[dict[str, Any]],
    path: str,
    *,
    expected_target: dict[str, str] | None,
) -> None:
    if not isinstance(value, dict):
        add(blockers, "broad_beta_capture_pack_path_missing_or_invalid", path, value=value)
        return
    if not isinstance(expected, dict):
        add(blockers, "broad_beta_capture_pack_path_expected_missing", path, expected=expected)
        return
    if value != expected:
        add(
            blockers,
            "broad_beta_capture_pack_path_mismatch",
            path,
            expected=expected,
            actual=value,
        )
    if value.get("id") != BROAD_BETA_CAPTURE_PACK_PATH_ID:
        add(
            blockers,
            "broad_beta_capture_pack_path_id_mismatch",
            f"{path}.id",
            expected=BROAD_BETA_CAPTURE_PACK_PATH_ID,
            actual=value.get("id"),
        )
    if value.get("surface_ids") != list(BROAD_BETA_CAPTURE_SURFACE_IDS):
        add(
            blockers,
            "broad_beta_capture_pack_path_surface_ids_mismatch",
            f"{path}.surface_ids",
            expected=list(BROAD_BETA_CAPTURE_SURFACE_IDS),
            actual=value.get("surface_ids"),
        )
    if value.get("action_group_ids") != list(BROAD_BETA_CAPTURE_ACTION_GROUP_IDS):
        add(
            blockers,
            "broad_beta_capture_pack_path_action_group_ids_mismatch",
            f"{path}.action_group_ids",
            expected=list(BROAD_BETA_CAPTURE_ACTION_GROUP_IDS),
            actual=value.get("action_group_ids"),
        )
    if value.get("status") != "status_only_candidate_capture_path":
        add(blockers, "broad_beta_capture_pack_path_status_mismatch", f"{path}.status", value=value.get("status"))
    if value.get("path_status") != "status_only_candidate_non_evidence":
        add(blockers, "broad_beta_capture_pack_path_status_mismatch", f"{path}.path_status", value=value.get("path_status"))
    for key in (
        "candidate_only",
        "candidate_capture_only",
        "status_only",
        "non_evidence",
        "debug_only",
        "side_lane_non_counting",
        "same_approved_runtime_window_required",
        "artifact_templates_only",
        "copy_to_offline_workspace_before_analysis",
        "redaction_required_before_checker_intake",
        "do_not_read_live_server_paths_from_pack",
        "correlation_metadata_required",
        "correlation_metadata_non_evidence",
        "requires_checker_acceptance",
        "requires_player_principal_triplet",
        "blocked_by_player_principal_evidence",
    ):
        if value.get(key) is not True:
            add(blockers, "broad_beta_capture_pack_path_true_flag_missing", f"{path}.{key}", value=value.get(key))
    for key in (
        "pack_authorizes_player_backed_window",
        "pack_authorizes_runtime_observer",
        "pack_authorizes_marker_or_env_change",
        "pack_authorizes_restart",
        "pack_authorizes_discord",
        "approved_runtime_evidence_present",
        "approved_runtime_evidence_ready",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_progress",
        "counts_as_p0_progress",
        "clears_approved_runtime_evidence_missing",
        "replaces_player_principal_evidence",
        "replaces_player_principal_triplet",
        "substitutes_for_player_principal_lifecycle_evidence",
        "substitutes_for_player_principal_lifecycle_triplet",
        "side_lane_substitutes_for_player_principal_lifecycle_evidence",
        "player_principal_lifecycle_evidence_substitution_allowed",
        "approved_runtime_evidence_substitution_allowed",
        "primary_evidence_substitution_allowed",
        "runtime_ready",
        "public_sdk_ready",
        "stable_sdk_ready",
        "v1_completion_ready",
        "readiness_claim_allowed",
        "downstream_unlock_allowed",
    ):
        if value.get(key) is not False:
            add(blockers, "broad_beta_capture_pack_path_false_flag_overclaim", f"{path}.{key}", value=value.get(key))
    if value.get("current_route_blocker") != CURRENT_ROUTE_BLOCKER:
        add(blockers, "broad_beta_capture_pack_path_route_blocker_mismatch", f"{path}.current_route_blocker", value=value.get("current_route_blocker"))
    if value.get("required_runtime_evidence") != NEXT_REQUIRED_ARTIFACT:
        add(blockers, "broad_beta_capture_pack_path_required_evidence_mismatch", f"{path}.required_runtime_evidence", value=value.get("required_runtime_evidence"))
    if not isinstance(value.get("non_claim"), str) or "does not authorize runtime capture" not in value["non_claim"]:
        add(blockers, "broad_beta_capture_pack_path_non_claim_missing", f"{path}.non_claim", value=value.get("non_claim"))
    validate_target(value.get("target"), blockers, f"{path}.target", expected_target=expected_target, reason_prefix="broad_beta_capture_pack_path_target")
    validate_target_binding(
        value.get("target_binding"),
        blockers,
        f"{path}.target_binding",
        expected_target=expected_target,
        reason_prefix="broad_beta_capture_pack_path_target_binding",
    )
    validate_target_binding_id(
        value.get("target_binding_id"),
        blockers,
        f"{path}.target_binding_id",
        expected_target=expected_target,
        reason_prefix="broad_beta_capture_pack_path_target_binding_id",
    )
    validate_approved_runtime_window_binding(
        value.get("approved_runtime_window_binding"),
        blockers,
        f"{path}.approved_runtime_window_binding",
        expected_target=expected_target,
        reason_prefix="broad_beta_capture_pack_path_approved_runtime_window_binding",
    )
    validate_lifecycle_correlation_metadata(
        value.get("lifecycle_correlation_metadata"),
        blockers,
        f"{path}.lifecycle_correlation_metadata",
        expected_target=expected_target,
        reason_prefix="broad_beta_capture_pack_path_lifecycle_correlation_metadata",
    )
    validate_lifecycle_correlation_field_ids(
        value.get("correlation_field_ids"),
        blockers,
        f"{path}.correlation_field_ids",
        reason_prefix="broad_beta_capture_pack_path_correlation",
    )
    validate_candidate_only_metadata(value.get("candidate_only_metadata"), blockers, f"{path}.candidate_only_metadata")
    validate_parallel_capture_boundary(value.get("parallel_capture_boundary"), blockers, f"{path}.parallel_capture_boundary")
    validate_player_principal_window_composition(
        value.get("player_principal_window_composition"),
        blockers,
        f"{path}.player_principal_window_composition",
    )
    validate_non_substitution_flags(value.get("non_substitution_flags"), blockers, f"{path}.non_substitution_flags")
    check_non_claim_flags(value.get("non_claim_flags"), blockers, f"{path}.non_claim_flags")
    surfaces = value.get("surfaces")
    if not isinstance(surfaces, list):
        add(blockers, "broad_beta_capture_pack_path_surfaces_missing_or_invalid", f"{path}.surfaces", value=surfaces)
    else:
        observed_ids = [surface.get("id") for surface in surfaces if isinstance(surface, dict)]
        if observed_ids != list(BROAD_BETA_CAPTURE_SURFACE_IDS):
            add(
                blockers,
                "broad_beta_capture_pack_path_surface_order_mismatch",
                f"{path}.surfaces",
                expected=list(BROAD_BETA_CAPTURE_SURFACE_IDS),
                actual=observed_ids,
            )
        for index, surface in enumerate(surfaces):
            if not isinstance(surface, dict):
                add(blockers, "broad_beta_capture_pack_path_surface_invalid", f"{path}.surfaces[{index}]", value=surface)
                continue
            validate_lifecycle_correlation_metadata(
                surface.get("lifecycle_correlation_metadata"),
                blockers,
                f"{path}.surfaces[{index}].lifecycle_correlation_metadata",
                expected_target=expected_target,
                reason_prefix="broad_beta_capture_pack_path_surface_lifecycle_correlation_metadata",
            )
            validate_lifecycle_correlation_field_ids(
                surface.get("correlation_field_ids"),
                blockers,
                f"{path}.surfaces[{index}].correlation_field_ids",
                reason_prefix="broad_beta_capture_pack_path_surface_correlation",
            )
            for key in (
                "candidate_only",
                "non_evidence",
                "requires_checker_acceptance",
                "requires_player_principal_triplet",
                "same_approved_runtime_window_required",
                "correlation_metadata_required",
                "correlation_metadata_non_evidence",
            ):
                if surface.get(key) is not True:
                    add(blockers, "broad_beta_capture_pack_path_surface_true_flag_missing", f"{path}.surfaces[{index}].{key}", value=surface.get(key))
            for key in ("counts_as_runtime_evidence", "counts_as_sdk_progress", "counts_as_p0_progress"):
                if surface.get(key) is not False:
                    add(blockers, "broad_beta_capture_pack_path_surface_false_flag_overclaim", f"{path}.surfaces[{index}].{key}", value=surface.get(key))


def validate_parallel_beta_capture_side_lane_matrix(
    value: Any,
    expected: Any,
    blockers: list[dict[str, Any]],
    path: str,
    *,
    expected_target: dict[str, str] | None,
) -> None:
    if not isinstance(value, dict):
        add(blockers, "parallel_beta_capture_side_lane_matrix_missing_or_invalid", path, value=value)
        return
    if not isinstance(expected, dict):
        add(blockers, "parallel_beta_capture_side_lane_matrix_expected_missing", path, expected=expected)
        return
    if value != expected:
        add(
            blockers,
            "parallel_beta_capture_side_lane_matrix_mismatch",
            path,
            expected=expected,
            actual=value,
        )
    if value.get("id") != PARALLEL_BETA_CAPTURE_MATRIX_ID:
        add(
            blockers,
            "parallel_beta_capture_side_lane_matrix_id_mismatch",
            f"{path}.id",
            expected=PARALLEL_BETA_CAPTURE_MATRIX_ID,
            actual=value.get("id"),
        )
    if value.get("surface_ids") != list(PARALLEL_BETA_CAPTURE_SURFACE_IDS):
        add(
            blockers,
            "parallel_beta_capture_side_lane_matrix_surface_ids_mismatch",
            f"{path}.surface_ids",
            expected=list(PARALLEL_BETA_CAPTURE_SURFACE_IDS),
            actual=value.get("surface_ids"),
        )
    if value.get("action_group_ids") != list(PARALLEL_BETA_CAPTURE_ACTION_GROUP_IDS):
        add(
            blockers,
            "parallel_beta_capture_side_lane_matrix_action_group_ids_mismatch",
            f"{path}.action_group_ids",
            expected=list(PARALLEL_BETA_CAPTURE_ACTION_GROUP_IDS),
            actual=value.get("action_group_ids"),
        )
    if value.get("status") != "status_only_parallel_candidate_capture_matrix":
        add(
            blockers,
            "parallel_beta_capture_side_lane_matrix_status_mismatch",
            f"{path}.status",
            value=value.get("status"),
        )
    if value.get("matrix_status") != "status_only_candidate_non_evidence":
        add(
            blockers,
            "parallel_beta_capture_side_lane_matrix_status_mismatch",
            f"{path}.matrix_status",
            value=value.get("matrix_status"),
        )
    for key in (
        "candidate_only",
        "candidate_capture_only",
        "status_only",
        "non_evidence",
        "debug_only",
        "optional_parallel_candidate_observations",
        "parallel_with_player_principal_lifecycle_window_planned",
        "same_approved_runtime_window_required",
        "exact_approved_runtime_window_required",
        "same_instance_and_map_required",
        "exact_target_binding_required",
        "side_lane_non_counting",
        "artifact_templates_only",
        "copy_to_offline_workspace_before_analysis",
        "redaction_required_before_checker_intake",
        "do_not_read_live_server_paths_from_pack",
        "correlation_metadata_required",
        "correlation_metadata_non_evidence",
        "requires_checker_acceptance",
        "requires_player_principal_triplet",
        "blocked_by_player_principal_evidence",
        "no_restart_required",
        "operator_actions_do_not_require_restart",
        "tester_actions_do_not_require_restart",
        "no_marker_or_env_change_required",
    ):
        if value.get(key) is not True:
            add(
                blockers,
                "parallel_beta_capture_side_lane_matrix_true_flag_missing",
                f"{path}.{key}",
                value=value.get(key),
            )
    for key in (
        "pack_authorizes_player_backed_window",
        "pack_authorizes_runtime_observer",
        "pack_authorizes_marker_or_env_change",
        "pack_authorizes_restart",
        "pack_authorizes_discord",
        "approved_runtime_evidence_present",
        "approved_runtime_evidence_ready",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_progress",
        "counts_as_p0_progress",
        "clears_approved_runtime_evidence_missing",
        "replaces_player_principal_evidence",
        "replaces_player_principal_triplet",
        "substitutes_for_player_principal_lifecycle_evidence",
        "substitutes_for_player_principal_lifecycle_triplet",
        "side_lane_substitutes_for_player_principal_lifecycle_evidence",
        "player_principal_lifecycle_evidence_substitution_allowed",
        "approved_runtime_evidence_substitution_allowed",
        "primary_evidence_substitution_allowed",
        "runtime_ready",
        "public_sdk_ready",
        "stable_sdk_ready",
        "v1_completion_ready",
        "readiness_claim_allowed",
        "downstream_unlock_allowed",
        "restart_required",
        "server_restart_required",
        "operator_action_requires_restart",
        "tester_action_requires_restart",
        "marker_or_env_change_required",
    ):
        if value.get(key) is not False:
            add(
                blockers,
                "parallel_beta_capture_side_lane_matrix_false_flag_overclaim",
                f"{path}.{key}",
                value=value.get(key),
            )
    validate_no_restart_action_fields(
        value,
        blockers,
        path,
        reason_prefix="parallel_beta_capture_side_lane_matrix",
    )
    if value.get("current_route_blocker") != CURRENT_ROUTE_BLOCKER:
        add(
            blockers,
            "parallel_beta_capture_side_lane_matrix_route_blocker_mismatch",
            f"{path}.current_route_blocker",
            value=value.get("current_route_blocker"),
        )
    if value.get("required_runtime_evidence") != NEXT_REQUIRED_ARTIFACT:
        add(
            blockers,
            "parallel_beta_capture_side_lane_matrix_required_evidence_mismatch",
            f"{path}.required_runtime_evidence",
            value=value.get("required_runtime_evidence"),
        )
    non_claim = value.get("non_claim")
    if not isinstance(non_claim, str) or "never replaces the required player-principal triplet" not in non_claim:
        add(
            blockers,
            "parallel_beta_capture_side_lane_matrix_non_claim_missing",
            f"{path}.non_claim",
            value=non_claim,
        )
    validate_target(
        value.get("target"),
        blockers,
        f"{path}.target",
        expected_target=expected_target,
        reason_prefix="parallel_beta_capture_side_lane_matrix_target",
    )
    validate_target_binding(
        value.get("target_binding"),
        blockers,
        f"{path}.target_binding",
        expected_target=expected_target,
        reason_prefix="parallel_beta_capture_side_lane_matrix_target_binding",
    )
    validate_target_binding_id(
        value.get("target_binding_id"),
        blockers,
        f"{path}.target_binding_id",
        expected_target=expected_target,
        reason_prefix="parallel_beta_capture_side_lane_matrix_target_binding_id",
    )
    validate_approved_runtime_window_binding(
        value.get("approved_runtime_window_binding"),
        blockers,
        f"{path}.approved_runtime_window_binding",
        expected_target=expected_target,
        reason_prefix="parallel_beta_capture_side_lane_matrix_approved_runtime_window_binding",
    )
    validate_lifecycle_correlation_metadata(
        value.get("lifecycle_correlation_metadata"),
        blockers,
        f"{path}.lifecycle_correlation_metadata",
        expected_target=expected_target,
        reason_prefix="parallel_beta_capture_side_lane_matrix_lifecycle_correlation_metadata",
    )
    validate_lifecycle_correlation_field_ids(
        value.get("correlation_field_ids"),
        blockers,
        f"{path}.correlation_field_ids",
        reason_prefix="parallel_beta_capture_side_lane_matrix_correlation",
    )
    validate_candidate_only_metadata(
        value.get("candidate_only_metadata"),
        blockers,
        f"{path}.candidate_only_metadata",
    )
    validate_parallel_capture_boundary(
        value.get("parallel_capture_boundary"),
        blockers,
        f"{path}.parallel_capture_boundary",
    )
    validate_player_principal_window_composition(
        value.get("player_principal_window_composition"),
        blockers,
        f"{path}.player_principal_window_composition",
    )
    validate_non_substitution_flags(value.get("non_substitution_flags"), blockers, f"{path}.non_substitution_flags")
    check_non_claim_flags(value.get("non_claim_flags"), blockers, f"{path}.non_claim_flags")
    expected_domain_rows = expected.get("domain_rows")
    domain_rows = value.get("domain_rows")
    if domain_rows != expected_domain_rows:
        add(
            blockers,
            "parallel_beta_capture_side_lane_matrix_domain_rows_mismatch",
            f"{path}.domain_rows",
            expected=expected_domain_rows,
            actual=domain_rows,
        )
    if not isinstance(domain_rows, list):
        add(blockers, "parallel_beta_capture_side_lane_matrix_domain_rows_invalid", f"{path}.domain_rows", value=domain_rows)
    else:
        expected_domains = [domain for domain, _surface_ids in PARALLEL_BETA_CAPTURE_DOMAINS]
        observed_domains = [row.get("domain") for row in domain_rows if isinstance(row, dict)]
        if observed_domains != expected_domains:
            add(
                blockers,
                "parallel_beta_capture_side_lane_matrix_domain_order_mismatch",
                f"{path}.domain_rows",
                expected=expected_domains,
                actual=observed_domains,
            )
        for index, row in enumerate(domain_rows):
            if not isinstance(row, dict):
                add(blockers, "parallel_beta_capture_side_lane_matrix_domain_row_invalid", f"{path}.domain_rows[{index}]", value=row)
                continue
            validate_target_binding(
                row.get("target_binding"),
                blockers,
                f"{path}.domain_rows[{index}].target_binding",
                expected_target=expected_target,
                reason_prefix="parallel_beta_capture_side_lane_matrix_domain_target_binding",
            )
            validate_target_binding_id(
                row.get("target_binding_id"),
                blockers,
                f"{path}.domain_rows[{index}].target_binding_id",
                expected_target=expected_target,
                reason_prefix="parallel_beta_capture_side_lane_matrix_domain_target_binding_id",
            )
            validate_approved_runtime_window_binding(
                row.get("approved_runtime_window_binding"),
                blockers,
                f"{path}.domain_rows[{index}].approved_runtime_window_binding",
                expected_target=expected_target,
                reason_prefix="parallel_beta_capture_side_lane_matrix_domain_approved_runtime_window_binding",
            )
            validate_lifecycle_correlation_metadata(
                row.get("lifecycle_correlation_metadata"),
                blockers,
                f"{path}.domain_rows[{index}].lifecycle_correlation_metadata",
                expected_target=expected_target,
                reason_prefix="parallel_beta_capture_side_lane_matrix_domain_lifecycle_correlation_metadata",
            )
            validate_lifecycle_correlation_field_ids(
                row.get("correlation_field_ids"),
                blockers,
                f"{path}.domain_rows[{index}].correlation_field_ids",
                reason_prefix="parallel_beta_capture_side_lane_matrix_domain_correlation",
            )
            validate_no_restart_action_fields(
                row,
                blockers,
                f"{path}.domain_rows[{index}]",
                reason_prefix="parallel_beta_capture_side_lane_matrix_domain",
                text_keys=("operator_next_action", "lead_next_action", "tester_brief"),
                list_keys=("operator_actions", "tester_actions"),
            )
            for key in (
                "candidate_only",
                "non_evidence",
                "same_approved_runtime_window_required",
                "exact_approved_runtime_window_required",
                "exact_target_binding_required",
                "requires_checker_acceptance",
                "requires_player_principal_triplet",
                "side_lane_non_counting",
                "correlation_metadata_required",
                "correlation_metadata_non_evidence",
            ):
                if row.get(key) is not True:
                    add(blockers, "parallel_beta_capture_side_lane_matrix_domain_true_flag_missing", f"{path}.domain_rows[{index}].{key}", value=row.get(key))
            for key in (
                "counts_as_runtime_evidence",
                "counts_as_sdk_progress",
                "counts_as_p0_progress",
                "substitutes_for_player_principal_lifecycle_evidence",
                "primary_evidence_substitution_allowed",
            ):
                if row.get(key) is not False:
                    add(blockers, "parallel_beta_capture_side_lane_matrix_domain_false_flag_overclaim", f"{path}.domain_rows[{index}].{key}", value=row.get(key))
    expected_group_rows = expected.get("action_group_rows")
    group_rows = value.get("action_group_rows")
    if group_rows != expected_group_rows:
        add(
            blockers,
            "parallel_beta_capture_side_lane_matrix_action_group_rows_mismatch",
            f"{path}.action_group_rows",
            expected=expected_group_rows,
            actual=group_rows,
        )
    if not isinstance(group_rows, list):
        add(blockers, "parallel_beta_capture_side_lane_matrix_action_group_rows_invalid", f"{path}.action_group_rows", value=group_rows)
    else:
        observed_group_ids = [row.get("action_group_id") for row in group_rows if isinstance(row, dict)]
        if observed_group_ids != list(PARALLEL_BETA_CAPTURE_ACTION_GROUP_IDS):
            add(
                blockers,
                "parallel_beta_capture_side_lane_matrix_action_group_order_mismatch",
                f"{path}.action_group_rows",
                expected=list(PARALLEL_BETA_CAPTURE_ACTION_GROUP_IDS),
                actual=observed_group_ids,
            )
        for index, row in enumerate(group_rows):
            if not isinstance(row, dict):
                add(blockers, "parallel_beta_capture_side_lane_matrix_action_group_row_invalid", f"{path}.action_group_rows[{index}]", value=row)
                continue
            validate_target_binding(
                row.get("target_binding"),
                blockers,
                f"{path}.action_group_rows[{index}].target_binding",
                expected_target=expected_target,
                reason_prefix="parallel_beta_capture_side_lane_matrix_action_group_target_binding",
            )
            validate_target_binding_id(
                row.get("target_binding_id"),
                blockers,
                f"{path}.action_group_rows[{index}].target_binding_id",
                expected_target=expected_target,
                reason_prefix="parallel_beta_capture_side_lane_matrix_action_group_target_binding_id",
            )
            validate_approved_runtime_window_binding(
                row.get("approved_runtime_window_binding"),
                blockers,
                f"{path}.action_group_rows[{index}].approved_runtime_window_binding",
                expected_target=expected_target,
                reason_prefix="parallel_beta_capture_side_lane_matrix_action_group_approved_runtime_window_binding",
            )
            validate_lifecycle_correlation_metadata(
                row.get("lifecycle_correlation_metadata"),
                blockers,
                f"{path}.action_group_rows[{index}].lifecycle_correlation_metadata",
                expected_target=expected_target,
                reason_prefix="parallel_beta_capture_side_lane_matrix_action_group_lifecycle_correlation_metadata",
            )
            validate_lifecycle_correlation_field_ids(
                row.get("correlation_field_ids"),
                blockers,
                f"{path}.action_group_rows[{index}].correlation_field_ids",
                reason_prefix="parallel_beta_capture_side_lane_matrix_action_group_correlation",
            )
            validate_no_restart_action_fields(
                row,
                blockers,
                f"{path}.action_group_rows[{index}]",
                reason_prefix="parallel_beta_capture_side_lane_matrix_action_group",
                text_keys=("operator_next_action", "lead_next_action", "tester_brief"),
                list_keys=("operator_actions", "tester_actions"),
            )
            for key in (
                "candidate_only",
                "non_evidence",
                "same_approved_runtime_window_required",
                "exact_approved_runtime_window_required",
                "exact_target_binding_required",
                "requires_checker_acceptance",
                "requires_player_principal_triplet",
                "side_lane_non_counting",
                "correlation_metadata_required",
                "correlation_metadata_non_evidence",
            ):
                if row.get(key) is not True:
                    add(blockers, "parallel_beta_capture_side_lane_matrix_action_group_true_flag_missing", f"{path}.action_group_rows[{index}].{key}", value=row.get(key))
            for key in (
                "counts_as_runtime_evidence",
                "counts_as_sdk_progress",
                "counts_as_p0_progress",
                "substitution_allowed",
                "primary_evidence_substitution_allowed",
            ):
                if row.get(key) is not False:
                    add(blockers, "parallel_beta_capture_side_lane_matrix_action_group_false_flag_overclaim", f"{path}.action_group_rows[{index}].{key}", value=row.get(key))
    surface_rows = value.get("surface_rows")
    expected_surface_rows = expected.get("surface_rows")
    if surface_rows != expected_surface_rows:
        add(
            blockers,
            "parallel_beta_capture_side_lane_matrix_surface_rows_mismatch",
            f"{path}.surface_rows",
            expected=expected_surface_rows,
            actual=surface_rows,
        )
    if not isinstance(surface_rows, list):
        add(blockers, "parallel_beta_capture_side_lane_matrix_surface_rows_invalid", f"{path}.surface_rows", value=surface_rows)
        return
    observed_ids = [row.get("id") for row in surface_rows if isinstance(row, dict)]
    if observed_ids != list(PARALLEL_BETA_CAPTURE_SURFACE_IDS):
        add(
            blockers,
            "parallel_beta_capture_side_lane_matrix_surface_order_mismatch",
            f"{path}.surface_rows",
            expected=list(PARALLEL_BETA_CAPTURE_SURFACE_IDS),
            actual=observed_ids,
        )
    for index, row in enumerate(surface_rows):
        if not isinstance(row, dict):
            add(blockers, "parallel_beta_capture_side_lane_matrix_surface_row_invalid", f"{path}.surface_rows[{index}]", value=row)
            continue
        surface_id = row.get("id")
        if surface_id == "player_principal_lifecycle":
            add(blockers, "parallel_beta_capture_side_lane_matrix_primary_surface_included", f"{path}.surface_rows[{index}].id")
        validate_target_binding(
            row.get("target_binding"),
            blockers,
            f"{path}.surface_rows[{index}].target_binding",
            expected_target=expected_target,
            reason_prefix="parallel_beta_capture_side_lane_matrix_surface_target_binding",
        )
        validate_target_binding_id(
            row.get("target_binding_id"),
            blockers,
            f"{path}.surface_rows[{index}].target_binding_id",
            expected_target=expected_target,
            reason_prefix="parallel_beta_capture_side_lane_matrix_surface_target_binding_id",
        )
        validate_approved_runtime_window_binding(
            row.get("approved_runtime_window_binding"),
            blockers,
            f"{path}.surface_rows[{index}].approved_runtime_window_binding",
            expected_target=expected_target,
            reason_prefix="parallel_beta_capture_side_lane_matrix_surface_approved_runtime_window_binding",
        )
        validate_lifecycle_correlation_metadata(
            row.get("lifecycle_correlation_metadata"),
            blockers,
            f"{path}.surface_rows[{index}].lifecycle_correlation_metadata",
            expected_target=expected_target,
            reason_prefix="parallel_beta_capture_side_lane_matrix_surface_lifecycle_correlation_metadata",
        )
        validate_lifecycle_correlation_field_ids(
            row.get("correlation_field_ids"),
            blockers,
            f"{path}.surface_rows[{index}].correlation_field_ids",
            reason_prefix="parallel_beta_capture_side_lane_matrix_surface_correlation",
        )
        validate_operator_tester_action_metadata(
            row.get("operator_tester_action_metadata"),
            row,
            blockers,
            f"{path}.surface_rows[{index}].operator_tester_action_metadata",
            expected_target=expected_target,
            reason_prefix="parallel_beta_capture_side_lane_matrix_surface_operator_tester_action_metadata",
        )
        validate_no_restart_action_fields(
            row,
            blockers,
            f"{path}.surface_rows[{index}]",
            reason_prefix="parallel_beta_capture_side_lane_matrix_surface",
            text_keys=("operator_next_action", "lead_next_action", "tester_brief"),
        )
        validate_checker_command(row, blockers, f"{path}.surface_rows[{index}]", "command")
        for key in (
            "same_approved_runtime_window_required",
            "exact_approved_runtime_window_required",
            "same_instance_and_map_required",
            "exact_target_binding_required",
            "candidate_only",
            "status_only",
            "non_evidence",
            "optional_parallel_candidate_observation",
            "parallel_with_player_principal_lifecycle_window",
            "side_lane",
            "side_lane_non_counting",
            "requires_checker_acceptance",
            "requires_player_principal_triplet",
            "blocked_by_player_principal_evidence",
            "correlation_metadata_required",
            "correlation_metadata_non_evidence",
            "no_restart_required",
            "operator_actions_do_not_require_restart",
            "tester_actions_do_not_require_restart",
            "no_marker_or_env_change_required",
        ):
            if row.get(key) is not True:
                add(blockers, "parallel_beta_capture_side_lane_matrix_surface_true_flag_missing", f"{path}.surface_rows[{index}].{key}", value=row.get(key))
        for key in (
            "approved_runtime_evidence_present",
            "approved_runtime_evidence_ready",
            "counts_as_approved_runtime_evidence",
            "counts_as_runtime_evidence",
            "counts_as_sdk_progress",
            "counts_as_p0_progress",
            "clears_approved_runtime_evidence_missing",
            "replaces_player_principal_evidence",
            "replaces_player_principal_triplet",
            "substitutes_for_player_principal_lifecycle_evidence",
            "substitutes_for_player_principal_lifecycle_triplet",
            "side_lane_substitutes_for_player_principal_lifecycle_evidence",
            "player_principal_lifecycle_evidence_substitution_allowed",
            "approved_runtime_evidence_substitution_allowed",
            "primary_evidence_substitution_allowed",
            "runtime_ready",
            "public_sdk_ready",
            "stable_sdk_ready",
            "v1_completion_ready",
            "pack_authorizes_restart",
            "restart_required",
            "server_restart_required",
            "operator_action_requires_restart",
            "tester_action_requires_restart",
            "marker_or_env_change_required",
        ):
            if row.get(key) is not False:
                add(blockers, "parallel_beta_capture_side_lane_matrix_surface_false_flag_overclaim", f"{path}.surface_rows[{index}].{key}", value=row.get(key))
        if row.get("current_route_blocker") != CURRENT_ROUTE_BLOCKER:
            add(blockers, "parallel_beta_capture_side_lane_matrix_surface_route_blocker_mismatch", f"{path}.surface_rows[{index}].current_route_blocker", value=row.get("current_route_blocker"))
        if row.get("required_runtime_evidence") != NEXT_REQUIRED_ARTIFACT:
            add(blockers, "parallel_beta_capture_side_lane_matrix_surface_required_evidence_mismatch", f"{path}.surface_rows[{index}].required_runtime_evidence", value=row.get("required_runtime_evidence"))


def validate_single_player_parallel_capture_sequence(
    value: Any,
    expected: Any,
    blockers: list[dict[str, Any]],
    path: str,
    *,
    expected_target: dict[str, str] | None,
) -> None:
    if not isinstance(value, dict):
        add(blockers, "single_player_parallel_capture_sequence_missing_or_invalid", path, value=value)
        return
    if not isinstance(expected, dict):
        add(blockers, "single_player_parallel_capture_sequence_expected_missing", path, expected=expected)
        return
    if value != expected:
        add(
            blockers,
            "single_player_parallel_capture_sequence_mismatch",
            path,
            expected=expected,
            actual=value,
        )
    if value.get("id") != SINGLE_PLAYER_PARALLEL_CAPTURE_SEQUENCE_ID:
        add(
            blockers,
            "single_player_parallel_capture_sequence_id_mismatch",
            f"{path}.id",
            expected=SINGLE_PLAYER_PARALLEL_CAPTURE_SEQUENCE_ID,
            actual=value.get("id"),
        )
    if value.get("status") != "status_only_parallel_candidate_sequence":
        add(blockers, "single_player_parallel_capture_sequence_status_mismatch", f"{path}.status", value=value.get("status"))
    if value.get("sequence_status") != "status_only_candidate_non_evidence":
        add(blockers, "single_player_parallel_capture_sequence_status_mismatch", f"{path}.sequence_status", value=value.get("sequence_status"))
    if value.get("action_group_ids") != list(SINGLE_PLAYER_PARALLEL_CAPTURE_ACTION_GROUP_IDS):
        add(
            blockers,
            "single_player_parallel_capture_sequence_action_group_ids_mismatch",
            f"{path}.action_group_ids",
            expected=list(SINGLE_PLAYER_PARALLEL_CAPTURE_ACTION_GROUP_IDS),
            actual=value.get("action_group_ids"),
        )
    if value.get("surface_ids") != list(SINGLE_PLAYER_PARALLEL_CAPTURE_SURFACE_IDS):
        add(
            blockers,
            "single_player_parallel_capture_sequence_surface_ids_mismatch",
            f"{path}.surface_ids",
            expected=list(SINGLE_PLAYER_PARALLEL_CAPTURE_SURFACE_IDS),
            actual=value.get("surface_ids"),
        )
    if value.get("single_player_route_surface_ids") != list(SINGLE_PLAYER_PARALLEL_CAPTURE_SURFACE_IDS):
        add(
            blockers,
            "single_player_parallel_capture_sequence_route_surface_ids_mismatch",
            f"{path}.single_player_route_surface_ids",
            expected=list(SINGLE_PLAYER_PARALLEL_CAPTURE_SURFACE_IDS),
            actual=value.get("single_player_route_surface_ids"),
        )
    if value.get("side_lane_surface_ids") != list(PARALLEL_BETA_CAPTURE_SURFACE_IDS):
        add(
            blockers,
            "single_player_parallel_capture_sequence_side_lane_surface_ids_mismatch",
            f"{path}.side_lane_surface_ids",
            expected=list(PARALLEL_BETA_CAPTURE_SURFACE_IDS),
            actual=value.get("side_lane_surface_ids"),
        )
    if value.get("candidate_domain_ids") != list(SINGLE_PLAYER_PARALLEL_CAPTURE_DOMAIN_IDS):
        add(
            blockers,
            "single_player_parallel_capture_sequence_domain_ids_mismatch",
            f"{path}.candidate_domain_ids",
            expected=list(SINGLE_PLAYER_PARALLEL_CAPTURE_DOMAIN_IDS),
            actual=value.get("candidate_domain_ids"),
        )
    if value.get("excluded_surface_ids") != list(SINGLE_PLAYER_ROUTE_EXCLUDED_SURFACE_IDS):
        add(
            blockers,
            "single_player_parallel_capture_sequence_excluded_surface_ids_mismatch",
            f"{path}.excluded_surface_ids",
            expected=list(SINGLE_PLAYER_ROUTE_EXCLUDED_SURFACE_IDS),
            actual=value.get("excluded_surface_ids"),
        )
    non_claim = value.get("non_claim")
    if non_claim != SINGLE_PLAYER_ROUTE_NON_CLAIM:
        add(
            blockers,
            "single_player_parallel_capture_sequence_non_claim_mismatch",
            f"{path}.non_claim",
            expected=SINGLE_PLAYER_ROUTE_NON_CLAIM,
            actual=non_claim,
        )
    validate_target(
        value.get("target"),
        blockers,
        f"{path}.target",
        expected_target=expected_target,
        reason_prefix="single_player_parallel_capture_sequence_target",
    )
    validate_target_binding(
        value.get("target_binding"),
        blockers,
        f"{path}.target_binding",
        expected_target=expected_target,
        reason_prefix="single_player_parallel_capture_sequence_target_binding",
    )
    validate_target_binding_id(
        value.get("target_binding_id"),
        blockers,
        f"{path}.target_binding_id",
        expected_target=expected_target,
        reason_prefix="single_player_parallel_capture_sequence_target_binding_id",
    )
    validate_approved_runtime_window_binding(
        value.get("approved_runtime_window_binding"),
        blockers,
        f"{path}.approved_runtime_window_binding",
        expected_target=expected_target,
        reason_prefix="single_player_parallel_capture_sequence_approved_runtime_window_binding",
    )
    validate_lifecycle_correlation_metadata(
        value.get("lifecycle_correlation_metadata"),
        blockers,
        f"{path}.lifecycle_correlation_metadata",
        expected_target=expected_target,
        reason_prefix="single_player_parallel_capture_sequence_lifecycle_correlation_metadata",
    )
    validate_lifecycle_correlation_field_ids(
        value.get("correlation_field_ids"),
        blockers,
        f"{path}.correlation_field_ids",
        reason_prefix="single_player_parallel_capture_sequence_correlation",
    )
    validate_text_privacy_boundary(value.get("text_privacy_boundary"), blockers, f"{path}.text_privacy_boundary")
    validate_no_restart_action_fields(
        value,
        blockers,
        path,
        reason_prefix="single_player_parallel_capture_sequence",
    )
    validate_single_player_route_constraints(
        value.get("single_player_route_constraints"),
        blockers,
        f"{path}.single_player_route_constraints",
        reason_prefix="single_player_route_constraints",
    )
    check_non_claim_flags(value.get("non_claim_flags"), blockers, f"{path}.non_claim_flags")
    for key in (
        "single_player_route",
        "candidate_only",
        "status_only",
        "non_evidence",
        "parallel_with_player_principal_lifecycle_window_planned",
        "same_approved_runtime_window_required",
        "exact_approved_runtime_window_required",
        "same_instance_and_map_required",
        "exact_target_binding_required",
        "requires_checker_acceptance",
        "requires_player_principal_triplet",
        "blocked_by_player_principal_evidence",
        "operator_action_metadata_explicit",
        "correlation_metadata_required",
        "correlation_metadata_non_evidence",
    ):
        if value.get(key) is not True:
            add(blockers, "single_player_parallel_capture_sequence_true_flag_missing", f"{path}.{key}", value=value.get(key))
    for key in (
        "raw_player_text_retention_allowed",
        "raw_player_text_capture_allowed",
        "raw_chat_payload_capture_allowed",
        "private_player_data_retention_allowed",
        "secrets_or_webhook_retention_allowed",
        "pack_authorizes_discord",
        "discord_send_required",
        "authorizes_discord_send",
        "authorizes_live_log_reads",
        "authorizes_runtime_capture",
        "authorizes_server_restart",
        "authorizes_server_start",
        "authorizes_server_stop",
        "authorizes_marker_or_env_changes",
        "approved_runtime_evidence_present",
        "approved_runtime_evidence_ready",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_progress",
        "counts_as_p0_progress",
        "clears_approved_runtime_evidence_missing",
        "substitution_allowed",
        "primary_evidence_substitution_allowed",
        "side_lane_collection_can_replace_player_principal_evidence",
        "side_lane_collection_counts_before_checker_acceptance",
        "side_lane_counts_toward_sdk",
        "side_lane_counts_toward_p0",
        "runtime_ready",
        "public_sdk_ready",
        "stable_sdk_ready",
        "restart_required",
        "server_restart_required",
        "operator_action_requires_restart",
        "tester_action_requires_restart",
        "marker_or_env_change_required",
    ):
        if value.get(key) is not False:
            add(blockers, "single_player_parallel_capture_sequence_false_flag_overclaim", f"{path}.{key}", value=value.get(key))
    if value.get("current_route_blocker") != CURRENT_ROUTE_BLOCKER:
        add(blockers, "single_player_parallel_capture_sequence_route_blocker_mismatch", f"{path}.current_route_blocker", value=value.get("current_route_blocker"))
    if value.get("required_runtime_evidence") != NEXT_REQUIRED_ARTIFACT:
        add(blockers, "single_player_parallel_capture_sequence_required_evidence_mismatch", f"{path}.required_runtime_evidence", value=value.get("required_runtime_evidence"))

    expected_phases = expected.get("phases")
    phases = value.get("phases")
    if phases != expected_phases:
        add(
            blockers,
            "single_player_parallel_capture_sequence_phases_mismatch",
            f"{path}.phases",
            expected=expected_phases,
            actual=phases,
        )
    if not isinstance(phases, list):
        add(blockers, "single_player_parallel_capture_sequence_phases_invalid", f"{path}.phases", value=phases)
        return
    if value.get("phase_count") != len(phases):
        add(blockers, "single_player_parallel_capture_sequence_phase_count_mismatch", f"{path}.phase_count", expected=len(phases), actual=value.get("phase_count"))
    observed_phase_ids = [phase.get("phase_id") for phase in phases if isinstance(phase, dict)]
    if observed_phase_ids != list(SINGLE_PLAYER_PARALLEL_CAPTURE_ACTION_GROUP_IDS):
        add(
            blockers,
            "single_player_parallel_capture_sequence_phase_order_mismatch",
            f"{path}.phases",
            expected=list(SINGLE_PLAYER_PARALLEL_CAPTURE_ACTION_GROUP_IDS),
            actual=observed_phase_ids,
        )
    for index, phase in enumerate(phases):
        if not isinstance(phase, dict):
            add(blockers, "single_player_parallel_capture_sequence_phase_invalid", f"{path}.phases[{index}]", value=phase)
            continue
        validate_target_binding(
            phase.get("target_binding"),
            blockers,
            f"{path}.phases[{index}].target_binding",
            expected_target=expected_target,
            reason_prefix="single_player_parallel_capture_sequence_phase_target_binding",
        )
        validate_target_binding_id(
            phase.get("target_binding_id"),
            blockers,
            f"{path}.phases[{index}].target_binding_id",
            expected_target=expected_target,
            reason_prefix="single_player_parallel_capture_sequence_phase_target_binding_id",
        )
        validate_approved_runtime_window_binding(
            phase.get("approved_runtime_window_binding"),
            blockers,
            f"{path}.phases[{index}].approved_runtime_window_binding",
            expected_target=expected_target,
            reason_prefix="single_player_parallel_capture_sequence_phase_approved_runtime_window_binding",
        )
        validate_lifecycle_correlation_metadata(
            phase.get("lifecycle_correlation_metadata"),
            blockers,
            f"{path}.phases[{index}].lifecycle_correlation_metadata",
            expected_target=expected_target,
            reason_prefix="single_player_parallel_capture_sequence_phase_lifecycle_correlation_metadata",
        )
        validate_lifecycle_correlation_field_ids(
            phase.get("correlation_field_ids"),
            blockers,
            f"{path}.phases[{index}].correlation_field_ids",
            reason_prefix="single_player_parallel_capture_sequence_phase_correlation",
        )
        validate_text_privacy_boundary(
            phase.get("text_privacy_boundary"),
            blockers,
            f"{path}.phases[{index}].text_privacy_boundary",
        )
        validate_no_restart_action_fields(
            phase,
            blockers,
            f"{path}.phases[{index}]",
            reason_prefix="single_player_parallel_capture_sequence_phase",
            text_keys=("operator_next_action", "lead_next_action", "tester_brief"),
            list_keys=("operator_actions", "tester_actions"),
        )
        expected_optional = phase.get("phase_id") != "primary_player_principal_gate"
        if phase.get("optional_parallel_candidate_observations") is not expected_optional:
            add(
                blockers,
                "single_player_parallel_capture_sequence_phase_optional_mismatch",
                f"{path}.phases[{index}].optional_parallel_candidate_observations",
                expected=expected_optional,
                actual=phase.get("optional_parallel_candidate_observations"),
            )
        expected_role = (
            "optional_parallel_candidate_observations"
            if expected_optional
            else "primary_player_principal_lifecycle"
        )
        if phase.get("phase_role") != expected_role:
            add(
                blockers,
                "single_player_parallel_capture_sequence_phase_role_mismatch",
                f"{path}.phases[{index}].phase_role",
                expected=expected_role,
                actual=phase.get("phase_role"),
            )
        phase_id = phase.get("phase_id")
        expected_domains = list(
            SINGLE_PLAYER_PHASE_DOMAIN_IDS_BY_ACTION_GROUP.get(phase_id, ())
            if isinstance(phase_id, str)
            else ()
        )
        if phase.get("phase_domain_ids") != expected_domains:
            add(
                blockers,
                "single_player_parallel_capture_sequence_phase_domain_ids_mismatch",
                f"{path}.phases[{index}].phase_domain_ids",
                expected=expected_domains,
                actual=phase.get("phase_domain_ids"),
            )
        validate_single_player_route_constraints(
            phase.get("single_player_route_constraints"),
            blockers,
            f"{path}.phases[{index}].single_player_route_constraints",
            reason_prefix="single_player_phase_route_constraints",
        )
        for key in (
            "single_player_route",
            "candidate_only",
            "status_only",
            "non_evidence",
            "same_approved_runtime_window_required",
            "exact_approved_runtime_window_required",
            "same_instance_and_map_required",
            "exact_target_binding_required",
            "requires_checker_acceptance",
            "requires_player_principal_triplet",
            "blocked_by_player_principal_evidence",
            "operator_action_metadata_explicit",
            "correlation_metadata_required",
            "correlation_metadata_non_evidence",
        ):
            if phase.get(key) is not True:
                add(blockers, "single_player_parallel_capture_sequence_phase_true_flag_missing", f"{path}.phases[{index}].{key}", value=phase.get(key))
        for key in (
            "raw_player_text_retention_allowed",
            "raw_player_text_capture_allowed",
            "raw_chat_payload_capture_allowed",
            "private_player_data_retention_allowed",
            "secrets_or_webhook_retention_allowed",
            "pack_authorizes_discord",
            "discord_send_required",
            "authorizes_discord_send",
            "authorizes_live_log_reads",
            "authorizes_runtime_capture",
            "approved_runtime_evidence_present",
            "approved_runtime_evidence_ready",
            "counts_as_approved_runtime_evidence",
            "counts_as_runtime_evidence",
            "counts_as_sdk_progress",
            "counts_as_p0_progress",
            "clears_approved_runtime_evidence_missing",
            "substitution_allowed",
            "primary_evidence_substitution_allowed",
            "side_lane_collection_can_replace_player_principal_evidence",
            "side_lane_collection_counts_before_checker_acceptance",
            "side_lane_counts_toward_sdk",
            "side_lane_counts_toward_p0",
            "runtime_ready",
            "public_sdk_ready",
            "stable_sdk_ready",
            "restart_required",
            "server_restart_required",
            "operator_action_requires_restart",
            "tester_action_requires_restart",
            "marker_or_env_change_required",
        ):
            if phase.get(key) is not False:
                add(blockers, "single_player_parallel_capture_sequence_phase_false_flag_overclaim", f"{path}.phases[{index}].{key}", value=phase.get(key))
        checker_commands = phase.get("checker_commands")
        if not isinstance(checker_commands, list) or not checker_commands:
            add(blockers, "single_player_parallel_capture_sequence_phase_checker_commands_missing", f"{path}.phases[{index}].checker_commands", value=checker_commands)
        else:
            for command_index, command_row in enumerate(checker_commands):
                if not isinstance(command_row, dict):
                    add(blockers, "single_player_parallel_capture_sequence_phase_checker_command_invalid", f"{path}.phases[{index}].checker_commands[{command_index}]", value=command_row)
                    continue
                validate_checker_command(
                    {"id": command_row.get("surface_id"), "command": command_row.get("command")},
                    blockers,
                    f"{path}.phases[{index}].checker_commands[{command_index}]",
                    "command",
                )
        support_rows = phase.get("readiness_checker_support")
        if not isinstance(support_rows, list) or not support_rows:
            add(blockers, "single_player_parallel_capture_sequence_phase_readiness_support_missing", f"{path}.phases[{index}].readiness_checker_support", value=support_rows)
        else:
            for support_index, support in enumerate(support_rows):
                if not isinstance(support, dict):
                    add(blockers, "single_player_parallel_capture_sequence_phase_readiness_support_invalid", f"{path}.phases[{index}].readiness_checker_support[{support_index}]", value=support)
                    continue
                surface_id = support.get("surface_id")
                if support.get("checker") != EXPECTED_SURFACE_CHECKERS.get(surface_id):
                    add(blockers, "single_player_parallel_capture_sequence_phase_readiness_checker_mismatch", f"{path}.phases[{index}].readiness_checker_support[{support_index}].checker", value=support.get("checker"))
                if support.get("supported_by_existing_readiness_script") is not True:
                    add(blockers, "single_player_parallel_capture_sequence_phase_readiness_support_not_true", f"{path}.phases[{index}].readiness_checker_support[{support_index}].supported_by_existing_readiness_script", value=support.get("supported_by_existing_readiness_script"))
                if support.get("checker_mode") != "offline_status_only":
                    add(blockers, "single_player_parallel_capture_sequence_phase_checker_mode_mismatch", f"{path}.phases[{index}].readiness_checker_support[{support_index}].checker_mode", value=support.get("checker_mode"))


def expected_required_checker_artifacts(surface: dict[str, Any], artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    placeholders = checker_placeholders(surface)
    rows = []
    for artifact in artifacts:
        checker_input = artifact.get("checker_input")
        if artifact.get("required_for_checker") is True and isinstance(checker_input, str):
            rows.append(
                {
                    "artifact_id": artifact["id"],
                    "checker_input": checker_input,
                    "path_template": artifact["path_template"],
                    "satisfies_checker_placeholder": checker_input in placeholders,
                    "target_binding_required": True,
                    "target_binding_id": artifact.get("target_binding", {}).get("binding_id")
                    if isinstance(artifact.get("target_binding"), dict)
                    else None,
                    "target_binding": artifact.get("target_binding"),
                    "same_approved_runtime_window_required": True,
                    "approved_runtime_window_binding": artifact.get("approved_runtime_window_binding"),
                    "redaction_required": True,
                    "must_not_be_live_server_path": True,
                }
            )
    return rows


def validate_required_checker_artifacts(
    surface: dict[str, Any],
    artifacts: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
    path: str,
) -> None:
    expected_required = expected_required_checker_artifacts(surface, artifacts)
    actual_required = surface.get("required_checker_artifacts")
    if actual_required != expected_required:
        add(blockers, "surface_required_checker_artifacts_mismatch", f"{path}.required_checker_artifacts", expected=expected_required, actual=actual_required)
    optional_expected = [
        artifact["id"]
        for artifact in artifacts
        if artifact.get("required_for_checker") is False
    ]
    if surface.get("optional_candidate_artifacts") != optional_expected:
        add(
            blockers,
            "surface_optional_candidate_artifacts_mismatch",
            f"{path}.optional_candidate_artifacts",
            expected=optional_expected,
            actual=surface.get("optional_candidate_artifacts"),
        )
    if surface.get("checker_inputs_satisfied_by_artifacts") is not True:
        add(
            blockers,
            "surface_checker_inputs_satisfied_by_artifacts_not_true",
            f"{path}.checker_inputs_satisfied_by_artifacts",
            value=surface.get("checker_inputs_satisfied_by_artifacts"),
        )


def normalized_key(key: str) -> str:
    return "".join(ch for ch in key.lower() if ch.isalnum())


def validate_false_progress_aliases(value: Any, blockers: list[dict[str, Any]], path: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if normalized_key(str(key)) in FALSE_PROGRESS_READINESS_KEY_ALIASES and child is not False and child != 0:
                add(blockers, "false_progress_readiness_flag_overclaim", child_path, value=child)
            validate_false_progress_aliases(child, blockers, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_false_progress_aliases(child, blockers, f"{path}[{index}]")


def validate_target_binding_aliases(value: Any, blockers: list[dict[str, Any]], path: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            key_text = str(key)
            if (
                key_text not in ALLOWED_TARGET_BINDING_KEYS
                and normalized_key(key_text) in TARGET_BINDING_ALIAS_KEY_ALIASES
            ):
                add(blockers, "target_binding_alias_not_allowed", child_path, key=key_text)
            validate_target_binding_aliases(child, blockers, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_target_binding_aliases(child, blockers, f"{path}[{index}]")


def path_marks_sensitive_retention_key(path: str) -> bool:
    leaf = path.rsplit(".", 1)[-1].split("[", 1)[0]
    alias = normalized_key(leaf)
    return alias in SENSITIVE_RETENTION_KEY_ALIASES or any(
        part in alias for part in SENSITIVE_RETENTION_KEY_PARTS
    )


def allowed_redacted_sensitive_value(value: str) -> bool:
    text = value.strip()
    folded = text.casefold()
    if folded in ALLOWED_REDACTED_SENTINELS:
        return True
    if text.startswith("<") and text.endswith(">") and any(
        token in folded for token in ("redacted", "withheld", "omitted")
    ):
        return True
    return False


def validate_retained_sensitive_text(value: Any, blockers: list[dict[str, Any]], path: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            validate_retained_sensitive_text(child, blockers, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            validate_retained_sensitive_text(child, blockers, f"{path}[{index}]")
        return
    if not isinstance(value, str):
        return
    if DISCORD_WEBHOOK_URL_RE.search(value):
        add(blockers, "forbidden_retained_discord_webhook_url", path)
    if TEXT_RETENTION_ASSIGNMENT_RE.search(value):
        add(blockers, "forbidden_retained_sensitive_text_assignment", path, value=value)
    if path_marks_sensitive_retention_key(path) and not allowed_redacted_sensitive_value(value):
        add(blockers, "forbidden_retained_sensitive_text_assignment", path, value=value)
        add(blockers, "forbidden_retained_sensitive_text_value", path, value=value)


def blocker_clearance_claim_is_negated(text: str, match: re.Match[str]) -> bool:
    prefix = text[max(0, match.start() - 32) : match.start()]
    matched_text = text[match.start() : match.end()]
    return bool(
        BLOCKER_CLEARANCE_NEGATION_RE.search(prefix)
        or BLOCKER_CLEARANCE_NEGATION_RE.search(matched_text)
    )


def validate_blocker_clearance_text(
    text: str,
    blockers: list[dict[str, Any]],
    path: str,
) -> None:
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in BLOCKER_CLEARANCE_CLAIM_RE.finditer(line):
            if blocker_clearance_claim_is_negated(line, match):
                continue
            add(
                blockers,
                "blocker_clearance_text_overclaim",
                f"{path}:{line_number}",
                value=line.strip(),
            )


def promotional_claim_is_negated(text: str, match: re.Match[str]) -> bool:
    prefix = text[max(0, match.start() - 48) : match.start()]
    matched_text = text[match.start() : match.end()]
    return bool(
        BLOCKER_CLEARANCE_NEGATION_RE.search(prefix)
        or BLOCKER_CLEARANCE_NEGATION_RE.search(matched_text)
        or re.search(r"\b(?:non|candidate[_ -]?only)\b", prefix, re.IGNORECASE)
    )


def validate_promotional_claim_text(
    text: str,
    blockers: list[dict[str, Any]],
    path: str,
) -> None:
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in PROMOTIONAL_CLAIM_TEXT_RE.finditer(line):
            if promotional_claim_is_negated(line, match):
                continue
            add(
                blockers,
                "promotional_claim_text_overclaim",
                f"{path}:{line_number}",
                value=line.strip(),
            )


def validate_blocker_clearance_claims(
    value: Any,
    blockers: list[dict[str, Any]],
    path: str,
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            validate_blocker_clearance_claims(child, blockers, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            validate_blocker_clearance_claims(child, blockers, f"{path}[{index}]")
        return
    if isinstance(value, str):
        validate_blocker_clearance_text(value, blockers, path)


def validate_promotional_claims(
    value: Any,
    blockers: list[dict[str, Any]],
    path: str,
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            validate_promotional_claims(child, blockers, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            validate_promotional_claims(child, blockers, f"{path}[{index}]")
        return
    if isinstance(value, str):
        validate_promotional_claim_text(value, blockers, path)


def validate_artifact_retention_scan(pack_root: Path, blockers: list[dict[str, Any]]) -> None:
    for name in sorted(EXPECTED_FILES):
        path = pack_root / name
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            add(blockers, "retention_scan_text_decode_failed", f"$artifact_text.{name}", error=str(exc))
            continue
        except OSError as exc:
            add(blockers, "retention_scan_text_read_failed", f"$artifact_text.{name}", error=str(exc))
            continue
        if DISCORD_WEBHOOK_URL_RE.search(text):
            add(blockers, "forbidden_retained_discord_webhook_url", f"$artifact_text.{name}")
        if not name.endswith(".json") and TEXT_RETENTION_ASSIGNMENT_RE.search(text):
            add(blockers, "forbidden_retained_sensitive_text_assignment", f"$artifact_text.{name}")
        if not name.endswith(".json"):
            validate_blocker_clearance_text(text, blockers, f"$artifact_text.{name}")
            validate_promotional_claim_text(text, blockers, f"$artifact_text.{name}")
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            add(blockers, "retention_scan_json_invalid", f"$artifact_json.{name}", error=str(exc))
            continue
        validate_retained_sensitive_text(payload, blockers, f"$artifact_json.{name}")
        validate_blocker_clearance_claims(payload, blockers, f"$artifact_json.{name}")
        validate_promotional_claims(payload, blockers, f"$artifact_json.{name}")


def validate_surface_guardrails(
    surface: dict[str, Any],
    blockers: list[dict[str, Any]],
    path: str,
    *,
    expected_target: dict[str, str] | None,
    false_reason: str,
    true_reason: str,
) -> None:
    for key in REQUIRED_TRUE_SURFACE_FLAGS:
        if surface.get(key) is not True:
            add(blockers, true_reason, f"{path}.{key}", value=surface.get(key))
    for key in REQUIRED_FALSE_SURFACE_FLAGS:
        if surface.get(key) is not False:
            add(blockers, false_reason, f"{path}.{key}", value=surface.get(key))
    surface_id = surface.get("id")
    expected_side_lane = surface_id != "player_principal_lifecycle"
    if surface.get("side_lane") is not expected_side_lane:
        add(blockers, "surface_side_lane_flag_mismatch", f"{path}.side_lane", expected=expected_side_lane, value=surface.get("side_lane"))
    if surface.get("side_lane_non_counting") is not expected_side_lane:
        add(
            blockers,
            "surface_side_lane_non_counting_flag_mismatch",
            f"{path}.side_lane_non_counting",
            expected=expected_side_lane,
            value=surface.get("side_lane_non_counting"),
        )
    if surface.get("candidate_classification") != "candidate_only_non_counting":
        add(
            blockers,
            "surface_candidate_classification_mismatch",
            f"{path}.candidate_classification",
            value=surface.get("candidate_classification"),
        )
    validate_candidate_only_metadata(
        surface.get("candidate_only_metadata"),
        blockers,
        f"{path}.candidate_only_metadata",
    )
    validate_parallel_capture_boundary(
        surface.get("parallel_capture_boundary"),
        blockers,
        f"{path}.parallel_capture_boundary",
    )
    validate_player_principal_window_composition(
        surface.get("player_principal_window_composition"),
        blockers,
        f"{path}.player_principal_window_composition",
    )
    validate_lifecycle_correlation_metadata(
        surface.get("lifecycle_correlation_metadata"),
        blockers,
        f"{path}.lifecycle_correlation_metadata",
        expected_target=expected_target,
        reason_prefix="surface_lifecycle_correlation_metadata",
    )
    validate_lifecycle_correlation_field_ids(
        surface.get("correlation_field_ids"),
        blockers,
        f"{path}.correlation_field_ids",
        reason_prefix="surface_correlation",
    )
    for key in ("correlation_metadata_required", "correlation_metadata_non_evidence"):
        if surface.get(key) is not True:
            add(blockers, true_reason, f"{path}.{key}", value=surface.get(key))
    validate_non_substitution_flags(
        surface.get("non_substitution_flags"),
        blockers,
        f"{path}.non_substitution_flags",
    )
    expected_role = (
        "optional_parallel_candidate_observation"
        if expected_side_lane
        else "primary_player_principal_lifecycle_window"
    )
    if surface.get("composition_role") != expected_role:
        add(
            blockers,
            "surface_composition_role_mismatch",
            f"{path}.composition_role",
            expected=expected_role,
            value=surface.get("composition_role"),
        )
    if surface.get("optional_parallel_candidate_observation") is not expected_side_lane:
        add(
            blockers,
            "surface_optional_parallel_candidate_observation_mismatch",
            f"{path}.optional_parallel_candidate_observation",
            expected=expected_side_lane,
            value=surface.get("optional_parallel_candidate_observation"),
        )
    if surface.get("parallel_with_player_principal_lifecycle_window") is not expected_side_lane:
        add(
            blockers,
            "surface_parallel_with_player_principal_lifecycle_window_mismatch",
            f"{path}.parallel_with_player_principal_lifecycle_window",
            expected=expected_side_lane,
            value=surface.get("parallel_with_player_principal_lifecycle_window"),
        )
    if surface.get("current_route_blocker") != CURRENT_ROUTE_BLOCKER:
        add(blockers, "surface_current_route_blocker_mismatch", f"{path}.current_route_blocker", value=surface.get("current_route_blocker"))
    if surface.get("required_runtime_evidence") != NEXT_REQUIRED_ARTIFACT:
        add(blockers, "surface_required_runtime_evidence_mismatch", f"{path}.required_runtime_evidence", value=surface.get("required_runtime_evidence"))
    validate_approved_runtime_window_binding(
        surface.get("approved_runtime_window_binding"),
        blockers,
        f"{path}.approved_runtime_window_binding",
        expected_target=expected_target,
        reason_prefix="surface_approved_runtime_window_binding",
    )
    validate_operator_tester_action_metadata(
        surface.get("operator_tester_action_metadata"),
        surface,
        blockers,
        f"{path}.operator_tester_action_metadata",
        expected_target=expected_target,
    )


def validate_checker_command(surface: dict[str, Any], blockers: list[dict[str, Any]], path: str, key: str) -> None:
    command = surface.get(key)
    if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
        add(blockers, "surface_checker_command_missing_or_invalid", f"{path}.{key}", value=command)
        return
    surface_id = surface.get("id")
    expected = EXPECTED_SURFACE_COMMANDS.get(surface_id)
    if expected is None:
        add(blockers, "surface_checker_command_unknown_surface", f"{path}.{key}", surface=surface_id)
        return
    if command != expected:
        add(blockers, "surface_checker_command_mismatch", f"{path}.{key}", expected=expected, value=command)


def validate_resolved_command_template(
    value: Any,
    blockers: list[dict[str, Any]],
    path: str,
    *,
    reason_prefix: str,
) -> None:
    if not isinstance(value, list) or not all(isinstance(part, str) for part in value):
        add(blockers, f"{reason_prefix}_invalid", path, value=value)
        return
    for index, part in enumerate(value):
        if any(fragment in part for fragment in FORBIDDEN_LIVE_PATH_FRAGMENTS):
            add(
                blockers,
                f"{reason_prefix}_live_path_fragment",
                f"{path}[{index}]",
                value=part,
            )


def validate_checker_command_binding_rows(
    value: Any,
    expected: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
    path: str,
    *,
    expected_target: dict[str, str] | None,
    reason_prefix: str,
) -> None:
    if value != expected:
        add(blockers, f"{reason_prefix}_mismatch", path, expected=expected, actual=value)
    if not isinstance(value, list):
        add(blockers, f"{reason_prefix}_missing_or_invalid", path, value=value)
        return
    for index, row in enumerate(value):
        row_path = f"{path}[{index}]"
        if not isinstance(row, dict):
            add(blockers, f"{reason_prefix}_row_invalid", row_path, value=row)
            continue
        validate_capture_artifact_path_template(
            row.get("path_template"),
            blockers,
            f"{row_path}.path_template",
        )
        resolved = row.get("resolved_argument_template")
        if not isinstance(resolved, str) or not resolved.strip():
            add(blockers, f"{reason_prefix}_resolved_argument_missing", f"{row_path}.resolved_argument_template", value=resolved)
        elif any(fragment in resolved for fragment in FORBIDDEN_LIVE_PATH_FRAGMENTS):
            add(blockers, f"{reason_prefix}_resolved_argument_live_path_fragment", f"{row_path}.resolved_argument_template", value=resolved)
        validate_target_binding(
            row.get("target_binding"),
            blockers,
            f"{row_path}.target_binding",
            expected_target=expected_target,
            reason_prefix=f"{reason_prefix}_target_binding",
        )
        validate_target_binding_id(
            row.get("target_binding_id"),
            blockers,
            f"{row_path}.target_binding_id",
            expected_target=expected_target,
            reason_prefix=f"{reason_prefix}_target_binding_id",
        )
        validate_approved_runtime_window_binding(
            row.get("approved_runtime_window_binding"),
            blockers,
            f"{row_path}.approved_runtime_window_binding",
            expected_target=expected_target,
            reason_prefix=f"{reason_prefix}_approved_runtime_window_binding",
        )
        for key in (
            "same_approved_runtime_window_required",
            "target_binding_required",
            "redaction_required",
            "must_not_be_live_server_path",
            "candidate_only",
            "non_evidence",
        ):
            if row.get(key) is not True:
                add(blockers, f"{reason_prefix}_true_flag_missing", f"{row_path}.{key}", value=row.get(key))
        for key in (
            "counts_as_approved_runtime_evidence",
            "counts_as_runtime_evidence",
            "counts_as_sdk_progress",
            "counts_as_p0_progress",
            "clears_approved_runtime_evidence_missing",
        ):
            if row.get(key) is not False:
                add(blockers, f"{reason_prefix}_false_flag_overclaim", f"{row_path}.{key}", value=row.get(key))


def validate_target_bound_checker_command_row(
    value: Any,
    expected: dict[str, Any],
    blockers: list[dict[str, Any]],
    path: str,
    *,
    expected_target: dict[str, str] | None,
    reason_prefix: str,
) -> None:
    if value != expected:
        add(blockers, f"{reason_prefix}_mismatch", path, expected=expected, actual=value)
    if not isinstance(value, dict):
        add(blockers, f"{reason_prefix}_missing_or_invalid", path, value=value)
        return
    if value.get("status") != TARGET_BOUND_CHECKER_COMMAND_MATRIX_STATUS:
        add(blockers, f"{reason_prefix}_status_mismatch", f"{path}.status", value=value.get("status"))
    surface_id = value.get("surface_id")
    validate_checker_command(
        {"id": surface_id, "command": value.get("command")},
        blockers,
        path,
        "command",
    )
    validate_resolved_command_template(
        value.get("resolved_checker_command_template"),
        blockers,
        f"{path}.resolved_checker_command_template",
        reason_prefix=f"{reason_prefix}_resolved_checker_command_template",
    )
    expected_bindings = expected.get("checker_command_bindings")
    validate_checker_command_binding_rows(
        value.get("checker_command_bindings"),
        expected_bindings if isinstance(expected_bindings, list) else [],
        blockers,
        f"{path}.checker_command_bindings",
        expected_target=expected_target,
        reason_prefix=f"{reason_prefix}_checker_command_bindings",
    )
    validate_target_binding(
        value.get("target_binding"),
        blockers,
        f"{path}.target_binding",
        expected_target=expected_target,
        reason_prefix=f"{reason_prefix}_target_binding",
    )
    validate_target_binding_id(
        value.get("target_binding_id"),
        blockers,
        f"{path}.target_binding_id",
        expected_target=expected_target,
        reason_prefix=f"{reason_prefix}_target_binding_id",
    )
    validate_approved_runtime_window_binding(
        value.get("approved_runtime_window_binding"),
        blockers,
        f"{path}.approved_runtime_window_binding",
        expected_target=expected_target,
        reason_prefix=f"{reason_prefix}_approved_runtime_window_binding",
    )
    validate_lifecycle_correlation_metadata(
        value.get("lifecycle_correlation_metadata"),
        blockers,
        f"{path}.lifecycle_correlation_metadata",
        expected_target=expected_target,
        reason_prefix=f"{reason_prefix}_lifecycle_correlation_metadata",
    )
    validate_lifecycle_correlation_field_ids(
        value.get("correlation_field_ids"),
        blockers,
        f"{path}.correlation_field_ids",
        reason_prefix=f"{reason_prefix}_correlation",
    )
    validate_no_restart_action_fields(value, blockers, path, reason_prefix=reason_prefix)
    for key in (
        "offline_template_only",
        "usable_after_redacted_artifact_copy",
        "same_approved_runtime_window_required",
        "exact_target_binding_required",
        "correlation_metadata_required",
        "correlation_metadata_non_evidence",
        "requires_checker_acceptance",
        "requires_player_principal_triplet",
        "candidate_only",
        "non_evidence",
    ):
        if value.get(key) is not True:
            add(blockers, f"{reason_prefix}_true_flag_missing", f"{path}.{key}", value=value.get(key))
    for key in (
        "raw_player_text_retention_allowed",
        "raw_player_text_capture_allowed",
        "raw_chat_payload_capture_allowed",
        "private_player_data_retention_allowed",
        "secrets_or_webhook_retention_allowed",
        "pack_authorizes_player_backed_window",
        "pack_authorizes_runtime_observer",
        "pack_authorizes_marker_or_env_change",
        "pack_authorizes_restart",
        "pack_authorizes_discord",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_progress",
        "counts_as_p0_progress",
        "clears_approved_runtime_evidence_missing",
        "restart_required",
        "server_restart_required",
        "operator_action_requires_restart",
        "tester_action_requires_restart",
        "marker_or_env_change_required",
    ):
        if value.get(key) is not False:
            add(blockers, f"{reason_prefix}_false_flag_overclaim", f"{path}.{key}", value=value.get(key))
    paths = value.get("candidate_artifact_paths")
    if not isinstance(paths, list):
        add(blockers, f"{reason_prefix}_candidate_artifact_paths_invalid", f"{path}.candidate_artifact_paths", value=paths)
    else:
        for path_index, path_template in enumerate(paths):
            validate_capture_artifact_path_template(
                path_template,
                blockers,
                f"{path}.candidate_artifact_paths[{path_index}]",
            )


def validate_surface_command_resolution(
    surface: dict[str, Any],
    blockers: list[dict[str, Any]],
    path: str,
    *,
    expected_target: dict[str, str] | None,
    command_key: str,
    reason_prefix: str,
) -> None:
    command = surface.get(command_key)
    artifacts = surface.get("capture_artifacts")
    if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
        return
    if not isinstance(artifacts, list) or not all(isinstance(item, dict) for item in artifacts):
        return
    try:
        expected_bindings = checker_command_bindings(command, artifacts)
        if isinstance(expected_target, dict):
            expected_bindings = attach_source_metadata(expected_bindings, expected_target)
        expected_resolved = resolved_checker_command_template(command, expected_bindings)
        expected_surface = dict(surface)
        expected_surface["post_capture_checker_command"] = command
        expected_surface["checker_command_bindings"] = expected_bindings
        expected_surface["resolved_checker_command_template"] = expected_resolved
        expected_target_for_attach = expected_target or surface.get("target")
        expected_row = target_bound_checker_command_row(expected_surface)
        if isinstance(expected_target_for_attach, dict):
            expected_row = attach_source_metadata(expected_row, expected_target_for_attach)
    except (KeyError, TypeError, SystemExit) as exc:
        add(blockers, f"{reason_prefix}_expected_build_failed", path, error=str(exc))
        return
    validate_checker_command_binding_rows(
        surface.get("checker_command_bindings"),
        expected_bindings,
        blockers,
        f"{path}.checker_command_bindings",
        expected_target=expected_target,
        reason_prefix=f"{reason_prefix}_checker_command_bindings",
    )
    if surface.get("resolved_checker_command_template") != expected_resolved:
        add(
            blockers,
            f"{reason_prefix}_resolved_checker_command_template_mismatch",
            f"{path}.resolved_checker_command_template",
            expected=expected_resolved,
            actual=surface.get("resolved_checker_command_template"),
        )
    validate_resolved_command_template(
        surface.get("resolved_checker_command_template"),
        blockers,
        f"{path}.resolved_checker_command_template",
        reason_prefix=f"{reason_prefix}_resolved_checker_command_template",
    )
    if surface.get("resolved_checker_command_status") != TARGET_BOUND_CHECKER_COMMAND_MATRIX_STATUS:
        add(
            blockers,
            f"{reason_prefix}_resolved_checker_command_status_mismatch",
            f"{path}.resolved_checker_command_status",
            value=surface.get("resolved_checker_command_status"),
        )
    validate_target_bound_checker_command_row(
        surface.get("target_bound_checker_command"),
        expected_row,
        blockers,
        f"{path}.target_bound_checker_command",
        expected_target=expected_target,
        reason_prefix=f"{reason_prefix}_target_bound_checker_command",
    )


def validate_target_bound_checker_command_matrix(
    value: Any,
    expected: Any,
    blockers: list[dict[str, Any]],
    path: str,
    *,
    expected_target: dict[str, str] | None,
) -> None:
    if value != expected:
        add(blockers, "target_bound_checker_command_matrix_mismatch", path, expected=expected, actual=value)
    if not isinstance(value, dict):
        add(blockers, "target_bound_checker_command_matrix_missing_or_invalid", path, value=value)
        return
    if value.get("id") != TARGET_BOUND_CHECKER_COMMAND_MATRIX_ID:
        add(blockers, "target_bound_checker_command_matrix_id_mismatch", f"{path}.id", expected=TARGET_BOUND_CHECKER_COMMAND_MATRIX_ID, actual=value.get("id"))
    if value.get("status") != TARGET_BOUND_CHECKER_COMMAND_MATRIX_STATUS:
        add(blockers, "target_bound_checker_command_matrix_status_mismatch", f"{path}.status", value=value.get("status"))
    if value.get("matrix_status") != "candidate_only_non_evidence":
        add(blockers, "target_bound_checker_command_matrix_status_mismatch", f"{path}.matrix_status", value=value.get("matrix_status"))
    validate_target(
        value.get("target"),
        blockers,
        f"{path}.target",
        expected_target=expected_target,
        reason_prefix="target_bound_checker_command_matrix_target",
    )
    validate_target_binding(
        value.get("target_binding"),
        blockers,
        f"{path}.target_binding",
        expected_target=expected_target,
        reason_prefix="target_bound_checker_command_matrix_target_binding",
    )
    validate_target_binding_id(
        value.get("target_binding_id"),
        blockers,
        f"{path}.target_binding_id",
        expected_target=expected_target,
        reason_prefix="target_bound_checker_command_matrix_target_binding_id",
    )
    validate_approved_runtime_window_binding(
        value.get("approved_runtime_window_binding"),
        blockers,
        f"{path}.approved_runtime_window_binding",
        expected_target=expected_target,
        reason_prefix="target_bound_checker_command_matrix_approved_runtime_window_binding",
    )
    validate_lifecycle_correlation_metadata(
        value.get("lifecycle_correlation_metadata"),
        blockers,
        f"{path}.lifecycle_correlation_metadata",
        expected_target=expected_target,
        reason_prefix="target_bound_checker_command_matrix_lifecycle_correlation_metadata",
    )
    validate_lifecycle_correlation_field_ids(
        value.get("correlation_field_ids"),
        blockers,
        f"{path}.correlation_field_ids",
        reason_prefix="target_bound_checker_command_matrix_correlation",
    )
    validate_no_restart_action_fields(
        value,
        blockers,
        path,
        reason_prefix="target_bound_checker_command_matrix",
    )
    validate_text_privacy_boundary(
        value.get("text_privacy_boundary"),
        blockers,
        f"{path}.text_privacy_boundary",
    )
    check_non_claim_flags(value.get("non_claim_flags"), blockers, f"{path}.non_claim_flags")
    for key in (
        "all_rows_target_bound",
        "all_rows_offline_templates_only",
        "all_rows_require_redacted_artifact_copy",
        "scalar_arguments_use_read_text_templates",
        "path_arguments_use_candidate_artifact_templates",
        "candidate_only",
        "non_evidence",
        "correlation_metadata_required",
        "correlation_metadata_non_evidence",
        "requires_checker_acceptance",
        "requires_player_principal_triplet",
        "same_approved_runtime_window_required",
        "exact_target_binding_required",
        "no_restart_required",
        "operator_actions_do_not_require_restart",
        "tester_actions_do_not_require_restart",
        "no_marker_or_env_change_required",
    ):
        if value.get(key) is not True:
            add(blockers, "target_bound_checker_command_matrix_true_flag_missing", f"{path}.{key}", value=value.get(key))
    for key in (
        "raw_player_text_retention_allowed",
        "raw_player_text_capture_allowed",
        "raw_chat_payload_capture_allowed",
        "private_player_data_retention_allowed",
        "secrets_or_webhook_retention_allowed",
        "pack_authorizes_player_backed_window",
        "pack_authorizes_runtime_observer",
        "pack_authorizes_marker_or_env_change",
        "pack_authorizes_restart",
        "pack_authorizes_discord",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_progress",
        "counts_as_p0_progress",
        "clears_approved_runtime_evidence_missing",
        "restart_required",
        "server_restart_required",
        "operator_action_requires_restart",
        "tester_action_requires_restart",
        "marker_or_env_change_required",
    ):
        if value.get(key) is not False:
            add(blockers, "target_bound_checker_command_matrix_false_flag_overclaim", f"{path}.{key}", value=value.get(key))
    if value.get("current_route_blocker") != CURRENT_ROUTE_BLOCKER:
        add(blockers, "target_bound_checker_command_matrix_route_blocker_mismatch", f"{path}.current_route_blocker", value=value.get("current_route_blocker"))
    if value.get("required_runtime_evidence") != NEXT_REQUIRED_ARTIFACT:
        add(blockers, "target_bound_checker_command_matrix_required_evidence_mismatch", f"{path}.required_runtime_evidence", value=value.get("required_runtime_evidence"))
    rows = value.get("rows")
    expected_rows = expected.get("rows") if isinstance(expected, dict) else None
    if not isinstance(rows, list):
        add(blockers, "target_bound_checker_command_matrix_rows_missing_or_invalid", f"{path}.rows", value=rows)
        return
    if value.get("row_count") != len(rows):
        add(blockers, "target_bound_checker_command_matrix_row_count_mismatch", f"{path}.row_count", expected=len(rows), actual=value.get("row_count"))
    if isinstance(expected_rows, list) and rows != expected_rows:
        add(blockers, "target_bound_checker_command_matrix_rows_mismatch", f"{path}.rows", expected=expected_rows, actual=rows)
    expected_by_surface = {
        row.get("surface_id"): row
        for row in expected_rows
        if isinstance(expected_rows, list) and isinstance(row, dict)
    } if isinstance(expected_rows, list) else {}
    observed_ids = [row.get("surface_id") for row in rows if isinstance(row, dict)]
    expected_ids = [surface["id"] for surface in PLAN_SURFACES]
    if observed_ids != expected_ids:
        add(blockers, "target_bound_checker_command_matrix_row_order_mismatch", f"{path}.rows", expected=expected_ids, actual=observed_ids)
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            add(blockers, "target_bound_checker_command_matrix_row_invalid", f"{path}.rows[{index}]", value=row)
            continue
        expected_row = expected_by_surface.get(row.get("surface_id"), {})
        validate_target_bound_checker_command_row(
            row,
            expected_row,
            blockers,
            f"{path}.rows[{index}]",
            expected_target=expected_target,
            reason_prefix="target_bound_checker_command_matrix_row",
        )


def validate_side_lane_capture_queue(
    value: Any,
    expected: Any,
    blockers: list[dict[str, Any]],
    path: str,
    *,
    expected_target: dict[str, str] | None,
) -> None:
    if not isinstance(value, dict):
        add(blockers, "side_lane_capture_queue_missing_or_invalid", path, value=value)
        return
    if not isinstance(expected, dict):
        add(blockers, "side_lane_capture_queue_expected_missing", path, expected=expected)
        return
    if value != expected:
        add(blockers, "side_lane_capture_queue_mismatch", path, expected=expected, actual=value)
    if value.get("id") != SIDE_LANE_CAPTURE_QUEUE_ID:
        add(blockers, "side_lane_capture_queue_id_mismatch", f"{path}.id", expected=SIDE_LANE_CAPTURE_QUEUE_ID, actual=value.get("id"))
    if value.get("status") != SIDE_LANE_CAPTURE_QUEUE_STATUS:
        add(blockers, "side_lane_capture_queue_status_mismatch", f"{path}.status", value=value.get("status"))
    if value.get("queue_status") != "candidate_only_non_evidence":
        add(blockers, "side_lane_capture_queue_status_mismatch", f"{path}.queue_status", value=value.get("queue_status"))
    if value.get("surface_ids") != list(PARALLEL_BETA_CAPTURE_SURFACE_IDS):
        add(blockers, "side_lane_capture_queue_surface_ids_mismatch", f"{path}.surface_ids", expected=list(PARALLEL_BETA_CAPTURE_SURFACE_IDS), actual=value.get("surface_ids"))
    if value.get("action_group_ids") != list(PARALLEL_BETA_CAPTURE_ACTION_GROUP_IDS):
        add(blockers, "side_lane_capture_queue_action_group_ids_mismatch", f"{path}.action_group_ids", expected=list(PARALLEL_BETA_CAPTURE_ACTION_GROUP_IDS), actual=value.get("action_group_ids"))
    if value.get("primary_surface_id") != "player_principal_lifecycle":
        add(blockers, "side_lane_capture_queue_primary_surface_mismatch", f"{path}.primary_surface_id", value=value.get("primary_surface_id"))
    if value.get("primary_route_blocker") != CURRENT_ROUTE_BLOCKER:
        add(blockers, "side_lane_capture_queue_route_blocker_mismatch", f"{path}.primary_route_blocker", value=value.get("primary_route_blocker"))
    if value.get("required_primary_evidence") != NEXT_REQUIRED_ARTIFACT:
        add(blockers, "side_lane_capture_queue_required_evidence_mismatch", f"{path}.required_primary_evidence", value=value.get("required_primary_evidence"))
    if value.get("required_primary_triplet") != STRICT_PLAYER_PRINCIPAL_TRIPLET:
        add(blockers, "side_lane_capture_queue_required_triplet_mismatch", f"{path}.required_primary_triplet", value=value.get("required_primary_triplet"))
    validate_target(
        value.get("target"),
        blockers,
        f"{path}.target",
        expected_target=expected_target,
        reason_prefix="side_lane_capture_queue_target",
    )
    validate_target_binding(
        value.get("target_binding"),
        blockers,
        f"{path}.target_binding",
        expected_target=expected_target,
        reason_prefix="side_lane_capture_queue_target_binding",
    )
    validate_target_binding_id(
        value.get("target_binding_id"),
        blockers,
        f"{path}.target_binding_id",
        expected_target=expected_target,
        reason_prefix="side_lane_capture_queue_target_binding_id",
    )
    validate_approved_runtime_window_binding(
        value.get("approved_runtime_window_binding"),
        blockers,
        f"{path}.approved_runtime_window_binding",
        expected_target=expected_target,
        reason_prefix="side_lane_capture_queue_approved_runtime_window_binding",
    )
    validate_lifecycle_correlation_metadata(
        value.get("lifecycle_correlation_metadata"),
        blockers,
        f"{path}.lifecycle_correlation_metadata",
        expected_target=expected_target,
        reason_prefix="side_lane_capture_queue_lifecycle_correlation_metadata",
    )
    validate_lifecycle_correlation_field_ids(
        value.get("correlation_field_ids"),
        blockers,
        f"{path}.correlation_field_ids",
        reason_prefix="side_lane_capture_queue_correlation",
    )
    validate_no_restart_action_fields(
        value,
        blockers,
        path,
        reason_prefix="side_lane_capture_queue",
    )
    validate_non_substitution_flags(value.get("non_substitution_flags"), blockers, f"{path}.non_substitution_flags")
    check_non_claim_flags(value.get("non_claim_flags"), blockers, f"{path}.non_claim_flags")
    for key in (
        "same_approved_runtime_window_required",
        "exact_target_binding_required",
        "copy_to_offline_workspace_before_checker",
        "redaction_required_before_checker_intake",
        "correlation_metadata_required",
        "correlation_metadata_non_evidence",
        "candidate_only",
        "non_evidence",
        "side_lane_non_counting",
        "primary_route_acceptance_required_before_counting",
        "own_checker_required_before_surface_claim",
        "blocked_by_player_principal_evidence",
        "requires_player_principal_triplet",
        "requires_checker_acceptance",
        "no_restart_required",
        "operator_actions_do_not_require_restart",
        "tester_actions_do_not_require_restart",
        "no_marker_or_env_change_required",
    ):
        if value.get(key) is not True:
            add(blockers, "side_lane_capture_queue_true_flag_missing", f"{path}.{key}", value=value.get(key))
    for key in (
        "pack_authorizes_player_backed_window",
        "pack_authorizes_runtime_observer",
        "pack_authorizes_marker_or_env_change",
        "pack_authorizes_restart",
        "pack_authorizes_discord",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_progress",
        "counts_as_p0_progress",
        "clears_approved_runtime_evidence_missing",
        "replaces_player_principal_evidence",
        "replaces_player_principal_triplet",
        "substitutes_for_player_principal_lifecycle_evidence",
        "primary_evidence_substitution_allowed",
        "side_lane_collection_can_replace_player_principal_evidence",
        "side_lane_collection_counts_before_checker_acceptance",
        "side_lane_counts_toward_sdk",
        "side_lane_counts_toward_p0",
        "runtime_ready",
        "public_sdk_ready",
        "stable_sdk_ready",
        "restart_required",
        "server_restart_required",
        "operator_action_requires_restart",
        "tester_action_requires_restart",
        "marker_or_env_change_required",
    ):
        if value.get(key) is not False:
            add(blockers, "side_lane_capture_queue_false_flag_overclaim", f"{path}.{key}", value=value.get(key))
    rows = value.get("rows")
    expected_rows = expected.get("rows")
    if not isinstance(rows, list):
        add(blockers, "side_lane_capture_queue_rows_missing_or_invalid", f"{path}.rows", value=rows)
        return
    if rows != expected_rows:
        add(blockers, "side_lane_capture_queue_rows_mismatch", f"{path}.rows", expected=expected_rows, actual=rows)
    if value.get("row_count") != len(rows):
        add(blockers, "side_lane_capture_queue_row_count_mismatch", f"{path}.row_count", expected=len(rows), actual=value.get("row_count"))
    observed_ids = [row.get("surface_id") for row in rows if isinstance(row, dict)]
    if observed_ids != list(PARALLEL_BETA_CAPTURE_SURFACE_IDS):
        add(blockers, "side_lane_capture_queue_row_order_mismatch", f"{path}.rows", expected=list(PARALLEL_BETA_CAPTURE_SURFACE_IDS), actual=observed_ids)
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            add(blockers, "side_lane_capture_queue_row_invalid", f"{path}.rows[{index}]", value=row)
            continue
        surface_id = row.get("surface_id")
        if row.get("queue_order") != index + 1:
            add(blockers, "side_lane_capture_queue_row_order_value_mismatch", f"{path}.rows[{index}].queue_order", expected=index + 1, actual=row.get("queue_order"))
        if row.get("status") != SIDE_LANE_CAPTURE_QUEUE_STATUS:
            add(blockers, "side_lane_capture_queue_row_status_mismatch", f"{path}.rows[{index}].status", value=row.get("status"))
        if row.get("primary_route_blocker") != CURRENT_ROUTE_BLOCKER:
            add(blockers, "side_lane_capture_queue_row_blocker_mismatch", f"{path}.rows[{index}].primary_route_blocker", value=row.get("primary_route_blocker"))
        if row.get("required_primary_evidence") != NEXT_REQUIRED_ARTIFACT:
            add(blockers, "side_lane_capture_queue_row_required_evidence_mismatch", f"{path}.rows[{index}].required_primary_evidence", value=row.get("required_primary_evidence"))
        if row.get("required_primary_triplet") != STRICT_PLAYER_PRINCIPAL_TRIPLET:
            add(blockers, "side_lane_capture_queue_row_required_triplet_mismatch", f"{path}.rows[{index}].required_primary_triplet", value=row.get("required_primary_triplet"))
        validate_target_binding(
            row.get("target_binding"),
            blockers,
            f"{path}.rows[{index}].target_binding",
            expected_target=expected_target,
            reason_prefix="side_lane_capture_queue_row_target_binding",
        )
        validate_target_binding_id(
            row.get("target_binding_id"),
            blockers,
            f"{path}.rows[{index}].target_binding_id",
            expected_target=expected_target,
            reason_prefix="side_lane_capture_queue_row_target_binding_id",
        )
        validate_approved_runtime_window_binding(
            row.get("approved_runtime_window_binding"),
            blockers,
            f"{path}.rows[{index}].approved_runtime_window_binding",
            expected_target=expected_target,
            reason_prefix="side_lane_capture_queue_row_approved_runtime_window_binding",
        )
        validate_lifecycle_correlation_metadata(
            row.get("lifecycle_correlation_metadata"),
            blockers,
            f"{path}.rows[{index}].lifecycle_correlation_metadata",
            expected_target=expected_target,
            reason_prefix="side_lane_capture_queue_row_lifecycle_correlation_metadata",
        )
        validate_lifecycle_correlation_field_ids(
            row.get("correlation_field_ids"),
            blockers,
            f"{path}.rows[{index}].correlation_field_ids",
            reason_prefix="side_lane_capture_queue_row_correlation",
        )
        validate_no_restart_action_fields(
            row,
            blockers,
            f"{path}.rows[{index}]",
            reason_prefix="side_lane_capture_queue_row",
            text_keys=("operator_next_action", "lead_next_action", "tester_brief", "tester_action"),
            list_keys=("resolved_checker_command_template", "candidate_artifact_ids", "candidate_artifact_paths"),
        )
        if row.get("checker") != EXPECTED_SURFACE_CHECKERS.get(surface_id):
            add(blockers, "side_lane_capture_queue_row_checker_mismatch", f"{path}.rows[{index}].checker", value=row.get("checker"))
        for key in (
            "same_approved_runtime_window_required",
            "exact_target_binding_required",
            "copy_to_offline_workspace_before_checker",
            "redaction_required_before_checker_intake",
            "correlation_metadata_required",
            "correlation_metadata_non_evidence",
            "candidate_only",
            "non_evidence",
            "side_lane",
            "side_lane_non_counting",
            "may_queue_with_primary_window",
            "primary_route_acceptance_required_before_counting",
            "own_checker_required_before_surface_claim",
            "blocked_by_player_principal_evidence",
            "requires_player_principal_triplet",
            "requires_checker_acceptance",
            "no_restart_required",
            "operator_actions_do_not_require_restart",
            "tester_actions_do_not_require_restart",
            "no_marker_or_env_change_required",
        ):
            if row.get(key) is not True:
                add(blockers, "side_lane_capture_queue_row_true_flag_missing", f"{path}.rows[{index}].{key}", value=row.get(key))
        for key in (
            "counts_as_approved_runtime_evidence",
            "counts_as_runtime_evidence",
            "counts_as_sdk_progress",
            "counts_as_p0_progress",
            "clears_approved_runtime_evidence_missing",
            "replaces_player_principal_evidence",
            "replaces_player_principal_triplet",
            "substitutes_for_player_principal_lifecycle_evidence",
            "primary_evidence_substitution_allowed",
            "runtime_ready",
            "public_sdk_ready",
            "stable_sdk_ready",
            "restart_required",
            "server_restart_required",
            "operator_action_requires_restart",
            "tester_action_requires_restart",
            "marker_or_env_change_required",
        ):
            if row.get(key) is not False:
                add(blockers, "side_lane_capture_queue_row_false_flag_overclaim", f"{path}.rows[{index}].{key}", value=row.get(key))


def checker_placeholders(surface: dict[str, Any]) -> set[str]:
    for key in ("checker_args", "command", "post_capture_checker_command"):
        value = surface.get(key)
        if isinstance(value, list) and all(isinstance(part, str) for part in value):
            return {part for part in value if part.startswith("<") and part.endswith(">")}
    return set()


def validate_capture_artifacts(
    surface: dict[str, Any],
    blockers: list[dict[str, Any]],
    path: str,
    *,
    expected_target: dict[str, str] | None,
) -> None:
    surface_id = surface.get("id")
    if not isinstance(surface_id, str):
        add(blockers, "surface_id_missing_or_invalid", f"{path}.id", value=surface_id)
        return
    if expected_target is None:
        add(blockers, "capture_artifacts_expected_target_missing", path)
        expected = EXPECTED_CAPTURE_ARTIFACTS_BY_SURFACE.get(surface_id)
    else:
        expected = attach_source_metadata(
            capture_artifacts_for(surface_id, expected_target),
            expected_target,
        )
    if expected is None:
        add(blockers, "capture_artifacts_unknown_surface", f"{path}.capture_artifacts", surface=surface_id)
        return
    artifacts = surface.get("capture_artifacts")
    if not isinstance(artifacts, list):
        add(blockers, "capture_artifacts_missing_or_invalid", f"{path}.capture_artifacts", value=artifacts)
        return
    if surface.get("candidate_artifact_count") != len(expected):
        add(
            blockers,
            "candidate_artifact_count_mismatch",
            f"{path}.candidate_artifact_count",
            expected=len(expected),
            actual=surface.get("candidate_artifact_count"),
        )
    valid_artifacts = [artifact for artifact in artifacts if isinstance(artifact, dict)]
    if len(valid_artifacts) != len(artifacts):
        add(blockers, "capture_artifact_entry_invalid", f"{path}.capture_artifacts")
    expected_by_id = {artifact["id"]: artifact for artifact in expected}
    observed_ids = [artifact.get("id") for artifact in valid_artifacts]
    string_ids = [artifact_id for artifact_id in observed_ids if isinstance(artifact_id, str)]
    duplicate_ids = sorted({artifact_id for artifact_id in string_ids if string_ids.count(artifact_id) > 1})
    if duplicate_ids:
        add(blockers, "capture_artifacts_duplicate_ids", f"{path}.capture_artifacts", duplicates=duplicate_ids)
    if string_ids != [artifact["id"] for artifact in expected]:
        add(
            blockers,
            "capture_artifacts_binding_mismatch",
            f"{path}.capture_artifacts",
            expected=[artifact["id"] for artifact in expected],
            actual=string_ids,
        )
    for index, artifact in enumerate(valid_artifacts):
        artifact_path = f"{path}.capture_artifacts[{index}]"
        artifact_id = artifact.get("id")
        if not isinstance(artifact_id, str):
            add(blockers, "capture_artifact_id_missing_or_invalid", f"{artifact_path}.id", value=artifact_id)
            continue
        expected_artifact = expected_by_id.get(artifact_id)
        if expected_artifact is None:
            add(blockers, "capture_artifact_unexpected", artifact_path, value=artifact_id)
            continue
        expected_keys = set(expected_artifact)
        actual_keys = set(artifact)
        if actual_keys != expected_keys:
            add(
                blockers,
                "capture_artifact_keys_mismatch",
                artifact_path,
                expected=sorted(expected_keys),
                actual=sorted(actual_keys),
            )
        for key in expected_keys | actual_keys:
            if artifact.get(key) != expected_artifact.get(key):
                add(
                    blockers,
                    "capture_artifact_field_mismatch",
                    f"{artifact_path}.{key}",
                    expected=expected_artifact.get(key),
                    actual=artifact.get(key),
                )
        validate_capture_artifact_path_template(
            artifact.get("path_template"),
            blockers,
            f"{artifact_path}.path_template",
        )
        checker_input = artifact.get("checker_input")
        if checker_input is not None and (
            not isinstance(checker_input, str)
            or not checker_input.startswith("<")
            or not checker_input.endswith(">")
        ):
            add(blockers, "capture_artifact_checker_input_invalid", f"{artifact_path}.checker_input", value=checker_input)
        for key in REQUIRED_TRUE_ARTIFACT_FLAGS:
            if artifact.get(key) is not True:
                add(blockers, "capture_artifact_required_true_flag_missing", f"{artifact_path}.{key}", value=artifact.get(key))
        for key in REQUIRED_FALSE_ARTIFACT_FLAGS:
            if artifact.get(key) is not False:
                add(blockers, "capture_artifact_false_flag_overclaim", f"{artifact_path}.{key}", value=artifact.get(key))
        validate_target_binding(
            artifact.get("target_binding"),
            blockers,
            f"{artifact_path}.target_binding",
            expected_target=expected_target,
            reason_prefix="capture_artifact_target_binding",
        )
        if isinstance(artifact.get("target_binding"), dict):
            validate_target_binding_id(
                artifact["target_binding"].get("binding_id"),
                blockers,
                f"{artifact_path}.target_binding.binding_id",
                expected_target=expected_target,
                reason_prefix="capture_artifact_target_binding_id",
            )
        validate_approved_runtime_window_binding(
            artifact.get("approved_runtime_window_binding"),
            blockers,
            f"{artifact_path}.approved_runtime_window_binding",
            expected_target=expected_target,
            reason_prefix="capture_artifact_approved_runtime_window_binding",
        )
        validate_lifecycle_correlation_metadata(
            artifact.get("lifecycle_correlation_metadata"),
            blockers,
            f"{artifact_path}.lifecycle_correlation_metadata",
            expected_target=expected_target,
            reason_prefix="capture_artifact_lifecycle_correlation_metadata",
        )
        validate_lifecycle_correlation_field_ids(
            artifact.get("correlation_field_ids"),
            blockers,
            f"{artifact_path}.correlation_field_ids",
            reason_prefix="capture_artifact_correlation",
        )
        for key in ("correlation_metadata_required", "correlation_metadata_non_evidence"):
            if artifact.get(key) is not True:
                add(
                    blockers,
                    "capture_artifact_required_true_flag_missing",
                    f"{artifact_path}.{key}",
                    value=artifact.get(key),
                )
        validate_artifact_intake_constraints(
            artifact.get("artifact_intake_constraints"),
            blockers,
            f"{artifact_path}.artifact_intake_constraints",
        )
        validate_redaction_policy(
            artifact.get("redaction_policy"),
            blockers,
            f"{artifact_path}.redaction_policy",
        )
        validate_candidate_only_metadata(
            artifact.get("candidate_only_metadata"),
            blockers,
            f"{artifact_path}.candidate_only_metadata",
        )
        validate_parallel_capture_boundary(
            artifact.get("parallel_capture_boundary"),
            blockers,
            f"{artifact_path}.parallel_capture_boundary",
        )
        validate_non_substitution_flags(
            artifact.get("non_substitution_flags"),
            blockers,
            f"{artifact_path}.non_substitution_flags",
        )
        redaction_note = artifact.get("redaction_note")
        if not isinstance(redaction_note, str):
            add(blockers, "capture_artifact_redaction_note_invalid", f"{artifact_path}.redaction_note", value=redaction_note)
        else:
            for token in REQUIRED_REDACTION_TOKENS:
                if token not in redaction_note:
                    add(blockers, "capture_artifact_redaction_note_missing_token", f"{artifact_path}.redaction_note", token=token)
        check_non_claim_flags(artifact.get("non_claim_flags"), blockers, f"{artifact_path}.non_claim_flags")
    placeholders = checker_placeholders(surface)
    artifact_inputs = {
        artifact.get("checker_input")
        for artifact in valid_artifacts
        if isinstance(artifact.get("checker_input"), str)
    }
    missing_inputs = sorted(placeholders - artifact_inputs)
    if missing_inputs:
        add(blockers, "capture_artifact_checker_input_missing", f"{path}.capture_artifacts", missing=missing_inputs)
    unused_required_inputs = sorted(
        artifact.get("checker_input")
        for artifact in valid_artifacts
        if artifact.get("required_for_checker") is True
        and isinstance(artifact.get("checker_input"), str)
        and artifact.get("checker_input") not in placeholders
    )
    if unused_required_inputs:
        add(blockers, "capture_artifact_checker_input_unused", f"{path}.capture_artifacts", unused=unused_required_inputs)
    validate_required_checker_artifacts(surface, valid_artifacts, blockers, path)


def check_no_duplicate_strings(value: Any, blockers: list[dict[str, Any]], path: str, reason: str) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        add(blockers, reason.replace("_duplicate", "_invalid"), path, value=value)
        return set()
    duplicates = sorted({item for item in value if value.count(item) > 1})
    if duplicates:
        add(blockers, reason, path, duplicates=duplicates)
    return set(value)


def validate_surface_collection(
    surfaces: Any,
    blockers: list[dict[str, Any]],
    path: str,
    *,
    reason_prefix: str,
    require_priority: bool,
) -> list[dict[str, Any]]:
    if not isinstance(surfaces, list):
        add(blockers, f"{reason_prefix}_missing", path)
        return []
    for index, surface in enumerate(surfaces):
        if not isinstance(surface, dict):
            add(blockers, f"{reason_prefix}_entry_invalid", f"{path}[{index}]")
    valid_surfaces = [surface for surface in surfaces if isinstance(surface, dict)]
    ids = [surface.get("id") for surface in valid_surfaces]
    string_ids = [surface_id for surface_id in ids if isinstance(surface_id, str)]
    duplicate_ids = sorted({surface_id for surface_id in string_ids if string_ids.count(surface_id) > 1})
    if duplicate_ids:
        add(blockers, f"{reason_prefix}_duplicate_ids", path, duplicates=duplicate_ids)
    observed = set(string_ids)
    if observed != EXPECTED_SURFACES:
        add(
            blockers,
            f"{reason_prefix}_mismatch",
            path,
            expected=sorted(EXPECTED_SURFACES),
            actual=sorted(observed),
        )
    if len(surfaces) != len(EXPECTED_SURFACES):
        add(
            blockers,
            f"{reason_prefix}_count_mismatch",
            path,
            expected=len(EXPECTED_SURFACES),
            actual=len(surfaces),
        )
    if require_priority:
        priorities = [surface.get("priority") for surface in valid_surfaces]
        int_priorities = [priority for priority in priorities if isinstance(priority, int)]
        duplicate_priorities = sorted({priority for priority in int_priorities if int_priorities.count(priority) > 1})
        if duplicate_priorities:
            add(blockers, f"{reason_prefix}_duplicate_priorities", path, duplicates=duplicate_priorities)
        if sorted(int_priorities) != list(range(1, len(EXPECTED_SURFACES) + 1)):
            add(
                blockers,
                f"{reason_prefix}_priority_sequence_mismatch",
                path,
                expected=list(range(1, len(EXPECTED_SURFACES) + 1)),
                actual=sorted(int_priorities),
            )
    return valid_surfaces


def validate_expected_surface_binding(surface: dict[str, Any], blockers: list[dict[str, Any]], path: str) -> None:
    surface_id = surface.get("id")
    if not isinstance(surface_id, str):
        add(blockers, "surface_id_missing_or_invalid", f"{path}.id", value=surface_id)
        return
    expected_checker = EXPECTED_SURFACE_CHECKERS.get(surface_id)
    if expected_checker is None:
        return
    if surface.get("checker") != expected_checker:
        add(
            blockers,
            "surface_checker_binding_mismatch",
            f"{path}.checker",
            expected=expected_checker,
            actual=surface.get("checker"),
        )
    checker_path = Path(expected_checker)
    if checker_path.is_absolute() or ".." in checker_path.parts or checker_path.parts[:1] != ("scripts",):
        add(blockers, "surface_checker_path_invalid", f"{path}.checker", value=expected_checker)
    elif not (REPO_ROOT / checker_path).is_file():
        add(blockers, "surface_checker_file_missing", f"{path}.checker", value=expected_checker)
    if "objective" in surface and surface.get("objective") != EXPECTED_SURFACE_OBJECTIVES.get(surface_id):
        add(
            blockers,
            "surface_objective_binding_mismatch",
            f"{path}.objective",
            expected=EXPECTED_SURFACE_OBJECTIVES.get(surface_id),
            actual=surface.get("objective"),
        )
    if surface.get("operator_action") != EXPECTED_SURFACE_OPERATOR_ACTIONS.get(surface_id):
        add(
            blockers,
            "surface_operator_action_binding_mismatch",
            f"{path}.operator_action",
            expected=EXPECTED_SURFACE_OPERATOR_ACTIONS.get(surface_id),
            actual=surface.get("operator_action"),
        )
    if surface.get("tester_action") != EXPECTED_SURFACE_TESTER_ACTIONS.get(surface_id):
        add(
            blockers,
            "surface_tester_action_binding_mismatch",
            f"{path}.tester_action",
            expected=EXPECTED_SURFACE_TESTER_ACTIONS.get(surface_id),
            actual=surface.get("tester_action"),
        )
    if "priority" in surface and surface.get("priority") != EXPECTED_SURFACE_PRIORITIES.get(surface_id):
        add(
            blockers,
            "surface_priority_binding_mismatch",
            f"{path}.priority",
            expected=EXPECTED_SURFACE_PRIORITIES.get(surface_id),
            actual=surface.get("priority"),
        )


def expected_surface_entries_for_target(target: dict[str, str]) -> list[dict[str, Any]]:
    return attach_source_metadata([
        surface_entry(surface, index, target)
        for index, surface in enumerate(PLAN_SURFACES, start=1)
    ], target)


def validate_manifest(
    pack_root: Path,
    manifest: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    expected_target: dict[str, str] | None = None,
) -> None:
    if manifest.get("schema") != PACK_SCHEMA:
        add(blockers, "manifest_schema_mismatch", "$.schema", expected=PACK_SCHEMA, actual=manifest.get("schema"))
    if manifest.get("status") != "candidate_capture_pack":
        add(blockers, "manifest_status_mismatch", "$.status", actual=manifest.get("status"))
    if manifest.get("non_authorization") != NON_AUTHORIZATION:
        add(blockers, "manifest_non_authorization_mismatch", "$.non_authorization")
    target = validate_target(
        manifest.get("target"),
        blockers,
        "$.target",
        expected_target=expected_target,
        reason_prefix="manifest_target",
    )
    validate_target_binding(
        manifest.get("target_binding"),
        blockers,
        "$.target_binding",
        expected_target=target,
        expected_source="operator_cli",
        reason_prefix="manifest_target_binding",
    )
    validate_target_binding_id(
        manifest.get("target_binding_id"),
        blockers,
        "$.target_binding_id",
        expected_target=target,
        reason_prefix="manifest_target_binding_id",
    )
    validate_target_binding(
        manifest.get("plan_target_binding"),
        blockers,
        "$.plan_target_binding",
        expected_target=target,
        reason_prefix="manifest_plan_target_binding",
    )
    validate_target_binding_id(
        manifest.get("plan_target_binding_id"),
        blockers,
        "$.plan_target_binding_id",
        expected_target=target,
        reason_prefix="manifest_plan_target_binding_id",
    )
    validate_approved_runtime_window_binding(
        manifest.get("approved_runtime_window_binding"),
        blockers,
        "$.approved_runtime_window_binding",
        expected_target=target,
        reason_prefix="manifest_approved_runtime_window_binding",
    )
    if manifest.get("candidate_surface_count") != len(EXPECTED_SURFACES):
        add(
            blockers,
            "manifest_candidate_surface_count_mismatch",
            "$.candidate_surface_count",
            expected=len(EXPECTED_SURFACES),
            actual=manifest.get("candidate_surface_count"),
        )
    expected_artifact_count = sum(len(artifacts) for artifacts in EXPECTED_CAPTURE_ARTIFACTS_BY_SURFACE.values())
    if manifest.get("candidate_artifact_count") != expected_artifact_count:
        add(
            blockers,
            "manifest_candidate_artifact_count_mismatch",
            "$.candidate_artifact_count",
            expected=expected_artifact_count,
            actual=manifest.get("candidate_artifact_count"),
        )
    if manifest.get("current_route_blocker") != CURRENT_ROUTE_BLOCKER:
        add(blockers, "manifest_current_route_blocker_mismatch", "$.current_route_blocker", value=manifest.get("current_route_blocker"))
    if manifest.get("next_required_artifact") != NEXT_REQUIRED_ARTIFACT:
        add(blockers, "manifest_next_required_artifact_mismatch", "$.next_required_artifact", value=manifest.get("next_required_artifact"))
    if manifest.get("side_lanes_non_counting_before_player_principal") is not True:
        add(
            blockers,
            "manifest_side_lanes_non_counting_before_player_principal_not_true",
            "$.side_lanes_non_counting_before_player_principal",
            value=manifest.get("side_lanes_non_counting_before_player_principal"),
        )
    if manifest.get("checker_matrix_includes_command_templates") is not True:
        add(
            blockers,
            "manifest_checker_matrix_command_templates_not_true",
            "$.checker_matrix_includes_command_templates",
            value=manifest.get("checker_matrix_includes_command_templates"),
        )
    if manifest.get("candidate_artifact_intake_included") is not True:
        add(
            blockers,
            "manifest_candidate_artifact_intake_not_included",
            "$.candidate_artifact_intake_included",
            value=manifest.get("candidate_artifact_intake_included"),
        )
    if manifest.get("broad_beta_capture_candidate_worksheet_included") is not True:
        add(
            blockers,
            "manifest_broad_beta_capture_candidate_worksheet_not_included",
            "$.broad_beta_capture_candidate_worksheet_included",
            value=manifest.get("broad_beta_capture_candidate_worksheet_included"),
        )
    if manifest.get("broad_beta_capture_candidate_worksheet_template") != BROAD_BETA_CAPTURE_WORKSHEET_FILE:
        add(
            blockers,
            "manifest_broad_beta_capture_candidate_worksheet_template_mismatch",
            "$.broad_beta_capture_candidate_worksheet_template",
            expected=BROAD_BETA_CAPTURE_WORKSHEET_FILE,
            actual=manifest.get("broad_beta_capture_candidate_worksheet_template"),
        )
    if manifest.get("broad_beta_capture_candidate_worksheet_schema") != BROAD_BETA_CAPTURE_WORKSHEET_SCHEMA:
        add(
            blockers,
            "manifest_broad_beta_capture_candidate_worksheet_schema_mismatch",
            "$.broad_beta_capture_candidate_worksheet_schema",
            expected=BROAD_BETA_CAPTURE_WORKSHEET_SCHEMA,
            actual=manifest.get("broad_beta_capture_candidate_worksheet_schema"),
        )
    if manifest.get("broad_beta_capture_candidate_worksheet_id") != BROAD_BETA_CAPTURE_WORKSHEET_ID:
        add(
            blockers,
            "manifest_broad_beta_capture_candidate_worksheet_id_mismatch",
            "$.broad_beta_capture_candidate_worksheet_id",
            expected=BROAD_BETA_CAPTURE_WORKSHEET_ID,
            actual=manifest.get("broad_beta_capture_candidate_worksheet_id"),
        )
    if manifest.get("simultaneous_beta_capture_candidate_worksheet_included") is not True:
        add(
            blockers,
            "manifest_simultaneous_beta_capture_candidate_worksheet_not_included",
            "$.simultaneous_beta_capture_candidate_worksheet_included",
            value=manifest.get("simultaneous_beta_capture_candidate_worksheet_included"),
        )
    if (
        manifest.get("simultaneous_beta_capture_candidate_worksheet_template")
        != SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE
    ):
        add(
            blockers,
            "manifest_simultaneous_beta_capture_candidate_worksheet_template_mismatch",
            "$.simultaneous_beta_capture_candidate_worksheet_template",
            expected=SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE,
            actual=manifest.get("simultaneous_beta_capture_candidate_worksheet_template"),
        )
    if (
        manifest.get("simultaneous_beta_capture_candidate_worksheet_schema")
        != SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_SCHEMA
    ):
        add(
            blockers,
            "manifest_simultaneous_beta_capture_candidate_worksheet_schema_mismatch",
            "$.simultaneous_beta_capture_candidate_worksheet_schema",
            expected=SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_SCHEMA,
            actual=manifest.get("simultaneous_beta_capture_candidate_worksheet_schema"),
        )
    if (
        manifest.get("simultaneous_beta_capture_candidate_worksheet_id")
        != SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_ID
    ):
        add(
            blockers,
            "manifest_simultaneous_beta_capture_candidate_worksheet_id_mismatch",
            "$.simultaneous_beta_capture_candidate_worksheet_id",
            expected=SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_ID,
            actual=manifest.get("simultaneous_beta_capture_candidate_worksheet_id"),
        )
    if (
        manifest.get("simultaneous_beta_capture_candidate_worksheet_surfaces")
        != list(SIMULTANEOUS_BETA_CAPTURE_SURFACE_IDS)
    ):
        add(
            blockers,
            "manifest_simultaneous_beta_capture_candidate_worksheet_surfaces_mismatch",
            "$.simultaneous_beta_capture_candidate_worksheet_surfaces",
            expected=list(SIMULTANEOUS_BETA_CAPTURE_SURFACE_IDS),
            actual=manifest.get("simultaneous_beta_capture_candidate_worksheet_surfaces"),
        )
    if manifest.get("next_action_groups_included") is not True:
        add(
            blockers,
            "manifest_next_action_groups_not_included",
            "$.next_action_groups_included",
            value=manifest.get("next_action_groups_included"),
        )
    validate_candidate_only_metadata(manifest.get("candidate_only_metadata"), blockers, "$.candidate_only_metadata")
    validate_parallel_capture_boundary(
        manifest.get("parallel_capture_boundary"),
        blockers,
        "$.parallel_capture_boundary",
    )
    validate_player_principal_window_composition(
        manifest.get("player_principal_window_composition"),
        blockers,
        "$.player_principal_window_composition",
    )
    validate_lifecycle_correlation_metadata(
        manifest.get("lifecycle_correlation_metadata"),
        blockers,
        "$.lifecycle_correlation_metadata",
        expected_target=target,
        reason_prefix="manifest_lifecycle_correlation_metadata",
    )
    validate_text_privacy_boundary(manifest.get("text_privacy_boundary"), blockers, "$.text_privacy_boundary")
    validate_beta_capture_interaction_boundary(
        manifest.get("beta_capture_interaction_boundary"),
        blockers,
        "$.beta_capture_interaction_boundary",
    )
    validate_non_substitution_flags(manifest.get("non_substitution_flags"), blockers, "$.non_substitution_flags")
    if isinstance(manifest.get("target"), dict):
        expected_surfaces = expected_surface_entries_for_target(manifest["target"])
        expected_parallel_matrix = attach_source_metadata(
            parallel_beta_capture_side_lane_matrix(expected_surfaces, manifest["target"]),
            manifest["target"],
        )
        expected_single_player_sequence = attach_source_metadata(
            single_player_parallel_capture_sequence(expected_surfaces, manifest["target"]),
            manifest["target"],
        )
        expected_command_matrix = attach_source_metadata(
            target_bound_checker_command_matrix(expected_surfaces, manifest["target"]),
            manifest["target"],
        )
        expected_queue = attach_source_metadata(
            side_lane_capture_queue(expected_surfaces, manifest["target"]),
            manifest["target"],
        )
    else:
        expected_parallel_matrix = {}
        expected_single_player_sequence = {}
        expected_command_matrix = {}
        expected_queue = {}
    validate_parallel_beta_capture_side_lane_matrix(
        manifest.get("parallel_beta_capture_side_lane_matrix"),
        expected_parallel_matrix,
        blockers,
        "$.parallel_beta_capture_side_lane_matrix",
        expected_target=target,
    )
    validate_single_player_parallel_capture_sequence(
        manifest.get("single_player_parallel_capture_sequence"),
        expected_single_player_sequence,
        blockers,
        "$.single_player_parallel_capture_sequence",
        expected_target=target,
    )
    if manifest.get("target_bound_checker_command_matrix_included") is not True:
        add(
            blockers,
            "manifest_target_bound_checker_command_matrix_not_included",
            "$.target_bound_checker_command_matrix_included",
            value=manifest.get("target_bound_checker_command_matrix_included"),
        )
    validate_target_bound_checker_command_matrix(
        manifest.get("target_bound_checker_command_matrix"),
        expected_command_matrix,
        blockers,
        "$.target_bound_checker_command_matrix",
        expected_target=target,
    )
    if manifest.get("side_lane_capture_queue_included") is not True:
        add(
            blockers,
            "manifest_side_lane_capture_queue_not_included",
            "$.side_lane_capture_queue_included",
            value=manifest.get("side_lane_capture_queue_included"),
        )
    validate_side_lane_capture_queue(
        manifest.get("side_lane_capture_queue"),
        expected_queue,
        blockers,
        "$.side_lane_capture_queue",
        expected_target=target,
    )
    if manifest.get("manifest_sha256_kind") != "sha256_of_manifest_without_manifest_sha256_field":
        add(blockers, "manifest_sha256_kind_mismatch", "$.manifest_sha256_kind", value=manifest.get("manifest_sha256_kind"))
    artifact_names = check_no_duplicate_strings(
        manifest.get("artifact_names"),
        blockers,
        "$.artifact_names",
        "manifest_artifact_names_duplicate",
    )
    if artifact_names != EXPECTED_FILES:
        add(blockers, "manifest_artifact_names_mismatch", "$.artifact_names", expected=sorted(EXPECTED_FILES), actual=sorted(artifact_names))
    if "output_dir" in manifest:
        add(blockers, "manifest_output_dir_not_allowed", "$.output_dir", actual=manifest.get("output_dir"))
    check_non_claim_flags(manifest.get("non_claim_flags"), blockers, "$.non_claim_flags")

    primary = manifest.get("primary_evidence_required")
    if not isinstance(primary, dict):
        add(blockers, "manifest_primary_evidence_required_missing", "$.primary_evidence_required")
    else:
        if primary.get("surface") != "player_principal_lifecycle":
            add(blockers, "manifest_primary_surface_mismatch", "$.primary_evidence_required.surface")
        if primary.get("strict_triplet") != STRICT_PLAYER_PRINCIPAL_TRIPLET:
            add(blockers, "manifest_primary_triplet_mismatch", "$.primary_evidence_required.strict_triplet")
        if primary.get("must_be_checker_accepted") is not True:
            add(blockers, "manifest_primary_checker_acceptance_not_required", "$.primary_evidence_required.must_be_checker_accepted")

    manifest_without_sha = dict(manifest)
    recorded_sha = manifest_without_sha.pop("manifest_sha256", None)
    if not isinstance(recorded_sha, str):
        add(blockers, "manifest_sha256_missing", "$.manifest_sha256")
    else:
        expected_sha = __import__("hashlib").sha256(json_bytes(manifest_without_sha)).hexdigest()
        if recorded_sha != expected_sha:
            add(blockers, "manifest_sha256_mismatch", "$.manifest_sha256", expected=expected_sha, actual=recorded_sha)


def validate_artifact_hashes(pack_root: Path, manifest: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        add(blockers, "manifest_artifacts_missing_or_invalid", "$.artifacts")
        return
    observed_names: set[str] = set()
    duplicate_names: set[str] = set()
    for index, artifact in enumerate(artifacts):
        label = f"$.artifacts[{index}]"
        if not isinstance(artifact, dict):
            add(blockers, "manifest_artifact_entry_invalid", label)
            continue
        name = artifact.get("name")
        if not isinstance(name, str) or name not in EXPECTED_ARTIFACTS:
            add(blockers, "manifest_artifact_name_unexpected", f"{label}.name", name=name)
            continue
        if name in observed_names:
            duplicate_names.add(name)
        observed_names.add(name)
        path = pack_root / name
        try:
            protected_paths.reject_symlink_component(path, f"artifact {name}")
        except SystemExit as exc:
            add(blockers, "manifest_artifact_path_rejected", f"{label}.path", file=str(path), detail=str(exc))
            continue
        if not path.exists():
            add(blockers, "artifact_file_missing", f"{label}.path", file=str(path))
            continue
        if not path.is_file():
            add(blockers, "artifact_file_not_regular", f"{label}.path", file=str(path))
            continue
        if artifact.get("path") != name:
            add(blockers, "manifest_artifact_path_mismatch", f"{label}.path", expected=name, actual=artifact.get("path"))
        actual_sha = sha256_file(path)
        if artifact.get("sha256") != actual_sha:
            add(blockers, "manifest_artifact_sha256_mismatch", f"{label}.sha256", expected=actual_sha, actual=artifact.get("sha256"))
        if artifact.get("size_bytes") != path.stat().st_size:
            add(blockers, "manifest_artifact_size_mismatch", f"{label}.size_bytes", expected=path.stat().st_size, actual=artifact.get("size_bytes"))
    missing = EXPECTED_ARTIFACTS - observed_names
    if missing:
        add(blockers, "manifest_artifacts_missing_expected_entries", "$.artifacts", missing=sorted(missing))
    if duplicate_names:
        add(blockers, "manifest_artifacts_duplicate_entries", "$.artifacts", duplicates=sorted(duplicate_names))
    unexpected_entries = {path.name for path in pack_root.iterdir()} - EXPECTED_FILES
    if unexpected_entries:
        add(blockers, "pack_root_unexpected_entries", "$pack_root", unexpected=sorted(unexpected_entries))
    non_file_entries = sorted(path.name for path in pack_root.iterdir() if path.name in EXPECTED_FILES and not path.is_file())
    if non_file_entries:
        add(blockers, "pack_root_expected_entries_not_files", "$pack_root", entries=non_file_entries)


def validate_plan(plan: dict[str, Any], manifest: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if plan.get("schema") != PLAN_SCHEMA:
        add(blockers, "plan_schema_mismatch", "$plan.schema", expected=PLAN_SCHEMA, actual=plan.get("schema"))
    if plan.get("status") != "candidate_capture_plan":
        add(blockers, "plan_status_mismatch", "$plan.status", actual=plan.get("status"))
    plan_target = validate_target(plan.get("target"), blockers, "$plan.target", expected_target=manifest.get("target"), reason_prefix="plan_target")
    validate_target_binding(
        plan.get("target_binding"),
        blockers,
        "$plan.target_binding",
        expected_target=plan_target,
        reason_prefix="plan_target_binding",
    )
    validate_target_binding_id(
        plan.get("target_binding_id"),
        blockers,
        "$plan.target_binding_id",
        expected_target=plan_target,
        reason_prefix="plan_target_binding_id",
    )
    validate_approved_runtime_window_binding(
        plan.get("approved_runtime_window_binding"),
        blockers,
        "$plan.approved_runtime_window_binding",
        expected_target=plan_target,
        reason_prefix="plan_approved_runtime_window_binding",
    )
    if plan.get("target") != manifest.get("target"):
        add(blockers, "plan_target_mismatch", "$plan.target", expected=manifest.get("target"), actual=plan.get("target"))
    if plan.get("required_primary_evidence") != manifest.get("primary_evidence_required"):
        add(blockers, "plan_primary_evidence_mismatch", "$plan.required_primary_evidence")
    if plan.get("current_route_blocker") != CURRENT_ROUTE_BLOCKER:
        add(blockers, "plan_current_route_blocker_mismatch", "$plan.current_route_blocker", value=plan.get("current_route_blocker"))
    if plan.get("next_required_artifact") != NEXT_REQUIRED_ARTIFACT:
        add(blockers, "plan_next_required_artifact_mismatch", "$plan.next_required_artifact", value=plan.get("next_required_artifact"))
    if plan.get("single_beta_session_intent") is not True:
        add(blockers, "plan_single_beta_session_intent_not_true", "$plan.single_beta_session_intent", value=plan.get("single_beta_session_intent"))
    validate_artifact_intake_constraints(plan.get("artifact_intake_constraints"), blockers, "$plan.artifact_intake_constraints")
    validate_candidate_only_metadata(plan.get("candidate_only_metadata"), blockers, "$plan.candidate_only_metadata")
    validate_parallel_capture_boundary(
        plan.get("parallel_capture_boundary"),
        blockers,
        "$plan.parallel_capture_boundary",
    )
    validate_player_principal_window_composition(
        plan.get("player_principal_window_composition"),
        blockers,
        "$plan.player_principal_window_composition",
    )
    validate_lifecycle_correlation_metadata(
        plan.get("lifecycle_correlation_metadata"),
        blockers,
        "$plan.lifecycle_correlation_metadata",
        expected_target=plan_target,
        reason_prefix="plan_lifecycle_correlation_metadata",
    )
    validate_text_privacy_boundary(plan.get("text_privacy_boundary"), blockers, "$plan.text_privacy_boundary")
    validate_beta_capture_interaction_boundary(
        plan.get("beta_capture_interaction_boundary"),
        blockers,
        "$plan.beta_capture_interaction_boundary",
    )
    validate_non_substitution_flags(plan.get("non_substitution_flags"), blockers, "$plan.non_substitution_flags")
    check_non_claim_flags(plan.get("non_claim_flags"), blockers, "$plan.non_claim_flags")
    server_policy = plan.get("server_policy")
    if not isinstance(server_policy, dict) or server_policy.get("max_ark_servers_running") != 2:
        add(blockers, "plan_server_policy_two_server_limit_missing", "$plan.server_policy")
    surfaces = validate_surface_collection(
        plan.get("capture_surfaces"),
        blockers,
        "$plan.capture_surfaces",
        reason_prefix="plan_capture_surfaces",
        require_priority=True,
    )
    if not surfaces:
        return
    try:
        expected_groups = beta_tester_next_action_groups(surfaces)
        if isinstance(plan_target, dict):
            expected_groups = attach_source_metadata(expected_groups, plan_target)
    except (KeyError, TypeError, SystemExit) as exc:
        add(blockers, "plan_next_action_groups_expected_build_failed", "$plan.next_action_groups", error=str(exc))
        expected_groups = []
    if expected_groups:
        validate_next_action_groups(plan.get("next_action_groups"), expected_groups, blockers, "$plan.next_action_groups")
    try:
        expected_broad_path = broad_beta_capture_pack_path(surfaces, plan_target or {})
        if isinstance(plan_target, dict):
            expected_broad_path = attach_source_metadata(expected_broad_path, plan_target)
    except (KeyError, TypeError, SystemExit) as exc:
        add(blockers, "plan_broad_beta_capture_pack_path_expected_build_failed", "$plan.broad_beta_capture_pack_path", error=str(exc))
        expected_broad_path = {}
    validate_broad_beta_capture_pack_path(
        plan.get("broad_beta_capture_pack_path"),
        expected_broad_path,
        blockers,
        "$plan.broad_beta_capture_pack_path",
        expected_target=plan_target,
    )
    try:
        expected_parallel_matrix = parallel_beta_capture_side_lane_matrix(surfaces, plan_target or {})
        if isinstance(plan_target, dict):
            expected_parallel_matrix = attach_source_metadata(expected_parallel_matrix, plan_target)
    except (KeyError, TypeError, SystemExit) as exc:
        add(blockers, "plan_parallel_beta_capture_side_lane_matrix_expected_build_failed", "$plan.parallel_beta_capture_side_lane_matrix", error=str(exc))
        expected_parallel_matrix = {}
    validate_parallel_beta_capture_side_lane_matrix(
        plan.get("parallel_beta_capture_side_lane_matrix"),
        expected_parallel_matrix,
        blockers,
        "$plan.parallel_beta_capture_side_lane_matrix",
        expected_target=plan_target,
    )
    try:
        expected_single_player_sequence = single_player_parallel_capture_sequence(surfaces, plan_target or {})
        if isinstance(plan_target, dict):
            expected_single_player_sequence = attach_source_metadata(expected_single_player_sequence, plan_target)
    except (KeyError, TypeError, SystemExit) as exc:
        add(blockers, "plan_single_player_parallel_capture_sequence_expected_build_failed", "$plan.single_player_parallel_capture_sequence", error=str(exc))
        expected_single_player_sequence = {}
    validate_single_player_parallel_capture_sequence(
        plan.get("single_player_parallel_capture_sequence"),
        expected_single_player_sequence,
        blockers,
        "$plan.single_player_parallel_capture_sequence",
        expected_target=plan_target,
    )
    try:
        expected_command_matrix = target_bound_checker_command_matrix(surfaces, plan_target or {})
        if isinstance(plan_target, dict):
            expected_command_matrix = attach_source_metadata(expected_command_matrix, plan_target)
    except (KeyError, TypeError, SystemExit) as exc:
        add(blockers, "plan_target_bound_checker_command_matrix_expected_build_failed", "$plan.target_bound_checker_command_matrix", error=str(exc))
        expected_command_matrix = {}
    validate_target_bound_checker_command_matrix(
        plan.get("target_bound_checker_command_matrix"),
        expected_command_matrix,
        blockers,
        "$plan.target_bound_checker_command_matrix",
        expected_target=plan_target,
    )
    try:
        expected_queue = side_lane_capture_queue(surfaces, plan_target or {})
        if isinstance(plan_target, dict):
            expected_queue = attach_source_metadata(expected_queue, plan_target)
    except (KeyError, TypeError, SystemExit) as exc:
        add(blockers, "plan_side_lane_capture_queue_expected_build_failed", "$plan.side_lane_capture_queue", error=str(exc))
        expected_queue = {}
    validate_side_lane_capture_queue(
        plan.get("side_lane_capture_queue"),
        expected_queue,
        blockers,
        "$plan.side_lane_capture_queue",
        expected_target=plan_target,
    )
    for index, surface in enumerate(surfaces):
        validate_surface_guardrails(
            surface,
            blockers,
            f"$plan.capture_surfaces[{index}]",
            expected_target=plan_target,
            false_reason="plan_surface_false_flag_overclaim",
            true_reason="plan_surface_required_true_flag_missing",
        )
        validate_expected_surface_binding(surface, blockers, f"$plan.capture_surfaces[{index}]")
        validate_target_binding(
            surface.get("target_binding"),
            blockers,
            f"$plan.capture_surfaces[{index}].target_binding",
            expected_target=plan_target,
            reason_prefix="plan_surface_target_binding",
        )
        validate_target_binding_id(
            surface.get("target_binding_id"),
            blockers,
            f"$plan.capture_surfaces[{index}].target_binding_id",
            expected_target=plan_target,
            reason_prefix="plan_surface_target_binding_id",
        )
        validate_checker_command(surface, blockers, f"$plan.capture_surfaces[{index}]", "post_capture_checker_command")
        validate_capture_artifacts(surface, blockers, f"$plan.capture_surfaces[{index}]", expected_target=plan_target)
        validate_surface_command_resolution(
            surface,
            blockers,
            f"$plan.capture_surfaces[{index}]",
            expected_target=plan_target,
            command_key="post_capture_checker_command",
            reason_prefix="plan_surface",
        )
        if not isinstance(surface.get("post_capture_boundary"), str) or "never promotes" not in surface["post_capture_boundary"]:
            add(blockers, "plan_surface_post_capture_boundary_missing", f"$plan.capture_surfaces[{index}].post_capture_boundary")
        check_non_claim_flags(surface.get("non_claim_flags"), blockers, f"$plan.capture_surfaces[{index}].non_claim_flags")


def validate_matrix(matrix: dict[str, Any], plan: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if matrix.get("schema") != CHECKER_MATRIX_SCHEMA:
        add(blockers, "matrix_schema_mismatch", "$matrix.schema")
    if matrix.get("status") != "candidate_only":
        add(blockers, "matrix_status_mismatch", "$matrix.status")
    matrix_target = validate_target(matrix.get("target"), blockers, "$matrix.target", expected_target=plan.get("target"), reason_prefix="matrix_target")
    validate_target_binding(
        matrix.get("target_binding"),
        blockers,
        "$matrix.target_binding",
        expected_target=matrix_target,
        reason_prefix="matrix_target_binding",
    )
    validate_target_binding_id(
        matrix.get("target_binding_id"),
        blockers,
        "$matrix.target_binding_id",
        expected_target=matrix_target,
        reason_prefix="matrix_target_binding_id",
    )
    validate_approved_runtime_window_binding(
        matrix.get("approved_runtime_window_binding"),
        blockers,
        "$matrix.approved_runtime_window_binding",
        expected_target=matrix_target,
        reason_prefix="matrix_approved_runtime_window_binding",
    )
    if matrix.get("target") != plan.get("target"):
        add(blockers, "matrix_target_mismatch", "$matrix.target", expected=plan.get("target"), actual=matrix.get("target"))
    if matrix.get("current_route_blocker") != CURRENT_ROUTE_BLOCKER:
        add(blockers, "matrix_current_route_blocker_mismatch", "$matrix.current_route_blocker", value=matrix.get("current_route_blocker"))
    if matrix.get("next_required_artifact") != NEXT_REQUIRED_ARTIFACT:
        add(blockers, "matrix_next_required_artifact_mismatch", "$matrix.next_required_artifact", value=matrix.get("next_required_artifact"))
    if matrix.get("primary_checker") != plan.get("required_primary_evidence"):
        add(blockers, "matrix_primary_checker_mismatch", "$matrix.primary_checker")
    validate_candidate_only_metadata(matrix.get("candidate_only_metadata"), blockers, "$matrix.candidate_only_metadata")
    validate_parallel_capture_boundary(
        matrix.get("parallel_capture_boundary"),
        blockers,
        "$matrix.parallel_capture_boundary",
    )
    validate_player_principal_window_composition(
        matrix.get("player_principal_window_composition"),
        blockers,
        "$matrix.player_principal_window_composition",
    )
    validate_lifecycle_correlation_metadata(
        matrix.get("lifecycle_correlation_metadata"),
        blockers,
        "$matrix.lifecycle_correlation_metadata",
        expected_target=matrix_target,
        reason_prefix="matrix_lifecycle_correlation_metadata",
    )
    validate_text_privacy_boundary(matrix.get("text_privacy_boundary"), blockers, "$matrix.text_privacy_boundary")
    validate_non_substitution_flags(matrix.get("non_substitution_flags"), blockers, "$matrix.non_substitution_flags")
    validate_next_action_groups(
        matrix.get("next_action_groups"),
        plan.get("next_action_groups"),
        blockers,
        "$matrix.next_action_groups",
    )
    validate_broad_beta_capture_pack_path(
        matrix.get("broad_beta_capture_pack_path"),
        plan.get("broad_beta_capture_pack_path"),
        blockers,
        "$matrix.broad_beta_capture_pack_path",
        expected_target=matrix_target,
    )
    validate_parallel_beta_capture_side_lane_matrix(
        matrix.get("parallel_beta_capture_side_lane_matrix"),
        plan.get("parallel_beta_capture_side_lane_matrix"),
        blockers,
        "$matrix.parallel_beta_capture_side_lane_matrix",
        expected_target=matrix_target,
    )
    validate_single_player_parallel_capture_sequence(
        matrix.get("single_player_parallel_capture_sequence"),
        plan.get("single_player_parallel_capture_sequence"),
        blockers,
        "$matrix.single_player_parallel_capture_sequence",
        expected_target=matrix_target,
    )
    validate_target_bound_checker_command_matrix(
        matrix.get("target_bound_checker_command_matrix"),
        plan.get("target_bound_checker_command_matrix"),
        blockers,
        "$matrix.target_bound_checker_command_matrix",
        expected_target=matrix_target,
    )
    validate_side_lane_capture_queue(
        matrix.get("side_lane_capture_queue"),
        plan.get("side_lane_capture_queue"),
        blockers,
        "$matrix.side_lane_capture_queue",
        expected_target=matrix_target,
    )
    surfaces = matrix.get("surfaces")
    plan_surfaces = plan.get("capture_surfaces") if isinstance(plan.get("capture_surfaces"), list) else []
    expected_by_id = {surface.get("id"): surface for surface in plan_surfaces if isinstance(surface, dict)}
    surfaces = validate_surface_collection(
        surfaces,
        blockers,
        "$matrix.surfaces",
        reason_prefix="matrix_surfaces",
        require_priority=True,
    )
    if not surfaces:
        return
    if set(expected_by_id) != EXPECTED_SURFACES:
        add(blockers, "matrix_plan_surface_set_mismatch", "$matrix.surfaces", expected=sorted(EXPECTED_SURFACES), actual=sorted(expected_by_id))
    for index, surface in enumerate(surfaces):
        expected = expected_by_id.get(surface.get("id"))
        if not isinstance(expected, dict):
            continue
        for key in (
            "checker",
            "objective",
            "operator_action",
            "tester_action",
            "priority",
            "approved_runtime_window_binding",
            "operator_tester_action_metadata",
            "checker_command_bindings",
            "resolved_checker_command_template",
            "resolved_checker_command_status",
            "target_bound_checker_command",
        ):
            if surface.get(key) != expected.get(key):
                add(blockers, "matrix_surface_plan_mismatch", f"$matrix.surfaces[{index}].{key}", expected=expected.get(key), actual=surface.get(key))
        validate_expected_surface_binding(surface, blockers, f"$matrix.surfaces[{index}]")
        validate_target_binding(
            surface.get("target_binding"),
            blockers,
            f"$matrix.surfaces[{index}].target_binding",
            expected_target=matrix_target,
            reason_prefix="matrix_surface_target_binding",
        )
        validate_target_binding_id(
            surface.get("target_binding_id"),
            blockers,
            f"$matrix.surfaces[{index}].target_binding_id",
            expected_target=matrix_target,
            reason_prefix="matrix_surface_target_binding_id",
        )
        validate_surface_guardrails(
            surface,
            blockers,
            f"$matrix.surfaces[{index}]",
            expected_target=matrix_target,
            false_reason="matrix_surface_false_flag_overclaim",
            true_reason="matrix_surface_required_true_flag_missing",
        )
        validate_checker_command(surface, blockers, f"$matrix.surfaces[{index}]", "command")
        validate_capture_artifacts(surface, blockers, f"$matrix.surfaces[{index}]", expected_target=matrix_target)
        validate_surface_command_resolution(
            surface,
            blockers,
            f"$matrix.surfaces[{index}]",
            expected_target=matrix_target,
            command_key="command",
            reason_prefix="matrix_surface",
        )


def validate_non_claim_manifest(payload: dict[str, Any], manifest: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if payload.get("schema") != NON_CLAIM_MANIFEST_SCHEMA:
        add(blockers, "non_claim_manifest_schema_mismatch", "$non_claim.schema")
    if payload.get("status") != "non_authorizing_candidate_pack":
        add(blockers, "non_claim_manifest_status_mismatch", "$non_claim.status")
    if payload.get("non_authorization") != NON_AUTHORIZATION:
        add(blockers, "non_claim_manifest_non_authorization_mismatch", "$non_claim.non_authorization")
    non_claim_target = validate_target(payload.get("target"), blockers, "$non_claim.target", expected_target=manifest.get("target"), reason_prefix="non_claim_manifest_target")
    validate_target_binding(
        payload.get("target_binding"),
        blockers,
        "$non_claim.target_binding",
        expected_target=non_claim_target,
        reason_prefix="non_claim_manifest_target_binding",
    )
    validate_target_binding_id(
        payload.get("target_binding_id"),
        blockers,
        "$non_claim.target_binding_id",
        expected_target=non_claim_target,
        reason_prefix="non_claim_manifest_target_binding_id",
    )
    validate_approved_runtime_window_binding(
        payload.get("approved_runtime_window_binding"),
        blockers,
        "$non_claim.approved_runtime_window_binding",
        expected_target=non_claim_target,
        reason_prefix="non_claim_manifest_approved_runtime_window_binding",
    )
    if payload.get("target") != manifest.get("target"):
        add(blockers, "non_claim_manifest_target_mismatch", "$non_claim.target")
    if payload.get("required_primary_evidence") != manifest.get("primary_evidence_required"):
        add(blockers, "non_claim_manifest_primary_evidence_mismatch", "$non_claim.required_primary_evidence")
    validate_candidate_only_metadata(payload.get("candidate_only_metadata"), blockers, "$non_claim.candidate_only_metadata")
    validate_parallel_capture_boundary(
        payload.get("parallel_capture_boundary"),
        blockers,
        "$non_claim.parallel_capture_boundary",
    )
    validate_player_principal_window_composition(
        payload.get("player_principal_window_composition"),
        blockers,
        "$non_claim.player_principal_window_composition",
    )
    validate_lifecycle_correlation_metadata(
        payload.get("lifecycle_correlation_metadata"),
        blockers,
        "$non_claim.lifecycle_correlation_metadata",
        expected_target=non_claim_target,
        reason_prefix="non_claim_lifecycle_correlation_metadata",
    )
    validate_text_privacy_boundary(
        payload.get("text_privacy_boundary"),
        blockers,
        "$non_claim.text_privacy_boundary",
    )
    validate_non_substitution_flags(payload.get("non_substitution_flags"), blockers, "$non_claim.non_substitution_flags")
    expected_groups = payload.get("next_action_groups")
    if isinstance(expected_groups, list):
        validate_next_action_groups(
            expected_groups,
            expected_groups,
            blockers,
            "$non_claim.next_action_groups",
        )
    else:
        validate_next_action_groups(
            expected_groups,
            [],
            blockers,
            "$non_claim.next_action_groups",
        )
    validate_broad_beta_capture_pack_path(
        payload.get("broad_beta_capture_pack_path"),
        manifest.get("broad_beta_capture_pack_path"),
        blockers,
        "$non_claim.broad_beta_capture_pack_path",
        expected_target=non_claim_target,
    )
    validate_parallel_beta_capture_side_lane_matrix(
        payload.get("parallel_beta_capture_side_lane_matrix"),
        manifest.get("parallel_beta_capture_side_lane_matrix"),
        blockers,
        "$non_claim.parallel_beta_capture_side_lane_matrix",
        expected_target=non_claim_target,
    )
    validate_single_player_parallel_capture_sequence(
        payload.get("single_player_parallel_capture_sequence"),
        manifest.get("single_player_parallel_capture_sequence"),
        blockers,
        "$non_claim.single_player_parallel_capture_sequence",
        expected_target=non_claim_target,
    )
    validate_target_bound_checker_command_matrix(
        payload.get("target_bound_checker_command_matrix"),
        manifest.get("target_bound_checker_command_matrix"),
        blockers,
        "$non_claim.target_bound_checker_command_matrix",
        expected_target=non_claim_target,
    )
    validate_side_lane_capture_queue(
        payload.get("side_lane_capture_queue"),
        manifest.get("side_lane_capture_queue"),
        blockers,
        "$non_claim.side_lane_capture_queue",
        expected_target=non_claim_target,
    )
    if payload.get("current_route_blocker") != CURRENT_ROUTE_BLOCKER:
        add(blockers, "non_claim_manifest_current_route_blocker_mismatch", "$non_claim.current_route_blocker")
    if payload.get("next_required_artifact") != NEXT_REQUIRED_ARTIFACT:
        add(blockers, "non_claim_manifest_next_required_artifact_mismatch", "$non_claim.next_required_artifact")
    expected_artifact_count = sum(len(artifacts) for artifacts in EXPECTED_CAPTURE_ARTIFACTS_BY_SURFACE.values())
    if payload.get("candidate_artifact_count") != expected_artifact_count:
        add(
            blockers,
            "non_claim_manifest_candidate_artifact_count_mismatch",
            "$non_claim.candidate_artifact_count",
            expected=expected_artifact_count,
            actual=payload.get("candidate_artifact_count"),
        )
    if payload.get("side_lanes_non_counting_before_player_principal") is not True:
        add(
            blockers,
            "non_claim_manifest_side_lanes_non_counting_before_player_principal_not_true",
            "$non_claim.side_lanes_non_counting_before_player_principal",
            value=payload.get("side_lanes_non_counting_before_player_principal"),
        )
    check_non_claim_flags(payload.get("non_claim_flags"), blockers, "$non_claim.non_claim_flags")
    surface_claims = payload.get("surface_non_claims")
    surface_claims = validate_surface_collection(
        surface_claims,
        blockers,
        "$non_claim.surface_non_claims",
        reason_prefix="non_claim_manifest_surfaces",
        require_priority=False,
    )
    if not surface_claims:
        return
    for index, surface in enumerate(surface_claims):
        validate_target_binding(
            surface.get("target_binding"),
            blockers,
            f"$non_claim.surface_non_claims[{index}].target_binding",
            expected_target=non_claim_target,
            reason_prefix="non_claim_manifest_surface_target_binding",
        )
        validate_target_binding_id(
            surface.get("target_binding_id"),
            blockers,
            f"$non_claim.surface_non_claims[{index}].target_binding_id",
            expected_target=non_claim_target,
            reason_prefix="non_claim_manifest_surface_target_binding_id",
        )
        validate_surface_guardrails(
            surface,
            blockers,
            f"$non_claim.surface_non_claims[{index}]",
            expected_target=non_claim_target,
            false_reason="non_claim_manifest_surface_false_flag_overclaim",
            true_reason="non_claim_manifest_surface_required_true_flag_missing",
        )
        for key in ("plugin_hub_ready", "publication_ready"):
            if surface.get(key) is not False:
                add(
                    blockers,
                    "non_claim_manifest_surface_false_flag_overclaim",
                    f"$non_claim.surface_non_claims[{index}].{key}",
                    value=surface.get(key),
                )


def validate_intake(payload: dict[str, Any], plan: dict[str, Any], manifest: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if payload.get("schema") != INTAKE_SCHEMA:
        add(blockers, "intake_schema_mismatch", "$intake.schema", expected=INTAKE_SCHEMA, actual=payload.get("schema"))
    if payload.get("status") != "candidate_artifact_intake_template":
        add(blockers, "intake_status_mismatch", "$intake.status", actual=payload.get("status"))
    intake_target = validate_target(payload.get("target"), blockers, "$intake.target", expected_target=manifest.get("target"), reason_prefix="intake_target")
    validate_target_binding(
        payload.get("target_binding"),
        blockers,
        "$intake.target_binding",
        expected_target=intake_target,
        reason_prefix="intake_target_binding",
    )
    validate_target_binding_id(
        payload.get("target_binding_id"),
        blockers,
        "$intake.target_binding_id",
        expected_target=intake_target,
        reason_prefix="intake_target_binding_id",
    )
    validate_approved_runtime_window_binding(
        payload.get("approved_runtime_window_binding"),
        blockers,
        "$intake.approved_runtime_window_binding",
        expected_target=intake_target,
        reason_prefix="intake_approved_runtime_window_binding",
    )
    if payload.get("target") != manifest.get("target"):
        add(blockers, "intake_target_mismatch", "$intake.target", expected=manifest.get("target"), actual=payload.get("target"))
    if payload.get("current_route_blocker") != CURRENT_ROUTE_BLOCKER:
        add(blockers, "intake_current_route_blocker_mismatch", "$intake.current_route_blocker", value=payload.get("current_route_blocker"))
    if payload.get("next_required_artifact") != NEXT_REQUIRED_ARTIFACT:
        add(blockers, "intake_next_required_artifact_mismatch", "$intake.next_required_artifact", value=payload.get("next_required_artifact"))
    if payload.get("required_primary_evidence") != manifest.get("primary_evidence_required"):
        add(blockers, "intake_primary_evidence_mismatch", "$intake.required_primary_evidence")
    validate_candidate_only_metadata(payload.get("candidate_only_metadata"), blockers, "$intake.candidate_only_metadata")
    validate_parallel_capture_boundary(
        payload.get("parallel_capture_boundary"),
        blockers,
        "$intake.parallel_capture_boundary",
    )
    validate_player_principal_window_composition(
        payload.get("player_principal_window_composition"),
        blockers,
        "$intake.player_principal_window_composition",
    )
    validate_lifecycle_correlation_metadata(
        payload.get("lifecycle_correlation_metadata"),
        blockers,
        "$intake.lifecycle_correlation_metadata",
        expected_target=intake_target,
        reason_prefix="intake_lifecycle_correlation_metadata",
    )
    validate_text_privacy_boundary(payload.get("text_privacy_boundary"), blockers, "$intake.text_privacy_boundary")
    validate_non_substitution_flags(payload.get("non_substitution_flags"), blockers, "$intake.non_substitution_flags")
    validate_next_action_groups(
        payload.get("next_action_groups"),
        plan.get("next_action_groups"),
        blockers,
        "$intake.next_action_groups",
    )
    validate_broad_beta_capture_pack_path(
        payload.get("broad_beta_capture_pack_path"),
        plan.get("broad_beta_capture_pack_path"),
        blockers,
        "$intake.broad_beta_capture_pack_path",
        expected_target=intake_target,
    )
    validate_parallel_beta_capture_side_lane_matrix(
        payload.get("parallel_beta_capture_side_lane_matrix"),
        plan.get("parallel_beta_capture_side_lane_matrix"),
        blockers,
        "$intake.parallel_beta_capture_side_lane_matrix",
        expected_target=intake_target,
    )
    validate_single_player_parallel_capture_sequence(
        payload.get("single_player_parallel_capture_sequence"),
        plan.get("single_player_parallel_capture_sequence"),
        blockers,
        "$intake.single_player_parallel_capture_sequence",
        expected_target=intake_target,
    )
    validate_target_bound_checker_command_matrix(
        payload.get("target_bound_checker_command_matrix"),
        plan.get("target_bound_checker_command_matrix"),
        blockers,
        "$intake.target_bound_checker_command_matrix",
        expected_target=intake_target,
    )
    validate_side_lane_capture_queue(
        payload.get("side_lane_capture_queue"),
        plan.get("side_lane_capture_queue"),
        blockers,
        "$intake.side_lane_capture_queue",
        expected_target=intake_target,
    )
    expected_artifact_count = sum(len(artifacts) for artifacts in EXPECTED_CAPTURE_ARTIFACTS_BY_SURFACE.values())
    if payload.get("candidate_artifact_count") != expected_artifact_count:
        add(
            blockers,
            "intake_candidate_artifact_count_mismatch",
            "$intake.candidate_artifact_count",
            expected=expected_artifact_count,
            actual=payload.get("candidate_artifact_count"),
        )
    constraints = payload.get("capture_session_constraints")
    if not isinstance(constraints, dict):
        add(blockers, "intake_constraints_missing_or_invalid", "$intake.capture_session_constraints", value=constraints)
    else:
        expected_constraint_keys = EXPECTED_INTAKE_CONSTRAINTS | EXPECTED_FALSE_INTAKE_CONSTRAINTS
        extra_keys = sorted(set(constraints) - expected_constraint_keys)
        missing_keys = sorted(expected_constraint_keys - set(constraints))
        if extra_keys:
            add(blockers, "intake_constraints_unexpected_keys", "$intake.capture_session_constraints", keys=extra_keys)
        if missing_keys:
            add(blockers, "intake_constraints_missing_keys", "$intake.capture_session_constraints", keys=missing_keys)
        for key in sorted(EXPECTED_INTAKE_CONSTRAINTS):
            if constraints.get(key) is not True:
                add(blockers, "intake_constraint_not_true", f"$intake.capture_session_constraints.{key}", value=constraints.get(key))
        for key in sorted(EXPECTED_FALSE_INTAKE_CONSTRAINTS):
            if constraints.get(key) is not False:
                add(
                    blockers,
                    "intake_constraint_not_false",
                    f"$intake.capture_session_constraints.{key}",
                    value=constraints.get(key),
                )
    validate_artifact_intake_constraints(payload.get("artifact_intake_constraints"), blockers, "$intake.artifact_intake_constraints")
    check_non_claim_flags(payload.get("non_claim_flags"), blockers, "$intake.non_claim_flags")

    plan_surfaces = plan.get("capture_surfaces") if isinstance(plan.get("capture_surfaces"), list) else []
    expected_by_id = {surface.get("id"): surface for surface in plan_surfaces if isinstance(surface, dict)}
    if set(expected_by_id) != EXPECTED_SURFACES:
        add(blockers, "intake_plan_surface_set_mismatch", "$intake.surfaces", expected=sorted(EXPECTED_SURFACES), actual=sorted(expected_by_id))
    surfaces = validate_surface_collection(
        payload.get("surfaces"),
        blockers,
        "$intake.surfaces",
        reason_prefix="intake_surfaces",
        require_priority=True,
    )
    if not surfaces:
        return
    for index, surface in enumerate(surfaces):
        expected = expected_by_id.get(surface.get("id"))
        if isinstance(expected, dict):
            for key in (
                "checker",
                "command",
                "objective",
                "operator_action",
                "tester_action",
                "priority",
                "candidate_artifact_count",
                "approved_runtime_window_binding",
                "operator_tester_action_metadata",
                "checker_command_bindings",
                "resolved_checker_command_template",
                "resolved_checker_command_status",
                "target_bound_checker_command",
            ):
                if surface.get(key) != expected.get("post_capture_checker_command" if key == "command" else key):
                    add(
                        blockers,
                        "intake_surface_plan_mismatch",
                        f"$intake.surfaces[{index}].{key}",
                        expected=expected.get("post_capture_checker_command" if key == "command" else key),
                        actual=surface.get(key),
                    )
        validate_expected_surface_binding(surface, blockers, f"$intake.surfaces[{index}]")
        validate_target_binding(
            surface.get("target_binding"),
            blockers,
            f"$intake.surfaces[{index}].target_binding",
            expected_target=intake_target,
            reason_prefix="intake_surface_target_binding",
        )
        validate_target_binding_id(
            surface.get("target_binding_id"),
            blockers,
            f"$intake.surfaces[{index}].target_binding_id",
            expected_target=intake_target,
            reason_prefix="intake_surface_target_binding_id",
        )
        validate_surface_guardrails(
            surface,
            blockers,
            f"$intake.surfaces[{index}]",
            expected_target=intake_target,
            false_reason="intake_surface_false_flag_overclaim",
            true_reason="intake_surface_required_true_flag_missing",
        )
        validate_checker_command(surface, blockers, f"$intake.surfaces[{index}]", "command")
        validate_capture_artifacts(surface, blockers, f"$intake.surfaces[{index}]", expected_target=intake_target)
        validate_surface_command_resolution(
            surface,
            blockers,
            f"$intake.surfaces[{index}]",
            expected_target=intake_target,
            command_key="command",
            reason_prefix="intake_surface",
        )


def validate_broad_beta_capture_candidate_worksheet(
    payload: dict[str, Any],
    plan: dict[str, Any],
    manifest: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    expected = broad_beta_capture_candidate_worksheet(plan)
    if payload != expected:
        add(
            blockers,
            "broad_beta_capture_candidate_worksheet_mismatch",
            "$worksheet",
            expected=expected,
            actual=payload,
        )
    if payload.get("schema") != BROAD_BETA_CAPTURE_WORKSHEET_SCHEMA:
        add(
            blockers,
            "broad_beta_capture_candidate_worksheet_schema_mismatch",
            "$worksheet.schema",
            expected=BROAD_BETA_CAPTURE_WORKSHEET_SCHEMA,
            actual=payload.get("schema"),
        )
    if payload.get("id") != BROAD_BETA_CAPTURE_WORKSHEET_ID:
        add(
            blockers,
            "broad_beta_capture_candidate_worksheet_id_mismatch",
            "$worksheet.id",
            expected=BROAD_BETA_CAPTURE_WORKSHEET_ID,
            actual=payload.get("id"),
        )
    if payload.get("file") != BROAD_BETA_CAPTURE_WORKSHEET_FILE:
        add(
            blockers,
            "broad_beta_capture_candidate_worksheet_file_mismatch",
            "$worksheet.file",
            expected=BROAD_BETA_CAPTURE_WORKSHEET_FILE,
            actual=payload.get("file"),
        )
    if payload.get("status") != "candidate_worksheet_template":
        add(blockers, "broad_beta_capture_candidate_worksheet_status_mismatch", "$worksheet.status", value=payload.get("status"))
    if payload.get("artifact_status") != "candidate_only":
        add(blockers, "broad_beta_capture_candidate_worksheet_artifact_status_mismatch", "$worksheet.artifact_status", value=payload.get("artifact_status"))
    worksheet_target = validate_target(
        payload.get("target"),
        blockers,
        "$worksheet.target",
        expected_target=manifest.get("target") if isinstance(manifest.get("target"), dict) else None,
        reason_prefix="broad_beta_capture_candidate_worksheet_target",
    )
    validate_target_binding(
        payload.get("target_binding"),
        blockers,
        "$worksheet.target_binding",
        expected_target=worksheet_target,
        reason_prefix="broad_beta_capture_candidate_worksheet_target_binding",
    )
    validate_target_binding_id(
        payload.get("target_binding_id"),
        blockers,
        "$worksheet.target_binding_id",
        expected_target=worksheet_target,
        reason_prefix="broad_beta_capture_candidate_worksheet_target_binding_id",
    )
    validate_approved_runtime_window_binding(
        payload.get("approved_runtime_window_binding"),
        blockers,
        "$worksheet.approved_runtime_window_binding",
        expected_target=worksheet_target,
        reason_prefix="broad_beta_capture_candidate_worksheet_approved_runtime_window_binding",
    )
    if payload.get("current_route_blocker") != CURRENT_ROUTE_BLOCKER:
        add(blockers, "broad_beta_capture_candidate_worksheet_route_blocker_mismatch", "$worksheet.current_route_blocker", value=payload.get("current_route_blocker"))
    if payload.get("next_required_artifact") != NEXT_REQUIRED_ARTIFACT:
        add(blockers, "broad_beta_capture_candidate_worksheet_next_required_artifact_mismatch", "$worksheet.next_required_artifact", value=payload.get("next_required_artifact"))
    if payload.get("broad_beta_capture_pack_path_id") != BROAD_BETA_CAPTURE_PACK_PATH_ID:
        add(blockers, "broad_beta_capture_candidate_worksheet_path_id_mismatch", "$worksheet.broad_beta_capture_pack_path_id", value=payload.get("broad_beta_capture_pack_path_id"))
    if payload.get("surface_ids") != list(BROAD_BETA_CAPTURE_SURFACE_IDS):
        add(
            blockers,
            "broad_beta_capture_candidate_worksheet_surface_ids_mismatch",
            "$worksheet.surface_ids",
            expected=list(BROAD_BETA_CAPTURE_SURFACE_IDS),
            actual=payload.get("surface_ids"),
        )
    if payload.get("action_group_ids") != list(BROAD_BETA_CAPTURE_ACTION_GROUP_IDS):
        add(
            blockers,
            "broad_beta_capture_candidate_worksheet_action_group_ids_mismatch",
            "$worksheet.action_group_ids",
            expected=list(BROAD_BETA_CAPTURE_ACTION_GROUP_IDS),
            actual=payload.get("action_group_ids"),
        )
    rows = payload.get("worksheet_rows")
    if not isinstance(rows, list):
        add(blockers, "broad_beta_capture_candidate_worksheet_rows_missing_or_invalid", "$worksheet.worksheet_rows", value=rows)
    else:
        observed = [row.get("surface_id") for row in rows if isinstance(row, dict)]
        if observed != list(BROAD_BETA_CAPTURE_SURFACE_IDS):
            add(
                blockers,
                "broad_beta_capture_candidate_worksheet_row_order_mismatch",
                "$worksheet.worksheet_rows",
                expected=list(BROAD_BETA_CAPTURE_SURFACE_IDS),
                actual=observed,
            )
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                add(blockers, "broad_beta_capture_candidate_worksheet_row_invalid", f"$worksheet.worksheet_rows[{index}]", value=row)
                continue
            if row.get("observation_rows") != []:
                add(
                    blockers,
                    "broad_beta_capture_candidate_worksheet_observation_rows_not_blank",
                    f"$worksheet.worksheet_rows[{index}].observation_rows",
                    value=row.get("observation_rows"),
                )
            fields = row.get("worksheet_fields")
            if not isinstance(fields, list) or not fields:
                add(
                    blockers,
                    "broad_beta_capture_candidate_worksheet_fields_missing_or_invalid",
                    f"$worksheet.worksheet_rows[{index}].worksheet_fields",
                    value=fields,
                )
            else:
                field_ids = [
                    field.get("field_id")
                    for field in fields
                    if isinstance(field, dict)
                ]
                missing_fields = sorted(set(LIFECYCLE_CORRELATION_FIELD_IDS) - set(field_ids))
                if missing_fields:
                    add(
                        blockers,
                        "broad_beta_capture_candidate_worksheet_correlation_fields_missing",
                        f"$worksheet.worksheet_rows[{index}].worksheet_fields",
                        fields=missing_fields,
                    )
            validate_lifecycle_correlation_metadata(
                row.get("lifecycle_correlation_metadata"),
                blockers,
                f"$worksheet.worksheet_rows[{index}].lifecycle_correlation_metadata",
                expected_target=worksheet_target,
                reason_prefix="broad_beta_capture_candidate_worksheet_row_lifecycle_correlation_metadata",
            )
            validate_lifecycle_correlation_field_ids(
                row.get("correlation_field_ids"),
                blockers,
                f"$worksheet.worksheet_rows[{index}].correlation_field_ids",
                reason_prefix="broad_beta_capture_candidate_worksheet_row_correlation",
            )
            for key in (
                "candidate_only",
                "non_evidence",
                "requires_checker_acceptance",
                "requires_player_principal_triplet",
                "blocked_by_player_principal_evidence",
                "same_approved_runtime_window_required",
                "exact_target_binding_required",
                "correlation_metadata_required",
                "correlation_metadata_blank_by_default",
                "correlation_metadata_non_evidence",
            ):
                if row.get(key) is not True:
                    add(
                        blockers,
                        "broad_beta_capture_candidate_worksheet_row_true_flag_missing",
                        f"$worksheet.worksheet_rows[{index}].{key}",
                        value=row.get(key),
                    )
            for key in (
                "counts_as_approved_runtime_evidence",
                "counts_as_runtime_evidence",
                "counts_as_sdk_progress",
                "counts_as_p0_progress",
                "clears_approved_runtime_evidence_missing",
                "runtime_ready",
                "public_sdk_ready",
                "stable_sdk_ready",
            ):
                if row.get(key) is not False:
                    add(
                        blockers,
                        "broad_beta_capture_candidate_worksheet_row_false_flag_overclaim",
                        f"$worksheet.worksheet_rows[{index}].{key}",
                        value=row.get(key),
                    )
    validate_candidate_only_metadata(payload.get("candidate_only_metadata"), blockers, "$worksheet.candidate_only_metadata")
    validate_parallel_capture_boundary(payload.get("parallel_capture_boundary"), blockers, "$worksheet.parallel_capture_boundary")
    validate_player_principal_window_composition(
        payload.get("player_principal_window_composition"),
        blockers,
        "$worksheet.player_principal_window_composition",
    )
    validate_lifecycle_correlation_metadata(
        payload.get("lifecycle_correlation_metadata"),
        blockers,
        "$worksheet.lifecycle_correlation_metadata",
        expected_target=worksheet_target,
        reason_prefix="broad_beta_capture_candidate_worksheet_lifecycle_correlation_metadata",
    )
    validate_text_privacy_boundary(payload.get("text_privacy_boundary"), blockers, "$worksheet.text_privacy_boundary")
    validate_non_substitution_flags(payload.get("non_substitution_flags"), blockers, "$worksheet.non_substitution_flags")
    check_non_claim_flags(payload.get("non_claim_flags"), blockers, "$worksheet.non_claim_flags")
    for key in (
        "candidate_only",
        "non_evidence",
        "correlation_metadata_required",
        "correlation_metadata_non_evidence",
        "requires_checker_acceptance",
        "requires_player_principal_triplet",
        "blocked_by_player_principal_evidence",
    ):
        if payload.get(key) is not True:
            add(blockers, "broad_beta_capture_candidate_worksheet_true_flag_missing", f"$worksheet.{key}", value=payload.get(key))
    for key in (
        "raw_player_text_retention_allowed",
        "raw_player_text_capture_allowed",
        "raw_chat_payload_capture_allowed",
        "private_player_data_retention_allowed",
        "secrets_or_webhook_retention_allowed",
        "authorizes_live_log_reads",
        "authorizes_runtime_capture",
        "authorizes_discord_send",
        "authorizes_server_restart",
        "authorizes_marker_or_env_changes",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_progress",
        "counts_as_p0_progress",
        "clears_approved_runtime_evidence_missing",
        "runtime_ready",
        "public_sdk_ready",
        "stable_sdk_ready",
    ):
        if payload.get(key) is not False:
            add(blockers, "broad_beta_capture_candidate_worksheet_false_flag_overclaim", f"$worksheet.{key}", value=payload.get(key))


def validate_simultaneous_beta_capture_candidate_worksheet(
    payload: dict[str, Any],
    plan: dict[str, Any],
    manifest: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    expected = simultaneous_beta_capture_candidate_worksheet(plan)
    if payload != expected:
        add(
            blockers,
            "simultaneous_beta_capture_candidate_worksheet_mismatch",
            "$simultaneous_worksheet",
            expected=expected,
            actual=payload,
        )
    if payload.get("schema") != SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_SCHEMA:
        add(
            blockers,
            "simultaneous_beta_capture_candidate_worksheet_schema_mismatch",
            "$simultaneous_worksheet.schema",
            expected=SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_SCHEMA,
            actual=payload.get("schema"),
        )
    if payload.get("id") != SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_ID:
        add(
            blockers,
            "simultaneous_beta_capture_candidate_worksheet_id_mismatch",
            "$simultaneous_worksheet.id",
            expected=SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_ID,
            actual=payload.get("id"),
        )
    if payload.get("file") != SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE:
        add(
            blockers,
            "simultaneous_beta_capture_candidate_worksheet_file_mismatch",
            "$simultaneous_worksheet.file",
            expected=SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE,
            actual=payload.get("file"),
        )
    if payload.get("status") != "candidate_worksheet_template":
        add(
            blockers,
            "simultaneous_beta_capture_candidate_worksheet_status_mismatch",
            "$simultaneous_worksheet.status",
            value=payload.get("status"),
        )
    if payload.get("artifact_status") != "candidate_only":
        add(
            blockers,
            "simultaneous_beta_capture_candidate_worksheet_artifact_status_mismatch",
            "$simultaneous_worksheet.artifact_status",
            value=payload.get("artifact_status"),
        )
    worksheet_target = validate_target(
        payload.get("target"),
        blockers,
        "$simultaneous_worksheet.target",
        expected_target=manifest.get("target") if isinstance(manifest.get("target"), dict) else None,
        reason_prefix="simultaneous_beta_capture_candidate_worksheet_target",
    )
    validate_target_binding(
        payload.get("target_binding"),
        blockers,
        "$simultaneous_worksheet.target_binding",
        expected_target=worksheet_target,
        reason_prefix="simultaneous_beta_capture_candidate_worksheet_target_binding",
    )
    validate_target_binding_id(
        payload.get("target_binding_id"),
        blockers,
        "$simultaneous_worksheet.target_binding_id",
        expected_target=worksheet_target,
        reason_prefix="simultaneous_beta_capture_candidate_worksheet_target_binding_id",
    )
    validate_approved_runtime_window_binding(
        payload.get("approved_runtime_window_binding"),
        blockers,
        "$simultaneous_worksheet.approved_runtime_window_binding",
        expected_target=worksheet_target,
        reason_prefix="simultaneous_beta_capture_candidate_worksheet_approved_runtime_window_binding",
    )
    if payload.get("current_route_blocker") != CURRENT_ROUTE_BLOCKER:
        add(
            blockers,
            "simultaneous_beta_capture_candidate_worksheet_route_blocker_mismatch",
            "$simultaneous_worksheet.current_route_blocker",
            value=payload.get("current_route_blocker"),
        )
    if payload.get("next_required_artifact") != NEXT_REQUIRED_ARTIFACT:
        add(
            blockers,
            "simultaneous_beta_capture_candidate_worksheet_next_required_artifact_mismatch",
            "$simultaneous_worksheet.next_required_artifact",
            value=payload.get("next_required_artifact"),
        )
    if payload.get("parallel_beta_capture_matrix_id") != PARALLEL_BETA_CAPTURE_MATRIX_ID:
        add(
            blockers,
            "simultaneous_beta_capture_candidate_worksheet_matrix_id_mismatch",
            "$simultaneous_worksheet.parallel_beta_capture_matrix_id",
            value=payload.get("parallel_beta_capture_matrix_id"),
        )
    if payload.get("surface_ids") != list(SIMULTANEOUS_BETA_CAPTURE_SURFACE_IDS):
        add(
            blockers,
            "simultaneous_beta_capture_candidate_worksheet_surface_ids_mismatch",
            "$simultaneous_worksheet.surface_ids",
            expected=list(SIMULTANEOUS_BETA_CAPTURE_SURFACE_IDS),
            actual=payload.get("surface_ids"),
        )
    if payload.get("action_group_ids") != list(SIMULTANEOUS_BETA_CAPTURE_ACTION_GROUP_IDS):
        add(
            blockers,
            "simultaneous_beta_capture_candidate_worksheet_action_group_ids_mismatch",
            "$simultaneous_worksheet.action_group_ids",
            expected=list(SIMULTANEOUS_BETA_CAPTURE_ACTION_GROUP_IDS),
            actual=payload.get("action_group_ids"),
        )
    rows = payload.get("worksheet_rows")
    if not isinstance(rows, list):
        add(
            blockers,
            "simultaneous_beta_capture_candidate_worksheet_rows_missing_or_invalid",
            "$simultaneous_worksheet.worksheet_rows",
            value=rows,
        )
    else:
        observed = [row.get("surface_id") for row in rows if isinstance(row, dict)]
        if observed != list(SIMULTANEOUS_BETA_CAPTURE_SURFACE_IDS):
            add(
                blockers,
                "simultaneous_beta_capture_candidate_worksheet_row_order_mismatch",
                "$simultaneous_worksheet.worksheet_rows",
                expected=list(SIMULTANEOUS_BETA_CAPTURE_SURFACE_IDS),
                actual=observed,
            )
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                add(
                    blockers,
                    "simultaneous_beta_capture_candidate_worksheet_row_invalid",
                    f"$simultaneous_worksheet.worksheet_rows[{index}]",
                    value=row,
                )
                continue
            if row.get("observation_rows") != []:
                add(
                    blockers,
                    "simultaneous_beta_capture_candidate_worksheet_observation_rows_not_blank",
                    f"$simultaneous_worksheet.worksheet_rows[{index}].observation_rows",
                    value=row.get("observation_rows"),
                )
            fields = row.get("worksheet_fields")
            if not isinstance(fields, list) or not fields:
                add(
                    blockers,
                    "simultaneous_beta_capture_candidate_worksheet_fields_missing_or_invalid",
                    f"$simultaneous_worksheet.worksheet_rows[{index}].worksheet_fields",
                    value=fields,
                )
            else:
                field_ids = [
                    field.get("field_id")
                    for field in fields
                    if isinstance(field, dict)
                ]
                missing_fields = sorted(set(LIFECYCLE_CORRELATION_FIELD_IDS) - set(field_ids))
                if missing_fields:
                    add(
                        blockers,
                        "simultaneous_beta_capture_candidate_worksheet_correlation_fields_missing",
                        f"$simultaneous_worksheet.worksheet_rows[{index}].worksheet_fields",
                        fields=missing_fields,
                    )
                if row.get("surface_id") == "mission_copied_bool" and "mission_context_shape" not in field_ids:
                    add(
                        blockers,
                        "simultaneous_beta_capture_candidate_worksheet_mission_fields_missing",
                        f"$simultaneous_worksheet.worksheet_rows[{index}].worksheet_fields",
                        fields=field_ids,
                    )
            validate_lifecycle_correlation_metadata(
                row.get("lifecycle_correlation_metadata"),
                blockers,
                f"$simultaneous_worksheet.worksheet_rows[{index}].lifecycle_correlation_metadata",
                expected_target=worksheet_target,
                reason_prefix="simultaneous_beta_capture_candidate_worksheet_row_lifecycle_correlation_metadata",
            )
            validate_lifecycle_correlation_field_ids(
                row.get("correlation_field_ids"),
                blockers,
                f"$simultaneous_worksheet.worksheet_rows[{index}].correlation_field_ids",
                reason_prefix="simultaneous_beta_capture_candidate_worksheet_row_correlation",
            )
            for key in (
                "candidate_only",
                "non_evidence",
                "requires_checker_acceptance",
                "requires_player_principal_triplet",
                "blocked_by_player_principal_evidence",
                "same_approved_runtime_window_required",
                "exact_target_binding_required",
                "correlation_metadata_required",
                "correlation_metadata_blank_by_default",
                "correlation_metadata_non_evidence",
            ):
                if row.get(key) is not True:
                    add(
                        blockers,
                        "simultaneous_beta_capture_candidate_worksheet_row_true_flag_missing",
                        f"$simultaneous_worksheet.worksheet_rows[{index}].{key}",
                        value=row.get(key),
                    )
            for key in (
                "counts_as_approved_runtime_evidence",
                "counts_as_runtime_evidence",
                "counts_as_sdk_progress",
                "counts_as_p0_progress",
                "clears_approved_runtime_evidence_missing",
                "runtime_ready",
                "public_sdk_ready",
                "stable_sdk_ready",
            ):
                if row.get(key) is not False:
                    add(
                        blockers,
                        "simultaneous_beta_capture_candidate_worksheet_row_false_flag_overclaim",
                        f"$simultaneous_worksheet.worksheet_rows[{index}].{key}",
                        value=row.get(key),
                    )
    validate_candidate_only_metadata(
        payload.get("candidate_only_metadata"),
        blockers,
        "$simultaneous_worksheet.candidate_only_metadata",
    )
    validate_parallel_capture_boundary(
        payload.get("parallel_capture_boundary"),
        blockers,
        "$simultaneous_worksheet.parallel_capture_boundary",
    )
    validate_player_principal_window_composition(
        payload.get("player_principal_window_composition"),
        blockers,
        "$simultaneous_worksheet.player_principal_window_composition",
    )
    validate_lifecycle_correlation_metadata(
        payload.get("lifecycle_correlation_metadata"),
        blockers,
        "$simultaneous_worksheet.lifecycle_correlation_metadata",
        expected_target=worksheet_target,
        reason_prefix="simultaneous_beta_capture_candidate_worksheet_lifecycle_correlation_metadata",
    )
    validate_text_privacy_boundary(
        payload.get("text_privacy_boundary"),
        blockers,
        "$simultaneous_worksheet.text_privacy_boundary",
    )
    validate_non_substitution_flags(
        payload.get("non_substitution_flags"),
        blockers,
        "$simultaneous_worksheet.non_substitution_flags",
    )
    check_non_claim_flags(
        payload.get("non_claim_flags"),
        blockers,
        "$simultaneous_worksheet.non_claim_flags",
    )
    for key in (
        "candidate_only",
        "non_evidence",
        "simultaneous_side_lane_rows",
        "correlation_metadata_required",
        "correlation_metadata_non_evidence",
        "requires_checker_acceptance",
        "requires_player_principal_triplet",
        "blocked_by_player_principal_evidence",
    ):
        if payload.get(key) is not True:
            add(
                blockers,
                "simultaneous_beta_capture_candidate_worksheet_true_flag_missing",
                f"$simultaneous_worksheet.{key}",
                value=payload.get(key),
            )
    for key in (
        "raw_player_text_retention_allowed",
        "raw_player_text_capture_allowed",
        "raw_chat_payload_capture_allowed",
        "private_player_data_retention_allowed",
        "secrets_or_webhook_retention_allowed",
        "authorizes_live_log_reads",
        "authorizes_runtime_capture",
        "authorizes_discord_send",
        "authorizes_server_restart",
        "authorizes_marker_or_env_changes",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_progress",
        "counts_as_p0_progress",
        "clears_approved_runtime_evidence_missing",
        "runtime_ready",
        "public_sdk_ready",
        "stable_sdk_ready",
    ):
        if payload.get(key) is not False:
            add(
                blockers,
                "simultaneous_beta_capture_candidate_worksheet_false_flag_overclaim",
                f"$simultaneous_worksheet.{key}",
                value=payload.get(key),
            )


def validate_single_player_parallel_capture_candidate_worksheet(
    payload: dict[str, Any],
    plan: dict[str, Any],
    manifest: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    expected = single_player_parallel_capture_candidate_worksheet(plan)
    if payload != expected:
        add(
            blockers,
            "single_player_parallel_capture_candidate_worksheet_mismatch",
            "$single_player_worksheet",
            expected=expected,
            actual=payload,
        )
    if payload.get("schema") != SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_SCHEMA:
        add(
            blockers,
            "single_player_parallel_capture_candidate_worksheet_schema_mismatch",
            "$single_player_worksheet.schema",
            expected=SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_SCHEMA,
            actual=payload.get("schema"),
        )
    if payload.get("id") != SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_ID:
        add(
            blockers,
            "single_player_parallel_capture_candidate_worksheet_id_mismatch",
            "$single_player_worksheet.id",
            expected=SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_ID,
            actual=payload.get("id"),
        )
    if payload.get("file") != SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE:
        add(
            blockers,
            "single_player_parallel_capture_candidate_worksheet_file_mismatch",
            "$single_player_worksheet.file",
            expected=SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE,
            actual=payload.get("file"),
        )
    if payload.get("status") != "candidate_worksheet_template":
        add(
            blockers,
            "single_player_parallel_capture_candidate_worksheet_status_mismatch",
            "$single_player_worksheet.status",
            value=payload.get("status"),
        )
    if payload.get("artifact_status") != "candidate_only":
        add(
            blockers,
            "single_player_parallel_capture_candidate_worksheet_artifact_status_mismatch",
            "$single_player_worksheet.artifact_status",
            value=payload.get("artifact_status"),
        )
    worksheet_target = validate_target(
        payload.get("target"),
        blockers,
        "$single_player_worksheet.target",
        expected_target=manifest.get("target") if isinstance(manifest.get("target"), dict) else None,
        reason_prefix="single_player_parallel_capture_candidate_worksheet_target",
    )
    validate_target_binding(
        payload.get("target_binding"),
        blockers,
        "$single_player_worksheet.target_binding",
        expected_target=worksheet_target,
        reason_prefix="single_player_parallel_capture_candidate_worksheet_target_binding",
    )
    validate_target_binding_id(
        payload.get("target_binding_id"),
        blockers,
        "$single_player_worksheet.target_binding_id",
        expected_target=worksheet_target,
        reason_prefix="single_player_parallel_capture_candidate_worksheet_target_binding_id",
    )
    validate_approved_runtime_window_binding(
        payload.get("approved_runtime_window_binding"),
        blockers,
        "$single_player_worksheet.approved_runtime_window_binding",
        expected_target=worksheet_target,
        reason_prefix="single_player_parallel_capture_candidate_worksheet_approved_runtime_window_binding",
    )
    if payload.get("current_route_blocker") != CURRENT_ROUTE_BLOCKER:
        add(
            blockers,
            "single_player_parallel_capture_candidate_worksheet_route_blocker_mismatch",
            "$single_player_worksheet.current_route_blocker",
            value=payload.get("current_route_blocker"),
        )
    if payload.get("next_required_artifact") != NEXT_REQUIRED_ARTIFACT:
        add(
            blockers,
            "single_player_parallel_capture_candidate_worksheet_next_required_artifact_mismatch",
            "$single_player_worksheet.next_required_artifact",
            value=payload.get("next_required_artifact"),
        )
    if payload.get("single_player_parallel_capture_sequence_id") != SINGLE_PLAYER_PARALLEL_CAPTURE_SEQUENCE_ID:
        add(
            blockers,
            "single_player_parallel_capture_candidate_worksheet_sequence_id_mismatch",
            "$single_player_worksheet.single_player_parallel_capture_sequence_id",
            value=payload.get("single_player_parallel_capture_sequence_id"),
        )
    if payload.get("surface_ids") != list(SINGLE_PLAYER_PARALLEL_CAPTURE_SURFACE_IDS):
        add(
            blockers,
            "single_player_parallel_capture_candidate_worksheet_surface_ids_mismatch",
            "$single_player_worksheet.surface_ids",
            expected=list(SINGLE_PLAYER_PARALLEL_CAPTURE_SURFACE_IDS),
            actual=payload.get("surface_ids"),
        )
    if payload.get("action_group_ids") != list(SINGLE_PLAYER_PARALLEL_CAPTURE_ACTION_GROUP_IDS):
        add(
            blockers,
            "single_player_parallel_capture_candidate_worksheet_action_group_ids_mismatch",
            "$single_player_worksheet.action_group_ids",
            expected=list(SINGLE_PLAYER_PARALLEL_CAPTURE_ACTION_GROUP_IDS),
            actual=payload.get("action_group_ids"),
        )
    if payload.get("primary_surface_id") != "player_principal_lifecycle":
        add(
            blockers,
            "single_player_parallel_capture_candidate_worksheet_primary_surface_mismatch",
            "$single_player_worksheet.primary_surface_id",
            value=payload.get("primary_surface_id"),
        )
    if payload.get("primary_row_index") != 1:
        add(
            blockers,
            "single_player_parallel_capture_candidate_worksheet_primary_row_index_mismatch",
            "$single_player_worksheet.primary_row_index",
            value=payload.get("primary_row_index"),
        )
    if payload.get("single_player_route_constraints") != EXPECTED_SINGLE_PLAYER_ROUTE_CONSTRAINTS:
        add(
            blockers,
            "single_player_parallel_capture_candidate_worksheet_route_constraints_mismatch",
            "$single_player_worksheet.single_player_route_constraints",
            expected=EXPECTED_SINGLE_PLAYER_ROUTE_CONSTRAINTS,
            actual=payload.get("single_player_route_constraints"),
        )
    rows = payload.get("worksheet_rows")
    if not isinstance(rows, list):
        add(
            blockers,
            "single_player_parallel_capture_candidate_worksheet_rows_missing_or_invalid",
            "$single_player_worksheet.worksheet_rows",
            value=rows,
        )
    else:
        observed = [row.get("surface_id") for row in rows if isinstance(row, dict)]
        if observed != list(SINGLE_PLAYER_PARALLEL_CAPTURE_SURFACE_IDS):
            add(
                blockers,
                "single_player_parallel_capture_candidate_worksheet_row_order_mismatch",
                "$single_player_worksheet.worksheet_rows",
                expected=list(SINGLE_PLAYER_PARALLEL_CAPTURE_SURFACE_IDS),
                actual=observed,
            )
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                add(
                    blockers,
                    "single_player_parallel_capture_candidate_worksheet_row_invalid",
                    f"$single_player_worksheet.worksheet_rows[{index}]",
                    value=row,
                )
                continue
            if row.get("observation_rows") != []:
                add(
                    blockers,
                    "single_player_parallel_capture_candidate_worksheet_observation_rows_not_blank",
                    f"$single_player_worksheet.worksheet_rows[{index}].observation_rows",
                    value=row.get("observation_rows"),
                )
            fields = row.get("worksheet_fields")
            if not isinstance(fields, list) or not fields:
                add(
                    blockers,
                    "single_player_parallel_capture_candidate_worksheet_fields_missing_or_invalid",
                    f"$single_player_worksheet.worksheet_rows[{index}].worksheet_fields",
                    value=fields,
                )
            else:
                field_ids = [
                    field.get("field_id")
                    for field in fields
                    if isinstance(field, dict)
                ]
                missing_fields = sorted(set(LIFECYCLE_CORRELATION_FIELD_IDS) - set(field_ids))
                if missing_fields:
                    add(
                        blockers,
                        "single_player_parallel_capture_candidate_worksheet_correlation_fields_missing",
                        f"$single_player_worksheet.worksheet_rows[{index}].worksheet_fields",
                        fields=missing_fields,
                    )
                if row.get("surface_id") == "player_principal_lifecycle":
                    required_primary_fields = {
                        "player_principal_join_cycle_step",
                        "session_start_observer_role",
                        "checkjoin_rejected_start_shape",
                        "session_end_correlation_shape",
                        "approved_evidence_manifest_path",
                    }
                    missing_primary_fields = sorted(required_primary_fields - set(field_ids))
                    if missing_primary_fields:
                        add(
                            blockers,
                            "single_player_parallel_capture_candidate_worksheet_primary_fields_missing",
                            f"$single_player_worksheet.worksheet_rows[{index}].worksheet_fields",
                            fields=missing_primary_fields,
                        )
            validate_lifecycle_correlation_metadata(
                row.get("lifecycle_correlation_metadata"),
                blockers,
                f"$single_player_worksheet.worksheet_rows[{index}].lifecycle_correlation_metadata",
                expected_target=worksheet_target,
                reason_prefix="single_player_parallel_capture_candidate_worksheet_row_lifecycle_correlation_metadata",
            )
            validate_lifecycle_correlation_field_ids(
                row.get("correlation_field_ids"),
                blockers,
                f"$single_player_worksheet.worksheet_rows[{index}].correlation_field_ids",
                reason_prefix="single_player_parallel_capture_candidate_worksheet_row_correlation",
            )
            for key in (
                "candidate_only",
                "non_evidence",
                "requires_checker_acceptance",
                "requires_player_principal_triplet",
                "blocked_by_player_principal_evidence",
                "same_approved_runtime_window_required",
                "exact_target_binding_required",
                "correlation_metadata_required",
                "correlation_metadata_blank_by_default",
                "correlation_metadata_non_evidence",
            ):
                if row.get(key) is not True:
                    add(
                        blockers,
                        "single_player_parallel_capture_candidate_worksheet_row_true_flag_missing",
                        f"$single_player_worksheet.worksheet_rows[{index}].{key}",
                        value=row.get(key),
                    )
            for key in (
                "counts_as_approved_runtime_evidence",
                "counts_as_runtime_evidence",
                "counts_as_sdk_progress",
                "counts_as_p0_progress",
                "clears_approved_runtime_evidence_missing",
                "runtime_ready",
                "public_sdk_ready",
                "stable_sdk_ready",
            ):
                if row.get(key) is not False:
                    add(
                        blockers,
                        "single_player_parallel_capture_candidate_worksheet_row_false_flag_overclaim",
                        f"$single_player_worksheet.worksheet_rows[{index}].{key}",
                        value=row.get(key),
                    )
    validate_candidate_only_metadata(
        payload.get("candidate_only_metadata"),
        blockers,
        "$single_player_worksheet.candidate_only_metadata",
    )
    validate_parallel_capture_boundary(
        payload.get("parallel_capture_boundary"),
        blockers,
        "$single_player_worksheet.parallel_capture_boundary",
    )
    validate_player_principal_window_composition(
        payload.get("player_principal_window_composition"),
        blockers,
        "$single_player_worksheet.player_principal_window_composition",
    )
    validate_lifecycle_correlation_metadata(
        payload.get("lifecycle_correlation_metadata"),
        blockers,
        "$single_player_worksheet.lifecycle_correlation_metadata",
        expected_target=worksheet_target,
        reason_prefix="single_player_parallel_capture_candidate_worksheet_lifecycle_correlation_metadata",
    )
    validate_text_privacy_boundary(
        payload.get("text_privacy_boundary"),
        blockers,
        "$single_player_worksheet.text_privacy_boundary",
    )
    validate_non_substitution_flags(
        payload.get("non_substitution_flags"),
        blockers,
        "$single_player_worksheet.non_substitution_flags",
    )
    validate_single_player_route_constraints(
        payload.get("single_player_route_constraints"),
        blockers,
        "$single_player_worksheet.single_player_route_constraints",
        reason_prefix="single_player_parallel_capture_candidate_worksheet_route_constraints",
    )
    check_non_claim_flags(
        payload.get("non_claim_flags"),
        blockers,
        "$single_player_worksheet.non_claim_flags",
    )
    for key in (
        "candidate_only",
        "non_evidence",
        "single_player_sequence_rows",
        "primary_player_principal_row_included",
        "side_lane_rows_included",
        "correlation_metadata_required",
        "correlation_metadata_non_evidence",
        "requires_checker_acceptance",
        "requires_player_principal_triplet",
        "blocked_by_player_principal_evidence",
    ):
        if payload.get(key) is not True:
            add(
                blockers,
                "single_player_parallel_capture_candidate_worksheet_true_flag_missing",
                f"$single_player_worksheet.{key}",
                value=payload.get(key),
            )
    for key in (
        "raw_player_text_retention_allowed",
        "raw_player_text_capture_allowed",
        "raw_chat_payload_capture_allowed",
        "private_player_data_retention_allowed",
        "secrets_or_webhook_retention_allowed",
        "authorizes_live_log_reads",
        "authorizes_runtime_capture",
        "authorizes_discord_send",
        "authorizes_server_restart",
        "authorizes_marker_or_env_changes",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_as_sdk_progress",
        "counts_as_p0_progress",
        "clears_approved_runtime_evidence_missing",
        "runtime_ready",
        "public_sdk_ready",
        "stable_sdk_ready",
    ):
        if payload.get(key) is not False:
            add(
                blockers,
                "single_player_parallel_capture_candidate_worksheet_false_flag_overclaim",
                f"$single_player_worksheet.{key}",
                value=payload.get(key),
            )


def validate_text_boundaries(pack_root: Path, manifest: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    readme = (pack_root / "README.md").read_text(encoding="utf-8") if (pack_root / "README.md").exists() else ""
    runbook = (pack_root / "operator-runbook.md").read_text(encoding="utf-8") if (pack_root / "operator-runbook.md").exists() else ""
    required = (
        "not approved runtime evidence",
        "does not authorize live operations",
        "Do not retain raw player text",
        "Keep at most two ARK servers running.",
        "Next-action groups:",
        "Run the strict player-principal approved evidence checker first.",
        "Side-lanes remain non-counting before the player-principal blocker is solved.",
        "optional parallel side-lane capture alongside a separately approved player-principal lifecycle window",
        "Side-lane groups are optional parallel candidate observations",
        "cannot authorize that window or replace player-principal evidence",
        "same approved runtime window, instance, and map",
        "Lifecycle correlation metadata:",
        "same redacted side_lane_correlation_id",
        "primary_lifecycle_phase_anchor",
        "event-label-only primary_lifecycle_event_reference",
        "metadata is non-evidence",
        "Admin/commands/dino/tribe/buff status-only candidate path",
        "Broad status-only candidate path:",
        "Simultaneous side-lane candidate worksheet template",
        "Admin/commands/dino/tribe/buff/inventory/item/transfer/mission parallel candidate matrix",
        "Parallel side-lane candidate matrix:",
        "Single-player parallel capture sequence:",
        "Single-player route surfaces:",
        "Single-player route domains:",
        "Single-player route excludes:",
        "no-restart, no-Discord, non-evidence, non-progress, and cannot clear approved_runtime_evidence_missing",
        "raw player text retention is not allowed",
        "Tester action:",
        "Tester actions: do not require or authorize starts, stops, restarts, marker changes, env changes, live log reads, or Discord sends.",
        "Target-bound offline checker command matrix",
        "Target-bound offline checker commands:",
        "Command placeholders resolve only to copied offline candidate-artifact templates.",
        "Path arguments point under `candidate-artifacts/`; scalar inputs use `<read-text:...>` templates.",
    )
    combined = f"{readme}\n{runbook}"
    for text in required:
        if text not in combined:
            add(blockers, "text_boundary_phrase_missing", "$text", phrase=text)
    target = manifest.get("target") if isinstance(manifest, dict) else None
    if isinstance(target, dict) and isinstance(target.get("instance"), str) and isinstance(target.get("map"), str):
        target_phrase = f"Target: `{target['instance']}` / `{target['map']}`"
        if target_phrase not in readme:
            add(blockers, "readme_target_phrase_mismatch", "$text.README.md", phrase=target_phrase)
        if target_phrase not in runbook:
            add(blockers, "runbook_target_phrase_mismatch", "$text.operator-runbook.md", phrase=target_phrase)


def validate_pack(pack_root: Path, *, expected_target: dict[str, str] | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    blockers: list[dict[str, Any]] = []
    manifest = load_json(pack_root / "manifest.json", blockers, "$.manifest")
    if manifest:
        validate_manifest(pack_root, manifest, blockers, expected_target=expected_target)
        validate_artifact_hashes(pack_root, manifest, blockers)
    plan = load_json(pack_root / "multi-surface-capture-plan.json", blockers, "$plan")
    intake = load_json(pack_root / "candidate-artifact-intake.json", blockers, "$intake")
    matrix = load_json(pack_root / "checker-command-matrix.json", blockers, "$matrix")
    non_claim = load_json(pack_root / "non-claim-manifest.json", blockers, "$non_claim")
    worksheet = load_json(pack_root / BROAD_BETA_CAPTURE_WORKSHEET_FILE, blockers, "$worksheet")
    simultaneous_worksheet = load_json(
        pack_root / SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE,
        blockers,
        "$simultaneous_worksheet",
    )
    single_player_worksheet = load_json(
        pack_root / SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE,
        blockers,
        "$single_player_worksheet",
    )
    for label, payload in (
        ("$manifest", manifest),
        ("$plan", plan),
        ("$intake", intake),
        ("$matrix", matrix),
        ("$non_claim", non_claim),
        ("$worksheet", worksheet),
        ("$simultaneous_worksheet", simultaneous_worksheet),
        ("$single_player_worksheet", single_player_worksheet),
    ):
        if payload:
            payload_target = (
                payload.get("target")
                if isinstance(payload.get("target"), dict)
                else manifest.get("target")
                if isinstance(manifest.get("target"), dict)
                else None
            )
            validate_explicit_source_metadata(
                payload,
                blockers,
                label,
                expected_target=payload_target,
            )
            validate_false_progress_aliases(payload, blockers, label)
            validate_target_binding_aliases(payload, blockers, label)
    if manifest and plan:
        validate_next_action_groups(
            manifest.get("next_action_groups"),
            plan.get("next_action_groups"),
            blockers,
            "$.next_action_groups",
        )
        validate_broad_beta_capture_pack_path(
            manifest.get("broad_beta_capture_pack_path"),
            plan.get("broad_beta_capture_pack_path"),
            blockers,
            "$.broad_beta_capture_pack_path",
            expected_target=manifest.get("target") if isinstance(manifest.get("target"), dict) else None,
        )
        validate_plan(plan, manifest, blockers)
    if manifest and plan and intake:
        validate_intake(intake, plan, manifest, blockers)
    if matrix and plan:
        validate_matrix(matrix, plan, blockers)
    if manifest and non_claim:
        validate_non_claim_manifest(non_claim, manifest, blockers)
    if manifest and plan and worksheet:
        validate_broad_beta_capture_candidate_worksheet(worksheet, plan, manifest, blockers)
    if manifest and plan and simultaneous_worksheet:
        validate_simultaneous_beta_capture_candidate_worksheet(
            simultaneous_worksheet,
            plan,
            manifest,
            blockers,
        )
    if manifest and plan and single_player_worksheet:
        validate_single_player_parallel_capture_candidate_worksheet(
            single_player_worksheet,
            plan,
            manifest,
            blockers,
        )
    if non_claim and plan:
        validate_next_action_groups(
            non_claim.get("next_action_groups"),
            plan.get("next_action_groups"),
            blockers,
            "$non_claim.next_action_groups",
        )
    validate_artifact_retention_scan(pack_root, blockers)
    validate_text_boundaries(pack_root, manifest, blockers)
    return manifest, blockers


def build_report(pack_root: Path, manifest: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    ready = not blockers
    target = manifest.get("target") if isinstance(manifest, dict) else None
    return {
        "schema": REPORT_SCHEMA,
        "status": "candidate_pack_validated" if ready else "candidate_pack_invalid",
        "ready": ready,
        "ready_scope": "candidate_capture_pack_integrity_only",
        "pack_root": str(pack_root),
        "target": target,
        "target_binding": manifest.get("target_binding") if isinstance(manifest, dict) else None,
        "target_binding_id": manifest.get("target_binding_id") if isinstance(manifest, dict) else None,
        "approved_runtime_window_binding": (
            manifest.get("approved_runtime_window_binding") if isinstance(manifest, dict) else None
        ),
        "candidate_surface_count": manifest.get("candidate_surface_count") if isinstance(manifest, dict) else None,
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_authorization": NON_AUTHORIZATION,
        "source_metadata_required": manifest.get("source_metadata_required") if isinstance(manifest, dict) else None,
        "source_metadata": manifest.get("source_metadata") if isinstance(manifest, dict) else None,
        "candidate_only_metadata": candidate_only_metadata(),
        "parallel_capture_boundary": parallel_capture_boundary(),
        "player_principal_window_composition": player_principal_window_composition(),
        "text_privacy_boundary": text_privacy_boundary(),
        "beta_capture_interaction_boundary": beta_capture_interaction_boundary(),
        "non_substitution_flags": non_substitution_flags(),
        "next_action_groups": manifest.get("next_action_groups") if isinstance(manifest.get("next_action_groups"), list) else [],
        "broad_beta_capture_pack_path": (
            manifest.get("broad_beta_capture_pack_path")
            if isinstance(manifest.get("broad_beta_capture_pack_path"), dict)
            else None
        ),
        "broad_beta_capture_candidate_worksheet_template": (
            manifest.get("broad_beta_capture_candidate_worksheet_template")
            if isinstance(manifest, dict)
            else None
        ),
        "broad_beta_capture_candidate_worksheet_schema": (
            manifest.get("broad_beta_capture_candidate_worksheet_schema")
            if isinstance(manifest, dict)
            else None
        ),
        "broad_beta_capture_candidate_worksheet_id": (
            manifest.get("broad_beta_capture_candidate_worksheet_id")
            if isinstance(manifest, dict)
            else None
        ),
        "broad_beta_capture_candidate_worksheet_included": (
            manifest.get("broad_beta_capture_candidate_worksheet_included")
            if isinstance(manifest, dict)
            else False
        ),
        "simultaneous_beta_capture_candidate_worksheet_template": (
            manifest.get("simultaneous_beta_capture_candidate_worksheet_template")
            if isinstance(manifest, dict)
            else None
        ),
        "simultaneous_beta_capture_candidate_worksheet_schema": (
            manifest.get("simultaneous_beta_capture_candidate_worksheet_schema")
            if isinstance(manifest, dict)
            else None
        ),
        "simultaneous_beta_capture_candidate_worksheet_id": (
            manifest.get("simultaneous_beta_capture_candidate_worksheet_id")
            if isinstance(manifest, dict)
            else None
        ),
        "simultaneous_beta_capture_candidate_worksheet_surfaces": (
            manifest.get("simultaneous_beta_capture_candidate_worksheet_surfaces")
            if isinstance(manifest, dict)
            else []
        ),
        "simultaneous_beta_capture_candidate_worksheet_included": (
            manifest.get("simultaneous_beta_capture_candidate_worksheet_included")
            if isinstance(manifest, dict)
            else False
        ),
        "single_player_parallel_capture_candidate_worksheet_template": (
            manifest.get("single_player_parallel_capture_candidate_worksheet_template")
            if isinstance(manifest, dict)
            else None
        ),
        "single_player_parallel_capture_candidate_worksheet_schema": (
            manifest.get("single_player_parallel_capture_candidate_worksheet_schema")
            if isinstance(manifest, dict)
            else None
        ),
        "single_player_parallel_capture_candidate_worksheet_id": (
            manifest.get("single_player_parallel_capture_candidate_worksheet_id")
            if isinstance(manifest, dict)
            else None
        ),
        "single_player_parallel_capture_candidate_worksheet_surfaces": (
            manifest.get("single_player_parallel_capture_candidate_worksheet_surfaces")
            if isinstance(manifest, dict)
            else []
        ),
        "single_player_parallel_capture_candidate_worksheet_included": (
            manifest.get("single_player_parallel_capture_candidate_worksheet_included")
            if isinstance(manifest, dict)
            else False
        ),
        "parallel_beta_capture_side_lane_matrix": (
            manifest.get("parallel_beta_capture_side_lane_matrix")
            if isinstance(manifest.get("parallel_beta_capture_side_lane_matrix"), dict)
            else None
        ),
        "single_player_parallel_capture_sequence": (
            manifest.get("single_player_parallel_capture_sequence")
            if isinstance(manifest.get("single_player_parallel_capture_sequence"), dict)
            else None
        ),
        "target_bound_checker_command_matrix": (
            manifest.get("target_bound_checker_command_matrix")
            if isinstance(manifest.get("target_bound_checker_command_matrix"), dict)
            else None
        ),
        "side_lane_capture_queue": (
            manifest.get("side_lane_capture_queue")
            if isinstance(manifest.get("side_lane_capture_queue"), dict)
            else None
        ),
        "candidate_only": True,
        "touches_live_servers": False,
        "raw_player_text_retention_allowed": False,
        "raw_player_text_capture_allowed": False,
        "raw_chat_payload_capture_allowed": False,
        "private_player_data_retention_allowed": False,
        "secrets_or_webhook_retention_allowed": False,
        "authorizes_live_operations": False,
        "authorizes_live_log_reads": False,
        "authorizes_runtime_capture": False,
        "authorizes_server_restart": False,
        "authorizes_server_start": False,
        "authorizes_server_stop": False,
        "authorizes_marker_or_env_changes": False,
        "authorizes_discord_send": False,
        "pack_authorizes_restart": False,
        "pack_authorizes_discord": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "replaces_player_principal_evidence": False,
        "replaces_player_principal_triplet": False,
        "substitutes_for_player_principal_lifecycle_evidence": False,
        "substitutes_for_player_principal_lifecycle_triplet": False,
        "side_lane_substitutes_for_player_principal_lifecycle_evidence": False,
        "player_principal_lifecycle_evidence_substitution_allowed": False,
        "approved_runtime_evidence_substitution_allowed": False,
        "primary_evidence_substitution_allowed": False,
        "side_lane_counts_toward_sdk": False,
        "side_lane_counts_toward_p0": False,
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "next_required_artifact": NEXT_REQUIRED_ARTIFACT,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "plugin_hub_ready": False,
        "publication_ready": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack", type=Path, help="Pack directory or manifest.json path")
    parser.add_argument("--expected-instance")
    parser.add_argument("--expected-map")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.expected_instance is not None and not SAFE_TOKEN_RE.fullmatch(args.expected_instance):
        raise SystemExit(f"--expected-instance contains unsafe characters: {args.expected_instance}")
    if args.expected_map is not None and not SAFE_MAP_RE.fullmatch(args.expected_map):
        raise SystemExit(f"--expected-map contains unsafe characters: {args.expected_map}")
    return args


def main() -> int:
    args = parse_args()
    pack_root = resolve_pack_root(args.pack)
    expected_target = None
    if args.expected_instance is not None or args.expected_map is not None:
        if args.expected_instance is None or args.expected_map is None:
            raise SystemExit("--expected-instance and --expected-map must be provided together")
        expected_target = {"instance": args.expected_instance, "map": args.expected_map}
    manifest, blockers = validate_pack(pack_root, expected_target=expected_target)
    report = build_report(pack_root, manifest, blockers)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"multi_surface_beta_capture_pack_check={report['status']}")
        print(f"ready={str(report['ready']).lower()}")
        print("candidate_only=true")
        print("same_approved_runtime_window_required=true")
        print("raw_player_text_retention_allowed=false")
        print("secrets_or_webhook_retention_allowed=false")
        if isinstance(report.get("parallel_beta_capture_side_lane_matrix"), dict):
            print(f"parallel_beta_capture_matrix={report['parallel_beta_capture_side_lane_matrix']['id']}")
            print("parallel_beta_capture_status=status_only_candidate_non_evidence")
        if isinstance(report.get("single_player_parallel_capture_sequence"), dict):
            print(f"single_player_parallel_capture_sequence={report['single_player_parallel_capture_sequence']['id']}")
            print("single_player_parallel_capture_status=status_only_candidate_non_evidence")
        if isinstance(report.get("target_bound_checker_command_matrix"), dict):
            print(f"target_bound_checker_command_matrix={report['target_bound_checker_command_matrix']['id']}")
            print("target_bound_checker_command_matrix_status=offline_command_templates_candidate_only")
        if isinstance(report.get("side_lane_capture_queue"), dict):
            print(f"side_lane_capture_queue={report['side_lane_capture_queue']['id']}")
            print("side_lane_capture_queue_status=queued_candidate_observations_non_counting")
        if report.get("broad_beta_capture_candidate_worksheet_included") is True:
            print(f"broad_beta_capture_candidate_worksheet={BROAD_BETA_CAPTURE_WORKSHEET_FILE}")
        if report.get("simultaneous_beta_capture_candidate_worksheet_included") is True:
            print(
                "simultaneous_beta_capture_candidate_worksheet="
                f"{SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE}"
            )
        if report.get("single_player_parallel_capture_candidate_worksheet_included") is True:
            print(
                "single_player_parallel_capture_candidate_worksheet="
                f"{SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE}"
            )
        print("counts_as_approved_runtime_evidence=false")
        print("counts_as_sdk_progress=false")
        print(f"current_route_blocker={report['current_route_blocker']}")
        for blocker in report["blockers"]:
            print(f"blocker={blocker}")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
