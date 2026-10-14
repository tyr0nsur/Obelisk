#!/usr/bin/env python3
"""Summarize Obelisk SDK readiness without changing any readiness gate."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SDK_CHECK = REPO_ROOT / "scripts" / "check_public_sdk_v1_completion.py"
HEADER_GATE_CHECK = REPO_ROOT / "scripts" / "check_player_identity_public_header_gate.py"
CLOSURE_REQUEST = REPO_ROOT / "scripts" / "prepare_player_principal_lifecycle_evidence_closure_request.py"
PUBLIC_CONTRACT_DECISIONS = REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json"
DEFAULT_SCOPED_RELEASE_STATEMENT = REPO_ROOT / "docs" / "SCOPED_NON_COMPLETE_V1_RELEASE_STATEMENT.md"
PRINCIPAL_START_END_RUNTIME_EVIDENCE_SCHEMA = (
    "obelisk.players-identity-runtime-principal-start-end-evidence-check.v1"
)
PRINCIPAL_START_END_RUNTIME_EVIDENCE_REPORT_NAME = (
    "principal-start-end-evidence.check.json"
)
PRINCIPAL_START_END_READY_SCOPE = "principal_start_end_runtime_evidence_only"
PRINCIPAL_START_END_RESOLVED_INPUT = "runtime.lifecycle_start_end_evidence"
PRINCIPAL_START_END_STRICT_UNRESOLVED_INPUTS = (
    "approved_runtime_principal_lifecycle_evidence_bundle",
    "runtime.lifecycle_rejected_start_evidence",
)
MULTI_SURFACE_BETA_CAPTURE_PACK_CHECK_SCHEMA = (
    "obelisk.multi-surface-beta-capture-pack-check.v1"
)
MULTI_SURFACE_BETA_CAPTURE_PACK_READY_SCOPE = (
    "candidate_capture_pack_integrity_only"
)
MULTI_SURFACE_BETA_CAPTURE_PACK_VALIDATED_STATUS = "candidate_pack_validated"
MULTI_SURFACE_BETA_CAPTURE_PACK_CHECK = (
    REPO_ROOT / "scripts" / "check_obelisk_multi_surface_beta_capture_pack.py"
)
DISCORD_BETA_BRIDGE_CONFIG_CHECK = REPO_ROOT / "scripts" / "discord_beta_bridge.py"
LOCAL_DISCORD_BRIDGE_PYTHON = REPO_ROOT / "local" / "discord-bridge-venv" / "bin" / "python"
DISCORD_BETA_BRIDGE_CONFIG_CHECK_SCHEMA = (
    "obelisk.discord-beta-bridge-config-check.v1"
)
RUNTIME_EVIDENCE_STATUS_SCHEMA = (
    "obelisk.player-principal-lifecycle-runtime-evidence-status.v1"
)
CURRENT_LIVE_DIAGNOSTIC_BLOCKERS_SCHEMA = (
    "obelisk.player-principal-lifecycle-current-live-diagnostic-blockers.v1"
)
FAIL_CLOSED_ACTION_FALSE_FLAGS = (
    "approved_runtime_evidence",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "authorizes_runtime_work",
    "authorizes_server_work",
    "authorizes_server_operations",
    "authorizes_discord",
    "discord_authorized",
    "discord_authorized_by_request",
    "discord_authorized_by_this_report",
    "discord_notice_authorized",
    "discord_sent",
    "runtime_work_authorized",
    "server_operations_authorized",
    "authorizes_workspace_work",
    "authorizes_workspace_writes",
    "workspace_writes_authorized",
    "live_ops_authorized",
    "marker_env_changes_authorized",
    "publication_authorized",
    "runtime_capture_authorized",
    "reads_live_logs",
    "read_live_logs",
    "runtime_window_authorized",
    "runtime_window_activation_ready_under_recorded_standing_launch_authority",
    "runtime_window_preparation_counts_as_approved_runtime_evidence",
    "runtime_window_preparation_counts_as_runtime_evidence",
    "runtime_window_preparation_counts_toward_sdk",
    "runtime_window_preparation_counts_toward_p0_dependency_chain",
    "runtime_window_preparation_counts_toward_complete_sdk_claim",
    "standing_authority",
    "standing_authority_accepted",
    "standing_authority_acceptance",
    "standing_authority_ready",
    "standing_authority_counts_as_approved_runtime_evidence",
    "standing_authority_counts_as_runtime_evidence",
    "standing_authority_counts_toward_sdk",
    "standing_authority_counts_toward_p0_dependency_chain",
    "standing_authority_counts_toward_complete_sdk_claim",
    "standing_launch_authority_counts_as_approved_runtime_evidence",
    "standing_launch_authority_counts_as_runtime_evidence",
    "standing_launch_authority_counts_toward_sdk",
    "standing_launch_authority_counts_toward_p0_dependency_chain",
    "standing_launch_authority_counts_toward_complete_sdk_claim",
    "counts_as_approved_runtime_evidence",
    "counts_as_passive_evidence",
    "counts_as_passive_snapshot_evidence",
    "counts_as_runtime_evidence",
    "counts_as_sdk_evidence",
    "counts_as_public_sdk",
    "counts_as_runtime",
    "counts_as_v1_completion",
    "counts_toward_sdk",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "counts_toward_p0_dependency_chain",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "side_lane_counts_toward_sdk",
    "side_lane_counts_toward_p0",
    "p0_ready",
    "p0_dependency_ready",
    "p0_dependency_chain_accounted",
    "p0_dependency_chain_ready",
    "p0_accounting_counts_as_promoted_surface",
    "sdk_accounting_counts_as_completed_surface",
    "sdk_ready",
    "module_ready",
    "module_sdk_ready",
    "public_module_ready",
    "public_module_sdk_ready",
    "public_route_ready",
    "route_readiness_ready",
    "route_snapshot_ready",
    "public_or_runtime_accounting_allowed",
    "passive_snapshot_evidence_allowed",
    "runtime_delivery_allowed",
    "runtime_evidence_present",
    "runtime_evidence_ready",
    "sdk_evidence_ready",
    "ready",
    "complete_sdk_allowed",
    "complete_sdk_claim_allowed",
    "complete_sdk_ready",
    "activation_preconditions_met",
    "promotion_ready",
    "request_pack_ready",
    "route_ready",
    "public_sdk_ready",
    "public_abi_ready",
    "public_header_allowed",
    "runtime_v1_ready",
    "runtime_ready",
    "stable_claim_allowed",
    "stable_sdk_claim_allowed",
    "stable_sdk_ready",
    "v1_complete",
    "v1_completion",
    "v1_completion_ready",
    "v1_release_ready",
    "counts_toward_complete_sdk_claim_now",
    "counts_toward_p0_dependency_chain_claim_now",
    "notice_action_authorized",
    "accepted_notice_action",
    "accepted_player_notice_action",
    "approved_notice_action",
    "approved_player_notice_action",
    "player_notice_action_authorized",
    "notice_action_accepted",
    "notice_action_bundle_accepted",
    "notice_action_dry_run_accepted",
    "notice_action_sent",
    "notice_sent",
    "beta_notice_sent",
    "confirmed_beta_notice_sent",
    "confirmed_notice_sent",
    "player_notice_sent",
    "discord_sent",
    "discord_notice_sent",
    "notice_dry_run_sent",
    "player_notice_action_accepted",
    "player_notice_action_bundle_accepted",
    "player_notice_action_dry_run_accepted",
    "player_notice_action_sent",
    "player_notice_dry_run_sent",
    "notice_dry_run_accepted",
    "player_notice_dry_run_accepted",
    "notice_bundle_accepted",
    "player_notice_bundle_accepted",
    "bundle_accepted",
    "approved_bundle_request_accepted",
    "approved_bundle_request_ready",
    "approved_runtime_bundle_request_accepted",
    "approved_runtime_bundle_request_ready",
    "beta_notice_send_attested",
    "beta_notice_sent_attested",
    "evidence_bundle_accepted",
    "approved_bundle_accepted",
    "approved_runtime_evidence_accepted",
    "public_reachability_counts_as_approved_runtime_evidence",
    "public_reachability_counts_as_evidence",
    "public_reachability_counts_as_runtime_evidence",
    "public_reachability_counts_as_sdk_evidence",
    "public_reachability_counts_toward_runtime_evidence",
    "public_reachability_counts_toward_sdk_evidence",
    "public_reachability_accepted",
    "public_reachability_ready",
    "public_reachability_reachable",
    "public_reachability_satisfies_runtime_evidence",
    "public_reachability_unlock_allowed",
    "route_bound_identity_source_forwarding_ready",
    "identity_source_forwarding_ready",
    "permissions_ready",
    "permissions_admin_ready",
    "permissions_admin_public_ready",
    "permissions_admin_unlocked",
    "permission_ready",
    "command_response_ready",
    "command_response_unlocked",
    "command_chat_response_ready",
    "commands_ready",
    "commands_replies_ready",
    "commands_replies_unlocked",
    "chat_replies_ready",
    "send_chat_ready",
    "broadcast_ready",
    "rcon_ready",
    "clears_approved_runtime_evidence_missing",
    "approved_runtime_evidence_missing_cleared",
    "blocker_cleared",
    "blocker_resolved",
    "current_route_blocker_cleared",
    "current_route_blocker_resolved",
    "remaining_route_blockers_cleared",
    "remaining_route_blockers_resolved",
    "route_blocker_cleared",
    "route_blocker_resolved",
    "route_lock_cleared",
    "route_lock_resolved",
    "sdk_route_blocker_cleared",
    "sdk_route_blocker_resolved",
    "side_lane_promoted",
    "structure_build_policy_ready",
    "active_notice_ready",
    "active_notice_sent",
    "active_notice_accepted",
    "active_notice_updated",
    "active_notice_counts_toward_sdk",
    "active_notice_counts_toward_p0_dependency_chain",
    "active_notice_counts_toward_complete_sdk_claim",
)
FAIL_CLOSED_ACTION_ZERO_FIELDS = (
    "claim_progress_contribution",
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_progress_contribution",
    "credit",
    "credits",
    "claim_credit",
    "claim_credits",
    "complete_sdk_credit",
    "complete_sdk_credits",
    "complete_sdk_claim_credit",
    "complete_sdk_claim_credits",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_progress_contribution",
    "p0_dependency_progress_contribution",
    "p0_credit",
    "p0_credits",
    "p0_dependency_chain_credit",
    "p0_dependency_chain_credits",
    "public_sdk_progress_contribution",
    "runtime_progress_contribution",
    "sdk_credit",
    "sdk_credits",
    "sdk_completion_credit",
    "sdk_completion_credits",
    "v1_completion_contribution",
    "v1_completion_credit",
    "v1_completion_credits",
    "progress",
)
NOTICE_OR_BUNDLE_STATUS_KEYS = {
    "acceptance",
    "bundle_status",
    "delivery_status",
    "dry_run_status",
    "mode",
    "notice_status",
    "outcome",
    "result",
    "state",
    "status",
}
NOTICE_OR_BUNDLE_STATUS_CONTAINER_KEYS = {
    "accepted_notice_action",
    "active_notice",
    "active_notice_action",
    "active_notice_report",
    "approved_bundle",
    "beta_notice",
    "beta_notice_attestation",
    "beta_notice_send",
    "beta_notice_send_attestation",
    "bundle_acceptance",
    "confirmed_beta_notice_report",
    "confirmed_notice_report",
    "discord_notice",
    "evidence_bundle",
    "notice_report",
    "notice_action",
    "notice_bundle",
    "notice_dry_run",
    "player_notice",
    "player_notice_action",
    "player_notice_bundle",
    "player_notice_dry_run",
    "runtime_evidence_bundle",
}
NOTICE_OR_BUNDLE_NON_PROGRESS_FALSE_ALIAS_KEYS = {
    "accepted_bundle",
    "accepted_notice_action",
    "accepted_player_notice_action",
    "active_notice_accepted",
    "active_notice_action_accepted",
    "active_notice_action_sent",
    "active_notice_sent",
    "accepted_runtime_evidence",
    "approved_bundle_accepted",
    "approved_notice_action",
    "approved_player_notice_action",
    "approved_runtime_evidence_accepted",
    "beta_notice_send_attested",
    "beta_notice_sent",
    "beta_notice_sent_attested",
    "bot_notice_send_performed",
    "bot_notice_sent",
    "bundle_accepted",
    "confirmed_send",
    "confirmed_beta_notice_sent",
    "confirmed_notice_sent",
    "discord_beta_bridge_bot_notice_sent",
    "discord_beta_bridge_notice_sent",
    "discord_beta_bridge_send_performed",
    "discord_beta_bot_notice_sent",
    "discord_bot_notice_sent",
    "discord_sent",
    "discord_notice_sent",
    "evidence_bundle_accepted",
    "notice_action_accepted",
    "notice_action_bundle_accepted",
    "notice_action_dry_run_accepted",
    "notice_action_sent",
    "notice_bundle_accepted",
    "notice_delivery_accepted",
    "notice_dry_run_accepted",
    "notice_dry_run_sent",
    "notice_sent",
    "approved_bundle_request_accepted",
    "approved_runtime_bundle_request_accepted",
    "player_notice_action_accepted",
    "player_notice_action_bundle_accepted",
    "player_notice_action_dry_run_accepted",
    "player_notice_action_sent",
    "player_notice_bundle_accepted",
    "player_notice_delivery_accepted",
    "player_notice_dry_run_accepted",
    "player_notice_dry_run_sent",
    "player_notice_sent",
    "send_performed",
}
NOTICE_OR_BUNDLE_POSITIVE_STATUS_VALUES = {
    "accepted",
    "accepted_bundle",
    "approved",
    "bundle_accepted",
    "closed",
    "confirmed_send",
    "delivered",
    "delivery_accepted",
    "dry_run_accepted",
    "dry_run_passed",
    "dry_run_sent",
    "notice_sent",
    "passed",
    "present",
    "prepared",
    "referenced",
    "ready_to_send",
    "send_ready",
    "sent",
    "sent_ok",
}
P0_DEPENDENCY_CHAIN_SURFACES = (
    "obelisk.player_identity.v1",
    "obelisk.permissions_admin.v1",
    "obelisk.command_chat_response_path.v1",
    "obelisk.commands_replies.v1",
)
COMPLETE_SDK_BLOCKER_SURFACES = (
    "obelisk.player_identity.v1",
    "obelisk.permissions_admin.v1",
    "obelisk.command_chat_response_path.v1",
    "obelisk.commands_replies.v1",
    "obelisk.inventory_items_mutation.v1",
    "obelisk.lifecycle_ops_recovery.v1",
    "obelisk.structure_census.v1",
    "obelisk.mission_transfer_dino_tribe.v1",
    "obelisk.object_identity_resource_handle.v1",
    "obelisk.player_services_economy_mobility.v1",
    "obelisk.operator_ingress_storage.v1",
    "obelisk.gameplay_tick_callbacks.v1",
)
OPERATOR_CONTEXT_SOURCE_KEYS = (
    (
        "post_reboot_passive_monitor",
        "post-reboot passive monitor context",
        (
            "post_reboot_monitor_context",
            "post_reboot_passive_monitor",
            "post_reboot_passive_monitor_context",
            "passive_latest_summary",
            "passive_monitor_summary",
            "player_principal_passive_snapshot_latest",
        ),
    ),
    (
        "confirmed_beta_notice",
        "confirmed beta notice context",
        (
            "confirmed_beta_notice_report",
            "confirmed_notice_report",
            "beta_notice_send_attestation",
            "beta_notice_attestation",
        ),
    ),
    (
        "package_shape_install",
        "installed SDK package-shape context",
        (
            "installed_sdk_package_shape",
            "installed_sdk_package",
            "package_shape_install",
        ),
    ),
    (
        "runtime_live_status",
        "runtime live status context",
        (
            "installed_runtime",
            "installed_runtime_status",
            "runtime_install_status",
            "runtime_installed_status",
            "broadcast_ok",
            "broadcast_status",
            "rcon_ok",
            "rcon_status",
        ),
    ),
    (
        "scoped_non_complete_release_statement",
        "scoped non-complete release-statement context",
        (
            "scoped_release_statement",
            "default_scoped_release_statement",
            "scoped_non_complete_release_statement",
        ),
    ),
)
DEFAULT_PLAYER_NOTICE_ACTION_ID = "player_notice_action"
REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES = (
    "session_start",
    "session_start_rejected",
    "session_end",
)
CURRENT_ROLE_SOURCE_REQUIREMENT = (
    "checked_copied_runtime_log_artifact_or_explicit_current_fresh_log_input"
)
TRUSTED_CURRENT_ROLE_SOURCE_BOOLEAN_KEYS = (
    "checked_copied_runtime_log_artifact",
    "checked_runtime_log_artifact",
    "checked_obelisk_log_artifact",
    "current_runtime_log_artifact_checked",
    "explicit_current_fresh_log_input",
    "current_fresh_log_input",
    "fresh_obelisk_log_input",
    "fresh_runtime_log_input",
)
TRUSTED_CURRENT_ROLE_SOURCE_TEXT_KEYS = (
    "artifact_kind",
    "artifact_type",
    "current_input",
    "current_input_source",
    "current_log_input",
    "current_role_source",
    "current_source",
    "current_source_type",
    "evidence_artifact",
    "evidence_source",
    "input_kind",
    "input_source",
    "log_artifact",
    "role_evidence_source",
    "role_source",
    "runtime_log_artifact",
    "runtime_log_source",
    "source",
    "source_kind",
    "source_type",
)
TRUSTED_CURRENT_ROLE_SOURCE_MARKERS = (
    "checked_copied_runtime_log_artifact",
    "checked_runtime_log_artifact",
    "checked_obelisk_log_artifact",
    "checked_copied_obelisk_log",
    "current_runtime_log_artifact_checked",
    "explicit_current_fresh_log_input",
    "current_fresh_log_input",
    "current_fresh_obelisk_log_input",
    "fresh_obelisk_log_input",
    "fresh_runtime_log_input",
)
UNTRUSTED_CURRENT_ROLE_SOURCE_TEXT_MARKERS = (
    "current_docs",
    "doc",
    "docs",
    "documentation",
    "handoff",
    "historical",
    "latest_summary",
    "passive_monitor",
    "passive_snapshot",
    "passive_summary",
)
SIDE_LANE_CANDIDATE_STATUS_MARKERS = {
    "candidate",
    "candidate_accepted",
    "candidate_blocked",
    "candidate_only",
    "candidate_only_accepted",
    "candidate_ready",
    "consume",
    "consume_mode",
    "excluded",
    "internal_planning",
    "manifest_umbrella_excluded",
    "non_claim",
    "post_v1",
    "release_statement_umbrella_excluded",
    "second_source_promotion",
}
SIDE_LANE_NON_CLAIM_BOOKKEEPING_FLAG_KEYS = {
    "explicit_non_promoted_outcome",
    "v1_accounted",
}
SIDE_LANE_NON_CLAIM_BOOKKEEPING_ROUTES = {
    "excluded",
    "manifest_umbrella_excluded",
    "post_v1",
    "release_statement_umbrella_excluded",
}
APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE = (
    "approved_runtime_principal_lifecycle_evidence_bundle"
)
APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_CHECK_REPORT_SCHEMA = (
    "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1"
)
APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_EVIDENCE_SCHEMA = (
    "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1"
)
APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_READY_SCOPE = "runtime_evidence_only"
APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_REJECTED_START_SHAPE = (
    "ShooterGameMode.CheckJoinInProgress(1,0)"
)
APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_EVIDENCE_CHECKER = (
    "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
)
IDENTITY_PUBLIC_CONTRACT_READINESS_CHECKER = (
    "scripts/check_player_identity_public_contract_readiness.py"
)
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA = (
    "obelisk.player-identity-promotion-certificate.v1"
)
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_ARTIFACT = (
    "hash_bound_player_identity_promotion_certificate"
)
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_BLOCKER = (
    "player_identity_promotion_certificate_missing"
)
PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA = (
    "obelisk.permissions-admin-promotion-certificate.v1"
)
PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_ARTIFACT = (
    "hash_bound_permissions_admin_promotion_certificate"
)
COMMAND_CHAT_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA = (
    "obelisk.command-chat-response-path-promotion-certificate.v1"
)
COMMAND_CHAT_RESPONSE_PROMOTION_CERTIFICATE_ARTIFACT = (
    "hash_bound_command_chat_response_path_promotion_certificate"
)
COMMANDS_REPLIES_PUBLIC_READINESS_CHECK_SCHEMA = (
    "obelisk.commands-replies-public-readiness-check.v1"
)
COMMANDS_REPLIES_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA = (
    "obelisk.commands-replies-promotion-certificate-build-report.v1"
)
COMMANDS_REPLIES_PROMOTION_CERTIFICATE_SCHEMA = (
    "obelisk.commands-replies-promotion-certificate.v1"
)
COMMANDS_REPLIES_PROMOTION_CERTIFICATE_ARTIFACT = (
    "hash_bound_commands_replies_promotion_certificate"
)
COMMANDS_REPLIES_FINAL_GATE_SOURCE_KEYS = (
    "commands_replies_promotion_certificate_build_report",
    "commands_replies_final_gate_build_report",
    "commands_replies_final_gate",
    "hash_bound_commands_replies_promotion_certificate",
    "commands_replies_promotion_certificate",
)
PERMISSIONS_ADMIN_PUBLIC_READINESS_CHECKER = (
    "scripts/check_permissions_admin_public_readiness.py"
)
STANDING_LAUNCH_AUTHORITY_RECORDED = True
STANDING_LAUNCH_AUTHORITY_SOURCE = "2026-06-06_operator_standing_launch_authority"
STANDING_OR_CURRENT_SCOPE_REQUIREMENT = (
    "recorded standing launch authority can prepare necessary ObeliskSDK runtime "
    "windows; otherwise an exact current-turn operator approval is required; "
    "this status report grants no evidence, readiness, publication, or SDK progress"
)
APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER = "approved_runtime_evidence_missing"
IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER = "identity_public_contract_gate_missing"
PRIVATE_LOGOUT_CORRELATION_BLOCKER_ID = "private_logout_correlation_internal_blocker"
PRIVATE_LOGOUT_CORRELATION_FALSE_FLAGS = (
    "promotion_ready",
    "public_contract_allowed",
    "public_identity_ready",
    "public_lookup_allowed",
    "public_lookup_ready",
    "identity_exposure_allowed",
    "public_abi_ready",
    "public_header_allowed",
    "public_header_ready",
    "public_sdk_ready",
    "runtime_ready",
    "live_authorization_allowed",
    "live_ops_authorized",
    "server_operations_authorized",
    "workspace_writes_authorized",
    "runtime_capture_authorized",
    "reads_live_logs",
    "read_live_logs",
)
PRIVATE_LOGOUT_CORRELATION_REQUIRED_NON_CLAIMS = (
    "no public lookup",
    "no identity exposure",
    "no ABI/header readiness",
    "no live authorization",
)
OBJECT_IDENTITY_RESOURCE_HANDLE_STRICT_NEXT_BLOCKER = (
    "rejected runtime object samples plus runtime serial reuse/wraparound semantics "
    "under future approved live-ops brief"
)
OBJECT_IDENTITY_RESOURCE_HANDLE_FALSE_FLAGS = (
    "promotion_ready",
    "public_contract_allowed",
    "public_sdk_ready",
    "runtime_ready",
    "stable_claim_allowed",
    "public_abi_ready",
    "public_header_allowed",
    "public_header_ready",
    "public_lookup_allowed",
    "public_lookup_ready",
    "lookup_ready",
    "object_lookup_ready",
    "resource_lookup_ready",
    "mutation_ready",
    "object_mutation_ready",
    "public_mutation_ready",
    "object_identity_ready",
    "public_object_identity_ready",
    "public_object_lookup_ready",
    "resource_handle_ready",
    "public_resource_handle_ready",
    "post_callback_resource_handle_ready",
    "post_callback_handle_ready",
    "post_callback_validity_ready",
    "post_callback_object_validity_ready",
    "cross_event_identity_ready",
    "cross_event_object_identity_ready",
    "persistent_handle_ready",
    "persistent_identity_ready",
    "persistent_object_identity_ready",
    "serial_policy_ready",
    "serial_reuse_ready",
    "serial_wraparound_ready",
    "runtime_object_negative_samples_ready",
    "runtime_sample_ready",
    "offline_artifacts_unlock_public_lookup_identity_runtime_sdk",
    "live_ops_authorized",
    "server_operations_authorized",
    "workspace_writes_authorized",
    "runtime_capture_authorized",
    "reads_live_logs",
    "read_live_logs",
)
OBJECT_IDENTITY_RESOURCE_HANDLE_REQUIRED_NON_CLAIMS = (
    "no public ResourceHandle ABI",
    "no public object identity ABI",
    "no public object lookup ABI",
    "no mutation API",
    "no cross-event object identity",
    "no persistent object identity",
    "no post-callback object validity",
    "no runtime authorization",
)
POST_EVIDENCE_P0_LOCK_SIMULATION_SCHEMA = (
    "obelisk.command-permission-route-post-evidence-p0-lock-simulation.v1"
)
POST_EVIDENCE_P0_LOCK_FALSE_FLAGS = (
    "permissions_admin_unlocked",
    "command_response_unlocked",
    "commands_replies_unlocked",
    "promotion_ready",
    "public_sdk_ready",
    "public_abi_ready",
    "public_header_allowed",
    "runtime_ready",
    "public_lookup_ready",
    "public_header_ready",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_complete_sdk_claim_now",
    "counts_toward_p0_dependency_chain_claim_now",
    "public_or_runtime_accounting_allowed",
    "stable_claim_allowed",
    "authorizes_runtime_work",
    "authorizes_server_work",
    "authorizes_workspace_work",
    "authorizes_workspace_writes",
    "server_operations_authorized",
    "workspace_writes_authorized",
    "live_ops_authorized",
    "runtime_capture_authorized",
    "reads_live_logs",
    "read_live_logs",
)
POST_EVIDENCE_P0_LOCK_ZERO_FIELDS = (
    "claim_progress_contribution",
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_progress_contribution",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_progress_contribution",
    "progress",
)
POST_EVIDENCE_P0_CHILD_FALSE_FLAGS = (
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "public_or_runtime_accounting_allowed",
)
PACKAGE_SHAPE_FALSE_FLAGS = (
    "abi_layout_ready",
    "abi_layout_validated",
    "cmake_config_ready",
    "cmake_package_found",
    "cmake_package_succeeded",
    "cmake_targets_ready",
    "component_sdk_found",
    "components_sdk_ready",
    "components_sdk_found",
    "find_package_found",
    "find_package_succeeded",
    "installed_headers_ready",
    "installed_sdk_package_ready",
    "installed_sdk_release_ready",
    "obelisk_config_cmake_ready",
    "obelisk_targets_cmake_ready",
    "owner_token_registration_ready",
    "owner_token_sdk_consumer_ready",
    "package_available",
    "package_install_success",
    "package_install_succeeded",
    "package_publication_allowed",
    "package_publication_ready",
    "package_published",
    "package_shape_counts_toward_release",
    "package_shape_release_ready",
    "package_shape_ready",
    "package_shape_v1_completion_ready",
    "package_shape_counts_toward_completion",
    "package_shape_counts_toward_public_sdk",
    "package_shape_counts_toward_v1_completion",
    "plugin_hub_package_published",
    "plugin_hub_counts_toward_completion",
    "plugin_hub_counts_toward_public_sdk",
    "plugin_hub_counts_toward_v1_completion",
    "plugin_hub_seed_ready",
    "plugin_hub_support_tier_ready",
    "plugin_hub_publication_allowed",
    "plugin_hub_readiness_claim_allowed",
    "plugin_hub_seed_package_publication",
    "public_abi_available",
    "public_header_allowed",
    "public_header_available",
    "public_headers_available",
    "public_module_sdk_coverage_claim_allowed",
    "public_module_sdk_coverage_ready",
    "public_module_sdk_covered",
    "public_sdk_coverage_ready",
    "public_package_available",
    "public_package_published",
    "public_package_ready",
    "release_statement_ready",
    "release_statement_bookkeeping_counts_toward_completion",
    "release_statement_counts_toward_completion",
    "release_statement_outcomes_satisfy_completion",
    "release_package_allowed",
    "release_package_available",
    "release_package_published",
    "release_package_ready",
    "release_packaged",
    "sdk_package_available",
    "sdk_package_published",
    "sdk_package_ready",
    "scoped_release_statement_counts_toward_complete_sdk_claim",
    "scoped_release_statement_counts_toward_completion",
    "scoped_release_statement_outcomes_satisfy_completion",
    "scoped_release_statement_ready",
    "sdk_coverage_complete",
    "sdk_package_install_success",
    "sdk_package_install_succeeded",
    "stable_release_contract_claim_allowed",
    "struct_size_ready",
    "struct_size_validated",
    "runtime_live_op_approval_allowed",
    "runtime_readiness_claim_allowed",
    "support_tier_activation_allowed",
    "support_tier_activated",
    "support_tier_allowed",
    "support_tier_supported",
    "v1_completion_claim_allowed",
)
PACKAGE_SHAPE_ZERO_FIELDS = (
    "complete_sdk_blockers_promoted_for_claim_count",
    "complete_sdk_blockers_promoted_for_claim_ratio",
    "p0_chain_promoted_count",
    "p0_chain_promoted_ratio",
    "p0_dependency_chain_promoted_for_claim_count",
    "p0_dependency_chain_promoted_for_claim_ratio",
    "promoted_for_claim_count",
    "promoted_for_claim_ratio",
    "release_statement_complete_sdk_progress_contribution",
    "sdk_completion_progress_percent",
    "sdk_completion_progress_ratio",
    "scoped_release_statement_claim_progress_contribution",
    "scoped_release_statement_complete_sdk_progress_contribution",
)
DEFAULT_COMPLETE_SDK_BLOCKER_TOTAL = 12
DEFAULT_P0_DEPENDENCY_CHAIN_TOTAL = 4
PRINCIPAL_START_END_REQUIRED_TRUE_KEYS = (
    "ready",
    "accepted_for_contract_review",
    "principal_start_end_runtime_evidence_present",
    "principal_start_end_runtime_evidence_ready",
)
PRINCIPAL_START_END_REQUIRED_FALSE_KEYS = (
    "approved_runtime_evidence",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "counts_as_approved_runtime_evidence",
    "public_abi_ready",
    "public_api_ready",
    "public_header_allowed",
    "public_sdk_ready",
    "runtime_ready",
    "lookup_ready",
    "permissions_ready",
    "commands_ready",
    "v1_completion_ready",
    "stable_claim_allowed",
    "publication_authorized",
)
PRINCIPAL_START_END_OPTIONAL_FALSE_KEYS = (
    "approved_bundle_accepted",
    "approved_runtime_evidence_accepted",
    "complete_sdk_allowed",
    "complete_sdk_ready",
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
    "evidence_bundle_accepted",
    "module_ready",
    "module_sdk_ready",
    "promotion_ready",
    "public_contract_allowed",
    "public_header_ready",
    "ready_for_public_contract_review",
    "runtime_evidence_present",
    "runtime_evidence_ready",
    "sdk_evidence_ready",
    "stable_sdk_ready",
    "v1_complete",
    "v1_completion",
    "v1_release_ready",
)
PRINCIPAL_START_END_FALSE_KEYS = frozenset(
    (
        set(PRINCIPAL_START_END_REQUIRED_FALSE_KEYS)
        | set(PRINCIPAL_START_END_OPTIONAL_FALSE_KEYS)
        | set(FAIL_CLOSED_ACTION_FALSE_FLAGS)
    )
    - set(PRINCIPAL_START_END_REQUIRED_TRUE_KEYS)
)
PRINCIPAL_START_END_ZERO_KEYS = frozenset(
    FAIL_CLOSED_ACTION_ZERO_FIELDS
    + (
        "complete_sdk_claim_progress_contribution",
        "complete_sdk_progress_contribution",
        "p0_dependency_chain_claim_progress_contribution",
        "p0_dependency_chain_progress_contribution",
        "public_sdk_progress_contribution",
        "runtime_progress_contribution",
        "sdk_completion_credit",
        "sdk_progress_contribution",
        "v1_completion_contribution",
    )
)
SIDE_LANE_SOURCE_ALIASES: dict[str, tuple[str, ...]] = {
    "transfer_scriptstruct": (
        "transfer_scriptstruct_readiness",
        "transfer_scriptstruct_readiness_report",
        "transfer_scriptstruct",
    ),
    "buff_status": (
        "buff_status_readiness",
        "buff_status_readiness_report",
        "buff_status",
    ),
    "dino_scalar": (
        "dino_scalar_readiness",
        "dino_scalar_readiness_report",
        "dino_policy_scalar_readiness",
        "dino_scalar",
    ),
    "mission_transfer_dino_tribe_buff_accounting": (
        "mission_transfer_dino_tribe_outcome_accounting",
        "mission_transfer_dino_tribe_buff_accounting",
        "mission_transfer_dino_tribe_accounting",
    ),
}
SIDE_LANE_LABELS: dict[str, str] = {
    "transfer_scriptstruct": "Transfer ScriptStruct",
    "buff_status": "Buff status manifest/source binding",
    "dino_scalar": "Dino scalar",
    "mission_transfer_dino_tribe_buff_accounting": (
        "Mission/Transfer/Dino/Tribe/Buff accounting"
    ),
}
SIDE_LANE_CONTAINER_KEYS = (
    "side_lanes",
    "non_claim_side_lanes",
    "side_lane_summaries",
    "v1_sdk_report_sections",
)
SIDE_LANE_FALSE_FLAGS = (
    "authorizes_runtime_work",
    "authorizes_server_work",
    "authorizes_server_operations",
    "server_operations_authorized",
    "runtime_work_authorized",
    "authorizes_workspace_work",
    "authorizes_workspace_writes",
    "workspace_writes_authorized",
    "live_ops_authorized",
    "marker_env_changes_authorized",
    "publication_authorized",
    "runtime_capture_authorized",
    "reads_live_logs",
    "read_live_logs",
    "approved_runtime_evidence",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "counts_as_approved_runtime_evidence",
    "counts_as_passive_evidence",
    "counts_as_passive_snapshot_evidence",
    "counts_as_runtime_evidence",
    "counts_as_sdk_evidence",
    "counts_toward_sdk",
    "counts_toward_p0_dependency_chain",
    "runtime_evidence_present",
    "runtime_evidence_ready",
    "sdk_evidence_ready",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "public_or_runtime_accounting_allowed",
    "readiness_counts_toward_v1_accounting",
    "complete_sdk_ready",
    "complete_sdk_claim_allowed",
    "p0_dependency_chain_accounted",
    "p0_accounting_counts_as_promoted_surface",
    "sdk_accounting_counts_as_completed_surface",
    "p0_dependency_chain_ready",
    "module_ready",
    "module_sdk_ready",
    "dino_sdk_ready",
    "mission_sdk_ready",
    "transfer_sdk_ready",
    "tribe_sdk_ready",
    "buff_sdk_ready",
    "buff_status_sdk_ready",
    "public_sdk_ready",
    "public_abi_ready",
    "public_api_ready",
    "public_header_allowed",
    "public_header_ready",
    "public_module_ready",
    "public_module_sdk_ready",
    "public_dino_sdk_ready",
    "public_mission_sdk_ready",
    "public_transfer_sdk_ready",
    "public_tribe_sdk_ready",
    "public_buff_sdk_ready",
    "public_buff_status_sdk_ready",
    "runtime_ready",
    "runtime_validated",
    "runtime_hook_ready",
    "runtime_wiring_ready",
    "stable_claim_allowed",
    "promotion_ready",
    "activation_preconditions_met",
    "request_pack_ready",
    "route_ready",
    "blocker_resolved",
    "route_blocker_resolved",
    "side_lane_promoted",
    "structure_build_policy_ready",
    "active_notice_ready",
    "active_notice_sent",
    "active_notice_accepted",
    "active_notice_updated",
    "v1_accounted",
    "v1_completion",
    "v1_completion_ready",
    "identity_ready",
    "lookup_ready",
    "mutation_ready",
    "return_override_ready",
    "resource_handle_ready",
)
SIDE_LANE_ZERO_FIELDS = (
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_claim_progress_percent",
    "complete_sdk_claim_progress_ratio",
    "credit",
    "credits",
    "claim_count",
    "claim_credit",
    "claim_credits",
    "completion_count",
    "complete_sdk_progress_contribution",
    "complete_sdk_progress_percent",
    "complete_sdk_progress_ratio",
    "complete_sdk_credit",
    "complete_sdk_credits",
    "complete_sdk_claim_credit",
    "complete_sdk_claim_credits",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_claim_progress_percent",
    "p0_dependency_chain_claim_progress_ratio",
    "p0_dependency_chain_credit",
    "p0_dependency_chain_credits",
    "p0_dependency_chain_progress_contribution",
    "p0_dependency_chain_progress_percent",
    "p0_dependency_chain_progress_ratio",
    "p0_dependency_progress_contribution",
    "p0_credit",
    "p0_credits",
    "promoted_count",
    "public_sdk_progress_contribution",
    "public_transfer_sdk_progress_contribution",
    "runtime_progress_contribution",
    "sdk_credit",
    "sdk_credits",
    "sdk_completion_credit",
    "sdk_completion_credits",
    "v1_completion_contribution",
    "v1_completion_credit",
    "v1_completion_credits",
    "progress",
)
MULTI_SURFACE_BETA_CAPTURE_PACK_REQUIRED_FALSE_KEYS = (
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
    "side_lane_counts_toward_sdk",
    "side_lane_counts_toward_p0",
    "runtime_ready",
    "public_sdk_ready",
    "stable_sdk_ready",
    "plugin_hub_ready",
    "publication_ready",
)
MULTI_SURFACE_BETA_CAPTURE_PACK_OPTIONAL_FALSE_KEYS = (
    "approved_runtime_evidence",
    "approved_runtime_evidence_accepted",
    "counts_as_sdk_evidence",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "public_abi_ready",
    "public_header_allowed",
    "runtime_evidence_present",
    "runtime_evidence_ready",
    "stable_claim_allowed",
    "v1_completion_ready",
)
MULTI_SURFACE_BETA_CAPTURE_PACK_FALSE_KEYS = frozenset(
    (
        set(MULTI_SURFACE_BETA_CAPTURE_PACK_REQUIRED_FALSE_KEYS)
        | set(MULTI_SURFACE_BETA_CAPTURE_PACK_OPTIONAL_FALSE_KEYS)
        | set(FAIL_CLOSED_ACTION_FALSE_FLAGS)
        | set(SIDE_LANE_FALSE_FLAGS)
    )
    - {"ready", "candidate_only"}
)
MULTI_SURFACE_BETA_CAPTURE_PACK_ZERO_KEYS = frozenset(
    set(FAIL_CLOSED_ACTION_ZERO_FIELDS)
    | set(SIDE_LANE_ZERO_FIELDS)
    | {
        "complete_sdk_claim_progress_contribution",
        "complete_sdk_progress_contribution",
        "p0_dependency_chain_claim_progress_contribution",
        "p0_dependency_chain_progress_contribution",
        "public_sdk_progress_contribution",
        "runtime_progress_contribution",
        "sdk_progress_contribution",
        "v1_completion_contribution",
    }
)
RUNTIME_EVIDENCE_STATUS_FALSE_KEYS = frozenset(
    (
        set(FAIL_CLOSED_ACTION_FALSE_FLAGS)
        | {
            "approved_runtime_evidence_accepted_by_checker",
            "authorized_by_this_report",
            "grants_readiness_claims",
            "marker_env_changes_authorized",
            "promotion_ready",
            "server_operations_authorized_by_this_report",
            "runtime_work_authorized_by_this_report",
            "workspace_writes_authorized_by_this_report",
            "marker_env_changes_authorized_by_this_report",
            "discord_authorized_by_this_report",
            "publication_authorized_by_this_report",
        }
    )
)
RUNTIME_EVIDENCE_STATUS_ZERO_KEYS = frozenset(
    set(FAIL_CLOSED_ACTION_ZERO_FIELDS)
    | {
        "complete_sdk_claim_progress_contribution",
        "p0_dependency_chain_claim_progress_contribution",
        "sdk_completion_count",
        "sdk_claim_count",
        "v1_completion_contribution",
    }
)
NON_COUNTING_CONTEXT_MARKER_RE = re.compile(
    r"(?:"
    r"object_?identity(?:_?resource_?handle)?(?:_?(?:readiness|status|blocker|report))?|"
    r"resource_?handle(?:_?(?:readiness|status|blocker|report|aliases?))?|"
    r"object_?lookup|resource_?lookup|"
    r"post_?callback(?:_?(?:handle|validity|object|resource_?handle))?|"
    r"cross_?event(?:_?object)?_?identity|"
    r"persistent(?:_?object)?_?identity|persistent_?handle|"
    r"object_?mutation|"
    r"(?:player_?)?notice(?:_?(?:action|bundle|dry_run|sent|accepted))?|"
    r"active_?notice(?:_?(?:action|accepted|ready|report|sent|status|updated?))?|"
    r"confirmed_?(?:beta_?)?notice(?:_?(?:report|reports|sent|status|attestation|confirmation|confirmed))?|"
    r"beta_?notice(?:_?(?:prep|send|sent|attestation|confirmed))?|"
    r"(?:discord_?)?beta_?bridge(?:_?(?:bot_?)?notice|_?config|_?events?|_?plans?|_?reports?|_?status)?|"
    r"(?:discord_?beta_?bridge_?)?bot_?notice(?:_?(?:report|status|workflow))?|"
    r"(?:discord_?bot_?)?tester_?(?:status_?)?workflow(?:_?(?:report|status|summary))?|"
    r"beta_?tester_?(?:status_?)?workflow(?:_?(?:report|status|summary))?|"
    r"active_?notice_?update_?policy|editable_?notice_?workflow|"
    r"discord_?notice|"
    r"passive(?:_?(?:snapshot|observation|activity|latest|capture|triplet|monitor|monitors?))?|"
    r"(?:active_?)?passive_?monitors?(?:_?(?:session|status|summary|snapshot|tick|ticks))?|"
    r"active_?monitors?(?:_?(?:session|status|summary|snapshot|tick|ticks))?|"
    r"diagnostic(?:_?(?:only|summary|triage|observer))?|"
    r"(?:native_?u?function_?)?static_?registration(?:_?(?:orientation|discovery|report|status|summary))?|"
    r"(?:radare2_?)?static_?orientation(?:_?(?:windows?|report|status|summary))?|"
    r"static_?lifecycle_?orientation(?:_?(?:check|report|status|summary))?|"
    r"registration_?orientation(?:_?(?:report|status|summary))?|"
    r"(?:player_?principal_?)?lifecycle_?(?:event|events|role|roles|triplet|proof|"
    r"artifact|evidence|observer|status|report|summary|partial|candidate|diagnostic|observed)(?:_?(?:artifact|evidence|proof|ready|status|summary|observed))*|"
    r"(?:partial_?)?(?:role|event)_?triplet(?:_?(?:artifact|evidence|proof|ready|status|summary))?|"
    r"(?:partial_?)?lifecycle_?(?:event|role)s?(?:_?(?:artifact|evidence|proof|ready|status|summary|observed))?|"
    r"(?:session_?start|session_?end|handle_?new_?player|on_?logout)(?:_?(?:observed|proof|ready|status|artifact|evidence))?|"
    r"(?:session_?start(?:_?and)?_?end|start_?end)(?:_?only)?_?evidence|"
    r"check_?join_?in_?progress(?:_?(?:diagnostic|offline|candidate(?:_?only)?|accept(?:ed|ance)|readiness|report|status|evidence|artifacts?|summary|source))*|"
    r"(?:session_?start_?rejected|rejected_?session_?start)(?:_?(?:diagnostic|offline|candidate(?:_?only)?|accept(?:ed|ance)|readiness|report|status|evidence|artifacts?|summary|source|check_?join_?in_?progress))+|"
    r"(?:diagnostic|offline|candidate(?:_?only)?)(?:_?(?:check_?join_?in_?progress|session_?start_?rejected|rejected_?session_?start)(?:_?(?:accept(?:ed|ance)|readiness|report|status|evidence|artifacts?|summary|source))?)+|"
    r"observer_?event_?triage|"
    r"(?:delegated_?)?handoff(?:_?(?:checkpoint|context|docs?|report|summary))?|"
    r"delegated_?(?:agent|artifact|metadata|report|route_?gate|summary|task|worker)(?:_?(?:artifact|metadata|report|reports|status|summary|summaries))?|"
    r"closed_?(?:agent|worker)(?:_?(?:notes?|report|reports|status|summary|summaries))?|"
    r"player_?principal_?passive_?snapshot|"
    r"activation_?preconditions?|"
    r"pre_?activation(?:_?(?:consistency|report|status|readiness|ready))?|"
    r"(?:runtime_?window_?|evidence_?|approved_?runtime_?)closure(?:_?(?:artifact|artifacts|bundle|bundles|request|requests|report|reports|output|outputs|summary|summaries|status|execution|executor))?|"
    r"closure_?(?:artifact|artifacts|bundle|bundles|request|requests|report|reports|output|outputs|summary|summaries|status|execution|executor)|"
    r"(?:runtime_?window_?)?(?:planner|executor)(?:_?(?:artifact|output|report|status))?|"
    r"request_?(?:pack|check|artifact|preflight|readiness)|"
    r"(?:fastest_?)?next_?sdk_?unblock(?:_?(?:summary|report))?|"
    r"next_?action_?sequence|"
    r"action(?:able)?_?paths?|action_?path(?:_?(?:candidate|summary|report|status))?|"
    r"(?:approved_?)?(?:runtime_?)?bundle_?requests?|"
    r"approved_?runtime_?manifests?|"
    r"accepted_?artifact_?class(?:_?(?:artifact|artifacts|metadata|report|reports|status))?|"
    r"binding_?required(?:_?(?:artifact|artifacts|metadata|report|reports|status))?|"
    r"public_?reachability(?:_?(?:check|ready|report))?|"
    r"(?:reviewed_?)?(?:identity_?)?public_?contract(?:_?(?:artifact|decision|decisions|input|readiness|ready|record|records|report|review))?|"
    r"contract_?review(?:_?(?:artifact|decision|decisions|input|readiness|ready|record|records|report))?|"
    r"(?:reviewed_?)?decision_?record(?:_?(?:artifact|draft|metadata|report|skeleton|status|summary|template))?|"
    r"(?:offline_?)?hardening(?:_?(?:artifact|metadata|report|status|summary))?|"
    r"(?:route_?bound_?)?identity_?source(?:_?(?:forward|forwarded|forwarding|readiness|report))?|"
    r"window_?request_?check|"
    r"player_?principal_?lifecycle_?window_?request|"
    r"runtime_?window(?:_?(?:activation|executor|execution|manifest|plan|planner|preflight|prepar(?:ed|ation)?|readiness|ready|request|status))?|"
    r"runtime_?window_?command(?:_?(?:plan|plans|sequence|sequences|report|reports|status))?|"
    r"(?:runtime_?evidence_?|player_?principal_?lifecycle_?)?evidence_?command_?sequence(?:_?(?:plan|report|status))?|"
    r"strict_?(?:lifecycle_?|triplet_?)?selector(?:_?(?:command|result|report|status|summary))?|"
    r"strict_?lifecycle_?triplet_?selector(?:_?(?:command|result|report|status|summary))?|"
    r"runtime_?evidence_?contract_?review_?currentness(?:_?(?:diagnostic|report|status|summary))?|"
    r"(?:identity_?)?public_?contract_?currentness(?:_?(?:diagnostic|report|status|summary))?|"
    r"runtime_?contract_?currentness(?:_?(?:diagnostic|report|status|summary))?|"
    r"(?:reviewed_?)?decision_?record(?:_?(?:artifact|draft|metadata|report|skeleton|status|summary|template))?|"
    r"(?:player_?identity|permissions?_admin|command_?chat_?response(?:_?path)?|"
    r"commands?_?replies)?_?promotion_?certificate(?:_?(?:build|builder|generation))?_?"
    r"(?:artifact|binding|certificate|output|report|status|summary)?|"
    r"promotion_?certificate(?:_?(?:build|builder|generation))?_?"
    r"(?:artifact|binding|certificate|output|report|status|summary)?|"
    r"(?:generated_?)?(?:promotion_?)?cert(?:ificate)?"
    r"(?:_?(?:artifact|binding|build|builder|generation|metadata|output|report|status|summary))?|"
    r"certificate_?binding(?:_?(?:valid|status|report|summary))?|"
    r"output_?certificate(?:_?(?:path|sha256|status|report|summary))?|"
    r"standing_?(?:launch_?)?authority|"
    r"install(?:ed)?_?runtime(?:_?(?:checks?|ok|ready|reports?|status))?|"
    r"runtime_?install(?:ed)?(?:_?(?:checks?|ok|ready|reports?|status))?|"
    r"broadcasts?(?:_?(?:checks?|ok|reports?|sent|status|notices?))?|"
    r"rcon(?:_?(?:checks?|commands?|counts?|player_?counts?|ok|ready|reachable|reports?|service|status))?|"
    r"(?:public_?|installed_?)?headers?|"
    r"(?:public_?)?obelisk_?api_?headers?|"
    r"obeliskapi|obelisk_?api_?h|"
    r"cmake_?(?:package|config)|"
    r"obelisk_?config(?:_?cmake)?|obelisk_?targets(?:_?cmake)?|"
    r"components?_?sdk|"
    r"(?:installed_?)?sdk_?consumer_?tests?|"
    r"tests_?sdk_?(?:installed_?)?consumer|"
    r"route_?planning(?:_?(?:report|readiness|snapshot|status|simulation))?|"
    r"planning_?route(?:_?(?:report|readiness|snapshot|status|simulation))?|"
    r"route_?(?:simulation|lock_?simulation|check_?readiness|readiness|snapshot|snapshots|snapshot_?report|status_?snapshot)|"
    r"status_?(?:snapshot|artifact|report)|"
    r"copied_?logs?_?only(?:_?(?:artifact|artifacts|report|reports|status))?|"
    r"post_?evidence_?identity_?lock|"
    r"identity_?lock(?:_?(?:simulation|readiness|report))?|"
    r"(?:multi_?surface_?)?beta_?capture(?:_?(?:candidate_?pack|candidates?|checker_?matrix|capture_?pack|capture_?plan|intake|non_?claim_?manifest|pack|plan|queue|readiness|report|reports|runbook|session|sessions|status|surface|surfaces))?|"
    r"multi_?surface_?beta_?packs?(?:_?(?:check|metadata|report|status))?|"
    r"multi_?surface(?:_?beta)?(?:_?(?:capture|candidate|candidates|intake|pack|packs|plan|plans|queue|queues|surface|surfaces))(?:_?(?:capture|candidate|candidates|intake|pack|packs|plan|plans|queue|queues|readiness|report|reports|session|sessions|status))?|"
    r"(?:offline_?)?candidate_?(?:capture_?)?(?:pack|packs|queue|queues)(?:_?(?:check|evidence|integrity|manifest|metadata|readiness|report|status|summary))?|"
    r"transfer_?(?:script_?struct|baccept)_?readiness|"
    r"buff_?status_?readiness|"
    r"dino_?scalar_?readiness|"
    r"tribe_?scalar_?boundary_?readiness|"
    r"scalar_?boundary_?readiness|"
    r"mission_?transfer_?dino_?tribe(?:_?buff)?_?accounting|"
    r"structure_?build_?policy(?:_?offline_?intake)?(?:_?(?:check|evidence|metadata|report|status))?|"
    r"side_?lane|"
    r"(?:installed_?)?sdk_?package(?:_?shape)?|"
    r"(?:sdk_?)?package_?(?:exact|non_?exact)(?:_?(?:check|evidence|install|report|status))?|"
    r"(?:install|installed|package)_?(?:sdk_?)?(?:package|shape|check|evidence|layout|success|succeed(?:ed)?|install|installed)(?:_?(?:checks?|ok|ready|reports?|status|success|succeed(?:ed)?|found))?|"
    r"find_?package(?:_?(?:obelisk|sdk|components?|success|succeed(?:ed)?|found|ready|reports?|status))?|"
    r"component_?sdk(?:_?(?:check|found|ready|reports?|status|success|succeed(?:ed)?))?|"
    r"(?:public_?debug|debug_?public)_?boundary(?:_?(?:fix|fixes|metadata|report|status|summary))?|"
    r"(?:public|release)_?package|"
    r"package_?shape(?:_?evidence)?|"
    r"install(?:ed)?_?sdk(?:_?(?:package|package_?shape|evidence|layout))?|"
    r"install_?evidence|"
    r"plugin_?hub(?:_?seed)?|"
    r"support_?tier|"
    r"scoped_?non_?complete(?:_?only)?|"
    r"scoped_?(?:non_?complete_?)?(?:v1_?)?release_?statements?|"
    r"release_?statement(?:_?bookkeeping)?|"
    r"(?:route_?gate_?)?post_?evidence_?p0_?lock_?simulation|"
    r"simulation_?only"
    r")",
    re.IGNORECASE,
)
NON_PUBLIC_CHECKJOIN_REJECTED_OFFLINE_ACCEPTANCE_RE = re.compile(
    r"(?:"
    r"check_?join_?in_?progress(?:_?(?:diagnostic|offline|candidate(?:_?only)?|non_?evidence|accept(?:ed|ance)|readiness|report|status|evidence|artifacts?|summary|source))+|"
    r"(?:session_?start_?rejected|rejected_?session_?start)(?:_?(?:diagnostic|offline|candidate(?:_?only)?|non_?evidence|accept(?:ed|ance)|readiness|report|status|evidence|artifacts?|summary|source|check_?join_?in_?progress))+|"
    r"(?:diagnostic|offline|candidate(?:_?only)?|non_?evidence)(?:_?(?:check_?join_?in_?progress|session_?start_?rejected|rejected_?session_?start)(?:_?(?:accept(?:ed|ance)|readiness|report|status|evidence|artifacts?|summary|source))?)+"
    r")",
    re.IGNORECASE,
)
NON_APPROVED_RUNTIME_EVIDENCE_SOURCE_RE = re.compile(
    r"(?:"
    r"active_?players?(?:_?(?:presence|detected|present|summary|status|snapshot))?|"
    r"players?_?presence(?:_?(?:active|detected|summary|status|snapshot))?|"
    r"observer_?only|no_?accepted(?:_?lifecycle)?(?:_?events?)?|"
    r"diagnostic(?:_?fname)?_?drift|fname_?drift|drift_?manifest|"
    r"diagnostic_?(?:compact_?)?(?:blocker_?)?chain(?:_?(?:metadata|report|status))?|"
    r"compact_?blocker_?chain(?:_?(?:diagnostic|metadata|report|status))?|"
    r"source_?bound(?:_?drift)?(?:_?(?:manifest|report|status|summary|source))?|"
    r"source_?binding_?drift(?:_?(?:manifest|report|status|summary))?|"
    r"(?:offline_?)?hardening(?:_?(?:artifact|metadata|report|status|summary))?|"
    r"(?:native_?u?function_?)?static_?registration(?:_?(?:orientation|discovery|report|status|summary))?|"
    r"(?:radare2_?)?static_?orientation(?:_?(?:windows?|report|status|summary))?|"
    r"static_?lifecycle_?orientation(?:_?(?:check|report|status|summary))?|"
    r"registration_?orientation(?:_?(?:report|status|summary))?|"
    r"(?:player_?|active_?|confirmed_?)?beta_?notice(?:_?(?:report|send|sent|status|attestation|confirmation|confirmed|active))?|"
    r"active_?notice(?:_?(?:action|accepted|ready|report|sent|status|updated?))?|"
    r"(?:discord_?beta_?bridge_?)?bot_?notice(?:_?(?:report|status|workflow))?|"
    r"(?:discord_?bot_?)?tester_?(?:status_?)?workflow(?:_?(?:report|status|summary))?|"
    r"beta_?tester_?(?:status_?)?workflow(?:_?(?:report|status|summary))?|"
    r"active_?notice_?update_?policy|editable_?notice_?workflow|"
    r"player_?notice(?:_?(?:action|bundle|dry_?run|report|sent|status|accepted))?|"
    r"discord(?:_?beta_?bridge)?(?:_?(?:config|readiness|report|status))?|"
    r"(?:candidate_?|future_?)?multi_?surface(?:_?beta_?capture)?"
    r"(?:_?(?:candidate_?queue|checker_?matrix|capture_?pack|capture_?plan|"
    r"non_?claim_?manifest|pack|plan|queue|runbook|manifest|status|report))?|"
    r"beta_?capture(?:_?(?:candidate_?pack|candidate_?queue|pack|plan|queue))?|"
    r"(?:offline_?)?candidate_?(?:capture_?)?(?:pack|packs|queue|queues)(?:_?(?:check|evidence|integrity|manifest|metadata|readiness|report|status|summary))?|"
    r"transfer_?(?:script_?struct|baccept)_?readiness|"
    r"buff_?status_?readiness|"
    r"dino_?scalar_?readiness|"
    r"mission_?transfer_?dino_?tribe(?:_?buff)?_?accounting|"
    r"structure_?build_?policy(?:_?offline_?intake)?(?:_?(?:check|evidence|metadata|report|status))?|"
    r"side_?lane(?:_?(?:candidate|metadata|report|status))?|"
    r"runtime_?window_?command(?:_?(?:plan|plans|sequence|sequences|report|reports|status))?|"
    r"(?:runtime_?evidence_?|player_?principal_?lifecycle_?)?evidence_?command_?sequence(?:_?(?:plan|report|status))?|"
    r"strict_?(?:lifecycle_?|triplet_?)?selector(?:_?(?:command|result|report|status|summary))?|"
    r"strict_?lifecycle_?triplet_?selector(?:_?(?:command|result|report|status|summary))?|"
    r"runtime_?evidence_?contract_?review_?currentness(?:_?(?:diagnostic|report|status|summary))?|"
    r"(?:identity_?)?public_?contract_?currentness(?:_?(?:diagnostic|report|status|summary))?|"
    r"runtime_?contract_?currentness(?:_?(?:diagnostic|report|status|summary))?|"
    r"(?:player_?identity|permissions?_admin|command_?chat_?response(?:_?path)?|"
    r"commands?_?replies)?_?promotion_?certificate(?:_?(?:build|builder|generation))?_?"
    r"(?:artifact|binding|certificate|output|report|status|summary)?|"
    r"promotion_?certificate(?:_?(?:build|builder|generation))?_?"
    r"(?:artifact|binding|certificate|output|report|status|summary)?|"
    r"(?:generated_?)?(?:promotion_?)?cert(?:ificate)?"
    r"(?:_?(?:artifact|binding|build|builder|generation|metadata|output|report|status|summary))?|"
    r"certificate_?binding(?:_?(?:valid|status|report|summary))?|"
    r"output_?certificate(?:_?(?:path|sha256|status|report|summary))?|"
    r"(?:installed_?)?sdk_?package(?:_?shape)?|"
    r"(?:sdk_?)?package_?(?:exact|non_?exact)(?:_?(?:check|evidence|install|report|status))?|"
    r"package_?shape(?:_?(?:evidence|install|metadata|report|status))?|"
    r"(?:public_?debug|debug_?public)_?boundary(?:_?(?:fix|fixes|metadata|report|status|summary))?|"
    r"install(?:ed)?_?sdk(?:_?(?:package|package_?shape|evidence|layout))?"
    r")",
    re.IGNORECASE,
)
APPROVED_RUNTIME_EVIDENCE_SOURCE_MARKER_KEYS = {
    "artifact_scope",
    "artifact_type",
    "classification",
    "evidence_classification",
    "evidence_kind",
    "evidence_source",
    "evidence_source_kind",
    "path_type",
    "readiness_classification",
    "readiness_scope",
    "ready_scope",
    "schema",
    "source",
    "source_kind",
    "source_marker",
    "source_markers",
    "source_provenance",
    "source_status",
    "source_type",
    "status",
    "summary_classification",
    "target_set",
    "type",
}
PARTIAL_LIFECYCLE_SHORTCUT_MARKERS = (
    "partial_lifecycle",
    "partial_role_triplet",
    "partial_event_triplet",
    "lifecycle_event_proof",
    "lifecycle_role_proof",
    "lifecycle_roles_observed",
    "session_start_observed",
    "session_end_observed",
)
APPROVED_RUNTIME_ACCEPTED_COUNT_KEYS = (
    "accepted_count",
    "accepted_event_count",
    "accepted_lifecycle_event_count",
    "observed_lifecycle_event_count",
)
APPROVED_RUNTIME_ACCEPTED_LIST_KEYS = (
    "accepted_events",
    "accepted_lifecycle_events",
    "observed_event_cases",
    "observed_lifecycle_event_cases",
)
NON_COUNTING_FALSE_ALIAS_KEYS = set(FAIL_CLOSED_ACTION_FALSE_FLAGS) | set(SIDE_LANE_FALSE_FLAGS) | set(
    POST_EVIDENCE_P0_LOCK_FALSE_FLAGS
) | set(POST_EVIDENCE_P0_CHILD_FALSE_FLAGS) | set(PACKAGE_SHAPE_FALSE_FLAGS) | set(
    OBJECT_IDENTITY_RESOURCE_HANDLE_FALSE_FLAGS
) | {
    "certificate_binding_valid",
    "identity_surface_certificate_binding_valid",
    "output_certificate_valid",
    "promotion_certificate_valid",
    "promotion_certificate_hash_bound",
    "promotion_certificate_accepted",
    "promotion_certificate_promoted",
}
NON_COUNTING_GLOBAL_FALSE_ALIAS_KEYS = NOTICE_OR_BUNDLE_NON_PROGRESS_FALSE_ALIAS_KEYS | {
    "approved_runtime_evidence",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "counts_as_approved_runtime_evidence",
    "counts_as_runtime_evidence",
    "counts_as_sdk_evidence",
    "counts_toward_sdk",
    "counts_toward_p0_dependency_chain",
    "counts_toward_complete_sdk_claim_now",
    "counts_toward_p0_dependency_chain_claim_now",
    "passive_snapshot_evidence_allowed",
    "passive_snapshot_counts_as_evidence",
    "passive_snapshot_counts_as_runtime_evidence",
    "passive_snapshot_counts_as_sdk_evidence",
    "runtime_evidence_present",
    "runtime_evidence_ready",
    "runtime_window_authorized",
    "runtime_window_activation_ready_under_recorded_standing_launch_authority",
    "runtime_window_preparation_counts_as_approved_runtime_evidence",
    "runtime_window_preparation_counts_as_runtime_evidence",
    "runtime_window_preparation_counts_toward_sdk",
    "runtime_window_preparation_counts_toward_p0_dependency_chain",
    "runtime_window_preparation_counts_toward_complete_sdk_claim",
    "clears_approved_runtime_evidence_missing",
    "approved_runtime_evidence_missing_cleared",
    "blocker_cleared",
    "blocker_resolved",
    "current_route_blocker_cleared",
    "current_route_blocker_resolved",
    "remaining_route_blockers_cleared",
    "remaining_route_blockers_resolved",
    "route_blocker_cleared",
    "route_blocker_resolved",
    "route_lock_cleared",
    "route_lock_resolved",
    "sdk_route_blocker_cleared",
    "sdk_route_blocker_resolved",
    "side_lane_promoted",
    "structure_build_policy_ready",
    "active_notice_ready",
    "active_notice_sent",
    "active_notice_accepted",
    "active_notice_updated",
    "active_notice_counts_toward_sdk",
    "active_notice_counts_toward_p0_dependency_chain",
    "active_notice_counts_toward_complete_sdk_claim",
    "sdk_evidence_ready",
    "standing_launch_authority_counts_as_approved_runtime_evidence",
    "standing_launch_authority_counts_as_runtime_evidence",
    "standing_launch_authority_counts_toward_sdk",
    "standing_launch_authority_counts_toward_p0_dependency_chain",
    "standing_launch_authority_counts_toward_complete_sdk_claim",
    "standing_authority_counts_as_approved_runtime_evidence",
    "standing_authority_counts_as_runtime_evidence",
    "standing_authority_counts_toward_sdk",
    "standing_authority_counts_toward_p0_dependency_chain",
    "standing_authority_counts_toward_complete_sdk_claim",
}
NON_COUNTING_ZERO_ALIAS_KEYS = (
    set(FAIL_CLOSED_ACTION_ZERO_FIELDS)
    | set(SIDE_LANE_ZERO_FIELDS)
    | set(POST_EVIDENCE_P0_LOCK_ZERO_FIELDS)
    | set(PACKAGE_SHAPE_ZERO_FIELDS)
)
NON_COUNTING_CONTEXT_READY_ALIAS_KEYS = {
    "ready",
    "accepted_for_contract_review",
    "activation_preconditions_met",
    "activation_ready",
    "abi_layout_ready",
    "abi_layout_validated",
    "approved_runtime_manifest_present",
    "approved_runtime_manifest_referenced",
    "candidate_ready",
    "cmake_config_ready",
    "cmake_package_ready",
    "cmake_package_support_tier_ready",
    "cmake_package_v1_completion_ready",
    "cmake_targets_ready",
    "closed",
    "closure_accepted",
    "closure_complete",
    "closure_ready",
    "complete",
    "complete_triplet_ready",
    "components_sdk_ready",
    "confirmed",
    "counts_as_approved_runtime_evidence",
    "counts_as_passive_evidence",
    "counts_as_passive_snapshot_evidence",
    "counts_as_runtime_evidence",
    "counts_as_sdk_evidence",
    "declared_support_tier",
    "declared_support_tiers",
    "delivered",
    "delivery_confirmed",
    "evidence_closure_accepted",
    "evidence_closure_complete",
    "evidence_closure_ready",
    "headers_count_toward_complete_sdk_claim",
    "identity_lock_ready",
    "contract_review_artifact_ready",
    "contract_review_ready",
    "installed_headers_ready",
    "installed_sdk_consumer_tests_ready",
    "installed_sdk_consumer_tests_v1_completion_ready",
    "installed_sdk_package_ready",
    "installed_sdk_release_ready",
    "module_ready",
    "module_sdk_ready",
    "obelisk_config_cmake_ready",
    "obelisk_targets_cmake_ready",
    "owner_token_registration_ready",
    "owner_token_sdk_consumer_ready",
    "package_available",
    "package_publication_allowed",
    "package_publication_ready",
    "package_published",
    "package_shape_counts_toward_release",
    "package_shape_release_ready",
    "package_shape_ready",
    "package_shape_v1_completion_ready",
    "package_shape_counts_toward_completion",
    "package_shape_counts_toward_public_sdk",
    "package_shape_counts_toward_v1_completion",
    "passive_triplet_ready",
    "passive_snapshot_counts_as_evidence",
    "passive_snapshot_counts_as_runtime_evidence",
    "passive_snapshot_counts_as_sdk_evidence",
    "preconditions_met",
    "precondition_ready",
    "runtime_window_activation_ready_under_recorded_standing_launch_authority",
    "runtime_window_closure_accepted",
    "runtime_window_closure_complete",
    "runtime_window_closure_ready",
    "runtime_window_preparation_ready",
    "runtime_window_prepared",
    "runtime_window_ready",
    "plugin_hub_publication_allowed",
    "plugin_hub_publication_ready",
    "plugin_hub_counts_toward_completion",
    "plugin_hub_counts_toward_public_sdk",
    "plugin_hub_counts_toward_v1_completion",
    "plugin_hub_readiness_claim_allowed",
    "plugin_hub_ready",
    "plugin_hub_package_published",
    "plugin_hub_seed_ready",
    "plugin_hub_seed_package_publication",
    "plugin_hub_support_tier_ready",
    "public_abi_available",
    "public_contract_allowed",
    "public_contract_artifact_ready",
    "public_contract_ready",
    "public_contract_review_ready",
    "public_header_allowed",
    "public_header_available",
    "public_header_ready",
    "public_headers_available",
    "public_headers_ready",
    "public_module_ready",
    "public_module_sdk_ready",
    "public_module_sdk_coverage_claim_allowed",
    "public_module_sdk_coverage_ready",
    "public_module_sdk_covered",
    "public_package_available",
    "public_package_published",
    "public_package_ready",
    "public_sdk_coverage_ready",
    "public_readiness_ready",
    "readiness_ready",
    "reviewed_public_contract",
    "reviewed_public_contract_ready",
    "request_check_ready",
    "request_pack_ready",
    "approved_bundle_request_ready",
    "approved_runtime_bundle_request_ready",
    "public_reachability_ready",
    "public_reachability_counts_as_evidence",
    "public_reachability_counts_as_runtime_evidence",
    "public_reachability_counts_as_sdk_evidence",
    "public_reachability_counts_toward_runtime_evidence",
    "public_reachability_counts_toward_sdk_evidence",
    "route_bound_identity_source_forwarding_ready",
    "identity_source_forwarding_ready",
    "release_package_allowed",
    "release_package_available",
    "release_package_published",
    "release_package_ready",
    "release_packaged",
    "release_statement_bookkeeping_counts_toward_completion",
    "release_statement_counts_toward_completion",
    "release_statement_outcomes_satisfy_completion",
    "release_statement_ready",
    "release_supported",
    "release_supported_seed",
    "route_ready",
    "sdk_package_available",
    "sdk_package_published",
    "sdk_package_ready",
    "source_binding_ready",
    "status",
    "state",
    "struct_size_ready",
    "struct_size_validated",
    "support_tier",
    "support_tier_activated",
    "support_tier_activation_allowed",
    "support_tier_activation_ready",
    "support_tier_allowed",
    "support_tier_ready",
    "support_tier_supported",
    "support_tiers",
    "scoped_release_statement_counts_toward_complete_sdk_claim",
    "scoped_release_statement_counts_toward_completion",
    "scoped_release_statement_outcomes_satisfy_completion",
    "scoped_release_statement_ready",
    "sdk_coverage_complete",
    "tier",
    "tiers",
    "result",
    "outcome",
}
NON_COUNTING_CONTEXT_READY_ALIAS_SUFFIXES = (
    "_allowed",
    "_accepted",
    "_available",
    "_closed",
    "_cleared",
    "_complete",
    "_completed",
    "_confirmed",
    "_covered",
    "_enabled",
    "_met",
    "_outcome",
    "_passed",
    "_prepared",
    "_published",
    "_reachable",
    "_readiness",
    "_ready",
    "_result",
    "_resolved",
    "_satisfied",
    "_state",
    "_status",
    "_supported",
    "_unblocked",
    "_unlocked",
    "_validated",
)
NON_COUNTING_CONTEXT_READY_ALIAS_EXEMPT_KEYS = {
    "discord_py_available",
    "review_status",
}
NON_COUNTING_CONTEXT_PROGRESS_ALIAS_EXEMPT_KEYS = {
    "remaining_for_claim_count",
}
NON_COUNTING_CONTEXT_PROGRESS_ALIAS_SUFFIXES = (
    "_claim_progress",
    "_claim_progress_contribution",
    "_progress",
    "_progress_contribution",
    "_progress_count",
    "_progress_percent",
    "_progress_ratio",
    "_claim_count",
    "_completion_count",
    "_credit",
    "_credits",
    "_promoted_count",
)
NON_COUNTING_CONTEXT_POSITIVE_STATUS_VALUES = NOTICE_OR_BUNDLE_POSITIVE_STATUS_VALUES | {
    "accepted",
    "allowed",
    "activated",
    "approved",
    "available",
    "candidate_only_accepted",
    "candidate_ready",
    "claim_allowed",
    "complete",
    "completed",
    "complete_sdk_ready",
    "complete_triplet",
    "complete_triplet_present",
    "closed",
    "covered",
    "counted",
    "counts",
    "enabled",
    "generated",
    "green",
    "live",
    "met",
    "ok",
    "operational",
    "passed",
    "passive_triplet_complete",
    "production_grade",
    "production_ready",
    "prepared",
    "present",
    "promoted",
    "public",
    "public_abi_ready",
    "public_api_ready",
    "public_header_ready",
    "public_sdk_ready",
    "published",
    "reachable",
    "ready",
    "release_grade",
    "release_ready",
    "release_supported",
    "reviewed",
    "referenced",
    "selected",
    "runtime_ready",
    "satisfied",
    "sdk_ready",
    "stable",
    "stable_claim_allowed",
    "stable_ready",
    "stable_sdk",
    "stable_sdk_ready",
    "true",
    "supported",
    "unblocked",
    "unlocked",
    "validated",
    "verified",
    "v1_completion",
    "v1_completion_ready",
    "v1_ready",
    "v1_sdk_stable",
    "v1_stable_sdk",
    "yes",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-sdk-json", type=Path, help="Use a precomputed SDK completion JSON report.")
    parser.add_argument("--header-gate-json", type=Path, help="Use a precomputed player identity header-gate JSON report.")
    parser.add_argument("--closure-json", type=Path, help="Use a precomputed evidence-closure JSON report.")
    parser.add_argument("--evidence-dir", type=Path, help="Optional evidence dir to inspect with the closure helper.")
    parser.add_argument(
        "--principal-start-end-runtime-evidence",
        type=Path,
        help=(
            "Precomputed principal start/end runtime evidence checker JSON. This is "
            "reported as a contract-review input only and never as approved runtime evidence."
        ),
    )
    parser.add_argument(
        "--multi-surface-beta-capture-pack-json",
        type=Path,
        help=(
            "Precomputed multi-surface beta capture pack checker JSON. This is "
            "reported as planning context only and never as SDK/P0/runtime evidence."
        ),
    )
    parser.add_argument(
        "--multi-surface-beta-capture-pack",
        type=Path,
        help=(
            "Offline multi-surface beta capture pack directory or manifest.json to "
            "validate with the pack checker and report as planning context only. "
            "This never becomes SDK/P0/runtime evidence."
        ),
    )
    parser.add_argument(
        "--runtime-evidence-status-json",
        type=Path,
        help=(
            "Precomputed player-principal lifecycle runtime-evidence status JSON. "
            "This is surfaced as current window context only and never as "
            "approved runtime evidence, SDK/P0 progress, runtime readiness, or "
            "public SDK readiness."
        ),
    )
    parser.add_argument(
        "--discord-beta-bridge-config-json",
        type=Path,
        help=(
            "Precomputed Discord beta bridge config-check JSON. This is reported "
            "as communication posture only and never as Discord authorization, "
            "runtime evidence, or SDK/P0 progress."
        ),
    )
    parser.add_argument(
        "--skip-discord-beta-bridge-config-check",
        action="store_true",
        help="Do not run the local offline Discord beta bridge config check.",
    )
    parser.add_argument(
        "--release-statement",
        type=Path,
        default=DEFAULT_SCOPED_RELEASE_STATEMENT,
        help="Scoped release statement to pass to the SDK completion checker.",
    )
    parser.add_argument(
        "--public-contract-decisions-json",
        type=Path,
        default=PUBLIC_CONTRACT_DECISIONS,
        help="Player identity public-contract decisions JSON to summarize for internal blockers.",
    )
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    output_group.add_argument(
        "--compact",
        action="store_true",
        help="Emit a compact non-claim summary for CI and handoff checkpoints.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_json_command(argv: list[str]) -> tuple[dict[str, Any], int, str]:
    result = subprocess.run(argv, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"failed to parse JSON from {' '.join(argv)}: {exc}\nstderr={result.stderr}") from exc
    return payload, result.returncode, result.stderr


def load_or_run_public_sdk(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    if args.public_sdk_json:
        return load_json(args.public_sdk_json), 0
    argv = [sys.executable, str(PUBLIC_SDK_CHECK), "--json"]
    if args.release_statement:
        argv.extend(["--release-statement", str(args.release_statement)])
    payload, returncode, _stderr = run_json_command(argv)
    return payload, returncode


def load_or_run_header_gate(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    if args.header_gate_json:
        return load_json(args.header_gate_json), 0
    payload, returncode, _stderr = run_json_command([sys.executable, str(HEADER_GATE_CHECK), "--json"])
    return payload, returncode


def load_or_run_closure(args: argparse.Namespace) -> tuple[dict[str, Any] | None, int | None]:
    if args.closure_json:
        return load_json(args.closure_json), 0
    if not args.evidence_dir:
        return None, None
    payload, returncode, _stderr = run_json_command(
        [
            sys.executable,
            str(CLOSURE_REQUEST),
            "--evidence-dir",
            str(args.evidence_dir),
            "--the-island-off",
            "--two-server-cap-preserved",
            "--format",
            "json",
        ]
    )
    return payload, returncode


def principal_start_end_runtime_evidence_path(args: argparse.Namespace) -> tuple[Path | None, str | None]:
    if args.principal_start_end_runtime_evidence:
        return args.principal_start_end_runtime_evidence, "provided_report_path"
    if args.evidence_dir:
        candidate = args.evidence_dir / PRINCIPAL_START_END_RUNTIME_EVIDENCE_REPORT_NAME
        if candidate.exists():
            return candidate, "canonical_copied_evidence_path"
    return None, None


def load_principal_start_end_runtime_evidence(
    args: argparse.Namespace,
) -> tuple[dict[str, Any] | None, Path | None, str | None]:
    path, source = principal_start_end_runtime_evidence_path(args)
    if path is None:
        return None, None, None
    return load_json(path), path, source


def load_multi_surface_beta_capture_pack(
    args: argparse.Namespace,
) -> tuple[dict[str, Any] | None, Path | None, str | None]:
    if args.multi_surface_beta_capture_pack_json and args.multi_surface_beta_capture_pack:
        raise SystemExit(
            "--multi-surface-beta-capture-pack-json and "
            "--multi-surface-beta-capture-pack are mutually exclusive"
        )
    if not args.multi_surface_beta_capture_pack_json:
        if not args.multi_surface_beta_capture_pack:
            return None, None, None
        path = args.multi_surface_beta_capture_pack
        payload, _returncode, _stderr = run_json_command(
            [
                sys.executable,
                str(MULTI_SURFACE_BETA_CAPTURE_PACK_CHECK),
                str(path),
                "--json",
            ]
        )
        return payload, path, "validated_pack_path"
    path = args.multi_surface_beta_capture_pack_json
    return load_json(path), path, "provided_checker_report_path"


def load_runtime_evidence_status(
    args: argparse.Namespace,
) -> tuple[dict[str, Any] | None, Path | None, str | None]:
    if not args.runtime_evidence_status_json:
        return None, None, None
    path = args.runtime_evidence_status_json
    return load_json(path), path, "provided_runtime_evidence_status_path"


def load_discord_beta_bridge_config(
    args: argparse.Namespace,
) -> tuple[dict[str, Any] | None, Path | None, str | None]:
    if args.discord_beta_bridge_config_json:
        path = args.discord_beta_bridge_config_json
        return load_json(path), path, "provided_discord_beta_bridge_config_path"
    if args.skip_discord_beta_bridge_config_check:
        return None, None, None
    if not DISCORD_BETA_BRIDGE_CONFIG_CHECK.exists():
        return None, None, None
    python = LOCAL_DISCORD_BRIDGE_PYTHON if LOCAL_DISCORD_BRIDGE_PYTHON.exists() else Path(sys.executable)
    source_kind = (
        "local_config_check_venv"
        if python == LOCAL_DISCORD_BRIDGE_PYTHON
        else "local_config_check"
    )
    payload, _returncode, _stderr = run_json_command(
        [
            str(python),
            str(DISCORD_BETA_BRIDGE_CONFIG_CHECK),
            "--check-config",
            "--json",
        ]
    )
    return payload, DISCORD_BETA_BRIDGE_CONFIG_CHECK, source_kind


def load_public_contract_decisions(args: argparse.Namespace) -> dict[str, Any] | None:
    if args.public_contract_decisions_json is None:
        return None
    try:
        return load_json(args.public_contract_decisions_json)
    except FileNotFoundError:
        return None


def dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def list_or_empty(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def string_list(value: Any) -> list[str]:
    return [item for item in list_or_empty(value) if isinstance(item, str) and item]


def nested_get(value: dict[str, Any], *keys: str) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def first_int(*values: Any) -> int | None:
    for value in values:
        parsed = int_or_none(value)
        if parsed is not None:
            return parsed
    return None


def progress_value_is_nonzero(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, float):
        return value != 0.0
    if isinstance(value, list):
        return any(progress_value_is_nonzero(item) for item in value)
    if isinstance(value, dict):
        return any(progress_value_is_nonzero(item) for item in value.values())
    if not isinstance(value, str):
        return False

    normalized = value.strip().lower()
    if not normalized or normalized in {"0", "0.0", "0%", "false", "none", "no"}:
        return False
    if re.fullmatch(r"0+\s*/\s*[1-9]\d*", normalized):
        return False
    if re.fullmatch(r"0+(?:\.0+)?\s*%", normalized):
        return False
    return True


def normalized_alias_key(value: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def normalized_alias_path_parts(path: str) -> list[str]:
    return [
        part
        for part in (
            normalized_alias_key(raw_part)
            for raw_part in re.split(r"(?:\.|\[\d+\])", path)
        )
        if part
    ]


def normalized_alias_path_suffixes(path: str) -> list[str]:
    parts = normalized_alias_path_parts(path)
    return ["_".join(parts[index:]) for index in range(len(parts))]


def alias_value_is_positive(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, list):
        return any(alias_value_is_positive(item) for item in value)
    if isinstance(value, dict):
        return any(alias_value_is_positive(item) for item in value.values())
    if isinstance(value, str):
        return normalized_alias_key(value) in NON_COUNTING_CONTEXT_POSITIVE_STATUS_VALUES
    return False


def value_marks_non_counting_context(value: Any) -> bool:
    if isinstance(value, str):
        return NON_COUNTING_CONTEXT_MARKER_RE.search(normalized_alias_key(value)) is not None
    if isinstance(value, list):
        return any(value_marks_non_counting_context(item) for item in value)
    if isinstance(value, dict):
        return any(
            value_marks_non_counting_context(item)
            for key, item in value.items()
            if normalized_alias_key(key)
            in {
                "artifact_scope",
                "classification",
                "evidence_kind",
                "path_type",
                "readiness_scope",
                "ready_scope",
                "schema",
                "source_kind",
                "status",
                "target_set",
                "type",
            }
        )
    return False


def non_public_checkjoin_session_start_rejected_acceptance_present(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if (
                NON_PUBLIC_CHECKJOIN_REJECTED_OFFLINE_ACCEPTANCE_RE.search(
                    normalized_alias_key(key)
                )
                is not None
                or non_public_checkjoin_session_start_rejected_acceptance_present(item)
            ):
                return True
        return False
    if isinstance(value, list):
        return any(
            non_public_checkjoin_session_start_rejected_acceptance_present(item)
            for item in value
        )
    if isinstance(value, str):
        return (
            NON_PUBLIC_CHECKJOIN_REJECTED_OFFLINE_ACCEPTANCE_RE.search(
                normalized_alias_key(value)
            )
            is not None
        )
    return False


def quarantined_runtime_evidence_source_present(
    value: Any,
    *,
    source_marker_context: bool = False,
) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            key_name = normalized_alias_key(key)
            key_is_quarantined = (
                NON_APPROVED_RUNTIME_EVIDENCE_SOURCE_RE.search(key_name) is not None
            )
            if key_is_quarantined:
                return True
            if quarantined_runtime_evidence_source_present(
                item,
                source_marker_context=(
                    source_marker_context
                    or key_name in APPROVED_RUNTIME_EVIDENCE_SOURCE_MARKER_KEYS
                ),
            ):
                return True
        return False
    if isinstance(value, list):
        return any(
            quarantined_runtime_evidence_source_present(
                item,
                source_marker_context=source_marker_context,
            )
            for item in value
        )
    if isinstance(value, str) and source_marker_context:
        return (
            NON_APPROVED_RUNTIME_EVIDENCE_SOURCE_RE.search(normalized_alias_key(value))
            is not None
        )
    return False


def accepted_runtime_lifecycle_count(value: dict[str, Any]) -> int | None:
    for key in APPROVED_RUNTIME_ACCEPTED_COUNT_KEYS:
        parsed = int_or_none(value.get(key))
        if parsed is not None:
            return parsed
    for key in APPROVED_RUNTIME_ACCEPTED_LIST_KEYS:
        item = value.get(key)
        if isinstance(item, list):
            return len(item)
    return None


def partial_lifecycle_shortcut_present(value: Any) -> bool:
    if isinstance(value, dict):
        accepted_count = accepted_runtime_lifecycle_count(value)
        if (
            accepted_count is not None
            and accepted_count != len(REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES)
        ):
            return True
        for key, item in value.items():
            key_name = normalized_alias_key(key)
            if any(marker in key_name for marker in PARTIAL_LIFECYCLE_SHORTCUT_MARKERS):
                return True
            if partial_lifecycle_shortcut_present(item):
                return True
        return False
    if isinstance(value, list):
        return any(partial_lifecycle_shortcut_present(item) for item in value)
    if isinstance(value, str):
        value_name = normalized_alias_key(value)
        return any(marker in value_name for marker in PARTIAL_LIFECYCLE_SHORTCUT_MARKERS)
    return False


def non_counting_context_ready_alias_key(key_name: str) -> bool:
    if key_name in NON_COUNTING_CONTEXT_READY_ALIAS_EXEMPT_KEYS:
        return False
    if "_counts_as_" in key_name or "_counts_toward_" in key_name:
        return True
    return key_name in NON_COUNTING_CONTEXT_READY_ALIAS_KEYS or any(
        key_name.endswith(suffix) for suffix in NON_COUNTING_CONTEXT_READY_ALIAS_SUFFIXES
    )


def non_counting_context_progress_alias_key(key_name: str) -> bool:
    if key_name in NON_COUNTING_CONTEXT_PROGRESS_ALIAS_EXEMPT_KEYS:
        return False
    return key_name in NON_COUNTING_ZERO_ALIAS_KEYS or any(
        key_name.endswith(suffix) for suffix in NON_COUNTING_CONTEXT_PROGRESS_ALIAS_SUFFIXES
    )


def allowed_non_counting_context_ready_alias(
    key_name: str,
    value: Any,
    container: dict[str, Any],
) -> bool:
    if key_name != "ready" or value is not True:
        return False
    schema = normalized_alias_key(container.get("schema"))
    blockers = container.get("blockers")
    return (
        schema == "obelisk_structure_build_policy_offline_intake_check_v1"
        and container.get("planning_only") is True
        and isinstance(blockers, list)
        and not blockers
    )


def notice_or_bundle_status_alias_overclaims(
    key_name: str,
    value: Any,
    path: str,
) -> bool:
    path_parts = normalized_alias_path_parts(path)
    if key_name in NOTICE_OR_BUNDLE_NON_PROGRESS_FALSE_ALIAS_KEYS:
        return alias_value_is_positive(value)
    if any(
        suffix in NOTICE_OR_BUNDLE_NON_PROGRESS_FALSE_ALIAS_KEYS
        for suffix in normalized_alias_path_suffixes(path)
    ):
        return alias_value_is_positive(value)

    status_key_match = key_name in NOTICE_OR_BUNDLE_STATUS_KEYS
    combined_status_key_match = any(
        key_name.endswith(f"_{status_key}")
        and any(container in key_name for container in NOTICE_OR_BUNDLE_STATUS_CONTAINER_KEYS)
        for status_key in NOTICE_OR_BUNDLE_STATUS_KEYS
    )
    if not status_key_match and not combined_status_key_match:
        return False
    if not combined_status_key_match and not any(
        part in NOTICE_OR_BUNDLE_STATUS_CONTAINER_KEYS for part in path_parts
    ):
        return False
    return alias_value_is_positive(value)


def sanitize_non_counting_alias_payload(
    payload: dict[str, Any],
    *,
    false_keys: set[str],
    zero_keys: set[str],
    initial_non_counting_context: bool,
) -> dict[str, Any]:
    def path_marks_non_counting_context(path: str) -> bool:
        return any(
            NON_COUNTING_CONTEXT_MARKER_RE.search(part) is not None
            for part in normalized_alias_path_parts(path)
        )

    def visit(value: Any, path: str, in_non_counting_context: bool) -> Any:
        current_context = in_non_counting_context or path_marks_non_counting_context(path)
        if isinstance(value, dict):
            current_context = current_context or value_marks_non_counting_context(value)
            sanitized: dict[str, Any] = {}
            for key, item in value.items():
                item_path = f"{path}.{key}" if path else str(key)
                key_name = normalized_alias_key(key)
                sanitized_item = visit(item, item_path, current_context)
                if (
                    key_name in false_keys
                    or notice_or_bundle_status_alias_overclaims(key_name, item, item_path)
                    or (
                        current_context
                        and non_counting_context_ready_alias_key(key_name)
                        and alias_value_is_positive(item)
                    )
                ):
                    sanitized_item = False
                if (
                    key_name in zero_keys
                    or (
                        current_context
                        and non_counting_context_progress_alias_key(key_name)
                        and progress_value_is_nonzero(item)
                    )
                ):
                    sanitized_item = 0
                sanitized[key] = sanitized_item
            return sanitized
        if isinstance(value, list):
            return [
                visit(item, f"{path}[{index}]", current_context)
                for index, item in enumerate(value)
            ]
        return value

    return visit(payload, "", initial_non_counting_context)


def source_alias_overclaim_paths(
    payload: dict[str, Any],
    *,
    false_keys: set[str],
    zero_keys: set[str],
    initial_non_counting_context: bool,
) -> tuple[list[str], list[str]]:
    overclaimed_false_flags: list[str] = []
    overclaimed_progress_flags: list[str] = []

    def path_marks_non_counting_context(path: str) -> bool:
        return any(
            NON_COUNTING_CONTEXT_MARKER_RE.search(part) is not None
            for part in normalized_alias_path_parts(path)
        )

    def visit(value: Any, path: str, in_non_counting_context: bool) -> None:
        current_context = in_non_counting_context or path_marks_non_counting_context(path)
        if isinstance(value, dict):
            current_context = current_context or value_marks_non_counting_context(value)
            for key, item in value.items():
                item_path = f"{path}.{key}" if path else str(key)
                key_name = normalized_alias_key(key)
                if key_name in false_keys and alias_value_is_positive(item):
                    overclaimed_false_flags.append(item_path)
                if notice_or_bundle_status_alias_overclaims(key_name, item, item_path):
                    overclaimed_false_flags.append(item_path)
                if (
                    current_context
                    and non_counting_context_ready_alias_key(key_name)
                    and alias_value_is_positive(item)
                    and not allowed_non_counting_context_ready_alias(key_name, item, value)
                ):
                    overclaimed_false_flags.append(item_path)
                if key_name in zero_keys and progress_value_is_nonzero(item):
                    overclaimed_progress_flags.append(item_path)
                if (
                    current_context
                    and non_counting_context_progress_alias_key(key_name)
                    and progress_value_is_nonzero(item)
                ):
                    overclaimed_progress_flags.append(item_path)
                visit(item, item_path, current_context)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]", current_context)

    visit(payload, "", initial_non_counting_context)
    return sorted(set(overclaimed_false_flags)), sorted(set(overclaimed_progress_flags))


def allowed_non_counting_false_progress_alias_path(path: str) -> bool:
    parts = normalized_alias_path_parts(path)
    return (
        len(parts) >= 4
        and parts[0] == "mission_transfer_dino_tribe_outcome_accounting"
        and parts[1] == "release_statement"
        and parts[2] == "leaf_exclusions"
    )


def non_counting_false_progress_alias_violations(payload: dict[str, Any]) -> list[str]:
    violations: list[str] = []

    def path_marks_non_counting_context(path: str) -> bool:
        return any(
            NON_COUNTING_CONTEXT_MARKER_RE.search(part) is not None
            for part in normalized_alias_path_parts(path)
        )

    def visit(value: Any, path: str, in_non_counting_context: bool) -> None:
        current_context = in_non_counting_context or path_marks_non_counting_context(path)
        if isinstance(value, dict):
            current_context = current_context or value_marks_non_counting_context(value)
            for key, item in value.items():
                item_path = f"{path}.{key}" if path else str(key)
                key_name = normalized_alias_key(key)
                if notice_or_bundle_status_alias_overclaims(key_name, item, item_path):
                    if not allowed_non_counting_false_progress_alias_path(item_path):
                        violations.append(item_path)
                allowed_ready_alias = allowed_non_counting_context_ready_alias(
                    key_name,
                    item,
                    value,
                )
                if (
                    key_name in NON_COUNTING_GLOBAL_FALSE_ALIAS_KEYS
                    and alias_value_is_positive(item)
                    and not allowed_ready_alias
                ):
                    if not allowed_non_counting_false_progress_alias_path(item_path):
                        violations.append(item_path)
                if (
                    current_context
                    and key_name in NON_COUNTING_FALSE_ALIAS_KEYS
                    and alias_value_is_positive(item)
                    and not allowed_ready_alias
                ):
                    if not allowed_non_counting_false_progress_alias_path(item_path):
                        violations.append(item_path)
                if (
                    current_context
                    and non_counting_context_ready_alias_key(key_name)
                    and alias_value_is_positive(item)
                    and not allowed_ready_alias
                ):
                    if not allowed_non_counting_false_progress_alias_path(item_path):
                        violations.append(item_path)
                if (
                    current_context
                    and non_counting_context_progress_alias_key(key_name)
                    and progress_value_is_nonzero(item)
                ):
                    violations.append(item_path)
                visit(item, item_path, current_context)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]", current_context)

    visit(payload, "", False)
    return sorted(set(violations))


def first_string_list_from_paths(
    payload: dict[str, Any],
    paths: tuple[tuple[str, ...], ...],
) -> list[str]:
    for path in paths:
        values = string_list(nested_get(payload, *path))
        if values:
            return values
    return []


def ordered_p0_dependency_chain_promoted(
    public_sdk: dict[str, Any],
    *,
    current_route_blocker: Any,
    remaining_route_blockers: list[str],
    p0_count_summary: dict[str, Any],
) -> bool:
    if route_blockers(current_route_blocker, remaining_route_blockers):
        return False
    promoted = int_or_none(p0_count_summary.get("promoted_for_claim_count"))
    remaining = int_or_none(p0_count_summary.get("remaining_for_claim_count"))
    total = int_or_none(p0_count_summary.get("total"))
    if promoted != len(P0_DEPENDENCY_CHAIN_SURFACES) or total != len(P0_DEPENDENCY_CHAIN_SURFACES):
        return False
    if remaining != 0:
        return False
    promoted_surfaces = first_string_list_from_paths(
        public_sdk,
        (
            ("p0_dependency_chain_claim_accounting", "promoted_for_claim_surfaces"),
            ("summary", "p0_completion", "promoted_for_claim_surfaces"),
            ("v1_sdk_progress", "p0_dependency_chain_promoted_for_claim"),
            ("p0_dependency_chain_promoted_for_claim",),
        ),
    )
    return promoted_surfaces == list(P0_DEPENDENCY_CHAIN_SURFACES)


def side_lane_source_containers(public_sdk: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    containers: list[tuple[str, dict[str, Any]]] = [("public_sdk", public_sdk)]
    for key in SIDE_LANE_CONTAINER_KEYS:
        value = public_sdk.get(key)
        if isinstance(value, dict):
            containers.append((key, value))
    return containers


def source_side_lane_payload(
    public_sdk: dict[str, Any],
    aliases: tuple[str, ...],
) -> tuple[dict[str, Any], str | None]:
    for container_name, container in side_lane_source_containers(public_sdk):
        for alias in aliases:
            value = container.get(alias)
            if isinstance(value, dict):
                return value, f"{container_name}.{alias}"
    return {}, None


def side_lane_candidate_status(source: dict[str, Any]) -> bool:
    return any(
        bool(source.get(key))
        for key in (
            "candidate_only",
            "candidate_only_mode",
            "accepted_for_candidate_review",
            "accepted_for_internal_planning",
            "offline_only",
            "fixture_only",
            "not_artifact_gate",
        )
    ) or any(
        normalized_alias_key(source.get(key)) in SIDE_LANE_CANDIDATE_STATUS_MARKERS
        for key in (
            "accounting_route",
            "artifact_scope",
            "classification",
            "mode",
            "readiness_classification",
            "status",
        )
        if isinstance(source.get(key), str)
    ) or value_marks_non_counting_context(source)


def filtered_side_lane_source_overclaimed_flags(
    source: dict[str, Any],
    source_overclaimed_flags: list[str],
) -> list[str]:
    if not side_lane_candidate_status(source):
        return source_overclaimed_flags
    accounting_route = normalized_alias_key(source.get("accounting_route"))

    def candidate_bookkeeping_flag(flag: str) -> bool:
        parts = normalized_alias_path_parts(flag)
        tail = parts[-1] if parts else normalized_alias_key(flag)
        if (
            accounting_route in SIDE_LANE_NON_CLAIM_BOOKKEEPING_ROUTES
            and parts[:2] == ["release_statement", "leaf_exclusions"]
        ):
            return True
        return (
            accounting_route in SIDE_LANE_NON_CLAIM_BOOKKEEPING_ROUTES
            and tail in SIDE_LANE_NON_CLAIM_BOOKKEEPING_FLAG_KEYS
        )

    return [
        flag
        for flag in source_overclaimed_flags
        if normalized_alias_key(flag) not in {"ready", "source_ready"}
        and not candidate_bookkeeping_flag(flag)
    ]


def side_lane_context(side_lane_id: str, source: dict[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {}
    for key in (
        "target_set",
        "target_sets",
        "surface",
        "accounting_route",
        "required_leaves",
        "observed_leaves",
        "missing_leaf_families",
        "leaf_statuses",
        "expected_targets",
        "checked_targets",
        "explicitly_excluded",
        "item_net_info_excluded",
    ):
        if key in source:
            context[key] = source[key]

    blockers = source.get("blockers")
    if isinstance(blockers, list):
        context["blocker_count"] = len(blockers)

    if side_lane_id == "buff_status":
        source_manifest = source.get("source_manifest")
        if isinstance(source_manifest, dict):
            context["source_manifest"] = {
                key: source_manifest.get(key)
                for key in (
                    "schema",
                    "source",
                    "status",
                    "sha256",
                    "ark_binary_sha256",
                    "sha_prefix",
                    "target_count",
                    "bound_target_count",
                )
                if key in source_manifest
            }
        summary = dict_or_empty(source.get("summary"))
        source_binding_count = first_int(
            source.get("source_binding_count"),
            summary.get("source_binding_count"),
        )
        if source_binding_count is None and isinstance(summary.get("source_bindings"), list):
            source_binding_count = len(summary["source_bindings"])
        if source_binding_count is not None:
            context["source_binding_count"] = source_binding_count

    if side_lane_id == "dino_scalar":
        source_isolation = source.get("source_isolation")
        if isinstance(source_isolation, dict):
            context["source_isolation"] = {
                key: source_isolation.get(key)
                for key in (
                    "public_or_runtime_dino_wiring_detected",
                    "scanned_blocked_source_files",
                )
                if key in source_isolation
            }

    return context


def normalize_side_lane(
    side_lane_id: str,
    public_sdk: dict[str, Any],
) -> dict[str, Any]:
    source, source_key = source_side_lane_payload(
        public_sdk,
        SIDE_LANE_SOURCE_ALIASES[side_lane_id],
    )
    source_present = bool(source_key)
    source_overclaimed_flags, source_overclaimed_progress_flags = (
        source_alias_overclaim_paths(
            source,
            false_keys=set(SIDE_LANE_FALSE_FLAGS) | set(FAIL_CLOSED_ACTION_FALSE_FLAGS),
            zero_keys=set(SIDE_LANE_ZERO_FIELDS),
            initial_non_counting_context=True,
        )
    )
    source_overclaimed_flags = filtered_side_lane_source_overclaimed_flags(
        source,
        source_overclaimed_flags,
    )
    normalized: dict[str, Any] = {
        "id": side_lane_id,
        "label": SIDE_LANE_LABELS[side_lane_id],
        "side_lane": True,
        "non_claim_side_lane": True,
        "status_report_only": True,
        "normalization_only": True,
        "source_present": source_present,
        "source_key": source_key,
        "synthetic_status_only": not source_present,
        "summary_source": (
            "precomputed_public_sdk_payload"
            if source_present
            else "synthetic_status_only; status reporter did not run side-lane checkers"
        ),
        "schema": "obelisk.sdk-status-side-lane-summary.v1",
        "source_schema": source.get("schema") if source_present else None,
        "status": "non_claim_side_lane",
        "source_status": source.get("status") if source_present else None,
        "ready": False,
        "source_ready": bool(source.get("ready")) if source_present else False,
        "candidate_status_observed": side_lane_candidate_status(source),
        "offline_status_only": True,
        "non_authorizing": True,
        "context": side_lane_context(side_lane_id, source) if source_present else {},
        "non_claim": (
            f"{SIDE_LANE_LABELS[side_lane_id]} is reported as a non-authorizing, "
            "non-claim side lane; this status report does not run its checker and "
            "does not count it toward SDK/P0 progress."
        ),
        "non_claims": string_list(source.get("non_claims"))
        + [
            "side-lane summary is status-only and non-authorizing",
            "does not authorize live ops, workspace writes, runtime capture, or live-log reads",
            "does not count toward complete SDK or P0 dependency-chain progress",
        ],
    }
    for key in SIDE_LANE_FALSE_FLAGS:
        normalized[key] = False
    for key in SIDE_LANE_ZERO_FIELDS:
        normalized[key] = 0
    if source_overclaimed_flags:
        normalized["source_overclaimed_authorization_or_claim_flags"] = sorted(
            source_overclaimed_flags
        )
    if source_overclaimed_progress_flags:
        normalized["source_overclaimed_progress_flags"] = sorted(
            source_overclaimed_progress_flags
        )
    return normalized


def normalize_side_lanes(public_sdk: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        side_lane_id: normalize_side_lane(side_lane_id, public_sdk)
        for side_lane_id in SIDE_LANE_SOURCE_ALIASES
    }


def summarize_side_lane_source_overclaims(
    side_lanes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    by_side_lane: dict[str, dict[str, list[str]]] = {}
    authorization_or_claim_flag_count = 0
    progress_flag_count = 0
    for side_lane_id, payload in side_lanes.items():
        authorization_or_claim = string_list(
            payload.get("source_overclaimed_authorization_or_claim_flags")
        )
        progress = string_list(payload.get("source_overclaimed_progress_flags"))
        if authorization_or_claim or progress:
            authorization_or_claim_flag_count += len(authorization_or_claim)
            progress_flag_count += len(progress)
            by_side_lane[side_lane_id] = {
                "authorization_or_claim": authorization_or_claim,
                "progress": progress,
            }

    return {
        "status_report_only": True,
        "non_claim": (
            "Source overclaims on side-lane inputs are normalized inside each side-lane "
            "summary and do not change SDK/P0 progress, runtime readiness, or route blockers."
        ),
        "count": len(by_side_lane),
        "authorization_or_claim_flag_count": authorization_or_claim_flag_count,
        "progress_flag_count": progress_flag_count,
        "total_flag_count": authorization_or_claim_flag_count + progress_flag_count,
        "side_lane_ids": sorted(by_side_lane),
        "side_lanes": by_side_lane,
    }


def summarize_report_source_overclaims(report: dict[str, Any]) -> dict[str, Any]:
    components: dict[str, dict[str, Any]] = {}

    def record(component: str, category: str, flags: Any) -> None:
        normalized_flags = string_list(flags)
        if not normalized_flags:
            return
        component_summary = components.setdefault(
            component,
            {
                "flag_count": 0,
                "categories": {},
            },
        )
        component_summary["categories"][category] = normalized_flags
        component_summary["flag_count"] += len(normalized_flags)

    record("report", "readiness", report.get("source_overclaimed_readiness_flags"))
    record("report", "route", report.get("source_overclaimed_route_flags"))
    record("report", "counts", report.get("source_overclaimed_count_flags"))

    fastest = report.get("fastest_next_sdk_unblock")
    if isinstance(fastest, dict):
        record("fastest_next_sdk_unblock", "authorization", fastest.get("source_overclaimed_authorization_flags"))
        record("fastest_next_sdk_unblock", "progress", fastest.get("source_overclaimed_progress_flags"))

    simulation = report.get("post_evidence_p0_lock_simulation")
    if isinstance(simulation, dict):
        record(
            "post_evidence_p0_lock_simulation",
            "authorization_or_claim",
            simulation.get("source_overclaimed_readiness_or_authorization_flags"),
        )
        record(
            "post_evidence_p0_lock_simulation",
            "progress",
            simulation.get("source_overclaimed_progress_flags"),
        )

    start_end = report.get("principal_start_end_runtime_evidence")
    if isinstance(start_end, dict):
        record(
            "principal_start_end_runtime_evidence",
            "authorization_or_claim",
            start_end.get("source_overclaimed_readiness_or_authorization_flags"),
        )
        record(
            "principal_start_end_runtime_evidence",
            "progress",
            start_end.get("source_overclaimed_progress_flags"),
        )

    multi_surface_pack = report.get("multi_surface_beta_capture_pack")
    if isinstance(multi_surface_pack, dict):
        record(
            "multi_surface_beta_capture_pack",
            "authorization_or_claim",
            multi_surface_pack.get(
                "source_overclaimed_readiness_or_authorization_flags"
            ),
        )
        record(
            "multi_surface_beta_capture_pack",
            "progress",
            multi_surface_pack.get("source_overclaimed_progress_flags"),
        )

    runtime_evidence_window = report.get("runtime_evidence_window")
    if isinstance(runtime_evidence_window, dict):
        record(
            "runtime_evidence_window",
            "authorization_or_claim",
            runtime_evidence_window.get(
                "source_overclaimed_readiness_or_authorization_flags"
            ),
        )
        record(
            "runtime_evidence_window",
            "progress",
            runtime_evidence_window.get("source_overclaimed_progress_flags"),
        )

    discord_bridge = report.get("discord_beta_bridge")
    if isinstance(discord_bridge, dict):
        record(
            "discord_beta_bridge",
            "authorization_or_claim",
            discord_bridge.get(
                "source_overclaimed_readiness_or_authorization_flags"
            ),
        )
        record(
            "discord_beta_bridge",
            "progress",
            discord_bridge.get("source_overclaimed_progress_flags"),
        )

    header = report.get("header_gate")
    if isinstance(header, dict):
        record("header_gate", "readiness", header.get("source_overclaimed_readiness_flags"))

    side_lane_overclaims = report.get("side_lane_source_overclaims")
    if isinstance(side_lane_overclaims, dict):
        side_lanes = side_lane_overclaims.get("side_lanes")
        if isinstance(side_lanes, dict):
            authorization_or_claim: list[str] = []
            progress: list[str] = []
            for side_lane_id, payload in side_lanes.items():
                if not isinstance(payload, dict):
                    continue
                authorization_or_claim.extend(
                    f"{side_lane_id}.{flag}"
                    for flag in string_list(payload.get("authorization_or_claim"))
                )
                progress.extend(
                    f"{side_lane_id}.{flag}"
                    for flag in string_list(payload.get("progress"))
                )
            record("side_lanes", "authorization_or_claim", authorization_or_claim)
            record("side_lanes", "progress", progress)

    operator_context = report.get("operator_context_summary")
    if isinstance(operator_context, dict):
        contexts = operator_context.get("contexts")
        if isinstance(contexts, list):
            authorization_or_claim: list[str] = []
            progress: list[str] = []
            for context in contexts:
                if not isinstance(context, dict):
                    continue
                context_id = compact_string(context.get("id")) or "unknown"
                authorization_or_claim.extend(
                    f"{context_id}.{flag}"
                    for flag in string_list(
                        context.get("source_overclaimed_authorization_or_claim_flags")
                    )
                )
                progress.extend(
                    f"{context_id}.{flag}"
                    for flag in string_list(context.get("source_overclaimed_progress_flags"))
                )
            record("operator_context", "authorization_or_claim", authorization_or_claim)
            record("operator_context", "progress", progress)

    closure = report.get("closure")
    if isinstance(closure, dict):
        record("closure", "readiness", closure.get("source_overclaimed_readiness_flags"))
        record("closure", "evidence", closure.get("source_overclaimed_evidence_flags"))

    actionable_paths = report.get("actionable_paths")
    if isinstance(actionable_paths, dict):
        authorization: list[str] = []
        progress: list[str] = []
        for path_id, payload in actionable_paths.items():
            if not isinstance(payload, dict):
                continue
            authorization.extend(
                f"{path_id}.{flag}"
                for flag in string_list(payload.get("source_overclaimed_authorization_flags"))
            )
            progress.extend(
                f"{path_id}.{flag}"
                for flag in string_list(payload.get("source_overclaimed_progress_flags"))
            )
        record("action_paths", "authorization", authorization)
        record("action_paths", "progress", progress)

    return {
        "status_report_only": True,
        "non_claim": (
            "Source overclaim totals are diagnostics only; normalized readiness, "
            "SDK/P0 progress, runtime readiness, and route blockers are unchanged."
        ),
        "component_count": len(components),
        "total_flag_count": sum(
            int(component.get("flag_count", 0)) for component in components.values()
        ),
        "components": components,
    }


def default_private_logout_correlation_status() -> dict[str, Any]:
    return {
        "id": PRIVATE_LOGOUT_CORRELATION_BLOCKER_ID,
        "status": "blocked/internal-planning",
        "visibility": "internal_non_public_planning_only",
        "current_blocker": "private_logout_correlation_missing",
        "blocks_before_public_identity_promotion": True,
        "decision_required": (
            "Define and test private logout correlation from session_end/logout "
            "observations to a process-local principal token before any public "
            "identity promotion review can proceed."
        ),
        "required_internal_contract": [
            "session_end/logout remains unresolved and fail-closed unless a private correlated principal token is present",
            "the correlation source remains internal and is not exposed to plugins",
            "correlated logout invalidates only the matching process-local principal generation",
            "uncorrelated, duplicate, stale, unsupported, or cross-process logout context fails closed",
        ],
        "forbidden_public_outcomes": [
            "no public lookup API",
            "no public identity exposure",
            "no public header symbols",
            "no public ABI readiness",
            "no public header readiness",
            "no public SDK readiness",
            "no runtime readiness",
            "no live authorization",
        ],
        "non_claims": [
            "private logout correlation planning is internal only: no public lookup",
            "private logout correlation planning is internal only: no identity exposure",
            "private logout correlation planning is internal only: no ABI/header readiness",
            "private logout correlation planning is internal only: no live authorization",
        ],
    }


def private_logout_correlation_status(
    public_contract_decisions: dict[str, Any] | None,
) -> dict[str, Any]:
    source = (
        dict_or_empty(public_contract_decisions.get(PRIVATE_LOGOUT_CORRELATION_BLOCKER_ID))
        if isinstance(public_contract_decisions, dict)
        else {}
    )
    status = default_private_logout_correlation_status()
    for key in ("id", "status", "visibility", "current_blocker", "decision_required"):
        value = source.get(key)
        if isinstance(value, str) and value:
            status[key] = value
    for key in ("required_internal_contract", "forbidden_public_outcomes"):
        values = string_list(source.get(key))
        if values:
            status[key] = values

    non_claims = string_list(source.get("non_claims"))
    if not non_claims:
        non_claims = list(status["non_claims"])
    for claim in PRIVATE_LOGOUT_CORRELATION_REQUIRED_NON_CLAIMS:
        if not any(claim in existing for existing in non_claims):
            non_claims.append(f"private logout correlation planning is internal only: {claim}")
    status["non_claims"] = non_claims

    source_overclaimed_flags = [
        key for key in PRIVATE_LOGOUT_CORRELATION_FALSE_FLAGS if alias_value_is_positive(source.get(key))
    ]
    status["blocks_before_public_identity_promotion"] = True
    source_internal_active = source.get("internal_blocker_active")
    status["internal_blocker_active"] = (
        source_internal_active
        if isinstance(source_internal_active, bool)
        else True
    )
    status["status_report_only"] = True
    for key in PRIVATE_LOGOUT_CORRELATION_FALSE_FLAGS:
        status[key] = False
    if source_overclaimed_flags:
        status["source_overclaimed_readiness_or_authorization_flags"] = sorted(
            source_overclaimed_flags
        )
    return status


def command_permission_route_gate(public_sdk: dict[str, Any]) -> dict[str, Any]:
    return dict_or_empty(public_sdk.get("command_permission_route_gate"))


def source_post_evidence_p0_lock_simulation(
    public_sdk: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    containers = (
        public_sdk,
        command_permission_route_gate(public_sdk),
        dict_or_empty(public_sdk.get("route_gate")),
    )
    for container in containers:
        for key in (
            "post_evidence_p0_lock_simulation",
            "route_gate_post_evidence_p0_lock_simulation",
        ):
            value = container.get(key)
            if isinstance(value, dict):
                return value, True
    return {}, False


def normalized_route_blocker_value(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return None


def normalize_post_evidence_child_check(child: Any) -> dict[str, Any]:
    source = dict(child) if isinstance(child, dict) else {}
    name = source.get("name")
    normalized: dict[str, Any] = {
        "name": name if isinstance(name, str) and name else None,
        "present": bool(source.get("present")),
        "current_route_blocker": normalized_route_blocker_value(
            source.get("current_route_blocker")
        ),
        "remaining_route_blockers": string_list(source.get("remaining_route_blockers")),
        "dependency_chain_locked": bool(source.get("dependency_chain_locked")),
    }
    overclaimed_flags, overclaimed_progress_flags = source_alias_overclaim_paths(
        source,
        false_keys=set(POST_EVIDENCE_P0_CHILD_FALSE_FLAGS),
        zero_keys=set(FAIL_CLOSED_ACTION_ZERO_FIELDS) | set(POST_EVIDENCE_P0_LOCK_ZERO_FIELDS),
        initial_non_counting_context=True,
    )
    for key in POST_EVIDENCE_P0_CHILD_FALSE_FLAGS:
        normalized[key] = False
    if overclaimed_flags:
        normalized["source_overclaimed_accounting_flags"] = sorted(overclaimed_flags)
    if overclaimed_progress_flags:
        normalized["source_overclaimed_progress_flags"] = sorted(overclaimed_progress_flags)
    return normalized


def normalize_post_evidence_p0_lock_simulation(
    public_sdk: dict[str, Any],
    *,
    current_route_blocker: Any,
    remaining_route_blockers: list[str],
) -> dict[str, Any]:
    command_route_gate = command_permission_route_gate(public_sdk)
    source, source_present = source_post_evidence_p0_lock_simulation(public_sdk)
    route_current_blocker = normalized_route_blocker_value(
        current_route_blocker,
        command_route_gate.get("current_route_blocker"),
        command_route_gate.get("current_blocker"),
        source.get("current_route_blocker"),
    )
    route_remaining_blockers = (
        remaining_route_blockers
        or string_list(command_route_gate.get("remaining_route_blockers"))
        or string_list(source.get("remaining_route_blockers"))
    )
    if route_current_blocker is not None:
        route_remaining_blockers = list(
            dict.fromkeys([route_current_blocker, *route_remaining_blockers])
        )

    source_accepted = source.get("approved_runtime_evidence_accepted")
    command_forwarded = command_route_gate.get("approved_runtime_evidence_forwarded")
    if route_current_blocker == "approved_runtime_evidence_missing":
        approved_runtime_evidence_accepted = False
    elif isinstance(command_forwarded, bool):
        approved_runtime_evidence_accepted = command_forwarded
    else:
        approved_runtime_evidence_accepted = bool(source_accepted)

    source_overclaimed_flags, source_overclaimed_progress_flags = source_alias_overclaim_paths(
        source,
        false_keys=set(POST_EVIDENCE_P0_LOCK_FALSE_FLAGS),
        zero_keys=set(POST_EVIDENCE_P0_LOCK_ZERO_FIELDS),
        initial_non_counting_context=True,
    )
    if (
        source_accepted is True
        and route_current_blocker == "approved_runtime_evidence_missing"
    ):
        source_overclaimed_flags.append("approved_runtime_evidence_accepted")

    source_next_blocker = source.get("simulated_route_blocker_after_accepted_runtime_evidence")
    normalized: dict[str, Any] = {
        "schema": POST_EVIDENCE_P0_LOCK_SIMULATION_SCHEMA,
        "source_schema": source.get("schema") if source_present else None,
        "source_present": source_present,
        "status_report_only": True,
        "simulation_only": True,
        "non_claim": (
            "post-evidence P0 lock simulation only; accepted runtime evidence can "
            "only move the route toward identity public contract review and does "
            "not unlock permissions/admin, command response, commands/replies, "
            "public ABI/header readiness, runtime readiness, public SDK readiness, "
            "P0 progress, complete SDK claim progress, live ops, runtime capture, "
            "or workspace writes"
        ),
        "source_non_claim": source.get("non_claim"),
        "approved_runtime_evidence_accepted": approved_runtime_evidence_accepted,
        "source_approved_runtime_evidence_accepted": source_accepted,
        "current_route_blocker": route_current_blocker,
        "source_current_route_blocker": source.get("current_route_blocker"),
        "remaining_route_blockers": route_remaining_blockers,
        "source_remaining_route_blockers": (
            string_list(source.get("remaining_route_blockers")) if source_present else []
        ),
        "simulated_route_blocker_after_accepted_runtime_evidence": (
            IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER
        ),
        "source_simulated_route_blocker_after_accepted_runtime_evidence": source_next_blocker,
        "identity_public_contract_required": True,
        "p0_child_checks": [
            normalize_post_evidence_child_check(child)
            for child in list_or_empty(source.get("p0_child_checks"))
        ],
    }
    for key in POST_EVIDENCE_P0_LOCK_FALSE_FLAGS:
        normalized[key] = False
    for key in POST_EVIDENCE_P0_LOCK_ZERO_FIELDS:
        normalized[key] = 0
    if source.get("schema") not in (None, POST_EVIDENCE_P0_LOCK_SIMULATION_SCHEMA):
        source_overclaimed_flags.append("schema")
    if (
        isinstance(source_next_blocker, str)
        and source_next_blocker
        and source_next_blocker != IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER
    ):
        source_overclaimed_flags.append(
            "simulated_route_blocker_after_accepted_runtime_evidence"
        )
    if source_overclaimed_flags:
        normalized["source_overclaimed_readiness_or_authorization_flags"] = sorted(
            set(source_overclaimed_flags)
        )
    if source_overclaimed_progress_flags:
        normalized["source_overclaimed_progress_flags"] = sorted(
            set(source_overclaimed_progress_flags)
        )
    return normalized


def ratio_parts(value: Any) -> tuple[int | None, int | None]:
    if not isinstance(value, str):
        return None, None
    match = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)\s*", value)
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def count_summary(
    public_sdk: dict[str, Any],
    *,
    progress_ratio_keys: tuple[str, ...],
    promoted_keys: tuple[str, ...],
    remaining_keys: tuple[str, ...],
    total_keys: tuple[str, ...],
    nested_progress_keys: tuple[tuple[str, ...], ...] = (),
    nested_promoted_keys: tuple[tuple[str, ...], ...] = (),
    nested_remaining_keys: tuple[tuple[str, ...], ...] = (),
    nested_total_keys: tuple[tuple[str, ...], ...] = (),
) -> dict[str, Any]:
    progress_ratio = next(
        (
            public_sdk.get(key)
            for key in progress_ratio_keys
            if isinstance(public_sdk.get(key), str)
        ),
        None,
    )
    if progress_ratio is None:
        progress_ratio = next(
            (
                nested_get(public_sdk, *keys)
                for keys in nested_progress_keys
                if isinstance(nested_get(public_sdk, *keys), str)
            ),
            None,
        )

    promoted = first_int(
        *(public_sdk.get(key) for key in promoted_keys),
        *(nested_get(public_sdk, *keys) for keys in nested_promoted_keys),
    )
    remaining = first_int(
        *(public_sdk.get(key) for key in remaining_keys),
        *(nested_get(public_sdk, *keys) for keys in nested_remaining_keys),
    )
    total = first_int(
        *(public_sdk.get(key) for key in total_keys),
        *(nested_get(public_sdk, *keys) for keys in nested_total_keys),
    )

    ratio_promoted, ratio_total = ratio_parts(progress_ratio)
    if promoted is None:
        promoted = ratio_promoted
    if total is None:
        total = ratio_total
    if remaining is None and promoted is not None and total is not None:
        remaining = max(total - promoted, 0)
    if total is None and promoted is not None and remaining is not None:
        total = promoted + remaining

    return {
        "total": total,
        "promoted_for_claim_count": promoted,
        "remaining_for_claim_count": remaining,
        "progress_ratio": progress_ratio,
        "ready": bool(total is not None and promoted == total and remaining == 0),
    }


def sdk_counts(public_sdk: dict[str, Any]) -> dict[str, Any]:
    return count_summary(
        public_sdk,
        progress_ratio_keys=(
            "complete_sdk_progress_ratio",
            "complete_sdk_claim_progress_ratio",
            "complete_sdk_blockers_promoted_for_claim_ratio",
        ),
        promoted_keys=("complete_sdk_blockers_promoted_for_claim_count",),
        remaining_keys=("complete_sdk_blockers_remaining_for_claim_count",),
        total_keys=("complete_sdk_blocker_total", "complete_sdk_blockers_total"),
        nested_progress_keys=(
            ("v1_sdk_progress", "complete_sdk_progress_ratio"),
            ("complete_sdk_blocker_claim_accounting", "progress_ratio"),
        ),
        nested_promoted_keys=(
            ("v1_sdk_progress", "complete_sdk_blockers_promoted_for_claim_count"),
            ("complete_sdk_blocker_claim_accounting", "promoted_for_claim_count"),
        ),
        nested_remaining_keys=(
            ("v1_sdk_progress", "complete_sdk_blockers_remaining_for_claim_count"),
            ("complete_sdk_blocker_claim_accounting", "remaining_for_claim_count"),
        ),
        nested_total_keys=(
            ("v1_sdk_progress", "complete_sdk_blocker_total"),
            ("v1_sdk_progress", "complete_sdk_blockers_total"),
            ("complete_sdk_blocker_claim_accounting", "total"),
        ),
    )


def p0_counts(public_sdk: dict[str, Any]) -> dict[str, Any]:
    return count_summary(
        public_sdk,
        progress_ratio_keys=(
            "p0_dependency_chain_progress_ratio",
            "p0_dependency_chain_claim_progress_ratio",
            "p0_chain_progress_ratio",
        ),
        promoted_keys=(
            "p0_dependency_chain_promoted_for_claim_count",
            "p0_chain_promoted_count",
        ),
        remaining_keys=("p0_dependency_chain_remaining_for_claim_count",),
        total_keys=("p0_dependency_chain_total", "p0_chain_total"),
        nested_progress_keys=(
            ("v1_sdk_progress", "p0_dependency_chain_progress_ratio"),
            ("v1_sdk_progress", "p0_dependency_chain_claim_progress_ratio"),
            ("p0_dependency_chain_claim_accounting", "progress_ratio"),
        ),
        nested_promoted_keys=(
            ("v1_sdk_progress", "p0_dependency_chain_promoted_for_claim_count"),
            ("v1_sdk_progress", "p0_chain_promoted_count"),
            ("p0_dependency_chain_claim_accounting", "promoted_for_claim_count"),
        ),
        nested_remaining_keys=(
            ("v1_sdk_progress", "p0_dependency_chain_remaining_for_claim_count"),
            ("p0_dependency_chain_claim_accounting", "remaining_for_claim_count"),
        ),
        nested_total_keys=(
            ("v1_sdk_progress", "p0_dependency_chain_total"),
            ("v1_sdk_progress", "p0_chain_total"),
            ("p0_dependency_chain_claim_accounting", "total"),
        ),
    )


def route_blockers(
    current_route_blocker: Any,
    remaining_route_blockers: list[str],
) -> set[str]:
    blockers = set(remaining_route_blockers)
    if isinstance(current_route_blocker, str) and current_route_blocker:
        blockers.add(current_route_blocker)
    return blockers


def remaining_claim_surfaces(
    public_sdk: dict[str, Any],
    *,
    counts: dict[str, Any],
    source_paths: tuple[tuple[str, ...], ...],
    fallback_surfaces: tuple[str, ...],
) -> list[str]:
    surfaces = first_string_list_from_paths(public_sdk, source_paths)
    if surfaces:
        return surfaces
    remaining = int_or_none(counts.get("remaining_for_claim_count"))
    total = int_or_none(counts.get("total"))
    if remaining == len(fallback_surfaces) or (
        remaining == total == len(fallback_surfaces)
    ):
        return list(fallback_surfaces)
    return []


def operator_context_source_status(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"present": True}
    return {
        key: value.get(key)
        for key in (
            "schema",
            "status",
            "state",
            "mode",
            "ready",
            "classification",
            "source_kind",
            "ready_scope",
            "readiness_scope",
        )
        if key in value
    }


def operator_context_summary(public_sdk: dict[str, Any]) -> dict[str, Any]:
    contexts: list[dict[str, Any]] = []
    for context_id, label, source_keys in OPERATOR_CONTEXT_SOURCE_KEYS:
        present_keys = [key for key in source_keys if key in public_sdk]
        if not present_keys:
            continue

        source_overclaimed_flags: list[str] = []
        source_overclaimed_progress_flags: list[str] = []
        source_statuses: dict[str, Any] = {}
        for key in present_keys:
            source_value = public_sdk.get(key)
            source_payload = source_value if isinstance(source_value, dict) else {"value": source_value}
            source_statuses[key] = operator_context_source_status(source_value)
            overclaimed_flags, overclaimed_progress_flags = source_alias_overclaim_paths(
                source_payload,
                false_keys=set(FAIL_CLOSED_ACTION_FALSE_FLAGS) | set(PACKAGE_SHAPE_FALSE_FLAGS),
                zero_keys=set(FAIL_CLOSED_ACTION_ZERO_FIELDS) | set(PACKAGE_SHAPE_ZERO_FIELDS),
                initial_non_counting_context=True,
            )
            source_overclaimed_flags.extend(
                f"{key}.{flag}" for flag in overclaimed_flags
            )
            source_overclaimed_progress_flags.extend(
                f"{key}.{flag}" for flag in overclaimed_progress_flags
            )

        context = {
            "id": context_id,
            "label": label,
            "source_keys": present_keys,
            "source_statuses": source_statuses,
            "operator_context_only": True,
            "status_report_only": True,
            "mentioned_as_operator_context": True,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_evidence": False,
            "counts_toward_sdk": False,
            "counts_toward_p0_dependency_chain": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_v1_completion": False,
            "approved_runtime_evidence_ready": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "stable_claim_allowed": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
            "v1_completion_contribution": 0,
            "non_claim": (
                f"{label} may be mentioned as operator context only; it does not "
                "satisfy approved runtime evidence, SDK/P0 progress, runtime "
                "readiness, public SDK readiness, release readiness, or stable SDK claims."
            ),
        }
        if source_overclaimed_flags:
            context["source_overclaimed_authorization_or_claim_flags"] = sorted(
                set(source_overclaimed_flags)
            )
        if source_overclaimed_progress_flags:
            context["source_overclaimed_progress_flags"] = sorted(
                set(source_overclaimed_progress_flags)
            )
        contexts.append(context)

    return {
        "schema": "obelisk.sdk-status-operator-context-summary.v1",
        "status_report_only": True,
        "operator_context_only": True,
        "context_count": len(contexts),
        "context_ids": [context["id"] for context in contexts],
        "contexts": contexts,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_v1_completion": False,
        "approved_runtime_evidence_ready": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_claim_allowed": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "v1_completion_contribution": 0,
        "non_claim": (
            "Operator context summary only; passive monitor, beta notice, package-shape, "
            "and scoped non-complete release-statement context remain non-evidence and "
            "zero-progress inputs."
        ),
    }


def first_present_value(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if value == "":
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        return value
    return None


def first_present_nested_value(
    payload: dict[str, Any],
    paths: tuple[tuple[str, ...], ...],
) -> Any:
    for path in paths:
        value = nested_get(payload, *path)
        if value is None:
            continue
        if value == "":
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        return value
    return None


def runtime_evidence_status_explicit_overclaims(
    source: dict[str, Any],
) -> tuple[list[str], list[str]]:
    overclaimed_flags: list[str] = []
    overclaimed_progress: list[str] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                item_path = f"{path}.{key}" if path else str(key)
                key_name = normalized_alias_key(key)
                if key_name in RUNTIME_EVIDENCE_STATUS_FALSE_KEYS and alias_value_is_positive(
                    item
                ):
                    overclaimed_flags.append(item_path)
                if key_name in RUNTIME_EVIDENCE_STATUS_ZERO_KEYS and progress_value_is_nonzero(
                    item
                ):
                    overclaimed_progress.append(item_path)
                visit(item, item_path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")

    visit(source, "")
    return sorted(set(overclaimed_flags)), sorted(set(overclaimed_progress))


def current_live_diagnostic_non_progress_fields() -> dict[str, Any]:
    return {
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "accepted_lifecycle_events_count_as_approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "server_operations_authorized": False,
        "runtime_capture_authorized": False,
        "live_ops_authorized": False,
        "reads_live_logs": False,
        "read_live_logs": False,
        "discord_authorized": False,
        "publication_authorized": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "sdk_progress": 0,
        "p0_progress": 0,
    }


def stale_operator_supplied_live_diagnostic_blockers() -> list[dict[str, Any]]:
    common = current_live_diagnostic_non_progress_fields()
    return [
        {
            "id": "theisland_active_player_observer_only_no_accepted_lifecycle_event",
            "blocker": "active_player_observer_only_no_accepted_lifecycle_event",
            "target": {"instance": "arkserver2", "map": "TheIsland"},
            "player_count_current": 1,
            "players_detected": True,
            "observer_enabled": True,
            "observer_only": True,
            "accepted_lifecycle_event_count": 0,
            "accepted_lifecycle_roles": [],
            "missing_accepted_lifecycle_roles": list(
                REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES
            ),
            "next_status_input_needed": (
                "same-window accepted lifecycle event triplet or window-end "
                "non-evidence classification"
            ),
            **common,
        },
        {
            "id": "ragnarok_diagnostic_fname_drift_blocks_accepted_events",
            "blocker": "diagnostic_fname_drift_blocks_accepted_events",
            "target": {"instance": "arkserver", "map": "Ragnarok"},
            "diagnostic_fname_mismatch_lines_present": True,
            "diagnostic_fname_drift": True,
            "accepted_lifecycle_event_count": 0,
            "accepted_lifecycle_roles": [],
            "next_status_input_needed": (
                "resolve or avoid diagnostic FName drift before treating lifecycle "
                "lines as accepted copied observer events"
            ),
            **common,
        },
    ]


def default_current_live_diagnostic_blockers_context() -> dict[str, Any]:
    stale_blockers = stale_operator_supplied_live_diagnostic_blockers()
    return {
        "schema": CURRENT_LIVE_DIAGNOSTIC_BLOCKERS_SCHEMA,
        "status": "stale_operator_supplied_context_only",
        "source": "operator_supplied_current_redacted_state",
        "source_freshness": "stale_operator_supplied",
        "current_posture_input_present": False,
        "current_live_state_source": False,
        "stale_operator_supplied_context": True,
        "stale_operator_supplied_blockers_suppressed": True,
        "stale_operator_supplied_next_blockers": stale_blockers,
        "stale_operator_supplied_next_blocker_ids": [
            str(blocker["id"]) for blocker in stale_blockers
        ],
        "planner_did_not_read_live_logs": True,
        "status_report_only": True,
        "blocker_context_only": True,
        "diagnostic_non_evidence": True,
        "active_ark_server_count": None,
        "active_server_targets": [],
        "inactive_or_unknown_targets": [],
        "current_route_blocker": APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER,
        "next_blockers": [],
        "next_blocker_ids": [],
        "primary_next_blocker": None,
        "secondary_next_blocker": None,
        "required_accepted_lifecycle_roles": list(
            REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES
        ),
        "approved_runtime_evidence_unlocks_after": (
            "checker-accepted copied runtime principal lifecycle evidence bundle"
        ),
        "non_claim": (
            "Stale operator-supplied redacted live state is retained only as "
            "historical diagnostic context and is not presented as current live "
            "posture. None of this is SDK/P0 progress, approved runtime evidence, "
            "runtime readiness, public SDK readiness, or live authorization."
        ),
        **current_live_diagnostic_non_progress_fields(),
    }


def value_is_explicitly_false_or_disabled(value: Any) -> bool:
    if value is False or value == 0:
        return True
    if isinstance(value, str):
        normalized = normalized_alias_key(value)
        return normalized in {
            "0",
            "absent",
            "disabled",
            "false",
            "none",
            "no",
            "not_present",
            "off",
            "unset",
        }
    return False


def value_is_zero_or_disabled(value: Any) -> bool:
    if value_is_explicitly_false_or_disabled(value):
        return True
    count = int_or_none(value)
    return count == 0


PROMOTABLE_CURRENT_POSTURE_TRUE_KEYS = {
    "active_promotable_observer_window",
    "current_observer_window_promotable",
    "observer_window_promotable",
    "promotable_observer_posture",
    "promotable_observer_window",
    "promotable_player_principal_observer_window",
    "posture_promotable",
}
CURRENT_POSTURE_OBSERVER_TRUE_KEYS = {
    "observer_enabled",
    "observer_gate_enabled",
    "player_principal_lifecycle_observer_enabled",
}
NO_DIAGNOSTIC_POSTURE_KEYS = {
    "diagnostic_candidate_lines_present",
    "diagnostic_candidate_env_present",
    "diagnostic_candidates",
    "diagnostic_candidates_enabled",
    "diagnostic_candidates_present",
    "diagnostic_env_present",
    "diagnostic_fname_drift",
    "diagnostic_fname_mismatch_lines_present",
    "lifecycle_diagnostic_candidates_enabled",
    "observer_env_contains_diagnostic_candidates",
    "player_principal_lifecycle_diagnostic_candidates_enabled",
}
NO_DIAGNOSTIC_COUNT_KEYS = {
    "diagnostic_candidate_count",
    "diagnostic_candidates_count",
    "player_principal_lifecycle_diagnostic_count",
    "player_principal_lifecycle_diagnostic_candidates_count",
}
CURRENT_POSTURE_CONTAINER_TOKENS = (
    "current_live_posture",
    "current_runtime_posture",
    "live_posture",
    "observer_posture",
    "observer_window_posture",
    "posture",
    "preflight_post",
    "preflight_post_restart",
    "runtime_posture",
)


def iter_nested_dicts(
    value: Any,
    path: tuple[str, ...] = (),
) -> list[tuple[tuple[str, ...], dict[str, Any]]]:
    if isinstance(value, dict):
        items = [(path, value)]
        for key, item in value.items():
            items.extend(iter_nested_dicts(item, (*path, str(key))))
        return items
    if isinstance(value, list):
        items = []
        for index, item in enumerate(value):
            items.extend(iter_nested_dicts(item, (*path, str(index))))
        return items
    return []


def first_current_posture_target(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("target", "target_hint", "current_target", "live_target"):
        target = payload.get(key)
        if isinstance(target, dict):
            return {
                target_key: target.get(target_key)
                for target_key in ("instance", "map", "query_port")
                if target.get(target_key) is not None
            }
    instance = payload.get("instance")
    game_map = payload.get("map") or payload.get("game_map")
    if instance or game_map:
        return {
            key: value
            for key, value in (("instance", instance), ("map", game_map))
            if value is not None
        }
    return {}


def current_promotable_no_diagnostic_posture(
    source: dict[str, Any],
) -> dict[str, Any] | None:
    for path, payload in iter_nested_dicts(source):
        normalized_keys = {normalized_alias_key(key): key for key in payload}
        status_values = [
            value
            for value in (
                compact_string(payload.get(key))
                for key in (
                    "status",
                    "state",
                    "classification",
                    "source_kind",
                    "ready_scope",
                    "readiness_scope",
                )
                if key in payload
            )
            if value is not None
        ]
        path_text = ".".join(normalized_alias_key(part) for part in path)
        status_text = " ".join(normalized_alias_key(value) for value in status_values)
        container_mentions_posture = any(
            token in path_text for token in CURRENT_POSTURE_CONTAINER_TOKENS
        )
        has_promotable = "promotable" in status_text or any(
            alias_value_is_positive(payload.get(source_key))
            for key, source_key in normalized_keys.items()
            if key in PROMOTABLE_CURRENT_POSTURE_TRUE_KEYS
        )
        has_observer = "observer" in status_text or any(
            alias_value_is_positive(payload.get(source_key))
            for key, source_key in normalized_keys.items()
            if key in CURRENT_POSTURE_OBSERVER_TRUE_KEYS
        )
        no_diagnostic = "no_diagnostic" in status_text or any(
            value_is_explicitly_false_or_disabled(payload.get(source_key))
            for key, source_key in normalized_keys.items()
            if key in NO_DIAGNOSTIC_POSTURE_KEYS
        ) or any(
            value_is_zero_or_disabled(payload.get(source_key))
            for key, source_key in normalized_keys.items()
            if key in NO_DIAGNOSTIC_COUNT_KEYS
        )
        if not (has_promotable and has_observer and no_diagnostic):
            continue
        if not (container_mentions_posture or "promotable" in status_text):
            continue
        return {
            "path": ".".join(path),
            "status": compact_string(payload.get("status")),
            "classification": compact_string(payload.get("classification")),
            "target": first_current_posture_target(payload),
            "observer_window_promotable": True,
            "diagnostic_candidates_present": False,
            "source_report_only": True,
        }
    return None


def stale_operator_supplied_context(context: dict[str, Any]) -> bool:
    freshness = compact_string(context.get("source_freshness"))
    if freshness and normalized_alias_key(freshness).startswith("stale"):
        return True
    return context.get("source") == "operator_supplied_current_redacted_state"


def suppress_stale_operator_supplied_diagnostics(
    context: dict[str, Any],
    *,
    posture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = dict(context)
    blockers = [
        item for item in normalized.get("next_blockers", []) if isinstance(item, dict)
    ]
    if not blockers:
        blockers = [
            item
            for item in normalized.get("stale_operator_supplied_next_blockers", [])
            if isinstance(item, dict)
        ]
    active_targets = normalized.get("active_server_targets")
    inactive_targets = normalized.get("inactive_or_unknown_targets")
    normalized["stale_operator_supplied_next_blockers"] = blockers
    normalized["stale_operator_supplied_next_blocker_ids"] = [
        str(blocker.get("id") or blocker.get("blocker"))
        for blocker in blockers
        if blocker.get("id") or blocker.get("blocker")
    ]
    normalized["stale_operator_supplied_active_ark_server_count"] = normalized.get(
        "active_ark_server_count"
    )
    normalized["stale_operator_supplied_active_server_targets"] = (
        active_targets if isinstance(active_targets, list) else []
    )
    normalized["stale_operator_supplied_inactive_or_unknown_targets"] = (
        inactive_targets if isinstance(inactive_targets, list) else []
    )
    normalized["next_blockers"] = []
    normalized["next_blocker_ids"] = []
    normalized["primary_next_blocker"] = None
    normalized["secondary_next_blocker"] = None
    normalized["active_ark_server_count"] = None
    normalized["active_server_targets"] = []
    normalized["inactive_or_unknown_targets"] = []
    normalized["source_freshness"] = "stale_operator_supplied"
    normalized["current_live_state_source"] = False
    normalized["stale_operator_supplied_context"] = True
    normalized["stale_operator_supplied_blockers_suppressed"] = True
    normalized["status"] = "stale_operator_supplied_context_only"
    if posture is not None:
        target = posture.get("target")
        normalized["status"] = "current_posture_supersedes_stale_operator_diagnostics"
        normalized["source_freshness"] = (
            "stale_operator_supplied_superseded_by_current_posture"
        )
        normalized["current_posture_input_present"] = True
        normalized["current_posture_no_diagnostic"] = True
        normalized["current_posture_summary"] = posture
        normalized["active_server_targets"] = (
            [target] if isinstance(target, dict) and target else []
        )
    else:
        normalized["current_posture_input_present"] = False
    normalized["non_claim"] = (
        "Stale operator-supplied redacted live diagnostic blockers are suppressed "
        "from current status output. Newer posture context, when present, is still "
        "status-only and does not satisfy approved runtime evidence, SDK/P0 "
        "progress, runtime readiness, public SDK readiness, or live authorization."
    )
    return normalized


def current_posture_no_diagnostic_context(
    posture: dict[str, Any],
) -> dict[str, Any]:
    target = posture.get("target")
    return {
        "schema": CURRENT_LIVE_DIAGNOSTIC_BLOCKERS_SCHEMA,
        "status": "current_posture_no_live_diagnostic_blockers",
        "source": "runtime_evidence_status_current_posture",
        "source_freshness": "current_posture_input",
        "current_posture_input_present": True,
        "current_live_state_source": True,
        "current_posture_no_diagnostic": True,
        "current_posture_summary": posture,
        "stale_operator_supplied_context": False,
        "stale_operator_supplied_blockers_suppressed": False,
        "planner_did_not_read_live_logs": True,
        "status_report_only": True,
        "blocker_context_only": True,
        "diagnostic_non_evidence": True,
        "active_ark_server_count": None,
        "active_server_targets": (
            [target] if isinstance(target, dict) and target else []
        ),
        "inactive_or_unknown_targets": [],
        "current_route_blocker": APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER,
        "next_blockers": [],
        "next_blocker_ids": [],
        "primary_next_blocker": None,
        "secondary_next_blocker": None,
        "required_accepted_lifecycle_roles": list(
            REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES
        ),
        "approved_runtime_evidence_unlocks_after": (
            "checker-accepted copied runtime principal lifecycle evidence bundle"
        ),
        "non_claim": (
            "Current posture input reports a promotable observer posture with no "
            "diagnostic candidates, but this remains status-only context and does "
            "not satisfy approved runtime evidence, SDK/P0 progress, runtime "
            "readiness, public SDK readiness, or live authorization."
        ),
        **current_live_diagnostic_non_progress_fields(),
    }


def force_current_live_diagnostic_context_non_claim(
    context: dict[str, Any],
) -> dict[str, Any]:
    normalized = sanitize_non_counting_alias_payload(
        context,
        false_keys=set(RUNTIME_EVIDENCE_STATUS_FALSE_KEYS),
        zero_keys=set(RUNTIME_EVIDENCE_STATUS_ZERO_KEYS)
        | {"sdk_progress", "p0_progress"},
        initial_non_counting_context=True,
    )
    normalized.update(current_live_diagnostic_non_progress_fields())
    blockers = normalized.get("next_blockers")
    if isinstance(blockers, list):
        normalized["next_blockers"] = [
            {
                **item,
                **current_live_diagnostic_non_progress_fields(),
            }
            for item in blockers
            if isinstance(item, dict)
        ]
    normalized["schema"] = CURRENT_LIVE_DIAGNOSTIC_BLOCKERS_SCHEMA
    normalized["status_report_only"] = True
    normalized["blocker_context_only"] = True
    normalized["diagnostic_non_evidence"] = True
    normalized["planner_did_not_read_live_logs"] = True
    normalized["current_route_blocker"] = APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER
    return normalized


def current_live_diagnostic_blockers_summary(
    source: dict[str, Any] | None,
) -> dict[str, Any]:
    default = default_current_live_diagnostic_blockers_context()
    if not isinstance(source, dict):
        return default
    posture = current_promotable_no_diagnostic_posture(source)
    source_context = source.get("current_live_diagnostic_blockers")
    if not isinstance(source_context, dict):
        source_context = nested_get(
            source,
            "operator_action_summary",
            "blocking_inputs",
            "current_live_diagnostic_blockers",
        )
    if not isinstance(source_context, dict):
        if posture is not None:
            return force_current_live_diagnostic_context_non_claim(
                current_posture_no_diagnostic_context(posture)
            )
        return default
    merged = {**default, **source_context}
    if stale_operator_supplied_context(merged):
        return force_current_live_diagnostic_context_non_claim(
            suppress_stale_operator_supplied_diagnostics(merged, posture=posture)
        )
    return force_current_live_diagnostic_context_non_claim(merged)


def runtime_evidence_window_summary(
    source: dict[str, Any] | None,
    *,
    source_path: Path | str | None = None,
    source_kind: str | None = None,
) -> dict[str, Any]:
    source_present = isinstance(source, dict)
    source_path_text = str(source_path) if source_path is not None else None
    false_flags = {
        "ready": False,
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "approved_runtime_evidence_accepted_by_checker": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_claim_allowed": False,
        "stable_sdk_ready": False,
        "v1_completion_ready": False,
        "promotion_ready": False,
        "publication_authorized": False,
        "plugin_hub_ready": False,
        "live_ops_authorized": False,
        "server_operations_authorized": False,
        "workspace_writes_authorized": False,
        "runtime_capture_authorized": False,
        "reads_live_logs": False,
        "read_live_logs": False,
        "discord_authorized": False,
        "authorizes_runtime_work": False,
        "authorizes_server_operations": False,
        "authorizes_workspace_writes": False,
    }
    zero_fields = {
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "complete_sdk_progress_contribution": 0,
        "p0_dependency_chain_progress_contribution": 0,
        "public_sdk_progress_contribution": 0,
        "runtime_progress_contribution": 0,
        "sdk_progress_contribution": 0,
        "v1_completion_contribution": 0,
    }
    base: dict[str, Any] = {
        "schema": "obelisk.sdk-status-runtime-evidence-window-summary.v1",
        "status_report_only": True,
        "offline_status_artifact_only": True,
        "operator_context_only": True,
        "non_evidence": True,
        "source_present": source_present,
        "provided": source_present,
        "source_path": source_path_text,
        "source_kind": source_kind,
        "source_schema": source.get("schema") if source_present else None,
        "status": "not_provided",
        "source_status": source.get("status") if source_present else None,
        "window_state": "not_supplied",
        "route_blocker": APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER,
        "after_runtime_evidence": IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER,
        "next_status_input_needed": None,
        "run_id": None,
        "missing_lifecycle_event_roles": [],
        "missing_required_artifacts": [],
        "missing_copied_lifecycle_event_triplet_labels": [],
        "player_availability_classification": None,
        "players_detected": False,
        "no_players_currently_detected": False,
        "player_context": "unknown",
        "known_player_counts_by_target": {},
        "post_reboot_passive_monitor_log_supplied": False,
        "monitor_latest_tick_utc": None,
        "monitor_query_targets": [],
        "confirmed_beta_notice_json_supplied": False,
        "confirmed_beta_notice_completed": False,
        "copy_ready_json_supplied": False,
        "copy_ready_status": None,
        "copy_readiness": None,
        "copy_ready_roles_present": [],
        "copy_ready_missing_roles": [],
        "copy_ready_active_observer_only_no_role_window": False,
        "current_live_diagnostic_blockers": (
            default_current_live_diagnostic_blockers_context()
        ),
        "first_machine_next_action": {
            "present": False,
            "action": None,
            "action_kind": None,
            "command_status": "NOT PROVIDED",
            "exact_command_available": False,
        },
        "source_overclaimed_readiness_or_authorization_flags": [],
        "source_overclaimed_progress_flags": [],
        "non_claim": (
            "Runtime-evidence window status is offline operator context only. It "
            "does not satisfy approved runtime evidence, SDK/P0 progress, runtime "
            "readiness, public SDK readiness, stable SDK claims, live ops, Discord, "
            "publication, or workspace writes."
        ),
    }
    base.update(false_flags)
    base.update(zero_fields)
    if not source_present:
        return base

    assert isinstance(source, dict)
    operator_summary = dict_or_empty(source.get("operator_action_summary"))
    blocking_inputs = dict_or_empty(operator_summary.get("blocking_inputs"))
    operator_inputs = dict_or_empty(operator_summary.get("operator_context_inputs"))
    resume_context = dict_or_empty(operator_summary.get("resume_context"))
    closure = dict_or_empty(source.get("closure"))
    monitor = dict_or_empty(source.get("post_reboot_passive_monitor"))
    beta_notice = dict_or_empty(source.get("confirmed_beta_notice"))
    copy_ready = dict_or_empty(source.get("copy_ready_log"))
    player_availability = dict_or_empty(source.get("runtime_player_availability"))
    if not player_availability:
        player_availability = dict_or_empty(operator_inputs.get("runtime_player_availability"))
    if not player_availability:
        player_availability = dict_or_empty(operator_inputs.get("player_presence_context"))
    first_action = dict_or_empty(source.get("first_machine_next_action"))
    if not first_action:
        first_action = dict_or_empty(source.get("exact_next_command"))

    source_status = compact_string(source.get("status"))
    source_overclaims, source_progress_overclaims = (
        runtime_evidence_status_explicit_overclaims(source)
    )
    missing_roles = (
        string_list(closure.get("missing_lifecycle_event_roles"))
        or string_list(blocking_inputs.get("missing_lifecycle_event_roles"))
        or string_list(operator_inputs.get("copy_ready_missing_roles"))
    )
    missing_artifacts = (
        string_list(closure.get("missing_required_artifacts"))
        or string_list(blocking_inputs.get("missing_required_artifacts"))
    )
    missing_triplet_labels = (
        string_list(closure.get("missing_copied_lifecycle_event_triplet_labels"))
        or string_list(blocking_inputs.get("missing_copied_lifecycle_event_triplet_labels"))
    )
    route_blocker = compact_string(
        first_present_value(
            nested_get(source, "route_gate", "current_route_blocker"),
            nested_get(source, "route_gate", "current_blocker"),
            blocking_inputs.get("route_blocker"),
        )
    )
    player_classification = compact_string(
        first_present_value(
            player_availability.get("classification"),
            operator_inputs.get("player_availability_classification"),
        )
    )
    players_detected = bool(player_availability.get("players_detected"))
    no_players = bool(
        player_availability.get("no_players_currently_detected")
        or operator_inputs.get("no_players_currently_detected")
    )
    if players_detected:
        player_context = "detected"
    elif no_players:
        player_context = "none_currently_detected"
    else:
        player_context = "unknown"
    monitor_query_targets = compact_string_values(
        first_present_value(
            operator_inputs.get("monitor_query_targets"),
            list(dict_or_empty(monitor.get("query_status_by_target")).keys()),
        )
    )
    copy_active_observer_only = bool(
        source.get("active_observer_only_no_role_window")
        or copy_ready.get("active_observer_only_no_role_window")
        or operator_inputs.get("copy_ready_active_observer_only_no_role_window")
    )
    copy_readiness = compact_string(
        first_present_value(
            copy_ready.get("copy_readiness"),
            operator_inputs.get("copy_readiness"),
            copy_ready.get("status"),
            operator_inputs.get("copy_ready_status"),
        )
    )
    if first_action:
        first_action_summary = {
            "present": bool(first_action.get("present", True)),
            "action": first_action.get("action"),
            "action_kind": first_action.get("action_kind"),
            "command_status": first_action.get("command_status", "NOT PROVIDED"),
            "exact_command_available": bool(first_action.get("exact_command_available")),
        }
    else:
        first_action_summary = base["first_machine_next_action"]
    window_state = source_status or "reported_context_only"
    current_live_blockers = current_live_diagnostic_blockers_summary(source)

    base.update(
        {
            "status": source_status or "unknown",
            "source_status": source.get("status"),
            "window_state": window_state,
            "route_blocker": route_blocker or APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER,
            "after_runtime_evidence": IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER,
            "next_status_input_needed": compact_string(
                first_present_value(
                    nested_get(source, "resume_context", "next_status_input_needed"),
                    resume_context.get("next_status_input_needed"),
                    first_action.get("next_status_input_needed"),
                )
            ),
            "run_id": compact_string(
                first_present_value(operator_summary.get("run_id"), closure.get("run_id"))
            ),
            "missing_lifecycle_event_roles": missing_roles,
            "missing_required_artifacts": missing_artifacts,
            "missing_copied_lifecycle_event_triplet_labels": missing_triplet_labels,
            "player_availability_classification": player_classification,
            "players_detected": players_detected,
            "no_players_currently_detected": no_players,
            "player_context": player_context,
            "known_player_counts_by_target": dict_or_empty(
                player_availability.get("known_player_counts_by_target")
            ),
            "post_reboot_passive_monitor_log_supplied": bool(
                monitor.get("present")
                or operator_inputs.get("post_reboot_passive_monitor_log_supplied")
            ),
            "monitor_latest_tick_utc": compact_string(
                first_present_value(
                    monitor.get("monitor_latest_tick_utc"),
                    operator_inputs.get("monitor_latest_tick_utc"),
                )
            ),
            "monitor_query_targets": monitor_query_targets,
            "confirmed_beta_notice_json_supplied": bool(
                beta_notice.get("present")
                or operator_inputs.get("confirmed_beta_notice_json_supplied")
            ),
            "confirmed_beta_notice_completed": bool(
                beta_notice.get("completed")
                or operator_inputs.get("confirmed_beta_notice_completed")
            ),
            "copy_ready_json_supplied": bool(
                copy_ready.get("present") or operator_inputs.get("copy_ready_json_supplied")
            ),
            "copy_ready_status": compact_string(
                first_present_value(
                    copy_ready.get("status"),
                    operator_inputs.get("copy_ready_status"),
                )
            ),
            "copy_readiness": copy_readiness,
            "copy_ready_roles_present": compact_string_values(
                first_present_value(
                    copy_ready.get("roles_present"),
                    operator_inputs.get("copy_ready_roles_present"),
                )
            ),
            "copy_ready_missing_roles": compact_string_values(
                first_present_value(
                    copy_ready.get("missing_roles"),
                    operator_inputs.get("copy_ready_missing_roles"),
                )
            ),
            "copy_ready_active_observer_only_no_role_window": copy_active_observer_only,
            "current_live_diagnostic_blockers": current_live_blockers,
            "first_machine_next_action": first_action_summary,
            "source_overclaimed_readiness_or_authorization_flags": source_overclaims,
            "source_overclaimed_progress_flags": source_progress_overclaims,
        }
    )
    return base


def principal_start_end_runtime_evidence_summary(
    source: dict[str, Any] | None,
    *,
    source_path: Path | str | None = None,
    source_kind: str | None = None,
) -> dict[str, Any]:
    source_present = isinstance(source, dict)
    source_path_text = str(source_path) if source_path is not None else None
    if not source_present:
        return {
            "schema": "obelisk.sdk-status-principal-start-end-runtime-evidence-summary.v1",
            "status_report_only": True,
            "contract_review_input_only": True,
            "source_present": False,
            "provided": False,
            "source_path": source_path_text,
            "source_kind": source_kind,
            "accepted_for_contract_review": False,
            "principal_start_end_runtime_evidence_present": False,
            "principal_start_end_runtime_evidence_ready": False,
            "source_ready": False,
            "source_accepted_for_contract_review": False,
            "source_principal_start_end_runtime_evidence_present": False,
            "source_principal_start_end_runtime_evidence_ready": False,
            "resolved_inputs": [],
            "remaining_runtime_inputs": [PRINCIPAL_START_END_RESOLVED_INPUT],
            "does_not_resolve": sorted(PRINCIPAL_START_END_STRICT_UNRESOLVED_INPUTS),
            "next_review_blocker": "principal_start_end_runtime_evidence_missing",
            "approved_runtime_evidence": False,
            "approved_runtime_evidence_present": False,
            "approved_runtime_evidence_ready": False,
            "counts_as_approved_runtime_evidence": False,
            "runtime_evidence_ready": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "stable_claim_allowed": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "counts_toward_public_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_v1_completion": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
            "blockers": ["principal_start_end_runtime_evidence_missing"],
            "source_overclaimed_readiness_or_authorization_flags": [],
            "source_overclaimed_progress_flags": [],
            "non_claim": (
                "Principal start/end runtime evidence is absent; approved runtime "
                "principal lifecycle evidence remains missing."
            ),
        }

    assert isinstance(source, dict)
    blockers: list[str] = []

    def reject(reason: str) -> None:
        if reason not in blockers:
            blockers.append(reason)

    if source.get("schema") != PRINCIPAL_START_END_RUNTIME_EVIDENCE_SCHEMA:
        reject("principal_start_end_runtime_evidence_schema_mismatch")
    if source.get("ready_scope") != PRINCIPAL_START_END_READY_SCOPE:
        reject("principal_start_end_runtime_evidence_ready_scope_mismatch")
    for key in PRINCIPAL_START_END_REQUIRED_TRUE_KEYS:
        if source.get(key) is not True:
            reject(f"principal_start_end_runtime_evidence_{key}_not_true")
    if source.get("next_review_blocker") != IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER:
        reject("principal_start_end_runtime_evidence_next_blocker_mismatch")
    if source.get("resolved_inputs") != [PRINCIPAL_START_END_RESOLVED_INPUT]:
        reject("principal_start_end_runtime_evidence_resolved_inputs_mismatch")
    does_not_resolve = source.get("does_not_resolve")
    if not isinstance(does_not_resolve, list) or not set(
        PRINCIPAL_START_END_STRICT_UNRESOLVED_INPUTS
    ).issubset({item for item in does_not_resolve if isinstance(item, str)}):
        reject("principal_start_end_runtime_evidence_does_not_resolve_missing_strict_inputs")
    if source.get("blockers") not in ([], None):
        reject("principal_start_end_runtime_evidence_report_blockers_present")

    for key in PRINCIPAL_START_END_REQUIRED_FALSE_KEYS:
        if source.get(key) is not False:
            reject(f"principal_start_end_runtime_evidence_{key}_not_false")
    for key in PRINCIPAL_START_END_OPTIONAL_FALSE_KEYS:
        if key in source and source.get(key) is not False:
            reject(f"principal_start_end_runtime_evidence_{key}_not_false")
    diagnostic = source.get("diagnostic_coverage")
    if (
        isinstance(diagnostic, dict)
        and diagnostic.get("diagnostic_candidates_count_as_evidence") is not False
    ):
        reject(
            "principal_start_end_runtime_evidence_diagnostic_candidates_count_as_evidence_not_false"
        )

    source_overclaimed_flags, source_overclaimed_progress = source_alias_overclaim_paths(
        source,
        false_keys=set(PRINCIPAL_START_END_FALSE_KEYS),
        zero_keys=set(PRINCIPAL_START_END_ZERO_KEYS),
        initial_non_counting_context=False,
    )
    allowed_contract_review_flags = set(PRINCIPAL_START_END_REQUIRED_TRUE_KEYS)
    source_overclaimed_flags = [
        flag for flag in source_overclaimed_flags if flag not in allowed_contract_review_flags
    ]
    for flag in source_overclaimed_flags:
        reject(f"principal_start_end_runtime_evidence_overclaim:{flag}")
    for flag in source_overclaimed_progress:
        reject(f"principal_start_end_runtime_evidence_progress_overclaim:{flag}")

    accepted = not blockers
    return {
        "schema": "obelisk.sdk-status-principal-start-end-runtime-evidence-summary.v1",
        "status_report_only": True,
        "contract_review_input_only": True,
        "milestone": "principal_start_end_runtime_evidence",
        "source_present": True,
        "provided": True,
        "source_path": source_path_text,
        "source_kind": source_kind,
        "source_schema": source.get("schema"),
        "source_ready_scope": source.get("ready_scope"),
        "accepted_for_contract_review": accepted,
        "principal_start_end_runtime_evidence_present": accepted
        and source.get("principal_start_end_runtime_evidence_present") is True,
        "principal_start_end_runtime_evidence_ready": accepted
        and source.get("principal_start_end_runtime_evidence_ready") is True,
        "source_ready": alias_value_is_positive(source.get("ready")),
        "source_accepted_for_contract_review": alias_value_is_positive(
            source.get("accepted_for_contract_review")
        ),
        "source_principal_start_end_runtime_evidence_present": alias_value_is_positive(
            source.get("principal_start_end_runtime_evidence_present")
        ),
        "source_principal_start_end_runtime_evidence_ready": alias_value_is_positive(
            source.get("principal_start_end_runtime_evidence_ready")
        ),
        "resolved_inputs": [PRINCIPAL_START_END_RESOLVED_INPUT] if accepted else [],
        "remaining_runtime_inputs": []
        if accepted
        else [PRINCIPAL_START_END_RESOLVED_INPUT],
        "does_not_resolve": sorted(PRINCIPAL_START_END_STRICT_UNRESOLVED_INPUTS),
        "next_review_blocker": IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER
        if accepted
        else "principal_start_end_runtime_evidence_rejected",
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "runtime_evidence_ready": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "stable_claim_allowed": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "blockers": blockers,
        "source_overclaimed_readiness_or_authorization_flags": source_overclaimed_flags,
        "source_overclaimed_progress_flags": source_overclaimed_progress,
        "source_non_claims": list_or_empty(source.get("non_claims")),
        "non_claim": (
            "Principal start/end runtime evidence is a contract-review input only. "
            "It does not satisfy approved runtime principal lifecycle evidence, "
            "rejected-start/CheckJoin proof, SDK/P0 progress, runtime readiness, "
            "public SDK readiness, stable SDK claims, live ops, or publication."
        ),
    }


def multi_surface_beta_capture_pack_summary(
    source: dict[str, Any] | None,
    *,
    source_path: Path | str | None = None,
    source_kind: str | None = None,
) -> dict[str, Any]:
    source_present = isinstance(source, dict)
    source_path_text = str(source_path) if source_path is not None else None
    false_flags = {
        "ready": False,
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "public_header_allowed": False,
        "runtime_evidence_ready": False,
        "runtime_ready": False,
        "stable_claim_allowed": False,
        "stable_sdk_ready": False,
        "v1_completion_ready": False,
        "plugin_hub_ready": False,
        "publication_ready": False,
        "publication_authorized": False,
        "live_ops_authorized": False,
        "server_operations_authorized": False,
        "workspace_writes_authorized": False,
        "runtime_capture_authorized": False,
        "reads_live_logs": False,
        "read_live_logs": False,
        "discord_authorized": False,
    }
    zero_fields = {
        "complete_sdk_claim_progress_contribution": 0,
        "complete_sdk_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "p0_dependency_chain_progress_contribution": 0,
        "public_sdk_progress_contribution": 0,
        "runtime_progress_contribution": 0,
        "sdk_progress_contribution": 0,
        "v1_completion_contribution": 0,
    }
    base: dict[str, Any] = {
        "schema": "obelisk.sdk-status-multi-surface-beta-capture-pack-summary.v1",
        "status_report_only": True,
        "planning_only": True,
        "non_evidence": True,
        "source_present": source_present,
        "provided": source_present,
        "source_path": source_path_text,
        "source_kind": source_kind,
        "source_schema": source.get("schema") if source_present else None,
        "source_status": source.get("status") if source_present else None,
        "source_ready_scope": source.get("ready_scope") if source_present else None,
        "source_ready": (
            alias_value_is_positive(source.get("ready")) if source_present else False
        ),
        "status": "not_provided",
        "candidate_pack_validated": False,
        "candidate_pack_context": {},
        "context": {},
        "target": None,
        "target_binding_id": None,
        "pack_root": None,
        "candidate_surface_count": None,
        "surface_count": None,
        "blockers": [],
        "source_overclaimed_readiness_or_authorization_flags": [],
        "source_overclaimed_progress_flags": [],
        "non_claim": (
            "Multi-surface beta capture pack context is planning-only. It does not "
            "authorize runtime work, approve runtime evidence, change route blockers, "
            "or count toward SDK/P0 progress, public SDK readiness, runtime readiness, "
            "or stable SDK claims."
        ),
    }
    base.update(false_flags)
    base.update(zero_fields)
    if not source_present:
        return base

    assert isinstance(source, dict)
    blockers: list[str] = []

    def reject(reason: str) -> None:
        if reason not in blockers:
            blockers.append(reason)

    if source.get("schema") != MULTI_SURFACE_BETA_CAPTURE_PACK_CHECK_SCHEMA:
        reject("multi_surface_beta_capture_pack_schema_mismatch")
    if source.get("status") != MULTI_SURFACE_BETA_CAPTURE_PACK_VALIDATED_STATUS:
        reject("multi_surface_beta_capture_pack_status_mismatch")
    if source.get("ready_scope") != MULTI_SURFACE_BETA_CAPTURE_PACK_READY_SCOPE:
        reject("multi_surface_beta_capture_pack_ready_scope_mismatch")
    if source.get("ready") is not True:
        reject("multi_surface_beta_capture_pack_source_ready_not_true")
    if source.get("blockers") not in ([], None):
        reject("multi_surface_beta_capture_pack_source_blockers_present")

    target = source.get("target")
    if not isinstance(target, dict):
        reject("multi_surface_beta_capture_pack_target_missing")
        target = None

    target_binding_id = source.get("target_binding_id")
    if not isinstance(target_binding_id, str) or not target_binding_id:
        reject("multi_surface_beta_capture_pack_target_binding_id_missing")
        target_binding_id = None

    candidate_surface_count = int_or_none(source.get("candidate_surface_count"))
    if candidate_surface_count is None or candidate_surface_count <= 0:
        reject("multi_surface_beta_capture_pack_candidate_surface_count_invalid")
        candidate_surface_count = None

    for key in MULTI_SURFACE_BETA_CAPTURE_PACK_REQUIRED_FALSE_KEYS:
        if source.get(key) is not False:
            reject(f"multi_surface_beta_capture_pack_{key}_not_false")
    for key in MULTI_SURFACE_BETA_CAPTURE_PACK_OPTIONAL_FALSE_KEYS:
        if key in source and source.get(key) is not False:
            reject(f"multi_surface_beta_capture_pack_{key}_not_false")

    source_overclaimed_flags, source_overclaimed_progress = source_alias_overclaim_paths(
        source,
        false_keys=set(MULTI_SURFACE_BETA_CAPTURE_PACK_FALSE_KEYS),
        zero_keys=set(MULTI_SURFACE_BETA_CAPTURE_PACK_ZERO_KEYS),
        initial_non_counting_context=False,
    )
    source_overclaimed_flags = [
        flag
        for flag in source_overclaimed_flags
        if flag not in {"ready"} and not flag.endswith(".ready")
    ]
    for flag in source_overclaimed_flags:
        reject(f"multi_surface_beta_capture_pack_overclaim:{flag}")
    for flag in source_overclaimed_progress:
        reject(f"multi_surface_beta_capture_pack_progress_overclaim:{flag}")

    accepted = not blockers
    context = {
        "status": source.get("status"),
        "ready_scope": source.get("ready_scope"),
        "pack_root": source.get("pack_root"),
        "target": target,
        "target_binding_id": target_binding_id,
        "candidate_surface_count": candidate_surface_count,
        "surface_count": candidate_surface_count,
        "current_route_blocker": source.get("current_route_blocker"),
        "next_required_artifact": source.get("next_required_artifact"),
    }
    base.update(
        {
            "status": (
                MULTI_SURFACE_BETA_CAPTURE_PACK_VALIDATED_STATUS
                if accepted
                else "candidate_pack_rejected_for_status_report"
            ),
            "candidate_pack_validated": accepted,
            "candidate_pack_context": context if accepted else {},
            "context": context if accepted else {},
            "target": target if accepted else None,
            "target_binding_id": target_binding_id if accepted else None,
            "pack_root": source.get("pack_root") if accepted else None,
            "candidate_surface_count": candidate_surface_count if accepted else None,
            "surface_count": candidate_surface_count if accepted else None,
            "blockers": blockers,
            "source_overclaimed_readiness_or_authorization_flags": sorted(
                source_overclaimed_flags
            ),
            "source_overclaimed_progress_flags": sorted(source_overclaimed_progress),
            "source_non_claims": list_or_empty(source.get("non_claims")),
        }
    )
    return base


def discord_beta_bridge_config_summary(
    source: dict[str, Any] | None,
    *,
    source_path: Path | str | None = None,
    source_kind: str | None = None,
) -> dict[str, Any]:
    source_present = isinstance(source, dict)
    source_path_text = str(source_path) if source_path is not None else None
    false_flags = {
        "ready": False,
        "authorizes_discord": False,
        "discord_authorized": False,
        "authorizes_discord_send": False,
        "authorizes_rcon": False,
        "authorizes_server_start": False,
        "authorizes_server_stop": False,
        "authorizes_server_restart": False,
        "authorizes_marker_or_env_changes": False,
        "authorizes_live_log_reads": False,
        "authorizes_runtime_capture": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "stable_sdk_ready": False,
        "plugin_hub_ready": False,
        "publication_ready": False,
    }
    zero_fields = {
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "sdk_progress_contribution": 0,
    }
    base: dict[str, Any] = {
        "schema": "obelisk.sdk-status-discord-beta-bridge-config-summary.v1",
        "status_report_only": True,
        "communication_context_only": True,
        "non_evidence": True,
        "source_present": source_present,
        "source_path": source_path_text,
        "source_kind": source_kind,
        "source_schema": source.get("schema") if source_present else None,
        "source_valid": bool(source.get("valid")) if source_present else False,
        "status": "not_provided",
        "config_valid": False,
        "token_present": False,
        "token_value_redacted": "<missing>",
        "guild_id": None,
        "beta_channel_id": None,
        "event_sink": None,
        "discord_py_available": False,
        "blockers": [],
        "source_overclaimed_readiness_or_authorization_flags": [],
        "source_overclaimed_progress_flags": [],
        "non_claim": (
            "Discord beta bridge config is communication posture only. It does not "
            "connect to Discord, authorize Discord sends, authorize live ops, or count "
            "toward runtime evidence, SDK/P0 progress, public readiness, stable "
            "readiness, Plugin Hub readiness, or publication."
        ),
    }
    base.update(false_flags)
    base.update(zero_fields)
    if not source_present:
        return base

    assert isinstance(source, dict)
    blockers = string_list(source.get("blockers"))
    if source.get("schema") != DISCORD_BETA_BRIDGE_CONFIG_CHECK_SCHEMA:
        blockers.append("discord_beta_bridge_config_schema_mismatch")

    non_authorization = dict_or_empty(source.get("non_authorization"))
    for key, value in non_authorization.items():
        if value is not False:
            blockers.append(f"discord_beta_bridge_non_authorization_{key}_not_false")

    source_overclaimed_flags, source_overclaimed_progress = source_alias_overclaim_paths(
        source,
        false_keys=set(false_flags),
        zero_keys=set(zero_fields),
        initial_non_counting_context=False,
    )
    for flag in source_overclaimed_flags:
        blockers.append(f"discord_beta_bridge_overclaim:{flag}")
    for flag in source_overclaimed_progress:
        blockers.append(f"discord_beta_bridge_progress_overclaim:{flag}")

    config_valid = (
        source.get("schema") == DISCORD_BETA_BRIDGE_CONFIG_CHECK_SCHEMA
        and source.get("valid") is True
        and not blockers
    )
    base.update(
        {
            "status": "config_valid" if config_valid else "config_not_ready",
            "config_valid": config_valid,
            "token_present": bool(source.get("token_present")),
            "token_value_redacted": (
                "<present>" if source.get("token_present") is True else "<missing>"
            ),
            "guild_id": source.get("guild_id"),
            "beta_channel_id": source.get("beta_channel_id"),
            "event_sink": source.get("event_sink"),
            "discord_py_available": bool(source.get("discord_py_available")),
            "blockers": list(dict.fromkeys(blockers)),
            "source_overclaimed_readiness_or_authorization_flags": sorted(
                source_overclaimed_flags
            ),
            "source_overclaimed_progress_flags": sorted(source_overclaimed_progress),
        }
    )
    return base


def stable_sdk_remaining_blockers_summary(
    *,
    public_sdk: dict[str, Any],
    current_route_blocker: Any,
    remaining_route_blockers: list[str],
    sdk_count_summary: dict[str, Any],
    p0_count_summary: dict[str, Any],
    fastest_summary: dict[str, Any],
    approved_in_game_evidence: dict[str, Any],
    post_evidence_p0_lock_simulation: dict[str, Any],
    debug_first_acceleration: dict[str, Any],
    operator_context: dict[str, Any],
) -> dict[str, Any]:
    sdk_remaining_surfaces = remaining_claim_surfaces(
        public_sdk,
        counts=sdk_count_summary,
        source_paths=(
            ("complete_sdk_blocker_claim_accounting", "remaining_for_claim_surfaces"),
            ("summary", "sdk_completion", "remaining_for_claim_surfaces"),
            ("v1_sdk_progress", "complete_sdk_blockers_remaining_for_claim"),
        ),
        fallback_surfaces=COMPLETE_SDK_BLOCKER_SURFACES,
    )
    p0_remaining_surfaces = remaining_claim_surfaces(
        public_sdk,
        counts=p0_count_summary,
        source_paths=(
            ("p0_dependency_chain_claim_accounting", "remaining_for_claim_surfaces"),
            ("summary", "p0_completion", "remaining_for_claim_surfaces"),
            ("v1_sdk_progress", "p0_dependency_chain_remaining_for_claim"),
            ("p0_dependency_chain_remaining_for_claim",),
        ),
        fallback_surfaces=P0_DEPENDENCY_CHAIN_SURFACES,
    )
    next_required_artifact = approved_in_game_evidence.get("next_required_artifact")
    if not isinstance(next_required_artifact, str) or not next_required_artifact:
        next_required_artifact = fastest_summary.get("next_required_artifact")
    operator_context_ids = string_list(operator_context.get("context_ids"))
    return {
        "schema": "obelisk.sdk-status-stable-sdk-remaining-blockers.v1",
        "status_report_only": True,
        "ready": False,
        "stable_claim_allowed": False,
        "stable_sdk_ready": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "current_route_blocker": current_route_blocker,
        "remaining_route_blockers": remaining_route_blockers,
        "next_required_artifact": next_required_artifact,
        "missing_required_artifact": approved_in_game_evidence.get("missing_required_artifact"),
        "after_runtime_evidence": post_evidence_p0_lock_simulation.get(
            "simulated_route_blocker_after_accepted_runtime_evidence"
        ),
        "debug_first_blocker_chain": debug_first_acceleration.get("compact_blocker_chain"),
        "debug_first_next_action": debug_first_acceleration.get("next_action"),
        "next_checker": debug_first_acceleration.get("next_checker"),
        "complete_sdk_progress_ratio": sdk_count_summary.get("progress_ratio"),
        "complete_sdk_remaining_for_claim_count": sdk_count_summary.get(
            "remaining_for_claim_count"
        ),
        "complete_sdk_total": sdk_count_summary.get("total"),
        "remaining_sdk_blocker_surfaces": sdk_remaining_surfaces,
        "remaining_sdk_blocker_surface_count": len(sdk_remaining_surfaces),
        "p0_dependency_chain_progress_ratio": p0_count_summary.get("progress_ratio"),
        "p0_dependency_chain_remaining_for_claim_count": p0_count_summary.get(
            "remaining_for_claim_count"
        ),
        "p0_dependency_chain_total": p0_count_summary.get("total"),
        "remaining_p0_dependency_chain_surfaces": p0_remaining_surfaces,
        "remaining_p0_dependency_chain_surface_count": len(p0_remaining_surfaces),
        "current_p0_surface": p0_remaining_surfaces[0] if p0_remaining_surfaces else None,
        "operator_context_ids": operator_context_ids,
        "operator_context_count": int_or_none(operator_context.get("context_count")) or 0,
        "operator_context_counts_as_approved_runtime_evidence": False,
        "operator_context_counts_as_sdk_progress": False,
        "operator_context_counts_toward_p0_dependency_chain": False,
        "operator_context_counts_toward_complete_sdk_claim": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "non_claim": (
            "Stable SDK remaining-blocker report only; operator context, passive "
            "monitor output, beta notices, package-shape installs, and scoped "
            "non-complete statements do not satisfy runtime evidence, SDK/P0 "
            "progress, runtime readiness, public SDK readiness, release readiness, "
            "or stable SDK wording."
        ),
    }


def accepted_approved_runtime_principal_lifecycle_bundle(public_sdk: dict[str, Any]) -> bool:
    containers = [
        public_sdk.get("approved_in_game_evidence"),
        public_sdk.get("approved_runtime_evidence"),
        public_sdk.get(APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE),
        nested_get(public_sdk, "runtime_required_blockers", "approved_runtime_evidence"),
    ]
    for container in containers:
        if not isinstance(container, dict):
            continue
        if non_public_checkjoin_session_start_rejected_acceptance_present(container):
            continue
        if quarantined_runtime_evidence_source_present(container):
            continue
        if partial_lifecycle_shortcut_present(container):
            continue
        if (
            container.get("approved_runtime_evidence_accepted") is True
            and container.get("evidence_bundle_accepted") is True
            and approved_runtime_principal_lifecycle_report_contract_satisfied(container)
        ):
            return True
    return False


def approved_runtime_principal_lifecycle_report_contract_satisfied(
    container: dict[str, Any],
) -> bool:
    if (
        container.get("schema") != APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_CHECK_REPORT_SCHEMA
        or container.get("input_schema")
        != APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_EVIDENCE_SCHEMA
        or container.get("ready_scope") != APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_READY_SCOPE
        or container.get("approved_runtime_evidence_present") is not True
        or container.get("runtime_evidence_ready") is not True
        or container.get("next_blocker") != IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER
    ):
        return False
    for key in (
        "promotion_ready",
        "public_header_allowed",
        "public_abi_ready",
        "public_sdk_ready",
        "v1_completion_ready",
        "runtime_ready",
        "stable_claim_allowed",
        "complete_sdk_allowed",
        "complete_sdk_ready",
    ):
        if container.get(key) is not False:
            return False

    selection = container.get("strict_lifecycle_triplet_selection")
    if not isinstance(selection, dict):
        return False
    if (
        container.get("strict_lifecycle_triplet_selected") is not True
        or selection.get("accepted") is not True
        or list(selection.get("selected_roles", []))
        != list(REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES)
        or selection.get("non_counting_context_event_count", 0) != 0
        or selection.get("non_counting_context_roles", []) != []
    ):
        return False

    observed_shape = container.get("strict_rejected_start_observed_shape")
    if not isinstance(observed_shape, dict):
        return False
    observed_fields = observed_shape.get("copied_bool_fields", [])
    observed_values = observed_shape.get("copied_bool_values", [])
    return (
        container.get("strict_rejected_start_expected_shape")
        == APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_REJECTED_START_SHAPE
        and observed_shape.get("target") == "ShooterGameMode.CheckJoinInProgress"
        and list(observed_fields) == ["bIsFromLogin", "ReturnValue"]
        and list(observed_values) == ["1", "0"]
        and observed_shape.get("apply_status") == "session_start_rejected_noop"
        and observed_shape.get("correlation_status") == "not_applicable"
    )


def source_current_route_blocker(
    public_sdk: dict[str, Any],
    fastest: dict[str, Any],
) -> str | None:
    current_route_blocker = public_sdk.get("current_route_blocker") or fastest.get(
        "current_route_blocker"
    )
    if isinstance(current_route_blocker, str) and current_route_blocker:
        return current_route_blocker
    return None


def source_remaining_route_blockers(
    public_sdk: dict[str, Any],
    fastest: dict[str, Any],
) -> list[str]:
    return (
        string_list(public_sdk.get("remaining_route_blockers"))
        or string_list(fastest.get("remaining_route_blockers"))
    )


def fail_closed_current_route_blocker(
    public_sdk: dict[str, Any],
    fastest: dict[str, Any],
    *,
    approved_runtime_checker_accepted: bool | None = None,
) -> str | None:
    checker_accepted = (
        accepted_approved_runtime_principal_lifecycle_bundle(public_sdk)
        if approved_runtime_checker_accepted is None
        else approved_runtime_checker_accepted
    )
    if not checker_accepted:
        return APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER

    current_route_blocker = source_current_route_blocker(public_sdk, fastest)
    if isinstance(current_route_blocker, str) and current_route_blocker:
        return current_route_blocker
    return IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER


def fail_closed_remaining_route_blockers(
    *,
    current_route_blocker: str | None,
    source_remaining_blockers: list[str],
    approved_runtime_checker_accepted: bool,
) -> list[str]:
    if not approved_runtime_checker_accepted:
        return [APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER]
    if isinstance(current_route_blocker, str) and current_route_blocker:
        return list(dict.fromkeys([current_route_blocker, *source_remaining_blockers]))
    return source_remaining_blockers


def source_route_overclaim_flags(
    *,
    source_current_blocker: str | None,
    source_remaining_blockers: list[str],
    approved_runtime_checker_accepted: bool,
) -> list[str]:
    if approved_runtime_checker_accepted:
        return []

    flags: list[str] = []
    if (
        isinstance(source_current_blocker, str)
        and source_current_blocker
        and source_current_blocker != APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER
    ):
        flags.append("current_route_blocker")
    if any(
        blocker != APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER
        for blocker in source_remaining_blockers
    ):
        flags.append("remaining_route_blockers")
    return flags


def count_summary_has_positive_progress(counts: dict[str, Any]) -> bool:
    promoted = int_or_none(counts.get("promoted_for_claim_count"))
    ratio_promoted, _ratio_total = ratio_parts(counts.get("progress_ratio"))
    return bool(
        (promoted is not None and promoted > 0)
        or (ratio_promoted is not None and ratio_promoted > 0)
        or counts.get("ready") is True
    )


def zeroed_count_summary(
    source: dict[str, Any],
    *,
    total_fallback: int,
    normalized_due_to: list[str],
) -> dict[str, Any]:
    source_total = int_or_none(source.get("total"))
    total = source_total if source_total is not None and source_total > 0 else total_fallback
    return {
        "total": total,
        "promoted_for_claim_count": 0,
        "remaining_for_claim_count": total,
        "progress_ratio": f"0/{total}",
        "ready": False,
        "source_total": source.get("total"),
        "source_promoted_for_claim_count": source.get("promoted_for_claim_count"),
        "source_remaining_for_claim_count": source.get("remaining_for_claim_count"),
        "source_progress_ratio": source.get("progress_ratio"),
        "source_ready": source.get("ready"),
        "normalized_due_to": normalized_due_to,
    }


def normalize_count_summary_for_route_blocker(
    source: dict[str, Any],
    *,
    total_fallback: int,
    blockers: set[str],
) -> dict[str, Any]:
    if not blockers:
        return source
    return zeroed_count_summary(
        source,
        total_fallback=total_fallback,
        normalized_due_to=sorted(blockers),
    )


def is_passive_non_evidence_path(path_id: str, payload: dict[str, Any]) -> bool:
    path_type = payload.get("path_type")
    marker_text = path_marker_text(path_id, payload)
    return (
        "passive" in path_id
        or (isinstance(path_type, str) and "passive" in path_type)
        or "passive" in marker_text
    )


def normalized_marker_key(value: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def is_player_notice_action_path(path_id: str, payload: dict[str, Any]) -> bool:
    marker_key = normalized_marker_key(path_marker_text(path_id, payload))
    return (
        "player_notice_action" in marker_key
        or "player_notice" in marker_key
        or "notice_action" in marker_key
        or "notice_dry_run" in marker_key
    )


def target_map_name(payload: dict[str, Any]) -> str | None:
    target = payload.get("target")
    if not isinstance(target, dict):
        return None
    map_name = target.get("map")
    return map_name if isinstance(map_name, str) and map_name else None


def role_values_from_path(path_payload: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    for key in keys:
        value = path_payload.get(key)
        if isinstance(value, str) and value:
            return [value]
        values = string_list(value)
        if values:
            return values
    return []


def current_role_source_is_trusted(path_payload: dict[str, Any]) -> bool:
    for key in TRUSTED_CURRENT_ROLE_SOURCE_BOOLEAN_KEYS:
        if path_payload.get(key) is True:
            return True

    source_values: list[str] = []
    for key in TRUSTED_CURRENT_ROLE_SOURCE_TEXT_KEYS:
        value = path_payload.get(key)
        if isinstance(value, str) and value:
            source_values.append(value)
        else:
            source_values.extend(string_list(value))

    normalized_values = {
        normalized_alias_key(value) for value in source_values if isinstance(value, str)
    }
    if any(
        marker == value or marker in value
        for marker in UNTRUSTED_CURRENT_ROLE_SOURCE_TEXT_MARKERS
        for value in normalized_values
    ):
        return False
    return any(
        marker == value or marker in value
        for marker in TRUSTED_CURRENT_ROLE_SOURCE_MARKERS
        for value in normalized_values
    )


def normalize_current_role_claims_for_path(path_payload: dict[str, Any]) -> dict[str, Any]:
    source_present_roles = role_values_from_path(path_payload, ("present_event_roles",))
    source_missing_roles = role_values_from_path(
        path_payload,
        (
            "missing_event_roles",
            "missing_roles",
            "missing_required_event_roles",
            "required_event_roles_missing",
        ),
    )
    trusted_source = current_role_source_is_trusted(path_payload)
    has_source_role_claim = bool(source_present_roles or source_missing_roles)
    normalized = dict(path_payload)
    normalized["role_source_requirement"] = CURRENT_ROLE_SOURCE_REQUIREMENT
    normalized["role_source_trusted_for_current_status"] = trusted_source
    if source_present_roles:
        normalized["source_present_event_roles"] = source_present_roles
    if source_missing_roles:
        normalized["source_missing_event_roles"] = source_missing_roles

    if trusted_source:
        present_role_set = set(source_present_roles)
        missing_role_set = set(source_missing_roles)
        if not source_missing_roles:
            missing_role_set = set(REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES) - present_role_set
        normalized["present_event_roles"] = [
            role
            for role in REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES
            if role in present_role_set
        ]
        normalized["missing_event_roles"] = [
            role
            for role in REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES
            if role in missing_role_set
        ]
        normalized["role_source_status"] = "trusted_current_log"
        return normalized

    if has_source_role_claim:
        normalized["present_event_roles"] = []
        normalized["missing_event_roles"] = list(REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES)
        normalized["role_source_status"] = "untrusted_for_current_status"
        normalized["role_source_untrusted_for_current_status"] = True
        return normalized

    normalized["role_source_status"] = "not_provided"
    return normalized


def path_marker_text(path_id: str, payload: dict[str, Any]) -> str:
    marker_values: list[str] = [path_id]
    for key in ("path_type", "missing_artifact_key", "missing_requirement_key"):
        value = payload.get(key)
        if isinstance(value, str):
            marker_values.append(value)
    for key in ("paths", "requirements"):
        marker_values.extend(string_list(payload.get(key)))
    return " ".join(marker_values).lower()


def action_path_classification(path_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    marker_text = path_marker_text(path_id, payload)
    map_name = (target_map_name(payload) or "").lower()
    missing_roles = {
        role.lower()
        for role in role_values_from_path(
            payload,
            (
                "missing_event_roles",
                "missing_roles",
                "missing_required_event_roles",
                "required_event_roles_missing",
            ),
        )
    }
    present_roles = {
        role.lower()
        for role in role_values_from_path(payload, ("present_event_roles",))
    }
    has_complete_triplet = set(REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES).issubset(present_roles)
    role_source_trusted = bool(payload.get("role_source_trusted_for_current_status"))
    is_genesis2_path = "genesis2" in marker_text or map_name == "genesis2"
    is_ragnarok_path = "ragnarok" in marker_text or map_name == "ragnarok"

    if is_player_notice_action_path(path_id, payload):
        return {
            "path_status": "player_notice_action_required",
            "path_summary": (
                "player-backed evidence windows require a player_notice_action before "
                "activation, but this status report does not send or authorize it"
            ),
            "non_authorizing_reason": (
                "player_notice_action runtime-window preparation can use recorded "
                "standing launch authority or exact current-turn operator scope; "
                "this report does not authorize Discord, player notices, live ops, "
                "runtime capture, live-log reads, or workspace writes"
            ),
            "non_evidence_reason": (
                "notice sent, notice dry-run accepted, and bundle accepted statuses "
                "do not satisfy approved runtime evidence or count toward SDK/P0 progress"
            ),
            "player_notice_action_required": True,
            "notice_action_authorized": False,
            "player_notice_action_authorized": False,
            "authorizes_discord": False,
            "discord_authorized": False,
            "required_next_action": DEFAULT_PLAYER_NOTICE_ACTION_ID,
        }

    if "theisland" in marker_text or map_name == "theisland":
        return {
            "path_status": "historical_theisland_sidecar_closure",
            "path_summary": (
                "historical TheIsland sidecar closure request; non-authorizing "
                "and non-evidence until an approved bundle is accepted"
            ),
            "non_authorizing_reason": (
                "historical TheIsland closure request does not authorize live ops, "
                "runtime capture, live-log reads, or workspace writes"
            ),
            "non_evidence_reason": (
                "historical TheIsland closure output remains non-evidence until "
                "an approved copied runtime evidence bundle is accepted"
            ),
        }

    if is_genesis2_path:
        if not role_source_trusted:
            return {
                "path_status": "active_genesis2_current_roles_unverified",
                "path_summary": (
                    "active Genesis2 current lifecycle roles are unverified by a "
                    "checked copied/runtime log artifact or explicit current fresh log input"
                ),
                "non_authorizing_reason": (
                    "Genesis2 passive or docs context does not authorize live ops, "
                    "runtime capture, live-log reads, or workspace writes"
                ),
                "non_evidence_reason": (
                    "Genesis2 passive or docs context is diagnostic only and cannot "
                    "imply current lifecycle roles are present"
                ),
                "required_current_role_source": CURRENT_ROLE_SOURCE_REQUIREMENT,
            }
        if missing_roles != {"session_end"}:
            next_missing_role = next(
                (
                    role
                    for role in REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES
                    if role in missing_roles
                ),
                None,
            )
            return {
                "path_status": (
                    "active_genesis2_missing_current_roles"
                    if missing_roles
                    else "active_genesis2_current_triplet_needs_approved_bundle"
                ),
                "path_summary": (
                    "active Genesis2 checked current log is missing lifecycle roles"
                    if missing_roles
                    else (
                        "active Genesis2 checked current log has the complete role "
                        "triplet but still needs a copied approved evidence bundle"
                    )
                ),
                "non_authorizing_reason": (
                    "Genesis2 current-log status does not authorize live ops, "
                    "runtime capture, live-log reads, or workspace writes"
                ),
                "non_evidence_reason": (
                    "Genesis2 current-log status remains diagnostic until a copied "
                    "approved runtime principal lifecycle evidence bundle is accepted"
                ),
                "required_next_event_role": next_missing_role,
                "approved_bundle_required": not bool(missing_roles),
                "required_next_artifact": (
                    APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE
                    if not missing_roles
                    else None
                ),
            }
        return {
            "path_status": "active_genesis2_missing_session_end",
            "path_summary": (
                "active Genesis2 checked current log is still missing session_end"
            ),
            "non_authorizing_reason": (
                "Genesis2 current-log status does not authorize live ops, "
                "runtime capture, live-log reads, or workspace writes"
            ),
            "non_evidence_reason": (
                "Genesis2 current-log status is diagnostic and is missing session_end"
            ),
            "required_next_event_role": "session_end",
        }

    if is_ragnarok_path:
        if not role_source_trusted:
            return {
                "path_status": "active_ragnarok_current_roles_unverified",
                "path_summary": (
                    "active Ragnarok current lifecycle roles are unverified by a "
                    "checked copied/runtime log artifact or explicit current fresh log input"
                ),
                "non_authorizing_reason": (
                    "Ragnarok passive or docs context does not authorize live ops, "
                    "runtime capture, live-log reads, or workspace writes"
                ),
                "non_evidence_reason": (
                    "Ragnarok passive or docs context is diagnostic only and cannot "
                    "imply current lifecycle roles are present"
                ),
                "required_current_role_source": CURRENT_ROLE_SOURCE_REQUIREMENT,
            }
        if not has_complete_triplet:
            next_missing_role = next(
                (
                    role
                    for role in REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES
                    if role in missing_roles
                ),
                None,
            )
            return {
                "path_status": "active_ragnarok_missing_current_roles",
                "path_summary": "active Ragnarok checked current log is missing lifecycle roles",
                "non_authorizing_reason": (
                    "Ragnarok current-log status does not authorize live ops, "
                    "runtime capture, live-log reads, or workspace writes"
                ),
                "non_evidence_reason": (
                    "Ragnarok current-log status is diagnostic and is missing "
                    "required event roles"
                ),
                "required_next_event_role": next_missing_role,
            }
        return {
            "path_status": "active_ragnarok_complete_passive_triplet_needs_approved_bundle",
            "path_summary": (
                "active Ragnarok checked current log has the complete role triplet "
                "but still needs a copied approved evidence bundle"
            ),
            "non_authorizing_reason": (
                "complete current Ragnarok triplet does not authorize live ops, "
                "runtime capture, live-log reads, or workspace writes"
            ),
            "non_evidence_reason": (
                "complete current Ragnarok triplet is diagnostic until a copied "
                "approved runtime principal lifecycle evidence bundle is accepted"
            ),
            "approved_bundle_required": True,
            "required_next_artifact": APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE,
        }

    if is_passive_non_evidence_path(path_id, payload) and role_source_trusted and (
        "approved_bundle_missing" in marker_text or has_complete_triplet
    ):
        return {
            "path_status": "active_passive_complete_triplet_needs_approved_bundle",
            "path_summary": (
                "active passive observation has the complete role triplet but still "
                "needs a copied approved evidence bundle"
            ),
            "non_authorizing_reason": (
                "complete passive role triplet does not authorize live ops, "
                "runtime capture, live-log reads, or workspace writes"
            ),
            "non_evidence_reason": (
                "complete passive role triplet is diagnostic until a copied approved "
                "runtime principal lifecycle evidence bundle is accepted"
            ),
            "approved_bundle_required": True,
            "required_next_artifact": APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE,
        }

    if not role_source_trusted and is_passive_non_evidence_path(path_id, payload):
        return {
            "path_status": "active_passive_current_roles_unverified",
            "path_summary": (
                "active passive current lifecycle roles are unverified by a checked "
                "copied/runtime log artifact or explicit current fresh log input"
            ),
            "non_authorizing_reason": (
                "passive or docs context does not authorize live ops, runtime capture, "
                "live-log reads, or workspace writes"
            ),
            "non_evidence_reason": (
                "passive or docs context is diagnostic only and cannot imply current "
                "lifecycle roles are present"
            ),
            "required_current_role_source": CURRENT_ROLE_SOURCE_REQUIREMENT,
        }

    if "session_end" in missing_roles and is_passive_non_evidence_path(path_id, payload):
        return {
            "path_status": "active_passive_missing_session_end",
            "path_summary": "active passive observation is still missing session_end",
            "non_authorizing_reason": (
                "passive observation does not authorize live ops, runtime capture, "
                "live-log reads, or workspace writes"
            ),
            "non_evidence_reason": (
                "passive observation is diagnostic and is missing required event roles"
            ),
            "required_next_event_role": "session_end",
        }

    if is_passive_non_evidence_path(path_id, payload):
        return {
            "path_status": "passive_non_evidence",
            "path_summary": "passive observation path; diagnostic only and non-evidence",
            "non_authorizing_reason": (
                "passive observation does not authorize live ops, runtime capture, "
                "live-log reads, or workspace writes"
            ),
            "non_evidence_reason": "passive observation is diagnostic only",
        }

    return {
        "path_status": "non_authorizing_non_evidence",
        "path_summary": "non-authorizing path; does not count as approved runtime evidence",
        "non_authorizing_reason": "path does not authorize runtime, server, or workspace work",
        "non_evidence_reason": "path does not count as approved runtime evidence",
    }


def default_player_notice_action_path() -> dict[str, Any]:
    return {
        "path_type": "player_notice_action",
        "authorization": "non-authorizing",
        "non_authorizing": True,
        "player_notice_action_required": True,
        "notice_action_authorized": False,
        "player_notice_action_authorized": False,
        "authorizes_discord": False,
        "discord_authorized": False,
        "authorizes_runtime_work": False,
        "authorizes_server_work": False,
        "authorizes_workspace_work": False,
        "authorizes_server_operations": False,
        "authorizes_workspace_writes": False,
        "reads_live_logs": False,
        "notice_sent": False,
        "player_notice_sent": False,
        "notice_dry_run_sent": False,
        "notice_dry_run_accepted": False,
        "notice_bundle_accepted": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_toward_complete_sdk_claim_now": False,
        "counts_toward_p0_dependency_chain_claim_now": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "paths": [
            DEFAULT_PLAYER_NOTICE_ACTION_ID,
            "standing-authorized or current-turn approved player notice path required before activation",
        ],
        "requirements": [
            (
                "player-backed evidence windows require a standing-authorized "
                "or current-turn approved player_notice_action before activation"
            ),
            (
                "this report does not authorize Discord, beta tester notices, runtime "
                "work, server operations, live-log reads, or workspace writes"
            ),
            (
                "notice sent, notice dry-run accepted, and bundle accepted statuses do "
                "not satisfy approved runtime evidence or count toward SDK/P0 progress"
            ),
        ],
        "required_event_roles": list(REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES),
        "missing_requirement_key": DEFAULT_PLAYER_NOTICE_ACTION_ID,
    }


def normalize_actionable_paths(raw_paths: Any) -> dict[str, dict[str, Any]]:
    if isinstance(raw_paths, dict):
        items = list(raw_paths.items())
    elif isinstance(raw_paths, list):
        items = []
        for index, item in enumerate(raw_paths, start=1):
            if isinstance(item, dict):
                path_id = item.get("path_id") or item.get("id")
                if not isinstance(path_id, str) or not path_id:
                    path_id = item.get("missing_artifact_key") or item.get("missing_requirement_key")
                if not isinstance(path_id, str) or not path_id:
                    path_id = f"path_{index}"
                items.append((path_id, item))
            elif isinstance(item, str) and item:
                items.append((item, {"path_id": item}))
    else:
        items = []

    normalized: dict[str, dict[str, Any]] = {}
    for path_id, source_payload in items:
        if not isinstance(path_id, str) or not path_id:
            continue
        payload = dict(source_payload) if isinstance(source_payload, dict) else {}
        source_authorization = payload.get("authorization")
        overclaimed_flags, overclaimed_progress_flags = source_alias_overclaim_paths(
            payload,
            false_keys=set(FAIL_CLOSED_ACTION_FALSE_FLAGS),
            zero_keys=set(FAIL_CLOSED_ACTION_ZERO_FIELDS),
            initial_non_counting_context=True,
        )
        payload = sanitize_non_counting_alias_payload(
            payload,
            false_keys=set(FAIL_CLOSED_ACTION_FALSE_FLAGS),
            zero_keys=set(FAIL_CLOSED_ACTION_ZERO_FIELDS),
            initial_non_counting_context=True,
        )

        payload["path_id"] = path_id
        if isinstance(source_authorization, str) and source_authorization != "non-authorizing":
            payload["source_authorization"] = source_authorization
        payload["authorization"] = "non-authorizing"
        payload["non_authorizing"] = True
        for key in FAIL_CLOSED_ACTION_FALSE_FLAGS:
            payload[key] = False
        for key in FAIL_CLOSED_ACTION_ZERO_FIELDS:
            payload[key] = 0
        payload = normalize_current_role_claims_for_path(payload)
        classification = action_path_classification(path_id, payload)
        payload.update(classification)
        if is_passive_non_evidence_path(path_id, payload):
            payload["evidence_status"] = "diagnostic_passive_non_evidence"
        elif is_player_notice_action_path(path_id, payload):
            payload["evidence_status"] = "player_notice_action_required_non_evidence"
        else:
            payload.setdefault("evidence_status", "non_evidence_until_approved_bundle_acceptance")
        if overclaimed_flags:
            payload["source_overclaimed_authorization_flags"] = sorted(overclaimed_flags)
        if overclaimed_progress_flags:
            payload["source_overclaimed_progress_flags"] = sorted(
                overclaimed_progress_flags
            )
        normalized[path_id] = payload
    return normalized


def ensure_player_notice_action_path(
    action_paths: dict[str, dict[str, Any]],
    *,
    current_route_blocker: Any,
) -> dict[str, dict[str, Any]]:
    if current_route_blocker != "approved_runtime_evidence_missing":
        return action_paths
    if any(is_player_notice_action_path(path_id, payload) for path_id, payload in action_paths.items()):
        return action_paths
    notice_path = normalize_actionable_paths(
        {DEFAULT_PLAYER_NOTICE_ACTION_ID: default_player_notice_action_path()}
    )
    return {**action_paths, **notice_path}


def canonical_route_unblock_defaults(current_route_blocker: str | None) -> dict[str, Any]:
    if current_route_blocker == "approved_runtime_evidence_missing":
        return {
            "unblock_kind": "approved_copied_runtime_principal_lifecycle_evidence",
            "recommended_next_action": (
                "produce approved copied runtime principal lifecycle evidence for "
                "obelisk.player_identity.v1 before reviewing public identity, "
                "permissions/admin, command response, or commands/replies ABI"
            ),
            "required_artifacts": [
                "approved_runtime_principal_lifecycle_evidence_bundle",
                "copied_Obelisk.log_with_PlayerPrincipalLifecycleObserver_event_triplet",
            ],
            "required_actions": [DEFAULT_PLAYER_NOTICE_ACTION_ID],
            "required_event_roles": list(REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES),
            "next_route_blocker_after_acceptance": "identity_public_contract_gate_missing",
            "active_runtime_window_requires_current_turn_scope": False,
            "active_runtime_window_requires_standing_or_current_scope": True,
        }
    if current_route_blocker == "identity_public_contract_gate_missing":
        return {
            "unblock_kind": "reviewed_identity_public_contract",
            "recommended_next_action": (
                "review the player identity public contract before permissions/admin, "
                "command response, or commands/replies ABI"
            ),
            "required_artifacts": ["reviewed_player_identity_public_contract_decision"],
            "required_actions": [],
            "required_event_roles": [],
            "next_route_blocker_after_acceptance": None,
            "active_runtime_window_requires_current_turn_scope": False,
            "active_runtime_window_requires_standing_or_current_scope": False,
        }
    return {}


def sanitized_next_action_sequence_metadata(source: Any) -> list[Any]:
    if source is None:
        return []
    sanitized = sanitize_non_counting_alias_payload(
        {"next_action_sequence": source},
        false_keys=set(FAIL_CLOSED_ACTION_FALSE_FLAGS) | set(PACKAGE_SHAPE_FALSE_FLAGS),
        zero_keys=set(FAIL_CLOSED_ACTION_ZERO_FIELDS) | set(PACKAGE_SHAPE_ZERO_FIELDS),
        initial_non_counting_context=True,
    ).get("next_action_sequence")
    if isinstance(sanitized, list):
        return sanitized
    if isinstance(sanitized, (dict, str)):
        return [sanitized]
    return []


def normalize_fastest_next_sdk_unblock(
    fastest: dict[str, Any],
    *,
    current_route_blocker: str | None,
    remaining_route_blockers: list[str],
    action_paths: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    defaults = canonical_route_unblock_defaults(current_route_blocker)
    source_required_artifacts = string_list(fastest.get("required_artifacts"))
    required_artifacts = (
        list(defaults["required_artifacts"])
        if defaults
        else source_required_artifacts
    )
    source_required_actions = string_list(fastest.get("required_actions"))
    required_actions = (
        list(defaults["required_actions"]) if defaults else source_required_actions
    )
    source_required_event_roles = string_list(fastest.get("required_event_roles"))
    required_event_roles = (
        list(defaults["required_event_roles"])
        if defaults
        else source_required_event_roles
    )
    next_required_artifact = first_next_required_artifact(required_artifacts, action_paths)
    source_overclaimed_authorization_flags, source_overclaimed_progress_flags = (
        source_alias_overclaim_paths(
            fastest,
            false_keys=set(FAIL_CLOSED_ACTION_FALSE_FLAGS),
            zero_keys=set(FAIL_CLOSED_ACTION_ZERO_FIELDS),
            initial_non_counting_context=True,
        )
    )
    exact_scope_required = fastest_unblock_requires_exact_scope(
        fastest,
        next_required_artifact=next_required_artifact,
    ) or bool(
        defaults.get("active_runtime_window_requires_current_turn_scope")
        or defaults.get("active_runtime_window_requires_standing_or_current_scope")
    )
    standing_launch_authority_recorded = STANDING_LAUNCH_AUTHORITY_RECORDED
    current_turn_scope_required = exact_scope_required and not standing_launch_authority_recorded
    source_recommended_next_action = fastest.get("recommended_next_action")
    recommended_next_action = defaults.get(
        "recommended_next_action",
        source_recommended_next_action,
    )
    source_next_action_sequence = fastest.get("next_action_sequence")
    next_action_sequence = sanitized_next_action_sequence_metadata(source_next_action_sequence)
    normalized = {
        "schema": fastest.get("schema"),
        "current_route_blocker": fastest.get("current_route_blocker") or current_route_blocker,
        "remaining_route_blockers": (
            string_list(fastest.get("remaining_route_blockers")) or remaining_route_blockers
        ),
        "unblock_kind": defaults.get("unblock_kind", fastest.get("unblock_kind")),
        "source_unblock_kind": fastest.get("unblock_kind"),
        "surface": fastest.get("surface"),
        "recommended_next_action": recommended_next_action,
        "source_recommended_next_action": source_recommended_next_action,
        "next_action_sequence": next_action_sequence,
        "source_next_action_sequence_present": source_next_action_sequence is not None,
        "next_action_sequence_metadata_only": True,
        "next_action_sequence_non_claim": (
            "next_action_sequence is planning metadata only; it does not count as "
            "runtime evidence, SDK/P0 progress, public readiness, Plugin Hub readiness, "
            "publication authority, live ops, or workspace authorization"
        ),
        "required_artifacts": required_artifacts,
        "source_required_artifacts": source_required_artifacts,
        "required_actions": required_actions,
        "source_required_actions": source_required_actions,
        "next_required_artifact": next_required_artifact,
        "required_event_roles": required_event_roles,
        "source_required_event_roles": source_required_event_roles,
        "next_route_blocker_after_acceptance": defaults.get(
            "next_route_blocker_after_acceptance",
            fastest.get("next_route_blocker_after_acceptance"),
        ),
        "source_next_route_blocker_after_acceptance": fastest.get(
            "next_route_blocker_after_acceptance"
        ),
        "active_runtime_window_requires_current_turn_scope": current_turn_scope_required,
        "active_runtime_window_requires_standing_or_current_scope": exact_scope_required,
        "current_turn_scope_required": current_turn_scope_required,
        "standing_launch_authority_recorded": standing_launch_authority_recorded,
        "standing_launch_authority_source": STANDING_LAUNCH_AUTHORITY_SOURCE,
        "standing_launch_authority_satisfies_runtime_window_scope": (
            exact_scope_required and standing_launch_authority_recorded
        ),
        "current_turn_scope_requirement": STANDING_OR_CURRENT_SCOPE_REQUIREMENT,
        "runtime_window_scope_requirement": STANDING_OR_CURRENT_SCOPE_REQUIREMENT,
        "runtime_window_can_be_prepared_under_standing_authority": (
            exact_scope_required and standing_launch_authority_recorded
        ),
        "runtime_window_preparation_counts_as_approved_runtime_evidence": False,
        "runtime_window_preparation_counts_as_runtime_evidence": False,
        "runtime_window_preparation_counts_toward_sdk": False,
        "runtime_window_preparation_counts_toward_p0_dependency_chain": False,
        "runtime_window_preparation_counts_toward_complete_sdk_claim": False,
        "standing_launch_authority_counts_as_approved_runtime_evidence": False,
        "standing_launch_authority_counts_as_runtime_evidence": False,
        "standing_launch_authority_counts_toward_sdk": False,
        "standing_launch_authority_counts_toward_p0_dependency_chain": False,
        "standing_launch_authority_counts_toward_complete_sdk_claim": False,
        "authorizes_runtime_work": False,
        "authorizes_server_work": False,
        "authorizes_server_operations": False,
        "server_operations_authorized": False,
        "authorizes_workspace_work": False,
        "authorizes_workspace_writes": False,
        "workspace_writes_authorized": False,
        "live_ops_authorized": False,
        "runtime_capture_authorized": False,
        "authorizes_discord": False,
        "discord_authorized": False,
        "notice_action_authorized": False,
        "player_notice_action_authorized": False,
        "reads_live_logs": False,
        "read_live_logs": False,
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "passive_snapshot_evidence_allowed": False,
        "runtime_evidence_present": False,
        "runtime_evidence_ready": False,
        "sdk_evidence_ready": False,
        "counts_toward_complete_sdk_claim_now": False,
        "counts_toward_p0_dependency_chain_claim_now": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "prioritization_only": True,
        "player_notice_action_required": any(
            is_player_notice_action_path(path_id, payload)
            for path_id, payload in action_paths.items()
        )
        or DEFAULT_PLAYER_NOTICE_ACTION_ID in required_actions,
        "notice_sent": False,
        "player_notice_sent": False,
        "notice_dry_run_sent": False,
        "notice_dry_run_accepted": False,
        "notice_bundle_accepted": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "stable_claim_allowed": False,
        "plugin_hub_ready": False,
        "plugin_hub_readiness_claim_allowed": False,
        "plugin_hub_publication_allowed": False,
        "publication_authorized": False,
        "actionable_paths": action_paths,
        "action_paths": action_paths,
        "source_non_claim": fastest.get("non_claim"),
        "non_claim": (
            "Prioritization only; this object does not approve runtime work, public ABI, "
            "public SDK readiness, or complete/full/production/stable SDK wording."
        ),
    }
    for key in FAIL_CLOSED_ACTION_FALSE_FLAGS:
        normalized[key] = False
    for key in FAIL_CLOSED_ACTION_ZERO_FIELDS:
        normalized[key] = 0
    if source_overclaimed_authorization_flags:
        normalized["source_overclaimed_authorization_flags"] = sorted(
            source_overclaimed_authorization_flags
        )
    if source_overclaimed_progress_flags:
        normalized["source_overclaimed_progress_flags"] = sorted(
            source_overclaimed_progress_flags
        )
    return normalized


def first_next_required_artifact(
    required_artifacts: list[str],
    action_paths: dict[str, dict[str, Any]],
) -> str | None:
    if APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE in required_artifacts:
        return APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE
    for path_payload in action_paths.values():
        artifact = path_payload.get("required_next_artifact")
        if isinstance(artifact, str) and artifact:
            return artifact
    return required_artifacts[0] if required_artifacts else None


def fastest_unblock_requires_exact_scope(
    fastest: dict[str, Any],
    *,
    next_required_artifact: str | None,
) -> bool:
    if bool(
        fastest.get("active_runtime_window_requires_current_turn_scope")
        or fastest.get("active_runtime_window_requires_standing_or_current_scope")
    ):
        return True
    if next_required_artifact == APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE:
        return True
    marker_text = " ".join(
        value
        for value in (
            fastest.get("unblock_kind"),
            fastest.get("recommended_next_action"),
        )
        if isinstance(value, str)
    ).lower()
    return "runtime" in marker_text


def approved_in_game_evidence_status(
    *,
    current_route_blocker: Any,
    fastest_summary: dict[str, Any],
    action_paths: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    path_summaries: dict[str, dict[str, Any]] = {}
    diagnostic_complete_triplet_path_ids: list[str] = []
    missing_role_path_ids: list[str] = []
    required_roles = list(REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES)
    required_role_set = set(required_roles)

    for path_id, payload in action_paths.items():
        present_roles = string_list(payload.get("present_event_roles"))
        missing_roles = string_list(payload.get("missing_event_roles"))
        present_role_set = set(present_roles)
        complete_triplet = required_role_set.issubset(present_role_set) and not missing_roles
        evidence_status = payload.get("evidence_status")
        if complete_triplet and evidence_status == "diagnostic_passive_non_evidence":
            diagnostic_complete_triplet_path_ids.append(path_id)
        if missing_roles:
            missing_role_path_ids.append(path_id)
        path_summaries[path_id] = {
            "target": payload.get("target"),
            "path_status": payload.get("path_status"),
            "path_type": payload.get("path_type"),
            "evidence_status": evidence_status,
            "authorization": "non-authorizing",
            "present_event_roles": present_roles,
            "missing_event_roles": missing_roles,
            "source_present_event_roles": string_list(payload.get("source_present_event_roles")),
            "source_missing_event_roles": string_list(payload.get("source_missing_event_roles")),
            "role_source_status": payload.get("role_source_status"),
            "role_source_trusted_for_current_status": bool(
                payload.get("role_source_trusted_for_current_status")
            ),
            "role_source_requirement": payload.get("role_source_requirement"),
            "complete_required_role_triplet": complete_triplet,
            "approved_runtime_evidence": False,
            "approved_runtime_evidence_accepted": False,
            "evidence_bundle_accepted": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_toward_complete_sdk_claim_now": False,
            "counts_toward_p0_dependency_chain_claim_now": False,
            "live_ops_authorized": False,
            "server_operations_authorized": False,
            "workspace_writes_authorized": False,
            "runtime_capture_authorized": False,
            "reads_live_logs": False,
            "read_live_logs": False,
            "required_next_artifact": payload.get("required_next_artifact"),
        }

    next_required_artifact = fastest_summary.get("next_required_artifact")
    current_turn_scope_required = bool(fastest_summary.get("current_turn_scope_required"))
    exact_scope_required = bool(
        fastest_summary.get("active_runtime_window_requires_standing_or_current_scope")
        or fastest_summary.get("active_runtime_window_requires_current_turn_scope")
    )
    standing_launch_authority_recorded = bool(
        fastest_summary.get("standing_launch_authority_recorded")
    )
    return {
        "schema": "obelisk.approved-in-game-evidence-status.v1",
        "status_report_only": True,
        "ready": False,
        "current_route_blocker": current_route_blocker,
        "approved_in_game_ready": False,
        "approved_in_game_evidence_ready": False,
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "approved_runtime_evidence_accepted": False,
        "runtime_evidence_present": False,
        "runtime_evidence_ready": False,
        "evidence_bundle_accepted": False,
        "complete_lifecycle_event_triplet_approved": False,
        "complete_lifecycle_event_triplet_observed_diagnostic_only": bool(
            diagnostic_complete_triplet_path_ids
        ),
        "diagnostic_complete_triplet_path_ids": diagnostic_complete_triplet_path_ids,
        "missing_role_path_ids": missing_role_path_ids,
        "required_event_roles": required_roles,
        "next_required_artifact": next_required_artifact,
        "missing_required_artifact": (
            next_required_artifact
            if current_route_blocker == "approved_runtime_evidence_missing"
            else None
        ),
        "current_turn_scope_required": current_turn_scope_required,
        "active_runtime_window_requires_standing_or_current_scope": exact_scope_required,
        "standing_launch_authority_recorded": standing_launch_authority_recorded,
        "standing_launch_authority_source": fastest_summary.get(
            "standing_launch_authority_source"
        ),
        "standing_launch_authority_satisfies_runtime_window_scope": (
            exact_scope_required and standing_launch_authority_recorded
        ),
        "runtime_window_scope_requirement": fastest_summary.get(
            "runtime_window_scope_requirement"
        ),
        "runtime_window_can_be_prepared_under_standing_authority": bool(
            fastest_summary.get("runtime_window_can_be_prepared_under_standing_authority")
        ),
        "runtime_window_preparation_counts_as_approved_runtime_evidence": False,
        "runtime_window_preparation_counts_as_runtime_evidence": False,
        "runtime_window_preparation_counts_toward_sdk": False,
        "runtime_window_preparation_counts_toward_p0_dependency_chain": False,
        "runtime_window_preparation_counts_toward_complete_sdk_claim": False,
        "standing_launch_authority_counts_as_approved_runtime_evidence": False,
        "standing_launch_authority_counts_as_runtime_evidence": False,
        "standing_launch_authority_counts_toward_sdk": False,
        "standing_launch_authority_counts_toward_p0_dependency_chain": False,
        "standing_launch_authority_counts_toward_complete_sdk_claim": False,
        "player_notice_action_required": bool(
            fastest_summary.get("player_notice_action_required")
        ),
        "live_ops_authorized": False,
        "server_operations_authorized": False,
        "workspace_writes_authorized": False,
        "runtime_capture_authorized": False,
        "discord_authorized": False,
        "reads_live_logs": False,
        "read_live_logs": False,
        "counts_toward_complete_sdk_claim_now": False,
        "counts_toward_p0_dependency_chain_claim_now": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "path_summaries": path_summaries,
        "path_summary_count": len(path_summaries),
        "blocker_reason": (
            "approved_runtime_principal_lifecycle_evidence_bundle_missing_or_unaccepted"
            if current_route_blocker == "approved_runtime_evidence_missing"
            else "not_current_runtime_evidence_blocker"
        ),
        "non_claim": (
            "Approved in-game evidence is false unless an approved copied runtime "
            "principal lifecycle evidence bundle is accepted by the evidence checkers; "
            "passive triplets, notice actions, public reachability, and closure requests "
            "remain diagnostic/non-evidence here."
        ),
    }


def debug_first_acceleration_summary(
    *,
    current_route_blocker: Any,
    remaining_route_blockers: list[str],
    fastest_summary: dict[str, Any],
    approved_in_game_evidence: dict[str, Any],
) -> dict[str, Any]:
    next_required_artifact = approved_in_game_evidence.get("next_required_artifact")
    if not isinstance(next_required_artifact, str) or not next_required_artifact:
        next_required_artifact = fastest_summary.get("next_required_artifact")
    if current_route_blocker == APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER:
        current_focus = APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE
        next_action = (
            "produce and checker-accept the copied approved runtime principal "
            "lifecycle evidence bundle"
        )
        next_checker = APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_EVIDENCE_CHECKER
        expected_next_route_blocker = IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER
    elif current_route_blocker == IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER:
        current_focus = "reviewed_player_identity_public_contract_decision"
        next_action = (
            "review the player identity public contract before any permissions/admin "
            "or command-route ABI promotion"
        )
        next_checker = IDENTITY_PUBLIC_CONTRACT_READINESS_CHECKER
        expected_next_route_blocker = None
    else:
        current_focus = next_required_artifact
        next_action = fastest_summary.get("recommended_next_action")
        next_checker = None
        expected_next_route_blocker = fastest_summary.get("next_route_blocker_after_acceptance")

    return {
        "schema": "obelisk.sdk-status-debug-first-acceleration.v1",
        "status_report_only": True,
        "debug_first": True,
        "posture": "debug_first_evidence_path_status_only",
        "status": "blocked",
        "current_route_blocker": current_route_blocker,
        "remaining_route_blockers": remaining_route_blockers,
        "blocker_chain": [
            APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER,
            APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE,
            IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER,
        ],
        "compact_blocker_chain": (
            "approved_runtime_evidence_missing -> approved runtime principal "
            "lifecycle evidence bundle -> identity public contract gate"
        ),
        "current_focus": current_focus,
        "next_action": next_action,
        "next_required_artifact": next_required_artifact,
        "required_event_roles": list(REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES),
        "next_checker": next_checker,
        "expected_next_route_blocker_after_checker_acceptance": (
            expected_next_route_blocker
        ),
        "identity_public_contract_gate": IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER,
        "action_sequence": [
            {
                "step": "runtime_principal_lifecycle_evidence_bundle",
                "status": (
                    "current_blocker"
                    if current_route_blocker == APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER
                    else "not_current_blocker"
                ),
                "required_artifact": APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE,
                "required_event_roles": list(REQUIRED_PRINCIPAL_LIFECYCLE_EVENT_ROLES),
                "checker": APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_EVIDENCE_CHECKER,
                "success_advances_to": IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER,
            },
            {
                "step": "identity_public_contract_gate",
                "status": (
                    "current_blocker"
                    if current_route_blocker == IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER
                    else "blocked_until_runtime_evidence_checker_acceptance"
                ),
                "required_artifact": "reviewed_player_identity_public_contract_decision",
                "checker": IDENTITY_PUBLIC_CONTRACT_READINESS_CHECKER,
                "success_advances_to": "next_p0_route_gate_only_after_checker_acceptance",
            },
        ],
        "active_runtime_window_requires_standing_or_current_scope": bool(
            fastest_summary.get("active_runtime_window_requires_standing_or_current_scope")
        ),
        "current_turn_scope_required": bool(
            fastest_summary.get("current_turn_scope_required")
        ),
        "standing_launch_authority_recorded": bool(
            fastest_summary.get("standing_launch_authority_recorded")
        ),
        "authorization": "status-only",
        "authorizes_runtime_work": False,
        "authorizes_server_work": False,
        "authorizes_server_operations": False,
        "authorizes_workspace_work": False,
        "authorizes_workspace_writes": False,
        "workspace_writes_authorized": False,
        "live_ops_authorized": False,
        "runtime_capture_authorized": False,
        "reads_live_logs": False,
        "read_live_logs": False,
        "discord_authorized": False,
        "publication_authorized": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_claim_allowed": False,
        "stable_sdk_ready": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "non_claim": (
            "Debug-first acceleration metadata only; the current blocker remains "
            "approved_runtime_evidence_missing until the approved runtime principal "
            "lifecycle evidence checker accepts the copied bundle, and acceptance "
            "only advances to the identity public contract gate."
        ),
    }


def header_gate_summary(header_gate: dict[str, Any]) -> dict[str, Any]:
    proposed_symbols = string_list(header_gate.get("proposed_symbols"))
    source_ready = alias_value_is_positive(header_gate.get("ready"))
    source_overclaimed_readiness = [
        key
        for key in (
            "promotion_ready",
            "public_header_allowed",
            "public_contract_allowed",
            "public_abi_ready",
            "public_api_ready",
            "public_sdk_ready",
            "runtime_ready",
        )
        if alias_value_is_positive(header_gate.get(key))
    ]
    return {
        "ready": False,
        "ready_scope": "normalized_status_report_only_not_public_header_readiness",
        "source_ready": source_ready,
        "accepted_for_header_gate_review": alias_value_is_positive(
            header_gate.get("accepted_for_header_gate_review", source_ready)
        ),
        "source_promotion_ready": alias_value_is_positive(header_gate.get("promotion_ready")),
        "source_public_header_allowed": alias_value_is_positive(header_gate.get("public_header_allowed")),
        "source_public_contract_allowed": alias_value_is_positive(header_gate.get("public_contract_allowed")),
        "source_public_abi_ready": alias_value_is_positive(header_gate.get("public_abi_ready")),
        "source_public_api_ready": alias_value_is_positive(header_gate.get("public_api_ready")),
        "source_public_sdk_ready": alias_value_is_positive(header_gate.get("public_sdk_ready")),
        "source_runtime_ready": alias_value_is_positive(header_gate.get("runtime_ready")),
        "source_overclaimed_readiness_flags": source_overclaimed_readiness,
        "public_header_ready": False,
        "next_blocker": header_gate.get("next_blocker"),
        "promotion_ready": False,
        "public_header_allowed": False,
        "public_contract_allowed": False,
        "public_abi_ready": False,
        "public_api_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "proposed_symbols_count": len(proposed_symbols),
        "proposed_symbols": proposed_symbols,
        "blockers": string_list(header_gate.get("blockers")),
        "non_claims": string_list(header_gate.get("non_claims")),
    }


def sha256_string(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def certificate_binding_hash_bound(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("path"), str)
        and sha256_string(value.get("sha256"))
    )


def source_commands_replies_final_gate(
    public_sdk: dict[str, Any],
) -> tuple[dict[str, Any], str | None]:
    for key in COMMANDS_REPLIES_FINAL_GATE_SOURCE_KEYS:
        value = public_sdk.get(key)
        if isinstance(value, dict):
            return value, key
    return {}, None


def commands_replies_final_gate_context(public_sdk: dict[str, Any]) -> dict[str, Any]:
    source, source_key = source_commands_replies_final_gate(public_sdk)
    source_present = bool(source_key)
    source_schema = compact_string(source.get("schema")) if source_present else None
    source_status = source.get("status") if source_present else None
    certificate_artifact_schema = (
        compact_string(source.get("certificate_artifact_schema"))
        or (
            source_schema
            if source_schema == COMMANDS_REPLIES_PROMOTION_CERTIFICATE_SCHEMA
            else COMMANDS_REPLIES_PROMOTION_CERTIFICATE_SCHEMA
        )
    )
    certificate_binding = source.get("certificate_binding") if source_present else None
    certificate_binding_present = certificate_binding_hash_bound(certificate_binding)
    certificate_sha256_present = sha256_string(source.get("certificate_sha256"))
    certificate_present = (
        source_schema == COMMANDS_REPLIES_PROMOTION_CERTIFICATE_SCHEMA
        or certificate_binding_present
        or (
            bool(source.get("certificate_written"))
            and certificate_sha256_present
            and certificate_artifact_schema == COMMANDS_REPLIES_PROMOTION_CERTIFICATE_SCHEMA
        )
    )
    source_hash_bound = certificate_binding_present
    if source_present and certificate_present and source_hash_bound:
        final_gate_status = "present_non_counting"
    elif source_present:
        final_gate_status = "missing_or_unbound_non_counting"
    else:
        final_gate_status = "missing_non_counting"

    source_overclaimed_flags: list[str] = []
    source_overclaimed_progress: list[str] = []
    if source_present:
        source_overclaimed_flags, source_overclaimed_progress = source_alias_overclaim_paths(
            source,
            false_keys=NON_COUNTING_FALSE_ALIAS_KEYS | NON_COUNTING_GLOBAL_FALSE_ALIAS_KEYS,
            zero_keys=set(NON_COUNTING_ZERO_ALIAS_KEYS),
            initial_non_counting_context=True,
        )

    context: dict[str, Any] = {
        "schema": "obelisk.sdk-status-commands-replies-final-gate-context.v1",
        "status_report_only": True,
        "roadmap_context_only": True,
        "non_counting_context": True,
        "planning_only": True,
        "authorization": "status-only",
        "status": final_gate_status,
        "required_artifact": COMMANDS_REPLIES_PROMOTION_CERTIFICATE_ARTIFACT,
        "required_schema": COMMANDS_REPLIES_PROMOTION_CERTIFICATE_SCHEMA,
        "required_public_readiness_report_schema": (
            COMMANDS_REPLIES_PUBLIC_READINESS_CHECK_SCHEMA
        ),
        "required_hash_bound": True,
        "source_present": source_present,
        "source_key": source_key,
        "source_schema": source_schema,
        "source_status": source_status,
        "certificate_artifact_schema": certificate_artifact_schema,
        "certificate_present": certificate_present,
        "certificate_binding_present": certificate_binding_present,
        "certificate_binding": certificate_binding if certificate_binding_present else None,
        "certificate_sha256_present": certificate_sha256_present,
        "source_hash_bound": source_hash_bound,
        "hash_bound_requirement_met": source_hash_bound,
        "missing_required_artifact": (
            None
            if certificate_present and source_hash_bound
            else COMMANDS_REPLIES_PROMOTION_CERTIFICATE_ARTIFACT
        ),
        "source_overclaimed_authorization_flags": source_overclaimed_flags,
        "source_overclaimed_progress_flags": source_overclaimed_progress,
        "source_overclaim_count": (
            len(source_overclaimed_flags) + len(source_overclaimed_progress)
        ),
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "stable_claim_allowed": False,
        "plugin_hub_ready": False,
        "publication_authorized": False,
        "authorizes_runtime_work": False,
        "authorizes_server_operations": False,
        "authorizes_workspace_writes": False,
        "runtime_capture_authorized": False,
        "discord_authorized": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "non_claim": (
            "Commands/replies final-gate context is roadmap/status only. A present "
            "hash-bound certificate remains non-authorizing and does not move "
            "SDK/P0 counters, authorize runtime work, publish surfaces, or clear "
            "the approved runtime evidence blocker."
        ),
    }
    return context


def p0_offline_roadmap_summary(
    *,
    current_route_blocker: Any,
    remaining_route_blockers: list[str],
    p0_count_summary: dict[str, Any],
    post_evidence_p0_lock_simulation: dict[str, Any],
    commands_replies_final_gate: dict[str, Any],
) -> dict[str, Any]:
    current_blocker = current_route_blocker if isinstance(current_route_blocker, str) else None
    after_runtime = compact_string(
        post_evidence_p0_lock_simulation.get(
            "simulated_route_blocker_after_accepted_runtime_evidence"
        )
    ) or IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER
    steps = [
        {
            "surface": "runtime_principal_lifecycle_evidence",
            "status": (
                "current_blocker"
                if current_blocker == APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER
                else "accepted_or_not_current_blocker"
            ),
            "required_artifact": APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE,
            "checker": APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_EVIDENCE_CHECKER,
            "success_advances_to": IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER,
            "counts_toward_p0_dependency_chain": False,
        },
        {
            "surface": "obelisk.player_identity.v1",
            "status": (
                "current_post_runtime_blocker"
                if current_blocker == IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER
                else "blocked_until_runtime_evidence_checker_acceptance"
            ),
            "required_artifact": "reviewed_identity_public_contract_decision_record",
            "checker": IDENTITY_PUBLIC_CONTRACT_READINESS_CHECKER,
            "success_advances_to": PLAYER_IDENTITY_PROMOTION_CERTIFICATE_BLOCKER,
            "post_contract_bridge_required_artifact": (
                PLAYER_IDENTITY_PROMOTION_CERTIFICATE_ARTIFACT
            ),
            "post_contract_bridge_required_schema": (
                PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA
            ),
            "post_contract_bridge_counts_toward_p0_dependency_chain": False,
            "counts_toward_p0_dependency_chain": False,
        },
        {
            "surface": "obelisk.permissions_admin.v1",
            "status": "blocked_until_hash_bound_player_identity_promotion_certificate",
            "required_upstream_artifact": PLAYER_IDENTITY_PROMOTION_CERTIFICATE_ARTIFACT,
            "required_upstream_schema": PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
            "required_artifact": "permissions_admin_query_only_public_contract_review",
            "post_contract_bridge_required_artifact": (
                PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_ARTIFACT
            ),
            "post_contract_bridge_required_schema": (
                PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA
            ),
            "post_contract_bridge_counts_toward_p0_dependency_chain": False,
            "checker": PERMISSIONS_ADMIN_PUBLIC_READINESS_CHECKER,
            "success_advances_to": "obelisk.command_chat_response_path.v1",
            "counts_toward_p0_dependency_chain": False,
        },
        {
            "surface": "obelisk.command_chat_response_path.v1",
            "status": "blocked_until_obelisk.permissions_admin.v1_promoted",
            "required_upstream_artifact": PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_ARTIFACT,
            "required_upstream_schema": PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
            "required_artifact": "command_chat_response_public_contract_review",
            "post_contract_bridge_required_artifact": (
                COMMAND_CHAT_RESPONSE_PROMOTION_CERTIFICATE_ARTIFACT
            ),
            "post_contract_bridge_required_schema": (
                COMMAND_CHAT_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA
            ),
            "post_contract_bridge_counts_toward_p0_dependency_chain": False,
            "checker": "scripts/check_command_chat_response_public_readiness.py",
            "success_advances_to": "obelisk.commands_replies.v1",
            "counts_toward_p0_dependency_chain": False,
        },
        {
            "surface": "obelisk.commands_replies.v1",
            "status": "blocked_until_obelisk.command_chat_response_path.v1_promoted",
            "required_upstream_artifact": COMMAND_CHAT_RESPONSE_PROMOTION_CERTIFICATE_ARTIFACT,
            "required_upstream_schema": COMMAND_CHAT_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA,
            "required_artifact": "commands_replies_public_contract_review",
            "post_contract_bridge_required_artifact": (
                COMMANDS_REPLIES_PROMOTION_CERTIFICATE_ARTIFACT
            ),
            "post_contract_bridge_required_schema": (
                COMMANDS_REPLIES_PROMOTION_CERTIFICATE_SCHEMA
            ),
            "post_contract_bridge_hash_bound": True,
            "post_contract_bridge_counts_toward_p0_dependency_chain": False,
            "public_readiness_report_schema": COMMANDS_REPLIES_PUBLIC_READINESS_CHECK_SCHEMA,
            "checker": "scripts/check_commands_replies_public_readiness.py",
            "success_advances_to": "p0_dependency_chain_complete_only_after_checker_acceptance",
            "counts_toward_p0_dependency_chain": False,
        },
    ]
    return {
        "schema": "obelisk.sdk-status-p0-offline-roadmap.v1",
        "status_report_only": True,
        "roadmap_only": True,
        "current_route_blocker": current_blocker,
        "remaining_route_blockers": list(remaining_route_blockers),
        "next_required_artifact": APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE,
        "after_runtime_evidence": after_runtime,
        "p0_dependency_chain": list(P0_DEPENDENCY_CHAIN_SURFACES),
        "p0_dependency_chain_progress_ratio": p0_count_summary.get("progress_ratio"),
        "p0_dependency_chain_promoted_for_claim_count": p0_count_summary.get(
            "promoted_for_claim_count"
        ),
        "p0_dependency_chain_remaining_for_claim_count": p0_count_summary.get(
            "remaining_for_claim_count"
        ),
        "next_offline_surface_after_runtime_evidence": "obelisk.player_identity.v1",
        "next_offline_blocker_after_runtime_evidence": after_runtime,
        "post_identity_bridge_required_artifact": (
            PLAYER_IDENTITY_PROMOTION_CERTIFICATE_ARTIFACT
        ),
        "post_identity_bridge_required_schema": (
            PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA
        ),
        "post_identity_bridge_blocker": PLAYER_IDENTITY_PROMOTION_CERTIFICATE_BLOCKER,
        "post_identity_bridge_status": (
            "required_after_identity_public_contract_before_permissions_admin"
        ),
        "post_identity_bridge_hash_bound": True,
        "post_identity_bridge_counts_toward_p0_dependency_chain": False,
        "post_identity_bridge_promotion_ready": False,
        "post_identity_bridge_public_sdk_ready": False,
        "post_identity_bridge_runtime_ready": False,
        "post_permissions_admin_bridge_required_artifact": (
            PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_ARTIFACT
        ),
        "post_permissions_admin_bridge_required_schema": (
            PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA
        ),
        "post_permissions_admin_bridge_counts_toward_p0_dependency_chain": False,
        "post_command_chat_response_bridge_required_artifact": (
            COMMAND_CHAT_RESPONSE_PROMOTION_CERTIFICATE_ARTIFACT
        ),
        "post_command_chat_response_bridge_required_schema": (
            COMMAND_CHAT_RESPONSE_PROMOTION_CERTIFICATE_SCHEMA
        ),
        "post_command_chat_response_bridge_counts_toward_p0_dependency_chain": False,
        "commands_replies_final_gate_required_artifact": (
            COMMANDS_REPLIES_PROMOTION_CERTIFICATE_ARTIFACT
        ),
        "commands_replies_final_gate_required_schema": (
            COMMANDS_REPLIES_PROMOTION_CERTIFICATE_SCHEMA
        ),
        "commands_replies_final_gate_public_readiness_report_schema": (
            COMMANDS_REPLIES_PUBLIC_READINESS_CHECK_SCHEMA
        ),
        "commands_replies_final_gate_status": commands_replies_final_gate["status"],
        "commands_replies_final_gate_source_present": commands_replies_final_gate[
            "source_present"
        ],
        "commands_replies_final_gate_certificate_present": commands_replies_final_gate[
            "certificate_present"
        ],
        "commands_replies_final_gate_certificate_binding_present": (
            commands_replies_final_gate["certificate_binding_present"]
        ),
        "commands_replies_final_gate_source_hash_bound": commands_replies_final_gate[
            "source_hash_bound"
        ],
        "commands_replies_final_gate_missing_required_artifact": (
            commands_replies_final_gate["missing_required_artifact"]
        ),
        "commands_replies_final_gate_hash_bound": True,
        "commands_replies_final_gate_counts_toward_p0_dependency_chain": False,
        "commands_replies_final_gate_counts_toward_complete_sdk_claim": False,
        "commands_replies_final_gate_promotion_ready": False,
        "commands_replies_final_gate_public_sdk_ready": False,
        "commands_replies_final_gate_runtime_ready": False,
        "commands_replies_final_gate_context": commands_replies_final_gate,
        "downstream_offline_order": list(P0_DEPENDENCY_CHAIN_SURFACES),
        "steps": steps,
        "authorizes_runtime_work": False,
        "authorizes_server_operations": False,
        "authorizes_workspace_writes": False,
        "discord_authorized": False,
        "approved_runtime_evidence_ready": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_claim_allowed": False,
        "promotion_ready": False,
        "plugin_hub_ready": False,
        "publication_authorized": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "non_claim": (
            "P0 roadmap is offline planning/status only. It does not accept runtime "
            "evidence, authorize live work, publish SDK surfaces, issue promotion "
            "certificates, or move SDK/P0 progress counters."
        ),
    }


def normalized_report_ready_allowed(
    *,
    public_sdk: dict[str, Any],
    public_sdk_returncode: int,
    current_route_blocker: Any,
    remaining_route_blockers: list[str],
    sdk_count_summary: dict[str, Any],
    p0_count_summary: dict[str, Any],
    non_counting_alias_violations: list[str],
    p0_dependency_chain_full_ordered_promotion_observed: bool,
) -> bool:
    blockers = route_blockers(current_route_blocker, remaining_route_blockers)
    return (
        public_sdk_returncode == 0
        and public_sdk.get("ready") is True
        and not blockers
        and (
            not non_counting_alias_violations
            or p0_dependency_chain_full_ordered_promotion_observed
        )
        and bool(sdk_count_summary.get("ready"))
        and bool(p0_count_summary.get("ready"))
    )


def normalized_status_value(source_status: Any, *, ready_allowed: bool) -> Any:
    if ready_allowed:
        return source_status
    if isinstance(source_status, str) and normalized_alias_key(source_status) in NON_COUNTING_CONTEXT_POSITIVE_STATUS_VALUES:
        return "blocked"
    return source_status


def summarize(
    *,
    public_sdk: dict[str, Any],
    public_sdk_returncode: int,
    header_gate: dict[str, Any],
    header_gate_returncode: int,
    public_contract_decisions: dict[str, Any] | None = None,
    closure: dict[str, Any] | None = None,
    closure_returncode: int | None = None,
    principal_start_end_runtime_evidence: dict[str, Any] | None = None,
    principal_start_end_runtime_evidence_path: Path | str | None = None,
    principal_start_end_runtime_evidence_source: str | None = None,
    multi_surface_beta_capture_pack: dict[str, Any] | None = None,
    multi_surface_beta_capture_pack_path: Path | str | None = None,
    multi_surface_beta_capture_pack_source: str | None = None,
    runtime_evidence_status: dict[str, Any] | None = None,
    runtime_evidence_status_path: Path | str | None = None,
    runtime_evidence_status_source: str | None = None,
    discord_beta_bridge_config: dict[str, Any] | None = None,
    discord_beta_bridge_config_path: Path | str | None = None,
    discord_beta_bridge_config_source: str | None = None,
) -> dict[str, Any]:
    fastest = dict_or_empty(public_sdk.get("fastest_next_sdk_unblock"))
    approved_runtime_checker_accepted = (
        accepted_approved_runtime_principal_lifecycle_bundle(public_sdk)
    )
    source_current_blocker = source_current_route_blocker(public_sdk, fastest)
    source_remaining_blockers = source_remaining_route_blockers(public_sdk, fastest)
    current_route_blocker = fail_closed_current_route_blocker(
        public_sdk,
        fastest,
        approved_runtime_checker_accepted=approved_runtime_checker_accepted,
    )
    remaining_route_blockers = fail_closed_remaining_route_blockers(
        current_route_blocker=current_route_blocker,
        source_remaining_blockers=source_remaining_blockers,
        approved_runtime_checker_accepted=approved_runtime_checker_accepted,
    )
    raw_sdk_count_summary = sdk_counts(public_sdk)
    raw_p0_count_summary = p0_counts(public_sdk)
    non_counting_alias_violations = non_counting_false_progress_alias_violations(public_sdk)
    p0_dependency_chain_full_ordered_promotion_observed = ordered_p0_dependency_chain_promoted(
        public_sdk,
        current_route_blocker=current_route_blocker,
        remaining_route_blockers=remaining_route_blockers,
        p0_count_summary=raw_p0_count_summary,
    )
    blockers_for_normalization = route_blockers(current_route_blocker, remaining_route_blockers)
    count_normalization_reasons = set(blockers_for_normalization)
    if (
        non_counting_alias_violations
        and not p0_dependency_chain_full_ordered_promotion_observed
    ):
        count_normalization_reasons.add("non_counting_false_progress_aliases")
    sdk_count_summary = normalize_count_summary_for_route_blocker(
        raw_sdk_count_summary,
        total_fallback=DEFAULT_COMPLETE_SDK_BLOCKER_TOTAL,
        blockers=count_normalization_reasons,
    )
    p0_count_summary = normalize_count_summary_for_route_blocker(
        raw_p0_count_summary,
        total_fallback=DEFAULT_P0_DEPENDENCY_CHAIN_TOTAL,
        blockers=count_normalization_reasons,
    )
    raw_action_paths = fastest.get("actionable_paths")
    if raw_action_paths is None:
        raw_action_paths = fastest.get("action_paths")
    action_paths = normalize_actionable_paths(raw_action_paths)
    action_paths = ensure_player_notice_action_path(
        action_paths,
        current_route_blocker=current_route_blocker,
    )
    fastest_summary = normalize_fastest_next_sdk_unblock(
        fastest,
        current_route_blocker=current_route_blocker if isinstance(current_route_blocker, str) else None,
        remaining_route_blockers=remaining_route_blockers,
        action_paths=action_paths,
    )
    approved_in_game_evidence = approved_in_game_evidence_status(
        current_route_blocker=current_route_blocker,
        fastest_summary=fastest_summary,
        action_paths=action_paths,
    )
    debug_first_acceleration = debug_first_acceleration_summary(
        current_route_blocker=current_route_blocker,
        remaining_route_blockers=remaining_route_blockers,
        fastest_summary=fastest_summary,
        approved_in_game_evidence=approved_in_game_evidence,
    )
    post_evidence_p0_lock_simulation = normalize_post_evidence_p0_lock_simulation(
        public_sdk,
        current_route_blocker=current_route_blocker,
        remaining_route_blockers=remaining_route_blockers,
    )
    commands_replies_final_gate = commands_replies_final_gate_context(public_sdk)
    p0_offline_roadmap = p0_offline_roadmap_summary(
        current_route_blocker=current_route_blocker,
        remaining_route_blockers=remaining_route_blockers,
        p0_count_summary=p0_count_summary,
        post_evidence_p0_lock_simulation=post_evidence_p0_lock_simulation,
        commands_replies_final_gate=commands_replies_final_gate,
    )
    start_end_runtime_evidence = principal_start_end_runtime_evidence_summary(
        principal_start_end_runtime_evidence,
        source_path=principal_start_end_runtime_evidence_path,
        source_kind=principal_start_end_runtime_evidence_source,
    )
    multi_surface_pack = multi_surface_beta_capture_pack_summary(
        multi_surface_beta_capture_pack,
        source_path=multi_surface_beta_capture_pack_path,
        source_kind=multi_surface_beta_capture_pack_source,
    )
    runtime_evidence_window = runtime_evidence_window_summary(
        runtime_evidence_status,
        source_path=runtime_evidence_status_path,
        source_kind=runtime_evidence_status_source,
    )
    discord_bridge = discord_beta_bridge_config_summary(
        discord_beta_bridge_config,
        source_path=discord_beta_bridge_config_path,
        source_kind=discord_beta_bridge_config_source,
    )
    operator_context = operator_context_summary(public_sdk)
    stable_sdk_remaining_blockers = stable_sdk_remaining_blockers_summary(
        public_sdk=public_sdk,
        current_route_blocker=current_route_blocker,
        remaining_route_blockers=remaining_route_blockers,
        sdk_count_summary=sdk_count_summary,
        p0_count_summary=p0_count_summary,
        fastest_summary=fastest_summary,
        approved_in_game_evidence=approved_in_game_evidence,
        post_evidence_p0_lock_simulation=post_evidence_p0_lock_simulation,
        debug_first_acceleration=debug_first_acceleration,
        operator_context=operator_context,
    )
    side_lanes = normalize_side_lanes(public_sdk)
    side_lane_source_overclaims = summarize_side_lane_source_overclaims(side_lanes)
    header_summary = header_gate_summary(header_gate)
    private_correlation = private_logout_correlation_status(public_contract_decisions)
    report_ready_allowed = normalized_report_ready_allowed(
        public_sdk=public_sdk,
        public_sdk_returncode=public_sdk_returncode,
        current_route_blocker=current_route_blocker,
        remaining_route_blockers=remaining_route_blockers,
        sdk_count_summary=sdk_count_summary,
        p0_count_summary=p0_count_summary,
        non_counting_alias_violations=non_counting_alias_violations,
        p0_dependency_chain_full_ordered_promotion_observed=(
            p0_dependency_chain_full_ordered_promotion_observed
        ),
    )
    source_overclaimed_readiness = []
    if not report_ready_allowed:
        source_overclaimed_readiness = [
            key
            for key in (
                "ready",
                "public_sdk_ready",
                "runtime_ready",
                "stable_claim_allowed",
                "stable_sdk_ready",
            )
            if alias_value_is_positive(public_sdk.get(key))
        ]
        if normalized_status_value(public_sdk.get("status"), ready_allowed=False) != public_sdk.get(
            "status"
        ):
            source_overclaimed_readiness.append("status")
    source_overclaimed_counts = []
    if raw_sdk_count_summary != sdk_count_summary and count_summary_has_positive_progress(
        raw_sdk_count_summary
    ):
        source_overclaimed_counts.extend(
            [
                "complete_sdk_blockers_promoted_for_claim_count",
                "complete_sdk_progress_ratio",
            ]
        )
    if raw_p0_count_summary != p0_count_summary and count_summary_has_positive_progress(
        raw_p0_count_summary
    ):
        source_overclaimed_counts.extend(
            [
                "p0_dependency_chain_promoted_for_claim_count",
                "p0_dependency_chain_progress_ratio",
            ]
        )
    if non_counting_alias_violations and not p0_dependency_chain_full_ordered_promotion_observed:
        source_overclaimed_counts.append("non_counting_false_progress_aliases")
    source_overclaimed_routes = source_route_overclaim_flags(
        source_current_blocker=source_current_blocker,
        source_remaining_blockers=source_remaining_blockers,
        approved_runtime_checker_accepted=approved_runtime_checker_accepted,
    )
    current_live_diagnostic_blockers = runtime_evidence_window.get(
        "current_live_diagnostic_blockers"
    )
    if not isinstance(current_live_diagnostic_blockers, dict):
        current_live_diagnostic_blockers = default_current_live_diagnostic_blockers_context()
    critical_path_summary = {
        "schema": "obelisk.sdk-status-critical-path-summary.v1",
        "status_report_only": True,
        "current_route_blocker": current_route_blocker,
        "remaining_route_blockers": remaining_route_blockers,
        "next_required_artifact": approved_in_game_evidence["next_required_artifact"],
        "missing_required_artifact": approved_in_game_evidence["missing_required_artifact"],
        "after_runtime_evidence": post_evidence_p0_lock_simulation.get(
            "simulated_route_blocker_after_accepted_runtime_evidence"
        ),
        "identity_public_contract_required": bool(
            post_evidence_p0_lock_simulation.get("identity_public_contract_required")
        ),
        "complete_sdk_progress_ratio": sdk_count_summary["progress_ratio"],
        "p0_dependency_chain_progress_ratio": p0_count_summary["progress_ratio"],
        "approved_runtime_evidence_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "stable_claim_allowed": False,
        "live_ops_authorized": False,
        "server_operations_authorized": False,
        "workspace_writes_authorized": False,
        "runtime_capture_authorized": False,
        "discord_authorized": False,
        "publication_authorized": False,
        "plugin_hub_ready": False,
        "plugin_hub_readiness_claim_allowed": False,
        "plugin_hub_publication_allowed": False,
        "debug_first_blocker_chain": debug_first_acceleration["compact_blocker_chain"],
        "debug_first_next_action": debug_first_acceleration["next_action"],
        "current_live_diagnostic_blockers": current_live_diagnostic_blockers,
        "non_claim": (
            "Critical-path status only; it does not approve runtime evidence, "
            "public SDK readiness, P0 progress, stable SDK claims, live ops, "
            "Discord, publication, or workspace writes."
        ),
    }
    report: dict[str, Any] = {
        "schema": "obelisk.sdk-status-report.v1",
        "status_report_only": True,
        "ready": report_ready_allowed,
        "source_ready": alias_value_is_positive(public_sdk.get("ready")),
        "public_sdk_ready": alias_value_is_positive(public_sdk.get("public_sdk_ready")) and report_ready_allowed,
        "source_public_sdk_ready": alias_value_is_positive(public_sdk.get("public_sdk_ready")),
        "runtime_ready": alias_value_is_positive(public_sdk.get("runtime_ready")) and report_ready_allowed,
        "source_runtime_ready": alias_value_is_positive(public_sdk.get("runtime_ready")),
        "stable_claim_allowed": alias_value_is_positive(public_sdk.get("stable_claim_allowed")) and report_ready_allowed,
        "source_stable_claim_allowed": alias_value_is_positive(public_sdk.get("stable_claim_allowed")),
        "stable_sdk_ready": alias_value_is_positive(public_sdk.get("stable_claim_allowed")) and report_ready_allowed,
        "source_stable_sdk_ready": alias_value_is_positive(public_sdk.get("stable_sdk_ready")),
        "source_overclaimed_readiness_flags": source_overclaimed_readiness,
        "status": normalized_status_value(public_sdk.get("status"), ready_allowed=report_ready_allowed),
        "source_status": public_sdk.get("status"),
        "public_sdk_checker_returncode": public_sdk_returncode,
        "header_gate_returncode": header_gate_returncode,
        "current_route_blocker": current_route_blocker,
        "source_current_route_blocker": source_current_blocker,
        "remaining_route_blockers": remaining_route_blockers,
        "source_remaining_route_blockers": source_remaining_blockers,
        "source_overclaimed_route_flags": source_overclaimed_routes,
        "complete_sdk_progress_ratio": sdk_count_summary["progress_ratio"],
        "p0_dependency_chain_progress_ratio": p0_count_summary["progress_ratio"],
        "p0_chain_progress_ratio": p0_count_summary["progress_ratio"],
        "sdk_counts": sdk_count_summary,
        "p0_counts": p0_count_summary,
        "source_sdk_counts": raw_sdk_count_summary,
        "source_p0_counts": raw_p0_count_summary,
        "source_overclaimed_count_flags": source_overclaimed_counts,
        "non_counting_false_progress_alias_violations": non_counting_alias_violations,
        "non_counting_false_progress_alias_count": len(non_counting_alias_violations),
        "p0_dependency_chain_full_ordered_promotion_observed": (
            p0_dependency_chain_full_ordered_promotion_observed
        ),
        "complete_sdk_blockers_promoted_for_claim_count": sdk_count_summary[
            "promoted_for_claim_count"
        ],
        "complete_sdk_blockers_remaining_for_claim_count": sdk_count_summary[
            "remaining_for_claim_count"
        ],
        "complete_sdk_blocker_total": sdk_count_summary["total"],
        "p0_dependency_chain_promoted_for_claim_count": p0_count_summary[
            "promoted_for_claim_count"
        ],
        "p0_dependency_chain_remaining_for_claim_count": p0_count_summary[
            "remaining_for_claim_count"
        ],
        "p0_dependency_chain_total": p0_count_summary["total"],
        "fastest_next_action": fastest_summary.get("recommended_next_action"),
        "next_action_sequence": fastest_summary.get("next_action_sequence", []),
        "next_action_sequence_metadata_only": True,
        "fastest_next_sdk_unblock": fastest_summary,
        "approved_in_game_evidence_ready": approved_in_game_evidence[
            "approved_in_game_evidence_ready"
        ],
        "approved_runtime_evidence_ready": approved_in_game_evidence[
            "approved_runtime_evidence_ready"
        ],
        "plugin_hub_ready": False,
        "plugin_hub_readiness_claim_allowed": False,
        "plugin_hub_publication_allowed": False,
        "publication_authorized": False,
        "next_required_artifact": approved_in_game_evidence["next_required_artifact"],
        "missing_required_artifact": approved_in_game_evidence[
            "missing_required_artifact"
        ],
        "critical_path_summary": critical_path_summary,
        "stable_sdk_remaining_blockers": stable_sdk_remaining_blockers,
        "operator_context_summary": operator_context,
        "debug_first_acceleration": debug_first_acceleration,
        "debug_first_blocker_chain": debug_first_acceleration["compact_blocker_chain"],
        "debug_first_next_action": debug_first_acceleration["next_action"],
        "approved_in_game_evidence": approved_in_game_evidence,
        "post_evidence_p0_lock_simulation": post_evidence_p0_lock_simulation,
        "commands_replies_final_gate": commands_replies_final_gate,
        "p0_offline_roadmap": p0_offline_roadmap,
        "principal_start_end_runtime_evidence": start_end_runtime_evidence,
        "multi_surface_beta_capture_pack": multi_surface_pack,
        "runtime_evidence_window": runtime_evidence_window,
        "current_live_diagnostic_blockers": current_live_diagnostic_blockers,
        "discord_beta_bridge": discord_bridge,
        "partial_contract_review_inputs": {
            "status_report_only": True,
            "contract_review_input_only": True,
            "principal_start_end_runtime_evidence": start_end_runtime_evidence,
            "input_ids": (
                ["principal_start_end_runtime_evidence"]
                if start_end_runtime_evidence.get("source_present") is True
                else []
            ),
            "accepted_input_ids": (
                ["principal_start_end_runtime_evidence"]
                if start_end_runtime_evidence.get("accepted_for_contract_review") is True
                else []
            ),
            "counts_as_approved_runtime_evidence": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "stable_claim_allowed": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
            "non_claim": (
                "Partial contract-review inputs are visible for routing context only; "
                "they do not change approved runtime evidence, route blockers, SDK/P0 "
                "progress, runtime readiness, public SDK readiness, or stable claims."
            ),
        },
        "route_gate": {
            "status_report_only": True,
            "current_route_blocker": post_evidence_p0_lock_simulation.get(
                "current_route_blocker"
            ),
            "remaining_route_blockers": post_evidence_p0_lock_simulation.get(
                "remaining_route_blockers"
            ),
            "post_evidence_p0_lock_simulation": post_evidence_p0_lock_simulation,
            "live_ops_authorized": False,
            "server_operations_authorized": False,
            "workspace_writes_authorized": False,
            "runtime_capture_authorized": False,
            "reads_live_logs": False,
            "read_live_logs": False,
            "publication_authorized": False,
            "plugin_hub_ready": False,
            "plugin_hub_readiness_claim_allowed": False,
            "plugin_hub_publication_allowed": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "stable_claim_allowed": False,
            "non_claim": (
                "route-gate status reporting only; post-evidence simulation does "
                "not authorize live ops, runtime capture, workspace writes, public "
                "readiness, runtime readiness, P0 progress, or SDK completion"
            ),
        },
        "actionable_paths": action_paths,
        "action_paths": action_paths,
        "actionable_path_count": len(action_paths),
        "side_lanes": side_lanes,
        "non_claim_side_lanes": side_lanes,
        "side_lane_count": len(side_lanes),
        "side_lane_source_overclaim_count": side_lane_source_overclaims["count"],
        "side_lane_source_overclaim_side_lanes": side_lane_source_overclaims[
            "side_lane_ids"
        ],
        "side_lane_source_overclaim_authorization_or_claim_flag_count": (
            side_lane_source_overclaims["authorization_or_claim_flag_count"]
        ),
        "side_lane_source_overclaim_progress_flag_count": side_lane_source_overclaims[
            "progress_flag_count"
        ],
        "side_lane_source_overclaim_total_flag_count": side_lane_source_overclaims[
            "total_flag_count"
        ],
        "side_lane_source_overclaims": side_lane_source_overclaims,
        "side_lane_non_claim": (
            "Transfer ScriptStruct, Buff status manifest/source binding, Dino scalar, "
            "and Mission/Transfer/Dino/Tribe/Buff accounting summaries are status-only "
            "side lanes here. The status report consumes only precomputed JSON and "
            "does not run extra side-lane checkers."
        ),
        "private_logout_correlation": private_correlation,
        "internal_blockers": {
            "private_logout_correlation": private_correlation,
        },
        "public_header_readiness": header_summary,
        "header_gate": header_summary,
        "authorizations": {
            "live_ops_authorized": False,
            "server_operations_authorized": False,
            "workspace_writes_authorized": False,
            "runtime_capture_authorized": False,
            "reads_live_logs": False,
            "read_live_logs": False,
            "discord_authorized": False,
            "player_notice_action_authorized": False,
            "passive_snapshots_count_as_evidence": False,
            "player_notices_count_as_evidence": False,
            "accepted_runtime_evidence_counts_toward_progress": False,
            "closure_requests_count_as_approved_runtime_evidence": False,
            "publication_authorized": False,
            "plugin_hub_readiness_claim_allowed": False,
        },
        "non_claims": [
            "status report only; does not authorize server operations, marker/env changes, starts, stops, restarts, or runtime capture",
            "does not make approved runtime evidence, public SDK readiness, runtime readiness, v1 completion, or stable SDK status true",
            "approved in-game evidence remains false until an approved copied runtime principal lifecycle evidence bundle is accepted",
            "request packs, player notices, notice dry-runs, accepted runtime evidence, sidecars, passive snapshots, and closure requests contribute 0 to SDK/P0 progress",
            "passive monitor output and closure requests remain non-evidence until approved evidence checkers accept the copied sibling-set bundle",
            "post-reboot passive monitor context and confirmed beta notices are operator context only and contribute 0 to SDK/P0 progress, runtime readiness, public SDK readiness, release readiness, and stable SDK claims",
            "post_evidence_p0_lock_simulation is simulation-only: accepted runtime evidence still does not unlock P0 progress, public SDK readiness, runtime readiness, public ABI/header readiness, live ops, runtime capture, or workspace writes",
            "p0_offline_roadmap is status-only planning and does not accept runtime evidence, authorize live work, publish SDK surfaces, or move SDK/P0 counters",
            "commands/replies final-gate certificates are visible only as non-counting roadmap/status context and never imply SDK/P0 progress, runtime readiness, publication, or authorization",
            "principal start/end runtime evidence is a contract-review input only and does not satisfy approved runtime evidence, rejected-start CheckJoin proof, SDK/P0 progress, runtime readiness, public SDK readiness, or stable SDK claims",
            "multi-surface beta capture packs are planning-only candidate capture context and do not satisfy approved runtime evidence, SDK/P0 progress, runtime readiness, public SDK readiness, or stable SDK claims",
            "runtime-evidence window status artifacts are offline context only and do not satisfy approved runtime evidence, SDK/P0 progress, runtime readiness, public SDK readiness, or stable SDK claims",
            "live diagnostic context is status-only; stale operator-supplied blockers are suppressed unless a current posture input provides them, and no live context advances SDK/P0 progress",
            "Discord beta bridge config is communication posture only and does not authorize Discord sends, live ops, runtime evidence, SDK/P0 progress, public readiness, stable readiness, Plugin Hub readiness, or publication",
            "runtime-window plans, executor/preactivation reports, request checks, activation preconditions, and approved-runtime manifest path references are non-evidence until the approved copied bundle checker accepts them",
            "Transfer ScriptStruct, Buff status manifest/source binding, Dino scalar, and Mission/Transfer/Dino/Tribe/Buff accounting summaries are non-authorizing side lanes and contribute 0 to complete SDK and P0 progress",
            "private logout correlation remains internal planning only: no public lookup, no identity exposure, no ABI/header readiness, no live authorization",
            "next_action_sequence is planning metadata only and never counts as runtime evidence, SDK/P0 progress, public readiness, Plugin Hub readiness, publication authority, or approved evidence",
            "debug-first acceleration metadata keeps the blocker path visible but does not authorize runtime work or count toward SDK/P0 progress",
        ],
    }
    if closure is not None:
        closure_readiness_claims = closure.get("readiness_claims") or {}
        source_public_sdk_ready = alias_value_is_positive(closure_readiness_claims.get("public_sdk_ready"))
        source_runtime_ready = alias_value_is_positive(closure_readiness_claims.get("runtime_ready"))
        source_overclaimed_closure_evidence = [
            key
            for key in (
                "approved_runtime_evidence",
                "approved_runtime_evidence_present",
                "counts_as_approved_runtime_evidence",
                "runtime_evidence_present",
                "runtime_evidence_ready",
            )
            if alias_value_is_positive(closure.get(key))
        ]
        source_overclaimed_closure_readiness = []
        if source_public_sdk_ready:
            source_overclaimed_closure_readiness.append("public_sdk_ready")
        if source_runtime_ready:
            source_overclaimed_closure_readiness.append("runtime_ready")
        report["closure"] = {
            "returncode": closure_returncode,
            "ready": False,
            "ready_scope": "normalized_status_report_only_not_public_or_runtime_readiness",
            "input_presence_ready": alias_value_is_positive(closure.get("ready")),
            "status": closure.get("status"),
            "evidence_dir": closure.get("evidence_dir"),
            "missing_required_artifacts": list(closure.get("missing_required_artifacts") or []),
            "present_siblings": list(closure.get("present_siblings") or []),
            "server_operations_authorized": False,
            "workspace_writes_authorized": False,
            "source_server_operations_authorized": bool(closure.get("server_operations_authorized")),
            "source_workspace_writes_authorized": bool(closure.get("workspace_writes_authorized")),
            "closure_request_only": True,
            "counts_as_approved_runtime_evidence": False,
            "approved_runtime_evidence": False,
            "approved_runtime_evidence_present": False,
            "runtime_evidence_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "source_public_sdk_ready": source_public_sdk_ready,
            "source_runtime_ready": source_runtime_ready,
            "source_overclaimed_readiness_flags": source_overclaimed_closure_readiness,
            "source_overclaimed_evidence_flags": source_overclaimed_closure_evidence,
        }
    report["source_overclaim_summary"] = summarize_report_source_overclaims(report)
    report["source_overclaim_total_flag_count"] = report["source_overclaim_summary"][
        "total_flag_count"
    ]
    report["source_overclaim_component_count"] = report["source_overclaim_summary"][
        "component_count"
    ]
    return report


def format_count_summary(label: str, counts: dict[str, Any]) -> str:
    promoted = counts.get("promoted_for_claim_count")
    total = counts.get("total")
    remaining = counts.get("remaining_for_claim_count")
    ratio = counts.get("progress_ratio")
    if promoted is not None and total is not None:
        return f"{label}: {promoted}/{total} promoted_for_claim; remaining={remaining}; ratio={ratio}"
    return f"{label}: ratio={ratio}; remaining={remaining}"


def compact_string(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    return None


def compact_string_values(value: Any) -> list[str]:
    if isinstance(value, str) and value:
        return [value]
    return string_list(value)


def format_compact_list(values: list[str]) -> str:
    return ",".join(values) if values else "none"


def format_action_path_target(target: Any) -> str:
    if isinstance(target, str) and target:
        return target
    if not isinstance(target, dict):
        return "unspecified"

    instance = compact_string(target.get("instance"))
    map_name = compact_string(target.get("map"))
    if instance and map_name:
        return f"{instance}/{map_name}"

    ordered_keys = ("instance", "map", "server", "cluster", "surface", "evidence_dir", "path")
    parts: list[str] = []
    seen: set[str] = set()
    for key in ordered_keys:
        value = compact_string(target.get(key))
        if value is not None:
            parts.append(f"{key}={value}")
            seen.add(key)
    for key in sorted(key for key in target if key not in seen):
        value = compact_string(target.get(key))
        if value is not None:
            parts.append(f"{key}={value}")
    return ",".join(parts) if parts else "unspecified"


def action_path_missing_roles(path_payload: dict[str, Any]) -> list[str]:
    for key in (
        "missing_event_roles",
        "missing_roles",
        "missing_required_event_roles",
        "required_event_roles_missing",
    ):
        values = compact_string_values(path_payload.get(key))
        if values:
            return values
    return []


def action_path_present_roles(path_payload: dict[str, Any]) -> list[str]:
    return role_values_from_path(path_payload, ("present_event_roles",))


def format_action_path_line(path_id: str, path_payload: dict[str, Any]) -> str:
    target = format_action_path_target(path_payload.get("target"))
    missing_roles = format_compact_list(action_path_missing_roles(path_payload))
    evidence_status = compact_string(path_payload.get("evidence_status")) or "unknown"
    authorization = compact_string(path_payload.get("authorization")) or "non-authorizing"
    parts = [
        f"target={target}",
        f"missing_roles={missing_roles}",
        f"evidence_status={evidence_status}",
        f"authorization={authorization}",
    ]
    path_status = compact_string(path_payload.get("path_status"))
    if path_status:
        parts.append(f"path_status={path_status}")
    role_source_status = compact_string(path_payload.get("role_source_status"))
    if role_source_status:
        parts.append(f"role_source_status={role_source_status}")
    trusted_role_source = path_payload.get("role_source_trusted_for_current_status")
    if isinstance(trusted_role_source, bool):
        parts.append(f"role_source_trusted={str(trusted_role_source).lower()}")
    present_roles = action_path_present_roles(path_payload)
    if present_roles:
        parts.append(f"present_roles={format_compact_list(present_roles)}")
    required_next_event_role = compact_string(path_payload.get("required_next_event_role"))
    if required_next_event_role:
        parts.append(f"required_next_role={required_next_event_role}")
    required_next_artifact = compact_string(path_payload.get("required_next_artifact"))
    if required_next_artifact:
        parts.append(f"required_next={required_next_artifact}")
    approved_bundle_required = path_payload.get("approved_bundle_required")
    if isinstance(approved_bundle_required, bool):
        parts.append(f"approved_bundle_required={str(approved_bundle_required).lower()}")
    player_notice_action_required = path_payload.get("player_notice_action_required")
    if isinstance(player_notice_action_required, bool):
        parts.append(
            "player_notice_action_required="
            f"{str(player_notice_action_required).lower()}"
        )
    notice_action_authorized = path_payload.get("notice_action_authorized")
    if isinstance(notice_action_authorized, bool):
        parts.append(
            "notice_action_authorized="
            f"{str(notice_action_authorized).lower()}"
        )
    discord_authorized = path_payload.get("discord_authorized")
    if isinstance(discord_authorized, bool):
        parts.append(f"discord_authorized={str(discord_authorized).lower()}")
    counts_as_approved_runtime_evidence = path_payload.get("counts_as_approved_runtime_evidence")
    if isinstance(counts_as_approved_runtime_evidence, bool):
        parts.append(
            "approved_runtime_evidence="
            f"{str(counts_as_approved_runtime_evidence).lower()}"
        )
    source_overclaims = compact_string_values(path_payload.get("source_overclaimed_authorization_flags"))
    if source_overclaims:
        parts.append(f"source_overclaims={format_compact_list(source_overclaims)}")
    return f"  - {path_id}: " + "; ".join(parts)


def format_false_authorizations(report: dict[str, Any]) -> str:
    authorizations = report.get("authorizations")
    if not isinstance(authorizations, dict):
        authorizations = {}
    return (
        "false authorizations: "
        f"live_ops={str(bool(authorizations.get('live_ops_authorized'))).lower()}; "
        f"server_operations={str(bool(authorizations.get('server_operations_authorized'))).lower()}; "
        f"workspace_writes={str(bool(authorizations.get('workspace_writes_authorized'))).lower()}; "
        f"runtime_capture={str(bool(authorizations.get('runtime_capture_authorized'))).lower()}; "
        f"reads_live_logs={str(bool(authorizations.get('reads_live_logs'))).lower()}; "
        f"discord={str(bool(authorizations.get('discord_authorized'))).lower()}; "
        "approved_runtime_evidence="
        f"{str(bool(authorizations.get('closure_requests_count_as_approved_runtime_evidence'))).lower()}; "
        "player_notices_as_evidence="
        f"{str(bool(authorizations.get('player_notices_count_as_evidence'))).lower()}; "
        "passive_snapshots_as_evidence="
        f"{str(bool(authorizations.get('passive_snapshots_count_as_evidence'))).lower()}"
    )


def format_private_logout_correlation(report: dict[str, Any]) -> str:
    private_correlation = report.get("private_logout_correlation")
    if not isinstance(private_correlation, dict):
        private_correlation = {}
    return (
        "private_logout_correlation: "
        f"status={private_correlation.get('status')}; "
        f"current_blocker={private_correlation.get('current_blocker')}; "
        "internal_blocker_active="
        f"{str(bool(private_correlation.get('internal_blocker_active'))).lower()}; "
        "public_lookup="
        f"{str(bool(private_correlation.get('public_lookup_allowed'))).lower()}; "
        "identity_exposure="
        f"{str(bool(private_correlation.get('identity_exposure_allowed'))).lower()}; "
        "public_abi_ready="
        f"{str(bool(private_correlation.get('public_abi_ready'))).lower()}; "
        "public_header_ready="
        f"{str(bool(private_correlation.get('public_header_ready'))).lower()}; "
        "live_authorization="
        f"{str(bool(private_correlation.get('live_authorization_allowed'))).lower()}"
    )


def format_post_evidence_p0_lock_simulation(report: dict[str, Any]) -> str:
    simulation = report.get("post_evidence_p0_lock_simulation")
    if not isinstance(simulation, dict):
        simulation = {}
    parts = [
        f"simulation_only={str(bool(simulation.get('simulation_only'))).lower()}",
        (
            "approved_runtime_evidence_accepted="
            f"{str(bool(simulation.get('approved_runtime_evidence_accepted'))).lower()}"
        ),
        f"current_route_blocker={simulation.get('current_route_blocker')}",
        (
            "simulated_after_accepted_runtime_evidence="
            f"{simulation.get('simulated_route_blocker_after_accepted_runtime_evidence')}"
        ),
        (
            "identity_public_contract_required="
            f"{str(bool(simulation.get('identity_public_contract_required'))).lower()}"
        ),
        (
            "permissions_admin_unlocked="
            f"{str(bool(simulation.get('permissions_admin_unlocked'))).lower()}"
        ),
        (
            "command_response_unlocked="
            f"{str(bool(simulation.get('command_response_unlocked'))).lower()}"
        ),
        (
            "commands_replies_unlocked="
            f"{str(bool(simulation.get('commands_replies_unlocked'))).lower()}"
        ),
        f"public_sdk_ready={str(bool(simulation.get('public_sdk_ready'))).lower()}",
        f"public_abi_ready={str(bool(simulation.get('public_abi_ready'))).lower()}",
        f"public_header_allowed={str(bool(simulation.get('public_header_allowed'))).lower()}",
        f"runtime_ready={str(bool(simulation.get('runtime_ready'))).lower()}",
        (
            "complete_sdk_progress="
            f"{simulation.get('complete_sdk_claim_progress_contribution')}"
        ),
        (
            "p0_progress="
            f"{simulation.get('p0_dependency_chain_claim_progress_contribution')}"
        ),
        f"live_ops_authorized={str(bool(simulation.get('live_ops_authorized'))).lower()}",
        (
            "workspace_writes_authorized="
            f"{str(bool(simulation.get('workspace_writes_authorized'))).lower()}"
        ),
        (
            "runtime_capture_authorized="
            f"{str(bool(simulation.get('runtime_capture_authorized'))).lower()}"
        ),
    ]
    source_overclaims = compact_string_values(
        simulation.get("source_overclaimed_readiness_or_authorization_flags")
    )
    if source_overclaims:
        parts.append(f"source_overclaims={format_compact_list(source_overclaims)}")
    source_progress_overclaims = compact_string_values(
        simulation.get("source_overclaimed_progress_flags")
    )
    if source_progress_overclaims:
        parts.append(
            f"source_progress_overclaims={format_compact_list(source_progress_overclaims)}"
        )
    return "post_evidence_p0_lock_simulation: " + "; ".join(parts)


def format_p0_offline_roadmap(report: dict[str, Any]) -> str:
    roadmap = report.get("p0_offline_roadmap")
    if not isinstance(roadmap, dict):
        roadmap = {}
    return (
        "p0_offline_roadmap: "
        f"current={roadmap.get('current_route_blocker')}; "
        f"next_runtime={roadmap.get('next_required_artifact')}; "
        f"after_runtime={roadmap.get('after_runtime_evidence')}; "
        "next_offline_surface="
        f"{roadmap.get('next_offline_surface_after_runtime_evidence')}; "
        "post_identity_bridge="
        f"{roadmap.get('post_identity_bridge_required_artifact')}; "
        "post_permissions_bridge="
        f"{roadmap.get('post_permissions_admin_bridge_required_artifact')}; "
        "post_command_response_bridge="
        f"{roadmap.get('post_command_chat_response_bridge_required_artifact')}; "
        "commands_replies_final_gate="
        f"{roadmap.get('commands_replies_final_gate_required_artifact')}; "
        "commands_replies_final_gate_schema="
        f"{roadmap.get('commands_replies_final_gate_required_schema')}; "
        "commands_replies_final_gate_status="
        f"{roadmap.get('commands_replies_final_gate_status')}; "
        "commands_replies_final_gate_present="
        f"{str(bool(roadmap.get('commands_replies_final_gate_certificate_present'))).lower()}; "
        "downstream_order="
        f"{format_compact_list(compact_string_values(roadmap.get('downstream_offline_order')))}; "
        "roadmap_only="
        f"{str(bool(roadmap.get('roadmap_only'))).lower()}; "
        "approved_runtime_evidence_ready="
        f"{str(bool(roadmap.get('approved_runtime_evidence_ready'))).lower()}; "
        f"runtime_ready={str(bool(roadmap.get('runtime_ready'))).lower()}; "
        f"public_sdk_ready={str(bool(roadmap.get('public_sdk_ready'))).lower()}; "
        "SDK_progress="
        f"{roadmap.get('complete_sdk_claim_progress_contribution')}; "
        "P0_progress="
        f"{roadmap.get('p0_dependency_chain_claim_progress_contribution')}"
    )


def format_principal_start_end_runtime_evidence(report: dict[str, Any]) -> str:
    start_end = report.get("principal_start_end_runtime_evidence")
    if not isinstance(start_end, dict):
        start_end = {}
    parts = [
        f"source_present={str(bool(start_end.get('source_present'))).lower()}",
        (
            "accepted_for_contract_review="
            f"{str(bool(start_end.get('accepted_for_contract_review'))).lower()}"
        ),
        (
            "principal_start_end_ready="
            f"{str(bool(start_end.get('principal_start_end_runtime_evidence_ready'))).lower()}"
        ),
        f"source_kind={start_end.get('source_kind') or 'none'}",
        f"source_path={start_end.get('source_path') or 'none'}",
        (
            "approved_runtime_evidence="
            f"{str(bool(start_end.get('approved_runtime_evidence'))).lower()}"
        ),
        f"runtime_ready={str(bool(start_end.get('runtime_ready'))).lower()}",
        f"public_sdk_ready={str(bool(start_end.get('public_sdk_ready'))).lower()}",
        f"stable_claim_allowed={str(bool(start_end.get('stable_claim_allowed'))).lower()}",
        (
            "complete_sdk_progress="
            f"{start_end.get('complete_sdk_claim_progress_contribution')}"
        ),
        (
            "p0_progress="
            f"{start_end.get('p0_dependency_chain_claim_progress_contribution')}"
        ),
    ]
    source_overclaims = compact_string_values(
        start_end.get("source_overclaimed_readiness_or_authorization_flags")
    )
    if source_overclaims:
        parts.append(f"source_overclaims={format_compact_list(source_overclaims)}")
    source_progress_overclaims = compact_string_values(
        start_end.get("source_overclaimed_progress_flags")
    )
    if source_progress_overclaims:
        parts.append(
            f"source_progress_overclaims={format_compact_list(source_progress_overclaims)}"
        )
    return "principal_start_end_runtime_evidence: " + "; ".join(parts)


def format_multi_surface_beta_capture_pack(report: dict[str, Any]) -> str:
    pack = report.get("multi_surface_beta_capture_pack")
    if not isinstance(pack, dict):
        pack = {}
    parts = [
        f"source_present={str(bool(pack.get('source_present'))).lower()}",
        (
            "candidate_pack_validated="
            f"{str(bool(pack.get('candidate_pack_validated'))).lower()}"
        ),
        f"status={pack.get('status')}",
        f"source_status={pack.get('source_status') or 'none'}",
        f"source_kind={pack.get('source_kind') or 'none'}",
        f"target={format_action_path_target(pack.get('target'))}",
        f"surface_count={pack.get('candidate_surface_count')}",
        f"source_path={pack.get('source_path') or 'none'}",
        (
            "approved_runtime_evidence="
            f"{str(bool(pack.get('approved_runtime_evidence'))).lower()}"
        ),
        f"runtime_ready={str(bool(pack.get('runtime_ready'))).lower()}",
        f"public_sdk_ready={str(bool(pack.get('public_sdk_ready'))).lower()}",
        f"stable_sdk_ready={str(bool(pack.get('stable_sdk_ready'))).lower()}",
        (
            "complete_sdk_progress="
            f"{pack.get('complete_sdk_claim_progress_contribution')}"
        ),
        (
            "p0_progress="
            f"{pack.get('p0_dependency_chain_claim_progress_contribution')}"
        ),
    ]
    source_overclaims = compact_string_values(
        pack.get("source_overclaimed_readiness_or_authorization_flags")
    )
    if source_overclaims:
        parts.append(f"source_overclaims={format_compact_list(source_overclaims)}")
    source_progress_overclaims = compact_string_values(
        pack.get("source_overclaimed_progress_flags")
    )
    if source_progress_overclaims:
        parts.append(
            f"source_progress_overclaims={format_compact_list(source_progress_overclaims)}"
        )
    return "multi_surface_beta_capture_pack: " + "; ".join(parts)


def format_discord_beta_bridge(report: dict[str, Any]) -> str:
    bridge = report.get("discord_beta_bridge")
    if not isinstance(bridge, dict):
        bridge = {}
    parts = [
        f"source_present={str(bool(bridge.get('source_present'))).lower()}",
        f"config_valid={str(bool(bridge.get('config_valid'))).lower()}",
        f"token_present={str(bool(bridge.get('token_present'))).lower()}",
        f"discord_py_available={str(bool(bridge.get('discord_py_available'))).lower()}",
        f"guild_id={bridge.get('guild_id') or 'none'}",
        f"channel_id={bridge.get('beta_channel_id') or 'none'}",
        f"discord_authorized={str(bool(bridge.get('discord_authorized'))).lower()}",
        "SDK_progress="
        f"{bridge.get('complete_sdk_claim_progress_contribution')}",
        "P0_progress="
        f"{bridge.get('p0_dependency_chain_claim_progress_contribution')}",
    ]
    blockers = compact_string_values(bridge.get("blockers"))
    if blockers:
        parts.append(f"blockers={format_compact_list(blockers)}")
    source_overclaims = compact_string_values(
        bridge.get("source_overclaimed_readiness_or_authorization_flags")
    )
    if source_overclaims:
        parts.append(f"source_overclaims={format_compact_list(source_overclaims)}")
    return "discord_beta_bridge: " + "; ".join(parts)


def format_runtime_evidence_window(report: dict[str, Any]) -> str:
    window = report.get("runtime_evidence_window")
    if not isinstance(window, dict):
        window = {}
    missing_roles = format_compact_list(
        compact_string_values(window.get("missing_lifecycle_event_roles"))
    )
    missing_artifacts = format_compact_list(
        compact_string_values(window.get("missing_required_artifacts"))
    )
    beta_notice = (
        "completed"
        if window.get("confirmed_beta_notice_completed") is True
        else "present"
        if window.get("confirmed_beta_notice_json_supplied") is True
        else "none"
    )
    copy_ready = compact_string(window.get("copy_readiness")) or compact_string(
        window.get("copy_ready_status")
    )
    if not copy_ready:
        copy_ready = (
            "observer_only_no_roles"
            if window.get("copy_ready_active_observer_only_no_role_window") is True
            else "none"
        )
    parts = [
        f"source_present={str(bool(window.get('source_present'))).lower()}",
        f"status={window.get('status')}",
        f"window_state={window.get('window_state')}",
        f"route_blocker={window.get('route_blocker')}",
        f"players={window.get('player_context')}",
        f"monitor_tick={window.get('monitor_latest_tick_utc') or 'none'}",
        f"beta_notice={beta_notice}",
        f"copy_ready={copy_ready}",
        f"missing_roles={missing_roles}",
        f"missing_artifacts={missing_artifacts}",
        f"next_input={window.get('next_status_input_needed') or 'none'}",
        (
            "approved_runtime_evidence="
            f"{str(bool(window.get('approved_runtime_evidence'))).lower()}"
        ),
        f"runtime_ready={str(bool(window.get('runtime_ready'))).lower()}",
        f"public_sdk_ready={str(bool(window.get('public_sdk_ready'))).lower()}",
        (
            "complete_sdk_progress="
            f"{window.get('complete_sdk_claim_progress_contribution')}"
        ),
        (
            "p0_progress="
            f"{window.get('p0_dependency_chain_claim_progress_contribution')}"
        ),
    ]
    source_overclaims = compact_string_values(
        window.get("source_overclaimed_readiness_or_authorization_flags")
    )
    if source_overclaims:
        parts.append(f"source_overclaims={format_compact_list(source_overclaims)}")
    source_progress_overclaims = compact_string_values(
        window.get("source_overclaimed_progress_flags")
    )
    if source_progress_overclaims:
        parts.append(
            f"source_progress_overclaims={format_compact_list(source_progress_overclaims)}"
        )
    return "runtime_evidence_window: " + "; ".join(parts)


def format_current_live_diagnostic_blockers(report: dict[str, Any]) -> str:
    context = report.get("current_live_diagnostic_blockers")
    if not isinstance(context, dict):
        context = {}
    stale_suppressed = context.get("stale_operator_supplied_blockers_suppressed") is True
    current_posture_input = context.get("current_posture_input_present") is True
    if stale_suppressed:
        label = "stale live diagnostic context"
    elif current_posture_input:
        label = "current live diagnostic context"
    else:
        label = "current live diagnostic blockers"
    inactive = context.get("inactive_or_unknown_targets")
    inactive_labels: list[str] = []
    if isinstance(inactive, list):
        for item in inactive:
            if not isinstance(item, dict):
                continue
            target = format_action_path_target(item)
            state = compact_string(item.get("state")) or "inactive_or_unknown"
            inactive_labels.append(f"{target}:{state}")
    blockers = context.get("next_blockers")
    blocker_parts: list[str] = []
    if isinstance(blockers, list):
        for blocker in blockers:
            if not isinstance(blocker, dict):
                continue
            target = format_action_path_target(blocker.get("target"))
            blocker_id = compact_string(blocker.get("blocker")) or "unknown"
            players = compact_string(blocker.get("player_count_current"))
            accepted = compact_string(blocker.get("accepted_lifecycle_event_count"))
            suffix_parts = []
            if players is not None:
                suffix_parts.append(f"players={players}")
            if accepted is not None:
                suffix_parts.append(f"accepted_events={accepted}")
            if blocker.get("diagnostic_fname_drift") is True:
                suffix_parts.append("fname_drift=true")
            suffix = ",".join(suffix_parts)
            blocker_parts.append(
                f"{target}:{blocker_id}" + (f"({suffix})" if suffix else "")
            )
    if stale_suppressed:
        blocker_text = "suppressed_stale_operator_context"
    else:
        blocker_text = format_compact_list(blocker_parts)
    return (
        f"{label}: "
        f"source={context.get('source') or 'none'}; "
        f"freshness={context.get('source_freshness') or 'unspecified'}; "
        "current_posture_input="
        f"{str(current_posture_input).lower()}; "
        "stale_blockers_suppressed="
        f"{str(stale_suppressed).lower()}; "
        f"active_servers={context.get('active_ark_server_count')}; "
        f"primary={context.get('primary_next_blocker')}; "
        f"secondary={context.get('secondary_next_blocker')}; "
        f"blockers={blocker_text}; "
        "stale_blocker_count="
        f"{len(context.get('stale_operator_supplied_next_blockers') or [])}; "
        f"inactive_or_unknown={format_compact_list(inactive_labels)}; "
        "approved_runtime_evidence="
        f"{str(bool(context.get('approved_runtime_evidence'))).lower()}; "
        f"SDK_progress={context.get('sdk_progress')}; "
        f"P0_progress={context.get('p0_progress')}"
    )


def format_debug_first_acceleration(report: dict[str, Any]) -> str:
    debug_first = report.get("debug_first_acceleration")
    if not isinstance(debug_first, dict):
        debug_first = {}
    roles = format_compact_list(
        compact_string_values(debug_first.get("required_event_roles"))
    )
    return (
        "debug-first path: "
        f"{debug_first.get('compact_blocker_chain')}; "
        f"next_action={debug_first.get('next_action')}; "
        f"next_required_artifact={debug_first.get('next_required_artifact')}; "
        f"checker={debug_first.get('next_checker')}; "
        f"roles={roles}; "
        f"authorization={debug_first.get('authorization')}; "
        "live_ops_authorized="
        f"{str(bool(debug_first.get('live_ops_authorized'))).lower()}; "
        "runtime_capture_authorized="
        f"{str(bool(debug_first.get('runtime_capture_authorized'))).lower()}; "
        "workspace_writes_authorized="
        f"{str(bool(debug_first.get('workspace_writes_authorized'))).lower()}; "
        "approved_runtime_evidence_ready="
        f"{str(bool(debug_first.get('approved_runtime_evidence_ready'))).lower()}; "
        "SDK_progress="
        f"{debug_first.get('complete_sdk_claim_progress_contribution')}; "
        "P0_progress="
        f"{debug_first.get('p0_dependency_chain_claim_progress_contribution')}"
    )


def format_stable_sdk_remaining_blockers(report: dict[str, Any]) -> str:
    stable_blockers = report.get("stable_sdk_remaining_blockers")
    if not isinstance(stable_blockers, dict):
        stable_blockers = {}
    operator_context_ids = format_compact_list(
        compact_string_values(stable_blockers.get("operator_context_ids"))
    )
    return (
        "stable SDK remaining blockers: "
        f"SDK={stable_blockers.get('complete_sdk_progress_ratio')}; "
        f"SDK_remaining={stable_blockers.get('complete_sdk_remaining_for_claim_count')}; "
        f"P0={stable_blockers.get('p0_dependency_chain_progress_ratio')}; "
        f"P0_remaining={stable_blockers.get('p0_dependency_chain_remaining_for_claim_count')}; "
        f"current={stable_blockers.get('current_route_blocker')}; "
        f"next={stable_blockers.get('next_required_artifact')}; "
        f"p0_next={stable_blockers.get('current_p0_surface')}; "
        f"after_runtime_evidence={stable_blockers.get('after_runtime_evidence')}; "
        f"operator_context={operator_context_ids}; "
        "operator_context_counts_as_progress="
        f"{str(bool(stable_blockers.get('operator_context_counts_as_sdk_progress'))).lower()}"
    )


def format_side_lane_line(side_lane_id: str, payload: dict[str, Any]) -> str:
    context = dict_or_empty(payload.get("context"))
    parts = [
        f"label={payload.get('label')}",
        f"source_present={str(bool(payload.get('source_present'))).lower()}",
        f"synthetic_status_only={str(bool(payload.get('synthetic_status_only'))).lower()}",
        f"source_key={payload.get('source_key') or 'none'}",
        f"live_ops={str(bool(payload.get('live_ops_authorized'))).lower()}",
        f"workspace={str(bool(payload.get('workspace_writes_authorized'))).lower()}",
        f"runtime_capture={str(bool(payload.get('runtime_capture_authorized'))).lower()}",
        f"read_live_logs={str(bool(payload.get('read_live_logs'))).lower()}",
        (
            "sdk_progress="
            f"{payload.get('complete_sdk_claim_progress_contribution')}"
        ),
        (
            "p0_progress="
            f"{payload.get('p0_dependency_chain_claim_progress_contribution')}"
        ),
    ]
    accounting_route = compact_string(context.get("accounting_route"))
    if accounting_route:
        parts.append(f"accounting_route={accounting_route}")
    source_binding_count = compact_string(context.get("source_binding_count"))
    if source_binding_count:
        parts.append(f"source_binding_count={source_binding_count}")
    source_overclaims = compact_string_values(
        payload.get("source_overclaimed_authorization_or_claim_flags")
    )
    if source_overclaims:
        parts.append(f"source_overclaims={format_compact_list(source_overclaims)}")
    source_progress_overclaims = compact_string_values(
        payload.get("source_overclaimed_progress_flags")
    )
    if source_progress_overclaims:
        parts.append(
            f"source_progress_overclaims={format_compact_list(source_progress_overclaims)}"
        )
    return f"  - {side_lane_id}: " + "; ".join(parts)


def format_text(report: dict[str, Any]) -> str:
    header_gate = report.get("header_gate") or {}
    approved_in_game_evidence = report.get("approved_in_game_evidence") or {}
    critical_path_summary = report.get("critical_path_summary") or {}
    lines = [
        "Obelisk SDK status report",
        f"- status: {report.get('status')}",
        f"- current_route_blocker: {report.get('current_route_blocker')}",
        (
            f"- stable_claim_allowed: {str(report.get('stable_claim_allowed')).lower()}; "
            f"stable_sdk_ready: {str(report.get('stable_sdk_ready')).lower()}"
        ),
        f"- public_sdk_ready: {str(report.get('public_sdk_ready')).lower()}; runtime_ready: {str(report.get('runtime_ready')).lower()}",
        f"- {format_count_summary('SDK counts', report.get('sdk_counts') or {})}",
        f"- {format_count_summary('P0 counts', report.get('p0_counts') or {})}",
        (
            "- public header gate: "
            f"review_ready={str(header_gate.get('accepted_for_header_gate_review')).lower()}; "
            f"public_header_allowed={str(header_gate.get('public_header_allowed')).lower()}; "
            f"promotion_ready={str(header_gate.get('promotion_ready')).lower()}; "
            f"next_blocker={header_gate.get('next_blocker')}; "
            f"proposed_symbols={header_gate.get('proposed_symbols_count')}"
        ),
        f"- {format_private_logout_correlation(report)}",
        (
            "- critical_path: "
            f"current={critical_path_summary.get('current_route_blocker')}; "
            f"next_required_artifact={critical_path_summary.get('next_required_artifact')}; "
            f"after_runtime_evidence={critical_path_summary.get('after_runtime_evidence')}; "
            f"SDK={critical_path_summary.get('complete_sdk_progress_ratio')}; "
            f"P0={critical_path_summary.get('p0_dependency_chain_progress_ratio')}; "
            "live_ops_authorized="
            f"{str(bool(critical_path_summary.get('live_ops_authorized'))).lower()}; "
            "public_sdk_ready="
            f"{str(bool(critical_path_summary.get('public_sdk_ready'))).lower()}"
        ),
        f"- {format_stable_sdk_remaining_blockers(report)}",
        f"- {format_post_evidence_p0_lock_simulation(report)}",
        f"- {format_p0_offline_roadmap(report)}",
        f"- {format_principal_start_end_runtime_evidence(report)}",
        f"- {format_multi_surface_beta_capture_pack(report)}",
        f"- {format_discord_beta_bridge(report)}",
    ]
    runtime_evidence_window = report.get("runtime_evidence_window")
    if (
        isinstance(runtime_evidence_window, dict)
        and runtime_evidence_window.get("source_present") is True
    ):
        lines.append(f"- {format_runtime_evidence_window(report)}")
    lines.append(f"- {format_current_live_diagnostic_blockers(report)}")
    lines.extend(
        [
            (
            "- approved in-game evidence: "
            f"ready={str(bool(approved_in_game_evidence.get('approved_in_game_evidence_ready'))).lower()}; "
            f"approved_runtime_evidence={str(bool(approved_in_game_evidence.get('approved_runtime_evidence'))).lower()}; "
            "diagnostic_complete_triplet="
            f"{str(bool(approved_in_game_evidence.get('complete_lifecycle_event_triplet_observed_diagnostic_only'))).lower()}; "
            f"current_turn_scope_required={str(bool(approved_in_game_evidence.get('current_turn_scope_required'))).lower()}; "
            "standing_launch_authority_recorded="
            f"{str(bool(approved_in_game_evidence.get('standing_launch_authority_recorded'))).lower()}; "
            f"next_required_artifact={approved_in_game_evidence.get('next_required_artifact')}; "
            f"blocker_reason={approved_in_game_evidence.get('blocker_reason')}"
            ),
            f"- {format_debug_first_acceleration(report)}",
        ]
    )
    source_readiness_overclaims = report.get("source_overclaimed_readiness_flags") or []
    if source_readiness_overclaims:
        lines.append(
            "- source readiness overclaims normalized false: "
            + ",".join(str(flag) for flag in source_readiness_overclaims)
        )
    source_route_overclaims = report.get("source_overclaimed_route_flags") or []
    if source_route_overclaims:
        lines.append(
            "- source route overclaims normalized to approved_runtime_evidence_missing: "
            + ",".join(str(flag) for flag in source_route_overclaims)
        )
    source_count_overclaims = report.get("source_overclaimed_count_flags") or []
    if source_count_overclaims:
        lines.append(
            "- source count overclaims normalized to current blocker: "
            + ",".join(str(flag) for flag in source_count_overclaims)
        )
    source_overclaim_summary = report.get("source_overclaim_summary") or {}
    if isinstance(source_overclaim_summary, dict):
        total_source_overclaim_flags = source_overclaim_summary.get("total_flag_count")
        source_overclaim_components = source_overclaim_summary.get("component_count")
        if isinstance(total_source_overclaim_flags, int) and total_source_overclaim_flags:
            lines.append(
                "- source overclaim summary: "
                f"total_flags={total_source_overclaim_flags}; "
                f"components={source_overclaim_components}"
            )
    non_counting_alias_violations = report.get(
        "non_counting_false_progress_alias_violations"
    ) or []
    if non_counting_alias_violations:
        lines.append(
            "- non-counting false progress aliases observed: "
            + ",".join(str(path) for path in non_counting_alias_violations)
            + "; ordered_p0_chain_promoted="
            + str(
                bool(report.get("p0_dependency_chain_full_ordered_promotion_observed"))
            ).lower()
        )
    header_readiness_overclaims = header_gate.get("source_overclaimed_readiness_flags") or []
    if header_readiness_overclaims:
        lines.append(
            "- header source readiness overclaims normalized false: "
            + ",".join(str(flag) for flag in header_readiness_overclaims)
        )
    fastest = report.get("fastest_next_sdk_unblock") or {}
    if isinstance(fastest, dict):
        fastest_parts: list[str] = []
        recommended_next_action = compact_string(fastest.get("recommended_next_action"))
        if recommended_next_action:
            fastest_parts.append(recommended_next_action)
        next_required_artifact = compact_string(fastest.get("next_required_artifact"))
        if next_required_artifact:
            fastest_parts.append(f"next_required_artifact={next_required_artifact}")
        current_turn_scope_required = fastest.get("current_turn_scope_required")
        if isinstance(current_turn_scope_required, bool):
            fastest_parts.append(
                f"current_turn_scope_required={str(current_turn_scope_required).lower()}"
            )
        standing_launch_authority_recorded = fastest.get("standing_launch_authority_recorded")
        if isinstance(standing_launch_authority_recorded, bool):
            fastest_parts.append(
                "standing_launch_authority_recorded="
                f"{str(standing_launch_authority_recorded).lower()}"
            )
        player_notice_action_required = fastest.get("player_notice_action_required")
        if isinstance(player_notice_action_required, bool):
            fastest_parts.append(
                "player_notice_action_required="
                f"{str(player_notice_action_required).lower()}"
            )
        fastest_parts.extend(
            [
                f"live_ops_authorized={str(bool(fastest.get('live_ops_authorized'))).lower()}",
                f"workspace_writes_authorized={str(bool(fastest.get('workspace_writes_authorized'))).lower()}",
                f"runtime_capture_authorized={str(bool(fastest.get('runtime_capture_authorized'))).lower()}",
                f"discord_authorized={str(bool(fastest.get('discord_authorized'))).lower()}",
            ]
        )
        lines.append(
            "- fastest_next_sdk_unblock: "
            + ("; ".join(fastest_parts) if fastest_parts else "unavailable")
        )
    side_lanes = report.get("side_lanes")
    if isinstance(side_lanes, dict) and side_lanes:
        lines.append(f"- non-claim side lanes: {len(side_lanes)}")
        side_lane_source_overclaim_count = report.get("side_lane_source_overclaim_count")
        if isinstance(side_lane_source_overclaim_count, int) and side_lane_source_overclaim_count:
            side_lane_source_overclaim_ids = compact_string_values(
                report.get("side_lane_source_overclaim_side_lanes")
            )
            suffix = (
                f" ({format_compact_list(side_lane_source_overclaim_ids)})"
                if side_lane_source_overclaim_ids
                else ""
            )
            authorization_or_claim_flag_count = report.get(
                "side_lane_source_overclaim_authorization_or_claim_flag_count"
            )
            progress_flag_count = report.get(
                "side_lane_source_overclaim_progress_flag_count"
            )
            count_suffix = ""
            if isinstance(authorization_or_claim_flag_count, int) and isinstance(
                progress_flag_count, int
            ):
                count_suffix = (
                    f"; authorization_or_claim_flags={authorization_or_claim_flag_count}; "
                    f"progress_flags={progress_flag_count}"
                )
            lines.append(
                "- side-lane source overclaims normalized: "
                f"{side_lane_source_overclaim_count}{suffix}{count_suffix}"
            )
        for side_lane_id, payload in side_lanes.items():
            if isinstance(payload, dict):
                lines.append(format_side_lane_line(side_lane_id, payload))
    closure = report.get("closure")
    if isinstance(closure, dict):
        missing = ", ".join(closure.get("missing_required_artifacts") or []) or "none"
        lines.append(f"- closure missing artifacts: {missing}")
        closure_readiness_overclaims = closure.get("source_overclaimed_readiness_flags") or []
        if closure_readiness_overclaims:
            lines.append(
                "- closure source readiness overclaims: "
                + ",".join(str(flag) for flag in closure_readiness_overclaims)
                + "; normalized_public_sdk_ready=false; normalized_runtime_ready=false"
            )
        closure_evidence_overclaims = closure.get("source_overclaimed_evidence_flags") or []
        if closure_evidence_overclaims:
            lines.append(
                "- closure source evidence overclaims: "
                + ",".join(str(flag) for flag in closure_evidence_overclaims)
                + "; normalized_approved_runtime_evidence=false"
            )
    actionable_paths = report.get("actionable_paths")
    if isinstance(actionable_paths, dict) and actionable_paths:
        lines.append(f"- non-authorizing action paths: {len(actionable_paths)}")
        for path_id, path_payload in actionable_paths.items():
            if isinstance(path_payload, dict):
                lines.append(format_action_path_line(path_id, path_payload))
    lines.append(f"- {format_false_authorizations(report)}")
    lines.append(
        "- non-claim: request packs, player notices, accepted runtime evidence, sidecars, "
        "passive snapshots, and closure requests are not SDK/P0 progress; "
        "this report does not authorize runtime work, live ops, workspace writes, or SDK readiness"
    )
    return "\n".join(lines) + "\n"


def format_compact_summary(report: dict[str, Any]) -> str:
    simulation = report.get("post_evidence_p0_lock_simulation")
    after_runtime_evidence = None
    if isinstance(simulation, dict):
        after_runtime_evidence = compact_string(
            simulation.get("simulated_route_blocker_after_accepted_runtime_evidence")
        )
    debug_first = report.get("debug_first_acceleration")
    if not isinstance(debug_first, dict):
        debug_first = {}
    start_end = report.get("principal_start_end_runtime_evidence")
    if not isinstance(start_end, dict):
        start_end = {}
    multi_surface_pack = report.get("multi_surface_beta_capture_pack")
    if not isinstance(multi_surface_pack, dict):
        multi_surface_pack = {}
    discord_bridge = report.get("discord_beta_bridge")
    if not isinstance(discord_bridge, dict):
        discord_bridge = {}
    runtime_evidence_window = report.get("runtime_evidence_window")
    if not isinstance(runtime_evidence_window, dict):
        runtime_evidence_window = {}
    p0_roadmap = report.get("p0_offline_roadmap")
    if not isinstance(p0_roadmap, dict):
        p0_roadmap = {}
    debug_roles = format_compact_list(
        compact_string_values(debug_first.get("required_event_roles"))
    )
    route_parts = [
        f"status={report.get('status')}",
        f"route={report.get('current_route_blocker')}",
        f"next={report.get('next_required_artifact')}",
        f"missing={report.get('missing_required_artifact')}",
    ]
    if after_runtime_evidence:
        route_parts.append(f"after_runtime_evidence={after_runtime_evidence}")
    lines = [
        "Obelisk SDK status: " + "; ".join(route_parts),
        (
            "Progress: "
            f"SDK={report.get('complete_sdk_progress_ratio')}; "
            f"P0={report.get('p0_chain_progress_ratio') or report.get('p0_dependency_chain_progress_ratio')}; "
            f"stable_claim_allowed={str(bool(report.get('stable_claim_allowed'))).lower()}; "
            f"stable_sdk_ready={str(bool(report.get('stable_sdk_ready'))).lower()}"
        ),
        "Stable blockers: "
        + format_stable_sdk_remaining_blockers(report).removeprefix(
            "stable SDK remaining blockers: "
        ),
        (
            "Readiness: "
            f"runtime={str(bool(report.get('runtime_ready'))).lower()}; "
            f"public_sdk={str(bool(report.get('public_sdk_ready'))).lower()}; "
            f"approved_runtime_evidence="
            f"{str(bool(report.get('approved_runtime_evidence_ready'))).lower()}; "
            f"approved_in_game="
            f"{str(bool(report.get('approved_in_game_evidence_ready'))).lower()}"
        ),
        (
            "P0 offline roadmap: "
            f"current={p0_roadmap.get('current_route_blocker')}; "
            f"next_runtime={p0_roadmap.get('next_required_artifact')}; "
            f"after_runtime={p0_roadmap.get('after_runtime_evidence')}; "
            "next_offline="
            f"{p0_roadmap.get('next_offline_surface_after_runtime_evidence')}; "
            "post_identity_bridge="
            f"{p0_roadmap.get('post_identity_bridge_required_artifact')}; "
            "post_permissions_bridge="
            f"{p0_roadmap.get('post_permissions_admin_bridge_required_artifact')}; "
            "post_command_response_bridge="
            f"{p0_roadmap.get('post_command_chat_response_bridge_required_artifact')}; "
            "commands_replies_final_gate="
            f"{p0_roadmap.get('commands_replies_final_gate_required_artifact')}; "
            "commands_replies_final_gate_schema="
            f"{p0_roadmap.get('commands_replies_final_gate_required_schema')}; "
            "commands_replies_final_gate_status="
            f"{p0_roadmap.get('commands_replies_final_gate_status')}; "
            "commands_replies_final_gate_present="
            f"{str(bool(p0_roadmap.get('commands_replies_final_gate_certificate_present'))).lower()}; "
            "order="
            f"{format_compact_list(compact_string_values(p0_roadmap.get('downstream_offline_order')))}; "
            "roadmap_only="
            f"{str(bool(p0_roadmap.get('roadmap_only'))).lower()}; "
            "SDK_progress="
            f"{p0_roadmap.get('complete_sdk_claim_progress_contribution')}; "
            "P0_progress="
            f"{p0_roadmap.get('p0_dependency_chain_claim_progress_contribution')}"
        ),
        (
            "Principal start/end input: "
            f"source_present={str(bool(start_end.get('source_present'))).lower()}; "
            "accepted_for_contract_review="
            f"{str(bool(start_end.get('accepted_for_contract_review'))).lower()}; "
            "approved_runtime_evidence="
            f"{str(bool(start_end.get('approved_runtime_evidence'))).lower()}; "
            f"runtime={str(bool(start_end.get('runtime_ready'))).lower()}; "
            f"public_sdk={str(bool(start_end.get('public_sdk_ready'))).lower()}; "
            f"SDK_progress={start_end.get('complete_sdk_claim_progress_contribution')}; "
            f"P0_progress={start_end.get('p0_dependency_chain_claim_progress_contribution')}"
        ),
        (
            "Multi-surface beta pack: "
            f"source_present={str(bool(multi_surface_pack.get('source_present'))).lower()}; "
            "candidate_pack_validated="
            f"{str(bool(multi_surface_pack.get('candidate_pack_validated'))).lower()}; "
            f"source_kind={multi_surface_pack.get('source_kind') or 'none'}; "
            f"target={format_action_path_target(multi_surface_pack.get('target'))}; "
            f"surfaces={multi_surface_pack.get('candidate_surface_count')}; "
            "approved_runtime_evidence="
            f"{str(bool(multi_surface_pack.get('approved_runtime_evidence'))).lower()}; "
            f"runtime={str(bool(multi_surface_pack.get('runtime_ready'))).lower()}; "
            f"public_sdk={str(bool(multi_surface_pack.get('public_sdk_ready'))).lower()}; "
            f"stable_sdk={str(bool(multi_surface_pack.get('stable_sdk_ready'))).lower()}; "
            "SDK_progress="
            f"{multi_surface_pack.get('complete_sdk_claim_progress_contribution')}; "
            "P0_progress="
            f"{multi_surface_pack.get('p0_dependency_chain_claim_progress_contribution')}"
        ),
        (
            "Discord beta bridge: "
            f"source_present={str(bool(discord_bridge.get('source_present'))).lower()}; "
            f"config_valid={str(bool(discord_bridge.get('config_valid'))).lower()}; "
            f"token_present={str(bool(discord_bridge.get('token_present'))).lower()}; "
            "discord_py_available="
            f"{str(bool(discord_bridge.get('discord_py_available'))).lower()}; "
            f"discord_authorized={str(bool(discord_bridge.get('discord_authorized'))).lower()}; "
            "SDK_progress="
            f"{discord_bridge.get('complete_sdk_claim_progress_contribution')}; "
            "P0_progress="
            f"{discord_bridge.get('p0_dependency_chain_claim_progress_contribution')}"
        ),
        (
            "Debug-first path: "
            f"{debug_first.get('compact_blocker_chain')}; "
            f"next_action={debug_first.get('next_action')}; "
            f"checker={debug_first.get('next_checker')}; "
            f"roles={debug_roles}; "
            f"authorization={debug_first.get('authorization')}; "
            "approved_runtime_evidence_ready="
            f"{str(bool(debug_first.get('approved_runtime_evidence_ready'))).lower()}; "
            "SDK_progress="
            f"{debug_first.get('complete_sdk_claim_progress_contribution')}; "
            "P0_progress="
            f"{debug_first.get('p0_dependency_chain_claim_progress_contribution')}"
        ),
        (
            "Source overclaims: "
            f"total={report.get('source_overclaim_total_flag_count')}; "
            f"components={report.get('source_overclaim_component_count')}; "
            f"side_lanes={report.get('side_lane_source_overclaim_count')}"
        ),
        (
            "Non-claim: status report only; no live-ops authorization, runtime evidence, "
            "public SDK readiness, SDK/P0 progress, stable SDK claim, Plugin Hub readiness, "
            "publication permission, or Discord authorization."
        ),
    ]
    if runtime_evidence_window.get("source_present") is True:
        beta_notice = (
            "completed"
            if runtime_evidence_window.get("confirmed_beta_notice_completed") is True
            else "present"
            if runtime_evidence_window.get("confirmed_beta_notice_json_supplied") is True
            else "none"
        )
        copy_ready = compact_string(runtime_evidence_window.get("copy_readiness"))
        if not copy_ready:
            copy_ready = compact_string(runtime_evidence_window.get("copy_ready_status"))
        if not copy_ready:
            copy_ready = (
                "observer_only_no_roles"
                if runtime_evidence_window.get(
                    "copy_ready_active_observer_only_no_role_window"
                )
                is True
                else "none"
            )
        runtime_window_line = (
            "Runtime evidence window: "
            "source_present=true; "
            f"status={runtime_evidence_window.get('status')}; "
            f"window_state={runtime_evidence_window.get('window_state')}; "
            f"players={runtime_evidence_window.get('player_context')}; "
            "monitor_tick="
            f"{runtime_evidence_window.get('monitor_latest_tick_utc') or 'none'}; "
            f"beta_notice={beta_notice}; "
            f"copy_ready={copy_ready}; "
            "missing_roles="
            f"{format_compact_list(compact_string_values(runtime_evidence_window.get('missing_lifecycle_event_roles')))}; "
            "next_input="
            f"{runtime_evidence_window.get('next_status_input_needed') or 'none'}; "
            "approved_runtime_evidence="
            f"{str(bool(runtime_evidence_window.get('approved_runtime_evidence'))).lower()}; "
            f"runtime={str(bool(runtime_evidence_window.get('runtime_ready'))).lower()}; "
            f"public_sdk={str(bool(runtime_evidence_window.get('public_sdk_ready'))).lower()}; "
            "SDK_progress="
            f"{runtime_evidence_window.get('complete_sdk_claim_progress_contribution')}; "
            "P0_progress="
            f"{runtime_evidence_window.get('p0_dependency_chain_claim_progress_contribution')}"
        )
        lines.insert(6, runtime_window_line)
    live_context_line = format_current_live_diagnostic_blockers(report)
    lines.insert(7, live_context_line[:1].upper() + live_context_line[1:])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    public_sdk, public_sdk_returncode = load_or_run_public_sdk(args)
    header_gate, header_gate_returncode = load_or_run_header_gate(args)
    closure, closure_returncode = load_or_run_closure(args)
    (
        principal_start_end_runtime_evidence,
        principal_start_end_runtime_evidence_path_value,
        principal_start_end_runtime_evidence_source,
    ) = load_principal_start_end_runtime_evidence(args)
    (
        multi_surface_beta_capture_pack,
        multi_surface_beta_capture_pack_path,
        multi_surface_beta_capture_pack_source,
    ) = load_multi_surface_beta_capture_pack(args)
    (
        runtime_evidence_status,
        runtime_evidence_status_path,
        runtime_evidence_status_source,
    ) = load_runtime_evidence_status(args)
    (
        discord_beta_bridge_config,
        discord_beta_bridge_config_path,
        discord_beta_bridge_config_source,
    ) = load_discord_beta_bridge_config(args)
    public_contract_decisions = load_public_contract_decisions(args)
    report = summarize(
        public_sdk=public_sdk,
        public_sdk_returncode=public_sdk_returncode,
        header_gate=header_gate,
        header_gate_returncode=header_gate_returncode,
        public_contract_decisions=public_contract_decisions,
        closure=closure,
        closure_returncode=closure_returncode,
        principal_start_end_runtime_evidence=principal_start_end_runtime_evidence,
        principal_start_end_runtime_evidence_path=(
            principal_start_end_runtime_evidence_path_value
        ),
        principal_start_end_runtime_evidence_source=(
            principal_start_end_runtime_evidence_source
        ),
        multi_surface_beta_capture_pack=multi_surface_beta_capture_pack,
        multi_surface_beta_capture_pack_path=multi_surface_beta_capture_pack_path,
        multi_surface_beta_capture_pack_source=multi_surface_beta_capture_pack_source,
        runtime_evidence_status=runtime_evidence_status,
        runtime_evidence_status_path=runtime_evidence_status_path,
        runtime_evidence_status_source=runtime_evidence_status_source,
        discord_beta_bridge_config=discord_beta_bridge_config,
        discord_beta_bridge_config_path=discord_beta_bridge_config_path,
        discord_beta_bridge_config_source=discord_beta_bridge_config_source,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.compact:
        print(format_compact_summary(report), end="")
    else:
        print(format_text(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
